class_name GaussArm
extends ActivePart
## GX-4 Gauss arm (owner, 2026-11-07; docs/design.md §3.4). The right forearm
## is a prosthetic coilgun.
##
## Deploy (LB with it selected): the gun goes down, the arm comes up into
## view, and the transform animation plays: fist, the fist splits into a
## fork, the forearm plates open, rails telescope out, six coils slide
## forward and lock, fins stand up (raw_assets/augments/gx4_gauss_arm). The
## animation is scrubbed from the part's deploy blend, so it always lines up
## with the state machine; stowing scrubs it backwards.
## Active: RT fires a 40 g slug at 3.2 km/s (Ballistics: it goes through
## bodies and thin cover), with a corkscrew beam, a very loud shot, heavy
## camera and arm kick, an FOV punch, hit-stop and rumble. The charge is
## rounds (10): the LED strip on the forearm shows what's left. Empty, it
## folds away by itself; LB folds it early (the rounds stay). Rounds refill
## one by one while it's stowed.

var cfg: GaussArmData
var rig: Node3D
var model: Node3D
var anim: AnimationPlayer
var anim_name: StringName = &""
var anim_len: float = 1.4
var muzzle_tip: Node3D
var leds: Array[Node3D] = []
var coils: Array[Node3D] = []
## Shots fired since it last deployed (tests, HUD).
var shots: int = 0

var _glow: StandardMaterial3D
var _led: StandardMaterial3D
var _coil_rest: Array[Vector3] = []
var _cooldown: float = 0.0
var _empty_wait: float = -1.0
var _flash: float = 0.0
var _ads: float = 0.0
var _kick_pos: Spring
var _kick_rot: Spring
var _sway: Spring
var _ripple: float = -1.0
var _bob_t: float = 0.0
var _hum: AudioStreamPlayer
var _script_fire: bool = false
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	super._ready()
	cfg = data as GaussArmData
	_rng.randomize()
	_kick_pos = Spring.new(cfg.arm_spring_hz, cfg.arm_spring_damping)
	_kick_rot = Spring.new(cfg.arm_spring_hz, cfg.arm_spring_damping)
	_sway = Spring.new(5.0, 0.7)
	_build_rig()
	_hum = AudioStreamPlayer.new()
	_hum.bus = &"SFX"
	_hum.volume_db = -16.0
	var loop: Array = Sfx.bank(&"gx4_hum")
	if not loop.is_empty():
		_hum.stream = loop[0]
	add_child(_hum)
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	if player and is_instance_valid(player):
		player.fov_punch_deg = 0.0
		player.fov_extra_scale = 1.0


func hud_name() -> String:
	return "GX-4"


func hud_pips() -> int:
	return roundi(data.charge_max)


## Rounds left (whole).
func rounds() -> int:
	return floori(charge + 0.001)


## Fires once on the next frame it can (tests, demos).
func script_fire() -> void:
	_script_fire = true


func _build_rig() -> void:
	rig = Node3D.new()
	rig.name = "GaussArmRig"
	rig.visible = false
	if player:
		player.camera().add_child(rig)
	else:
		add_child(rig)
	model = cfg.scene.instantiate() as Node3D
	rig.add_child(model)
	for n: Node in model.find_children("*", "AnimationPlayer", true, false):
		anim = n as AnimationPlayer
		break
	if anim:
		var names: PackedStringArray = anim.get_animation_list()
		if not names.is_empty():
			anim_name = StringName(names[0])
			anim_len = anim.get_animation(anim_name).length
			anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
			anim.play(anim_name)
			anim.seek(0.0, true)
	muzzle_tip = model.find_child("muzzle_tip", true, false) as Node3D
	for k: int in 10:
		var led: Node3D = model.find_child("led_%d" % k, true, false) as Node3D
		if led:
			leds.append(led)
	for k: int in 6:
		var c: Node3D = model.find_child("coil_%d" % (k + 1), true, false) as Node3D
		if c:
			coils.append(c)
	_glow = StandardMaterial3D.new()
	_glow.albedo_color = Color(0.05, 0.08, 0.12)
	_glow.emission_enabled = true
	_glow.emission = cfg.glow_color
	_glow.emission_energy_multiplier = cfg.glow_folded
	_led = _glow.duplicate() as StandardMaterial3D
	_led.emission_energy_multiplier = cfg.glow_armed
	for n: Node in model.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i: int in mi.mesh.get_surface_count():
			var m: Material = mi.mesh.surface_get_material(i)
			if m == null:
				continue
			if m.resource_name == "glow":
				mi.set_surface_override_material(i, _glow)
			elif m.resource_name == "led":
				mi.set_surface_override_material(i, _led)
	_update_leds()


