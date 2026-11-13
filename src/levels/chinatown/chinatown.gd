class_name ChinatownMap
extends Node3D
## Chinatown docks at night (owner, 2026-11-04): a city block on the harbour
## with a fish market, a restaurant, shophouses, a back alley, the quay, a
## pier and a moored fishing boat. Built by raw_assets/levels/chinatown/
## (build.py → bake.py): the meshes and baked lightmap come from the glTF,
## everything else (colliders, spawn points, character lights, steam, sounds,
## cameras) from layout.json.
##
## Enemies arrive on a rolling clock (RollingSpawner, data/levels/
## chinatown_spawns.tres): 8 at the start, 3 more whenever fewer than 4 are
## still fighting, always out of sight.
##
## Layout coordinates are Blender's (x east, y north, z up); Godot's are
## (x, z, -y). See `b2g`.

const LAYOUT_PATH: String = "res://assets/levels/chinatown/layout.json"
const MAP_SCENE: String = "res://assets/levels/chinatown/chinatown.gltf"
const LIGHTMAP: String = "res://assets/levels/chinatown/lightmap.png"
const SPAWN_CONFIG: String = "res://data/levels/chinatown_spawns.tres"
const ATMOS_CONFIG: String = "res://data/levels/chinatown_night.tres"
const PLAYER_SCENE: PackedScene = preload("res://src/player/player.tscn")
## Visual layer of the static map. Character lights and the moon skip it
## (its lighting is baked).
const MAP_LAYER: int = 2
const WORLD_PRIORITY: int = 2
## Physics layer for invisible walls: they stop people, not bullets.
const LAYER_CLIP: int = Ballistics.LAYER_CLIP
const DETAIL_RANGE: float = 42.0

var layout: Dictionary = {}
var player: Player
var wave_mode: RollingSpawner
var combat_hud: CombatHud
var atmos: NightAtmosphere
var spawn_points: Array[Vector3] = []
var nav_region: NavigationRegion3D
var world_material: ShaderMaterial
var glass_material: ShaderMaterial
var player_start: Vector3 = Vector3.ZERO
var player_yaw: float = 0.0
var static_bodies: Dictionary[String, StaticBody3D] = {}
var map_root: Node3D
## Start the rolling spawns on load (tests turn this off and start them by hand).
var autostart_spawns: bool = true

var sweep: FeatureSweep
var _bench: FrameBench
var _hud: Node
var _bench_yaw0: float = 0.0
var _quit_after_bench: bool = false


static func b2g(v: Array) -> Vector3:
	var x: float = v[0]
	var y: float = v[1]
	var z: float = v[2]
	return Vector3(x, z, -y)


## Typed reads from the layout JSON (numbers arrive as float).
static func fnum(d: Dictionary, key: String, def: float = 0.0) -> float:
	var v: float = d.get(key, def)
	return v


static func fstr(d: Dictionary, key: String) -> String:
	var v: String = d.get(key, "")
	return v


static func fbool(d: Dictionary, key: String) -> bool:
	var v: bool = d.get(key, false)
	return v


static func fpos(d: Dictionary, key: String = "p") -> Vector3:
	var a: Array = d[key]
	return b2g(a)


static func fcolor(d: Dictionary, key: String = "color") -> Color:
	var a: Array = d[key]
	var r: float = a[0]
	var g: float = a[1]
	var b: float = a[2]
	return Color(r, g, b)


