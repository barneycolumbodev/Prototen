class_name Enemy
extends CharacterBody3D
## A triad member (docs/design.md §5.1, §5.6). Unaugmented: slower, weaker
## and far more fragile than the player, and they know it.
##
## Damage: 19 zones with their own multipliers and reactions. Legs: stumble,
## limp, crawl. Arms and hands: aim ruined, weapon dropped (and often a
## surrender). Gut: doubled over. Head and neck: kill. Pass-through wounds
## bleed. Plates (Enforcer) stop what Ballistics says they stop.
## Gore at Maximum (docs/design.md §5.5, GoreConfig): a hit takes the body
## apart at the cut nearest where it landed, if it was violent enough
## (energy left + a share of what arrived): heads, arms at the upper arm,
## forearms, hands, legs above the knee, shins; destroyed outright when far
## past it; sustained fire adds up. Enough into the torso bursts the body.
##
## Behaviour (combat mode): awareness from sight, gunfire and bodies; cover,
## peeking and bursts, a few shooters at a time (Squad tokens); near misses
## suppress; morale drops with casualties, wounds and the augment close up,
## and when it breaks they flee, cower, fire blind or surrender.
## Passive mode (the firing range): they stand and react but never fire or walk off.

signal died(enemy: Enemy)

enum State { IDLE, ALERT, COMBAT, FLEE, SURRENDER, COWER, BLIND, CRAWL, GUT, DEAD }
enum Tactic { HOLD, MOVE, HIDE, PEEK, ADVANCE }

const LEG_ZONES: Array[StringName] = [&"l_thigh", &"l_shin", &"l_foot", &"r_thigh", &"r_shin", &"r_foot"]
const ARM_ZONES: Array[StringName] = [&"l_upper_arm", &"l_forearm", &"l_hand", &"r_upper_arm", &"r_forearm", &"r_hand"]
const LOS_MASK: int = Ballistics.LAYER_WORLD

@export var config: EnemyConfig
## Firing-range target: reacts, never fires or walks away.
@export var passive: bool = false
## Seed for what he wears (TriadLook); < 0: random.
@export var look_seed: int = -1
## What he wears, picked ahead by the spawner so his meshes are built in the
## background before he arrives (TriadMeshBaker); null: picked on spawn.
var look: TriadLook

var squad: Squad
var body: EnemyBody
## A man with a blade (EnemyConfig.melee): how he fights instead of shooting.
var melee: MeleeBrain
## A boss (EnemyConfig.boss): his attacks, his knee, his execution.
var boss: BossBrain
var nav: NavigationAgent3D
var state: State = State.IDLE
var tactic: Tactic = Tactic.HOLD
var health: float = 100.0
var alive: bool = true
var morale: float = 0.7
var suppression: float = 0.0
var awareness: float = 0.0
var sees_player: bool = false
var last_known: Vector3 = Vector3.INF
var zone_damage: Dictionary[StringName, float] = {}
var bleed_dps: float = 0.0
var has_gun: bool = true
var ammo: int = 30
var limping: bool = false
var arm_hurt: bool = false
var burn_left: float = 0.0
var burn_dps: float = 0.0
var charred: float = 0.0
## Plasma (docs/design.md §4.9): seconds left of burning agony (he runs
## blind, flails and screams, and doesn't fight), and when he next lurches.
var agony: float = 0.0
var _agony_turn: float = 0.0
var _agony_cry: float = 0.0
var _spread_check: float = 0.0
## Fire on a man spreads: a burning man who comes within SPREAD_REACH of
## another sets him alight too (checked every SPREAD_EVERY s, CATCH_CHANCE each time).
const SPREAD_REACH: float = 1.1
const SPREAD_EVERY: float = 0.4
const CATCH_CHANCE: float = 0.45
var last_hit: BallisticHit
## Hits per zone (range readout, tests).
var zone_hits: Dictionary[StringName, int] = {}
## The zones' hitboxes (same keys as EnemyBody.ZONES).
var parts: Dictionary[StringName, HitboxPart]:
	get:
		return body.hitboxes if body else {}
var dead: bool:
	get:
		return not alive
## Seconds since the last decision, since first seeing the player this time, of aim settle.
var _think: float = 0.0
var _seen_for: float = 0.0
var _unseen_for: float = 99.0
var _perceive: float = 0.0
var _state_time: float = 0.0
var _tactic_time: float = 0.0
var _tactic_len: float = 2.0
var _move_target: Vector3 = Vector3.INF
var _cover_point: Vector3 = Vector3.INF
var _burst_left: int = 0
var _shot_timer: float = 0.0
var _reloading: float = 0.0
var _has_token: bool = false
var _rounds_this_engagement: int = 0
var _yaw: float = 0.0
var _volley: int = -1
var _volley_dep: Dictionary[StringName, float] = {}
## Dismemberment (GoreConfig): violence at each cut this volley and in
## total, and into the torso.
var _cut_volley: Dictionary[StringName, float] = {}
var _cut_left: Dictionary[StringName, float] = {}
var _cut_total: Dictionary[StringName, float] = {}
var _torso_volley: float = 0.0
var _torso_total: float = 0.0
var _bleeders: Array[Bleeder] = []
var _drip_dist: float = 0.0
var _last_drip: Vector3
var _last_pos: Vector3
var _flash: MeshInstance3D
var _flash_time: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _pain_cooldown: float = 0.0
## Shove from a slide or a blast (m/s, world); decays on the ground.
var _knock: Vector3 = Vector3.ZERO
const KNOCK_DECAY: float = 13.0
## Launched by a slide (owner, 2026-11-14: "knock them in the air and then
## shoot them"): airborne, tumbling, out of the fight until he has landed
## and found his feet again. See `launch`.
var launched: bool = false
var _launch_air: bool = false
var _launch_time: float = 0.0
var _launch_air_time: float = 1.0
var _launch_gravity: float = 20.0
var _launch_tumble: float = 0.0
## Tumble axis in his own frame, and the tilt now (rad).
var _launch_axis: Vector3 = Vector3.RIGHT
var _launch_tilt: float = 0.0
var _launch_stun: float = 0.0
const GRAVITY: float = 20.0
## Height (m) of the point his body tumbles about (about his hips).
const TUMBLE_PIVOT: float = 1.0
## State when the killing blow landed (picks the death voice).
var state_before_death: State = State.IDLE
## Seized by the mesh arm (NT-5): limp in its grip, alive until he's thrown
## or dropped. Out of the fight (no AI, not in the enemies group).
var held: bool = false
## Thrown by the mesh arm: flying. He hits whoever is in the way and dies when he lands.
var _thrown_by: Node
var _thrown_speed: float = 0.0
var _thrown_time: float = 0.0
var _thrown_hit: Array[Node] = []
## Which of the triad voices speaks for him (VoiceLines.VOICES), picked at spawn.
var voice: StringName = &""
## His voice: callouts, pain and dying sounds, from his head. Every enemy has
## his own, so impacts and gunfire never steal it (they share Sfx's pool).
var mouth: AudioStreamPlayer3D
## Said "where'd he go" since he last saw the operative.
var _said_lost: bool = false
## What the squad has him doing while there's contact (Squad.assign_roles,
## docs/design.md §5.6a): pin, flank or push. NONE: his own judgment.
var squad_role: Squad.Role = Squad.Role.NONE
## Where a flanker is running to, and when his last flank ended (-1: never).
var flank_target: Vector3 = Vector3.INF
var flank_done_at: float = -1.0
var _role_time: float = 0.0
var _in_cover_for: float = 0.0
var _said_suppress: bool = false
var _stuck_check: float = 1.0
var _stuck_from: Vector3 = Vector3.INF
var _stuck_for: float = 0.0
const MOUTH_UNIT_SIZE: float = 10.0


## A stump bleeding after a limb or the head came off. A cut artery pumps
## in beats: a stream with each beat of the heart, weaker each time as the
## pressure falls; once the heart has stopped (or the pressure is gone) it
## only drips. `strength`: how big the artery is.
class Bleeder:
	extends RefCounted
	var part: StringName
	var age: float = 0.0
	var strength: float = 1.0
	## Drops owed (fractions carry over between frames).
	var owed: float = 0.0
	var count: int = 0

	func _init(p: StringName) -> void:
		part = p
		var n: String = String(p)
		strength = 1.0 if n == "head" or n.begins_with("upper_arm") or n.begins_with("thigh") else (0.5 if n.begins_with("hand") else 0.75)


func _ready() -> void:
	_rng.randomize()
	if config == null:
		config = load("res://data/enemies/gunman.tres") as EnemyConfig
	health = config.health
	ammo = config.magazine
	morale = clampf(config.courage + _rng.randf_range(-0.08, 0.08), 0.1, 1.0)
	add_to_group(&"enemies")
	add_to_group(&"aim_assist_targets")
	add_to_group(&"suppressible")
	add_to_group(&"triad")
	collision_layer = Ballistics.LAYER_ENEMY
	collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_ENEMY | Ballistics.LAYER_CLIP
	var cs: CollisionShape3D = CollisionShape3D.new()
	cs.name = "Capsule"
	var cap: CapsuleShape3D = CapsuleShape3D.new()
	cap.radius = 0.3 * maxf(config.body_scale / 1.12, 1.0)
	cap.height = 1.75 * config.body_scale
	cs.shape = cap
	cs.position = Vector3(0, cap.height * 0.5, 0)
	add_child(cs)
	body = EnemyBody.new()
	body.name = "Body"
	body.setup(self, config, look, look_seed)
	add_child(body)
	nav = NavigationAgent3D.new()
	nav.path_desired_distance = 0.6
	nav.target_desired_distance = 0.7
	nav.radius = 0.35
	nav.avoidance_enabled = false
	add_child(nav)
	_yaw = rotation.y
	_last_pos = global_position
	_build_flash()
	_build_mouth()
	body.set_stance(&"idle")
	if config.melee:
		melee = MeleeBrain.new(self)
	if config.boss:
		boss = BossBrain.new(self)
		boss.setup()
		morale = 1.0
	if not passive:
		EventBus.shot_fired.connect(_on_shot_heard)


