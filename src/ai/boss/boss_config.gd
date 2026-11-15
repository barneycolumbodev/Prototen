class_name BossConfig
extends Resource
## A boss's own tuning (docs/design.md §8.7a): his name card, his hardware,
## his three attacks, staggers and rage, the entrance and the execution.
## Hung on an EnemyConfig (`boss`); the body, health and zones are there.
## data/enemies/bosses/*.tres

@export_group("Name")
## The name card in the entrance and over the health bar.
@export var title: String = "THE INCENSE MASTER"
@export var subtitle: String = "438  ·  Triad enforcer  ·  black-market Gauss arm"

@export_group("Drop")
## What he drops (Survival, docs/design.md §8.7): this active at Mk I if the
## operative doesn't have it, or its next mark if he does.
@export var drop: ActivePartData

@export_group("Hardware")
## assets/characters/incense_master/hardware.gltf: arm_upper, arm_fore,
## arm_hand, pendant (each in its bone's space) and the empty `muzzle`.
@export var hardware: PackedScene
## The pendant's nudge on the chest bone (m, bone space) so it sits on the skin.
@export var pendant_offset: Vector3 = Vector3.ZERO
## The coils' light: idle, while charging (rises to this), and the flash of a shot.
@export var glow_color: Color = Color(0.45, 0.8, 1.0)
@export var glow_idle: float = 1.2
@export var glow_charged: float = 9.0
@export var glow_flash: float = 18.0

@export_group("Movement")
## Real metres per second (the man is already scaled): a heavy walk, and the
## charge when he's far off or enraged.
@export_range(0.5, 6.0) var walk_speed: float = 2.3
@export_range(1.0, 10.0) var charge_speed: float = 5.0
## He charges beyond this distance (m) if he can't use the cannon.
@export_range(4.0, 40.0) var charge_beyond: float = 12.0
@export_range(30.0, 720.0) var turn_deg: float = 150.0

@export_group("Haymaker")
## Close: the prosthetic cocked back by his side (the tell) and swung across
## at head height. Lands `swing_windup` s in if the operative is within reach
## and arc. Dodged by a sidestep, a slide or a jump back.
@export_range(1.0, 6.0) var swing_commit: float = 3.4
@export_range(1.0, 6.0) var swing_reach: float = 3.5
@export_range(30.0, 240.0) var swing_arc_deg: float = 130.0
@export_range(0.2, 1.5) var swing_windup: float = 0.52
@export_range(0.0, 400.0) var swing_damage: float = 48.0
## Thrown along the swing (m/s) and up.
@export_range(0.0, 30.0) var swing_push: float = 11.0
@export_range(0.0, 15.0) var swing_lift: float = 4.0
@export_range(0.0, 10.0) var swing_cooldown: float = 1.8

@export_group("Ground pound")
## Fists up over his head (the tell, with a roar), then the prosthetic into the
## ground: a shockwave out to `pound_radius`, `pound_damage_near` at the fist
## down to `pound_damage_far` at the edge, a throw up and away. In the air at
## the moment it lands (`pound_air` above the ground) it misses you.
## His own men in it are thrown too.
@export_range(1.0, 12.0) var pound_trigger: float = 6.5
@export_range(1.0, 15.0) var pound_radius: float = 8.0
@export_range(0.3, 2.5) var pound_windup: float = 1.0
@export_range(0.0, 400.0) var pound_damage_near: float = 55.0
@export_range(0.0, 400.0) var pound_damage_far: float = 10.0
@export_range(0.0, 20.0) var pound_lift: float = 6.5
@export_range(0.0, 30.0) var pound_push: float = 9.0
@export_range(0.0, 2.0) var pound_air: float = 0.35
@export_range(0.0, 20.0) var pound_cooldown: float = 5.5
## Seconds the operative has been close before he'd rather pound than swing.
@export_range(0.0, 10.0) var pound_after_close: float = 2.5

