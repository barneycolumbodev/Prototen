extends GutTest
## Movement tech (M1b): slide, slide-hop, wall-run, mantle, in the real test room.

var room: TestRoom
var player: Player


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(20)


func after_each() -> void:
	for action: StringName in [&"move_forward", &"sprint", &"jump", &"slide"]:
		Input.action_release(action)


func _sprint() -> void:
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_physics_frames(2)
	Input.action_release(&"sprint")
	await wait_physics_frames(25)


func _speed() -> float:
	return Vector2(player.velocity.x, player.velocity.z).length()


func test_b_while_sprinting_slides_faster_and_lower() -> void:
	await _sprint()
	var eye: float = player.camera().global_position.y
	Input.action_press(&"slide")
	await wait_physics_frames(3)
	assert_true(player.is_sliding(), "sliding")
	assert_gt(_speed(), player.movement.sprint_speed, "the slide starts faster than a sprint")
	await wait_physics_frames(12)
	assert_lt(player.camera().global_position.y, eye - 0.2, "camera drops")
	await wait_physics_frames(170)
	assert_false(player.is_sliding(), "it runs out")
	assert_true(player.is_crouching(), "and leaves you crouched while B is held")


func test_a_tap_of_b_slides_the_whole_way() -> void:
	# Owner, 2026-11-07: no holding B, a tap runs it out. 2026-11-14: but
	# shorter (about 7 m), a move for cover and shots, not for skating.
	await _sprint()
	var start: Vector3 = player.global_position
	Input.action_press(&"slide")
	await wait_physics_frames(2)
	Input.action_release(&"slide")
	await wait_physics_frames(20)
	assert_true(player.is_sliding(), "still sliding after letting go")
	var t: int = 0
	while player.is_sliding() and t < 300:
		await wait_physics_frames(1)
		t += 1
	var dist: float = Vector2(player.global_position.x - start.x, player.global_position.z - start.z).length()
	assert_between(dist, 5.0, 10.0, "a short slide (%.1f m)" % dist)
	assert_lt(t, 60, "over in under a second and a bit")


func test_b_again_ends_the_slide() -> void:
	await _sprint()
	Input.action_press(&"slide")
	await wait_physics_frames(2)
	Input.action_release(&"slide")
	await wait_physics_frames(10)
	Input.action_press(&"slide")
	await wait_physics_frames(2)
	assert_false(player.is_sliding(), "a second tap stands you up")


func test_sliding_into_an_enemy_launches_him() -> void:
	# Owner, 2026-11-14 (after Dishonored): no damage, he goes up in the air.
	var e: Enemy = room.shooting_range.targets[0]
	await _sprint()
	var fwd: Vector3 = -player.global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	e.global_position = player.global_position + fwd * 4.0
	await wait_physics_frames(2)
	var before: Vector3 = e.global_position
	var hp: float = e.health
	var hits: Array[float] = []
	EventBus.slide_impact.connect(func(_n: Node, push: float) -> void: hits.append(push))
	Input.action_press(&"slide")
	await wait_physics_frames(2)
	Input.action_release(&"slide")
	var peak: float = 0.0
	var was_launched: bool = false
	for i: int in 60:
		await wait_physics_frames(1)
		peak = maxf(peak, e.global_position.y - before.y)
		was_launched = was_launched or e.launched
	assert_eq(hits.size(), 1, "one hit per slide")
	assert_true(was_launched, "launched")
	assert_gt(peak, 0.9, "up in the air (%.2f m)" % peak)
	var moved: Vector3 = e.global_position - before
	moved.y = 0.0
	assert_gt(moved.dot(fwd), 0.6, "and along the slide (%.2f m)" % moved.dot(fwd))
	assert_eq(e.health, hp, "no damage")
	assert_true(e.alive)
	await wait_physics_frames(90)
	assert_false(e.launched, "back on his feet")
	assert_lt(e.global_position.y - before.y, 0.1, "on the ground")


