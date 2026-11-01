class_name ViewmodelMotion
extends RefCounted
## Procedural first-person weapon motion (docs/design.md §5.4): springs for
## recoil, sway, bob, landing and poses (sprint, reload, draw), blended
## between the hip and aimed placements. Pure math so it can be tested; the
## weapon controller feeds it every frame and applies `compose()`.
##
## Rotations are in weapon space, degrees: x = roll about the bore,
## y = yaw, z = muzzle rise. Offsets are in camera space, metres.

var data: WeaponData

## Recoil: position (camera space) and rotation (weapon space).
var recoil_pos: Spring
var recoil_rot: Spring
var sway: Spring
var pose_pos: Spring
var pose_rot: Spring
var land: Spring

var bob_phase: float = 0.0
var bob: Vector3 = Vector3.ZERO
## 0..1, how far the slide is back.
var slide: float = 0.0
var _slide_time: float = 1.0
var _slide_locked: bool = false


func _init(p_data: WeaponData) -> void:
	data = p_data
	recoil_pos = Spring.new()
	recoil_rot = Spring.new()
	sway = Spring.new()
	pose_pos = Spring.new()
	pose_rot = Spring.new()
	land = Spring.new(5.0, 0.6)
	apply_tuning()
	# Start lowered so the gun comes up on spawn.
	pose_pos.reset(data.draw_offset)
	pose_rot.reset(data.draw_rotation_deg)


## Re-reads spring tuning from the data (the tuning menu changes it live).
func apply_tuning() -> void:
	recoil_pos.frequency = data.vm_spring_hz
	recoil_pos.damping = data.vm_spring_damping
	recoil_rot.frequency = data.vm_spring_hz
	recoil_rot.damping = data.vm_spring_damping
	sway.frequency = data.sway_spring_hz
	sway.damping = data.sway_spring_damping
	pose_pos.frequency = data.pose_spring_hz
	pose_pos.damping = data.pose_spring_damping
	pose_rot.frequency = data.pose_spring_hz
	pose_rot.damping = data.pose_spring_damping


func fire(ads: float, rng: RandomNumberGenerator) -> void:
	var s: float = lerpf(1.0, data.ads_vm_scale, ads)
	recoil_pos.kick(Vector3(0.0, data.vm_kick_back * 0.12, data.vm_kick_back) * s)
	recoil_rot.kick(Vector3(rng.randf_range(-1.0, 1.0) * data.vm_kick_roll_deg,
			rng.randf_range(-0.3, 0.3) * data.vm_kick_roll_deg,
			data.vm_kick_rise_deg * rng.randf_range(0.85, 1.1)) * s)
	_slide_time = 0.0


## Small extra jolts for reload beats (magazine out, slap in, slide release).
func jolt(pos: Vector3, rot_deg: Vector3) -> void:
	recoil_pos.kick(pos)
	recoil_rot.kick(rot_deg)


func landed(fall_speed: float) -> void:
	land.kick(Vector3(0.0, -fall_speed * data.land_dip, 0.0))


## `look_rate`: degrees per second, x = turning right, y = looking up.
## `pose`: 0 = none, 1 = sprint, 2 = reload (draw handled by the start state).
func update(delta: float, ads: float, look_rate: Vector2, move_fraction: float,
		on_floor: bool, pose: int) -> void:
	var still: float = 1.0 - 0.75 * ads
	var sway_target: Vector3 = Vector3(
			-look_rate.x * data.sway_per_turn * 0.4,
			look_rate.x * data.sway_per_turn,
			-look_rate.y * data.sway_per_turn) * still
	sway.target = sway_target.clamp(-Vector3.ONE * data.sway_max_deg, Vector3.ONE * data.sway_max_deg)
	sway.step(delta)

	match pose:
		1:
			pose_pos.target = data.sprint_offset
			pose_rot.target = data.sprint_rotation_deg
		2:
			pose_pos.target = data.reload_offset * (1.0 - ads)
			pose_rot.target = data.reload_rotation_deg * (1.0 - ads)
		_:
			pose_pos.target = Vector3.ZERO
			pose_rot.target = Vector3.ZERO
	pose_pos.step(delta)
	pose_rot.step(delta)
	recoil_pos.step(delta)
	recoil_rot.step(delta)
	land.step(delta)

	# Figure-eight bob, faster and bigger when sprinting, nearly gone when aimed.
	var rate: float = data.bob_rate * (1.45 if pose == 1 else 1.0)
	if on_floor and move_fraction > 0.05:
		bob_phase = fmod(bob_phase + TAU * rate * move_fraction * delta, TAU * 2.0)
	var amp: float = data.bob_amount * clampf(move_fraction, 0.0, 1.6) * (1.0 - 0.85 * ads) * (1.0 if on_floor else 0.3)
	bob = bob.lerp(Vector3(sin(bob_phase) * amp, sin(bob_phase * 2.0) * amp * 0.5, 0.0), clampf(delta * 12.0, 0.0, 1.0))

	_slide_time += delta
	var cycle: float = data.slide_cycle_time
	# Slide slams back fast (25 % of the cycle) and returns on its spring.
	if _slide_locked and _slide_time >= cycle * 0.25:
		slide = 1.0
	elif _slide_time < cycle * 0.25:
		slide = _slide_time / (cycle * 0.25)
	elif _slide_time < cycle:
		slide = 1.0 - (_slide_time - cycle * 0.25) / (cycle * 0.75)
	else:
		slide = 0.0


## Holds the slide locked back (empty gun).
func lock_slide() -> void:
	_slide_locked = true


func release_slide() -> void:
	_slide_locked = false
	_slide_time = data.slide_cycle_time * 0.25


func compose(hip: Transform3D, ads_xform: Transform3D, ads: float) -> Transform3D:
	var base: Transform3D = hip.interpolate_with(ads_xform, ads)
	var rot: Vector3 = (recoil_rot.value + sway.value + pose_rot.value) * (PI / 180.0)
	var pivot: Vector3 = data.grip_pivot
	var local: Transform3D = Transform3D(Basis(), pivot) * Transform3D(Basis.from_euler(rot), Vector3.ZERO) * Transform3D(Basis(), -pivot)
	var offset: Vector3 = recoil_pos.value + pose_pos.value + land.value + bob
	return Transform3D(Basis(), offset) * base * local
