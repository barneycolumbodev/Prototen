class_name RunItem
extends Resource
## One thing a Survival supply drop can bring (docs/design.md §8.4): a gun
## (WeaponData) or a part (PartData; actives drop at Mk I). Its tags steer
## the odds (doctrine and affinity, §8.5). Actives also carry their Mk I and
## Mk II tuning here (§8.3): property overrides on the part's resource; Mk III
## is the part as built, the same as in Sandbox.
## Generated into data/run/survival.tres by tools/run/gen_pool.py.

enum Kind { WEAPON, ACTIVE, PASSIVE }

## The gun or the part.
@export var item: Resource
## `mobility`, `stealth`, `heavy`, `precision`, `close`, `tech`.
@export var tags: Array[StringName] = []
## Relative odds inside its kind before tags (1 = ordinary).
@export_range(0.0, 10.0) var weight: float = 1.0
## Doesn't drop before this wave.
@export_range(1, 100) var min_wave: int = 1
## Only a boss carries it (§8.7): never in an ordinary drop.
@export var boss_only: bool = false
## One line for the drop card (guns; parts use their own description if empty).
@export_multiline var blurb: String = ""
@export_group("Marks (actives)")
## Overrides for Mk I and Mk II (property → value on the part).
@export var mk1: Dictionary[StringName, Variant] = {}
@export var mk2: Dictionary[StringName, Variant] = {}

const MAX_MARK: int = 3
const MARK_NAMES: Array[String] = ["", "Mk I", "Mk II", "Mk III"]


func kind() -> Kind:
	if item is WeaponData:
		return Kind.WEAPON
	if item is ActivePartData:
		return Kind.ACTIVE
	return Kind.PASSIVE


func id() -> StringName:
	if item is WeaponData:
		return StringName((item as WeaponData).resource_path.get_file().get_basename())
	var p: PartData = item as PartData
	return p.id if p else &""


func display_name() -> String:
	if item is WeaponData:
		return (item as WeaponData).display_name
	var p: PartData = item as PartData
	return p.display_name if p else "?"


func description() -> String:
	if blurb != "":
		return blurb
	var p: PartData = item as PartData
	return p.description if p else ""


func has_tag(t: StringName) -> bool:
	return t in tags


func overrides(mark: int) -> Dictionary[StringName, Variant]:
	if mark == 1:
		return mk1
	if mark == 2:
		return mk2
	return {}


## The active at `mark` (1..3): Mk III is the part itself; Mk I and II are
## copies with their overrides set. Its name says the mark.
func active_at(mark: int) -> ActivePartData:
	var a: ActivePartData = item as ActivePartData
	if a == null:
		return null
	mark = clampi(mark, 1, MAX_MARK)
	if mark >= MAX_MARK:
		return a
	var copy: ActivePartData = a.duplicate() as ActivePartData
	for k: StringName in overrides(mark):
		copy.set(k, overrides(mark)[k])
	copy.display_name = "%s %s" % [a.display_name, MARK_NAMES[mark]]
	return copy
