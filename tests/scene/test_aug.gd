extends GutTest
## The Steyr AUG A1 in the real test room (owner, 2026-11-20: "a really
## awesome AUG model ... super realistic"; an assault rifle between the MP5
## and the M14/P). 5.56×45 at 680 rpm, 30+1; the progressive trigger (a light
## pull fires single rounds, a full pull automatic); aiming always goes
## through the integral 1.5× scope (HUD ring reticle, the viewmodel steps
## aside); the clear magazine shows the rounds left and its follower rides up.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("AUG A1"))
	await wait_physics_frames(3)


func after_each() -> void:
	for action: StringName in [&"aim", &"fire", &"reload"]:
		Input.action_release(action)
	Fx.enabled = true


func _press(action: StringName) -> void:
	Input.action_press(action)
	await wait_physics_frames(2)
	Input.action_release(action)


func test_it_is_a_5_56_bullpup_with_a_scope_and_a_clear_magazine() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.display_name, "AUG A1")
	assert_eq(d.weapon_class, WeaponData.WeaponClass.RIFLE)
	assert_true(d.automatic, "automatic")
	assert_true(d.progressive_trigger, "two-stage trigger")
	assert_eq(weapon.mechanism.loaded(), 31, "30 + 1")
	assert_between(d.muzzle_energy(), 1500.0, 2000.0, "5.56×45, %.0f J" % d.muzzle_energy())
	assert_between(60.0 / d.fire_interval, 650.0, 750.0, "about 680 rpm")
	assert_true(d.integral_optic, "the 1.5x scope is part of the gun")
	assert_almost_eq(d.optic_fov_scale, 1.0 / 1.5, 0.01, "1.5x")
	for part: StringName in [&"magazine", &"charging_handle", &"mag_rounds", &"mag_follower"]:
		assert_true(weapon.rig().has_part(part), "has a %s" % part)
	# Between the MP5 and the M14/P: more energy than the 9 mm, less than the 7.62.
	var mp5: WeaponData = load("res://data/weapons/mp5.tres") as WeaponData
	var m14: WeaponData = load("res://data/weapons/m14p.tres") as WeaponData
	assert_between(d.muzzle_energy(), mp5.muzzle_energy(), m14.muzzle_energy())


func test_a_full_pull_fires_automatic() -> void:
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	Input.action_press(&"fire", 1.0)
	await wait_seconds(0.6)
	Input.action_release(&"fire")
	assert_between(shots[0], 6, 9, "about 7 rounds in 0.6 s (%d)" % shots[0])


func test_a_light_pull_fires_one_round() -> void:
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	Input.action_press(&"fire", 0.55)
	await wait_seconds(0.6)
	Input.action_release(&"fire")
	assert_eq(shots[0], 1, "first stage: semi-automatic")
	# Squeezing on through the second stage goes automatic.
	await wait_physics_frames(3)
	Input.action_press(&"fire", 0.55)
	await wait_physics_frames(3)
	Input.action_press(&"fire", 1.0)
	await wait_seconds(0.5)
	Input.action_release(&"fire")
	assert_gt(shots[0], 4, "second stage: automatic (%d)" % shots[0])


func test_aiming_looks_through_the_scope() -> void:
	var base_fov: float = player.camera().fov
	Input.action_press(&"aim")
	await wait_seconds(0.7)
	assert_almost_eq(weapon.scope_amount(), 1.0, 0.02, "all the way into the scope")
	assert_true(weapon.optic_on())
	assert_true(weapon.rig().is_scoped(), "the viewmodel steps aside for the scope view")
	assert_lt(player.camera().fov, base_fov * 0.72, "1.5x zoom (%.1f° from %.1f°)" % [player.camera().fov, base_fov])
	Input.action_release(&"aim")
	await wait_seconds(0.5)
	assert_false(weapon.rig().is_scoped(), "back at the hip")


func test_the_clear_magazine_shows_the_rounds_left() -> void:
	await wait_frames(2)
	var rig: ViewmodelRig = weapon.rig()
	assert_eq(rig.mag_rounds_shown(), 30, "full magazine")
	var rest: Transform3D = rig.follower_transform()
	for i: int in 5:
		await _press(&"fire")
		await wait_seconds(0.12)
	await wait_frames(2)
	assert_eq(weapon.mechanism.magazine, 25)
	assert_eq(rig.mag_rounds_shown(), 25, "five rounds gone from the stack")
	var moved: Transform3D = rig.follower_transform()
	assert_gt(moved.origin.distance_to(rest.origin) + absf(moved.basis.get_euler().z - rest.basis.get_euler().z), 0.0001,
			"the follower rode up")
	# Up the magazine (+Y): the follower turns toward the top.
	var p_rest: Vector3 = rest * Vector3(-0.17, -0.22, 0.0)
	var p_moved: Vector3 = moved * Vector3(-0.17, -0.22, 0.0)
	assert_gt(p_moved.y, p_rest.y, "follower moved up the magazine")
	await _press(&"reload")
	await wait_seconds(weapon.data.reload_tactical_time + 0.3)
	assert_eq(rig.mag_rounds_shown(), 30, "a full magazine after the reload")


func test_empty_reload_works_the_cocking_handle() -> void:
	weapon.mechanism.magazine = 0
	await _press(&"fire")
	await wait_physics_frames(6)
	assert_eq(weapon.mechanism.loaded(), 0)
	await wait_frames(2)
	assert_gt(weapon.rig().charging_handle_back(), 0.05, "handle back")
	await _press(&"reload")
	await wait_seconds(weapon.data.reload_empty_time + 0.3)
	assert_eq(weapon.mechanism.loaded(), 31, "loaded and chambered")
	assert_almost_eq(weapon.rig().charging_handle_back(), 0.0, 0.001, "handle home")
