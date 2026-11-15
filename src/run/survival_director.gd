class_name SurvivalDirector
extends RollingSpawner
## Survival waves on an open map (docs/design.md §8.6). Each wave's men
## (SurvivalWaves.compose) come in one after another at spawn points the
## player can't see, like the rolling spawns, never more than `max_alive`
## at once: a big wave is fought as reinforcements arrive. A wave is over
## when its queue is empty and nobody is left fighting; the surrendered and
## crawling are cleared away. Dying doesn't restart anything here:
## SurvivalRun ends the run.

signal wave_cleared(wave: int)
## A boss wave's boss arrived (his entrance starts now).
signal boss_arrived(boss: Enemy)

var survival: SurvivalConfig
var wave: int = 0
## Men still to come in this wave.
var queue: Array[String] = []
var in_wave: bool = false
## This wave's boss (docs/design.md §8.7), or null.
var boss: Enemy
## Plays his entrance (off in tests that drive the fight directly).
var boss_intro: bool = true
var _last_left: int = -2
## How long each fighting man has gone without seeing the operative, once
## the whole wave is in (stragglers, SurvivalConfig.straggler_*).
var _out_of_touch: Dictionary[Enemy, float] = {}
var _straggler_tick: float = 0.0
const STRAGGLER_TICK: float = 0.5


## Sets up the squad and cover; no one comes until begin_wave().
func start() -> void:
	if running:
		return
	running = true
	_build_squad()
	kills = 0
	spawned_total = 0
	wave = 0
	for e: WaveEnemy in survival.roster:
		if e.first_wave <= 2:
			_fill_looks(e.role, LOOKS_AHEAD + 2)
	for b: String in survival.bosses:
		_fill_looks(b, 1)


func begin_wave(n: int) -> void:
	wave = n
	queue = SurvivalWaves.compose(n, survival, _rng)
	in_wave = true
	_timer = 1.2
	_last_left = -2
	_out_of_touch.clear()
	# Looks for this wave's roles start baking now.
	var seen: Array[String] = []
	for r: String in queue:
		if r not in seen:
			seen.append(r)
			_fill_looks(r, LOOKS_AHEAD + mini(queue.count(r), 4))
	EventBus.wave_changed.emit(wave, -1)
	var role: String = survival.boss_for(n)
	if role != "":
		_bring_boss(role)


## The boss drops in front of the operative (his entrance, BossIntro); his
## escorts come in after it.
func _bring_boss(role: String) -> void:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % role) as EnemyConfig
	e.look = _take_look(role)
	squad.add(e)
	level.add_child(e)
	var at: Vector3 = BossIntro.pick_landing(player, e.config.boss)
	e.global_position = at + Vector3.UP * 0.05
	var to: Vector3 = player.global_position - at
	e.face(atan2(to.x, to.z))
	e.awareness = 1.0
	e.last_known = player.global_position
	blobs.track(e)
	e.died.connect(func(_x: Enemy) -> void:
		kills += 1)
	enemies.append(e)
	spawned_total += 1
	boss = e
	if boss_intro:
		var intro: BossIntro = BossIntro.new()
		intro.name = "BossIntro"
		intro.boss = e
		intro.player = player
		intro.landing = at
		level.add_child(intro)
	else:
		e._enter(Enemy.State.COMBAT)
	_timer = survival.boss_escort_delay if boss_intro else 1.2
	boss_arrived.emit(e)


func left() -> int:
	return fighting() + queue.size()


func _process(delta: float) -> void:
	if not running or not in_wave:
		return
	if not queue.is_empty():
		_timer -= delta
		if _timer <= 0.0 and alive() < config.max_alive:
			var i: int = pick_spawn()
			if i >= 0:
				var role: String = queue.pop_front()
				_spawn(role, spawn_points[i])
				_timer = config.spawn_gap
			else:
				_timer = 0.3
	if queue.is_empty():
		_straggler_tick -= delta
		if _straggler_tick <= 0.0:
			_straggler_tick = STRAGGLER_TICK
			watch_stragglers(STRAGGLER_TICK)
	var n: int = left()
	if queue.is_empty() and fighting() == 0:
		in_wave = false
		clear_out()
		EventBus.wave_changed.emit(wave, 0)
		wave_cleared.emit(wave)
		return
	if n != _last_left and _timer < 1.0:
		_last_left = n
		EventBus.wave_changed.emit(wave, n)


## The last of a wave can't hold it up forever: whoever hasn't seen the
## operative for a while is told where he is, and whoever stays lost (stuck
## somewhere, or thrown off the map) comes back in out of sight. `dt`: the
## seconds since the last look.
func watch_stragglers(dt: float) -> void:
	var space: PhysicsDirectSpaceState3D = level.get_world_3d().direct_space_state
	var eye: Vector3 = player.camera().global_position
	var seen: Dictionary[Enemy, float] = {}
	for e: Enemy in enemies:
		if not is_instance_valid(e) or not e.alive or e.boss or e.held or e.out_of_fight():
			continue
		var t: float = 0.0 if e.sees_player else _out_of_touch.get(e, 0.0) + dt
		var fell: bool = e.global_position.y < survival.straggler_floor_y
		if fell or (t >= survival.straggler_move_after and not sees(space, eye, e.global_position)):
			var i: int = pick_spawn()
			if i >= 0:
				e.relocate(spawn_points[i])
				t = survival.straggler_hunt_after
		if t >= survival.straggler_hunt_after:
			e.hunt(player.global_position)
		seen[e] = t
	_out_of_touch = seen


## End of a wave: those out of the fight go (surrendered, crawling, fled
## without a gun), bodies beyond the cap go.
func clear_out() -> void:
	for e: Enemy in enemies.duplicate():
		if is_instance_valid(e) and e.alive and e.out_of_fight():
			enemies.erase(e)
			e.queue_free()
	_cleanup()


## Stops sending men (the run is over); those in the street stay.
func halt() -> void:
	queue.clear()
	in_wave = false


func _on_player_died() -> void:
	halt()
