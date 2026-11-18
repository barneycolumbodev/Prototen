class_name PlasmaBolts
extends Node3D
## Plasma bolts in flight (the SL-9 Slagger, docs/design.md §4.9). One node
## under the scene root (`PlasmaBolts.get_for(node)`; not an Fx member: Fx is
## an autoload and this depends on Enemy), a small pool (MAX_BOLTS, the
## first two with a light).
##
## Each bolt is a glowing mass that flies (slower than a bullet, with a
## little droop), trailing sparks, and checks every tick:
## - square hits (a ray along its path, its radius ahead): a man takes
##   Enemy.on_plasma_hit, which may burn a hole through him (the bolt goes
##   on, weaker, `PlasmaData.through_keep`), take a limb off cauterised and
##   burning, or set him alight; anything else with hitboxes gets the
##   ballistic hit and catches fire; a surface stops it in a splash of
##   molten fire that sets alight whoever stands in it;
## - grazes (a sphere of `graze` radius round it, every other tick): men it
##   passes close to catch fire and run screaming (Enemy.on_plasma_graze).

const MAX_BOLTS: int = 5
const LIGHTS: int = 2

class Bolt:
	extends RefCounted
	var id: int = 0
	var live: bool = false
	var pos: Vector3
	var vel: Vector3
	var charge: float = 1.0
	var life: float = 0.0
	var shooter: Node
	var weapon: WeaponData
	var pd: PlasmaData
	var exclude: Array[RID] = []
	var touched: Dictionary = {}
	var node: Node3D
	var ball: MeshInstance3D
	var ball_mat: ShaderMaterial
	var trail: CPUParticles3D
	var light: OmniLight3D
	var tick: int = 0

static var _instance: PlasmaBolts


## The one PlasmaBolts in `from`'s tree (made on first use).
static func get_for(from: Node) -> PlasmaBolts:
	if _instance == null or not is_instance_valid(_instance) or not _instance.is_inside_tree():
		_instance = PlasmaBolts.new()
		_instance.name = "PlasmaBolts"
		from.get_tree().root.add_child(_instance)
	return _instance


var bolts: Array[Bolt] = []
var _next: int = 0
var _serial: int = 900000
## For tests and the overlay.
var launched: int = 0
var hits: int = 0
var grazes: int = 0
var splashes: int = 0


func _ensure(pd: PlasmaData) -> void:
	if not bolts.is_empty():
		return
	for i: int in MAX_BOLTS:
		var b: Bolt = Bolt.new()
		b.node = Node3D.new()
		b.node.visible = false
		add_child(b.node)
		b.ball = MeshInstance3D.new()
		var sm: SphereMesh = SphereMesh.new()
		sm.radius = 1.0
		sm.height = 2.0
		sm.radial_segments = 16
		sm.rings = 8
		b.ball.mesh = sm
		b.ball_mat = PlasmaCharge.ball_material(pd)
		b.ball.material_override = b.ball_mat
		b.ball.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		b.node.add_child(b.ball)
		b.trail = CPUParticles3D.new()
		b.trail.amount = 40
		b.trail.lifetime = 0.4
		b.trail.local_coords = false
		b.trail.emitting = false
		b.trail.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
		b.trail.emission_sphere_radius = 0.03
		b.trail.spread = 180.0
		b.trail.initial_velocity_min = 0.2
		b.trail.initial_velocity_max = 1.2
		b.trail.gravity = Vector3(0, -3.0, 0)
		b.trail.scale_amount_min = 0.01
		b.trail.scale_amount_max = 0.03
		var curve: Curve = Curve.new()
		curve.add_point(Vector2(0.0, 1.0))
		curve.add_point(Vector2(1.0, 0.0))
		b.trail.scale_amount_curve = curve
		var qm: QuadMesh = QuadMesh.new()
		var m: StandardMaterial3D = StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		m.billboard_keep_scale = true
		m.vertex_color_use_as_albedo = true
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.albedo_texture = Fx._soft_dot()
		m.albedo_color = Color(1.0, 0.5, 0.15) * 2.5
		qm.material = m
		b.trail.mesh = qm
		b.node.add_child(b.trail)
		if i < LIGHTS:
			b.light = OmniLight3D.new()
			b.light.light_color = pd.hot_color
			b.light.shadow_enabled = false
			b.light.omni_attenuation = 1.5
			b.node.add_child(b.light)
		bolts.append(b)


