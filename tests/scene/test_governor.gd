extends GutTest
## The Governor (docs/design.md §4.9): a .45-70 lever action. Seven rounds
## (six in the tube, one chambered); after each shot the lever is thrown and
## the bolt runs, the hammer is cocked, the case flies at the bottom of the
## stroke; loads a round at a time through the gate; men it hits are thrown.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var _gore: int


func before_each() -> void:
	Fx.enabled = false
	_gore = Settings.gore_level
	Settings.gore_level = Gore.Level.MAXIMUM
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("The Governor"))
	await wait_physics_frames(3)


func after_each() -> void:
	weapon.end_script_input()
	Settings.gore_level = _gore
	Gore.clear()
	Fx.enabled = true


func _target(i: int = 0) -> Enemy:
	return room.shooting_range.targets[i]


func test_it_is_a_seven_round_lever_action() -> void:
	var d: WeaponData = weapon.data
	assert_true(d.lever_action, "a lever action")
	assert_true(d.loads_singly(), "loads through the gate a round at a time")
	assert_eq(weapon.mechanism.loaded(), 7, "6 in the tube + 1")
	for part: StringName in [&"lever", &"bolt", &"hammer", &"load_round", &"stock"]:
		assert_true(weapon.rig().has_part(part), "has a %s" % part)
	assert_gte(d.fire_interval, d.lever_delay + d.lever_time, "the lever has time to cycle before the next shot")


func test_a_shot_throws_the_lever_and_cocks_the_hammer() -> void:
	var rest: Transform3D = weapon.rig().lever_transform()
	weapon.script_input(true, false)
	await wait_physics_frames(2)
	assert_eq(weapon.mechanism.loaded(), 6, "fired one")
	assert_true(weapon.hammer_down, "hammer fell")
	await wait_seconds(weapon.data.lever_delay + weapon.data.lever_time * 0.4)
	var open: Transform3D = weapon.rig().lever_transform()
	assert_gt(open.origin.distance_to(rest.origin) + (open.basis.x - rest.basis.x).length(), 0.05, "lever thrown down")
	assert_false(weapon.hammer_down, "the stroke cocked the hammer")
	await wait_seconds(weapon.data.lever_time)
	assert_lt(weapon.lever_t, 0.0, "lever home")
	assert_almost_eq((weapon.rig().lever_transform().basis.x - rest.basis.x).length(), 0.0, 0.01, "back where it started")


func test_reload_loads_round_by_round_to_seven() -> void:
	for i: int in 3:
		weapon.script_input(true, false)
		await wait_seconds(weapon.data.fire_interval + 0.05)
	assert_eq(weapon.mechanism.loaded(), 4)
	weapon.script_input(false, false, true)
	await wait_physics_frames(2)
	assert_true(weapon.is_reloading())
	await wait_seconds(weapon.data.reload_open_time + weapon.data.round_load_time * 1.5)
	assert_eq(weapon.mechanism.loaded(), 5, "one round in so far")
	await wait_seconds(weapon.data.round_load_time * 3.0)
	assert_eq(weapon.mechanism.loaded(), 7, "full")


func test_a_chest_hit_kills_and_throws_him() -> void:
	var e: Enemy = _target()
	var at: Vector3 = e.body.hitboxes[&"chest"].global_position
	var from: Vector3 = Vector3(0, 1.6, 9.0)
	Ballistics.fire(weapon.data, from, (at - from).normalized(), player)
	await wait_physics_frames(6)
	assert_false(e.alive, "one .45-70 to the chest kills")
	assert_gt(weapon.data.ragdoll_push, 1.5, "and throws him harder than a rifle")


func test_a_leg_hit_takes_the_leg_off_at_maximum_gore() -> void:
	var e: Enemy = _target()
	var at: Vector3 = e.body.hitboxes[&"l_thigh"].global_position
	var from: Vector3 = Vector3(0, 1.0, 9.0)
	Ballistics.fire(weapon.data, from, (at - from).normalized(), player)
	await wait_physics_frames(6)
	assert_true(e.body.severed.has(&"thigh_L") or e.body.severed.has(&"shin_L"), "the leg comes off")
