extends Node3D
## 40 mm grenades in flight (docs/design.md §4.8). Autoloaded as Grenades.
##
## A launched round is a real projectile stepped every physics tick (world
## time, so RX-9 slow motion slows it): gravity, quadratic drag, a ray along
## each step against the world, hitboxes, props and debris. Its fuze arms
## after `GrenadeData.arming_distance` of flight. Armed, it bursts on contact
## (on a body: right where it touched him), or in the air where its programmed
## airburst distance runs out (the fire control's lased range + offset).
## Unarmed, it's a 230 g lump at 76 m/s: a body it hits takes a blunt blow
## and is shoved, and the round bounces off the world as a dud, skids, lies
## there and is cleared away later.
##
## The burst itself is Explosion.grenade (blast, fragments, the fireball).
## Up to MAX_LIVE rounds and duds at once (the oldest dud goes first).

signal detonated(at: Vector3, kills: int)
signal dud(at: Vector3)

const MAX_LIVE: int = 14
## The round seen in flight (loaded on first use, not preloaded: an autoload
## compiles before a fresh checkout's first import has the glTF ready).
const SCENE_PATH: String = "res://assets/weapons/m32/grenade_40mm.gltf"
## Rounds at least this close to the camera aren't drawn (the first tick
## would put one across the view).
const HIDE_NEAR: float = 0.55

## Bursts since start, and where the last one was (tests, demos).
var bursts: int = 0
var last_burst: Vector3 = Vector3.INF
var last_burst_airburst: bool = false
var last_kills: int = 0
var duds: int = 0


class Round:
	extends RefCounted
	var data: GrenadeData
	var weapon: WeaponData
	var shooter: Node
	var position: Vector3
	var velocity: Vector3
	var travelled: float = 0.0
	var age: float = 0.0
	## Programmed burst distance along the flight path (-1: impact only).
	var fuze_at: float = -1.0
	var armed: bool = false
	var dud: bool = false
	var resting: bool = false
	var rest_age: float = 0.0
	var spin: float = 0.0
	var bounces: int = 0
	var hit_bodies: Array[int] = []
	var exclude: Array[RID] = []
	var node: Node3D
	var alive: bool = true


var _live: Array[Round] = []
var _pool: Array[Node3D] = []
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _scene: PackedScene


func _ready() -> void:
	_rng.randomize()


## Launches a round from `origin` at `velocity`. `fuze_at` > 0 programs an
## airburst that many metres along the flight path.
func launch(g: GrenadeData, weapon: WeaponData, origin: Vector3, velocity: Vector3, shooter: Node,
		fuze_at: float = -1.0) -> Round:
	var r: Round = Round.new()
	r.data = g
	r.weapon = weapon
	r.shooter = shooter
	r.position = origin
	r.velocity = velocity
	r.fuze_at = fuze_at
	r.spin = _rng.randf() * TAU
	if shooter and shooter.has_method(&"ballistic_exclude"):
		r.exclude = shooter.call(&"ballistic_exclude")
	r.node = _claim_node()
	_place(r)
	_live.append(r)
	_trim()
	# First tick now: a point-blank round lands on the trigger frame.
	_step(r, 1.0 / Engine.physics_ticks_per_second * Engine.time_scale)
	_place(r)
	return r


func live_count() -> int:
	var n: int = 0
	for r: Round in _live:
		if r.alive and not r.dud:
			n += 1
	return n


func dud_count() -> int:
	var n: int = 0
	for r: Round in _live:
		if r.alive and r.dud:
			n += 1
	return n


## Rounds and duds, newest last (tests).
func rounds() -> Array[Round]:
	return _live


func clear() -> void:
	for r: Round in _live:
		_release(r)
	_live.clear()


func _physics_process(delta: float) -> void:
	if _live.is_empty():
		return
	for r: Round in _live:
		if r.alive:
			_step(r, delta)
	var still: Array[Round] = []
	for r: Round in _live:
		if r.alive:
			still.append(r)
		else:
			_release(r)
	_live = still


func _process(delta: float) -> void:
	var cam: Camera3D = get_viewport().get_camera_3d()
	for r: Round in _live:
		if not r.alive:
			continue
		if not r.resting:
			r.spin += r.data.spin_hz * TAU * delta * (0.15 if r.dud else 1.0)
		_place(r)
		if cam and r.node:
			r.node.visible = r.node.global_position.distance_to(cam.global_position) > HIDE_NEAR


func _step(r: Round, delta: float) -> void:
	if not r.alive or delta <= 0.0:
		return
	r.age += delta
	if r.dud:
		_step_dud(r, delta)
		return
	if r.age > r.data.max_flight_time:
		r.alive = false
		return
	var g: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
	r.velocity = r.data.step_velocity(r.velocity, delta, g)
	var move: Vector3 = r.velocity * delta
	var length: float = move.length()
	if length < 0.00001:
		return
	var dir: Vector3 = move / length
	# Airburst: the programmed distance runs out somewhere along this step.
	var burst_in: float = r.fuze_at - r.travelled if r.fuze_at > 0.0 else INF
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(r.position, r.position + move,
			Ballistics.BULLET_MASK, r.exclude)
	q.hit_back_faces = false
	var res: Dictionary = space.intersect_ray(q)
	var hit_at: float = INF
	if not res.is_empty():
		var contact: Vector3 = res["position"]
		hit_at = r.position.distance_to(contact)
	if burst_in <= length and burst_in < hit_at and r.travelled + burst_in >= r.data.arming_distance:
		_burst(r, r.position + dir * maxf(burst_in, 0.0), -dir, true)
		return
	if res.is_empty():
		r.position += move
		r.travelled += length
		r.armed = r.travelled >= r.data.arming_distance
		return
	var point: Vector3 = res["position"]
	var normal: Vector3 = res["normal"]
	r.travelled += hit_at
	r.armed = r.travelled >= r.data.arming_distance
	var collider: Object = res["collider"]
	if r.armed:
		# Point detonating: on a body it bursts where it touched him; on a
		# surface a little off it.
		var at: Vector3 = point - dir * 0.04 if collider is HitboxPart else point + normal * 0.05
		_burst(r, at, normal, false)
		return
	_dud_hit(r, collider, point, normal, dir)


