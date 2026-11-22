class_name WeaponData
extends Resource
## Everything that defines how a gun shoots, handles and feels
## (docs/design.md §5.2–5.4, docs/m1-gunplay-plan.md). One .tres per weapon
## in data/weapons/. The on-device tuning menu edits these live.
##
## Weapon space follows the glTF models: +X muzzle, +Y up, +Z the gun's right
## side, origin on the bore axis above the grip.

## Which body proficiency stat it uses (docs/design.md §3.6): handgun,
## shotgun, rifle (rifles and rail guns) or heavy (machine guns).
enum WeaponClass { HANDGUN, SHOTGUN, RIFLE, HEAVY }
## Weapon wheel category (owner, 2026-11-20: categories like GTA V's wheel;
## the stick picks a category, the D-pad scrolls the guns in it).
enum WheelCategory { PISTOLS, SMGS, SHOTGUNS, RIFLES, HEAVY, SPECIAL }
const WHEEL_NAMES: PackedStringArray = ["PISTOLS", "SMGs", "SHOTGUNS", "RIFLES", "HEAVY", "SPECIAL"]

@export var display_name: String = "Five-seveN SR"
@export var weapon_class: WeaponClass = WeaponClass.HANDGUN
@export var wheel_category: WheelCategory = WheelCategory.PISTOLS
@export var caliber: String = "5.7×28mm"
## Weapon wheel icon (raw_assets/ui/weapon_icons/build.py renders one per gun).
@export var icon: Texture2D

@export_group("Magazine")
@export_range(1, 500) var magazine_size: int = 20
## A tactical reload keeps the round in the chamber (20 + 1). False = open
## bolt (belt-fed MG): no +1, and every reload is the same length.
@export var closed_bolt: bool = true
@export_range(0, 9999) var reserve_ammo: int = 200
## Range/testing: reserve never runs out.
@export var infinite_reserve: bool = true

@export_group("Launcher")
## A grenade launcher: each shot launches this round (Grenades) from the
## muzzle instead of firing a Ballistics round. Aimed, the fire control lases
## the range and programs an airburst (GrenadeData, PlayerWeapon.fcs_*).
@export var grenade: GrenadeData
## Revolver cylinder: chambers (0 = none). The rig turns node "cylinder" one
## chamber per shot about `cylinder_axis` (a line along X through this point,
## weapon space) and shows a "round_<n>" in each loaded chamber.
@export_range(0, 12) var cylinder_chambers: int = 0
@export var cylinder_axis: Vector3 = Vector3.ZERO
## Seconds the cylinder takes to turn one chamber.
@export_range(0.01, 0.5) var cylinder_index_time: float = 0.07
## The crane the cylinder swings out on to load ("crane", "cylinder" and the
## rounds turn about a line along X through `crane_hinge` by `crane_swing_deg`).
@export var crane_hinge: Vector3 = Vector3.ZERO
@export_range(-180.0, 180.0) var crane_swing_deg: float = 0.0

@export_group("Plasma")
## A plasma gun (the SL-9 Slagger): hold the trigger to charge, let go to
## fire one bolt of the charge (PlasmaBolts). Charge, bolt, burn and gore
## values live in the PlasmaData; recoil and kick here are the full-charge
## values (PlasmaData.recoil scales them).
@export var plasma: PlasmaData

