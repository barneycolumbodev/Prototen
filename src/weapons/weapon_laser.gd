class_name WeaponLaser
extends Node3D
## Under-barrel laser (docs/design.md §4.6): a faint beam from the gun's
## emitter and a dot where it lands. The dot sits on the first surface along
## the gun's aim line from the eye (PlayerWeapon.aim_forward()), the same
## line the rounds leave along, so the dot is the centre of the shot cone.
## The beam is drawn from the emitter to the dot. Two draw calls, no light.

const BEAM_WIDTH: float = 0.0022
## Pulled toward the eye so the dot never sinks into the wall it's on.
const DOT_LIFT: float = 0.012

var data: WeaponData
## The dot is on a surface (false: nothing within range, or the laser is off).
var on_surface: bool = false
var hit_point: Vector3 = Vector3.ZERO
var hit_normal: Vector3 = Vector3.UP
var hit_collider: Object

var _beam: MeshInstance3D
var _dot: MeshInstance3D
var _beam_mat: ShaderMaterial
var _dot_mat: ShaderMaterial


func _ready() -> void:
	top_level = true
	_beam = MeshInstance3D.new()
	_beam.mesh = _beam_mesh()
	_beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_beam.extra_cull_margin = 16384.0
	_beam_mat = ShaderMaterial.new()
	_beam_mat.shader = preload("res://src/vfx/laser_beam.gdshader")
	_beam.material_override = _beam_mat
	add_child(_beam)
	_dot = MeshInstance3D.new()
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2.ONE
	_dot.mesh = quad
	_dot.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_dot.extra_cull_margin = 1.0
	_dot_mat = ShaderMaterial.new()
	_dot_mat.shader = preload("res://src/vfx/laser_dot.gdshader")
	_dot.material_override = _dot_mat
	add_child(_dot)
	hide_laser()


func set_data(d: WeaponData) -> void:
	data = d
	if d == null or d.laser_range <= 0.0:
		hide_laser()
		return
	_beam_mat.set_shader_parameter(&"color", d.laser_color)
	_dot_mat.set_shader_parameter(&"color", d.laser_color)


func hide_laser() -> void:
	on_surface = false
	hit_collider = null
	if _beam:
		_beam.visible = false
		_dot.visible = false


## Casts the laser from `eye` along `dir` and draws it from `emitter` (world
## space). `exclude`: bodies the ray ignores (the player).
func update_laser(emitter: Vector3, eye: Vector3, dir: Vector3, space: PhysicsDirectSpaceState3D,
		exclude: Array[RID] = []) -> void:
	if data == null or data.laser_range <= 0.0 or space == null:
		hide_laser()
		return
	var to: Vector3 = eye + dir * data.laser_range
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, to, Ballistics.BULLET_MASK, exclude)
	q.collide_with_areas = false
	var res: Dictionary = space.intersect_ray(q)
	on_surface = not res.is_empty()
	var end: Vector3 = to
	if on_surface:
		hit_point = res["position"]
		hit_normal = res["normal"]
		hit_collider = res["collider"]
		end = hit_point
	else:
		hit_collider = null
	_place_beam(emitter, end, not on_surface)
	_dot.visible = on_surface
	if on_surface:
		var dist: float = eye.distance_to(hit_point)
		var size: float = maxf(data.laser_dot_min_m, dist * tan(deg_to_rad(data.laser_dot_deg)))
		var back: Vector3 = (eye - hit_point).normalized()
		_dot.global_transform = Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * size),
				hit_point + hit_normal * 0.002 + back * minf(DOT_LIFT, dist * 0.2))


func _place_beam(from: Vector3, to: Vector3, open_ended: bool) -> void:
	var v: Vector3 = to - from
	var length: float = v.length()
	if length < 0.01 or data.laser_beam_energy <= 0.0:
		_beam.visible = false
		return
	_beam.visible = true
	# The mesh runs from 0 to -1 along Z; stretch it from the emitter to the dot.
	var b: Basis = Basis.looking_at(v / length, Vector3.UP if absf(v.normalized().y) < 0.99 else Vector3.RIGHT)
	_beam.global_transform = Transform3D(b.scaled_local(Vector3(BEAM_WIDTH, BEAM_WIDTH, length)), from)
	_beam_mat.set_shader_parameter(&"energy", data.laser_beam_energy)
	_beam_mat.set_shader_parameter(&"length", length)
	_beam_mat.set_shader_parameter(&"open_ended", 1.0 if open_ended else 0.0)


## Two crossed ribbons, 1 unit wide, from z = 0 to z = -1 (UV.y = 0 at the emitter).
static func _beam_mesh() -> ArrayMesh:
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for axis: Vector3 in [Vector3(0.5, 0, 0), Vector3(0, 0.5, 0)]:
		var corners: Array[Vector3] = [-axis, axis, axis + Vector3(0, 0, -1), -axis + Vector3(0, 0, -1)]
		var uvs: Array[Vector2] = [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
		for i: int in [0, 1, 2, 0, 2, 3]:
			st.set_uv(uvs[i])
			st.add_vertex(corners[i])
	return st.commit()


func dot_visible() -> bool:
	return _dot != null and _dot.visible


func beam_visible() -> bool:
	return _beam != null and _beam.visible


func dot_size() -> float:
	return _dot.global_basis.get_scale().x if _dot else 0.0
