class_name DaoConfig
extends Resource
## The Dao swordsman's guard and his two cuts (docs/design.md §8.8b). Every
## ability is hardware: the guard is a steel plate grafted into his left
## forearm. Tuning: data/enemies/dao_swordsman.tres.

## The guard as a hitbox on the chest bone while he holds it (unscaled rig
## metres, chest frame: X his left, Y up the chest, Z forward). Rounds from
## the front hit it before they reach him.
@export var guard_size: Vector3 = Vector3(0.5, 0.86, 0.05)
@export var guard_center: Vector3 = Vector3(0.02, 0.12, 0.44)
## A round up to this energy (J) is turned aside (it ricochets); above it,
## it goes through the plate (the GX-4's slug).
@export_range(500.0, 20000.0) var deflect_max: float = 6000.0
## What the guard can take (J of rounds turned aside) before it breaks: he
## staggers and drops it for `broken_time`. It recovers at `regen` J/s.
@export_range(500.0, 50000.0) var guard_energy: float = 7000.0
@export_range(0.0, 10000.0) var guard_regen: float = 1500.0
@export_range(0.2, 5.0) var broken_time: float = 2.2
## Walking in behind the guard (m/s).
@export_range(0.5, 6.0) var guard_speed: float = 2.2
## The slash (close) and the lunge (a step further out).
@export_range(0.15, 1.5) var slash_windup: float = 0.42
@export_range(0.8, 4.0) var slash_reach: float = 2.3
@export_range(30.0, 270.0) var slash_arc_deg: float = 130.0
@export_range(0.0, 500.0) var slash_damage: float = 48.0
@export_range(1.0, 6.0) var slash_range: float = 2.8
@export_range(0.15, 1.5) var lunge_windup: float = 0.48
@export_range(0.8, 6.0) var lunge_reach: float = 2.2
@export_range(20.0, 180.0) var lunge_arc_deg: float = 60.0
@export_range(0.0, 500.0) var lunge_damage: float = 60.0
@export_range(0.0, 20.0) var lunge_speed: float = 9.0
## He lunges from between slash_range and this (m).
@export_range(2.0, 10.0) var lunge_range: float = 5.2
