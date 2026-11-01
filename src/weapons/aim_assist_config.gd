class_name AimAssistConfig
extends Resource
## Controller aim assist in layers (CLAUDE.md §9.4). data/input/aim_assist.tres.
## Targets join the `aim_assist_targets` group and expose aim points
## (`aim_points() -> PackedVector3Array`, e.g. head and chest).

@export var enabled: bool = true
@export_group("Slowdown")
## Look speed multiplier when the crosshair is on a target (1 = none).
@export_range(0.1, 1.0) var slowdown: float = 0.55
## Angular radius around an aim point where slowdown applies, degrees,
## at 10 m (it shrinks with distance so far targets aren't sticky).
@export_range(0.0, 15.0) var slowdown_radius_deg: float = 4.0
@export_group("Pull while aimed")
## Rotation toward the target while aiming and moving the stick, degrees/s.
@export_range(0.0, 30.0) var pull_deg_s: float = 6.0
@export_range(0.0, 15.0) var pull_radius_deg: float = 3.0
## Pull only works while the stick moves (no auto-aim on a still stick).
@export_range(0.0, 1.0) var pull_needs_input: float = 0.05
@export_group("Range")
@export_range(1.0, 200.0) var max_distance: float = 60.0
