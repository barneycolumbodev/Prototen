class_name PlayerWeapon
extends Node
## The player's guns (docs/m1-gunplay-plan.md). Holds a small loadout (the
## suppressed pistol, the MG42 and the RC-6 rail carbine), one viewmodel rig per gun. Reads the
## controller, runs the active gun's GunMechanism, fires rounds through
## Ballistics from the eye (so the round goes exactly where the crosshair or
## sights point, plus the gun's spread), and drives every piece of feedback:
## camera recoil, viewmodel springs, flash, shells, tracers, sound and rumble.
##
## Controls (CLAUDE.md §9.4): RT fire, LT held = aim down sights, X reload,
## Y switches gun (and cancels a reload). Firing during a sprint drops the
## sprint first. The active gun's "Carry" values slow the player down.
##
## Railguns (WeaponData.charge_time > 0): each shot gets the capacitor's
## charge as its power (speed, recoil); a rising whine plays while it
## recharges and a tone when it's full; overheating lifts the vent shroud and
## steams for `vent_time`; the glow strips follow charge and heat.

signal fired
signal ammo_changed(loaded: int, reserve: int)
signal weapon_changed(data: WeaponData)


## One gun in the loadout.
class Slot:
	extends RefCounted
	var data: WeaponData
	var rig: ViewmodelRig
	var mechanism: GunMechanism
	var motion: ViewmodelMotion
	var hip_xform: Transform3D
	var ads_xform: Transform3D

	func _init(p_data: WeaponData, p_rig: ViewmodelRig) -> void:
		data = p_data
		rig = p_rig
		mechanism = GunMechanism.new(data)
		motion = ViewmodelMotion.new(data)
		hip_xform = rig.config.weapon_transform()
		ads_xform = PlayerWeapon.ads_transform(data)


## Guns in switch order, and the viewmodel rig of each (same order).
@export var loadout: Array[WeaponData] = [
	preload("res://data/weapons/pistol_57.tres"),
	preload("res://data/weapons/mg42.tres"),
	preload("res://data/weapons/rail_carbine.tres"),
]
@export var rig_paths: Array[NodePath] = [^"../Head/Camera3D/Viewmodel", ^"../Head/Camera3D/ViewmodelMG42",
		^"../Head/Camera3D/ViewmodelRail"]
@export var input_enabled: bool = true

var slots: Array[Slot] = []
var current: int = 0
## Active gun's data / mechanism / procedural motion.
var data: WeaponData:
	get:
		return slots[current].data if not slots.is_empty() else loadout[0]
var mechanism: GunMechanism:
	get:
		return slots[current].mechanism
var motion: ViewmodelMotion:
	get:
		return slots[current].motion
## 0..1 aim-down-sights amount (linear in time; `ads_visual()` is eased).
var ads: float = 0.0
var aim_held: bool = false
## Extra spread from rapid fire, degrees.
var bloom: float = 0.0
## Seconds of sustained fire (drives the hip walk of heavy guns).
var sustained: float = 0.0
## Current full-width spread cone in degrees (HUD reticle reads this).
var spread: float = 0.0
## Camera recoil spring, degrees: x = pitch up, y = yaw right, z = roll.
var cam_recoil: Spring
## Gun being switched to (-1 = not switching) and holster time left.
var switching_to: int = -1

var _player: Player
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _sprint_out: float = 0.0
var _holster_left: float = 0.0
var _since_shot: float = 99.0
var _shots: int = 0
var _tail_cooldown: float = 0.0
var _belt_shake: Spring
var _cover_closed_sound: bool = true
## Railgun charge whine (stopped when the next shot fires).
var _charge_voice: AudioStreamPlayer
var _glow_time: float = 0.0
## Scripted input for tests and the capture demo (overrides the controller).
var _script_pull: bool = false
var _script_aim: bool = false
var _script_reload: bool = false
var _script_switch: bool = false
var _scripted: bool = false


