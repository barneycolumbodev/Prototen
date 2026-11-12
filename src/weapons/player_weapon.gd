class_name PlayerWeapon
extends Node
## The player's guns (docs/m1-gunplay-plan.md). Holds a small loadout (the
## suppressed pistol, the MG42, the Saiga-12K, the RC-6 rail carbine and the M14/P), one viewmodel rig per gun. Reads the
## controller, runs the active gun's GunMechanism, fires rounds through
## Ballistics from the eye (so the round goes exactly where the crosshair or
## sights point, plus the gun's spread), and drives every piece of feedback:
## camera recoil, viewmodel springs, flash, shells, tracers, sound and rumble.
##
## Controls (CLAUDE.md §9.4): RT fire, LT held = aim down sights, X reload.
## Y: a tap swaps back to the previous gun; holding it opens the weapon wheel
## (time slows, the right stick picks a gun, letting go draws it). Switching
## cancels a reload. `over_enemy` says whether the line of sight is on an
## enemy (reticles turn crimson, ReticleStyle). Firing during a sprint drops the
## sprint first. The active gun's "Carry" values slow the player down.
##
## Guns with shell types (WeaponData.ammo_types): D-pad right/left picks the
## next/previous load; a moment after the last press the gun swaps to a
## magazine of it and racks the old shell out (GunMechanism). Each shot fires
## the load in the chamber (`pellets` projectiles in a pattern). A load with
## `use_optic` mounts the optic: aiming goes through it, and near full aim the
## viewmodel hides behind the HUD's scope view (`scope_amount()`).
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
	var optic_xform: Transform3D
	## What one round of each load is fired with (AmmoData.apply_to), same order as data.ammo_types.
	var rounds: Array[WeaponData] = []

	func _init(p_data: WeaponData, p_rig: ViewmodelRig) -> void:
		data = p_data
		rig = p_rig
		mechanism = GunMechanism.new(data)
		motion = ViewmodelMotion.new(data)
		hip_xform = rig.config.weapon_transform()
		ads_xform = PlayerWeapon.ads_transform(data)
		optic_xform = PlayerWeapon.eye_transform(data.optic_eye_position, data.optic_look_target)
		build_rounds()

	func build_rounds() -> void:
		rounds.clear()
		for a: AmmoData in data.ammo_types:
			rounds.append(a.apply_to(data))

	## Round data for load `index` (the gun's own data if it has no shell types).
	func round_for(index: int) -> WeaponData:
		return rounds[index] if index >= 0 and index < rounds.size() else data

	func ammo(index: int) -> AmmoData:
		return data.ammo_types[index] if index >= 0 and index < data.ammo_types.size() else null


## Guns in switch order, and the viewmodel rig of each (same order).
@export var loadout: Array[WeaponData] = [
	preload("res://data/weapons/pistol_57.tres"),
	preload("res://data/weapons/mg42.tres"),
	preload("res://data/weapons/saiga12k.tres"),
	preload("res://data/weapons/rail_carbine.tres"),
	preload("res://data/weapons/m14p.tres"),
]
@export var rig_paths: Array[NodePath] = [^"../Head/Camera3D/Viewmodel", ^"../Head/Camera3D/ViewmodelMG42",
		^"../Head/Camera3D/ViewmodelSaiga", ^"../Head/Camera3D/ViewmodelRail", ^"../Head/Camera3D/ViewmodelM14"]
@export var input_enabled: bool = true
@export var wheel_config: WeaponWheelConfig = preload("res://data/input/weapon_wheel.tres")

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
## Current full-width spread cone in degrees (where the shot is centred).
var spread: float = 0.0
## Spread plus the pellet pattern: the cone the whole shot lands in (HUD reticle).
var reticle_spread: float = 0.0
## Camera recoil spring, degrees: x = pitch up, y = yaw right, z = roll.
var cam_recoil: Spring
## Gun being switched to (-1 = not switching) and holster time left.
var switching_to: int = -1
## Gun drawn before this one (a tap on Y goes back to it; -1 = none yet).
var previous: int = -1
## Weapon wheel: open, and the slot the stick points at.
var wheel_open: bool = false
var wheel_pick: int = 0
## The line of sight is on a live enemy; `enemy_amount` eases 0..1 for colour.
var over_enemy: bool = false
var enemy_amount: float = 0.0

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
var _script_ammo: int = 0
var _scripted: bool = false
## Scripted weapon-wheel input (tests): Y held, right stick.
var _script_wheel: bool = false
var _script_y: bool = false
var _script_stick: Vector2 = Vector2.ZERO
## Real time (ms) Y went down, -1 when it's up.
var _y_down_ms: int = -1
## Countdown from the last shell-type press to the swap (-1 = none pending).
var _select_left: float = -1.0


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
	return eye_transform(d.ads_eye_position, d.ads_look_target)


