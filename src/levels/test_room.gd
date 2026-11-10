class_name TestRoom
extends Node3D
## M0 test room: greybox built from the BLOCKS table so the layout is easy to
## read and change. Two levels (mezzanine on the north side), cover crates,
## mantle ledges of 1.0/1.5/2.0 m, a freestanding wall-run wall, pillars.
## Fixed capture cameras for tools/screenshot.sh; a benchmark sweep point.
##
## Units are metres; +Y up, -Z north. One CSGCombiner3D per material keeps
## draw calls low.

const SIZE: float = 32.0
const WALL_H: float = 6.0
const MEZZ_TOP: float = 3.5

## [material, size, centre, yaw_deg, pitch_deg]
const BLOCKS: Array = [
	# Floor and outer walls
	["floor", Vector3(32, 0.5, 32), Vector3(0, -0.25, 0), 0, 0],
	["wall", Vector3(33, 6, 0.5), Vector3(0, 3, -16.25), 0, 0],
	["wall", Vector3(33, 6, 0.5), Vector3(0, 3, 16.25), 0, 0],
	["wall", Vector3(0.5, 6, 32), Vector3(16.25, 3, 0), 0, 0],
	["wall", Vector3(0.5, 6, 32), Vector3(-16.25, 3, 0), 0, 0],
	# Mezzanine (second level) along the north wall, with pillars and a low parapet
	["floor", Vector3(32, 0.4, 8), Vector3(0, MEZZ_TOP - 0.2, -12), 0, 0],
	["wall", Vector3(0.6, 3.1, 0.6), Vector3(-10, 1.55, -8.4), 0, 0],
	["wall", Vector3(0.6, 3.1, 0.6), Vector3(0, 1.55, -8.4), 0, 0],
	["wall", Vector3(0.6, 3.1, 0.6), Vector3(10, 1.55, -8.4), 0, 0],
	["prop", Vector3(6, 1.0, 0.3), Vector3(-6, MEZZ_TOP + 0.5, -8.15), 0, 0],
	["prop", Vector3(6, 1.0, 0.3), Vector3(5, MEZZ_TOP + 0.5, -8.15), 0, 0],
	# Ramp up to the mezzanine (east side, ~25 degrees)
	["floor", Vector3(3, 0.3, 8.6), Vector3(13.5, 1.65, -4.2), 0, 24],
	# Freestanding wall-run wall (west side)
	["wall", Vector3(0.5, 5, 14), Vector3(-9, 2.5, 6), 0, 0],
	# Mantle ledges along the west wall: 1.0, 1.5, 2.0 m
	["prop", Vector3(2, 1.0, 2), Vector3(-15, 0.5, -4), 0, 0],
	["prop", Vector3(2, 1.5, 2), Vector3(-15, 0.75, -1), 0, 0],
	["prop", Vector3(2, 2.0, 2), Vector3(-15, 1.0, 2), 0, 0],
	# Cover crates
	["prop", Vector3(1.2, 1.2, 1.2), Vector3(-3, 0.6, 2), 0, 0],
	["prop", Vector3(2.4, 1.2, 1.2), Vector3(3, 0.6, -2), 15, 0],
	["prop", Vector3(1.2, 1.2, 1.2), Vector3(6, 0.6, 6), 30, 0],
	["prop", Vector3(1.2, 2.4, 1.2), Vector3(-4, 1.2, 10), 0, 0],
	["prop", Vector3(3, 1.0, 0.6), Vector3(8, 0.5, 11), 0, 0],
	# Partition with a doorway (south-east)
	["wall", Vector3(5, 4, 0.4), Vector3(8.5, 2, 8), 0, 0],
	["wall", Vector3(4, 4, 0.4), Vector3(15, 2, 8), 0, 0],
]

## Ballistic surface of each greybox material (data/surfaces/).
const SURFACES: Dictionary[String, StringName] = {"floor": &"concrete", "wall": &"concrete", "prop": &"crate"}