func _ready() -> void:
	_rng.randomize()
	_player = get_parent() as Player
	for i: int in loadout.size():
		var rig: ViewmodelRig = get_node(rig_paths[i]) as ViewmodelRig
		slots.append(Slot.new(loadout[i], rig))
		rig.visible = i == current
	cam_recoil = Spring.new(data.camera_spring_hz, data.camera_spring_damping)
	_belt_shake = Spring.new(14.0, 0.25)
	_player.landed.connect(func(speed: float) -> void: motion.landed(speed))
	EventBus.target_hit.connect(_on_target_hit)
	_emit_ammo.call_deferred()


func _emit_ammo() -> void:
	ammo_changed.emit(mechanism.loaded(), mechanism.reserve)


## Weapon placement (camera space) that puts the eye on the sight line.
static func ads_transform(d: WeaponData) -> Transform3D:
	var eye: Transform3D = Transform3D(Basis.looking_at(d.ads_look_target - d.ads_eye_position, Vector3.UP), d.ads_eye_position)
	return eye.affine_inverse()


func rig() -> ViewmodelRig:
	return slots[current].rig


## Eased ADS amount for visuals, FOV and sensitivity.
func ads_visual() -> float:
	return ads * ads * (3.0 - 2.0 * ads)


func is_reloading() -> bool:
	return mechanism.state == GunMechanism.State.RELOADING


func is_switching() -> bool:
	return switching_to >= 0


func index_of(display_name: String) -> int:
	for i: int in slots.size():
		if slots[i].data.display_name == display_name:
			return i
	return -1


## Drives the gun without a controller (tests, capture demos).
func script_input(pull: bool, aim: bool, reload: bool = false, switch: bool = false) -> void:
	_scripted = true
	_script_pull = pull
	_script_aim = aim
	_script_reload = reload
	_script_switch = switch


func end_script_input() -> void:
	_scripted = false


## Switches to gun `index` immediately, already drawn (tests, demos, spawn).
func select_now(index: int) -> void:
	if index < 0 or index >= slots.size():
		return
	_activate(index)
	motion.pose_pos.reset()
	motion.pose_rot.reset()
	mechanism.state = GunMechanism.State.READY


## Starts putting the current gun away; the next one is drawn after.
func request_switch(index: int = -1) -> void:
	if slots.size() < 2 or is_switching():
		return
	var target: int = (current + 1) % slots.size() if index < 0 else index
	if target == current:
		return
	for ev: StringName in mechanism.holster():
		_handle(ev)
	_stop_charge_whine()
	switching_to = target
	_holster_left = data.holster_time
	Sfx.play_ui(&"holster", -4.0)


## Re-reads tuning that springs cache (call after editing `data` live).
func apply_tuning() -> void:
	for s: Slot in slots:
		s.motion.apply_tuning()
		s.ads_xform = ads_transform(s.data)
	cam_recoil.frequency = data.camera_spring_hz
	cam_recoil.damping = data.camera_spring_damping


func _activate(index: int) -> void:
	current = index
	for i: int in slots.size():
		slots[i].rig.visible = i == current
	switching_to = -1
	bloom = 0.0
	sustained = 0.0
	apply_tuning()
	weapon_changed.emit(data)
	ammo_changed.emit(mechanism.loaded(), mechanism.reserve)


