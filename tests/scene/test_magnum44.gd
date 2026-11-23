extends GutTest
## The .44 Magnum (owner, 2026-11-23: "a meaty fucking hand cannon ... really,
## really punchy recoil and a nice smoke effect smoking from the barrel ... I
## want to be blowing people's fucking heads off with this"). A Smith & Wesson
## Model 629: six rounds in a swing-out cylinder, reloaded with a speedloader;
## every shot leaps the gun up out of the grip, and the barrel keeps smoking.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var _gore: int


func before_each() -> void:
	_gore = Settings.gore_level
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("Model 629"))
	await wait_physics_frames(3)


func after_each() -> void:
	weapon.end_script_input()
	Fx.enabled = true
	Settings.gore_level = _gore
	Gore.clear()


func _wait_until(cond: Callable, limit: float) -> float:
	var waited: float = 0.0
	while not cond.call() and waited < limit:
		await wait_physics_frames(1)
		waited += 1.0 / Engine.physics_ticks_per_second
	return waited


func test_a_six_shot_44_magnum_in_the_pistols() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.caliber, ".44 Magnum")
	assert_eq(d.wheel_category, WeaponData.WheelCategory.PISTOLS)
	assert_eq(d.cylinder_chambers, 6)
	assert_eq(weapon.mechanism.loaded(), 6, "six in the cylinder, no +1")
	assert_eq(weapon.live_chambers(), 6)
	assert_true(d.speedloader)
	for part: StringName in [&"cylinder", &"crane", &"speedloader"]:
		assert_true(weapon.rig().has_part(part), "has a %s" % part)
	assert_true(weapon.rig().round_visible(5), "a case head in every chamber")


func test_a_shot_leaps_the_gun_up_turns_the_cylinder_and_smokes() -> void:
	var d: WeaponData = weapon.data
	await wait_physics_frames(20)
	var rest: Vector3 = weapon.rig().transform * d.muzzle_point
	var cyl0: Transform3D = weapon.rig().cylinder_transform()
	weapon.script_input(true, false)
	await wait_physics_frames(2)
	assert_eq(weapon.mechanism.loaded(), 5)
	await wait_seconds(d.vm_flip_rise)
	var up: Vector3 = weapon.rig().transform * d.muzzle_point
	assert_gt(up.y - rest.y, 0.05, "the muzzle leaps up (%.3f m)" % (up.y - rest.y))
	assert_gt(player.shot_fov_punch, 0.5, "the view punches")
	assert_false(weapon.rig().cylinder_transform().basis.is_equal_approx(cyl0.basis), "the cylinder turned a chamber")
	assert_gt(weapon.smoke.live_puffs(), 8, "a cloud out of the muzzle")
	# Hauled back down before the next shot is allowed.
	await wait_seconds(d.fire_interval)
	var back: Vector3 = weapon.rig().transform * d.muzzle_point
	assert_lt(absf(back.y - rest.y), 0.03, "back on target for the next shot (%.3f m off)" % (back.y - rest.y))
	# The barrel still smoking a second later.
	await wait_seconds(1.0)
	assert_gt(weapon.smoke.heat, 0.0, "the barrel is still smoking")
	assert_gt(weapon.smoke.live_puffs(), 4)


func test_speedloader_reload_dumps_all_six_and_puts_six_back() -> void:
	var d: WeaponData = weapon.data
	for i: int in 3:
		weapon.script_input(true, false)
		await wait_physics_frames(2)
		await wait_seconds(d.fire_interval + 0.02)
	assert_eq(weapon.mechanism.loaded(), 3)
	weapon.script_input(false, false, true)
	await wait_physics_frames(2)
	assert_true(weapon.is_reloading())
	await _wait_until(func() -> bool: return weapon.mechanism.reload_progress() > d.mag_out_point + 0.02, 2.0)
	assert_almost_eq(weapon.crane_open(), 1.0, 0.01, "the cylinder is swung out")
	assert_eq(weapon.live_chambers(), 0, "the ejector threw every case, live ones too")
	assert_false(weapon.rig().round_visible(0))
	await _wait_until(func() -> bool: return weapon.rig().speedloader_shown(), 2.0)
	assert_true(weapon.rig().speedloader_shown(), "the speedloader comes in")
	assert_gt(weapon.reload_turn(), 0.5, "muzzle down to load")
	var took: float = await _wait_until(func() -> bool: return not weapon.is_reloading(), 3.0)
	assert_eq(weapon.mechanism.loaded(), 6, "six back in at once")
	assert_eq(weapon.live_chambers(), 6)
	assert_false(weapon.rig().speedloader_shown())
	assert_almost_eq(weapon.crane_open(), 0.0, 0.001, "shut")
	assert_lt(took, 2.2, "a speedloader is quick")


func test_a_head_shot_takes_the_head_apart_and_a_chest_shot_kills() -> void:
	Settings.gore_level = Gore.Level.MAXIMUM
	var d: WeaponData = weapon.data
	var e: Enemy = room.shooting_range.targets[0]
	var head: Vector3 = e.body.hitboxes[&"head"].global_position
	var from: Vector3 = head + Vector3(0, 0.1, 15.0)
	Ballistics.fire(d, from, (head - from).normalized(), player)
	await wait_physics_frames(5)
	assert_true(e.dead)
	assert_true(e.body.is_severed(&"head"), "a .44 to the head at 15 m takes it off")
	var e2: Enemy = room.shooting_range.targets[1]
	var chest: Vector3 = e2.body.hitboxes[&"chest"].global_position
	from = chest + Vector3(0, 0.1, 10.0)
	Ballistics.fire(d, from, (chest - from).normalized(), player)
	await wait_physics_frames(5)
	assert_true(e2.dead, "one to the chest at 10 m")