const MATERIALS: Dictionary = {
	"floor": [Color(0.27, 0.28, 0.3), Color(0.5, 0.52, 0.55)],
	"wall": [Color(0.42, 0.43, 0.45), Color(0.6, 0.62, 0.65)],
	"prop": [Color(0.62, 0.38, 0.16), Color(0.82, 0.58, 0.3)],
}

## Fixed capture cameras: name -> [position, look-at target]
const CAPTURE_CAMERAS: Dictionary = {
	"CapOverview": [Vector3(13, 9, 14), Vector3(-2, 0, -4)],
	"CapMezzanine": [Vector3(-12, 5.2, -13), Vector3(6, 1, 6)],
	"CapFloor": [Vector3(0, 1.65, 13), Vector3(0, 1.4, -10)],
	"CapPenLane": [Vector3(4.2, 2.2, 6.2), Vector3(10.5, 0.9, 0.8)],
	"CapRange": [Vector3(-1.5, 2.6, 6.0), Vector3(-2.0, 0.9, -5.0)],
	"CapWalls": [Vector3(0.5, 1.9, 2.0), Vector3(5.0, 1.0, -6.0)],
	"CapDummy": [Vector3(1.2, 1.55, 0.7), Vector3(1.5, 1.2, -1.0)],
	"CapGore": [Vector3(-1.6, 1.4, 1.2), Vector3(1.2, 0.4, -1.6)],
	"CapBodies": [Vector3(-5.2, 1.5, 2.2), Vector3(-7.6, 0.5, -1.2)],
	"CapSever": [Vector3(-3.6, 1.5, 6.2), Vector3(-5.6, 0.4, 3.6)],
}

const PLAYER_SCENE: PackedScene = preload("res://src/player/player.tscn")
const SPAWN: Vector3 = Vector3(0, 0, 12)
const BENCH_POINT: Vector3 = Vector3(0, 0, 3)

var player: Player
var shooting_range: ShootingRange
var wave_mode: WaveMode
var combat_hud: CombatHud
var _bench: FrameBench
var _hud: Node
var _bench_yaw0: float = 0.0
var _quit_after_bench: bool = false


func _ready() -> void:
	_build_geometry()
	_build_lighting()
	_build_capture_cameras()
	shooting_range = ShootingRange.new()
	shooting_range.name = "ShootingRange"
	add_child(shooting_range)
	Sfx.set_room(0.6)
	player = PLAYER_SCENE.instantiate() as Player
	add_child(player)
	player.global_position = SPAWN
	player.spawn_point = SPAWN
	player.set_view(0.0, 0.0)
	player.aim_assist = AimAssist.new(load("res://data/input/aim_assist.tres") as AimAssistConfig)
	# Tuning the owner saved on the phone (pause menu → Gun tuning).
	if not CaptureDirector.is_capturing():
		TuningMenu.load_saved_all(player.weapon(), player.aim_assist.config)
		player.weapon().apply_tuning.call_deferred()
	_bench = FrameBench.new()
	add_child(_bench)
	_bench.finished.connect(_on_bench_finished)
	_hud = preload("res://src/ui/hud.gd").new()
	_hud.set("bench", _bench)
	_hud.set("weapon", player.weapon())
	add_child(_hud)
	combat_hud = CombatHud.new()
	combat_hud.player = player
	add_child(combat_hud)
	wave_mode = WaveMode.new()
	wave_mode.name = "WaveMode"
	wave_mode.room = self
	add_child(wave_mode)
	EventBus.wave_mode_requested.connect(wave_mode.toggle)
	EventBus.benchmark_requested.connect(start_benchmark)
	# `-- --bench=<seconds>`: run the benchmark at startup and quit (cloud/CI use).
	for arg: String in OS.get_cmdline_user_args():
		if arg == "--waves":
			wave_mode.start.call_deferred()
		if arg == "--god":
			player.invulnerable = true
		if arg == "--demo=gauss":
			var gauss: GaussDemo = GaussDemo.new()
			gauss.room = self
			add_child(gauss)
		elif arg.begins_with("--demo=active:"):
			var ad: ActivesDemo = ActivesDemo.new()
			ad.room = self
			ad.part_id = arg.trim_prefix("--demo=active:")
			add_child(ad)
		elif arg == "--demo=gore":
			var gd: GoreDemo = GoreDemo.new()
			gd.room = self
			add_child(gd)
		elif arg.begins_with("--demo="):
			var demo: GunplayDemo = GunplayDemo.new()
			demo.room = self
			demo.mode = arg.trim_prefix("--demo=")
			add_child(demo)
		if arg.begins_with("--bench="):
			_quit_after_bench = true
			start_benchmark.call_deferred(arg.trim_prefix("--bench=").to_float())


