extends GutTest
## Triad enemies on the range and in wave mode (docs/design.md §5.1, §5.5, §5.6):
## zones, armour, wounds, ragdolls and their cap, dismemberment and the gore
## setting, AI that fires back, suppression and wave composition.

var room: TestRoom
var player: Player
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var rail: WeaponData = preload("res://data/weapons/rail_carbine.tres")
var m14: WeaponData = preload("res://data/weapons/m14p.tres")
var _gore: int


func before_each() -> void:
	_gore = Settings.gore_level
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(20)


func after_each() -> void:
	Settings.gore_level = _gore
	Gore.clear()


func _shoot(w: WeaponData, at: Vector3, from: Vector3 = Vector3(0, 1.6, 9.0)) -> void:
	Ballistics.fire(w, from, (at - from).normalized(), player)
	await wait_physics_frames(4)


func _target(i: int = 0) -> Enemy:
	return room.shooting_range.targets[i]


func test_range_targets_are_triad_members() -> void:
	assert_eq(room.shooting_range.targets.size(), ShootingRange.DUMMIES.size())
	var roles: Array[String] = []
	for e: Enemy in room.shooting_range.targets:
		assert_true(e.passive, "range targets don't shoot back")
		roles.append(e.config.callsign)
	assert_has(roles, "GUNMAN")
	assert_has(roles, "ENFORCER")
	assert_has(roles, "RED POLE")
	assert_eq(_target().body.hitboxes.size(), 17, "17 damage zones on bones")


func test_hitboxes_follow_the_bones() -> void:
	var e: Enemy = _target()
	var head: Vector3 = e.body.hitboxes[&"head"].global_position
	var foot: Vector3 = e.body.hitboxes[&"l_foot"].global_position
	assert_almost_eq(head.y, 1.65, 0.12, "head at head height")
	assert_lt(foot.y, 0.2, "feet on the floor")


func test_chest_hit_paints_entry_and_exit_wounds_and_sprays() -> void:
	var e: Enemy = _target()
	var sprays: int = Gore.sprays_fired
	await _shoot(m14, e.body.hitboxes[&"chest"].global_position)
	assert_lt(e.health, e.config.health)
	assert_eq(e.body.wound_count(), 2, "entry and exit")
	assert_gt(Gore.sprays_fired, sprays)
	await wait_seconds(0.6)
	assert_gt(Gore.splat_count(), 0, "blood behind him")


func test_headshot_kills_and_ragdolls_then_freezes() -> void:
	var e: Enemy = _target()
	await _shoot(pistol, e.body.hitboxes[&"head"].global_position)
	assert_true(e.dead)
	assert_true(e.body.ragdolling)
	assert_true(e.body.is_simulating())
	var head_y: float = e.body.bone_position(&"head").y
	await wait_seconds(RagdollBudget.FREEZE_AFTER * 2.0 + 0.5)
	assert_true(e.body.frozen, "frozen after it settles")
	assert_lt(e.body.bone_position(&"head").y, head_y - 0.8, "and it fell (head %.2f m)" % e.body.bone_position(&"head").y)
	assert_gt(Gore.pool_count(), 0, "a pool under the body")


func test_at_most_three_ragdolls_simulate() -> void:
	for i: int in 4:
		var e: Enemy = _target(i)
		e.die(null, &"chest")
	await wait_physics_frames(2)
	assert_lte(RagdollBudget.active_count(), RagdollBudget.MAX_ACTIVE)
	var simulating: int = 0
	for b: Enemy in room.shooting_range.bodies:
		if b.body.is_simulating():
			simulating += 1
	assert_eq(simulating, 3, "the oldest froze")


func test_railgun_destroys_the_head_at_maximum_gore() -> void:
	Settings.gore_level = Gore.Level.MAXIMUM
	var e: Enemy = _target()
	await _shoot(rail, e.body.hitboxes[&"head"].global_position)
	assert_true(e.dead)
	assert_true(e.body.is_severed(&"head"))
	assert_gt(Gore.gib_count(), 0, "chunks")