## Weapon placement (camera space) with the eye at `eye` looking at `look` (weapon space).
static func eye_transform(eye_pos: Vector3, look: Vector3) -> Transform3D:
	var dir: Vector3 = look - eye_pos
	if dir.length_squared() < 0.0001:
		dir = Vector3(1, 0, 0)
	var eye: Transform3D = Transform3D(Basis.looking_at(dir, Vector3.UP), eye_pos)
	return eye.affine_inverse()


func has_shell_types() -> bool:
	return not data.ammo_types.is_empty()


## The load in the chamber (fires next), in the magazine, and selected (null for guns without shell types).
func chamber_ammo() -> AmmoData:
	return slots[current].ammo(mechanism.chamber_ammo)


func magazine_ammo() -> AmmoData:
	return slots[current].ammo(mechanism.mag_ammo)


func selected_ammo() -> AmmoData:
	return slots[current].ammo(mechanism.load_ammo)


## What the next shot fires: the chambered load's round data.
func round_data() -> WeaponData:
	return slots[current].round_for(mechanism.chamber_ammo)


## A shell-type press is waiting out its delay, or the swap it asked for hasn't finished.
func swap_pending() -> bool:
	return has_shell_types() and (mechanism.needs_swap() or _select_left >= 0.0)


## Picks the next (+1) or previous (-1) load. The swap starts after `ammo_select_delay`.
func select_ammo(step: int) -> void:
	if not has_shell_types() or step == 0:
		return
	mechanism.load_ammo = posmod(mechanism.load_ammo + step, data.ammo_types.size())
	_select_left = data.ammo_select_delay
	Sfx.play_ui(&"ammo_select", -6.0)


## Loads `index` straight away, chamber and magazine (tests, demos, spawn).
func select_ammo_now(index: int) -> void:
	if index < 0 or index >= data.ammo_types.size():
		return
	mechanism.load_ammo = index
	mechanism.mag_ammo = index
	mechanism.chamber_ammo = index
	_select_left = -1.0


## The load the magazine in view holds: the new one once the old magazine is out of sight.
func _shown_ammo() -> int:
	if is_reloading() and mechanism.reload_progress() > (data.mag_out_point + data.mag_in_point) * 0.5:
		return mechanism.load_ammo
	return mechanism.mag_ammo


## The optic is mounted (the magazine in view holds a load that uses it).
func optic_on() -> bool:
	var a: AmmoData = slots[current].ammo(_shown_ammo())
	return a != null and a.use_optic


## 0..1 how far the view has gone through the optic (HUD scope view, viewmodel hidden).
func scope_amount() -> float:
	if not optic_on():
		return 0.0
	return smoothstep(0.72, 0.96, ads_visual())


func rig() -> ViewmodelRig:
	return slots[current].rig


## Eased ADS amount for visuals, FOV and sensitivity.
func ads_visual() -> float:
	return ads * ads * (3.0 - 2.0 * ads)


func is_reloading() -> bool:
	return mechanism.state == GunMechanism.State.RELOADING


func is_switching() -> bool:
	return switching_to >= 0


## An active part has the hands (the GX-4 arm cannon): the gun goes down and
## stays down, no firing, reloading, switching or aiming until unstow().
var stowed: bool = false
## The part holding the hands while stowed (the HUD shows its rounds).
var stowed_by: ActivePart
var _stow_left: float = 0.0


func stow() -> void:
	if stowed:
		return
	stowed = true
	if wheel_open:
		_close_wheel(false)
	for ev: StringName in mechanism.holster():
		_handle(ev)
	_stop_charge_whine()
	_stow_left = data.holster_time / handling()
	Sfx.play_ui(&"holster", -4.0)