func _process(_delta: float) -> void:
	if _bench.is_running():
		# One slow full turn with a gentle pitch wave: the same view sequence every run.
		var t: float = _bench.progress()
		player.set_view(_bench_yaw0 + TAU * t, -0.12 + 0.1 * sin(t * TAU * 2.0))


func start_benchmark(duration_sec: float) -> void:
	player.input_enabled = false
	player.invulnerable = true
	player.global_position = BENCH_POINT
	player.velocity = Vector3.ZERO
	_bench_yaw0 = 0.0
	_bench.start(duration_sec)


func _on_bench_finished(result: Dictionary) -> void:
	player.input_enabled = true
	player.invulnerable = false
	Settings.store_bench_result(result)
	EventBus.benchmark_finished.emit(result)
	_hud.call("show_bench_done", result)
	if _quit_after_bench:
		print("bench: ", JSON.stringify(result))
		get_tree().quit()


func _build_geometry() -> void:
	var combiners: Dictionary[String, CSGCombiner3D] = {}
	for key: String in MATERIALS:
		var colors: Array = MATERIALS[key]
		var mat: ShaderMaterial = ShaderMaterial.new()
		mat.shader = preload("res://src/levels/grid.gdshader")
		mat.set_shader_parameter("base_color", colors[0])
		mat.set_shader_parameter("line_color", colors[1])
		var combiner: CSGCombiner3D = CSGCombiner3D.new()
		combiner.name = "Geo_" + key
		combiner.use_collision = true
		combiner.set_meta(&"surface", SURFACES[key])
		combiner.material_override = mat
		add_child(combiner)
		combiners[key] = combiner
	for block: Array in BLOCKS:
		var key: String = block[0]
		var yaw_deg: float = block[3]
		var pitch_deg: float = block[4]
		var box: CSGBox3D = CSGBox3D.new()
		box.size = block[1]
		box.position = block[2]
		box.rotation_degrees = Vector3(pitch_deg, yaw_deg, 0.0)
		combiners[key].add_child(box)


func _build_lighting() -> void:
	var env: Environment = Environment.new()
	var sky_mat: ProceduralSkyMaterial = ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.33, 0.42, 0.55)
	sky_mat.sky_horizon_color = Color(0.62, 0.62, 0.6)
	sky_mat.ground_horizon_color = Color(0.4, 0.38, 0.35)
	var sky: Sky = Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.55, 0.57, 0.6)
	env.fog_density = 0.004
	var world_env: WorldEnvironment = WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun: DirectionalLight3D = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-52, -35, 0)
	sun.light_energy = 1.3
	sun.shadow_enabled = true  # the only shadow-casting light (CLAUDE.md §8)
	sun.directional_shadow_max_distance = 40.0
	add_child(sun)
	# Two warm fill lights under the mezzanine; no shadows. Total dynamic lights: 3.
	for x: float in [-7.0, 7.0]:
		var lamp: OmniLight3D = OmniLight3D.new()
		lamp.position = Vector3(x, 2.8, -12)
		lamp.light_color = Color(1.0, 0.75, 0.45)
		lamp.light_energy = 2.0
		lamp.omni_range = 9.0
		add_child(lamp)


func _build_capture_cameras() -> void:
	for cam_name: String in CAPTURE_CAMERAS:
		var spec: Array = CAPTURE_CAMERAS[cam_name]
		var cam: Camera3D = Camera3D.new()
		cam.name = cam_name
		cam.fov = 60.0
		cam.current = false
		add_child(cam)
		var from: Vector3 = spec[0]
		var target: Vector3 = spec[1]
		cam.look_at_from_position(from, target)
		cam.add_to_group(&"capture_cameras")