@export_group("Lever action")
## A lever action (the Governor): after each shot the lever is thrown down
## and back up (`lever_delay` after the shot, over `lever_time`), which runs
## the bolt back (`bolt_travel`, node "bolt"), throws the case out at the
## bottom of the stroke and cocks the hammer (node "hammer", fallen
## `hammer_fall_deg` about `hammer_hinge` after a shot). The lever (node
## "lever") swings `lever_open_deg` about the line along the gun's side
## through `lever_hinge` (weapon space). fire_interval should be at least
## lever_delay + lever_time. The gun cants by `lever_cant_deg` (x roll, y
## yaw, z muzzle rise) and moves `lever_cant_offset` (camera space) at the
## bottom of the stroke. `rumble_lever_open` / `rumble_lever_close`: the
## clunks in the hands. Loading: one round at a time through the gate (node
## "load_round" is shown sliding in from `load_round_from`).
@export var lever_action: bool = false
@export var lever_hinge: Vector3 = Vector3.ZERO
@export_range(-120.0, 120.0) var lever_open_deg: float = 50.0
@export_range(0.0, 0.5) var lever_delay: float = 0.12
@export_range(0.1, 1.5) var lever_time: float = 0.4
@export_range(0.0, 0.15) var bolt_travel: float = 0.05
@export var hammer_hinge: Vector3 = Vector3.ZERO
@export_range(-90.0, 90.0) var hammer_fall_deg: float = -32.0
@export var lever_cant_deg: Vector3 = Vector3(-10.0, 4.0, 7.0)
@export var lever_cant_offset: Vector3 = Vector3(0.0, -0.015, 0.02)
@export var rumble_lever_open: Vector3 = Vector3(0.2, 0.5, 0.06)
@export var rumble_lever_close: Vector3 = Vector3(0.45, 0.85, 0.09)
@export var load_round_from: Vector3 = Vector3(-0.02, -0.03, 0.06)
## How much of the lever's swing the firing hand follows (0 = stays on the grip).
@export_range(0.0, 1.0) var lever_hand_follow: float = 0.8

@export_group("Pump action")
## A pump action (the SPAS-12, pump only): `pump_delay` after the shot the
## gun comes up, muzzle high (`pump_raise_deg`: x roll, y yaw, z muzzle rise,
## about `grip_pivot`; `pump_raise_offset` camera space), the fore-end
## (node "pump", the support arm "support_arm" with it, the bolt "bolt" too)
## is racked back `pump_travel` and slammed forward, and the gun comes back
## down; `pump_time` for the whole move. The hull flies out at the back of
## the stroke. fire_interval should be at least pump_delay + pump_time.
## Loads one shell at a time (`round_load_time`, node "load_round" pushed in
## from `load_round_from`); if it went in empty, the pump chambers one.
@export var pump_action: bool = false
@export_range(0.0, 0.5) var pump_delay: float = 0.08
@export_range(0.1, 1.5) var pump_time: float = 0.62
@export_range(0.0, 0.2) var pump_travel: float = 0.085
@export var pump_raise_deg: Vector3 = Vector3(-8.0, 6.0, 26.0)
@export var pump_raise_offset: Vector3 = Vector3(-0.015, 0.035, 0.02)
## Where in the stroke (0..1 of pump_time) the "pump_back" and "pump_forward"
## sounds start. Recorded racks (2026-11-21) begin at the unlock and the start
## of the forward push, so they start early enough that their hard stop and
## lock land when the fore-end reaches the rear (0.42) and home (0.62).
@export_range(0.0, 1.0) var pump_back_sound_t: float = 0.41
@export_range(0.0, 1.0) var pump_forward_sound_t: float = 0.6
@export var rumble_pump_back: Vector3 = Vector3(0.3, 0.6, 0.07)
@export var rumble_pump_forward: Vector3 = Vector3(0.6, 1.0, 0.1)
## Colour of the spent hull the pump throws out.
@export var hull_color: Color = Color(0.78, 0.1, 0.07)

@export_group("Fire")
## Fastest the mechanism cycles (seconds between shots). Semi-auto.
@export_range(0.03, 1.0) var fire_interval: float = 0.1
@export var automatic: bool = false
## The AUG's progressive trigger (automatic guns): a light pull fires one
## round per pull; pulled past `full_auto_pull` (raw right-trigger travel,
## 0..1) it fires automatic. Mouse and digital triggers are always full.
@export var progressive_trigger: bool = false
@export_range(0.4, 1.0) var full_auto_pull: float = 0.85
## A trigger pull this early before the gun is ready still fires when it is.
@export_range(0.0, 0.3) var fire_buffer: float = 0.12
## Delay between leaving a sprint and the first shot.
@export_range(0.0, 0.5) var sprint_to_fire: float = 0.13
## Fires on the run: the trigger doesn't end a sprint, and the gun comes up
## out of the sprint pose while firing (the MP5's run-and-gun).
@export var sprint_fire: bool = false
@export_range(0.0, 1.5) var draw_time: float = 0.4
## Seconds to put the gun away when switching to the other one.
@export_range(0.05, 1.5) var holster_time: float = 0.2

