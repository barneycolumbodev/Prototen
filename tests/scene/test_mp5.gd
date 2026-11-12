extends GutTest
## The MP5 in the real test room (owner, 2026-11-12: "a very detailed mp5,
## with a red dot sight, suppressor, under barrel green laser. It must have
## great hipfire spread ... high mobility run and gun, contained hipfire,
## which is accurate to the green laser, even while moving, jumping, or walk
## running"). Full-auto suppressed 9×19, 30+1; the laser dot sits on the aim
## line every round leaves along; the hip cone stays tight moving, in the air
## and sprinting; the trigger doesn't end a sprint; the cocking handle stays
## back on an empty gun until the reload slaps it home.

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
	weapon.select_now(weapon.index_of("MP5/SD-L"))
	await wait_physics_frames(3)


func after_each() -> void:
	for action: StringName in [&"aim", &"fire", &"reload", &"move_forward", &"move_right", &"sprint", &"jump"]:
		Input.action_release(action)
	Fx.enabled = true


func _press(action: StringName) -> void:
	Input.action_press(action)
	await wait_physics_frames(2)
	Input.action_release(action)


## Looks at the floor a few metres ahead (the laser needs a surface).
func _look_down(deg: float = 22.0) -> void:
	player.set_view(player.yaw, deg_to_rad(-deg))
	await wait_frames(3)


func test_it_is_a_suppressed_full_auto_9mm_with_a_laser_and_red_dot() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.display_name, "MP5/SD-L")
	assert_true(d.automatic, "full auto")
	assert_eq(weapon.mechanism.loaded(), 31, "30 + 1")
	assert_between(d.muzzle_energy(), 450.0, 800.0, "9×19, %.0f J" % d.muzzle_energy())
	assert_between(60.0 / d.fire_interval, 700.0, 900.0, "about 800 rpm")
	assert_lt(d.flash_scale, 0.3, "suppressed: small flash")
	assert_gt(d.laser_range, 50.0, "has a laser")
	for part: StringName in [&"slide", &"magazine", &"stock", &"charging_handle", &"lens", &"reticle", &"laser"]:
		assert_true(weapon.rig().has_part(part), "has a %s" % part)


func test_holding_rt_fires_full_auto() -> void:
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	Input.action_press(&"fire")
	await wait_seconds(0.6)
	Input.action_release(&"fire")
	assert_between(shots[0], 6, 10, "about 8 rounds in 0.6 s (%d)" % shots[0])


func test_no_weight_penalty() -> void:
	var d: WeaponData = weapon.data
	for v: float in [d.carry_speed_scale, d.carry_sprint_scale, d.carry_jump_scale, d.carry_turn_scale]:
		assert_eq(v, 1.0, "carries like nothing")
	assert_lt(d.draw_time, 0.4, "fast draw")
	assert_lt(d.ads_time, 0.2, "fast to the sights")
	assert_gt(d.ads_move_speed, 0.8, "moves fast aimed")


func test_hip_cone_on_the_move_beats_every_other_gun() -> void:
	# Walking (full stick) and in the air, after a long burst: the MP5's hip cone
	# against every other gun's, same state, no bloom for them.
	var mp5: WeaponData = weapon.data
	var worst: float = mp5.spread_deg(0.0, 1.0, true, mp5.bloom_max_deg)
	assert_lt(worst, 1.6, "MP5 hip cone moving, airborne, full bloom: %.2f°" % worst)
	var moving: float = mp5.spread_deg(0.0, 1.0, false, 0.0)
	var jumping: float = mp5.spread_deg(0.0, 1.0, true, 0.0)
	assert_lt(moving - mp5.spread_deg(0.0, 0.0, false, 0.0), 0.3, "moving barely widens it")
	for s: PlayerWeapon.Slot in weapon.slots:
		if s.data == mp5:
			continue
		var other: WeaponData = s.round_for(0)
		assert_lt(moving, other.spread_deg(0.0, 1.0, false, 0.0), "tighter than %s walking" % other.display_name)
		assert_lt(jumping, other.spread_deg(0.0, 1.0, true, 0.0), "tighter than %s in the air" % other.display_name)


