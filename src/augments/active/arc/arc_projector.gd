class_name ArcProjector
extends ActivePart
## AD-2 Arc Projector (ArcProjectorData): a shoulder electrolaser. Press LB:
## the mast swings up into the top right of the view (the deploy clip) and
## discharges at whoever is nearest the crosshair; the arc chains on to
## bodies near him. While the mast is up LB fires again (one stored charge
## each); it folds away `linger` seconds after the last discharge. Reads
## the body: each discharge comes out of the power reserve (no reserve, no
## arc), a bigger reserve chains further, and spare power refills charges
## faster.

var cfg: ArcProjectorData
var rig: ArmRig
var muzzle: Node3D
var weapon: WeaponData
## Bodies hit by the last discharge, in order (tests, HUD).
var last_targets: Array[Enemy] = []
var discharges: int = 0

var _glow: StandardMaterial3D
var _flash: float = 0.0
var _cooldown: float = 0.0
var _linger: float = 0.0
var _pending: bool = false


func _ready() -> void:
	super._ready()
	cfg = data as ArcProjectorData
	weapon = AugHit.weapon_named("AD-2 Arc Projector")
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "ArcProjectorRig")
	if player == null:
		add_child(rig)
	rig.raise_drop = 0.0
	rig.raise_share = 0.01
	muzzle = rig.part("muzzle_tip")
	_glow = rig.drive("glow")
	if _glow:
		_glow.emission = cfg.bolt_color
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()


func hud_pips() -> int:
	return roundi(charge_capacity())


func _drain(_real: float) -> void:
	pass


func offline_reason() -> String:
	var why: String = super.offline_reason()
	if why == "" and body and body.power_j < cfg.discharge_j:
		return "reserve below %.0f kJ" % (cfg.discharge_j / 1000.0)
	return why


## Bodies the arc can jump to after the first: more with a bigger reserve.
func chain_count() -> int:
	if body == null:
		return cfg.chains
	var extra: float = body.stat(&"power_capacity_j") - body.frame.power_capacity_j
	return clampi(cfg.chains + floori(extra / maxf(cfg.chain_per_j, 1.0)), 0, cfg.max_chains)


func regen_scale() -> float:
	if body == null:
		return 1.0
	return clampf(body.headroom_w() / maxf(cfg.power_ref_w, 1.0), cfg.recharge_min_scale, cfg.recharge_max_scale)


## LB: raise it and fire; while it's up, fire again.
func toggle() -> void:
	if state == State.ACTIVE:
		if charge >= 1.0 and _cooldown <= 0.0 and not is_offline():
			_fire()
		else:
			_on_denied()
	elif state == State.DEPLOYING:
		_pending = true
	else:
		super.toggle()


func _on_start() -> void:
	_pending = true
	rig.visible = true
	Sfx.play_ui(&"ad2_deploy", -4.0, 0.0)


func _on_stop() -> void:
	Sfx.play_ui(&"ad2_stow", -8.0, 0.0)


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_state_changed(s: State) -> void:
	if s == State.COOLDOWN:
		rig.visible = false
	elif s == State.ACTIVE:
		_linger = cfg.linger


func _on_blend(a: float) -> void:
	rig.seek(a)
	if _glow:
		_glow.emission_energy_multiplier = cfg.glow_idle * a


func _on_active(real: float) -> void:
	_cooldown -= real * TimeControl.player_scale_now()
	if _pending and _cooldown <= 0.0:
		_pending = false
		if charge >= 1.0:
			_fire()
	_linger -= real
	if _linger <= 0.0:
		stop()


## The living enemy nearest the crosshair inside the cone, in reach and in sight.
func primary_target() -> Enemy:
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var best: Enemy = null
	var best_ang: float = cfg.cone_deg
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive:
			continue
		var to: Vector3 = e.body.chest_position() - eye
		if to.length() > cfg.reach:
			continue
		var ang: float = rad_to_deg(fwd.angle_to(to))
		if ang < best_ang and _clear(eye, e.body.chest_position()):
			best_ang = ang
			best = e
	return best


