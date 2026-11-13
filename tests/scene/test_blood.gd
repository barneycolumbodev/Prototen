extends GutTest
## Blood as drops (docs/design.md §5.5; owner, 2026-11-11: "not simulated
## accurately, rather obnoxious light red clouds"). Drops fly on real paths,
## are traced against the level, and stain where and how they land.

var room: TestRoom
var player: Player
var m14: WeaponData = preload("res://data/weapons/m14p.tres")
var _gore: int
## A clear patch of the test room floor.
const SPOT: Vector3 = Vector3(-1.8, 0, 2.0)


func before_each() -> void:
	_gore = Settings.gore_level
	Settings.gore_level = Gore.Level.MAXIMUM
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(20)
	Gore.clear()


func after_each() -> void:
	Settings.gore_level = _gore
	Engine.time_scale = 1.0
	Gore.clear()


## A wall across the lane at z = `z`, facing +Z.
func _wall(z: float) -> void:
	var wall: StaticBody3D = StaticBody3D.new()
	wall.collision_layer = Ballistics.LAYER_WORLD
	var cs: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(6, 4, 0.2)
	cs.shape = box
	wall.add_child(cs)
	room.add_child(wall)
	wall.global_position = Vector3(SPOT.x, 2.0, z - 0.1)
	await wait_physics_frames(2)


func _stain_basis(i: int) -> Basis:
	return Gore.stain_transform(i).basis


func test_there_are_no_particle_clouds_left() -> void:
	assert_eq(Gore.find_children("*", "CPUParticles3D", true, false).size(), 0, "blood is drops, not billboard clouds")
	assert_eq(Gore.find_children("*", "GPUParticles3D", true, false).size(), 0)
	Gore.mist(SPOT + Vector3.UP, Vector3.FORWARD, 2.0)
	assert_gt(Gore.drop_count(), 5, "a fine spray is small drops")
	assert_eq(Gore.drops.landings.size(), 0, "too fine to stain")


func test_a_drop_falls_to_the_floor_and_stains_it_there() -> void:
	var from: Vector3 = SPOT + Vector3(0, 1.5, 0)
	var flight: float = Gore.drops.emit(from, Vector3(1.0, 0, 0), 0.015, 0.1, true)
	assert_almost_eq(flight, sqrt(2.0 * 1.5 / 9.8), 0.06, "it takes as long as a fall from 1.5 m")
	assert_eq(Gore.splat_count(), 0, "nothing on the floor while it is in the air")
	assert_eq(Gore.drop_count(), 1)
	var l: BloodDrops.Landing = Gore.drops.landings[0]
	assert_almost_eq(l.point.y, 0.0, 0.01, "on the floor")
	assert_almost_eq(l.point.x, from.x + 1.0 * flight, 0.08, "carried along by its speed")
	assert_gt(l.normal.y, 0.9)
	await wait_seconds(flight + 0.15)
	assert_eq(Gore.splat_count(), 1, "the stain appears when it lands")
	assert_eq(Gore.drop_count(), 0, "and the drop is gone")
	var at: Vector3 = Gore.stain_transform(Gore.MAX_SPLATS).origin
	assert_lt(at.distance_to(l.point), 0.06, "where it came down")


func test_a_drop_thrown_at_a_wall_stains_the_wall() -> void:
	await _wall(0.0)
	var from: Vector3 = SPOT + Vector3(0, 1.5, 0)
	Gore.drops.emit(from, Vector3(0, 0.5, -8.0), 0.015, 0.1, true)
	var l: BloodDrops.Landing = Gore.drops.landings[0]
	assert_almost_eq(l.point.z, 0.0, 0.01, "on the wall, not the floor behind it")
	assert_gt(l.normal.z, 0.9)
	assert_gt(l.point.y, 1.2, "still at chest height when it gets there")


func test_the_stain_is_shaped_by_the_angle_it_lands_at() -> void:
	var from: Vector3 = SPOT + Vector3(0, 0.4, 0)
	# Straight down: round. Fast and flat along +X: long, pointing along +X.
	Gore.drops.emit(from + Vector3(0, 0, 1), Vector3(0, -1, 0), 0.015, 0.05, true)
	Gore.drops.emit(from, Vector3(9.0, 0, 0), 0.015, 0.05, true)
	await wait_seconds(0.5)
	assert_eq(Gore.splat_count(), 2)
	var round_stain: Basis = _stain_basis(Gore.MAX_SPLATS)
	var long_stain: Basis = _stain_basis(Gore.MAX_SPLATS + 1)
	assert_almost_eq(round_stain.x.length() / round_stain.y.length(), 1.0, 0.01, "square on: a round stain")
	assert_true(Gore.stain_cell(Gore.MAX_SPLATS) in Gore.CELLS_ROUND)
	assert_true(Gore.stain_cell(Gore.MAX_SPLATS + 1) in Gore.CELLS_LONG, "at an angle: a long one with a tail")
	assert_gt(long_stain.x.normalized().dot(Vector3.RIGHT), 0.95, "its tail points the way it was going")
	# Body length = quad x × 0.46, width = quad y × 0.22: longer than wide by 1/sin(angle).
	var length: float = long_stain.x.length() * 0.46
	var width: float = long_stain.y.length() * 0.22
	assert_gt(length / width, 2.0, "a flat impact makes a long stain (%.1f : 1)" % (length / width))


