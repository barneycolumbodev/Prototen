class_name BodyStatus
extends CanvasLayer
## Body status and loadout (View button, CLAUDE.md §9.4; also Pause → Body
## status; docs/design.md §3.6). Left: the operative on a turntable, wearing
## whatever is being previewed. Middle: every part laid out at once (owner,
## 2026-11-11: "all the options laid out and you can just click on the one
## you want"): the presets, the nine actives, then the passives row by row
## under their body location. Right: the selected part's card (what it does,
## what it costs, what it needs and which parts supply that) and the whole
## stat sheet with the change it would make.
##
## Controls: the D-pad or the stick moves over the tiles (the body and every
## number preview the one under the cursor); A installs it, or takes it out
## if it's in (a preset: applies it); X moves an installed active to the next
## D-pad direction; RB jumps to a part that supplies what the selected part
## (or an offline one) is missing; Y helmet; LT zoom; RS turns the model; B or
## View closes and puts the loadout on the player (saved for next time).
## Touch: tap a tile to select it, tap it again (or the button under the
## card) to install or remove; tap a part named in the card to go to it.
##
## LB switches to the Colours page (docs/design.md §3.7): one row per suit
## piece and per installed part with hardware. Left/right steps through the
## palette, A opens the sliders (hue, saturation, brightness, finish), X
## puts the piece back the way it was built.

const STUDIO_SKY: Shader = preload("res://src/ui/studio_sky.gdshader")
## Passive rows, top to bottom.
const ORDER: Array[int] = [
	PartData.Location.HEAD, PartData.Location.EYES, PartData.Location.EARS,
	PartData.Location.NERVOUS, PartData.Location.SKELETON, PartData.Location.MUSCLE, PartData.Location.ORGANS,
	PartData.Location.TORSO, PartData.Location.ARMS, PartData.Location.HANDS, PartData.Location.LEGS,
	PartData.Location.SPINE, PartData.Location.BACK, PartData.Location.SKIN, PartData.Location.BLOOD,
]
## Tiles per row in the grid.
const COLUMNS: int = 4
enum Page { LOADOUT, COLOURS }
const SLIDERS: Array[String] = ["Hue", "Saturation", "Brightness", "Finish"]
const C_GOOD: String = "#5cdcc6"
const C_BAD: String = "#e0705a"
const C_DIM: String = "#7d8b8b"
const C_NAME: String = "#ffd28a"
const C_OFF: String = "#9a9fa3"
const C_ACTIVE: String = "#ffb054"
const C_FIX: String = "#ffd040"

var player: Player
var appearance: BodyAppearance
var library: PartLibrary = LoadoutStore.LIBRARY
## The loadout being built (applied to the player on close).
var working: BodyLoadout
## What the selection would make of it, and its numbers.
var preview: BodyLoadout
var preview_body: BodyModel
var working_body: BodyModel
## The tile under the cursor: a part id, or a preset (selected_preset >= 0).
var selected: StringName = &""
var selected_preset: int = -1
var changed: bool = false
## Which page is showing, and the Colours page's state.
var page: Page = Page.LOADOUT
var working_colors: BodyColors
var colors_changed: bool = false
var color_row: int = 0
## The sliders are open on the channel under the cursor.
var editing: bool = false
var slider: int = 0
var _channels: Array[StringName] = []
var _channel_labels: Array[String] = []

var _presets: Array[BodyLoadout] = []
var _viewport: SubViewport
var _pivot: Node3D
var _cam: Camera3D
## 0 = whole body, 1 = close on the upper body (LT held).
var zoom: float = 0.0
var _zoom_held: bool = false
## Right stick turns the model; the turntable resumes when it's let go.
var _manual_turn: float = 0.0
## Colours page text (the loadout page uses the grid).
var _list: RichTextLabel
var _list_box: MarginContainer
var _text: RichTextLabel
var _grid_page: Control
var _scroll: ScrollContainer
var _header: RichTextLabel
var _tiles: Dictionary[StringName, Button] = {}
var _preset_tiles: Array[Button] = []
## Parts that would fix what the selection is missing (outlined in the grid).
var fix_ids: Array[StringName] = []
var _act_button: Button
var _button_bar: HBoxContainer
var _jump_button: Button
## A tile selected by this very tap (touch): the tap selects, the next one acts.
var _tap_selected: String = ""
## When the cursor last moved to a tile (process frame): a press in the same
## frame is the press that selected it.
var _focus_frame: int = -1
var _styles: Dictionary[String, StyleBoxFlat] = {}
var _building: bool = false


func _ready() -> void:
	layer = 105  # above the debug overlay
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	_presets = LoadoutStore.presets()
	_make_styles()
	var bg: ColorRect = ColorRect.new()
	bg.color = Color(0.02, 0.025, 0.03, 0.95)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var row_box: HBoxContainer = HBoxContainer.new()
	row_box.set_anchors_preset(Control.PRESET_FULL_RECT)
	row_box.add_theme_constant_override("separation", 10)
	add_child(row_box)
	var svc: SubViewportContainer = SubViewportContainer.new()
	svc.stretch = true
	svc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	svc.size_flags_stretch_ratio = 0.45
	svc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row_box.add_child(svc)
	_viewport = SubViewport.new()
	_viewport.own_world_3d = true
	_viewport.transparent_bg = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_WHEN_VISIBLE
	svc.add_child(_viewport)
	# Middle: the grid (loadout) or the colour list.
	var middle: Control = Control.new()
	middle.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	middle.size_flags_vertical = Control.SIZE_EXPAND_FILL
	middle.size_flags_stretch_ratio = 1.3
	row_box.add_child(middle)
	_grid_page = _build_grid()
	_grid_page.set_anchors_preset(Control.PRESET_FULL_RECT)
	middle.add_child(_grid_page)
	_list = _label(14)
	_list_box = _margin(_list, 1.0)
	_list_box.set_anchors_preset(Control.PRESET_FULL_RECT)
	middle.add_child(_list_box)
	# Right: the card and the stat sheet, with touch buttons under it.
	var right: VBoxContainer = VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.size_flags_stretch_ratio = 0.85
	row_box.add_child(right)
	_text = _label(12)
	_text.meta_clicked.connect(_on_meta)
	right.add_child(_margin(_text, 1.0))
	var buttons: HBoxContainer = HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 6)
	right.add_child(buttons)
	_button_bar = buttons
	_act_button = _bar_button("A  Install", activate)
	buttons.add_child(_act_button)
	_jump_button = _bar_button("RB  Go to fix", func() -> void: jump_to_fix())
	buttons.add_child(_jump_button)
	buttons.add_child(_bar_button("B  Done", close))
	var pad: Control = Control.new()
	pad.custom_minimum_size = Vector2(0, 6)
	right.add_child(pad)


