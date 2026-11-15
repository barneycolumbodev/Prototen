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
