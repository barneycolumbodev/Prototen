extends GutTest
## The RC-6 rail carbine in the real test room: every shot
## leaves an ionized trail and no casing, slugs go through AR500 and through
## a dummy, one torso hit kills, spamming RT overheats the rails and the vent
## shroud lifts, and the top magazine comes off back and up.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var rail: WeaponData


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	weapon = player.weapon()
	rail = (load("res://data/weapons/rail_carbine.tres") as WeaponData).duplicate() as WeaponData
	await wait_physics_frames(int(weapon.data.draw_time * 60.0) + 10)


func after_each() -> void:
	for action: StringName in [&"aim", &"fire", &"reload", &"switch_weapon"]:
		Input.action_release(action)
	Fx.enabled = true
	Engine.time_scale = 1.0


func _press(action: StringName) -> void:
	Input.action_press(action)
	await wait_physics_frames(2)
	Input.action_release(action)


func _to_rail() -> void:
	var i: int = weapon.index_of("RC-6 Lance")
	assert_gt(i, 0, "the rail carbine is in the loadout")
	weapon.select_now(i)
	await wait_physics_frames(3)


func test_shot_leaves_a_trail_and_no_casing() -> void:
	await _to_rail()
	assert_true(weapon.rig().visible)
	assert_eq(weapon.mechanism.loaded(), 40)
	GunplayDemo.aim_at(player, room.shooting_range.targets[0].parts[&"chest"].global_position)
	await wait_physics_frames(2)
	var shells: int = Fx.live_shells()
	await _press(&"fire")
	assert_eq(weapon.mechanism.loaded(), 39)
	assert_gt(Ballistics.trail_count(), 0, "ionized trail drawn")
	await wait_physics_frames(3)
	assert_gt(Ballistics.newest_trail_length(), 5.0, "the trail follows the slug down range")
	assert_eq(Fx.live_shells(), shells, "no case ejected")
	assert_lt(weapon.mechanism.charge(), 0.5, "capacitor recharging")
	await wait_seconds(rail.charge_time + 0.1)
	assert_eq(weapon.mechanism.charge(), 1.0, "capacitor full again")
	await wait_seconds(rail.beam_trail_time + 0.2)
	assert_eq(Ballistics.trail_count(), 0, "trail faded")


func test_slug_goes_through_ar500_that_stops_the_pistol() -> void:
	var steel: PenPanel = room.shooting_range.panels[5]
	var face: Vector3 = steel.global_position + Vector3(0, 0.9, 0.0)
	Ballistics.fire(rail, face + Vector3(0, 0.1, 2.0), (face - (face + Vector3(0, 0.1, 2.0))).normalized(), player)
	await wait_physics_frames(6)
	assert_eq(steel.hits, 1)
	assert_eq(steel.through, 1, "AR500 doesn't stop a 24 kJ tungsten slug")


func test_one_torso_hit_kills_and_the_slug_keeps_going() -> void:
	var d: Enemy = room.shooting_range.targets[0]
	var hits: Array[BallisticHit] = []
	var cb: Callable = func(h: BallisticHit) -> void: hits.append(h)
	EventBus.ballistic_hit.connect(cb)
	var from: Vector3 = Vector3(0, 1.6, 10)
	var chest: Vector3 = d.parts[&"chest"].global_position
	Ballistics.fire(rail, from, (chest - from).normalized(), player)
	await wait_physics_frames(6)
	EventBus.ballistic_hit.disconnect(cb)
	assert_true(d.dead, "one chest hit is lethal")
	var through_body: bool = false
	for h: BallisticHit in hits:
		if h.surface.is_flesh and h.result == BallisticHit.Result.PENETRATED:
			through_body = true
			assert_gt(h.deposited(), 1000.0, "hypervelocity drag dumps kJ into the body (%.0f J)" % h.deposited())
			assert_gt(h.speed_out, 1500.0, "and the slug leaves at %.0f m/s" % h.speed_out)
	assert_true(through_body, "the slug passed through the dummy")


func test_spamming_rt_overheats_and_the_shroud_lifts() -> void:
	await _to_rail()
	var rig: ViewmodelRig = weapon.rig()
	assert_true(rig.has_part(&"vent"), "rail model has the vent shroud")
	assert_true(rig.has_part(&"glow"), "and glow strips")
	var vent: Node3D = rig.find_child("vent", true, false) as Node3D
	var rest_y: float = vent.position.y
	var max_lift: float = 0.0
	var glow_seen: PackedFloat32Array = PackedFloat32Array([rig.glow_energy()])  # full charge, cold
	for i: int in 50:
		if weapon.mechanism.venting:
			break
		await _press(&"fire")
		await wait_physics_frames(int(rail.fire_interval * 60.0) + 1)
		glow_seen.append(rig.glow_energy())
	assert_true(weapon.mechanism.venting, "rails overheated")
	for i: int in 40:
		await get_tree().process_frame
		max_lift = maxf(max_lift, vent.position.y - rest_y)
	assert_gt(max_lift, rail.vent_lift * 0.6, "vent shroud lifts (%.4f m)" % max_lift)
	var shots_before: int = weapon.mechanism.loaded()
	await _press(&"fire")
	assert_eq(weapon.mechanism.loaded(), shots_before, "no shot while venting")
	await wait_seconds(rail.vent_time + 0.2)
	assert_false(weapon.mechanism.venting)
	assert_almost_eq(vent.position.y, rest_y, 0.001, "shroud closed again")
	var lo: float = 999.0
	var hi: float = 0.0
	for g: float in glow_seen:
		lo = minf(lo, g)
		hi = maxf(hi, g)
	assert_gt(hi - lo, 0.5, "glow follows charge and heat (%.2f..%.2f)" % [lo, hi])


func test_top_magazine_comes_off_back_and_up() -> void:
	await _to_rail()
	await _press(&"fire")
	await wait_physics_frames(15)
	await _press(&"reload")
	await wait_physics_frames(3)
	assert_true(weapon.is_reloading())
	var mag: Node3D = weapon.rig().find_child("magazine", true, false) as Node3D
	var rest: Vector3 = mag.position
	var furthest: Vector3 = Vector3.ZERO
	var t: float = 0.0
	while weapon.is_reloading() and t < 4.0:
		await get_tree().physics_frame
		t += 1.0 / 60.0
		var off: Vector3 = mag.position - rest
		if off.length() > furthest.length():
			furthest = off
	assert_lt(furthest.x, -0.05, "slides back (%s)" % furthest)
	assert_gt(furthest.y, 0.01, "and up")
	assert_eq(weapon.mechanism.loaded(), 40)