func _label(size: int) -> RichTextLabel:
	var l: RichTextLabel = RichTextLabel.new()
	l.bbcode_enabled = true
	l.fit_content = false
	l.scroll_active = false
	l.add_theme_font_size_override("normal_font_size", size)
	l.add_theme_font_size_override("bold_font_size", size + 1)
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	l.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return l


func _margin(c: Control, ratio: float) -> MarginContainer:
	var m: MarginContainer = MarginContainer.new()
	m.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	m.size_flags_vertical = Control.SIZE_EXPAND_FILL
	m.size_flags_stretch_ratio = ratio
	m.add_theme_constant_override("margin_top", 14)
	m.add_theme_constant_override("margin_bottom", 4)
	m.add_theme_constant_override("margin_right", 14)
	m.add_child(c)
	return m


func _bar_button(text: String, cb: Callable) -> Button:
	var b: Button = Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.custom_minimum_size = Vector2(0, 40)
	b.add_theme_font_size_override("font_size", 13)
	b.add_theme_stylebox_override("normal", _styles["bar"])
	b.add_theme_stylebox_override("hover", _styles["bar"])
	b.add_theme_stylebox_override("pressed", _styles["installed"])
	b.pressed.connect(cb)
	return b


func _make_styles() -> void:
	var spec: Dictionary[String, Array] = {
		# fill, border, border width
		"empty": [Color(0.07, 0.08, 0.085), Color(0.16, 0.18, 0.19), 1],
		"installed": [Color(0.07, 0.24, 0.22), Color(0.36, 0.86, 0.78), 1],
		"offline": [Color(0.24, 0.08, 0.06), Color(0.88, 0.44, 0.35), 1],
		"fix": [Color(0.2, 0.17, 0.04), Color(1.0, 0.82, 0.25), 2],
		"focus": [Color(0, 0, 0, 0), Color(1, 1, 1, 0.95), 2],
		"bar": [Color(0.09, 0.11, 0.12), Color(0.3, 0.36, 0.37), 1],
		"locked": [Color(0.05, 0.05, 0.055), Color(0.12, 0.12, 0.13), 1],
	}
	for k: String in spec:
		var sb: StyleBoxFlat = StyleBoxFlat.new()
		var fill: Color = spec[k][0]
		var edge: Color = spec[k][1]
		var width: int = spec[k][2]
		sb.bg_color = fill
		sb.border_color = edge
		sb.set_border_width_all(width)
		sb.set_corner_radius_all(3)
		sb.content_margin_left = 6
		sb.content_margin_right = 4
		sb.content_margin_top = 2
		sb.content_margin_bottom = 2
		if k == "focus":
			sb.expand_margin_left = 1
			sb.expand_margin_right = 1
			sb.expand_margin_top = 1
			sb.expand_margin_bottom = 1
		_styles[k] = sb


## The tile grid: header, presets, actives, then a row per body location.
func _build_grid() -> Control:
	var outer: MarginContainer = MarginContainer.new()
	outer.add_theme_constant_override("margin_top", 10)
	outer.add_theme_constant_override("margin_bottom", 6)
	var v: VBoxContainer = VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	outer.add_child(v)
	_header = _label(13)
	_header.fit_content = true
	_header.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	v.add_child(_header)
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.follow_focus = true
	v.add_child(_scroll)
	var rows: VBoxContainer = VBoxContainer.new()
	rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rows.add_theme_constant_override("separation", 3)
	_scroll.add_child(rows)
	# Presets.
	var preset_ids: Array[String] = []
	for i: int in _presets.size():
		preset_ids.append("preset:%d" % i)
	_add_rows(rows, "Presets", preset_ids, C_NAME)
	# Actives (any three, on the D-pad).
	var act_ids: Array[String] = []
	for a: ActivePartData in library.actives():
		act_ids.append(String(a.id))
	_add_rows(rows, "Actives  LB", act_ids, C_ACTIVE)
	for loc: int in ORDER:
		var ids: Array[String] = []
		for p: PartData in library.at(loc):
			if not p.is_active() and not p.fixed:
				ids.append(String(p.id))
		if not ids.is_empty():
			_add_rows(rows, PartData.location_name(loc), ids, C_DIM)
	return outer


func _add_rows(parent: VBoxContainer, title: String, ids: Array[String], color: String) -> void:
	var i: int = 0
	while i < ids.size():
		var h: HBoxContainer = HBoxContainer.new()
		h.add_theme_constant_override("separation", 4)
		parent.add_child(h)
		var lab: Label = Label.new()
		lab.text = title if i == 0 else ""
		lab.custom_minimum_size = Vector2(104, 0)
		lab.clip_text = true
		lab.add_theme_font_size_override("font_size", 12)
		lab.add_theme_color_override("font_color", Color.html(color))
		lab.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		h.add_child(lab)
		for c: int in COLUMNS:
			if i + c < ids.size():
				h.add_child(_make_tile(ids[i + c]))
			else:
				var gap: Control = Control.new()
				gap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
				gap.mouse_filter = Control.MOUSE_FILTER_IGNORE
				h.add_child(gap)
		i += COLUMNS


