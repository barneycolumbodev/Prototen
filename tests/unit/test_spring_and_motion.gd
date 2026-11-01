extends GutTest
## Springs and procedural viewmodel motion.

var data: WeaponData


func before_each() -> void:
	data = (load("res://data/weapons/pistol_57.tres") as WeaponData).duplicate() as WeaponData


func test_kick_peaks_at_requested_amount_when_critically_damped() -> void:
	var s: Spring = Spring.new(6.0, 1.0)
	s.kick(Vector3(2.0, 0, 0))
	var peak: float = 0.0
	for i: int in 240:
		peak = maxf(peak, s.step(1.0 / 240.0).x)
	assert_almost_eq(peak, 2.0, 0.05)
	assert_true(s.is_settled(0.01), "back to rest after a second")


func test_kick_peak_is_exact_for_bouncy_and_stiff_springs() -> void:
	for z: float in [0.3, 0.55, 0.9, 1.4]:
		var s: Spring = Spring.new(7.0, z)
		s.kick(Vector3(1.5, 0, 0))
		var peak: float = 0.0
		for i: int in 600:
			peak = maxf(peak, s.step(1.0 / 600.0).x)
		assert_almost_eq(peak, 1.5, 0.01, "damping %.2f" % z)


func test_spring_is_stable_at_low_frame_rate() -> void:
	var s: Spring = Spring.new(25.0, 0.3)
	s.kick(Vector3.ONE)
	for i: int in 30:
		s.step(0.1)  # 10 fps
	assert_lt(s.value.length(), 0.5, "a stiff spring stays stable at 10 fps")


func test_same_motion_at_30_and_120_fps() -> void:
	var a: Spring = Spring.new(8.0, 0.55)
	var b: Spring = Spring.new(8.0, 0.55)
	a.kick(Vector3(3, 0, 0))
	b.kick(Vector3(3, 0, 0))
	for i: int in 9:
		a.step(1.0 / 30.0)
	for i: int in 36:
		b.step(1.0 / 120.0)
	assert_almost_eq(a.value.x, b.value.x, 0.0001, "frame-rate independent")


func test_motion_at_rest_is_the_hip_pose() -> void:
	var m: ViewmodelMotion = ViewmodelMotion.new(data)
	for i: int in 240:  # let the draw pose settle
		m.update(1.0 / 60.0, 0.0, Vector2.ZERO, 0.0, true, 0)
	var hip: Transform3D = Transform3D(Basis(), Vector3(0.1, -0.1, -0.3))
	var ads: Transform3D = Transform3D(Basis(), Vector3(0, -0.02, -0.4))
	assert_true(m.compose(hip, ads, 0.0).origin.is_equal_approx(hip.origin) or m.compose(hip, ads, 0.0).origin.distance_to(hip.origin) < 0.001)
	assert_lt(m.compose(hip, ads, 1.0).origin.distance_to(ads.origin), 0.001)


func test_firing_kicks_the_gun_back_and_cycles_the_slide() -> void:
	var m: ViewmodelMotion = ViewmodelMotion.new(data)
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	m.fire(0.0, rng)
	var max_back: float = 0.0
	var max_slide: float = 0.0
	for i: int in 12:
		m.update(1.0 / 120.0, 0.0, Vector2.ZERO, 0.0, true, 0)
		max_back = maxf(max_back, m.recoil_pos.value.z)
		max_slide = maxf(max_slide, m.slide)
	assert_gt(max_back, data.vm_kick_back * 0.6, "gun pushed back into the hand")
	assert_gt(max_slide, 0.9, "slide went fully back")
	for i: int in 60:
		m.update(1.0 / 60.0, 0.0, Vector2.ZERO, 0.0, true, 0)
	assert_eq(m.slide, 0.0, "slide returned to battery")


func test_last_round_locks_the_slide_until_released() -> void:
	var m: ViewmodelMotion = ViewmodelMotion.new(data)
	m.fire(0.0, RandomNumberGenerator.new())
	m.lock_slide()
	for i: int in 60:
		m.update(1.0 / 60.0, 0.0, Vector2.ZERO, 0.0, true, 2)
	assert_eq(m.slide, 1.0)
	m.release_slide()
	for i: int in 30:
		m.update(1.0 / 60.0, 0.0, Vector2.ZERO, 0.0, true, 0)
	assert_eq(m.slide, 0.0)


func test_turning_right_swings_the_muzzle_left() -> void:
	var m: ViewmodelMotion = ViewmodelMotion.new(data)
	for i: int in 60:
		m.update(1.0 / 60.0, 0.0, Vector2(200, 0), 0.0, true, 0)
	assert_gt(m.sway.value.y, 0.5, "positive weapon-space yaw = muzzle toward the gun's left")


func test_spread_aimed_is_the_guns_mechanical_precision() -> void:
	var aimed: float = data.spread_deg(1.0, 0.0, false, 0.0)
	assert_almost_eq(aimed, data.mechanical_moa / 60.0, 0.0001, "1.5 MOA = 0.025°")
	assert_gt(data.spread_deg(0.0, 0.0, false, 0.0), aimed * 20.0, "hip fire is much looser")
	assert_gt(data.spread_deg(0.0, 1.0, false, 0.0), data.spread_deg(0.0, 0.0, false, 0.0), "moving adds spread")
	assert_gt(data.spread_deg(0.0, 0.0, true, 0.0), data.spread_deg(0.0, 1.0, false, 0.0), "airborne is worst")