# ------------------------------------------------------------------ queries

func aim_points() -> PackedVector3Array:
	if not alive or state == State.SURRENDER:
		return PackedVector3Array()
	return PackedVector3Array([body.head_position(), body.chest_position()])


func suppress_point() -> Vector3:
	return body.head_position() if alive else Vector3(0, -1000, 0)


func ballistic_exclude() -> Array[RID]:
	return body.ballistic_exclude()


func is_threat() -> bool:
	return alive and has_gun and state in [State.COMBAT, State.ALERT, State.BLIND]


func state_name() -> String:
	return State.keys()[state]


func set_squad_role(r: Squad.Role) -> void:
	if r == squad_role:
		return
	squad_role = r
	_role_time = 0.0


func _hunting() -> bool:
	return squad != null and squad.hunt != null


# ------------------------------------------------------------------ hits

func on_part_hit(part: HitboxPart, hit: BallisticHit) -> void:
	var zone: StringName = part.get_meta(&"zone")
	last_hit = hit
	zone_hits[zone] = zone_hits.get(zone, 0) + 1
	if hit.volley_id != _volley:
		_volley = hit.volley_id
		_volley_dep.clear()
		_cut_volley.clear()
		_cut_left.clear()
		_torso_volley = 0.0
	var dep: float = hit.deposited()
	_volley_dep[zone] = _volley_dep.get(zone, 0.0) + dep
	var head: bool = zone == &"head" or zone == &"neck"
	# Wounds and blood (also on corpses).
	# Drawn a little bigger than life so a hit reads at a distance on a
	# 720p phone (owner, 2026-11-13: more feedback the moment a round hits).
	var entry_r: float = clampf(0.011 + dep * 0.000006, 0.011, 0.024)
	body.add_wound(zone, hit.point, entry_r, false)
	if hit.result == BallisticHit.Result.PENETRATED:
		body.add_wound(zone, hit.exit_point, clampf(0.02 + hit.energy_out * 0.000005, 0.02, 0.05), true)
	var violence: float = sqrt(maxf(dep, 30.0) / 300.0)
	if hit.weapon and hit.weapon.gore_style != &"":
		# Its own effect replaces the usual sprays (the GX-4's corkscrew).
		Gore.special_hit(hit, body)
	else:
		Gore.flesh_hit(hit, violence, head)
	var impulse: Vector3 = hit.direction * hit.damage.impulse * TimeControl.impact_multiplier()
	if not alive:
		body.push_bone(zone, impulse * 1.2, hit.point)
		_try_sever(zone, hit)
		_try_burst(zone, hit)
		return
	var mult: float = config.zone_multipliers.get(zone, 1.0)
	var dmg: float = hit.damage.amount * mult
	zone_damage[zone] = zone_damage.get(zone, 0.0) + dmg
	if boss:
		_boss_hit(zone, dmg, hit, head)
		return
	health -= dmg
	if hit.result == BallisticHit.Result.PENETRATED:
		bleed_dps = minf(bleed_dps + 1.5, 6.0)
	body.flinch(hit.direction, clampf(hit.damage.impulse / 3.0 * TimeControl.impact_multiplier(), 0.3, 3.5), head)
	if melee:
		melee.on_hurt(dmg)
	_alerted_by(hit.shooter)
	suppression = minf(suppression + 0.45, 1.0)
	morale -= 0.08 + clampf(dmg / 300.0, 0.0, 0.2)
	if _try_sever(zone, hit) and not alive:
		return
	if _try_burst(zone, hit):
		return
	var kind: StringName = &"hit"
	if health <= 0.0:
		kind = &"kill"
		die(hit, zone)
	else:
		if head:
			kind = &"headshot"
		if hit.weapon and hit.weapon.stagger_push > 0.0 and not melee:
			# A heavy round that doesn't kill still takes him off his feet's line.
			knock_back(hit.direction * hit.weapon.stagger_push + Vector3.UP * 0.6, hit.shooter, 0.0, 0.15)
			if not alive:
				EventBus.target_hit.emit(&"kill", hit)
				EventBus.damage_applied.emit(hit.damage, self)
				return
		_react(zone, dmg, hit)
	EventBus.target_hit.emit(kind, hit)
	EventBus.damage_applied.emit(hit.damage, self)


## A round into the boss: no limb wounds or flight, no gore that takes him
## apart; staggers and rage (BossBrain); at zero he goes down on one knee.
func _boss_hit(zone: StringName, dmg: float, hit: BallisticHit, head: bool) -> void:
	if boss.is_down() or boss.phase == BossBrain.Phase.INTRO:
		body.flinch(hit.direction, 0.6, head)
		EventBus.target_hit.emit(&"hit", hit)
		return
	health -= dmg
	body.flinch(hit.direction, clampf(hit.damage.impulse / 9.0 * TimeControl.impact_multiplier(), 0.15, 1.6), head)
	_alerted_by(hit.shooter)
	boss.on_hurt(dmg, hit)
	var kind: StringName = &"headshot" if head else &"hit"
	if health <= 0.0:
		kind = &"kill"
		die(hit, zone)
	elif _pain_cooldown <= 0.0 and dmg > 30.0:
		_pain_cooldown = 1.6
		vocal(&"enemy_pain", 2.0, 0.05)
	EventBus.target_hit.emit(kind, hit)
	EventBus.damage_applied.emit(hit.damage, self)


## Shoved by the operative (a slide into him): flies back along `push`,
## staggers, gets hurt a little and badly rattled. Dead men don't get shoved
## here (their ragdoll takes hits through push_bone).
func knock_back(push: Vector3, from: Node, damage: float, morale_loss: float) -> void:
	if not alive:
		return
	if boss:
		# Too heavy to shove: it hurts (capped: a knife isn't a kill here) and may stagger.
		if boss.is_down() or boss.phase == BossBrain.Phase.INTRO:
			return
		var dmg: float = minf(damage, 150.0)
		health -= dmg
		body.flinch(push.normalized(), 1.0, false)
		Sfx.play_at(&"impact_flesh", body.chest_position(), -2.0, 0.1)
		_alerted_by(from)
		boss.on_hurt(dmg, null)
		if health <= 0.0:
			die(null, &"chest", &"impact")
		return
	if melee:
		melee.reset()
	_knock = Vector3(push.x, 0.0, push.z).limit_length(14.0)
	velocity.y = maxf(velocity.y, minf(push.y, 6.0))
	body.play_stumble()
	body.flinch(push.normalized(), clampf(push.length() / 2.5, 0.6, 3.5), false)
	suppression = minf(suppression + 0.6, 1.0)
	morale -= morale_loss
	_alerted_by(from)
	health -= damage
	Sfx.play_at(&"body_fall", body.chest_position(), -6.0, 0.1)
	if _pain_cooldown <= 0.0:
		_pain_cooldown = 1.5
		vocal(&"enemy_pain", -3.0)
	if health <= 0.0:
		# Broken by the impact: he goes flying the way he was shoved.
		velocity = Vector3(push.x, maxf(push.y, 2.0), push.z).limit_length(9.0)
		die(null, &"chest", &"impact")


## Knocked into the air by a slide (no damage): `v` (m/s, world) sends him
## up and along; he falls under `gravity`, tumbling back up to `tumble_deg`
## (feet swept out, head toward whoever hit him), can't shoot or think while
## he's up, and needs `stun` seconds on the ground after he lands. A kill in
## the air sends the ragdoll on with his flight (die() uses his velocity).
func launch(v: Vector3, from: Node, morale_loss: float, gravity: float, tumble_deg: float, stun: float) -> void:
	if not alive or held or _thrown_speed > 0.0 or boss:
		return
	if melee:
		melee.reset()
	launched = true
	_launch_air = true
	_launch_time = 0.0
	_launch_gravity = maxf(gravity, 1.0)
	_launch_air_time = 2.0 * maxf(v.y, 0.5) / _launch_gravity
	_launch_tumble = deg_to_rad(tumble_deg) * _rng.randf_range(0.85, 1.15)
	_launch_stun = stun
	var flat: Vector3 = Vector3(v.x, 0.0, v.z)
	var dir: Vector3 = flat.normalized() if flat.length() > 0.05 else -global_basis.z
	# Top of the body toward -dir: about dir × up, a little skewed so no two
	# launches look the same.
	var axis_world: Vector3 = dir.cross(Vector3.UP).rotated(Vector3.UP, _rng.randf_range(-0.35, 0.35))
	_launch_axis = (global_basis.inverse() * axis_world).normalized()
	_knock = flat.limit_length(10.0)
	velocity.y = v.y
	_stop()
	body.play_stumble()
	body.flinch(-dir, 3.0, false)
	suppression = 1.0
	morale -= morale_loss
	_alerted_by(from)
	Sfx.play_at(&"body_fall", body.chest_position(), -4.0, 0.1)
	if _pain_cooldown <= 0.0:
		_pain_cooldown = 1.2
		vocal(&"enemy_pain", -2.0, 0.1)


