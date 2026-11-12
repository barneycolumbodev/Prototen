extends Node
## Player-facing settings, saved to user://settings.cfg. Autoloaded as Settings.
## Also registers the default input actions at startup.
##
## The renderer can't change while running: it is written to the project
## settings override file (application/config/project_settings_override) and
## applies the next time the app starts.

signal changed

const SETTINGS_PATH: String = "user://settings.cfg"
const OVERRIDE_PATH: String = "user://settings_override.cfg"
const RENDER_SCALES: Array[float] = [0.7, 0.8, 0.9, 1.0]
const FPS_CAPS: Array[int] = [60, 30]
const RENDERERS: Array[String] = ["mobile", "gl_compatibility"]
const LOOK_PRESETS: Array[String] = ["standard", "linear", "precise"]
## Look speed multipliers offered in the pause menu (on top of the preset).
const LOOK_SPEEDS: Array[float] = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.15, 1.3, 1.5]

var render_scale: float = 1.0
## Lower the 3D resolution (down to 60 %) when the GPU can't hold the frame
## cap; render_scale is then the most it uses (playtest 2026-11-05).
var adaptive_resolution: bool = true
var adaptive: AdaptiveResolution
var max_fps: int = 60
var overlay_visible: bool = true
## Godot's bloom. Off by default: on the Moto G it cost 3.2 ms of a 17.9 ms
## frame (map cost test, 2026-11-07) and side-by-side captures of Chinatown
## with and without it are nearly identical. Levels read this.
var bloom: bool = false
## Gore.Level: 0 off, 1 standard, 2 maximum (dismemberment). Maximum by default in the prototype.
var gore_level: int = 2
var look_preset: String = "standard"
## Multiplies stick look speed (pause menu → Look speed).
var look_sensitivity: float = 1.0
## Vertical field of view in degrees. 60 vertical ≈ 104 horizontal on the 20:9 target phone.
var vertical_fov: float = 60.0
## Last benchmark per renderer: { "mobile": {...}, "gl_compatibility": {...} }
var bench_results: Dictionary = {}

var _look: LookConfig


func _ready() -> void:
	InputBindings.register_defaults()
	adaptive = AdaptiveResolution.new()
	adaptive.name = "AdaptiveResolution"
	add_child(adaptive)
	load_settings()
	apply()


func load_settings() -> void:
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(SETTINGS_PATH) != OK:
		return
	render_scale = cfg.get_value("video", "render_scale", render_scale)
	adaptive_resolution = cfg.get_value("video", "adaptive_resolution", adaptive_resolution)
	max_fps = cfg.get_value("video", "max_fps", max_fps)
	vertical_fov = cfg.get_value("video", "vertical_fov", vertical_fov)
	overlay_visible = cfg.get_value("debug", "overlay_visible", overlay_visible)
	bloom = cfg.get_value("video", "bloom_v2", bloom)
	var gore: int = cfg.get_value("video", "gore_level", gore_level)
	gore_level = clampi(gore, 0, 2)
	look_preset = cfg.get_value("input", "look_preset", look_preset)
	var sens: float = cfg.get_value("input", "look_sensitivity", look_sensitivity)
	look_sensitivity = clampf(sens, 0.2, 3.0)
	var bench: Variant = cfg.get_value("debug", "bench_results", {})
	if bench is Dictionary:
		bench_results = bench
	if look_preset not in LOOK_PRESETS:
		look_preset = LOOK_PRESETS[0]


func save_settings() -> void:
	var cfg: ConfigFile = ConfigFile.new()
	cfg.set_value("video", "render_scale", render_scale)
	cfg.set_value("video", "adaptive_resolution", adaptive_resolution)
	cfg.set_value("video", "max_fps", max_fps)
	cfg.set_value("video", "vertical_fov", vertical_fov)
	cfg.set_value("debug", "overlay_visible", overlay_visible)
	cfg.set_value("video", "bloom_v2", bloom)
	cfg.set_value("video", "gore_level", gore_level)
	cfg.set_value("debug", "bench_results", bench_results)
	cfg.set_value("input", "look_preset", look_preset)
	cfg.set_value("input", "look_sensitivity", look_sensitivity)
	var err: Error = cfg.save(SETTINGS_PATH)
	if err != OK:
		push_warning("Settings: could not save (%s)" % error_string(err))


