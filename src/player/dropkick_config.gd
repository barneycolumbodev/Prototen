class_name DropkickConfig
extends Resource
## Midair dropkick tuning (docs/design.md §5.7b): jump, then press A again in
## midair to surge forward into a brutal double-boot flying dropkick. Kicking
## an enemy blasts him back and up into the air while rebounding you backward
## with your gun sweeping out into a canted Max Payne / John Woo dive-fire
## stance. Tuning lives in data/player/dropkick_default.tres.

@export_group("Trigger & Flight")
## Minimum airborne time (s) before a second A press triggers a dropkick.
@export var min_air_time: float = 0.08
## While falling within this distance (m) of the floor, pressing A buffers a
## landing jump instead of dropkicking into the ground.
@export var land_grace_height: float = 0.28
## Seconds after recovery ends before another dropkick can start.
@export var cooldown: float = 0.45
## Minimum horizontal launch speed (m/s), speed added on top of current speed, and cap.
@export var launch_speed: float = 12.2
@export var speed_boost: float = 2.6
@export var max_speed: float = 15.5
## Upward pop (m/s) on launch plus share of existing upward speed kept.
@export var launch_up: float = 2.1
@export_range(0.0, 1.0) var keep_up_fraction: float = 0.15
## Gravity multiplier during the forward kick dive (< 1 gives heroic hang time).
@export_range(0.3, 1.5) var gravity_scale: float = 0.72
## Gentle steering rate (rad/s) while airborne in the dive.
@export var air_steer: float = 1.6
## Subtle magnetic guidance toward a living enemy in front on launch.
@export var assist_range: float = 6.5
@export_range(0.0, 60.0) var assist_cone_deg: float = 26.0
@export_range(0.0, 1.0) var assist_strength: float = 0.65

@export_group("Impact & Enemy Launch")
## Horizontal and vertical reach (m, centre to centre) for boot contact.
@export var hit_reach: float = 1.35
@export var hit_vertical_reach: float = 1.65
## Brief grace window (s) after first hit so shoulder-to-shoulder enemies both fly.
@export var cluster_window: float = 0.055
## Reference shove strength (m/s) for a 100 kg operative at strength 1 moving at knock_ref_speed.
@export var knock_speed: float = 9.5
@export var knock_ref_speed: float = 12.5
## Base upward and forward launch speed (m/s) given to an enemy at reference strength.
## Scaled by sqrt(push / knock_speed) within launch_scale_min..max.
@export var launch_up_speed: float = 5.4
@export var launch_forward_speed: float = 6.8
@export var launch_scale_min: float = 0.85
@export var launch_scale_max: float = 1.55
## Horizontal speed cap (m/s) on launched enemies ("far, not crazy far").
@export var launch_max_speed: float = 12.0
## Gravity (m/s²) on a dropkicked enemy so he hangs cleanly for midair shots.
@export var launch_gravity: float = 11.2
## How far he tips back (°) in flight and how long (s) he needs to get up on landing.
@export var launch_tumble_deg: float = 78.0
@export var launch_stun: float = 1.15
## Blunt impact damage at reference strength; past lethal_push breaks the body outright.
@export var damage: float = 36.0
@export var lethal_push: float = 19.0
## Bonus damage when a dropkicked enemy slams into a wall mid-flight.
@export var wall_slam_damage: float = 30.0
@export var morale_loss: float = 0.35

@export_group("Rebound & Recovery")
## Upward pop and backward recoil (m/s) when kicking off an enemy ("falling back").
@export var rebound_up: float = 3.3
@export var rebound_back: float = 4.2
## Gravity multiplier while floating backward off the rebound.
@export_range(0.3, 1.5) var rebound_gravity_scale: float = 0.68
## Low-profile ground skid recovery time (s) and braking (m/s²). Gun stays live throughout.
@export var recover_time: float = 0.30
@export var recover_friction: float = 16.0
## Fraction of recovery after which pressing A springs straight into a jump.
@export_range(0.0, 1.0) var recover_jump_cancel_at: float = 0.55

@export_group("Camera & Feel")
@export var dive_fov_deg: float = 8.5
@export var rebound_fov_deg: float = 5.5
@export var dive_roll_deg: float = 8.5
@export var dive_eye_height: float = 1.18
## Camera recoil kicks (deg: pitch up, yaw right, roll) on launch and impact.
@export var launch_kick_deg: Vector3 = Vector3(4.5, 0.0, -3.5)
@export var impact_kick_deg: Vector3 = Vector3(5.5, 0.0, 5.0)
## Crisp impact hit-stop (real seconds, world scale) and brief rebound slow-mo
## beat when RX-9 time dilation is not already active.
@export var hitstop_time: float = 0.065
@export_range(0.05, 1.0) var hitstop_scale: float = 0.08
@export var slowmo_time: float = 0.28
@export_range(0.1, 1.0) var slowmo_scale: float = 0.55
## Controller rumble: weak motor, strong motor, seconds.
@export var rumble_launch: Vector3 = Vector3(0.35, 0.45, 0.10)
@export var rumble_impact: Vector3 = Vector3(0.95, 1.0, 0.22)
@export var rumble_land: Vector3 = Vector3(0.45, 0.65, 0.12)

@export_group("Gun Dive Stance")
## Brief fire lockout (s) during the explosive initial leg whip; firing anytime after
## snaps the gun straight up out of the holster-side tuck.
@export var fire_lock_time: float = 0.06
## Gun tucks briefly toward the hip/holster on launch, then sweeps up canted into
## the Max Payne / John Woo dive-firing stance (or immediately on impact / fire).
@export var tuck_in_time: float = 0.06
@export var tuck_hold_time: float = 0.13
@export var draw_up_time: float = 0.14
@export var tuck_offset: Vector3 = Vector3(0.08, -0.24, 0.07)
@export var tuck_rot_deg: Vector3 = Vector3(-24.0, -10.0, -28.0)
@export var dive_offset: Vector3 = Vector3(-0.022, 0.015, -0.022)
## Roll about the bore (°) while diving hip-fire (blends cleanly to 0 in ADS).
@export var dive_cant_deg: float = 20.0
## Airborne and moving spread multipliers while dropkicking (sharp Max Payne shots).
@export_range(0.0, 1.0) var dive_air_spread_scale: float = 0.2
@export_range(0.0, 1.0) var dive_move_spread_scale: float = 0.45

@export_group("Legs Viewmodel")
## Articulated first-person GS-2 legs and boots (raw_assets/characters/fp_legs/build.py).
@export var legs_scene: PackedScene
@export var chamber_time: float = 0.055
@export var extend_time: float = 0.095
@export var retract_time: float = 0.18
## Maximum yaw offset (deg) the legs keep toward launch direction while looking around.
@export var yaw_follow_max_deg: float = 42.0
## Share of pitch change countered so looking up to shoot doesn't lift your boots to the sky.
@export_range(0.0, 1.0) var pitch_counter_share: float = 0.65
@export var trail_time: float = 0.08
@export var trail_color: Color = Color(0.78, 0.90, 1.0, 0.34)
