extends GutTest
## 2026-11-12 performance pass: auto resolution only trades pixels when the
## GPU is the limit; the HUD vignette's textured edges match the 40 strips
## it replaced.

const BUDGET: float = 1000.0 / 60.0


func test_gpu_bound_frames_lower_the_resolution() -> void:
	var next: float = AdaptiveResolution.step(1.0, 18.0, 22.0, BUDGET, 0)
	assert_lt(next, 1.0, "GPU at 18 ms of 16.7: fewer pixels")


func test_cpu_bound_frames_keep_the_resolution() -> void:
	# Frames at 22 ms but the GPU at 8 ms: pixels aren't the cost.
	assert_eq(AdaptiveResolution.step(0.9, 8.0, 22.0, BUDGET, 0), 0.9, "held")
	# ...and it may climb back toward the player's scale.
	assert_true(AdaptiveResolution.is_calm(8.0, 22.0, BUDGET))
	assert_gt(AdaptiveResolution.step(0.8, 8.0, 22.0, BUDGET, 3), 0.8, "climbs back")


func test_silent_gpu_timer_still_falls_back_to_frame_time() -> void:
	assert_lt(AdaptiveResolution.step(1.0, 0.0, 24.0, BUDGET, 0), 1.0, "no GPU timer: missed frames count")


func test_busy_gpu_with_missed_frames_still_scales() -> void:
	# GPU near its budget and frames missing: the timer may not see everything.
	assert_lt(AdaptiveResolution.step(1.0, 12.0, 24.0, BUDGET, 0), 1.0)


func test_vignette_profile_matches_the_stacked_strips() -> void:
	# Stacked strips: layer i covers the outer (1 - i/10) at a·(1 - i/10)·0.22.
	for a: float in [0.2, 0.55, 0.8]:
		for x: float in [0.02, 0.33, 0.61, 0.97]:
			var keep: float = 1.0
			for i: int in 10:
				var t: float = i / 10.0
				if x < 1.0 - t:
					keep *= 1.0 - a * (1.0 - t) * 0.22
			assert_almost_eq(CombatHud.Vignette.profile(a, x), 1.0 - keep, 0.0001)
	assert_eq(CombatHud.Vignette.profile(0.8, 1.0), 0.0, "nothing past the strip")
