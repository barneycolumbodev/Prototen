extends GutTest
## The Tuning screen's Lever and Plasma sections (the Governor, the SL-9):
## shown only for the gun they belong to, aimed at the right resource, and
## plasma values saved under their own prefix.

var gov: WeaponData = preload("res://data/weapons/governor.tres")
var slag: WeaponData = preload("res://data/weapons/slagger.tres")
var m14: WeaponData = preload("res://data/weapons/m14p.tres")


func _param(section: String, prop: String) -> Array:
	for p: Array in TuningMenu.WEAPON_PARAMS:
		if p[0] == section and p[1] == prop:
			return p
	return []


func test_sections_show_for_their_gun_only() -> void:
	var lever: Array = _param("Lever", "lever_time")
	var plasma: Array = _param("Plasma", "full_charge_time")
	assert_false(lever.is_empty())
	assert_false(plasma.is_empty())
	assert_true(TuningMenu.shows(lever, gov))
	assert_false(TuningMenu.shows(lever, m14))
	assert_true(TuningMenu.shows(plasma, slag))
	assert_false(TuningMenu.shows(plasma, gov))
	assert_false(TuningMenu.shows(_param("Ballistics", "muzzle_velocity"), slag), "no bullet ballistics on a plasma gun")


func test_plasma_values_live_in_the_plasma_data() -> void:
	var p: Array = _param("Plasma", "speed_full")
	assert_eq(TuningMenu.param_target(p, slag), slag.plasma)
	assert_eq(TuningMenu.key_prefix(p), TuningMenu.PLASMA_KEY)
	for q: Array in TuningMenu.WEAPON_PARAMS:
		var prop: String = q[1]
		if TuningMenu.shows(q, slag):
			assert_true(prop in TuningMenu.param_target(q, slag), "%s exists on its target" % prop)
		if TuningMenu.shows(q, gov):
			assert_true(prop in TuningMenu.param_target(q, gov), "%s exists on the Governor" % prop)
