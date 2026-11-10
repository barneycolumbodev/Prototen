class_name PartLibrary
extends Resource
## Every part the loadout screen offers, in screen order
## (data/body/part_library.tres, written by tools/parts/gen_parts.py).
## A list instead of a folder scan: exported Android builds remap .tres files.

@export var parts: Array[PartData] = []


func find(id: StringName) -> PartData:
	for p: PartData in parts:
		if p and p.id == id:
			return p
	return null


func at(loc: int) -> Array[PartData]:
	var out: Array[PartData] = []
	for p: PartData in parts:
		if p and p.location == loc:
			out.append(p)
	return out


## Every active part, in library order.
func actives() -> Array[ActivePartData]:
	var out: Array[ActivePartData] = []
	for p: PartData in parts:
		var a: ActivePartData = p as ActivePartData
		if a:
			out.append(a)
	return out


## Builds a loadout from saved part ids (unknown ids are skipped); fixed
## parts are always included.
func loadout_from_ids(ids: PackedStringArray, name: String = "Custom") -> BodyLoadout:
	var lo: BodyLoadout = BodyLoadout.new()
	lo.display_name = name
	for p: PartData in parts:
		if p and p.fixed:
			lo.parts.append(p)
	for id: String in ids:
		var p: PartData = find(StringName(id))
		if p and not lo.has_part(p.id):
			lo.install(p)
	return lo
