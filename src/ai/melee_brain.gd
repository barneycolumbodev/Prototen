class_name MeleeBrain
extends RefCounted
## How a man with a blade fights (the Hatchet Man, docs/design.md §8.8):
## "Melee. Cleaver or hatchet, sprints between cover, vaults low walls,
## comes from the side. Has to be killed or dodged, not out-shot from cover."
##
## - Approach: out of `charge_range` he sprints from one cover to the next,
##   each one nearer the operative and out of his sight, toward a point off
##   the operative's side (`flank_angle_deg` from where he's looking), and
##   waits a moment behind each (`cover_pause`). If he's being looked at, he
##   keeps sweeping wide on the side he's already on.
## - Charge: inside `charge_range` he runs straight in, weaving when he's
##   looked at. Over low walls he goes straight over (a vault) instead of
##   round by the nav path.
## - The chop: within `melee_commit_range` the blade goes up high (the
##   tell), he lunges and turns after the operative at `melee_track_deg`, and
##   the blow lands `melee_windup` s later if the operative is still within
##   `melee_reach` and `melee_arc_deg` in front of him. A sidestep, a slide or
##   a jump at the right moment leaves him swinging at air. A solid hit
##   (`melee_interrupt`) during the windup breaks it off.
## - Vault: anything from 0.3 m up to `vault_height` across his path, with
##   room to land beyond it, he goes over in `vault_time`.
## Tuning: data/enemies/hatchet_man.tres (EnemyConfig, Melee group).

enum Phase { APPROACH, HOLD, CHARGE, WINDUP, RECOVER, VAULT }

var e: Enemy
var cfg: EnemyConfig
var phase: Phase = Phase.APPROACH
## +1: comes round the operative's right, -1: his left.
var side: float = 1.0
## Counts (tests, the range readout).
var strikes: int = 0
var hits: int = 0
var whiffs: int = 0
var vaults: int = 0
## Damage the last blow did (after armour and the fan shield).
var last_damage: float = 0.0

var _t: float = 0.0
var _len: float = 0.0
var _cover: Vector3 = Vector3.INF
var _struck: bool = false
var _swished: bool = false
## Running straight at `_direct_to` (over low walls) instead of the nav path.
var _direct: bool = false
var _direct_to: Vector3 = Vector3.INF
var _probe: float = 0.0
var _watched_for: float = 0.0
var _weave: float = 0.0
var _vault_from: Vector3
var _vault_to: Vector3
var _vault_rise: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _side_picked: bool = false
var _windup_damage: float = 0.0

const LOW_PROBE: float = 0.45
const PROBE_AHEAD: float = 0.9
## How high the vault clip tucks the feet above the root (raw_assets/characters/triad/build.py).
const VAULT_TUCK: float = 0.38


func _init(enemy: Enemy) -> void:
	e = enemy
	cfg = enemy.config
	_rng.randomize()
	side = 1.0 if _rng.randf() < 0.5 else -1.0


func is_busy() -> bool:
	return phase in [Phase.WINDUP, Phase.RECOVER, Phase.VAULT]


func is_vaulting() -> bool:
	return phase == Phase.VAULT


func is_winding_up() -> bool:
	return phase == Phase.WINDUP


## Knocked out of whatever he was doing (launched, seized, fled, killed).
func reset() -> void:
	if phase == Phase.WINDUP:
		e.body.cancel_chop()
	phase = Phase.APPROACH
	_t = 0.0
	_direct = false
	_cover = Vector3.INF


## A hit: enough damage during the windup (added up: two quick pistol
## rounds, one rifle round or a shotgun blast) breaks it off and staggers him.
func on_hurt(damage: float) -> void:
	if phase != Phase.WINDUP:
		return
	_windup_damage += damage
	if _windup_damage >= cfg.melee_interrupt:
		e.body.cancel_chop()
		e.body.play_stumble()
		_enter(Phase.RECOVER, cfg.melee_recovery + 0.35)


# ------------------------------------------------------------------ decisions

