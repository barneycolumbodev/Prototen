class_name Spas12Demo
extends Node
## Cloud screenshots of the SPAS-12 (`-- --demo=spas12:<shot>`, tools/screenshot.sh
## with `--capture-only=Camera3D`). Freezes the game for the shot:
##   hip      at the hip, eight in the tube and one chambered
##   fire     the frame after the shot: flash, smoke, the kick
##   raise    the gun up and the pump racked all the way back, the hull flying
##   rack     the pump slammed home, the gun on its way back down
##   aim      shouldered (the folded stock over the top; the ring stays, smaller)
##   reload   a shell going into the loading port
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
		w.select_now(w.index_of("SPAS-12"))
	if _frames < 40:
		return
	match shot:
		"hip":
			if _frames > 50:
				_freeze()
		"fire":
			if _frames == 40:
				w.script_input(true, false)
			if _frames == 42:
				_freeze()
		"raise":
			if _frames == 40:
				w.script_input(true, false)
			if w.pump_t >= 0.43:
				_freeze()
		"rack":
			if _frames == 40:
				w.script_input(true, false)
			if w.pump_t >= 0.66:
				_freeze()
		"aim":
			w.script_input(false, true)
			if _frames > 90:
				_freeze()
		"reload":
			if _frames == 40:
				w.mechanism.magazine = 3
				w.script_input(false, false, true)
			if _frames > 40 and w.mechanism.round_progress() > 0.45:
				_freeze()


func _freeze() -> void:
	_done = true
	get_tree().paused = true
	remove_from_group(&"capture_busy")
