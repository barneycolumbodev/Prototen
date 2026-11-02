class_name TargetDummy
extends Node3D
## Range mannequin with 13 damage zones (docs/design.md §5.1). Shows where
## each round landed (holes stay on the body part, a readout names the zone
## and damage), wobbles on its stand from the round's momentum, and falls
## over the way it was shot when killed, then stands back up. Embers set it
## alight: it burns (damage over time, flames riding on the hit zone) until
## the fire goes out or it goes down.
## Faces +Z; its left side is +X.

const PARTS: Array = [
	# zone, shape ("sphere" r | "capsule" r,h | "box" size), position, roll_deg
	[&"head", "sphere", Vector3(0.105, 0, 0), Vector3(0, 1.62, 0), 0.0],
	[&"neck", "capsule", Vector3(0.055, 0.17, 0), Vector3(0, 1.475, 0), 0.0],
	[&"chest", "box", Vector3(0.38, 0.3, 0.22), Vector3(0, 1.27, 0), 0.0],
	[&"stomach", "box", Vector3(0.33, 0.2, 0.19), Vector3(0, 1.02, 0), 0.0],
	[&"pelvis", "box", Vector3(0.35, 0.17, 0.2), Vector3(0, 0.835, 0), 0.0],
	[&"l_upper_arm", "capsule", Vector3(0.05, 0.32, 0), Vector3(0.245, 1.24, 0), 8.0],
	[&"r_upper_arm", "capsule", Vector3(0.05, 0.32, 0), Vector3(-0.245, 1.24, 0), -8.0],
	[&"l_forearm", "capsule", Vector3(0.045, 0.3, 0), Vector3(0.275, 0.95, 0.03), 4.0],
	[&"r_forearm", "capsule", Vector3(0.045, 0.3, 0), Vector3(-0.275, 0.95, 0.03), -4.0],
	[&"l_thigh", "capsule", Vector3(0.075, 0.46, 0), Vector3(0.1, 0.53, 0), 0.0],
	[&"r_thigh", "capsule", Vector3(0.075, 0.46, 0), Vector3(-0.1, 0.53, 0), 0.0],
	[&"l_shin", "capsule", Vector3(0.055, 0.34, 0), Vector3(0.1, 0.17, 0), 0.0],
	[&"r_shin", "capsule", Vector3(0.055, 0.34, 0), Vector3(-0.1, 0.17, 0), 0.0],
]

const ZONE_NAMES: Dictionary[StringName, String] = {
	&"head": "HEAD", &"neck": "NECK", &"chest": "CHEST", &"stomach": "STOMACH", &"pelvis": "PELVIS",
	&"l_upper_arm": "L ARM", &"r_upper_arm": "R ARM", &"l_forearm": "L FOREARM", &"r_forearm": "R FOREARM",
	&"l_thigh": "L THIGH", &"r_thigh": "R THIGH", &"l_shin": "L SHIN", &"r_shin": "R SHIN",
}

@export var config: TargetDummyConfig = preload("res://data/targets/dummy.tres")
@export var body_color: Color = Color(0.78, 0.5, 0.3)

var health: float = 100.0
var dead: bool = false
## Hits per zone since the last reset.
var zone_hits: Dictionary[StringName, int] = {}
var parts: Dictionary[StringName, HitboxPart] = {}

var _body: Node3D
var _readout: Label3D
var _readout_time: float = 0.0
var _wobble: Spring
var _fall: Spring
var _dead_time: float = 0.0
## Seconds of fire left, damage per second, and the hit that started it.
var burn_left: float = 0.0
var burn_dps: float = 0.0
var _burn_hit: BallisticHit
var _burn_shown: float = 0.0


func _ready() -> void:
	add_to_group(&"aim_assist_targets")
	add_to_group(&"range_targets")
	add_to_group(&"enemies")  # while alive: reticles turn crimson over it
	set_meta(&"dynamic_holes", true)
	health = config.health
	_wobble = Spring.new(config.wobble_hz, config.wobble_damping)
	_fall = Spring.new(1.4, 0.55)
	_build()


func aim_points() -> PackedVector3Array:
	if dead:
		return PackedVector3Array()
	return PackedVector3Array([parts[&"head"].global_position, parts[&"chest"].global_position])


