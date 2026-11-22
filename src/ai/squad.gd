class_name Squad
extends Node
## Coordinates the triad members in a level (docs/design.md §5.6):
## - Only a few shoot at the player at once (tokens, handed round).
## - Contact reports spread: one sees the augment, all know where he was.
## - Deaths hit the morale of everyone who saw them; losing the Red Pole hits
##   everyone; a living Red Pole steadies those near him.
## - Callouts with a cooldown, spoken (Enemy.speak) and shown as subtitles.
## - Cover: points next to low cover, scored by whether they hide a man from
##   the player and how far he has to run.
## - In wave modes (`hunt` set, docs/design.md §5.6a): the squad always
##   knows roughly where the operative is (lookouts phone it in when nobody
##   has eyes on him), nobody stands around, and once they have contact
##   they work together: pinners hold and keep his head down, flankers run
##   round to his side, everyone else moves up cover by cover.

enum Role { NONE, PIN, FLANK, PUSH }

const MAX_SHOOTERS: int = 3
const CALLOUT_GAP: float = 2.2
const COVER_SPACING: float = 1.2

var members: Array[Enemy] = []
var cover_points: PackedVector3Array = PackedVector3Array()
## Cover point -> the enemy holding it.
var _claimed: Dictionary = {}
var _shooters: Array[Enemy] = []
var _player: Player
var _last_callout: float = -99.0
## Wave modes: how the squad hunts and coordinates. Null: it doesn't.
var hunt: HuntConfig
## The squad's picture of where he is, and the clock (seconds, scaled time).
var intel: Vector3 = Vector3.INF
var clock: float = 0.0
## When anyone last had eyes on him, and when the last lookout tip came.
var seen_at: float = -99.0
var tip_at: float = -99.0
var tips: int = 0
## Set by the spawner: moves a stuck man to a spawn point the operative
## can't see; returns whether it did.
var relocate: Callable
var relocations: int = 0
var _role_timer: float = 0.0
## Packs (HuntConfig "Packs"): the one being filled, how full it is, each
## pack's bearing from him, when it last saw him, and which packs hunt.
var _pack_next: int = 0
var _pack_fill: int = 0
var _pack_bearing: Dictionary[int, float] = {}
var _pack_engaged: Dictionary[int, float] = {}
var _pack_hunting: Dictionary[int, bool] = {}
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _last_prune_frame: int = -1


func _ready() -> void:
	_rng.randomize()


func set_player(p: Player) -> void:
	_player = p


## Turns on the hunt (wave modes).
func enable_hunt(cfg: HuntConfig = null) -> void:
	hunt = cfg if cfg else load("res://data/enemies/hunt.tres") as HuntConfig


func player() -> Player:
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group(&"player") as Player
	return _player


func add(e: Enemy) -> void:
	_prune(true)
	members.append(e)
	e.squad = self
	if _pack_fill >= (hunt.pack_size if hunt else 3):
		new_pack()
	e.pack = _pack_next
	_pack_fill += 1


## The next man added starts a pack of his own (the spawner calls this
## before each batch, so a batch comes in together).
func new_pack() -> void:
	if _pack_fill > 0:
		_pack_next += 1
		_pack_fill = 0


## Does pack `k` hunt him right now? Everyone does when few are left.
func is_hunting(k: int) -> bool:
	if hunt == null or hunt.hunting_packs <= 0:
		return true
	var on: bool = _pack_hunting.get(k, false)
	return on or fighting_count() <= hunt.last_count


## Where a holding pack waits: `hold_distance` from him on its own bearing
## (taken from where `e` is the first time), spread over `hold_scatter`.
func hold_point(e: Enemy) -> Vector3:
	var p: Player = player()
	if p == null:
		return e.global_position
	if not _pack_bearing.has(e.pack):
		var off: Vector3 = _flat(e.global_position - p.global_position)
		_pack_bearing[e.pack] = atan2(off.x, off.z) if off.length_squared() > 0.01 else _rng.randf() * TAU
	var b: float = _pack_bearing[e.pack]
	return _scatter(p.global_position + Vector3(sin(b), 0.0, cos(b)) * hunt.hold_distance, hunt.hold_scatter)


