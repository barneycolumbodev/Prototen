extends StaticBody3D
## A steel plate in an Enforcer's carrier (data/surfaces/armor_plate.tres).
## Ballistics decides whether a round gets through; the wearer only hears
## about the hit (stagger, armour marker).

var target: Node


func on_ballistic_hit(hit: BallisticHit) -> void:
	if target and target.has_method(&"on_plate_hit"):
		target.call(&"on_plate_hit", self, hit)
