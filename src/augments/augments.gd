class_name Augments
extends Node
## The player's active parts (docs/design.md §3.4): one ActivePart node per
## active in the loadout, on its button (active_1 = LB, active_2 = RB,
## active_3 = D-pad up). A press toggles the part. Also owns the actives'
## HUD (charge bars above the health bar) and stops everything when the
## player dies.

const ACTIONS: Array[StringName] = [&"active_1", &"active_2", &"active_3"]
const BUTTONS: Array[String] = ["LB", "RB", "D-UP"]

var player: Player
var parts: Dictionary[int, ActivePart] = {}
var hud: AugmentHud


func _ready() -> void:
	player = get_parent() as Player
	for a: ActivePartData in player.loadout.actives():
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
		parts[a.slot] = node
	player.died.connect(_on_died)
	if not parts.is_empty() and not CaptureDirector.is_capturing():
		hud = AugmentHud.new()
		hud.augments = self
		add_child(hud)


func part(slot: int) -> ActivePart:
	return parts.get(slot)


## The part with this id, or null.
func find(id: StringName) -> ActivePart:
	for p: ActivePart in parts.values():
		if p.data.id == id:
			return p
	return null


func _process(_delta: float) -> void:
	if not player.input_enabled or player.look_blocked or player.dead or get_tree().paused:
		return
	for i: int in ACTIONS.size():
		if Input.is_action_just_pressed(ACTIONS[i]) and parts.has(i + 1):
			parts[i + 1].toggle()


func _on_died() -> void:
	for p: ActivePart in parts.values():
		p.interrupt()
