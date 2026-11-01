extends GutTest

var look: LookConfig


func before_each() -> void:
	look = load("res://data/input/look_standard.tres") as LookConfig


func test_presets_load() -> void:
	for id: String in Settings.LOOK_PRESETS:
		var preset: LookConfig = load("res://data/input/look_%s.tres" % id) as LookConfig
		assert_not_null(preset, id)
		assert_gt(preset.yaw_speed_deg, 0.0, id)


func test_full_deflection_turns_at_yaw_speed() -> void:
	var rate: Vector2 = look.look_rate(Vector2(1, 0), 0.0)
	assert_almost_eq(rate.x, look.yaw_speed_deg, 0.01)


func test_full_tilt_boost_ramps_after_delay() -> void:
	assert_eq(look.boost_for(0.0), 1.0)
	assert_eq(look.boost_for(look.full_tilt_delay), 1.0)
	assert_almost_eq(look.boost_for(look.full_tilt_delay + look.full_tilt_ramp), look.full_tilt_boost, 0.001)
	assert_almost_eq(look.boost_for(10.0), look.full_tilt_boost, 0.001)


func test_boost_applies_to_yaw_only() -> void:
	var held: float = look.full_tilt_delay + look.full_tilt_ramp
	var rate: Vector2 = look.look_rate(Vector2(0, 1), held)
	assert_almost_eq(rate.y, look.pitch_speed_deg, 0.01)


func test_invert_y() -> void:
	var inverted: LookConfig = look.duplicate() as LookConfig
	inverted.invert_y = true
	assert_lt(inverted.look_rate(Vector2(0, 1), 0.0).y, 0.0)
