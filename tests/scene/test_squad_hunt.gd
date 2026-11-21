extends GutTest
## The squad hunts and works together (owner, 2026-11-16; docs/design.md
## §5.6a), on the Chinatown docks: a lone man who lost the operative comes
## for him anyway, the lookouts phone in where he is, contact splits the
## gunmen into pinners and flankers, a pinner keeps firing where he ducked,
## and the HUD marks the last man of a wave.

var map: ChinatownMap
var hunt: HuntConfig = preload("res://data/enemies/hunt.tres")


func before_each() -> void:
	map = (load("res://src/levels/chinatown/chinatown.tscn") as PackedScene).instantiate() as ChinatownMap
	map.autostart_spawns = false
	add_child_autofree(map)
	await wait_physics_frames(20)
	map.player.invulnerable = true


## `n` men in, nobody else coming.
func _spawn(n: int) -> Array[Enemy]:
	var c: RollingSpawnConfig = map.wave_mode.config.duplicate() as RollingSpawnConfig
	c.start_count = n
	c.low_water = 0
	c.hatchet_man_weight = 0.0
	c.attack_dog_weight = 0.0  # the men's tactics; dogs aren't in the squad
	map.wave_mode.config = c
	map.wave_mode.start()
	await wait_until(func() -> bool: return map.wave_mode.spawned_total >= n, c.spawn_gap * n + 4.0)
	await wait_physics_frames(2)
	return map.wave_mode.enemies.duplicate()


func test_the_squad_hunts_in_wave_modes() -> void:
	await _spawn(1)
	assert_not_null(map.wave_mode.squad.hunt, "the docks squad hunts")


func test_a_lost_straggler_comes_to_you() -> void:
	var men: Array[Enemy] = await _spawn(1)
	var e: Enemy = men[0]
	# Make him a straggler who forgot about you: idle, unaware, no idea where you are.
	e._enter(Enemy.State.IDLE)
	e.awareness = 0.0
	e.last_known = Vector3.INF
	e._stop()
	var start: float = e.global_position.distance_to(map.player.global_position)
	var found: bool = false
	var t: float = 0.0
	while t < 25.0:
		await wait_seconds(0.5)
		t += 0.5
		if e.sees_player or e.state == Enemy.State.COMBAT:
			found = true
			break
	var d: float = e.global_position.distance_to(map.player.global_position)
	gut.p("straggler: %.0f m -> %.0f m in %.1f s, %s, tips %d" % [start, d, t, e.state_name(), map.wave_mode.squad.tips])
	assert_gt(map.wave_mode.squad.tips, 0, "the lookouts phoned it in")
	assert_ne(e.state, Enemy.State.IDLE, "he doesn't stand around")
	assert_true(found or d < start - 10.0, "he found you or came a long way toward you")


func test_lookout_tips_land_near_him() -> void:
	await _spawn(2)
	var sq: Squad = map.wave_mode.squad
	for e: Enemy in sq.members:
		e.sees_player = false
	sq.seen_at = sq.clock - 100.0
	sq.tip_at = sq.clock - 100.0
	var before: int = sq.tips
	await wait_physics_frames(2)
	assert_eq(sq.tips, before + 1, "one tip")
	assert_lt(Squad._flat(sq.intel - map.player.global_position).length(), hunt.intel_noise + 0.1, "within the noise of where he is")
	for e: Enemy in sq.members:
		if e.state in [Enemy.State.ALERT, Enemy.State.COMBAT]:
			assert_lt(Squad._flat(e.last_known - sq.intel).length(), 4.0, "everyone heads for the tip")


