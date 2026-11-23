class_name FlamerBrain
extends RefCounted
## Triad Flamer (docs/design.md §8.8c): a fast, agile triad arsonist fighting
## with a pressurized aerosol can in his right hand and a flip-top lighter in
## his left.
##
## - Approach: sprints aggressively, flanking off the operative's sightline and
##   weaving when watched, closing into short-to-mid flame range.
## - Ignite (the tell): raises can and lighter, pilot flame flares, audible
##   flint-spark + aerosol hiss for `flamer_ignite_time` s.
## - Spray: unleashes a damaging cone of fire out to `flamer_range` m while
##   strafing laterally at `flamer_strafe_speed` and tracking at most
##   `flamer_track_deg` deg/s (dodgeable by a sprint/slide/dropkick, blocked by
##   solid cover and by the BW-6 fan shield). Deals heavy direct fire DPS plus
##   lingering afterburn.
## - Reposition: darts sideways/diagonally between bursts so he stays slippery.
## - Weakness (the aerosol can): `can_hitbox` (AerosolCan on LAYER_HITBOX) rides
##   on the can in his right hand. Shooting it ruptures the can into a fuel-air
##   fireball that engulfs him in place (no huge explosive launch) and sets
##   nearby enemies alight (chain-cooking other Flamers' cans).
## Tuning: data/enemies/flamer.tres (EnemyConfig, Flamer group).

enum Phase { APPROACH, IGNITE, SPRAY, REPOSITION }

const TICK_INTERVAL: float = 0.12
const FLAME_MASK: int = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS

var e: Enemy
var cfg: EnemyConfig
var phase: Phase = Phase.APPROACH
## +1 / -1 lateral flank & strafe side.
var side: float = 1.0
var can_hitbox: AerosolCan
var lighter: Node3D
var pilot_flame: MeshInstance3D
var flame_jet: FlameJet
var can_detonated: bool = false
var has_lighter: bool = true

## Counters for tests and demos.
var sprays: int = 0
var fire_ticks: int = 0
var splash_ignited: int = 0

var _t: float = 0.0
var _len: float = 0.0
var _weave: float = 0.0
var _watched_for: float = 0.0
var _side_picked: bool = false
var _damage_in_burst: float = 0.0
var _tick_cd: float = 0.0
var _spray_yaw: float = 0.0
var _spray_pitch: float = 0.0
var _jet_reach: float = 6.5
var _pilot_time: float = 0.0
var _cookoff_timer: float = -1.0
var _cookoff_shooter: Node
var _spray_audio: AudioStreamPlayer3D
var _reposition_to: Vector3 = Vector3.INF
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(enemy: Enemy) -> void:
	e = enemy
	cfg = enemy.config
	_rng.randomize()
	side = 1.0 if _rng.randf() < 0.5 else -1.0


## Attaches the can's weak-point hitbox, the left-hand lighter + pilot flame,
## the FlameJet VFX node, and the 3D spray audio player. Called from Enemy._ready().
func setup() -> void:
	var body: EnemyBody = e.body
	# Precision weak-point hitbox riding directly on the aerosol can in right hand.
	if body.gun != null:
		can_hitbox = AerosolCan.new()
		can_hitbox.name = "AerosolCanHitbox"
		can_hitbox.target = e
		can_hitbox.collision_layer = Ballistics.LAYER_HITBOX
		can_hitbox.collision_mask = 0
		can_hitbox.set_meta(&"surface", &"sheet_metal")
		can_hitbox.set_meta(&"aerosol_can", true)
		can_hitbox.set_meta(&"stops_rounds", true)
		var cs: CollisionShape3D = CollisionShape3D.new()
		var cap: CapsuleShape3D = CapsuleShape3D.new()
		cap.radius = 0.068
		cap.height = 0.29
		cs.shape = cap
		can_hitbox.add_child(cs)
		# Matches raw_assets/weapons/enemy_flamer/build.py can centre in Godot gun space (+X fwd, +Y up, +Z right).
		can_hitbox.position = Vector3(0.028, 0.056, 0.026)
		can_hitbox.rotation = Vector3(0.0, 0.0, -deg_to_rad(8.0))
		body.gun.add_child(can_hitbox)
		body.add_plate(can_hitbox)
	# Flip-top brass lighter in left hand (bone space of hand.L) + live pilot flame.
	if cfg.lighter_scene:
		var att_l: BoneAttachment3D = body.bone_attachment(&"hand.L")
		lighter = cfg.lighter_scene.instantiate() as Node3D
		lighter.name = "Lighter"
		att_l.add_child(lighter)
		GunFlatten.apply(lighter)
		var wick: Node3D = lighter.find_child("wick", true, false) as Node3D
		pilot_flame = FlameJet.make_pilot_flame()
		if wick:
			wick.add_child(pilot_flame)
		else:
			lighter.add_child(pilot_flame)
			pilot_flame.position = Vector3(-0.007, 0.070, -0.110)
	# Volumetric flame jet + ember trail + spray light.
	flame_jet = FlameJet.new()
	flame_jet.name = "FlameJet"
	e.add_child(flame_jet)
	# Dedicated 3D voice for the roaring flame stream so impacts/gunfire never steal it.
	_spray_audio = AudioStreamPlayer3D.new()
	_spray_audio.name = "FlameAudio"
	_spray_audio.bus = &"SFX"
	_spray_audio.unit_size = 7.0
	_spray_audio.max_distance = 55.0
	_spray_audio.attenuation_filter_cutoff_hz = 10000.0
	body.bone_attachment(&"hand.R").add_child(_spray_audio)