@export_group("Carry")
## Movement while this gun is out, as a fraction of normal. Universal for now;
## later it comes from the body's strength and load parts (docs/design.md §3.2).
@export_range(0.3, 1.0) var carry_speed_scale: float = 1.0
@export_range(0.3, 1.0) var carry_sprint_scale: float = 1.0
@export_range(0.3, 1.0) var carry_jump_scale: float = 1.0
## Look speed while this gun is out (a heavy gun turns slower).
@export_range(0.3, 1.0) var carry_turn_scale: float = 1.0

@export_group("Reload")
## Magazine change with a round still chambered.
@export_range(0.3, 5.0) var reload_tactical_time: float = 1.35
## Empty gun: magazine change plus slide release.
@export_range(0.3, 5.0) var reload_empty_time: float = 1.75
## Fraction of the reload where the old magazine leaves the gun.
@export_range(0.0, 1.0) var mag_out_point: float = 0.22
## Fraction where the new magazine seats; ammo is committed from here.
@export_range(0.0, 1.0) var mag_in_point: float = 0.6
## One round at a time (a revolver cylinder): > 0 = seconds per round. The
## reload opens the gun (`reload_open_time`, spent cases out), loads rounds
## one by one until it's full, then closes (`reload_close_time`). A trigger
## pull with a round in closes it early; sprinting or switching stops it with
## whatever went in.
@export_range(0.0, 2.0) var round_load_time: float = 0.0
@export_range(0.0, 2.0) var reload_open_time: float = 0.4
@export_range(0.0, 2.0) var reload_close_time: float = 0.35

@export_group("Ballistics")
## Metres per second at the muzzle (SS190 from a 4.8" barrel with can ≈ 650).
@export_range(50.0, 3500.0) var muzzle_velocity: float = 650.0
@export_range(0.1, 50.0) var bullet_mass_g: float = 2.0
## Air drag: speed falls as v(x) = v0 * e^(-k x). 0.0015/m ≈ 14 % lost over 100 m.
@export_range(0.0, 0.05) var drag_per_m: float = 0.0015
@export_range(0.0, 2.0) var gravity_scale: float = 1.0
@export_range(10.0, 6000.0) var max_range: float = 600.0
## How many surfaces one round may pass through.
@export_range(0, 24) var max_penetrations: int = 6
## Augment hook: multiplies the energy available for punching through material.
@export_range(0.1, 5.0) var penetration_scale: float = 1.0
@export_range(0, 4) var max_ricochets: int = 2

@export_group("Shot")
## Projectiles per shot (shotgun pellets) and the pattern they spread into
## around the aim point (full width, degrees). 1 / 0 for rifles and pistols.
@export_range(1, 32) var pellets: int = 1
@export_range(0.0, 30.0) var pattern_deg: float = 0.0
## Each projectile is a burning ember (Dragon's Breath): drawn as a glowing
## streak, and leaves `burn_dps` for `burn_time` seconds on what it hits.
@export var embers: bool = false
@export_range(0.0, 200.0) var burn_dps: float = 0.0
@export_range(0.0, 10.0) var burn_time: float = 0.0

@export_group("Shell types")
## Loads this gun takes (data/weapons/ammo/). Empty = one fixed load (the
## values above). D-pad right/left picks the next/previous load, which swaps
## in a magazine of it and racks the chambered shell out (the empty reload).
@export var ammo_types: Array[AmmoData] = []
## Seconds after the last D-pad press before the swap starts (lets two taps skip a load).
@export_range(0.0, 1.0) var ammo_select_delay: float = 0.3

