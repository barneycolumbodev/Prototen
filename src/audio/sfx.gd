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
	p.pitch_scale = _pitch(pitch_rand)
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
	p.pitch_scale = _pitch(pitch_rand)
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


func _pitch(rand: float) -> float:
	return clampf(Engine.time_scale, 0.25, 1.0) * (1.0 + _rng.randf_range(-rand, rand))


func _on_hit(hit: BallisticHit) -> void:
	var vol: float = linear_to_db(clampf(hit.energy_in / maxf(hit.weapon.muzzle_energy(), 1.0), 0.15, 1.0))
	var sound: StringName = &"impact_" + String(hit.surface.impact_sound)
	if hit.result == BallisticHit.Result.RICOCHET:
		sound = &"impact_metal"
	play_at(sound, hit.point, vol)


func _on_target_hit(kind: StringName, hit: BallisticHit) -> void:
	if hit.shooter == null or not hit.shooter.is_in_group(&"player"):
		return
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
