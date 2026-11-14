class_name Explosion
extends RefCounted
## Blasts: the SD-3 drone's warhead and the 40 mm grenades (docs/design.md
## §3.4b, §4.8).
##
## Blast (`detonate`): everything alive within `radius` with a clear line to
## the centre is hit through its chest hitbox with falloff, thrown away from
## the blast and, at Maximum gore, torn apart: limbs off by how close they
## are, the whole body burst up close. The operative is hurt too if he's
## inside it.
##
## Fragments (`fragments`, the grenades): each live body near the burst gets
## the share of the fragments that would reach it (its projected area ÷ the
## sphere at its distance, drawn as a Poisson count), and each one is fired as
## a real Ballistics round from the burst at a random zone, weighted by the
## zone's size. So a wall, a car or another man in the way stops them, a
## fragment wounds the zone it reaches (a leg: he limps), and the near misses
## suppress like gunfire. A handful more fly off at random for the pockmarks
## and sparks around the burst. The operative's share is worked out the same
## way and taken as damage directly.
##
## The look is ExplosionFx (fireball, smoke, dust ring, scorch), plus sparks,
## debris, a flash of light, camera shake and, close in, stunned hearing.

const FLASH_TIME: float = 0.22
## Zones a fragment is aimed at, weighted by their projected area (m², a
## standing man; they sum to about 0.67).
const FRAGMENT_ZONES: Dictionary[StringName, float] = {
	&"head": 0.031, &"neck": 0.010, &"chest": 0.083, &"stomach": 0.054, &"pelvis": 0.065,
	&"l_upper_arm": 0.035, &"r_upper_arm": 0.035, &"l_forearm": 0.027, &"r_forearm": 0.027,
	&"l_hand": 0.014, &"r_hand": 0.014, &"l_thigh": 0.076, &"r_thigh": 0.076,
	&"l_shin": 0.053, &"r_shin": 0.053, &"l_foot": 0.010, &"r_foot": 0.010,
}

## Fragments fired by the last burst (tests): at bodies, and scattered.
static var last_aimed: int = 0
static var last_scattered: int = 0
static var last_player_fragments: int = 0
static var _rng: RandomNumberGenerator


static func rng() -> RandomNumberGenerator:
	if _rng == null:
		_rng = RandomNumberGenerator.new()
		_rng.randomize()
	return _rng


## The blast alone. Returns how many it killed. `self_scale`: the share the
## operative takes inside the radius. `with_effects`: also the drone's look.
static func detonate(world: Node3D, at: Vector3, radius: float, damage: float, shooter: Node, weapon: WeaponData,
		self_scale: float = 0.45, with_effects: bool = true) -> int:
	var tree: SceneTree = world.get_tree()
	var space: PhysicsDirectSpaceState3D = world.get_world_3d().direct_space_state
	var kills: int = 0
	for n: Node in tree.get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive:
			continue
		var chest: Vector3 = e.body.chest_position()
		var d: float = chest.distance_to(at)
		if d > radius or not _clear(space, at, chest):
			continue
		var f: float = 1.0 - pow(d / radius, 1.5)
		var dir: Vector3 = (chest - at).normalized() if d > 0.05 else Vector3.UP
		dir = (dir + Vector3.UP * 0.35).normalized()
		var part: HitboxPart = e.parts.get(&"chest")
		if part == null:
			continue
		AugHit.strike(part, weapon, shooter, chest - dir * 0.1, dir, damage * f, 10.0 + 30.0 * f, 600.0 + 3000.0 * f, DamageInfo.Type.EXPLOSIVE, false)
		if not e.alive:
			kills += 1
		if Gore.is_maximum():
			_tear(e, at, radius, f, dir)
	var p: Player = tree.get_first_node_in_group(&"player") as Player
	if p and not p.dead:
		var eye: Vector3 = p.camera().global_position
		var pd: float = eye.distance_to(at)
		if pd < radius and _clear(space, at, eye):
			p.take_damage(damage * self_scale * (1.0 - pd / radius), (at - eye).normalized())
	if with_effects:
		effects(world, at, radius)
	EventBus.shot_fired.emit(shooter, at, Vector3.UP)
	return kills