@export_group("Optic")
## Eye position and look point in weapon space through the optic (loads with
## `use_optic`), its zoom and how long it takes to get behind it.
@export var optic_eye_position: Vector3 = Vector3.ZERO
@export var optic_look_target: Vector3 = Vector3(1.0, 0.0, 0.0)
@export_range(0.3, 1.0) var optic_fov_scale: float = 0.9
@export_range(0.03, 1.0) var optic_ads_time: float = 0.3
@export_range(0.1, 1.5) var optic_sensitivity: float = 0.75
## The optic is part of the gun (the AUG's 1.5x scope): aiming always goes
## through it with the values above, no shell type needed.
@export var integral_optic: bool = false
## What the HUD scope view draws: &"chevron" (the Saiga slug optic's ranging
## reticle) or &"ring" (the AUG's circle, the aim point in its centre).
@export var scope_reticle: StringName = &"chevron"
## Ring reticle: angular diameter (degrees of true field) and how much of the
## screen's height the eyepiece fills.
@export_range(0.2, 6.0) var scope_ring_deg: float = 1.6
@export_range(0.2, 0.6) var scope_eyepiece: float = 0.44

@export_group("Clear magazine")
## A see-through magazine (the AUG's): the viewmodel's "mag_rounds" show the
## rounds left and its "mag_follower" rides up under the last one, turning
## `mag_follower_step_deg` per round gone about the line along Z through
## `mag_arc_center` (weapon space; the magazine's curve).
@export var mag_arc_center: Vector3 = Vector3.ZERO
@export_range(-5.0, 5.0) var mag_follower_step_deg: float = 0.0

@export_group("Damage")
## Damage per joule the round leaves inside a body.
@export_range(0.0, 1.0) var damage_per_joule: float = 0.14
## Every hit deals at least this much (temporary cavity, shock).
@export_range(0.0, 500.0) var min_damage: float = 10.0
## Multiplies real bullet momentum for physics pushes (props, plates, ragdolls).
@export_range(0.0, 200.0) var impulse_scale: float = 30.0

## How hard a man this round kills is thrown (× the usual push: a .45-70
## carries him off his feet), and the shove it gives a man it doesn't kill
## (m/s; 0 = only the usual flinch).
@export_range(0.5, 4.0) var ragdoll_push: float = 1.0
@export_range(0.0, 12.0) var stagger_push: float = 0.0

## Special gore for this round (Gore.special_hit): &"gauss" = the GX-4 arm
## cannon's corkscrew wound and electrocution. Empty = the normal wounds.
@export var gore_style: StringName = &""

@export_group("Capacitor and heat")
## Railguns: seconds after a shot until the capacitor bank is full again.
## 0 = a conventional gun (every shot full power, no heat).
@export_range(0.0, 3.0) var charge_time: float = 0.0
## Energy of a shot fired at the earliest moment (one `fire_interval` after
## the last), as a fraction of a full-charge shot. Velocity goes with √energy.
@export_range(0.1, 1.0) var min_charge_power: float = 1.0
## Rail heat added by a full-power shot (1.0 = overheated, forced vent).
@export_range(0.0, 1.0) var heat_per_shot: float = 0.0
## Heat lost per second once the gun has rested `heat_cool_delay` seconds.
@export_range(0.0, 5.0) var heat_cool_per_s: float = 0.3
@export_range(0.0, 3.0) var heat_cool_delay: float = 0.4
## Forced vent after overheating: seconds the gun can't fire.
@export_range(0.1, 5.0) var vent_time: float = 1.5
## How far the vent shroud (node "vent") lifts while venting, metres (+Y).
@export_range(0.0, 0.05) var vent_lift: float = 0.0
## Emissive parts (node "glow"): colour when cool and when hot, and emission
## energy from an empty (x) to a full (y) capacitor.
@export var glow_color: Color = Color(0.35, 0.85, 1.0)
@export var glow_hot_color: Color = Color(1.0, 0.42, 0.12)
@export var glow_energy: Vector2 = Vector2(0.5, 4.0)

