class_name Doctrine
extends Resource
## The baseline character a Survival run starts from (docs/design.md §8.2,
## §8.5): a few passive parts on the bare graft suit, the actives that body
## can run (the start screen offers only these, at Mk I), and the tags whose
## drops it favours.

@export var display_name: String = "Ghost"
@export_multiline var description: String = ""
## Passives installed at the start (the suit is always there).
@export var parts: Array[PartData] = []
## Starting actives on offer: each must come online with `parts`.
@export var starter_actives: Array[ActivePartData] = []
## Favoured tags: drops with the first are ×primary_bias, the second ×secondary_bias.
@export var primary_tag: StringName = &"stealth"
@export var secondary_tag: StringName = &"mobility"
@export_range(1.0, 10.0) var primary_bias: float = 3.0
@export_range(1.0, 10.0) var secondary_bias: float = 2.0


## Weight multiplier for an item with these tags (the best matching tag).
func bias(tags: Array[StringName]) -> float:
	var b: float = 1.0
	if primary_tag in tags:
		b = maxf(b, primary_bias)
	if secondary_tag in tags:
		b = maxf(b, secondary_bias)
	return b
