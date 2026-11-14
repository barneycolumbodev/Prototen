extends Node3D
## Lookdev for the main menu's smoking operative (MenuSmoker): the figure
## against a plain wall under studio light, with cameras front, side, three
## quarter and on the face. `-- --pose-t=<s>` holds the cycle at that time
## (0.9-2.2: the drag; 3.5: breathing out; 6: idle).

const CONFIG: MenuSceneConfig = preload("res://data/levels/main_menu.tres")


func _ready() -> void:
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.06, 0.07, 0.08)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.4, 0.42, 0.45)
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	var we: WorldEnvironment = WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun: DirectionalLight3D = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-35, 30, 0)
	add_child(sun)
	var wall: MeshInstance3D = MeshInstance3D.new()
	var bm: BoxMesh = BoxMesh.new()
	bm.size = Vector3(3, 2.6, 0.1)
	wall.mesh = bm
	wall.position = Vector3(0, 1.3, MenuSmoker.WALL_Z - 0.05)
	var wm: StandardMaterial3D = StandardMaterial3D.new()
	wm.albedo_color = Color(0.45, 0.2, 0.15)
	wall.material_override = wm
	add_child(wall)
	var fl: MeshInstance3D = MeshInstance3D.new()
	var pm: PlaneMesh = PlaneMesh.new()
	pm.size = Vector2(3, 3)
	fl.mesh = pm
	add_child(fl)
	var s: MenuSmoker = MenuSmoker.new()
	s.config = CONFIG
	add_child(s)
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--pose-t="):
			s.hold_t = a.get_slice("=", 1).to_float()
	var cams: Dictionary[String, Array] = {
		"Front": [Vector3(0, 1.0, 3.2), Vector3(0, 0.95, 0)],
		"Side": [Vector3(3.2, 1.0, -0.1), Vector3(0, 0.95, -0.1)],
		"ThreeQuarter": [Vector3(1.8, 1.3, 2.2), Vector3(0, 1.0, 0)],
		"Face": [Vector3(0.35, 1.62, 0.9), Vector3(-0.05, 1.55, 0.05)],
	}
	for nm: String in cams:
		var c: Camera3D = Camera3D.new()
		c.name = nm
		c.fov = 40.0
		add_child(c)
		var v: Array = cams[nm]
		var p: Vector3 = v[0]
		var t: Vector3 = v[1]
		c.look_at_from_position(p, t)
		c.add_to_group(&"capture_cameras")