## Picks the packs that hunt: those that saw him lately first, then the
## nearest, up to `hunting_packs`. A pack that starts hunting is sent at
## him; one that stops is sent back to its holding point.
func update_packs() -> void:
	var p: Player = player()
	if p == null or hunt == null:
		return
	var nearest: Dictionary[int, float] = {}
	for e: Enemy in members:
		if not is_instance_valid(e) or not e.alive or e.passive or e.state == Enemy.State.SURRENDER or e.state == Enemy.State.CRAWL:
			continue
		var d: float = e.global_position.distance_to(p.global_position)
		var cur: float = nearest.get(e.pack, INF)
		nearest[e.pack] = minf(cur, d)
	var packs: Array = nearest.keys()
	packs.sort_custom(func(a: int, b: int) -> bool:
		var ta: float = _pack_engaged.get(a, -99.0)
		var tb: float = _pack_engaged.get(b, -99.0)
		var ea: bool = clock - ta < hunt.engaged_memory
		var eb: bool = clock - tb < hunt.engaged_memory
		if ea != eb:
			return ea
		var na: float = nearest[a]
		var nb: float = nearest[b]
		return na < nb)
	var all: bool = hunt.hunting_packs <= 0 or fighting_count() <= hunt.last_count
	for i: int in packs.size():
		var k: int = packs[i]
		var now: bool = all or i < hunt.hunting_packs
		var was: Variant = _pack_hunting.get(k)
		_pack_hunting[k] = now
		if was != null and was == now:
			continue
		for e: Enemy in members:
			if not is_instance_valid(e) or e.pack != k or not e.alive or e.passive or (e.state != Enemy.State.IDLE and e.state != Enemy.State.ALERT):
				continue
			if now:
				var at: Vector3 = intel if intel != Vector3.INF else p.global_position
				e.last_known = _scatter(at, hunt.tip_scatter + hunt.intel_noise * 0.5)
			else:
				e.last_known = hold_point(e)


## Drops freed members (bodies cleaned up, range targets replaced) in place.
func _prune(force: bool = false) -> void:
	var frame: int = Engine.get_physics_frames()
	if not force and frame == _last_prune_frame:
		return
	_last_prune_frame = frame
	for i: int in range(members.size() - 1, -1, -1):
		if not is_instance_valid(members[i]):
			members.remove_at(i)
	for i: int in range(_shooters.size() - 1, -1, -1):
		var sh: Variant = _shooters[i]
		if not is_instance_valid(sh):
			_shooters.remove_at(i)
		else:
			var e: Enemy = sh
			if not e.alive:
				_shooters.remove_at(i)
	if not _claimed.is_empty():
		var dead_keys: Array = []
		for k: Variant in _claimed:
			if not is_instance_valid(_claimed[k]):
				dead_keys.append(k)
		for k: Variant in dead_keys:
			_claimed.erase(k)


## Who holds cover point `i` (null if nobody alive).
func _holder(i: int) -> Enemy:
	if not _claimed.has(i) or not is_instance_valid(_claimed[i]):
		return null
	var e: Enemy = _claimed[i]
	return e if e.alive else null


func alive_count() -> int:
	_prune()
	var n: int = 0
	for e: Enemy in members:
		if is_instance_valid(e) and e.alive:
			n += 1
	return n


## Living members that still fight (not surrendered, crawling or fled for good).
func fighting_count() -> int:
	_prune()
	var n: int = 0
	for e: Enemy in members:
		if is_instance_valid(e) and e.alive and e.state != Enemy.State.SURRENDER and e.state != Enemy.State.CRAWL:
			n += 1
	return n


func request_token(e: Enemy) -> bool:
	_prune()
	if e in _shooters:
		return true
	if _shooters.size() < MAX_SHOOTERS:
		_shooters.append(e)
		return true
	return false


func release_token(e: Enemy) -> void:
	_shooters.erase(e)


func shooter_count() -> int:
	return _shooters.size()


func report_contact(from: Enemy, where: Vector3) -> void:
	_prune()
	intel = where
	seen_at = clock
	for e: Enemy in members:
		if is_instance_valid(e) and e.alive and e != from and e.global_position.distance_to(from.global_position) < 30.0:
			if e.last_known == Vector3.INF or not e.sees_player:
				e.last_known = where
			e.awareness = maxf(e.awareness, 0.9)
			if e.state == Enemy.State.IDLE and not e.passive:
				e._enter(Enemy.State.ALERT)


