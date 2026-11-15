class_name WaveEnemy
extends Resource
## One enemy type on a map's Survival roster (docs/design.md §8.6, §8.8):
## what it costs out of a wave's threat budget, the wave it first appears
## on, and how often it's picked.

## data/enemies/<role>.tres
@export var role: String = "gunman"
@export_range(0.5, 50.0) var cost: float = 2.0
@export_range(1, 100) var first_wave: int = 1
## Pick weight at its first wave, and the change per wave after (clamped ≥ min_weight).
@export_range(0.0, 20.0) var weight: float = 1.0
@export_range(-2.0, 2.0) var weight_per_wave: float = 0.0
@export_range(0.0, 5.0) var min_weight: float = 0.05
## Most of this type in one wave (0: no limit); `max_count_late` from `late_wave` on.
@export_range(0, 50) var max_count: int = 0
@export_range(0, 50) var max_count_late: int = 0
@export_range(1, 100) var late_wave: int = 10


func weight_at(wave: int) -> float:
	if wave < first_wave:
		return 0.0
	return maxf(weight + weight_per_wave * float(wave - first_wave), min_weight)


func cap_at(wave: int) -> int:
	if max_count_late > 0 and wave >= late_wave:
		return max_count_late
	return max_count
