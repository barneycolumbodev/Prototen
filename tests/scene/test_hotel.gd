extends GutTest
## The Golden Dragon hotel (map 2, docs/design.md §7.2): loads indoors, the
## grand stairs carry people up to the gallery, the navigation reaches both
## storeys, the enemy only comes from the lifts and the street, and a car
## chimes and opens to let out whoever spawned in it.

var map: HotelMap


func before_each() -> void:
	map = (load("res://src/levels/hotel/hotel.tscn") as PackedScene).instantiate() as HotelMap
	map.autostart_spawns = false
	add_child_autofree(map)
	await wait_physics_frames(20)


func test_map_builds_indoors() -> void:
	var meshes: Array[Node] = map.map_root.find_children("*", "MeshInstance3D", true, false)
	assert_gt(meshes.size(), 20, "map meshes")
	assert_false(map.atmos.config.outdoor, "indoor atmosphere")
	assert_null(map.atmos.rain, "no rain indoors")
	assert_eq(map.lifts.size(), 6, "six lifts")


func test_spawns_are_lifts_and_the_street() -> void:
	var lifts: int = 0
	var street: int = 0
	for m: Dictionary in map.layout["markers"]:
		if ChinatownMap.fstr(m, "kind") != "spawn":
			continue
		var name: String = ChinatownMap.fstr(m, "name")
		if name.begins_with("lift_"):
			lifts += 1
		elif name.begins_with("drive_"):
			street += 1
		else:
			fail_test("unexpected spawn %s" % name)
	assert_eq(lifts, 12, "two places in each of six cars")
	assert_eq(street, 6, "six out on the drive")


func test_player_starts_on_the_floor_in_the_entrance_hall() -> void:
	await wait_physics_frames(20)
	assert_true(map.player.is_on_floor(), "standing")
	assert_almost_eq(map.player.global_position.y, 0.0, 0.2)


func test_grand_stairs_are_walkable_ramps() -> void:
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	# Halfway up the west stair (Blender y 4: bottom at y 10, top at y -2, 4.5 m up).
	var p: Vector3 = ChinatownMap.b2g([-14.5, 4.0, 8.0])
	var res: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(p, p + Vector3.DOWN * 10.0, Ballistics.LAYER_WORLD))
	assert_false(res.is_empty(), "something under the stair")
	var hit: Vector3 = res["position"]
	assert_almost_eq(hit.y, 4.5 * 6.0 / 12.0, 0.35, "ramp surface halfway up")


func test_navigation_reaches_the_gallery() -> void:
	await wait_seconds(1.5)
	var m: RID = map.get_world_3d().navigation_map
	var from: Vector3 = NavigationServer3D.map_get_closest_point(m, map.player_start)
	var gallery: Vector3 = ChinatownMap.b2g([0.0, 18.0, 4.5])
	var path: PackedVector3Array = NavigationServer3D.map_get_path(m, from, gallery, true)
	assert_false(path.is_empty())
	assert_almost_eq(path[path.size() - 1].y, 4.5, 0.4, "path ends up on the gallery")


func test_a_lift_opens_for_whoever_spawned_in_it() -> void:
	var lift: Lift = map.lifts[2]
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	e.passive = true
	map.add_child(e)
	e.global_position = lift.car_centre + Vector3.UP * 0.05
	assert_true(lift.contains(e.global_position), "he's in the car")
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	var eye: Vector3 = lift.door_centre + (lift.door_centre - lift.car_centre).normalized() * 6.0 + Vector3.UP * 1.6
	assert_false(RollingSpawner.sees(space, eye, e.global_position), "shut doors hide the car")
	map._arrived(e)
	assert_eq(lift.state, Lift.State.ARRIVING, "the chime")
	await wait_seconds(Lift.CHIME_TO_OPEN + Lift.OPEN_TIME + 0.2)
	assert_true(lift.is_open(), "doors open")
	assert_true(RollingSpawner.sees(space, eye, e.global_position), "and you can see him")
	e.queue_free()


func test_survival_runs_on_the_hotel_and_the_lifts_deliver() -> void:
	var cfg: SurvivalConfig = preload("res://data/run/survival.tres")
	var ghost: Doctrine = cfg.doctrine_named("Ghost")
	await map.start_survival(ghost, cfg.starter_weapons[0], ghost.starter_actives[0], 7)
	var run: SurvivalRun = map.survival
	assert_not_null(run)
	await wait_until(func() -> bool: return run.director.spawned_total >= 3, 20.0)
	assert_gte(run.director.spawned_total, 3, "men came in")
	var by_lift: int = 0
	for e: Enemy in run.director.enemies:
		if is_instance_valid(e) and map.lift_at(e.global_position) != null:
			by_lift += 1
	var calling: int = 0
	for l: Lift in map.lifts:
		if l.state != Lift.State.CLOSED:
			calling += 1
	assert_true(by_lift == 0 or calling > 0, "a man in a car has his lift coming")


func test_glass_breaks_when_shot() -> void:
	assert_gt(map.glass.count(), 60, "panes along the gallery and the front")
	# A balustrade pane on the gallery (under a metre tall) with a clear line to it.
	var space: PhysicsDirectSpaceState3D = map.get_world_3d().direct_space_state
	var i: int = -1
	var at: Vector3
	var from: Vector3
	for k: int in map.glass.count():
		var b: GlassPanes.Pane = map.glass.bodies[k]
		if (b.get_child(0) as CollisionShape3D).shape.get("size").y > 1.0:
			continue
		for side: float in [1.0, -1.0]:
			var f: Vector3 = b.global_position + b.global_basis.z * 3.0 * side
			var r: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(f, b.global_position, Ballistics.LAYER_WORLD))
			if not r.is_empty() and r["collider"] == b:
				i = k
				at = b.global_position
				from = f
				break
		if i >= 0:
			break
	assert_gte(i, 0, "a pane in the open")
	var pane: GlassPanes.Pane = map.glass.bodies[i]
	var n: Vector3 = (from - at).normalized()
	Ballistics.fire(preload("res://data/weapons/pistol_57.tres"), from, (at - from).normalized(), map.player)
	await wait_physics_frames(4)
	assert_true(map.glass.is_broken(i), "the pane burst")
	assert_gte(map.glass.broken, 1, "(the round may go on and burst more beyond it)")
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, at - n * 0.3, Ballistics.LAYER_WORLD)
	q.exclude = []
	var res: Dictionary = space.intersect_ray(q)
	var blocker: Object = null if res.is_empty() else res["collider"]
	assert_ne(blocker, pane, "nothing left to stop a body there")