@export_group("Gauss shot")
## Far: he plants, raises the arm and charges it (glow and whine) for
## `cannon_charge` s, tracking the operative at `cannon_track_deg`; for the
## last `cannon_lock` s he holds still, then fires a real slug
## (`cannon_round`, a Ballistics round: it goes through thin cover, and the
## LC-6 catches it). Without sight he fires where he last saw you.
@export var cannon_round: WeaponData
@export_range(2.0, 80.0) var cannon_min: float = 6.5
@export_range(5.0, 150.0) var cannon_max: float = 70.0
@export_range(0.3, 4.0) var cannon_charge: float = 1.5
@export_range(0.0, 1.5) var cannon_lock: float = 0.28
@export_range(5.0, 720.0) var cannon_track_deg: float = 80.0
@export_range(0.0, 10.0) var cannon_error_deg: float = 0.7
@export_range(0.0, 30.0) var cannon_cooldown: float = 6.0
## Shots in a volley (the second follows `cannon_gap` s later).
@export_range(1, 5) var cannon_shots: int = 1
@export_range(0.1, 2.0) var cannon_gap: float = 0.55

@export_group("Stagger")
## This much damage inside `stagger_window` s (or one hit from a Gauss slug,
## his own thrown back included) staggers him for `stagger_time` s: he breaks
## off whatever he was doing. Not again for `stagger_immunity` s.
@export_range(10.0, 2000.0) var stagger_damage: float = 220.0
@export_range(0.1, 3.0) var stagger_window: float = 0.8
@export_range(0.2, 4.0) var stagger_time: float = 1.1
@export_range(0.0, 15.0) var stagger_immunity: float = 4.0

@export_group("Rage")
## Below this share of his health he's faster and fires two slugs.
@export_range(0.0, 1.0) var rage_at: float = 0.5
@export_range(1.0, 2.0) var rage_speed: float = 1.25
@export_range(1, 5) var rage_shots: int = 2
@export_range(0.2, 1.0) var rage_cooldown_scale: float = 0.7

@export_group("Entrance")
## He comes down from this high (m) and this far behind the landing, lands
## `intro_fall` s in, and the camera cuts back after `intro_length` s.
@export_range(2.0, 40.0) var intro_drop_height: float = 13.0
@export_range(0.0, 20.0) var intro_drop_back: float = 4.0
@export_range(0.3, 3.0) var intro_fall: float = 0.9
@export_range(2.0, 10.0) var intro_length: float = 4.4
## Where he lands: this far in front of the operative (m), within this angle
## either side of where he's looking.
@export_range(5.0, 40.0) var intro_distance: float = 13.0
@export_range(0.0, 180.0) var intro_spread_deg: float = 70.0
## The landing's shockwave (radius m) and the knock it gives what's near.
@export_range(1.0, 15.0) var intro_shock_radius: float = 6.0

@export_group("Execution")
## On his knee: the prompt shows within this distance (m) and angle of view.
@export_range(1.0, 6.0) var execute_range: float = 3.2
@export_range(10.0, 90.0) var execute_view_deg: float = 45.0
## The operative's eye stands this far from his head (m, flat) for the punches.
@export_range(0.3, 1.5) var execute_stand: float = 0.62
## Seconds into the execution each punch lands; the last one takes the head.
@export var punch_times: PackedFloat32Array = PackedFloat32Array([0.95, 1.4, 1.78, 2.55])
## Each punch: the fist's draw back and strike (s).
@export_range(0.05, 0.6) var punch_windup: float = 0.2
@export_range(0.05, 0.6) var punch_last_windup: float = 0.42
@export_range(0.05, 0.6) var punch_recover: float = 0.18
## After the last punch: let go, look at the fist, shake the blood off, lower it.
@export_range(0.1, 2.0) var release_time: float = 0.45
@export_range(0.3, 3.0) var examine_time: float = 1.5
@export_range(0.2, 2.0) var shake_time: float = 0.75
@export_range(0.1, 1.5) var lower_time: float = 0.45
## Slow motion as the last punch lands: world scale and how long (real s).
@export_range(0.05, 1.0) var finish_slowmo: float = 0.25
@export_range(0.0, 2.0) var finish_slowmo_time: float = 0.55
