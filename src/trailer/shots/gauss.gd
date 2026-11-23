extends TrailerShot
## scene: res://src/levels/chinatown/chinatown.tscn
## frames: 300
## The fish market: RX-9 slows the world, the GX-4 arm unfolds, and one
## round goes through four men in a line. `--cam=side` replays the same
## simulation from a slow dolly beside the line (bullet time).

var line: Array[Enemy] = []
var _fired: int = -1
var _side: bool = false
const START: Vector3 = Vector3(-6.0, 0.0, 6.0)


func setup() -> void:
	length = 700
	_side = "--cam=side" in OS.get_cmdline_user_args()
	loadout(["rx9_reflex_overclock", "gx4_gauss_arm"])
	var start: Vector3 = bv(-13.0, -7.45)
	var looks: Array[int] = [4, 7, 2]
	for i: int in 3:
		var p: Vector3 = bv(-8.6 + i * 2.3, -7.45 + (0.06 if i % 2 == 0 else -0.06))
		line.append(spawn("gunman", p, start, looks[i]))
	place_player(start, line[0].body.chest_position())
	for e: Enemy in line:
		alert(e)
	if _side:
		make_cam(30.0)
		# The replay is a camera beside the line, not the operative's eyes:
		# RX-9's first-person grade (colour drained, the cyan vignette) stays
		# off it, so the blood reads red, not black. Set just before each draw.
		RenderingServer.frame_pre_draw.connect(_replay_grade)


func _replay_grade() -> void:
	var rx: TimeDilation = part("rx9_reflex_overclock") as TimeDilation
	if rx == null:
		return
	if rx._env:
		rx._env.adjustment_saturation = rx._base_saturation
	if rx._layer:
		rx._layer.visible = false


func step() -> void:
	var arm: GaussArm = part("gx4_gauss_arm") as GaussArm
	if _fired < 0 and f > 8:
		for i: int in 1:
			if (f + i * 4) % 15 == 0:
				enemy_fire(line[i], player.camera().global_position + Vector3(0.0, -0.3, 0.5), 3.0)
	aim(line[0].body.chest_position() + Vector3(0.0, 0.08, 0.0), 8.0)
	if f == 14:
		use_part("rx9_reflex_overclock")
	if f == 40:
		use_part("gx4_gauss_arm")
	if _fired < 0 and f > 40 and arm.state == ActivePart.State.ACTIVE and f > 90:
		arm.script_fire()
		_fired = f
		print("trailer: gauss fired at ", f)
	if _fired > 0 and f == _fired + 60:
		var dead: int = 0
		for e: Enemy in line:
			dead += 0 if e.alive else 1
		print("trailer: %d of 3 dead" % dead)
	if _side and cam:
		# Beside the line, dollying along it with the round.
		var u: float = clampf(float(f - 60) / 300.0, 0.0, 1.0)
		var from: Vector3 = bv(0.2, -6.75, 1.4).lerp(bv(-0.8, -6.85, 1.25), ease_io(u))
		var look: Vector3 = bv(-6.2, -7.45, 1.25).lerp(bv(-5.6, -7.45, 1.0), ease_io(u))
		cam.look_at_from_position(from + handheld(f / 60.0, 0.03), look)
	if _fired > 0 and f > _fired + 300:
		finish()
