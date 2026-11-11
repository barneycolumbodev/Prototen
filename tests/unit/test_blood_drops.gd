extends GutTest
## The flight of a blood drop (src/gore/blood_drops.gd): the closed-form path
## under gravity and linear drag that both the script and the shader use.


## Steps the same equations of motion numerically.
func _integrate(p0: Vector3, v0: Vector3, k: float, t: float) -> Vector3:
	var p: Vector3 = p0
	var v: Vector3 = v0
	var dt: float = 0.0002
	var steps: int = roundi(t / dt)
	for i: int in steps:
		v += (Vector3(0, -BloodDrops.GRAVITY, 0) - v * k) * dt
		p += v * dt
	return p


func test_the_path_is_the_solution_of_gravity_and_drag() -> void:
	for k: float in [0.1, 0.9, 6.0]:
		var p0: Vector3 = Vector3(1, 1.5, -2)
		var v0: Vector3 = Vector3(4, 2, -3)
		var want: Vector3 = _integrate(p0, v0, k, 0.6)
		var got: Vector3 = BloodDrops.position_at(p0, v0, k, 0.6)
		assert_lt(got.distance_to(want), 0.005, "drag %.1f: %s vs %s" % [k, got, want])


func test_velocity_is_the_paths_slope() -> void:
	var v0: Vector3 = Vector3(5, 3, 0)
	var a: Vector3 = BloodDrops.position_at(Vector3.ZERO, v0, 1.2, 0.3)
	var b: Vector3 = BloodDrops.position_at(Vector3.ZERO, v0, 1.2, 0.301)
	assert_lt(((b - a) / 0.001).distance_to(BloodDrops.velocity_at(v0, 1.2, 0.3005)), 0.01)


func test_without_much_drag_it_is_a_parabola() -> void:
	var p: Vector3 = BloodDrops.position_at(Vector3.ZERO, Vector3(3, 4, 0), 0.05, 0.5)
	assert_almost_eq(p.x, 1.5, 0.03)
	assert_almost_eq(p.y, 4.0 * 0.5 - 0.5 * 9.8 * 0.25, 0.03)


func test_a_fine_spray_stops_where_heavy_drops_carry_on() -> void:
	var fine: float = BloodDrops.drag_for(0.004, 3.2)
	var heavy: float = BloodDrops.drag_for(0.02, 0.9)
	assert_gt(fine, heavy * 5.0, "small drops feel the air far more")
	var v0: Vector3 = Vector3(6, 0, 0)
	var far_fine: float = BloodDrops.position_at(Vector3.ZERO, v0, fine, 0.6).x
	var far_heavy: float = BloodDrops.position_at(Vector3.ZERO, v0, heavy, 0.6).x
	assert_lt(far_fine, 0.7, "the spray hangs within arm's reach (%.2f m)" % far_fine)
	assert_gt(far_heavy, 2.5, "the heavy drop is across the room (%.2f m)" % far_heavy)


func test_time_to_the_floor() -> void:
	# Dropped from 1.5 m with almost no drag: sqrt(2h/g).
	var t: float = BloodDrops.time_to_height(Vector3(0, 1.5, 0), Vector3.ZERO, 0.05, 0.0, 3.0)
	assert_almost_eq(t, sqrt(2.0 * 1.5 / 9.8), 0.02)
	# Thrown upward it takes longer; never reaching it returns the life.
	assert_gt(BloodDrops.time_to_height(Vector3(0, 1.5, 0), Vector3(0, 3, 0), 0.05, 0.0, 3.0), t + 0.3)
	assert_eq(BloodDrops.time_to_height(Vector3(0, 1.5, 0), Vector3.ZERO, 0.05, -50.0, 1.0), 1.0)