func _make_tile(key: String) -> Button:
	var b: Button = Button.new()
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.custom_minimum_size = Vector2(60, 28)
	b.clip_text = true
	b.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.focus_mode = Control.FOCUS_ALL
	b.add_theme_font_size_override("font_size", 12)
	b.add_theme_stylebox_override("focus", _styles["focus"])
	b.focus_entered.connect(_on_tile_focus.bind(key))
	b.pressed.connect(_on_tile_pressed.bind(key))
	b.gui_input.connect(_on_tile_input.bind(key))
	if key.begins_with("preset:"):
		var pi: int = key.get_slice(":", 1).to_int()
		b.text = _presets[pi].display_name
		_preset_tiles.append(b)
	else:
		var p: PartData = library.find(StringName(key))
		b.text = p.display_name
		b.tooltip_text = PartData.location_name(p.location)
		_tiles[StringName(key)] = b
	return b


func _build_stage() -> void:
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.25, 0.28, 0.33)
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true
	# A studio sky that is only reflected (the background stays transparent):
	# softbox strips give the gloss plates their highlights.
	var sky_mat: ShaderMaterial = ShaderMaterial.new()
	sky_mat.shader = STUDIO_SKY
	env.sky = Sky.new()
	env.sky.sky_material = sky_mat
	env.sky.radiance_size = Sky.RADIANCE_SIZE_128
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	var we: WorldEnvironment = WorldEnvironment.new()
	we.environment = env
	_viewport.add_child(we)
	_cam = Camera3D.new()
	_cam.fov = 30.0
	_viewport.add_child(_cam)
	_place_camera()
	# Key (warm, front right), two cool rims from behind, a faint fill.
	for spec: Array in [[Vector3(-35, 35, 0), Color(1.0, 0.94, 0.87), 0.5], [Vector3(-20, 145, 0), Color(0.55, 0.85, 1.0), 0.75],
			[Vector3(-15, -140, 0), Color(0.8, 0.9, 1.0), 0.55], [Vector3(-5, -50, 0), Color(0.85, 0.85, 1.0), 0.1]]:
		var l: DirectionalLight3D = DirectionalLight3D.new()
		l.rotation_degrees = spec[0]
		l.light_color = spec[1]
		l.light_energy = spec[2]
		_viewport.add_child(l)
	_pivot = Node3D.new()
	_viewport.add_child(_pivot)
	appearance = BodyAppearance.new()
	_pivot.add_child(appearance)
	var floor_mesh: MeshInstance3D = MeshInstance3D.new()
	var disc: CylinderMesh = CylinderMesh.new()
	disc.top_radius = 0.6
	disc.bottom_radius = 0.62
	disc.height = 0.03
	floor_mesh.mesh = disc
	var fm: StandardMaterial3D = StandardMaterial3D.new()
	fm.albedo_color = Color(0.05, 0.055, 0.06)
	fm.roughness = 0.3
	fm.emission_enabled = true
	fm.emission = Color(0.36, 0.86, 0.78) * 0.08
	floor_mesh.material_override = fm
	floor_mesh.position.y = -0.015
	_viewport.add_child(floor_mesh)


func is_open() -> bool:
	return visible


func open() -> void:
	if player == null:
		return
	if appearance == null:
		_build_stage()
	working = player.loadout.copy()
	working_colors = player.colors.copy() if player.colors else BodyColors.new()
	appearance.colors = working_colors
	colors_changed = false
	editing = false
	changed = false
	page = Page.LOADOUT
	# Start where the trouble is: an offline part (the HUD said it needs
	# something), else the first active installed, else where we were.
	var wb: BodyModel = BodyModel.new(player.body_config, working)
	var start: StringName = selected
	for p: PartData in working.parts:
		if wb.offline.has(p.id):
			start = p.id
			break
	if start == &"" or not _tiles.has(start):
		var acts: Array[ActivePartData] = working.actives()
		start = acts[0].id if not acts.is_empty() else library.actives()[0].id
	visible = true
	get_tree().paused = true
	select_part(start)
	_pivot.rotation.y = 0.35


## Holds the close-up (cloud captures; LT does it in play).
func set_zoom(on: bool) -> void:
	_zoom_held = on
	zoom = 1.0 if on else 0.0
	_place_camera()


## Turns the model on its turntable (cloud captures).
func set_yaw(rad: float) -> void:
	if _pivot:
		_pivot.rotation.y = rad


## Helmet off (the operative's face) or back on.
func toggle_helmet() -> void:
	if appearance:
		appearance.helmet_on = not appearance.helmet_on


func close() -> void:
	visible = false
	get_tree().paused = false
	if changed and player:
		player.apply_loadout(working)
		LoadoutStore.save(working)
	changed = false
	if colors_changed and player:
		player.set_colors(working_colors)
		LoadoutStore.save_colors(working_colors)
	colors_changed = false


## Whole body, or (zoom 1) close on the chest and shoulders.
func _place_camera() -> void:
	if _cam == null:
		return
	var z: float = zoom * zoom * (3.0 - 2.0 * zoom)
	var pos: Vector3 = Vector3(0, 1.02, 5.6).lerp(Vector3(0, 1.36, 2.15), z)
	var look: Vector3 = Vector3(0, 0.98, 0).lerp(Vector3(0, 1.3, 0), z)
	_cam.look_at_from_position(pos, look)


func _process(delta: float) -> void:
	if not visible or _pivot == null:
		return
	var real: float = TimeControl.real_delta(delta) if not get_tree().paused else delta
	var want: float = 1.0 if _zoom_held or Input.is_action_pressed(&"aim") else 0.0
	if not is_equal_approx(zoom, want):
		zoom = move_toward(zoom, want, real * 3.0)
		_place_camera()
	var turn: float = Input.get_axis(&"look_left", &"look_right")
	if absf(turn) > 0.2:
		_pivot.rotation.y += turn * real * 2.5
		_manual_turn = 2.0
	elif _manual_turn > 0.0:
		_manual_turn -= real
	elif not CaptureDirector.is_capturing():
		# Cloud screenshots hold the view they were given.
		_pivot.rotation.y += real * 0.6


