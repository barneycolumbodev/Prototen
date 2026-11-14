class_name MainMenu
extends Node3D
## The main menu (owner, 2026-11-14): the game opens on the operative,
## helmet off, leaning on the front of the Sea View restaurant on the
## Chinatown docks at night, smoking. Left: Begin, Loadout, Map, Options,
## Quit. Loadout opens the loadout screen over the scene with him in the
## clear left quarter, wearing every part as it's browsed and installed;
## what's built is saved and goes into the game. Begin fades to black and
## starts the chosen map (Chinatown starts right here, on this map).
##
## Lives under ChinatownMap (which builds the map, the atmosphere and the
## lights first and holds the game back until Begin). Staging values in
## data/levels/main_menu.tres.

signal begin_requested(scene_path: String)

const CONFIG_PATH: String = "res://data/levels/main_menu.tres"
const DEFAULT_LOADOUT: BodyLoadout = preload("res://data/body/loadout_default.tres")
## Maps Begin can start (scene path, name).
const MAPS: Array[Array] = [
	["res://src/levels/chinatown/chinatown.tscn", "Chinatown docks"],
	["res://src/levels/test_room.tscn", "Test range"],
]
const C_ACCENT: Color = Color(0.36, 0.86, 0.78)
const C_TEXT: Color = Color(0.86, 0.88, 0.88)
const C_DIM: Color = Color(0.52, 0.58, 0.6)

var config: MenuSceneConfig
var smoker: MenuSmoker
var camera: Camera3D
var status: BodyStatus
var loadout: BodyLoadout
var colors: BodyColors
var map_index: int = 0
## 0 = the main framing, 1 = the loadout framing (eased between).
var framing: float = 0.0
var _framing_to: float = 0.0
var _clock: float = 0.0
var _starting: bool = false
var _ui: CanvasLayer
var _panel: Control
var _list: VBoxContainer
var _buttons: Dictionary[String, Button] = {}
var _summary: Label
var _black: ColorRect


func _ready() -> void:
	add_to_group(&"main_menu")
	# The debug numbers stay out of the menu's picture (back on Begin).
	DebugOverlay.visible = false
	config = load(CONFIG_PATH) as MenuSceneConfig
	loadout = LoadoutStore.load_saved(DEFAULT_LOADOUT)
	colors = LoadoutStore.load_colors()
	smoker = MenuSmoker.new()
	smoker.name = "Operative"
	smoker.config = config
	add_child(smoker)
	smoker.global_position = config.figure_position
	smoker.rotation.y = deg_to_rad(config.figure_yaw_deg)
	smoker.appearance.loadout = loadout
	smoker.appearance.colors = colors
	smoker.appearance.rebuild()
	camera = Camera3D.new()
	camera.name = "MenuCam"
	camera.fov = config.fov
	camera.near = 0.05
	add_child(camera)
	camera.current = true
	camera.add_to_group(&"capture_cameras")
	_place_camera()
	_build_key_light()
	_build_ui()
	status = BodyStatus.new()
	add_child(status)
	status.closed.connect(_on_loadout_closed)
	_refresh()
	_focus.call_deferred()
	# Cloud captures: --capture-menu-loadout opens the loadout screen;
	# --capture-menu-preset=N also puts the cursor on preset N (he wears it);
	# --pose-t=<s> holds his cigarette cycle at that time.
	for a: String in OS.get_cmdline_user_args():
		if a == "--capture-menu-loadout":
			open_loadout.call_deferred()
		elif a.begins_with("--pose-t="):
			smoker.hold_t = a.get_slice("=", 1).to_float()
		elif a.begins_with("--capture-menu-preset="):
			var n: int = a.get_slice("=", 1).to_int()
			(func() -> void:
				open_loadout()
				status.select_preset(n)).call_deferred()


func _exit_tree() -> void:
	DebugOverlay.visible = true


