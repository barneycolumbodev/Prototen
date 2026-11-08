extends GutTest
## Core stats, requirements, slots, derived values and the part library
## (docs/design.md §3.6).

var frame: PlayerBodyConfig = preload("res://data/player/body_default.tres")
var lib: PartLibrary = preload("res://data/body/part_library.tres")


func _body(ids: Array[String]) -> BodyModel:
	var lo: BodyLoadout = BodyLoadout.new()
	for id: String in ids:
		var p: PartData = lib.find(StringName(id))
		assert_not_null(p, id)
		lo.parts.append(p)
	return BodyModel.new(frame, lo)


func test_every_stat_has_a_base_inside_its_range() -> void:
	var b: BodyModel = BodyModel.new(frame, BodyLoadout.new())
	assert_gt(Stats.keys().size(), 30)
	for s: StringName in Stats.keys():
		var v: float = b.stat(s)
		assert_between(v, Stats.min_value(s), Stats.max_value(s), String(s))
		assert_ne(Stats.label(s), "", String(s))
		assert_ne(Stats.reads(s), "", "%s says what reads it" % s)
	assert_eq(b.stat(&"connectivity"), 0.0, "an unaugmented brain has no link")
	assert_eq(b.capacity_total(), 16)


func test_library_has_every_part_file_and_every_location() -> void:
	var dir: DirAccess = DirAccess.open("res://data/body/parts")
	var files: int = 0
	for f: String in dir.get_files():
		if f.ends_with(".tres"):
			files += 1
			var p: PartData = load("res://data/body/parts/" + f) as PartData
			assert_not_null(lib.find(p.id), "%s is in the library" % p.id)
	assert_eq(lib.parts.size(), files)
	for loc: int in PartData.Location.values():
		assert_gt(lib.at(loc).size(), 0, "something fits %s" % PartData.location_name(loc))


func test_every_passive_trades_something() -> void:
	for p: PartData in lib.parts:
		if p.fixed or p.is_active():
			continue
		var good: int = 0
		for m: StatModifier in p.modifiers:
			if Stats.modifier_sign(m) > 0:
				good += 1
		assert_gt(good, 0, "%s improves something" % p.id)
		var cost: bool = p.capacity > 0 or p.power_draw_w > 0.0 or p.heat_w > 0.0 or p.mass_kg >= 1.0 or not p.requirements.is_empty()
		assert_true(cost, "%s costs something" % p.id)


func test_unmet_requirement_takes_a_part_offline() -> void:
	var b: BodyModel = _body(["cs1_carapace", "gx4_gauss_arm", "hm5_hydraulic_myomer"])
	assert_false(b.is_online(&"gx4_gauss_arm"), "structure 1.0 < 1.25")
	assert_false(b.is_online(&"hm5_hydraulic_myomer"))
	assert_string_contains(b.offline[&"gx4_gauss_arm"], "structure")
	assert_almost_eq(b.stat(&"strength"), 1.0, 0.001, "an offline part changes no stats")
	assert_almost_eq(b.power_draw_w, 15.0, 0.001, "and draws no power (only the suit)")
	assert_gt(b.mass_kg, frame.base_mass_kg + 15.0, "but its mass still counts")
	var fixed: BodyModel = _body(["cs1_carapace", "gx4_gauss_arm", "hm5_hydraulic_myomer", "tl3_titanium_skeleton"])
	assert_true(fixed.is_online(&"gx4_gauss_arm"))
	assert_true(fixed.is_online(&"hm5_hydraulic_myomer"))


func test_requirements_chain() -> void:
	# FC-1 needs connectivity 1; the MR-1 gives 1.5.
	assert_false(_body(["fc1_fire_control"]).is_online(&"fc1_fire_control"))
	assert_true(_body(["fc1_fire_control", "mr1_mesh_relay"]).is_online(&"fc1_fire_control"))
	# SB-2 needs processing 1.1 and gives capacity.
	var bus: BodyModel = _body(["sb2_spinal_bus", "sa2_synaptic_accelerator"])
	assert_eq(bus.capacity_total(), 19)
	assert_eq(_body(["sb2_spinal_bus"]).capacity_total(), 16, "offline: no extra capacity")


func test_structure_caps_strength() -> void:
	var weak: BodyModel = _body(["hm5_hydraulic_myomer", "cb1_carbon_sheathing"])
	# structure 1.25 -> cap 1.625; strength 1.65
	assert_true(weak.is_online(&"hm5_hydraulic_myomer"))
	assert_almost_eq(weak.usable_strength(), 1.25 * frame.strength_per_structure, 0.001)
	assert_true(weak.strength_capped())
	var strong: BodyModel = _body(["hm5_hydraulic_myomer", "tn9_tungsten_cores"])
	assert_almost_eq(strong.usable_strength(), 1.65, 0.001)
	assert_false(strong.strength_capped())


func test_load_slows_heavy_bodies_unless_strength_carries_them() -> void:
	var base: BodyModel = _body(["cs1_carapace"])
	assert_almost_eq(base.load_scale(), 1.0, 0.02, "the base operative is neutral")
	var heavy: BodyModel = _body(["cs1_carapace", "ct7_trauma_plating", "tn9_tungsten_cores", "dl1_dorsal_load_frame"])
	assert_lt(heavy.load_scale(), 0.8, "56 kg of armour and bone with base muscle")
	var carried: BodyModel = _body(["cs1_carapace", "ct7_trauma_plating", "tn9_tungsten_cores", "dl1_dorsal_load_frame", "hm5_hydraulic_myomer"])
	assert_gt(carried.load_scale(), 0.97, "hydraulic muscle carries it")
	var light: BodyModel = _body(["cs1_carapace", "em2_myofibrils"])
	assert_gt(light.load_scale(), 1.0, "strong and light: a little bonus")