func is_spraying() -> bool:
	return phase == Phase.SPRAY


func is_igniting() -> bool:
	return phase == Phase.IGNITE


func can_world_position() -> Vector3:
	if can_hitbox and is_instance_valid(can_hitbox) and can_hitbox.is_inside_tree():
		return can_hitbox.global_position
	if e.body.gun and is_instance_valid(e.body.gun) and e.body.gun.is_inside_tree():
		return e.body.gun.global_position
	return e.body.chest_position()


func nozzle_position() -> Vector3:
	if pilot_flame and is_instance_valid(pilot_flame) and pilot_flame.is_inside_tree() and pilot_flame.visible:
		return pilot_flame.global_position
	return e.body.muzzle_transform().origin


## Knocked out of whatever he's doing (launched, seized, fled, staggered, killed).
func reset() -> void:
	_stop_flame()
	phase = Phase.APPROACH
	_t = 0.0
	_reposition_to = Vector3.INF


## Called on Enemy.die() (if he dies from body shots, not a can blast).
func on_death() -> void:
	_stop_flame()
	_cookoff_timer = -1.0
	if can_hitbox and is_instance_valid(can_hitbox):
		can_hitbox.collision_layer = 0
	if pilot_flame and is_instance_valid(pilot_flame):
		pilot_flame.visible = false
	drop_lighter(e.velocity + Vector3(_rng.randf_range(-1.2, 1.2), 1.4, _rng.randf_range(-1.2, 1.2)))


## Called when a limb is severed: losing the left hand drops the lighter and stops him lighting the spray.
func on_sever(group: Array[StringName]) -> void:
	if (&"hand_L" in group) and has_lighter:
		has_lighter = false
		_stop_flame()
		if pilot_flame and is_instance_valid(pilot_flame):
			pilot_flame.visible = false
		drop_lighter(Vector3(_rng.randf_range(-1.0, 1.0), 1.5, _rng.randf_range(-1.0, 1.0)))
	if (&"hand_R" in group):
		_stop_flame()
		if can_hitbox and is_instance_valid(can_hitbox):
			can_hitbox.collision_layer = 0


func drop_lighter(vel: Vector3) -> void:
	if lighter == null or not is_instance_valid(lighter):
		return
	var xform: Transform3D = lighter.global_transform
	if pilot_flame and is_instance_valid(pilot_flame):
		pilot_flame.visible = false
	var rb: RigidBody3D = RigidBody3D.new()
	rb.collision_layer = Ballistics.LAYER_DEBRIS
	rb.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	rb.mass = 0.12
	rb.set_meta(&"surface", &"sheet_metal")
	var cs: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(0.05, 0.07, 0.03)
	cs.shape = box
	rb.add_child(cs)
	lighter.get_parent().remove_child(lighter)
	rb.add_child(lighter)
	lighter.transform = Transform3D.IDENTITY
	var level: Node = e.get_parent() if e.get_parent() else e.get_tree().root
	level.add_child(rb)
	rb.global_transform = xform
	rb.linear_velocity = vel
	rb.angular_velocity = Vector3(_rng.randf_range(-6, 6), _rng.randf_range(-6, 6), _rng.randf_range(-6, 6))
	rb.add_to_group(&"dropped_guns")
	lighter = null


