class_name RollingSpawner
extends Node
## Rolling enemy spawns for open maps (owner, 2026-11-04). Starts with
## `config.start_count` triad members; whenever fewer than `config.low_water`
## are still fighting (the dead, surrendered and crawling don't count),
## `config.batch` more come in. Each one appears at a spawn point the player
## can't see (line of sight from the camera blocked at chest and head
## height), not too close, preferably behind the player, and knows roughly
## where the player is. Dying restarts the round.
##
## The level sets `level`, `player`, `spawn_points` and `cover_regions`
## ([origin, half_extent] pairs for Squad.build_cover) before `start()`.
## Named "WaveMode" in the scene so the pause menu's toggle works on it.

signal spawned(e: Enemy)

var config: RollingSpawnConfig
var level: Node3D
var player: Player
var spawn_points: Array[Vector3] = []
var cover_regions: Array = []
var squad: Squad
var running: bool = false
var kills: int = 0
var spawned_total: int = 0
var enemies: Array[Enemy] = []

var _queue: int = 0
var _timer: float = 0.0
var _restart: float = -1.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _recent: Array[int] = []


func _ready() -> void:
	_rng.randomize()
	EventBus.player_died.connect(_on_player_died)


func start() -> void:
	if running:
		return
	running = true
	squad = Squad.new()
	squad.name = "Squad"
	add_child(squad)
	squad.set_player(player)
	var first: bool = true
	for region: Array in cover_regions:
		var origin: Vector3 = region[0]
		var half: float = region[1]
		squad.build_cover(origin, half, level.get_world_3d(), not first)
		first = false
	kills = 0
	spawned_total = 0
	_queue = config.start_count
	_timer = 0.5
	_emit()


func stop() -> void:
	running = false
	for e: Enemy in enemies:
		if is_instance_valid(e):
			e.queue_free()
	enemies.clear()
	_queue = 0
	if squad:
		squad.queue_free()
		squad = null
	EventBus.wave_changed.emit(0, 0)


func toggle() -> void:
	if running:
		stop()
	else:
		start()


func fighting() -> int:
	return squad.fighting_count() if squad else 0


func alive() -> int:
	var n: int = 0
	for e: Enemy in enemies:
		if is_instance_valid(e) and e.alive:
			n += 1
	return n


## The rule: below `low_water` fighters and nothing already on its way → send a batch.
static func wants_batch(fighting_now: int, queued: int, cfg: RollingSpawnConfig) -> bool:
	return queued == 0 and fighting_now < cfg.low_water


func _process(delta: float) -> void:
	if _restart >= 0.0:
		_restart -= delta
		if _restart < 0.0:
			_restart = -1.0
			player.respawn()
			if running:
				stop()
				start()
		return
	if not running:
		return
	if wants_batch(fighting(), _queue, config):
		_queue = config.batch
		_timer = minf(_timer, 0.8)
	if _queue > 0:
		_timer -= delta
		if _timer <= 0.0 and alive() < config.max_alive:
			var i: int = pick_spawn()
			if i >= 0:
				_spawn(config.pick_role(_rng.randf()), spawn_points[i])
				_queue -= 1
				_timer = config.spawn_gap
			else:
				_timer = 0.3  # nowhere hidden right now: try again shortly
	_emit()


func _emit() -> void:
	EventBus.score_changed.emit(kills, fighting() + _queue)


## Index of the best hidden spawn point, or -1.
func pick_spawn() -> int:
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var space: PhysicsDirectSpaceState3D = level.get_world_3d().direct_space_state
	var best: Array[int] = []
	var scores: Array[float] = []
	for i: int in spawn_points.size():
		var p: Vector3 = spawn_points[i]
		var d: float = p.distance_to(player.global_position)
		if d < config.min_distance:
			continue
		if _occupied(p):
			continue
		if sees(space, eye, p):
			continue
		var to: Vector3 = (p - eye).normalized()
		var behind: float = 1.0 - clampf(fwd.dot(to), -1.0, 1.0)  # 0 ahead .. 2 behind
		var band: float = 0.0 if d >= config.preferred_min and d <= config.preferred_max else minf(absf(d - clampf(d, config.preferred_min, config.preferred_max)) / 10.0, 1.5)
		var score: float = behind - band - (0.8 if i in _recent else 0.0) + _rng.randf() * 0.6
		best.append(i)
		scores.append(score)
	if best.is_empty():
		return -1
	var top: int = 0
	for k: int in scores.size():
		if scores[k] > scores[top]:
			top = k
	var pick: int = best[top]
	_recent.append(pick)
	if _recent.size() > 4:
		_recent.pop_front()
	return pick


## Can the player's eye see a man standing at `p` (chest or head)?
static func sees(space: PhysicsDirectSpaceState3D, eye: Vector3, p: Vector3) -> bool:
	for h: float in [1.0, 1.65]:
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, p + Vector3.UP * h, Ballistics.LAYER_WORLD)
		if space.intersect_ray(q).is_empty():
			return true
	return false


func _occupied(p: Vector3) -> bool:
	for e: Enemy in enemies:
		if is_instance_valid(e) and e.alive and e.global_position.distance_to(p) < 1.6:
			return true
	return false


func _spawn(role: String, at: Vector3) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % role) as EnemyConfig
	squad.add(e)
	level.add_child(e)
	# A little jitter so repeat spawns don't stack, but never into view: at a
	# doorway or corner 0.3 m can be enough to step out from cover.
	var jit: Vector3 = at + Vector3(_rng.randf_range(-0.3, 0.3), 0.0, _rng.randf_range(-0.3, 0.3))
	if sees(level.get_world_3d().direct_space_state, player.camera().global_position, jit):
		jit = at
	e.global_position = jit + Vector3(0, 0.05, 0)
	var to: Vector3 = player.global_position - e.global_position
	e.face(atan2(to.x, to.z))
	e.awareness = config.arrival_awareness
	e.last_known = player.global_position + Vector3(_rng.randf_range(-4, 4), 0, _rng.randf_range(-4, 4))
	e._enter(Enemy.State.ALERT)
	var blob: MeshInstance3D = _blob_shadow()
	e.add_child(blob)
	e.died.connect(func(_x: Enemy) -> void:
		kills += 1
		if is_instance_valid(blob):
			blob.queue_free()
		_emit())
	enemies.append(e)
	spawned_total += 1
	_cleanup()
	spawned.emit(e)
	return e


static var _blob_mesh: QuadMesh


## A soft dark disc at the feet (baked maps get no live shadows).
static func _blob_shadow() -> MeshInstance3D:
	if _blob_mesh == null:
		_blob_mesh = QuadMesh.new()
		_blob_mesh.size = Vector2(1.1, 1.1)
		_blob_mesh.orientation = PlaneMesh.FACE_Y
		var mat: ShaderMaterial = ShaderMaterial.new()
		mat.shader = preload("res://src/levels/blob_shadow.gdshader")
		_blob_mesh.material = mat
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.name = "BlobShadow"
	mi.mesh = _blob_mesh
	mi.position = Vector3(0, 0.03, 0)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


## Oldest bodies go once there are too many.
func _cleanup() -> void:
	var bodies: Array[Enemy] = []
	var keep: Array[Enemy] = []
	for e: Enemy in enemies:
		if not is_instance_valid(e):
			continue
		if not e.alive:
			bodies.append(e)
		keep.append(e)
	while bodies.size() > config.max_bodies:
		var old: Enemy = bodies.pop_front()
		keep.erase(old)
		old.queue_free()
	enemies = keep


func _on_player_died() -> void:
	_restart = player.body_config.respawn_time