func test_contact_splits_them_into_pinners_and_flankers() -> void:
	var men: Array[Enemy] = await _spawn(5)
	var sq: Squad = map.wave_mode.squad
	for e: Enemy in men:
		e._enter(Enemy.State.COMBAT)
	sq.seen_at = sq.clock
	sq.intel = map.player.global_position
	sq.assign_roles()
	var pins: Array[Enemy] = []
	var flanks: Array[Enemy] = []
	var gunmen: int = 0
	for e: Enemy in men:
		if e.melee == null:
			gunmen += 1
		if e.squad_role == Squad.Role.PIN:
			pins.append(e)
		elif e.squad_role == Squad.Role.FLANK:
			flanks.append(e)
	gut.p("gunmen %d: %d pin, %d flank" % [gunmen, pins.size(), flanks.size()])
	if gunmen < 2:
		pending("this spawn rolled mostly melee men")
		return
	assert_gt(pins.size(), 0, "someone pins")
	assert_lte(pins.size(), hunt.pin_count)
	assert_gt(flanks.size(), 0, "someone flanks")
	assert_lte(flanks.size(), gunmen / 2, "never more than half")
	var at: Vector3 = map.player.global_position
	var axis: Vector3 = Vector3.ZERO
	for e: Enemy in pins:
		axis += Squad._flat(e.global_position - at).normalized()
	for e: Enemy in flanks:
		var off: float = rad_to_deg(axis.angle_to(Squad._flat(e.flank_target - at)))
		assert_gt(off, 50.0, "the flank point is round his side (%.0f° off the pin line)" % off)
	# No contact for a while: roles go, they hunt instead.
	sq.seen_at = sq.clock - 100.0
	sq.assign_roles()
	for e: Enemy in men:
		assert_eq(e.squad_role, Squad.Role.NONE)


func test_a_flanker_runs_for_his_flank_point() -> void:
	var men: Array[Enemy] = await _spawn(1)
	var e: Enemy = men[0]
	if e.melee != null:
		pending("rolled a melee man")
		return
	e._enter(Enemy.State.COMBAT)
	var to: Vector3 = Squad._flat(map.player.global_position - e.global_position)
	e.flank_target = map.wave_mode.squad._scatter(e.global_position + to.normalized().rotated(Vector3.UP, PI * 0.5) * 6.0, 0.0)
	e.set_squad_role(Squad.Role.FLANK)
	var d0: float = e.global_position.distance_to(e.flank_target)
	# Hold the role still for the test: re-assigning would hand him PUSH.
	map.wave_mode.squad.hunt = hunt.duplicate() as HuntConfig
	map.wave_mode.squad.hunt.role_interval = 999.0
	map.wave_mode.squad._role_timer = 999.0
	await wait_seconds(2.5)
	var d1: float = e.global_position.distance_to(e.flank_target)
	gut.p("flank: %.1f -> %.1f m, role %d" % [d0, d1, e.squad_role])
	assert_true(d1 < d0 - 2.0 or e.squad_role == Squad.Role.PUSH, "ran for it (or got there and pushed)")


func test_a_pinner_fires_where_he_ducked() -> void:
	var men: Array[Enemy] = await _spawn(1)
	var e: Enemy = men[0]
	if e.melee != null:
		pending("rolled a melee man")
		return
	var shots: Array[Vector3] = []
	var cb: Callable = func(shooter: Node, _o: Vector3, dir: Vector3) -> void:
		if shooter == e:
			shots.append(dir)
	EventBus.shot_fired.connect(cb)
	e._enter(Enemy.State.COMBAT)
	e.set_squad_role(Squad.Role.PIN)
	e.sees_player = false
	e._unseen_for = 1.0
	e._rounds_this_engagement = 3
	e.last_known = map.player.global_position
	e._shot_timer = 0.0
	e._reloading = 0.0
	e._try_fire(map.player, 0.016)
	assert_eq(shots.size(), 1, "a round at where he went")
	# A man with no role doesn't fire at nothing.
	e.set_squad_role(Squad.Role.NONE)
	e._shot_timer = 0.0
	e._try_fire(map.player, 0.016)
	assert_eq(shots.size(), 1)
	# And a pinner stops once he's been gone long enough.
	e.set_squad_role(Squad.Role.PIN)
	e._unseen_for = hunt.pin_fire_time + 1.0
	e._shot_timer = 0.0
	e._try_fire(map.player, 0.016)
	assert_eq(shots.size(), 1)
	EventBus.shot_fired.disconnect(cb)


func test_the_last_one_runs_out_of_places_to_hide() -> void:
	var men: Array[Enemy] = await _spawn(1)
	var e: Enemy = men[0]
	e._enter(Enemy.State.COMBAT)
	e.morale = 0.05
	e._enter(Enemy.State.FLEE)
	await wait_seconds(hunt.cornered_after + 1.5)
	assert_eq(e.state, Enemy.State.COMBAT, "the last man turns back")


