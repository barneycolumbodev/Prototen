class_name Stats
extends RefCounted
## The body's core stats (docs/design.md §3.6): what each one means, which
## group it belongs to on the body-status screen, which way is better, the
## range it's clamped to, and which systems read it. Base values (the
## operative with no parts) live in data/player/body_default.tres
## (PlayerBodyConfig.stat_bases); `base` here is only the fallback.
##
## Every stat is computed the same way: (base + Σ add) × Π mul over the
## online parts, then clamped. Multiplier stats start at 1.0; point stats
## (health, connectivity, watts) start at their frame value.

enum Group { DURABILITY, MOBILITY, STRENGTH, MELEE, FIREARMS, SIGNATURE, NEURAL, SYSTEMS }

const GROUP_NAMES: Array[String] = ["DURABILITY", "MOBILITY", "STRENGTH", "MELEE", "FIREARMS", "SIGNATURE", "NEURAL", "POWER AND HEAT"]

## Display formats.
const MULT: int = 0      # ×1.15
const POINTS: int = 1    # 200
const WATTS: int = 2     # 450 W
const KG: int = 3        # 40 kg
const SECONDS: int = 4   # 3.0 s
const JOULES: int = 5    # 60 kJ

class StatDef:
	var group: int
	var label: String
	var fmt: int
	var better: int
	var min_value: float
	var max_value: float
	var base: float
	var reads: String

	static func make(p_group: int, p_label: String, p_fmt: int, p_better: int, p_min: float, p_max: float, p_base: float, p_reads: String) -> StatDef:
		var d: StatDef = StatDef.new()
		d.group = p_group
		d.label = p_label
		d.fmt = p_fmt
		d.better = p_better
		d.min_value = p_min
		d.max_value = p_max
		d.base = p_base
		d.reads = p_reads
		return d