func _input(event: InputEvent) -> void:
	if event.is_action_pressed(&"body_status"):
		if visible:
			close()
		elif not get_tree().paused:
			open()
		get_viewport().set_input_as_handled()
		return
	if not visible:
		return
	var handled: bool = true
	if event.is_action_pressed(&"active_use"):
		set_page(Page.COLOURS if page == Page.LOADOUT else Page.LOADOUT)
	elif page == Page.COLOURS:
		handled = _colour_input(event)
	elif event.is_action_pressed(&"switch_weapon"):
		toggle_helmet()
	elif event.is_action_pressed(&"ui_cancel") or event.is_action_pressed(&"pause"):
		close()
	elif event.is_action_pressed(&"menu_jump"):
		jump_to_fix()
	elif event.is_action_pressed(&"reload"):
		secondary()
	else:
		# The D-pad, the stick and A go to the tiles (focus and press).
		handled = false
	if handled:
		get_viewport().set_input_as_handled()


# ------------------------------------------------------------------ editing

## Puts the cursor on a part's tile (the body and the numbers preview it).
## Returns whether the part is on the screen.
func select_part(id: StringName) -> bool:
	if not _tiles.has(id):
		return false
	selected = id
	selected_preset = -1
	var b: Button = _tiles[id]
	if visible and b.is_inside_tree() and not b.has_focus():
		_building = true
		b.grab_focus()
		_building = false
	_refresh()
	return true


## Puts the cursor on a preset.
func select_preset(i: int) -> void:
	if i < 0 or i >= _presets.size():
		return
	selected_preset = i
	selected = &""
	var b: Button = _preset_tiles[i]
	if visible and b.is_inside_tree() and not b.has_focus():
		_building = true
		b.grab_focus()
		_building = false
	_refresh()


## The part under the cursor (null on a preset).
func selected_part() -> PartData:
	return library.find(selected) if selected != &"" else null


func _on_tile_focus(key: String) -> void:
	if _building:
		return
	_focus_frame = Engine.get_process_frames()
	if key.begins_with("preset:"):
		select_preset(key.get_slice(":", 1).to_int())
	else:
		select_part(StringName(key))
	Sfx.play_ui(&"wheel_tick", -12.0, 0.02)


## A finger or mouse coming down on a tile that this same press just moved
## the cursor to: it only selects (the press is let through to the button,
## and _on_tile_pressed ignores it).
func _on_tile_input(event: InputEvent, key: String) -> void:
	var down: bool = false
	var mb: InputEventMouseButton = event as InputEventMouseButton
	if mb and mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
		down = true
	var touch: InputEventScreenTouch = event as InputEventScreenTouch
	if touch and touch.pressed:
		down = true
	if down and _focus_frame == Engine.get_process_frames():
		_tap_selected = key


func _on_tile_pressed(key: String) -> void:
	if _tap_selected == key:
		# This tap only selected it; the next one acts.
		_tap_selected = ""
		return
	_tap_selected = ""
	activate()


func _on_meta(meta: Variant) -> void:
	var id: StringName = StringName(str(meta))
	if select_part(id):
		Sfx.play_ui(&"wheel_tick", -8.0, 0.02)


## A: install the selected part, or take it out if it's in; on a preset,
## apply the preset.
func activate() -> void:
	if selected_preset >= 0:
		working = _presets[selected_preset].copy()
		changed = true
		Sfx.play_ui(&"draw", -6.0)
		_refresh()
		return
	var p: PartData = selected_part()
	if p == null or p.fixed:
		return
	if working.has_part(p.id):
		working.remove(p.id)
		Sfx.play_ui(&"holster", -6.0)
	else:
		working.install(p)
		Sfx.play_ui(&"draw", -6.0)
	working.display_name = "Custom"
	changed = true
	_refresh()


## X: an installed active moves to the next D-pad direction; any other
## installed part comes out.
func secondary() -> void:
	var p: PartData = selected_part()
	if p == null or not working.has_part(p.id):
		return
	if p.is_active() and working.actives().size() >= 2:
		working.cycle_slot(p.id)
		Sfx.play_ui(&"wheel_tick", -6.0)
	elif not p.fixed:
		working.remove(p.id)
		Sfx.play_ui(&"holster", -6.0)
	else:
		return
	working.display_name = "Custom"
	changed = true
	_refresh()


## Takes the selected part out (tests and X).
func remove_selected() -> bool:
	var p: PartData = selected_part()
	if p and working.remove(p.id):
		working.display_name = "Custom"
		changed = true
		_refresh()
		return true
	return false


## Loadout or Colours.
func set_page(p: Page) -> void:
	page = p
	editing = false
	Sfx.play_ui(&"wheel_tick", -8.0, 0.02)
	_refresh()
	if page == Page.LOADOUT:
		if selected_preset >= 0:
			select_preset(selected_preset)
		elif selected != &"":
			select_part(selected)


# ------------------------------------------------------------------ what fixes it

## Parts in `lib` that raise (or, for an upper limit, lower) `stat`,
## strongest first.
static func providers(lib: PartLibrary, req: StatRequirement) -> Array[PartData]:
	var want_up: bool = req.at_least > -INF
	var scored: Array[Array] = []
	var base: float = Stats.default_base(req.stat)
	for p: PartData in lib.parts:
		if p == null or p.fixed:
			continue
		for m: StatModifier in p.modifiers:
			if m.stat != req.stat:
				continue
			var gain: float = (base + m.add) * m.mul - base
			if (gain > 0.0001 and want_up) or (gain < -0.0001 and not want_up):
				scored.append([absf(gain), p])
	scored.sort_custom(func(a: Array, b: Array) -> bool: return a[0] > b[0])
	var out: Array[PartData] = []
	for e: Array in scored:
		out.append(e[1])
	return out


