class_name MovementConfig
extends Resource
## Player movement tuning (data/player/*.tres). Augmented baseline: faster and
## higher-jumping than the human enemies. Parts will modify these in M2.

@export_group("Speed (m/s)")
@export var walk_speed: float = 6.5
@export var sprint_speed: float = 11.0
@export var crouch_speed: float = 3.2
@export_group("Acceleration (m/s²)")
## Most the ground speed can change per second, speeding up and slowing down.
@export var ground_accel: float = 70.0
@export var ground_decel: float = 55.0
@export var air_accel: float = 18.0
@export_group("Feel (2026-11-11 overhaul)")
## How quickly speed closes on the target (1/s): the gap shrinks at this
## rate, capped by ground_accel/decel, so starts and stops ease out instead
## of snapping. Higher = snappier.
@export var ground_response: float = 14.0
@export var stop_response: float = 16.0
## Turning while moving swings the velocity round at this rate (rad/s)
## without losing speed ("carving"). Past reverse_angle_deg you plant and
## push off the other way instead.
@export var ground_turn_rate: float = 13.0
@export_range(90.0, 180.0) var reverse_angle_deg: float = 125.0
## Speed above the current target (out of a slide, a wall jump, a dash, a
## fall) bleeds off this slowly (m/s²) while you keep pushing; let go of the
## stick and normal braking applies.
@export var overspeed_friction: float = 7.0
## In the air: the stick swings the velocity round (rad/s) without slowing
## you; pulling back brakes at air_accel.
@export var air_turn_rate: float = 3.2
## Gravity × this while rising with A held, rising after letting go of A
## (short hop), near the top of the arc (hang), and falling.
@export var rise_gravity_scale: float = 1.0
@export var jump_release_gravity_scale: float = 2.3
@export var apex_gravity_scale: float = 0.7
@export var apex_band: float = 1.6
@export var fall_gravity_scale: float = 1.15
@export var max_fall_speed: float = 38.0
## Sprint holds while the stick is within this angle of forward and tilted
## at least sprint_hold_tilt (strafing at a run doesn't drop it).
@export_range(20.0, 90.0) var sprint_cone_deg: float = 70.0
@export_range(0.1, 1.0) var sprint_hold_tilt: float = 0.4
## B pressed this long before landing at speed starts a slide on touchdown.
@export var slide_buffer: float = 0.2
## Downhill pulls a slide along (× gravity × slope).
@export var slide_slope_accel: float = 0.6
## Wall-run entry: the velocity swings onto the wall over this long (s).
@export var wallrun_entry_time: float = 0.12
## A mantle keeps this share of the speed you came in with (at least 3 m/s).
@export_range(0.0, 1.0) var mantle_keep_speed: float = 0.85
@export_group("Camera feel")
## The camera is drawn where the body is between physics ticks, so motion
## stays smooth whatever the frame rate.
@export var camera_interpolation: bool = true
## Camera dip on landing (m per m/s of fall speed, max), and its spring.
@export var land_dip_per_mps: float = 0.009
@export var land_dip_max: float = 0.14
@export var land_spring_hz: float = 5.0
@export var land_spring_damping: float = 0.65
## Field of view added (°) at a full sprint and in a slide.
@export var sprint_fov_deg: float = 4.0
@export var slide_fov_deg: float = 7.0
@export var fov_smooth: float = 7.0
## Roll (°) into a strafe at full speed.
@export var strafe_roll_deg: float = 1.1
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
## Full tilt forward sprints on its own after `auto_sprint_delay` (L3 still
## works). Playtest 2026-11-05: movement felt clumsy.
@export var auto_sprint: bool = true
@export_range(0.5, 1.0) var auto_sprint_tilt: float = 0.92
@export var auto_sprint_delay: float = 0.15
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
## Off: a tap of B slides until the speed runs out (B again or A ends it
## early; owner, 2026-11-07). On: let go of B to stop. Owner, 2026-11-14:
## shorter (about 7 m), a move for cover and setting up a shot, not for
## skating round the map.
@export var slide_hold: bool = false
## Pulling the stick back this far ends the slide.
@export var slide_brake_stick: float = 0.6
@export_group("Slide knockback")
## Sliding into a living enemy knocks him into the air (owner, 2026-11-07;
## launch and no damage, 2026-11-14). Strength of the hit (m/s) for a 100 kg
## operative at strength 1 sliding at slide_knock_ref_speed; scales with
## mass × strength × impact × speed.
@export var slide_knock_speed: float = 6.5
@export var slide_knock_ref_speed: float = 12.0
## The player has to be sliding at least this fast.
@export var slide_knock_min_speed: float = 5.0
## How close (m, centre to centre, horizontal) counts as hitting him.
@export var slide_knock_reach: float = 1.05
## Share of the player's slide speed lost per enemy hit (he goes up in front of you).
@export var slide_knock_speed_loss: float = 0.2
@export var slide_knock_morale: float = 0.15
## Used by the RAM thrusters' charge only (the slide does no damage): damage
## at slide_knock_speed (grows with the square of the shove), and the shove
## that breaks a body.
@export var slide_knock_damage: float = 8.0
@export var slide_knock_lethal_speed: float = 16.0
@export_group("Slide launch")
## Speed (m/s) the base operative's slide sends a man up, and along the slide.
@export var slide_launch_up: float = 4.6
@export var slide_launch_forward: float = 4.0
## Range of the body's effect (hit strength / slide_knock_speed); both speeds scale with its square root.
## The Operator (125 kg, strength ×1.15) hits at about 1.5: ~1.4 m up, ~5 m along, ~1 s in the air.
@export var slide_launch_scale_min: float = 0.75
@export var slide_launch_scale_max: float = 1.6
## Gravity (m/s²) on a launched man: lower than his normal 20 so he hangs for the shot.
@export var slide_launch_gravity: float = 12.0
## How far he tips back in the air (°), and how long (s) he needs on the ground to recover.
@export var slide_launch_tumble_deg: float = 60.0
@export var slide_launch_stun: float = 0.8
## The slow beat right after the hit: real seconds, and the time scale.
@export var slide_launch_slowmo_time: float = 0.35
@export_range(0.05, 1.0) var slide_launch_slowmo_scale: float = 0.45
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
@export_group("Steps")
## Curbs, sills, stair treads and low lips up to this height are walked
## over without a jump; the camera eases over the step instead of popping.
@export var step_height: float = 0.45
## How fast the camera catches up after a step (1/s, exponential).
@export var step_smooth: float = 14.0
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


