class_name FirstTimeTips
extends Node
## First-time prompts in Survival (docs/design.md §8.11): each tip shows once
## ever, the first time its moment comes up in a run, on the PromptCard in
## the top right, for a few seconds. Nothing pauses. Tips queue, one at a
## time. SurvivalRun owns this node and calls `trigger` at the moments it
## knows about (a drop, a new gun); the node watches the rest itself (the
## director's spawns, the last man, low health).
##
## Pause → Options → "Tips: show again" brings them all back.

## id → [title, text]. Button names as on the pad (CLAUDE.md §9.4).
const TIPS: Dictionary[StringName, Array] = {
	&"run_start": ["SURVIVAL", "Clear each wave. A supply drop comes after every one, and a boss every fifth. Die and the run is over."],
	&"mark_one": ["MK I", "Your active starts tuned down. Its marks (Mk II, then Mk III) come in supply drops."],
	&"last_man": ["LAST HOSTILE", "The last man of a wave is marked on your HUD. Go and get him."],
	&"drop": ["SUPPLY DROP", "Pick one. Your doctrine and what you already carry steer what turns up next."],
	&"new_gun": ["NEW GUN", "Tap Y for your last gun. Hold Y for the wheel: the stick picks a type, the D-pad scrolls."],
	&"new_active": ["NEW ACTIVE", "D-pad left, down, right picks which part LB fires."],
	&"hatchet": ["HATCHET MAN", "He comes in fast from cover. When the arm goes up, slide out of the chop or hit him first with R3."],
	&"dog": ["ATTACK DOGS", "They run straight at you and leap. R3 knocks a dog out of the air."],
	&"flamer": ["FLAMER", "Shoot the can in his hand. It goes up and takes the men near him with it."],
	&"boss": ["BOSS", "Wear him down. When he drops to one knee, walk up to him and press RB."],
	&"low_health": ["HURT", "Get out of sight. Health comes back once you stop taking hits."],
}

var config: TutorialConfig = preload("res://data/ui/tutorial.tres")
var player: Player
var card: PromptCard
## Tips waiting their turn.
var queue: Array[StringName] = []
## The tip on the card now (&"" = none).
var showing: StringName = &""
var _left: float = 0.0
var _gap: float = 0.0
var _director: SurvivalDirector


func _ready() -> void:
	card = PromptCard.new()
	card.name = "TipCard"
	add_child(card)
	EventBus.wave_changed.connect(_on_wave)


## Watches this director's spawns (melee men, flamers, dogs, the boss).
func watch(director: SurvivalDirector) -> void:
	_director = director
	director.spawned.connect(_on_spawned)
	director.dog_spawned.connect(func(_d: AttackDog) -> void: trigger(&"dog"))
	director.boss_arrived.connect(func(_b: Enemy) -> void: trigger(&"boss"))


## A run began: its first two tips come a moment later.
func run_started() -> void:
	_gap = config.run_start_delay
	trigger(&"run_start")
	trigger(&"mark_one")


## Shows tip `id` if it has never been shown (queued behind the one up now).
func trigger(id: StringName) -> void:
	if not TIPS.has(id) or TutorialStore.seen(id) or id == showing or id in queue:
		return
	queue.append(id)


func _on_spawned(e: Enemy) -> void:
	if e.config == null:
		return
	if e.config.flamer:
		trigger(&"flamer")
	elif e.config.melee and e.config.boss == null:
		trigger(&"hatchet")


func _on_wave(wave: int, left: int) -> void:
	if wave > 0 and left == 1:
		trigger(&"last_man")


func _process(delta: float) -> void:
	if player and not player.dead and player.health_fraction() < config.low_health:
		trigger(&"low_health")
	if showing != &"":
		_left -= delta
		if _left <= 0.0:
			showing = &""
			card.dismiss()
			_gap = config.tip_gap
		return
	if _gap > 0.0:
		_gap -= delta
		return
	if not queue.is_empty():
		var id: StringName = queue.pop_front()
		_show(id)


func _show(id: StringName) -> void:
	var t: Array = TIPS[id]
	showing = id
	_left = config.tip_seconds
	TutorialStore.mark(id)
	card.heading = "FIRST TIME"
	card.title = t[0]
	card.body = t[1]
	card.checks = []
	card.hint = ""
	card.progress = -1.0
	card.present()
	card.flash()
	Sfx.play_ui(&"wheel_tick", -6.0, 0.0)
