class_name BossBrain
extends RefCounted
## How the Incense Master fights (docs/design.md §8.7a). A huge triad
## enforcer with a black-market Gauss prosthetic for a right arm. He walks
## the operative down and has three answers to where he is:
##
## - Close (`swing_commit`): the haymaker. The arm cocks back by his side
##   (the tell), and comes across at head height: a big hit and a throw.
##   Sidestep it, slide under it, back off.
## - Close for a while, or inside `pound_trigger`: the ground pound. Both
##   fists go up over his head, then the prosthetic comes down into the
##   street: a shockwave out to `pound_radius` that hurts and throws. Be in
##   the air when it lands, or be outside it. His own men are thrown too.
## - Far: the Gauss shot. He plants, raises the arm, and it charges with a
##   glow, a rising whine and a thin line to where it's aimed; it stops
##   tracking just before it fires a real slug (Ballistics: through thin
##   cover; the LC-6 can catch it and throw it back).
##
## Hard hits stagger him (damage in a short window, or any Gauss slug); below
## half health he's faster and fires two. At zero he doesn't die: he goes down
## on one knee (DOWN) and waits for the execution (BossExecution).

enum Phase { INTRO, HUNT, SWING, POUND, CANNON, STAGGER, DOWN, DEAD }

var e: Enemy
var cfg: BossConfig
var hw: BossHardware
var phase: Phase = Phase.HUNT
var enraged: bool = false
## Set by the execution just before the head goes: now he can die.
var executed: bool = false
var execution: BossExecution
## Counts (tests, the range readout).
var swings: int = 0
var swing_hits: int = 0
var pounds: int = 0
var pound_hits: int = 0
var shots: int = 0
var staggers: int = 0
## Damage the last swing / pound did to the operative.
var last_damage: float = 0.0

var _t: float = 0.0
var _cool_swing: float = 0.0
var _cool_pound: float = 2.0
var _cool_cannon: float = 2.5
var _close_for: float = 0.0
var _window: float = 0.0
var _immune: float = 0.0
var _struck: bool = false
var _swished: bool = false
var _shots_left: int = 0
var _locked: bool = false
var _aim_at: Vector3 = Vector3.ZERO
var _whine: AudioStreamPlayer3D
var _tell: MeshInstance3D
var _tell_mat: StandardMaterial3D
var _spark_t: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(enemy: Enemy) -> void:
	e = enemy
	cfg = enemy.config.boss
	_rng.randomize()


## Called from Enemy._ready once the body exists.
func setup() -> void:
	e.add_to_group(&"boss")
	if cfg.hardware:
		hw = BossHardware.fit(e, cfg)
	_whine = AudioStreamPlayer3D.new()
	_whine.name = "Whine"
	_whine.bus = &"SFX"
	_whine.unit_size = 14.0
	_whine.max_distance = 120.0
	var bank: Array = Sfx.bank(&"boss_charge")
	if not bank.is_empty():
		_whine.stream = bank[0]
	e.add_child(_whine)
	_tell = MeshInstance3D.new()
	_tell.name = "AimLine"
	_tell.top_level = true
	var cyl: CylinderMesh = CylinderMesh.new()
	cyl.top_radius = 1.0
	cyl.bottom_radius = 1.0
	cyl.height = 1.0
	cyl.radial_segments = 6
	cyl.rings = 1
	cyl.cap_top = false
	cyl.cap_bottom = false
	_tell.mesh = cyl
	_tell_mat = StandardMaterial3D.new()
	_tell_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_tell_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_tell_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_tell_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_tell_mat.no_depth_test = false
	_tell_mat.albedo_color = Color(cfg.glow_color, 0.0)
	_tell.material_override = _tell_mat
	_tell.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_tell.visible = false
	e.add_child(_tell)


func is_down() -> bool:
	return phase == Phase.DOWN


