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

var squad: Squad
var body: EnemyBody
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
	cap.radius = 0.3
	cap.height = 1.75 * config.body_scale
	cs.shape = cap
	cs.position = Vector3(0, cap.height * 0.5, 0)
	add_child(cs)
	body = EnemyBody.new()
	body.name = "Body"
	body.setup(self, config, null, look_seed)
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
	var entry_r: float = clampf(0.007 + dep * 0.000006, 0.006, 0.02)
	body.add_wound(zone, hit.point, entry_r, false)
	if hit.result == BallisticHit.Result.PENETRATED:
		body.add_wound(zone, hit.exit_point, clampf(0.012 + hit.energy_out * 0.000004, 0.012, 0.045), true)
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
	health -= dmg
	if hit.result == BallisticHit.Result.PENETRATED:
		bleed_dps = minf(bleed_dps + 1.5, 6.0)
	body.flinch(hit.direction, clampf(hit.damage.impulse / 3.0 * TimeControl.impact_multiplier(), 0.3, 3.5), head)
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
		_react(zone, dmg, hit)
	EventBus.target_hit.emit(kind, hit)
	EventBus.damage_applied.emit(hit.damage, self)


## Shoved by the operative (a slide into him): flies back along `push`,
## staggers, gets hurt a little and badly rattled. Dead men don't get shoved
## here (their ragdoll takes hits through push_bone).
func knock_back(push: Vector3, from: Node, damage: float, morale_loss: float) -> void:
	if not alive:
		return
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


## Seized by the mesh arm: he goes limp in its grip (a ragdoll, still
## alive), drops his gun and leaves the fight. Returns false if he can't be
## taken (dead, already held).
func seize(by: Node) -> bool:
	if not alive or held:
		return false
	held = true
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
	if not Gore.is_maximum() or body.gibbed:
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
func sever(seg: StringName, velocity_out: Vector3, destroy: bool, hit: BallisticHit = null, zone: StringName = &"chest") -> bool:
	var group: Array[StringName] = body.attached(seg)
	if not body.sever(seg, velocity_out, destroy):
		return false
	_bleeders.append(Bleeder.new(seg))
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
	bleed_dps = maxf(bleed_dps, 14.0 if seg.begins_with("upper_arm") or seg.begins_with("thigh") else 9.0)
	return true


## Maximum gore: enough into the torso in one volley (or into a corpse over
## time) blows the whole body apart. Returns whether it did.
func _try_burst(zone: StringName, hit: BallisticHit) -> bool:
	if not Gore.is_maximum() or body.gibbed or not zone in Dismemberment.TORSO:
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
	if body.gibbed:
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
		var heavy: float = clampf(hit.damage.impulse, 4.0, 40.0)
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
	_state_time += delta
	_pain_cooldown -= delta
	if state == State.CRAWL and _pain_cooldown <= 0.0:
		# Crawling wounded moan as they drag themselves away.
		_pain_cooldown = _rng.randf_range(3.5, 6.5)
		vocal(&"death_groan", -9.0)
	_update_flash(delta)
	_update_burn(delta)
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
	_think -= delta
	if _think <= 0.0:
		_think = _rng.randf_range(0.35, 0.7)
		_decide()
	_act(delta)
	_move(delta)


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
	if state in [State.SURRENDER, State.CRAWL, State.DEAD]:
		return
	var calm: bool = suppression < 0.2 and not sees_player
	morale += delta * ((0.02 if calm else 0.0) + (0.03 if squad and squad.officer_near(self) else 0.0))
	morale -= delta * 0.04 * suppression
	morale = clampf(morale, 0.0, 1.0)
	if morale < 0.18 and state == State.COMBAT and not passive:
		_break()
	elif state in [State.FLEE, State.COWER, State.BLIND] and morale > 0.45 and _state_time > 6.0 and has_gun:
		_enter(State.COMBAT)


func _break() -> void:
	var p: Player = squad.player() if squad else null
	var d: float = global_position.distance_to(p.global_position) if p else 99.0
	var r: float = _rng.randf()
	if not has_gun or (d < 9.0 and r < 0.5):
		_enter(State.SURRENDER)
	elif _cover_point != Vector3.INF and global_position.distance_to(_cover_point) < 1.0 and r < 0.6:
		_enter(State.BLIND if r < 0.35 else State.COWER)
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
	match s:
		State.COMBAT:
			_tactic_time = 0.0
			if prev == State.IDLE or prev == State.ALERT:
				_callout(&"contact")
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
			body.set_stance(&"loco")
			if last_known != Vector3.INF and global_position.distance_to(last_known) > 2.0:
				_go(last_known)
			elif _state_time > 6.0:
				_enter(State.IDLE)
		State.GUT:
			if _state_time > 3.5 and health > config.health * 0.3 and has_gun and not passive:
				_enter(State.COMBAT)
		State.FLEE:
			if passive:
				body.set_stance(&"cower")
				return
			if _move_target == Vector3.INF or global_position.distance_to(_move_target) < 1.5:
				_pick_flee_point()
		State.CRAWL:
			if not passive and (_move_target == Vector3.INF or global_position.distance_to(_move_target) < 1.0):
				_pick_flee_point()
		State.COMBAT:
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
	# Lost him: go look where he was.
	if _unseen_for > 4.0 and last_known != Vector3.INF:
		tactic = Tactic.MOVE
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
	if tactic == Tactic.MOVE and _move_target != Vector3.INF and global_position.distance_to(_move_target) > 0.9:
		return
	if in_cover:
		_stop()
		if tactic != Tactic.HIDE and tactic != Tactic.PEEK:
			tactic = Tactic.HIDE
			_tactic_time = 0.0
			_tactic_len = _rng.randf_range(1.0, 2.5)
		if _tactic_time > _tactic_len:
			_tactic_time = 0.0
			if tactic == Tactic.HIDE and suppression < 0.6 and _reloading <= 0.0:
				tactic = Tactic.PEEK
				_tactic_len = _rng.randf_range(1.8, 3.8)
			else:
				tactic = Tactic.HIDE
				_tactic_len = _rng.randf_range(1.2, 3.0) * (1.0 + suppression * 1.5)
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
	if not sees_player or _seen_for < config.reaction_time:
		return
	if not _has_token:
		_has_token = squad.request_token(self) if squad else true
		if not _has_token:
			return
	if _shot_timer > 0.0:
		return
	if _burst_left <= 0:
		_burst_left = _rng.randi_range(config.burst_min, config.burst_max)
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
	var horizontal: Vector3 = Vector3(velocity.x, 0, velocity.z).move_toward(want, 14.0 * delta)
	if _knock.length_squared() > 0.01:
		# Shoved: the push wins over his own legs until it dies away.
		horizontal = _knock
		_knock = _knock.move_toward(Vector3.ZERO, KNOCK_DECAY * delta)
	var vy: float = velocity.y - 20.0 * delta if (not is_on_floor() or velocity.y > 0.0) else -0.5
	velocity = Vector3(horizontal.x, vy, horizontal.z)
	move_and_slide()
	if horizontal.length() > 0.3 and (run or state in [State.FLEE, State.CRAWL] or not sees_player):
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
