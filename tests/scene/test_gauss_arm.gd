extends GutTest
## GX-4 Gauss arm (owner, 2026-11-07): D-pad down selects it, LB raises it
## and it transforms into a coilgun, RT fires 10 rounds that go through
## people, LB folds it away; the gun comes back.

var room: TestRoom
var player: Player
var arm: GaussArm
var _gore: int = 2


func before_each() -> void:
	_gore = Settings.gore_level
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(10)
	arm = player.augments.part(2) as GaussArm


func after_each() -> void:
	for a: StringName in [&"active_use", &"active_select_1", &"active_select_2", &"fire"]:
		Input.action_release(a)
	Settings.gore_level = _gore
	TimeControl.set_dilation(1.0, 1.0)
	Gore.clear()


func _tap(action: StringName) -> void:
	Input.action_press(action)
	await wait_frames(2)
	Input.action_release(action)
	await wait_frames(1)


func _real_wait(seconds: float) -> void:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await wait_frames(1)


func _deploy() -> void:
	await _tap(&"active_select_2")
	await _tap(&"active_use")
	await _real_wait(arm.data.deploy_time + 0.2)


func test_it_is_installed_on_d_pad_down() -> void:
	assert_not_null(arm, "GX-4 in slot 2")
	assert_eq(arm.hud_pips(), 10, "ten rounds")
	assert_eq(player.augments.selected, 1, "RX-9 (D-pad left) is selected at start")
	await _tap(&"active_select_2")
	assert_eq(player.augments.selected, 2, "D-pad down selects the arm")
	await _tap(&"active_select_1")
	assert_eq(player.augments.selected, 1, "D-pad left goes back to RX-9")


func test_lb_transforms_the_arm_and_stows_the_gun() -> void:
	await _tap(&"active_select_2")
	await _tap(&"active_use")
	assert_true(arm.is_running(), "deploying")
	assert_true(player.weapon().stowed, "the gun goes down")
	assert_true(arm.rig.visible, "the arm comes up")
	assert_not_null(arm.anim, "the transform animation was imported")
	await _real_wait(arm.data.deploy_time + 0.2)
	assert_eq(arm.state, ActivePart.State.ACTIVE)
	assert_almost_eq(arm.anim.current_animation_position, arm.anim_len, 0.02, "fully transformed")
	var coil: Node3D = arm.coils[5]
	assert_gt(coil.position.x, 0.15, "the front coil slid out along the rails")
	assert_true(player.weapon().is_stowed_away(), "gun hidden")


func test_the_round_goes_through_two_men() -> void:
	# Standard gore: at Maximum the slug bursts both men instead (2026-11-11,
	# tests/scene/test_gore.gd), leaving nothing for the arcs to crawl over.
	Settings.gore_level = 1
	await _deploy()
	var cam: Camera3D = player.camera()
	var fwd: Vector3 = -cam.global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	var a: Enemy = room.shooting_range.targets[0]
	var b: Enemy = room.shooting_range.targets[1]
	var base: Vector3 = player.global_position
	a.global_position = base + fwd * 6.0
	b.global_position = base + fwd * 9.0
	a.face(0.0)
	b.face(0.0)
	await wait_physics_frames(3)
	# Aim at chest height on the first man.
	var aim: Vector3 = a.body.chest_position() - cam.global_position
	player.set_view(atan2(-aim.x, -aim.z), atan2(aim.y, Vector2(aim.x, aim.z).length()))
	await wait_physics_frames(2)
	var before: int = arm.rounds()
	arm.script_fire()
	await wait_physics_frames(12)
	assert_eq(arm.rounds(), before - 1, "one round spent")
	assert_false(a.alive, "first man down")
	assert_false(b.alive, "the slug went on through the second")
	assert_gt(Gore.gauss.corkscrews_fired, 0, "corkscrew wound")
	assert_gt(Gore.gauss.live_shocks(), 0, "the bodies are being electrocuted")
	assert_gt(Fx.live_beams(), 0, "the beam is drawn")


func test_empty_it_folds_away_and_the_gun_comes_back() -> void:
	await _deploy()
	arm.charge = 1.0
	arm.script_fire()
	await wait_frames(3)
	assert_eq(arm.rounds(), 0)
	await _real_wait(arm.cfg.empty_stow_delay + arm.data.recover_time + 0.3)
	assert_false(arm.is_running(), "folded away by itself")
	assert_false(arm.rig.visible, "arm gone")
	assert_false(player.weapon().stowed, "gun back in hand")
	await _tap(&"active_use")
	assert_false(arm.is_running(), "can't raise it with no rounds")
	await _real_wait(arm.data.regen_delay + 4.5)
	assert_gte(arm.rounds(), 1, "rounds refill while folded")


func test_lb_again_folds_it_early_and_keeps_the_rounds() -> void:
	await _deploy()
	arm.script_fire()
	await wait_frames(3)
	var left: int = arm.rounds()
	await _tap(&"active_use")
	assert_eq(arm.state, ActivePart.State.RECOVERING, "folding")
	await _real_wait(arm.data.recover_time + 0.2)
	assert_false(arm.rig.visible)
	assert_false(player.weapon().stowed, "gun back")
	assert_eq(arm.rounds(), left, "rounds kept")


func test_rx9_and_the_arm_run_together() -> void:
	var td: ActivePart = player.augments.part(1)
	await _tap(&"active_use")
	assert_true(td.is_running(), "RX-9 on")
	await _deploy()
	assert_true(td.is_running(), "still on after selecting and raising the arm")
	assert_true(arm.is_running())