## One tick of ground movement (horizontal velocity `h`, m/s). `wish`:
## stick direction in the world (length 0..1); `top`: the speed for this
## state (walk, sprint, crouch) at full tilt; `agility` scales every rate.
## Speed and direction are handled apart: speed eases toward the target,
## direction swings round at ground_turn_rate, so turns keep their speed.
## `carry`: the speed momentum bleeds down to gently (a sprint); below it,
## normal braking takes speed down to the target (aiming, crouching).
func ground_step(h: Vector3, wish: Vector3, top: float, agility: float, delta: float, carry: float = -1.0) -> Vector3:
	if carry < 0.0:
		carry = top
	var speed: float = h.length()
	var tilt: float = minf(wish.length(), 1.0)
	var target: float = top * tilt
	if tilt < 0.02:
		return h.normalized() * _ease_speed(speed, 0.0, carry, false, agility, delta) if speed > 0.0001 else Vector3.ZERO
	var want: Vector3 = wish / wish.length()
	if speed < 0.4:
		# From (nearly) standing: push off straight along the stick.
		return approach(h, want * target, ground_accel * agility, ground_decel * agility, delta)
	var dir: Vector3 = h / speed
	var ang: float = dir.signed_angle_to(want, Vector3.UP)
	if absf(ang) > deg_to_rad(reverse_angle_deg):
		# Reversing: plant and push off the other way.
		return approach(h, want * target, ground_accel * agility, ground_decel * agility * 1.15, delta)
	var turn: float = ground_turn_rate * agility * delta
	dir = dir.rotated(Vector3.UP, clampf(ang, -turn, turn))
	return dir * _ease_speed(speed, target, maxf(carry, top), true, agility, delta)


## Eases `speed` toward `target`: the gap closes at *_response per second,
## never faster than ground_accel/decel. Above `carry` (momentum from a
## slide, a jump: faster than a sprint) it bleeds at overspeed_friction while
## `pushing`; from `carry` down to the target, normal braking.
func _ease_speed(speed: float, target: float, carry: float, pushing: bool, agility: float, delta: float) -> float:
	if speed < target:
		var rate: float = minf(ground_accel * agility, (target - speed) * ground_response + 2.0)
		return minf(speed + rate * delta, target)
	if pushing and speed > carry + 0.05:
		return maxf(speed - overspeed_friction * delta, maxf(target, carry))
	var down: float = minf(ground_decel * agility, (speed - target) * stop_response + 2.5)
	return maxf(speed - down * delta, target)


## One tick of air control: the stick swings the velocity round without
## slowing it, adds speed up to `top`, and pulling back brakes.
func air_step(h: Vector3, wish: Vector3, top: float, agility: float, delta: float) -> Vector3:
	var tilt: float = minf(wish.length(), 1.0)
	if tilt < 0.02:
		return h
	var want: Vector3 = wish / wish.length()
	var speed: float = h.length()
	if speed < 0.5:
		return approach(h, want * top * tilt, air_accel * agility, air_accel * agility, delta)
	var dir: Vector3 = h / speed
	var ang: float = dir.signed_angle_to(want, Vector3.UP)
	if absf(ang) > deg_to_rad(150.0):
		return dir * maxf(speed - air_accel * agility * tilt * delta, 0.0)
	var turn: float = air_turn_rate * agility * tilt * delta
	dir = dir.rotated(Vector3.UP, clampf(ang, -turn, turn))
	if speed < top * tilt:
		speed = minf(speed + air_accel * agility * tilt * delta, top * tilt)
	return dir * speed


## Gravity multiplier for this moment of a jump (`vy` up speed).
func gravity_scale(vy: float, jump_held: bool) -> float:
	if absf(vy) < apex_band:
		return apex_gravity_scale
	if vy > 0.0:
		return rise_gravity_scale if jump_held else jump_release_gravity_scale
	return fall_gravity_scale


## Whether a sprint carries on with the stick at `stick` (y < 0 = forward).
func sprint_holds(stick: Vector2) -> bool:
	if stick.length() < sprint_hold_tilt or stick.y > 0.0:
		return false
	return rad_to_deg(atan2(absf(stick.x), -stick.y)) <= sprint_cone_deg


## Moves horizontal velocity toward `target`. Uses `accel` when speeding up
## (or turning), `decel` when slowing toward a smaller target.
static func approach(current: Vector3, target: Vector3, accel: float, decel: float, delta: float) -> Vector3:
	var rate: float = accel if target.length_squared() >= current.length_squared() else decel
	return current.move_toward(target, rate * delta)


## Height of a jump with these settings, in metres.
func jump_height() -> float:
	return jump_velocity * jump_velocity / (2.0 * gravity)