## Called on the enemy's think tick while he's in COMBAT.
func decide() -> void:
	var p: Player = _player()
	if p == null or is_busy():
		return
	var to_p: Vector3 = _flat(p.global_position - e.global_position)
	var d: float = to_p.length()
	if not _side_picked:
		# Round the side he's already on.
		_side_picked = true
		var fwd: Vector3 = _flat(-p.camera().global_basis.z)
		var c: float = fwd.cross(-to_p).y
		if absf(c) > 0.01:
			side = -signf(c)
	# Lost him: run to where he was.
	if not e.sees_player and e._unseen_for > 3.0 and e.last_known != Vector3.INF:
		if e._hunting() and e.global_position.distance_to(e.last_known) < 2.5:
			# Hunting: he's not here, try where the squad says next.
			e.last_known = e.squad.search_point(e)
		e.tactic = Enemy.Tactic.MOVE
		_set_direct(false)
		e._go(e.last_known)
		if not e._said_lost:
			e._said_lost = true
			e._callout(&"lost")
		return
	if e.sees_player:
		e._said_lost = false
	if d <= cfg.charge_range:
		if phase != Phase.CHARGE:
			_enter(Phase.CHARGE, 0.0)
			if _rng.randf() < 0.6:
				e._callout(&"advance")
		e.tactic = Enemy.Tactic.ADVANCE
		var target: Vector3 = p.global_position
		if _watched_for > 0.4 and d > 4.5:
			# Looked at: weave across his line instead of running straight down it.
			var across: Vector3 = Vector3.UP.cross(to_p.normalized())
			target += across * side * sin(_weave) * 2.2
		_steer_to(target)
		return
	if phase == Phase.HOLD:
		if _t < _len:
			e._stop()
			return
		_enter(Phase.APPROACH, 0.0)
		_cover = Vector3.INF
	if phase != Phase.APPROACH:
		_enter(Phase.APPROACH, 0.0)
	e.tactic = Enemy.Tactic.MOVE
	if _cover != Vector3.INF and _flat(e.global_position - _cover).length() < 0.9:
		_enter(Phase.HOLD, _rng.randf_range(cfg.cover_pause.x, cfg.cover_pause.y) * (1.0 + e.suppression))
		_set_direct(false)
		e._stop()
		return
	if _cover == Vector3.INF or _flat(_cover - p.global_position).length() >= d - 1.0:
		_cover = _pick_cover(p, d)
	_steer_to(_cover if _cover != Vector3.INF else flank_point(p, d))


## Where he's heading round the side: off the operative's facing by the
## flank angle, on his side, nearer than he is now.
func flank_point(p: Player, d: float) -> Vector3:
	var fwd: Vector3 = _flat(-p.camera().global_basis.z).normalized()
	if fwd.length_squared() < 0.01:
		fwd = Vector3.FORWARD
	var dir: Vector3 = fwd.rotated(Vector3.UP, -side * deg_to_rad(cfg.flank_angle_deg))
	return p.global_position + dir * clampf(d * 0.55, 3.0, 12.0)


## The next cover on the way in: nearer the operative, hidden from him, not
## too far a sprint, and as close to the flank point as can be.
func _pick_cover(p: Player, d: float) -> Vector3:
	if e.squad == null:
		return Vector3.INF
	var goal: Vector3 = flank_point(p, d)
	var best: Vector3 = Vector3.INF
	var best_score: float = INF
	for c: Vector3 in e.squad.cover_points:
		var to_me: float = _flat(c - e.global_position).length()
		if to_me > 14.0 or to_me < 2.0:
			continue
		var to_p: float = _flat(c - p.global_position).length()
		if to_p > d - 2.5 or to_p < 4.0:
			continue
		var score: float = _flat(c - goal).length() + to_me * 0.3
		if score >= best_score:
			continue
		if not e.squad.cover_hides(c, p):
			continue
		best_score = score
		best = c
	return best


## Heads for `target`: straight over low walls when that's clearly shorter,
## otherwise by the nav path.
func _steer_to(target: Vector3) -> void:
	_set_direct(_straight_ok(target))
	_direct_to = target
	e._go(target)


