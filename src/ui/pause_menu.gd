extends CanvasLayer
## Pause menu (Menu/Start button): resume, gun tuning, renderer, render scale, frame cap,
## look curve, look speed, debug overlay, benchmark, quit. Controller: D-pad/stick to
## move, A to press, B to close (A/B are bound by InputBindings.register_ui_buttons).
## Autoloaded as PauseMenu.

const BENCH_SECONDS: float = 20.0

var _root: Control
var _list: VBoxContainer
var _notice: Label
var _buttons: Dictionary[String, Button] = {}


func _ready() -> void:
	layer = 50
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build()
	_root.visible = false


func is_open() -> bool:
	return _root.visible


func open() -> void:
	_refresh()
	_root.visible = true
	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_buttons["resume"].grab_focus()


func close() -> void:
	_root.visible = false
	get_tree().paused = false


func _unhandled_input(event: InputEvent) -> void:
	if TuningMenu.is_open():
		return
	if event.is_action_pressed(&"pause"):
		if is_open():
			close()
		else:
			open()
		get_viewport().set_input_as_handled()
	elif is_open() and event.is_action_pressed(&"ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _build() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	var dim: ColorRect = ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)
	var center: CenterContainer = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	_list = VBoxContainer.new()
	_list.custom_minimum_size = Vector2(420, 0)
	_list.add_theme_constant_override("separation", 6)
	center.add_child(_list)
	var title: Label = Label.new()
	title.text = "PAUSED"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 28)
	_list.add_child(title)
	_add("resume", close)
	_add("tuning", _on_tuning)
	_add("renderer", _on_renderer)
	_add("scale", Settings.cycle_render_scale)
	_add("fps", Settings.cycle_max_fps)
	_add("look", Settings.cycle_look_preset)
	_add("look_speed", Settings.cycle_look_sensitivity)
	# Left/right on the look-speed button steps it down/up.
	_buttons["look_speed"].gui_input.connect(func(event: InputEvent) -> void:
		if event.is_action_pressed(&"ui_left") or event.is_action_pressed(&"ui_right"):
			Settings.step_look_sensitivity(1 if event.is_action_pressed(&"ui_right") else -1)
			_buttons["look_speed"].accept_event())
	_add("overlay", func() -> void: Settings.set_overlay_visible(not Settings.overlay_visible))
	_add("bench", _on_bench)
	_add("quit", func() -> void: get_tree().quit())
	_notice = Label.new()
	_notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_notice.add_theme_font_size_override("font_size", 14)
	_list.add_child(_notice)
	Settings.changed.connect(_refresh)


func _add(id: String, action: Callable) -> void:
	var b: Button = Button.new()
	b.custom_minimum_size = Vector2(0, 40)
	b.pressed.connect(action)
	b.pressed.connect(_refresh)
	_list.add_child(b)
	_buttons[id] = b


func _label(id: String, text: String) -> void:
	_buttons[id].text = text


func _refresh() -> void:
	_label("resume", "Resume")
	_label("tuning", "Gun tuning")
	var now: String = Settings.current_renderer()
	var next: String = Settings.next_start_renderer()
	_label("renderer", "Renderer: %s%s" % [_pretty(now), "" if next == now else "  →  %s after restart" % _pretty(next)])
	_label("scale", "Render scale: %d%%" % roundi(Settings.render_scale * 100.0))
	_label("fps", "Frame cap: %d fps" % Settings.max_fps)
	_label("look", "Look curve: %s" % Settings.look_config().display_name)
	_label("look_speed", "Look speed: %d%%   (< >)" % roundi(Settings.look_sensitivity * 100.0))
	_label("overlay", "Debug overlay: %s" % ("on" if Settings.overlay_visible else "off"))
	_label("bench", "Run benchmark (%d s)" % roundi(BENCH_SECONDS))
	_label("quit", "Quit")


func _on_renderer() -> void:
	var method: String = Settings.cycle_next_start_renderer()
	_notice.text = "Close the app and open it again to start with the %s renderer." % _pretty(method)


func _on_tuning() -> void:
	_root.visible = false
	TuningMenu.open()


func _on_bench() -> void:
	close()
	EventBus.benchmark_requested.emit(BENCH_SECONDS)


static func _pretty(method: String) -> String:
	return "Compatibility" if method == "gl_compatibility" else "Mobile"
