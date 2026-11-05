class_name PartData
extends Resource
## A physical component installed in the augmented body (docs/design.md
## §3.2). Parts don't script their combinations: they add mass, draw or make
## power, make or remove heat, cost loadout capacity, change named stats and
## add visible hardware. BodyModel sums them; systems read the totals.
## Data lives in data/body/parts/*.tres.

enum Location { HEAD, EYES, NERVOUS, SKELETON, MUSCLE, TORSO, ARMS, HANDS, LEGS, SPINE, SKIN, BLOOD }

@export var id: StringName = &""
## Technical hardware name, e.g. "NW-4 Nanoweave Fiber Vest".
@export var display_name: String = ""
@export_multiline var description: String = ""
@export var location: Location = Location.TORSO

@export_group("Physical")
## kg added to the body.
@export var mass_kg: float = 0.0
## Watts drawn all the time (negative = the part supplies power).
@export var power_draw_w: float = 0.0
## Watts of heat made all the time (negative = the part removes heat).
@export var heat_w: float = 0.0
## Loadout capacity used (the body has a fixed budget).
@export var capacity: int = 1

@export_group("Effects")
@export var modifiers: Array[StatModifier] = []
@export var visuals: Array[PartVisual] = []


func is_active() -> bool:
	return false
