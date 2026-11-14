extends GutTest
## The 40 mm grenade's numbers (GrenadeData, docs/design.md §4.8): flight,
## the fire control's launch solution, fragments, and the single-round reload
## of a revolver cylinder (GunMechanism).

var g: GrenadeData = preload("res://data/weapons/ammo/grenade_40mm_hedp.tres")
var m32: WeaponData = preload("res://data/weapons/m32.tres")
const GRAVITY: float = 9.8


## Steps a round launched at `elev_deg` until it comes back down to y = 0.
func _range_at(elev_deg: float) -> float:
	var e: float = deg_to_rad(elev_deg)
	var v: Vector3 = Vector3(cos(e), sin(e), 0.0) * g.muzzle_velocity
	var p: Vector3 = Vector3.ZERO
	var dt: float = 1.0 / 240.0
	for i: int in 20000:
		v = g.step_velocity(v, dt, GRAVITY)
		p += v * dt
		if p.y < 0.0:
			return p.x
	return p.x


func test_it_is_an_m433_class_round() -> void:
	assert_between(g.muzzle_energy(), 600.0, 720.0, "230 g at 76 m/s: %.0f J" % g.muzzle_energy())
	assert_between(g.arming_distance, 5.0, 30.0, "arms after a few metres")


func test_maximum_range_is_about_400_m() -> void:
	var best: float = 0.0
	for a: int in range(30, 50):
		best = maxf(best, _range_at(float(a)))
	assert_between(best, 380.0, 440.0, "max range %.0f m (the real round: about 400 m)" % best)


func test_it_drops_a_lot_over_fighting_ranges() -> void:
	# Fired level from 1.5 m up, it hits the ground about 40 m out: a launcher is aimed, not pointed.
	var p: Vector3 = Vector3(0, 1.5, 0)
	var v: Vector3 = Vector3(g.muzzle_velocity, 0, 0)
	var dt: float = 1.0 / 240.0
	while p.y > 0.0:
		v = g.step_velocity(v, dt, GRAVITY)
		p += v * dt
	assert_between(p.x, 30.0, 45.0, "a level shot lands at %.1f m" % p.x)


func test_the_launch_solution_goes_through_the_target() -> void:
	for target: Vector3 in [Vector3(25, 0.5, 3), Vector3(60, -1.0, -12), Vector3(110, 4.0, 20), Vector3(14, -1.2, 0)]:
		var dir: Vector3 = g.solve_launch(Vector3.ZERO, target, GRAVITY)
		var v: Vector3 = dir * g.muzzle_velocity
		var p: Vector3 = Vector3.ZERO
		var dt: float = 1.0 / 480.0
		var flat: Vector3 = Vector3(target.x, 0, target.z)
		var heading: Vector3 = flat.normalized()
		var closest: float = INF
		for i: int in 20000:
			v = g.step_velocity(v, dt, GRAVITY)
			p += v * dt
			if p.dot(heading) >= flat.length():
				closest = p.distance_to(target)
				break
		assert_lt(closest, 0.15, "passes %.2f m from %s" % [closest, target])
		assert_gt(dir.y, (target - Vector3.ZERO).normalized().y, "aimed above the line to it")


func test_fragments_thin_out_with_distance() -> void:
	var near: float = g.expected_fragments(2.0, g.body_area_m2)
	var mid: float = g.expected_fragments(5.0, g.body_area_m2)
	var far: float = g.expected_fragments(12.0, g.body_area_m2)
	assert_gt(near, 5.0, "a man 2 m away takes several (%.1f)" % near)
	assert_between(mid, 0.8, 2.5, "at 5 m about one or two (%.2f)" % mid)
	assert_lt(far, 0.4, "at 12 m it's luck (%.2f)" % far)
	assert_gt(g.fragment_energy_at(3.0), 250.0, "a fragment at 3 m carries a pistol round's energy")
	assert_lt(g.fragment_energy_at(20.0), g.fragment_energy_at(3.0) * 0.3, "and sheds it fast")


func test_poisson_counts_have_the_right_mean() -> void:
	var r: RandomNumberGenerator = RandomNumberGenerator.new()
	r.seed = 40
	for mean: float in [0.4, 2.5, 6.0]:
		var total: int = 0
		for i: int in 4000:
			total += Explosion.poisson(mean, r)
		assert_almost_eq(float(total) / 4000.0, mean, mean * 0.08 + 0.03, "mean %.1f" % mean)


