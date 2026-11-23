extends TrailerShot
## scene: res://src/levels/chinatown/chinatown.tscn
## frames: 225
## Opening: the Chinatown docks street at night in the rain, a slow crane
## down toward the gate under the neon. Triad men stand in the street and
## turn to look up at the lens.


func setup() -> void:
	length = 330
	player.global_position = bv(19.0, 8.4)
	spawn("gunman", bv(3.5, 9.6), bv(19.0, 8.4), 3)
	spawn("gunman", bv(2.6, 7.6), bv(19.0, 8.4), 8)
	spawn("enforcer", bv(-3.5, 10.6), bv(19.0, 8.4), 5)
	spawn("gunman", bv(-8.5, 7.4), bv(19.0, 8.4), 11)
	spawn("gunman", bv(-14.0, 9.8), bv(19.0, 8.4), 2)
	make_cam(42.0)
	map.atmos.follow(cam)
	step()


func step() -> void:
	var u: float = ease_io(f / 300.0)
	var from: Vector3 = bv(17.5, 8.2, 8.5).lerp(bv(11.5, 8.5, 2.1), u)
	var look: Vector3 = bv(-14.0, 9.0, 1.0).lerp(bv(-22.0, 8.8, 3.0), u)
	cam.look_at_from_position(from + handheld(f / 60.0, 0.015), look)