func test_jumping_out_of_a_slide_keeps_the_speed() -> void:
	await _sprint()
	Input.action_press(&"slide")
	await wait_physics_frames(4)
	Input.action_press(&"jump")
	await wait_physics_frames(3)
	Input.action_release(&"jump")
	assert_false(player.is_sliding())
	assert_false(player.is_on_floor(), "hopped")
	assert_gt(_speed(), player.movement.sprint_speed, "with the slide's speed")


func test_wall_run_holds_you_up() -> void:
	# Beside the free-standing wall at x = -9 (it runs north-south), in the air, heading north.
	player.global_position = Vector3(-8.3, 2.0, 11.0)
	player.set_view(0.0, 0.0)
	player.velocity = Vector3(0, 0, -9.0)
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(3)
	assert_true(player.is_wallrunning(), "running on the wall")
	var y0: float = player.global_position.y
	await wait_physics_frames(30)
	assert_true(player.is_wallrunning(), "still on it half a second later")
	# Free fall from rest would drop 0.5 * 22 * 0.5² = 2.75 m in that time.
	assert_gt(player.global_position.y, y0 - 1.0, "barely dropped (%.2f m)" % (y0 - player.global_position.y))
	assert_lt(player.global_position.z, 7.5, "ran along it")
	Input.action_press(&"jump")
	await wait_physics_frames(3)
	assert_false(player.is_wallrunning(), "jumped off")
	assert_gt(player.velocity.x, 3.0, "pushed away from the wall (+X)")


func test_a_at_a_ledge_mantles_onto_it() -> void:
	# The 1.5 m block on the west wall: east face at x = -14, centre z = -1.
	player.global_position = Vector3(-13.3, 0.0, -1.0)
	player.set_view(PI * 0.5, 0.0)  # facing -X
	await wait_physics_frames(5)
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"jump")
	await wait_physics_frames(3)
	Input.action_release(&"jump")
	assert_true(player.is_mantling(), "climbing")
	await wait_physics_frames(45)
	assert_false(player.is_mantling())
	assert_almost_eq(player.global_position.y, 1.5, 0.1, "standing on the ledge")
	assert_lt(player.global_position.x, -14.0, "on top, past the edge")


func _box_ahead(distance: float, height: float) -> StaticBody3D:
	var b: StaticBody3D = StaticBody3D.new()
	b.collision_layer = Ballistics.LAYER_WORLD
	var cs: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(6.0, height, 30.0)
	cs.shape = box
	b.add_child(cs)
	room.add_child(b)
	var fwd: Vector3 = -player.global_basis.z
	b.global_position = player.global_position + fwd * (distance + 15.0) + Vector3.UP * height * 0.5
	b.global_basis = player.global_basis
	return b


func test_running_over_a_curb_keeps_speed() -> void:
	# Playtest 2026-11-05: movement felt clumsy; a 20 cm curb stopped you dead.
	_box_ahead(1.5, 0.2)
	await wait_physics_frames(2)
	var y0: float = player.global_position.y
	Input.action_press(&"move_forward", 1.0)
	var slowest: float = 99.0
	for i: int in 40:
		await wait_physics_frames(1)
		if i > 12:
			slowest = minf(slowest, _speed())
	assert_gt(slowest, player.movement.walk_speed - 0.5, "the curb doesn't stop you (slowest %.1f m/s)" % slowest)
	assert_gt(player.global_position.y, y0 + 0.17, "up on the curb (%.2f m)" % (player.global_position.y - y0))
	assert_gt(_speed(), player.movement.walk_speed, "still running (%.1f m/s)" % _speed())


func test_a_crate_still_blocks() -> void:
	_box_ahead(1.0, 0.7)
	await wait_physics_frames(2)
	var y0: float = player.global_position.y
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(50)
	assert_lt(player.global_position.y, y0 + 0.1, "a 70 cm crate is a mantle, not a step")


func test_full_tilt_sprints_without_l3() -> void:
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(30)
	assert_true(player.is_sprinting(), "auto-sprint")
	assert_gt(_speed(), player.movement.walk_speed + 1.0)