## Enough body damage during ignite or spray staggers him out of the burst.
func on_hurt(damage: float) -> void:
	if phase != Phase.IGNITE and phase != Phase.SPRAY:
		return
	_damage_in_burst += damage
	if _damage_in_burst >= cfg.flamer_interrupt:
		_stop_flame()
		e.body.play_stumble()
		side = -side
		_enter(Phase.REPOSITION, _rng.randf_range(cfg.flamer_cooldown.x, cfg.flamer_cooldown.y) + 0.3)


## Runs every physics frame while alive (updates flame visuals, pilot flicker, and cook-off timer).
func tick(delta: float) -> void:
	_pilot_time += delta
	if pilot_flame and is_instance_valid(pilot_flame) and pilot_flame.visible:
		var mat: ShaderMaterial = pilot_flame.material_override as ShaderMaterial
		if mat:
			mat.set_shader_parameter(&"now", _pilot_time)
			var flare: float = 1.65 if phase == Phase.IGNITE else (1.35 if phase == Phase.SPRAY else 1.0)
			mat.set_shader_parameter(&"flare", flare)
	if flame_jet:
		flame_jet.step(delta)
	if _cookoff_timer >= 0.0:
		_cookoff_timer -= delta
		if _cookoff_timer <= 0.0:
			_cookoff_timer = -1.0
			var h: BallisticHit = BallisticHit.new()
			h.shooter = _cookoff_shooter
			h.point = can_world_position()
			h.normal = Vector3.UP
			h.direction = Vector3.UP
			var info: DamageInfo = DamageInfo.new()
			info.type = DamageInfo.Type.FIRE
			info.amount = cfg.flamer_can_self_damage
			info.impulse = 1.5
			h.damage = info
			on_can_hit(h)


## Schedules a short delayed cook-off when another Flamer's fireball engulfs this one.
func schedule_cookoff(delay: float, shooter: Node) -> void:
	if can_detonated or not e.alive or _cookoff_timer >= 0.0:
		return
	_cookoff_timer = maxf(delay, 0.05)
	_cookoff_shooter = shooter


# ------------------------------------------------------------------ aerosol can detonation

