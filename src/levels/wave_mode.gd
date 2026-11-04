class_name WaveMode
extends Node
## Wave mode in the test room (CLAUDE.md §12, M1): the range targets clear
## away and triad squads come in waves from the edges of the room. Each wave
## is bigger (up to 12 at once, CLAUDE.md §8): Gunmen first, Enforcers from
## wave 2, a Red Pole leading from wave 3. A wave is over when nobody is left
## fighting (the dead, the surrendered and the crawling don't count). Dying
## restarts from wave 1. Pause menu → Wave mode starts and stops it.

const MAX_ACTIVE: int = 12
const MAX_BODIES: int = 10
const BREAK_TIME: float = 5.0
const SPAWN_GAP: float = 0.7
## Edges of the room, ground floor and mezzanine.
const SPAWNS: Array[Vector3] = [
	Vector3(-13.0, 0.0, -5.0), Vector3(12.5, 0.0, -1.5), Vector3(-6.0, 3.5, -13.5), Vector3(6.0, 3.5, -13.5),
	Vector3(-13.5, 0.0, 6.0), Vector3(14.0, 0.0, 4.0), Vector3(0.0, 3.5, -14.0), Vector3(-2.0, 0.0, -7.5),
]

var room: TestRoom
var squad: Squad
var wave: int = 0
var running: bool = false
var kills: int = 0
var enemies: Array[Enemy] = []

var _queue: Array[String] = []
var _spawn_timer: float = 0.0
var _break: float = 0.0
var _nav: NavigationRegion3D
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _restart: float = -1.0


func _ready() -> void:
	_rng.randomize()
	EventBus.player_died.connect(_on_player_died)


func start() -> void:
	if running:
		return
	running = true
	room.shooting_range.clear_targets()
	_build_navigation()
	squad = Squad.new()
	squad.name = "WaveSquad"
	add_child(squad)
	squad.set_player(room.player)
	squad.build_cover(Vector3(0, 0, 0), 15.5, room.get_world_3d())
	squad.build_cover(Vector3(0, TestRoom.MEZZ_TOP, -12.0), 15.5, room.get_world_3d(), true)
	wave = 0
	kills = 0
	_next_wave()


func stop() -> void:
	running = false
	for e: Enemy in enemies:
		if is_instance_valid(e):
			e.queue_free()
	enemies.clear()
	_queue.clear()
	if squad:
		squad.queue_free()
		squad = null
	EventBus.wave_changed.emit(0, 0)
	room.shooting_range.restore_targets()


func toggle() -> void:
	if running:
		stop()
	else:
		start()


## Who's in wave `n`: role names.
static func composition(n: int) -> Array[String]:
	var count: int = mini(3 + n, MAX_ACTIVE)
	var out: Array[String] = []
	if n >= 3:
		out.append("red_pole")
	for i: int in mini(n / 2, 3):
		out.append("enforcer")
	while out.size() < count:
		out.append("gunman")
	return out


func _next_wave() -> void:
	wave += 1
	_queue = composition(wave)
	_spawn_timer = 1.5
	EventBus.wave_changed.emit(wave, -1)


func _process(delta: float) -> void:
	if _restart >= 0.0:
		_restart -= delta
		if _restart < 0.0:
			_restart = -1.0
			room.player.respawn()
			if running:
				stop()
				start()
		return
	if not running:
		return
	if not _queue.is_empty():
		_spawn_timer -= delta
		if _spawn_timer <= 0.0 and _alive() < MAX_ACTIVE:
			var role: String = _queue.pop_front()
			_spawn(role)
			_spawn_timer = SPAWN_GAP
		return
	var left: int = squad.fighting_count()
	if left == 0:
		if _break <= 0.0:
			_break = BREAK_TIME
			EventBus.wave_changed.emit(wave, 0)
		_break -= delta
		if _break <= 0.0:
			_break = 0.0
			_cleanup(true)
			_next_wave()
	else:
		EventBus.wave_changed.emit(wave, left)


func _alive() -> int:
	var n: int = 0
	for e: Enemy in enemies:
		if is_instance_valid(e) and e.alive:
			n += 1
	return n


func _spawn(role: String) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % role) as EnemyConfig
	squad.add(e)
	room.add_child(e)
	e.global_position = _pick_spawn()
	var to: Vector3 = room.player.global_position - e.global_position
	e.face(atan2(to.x, to.z))
	e.awareness = 0.6
	e.last_known = room.player.global_position
	e._enter(Enemy.State.ALERT)
	e.died.connect(func(_x: Enemy) -> void: kills += 1)
	enemies.append(e)
	_cleanup(false)
	return e


var _last_spawns: Array[int] = []


## A spawn point away from the player, not one of the last few used.
func _pick_spawn() -> Vector3:
	var p: Vector3 = room.player.global_position
	var picks: Array[int] = []
	for i: int in SPAWNS.size():
		if SPAWNS[i].distance_to(p) > 9.0 and i not in _last_spawns:
			picks.append(i)
	if picks.is_empty():
		picks.append(_rng.randi() % SPAWNS.size())
	var i: int = picks[_rng.randi() % picks.size()]
	_last_spawns.append(i)
	if _last_spawns.size() > 3:
		_last_spawns.pop_front()
	return SPAWNS[i] + Vector3(_rng.randf_range(-0.6, 0.6), 0.05, _rng.randf_range(-0.6, 0.6))


## Keeps the body count down (oldest first); `all_out` also removes the
## surrendered and crawling at the end of a wave.
func _cleanup(all_out: bool) -> void:
	var bodies: Array[Enemy] = []
	var keep: Array[Enemy] = []
	for e: Enemy in enemies:
		if not is_instance_valid(e):
			continue
		if not e.alive:
			bodies.append(e)
		elif all_out and e.state in [Enemy.State.SURRENDER, Enemy.State.CRAWL]:
			e.queue_free()
			continue
		keep.append(e)
	while bodies.size() > MAX_BODIES:
		var old: Enemy = bodies.pop_front()
		keep.erase(old)
		old.queue_free()
	enemies = keep


func _on_player_died() -> void:
	_restart = room.player.body_config.respawn_time


func _build_navigation() -> void:
	if _nav:
		return
	_nav = NavigationRegion3D.new()
	_nav.name = "Navigation"
	var nm: NavigationMesh = NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = Ballistics.LAYER_WORLD
	nm.agent_radius = 0.5
	nm.agent_height = 1.75
	nm.agent_max_climb = 0.25
	nm.agent_max_slope = 40.0
	room.add_child(_nav)
	var source: NavigationMeshSourceGeometryData3D = NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nm, source, room)
	NavigationServer3D.bake_from_source_geometry_data(nm, source)
	_nav.navigation_mesh = nm