func is_busy() -> bool:
	return phase == Phase.SWING or phase == Phase.POUND or phase == Phase.CANNON or phase == Phase.STAGGER


func health_fraction() -> float:
	return clampf(e.health / maxf(e.config.health, 1.0), 0.0, 1.0)


func _player() -> Player:
	return e.squad.player() if e.squad else null


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)


func _enter(p: Phase) -> void:
	phase = p
	_t = 0.0


# ------------------------------------------------------------------ hits

## Damage taken (after zones): staggers, rage.
func on_hurt(damage: float, hit: BallisticHit) -> void:
	if phase == Phase.INTRO or phase == Phase.DOWN or phase == Phase.DEAD:
		return
	_window += damage
	var gauss: bool = hit != null and hit.weapon != null and hit.weapon.gore_style == &"gauss"
	if (_window >= cfg.stagger_damage or gauss) and _immune <= 0.0:
		stagger()
	if not enraged and health_fraction() < cfg.rage_at:
		enraged = true
		Sfx.play_at(&"boss_roar", e.body.head_position(), 4.0, 0.03)
		EventBus.callout.emit(e.config.callsign, "Enough!", e.global_position)


func stagger() -> void:
	staggers += 1
	_immune = cfg.stagger_immunity
	_window = 0.0
	_cancel()
	e.body.play_stumble()
	e.vocal(&"enemy_pain", 4.0, 0.05)
	_enter(Phase.STAGGER)


func _cancel() -> void:
	e.body.cancel_boss_moves()
	_whine.stop()
	_tell.visible = false
	if hw:
		hw.set_glow(cfg.glow_idle)


# ------------------------------------------------------------------ decisions

## Called on the enemy's think tick while he's in COMBAT.
func decide() -> void:
	var p: Player = _player()
	if p == null or phase != Phase.HUNT:
		return
	var d: float = _flat(p.global_position - e.global_position).length()
	if _pick_attack(p, d):
		return
	e.tactic = Enemy.Tactic.ADVANCE
	e._go(p.global_position if e.sees_player or e.last_known == Vector3.INF else e.last_known)


## Starts an attack if one fits. True if it did.
func _pick_attack(p: Player, d: float) -> bool:
	var dy: float = absf(p.global_position.y - e.global_position.y)
	if d <= cfg.pound_trigger and _cool_pound <= 0.0 and (_close_for >= cfg.pound_after_close or (d > cfg.swing_commit and dy < 2.5 and _rng.randf() < 0.35)):
		_start_pound()
		return true
	if d <= cfg.swing_commit and _cool_swing <= 0.0 and dy < 1.8 and _clear_to(p):
		_start_swing()
		return true
	if d >= cfg.cannon_min and d <= cfg.cannon_max and _cool_cannon <= 0.0 and (e.sees_player or e._unseen_for < 2.5):
		_start_cannon()
		return true
	return false


func speed() -> float:
	var p: Player = _player()
	var k: float = cfg.rage_speed if enraged else 1.0
	if phase != Phase.HUNT:
		return 0.0
	var far: bool = p != null and _flat(p.global_position - e.global_position).length() > cfg.charge_beyond
	return (cfg.charge_speed if far or not e.sees_player else cfg.walk_speed) * k


## The velocity he wants this frame, or INF to follow the nav path.
func want_velocity() -> Vector3:
	match phase:
		Phase.HUNT:
			return Vector3.INF
		Phase.SWING:
			var p: Player = _player()
			if p and _t < cfg.swing_windup * 0.9 and _flat(p.global_position - e.global_position).length() > cfg.swing_reach * 0.6:
				return e.global_basis.z * 2.4
	return Vector3.ZERO


# ------------------------------------------------------------------ every frame

