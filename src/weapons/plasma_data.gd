class_name PlasmaData
extends Resource
## The charge and the bolt of a plasma gun (the SL-9 Slagger, docs/design.md
## §4.9; owner, 2026-11-18). Hold the trigger to charge; a red-orange ball of
## plasma builds at the emitter, held by a magnetic field; let go and it
## leaves as a glowing mass. Every value scales with the charge fraction
## (0..1, `full_charge_time` seconds of holding): lerp(min, full, charge).
## data/weapons/ammo/plasma_bolt.tres.

@export_group("Charge")
## Seconds of holding to a full charge.
@export_range(0.3, 6.0) var full_charge_time: float = 2.75
## Let go below this fraction and the field collapses with a pop: no shot.
@export_range(0.0, 0.5) var min_charge: float = 0.12
## Held at full this long, the field fails: the ball vents in your hands
## (no shot) and the gun needs `overload_lockout` to recover.
@export_range(0.5, 10.0) var overload_time: float = 3.0
@export_range(0.2, 4.0) var overload_lockout: float = 1.4
## Charge curve exponent: >1 = slow start, fast finish (it gathers, then surges).
@export_range(0.5, 3.0) var charge_curve: float = 1.35

@export_group("Bolt")
@export_range(5.0, 200.0) var speed_min: float = 34.0
@export_range(5.0, 200.0) var speed_full: float = 58.0
## Ball radius (what it hits with) and how wide it grazes past that (sets alight).
@export_range(0.005, 0.3) var radius_min: float = 0.025
@export_range(0.005, 0.3) var radius_full: float = 0.075
@export_range(0.0, 1.5) var graze_min: float = 0.18
@export_range(0.0, 1.5) var graze_full: float = 0.55
## Downward pull, m/s² (hot plasma barely drops).
@export_range(0.0, 10.0) var gravity: float = 0.6
@export_range(0.2, 6.0) var lifetime: float = 2.6

@export_group("Damage")
@export_range(0.0, 2000.0) var damage_min: float = 40.0
@export_range(0.0, 2000.0) var damage_full: float = 520.0
## Fire left on what it touches: seconds and damage per second.
@export_range(0.0, 20.0) var burn_time: float = 7.0
@export_range(0.0, 100.0) var burn_dps_min: float = 9.0
@export_range(0.0, 100.0) var burn_dps_full: float = 24.0
## A graze: this fraction of the burn, and seconds of agony (running, screaming, flailing).
@export_range(0.0, 1.0) var graze_burn: float = 0.75
@export_range(0.0, 20.0) var agony_time: float = 6.0
## From this charge up a hit to the trunk burns a hole clean through and the
## bolt carries on with `through_keep` of its charge; a limb comes off
## (cauterised, burning); a head goes. Above `pulp_charge` the limb is
## reduced to burning chunks instead of coming off whole.
@export_range(0.0, 1.0) var burn_through_charge: float = 0.5
@export_range(0.0, 1.0) var through_keep: float = 0.6
@export_range(0.0, 1.0) var sever_charge: float = 0.35
@export_range(0.0, 1.0) var pulp_charge: float = 0.88
@export_range(0.0, 1.0) var head_charge: float = 0.3
@export_range(0.01, 0.3) var hole_min: float = 0.045
@export_range(0.01, 0.3) var hole_full: float = 0.1
## Splash where it bursts on a surface: radius that sets men alight, and its damage.
@export_range(0.0, 5.0) var splash_full: float = 1.7
@export_range(0.0, 500.0) var splash_damage_full: float = 60.0
## Momentum it carries into a body (m/s of shove at full charge).
@export_range(0.0, 20.0) var push_full: float = 5.0

@export_group("Look")
@export var core_color: Color = Color(1.0, 0.82, 0.45)
@export var hot_color: Color = Color(1.0, 0.36, 0.06)
@export var field_color: Color = Color(1.0, 0.55, 0.2)
@export_range(0.0, 16.0) var light_energy: float = 5.0
@export_range(0.5, 20.0) var light_range: float = 7.0

@export_group("Feedback")
## Viewmodel and camera recoil × this at full charge (min at the smallest shot).
@export_range(0.0, 4.0) var recoil_min: float = 0.3
@export_range(0.0, 4.0) var recoil_full: float = 1.0
## Rumble while charging: weak and strong motor at full.
@export var rumble_charge: Vector2 = Vector2(0.55, 0.45)
## The gun trembles harder as it fills (viewmodel jitter, metres / degrees at full).
@export_range(0.0, 0.01) var tremble_pos: float = 0.0018
@export_range(0.0, 5.0) var tremble_rot: float = 1.1


## 0..1 charge after `held` seconds.
func charge_fraction(held: float) -> float:
	return pow(clampf(held / maxf(full_charge_time, 0.05), 0.0, 1.0), charge_curve)


func at(lo: float, hi: float, charge: float) -> float:
	return lerpf(lo, hi, clampf(charge, 0.0, 1.0))


func speed(charge: float) -> float:
	return at(speed_min, speed_full, charge)


func radius(charge: float) -> float:
	return at(radius_min, radius_full, charge)


func graze(charge: float) -> float:
	return at(graze_min, graze_full, charge)


func damage(charge: float) -> float:
	return at(damage_min, damage_full, charge * charge)


func burn_dps(charge: float) -> float:
	return at(burn_dps_min, burn_dps_full, charge)


func hole_radius(charge: float) -> float:
	return at(hole_min, hole_full, charge)


func recoil(charge: float) -> float:
	return at(recoil_min, recoil_full, charge)
