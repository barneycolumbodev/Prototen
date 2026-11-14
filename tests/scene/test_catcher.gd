extends GutTest
## LC-6 Lorentz Catcher (docs/design.md §3.4d, owner 2026-11-13): hold LB
## and enemy rounds from the front are caught in the air; let go and the
## same rounds go back out over an area at the aim point. It throws exactly
## what it caught.

var room: TestRoom
var player: Player
var lib: PartLibrary = preload("res://data/body/part_library.tres")


func before_each() -> void:
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
	TimeControl.set_dilation(1.0, 1.0)
	Ballistics.clear()


func _equip(ids: Array[StringName]) -> LorentzCatcher:
	var lo: BodyLoadout = player.loadout.copy()
	for id: StringName in ids:
		lo.install(lib.find(id))
	player.apply_loadout(lo)
	await wait_physics_frames(2)
	return player.augments.find(&"lc6_lorentz_catcher") as LorentzCatcher


func _real_wait(seconds: float) -> void:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await wait_physics_frames(1)


## LB down and held (scripted), until the field is up.
func _hold(part: LorentzCatcher) -> void:
	part.script_hold(true)
	player.augments.select(part.slot)
	player.augments.use_selected()
	await _real_wait(part.data.deploy_time + 0.1)


func _target(i: int, at: Vector3) -> Enemy:
	var e: Enemy = room.shooting_range.targets[i]
	e.global_position = at
	e.face(0.0)
	return e


## `n` rounds of the gunman's rifle from `from` at the operative's eye.
func _fire_at_player(shooter: Enemy, from: Vector3, n: int) -> void:
	var eye: Vector3 = player.camera().global_position
	for k: int in n:
		var at: Vector3 = eye + Vector3(randf_range(-0.25, 0.25), randf_range(-0.6, 0.1), 0.0)
		Ballistics.fire(_rifle(), from, (at - from).normalized(), shooter)
	await wait_physics_frames(3)


func _rifle() -> WeaponData:
	return load("res://data/enemies/weapons/type56.tres") as WeaponData


func test_installs_online_on_the_operator_and_takes_the_left_arm() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	assert_not_null(c, "installed")
	assert_eq(c.offline_reason(), "", "HS-5: 640 W of cooling meets the 500 W requirement")
	assert_eq(c.capacity(), 40, "40 rounds at the base 450 W supply")
	var lo: BodyLoadout = player.loadout.copy()
	lo.install(lib.find(&"bw6_fan_shield"))
	assert_false(lo.has_part(&"lc6_lorentz_catcher"), "the shield is the left forearm too")
	var cool: BodyLoadout = player.loadout.copy()
	cool.remove(&"hs5_heat_sinks")
	player.apply_loadout(cool)
	await wait_physics_frames(2)
	var c2: LorentzCatcher = player.augments.find(&"lc6_lorentz_catcher") as LorentzCatcher
	assert_ne(c2.offline_reason(), "", "no heat sinks: 380 W isn't enough, it stays offline")


func test_holding_lb_catches_rounds_from_the_front() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	var shooter: Enemy = _target(0, Vector3(0.5, 0.0, -6.0))
	player.invulnerable = false
	var hp: float = player.health
	await _hold(c)
	assert_eq(c.state, ActivePart.State.ACTIVE)
	assert_eq(c.mode, LorentzCatcher.Mode.CATCHING)
	assert_true(player.weapon().stowed, "the left hand is out: the gun goes down")
	var before: int = Ballistics.rounds_caught
	await _fire_at_player(shooter, shooter.global_position + Vector3(0.0, 1.4, 0.0), 12)
	assert_eq(c.held.size(), 12, "every round from the front is held")
	assert_eq(Ballistics.rounds_caught - before, 12)
	assert_eq(player.health, hp, "none reached the body")
	var heat0: float = player.body.heat_j
	assert_gt(heat0, 0.0, "braking them heated the body")