func _ready() -> void:
	layout = load_layout()
	_build_map_meshes()
	_build_colliders()
	_build_occluders()
	_build_markers()
	atmos = NightAtmosphere.new()
	atmos.name = "Atmosphere"
	atmos.config = load(ATMOS_CONFIG) as NightAtmosphereConfig
	atmos.map = self
	add_child(atmos)
	Sfx.set_room(0.25)
	player = PLAYER_SCENE.instantiate() as Player
	add_child(player)
	player.global_position = player_start
	player.spawn_point = player_start
	player.set_view(player_yaw, 0.0)
	player.aim_assist = AimAssist.new(load("res://data/input/aim_assist.tres") as AimAssistConfig)
	if not CaptureDirector.is_capturing():
		TuningMenu.load_saved_all(player.weapon(), player.aim_assist.config)
		player.weapon().apply_tuning.call_deferred()
	atmos.follow(player)
	_bench = FrameBench.new()
	add_child(_bench)
	_bench.finished.connect(_on_bench_finished)
	sweep = FeatureSweep.new()
	sweep.name = "FeatureSweep"
	sweep.atmos = atmos
	sweep.bench = _bench
	sweep.spawn_men = _sweep_men
	for c: Node in player.camera().get_children():
		if c is Node3D:
			sweep.viewmodel.append(c as Node3D)
	add_child(sweep)
	sweep.finished.connect(_on_sweep_finished)
	_hud = preload("res://src/ui/hud.gd").new()
	_hud.set("bench", _bench)
	_hud.set("weapon", player.weapon())
	add_child(_hud)
	combat_hud = CombatHud.new()
	combat_hud.player = player
	add_child(combat_hud)
	wave_mode = RollingSpawner.new()
	wave_mode.name = "WaveMode"
	wave_mode.config = load(SPAWN_CONFIG) as RollingSpawnConfig
	wave_mode.level = self
	wave_mode.player = player
	wave_mode.spawn_points = spawn_points
	# Cover: the whole ground level, and the gallery on the east tenement.
	wave_mode.cover_regions = [[Vector3(0, 0, 5), 47.0], [Vector3(35, 3.95, 14.1), 11.0]]
	add_child(wave_mode)
	EventBus.wave_mode_requested.connect(wave_mode.toggle)
	EventBus.benchmark_requested.connect(start_benchmark)
	EventBus.feature_sweep_requested.connect(start_feature_sweep)
	_build_navigation()
	var spawns_on: bool = autostart_spawns and not CaptureDirector.is_capturing()
	for arg: String in OS.get_cmdline_user_args():
		if arg == "--waves":
			spawns_on = true
		if arg == "--nospawn":
			spawns_on = false
		if arg.begins_with("--debug-view="):
			world_material.set_shader_parameter(&"debug_view", arg.trim_prefix("--debug-view=").to_int())
		if arg == "--god":
			player.invulnerable = true
		if arg == "--no-lod":
			get_viewport().mesh_lod_threshold = 0.0  # capture A/B: every mesh at full detail
		if arg == "--line-up":
			_line_up.call_deferred()
		if arg == "--sweep":
			_quit_after_bench = true
			spawns_on = false
			start_feature_sweep.call_deferred()
		if arg.begins_with("--perf="):
			var probe: PerfProbe = PerfProbe.new()
			probe.seconds = arg.trim_prefix("--perf=").to_float()
			probe.player = player
			for a2: String in OS.get_cmdline_user_args():
				if a2.begins_with("--perf-exp="):
					probe.experiment = a2.trim_prefix("--perf-exp=")
				if a2 == "--perf-calm":
					probe.calm = true
				if a2 == "--perf-spin":
					probe.spin = true
			player.invulnerable = true
			spawns_on = true
			add_child(probe)
		if arg.begins_with("--bench="):
			_quit_after_bench = true
			spawns_on = false
			start_benchmark.call_deferred(arg.trim_prefix("--bench=").to_float())
	if spawns_on:
		_start_spawns.call_deferred()


## Capture aid (--line-up): three passive triad men down the street ahead of
## the player start, at 9, 17 and 28 m, to judge size and readability.
func _line_up() -> void:
	await get_tree().physics_frame
	var fwd: Vector3 = -player.global_basis.z
	var right: Vector3 = player.global_basis.x
	var roles: Array[String] = ["gunman", "red_pole", "enforcer"]
	var dists: Array[float] = [9.0, 17.0, 28.0]
	for i: int in 3:
		var e: Enemy = Enemy.new()
		e.config = load("res://data/enemies/%s.tres" % roles[i]) as EnemyConfig
		e.passive = true
		e.look_seed = 1000 + i  # the same men every capture (A/B shots)
		add_child(e)
		e.global_position = player.global_position + fwd * dists[i] + right * (1.6 * (i - 1))
		var to: Vector3 = player.global_position - e.global_position
		e.face(atan2(to.x, to.z))


