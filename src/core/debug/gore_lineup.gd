class_name GoreLineup
extends Node
## Cloud screenshots of dismemberment and blood (`-- --demo=gore-lineup`,
## tools/screenshot.sh with --capture-only=CapLineup). Clears the range and
## stands six triad members in a row in front of a wall and a close camera,
## then shoots each with real rounds from 5 m, each somewhere else and with
## a different gun (docs/design.md §5.5):
## an M14 round through the upper arm (the arm comes off), two MG42 rounds
## through the thigh (the leg above the knee), three pistol rounds into the
## hand (the hand), a shell of buckshot at the head from 3 m, an M14 round
## into the head (the head breaks apart), and a Gauss slug into the chest
## (the body bursts). The capture waits until the pieces have landed, or
## with --lineup-at=<frames> freezes the world that soon after the shots.
## Cameras: CapLineup (all six), CapLineupL, CapLineupR (close), CapLineupWall
## (the wall behind them and the floor in front of it), CapLineupFloor (the
## floor round the two headless men, from above).

const SPOTS: Array[Vector3] = [Vector3(-5.0, 0, -2.0), Vector3(-3.4, 0, -2.0), Vector3(-1.8, 0, -2.0), Vector3(-0.2, 0, -2.0),
		Vector3(1.4, 0, -2.0), Vector3(3.0, 0, -2.0)]
## [segment the round goes through (aimed just past its cut; &"skull": the
## middle of the head), weapon, rounds, metres away]
const SHOTS: Array = [
	[&"upper_arm_L", "res://data/weapons/m14p.tres", 1, 5.0],
	[&"thigh_R", "res://data/weapons/mg42.tres", 2, 5.0],
	[&"hand_L", "res://data/weapons/pistol_57.tres", 3, 5.0],
	[&"skull", "res://data/weapons/saiga12k.tres", 1, 3.0],
	[&"skull", "res://data/weapons/m14p.tres", 1, 5.0],
	[&"", "res://data/weapons/gx4_slug.tres", 1, 5.0],
]
const SETTLE_FRAMES: int = 150
const WALL_Z: float = -3.5

var room: TestRoom
var men: Array[Enemy] = []
var _frame: int = 0
var _capture_at: int = SETTLE_FRAMES
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	add_to_group(&"capture_busy")
	Settings.gore_level = Gore.Level.MAXIMUM
	room.player.invulnerable = true
	room.player.global_position = Vector3(0, 0, 6)
	room.shooting_range.clear_targets()
	_build_wall()
	for spec: Array in [["CapLineup", Vector3(-1.0, 1.9, 3.4), Vector3(-1.0, 0.7, -2.2), 64.0],
			["CapLineupL", Vector3(-3.6, 2.2, 0.4), Vector3(-3.6, 0.5, -2.6), 58.0],
			["CapLineupR", Vector3(1.6, 2.2, 0.6), Vector3(1.6, 0.5, -2.6), 62.0],
			["CapLineupWall", Vector3(0.4, 1.3, -0.4), Vector3(0.6, 0.8, -3.5), 62.0],
			["CapLineupFloor", Vector3(0.6, 2.7, -0.6), Vector3(0.6, 0.0, -1.9), 60.0]]:
		var cam: Camera3D = Camera3D.new()
		cam.name = spec[0]
		room.add_child(cam)
		var eye: Vector3 = spec[1]
		var look: Vector3 = spec[2]
		cam.look_at_from_position(eye, look)
		cam.fov = spec[3]
		cam.add_to_group(&"capture_cameras")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--lineup-at="):
			# Capture this many frames after the shots, the world frozen (the burst in the air).
			_capture_at = arg.trim_prefix("--lineup-at=").to_int()
	for i: int in SPOTS.size():
		var e: Enemy = Enemy.new()
		var roles: Array[String] = ["gunman", "red_pole", "gunman", "enforcer", "gunman", "gunman"]
		e.config = load("res://data/enemies/%s.tres" % roles[i]) as EnemyConfig
		e.passive = true
		e.name = "Lineup%d" % i
		room.add_child(e)
		e.position = SPOTS[i]
		e.face(0.0)
		men.append(e)


## A pale wall close behind the men, so what leaves them has somewhere to land.
func _build_wall() -> void:
	var wall: StaticBody3D = StaticBody3D.new()
	wall.name = "LineupWall"
	wall.collision_layer = Ballistics.LAYER_WORLD
	wall.collision_mask = 0
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(11.0, 3.0, 0.3)
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
	wall.position = Vector3(-1.0, 1.5, WALL_Z - 0.15)


func _physics_process(_delta: float) -> void:
	_frame += 1
	# Rounds a few frames apart, as a gun fires them (two rounds are two volleys).
	for i: int in men.size():
		var rounds: int = SHOTS[i][2]
		for r: int in rounds:
			if _frame == 20 + r * 6:
				_shoot(i)
	if _frame == 26 + _capture_at:
		if _capture_at < SETTLE_FRAMES:
			get_tree().paused = true  # physics and effects hold still for the shot
		for e: Enemy in men:
			print("gore-lineup: %s severed %s gibbed %s" % [e.name, e.body.severed.keys(), e.body.gibbed])
		print("gore-lineup: gibs %d, drops in the air %d, stains %d, trace rays %d" % [Gore.gib_count(), Gore.drop_count(),
				Gore.splat_count(), Gore.drops.rays_cast])
		remove_from_group(&"capture_busy")


func _shoot(i: int) -> void:
	var e: Enemy = men[i]
	var seg: StringName = SHOTS[i][0]
	var path: String = SHOTS[i][1]
	var dist: float = SHOTS[i][3]
	var w: WeaponData = load(path) as WeaponData
	var at: Vector3
	if seg == &"":
		at = e.body.chest_position()
	elif seg == &"skull":
		at = e.body.hitboxes[&"head"].global_position
	else:
		var sp: Array = EnemyBody.SEGMENTS[seg]
		var end_bone: StringName = sp[4]
		at = e.body.cut_point(seg).lerp(e.body.bone_position(end_bone), 0.12)
	# From in front and a little to the side, through the limb.
	var side: float = 0.0 if seg == &"skull" or seg == &"" else 0.12 * dist * signf(at.x - e.global_position.x + 0.001)
	var from: Vector3 = at + Vector3(side, 0.03 * dist, dist)
	var dir: Vector3 = (at - from).normalized()
	var volley: int = 0
	for n: int in maxi(w.pellets, 1):
		var d: Vector3 = dir if w.pellets <= 1 else Ballistics.pattern_dir(dir, w.pattern_deg, n, w.pellets, 0.0, _rng)
		var id: int = Ballistics.fire(w, from, d, room.player, Vector3.INF, volley)
		if volley == 0:
			volley = id