## Short hint for the HUD: which parts supply what `p` is missing on body
## `b` ("fit SA-2 or TG-6"). Empty if nothing is missing.
static func fix_hint(lib: PartLibrary, p: PartData, b: BodyModel) -> String:
	var names: PackedStringArray = PackedStringArray()
	for r: StatRequirement in p.requirements:
		if r == null or r.met(b.stat(r.stat)):
			continue
		for q: PartData in providers(lib, r):
			var code: String = q.display_name.get_slice(" ", 0)
			if not names.has(code) and names.size() < 3:
				names.append(code)
	return "" if names.is_empty() else "fit " + " or ".join(names)


## The part RB goes to: one that supplies what the selection is missing
## (else what an offline part is missing). One that fixes it on its own
## first, then the strongest; one that's already in (but offline) last.
func fix_target() -> StringName:
	var p: PartData = selected_part()
	var body: BodyModel = preview_body if preview_body else working_body
	var who: PartData = null
	if p and body and body.unmet(p) != "":
		who = p
	elif working_body:
		for q: PartData in working.parts:
			if working_body.offline.has(q.id):
				who = q
				break
	if who == null:
		return &""
	var fallback: StringName = &""
	for r: StatRequirement in who.requirements:
		if r == null or r.met(body.stat(r.stat)):
			continue
		var first: StringName = &""
		for q: PartData in providers(library, r):
			if working.has_part(q.id):
				if fallback == &"":
					fallback = q.id
				continue
			if first == &"":
				first = q.id
			var lo: BodyLoadout = working.copy()
			if not working.has_part(who.id):
				lo.install(who)
			lo.install(q)
			var tb: BodyModel = BodyModel.new(player.body_config, lo)
			if r.met(tb.stat(r.stat)):
				return q.id
		if first != &"":
			return first
	return fallback


## RB: go to the part that fixes it. Returns where it went (&"" = nowhere).
func jump_to_fix() -> StringName:
	var to: StringName = fix_target()
	if to != &"":
		select_part(to)
		Sfx.play_ui(&"wheel_tick", -6.0, 0.02)
	return to


## The loadout with the selection on it: a preset as it is; a part that
## isn't in yet, installed (what it would replace comes out).
func _make_preview() -> BodyLoadout:
	if page == Page.COLOURS:
		return working.copy()
	if selected_preset >= 0:
		return _presets[selected_preset].copy()
	var lo: BodyLoadout = working.copy()
	var p: PartData = selected_part()
	if p and not working.has_part(p.id):
		lo.install(p)
	return lo


func _refresh() -> void:
	if working == null or player == null:
		return
	working_body = BodyModel.new(player.body_config, working)
	preview = _make_preview()
	preview_body = BodyModel.new(player.body_config, preview)
	preview_body.heat_j = player.body.heat_j
	if appearance:
		appearance.loadout = preview
		appearance.colors = working_colors
		appearance.rebuild()
	_grid_page.visible = page == Page.LOADOUT
	_list_box.visible = page == Page.COLOURS
	_button_bar.visible = page == Page.LOADOUT
	if page == Page.COLOURS:
		_build_channels()
		_list.text = _colour_list_text()
		_text.text = _colour_card()
		return
	_update_fix_ids()
	_paint_tiles()
	_header.text = _header_text()
	_text.text = describe(preview_body, working_body, _card())
	var p: PartData = selected_part()
	if selected_preset >= 0:
		_act_button.text = "A  Apply preset"
	elif p and working.has_part(p.id):
		_act_button.text = "A  Remove" if not p.fixed else "Built in"
	else:
		_act_button.text = "A  Install"
	_jump_button.disabled = fix_ids.is_empty()


func _update_fix_ids() -> void:
	fix_ids.clear()
	var p: PartData = selected_part()
	if p == null or preview_body == null or preview_body.unmet(p) == "":
		return
	for r: StatRequirement in p.requirements:
		if r and not r.met(preview_body.stat(r.stat)):
			for q: PartData in providers(library, r):
				if not fix_ids.has(q.id):
					fix_ids.append(q.id)


## Colours and badges: installed (teal), installed but offline (red), a part
## that would fix the selection (amber outline); actives show their D-pad
## direction.
func _paint_tiles() -> void:
	for id: StringName in _tiles:
		var b: Button = _tiles[id]
		var p: PartData = library.find(id)
		var inn: bool = working.has_part(id)
		var style: String = "empty"
		if fix_ids.has(id):
			style = "fix"
		elif inn and working_body.offline.has(id):
			style = "offline"
		elif inn:
			style = "installed"
		for st: String in ["normal", "hover", "pressed", "disabled"]:
			b.add_theme_stylebox_override(st, _styles[style])
		var label: String = p.display_name
		if p.is_active() and inn:
			label = "%s %s" % [Augments.SLOT_ARROWS[working.slot_of(id) - 1], label]
		elif inn:
			label = "+ " + label
		b.text = label
		var col: Color = Color.html("#ffffff") if inn else Color.html("#aeb6b7")
		if p.is_active() and not inn:
			col = Color.html(C_ACTIVE)
		if style == "fix":
			col = Color.html(C_FIX)
		for c: String in ["font_color", "font_hover_color", "font_focus_color", "font_pressed_color"]:
			b.add_theme_color_override(c, col)
	for i: int in _preset_tiles.size():
		var b: Button = _preset_tiles[i]
		var same: bool = _presets[i].ids() == working.ids()
		for st: String in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(st, _styles["installed" if same else "bar"])
		b.add_theme_color_override("font_color", Color.html(C_NAME))
		b.add_theme_color_override("font_focus_color", Color.html(C_NAME))


func _header_text() -> String:
	var acts: PackedStringArray = PackedStringArray()
	for a: ActivePartData in working.actives():
		var off: bool = working_body.offline.has(a.id)
		acts.append("[color=%s]%s %s[/color]" % [C_BAD if off else C_ACTIVE, Augments.SLOT_ARROWS[working.slot_of(a.id) - 1], a.display_name.get_slice(" ", 0)])
	var off_n: int = working_body.offline.size()
	var warn: String = "   [color=%s]%d offline: RB finds the fix[/color]" % [C_BAD, off_n] if off_n > 0 else ""
	return "[b]LOADOUT[/b]  [color=%s]%s[/color]   [color=%s]capacity %d / %d · %.0f kg[/color]   %s%s\n[color=%s]D-pad: move   A: install / remove   X: active's D-pad slot   RB: go to fix   LB: colours   Y: helmet   B: done[/color]" % [
		C_NAME, working.display_name, C_DIM, working_body.capacity_used, working_body.capacity_total(), working_body.mass_kg,
		"  ".join(acts), warn, C_DIM]


