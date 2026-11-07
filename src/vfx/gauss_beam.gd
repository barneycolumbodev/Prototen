class_name GaussBeam
extends MeshInstance3D
## One GX-4 shot's beam (Fx.gauss_beam). The mesh is built once and shared:
## a three-way crossed core 400 m long and a double helix 90 m long, along
## -Z. Each shot only moves the node to the muzzle, points it, and sets the
## length the shader clips to: no per-shot mesh work on the phone.

const CORE_LEN: float = 400.0
const HELIX_LEN: float = 90.0
const HELIX_RADIUS: float = 0.07
const HELIX_TURNS_PER_M: float = 1.1
const HELIX_STEPS_PER_TURN: int = 10
const RIBBON: float = 0.045
const SHADER: Shader = preload("res://src/vfx/gauss_beam.gdshader")

static var _mesh: ArrayMesh

var age: float = 99.0
var life: float = 1.2
var _mat: ShaderMaterial


func _init() -> void:
	if _mesh == null:
		_mesh = build_mesh()
	mesh = _mesh
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	material_override = _mat
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	top_level = true
	visible = false


func fire(from: Vector3, to: Vector3, color: Color, p_life: float = 1.2) -> void:
	var d: Vector3 = to - from
	var length: float = d.length()
	if length < 0.05:
		return
	var up: Vector3 = Vector3.UP if absf(d.normalized().y) < 0.98 else Vector3.RIGHT
	global_transform = Transform3D(Basis.looking_at(d / length, up), from)
	# Spin the helix a random amount so shots don't look stamped.
	rotate_object_local(Vector3.FORWARD, randf() * TAU)
	age = 0.0
	life = p_life
	_mat.set_shader_parameter(&"color", color)
	_mat.set_shader_parameter(&"beam_len", length)
	_mat.set_shader_parameter(&"life", life)
	_mat.set_shader_parameter(&"age", 0.0)
	visible = true


func is_live() -> bool:
	return visible


func _process(delta: float) -> void:
	if not visible:
		return
	age += delta
	_mat.set_shader_parameter(&"age", age)
	if age >= life:
		visible = false


static func build_mesh() -> ArrayMesh:
	var pos: PackedVector3Array = PackedVector3Array()
	var nrm: PackedVector3Array = PackedVector3Array()
	var uv: PackedVector2Array = PackedVector2Array()
	var uv2: PackedVector2Array = PackedVector2Array()
	var idx: PackedInt32Array = PackedInt32Array()
	# Core: a line and a wider glow; the shader turns them to face the camera.
	for glow: int in 2:
		var b: int = pos.size()
		pos.append_array([Vector3.ZERO, Vector3.ZERO, Vector3(0, 0, -CORE_LEN), Vector3(0, 0, -CORE_LEN)])
		uv.append_array([Vector2(0, 0), Vector2(0, 1), Vector2(CORE_LEN, 1), Vector2(CORE_LEN, 0)])
		for k: int in 4:
			nrm.append(Vector3(0, 0, -1))
			uv2.append(Vector2(0, glow))
		idx.append_array([b, b + 1, b + 2, b, b + 2, b + 3])
	# Double helix: bands lying flat to the axis (radial width), so from behind they read as a spiral.
	var steps: int = int(HELIX_LEN * HELIX_TURNS_PER_M * HELIX_STEPS_PER_TURN)
	for strand: int in 2:
		var phase: float = strand * PI
		var first: int = pos.size()
		for s: int in steps + 1:
			var z: float = float(s) / (HELIX_TURNS_PER_M * HELIX_STEPS_PER_TURN)
			var ang: float = z * HELIX_TURNS_PER_M * TAU + phase
			var radial: Vector3 = Vector3(cos(ang), sin(ang), 0.0)
			# Tight at the muzzle, opening over the first metre.
			var r: float = HELIX_RADIUS * (0.45 + 0.55 * minf(z, 1.0))
			var c: Vector3 = radial * r + Vector3(0, 0, -z)
			var half: Vector3 = radial * RIBBON * 0.5
			pos.append_array([c - half, c + half])
			nrm.append_array([radial, radial])
			uv.append_array([Vector2(z, 0), Vector2(z, 1)])
			uv2.append_array([Vector2(1, 0), Vector2(1, 0)])
			if s > 0:
				var b2: int = first + (s - 1) * 2
				idx.append_array([b2, b2 + 1, b2 + 3, b2, b2 + 3, b2 + 2])
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = pos
	arrays[Mesh.ARRAY_NORMAL] = nrm
	arrays[Mesh.ARRAY_TEX_UV] = uv
	arrays[Mesh.ARRAY_TEX_UV2] = uv2
	arrays[Mesh.ARRAY_INDEX] = idx
	var m: ArrayMesh = ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	m.custom_aabb = AABB(Vector3(-1, -1, -CORE_LEN), Vector3(2, 2, CORE_LEN))
	return m
