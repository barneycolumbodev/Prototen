class_name ImpactDemo
extends Node
## Cloud screenshots of one round going through a man in RX-9 slow motion
## (`-- --demo=impact`, run with Godot's `--fixed-fps 60` so every frame is
## the same slice of time). One triad member stands 1.3 m in front of a pale
## wall; a round is fired through his chest from 6 m with the world at the
## RX-9's world scale. Saves a frame sequence (impact_f<frames>.png: frames
## after the shot, the camera side-on) and a last shot of the wall, then
## lets CaptureDirector finish.
## `--impact-gun=<weapon .tres name>` picks the gun (default pistol_57),
## `--impact-zone=<zone>` where it goes in (default chest),
## `--impact-normal` runs at normal speed instead, `--impact-cam=shooter`
## watches from beside the gun (what the player sees).

const MAN_AT: Vector3 = Vector3(0.0, 0.0, -2.0)
const WALL_Z: float = -3.3
const SHOT_FRAME: int = 40
## Frames after the shot to save (-1: just before it).
const FRAMES: Array[int] = [-1, 1, 2, 3, 5, 8, 12, 18, 26, 40, 60, 90, 140]

var room: TestRoom
var _frame: int = 0
var _dir: String = ""
var _gun: String = "pistol_57"
var _zone: StringName = &"chest"
var _slow: bool = true
## Watch from just beside the gun (what the player sees) instead of side-on.
var _from_shooter: bool = false
var _man: Enemy
var _side: Camera3D
var _wall_cam: Camera3D


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
		elif arg.begins_with("--impact-gun="):
			_gun = arg.trim_prefix("--impact-gun=")
		elif arg.begins_with("--impact-zone="):
			_zone = StringName(arg.trim_prefix("--impact-zone="))
		elif arg == "--impact-normal":
			_slow = false
		elif arg == "--impact-cam=shooter":
			_from_shooter = true
	room.player.invulnerable = true
	room.player.global_position = Vector3(0, 0, 8)
	room.shooting_range.clear_targets()
	_build_wall()
	_side = _camera("ImpactSide", Vector3(2.3, 1.5, -1.6), Vector3(-0.2, 1.2, -2.75), 48.0)
	_wall_cam = _camera("ImpactWall", Vector3(0.9, 1.35, 0.2), Vector3(-0.1, 1.0, -3.3), 55.0)
	_side.make_current()
	if _from_shooter:
		_camera("ImpactShooter", Vector3(-0.55, 1.62, 4.0), Vector3(0.0, 1.3, -2.0), 40.0).make_current()
	_man = Enemy.new()
	_man.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	_man.passive = true
	_man.name = "ImpactMan"
	room.add_child(_man)
	_man.position = MAN_AT
	_man.face(0.0)


func _camera(cam_name: String, eye: Vector3, look: Vector3, fov: float) -> Camera3D:
	var cam: Camera3D = Camera3D.new()
	cam.name = cam_name
	room.add_child(cam)
	cam.look_at_from_position(eye, look)
	cam.fov = fov
	return cam


func _build_wall() -> void:
	var wall: StaticBody3D = StaticBody3D.new()
	wall.name = "ImpactWall"
	wall.collision_layer = Ballistics.LAYER_WORLD
	wall.collision_mask = 0
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(6.0, 3.0, 0.3)
	var cs: CollisionShape3D = CollisionShape3D.new()
	cs.shape = box
	wall.add_child(cs)
	var mesh: BoxMesh = BoxMesh.new()
	mesh.size = box.size
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = Color(0.62, 0.61, 0.58)
	mat.roughness = 0.9
	mesh.material = mat
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.mesh = mesh
	wall.add_child(mi)
	room.add_child(wall)
	wall.position = Vector3(0.0, 1.5, WALL_Z - 0.15)


func _process(_delta: float) -> void:
	_frame += 1
	if _frame == SHOT_FRAME - 12 and _slow:
		TimeControl.set_dilation(0.24, 0.65)
	var after: int = _frame - SHOT_FRAME
	if after == -1 or (after > 0 and after in FRAMES):
		_save("impact_f%03d.png" % maxi(after, 0) if after > 0 else "impact_before.png")
	if _frame == SHOT_FRAME:
		_shoot()
	if after == FRAMES[FRAMES.size() - 1] + 1:
		_wall_cam.make_current()
	if after == FRAMES[FRAMES.size() - 1] + 4:
		_save("impact_wall.png")
		print("impact: drops in the air %d, stains %d, wounds %d" % [Gore.drop_count(), Gore.splat_count(),
				_man.body.wound_count()])
		TimeControl.set_dilation(1.0, 1.0)
		remove_from_group(&"capture_busy")
		set_process(false)


func _shoot() -> void:
	var w: WeaponData = load("res://data/weapons/%s.tres" % _gun) as WeaponData
	var at: Vector3 = _man.body.hitboxes[_zone].global_position
	at += Vector3(0.05, 0.03, 0.0)
	var from: Vector3 = at + Vector3(-0.4, 0.25, 6.0)
	var dir: Vector3 = (at - from).normalized()
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 7
	var volley: int = 0
	for n: int in maxi(w.pellets, 1):
		var d: Vector3 = dir if w.pellets <= 1 else Ballistics.pattern_dir(dir, w.pattern_deg, n, w.pellets, 0.0, rng)
		var id: int = Ballistics.fire(w, from, d, room.player, Vector3.INF, volley)
		if volley == 0:
			volley = id
	print("impact: fired %s at %s" % [_gun, _zone])


func _save(file_name: String) -> void:
	if _dir.is_empty():
		return
	var image: Image = get_viewport().get_texture().get_image()
	image.save_png(_dir.path_join(file_name))
	print("capture: saved ", file_name)
