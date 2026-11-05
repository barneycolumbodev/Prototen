class_name BodyModel
extends RefCounted
## The augmented body as numbers (docs/design.md §3.2, §9.2 proposal): the
## frame's base values plus everything the installed parts add.
##
## - Totals: mass, constant power draw and heat, loadout capacity used.
## - Stats: stat = (base + Σ add) × Π mul over every part's StatModifiers.
## - Runtime pools: a power reserve (the frame's cell recharges it, parts
##   drain it) and stored heat (the frame sheds it). Actives add their draw
##   and heat while running. Nothing reads power or heat for gameplay yet;
##   they're on the body-status screen so the numbers can be tuned before M2
##   makes them bite (overheating, brown-outs, EMP).

signal changed

## Stat names and what reads them. Bases come from PlayerBodyConfig.
const STATS: Array[StringName] = [
	&"max_health",      # Player
	&"damage_per_kj",   # Player: damage taken per kJ of a round
	&"regen_rate",      # Player: health per second
	&"regen_delay",     # Player: seconds out of fire before healing
	&"move_speed",      # Player: multiplier on walk/sprint/crouch
	&"jump",            # Player: multiplier on jump height
	&"carry_kg",        # (M3) heavy weapons
	&"recoil",          # (M2) multiplier on recoil
	&"aim_speed",       # (M2) multiplier on ADS speed
	&"reload_speed",    # (M2) multiplier on reload speed
]

var frame: PlayerBodyConfig
var loadout: BodyLoadout
var mass_kg: float = 0.0
var power_draw_w: float = 0.0
var heat_w: float = 0.0
var capacity_used: int = 0
## Joules in the reserve, and stored heat in joules.
var power_j: float = 0.0
var heat_j: float = 0.0

var _stats: Dictionary[StringName, float] = {}
var _active_draw_w: float = 0.0
var _active_heat_w: float = 0.0


func _init(p_frame: PlayerBodyConfig, p_loadout: BodyLoadout) -> void:
	frame = p_frame
	loadout = p_loadout if p_loadout else BodyLoadout.new()
	rebuild()
	power_j = frame.power_capacity_j


func base(stat: StringName) -> float:
	match stat:
		&"max_health":
			return frame.max_health
		&"damage_per_kj":
			return frame.damage_per_kj
		&"regen_rate":
			return frame.regen_rate
		&"regen_delay":
			return frame.regen_delay
		&"carry_kg":
			return frame.carry_kg
	return 1.0  # multipliers


## Recomputes totals and stats from the loadout (after a part is added/removed).
func rebuild() -> void:
	mass_kg = frame.base_mass_kg
	power_draw_w = 0.0
	heat_w = 0.0
	capacity_used = 0
	var adds: Dictionary[StringName, float] = {}
	var muls: Dictionary[StringName, float] = {}
	for p: PartData in loadout.parts:
		mass_kg += p.mass_kg
		power_draw_w += p.power_draw_w
		heat_w += p.heat_w
		capacity_used += p.capacity
		for m: StatModifier in p.modifiers:
			if m.stat not in STATS:
				push_warning("BodyModel: part %s changes unknown stat '%s'" % [p.id, m.stat])
				continue
			adds[m.stat] = adds.get(m.stat, 0.0) + m.add
			muls[m.stat] = muls.get(m.stat, 1.0) * m.mul
	_stats.clear()
	for s: StringName in STATS:
		_stats[s] = (base(s) + adds.get(s, 0.0)) * muls.get(s, 1.0)
	changed.emit()


func stat(name: StringName) -> float:
	return _stats.get(name, base(name))


func capacity_left() -> int:
	return frame.capacity - capacity_used


## Power/heat while an active part runs (it calls this on start and stop).
func set_active_load(draw_w: float, heat: float) -> void:
	_active_draw_w = draw_w
	_active_heat_w = heat


## Total draw right now (W): constant parts plus running actives.
func current_draw_w() -> float:
	return power_draw_w + _active_draw_w


func tick(delta: float) -> void:
	var net_w: float = frame.power_supply_w - current_draw_w()
	power_j = clampf(power_j + net_w * delta, 0.0, frame.power_capacity_j)
	var heat_in: float = heat_w + _active_heat_w
	heat_j = clampf(heat_j + (heat_in - frame.heat_dissipation_w) * delta, 0.0, frame.heat_capacity_j)


func power_fraction() -> float:
	return power_j / maxf(frame.power_capacity_j, 1.0)


func heat_fraction() -> float:
	return heat_j / maxf(frame.heat_capacity_j, 1.0)
