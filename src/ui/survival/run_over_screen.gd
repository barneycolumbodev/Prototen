class_name RunOverScreen
extends CanvasLayer
## The end of a Survival run (docs/design.md §8.2): the wave reached, the
## kills, the kit, what was picked up. A goes back to the main menu.

signal done

var _box: VBoxContainer
var _open_time: int = 0


func _init() -> void:
	layer = 46
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false


func _ready() -> void:
	var root: Control = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	root.add_child(RunUi.wash(0.8))
	_box = VBoxContainer.new()
	_box.set_anchors_preset(Control.PRESET_FULL_RECT)
	_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_box.add_theme_constant_override("separation", 8)
	root.add_child(_box)


func show_run(r: RunState) -> void:
	for c: Node in _box.get_children():
		c.queue_free()
	var t: Label = RunUi.label("RUN OVER", 46, RunUi.C_WARN)
	t.add_theme_font_override("font", RunUi.title_font())
	_center(t)
	_center(RunUi.label("Fell on wave %d  ·  %d kills" % [r.wave, r.kills], 22))
	var guns: PackedStringArray = PackedStringArray()
	for g: WeaponData in r.guns:
		guns.append(g.display_name)
	var acts: PackedStringArray = PackedStringArray()
	for a: ActivePartData in r.loadout.actives():
		acts.append(a.display_name)
	var passives: int = 0
	for p: PartData in r.loadout.parts:
		if not p.fixed and not p.is_active():
			passives += 1
	_center(RunUi.label("%s  ·  %s" % [r.doctrine.display_name, ", ".join(guns)], 16, RunUi.C_ACCENT))
	_center(RunUi.label("%s  ·  %d passives" % [", ".join(acts), passives], 16, RunUi.C_ACCENT))
	var hist: Array[String] = r.history.slice(maxi(r.history.size() - 8, 0))
	if not hist.is_empty():
		_center(RunUi.label("\n".join(hist), 14, RunUi.C_DIM))
	_center(RunUi.label("A  main menu", 14, RunUi.C_DIM))
	visible = true
	_open_time = Time.get_ticks_msec()


func _center(l: Label) -> void:
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_box.add_child(l)


func _input(event: InputEvent) -> void:
	if not visible or Time.get_ticks_msec() - _open_time < 900:
		return
	if event.is_action_pressed(&"ui_accept"):
		get_viewport().set_input_as_handled()
		visible = false
		done.emit()
