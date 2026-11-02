class_name AmmoData
extends Resource
## One shell type for a gun that takes several (the Saiga-12K: 00 buck,
## slugs, Dragon's Breath). One .tres per load in data/weapons/ammo/.
##
## A load replaces the gun's ballistic, shot and flash values; `apply_to()`
## turns the gun's WeaponData into the WeaponData a round of this load is
## fired with (PlayerWeapon caches one per load). Handling (springs, ADS,
## reloads, carry) stays the gun's. Recoil is the gun's times `recoil_scale`.

@export var display_name: String = "00 Buck"
## HUD label.
@export var short_name: String = "BUCK"
## HUD text, the tape round the magazine and the shell hull.
@export var color: Color = Color(0.78, 0.1, 0.07)

@export_group("Shot")
## Projectiles per shell and the pattern they spread into (full width, degrees).
@export_range(1, 32) var pellets: int = 9
@export_range(0.0, 30.0) var pattern_deg: float = 3.2
@export_range(0.05, 60.0) var pellet_mass_g: float = 3.5
@export_range(50.0, 1500.0) var muzzle_velocity: float = 400.0
## Air drag per metre (see WeaponData.drag_per_m). Round lead balls lose speed fast.
@export_range(0.0, 0.2) var drag_per_m: float = 0.0045
@export_range(5.0, 3000.0) var max_range: float = 160.0
@export_range(0, 12) var max_penetrations: int = 3
@export_range(0.1, 5.0) var penetration_scale: float = 0.55
@export_range(0, 4) var max_ricochets: int = 1
@export_range(0.0, 1.0) var damage_per_joule: float = 0.14
@export_range(0.0, 200.0) var min_damage: float = 10.0
@export_range(0.0, 200.0) var impulse_scale: float = 10.0
## Precision of the pattern's centre when aimed, MOA.
@export_range(0.0, 60.0) var mechanical_moa: float = 8.0

@export_group("Incendiary")
## Every pellet is a burning ember: drawn as a glowing streak, sparks where it lands.
@export var embers: bool = false
## Burn each ember leaves on whatever it hits: damage per second, seconds.
@export_range(0.0, 200.0) var burn_dps: float = 0.0
@export_range(0.0, 10.0) var burn_time: float = 0.0

@export_group("Feel")
@export_range(0.0, 3.0) var recoil_scale: float = 1.0
@export_range(0.0, 6.0) var flash_scale: float = 1.4
@export_range(0.0, 20.0) var flash_light_energy: float = 3.5
@export var flash_color: Color = Color(1.0, 0.72, 0.42)
## Seconds the muzzle light lingers (Dragon's Breath lights the room up).
@export_range(0.02, 1.0) var flash_light_time: float = 0.06
@export_range(0, 10) var smoke_per_shot: int = 3
## Shot sound bank prefix ("saiga_db_" plays saiga_db_shot). Empty = the gun's.
@export var sound_prefix: String = ""
@export_range(-30.0, 6.0) var shot_volume_db: float = 0.0
## Mount the optic while this load is in the gun (slugs get the PSO-pattern 1x).
@export var use_optic: bool = false


## The WeaponData a round of this load is fired with: a copy of `gun` with the
## load's values in place of the gun's.
func apply_to(gun: WeaponData) -> WeaponData:
	var r: WeaponData = gun.duplicate() as WeaponData
	r.pellets = pellets
	r.pattern_deg = pattern_deg
	r.bullet_mass_g = pellet_mass_g
	r.muzzle_velocity = muzzle_velocity
	r.drag_per_m = drag_per_m
	r.max_range = max_range
	r.max_penetrations = max_penetrations
	r.penetration_scale = penetration_scale
	r.max_ricochets = max_ricochets
	r.damage_per_joule = damage_per_joule
	r.min_damage = min_damage
	r.impulse_scale = impulse_scale
	r.mechanical_moa = mechanical_moa
	r.embers = embers
	r.burn_dps = burn_dps
	r.burn_time = burn_time
	r.kick_pitch_deg = gun.kick_pitch_deg * recoil_scale
	r.kick_yaw_deg = gun.kick_yaw_deg * recoil_scale
	r.vm_kick_back = gun.vm_kick_back * recoil_scale
	r.vm_kick_rise_deg = gun.vm_kick_rise_deg * recoil_scale
	r.vm_kick_roll_deg = gun.vm_kick_roll_deg * recoil_scale
	r.flash_scale = flash_scale
	r.flash_light_energy = flash_light_energy
	r.flash_color = flash_color
	r.flash_light_time = flash_light_time
	r.smoke_per_shot = smoke_per_shot
	if not sound_prefix.is_empty():
		r.sound_prefix = sound_prefix
	r.shot_volume_db = shot_volume_db
	return r


## Total muzzle energy of one shell, joules.
func shell_energy() -> float:
	return 0.5 * pellet_mass_g * 0.001 * muzzle_velocity * muzzle_velocity * pellets


## Drop below the line of fire at `distance` m (positive = below), for a
## round fired level from the eye: the holdover the optic's chevrons show.
## Same drag and gravity model as Ballistics, stepped at 240 Hz.
func drop_at(distance: float, gravity: float = 9.8) -> float:
	var x: float = 0.0
	var y: float = 0.0
	var vx: float = muzzle_velocity
	var vy: float = 0.0
	var dt: float = 1.0 / 240.0
	for i: int in 4000:
		if x >= distance:
			break
		var speed: float = sqrt(vx * vx + vy * vy)
		var new_speed: float = speed / (1.0 + drag_per_m * speed * dt)
		var k: float = new_speed / maxf(speed, 0.001)
		vx *= k
		vy = vy * k - gravity * dt
		x += vx * dt
		y += vy * dt
	return -y
