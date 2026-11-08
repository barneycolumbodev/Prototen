class_name MeleeConfig
extends Resource
## The R3 strike (CLAUDE.md §9.4: right stick click = melee). Numbers for the
## base operative; the body scales them (docs/design.md §3.6): damage ×
## melee_power × usable strength, shove × mass/100 × usable strength ×
## impact, recovery ÷ melee_speed. Tuning in data/player/melee_default.tres.

## How far (m, camera to the enemy's chest) and how wide (degrees) it reaches.
@export var reach: float = 2.1
@export_range(10.0, 120.0) var cone_deg: float = 55.0
## Seconds from the press to the hit, and from the hit until the next strike.
@export_range(0.0, 0.5) var windup: float = 0.07
@export_range(0.1, 2.0) var recovery: float = 0.42
## Damage to the enemy and the speed (m/s) it shoves him at.
@export var damage: float = 55.0
@export var push: float = 7.0
## Shoves at least this fast break the body (lethal, ragdoll).
@export var lethal_push: float = 17.0
@export var morale_loss: float = 0.25
## The operative lunges at the target this fast (m/s) for the windup.
@export var lunge_speed: float = 5.0
## Feel: hit-stop (s, world scale), rumble (weak, strong, s), camera kick (deg).
@export var hitstop_time: float = 0.07
@export_range(0.05, 1.0) var hitstop_scale: float = 0.08
@export var rumble: Vector3 = Vector3(0.8, 1.0, 0.18)
@export var camera_kick_deg: Vector3 = Vector3(-2.2, 1.4, 3.5)
## The gun swings in (m, deg) on a strike.
@export var viewmodel_jolt: Vector3 = Vector3(-0.06, -0.03, -0.12)
@export var viewmodel_jolt_rot_deg: Vector3 = Vector3(-12.0, 18.0, 28.0)
