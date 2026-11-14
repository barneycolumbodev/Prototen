extends GutTest
## The active parts as data (docs/design.md §3.4, 2026-11-10): the library,
## D-pad slots, mounts, requirements against the passive stats, colours.

var frame: PlayerBodyConfig = preload("res://data/player/body_default.tres")
var lib: PartLibrary = preload("res://data/body/part_library.tres")
const NEW: Array[StringName] = [&"mw7_monofilament_whip", &"nt5_mesh_arm", &"bw6_fan_shield", &"sd3_shrike_drone",
	&"ad2_arc_projector", &"kr5_ram_thrusters", &"tc4_thermoptic_shroud", &"sx8_urticating_setae",
	&"lc6_lorentz_catcher"]


func _operator_with(ids: Array[StringName]) -> BodyLoadout:
	var lo: BodyLoadout = (load("res://data/body/loadout_default.tres") as BodyLoadout).copy()
	for id: StringName in ids:
		lo.install(lib.find(id))
	return lo


func test_the_library_has_eleven_actives_with_behaviours() -> void:
	var acts: Array[ActivePartData] = lib.actives()
	assert_eq(acts.size(), 11, "RX-9, GX-4, the seven of 2026-11-10, the SX-8 and the LC-6")
	for a: ActivePartData in acts:
		assert_not_null(a.behaviour, String(a.id))
		assert_ne(a.short_name, "", String(a.id))
		assert_false(a.requirements.is_empty(), "%s needs something from the passives" % a.id)
		assert_ne(a.synergy, "", "%s says how stats change it" % a.id)
	for id: StringName in NEW:
		assert_not_null(lib.find(id), String(id))


func test_slots_follow_install_order_and_a_fourth_pushes_out_the_first() -> void:
	var lo: BodyLoadout = _operator_with([])
	assert_eq(lo.slot_of(&"rx9_reflex_overclock"), 1)
	assert_eq(lo.slot_of(&"gx4_gauss_arm"), 2)
	lo.install(lib.find(&"kr5_ram_thrusters"))
	assert_eq(lo.slot_of(&"kr5_ram_thrusters"), 3, "third active: D-pad right")
	var out: Array[PartData] = lo.install(lib.find(&"tc4_thermoptic_shroud"))
	assert_eq(lo.actives().size(), 3, "never more than three")
	assert_false(lo.has_part(&"rx9_reflex_overclock"), "the first one installed makes room")
	assert_true(out.has(lib.find(&"rx9_reflex_overclock")))
	assert_eq(lo.slot_of(&"gx4_gauss_arm"), 1, "the others move up")


func test_cycle_slot_swaps_with_the_next() -> void:
	var lo: BodyLoadout = _operator_with([&"kr5_ram_thrusters"])
	assert_eq(lo.cycle_slot(&"rx9_reflex_overclock"), 2)
	assert_eq(lo.slot_of(&"gx4_gauss_arm"), 1)
	assert_eq(lo.cycle_slot(&"kr5_ram_thrusters"), 1, "from the last slot it wraps to the first")
	assert_eq(lo.slot_of(&"gx4_gauss_arm"), 3)


func test_one_part_per_arm() -> void:
	var lo: BodyLoadout = _operator_with([&"mw7_monofilament_whip"])
	assert_false(lo.has_part(&"gx4_gauss_arm"), "the whip and the Gauss arm are both the right arm")
	lo.install(lib.find(&"nt5_mesh_arm"))
	assert_true(lo.has_part(&"mw7_monofilament_whip"), "left and right arms go together")
	lo.install(lib.find(&"bw6_fan_shield"))
	assert_false(lo.has_part(&"nt5_mesh_arm"), "the shield and the mesh arm are both the left arm")
	assert_true(lo.has_part(&"mw7_monofilament_whip"))
	lo.install(lib.find(&"sx8_urticating_setae"))
	assert_false(lo.has_part(&"bw6_fan_shield"), "the setae bank is the left forearm too")
	lo.install(lib.find(&"lc6_lorentz_catcher"))
	assert_false(lo.has_part(&"sx8_urticating_setae"), "so is the catcher's drive ring")
	assert_true(lo.has_part(&"mw7_monofilament_whip"), "the whip in the right hand goes with it")