# ------------------------------------------------------------------ text

## The card for the part (or preset) under the cursor.
func _card() -> String:
	var lines: PackedStringArray = PackedStringArray()
	if selected_preset >= 0:
		var lo: BodyLoadout = _presets[selected_preset]
		lines.append("[b][color=%s]PRESET: %s[/color][/b]   [color=%s]A: apply[/color]" % [C_NAME, lo.display_name, C_DIM])
		lines.append(lo.description)
		return "\n".join(lines)
	var c: PartData = selected_part()
	if c == null:
		return ""
	var inn: bool = working.has_part(c.id)
	var state: String = ""
	if inn:
		state = "  [color=%s]INSTALLED[/color]" % C_GOOD
	if preview_body.offline.has(c.id):
		state += "  [color=%s]OFFLINE[/color]" % C_BAD
	var kind: String = "passive"
	if c.is_active():
		var s_c: int = preview.slot_of(c.id)
		kind = "ACTIVE (LB, %s)" % Augments.SLOT_NAMES[s_c - 1] if s_c > 0 else "ACTIVE"
	lines.append("[b][color=%s]%s[/color][/b]%s" % [C_NAME, c.display_name, state])
	lines.append("[color=%s]%s · %s · %.1f kg · %+.0f W · %+.0f W heat · capacity %d[/color]" % [C_DIM, PartData.location_name(c.location), kind, c.mass_kg, c.power_draw_w, c.heat_w, c.capacity])
	if not inn:
		var lo: BodyLoadout = working.copy()
		var out: Array[PartData] = lo.install(c)
		if not out.is_empty():
			var names: PackedStringArray = PackedStringArray()
			for q: PartData in out:
				names.append(q.display_name)
			lines.append("[color=%s]Installing it takes out: %s[/color]" % [C_BAD, ", ".join(names)])
	lines.append(c.description)
	var effects: PackedStringArray = PackedStringArray()
	for m: StatModifier in c.modifiers:
		var sgn: int = Stats.modifier_sign(m)
		effects.append("[color=%s]%s[/color]" % [C_GOOD if sgn > 0 else (C_BAD if sgn < 0 else C_DIM), Stats.describe_modifier(m)])
	if not effects.is_empty():
		lines.append(" · ".join(effects))
	for r: StatRequirement in c.requirements:
		var ok: bool = r.met(preview_body.stat(r.stat))
		lines.append("[color=%s]%s Needs %s (now %s): %s[/color]" % [C_GOOD if ok else C_BAD, "OK" if ok else "NO", r.describe(), Stats.format(r.stat, preview_body.stat(r.stat)), r.reason])
		if not ok:
			var links: PackedStringArray = PackedStringArray()
			for q: PartData in providers(library, r):
				var tag: String = " (in)" if working.has_part(q.id) else ""
				links.append("[url=%s][color=%s]%s[/color][/url] [color=%s]%s%s[/color]" % [q.id, C_FIX, q.display_name, C_DIM, PartData.location_name(q.location), tag])
			if not links.is_empty():
				lines.append("   From: " + " · ".join(links) + "   [color=%s]RB: go there[/color]" % C_DIM)
	if c.synergy != "":
		lines.append("[color=%s]%s[/color]" % ["#9ec7ff", c.synergy])
	return "\n".join(lines)


static func _bar(fraction: float, width: int = 16) -> String:
	var n: int = clampi(roundi(fraction * width), 0, width)
	return "[color=%s]%s[/color][color=#30383a]%s[/color]" % [C_GOOD, "|".repeat(n), "|".repeat(width - n)]


static func _delta(s: StringName, v: float, was: float) -> String:
	if absf(v - was) < 0.005:
		return ""
	var better: bool = (v > was) == (Stats.better(s) > 0)
	var num: String = ("%+.2f" % (v - was)) if Stats.format_kind(s) == Stats.MULT else ("%+.0f" % (v - was))
	return " [color=%s](%s)[/color]" % [C_GOOD if better else C_BAD, num]


static func _plain_delta(v: float, was: float, fmt: String = "%+.0f") -> String:
	return "" if absf(v - was) < 0.05 else " [color=%s](%s)[/color]" % [C_DIM, fmt % (v - was)]