func test_rounds_from_behind_get_through() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	var shooter: Enemy = _target(0, Vector3(0.5, 0.0, -6.0))
	await _hold(c)
	var eye: Vector3 = player.camera().global_position
	var from: Vector3 = eye + Vector3(0.0, 0.0, 8.0)
	for k: int in 4:
		Ballistics.fire(_rifle(), from, (eye + Vector3(0.0, -0.4, 0.0) - from).normalized(), shooter)
	await wait_physics_frames(3)
	assert_eq(c.held.size(), 0, "the field only faces forward")


func test_it_holds_only_so_many() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	var shooter: Enemy = _target(0, Vector3(0.5, 0.0, -6.0))
	player.body.heat_j = 0.0
	await _hold(c)
	await _fire_at_player(shooter, shooter.global_position + Vector3(0.0, 1.4, 0.0), 30)
	player.body.heat_j = 0.0
	await _fire_at_player(shooter, shooter.global_position + Vector3(0.0, 1.4, 0.0), 20)
	assert_eq(c.held.size(), c.capacity(), "full at 40")
	assert_eq(c.refused, 10, "the rest fly on")


func test_letting_go_throws_back_exactly_what_it_caught() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	var shooter: Enemy = _target(0, Vector3(-3.0, 0.0, -4.0))
	var victim: Enemy = _target(2, Vector3(0.5, 0.0, -8.0))
	player.set_view(0.0, deg_to_rad(-3.0))
	await wait_physics_frames(3)
	await _hold(c)
	await _fire_at_player(shooter, shooter.global_position + Vector3(0.0, 1.4, 0.0), 18)
	assert_eq(c.held.size(), 18)
	var thrown0: int = c.thrown_total
	var fired0: int = Ballistics.rounds_fired
	c.script_hold(false)
	await _real_wait(0.1)
	assert_eq(c.mode, LorentzCatcher.Mode.RELEASING, "let go: it throws")
	assert_eq(c.release_reason, &"button")
	await _real_wait(0.6)
	assert_eq(c.thrown_total - thrown0, 18, "every caught round goes back out")
	assert_eq(Ballistics.rounds_fired - fired0, 18, "and not one more")
	assert_eq(c.last_volley, 18)
	assert_almost_eq(c.last_aim.z, victim.global_position.z, 1.5, "the area is where the crosshair is (on the man down range)")
	assert_gt(c.last_radius, 1.0, "a wide area")
	assert_false(victim.alive, "18 rifle rounds into the area put the man in it down")
	await _real_wait(0.8)
	assert_false(c.is_running(), "folded after the throw")
	assert_eq(c.held.size(), 0)
	assert_false(player.weapon().stowed, "the gun comes back up")


func test_a_tap_with_nothing_caught_just_folds() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	var fired0: int = Ballistics.rounds_fired
	await _hold(c)
	c.script_hold(false)
	await _real_wait(0.5)
	assert_false(c.is_running())
	assert_eq(c.last_volley, 0)
	assert_eq(Ballistics.rounds_fired, fired0, "nothing caught, nothing thrown")


func test_out_of_time_or_too_hot_it_lets_go() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher"])
	var shooter: Enemy = _target(0, Vector3(0.5, 0.0, -6.0))
	await _hold(c)
	await _fire_at_player(shooter, shooter.global_position + Vector3(0.0, 1.4, 0.0), 5)
	c.charge = 0.05
	await _real_wait(0.2)
	assert_eq(c.release_reason, &"time", "the hold time ran out: it throws")
	assert_eq(c.last_volley, 5)
	await _real_wait(1.2)
	c.charge = c.charge_capacity()
	await _hold(c)
	player.body.heat_j = player.body.frame.heat_capacity_j - 300.0
	await _fire_at_player(shooter, shooter.global_position + Vector3(0.0, 1.4, 0.0), 3)
	assert_eq(c.release_reason, &"heat", "the coils overheated: it lets go of everything")
	assert_eq(c.mode, LorentzCatcher.Mode.RELEASING)


func test_stats_drive_it() -> void:
	var c: LorentzCatcher = await _equip([&"lc6_lorentz_catcher", &"pc3_power_cell", &"ob5_ocular_ballistics"])
	assert_eq(c.capacity(), 58, "PC-3: 650 W holds 58")
	assert_gt(c.seek_share(), 0.3 * 1.15, "sharper perception sends more onto bodies")