func _set_direct(on: bool) -> void:
	_direct = on


## True if a man can run straight to `target`: nothing above vault height in
## the way, and ground all along (no water, no drop).
func _straight_ok(target: Vector3) -> bool:
	var from: Vector3 = e.global_position
	var flat: Vector3 = _flat(target - from)
	var dist: float = flat.length()
	if dist < 0.5 or absf(target.y - from.y) > 1.2:
		return false
	var space: PhysicsDirectSpaceState3D = e.get_world_3d().direct_space_state
	var h: float = cfg.vault_height + 0.25
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from + Vector3.UP * h, target + Vector3.UP * h, Ballistics.LAYER_WORLD)
	if not space.intersect_ray(q).is_empty():
		return false
	var steps: int = mini(int(dist / 1.5), 10)
	for i: int in steps:
		var at: Vector3 = from + flat * (float(i + 1) / float(steps + 1))
		var down: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(at + Vector3.UP * h, at + Vector3.DOWN * 1.0, Ballistics.LAYER_WORLD)
		if space.intersect_ray(down).is_empty():
			return false
	return true


# ------------------------------------------------------------------ every frame

## Called every physics frame while he's in COMBAT (instead of aiming and firing).
func act(delta: float) -> void:
	var p: Player = _player()
	_t += delta
	_weave += delta * 3.2
	if p:
		var watched: bool = _flat(-p.camera().global_basis.z).normalized().dot(_flat(e.global_position - p.global_position).normalized()) > cos(deg_to_rad(22.0))
		_watched_for = _watched_for + delta if watched and e.sees_player else maxf(0.0, _watched_for - delta * 2.0)
	match phase:
		Phase.WINDUP:
			_windup(p, delta)
			return
		Phase.RECOVER:
			e.body.set_stance(&"melee_ready")
			_look(p, 0.4, delta, true)
			if _t >= _len:
				_enter(Phase.CHARGE, 0.0)
				e._think = 0.0
			return
		Phase.VAULT:
			return
		Phase.HOLD:
			e.body.set_stance(&"cover")
			_look(p, 0.3, delta, false)
			return
	e.body.set_stance(&"run")
	_look(p, 0.25, delta, false)
	if p == null:
		return
	var to_p: Vector3 = _flat(p.global_position - e.global_position)
	var d: float = to_p.length()
	# The chop: close, in sight, on about the same level, nothing low between (else over it first).
	if d <= cfg.melee_commit_range and e.sees_player and absf(p.global_position.y - e.global_position.y) < 1.6 \
			and _clear_between(p):
		_start_chop()
		return
	_probe -= delta
	if _probe <= 0.0:
		_probe = 0.08
		_try_vault()


## The speed (m/s) and direction he wants this frame, or INF to leave it to
## the nav path (Enemy._move).
func want_velocity() -> Vector3:
	match phase:
		Phase.WINDUP:
			var p: Player = _player()
			if p and _flat(p.global_position - e.global_position).length() > cfg.melee_reach * 0.55 and _t < cfg.melee_windup:
				return e.global_basis.z * cfg.melee_lunge_speed
			return Vector3.ZERO
		Phase.RECOVER, Phase.HOLD, Phase.VAULT:
			return Vector3.ZERO
	if _direct and _direct_to != Vector3.INF:
		var to: Vector3 = _flat(_direct_to - e.global_position)
		if to.length() > 0.6:
			return to.normalized() * speed()
	return Vector3.INF


func speed() -> float:
	return cfg.run_speed * (0.5 if e.limping else 1.0)


func _look(p: Player, weight: float, delta: float, turn: bool) -> void:
	if p == null:
		e.body.set_aim(0.0, 0.0, 0.0)
		return
	var to: Vector3 = p.camera().global_position - e.body.chest_position()
	var want_yaw: float = atan2(to.x, to.z)
	if turn:
		e._turn_toward(want_yaw, delta)
	var rel: float = wrapf(want_yaw - e._yaw, -PI, PI)
	e.body.set_aim(rel, atan2(to.y, Vector2(to.x, to.z).length()), weight)