@export_group("Accuracy")
## Mechanical precision when aimed, minutes of angle (1 MOA ≈ 3 cm at 100 m).
@export_range(0.0, 20.0) var mechanical_moa: float = 1.5
## Hip-fire cone (degrees, full width).
@export_range(0.0, 10.0) var hip_spread_deg: float = 0.8
## Extra hip spread at full walking speed.
@export_range(0.0, 10.0) var move_spread_deg: float = 1.1
@export_range(0.0, 15.0) var air_spread_deg: float = 2.5
## Extra hip spread while firing continuously (the gun walks around at the
## hip), degrees per second of sustained fire, up to `hip_walk_max_deg`.
@export_range(0.0, 20.0) var hip_walk_deg_s: float = 0.0
@export_range(0.0, 20.0) var hip_walk_max_deg: float = 0.0
## Extra spread added per shot, recovers over time.
@export_range(0.0, 5.0) var bloom_per_shot_deg: float = 0.3
@export_range(0.0, 10.0) var bloom_max_deg: float = 1.5
@export_range(0.0, 30.0) var bloom_recovery_deg_s: float = 4.5
## Fraction of hip spread, movement spread and bloom that still applies aimed.
@export_range(0.0, 1.0) var ads_spread_scale: float = 0.12
## Fraction of the viewmodel's turn (sway, recoil, poses) the shots follow:
## 0 = rounds always leave along the centre of the view; above 0 they leave
## along the gun, and so does the laser, so the dot shows where they go.
@export_range(0.0, 1.0) var aim_follows_gun: float = 0.0

@export_group("Laser")
## Under-barrel laser: emitter in weapon space, how far it reaches (0 = no
## laser), colour. The beam and dot mark the centre of the shot cone, at the
## hip and aimed; the hip reticle gives way to the dot while it's on a surface.
@export var laser_point: Vector3 = Vector3.ZERO
@export_range(0.0, 500.0) var laser_range: float = 0.0
@export var laser_color: Color = Color(0.25, 1.0, 0.35)
## Dot size: angular diameter (degrees) and the smallest it gets up close (m).
@export_range(0.01, 2.0) var laser_dot_deg: float = 0.22
@export_range(0.001, 0.1) var laser_dot_min_m: float = 0.012
## Beam brightness near the emitter (0 = dot only; a real 5 mW beam is faint).
@export_range(0.0, 4.0) var laser_beam_energy: float = 0.6

@export_group("Recoil: camera")
## Peak upward kick per shot, degrees.
@export_range(0.0, 10.0) var kick_pitch_deg: float = 1.1
## Random sideways kick, ± degrees.
@export_range(0.0, 5.0) var kick_yaw_deg: float = 0.28
## Consistent drift to the right (+) or left (−), degrees per shot.
@export_range(-2.0, 2.0) var kick_yaw_bias_deg: float = 0.06
## Fraction of each kick that stays (muzzle climb you pull down yourself).
@export_range(0.0, 1.0) var kick_permanent: float = 0.18
@export_range(0.5, 30.0) var camera_spring_hz: float = 6.5
@export_range(0.1, 2.0) var camera_spring_damping: float = 0.9
## Recoil multiplier while aiming down sights.
@export_range(0.0, 2.0) var ads_recoil_scale: float = 0.7

@export_group("Recoil: viewmodel")
## Gun pushed back into the hand, metres.
@export_range(0.0, 0.2) var vm_kick_back: float = 0.03
## Muzzle flip, degrees.
@export_range(0.0, 30.0) var vm_kick_rise_deg: float = 7.0
@export_range(0.0, 15.0) var vm_kick_roll_deg: float = 2.5
@export_range(0.5, 30.0) var vm_spring_hz: float = 8.5
@export_range(0.1, 2.0) var vm_spring_damping: float = 0.55
@export_range(0.0, 2.0) var ads_vm_scale: float = 0.45
## How far the slide travels back and how long it takes to return, s.
@export_range(0.0, 0.1) var slide_travel: float = 0.032
@export_range(0.01, 0.3) var slide_cycle_time: float = 0.065

@export_group("Aim down sights")
## Seconds from hip to fully aimed.
@export_range(0.03, 1.0) var ads_time: float = 0.15
## Keep the hip reticle while aiming (the SPAS-12: the folded stock sits over
## the sights, so aiming brings the gun up to the shoulder and the ring stays,
## shrunk by `ads_spread_scale`).
@export var reticle_when_aimed: bool = false
## Field of view while aimed, as a fraction of the normal one.
@export_range(0.3, 1.0) var ads_fov_scale: float = 0.8
## Look sensitivity while aimed, before the FOV correction.
@export_range(0.1, 1.5) var ads_sensitivity: float = 0.75
@export_range(0.1, 1.0) var ads_move_speed: float = 0.65
## Eye position and look point in weapon space when aimed (on the sight line).
@export var ads_eye_position: Vector3 = Vector3(-0.5, 0.0262, 0.0)
@export var ads_look_target: Vector3 = Vector3(1.0, 0.0262, 0.0)

