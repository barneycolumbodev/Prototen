extends Node3D
## Sound playback, pooled (CLAUDE.md §9.2). Autoloaded as Sfx.
##
## Banks are WAVs in assets/audio/sfx named `<bank>_<n>.wav`; a random
## variant plays each time. A gun's own banks use its `sound_prefix`
## ("mg42_shot") and fall back to the shared ones ("shot"). Shots have their
## own voice pool so 1,200 rpm can't cut off confirms and reload sounds. Own-gun shots are non-positional with a room
## tail on the "Tail" bus, whose reverb size the level sets (`set_room`).
## Impacts are positional, heard from where the round landed.
## Pitch follows the time scale so hit-stop and slow motion sound right.
## Shotgun pellets: one confirm per shell (the loudest kind wins), and each
## pellet's impact is a little quieter than a single round's.

const DIR: String = "res://assets/audio/sfx/"
const VOICES_3D: int = 16
const VOICES_2D: int = 8
const VOICES_SHOT: int = 8
const VOICES_TAIL: int = 3

var _banks: Dictionary[StringName, Array] = {}
var _voices3d: Array[AudioStreamPlayer3D] = []
var _voices2d: Array[AudioStreamPlayer] = []
var _voices_shot: Array[AudioStreamPlayer] = []
var _voices_tail: Array[AudioStreamPlayer] = []
var _next_shot: int = 0
var _next_tail: int = 0
var _next3d: int = 0
var _next2d: int = 0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _reverb: AudioEffectReverb
## Confirm already played for this volley, and how strong (hit 1, headshot 2, kill 3).
var _confirm_volley: int = 0
var _confirm_rank: int = 0
var _last_ricochet: float = -10.0
var _death_voices: Array[float] = []
var _muffle: AudioEffectLowPassFilter
const DEATH_VOICE_WINDOW: float = 0.6
const DEATH_VOICE_MAX: int = 2
## Seconds between ricochet whines (an MG42 burst along the street would chain them).
const RICOCHET_GAP: float = 0.35
## Only some glancing rounds are heard at all.
const RICOCHET_AUDIBLE: float = 0.4
## Casing landings: at most one per this many seconds (an MG42 burst drops 20 a second).
const CASING_GAP: float = 0.15
var _last_casing: float = -10.0


func _ready() -> void:
	_rng.randomize()
	_make_buses()
	for i: int in VOICES_3D:
		var p: AudioStreamPlayer3D = AudioStreamPlayer3D.new()
		p.bus = &"SFX"
		p.unit_size = 6.0
		p.max_distance = 80.0
		p.attenuation_filter_cutoff_hz = 9000.0
		add_child(p)
		_voices3d.append(p)
	for i: int in VOICES_2D:
		var p: AudioStreamPlayer = AudioStreamPlayer.new()
		p.bus = &"SFX"
		add_child(p)
		_voices2d.append(p)
	for i: int in VOICES_SHOT:
		var p: AudioStreamPlayer = AudioStreamPlayer.new()
		p.bus = &"SFX"
		add_child(p)
		_voices_shot.append(p)
	for i: int in VOICES_TAIL:
		var p: AudioStreamPlayer = AudioStreamPlayer.new()
		p.bus = &"Tail"
		add_child(p)
		_voices_tail.append(p)
	EventBus.ballistic_hit.connect(_on_hit)
	EventBus.target_hit.connect(_on_target_hit)


## Room size 0..1 for the shot tail (small room = short and bright).
func set_room(size: float) -> void:
	_reverb.room_size = clampf(size, 0.0, 1.0)
	_reverb.damping = lerpf(0.3, 0.6, size)


func bank(name: StringName) -> Array:
	if not _banks.has(name):
		var streams: Array = []
		for i: int in range(1, 9):
			var path: String = "%s%s_%d.wav" % [DIR, name, i]
			if not ResourceLoader.exists(path):
				break
			streams.append(load(path))
		_banks[name] = streams
	return _banks[name]


## The gun's bank for `name`: prefix + name if it exists, else the shared one.
func weapon_bank(data: WeaponData, name: StringName) -> StringName:
	if not data.sound_prefix.is_empty():
		var own: StringName = StringName(data.sound_prefix + String(name))
		if not bank(own).is_empty():
			return own
	return name


## Own-gun shot, plus the room tail when `with_tail` (automatic guns rate-limit it).
## `extra_db`: per-shot change (a railgun shot on a half-charged capacitor is quieter).
func play_shot(data: WeaponData, with_tail: bool = true, extra_db: float = 0.0) -> void:
	_play_pool(_voices_shot, _next_shot, weapon_bank(data, &"shot"), data.shot_volume_db + extra_db, 0.04)
	_next_shot = (_next_shot + 1) % _voices_shot.size()
	if with_tail:
		_play_pool(_voices_tail, _next_tail, weapon_bank(data, &"tail"), -8.0 + data.shot_volume_db, 0.05)
		_next_tail = (_next_tail + 1) % _voices_tail.size()