# ------------------------------------------------------------------ the chop

func _start_chop() -> void:
	strikes += 1
	_enter(Phase.WINDUP, 0.0)
	_struck = false
	_swished = false
	_windup_damage = 0.0
	e._stop()
	e.body.play_chop(cfg.melee_windup)
	if _rng.randf() < 0.5:
		e.vocal(&"enemy_pain", 1.0, 0.2)  # a grunt as the blade goes up


func _windup(p: Player, delta: float) -> void:
	# He turns after the operative, but only so fast: a dodge across him works.
	if p:
		var to: Vector3 = _flat(p.global_position - e.global_position)
		var want_yaw: float = atan2(to.x, to.z)
		e._yaw = rotate_toward(e._yaw, want_yaw, deg_to_rad(cfg.melee_track_deg) * delta)
		e.rotation.y = e._yaw
		e.body.set_aim(0.0, 0.0, 0.0)
	if not _swished and _t >= cfg.melee_windup * 0.78:
		_swished = true
		Sfx.play_at(&"mw7_swish", e.body.chest_position(), -2.0, 0.12)
	if not _struck and _t >= cfg.melee_windup:
		_struck = true
		_resolve(p)
	if _t >= cfg.melee_windup + cfg.melee_recovery:
		_enter(Phase.CHARGE, 0.0)
		e._think = 0.0


## The blow falls: does it land?
func _resolve(p: Player) -> void:
	last_damage = 0.0
	if p == null or p.dead or not lands_on(p):
		whiffs += 1
		return
	var dir: Vector3 = _flat(p.global_position - e.global_position).normalized()
	last_damage = p.on_melee_hit(e, cfg.melee_damage, dir, cfg.melee_push)
	hits += 1
	var at: Vector3 = p.camera().global_position - Vector3.UP * 0.35
	if last_damage > 0.0:
		Sfx.play_at(&"impact_flesh", at, 3.0, 0.1)
		Sfx.play_at(&"mw7_cut", at, -2.0, 0.1)
		p.add_shake(0.35 + cfg.melee_kick_deg * 0.06)
		for pad: int in Input.get_connected_joypads():
			Input.start_joy_vibration(pad, 0.8, 1.0, 0.22)
	else:
		Sfx.play_at(&"impact_steel", at, 0.0, 0.1)


## Nothing between his knees and the operative's (a low wall is vaulted, not chopped across).
func _clear_between(p: Player) -> bool:
	var mask: int = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(e.global_position + Vector3.UP * 0.5, p.global_position + Vector3.UP * 0.5, mask)
	return e.get_world_3d().direct_space_state.intersect_ray(q).is_empty()


## True if the operative is within reach and arc of the blade right now,
## and nothing solid is between them.
func lands_on(p: Player) -> bool:
	var to: Vector3 = _flat(p.global_position - e.global_position)
	if to.length() > cfg.melee_reach or absf(p.global_position.y - e.global_position.y) > 1.5:
		return false
	var fwd: Vector3 = _flat(e.global_basis.z).normalized()
	if to.length() > 0.4 and rad_to_deg(fwd.angle_to(to.normalized())) > cfg.melee_arc_deg * 0.5:
		return false
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(e.body.chest_position(), p.camera().global_position - Vector3.UP * 0.4, Ballistics.LAYER_WORLD)
	return e.get_world_3d().direct_space_state.intersect_ray(q).is_empty()


# ------------------------------------------------------------------ vaulting