## Precision shot hit the aerosol can in the Flamer's hand!
## Fuel-air BLEVE fireball: engulfs the Flamer in place (NO huge explosive launch)
## and ignites/damages nearby enemies with burning agony + chain cook-offs.
func on_can_hit(hit: BallisticHit) -> void:
	if can_detonated or not e.alive:
		return
	can_detonated = true
	if can_hitbox and is_instance_valid(can_hitbox):
		can_hitbox.detonated = true
		can_hitbox.collision_layer = 0
	_stop_flame()
	_cookoff_timer = -1.0
	var at: Vector3 = can_world_position()
	# Destroy the aerosol can immediately so an intact can never drops out of the fireball.
	e.has_gun = false
	if e.body.gun and is_instance_valid(e.body.gun):
		e.body.gun.visible = false
		e.body.gun.queue_free()
		e.body.gun = null
	if pilot_flame and is_instance_valid(pilot_flame):
		pilot_flame.visible = false
	drop_lighter(Vector3(_rng.randf_range(-2.5, 2.5), 2.8, _rng.randf_range(-2.5, 2.5)))

	# 1. Visual fuel-air fireball (blooms right around him, no ground dust shockwave throw).
	var radius: float = cfg.flamer_fireball_radius
	if Fx.enabled:
		Fx.explosion(at, Vector3.UP, radius * 0.56, true)
		for i: int in 4:
			var sdir: Vector3 = Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(0.15, 1.0), _rng.randf_range(-1.0, 1.0)).normalized()
			Fx._emit(&"sparks", at, sdir, Color(1.0, 0.65, 0.18, 1.0), 22, 1.8)
		var world_node: Node3D = e.get_parent() as Node3D
		if world_node == null:
			world_node = e
		Explosion._flash(world_node, at, radius * 1.15)
	Sfx.play_at(&"flamer_can_boom", at, 7.0, 0.08)

	# 2. Engulf the Flamer himself: charred, covered in roaring flames, collapses on the spot (low impulse!).
	e.charred = 0.9
	e.body.set_char(e.charred)
	e.burn_left = maxf(e.burn_left, cfg.flamer_splash_burn_time)
	e.burn_dps = maxf(e.burn_dps, cfg.flamer_splash_burn_dps)
	var chest_part: HitboxPart = e.body.hitboxes.get(&"chest")
	var head_part: HitboxPart = e.body.hitboxes.get(&"head")
	if chest_part:
		Fx.burn_at(chest_part, chest_part.global_position, Vector3.UP, 6.0, true)
	if head_part:
		Fx.burn_at(head_part, head_part.global_position, Vector3.UP, 5.0, true)

	# Build a gentle-impulse burn hit so he slumps/collapses engulfed rather than flying across the room.
	var burn_hit: BallisticHit = BallisticHit.new()
	burn_hit.weapon = hit.weapon if hit else null
	burn_hit.shooter = hit.shooter if hit else null
	burn_hit.point = at
	burn_hit.normal = Vector3.UP
	burn_hit.direction = -e.global_basis.z * 0.4 + Vector3.DOWN * 0.2
	var dmg_info: DamageInfo = DamageInfo.new()
	dmg_info.type = DamageInfo.Type.FIRE
	dmg_info.amount = cfg.flamer_can_self_damage
	dmg_info.impulse = 1.6  # tiny slump, NOT an explosion throw!
	burn_hit.damage = dmg_info

	# 3. Splash fireball to nearby enemies, dogs, and point-blank player.
	_splash_fireball(at, radius, hit)

	# 4. Kill/engulf the Flamer and report crisp kill confirmation to the HUD/SFX.
	e.last_hit = burn_hit
	e.health -= cfg.flamer_can_self_damage
	if e.health <= 0.0:
		e.velocity = Vector3.ZERO
		e.die(burn_hit, &"chest", &"burn")
		EventBus.target_hit.emit(&"kill", hit if hit else burn_hit)
		EventBus.damage_applied.emit(dmg_info, e)
	else:
		e.ignite(chest_part, burn_hit, cfg.flamer_splash_burn_time, cfg.flamer_splash_burn_dps * 2.0, cfg.flamer_splash_agony)
		EventBus.target_hit.emit(&"headshot", hit if hit else burn_hit)
		EventBus.damage_applied.emit(dmg_info, e)

	# 5. Nearby player feel (shake + rumble) + alert nearby enemies.
	var p: Player = _player()
	if p and not p.dead:
		var pd: float = p.camera().global_position.distance_to(at)
		if pd < 16.0:
			var k: float = 1.0 - pd / 16.0
			p.add_shake(0.55 * k * k)
			for pad: int in Input.get_connected_joypads():
				Input.start_joy_vibration(pad, 0.45 * k, 0.85 * k, 0.22 + 0.18 * k)
	EventBus.shot_fired.emit(hit.shooter if hit else e, at, Vector3.UP)