## One of them was snatched off his feet by the mesh arm: everyone who can
## see it is shaken, and knows where the operative is.
func on_ally_seized(taken: Enemy, by: Node) -> void:
	_prune()
	for e: Enemy in members:
		if not is_instance_valid(e) or not e.alive or e == taken:
			continue
		if e.global_position.distance_to(taken.global_position) < 20.0:
			e.morale -= 0.12
			e._alerted_by(by)


func on_death(dead: Enemy, hit: BallisticHit) -> void:
	_prune(true)
	var gory: bool = not dead.body.severed.is_empty() or (hit != null and hit.damage != null and hit.damage.has_flag(DamageInfo.Flags.HEADSHOT))
	var officer: bool = dead.config.officer
	for e: Enemy in members:
		if not is_instance_valid(e) or not e.alive or e == dead:
			continue
		if officer or _can_see(e, dead.global_position + Vector3.UP):
			e.on_ally_down(dead.global_position, gory, officer)
	var near: Enemy = _nearest_alive(dead.global_position)
	if near:
		if officer:
			callout(near, &"officer_down", true)
		else:
			callout(near, &"man_down")
	for k: Variant in _claimed.keys():
		if _claimed[k] == dead:
			_claimed.erase(k)


func officer_near(e: Enemy) -> bool:
	_prune()
	for o: Enemy in members:
		if is_instance_valid(o) and o.alive and o.config.officer and o != e and o.global_position.distance_to(e.global_position) < 12.0:
			return true
	return false


## `from` says a line for `situation` (VoiceLines), unless someone spoke
## less than CALLOUT_GAP ago (`force` ignores that).
func callout(from: Enemy, situation: StringName, force: bool = false) -> void:
	var now: float = Time.get_ticks_msec() * 0.001
	if not force and now - _last_callout < CALLOUT_GAP:
		return
	if from.speak(situation) != "":
		_last_callout = now


## Someone broke and ran: a Red Pole nearby shouts at them to hold.
func rally(runner: Enemy) -> void:
	_prune()
	for o: Enemy in members:
		if is_instance_valid(o) and o.alive and o.config.officer and o != runner \
				and o.global_position.distance_to(runner.global_position) < 15.0:
			callout(o, &"rally")
			return


# ------------------------------------------------------------------ cover

## Samples cover points around the level's low obstacles: spots on open
## ground with something 0.6–1.4 m tall within arm's reach.
func build_cover(origin: Vector3, half_extent: float, world: World3D, append: bool = false) -> void:
	if not append:
		cover_points.clear()
	var space: PhysicsDirectSpaceState3D = world.direct_space_state
	var steps: int = int(half_extent * 2.0 / COVER_SPACING)
	var dirs: Array[Vector3] = [Vector3.FORWARD, Vector3.BACK, Vector3.LEFT, Vector3.RIGHT]
	for ix: int in steps + 1:
		for iz: int in steps + 1:
			var p: Vector3 = origin + Vector3(-half_extent + ix * COVER_SPACING, 0.0, -half_extent + iz * COVER_SPACING)
			# Standing room: nothing at 0.5 m or 1.6 m right here.
			var down: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.3, p + Vector3.DOWN * 0.5, Ballistics.LAYER_WORLD))
			if down.is_empty():
				continue
			var ground: Vector3 = down["position"]
			if _blocked_sphere(space, ground + Vector3.UP * 0.9, 0.35):
				continue
			for d: Vector3 in dirs:
				var low: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(ground + Vector3.UP * 0.8, ground + Vector3.UP * 0.8 + d * 0.9, Ballistics.LAYER_WORLD))
				if low.is_empty():
					continue
				var high: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(ground + Vector3.UP * 1.55, ground + Vector3.UP * 1.55 + d * 1.0, Ballistics.LAYER_WORLD))
				if high.is_empty():
					var low_at: Vector3 = low["position"]
					var at: Vector3 = low_at - d * 0.55
					at.y = ground.y
					cover_points.append(at)
					break