func _build_key_light() -> void:
	var key: SpotLight3D = SpotLight3D.new()
	key.name = "MenuKey"
	key.light_color = config.key_color
	key.light_energy = config.key_energy
	key.spot_range = 7.0
	key.spot_angle = 28.0
	key.spot_attenuation = 0.8
	key.light_cull_mask = 0xFFFFF & ~ChinatownMap.MAP_LAYER
	key.light_specular = 0.7
	add_child(key)
	key.look_at_from_position(config.key_position, config.figure_position + Vector3.UP * 1.3)


# ------------------------------------------------------------------ camera

func _place_camera() -> void:
	var k: float = framing * framing * (3.0 - 2.0 * framing)
	var pos: Vector3 = config.main_cam_position.lerp(config.loadout_cam_position, k)
	var look: Vector3 = config.main_cam_target.lerp(config.loadout_cam_target, k)
	var dr: float = config.cam_drift
	pos += Vector3(sin(_clock * 0.21) * dr, sin(_clock * 0.17 + 1.0) * dr * 0.5, cos(_clock * 0.13) * dr)
	camera.look_at_from_position(pos, look)
	smoker.look_from = camera.global_position


func _process(delta: float) -> void:
	_clock += delta
	if not is_equal_approx(framing, _framing_to):
		framing = move_toward(framing, _framing_to, delta / maxf(config.cam_move_time, 0.05))
	_place_camera()
	# Back from Options (the pause menu) or the loadout: the cursor on the list.
	if _panel.visible and not _starting and get_viewport().gui_get_focus_owner() == null and not PauseMenu.is_open():
		_focus()


# ------------------------------------------------------------------ UI

func _build_ui() -> void:
	_ui = CanvasLayer.new()
	_ui.layer = 40
	add_child(_ui)
	_panel = Control.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.add_child(_panel)
	# A dark wash on the left so the text reads over the street.
	var wash: TextureRect = TextureRect.new()
	var g: Gradient = Gradient.new()
	g.set_color(0, Color(0.01, 0.012, 0.016, 0.82))
	g.set_color(1, Color(0.01, 0.012, 0.016, 0.0))
	var gt: GradientTexture2D = GradientTexture2D.new()
	gt.gradient = g
	gt.width = 128
	gt.height = 4
	wash.texture = gt
	wash.stretch_mode = TextureRect.STRETCH_SCALE
	wash.anchor_right = 0.5
	wash.anchor_bottom = 1.0
	wash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(wash)
	var box: VBoxContainer = VBoxContainer.new()
	box.anchor_left = 0.0
	box.anchor_top = 0.0
	box.anchor_bottom = 1.0
	box.offset_left = 64.0
	box.offset_top = 56.0
	box.offset_bottom = -40.0
	box.offset_right = 520.0
	box.add_theme_constant_override("separation", 4)
	_panel.add_child(box)
	var title: Label = Label.new()
	title.text = "GRAFT"
	var fv: FontVariation = FontVariation.new()
	fv.base_font = ThemeDB.fallback_font
	fv.spacing_glyph = 10
	fv.variation_embolden = 0.6
	title.add_theme_font_override("font", fv)
	title.add_theme_font_size_override("font_size", 64)
	title.add_theme_color_override("font_color", C_TEXT)
	box.add_child(title)
	var sub: Label = Label.new()
	sub.text = "AUGMENTED INFANTRY  ·  PROTOTYPE"
	sub.add_theme_font_size_override("font_size", 14)
	sub.add_theme_color_override("font_color", C_ACCENT)
	box.add_child(sub)
	var gap: Control = Control.new()
	gap.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(gap)
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 2)
	box.add_child(_list)
	_add("begin", "BEGIN", begin)
	_add("loadout", "LOADOUT", open_loadout)
	_add("map", "MAP", func() -> void: cycle_map(1))
	_buttons["map"].gui_input.connect(_on_map_input)
	_add("options", "OPTIONS", _on_options)
	_add("quit", "QUIT", func() -> void: get_tree().quit())
	var gap2: Control = Control.new()
	gap2.custom_minimum_size = Vector2(0, 18)
	box.add_child(gap2)
	_summary = Label.new()
	_summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_summary.add_theme_font_size_override("font_size", 14)
	_summary.add_theme_color_override("font_color", C_DIM)
	box.add_child(_summary)
	var gap3: Control = Control.new()
	gap3.size_flags_vertical = Control.SIZE_EXPAND_FILL
	gap3.size_flags_stretch_ratio = 0.4
	box.add_child(gap3)
	var hints: Label = Label.new()
	hints.text = "A  select      D-pad  move      ◀ ▶  change map      View  loadout"
	hints.add_theme_font_size_override("font_size", 13)
	hints.add_theme_color_override("font_color", C_DIM)
	box.add_child(hints)
	_black = ColorRect.new()
	_black.color = Color(0, 0, 0, 0)
	_black.set_anchors_preset(Control.PRESET_FULL_RECT)
	_black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.add_child(_black)


