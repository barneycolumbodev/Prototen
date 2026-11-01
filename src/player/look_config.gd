class_name LookConfig
extends Resource
## Controller look tuning (CLAUDE.md §9.4). One .tres per preset in data/input/.

@export var display_name: String = "Standard"
@export_group("Speed")
## Turn rate at full stick deflection, degrees per second.
@export_range(30.0, 720.0) var yaw_speed_deg: float = 240.0
@export_range(30.0, 720.0) var pitch_speed_deg: float = 170.0
@export var invert_y: bool = false
@export_group("Stick shape")
@export_range(0.0, 0.5) var inner_deadzone: float = 0.12
@export_range(0.0, 0.3) var outer_deadzone: float = 0.04
## 1 = linear. Higher = finer control near the centre.
@export_range(0.5, 4.0) var curve_exponent: float = 1.8
@export_group("Full-tilt acceleration")
## Stick length (after shaping) that counts as full tilt.
@export_range(0.5, 1.0) var full_tilt_threshold: float = 0.95
## Seconds at full tilt before the boost starts.
@export_range(0.0, 1.0) var full_tilt_delay: float = 0.12
## Seconds to ramp from no boost to the full boost.
@export_range(0.01, 2.0) var full_tilt_ramp: float = 0.3
## Yaw multiplier once fully ramped.
@export_range(1.0, 4.0) var full_tilt_boost: float = 1.8
@export_group("Mouse (desktop testing)")
@export var mouse_deg_per_pixel: float = 0.12


## Yaw multiplier after holding full tilt for `tilt_time` seconds.
func boost_for(tilt_time: float) -> float:
	if tilt_time <= full_tilt_delay:
		return 1.0
	return lerpf(1.0, full_tilt_boost, clampf((tilt_time - full_tilt_delay) / full_tilt_ramp, 0.0, 1.0))


## Look rate in degrees per second (x = yaw, y = pitch; positive y = look down).
func look_rate(raw_stick: Vector2, tilt_time: float) -> Vector2:
	var s: Vector2 = Stick.shape(raw_stick, inner_deadzone, outer_deadzone, curve_exponent)
	var pitch_sign: float = -1.0 if invert_y else 1.0
	return Vector2(s.x * yaw_speed_deg * boost_for(tilt_time), s.y * pitch_speed_deg * pitch_sign)


func is_full_tilt(raw_stick: Vector2) -> bool:
	return Stick.shape(raw_stick, inner_deadzone, outer_deadzone, 1.0).length() >= full_tilt_threshold