## Fires a bolt of `charge` (0..1) from `from` along `dir`.
func launch(weapon: WeaponData, from: Vector3, dir: Vector3, charge: float, shooter: Node) -> void:
	var pd: PlasmaData = weapon.plasma
	_ensure(pd)
	var b: Bolt = bolts[_next]
	# The pool wraps; the lit bolts go first while they're free.
	for i: int in bolts.size():
		if not bolts[i].live and (bolts[i].light != null or bolts[_next].live):
			b = bolts[i]
			break
	_next = (_next + 1) % bolts.size()
	_serial += 1
	b.id = _serial
	b.live = true
	b.pos = from
	b.vel = dir.normalized() * pd.speed(charge)
	b.charge = charge
	b.life = pd.lifetime
	b.shooter = shooter
	b.weapon = weapon
	b.pd = pd
	b.exclude.clear()
	b.touched.clear()
	if shooter is CollisionObject3D:
		b.exclude.append((shooter as CollisionObject3D).get_rid())
	b.node.visible = true
	b.node.global_position = from
	b.trail.emitting = true
	b.trail.restart()
	b.tick = 0
	launched += 1
	_dress(b)


func live_count() -> int:
	var n: int = 0
	for b: Bolt in bolts:
		if b.live:
			n += 1
	return n


func clear() -> void:
	for b: Bolt in bolts:
		_end(b)


func _dress(b: Bolt) -> void:
	var r: float = b.pd.radius(b.charge)
	b.ball.scale = Vector3.ONE * r * 1.25
	b.ball_mat.set_shader_parameter(&"intensity", lerpf(2.5, 5.0, b.charge))
	b.ball_mat.set_shader_parameter(&"heat", b.charge)
	b.ball_mat.set_shader_parameter(&"churn", 2.0 + 3.0 * b.charge)
	b.trail.emission_sphere_radius = r
	b.trail.scale_amount_max = 0.015 + 0.03 * b.charge
	if b.light:
		b.light.light_energy = b.pd.light_energy * (0.4 + 0.6 * b.charge)
		b.light.omni_range = b.pd.light_range * (0.5 + 0.5 * b.charge)


func _physics_process(delta: float) -> void:
	if bolts.is_empty():
		return
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	for b: Bolt in bolts:
		if not b.live:
			continue
		_step(b, delta, space)


func _step(b: Bolt, delta: float, space: PhysicsDirectSpaceState3D) -> void:
	b.life -= delta
	if b.life <= 0.0:
		_fizzle(b)
		return
	b.tick += 1
	b.vel.y -= b.pd.gravity * delta
	var dir: Vector3 = b.vel.normalized()
	var r: float = b.pd.radius(b.charge)
	var to: Vector3 = b.pos + b.vel * delta
	# Not debris: it would burst on the burned pieces it just threw out of a man.
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(b.pos, to + dir * r,
			Ballistics.BULLET_MASK & ~Ballistics.LAYER_DEBRIS, b.exclude)
	var res: Dictionary = space.intersect_ray(q)
	if not res.is_empty():
		var go_on: bool = _contact(b, res, dir)
		if not go_on:
			return
		to = b.pos
	else:
		b.pos = to
	if b.tick % 2 == 0:
		_graze(b, space, dir)
	b.node.global_position = b.pos
	var flick: float = 0.85 + 0.3 * randf()
	b.ball_mat.set_shader_parameter(&"flicker", flick)
	if b.light:
		b.light.light_energy = b.pd.light_energy * (0.4 + 0.6 * b.charge) * flick


## Returns whether the bolt carries on.
func _contact(b: Bolt, res: Dictionary, dir: Vector3) -> bool:
	var collider: Object = res["collider"]
	var point: Vector3 = res["position"]
	var normal: Vector3 = res["normal"]
	var part: HitboxPart = collider as HitboxPart
	if part:
		hits += 1
		var hit: BallisticHit = _make_hit(b, collider, point, normal, dir)
		var enemy: Enemy = part.target as Enemy
		if enemy:
			var stopped: bool = enemy.on_plasma_hit(part, hit, b.charge, b.pd)
			b.touched[enemy.get_instance_id()] = true
			if stopped:
				_splash(b, point, normal, collider, false)
				_end(b)
				return false
			# Burned through: on it goes, weaker, past this man.
			for rid: RID in enemy.ballistic_exclude():
				b.exclude.append(rid)
			b.charge *= b.pd.through_keep
			b.pos = point + dir * 0.05
			_dress(b)
			return true
		part.on_ballistic_hit(hit)
		part.on_burn(hit)
		_splash(b, point, normal, collider, false)
		_end(b)
		return false
	_splash(b, point, normal, collider, true)
	_end(b)
	return false


