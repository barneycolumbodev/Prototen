extends GutTest
## The SL-9 Slagger plasma pistol (docs/design.md §4.9): hold to charge (2.75 s
## to full), let go to fire; too short a charge fizzles; held too long past
## full it overloads. Grazes set men alight and send them running; a charged
## hit to the trunk burns a hole through and goes on; limbs come off
## cauterised (no bleeding stump).

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var _gore: int


func before_each() -> void:
	Fx.enabled = false
	_gore = Settings.gore_level
	Settings.gore_level = Gore.Level.MAXIMUM
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("SL-9 Slagger"))
	await wait_physics_frames(3)


func after_each() -> void:
	weapon.end_script_input()
	PlasmaBolts.get_for(self).clear()
	Settings.gore_level = _gore
	Gore.clear()
	Fx.enabled = true


func _target(i: int = 0) -> Enemy:
	return room.shooting_range.targets[i]


## Holds the trigger for `seconds` (scripted input is per tick), then lets go.
func _hold(seconds: float) -> void:
	weapon.script_hold(true)
	var held: float = 0.0
	while held < seconds:
		await wait_physics_frames(1)
		held = weapon.plasma_held if weapon.plasma_charging else held + 1.0 / Engine.physics_ticks_per_second
	weapon.script_hold(false)
	await wait_physics_frames(3)


func _bolt_at(e: Enemy, zone: StringName, charge: float, side: float = 0.0) -> void:
	var at: Vector3 = e.body.hitboxes[zone].global_position + Vector3(side, 0, 0)
	var from: Vector3 = at + Vector3(0, 0, 3.0)
	PlasmaBolts.get_for(self).launch(weapon.data, from, (at - from).normalized(), charge, player)
	await wait_physics_frames(12)


func test_holding_charges_and_letting_go_fires() -> void:
	var before: int = PlasmaBolts.get_for(self).launched
	await _hold(1.0)
	assert_eq(PlasmaBolts.get_for(self).launched, before + 1, "a bolt left on release")
	assert_almost_eq(weapon.plasma_shot_charge, weapon.data.plasma.charge_fraction(1.0), 0.05, "with the charge built")
	assert_eq(weapon.mechanism.loaded(), weapon.data.magazine_size - 1, "one cell charge spent")


func test_a_full_charge_takes_two_point_seven_five_seconds() -> void:
	var pd: PlasmaData = weapon.data.plasma
	assert_almost_eq(pd.full_charge_time, 2.75, 0.001)
	assert_almost_eq(pd.charge_fraction(2.75), 1.0, 0.001)
	assert_lt(pd.charge_fraction(1.375), 0.5, "it surges at the end")


func test_a_tap_fizzles() -> void:
	var before: int = PlasmaBolts.get_for(self).launched
	await _hold(0.05)
	assert_eq(PlasmaBolts.get_for(self).launched, before, "no shot from a tap")
	assert_eq(weapon.mechanism.loaded(), weapon.data.magazine_size, "nothing spent")


func test_holding_past_full_overloads() -> void:
	var pd: PlasmaData = weapon.data.plasma
	var before: int = PlasmaBolts.get_for(self).launched
	await _hold(pd.full_charge_time + pd.overload_time + 0.2)
	assert_eq(PlasmaBolts.get_for(self).launched, before, "the field failed: no shot")
	assert_false(weapon.plasma_charging)


func test_a_full_charge_burns_through_the_chest_and_goes_on() -> void:
	var e: Enemy = _target()
	await _bolt_at(e, &"chest", 1.0)
	assert_false(e.alive, "dead")
	assert_eq(e.body.hole_count(), 1, "a hole burned clean through")
	assert_gt(PlasmaBolts.get_for(self).hits, 0)


func test_a_graze_sets_him_alight_and_mad_with_pain() -> void:
	var e: Enemy = _target()
	e.passive = false
	await _bolt_at(e, &"chest", 0.6, 0.45)
	assert_true(e.is_burning(), "on fire")
	if e.alive:
		assert_gt(e.agony, 0.0, "in agony")
		assert_eq(e.state, Enemy.State.FLEE, "running")


func test_a_charged_arm_hit_takes_it_off_cauterised() -> void:
	var e: Enemy = _target()
	await _bolt_at(e, &"l_forearm", 0.6)
	assert_true(e.body.severed.has(&"forearm_L") or e.body.severed.has(&"hand_L"), "the arm comes off")
	assert_eq(e.bleed_dps, 0.0, "cauterised: no bleeding stump")