## The status text (BBCode): summary, the card, problems, derived values
## and every stat with its change from `was` (the current loadout). Static
## so tests can check it without a screen.
static func describe(b: BodyModel, was: BodyModel = null, card: String = "") -> String:
	if was == null:
		was = b
	var lines: PackedStringArray = PackedStringArray()
	lines.append("[b]BODY STATUS[/b]   %s" % b.loadout.display_name)
	lines.append("Mass %.0f kg%s   Load %.0f kg → mobility ×%.2f%s   Capacity %s %d/%d" % [b.mass_kg, _plain_delta(b.mass_kg, was.mass_kg),
		b.load_kg(), b.load_scale(), _delta(&"move_speed", b.load_scale(), was.load_scale()), _bar(float(b.capacity_used) / maxf(b.capacity_total(), 1.0), 10), b.capacity_used, b.capacity_total()])
	lines.append("Power %s %.0f / %.0f W   Heat in %.0f W / cooling %.0f W" % [_bar(b.current_draw_w() / maxf(b.stat(&"power_supply_w"), 1.0), 10),
		b.current_draw_w(), b.stat(&"power_supply_w"), b.heat_w, b.stat(&"heat_dissipation_w")])
	if card != "":
		lines.append("")
		lines.append(card)
	var problems: PackedStringArray = b.problems()
	if not problems.is_empty():
		lines.append("")
		for p: String in problems:
			lines.append("[color=%s]! %s[/color]" % [C_BAD, p])
	lines.append("")
	var cap: String = " (capped by structure)" if b.strength_capped() else ""
	lines.append("[color=%s]Usable strength ×%.2f%s · link range %.0f m · detection ×%.2f · slide hit %.1f m/s[/color]" % [C_DIM,
		b.usable_strength(), cap, b.link_range_m(), b.detection_scale(), b.mass_kg / 100.0 * b.usable_strength() * b.stat(&"impact") * 6.5])
	for g: int in Stats.GROUP_NAMES.size():
		var cells: PackedStringArray = PackedStringArray()
		for s: StringName in Stats.in_group(g):
			cells.append("%s [b]%s[/b]%s" % [Stats.label(s), Stats.format(s, b.stat(s)), _delta(s, b.stat(s), was.stat(s))])
		lines.append("[color=%s]%s[/color]  %s" % [C_GOOD, Stats.GROUP_NAMES[g], "   ".join(cells)])
	lines.append("")
	lines.append("[b]INSTALLED[/b]")
	for p: PartData in b.loadout.parts:
		var kind: String = "ACTIVE (LB, %s)" % Augments.SLOT_NAMES[clampi(b.loadout.slot_of(p.id), 1, 3) - 1] if p.is_active() else "passive"
		var off: String = "  [color=%s]OFFLINE: %s[/color]" % [C_BAD, b.offline[p.id]] if b.offline.has(p.id) else ""
		lines.append("[color=%s]%s[/color]  [color=%s]%s · %s[/color]%s" % [C_NAME, p.display_name, C_DIM, PartData.location_name(p.location).to_lower(), kind, off])
	return "\n".join(lines)


# ------------------------------------------------------------------ colours

## The channels of the Colours page: every suit piece, then each installed
## part that shows hardware (its paint, then its lights).
func _build_channels() -> void:
	_channels.clear()
	_channel_labels.clear()
	for i: int in BodyColors.SUIT_CHANNELS.size():
		_channels.append(BodyColors.SUIT_CHANNELS[i])
		_channel_labels.append(BodyColors.SUIT_LABELS[i])
	for p: PartData in working.parts:
		if p.visuals.is_empty() or p.fixed:
			continue
		var short: String = p.display_name.get_slice(" ", 0)
		_channels.append(BodyColors.part_key(p.id))
		_channel_labels.append(short + " hardware")
		_channels.append(BodyColors.glow_key(p.id))
		_channel_labels.append(short + " lights")
	color_row = clampi(color_row, 0, _channels.size() - 1)


func channel() -> StringName:
	return _channels[color_row] if color_row < _channels.size() else &""


## The colour shown for a channel that hasn't been set yet (where the
## sliders start from).
func _start_color(ch: StringName) -> Color:
	if working_colors.has(ch):
		return working_colors.color(ch)
	if ch == &"lights" or String(ch).begins_with("glow:"):
		return Color(0.36, 0.86, 0.78)
	if ch == &"trim":
		return Color(0.3, 0.32, 0.34)
	return Color(0.035, 0.036, 0.04)


func _is_light(ch: StringName) -> bool:
	return ch == &"lights" or String(ch).begins_with("glow:")


## Puts a colour on the channel under the cursor.
func paint(c: Color) -> void:
	working_colors.set_color(channel(), c)
	colors_changed = true
	if appearance:
		appearance.rebuild()
	_refresh_colour_text()


func _refresh_colour_text() -> void:
	_list.text = _colour_list_text()
	_text.text = _colour_card()


## Nearest palette entry to the channel's colour (-1: not set).
func _palette_index(ch: StringName) -> int:
	if not working_colors.has(ch):
		return -1
	var c: Color = working_colors.color(ch)
	var best: int = 0
	var best_d: float = INF
	for i: int in BodyColors.PALETTE.size():
		var q: Color = BodyColors.PALETTE[i][1]
		var d: float = Vector3(c.r - q.r, c.g - q.g, c.b - q.b).length_squared()
		if d < best_d:
			best_d = d
			best = i
	return best


## Left/right on a channel: the next palette colour ("as built" sits before the first).
func step_palette(step: int) -> void:
	var ch: StringName = channel()
	var i: int = _palette_index(ch) + step
	if i < 0 or i >= BodyColors.PALETTE.size():
		working_colors.colors.erase(ch)
		colors_changed = true
		if appearance:
			appearance.rebuild()
		_refresh_colour_text()
		return
	var swatch: Color = BodyColors.PALETTE[i][1]
	paint(swatch)


## Left/right on a slider.
func step_slider(step: int) -> void:
	var ch: StringName = channel()
	if slider == 3:
		if _is_light(ch):
			return
		working_colors.set_finish(ch, wrapi(working_colors.finish(ch) + step, 0, BodyColors.FINISH_NAMES.size()))
		colors_changed = true
		if appearance:
			appearance.rebuild()
		_refresh_colour_text()
		return
	var c: Color = _start_color(ch)
	var h: float = c.h
	var sat: float = c.s
	var val: float = c.v
	match slider:
		0:
			h = wrapf(h + step / 36.0, 0.0, 1.0)
			if sat < 0.05:
				sat = 0.6
		1:
			sat = clampf(sat + step * 0.05, 0.0, 1.0)
		2:
			val = clampf(val + step * 0.04, 0.0, 1.0)
	paint(Color.from_hsv(h, sat, val))


## X: the channel goes back to the way it was built.
func reset_channel() -> void:
	working_colors.clear(channel())
	colors_changed = true
	if appearance:
		appearance.rebuild()
	_refresh_colour_text()


