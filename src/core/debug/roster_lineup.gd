class_name RosterLineup
extends Node
## Cloud screenshots of the triad roster (`-- --demo=roster`, tools/screenshot.sh;
## docs/design.md §8.8): the six types added 2026-11-16 in a row beside a
## Gunman and a Hatchet Man, each in his own stance: the Dao swordsman behind
## his guard, the Shield man braced, the Firebomber with a bottle up, the
## Marksman and the Gunner aiming, the specialist at ease. A molotov's fire
## burns in front of the row and the Marksman's laser is on. Cameras:
## CapRoster (the row), CapRosterL / CapRosterR (close), CapRosterFar (22 m,
## as in a fight), CapRosterFaces (heads), CapRosterFace (one face, close).

const ROLES: Array[String] = ["gunman", "hatchet_man", "dao_swordsman", "shield_man", "firebomber", "marksman", "gunner",
		"anti_augment"]

var room: TestRoom
var men: Array[Enemy] = []
var _frame: int = 0
var _squad: Squad


func _ready() -> void:
	var p: Player = room.player
	p.invulnerable = true
	p.input_enabled = false
	p.global_position = Vector3(0.0, 0, 13.5)
	p.set_view(0.0, 0.0)
	room.shooting_range.clear_targets()
	_squad = Squad.new()
	room.add_child(_squad)
	_squad.set_player(p)
	for spec: Array in [["CapRoster", Vector3(0.0, 1.55, 11.6), Vector3(0.0, 1.05, 4.0), 66.0],
			["CapRosterL", Vector3(-3.0, 1.55, 7.6), Vector3(-3.0, 1.1, 4.0), 50.0],
			["CapRosterR", Vector3(3.0, 1.55, 7.6), Vector3(3.0, 1.1, 4.0), 50.0],
			["CapRosterFar", Vector3(0.5, 1.7, 22.0), Vector3(0.0, 1.0, 4.0), 26.0],
			["CapRosterFaces", Vector3(-1.5, 2.0, 6.6), Vector3(-1.5, 1.9, 4.0), 40.0],
			["CapRosterFace", Vector3(-3.0, 2.02, 5.05), Vector3(-3.0, 1.95, 4.0), 30.0]]:
		var cam: Camera3D = Camera3D.new()
		cam.name = spec[0]
		room.add_child(cam)
		cam.look_at_from_position(spec[1], spec[2])
		cam.fov = spec[3]
		cam.add_to_group(&"capture_cameras")
	for i: int in ROLES.size():
		var e: Enemy = Enemy.new()
		e.config = load("res://data/enemies/%s.tres" % ROLES[i]) as EnemyConfig
		e.passive = true
		e.look_seed = 7000 + i * 13
		e.name = "Roster%d" % i
		_squad.add(e)
		room.add_child(e)
		e.position = Vector3(-5.6 + i * 1.6, 0, 4.0)
		e.face(0.0)
		men.append(e)
	var cfg: ThrowerConfig = (load("res://data/enemies/firebomber.tres") as EnemyConfig).thrower
	FirePatch.spawn(room, Vector3(-1.0, 0.0, 7.2), Vector3.UP, cfg, null)


func _physics_process(_delta: float) -> void:
	_frame += 1
	for e: Enemy in men:
		match e.config.resource_path.get_file().get_basename():
			"dao_swordsman":
				e.body.guarding = true
				e.body.set_stance(&"loco")
			"shield_man", "hatchet_man", "firebomber":
				e.body.set_stance(&"loco")
			"anti_augment":
				e.body.set_stance(&"idle")
			_:
				e.body._set_stance(&"crouch_aim" if e.config.resource_path.ends_with("gunner.tres") else &"aim")
		if e.sight:
			e.sight.update(room.player, 0.05 if _frame < 20 else 0.0, true)
