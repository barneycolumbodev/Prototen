class_name FanShieldData
extends ActivePartData
## BW-6 Bulwark Fan Shield (2026-11-10): seven boron-carbide leaves folded
## along the left forearm that fan out into a shield. LB (with it selected)
## raises it, LB again folds it. Rounds that come from the front are stopped
## and their energy is taken from the shield's integrity (the charge, in
## kJ); at zero it breaks and needs a long cooldown. It takes the left hand,
## so two-handed guns go away: use it with the Gauss arm, the whip, or the
## R3 strike (a shield bash). Tuning in data/body/parts/bw6_fan_shield.tres.

@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Protection")
## Half-angle (deg) of the cone in front of the view it covers.
@export_range(10.0, 180.0) var arc_deg: float = 75.0
## Integrity lost per kJ stopped.
@export var loss_per_kj: float = 1.0
## Part of a stopped round's damage that still gets through (blunt trauma).
@export_range(0.0, 1.0) var leak: float = 0.0
## Structure at which `charge_max` applies; integrity scales with structure ÷ this.
@export var structure_ref: float = 1.45
## Seconds before it can come up again after breaking.
@export var break_cooldown: float = 5.0

@export_group("Handling")
## Move speed while it's up.
@export_range(0.3, 1.0) var move_scale: float = 0.85
## R3 strike shove multiplier while it's up (a shield bash).
@export var bash_bonus: float = 1.6

@export_group("Look")
@export var glow_color: Color = Color(1.0, 0.62, 0.25)
@export var glow_idle: float = 1.6
@export var glow_hit: float = 9.0
