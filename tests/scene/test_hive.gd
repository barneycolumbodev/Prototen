extends GutTest
## HV-3 Harvester Hive (docs/design.md §3.4e, owner 2026-11-24): LB sends the
## swarm at the man under the crosshair; it takes him out of the fight at
## once, strips him to the muscle, kills him and brings back over a third of
## the operative's health. Nobody in reach: nothing happens.

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
	TimeControl.set_dilation(1.0, 1.0)
	Gore.clear()


func _equip() -> HarvesterHive:
	var lo: BodyLoadout = player.loadout.copy()
	lo.install(lib.find(&"hv3_harvester_hive"))
	player.apply_loadout(lo)
	await wait_physics_frames(2)
	var part: HarvesterHive = player.augments.find(&"hv3_harvester_hive") as HarvesterHive
	assert_not_null(part, "installed")
	if part:
		assert_eq(part.offline_reason(), "", "online on the Operator (SA-2: processing 1.2)")
	return part


func _target(i: int, at: Vector3) -> Enemy:
	var e: Enemy = room.shooting_range.targets[i]
	e.global_position = at
	e.face(0.0)
	return e


func _real_wait(seconds: float) -> void:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await wait_physics_frames(1)


func test_the_swarm_strips_him_kills_him_and_heals() -> void:
	var hv: HarvesterHive = await _equip()
	var e: Enemy = _target(0, Vector3(0.5, 0.0, -1.0))
	var witness: Enemy = _target(1, Vector3(3.0, 0.0, -2.0))
	var nerve: float = witness.morale
	GunplayDemo.aim_at(player, e.body.chest_position())
	player.health = player.max_health() * 0.3
	player.augments.select(hv.slot)
	player.augments.use_selected()
	assert_eq(hv.target, e, "LB took the man under the crosshair")
	assert_true(player.weapon().stowed, "the hand comes up: the gun goes down")
	# Deploy (0.35 s) and a 7 m flight.
	await _real_wait(hv.data.deploy_time + 0.4)
	assert_true(e.engulfed, "the swarm is on him")
	assert_false(e.has_gun, "he drops his gun")
	assert_false(e.is_in_group(&"enemies"), "he's out of the fight at once")
	assert_lt(witness.morale, nerve, "whoever sees it loses his nerve")
	var before: float = player.health
	await _real_wait(1.5)
	assert_false(e.alive, "stripped to the muscle, he dies")
	assert_almost_eq(e.body.flay, 1.0, 0.01, "all the way")
	assert_almost_eq(hv.healed, player.max_health() * hv.cfg.heal_share, 0.5, "38 % of max health came back")
	assert_gte(player.health - before, hv.healed - 0.5)
	assert_lt(hv.charge, 1.0, "the swarm is spent until the hive rebuilds it")
	await _real_wait(hv.data.recover_time + hv.data.cooldown_time + 0.1)
	assert_false(player.weapon().stowed, "the gun comes back up")


func test_nobody_in_reach_nothing_happens() -> void:
	var hv: HarvesterHive = await _equip()
	for e: Enemy in room.shooting_range.targets:
		e.global_position = Vector3(40.0, 0.0, 40.0)
	player.augments.select(hv.slot)
	player.augments.use_selected()
	await wait_physics_frames(5)
	assert_eq(hv.state, ActivePart.State.IDLE, "no target: the hand stays down")
	assert_eq(hv.charge, 1.0, "nothing spent")
	assert_false(player.weapon().stowed)


func test_a_dog_is_stripped_too() -> void:
	var hv: HarvesterHive = await _equip()
	room.shooting_range.clear_targets()
	var d: AttackDog = AttackDog.new()
	d.player = player
	room.add_child(d)
	d.global_position = Vector3(0.5, 0.0, 1.0)
	d.set_physics_process(false)
	await wait_physics_frames(2)
	GunplayDemo.aim_at(player, d.chest_position())
	player.augments.select(hv.slot)
	player.augments.use_selected()
	assert_eq(hv.target, d, "LB took the dog")
	await _real_wait(2.2)
	assert_false(d.alive, "it dies")
	assert_almost_eq(d.flay, 1.0, 0.01, "stripped like a man")
	assert_gt(hv.healed, 0.0, "and it heals")
