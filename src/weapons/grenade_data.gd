class_name GrenadeData
extends Resource
## A 40 mm low-velocity grenade (docs/design.md §4.8): how it flies, when its
## fuze arms and fires, and what the burst does. Guns that launch grenades
## (WeaponData.grenade) fire these instead of Ballistics rounds. The burst is
## a blast (Explosion.detonate) plus fragments that are real Ballistics
## rounds (Explosion.fragments), so cover stops them and they wound whatever
## zone they reach.

@export var display_name: String = "40 mm HEDP"

@export_group("Flight")
## Projectile mass (kg) and muzzle velocity (m/s): an M433-class round.
@export_range(0.05, 1.0) var mass_kg: float = 0.23
@export_range(20.0, 300.0) var muzzle_velocity: float = 76.0
## Air drag: dv/dt = -k v² (k per metre), the same law as Ballistics rounds.
## 0.001 gives a maximum range of about 410 m at 42°, like the real round.
@export_range(0.0, 0.01) var drag_per_m: float = 0.001
@export_range(0.0, 2.0) var gravity_scale: float = 1.0
## Spin about the flight axis, turns per second (rifling; only for the look).
@export_range(0.0, 100.0) var spin_hz: float = 60.0
## Seconds before a round still in the air is dropped (it left the map).
@export_range(1.0, 30.0) var max_flight_time: float = 12.0

@export_group("Fuze")
## Metres of flight before the fuze arms. Inside it the round is a 230 g
## blunt projectile: it hits like a thrown brick and bounces off as a dud.
## (The real M433 arms at 14-27 m; shortened for the maps' fighting ranges.)
@export_range(0.0, 40.0) var arming_distance: float = 9.0
## A dud's hit on a body: damage per joule it carries, and the shove.
@export_range(0.0, 1.0) var blunt_damage_per_j: float = 0.09
@export_range(0.0, 1.0) var bounce_restitution: float = 0.32
@export_range(0.0, 1.0) var bounce_friction: float = 0.55
## Seconds a dud lies where it stopped before it's cleared away.
@export_range(0.0, 60.0) var dud_lifetime: float = 9.0

@export_group("Airburst (fire control)")
## Aimed, the sight's laser rangefinder lases the point under the dot and the
## fuze setter at the muzzle programs the round to burst this far past it.
@export_range(0.0, 5.0) var airburst_offset: float = 1.5
## How high above a lased surface (not a body) the round is sent, so it clears
## the top of the cover it was aimed at.
@export_range(0.0, 1.0) var airburst_clearance: float = 0.35
## Farthest the rangefinder reads, m.
@export_range(10.0, 400.0) var fcs_max_range: float = 200.0
## Seconds aimed before the fire control has a solution.
@export_range(0.0, 1.0) var fcs_lock_time: float = 0.12

@export_group("Blast")
## Overpressure: radius (m) and damage at the centre (falls off to the edge).
@export_range(0.5, 10.0) var blast_radius: float = 3.4
@export_range(0.0, 1000.0) var blast_damage: float = 260.0
## Share of the blast the operative takes inside the radius (the suit and frame).
@export_range(0.0, 1.0) var self_blast_scale: float = 0.45

@export_group("Fragments")
## Effective fragments from the body: each body near the burst gets the
## share that would reach it (projected area ÷ the sphere at its distance),
## fired as real rounds at random zones, so cover and other bodies stop them.
@export_range(0, 3000) var fragment_count: int = 620
## Projected area of a standing man, m².
@export_range(0.1, 2.0) var body_area_m2: float = 0.7
@export_range(0.05, 5.0) var fragment_mass_g: float = 0.4
@export_range(100.0, 3000.0) var fragment_velocity: float = 1500.0
## Fragments are draggy (irregular, light): v(x) = v0·e^(-k x).
@export_range(0.0, 0.2) var fragment_drag_per_m: float = 0.04
@export_range(1.0, 60.0) var fragment_range: float = 22.0
## Most fragments one body takes from one burst (caps the work).
@export_range(1, 20) var fragment_max_per_body: int = 8
## Fragments fired at nothing in particular, for the pockmarks and sparks on
## the walls and floor around the burst.
@export_range(0, 64) var fragment_scatter: int = 14
@export_range(0.0, 1.0) var fragment_damage_per_joule: float = 0.13

@export_group("Look")
## Fireball radius (m); the smoke grows past it.
@export_range(0.2, 4.0) var fireball_radius: float = 0.75
## Camera shake at the centre (fades out by `shake_range`) and the distance
## inside which the operative's hearing is stunned for a moment.
@export_range(0.0, 3.0) var shake_strength: float = 1.0
@export_range(1.0, 60.0) var shake_range: float = 26.0
@export_range(0.0, 20.0) var concussion_range: float = 7.0


