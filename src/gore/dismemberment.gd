class_name Dismemberment
extends RefCounted
## Where a hit takes a body apart (the model is described in GoreConfig).
## Pure functions, so tests can check them without a scene.

enum Outcome { NONE, SEVER, PULP }

## The cuts a hit on each zone can act on (the nearest wins, by distance).
## A hit on the upper arm near the elbow takes the forearm; near the
## shoulder, the arm. The torso has no cut of its own: hits close to a
## shoulder or a hip can still take the limb there.
const ZONE_CUTS: Dictionary[StringName, Array] = {
	&"head": [&"head"],
	&"neck": [&"head"],
	&"l_upper_arm": [&"upper_arm_L", &"forearm_L"],
	&"r_upper_arm": [&"upper_arm_R", &"forearm_R"],
	&"l_forearm": [&"forearm_L", &"hand_L", &"upper_arm_L"],
	&"r_forearm": [&"forearm_R", &"hand_R", &"upper_arm_R"],
	&"l_hand": [&"hand_L", &"forearm_L"],
	&"r_hand": [&"hand_R", &"forearm_R"],
	&"l_thigh": [&"thigh_L", &"shin_L"],
	&"r_thigh": [&"thigh_R", &"shin_R"],
	&"l_shin": [&"shin_L", &"thigh_L"],
	&"r_shin": [&"shin_R", &"thigh_R"],
	&"l_foot": [&"shin_L"],
	&"r_foot": [&"shin_R"],
	&"chest": [],
	&"stomach": [],
	&"pelvis": [],
}
const TORSO: Array[StringName] = [&"chest", &"stomach", &"pelvis"]


## A hit's violence (J): what it left in the body, plus a share of what it
## arrived with, × its damage type.
static func violence(cfg: GoreConfig, deposited: float, energy_in: float, type: DamageInfo.Type) -> float:
	return (maxf(deposited, 0.0) + cfg.arrival_share * maxf(energy_in, 0.0)) * cfg.type_factor(type)


## The cut a hit at `point` on `zone` acts on, and the share of its violence
## that reaches it: [segment, share]. `cuts`: segment -> where its cut is
## now (world). Severed segments are skipped. [&"", 0] if none is in reach.
static func nearest_cut(cfg: GoreConfig, zone: StringName, point: Vector3, cuts: Dictionary[StringName, Vector3],
		severed: Dictionary[StringName, bool]) -> Array:
	var best: StringName = &""
	var best_share: float = 0.0
	for seg: StringName in ZONE_CUTS.get(zone, []):
		if severed.has(seg) or not cuts.has(seg):
			continue
		var share: float = cfg.falloff(point.distance_to(cuts[seg]))
		if share > best_share and share >= 0.1:
			best_share = share
			best = seg
	return [best, best_share]


## What a volley does to a segment: `volley` = violence at the cut this
## volley, `total` = what has added up there so far (this volley included).
static func outcome(cfg: GoreConfig, segment: StringName, volley: float, total: float) -> Outcome:
	var t: float = cfg.threshold(segment)
	if volley >= t * cfg.pulp_factor and segment != &"head":
		return Outcome.PULP
	if volley >= t or total >= t * cfg.accumulate_factor:
		return Outcome.SEVER
	return Outcome.NONE


## Whether one hit's share counts toward the running total at a cut.
static func adds_up(cfg: GoreConfig, segment: StringName, amount: float) -> bool:
	return amount >= cfg.threshold(segment) * cfg.min_share


## How fast a severed piece flies off (m/s) for a volley of `violence` J.
static func fling_speed(cfg: GoreConfig, violence_j: float) -> float:
	return clampf(violence_j * 0.001 * cfg.fling_per_kj, cfg.fling_min, cfg.fling_max)
