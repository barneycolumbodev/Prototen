extends GutTest
## The Saiga-12K as a machine (GunMechanism with shell types): the chamber and
## the magazine remember their load, a swap seats a magazine of the selected
## load and racks the old shell out, and a cancelled swap changes nothing.

const BUCK: int = 0
const SLUG: int = 1
const DB: int = 2

var data: WeaponData
var gun: GunMechanism
var events: Array[StringName] = []


func before_each() -> void:
	data = (load("res://data/weapons/saiga12k.tres") as WeaponData).duplicate() as WeaponData
	gun = GunMechanism.new(data)
	events.clear()
	_run(data.draw_time + 0.05)


func _step(pull: bool = false, reload: bool = false, dt: float = 1.0 / 60.0) -> void:
	events.append_array(gun.update(dt, pull, pull, reload, false))


func _run(seconds: float) -> void:
	for i: int in ceili(seconds * 60.0):
		_step()


func _fire_once() -> void:
	_step(true)
	_run(data.fire_interval + 0.02)


func test_fresh_gun_holds_ten_plus_one_of_the_first_load() -> void:
	assert_eq(gun.loaded(), 11)
	assert_eq(gun.chamber_ammo, BUCK)
	assert_eq(gun.mag_ammo, BUCK)
	assert_false(gun.needs_swap())


func test_swap_seats_the_new_load_and_racks_the_old_shell_out() -> void:
	_fire_once()
	assert_eq(gun.fired_ammo, BUCK)
	gun.load_ammo = SLUG
	assert_true(gun.needs_swap())
	gun.request_swap()
	_step()
	assert_has(events, GunMechanism.EV_RELOAD_START)
	assert_true(gun.swapping)
	assert_almost_eq(gun.reload_duration(), data.reload_empty_time, 0.001, "a swap is the long reload (with the rack)")
	_run(data.reload_empty_time + 0.05)
	assert_has(events, GunMechanism.EV_MAG_IN)
	assert_has(events, GunMechanism.EV_EJECT_CHAMBERED, "the live buck shell flies out")
	assert_has(events, GunMechanism.EV_SLIDE_RELEASE)
	assert_eq(gun.ejected_ammo, BUCK)
	assert_eq(gun.chamber_ammo, SLUG)
	assert_eq(gun.mag_ammo, SLUG)
	assert_eq(gun.loaded(), 10, "a full slug magazine with one of them chambered")
	assert_false(gun.needs_swap())
	_step(true)
	assert_eq(gun.fired_ammo, SLUG)


func test_swap_waits_for_the_gun_to_finish_cycling() -> void:
	_step(true)
	assert_eq(gun.state, GunMechanism.State.CYCLING)
	gun.load_ammo = DB
	gun.request_swap()
	_step()
	assert_does_not_have(events, GunMechanism.EV_RELOAD_START, "still cycling")
	_run(data.fire_interval)
	assert_has(events, GunMechanism.EV_RELOAD_START)


func test_trigger_before_the_magazine_seats_cancels_and_fires_the_old_load() -> void:
	gun.load_ammo = SLUG
	gun.request_swap()
	_step()
	_run(data.reload_empty_time * data.mag_in_point * 0.5)
	_step(true)
	assert_has(events, GunMechanism.EV_RELOAD_CANCEL)
	assert_has(events, GunMechanism.EV_FIRE)
	assert_eq(gun.fired_ammo, BUCK)
	assert_eq(gun.mag_ammo, BUCK, "nothing changed")
	assert_eq(gun.load_ammo, SLUG, "the selection stays")


func test_trigger_after_the_magazine_seats_racks_and_fires_the_new_load() -> void:
	gun.load_ammo = DB
	gun.request_swap()
	_step()
	_run(data.reload_empty_time * (data.mag_in_point + 0.05))
	assert_has(events, GunMechanism.EV_MAG_IN)
	_step(true)
	assert_has(events, GunMechanism.EV_EJECT_CHAMBERED)
	assert_has(events, GunMechanism.EV_FIRE)
	assert_eq(gun.fired_ammo, DB, "augmented hands rack it instantly and the new load fires")


func test_swapping_an_empty_gun_has_nothing_to_rack_out() -> void:
	for i: int in 11:
		_fire_once()
	assert_eq(gun.loaded(), 0)
	gun.load_ammo = DB
	gun.request_swap()
	_run(data.reload_empty_time + 0.1)
	assert_does_not_have(events, GunMechanism.EV_EJECT_CHAMBERED)
	assert_eq(gun.chamber_ammo, DB)
	assert_eq(gun.loaded(), 10)


func test_reload_with_another_load_selected_is_a_swap() -> void:
	gun.load_ammo = SLUG
	_step(false, true)
	assert_true(gun.swapping, "X with a different load selected swaps (the gun is full, so a plain reload couldn't)")


func test_selecting_back_to_what_is_loaded_drops_the_swap() -> void:
	_step(true)  # cycling, so the request has to wait
	gun.load_ammo = SLUG
	gun.request_swap()
	gun.load_ammo = BUCK
	_run(data.fire_interval + 0.1)
	assert_does_not_have(events, GunMechanism.EV_RELOAD_START)
