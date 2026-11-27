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


## Audio pass 2026-11-27: every firearm, the player's and the enemies', fires its
## own shot bank (real recordings, design §4.13), with a tail for the player's.
func test_every_firearm_has_its_own_shot() -> void:
	var player_guns: Array[String] = ["aug", "glock22", "governor", "m14p", "m32", "magnum44", "mg42", "mp5",
		"saiga12k", "spas12"]
	var seen: Dictionary = {}
	for gun: String in player_guns:
		var data: WeaponData = load("res://data/weapons/%s.tres" % gun) as WeaponData
		var shot: StringName = Sfx.weapon_bank(data, &"shot")
		assert_eq(String(shot), data.sound_prefix + "shot", "%s has its own shot bank" % gun)
		assert_gt(Sfx.bank(shot).size(), 0, "%s shot loads" % gun)
		assert_gt(Sfx.bank(Sfx.weapon_bank(data, &"tail")).size(), 0, "%s has a tail" % gun)
		assert_false(seen.has(shot), "%s shares no bank" % gun)
		seen[shot] = true
	assert_gt(Sfx.bank(&"shot").size(), 0, "the Five-seveN's (the shared bank)")
	for gun: String in ["type56", "smg", "pump"]:
		var data: WeaponData = load("res://data/enemies/weapons/%s.tres" % gun) as WeaponData
		assert_gt(Sfx.bank(StringName("enemy_" + data.sound_prefix + "shot")).size(), 0, "enemy %s shot loads" % gun)
