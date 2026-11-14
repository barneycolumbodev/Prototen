class_name LorentzCatcherData
extends ActivePartData
## LC-6 Lorentz Catcher (owner, 2026-11-13): eight coil petals on a drive
## ring at the left wrist. Hold LB: they bloom forward round the open hand
## and throw a pulsed magnetic field out in front of it. Enemy rounds that
## fly into it are braked by eddy currents (they're copper and lead: a
## strong changing field drags on any conductor) and held, hot, in a cloud
## in front of the palm. Let go of LB, or run out of hold time, and the
## same coils fire every round it caught back out as a spread over a wide
## area where you're aiming. It throws back exactly what it caught.
## Tuning in data/body/parts/lc6_lorentz_catcher.tres.

@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Field")
## The catch sphere: its centre this far ahead of the eye (m) and this far
## down, and its radius. Rounds that reach the body from the front are caught too.
@export var field_ahead: float = 0.9
@export var field_drop: float = 0.25
@export var field_radius: float = 1.25
## Half-angle (deg) of the open side: rounds from further round than this pass.
@export_range(10.0, 180.0) var arc_deg: float = 75.0
## Rounds held at `power_ref_w` of supply; it scales with supply ÷ ref, between the limits.
@export var base_capacity: int = 40
@export var power_ref_w: float = 450.0
@export var min_capacity: int = 20
@export var max_capacity: int = 96
## Share of a caught round's energy that ends up as heat in the body (eddy braking).
@export_range(0.0, 1.0) var heat_share: float = 0.35
## Move speed while it's up.
@export_range(0.3, 1.0) var move_scale: float = 0.82

@export_group("Release")
## Real seconds: the push forward before the rounds go, the spread of their
## launch (a ripple, not one frame), and how long the arm stays out after.
@export var push_time: float = 0.09
@export var ripple: float = 0.14
@export var after: float = 0.32
## Speed of a returned round as a fraction of how fast it was going when caught.
@export var return_speed: float = 0.92
## Reserve (J) per joule the rounds carry out; short of it they leave slower
## (speed × √(what there is ÷ what it needs)), never below `min_power_scale`.
@export var power_per_j: float = 0.4
@export var min_power_scale: float = 0.35
## The area at the aim point: a disc this wide (m radius), held between these
## half-angles (deg) so it stays wide close in and doesn't vanish far out.
@export var spread_radius: float = 3.0
@export var spread_min_deg: float = 3.0
@export var spread_max_deg: float = 16.0
## How far the aim point is looked for (m); beyond, the disc sits this far out.
@export var aim_reach: float = 90.0
@export var aim_default: float = 40.0
## Share of the rounds that go for bodies inside the area (× perception), at most `seek_max`.
@export var seek_per_perception: float = 0.3
@export_range(0.0, 1.0) var seek_max: float = 0.8

@export_group("Cloud")
## The held rounds: a disc this far from the eye, this wide (m), turning this fast (rad/s).
@export var cloud_depth: float = 0.62
@export var cloud_radius: float = 0.14
@export var cloud_spin: float = 0.6
## Real seconds for a caught round to settle into the cloud.
@export var settle_time: float = 0.22
## Drawn size of a held round (m): rounds are tiny; this is about 2× real so they read.
@export var slug_length: float = 0.04
@export var slug_width: float = 0.0115

@export_group("Look")
@export var glow_color: Color = Color(0.48, 0.78, 1.0)
@export var glow_idle: float = 0.4
@export var glow_on: float = 3.2
@export var glow_release: float = 14.0
## Held rounds: hot when caught, cooling while held, white again at release.
@export var hot_color: Color = Color(1.0, 0.5, 0.16)
## The returned rounds' streaks.
@export var return_color: Color = Color(1.0, 0.72, 0.4, 0.95)
@export var fov_kick_deg: float = 6.0
@export var camera_kick_deg: Vector3 = Vector3(-2.2, 0.8, 1.6)
@export var rumble_catch: Vector3 = Vector3(0.25, 0.35, 0.05)
@export var rumble_release: Vector3 = Vector3(0.7, 1.0, 0.3)
