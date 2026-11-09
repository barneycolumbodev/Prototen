class_name BodyLoadout
extends Resource
## The parts installed in a body (docs/design.md §3.1: no classes, a
## character is the set of parts plus gear). data/body/loadout_default.tres
## is what a new player starts with; presets are in data/body/presets/; the
## loadout screen (body status) edits a copy and saves it to user://.

@export var display_name: String = "Operative"
@export_multiline var description: String = ""
@export var parts: Array[PartData] = []


func actives() -> Array[ActivePartData]:
	var out: Array[ActivePartData] = []
	for p: PartData in parts:
		var a: ActivePartData = p as ActivePartData
		if a:
			out.append(a)
	return out


func has_part(id: StringName) -> bool:
	return find(id) != null


func find(id: StringName) -> PartData:
	for p: PartData in parts:
		if p and p.id == id:
			return p
	return null


func parts_at(loc: int) -> Array[PartData]:
	var out: Array[PartData] = []
	for p: PartData in parts:
		if p and p.location == loc:
			out.append(p)
	return out


## Installs `part`. If its location is full, the part installed there first
## comes out to make room (and an active wanting a taken D-pad slot pushes
## the other active out). Returns what was removed.
func install(part: PartData) -> Array[PartData]:
	var removed: Array[PartData] = []
	if part == null or has_part(part.id):
		return removed
	var here: Array[PartData] = parts_at(part.location)
	while here.size() >= PartData.slots_for(part.location):
		var out: PartData = null
		for p: PartData in here:
			if not p.fixed:
				out = p
				break
		if out == null:
			return removed  # only fixed parts there
		parts.erase(out)
		here.erase(out)
		removed.append(out)
	var act: ActivePartData = part as ActivePartData
	if act:
		for a: ActivePartData in actives():
			if a.slot == act.slot:
				parts.erase(a)
				removed.append(a)
	parts.append(part)
	return removed


## Takes a part out (not fixed ones). Returns whether it was removed.
func remove(id: StringName) -> bool:
	var p: PartData = find(id)
	if p == null or p.fixed:
		return false
	parts.erase(p)
	return true


func ids() -> PackedStringArray:
	var out: PackedStringArray = PackedStringArray()
	for p: PartData in parts:
		if p:
			out.append(String(p.id))
	return out


## A copy that can be edited without touching the resource on disk.
func copy() -> BodyLoadout:
	var lo: BodyLoadout = BodyLoadout.new()
	lo.display_name = display_name
	lo.description = description
	lo.parts = parts.duplicate()
	return lo
