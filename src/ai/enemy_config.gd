class_name EnemyConfig
extends Resource
## One enemy role (data/enemies/*.tres): body, armour, weapon, behaviour.
## Triad roles for M1 (owner, 2026-11-03): Gunman (rifle), Enforcer
## (shotgun + plate carrier), Red Pole (lieutenant, SMG).

@export var display_name: String = "Gunman"
## Shown with callouts ("GUNMAN: Augment!").
@export var callsign: String = "GUNMAN"

@export_group("Look")
@export var jacket_tint: Color = Color(0.07, 0.072, 0.078)
@export var trousers_tint: Color = Color(0.16, 0.16, 0.15)
@export var skin_tint: Color = Color(1, 1, 1)
@export var plate_carrier: bool = false
## Third-person gun model (assets/weapons/enemy/*.gltf) and its ballistics.
@export var gun_scene: PackedScene
@export var weapon: WeaponData
## Muzzle in the gun model's space (Blender +X forward, +Z up → Godot +X, +Y).
@export var muzzle: Vector3 = Vector3(0.635, 0.047, 0.0)

@export_group("Body")
@export_range(10.0, 1000.0) var health: float = 100.0
## Damage multiplier per zone (docs/design.md §5.1).
@export var zone_multipliers: Dictionary[StringName, float] = {
	&"head": 4.0, &"neck": 3.0, &"chest": 1.25, &"stomach": 1.0, &"pelvis": 1.0,
	&"l_upper_arm": 0.6, &"l_forearm": 0.5, &"l_hand": 0.35, &"r_upper_arm": 0.6, &"r_forearm": 0.5, &"r_hand": 0.35,
	&"l_thigh": 0.75, &"l_shin": 0.6, &"l_foot": 0.4, &"r_thigh": 0.75, &"r_shin": 0.6, &"r_foot": 0.4,
}
## Zones covered by armour and the energy (J) a round must still carry to get
## through it. Stopped rounds do `armor_blunt` of their damage (bruising).
@export var armor_zones: Array[StringName] = []
@export_range(0.0, 10000.0) var armor_stop_j: float = 0.0
@export_range(0.0, 1.0) var armor_blunt: float = 0.15
## Damage to a limb before it is crippled (leg: limp/crawl, arm: weapon dropped).
@export_range(5.0, 200.0) var limb_cripple: float = 28.0

@export_group("Movement")
@export_range(0.5, 4.0) var walk_speed: float = 1.4
@export_range(1.0, 8.0) var run_speed: float = 4.4
@export_range(1.0, 30.0) var turn_speed_deg: float = 220.0

@export_group("Combat")
## Rounds per burst, seconds between rounds, pause between bursts.
@export_range(1, 30) var burst_min: int = 3
@export_range(1, 30) var burst_max: int = 6
@export_range(0.03, 2.0) var fire_interval: float = 0.1
@export_range(0.0, 5.0) var burst_pause: float = 0.9
@export_range(1, 200) var magazine: int = 30
@export_range(0.5, 6.0) var reload_time: float = 2.4
## Aim error (degrees, full cone) at 10 m when calm and settled; grows with
## suppression and target speed, shrinks the longer they hold aim.
@export_range(0.0, 20.0) var aim_error_deg: float = 3.2
@export_range(0.0, 5.0) var aim_settle_time: float = 1.2
## Seconds from seeing the player to the first shot.
@export_range(0.0, 3.0) var reaction_time: float = 0.55
@export_range(2.0, 80.0) var preferred_range: float = 14.0
@export_range(2.0, 120.0) var max_range: float = 45.0
## Pushes toward the player instead of holding cover.
@export var aggressive: bool = false
## Officer: holds morale up while alive, the squad wavers when he dies.
@export var officer: bool = false

@export_group("Perception")
@export_range(5.0, 120.0) var sight_range: float = 45.0
@export_range(20.0, 180.0) var sight_fov_deg: float = 130.0
## Hearing range for unsuppressed shots; suppressed ones count at a fraction.
@export_range(5.0, 120.0) var hearing_range: float = 40.0
@export_range(0.0, 1.0) var suppressed_hearing: float = 0.25

@export_group("Morale")
@export_range(0.0, 1.0) var courage: float = 0.6
@export_range(0.0, 1.0) var suppression_resist: float = 0.4