@export_group("Handling")
## Viewmodel lag when turning: degrees per (degree/second) of look speed.
@export_range(0.0, 0.1) var sway_per_turn: float = 0.018
@export_range(0.0, 15.0) var sway_max_deg: float = 6.0
@export_range(0.5, 30.0) var sway_spring_hz: float = 5.0
@export_range(0.1, 2.0) var sway_spring_damping: float = 0.7
## Walk bob amplitude (metres). Steps per second at walking speed: only for
## a viewmodel with no gait (the stride sets the cadence since 2026-11-17).
@export_range(0.0, 0.05) var bob_amount: float = 0.008
@export_range(0.5, 4.0) var bob_rate: float = 1.9
## Dip on landing, metres per (m/s) of fall speed.
@export_range(0.0, 0.02) var land_dip: float = 0.006
## How much the gun trails the body when you speed up, stop and strafe, and
## rides each heel strike (× MovementConfig gun_* values; 2026-11-17). A
## pistol is light in the hands, the MG42 swings.
@export_range(0.0, 3.0) var move_inertia: float = 1.0
## Pivot for procedural rotation (in the hand, behind the trigger guard).
@export var grip_pivot: Vector3 = Vector3(-0.07, -0.055, 0.0)
## Poses: offset in camera space (m; +X right, +Y up, +Z back) and rotation in
## weapon space (degrees: x = roll about the bore, y = yaw, z = muzzle rise).
@export var sprint_offset: Vector3 = Vector3(0.015, -0.05, 0.035)
@export var sprint_rotation_deg: Vector3 = Vector3(28.0, 18.0, -16.0)
@export var reload_offset: Vector3 = Vector3(-0.02, -0.03, 0.025)
@export var reload_rotation_deg: Vector3 = Vector3(32.0, -6.0, 14.0)
@export var draw_offset: Vector3 = Vector3(0.0, -0.2, 0.05)
@export var draw_rotation_deg: Vector3 = Vector3(0.0, 0.0, -40.0)
@export_range(0.5, 30.0) var pose_spring_hz: float = 4.5
@export_range(0.1, 2.0) var pose_spring_damping: float = 0.85

@export_group("Muzzle and ejection")
@export var muzzle_point: Vector3 = Vector3(0.284, 0.0, 0.0)
@export var ejection_point: Vector3 = Vector3(0.012, 0.018, 0.006)
## Shell launch velocity in weapon space, m/s (+Z = right).
@export var ejection_velocity: Vector3 = Vector3(-0.6, 1.6, 2.6)
## Brass/case ejection. Railguns have no case.
@export var ejects_shells: bool = true
## Suppressed: small flash and dim light.
@export_range(0.0, 3.0) var flash_scale: float = 0.35
@export_range(0.0, 20.0) var flash_light_energy: float = 1.2
@export var flash_color: Color = Color(1.0, 0.72, 0.42)
## Seconds the muzzle light takes to fade.
@export_range(0.02, 1.0) var flash_light_time: float = 0.06
## Ejects 12-gauge shells (tinted per load) instead of small brass cases.
@export var shotshell: bool = false
## Every Nth round is a tracer (0 = none).
@export_range(0, 10) var tracer_every: int = 0
## Muzzle smoke puffs per shot (suppressor puff / propellant smoke).
@export_range(0, 10) var smoke_per_shot: int = 3
## Ionized-air trail along the whole path of every round, seconds it lingers
## (0 = none). Drawn from the muzzle through every wall it crosses.
@export_range(0.0, 3.0) var beam_trail_time: float = 0.0
@export_range(0.001, 0.1) var beam_trail_width: float = 0.012
@export var beam_trail_color: Color = Color(0.55, 0.85, 1.0)
## Impact particles and hole size, relative to the surface defaults.
@export_range(0.5, 4.0) var impact_fx_scale: float = 1.0

