extends GutTest
## RX-9 Reflex Overclock (owner, 2026-11-05): LB toggles time slowdown; it
## drains a charge that refills over time; no holding.

var room: TestRoom
var player: Player
var td: TimeDilation


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(10)
	td = player.augments.part(1) as TimeDilation


func after_each() -> void:
	for a: StringName in [&"active_1", &"move_forward"]:
		Input.action_release(a)
	TimeControl.set_dilation(1.0, 1.0)


func _tap_lb() -> void:
	Input.action_press(&"active_1")
	await wait_frames(2)
	Input.action_release(&"active_1")
	await wait_frames(1)


func _real_wait(seconds: float) -> void:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await wait_frames(1)


func test_lb_slows_the_world_and_lb_again_stops_it() -> void:
	assert_not_null(td, "RX-9 is on LB")
	await _tap_lb()
	assert_true(td.is_running(), "a tap starts it (no holding)")
	await _real_wait(0.5)
	assert_eq(td.state, ActivePart.State.ACTIVE)
	assert_almost_eq(Engine.time_scale, td.cfg.world_scale, 0.02, "the world runs at 30 %")
	assert_gt(TimeControl.player_boost(), 1.5, "the operative runs faster than the world")
	var before: float = td.charge
	await _real_wait(0.5)
	assert_lt(td.charge, before - 0.3, "charge drains in real time")
	await _tap_lb()
	assert_false(td.is_running(), "a second tap stops it")
	await _real_wait(td.data.recover_time + 0.2)
	assert_almost_eq(Engine.time_scale, 1.0, 0.01, "back to normal time")


func test_runs_out_and_refills() -> void:
	td.charge = td.data.min_to_start + 0.2
	await _tap_lb()
	await _real_wait(td.charge / td.data.drain_per_s + 0.4)
	assert_false(td.is_running(), "stops by itself when the charge is gone")
	await _real_wait(td.data.recover_time + td.data.cooldown_time + 0.2)
	assert_almost_eq(Engine.time_scale, 1.0, 0.01)
	var empty: float = td.charge
	await _real_wait(td.data.regen_delay + 0.6)
	assert_gt(td.charge, empty + 0.1, "refills over time, like health")
	await _tap_lb()
	assert_false(td.is_running(), "can't start below the minimum")


func test_player_moves_faster_relative_to_the_world() -> void:
	player.movement = player.movement.duplicate() as MovementConfig
	player.movement.auto_sprint = false
	await _tap_lb()
	await _real_wait(0.4)
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(20)
	var z0: float = player.global_position.z
	var frames: int = 30
	await wait_physics_frames(frames)
	var moved: float = absf(player.global_position.z - z0)
	var game_seconds: float = frames / float(Engine.physics_ticks_per_second) * Engine.time_scale
	var expected_slowed: float = player.movement.walk_speed * game_seconds
	assert_gt(moved, expected_slowed * 1.6, "covers more ground than the slowed world would let it (%.2f m)" % moved)


func test_death_ends_it() -> void:
	await _tap_lb()
	await _real_wait(0.3)
	player.invulnerable = false
	player.take_damage(99999.0, Vector3.FORWARD)
	await wait_frames(2)
	assert_false(td.is_running())
	assert_almost_eq(Engine.time_scale, 1.0, 0.01)
