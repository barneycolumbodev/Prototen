extends GutTest
## The Incense Master, the triad map's first boss (docs/design.md §8.7a/b):
## a huge enforcer with a Gauss prosthetic. The haymaker, the ground pound
## (jump it), the Gauss shot (a real slug: it hurts, the LC-6 catches it and
## throws it back, which staggers him), down on one knee at zero instead of
## dead, and the execution that takes his head.

var room: TestRoom
var player: Player
var squad: Squad
var cfg: EnemyConfig = preload("res://data/enemies/incense_master.tres")
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var lib: PartLibrary = preload("res://data/body/part_library.tres")


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


func after_each() -> void:
	TimeControl.set_slowmo(1.0)
	Ballistics.clear()


## The boss at `at`, facing the operative, in the fight, doing nothing until told.
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
	# Hold him still until the test starts a move (a long stagger).
	e.boss.phase = BossBrain.Phase.STAGGER
	e.boss._t = -999.0
	return e


func _place_player(at: Vector3, look: Vector3) -> void:
	player.global_position = at
	player.velocity = Vector3.ZERO
	var to: Vector3 = look - player.camera().global_position
	player.set_view(atan2(-to.x, -to.z), atan2(to.y, Vector2(to.x, to.z).length()))


func _wait_for(cond: Callable, seconds: float) -> bool:
	var frames: int = int(seconds * 60.0)
	for i: int in frames:
		if cond.call():
			return true
		await wait_physics_frames(1)
	return cond.call()


func _real_wait_for(cond: Callable, seconds: float) -> bool:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		if cond.call():
			return true
		await wait_physics_frames(1)
	return cond.call()


func test_he_is_huge_and_wears_his_hardware() -> void:
	var e: Enemy = _spawn(Vector3(2, 0, 12))
	await wait_physics_frames(2)
	assert_not_null(e.boss, "a boss brain")
	assert_true(e.is_in_group(&"boss"))
	assert_gt(cfg.body_scale, 1.3, "massive: %.2f m" % (1.75 * cfg.body_scale))
	assert_null(e.body.gun, "no gun: the arm is the gun")
	var hw: BossHardware = e.boss.hw
	assert_eq(hw.pieces.size(), 4, "upper arm, forearm, fist, pendant")
	assert_not_null(hw.muzzle, "the rails' muzzle")
	assert_eq(hw.plates.size(), 2, "steel over the forearm and the fist")
	assert_true(e.body.is_severed(&"forearm_R"), "his own forearm is gone")
	assert_eq(e.body.hitboxes[&"r_forearm"].collision_layer, 0, "no flesh where the prosthetic is")
	assert_ne(e.body.hitboxes[&"l_forearm"].collision_layer, 0)
	# Since 2026-11-17 he's a whole Tripo man (bald, black leather, tattoos; docs/design.md §5.6b).
	assert_eq(e.body.look.key(), "tp_incense_master", "the Tripo Incense Master")


func test_the_haymaker_lands_close_and_misses_a_sidestep() -> void:
	_place_player(Vector3(2, 0, 9.5), Vector3(2, 1.6, 12))
	var e: Enemy = _spawn(Vector3(2, 0, 12))
	await wait_physics_frames(3)
	var b: BossBrain = e.boss
	b.phase = BossBrain.Phase.HUNT
	b._start_swing()
	var hp: float = player.health
	await _wait_for(func() -> bool: return b._struck, 2.0)
	await wait_physics_frames(1)
	assert_eq(b.swing_hits, 1, "the haymaker lands at 2.5 m")
	var expected: float = b.cfg.swing_damage * player.body.stat(&"damage_per_kj") / Player.BASE_DAMAGE_PER_KJ
	assert_almost_eq(hp - player.health, expected, 0.5, "armour-scaled")
	await _wait_for(func() -> bool: return b.phase == BossBrain.Phase.HUNT, 2.0)
	b._cool_swing = 0.0
	_place_player(Vector3(2, 0, 9.5), Vector3(2, 1.6, 12))
	await wait_physics_frames(2)
	b._start_swing()
	await _wait_for(func() -> bool: return b._t >= b.cfg.swing_windup * 0.4, 2.0)
	# A dash out to his side, faster than he turns.
	_place_player(Vector3(6.5, 0, 12.5), Vector3(2, 1.6, 12))
	await _wait_for(func() -> bool: return b._struck, 2.0)
	assert_eq(b.swing_hits, 1, "the sidestep made him miss")


