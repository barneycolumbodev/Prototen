class_name PlayerWeapon
extends Node
## The player's gun (docs/m1-gunplay-plan.md M1a). Reads the controller,
## runs the GunMechanism, fires rounds through Ballistics from the eye (so
## the round goes exactly where the crosshair/sights point, plus the gun's
## spread), and drives every piece of feedback: camera recoil, viewmodel
## springs, flash, shells, sound and rumble.
##
## Controls (CLAUDE.md §9.4): RT fire, LT held = aim down sights, X reload,
## Y cancels a reload. Firing during a sprint drops the sprint first.

signal fired
signal ammo_changed(loaded: int, reserve: int)

@export var data: WeaponData = preload("res://data/weapons/pistol_57.tres")
@export var rig_path: NodePath = ^"../Head/Camera3D/Viewmodel"
@export var input_enabled: bool = true

var mechanism: GunMechanism
var motion: ViewmodelMotion
## 0..1 aim-down-sights amount (linear in time; `ads_visual()` is eased).
var ads: float = 0.0
var aim_held: bool = false
## Extra spread from rapid fire, degrees.
var bloom: float = 0.0
## Current full-width spread cone in degrees (HUD reticle reads this).
var spread: float = 0.0
## Camera recoil spring, degrees: x = pitch up, y = yaw right, z = roll.
var cam_recoil: Spring

var _player: Player
var _rig: ViewmodelRig
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _sprint_out: float = 0.0
var _was_on_floor: bool = true
var _hip_xform: Transform3D
var _ads_xform: Transform3D
## Scripted input for tests and the capture demo (overrides the controller).
var _script_pull: bool = false
var _script_aim: bool = false
var _script_reload: bool = false
var _scripted: bool = false


func _ready() -> void:
	_rng.randomize()
	_player = get_parent() as Player
	_rig = get_node(rig_path) as ViewmodelRig
	mechanism = GunMechanism.new(data)
	motion = ViewmodelMotion.new(data)
	cam_recoil = Spring.new(data.camera_spring_hz, data.camera_spring_damping)
	_hip_xform = _rig.config.weapon_transform()
	_ads_xform = ads_transform(data)
	_player.landed.connect(func(speed: float) -> void: motion.landed(speed))
	EventBus.target_hit.connect(_on_target_hit)
	ammo_changed.emit.call_deferred(mechanism.loaded(), mechanism.reserve)


## Weapon placement (camera space) that puts the eye on the sight line.
static func ads_transform(d: WeaponData) -> Transform3D:
	var eye: Transform3D = Transform3D(Basis.looking_at(d.ads_look_target - d.ads_eye_position, Vector3.UP), d.ads_eye_position)
	return eye.affine_inverse()


## Eased ADS amount for visuals, FOV and sensitivity.
func ads_visual() -> float:
	return ads * ads * (3.0 - 2.0 * ads)


func is_reloading() -> bool:
	return mechanism.state == GunMechanism.State.RELOADING


## Drives the gun without a controller (tests, capture demos).
func script_input(pull: bool, aim: bool, reload: bool = false) -> void:
	_scripted = true
	_script_pull = pull
	_script_aim = aim
	_script_reload = reload


func end_script_input() -> void:
	_scripted = false


## Re-reads tuning that springs cache (call after editing `data` live).
func apply_tuning() -> void:
	motion.apply_tuning()
	cam_recoil.frequency = data.camera_spring_hz
	cam_recoil.damping = data.camera_spring_damping
	_ads_xform = ads_transform(data)


func _physics_process(delta: float) -> void:
	var active: bool = input_enabled and _player.input_enabled
	var pull: bool = false
	var held: bool = false
	var reload: bool = false
	var cancel: bool = false
	if _scripted:
		pull = _script_pull
		held = _script_pull
		reload = _script_reload
		aim_held = _script_aim
		_script_pull = false
		_script_reload = false
	elif active:
		pull = Input.is_action_just_pressed(&"fire")
		held = Input.is_action_pressed(&"fire")
		reload = Input.is_action_just_pressed(&"reload")
		cancel = Input.is_action_just_pressed(&"switch_weapon")
		aim_held = Input.is_action_pressed(&"aim")
	else:
		aim_held = false

	# Aiming or shooting beats sprinting.
	_player.sprint_blocked = aim_held
	if (pull or aim_held) and _player.is_sprinting():
		_player.stop_sprint()
	if _player.is_sprinting():
		_sprint_out = data.sprint_to_fire
	else:
		_sprint_out = maxf(0.0, _sprint_out - delta)
	var blocked: bool = _player.is_sprinting() or _sprint_out > 0.0

	var before: int = mechanism.loaded()
	var events: Array[StringName] = mechanism.update(delta, pull, held, reload, blocked, cancel)
	for ev: StringName in events:
		_handle(ev)
	if mechanism.loaded() != before or events.has(GunMechanism.EV_MAG_IN):
		ammo_changed.emit(mechanism.loaded(), mechanism.reserve)

	# ADS: hold LT. Reloading drops the sights.
	var ads_target: float = 1.0 if aim_held and not is_reloading() and not _player.is_sprinting() else 0.0
	ads = move_toward(ads, ads_target, delta / maxf(data.ads_time, 0.01))
	bloom = maxf(0.0, bloom - data.bloom_recovery_deg_s * delta)
	spread = data.spread_deg(ads, _move_fraction(), not _player.is_on_floor(), bloom)