## Reload beats, dry fire etc. for this gun (non-positional).
func play_weapon(data: WeaponData, name: StringName, volume_db: float = 0.0) -> void:
	play_ui(weapon_bank(data, name), volume_db)


func _play_pool(pool: Array[AudioStreamPlayer], index: int, name: StringName, volume_db: float, pitch_rand: float) -> void:
	var streams: Array = bank(name)
	if streams.is_empty():
		return
	var p: AudioStreamPlayer = pool[index]
	var stream: AudioStream = streams[_rng.randi() % streams.size()]
	p.stream = stream
	p.volume_db = volume_db
	p.pitch_scale = TimeControl.player_pitch() * (1.0 + _rng.randf_range(-pitch_rand, pitch_rand))
	p.play()


## Non-positional sound (own gun, reload, confirms). Returns the voice used.
func play_ui(name: StringName, volume_db: float = 0.0, pitch_rand: float = 0.03) -> AudioStreamPlayer:
	var streams: Array = bank(name)
	if streams.is_empty():
		return null
	var p: AudioStreamPlayer = _voices2d[_next2d]
	_next2d = (_next2d + 1) % _voices2d.size()
	p.bus = &"SFX"
	var stream: AudioStream = streams[_rng.randi() % streams.size()]
	p.stream = stream
	p.volume_db = volume_db
	# Your own gun and gear: your time, not the world's.
	p.pitch_scale = TimeControl.player_pitch() * (1.0 + _rng.randf_range(-pitch_rand, pitch_rand))
	p.play()
	return p


func play_at(name: StringName, at: Vector3, volume_db: float = 0.0, pitch_rand: float = 0.06) -> void:
	var streams: Array = bank(name)
	if streams.is_empty():
		return
	var p: AudioStreamPlayer3D = _voices3d[_next3d]
	_next3d = (_next3d + 1) % _voices3d.size()
	p.global_position = at
	var stream: AudioStream = streams[_rng.randi() % streams.size()]
	p.stream = stream
	p.volume_db = volume_db
	p.pitch_scale = _pitch(pitch_rand)
	p.play()


## A spent case landing near the player: a soft tick, rate-limited.
func play_casing(bank_name: StringName, at: Vector3) -> void:
	var now: float = Time.get_ticks_msec() * 0.001
	if now - _last_casing < CASING_GAP:
		return
	_last_casing = now
	play_at(bank_name, at, -20.0, 0.08)


## Muffles everything (time dilation): 0 = clear, 1 = cut off at `cutoff_hz`.
func set_muffle(amount: float, cutoff_hz: float = 2400.0) -> void:
	var bus: int = AudioServer.get_bus_index(&"Master")
	if _muffle == null:
		_muffle = AudioEffectLowPassFilter.new()
		_muffle.resonance = 0.6
		AudioServer.add_bus_effect(bus, _muffle)
	var idx: int = -1
	for i: int in AudioServer.get_bus_effect_count(bus):
		if AudioServer.get_bus_effect(bus, i) == _muffle:
			idx = i
	var a: float = clampf(amount, 0.0, 1.0)
	_muffle.cutoff_hz = lerpf(20000.0, cutoff_hz, sqrt(a))
	if idx >= 0:
		AudioServer.set_bus_effect_enabled(bus, idx, a > 0.001)


## Stunned hearing after a blast close by (Explosion.grenade): every sound but
## the ring is muffled by `amount` (0..1), easing back over CONCUSS_TIME of
## real time; above a quarter, a ring in the ears.
const CONCUSS_TIME: float = 2.6
var _concuss: float = 0.0
var _concuss_filters: Array[AudioEffectLowPassFilter] = []
var _ring: AudioStreamPlayer


func concuss(amount: float) -> void:
	var a: float = clampf(amount, 0.0, 1.0)
	if _concuss_filters.is_empty():
		for bus_name: StringName in [&"SFX", &"Tail"]:
			var bus: int = AudioServer.get_bus_index(bus_name)
			if bus < 0:
				continue
			var f: AudioEffectLowPassFilter = AudioEffectLowPassFilter.new()
			f.resonance = 0.5
			f.cutoff_hz = 20000.0
			AudioServer.add_bus_effect(bus, f)
			_concuss_filters.append(f)
		_ring = AudioStreamPlayer.new()
		_ring.bus = &"Master"
		add_child(_ring)
	if a > 0.25:
		var streams: Array = bank(&"ear_ring")
		if not streams.is_empty() and (not _ring.playing or a > _concuss + 0.2):
			_ring.stream = streams[_rng.randi() % streams.size()]
			_ring.volume_db = lerpf(-26.0, -9.0, a)
			_ring.play()
	_concuss = maxf(_concuss, a)
	_apply_concuss()