func test_the_ground_pound_hurts_on_the_ground_not_in_the_air() -> void:
	_place_player(Vector3(2, 0, 7.5), Vector3(2, 1.6, 12))
	var e: Enemy = _spawn(Vector3(2, 0, 12))
	await wait_physics_frames(3)
	var b: BossBrain = e.boss
	b.phase = BossBrain.Phase.HUNT
	b._start_pound()
	var hp: float = player.health
	await _wait_for(func() -> bool: return b._struck, 3.0)
	await wait_physics_frames(1)
	assert_eq(b.pound_hits, 1, "4.5 m from the fist, standing: hit")
	assert_gt(hp - player.health, b.cfg.pound_damage_far * 0.9)
	assert_lt(hp - player.health, b.cfg.pound_damage_near + 0.1)
	assert_gt(player.velocity.y, 1.0, "thrown up")
	await _wait_for(func() -> bool: return b.phase == BossBrain.Phase.HUNT, 3.0)
	await _wait_for(func() -> bool: return player.is_on_floor(), 3.0)
	_place_player(Vector3(2, 0, 7.5), Vector3(2, 1.6, 12))
	b._start_pound()
	await _wait_for(func() -> bool: return b._t >= b.cfg.pound_windup - 0.12, 3.0)
	# Jumped: up in the air as it lands.
	player.global_position += Vector3.UP * 1.0
	player.velocity = Vector3.UP * 3.0
	hp = player.health
	await _wait_for(func() -> bool: return b._struck, 2.0)
	assert_eq(b.pound_hits, 1, "jumped it")
	assert_eq(player.health, hp)


func test_the_gauss_shot_is_a_real_slug() -> void:
	_place_player(Vector3(2, 0, -4), Vector3(2, 1.6, 12))
	var e: Enemy = _spawn(Vector3(2, 0, 12))
	await wait_physics_frames(12)
	var b: BossBrain = e.boss
	b.phase = BossBrain.Phase.HUNT
	b._start_cannon()
	assert_eq(b.phase, BossBrain.Phase.CANNON)
	var hp: float = player.health
	var fired0: int = Ballistics.rounds_fired
	assert_true(await _wait_for(func() -> bool: return b.shots > 0, 3.0), "fired after the charge")
	assert_gte(b._t, b.cfg.cannon_charge - 0.05, "not before the charge was done")
	assert_eq(Ballistics.rounds_fired - fired0, 1, "one round through Ballistics")
	await wait_physics_frames(4)
	var slug: WeaponData = b.cfg.cannon_round
	var energy_kj: float = 0.5 * slug.bullet_mass_g * 0.001 * slug.muzzle_velocity * slug.muzzle_velocity * 0.001
	gut.p("slug: %.1f kJ, took %.1f" % [energy_kj, hp - player.health])
	assert_gt(hp - player.health, 40.0, "it hurts (%.1f)" % (hp - player.health))


func test_the_lc6_catches_his_slug_and_throwing_it_back_staggers_him() -> void:
	var lo: BodyLoadout = player.loadout.copy()
	lo.install(lib.find(&"lc6_lorentz_catcher"))
	player.apply_loadout(lo)
	player.invulnerable = true
	_place_player(Vector3(2, 0, -4), Vector3(2, 1.6, 12))
	var e: Enemy = _spawn(Vector3(2, 0, 12))
	await wait_physics_frames(12)
	var c: LorentzCatcher = player.augments.find(&"lc6_lorentz_catcher") as LorentzCatcher
	c.script_hold(true)
	player.augments.select(c.slot)
	player.augments.use_selected()
	await _real_wait_for(func() -> bool: return c.state == ActivePart.State.ACTIVE, 2.0)
	var b: BossBrain = e.boss
	b.phase = BossBrain.Phase.HUNT
	b._start_cannon()
	await _wait_for(func() -> bool: return b.shots > 0, 3.0)
	await wait_physics_frames(3)
	assert_eq(c.gauss_caught, 1, "the slug is held in the field")
	assert_eq(c.held.size(), 1)
	assert_true(LorentzCatcher.is_gauss(c.held[0].weapon), "as a Gauss slug")
	var hp: float = e.health
	b.phase = BossBrain.Phase.HUNT
	b._immune = 0.0
	_place_player(Vector3(2, 0, -4), e.body.chest_position())
	await wait_physics_frames(2)
	c.script_hold(false)
	await _real_wait_for(func() -> bool: return c.thrown_total >= 1, 2.0)
	await wait_physics_frames(4)
	assert_eq(c.thrown_total, 1, "it goes back")
	assert_lt(e.health, hp - 100.0, "it hit him hard (%.0f -> %.0f)" % [hp, e.health])
	assert_gte(b.staggers, 1, "a Gauss slug staggers him")