## Every physics frame while in COMBAT (instead of aiming and firing).
func act(delta: float) -> void:
	var p: Player = _player()
	_t += delta
	_cool_swing -= delta
	_cool_pound -= delta
	_cool_cannon -= delta
	_immune -= delta
	_window *= exp(-delta / maxf(cfg.stagger_window, 0.05))
	var d: float = 99.0
	if p:
		d = _flat(p.global_position - e.global_position).length()
		_close_for = _close_for + delta if d <= cfg.pound_trigger else maxf(0.0, _close_for - delta * 2.0)
	if hw and phase != Phase.CANNON:
		hw.set_glow(move_toward(hw.glow_energy(), cfg.glow_idle * (1.6 if enraged else 1.0), delta * 20.0))
	match phase:
		Phase.HUNT:
			e.body.set_stance(&"loco")
			_look(p, 0.45, delta, e.velocity.length() < 0.5)
			if p and d <= cfg.swing_commit and _cool_swing <= 0.0 and absf(p.global_position.y - e.global_position.y) < 1.8 and _clear_to(p):
				_start_swing()
		Phase.SWING:
			_swing_frame(p, delta)
		Phase.POUND:
			_pound_frame(p, delta)
		Phase.CANNON:
			_cannon_frame(p, delta)
		Phase.STAGGER:
			e.body.set_stance(&"brute_ready")
			e.body.set_aim(0.0, 0.0, 0.0)
			if _t >= cfg.stagger_time:
				_enter(Phase.HUNT)
				e._think = 0.0


func _look(p: Player, weight: float, delta: float, turn: bool) -> void:
	if p == null:
		e.body.set_aim(0.0, 0.0, 0.0)
		return
	var to: Vector3 = p.camera().global_position - e.body.chest_position()
	var want_yaw: float = atan2(to.x, to.z)
	if turn:
		e._yaw = rotate_toward(e._yaw, want_yaw, deg_to_rad(cfg.turn_deg) * delta)
		e.rotation.y = e._yaw
	var rel: float = wrapf(want_yaw - e._yaw, -PI, PI)
	e.body.set_aim(rel, atan2(to.y, Vector2(to.x, to.z).length()), weight)


func _turn_to(p: Player, deg_per_s: float, delta: float) -> void:
	if p == null:
		return
	var to: Vector3 = _flat(p.global_position - e.global_position)
	e._yaw = rotate_toward(e._yaw, atan2(to.x, to.z), deg_to_rad(deg_per_s) * delta)
	e.rotation.y = e._yaw


