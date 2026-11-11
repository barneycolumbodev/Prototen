extends GutTest

var cfg: MovementConfig


func before_each() -> void:
	cfg = load("res://data/player/movement_default.tres") as MovementConfig


func test_augmented_baseline_is_fast() -> void:
	# The player should out-run a sprinting human (~6-7 m/s) and jump higher than one.
	assert_gt(cfg.sprint_speed, 9.0)
	assert_gt(cfg.jump_height(), 1.2)
	assert_gt(cfg.sprint_speed, cfg.walk_speed)
	assert_gt(cfg.walk_speed, cfg.crouch_speed)


func test_approach_accelerates_and_clamps() -> void:
	var v: Vector3 = MovementConfig.approach(Vector3.ZERO, Vector3(10, 0, 0), 50.0, 20.0, 0.1)
	assert_almost_eq(v.x, 5.0, 0.001)
	v = MovementConfig.approach(v, Vector3(10, 0, 0), 50.0, 20.0, 1.0)
	assert_almost_eq(v.x, 10.0, 0.001)


func test_approach_uses_decel_when_stopping() -> void:
	var v: Vector3 = MovementConfig.approach(Vector3(10, 0, 0), Vector3.ZERO, 50.0, 20.0, 0.1)
	assert_almost_eq(v.x, 8.0, 0.001)


func test_slide_knockback_scales_with_mass_strength_and_speed() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres") as MovementConfig
	var base: float = Player.slide_knock_strength(cfg, 100.0, 1.0, cfg.slide_knock_ref_speed)
	assert_almost_eq(base, cfg.slide_knock_speed, 0.001, "reference: 100 kg, strength 1")
	assert_gt(Player.slide_knock_strength(cfg, 160.0, 1.0, cfg.slide_knock_ref_speed), base, "heavier body hits harder")
	assert_gt(Player.slide_knock_strength(cfg, 100.0, 1.5, cfg.slide_knock_ref_speed), base, "stronger body hits harder")
	assert_lt(Player.slide_knock_strength(cfg, 100.0, 1.0, 6.0), base, "a slow slide barely pushes")


# ------------------------------------------------------------------ 2026-11-11 feel overhaul

func _run_ground(cfg: MovementConfig, h: Vector3, wish: Vector3, top: float, seconds: float) -> Array[float]:
	var speeds: Array[float] = []
	var t: float = 0.0
	while t < seconds:
		h = cfg.ground_step(h, wish, top, 1.0, 1.0 / 60.0)
		speeds.append(h.length())
		t += 1.0 / 60.0
	return speeds


func test_a_90_degree_turn_keeps_its_speed() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	var h: Vector3 = Vector3(0, 0, -cfg.sprint_speed)
	var speeds: Array[float] = _run_ground(cfg, h, Vector3(1, 0, 0), cfg.sprint_speed, 0.25)
	var lowest: float = speeds.min()
	assert_gt(lowest, cfg.sprint_speed * 0.97, "carving: no dip through the turn (min %.2f)" % lowest)
	# The old linear blend dipped to ~71 % through the same turn.
	var old: Vector3 = h
	var old_min: float = INF
	for i: int in 15:
		old = MovementConfig.approach(old, Vector3(cfg.sprint_speed, 0, 0), cfg.ground_accel, cfg.ground_decel, 1.0 / 60.0)
		old_min = minf(old_min, old.length())
	assert_lt(old_min, cfg.sprint_speed * 0.8, "for reference, the old blend lost speed")


func test_turn_finishes_quickly() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	var h: Vector3 = Vector3(0, 0, -cfg.walk_speed)
	for i: int in 9:  # 0.15 s
		h = cfg.ground_step(h, Vector3(1, 0, 0), cfg.walk_speed, 1.0, 1.0 / 60.0)
	assert_gt(h.normalized().x, 0.95, "facing the new way within 0.15 s")


func test_momentum_above_sprint_bleeds_slowly_while_pushing() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	var speeds: Array[float] = _run_ground(cfg, Vector3(0, 0, -15.0), Vector3(0, 0, -1), cfg.sprint_speed, 0.3)
	assert_gt(speeds[-1], 12.5, "a slide-hop's speed carries for a while (%.1f after 0.3 s)" % speeds[-1])
	var free: Array[float] = _run_ground(cfg, Vector3(0, 0, -15.0), Vector3.ZERO, cfg.sprint_speed, 0.3)
	assert_lt(free[-1], 1.0, "let go of the stick and you stop")


func test_stopping_eases_out() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	var speeds: Array[float] = _run_ground(cfg, Vector3(0, 0, -cfg.walk_speed), Vector3.ZERO, cfg.walk_speed, 0.6)
	var stop_at: int = speeds.find(0.0)
	assert_between(stop_at, 6, 27, "stops in 0.1-0.45 s (tick %d)" % stop_at)
	var first: float = cfg.walk_speed - speeds[0]
	var late: float = speeds[stop_at - 2] - speeds[stop_at - 1]
	assert_lt(late, first, "slows harder at first, gently at the end")


func test_air_control_turns_without_losing_speed() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	var h: Vector3 = Vector3(0, 0, -12.0)
	for i: int in 12:
		h = cfg.air_step(h, Vector3(1, 0, 0), cfg.sprint_speed, 1.0, 1.0 / 60.0)
	assert_almost_eq(h.length(), 12.0, 0.01, "speed kept in the air")
	assert_gt(h.normalized().x, 0.3, "and it steers")


func test_short_hop_and_hang_time() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	assert_gt(cfg.gravity_scale(5.0, false), cfg.gravity_scale(5.0, true), "letting go of A early cuts the jump")
	assert_lt(cfg.gravity_scale(0.3, true), 1.0, "a little hang at the top")
	assert_gt(cfg.gravity_scale(-5.0, false), 1.0, "falls a touch faster than it rises")


func test_sprint_holds_while_strafing_forward() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	assert_true(cfg.sprint_holds(Vector2(0.6, -0.6)), "45 degrees off forward keeps the sprint")
	assert_false(cfg.sprint_holds(Vector2(1.0, 0.0)), "straight sideways ends it")
	assert_false(cfg.sprint_holds(Vector2(0.0, -0.2)), "barely tilted ends it")