func test_at_zero_he_goes_down_on_one_knee_and_wont_die() -> void:
	_place_player(Vector3(2, 0, 6), Vector3(2, 1.6, 12))
	var e: Enemy = _spawn(Vector3(2, 0, 10))
	await wait_physics_frames(3)
	e.boss.phase = BossBrain.Phase.HUNT
	e.health = 5.0
	var eye: Vector3 = player.camera().global_position
	Ballistics.fire(pistol, eye, (e.body.chest_position() - eye).normalized(), player)
	await wait_physics_frames(3)
	assert_true(e.alive, "not dead")
	assert_true(e.boss.is_down(), "down on one knee")
	assert_eq(e.body.stance, &"kneel_down")
	assert_false(e.is_in_group(&"enemies"), "out of the fight")
	assert_true(e.is_in_group(&"boss"), "still the boss: the bar and the prompt find him")
	assert_not_null(e.boss.execution, "waiting for the execution")
	for k: int in 6:
		Ballistics.fire(pistol, eye, (e.body.head_position() - eye).normalized(), player)
	e.burst(Vector3.FORWARD * 10.0)
	assert_false(e.sever(&"head", Vector3.FORWARD, true), "nothing comes off him yet")
	await wait_physics_frames(3)
	assert_true(e.alive, "shooting him on his knee doesn't finish him")
	assert_false(e.body.gibbed)


func test_the_execution_takes_his_head() -> void:
	_place_player(Vector3(2, 0, 7.5), Vector3(2, 1.4, 10))
	var e: Enemy = _spawn(Vector3(2, 0, 10))
	await wait_physics_frames(3)
	e.die(null, &"chest")
	await wait_physics_frames(30)
	var ex: BossExecution = e.boss.execution
	assert_true(ex.can_start(), "close and looking at him: the prompt")
	_place_player(Vector3(2, 0, 2), Vector3(2, 1.4, 10))
	await wait_physics_frames(2)
	assert_false(ex.can_start(), "too far: no prompt")
	_place_player(Vector3(2, 0, 7.5), Vector3(2, 1.4, 10))
	await wait_physics_frames(2)
	var died: Array[bool] = [false]
	e.died.connect(func(_x: Enemy) -> void: died[0] = true)
	ex.script_start()
	await wait_physics_frames(2)
	assert_true(ex.running)
	assert_false(player.input_enabled, "the operative is in the cutscene")
	assert_true(player.invulnerable)
	assert_true(player.weapon().stowed, "both hands busy: the gun is down")
	await _real_wait_for(func() -> bool: return ex.head_gone, 6.0)
	assert_eq(ex.punches, e.config.boss.punch_times.size(), "every punch landed")
	assert_true(e.body.is_severed(&"head"), "the last one took the head")
	assert_false(e.alive)
	assert_true(died[0], "he counts as killed")
	assert_false(e.is_in_group(&"boss"))
	await _real_wait_for(func() -> bool: return ex.done, 6.0)
	assert_eq(ex.flicks, 3, "the blood shaken off")
	assert_true(player.input_enabled, "back in control")
	assert_false(player.invulnerable)
	assert_eq(Engine.time_scale, 1.0, "slow motion over")
	await wait_physics_frames(30)
	assert_false(player.weapon().stowed, "the gun comes back up")


func test_below_half_he_rages() -> void:
	var e: Enemy = _spawn(Vector3(2, 0, 10))
	await wait_physics_frames(2)
	e.boss.phase = BossBrain.Phase.HUNT
	e.health = cfg.health * 0.45
	e.boss.on_hurt(10.0, null)
	assert_true(e.boss.enraged)
	assert_gt(e.boss.speed(), 0.0)
	var bc: BossConfig = e.config.boss
	var v: float = e.boss.speed()
	assert_true(is_equal_approx(v, bc.walk_speed * bc.rage_speed) or is_equal_approx(v, bc.charge_speed * bc.rage_speed), "faster: %.2f" % v)


func test_the_intro_lands_him_and_hands_back_control() -> void:
	_place_player(Vector3(2, 0, 2), Vector3(2, 1.6, 14))
	await wait_physics_frames(2)
	var e: Enemy = Enemy.new()
	e.config = cfg
	squad.add(e)
	room.add_child(e)
	var intro: BossIntro = BossIntro.new()
	intro.boss = e
	intro.player = player
	room.add_child(intro)
	await wait_physics_frames(2)
	assert_eq(e.boss.phase, BossBrain.Phase.INTRO)
	assert_false(player.input_enabled)
	assert_true(player.invulnerable)
	var at: Vector3 = intro.landing
	var ended: Array[bool] = [false]
	intro.finished.connect(func() -> void: ended[0] = true)
	assert_gt(at.distance_to(player.global_position), 5.0, "in front of him, not on him")
	var fwd: Vector3 = -player.camera().global_basis.z
	assert_gt(fwd.dot((at - player.global_position).normalized()), 0.3, "where he's looking")
	await _real_wait_for(func() -> bool: return ended[0], 8.0)
	assert_true(ended[0], "the entrance ends")
	assert_almost_eq(e.global_position.x, at.x, 0.3, "he landed where it said")
	assert_almost_eq(e.global_position.z, at.z, 0.3)
	assert_eq(e.boss.phase, BossBrain.Phase.HUNT, "and fights")
	assert_eq(e.state, Enemy.State.COMBAT)
	assert_true(player.input_enabled, "control back")
	assert_false(player.invulnerable)
	assert_eq(get_viewport().get_camera_3d(), player.camera(), "the operative's eyes again")
