extends GutTest
## Range targets react to real rounds: plates fall, walls break apart,
## the penetration lane counts what got through, bottles shatter.

var room: TestRoom
var weapon: WeaponData


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	room.player.input_enabled = false
	weapon = (load("res://data/weapons/pistol_57.tres") as WeaponData).duplicate() as WeaponData
	await wait_physics_frames(10)


func _shoot(at: Vector3, from: Vector3 = Vector3(0, 1.6, 10)) -> void:
	Ballistics.fire(weapon, from, (at - from).normalized(), room.player)
	await wait_physics_frames(6)


func test_steel_plate_falls_and_resets() -> void:
	var plate: SteelPlate = room.shooting_range.plates[0]
	await _shoot(plate.aim_points()[0])
	assert_true(plate.down)
	await wait_seconds(plate.reset_time + 0.3)
	assert_false(plate.down, "popped back up")


func test_drywall_wall_breaks_open_under_sustained_fire() -> void:
	var wall: DestructibleWall = room.shooting_range.walls[0]
	var target: Vector3 = wall.global_position + Vector3(0.1, 1.2, 0.0)
	for i: int in 8:
		await _shoot(target)
	assert_gt(wall.broken, 0, "cells broke out")
	# Now there's a hole: the next round goes through the gap without touching the wall.
	var hits: Array[BallisticHit] = []
	var cb: Callable = func(h: BallisticHit) -> void: hits.append(h)
	EventBus.ballistic_hit.connect(cb)
	await _shoot(target)
	EventBus.ballistic_hit.disconnect(cb)
	var touched_wall: bool = false
	for h: BallisticHit in hits:
		if h.collider is StaticBody3D and (h.collider as Node).get_parent() == wall and h.surface.id == &"drywall":
			touched_wall = true
	assert_false(touched_wall, "round passed through the broken-out hole")


func test_penetration_lane_drywall_lets_rounds_through_and_steel_stops_them() -> void:
	var drywall: PenPanel = room.shooting_range.panels[0]
	var steel: PenPanel = room.shooting_range.panels[5]
	for p: PenPanel in [drywall, steel]:
		var face: Vector3 = p.global_position + Vector3(0, 0.9, 0.0)
		await _shoot(face, face + Vector3(0, 0.1, 2.0))
	assert_eq(drywall.hits, 1)
	assert_eq(drywall.through, 1)
	assert_gt(drywall.last_exit_j, 300.0)
	assert_eq(steel.hits, 1)
	assert_eq(steel.through, 0, "AR500 stops 5.7")


func test_bottle_shatters() -> void:
	var bottle: RangeProp = null
	for n: Node in room.shooting_range.get_children():
		if n is RangeProp and (n as RangeProp).breakable:
			bottle = n as RangeProp
			break
	await _shoot(bottle.global_position, bottle.global_position + Vector3(0, 0.3, 4.0))
	assert_false(bottle.visible, "shattered")


func test_target_takes_zone_damage_and_goes_down() -> void:
	var d: Enemy = room.shooting_range.targets[0]
	var chest: Vector3 = d.parts[&"chest"].global_position
	await _shoot(chest)
	assert_lt(d.health, d.config.health)
	assert_false(d.dead)
	await _shoot(d.parts[&"head"].global_position)
	assert_true(d.dead, "headshot finishes it")
	assert_null(room.shooting_range.targets[0], "the spot is empty")
	await wait_seconds(ShootingRange.TARGET_RESPAWN + 0.3)
	var fresh: Enemy = room.shooting_range.targets[0]
	assert_not_null(fresh, "a new one takes the spot")
	assert_false(fresh.dead)
	assert_true(is_instance_valid(d) and d.body.ragdolling, "the body stays down")


func test_aim_assist_slows_the_stick_on_a_target() -> void:
	var player: Player = room.player
	var d: Enemy = room.shooting_range.targets[0]
	GunplayDemo.aim_at(player, d.parts[&"chest"].global_position)
	await wait_physics_frames(2)
	var rate: Vector2 = player.aim_assist.apply(player, Vector2(100, 0), 1.0 / 60.0)
	assert_true(player.aim_assist.on_target)
	assert_lt(rate.x, 90.0, "slowed down near the target")
	player.set_view(player.yaw + 1.2, 0.0)  # look well away
	await wait_physics_frames(2)
	rate = player.aim_assist.apply(player, Vector2(100, 0), 1.0 / 60.0)
	assert_almost_eq(rate.x, 100.0, 0.01, "no effect off target")
	player.aim_assist.config.enabled = false
	GunplayDemo.aim_at(player, d.parts[&"chest"].global_position)
	await wait_physics_frames(2)
	rate = player.aim_assist.apply(player, Vector2(100, 0), 1.0 / 60.0)
	assert_almost_eq(rate.x, 100.0, 0.01, "switched off")
	player.aim_assist.config.enabled = true