## Flight, landing and getting up after a launch. True while he's out of the fight.
func _update_launch(delta: float) -> bool:
	if not launched:
		return false
	_launch_time += delta
	if _launch_air:
		var f: float = clampf(_launch_time / _launch_air_time, 0.0, 1.0)
		_launch_tilt = _launch_tumble * pow(sin(PI * minf(f * 1.15, 1.0)), 0.6)
		if _launch_time > 0.12 and is_on_floor() and velocity.y <= 0.0:
			_launch_air = false
			_launch_time = 0.0
			body.play_stumble()
			Sfx.play_at(&"body_fall", global_position + Vector3.UP * 0.3, -1.0, 0.1)
	else:
		_launch_tilt = move_toward(_launch_tilt, 0.0, delta * 4.0)
		if _launch_time >= _launch_stun and _launch_tilt <= 0.0:
			launched = false
	_apply_tumble()
	return launched


func _apply_tumble() -> void:
	if is_zero_approx(_launch_tilt):
		body.transform = Transform3D.IDENTITY
		return
	var b: Basis = Basis(_launch_axis, _launch_tilt)
	var pivot: Vector3 = Vector3.UP * TUMBLE_PIVOT
	body.transform = Transform3D(b, pivot - b * pivot)


## Seized by the mesh arm: he goes limp in its grip (a ragdoll, still
## alive), drops his gun and leaves the fight. Returns false if he can't be
## taken (dead, already held).
func seize(by: Node) -> bool:
	if not alive or held or boss:
		return false
	held = true
	if melee:
		melee.reset()
	remove_from_group(&"enemies")
	remove_from_group(&"aim_assist_targets")
	remove_from_group(&"suppressible")
	_release_token()
	_stop()
	if has_gun:
		has_gun = false
		body.drop_gun(Vector3.UP * 1.5)
	(get_node(^"Capsule") as CollisionShape3D).disabled = true
	velocity = Vector3.ZERO
	body.hold_awake = true
	body.ragdoll(Vector3.ZERO, body.chest_position(), &"chest")
	morale = 0.0
	_pain_cooldown = 0.9
	if _rng.randf() < 0.65:
		speak(&"grabbed")
	else:
		vocal(&"death_scream", -3.0)
	if squad:
		squad.on_ally_seized(self, by)
	return true


## Let go by the mesh arm with `throw_velocity` (zero: dropped). He flies,
## knocks down whoever he hits, and dies where he lands.
func release(throw_velocity: Vector3, by: Node) -> void:
	if not held:
		return
	held = false
	body.hold_awake = false
	body.fling(throw_velocity)
	_thrown_by = by
	_thrown_speed = maxf(throw_velocity.length(), 0.5)
	_thrown_time = 0.0
	set_physics_process(true)
	_thrown_hit.clear()


func _update_thrown(delta: float) -> void:
	_thrown_time += delta
	var at: Vector3 = body.chest_position()
	var v: Vector3 = body.chest_velocity()
	if _thrown_speed > 4.0:
		for n: Node in get_tree().get_nodes_in_group(&"enemies"):
			var e: Enemy = n as Enemy
			if e == null or e == self or not e.alive or n in _thrown_hit:
				continue
			if e.body.chest_position().distance_to(at) < 1.0:
				_thrown_hit.append(n)
				var push: Vector3 = v * 0.6 + Vector3.UP * 1.5
				var lethal: bool = v.length() >= 13.0
				e.knock_back(push, _thrown_by, 9999.0 if lethal else v.length() * 6.0, 0.5)
				Sfx.play_at(&"impact_flesh", at, 2.0, 0.1)
				Gore.spray(at, v.normalized(), 1.2, 6)
				EventBus.slide_impact.emit(e, v.length())
	var landed: bool = _thrown_time > 0.2 and v.length() < maxf(_thrown_speed * 0.45, 2.5)
	if landed or _thrown_time > 2.0:
		_thrown_speed = 0.0
		if alive:
			Gore.spray(at, Vector3.UP, 1.4, 10)
			Sfx.play_at(&"impact_flesh", at, 3.0, 0.1)
			die(null, &"chest", &"impact")


## A round hit a plate in the carrier (stopped or not: Ballistics decided).
func on_plate_hit(_plate: Node, hit: BallisticHit) -> void:
	if not alive:
		return
	body.flinch(hit.direction, clampf(hit.damage.impulse / 2.5, 0.4, 2.5), false)
	if hit.result == BallisticHit.Result.STOPPED:
		# Blunt trauma through the plate.
		health -= hit.damage.amount * config.armor_blunt
		suppression = minf(suppression + 0.3, 1.0)
		_alerted_by(hit.shooter)
		if hit.energy_in > 1500.0 and _rng.randf() < 0.6:
			body.play_stumble()
		if boss:
			boss.on_hurt(hit.damage.amount * config.armor_blunt, hit)
		if health <= 0.0:
			die(hit, &"chest")
			EventBus.target_hit.emit(&"kill", hit)
			return
		EventBus.target_hit.emit(&"armor", hit)


func on_part_burn(part: HitboxPart, hit: BallisticHit) -> void:
	if not alive:
		return
	if burn_left <= 0.0:
		Fx.burn_at(part, hit.point, hit.normal, hit.weapon.burn_time, true)
		if _rng.randf() < 0.6:
			speak(&"burning")
		elif Sfx.claim_death_voice():
			vocal(&"death_scream", -2.0)
	burn_left = maxf(burn_left, hit.weapon.burn_time)
	burn_dps = maxf(burn_dps, hit.weapon.burn_dps)
	last_hit = hit
	_alerted_by(hit.shooter)
	morale -= 0.05


func is_burning() -> bool:
	return burn_left > 0.0


func on_near_miss(shooter: Node, weapon: WeaponData, distance: float, _point: Vector3) -> void:
	if not alive or shooter == self or (shooter != null and shooter.is_in_group(&"triad")):
		return
	var k: float = (1.0 - distance / Ballistics.NEAR_MISS_RADIUS) * clampf(weapon.muzzle_energy() / 1500.0, 0.3, 2.0)
	var before: float = suppression
	suppression = minf(suppression + k * 0.35 * (1.0 - config.suppression_resist), 1.0)
	_alerted_by(shooter)
	if before < 0.55 and suppression >= 0.55 and state == State.COMBAT:
		_callout(&"pinned")


func _alerted_by(shooter: Node) -> void:
	var p: Player = squad.player() if squad else null
	if p and (shooter == p or shooter == null):
		last_known = p.global_position
	awareness = 1.0
	if (state == State.IDLE or state == State.ALERT) and not passive:
		_enter(State.COMBAT)


func _react(zone: StringName, dmg: float, hit: BallisticHit) -> void:
	var leg_hits: int = 0
	for z: StringName in LEG_ZONES:
		if zone_damage.get(z, 0.0) > config.limb_cripple:
			leg_hits += 1
	if zone in LEG_ZONES:
		if leg_hits >= 2 or (leg_hits == 1 and health < config.health * 0.45):
			_enter(State.CRAWL)
			_callout(&"legs")
			return
		if leg_hits == 1:
			limping = true
		body.play_stumble()
	elif zone in ARM_ZONES:
		arm_hurt = arm_hurt or zone_damage.get(zone, 0.0) > config.limb_cripple * 0.6
		var drop: float = {&"r_hand": 0.8, &"l_hand": 0.55, &"r_forearm": 0.5, &"l_forearm": 0.35}.get(zone, 0.15)
		if has_gun and _rng.randf() < drop:
			has_gun = false
			body.drop_gun(hit.direction * 2.0 + Vector3.UP)
			morale -= 0.25
			if morale < 0.45 and squad and squad.player() and global_position.distance_to(squad.player().global_position) < 18.0:
				_enter(State.SURRENDER)
			else:
				_enter(State.FLEE)
			return
	elif (zone == &"stomach" or zone == &"pelvis") and dmg > 20.0 and health < config.health * 0.7:
		_enter(State.GUT)
		return
	elif dmg > 35.0 and _rng.randf() < 0.5:
		body.play_stumble()
	if _pain_cooldown <= 0.0:
		_pain_cooldown = 2.0
		vocal(&"enemy_pain", -4.0)


## Maximum gore: takes the body apart at the cut nearest the hit when the
## volley is violent enough there, or enough has added up (GoreConfig).
## Returns whether something came off.
func _try_sever(zone: StringName, hit: BallisticHit) -> bool:
	if not Gore.is_maximum() or body.gibbed or (boss and not boss.executed):
		return false
	var cfg: GoreConfig = Gore.config
	var type: DamageInfo.Type = hit.damage.type if hit.damage else DamageInfo.Type.BALLISTIC
	var v: float = Dismemberment.violence(cfg, hit.deposited(), hit.energy_in, type)
	var pick: Array = Dismemberment.nearest_cut(cfg, zone, hit.point, body.cut_points(), body.severed)
	var seg: StringName = pick[0]
	if seg == &"":
		return false
	var reach: float = pick[1]
	var share: float = v * reach
	_cut_volley[seg] = _cut_volley.get(seg, 0.0) + share
	# What the round left in the piece (not what it carried on through).
	_cut_left[seg] = _cut_left.get(seg, 0.0) + Dismemberment.violence(cfg, hit.deposited(), 0.0, type) * reach
	if Dismemberment.adds_up(cfg, seg, share):
		_cut_total[seg] = _cut_total.get(seg, 0.0) + share
	var volley: float = _cut_volley[seg]
	var so_far: float = _cut_total.get(seg, 0.0)
	var result: Dismemberment.Outcome = Dismemberment.outcome(cfg, seg, volley, so_far, _cut_left[seg], zone == &"head")
	if result == Dismemberment.Outcome.NONE:
		return false
	var destroy: bool = result == Dismemberment.Outcome.PULP
	var speed: float = Dismemberment.fling_speed(cfg, volley)
	var v_out: Vector3 = hit.direction * speed + Vector3.UP * minf(1.5 + speed * 0.15, 3.0)
	return sever(seg, v_out, destroy, hit, zone)


