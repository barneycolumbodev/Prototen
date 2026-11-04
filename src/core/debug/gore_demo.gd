class_name GoreDemo
extends Node
## Scripted shots at the range's triad targets for cloud screenshots of the
## gore system (`-- --demo=gore`, tools/screenshot.sh). Each step switches to
## a gun, aims at a zone of a target and fires; the capture waits until the
## bodies have fallen and bled.
## `--gore-steps=<name>` picks a sequence (default "mixed").

signal finished

## [weapon slot, ammo index (-1 = keep), target index, zone, rounds]
const SEQUENCES: Dictionary[String, Array] = {
	"mixed": [
		[3, -1, 0, &"head", 1],            # rail carbine: the head comes apart
		[4, -1, 3, &"chest", 2],           # M14/P: through and through, spray on the wall behind
		[3, -1, 1, &"l_forearm", 1],       # rail carbine: forearm off
		[2, 0, 2, &"stomach", 1],          # Saiga buck: gut shot, doubled over
		[1, -1, 3, &"r_shin", 6],          # MG42: chews a shin off the body
	],
	"wounds": [
		[0, -1, 0, &"chest", 2],
		[0, -1, 0, &"stomach", 1],
		[0, -1, 0, &"l_upper_arm", 1],
	],
	"surrender": [
		[0, -1, 0, &"r_hand", 1],
	],
}
const AIM_FRAMES: int = 6
const SETTLE_FRAMES: int = 22
const END_FRAMES: int = 150

var room: TestRoom
var _steps: Array = []
var _step: int = 0
var _left: int = 0
var _wait: int = 30
var _ending: int = -1


func _ready() -> void:
	process_physics_priority = -20
	add_to_group(&"capture_busy")
	var seq: String = "mixed"
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--gore-steps="):
			seq = arg.trim_prefix("--gore-steps=")
	_steps = SEQUENCES.get(seq, SEQUENCES["mixed"])
	room.player.global_position = Vector3(0.5, 0.0, 5.0)
	room.player.invulnerable = true


func _physics_process(_delta: float) -> void:
	var weapon: PlayerWeapon = room.player.weapon()
	if _ending >= 0:
		weapon.script_input(false, false)
		_ending += 1
		if _ending == END_FRAMES:
			remove_from_group(&"capture_busy")
			finished.emit()
		return
	if _wait > 0:
		_wait -= 1
		weapon.script_input(false, true)
		return
	if _step >= _steps.size():
		_ending = 0
		return
	var s: Array = _steps[_step]
	var slot: int = s[0]
	var ammo: int = s[1]
	var target: int = s[2]
	var zone: StringName = s[3]
	if _left == 0:
		_left = s[4]
		weapon.select_now(slot)
		if ammo >= 0:
			weapon.select_ammo_now(ammo)
		_wait = AIM_FRAMES
		return
	var at: Vector3 = room.shooting_range.target_point(target, zone)
	GunplayDemo.aim_at(room.player, at)
	weapon.cam_recoil.reset()
	weapon.bloom = 0.0
	weapon.script_input(true, true)
	_left -= 1
	_wait = 4 if slot == 1 else SETTLE_FRAMES
	if _left == 0:
		_step += 1
		_wait = SETTLE_FRAMES
