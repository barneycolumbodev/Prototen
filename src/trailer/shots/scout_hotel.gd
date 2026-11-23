extends TrailerShot
## scene: res://src/levels/hotel/hotel.tscn
## frames: 200
## Location scouting: `--scout=x,y,z,tx,ty,tz,fov/...` (Blender coordinates),
## holds each view for 4 frames. Use the frames to plan shots.

var views: Array[PackedFloat64Array] = []


func setup() -> void:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--scout="):
			for v: String in a.trim_prefix("--scout=").split("/"):
				views.append(v.split_floats(","))
	length = views.size() * 4 + 2
	make_cam(50.0)


func step() -> void:
	var i: int = (f - 1) / 4
	if i < views.size():
		var v: PackedFloat64Array = views[i]
		cam.fov = v[6] if v.size() > 6 else 50.0
		cam.look_at_from_position(bv(v[0], v[1], v[2]), bv(v[3], v[4], v[5]))