## How stunned the hearing is now (0..1).
func concussion() -> float:
	return _concuss


func _process(delta: float) -> void:
	if _concuss <= 0.0:
		return
	_concuss = maxf(0.0, _concuss - TimeControl.real_delta(delta) / CONCUSS_TIME)
	_apply_concuss()


func _apply_concuss() -> void:
	for f: AudioEffectLowPassFilter in _concuss_filters:
		f.cutoff_hz = lerpf(20000.0, 450.0, pow(_concuss, 0.6))
	for bus_name: StringName in [&"SFX", &"Tail"]:
		var bus: int = AudioServer.get_bus_index(bus_name)
		for i: int in AudioServer.get_bus_effect_count(bus):
			var fx: AudioEffect = AudioServer.get_bus_effect(bus, i)
			if fx in _concuss_filters:
				AudioServer.set_bus_effect_enabled(bus, i, _concuss > 0.001)


## Rate limit for dying voices: a shotgun blast into a crowd shouldn't stack
## five screams. Returns true (and takes the slot) if one may play now.
func claim_death_voice() -> bool:
	var now: float = Time.get_ticks_msec() * 0.001
	_death_voices = _death_voices.filter(func(t: float) -> bool: return now - t < DEATH_VOICE_WINDOW)
	if _death_voices.size() >= DEATH_VOICE_MAX:
		return false
	_death_voices.append(now)
	return true


## Pitch for a sound in the world: follows slow motion, plus a random spread.
func world_pitch(rand: float) -> float:
	return _pitch(rand)


func _pitch(rand: float) -> float:
	return clampf(Engine.time_scale, 0.25, 1.0) * (1.0 + _rng.randf_range(-rand, rand))


func _on_hit(hit: BallisticHit) -> void:
	var vol: float = linear_to_db(clampf(hit.energy_in / maxf(hit.weapon.muzzle_energy(), 1.0), 0.15, 1.0))
	if hit.weapon.embers and _rng.randf() > 0.3:
		return  # 14 embers landing together: a few ticks are enough under the roar
	if hit.weapon.pellets > 1:
		vol -= 5.0
	var sound: StringName = &"impact_" + String(hit.surface.impact_sound)
	play_at(sound, hit.point, vol)
	# A glancing round: the surface's own impact plus a short whine (not the
	# range's steel ping, which every grazing street hit used to play).
	if hit.result == BallisticHit.Result.RICOCHET:
		var now: float = Time.get_ticks_msec() * 0.001
		if now - _last_ricochet > RICOCHET_GAP and _rng.randf() < RICOCHET_AUDIBLE:
			_last_ricochet = now
			play_at(&"ricochet", hit.point, vol - 4.0, 0.1)


func _on_target_hit(kind: StringName, hit: BallisticHit) -> void:
	if hit.shooter == null or not hit.shooter.is_in_group(&"player"):
		return
	var rank: int = 1
	if kind == &"headshot":
		rank = 2
	elif kind == &"kill":
		rank = 3
	if hit.volley_id != 0 and hit.volley_id == _confirm_volley and rank <= _confirm_rank:
		return  # another pellet of a shell that already confirmed
	_confirm_volley = hit.volley_id
	_confirm_rank = rank
	match kind:
		&"headshot":
			play_ui(&"headshot", -2.0, 0.02)
		&"kill":
			play_ui(&"kill", -2.0, 0.02)
		_:
			play_ui(&"hit_marker", -6.0, 0.05)


func _make_buses() -> void:
	for bus_name: StringName in [&"SFX", &"Tail"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			AudioServer.add_bus()
			var idx: int = AudioServer.bus_count - 1
			AudioServer.set_bus_name(idx, bus_name)
			AudioServer.set_bus_send(idx, &"Master")
	var tail: int = AudioServer.get_bus_index(&"Tail")
	if AudioServer.get_bus_effect_count(tail) == 0:
		_reverb = AudioEffectReverb.new()
		_reverb.dry = 0.35
		_reverb.wet = 0.65
		_reverb.predelay_msec = 12.0
		AudioServer.add_bus_effect(tail, _reverb)
	else:
		var fx: AudioEffect = AudioServer.get_bus_effect(tail, 0)
		_reverb = fx as AudioEffectReverb
	set_room(0.55)
