class_name FrameBench
extends Node
## Records frame times for a fixed duration and summarises them. Used for
## the M0 renderer comparison (Mobile vs Compatibility, by measured frame time).
## Results go to user://bench/<renderer>_<time>.json and to Settings.

signal finished(result: Dictionary)

var _frame_ms: PackedFloat32Array = PackedFloat32Array()
var _gpu_ms: PackedFloat32Array = PackedFloat32Array()
var _duration: float = 0.0
var _elapsed: float = 0.0
var _running: bool = false
var _saved_max_fps: int = 0
var _saved_held: bool = false


func is_running() -> bool:
	return _running


## 0..1 progress of the current run.
func progress() -> float:
	return clampf(_elapsed / _duration, 0.0, 1.0) if _duration > 0.0 else 0.0


func start(duration_sec: float) -> void:
	_frame_ms.clear()
	_gpu_ms.clear()
	_duration = duration_sec
	_elapsed = 0.0
	_running = true
	# Uncap so the numbers show headroom; vsync still limits to the panel rate.
	_saved_max_fps = Engine.max_fps
	Engine.max_fps = 0
	_saved_held = Settings.adaptive.held
	Settings.adaptive.held = true
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)


func _process(delta: float) -> void:
	if not _running:
		return
	_elapsed += delta
	_frame_ms.append(delta * 1000.0)
	var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid())
	if gpu > 0.0:
		_gpu_ms.append(gpu)
	if _elapsed >= _duration:
		_finish()


func _finish() -> void:
	_running = false
	Engine.max_fps = _saved_max_fps
	Settings.adaptive.held = _saved_held
	var result: Dictionary = summarize(_frame_ms)
	result["gpu_avg_ms"] = _mean(_gpu_ms)
	result["renderer"] = RenderingServer.get_current_rendering_method()
	result["driver"] = RenderingServer.get_current_rendering_driver_name()
	result["gpu"] = RenderingServer.get_video_adapter_name()
	result["render_scale"] = get_tree().root.scaling_3d_scale
	result["window"] = DisplayServer.window_get_size()
	result["time"] = Time.get_datetime_string_from_system()
	_write(result)
	finished.emit(result)


## Average, percentiles and max of frame times in milliseconds.
static func summarize(frame_ms: PackedFloat32Array) -> Dictionary:
	var sorted: PackedFloat32Array = frame_ms.duplicate()
	sorted.sort()
	var avg: float = _mean(sorted)
	return {
		"frames": sorted.size(),
		"avg_ms": avg,
		"p50_ms": _percentile(sorted, 0.50),
		"p95_ms": _percentile(sorted, 0.95),
		"p99_ms": _percentile(sorted, 0.99),
		"max_ms": sorted[sorted.size() - 1] if sorted.size() > 0 else 0.0,
		"avg_fps": 1000.0 / avg if avg > 0.0 else 0.0,
	}


static func _percentile(sorted: PackedFloat32Array, q: float) -> float:
	if sorted.is_empty():
		return 0.0
	var index: int = clampi(ceili(q * sorted.size()) - 1, 0, sorted.size() - 1)
	return sorted[index]


static func _mean(values: PackedFloat32Array) -> float:
	if values.is_empty():
		return 0.0
	var total: float = 0.0
	for v: float in values:
		total += v
	return total / values.size()


func _write(result: Dictionary) -> void:
	DirAccess.make_dir_recursive_absolute("user://bench")
	var stamp: String = Time.get_datetime_string_from_system().replace(":", "-")
	var path: String = "user://bench/%s_%s.json" % [result["renderer"], stamp]
	var file: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(result, "  "))
		print("bench: wrote ", ProjectSettings.globalize_path(path))
