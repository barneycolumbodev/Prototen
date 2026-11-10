class_name BodyStatus
extends CanvasLayer
## Body status and loadout (View button, CLAUDE.md §9.4; also Pause → Body
## status; docs/design.md §3.6). Left: the operative on a turntable, wearing
## whatever is being previewed. Middle: every place in the body that takes
## a part, and the presets. Right: the part under the cursor (what it does,
## what it costs, what it needs, how it combines) and the whole stat sheet
## with the change the preview would make.
##
## Controls: up/down picks a row; left/right browses the parts that fit
## there (the body and the numbers preview each one); A installs it (or
## applies the preset); X takes the part out; Y helmet on/off; View or B
## closes and puts the new loadout on the player (saved for next time).
## The Actives row lists every active part; A on an installed active moves
## it to the next D-pad direction. Pauses the game.
##
## LB switches to the Colours page (docs/design.md §3.7): one row per suit
## piece and per installed part with hardware. Left/right steps through the
## palette, A opens the sliders (hue, saturation, brightness, finish), X
## puts the piece back the way it was built.

const STUDIO_SKY: Shader = preload("res://src/ui/studio_sky.gdshader")
## Rows, top to bottom (each location once per slot it has).
const ORDER: Array[int] = [
	PartData.Location.SUIT, PartData.Location.HEAD, PartData.Location.EYES, PartData.Location.EARS,
	PartData.Location.NERVOUS, PartData.Location.SKELETON, PartData.Location.MUSCLE, PartData.Location.ORGANS,
	PartData.Location.TORSO, PartData.Location.ARMS, PartData.Location.HANDS, PartData.Location.LEGS,
	PartData.Location.SPINE, PartData.Location.BACK, PartData.Location.SKIN, PartData.Location.BLOOD,
]
## Row ids that aren't body locations.
const ROW_PRESETS: int = -1
const ROW_ACTIVES: int = -2
enum Page { LOADOUT, COLOURS }
const SLIDERS: Array[String] = ["Hue", "Saturation", "Brightness", "Finish"]
const C_GOOD: String = "#5cdcc6"
const C_BAD: String = "#e0705a"
const C_DIM: String = "#7d8b8b"
const C_NAME: String = "#ffd28a"
const C_OFF: String = "#9a9fa3"

var player: Player
var appearance: BodyAppearance
var library: PartLibrary = LoadoutStore.LIBRARY
## The loadout being built (applied to the player on close).
var working: BodyLoadout
## What the cursor would make of it, and its numbers.
var preview: BodyLoadout
var preview_body: BodyModel
var working_body: BodyModel
## Row under the cursor (0 = presets) and the candidate browsed there.
var row: int = 1
var candidate: int = 0
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

var _rows: Array[Vector2i] = []  # (location, slot index); (-1, 0) = presets
var _presets: Array[BodyLoadout] = []
var _viewport: SubViewport
var _pivot: Node3D
var _cam: Camera3D
## 0 = whole body, 1 = close on the upper body (LT held).
var zoom: float = 0.0
var _zoom_held: bool = false
## Right stick turns the model; the turntable resumes when it's let go.
var _manual_turn: float = 0.0
var _list: RichTextLabel
var _text: RichTextLabel


func _ready() -> void:
	layer = 105  # above the debug overlay
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	_rows.append(Vector2i(ROW_PRESETS, 0))
	_rows.append(Vector2i(ROW_ACTIVES, 0))
	for loc: int in ORDER:
		for i: int in PartData.slots_for(loc):
			_rows.append(Vector2i(loc, i))
	_presets = LoadoutStore.presets()
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
	svc.size_flags_stretch_ratio = 0.62
	row_box.add_child(svc)
	_viewport = SubViewport.new()
	_viewport.own_world_3d = true
	_viewport.transparent_bg = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_WHEN_VISIBLE
	svc.add_child(_viewport)
	_list = _label(14)
	row_box.add_child(_margin(_list, 0.62))
	_text = _label(12)
	row_box.add_child(_margin(_text, 1.0))


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
	m.size_flags_stretch_ratio = ratio
	m.add_theme_constant_override("margin_top", 18)
	m.add_theme_constant_override("margin_bottom", 10)
	m.add_theme_constant_override("margin_right", 14)
	m.add_child(c)
	return m


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
	row = clampi(row, 0, _rows.size() - 1)
	_reset_candidate()
	_refresh()
	_pivot.rotation.y = 0.35
	visible = true
	get_tree().paused = true


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
	elif event.is_action_pressed(&"ui_up", true):
		move_row(-1)
	elif event.is_action_pressed(&"ui_down", true):
		move_row(1)
	elif event.is_action_pressed(&"ui_left", true):
		browse(-1)
	elif event.is_action_pressed(&"ui_right", true):
		browse(1)
	elif event.is_action_pressed(&"ui_accept"):
		accept()
	elif event.is_action_pressed(&"reload"):
		remove_here()
	else:
		handled = false
	if handled:
		get_viewport().set_input_as_handled()


# ------------------------------------------------------------------ editing