func test_requirements_come_from_the_passives() -> void:
	var b: BodyModel = BodyModel.new(frame, _operator_with([&"mw7_monofilament_whip", &"nt5_mesh_arm", &"kr5_ram_thrusters"]))
	assert_true(b.is_online(&"mw7_monofilament_whip"), "SA-2: processing 1.2")
	assert_true(b.is_online(&"nt5_mesh_arm"), "EM-2: strength 1.15; TL-3: structure 1.45")
	assert_true(b.is_online(&"kr5_ram_thrusters"), "TL-3: structure 1.45")
	b = BodyModel.new(frame, _operator_with([&"sd3_shrike_drone", &"ad2_arc_projector", &"tc4_thermoptic_shroud"]))
	assert_false(b.is_online(&"sd3_shrike_drone"), "no uplink, no drone")
	assert_false(b.is_online(&"ad2_arc_projector"), "450 W won't charge it")
	assert_false(b.is_online(&"tc4_thermoptic_shroud"), "it replaced the heat sinks: not enough cooling")
	b = BodyModel.new(frame, _operator_with([&"nl3_cortical_uplink", &"sd3_shrike_drone", &"pc3_power_cell", &"ad2_arc_projector",
		&"hp4_hyperoxic_lungs", &"tc4_thermoptic_shroud"]))
	assert_true(b.is_online(&"sd3_shrike_drone"), "NL-3: connectivity 3")
	assert_almost_eq(b.link_range_m(), 120.0, 0.01)
	assert_true(b.is_online(&"ad2_arc_projector"), "PC-3: 650 W")
	assert_true(b.is_online(&"tc4_thermoptic_shroud"), "HP-4: 420 W of cooling")
	var bare: BodyLoadout = BodyLoadout.new()
	bare.install(lib.find(&"bw6_fan_shield"))
	assert_false(BodyModel.new(frame, bare).is_online(&"bw6_fan_shield"), "an organic skeleton can't take the hits")


func test_several_parts_add_their_loads() -> void:
	var b: BodyModel = BodyModel.new(frame, BodyLoadout.new())
	var a: Object = RefCounted.new()
	var c: Object = RefCounted.new()
	b.add_active_load(a, 100.0, 50.0)
	b.add_active_load(c, 40.0, 10.0)
	assert_almost_eq(b.current_draw_w(), 140.0, 0.01)
	b.remove_active_load(a)
	assert_almost_eq(b.current_draw_w(), 40.0, 0.01)
	b.remove_active_load(c)
	assert_almost_eq(b.current_draw_w(), 0.0, 0.01)


func test_cloak_cuts_detection() -> void:
	var b: BodyModel = BodyModel.new(frame, BodyLoadout.new())
	var seen: float = b.detection_scale()
	b.cloak = 1.0
	assert_lt(b.detection_scale(), seen * 0.05)
	assert_true(b.hidden_at(10.0))
	assert_false(b.hidden_at(2.0), "close up they see the shimmer")


func test_colours_round_trip_and_reset() -> void:
	var c: BodyColors = BodyColors.new()
	assert_true(c.is_default())
	c.set_color(&"torso", Color(0.5, 0.1, 0.1))
	c.set_finish(&"torso", BodyColors.Finish.GLOSS)
	c.set_color(BodyColors.part_key(&"hs5_heat_sinks"), Color(1, 0, 0))
	var back: BodyColors = BodyColors.from_dict(c.to_dict())
	assert_true(back.has(&"torso"))
	assert_almost_eq(back.color(&"torso").r, 0.5, 0.01)
	assert_eq(back.finish(&"torso"), BodyColors.Finish.GLOSS)
	assert_true(back.has(&"part:hs5_heat_sinks"))
	back.clear(&"torso")
	assert_false(back.has(&"torso"))
	assert_eq(back.finish(&"torso"), BodyColors.Finish.DEFAULT)
	assert_eq(BodyColors.SUIT_CHANNELS.size(), BodyColors.SUIT_LABELS.size())
	assert_eq(BodyColors.SUIT_CHANNELS.size(), BodyColors.SUIT_REF.size())


func test_region_maps_exist_for_the_suit_and_every_arm_set() -> void:
	for path: String in ["res://assets/characters/operative/textures/operative_regions.png", "res://assets/characters/fp_arms/textures/fp_arms_regions.png",
			"res://assets/characters/fp_arms_m14p/textures/fp_arms_m14p_regions.png", "res://assets/characters/fp_arms_mg42/textures/fp_arms_mg42_regions.png",
			"res://assets/characters/fp_arms_rail/textures/fp_arms_rail_regions.png", "res://assets/characters/fp_arms_saiga/textures/fp_arms_saiga_regions.png"]:
		assert_true(ResourceLoader.exists(path), path)
	var img: Image = (load("res://assets/characters/operative/textures/operative_regions.png") as Texture2D).get_image()
	var seen: Dictionary[int, bool] = {}
	for y: int in range(0, img.get_height(), 8):
		for x: int in range(0, img.get_width(), 8):
			seen[roundi(img.get_pixel(x, y).r * 255.0)] = true
	for id: int in range(1, 11):
		assert_true(seen.has(id), "channel %d (%s) is somewhere on the suit" % [id, BodyColors.SUIT_CHANNELS[id - 1]])
