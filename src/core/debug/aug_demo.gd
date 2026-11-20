class_name AugDemo
extends Node
## Cloud screenshots of the Steyr AUG (`-- --demo=aug:<shot>`, tools/screenshot.sh
## with `--capture-only=Camera3D`). Freezes the game for the shot:
##   hip      the AUG at the hip, a full magazine
##   burst    an automatic burst (12 rounds gone from the clear magazine), mid-fire
##   raise    halfway to the scope
##   scope    through the 1.5x scope (the HUD's circle reticle)
##   reload   the old magazine on its way out
##   handle   an empty reload, the cocking handle pulled back
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
		w.select_now(w.index_of("AUG A1"))
	if _frames < 40:
		return
	match shot:
		"hip":
			if _frames > 50:
				_freeze()
		"burst":
			if _frames == 40:
				w.script_hold(true)
			if w.mechanism.magazine <= 18 and w.motion.slide > 0.0:
				_freeze()
			elif w.mechanism.magazine <= 17:
				_freeze()
		"raise":
			w.script_input(false, true)
			if w.ads_visual() > 0.45:
				_freeze()
		"scope":
			w.script_input(false, true)
			if _frames > 90:
				_freeze()
		"reload":
			if _frames == 40:
				w.mechanism.magazine = 9
				w.script_input(false, false, true)
			if _frames > 40 and w.mechanism.reload_progress() > (w.data.mag_out_point + 0.08):
				_freeze()
		"handle":
			if _frames == 40:
				w.mechanism.magazine = 0
				w.script_input(true, false)
			if _frames == 50:
				w.script_input(false, false, true)
			if _frames > 50 and w.mechanism.reload_progress() > 0.86:
				_freeze()


func _freeze() -> void:
	_done = true
	get_tree().paused = true
	remove_from_group(&"capture_busy")
