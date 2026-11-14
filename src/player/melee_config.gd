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
## Camera kick (deg) as the arm cocks back, before the blow.
@export var windup_kick_deg: Vector3 = Vector3(0.7, -0.8, -1.6)

@export_group("Knife animation")
## The first-person hand and KB-1 knife (raw_assets/weapons/knife/build.py).
@export var knife_scene: PackedScene
## Keys of the slash (KnifeViewmodel), in seconds at melee_speed 1; the blow
## lands at `windup`, so one key should sit there. Camera space (−Z ahead,
## +X right, +Y up): where the handle is, the direction the forearm runs back
## toward the elbow, and the way the edge faces (the slash direction).
@export var knife_times: PackedFloat32Array = []
@export var knife_pos: PackedVector3Array = []
@export var knife_forearm: PackedVector3Array = []
@export var knife_edge: PackedVector3Array = []
## The gun is fully down after `gun_away_in` s and comes back up from `gun_return_at` to the end of the slash.
@export var gun_away_in: float = 0.06
@export var gun_return_at: float = 0.3
## Where the gun goes (camera space m, and its own rotation in degrees).
@export var gun_away_offset: Vector3 = Vector3(0.06, -0.3, 0.08)
@export var gun_away_rot_deg: Vector3 = Vector3(-40.0, -10.0, -25.0)
## The trail along the edge: how long it lasts (s), the tip speed (m/s) where it starts showing, its colours.
@export var trail_time: float = 0.07
@export var trail_min_speed: float = 3.0
@export var trail_color: Color = Color(0.75, 0.86, 1.0, 0.55)
@export var trail_blood_color: Color = Color(0.55, 0.02, 0.02, 0.8)
## Blood on the blade: how much of it one cut / one kill adds (0..1 covers
## the whole blade; it never comes off), and seconds for wet blood to dry dark.
@export var blood_per_cut: float = 0.12
@export var blood_per_kill: float = 0.2
@export var blood_dry_time: float = 45.0