# ------------------------------------------------------------------ states

func _on_start() -> void:
	shots = 0
	_cooldown = 0.0
	_empty_wait = -1.0
	_kick_pos.value = Vector3.ZERO
	_kick_rot.value = Vector3.ZERO
	if player and player.weapon():
		player.weapon().stow()
		player.weapon().stowed_by = self
	rig.visible = true
	_coil_rest.clear()
	_update_leds()
	Sfx.play_ui(&"gx4_deploy", -1.0, 0.0)
	_rumble(Vector3(0.15, 0.35, 0.5))


func _on_stop() -> void:
	_hum.stop()
	Sfx.play_ui(&"gx4_stow", -3.0, 0.0)


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -6.0, 0.0)


func _on_state_changed(s: State) -> void:
	match s:
		State.ACTIVE:
			# A beat for the coils to lock before the first shot.
			_cooldown = 0.12
			_capture_coils()
			if _hum.stream:
				_hum.play()
		State.COOLDOWN:
			# Folded and down: hand the gun back.
			rig.visible = false
			_hum.stop()
			if player:
				player.fov_punch_deg = 0.0
				player.fov_extra_scale = 1.0
				if player.weapon():
					player.weapon().unstow()


func _on_blend(a: float) -> void:
	# Deploying: a 0 -> 1 in real time; stowing: 1 -> 0. The animation follows.
	_seek(a * anim_len)
	if state == State.DEPLOYING:
		var g: float = clampf((a - 0.55) / 0.45, 0.0, 1.0)
		_glow.emission_energy_multiplier = lerpf(cfg.glow_folded, cfg.glow_armed, g)
	elif state == State.RECOVERING:
		_glow.emission_energy_multiplier = lerpf(cfg.glow_folded, cfg.glow_armed, a)


func _seek(t: float) -> void:
	if anim and anim_name != &"":
		anim.seek(clampf(t, 0.0, anim_len), true)


func _capture_coils() -> void:
	_coil_rest.clear()
	for c: Node3D in coils:
		_coil_rest.append(c.position)


# ------------------------------------------------------------------ every frame

## Rounds aren't drained over time (each shot spends one), and an empty
## arm folds away after empty_stow_delay rather than the instant it empties.
func _drain(_real: float) -> void:
	pass


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if rig.visible:
		_update_rig(real)


func _on_active(real: float) -> void:
	_cooldown -= real * TimeControl.player_scale_now()
	if _empty_wait >= 0.0:
		_empty_wait -= real
		if _empty_wait < 0.0:
			stop()
		return
	var can_input: bool = player != null and player.input_enabled and not player.dead and not get_tree().paused
	var want: bool = _script_fire or (can_input and Input.is_action_pressed(&"fire"))
	if want and _cooldown <= 0.0 and rounds() >= 1:
		_script_fire = false
		_fire()
	var aim: bool = can_input and Input.is_action_pressed(&"aim")
	_ads = move_toward(_ads, 1.0 if aim else 0.0, real / maxf(cfg.ads_time, 0.01))


