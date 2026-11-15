extends GutTest
## The Hatchet Man (docs/design.md §8.8): a triad man with a hatchet or a
## cleaver who flanks, sprints between cover, vaults low walls and closes in
## for a telegraphed chop that has to be dodged or stopped.

var room: TestRoom
var player: Player
var squad: Squad
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var cfg: EnemyConfig = preload("res://data/enemies/hatchet_man.tres")


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	await wait_physics_frames(10)
	room.shooting_range.clear_targets()
	room.wave_mode._build_navigation()
	squad = Squad.new()
	room.add_child(squad)
	squad.set_player(player)
	squad.build_cover(Vector3.ZERO, 15.5, room.get_world_3d())
	player.invulnerable = false
	player.input_enabled = false
	player.body_config = player.body_config.duplicate() as PlayerBodyConfig
	player.body_config.max_health = 5000.0
	player.health = 5000.0
	await wait_physics_frames(2)


## A Hatchet Man at `at`, facing the operative, already in the fight.
func _spawn(at: Vector3) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = cfg
	squad.add(e)
	room.add_child(e)
	e.global_position = at
	var to: Vector3 = player.global_position - at
	e.face(atan2(to.x, to.z))
	e.awareness = 1.0
	e.last_known = player.global_position
	e._enter(Enemy.State.COMBAT)
	return e


## The operative at `at`, looking at `look`.
func _place_player(at: Vector3, look: Vector3) -> void:
	player.global_position = at
	player.velocity = Vector3.ZERO
	var to: Vector3 = look - at
	player.set_view(atan2(-to.x, -to.z), 0.0)


func _wait_for(cond: Callable, seconds: float) -> bool:
	var frames: int = int(seconds * 60.0)
	for i: int in frames:
		if cond.call():
			return true
		await wait_physics_frames(1)
	return cond.call()


func test_he_carries_a_blade_and_no_gun() -> void:
	assert_true(cfg.melee)
	assert_eq(cfg.melee_scenes.size(), 2, "a hatchet or a cleaver")
	var e: Enemy = _spawn(Vector3(0, 0, 4))
	await wait_physics_frames(2)
	assert_not_null(e.melee, "a melee brain")
	assert_not_null(e.body.gun, "the blade in his hand")
	assert_true(e.body.gun.scene_file_path.ends_with("hatchet.gltf") or e.body.gun.scene_file_path.ends_with("cleaver.gltf"),
			"a blade: %s" % e.body.gun.scene_file_path)
	assert_true(e.is_threat())


func test_he_runs_in_and_the_chop_lands() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 1, 0))
	var e: Enemy = _spawn(Vector3(0, 0, 5))
	var health: float = player.health
	var landed: bool = await _wait_for(func() -> bool: return e.melee.hits > 0, 5.0)
	assert_true(landed, "he closed 8 m and struck (strikes %d, whiffs %d, at %.1f m)" % [e.melee.strikes, e.melee.whiffs,
			e.global_position.distance_to(player.global_position)])
	var expected: float = cfg.melee_damage * player.body.stat(&"damage_per_kj") / Player.BASE_DAMAGE_PER_KJ
	assert_almost_eq(health - player.health, expected * e.melee.hits, 0.5, "a chop's damage, scaled by armour")
	assert_gt(e.melee.strikes, 0)


func test_a_sidestep_in_the_windup_makes_him_miss() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 1, 0))
	var e: Enemy = _spawn(Vector3(0, 0, 9.5))
	var cocked: bool = await _wait_for(func() -> bool: return e.melee.is_winding_up(), 3.0)
	assert_true(cocked, "the blade went up")
	var health: float = player.health
	# The operative slides out to the side while the blade is up.
	_place_player(player.global_position + Vector3(4.5, 0, 0), e.global_position)
	await wait_seconds(cfg.melee_windup + 0.1)
	assert_eq(e.melee.hits, 0, "swung at air")
	assert_eq(e.melee.whiffs, 1)
	assert_eq(player.health, health, "untouched")


func test_two_quick_rounds_in_the_windup_break_it_off() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 1, 0))
	var e: Enemy = _spawn(Vector3(0, 0, 9.5))
	var cocked: bool = await _wait_for(func() -> bool: return e.melee.is_winding_up(), 3.0)
	assert_true(cocked, "the blade went up")
	var health: float = player.health
	var chest: Vector3 = e.body.hitboxes[&"stomach"].global_position
	var from: Vector3 = player.camera().global_position
	# Two quick rounds into him while the blade is up.
	for i: int in 2:
		Ballistics.fire(pistol, from, (chest - from).normalized(), player)
		await wait_physics_frames(3)
	assert_true(e.dead or e.melee.phase == MeleeBrain.Phase.RECOVER, "staggered out of it (hp %.0f)" % e.health)
	await wait_seconds(cfg.melee_windup + 0.1)
	assert_true(e.dead or e.melee.hits == 0, "the chop was broken off")
	assert_eq(player.health, health, "and never landed")


func test_he_vaults_a_low_crate_but_not_a_tall_one() -> void:
	# The low crate at (8, 0.5, 11): 3 x 1.0 x 0.6 m.
	var e: Enemy = _spawn(Vector3(8, 0, 12.0))
	await wait_physics_frames(2)
	var plan: Array = e.melee.vault_plan(e.global_position, Vector3(0, 0, -1))
	assert_eq(plan.size(), 2, "a 1.0 m crate is vaultable")
	if plan.size() == 2:
		var land: Vector3 = plan[0]
		assert_lt(land.z, 10.7, "lands beyond it (z %.2f)" % land.z)
		assert_almost_eq(land.y, 0.0, 0.1, "on the floor")
	# The tall crate at (-4, 1.2, 10): 2.4 m.
	e.global_position = Vector3(-4, 0, 11.4)
	await wait_physics_frames(2)
	assert_eq(e.melee.vault_plan(e.global_position, Vector3(0, 0, -1)).size(), 0, "2.4 m is too tall")


func test_he_goes_over_a_low_wall_to_reach_you() -> void:
	# The operative behind the low crate at z 11 (and the partition behind him).
	_place_player(Vector3(8, 0, 9.4), Vector3(8, 1, 14))
	var e: Enemy = _spawn(Vector3(8, 0, 13.6))
	var over: bool = await _wait_for(func() -> bool: return e.global_position.z < 10.6, 4.0)
	assert_true(over, "he crossed the crate (z %.2f)" % e.global_position.z)
	assert_gt(e.melee.vaults, 0, "by vaulting it")
	var landed: bool = await _wait_for(func() -> bool: return e.melee.hits > 0, 3.0)
	assert_true(landed, "and struck")


func test_the_flank_point_is_off_to_the_side() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 1, 0))
	var e: Enemy = _spawn(Vector3(0, 0, -2))
	await wait_physics_frames(2)
	var fwd: Vector3 = -player.camera().global_basis.z
	fwd.y = 0.0
	for s: float in [1.0, -1.0]:
		e.melee.side = s
		var to: Vector3 = e.melee.flank_point(player, 15.0) - player.global_position
		to.y = 0.0
		assert_almost_eq(rad_to_deg(fwd.angle_to(to)), cfg.flank_angle_deg, 1.0, "off his facing by the flank angle")
		assert_almost_eq(signf(fwd.cross(to).y), -s, 0.01, "on side %d" % int(s))
