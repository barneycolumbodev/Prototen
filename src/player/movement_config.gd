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
@export_group("Slide")
## B while moving this fast (sprinting) starts a slide.
@export var slide_min_speed: float = 8.0
## Speed added when the slide starts, and the most it can reach.
@export var slide_boost: float = 3.0
@export var slide_max_speed: float = 15.0
## Deceleration while sliding (m/s²) and the speed it ends at.
@export var slide_friction: float = 6.5
@export var slide_end_speed: float = 4.5
## How fast the stick can bend the slide (rad/s).
@export var slide_steer: float = 1.4
@export var slide_cooldown: float = 0.35
@export var slide_tilt_deg: float = 5.0
@export_group("Wall-run")
## Airborne, pushing forward, at least this fast, with a wall at your side.
@export var wallrun_min_speed: float = 5.5
@export var wallrun_speed: float = 11.5
@export var wallrun_time: float = 1.6
## Gravity on the wall: starts at this fraction and returns to full by the end.
@export_range(0.0, 1.0) var wallrun_gravity_scale: float = 0.1
@export var wallrun_detect: float = 0.75
## Jumping off: push from the wall and up.
@export var wallrun_jump_out: float = 7.0
@export var wallrun_jump_up: float = 8.0
@export var wallrun_tilt_deg: float = 12.0
@export var wallrun_cooldown: float = 0.4
@export_group("Mantle")
## Ledges between these heights (above the feet) can be climbed with A.
@export var mantle_min_height: float = 0.45
@export var mantle_max_height: float = 2.2
@export var mantle_reach: float = 0.85
@export var mantle_time: float = 0.34
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
