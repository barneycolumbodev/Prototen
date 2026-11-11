extends GutTest
## Spoken callouts (owner, 2026-11-11: "I can't hear the actual voices of them
## in the game"): every line in every voice is there and loads.


func test_every_line_has_a_clip_in_every_voice() -> void:
	assert_gt(VoiceLines.VOICES.size(), 3, "several voices")
	var count: int = 0
	for voice: StringName in VoiceLines.VOICES:
		for situation: StringName in VoiceLines.LINES:
			var lines: Array = VoiceLines.LINES[situation]
			for i: int in lines.size():
				var path: String = VoiceLines.path(voice, situation, i)
				assert_true(ResourceLoader.exists(path), path)
				var s: AudioStream = load(path) as AudioStream
				assert_not_null(s, path)
				if s:
					assert_between(s.get_length(), 0.25, 3.5, "%s is a short shout" % path)
				count += 1
	assert_gt(count, 200)


func test_the_situations_the_ai_uses_exist() -> void:
	for situation: StringName in [&"contact", &"flee", &"surrender", &"cower", &"gut", &"legs", &"reload",
			&"man_down", &"officer_down", &"pinned", &"lost", &"advance", &"burning", &"grabbed", &"limb_off", &"rally"]:
		assert_true(VoiceLines.LINES.has(situation), String(situation))
