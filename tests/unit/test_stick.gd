extends GutTest


func test_inside_deadzone_is_zero() -> void:
	assert_eq(Stick.shape(Vector2(0.1, 0.0), 0.15, 0.05, 1.0), Vector2.ZERO)
	assert_eq(Stick.shape(Vector2.ZERO, 0.0, 0.0, 1.0), Vector2.ZERO)


func test_deadzone_is_radial_not_per_axis() -> void:
	# A diagonal of length 0.2 passes a 0.15 radial deadzone even though each axis is ~0.14.
	var v: Vector2 = Stick.shape(Vector2(0.1414, 0.1414), 0.15, 0.05, 1.0)
	assert_gt(v.length(), 0.0)
	assert_almost_eq(v.normalized().angle(), PI / 4.0, 0.001)


func test_full_tilt_reaches_one_before_rim() -> void:
	assert_almost_eq(Stick.shape(Vector2(0.96, 0.0), 0.15, 0.05, 1.0).length(), 1.0, 0.0001)
	assert_almost_eq(Stick.shape(Vector2(1.0, 0.0), 0.15, 0.05, 2.0).length(), 1.0, 0.0001)


func test_rescaled_from_deadzone_edge() -> void:
	# Just outside the deadzone gives a tiny output, not a jump to 0.15.
	assert_lt(Stick.shape(Vector2(0.16, 0.0), 0.15, 0.05, 1.0).length(), 0.02)


func test_exponent_gives_finer_centre() -> void:
	var linear: float = Stick.shape(Vector2(0.5, 0.0), 0.1, 0.0, 1.0).length()
	var curved: float = Stick.shape(Vector2(0.5, 0.0), 0.1, 0.0, 2.0).length()
	assert_lt(curved, linear)