## Cuts `seg` off (and what's on it) and makes the man react. Also used by
## blasts. Returns whether it came off.
func sever(seg: StringName, velocity_out: Vector3, destroy: bool, hit: BallisticHit = null, zone: StringName = &"chest",
		cauterize: bool = false) -> bool:
	if boss and not boss.executed:
		return false
	var group: Array[StringName] = body.attached(seg)
	if not body.sever(seg, velocity_out, destroy, cauterize):
		return false
	if not cauterize:
		_bleeders.append(Bleeder.new(seg))
	set_physics_process(true)
	Sfx.play_at(&"gore_sever", body.cut_point(seg), 0.0, 0.1)
	if not alive:
		return true
	if seg == &"head":
		health = 0.0
		die(hit, zone)
		if hit:
			EventBus.target_hit.emit(&"kill", hit)
	elif seg.begins_with("thigh") or seg.begins_with("shin"):
		_enter(State.CRAWL)
		morale = 0.0
		speak(&"legs")
	else:
		has_gun = has_gun and not (&"hand_R" in group)
		morale = 0.0
		_enter(State.COWER if _rng.randf() < 0.5 else State.FLEE)
		speak(&"limb_off")
	if not cauterize:
		bleed_dps = maxf(bleed_dps, 14.0 if seg.begins_with("upper_arm") or seg.begins_with("thigh") else 9.0)
	return true


# ------------------------------------------------------------------ plasma (docs/design.md §4.9)

## A plasma bolt hit `part` square on. `charge`: the shot's 0..1. Returns
## true if the bolt stops in him, false if it burned through and carries on.
func on_plasma_hit(part: HitboxPart, hit: BallisticHit, charge: float, pd: PlasmaData) -> bool:
	var zone: StringName = part.get_meta(&"zone")
	last_hit = hit
	zone_hits[zone] = zone_hits.get(zone, 0) + 1
	var torso: bool = zone in Dismemberment.TORSO
	var head: bool = zone == &"head" or zone == &"neck"
	var maximum: bool = Gore.is_maximum()
	var through: bool = torso and charge >= pd.burn_through_charge
	# The wound is a burn: cooked, no blood (Gore.plasma_hit), charred round it.
	body.add_wound(zone, hit.point, pd.at(0.02, 0.045, charge), false)
	if through:
		body.add_hole(zone, hit.point, hit.direction, pd.hole_radius(charge))
	Gore.plasma_hit(hit, charge, through)
	var push: Vector3 = hit.direction * pd.push_full * charge
	if not alive:
		body.push_bone(zone, push * 6.0, hit.point)
		if not torso and maximum and charge >= pd.sever_charge and not body.gibbed:
			_plasma_sever(zone, hit, charge, pd)
		Fx.burn_at(part, hit.point, hit.normal, pd.burn_time, true)
		charred = minf(charred + 0.3 * charge, 1.0)
		body.set_char(charred)
		return not through
	var mult: float = config.zone_multipliers.get(zone, 1.0)
	var dmg: float = pd.damage(charge) * mult
	if boss:
		_boss_hit(zone, dmg, hit, head)
		ignite(part, hit, pd.burn_time * 0.5, pd.burn_dps(charge) * 0.5, 0.0)
		return true
	zone_damage[zone] = zone_damage.get(zone, 0.0) + dmg
	health -= dmg
	_alerted_by(hit.shooter)
	body.flinch(hit.direction, clampf(1.0 + 2.5 * charge, 0.6, 3.5), head)
	if maximum and charge >= (pd.head_charge if head else pd.sever_charge) and not torso:
		_plasma_sever(zone, hit, charge, pd)
		if not alive:
			return true
	ignite(part, hit, pd.burn_time, pd.burn_dps(charge), pd.agony_time)
	var kind: StringName = &"hit"
	if health <= 0.0:
		kind = &"kill"
		die(hit, zone, &"shot")
	elif head:
		kind = &"headshot"
	EventBus.target_hit.emit(kind, hit)
	EventBus.damage_applied.emit(hit.damage, self)
	if alive and charge > 0.3 and not melee:
		knock_back(push + Vector3.UP * 0.5, hit.shooter, 0.0, 0.2)
	return not through


## Plasma that only passed close (or the splash where it burst): he catches
## fire and goes mad with it.
func on_plasma_graze(part: HitboxPart, hit: BallisticHit, charge: float, pd: PlasmaData) -> void:
	if not alive:
		Fx.burn_at(part, hit.point, hit.normal, pd.burn_time * 0.5, false)
		return
	last_hit = hit
	_alerted_by(hit.shooter)
	health -= pd.damage(charge) * 0.12
	ignite(part, hit, pd.burn_time * pd.graze_burn, pd.burn_dps(charge), pd.agony_time)
	if health <= 0.0:
		die(hit, &"chest", &"burn")
		EventBus.target_hit.emit(&"kill", hit)
	else:
		EventBus.target_hit.emit(&"hit", hit)


## Sets him alight (Fx fire riding on `part`): `seconds` of `dps`, and
## `agony_s` seconds of burning panic.
func ignite(part: HitboxPart, hit: BallisticHit, seconds: float, dps: float, agony_s: float) -> void:
	if not alive:
		return
	var first: bool = burn_left <= 0.0
	burn_left = maxf(burn_left, seconds)
	burn_dps = maxf(burn_dps, dps)
	charred = minf(charred + 0.12, 1.0)
	body.set_char(charred)
	var on: Node3D = part
	if on == null:
		on = body
	Fx.burn_at(on, hit.point, hit.normal, seconds, true)
	if agony_s <= 0.0 or boss:
		return
	var was: float = agony
	agony = maxf(agony, agony_s)
	morale = 0.0
	suppression = 1.0
	if was <= 0.0 and state not in [State.CRAWL, State.DEAD, State.SURRENDER]:
		if has_gun and _rng.randf() < 0.55:
			has_gun = false
			body.drop_gun(Vector3(_rng.randf_range(-1, 1), 1.5, _rng.randf_range(-1, 1)))
		_enter(State.FLEE)
		_agony_turn = 0.0
	if first or was <= 0.0:
		_agony_cry = 0.0


## Takes off the piece nearest a plasma hit, cauterised: whole and burning,
## or (a full charge, or the head) burned to charred pieces.
func _plasma_sever(zone: StringName, hit: BallisticHit, charge: float, pd: PlasmaData) -> void:
	var pick: Array = Dismemberment.nearest_cut(Gore.config, zone, hit.point, body.cut_points(), body.severed)
	var seg: StringName = pick[0]
	if seg == &"":
		return
	var destroy: bool = seg == &"head" or charge >= pd.pulp_charge
	var v_out: Vector3 = hit.direction * (3.0 + 4.0 * charge) + Vector3.UP * (1.5 + 1.5 * charge)
	var at: Vector3 = body.cut_point(seg)
	if sever(seg, v_out, destroy, hit, zone, true):
		Gore.charred_chunks(at, hit.direction + Vector3.UP * 0.4, 3 + roundi(4.0 * charge) if destroy else 2,
				3.0 + 5.0 * charge, pd.burn_time)
		Fx._emit(&"smoke", at, Vector3.UP, Color(0.18, 0.16, 0.15, 0.4), 4, 0.8)


## A burning man sets those he runs into alight (and the panic with it).
func _spread_fire(delta: float) -> void:
	if burn_left <= 0.0 or not alive:
		return
	_spread_check -= delta
	if _spread_check > 0.0:
		return
	_spread_check = SPREAD_EVERY
	for n: Node in get_tree().get_nodes_in_group(&"triad"):
		var other: Enemy = n as Enemy
		if other == null or other == self or not other.alive or other.is_burning() or other.boss:
			continue
		if other.global_position.distance_to(global_position) > SPREAD_REACH:
			continue
		if _rng.randf() > CATCH_CHANCE:
			continue
		var h: BallisticHit = last_hit
		if h == null:
			continue
		var part: HitboxPart = other.body.hitboxes[&"chest"] if other.body.hitboxes.has(&"chest") else null
		var catch_hit: BallisticHit = BallisticHit.new()
		catch_hit.weapon = h.weapon
		catch_hit.shooter = h.shooter
		catch_hit.damage = h.damage
		catch_hit.point = other.body.chest_position()
		catch_hit.normal = (global_position - other.global_position).normalized()
		catch_hit.direction = -catch_hit.normal
		other.last_hit = catch_hit
		other.ignite(part, catch_hit, burn_left * 0.8, burn_dps * 0.8, 4.0)
		other.speak(&"burning")


