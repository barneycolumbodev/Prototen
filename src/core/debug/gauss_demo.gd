class_name GaussDemo
extends Node
## Cloud screenshots of the GX-4 arm (`-- --demo=gauss`, tools/screenshot.sh
## with `--capture-only=Camera3D`). Raises the arm and freezes the game:
##   --gauss-stage=<0..1>  part-way through the transformation (default 1)
##   --gauss-fire=<frames> lines two range targets up, fires through both,
##                         and freezes this many frames after the shot
## The capture waits (group capture_busy) until it has frozen.

var room: TestRoom
var stage: float = 1.0
var fire_after: int = -1
var _arm: GaussArm
var _phase: int = 0
var _frames: int = 0
var _a: Enemy
var _b: Enemy
var _beam_test: bool = false


func _ready() -> void:
	add_to_group(&"capture_busy")
	process_mode = Node.PROCESS_MODE_ALWAYS
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--gauss-stage="):
			stage = clampf(arg.trim_prefix("--gauss-stage=").to_float(), 0.0, 1.0)
		if arg.begins_with("--gauss-fire="):
			fire_after = arg.trim_prefix("--gauss-fire=").to_int()
		if arg == "--gauss-beamtest":
			_beam_test = true
	var p: Player = room.player
	p.invulnerable = true
	p.global_position = Vector3(0.5, 0.0, 6.0)
	p.set_view(0.0, deg_to_rad(-2.0))


func _physics_process(_delta: float) -> void:
	var p: Player = room.player
	_frames += 1
	if _beam_test and _phase == 0 and _frames == 20:
		Fx.gauss_beam(Vector3(-4.0, 1.4, -2.0), Vector3(5.0, 1.8, -6.0), Color(0.45, 0.72, 1.0))
		_phase = 8
		_frames = 0
	if _phase == 8:
		if _frames >= 3:
			_freeze()
		return
	match _phase:
		0:
			if _frames < 20:
				return
			_arm = p.augments.part(2) as GaussArm
			p.augments.select(2)
			if fire_after >= 0:
				# Two targets in a row down the lane, facing the player.
				_a = room.shooting_range.targets[0]
				_b = room.shooting_range.targets[2]
				_a.global_position = Vector3(0.7, 0.0, -1.0)
				_b.global_position = Vector3(1.1, 0.0, -5.5)
				_a.face(0.0)
				_b.face(0.0)
			p.augments.use_selected()
			_phase = 1
			_frames = 0
		1:
			if fire_after < 0:
				if _arm.blend >= stage - 0.001 and (_arm.state == ActivePart.State.ACTIVE or stage < 1.0):
					_freeze()
				return
			if _arm.state != ActivePart.State.ACTIVE:
				return
			GunplayDemo.aim_at(p, _a.body.chest_position() + Vector3(0.0, 0.05, 0.0))
			_phase = 2
			_frames = 0
		2:
			if _frames == 20:
				_arm.script_fire()
				_frames = 0
				_phase = 3
		3:
			if _frames >= fire_after:
				_freeze()


func _freeze() -> void:
	_phase = 9
	get_tree().paused = true
	remove_from_group(&"capture_busy")