func _clear_to(p: Player) -> bool:
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(e.body.chest_position(), p.camera().global_position - Vector3.UP * 0.4, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
	return e.get_world_3d().direct_space_state.intersect_ray(q).is_empty()


# ------------------------------------------------------------------ the haymaker

func _start_swing() -> void:
	swings += 1
	_enter(Phase.SWING)
	_struck = false
	_swished = false
	e._stop()
	e.body.play_swing(cfg.swing_windup)
	e.vocal(&"enemy_pain", 2.0, 0.08)


func _swing_frame(p: Player, delta: float) -> void:
	e.body.set_aim(0.0, 0.0, 0.0)
	if not _struck:
		_turn_to(p, cfg.turn_deg * 0.9, delta)
	if not _swished and _t >= cfg.swing_windup * 0.55:
		_swished = true
		Sfx.play_at(&"boss_swing", e.body.chest_position(), 2.0, 0.06)
	if not _struck and _t >= cfg.swing_windup:
		_struck = true
		_resolve_swing(p)
	if _t >= cfg.swing_windup + 0.62:
		_cool_swing = cfg.swing_cooldown * (cfg.rage_cooldown_scale if enraged else 1.0)
		_enter(Phase.HUNT)
		e._think = 0.0


## True if the operative is inside the haymaker's reach and arc now.
func swing_lands_on(p: Player) -> bool:
	var to: Vector3 = _flat(p.global_position - e.global_position)
	if to.length() > cfg.swing_reach or absf(p.global_position.y - e.global_position.y) > 1.9:
		return false
	var fwd: Vector3 = _flat(e.global_basis.z).normalized()
	if to.length() > 0.5 and rad_to_deg(fwd.angle_to(to.normalized())) > cfg.swing_arc_deg * 0.5:
		return false
	return _clear_to(p)


func _resolve_swing(p: Player) -> void:
	last_damage = 0.0
	if p == null or p.dead or not swing_lands_on(p):
		return
	var fwd: Vector3 = _flat(e.global_basis.z).normalized()
	var across: Vector3 = fwd.cross(Vector3.UP)  # the fist travels to his left
	var dir: Vector3 = (fwd * 0.6 - across * 0.8).normalized()
	last_damage = p.on_melee_hit(e, cfg.swing_damage, dir, cfg.swing_push)
	var at: Vector3 = p.camera().global_position - Vector3.UP * 0.3
	if last_damage > 0.0:
		swing_hits += 1
		p.velocity.y = maxf(p.velocity.y, cfg.swing_lift)
		Sfx.play_at(&"exec_punch", at, 4.0, 0.08)
		Sfx.play_at(&"kr5_hit", at, 0.0, 0.08)
		p.add_shake(1.1)
		_rumble(1.0, 1.0, 0.35)
	else:
		Sfx.play_at(&"impact_steel", at, 2.0, 0.1)


# ------------------------------------------------------------------ the ground pound

func _start_pound() -> void:
	pounds += 1
	_enter(Phase.POUND)
	_struck = false
	_swished = false
	e._stop()
	e.body.play_pound(cfg.pound_windup)


func _pound_frame(p: Player, delta: float) -> void:
	e.body.set_aim(0.0, 0.0, 0.0)
	if _t < cfg.pound_windup * 0.6:
		_turn_to(p, cfg.turn_deg * 0.5, delta)
	if hw:
		var rise: float = clampf(_t / cfg.pound_windup, 0.0, 1.0)
		hw.set_glow(lerpf(cfg.glow_idle, cfg.glow_charged * 0.7, rise) if not _struck else move_toward(hw.glow_energy(), cfg.glow_idle, delta * 30.0))
	if not _swished and _t >= cfg.pound_windup * 0.2:
		_swished = true
		e.vocal(&"death_scream", 2.0, 0.02)
	if not _struck and _t >= cfg.pound_windup:
		_struck = true
		_resolve_pound(p)
	if _t >= cfg.pound_windup + 0.75:
		_cool_pound = cfg.pound_cooldown * (cfg.rage_cooldown_scale if enraged else 1.0)
		_close_for = 0.0
		_enter(Phase.HUNT)
		e._think = 0.0


## Where the fist meets the ground: [point, normal].
func pound_point() -> Array:
	var fist: Vector3 = e.body.bone_position(&"hand.R")
	var from: Vector3 = Vector3(fist.x, e.global_position.y + 1.0, fist.z)
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 3.0, Ballistics.LAYER_WORLD)
	var res: Dictionary = e.get_world_3d().direct_space_state.intersect_ray(q)
	if res.is_empty():
		return [Vector3(fist.x, e.global_position.y, fist.z), Vector3.UP]
	return [res["position"], res["normal"]]


func _resolve_pound(p: Player) -> void:
	last_damage = 0.0
	var pp: Array = pound_point()
	var at: Vector3 = pp[0]
	var n: Vector3 = pp[1]
	shockwave(at, n, cfg.pound_radius, cfg.pound_damage_near, cfg.pound_damage_far, cfg.pound_lift, cfg.pound_push, p)
	Sfx.play_at(&"boss_pound", at, 6.0, 0.04)


