class_name PlasmaCharge
extends Node3D
## The charge gathering at a plasma gun's emitter (the SL-9 Slagger,
## docs/design.md §4.9): a ball of angry red-orange plasma, white at the
## core, held by a magnetic field drawn as broken bands crawling round it.
## It grows with the charge, the field strains and breaks up as the charge
## goes past full toward an overload, sparks spit off it and it lights the
## hands. PlayerWeapon parents one to the gun's rig at the muzzle point and
## calls `set_state()` every frame.

const BALL_MIN: float = 0.004
const RINGS: int = 3

var data: PlasmaData
var ball: MeshInstance3D
var ball_mat: ShaderMaterial
var rings: Array[MeshInstance3D] = []
var ring_mat: ShaderMaterial
var light: OmniLight3D
var sparks: CPUParticles3D
var charge: float = 0.0
var strain: float = 0.0
var _t: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()

static var _noise: Texture2D


static func noise() -> Texture2D:
	if _noise == null:
		_noise = NightAtmosphere._noise_texture(0.035, false, 909)
	return _noise


static func ball_material(pd: PlasmaData) -> ShaderMaterial:
	var m: ShaderMaterial = ShaderMaterial.new()
	m.shader = preload("res://src/vfx/plasma.gdshader")
	m.set_shader_parameter(&"noise_tex", noise())
	m.set_shader_parameter(&"core_color", pd.core_color)
	m.set_shader_parameter(&"hot_color", pd.hot_color)
	return m


func _ready() -> void:
	_rng.randomize()
	ball = MeshInstance3D.new()
	var sm: SphereMesh = SphereMesh.new()
	sm.radius = 1.0
	sm.height = 2.0
	sm.radial_segments = 20
	sm.rings = 10
	ball.mesh = sm
	ball_mat = ball_material(data)
	ball.material_override = ball_mat
	ball.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ball)
	ring_mat = ShaderMaterial.new()
	ring_mat.shader = preload("res://src/vfx/plasma_field.gdshader")
	ring_mat.set_shader_parameter(&"noise_tex", noise())
	ring_mat.set_shader_parameter(&"field_color", data.field_color)
	for i: int in RINGS:
		var r: MeshInstance3D = MeshInstance3D.new()
		var tm: TorusMesh = TorusMesh.new()
		tm.inner_radius = 0.94
		tm.outer_radius = 1.0
		tm.rings = 24
		tm.ring_segments = 4
		r.mesh = tm
		r.material_override = ring_mat
		r.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		r.rotation = Vector3(_rng.randf() * TAU, _rng.randf() * TAU, 0.0)
		add_child(r)
		rings.append(r)
	light = OmniLight3D.new()
	light.light_color = data.hot_color
	light.omni_range = data.light_range
	light.omni_attenuation = 1.6
	light.shadow_enabled = false
	light.light_energy = 0.0
	add_child(light)
	sparks = CPUParticles3D.new()
	sparks.amount = 24
	sparks.lifetime = 0.35
	sparks.local_coords = false
	sparks.emitting = false
	sparks.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE_SURFACE
	sparks.emission_sphere_radius = 0.02
	sparks.direction = Vector3(1, 0, 0)
	sparks.spread = 180.0
	sparks.initial_velocity_min = 0.4
	sparks.initial_velocity_max = 1.6
	sparks.gravity = Vector3(0, -2.0, 0)
	sparks.scale_amount_min = 0.004
	sparks.scale_amount_max = 0.009
	var qm: QuadMesh = QuadMesh.new()
	qm.size = Vector2(1, 1)
	var sp_mat: StandardMaterial3D = StandardMaterial3D.new()
	sp_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sp_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	sp_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	sp_mat.albedo_color = Color(1.0, 0.6, 0.2) * 3.0
	qm.material = sp_mat
	sparks.mesh = qm
	add_child(sparks)
	_apply()


## `c`: charge 0..1; `s`: strain 0..1 past full (toward an overload).
func set_state(c: float, s: float, delta: float) -> void:
	charge = c
	strain = s
	_t += delta
	_apply()


func _apply() -> void:
	var on: bool = charge > 0.002
	visible = on
	sparks.emitting = on and charge > 0.25
	if not on:
		light.light_energy = 0.0
		return
	# It swells as it fills, and shivers: harder near full and past it.
	var flick: float = 0.85 + 0.15 * sin(_t * 47.0) * sin(_t * 31.0) + _rng.randf_range(-0.1, 0.1) * (0.4 + strain)
	var r: float = lerpf(BALL_MIN, data.radius_full * 0.85, sqrt(charge)) * (1.0 + 0.08 * flick * charge + strain * 0.12 * _rng.randf())
	ball.scale = Vector3.ONE * r
	ball_mat.set_shader_parameter(&"intensity", lerpf(1.6, 4.5, charge))
	ball_mat.set_shader_parameter(&"heat", clampf(charge * 0.9 + strain * 0.3, 0.0, 1.0))
	ball_mat.set_shader_parameter(&"churn", 1.0 + 2.5 * charge + 3.0 * strain)
	ball_mat.set_shader_parameter(&"flicker", flick)
	ring_mat.set_shader_parameter(&"strain", strain)
	ring_mat.set_shader_parameter(&"intensity", lerpf(0.4, 2.2, charge) * (1.0 + strain))
	ring_mat.set_shader_parameter(&"speed", 1.0 + 3.0 * charge + 4.0 * strain)
	for i: int in rings.size():
		var ring: MeshInstance3D = rings[i]
		ring.visible = charge > 0.08
		var spin: float = (1.8 + i * 0.9) * (1.0 + 2.0 * charge)
		ring.rotate_object_local(Vector3.UP if i % 2 == 0 else Vector3.RIGHT, spin * 0.016 * (1.0 + strain))
		ring.rotate_object_local(Vector3.FORWARD, 0.011 * (i + 1))
		var wob: float = 1.0 + strain * 0.2 * sin(_t * (23.0 + i * 7.0))
		ring.scale = Vector3.ONE * r * (1.35 + 0.12 * i) * wob
	light.light_energy = data.light_energy * charge * flick * (1.0 + strain * 0.5)
	light.omni_range = lerpf(1.0, data.light_range, charge)
	sparks.emission_sphere_radius = r
	sparks.speed_scale = 0.8 + 1.5 * charge + 2.0 * strain