func _start_spawns() -> void:
	# Physics needs a frame to register the colliders before cover sampling.
	await get_tree().physics_frame
	await get_tree().physics_frame
	wave_mode.start()


static func load_layout() -> Dictionary:
	var f: FileAccess = FileAccess.open(LAYOUT_PATH, FileAccess.READ)
	var d: Dictionary = JSON.parse_string(f.get_as_text())
	return d


# ------------------------------------------------------------------ meshes

func _build_map_meshes() -> void:
	world_material = ShaderMaterial.new()
	world_material.shader = preload("res://src/levels/chinatown/world.gdshader")
	# Drawn after the first-person view (0) and the men (EnemyBody.RENDER_PRIORITY):
	# the Mobile renderer draws lower priorities first (optimization overhaul R-01).
	world_material.render_priority = WORLD_PRIORITY
	world_material.set_shader_parameter(&"albedo_arr", load("res://assets/env/world/world_albedo.webp"))
	world_material.set_shader_parameter(&"normal_arr", load("res://assets/env/world/world_normal.webp"))
	world_material.set_shader_parameter(&"orm_arr", load("res://assets/env/world/world_orm.webp"))
	if ResourceLoader.exists(LIGHTMAP):
		world_material.set_shader_parameter(&"lightmap", load(LIGHTMAP))
	world_material.set_shader_parameter(&"noise_tex", NightAtmosphere._noise_texture(0.06, false, 7))
	world_material.set_shader_parameter(&"hash_tex", hash_texture())
	glass_material = ShaderMaterial.new()
	glass_material.shader = preload("res://src/levels/chinatown/glass.gdshader")
	glass_material.set_shader_parameter(&"albedo_arr", load("res://assets/env/world/world_albedo.webp"))
	glass_material.set_shader_parameter(&"orm_arr", load("res://assets/env/world/world_orm.webp"))
	glass_material.render_priority = 1
	var scene: PackedScene = load(MAP_SCENE) as PackedScene
	map_root = scene.instantiate() as Node3D
	map_root.name = "Map"
	add_child(map_root)
	for n: Node in map_root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		mi.layers = MAP_LAYER
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var nm: String = String(mi.name)
		if nm.ends_with("glass"):
			mi.material_override = glass_material
		else:
			mi.material_override = world_material
		if nm.ends_with("detail"):
			mi.visibility_range_end = DETAIL_RANGE
			mi.visibility_range_end_margin = 4.0
			mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED


## 64×64 white noise, one random per channel per texel (the world shader's
## per-cell randoms for rain ripples).
static func hash_texture() -> ImageTexture:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 4417
	var bytes: PackedByteArray = PackedByteArray()
	bytes.resize(64 * 64 * 4)
	for i: int in bytes.size():
		bytes[i] = rng.randi() % 256
	return ImageTexture.create_from_image(Image.create_from_data(64, 64, false, Image.FORMAT_RGBA8, bytes))


# ------------------------------------------------------------------ occlusion

## Big walls from layout.json become occluders, so the cells behind a
## building aren't drawn (the map is split into 12 m cells for this). Only
## upright, opaque boxes at least OCCLUDER_MIN tall and wide; glass and
## invisible clip walls never occlude.
const OCCLUDER_MIN: Vector2 = Vector2(2.6, 2.5)


static func is_occluder(c: Dictionary) -> bool:
	if fbool(c, "clip") or fstr(c, "surface") in ["glass", "thin_metal", "cardboard"]:
		return false
	if absf(fnum(c, "rx")) > 1.0 or absf(fnum(c, "ry")) > 1.0:
		return false
	var s: Vector3 = collider_size(c)  # Godot axes: y is height
	return s.y >= OCCLUDER_MIN.x and maxf(s.x, s.z) >= OCCLUDER_MIN.y


