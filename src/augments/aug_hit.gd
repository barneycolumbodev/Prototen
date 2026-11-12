class_name AugHit
extends RefCounted
## Hits dealt by active parts that aren't rounds (the whip's cut, the arc,
## an explosion). A BallisticHit built by hand and given to the hitbox, so
## everything downstream (damage zones, wounds, gore, severing, the kill
## confirm, morale) works exactly as it does for a bullet.

static var _next_id: int = 1 << 24


## Hits `part` at `point` along `dir`. `energy_j` drives wound size, blood
## and the severing thresholds (Enemy.SEVER_*); `through`: it leaves the
## body (an exit wound, blood behind).
static func strike(part: HitboxPart, weapon: WeaponData, shooter: Node, point: Vector3, dir: Vector3, amount: float,
		impulse: float, energy_j: float, type: DamageInfo.Type = DamageInfo.Type.BLADE, through: bool = true) -> BallisticHit:
	_next_id += 1
	var hit: BallisticHit = BallisticHit.new()
	hit.shot_id = _next_id
	hit.volley_id = _next_id
	hit.weapon = weapon
	hit.shooter = shooter
	hit.collider = part
	hit.point = point
	hit.direction = dir.normalized()
	hit.normal = -hit.direction
	hit.energy_in = energy_j
	if through:
		hit.result = BallisticHit.Result.PENETRATED
		hit.exit_point = point + hit.direction * 0.14
		hit.exit_normal = hit.direction
		hit.energy_out = energy_j * 0.15
	var d: DamageInfo = DamageInfo.new()
	d.amount = amount
	d.type = type
	d.impulse = impulse
	d.zone = part.get_meta(&"zone", &"")
	d.point = point
	d.normal = hit.normal
	d.source = shooter
	if d.zone == &"head":
		d.flags |= DamageInfo.Flags.HEADSHOT
	hit.damage = d
	part.on_ballistic_hit(hit)
	return hit


## A weapon record for an active part's hits (kill feed, sound lookups).
static func weapon_named(display_name: String) -> WeaponData:
	var w: WeaponData = WeaponData.new()
	w.display_name = display_name
	return w
