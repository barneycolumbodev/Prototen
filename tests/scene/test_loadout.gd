extends GutTest
## The loadout screen (body status), stat-driven actives and the R3 strike
## (docs/design.md §3.6).

var room: TestRoom
var player: Player


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(10)


func after_each() -> void:
	if player and player.augments and player.augments.status and player.augments.status.is_open():
		player.augments.status.close()
	get_tree().paused = false
	TimeControl.set_dilation(1.0, 1.0)


func test_install_trauma_plating_from_the_screen() -> void:
	var st: BodyStatus = player.augments.status
	var mass: float = player.body.mass_kg
	st.open()
	assert_true(st.select_part(&"ct7_trauma_plating"), "every part has a tile")
	assert_gt(st.preview_body.mass_kg, mass + 17.0, "the preview carries the plates")
	assert_eq(player.body.mass_kg, mass, "nothing changes until it's installed")
	var shown: int = st.appearance.mounted.size()
	assert_gt(shown, 0, "the preview body wears hardware")
	st.activate()
	st.close()
	await wait_frames(1)
	assert_true(player.loadout.has_part(&"ct7_trauma_plating"))
	assert_almost_eq(player.body.mass_kg, mass + 18.0, 0.01)
	assert_lt(player.body.stat(&"damage_per_kj"), 5.0)
	assert_false(get_tree().paused)


func test_removing_the_accelerator_takes_rx9_offline() -> void:
	var st: BodyStatus = player.augments.status
	st.open()
	assert_true(st.select_part(&"sa2_synaptic_accelerator"))
	assert_true(st.working.has_part(&"sa2_synaptic_accelerator"))
	st.activate()  # A on an installed part takes it out
	assert_false(st.working.has_part(&"sa2_synaptic_accelerator"))
	st.close()
	await wait_frames(2)
	var rx9: ActivePart = player.augments.find(&"rx9_reflex_overclock")
	assert_not_null(rx9)
	assert_true(rx9.is_offline(), "processing 1.0 < 1.15")
	assert_string_contains(rx9.offline_reason(), "processing")
	assert_false(rx9.can_start())


func test_processing_changes_rx9() -> void:
	var rx9: TimeDilation = player.augments.find(&"rx9_reflex_overclock") as TimeDilation
	var at_ref: float = rx9.player_scale_now()
	assert_almost_eq(at_ref, (rx9.data as TimeDilationData).player_scale, 0.001, "the default loadout is the reference")
	var lo: BodyLoadout = player.loadout.copy()
	lo.install(LoadoutStore.LIBRARY.find(&"tg6_threat_graph"))  # cranial: +0.1 processing
	player.apply_loadout(lo)
	await wait_frames(1)
	rx9 = player.augments.find(&"rx9_reflex_overclock") as TimeDilation
	assert_almost_eq(player.body.stat(&"processing"), 1.3, 0.001)
	assert_gt(rx9.player_scale_now(), at_ref, "more processing: faster in slow motion")
	assert_gt(rx9.charge_capacity(), rx9.data.charge_max, "and a longer charge")


func test_gx4_kick_follows_bracing() -> void:
	var gx: GaussArm = player.augments.find(&"gx4_gauss_arm") as GaussArm
	assert_almost_eq(gx.kick_scale(), 1.0, 0.05, "TL-3 + EM-2 is the reference")
	var lo: BodyLoadout = LoadoutStore.presets()[2].copy()  # juggernaut: tungsten + hydraulics
	player.apply_loadout(lo)
	await wait_frames(1)
	gx = player.augments.find(&"gx4_gauss_arm") as GaussArm
	assert_lt(gx.kick_scale(), 0.6, "a juggernaut barely flinches (about half the kick)")


func _face(e: Enemy, dist: float) -> void:
	var to: Vector3 = (player.global_position - e.global_position)
	to.y = 0.0
	player.global_position = e.global_position + to.normalized() * dist
	var d: Vector3 = e.global_position - player.global_position
	player.set_view(atan2(-d.x, -d.z), -0.15)