func _splash_fireball(at: Vector3, radius: float, source_hit: BallisticHit) -> void:
	var tree: SceneTree = e.get_tree()
	var space: PhysicsDirectSpaceState3D = e.get_world_3d().direct_space_state
	var shooter: Node = source_hit.shooter if source_hit else null
	var w: WeaponData = source_hit.weapon if source_hit else null
	for n: Node in tree.get_nodes_in_group(&"enemies"):
		var other: Enemy = n as Enemy
		if other == null or other == e or not other.alive:
			continue
		var chest: Vector3 = other.body.chest_position()
		var d: float = chest.distance_to(at)
		if d > radius:
			continue
		var los: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(at, chest, Ballistics.LAYER_WORLD)
		if not space.intersect_ray(los).is_empty():
			continue
		var f: float = clampf(1.0 - pow(d / radius, 1.35), 0.15, 1.0)
		var away: Vector3 = (chest - at).normalized() if d > 0.05 else Vector3.UP
		var part: HitboxPart = other.body.hitboxes.get(&"chest")
		var sh: BallisticHit = BallisticHit.new()
		sh.weapon = w
		sh.shooter = shooter
		sh.point = chest
		sh.normal = -away
		sh.direction = away
		var info: DamageInfo = DamageInfo.new()
		info.type = DamageInfo.Type.FIRE
		info.amount = cfg.flamer_splash_damage * f
		info.impulse = 2.2 * f
		sh.damage = info
		other.last_hit = sh
		other._alerted_by(shooter)
		# Chain reaction: another Flamer right next to the fireball cooks off shortly after!
		if other.flamer and not other.flamer.can_detonated and d < radius * 0.72:
			other.flamer.schedule_cookoff(_rng.randf_range(0.18, 0.34), shooter)
		if other.boss:
			other.health -= info.amount * 0.5
			other.body.flinch(away, 0.6 * f, false)
			other.ignite(part, sh, cfg.flamer_splash_burn_time * 0.5, cfg.flamer_splash_burn_dps * 0.5, 0.0)
			if other.health <= 0.0:
				other.die(sh, &"chest", &"burn")
			continue
		other.health -= info.amount
		other.body.flinch(away, 1.6 * f, false)
		other.body.play_stumble()
		other.ignite(part, sh, cfg.flamer_splash_burn_time * (0.65 + 0.35 * f),
				cfg.flamer_splash_burn_dps, cfg.flamer_splash_agony * (0.6 + 0.4 * f))
		splash_ignited += 1
		if other.health <= 0.0:
			other.die(sh, &"chest", &"burn")
	for n2: Node in tree.get_nodes_in_group(&"dogs"):
		var dg: AttackDog = n2 as AttackDog
		if dg == null or not dg.alive:
			continue
		var c: Vector3 = dg.chest_position()
		var dd: float = c.distance_to(at)
		if dd > radius:
			continue
		var los2: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(at, c, Ballistics.LAYER_WORLD)
		if not space.intersect_ray(los2).is_empty():
			continue
		var ff: float = clampf(1.0 - pow(dd / radius, 1.35), 0.15, 1.0)
		var ddir: Vector3 = (c - at).normalized() if dd > 0.05 else Vector3.UP
		dg.strike(cfg.flamer_splash_damage * 1.15 * ff, Vector3(ddir.x, 0.0, ddir.z).normalized() * 1.5, shooter)
		Fx.burn_at(dg, c, Vector3.UP, 3.5, true)
		splash_ignited += 1
	# Point-blank risk/reward: shooting the can right in your own face singes you.
	var p: Player = _player()
	if p and not p.dead:
		var eye: Vector3 = p.camera().global_position
		var pd: float = eye.distance_to(at)
		var p_rad: float = radius * 0.72
		if pd < p_rad:
			var los3: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(at, eye, Ballistics.LAYER_WORLD)
			if space.intersect_ray(los3).is_empty():
				var pf: float = 1.0 - pd / p_rad
				p.on_fire_hit(e, cfg.flamer_splash_damage * cfg.flamer_player_splash_scale * pf,
						(eye - at).normalized(), cfg.flamer_burn_time * 0.6 * pf, cfg.flamer_burn_dps * 0.6)


# ------------------------------------------------------------------ combat decisions