func test_a_slide_hop_keeps_its_speed_after_landing() -> void:
	await _sprint()
	Input.action_press(&"slide")
	await wait_physics_frames(4)
	Input.action_release(&"slide")
	Input.action_press(&"jump")
	await wait_physics_frames(2)
	Input.action_release(&"jump")
	var t: int = 0
	while not player.is_on_floor() and t < 120:
		await wait_physics_frames(1)
		t += 1
	var landed_at: float = _speed()
	assert_gt(landed_at, player.movement.sprint_speed, "faster than a sprint when it lands (%.1f)" % landed_at)
	await wait_physics_frames(18)
	assert_gt(_speed(), landed_at * 0.8, "most of it is still there 0.3 s later (%.1f of %.1f)" % [_speed(), landed_at])


func test_a_tap_of_a_jumps_lower_than_holding_it() -> void:
	var heights: Array[float] = []
	for hold: int in [2, 40]:
		player.global_position = player.spawn_point
		player.velocity = Vector3.ZERO
		await wait_physics_frames(10)
		var y0: float = player.global_position.y
		var top: float = y0
		Input.action_press(&"jump")
		for i: int in 60:
			if i == hold:
				Input.action_release(&"jump")
			await wait_physics_frames(1)
			top = maxf(top, player.global_position.y)
		Input.action_release(&"jump")
		heights.append(top - y0)
	assert_lt(heights[0], heights[1] * 0.8, "short hop %.2f m vs full jump %.2f m" % [heights[0], heights[1]])


func test_the_camera_moves_smoothly_between_physics_ticks() -> void:
	# Frames that don't line up with the 60 Hz physics ticks (40 fps here, as
	# on a phone that drops frames: one tick some frames, two others). The
	# body only moves on ticks; the camera is drawn between them, so its
	# speed per frame stays even.
	var fps: int = Engine.max_fps
	Engine.max_fps = 40
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(20)
	var probe: FrameProbe = FrameProbe.new()
	probe.player = player
	add_child_autofree(probe)
	var frames: int = 0
	while frames < 120 and probe.cam_steps.size() < 30:
		await get_tree().process_frame
		frames += 1
	var cam_steps: Array[float] = probe.cam_steps
	var body_steps: Array[float] = probe.body_steps
	var spread: Callable = func(a: Array[float]) -> float:
		var m: float = 0.0
		for v: float in a:
			m += v
		m /= maxf(a.size(), 1)
		var var_sum: float = 0.0
		for v: float in a:
			var_sum += (v - m) * (v - m)
		return sqrt(var_sum / maxf(a.size(), 1)) / maxf(m, 0.001)
	Engine.max_fps = fps
	var cam_cv: float = spread.call(cam_steps)
	var body_cv: float = spread.call(body_steps)
	gut.p("camera speed spread %.2f, body %.2f over %d frames" % [cam_cv, body_cv, cam_steps.size()])
	if body_cv < 0.15:
		pass_test("frames lined up with ticks in this run (body spread %.2f): nothing to smooth" % body_cv)
		return
	assert_lt(cam_cv, body_cv * 0.5, "the camera's motion per frame is far more even than the body's")
	Input.action_release(&"move_forward")


## Samples the camera after every other node's _process (what gets drawn).
class FrameProbe:
	extends Node
	var player: Player
	var cam_steps: Array[float] = []
	var body_steps: Array[float] = []
	var _last_cam: Vector3 = Vector3.INF
	var _last_body: Vector3

	func _ready() -> void:
		process_priority = 10000

	func _process(dt: float) -> void:
		var c: Vector3 = player.camera().global_position
		var b: Vector3 = player.global_position
		# Only the regular 40 fps frames (the odd stretched or squeezed one
		# while the frame cap settles would swamp the measure).
		if _last_cam != Vector3.INF and absf(dt - 0.025) < 0.004:
			cam_steps.append(Vector2(c.x - _last_cam.x, c.z - _last_cam.z).length() / dt)
			body_steps.append(Vector2(b.x - _last_body.x, b.z - _last_body.z).length() / dt)
		_last_cam = c
		_last_body = b
