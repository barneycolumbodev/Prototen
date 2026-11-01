class_name MovementConfig
extends Resource
## Player movement tuning (data/player/*.tres). Augmented baseline: faster and
## higher-jumping than the human enemies. Parts will modify these in M2.

@export_group("Speed (m/s)")
@export var walk_speed: float = 6.5
@export var sprint_speed: float = 11.0
@export var crouch_speed: float = 3.2
@export_group("Acceleration (m/s²)")
@export var ground_accel: float = 70.0
@export var ground_decel: float = 55.0
@export var air_accel: float = 18.0
@export_group("Jump")
@export var gravity: float = 22.0
@export var jump_velocity: float = 8.0
## Grace period after leaving a ledge during which a jump still works.
@export var coyote_time: float = 0.12
## A jump pressed this long before landing still fires on landing.
@export var jump_buffer: float = 0.12
@export_group("Stick")
@export_range(0.0, 0.5) var move_inner_deadzone: float = 0.15
@export_range(0.0, 0.3) var move_outer_deadzone: float = 0.05
## Sprint ends when the stick drops below this or points sideways/back.
@export_range(0.1, 1.0) var sprint_min_forward: float = 0.5
@export_group("Body")
@export var stand_height: float = 1.8
@export var crouch_height: float = 1.1
@export var stand_eye_height: float = 1.65
@export var crouch_eye_height: float = 0.95
@export var crouch_transition_speed: float = 10.0


## Moves horizontal velocity toward `target`. Uses `accel` when speeding up
## (or turning), `decel` when slowing toward a smaller target.
static func approach(current: Vector3, target: Vector3, accel: float, decel: float, delta: float) -> Vector3:
	var rate: float = accel if target.length_squared() >= current.length_squared() else decel
	return current.move_toward(target, rate * delta)


## Height of a jump with these settings, in metres.
func jump_height() -> float:
	return jump_velocity * jump_velocity / (2.0 * gravity)
