class_name ThrowerConfig
extends Resource
## Something an enemy throws (docs/design.md §8.8c, §8.8g): the Firebomber's
## molotovs, the anti-augment specialist's EMP grenades. Tuning:
## data/enemies/firebomber.tres, data/enemies/anti_augment.tres.

enum Kind { MOLOTOV, EMP }
@export var kind: Kind = Kind.MOLOTOV
## The thrown thing's model (assets/weapons/enemy/molotov.gltf, emp.gltf).
@export var model: PackedScene
## Throws from this far (m) to this far.
@export_range(2.0, 60.0) var min_range: float = 7.0
@export_range(4.0, 80.0) var max_range: float = 26.0
## Seconds between throws (min, max); how many he carries (0: no limit).
@export var cooldown: Vector2 = Vector2(4.0, 6.5)
@export_range(0, 50) var count: int = 6
## The first throw comes this long after he first knows where the operative is.
@export_range(0.0, 10.0) var first_delay: float = 1.5
## Seconds from the start of the throw to the release (matched to the clip).
@export_range(0.2, 2.0) var release_time: float = 0.56
## Flight: the arc's time in the air per 10 m (s), and how far off it lands (m at 20 m).
@export_range(0.3, 3.0) var flight_per_10m: float = 0.75
@export_range(0.0, 5.0) var spread: float = 1.2
## He leads a moving target by this share of where he'll be on landing.
@export_range(0.0, 1.5) var lead: float = 0.6
## This much damage while he winds up makes him drop it (a molotov: at his
## own feet, lit).
@export_range(1.0, 200.0) var interrupt: float = 25.0

@export_group("Fire (molotov)")
## The pool of burning fuel: radius (m), how long it burns, damage per second
## to the operative (bare suit) and how long a man in it burns.
@export_range(0.5, 6.0) var fire_radius: float = 2.4
@export_range(1.0, 30.0) var fire_time: float = 8.0
@export_range(0.0, 200.0) var fire_dps: float = 22.0
@export_range(0.0, 20.0) var ignite_time: float = 4.0
@export_range(0.0, 100.0) var ignite_dps: float = 18.0

@export_group("EMP")
## The pulse: radius (m), and how long the operative's actives stay down.
@export_range(1.0, 20.0) var emp_radius: float = 7.5
@export_range(0.0, 20.0) var emp_stall: float = 5.0
## Fuse after it lands (s).
@export_range(0.0, 3.0) var emp_fuse: float = 0.7
