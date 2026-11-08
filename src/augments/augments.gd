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
	for a: ActivePartData in player.loadout.actives():
		if a.behaviour == null:
			push_warning("Augments: %s has no behaviour script" % a.id)
			continue
		if parts.has(a.slot):
			push_warning("Augments: %s wants slot %d, which is taken" % [a.id, a.slot])
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
		parts[a.slot] = node
	for s: int in [1, 2, 3]:
		if parts.has(s):
			selected = s
			break
	player.died.connect(_on_died)
	status = BodyStatus.new()
	status.player = player
	add_child(status)
	if "--capture-body" in OS.get_cmdline_user_args():
		status.open.call_deferred()
		if "--capture-bare" in OS.get_cmdline_user_args():
			status.toggle_helmet.call_deferred()
	if not parts.is_empty() and not CaptureDirector.is_capturing():
		hud = AugmentHud.new()
		hud.augments = self
		add_child(hud)


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