func _blocked_sphere(space: PhysicsDirectSpaceState3D, at: Vector3, r: float) -> bool:
	var q: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	var s: SphereShape3D = SphereShape3D.new()
	s.radius = r
	q.shape = s
	q.transform = Transform3D(Basis(), at)
	q.collision_mask = Ballistics.LAYER_WORLD
	return not space.intersect_shape(q, 1).is_empty()


## Best free cover point for `e` against a threat at `threat`, or INF.
func find_cover(e: Enemy, threat: Vector3) -> Vector3:
	_prune()
	var best: Vector3 = Vector3.INF
	var best_score: float = INF
	var best_i: int = -1
	var p: Player = player()
	for i: int in cover_points.size():
		var c: Vector3 = cover_points[i]
		var holder: Enemy = _holder(i)
		if holder != null and holder != e:
			continue
		var dist: float = c.distance_to(e.global_position)
		if dist > 24.0:
			continue
		var to_threat: float = c.distance_to(threat)
		if to_threat < 4.0 or to_threat > e.config.max_range:
			continue
		var score: float = dist + absf(to_threat - e.config.preferred_range) * 0.5
		if score >= best_score:
			continue
		if p and not cover_hides(c, p):
			continue
		best_score = score
		best = c
		best_i = i
	if best_i >= 0:
		_claim(best_i, e)
	return best


func _claim(i: int, e: Enemy) -> void:
	for k: Variant in _claimed.keys():
		if _claimed[k] == e:
			_claimed.erase(k)
	_claimed[i] = e


## A crouched man at `c` is hidden from the player but can rise to shoot over it.
func cover_hides(c: Vector3, p: Player) -> bool:
	if c == Vector3.INF or p == null:
		return false
	var eye: Vector3 = p.camera().global_position
	var space: PhysicsDirectSpaceState3D = p.get_world_3d().direct_space_state
	var low: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, c + Vector3.UP * 0.8, Ballistics.LAYER_WORLD))
	if low.is_empty():
		return false
	var at: Vector3 = low["position"]
	return at.distance_to(c) < 2.6


func _can_see(e: Enemy, at: Vector3) -> bool:
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(e.body.head_position(), at, Ballistics.LAYER_WORLD)
	return e.get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _nearest_alive(at: Vector3) -> Enemy:
	_prune()
	var best: Enemy
	var best_d: float = INF
	for e: Enemy in members:
		if is_instance_valid(e) and e.alive and e.state != Enemy.State.SURRENDER:
			var d: float = e.global_position.distance_to(at)
			if d < best_d:
				best_d = d
				best = e
	return best


# ------------------------------------------------------------------ the hunt

func _physics_process(delta: float) -> void:
	clock += delta
	if hunt == null:
		return
	var p: Player = player()
	if p == null or p.dead:
		return
	_prune()
	for e: Enemy in members:
		if is_instance_valid(e) and e.alive and e.sees_player:
			seen_at = clock
			intel = p.global_position
			_pack_engaged[e.pack] = clock
	var few: bool = fighting_count() <= hunt.last_count
	var refresh: float = hunt.last_refresh if few else hunt.intel_refresh
	if clock - maxf(seen_at, tip_at) > refresh:
		_lookout_tip(p, hunt.last_noise if few else hunt.intel_noise)
	_role_timer -= delta
	if _role_timer <= 0.0:
		_role_timer = hunt.role_interval
		update_packs()
		assign_roles()


## Nobody has eyes on him: the lookouts phone in where he is, give or take
## `noise` metres, and every man still fighting heads there.
func _lookout_tip(p: Player, noise: float) -> void:
	tip_at = clock
	tips += 1
	var a: float = _rng.randf() * TAU
	intel = p.global_position + Vector3(cos(a), 0.0, sin(a)) * noise * sqrt(_rng.randf())
	var spoke: bool = false
	for e: Enemy in members:
		if not is_instance_valid(e) or not e.alive or e.passive or e.state == Enemy.State.SURRENDER or e.state == Enemy.State.CRAWL or e.state == Enemy.State.GUT:
			continue
		if e.sees_player:
			continue
		if not is_hunting(e.pack):
			# Holding off: keep to his side of the map, a step out of reach.
			if e.state == Enemy.State.IDLE or e.state == Enemy.State.ALERT:
				e.last_known = hold_point(e)
			continue
		e.last_known = _scatter(intel, hunt.tip_scatter)
		e.awareness = maxf(e.awareness, 0.9)
		if e.state == Enemy.State.IDLE:
			e._enter(Enemy.State.ALERT)
		if not spoke and (e.state == Enemy.State.ALERT or e.state == Enemy.State.COMBAT) and _rng.randf() < 0.5:
			callout(e, &"hunt")
			spoke = true


