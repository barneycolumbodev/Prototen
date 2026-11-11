class_name GoreLineup
extends Node
## Cloud screenshots of dismemberment (`-- --demo=gore-lineup`,
## tools/screenshot.sh with --capture-only=CapLineup). Clears the range and
## stands five triad members in a row in front of a close camera, then puts
## one real round into each, each somewhere else (docs/design.md §5.5):
## the upper arm (the arm comes off), the thigh (the leg above the knee), the
## wrist (the hand), the neck (the head), and a Gauss slug into the chest
## (the body bursts). The capture waits until the pieces have landed, or
## with --lineup-at=<frames> freezes the world that soon after the shots.
## Cameras: CapLineup (all five), CapLineupL, CapLineupR (close).

const SPOTS: Array[Vector3] = [Vector3(-5.0, 0, -2.0), Vector3(-3.4, 0, -2.0), Vector3(-1.8, 0, -2.0), Vector3(-0.2, 0, -2.0), Vector3(1.4, 0, -2.0)]
## [segment the round goes through (aimed just past its cut), weapon]
const SHOTS: Array = [
	[&"upper_arm_L", "res://data/weapons/rail_carbine.tres"],
	[&"thigh_R", "res://data/weapons/rail_carbine.tres"],
	[&"hand_L", "res://data/weapons/rail_carbine.tres"],
	[&"head", "res://data/weapons/rail_carbine.tres"],
	[&"", "res://data/weapons/gx4_slug.tres"],
]
const SETTLE_FRAMES: int = 150

var room: TestRoom
var men: Array[Enemy] = []
var _frame: int = 0
var _capture_at: int = SETTLE_FRAMES


func _ready() -> void:
	add_to_group(&"capture_busy")
	Settings.gore_level = Gore.Level.MAXIMUM
	room.player.invulnerable = true
	room.player.global_position = Vector3(0, 0, 6)
	room.shooting_range.clear_targets()
	for spec: Array in [["CapLineup", Vector3(-1.5, 1.9, 2.6), Vector3(-1.8, 0.6, -2.2), 62.0],
			["CapLineupL", Vector3(-4.0, 2.3, 0.2), Vector3(-4.0, 0.1, -2.4), 55.0],
			["CapLineupR", Vector3(0.6, 2.3, 0.6), Vector3(0.6, 0.4, -2.4), 62.0]]:
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
		var roles: Array[String] = ["gunman", "red_pole", "gunman", "enforcer", "gunman"]
		e.config = load("res://data/enemies/%s.tres" % roles[i]) as EnemyConfig
		e.passive = true
		e.name = "Lineup%d" % i
		room.add_child(e)
		e.position = SPOTS[i]
		e.face(0.0)
		men.append(e)


func _physics_process(_delta: float) -> void:
	_frame += 1
	if _frame == 20:
		for i: int in men.size():
			var e: Enemy = men[i]
			var seg: StringName = SHOTS[i][0]
			var path: String = SHOTS[i][1]
			var w: WeaponData = load(path) as WeaponData
			var at: Vector3
			if seg == &"":
				at = e.body.chest_position()
			elif seg == &"head":
				at = e.body.cut_point(seg) + Vector3.UP * 0.02
			else:
				var sp: Array = EnemyBody.SEGMENTS[seg]
				var end_bone: StringName = sp[4]
				at = e.body.cut_point(seg).lerp(e.body.bone_position(end_bone), 0.12)
			# From in front and a little to the side, through the limb.
			var from: Vector3 = at + Vector3(0.6 * signf(at.x - e.global_position.x + 0.001), 0.15, 5.0)
			Ballistics.fire(w, from, (at - from).normalized(), room.player)
	if _frame == 20 + _capture_at:
		if _capture_at < SETTLE_FRAMES:
			get_tree().paused = true  # physics and effects hold still for the shot
		for e: Enemy in men:
			print("gore-lineup: %s severed %s gibbed %s" % [e.name, e.body.severed.keys(), e.body.gibbed])
		print("gore-lineup: gibs in the air or down: %d" % Gore.gib_count())
		remove_from_group(&"capture_busy")
