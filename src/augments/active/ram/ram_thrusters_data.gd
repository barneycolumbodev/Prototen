class_name RamThrustersData
extends ActivePartData
## KR-5 Ram Thrusters (2026-11-10): two cold-gas thrusters on the shoulder
## blades. LB (with it selected) fires them: the operative is thrown
## forward along the view and goes through whoever is in the way. The hit
## is the slide hit (docs/design.md §3.6: mass × usable strength × impact)
## times `ram_multiplier`, so a heavy, strong, plated body kills with it and
## a light one only shoves. A heavier body also flies less far.
## Tuning in data/body/parts/kr5_ram_thrusters.tres.

@export_group("Dash")
## Speed (m/s) at `ref_mass_kg`, and how long the burn lasts (s).
@export var dash_speed: float = 27.0
@export_range(0.05, 1.0) var dash_time: float = 0.26
## The body mass the speed is tuned for; speed scales with √(ref ÷ mass),
## between these limits.
@export var ref_mass_kg: float = 125.0
@export var min_speed_scale: float = 0.7
@export var max_speed_scale: float = 1.25
## Looking up or down tilts the dash by at most this much (deg).
@export var max_climb_deg: float = 22.0
@export var max_dive_deg: float = 8.0

@export_group("Impact")
## Times the slide hit (MovementConfig.slide_knock_speed × mass/100 × usable strength × impact).
@export var ram_multiplier: float = 1.8
@export var morale_loss: float = 0.6
## Speed kept after each body (the rest goes into him).
@export_range(0.0, 1.0) var speed_kept: float = 0.85

@export_group("Cost")
## Joules from the power reserve and heat into the body per burn.
@export var energy_j: float = 7000.0
@export var heat_j: float = 4500.0

@export_group("Feel")
@export var fov_punch_deg: float = 13.0
@export var fov_recover: float = 3.2
@export var camera_kick_deg: Vector3 = Vector3(-2.5, 0.0, 0.0)
## Weak motor, strong motor, seconds.
@export var rumble_fire: Vector3 = Vector3(0.9, 1.0, 0.3)
@export var streak_color: Color = Color(0.75, 0.9, 1.0, 0.5)
