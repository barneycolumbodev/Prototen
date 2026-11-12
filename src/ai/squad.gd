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


func set_player(p: Player) -> void:
	_player = p


func player() -> Player:
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group(&"player") as Player
	return _player


func add(e: Enemy) -> void:
	_prune()
	members.append(e)
	e.squad = self


## Drops freed members (bodies cleaned up, range targets replaced).
func _prune() -> void:
	var keep: Array[Enemy] = []
	for x: Variant in members:
		if is_instance_valid(x):
			var m: Enemy = x
			keep.append(m)
	members = keep
	var shooters: Array[Enemy] = []
	for x: Variant in _shooters:
		if is_instance_valid(x):
			var sh: Enemy = x
			if sh.alive:
				shooters.append(sh)
	_shooters = shooters
	for k: Variant in _claimed.keys():
		if not is_instance_valid(_claimed[k]):
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
		if is_instance_valid(e) and e.alive and e.state not in [Enemy.State.SURRENDER, Enemy.State.CRAWL]:
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
	_prune()
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
		if p and not cover_hides(c, p):
			continue
		var score: float = dist + absf(to_threat - e.config.preferred_range) * 0.5
		if score < best_score:
			best_score = score
			best = c
			_claim(i, e)
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
