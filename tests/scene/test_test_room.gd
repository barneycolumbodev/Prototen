extends GutTest
## Loads the real test room and drives the player with simulated controller input.

var room: TestRoom
var player: Player


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	await wait_physics_frames(30)


func after_each() -> void:
	for action: StringName in [&"move_forward", &"sprint", &"jump", &"slide", &"look_right"]:
		Input.action_release(action)


func test_player_lands_on_floor() -> void:
	assert_true(player.is_on_floor())
	assert_almost_eq(player.global_position.y, 0.0, 0.05)


func test_stick_forward_moves_north_at_walk_speed() -> void:
	var start: Vector3 = player.global_position
	# Just under full tilt (full tilt auto-sprints).
	player.movement = player.movement.duplicate() as MovementConfig
	player.movement.auto_sprint = false
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(30)
	var speed: float = Vector2(player.velocity.x, player.velocity.z).length()
	assert_almost_eq(speed, player.movement.walk_speed * player.speed_factor(), 0.2, "walk speed × the body's speed factor")
	assert_lt(player.global_position.z, start.z - 1.0, "moved toward -Z")


func test_sprint_is_faster_and_ends_when_stick_released() -> void:
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_physics_frames(2)
	Input.action_release(&"sprint")
	await wait_physics_frames(30)
	assert_true(player.is_sprinting())
	assert_almost_eq(Vector2(player.velocity.x, player.velocity.z).length(), player.movement.sprint_speed * player.speed_factor(), 0.3)
	Input.action_release(&"move_forward")
	await wait_physics_frames(2)
	assert_false(player.is_sprinting())


func test_jump_leaves_floor_and_lands() -> void:
	Input.action_press(&"jump")
	await wait_physics_frames(3)
	Input.action_release(&"jump")
	assert_false(player.is_on_floor())
	await wait_physics_frames(60)
	assert_true(player.is_on_floor())


func test_crouch_lowers_the_camera() -> void:
	var standing: float = player.camera().global_position.y
	Input.action_press(&"slide")
	await wait_frames(30)
	assert_true(player.is_crouching())
	assert_lt(player.camera().global_position.y, standing - 0.5)


func test_right_stick_turns_right() -> void:
	var yaw0: float = player.yaw
	Input.action_press(&"look_right", 1.0)
	await wait_frames(20)
	assert_lt(player.yaw, yaw0, "yaw decreases when turning right")


func test_lighting_within_budget() -> void:
	# CLAUDE.md §8: at most 4 dynamic lights, only one casts shadows.
	var lights: Array[Node] = room.find_children("*", "Light3D", true, false)
	var shadowed: int = 0
	for node: Node in lights:
		if (node as Light3D).shadow_enabled:
			shadowed += 1
	assert_lte(lights.size(), 4)
	assert_eq(shadowed, 1)


func test_has_capture_cameras() -> void:
	assert_gte(get_tree().get_nodes_in_group(&"capture_cameras").size(), 3)
