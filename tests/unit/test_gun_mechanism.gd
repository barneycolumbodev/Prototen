extends GutTest
## The gun as a machine: chamber + magazine, fire rate, buffered shots, reloads.

const DT: float = 1.0 / 60.0
var data: WeaponData
var gun: GunMechanism


func before_each() -> void:
	data = (load("res://data/weapons/pistol_57.tres") as WeaponData).duplicate() as WeaponData
	data.infinite_reserve = false
	data.reserve_ammo = 45
	gun = GunMechanism.new(data)
	_run(data.draw_time + DT)


## Runs the mechanism for `seconds` with no input; returns all events.
func _run(seconds: float, pull_first: bool = false, held: bool = false) -> Array[StringName]:
	var all: Array[StringName] = []
	var t: float = 0.0
	var first: bool = true
	while t < seconds:
		all.append_array(gun.update(DT, pull_first and first, held, false, false))
		first = false
		t += DT
	return all


func _pull() -> Array[StringName]:
	return gun.update(DT, true, true, false, false)


func test_starts_with_twenty_plus_one() -> void:
	assert_eq(gun.loaded(), 21)
	assert_eq(gun.state, GunMechanism.State.READY)


func test_one_shot_per_pull_and_fire_rate_cap() -> void:
	assert_has(_pull(), GunMechanism.EV_FIRE)
	assert_eq(gun.loaded(), 20)
	# Holding the trigger on a semi-auto doesn't fire again.
	var held: Array[StringName] = []
	for i: int in 30:
		held.append_array(gun.update(DT, false, true, false, false))
	assert_does_not_have(held, GunMechanism.EV_FIRE)


func test_early_pull_is_buffered_not_lost() -> void:
	_pull()
	var events: Array[StringName] = gun.update(DT, true, true, false, false)  # too soon
	assert_does_not_have(events, GunMechanism.EV_FIRE)
	events = _run(data.fire_interval)
	assert_has(events, GunMechanism.EV_FIRE, "buffered shot fires once the gun cycles")
	assert_eq(gun.loaded(), 19)


func test_last_round_locks_slide_and_dry_fire_starts_empty_reload() -> void:
	for i: int in 21:
		_pull()
		_run(data.fire_interval + DT)
	assert_eq(gun.loaded(), 0)
	assert_false(gun.chambered)
	var events: Array[StringName] = _pull()
	assert_has(events, GunMechanism.EV_DRY_FIRE)
	assert_has(events, GunMechanism.EV_RELOAD_START)
	assert_true(gun.empty_reload)
	events = _run(data.reload_empty_time + DT)
	assert_has(events, GunMechanism.EV_SLIDE_RELEASE)
	assert_eq(gun.loaded(), 20, "empty reload: 19 in the mag + 1 chambered")
	assert_eq(gun.reserve, 25)


func test_tactical_reload_keeps_the_chambered_round() -> void:
	for i: int in 5:
		_pull()
		_run(data.fire_interval + DT)
	assert_eq(gun.loaded(), 16)
	var events: Array[StringName] = gun.update(DT, false, false, true, false)
	assert_has(events, GunMechanism.EV_RELOAD_START)
	assert_false(gun.empty_reload)
	_run(data.reload_tactical_time + DT)
	assert_eq(gun.loaded(), 21)
	assert_eq(gun.reserve, 45 - 5, "partial mag went back to reserve")


func test_cancel_before_mag_seats_loses_nothing() -> void:
	_pull()
	_run(data.fire_interval + DT)
	gun.update(DT, false, false, true, false)
	_run(data.reload_tactical_time * data.mag_out_point + 0.05)
	var events: Array[StringName] = _pull()  # shoot to cancel
	assert_has(events, GunMechanism.EV_RELOAD_CANCEL)
	assert_has(events, GunMechanism.EV_FIRE, "the cancelling pull fires")
	assert_eq(gun.loaded(), 19)
	assert_eq(gun.reserve, 45)


func test_sprint_cancel_after_mag_seats_finishes_the_reload() -> void:
	for i: int in 21:
		_pull()
		_run(data.fire_interval + DT)
	_pull()  # dry fire -> empty reload
	_run(data.reload_empty_time * (data.mag_in_point + 0.05))
	var events: Array[StringName] = gun.update(DT, false, false, false, true, true)
	assert_has(events, GunMechanism.EV_RELOAD_DONE)
	assert_true(gun.chambered, "slide released, ready to fire")


func test_blocked_gun_holds_a_buffered_shot() -> void:
	var events: Array[StringName] = gun.update(DT, true, true, false, true)
	assert_does_not_have(events, GunMechanism.EV_FIRE)
	events = gun.update(DT, false, true, false, false)
	assert_has(events, GunMechanism.EV_FIRE, "fires as soon as the sprint ends, inside the buffer")


func test_no_reload_when_full_or_no_reserve() -> void:
	assert_false(gun.can_reload(), "21/21")
	_pull()
	_run(data.fire_interval + DT)
	gun.reserve = 0
	assert_false(gun.can_reload())