func apply() -> void:
	get_tree().root.scaling_3d_scale = render_scale
	Engine.max_fps = max_fps
	adaptive.configure(adaptive_resolution, render_scale)
	_look = load("res://data/input/look_%s.tres" % look_preset) as LookConfig
	changed.emit()


func look_config() -> LookConfig:
	return _look


func cycle_render_scale() -> void:
	render_scale = next_in(RENDER_SCALES, render_scale)
	_commit()


func toggle_adaptive_resolution() -> void:
	adaptive_resolution = not adaptive_resolution
	_commit()


func cycle_max_fps() -> void:
	var caps: Array[float] = []
	for c: int in FPS_CAPS:
		caps.append(float(c))
	max_fps = int(next_in(caps, float(max_fps)))
	_commit()


func toggle_bloom() -> void:
	bloom = not bloom
	_commit()


func cycle_look_preset() -> void:
	var i: int = LOOK_PRESETS.find(look_preset)
	look_preset = LOOK_PRESETS[(i + 1) % LOOK_PRESETS.size()]
	_commit()


## Steps the look speed up (+1) or down (-1) through LOOK_SPEEDS, without wrapping.
func step_look_sensitivity(direction: int) -> void:
	var i: int = 0
	var best: float = INF
	for k: int in LOOK_SPEEDS.size():
		var d: float = absf(LOOK_SPEEDS[k] - look_sensitivity)
		if d < best:
			best = d
			i = k
	look_sensitivity = LOOK_SPEEDS[clampi(i + direction, 0, LOOK_SPEEDS.size() - 1)]
	_commit()


## A on the menu button: next step up, wrapping to the slowest after the fastest.
func cycle_look_sensitivity() -> void:
	if is_equal_approx(look_sensitivity, LOOK_SPEEDS[LOOK_SPEEDS.size() - 1]):
		look_sensitivity = LOOK_SPEEDS[0]
		_commit()
	else:
		step_look_sensitivity(1)


func cycle_gore_level() -> void:
	gore_level = (gore_level + 1) % 3
	_commit()


func gore_name() -> String:
	return ["Off", "Standard", "Maximum"][clampi(gore_level, 0, 2)]


func set_overlay_visible(value: bool) -> void:
	overlay_visible = value
	_commit()


func store_bench_result(result: Dictionary) -> void:
	bench_results[current_renderer()] = result
	save_settings()
	changed.emit()


func current_renderer() -> String:
	return RenderingServer.get_current_rendering_method()


## Renderer that will be used on the next start.
func next_start_renderer() -> String:
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(OVERRIDE_PATH) == OK:
		return str(cfg.get_value("rendering", "renderer/rendering_method.mobile", current_renderer()))
	return str(ProjectSettings.get_setting("rendering/renderer/rendering_method.mobile", current_renderer()))


func cycle_next_start_renderer() -> String:
	var i: int = RENDERERS.find(next_start_renderer())
	var method: String = RENDERERS[(i + 1) % RENDERERS.size()]
	var cfg: ConfigFile = ConfigFile.new()
	cfg.load(OVERRIDE_PATH)  # missing file is fine
	cfg.set_value("rendering", "renderer/rendering_method", method)
	cfg.set_value("rendering", "renderer/rendering_method.mobile", method)
	var err: Error = cfg.save(OVERRIDE_PATH)
	if err != OK:
		push_warning("Settings: could not save renderer override (%s)" % error_string(err))
	return method


## The element after `current` in `values` (wraps). Unknown values go to the first element.
static func next_in(values: Array[float], current: float) -> float:
	for i: int in values.size():
		if is_equal_approx(values[i], current):
			return values[(i + 1) % values.size()]
	return values[0]


func _commit() -> void:
	save_settings()
	apply()
