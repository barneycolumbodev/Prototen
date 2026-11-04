class_name RangeStats
extends Node
## Shooting stats for the range (docs/m1-gunplay-plan.md item 6), shown in
## the debug overlay: shots, hit %, headshot %, kills, time between shots.
## A shot counts as a hit once, on the first target it touches (a shotgun
## shell once, however many pellets land: hits are keyed by volley).

const SPLITS_KEPT: int = 10

var shots: int = 0
var hits: int = 0
var headshots: int = 0
var kills: int = 0
var longest_hit: float = 0.0

var _hit_shots: Dictionary[int, bool] = {}
var _last_shot_ms: int = -1
var _splits: PackedFloat32Array = PackedFloat32Array()
var _best_split: float = INF


func _ready() -> void:
	add_to_group(&"range_stats")
	EventBus.shot_fired.connect(_on_shot)
	EventBus.target_hit.connect(_on_target_hit)


func reset() -> void:
	shots = 0
	hits = 0
	headshots = 0
	kills = 0
	longest_hit = 0.0
	_hit_shots.clear()
	_splits.clear()
	_best_split = INF
	_last_shot_ms = -1


func accuracy() -> float:
	return float(hits) / shots if shots > 0 else 0.0


func headshot_rate() -> float:
	return float(headshots) / hits if hits > 0 else 0.0


## Average time between the last few shots, seconds (0 if fewer than two).
func average_split() -> float:
	if _splits.is_empty():
		return 0.0
	var sum: float = 0.0
	for s: float in _splits:
		sum += s
	return sum / _splits.size()


func summary() -> String:
	return "range: shots %d  hits %d (%d%%)  head %d%%  kills %d  split %.0f ms (best %s)  longest %.1f m" % [
		shots, hits, roundi(accuracy() * 100.0), roundi(headshot_rate() * 100.0), kills,
		average_split() * 1000.0, "--" if _best_split == INF else "%.0f ms" % (_best_split * 1000.0), longest_hit]


func _on_shot(shooter: Node, _origin: Vector3, _dir: Vector3) -> void:
	if shooter == null or not shooter.is_in_group(&"player"):
		return
	shots += 1
	var now: int = Time.get_ticks_msec()
	if _last_shot_ms >= 0:
		var split: float = (now - _last_shot_ms) / 1000.0
		if split < 2.0:  # ignore pauses between strings
			_splits.append(split)
			if _splits.size() > SPLITS_KEPT:
				_splits.remove_at(0)
			_best_split = minf(_best_split, split)
	_last_shot_ms = now


func _on_target_hit(kind: StringName, hit: BallisticHit) -> void:
	if hit.shooter == null or not hit.shooter.is_in_group(&"player"):
		return
	if kind == &"kill":
		kills += 1
	var key: int = hit.volley_id if hit.volley_id != 0 else hit.shot_id
	if _hit_shots.has(key):
		return
	_hit_shots[key] = true
	hits += 1
	longest_hit = maxf(longest_hit, hit.distance)
	if hit.damage and hit.damage.has_flag(DamageInfo.Flags.HEADSHOT):
		headshots += 1
