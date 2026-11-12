class_name StatRequirement
extends Resource
## A stat a part needs before it works (docs/design.md §3.6): "the GX-4 needs
## structure ≥ 1.25", "a drone needs connectivity ≥ 2". A part whose
## requirements aren't met stays installed (its mass and capacity count) but
## is offline: no power, no heat, no stat changes, and an active can't start.

@export var stat: StringName = &""
## The stat has to be at least this (-INF: no lower bound).
@export var at_least: float = -INF
## ...and at most this (INF: no upper bound), e.g. a silhouette limit.
@export var at_most: float = INF
## Why, in a few words ("coil recoil would shatter an organic arm").
@export var reason: String = ""


static func make(p_stat: StringName, p_at_least: float, p_reason: String = "") -> StatRequirement:
	var r: StatRequirement = StatRequirement.new()
	r.stat = p_stat
	r.at_least = p_at_least
	r.reason = p_reason
	return r


func met(value: float) -> bool:
	return value >= at_least - 0.0001 and value <= at_most + 0.0001


## "structure 1.25+" / "silhouette at most 1.20".
func describe() -> String:
	var name: String = Stats.label(stat).to_lower()
	if at_least > -INF and at_most < INF:
		return "%s %s-%s" % [name, Stats.format(stat, at_least), Stats.format(stat, at_most)]
	if at_most < INF:
		return "%s at most %s" % [name, Stats.format(stat, at_most)]
	return "%s %s+" % [name, Stats.format(stat, at_least)]