## Something low across his path with room beyond: over it.
func _try_vault() -> void:
	if not e.is_on_floor():
		return
	# Where he wants to go (not where he's going: pressed against a wall he isn't moving).
	var v: Vector3 = Vector3.ZERO
	if _direct and _direct_to != Vector3.INF:
		v = _flat(_direct_to - e.global_position)
	elif e._move_target != Vector3.INF and not e.nav.is_navigation_finished():
		v = _flat(e.nav.get_next_path_position() - e.global_position)
	if v.length() < 0.3:
		return
	var plan: Array = vault_plan(e.global_position, v.normalized())
	if plan.is_empty():
		return
	_vault_from = e.global_position
	_vault_to = plan[0]
	_vault_rise = plan[1]
	vaults += 1
	_enter(Phase.VAULT, 0.0)
	e.velocity = Vector3.ZERO
	e._yaw = atan2(v.x, v.z)
	e.rotation.y = e._yaw
	e.body.play_vault(cfg.vault_time)
	Sfx.play_at(&"mantle", e.global_position + Vector3.UP * 0.8, -4.0, 0.1)


## [landing point, peak height of the feet over the start] for a vault from
## `from` along `dir`, or [] if there's nothing to vault or no room to land.
func vault_plan(from: Vector3, dir: Vector3) -> Array:
	var space: PhysicsDirectSpaceState3D = e.get_world_3d().direct_space_state
	var mask: int = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS
	var low: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(from + Vector3.UP * LOW_PROBE, from + Vector3.UP * LOW_PROBE + dir * PROBE_AHEAD, mask))
	if low.is_empty():
		return []
	var wall: Vector3 = low["position"]
	# Its top: straight down from above, just past the face.
	var top_ray: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(
			Vector3(wall.x, from.y + cfg.vault_height + 0.4, wall.z) + dir * 0.12, Vector3(wall.x, from.y + 0.2, wall.z) + dir * 0.12, mask))
	if top_ray.is_empty():
		return []
	var top_at: Vector3 = top_ray["position"]
	var top: float = top_at.y - from.y
	if top < 0.3 or top > cfg.vault_height:
		return []
	# Room for the body over the top.
	var over: float = from.y + top + 0.95
	if not space.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(from.x, over, from.z), Vector3(wall.x, over, wall.z) + dir * 1.8, mask)).is_empty():
		return []
	# Ground beyond, below the top (not on it), about level with where he started.
	for k: float in [0.55, 0.85, 1.2, 1.6]:
		var at: Vector3 = Vector3(wall.x, 0.0, wall.z) + dir * k
		var down: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(
				Vector3(at.x, from.y + top + 0.5, at.z), Vector3(at.x, from.y - 1.2, at.z), mask))
		if down.is_empty():
			return []
		var g: Vector3 = down["position"]
		if g.y > from.y + top - 0.25:
			continue  # still on top of it
		if absf(g.y - from.y) > 0.8:
			return []
		var land: Vector3 = g + dir * 0.35
		# The clip tucks the feet up about 0.35 m; the body itself rises to clear the top by ~0.25 m.
		return [land, maxf(top - VAULT_TUCK + 0.25, 0.2)]
	return []


## Carries the body over (Enemy._physics_process calls this instead of
## moving him). True while the vault lasts.
func update_vault(delta: float) -> bool:
	if phase != Phase.VAULT:
		return false
	_t += delta
	var u: float = clampf(_t / cfg.vault_time, 0.0, 1.0)
	var at: Vector3 = _vault_from.lerp(_vault_to, u)
	var base: float = lerpf(_vault_from.y, _vault_to.y, u)
	at.y = base + maxf(_vault_rise - (base - _vault_from.y), 0.0) * sin(PI * minf(u * 1.15, 1.0))
	e.global_position = at
	e.velocity = Vector3.ZERO
	e.body.set_motion(Vector3.ZERO)
	if u >= 1.0:
		_enter(Phase.CHARGE if _flat(_vault_to - (_player().global_position if _player() else _vault_to)).length() <= cfg.charge_range else Phase.APPROACH, 0.0)
		e.velocity = _flat(_vault_to - _vault_from).normalized() * speed() * 0.8
		e._think = 0.0
	return true


# ------------------------------------------------------------------ helpers

func _enter(ph: Phase, length: float) -> void:
	phase = ph
	_t = 0.0
	_len = length


func _player() -> Player:
	return e.squad.player() if e.squad else null


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)