## A 40 mm grenade bursting at `at` (`normal`: the surface it hit, or back
## along its flight for an airburst). Blast, fragments, look and feel.
## Returns how many it killed.
static func grenade(world: Node3D, at: Vector3, normal: Vector3, g: GrenadeData, weapon: WeaponData, shooter: Node,
		airburst: bool) -> int:
	var n: Vector3 = normal.normalized() if normal.length() > 0.01 else Vector3.UP
	var kills: int = detonate(world, at, g.blast_radius, g.blast_damage, shooter, weapon, g.self_blast_scale, false)
	kills += fragments(world, at, n, g, shooter, airburst)
	if Fx.enabled:
		Fx.explosion(at, n, g.fireball_radius, airburst)
	_feel(world, at, g)
	Sfx.play_at(&"grenade_blast", at, 8.0, 0.07)
	Sfx.play_ui(&"grenade_blast_far", -10.0, 0.05)
	return kills


## The fragments of a burst at `at`. Returns the kills they made.
static func fragments(world: Node3D, at: Vector3, normal: Vector3, g: GrenadeData, shooter: Node, airburst: bool) -> int:
	var tree: SceneTree = world.get_tree()
	var space: PhysicsDirectSpaceState3D = world.get_world_3d().direct_space_state
	var w: WeaponData = g.fragment_weapon()
	var r: RandomNumberGenerator = rng()
	var origin: Vector3 = at + normal * 0.03
	var kills: int = 0
	last_aimed = 0
	last_scattered = 0
	last_player_fragments = 0
	var volley: int = 0
	for node: Node in tree.get_nodes_in_group(&"enemies"):
		var e: Enemy = node as Enemy
		if e == null or not e.alive:
			continue
		var chest: Vector3 = e.body.chest_position()
		var d: float = chest.distance_to(at)
		if d > g.fragment_range:
			continue
		# A surface burst throws nothing into the surface itself.
		if not airburst and (chest - at).dot(normal) < -0.1:
			continue
		var count: int = mini(poisson(g.expected_fragments(d, g.body_area_m2), r), g.fragment_max_per_body)
		for i: int in count:
			var zone: StringName = pick_zone(r)
			var part: HitboxPart = e.parts.get(zone)
			if part == null:
				continue
			var aim: Vector3 = part.global_position + Vector3(r.randf_range(-0.04, 0.04), r.randf_range(-0.05, 0.05),
					r.randf_range(-0.04, 0.04))
			var id: int = Ballistics.fire(w, origin, (aim - origin).normalized(), shooter, Vector3.INF, volley)
			if volley == 0:
				volley = id
			last_aimed += 1
		if count > 0 and not e.alive:
			kills += 1
	# Scatter: pockmarks, sparks and near misses around the burst.
	for i: int in g.fragment_scatter:
		var dir: Vector3 = Vector3(r.randf_range(-1, 1), r.randf_range(-1, 1), r.randf_range(-1, 1)).normalized()
		if not airburst and dir.dot(normal) < 0.0:
			dir = dir - normal * (2.0 * dir.dot(normal))
		dir = (dir + normal * 0.25).normalized()
		Ballistics.fire(w, origin, dir, shooter, Vector3.INF, volley)
		last_scattered += 1
	# The operative: his share, straight off his health.
	var p: Player = tree.get_first_node_in_group(&"player") as Player
	if p and not p.dead:
		var eye: Vector3 = p.camera().global_position
		var mid: Vector3 = eye + Vector3.DOWN * 0.6
		var pd: float = mid.distance_to(at)
		if pd < g.fragment_range and _clear(space, origin, mid):
			var hits: int = mini(poisson(g.expected_fragments(pd, g.body_area_m2 * 0.85), r), g.fragment_max_per_body)
			last_player_fragments = hits
			if hits > 0:
				var per_kj: float = p.body.stat(&"damage_per_kj") if p.body else 1.0
				p.take_damage(g.fragment_energy_at(pd) * 0.001 * per_kj * float(hits), (at - eye).normalized())
	return kills


