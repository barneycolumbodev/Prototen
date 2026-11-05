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
	await wait_physics_frames(90)
	assert_false(player.is_sliding(), "it runs out")
	assert_true(player.is_crouching(), "and leaves you crouched while B is held")


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
