extends GutTest
## Dropkick scene tests (docs/design.md §5.7b): midair second-A trigger, brutal
## enemy knockback & rebound, Max Payne midair shooting with RX-9 slow-mo, and
## compatibility with normal jump / ledge mantle.

var room: TestRoom
var player: Player


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(15)


func after_each() -> void:
	for action: StringName in [&"move_forward", &"sprint", &"jump", &"slide", &"active_use"]:
		Input.action_release(action)
	if player and player.weapon():
		player.weapon().end_script_input()
	TimeControl.set_dilation(1.0, 1.0)


func _tap_jump() -> void:
	Input.action_press(&"jump")
	await wait_physics_frames(2)
	Input.action_release(&"jump")


func test_midair_jump_launches_dropkick_and_recovers() -> void:
	var start: Vector3 = player.global_position
	Input.action_press(&"move_forward", 1.0)
	await wait_physics_frames(8)
	await _tap_jump()
	await wait_physics_frames(8)
	assert_false(player.is_on_floor(), "airborne after first jump")
	await _tap_jump()
	await wait_physics_frames(2)
	assert_true(player.is_dropkicking(), "second A press midair starts dropkick")
	assert_eq(player.dropkick_phase_now(), Player.DropkickPhase.KICK, "in KICK phase")
	assert_not_null(player.dropkick_view, "legs viewmodel exists")
	assert_true(player.dropkick_view.is_active(), "legs viewmodel playing")
	var fwd_speed: float = Vector2(player.velocity.x, player.velocity.z).length()
	assert_gt(fwd_speed, player.movement.sprint_speed, "surges forward faster than a sprint (%.1f m/s)" % fwd_speed)
	Input.action_release(&"move_forward")
	# Wait for flight + ground skid recovery to finish cleanly.
	var ticks: int = 0
	while player.is_dropkicking() and ticks < 140:
		await wait_physics_frames(1)
		ticks += 1
	assert_false(player.is_dropkicking(), "cleanly finished recovery in %d ticks" % ticks)
	assert_true(player.is_on_floor(), "back on the ground")
	var dist: float = Vector2(player.global_position.x - start.x, player.global_position.z - start.z).length()
	assert_gt(dist, 5.0, "covered real diving distance (%.1f m)" % dist)


func test_dropkick_launches_enemy_far_deals_damage_and_rebounds_player() -> void:
	var e: Enemy = room.shooting_range.targets[0]
	player.global_position = Vector3(0.0, 0.0, 8.0)
	player.set_view(0.0, 0.0)
	player.reset_camera_smoothing()
	var fwd: Vector3 = -player.global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	e.global_position = player.global_position + fwd * 4.2
	await wait_physics_frames(4)
	var before: Vector3 = e.global_position
	var hp0: float = e.health
	var hits: Array[float] = []
	var cb: Callable = func(_n: Node, push: float) -> void: hits.append(push)
	EventBus.dropkick_impact.connect(cb)

	Input.action_press(&"move_forward", 1.0)
	await _tap_jump()
	await wait_physics_frames(8)
	await _tap_jump()
	Input.action_release(&"move_forward")

	var peak: float = 0.0
	var saw_rebound: bool = false
	var rebounded_back: bool = false
	for i: int in 90:
		await wait_physics_frames(1)
		peak = maxf(peak, e.global_position.y - before.y)
		if player.dropkick_phase_now() == Player.DropkickPhase.REBOUND:
			saw_rebound = true
			if Vector3(player.velocity.x, 0.0, player.velocity.z).dot(fwd) < -1.0:
				rebounded_back = true
	EventBus.dropkick_impact.disconnect(cb)

	assert_eq(hits.size(), 1, "one dropkick impact")
	assert_true(saw_rebound, "player entered REBOUND phase on impact")
	assert_true(rebounded_back, "player rebounded backward off the enemy")
	assert_gt(peak, 1.3, "enemy launched high in the air (%.2f m)" % peak)
	var horiz: float = (e.global_position - before).dot(fwd)
	assert_between(horiz, 5.0, 12.5, "enemy knocked back far, not crazy far (%.2f m)" % horiz)
	assert_lt(e.health, hp0, "dropkick dealt blunt impact damage (%.0f -> %.0f)" % [hp0, e.health])
	assert_true(e.alive, "full-health gunman survives the kick to be shot in midair")


func test_dropkick_allows_crisp_midair_shooting_with_rx9() -> void:
	# Measure normal airborne spread first.
	await _tap_jump()
	await wait_physics_frames(8)
	var w: PlayerWeapon = player.weapon()
	var normal_air_spread: float = w.spread
	# Engage RX-9 Reflex Overclock (slot 0 on default Operator loadout) and launch dropkick!
	var rx9: ActivePart = player.augments.selected_part()
	assert_not_null(rx9, "default loadout carries RX-9")
	rx9.toggle()
	await wait_physics_frames(6)
	await _tap_jump()
	await wait_physics_frames(6)
	assert_true(player.is_dropkicking(), "dropkicking during RX-9 slow-mo")
	assert_lt(w.spread, normal_air_spread, "dropkick dive tightens airborne spread (%.2f vs %.2f)" % [w.spread, normal_air_spread])
	# Fire midair right out of the dive!
	var ammo_before: int = w.mechanism.loaded()
	w.script_input(true, false)
	await wait_physics_frames(4)
	w.script_input(false, false)
	assert_lt(w.mechanism.loaded(), ammo_before, "gun fires cleanly mid-dropkick in RX-9 slow-mo")
	assert_gt(player.dropkick_gun_dive(), 0.2, "gun whipped into Max Payne dive stance")
	rx9.stop()


func test_dropkick_preserves_ledge_mantle() -> void:
	# Pressing A at the 1.5 m west block still mantles instead of dropkicking.
	player.global_position = Vector3(-13.3, 0.0, -1.0)
	player.set_view(PI * 0.5, 0.0)
	await wait_physics_frames(5)
	Input.action_press(&"move_forward", 1.0)
	await _tap_jump()
	await wait_physics_frames(2)
	assert_true(player.is_mantling(), "mantle takes priority at a ledge")
	assert_false(player.is_dropkicking(), "did not hijack mantle")
