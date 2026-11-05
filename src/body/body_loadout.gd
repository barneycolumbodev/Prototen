class_name BodyLoadout
extends Resource
## The parts installed in a body (docs/design.md §3.1: no classes, a
## character is the set of parts plus gear). data/body/loadout_default.tres
## is what the player starts with until the loadout screen exists (M2).

@export var display_name: String = "Operative"
@export var parts: Array[PartData] = []


func actives() -> Array[ActivePartData]:
	var out: Array[ActivePartData] = []
	for p: PartData in parts:
		var a: ActivePartData = p as ActivePartData
		if a:
			out.append(a)
	return out


func has_part(id: StringName) -> bool:
	for p: PartData in parts:
		if p.id == id:
			return true
	return false