func on_part_hit(part: HitboxPart, hit: BallisticHit) -> void:
	var zone: StringName = part.get_meta(&"zone")
	# Momentum knocks the dummy on its stand; higher hits tip it more.
	var horizontal: Vector3 = Vector3(hit.direction.x, 0.0, hit.direction.z).normalized()
	var lever: float = clampf((hit.point.y - global_position.y) / 1.6, 0.2, 1.2)
	var axis: Vector3 = global_basis.inverse() * Vector3.UP.cross(horizontal)
	_wobble.kick(axis * hit.damage.impulse * config.wobble_per_impulse * lever)
	zone_hits[zone] = zone_hits.get(zone, 0) + 1
	if dead:
		EventBus.target_hit.emit(&"hit", hit)
		return
	var dmg: float = hit.damage.amount * config.zone_multipliers.get(zone, 1.0)
	health -= dmg
	var kind: StringName = &"hit"
	if health <= 0.0:
		kind = &"kill"
		_die(axis)
	elif hit.damage.has_flag(DamageInfo.Flags.HEADSHOT):
		kind = &"headshot"
	_show(zone, dmg, kind, hit)
	EventBus.target_hit.emit(kind, hit)


## An ember landed on `part`: (re)ignite. Fresh embers top the fire up.
func on_part_burn(part: HitboxPart, hit: BallisticHit) -> void:
	if dead:
		return
	if burn_left <= 0.0:
		Fx.burn_at(part, hit.point, hit.normal, hit.weapon.burn_time, true)
	burn_left = maxf(burn_left, hit.weapon.burn_time)
	burn_dps = maxf(burn_dps, hit.weapon.burn_dps)
	_burn_hit = hit


func is_burning() -> bool:
	return burn_left > 0.0


func reset_target() -> void:
	dead = false
	burn_left = 0.0
	burn_dps = 0.0
	health = config.health
	_fall.target = Vector3.ZERO
	zone_hits.clear()
	add_to_group(&"aim_assist_targets")
	add_to_group(&"enemies")


func _die(axis: Vector3) -> void:
	dead = true
	_dead_time = 0.0
	_fall.target = axis.normalized() * deg_to_rad(84.0)
	remove_from_group(&"aim_assist_targets")
	remove_from_group(&"enemies")


func _process(delta: float) -> void:
	if burn_left > 0.0:
		_burn(delta)
	_wobble.step(delta)
	_fall.step(delta)
	_body.basis = Basis.from_euler(_wobble.value * (PI / 180.0) + _fall.value)
	if dead:
		_dead_time += delta
		if _dead_time > config.reset_time:
			reset_target()
	if _readout_time > 0.0:
		_readout_time -= delta
		_readout.modulate.a = clampf(_readout_time / 0.5, 0.0, 1.0)
		_readout.outline_modulate.a = _readout.modulate.a


func _burn(delta: float) -> void:
	burn_left -= delta
	if dead or _burn_hit == null:
		burn_left = 0.0
		return
	health -= burn_dps * delta
	_burn_shown -= delta
	if health <= 0.0:
		burn_left = 0.0
		var horizontal: Vector3 = Vector3(_burn_hit.direction.x, 0.0, _burn_hit.direction.z).normalized()
		_die(global_basis.inverse() * Vector3.UP.cross(horizontal))
		_readout.text = "BURNING\nDOWN"
		_readout.modulate = Color(1.0, 0.45, 0.15)
		_readout_time = 2.0
		EventBus.target_hit.emit(&"kill", _burn_hit)
	elif _burn_shown <= 0.0:
		_burn_shown = 0.25
		_readout.text = "BURNING\n%d HP" % maxi(0, ceili(health))
		_readout.modulate = Color(1.0, 0.6, 0.25)
		_readout_time = 0.6
	if burn_left <= 0.0:
		burn_dps = 0.0


func _show(zone: StringName, dmg: float, kind: StringName, hit: BallisticHit) -> void:
	var tag: String = ZONE_NAMES.get(zone, String(zone))
	var extra: String = ""
	if hit.damage.has_flag(DamageInfo.Flags.PASS_THROUGH):
		extra = "  THROUGH"
	if hit.damage.has_flag(DamageInfo.Flags.PENETRATED):
		extra += "  (after cover)"
	_readout.text = "%s  %d%s\n%d HP" % [tag, roundi(dmg), extra, maxi(0, ceili(health))]
	match kind:
		&"kill":
			_readout.modulate = Color(1.0, 0.3, 0.25)
			_readout.text = "%s  %d%s\nDOWN" % [tag, roundi(dmg), extra]
		&"headshot":
			_readout.modulate = Color(1.0, 0.82, 0.3)
		_:
			_readout.modulate = Color(1, 1, 1)
	_readout_time = 2.0


