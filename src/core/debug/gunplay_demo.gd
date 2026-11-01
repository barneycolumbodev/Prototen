class_name GunplayDemo
extends Node
## Scripted gunplay for cloud screenshots and scene tests
## (`-- --demo=range`, see tools/screenshot.sh). Aims down sights at each
## target in turn and fires, with trajectories visible, then holds the
## sights on the plates so the capture shows the aimed view.

signal finished

const SETTLE_FRAMES: int = 14
## How many rounds to put into each destructible wall.
const WALL_ROUNDS: int = 14

var room: TestRoom
var done: bool = false
var shots_fired: int = 0

var _queue: Array[Vector3] = []
var _frame: int = 0
var _wait: int = 30


func _ready() -> void:
	process_physics_priority = -20
	add_to_group(&"capture_busy")
	Ballistics.show_trajectories = true
	var r: ShootingRange = room.shooting_range
	room.player.global_position = Vector3(1.0, 0.0, 9.0)
	for d: TargetDummy in r.dummies:
		_queue.append(d.parts[&"head"].global_position)
		_queue.append(d.parts[&"chest"].global_position + Vector3(0.05, 0.02, 0))
		_queue.append(d.parts[&"l_thigh"].global_position)
	for p: PenPanel in r.panels:
		for k: int in 3:
			_queue.append(p.global_position + Vector3(-0.25 + k * 0.25, 0.9 + 0.1 * k, 0.05))
	for w: DestructibleWall in r.walls:
		for k: int in WALL_ROUNDS:
			var a: float = k * 2.39996  # golden-angle spiral: a tight group that breaks cells out
			_queue.append(w.global_position + Vector3(cos(a) * 0.05 * sqrt(k), 1.2 + sin(a) * 0.05 * sqrt(k), 0.02))
	for pl: SteelPlate in r.plates:
		_queue.append(pl.aim_points()[0])


func _physics_process(_delta: float) -> void:
	var player: Player = room.player
	var weapon: PlayerWeapon = player.weapon()
	_frame += 1
	if done:
		weapon.script_input(false, true)
		return
	if _wait > 0:
		_wait -= 1
		weapon.script_input(false, true)
		return
	if _queue.is_empty():
		done = true
		# Hold the sights on the poppers for the capture.
		aim_at(player, Vector3(-4.0, 1.4, -6.5))
		weapon.cam_recoil.reset()
		remove_from_group(&"capture_busy")
		finished.emit()
		return
	var target: Vector3 = _queue.pop_front()
	aim_at(player, target)
	weapon.cam_recoil.reset()
	weapon.bloom = 0.0
	weapon.script_input(true, true)
	shots_fired += 1
	_wait = SETTLE_FRAMES


static func aim_at(player: Player, target: Vector3) -> void:
	var eye: Vector3 = player.camera().global_position
	var d: Vector3 = target - eye
	player.set_view(atan2(-d.x, -d.z), asin(clampf(d.y / d.length(), -1.0, 1.0)))