func _add(id: String, text: String, cb: Callable) -> void:
	var b: Button = Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(380, 46)
	b.add_theme_font_size_override("font_size", 22)
	b.add_theme_color_override("font_color", C_TEXT)
	b.add_theme_color_override("font_focus_color", Color.WHITE)
	b.add_theme_color_override("font_hover_color", Color.WHITE)
	var plain: StyleBoxFlat = StyleBoxFlat.new()
	plain.bg_color = Color(0, 0, 0, 0)
	plain.content_margin_left = 18
	var lit: StyleBoxFlat = StyleBoxFlat.new()
	lit.bg_color = Color(C_ACCENT.r, C_ACCENT.g, C_ACCENT.b, 0.16)
	lit.border_color = C_ACCENT
	lit.border_width_left = 4
	lit.content_margin_left = 18
	b.add_theme_stylebox_override("normal", plain)
	b.add_theme_stylebox_override("hover", lit)
	b.add_theme_stylebox_override("focus", lit)
	b.add_theme_stylebox_override("pressed", lit)
	b.pressed.connect(cb)
	b.mouse_entered.connect(b.grab_focus)
	_list.add_child(b)
	_buttons[id] = b


func _focus() -> void:
	if _panel.visible and is_inside_tree():
		_buttons["begin"].grab_focus()


func map_path() -> String:
	var p: String = MAPS[map_index][0]
	return p


func map_name() -> String:
	var n: String = MAPS[map_index][1]
	return n


func _refresh() -> void:
	_buttons["map"].text = "MAP   ◀  %s  ▶" % map_name().to_upper()
	var acts: Array[String] = []
	for a: ActivePartData in loadout.actives():
		acts.append(a.display_name)
	_summary.text = "%s  ·  %d parts\n%s" % [loadout.display_name, loadout.parts.size(),
			"  ·  ".join(acts) if not acts.is_empty() else "no actives"]


func _on_map_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"ui_left") or event.is_action_pressed(&"ui_right"):
		cycle_map(1 if event.is_action_pressed(&"ui_right") else -1)
		_buttons["map"].accept_event()


func cycle_map(step: int) -> void:
	map_index = posmod(map_index + step, MAPS.size())
	_refresh()


func _on_options() -> void:
	PauseMenu.open_options()


func _unhandled_input(event: InputEvent) -> void:
	if _starting or not _panel.visible:
		return
	if event.is_action_pressed(&"body_status"):
		open_loadout()
		get_viewport().set_input_as_handled()


# ------------------------------------------------------------------ loadout and begin

func open_loadout() -> void:
	if status.visible or _starting:
		return
	_panel.visible = false
	_framing_to = 1.0
	status.open_for_menu(smoker.appearance, loadout, colors)


func _on_loadout_closed() -> void:
	loadout = status.menu_loadout()
	colors = status.menu_colors()
	_panel.visible = true
	_framing_to = 0.0
	_refresh()
	_focus()


func begin() -> void:
	if _starting:
		return
	_starting = true
	get_viewport().gui_release_focus()
	var tw: Tween = create_tween()
	tw.tween_property(_black, "color:a", 1.0, 0.45)
	tw.tween_callback(func() -> void: begin_requested.emit(map_path()))
