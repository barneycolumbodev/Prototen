extends GutTest
## Playtest 2026-11-05: wrong metal clink on the Chinatown map, no death audio.


func test_death_cry_picks_by_zone_and_cause() -> void:
	assert_eq(Enemy.death_cry(&"neck", true, Enemy.State.COMBAT, false, 0.5), &"death_choke")
	assert_eq(Enemy.death_cry(&"head", true, Enemy.State.COMBAT, false, 0.1), &"death_breath")
	assert_eq(Enemy.death_cry(&"head", true, Enemy.State.COMBAT, false, 0.9), &"", "some head shots are silent")
	assert_eq(Enemy.death_cry(&"l_thigh", true, Enemy.State.COMBAT, false, 0.5), &"death_scream")
	assert_eq(Enemy.death_cry(&"chest", true, Enemy.State.COMBAT, true, 0.5), &"death_scream", "burning screams")
	assert_eq(Enemy.death_cry(&"stomach", false, Enemy.State.COMBAT, false, 0.9), &"death_groan", "bled out")
	assert_eq(Enemy.death_cry(&"chest", true, Enemy.State.CRAWL, false, 0.9), &"death_groan", "finished off while crawling")


func test_every_death_sound_exists() -> void:
	for bank: StringName in [&"death_scream", &"death_choke", &"death_groan", &"death_breath", &"ricochet"]:
		assert_gt(Sfx.bank(bank).size(), 0, "%s has variants" % bank)


func test_death_voices_are_rate_limited() -> void:
	var allowed: int = 0
	for i: int in 5:
		if Sfx.claim_death_voice():
			allowed += 1
	assert_lte(allowed, Sfx.DEATH_VOICE_MAX)


func test_map_has_no_range_steel() -> void:
	var layout: Dictionary = ChinatownMap.load_layout()
	for c: Dictionary in layout["colliders"]:
		assert_ne(ChinatownMap.fstr(c, "surface"), "steel_target", "the range's ringing plates stay on the range")
	var post: SurfaceMaterial = SurfaceLibrary.shared().get_material(&"steel_post")
	assert_eq(post.id, &"steel_post")
	assert_ne(post.impact_sound, &"steel")
