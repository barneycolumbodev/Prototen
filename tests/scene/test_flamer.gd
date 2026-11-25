extends GutTest
## The Triad Flamer (docs/design.md §8.8c): agile, fast-moving arsonist using
## an aerosol can and lighter to spray damaging fire; shooting the can in his
## hand engulfs him in a fireball (without throwing him) and ignites nearby enemies.

var room: TestRoom
var player: Player
var squad: Squad
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var flamer_cfg: EnemyConfig = preload("res://data/enemies/flamer.tres")
var gunman_cfg: EnemyConfig = preload("res://data/enemies/gunman.tres")


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


func _spawn(at: Vector3, cfg: EnemyConfig = flamer_cfg, passive_mode: bool = false) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = cfg
	e.passive = passive_mode
	squad.add(e)
	room.add_child(e)
	e.global_position = at
	var to: Vector3 = player.global_position - at
	e.face(atan2(to.x, to.z))
	if not passive_mode:
		e.awareness = 1.0
		e.last_known = player.global_position
		e._enter(Enemy.State.COMBAT)
	return e


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


func test_flamer_spawns_with_aerosol_can_lighter_and_weakpoint() -> void:
	assert_true(flamer_cfg.flamer)
	assert_gt(flamer_cfg.run_speed, 5.5, "fast and agile")
	var e: Enemy = _spawn(Vector3(0, 0, 5), flamer_cfg, true)
	await wait_physics_frames(2)
	assert_not_null(e.flamer, "FlamerBrain initialized")
	assert_not_null(e.body.gun, "aerosol can in right hand")
	assert_true(e.body.gun.scene_file_path.ends_with("aerosol_can.gltf"), "aerosol can gltf")
	assert_not_null(e.flamer.can_hitbox, "precision weak-point hitbox on can")
	assert_eq(e.flamer.can_hitbox.collision_layer, Ballistics.LAYER_HITBOX)
	assert_not_null(e.flamer.lighter, "lighter in left hand")
	assert_not_null(e.flamer.pilot_flame, "live pilot flame on lighter")
	assert_not_null(e.flamer.flame_jet, "volumetric flame jet node")
	assert_not_null(e.body.look.whole_body(), "reuses existing Tripo triad body model")
	for bank: StringName in [&"flamer_ignite", &"flamer_spray", &"flamer_can_boom", &"player_burn"]:
		assert_gt(Sfx.bank(bank).size(), 0, "SFX bank %s loaded" % bank)


func test_flamer_closes_in_sprays_fire_and_burns_player() -> void:
	_place_player(Vector3(0, 0, 12), Vector3(0, 1, 2))
	var e: Enemy = _spawn(Vector3(0, 0, 3))
	var start_hp: float = player.health
	var burned: bool = await _wait_for(func() -> bool: return e.flamer.fire_ticks >= 3, 5.0)
	assert_true(burned, "closed in and sprayed damaging fire (sprays %d, ticks %d, dist %.1f m)" % [
			e.flamer.sprays, e.flamer.fire_ticks, e.global_position.distance_to(player.global_position)])
	assert_lt(player.health, start_hp - 5.0, "direct flame stream dealt meaningful damage")
	assert_true(player.is_burning(), "lingering afterburn active on player")
	assert_gt(player.burn_intensity(), 0.0, "burn vignette driven while burning")
	# Kill the Flamer and confirm lingering afterburn still ticks damage briefly.
	var hp_after_spray: float = player.health
	e.die(null, &"head")
	await wait_seconds(0.45)
	assert_lt(player.health, hp_after_spray, "afterburn keeps hurting after spray ends")