func _build() -> void:
	# Stand: base plate and a post behind the dummy (sheet metal).
	var stand: StaticBody3D = StaticBody3D.new()
	stand.set_meta(&"surface", &"sheet_metal")
	add_child(stand)
	var post_shape: CollisionShape3D = CollisionShape3D.new()
	var post_box: BoxShape3D = BoxShape3D.new()
	post_box.size = Vector3(0.05, 1.0, 0.05)
	post_shape.shape = post_box
	post_shape.position = Vector3(0, 0.5, -0.16)
	stand.add_child(post_shape)
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var plate: CylinderMesh = CylinderMesh.new()
	plate.top_radius = 0.3
	plate.bottom_radius = 0.32
	plate.height = 0.03
	st.append_from(plate, 0, Transform3D(Basis(), Vector3(0, 0.015, -0.05)))
	var post: BoxMesh = BoxMesh.new()
	post.size = post_box.size
	st.append_from(post, 0, Transform3D(Basis(), post_shape.position))
	var stand_mesh: MeshInstance3D = MeshInstance3D.new()
	stand_mesh.mesh = st.commit()
	var steel: StandardMaterial3D = StandardMaterial3D.new()
	steel.albedo_color = Color(0.2, 0.21, 0.22)
	steel.metallic = 0.7
	steel.roughness = 0.5
	stand_mesh.material_override = steel
	add_child(stand_mesh)

	_body = Node3D.new()
	_body.name = "Body"
	add_child(_body)
	var body_st: SurfaceTool = SurfaceTool.new()
	body_st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for p: Array in PARTS:
		var zone: StringName = p[0]
		var kind: String = p[1]
		var dims: Vector3 = p[2]
		var pos: Vector3 = p[3]
		var roll: float = p[4]
		var xform: Transform3D = Transform3D(Basis(Vector3.FORWARD, deg_to_rad(roll)), pos)
		var shape: Shape3D
		var mesh: PrimitiveMesh
		match kind:
			"sphere":
				var s: SphereShape3D = SphereShape3D.new()
				s.radius = dims.x
				shape = s
				var sm: SphereMesh = SphereMesh.new()
				sm.radius = dims.x
				sm.height = dims.x * 2.0
				sm.radial_segments = 16
				sm.rings = 8
				mesh = sm
			"capsule":
				var c: CapsuleShape3D = CapsuleShape3D.new()
				c.radius = dims.x
				c.height = dims.y
				shape = c
				var cm: CapsuleMesh = CapsuleMesh.new()
				cm.radius = dims.x
				cm.height = dims.y
				cm.radial_segments = 12
				cm.rings = 2
				mesh = cm
			_:
				var b: BoxShape3D = BoxShape3D.new()
				b.size = dims
				shape = b
				var bm: BoxMesh = BoxMesh.new()
				bm.size = dims
				mesh = bm
		var part: HitboxPart = HitboxPart.new()
		part.name = String(zone)
		part.target = self
		part.collision_layer = Ballistics.LAYER_HITBOX
		part.collision_mask = 0
		part.set_meta(&"zone", zone)
		part.set_meta(&"surface", &"flesh")
		part.transform = xform
		var cs: CollisionShape3D = CollisionShape3D.new()
		cs.shape = shape
		part.add_child(cs)
		_body.add_child(part)
		parts[zone] = part
		body_st.append_from(mesh, 0, xform)
	var body_mesh: MeshInstance3D = MeshInstance3D.new()
	body_mesh.mesh = body_st.commit()
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = body_color
	mat.roughness = 0.55
	mat.rim_enabled = true
	mat.rim = 0.3
	body_mesh.material_override = mat
	_body.add_child(body_mesh)

	_readout = Label3D.new()
	_readout.position = Vector3(0, 2.05, 0)
	_readout.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_readout.no_depth_test = true
	_readout.fixed_size = true
	_readout.pixel_size = 0.0011
	_readout.font_size = 26
	_readout.outline_size = 8
	_readout.modulate.a = 0.0
	_readout.outline_modulate = Color(0, 0, 0, 0)
	add_child(_readout)
