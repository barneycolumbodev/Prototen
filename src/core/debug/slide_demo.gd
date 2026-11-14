class_name SlideDemo
extends Node
## Cloud screenshots of a slide launch (`-- --demo=slide`, run with Godot's
## `--fixed-fps 60`): the operative sprints at a triad gunman and slides into
## him; he goes up in the air (no damage) and the frames show what the
## player sees. Saves slide_f<frames>.png (frames after the slide starts)
## and slide_side_f<frames>.png from beside, then lets CaptureDirector finish.

const MAN_AT: Vector3 = Vector3(0.0, 0.0, -1.0)
const START: Vector3 = Vector3(0.0, 0.0, 9.0)
## Frames of sprinting before B.
const SLIDE_FRAME: int = 45
## Frames after B to save, from the player's eyes and from the side.
const FRAMES: Array[int] = [0, 12, 22, 32, 44, 60, 80]

var room: TestRoom
var _frame: int = 0
var _dir: String = ""
var _man: Enemy
var _side: Camera3D
var _peak: float = 0.0


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	room.player.invulnerable = true
	room.player.global_position = START
	room.player.set_view(0.0, -0.05)
	room.shooting_range.clear_targets()
	_man = Enemy.new()
	_man.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	_man.passive = true
	_man.look_seed = 77
	room.add_child(_man)
	_man.global_position = MAN_AT
	_man.face(0.0)
	_side = Camera3D.new()
	_side.fov = 50.0
	room.add_child(_side)
	_side.look_at_from_position(Vector3(5.5, 1.4, 0.5), Vector3(0.0, 1.0, -0.5))


func _process(_delta: float) -> void:
	_frame += 1
	if _frame == 2:
		Input.action_press(&"move_forward", 1.0)
		Input.action_press(&"sprint")
	elif _frame == 4:
		Input.action_release(&"sprint")
	elif _frame == SLIDE_FRAME:
		Input.action_press(&"slide")
	elif _frame == SLIDE_FRAME + 2:
		Input.action_release(&"slide")
	_peak = maxf(_peak, _man.global_position.y)
	var after: int = _frame - SLIDE_FRAME
	if after in FRAMES:
		_shoot.call_deferred(after)
	if after > FRAMES[FRAMES.size() - 1] + 2:
		Input.action_release(&"move_forward")
		print("slide demo: peak %.2f m, health %.0f, alive %s" % [_peak, _man.health, _man.alive])
		set_process(false)
		remove_from_group(&"capture_busy")


func _shoot(after: int) -> void:
	if _dir.is_empty():
		return
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("slide_f%02d.png" % after))
	_side.make_current()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("slide_side_f%02d.png" % after))
	room.player.camera().make_current()
