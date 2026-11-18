class_name Gait
extends RefCounted
## Footfalls and body weight for the first-person view (docs/design.md §5.7a,
## owner 2026-11-17: "smooth stepping... like Modern Warfare 2019... instead
## it just feels like a camera gliding").
##
## A camera that only translates reads as a dolly on a rail. A person reads
## as a body: the head rides a stride (a cusp at each heel strike, round over
## the top), each strike lands with a little weight that settles on a spring,
## the head and the gun lag behind the body when it speeds up and carry on
## when it stops, and every step is heard. All of that is here, as pure maths
## the player and the weapon read each frame; tuning is in MovementConfig
## ("Gait" group, data/player/movement_default.tres).
##
## Steps are tied to ground covered, not to a clock, so the feet never skate:
## the stride grows with speed (stride_walk × (speed / walk)^stride_exponent),
## as a real runner's does, so cadence rises gently from a walk to a sprint.

var cfg: MovementConfig

## Steps taken (continuous): a heel strikes at every whole number. Even
## numbers are the left foot, odd the right.
var phase: float = 0.0
## How much of the stride shows (0 standing, ~1 at a walk, more at a sprint).
var intensity: float = 0.0
## The heel strike's weight: x = side sway (m), y = dip (m), z = pitch (deg,
## + = nose down). Kicked on every footfall and landing, settles on a spring.
var impact: Spring
## The head's lag behind the body's velocity (m/s, body space: x right,
## z back). Leans the view and swings the gun when you speed up, stop, strafe.
var inertia: Spring
## The roll part of a step (deg), its own spring so it can settle slower.
var roll_kick: Spring
## The gun's vertical lag (m/s of the body's up speed, smoothed).
var vertical: Spring
## Footfalls this frame: Array of [side (-1 left, +1 right), strength 0..2].
var footfalls: Array[Vector2] = []
var _primed: bool = false
## Where the stride stands: 0 = foot planted, 1 = mid-air between steps.
var _lift: float = 0.0


func _init(p_cfg: MovementConfig) -> void:
	cfg = p_cfg
	impact = Spring.new(cfg.step_spring_hz, cfg.step_spring_damping)
	roll_kick = Spring.new(cfg.step_spring_hz * 0.7, cfg.step_spring_damping)
	inertia = Spring.new(cfg.lean_spring_hz, cfg.lean_spring_damping)
	vertical = Spring.new(4.0, 0.8)


## Metres covered per step at this speed.
func stride(speed: float) -> float:
	var walk: float = maxf(cfg.walk_speed, 0.1)
	return maxf(cfg.stride_walk * pow(maxf(speed, 0.0) / walk, cfg.stride_exponent), 0.5)


## Steps per second at this speed (what the tests and the HUD read).
func cadence(speed: float) -> float:
	return speed / stride(speed) if speed > 0.01 else 0.0


## One frame. `local_vel`: the body's velocity in its own space (x right,
## y up, z back). `delta`: the player's own time.
func update(delta: float, local_vel: Vector3, on_floor: bool, crouched: bool) -> void:
	footfalls.clear()
	if delta <= 0.0:
		return
	impact.frequency = cfg.step_spring_hz
	impact.damping = cfg.step_spring_damping
	roll_kick.frequency = cfg.step_spring_hz * 0.7
	roll_kick.damping = cfg.step_spring_damping
	inertia.frequency = cfg.lean_spring_hz
	inertia.damping = cfg.lean_spring_damping
	var flat: Vector3 = Vector3(local_vel.x, 0.0, local_vel.z)
	var speed: float = flat.length()
	# The head follows the body's velocity on a spring: the gap is the lean.
	if not _primed:
		inertia.reset(flat)
		_primed = true
	inertia.target = flat
	inertia.step(delta)
	vertical.target = Vector3(0.0, clampf(local_vel.y, -12.0, 12.0), 0.0)
	vertical.step(delta)
	var walking: bool = on_floor and speed > 0.3
	var want: float = clampf(speed / maxf(cfg.walk_speed, 0.1), 0.0, 1.8) if walking else 0.0
	if crouched:
		want *= cfg.crouch_bob_scale
	# Fades in over the first step, out as you stop (no pop either way).
	intensity = move_toward(intensity, want, delta * (6.0 if want > intensity else 4.0))
	if walking:
		var before: float = phase
		phase += speed * delta / stride(speed)
		if floorf(phase) > floorf(before):
			var side: float = 1.0 if int(floorf(phase)) % 2 == 1 else -1.0
			_strike(side, clampf(speed / maxf(cfg.walk_speed, 0.1), 0.3, 1.8) * (cfg.crouch_bob_scale if crouched else 1.0))
	elif speed <= 0.3 and on_floor:
		# Standing: settle onto the nearest planted foot, so the next step
		# starts from a heel strike rather than mid-stride.
		var frac: float = phase - floorf(phase)
		if frac > 0.0:
			phase = move_toward(phase, floorf(phase) + (1.0 if frac > 0.5 else 0.0), delta * 2.5)
	_lift = absf(sin(PI * phase))
	impact.step(delta)
	roll_kick.step(delta)


