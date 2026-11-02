extends GutTest
## The MG42 as a machine: open bolt (no +1), belt reloads, exact 1,200 rpm.

const DT: float = 1.0 / 60.0
var data: WeaponData
var gun: GunMechanism


func before_each() -> void:
	data = (load("res://data/weapons/mg42.tres") as WeaponData).duplicate() as WeaponData
	data.infinite_reserve = false
	data.reserve_ammo = 400
	gun = GunMechanism.new(data)
	for i: int in int(data.draw_time / DT) + 2:
		gun.update(DT, false, false, false, false)


func _hold(seconds: float) -> int:
	var shots: int = 0
	var t: float = 0.0
	var first: bool = true
	while t < seconds - 0.0001:
		for ev: StringName in gun.update(DT, first, true, false, false):
			if ev == GunMechanism.EV_FIRE:
				shots += 1
		first = false
		t += DT
	return shots


func test_data_is_a_1200_rpm_308_belt_gun() -> void:
	assert_almost_eq(60.0 / data.fire_interval, 1200.0, 0.5, "1,200 rounds per minute")
	assert_true(data.automatic)
	assert_false(data.closed_bolt, "open bolt")
	assert_between(data.muzzle_velocity, 750.0, 860.0, "7.62x51 / .308 velocity")
	assert_between(data.bullet_mass_g, 9.0, 11.7, ".308 bullet (139-180 gr)")
	var pistol: WeaponData = load("res://data/weapons/pistol_57.tres") as WeaponData
	assert_gt(data.muzzle_energy(), pistol.muzzle_energy() * 5.0, "several times the pistol's energy")


func test_belt_starts_full_without_plus_one() -> void:
	assert_eq(gun.loaded(), 150)
	assert_eq(gun.state, GunMechanism.State.READY)
	assert_false(gun.can_reload(), "a full belt can't be reloaded")


func test_holding_the_trigger_fires_exactly_20_rounds_a_second() -> void:
	var shots: int = _hold(1.0)
	assert_between(shots, 20, 21, "1,200 rpm at 60 Hz physics (fired %d)" % shots)
	assert_eq(gun.loaded(), 150 - shots)
	shots = _hold(3.0)
	assert_between(shots, 59, 61, "no drift over a long burst (fired %d in 3 s)" % shots)


func test_reload_is_same_length_full_or_empty_and_never_plus_one() -> void:
	_hold(1.0)
	assert_true(gun.can_reload())
	gun.update(DT, false, false, true, false)
	assert_eq(gun.state, GunMechanism.State.RELOADING)
	assert_almost_eq(gun.reload_duration(), data.reload_tactical_time, 0.001)
	for i: int in int(data.reload_tactical_time / DT) + 3:
		gun.update(DT, false, false, false, false)
	assert_eq(gun.loaded(), 150, "fresh belt, no +1")
	# Run the belt dry with the trigger held: the gun clicks and starts the reload itself,
	# and the empty reload takes the same time.
	var events: Array[StringName] = []
	var t: float = 0.0
	while gun.state != GunMechanism.State.RELOADING and t < 10.0:
		events = gun.update(DT, false, true, false, false)
		t += DT
	assert_has(events, GunMechanism.EV_DRY_FIRE)
	assert_eq(gun.state, GunMechanism.State.RELOADING, "dry trigger starts the reload")
	assert_almost_eq(gun.reload_duration(), data.reload_tactical_time, 0.001)
	for i: int in int(data.reload_tactical_time / DT) + 3:
		events = gun.update(DT, false, false, false, false)
		assert_does_not_have(events, GunMechanism.EV_SLIDE_RELEASE)
	assert_eq(gun.loaded(), 150)


func test_reserve_is_spent_by_the_belt() -> void:
	_hold(2.0)  # ~40 rounds
	var left: int = gun.loaded()
	gun.update(DT, false, false, true, false)
	for i: int in int(data.reload_tactical_time / DT) + 3:
		gun.update(DT, false, false, false, false)
	# The old belt goes back into reserve; a full one comes out.
	assert_eq(gun.loaded(), 150)
	assert_eq(gun.reserve, 400 + left - 150)


func test_holster_cancels_a_reload_without_losing_ammo() -> void:
	_hold(1.0)
	var left: int = gun.loaded()
	gun.update(DT, false, false, true, false)
	var events: Array[StringName] = gun.holster()
	assert_has(events, GunMechanism.EV_RELOAD_CANCEL)
	assert_eq(gun.state, GunMechanism.State.READY)
	assert_eq(gun.loaded(), left)
	gun.draw()
	assert_eq(gun.state, GunMechanism.State.DRAWING)
