extends GutTest
## Parts system foundation (docs/design.md §3) and the RX-9 time slowdown.

var frame: PlayerBodyConfig = preload("res://data/player/body_default.tres")


func test_body_sums_parts_and_applies_modifiers() -> void:
	var lo: BodyLoadout = BodyLoadout.new()
	var myo: PartData = load("res://data/body/parts/em2_myofibrils.tres")
	var plate: PartData = load("res://data/body/parts/ct7_trauma_plating.tres")
	lo.parts = [myo, plate]
	var b: BodyModel = BodyModel.new(frame, lo)
	assert_almost_eq(b.mass_kg, frame.base_mass_kg + myo.mass_kg + plate.mass_kg, 0.001)
	assert_almost_eq(b.power_draw_w, myo.power_draw_w + plate.power_draw_w, 0.001)
	assert_eq(b.capacity_used, myo.capacity + plate.capacity)
	# move_speed = 1 × 1.12 × 0.93
	assert_almost_eq(b.stat(&"move_speed"), 1.12 * 0.93, 0.001)
	assert_almost_eq(b.stat(&"damage_per_kj"), frame.damage_per_kj * 0.65, 0.001)
	assert_almost_eq(b.stat(&"max_health"), frame.max_health, 0.001, "untouched stats keep the frame's value")


func test_power_and_heat_pools() -> void:
	var b: BodyModel = BodyModel.new(frame, BodyLoadout.new())
	assert_almost_eq(b.power_fraction(), 1.0, 0.001)
	b.set_active_load(frame.power_supply_w + 1000.0, frame.heat_dissipation_w + 1000.0)
	b.tick(1.0)
	assert_almost_eq(b.power_j, frame.power_capacity_j - 1000.0, 0.01, "an active part drains the reserve")
	assert_almost_eq(b.heat_j, 1000.0, 0.01, "and heats the body")


func test_default_loadout_is_the_base_suit_and_rx9_on_lb() -> void:
	var lo: BodyLoadout = load("res://data/body/loadout_default.tres")
	assert_true(lo.has_part(&"cs1_carapace"))
	var actives: Array[ActivePartData] = lo.actives()
	assert_eq(actives.size(), 1)
	assert_eq(actives[0].id, &"rx9_reflex_overclock")
	assert_eq(actives[0].slot, 1, "LB")


func test_every_part_file_loads_with_known_stats() -> void:
	var dir: DirAccess = DirAccess.open("res://data/body/parts")
	var n: int = 0
	for f: String in dir.get_files():
		if not f.ends_with(".tres"):
			continue
		var p: PartData = load("res://data/body/parts/" + f) as PartData
		assert_not_null(p, f)
		assert_ne(p.id, &"", f)
		for m: StatModifier in p.modifiers:
			assert_has(BodyModel.STATS, m.stat, "%s: %s" % [f, m.stat])
		n += 1
	assert_gt(n, 6)


func test_time_control_dilation_and_player_boost() -> void:
	TimeControl.set_dilation(0.3, 0.6)
	assert_almost_eq(Engine.time_scale, 0.3, 0.001)
	assert_almost_eq(TimeControl.player_boost(), 2.0, 0.001, "the player runs twice as fast as the world")
	assert_almost_eq(TimeControl.real_delta(0.3 / 60.0), 1.0 / 60.0, 0.0001)
	TimeControl.set_dilation(1.0, 1.0)
	assert_almost_eq(Engine.time_scale, 1.0, 0.001)
	assert_almost_eq(TimeControl.player_boost(), 1.0, 0.001)