func _build_occluders() -> int:
	var root: Node3D = Node3D.new()
	root.name = "Occluders"
	add_child(root)
	var n: int = 0
	for c: Dictionary in layout["colliders"]:
		if not is_occluder(c):
			continue
		var box: BoxOccluder3D = BoxOccluder3D.new()
		# A hair smaller than the wall, so it never hides what's in front of it.
		box.size = collider_size(c) - Vector3(0.05, 0.05, 0.05)
		var oi: OccluderInstance3D = OccluderInstance3D.new()
		oi.occluder = box
		oi.transform = collider_transform(c)
		root.add_child(oi)
		n += 1
	return n


# ------------------------------------------------------------------ colliders

func _body(surface: String, clip: bool) -> StaticBody3D:
	var key: String = ("clip_" if clip else "") + surface
	if static_bodies.has(key):
		return static_bodies[key]
	var b: StaticBody3D = StaticBody3D.new()
	b.name = "Col_" + key
	if clip:
		b.collision_layer = LAYER_CLIP
		b.collision_mask = 0
	else:
		b.collision_layer = Ballistics.LAYER_WORLD
		b.collision_mask = 0
		b.set_meta(&"surface", StringName(surface))
	add_child(b)
	static_bodies[key] = b
	return b


static func collider_transform(c: Dictionary) -> Transform3D:
	var yaw: float = deg_to_rad(fnum(c, "yaw"))
	var rx: float = deg_to_rad(fnum(c, "rx"))
	var ry: float = deg_to_rad(fnum(c, "ry"))
	var basis: Basis = Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, rx) * Basis(Vector3.BACK, -ry)
	return Transform3D(basis, fpos(c, "c"))


static func collider_size(c: Dictionary) -> Vector3:
	var s: Array = c["s"]
	var sx: float = s[0]
	var sy: float = s[1]
	var sz: float = s[2]
	return Vector3(maxf(sx, 0.02), maxf(sz, 0.02), maxf(sy, 0.02))


func _build_colliders() -> void:
	for c: Dictionary in layout["colliders"]:
		var clip: bool = fbool(c, "clip")
		var body: StaticBody3D = _body(fstr(c, "surface"), clip)
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = collider_size(c)
		cs.shape = box
		cs.transform = collider_transform(c)
		body.add_child(cs)


# ------------------------------------------------------------------ markers

func _build_markers() -> void:
	for m: Dictionary in layout["markers"]:
		var kind: String = fstr(m, "kind")
		var p: Vector3 = fpos(m)
		match kind:
			"spawn":
				spawn_points.append(p)
			"player_start":
				player_start = p + Vector3.UP * 0.05
				player_yaw = deg_to_rad(fnum(m, "yaw"))
			"camera":
				var cam: Camera3D = Camera3D.new()
				cam.name = fstr(m, "name")
				cam.fov = 70.0
				cam.current = false
				add_child(cam)
				cam.look_at_from_position(p, fpos(m, "target"))
				cam.add_to_group(&"capture_cameras")
			"light":
				if fbool(m, "dyn"):
					_character_light(m, p)


## Lights that only touch characters, guns and effects: the map's own
## lighting is baked, so these skip MAP_LAYER and cast no shadows.
func _character_light(m: Dictionary, p: Vector3) -> void:
	var watts: float = fnum(m, "energy")
	var l: Light3D
	if fstr(m, "type") == "SPOT":
		var s: SpotLight3D = SpotLight3D.new()
		s.spot_range = fnum(m, "range", 10.0)
		s.spot_angle = clampf(fnum(m, "spot", 90.0) * 0.5, 10.0, 80.0)
		l = s
	else:
		var o: OmniLight3D = OmniLight3D.new()
		o.omni_range = fnum(m, "range", 6.0)
		o.omni_attenuation = 1.6
		l = o
	l.light_color = fcolor(m)
	l.light_energy = clampf(watts / 60.0, 0.4, 3.0)
	l.light_cull_mask = 0xFFFFF & ~MAP_LAYER
	l.shadow_enabled = false
	l.light_specular = 0.6
	add_child(l)
	l.global_position = p
	if m.has("dir"):
		var d: Vector3 = fpos(m, "dir")
		l.look_at(p + d, Vector3.FORWARD if absf(d.y) > 0.9 else Vector3.UP)
	l.add_to_group(&"character_lights")