func _update_agony(delta: float) -> void:
	_spread_fire(delta)
	if agony <= 0.0:
		return
	agony -= delta
	if not alive or state in [State.DEAD, State.CRAWL]:
		agony = 0.0
		return
	_agony_turn -= delta
	if _agony_turn <= 0.0:
		# Blind, burning: he lurches one way then another, clawing at himself.
		_agony_turn = _rng.randf_range(0.45, 0.9)
		var dir: Vector3 = Vector3(_rng.randf_range(-1, 1), 0.0, _rng.randf_range(-1, 1)).normalized()
		_go(global_position + dir * _rng.randf_range(3.0, 6.5))
		body.flinch(-dir, _rng.randf_range(1.2, 2.6), _rng.randf() < 0.3)
		if _rng.randf() < 0.3:
			body.play_stumble()
	_agony_cry -= delta
	if _agony_cry <= 0.0:
		_agony_cry = _rng.randf_range(1.4, 2.4)
		if _rng.randf() < 0.45:
			speak(&"burning")
		elif Sfx.claim_death_voice():
			vocal(&"death_scream", -1.0, 0.15)
		else:
			vocal(&"enemy_pain", 0.0, 0.2)
	if state != State.FLEE and state != State.DEAD:
		_enter(State.FLEE)


## Maximum gore: enough into the torso in one volley (or into a corpse over
## time) blows the whole body apart. Returns whether it did.
func _try_burst(zone: StringName, hit: BallisticHit) -> bool:
	if not Gore.is_maximum() or body.gibbed or not zone in Dismemberment.TORSO or (boss and not boss.executed):
		return false
	var cfg: GoreConfig = Gore.config
	var type: DamageInfo.Type = hit.damage.type if hit.damage else DamageInfo.Type.BALLISTIC
	var v: float = Dismemberment.violence(cfg, hit.deposited(), hit.energy_in, type)
	_torso_volley += v
	_torso_total += v
	if _torso_volley < cfg.gib_volley_j * cfg.toughness and (alive or _torso_total < cfg.gib_corpse_j * cfg.toughness):
		return false
	burst(hit.direction * Dismemberment.fling_speed(cfg, _torso_volley), hit, zone)
	return true


## Blown apart (a huge hit, a blast up close, a corpse shot to pieces).
func burst(push: Vector3, hit: BallisticHit = null, zone: StringName = &"chest") -> void:
	if body.gibbed or (boss and not boss.executed):
		return
	if alive:
		health = 0.0
		die(hit, zone)
		if hit:
			EventBus.target_hit.emit(&"kill", hit)
	_bleeders.clear()
	body.burst(push)
	Sfx.play_at(&"gore_sever", body.global_position + Vector3.UP, 3.0, 0.1)


## `cause`: &"shot", &"bleed" (bled out) or &"burn" (burned to death).
func die(hit: BallisticHit, zone: StringName, cause: StringName = &"shot") -> void:
	if not alive:
		return
	if boss and not boss.executed:
		# A boss doesn't die at zero: he goes down on one knee for the execution.
		boss.go_down()
		return
	alive = false
	state_before_death = state
	_enter(State.DEAD)
	remove_from_group(&"enemies")
	remove_from_group(&"aim_assist_targets")
	remove_from_group(&"suppressible")
	_release_token()
	(get_node(^"Capsule") as CollisionShape3D).disabled = true
	if body.gun:
		body.drop_gun(velocity + (hit.direction if hit else Vector3.ZERO) * 1.5 + Vector3.UP)
	var impulse: Vector3 = Vector3.ZERO
	var point: Vector3 = body.chest_position()
	if hit:
		var heavy: float = clampf(hit.damage.impulse, 4.0, 40.0) * (hit.weapon.ragdoll_push if hit.weapon else 1.0)
		impulse = (hit.direction * heavy * 1.4 + Vector3.UP * heavy * 0.15) * TimeControl.impact_multiplier()
		point = hit.point
	body.ragdoll(impulse + velocity * 40.0, point, zone)
	body.ragdoll_frozen.connect(_on_frozen, CONNECT_ONE_SHOT)
	create_tween().tween_method(body.set_rim, 1.0, 0.0, 0.8)
	Sfx.play_at(&"body_fall", global_position + Vector3.UP * 0.5, -2.0, 0.1)
	var cry: StringName = death_cry(zone, cause == &"shot" and hit != null, state_before_death, cause == &"burn" or is_burning(), _rng.randf())
	if cry != &"" and Sfx.claim_death_voice():
		vocal(cry, -1.0, 0.08)
	elif cry == &"" and mouth:
		mouth.stop()  # a head shot cuts him off mid-word
	if squad:
		squad.on_death(self, hit)
	EventBus.killed.emit(self, hit.damage if hit else null)
	died.emit(self)


## Which dying sound fits (owner, 2026-11-05: "add audio for enemies dying").
## Head shots: the air leaving, or nothing when the head is gone. Neck: choking.
## Chest: choking or a scream. Burning: a scream. Bleeding out or crawling: a
## long groan. Everything else: a scream. `roll` is 0..1.
static func death_cry(zone: StringName, shot: bool, before: State, burning: bool, roll: float) -> StringName:
	if burning:
		return &"death_scream"
	if not shot or before == State.CRAWL:
		return &"death_groan"
	match zone:
		&"head":
			return &"death_breath" if roll < 0.6 else &""
		&"neck":
			return &"death_choke"
		&"chest":
			return &"death_choke" if roll < 0.45 else &"death_scream"
		&"stomach", &"pelvis":
			return &"death_groan" if roll < 0.35 else &"death_scream"
	return &"death_scream"


func _on_frozen() -> void:
	Gore.pool_under(body.bone_position(&"chest"), 0.55 if Gore.is_maximum() else 0.4)


# ------------------------------------------------------------------ hearing

func _on_shot_heard(shooter: Node, origin: Vector3, _dir: Vector3) -> void:
	if not alive or shooter == null or not shooter.is_in_group(&"player"):
		return
	var range_m: float = config.hearing_range
	var p: Player = shooter as Player
	if p and p.weapon() and p.weapon().data and p.weapon().data.flash_scale < 0.5:
		range_m *= config.suppressed_hearing  # suppressed guns
	if global_position.distance_to(origin) < range_m:
		last_known = origin
		awareness = maxf(awareness, 0.8)
		if state == State.IDLE:
			_enter(State.ALERT)


## A friend went down where this one could see it.
func on_ally_down(where: Vector3, gory: bool, officer: bool) -> void:
	if not alive:
		return
	var d: float = global_position.distance_to(where)
	if d > 20.0:
		return
	morale -= (0.12 + (0.12 if gory else 0.0)) * (1.0 - d / 25.0) + (0.25 if officer else 0.0)
	last_known = where if last_known == Vector3.INF else last_known
	awareness = maxf(awareness, 0.7)
	if state == State.IDLE and not passive:
		_enter(State.ALERT)


# ------------------------------------------------------------------ update

func _physics_process(delta: float) -> void:
	if not alive:
		_update_bleeders(delta)
		if _thrown_speed > 0.0:
			_update_thrown(delta)
		elif _bleeders.is_empty() and body.frozen and not held:
			# A frozen corpse that has stopped bleeding runs no code until a
			# cut or a throw wakes it (optimization overhaul F-15).
			set_physics_process(false)
		return
	if held or _thrown_speed > 0.0:
		_update_bleeders(delta)
		if _thrown_speed > 0.0:
			_update_thrown(delta)
		elif _pain_cooldown <= 0.0:
			_pain_cooldown = _rng.randf_range(1.2, 2.4)
			vocal(&"enemy_pain", -2.0, 0.15)
		_pain_cooldown -= delta
		return
	if boss and (boss.phase == BossBrain.Phase.INTRO or boss.is_down()):
		if boss.is_down():
			boss.down_frame(delta)
		return
	_state_time += delta
	_pain_cooldown -= delta
	if state == State.CRAWL and _pain_cooldown <= 0.0:
		# Crawling wounded moan as they drag themselves away.
		_pain_cooldown = _rng.randf_range(3.5, 6.5)
		vocal(&"death_groan", -9.0)
	_update_flash(delta)
	_update_burn(delta)
	_update_agony(delta)
	_update_bleeders(delta)
	if bleed_dps > 0.0:
		health -= bleed_dps * delta
		_drip_dist += global_position.distance_to(_last_pos)
		if _drip_dist > 0.7:
			_drip_dist = 0.0
			if state == State.CRAWL:
				# Dragging himself along: wiped across the ground behind him.
				var back: Vector3 = _last_drip - global_position
				Gore.smear(global_position + Vector3.UP * 0.01, Vector3.UP, back, 0.75, 0.3)
			else:
				Gore.drip(body.chest_position() + Vector3.DOWN * 0.25, 0.01 + 0.0012 * bleed_dps)
			_last_drip = global_position
		if health <= 0.0:
			die(last_hit, &"stomach", &"bleed")
			if last_hit:
				EventBus.target_hit.emit(&"kill", last_hit)
			return
	_last_pos = global_position
	suppression = maxf(0.0, suppression - delta * 0.22)
	_update_morale(delta)
	_perceive -= delta
	if _perceive <= 0.0:
		_perceive = 0.15
		_update_perception(0.15)
	if _update_launch(delta):
		# Up in the air or finding his feet: no thinking, no shooting.
		_move(delta)
		return
	if melee and melee.update_vault(delta):
		return
	_think -= delta
	if _think <= 0.0:
		_think = _rng.randf_range(0.35, 0.7)
		_decide()
	_act(delta)
	_move(delta)
	if _hunting() and boss == null and squad.hunt.stuck_after > 0.0:
		_check_stuck(delta)


