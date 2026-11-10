class_name ThermopticShroudData
extends ActivePartData
## TC-4 Thermoptic Shroud (2026-11-10): a skin of phased emitters that bends
## light round the body and holds its heat in. LB (with it selected) raises
## it, LB again drops it. Enemies can't see the operative beyond
## `reveal_m`; they still hear him. Firing breaks it for a moment and costs
## charge. It traps heat (active_heat_w): when the body overheats it fails,
## so cooling decides how long it holds. Tuning in
## data/body/parts/tc4_thermoptic_shroud.tres.

@export_group("Stealth")
## Inside this distance (m) they see the shimmer; times the signature stat.
@export var reveal_m: float = 3.0
## Seconds visible after firing a shot, and the charge each shot costs.
@export var shot_reveal_time: float = 1.1
@export var shot_cost: float = 1.2
## Seconds visible after taking a hit.
@export var hit_reveal_time: float = 0.6

@export_group("Look")
## How see-through your own arms and gun are (0..1).
@export_range(0.0, 1.0) var arm_transparency: float = 0.8
@export var tint: Color = Color(0.5, 0.75, 1.0, 0.2)
