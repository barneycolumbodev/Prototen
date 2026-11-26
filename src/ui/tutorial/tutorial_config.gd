class_name TutorialConfig
extends Resource
## Tuning for boot camp and the Survival first-time tips (docs/design.md §8.11).
## Positions are in the test range (spawn 0,0,12 facing north, -Z).

@export_group("Boot camp: markers and targets")
@export var walk_marker: Vector3 = Vector3(0, 0, 6)
@export var sprint_marker: Vector3 = Vector3(0, 0, -3)
@export_range(0.5, 3.0) var marker_radius: float = 1.3
## The man for the knife step.
@export var knife_spot: Vector3 = Vector3(0, 0, 1)
## The man for the dropkick step (open floor by the spawn).
@export var kick_spot: Vector3 = Vector3(1.5, 0, 10.5)
## A target shot dead before the step is done stands up again after this.
@export_range(0.5, 10.0) var target_respawn: float = 1.5

@export_group("Boot camp: goals")
@export_range(2.0, 30.0) var sprint_metres: float = 8.0
@export_range(1, 5) var slides: int = 2
@export_range(1, 6) var plates: int = 3
## Dropkicks that miss before the step counts anyway.
@export_range(1, 10) var kick_attempts: int = 4
@export_range(1, 10) var gauss_shots: int = 1
## RX-9 on for this long (world seconds).
@export_range(0.2, 5.0) var slowmo_seconds: float = 0.6
## The live wave at the end.
@export var wave: Array[String] = ["gunman", "gunman", "enforcer", "gunman"]

@export_group("Boot camp: pacing")
## After a step is done, before the next one appears.
@export_range(0.2, 4.0) var step_gap: float = 1.1
## Stuck this long on a step: the card shows a hint.
@export_range(5.0, 60.0) var hint_after: float = 16.0

@export_group("Survival tips")
## How long a tip stays up.
@export_range(2.0, 20.0) var tip_seconds: float = 7.0
## Between two tips in the queue.
@export_range(0.0, 5.0) var tip_gap: float = 0.8
## The first tips of a run come this long after it starts.
@export_range(0.0, 10.0) var run_start_delay: float = 2.5
## Health under this fraction: the "hurt" tip.
@export_range(0.05, 0.9) var low_health: float = 0.3
