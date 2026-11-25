class_name AerosolCan
extends StaticBody3D
## Precision weak-point hitbox on a Triad Flamer's pressurized aerosol can
## (docs/design.md §8.8c). Shooting it (ballistics, plasma, Dragon's Breath,
## Gauss, whip, setae) ruptures the can into a fuel-air fireball that engulfs
## the Flamer and can ignite nearby enemies.

var target: Node
var detonated: bool = false


func on_ballistic_hit(hit: BallisticHit) -> void:
	if detonated:
		return
	if target and target.has_method(&"on_can_hit"):
		target.call(&"on_can_hit", self, hit)


func on_burn(hit: BallisticHit) -> void:
	on_ballistic_hit(hit)