func test_laser_dot_is_on_the_aim_line() -> void:
	await _look_down()
	await wait_frames(2)
	var laser: WeaponLaser = weapon.laser
	assert_true(laser.on_surface, "dot on the floor")
	assert_true(laser.dot_visible(), "dot drawn")
	assert_true(laser.beam_visible(), "beam drawn")
	var eye: Vector3 = player.camera().global_position
	var to_dot: Vector3 = (laser.hit_point - eye).normalized()
	var off: float = rad_to_deg(to_dot.angle_to(weapon.aim_forward()))
	assert_lt(off, 0.05, "dot on the aim line (%.3f° off)" % off)


func test_rounds_land_on_the_dot_while_running_and_jumping() -> void:
	await _look_down()
	# Each shot: angle between the round's direction and the aim line the laser draws.
	var worst: Array[float] = [0.0]
	var shots: Array[int] = [0]
	var cb: Callable = func(shooter: Node, _origin: Vector3, dir: Vector3) -> void:
		if shooter == player:
			shots[0] += 1
			worst[0] = maxf(worst[0], rad_to_deg(dir.angle_to(weapon.aim_forward())))
	EventBus.shot_fired.connect(cb)
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"move_right", 0.6)
	await wait_physics_frames(20)
	Input.action_press(&"fire")
	Input.action_press(&"jump")
	await wait_physics_frames(3)
	Input.action_release(&"jump")
	var airborne: bool = false
	var air_spread: float = 0.0
	for i: int in 30:
		await wait_physics_frames(1)
		if not player.is_on_floor():
			airborne = true
			air_spread = maxf(air_spread, weapon.spread)
	Input.action_release(&"fire")
	EventBus.shot_fired.disconnect(cb)
	assert_true(airborne, "jumped mid-burst")
	assert_gt(shots[0], 5, "kept firing on the move (%d)" % shots[0])
	gut.p("MP5 jumping burst: %d rounds, hip cone %.2f°, worst %.2f° off the laser line" % [shots[0], air_spread, worst[0]])
	assert_lt(air_spread, 1.6, "hip cone in the air, moving, firing: %.2f°" % air_spread)
	# Every round inside the cone around the laser line (half the full-width cone, plus rounding).
	assert_lt(worst[0], weapon.data.spread_deg(0.0, 1.0, true, weapon.data.bloom_max_deg) * 0.5 + 0.01,
			"every round within the cone round the dot (worst %.2f°)" % worst[0])


func test_the_trigger_does_not_end_a_sprint() -> void:
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_physics_frames(3)
	Input.action_release(&"sprint")
	await wait_physics_frames(20)
	assert_true(player.is_sprinting(), "sprinting before the trigger")
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	Input.action_press(&"fire")
	await wait_seconds(0.4)
	assert_true(player.is_sprinting(), "still sprinting while firing")
	assert_gt(shots[0], 3, "fired on the run (%d)" % shots[0])
	assert_true(weapon.firing_on_the_run())
	var speed: float = Vector2(player.velocity.x, player.velocity.z).length()
	assert_gt(speed, player.movement.walk_speed * player.speed_factor() + 1.0, "at sprint speed (%.1f m/s)" % speed)
	Input.action_release(&"fire")


func test_other_guns_still_drop_the_sprint() -> void:
	weapon.select_now(weapon.index_of("M14/P"))
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_physics_frames(3)
	Input.action_release(&"sprint")
	await wait_physics_frames(20)
	assert_true(player.is_sprinting())
	await _press(&"fire")
	await wait_physics_frames(2)
	assert_false(player.is_sprinting(), "a battle rifle ends the sprint")


func test_hip_reticle_gives_way_to_the_dot() -> void:
	await _look_down()
	await wait_frames(3)
	assert_true(weapon.laser_on())
	weapon.select_now(weapon.index_of("M14/P"))
	await wait_frames(3)
	assert_false(weapon.laser_on(), "no laser on the M14/P")
	assert_false(weapon.laser.dot_visible())


func test_laser_goes_off_while_switching() -> void:
	await _look_down()
	await wait_frames(2)
	assert_true(weapon.laser.dot_visible())
	weapon.request_switch(weapon.index_of("M14/P"))
	await wait_frames(2)
	assert_false(weapon.laser.dot_visible(), "laser off as the gun goes down")