func _clear(from: Vector3, to: Vector3) -> bool:
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, Ballistics.LAYER_WORLD)
	return player.get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _fire() -> void:
	charge = maxf(charge - 1.0, 0.0)
	discharges += 1
	_cooldown = cfg.refire
	_linger = cfg.linger
	_since_stop = 0.0
	if body:
		body.power_j = maxf(body.power_j - cfg.discharge_j, 0.0)
		body.heat_j = minf(body.heat_j + cfg.heat_j, body.frame.heat_capacity_j)
	var cam: Camera3D = player.camera()
	var from: Vector3 = muzzle.global_position if muzzle else cam.global_position + cam.global_basis * Vector3(0.25, 0.2, -0.4)
	var pts: PackedVector3Array = PackedVector3Array([from])
	last_targets.clear()
	var e: Enemy = primary_target()
	var dmg: float = cfg.damage
	var prev: Vector3 = cam.global_position
	while e and last_targets.size() <= chain_count():
		last_targets.append(e)
		var at: Vector3 = e.body.chest_position()
		pts.append(at)
		_shock(e, at, (at - prev).normalized(), dmg)
		dmg *= cfg.chain_falloff
		prev = at
		# The next body: the nearest one in reach that the arc hasn't been through.
		var next: Enemy = null
		var best: float = cfg.chain_reach
		for n: Node in get_tree().get_nodes_in_group(&"enemies"):
			var o: Enemy = n as Enemy
			if o == null or not o.alive or o in last_targets:
				continue
			var d: float = o.body.chest_position().distance_to(at)
			if d < best and _clear(at, o.body.chest_position()):
				best = d
				next = o
		e = next
	if last_targets.is_empty():
		# Nobody there: it grounds on whatever is in front.
		var end: Vector3 = cam.global_position - cam.global_basis.z * cfg.reach
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(cam.global_position, end, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
		var res: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
		if not res.is_empty():
			end = res["position"]
			var nrm: Vector3 = res["normal"]
			Fx._emit(&"sparks", end, nrm, Color(0.7, 0.85, 1.0, 1.0), 4, 1.2)
		pts.append(end)
	ArcBolt.spawn(world(), pts, cfg.bolt_color, 0.32, 0.09)
	Sfx.play_ui(&"ad2_fire", 0.0, 0.05)
	EventBus.shot_fired.emit(player, cam.global_position, -cam.global_basis.z)
	_flash = 1.0
	rig.kick_pos.kick(Vector3(0.0, 0.01, 0.03))
	rumble(cfg.rumble_fire.x, cfg.rumble_fire.y, cfg.rumble_fire.z)
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(Vector3(cfg.camera_kick_deg.x, cfg.camera_kick_deg.y * randf_range(-1.0, 1.0), cfg.camera_kick_deg.z * randf_range(-1.0, 1.0)))
	_light(from)


func _shock(e: Enemy, at: Vector3, dir: Vector3, dmg: float) -> void:
	var part: HitboxPart = e.parts.get(&"chest")
	if part == null:
		return
	AugHit.strike(part, weapon, player, at, dir, dmg, 5.0, 350.0, DamageInfo.Type.EMP, false)
	Gore.electrocute(e.body)
	Sfx.play_at(&"gx4_zap", at, 0.0, 0.1)
	if e.alive:
		# Every muscle locks: he staggers and his nerve goes.
		e.knock_back(dir * 2.5, player, 0.0, 0.45)


func _light(at: Vector3) -> void:
	if not Fx.enabled:
		return
	var l: OmniLight3D = OmniLight3D.new()
	l.light_color = cfg.bolt_color
	l.light_energy = 9.0
	l.omni_range = 12.0
	world().add_child(l)
	l.global_position = at
	var tw: Tween = l.create_tween()
	tw.tween_property(l, ^"light_energy", 0.0, 0.18)
	tw.tween_callback(l.queue_free)


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if rig.visible:
		rig.tick(real, blend, player)
		_flash = maxf(0.0, _flash - real * 5.0)
		if _glow and state == State.ACTIVE:
			var primed: float = clampf(1.0 - _cooldown / maxf(cfg.refire, 0.01), 0.0, 1.0) if charge >= 1.0 else 0.15
			_glow.emission_energy_multiplier = cfg.glow_idle * primed + cfg.glow_flash * _flash * _flash
