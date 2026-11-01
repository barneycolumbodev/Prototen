extends CanvasLayer
## M0 HUD: centre dot, controller prompt, benchmark progress.

var bench: FrameBench

var _status: Label
var _pad_notice: Label


func _ready() -> void:
	var dot: ColorRect = ColorRect.new()
	dot.color = Color(1, 1, 1, 0.85)
	dot.size = Vector2(4, 4)
	dot.set_anchors_preset(Control.PRESET_CENTER)
	dot.position -= Vector2(2, 2)
	add_child(dot)
	_status = _make_label(Control.PRESET_CENTER_TOP, 18)
	_pad_notice = _make_label(Control.PRESET_CENTER_BOTTOM, 15)
	_pad_notice.text = "No controller detected. Connect one to play."
	Input.joy_connection_changed.connect(func(_device: int, _connected: bool) -> void: _update_pad_notice())
	_update_pad_notice()


func _process(_delta: float) -> void:
	if bench and bench.is_running():
		_status.text = "BENCHMARK %d%%  (don't touch the controller)" % roundi(bench.progress() * 100.0)
	elif not _status.text.is_empty() and not _status.text.begins_with("Benchmark done"):
		_status.text = ""


func show_bench_done(result: Dictionary) -> void:
	_status.text = "Benchmark done: avg %.1f ms, p95 %.1f ms (%s). Saved; see debug overlay." % [
		result.get("avg_ms", 0.0), result.get("p95_ms", 0.0), result.get("renderer", "")]
	get_tree().create_timer(8.0).timeout.connect(func() -> void: _status.text = "")


func _update_pad_notice() -> void:
	_pad_notice.visible = Input.get_connected_joypads().is_empty() and OS.has_feature("mobile")


func _make_label(preset: Control.LayoutPreset, size: int) -> Label:
	var label: Label = Label.new()
	label.set_anchors_and_offsets_preset(preset, Control.PRESET_MODE_KEEP_SIZE, 24)
	label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 4)
	add_child(label)
	return label
