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
## "range": aimed shots at every target. "fire": hip-fire a few rounds and
## freeze time just after the last one (flash, shell and recoil in frame).
## "hip": no shots, just the hip-fire hold (for checking viewmodel placement).
## "wheel": hold Y with the stick on `--wheel-pick=<slot>` (weapon wheel open).
## `--aim=dummy` holds the final aim on a dummy (crimson reticle).
## "ads": no shots, aimed (sight picture). "burst": hold the trigger from the
## hip at a dummy for `BURST_FRAMES`, then freeze time mid-burst.
## Options: `--weapon=<i>` (loadout slot), `--ammo=<i>` (shell type).
var mode: String = "range"
const BURST_FRAMES: int = 34
var _burst: int = 0
var done: bool = false
var shots_fired: int = 0

var _queue: Array[Vector3] = []
var _frame: int = 0
var _wait: int = 30


func _ready() -> void:
	process_physics_priority = -20
	add_to_group(&"capture_busy")
	# Debug bullet paths, unless `--no-paths` (clean shots of tracers and rail trails).
	Ballistics.show_trajectories = not OS.get_cmdline_user_args().has("--no-paths")
	var r: ShootingRange = room.shooting_range
	room.player.global_position = Vector3(1.0, 0.0, 9.0)
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--weapon="):
			room.player.weapon().select_now(arg.trim_prefix("--weapon=").to_int())
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--ammo="):  # shell type for guns that take several (Saiga: 0 buck, 1 slug, 2 dragon's breath)
			room.player.weapon().select_ammo_now(arg.trim_prefix("--ammo=").to_int())
	if mode == "wheel":
		# Hold Y with the stick on slot `--wheel-pick=<n>` (the wheel stays open for the capture).
		var pick: int = 3
		for arg: String in OS.get_cmdline_user_args():
			if arg.begins_with("--wheel-pick="):
				pick = arg.trim_prefix("--wheel-pick=").to_int()
		var n: int = room.player.weapon().slots.size()
		var ang: float = pick * TAU / n
		room.player.weapon().script_wheel(true, Vector2(sin(ang), -cos(ang)))
		return
	if mode == "hip" or mode == "ads":
		return
	if mode == "burst":
		_wait = 20
		return
	if mode == "fire":
		for i: int in 4:
			_queue.append(r.dummies[0].parts[&"chest"].global_position)
		return
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
	var aimed: bool = mode == "range" or mode == "ads"
	if mode == "burst" and not done and _wait <= 0:
		aim_at(player, room.shooting_range.dummies[0].parts[&"chest"].global_position + Vector3(0.0, 0.1 * sin(_burst * 0.4), 0.0))
		weapon.script_input(true, false)
		_burst += 1
		shots_fired = _burst
		if _burst >= BURST_FRAMES:
			_freeze.call_deferred()
		return
	if done:
		weapon.script_input(false, aimed)
		return
	if _wait > 0:
		_wait -= 1
		weapon.script_input(false, aimed)
		return
	if _queue.is_empty():
		done = true
		# Hold the sights on the poppers for the capture (`--aim=dummy`: on a dummy's chest).
		if OS.get_cmdline_user_args().has("--aim=dummy"):
			aim_at(player, room.shooting_range.dummies[0].parts[&"chest"].global_position)
		else:
			aim_at(player, Vector3(-4.0, 1.4, -6.5) if aimed else Vector3(-2.0, 1.5, -6.5))
		weapon.cam_recoil.reset()
		remove_from_group(&"capture_busy")
		finished.emit()
		return
	var target: Vector3 = _queue.pop_front()
	aim_at(player, target)
	weapon.cam_recoil.reset()
	weapon.bloom = 0.0
	weapon.script_input(true, aimed)
	shots_fired += 1
	_wait = SETTLE_FRAMES
	if mode == "fire" and _queue.is_empty():
		_freeze.call_deferred()


func _freeze() -> void:
	# Let the shot frame play out a little, then nearly stop time (software
	# rendering is slow enough that 1 % speed still ages railgun trails out
	# during the capture warm-up).
	await get_tree().physics_frame
	await get_tree().physics_frame
	Engine.time_scale = 0.0005
	done = true
	remove_from_group(&"capture_busy")


static func aim_at(player: Player, target: Vector3) -> void:
	var eye: Vector3 = player.camera().global_position
	var d: Vector3 = target - eye
	player.set_view(atan2(-d.x, -d.z), asin(clampf(d.y / d.length(), -1.0, 1.0)))