func test_the_last_hostile_is_marked() -> void:
	var men: Array[Enemy] = await _spawn(2)
	# The Sandbox counter would keep overwriting the wave banner.
	map.wave_mode.running = false
	var hud: CombatHud = map.combat_hud
	EventBus.wave_changed.emit(3, 2)
	await wait_seconds(0.4)
	assert_eq(hud.marked_hostiles().size(), 0, "two left: no marker (mark_when_left = %d)" % hunt.mark_when_left)
	assert_false(hud.marker().visible)
	men[1].die(null, &"chest")
	EventBus.wave_changed.emit(3, 1)
	await wait_seconds(0.4)
	assert_eq(hud.marked_hostiles(), [men[0]] as Array[Enemy], "the last one is marked")
	assert_true(hud.marker().visible)
	# Behind you and to your left: the arrow sits low on the left of the screen.
	var e: Enemy = men[0]
	e.passive = true
	var cam: Camera3D = map.player.camera()
	var back: Vector3 = cam.global_basis.z
	var left: Vector3 = -cam.global_basis.x
	e.global_position = map.player.global_position + Squad._flat(back * 10.0 + left * 4.0)
	await wait_physics_frames(2)
	var vp: Vector2 = hud.marker().get_viewport_rect().size
	var where: Array = hud.marker().place(e, vp)
	gut.p("marker at %s of %s, on screen %s" % [where[0], vp, where[1]])
	var on_screen: bool = where[1]
	assert_false(on_screen, "off screen: an edge arrow")
	var p: Vector2 = where[0]
	assert_lt(p.x, vp.x * 0.5, "on the left")
	assert_gt(p.y, vp.y * 0.5, "low: he's behind you")
	# In front of you: a marker over him.
	e.global_position = map.player.global_position + Squad._flat(-cam.global_basis.z * 12.0)
	await wait_physics_frames(2)
	where = hud.marker().place(e, vp)
	on_screen = where[1]
	assert_true(on_screen, "on screen: over his head")
	EventBus.wave_changed.emit(3, 0)
	await wait_seconds(0.4)
	assert_false(hud.marker().visible, "wave over: gone")



func test_every_spawn_point_has_a_way_to_you() -> void:
	await wait_until(func() -> bool: return map.spawns_fixed >= 0, 10.0)
	gut.p("spawn points moved onto the connected navmesh: %d" % map.spawns_fixed)
	assert_gt(map.spawn_points.size(), 15, "the map keeps its spawns")
	var m: RID = map.get_world_3d().navigation_map
	var home: Vector3 = NavigationServer3D.map_get_closest_point(m, map.player_start)
	for sp: Vector3 in map.spawn_points:
		var path: PackedVector3Array = NavigationServer3D.map_get_path(m, NavigationServer3D.map_get_closest_point(m, sp), home, true)
		assert_gt(path.size(), 0)
		assert_lt(path[path.size() - 1].distance_to(home), 1.0, "a path from %s to the player start" % sp)


func test_a_stuck_man_is_moved_out_of_sight() -> void:
	var men: Array[Enemy] = await _spawn(1)
	var e: Enemy = men[0]
	# On the moored boat: no way off it.
	var boat: Vector3 = Vector3(-20.6, -0.4, 41.1)
	e.global_position = boat
	e.velocity = Vector3.ZERO
	e._enter(Enemy.State.ALERT)
	e.last_known = map.player.global_position
	e._go(e.last_known)
	await wait_seconds(hunt.stuck_after + 4.0)
	gut.p("stuck man now at %s (%.1f m from the boat), relocations %d" % [e.global_position, e.global_position.distance_to(boat), map.wave_mode.squad.relocations])
	assert_gt(map.wave_mode.squad.relocations, 0, "moved")
	assert_gt(e.global_position.distance_to(boat), 3.0, "off the boat")


func test_they_come_in_packs_and_only_two_hunt() -> void:
	var men: Array[Enemy] = await _spawn(7)
	var sq: Squad = map.wave_mode.squad
	sq.update_packs()
	var packs: Dictionary = {}
	for e: Enemy in men:
		packs[e.pack] = packs.get(e.pack, 0) + 1
	assert_eq(packs.size(), 3, "7 men: packs of 3, 3 and 1")
	var hunting: int = 0
	for k: int in packs.keys():
		if sq.is_hunting(k):
			hunting += 1
	assert_eq(hunting, hunt.hunting_packs, "only two packs hunt; the third holds off")
