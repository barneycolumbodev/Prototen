class_name WeaponWheelConfig
extends Resource
## Weapon wheel tuning (data/input/weapon_wheel.tres). Tap Y swaps back to
## the previous gun; hold Y opens the wheel, the right stick picks a gun and
## letting go of Y draws it.

## Seconds Y must be held before the wheel opens (shorter = a tap).
@export_range(0.05, 0.6) var hold_time: float = 0.2
## Game speed while the wheel is open (1 = no slow-down).
@export_range(0.05, 1.0) var time_scale: float = 0.3
## Right-stick deflection needed to move the highlight.
@export_range(0.1, 0.9) var stick_deadzone: float = 0.45