func test_a_big_stain_on_a_wall_runs_down_it() -> void:
	await _wall(0.0)
	Gore.drops.emit(SPOT + Vector3(0, 1.5, 0.5), Vector3(0, 0, -6.0), 0.03, 0.1, true, -INF, BloodDrops.MAX_FLIGHT, 0.4)
	await wait_seconds(0.7)
	assert_eq(Gore._big[2], 1, "the stain")
	assert_eq(Gore._spots[2], 1, "and a run under it")
	var run: Transform3D = Gore.stain_transform(Gore.MAX_SPLATS)
	assert_true(Gore.stain_cell(Gore.MAX_SPLATS) in Gore.CELLS_RUN)
	assert_gt(Gore.stain_run_time(Gore.MAX_SPLATS), 1.0, "it takes seconds to run")
	assert_gt(run.basis.y.normalized().dot(Vector3.UP), 0.99, "straight down the wall")
	assert_lt(run.origin.y, 1.5, "below where it hit")


func test_a_round_through_a_body_puts_blood_on_the_wall_behind() -> void:
	room.shooting_range.clear_targets()
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	e.passive = true
	room.add_child(e)
	e.position = SPOT + Vector3(0, 0, -1.0)
	e.face(0.0)
	await _wall(SPOT.z - 2.2)
	await wait_physics_frames(6)
	var at: Vector3 = e.body.chest_position()
	Ballistics.fire(m14, at + Vector3(0, 0, 5.0), Vector3(0, 0, -1), player)
	await wait_physics_frames(3)
	assert_gt(Gore.drop_count(), 8, "drops in the air")
	await wait_seconds(1.2)
	var on_wall: int = 0
	var on_floor: int = 0
	for i: int in Gore.MAX_SPLATS + Gore.MAX_SPOTS:
		var t: Transform3D = Gore.stain_transform(i)
		if t.basis.x.length() < 0.001:
			continue
		if absf(t.origin.z - (SPOT.z - 2.2)) < 0.02:
			on_wall += 1
		elif t.origin.y < 0.02:
			on_floor += 1
	assert_gt(on_wall, 0, "blood from the exit wound on the wall behind him")
	assert_gt(on_wall + on_floor, 2)


func test_a_stump_pumps_in_beats() -> void:
	room.shooting_range.clear_targets()
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	e.passive = true
	room.add_child(e)
	e.position = SPOT
	e.face(0.0)
	await wait_physics_frames(6)
	e.sever(&"upper_arm_L", Vector3(2, 2, 0), false)
	var before: int = Gore.drops.emitted
	# Count what leaves in each tenth of a second over two beats.
	var per_tenth: Array[int] = []
	for i: int in 9:
		var was: int = Gore.drops.emitted
		await wait_seconds(0.1)
		per_tenth.append(Gore.drops.emitted - was)
	assert_gt(Gore.drops.emitted - before, 15, "the stump bleeds")
	var most: int = 0
	var least: int = 9999
	for n: int in per_tenth:
		most = maxi(most, n)
		least = mini(least, n)
	assert_gt(most, least * 3 + 2, "in beats, not a steady flow: %s" % [per_tenth])
	await wait_seconds(1.0)
	assert_gt(Gore._spots[2], 0, "the stream marks the floor")


func test_slow_motion_slows_the_blood() -> void:
	var from: Vector3 = SPOT + Vector3(0, 1.5, 0)
	Engine.time_scale = 0.25
	var flight: float = Gore.drops.emit(from, Vector3.ZERO, 0.015, 0.1, true)
	var real_start: int = Time.get_ticks_msec()
	while Gore.splat_count() == 0 and Time.get_ticks_msec() - real_start < 5000:
		await wait_frames(1)
	var real: float = float(Time.get_ticks_msec() - real_start) / 1000.0
	Engine.time_scale = 1.0
	assert_gt(real, flight * 3.0, "at quarter speed the fall takes four times as long (%.2f s for a %.2f s fall)" % [real, flight])