func test_empty_gun_holds_the_cocking_handle_back_until_the_slap() -> void:
	weapon.mechanism.magazine = 0
	await _press(&"fire")
	await wait_physics_frames(6)
	assert_eq(weapon.mechanism.loaded(), 0)
	await wait_frames(2)
	assert_gt(weapon.rig().charging_handle_back(), 0.08, "handle back in its notch")
	await _press(&"reload")
	await wait_seconds(weapon.data.reload_empty_time + 0.25)
	assert_eq(weapon.mechanism.loaded(), 30, "a full magazine; the slap chambers one from it")
	assert_lt(weapon.rig().charging_handle_back(), 0.001, "handle slapped home")


func test_stock_hides_and_the_dot_still_shows_aimed() -> void:
	await _look_down()
	var stock: Node3D = weapon.rig().find_child("stock", true, false) as Node3D
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.25)
	assert_false(stock.visible, "stock out of the way of the red dot")
	assert_true(weapon.laser.dot_visible(), "laser still on, aimed")
	Input.action_release(&"aim")


func test_a_burst_strafing_and_jumping_groups_tight_on_a_far_wall() -> void:
	# Hold the dot on one spot of the back wall while strafing and jumping:
	# where do the rounds land around it?
	var spot: Vector3 = Vector3(player.global_position.x, 1.4, -16.0)
	var impacts: Array[Vector3] = []
	var cb: Callable = func(h: BallisticHit) -> void:
		if h.shooter == player and h.prior_penetrations == 0 and absf(h.point.z + 16.0) < 0.05:
			impacts.append(h.point)
	EventBus.ballistic_hit.connect(cb)
	Input.action_press(&"move_right", 1.0)
	await wait_physics_frames(10)
	for i: int in 50:
		if i == 6:
			Input.action_press(&"jump")
		if i == 9:
			Input.action_release(&"jump")
		GunplayDemo.aim_at(player, spot)
		weapon.script_input(true, false)
		await wait_physics_frames(1)
	weapon.end_script_input()
	Input.action_release(&"move_right")
	await wait_physics_frames(10)
	EventBus.ballistic_hit.disconnect(cb)
	assert_gt(impacts.size(), 10, "a real burst on the wall (%d)" % impacts.size())
	var dist: float = player.camera().global_position.distance_to(spot)
	var worst: float = 0.0
	for p: Vector3 in impacts:
		worst = maxf(worst, Vector2(p.x - spot.x, p.y - spot.y).length())
	var cone: float = weapon.data.spread_deg(0.0, 1.0, true, weapon.data.bloom_max_deg)
	var allowed: float = dist * tan(deg_to_rad(cone * 0.5)) + dist * tan(deg_to_rad(0.6))
	gut.p("MP5 group: %d rounds, worst %.2f m from the dot at %.1f m (cone %.2f°)" % [impacts.size(), worst, dist, cone])
	assert_lt(worst, allowed, "every round within %.2f m of the dot at %.0f m (worst %.2f m)" % [allowed, dist, worst])
	assert_lt(worst, 0.6, "a fist-to-torso-sized group at %.0f m on the move (worst %.2f m)" % [dist, worst])


func test_drops_a_man_in_a_few_rounds_on_the_run() -> void:
	# Strafing past a gunman ten metres off, dot on his chest from the hip.
	var d: Enemy = room.shooting_range.targets[0]
	player.global_position = d.global_position + Vector3(-3.0, 0.0, 9.5)
	await wait_physics_frames(3)
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	Input.action_press(&"move_right", 1.0)
	for i: int in 60:
		if d.health <= 0.0:
			break
		GunplayDemo.aim_at(player, d.parts[&"chest"].global_position)
		weapon.script_input(true, false)
		await wait_physics_frames(1)
	weapon.end_script_input()
	Input.action_release(&"move_right")
	gut.p("MP5 on the run: gunman down in %d rounds" % shots[0])
	assert_true(d.health <= 0.0, "he's down")
	assert_lt(shots[0], 7, "in %d rounds" % shots[0])