## A shockwave from `at` (the pound and the landing): hurts and throws the
## operative unless he's in the air, throws men, kicks loose things.
func shockwave(at: Vector3, n: Vector3, radius: float, near: float, far: float, lift: float, push: float, p: Player) -> void:
	Fx.explosion_fx().shockwave(at, n, radius)
	Fx.debris(at + Vector3.UP * 0.1, Vector3.UP * 4.0, Color(0.35, 0.33, 0.3), 0.05, 14, 2.0)
	if p and not p.dead:
		var d: float = _flat(p.global_position - at).length()
		var shake: float = clampf(1.6 - d / (radius * 2.0), 0.3, 1.6)
		p.add_shake(shake)
		_rumble(0.7 * shake, shake, 0.4)
		if d <= radius and not _in_air(p, at):
			var f: float = clampf(d / radius, 0.0, 1.0)
			var out: Vector3 = _flat(p.global_position - at).normalized()
			if out.length_squared() < 0.01:
				out = _flat(-e.global_basis.z).normalized()
			if near > 0.0:
				last_damage = p.on_melee_hit(e, lerpf(near, far, f), out, push * (1.0 - f * 0.6))
				if last_damage > 0.0:
					pound_hits += 1
					p.velocity.y = maxf(p.velocity.y, lift * (1.0 - f * 0.5))
	for node: Node in e.get_tree().get_nodes_in_group(&"enemies"):
		var o: Enemy = node as Enemy
		if o == null or o == e or not o.alive:
			continue
		var od: float = _flat(o.global_position - at).length()
		if od < radius:
			var k: float = 1.0 - od / radius
			var away: Vector3 = _flat(o.global_position - at).normalized()
			o.launch(away * push * k * 0.6 + Vector3.UP * lift * (0.4 + 0.6 * k), e, 0.15, 20.0, 70.0, 0.8)
	var space: PhysicsDirectSpaceState3D = e.get_world_3d().direct_space_state
	var shape: SphereShape3D = SphereShape3D.new()
	shape.radius = radius
	var q: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	q.shape = shape
	q.transform = Transform3D(Basis(), at)
	q.collision_mask = Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	for r: Dictionary in space.intersect_shape(q, 24):
		var col: Object = r["collider"]
		var rb: RigidBody3D = col as RigidBody3D
		if rb:
			var to: Vector3 = rb.global_position - at
			var k2: float = clampf(1.0 - to.length() / radius, 0.0, 1.0)
			rb.apply_central_impulse((_flat(to).normalized() * 2.5 + Vector3.UP * 3.0) * rb.mass * k2)


## Off the ground at the moment the shock goes through (jumped it).
func _in_air(p: Player, at: Vector3) -> bool:
	return not p.is_on_floor() and p.global_position.y - at.y > cfg.pound_air


# ------------------------------------------------------------------ the Gauss shot

func _start_cannon() -> void:
	_enter(Phase.CANNON)
	_locked = false
	_shots_left = cfg.rage_shots if enraged else cfg.cannon_shots
	e._stop()
	e.body.set_stance(&"cannon")
	_whine.pitch_scale = 1.0 / maxf(cfg.cannon_charge / 1.5, 0.3)
	_whine.play()
	_aim_at = _aim_point()


## Where he wants the slug to go: the operative's chest if he sees him, else where he last was.
func _aim_point() -> Vector3:
	var p: Player = _player()
	if p == null:
		return e.global_position + e.global_basis.z * 10.0 + Vector3.UP * 1.4
	if e.sees_player:
		return p.camera().global_position - Vector3.UP * 0.35
	return (e.last_known if e.last_known != Vector3.INF else p.global_position) + Vector3.UP * 1.3


