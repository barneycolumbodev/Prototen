class_name BodyModel
extends RefCounted
## The augmented body as numbers (docs/design.md §3.2, §3.6): the frame's
## base values plus everything the installed parts add.
##
## - Totals: mass and capacity of every installed part; constant power draw
##   and heat of the parts that are online.
## - Stats (Stats.DEFS): (base + Σ add) × Π mul over the online parts, clamped.
## - Requirements: a part whose StatRequirements aren't met goes offline (no
##   power, heat or stat changes). Taking one part offline can take others
##   with it, so this repeats until nothing changes.
## - Derived values, the relationships between stats: usable strength
##   (capped by structure), load (mass ÷ usable strength) and the mobility
##   it costs, link range (connectivity), signature (raised by stored heat),
##   power headroom.
## - Runtime pools: a power reserve (the supply recharges it, parts drain it;
##   empty = brown-out, actives that draw power can't start) and stored heat
##   (shed by cooling; full = overheated, no regen, a hot signature).

signal changed

var frame: PlayerBodyConfig
var loadout: BodyLoadout
var mass_kg: float = 0.0
var power_draw_w: float = 0.0
var heat_w: float = 0.0
var capacity_used: int = 0
## Joules in the reserve, and stored heat in joules.
var power_j: float = 0.0
var heat_j: float = 0.0
## Installed parts that work, and why the others don't (id -> reason).
var online: Array[PartData] = []
var offline: Dictionary[StringName, String] = {}

var _stats: Dictionary[StringName, float] = {}
var _active_draw_w: float = 0.0
var _active_heat_w: float = 0.0


func _init(p_frame: PlayerBodyConfig, p_loadout: BodyLoadout) -> void:
	frame = p_frame
	loadout = p_loadout if p_loadout else BodyLoadout.new()
	rebuild()
	power_j = stat(&"power_capacity_j")


func base(s: StringName) -> float:
	match s:
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
		&"power_supply_w":
			return frame.power_supply_w
		&"power_capacity_j":
			return frame.power_capacity_j
		&"heat_dissipation_w":
			return frame.heat_dissipation_w
		&"capacity":
			return float(frame.capacity)
	if frame.stat_bases.has(s):
		return frame.stat_bases[s]
	return Stats.default_base(s)


## Recomputes totals, requirements and stats from the loadout (after a part
## is added or removed).
func rebuild() -> void:
	var parts: Array[PartData] = []
	for p: PartData in loadout.parts:
		if p != null:
			parts.append(p)
	var on: Array[PartData] = parts.duplicate()
	offline.clear()
	for _i: int in 12:
		_compute(on)
		var removed: bool = false
		for p: PartData in on.duplicate():
			var why: String = unmet(p)
			if why != "":
				on.erase(p)
				offline[p.id] = why
				removed = true
		if not removed:
			break
	_compute(on)
	online = on
	mass_kg = frame.base_mass_kg
	capacity_used = 0
	for p: PartData in parts:
		mass_kg += p.mass_kg
		capacity_used += p.capacity
	power_draw_w = 0.0
	heat_w = 0.0
	for p: PartData in on:
		power_draw_w += p.power_draw_w
		heat_w += p.heat_w
	power_j = minf(power_j, stat(&"power_capacity_j"))
	changed.emit()


func _compute(parts: Array[PartData]) -> void:
	var adds: Dictionary[StringName, float] = {}
	var muls: Dictionary[StringName, float] = {}
	for p: PartData in parts:
		for m: StatModifier in p.modifiers:
			if m == null:
				continue
			if not Stats.has(m.stat):
				push_warning("BodyModel: part %s changes unknown stat '%s'" % [p.id, m.stat])
				continue
			adds[m.stat] = adds.get(m.stat, 0.0) + m.add
			muls[m.stat] = muls.get(m.stat, 1.0) * m.mul
	_stats.clear()
	for s: StringName in Stats.keys():
		var v: float = (base(s) + adds.get(s, 0.0)) * muls.get(s, 1.0)
		_stats[s] = clampf(v, Stats.min_value(s), Stats.max_value(s))


func stat(s: StringName) -> float:
	return _stats.get(s, base(s))


## "" if the part's requirements are met by the current stats, else why not.
func unmet(p: PartData) -> String:
	var missing: PackedStringArray = PackedStringArray()
	for r: StatRequirement in p.requirements:
		if r and not r.met(stat(r.stat)):
			missing.append(r.describe())
	return "" if missing.is_empty() else "needs " + ", ".join(missing)


func is_online(id: StringName) -> bool:
	for p: PartData in online:
		if p.id == id:
			return true
	return false


func capacity_total() -> int:
	return roundi(stat(&"capacity"))


func capacity_left() -> int:
	return capacity_total() - capacity_used