func test_cover_blocks_flame_spray() -> void:
	# Tall crate at (-4, 1.2, 10) is 2.4 m tall: solid cover between them.
	_place_player(Vector3(-4, 0, 8.2), Vector3(-4, 1, 12))
	var e: Enemy = _spawn(Vector3(-4, 0, 11.8), flamer_cfg, true)
	await wait_physics_frames(4)
	var start_hp: float = player.health
	var origin: Vector3 = e.flamer.nozzle_position()
	var dir: Vector3 = (player.camera().global_position - origin).normalized()
	var reach: float = e.flamer._probe_reach(origin, dir, flamer_cfg.flamer_range)
	assert_lt(reach, 3.0, "tall cover clamps visual flame reach (%.2f m)" % reach)
	e.flamer._apply_flame_tick(player, origin, dir, reach)
	assert_eq(player.health, start_hp, "solid cover blocks flame damage")
	assert_false(player.is_burning(), "no afterburn through cover")


func test_shooting_aerosol_can_engulfs_flamer_and_ignites_nearby() -> void:
	_place_player(Vector3(0, 0, 12), Vector3(0, 1.2, 6))
	var e: Enemy = _spawn(Vector3(0, 0, 6), flamer_cfg, true)
	var near_ally: Enemy = _spawn(Vector3(2.0, 0, 6), gunman_cfg, true)
	var far_ally: Enemy = _spawn(Vector3(-9.5, 0, 6), gunman_cfg, true)
	await wait_physics_frames(4)
	var start_pos: Vector3 = e.global_position
	var near_hp: float = near_ally.health
	var far_hp: float = far_ally.health
	var can_pos: Vector3 = e.flamer.can_world_position()
	var from: Vector3 = player.camera().global_position
	Ballistics.fire(pistol, from, (can_pos - from).normalized(), player)
	await wait_physics_frames(20)
	assert_true(e.flamer.can_detonated, "aerosol can detonated from precision shot")
	assert_true(e.dead, "Flamer killed by engulfing fireball")
	assert_gte(e.charred, 0.85, "Flamer heavily charred by fireball")
	var flat_shift: float = Vector2(e.body.chest_position().x - start_pos.x, e.body.chest_position().z - start_pos.z).length()
	assert_lt(flat_shift, 1.8, "collapsed engulfed in place rather than thrown by blast (shift %.2f m)" % flat_shift)
	assert_true(near_ally.is_burning(), "nearby enemy engulfed/ignited by fireball")
	assert_lt(near_ally.health, near_hp, "nearby enemy took fireball heat damage")
	assert_gt(near_ally.agony, 0.0, "nearby enemy sent into burning agony")
	assert_false(far_ally.is_burning(), "distant enemy unaffected")
	assert_eq(far_ally.health, far_hp, "distant enemy untouched")


func test_body_shots_kill_without_detonating_can() -> void:
	_place_player(Vector3(0, 0, 12), Vector3(0, 1.4, 6))
	var e: Enemy = _spawn(Vector3(0, 0, 6), flamer_cfg, true)
	await wait_physics_frames(4)
	var head_pos: Vector3 = e.body.head_position()
	var from: Vector3 = player.camera().global_position
	for i: int in 3:
		if e.dead:
			break
		Ballistics.fire(pistol, from, (head_pos - from).normalized(), player)
		await wait_physics_frames(2)
	assert_true(e.dead, "headshots killed the Flamer")
	assert_false(e.flamer.can_detonated, "shooting his head does not blow up the aerosol can")


func test_flamer_registered_in_sandbox_spawns() -> void:
	var c: RollingSpawnConfig = RollingSpawnConfig.new()
	c.gunman_weight = 0.0
	c.enforcer_weight = 0.0
	c.red_pole_weight = 0.0
	c.hatchet_man_weight = 0.0
	c.attack_dog_weight = 0.0
	c.flamer_weight = 1.0
	assert_eq(c.pick_role(0.5), "flamer")
	var china: RollingSpawnConfig = load("res://data/levels/chinatown_spawns.tres") as RollingSpawnConfig
	var hotel: RollingSpawnConfig = load("res://data/levels/hotel_spawns.tres") as RollingSpawnConfig
	assert_gt(china.flamer_weight, 0.0, "Flamer spawns on Chinatown docks")
	assert_gt(hotel.flamer_weight, 0.0, "Flamer spawns in Golden Dragon Hotel")
