class_name GaussArmData
extends ActivePartData
## GX-4 Gauss arm (owner, 2026-11-07): the right forearm is a prosthetic that
## folds open into a coilgun. LB (with it selected on the D-pad) raises the
## hand, which transforms into the cannon; RT fires; LB again folds it away.
## The charge is rounds: 10, refilled one at a time while it's stowed, like
## Destiny's Golden Gun as a piece of hardware. Tuning in
## data/body/parts/gx4_gauss_arm.tres; the round in data/weapons/gx4_slug.tres.

@export var round: WeaponData
## The arm model (glTF with its transform animation) and where it sits.
@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Firing")
## Seconds between shots (the coils recharge; the glow ramps back up).
@export_range(0.1, 3.0) var fire_interval: float = 0.6
## Folds away by itself this long after the last round.
@export_range(0.0, 2.0) var empty_stow_delay: float = 0.45
## Hip spread (degrees, cone half-angle) and while aiming (LT).
@export_range(0.0, 5.0) var hip_spread_deg: float = 0.35
@export_range(0.0, 5.0) var ads_spread_deg: float = 0.0
## LT: field of view scale and the time to get there.
@export_range(0.3, 1.0) var ads_fov_scale: float = 0.8
@export_range(0.02, 1.0) var ads_time: float = 0.16

@export_group("Kick")
## Camera kick per shot: degrees up, right, roll (peak of the spring).
@export var camera_kick_deg: Vector3 = Vector3(5.5, 0.6, 2.5)
## The arm thrown back (m) and up (deg) by each shot.
@export var arm_kick_back: float = 0.075
@export var arm_kick_rise_deg: float = 11.0
@export var arm_spring_hz: float = 7.0
@export_range(0.05, 1.0) var arm_spring_damping: float = 0.45
## Field of view punch (degrees) and how fast it settles (1/s).
@export var fov_punch_deg: float = 7.0
@export var fov_punch_recover: float = 6.0
## Weak motor, strong motor, seconds.
@export var rumble_fire: Vector3 = Vector3(1.0, 1.0, 0.28)
## World slows to this for a moment on each shot (heavy hit-stop feel), and for how long (real s).
@export_range(0.05, 1.0) var shot_hitstop_scale: float = 0.15
@export_range(0.0, 0.3) var shot_hitstop_time: float = 0.06

@export_group("Body stats (docs/design.md §3.6)")
## Bracing = structure × usable strength. At brace_ref (TL-3 + EM-2) the
## kick is as tuned above; a stronger frame shrinks it (down to
## brace_min_kick of it), a weaker one grows it.
@export var brace_ref: float = 1.67
@export_range(0.1, 1.0) var brace_min_kick: float = 0.45
## Rounds recharge at regen_per_s × headroom ÷ power_ref_w (supply minus
## draw while it's folded), between these limits.
@export var power_ref_w: float = 300.0
@export var recharge_min_scale: float = 0.35
@export var recharge_max_scale: float = 1.8

@export_group("Look")
## Glow colour of the coils, seams and round counter.
@export var glow_color: Color = Color(0.45, 0.72, 1.0)
## Glow energy: idle (armed), just fired (flash), while folding.
@export var glow_armed: float = 3.0
@export var glow_flash: float = 14.0
@export var glow_folded: float = 0.4
## The arm comes up from this far below during the first part of the deploy (m).
@export var raise_drop: float = 0.32
## Fraction of the deploy spent raising the arm into view.
@export_range(0.05, 0.6) var raise_share: float = 0.22