func test_melee_strike_hurts_and_shoves() -> void:
	var e: Enemy = room.shooting_range.targets[0]
	_face(e, 1.6)
	await wait_physics_frames(2)
	_face(e, 1.6)
	var hp: float = e.health
	assert_eq(player.melee.target(), e)
	player.melee.script_strike()
	await wait_physics_frames(20)
	assert_true(not e.alive or e.health < hp - 30.0, "the strike lands (%.0f -> %.0f)" % [hp, e.health])


func test_juggernaut_strike_breaks_the_body() -> void:
	player.apply_loadout(LoadoutStore.presets()[2].copy())
	assert_gt(player.melee.push_speed(), player.melee.cfg.lethal_push)
	var e: Enemy = room.shooting_range.targets[0]
	_face(e, 1.6)
	await wait_physics_frames(2)
	_face(e, 1.6)
	player.melee.script_strike()
	await wait_physics_frames(20)
	assert_false(e.alive, "lethal")


func test_noise_and_signature_reach_enemies() -> void:
	assert_eq(player.noise_level(), 0.0, "standing still is silent")
	var ghost: BodyModel = BodyModel.new(player.body_config, LoadoutStore.presets()[1])
	var jug: BodyModel = BodyModel.new(player.body_config, LoadoutStore.presets()[2])
	assert_lt(ghost.detection_scale(), 0.75, "chromatophore skin")
	assert_lt(ghost.stat(&"noise"), 0.6, "dampers")
	assert_gt(jug.stat(&"profile"), 1.3, "plates and the frame")


func test_every_part_is_on_the_grid() -> void:
	var st: BodyStatus = player.augments.status
	st.open()
	var shown: int = 0
	for p: PartData in LoadoutStore.LIBRARY.parts:
		if p.fixed:
			continue
		assert_true(st.select_part(p.id), "%s has a tile" % p.id)
		shown += 1
	assert_eq(st._preset_tiles.size(), LoadoutStore.presets().size(), "a tile per preset")
	assert_gt(shown, 40)


func test_a_missing_requirement_names_its_parts_and_rb_goes_there() -> void:
	var st: BodyStatus = player.augments.status
	st.open()
	st.select_part(&"sa2_synaptic_accelerator")
	st.activate()  # out: RX-9 goes offline
	assert_true(st.working_body.offline.has(&"rx9_reflex_overclock"))
	st.select_part(&"rx9_reflex_overclock")
	assert_true(st.fix_ids.has(&"sa2_synaptic_accelerator"), "SA-2 supplies processing: its tile is outlined")
	assert_string_contains(st._text.text, "SA-2 Synaptic Accelerator", "the card names the part that fixes it")
	var to: StringName = st.jump_to_fix()
	assert_ne(to, &"", "RB goes somewhere")
	assert_eq(st.selected, to)
	st.activate()
	assert_false(st.working_body.offline.has(&"rx9_reflex_overclock"), "installing the part RB found brings RX-9 back")
	# The HUD's offline line names the fix too.
	var lo: BodyLoadout = player.loadout.copy()
	lo.remove(&"sa2_synaptic_accelerator")
	var b: BodyModel = BodyModel.new(player.body_config, lo)
	assert_string_contains(BodyStatus.fix_hint(LoadoutStore.LIBRARY, LoadoutStore.LIBRARY.find(&"rx9_reflex_overclock"), b), "SA-2")


func test_x_moves_an_active_to_the_next_dpad_slot() -> void:
	var st: BodyStatus = player.augments.status
	st.open()
	var acts: Array[ActivePartData] = st.working.actives()
	if acts.size() < 2:
		pass_test("needs two actives")
		return
	var id: StringName = acts[0].id
	st.select_part(id)
	st.secondary()
	assert_eq(st.working.slot_of(id), 2, "D-left -> D-down")


func test_presets_apply_from_their_tiles() -> void:
	var st: BodyStatus = player.augments.status
	st.open()
	st.select_preset(2)
	st.activate()
	assert_eq(st.working.ids(), LoadoutStore.presets()[2].ids())