func test_fragments_aim_at_zones_by_size() -> void:
	var r: RandomNumberGenerator = RandomNumberGenerator.new()
	r.seed = 3
	var count: Dictionary[StringName, int] = {}
	for i: int in 6000:
		var z: StringName = Explosion.pick_zone(r)
		count[z] = count.get(z, 0) + 1
	var chest: int = count.get(&"chest", 0)
	var head: int = count.get(&"head", 0)
	var thigh: int = count.get(&"l_thigh", 0)
	var hand: int = count.get(&"l_hand", 0)
	assert_gt(chest, head * 2, "the chest is a bigger target than the head")
	assert_gt(thigh, hand * 3, "a thigh more than a hand")
	assert_eq(count.size(), EnemyBody.ZONES.size(), "every zone can be hit")


# ------------------------------------------------------------------ the cylinder's reload

func _run(m: GunMechanism, seconds: float, pull: bool = false, reload: bool = false) -> Array[StringName]:
	var all: Array[StringName] = []
	var dt: float = 1.0 / 60.0
	var first: bool = true
	var left: float = seconds
	while left > 0.0:
		all.append_array(m.update(dt, pull and first, false, reload and first, false))
		first = false
		left -= dt
	return all


func _empty_gun() -> GunMechanism:
	var m: GunMechanism = GunMechanism.new(m32)
	_run(m, 1.0)
	for i: int in 6:
		_run(m, m32.fire_interval + 0.05, true)
	return m


func test_six_rounds_then_empty() -> void:
	var m: GunMechanism = GunMechanism.new(m32)
	_run(m, 1.0)
	assert_eq(m.loaded(), 6, "six in the cylinder, none in a chamber outside it")
	var m2: GunMechanism = _empty_gun()
	assert_eq(m2.loaded(), 0)


func test_reload_loads_one_round_at_a_time() -> void:
	var m: GunMechanism = _empty_gun()
	var ev: Array[StringName] = _run(m, 0.05, false, true)
	assert_true(ev.has(GunMechanism.EV_RELOAD_START))
	ev = _run(m, m32.reload_open_time)
	assert_true(ev.has(GunMechanism.EV_MAG_OUT), "opened: the cases fall out")
	assert_gt(m.open_amount(), 0.95, "swung out")
	assert_eq(m.loaded(), 0)
	ev = _run(m, m32.round_load_time + 0.02)
	assert_eq(ev.count(GunMechanism.EV_ROUND_IN), 1, "one round in")
	assert_eq(m.loaded(), 1)
	ev = _run(m, m32.round_load_time * 5.0 + m32.reload_close_time + 0.1)
	assert_eq(ev.count(GunMechanism.EV_ROUND_IN), 5, "the other five")
	assert_true(ev.has(GunMechanism.EV_SLIDE_RELEASE), "closed")
	assert_eq(m.loaded(), 6)
	assert_eq(m.state, GunMechanism.State.READY)
	var full: float = m32.reload_open_time + m32.round_load_time * 6.0 + m32.reload_close_time
	assert_between(full, 2.5, 4.0, "a full reload takes %.1f s" % full)


func test_a_trigger_pull_closes_it_and_fires() -> void:
	var m: GunMechanism = _empty_gun()
	_run(m, 0.05, false, true)
	_run(m, m32.reload_open_time + m32.round_load_time * 2.0 + 0.02)
	assert_eq(m.loaded(), 2, "two in")
	var ev: Array[StringName] = _run(m, m32.reload_close_time + 0.1, true)
	assert_true(ev.has(GunMechanism.EV_SLIDE_RELEASE), "it shut")
	assert_true(ev.has(GunMechanism.EV_FIRE), "and fired once shut")
	assert_eq(m.loaded(), 1)


func test_a_sprint_keeps_what_went_in() -> void:
	var m: GunMechanism = _empty_gun()
	_run(m, 0.05, false, true)
	_run(m, m32.reload_open_time + m32.round_load_time * 3.0 + 0.02)
	var ev: Array[StringName] = m.update(1.0 / 60.0, false, false, false, false, true)
	assert_true(ev.has(GunMechanism.EV_RELOAD_CANCEL))
	assert_eq(m.loaded(), 3, "three rounds stay in")
	assert_eq(m.open_amount(), 0.0, "shut")


func test_the_tuning_menu_reaches_the_launcher_values() -> void:
	var rows: int = 0
	for p: Array in preload("res://src/ui/tuning_menu.gd").WEAPON_PARAMS:
		if p[0] != "Launcher":
			continue
		rows += 1
		var prop: String = p[1]
		assert_true(prop in g, "%s is a GrenadeData value" % prop)
		assert_true(preload("res://src/ui/tuning_menu.gd").shows(p, m32), "shown for the M32")
		assert_eq(preload("res://src/ui/tuning_menu.gd").param_target(p, m32), m32.grenade, "edits its grenade")
	assert_gte(rows, 5)
