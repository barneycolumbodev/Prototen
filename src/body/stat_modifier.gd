class_name StatModifier
extends Resource
## One change a part makes to one body stat (docs/design.md §3.2, §9.2):
## stat = (base + sum of `add`) * product of `mul`.
## Stats are named (see BodyModel.BASE_STATS); unknown names are ignored with
## a warning so a typo in a .tres shows up in the log.

@export var stat: StringName = &""
@export var add: float = 0.0
@export var mul: float = 1.0


static func make(p_stat: StringName, p_add: float = 0.0, p_mul: float = 1.0) -> StatModifier:
	var m: StatModifier = StatModifier.new()
	m.stat = p_stat
	m.add = p_add
	m.mul = p_mul
	return m
