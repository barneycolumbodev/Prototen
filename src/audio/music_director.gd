extends Node
## The adaptive score (docs/design.md §6.1). Autoloaded as MusicDirector.
##
## Three stems in one AudioStreamSynchronized so they never drift: Tension
## Pulse, Combat Drive and Boss Threat (assets/audio/music/, built by
## raw_assets/audio/build_music.py). Each layer's volume eases toward a
## target worked out from the fight:
## - armed: a combat mode is running (a wave, the rolling spawns). Unarmed,
##   the score is silent (main menu, boot camp drills, the empty range).
## - engaged: a man is in COMBAT near the operative (or alert enough), or
##   the operative was hit, within the last `combat_hold` seconds.
## - boss: a boss is up and fighting (he leaves the "enemies" group when he
##   goes down on one knee).
## Everything runs on the "Music" bus: RX-9 time dilation pulls a resonant
## low-pass down and bends pitch/tempo (TimeControl), the underwater throb.
## Lounge speakers (the hotel's jazz) register here; they go to the
## "Lounge" bus, ducked and muffled while a wave or fight is on, swelling
## back in the breathers. Stingers (`stinger()`, or EventBus.music_cue)
## play over the layers, which dip so they read. Tuning: data/audio/music.tres.

const DIR: String = "res://assets/audio/music/"
const LAYER_TENSION: int = 0
const LAYER_COMBAT: int = 1
const LAYER_BOSS: int = 2
const STEMS: Array[String] = ["music_tension", "music_combat", "music_boss"]
const SILENT_DB: float = -80.0
## Music volume by Settings.music_level (off, low, medium, full).
const LEVEL_DB: Array[float] = [-80.0, -12.0, -6.0, 0.0]

var config: MusicConfig = preload("res://data/audio/music.tres")
var armed: bool = false
var engaged: bool = false
var boss: bool = false
## A wave is under way (wave modes; the lounge stays ducked through it).
var in_wave: bool = false
## Linear 0..1 of each layer right now (eased toward its target).
var levels: Array[float] = [0.0, 0.0, 0.0]
## Dilation as the score hears it (0..1, eased).
var dilation: float = 0.0

var _player: AudioStreamPlayer
var _stream: AudioStreamSynchronized
var _stingers: Array[AudioStreamPlayer] = []
var _next_sting: int = 0
var _sting_cache: Dictionary[StringName, AudioStream] = {}
var _sting_duck: float = 0.0
var _lowpass: AudioEffectLowPassFilter
var _lounge_lowpass: AudioEffectLowPassFilter
var _lounge: Array[AudioStreamPlayer3D] = []
var _lounge_level: float = 1.0
var _engaged_left: float = 0.0
var _scan_left: float = 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_make_buses()
	_stream = AudioStreamSynchronized.new()
	_stream.stream_count = STEMS.size()
	for i: int in STEMS.size():
		var path: String = DIR + STEMS[i] + ".ogg"
		if ResourceLoader.exists(path):
			var s: AudioStream = load(path)
			if s is AudioStreamOggVorbis:
				(s as AudioStreamOggVorbis).loop = true
			_stream.set_sync_stream(i, s)
		_stream.set_sync_stream_volume(i, SILENT_DB)
	_player = AudioStreamPlayer.new()
	_player.name = "Score"
	_player.bus = &"Music"
	_player.stream = _stream
	add_child(_player)
	for i: int in 2:
		var p: AudioStreamPlayer = AudioStreamPlayer.new()
		p.name = "Stinger%d" % i
		p.bus = &"Music"
		add_child(p)
		_stingers.append(p)
	EventBus.wave_changed.connect(_on_wave_changed)
	EventBus.score_changed.connect(_on_score_changed)
	EventBus.player_died.connect(_on_player_died)
	EventBus.player_damaged.connect(_on_player_damaged)
	EventBus.music_cue.connect(stinger)
	get_tree().scene_changed.connect(_on_scene_changed)
	Settings.changed.connect(_apply_volume)
	_apply_volume()


# ------------------------------------------------------------------ API

## Starts the score (a combat mode began). Safe to call every frame.
func arm() -> void:
	if armed:
		return
	armed = true
	if not _player.playing:
		_player.play()


## The mode stopped: the score fades out over `stop_fade` and stops.
func disarm() -> void:
	armed = false
	engaged = false
	boss = false
	in_wave = false
	_engaged_left = 0.0


