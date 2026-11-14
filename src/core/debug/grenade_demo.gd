class_name GrenadeDemo
extends Node
## Cloud screenshots of the M32A1 (`-- --demo=grenade`, run with Godot's
## `--fixed-fps 60` so every frame is the same slice of time; docs/design.md
## §4.8). Two triad men stand behind a low concrete wall 12 m out. The
## operative aims at the top of the wall (grenade_ads.png: the sight and the
## fire control's readout), fires an airburst over it, and the burst is saved
## side-on frame by frame (grenade_f<frames after>.png) and once from the
## operative's eyes (grenade_player.png). Then he reloads (grenade_reload.png:
## the cylinder swung out, rounds going in) and drops the sights onto the floor
## (grenade_hip.png: the landing marker). Then CaptureDirector finishes.

const WALL_AT: Vector3 = Vector3(0.0, 0.0, -1.6)
const WALL_SIZE: Vector3 = Vector3(4.2, 1.15, 0.3)
const MEN: Array[Vector3] = [Vector3(-0.7, 0.0, -3.1), Vector3(0.8, 0.0, -3.5)]
const AFTER: Array[int] = [4, 6, 9, 13, 18, 26, 40, 70, 120]
const PLAYER_AT: int = 2

var room: TestRoom
var _dir: String = ""
var _frame: int = 0
var _burst_frame: int = -1
var _side: Camera3D
var _weapon: PlayerWeapon
var _step: String = "aim"
var _step_frame: int = 0


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	room.player.invulnerable = true
	room.player.global_position = Vector3(0.0, 0.0, 9.0)
	room.shooting_range.clear_targets()
	_build_wall()
	for i: int in MEN.size():
		var e: Enemy = Enemy.new()
		e.config = load("res://data/enemies/%s.tres" % ["gunman", "enforcer"][i]) as EnemyConfig
		e.passive = true
		e.name = "Behind%d" % i
		room.add_child(e)
		e.position = MEN[i]
		e.face(0.0)
	_side = Camera3D.new()
	_side.name = "GrenadeSide"
	room.add_child(_side)
	_side.look_at_from_position(Vector3(6.2, 2.1, 1.4), Vector3(0.0, 1.0, -2.6))
	_side.fov = 52.0
	_weapon = room.player.weapon()
	Grenades.detonated.connect(func(_at: Vector3, _kills: int) -> void: _burst_frame = _frame)


func _build_wall() -> void:
	var wall: StaticBody3D = StaticBody3D.new()
	wall.name = "DemoWall"
	wall.collision_layer = Ballistics.LAYER_WORLD
	wall.collision_mask = 0
	wall.set_meta(SurfaceLibrary.META, &"concrete")
	var box: BoxShape3D = BoxShape3D.new()
	box.size = WALL_SIZE
	var cs: CollisionShape3D = CollisionShape3D.new()
	cs.shape = box
	wall.add_child(cs)
	var mesh: BoxMesh = BoxMesh.new()
	mesh.size = WALL_SIZE
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = Color(0.55, 0.54, 0.51)
	mat.roughness = 0.92
	mesh.material = mat
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.mesh = mesh
	wall.add_child(mi)
	room.add_child(wall)
	wall.position = WALL_AT + Vector3(0.0, WALL_SIZE.y * 0.5, 0.0)


func _physics_process(_delta: float) -> void:
	_frame += 1
	_step_frame += 1
	match _step:
		"aim":
			if _frame == 12:
				_weapon.select_now(_weapon.index_of("M32A1 MGL"))
			if _frame >= 12:
				_look_at(WALL_AT + Vector3(0.0, WALL_SIZE.y - 0.08, WALL_SIZE.z * 0.5 + 0.01))
				_weapon.script_input(false, true)
			if _frame == 80:
				_save("grenade_ads.png")
			if _frame == 82:
				_weapon.script_input(true, true)
				_step = "burst"
				_step_frame = 0
		"burst":
			if _burst_frame < 0:
				_weapon.script_input(false, true)
				return
			var after: int = _frame - _burst_frame
			if after == PLAYER_AT:
				_save("grenade_player.png")
			if after == PLAYER_AT + 1:
				_side.make_current()
				_hud(false)
			if after > PLAYER_AT + 1 and after in AFTER:
				_save("grenade_f%03d.png" % after)
			if after > AFTER[AFTER.size() - 1]:
				room.player.camera().make_current()
				_hud(true)
				_weapon.end_script_input()
				_weapon.script_input(false, false, true)
				_step = "reload"
				_step_frame = 0
		"reload":
			if _step_frame == 52:
				_save("grenade_reload.png")
			if _step_frame == 300:
				room.player.set_view(room.player.yaw, deg_to_rad(-4.5))
			if _step_frame == 330:
				_save("grenade_hip.png")
				_step = "done"
				remove_from_group(&"capture_busy")


func _look_at(point: Vector3) -> void:
	var d: Vector3 = (point - room.player.camera().global_position).normalized()
	room.player.set_view(atan2(-d.x, -d.z), asin(d.y))


func _hud(shown: bool) -> void:
	for n: Node in room.get_children():
		var layer: CanvasLayer = n as CanvasLayer
		if layer:
			layer.visible = shown


func _save(file_name: String) -> void:
	if _dir.is_empty():
		return
	var image: Image = get_viewport().get_texture().get_image()
	image.save_png(_dir.path_join(file_name))
	print("capture: saved ", file_name)