func unstow() -> void:
	if not stowed:
		return
	stowed = false
	stowed_by = null
	_stow_left = 0.0
	slots[current].rig.visible = true
	motion.start_draw()
	mechanism.draw()
	Sfx.play_ui(&"draw", -4.0)


## The gun is all the way down (hidden) while stowed.
func is_stowed_away() -> bool:
	return stowed and _stow_left <= 0.0


func index_of(display_name: String) -> int:
	for i: int in slots.size():
		if slots[i].data.display_name == display_name:
			return i
	return -1


## Drives the gun without a controller (tests, capture demos).
## `ammo_step`: a D-pad shell-type press (+1 next, -1 previous).
func script_input(pull: bool, aim: bool, reload: bool = false, switch: bool = false, ammo_step: int = 0) -> void:
	_scripted = true
	_script_pull = pull
	_script_aim = aim
	_script_reload = reload
	_script_switch = switch
	_script_ammo = ammo_step


func end_script_input() -> void:
	_scripted = false
	_script_wheel = false


## Drives Y and the right stick for the weapon wheel without a controller (tests).
func script_wheel(y_held: bool, stick: Vector2 = Vector2.ZERO) -> void:
	_script_wheel = true
	_script_y = y_held
	_script_stick = stick


## Wheel slot the stick points at: slot 0 at the top, then clockwise.
## `stick` uses Input.get_vector axes (x right, y down).
static func wheel_slot(stick: Vector2, count: int) -> int:
	if count <= 0:
		return 0
	var angle: float = atan2(stick.x, -stick.y)
	return posmod(roundi(angle / (TAU / count)), count)


## A tap on Y: back to the gun you had before (the next one if there isn't one).
func quick_switch() -> void:
	var target: int = previous if previous >= 0 and previous != current else (current + 1) % slots.size()
	request_switch(target)


func _open_wheel() -> void:
	wheel_open = true
	wheel_pick = current
	_player.look_blocked = true
	TimeControl.set_slowmo(wheel_config.time_scale)
	Sfx.play_ui(&"wheel_open", -6.0)


## Closes the wheel; `apply` draws the highlighted gun.
func _close_wheel(apply: bool) -> void:
	wheel_open = false
	_player.look_blocked = false
	TimeControl.set_slowmo(1.0)
	if apply and wheel_pick != current and wheel_pick != switching_to:
		request_switch(wheel_pick)


## Y and the wheel, in real time (the wheel slows the game down).
func _update_wheel() -> void:
	var active: bool = input_enabled and _player.input_enabled and not stowed
	var held: bool = _script_y if _script_wheel else (active and not _scripted and Input.is_action_pressed(&"switch_weapon"))
	var now: int = Time.get_ticks_msec()
	if held and _y_down_ms < 0:
		_y_down_ms = now
	if held and not wheel_open and slots.size() > 2 and now - _y_down_ms >= int(wheel_config.hold_time * 1000.0):
		_open_wheel()
	if wheel_open:
		var stick: Vector2 = _script_stick if _script_wheel else Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.0)
		if stick.length() >= wheel_config.stick_deadzone:
			var pick: int = wheel_slot(stick, slots.size())
			if pick != wheel_pick:
				wheel_pick = pick
				Sfx.play_ui(&"wheel_tick", -12.0, 0.02)
	if not held and _y_down_ms >= 0:
		_y_down_ms = -1
		if wheel_open:
			_close_wheel(true)
		else:
			quick_switch()


## Is the first thing along the line of sight a live enemy?
func _check_enemy() -> void:
	var cam: Camera3D = _player.camera()
	if cam == null or not cam.is_inside_tree():
		over_enemy = false
		return
	var from: Vector3 = cam.global_position
	var to: Vector3 = from - cam.global_basis.z * minf(round_data().max_range, 400.0)
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, Ballistics.BULLET_MASK)
	q.collide_with_areas = false
	var res: Dictionary = cam.get_world_3d().direct_space_state.intersect_ray(q)
	over_enemy = false
	if res.is_empty():
		return
	var hit_obj: Object = res["collider"]
	var n: Node = hit_obj as Node
	for i: int in 9:
		if n == null:
			return
		if n.is_in_group(&"enemies"):
			over_enemy = true
			return
		n = n.get_parent()


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
	_holster_left = data.holster_time / handling()
	Sfx.play_ui(&"holster", -4.0)


# ------------------------------------------------------------------ body stats (docs/design.md §3.6)