func _colour_input(event: InputEvent) -> bool:
	if event.is_action_pressed(&"switch_weapon"):
		toggle_helmet()
	elif event.is_action_pressed(&"pause"):
		close()
	elif event.is_action_pressed(&"ui_cancel"):
		if editing:
			editing = false
			_refresh_colour_text()
		else:
			close()
	elif event.is_action_pressed(&"ui_accept"):
		editing = not editing
		slider = 0
		Sfx.play_ui(&"draw", -8.0)
		_refresh_colour_text()
	elif event.is_action_pressed(&"reload"):
		reset_channel()
		Sfx.play_ui(&"holster", -6.0)
	elif event.is_action_pressed(&"ui_up", true) or event.is_action_pressed(&"ui_down", true):
		var step: int = -1 if event.is_action_pressed(&"ui_up", true) else 1
		if editing:
			slider = wrapi(slider + step, 0, SLIDERS.size())
		else:
			color_row = wrapi(color_row + step, 0, _channels.size())
		Sfx.play_ui(&"wheel_tick", -12.0, 0.02)
		_refresh_colour_text()
	elif event.is_action_pressed(&"ui_left", true) or event.is_action_pressed(&"ui_right", true):
		var step: int = -1 if event.is_action_pressed(&"ui_left", true) else 1
		if editing:
			step_slider(step)
		else:
			step_palette(step)
		Sfx.play_ui(&"wheel_tick", -10.0, 0.04)
	else:
		return false
	return true


func _chip(ch: StringName) -> String:
	if not working_colors.has(ch):
		return "[color=%s][ -- ][/color]" % C_DIM
	return "[bgcolor=#%s]      [/bgcolor]" % working_colors.color(ch).to_html(false)


func _colour_list_text() -> String:
	var lines: PackedStringArray = PackedStringArray()
	lines.append("[b]COLOURS[/b]  [color=%s]%s[/color]" % [C_NAME, working.display_name])
	lines.append("[color=%s]Each piece keeps the look it was built with until you paint it.[/color]" % C_DIM)
	lines.append("")
	var table: String = "[table=3]"
	for i: int in _channels.size():
		var ch: StringName = _channels[i]
		var sel: bool = i == color_row
		var what: String = "as built"
		if working_colors.has(ch):
			var pi: int = _palette_index(ch)
			var q: Color = BodyColors.PALETTE[pi][1]
			var c: Color = working_colors.color(ch)
			what = BodyColors.PALETTE[pi][0] if Vector3(c.r - q.r, c.g - q.g, c.b - q.b).length() < 0.02 else "custom #" + c.to_html(false)
		var fin: int = working_colors.finish(ch)
		if fin != BodyColors.Finish.DEFAULT:
			what += ", " + BodyColors.FINISH_NAMES[fin]
		var mark: String = "[color=%s]> [/color]" % C_GOOD if sel else "  "
		var name_col: String = "#ffffff" if sel else C_DIM
		var bg0: String = "[bgcolor=#1d3a36]" if sel else ""
		var bg1: String = "[/bgcolor]" if sel else ""
		table += "[cell]%s%s[color=%s]%s[/color]  %s[/cell]" % [bg0, mark, name_col, _channel_labels[i], bg1]
		table += "[cell]%s  [/cell]" % _chip(ch)
		table += "[cell]%s[color=%s]%s[/color]%s[/cell]" % [bg0, C_NAME if working_colors.has(ch) else C_DIM, what, bg1]
	lines.append(table + "[/table]")
	lines.append("")
	if editing:
		lines.append("[color=%s]Up/down: slider   Left/right: change   A or B: back   X: as built[/color]" % C_DIM)
	else:
		lines.append("[color=%s]Up/down: piece   Left/right: palette   A: sliders   X: as built[/color]" % C_DIM)
	lines.append("[color=%s]LB: loadout   Y: helmet   LT: zoom   RS: turn   B: done[/color]" % C_DIM)
	return "\n".join(lines)


func _colour_card() -> String:
	var lines: PackedStringArray = PackedStringArray()
	var ch: StringName = channel()
	if ch == &"":
		return ""
	var c: Color = _start_color(ch)
	lines.append("[b][color=%s]%s[/color][/b]   %s" % [C_NAME, _channel_labels[color_row].to_upper(), _chip(ch)])
	if not working_colors.has(ch):
		lines.append("[color=%s]As built. Left/right picks a palette colour; A opens the sliders.[/color]" % C_DIM)
	lines.append("")
	var values: Array[float] = [c.h, c.s, c.v]
	for i: int in SLIDERS.size():
		var sel: bool = editing and i == slider
		var body_text: String
		if i < 3:
			body_text = "%s %3d%%" % [_bar(values[i], 24), roundi(values[i] * 100.0)]
		elif _is_light(ch):
			body_text = "[color=%s]lights only take a colour[/color]" % C_DIM
		else:
			var names: PackedStringArray = PackedStringArray()
			for k: int in BodyColors.FINISH_NAMES.size():
				var on: bool = k == working_colors.finish(ch)
				names.append("[color=%s]%s[/color]" % [C_GOOD if on else C_DIM, BodyColors.FINISH_NAMES[k]])
			body_text = "  ".join(names)
		var line: String = "%s[color=%s]%-11s[/color] %s" % ["[color=%s]> [/color]" % C_GOOD if sel else "  ", "#ffffff" if sel else C_DIM, SLIDERS[i], body_text]
		if sel:
			line = "[bgcolor=#1d3a36]" + line + "[/bgcolor]"
		lines.append(line)
	lines.append("")
	lines.append("[b]PALETTE[/b]")
	var row_text: String = ""
	var at: int = _palette_index(ch)
	for i: int in BodyColors.PALETTE.size():
		var q: Color = BodyColors.PALETTE[i][1]
		row_text += "[bgcolor=#%s]%s[/bgcolor] " % [q.to_html(false), "[color=#ffffff]<>[/color]" if i == at else "    "]
		if i % 9 == 8:
			lines.append(row_text)
			lines.append("")
			row_text = ""
	if row_text != "":
		lines.append(row_text)
	lines.append("")
	lines.append("[color=%s]The suit's plates, weave, trim and lights are painted piece by piece; the first-person arms follow the arm, hand, undersuit and light colours. Hardware on installed parts takes one paint and one light colour each.[/color]" % C_DIM)
	return "\n".join(lines)
