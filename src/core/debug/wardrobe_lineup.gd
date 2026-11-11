class_name WardrobeLineup
extends Node
## Cloud screenshots of the triad wardrobe (`-- --demo=wardrobe`,
## tools/screenshot.sh): clears the range and stands a row of triad men,
## each dressed from his role's outfits with his own seed (garments,
## colours, prints, tattoos, facial hair), some aiming, some at ease.
## `--wardrobe-seed=<n>` changes the whole row. Cameras: CapWardrobe (the
## row), CapWardrobeL / CapWardrobeR (three men close), CapWardrobeBack
## (the row from behind), CapWardrobeFar (the row from 22 m, as in a fight).

const ROLES: Array[String] = ["gunman", "gunman", "red_pole", "enforcer", "gunman", "gunman", "red_pole", "gunman"]
const STANCES: Array[StringName] = [&"idle", &"loco", &"idle", &"loco", &"idle", &"idle", &"loco", &"idle"]

var room: TestRoom
var men: Array[Enemy] = []
var seed_base: int = 11


func _ready() -> void:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--wardrobe-seed="):
			seed_base = arg.trim_prefix("--wardrobe-seed=").to_int()
	room.player.invulnerable = true
	room.player.global_position = Vector3(13, 0, 13)
	room.shooting_range.clear_targets()
	for spec: Array in [["CapWardrobe", Vector3(0.0, 1.5, 10.4), Vector3(0.0, 1.0, 4.0), 70.0],
			["CapWardrobeL", Vector3(-3.0, 1.55, 6.7), Vector3(-3.0, 1.05, 4.0), 52.0],
			["CapWardrobeR", Vector3(3.0, 1.55, 6.7), Vector3(3.0, 1.05, 4.0), 52.0],
			["CapWardrobeBack", Vector3(0.0, 1.6, -1.0), Vector3(0.0, 1.0, 4.0), 70.0],
			["CapWardrobeFar", Vector3(0.5, 1.7, 15.5), Vector3(0.0, 1.0, 4.0), 30.0],
			["CapWardrobeHeads", Vector3(-0.75, 1.95, 6.0), Vector3(-0.75, 1.88, 4.0), 32.0],
			["CapWardrobeFace", Vector3(-2.25, 1.9, 5.0), Vector3(-2.25, 1.75, 4.0), 30.0]]:
		var cam: Camera3D = Camera3D.new()
		cam.name = spec[0]
		room.add_child(cam)
		var eye: Vector3 = spec[1]
		var look: Vector3 = spec[2]
		cam.look_at_from_position(eye, look)
		cam.fov = spec[3]
		cam.add_to_group(&"capture_cameras")
	for i: int in ROLES.size():
		var cfg: EnemyConfig = load("res://data/enemies/%s.tres" % ROLES[i]) as EnemyConfig
		var e: Enemy = Enemy.new()
		e.config = cfg
		e.passive = true
		e.look_seed = seed_base * 100 + i
		e.name = "Wardrobe%d" % i
		room.add_child(e)
		e.position = Vector3(-5.25 + i * 1.5, 0, 4.0)
		e.face(0.0)
		e.body.set_stance(STANCES[i])
		men.append(e)
		for arg: String in OS.get_cmdline_user_args():
			if arg.begins_with("--wardrobe-debug="):
				e.body.material.set_shader_parameter(&"debug_view", arg.trim_prefix("--wardrobe-debug=").to_int())
