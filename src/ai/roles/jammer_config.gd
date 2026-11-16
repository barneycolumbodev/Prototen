class_name JammerConfig
extends Resource
## The anti-augment specialist's jammer backpack (docs/design.md §8.8g).
## Within its radius the Shrike drone loses its link and falls, and the
## thermoptic shroud can't hold. Shooting the pack kills it.

@export_range(1.0, 60.0) var radius: float = 16.0
## The pack as a hitbox on the chest bone (unscaled rig metres, chest frame:
## X his left, Y up the chest, Z forward; the pack is behind him).
@export var box_size: Vector3 = Vector3(0.3, 0.38, 0.14)
@export var box_center: Vector3 = Vector3(0.0, 0.005, -0.215)
## Damage the pack takes before it dies (sparks, a pop, the lamps go out).
@export_range(1.0, 1000.0) var health: float = 60.0