func test_link_range_follows_connectivity() -> void:
	var b: BodyModel = _body(["nl3_cortical_uplink", "mr1_mesh_relay"])
	assert_almost_eq(b.stat(&"connectivity"), 4.5, 0.001)
	assert_almost_eq(b.link_range_m(), 4.5 * frame.link_m_per_connectivity, 0.01)
	assert_eq(_body([]).link_range_m(), 0.0)


func test_heat_raises_signature_and_overheat_is_reported() -> void:
	var b: BodyModel = _body(["cs1_carapace"])
	var cold: float = b.signature_now()
	b.heat_j = frame.heat_capacity_j
	assert_almost_eq(b.signature_now(), cold * (1.0 + frame.heat_signature), 0.001)
	assert_true(b.overheated())


func test_proficiency_and_heavy_recoil() -> void:
	var b: BodyModel = _body(["fc1_fire_control", "mr1_mesh_relay"])
	assert_almost_eq(b.proficiency(WeaponData.WeaponClass.HANDGUN), 1.15, 0.001)
	assert_almost_eq(b.recoil_scale(WeaponData.WeaponClass.HANDGUN), 0.85 / 1.15, 0.001)
	var plain: BodyModel = _body([])
	var heavy: BodyModel = _body(["hm5_hydraulic_myomer", "tn9_tungsten_cores"])
	assert_lt(heavy.recoil_scale(WeaponData.WeaponClass.HEAVY), plain.recoil_scale(WeaponData.WeaponClass.HEAVY) * 0.6,
			"strength and structure hold a machine gun down")


func test_slots_and_install_replaces() -> void:
	var lo: BodyLoadout = BodyLoadout.new()
	lo.install(lib.find(&"tl3_titanium_skeleton"))
	var out: Array[PartData] = lo.install(lib.find(&"tn9_tungsten_cores"))
	assert_eq(out.size(), 1, "one skeleton")
	assert_eq(out[0].id, &"tl3_titanium_skeleton")
	lo.install(lib.find(&"hp4_hyperoxic_lungs"))
	lo.install(lib.find(&"ch2_cardiac_pump"))
	assert_eq(lo.parts_at(PartData.Location.ORGANS).size(), 2, "two organ slots")
	lo.install(lib.find(&"pc3_power_cell"))
	assert_eq(lo.parts_at(PartData.Location.ORGANS).size(), 2)
	assert_false(lo.has_part(&"hp4_hyperoxic_lungs"), "the first one out")


func test_fixed_suit_stays() -> void:
	var lo: BodyLoadout = lib.loadout_from_ids(PackedStringArray(["em2_myofibrils"]))
	assert_true(lo.has_part(&"cs1_carapace"), "the graft suit is always there")
	assert_false(lo.remove(&"cs1_carapace"))
	assert_true(lo.has_part(&"em2_myofibrils"))


func test_presets_are_valid_and_different() -> void:
	var seen: Dictionary[String, bool] = {}
	for lo: BodyLoadout in LoadoutStore.presets():
		var b: BodyModel = BodyModel.new(frame, lo)
		assert_eq(b.problems().size(), 0, "%s: %s" % [lo.display_name, ", ".join(b.problems())])
		var key: String = "%.2f %.2f %.2f" % [b.stat(&"damage_per_kj"), b.load_scale() * b.stat(&"move_speed"), b.stat(&"signature")]
		assert_false(seen.has(key), "%s plays differently" % lo.display_name)
		seen[key] = true
	assert_eq(seen.size(), 4)


func test_loadout_round_trips_through_ids() -> void:
	var lo: BodyLoadout = load("res://data/body/presets/marksman.tres") as BodyLoadout
	var back: BodyLoadout = lib.loadout_from_ids(lo.ids())
	assert_eq(back.ids(), lo.ids())


func test_slide_knock_scales_with_momentum_and_kills_past_the_limit() -> void:
	var cfg: MovementConfig = load("res://data/player/movement_default.tres")
	var base: float = Player.slide_knock_strength(cfg, 100.0, 1.0, cfg.slide_knock_ref_speed)
	assert_almost_eq(base, cfg.slide_knock_speed, 0.001)
	assert_almost_eq(Player.slide_knock_damage(cfg, base), cfg.slide_knock_damage, 0.001)
	assert_almost_eq(Player.slide_knock_damage(cfg, base * 2.0), cfg.slide_knock_damage * 4.0, 0.001, "energy: the square")
	var jug: BodyModel = BodyModel.new(frame, load("res://data/body/presets/juggernaut.tres") as BodyLoadout)
	var push: float = Player.slide_knock_strength(cfg, jug.mass_kg, jug.usable_strength() * jug.stat(&"impact"), cfg.slide_knock_ref_speed)
	assert_gt(push, cfg.slide_knock_lethal_speed, "a juggernaut slide breaks bodies")
	assert_gt(Player.slide_knock_damage(cfg, push), 1000.0)


func test_requirement_text() -> void:
	var r: StatRequirement = StatRequirement.make(&"structure", 1.25)
	assert_eq(r.describe(), "structure ×1.25+")
	assert_true(r.met(1.25))
	assert_false(r.met(1.2))
