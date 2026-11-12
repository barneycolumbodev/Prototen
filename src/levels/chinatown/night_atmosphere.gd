class_name NightAtmosphere
extends Node3D
## Everything that makes the map feel like a wet harbour night: sky, fog,
## bloom, the moon (characters only), harbour water with light streaks from
## the quay, a distant lit skyline across the bay, rain that stops under
## roofs, steam from drains and kitchen vents, reflection probes for the
## wet streets, and ambient sound emitters from layout.json.

var config: NightAtmosphereConfig
var map: ChinatownMap
var env: Environment
var rain: GPUParticles3D
var roof_tex: ImageTexture
## Roof map: highest solid surface above head height per 1 m cell (Godot x/z).
var roof_origin: Vector2 = Vector2(-60, -50)
var roof_size: Vector2i = Vector2i(120, 110)
var water: MeshInstance3D
var water_material: ShaderMaterial
var probe_nodes: Array[ReflectionProbe] = []
var steam: Array[GPUParticles3D] = []
var _follow: Node3D

const SKY_TEXTURE: String = "res://assets/env/sky/harbour_night.png"
## Switches for the per-feature cost benchmark (FeatureSweep) and quality settings.
const FEATURES: Array[StringName] = [&"probes", &"glow", &"water_streaks", &"ripples", &"rain", &"steam", &"fog"]


func _ready() -> void:
	_build_environment()
	_build_moon()
	_build_water()
	_build_skyline()
	_build_probes()
	_build_roof_map.call_deferred()
	_build_steam()
	_build_sounds()
	var wm: ShaderMaterial = map.world_material
	wm.set_shader_parameter(&"lm_gain", config.lightmap_gain)
	wm.set_shader_parameter(&"emission_gain", config.emission_gain)
	wm.set_shader_parameter(&"rain", config.rain_wetness)
	wm.set_shader_parameter(&"puddles", config.puddles)


func follow(n: Node3D) -> void:
	_follow = n
	var p: Player = n as Player
	if p and config.viewmodel_fill_energy > 0.0:
		var fill: OmniLight3D = OmniLight3D.new()
		fill.name = "ViewmodelFill"
		fill.light_color = config.viewmodel_fill_color
		fill.light_energy = config.viewmodel_fill_energy
		fill.omni_range = 1.4
		fill.omni_attenuation = 1.5
		fill.light_specular = 0.4
		fill.shadow_enabled = false
		fill.light_cull_mask = 0xFFFFF & ~ChinatownMap.MAP_LAYER
		p.camera().add_child(fill)
		fill.position = Vector3(-0.35, 0.25, 0.15)


func _process(_delta: float) -> void:
	if _follow and rain:
		var p: Vector3 = _follow.global_position
		rain.global_position = Vector3(p.x, p.y + 9.0, p.z)


# ------------------------------------------------------------------ sky, fog, glow

func _build_environment() -> void:
	env = Environment.new()
	# A pre-rendered panorama (raw_assets/env/sky/build_night_sky.py): the
	# old procedural sky used TIME, so the phone rebuilt its radiance every
	# frame (playtest 2026-11-05). Now radiance is computed once.
	var sky_mat: PanoramaSkyMaterial = PanoramaSkyMaterial.new()
	sky_mat.panorama = load(SKY_TEXTURE) as Texture2D
	sky_mat.energy_multiplier = config.sky_energy
	sky_mat.filter = true
	var sky: Sky = Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	sky.process_mode = Sky.PROCESS_MODE_QUALITY
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = config.ambient_color
	env.ambient_light_energy = config.ambient_energy
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = config.exposure
	env.glow_enabled = true
	env.glow_intensity = config.glow_intensity
	env.glow_bloom = config.glow_bloom
	env.glow_hdr_threshold = config.glow_threshold
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	# Level 1 is the half-resolution pass, the costly one on Mali; the wider
	# levels carry the neon bloom (playtest 2026-11-05).
	env.set_glow_level(0, 0.0)
	env.set_glow_level(1, 0.0)
	env.set_glow_level(2, 1.0)
	env.set_glow_level(3, 0.8)
	env.set_glow_level(4, 0.5)
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = config.fog_color
	env.fog_density = config.fog_density
	env.fog_sky_affect = config.fog_sky_affect
	env.fog_height = config.fog_height
	env.fog_height_density = config.fog_height_density
	env.adjustment_enabled = true
	env.adjustment_saturation = config.saturation
	env.adjustment_contrast = config.contrast
	if "--nofog" in OS.get_cmdline_user_args():
		env.fog_enabled = false
	env.glow_enabled = Settings.bloom and not ("--noglow" in OS.get_cmdline_user_args())
	if "--glow" in OS.get_cmdline_user_args():
		env.glow_enabled = true
	Settings.changed.connect(_on_settings_changed)
	var we: WorldEnvironment = WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _on_settings_changed() -> void:
	# The cost sweep switches glow itself; otherwise the setting rules.
	if env:
		env.glow_enabled = Settings.bloom