## What's wrong with the loadout: over capacity, too many parts in one
## place, parts offline, power over budget. Empty = good to go.
func problems() -> PackedStringArray:
	var out: PackedStringArray = PackedStringArray()
	if capacity_used > capacity_total():
		out.append("Over capacity: %d / %d" % [capacity_used, capacity_total()])
	var counts: Dictionary[int, int] = {}
	for p: PartData in loadout.parts:
		if p:
			counts[p.location] = counts.get(p.location, 0) + 1
	for loc: int in counts:
		if counts[loc] > PartData.slots_for(loc):
			out.append("%s holds %d, has %d" % [PartData.location_name(loc), PartData.slots_for(loc), counts[loc]])
	for p: PartData in loadout.parts:
		if p and offline.has(p.id):
			out.append("%s offline: %s" % [p.display_name, offline[p.id]])
	if power_draw_w > stat(&"power_supply_w"):
		out.append("Draw %.0f W over supply %.0f W: the reserve drains" % [power_draw_w, stat(&"power_supply_w")])
	return out


# ------------------------------------------------------------------ derived

## Strength the body can use: muscles stronger than the skeleton can take
## are throttled to structure × strength_per_structure.
func usable_strength() -> float:
	return minf(stat(&"strength"), stat(&"structure") * frame.strength_per_structure)


func strength_capped() -> bool:
	return stat(&"strength") > usable_strength() + 0.001


## The mass the muscles feel (kg): mass ÷ usable strength.
func load_kg() -> float:
	return mass_kg / maxf(usable_strength(), 0.1)


## Multiplier on speed, jump and wall-run from the load: 1 up to
## load_free_kg, falling to 1 - load_max_penalty over load_span_kg; a small
## bonus for a light body.
func load_scale() -> float:
	var l: float = load_kg()
	if l > frame.load_free_kg:
		return 1.0 - clampf((l - frame.load_free_kg) / maxf(frame.load_span_kg, 1.0), 0.0, 1.0) * frame.load_max_penalty
	var t: float = clampf((frame.load_free_kg - l) / maxf(frame.load_free_kg - frame.load_light_kg, 1.0), 0.0, 1.0)
	return 1.0 + frame.load_light_bonus * t


## How far (m) a remote-linked part (a drone) can go before the link drops.
func link_range_m() -> float:
	return stat(&"connectivity") * frame.link_m_per_connectivity


## Signature now: the stat, raised by stored heat.
func signature_now() -> float:
	return stat(&"signature") * (1.0 + frame.heat_signature * heat_fraction())


## How fast enemies spot you, relative to the base body: silhouette × signature.
func detection_scale() -> float:
	return stat(&"profile") * signature_now()


func overheated() -> bool:
	return heat_j >= frame.heat_capacity_j - 0.5


## The reserve is empty: powered actives can't start.
func brownout() -> bool:
	return power_j <= 0.5


## Watts left over: supply minus what's drawn now.
func headroom_w() -> float:
	return stat(&"power_supply_w") - current_draw_w()


## Proficiency with a weapon class (WeaponData.WeaponClass).
func proficiency(weapon_class: int) -> float:
	match weapon_class:
		WeaponData.WeaponClass.HANDGUN:
			return stat(&"handgun")
		WeaponData.WeaponClass.SHOTGUN:
			return stat(&"shotgun")
		WeaponData.WeaponClass.HEAVY:
			return stat(&"heavy")
	return stat(&"rifle")


## Recoil multiplier for a weapon class: the recoil stat ÷ proficiency;
## heavy weapons are also held by muscle (÷ √usable strength) and bone
## (÷ √structure).
func recoil_scale(weapon_class: int) -> float:
	var r: float = stat(&"recoil") / maxf(proficiency(weapon_class), 0.1)
	if weapon_class == WeaponData.WeaponClass.HEAVY:
		r /= sqrt(maxf(usable_strength() * stat(&"structure"), 0.1))
	return r


## Power/heat while an active part runs (it calls this on start and stop).
func set_active_load(draw_w: float, heat: float) -> void:
	_active_draw_w = draw_w
	_active_heat_w = heat


## Total draw right now (W): constant parts plus running actives.
func current_draw_w() -> float:
	return power_draw_w + _active_draw_w


func tick(delta: float) -> void:
	var net_w: float = stat(&"power_supply_w") - current_draw_w()
	power_j = clampf(power_j + net_w * delta, 0.0, stat(&"power_capacity_j"))
	var heat_in: float = heat_w + _active_heat_w
	heat_j = clampf(heat_j + (heat_in - stat(&"heat_dissipation_w")) * delta, 0.0, frame.heat_capacity_j)


func power_fraction() -> float:
	return power_j / maxf(stat(&"power_capacity_j"), 1.0)


func heat_fraction() -> float:
	return heat_j / maxf(frame.heat_capacity_j, 1.0)
