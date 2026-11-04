extends GutTest
## Chinatown docks map: loads, has solid ground and walls, and the rolling
## spawn rule (8 at the start, 3 more whenever fewer than 4 are fighting,
## always out of the player's sight) holds.

var map: ChinatownMap
var cfg: RollingSpawnConfig


func before_all() -> void:
	cfg = load("res://data/levels/chinatown_spawns.tres") as RollingSpawnConfig


func before_each() -> void:
	map = (load("res://src/levels/chinatown/chinatown.tscn") as PackedScene).instantiate() as ChinatownMap
	map.autostart_spawns = false
	add_child_autofree(map)
	await wait_physics_frames(20)


func test_config_matches_the_owners_rule() -> void:
	assert_eq(cfg.start_count, 8)
	assert_eq(cfg.low_water, 4)
	assert_eq(cfg.batch, 3)


func test_batch_rule() -> void:
	assert_true(RollingSpawner.wants_batch(3, 0, cfg), "3 fighting: send more")
	assert_true(RollingSpawner.wants_batch(0, 0, cfg))
	assert_false(RollingSpawner.wants_batch(4, 0, cfg), "4 fighting: not yet")
	assert_false(RollingSpawner.wants_batch(2, 3, cfg), "a batch is already on its way")


func test_map_builds() -> void:
	assert_gt(map.spawn_points.size(), 12, "spawn points")
	var shapes: int = 0
	for b: StaticBody3D in map.static_bodies.values():
		shapes += b.get_child_count()
	assert_gt(shapes, 300, "colliders")
	var meshes: Array[Node] = map.map_root.find_children("*", "MeshInstance3D", true, false)
	assert_gt(meshes.size(), 10, "map chunks")
	for n: Node in meshes:
		var mi: MeshInstance3D = n as MeshInstance3D
		assert_eq(mi.layers, ChinatownMap.MAP_LAYER)
		assert_not_null(mi.material_override)


func test_player_stands_on_the_quay() -> void:
	await wait_physics_frames(30)
	assert_true(map.player.is_on_floor())
	assert_almost_eq(map.player.global_position.y, 0.0, 0.1)


func test_walls_stop_bullets_but_clip_walls_do_not() -> void:
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	# Through the warehouse's north wall (Blender y = 2): world layer
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(
		ChinatownMap.b2g([-30.0, 6.0, 1.2]), ChinatownMap.b2g([-30.0, -2.0, 1.2]), Ballistics.LAYER_WORLD)
	assert_false(space.intersect_ray(q).is_empty(), "warehouse wall blocks bullets")
	# Out over the water: only a clip wall, invisible to bullets
	var w: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(
		ChinatownMap.b2g([0.0, -20.0, 1.5]), ChinatownMap.b2g([0.0, -40.0, 1.5]), Ballistics.LAYER_WORLD)
	assert_true(space.intersect_ray(w).is_empty(), "nothing solid over the water")
	w.collision_mask = Ballistics.LAYER_CLIP
	assert_false(space.intersect_ray(w).is_empty(), "the clip wall keeps people out of the water")


func test_spawns_start_with_eight_out_of_sight() -> void:
	var seen: Array[bool] = []
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	map.wave_mode.spawned.connect(func(e: Enemy) -> void:
		seen.append(RollingSpawner.sees(space, map.player.camera().global_position, e.global_position)))
	map.wave_mode.start()
	await wait_seconds(cfg.spawn_gap * cfg.start_count + 2.0)
	assert_eq(map.wave_mode.spawned_total, cfg.start_count)
	assert_eq(seen.size(), cfg.start_count)
	assert_false(true in seen, "no one appeared in plain sight")
	for e: Enemy in map.wave_mode.enemies:
		assert_gt(e.global_position.distance_to(map.player.global_position), cfg.min_distance - 0.5)


func test_three_more_when_fewer_than_four_fight() -> void:
	map.wave_mode.start()
	await wait_seconds(cfg.spawn_gap * cfg.start_count + 1.5)
	assert_eq(map.wave_mode.spawned_total, 8)
	# take five out of the fight: three are left, below the low-water mark of four
	var gone: int = 0
	for e: Enemy in map.wave_mode.enemies.duplicate():
		if gone == 5:
			break
		map.wave_mode.squad.members.erase(e)
		map.wave_mode.enemies.erase(e)
		e.queue_free()
		gone += 1
	await wait_seconds(cfg.spawn_gap * cfg.batch + 1.5)
	assert_eq(map.wave_mode.spawned_total, 11, "one batch of three")
	assert_eq(map.wave_mode.fighting(), 6)


func test_enemies_find_their_way_to_the_player() -> void:
	map.player.invulnerable = true
	map.wave_mode.start()
	await wait_seconds(cfg.spawn_gap * cfg.start_count + 1.0)
	assert_gt(map.nav_region.navigation_mesh.get_polygon_count(), 100, "navmesh baked")
	var start: Dictionary[Enemy, float] = {}
	for e: Enemy in map.wave_mode.enemies:
		start[e] = e.global_position.distance_to(map.player.global_position)
	await wait_seconds(14.0)
	var closer: int = 0
	var engaged: int = 0
	var report: String = ""
	for e: Enemy in start:
		if not is_instance_valid(e):
			continue
		var d: float = e.global_position.distance_to(map.player.global_position)
		report += " %s %.0f→%.0f m;" % [e.state_name(), start[e], d]
		if d < start[e] - 3.0:
			closer += 1
		if e.state_name() in ["COMBAT", "combat"]:
			engaged += 1
	gut.p("enemies:" + report)
	assert_gt(closer + engaged, start.size() / 2, "most close in or engage")
