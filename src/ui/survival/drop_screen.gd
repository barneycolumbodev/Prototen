class_name DropScreen
extends CanvasLayer
## The supply drop after a Survival wave (docs/design.md §8.4): one card
## (picked for you: A takes it) or two (◀ ▶ chooses, A takes). A boss drop
## (§8.7) is its own card first. Pauses the game while it's up.

signal taken(offer: RunState.Offer)

var offers: Array[RunState.Offer] = []
var pick: int = 0
var heading: String = ""
var subheading: String = ""
var accent: Color = RunUi.C_ACCENT

var _cards: Array[PanelContainer] = []
var _row: HBoxContainer
var _title: Label
var _sub: Label
var _hint: Label
var _open_time: int = 0


func _init() -> void:
	layer = 44
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false


func _ready() -> void:
	var root: Control = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	root.add_child(RunUi.wash(0.62))
	var col: VBoxContainer = VBoxContainer.new()
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 10)
	root.add_child(col)
	_title = RunUi.label("", 34)
	_title.add_theme_font_override("font", RunUi.title_font())
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_title)
	_sub = RunUi.label("", 15, RunUi.C_DIM)
	_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_sub)
	_row = HBoxContainer.new()
	_row.alignment = BoxContainer.ALIGNMENT_CENTER
	_row.add_theme_constant_override("separation", 28)
	col.add_child(_row)
	_hint = RunUi.label("", 14, RunUi.C_DIM)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(_hint)


## Shows `p_offers` (one or two).
func show_offers(p_offers: Array[RunState.Offer], p_heading: String, p_sub: String, p_accent: Color = RunUi.C_ACCENT) -> void:
	offers = p_offers
	heading = p_heading
	subheading = p_sub
	accent = p_accent
	pick = 0
	_build_cards()
	visible = true
	_open_time = Time.get_ticks_msec()
	get_tree().paused = true
	# Opening sound: the supply-drop stinger (MusicDirector, music_cue from SurvivalRun).


func _build_cards() -> void:
	for c: PanelContainer in _cards:
		c.queue_free()
	_cards.clear()
	_title.text = heading
	_title.add_theme_color_override("font_color", accent)
	_sub.text = subheading
	for o: RunState.Offer in offers:
		var pc: PanelContainer = PanelContainer.new()
		pc.custom_minimum_size = Vector2(440, 330)
		var v: VBoxContainer = VBoxContainer.new()
		v.add_theme_constant_override("separation", 6)
		v.add_child(RunUi.label(o.kind_label(), 13, RunUi.C_GOLD if o.upgrade else accent))
		var t: Label = RunUi.label(o.title(), 24, Color.WHITE, true)
		t.custom_minimum_size = Vector2(400, 0)
		v.add_child(t)
		v.add_child(RunUi.label(RunUi.tags_text(o.item.tags), 12, RunUi.C_DIM))
		var body: String = o.item.description()
		if o.item.kind() == RunItem.Kind.ACTIVE:
			body = RunUi.mark_changes(o.item, o.mark - 1 if o.upgrade else 0, o.mark) if o.upgrade else body
		var d: Label = RunUi.label(body, 14, RunUi.C_TEXT, true)
		d.custom_minimum_size = Vector2(400, 0)
		d.max_lines_visible = 8
		d.size_flags_vertical = Control.SIZE_EXPAND_FILL
		v.add_child(d)
		var notes: PackedStringArray = PackedStringArray()
		for p: PartData in o.replaces:
			notes.append("Replaces %s" % p.display_name)
		if o.offline != "":
			notes.append("Offline on this body: %s" % o.offline)
		if not notes.is_empty():
			v.add_child(RunUi.label("\n".join(notes), 13, RunUi.C_WARN, true))
		pc.add_child(v)
		_row.add_child(pc)
		_cards.append(pc)
	_hint.text = "◀ ▶  choose     A  take" if offers.size() > 1 else "A  take"
	_paint()


func _paint() -> void:
	for i: int in _cards.size():
		_cards[i].add_theme_stylebox_override("panel", RunUi.box(i == pick, RunUi.C_GOLD if offers[i].upgrade else accent))
		_cards[i].modulate = Color.WHITE if i == pick or _cards.size() == 1 else Color(1, 1, 1, 0.72)


func choose(i: int) -> void:
	pick = clampi(i, 0, offers.size() - 1)
	_paint()


func take() -> void:
	if offers.is_empty():
		return
	var o: RunState.Offer = offers[pick]
	visible = false
	get_tree().paused = false
	offers = []
	Sfx.play_ui(&"draw", -4.0)
	taken.emit(o)


func _input(event: InputEvent) -> void:
	if not visible:
		return
	# A beat before input counts, so a held trigger or a mashed A doesn't take a card unseen.
	if Time.get_ticks_msec() - _open_time < 450:
		return
	var handled: bool = true
	if event.is_action_pressed(&"ui_left"):
		choose(pick - 1)
		Sfx.play_ui(&"wheel_tick", -8.0, 0.02)
	elif event.is_action_pressed(&"ui_right"):
		choose(pick + 1)
		Sfx.play_ui(&"wheel_tick", -8.0, 0.02)
	elif event.is_action_pressed(&"ui_accept"):
		take()
	else:
		handled = false
	if handled:
		get_viewport().set_input_as_handled()