## Every stat: key -> StatDef(group, label, format, better (+1 higher, -1 lower), min, max, base, what reads it).
static var DEFS: Dictionary[StringName, StatDef] = {
	&"max_health": StatDef.make(Group.DURABILITY, "Health", POINTS, 1, 20.0, 2000.0, 200.0, "Player health pool"),
	&"damage_per_kj": StatDef.make(Group.DURABILITY, "Damage per kJ", POINTS, -1, 0.5, 100.0, 7.0, "Damage taken per kJ of a round that hits you (armour lowers it)"),
	&"regen_rate": StatDef.make(Group.DURABILITY, "Regen rate", POINTS, 1, 0.0, 500.0, 50.0, "Health per second once healing starts"),
	&"regen_delay": StatDef.make(Group.DURABILITY, "Regen delay", SECONDS, -1, 0.3, 20.0, 3.0, "Seconds out of fire before healing starts"),
	&"move_speed": StatDef.make(Group.MOBILITY, "Move speed", MULT, 1, 0.3, 2.5, 1.0, "Walk, sprint and crouch speed (times the load factor)"),
	&"agility": StatDef.make(Group.MOBILITY, "Agility", MULT, 1, 0.3, 2.5, 1.0, "Acceleration, braking, air control, slide steering, mantle speed"),
	&"jump": StatDef.make(Group.MOBILITY, "Jump", MULT, 1, 0.2, 3.0, 1.0, "Jump height (times the load factor)"),
	&"slide": StatDef.make(Group.MOBILITY, "Slide", MULT, 1, 0.2, 3.0, 1.0, "Slide distance: less friction, more launch speed"),
	&"wallrun": StatDef.make(Group.MOBILITY, "Wall-run", MULT, 1, 0.0, 3.0, 1.0, "Wall-run duration. 0 = can't wall-run"),
	&"climb": StatDef.make(Group.MOBILITY, "Climb", MULT, 1, 0.3, 2.0, 1.0, "Highest ledge you can mantle"),
	&"strength": StatDef.make(Group.STRENGTH, "Strength", MULT, 1, 0.3, 4.0, 1.0, "Muscle force: carries mass (load), slide and melee impact, heavy-weapon recoil. Capped by structure"),
	&"structure": StatDef.make(Group.STRENGTH, "Structure", MULT, 1, 0.3, 4.0, 1.0, "Skeletal load rating: caps usable strength, absorbs heavy recoil, required by heavy hardware"),
	&"carry_kg": StatDef.make(Group.STRENGTH, "Carry", KG, 1, 5.0, 300.0, 40.0, "Weapon mass carried without a handling penalty"),
	&"impact": StatDef.make(Group.STRENGTH, "Impact", MULT, 1, 0.2, 4.0, 1.0, "How hard your body hits: slide and melee knockback"),
	&"melee_power": StatDef.make(Group.MELEE, "Melee power", MULT, 1, 0.2, 5.0, 1.0, "R3 strike damage"),
	&"melee_speed": StatDef.make(Group.MELEE, "Melee speed", MULT, 1, 0.3, 3.0, 1.0, "R3 strike recovery"),
	&"recoil": StatDef.make(Group.FIREARMS, "Recoil", MULT, -1, 0.2, 3.0, 1.0, "Recoil on every gun"),
	&"aim_speed": StatDef.make(Group.FIREARMS, "Aim speed", MULT, 1, 0.3, 3.0, 1.0, "Aim-down-sights speed"),
	&"reload_speed": StatDef.make(Group.FIREARMS, "Reload speed", MULT, 1, 0.3, 3.0, 1.0, "Reload speed"),
	&"handling": StatDef.make(Group.FIREARMS, "Handling", MULT, 1, 0.3, 3.0, 1.0, "Draw, holster and sprint-to-fire speed"),
	&"stability": StatDef.make(Group.FIREARMS, "Stability", MULT, 1, 0.3, 4.0, 1.0, "Accuracy on the move and in the air"),
	&"handgun": StatDef.make(Group.FIREARMS, "Handguns", MULT, 1, 0.3, 3.0, 1.0, "Proficiency: recoil, spread, aim and reload with pistols"),
	&"shotgun": StatDef.make(Group.FIREARMS, "Shotguns", MULT, 1, 0.3, 3.0, 1.0, "Proficiency: recoil, spread, aim and reload with shotguns"),
	&"rifle": StatDef.make(Group.FIREARMS, "Rifles", MULT, 1, 0.3, 3.0, 1.0, "Proficiency: recoil, spread, aim and reload with rifles and rail guns"),
	&"heavy": StatDef.make(Group.FIREARMS, "Heavy weapons", MULT, 1, 0.3, 3.0, 1.0, "Proficiency: recoil, spread, aim and reload with machine guns"),
	&"profile": StatDef.make(Group.SIGNATURE, "Silhouette", MULT, -1, 0.4, 3.0, 1.0, "Your size as a target: enemies hit a bigger body more often and spot it sooner"),
	&"signature": StatDef.make(Group.SIGNATURE, "Signature", MULT, -1, 0.1, 4.0, 1.0, "Thermal and visual signature: how fast enemies spot you (heat raises it)"),
	&"noise": StatDef.make(Group.SIGNATURE, "Noise", MULT, -1, 0.0, 4.0, 1.0, "How far enemies hear you move"),
	&"processing": StatDef.make(Group.NEURAL, "Processing", MULT, 1, 0.3, 3.0, 1.0, "Neural processing: RX-9 speed and duration, required by reflex hardware"),
	&"connectivity": StatDef.make(Group.NEURAL, "Connectivity", POINTS, 1, 0.0, 20.0, 0.0, "Neural link bandwidth: gates remote-controlled hardware (drones), sets link range, links smart weapons"),
	&"perception": StatDef.make(Group.NEURAL, "Perception", MULT, 1, 0.3, 3.0, 1.0, "Target tracking: aim-assist strength"),
	&"power_supply_w": StatDef.make(Group.SYSTEMS, "Power supply", WATTS, 1, 0.0, 5000.0, 450.0, "What the power cells deliver; constant draw above it drains the reserve"),
	&"power_capacity_j": StatDef.make(Group.SYSTEMS, "Power reserve", JOULES, 1, 1000.0, 1000000.0, 60000.0, "Stored energy for actives and brown-outs"),
	&"heat_dissipation_w": StatDef.make(Group.SYSTEMS, "Cooling", WATTS, 1, 0.0, 5000.0, 380.0, "Heat the body sheds; more heat in than this builds up"),
	&"capacity": StatDef.make(Group.SYSTEMS, "Capacity", POINTS, 1, 0.0, 60.0, 16.0, "Loadout budget: parts cost 0-4 each"),
}

