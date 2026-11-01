class_name SteelPlate
extends Node3D
## AR500 popper on a stand: rings, flashes, and falls back on its hinge when
## hit hard enough, then pops back up. Lead splash marks stay on the plate.
## Faces +Z.

@export var plate_size: Vector2 = Vector2(0.3, 0.45)
@export var height: float = 1.1
@export var round_plate: bool = false
## Momentum (N·s, after impulse_scale) needed to knock it down.
@export var knockdown_impulse: float = 4.0
@export var reset_time: float = 2.0

var down: bool = false

var _hinge: Node3D
var _plate: StaticBody3D
var _mat: StandardMaterial3D
var _swing: Spring
var _flash: float = 0.0
var _down_time: float = 0.0


func _ready() -> void:
	add_to_group(&"range_targets")
	set_meta(&"dynamic_holes", true)
	add_to_group(&"aim_assist_targets")
	_swing = Spring.new(2.6, 0.35)
	_build()


func aim_points() -> PackedVector3Array:
	return PackedVector3Array() if down else PackedVector3Array([_plate.global_position])


func on_plate_hit(hit: BallisticHit) -> void:
	_flash = 1.0
	# Swing back by the push; past the threshold it goes over.
	_swing.kick(Vector3(hit.damage.impulse * 4.0, 0, 0))
	var kind: StringName = &"hit"
	if not down and hit.damage.impulse >= knockdown_impulse:
		down = true
		_down_time = 0.0
		_swing.target = Vector3(80.0, 0, 0)
		remove_from_group(&"aim_assist_targets")
		kind = &"kill"
	EventBus.target_hit.emit(kind, hit)


func _process(delta: float) -> void:
	_swing.step(delta)
	_hinge.rotation.x = -deg_to_rad(clampf(_swing.value.x, -20.0, 88.0))
	if _flash > 0.0:
		_flash = maxf(0.0, _flash - delta * 6.0)
		_mat.emission_energy_multiplier = _flash * 2.5
	if down:
		_down_time += delta
		if _down_time > reset_time:
			down = false
			_swing.target = Vector3.ZERO
			add_to_group(&"aim_assist_targets")


func _build() -> void:
	var paint: StandardMaterial3D = StandardMaterial3D.new()
	paint.albedo_color = Color(0.16, 0.17, 0.18)
	paint.metallic = 0.6
	paint.roughness = 0.6
	var stand: StaticBody3D = StaticBody3D.new()
	stand.set_meta(&"surface", &"sheet_metal")
	add_child(stand)
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for spec: Array in [[Vector3(0.05, height - 0.05, 0.05), Vector3(0, (height - 0.05) * 0.5, -0.06)],
			[Vector3(0.5, 0.04, 0.4), Vector3(0, 0.02, -0.06)]]:
		var size: Vector3 = spec[0]
		var at: Vector3 = spec[1]
		var bm: BoxMesh = BoxMesh.new()
		bm.size = size
		st.append_from(bm, 0, Transform3D(Basis(), at))
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = size
		cs.shape = box
		cs.position = at
		stand.add_child(cs)
	var stand_mesh: MeshInstance3D = MeshInstance3D.new()
	stand_mesh.mesh = st.commit()
	stand_mesh.material_override = paint
	add_child(stand_mesh)

	_hinge = Node3D.new()
	_hinge.position = Vector3(0, height - 0.05, 0)
	add_child(_hinge)
	_plate = PlateBody.new()
	(_plate as PlateBody).owner_plate = self
	_plate.set_meta(&"surface", &"steel_target")
	_plate.collision_layer = Ballistics.LAYER_WORLD
	_plate.position = Vector3(0, 0.05 + plate_size.y * 0.5, 0)
	_hinge.add_child(_plate)
	var cs2: CollisionShape3D = CollisionShape3D.new()
	var mi: MeshInstance3D = MeshInstance3D.new()
	if round_plate:
		var cyl: CylinderShape3D = CylinderShape3D.new()
		cyl.radius = plate_size.x * 0.5
		cyl.height = 0.012
		cs2.shape = cyl
		cs2.rotation.x = PI * 0.5
		var cm: CylinderMesh = CylinderMesh.new()
		cm.top_radius = plate_size.x * 0.5
		cm.bottom_radius = plate_size.x * 0.5
		cm.height = 0.012
		cm.radial_segments = 24
		mi.mesh = cm
		mi.rotation.x = PI * 0.5
	else:
		var box2: BoxShape3D = BoxShape3D.new()
		box2.size = Vector3(plate_size.x, plate_size.y, 0.012)
		cs2.shape = box2
		var bm2: BoxMesh = BoxMesh.new()
		bm2.size = box2.size
		mi.mesh = bm2
	_plate.add_child(cs2)
	_mat = StandardMaterial3D.new()
	_mat.albedo_color = Color(0.86, 0.86, 0.82)  # painted white so splashes read
	_mat.roughness = 0.7
	_mat.emission_enabled = true
	_mat.emission = Color(1.0, 0.9, 0.6)
	_mat.emission_energy_multiplier = 0.0
	mi.material_override = _mat
	_plate.add_child(mi)
	# Hanger arm from the hinge to the plate.
	var arm: MeshInstance3D = MeshInstance3D.new()
	var arm_mesh: BoxMesh = BoxMesh.new()
	arm_mesh.size = Vector3(0.03, 0.08, 0.03)
	arm.mesh = arm_mesh
	arm.position = Vector3(0, 0.02, -0.01)
	arm.material_override = paint
	_hinge.add_child(arm)


class PlateBody:
	extends StaticBody3D
	var owner_plate: SteelPlate

	func on_ballistic_hit(hit: BallisticHit) -> void:
		owner_plate.on_plate_hit(hit)