func _physics_process(delta: float) -> void:
	var active: bool = input_enabled and _player.input_enabled
	var pull: bool = false
	var held: bool = false
	var reload: bool = false
	var switch: bool = false
	if _scripted:
		pull = _script_pull
		held = _script_pull
		reload = _script_reload
		switch = _script_switch
		aim_held = _script_aim
		_script_pull = false
		_script_reload = false
		_script_switch = false
	elif active:
		pull = Input.is_action_just_pressed(&"fire")
		held = Input.is_action_pressed(&"fire")
		reload = Input.is_action_just_pressed(&"reload")
		switch = Input.is_action_just_pressed(&"switch_weapon")
		aim_held = Input.is_action_pressed(&"aim")
	else:
		aim_held = false

	if switch:
		request_switch()
	if is_switching():
		_holster_left -= delta
		pull = false
		held = false
		reload = false
		if _holster_left <= 0.0:
			var next: int = switching_to
			_activate(next)
			motion.start_draw()
			mechanism.draw()
			Sfx.play_ui(&"draw", -4.0)

	# Aiming or shooting beats sprinting.
	_player.sprint_blocked = aim_held
	if (pull or aim_held) and _player.is_sprinting():
		_player.stop_sprint()
	if _player.is_sprinting():
		_sprint_out = data.sprint_to_fire
	else:
		_sprint_out = maxf(0.0, _sprint_out - delta)
	var blocked: bool = _player.is_sprinting() or _sprint_out > 0.0 or is_switching()

	# Holstered guns keep recharging and cooling.
	for i: int in slots.size():
		if i != current:
			slots[i].mechanism.idle(delta)
	var before: int = mechanism.loaded()
	var events: Array[StringName] = mechanism.update(delta, pull, held, reload, blocked)
	for ev: StringName in events:
		_handle(ev)
	if mechanism.loaded() != before or events.has(GunMechanism.EV_MAG_IN):
		ammo_changed.emit(mechanism.loaded(), mechanism.reserve)

	# ADS: hold LT. Reloading and switching drop the sights.
	var can_aim: bool = aim_held and not is_reloading() and not _player.is_sprinting() and not is_switching()
	ads = move_toward(ads, 1.0 if can_aim else 0.0, delta / maxf(data.ads_time, 0.01))
	bloom = maxf(0.0, bloom - data.bloom_recovery_deg_s * delta)
	_since_shot += delta
	_tail_cooldown -= delta
	if _since_shot < data.fire_interval * 2.5 + 0.03:
		sustained += delta
	else:
		sustained = maxf(0.0, sustained - delta * 3.0)
	var walk: float = minf(sustained * data.hip_walk_deg_s, data.hip_walk_max_deg)
	spread = data.spread_deg(ads, _move_fraction(), not _player.is_on_floor(), bloom, walk)


func _process(delta: float) -> void:
	var a: float = ads_visual()
	# Camera: recoil springs back; FOV and look speed follow the sights.
	cam_recoil.step(delta)
	_player.set_camera_recoil(cam_recoil.value)
	_player.fov_scale = lerpf(1.0, data.ads_fov_scale, a)
	_player.look_scale = lerpf(1.0, data.ads_sensitivity * data.ads_fov_scale, a) * data.carry_turn_scale
	_player.move_scale = lerpf(1.0, data.ads_move_speed, a) * data.carry_speed_scale
	_player.sprint_scale = data.carry_sprint_scale
	_player.jump_scale = data.carry_jump_scale
	if _player.aim_assist:
		_player.aim_assist.ads = a

	var pose: int = 0
	if is_switching():
		pose = 3
	elif is_reloading():
		pose = 2
	elif _player.is_sprinting():
		pose = 1
	var s: Slot = slots[current]
	s.motion.update(delta, a, _player.look_velocity, _move_fraction(), _player.is_on_floor(), pose)
	s.rig.transform = s.motion.compose(s.hip_xform, s.ads_xform, a)
	s.rig.set_slide(s.motion.slide * data.slide_travel)
	s.rig.set_magazine_out(_mag_offset(), data.magazine_travel)
	s.rig.set_aimed(a)
	if data.is_rail():
		_update_rail_visuals(delta, s)
	if data.cover_open_deg > 0.0:
		var cover: float = _cover_open()
		s.rig.set_cover_open(cover * data.cover_open_deg, data.cover_hinge)
		if cover > 0.5:
			_cover_closed_sound = false
		elif not _cover_closed_sound and is_reloading():
			_cover_closed_sound = true
			_play(&"slide_release")
			s.motion.jolt(Vector3(0, -0.006, 0.004), Vector3(-2, 0, -3))
			_rumble(Vector3(0.3, 0.35, 0.08))
	if data.belt_jiggle > 0.0:
		_belt_shake.step(delta)
		s.rig.set_belt_offset(_belt_shake.value)


