class_name MarksmanConfig
extends Resource
## The Marksman's tell (docs/design.md §8.8d): a laser on the target and a
## glint off the scope before every shot. Tuning: data/enemies/marksman.tres.

## Seconds the laser is on the target before the shot; it stops tracking
## `lock_time` before (a step sideways then takes the round off you).
@export_range(0.3, 5.0) var aim_time: float = 1.6
@export_range(0.0, 1.5) var lock_time: float = 0.3
## How fast the laser follows the operative (deg/s).
@export_range(5.0, 360.0) var track_deg: float = 55.0
@export var laser_color: Color = Color(1.0, 0.12, 0.08)
## The glint: size (m at 1 m, kept on screen by distance) and its colour.
@export_range(0.0, 2.0) var glint_size: float = 0.09
@export var glint_color: Color = Color(1.0, 0.95, 0.85)
## Where the glint sits on the gun model (assets/weapons/enemy/type79.gltf, Godot axes).
@export var scope_front: Vector3 = Vector3(0.245, 0.104, -0.012)
## He moves to another spot after this many shots from one place.
@export_range(1, 10) var shots_per_spot: int = 2
## Score bonus per metre of height over the operative when he picks cover.
@export_range(0.0, 10.0) var height_bonus: float = 2.5
