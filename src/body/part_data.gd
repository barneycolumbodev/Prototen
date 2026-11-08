class_name PartData
extends Resource
## A physical component installed in the augmented body (docs/design.md
## §3.2, §3.6). Parts don't script their combinations: they add mass, draw or
## make power, make or remove heat, cost loadout capacity, change named stats
## (Stats.DEFS) and add visible hardware. BodyModel sums them; systems read
## the totals. Some need other stats first (`requirements`).
## Data lives in data/body/parts/*.tres.

## Where it goes. Each location holds SLOTS[location] parts (default 1).
## New values go at the end: .tres files store the number.
enum Location { HEAD, EYES, NERVOUS, SKELETON, MUSCLE, TORSO, ARMS, HANDS, LEGS, SPINE, SKIN, BLOOD, EARS, ORGANS, SUIT }

## How many parts each location holds (others: 1). Two nervous-system
## co-processors, two organ grafts, two arm prosthetics.
const SLOTS: Dictionary[int, int] = {
	Location.NERVOUS: 2,
	Location.ORGANS: 2,
	Location.ARMS: 2,
}

## Short names for the loadout screen, in Location order.
const LOCATION_NAMES: Array[String] = ["Cranial", "Eyes", "Nervous system", "Skeleton", "Musculature", "Torso armour", "Arms",
	"Hands", "Legs", "Spine", "Skin", "Blood", "Inner ear", "Organs", "Suit"]

@export var id: StringName = &""
## Technical hardware name, e.g. "NW-4 Nanoweave Fiber Vest".
@export var display_name: String = ""
@export_multiline var description: String = ""
@export var location: Location = Location.TORSO
## Part of the base body (the graft suit): always installed, can't be removed.
@export var fixed: bool = false

@export_group("Physical")
## kg added to the body.
@export var mass_kg: float = 0.0
## Watts drawn all the time (negative = the part supplies power).
@export var power_draw_w: float = 0.0
## Watts of heat made all the time (negative = the part removes heat).
@export var heat_w: float = 0.0
## Loadout capacity used (the body has a budget, the `capacity` stat).
@export var capacity: int = 1

@export_group("Effects")
@export var modifiers: Array[StatModifier] = []
## Stats the part needs before it comes online.
@export var requirements: Array[StatRequirement] = []
## How other stats change what this part does ("scales with processing:
## operative speed in slow motion"). Shown on the loadout screen.
@export_multiline var synergy: String = ""
@export var visuals: Array[PartVisual] = []


func is_active() -> bool:
	return false


static func slots_for(loc: int) -> int:
	return SLOTS[loc] if SLOTS.has(loc) else 1


static func location_name(loc: int) -> String:
	return LOCATION_NAMES[loc] if loc >= 0 and loc < LOCATION_NAMES.size() else "?"