## Glow strips follow the capacitor (dim after a shot, bright when full) and
## heat (toward orange, pulsing while venting); the vent shroud lifts and
## steams while the rails vent.
func _update_rail_visuals(delta: float, s: Slot) -> void:
	_glow_time += delta
	var m: GunMechanism = s.mechanism
	var charge: float = m.charge()
	var energy: float = lerpf(data.glow_energy.x, data.glow_energy.y, charge * charge)
	energy *= 1.0 + 0.8 * m.heat
	# Discharge flash on the shot itself.
	energy += data.glow_energy.y * 2.5 * exp(-m.since_shot() * 22.0)
	if m.venting:
		energy *= 0.75 + 0.25 * sin(_glow_time * 14.0)
	s.rig.set_glow(data.glow_color.lerp(data.glow_hot_color, pow(m.heat, 0.8)), energy)
	var p: float = m.vent_progress()
	var open: float = smoothstep(0.0, 0.1, p) * (1.0 - smoothstep(0.85, 1.0, p)) if m.venting else 0.0
	s.rig.set_vent(open * data.vent_lift)
	if open > 0.3:
		var at: Vector3 = s.rig.global_transform * Vector3(0.2, 0.06, 0.0)
		Fx.vent_steam(at, s.rig.global_basis.y, 1.0 - p * 0.6)


## The charge whine plays on a shared voice; only stop it if it's still ours.
func _stop_charge_whine() -> void:
	if _charge_voice and _charge_voice.playing and _charge_voice.stream in Sfx.bank(Sfx.weapon_bank(data, &"charge")):
		_charge_voice.stop()
	_charge_voice = null


func _move_fraction() -> float:
	var v: Vector3 = _player.velocity
	return Vector2(v.x, v.z).length() / maxf(_player.movement.walk_speed, 0.1)


## Magazine (or ammo box) drop distance during a reload.
func _mag_offset() -> float:
	if not is_reloading():
		return 0.0
	var t: float = mechanism.reload_progress()
	var out_t: float = data.mag_out_point
	var in_t: float = data.mag_in_point
	if t < out_t:
		return 0.0
	if t < in_t:
		var k: float = (t - out_t) / maxf(in_t - out_t, 0.01)
		return 0.2 * sin(k * PI)  # old mag drops away, new one comes up
	return 0.0


## 0..1 how far the feed cover is open: up before the box comes off, down
## (slammed) just after the new belt is laid.
func _cover_open() -> float:
	if not is_reloading():
		return 0.0
	var t: float = mechanism.reload_progress()
	var open_end: float = data.mag_out_point * 0.85
	var close_start: float = data.mag_in_point + 0.08
	if t < open_end:
		return smoothstep(0.0, open_end, t)
	if t < close_start:
		return 1.0
	return 1.0 - smoothstep(close_start, close_start + 0.07, t)


func _play(event_name: StringName, volume_db: float = 0.0) -> void:
	Sfx.play_weapon(data, event_name, volume_db)


func _handle(ev: StringName) -> void:
	match ev:
		GunMechanism.EV_FIRE:
			_fire()
		GunMechanism.EV_LAST_ROUND:
			motion.lock_slide()
		GunMechanism.EV_DRY_FIRE:
			_play(&"dry_fire")
			motion.jolt(Vector3(0, 0, 0.003), Vector3(0, 0, 0.6))
		GunMechanism.EV_RELOAD_START:
			_play(&"reload_start", -6.0)
		GunMechanism.EV_MAG_OUT:
			_play(&"mag_out")
			motion.jolt(Vector3(0, -0.004, 0), Vector3(-3, 0, 2))
		GunMechanism.EV_MAG_IN:
			_play(&"mag_in")
			motion.jolt(Vector3(0, 0.01, 0), Vector3(4, 0, 5))
			_rumble(Vector3(0.0, 0.2, 0.04))
		GunMechanism.EV_SLIDE_RELEASE:
			_play(&"slide_release")
			motion.release_slide()
			motion.jolt(Vector3(0, 0, 0.008), Vector3(-2, 0, 3))
			_rumble(Vector3(0.15, 0.1, 0.04))
		GunMechanism.EV_RELOAD_CANCEL:
			_play(&"reload_cancel", -8.0)
		GunMechanism.EV_CHARGED:
			_play(&"ready", -6.0)
		GunMechanism.EV_OVERHEAT:
			_stop_charge_whine()
			_play(&"overheat", -4.0)
			_play(&"vent", -2.0)
			motion.jolt(Vector3(0, -0.004, 0.006), Vector3(-1.5, 0, -2.5))
			_rumble(Vector3(0.2, 0.15, 0.25))
		GunMechanism.EV_VENT_DONE:
			_play(&"ready", -4.0)
			motion.jolt(Vector3(0, 0.003, 0), Vector3(0, 0, 1.5))