## Shake, a light, sparks and debris; stunned hearing close in.
static func _feel(world: Node3D, at: Vector3, g: GrenadeData) -> void:
	var p: Player = world.get_tree().get_first_node_in_group(&"player") as Player
	if p and not p.dead:
		var d: float = p.camera().global_position.distance_to(at)
		if d < g.shake_range:
			var k: float = 1.0 - d / g.shake_range
			p.add_shake(g.shake_strength * k * k)
			for pad: int in Input.get_connected_joypads():
				Input.start_joy_vibration(pad, 0.6 * k, 1.0 * k, 0.25 + 0.3 * k)
		if d < g.concussion_range:
			Sfx.concuss(1.0 - d / g.concussion_range)
	if not Fx.enabled:
		return
	for i: int in 4:
		var dir: Vector3 = Vector3(randf_range(-1, 1), randf_range(0.2, 1), randf_range(-1, 1)).normalized()
		Fx._emit(&"sparks", at, dir, Color(1.0, 0.8, 0.45, 1.0), 26, 2.6)
	Fx.debris(at + Vector3.UP * 0.15, Vector3.UP * 5.0, Color(0.2, 0.2, 0.2), 0.05, 8, 4.0)
	_flash(world, at, g.blast_radius)


## A Poisson count with mean `mean` (Knuth; means here are small).
static func poisson(mean: float, r: RandomNumberGenerator) -> int:
	if mean <= 0.0:
		return 0
	if mean > 20.0:
		return maxi(0, roundi(r.randfn(mean, sqrt(mean))))
	var limit: float = exp(-mean)
	var k: int = 0
	var prod: float = r.randf()
	while prod > limit:
		k += 1
		prod *= r.randf()
	return k


## A zone at random, weighted by projected area.
static func pick_zone(r: RandomNumberGenerator) -> StringName:
	var total: float = 0.0
	for z: StringName in FRAGMENT_ZONES:
		total += FRAGMENT_ZONES[z]
	var x: float = r.randf() * total
	for z: StringName in FRAGMENT_ZONES:
		x -= FRAGMENT_ZONES[z]
		if x <= 0.0:
			return z
	return &"chest"


## Maximum gore: the blast tears at each limb by how close its cut is (the
## side facing it goes first); up close the body bursts (GoreConfig).
static func _tear(e: Enemy, at: Vector3, radius: float, f: float, dir: Vector3) -> void:
	var cfg: GoreConfig = Gore.config
	if f >= cfg.blast_gib_f:
		e.burst(dir * cfg.gib_speed * f)
		return
	for seg: StringName in e.body.cut_points().keys():
		if e.body.is_severed(seg):
			continue  # went with its parent this blast
		var cut: Vector3 = e.body.cut_point(seg)
		var fc: float = 1.0 - pow(clampf(cut.distance_to(at) / radius, 0.0, 1.0), 1.5)
		if fc < cfg.blast_sever_f:
			continue
		var out: Vector3 = (cut - at).normalized() if cut.distance_to(at) > 0.05 else dir
		var v: Vector3 = (out + Vector3.UP * 0.4).normalized() * cfg.gib_speed * fc
		e.sever(seg, v, fc > cfg.blast_sever_f + (1.0 - cfg.blast_sever_f) * 0.6)


static func _clear(space: PhysicsDirectSpaceState3D, from: Vector3, to: Vector3) -> bool:
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, Ballistics.LAYER_WORLD)
	return space.intersect_ray(q).is_empty()


## The drone's look and sound: the shared fireball, sparks, debris, a light.
static func effects(world: Node3D, at: Vector3, radius: float) -> void:
	Sfx.play_at(&"explosion", at, 6.0, 0.06)
	Sfx.play_ui(&"explosion_far", -8.0, 0.05)
	if not Fx.enabled:
		return
	Fx.explosion(at, Vector3.UP, radius * 0.15, false)
	for i: int in 4:
		var dir: Vector3 = Vector3(randf_range(-1, 1), randf_range(0.1, 1), randf_range(-1, 1)).normalized()
		Fx._emit(&"sparks", at, dir, Color(1.0, 0.8, 0.45, 1.0), 30, 2.4)
	Fx.debris(at + Vector3.UP * 0.15, Vector3.UP * 5.0, Color(0.2, 0.2, 0.2), 0.06, 10, 4.0)
	_flash(world, at, radius)


## A brief light at the burst (one of the ≤ 4 dynamic lights, no shadows).
static func _flash(world: Node3D, at: Vector3, radius: float) -> void:
	var light: OmniLight3D = OmniLight3D.new()
	light.light_color = Color(1.0, 0.7, 0.38)
	light.light_energy = 14.0
	light.omni_range = radius * 2.6
	light.shadow_enabled = false
	world.add_child(light)
	light.global_position = at + Vector3.UP * 0.4
	var tw: Tween = light.create_tween()
	tw.tween_property(light, ^"light_energy", 0.0, FLASH_TIME)
	tw.tween_callback(light.queue_free)
