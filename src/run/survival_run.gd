class_name SurvivalRun
extends Node
## A Survival run on a map (docs/design.md §8): puts the RunState's body and
## guns on the player, runs the waves (SurvivalDirector), shows the supply
## drop after each wave (a boss drop first after a lieutenant wave), and
## the run-over screen when the operative dies. Named "Survival" in the
## scene (the pause menu hides the map and enemy toggles for it).
##
## The level sets `level`, `player`, `spawn_config`, `spawn_points` and
## `cover_regions`, then calls begin(doctrine, gun, active).

signal run_over(state: RunState)

var config: SurvivalConfig = preload("res://data/run/survival.tres")
var level: Node3D
var player: Player
var spawn_config: RollingSpawnConfig
var spawn_points: Array[Vector3] = []
var cover_regions: Array = []

var state: RunState
var director: SurvivalDirector
var drop_screen: DropScreen
var over_screen: RunOverScreen
## Seconds until the next step (drop, wave); -1 = waiting on something else.
var _wait: float = -1.0
var _next: Callable
## Drop screens still to show after this wave (a boss drop, then the supply drop).
class PendingDrop:
	extends RefCounted
	var offers: Array[RunState.Offer] = []
	var heading: String = ""
	var sub: String = ""
	var accent: Color = RunUi.C_ACCENT

	func _init(p_offers: Array[RunState.Offer], p_heading: String, p_sub: String, p_accent: Color) -> void:
		offers = p_offers
		heading = p_heading
		sub = p_sub
		accent = p_accent

var _pending: Array[PendingDrop] = []
var over: bool = false


func _ready() -> void:
	drop_screen = DropScreen.new()
	drop_screen.taken.connect(_on_taken)
	add_child(drop_screen)
	over_screen = RunOverScreen.new()
	over_screen.done.connect(_to_menu)
	add_child(over_screen)


func begin(doctrine: Doctrine, gun: WeaponData, active: ActivePartData, seed_value: int = 0) -> void:
	state = RunState.new(config, seed_value)
	state.start(doctrine, gun, active)
	_dress_player()
	player.weapon().set_guns(state.guns)
	_refill()
	player.augments.status.locked = true
	player.died.connect(_on_died)
	director = SurvivalDirector.new()
	director.name = "SurvivalDirector"
	director.survival = config
	director.config = spawn_config
	director.level = level
	director.player = player
	director.spawn_points = spawn_points
	director.cover_regions = cover_regions
	director.wave_cleared.connect(_on_wave_cleared)
	add_child(director)
	director.start()
	_after(1.5, _next_wave)
	if CaptureDirector.is_capturing():
		_capture_setup()


## Cloud captures: --capture-drops=N takes N drops first (a run in
## progress); --capture-drop shows the next supply drop, --capture-boss a
## boss drop, --capture-over the run-over screen.
func _capture_setup() -> void:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--capture-drops="):
			for i: int in a.get_slice("=", 1).to_int():
				state.wave = i + 1
				var d: Array[RunState.Offer] = state.roll_drop()
				if not d.is_empty():
					state.take(d[0])
			state.wave += 1
			_dress_player()
			player.weapon().set_guns(state.guns)
	for a: String in OS.get_cmdline_user_args():
		if a == "--capture-drop":
			_wait = -1.0
			var d2: Array[RunState.Offer] = state.roll_drop()
			drop_screen.show_offers(d2, "WAVE %d CLEARED" % maxi(state.wave, 1), "Supply drop  ·  %s" % ("Choose one" if d2.size() > 1 else "Delivered"))
		elif a == "--capture-boss":
			_wait = -1.0
			state.wave = 5
			var bc: BossConfig = _boss_config(5)
			var bd: Array[RunState.Offer] = state.roll_boss_drops(bc.drop)
			drop_screen.show_offers(bd, "%s IS DEAD" % bc.title, "Boss drop  ·  his %s" % bc.drop.display_name, RunUi.C_GOLD)
		elif a == "--capture-over":
			_wait = -1.0
			state.kills = 57
			over = true
			over_screen.show_run(state)


func _process(delta: float) -> void:
	if _wait >= 0.0:
		_wait -= delta
		if _wait < 0.0:
			_wait = -1.0
			var f: Callable = _next
			_next = Callable()
			if f.is_valid():
				f.call()
	if director and not over:
		state.kills = director.kills


func _after(seconds: float, f: Callable) -> void:
	_wait = seconds
	_next = f


func _next_wave() -> void:
	state.wave += 1
	director.begin_wave(state.wave)


func _on_wave_cleared(wave: int) -> void:
	if over:
		return
	_refill()
	_pending.clear()
	if config.is_boss_wave(wave):
		var boss_cfg: BossConfig = _boss_config(wave)
		if boss_cfg:
			# His own hardware: the active he carried, or its next mark (§8.7).
			var bd: Array[RunState.Offer] = state.roll_boss_drops(boss_cfg.drop)
			if not bd.is_empty():
				var what: String = "his %s" % boss_cfg.drop.display_name if boss_cfg.drop else "his hardware"
				_pending.append(PendingDrop.new(bd, "%s IS DEAD" % boss_cfg.title, "Boss drop  ·  %s%s" % [what, "  ·  choose one" if bd.size() > 1 else ""], RunUi.C_GOLD))
		else:
			var b: RunState.Offer = state.roll_boss_drop()
			if b:
				var boss_one: Array[RunState.Offer] = [b]
				_pending.append(PendingDrop.new(boss_one, "LIEUTENANTS DOWN", "Boss drop  ·  wave %d" % wave, RunUi.C_GOLD))
	var d: Array[RunState.Offer] = state.roll_drop()
	if not d.is_empty():
		var sub: String = "Choose one" if d.size() > 1 else "Delivered"
		_pending.append(PendingDrop.new(d, "WAVE %d CLEARED" % wave, "Supply drop  ·  %s" % sub, RunUi.C_ACCENT))
	_after(config.drop_delay, _show_next_drop)


## The BossConfig of wave `wave`'s boss, or null (a lieutenant wave).
func _boss_config(wave: int) -> BossConfig:
	var role: String = config.boss_for(wave)
	if role == "":
		return null
	var ec: EnemyConfig = load("res://data/enemies/%s.tres" % role) as EnemyConfig
	return ec.boss if ec else null


func _show_next_drop() -> void:
	if over:
		return
	if _pending.is_empty():
		_after(config.next_wave_delay, _next_wave)
		return
	var p: PendingDrop = _pending.pop_front()
	drop_screen.show_offers(p.offers, p.heading, p.sub, p.accent)


func _on_taken(o: RunState.Offer) -> void:
	state.take(o)
	_dress_player()
	if o.item.kind() == RunItem.Kind.WEAPON:
		player.weapon().give_gun(o.item.item as WeaponData)
	_refill()
	_show_next_drop()


func _dress_player() -> void:
	player.apply_loadout(state.loadout.copy())


## Between waves: health and active charges back to full (§8.2).
func _refill() -> void:
	player.health = player.max_health()
	if player.augments:
		for p: ActivePart in player.augments.parts.values():
			p.charge = p.charge_capacity()


func _on_died() -> void:
	if over:
		return
	over = true
	state.kills = director.kills
	director.halt()
	_wait = -1.0
	run_over.emit(state)
	get_tree().create_timer(2.0).timeout.connect(func() -> void: over_screen.show_run(state))


func _to_menu() -> void:
	ChinatownMap.menu_on_load = true
	get_tree().change_scene_to_file.call_deferred("res://src/levels/chinatown/chinatown.tscn")