func _stat(s: StringName) -> float:
	return _player.body.stat(s) if _player and _player.body else 1.0


## Proficiency with the current gun's class (handgun, shotgun, rifle, heavy).
func proficiency() -> float:
	return _player.body.proficiency(data.weapon_class) if _player and _player.body else 1.0


## Recoil multiplier: recoil stat ÷ proficiency (heavy: also strength, structure).
func recoil_scale() -> float:
	return _player.body.recoil_scale(data.weapon_class) if _player and _player.body else 1.0


func aim_rate() -> float:
	return maxf(_stat(&"aim_speed") * proficiency(), 0.1)


func reload_rate() -> float:
	return maxf(_stat(&"reload_speed") * proficiency(), 0.1)


func handling() -> float:
	return maxf(_stat(&"handling"), 0.1)


## A heavy gun's handling penalty (1 - scale) shrinks with the body's carry
## stat: base carry ÷ carry, so TL-3 (+25 kg) takes off ~40 % and the DL-1
## frame (+55 kg) ~60 %.
func carry_scale(scale: float) -> float:
	if _player == null or _player.body == null or is_equal_approx(scale, 1.0):
		return scale
	var k: float = clampf(_player.body.frame.carry_kg / maxf(_player.body.stat(&"carry_kg"), 1.0), 0.0, 2.0)
	return clampf(1.0 - (1.0 - scale) * k, 0.1, 1.0)


## Re-reads tuning that springs cache (call after editing `data` live).
func apply_tuning() -> void:
	for s: Slot in slots:
		s.motion.apply_tuning()
		s.ads_xform = ads_transform(s.data)
		s.optic_xform = eye_transform(s.data.optic_eye_position, s.data.optic_look_target)
		s.build_rounds()
	cam_recoil.frequency = data.camera_spring_hz
	cam_recoil.damping = data.camera_spring_damping


func _activate(index: int) -> void:
	if index != current:
		previous = current
	current = index
	for i: int in slots.size():
		slots[i].rig.visible = i == current
	switching_to = -1
	_select_left = -1.0
	bloom = 0.0
	sustained = 0.0
	apply_tuning()
	weapon_changed.emit(data)
	ammo_changed.emit(mechanism.loaded(), mechanism.reserve)


func _physics_process(delta: float) -> void:
	# The gun runs in the player's time (faster than the world while dilated).
	delta *= TimeControl.player_boost()
	var active: bool = input_enabled and _player.input_enabled
	var pull: bool = false
	var held: bool = false
	var reload: bool = false
	var switch: bool = false
	var ammo_step: int = 0
	if _scripted:
		pull = _script_pull
		held = _script_pull
		reload = _script_reload
		switch = _script_switch
		aim_held = _script_aim
		ammo_step = _script_ammo
		_script_pull = false
		_script_reload = false
		_script_switch = false
		_script_ammo = 0
	elif active:
		pull = Input.is_action_just_pressed(&"fire")
		held = Input.is_action_pressed(&"fire")
		reload = Input.is_action_just_pressed(&"reload")
		aim_held = Input.is_action_pressed(&"aim")
		if Input.is_action_just_pressed(&"item_next"):
			ammo_step += 1
		if Input.is_action_just_pressed(&"item_prev"):
			ammo_step -= 1
	else:
		aim_held = false

	# Shell type: pick now, swap once the presses stop.
	if ammo_step != 0 and not is_switching() and not stowed:
		select_ammo(ammo_step)
	if _select_left >= 0.0:
		_select_left -= delta
		if _select_left < 0.0 and mechanism.needs_swap():
			mechanism.request_swap()

	if wheel_open:
		# Picking a gun: no shooting, aiming or shell swaps until the wheel closes.
		pull = false
		held = false
		aim_held = false
	if stowed:
		pull = false
		held = false
		reload = false
		switch = false
		aim_held = false
		if _stow_left > 0.0:
			_stow_left -= delta
			if _stow_left <= 0.0:
				slots[current].rig.visible = false
	if switch:
		quick_switch()
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
	# Holding the trigger keeps auto-sprint from starting again mid-burst.
	_player.auto_sprint_blocked = held or pull
	if (pull or aim_held) and _player.is_sprinting():
		_player.stop_sprint()
	if _player.is_sprinting():
		_sprint_out = data.sprint_to_fire / handling()
	else:
		_sprint_out = maxf(0.0, _sprint_out - delta)
	var blocked: bool = _player.is_sprinting() or _sprint_out > 0.0 or is_switching() or _player.is_mantling() or stowed

	# Holstered guns keep recharging and cooling.
	for i: int in slots.size():
		if i != current:
			slots[i].mechanism.idle(delta)
	var before: int = mechanism.loaded()
	mechanism.reload_rate = reload_rate()
	mechanism.draw_rate = handling()
	var events: Array[StringName] = mechanism.update(delta, pull, held, reload, blocked)
	for ev: StringName in events:
		_handle(ev)
	if mechanism.loaded() != before or events.has(GunMechanism.EV_MAG_IN):
		ammo_changed.emit(mechanism.loaded(), mechanism.reserve)

	# ADS: hold LT. Reloading and switching drop the sights.
	var can_aim: bool = aim_held and not is_reloading() and not _player.is_sprinting() and not is_switching()
	var aim_time: float = (data.optic_ads_time if optic_on() else data.ads_time) / aim_rate()
	ads = move_toward(ads, 1.0 if can_aim else 0.0, delta / maxf(aim_time, 0.01))
	bloom = maxf(0.0, bloom - data.bloom_recovery_deg_s * delta)
	_since_shot += delta
	_tail_cooldown -= delta
	if _since_shot < data.fire_interval * 2.5 + 0.03:
		sustained += delta
	else:
		sustained = maxf(0.0, sustained - delta * 3.0)
	var walk: float = minf(sustained * data.hip_walk_deg_s, data.hip_walk_max_deg)
	var r: WeaponData = round_data()
	# Stability divides the movement and air penalties; proficiency tightens the whole cone (÷ √).
	spread = r.spread_deg(ads, _move_fraction(), not _player.is_on_floor(), bloom, walk, _stat(&"stability")) / sqrt(proficiency())
	reticle_spread = spread + (r.pattern_deg if r.pellets > 1 else 0.0)
	_check_enemy()


