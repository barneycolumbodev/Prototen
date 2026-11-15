extends GutTest
## Survival on the Chinatown docks (docs/design.md §8), played through: the
## kit goes on the player, wave 1 comes in out of sight, clearing it brings
## a supply drop with a choice of two, taking one changes the run, wave 2
## follows, and death ends the run.

var map: ChinatownMap
var cfg: SurvivalConfig = preload("res://data/run/survival.tres")


func before_all() -> void:
	# The drop screen pauses the tree: GUT's waits must keep running, the map must not.
	process_mode = Node.PROCESS_MODE_ALWAYS


func before_each() -> void:
	map = (load("res://src/levels/chinatown/chinatown.tscn") as PackedScene).instantiate() as ChinatownMap
	map.autostart_spawns = false
	map.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child_autofree(map)
	await wait_physics_frames(10)


func after_each() -> void:
	get_tree().paused = false


func _start() -> SurvivalRun:
	var ghost: Doctrine = cfg.doctrine_named("Ghost")
	var mp5: WeaponData = cfg.starter_weapons[1]
	await map.start_survival(ghost, mp5, ghost.starter_actives[0], 42)
	await wait_physics_frames(2)
	return map.survival


func _kill_all(run: SurvivalRun) -> void:
	for e: Enemy in run.director.enemies:
		if is_instance_valid(e) and e.alive:
			e.die(null, &"chest")


func test_kit_goes_on_the_player() -> void:
	var run: SurvivalRun = await _start()
	assert_not_null(run)
	assert_null(map.wave_mode, "no Sandbox spawner in a run")
	var w: PlayerWeapon = map.player.weapon()
	assert_eq(w.slots.size(), 1, "one gun")
	assert_eq(w.data.display_name, cfg.starter_weapons[1].display_name)
	var acts: Array[ActivePartData] = map.player.loadout.actives()
	assert_eq(acts.size(), 1)
	assert_eq(acts[0].charge_max, 4.0, "RX-9 Mk I: 4 s")
	assert_true(map.player.body.is_online(&"rx9_reflex_overclock"), "the Ghost body runs it")
	assert_true(map.player.augments.status.locked, "the loadout screen can't change the body")


func test_a_wave_clears_into_a_drop_then_the_next_wave() -> void:
	var run: SurvivalRun = await _start()
	await wait_until(func() -> bool: return run.director.in_wave, 5.0)
	assert_eq(run.state.wave, 1)
	var expected: int = run.director.queue.size()
	assert_between(expected, 3, 5)
	await wait_until(func() -> bool: return run.director.queue.is_empty(), 15.0)
	assert_eq(run.director.spawned_total, expected, "the whole wave came in")
	var cam: Vector3 = map.player.camera().global_position
	for e: Enemy in run.director.enemies:
		assert_gte(e.global_position.distance_to(map.player.global_position), run.spawn_config.min_distance - 1.0)
	gut.p("wave 1: %d men, camera at %s" % [expected, cam])
	_kill_all(run)
	await wait_until(func() -> bool: return run.drop_screen.visible, 6.0)
	assert_true(run.drop_screen.visible, "the supply drop")
	assert_eq(run.drop_screen.offers.size(), 2, "the first drop is a choice")
	assert_true(get_tree().paused)
	var o: RunState.Offer = run.drop_screen.offers[0]
	gut.p("offered: %s | %s" % [o.title(), run.drop_screen.offers[1].title()])
	run.drop_screen.take()
	assert_false(get_tree().paused)
	assert_eq(run.state.drops, 1)
	assert_true(run.state.owns(o.item), "the run has it")
	if o.item.kind() == RunItem.Kind.WEAPON:
		assert_eq(map.player.weapon().slots.size(), 2, "the gun is on the wheel")
	else:
		assert_true(map.player.loadout.has_part(o.item.id()), "the part is in the body")
	await wait_until(func() -> bool: return run.director.in_wave, 6.0)
	assert_eq(run.state.wave, 2)


func test_death_ends_the_run() -> void:
	var run: SurvivalRun = await _start()
	await wait_until(func() -> bool: return run.director.in_wave, 5.0)
	map.player.take_damage(99999.0, Vector3.FORWARD)
	await wait_physics_frames(2)
	assert_true(run.over)
	assert_true(run.director.queue.is_empty(), "no more men come")
	await wait_until(func() -> bool: return run.over_screen.visible, 4.0)
	assert_true(run.over_screen.visible, "run over")


