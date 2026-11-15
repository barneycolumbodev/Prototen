class_name EnemyConfig
extends Resource
## One enemy role (data/enemies/*.tres): body, armour, weapon, behaviour.
## Triad roles for M1 (owner, 2026-11-03): Gunman (rifle), Enforcer
## (shotgun + plate carrier), Red Pole (lieutenant, SMG).

@export var display_name: String = "Gunman"
## Shown with callouts ("GUNMAN: Augment!").
@export var callsign: String = "GUNMAN"

@export_group("Look")
## What men in this role wear (data/enemies/outfits/*.tres): one outfit is
## picked per man, then garments, colours, prints, tattoos (TriadLook).
@export var outfits: Array[Outfit] = []
@export var plate_carrier: bool = false
## Whole-body scale (model, hitboxes, capsule). Owner, 2026-11-05: enemies read
## too small on the phone screen; 1.08 made a 1.75 m man about 1.89 m.
## 2026-11-11 ("they are quite small"): 1.12, about 1.96 m.
@export_range(0.8, 1.3) var body_scale: float = 1.12
## Rim light that outlines the body against a dark background, stronger with
## distance (owner: "they need to stand out against the environment, think
## Halo CE"). 0 = off. Fades out when he dies.
@export var rim_color: Color = Color(0.62, 0.72, 0.85)
@export_range(0.0, 2.0) var rim_strength: float = 1.0
## Soft light from the viewer on his front (2026-11-11: "really hard to see"),
## a little more with distance, so a man in a dark street still reads. 0 = off.
@export_range(0.0, 1.0) var fill_light: float = 0.45
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
## Armour is physical: an Enforcer's carrier holds AR500 plates and
## Ballistics decides what gets through. A stopped round still does this
## fraction of its damage (blunt trauma).
@export_range(0.0, 1.0) var armor_blunt: float = 0.15
## Damage to a limb before it is crippled (leg: limp/crawl, arm: weapon dropped).
@export_range(5.0, 200.0) var limb_cripple: float = 18.0

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
## Hears the operative moving within this many metres at a full sprint with
## noise ×1 (scales with speed and the body's noise stat; crouched is quieter).
@export_range(0.0, 60.0) var footstep_hearing: float = 13.0

@export_group("Morale")
@export_range(0.0, 1.0) var courage: float = 0.6
@export_range(0.0, 1.0) var suppression_resist: float = 0.4

@export_group("Melee")
## A blade instead of a gun (the Hatchet Man, docs/design.md §8.8): no
## shooting, no cover-to-cover firefight. He flanks, sprints from cover to
## cover, vaults what's low enough, and closes in for a telegraphed chop
## (MeleeBrain). `gun_scene` is then unused: one of `melee_scenes` is
## picked per man.
@export var melee: bool = false
@export var melee_scenes: Array[PackedScene] = []
## Damage of a chop that lands, before armour: scaled by the operative's
## damage per kJ over the bare suit's 7 (armour parts lower it).
@export_range(0.0, 500.0) var melee_damage: float = 42.0
## Seconds from the start of the chop to the blow (the tell: the blade goes
## up high over his shoulder), and from the blow until he can move again.
@export_range(0.15, 1.5) var melee_windup: float = 0.46
@export_range(0.1, 2.0) var melee_recovery: float = 0.55
## The blow lands if the operative is within this reach (m, flat, from his
## feet) and this arc (degrees, full) in front of him when it falls.
@export_range(0.8, 4.0) var melee_reach: float = 2.0
@export_range(20.0, 240.0) var melee_arc_deg: float = 110.0
## He starts the chop this close (m), and lunges (m/s) through the windup,
## turning toward the operative at most this fast (deg/s): a sidestep, a
## slide or a jump at the right moment leaves him swinging at air.
@export_range(1.0, 6.0) var melee_commit_range: float = 3.0
@export_range(0.0, 10.0) var melee_lunge_speed: float = 4.2
@export_range(30.0, 720.0) var melee_track_deg: float = 200.0
## This much damage taken during the windup (added up) breaks off the chop:
## two quick Five-seveN rounds (about 13 each to the body), one rifle round.
@export_range(1.0, 200.0) var melee_interrupt: float = 20.0
## Shove (m/s) and view kick (degrees) the operative takes from a chop.
@export_range(0.0, 10.0) var melee_push: float = 3.0
@export_range(0.0, 20.0) var melee_kick_deg: float = 7.0
## Inside this range (m) he stops hopping between covers and charges.
@export_range(2.0, 30.0) var charge_range: float = 9.0
## Approach angle (degrees) off the operative's facing: he runs wide to come
## in from the side, and switches sides when he's looked at.
@export_range(0.0, 150.0) var flank_angle_deg: float = 75.0
## Seconds crouched at each cover on the way in (min, max).
@export var cover_pause: Vector2 = Vector2(0.35, 1.1)
## Highest obstacle (m) he vaults, and how long a vault takes (s).
@export_range(0.4, 1.6) var vault_height: float = 1.25
@export_range(0.25, 1.5) var vault_time: float = 0.55
