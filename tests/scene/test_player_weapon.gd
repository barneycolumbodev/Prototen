extends GutTest
## The gun in the real test room, driven through the same input actions as
## the controller (LT = aim, RT = fire, X = reload, L3 = sprint).

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
	for action: StringName in [&"aim", &"fire", &"reload", &"sprint", &"move_forward"]:
		Input.action_release(action)
	Fx.enabled = true
	Engine.time_scale = 1.0


func _pull() -> void:
	Input.action_press(&"fire")
	await wait_physics_frames(2)
	Input.action_release(&"fire")
	await wait_physics_frames(1)


func test_holding_lt_aims_down_sights_and_releasing_returns() -> void:
	var fov: float = player.camera().fov
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.15)
	assert_eq(weapon.ads, 1.0, "fully aimed while held")
	assert_almost_eq(player.camera().fov, fov * weapon.data.ads_fov_scale, 0.1)
	assert_lt(weapon.spread, 0.05, "aimed spread is the gun's precision")
	assert_lt(player.look_scale, 1.0, "aimed look is slower")
	Input.action_release(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.15)
	assert_eq(weapon.ads, 0.0, "hold, not toggle")


func test_rt_fires_one_round_and_recoil_recovers() -> void:
	var pitch0: float = player.pitch
	var peak: float = 0.0
	Input.action_press(&"fire")
	for i: int in 20:
		await wait_frames(1)
		peak = maxf(peak, weapon.cam_recoil.value.x)
	Input.action_release(&"fire")
	assert_eq(weapon.mechanism.loaded(), 20)
	var expected: float = weapon.data.kick_pitch_deg * (1.0 - weapon.data.kick_permanent)
	assert_between(peak, expected * 0.8, expected * 1.2, "camera kicked up by the tuned amount")
	await wait_seconds(1.0)
	assert_lt(absf(weapon.cam_recoil.value.x), 0.05, "spring recovered")
	var kept: float = rad_to_deg(player.pitch - pitch0)
	assert_between(kept, 0.0, weapon.data.kick_pitch_deg * 0.4, "only a little climb stays (moderate recoil)")


func test_rounds_land_where_the_sights_point() -> void:
	var dummy: TargetDummy = room.shooting_range.dummies[0]
	var head: Vector3 = dummy.parts[&"head"].global_position
	var kinds: Array[StringName] = []
	EventBus.target_hit.connect(func(kind: StringName, _h: BallisticHit) -> void: kinds.append(kind))
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.1)
	GunplayDemo.aim_at(player, head)
	weapon.cam_recoil.reset()
	await _pull()
	await wait_physics_frames(4)
	assert_true(kinds.has(&"kill") or kinds.has(&"headshot"), "aimed shot at the head is a headshot: %s" % [kinds])
	assert_true(dummy.zone_hits.has(&"head"))


func test_x_reloads_and_the_magazine_refills() -> void:
	for i: int in 3:
		await _pull()
		await wait_seconds(weapon.data.fire_interval)
	assert_eq(weapon.mechanism.loaded(), 18)
	Input.action_press(&"reload")
	await wait_physics_frames(2)
	Input.action_release(&"reload")
	assert_true(weapon.is_reloading())
	await wait_seconds(weapon.data.reload_tactical_time + 0.1)
	assert_eq(weapon.mechanism.loaded(), 21, "tactical: 20 + 1")


func test_firing_out_of_a_sprint_drops_the_sprint_then_shoots() -> void:
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_physics_frames(20)
	assert_true(player.is_sprinting())
	await _pull()
	assert_false(player.is_sprinting(), "trigger ends the sprint")
	await wait_seconds(weapon.data.sprint_to_fire + 0.05)
	assert_eq(weapon.mechanism.loaded(), 20, "the buffered shot fired after the sprint-out delay")


func test_aiming_blocks_sprint() -> void:
	Input.action_press(&"aim")
	Input.action_press(&"move_forward", 1.0)
	Input.action_press(&"sprint")
	await wait_physics_frames(10)
	assert_false(player.is_sprinting())