## Hunting and getting nowhere (caught on something, or thrown where
## there's no way back): after `stuck_after` the squad moves him to a spawn
## point out of the operative's sight.
func _check_stuck(delta: float) -> void:
	_stuck_check -= delta
	if _stuck_check > 0.0:
		return
	_stuck_check = 1.0
	var moved: float = global_position.distance_to(_stuck_from) if _stuck_from != Vector3.INF else 99.0
	_stuck_from = global_position
	var wants: bool = state in [State.ALERT, State.COMBAT] and not sees_player and not launched \
			and _move_target != Vector3.INF and global_position.distance_to(_move_target) > 2.5
	if wants and moved < 0.5:
		_stuck_for += 1.0
	else:
		_stuck_for = 0.0
	if _stuck_for >= squad.hunt.stuck_after:
		_stuck_for = 0.0
		squad.unstick(self)


func _update_perception(dt: float) -> void:
	var p: Player = squad.player() if squad else null
	sees_player = false
	if p == null:
		return
	var eye: Vector3 = body.head_position()
	var target: Vector3 = p.camera().global_position - Vector3.UP * 0.35
	var to: Vector3 = target - eye
	var dist: float = to.length()
	if dist > config.sight_range:
		_unseen_for += dt
		return
	var fwd: Vector3 = global_basis.z
	var flat: Vector3 = Vector3(to.x, 0, to.z).normalized()
	var in_fov: bool = fwd.angle_to(flat) < deg_to_rad(config.sight_fov_deg) * 0.5 or dist < 4.0 or awareness >= 1.0
	# A thermoptic shroud (TC-4) hides the operative unless he's on top of you.
	if in_fov and not p.body.hidden_at(dist):
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, target, LOS_MASK)
		sees_player = get_world_3d().direct_space_state.intersect_ray(q).is_empty()
	if sees_player:
		_unseen_for = 0.0
		_seen_for += dt
		last_known = p.global_position
		# A bigger, hotter body is spotted faster (silhouette × signature, docs/design.md §3.6).
		var rate: float = (3.0 if dist < 12.0 else 1.4) * (2.0 if p.velocity.length() > 7.0 else 1.0) * p.body.detection_scale()
		awareness = minf(awareness + rate * dt, 1.0)
		if awareness >= 1.0 and state in [State.IDLE, State.ALERT] and not passive:
			_enter(State.COMBAT)
			if squad:
				squad.report_contact(self, p.global_position)
		# The augment up close is terrifying.
		if dist < 5.0:
			morale -= 0.06 * dt * (1.0 - config.courage * 0.5)
	else:
		_seen_for = 0.0
		_unseen_for += dt
		# Footsteps: heard within footstep_hearing × how much noise he makes.
		var heard_at: float = config.footstep_hearing * p.noise_level()
		if heard_at > 0.5 and global_position.distance_to(p.global_position) < heard_at:
			awareness = minf(awareness + 0.9 * dt, 1.0)
			last_known = p.global_position
			if state == State.IDLE and awareness > 0.3:
				_enter(State.ALERT)
		elif state == State.IDLE:
			awareness = maxf(0.0, awareness - dt * 0.1)


func _update_morale(delta: float) -> void:
	if boss:
		morale = 1.0
		return
	if state in [State.SURRENDER, State.CRAWL, State.DEAD]:
		return
	var calm: bool = suppression < 0.2 and not sees_player
	morale += delta * ((0.02 if calm else 0.0) + (0.03 if squad and squad.officer_near(self) else 0.0))
	morale -= delta * 0.04 * suppression
	morale = clampf(morale, 0.0, 1.0)
	if morale < 0.18 and state == State.COMBAT and not passive:
		_break()
	elif state in [State.FLEE, State.COWER, State.BLIND] and has_gun:
		if morale > 0.45 and _state_time > 6.0:
			_enter(State.COMBAT)
		elif squad and squad.cornered() and _state_time > squad.hunt.cornered_after:
			# The last of them: nowhere left to run, so he comes back.
			morale = maxf(morale, 0.35)
			_enter(State.COMBAT)


func _break() -> void:
	var p: Player = squad.player() if squad else null
	var d: float = global_position.distance_to(p.global_position) if p else 99.0
	var r: float = _rng.randf()
	if not has_gun or (d < 9.0 and r < 0.5):
		_enter(State.SURRENDER)
	elif _cover_point != Vector3.INF and global_position.distance_to(_cover_point) < 1.0 and r < 0.6:
		_enter(State.BLIND if r < 0.35 and melee == null else State.COWER)
	else:
		_enter(State.FLEE)


func _enter(s: State) -> void:
	if state == State.DEAD:
		return
	if s == state:
		return
	var prev: State = state
	state = s
	_state_time = 0.0
	if melee and s != State.COMBAT:
		melee.reset()
	match s:
		State.COMBAT:
			_tactic_time = 0.0
			if prev == State.IDLE or prev == State.ALERT:
				# A man with a blade doesn't shout "shoot him".
				_callout(&"advance" if melee else &"contact")
		State.FLEE:
			_release_token()
			body.set_stance(&"flee")
			_callout(&"flee")
			if squad:
				squad.rally(self)
			_pick_flee_point()
		State.SURRENDER:
			_release_token()
			if body.gun:
				has_gun = false
				body.drop_gun(global_basis.z * 1.5 + Vector3.UP)
			body.set_stance(&"surrender")
			remove_from_group(&"enemies")
			_callout(&"surrender", true)
		State.COWER:
			_release_token()
			body.set_stance(&"cower")
			_callout(&"cower")
		State.BLIND:
			body.set_stance(&"blind_fire")
		State.CRAWL:
			_release_token()
			has_gun = false
			if body.gun:
				body.drop_gun(Vector3.UP)
			body.set_stance(&"crawl")
			remove_from_group(&"enemies")
			_pick_flee_point()
		State.GUT:
			_release_token()
			body.set_stance(&"gut")
			_callout(&"gut", true)
		State.DEAD:
			pass
		_:
			pass


func _decide() -> void:
	match state:
		State.IDLE:
			body.set_stance(&"idle")
		State.ALERT:
			if passive:
				body.set_stance(&"loco")
				return
			# Hunting (wave modes): run where the squad says he is, never
			# stand down (docs/design.md §5.6a).
			var hunting: bool = _hunting()
			if hunting and (last_known == Vector3.INF or global_position.distance_to(last_known) <= 2.0):
				last_known = squad.search_point(self)
			var far: bool = last_known != Vector3.INF and global_position.distance_to(last_known) > (squad.hunt.run_beyond if hunting else INF)
			body.set_stance(&"run" if far and not limping else &"loco")
			if last_known != Vector3.INF and global_position.distance_to(last_known) > 2.0:
				_go(last_known)
			elif _state_time > 6.0 and not hunting:
				_enter(State.IDLE)
		State.GUT:
			if _state_time > 3.5 and health > config.health * 0.3 and has_gun and not passive:
				_enter(State.COMBAT)
		State.FLEE:
			if passive:
				body.set_stance(&"cower")
				return
			if agony > 0.0:
				pass  # running blind (_update_agony picks where)
			elif _move_target == Vector3.INF or global_position.distance_to(_move_target) < 1.5:
				_pick_flee_point()
		State.CRAWL:
			if not passive and (_move_target == Vector3.INF or global_position.distance_to(_move_target) < 1.0):
				_pick_flee_point()
		State.COMBAT:
			if boss and not passive:
				boss.decide()
			elif melee and not passive:
				if not has_gun:
					_enter(State.FLEE)
				else:
					melee.decide()
			else:
				_decide_combat()
		_:
			pass