# ------------------------------------------------------------------ navigation

func _build_navigation() -> void:
	nav_region = NavigationRegion3D.new()
	nav_region.name = "Navigation"
	var nm: NavigationMesh = NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = Ballistics.LAYER_WORLD | LAYER_CLIP
	nm.agent_radius = 0.5
	nm.agent_height = 1.75
	nm.agent_max_climb = 0.25
	nm.agent_max_slope = 40.0
	nm.cell_size = 0.25
	nm.cell_height = 0.1
	# Only the ground floor and the first-floor gallery: no roofs.
	nm.filter_baking_aabb = AABB(Vector3(-47, -1.0, -35), Vector3(94, 6.0, 81))
	add_child(nav_region)
	NavigationServer3D.map_set_cell_height(get_world_3d().navigation_map, nm.cell_height)
	NavigationServer3D.map_set_cell_size(get_world_3d().navigation_map, nm.cell_size)
	nav_region.navigation_mesh = nm
	var source: NavigationMeshSourceGeometryData3D = NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nm, source, self)
	NavigationServer3D.bake_from_source_geometry_data_async(nm, source, func() -> void:
		nav_region.navigation_mesh = nm
		nav_region.enabled = true)


# ------------------------------------------------------------------ benchmark (same as the test room)

func _process(_delta: float) -> void:
	if _bench.is_running() or sweep.is_running():
		var t: float = _bench.progress() if _bench.is_running() else 0.0
		player.set_view(_bench_yaw0 + TAU * t, -0.08 + 0.1 * sin(t * TAU * 2.0))


func start_benchmark(duration_sec: float) -> void:
	player.input_enabled = false
	player.invulnerable = true
	player.global_position = b2g([-8.0, 7.0, -0.15])
	player.velocity = Vector3.ZERO
	_bench_yaw0 = 0.0
	_bench.start(duration_sec)


## Pause menu → Map cost test (FeatureSweep).
func start_feature_sweep() -> void:
	player.input_enabled = false
	player.invulnerable = true
	player.global_position = b2g([-8.0, 7.0, -0.15])
	player.velocity = Vector3.ZERO
	_bench_yaw0 = 0.0
	if wave_mode.running:
		wave_mode.stop()
	sweep.start()


## Ten passive men round the map cost test's spot, 5 to 27 m out, on the
## navmesh, facing it (the "+10 men" rows).
func _sweep_men() -> Array:
	var out: Array = []
	var centre: Vector3 = player.global_position
	var nav_map: RID = get_world_3d().navigation_map
	var roles: Array[String] = ["gunman", "gunman", "enforcer", "gunman", "red_pole"]
	for i: int in 10:
		var ang: float = TAU * i / 10.0 + 0.3
		var want: Vector3 = centre + Vector3(sin(ang), 0.0, cos(ang)) * (5.0 + 2.4 * i)
		var at: Vector3 = NavigationServer3D.map_get_closest_point(nav_map, want)
		if at == Vector3.ZERO and want.length() > 1.0:
			at = Vector3(want.x, centre.y, want.z)
		var e: Enemy = Enemy.new()
		e.config = load("res://data/enemies/%s.tres" % roles[i % roles.size()]) as EnemyConfig
		e.passive = true
		add_child(e)
		e.global_position = at
		var to: Vector3 = centre - at
		e.face(atan2(to.x, to.z))
		out.append(e)
	return out


func _on_sweep_finished(_rows: Array[Dictionary]) -> void:
	player.input_enabled = true
	player.invulnerable = false
	if _quit_after_bench:
		get_tree().quit()


func _on_bench_finished(result: Dictionary) -> void:
	if sweep.is_running():
		return
	player.input_enabled = true
	player.invulnerable = false
	Settings.store_bench_result(result)
	EventBus.benchmark_finished.emit(result)
	_hud.call("show_bench_done", result)
	if _quit_after_bench:
		print("bench: ", JSON.stringify(result))
		get_tree().quit()