## Puts the cursor on a location's row (slot index for two-slot places).
func select_row(loc: int, slot: int = 0) -> void:
	var i: int = _rows.find(Vector2i(loc, slot))
	if i >= 0:
		row = i
		_reset_candidate()
		_refresh()


## Browses to a part by id in the current row. Returns whether it's there.
func browse_to(id: StringName) -> bool:
	var opts: Array[PartData] = options()
	for i: int in opts.size():
		if opts[i] and opts[i].id == id:
			candidate = i
			_refresh()
			return true
	return false


func row_location() -> int:
	return _rows[row].x


## The part installed in the cursor's row, or null. On the Actives row:
## the browsed active, if it's installed.
func installed_here() -> PartData:
	var r: Vector2i = _rows[row]
	if r.x == ROW_ACTIVES:
		var acts: Array[ActivePartData] = library.actives()
		if candidate >= 0 and candidate < acts.size() and working.has_part(acts[candidate].id):
			return acts[candidate]
		return null
	if r.x < 0:
		return null
	var here: Array[PartData] = working.parts_at(r.x)
	return here[r.y] if r.y < here.size() else null


## What can go in the cursor's row: null (empty) and every part for that
## location that isn't already in its other slot.
func options() -> Array[PartData]:
	var out: Array[PartData] = []
	var r: Vector2i = _rows[row]
	if r.x == ROW_ACTIVES:
		for a: ActivePartData in library.actives():
			out.append(a)
		return out
	if r.x < 0:
		return out
	var mine: PartData = installed_here()
	if mine == null or not mine.fixed:
		out.append(null)
	for p: PartData in library.at(r.x):
		if p == mine or not working.has_part(p.id):
			out.append(p)
	return out


func candidate_part() -> PartData:
	var opts: Array[PartData] = options()
	return opts[candidate] if candidate >= 0 and candidate < opts.size() else null


func move_row(step: int) -> void:
	row = wrapi(row + step, 0, _rows.size())
	_reset_candidate()
	_refresh()
	Sfx.play_ui(&"wheel_tick", -12.0, 0.02)


func browse(step: int) -> void:
	if _rows[row].x == ROW_PRESETS:
		candidate = wrapi(candidate + step, 0, maxi(_presets.size(), 1))
	else:
		candidate = wrapi(candidate + step, 0, maxi(options().size(), 1))
	_refresh()
	Sfx.play_ui(&"wheel_tick", -10.0, 0.04)


## A: install the browsed part (or apply the browsed preset).
func accept() -> void:
	var keep: int = -1
	if _rows[row].x == ROW_PRESETS:
		if candidate < _presets.size():
			working = _presets[candidate].copy()
			changed = true
	else:
		var c: PartData = candidate_part()
		var mine: PartData = installed_here()
		if c == mine:
			# Already in: an active moves to the next D-pad direction.
			if c == null or not c.is_active() or working.actives().size() < 2:
				return
			working.cycle_slot(c.id)
			working.display_name = "Custom"
			changed = true
			Sfx.play_ui(&"wheel_tick", -6.0)
			_refresh()
			return
		if _rows[row].x == ROW_ACTIVES:
			keep = candidate
		elif mine:
			working.remove(mine.id)
		if c:
			working.install(c)
		working.display_name = "Custom"
		changed = true
	Sfx.play_ui(&"draw", -6.0)
	_reset_candidate()
	if keep >= 0:
		candidate = keep
	_refresh()


## X: take the part in this row out.
func remove_here() -> void:
	var mine: PartData = installed_here()
	if mine and working.remove(mine.id):
		working.display_name = "Custom"
		changed = true
		Sfx.play_ui(&"holster", -6.0)
		if _rows[row].x != ROW_ACTIVES:
			_reset_candidate()
		_refresh()


func _reset_candidate() -> void:
	if working == null:
		candidate = 0
		return
	if _rows[row].x < 0:
		candidate = 0
		return
	var opts: Array[PartData] = options()
	candidate = maxi(opts.find(installed_here()), 0)


## Loadout or Colours.
func set_page(p: Page) -> void:
	page = p
	editing = false
	Sfx.play_ui(&"wheel_tick", -8.0, 0.02)
	_refresh()


## The loadout with the browsed candidate swapped in.
func _make_preview() -> BodyLoadout:
	if page == Page.COLOURS:
		return working.copy()
	if _rows[row].x == ROW_PRESETS:
		return _presets[candidate].copy() if candidate < _presets.size() else working.copy()
	var lo: BodyLoadout = working.copy()
	var c: PartData = candidate_part()
	var mine: PartData = installed_here()
	if c != mine:
		if mine and _rows[row].x != ROW_ACTIVES:
			lo.remove(mine.id)
		if c:
			lo.install(c)
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
	if page == Page.COLOURS:
		_build_channels()
		_list.text = _colour_list_text()
		_text.text = _colour_card()
		return
	_list.text = _list_text()
	_text.text = describe(preview_body, working_body, _card())


# ------------------------------------------------------------------ text