func _decide_combat() -> void:
	if passive:
		body.set_stance(&"loco")
		tactic = Tactic.HOLD
		return
	var p: Player = squad.player() if squad else null
	if p == null:
		return
	if not has_gun:
		_enter(State.FLEE)
		return
	var d: float = global_position.distance_to(p.global_position)
	_tactic_time += _think
	_role_time += _think
	var hunting: bool = _hunting()
	if sees_player:
		_said_suppress = false
	# Flanking: run round to his side while the pinners hold him.
	if squad_role == Squad.Role.FLANK and hunting:
		var there: bool = flank_target == Vector3.INF or global_position.distance_to(flank_target) < 1.5
		if there or (sees_player and d < 9.0) or _role_time > squad.hunt.flank_timeout:
			flank_done_at = squad.clock
			set_squad_role(Squad.Role.PUSH)
			_cover_point = Vector3.INF
			tactic = Tactic.HOLD
		else:
			tactic = Tactic.MOVE
			_cover_point = Vector3.INF
			_go(flank_target)
			return
	# Lost him: go look where he was (hunting: and keep looking).
	if _unseen_for > 4.0 and last_known != Vector3.INF:
		tactic = Tactic.MOVE
		if hunting and global_position.distance_to(last_known) < 2.5:
			last_known = squad.search_point(self)
		_go(last_known)
		if not _said_lost:
			_said_lost = true
			_callout(&"lost")
		return
	if sees_player:
		_said_lost = false
	if config.aggressive:
		if d > 7.0 or not sees_player:
			if tactic != Tactic.ADVANCE and _rng.randf() < 0.35:
				_callout(&"advance")
			tactic = Tactic.ADVANCE
			_go(p.global_position + (global_position - p.global_position).normalized() * 4.5)
		else:
			tactic = Tactic.HOLD
			_stop()
		return
	var in_cover: bool = _cover_point != Vector3.INF and global_position.distance_to(_cover_point) < 0.9
	_in_cover_for = _in_cover_for + _think if in_cover else 0.0
	if tactic == Tactic.MOVE and _move_target != Vector3.INF and global_position.distance_to(_move_target) > 0.9:
		return
	# Pushing: don't sit in one spot, move up cover by cover.
	if in_cover and hunting and squad_role == Squad.Role.PUSH and _in_cover_for > squad.hunt.push_after \
			and suppression < 0.5 and _reloading <= 0.0:
		var nearer: Vector3 = squad.find_cover_nearer(self, p.global_position, squad.hunt.push_step)
		_in_cover_for = 0.0
		if nearer != Vector3.INF:
			_cover_point = nearer
			tactic = Tactic.MOVE
			_go(nearer)
			if _rng.randf() < 0.4:
				_callout(&"advance")
			return
	if in_cover:
		_stop()
		if tactic != Tactic.HIDE and tactic != Tactic.PEEK:
			tactic = Tactic.HIDE
			_tactic_time = 0.0
			_tactic_len = _rng.randf_range(1.0, 2.5)
		if _tactic_time > _tactic_len:
			_tactic_time = 0.0
			var pinning: bool = squad_role == Squad.Role.PIN
			if tactic == Tactic.HIDE and suppression < (0.75 if pinning else 0.6) and _reloading <= 0.0:
				tactic = Tactic.PEEK
				_tactic_len = _rng.randf_range(1.8, 3.8) * (1.5 if pinning else 1.0)
			else:
				tactic = Tactic.HIDE
				_tactic_len = _rng.randf_range(1.2, 3.0) * (1.0 + suppression * 1.5) * (0.6 if pinning else 1.0)
				if _rng.randf() < 0.2:
					_cover_point = Vector3.INF  # move on to another spot next time
		# Cover no longer between us: find another.
		if squad and not squad.cover_hides(_cover_point, p):
			_cover_point = Vector3.INF
		return
	# Out of cover: get to some if under fire or within his reach.
	if squad and (suppression > 0.25 or d < config.max_range):
		var c: Vector3 = squad.find_cover(self, p.global_position)
		if c != Vector3.INF:
			_cover_point = c
			tactic = Tactic.MOVE
			_go(c)
			return
	if d > config.preferred_range * 1.4 or not sees_player:
		tactic = Tactic.ADVANCE
		_go(p.global_position)
	else:
		tactic = Tactic.HOLD
		_stop()


func _act(delta: float) -> void:
	var p: Player = squad.player() if squad else null
	_reloading = maxf(0.0, _reloading - delta)
	_shot_timer -= delta
	var aiming: bool = false
	if boss and state == State.COMBAT and not passive:
		boss.act(delta)
		return
	if melee and state == State.COMBAT and not passive:
		melee.act(delta)
		return
	match state:
		State.COMBAT:
			match tactic:
				Tactic.HIDE:
					body.set_stance(&"cover")
				Tactic.PEEK:
					body.set_stance(&"crouch_aim" if suppression < 0.3 else &"cover")
					aiming = true
				Tactic.MOVE, Tactic.ADVANCE:
					var fast: bool = not sees_player or global_position.distance_to(_move_target) > 8.0
					body.set_stance(&"run" if fast and not limping else &"loco")
					aiming = not fast
				_:
					body.set_stance(&"crouch_aim" if suppression > 0.45 else &"loco")
					aiming = true
			if passive:
				aiming = sees_player
		State.BLIND:
			aiming = false
			if p and _shot_timer <= 0.0 and has_gun:
				_blind_burst(p)
		_:
			pass
	# Look/aim at the player (or the last place he was).
	var look_at_pos: Vector3 = Vector3.INF
	if p and (sees_player or state == State.COMBAT):
		look_at_pos = p.camera().global_position - Vector3.UP * 0.3 if sees_player else last_known + Vector3.UP * 1.3
	if passive and p and state == State.IDLE:
		look_at_pos = p.camera().global_position
	if look_at_pos != Vector3.INF and state in [State.COMBAT, State.ALERT, State.GUT, State.SURRENDER, State.IDLE]:
		var to: Vector3 = look_at_pos - body.chest_position()
		var want_yaw: float = atan2(to.x, to.z)
		var rel: float = wrapf(want_yaw - _yaw, -PI, PI)
		var moving: bool = velocity.length() > 0.5
		if not moving or tactic != Tactic.MOVE:
			_turn_toward(want_yaw, delta)
			rel = wrapf(want_yaw - _yaw, -PI, PI)
		var pitch: float = atan2(to.y, Vector2(to.x, to.z).length())
		body.set_aim(rel, pitch, 1.0 if aiming else 0.35)
	else:
		body.set_aim(0.0, 0.0, 0.0)
	if aiming and p and state == State.COMBAT and not passive and has_gun:
		_try_fire(p, delta)


func _try_fire(p: Player, _delta: float) -> void:
	if _reloading > 0.0:
		return
	if ammo <= 0:
		_start_reload()
		return
	# A pinner keeps firing where he went for a while: rounds into his
	# cover keep his head down while the flankers go round.
	var pin_fire: bool = false
	if not sees_player:
		if squad_role != Squad.Role.PIN or not _hunting() or last_known == Vector3.INF \
				or _unseen_for > squad.hunt.pin_fire_time or _rounds_this_engagement == 0:
			return
		pin_fire = true
	elif _seen_for < config.reaction_time:
		return
	if not _has_token:
		_has_token = squad.request_token(self) if squad else true
		if not _has_token:
			return
	if _shot_timer > 0.0:
		return
	if _burst_left <= 0:
		_burst_left = _rng.randi_range(config.burst_min, config.burst_max)
	if pin_fire:
		if not _said_suppress:
			_said_suppress = true
			_callout(&"suppress")
		_fire_at(last_known + Vector3.UP * _rng.randf_range(0.9, 1.7), _aim_error(p) * squad.hunt.pin_error_scale)
	else:
		_fire_at(p.camera().global_position - Vector3.UP * _rng.randf_range(0.15, 0.55), _aim_error(p))
	_burst_left -= 1
	_shot_timer = config.fire_interval
	if _burst_left <= 0:
		_shot_timer = config.burst_pause * _rng.randf_range(0.7, 1.4) * (1.0 + suppression)
		if squad and _rng.randf() < 0.4:
			_release_token()


func _aim_error(p: Player) -> float:
	var settle: float = lerpf(1.7, 1.0, clampf(_seen_for / maxf(config.aim_settle_time, 0.01), 0.0, 1.0))
	var e: float = config.aim_error_deg * settle * (1.0 + 2.2 * suppression) * (1.0 + p.velocity.length() / 6.0)
	# A bigger silhouette is easier to hit: the same aim error covers less of it.
	e /= maxf(p.body.stat(&"profile"), 0.3)
	if arm_hurt:
		e *= 2.2
	if limping:
		e *= 1.2
	# The first rounds of an engagement go wide: a warning the player can read.
	if _rounds_this_engagement < 3:
		e *= 2.4
	return e


func _fire_at(target: Vector3, error_deg: float) -> void:
	var m: Transform3D = body.muzzle_transform()
	var dir: Vector3 = (target - m.origin).normalized()
	var w: WeaponData = config.weapon
	var volley: int = 0
	var tracer: bool = _rounds_this_engagement % 2 == 0
	for i: int in maxi(w.pellets, 1):
		var d: Vector3 = Ballistics.random_in_cone(dir, error_deg, _rng)
		if w.pellets > 1:
			d = Ballistics.pattern_dir(d, w.pattern_deg, i, w.pellets, _rng.randf() * TAU, _rng)
		var id: int = Ballistics.fire(w, m.origin, d, self, m.origin if tracer and i == 0 else Vector3.INF, volley)
		if volley == 0:
			volley = id
	ammo -= 1
	_rounds_this_engagement += 1
	Sfx.play_at(StringName("enemy_" + w.sound_prefix + "shot"), m.origin, w.shot_volume_db, 0.05)
	_show_flash(m)
	body.flinch(-global_basis.z, 0.25, false)
	EventBus.shot_fired.emit(self, m.origin, dir)


func _blind_burst(p: Player) -> void:
	if ammo <= 0:
		_start_reload()
		return
	_fire_at(p.global_position + Vector3(_rng.randf_range(-3, 3), _rng.randf_range(0.5, 2.5), _rng.randf_range(-3, 3)), 6.0)
	_shot_timer = config.fire_interval * 1.3
	if _rng.randf() < 0.15:
		_shot_timer = 1.2


func _start_reload() -> void:
	if _reloading > 0.0:
		return
	_reloading = config.reload_time
	ammo = config.magazine
	_burst_left = 0
	body.play_reload()
	Sfx.play_at(&"enemy_reload", body.chest_position(), -6.0)
	if _rng.randf() < 0.5:
		_callout(&"reload")
	_release_token()


func _release_token() -> void:
	if _has_token and squad:
		squad.release_token(self)
	_has_token = false


# ------------------------------------------------------------------ movement

func _go(target: Vector3) -> void:
	_move_target = target
	nav.target_position = target


