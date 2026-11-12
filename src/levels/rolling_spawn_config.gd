class_name RollingSpawnConfig
extends Resource
## Rolling enemy spawns for open maps (owner, 2026-11-04): start with
## `start_count`; whenever fewer than `low_water` are still fighting, send
## `batch` more. Every one comes in out of the player's sight.

@export var start_count: int = 8
@export var low_water: int = 4
@export var batch: int = 3
## Seconds between two spawns of the same batch.
@export var spawn_gap: float = 0.6
## Never closer than this to the player (metres).
@export var min_distance: float = 14.0
## Preferred distance band: spawns here score best.
@export var preferred_min: float = 18.0
@export var preferred_max: float = 38.0
## Keep this many dead bodies at most (oldest go first).
@export var max_bodies: int = 10
## Hard cap on living enemies (CLAUDE.md §8: 12).
@export var max_alive: int = 12
## Role mix by weight.
@export var gunman_weight: float = 0.62
@export var enforcer_weight: float = 0.26
@export var red_pole_weight: float = 0.12
## How aware a new arrival is (0..1) and whether it knows where you are.
@export var arrival_awareness: float = 0.6


func pick_role(r: float) -> String:
	var total: float = gunman_weight + enforcer_weight + red_pole_weight
	var x: float = r * total
	if x < gunman_weight:
		return "gunman"
	if x < gunman_weight + enforcer_weight:
		return "enforcer"
	return "red_pole"
