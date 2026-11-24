class_name FlameJet
extends Node3D
## Visuals for the Triad Flamer's aerosol flame stream:
## - One segmented tapered flame cone mesh (`flame_jet.gdshader`, 1 draw call)
##   oriented from the lighter/nozzle along the spray direction, clamped to
##   obstacle distance so fire never pokes through cover.
## - One lightweight world-space CPUParticles3D trail of flame tongues & sparks
##   that bends naturally through the air as the Flamer strafes.
## - One warm orange OmniLight3D, visible ONLY while actively spraying.
## Driven in game time (`step(delta)`) so RX-9 slow motion slows the roar.

const JET_SHADER: Shader = preload("res://src/vfx/flame_jet.gdshader")
const PILOT_SHADER: Shader = preload("res://src/vfx/pilot_flame.gdshader")

static var _cone_mesh: ArrayMesh
static var _spark_tex: ImageTexture
static var _spark_ramp: Gradient
static var _spark_curve: Curve
static var _pilot_quad: QuadMesh

var active: bool = false
var intensity: float = 0.0
var reach_m: float = 6.5

var _now: float = 0.0
var _cone: MeshInstance3D
var _cone_mat: ShaderMaterial
var _particles: CPUParticles3D
var _light: OmniLight3D
var _seed: float = 0.0


func _ready() -> void:
	top_level = true
	_seed = randf() * 10.0
	_build_cone()
	_build_particles()
	_build_light()


## Builds a flickering pilot flame mesh to parent onto the Flamer's lighter wick.
static func make_pilot_flame() -> MeshInstance3D:
	if _pilot_quad == null:
		_pilot_quad = QuadMesh.new()
		_pilot_quad.size = Vector2(0.026, 0.046)
		_pilot_quad.center_offset = Vector3(0.0, 0.020, 0.0)
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = PILOT_SHADER
	mat.set_shader_parameter(&"flare", 1.0)
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.name = "PilotFlame"
	mi.mesh = _pilot_quad
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


func set_stream(on: bool, origin: Vector3, dir: Vector3, dist_m: float) -> void:
	active = on
	reach_m = clampf(dist_m, 0.5, 10.0)
	var d: Vector3 = dir.normalized() if dir.length_squared() > 0.0001 else Vector3.FORWARD
	var up: Vector3 = Vector3.UP if absf(d.y) < 0.94 else Vector3.RIGHT
	# Cone mesh points along local +Z, so Basis columns are (right, up, forward = d).
	var right: Vector3 = up.cross(d).normalized()
	var ortho_up: Vector3 = d.cross(right).normalized()
	global_transform = Transform3D(Basis(right, ortho_up, d), origin)
	if _cone_mat:
		_cone_mat.set_shader_parameter(&"length_m", reach_m)
	if _particles:
		_particles.emitting = on and Fx.enabled
		_particles.direction = Vector3(0.0, 0.04, 1.0).normalized()
		var spd: float = clampf(reach_m * 1.75, 4.0, 14.0)
		_particles.initial_velocity_min = spd * 0.72
		_particles.initial_velocity_max = spd * 1.08
	if _light:
		_light.position = Vector3(0.0, 0.15, minf(reach_m * 0.45, 2.6))


func step(delta: float) -> void:
	_now += delta
	var target: float = 1.0 if active else 0.0
	var rate: float = 11.0 if active else 7.5
	intensity = move_toward(intensity, target, delta * rate)
	var show_jet: bool = Fx.enabled and intensity > 0.02
	if _cone:
		_cone.visible = show_jet
		if show_jet:
			_cone_mat.set_shader_parameter(&"now", _now)
			_cone_mat.set_shader_parameter(&"intensity", intensity)
	if _light:
		_light.visible = show_jet
		if show_jet:
			var flicker: float = 0.84 + 0.16 * sin(_now * 41.0 + _seed) + 0.08 * sin(_now * 67.0)
			_light.light_energy = 2.6 * intensity * flicker
	if _particles and not active and _particles.emitting:
		_particles.emitting = false