func _list_text() -> String:
	var lines: PackedStringArray = PackedStringArray()
	lines.append("[b]LOADOUT[/b]  [color=%s]%s[/color]" % [C_NAME, working.display_name])
	lines.append("[color=%s]Capacity %d / %d   %.0f kg[/color]" % [C_DIM, working_body.capacity_used, working_body.capacity_total(), working_body.mass_kg])
	lines.append("")
	var last_loc: int = -2
	for i: int in _rows.size():
		var r: Vector2i = _rows[i]
		var sel: bool = i == row
		var name: String
		var label: String
		if r.x == ROW_PRESETS:
			label = "Presets"
			name = _presets[candidate].display_name if sel and candidate < _presets.size() else "%d builds" % _presets.size()
		elif r.x == ROW_ACTIVES:
			label = "Actives"
			var a: PartData = candidate_part() if sel else null
			if a:
				var s_at: int = working.slot_of(a.id)
				name = "[color=%s]%s[/color] [color=%s]%s[/color]" % ["#ffffff", a.display_name, C_GOOD if s_at > 0 else C_DIM,
					"[%s]" % Augments.SLOT_ARROWS[s_at - 1] if s_at > 0 else "not installed"]
			else:
				name = "%d / %d installed" % [working.actives().size(), BodyLoadout.MAX_ACTIVES]
		else:
			label = PartData.location_name(r.x) if r.x != last_loc else ""
			var here: Array[PartData] = working.parts_at(r.x)
			var p: PartData = here[r.y] if r.y < here.size() else null
			if sel:
				p = candidate_part()
			if p == null:
				name = "[color=%s]empty[/color]" % C_DIM
			else:
				var col: String = C_OFF if working_body.offline.has(p.id) else (C_NAME if not sel else "#ffffff")
				name = "[color=%s]%s[/color]" % [col, p.display_name]
				var s_of: int = (preview if sel else working).slot_of(p.id)
				if p.is_active() and s_of > 0:
					name += " [color=%s][%s][/color]" % [C_DIM, Augments.SLOT_ARROWS[s_of - 1]]
		last_loc = r.x
		var arrow: String = "[color=%s]< [/color]" % C_GOOD if sel else "  "
		var tail: String = "[color=%s] >[/color]" % C_GOOD if sel else ""
		var line: String = "[color=%s]%-14s[/color] %s%s%s" % [C_DIM, label, arrow, name, tail]
		if sel:
			line = "[bgcolor=#1d3a36]" + line + "[/bgcolor]"
		lines.append(line)
	lines.append("")
	lines.append("[color=%s]Up/down: place   Left/right: browse   A: install (an installed active: next D-pad slot)   X: remove[/color]" % C_DIM)
	lines.append("[color=%s]LB: colours   Y: helmet   LT: zoom   RS: turn   B: done[/color]" % C_DIM)
	return "\n".join(lines)


## The card for the part (or preset) under the cursor.
func _card() -> String:
	var lines: PackedStringArray = PackedStringArray()
	if _rows[row].x == ROW_PRESETS:
		if candidate < _presets.size():
			var lo: BodyLoadout = _presets[candidate]
			lines.append("[b][color=%s]PRESET: %s[/color][/b]   [color=%s]%d / %d   A: apply[/color]" % [C_NAME, lo.display_name, C_DIM, candidate + 1, _presets.size()])
			lines.append(lo.description)
		return "\n".join(lines)
	var c: PartData = candidate_part()
	var opts: Array[PartData] = options()
	var where: String = "%s   %d / %d" % [PartData.location_name(c.location if c else _rows[row].x), candidate + 1, opts.size()]
	if c == null:
		lines.append("[b]EMPTY[/b]   [color=%s]%s[/color]" % [C_DIM, where])
		return "\n".join(lines)
	var state: String = ""
	if c == installed_here():
		state = "  [color=%s]INSTALLED[/color]" % C_GOOD
	if preview_body.offline.has(c.id):
		state += "  [color=%s]OFFLINE[/color]" % C_BAD
	var kind: String = "passive"
	if c.is_active():
		var s_c: int = preview.slot_of(c.id)
		kind = "ACTIVE (LB, %s)" % Augments.SLOT_NAMES[s_c - 1] if s_c > 0 else "ACTIVE"
	lines.append("[b][color=%s]%s[/color][/b]%s" % [C_NAME, c.display_name, state])
	lines.append("[color=%s]%s · %s · %.1f kg · %+.0f W · %+.0f W heat · capacity %d[/color]" % [C_DIM, where, kind, c.mass_kg, c.power_draw_w, c.heat_w, c.capacity])
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
		var arrow: String = "[color=%s]< [/color]" % C_GOOD if sel and not editing else "  "
		var tail: String = "[color=%s] >[/color]" % C_GOOD if sel and not editing else ""
		var line: String = "[color=%s]%-20s[/color] %s%s [color=%s]%s[/color]%s" % [C_DIM if not sel else "#ffffff", _channel_labels[i], arrow, _chip(ch),
			C_NAME if working_colors.has(ch) else C_DIM, what, tail]
		if sel:
			line = "[bgcolor=#1d3a36]" + line + "[/bgcolor]"
		lines.append(line)
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
