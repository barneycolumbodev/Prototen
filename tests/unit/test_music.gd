extends GutTest
## The adaptive score (docs/design.md §6.1): layers follow the fight, RX-9
## bends the score, the hotel's jazz ducks, the stingers exist.


func before_each() -> void:
	MusicDirector.disarm()
	MusicDirector.levels = [0.0, 0.0, 0.0]
	TimeControl.set_dilation(1.0, 1.0)
	TimeControl.set_slowmo(1.0)


func after_all() -> void:
	MusicDirector.disarm()
	MusicDirector.step(10.0)
	TimeControl.set_dilation(1.0, 1.0)


func test_stems_loop_and_fit_the_budget() -> void:
	var bytes: int = 0
	for stem: String in MusicDirector.STEMS:
		var s: AudioStreamOggVorbis = load(MusicDirector.DIR + stem + ".ogg") as AudioStreamOggVorbis
		assert_not_null(s, stem)
		assert_almost_eq(s.get_length(), 64.0, 0.05, "%s is 32 bars at 120 BPM" % stem)
		bytes += FileAccess.get_file_as_bytes(MusicDirector.DIR + stem + ".ogg").size()
	for cue: StringName in MusicDirector.config.stinger_db:
		var path: String = "%ssting_%s.ogg" % [MusicDirector.DIR, cue]
		assert_true(ResourceLoader.exists(path), path)
		bytes += FileAccess.get_file_as_bytes(path).size()
	assert_lt(bytes, 6 * 1024 * 1024, "the whole score stays under 6 MB")


func test_layers_follow_the_fight() -> void:
	var m: Node = MusicDirector
	assert_eq(MusicDirector.targets(), [0.0, 0.0, 0.0] as Array[float], "silent until a mode runs")
	EventBus.wave_changed.emit(1, -1)
	assert_true(MusicDirector.armed)
	assert_true(MusicDirector.in_wave)
	var t: Array[float] = MusicDirector.targets()
	assert_gt(t[MusicDirector.LAYER_TENSION], 0.0, "tension while nobody is fighting")
	assert_eq(t[MusicDirector.LAYER_COMBAT], 0.0)
	EventBus.player_damaged.emit(10.0, Vector3.FORWARD)
	m.call(&"_process", 0.016)
	t = MusicDirector.targets()
	assert_gt(t[MusicDirector.LAYER_COMBAT], t[MusicDirector.LAYER_TENSION], "combat drive over the tension floor")
	MusicDirector.step(3.0)
	assert_gt(MusicDirector.levels[MusicDirector.LAYER_COMBAT], 0.5, "faded in")
	MusicDirector.boss = true
	t = MusicDirector.targets()
	assert_gt(t[MusicDirector.LAYER_BOSS], t[MusicDirector.LAYER_COMBAT], "boss threat on top")
	MusicDirector.boss = false
	EventBus.wave_changed.emit(1, 0)
	assert_false(MusicDirector.in_wave, "wave cleared")
	EventBus.wave_changed.emit(0, 0)
	assert_false(MusicDirector.armed, "mode stopped")
	MusicDirector.step(10.0)
	assert_eq(MusicDirector.levels, [0.0, 0.0, 0.0] as Array[float], "faded out")


func test_dilation_pulls_the_score_under_water() -> void:
	EventBus.wave_changed.emit(1, -1)
	TimeControl.set_dilation(0.3, 0.6)
	MusicDirector.step(1.0)
	var bus: int = AudioServer.get_bus_index(&"Music")
	var lp: AudioEffectLowPassFilter = AudioServer.get_bus_effect(bus, 0) as AudioEffectLowPassFilter
	assert_true(AudioServer.is_bus_effect_enabled(bus, 0))
	assert_lt(lp.cutoff_hz, 600.0)
	var score: AudioStreamPlayer = MusicDirector.get_node(^"Score") as AudioStreamPlayer
	assert_lt(score.pitch_scale, 0.95, "tempo and pitch bend down")
	TimeControl.set_dilation(1.0, 1.0)
	MusicDirector.step(1.0)
	assert_eq(score.pitch_scale, 1.0)
	assert_false(AudioServer.is_bus_effect_enabled(bus, 0))


func test_lounge_ducks_in_a_wave_and_swells_after() -> void:
	var speaker: AudioStreamPlayer3D = AudioStreamPlayer3D.new()
	add_child_autofree(speaker)
	MusicDirector.register_lounge(speaker)
	assert_eq(speaker.bus, &"Lounge")
	var bus: int = AudioServer.get_bus_index(&"Lounge")
	EventBus.wave_changed.emit(2, -1)
	MusicDirector.step(3.0)
	assert_almost_eq(AudioServer.get_bus_volume_db(bus), MusicDirector.config.lounge_duck_db, 0.5, "ducked")
	EventBus.wave_changed.emit(2, 0)
	MusicDirector.step(10.0)
	assert_almost_eq(AudioServer.get_bus_volume_db(bus), 0.0, 0.5, "swelled back between waves")
	assert_lt(MusicDirector.targets()[MusicDirector.LAYER_TENSION], db_to_linear(MusicDirector.config.tension_db),
		"the jazz carries the breather")
