class_name ShieldConfig
extends Resource
## The Shield man's ballistic shield (docs/design.md §8.8e). A stolen police
## shield on his chest, held out by the left hand; the Type 54 comes round
## its right edge. Tuning: data/enemies/shield_man.tres.

## The shield as a hitbox on the chest bone (unscaled rig metres, the chest
## bone's frame: X his left, Y up the chest, Z forward), matching
## raw_assets/characters/triad_gear (kit "shield").
@export var box_size: Vector3 = Vector3(0.56, 0.95, 0.03)
@export var box_center: Vector3 = Vector3(0.03, 0.05, 0.41)
## A round carrying more than this (J) knocks the shield aside: he staggers
## for `stagger_time` and the body behind is open.
@export_range(500.0, 20000.0) var stagger_energy: float = 2600.0
@export_range(0.2, 3.0) var stagger_time: float = 0.9
## Energy (J) the shield takes before it cracks and he throws it down. A
## Five-seveN round is ~470 J, a rifle round ~2,000, an MG42 round ~3,600.
@export_range(1000.0, 200000.0) var integrity: float = 30000.0
## How fast he turns the shield after the operative (deg/s): flanking works.
@export_range(30.0, 720.0) var turn_deg: float = 120.0
## He walks in to this distance (m) and holds there, pistol out.
@export_range(2.0, 30.0) var hold_range: float = 7.0
## Men with guns within this (m) of him fall in behind the shield.
@export_range(0.0, 30.0) var stack_range: float = 12.0
## The shield bash: inside this range he shoves the operative back.
@export_range(0.0, 4.0) var bash_range: float = 2.2
@export_range(0.0, 200.0) var bash_damage: float = 14.0
@export_range(0.0, 20.0) var bash_push: float = 7.5
@export_range(0.5, 10.0) var bash_cooldown: float = 2.2