## Plays a stinger (sting_<cue>.ogg) over the layers. Returns false if there is none.
func stinger(cue: StringName) -> bool:
	var s: AudioStream = _sting(cue)
	if s == null:
		return false
	var p: AudioStreamPlayer = _stingers[_next_sting]
	_next_sting = (_next_sting + 1) % _stingers.size()
	p.stream = s
	var db: float = config.stinger_db.get(cue, -3.0)
	p.volume_db = db
	p.pitch_scale = 1.0
	p.play()
	_sting_duck = 1.0
	return true


## A sound emitter playing diegetic music (the hotel's lobby and bar speakers).
func register_lounge(p: AudioStreamPlayer3D) -> void:
	p.bus = &"Lounge"
	if p not in _lounge:
		_lounge.append(p)


## Target linear level of each layer for the state right now (tests read it).
func targets() -> Array[float]:
	var t: Array[float] = [0.0, 0.0, 0.0]
	if not armed:
		return t
	var lounge: bool = has_lounge()
	if boss:
		t[LAYER_TENSION] = db_to_linear(config.tension_boss_db)
		t[LAYER_COMBAT] = db_to_linear(config.combat_boss_db)
		t[LAYER_BOSS] = db_to_linear(config.boss_db)
	elif engaged:
		t[LAYER_TENSION] = db_to_linear(config.tension_combat_db)
		t[LAYER_COMBAT] = db_to_linear(config.combat_db)
	else:
		var db: float = config.tension_db + (config.lounge_tension_db if lounge and not in_wave else 0.0)
		t[LAYER_TENSION] = db_to_linear(db)
	return t


## Is diegetic music playing on this map?
func has_lounge() -> bool:
	for i: int in range(_lounge.size() - 1, -1, -1):
		if not is_instance_valid(_lounge[i]):
			_lounge.remove_at(i)
	return not _lounge.is_empty()


## Should the lounge be ducked right now?
func lounge_ducked() -> bool:
	return armed and (in_wave or engaged or boss)


func is_playing() -> bool:
	return _player.playing


# ------------------------------------------------------------------ frame

func _process(delta: float) -> void:
	var dt: float = minf(delta / maxf(Engine.time_scale, 0.001), 0.1)
	if armed:
		_scan_left -= dt
		if _scan_left <= 0.0:
			_scan_left = config.scan_interval
			_scan()
		_engaged_left = maxf(0.0, _engaged_left - dt)
		engaged = _engaged_left > 0.0
	step(dt)


## Eases levels, dilation, lounge and stinger duck by `dt` real seconds
## (tests call it directly).
func step(dt: float) -> void:
	var t: Array[float] = targets()
	var duck: float = lerpf(1.0, db_to_linear(config.stinger_duck_db), _sting_duck)
	_sting_duck = maxf(0.0, _sting_duck - dt / maxf(config.stinger_duck_time, 0.01))
	for i: int in levels.size():
		var rate: float
		if t[i] > levels[i]:
			rate = config.boss_fade_in if i == LAYER_BOSS else config.fade_in
		else:
			rate = config.fade_out if armed else config.stop_fade
		levels[i] = move_toward(levels[i], t[i], dt / maxf(rate, 0.01))
		_stream.set_sync_stream_volume(i, linear_to_db(levels[i] * duck) if levels[i] > 0.0005 else SILENT_DB)
	if not armed and _player.playing and _silent():
		_player.stop()
	_step_dilation(dt)
	_step_lounge(dt)


func _silent() -> bool:
	for v: float in levels:
		if v > 0.0:
			return false
	return true


func _step_dilation(dt: float) -> void:
	var want: float = maxf(TimeControl.dilation_amount(), (1.0 - TimeControl.slowmo_scale) * config.slowmo_weight)
	dilation = move_toward(dilation, clampf(want, 0.0, 1.0), dt / maxf(config.dilation_ease, 0.01))
	_lowpass.cutoff_hz = lerpf(20000.0, config.dilation_cutoff_hz, sqrt(dilation))
	_lowpass.resonance = lerpf(0.5, config.dilation_resonance, dilation)
	_set_effect_on(&"Music", _lowpass, dilation > 0.001)
	_player.pitch_scale = lerpf(1.0, config.dilation_pitch, dilation)


func _step_lounge(dt: float) -> void:
	var down: bool = lounge_ducked()
	var target: float = 0.0 if down else 1.0
	var rate: float = config.lounge_duck_time if down else config.lounge_swell_time
	_lounge_level = move_toward(_lounge_level, target, dt / maxf(rate, 0.01))
	var bus: int = AudioServer.get_bus_index(&"Lounge")
	AudioServer.set_bus_volume_db(bus, lerpf(0.0, config.lounge_duck_db, _lounge_level_curve()))
	_lounge_lowpass.cutoff_hz = lerpf(20000.0, config.lounge_duck_cutoff_hz, _lounge_level_curve())
	_set_effect_on(&"Lounge", _lounge_lowpass, _lounge_level < 0.999)