func _build_cone() -> void:
	if _cone_mesh == null:
		_cone_mesh = _make_tube_mesh(12, 14)
	_cone_mat = ShaderMaterial.new()
	_cone_mat.shader = JET_SHADER
	_cone_mat.set_shader_parameter(&"seed", _seed)
	_cone_mat.set_shader_parameter(&"intensity", 0.0)
	_cone_mat.set_shader_parameter(&"length_m", reach_m)
	_cone = MeshInstance3D.new()
	_cone.name = "FlameCone"
	_cone.mesh = _cone_mesh
	_cone.material_override = _cone_mat
	_cone.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_cone.custom_aabb = AABB(Vector3(-2.0, -2.0, -0.5), Vector3(4.0, 4.0, 11.0))
	_cone.visible = false
	add_child(_cone)


func _build_particles() -> void:
	if _spark_tex == null:
		var sz: int = 32
		var img: Image = Image.create_empty(sz, sz, false, Image.FORMAT_RGBA8)
		var c: float = (sz - 1) * 0.5
		for y: int in sz:
			for x: int in sz:
				var r: float = Vector2(x - c, y - c).length() / c
				img.set_pixel(x, y, Color(1.0, 1.0, 1.0, pow(clampf(1.0 - r, 0.0, 1.0), 1.6)))
		_spark_tex = ImageTexture.create_from_image(img)
		_spark_ramp = Gradient.new()
		_spark_ramp.set_color(0, Color(1.0, 0.92, 0.55, 0.95))
		_spark_ramp.add_point(0.32, Color(1.0, 0.48, 0.08, 0.85))
		_spark_ramp.add_point(0.72, Color(0.85, 0.14, 0.02, 0.5))
		_spark_ramp.set_color(_spark_ramp.get_point_count() - 1, Color(0.25, 0.04, 0.01, 0.0))
		_spark_curve = Curve.new()
		_spark_curve.add_point(Vector2(0.0, 0.35))
		_spark_curve.add_point(Vector2(0.35, 1.0))
		_spark_curve.add_point(Vector2(1.0, 0.15))
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.vertex_color_use_as_albedo = true
	mat.albedo_color = Color(1.4, 0.72, 0.22)
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.billboard_keep_scale = true
	mat.albedo_texture = _spark_tex
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2.ONE
	_particles = CPUParticles3D.new()
	_particles.name = "FlameTrail"
	_particles.emitting = false
	_particles.amount = 34
	_particles.lifetime = 0.52
	_particles.local_coords = false
	_particles.mesh = q
	_particles.material_override = mat
	_particles.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_particles.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	_particles.emission_sphere_radius = 0.05
	_particles.direction = Vector3(0.0, 0.05, 1.0)
	_particles.spread = 12.0
	_particles.gravity = Vector3(0.0, 2.8, 0.0)
	_particles.damping_min = 3.2
	_particles.damping_max = 6.0
	_particles.initial_velocity_min = 8.5
	_particles.initial_velocity_max = 12.5
	_particles.scale_amount_min = 0.22
	_particles.scale_amount_max = 0.52
	_particles.scale_amount_curve = _spark_curve
	_particles.color_ramp = _spark_ramp
	add_child(_particles)


func _build_light() -> void:
	_light = OmniLight3D.new()
	_light.name = "FlameLight"
	_light.light_color = Color(1.0, 0.54, 0.14)
	_light.light_energy = 0.0
	_light.omni_range = 7.5
	_light.shadow_enabled = false
	_light.visible = false
	add_child(_light)


## Unit cylinder along +Z (z in 0..1, radius 1 in XY), subdivided for smooth vertex noise.
static func _make_tube_mesh(radial: int, rings: int) -> ArrayMesh:
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for r: int in rings:
		var z0: float = float(r) / float(rings)
		var z1: float = float(r + 1) / float(rings)
		for s: int in radial:
			var a0: float = TAU * float(s) / float(radial)
			var a1: float = TAU * float(s + 1) / float(radial)
			var n0: Vector3 = Vector3(cos(a0), sin(a0), 0.0)
			var n1: Vector3 = Vector3(cos(a1), sin(a1), 0.0)
			var p00: Vector3 = Vector3(n0.x, n0.y, z0)
			var p10: Vector3 = Vector3(n1.x, n1.y, z0)
			var p01: Vector3 = Vector3(n0.x, n0.y, z1)
			var p11: Vector3 = Vector3(n1.x, n1.y, z1)
			st.set_normal(n0); st.add_vertex(p00)
			st.set_normal(n1); st.add_vertex(p10)
			st.set_normal(n1); st.add_vertex(p11)
			st.set_normal(n0); st.add_vertex(p00)
			st.set_normal(n1); st.add_vertex(p11)
			st.set_normal(n0); st.add_vertex(p01)
	return st.commit()