func test_wave_5_brings_the_incense_master_and_his_drop() -> void:
	var run: SurvivalRun = await _start()
	await wait_until(func() -> bool: return run.director.in_wave, 5.0)
	# Skip to the end of wave 4.
	run.director.queue.clear()
	_kill_all(run)
	run._wait = -1.0
	run.drop_screen.visible = false
	get_tree().paused = false
	run.state.wave = 4
	run._next_wave()
	assert_eq(run.state.wave, 5)
	var boss: Enemy = run.director.boss
	assert_not_null(boss, "the boss came with wave 5")
	assert_eq(boss.config.boss.title, "THE INCENSE MASTER")
	assert_false(map.player.input_enabled, "his entrance is playing")
	var landed: bool = await wait_until(func() -> bool: return boss.boss.phase == BossBrain.Phase.HUNT, 8.0)
	assert_true(landed, "the entrance ends and he fights")
	assert_true(map.player.input_enabled)
	assert_gt(run.director.queue.size() + run.director.alive() - 1, 0, "with escorts")
	# Beat him, execute him, clear the escorts.
	run.director.queue.clear()
	boss.die(null, &"chest")
	assert_true(boss.alive and boss.boss.is_down(), "on his knee")
	await wait_physics_frames(5)
	assert_true(run.director.in_wave, "the wave isn't over while he kneels")
	boss.boss.execution.script_start()
	await wait_until(func() -> bool: return boss.boss.execution.done, 9.0)
	assert_false(boss.alive)
	_kill_all(run)
	await wait_until(func() -> bool: return run.drop_screen.visible, 8.0)
	assert_true(run.drop_screen.visible, "the boss drop")
	var o: RunState.Offer = run.drop_screen.offers[0]
	assert_eq(o.item.id(), &"gx4_gauss_arm", "his Gauss arm")
	assert_eq(o.mark, 1)
	gut.p("boss drop: %s (%d offers)" % [o.title(), run.drop_screen.offers.size()])
	run.drop_screen.take()
	assert_true(map.player.loadout.has_part(&"gx4_gauss_arm"), "on the body")


## Playtest 2026-11-15: the last Blue Lantern of wave 1 lost his gun and ran
## (nothing gives it back), still counted as fighting: the wave never ended.
func test_a_man_who_lost_his_gun_does_not_hold_up_the_wave() -> void:
	var run: SurvivalRun = await _start()
	await wait_until(func() -> bool: return run.director.in_wave and run.director.queue.is_empty(), 15.0)
	var last: Enemy
	for e: Enemy in run.director.enemies:
		if is_instance_valid(e) and e.alive:
			if last == null:
				last = e
			else:
				e.die(null, &"chest")
	assert_not_null(last)
	last.has_gun = false
	last.body.drop_gun(Vector3.UP)
	last._enter(Enemy.State.FLEE)
	assert_true(last.out_of_fight(), "unarmed and running: out of the fight")
	assert_eq(run.director.fighting(), 0)
	await wait_until(func() -> bool: return run.drop_screen.visible, 6.0)
	assert_true(run.drop_screen.visible, "the wave ended")
	assert_false(is_instance_valid(last) and last.is_inside_tree() and not last.is_queued_for_deletion(), "he's cleared away with the wave")
	# Still armed, he's only rattled: he comes back, so he still counts.
	var e2: Enemy = Enemy.new()
	e2.config = load("res://data/enemies/blue_lantern.tres") as EnemyConfig
	map.add_child(e2)
	e2._enter(Enemy.State.FLEE)
	assert_false(e2.out_of_fight(), "armed and fleeing: still in it")
	e2.queue_free()


## The last of a wave who lost the operative is told where he is; one who
## stays lost (stuck, or fallen off the map) comes back in at a spawn point.
func test_a_lost_straggler_is_sent_back_in() -> void:
	var run: SurvivalRun = await _start()
	var d: SurvivalDirector = run.director
	await wait_until(func() -> bool: return d.in_wave and d.queue.is_empty(), 15.0)
	var last: Enemy
	for e: Enemy in d.enemies:
		if is_instance_valid(e) and e.alive:
			if last == null:
				last = e
			else:
				e.die(null, &"chest")
	assert_not_null(last)
	var you: Vector3 = map.player.global_position
	# Lost: hasn't seen the operative for straggler_hunt_after s.
	last.sees_player = false
	last.last_known = you + Vector3(30, 0, 30)
	d.watch_stragglers(cfg.straggler_hunt_after)
	assert_almost_eq(last.last_known.distance_to(you), 0.0, 0.01, "told where he is")
	assert_eq(last.awareness, 1.0)
	# Stuck somewhere out of sight (just off a hidden spawn point) for straggler_move_after s.
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	var eye: Vector3 = map.player.camera().global_position
	var stuck: Vector3 = Vector3.INF
	for p: Vector3 in d.spawn_points:
		var q: Vector3 = p + Vector3(0.6, 0.0, 0.0)
		if not RollingSpawner.sees(space, eye, q) and _nearest_spawn(d, q) > 0.5:
			stuck = q
			break
	assert_ne(stuck, Vector3.INF, "a hidden spot")
	last.global_position = stuck
	last.sees_player = false
	d.watch_stragglers(cfg.straggler_move_after)
	assert_lt(_nearest_spawn(d, last.global_position), 0.1, "back in at a spawn point")
	# Fallen out of the map: back at once.
	last.global_position = Vector3(0, -40.0, 0)
	last.sees_player = true
	d.watch_stragglers(0.5)
	assert_gt(last.global_position.y, -1.0, "a fall out of the map brings him straight back")
	assert_eq(d.fighting(), 1, "still the one man left")


func _nearest_spawn(d: SurvivalDirector, at: Vector3) -> float:
	var near: float = INF
	for p: Vector3 in d.spawn_points:
		near = minf(near, Vector2(p.x, p.z).distance_to(Vector2(at.x, at.z)))
	return near
