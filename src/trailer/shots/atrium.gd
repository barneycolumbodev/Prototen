extends TrailerShot
## scene: res://src/levels/hotel/hotel.tscn
## frames: 265
## The Golden Dragon Grand Hotel: a slow dolly through the arch from the
## entrance hall into the atrium, tilting up to the chandelier. Triad men on
## guard at the fortifications.


func setup() -> void:
	length = 300
	player.global_position = bv(0.0, -15.0)
	spawn("gunman", bv(-6.5, 1.2), bv(0.0, -12.0), 3)
	spawn("gunman", bv(5.8, 0.6), bv(0.0, -12.0), 9)
	spawn("enforcer", bv(-1.5, 4.5), bv(0.0, -12.0), 6)
	spawn("gunman", bv(9.0, 8.0), bv(0.0, -12.0), 12)
	make_cam(44.0)
	map.atmos.follow(cam)
	step()


func step() -> void:
	var u: float = ease_io(f / 300.0)
	var from: Vector3 = bv(-1.9, -12.8, 1.3).lerp(bv(-1.9, -5.2, 2.2), u)
	var look: Vector3 = bv(-0.8, 6.0, 2.0).lerp(bv(0.0, 7.0, 8.0), u)
	cam.look_at_from_position(from + handheld(f / 60.0, 0.012), look)