func _graze(b: Bolt, space: PhysicsDirectSpaceState3D, dir: Vector3) -> void:
	var g: float = b.pd.radius(b.charge) + b.pd.graze(b.charge)
	var shape: SphereShape3D = SphereShape3D.new()
	shape.radius = g
	var p: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	p.shape = shape
	p.transform = Transform3D(Basis(), b.pos)
	p.collision_mask = Ballistics.LAYER_HITBOX
	p.exclude = b.exclude
	for r: Dictionary in space.intersect_shape(p, 16):
		var obj: Object = r["collider"]
		var part: HitboxPart = obj as HitboxPart
		if part == null:
			continue
		var enemy: Enemy = part.target as Enemy
		if enemy == null or b.touched.has(enemy.get_instance_id()):
			continue
		b.touched[enemy.get_instance_id()] = true
		grazes += 1
		var hit: BallisticHit = _make_hit(b, part, part.global_position, -dir, dir)
		hit.damage.amount = b.pd.damage(b.charge) * 0.12
		enemy.on_plasma_graze(part, hit, b.charge, b.pd)


## Molten splash where it bursts: fire, sparks, a scorch; men close by catch fire.
func _splash(b: Bolt, point: Vector3, normal: Vector3, collider: Object, surface: bool) -> void:
	splashes += 1
	var c: float = b.charge
	if surface:
		if c > 0.45:
			Fx.explosion(point, normal, 0.2 + 0.5 * c, false)
		Fx._emit(&"sparks", point, normal, Color(1.0, 0.55, 0.18, 1.0), 14 + roundi(26.0 * c), 1.2 + 1.6 * c)
		Fx._emit(&"smoke", point, normal, Color(0.22, 0.2, 0.19, 0.35), 2 + roundi(3.0 * c), 0.8)
		Fx.burn_at(collider as Node3D, point, normal, 2.0 + 4.0 * c, true)
		Sfx.play_at(&"slagger_impact", point, -2.0 + 4.0 * c, 0.08)
	var radius: float = b.pd.splash_full * c
	if radius < 0.2:
		return
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var shape: SphereShape3D = SphereShape3D.new()
	shape.radius = radius
	var p: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	p.shape = shape
	p.transform = Transform3D(Basis(), point + normal * 0.1)
	p.collision_mask = Ballistics.LAYER_HITBOX
	for r: Dictionary in space.intersect_shape(p, 24):
		var obj: Object = r["collider"]
		var part: HitboxPart = obj as HitboxPart
		if part == null:
			continue
		var enemy: Enemy = part.target as Enemy
		if enemy == null or b.touched.has(enemy.get_instance_id()):
			continue
		b.touched[enemy.get_instance_id()] = true
		var hit: BallisticHit = _make_hit(b, part, part.global_position, normal, (part.global_position - point).normalized())
		hit.damage.amount = b.pd.splash_damage_full * c
		enemy.on_plasma_graze(part, hit, c, b.pd)


func _fizzle(b: Bolt) -> void:
	Fx._emit(&"sparks", b.pos, Vector3.UP, Color(1.0, 0.5, 0.15, 1.0), 10, 0.8)
	_end(b)


func _end(b: Bolt) -> void:
	b.live = false
	b.node.visible = false
	b.trail.emitting = false
	if b.light:
		b.light.light_energy = 0.0


func _make_hit(b: Bolt, collider: Object, point: Vector3, normal: Vector3, dir: Vector3) -> BallisticHit:
	var h: BallisticHit = BallisticHit.new()
	h.shot_id = b.id
	h.volley_id = b.id
	h.weapon = b.weapon
	h.shooter = b.shooter
	h.collider = collider
	h.point = point
	h.normal = normal
	h.direction = dir
	h.speed_in = b.vel.length()
	h.energy_in = b.pd.damage(b.charge) * 8.0
	h.energy_out = 0.0
	h.result = BallisticHit.Result.STOPPED
	var d: DamageInfo = DamageInfo.new()
	d.type = DamageInfo.Type.EXPLOSIVE
	d.amount = b.pd.damage(b.charge)
	d.impulse = 8.0 + 30.0 * b.charge
	var node: Node = collider as Node
	if node and node.has_meta(&"zone"):
		var zone: StringName = node.get_meta(&"zone")
		d.zone = zone
		if zone == &"head" or zone == &"neck":
			d.flags |= DamageInfo.Flags.HEADSHOT | DamageInfo.Flags.HEAVY
	d.point = point
	d.normal = normal
	d.source = b.shooter
	h.damage = d
	return h
