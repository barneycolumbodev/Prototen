class_name BodyLoadout
extends Resource
## The parts installed in a body (docs/design.md §3.1: no classes, a
## character is the set of parts plus gear). data/body/loadout_default.tres
## is what a new player starts with; presets are in data/body/presets/; the
## loadout screen (body status) edits a copy and saves it to user://.

@export var display_name: String = "Operative"
@export_multiline var description: String = ""
@export var parts: Array[PartData] = []


## Most actives a body can carry: one per D-pad direction.
const MAX_ACTIVES: int = 3


## The actives in D-pad order: the first is on D-pad left, then down, right
## (owner, 2026-11-07: three actives, LB fires the selected one).
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


## D-pad slot of an installed active (1 = left, 2 = down, 3 = right); 0 if
## it isn't installed.
func slot_of(id: StringName) -> int:
	var acts: Array[ActivePartData] = actives()
	for i: int in acts.size():
		if acts[i].id == id:
			return i + 1
	return 0


## Moves an installed active to the next D-pad direction (it swaps places
## with the active there; wraps round). Returns its new slot.
func cycle_slot(id: StringName) -> int:
	var acts: Array[ActivePartData] = actives()
	var from: int = slot_of(id) - 1
	if from < 0 or acts.size() < 2:
		return from + 1
	var to: int = (from + 1) % acts.size()
	var a: int = parts.find(acts[from])
	var b: int = parts.find(acts[to])
	parts[a] = acts[to]
	parts[b] = acts[from]
	return to + 1


## Installs `part`. If its location is full, the part installed there first
## comes out to make room; a part on the same mount (the right forearm)
## comes out; a fourth active pushes out the one installed first. Returns
## what was removed.
func install(part: PartData) -> Array[PartData]:
	var removed: Array[PartData] = []
	if part == null or has_part(part.id):
		return removed
	# The same mount first (the other part on that arm), then room in the location.
	if part.mount != &"":
		for p: PartData in parts.duplicate():
			if p.mount == part.mount and not p.fixed:
				parts.erase(p)
				removed.append(p)
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
	if part.is_active():
		var acts: Array[ActivePartData] = actives()
		while acts.size() >= MAX_ACTIVES:
			parts.erase(acts[0])
			removed.append(acts[0])
			acts.remove_at(0)
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
