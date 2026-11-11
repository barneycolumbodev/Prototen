class_name Explosion
extends RefCounted
## A blast (the SD-3 drone's warhead). Everything alive within `radius`
## with a clear line to the centre is hit through its chest hitbox with
## falloff, thrown away from the blast and, at Maximum gore, torn apart:
## limbs off by how close they are, the whole body burst up close. The
## operative is hurt too if he's inside it. Fire, smoke, sparks, debris, a flash of light, a scorch of noise the squads hear.

const FLASH_TIME: float = 0.22


## Returns how many it killed.
static func detonate(world: Node3D, at: Vector3, radius: float, damage: float, shooter: Node, weapon: WeaponData) -> int:
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
			p.take_damage(damage * 0.45 * (1.0 - pd / radius), (at - eye).normalized())
	effects(world, at, radius)
	EventBus.shot_fired.emit(shooter, at, Vector3.UP)
	return kills


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


## The look and sound of it.
static func effects(world: Node3D, at: Vector3, radius: float) -> void:
	Sfx.play_at(&"explosion", at, 6.0, 0.06)
	Sfx.play_ui(&"explosion_far", -8.0, 0.05)
	if not Fx.enabled:
		return
	for i: int in 5:
		var dir: Vector3 = Vector3(randf_range(-1, 1), randf_range(0.1, 1), randf_range(-1, 1)).normalized()
		Fx._emit(&"flame", at + dir * 0.2, dir, Color(1.0, 0.62, 0.22, 1.0), 26, 0.55)
		Fx._emit(&"sparks", at, dir, Color(1.0, 0.8, 0.45, 1.0), 30, 2.4)
	for i: int in 4:
		Fx._emit(&"dust", at + Vector3(randf_range(-0.6, 0.6), 0.2, randf_range(-0.6, 0.6)), Vector3.UP, Color(0.16, 0.15, 0.14, 0.55), 22, 1.6)
	Fx.debris(at + Vector3.UP * 0.15, Vector3.UP * 5.0, Color(0.2, 0.2, 0.2), 0.06, 10, 4.0)
	var light: OmniLight3D = OmniLight3D.new()
	light.light_color = Color(1.0, 0.7, 0.38)
	light.light_energy = 14.0
	light.omni_range = radius * 2.2
	light.shadow_enabled = false
	var level: Node = world.get_parent() if world.get_parent() else world.get_tree().current_scene
	level.add_child(light)
	light.global_position = at + Vector3.UP * 0.4
	var tw: Tween = light.create_tween()
	tw.tween_property(light, ^"light_energy", 0.0, FLASH_TIME)
	tw.tween_callback(light.queue_free)
