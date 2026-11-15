class_name KitScreen
extends CanvasLayer
## Survival's start screen (docs/design.md §8.2): pick a doctrine (the
## baseline body and the drops it favours), one gun and one active at Mk I
## from those the doctrine's body can run. D-pad up/down picks the row,
## left/right changes it; A deploys, B goes back.

signal confirmed(doctrine: Doctrine, gun: WeaponData, active: ActivePartData)
signal cancelled
## The pick changed: the body it starts with (the menu dresses the operative in it).
signal preview(body: BodyLoadout)

const ROWS: Array[String] = ["DOCTRINE", "WEAPON", "ACTIVE"]

var config: SurvivalConfig
var row: int = 0
var doctrine_i: int = 0
var gun_i: int = 0
var active_i: int = 0

var _rows: Array[PanelContainer] = []
var _values: Array[Label] = []
var _detail: Label
var _detail_title: Label
var _root: Control


func _init(p_config: SurvivalConfig = null) -> void:
	config = p_config if p_config else preload("res://data/run/survival.tres")
	layer = 42
	process_mode = Node.PROCESS_MODE_ALWAYS


func _ready() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	var shade: ColorRect = RunUi.wash(0.0)
	_root.add_child(shade)
	var g: Gradient = Gradient.new()
	g.set_color(0, Color(0.01, 0.012, 0.016, 0.9))
	g.set_color(1, Color(0.01, 0.012, 0.016, 0.0))
	var gt: GradientTexture2D = GradientTexture2D.new()
	gt.gradient = g
	gt.width = 128
	gt.height = 4
	var tr: TextureRect = TextureRect.new()
	tr.texture = gt
	tr.stretch_mode = TextureRect.STRETCH_SCALE
	tr.anchor_right = 0.75
	tr.anchor_bottom = 1.0
	tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(tr)
	var col: VBoxContainer = VBoxContainer.new()
	col.anchor_bottom = 1.0
	col.offset_left = 64.0
	col.offset_top = 48.0
	col.offset_right = 640.0
	col.offset_bottom = -32.0
	col.add_theme_constant_override("separation", 8)
	_root.add_child(col)
	var title: Label = RunUi.label("SURVIVAL", 48)
	title.add_theme_font_override("font", RunUi.title_font())
	col.add_child(title)
	col.add_child(RunUi.label("CHINATOWN DOCKS  ·  TRIAD  ·  WAVES UNTIL YOU FALL", 14, RunUi.C_ACCENT))
	var gap: Control = Control.new()
	gap.custom_minimum_size = Vector2(0, 14)
	col.add_child(gap)
	for i: int in ROWS.size():
		var pc: PanelContainer = PanelContainer.new()
		pc.custom_minimum_size = Vector2(560, 0)
		var hb: HBoxContainer = HBoxContainer.new()
		hb.add_child(RunUi.label(ROWS[i], 14, RunUi.C_DIM))
		var sp: Control = Control.new()
		sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hb.add_child(sp)
		var v: Label = RunUi.label("", 22)
		hb.add_child(v)
		pc.add_child(hb)
		col.add_child(pc)
		_rows.append(pc)
		_values.append(v)
	var gap2: Control = Control.new()
	gap2.custom_minimum_size = Vector2(0, 8)
	col.add_child(gap2)
	_detail_title = RunUi.label("", 16, RunUi.C_ACCENT)
	col.add_child(_detail_title)
	_detail = RunUi.label("", 15, RunUi.C_TEXT, true)
	_detail.custom_minimum_size = Vector2(560, 0)
	_detail.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(_detail)
	col.add_child(RunUi.label("D-pad ▲▼  row     ◀ ▶  change     A  deploy     B  back", 13, RunUi.C_DIM))
	_refresh()


func doctrine() -> Doctrine:
	return config.doctrines[doctrine_i]


func gun() -> WeaponData:
	return config.starter_weapons[gun_i]


func active() -> ActivePartData:
	var acts: Array[ActivePartData] = doctrine().starter_actives
	return acts[clampi(active_i, 0, acts.size() - 1)]


## Changes the focused row's pick by `step`.
func cycle(step: int) -> void:
	match row:
		0:
			doctrine_i = posmod(doctrine_i + step, config.doctrines.size())
			active_i = 0
		1:
			gun_i = posmod(gun_i + step, config.starter_weapons.size())
		2:
			active_i = posmod(active_i + step, doctrine().starter_actives.size())
	Sfx.play_ui(&"wheel_tick", -8.0, 0.02)
	_refresh()


func move(step: int) -> void:
	row = clampi(row + step, 0, ROWS.size() - 1)
	Sfx.play_ui(&"wheel_tick", -10.0, 0.02)
	_refresh()


## The starting body of the current pick: the doctrine's frame and the active at Mk I.
func start_body() -> BodyLoadout:
	var r: RunState = RunState.new(config, 1)
	r.start(doctrine(), gun(), active())
	return r.loadout


func confirm() -> void:
	Sfx.play_ui(&"draw", -4.0)
	confirmed.emit(doctrine(), gun(), active())


func _input(event: InputEvent) -> void:
	if not visible:
		return
	var handled: bool = true
	if event.is_action_pressed(&"ui_up"):
		move(-1)
	elif event.is_action_pressed(&"ui_down"):
		move(1)
	elif event.is_action_pressed(&"ui_left"):
		cycle(-1)
	elif event.is_action_pressed(&"ui_right"):
		cycle(1)
	elif event.is_action_pressed(&"ui_accept"):
		confirm()
	elif event.is_action_pressed(&"ui_cancel"):
		cancelled.emit()
	else:
		handled = false
	if handled:
		get_viewport().set_input_as_handled()


func _refresh() -> void:
	if _values.is_empty():
		return
	var d: Doctrine = doctrine()
	_values[0].text = "◀  %s  ▶" % d.display_name.to_upper()
	_values[1].text = "◀  %s  ▶" % gun().display_name
	var it: RunItem = config.item_for(active())
	_values[2].text = "◀  %s  Mk I  ▶" % active().display_name
	for i: int in _rows.size():
		_rows[i].add_theme_stylebox_override("panel", RunUi.box(i == row))
		_values[i].add_theme_color_override("font_color", Color.WHITE if i == row else RunUi.C_TEXT)
	if is_inside_tree():
		preview.emit(start_body())
	match row:
		0:
			var parts: PackedStringArray = PackedStringArray()
			for p: PartData in d.parts:
				parts.append(p.display_name)
			var acts: PackedStringArray = PackedStringArray()
			for a: ActivePartData in d.starter_actives:
				acts.append(a.display_name)
			_detail_title.text = "FAVOURS  %s  ·  %s" % [String(d.primary_tag).to_upper(), String(d.secondary_tag).to_upper()]
			_detail.text = "%s\n\nBody: %s\nCan start with: %s" % [d.description, ", ".join(parts), ", ".join(acts)]
		1:
			var wi: RunItem = config.item_for(gun())
			_detail_title.text = RunUi.tags_text(wi.tags) if wi else ""
			_detail.text = wi.description() if wi else ""
		2:
			_detail_title.text = "MK I  ·  " + (RunUi.tags_text(it.tags) if it else "")
			var desc: String = active().description
			_detail.text = "%s\n\nMk I: %s" % [desc, RunUi.mark_changes(it, 0, 1).replace("\n", ",  ")] if it else desc