## Called on Enemy's think tick while in COMBAT.
func decide() -> void:
	if not e.has_gun or not has_lighter or can_detonated:
		e._enter(Enemy.State.FLEE)
		return
	var p: Player = _player()
	if p == null or phase == Phase.IGNITE or phase == Phase.SPRAY:
		return
	var to_p: Vector3 = _flat(p.global_position - e.global_position)
	var d: float = to_p.length()
	if not _side_picked:
		_side_picked = true
		var fwd: Vector3 = _flat(-p.camera().global_basis.z)
		var c: float = fwd.cross(-to_p).y
		if absf(c) > 0.01:
			side = -signf(c)
	# Lost the operative: hunt to last_known (or latest squad tip).
	if not e.sees_player and e._unseen_for > 2.8 and e.last_known != Vector3.INF:
		if e._hunting() and e.global_position.distance_to(e.last_known) < 2.5:
			e.last_known = e.squad.search_point(e)
		e.tactic = Enemy.Tactic.MOVE
		e._go(e.last_known)
		if not e._said_lost:
			e._said_lost = true
			e._callout(&"lost")
		return
	if e.sees_player:
		e._said_lost = false
	if phase == Phase.REPOSITION:
		if _t < _len:
			if _reposition_to == Vector3.INF or _flat(e.global_position - _reposition_to).length() < 1.1:
				_pick_reposition(p, d)
			e.tactic = Enemy.Tactic.MOVE
			e._go(_reposition_to)
			return
		_enter(Phase.APPROACH, 0.0)
	# Approach: sprint fast, flanking and weaving in toward flame range.
	e.tactic = Enemy.Tactic.ADVANCE
	if d > cfg.flamer_engage_range + 4.5:
		e._go(_flank_point(p, d))
	else:
		var target: Vector3 = p.global_position
		if _watched_for > 0.35 and d > 4.2:
			var across: Vector3 = Vector3.UP.cross(to_p.normalized())
			target += across * side * sin(_weave) * 2.4
		e._go(target)


## Called every physics frame while in COMBAT (replaces standard gun aiming/firing).
func act(delta: float) -> void:
	if not e.has_gun or not has_lighter or can_detonated:
		_stop_flame()
		return
	var p: Player = _player()
	_t += delta
	_weave += delta * 3.8
	if p:
		var to_e: Vector3 = _flat(e.global_position - p.global_position)
		if to_e.length_squared() > 0.01:
			var watched: bool = _flat(-p.camera().global_basis.z).normalized().dot(to_e.normalized()) > cos(deg_to_rad(22.0))
			_watched_for = _watched_for + delta if watched and e.sees_player else maxf(0.0, _watched_for - delta * 2.0)
	match phase:
		Phase.IGNITE:
			_act_ignite(p, delta)
			return
		Phase.SPRAY:
			_act_spray(p, delta)
			return
		Phase.REPOSITION:
			_stop_flame()
			e.body.set_stance(&"run" if not e.limping else &"loco")
			_look(p, 0.45, delta, false)
			if _t >= _len:
				_enter(Phase.APPROACH, 0.0)
				e._think = 0.0
			return
	# APPROACH: fast sprint closing in; once in range with clear line, ignite!
	_stop_flame()
	var fast: bool = p == null or _flat(p.global_position - e.global_position).length() > cfg.flamer_engage_range + 0.5
	e.body.set_stance(&"run" if fast and not e.limping else &"loco")
	_look(p, 0.35 if fast else 0.85, delta, not fast)
	if p and e.sees_player and not p.dead:
		var d: float = _flat(p.global_position - e.global_position).length()
		if d <= cfg.flamer_engage_range and absf(p.global_position.y - e.global_position.y) < 2.2:
			_start_ignite(p)


## Agile velocity override during spray/ignite; INF leaves movement to navmesh.
func want_velocity() -> Vector3:
	if phase != Phase.IGNITE and phase != Phase.SPRAY:
		return Vector3.INF
	var p: Player = _player()
	if p == null:
		return Vector3.ZERO
	var to_p: Vector3 = _flat(p.global_position - e.global_position)
	var d: float = to_p.length()
	if d < 0.05:
		return Vector3.ZERO
	var fwd: Vector3 = to_p / d
	var strafe: Vector3 = Vector3.UP.cross(fwd) * side
	var radial: float = 0.0
	if d > cfg.flamer_range * 0.72:
		radial = 0.65  # press forward to keep the player inside the fire cone
	elif d < 2.3:
		radial = -0.55  # give himself breathing room while torching
	var dir: Vector3 = (strafe + fwd * radial).normalized()
	var spd: float = cfg.flamer_strafe_speed * (0.65 if phase == Phase.IGNITE else 1.0) * (0.5 if e.limping else 1.0)
	return dir * spd


func speed() -> float:
	return cfg.run_speed * (0.5 if e.limping else 1.0)


# ------------------------------------------------------------------ ignite & spray

