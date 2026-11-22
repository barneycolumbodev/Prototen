class_name DropkickDemo
extends Node
## Cloud screenshots of a midair dropkick + Max Payne / John Woo rebound shootout
## (`-- --demo=dropkick`, run with Godot's `--fixed-fps 60`): the operative runs,
## jumps, presses A again midair to launch a brutal double-boot dropkick into a
## Triad gunman, blasts him far into the air, pops RX-9 Reflex Overclock on
## rebound, and fires the canted Five-seveN while falling back.
## Saves dk_f<frames>.png (first person) and dk_side_f<frames>.png (side view).

const MAN_AT: Vector3 = Vector3(0.0, 0.0, 1.5)
const START: Vector3 = Vector3(0.0, 0.0, 8.2)
const JUMP_FRAME: int = 16
const KICK_FRAME: int = 24
## Frames after the midair A dropkick press to capture.
const FRAMES: Array[int] = [4, 10, 14, 22, 32, 46, 64]

var room: TestRoom
var _frame: int = 0
var _dir: String = ""
var _man: Enemy
var _side: Camera3D
var _peak: float = 0.0
var _impact_frame: int = -1
var _rx9_on: bool = false


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	room.player.invulnerable = true
	room.player.global_position = START
	room.player.set_view(0.0, -0.02)
	room.player.reset_camera_smoothing()
	room.shooting_range.clear_targets()
	_man = Enemy.new()
	_man.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	_man.passive = true
	_man.look_seed = 77
	room.add_child(_man)
	_man.global_position = MAN_AT
	_man.face(0.0)
	_side = Camera3D.new()
	_side.fov = 54.0
	room.add_child(_side)
	_side.look_at_from_position(Vector3(8.4, 2.0, 2.2), Vector3(0.0, 1.35, -0.3))
	EventBus.dropkick_impact.connect(_on_impact)


func _on_impact(_e: Node, _push: float) -> void:
	_impact_frame = _frame
	# Engage RX-9 Reflex Overclock right as we rebound back for slow-mo gunplay!
	if not _rx9_on and room.player.augments:
		var part: ActivePart = room.player.augments.selected_part()
		if part:
			_rx9_on = true
			part.toggle()


func _process(_delta: float) -> void:
	_frame += 1
	if _frame == 2:
		Input.action_press(&"move_forward", 1.0)
	elif _frame == JUMP_FRAME:
		Input.action_press(&"jump")
	elif _frame == JUMP_FRAME + 2:
		Input.action_release(&"jump")
	elif _frame == KICK_FRAME:
		Input.action_press(&"jump")
	elif _frame == KICK_FRAME + 2:
		Input.action_release(&"jump")
		Input.action_release(&"move_forward")

	# Track the flying enemy smoothly during rebound and fire midair Max Payne shots!
	if _impact_frame >= 0 and _man and is_instance_valid(_man):
		var cam_pos: Vector3 = room.player.camera().global_position
		var aim_at: Vector3 = _man.global_position + Vector3.UP * 1.15
		var to: Vector3 = aim_at - cam_pos
		if to.length() > 0.5:
			var flat: float = Vector2(to.x, to.z).length()
			var want_pitch: float = atan2(to.y, flat)
			room.player.set_view(0.0, lerpf(room.player.pitch, want_pitch, 0.35))
		var since: int = _frame - _impact_frame
		if since == 12 or since == 22 or since == 34:
			room.player.weapon().script_input(true, false)
		elif since == 14 or since == 24 or since == 36:
			room.player.weapon().script_input(false, false)

	if _man and is_instance_valid(_man):
		_peak = maxf(_peak, _man.global_position.y)
	var after: int = _frame - KICK_FRAME
	if after in FRAMES:
		_shoot.call_deferred(after)
	if after > FRAMES[FRAMES.size() - 1] + 4:
		Input.action_release(&"move_forward")
		Input.action_release(&"jump")
		room.player.weapon().end_script_input()
		if _rx9_on and room.player.augments:
			var part: ActivePart = room.player.augments.selected_part()
			if part:
				part.stop()
		var dist: float = MAN_AT.z - _man.global_position.z if _man and is_instance_valid(_man) else 0.0
		print("dropkick demo: impact=%d peak=%.2fm dist=%.2fm hp=%.0f alive=%s" % [
			_impact_frame, _peak, dist, _man.health if _man else 0.0, _man.alive if _man else false])
		set_process(false)
		remove_from_group(&"capture_busy")


func _shoot(after: int) -> void:
	if _dir.is_empty():
		return
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("dk_f%02d.png" % after))
	_side.make_current()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("dk_side_f%02d.png" % after))
	room.player.camera().make_current()
