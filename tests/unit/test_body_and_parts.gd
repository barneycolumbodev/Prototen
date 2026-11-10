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
	assert_almost_eq(b.stat(&"move_speed"), 1.1, 0.001)
	assert_almost_eq(b.stat(&"damage_per_kj"), frame.damage_per_kj * 0.62, 0.001)
	assert_almost_eq(b.stat(&"max_health"), frame.max_health + 40.0, 0.001)
	assert_almost_eq(b.stat(&"regen_rate"), frame.regen_rate, 0.001, "untouched stats keep the frame's value")


func test_power_and_heat_pools() -> void:
	var b: BodyModel = BodyModel.new(frame, BodyLoadout.new())
	assert_almost_eq(b.power_fraction(), 1.0, 0.001)
	b.set_active_load(frame.power_supply_w + 1000.0, frame.heat_dissipation_w + 1000.0)
	b.tick(1.0)
	assert_almost_eq(b.power_j, frame.power_capacity_j - 1000.0, 0.01, "an active part drains the reserve")
	assert_almost_eq(b.heat_j, 1000.0, 0.01, "and heats the body")


func test_default_loadout_is_the_base_suit_rx9_and_the_gauss_arm() -> void:
	var lo: BodyLoadout = load("res://data/body/loadout_default.tres")
	assert_true(lo.has_part(&"cs1_carapace"))
	var b: BodyModel = BodyModel.new(frame, lo)
	assert_eq(b.problems().size(), 0, "the default loadout is valid: %s" % ", ".join(b.problems()))
	assert_true(b.is_online(&"rx9_reflex_overclock"), "SA-2 meets the RX-9's processing requirement")
	assert_true(b.is_online(&"gx4_gauss_arm"), "TL-3 meets the GX-4's structure requirement")
	var actives: Array[ActivePartData] = lo.actives()
	assert_eq(actives.size(), 2)
	assert_eq(actives[0].id, &"rx9_reflex_overclock")
	assert_eq(lo.slot_of(&"rx9_reflex_overclock"), 1, "D-pad left")
	assert_eq(actives[1].id, &"gx4_gauss_arm")
	assert_eq(lo.slot_of(&"gx4_gauss_arm"), 2, "D-pad down")


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
			assert_true(Stats.has(m.stat), "%s: %s" % [f, m.stat])
		for r: StatRequirement in p.requirements:
			assert_true(Stats.has(r.stat), "%s requires %s" % [f, r.stat])
			for m: StatModifier in p.modifiers:
				assert_ne(m.stat, r.stat, "%s can't meet its own requirement" % f)
		n += 1
	assert_gt(n, 30, "the passive library")


func test_time_control_dilation_and_player_boost() -> void:
	TimeControl.set_dilation(0.3, 0.6)
	assert_almost_eq(Engine.time_scale, 0.3, 0.001)
	assert_almost_eq(TimeControl.player_boost(), 2.0, 0.001, "the player runs twice as fast as the world")
	assert_almost_eq(TimeControl.real_delta(0.3 / 60.0), 1.0 / 60.0, 0.0001)
	TimeControl.set_dilation(1.0, 1.0)
	assert_almost_eq(Engine.time_scale, 1.0, 0.001)
	assert_almost_eq(TimeControl.player_boost(), 1.0, 0.001)
