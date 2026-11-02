extends GutTest


func test_next_in_cycles_and_wraps() -> void:
	var values: Array[float] = [0.7, 0.8, 1.0]
	assert_eq(Settings.next_in(values, 0.7), 0.8)
	assert_eq(Settings.next_in(values, 1.0), 0.7)
	assert_eq(Settings.next_in(values, 0.55), 0.7)


func test_bench_summary() -> void:
	var frames: PackedFloat32Array = PackedFloat32Array()
	for i: int in 100:
		frames.append(10.0)
	frames[99] = 40.0
	var r: Dictionary = FrameBench.summarize(frames)
	var count: int = r["frames"]
	var avg: float = r["avg_ms"]
	var p50: float = r["p50_ms"]
	var p99: float = r["p99_ms"]
	var worst: float = r["max_ms"]
	assert_eq(count, 100)
	assert_almost_eq(avg, 10.3, 0.001)
	assert_eq(p50, 10.0)
	assert_eq(p99, 10.0)
	assert_eq(worst, 40.0)


func test_bench_summary_empty() -> void:
	var r: Dictionary = FrameBench.summarize(PackedFloat32Array())
	var count: int = r["frames"]
	var avg: float = r["avg_ms"]
	assert_eq(count, 0)
	assert_eq(avg, 0.0)


func test_look_speed_steps_without_wrapping_and_scales_the_stick() -> void:
	var saved: float = Settings.look_sensitivity
	Settings.look_sensitivity = 1.0
	Settings.step_look_sensitivity(1)
	assert_almost_eq(Settings.look_sensitivity, 1.15, 0.001)
	for i: int in 20:
		Settings.step_look_sensitivity(-1)
	assert_almost_eq(Settings.look_sensitivity, Settings.LOOK_SPEEDS[0], 0.001, "stops at the slowest")
	Settings.cycle_look_sensitivity()
	assert_gt(Settings.look_sensitivity, Settings.LOOK_SPEEDS[0])
	Settings.look_sensitivity = saved
	Settings.save_settings()


func test_default_look_is_slower_than_m1a() -> void:
	# Playtest 2026-11-01: "a little too sensitive". M1a's Standard curve turned 240°/s.
	var look: LookConfig = load("res://data/input/look_standard.tres") as LookConfig
	assert_lt(look.yaw_speed_deg, 200.0)
	assert_lt(look.yaw_speed_deg * look.full_tilt_boost, 300.0, "full-tilt turn stays controllable")
