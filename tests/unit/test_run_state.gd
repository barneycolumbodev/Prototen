extends GutTest
## A Survival run as data (docs/design.md §8.2, §8.4, §8.5): doctrines as
## baseline bodies, the supply drops, doctrine and affinity bias.

var cfg: SurvivalConfig = preload("res://data/run/survival.tres")
var lib: PartLibrary = preload("res://data/body/part_library.tres")


func _run(doctrine: String = "Ghost", seed_value: int = 7) -> RunState:
	var r: RunState = RunState.new(cfg, seed_value)
	var d: Doctrine = cfg.doctrine_named(doctrine)
	r.start(d, cfg.starter_weapons[0], d.starter_actives[0])
	return r


func test_the_pool_covers_every_gun_and_part() -> void:
	for p: PartData in lib.parts:
		if not p.fixed:
			assert_not_null(cfg.item_by_id(p.id), "%s can drop" % p.id)
	assert_eq(cfg.starter_weapons.size(), 3, "Five-seveN, MP5, Saiga-12K")
	for it: RunItem in cfg.pool:
		assert_false(it.tags.is_empty(), "%s has tags" % it.id())
		for t: StringName in it.tags:
			assert_true(t in [&"mobility", &"stealth", &"heavy", &"precision", &"close", &"tech"], "%s: tag %s" % [it.id(), t])


func test_every_doctrine_runs_its_starting_actives_at_mk1() -> void:
	assert_eq(cfg.doctrines.size(), 5)
	for d: Doctrine in cfg.doctrines:
		assert_gte(d.starter_actives.size(), 2, "%s offers a choice" % d.display_name)
		for a: ActivePartData in d.starter_actives:
			var r: RunState = RunState.new(cfg, 1)
			r.start(d, cfg.starter_weapons[0], a)
			var m: BodyModel = r.body()
			assert_true(m.is_online(a.id), "%s runs %s (%s)" % [d.display_name, a.id, m.unmet(a)])
			assert_gte(m.capacity_left(), 0, "%s with %s fits" % [d.display_name, a.id])
			assert_eq(r.mark_of(a.id), 1)
			assert_string_contains(r.loadout.find(a.id).display_name, "Mk I")
			assert_true(m.problems().is_empty(), "%s + %s: %s" % [d.display_name, a.id, m.problems()])


func test_start_kit() -> void:
	var r: RunState = _run()
	assert_eq(r.guns.size(), 1)
	assert_eq(r.loadout.actives().size(), 1)
	assert_true(r.loadout.has_part(&"cs1_carapace"), "the suit")
	assert_true(r.loadout.has_part(&"sa2_synaptic_accelerator"), "Ghost's frame")


func test_first_drop_is_a_choice_of_two_different_kinds() -> void:
	for s: int in range(1, 30):
		var r: RunState = _run("Ghost", s)
		r.wave = 1
		var d: Array[RunState.Offer] = r.roll_drop()
		assert_eq(d.size(), 2, "seed %d" % s)
		if d.size() == 2:
			assert_ne(d[0].item, d[1].item)
			assert_ne(d[0].item.kind(), d[1].item.kind(), "seed %d: a gun or an active or a passive" % s)


func test_drops_never_bring_what_you_own_or_boss_only_hardware() -> void:
	var r: RunState = _run("Reaper", 3)
	for w: int in range(1, 25):
		r.wave = w
		for o: RunState.Offer in r.roll_drop():
			assert_false(o.item.boss_only and not o.upgrade, "%s is boss-only" % o.item.id())
			if not o.upgrade:
				assert_false(r.owns(o.item), "%s already owned" % o.item.id())
			assert_lte(o.item.min_wave, w)
		var drop: Array[RunState.Offer] = r.roll_drop()
		if not drop.is_empty():
			r.take(drop[0])
		assert_lte(r.guns.size(), cfg.max_guns)
		assert_lte(r.loadout.actives().size(), BodyLoadout.MAX_ACTIVES)
		assert_gte(r.body().capacity_left(), 0, "wave %d: within capacity" % w)


func test_doctrine_bends_the_odds() -> void:
	# Over many first offers, Ghost sees far more stealth items than Juggernaut does.
	var counts: Dictionary[String, int] = {"Ghost": 0, "Juggernaut": 0}
	for name: String in counts.keys():
		for s: int in range(1, 400):
			var r: RunState = _run(name, s)
			r.wave = 8
			var o: Array[RunState.Offer] = r.roll_drop()
			if not o.is_empty() and o[0].item.has_tag(&"stealth"):
				counts[name] += 1
	gut.p("stealth first offers: %s" % counts)
	assert_gt(counts["Ghost"], counts["Juggernaut"] * 1.6)