func _moon_dir() -> Vector3:
	var b: Basis = Basis.from_euler(Vector3(deg_to_rad(config.moon_dir_deg.x), deg_to_rad(config.moon_dir_deg.y), 0))
	return -b.z


func _build_moon() -> void:
	var moon: DirectionalLight3D = DirectionalLight3D.new()
	moon.name = "Moon"
	moon.rotation_degrees = Vector3(config.moon_dir_deg.x, config.moon_dir_deg.y, 0)
	moon.light_color = config.moon_color
	moon.light_energy = config.moon_energy
	moon.light_cull_mask = 0xFFFFF & ~ChinatownMap.MAP_LAYER
	moon.shadow_enabled = false
	moon.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	add_child(moon)


# ------------------------------------------------------------------ water and skyline

func _build_water() -> void:
	var wz: float = ChinatownMap.fnum(map.layout, "water_z", -2.1)
	var plane: PlaneMesh = PlaneMesh.new()
	plane.size = Vector2(1400, 700)
	plane.subdivide_width = 0
	plane.subdivide_depth = 0
	water = MeshInstance3D.new()
	water.name = "Water"
	water.mesh = plane
	water.position = Vector3(0, wz, 24.0 + 350.0 - 2.0)
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = preload("res://src/levels/chinatown/water.gdshader")
	mat.set_shader_parameter(&"deep", config.water_color)
	mat.set_shader_parameter(&"reflect", config.water_reflect)
	# The brightest lights on the waterfront make streaks on the water.
	var lights: Array[Vector4] = []
	var cols: Array[Vector4] = []
	for m: Dictionary in map.layout["markers"]:
		if ChinatownMap.fstr(m, "kind") != "light":
			continue
		var p: Vector3 = ChinatownMap.fpos(m)
		var watts: float = ChinatownMap.fnum(m, "energy")
		if p.z < 8.0 or watts < 9.0:
			continue
		var c: Color = ChinatownMap.fcolor(m)
		lights.append(Vector4(p.x, p.y, p.z, 0.0))
		cols.append(Vector4(c.r, c.g, c.b, clampf(watts / 120.0, 0.25, 1.6)))
	lights.sort_custom(func(a: Vector4, b: Vector4) -> bool: return a.z > b.z)
	var n: int = mini(lights.size(), 12)
	var lp: PackedVector4Array = PackedVector4Array()
	var lc: PackedVector4Array = PackedVector4Array()
	# Keep the ones nearest the water (largest z), but spread along the quay.
	for i: int in n:
		lp.append(lights[i])
		lc.append(cols[i])
	mat.set_shader_parameter(&"light_pos", lp)
	mat.set_shader_parameter(&"light_col", lc)
	mat.set_shader_parameter(&"light_count", n)
	mat.set_shader_parameter(&"wave_normal", _noise_texture(0.035, true, 11))
	mat.set_shader_parameter(&"shimmer_tex", _noise_texture(0.05, false, 12))
	water.material_override = mat
	water_material = mat
	add_child(water)


static func _noise_texture(freq: float, normal_map: bool, seed_: int) -> NoiseTexture2D:
	var fn: FastNoiseLite = FastNoiseLite.new()
	fn.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	fn.frequency = freq
	fn.seed = seed_
	fn.fractal_octaves = 3
	var t: NoiseTexture2D = NoiseTexture2D.new()
	t.width = 256
	t.height = 256
	t.seamless = true
	t.noise = fn
	t.as_normal_map = normal_map
	t.bump_strength = 6.0
	t.generate_mipmaps = true
	return t


