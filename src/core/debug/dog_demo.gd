class_name DogDemo
extends Node
## Cloud screenshots of the attack dogs on the docks (`-- --demo=dogs`, run
## with Godot's `--fixed-fps 60`; docs/design.md §8.8b). Three dogs are let
## loose down a clear stretch ahead of the operative. Saves dogs_<moment>.png
## from his eyes and dogs_<moment>_side.png from beside the run: charge (the
## pack galloping in), leap (the first dog in the air, jaw open), bite (it
## connects), down (one shot dead, lying where it fell); then lets
## CaptureDirector finish.

var map: ChinatownMap
var dogs: Array[AttackDog] = []
var _dir: String = ""
var _frame: int = 0
var _done: Dictionary[String, bool] = {}
var _side: Camera3D
var _fwd: Vector3
var _right: Vector3
var _run: float = 16.0
var _bite_frame: int = -1
var _shot_frame: int = -1
var _pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	map.player.input_enabled = false
	map.player.invulnerable = true


func _physics_process(_delta: float) -> void:
	_frame += 1
	var p: Player = map.player
	if _frame == 20:
		_pick_lane(p)
	if _frame == 24:
		var eye: Vector3 = p.camera().global_position
		var base: Vector3 = p.global_position + _fwd * _run
		var offsets: Array[Vector3] = [Vector3.ZERO, _right * 1.4 + _fwd * 1.6, -_right * 1.3 + _fwd * 2.8]
		for o: Vector3 in offsets:
			var d: AttackDog = AttackDog.new()
			d.player = p
			map.add_child(d)
			d.global_position = base + o + Vector3.UP * 0.1
			var to: Vector3 = p.global_position - d.global_position
			d.face(atan2(to.x, to.z))
			dogs.append(d)
		_side = Camera3D.new()
		_side.fov = 60.0
		map.add_child(_side)
		var mid: Vector3 = p.global_position + _fwd * (_run * 0.42)
		_side.look_at_from_position(mid + _right * 4.2 + Vector3.UP * 0.9 - _fwd * 1.0, mid - _fwd * 2.5 + Vector3.UP * 0.4)
		p.set_view(atan2(-_fwd.x, -_fwd.z), -0.12)
		print("dog demo: lane %.1f m, eye %s" % [_run, eye])
	if dogs.is_empty():
		return
	var lead: AttackDog = dogs[0]
	if _frame == 52:
		_snap("charge")
	if (lead.state == AttackDog.State.LUNGE and lead._t >= 0.1) and not _done.has("leap"):
		_snap("leap")
	if lead.bites > 0 and _bite_frame < 0:
		_bite_frame = _frame
	if _bite_frame > 0 and _frame == _bite_frame + 1:
		_snap("bite")
	# Then he shoots the second dog in the head and it goes down.
	if _bite_frame > 0 and _frame == _bite_frame + 12 and dogs.size() > 1 and dogs[1].alive:
		var from: Vector3 = p.camera().global_position
		for i: int in 3:
			if dogs[1].alive:
				Ballistics.fire(_pistol, from, (dogs[1].head_position() - from).normalized(), p)
		_shot_frame = _frame
	if _shot_frame > 0 and _frame == _shot_frame + 70:
		for d: AttackDog in dogs:
			d.set_physics_process(d == dogs[1])
		p.set_view(atan2(-(dogs[1].global_position - p.global_position).x, -(dogs[1].global_position - p.global_position).z), -0.35)
		_side.look_at_from_position(dogs[1].global_position + _right * 2.2 + Vector3.UP * 1.1 + _fwd * 0.8, dogs[1].global_position + Vector3.UP * 0.2)
	if _shot_frame > 0 and _frame == _shot_frame + 74:
		_snap("down")
	if _frame > 600 or (_shot_frame > 0 and _frame > _shot_frame + 90):
		print("dog demo: bites %d whiffs %d dead %d" % [lead.bites, lead.whiffs, dogs.filter(func(d: AttackDog) -> bool: return not d.alive).size()])
		set_physics_process(false)
		await get_tree().create_timer(0.5).timeout
		remove_from_group(&"capture_busy")


## The clearest straight stretch from the operative (the dogs come down it).
func _pick_lane(p: Player) -> void:
	var space: PhysicsDirectSpaceState3D = p.get_world_3d().direct_space_state
	var from: Vector3 = p.global_position + Vector3.UP * 0.5
	var best: float = -1.0
	for i: int in 24:
		var dir: Vector3 = Vector3.FORWARD.rotated(Vector3.UP, TAU * i / 24.0)
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, from + dir * 22.0, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
		var hit: Dictionary = space.intersect_ray(q)
		var d: float = 22.0 if hit.is_empty() else from.distance_to(hit["position"])
		if d > best:
			best = d
			_fwd = dir
	_run = clampf(best - 3.0, 9.0, 16.0)
	_right = _fwd.cross(Vector3.UP).normalized()


func _snap(moment: String) -> void:
	if _done.has(moment):
		return
	_done[moment] = true
	_shoot.call_deferred(moment)


func _shoot(moment: String) -> void:
	if _dir.is_empty():
		return
	get_tree().paused = true
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("dogs_%s.png" % moment))
	_side.make_current()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("dogs_%s_side.png" % moment))
	map.player.camera().make_current()
	get_tree().paused = false
	print("capture dogs_%s" % moment)