## `e` has been stuck: put him somewhere he can come from (out of sight).
func unstick(e: Enemy) -> bool:
	if not relocate.is_valid():
		return false
	var ok: bool = relocate.call(e)
	if ok:
		relocations += 1
		e.last_known = search_point(e)
	return ok


## Where `e` should look next: the latest tip if he hasn't been there, or
## somewhere round it he hasn't checked.
func search_point(e: Enemy) -> Vector3:
	if hunt and not is_hunting(e.pack):
		return hold_point(e)
	var base: Vector3 = intel if intel != Vector3.INF else e.global_position
	var r: float = hunt.search_radius if hunt else 6.0
	if e.last_known == Vector3.INF or _flat(e.last_known - base).length() > r:
		return _scatter(base, 1.5)
	return _scatter(base, r)


## A reachable point within `r` of `at`.
func _scatter(at: Vector3, r: float) -> Vector3:
	var a: float = _rng.randf() * TAU
	var want: Vector3 = at + Vector3(cos(a), 0.0, sin(a)) * r * sqrt(_rng.randf())
	var p: Player = player()
	if p == null or not p.is_inside_tree():
		return want
	var map: RID = p.get_world_3d().navigation_map
	if map.is_valid() and NavigationServer3D.map_get_iteration_id(map) > 0 and not NavigationServer3D.map_get_regions(map).is_empty():
		return NavigationServer3D.map_get_closest_point(map, want)
	return want


## Somebody saw him recently.
func contact_fresh() -> bool:
	return hunt != null and clock - seen_at < hunt.contact_fresh


## Down to the last few: the ones who ran turn back.
func cornered() -> bool:
	return hunt != null and fighting_count() <= hunt.last_count


## Hands out pin / flank / push to the gunmen while there's contact: the
## ones with eyes on him (or nearest his line) pin, the ones furthest round
## his side flank, the rest push. No contact: no roles, everyone hunts.
func assign_roles() -> void:
	var p: Player = player()
	if p == null:
		return
	var gunmen: Array[Enemy] = []
	for e: Enemy in members:
		if not e.alive or e.passive or e.boss != null or e.melee != null or e.state != Enemy.State.COMBAT or not e.has_gun or not is_hunting(e.pack):
			if e.alive and e.squad_role != Role.NONE and (e.state != Enemy.State.COMBAT or not is_hunting(e.pack)):
				e.set_squad_role(Role.NONE)
			continue
		gunmen.append(e)
	# Contact is shared: whoever has eyes on him calls it, so the rest know
	# where to put their rounds and where to go.
	if clock - seen_at < 0.5 and intel != Vector3.INF:
		for e: Enemy in members:
			if e.alive and not e.sees_player and e.state == Enemy.State.COMBAT and is_hunting(e.pack):
				e.last_known = intel
	if not contact_fresh() or gunmen.is_empty():
		for e: Enemy in gunmen:
			e.set_squad_role(Role.NONE)
		return
	if gunmen.size() == 1:
		gunmen[0].set_squad_role(Role.PUSH)
		return
	var at: Vector3 = p.global_position
	# Pinners first: keep the ones who already pin and still see him or did
	# moments ago; then whoever has eyes on him, nearest first. Melee men
	# can't pin.
	var pinners: Array[Enemy] = []
	var by_contact: Array[Enemy] = gunmen.duplicate()
	by_contact.sort_custom(func(a: Enemy, b: Enemy) -> bool:
		return _pin_score(a, at) < _pin_score(b, at))
	var flank_n: int = mini(hunt.flank_count, gunmen.size() / 2)
	var pin_n: int = mini(hunt.pin_count, gunmen.size() - flank_n)
	for e: Enemy in by_contact:
		if pinners.size() >= pin_n:
			break
		if e.melee == null and not e.config.aggressive:
			pinners.append(e)
	if pinners.is_empty():
		pin_n = 0
	# The pin axis: from him toward the pinners (or the squad's middle).
	var axis: Vector3 = Vector3.ZERO
	for e: Enemy in (pinners if not pinners.is_empty() else gunmen):
		axis += _flat(e.global_position - at).normalized()
	axis = axis.normalized() if axis.length_squared() > 0.001 else Vector3.FORWARD
	# Flankers: whoever is already furthest round off that axis (and not a
	# pinner, not the Red Pole); existing flankers keep going.
	var rest: Array[Enemy] = []
	for e: Enemy in gunmen:
		if e not in pinners:
			rest.append(e)
	rest.sort_custom(func(a: Enemy, b: Enemy) -> bool:
		return _flank_score(a, at, axis) > _flank_score(b, at, axis))
	var flankers: Array[Enemy] = []
	for e: Enemy in rest:
		if flankers.size() >= flank_n:
			break
		if e.config.officer:
			continue
		if e.squad_role == Role.FLANK or e.flank_done_at < 0.0 or clock - e.flank_done_at > hunt.flank_timeout:
			flankers.append(e)
	for e: Enemy in gunmen:
		if e in pinners:
			e.set_squad_role(Role.PIN)
		elif e in flankers:
			if e.squad_role != Role.FLANK:
				var side: float = signf(axis.cross(_flat(e.global_position - at)).y)
				if side == 0.0:
					side = 1.0 if _rng.randf() < 0.5 else -1.0
				e.flank_target = flank_point(at, axis, side)
				e.set_squad_role(Role.FLANK)
				var caller: Enemy = _officer_or(pinners[0] if not pinners.is_empty() else e)
				callout(caller, &"flank")
		else:
			e.set_squad_role(Role.PUSH)