static func has(stat: StringName) -> bool:
	return DEFS.has(stat)


static func keys() -> Array[StringName]:
	var out: Array[StringName] = []
	for k: StringName in DEFS:
		out.append(k)
	return out


static func _def(stat: StringName) -> StatDef:
	if DEFS.has(stat):
		return DEFS[stat]
	return StatDef.make(Group.SYSTEMS, String(stat), MULT, 1, -INF, INF, 1.0, "")


static func group(stat: StringName) -> int:
	return _def(stat).group


static func label(stat: StringName) -> String:
	return _def(stat).label


static func format_kind(stat: StringName) -> int:
	return _def(stat).fmt


## +1: more is better; -1: less is better.
static func better(stat: StringName) -> int:
	return _def(stat).better


static func min_value(stat: StringName) -> float:
	return _def(stat).min_value


static func max_value(stat: StringName) -> float:
	return _def(stat).max_value


static func default_base(stat: StringName) -> float:
	return _def(stat).base


static func reads(stat: StringName) -> String:
	return _def(stat).reads


static func in_group(g: int) -> Array[StringName]:
	var out: Array[StringName] = []
	for k: StringName in keys():
		if group(k) == g:
			out.append(k)
	return out


## The value as the body-status screen shows it.
static func format(stat: StringName, v: float) -> String:
	match format_kind(stat):
		MULT:
			return "×%.2f" % v
		WATTS:
			return "%.0f W" % v
		KG:
			return "%.0f kg" % v
		SECONDS:
			return "%.1f s" % v
		JOULES:
			return "%.0f kJ" % (v * 0.001)
	if absf(v - roundf(v)) < 0.01:
		return "%d" % roundi(v)
	return "%.1f" % v


## A modifier as a short line: "+20 health", "agility ×1.15".
static func describe_modifier(m: StatModifier) -> String:
	var parts: PackedStringArray = PackedStringArray()
	if not is_zero_approx(m.add):
		var unit: String = ""
		match format_kind(m.stat):
			WATTS:
				unit = " W"
			KG:
				unit = " kg"
			SECONDS:
				unit = " s"
			JOULES:
				parts.append("%+.0f kJ %s" % [m.add * 0.001, label(m.stat).to_lower()])
		if format_kind(m.stat) != JOULES:
			var num: String = ("%+d" % roundi(m.add)) if absf(m.add - roundf(m.add)) < 0.01 else ("%+.2f" % m.add)
			parts.append("%s%s %s" % [num, unit, label(m.stat).to_lower()])
	if not is_equal_approx(m.mul, 1.0):
		parts.append("%s ×%.2f" % [label(m.stat).to_lower(), m.mul])
	return ", ".join(parts)


## Whether this modifier makes the body better (+1), worse (-1) or neither.
static func modifier_sign(m: StatModifier) -> int:
	var b: float = 1.0
	var after: float = (b + m.add / maxf(absf(default_base(m.stat)), 1.0)) * m.mul
	if is_equal_approx(after, b):
		return 0
	return better(m.stat) * (1 if after > b else -1)
