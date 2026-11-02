class_name WeaponData
extends Resource
## Everything that defines how a gun shoots, handles and feels
## (docs/design.md §5.2–5.4, docs/m1-gunplay-plan.md). One .tres per weapon
## in data/weapons/. The on-device tuning menu edits these live.
##
## Weapon space follows the glTF models: +X muzzle, +Y up, +Z the gun's right
## side, origin on the bore axis above the grip.

@export var display_name: String = "Five-seveN SR"
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

@export_group("Fire")
## Fastest the mechanism cycles (seconds between shots). Semi-auto.
@export_range(0.03, 1.0) var fire_interval: float = 0.1
@export var automatic: bool = false
## A trigger pull this early before the gun is ready still fires when it is.
@export_range(0.0, 0.3) var fire_buffer: float = 0.12
## Delay between leaving a sprint and the first shot.
@export_range(0.0, 0.5) var sprint_to_fire: float = 0.13
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

@export_group("Damage")
## Damage per joule the round leaves inside a body.
@export_range(0.0, 1.0) var damage_per_joule: float = 0.14
## Every hit deals at least this much (temporary cavity, shock).
@export_range(0.0, 500.0) var min_damage: float = 10.0
## Multiplies real bullet momentum for physics pushes (props, plates, ragdolls).
@export_range(0.0, 200.0) var impulse_scale: float = 30.0

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
## Walk bob amplitude (metres) and steps per second at walking speed.
@export_range(0.0, 0.05) var bob_amount: float = 0.008
@export_range(0.5, 4.0) var bob_rate: float = 1.9
## Dip on landing, metres per (m/s) of fall speed.
@export_range(0.0, 0.02) var land_dip: float = 0.006
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
func spread_deg(aim: float, move_fraction: float, airborne: bool, bloom: float, hip_walk: float = 0.0) -> float:
	var extra: float = move_spread_deg * clampf(move_fraction, 0.0, 1.0) + bloom + hip_walk
	if airborne:
		extra += air_spread_deg
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