func _pin_score(e: Enemy, at: Vector3) -> float:
	var s: float = _flat(e.global_position - at).length() * 0.1
	if e.sees_player:
		s -= 10.0
	elif e._unseen_for < 2.0:
		s -= 5.0
	if e.squad_role == Role.PIN:
		s -= 3.0
	return s


func _flank_score(e: Enemy, at: Vector3, axis: Vector3) -> float:
	var off: float = axis.angle_to(_flat(e.global_position - at).normalized())
	return off + (2.0 if e.squad_role == Role.FLANK else 0.0)


## A spot off his side: `flank_angle_deg` round from the pin axis, on
## `side`, at `flank_distance`; cover there that hides from him if any.
func flank_point(at: Vector3, axis: Vector3, side: float) -> Vector3:
	var dir: Vector3 = axis.rotated(Vector3.UP, side * deg_to_rad(hunt.flank_angle_deg if hunt else 95.0))
	var want: Vector3 = at + dir * (hunt.flank_distance if hunt else 11.0)
	var p: Player = player()
	var best: Vector3 = Vector3.INF
	var best_d: float = 6.0
	for c: Vector3 in cover_points:
		var d: float = _flat(c - want).length()
		if d < best_d and _flat(c - at).length() > 4.0 and (p == null or cover_hides(c, p)):
			best_d = d
			best = c
	return best if best != Vector3.INF else _scatter(want, 0.0)


func _officer_or(e: Enemy) -> Enemy:
	for o: Enemy in members:
		if o.alive and o.config.officer and o.state == Enemy.State.COMBAT:
			return o
	return e


## Free cover at least `step` nearer to him than `e` is now, hidden from him,
## a short run away. INF if there's none.
func find_cover_nearer(e: Enemy, threat: Vector3, step: float) -> Vector3:
	_prune()
	var p: Player = player()
	var now: float = _flat(e.global_position - threat).length()
	var best: Vector3 = Vector3.INF
	var best_score: float = INF
	var best_i: int = -1
	for i: int in cover_points.size():
		var c: Vector3 = cover_points[i]
		var holder: Enemy = _holder(i)
		if holder != null and holder != e:
			continue
		var to_threat: float = _flat(c - threat).length()
		if to_threat > now - step or to_threat < 4.0:
			continue
		var run: float = _flat(c - e.global_position).length()
		if run > 16.0:
			continue
		var score: float = run + to_threat * 0.4
		if score >= best_score:
			continue
		if p and not cover_hides(c, p):
			continue
		best_score = score
		best = c
		best_i = i
	if best_i >= 0:
		_claim(best_i, e)
	return best


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)