func _process(delta: float) -> void:
	delta *= TimeControl.player_boost()
	_update_wheel()
	enemy_amount = move_toward(enemy_amount, 1.0 if over_enemy else 0.0, TimeControl.real_delta(delta / TimeControl.player_boost()) / 0.06)
	var a: float = ads_visual()
	# Camera: recoil springs back; FOV and look speed follow the sights.
	cam_recoil.step(delta)
	_player.set_camera_recoil(cam_recoil.value)
	var optic: bool = optic_on()
	var fov: float = data.optic_fov_scale if optic else data.ads_fov_scale
	var sens: float = data.optic_sensitivity if optic else data.ads_sensitivity
	_player.fov_scale = lerpf(1.0, fov, a)
	_player.look_scale = lerpf(1.0, sens * fov, a) * carry_scale(data.carry_turn_scale)
	_player.move_scale = lerpf(1.0, data.ads_move_speed, a) * carry_scale(data.carry_speed_scale)
	_player.sprint_scale = carry_scale(data.carry_sprint_scale)
	_player.jump_scale = carry_scale(data.carry_jump_scale)
	if _player.aim_assist:
		_player.aim_assist.ads = a

	var pose: int = 0
	if is_switching() or _player.is_mantling() or stowed:
		pose = 3
	elif is_reloading():
		pose = 2
	elif _player.is_sprinting():
		pose = 1
	var s: Slot = slots[current]
	s.motion.update(delta, a, _player.look_velocity, _move_fraction(), _player.is_on_floor(), pose)
	s.rig.transform = s.motion.compose(s.hip_xform, s.optic_xform if optic else s.ads_xform, a)
	var away: float = _player.melee.gun_away() if _player.melee else 0.0
	if away > 0.0:
		# Dropped out of the knife's way (PlayerMelee / KnifeViewmodel).
		var mc: MeleeConfig = _player.melee.cfg
		s.rig.transform.basis = Basis.from_euler(mc.gun_away_rot_deg * (PI / 180.0) * away) * s.rig.transform.basis
		s.rig.transform.origin += mc.gun_away_offset * away
	s.rig.set_slide(s.motion.slide * data.slide_travel)
	s.rig.set_magazine_out(_mag_offset(), data.magazine_travel)
	s.rig.set_aimed(a)
	s.rig.set_reticle_color(ReticleStyle.color(enemy_amount))
	if data.is_rail():
		_update_rail_visuals(delta, s)
	if has_shell_types():
		var shown: AmmoData = s.ammo(_shown_ammo())
		s.rig.set_optic(shown.use_optic)
		s.rig.set_shell_color(shown.color)
		s.rig.set_scoped(scope_amount() > 0.5)
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
			if mechanism.swapping:
				motion.lock_slide()  # hand pulls the charging handle back to rack the old shell out
		GunMechanism.EV_EJECT_CHAMBERED:
			var gun: Transform3D = rig().global_transform
			var spent: AmmoData = slots[current].ammo(mechanism.ejected_ammo)
			var vel: Vector3 = gun.basis * (data.ejection_velocity * 0.6) + _player.velocity
			Fx.eject_shell(gun * data.ejection_point, vel, gun.basis, spent.color if spent and data.shotshell else Color(0, 0, 0, 0))
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
	# The round that just left: the load that was in the chamber.
	var r: WeaponData = slots[current].round_for(mechanism.fired_ammo)
	var shell: AmmoData = slots[current].ammo(mechanism.fired_ammo)
	var cam: Camera3D = _player.camera()
	var eye: Transform3D = cam.global_transform
	var forward: Vector3 = -eye.basis.z
	var dir: Vector3 = Ballistics.random_in_cone(forward, spread, _rng)
	var gun: Transform3D = rig().global_transform
	var muzzle: Transform3D = gun * Transform3D(Basis(), data.muzzle_point)
	_shots += 1
	var tracer: bool = (r.tracer_every > 0 and _shots % r.tracer_every == 0) or r.beam_trail_time > 0.0
	var trail_from: Vector3 = muzzle.origin if tracer or r.embers else Vector3.INF
	# Railguns: the capacitor's charge sets this shot's energy (1 for other guns).
	var power: float = mechanism.last_power
	# Pellets: a pattern around the aim point, all one volley (one shot in the stats).
	var volley: int = 0
	var phase: float = _rng.randf() * TAU
	for i: int in r.pellets:
		var pellet_dir: Vector3 = Ballistics.pattern_dir(dir, r.pattern_deg, i, r.pellets, phase, _rng)
		var id: int = Ballistics.fire(r, eye.origin, pellet_dir, _player, trail_from, volley, power)
		if volley == 0:
			volley = id
	EventBus.shot_fired.emit(_player, eye.origin, dir)

	var a: float = ads_visual()
	# Recoil is the round's momentum: for a railgun it goes with speed, √power.
	var strength: float = sqrt(power)
	var s: float = lerpf(1.0, data.ads_recoil_scale, a) * strength * recoil_scale()
	var pitch_kick: float = r.kick_pitch_deg * _rng.randf_range(0.9, 1.1) * s
	var yaw_kick: float = (_rng.randf_range(-1.0, 1.0) * r.kick_yaw_deg + data.kick_yaw_bias_deg) * s
	cam_recoil.kick(Vector3(pitch_kick, yaw_kick, _rng.randf_range(-0.4, 0.4) * s) * (1.0 - data.kick_permanent))
	# The part that stays: muzzle climb the player pulls down.
	_player.set_view(_player.yaw - deg_to_rad(yaw_kick * data.kick_permanent),
			_player.pitch + deg_to_rad(pitch_kick * data.kick_permanent))
	bloom = minf(bloom + data.bloom_per_shot_deg, data.bloom_max_deg)
	_since_shot = 0.0
	motion.fire(a, _rng, (shell.recoil_scale if shell else 1.0) * strength)
	if data.belt_jiggle > 0.0:
		_belt_shake.kick(Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(0.2, 1.0), _rng.randf_range(-1.0, 1.0)) * data.belt_jiggle)

	Fx.muzzle_flash(muzzle, r)
	if data.ejects_shells:
		var eject_vel: Vector3 = gun.basis * data.ejection_velocity + _player.velocity
		var hull: Color = shell.color if shell and data.shotshell else Color(0, 0, 0, 0)
		Fx.eject_shell(gun * data.ejection_point, eject_vel, gun.basis, hull)
	Sfx.play_shot(r, _tail_cooldown <= 0.0, linear_to_db(lerpf(0.55, 1.0, power)))
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