func _cannon_frame(p: Player, delta: float) -> void:
	e.body.set_stance(&"cannon")
	var charge: float = cfg.cannon_charge * (0.75 if enraged else 1.0)
	if not _locked:
		var want: Vector3 = _aim_point()
		# Tracks, but only so fast: a sprint across his line stays ahead of the aim.
		var from: Vector3 = e.body.chest_position()
		var cur: Vector3 = _aim_at - from
		var tgt: Vector3 = want - from
		var ang: float = cur.angle_to(tgt)
		var step: float = deg_to_rad(cfg.cannon_track_deg) * delta
		if ang > 0.0001:
			var axis: Vector3 = cur.cross(tgt).normalized()
			if axis.length_squared() > 0.5:
				cur = cur.rotated(axis, minf(step, ang))
			else:
				cur = tgt
		cur = cur.normalized() * tgt.length()
		_aim_at = from + cur
		if _t >= charge - cfg.cannon_lock:
			_locked = true
	var to: Vector3 = _aim_at - e.body.chest_position()
	var want_yaw: float = atan2(to.x, to.z)
	e._yaw = rotate_toward(e._yaw, want_yaw, deg_to_rad(cfg.turn_deg) * delta)
	e.rotation.y = e._yaw
	e.body.set_aim(wrapf(want_yaw - e._yaw, -PI, PI), atan2(to.y, Vector2(to.x, to.z).length()), 1.0)
	var k: float = clampf(_t / charge, 0.0, 1.0)
	if hw:
		hw.set_glow(lerpf(cfg.glow_idle, cfg.glow_charged, k * k))
	_update_tell(k)
	if _shots_left > 0 and _t >= charge:
		_fire()
		_shots_left -= 1
		if _shots_left > 0:
			_t = charge - cfg.cannon_gap
			_locked = false
			_whine.play(_whine.stream.get_length() * 0.6 if _whine.stream else 0.0)
	if _shots_left <= 0 and _t >= charge + 0.6:
		_tell.visible = false
		_cool_cannon = cfg.cannon_cooldown * (cfg.rage_cooldown_scale if enraged else 1.0)
		_enter(Phase.HUNT)
		e._think = 0.0


## The thin line from the rails to where they point: fainter early, solid when locked.
func _update_tell(k: float) -> void:
	if hw == null:
		return
	var m: Transform3D = hw.muzzle_transform()
	var from: Vector3 = m.origin
	var dir: Vector3 = (_aim_at - from).normalized()
	var end: Vector3 = from + dir * 120.0
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, end, Ballistics.LAYER_WORLD | Ballistics.LAYER_PLAYER)
	var res: Dictionary = e.get_world_3d().direct_space_state.intersect_ray(q)
	if not res.is_empty():
		end = res["position"]
	var length: float = from.distance_to(end)
	if length < 0.2:
		_tell.visible = false
		return
	_tell.visible = true
	var mid: Vector3 = (from + end) * 0.5
	var y: Vector3 = dir
	var x: Vector3 = y.cross(Vector3.UP if absf(y.y) < 0.95 else Vector3.RIGHT).normalized()
	var z: Vector3 = x.cross(y).normalized()
	var w: float = 0.006 + 0.01 * k
	_tell.global_transform = Transform3D(Basis(x * w, y * length, z * w), mid)
	var a: float = (0.18 + 0.55 * k) * (1.0 if _locked else 0.6 + 0.4 * sin(_t * 40.0))
	_tell_mat.albedo_color = Color(cfg.glow_color.lerp(Color(1, 1, 1), 0.3 * k), a)


func _fire() -> void:
	shots += 1
	var m: Transform3D = hw.muzzle_transform() if hw else e.body.muzzle_transform()
	var origin: Vector3 = m.origin
	var dir: Vector3 = Ballistics.random_in_cone((_aim_at - origin).normalized(), cfg.cannon_error_deg, _rng)
	Ballistics.fire(cfg.cannon_round, origin, dir, e, origin)
	var end: Vector3 = origin + dir * 160.0
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(origin, end, Ballistics.LAYER_WORLD)
	var res: Dictionary = e.get_world_3d().direct_space_state.intersect_ray(q)
	if not res.is_empty():
		end = res["position"]
	Fx.gauss_beam(origin, end, cfg.glow_color)
	Fx.muzzle_flash(Transform3D(Basis.looking_at(dir, Vector3.UP) * Basis(Vector3.UP, -PI * 0.5), origin), cfg.cannon_round)
	Sfx.play_at(&"gx4_shot", origin, 6.0, 0.04)
	Sfx.play_at(&"gx4_crack", origin, 2.0, 0.04)
	EventBus.shot_fired.emit(e, origin, dir)
	e.body.flinch(-dir, 2.5, false)
	if hw:
		hw.set_glow(cfg.glow_flash)
	_whine.stop()
	var p: Player = _player()
	if p:
		var close: float = clampf(1.0 - p.global_position.distance_to(origin) / 30.0, 0.0, 1.0)
		p.add_shake(0.25 + 0.6 * close)