@export_group("Sound")
## Sfx bank prefix for this gun's sounds ("mg42_" plays mg42_shot, mg42_mag_in...).
## Banks the prefix doesn't have fall back to the plain names.
@export var sound_prefix: String = ""
@export_range(-30.0, 6.0) var shot_volume_db: float = 0.0
## Shortest gap between room tails (automatic fire would stack dozens).
@export_range(0.0, 1.0) var tail_interval: float = 0.0

@export_group("Moving parts")
## Feed cover (node "cover"): hinge point in weapon space, and how far it
## opens during a reload (degrees, muzzle up).
@export var cover_hinge: Vector3 = Vector3.ZERO
@export_range(0.0, 120.0) var cover_open_deg: float = 0.0
## Direction the magazine (node "magazine") leaves the gun during a reload,
## weapon space. Down for a pistol; back and up for a top-mounted magazine.
@export var magazine_travel: Vector3 = Vector3(0.0, -1.0, 0.0)
## Belt (node "belt") shake per shot, metres.
@export_range(0.0, 0.02) var belt_jiggle: float = 0.0
## Cocking handle (node "charging_handle"): how far back it sits while the
## bolt is held open (empty gun) before the slap forward, weapon −X metres.
@export_range(0.0, 0.2) var charging_handle_travel: float = 0.0

@export_group("Feedback")
## Controller rumble per shot: weak motor, strong motor, seconds.
@export var rumble_fire: Vector3 = Vector3(0.25, 0.1, 0.06)
@export var rumble_hit: Vector3 = Vector3(0.0, 0.25, 0.05)
@export var rumble_kill: Vector3 = Vector3(0.4, 0.6, 0.14)
## Real-time seconds of hit-stop, and the time scale during it.
@export_range(0.0, 0.3) var hitstop_headshot: float = 0.055
@export_range(0.0, 0.3) var hitstop_kill: float = 0.04
@export_range(0.0, 1.0) var hitstop_time_scale: float = 0.06


## Kinetic energy at the muzzle, J (`power`: capacitor charge fraction for railguns).
func muzzle_energy(power: float = 1.0) -> float:
	return 0.5 * bullet_mass_g * 0.001 * muzzle_velocity * muzzle_velocity * power


## True for guns that load one round at a time (a revolver cylinder).
func loads_singly() -> bool:
	return round_load_time > 0.0


## True for guns with a capacitor bank (railguns).
func is_rail() -> bool:
	return charge_time > 0.0


## 0..1 how full the capacitor is `since_shot` seconds after the last shot.
func charge_fraction(since_shot: float) -> float:
	if charge_time <= 0.0:
		return 1.0
	return clampf((since_shot - fire_interval) / maxf(charge_time - fire_interval, 0.001), 0.0, 1.0)


## Energy fraction of a shot fired `since_shot` seconds after the last one.
func charge_power(since_shot: float) -> float:
	return lerpf(min_charge_power, 1.0, charge_fraction(since_shot)) if is_rail() else 1.0


## Full-width spread cone in degrees for the current state.
## `stability` (body stat) divides the movement and air penalties.
func spread_deg(aim: float, move_fraction: float, airborne: bool, bloom: float, hip_walk: float = 0.0, stability: float = 1.0, air_scale: float = 1.0) -> float:
	var st: float = maxf(stability, 0.1)
	var extra: float = move_spread_deg * clampf(move_fraction, 0.0, 1.0) / st + bloom + hip_walk
	if airborne:
		extra += air_spread_deg * air_scale / st
	var mech: float = mechanical_moa / 60.0
	var hip: float = maxf(hip_spread_deg + extra, mech)
	# Aimed: the gun's own precision plus a fraction of the movement/bloom penalty.
	var aimed: float = mech + extra * ads_spread_scale
	return lerpf(hip, aimed, clampf(aim, 0.0, 1.0))


## Energy (J) needed to cross `thickness_m` of `surface` at `speed` m/s
## (speed only matters for water-like materials, see SurfaceMaterial).
func penetration_cost(surface: SurfaceMaterial, thickness_m: float, speed: float = 0.0) -> float:
	return thickness_m * 100.0 * surface.resistance_j_per_cm * surface.speed_factor(speed) / penetration_scale


func damage_for(deposited_j: float) -> float:
	return maxf(min_damage, deposited_j * damage_per_joule)