## Turns one atmosphere feature on or off (see FEATURES).
func set_feature(feature: StringName, on: bool) -> void:
	match feature:
		&"probes":
			for rp: ReflectionProbe in probe_nodes:
				rp.visible = on
		&"glow":
			env.glow_enabled = on
		&"water_streaks":
			water_material.set_shader_parameter(&"streaks", 1.0 if on else 0.0)
		&"ripples":
			map.world_material.set_shader_parameter(&"ripple_amount", 1.0 if on else 0.0)
		&"rain":
			if rain:
				rain.visible = on
				rain.emitting = on
		&"steam":
			for s: GPUParticles3D in steam:
				s.visible = on
				s.emitting = on
		&"fog":
			env.fog_enabled = on


func _build_skyline() -> void:
	# A far shore across the bay: towers with lit windows, cranes, a ridge of hills.
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 1997
	var x: float = -520.0
	while x < 520.0:
		var w: float = rng.randf_range(14.0, 42.0)
		var h: float = rng.randf_range(18.0, 70.0) * (1.6 if absf(x) < 160.0 and rng.randf() < 0.35 else 1.0)
		var d: float = rng.randf_range(12.0, 30.0)
		var z: float = rng.randf_range(330.0, 420.0)
		_box(st, Vector3(x + w * 0.5, -2.0 + h * 0.5, z), Vector3(w, h, d))
		x += w + rng.randf_range(2.0, 18.0)
	st.generate_normals()
	var mesh: ArrayMesh = st.commit()
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.name = "Skyline"
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = preload("res://src/levels/chinatown/skyline.gdshader")
	mi.material_override = mat
	add_child(mi)


static func _box(st: SurfaceTool, c: Vector3, s: Vector3) -> void:
	var h: Vector3 = s * 0.5
	var corners: Array[Vector3] = []
	for i: int in 8:
		corners.append(c + Vector3(h.x * (1 if i & 1 else -1), h.y * (1 if i & 2 else -1), h.z * (1 if i & 4 else -1)))
	var faces: Array = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
	for f: Array in faces:
		var a: Vector3 = corners[f[0]]
		var b: Vector3 = corners[f[1]]
		var cc: Vector3 = corners[f[2]]
		var d: Vector3 = corners[f[3]]
		for v: Vector3 in [a, cc, b, a, d, cc]:
			st.set_uv(Vector2(v.x + v.z, v.y))
			st.add_vertex(v)


# ------------------------------------------------------------------ reflections

func _build_probes() -> void:
	# [centre, size] in Godot coordinates; box-projected, rendered once.
	var probes: Array = [
		[Vector3(-22, 4, -7), Vector3(50, 10, 12)], [Vector3(24, 4, -7), Vector3(46, 10, 12)],
		[Vector3(0, 3.5, 6), Vector3(32, 8, 15)], [Vector3(0, 3, 19), Vector3(94, 8, 10)],
		[Vector3(-33, 4, 6), Vector3(26, 9, 16)], [Vector3(34, 4, 6), Vector3(24, 9, 16)],
		[Vector3(0, 4, -25), Vector3(60, 9, 6)], [Vector3(-18, 2.2, -17), Vector3(12, 4.4, 10)],
		[Vector3(-33, 4, -6), Vector3(26, 8, 16)],
	]
	for p: Array in probes:
		var rp: ReflectionProbe = ReflectionProbe.new()
		rp.update_mode = ReflectionProbe.UPDATE_ONCE
		rp.box_projection = true
		rp.size = p[1]
		rp.max_distance = 120.0
		rp.intensity = 1.0
		rp.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
		rp.cull_mask = ChinatownMap.MAP_LAYER
		add_child(rp)
		probe_nodes.append(rp)
		rp.global_position = p[0]


# ------------------------------------------------------------------ rain (stops under roofs)

func _build_roof_map() -> void:
	var img: Image = Image.create(roof_size.x, roof_size.y, false, Image.FORMAT_RF)
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	for j: int in roof_size.y:
		for i: int in roof_size.x:
			var x: float = roof_origin.x + i + 0.5
			var z: float = roof_origin.y + j + 0.5
			var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(Vector3(x, 40.0, z), Vector3(x, 2.2, z), Ballistics.LAYER_WORLD)
			var hit: Dictionary = space.intersect_ray(q)
			var h: float = -50.0
			if not hit.is_empty():
				var hp: Vector3 = hit["position"]
				h = hp.y
			img.set_pixel(i, j, Color(h, 0, 0))
	roof_tex = ImageTexture.create_from_image(img)
	_build_rain()


