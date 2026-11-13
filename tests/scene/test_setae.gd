extends GutTest
## SX-8 Urticating Setae (docs/design.md §3.4c, owner 2026-11-13): the
## fibres grow, the world slows, marks go on body parts, the throw kills
## what was marked and gives time back.

var room: TestRoom
var player: Player
var lib: PartLibrary = preload("res://data/body/part_library.tres")
var _gore: int = 2


func before_each() -> void:
	_gore = Settings.gore_level
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(10)
	player.global_position = Vector3(0.5, 0.0, 6.0)
	player.set_view(0.0, 0.0)


func after_each() -> void:
	for a: StringName in [&"active_use", &"fire", &"aim"]:
		Input.action_release(a)
	Settings.gore_level = _gore
	TimeControl.set_dilation(1.0, 1.0)
	Gore.clear()


func _equip(ids: Array[StringName]) -> Setae:
	var lo: BodyLoadout = player.loadout.copy()
	for id: StringName in ids:
		lo.install(lib.find(id))
	player.apply_loadout(lo)
	await wait_physics_frames(2)
	var part: Setae = player.augments.find(&"sx8_urticating_setae") as Setae
	assert_not_null(part, "installed")
	if part:
		assert_eq(part.offline_reason(), "", "online on the Operator (SA-2: processing 1.2)")
	return part


func _real_wait(seconds: float) -> void:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await wait_physics_frames(1)


func _deploy(part: Setae) -> void:
	player.augments.select(part.slot)
	player.augments.use_selected()
	await _real_wait(part.data.deploy_time + 0.1)


func _target(i: int, at: Vector3) -> Enemy:
	var e: Enemy = room.shooting_range.targets[i]
	e.global_position = at
	e.face(0.0)
	return e


func test_deploy_grows_fibres_slows_time_and_lowers_the_gun() -> void:
	var s: Setae = await _equip([&"sx8_urticating_setae"])
	await _deploy(s)
	assert_eq(s.state, ActivePart.State.ACTIVE)
	assert_eq(s.mode, Setae.Mode.MARKING)
	assert_almost_eq(TimeControl.dilation_scale, s.cfg.world_scale, 0.01, "the world crawls")
	assert_true(player.weapon().stowed, "the left arm is out: the gun goes down")
	await _real_wait(0.9)
	assert_eq(s.hairs_grown(), 48, "two fibres from each of the 24 ports")
	assert_almost_eq(s.window_seconds(), 5.0, 0.01, "5 s of marking at processing 1.2")


func test_four_marks_five_with_sharp_eyes() -> void:
	var s: Setae = await _equip([&"sx8_urticating_setae"])
	var e: Enemy = _target(0, Vector3(0.5, 0.0, -2.0))
	await _deploy(s)
	assert_eq(s.mark_limit(), 4)
	for k: int in 6:
		s.script_mark(e, &"head" if k % 2 == 0 else &"chest")
	assert_eq(s.marks.size(), 4, "never more than the limit; one man can take several")
	s.toggle()
	await _real_wait(1.2)
	var s2: Setae = await _equip([&"ob5_ocular_ballistics"])
	assert_eq(s2.mark_limit(), 5, "OB-5: perception 1.2")


func test_the_throw_takes_the_marked_apart_and_gives_time_back() -> void:
	Settings.gore_level = Gore.Level.MAXIMUM
	var s: Setae = await _equip([&"sx8_urticating_setae"])
	var a: Enemy = _target(0, Vector3(-0.8, 0.0, -2.0))
	var b: Enemy = _target(2, Vector3(1.6, 0.0, -4.0))
	var c: Enemy = _target(1, Vector3(4.0, 0.0, -1.0))
	await wait_physics_frames(3)
	await _deploy(s)
	assert_true(s.script_mark(a, &"head"))
	assert_true(s.script_mark(b, &"chest"))
	s.script_throw()
	await _real_wait(0.3)
	assert_eq(s.throws, 1)
	assert_lt(s.charge, 1.0, "the throw is spent")
	await _real_wait(1.6)
	assert_false(a.alive, "head mark")
	assert_false(b.alive, "chest mark")
	assert_true(c.alive, "not marked, not touched")
	assert_eq(s.cavities, 2, "one cavity per mark")
	assert_true(a.body.severed.has(&"head") or a.body.gibbed, "the head is gone")
	assert_true(b.body.gibbed, "the Operator's throw bursts a torso at Maximum gore")
	assert_almost_eq(TimeControl.dilation_scale, 1.0, 0.01, "time is back")
	assert_eq(s.deadeye, 0.0)
	assert_false(s.is_running(), "folded after the throw")
	assert_eq(s.needles_in_flight(), 0)
	await _real_wait(0.5)
	assert_false(player.weapon().stowed, "the gun comes back up")


func test_lb_folds_without_spending_and_the_window_runs_out() -> void:
	var s: Setae = await _equip([&"sx8_urticating_setae"])
	var e: Enemy = _target(0, Vector3(0.5, 0.0, -2.0))
	await _deploy(s)
	s.script_mark(e)
	s.toggle()
	await _real_wait(0.6)
	assert_false(s.is_running(), "LB folds it")
	assert_eq(s.throws, 0)
	assert_almost_eq(s.charge, 1.0, 0.01, "nothing thrown, nothing spent")
	assert_true(e.alive)
	assert_almost_eq(TimeControl.dilation_scale, 1.0, 0.01)
	await _real_wait(0.6)
	await _deploy(s)
	await _real_wait(s.window_seconds() + 0.6)
	assert_false(s.is_running(), "out of time with nothing marked: it folds")
	assert_eq(s.throws, 0)


func test_stats_drive_the_throw() -> void:
	var s: Setae = await _equip([&"sx8_urticating_setae"])
	assert_almost_eq(s.strength_scale(), 1.0, 0.01, "EM-2: usable strength 1.15 is the reference")
	var cfg: SetaeData = s.cfg
	var light: BodyLoadout = player.loadout.copy()
	light.install(lib.find(&"ft1_fast_twitch"))
	player.apply_loadout(light)
	await wait_physics_frames(2)
	var s2: Setae = player.augments.find(&"sx8_urticating_setae") as Setae
	assert_lt(s2.cavity_energy(), cfg.cavity_energy_j, "a lighter muscle graft throws softer")
	assert_lt(s2.needle_speed(), cfg.needle_speed)


func test_rx9_keeps_its_slowdown_after_the_throw() -> void:
	var s: Setae = await _equip([&"sx8_urticating_setae"])
	var td: TimeDilation = player.augments.find(&"rx9_reflex_overclock") as TimeDilation
	player.augments.select(td.slot)
	player.augments.use_selected()
	await _real_wait(0.6)
	var rx_scale: float = TimeControl.dilation_scale
	assert_lt(rx_scale, 0.9)
	await _deploy(s)
	assert_almost_eq(TimeControl.dilation_scale, s.cfg.world_scale, 0.01)
	s.script_throw()
	await _real_wait(1.4)
	assert_almost_eq(TimeControl.dilation_scale, rx_scale, 0.02, "back to RX-9's time, not to full speed")