# ------------------------------------------------------------------ down and out

## Zero health: down on one knee, out of the fight, waiting for the execution.
func go_down() -> void:
	if phase == Phase.DOWN or phase == Phase.DEAD:
		return
	_cancel()
	_enter(Phase.DOWN)
	e.health = 0.0
	e.bleed_dps = 0.0
	e.burn_left = 0.0
	e._stop()
	e.velocity = Vector3.ZERO
	e.body.set_stance(&"kneel_down")
	e.remove_from_group(&"enemies")
	e.remove_from_group(&"aim_assist_targets")
	e.remove_from_group(&"suppressible")
	e._release_token()
	e.vocal(&"death_groan", 4.0, 0.03)
	Sfx.play_at(&"body_fall", e.global_position + Vector3.UP * 0.4, 4.0, 0.05)
	EventBus.music_cue.emit(&"boss_kneel")
	if hw:
		hw.set_glow(cfg.glow_idle * 0.4)
	execution = BossExecution.new()
	execution.name = "BossExecution"
	execution.boss = e
	(e.get_parent() if e.get_parent() else e.get_tree().current_scene).add_child(execution)


## Every physics frame while he's down: kneeling, breathing, the arm sputtering.
func down_frame(delta: float) -> void:
	e.velocity = Vector3(0.0, e.velocity.y - Enemy.GRAVITY * delta if not e.is_on_floor() else -0.5, 0.0)
	e.move_and_slide()
	e.body.set_motion(Vector3.ZERO)
	if execution and execution.running:
		return
	e.body.set_stance(&"kneel_down")
	var p: Player = _player()
	if p:
		var to: Vector3 = p.camera().global_position - e.body.head_position()
		var rel: float = wrapf(atan2(to.x, to.z) - e._yaw, -PI, PI)
		var near: float = clampf(1.0 - _flat(to).length() / 8.0, 0.0, 1.0)
		e.body.set_aim(clampf(rel, -0.8, 0.8), atan2(to.y, Vector2(to.x, to.z).length()) + 0.3, 0.25 + 0.5 * near)
	_spark_t -= delta
	if _spark_t <= 0.0 and hw and hw.muzzle and hw.muzzle.is_inside_tree():
		_spark_t = _rng.randf_range(0.4, 1.3)
		var at: Vector3 = e.body.bone_position(&"forearm.R")
		Fx._emit(&"sparks", at, Vector3.UP, cfg.glow_color, 6, 0.6)
		Sfx.play_at(&"gx4_zap", at, -6.0, 0.15)
		hw.set_glow(cfg.glow_charged * 0.5)
	elif hw:
		hw.set_glow(move_toward(hw.glow_energy(), cfg.glow_idle * 0.3, delta * 20.0))


## The execution's last punch: he can die now.
func finish() -> void:
	executed = true
	phase = Phase.DEAD
	e.remove_from_group(&"boss")
	if hw:
		hw.set_glow(0.0)
		hw.disable_plates()


func _rumble(weak: float, strong: float, seconds: float) -> void:
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, clampf(weak, 0.0, 1.0), clampf(strong, 0.0, 1.0), seconds)
