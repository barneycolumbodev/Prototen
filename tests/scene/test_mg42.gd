extends GutTest
## The MG42 in the real test room, driven through the controller actions:
## Y switches to it, it slows you down, hip fire is loose, aimed fire is tight,
## holding RT shreds at 1,200 rpm with tracers, and the belt reload works.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	weapon = player.weapon()
	await wait_physics_frames(int(weapon.data.draw_time * 60.0) + 10)


func after_each() -> void:
	for action: StringName in [&"aim", &"fire", &"reload", &"switch_weapon", &"move_forward", &"sprint"]:
		Input.action_release(action)
	Fx.enabled = true
	Engine.time_scale = 1.0


func _switch_to_mg() -> void:
	Input.action_press(&"switch_weapon")
	await wait_physics_frames(2)
	Input.action_release(&"switch_weapon")
	var mg: WeaponData = weapon.loadout[1]
	await wait_seconds(weapon.loadout[0].holster_time + mg.draw_time + 0.2)


func test_y_switches_to_the_mg42_and_back() -> void:
	assert_eq(weapon.data.display_name, "Five-seveN SR")
	await _switch_to_mg()
	assert_eq(weapon.data.display_name, "MG42/A")
	assert_eq(weapon.mechanism.state, GunMechanism.State.READY, "drawn and ready")
	assert_true(weapon.rig().visible)
	assert_false(weapon.slots[0].rig.visible, "pistol put away")
	assert_eq(weapon.mechanism.loaded(), 150)
	Input.action_press(&"switch_weapon")
	await wait_physics_frames(2)
	Input.action_release(&"switch_weapon")
	await wait_seconds(weapon.loadout[1].holster_time + weapon.loadout[0].draw_time + 0.2)
	assert_eq(weapon.data.display_name, "Five-seveN SR")


func test_mg42_slows_you_down() -> void:
	Input.action_press(&"move_forward")
	await wait_seconds(0.8)
	var pistol_speed: float = Vector2(player.velocity.x, player.velocity.z).length()
	Input.action_release(&"move_forward")
	await _switch_to_mg()
	Input.action_press(&"move_forward")
	await wait_seconds(0.8)
	var mg_speed: float = Vector2(player.velocity.x, player.velocity.z).length()
	assert_almost_eq(mg_speed / pistol_speed, weapon.data.carry_speed_scale, 0.03,
			"walk speed scaled by the carry penalty (%.2f vs %.2f m/s)" % [mg_speed, pistol_speed])
	assert_lt(player.sprint_scale, 1.0)
	assert_lt(player.jump_scale, 1.0)


func test_hip_fire_is_loose_and_aimed_fire_is_tight() -> void:
	var pistol_hip: float = weapon.spread
	await _switch_to_mg()
	assert_gt(weapon.spread, pistol_hip * 3.0, "MG42 hip cone %.2f° vs pistol %.2f°" % [weapon.spread, pistol_hip])
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.2)
	assert_lt(weapon.spread, 0.1, "aimed: the gun's own precision")
	Input.action_release(&"aim")


func test_holding_rt_shreds_with_tracers() -> void:
	await _switch_to_mg()
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	var tracers_seen: int = 0
	var spread_start: float = weapon.spread
	Input.action_press(&"fire")
	for i: int in 60:
		await get_tree().physics_frame
		tracers_seen = maxi(tracers_seen, Ballistics.tracer_count())
	var spread_end: float = weapon.spread
	Input.action_release(&"fire")
	assert_between(shots[0], 19, 21, "about 20 rounds in one second (%d)" % shots[0])
	assert_eq(weapon.mechanism.loaded(), 150 - shots[0])
	assert_gt(tracers_seen, 0, "tracers are visible")
	assert_gt(spread_end, spread_start, "sustained hip fire walks the gun around")


func test_belt_reload_opens_cover_and_drops_the_box() -> void:
	await _switch_to_mg()
	Input.action_press(&"fire")
	await wait_seconds(0.5)
	Input.action_release(&"fire")
	Input.action_press(&"reload")
	await wait_physics_frames(2)
	Input.action_release(&"reload")
	assert_true(weapon.is_reloading())
	var mg: ViewmodelRig = weapon.rig()
	var cover: Node3D = mg.find_child("cover", true, false) as Node3D
	var box: Node3D = mg.find_child("magazine", true, false) as Node3D
	var cover_rest: Basis = cover.transform.basis
	var max_cover: float = 0.0
	var max_drop: float = 0.0
	var box_rest: float = box.position.y
	var t: float = 0.0
	while weapon.is_reloading() and t < 6.0:
		await get_tree().physics_frame
		t += 1.0 / 60.0
		max_cover = maxf(max_cover, rad_to_deg(cover.transform.basis.get_euler().z - cover_rest.get_euler().z))
		max_drop = maxf(max_drop, box_rest - box.position.y)
	assert_gt(max_cover, 40.0, "feed cover swings open (%.0f°)" % max_cover)
	assert_gt(max_drop, 0.1, "ammo box comes off")
	assert_eq(weapon.mechanism.loaded(), 150)
	assert_almost_eq(cover.transform.basis.get_euler().z, cover_rest.get_euler().z, 0.01, "cover closed again")