func _stop() -> void:
	_move_target = Vector3.INF


func _pick_flee_point() -> void:
	var p: Player = squad.player() if squad else null
	var away: Vector3 = (global_position - (p.global_position if p else global_position + Vector3.FORWARD)).normalized()
	_go(global_position + away.rotated(Vector3.UP, _rng.randf_range(-0.7, 0.7)) * _rng.randf_range(6.0, 12.0))


func _move(delta: float) -> void:
	var speed: float = 0.0
	var run: bool = false
	if not passive and _move_target != Vector3.INF:
		match state:
			State.COMBAT, State.ALERT:
				if boss:
					run = true
					speed = boss.speed()
				elif melee:
					run = true
					speed = melee.speed() * (1.0 if state == State.COMBAT else 0.55)
				else:
					run = body.stance == &"run"
					speed = config.run_speed if run else config.walk_speed
			State.FLEE:
				speed = config.run_speed * 1.1
				run = true
			State.CRAWL:
				speed = 0.45
			_:
				speed = 0.0
		if limping:
			speed *= 0.5
	var want: Vector3 = Vector3.ZERO
	if speed > 0.0 and not nav.is_navigation_finished():
		var next: Vector3 = nav.get_next_path_position()
		var to: Vector3 = next - global_position
		to.y = 0.0
		if to.length() > 0.05:
			want = to.normalized() * speed
		if global_position.distance_to(_move_target) < nav.target_desired_distance + 0.2:
			_move_target = Vector3.INF
	elif speed > 0.0 and nav.get_navigation_map().is_valid() == false:
		var to2: Vector3 = _move_target - global_position
		to2.y = 0.0
		if to2.length() > 0.8:
			want = to2.normalized() * speed
	if melee and state == State.COMBAT and not passive:
		# Straight over low walls, the lunge, standing still for the chop.
		var mv: Vector3 = melee.want_velocity()
		if mv != Vector3.INF:
			want = mv
	if boss and state == State.COMBAT and not passive:
		var bv: Vector3 = boss.want_velocity()
		if bv != Vector3.INF:
			want = bv
	var horizontal: Vector3 = Vector3(velocity.x, 0, velocity.z).move_toward(want, (20.0 if melee else 14.0) * delta)
	if _knock.length_squared() > 0.01:
		# Shoved: the push wins over his own legs until it dies away.
		horizontal = _knock
		# In the air nothing but drag slows him.
		_knock = _knock.move_toward(Vector3.ZERO, KNOCK_DECAY * (0.1 if _launch_air else 1.0) * delta)
	var g: float = _launch_gravity if _launch_air else GRAVITY
	var vy: float = velocity.y - g * delta if (not is_on_floor() or velocity.y > 0.0) else -0.5
	velocity = Vector3(horizontal.x, vy, horizontal.z)
	move_and_slide()
	if launched:
		body.set_motion(Vector3.ZERO)
		return
	if horizontal.length() > 0.3 and (run or state in [State.FLEE, State.CRAWL] or not sees_player) and not (boss and boss.is_busy()):
		_turn_toward(atan2(horizontal.x, horizontal.z), delta)
	var local: Vector3 = global_basis.inverse() * horizontal
	body.set_motion(local)


func _turn_toward(yaw: float, delta: float) -> void:
	_yaw = rotate_toward(_yaw, yaw, deg_to_rad(config.turn_speed_deg) * delta)
	rotation.y = _yaw


## Faces `yaw` at once (spawning).
func face(yaw: float) -> void:
	_yaw = yaw
	rotation.y = yaw


# ------------------------------------------------------------------ fire, bleeding, flash

func _update_burn(delta: float) -> void:
	if burn_left <= 0.0:
		return
	burn_left -= delta
	health -= burn_dps * delta
	charred = minf(charred + delta * 0.12, 1.0)
	body.set_char(charred)
	morale -= delta * 0.15
	if health <= 0.0:
		burn_left = 0.0
		die(last_hit, &"chest", &"burn")
		if last_hit:
			EventBus.target_hit.emit(&"kill", last_hit)
	elif state == State.COMBAT and morale < 0.4:
		_enter(State.FLEE)


## Beats per second of a man bleeding out, how fast the pressure falls
## (alive / heart stopped), and how long a stump goes on.
const BLEED_HEART_HZ: float = 2.3
const BLEED_PRESSURE_TIME: float = 2.2
const BLEED_PRESSURE_TIME_DEAD: float = 0.55
const BLEED_TIME: float = 5.0


func _update_bleeders(delta: float) -> void:
	if _bleeders.is_empty():
		return
	var still: Array[Bleeder] = []
	var floor_y: float = global_position.y
	for b: Bleeder in _bleeders:
		b.age += delta
		var t: Transform3D = body.stump(b.part)
		var pressure: float = b.strength * exp(-b.age / (BLEED_PRESSURE_TIME if alive else BLEED_PRESSURE_TIME_DEAD))
		# Systole: the first third of each beat pushes; between beats it only runs.
		var beat: float = fposmod(b.age * BLEED_HEART_HZ, 1.0)
		var push: float = sin(beat / 0.35 * PI) if beat < 0.35 else 0.0
		var flow: float = pressure * push
		if flow > 0.04:
			b.owed += delta * (20.0 + 150.0 * flow) * Gore.config.blood_amount
			var n: int = floori(b.owed)
			if n > 0:
				b.owed -= float(n)
				b.count += n
				# One in six is traced: they mark where the stream comes down.
				Gore.spurt(t.origin, t.basis.y, 1.0 + 3.8 * flow, n, 1 if b.count % 6 < n else 0, velocity, floor_y)
		elif b.age < BLEED_TIME:
			b.owed += delta * 2.5 * b.strength * Gore.config.blood_amount
			if b.owed >= 1.0:
				b.owed -= 1.0
				Gore.drip(t.origin, 0.012)
		if b.age < BLEED_TIME:
			still.append(b)
	_bleeders = still


func _show_flash(m: Transform3D) -> void:
	_flash.global_transform = Transform3D(m.basis.orthonormalized().rotated(m.basis.x.normalized(), _rng.randf() * TAU), m.origin)
	_flash.scale = Vector3.ONE * _rng.randf_range(0.8, 1.2) * config.weapon.flash_scale
	_flash.visible = true
	_flash_time = 0.04


func _update_flash(delta: float) -> void:
	if _flash_time > 0.0:
		_flash_time -= delta
		if _flash_time <= 0.0:
			_flash.visible = false


func _build_flash() -> void:
	_flash = MeshInstance3D.new()
	_flash.top_level = true
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# Two crossed quads along +X plus a front star.
	for k: int in 2:
		var a: float = PI * 0.5 * k
		var u: Vector3 = Vector3(0, cos(a), sin(a)) * 0.07
		st.add_vertex(-u)
		st.add_vertex(u)
		st.add_vertex(u + Vector3(0.22, 0, 0))
		st.add_vertex(-u)
		st.add_vertex(u + Vector3(0.22, 0, 0))
		st.add_vertex(-u + Vector3(0.22, 0, 0))
	_flash.mesh = st.commit()
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.albedo_color = Color(2.6, 1.7, 0.8)
	mat.albedo_texture = preload("res://assets/gore/mist.png")
	_flash.material_override = mat
	_flash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_flash.visible = false
	add_child(_flash)


## A callout for `situation` (VoiceLines.LINES). Through the squad, which
## keeps them from talking over each other unless `force`.
func _callout(situation: StringName, force: bool = false) -> void:
	if squad:
		squad.callout(self, situation, force)
	else:
		speak(situation)


## Says one of the lines for `situation` (`index` < 0: a random one) in his
## voice, from his head, with the subtitle. Returns the line, or "" if he
## can't speak (dead, or no such line).
func speak(situation: StringName, index: int = -1) -> String:
	var lines: Array = VoiceLines.LINES.get(situation, [])
	if lines.is_empty() or not alive:
		return ""
	var i: int = index if index >= 0 and index < lines.size() else _rng.randi() % lines.size()
	var text: String = lines[i]
	var stream: AudioStream = load(VoiceLines.path(voice, situation, i)) as AudioStream if voice != &"" else null
	if stream and mouth:
		mouth.stream = stream
		mouth.volume_db = 3.0
		mouth.pitch_scale = Sfx.world_pitch(0.02)
		mouth.play()
	EventBus.callout.emit(config.callsign, text, global_position)
	return text


## A wordless sound from his mouth (pain, dying): one of Sfx's banks.
func vocal(bank: StringName, volume_db: float = 0.0, pitch_rand: float = 0.12) -> void:
	var streams: Array = Sfx.bank(bank)
	if streams.is_empty() or mouth == null:
		return
	mouth.stream = streams[_rng.randi() % streams.size()]
	mouth.volume_db = volume_db
	mouth.pitch_scale = Sfx.world_pitch(pitch_rand)
	mouth.play()


func _build_mouth() -> void:
	if voice == &"":
		voice = VoiceLines.VOICES[_rng.randi() % VoiceLines.VOICES.size()]
	mouth = AudioStreamPlayer3D.new()
	mouth.name = "Mouth"
	mouth.bus = &"SFX"
	mouth.unit_size = MOUTH_UNIT_SIZE
	mouth.max_distance = 90.0
	mouth.attenuation_filter_cutoff_hz = 12000.0
	body.head_anchor().add_child(mouth)
	mouth.position = Vector3(0, 0.06, 0.08)