## Kinetic energy at the muzzle, J.
func muzzle_energy() -> float:
	return 0.5 * mass_kg * muzzle_velocity * muzzle_velocity


## Acceleration from gravity and drag at velocity `v`.
func accel(v: Vector3, gravity: float) -> Vector3:
	return Vector3(0.0, -gravity * gravity_scale, 0.0) - v * (drag_per_m * v.length())


## One step of flight: drag integrated exactly for the speed (as Ballistics),
## then gravity. Returns the new velocity.
func step_velocity(v: Vector3, dt: float, gravity: float) -> Vector3:
	var s: float = v.length()
	var ns: float = s / (1.0 + drag_per_m * s * dt)
	var out: Vector3 = v * (ns / maxf(s, 0.0001))
	out.y -= gravity * gravity_scale * dt
	return out


## Where a round launched from `origin` at `velocity` is after `t` seconds
## (stepped like the real flight, at `dt`).
func position_at(origin: Vector3, velocity: Vector3, t: float, gravity: float, dt: float = 1.0 / 120.0) -> Vector3:
	var p: Vector3 = origin
	var v: Vector3 = velocity
	var left: float = t
	while left > 0.0:
		var h: float = minf(dt, left)
		v = step_velocity(v, h, gravity)
		p += v * h
		left -= h
	return p


## Launch direction from `origin` that brings the round through `target`
## (the low arc). Falls back to the straight line if it's out of reach.
## Solved by bisection on the elevation above the line to the target.
func solve_launch(origin: Vector3, target: Vector3, gravity: float) -> Vector3:
	var to: Vector3 = target - origin
	var flat: Vector3 = Vector3(to.x, 0.0, to.z)
	var dist: float = flat.length()
	if dist < 0.01:
		return to.normalized() if to.length() > 0.001 else Vector3.FORWARD
	var heading: Vector3 = flat / dist
	var los: float = atan2(to.y, dist)
	var lo: float = los
	var hi: float = minf(los + deg_to_rad(40.0), deg_to_rad(44.0))
	if hi <= lo:
		return to.normalized()
	if _height_error(hi, heading, dist, to.y, gravity) < 0.0:
		return to.normalized()  # out of reach: fire along the line
	for i: int in 22:
		var mid: float = (lo + hi) * 0.5
		if _height_error(mid, heading, dist, to.y, gravity) < 0.0:
			lo = mid
		else:
			hi = mid
	var e: float = (lo + hi) * 0.5
	return (heading * cos(e) + Vector3.UP * sin(e)).normalized()


## How far above (+) or below (-) the target height a round launched at
## elevation `elev` along `heading` is when it has covered `dist` m across.
func _height_error(elev: float, heading: Vector3, dist: float, rise: float, gravity: float) -> float:
	var v: Vector3 = (heading * cos(elev) + Vector3.UP * sin(elev)) * muzzle_velocity
	var p: Vector3 = Vector3.ZERO
	var dt: float = 1.0 / 120.0
	for i: int in 2400:
		var nv: Vector3 = step_velocity(v, dt, gravity)
		var np: Vector3 = p + nv * dt
		var a: float = p.dot(heading)
		var b: float = np.dot(heading)
		if b >= dist:
			var f: float = (dist - a) / maxf(b - a, 0.0001)
			return lerpf(p.y, np.y, f) - rise
		if nv.dot(heading) <= 0.0:
			break
		p = np
		v = nv
	return -1000.0


## The fragments as a Ballistics round.
func fragment_weapon() -> WeaponData:
	var w: WeaponData = WeaponData.new()
	w.display_name = display_name
	w.caliber = "fragment"
	w.muzzle_velocity = fragment_velocity
	w.bullet_mass_g = fragment_mass_g
	w.drag_per_m = fragment_drag_per_m
	w.gravity_scale = 0.0
	w.max_range = fragment_range
	w.max_penetrations = 2
	w.penetration_scale = 0.45
	w.max_ricochets = 1
	w.damage_per_joule = fragment_damage_per_joule
	w.min_damage = 6.0
	w.impulse_scale = 16.0
	w.impact_fx_scale = 0.55
	w.ejects_shells = false
	return w


## Expected fragments reaching a body of area `area_m2` at `distance` m.
func expected_fragments(distance: float, area_m2: float) -> float:
	var d: float = maxf(distance, 0.5)
	return float(fragment_count) * area_m2 / (4.0 * PI * d * d)


## A fragment's energy (J) after `distance` m of flight.
func fragment_energy_at(distance: float) -> float:
	var v: float = fragment_velocity * exp(-fragment_drag_per_m * distance)
	return 0.5 * fragment_mass_g * 0.001 * v * v
