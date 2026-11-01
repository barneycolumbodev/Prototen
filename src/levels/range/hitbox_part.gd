class_name HitboxPart
extends StaticBody3D
## One damage zone of a target (head, chest, left shin...). Forwards bullet
## contacts to its target, which owns health and reactions.
## Carries metadata `zone` and `surface` for Ballistics.

var target: Node


func on_ballistic_hit(hit: BallisticHit) -> void:
	if target and target.has_method(&"on_part_hit"):
		target.call(&"on_part_hit", self, hit)