func _start_ignite(p: Player) -> void:
	_enter(Phase.IGNITE, cfg.flamer_ignite_time)
	_damage_in_burst = 0.0
	var to: Vector3 = _target_point(p) - nozzle_position()
	_spray_yaw = atan2(to.x, to.z)
	_spray_pitch = clampf(atan2(to.y, Vector2(to.x, to.z).length()), -0.6, 0.6)
	e._stop()
	e.body.set_stance(&"loco")
	Sfx.play_at(&"flamer_ignite", nozzle_position(), 2.0, 0.08)
	if _rng.randf() < 0.45:
		e._callout(&"advance")


func _act_ignite(p: Player, delta: float) -> void:
	e.body.set_stance(&"loco")
	if p:
		var to: Vector3 = _target_point(p) - nozzle_position()
		var want_yaw: float = atan2(to.x, to.z)
		_spray_yaw = rotate_toward(_spray_yaw, want_yaw, deg_to_rad(cfg.turn_speed_deg) * delta)
		_spray_pitch = move_toward(_spray_pitch, clampf(atan2(to.y, Vector2(to.x, to.z).length()), -0.6, 0.6), delta * 3.0)
		e._yaw = rotate_toward(e._yaw, _spray_yaw, deg_to_rad(cfg.turn_speed_deg) * delta)
		e.rotation.y = e._yaw
		e.body.set_aim(wrapf(_spray_yaw - e._yaw, -PI, PI), _spray_pitch, 1.0)
	if _t >= _len:
		_start_spray()


func _start_spray() -> void:
	sprays += 1
	_enter(Phase.SPRAY, _rng.randf_range(cfg.flamer_spray_time.x, cfg.flamer_spray_time.y))
	_tick_cd = 0.04
	_play_spray_audio()


func _act_spray(p: Player, delta: float) -> void:
	e.body.set_stance(&"loco")
	if p and not p.dead:
		var to: Vector3 = _target_point(p) - nozzle_position()
		var want_yaw: float = atan2(to.x, to.z)
		var want_pitch: float = clampf(atan2(to.y, Vector2(to.x, to.z).length()), -0.6, 0.6)
		# Limited tracking speed while spraying so agile dodging works!
		var max_step: float = deg_to_rad(cfg.flamer_track_deg) * delta
		_spray_yaw = rotate_toward(_spray_yaw, want_yaw, max_step)
		_spray_pitch = move_toward(_spray_pitch, want_pitch, delta * 1.8)
		e._yaw = rotate_toward(e._yaw, _spray_yaw, max_step * 1.15)
		e.rotation.y = e._yaw
		e.body.set_aim(wrapf(_spray_yaw - e._yaw, -PI, PI), _spray_pitch, 1.0)
	var origin: Vector3 = nozzle_position()
	var dir: Vector3 = Vector3(sin(_spray_yaw) * cos(_spray_pitch), sin(_spray_pitch), cos(_spray_yaw) * cos(_spray_pitch)).normalized()
	_jet_reach = _probe_reach(origin, dir, cfg.flamer_range)
	if flame_jet:
		flame_jet.set_stream(true, origin, dir, _jet_reach)
	if _spray_audio and not _spray_audio.playing:
		_play_spray_audio()
	# Damage tick against the player inside the active flame cone.
	_tick_cd -= delta
	if _tick_cd <= 0.0:
		_tick_cd = TICK_INTERVAL
		_apply_flame_tick(p, origin, dir, _jet_reach)
	# Stop spraying if burst ends or the player got well out of range/sight.
	var far_out: bool = p == null or p.dead or _flat(p.global_position - e.global_position).length() > cfg.flamer_range + 3.2
	if _t >= _len or (far_out and _t > 0.45):
		_stop_flame()
		side = -side if _rng.randf() < 0.65 else side
		_reposition_to = Vector3.INF
		_enter(Phase.REPOSITION, _rng.randf_range(cfg.flamer_cooldown.x, cfg.flamer_cooldown.y))
		e._think = 0.0


