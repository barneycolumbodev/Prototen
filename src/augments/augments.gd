class_name Augments
extends Node
## The player's active parts (docs/design.md §3.4): one ActivePart node per
## active in the loadout, up to three. They all fire from LB; the D-pad picks
## which one LB uses (owner, 2026-11-07): left = slot 1, down = slot 2,
## right = slot 3. A press of LB toggles the selected part. Parts keep running
## when you select another one, so RX-9 can stay on while you deploy the arm
## cannon; select it again and press LB to stop it.
## Also owns the actives' HUD (charge bars above the health bar) and stops
## everything when the player dies.

const USE: StringName = &"active_use"
const SELECT: Array[StringName] = [&"active_select_1", &"active_select_2", &"active_select_3"]
## Short labels for each slot's D-pad direction.
const SLOT_NAMES: Array[String] = ["D-LEFT", "D-DOWN", "D-RIGHT"]
const SLOT_ARROWS: Array[String] = ["<", "v", ">"]

signal selected_changed(slot: int)

var player: Player
var parts: Dictionary[int, ActivePart] = {}
## The slot LB fires (0 = no actives installed).
var selected: int = 0
var hud: AugmentHud
## The body-status screen (View button).
var status: BodyStatus


func _ready() -> void:
	player = get_parent() as Player
	_build_parts()
	player.died.connect(_on_died)
	status = BodyStatus.new()
	status.player = player
	add_child(status)
	if "--capture-body" in OS.get_cmdline_user_args():
		_capture_setup.call_deferred()
	if not CaptureDirector.is_capturing():
		hud = AugmentHud.new()
		hud.augments = self
		add_child(hud)


## Cloud captures of the loadout screen: --capture-body opens it;
## --capture-parts=a,b installs parts first; --capture-preset=N applies a
## preset; --capture-browse=id puts the cursor on that part (its card and
## preview); --capture-yaw=deg turns the model; --capture-bare: helmet off;
## --capture-zoom: the close-up; --capture-active=id: the Actives row on
## that part; --capture-colors=channel:rrggbb[:finish],...: paint and show
## the Colours page ("part+<id>" for a part's hardware);
## --capture-color-row=N: the sliders open on row N.
func _capture_setup() -> void:
	var lib: PartLibrary = LoadoutStore.LIBRARY
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--capture-preset="):
			player.apply_loadout(LoadoutStore.presets()[a.get_slice("=", 1).to_int()].copy())
		elif a.begins_with("--capture-parts="):
			var lo: BodyLoadout = player.loadout.copy()
			for id: String in a.get_slice("=", 1).split(","):
				var p: PartData = lib.find(StringName(id))
				if p:
					lo.install(p)
			player.apply_loadout(lo)
	status.open()
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--capture-browse="):
			var p: PartData = lib.find(StringName(a.get_slice("=", 1)))
			if p:
				status.select_row(p.location)
				status.browse_to(p.id)
		elif a.begins_with("--capture-yaw="):
			status.set_yaw(deg_to_rad(a.get_slice("=", 1).to_float()))
		elif a.begins_with("--capture-active="):
			# The Actives row, on this part.
			status.select_row(BodyStatus.ROW_ACTIVES)
			status.browse_to(StringName(a.get_slice("=", 1)))
		elif a.begins_with("--capture-colors="):
			# channel:rrggbb[:finish],... painted on, then the Colours page.
			for spec: String in a.get_slice("=", 1).split(","):
				var bits: PackedStringArray = spec.split(":")
				var ch: StringName = StringName(bits[0].replace("+", ":"))
				status.working_colors.set_color(ch, Color.html(bits[1]))
				if bits.size() > 2:
					status.working_colors.set_finish(ch, bits[2].to_int())
			status.colors_changed = true
			status.set_page(BodyStatus.Page.COLOURS)
		elif a.begins_with("--capture-color-row="):
			status.color_row = a.get_slice("=", 1).to_int()
			status.editing = true
			status.set_page(BodyStatus.Page.COLOURS)
			status.editing = true
			status._refresh()
		elif a == "--capture-bare":
			status.toggle_helmet()
		elif a == "--capture-zoom":
			status.set_zoom(true)


## The loadout changed (loadout screen): rebuild the active parts. A part
## that stays keeps its charge.
func rebuild() -> void:
	var kept: Dictionary[StringName, float] = {}
	for p: ActivePart in parts.values():
		p.interrupt()
		kept[p.data.id] = p.charge
		remove_child(p)
		p.queue_free()
	parts.clear()
	selected = 0
	_build_parts()
	for p: ActivePart in parts.values():
		if kept.has(p.data.id):
			p.charge = minf(kept[p.data.id], p.charge_capacity())
	selected_changed.emit(selected)


func _build_parts() -> void:
	# D-pad slots follow the order the actives were installed in.
	var at: int = 0
	for a: ActivePartData in player.loadout.actives():
		at += 1
		if at > BodyLoadout.MAX_ACTIVES:
			break
		if a.behaviour == null:
			push_warning("Augments: %s has no behaviour script" % a.id)
			continue
		var script: GDScript = a.behaviour as GDScript
		var obj: Object = script.new() if script else null
		var node: ActivePart = obj as ActivePart
		if node == null:
			push_warning("Augments: %s's behaviour isn't an ActivePart" % a.id)
			continue
		node.name = String(a.id)
		node.setup(a, player.body, player)
		add_child(node)
		node.slot = at
		parts[at] = node
	for slot: int in [1, 2, 3]:
		if parts.has(slot):
			selected = slot
			break


func part(slot: int) -> ActivePart:
	return parts.get(slot)


func selected_part() -> ActivePart:
	return parts.get(selected)


## The part with this id, or null.
func find(id: StringName) -> ActivePart:
	for p: ActivePart in parts.values():
		if p.data.id == id:
			return p
	return null


## Makes `slot` the one LB fires. Returns false if nothing is installed there.
func select(slot: int) -> bool:
	if not parts.has(slot):
		return false
	if slot != selected:
		selected = slot
		Sfx.play_ui(&"wheel_tick", -8.0, 0.02)
		selected_changed.emit(slot)
	if hud:
		hud.flash_selection()
	return true


## LB: toggle the selected part.
func use_selected() -> void:
	var p: ActivePart = selected_part()
	if p:
		p.toggle()


func _process(_delta: float) -> void:
	if not player.input_enabled or player.look_blocked or player.dead or get_tree().paused:
		return
	for i: int in SELECT.size():
		if Input.is_action_just_pressed(SELECT[i]):
			select(i + 1)
	if Input.is_action_just_pressed(USE):
		use_selected()


func _on_died() -> void:
	for p: ActivePart in parts.values():
		p.interrupt()