func _fire() -> void:
	var cam: Camera3D = _player.camera()
	var eye: Transform3D = cam.global_transform
	var forward: Vector3 = -eye.basis.z
	var dir: Vector3 = Ballistics.random_in_cone(forward, spread, _rng)
	var gun: Transform3D = rig().global_transform
	var muzzle: Transform3D = gun * Transform3D(Basis(), data.muzzle_point)
	_shots += 1
	var tracer: bool = (data.tracer_every > 0 and _shots % data.tracer_every == 0) or data.beam_trail_time > 0.0
	var power: float = mechanism.last_power
	Ballistics.fire(data, eye.origin, dir, _player, muzzle.origin if tracer else Vector3.INF, power)
	EventBus.shot_fired.emit(_player, eye.origin, dir)

	var a: float = ads_visual()
	# Recoil is the slug's momentum: it goes with speed, √power.
	var strength: float = sqrt(power)
	var s: float = lerpf(1.0, data.ads_recoil_scale, a) * strength
	var pitch_kick: float = data.kick_pitch_deg * _rng.randf_range(0.9, 1.1) * s
	var yaw_kick: float = (_rng.randf_range(-1.0, 1.0) * data.kick_yaw_deg + data.kick_yaw_bias_deg) * s
	cam_recoil.kick(Vector3(pitch_kick, yaw_kick, _rng.randf_range(-0.4, 0.4) * s) * (1.0 - data.kick_permanent))
	# The part that stays: muzzle climb the player pulls down.
	_player.set_view(_player.yaw - deg_to_rad(yaw_kick * data.kick_permanent),
			_player.pitch + deg_to_rad(pitch_kick * data.kick_permanent))
	bloom = minf(bloom + data.bloom_per_shot_deg, data.bloom_max_deg)
	_since_shot = 0.0
	motion.fire(a, _rng, strength)
	if data.belt_jiggle > 0.0:
		_belt_shake.kick(Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(0.2, 1.0), _rng.randf_range(-1.0, 1.0)) * data.belt_jiggle)

	Fx.muzzle_flash(muzzle, data)
	if data.ejects_shells:
		var eject_vel: Vector3 = gun.basis * data.ejection_velocity + _player.velocity
		Fx.eject_shell(gun * data.ejection_point, eject_vel, gun.basis)
	Sfx.play_shot(data, _tail_cooldown <= 0.0, linear_to_db(lerpf(0.55, 1.0, power)))
	if _tail_cooldown <= 0.0:
		_tail_cooldown = data.tail_interval
	if data.is_rail():
		_stop_charge_whine()
		if not mechanism.venting:
			_charge_voice = Sfx.play_ui(Sfx.weapon_bank(data, &"charge"), -10.0, 0.0)
	_rumble(data.rumble_fire * Vector3(strength, strength, 1.0))
	fired.emit()


func _on_target_hit(kind: StringName, hit: BallisticHit) -> void:
	if hit.shooter != _player:
		return
	match kind:
		&"headshot":
			TimeControl.hitstop(data.hitstop_headshot, data.hitstop_time_scale)
			_rumble(data.rumble_kill)
		&"kill":
			var head: bool = hit.damage != null and hit.damage.has_flag(DamageInfo.Flags.HEADSHOT)
			TimeControl.hitstop(data.hitstop_headshot if head else data.hitstop_kill, data.hitstop_time_scale)
			_rumble(data.rumble_kill)
		_:
			_rumble(data.rumble_hit)


## `r`: weak motor, strong motor, seconds.
func _rumble(r: Vector3) -> void:
	if r.z <= 0.0:
		return
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, r.x, r.y, r.z)
