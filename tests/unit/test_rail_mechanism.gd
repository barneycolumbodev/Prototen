extends GutTest
## RC-6 rail carbine as a machine (data/weapons/rail_carbine.tres): capacitor
## charge sets each shot's power, rails heat up and force a vent, heat bleeds
## off at rest, and the hypervelocity numbers are what the brief asks for.

const RAIL: WeaponData = preload("res://data/weapons/rail_carbine.tres")
const PISTOL: WeaponData = preload("res://data/weapons/pistol_57.tres")
const MG42: WeaponData = preload("res://data/weapons/mg42.tres")
const FLESH: SurfaceMaterial = preload("res://data/surfaces/flesh.tres")
const DT: float = 1.0 / 60.0


func _ready_gun() -> GunMechanism:
	var m: GunMechanism = GunMechanism.new(RAIL)
	_run(m, RAIL.draw_time + 0.05)
	assert_eq(m.state, GunMechanism.State.READY)
	return m


func _run(m: GunMechanism, seconds: float) -> Array[StringName]:
	var all: Array[StringName] = []
	var t: float = 0.0
	while t < seconds - 0.0001:
		all.append_array(m.update(DT, false, false, false, false))
		t += DT
	return all


func _shoot(m: GunMechanism) -> Array[StringName]:
	return m.update(DT, true, true, false, false)


func test_it_is_a_railgun_and_the_others_are_not() -> void:
	assert_true(RAIL.is_rail())
	assert_false(PISTOL.is_rail())
	assert_false(MG42.is_rail())
	assert_eq(PISTOL.charge_power(0.0), 1.0, "conventional guns always fire at full power")


func test_hypervelocity_numbers() -> void:
	assert_almost_eq(RAIL.muzzle_velocity, 2600.0, 1.0, "Mach 7.6")
	var e: float = RAIL.muzzle_energy()
	assert_between(e, 20000.0, 30000.0, "about 24 kJ (%.0f J)" % e)
	assert_gt(e, MG42.muzzle_energy() * 6.0, "many times a .308 MG round")
	assert_gt(e, PISTOL.muzzle_energy() * 40.0, "dwarfs the pistol")
	assert_false(RAIL.ejects_shells, "no case to eject")
	assert_gt(RAIL.beam_trail_time, 0.0, "every shot leaves a trail")


func test_first_shot_is_full_power() -> void:
	var m: GunMechanism = _ready_gun()
	assert_eq(m.charge(), 1.0)
	assert_true(_shoot(m).has(GunMechanism.EV_FIRE))
	assert_almost_eq(m.last_power, 1.0, 0.001)
	assert_eq(m.charge(), 0.0, "capacitor drained by the shot")


func test_firing_early_gives_less_power_and_waiting_gives_full() -> void:
	var m: GunMechanism = _ready_gun()
	_shoot(m)
	_run(m, RAIL.fire_interval + 0.01)
	_shoot(m)
	assert_almost_eq(m.last_power, RAIL.min_charge_power, 0.05, "fired at the earliest moment")
	var events: Array[StringName] = _run(m, RAIL.charge_time + 0.05)
	assert_true(events.has(GunMechanism.EV_CHARGED), "ready tone once full")
	assert_eq(m.charge(), 1.0)
	_shoot(m)
	assert_almost_eq(m.last_power, 1.0, 0.001)


func test_charge_power_curve() -> void:
	assert_almost_eq(RAIL.charge_power(RAIL.fire_interval), RAIL.min_charge_power, 0.001)
	assert_almost_eq(RAIL.charge_power(RAIL.charge_time), 1.0, 0.001)
	var mid: float = RAIL.charge_power((RAIL.fire_interval + RAIL.charge_time) * 0.5)
	assert_between(mid, RAIL.min_charge_power, 1.0)


func test_spamming_overheats_and_forces_a_vent() -> void:
	var m: GunMechanism = _ready_gun()
	var shots: int = 0
	var overheated: bool = false
	for i: int in 60:
		var ev: Array[StringName] = _shoot(m)
		if ev.has(GunMechanism.EV_FIRE):
			shots += 1
		if ev.has(GunMechanism.EV_OVERHEAT):
			overheated = true
			break
		_run(m, RAIL.fire_interval)
	assert_true(overheated, "rapid fire overheats the rails")
	assert_between(shots, 8, 30, "after a sustained burst (%d shots)" % shots)
	assert_true(m.venting)
	# While venting the trigger only clicks.
	_run(m, RAIL.fire_interval + 0.02)
	var ev2: Array[StringName] = _shoot(m)
	ev2.append_array(_run(m, 0.1))
	assert_false(ev2.has(GunMechanism.EV_FIRE), "can't fire while venting")
	assert_eq(ev2.count(GunMechanism.EV_DRY_FIRE), 1, "the trigger clicks once")
	var events: Array[StringName] = _run(m, RAIL.vent_time + 0.05)
	assert_true(events.has(GunMechanism.EV_VENT_DONE))
	assert_false(m.venting)
	assert_eq(m.heat, 0.0, "vented rails are cold")
	assert_true(_shoot(m).has(GunMechanism.EV_FIRE), "fires again after the vent")


func test_paced_full_power_fire_does_not_overheat() -> void:
	var m: GunMechanism = _ready_gun()
	for i: int in 30:
		var ev: Array[StringName] = _shoot(m)
		assert_false(ev.has(GunMechanism.EV_OVERHEAT), "shot %d" % i)
		_run(m, RAIL.charge_time)
	assert_lt(m.heat, 0.6)


func test_heat_bleeds_off_at_rest_and_while_holstered() -> void:
	var m: GunMechanism = _ready_gun()
	for i: int in 4:
		_shoot(m)
		_run(m, RAIL.fire_interval)
	var hot: float = m.heat
	assert_gt(hot, 0.2)
	for i: int in 60:
		m.idle(DT)
	assert_lt(m.heat, hot, "cools while holstered")
	_run(m, 3.0)
	assert_eq(m.heat, 0.0)


func test_reload_works_while_venting() -> void:
	var m: GunMechanism = _ready_gun()
	m.heat = 0.99
	_shoot(m)
	assert_true(m.venting)
	m.update(DT, false, false, true, false)
	_run(m, RAIL.fire_interval + 0.05)
	assert_true(m.venting)
	assert_eq(m.state, GunMechanism.State.RELOADING, "hands swap the magazine while the rails cool")


func test_flesh_drag_grows_at_hypervelocity_only() -> void:
	assert_eq(FLESH.speed_factor(650.0), 1.0, "pistol unchanged")
	assert_eq(FLESH.speed_factor(800.0), 1.0, "MG42 unchanged")
	var k: float = FLESH.speed_factor(2600.0)
	assert_between(k, 6.0, 12.0, "v² drag at 2,600 m/s (×%.1f)" % k)
	# A torso (22 cm) takes a big bite out of the slug but it still exits.
	var cost: float = RAIL.penetration_cost(FLESH, 0.22, 2600.0)
	assert_between(cost, 800.0, RAIL.muzzle_energy() * 0.5, "%.0f J left in a torso" % cost)
	assert_gt(RAIL.damage_for(cost), 150.0, "any torso hit is lethal")
