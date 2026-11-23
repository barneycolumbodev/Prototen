class_name Magnum44Demo
extends Node
## Cloud screenshots of the .44 Magnum (`-- --demo=magnum44:<shot>`, tools/screenshot.sh
## with `--capture-only=Camera3D`). Freezes the game for the shot:
##   hip      at the hip, six in the cylinder
##   fire     the frame after the shot: flash, the cloud out of the muzzle, the gap jets
##   leap     the gun at the top of its leap out of the grip
##   smoke    a second after three shots: the barrel still smoking
##   aim      on the sights
##   eject    cylinder swung out, muzzle up, the cases thrown
##   load     the speedloader going in
## The capture waits (group capture_busy) until it has frozen.

var room: TestRoom
var shot: String = "hip"
var _frames: int = 0
var _done: bool = false


func _ready() -> void:
	add_to_group(&"capture_busy")
	process_mode = Node.PROCESS_MODE_ALWAYS
	var p: Player = room.player
	p.invulnerable = true
	p.global_position = Vector3(0.5, 0.0, 6.0)
	p.set_view(0.0, deg_to_rad(-3.0))


func _physics_process(_delta: float) -> void:
	if _done:
		return
	_frames += 1
	var w: PlayerWeapon = room.player.weapon()
	if _frames == 10:
		w.select_now(w.index_of("Model 629"))
	if _frames < 40:
		return
	match shot:
		"hip":
			if _frames > 50:
				_freeze()
		"fire":
			if _frames == 40:
				w.script_input(true, false)
			if _frames == 43:
				_freeze()
		"leap":
			if _frames == 40:
				w.script_input(true, false)
			if _frames > 40 and w.motion.flip_amount() > 0.97:
				_freeze()
		"smoke":
			if _frames in [40, 62, 84]:
				w.script_input(true, false)
			if _frames == 84 + 70:
				_freeze()
		"aim":
			w.script_input(false, true)
			if _frames > 90:
				_freeze()
		"eject":
			if _frames == 40:
				w.script_input(true, false)
			if _frames == 62:
				w.script_input(false, false, true)
			if _frames > 62 and w.mechanism.reload_progress() > w.data.mag_out_point + 0.04:
				_freeze()
		"load":
			if _frames == 40:
				w.script_input(true, false)
			if _frames == 62:
				w.script_input(false, false, true)
			if _frames > 62 and w.mechanism.reload_progress() > w.data.mag_in_point - 0.06:
				_freeze()


func _freeze() -> void:
	_done = true
	get_tree().paused = true
	remove_from_group(&"capture_busy")
