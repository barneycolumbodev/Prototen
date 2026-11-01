extends CanvasLayer
## On-device debug overlay (CLAUDE.md §10.4): FPS, frame time, draw calls,
## memory, enemy/ragdoll/decal counts, renderer and benchmark results.
## Autoloaded as DebugOverlay. Toggle with F3 or from the pause menu.

const REFRESH_SEC: float = 0.25

var _label: Label
var _panel: PanelContainer
var _since_refresh: float = 0.0
var _frames: int = 0
var _frame_sum: float = 0.0
var _frame_max: float = 0.0


func _ready() -> void:
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	_panel = PanelContainer.new()
	_panel.position = Vector2(8, 8)
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0, 0, 0, 0.55)
	style.set_content_margin_all(6)
	_panel.add_theme_stylebox_override("panel", style)
	_label = Label.new()
	_label.add_theme_font_size_override("font_size", 13)
	_label.add_theme_color_override("font_color", Color(0.85, 1.0, 0.85))
	_panel.add_child(_label)
	add_child(_panel)
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	Settings.changed.connect(_sync_visibility)
	_sync_visibility()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"toggle_overlay"):
		Settings.set_overlay_visible(not Settings.overlay_visible)


func _process(delta: float) -> void:
	_frames += 1
	_frame_sum += delta
	_frame_max = maxf(_frame_max, delta)
	_since_refresh += delta
	if _since_refresh < REFRESH_SEC or not _panel.visible:
		return
	_label.text = _build_text()
	_since_refresh = 0.0
	_frames = 0
	_frame_sum = 0.0
	_frame_max = 0.0


func _build_text() -> String:
	var tree: SceneTree = get_tree()
	var vp_rid: RID = get_viewport().get_viewport_rid()
	var avg_ms: float = _frame_sum / maxi(_frames, 1) * 1000.0
	var lines: PackedStringArray = PackedStringArray()
	lines.append("GRAFT %s  %s/%s  %s" % [
		ProjectSettings.get_setting("application/config/version"),
		RenderingServer.get_current_rendering_method(),
		RenderingServer.get_current_rendering_driver_name(),
		RenderingServer.get_video_adapter_name()])
	lines.append("FPS %d  frame %.1f ms (max %.1f)  gpu %.1f ms  cpu %.1f ms" % [
		Engine.get_frames_per_second(), avg_ms, _frame_max * 1000.0,
		RenderingServer.viewport_get_measured_render_time_gpu(vp_rid),
		RenderingServer.viewport_get_measured_render_time_cpu(vp_rid)])
	lines.append("draws %d  prims %.1fk  objects %d" % [
		Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME) / 1000.0,
		Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)])
	lines.append("mem %.0f MB  vram %.0f MB  scale %.2f  cap %s" % [
		OS.get_static_memory_usage() / 1048576.0,
		Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0,
		get_tree().root.scaling_3d_scale,
		str(Engine.max_fps) if Engine.max_fps > 0 else "off"])
	lines.append("enemies %d  ragdolls %d  decals %d" % [
		tree.get_node_count_in_group(&"enemies"),
		tree.get_node_count_in_group(&"ragdolls"),
		tree.get_node_count_in_group(&"decals")])
	var pads: Array[int] = Input.get_connected_joypads()
	lines.append("pad: %s" % (Input.get_joy_name(pads[0]) if not pads.is_empty() else "none"))
	for method: String in Settings.RENDERERS:
		lines.append("bench %s: %s" % [method, format_bench(Settings.bench_results.get(method, {}))])
	return "\n".join(lines)


static func format_bench(result: Variant) -> String:
	var r: Dictionary = result if result is Dictionary else {}
	if r.is_empty():
		return "--"
	return "avg %.1f  p95 %.1f  p99 %.1f ms  (%.0f fps, gpu %.1f ms, scale %.2f)" % [
		r.get("avg_ms", 0.0), r.get("p95_ms", 0.0), r.get("p99_ms", 0.0),
		r.get("avg_fps", 0.0), r.get("gpu_avg_ms", 0.0), r.get("render_scale", 1.0)]


func _sync_visibility() -> void:
	_panel.visible = Settings.overlay_visible