## 0 = full lounge, 1 = fully ducked, eased (smoothstep).
func _lounge_level_curve() -> float:
	return smoothstep(0.0, 1.0, 1.0 - _lounge_level)


## Who's fighting: men in COMBAT (or alert enough) near the operative, and the boss.
func _scan() -> void:
	var p: Node3D = get_tree().get_first_node_in_group(&"player") as Node3D
	var any_boss: bool = false
	var hot: bool = false
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive:
			continue
		if e.config and e.config.boss:
			any_boss = true
		if hot:
			continue
		var fighting: bool = e.state == Enemy.State.COMBAT or (e.state == Enemy.State.ALERT and e.awareness >= config.engage_awareness)
		if fighting and (p == null or p.global_position.distance_to(e.global_position) <= config.engage_range):
			hot = true
	# Dogs always hunt: a live one in range is a fight.
	if not hot and p:
		for n: Node in get_tree().get_nodes_in_group(&"dogs"):
			var d: AttackDog = n as AttackDog
			if d and d.alive and p.global_position.distance_to(d.global_position) <= config.engage_range * 0.5:
				hot = true
				break
	boss = any_boss
	if hot:
		_engaged_left = config.combat_hold


# ------------------------------------------------------------------ events

func _on_wave_changed(wave: int, left: int) -> void:
	if wave <= 0:
		if left == 0:
			disarm()
		return
	arm()
	if left == -1 and not in_wave:
		in_wave = true
		stinger(&"wave_start")
	elif left == 0 and in_wave:
		in_wave = false
		stinger(&"wave_cleared")


func _on_score_changed(_kills: int, _hostiles: int) -> void:
	arm()


func _on_player_damaged(_amount: float, _from: Vector3) -> void:
	if armed:
		_engaged_left = config.combat_hold


func _on_player_died() -> void:
	if armed:
		stinger(&"run_over")
	disarm()


## A new map: the score stops dead. Fires after the new scene's _ready, so
## lounge speakers it just registered stay (freed ones drop out by themselves).
func _on_scene_changed() -> void:
	disarm()
	levels = [0.0, 0.0, 0.0]
	_player.stop()
	_lounge_level = 1.0


# ------------------------------------------------------------------ plumbing

func _sting(cue: StringName) -> AudioStream:
	if not _sting_cache.has(cue):
		var path: String = "%ssting_%s.ogg" % [DIR, cue]
		_sting_cache[cue] = load(path) as AudioStream if ResourceLoader.exists(path) else null
	return _sting_cache[cue]


func _apply_volume() -> void:
	var bus: int = AudioServer.get_bus_index(&"Music")
	var level: int = clampi(Settings.music_level, 0, LEVEL_DB.size() - 1)
	AudioServer.set_bus_volume_db(bus, LEVEL_DB[level])
	AudioServer.set_bus_mute(bus, level == 0)


func _make_buses() -> void:
	for bus_name: StringName in [&"Music", &"Lounge"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			AudioServer.add_bus()
			var idx: int = AudioServer.bus_count - 1
			AudioServer.set_bus_name(idx, bus_name)
			AudioServer.set_bus_send(idx, &"Master")
	var music: int = AudioServer.get_bus_index(&"Music")
	_lowpass = AudioEffectLowPassFilter.new()
	_lowpass.cutoff_hz = 20000.0
	AudioServer.add_bus_effect(music, _lowpass)
	AudioServer.set_bus_effect_enabled(music, 0, false)
	# Three stems and a stinger can stack: a limiter keeps the sum off the ceiling.
	var limiter: AudioEffectHardLimiter = AudioEffectHardLimiter.new()
	limiter.ceiling_db = -1.0
	AudioServer.add_bus_effect(music, limiter)
	var lounge: int = AudioServer.get_bus_index(&"Lounge")
	_lounge_lowpass = AudioEffectLowPassFilter.new()
	_lounge_lowpass.cutoff_hz = 20000.0
	AudioServer.add_bus_effect(lounge, _lounge_lowpass)
	AudioServer.set_bus_effect_enabled(lounge, 0, false)


func _set_effect_on(bus_name: StringName, fx: AudioEffect, on: bool) -> void:
	var bus: int = AudioServer.get_bus_index(bus_name)
	for i: int in AudioServer.get_bus_effect_count(bus):
		if AudioServer.get_bus_effect(bus, i) == fx:
			if AudioServer.is_bus_effect_enabled(bus, i) != on:
				AudioServer.set_bus_effect_enabled(bus, i, on)
			return
