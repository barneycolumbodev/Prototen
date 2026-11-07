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