func test_railgun_takes_a_forearm_off() -> void:
	Settings.gore_level = Gore.Level.MAXIMUM
	var e: Enemy = _target(2)
	var arm: Vector3 = e.body.hitboxes[&"l_forearm"].global_position
	await _shoot(rail, arm, arm + Vector3(-0.2, 0.05, 6.0))
	assert_true(e.body.is_severed(&"forearm_L"), "forearm severed")
	assert_eq(e.body.hitboxes[&"l_hand"].collision_layer, 0, "its zones are gone")


func test_standard_gore_never_dismembers() -> void:
	Settings.gore_level = Gore.Level.STANDARD
	var e: Enemy = _target()
	await _shoot(rail, e.body.hitboxes[&"head"].global_position)
	assert_true(e.dead)
	assert_false(e.body.is_severed(&"head"))


func test_gore_off_means_no_blood() -> void:
	Settings.gore_level = Gore.Level.OFF
	var e: Enemy = _target()
	var sprays: int = Gore.sprays_fired
	await _shoot(m14, e.body.hitboxes[&"chest"].global_position)
	assert_lt(e.health, e.config.health, "still takes damage")
	assert_eq(e.body.wound_count(), 0)
	assert_eq(Gore.sprays_fired, sprays)


func test_enforcer_plate_stops_a_pistol_round() -> void:
	var e: Enemy = _target(1)
	assert_true(e.config.plate_carrier)
	var kinds: Array[StringName] = []
	var cb: Callable = func(k: StringName, _h: BallisticHit) -> void: kinds.append(k)
	EventBus.target_hit.connect(cb)
	var chest: Vector3 = e.body.hitboxes[&"chest"].global_position
	await _shoot(pistol, chest, chest + Vector3(0.0, 0.0, 6.0))
	EventBus.target_hit.disconnect(cb)
	assert_has(kinds, &"armor", "the plate took it")
	assert_gt(e.health, e.config.health * 0.9, "only blunt trauma")


func test_leg_hits_put_him_on_the_ground() -> void:
	var e: Enemy = _target()
	for z: StringName in [&"l_thigh", &"r_thigh", &"l_shin"]:
		await _shoot(m14, e.body.hitboxes[z].global_position)
		if e.dead:
			break
	assert_true(e.dead or e.state == Enemy.State.CRAWL, "crawling (state %s)" % e.state_name())


func test_wave_composition_grows() -> void:
	assert_eq(WaveMode.composition(1).size(), 4)
	assert_does_not_have(WaveMode.composition(1), "red_pole")
	assert_has(WaveMode.composition(2), "enforcer")
	assert_has(WaveMode.composition(3), "red_pole")
	assert_eq(WaveMode.composition(20).size(), WaveMode.MAX_ACTIVE)


func test_wave_mode_spawns_enemies_that_fire_back() -> void:
	player.invulnerable = false
	# A tougher body for the test, so a lucky wave doesn't restart it.
	player.body_config = player.body_config.duplicate() as PlayerBodyConfig
	player.body_config.max_health = 5000.0
	player.health = 5000.0
	var hits: Array[float] = []
	var cb: Callable = func(a: float, _d: Vector3) -> void: hits.append(a)
	EventBus.player_damaged.connect(cb)
	room.wave_mode.start()
	assert_eq(room.shooting_range.targets[0], null, "the range cleared")
	await wait_seconds(12.0)
	EventBus.player_damaged.disconnect(cb)
	assert_gt(room.wave_mode.enemies.size(), 2, "a wave came in")
	assert_lte(room.wave_mode.squad.shooter_count(), Squad.MAX_SHOOTERS, "only a few shoot at once")
	assert_gt(hits.size(), 0, "and they hit the player")
	var worst: float = 0.0
	for a: float in hits:
		worst = maxf(worst, a)
	assert_lt(worst, 40.0, "the augmented body soaks up rifle rounds (max %.0f)" % worst)
	room.wave_mode.stop()
	await wait_physics_frames(2)
	assert_not_null(room.shooting_range.targets[0], "range back after the waves")


func test_near_misses_suppress() -> void:
	var e: Enemy = _target()
	var head: Vector3 = e.body.head_position()
	var from: Vector3 = head + Vector3(0.5, 0.0, 8.0)
	Ballistics.fire(m14, from, (head + Vector3(0.6, 0.0, -2.0) - from).normalized(), player)
	await wait_physics_frames(4)
	assert_gt(e.suppression, 0.1, "a round past his head")