func _process(delta: float) -> void:
	var a: float = ads_visual()
	# Camera: recoil springs back; FOV and look speed follow the sights.
	cam_recoil.step(delta)
	_player.set_camera_recoil(cam_recoil.value)
	_player.fov_scale = lerpf(1.0, data.ads_fov_scale, a)
	_player.look_scale = lerpf(1.0, data.ads_sensitivity * data.ads_fov_scale, a)
	_player.move_scale = lerpf(1.0, data.ads_move_speed, a)
	if _player.aim_assist:
		_player.aim_assist.ads = a

	var pose: int = 0
	if is_reloading():
		pose = 2
	elif _player.is_sprinting():
		pose = 1
	motion.update(delta, a, _player.look_velocity, _move_fraction(), _player.is_on_floor(), pose)
	_rig.transform = motion.compose(_hip_xform, _ads_xform, a)
	_rig.set_slide(motion.slide * data.slide_travel)
	_rig.set_magazine_out(_mag_offset())


func _move_fraction() -> float:
	var v: Vector3 = _player.velocity
	return Vector2(v.x, v.z).length() / maxf(_player.movement.walk_speed, 0.1)


## Magazine drop distance during a reload (for a separate magazine mesh).
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


func _handle(ev: StringName) -> void:
	match ev:
		GunMechanism.EV_FIRE:
			_fire()
		GunMechanism.EV_LAST_ROUND:
			motion.lock_slide()
		GunMechanism.EV_DRY_FIRE:
			Sfx.play_ui(&"dry_fire")
			motion.jolt(Vector3(0, 0, 0.003), Vector3(0, 0, 0.6))
		GunMechanism.EV_RELOAD_START:
			Sfx.play_ui(&"reload_start", -6.0)
		GunMechanism.EV_MAG_OUT:
			Sfx.play_ui(&"mag_out")
			motion.jolt(Vector3(0, -0.004, 0), Vector3(-3, 0, 2))
		GunMechanism.EV_MAG_IN:
			Sfx.play_ui(&"mag_in")
			motion.jolt(Vector3(0, 0.01, 0), Vector3(4, 0, 5))
			_rumble(Vector3(0.0, 0.2, 0.04))
		GunMechanism.EV_SLIDE_RELEASE:
			Sfx.play_ui(&"slide_release")
			motion.release_slide()
			motion.jolt(Vector3(0, 0, 0.008), Vector3(-2, 0, 3))
			_rumble(Vector3(0.15, 0.1, 0.04))
		GunMechanism.EV_RELOAD_CANCEL:
			Sfx.play_ui(&"reload_cancel", -8.0)


func _fire() -> void:
	var cam: Camera3D = _player.camera()
	var eye: Transform3D = cam.global_transform
	var forward: Vector3 = -eye.basis.z
	var dir: Vector3 = Ballistics.random_in_cone(forward, spread, _rng)
	Ballistics.fire(data, eye.origin, dir, _player)
	EventBus.shot_fired.emit(_player, eye.origin, dir)

	var a: float = ads_visual()
	var s: float = lerpf(1.0, data.ads_recoil_scale, a)
	var pitch_kick: float = data.kick_pitch_deg * _rng.randf_range(0.9, 1.1) * s
	var yaw_kick: float = (_rng.randf_range(-1.0, 1.0) * data.kick_yaw_deg + data.kick_yaw_bias_deg) * s
	cam_recoil.kick(Vector3(pitch_kick, yaw_kick, _rng.randf_range(-0.4, 0.4) * s) * (1.0 - data.kick_permanent))
	# The part that stays: muzzle climb the player pulls down.
	_player.set_view(_player.yaw - deg_to_rad(yaw_kick * data.kick_permanent),
			_player.pitch + deg_to_rad(pitch_kick * data.kick_permanent))
	bloom = minf(bloom + data.bloom_per_shot_deg, data.bloom_max_deg)
	motion.fire(a, _rng)

	var gun: Transform3D = _rig.global_transform
	Fx.muzzle_flash(gun * Transform3D(Basis(), data.muzzle_point), data)
	var eject_vel: Vector3 = gun.basis * data.ejection_velocity + _player.velocity
	Fx.eject_shell(gun * data.ejection_point, eject_vel, gun.basis)
	Sfx.play_shot(data)
	_rumble(data.rumble_fire)
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