func _apply_flame_tick(p: Player, origin: Vector3, dir: Vector3, reach: float) -> void:
	if p == null or p.dead:
		return
	var target: Vector3 = _target_point(p)
	var to: Vector3 = target - origin
	var dist: float = to.length()
	if dist > reach + 0.55 or dist < 0.05:
		return
	var ang_deg: float = rad_to_deg(dir.angle_to(to / dist))
	# Generous angular check near the nozzle where the player's body fills a wide angle.
	var half_cone: float = cfg.flamer_cone_deg * 0.5 + clampf(22.0 / maxf(dist, 0.8), 0.0, 18.0)
	if ang_deg > half_cone:
		return
	# Cover blocks the fire stream!
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(origin, target, FLAME_MASK)
	if not e.get_world_3d().direct_space_state.intersect_ray(q).is_empty():
		return
	# Closer = hotter (1.0 up to 55% reach, tapering gently to 0.72 at the far tip).
	var falloff: float = lerpf(1.0, 0.72, clampf((dist / maxf(cfg.flamer_range, 0.1) - 0.55) / 0.45, 0.0, 1.0))
	var dmg: float = cfg.flamer_dps * TICK_INTERVAL * falloff
	var dealt: float = p.on_fire_hit(e, dmg, dir, cfg.flamer_burn_time, cfg.flamer_burn_dps)
	if dealt > 0.0:
		fire_ticks += 1
		p.add_shake(0.11)


func _probe_reach(origin: Vector3, dir: Vector3, max_range: float) -> float:
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(origin, origin + dir * max_range, FLAME_MASK)
	var hit: Dictionary = e.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return max_range
	var pos: Vector3 = hit["position"]
	var nrm: Vector3 = hit["normal"]
	var d: float = origin.distance_to(pos)
	if Fx.enabled and _rng.randf() < 0.35:
		Fx._emit(&"sparks", pos, nrm, Color(1.0, 0.55, 0.15, 1.0), 4, 0.7)
	return maxf(d, 0.4)


func _stop_flame() -> void:
	if flame_jet:
		flame_jet.active = false
	if _spray_audio and _spray_audio.playing:
		_spray_audio.stop()


func _play_spray_audio() -> void:
	if _spray_audio == null:
		return
	var streams: Array = Sfx.bank(&"flamer_spray")
	if streams.is_empty():
		return
	_spray_audio.stream = streams[_rng.randi() % streams.size()]
	_spray_audio.volume_db = 2.0
	_spray_audio.pitch_scale = Sfx.world_pitch(0.06)
	_spray_audio.play()


# ------------------------------------------------------------------ navigation helpers

func _flank_point(p: Player, d: float) -> Vector3:
	var fwd: Vector3 = _flat(-p.camera().global_basis.z).normalized()
	if fwd.length_squared() < 0.01:
		fwd = Vector3.FORWARD
	var dir: Vector3 = fwd.rotated(Vector3.UP, -side * deg_to_rad(cfg.flank_angle_deg))
	return p.global_position + dir * clampf(d * 0.55, 3.8, 10.5)


func _pick_reposition(p: Player, d: float) -> void:
	var to_me: Vector3 = _flat(e.global_position - p.global_position)
	var radial: Vector3 = to_me.normalized() if to_me.length_squared() > 0.01 else Vector3.FORWARD
	var tangent: Vector3 = Vector3.UP.cross(radial) * side
	var want_dist: float = clampf(d, 4.2, cfg.flamer_range * 0.85)
	var candidate: Vector3 = p.global_position + (radial * 0.65 + tangent * 0.95).normalized() * want_dist
	var map: RID = e.get_world_3d().navigation_map
	if map.is_valid() and NavigationServer3D.map_get_iteration_id(map) > 0 and not NavigationServer3D.map_get_regions(map).is_empty():
		candidate = NavigationServer3D.map_get_closest_point(map, candidate)
	_reposition_to = candidate


func _look(p: Player, weight: float, delta: float, turn: bool) -> void:
	if p == null:
		e.body.set_aim(0.0, 0.0, 0.0)
		return
	var to: Vector3 = _target_point(p) - e.body.chest_position()
	var want_yaw: float = atan2(to.x, to.z)
	if turn:
		e._turn_toward(want_yaw, delta)
	var rel: float = wrapf(want_yaw - e._yaw, -PI, PI)
	e.body.set_aim(rel, atan2(to.y, Vector2(to.x, to.z).length()), weight)


func _target_point(p: Player) -> Vector3:
	return p.camera().global_position - Vector3.UP * 0.35


func _enter(ph: Phase, length: float) -> void:
	phase = ph
	_t = 0.0
	_len = length


func _player() -> Player:
	return e.squad.player() if e.squad else null


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)
