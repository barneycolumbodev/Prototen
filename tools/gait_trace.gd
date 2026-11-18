extends SceneTree
## Prints a CSV trace of the ground speed and the gait (head, gun, footfalls)
## for a start, a walk and a stop, then a strafe right and a stop, from the real MovementConfig
## and Gait code. Used to plot before/after evidence (docs/previews/gait_trace.png).
## Usage: godot --headless -s res://tools/gait_trace.gd


func _init() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres") as MovementConfig
	var g: Gait = Gait.new(cfg)
	var dt: float = 1.0 / 60.0
	var h: Vector3 = Vector3.ZERO
	print("t,speed,head_y,head_pitch,head_roll,gun_z,footfall")
	for i: int in 270:
		var t: float = i * dt
		var wish: Vector3 = Vector3.ZERO
		if t >= 0.2 and t < 1.6:
			wish = Vector3(0, 0, -1)
		elif t >= 2.2 and t < 3.4:
			wish = Vector3(1, 0, 0)
		var top: float = cfg.walk_speed
		h = cfg.ground_step(h, wish, top, 1.0, dt, cfg.sprint_speed)
		g.update(dt, h, true, false)
		var off: Vector3 = g.head_offset()
		var rot: Vector3 = g.head_rotation_deg()
		print("%.4f,%.4f,%.5f,%.4f,%.4f,%.5f,%d" % [t, h.length(), off.y, rot.x, rot.z, g.gun_offset(1.0).z, g.footfalls.size()])
	quit()
