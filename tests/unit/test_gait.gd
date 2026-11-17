extends GutTest
## Gait (src/player/gait.gd, 2026-11-17): footfalls tied to ground covered,
## the head riding the stride, heel strikes and weight shift, the gun's lag.

const DT: float = 1.0 / 60.0
var cfg: MovementConfig


func before_each() -> void:
	cfg = load("res://data/player/movement_default.tres") as MovementConfig


func _walk(g: Gait, vel: Vector3, seconds: float, on_floor: bool = true) -> Array[Vector2]:
	var falls: Array[Vector2] = []
	var t: float = 0.0
	while t < seconds - 0.0001:
		g.update(DT, vel, on_floor, false)
		falls.append_array(g.footfalls)
		t += DT
	return falls


func test_steps_are_tied_to_ground_covered() -> void:
	var g: Gait = Gait.new(cfg)
	var falls: Array[Vector2] = _walk(g, Vector3(0, 0, -cfg.walk_speed), 4.0)
	var expected: float = cfg.walk_speed * 4.0 / g.stride(cfg.walk_speed)
	assert_almost_eq(float(falls.size()), expected, 1.01, "%d steps over %.1f m (stride %.2f m)" % [falls.size(), cfg.walk_speed * 4.0, g.stride(cfg.walk_speed)])
	for i: int in range(1, falls.size()):
		assert_ne(falls[i].x, falls[i - 1].x, "left, right, left...")


func test_cadence_rises_gently_from_a_walk_to_a_sprint() -> void:
	var g: Gait = Gait.new(cfg)
	var walk: float = g.cadence(cfg.walk_speed)
	var sprint: float = g.cadence(cfg.sprint_speed)
	assert_between(walk, 2.0, 3.0, "walk %.2f steps/s" % walk)
	assert_between(sprint, walk * 1.1, 3.6, "sprint %.2f steps/s" % sprint)
	assert_gt(g.stride(cfg.sprint_speed), g.stride(cfg.walk_speed), "longer strides at a run")


func test_no_steps_in_the_air_or_standing() -> void:
	var g: Gait = Gait.new(cfg)
	assert_eq(_walk(g, Vector3(0, 0, -9.0), 1.0, false).size(), 0, "airborne")
	assert_eq(_walk(g, Vector3.ZERO, 1.0).size(), 0, "standing")


func test_head_is_lowest_at_the_heel_strike() -> void:
	var g: Gait = Gait.new(cfg)
	var v: Vector3 = Vector3(0, 0, -cfg.walk_speed)
	_walk(g, v, 1.5)  # up to full intensity
	var at_strike: float = INF
	var mid_stride: float = -INF
	for i: int in 120:
		g.update(DT, v, true, false)
		var frac: float = g.phase - floorf(g.phase)
		var y: float = g.head_offset().y - g.impact.value.y
		if frac < 0.06 or frac > 0.94:
			at_strike = minf(at_strike, y)
		if absf(frac - 0.5) < 0.06:
			mid_stride = maxf(mid_stride, y)
	assert_lt(at_strike, mid_stride - cfg.bob_height * 0.5, "the stride: low at the strike (%.4f), high mid-stride (%.4f)" % [at_strike, mid_stride])


func test_each_heel_strike_lands_with_weight() -> void:
	var g: Gait = Gait.new(cfg)
	var v: Vector3 = Vector3(0, 0, -cfg.walk_speed)
	while true:
		g.update(DT, v, true, false)
		if not g.footfalls.is_empty():
			break
	var lowest: float = 0.0
	for i: int in 6:
		g.update(DT, v, true, false)
		lowest = minf(lowest, g.impact.value.y)
	assert_lt(lowest, -cfg.step_dip * 0.3, "the head dips after the strike (%.4f m)" % lowest)


func test_stopping_pitches_forward_and_starting_rocks_back() -> void:
	var g: Gait = Gait.new(cfg)
	var max_back: float = 0.0
	for i: int in 12:
		var v: Vector3 = Vector3(0, 0, -cfg.walk_speed * minf(float(i + 1) / 10.0, 1.0))
		g.update(DT, v, true, false)
		max_back = minf(max_back, g.head_rotation_deg().x - g.impact.value.z)
	assert_lt(max_back, -0.1, "pushing off rocks the head back (%.2f°)" % max_back)
	_walk(g, Vector3(0, 0, -cfg.walk_speed), 1.0)
	var max_fwd: float = 0.0
	for i: int in 20:
		var v2: Vector3 = Vector3(0, 0, -cfg.walk_speed * maxf(1.0 - float(i + 1) / 8.0, 0.0))
		g.update(DT, v2, true, false)
		max_fwd = maxf(max_fwd, g.head_rotation_deg().x - g.impact.value.z)
	assert_gt(max_fwd, 0.15, "a stop pitches the head forward (%.2f°)" % max_fwd)


func test_strafing_leans_into_it() -> void:
	var g: Gait = Gait.new(cfg)
	var lean: float = 0.0
	for i: int in 10:
		g.update(DT, Vector3(cfg.walk_speed * float(i + 1) / 10.0, 0, 0), true, false)
		lean = minf(lean, g.head_rotation_deg().z - g.roll_kick.value.z - sin(PI * g.phase) * cfg.bob_roll_deg * g.intensity)
	assert_lt(lean, -0.1, "speeding up to the right lowers the right side (%.2f°)" % lean)


func test_the_gun_trails_the_body_and_heavier_guns_trail_more() -> void:
	var g: Gait = Gait.new(cfg)
	for i: int in 8:
		g.update(DT, Vector3(0, 0, -cfg.walk_speed * float(i + 1) / 8.0), true, false)
	var light: Vector3 = g.gun_offset(0.8)
	var heavy: Vector3 = g.gun_offset(1.7)
	assert_gt(light.z, 0.0, "pushing off: the gun comes back toward you (%.4f m)" % light.z)
	assert_gt(heavy.z, light.z * 1.5, "an MG42 swings more than a pistol")
	assert_lt(g.gun_rotation_deg(1.0).z, 0.0, "and its muzzle dips")


func test_everything_settles_when_you_stand_still() -> void:
	var g: Gait = Gait.new(cfg)
	_walk(g, Vector3(0, 0, -cfg.sprint_speed), 2.0)
	_walk(g, Vector3.ZERO, 2.0)
	assert_lt(g.head_offset().length(), 0.001, "head back at rest")
	assert_lt(g.head_rotation_deg().length(), 0.02, "no lean left")
	assert_lt(g.gun_offset(1.0).length(), 0.001, "gun back at rest")


func test_landing_restarts_the_stride_and_nods() -> void:
	var g: Gait = Gait.new(cfg)
	g.land(10.0)
	var nod: float = 0.0
	for i: int in 10:
		g.update(DT, Vector3.ZERO, true, false)
		nod = maxf(nod, g.head_rotation_deg().x)
	assert_gt(nod, cfg.land_pitch_deg * 0.4, "a nod on landing (%.2f°)" % nod)


func test_footstep_banks_follow_the_surface() -> void:
	var lib: SurfaceLibrary = SurfaceLibrary.shared()
	assert_eq(Player.footstep_bank(lib.get_material(&"concrete")), &"step_concrete")
	assert_eq(Player.footstep_bank(lib.get_material(&"wood")), &"step_wood")
	assert_eq(Player.footstep_bank(lib.get_material(&"sheet_metal")), &"step_metal")
	for bank: StringName in [&"step_concrete", &"step_metal", &"step_wood", &"step_dirt", &"step_land", &"step_gear"]:
		assert_gt(Sfx.bank(bank).size(), 0, "%s has sounds" % bank)