func roof_height(p: Vector3) -> float:
	if roof_tex == null:
		return -50.0
	var i: int = int(p.x - roof_origin.x)
	var j: int = int(p.z - roof_origin.y)
	if i < 0 or j < 0 or i >= roof_size.x or j >= roof_size.y:
		return -50.0
	return roof_tex.get_image().get_pixel(i, j).r


func _build_rain() -> void:
	rain = GPUParticles3D.new()
	rain.name = "Rain"
	rain.amount = config.rain_amount
	rain.lifetime = 2.2
	rain.preprocess = 2.0
	rain.visibility_aabb = AABB(Vector3(-20, -24, -20), Vector3(40, 30, 40))
	rain.local_coords = false
	var pm: ParticleProcessMaterial = ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(18, 1, 18)
	pm.direction = Vector3(config.rain_wind.x, -config.rain_speed, config.rain_wind.y).normalized()
	pm.spread = 2.0
	pm.initial_velocity_min = config.rain_speed * 0.9
	pm.initial_velocity_max = config.rain_speed * 1.1
	pm.gravity = Vector3.ZERO
	rain.process_material = pm
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2(0.012, 0.55)
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = preload("res://src/levels/chinatown/rain.gdshader")
	mat.set_shader_parameter(&"color", config.rain_color)
	mat.set_shader_parameter(&"roof_map", roof_tex)
	mat.set_shader_parameter(&"roof_origin", roof_origin)
	mat.set_shader_parameter(&"roof_size", Vector2(roof_size))
	quad.material = mat
	rain.draw_pass_1 = quad
	rain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(rain)
	if _follow:
		rain.global_position = _follow.global_position + Vector3.UP * 9.0


# ------------------------------------------------------------------ steam and sound

func _build_steam() -> void:
	var shader: Shader = preload("res://src/levels/chinatown/steam.gdshader")
	for m: Dictionary in map.layout["markers"]:
		if ChinatownMap.fstr(m, "kind") != "steam":
			continue
		var p: GPUParticles3D = GPUParticles3D.new()
		p.amount = 10
		p.lifetime = 4.0
		p.preprocess = 4.0
		var pm: ParticleProcessMaterial = ParticleProcessMaterial.new()
		pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
		pm.emission_sphere_radius = 0.25
		pm.direction = Vector3.UP
		pm.spread = 12.0
		pm.initial_velocity_min = 0.35
		pm.initial_velocity_max = 0.7
		pm.gravity = Vector3(0.12, 0.05, -0.05)
		pm.scale_min = 0.8
		pm.scale_max = 1.4
		var curve: CurveTexture = CurveTexture.new()
		var cv: Curve = Curve.new()
		cv.add_point(Vector2(0, 0.4))
		cv.add_point(Vector2(1, 2.4))
		curve.curve = cv
		pm.scale_curve = curve
		p.process_material = pm
		var q: QuadMesh = QuadMesh.new()
		q.size = Vector2(1.0, 1.0)
		var mat: ShaderMaterial = ShaderMaterial.new()
		mat.shader = shader
		q.material = mat
		p.draw_pass_1 = q
		p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(p)
		p.global_position = ChinatownMap.fpos(m)
		steam.append(p)


func _build_sounds() -> void:
	for m: Dictionary in map.layout["markers"]:
		if ChinatownMap.fstr(m, "kind") != "audio":
			continue
		var path: String = "res://assets/audio/sfx/amb_%s.wav" % ChinatownMap.fstr(m, "sound")
		if not ResourceLoader.exists(path):
			continue
		var a: AudioStreamPlayer3D = AudioStreamPlayer3D.new()
		a.stream = load(path)
		a.volume_db = ChinatownMap.fnum(m, "volume", -8.0)
		a.unit_size = 4.0
		a.max_distance = 40.0
		a.autoplay = true
		add_child(a)
		a.global_position = ChinatownMap.fpos(m)
	var beds: Dictionary[String, float] = {"rain": -9.0, "harbour": -12.0}
	for bed: String in beds:
		var path2: String = "res://assets/audio/sfx/amb_%s.wav" % bed
		if ResourceLoader.exists(path2):
			var s: AudioStreamPlayer = AudioStreamPlayer.new()
			s.stream = load(path2)
			s.volume_db = beds[bed]
			s.autoplay = true
			add_child(s)
