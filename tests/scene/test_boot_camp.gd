extends GutTest
## Boot camp (docs/design.md §8.11): the guided range sequence follows what
## the player does, step by step, ends in one live wave, and is remembered.

var room: TestRoom
var camp: BootCamp


func before_each() -> void:
	TutorialStore.clear_for_tests()
	TestRoom.boot_camp_pending = true
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	await wait_physics_frames(20)
	camp = room.boot_camp


func after_each() -> void:
	for a: StringName in [&"move_forward", &"sprint"]:
		Input.action_release(a)


func _row(i: int) -> bool:
	var done: bool = camp.checks[i][1]
	return done


func _skip_to(s: BootCamp.Step) -> void:
	while camp.step != s:
		var was: BootCamp.Step = camp.step
		camp.skip_step()
		await wait_until(func() -> bool: return camp.step != was, 3.0)


func test_steps_follow_the_player() -> void:
	assert_not_null(camp, "the range opened on boot camp")
	assert_eq(camp.step, BootCamp.Step.MOVE)
	assert_true(camp.card.is_presented(), "the card is up")
	for t: Enemy in room.shooting_range.targets:
		assert_null(t, "the range's own targets are cleared away")
	assert_eq(room.player.weapon().slots.size(), 1, "just the Five-seveN")
	# Walk onto the marker.
	room.player.global_position = camp.config.walk_marker
	await wait_until(func() -> bool: return camp.step == BootCamp.Step.SPRINT, 3.0)
	assert_eq(camp.step, BootCamp.Step.SPRINT)
	# Sprint north.
	room.player.set_view(0.0, 0.0)
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_until(func() -> bool: return camp.step == BootCamp.Step.SLIDE, 6.0)
	Input.action_release(&"sprint")
	Input.action_release(&"move_forward")
	assert_eq(camp.step, BootCamp.Step.SLIDE, "sprinted %.1f m" % camp.count)
	await _skip_to(BootCamp.Step.SHOOT)
	# Three plates down with real rounds.
	var gun: WeaponData = BootCamp.GUN
	for i: int in 3:
		var at: Vector3 = room.shooting_range.plates[i].aim_points()[0]
		Ballistics.fire(gun, at + Vector3(0, 0.3, 6.0), (at - (at + Vector3(0, 0.3, 6.0))).normalized(), room.player)
		await wait_physics_frames(6)
	await wait_until(func() -> bool: return camp.step == BootCamp.Step.KNIFE, 3.0)
	assert_eq(camp.step, BootCamp.Step.KNIFE, "plates down: %d" % camp.count)
	# The knife: up to him, R3.
	var man: Enemy = camp.target
	assert_not_null(man)
	assert_true(man.passive, "he doesn't fire back")
	var at_man: Vector3 = man.global_position + Vector3(0, 0, 1.4)
	room.player.global_position = at_man
	room.player.set_view(0.0, -0.2)
	await wait_physics_frames(4)
	room.player.melee.script_strike()
	await wait_until(func() -> bool: return camp.step == BootCamp.Step.DROPKICK, 3.0)
	assert_eq(camp.step, BootCamp.Step.DROPKICK)


func test_active_checklist_goes_in_order() -> void:
	await _skip_to(BootCamp.Step.GAUSS)
	var aug: Augments = room.player.augments
	var gx: ActivePart = aug.find(BootCamp.GX4)
	assert_not_null(gx, "the default body carries the GX-4")
	assert_ne(aug.selected, gx.slot, "RX-9 is picked to start with")
	aug.select(gx.slot)
	await wait_physics_frames(2)
	assert_true(_row(0), "selected")
	aug.use_selected()
	await wait_physics_frames(2)
	assert_true(_row(1), "deployed")
	aug.use_selected()
	await wait_physics_frames(2)
	assert_false(_row(3), "putting it away doesn't count before a shot")
	assert_eq(camp.step, BootCamp.Step.GAUSS)


func test_live_wave_then_the_end_card() -> void:
	await _skip_to(BootCamp.Step.LIVE)
	var wm: WaveMode = room.wave_mode
	assert_true(wm.running)
	await wait_until(func() -> bool: return wm.enemies.size() == camp.config.wave.size(), 10.0)
	assert_eq(wm.enemies.size(), camp.config.wave.size(), "one small wave")
	for e: Enemy in wm.enemies:
		assert_false(e.passive, "these shoot back")
		e.die(null, &"chest")
	await wait_until(func() -> bool: return camp.step == BootCamp.Step.DONE, 4.0)
	assert_eq(camp.step, BootCamp.Step.DONE)
	assert_false(wm.running, "no wave 2")
	assert_not_null(camp.end_screen)
	assert_true(TutorialStore.boot_camp_done(), "remembered")
	assert_false(room.player.input_enabled, "the end card has the pad")
	camp.stay()
	await wait_physics_frames(2)
	assert_true(room.player.input_enabled)
	assert_not_null(room.shooting_range.targets[0], "the range is back")
	assert_gt(room.player.weapon().slots.size(), 1, "every gun again")