## A heel strike: the weight drops onto that foot.
func _strike(side: float, strength: float) -> void:
	impact.kick(Vector3(side * cfg.step_sway_kick, -cfg.step_dip, cfg.step_pitch_deg) * strength)
	# Roll convention (as the strafe lean): - z = right side down.
	roll_kick.kick(Vector3(0.0, 0.0, -side * cfg.step_roll_deg) * strength)
	footfalls.append(Vector2(side, strength))


## Both feet down from a fall (m/s): a heavier strike, and the stride restarts
## from planted feet.
func land(fall_speed: float) -> void:
	var k: float = clampf(fall_speed / 8.0, 0.25, 1.6)
	var side: float = 1.0 if int(floorf(phase)) % 2 == 0 else -1.0
	impact.kick(Vector3(0.0, -cfg.step_dip * 1.5, cfg.land_pitch_deg) * k)
	roll_kick.kick(Vector3(0.0, 0.0, -side * cfg.step_roll_deg * 1.5) * k)
	phase = floorf(phase) + 0.5


## The push off the ground for a jump.
func takeoff() -> void:
	impact.kick(Vector3(0.0, -cfg.step_dip * 0.6, -cfg.step_pitch_deg * 0.5))


## The lean (m/s): how far the head trails the body. + z = the head is behind
## (speeding up forward), - z = it runs on ahead (stopping).
func lean() -> Vector3:
	return inertia.value - inertia.target


## Head offset in body space (m): the stride plus the strike's weight plus the lean.
func head_offset() -> Vector3:
	var b: float = cfg.bob_height * intensity
	# Low at each heel strike, high mid-stride: a smooth wave with bob_cusp of
	# a sharper inverted-pendulum cusp mixed in (more = punchier steps).
	var smooth: float = 0.5 - 0.5 * cos(TAU * phase)
	var up: float = (lerpf(smooth, _lift, cfg.bob_cusp) - 0.5) * b
	# Over the planted foot: right during a right step (phase 1..2, sin < 0).
	var side: float = -sin(PI * phase) * cfg.bob_sway * intensity
	var l: Vector3 = lean()
	var lean_pos: Vector3 = Vector3(l.x, 0.0, l.z) * cfg.lean_offset_per_mps
	return Vector3(side + impact.value.x, up + impact.value.y, 0.0) + lean_pos


## Head turn in degrees: x = pitch (+ nose down), z = roll (- right side
## down, as Player's strafe lean).
func head_rotation_deg() -> Vector3:
	var l: Vector3 = lean()
	# Right side down while on the right foot.
	var bob_roll: float = sin(PI * phase) * cfg.bob_roll_deg * intensity
	# Stopping (head runs ahead, -z) pitches forward; speeding up rocks back.
	# Speeding up to the right (l.x < 0) leans into it (- roll).
	var pitch: float = impact.value.z - l.z * cfg.lean_pitch_per_mps
	var roll: float = roll_kick.value.z + bob_roll + l.x * cfg.lean_roll_per_mps
	return Vector3(clampf(pitch, -4.0, 4.0), 0.0, clampf(roll, -4.0, 4.0))


## The gun's offset in camera space (m) for a gun of weight `inertia_scale`:
## it trails the body (back and to the side), rides the stride a little
## behind the head and sinks as you rise, floats as you fall.
func gun_offset(inertia_scale: float) -> Vector3:
	var l: Vector3 = lean()
	var lag: Vector3 = Vector3(l.x, 0.0, l.z) * cfg.gun_lag_per_mps * inertia_scale
	var v: float = clampf(-vertical.value.y * cfg.gun_rise_per_mps, -0.03, 0.03) * inertia_scale
	var strike: Vector3 = Vector3(impact.value.x * 0.5, impact.value.y * cfg.gun_step_scale, 0.0) * inertia_scale
	return (lag + Vector3(0.0, v, 0.0) + strike).clamp(-Vector3.ONE * 0.06, Vector3.ONE * 0.06)


## The gun's turn (weapon space, deg: x roll about the bore, y yaw, z muzzle
## rise): it rolls and yaws against a strafe (the muzzle trails), dips as
## the arms take the weight pushing off and again as it carries on over a
## stop, and nods with each strike.
func gun_rotation_deg(inertia_scale: float) -> Vector3:
	var l: Vector3 = lean()
	var k: float = cfg.gun_turn_per_mps * inertia_scale
	var roll: float = -l.x * k * 1.4 + roll_kick.value.z * cfg.gun_step_scale
	# + yaw = muzzle left (as the look sway: turning right, it trails left).
	var yaw: float = -l.x * k * 0.6
	var rise: float = -absf(l.z) * k - impact.value.z * cfg.gun_step_scale * 0.6
	return Vector3(roll, yaw, rise).clamp(-Vector3.ONE * 8.0, Vector3.ONE * 8.0)
