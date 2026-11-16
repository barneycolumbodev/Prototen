class_name HuntDemo
extends Node
## Cloud screenshots of the last-hostile marker on the docks (`-- --demo=hunt`;
## docs/design.md §5.6a): one man left in a wave, first behind the
## operative to his left (the arrow at the screen edge), then ahead of him
## behind a wall (the marker over him, through the wall). Saves
## hunt_marker_<moment>.png, then lets CaptureDirector finish.

var map: ChinatownMap
var _dir: String = ""
var _man: Enemy
var _frame: int = 0


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	map.player.input_enabled = false
	map.player.invulnerable = true


func _physics_process(_delta: float) -> void:
	_frame += 1
	var p: Player = map.player
	if _frame == 20:
		_man = Enemy.new()
		_man.config = load("res://data/enemies/gunman.tres") as EnemyConfig
		_man.look_seed = 7
		map.add_child(_man)
		# Held still for the shots (a passive man isn't marked).
		_man.set_physics_process(false)
		# One left in the wave: the HUD marks him.
		EventBus.wave_changed.emit(4, 1)
	if _man == null:
		return
	var cam: Camera3D = p.camera()
	var fwd: Vector3 = Vector3(-cam.global_basis.z.x, 0.0, -cam.global_basis.z.z).normalized()
	var right: Vector3 = Vector3(cam.global_basis.x.x, 0.0, cam.global_basis.x.z).normalized()
	if _frame == 22:
		_man.global_position = p.global_position - fwd * 14.0 - right * 6.0
	if _frame == 60:
		_shoot("behind")
	if _frame == 90:
		_man.global_position = _ahead_behind_wall(p, fwd)
	if _frame == 130:
		_shoot("ahead")
	if _frame == 170:
		set_physics_process(false)
		remove_from_group(&"capture_busy")


## A spot ahead of him with a wall between: the first thing a ray forward
## hits, a few metres past it.
func _ahead_behind_wall(p: Player, fwd: Vector3) -> Vector3:
	var space: PhysicsDirectSpaceState3D = p.get_world_3d().direct_space_state
	var eye: Vector3 = p.camera().global_position
	for ang: float in [0.0, 0.25, -0.25, 0.5, -0.5]:
		var d: Vector3 = fwd.rotated(Vector3.UP, ang)
		var hit: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, eye + d * 30.0, Ballistics.LAYER_WORLD))
		if not hit.is_empty():
			var at: Vector3 = hit["position"] + d * 2.5
			return Vector3(at.x, p.global_position.y, at.z)
	return p.global_position + fwd * 18.0


func _shoot(moment: String) -> void:
	if _dir.is_empty():
		return
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("hunt_marker_%s.png" % moment))
	print("capture hunt_marker_%s" % moment)