## An unarmed round hits something: a body takes a blow, a surface bounces it.
func _dud_hit(r: Round, collider: Object, point: Vector3, normal: Vector3, dir: Vector3) -> void:
	var speed: float = r.velocity.length()
	var energy: float = 0.5 * r.data.mass_kg * speed * speed
	var part: HitboxPart = collider as HitboxPart
	r.dud = true
	duds += 1
	dud.emit(point)
	if part:
		var who: int = part.target.get_instance_id() if part.target else part.get_instance_id()
		if who not in r.hit_bodies:
			r.hit_bodies.append(who)
			AugHit.strike(part, r.weapon, r.shooter, point, dir, energy * r.data.blunt_damage_per_j,
					r.data.mass_kg * speed, energy, DamageInfo.Type.BLUNT, false)
			var e: Enemy = part.target as Enemy
			if e and e.alive:
				e.knock_back(dir * minf(speed * 0.06, 4.0), r.shooter, 0.0, 12.0)
		Sfx.play_at(&"m32_dud_body", point, -2.0, 0.08)
		# Drops off him.
		r.velocity = -dir * speed * 0.12 + Vector3.UP * 1.2
		r.position = point - dir * 0.06
		r.exclude.append(part.get_rid())
		return
	var body: RigidBody3D = collider as RigidBody3D
	if body:
		body.apply_impulse(dir * r.data.mass_kg * speed * 0.5, point - body.global_position)
	_bounce(r, point, normal, speed)


func _bounce(r: Round, point: Vector3, normal: Vector3, speed: float) -> void:
	var vn: Vector3 = normal * r.velocity.dot(normal)
	var vt: Vector3 = r.velocity - vn
	r.velocity = vt * (1.0 - r.data.bounce_friction) - vn * r.data.bounce_restitution
	r.position = point + normal * 0.022
	r.bounces += 1
	if speed > 3.0:
		Sfx.play_at(&"m32_dud_bounce", point, linear_to_db(clampf(speed / 40.0, 0.15, 1.0)), 0.1)
	if r.velocity.length() < 0.6 and normal.y > 0.6:
		r.resting = true
		r.velocity = Vector3.ZERO


## A dud skidding to a stop and lying there.
func _step_dud(r: Round, delta: float) -> void:
	if r.resting:
		r.rest_age += delta
		if r.rest_age > r.data.dud_lifetime:
			r.alive = false
		return
	if r.age > r.data.max_flight_time:
		r.alive = false
		return
	var g: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
	r.velocity.y -= g * delta
	var move: Vector3 = r.velocity * delta
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(r.position, r.position + move,
			Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS, r.exclude)
	var res: Dictionary = space.intersect_ray(q)
	if res.is_empty():
		r.position += move
		return
	var n: Vector3 = res["normal"]
	var at: Vector3 = res["position"]
	_bounce(r, at, n, r.velocity.length())
	if r.bounces > 12:
		r.resting = true


func _burst(r: Round, at: Vector3, normal: Vector3, airburst: bool) -> void:
	r.alive = false
	r.position = at
	bursts += 1
	last_burst = at
	last_burst_airburst = airburst
	var world: Node3D = get_tree().current_scene as Node3D
	if world == null:
		world = self
	last_kills = Explosion.grenade(world, at, normal, r.data, r.weapon, r.shooter, airburst)
	detonated.emit(at, last_kills)


func _place(r: Round) -> void:
	if r.node == null:
		return
	var dir: Vector3 = r.velocity.normalized() if r.velocity.length() > 0.5 else r.node.global_basis.x
	if r.resting:
		return
	var up: Vector3 = Vector3.UP if absf(dir.y) < 0.98 else Vector3.RIGHT
	var z: Vector3 = dir.cross(up).normalized()
	var y: Vector3 = z.cross(dir).normalized()
	var b: Basis = Basis(dir, y, z) * Basis(Vector3.RIGHT, r.spin)
	r.node.global_transform = Transform3D(b, r.position)


func _claim_node() -> Node3D:
	var n: Node3D
	if not _pool.is_empty():
		n = _pool.pop_back()
	else:
		if _scene == null:
			_scene = load(SCENE_PATH) as PackedScene
		n = _scene.instantiate() as Node3D if _scene else Node3D.new()
		add_child(n)
		for g: Node in n.find_children("*", "GeometryInstance3D", true, false):
			(g as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	n.visible = true
	return n


func _release(r: Round) -> void:
	if r.node:
		r.node.visible = false
		_pool.append(r.node)
		r.node = null


## Over the cap: the oldest dud goes first, then the oldest round.
func _trim() -> void:
	while _live.size() > MAX_LIVE:
		var drop: int = 0
		for i: int in _live.size():
			if _live[i].dud:
				drop = i
				break
		_release(_live[drop])
		_live.remove_at(drop)