func _update_rig(real: float) -> void:
	var dt: float = real * TimeControl.player_scale_now()
	var base: Transform3D = cfg.viewmodel.weapon_transform()
	# Raise from below during the first part of the deploy (and drop at the end of stowing).
	var up: float = clampf(blend / cfg.raise_share, 0.0, 1.0)
	up = 1.0 - pow(1.0 - up, 3.0)
	var raise: Vector3 = Vector3(0.0, -cfg.raise_drop * (1.0 - up), 0.06 * (1.0 - up))
	var tilt: Vector3 = Vector3(deg_to_rad(-25.0) * (1.0 - up), 0.0, deg_to_rad(10.0) * (1.0 - up))
	# Sway against look speed, a little bob when moving.
	var lv: Vector2 = player.look_velocity if player else Vector2.ZERO
	_sway.target = Vector3(clampf(-lv.y * 0.0006, -0.06, 0.06), clampf(lv.x * 0.0008, -0.08, 0.08), 0.0)
	_sway.step(dt)
	var speed: float = 0.0
	if player:
		speed = Vector2(player.velocity.x, player.velocity.z).length()
	_bob_t += dt * (1.6 + speed * 0.18)
	var bob: float = sin(_bob_t * TAU) * clampf(speed / 11.0, 0.0, 1.0) * 0.008
	_kick_pos.step(dt)
	_kick_rot.step(dt)
	var off: Transform3D = Transform3D.IDENTITY
	off = off.translated(raise + Vector3(0.0, bob, 0.0) + _kick_pos.value)
	off.basis = Basis.from_euler(tilt + _sway.value + _kick_rot.value)
	# LT pulls the arm in toward the centre a touch.
	var ads_shift: Transform3D = Transform3D(Basis.IDENTITY, Vector3(-0.06, 0.025, -0.02) * _ads)
	rig.transform = ads_shift * off * base
	# Glow: flash on a shot, settle to armed.
	_flash = maxf(0.0, _flash - dt * 4.0)
	if state == State.ACTIVE:
		var recharge: float = clampf(1.0 - _cooldown / cfg.fire_interval, 0.0, 1.0)
		_glow.emission_energy_multiplier = lerpf(cfg.glow_folded, cfg.glow_armed, recharge) + cfg.glow_flash * _flash * _flash
	_led.emission_energy_multiplier = cfg.glow_armed + 4.0 * _flash
	# Coils ripple forward one after another after a shot.
	if _ripple >= 0.0 and _coil_rest.size() == coils.size():
		_ripple += dt
		for i: int in coils.size():
			var k: int = coils.size() - 1 - i
			var t: float = _ripple - i * 0.012
			var push: float = 0.0
			if t > 0.0:
				push = sin(minf(t / 0.09, 1.0) * PI) * 0.007
			coils[k].position = _coil_rest[k] + Vector3(push, 0.0, 0.0)
		if _ripple > 0.25:
			_ripple = -1.0
	if player:
		player.fov_punch_deg = move_toward(player.fov_punch_deg, 0.0, player.fov_punch_deg * cfg.fov_punch_recover * real + real)
		player.fov_extra_scale = lerpf(1.0, cfg.ads_fov_scale, _ads)


# ------------------------------------------------------------------ firing

func _fire() -> void:
	charge = maxf(charge - 1.0, 0.0)
	shots += 1
	_cooldown = cfg.fire_interval
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var dir: Vector3 = -cam.global_basis.z
	var spread: float = lerpf(cfg.hip_spread_deg, cfg.ads_spread_deg, _ads)
	if spread > 0.0:
		var axis: Vector3 = dir.cross(Vector3.UP if absf(dir.y) < 0.95 else Vector3.RIGHT).normalized()
		axis = axis.rotated(dir, _rng.randf() * TAU)
		dir = dir.rotated(axis, deg_to_rad(spread) * sqrt(_rng.randf()))
	var from: Vector3 = muzzle_tip.global_position if muzzle_tip else eye + dir * 0.6
	Ballistics.fire(cfg.round, eye, dir, player, from)
	EventBus.shot_fired.emit(player, eye, dir)
	# The beam: muzzle to where the line of sight meets solid world.
	var end: Vector3 = eye + dir * minf(cfg.round.max_range, 400.0)
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, end, Ballistics.LAYER_WORLD)
	var res: Dictionary = space.intersect_ray(q)
	if not res.is_empty():
		end = res["position"]
	Fx.gauss_beam(from, end, cfg.glow_color)
	var muzzle_xform: Transform3D = Transform3D(Basis.looking_at(dir, Vector3.UP) * Basis(Vector3.UP, -PI * 0.5), from)
	Fx.muzzle_flash(muzzle_xform, cfg.round)
	Sfx.play_shot(cfg.round, true)
	Sfx.play_ui(&"gx4_crack", 0.0, 0.04)
	# Kick: camera, arm, field of view, pads, a beat of hit-stop.
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(Vector3(cfg.camera_kick_deg.x, cfg.camera_kick_deg.y * _rng.randf_range(-1.0, 1.0), cfg.camera_kick_deg.z * _rng.randf_range(-1.0, 1.0)))
	_kick_pos.kick(Vector3(-cfg.arm_kick_back * 0.4, 0.012, cfg.arm_kick_back))
	_kick_rot.kick(Vector3(0.0, 0.0, deg_to_rad(cfg.arm_kick_rise_deg)))
	player.fov_punch_deg = cfg.fov_punch_deg
	_rumble(cfg.rumble_fire)
	TimeControl.hitstop(cfg.shot_hitstop_time, cfg.shot_hitstop_scale)
	_flash = 1.0
	_ripple = 0.0
	_update_leds()
	if rounds() < 1:
		_empty_wait = cfg.empty_stow_delay
		Sfx.play_ui(&"gx4_empty", -4.0, 0.0)
	else:
		Sfx.play_ui(&"gx4_recharge", -10.0, 0.03)


func _update_leds() -> void:
	var n: int = rounds()
	for k: int in leds.size():
		leds[k].visible = k < n


func _rumble(r: Vector3) -> void:
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, r.x, r.y, r.z)
