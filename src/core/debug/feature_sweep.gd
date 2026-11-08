class_name FeatureSweep
extends Node
## Map cost test (pause menu, Chinatown): spins the camera in the same spot
## once with everything on, then once with each effect switched off, and
## shows how many milliseconds of GPU time each one costs on this phone.
## Built after the 2026-11-05 playtest (28-29 fps on the Moto G) so the next
## optimisation pass works from the phone's numbers, not guesses.
## Results: on screen until the next pause, the debug overlay, and
## user://bench/sweep_<time>.json.

signal finished(rows: Array[Dictionary])

const STEP_SECONDS: float = 4.0
const SETTLE_SECONDS: float = 1.0
## [label, features switched off, render scale (0 = the scale it started at)].
## 2026-11-07: rows for the gun model and two fixed resolutions, so the next
## round shows how much the frame scales with pixels on the phone.
const STEPS: Array = [
	["all on", [], 0.0],
	["reflections off", [&"probes"]],
	["bloom off", [&"glow"]],
	["water streaks off", [&"water_streaks"]],
	["puddle ripples off", [&"ripples"]],
	["rain off", [&"rain"]],
	["steam off", [&"steam"]],
	["fog off", [&"fog"]],
	["gun hidden", [&"viewmodel"]],
	["all on @ 100% res", [], 1.0],
	["all on @ 70% res", [], 0.7],
]

var atmos: NightAtmosphere
## Hidden for the "gun hidden" row: the first-person rigs and their fill light.
var viewmodel: Array[Node3D] = []
var _vm_saved: Dictionary[Node3D, bool] = {}
var _start_scale: float = 1.0
var bench: FrameBench
var rows: Array[Dictionary] = []
var _i: int = -1
var _settle: float = 0.0
var _label: Label
var _layer: CanvasLayer


static func total_seconds() -> float:
	return STEPS.size() * (STEP_SECONDS + SETTLE_SECONDS)


func is_running() -> bool:
	return _i >= 0


func start() -> void:
	rows.clear()
	_i = 0
	_start_scale = get_tree().root.scaling_3d_scale
	Settings.adaptive.held = true
	_begin_step()


func _begin_step() -> void:
	for f: StringName in NightAtmosphere.FEATURES:
		atmos.set_feature(f, true)
	_show_viewmodel(true)
	var step: Array = STEPS[_i]
	var off: Array = step[1]
	for f: StringName in off:
		if f == &"viewmodel":
			_show_viewmodel(false)
		else:
			atmos.set_feature(f, false)
	var s: float = step[2] if step.size() > 2 else 0.0
	get_tree().root.scaling_3d_scale = s if s > 0.0 else _start_scale
	_settle = SETTLE_SECONDS


func _process(delta: float) -> void:
	if _i < 0 or bench.is_running():
		return
	_settle -= delta
	if _settle <= 0.0:
		bench.finished.connect(_on_step_done, CONNECT_ONE_SHOT)
		bench.start(STEP_SECONDS)


## Hides the rigs (remembering which were showing), or puts them back.
func _show_viewmodel(on: bool) -> void:
	if not on:
		if not _vm_saved.is_empty():
			return
		for n: Node3D in viewmodel:
			if is_instance_valid(n):
				_vm_saved[n] = n.visible
				n.visible = false
		return
	for n: Node3D in _vm_saved:
		if is_instance_valid(n):
			n.visible = _vm_saved[n]
	_vm_saved.clear()


## 0..1 over the whole sweep.
func progress() -> float:
	if _i < 0:
		return 0.0
	return clampf((_i + bench.progress()) / STEPS.size(), 0.0, 1.0)


func _on_step_done(result: Dictionary) -> void:
	rows.append({"step": STEPS[_i][0], "gpu_ms": result.get("gpu_avg_ms", 0.0), "frame_ms": result.get("avg_ms", 0.0),
		"p95_ms": result.get("p95_ms", 0.0), "scale": get_tree().root.scaling_3d_scale})
	_i += 1
	if _i < STEPS.size():
		_begin_step()
		return
	_i = -1
	for f: StringName in NightAtmosphere.FEATURES:
		atmos.set_feature(f, true)
	atmos.set_feature(&"glow", Settings.bloom)
	_show_viewmodel(true)
	get_tree().root.scaling_3d_scale = _start_scale
	Settings.adaptive.held = false
	_save()
	_show()
	finished.emit(rows)


static func _scale_of(row: Dictionary) -> float:
	var v: Variant = row.get("scale", 1.0)
	return v if v is float else 1.0


## One line per step: GPU ms and the saving against "all on".
static func format_rows(r: Array[Dictionary]) -> String:
	if r.is_empty():
		return ""
	var base_gpu: float = r[0]["gpu_ms"]
	var base_frame: float = r[0]["frame_ms"]
	var lines: PackedStringArray = PackedStringArray()
	lines.append("MAP COST TEST  (GPU ms per frame; saving vs all on; res %d%%)" % roundi(_scale_of(r[0]) * 100.0))
	for row: Dictionary in r:
		var g: float = row["gpu_ms"]
		var f: float = row["frame_ms"]
		if row == r[0]:
			lines.append("%-20s gpu %5.1f   frame %5.1f" % [row["step"], g, f])
		else:
			lines.append("%-20s gpu %5.1f (%+.1f)   frame %5.1f (%+.1f)" % [row["step"], g, g - base_gpu, f, f - base_frame])
	lines.append("Screenshot this for Claude. Pause to close.")
	return "\n".join(lines)


func _save() -> void:
	DirAccess.make_dir_recursive_absolute("user://bench")
	var stamp: String = Time.get_datetime_string_from_system().replace(":", "-")
	var f: FileAccess = FileAccess.open("user://bench/sweep_%s.json" % stamp, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({"rows": rows, "gpu": RenderingServer.get_video_adapter_name(),
			"renderer": RenderingServer.get_current_rendering_method(), "scale": get_tree().root.scaling_3d_scale}, "  "))
	print("sweep: ", JSON.stringify(rows))


func _show() -> void:
	if _layer == null:
		_layer = CanvasLayer.new()
		_layer.layer = 90
		add_child(_layer)
		var panel: PanelContainer = PanelContainer.new()
		var style: StyleBoxFlat = StyleBoxFlat.new()
		style.bg_color = Color(0, 0, 0, 0.75)
		style.set_content_margin_all(12)
		panel.add_theme_stylebox_override("panel", style)
		panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
		panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
		panel.grow_vertical = Control.GROW_DIRECTION_BOTH
		_label = Label.new()
		_label.add_theme_font_size_override("font_size", 18)
		_label.add_theme_color_override("font_color", Color(0.85, 1.0, 0.9))
		var mono: SystemFont = SystemFont.new()
		mono.font_names = PackedStringArray(["monospace", "Droid Sans Mono", "Courier New"])
		_label.add_theme_font_override("font", mono)
		panel.add_child(_label)
		_layer.add_child(panel)
	_label.text = format_rows(rows)
	_layer.visible = true


func _input(event: InputEvent) -> void:
	if _layer and _layer.visible and event.is_action_pressed(&"pause"):
		_layer.visible = false