func test_caps_hold() -> void:
	# Far more than fit, all in one frame: the trace budget runs out and the
	# rest fall to the floor under the wound instead (no rays).
	var rays: int = Gore.drops.rays_cast
	for i: int in 500:
		Gore.drops.emit(SPOT + Vector3(0, 1.0, 0), Vector3(randf_range(-3, 3), 2, randf_range(-3, 3)), 0.012, 0.5, true, 0.0)
	assert_lte(Gore.drop_count(), BloodDrops.MAX_DROPS)
	assert_lte(Gore.drops.rays_cast - rays, BloodDrops.RAYS_PER_FRAME, "one frame's traces stay inside the budget")
	assert_eq(Gore.drops.landings.size(), 500, "every drop still comes down somewhere")
	await wait_seconds(1.6)
	assert_lte(Gore.splat_count(), Gore.MAX_SPLATS + Gore.MAX_SPOTS)
	assert_eq(Gore._spots[2], Gore.MAX_SPOTS, "the ring is full, not over")


func test_gore_off_spills_nothing() -> void:
	Settings.gore_level = Gore.Level.OFF
	Gore.spray(SPOT + Vector3.UP, Vector3.UP, 1.0, 20)
	Gore.mist(SPOT + Vector3.UP, Vector3.UP, 1.0)
	Gore.spurt(SPOT + Vector3.UP, Vector3.UP, 3.0, 5, 1)
	Gore.drip(SPOT + Vector3.UP)
	Gore.splat(SPOT, Vector3.UP, 0.3)
	assert_eq(Gore.drop_count(), 0)
	assert_eq(Gore.splat_count(), 0)


## Owner, 2026-11-13: more punch the moment a round hits, clearest in RX-9
## slow motion: a burst at the entry, a fan out of the exit, bits of tissue.
func test_a_round_through_a_body_bursts_at_entry_and_exit() -> void:
	room.shooting_range.clear_targets()
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	e.passive = true
	room.add_child(e)
	e.position = SPOT + Vector3(0, 0, -1.0)
	e.face(0.0)
	await wait_physics_frames(6)
	var bursts: int = Gore.bursts_fx.emitted
	var at: Vector3 = e.body.chest_position()
	Ballistics.fire(m14, at + Vector3(0, 0, 5.0), Vector3(0, 0, -1), player)
	await wait_physics_frames(2)
	assert_eq(Gore.bursts_fx.emitted - bursts, 2, "one burst where it went in, one where it came out")
	assert_eq(Gore.bursts_fx.live_count(Gore.drops.clock), 2, "both showing")
	var chunks: int = 0
	for i: int in BloodDrops.MAX_DROPS:
		if roundi(Gore.drops.multimesh.get_instance_transform(i).basis.z.z) == BloodDrops.KIND_CHUNK:
			chunks += 1
	assert_gt(chunks, 0, "bits of tissue thrown out of the exit")
	await wait_seconds(0.4)
	assert_eq(Gore.bursts_fx.live_count(Gore.drops.clock), 0, "gone a fraction of a second later")


func test_the_burst_runs_on_game_time() -> void:
	Engine.time_scale = 0.25
	Gore.bursts_fx.emit(Gore.drops.clock, SPOT + Vector3.UP, Vector3.FORWARD, 0.3, 0.2, 0.04, true)
	var real_start: int = Time.get_ticks_msec()
	while Time.get_ticks_msec() - real_start < 300:
		await wait_frames(1)
	assert_eq(Gore.bursts_fx.live_count(Gore.drops.clock), 1, "at quarter speed a 0.2 s burst is still going after 0.3 s")
	Engine.time_scale = 1.0
	await wait_seconds(0.3)
	assert_eq(Gore.bursts_fx.live_count(Gore.drops.clock), 0)


func test_bursts_are_capped() -> void:
	for i: int in ImpactBursts.MAX_BURSTS * 3:
		Gore.bursts_fx.emit(Gore.drops.clock, SPOT + Vector3.UP, Vector3.FORWARD, 0.3, 0.5, 0.04, true)
	assert_eq(Gore.bursts_fx.live_count(Gore.drops.clock), ImpactBursts.MAX_BURSTS, "the oldest is reused")


## Impact particles (dust, sparks, splinters) were drawn about a metre
## across: a billboard particle material drops the particle's scale unless
## told to keep it. Found in the 2026-11-13 impact captures.
func test_impact_particles_keep_their_size() -> void:
	for kind: StringName in [&"dust", &"sparks", &"splinters", &"glass"]:
		var m: StandardMaterial3D = Fx._particle_material(kind)
		assert_true(m.billboard_keep_scale, "%s particles are drawn at their own size" % kind)