func test_affinity_pulls_more_of_the_same() -> void:
	var r: RunState = _run("Ghost", 5)
	var before: float = r.affinity([&"heavy"])
	r.loadout.install(lib.find(&"tl3_titanium_skeleton"))
	r.loadout.install(lib.find(&"ct7_trauma_plating"))
	assert_gt(r.affinity([&"heavy"]), before)
	assert_lte(r.affinity([&"heavy"]), cfg.affinity_max)


func test_taking_an_upgrade_keeps_the_dpad_slot() -> void:
	var r: RunState = _run("Ghost", 9)
	var setae: RunItem = cfg.item_by_id(&"sx8_urticating_setae")
	r.take(r.make_offer(setae))
	assert_eq(r.loadout.slot_of(&"sx8_urticating_setae"), 2)
	var rx: RunItem = cfg.item_by_id(&"rx9_reflex_overclock")
	var up: RunState.Offer = r.make_offer(rx, true)
	assert_true(up.upgrade)
	assert_eq(up.mark, 2)
	r.take(up)
	assert_eq(r.mark_of(&"rx9_reflex_overclock"), 2)
	assert_eq(r.loadout.slot_of(&"rx9_reflex_overclock"), 1, "still D-pad left")
	assert_eq((r.loadout.find(&"rx9_reflex_overclock") as ActivePartData).charge_max, 6.0)


func test_boss_drop_upgrades_or_brings_an_active() -> void:
	var r: RunState = _run("Marksman", 4)
	r.wave = 5
	var o: RunState.Offer = r.roll_boss_drop()
	assert_not_null(o)
	assert_true(o.upgrade, "the starting active goes to Mk II")
	r.take(o)
	r.take(r.roll_boss_drop())
	assert_eq(r.mark_of(&"rx9_reflex_overclock"), 3, "Mk III, the ceiling")
	var o3: RunState.Offer = r.roll_boss_drop()
	assert_false(o3.upgrade, "nothing left to upgrade: a new active")
	assert_eq(o3.item.kind(), RunItem.Kind.ACTIVE)


func test_the_incense_master_drops_his_gauss_arm_or_its_next_mark() -> void:
	var gx4: ActivePartData = lib.find(&"gx4_gauss_arm") as ActivePartData
	var r: RunState = _run("Juggernaut", 3)
	r.wave = 5
	var d: Array[RunState.Offer] = r.roll_boss_drops(gx4)
	assert_eq(d.size(), 1, "the Juggernaut has a free right arm and room on the D-pad: just the arm")
	assert_eq(d[0].item.id(), &"gx4_gauss_arm")
	assert_eq(d[0].mark, 1)
	assert_false(d[0].upgrade)
	r.take(d[0])
	assert_eq(r.mark_of(&"gx4_gauss_arm"), 1)
	var d2: Array[RunState.Offer] = r.roll_boss_drops(gx4)
	assert_true(d2[0].upgrade, "has it: the next mark")
	assert_eq(d2[0].mark, 2)
	r.take(d2[0])
	r.take(r.roll_boss_drops(gx4)[0])
	assert_eq(r.mark_of(&"gx4_gauss_arm"), 3)
	var d4: Array[RunState.Offer] = r.roll_boss_drops(gx4)
	assert_false(d4.is_empty(), "at Mk III: the usual boss drop instead")
	assert_ne(d4[0].item.id(), &"gx4_gauss_arm")


func test_when_the_arm_would_cost_an_active_there_is_a_choice() -> void:
	var gx4: ActivePartData = lib.find(&"gx4_gauss_arm") as ActivePartData
	# Reaper with the whip: the whip is on the right arm too.
	var r: RunState = RunState.new(cfg, 5)
	var d: Doctrine = cfg.doctrine_named("Reaper")
	r.start(d, cfg.starter_weapons[0], lib.find(&"mw7_monofilament_whip") as ActivePartData)
	r.wave = 5
	var offers: Array[RunState.Offer] = r.roll_boss_drops(gx4)
	assert_eq(offers.size(), 2, "the arm, or the usual boss drop")
	assert_eq(offers[0].item.id(), &"gx4_gauss_arm")
	var ids: Array[StringName] = []
	for p: PartData in offers[0].replaces:
		ids.append(p.id)
	assert_true(&"mw7_monofilament_whip" in ids, "the card says the whip comes off")


func test_a_passive_that_would_push_out_an_active_never_drops() -> void:
	# Ghost: SA-2 and RX-9 fill both nervous-system slots; ER-2 and MR-1 would push one out.
	var r: RunState = _run("Ghost", 2)
	var ids: Array[StringName] = []
	for it: RunItem in r.eligible(RunItem.Kind.PASSIVE):
		ids.append(it.id())
	assert_false(&"er2_reflex_bypass" in ids)
	assert_false(&"mr1_mesh_relay" in ids)
