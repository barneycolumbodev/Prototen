class_name WhipData
extends ActivePartData
## MW-7 Monofilament Whip (owner, 2026-11-10: "mono filament razor whip";
## design §3.4: "Hold LT to stop looking around; the right stick then moves
## the whip through the air. A melee weapon."). A reel on the right wrist
## pays out a monomolecular filament with a tungsten bead on the end. LB
## (with it selected) draws it, LB again reels it in. Hold LT: the view
## holds still and the right stick steers the whip; RT is a quick lash
## across the crosshair. Whatever the filament crosses fast enough is cut.
## Tuning in data/body/parts/mw7_monofilament_whip.tres.

@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Filament")
@export var length: float = 6.5
@export_range(6, 32) var segments: int = 16
## How hard the handle drags the filament to where it points (1/s at the
## reel, falling to `tip_follow` at the bead).
@export var root_follow: float = 38.0
@export var tip_follow: float = 5.0
## Fraction of its speed the filament keeps each 1/60 s (air drag).
@export_range(0.8, 1.0) var damping: float = 0.975
@export var gravity: float = 4.0

@export_group("Steering (LT + right stick)")
## Full stick = this far off the view's centre (deg).
@export var max_yaw_deg: float = 62.0
@export var max_pitch_deg: float = 42.0
## How fast the handle can swing (deg/s), times the melee speed stat.
@export var swing_rate_deg: float = 520.0
## Where the handle points at rest (deg right, deg up).
@export var rest_aim_deg: Vector2 = Vector2(16.0, -34.0)

@export_group("Lash (RT)")
## A sweep of this many degrees across the crosshair in this long (÷ melee speed).
@export var lash_sweep_deg: float = 115.0
@export var lash_time: float = 0.2
@export var lash_recover: float = 0.22

@export_group("Cut")
## The filament has to be moving at least this fast (m/s) to cut.
@export var min_cut_speed: float = 8.0
## Damage of a cut (times √melee power) and the energy it's treated as for
## wounds and severing (J).
@export var damage: float = 95.0
@export var energy_j: float = 1500.0
@export var impulse: float = 2.5
## Seconds before the same part of the same body can be cut again.
@export var recut_time: float = 0.2
@export_range(1, 8) var max_cuts_per_frame: int = 3

@export_group("Look")
@export var filament_color: Color = Color(0.75, 0.95, 1.0)
@export var filament_width: float = 0.006
@export var trail_color: Color = Color(0.55, 0.85, 1.0, 0.35)
@export var rumble_cut: Vector3 = Vector3(0.6, 0.3, 0.08)
