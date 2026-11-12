extends GutTest
## The seven active parts of 2026-11-10 in the test room (docs/design.md
## §3.4): the whip, the mesh arm, the fan shield, the Shrike drone, the arc
## projector, the ram thrusters and the thermoptic shroud.

var room: TestRoom
var player: Player
var lib: PartLibrary = preload("res://data/body/part_library.tres")
var _gore: int = 2


func before_each() -> void:
	_gore = Settings.gore_level
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(10)
	player.global_position = Vector3(0.5, 0.0, 6.0)
	player.set_view(0.0, 0.0)


func after_each() -> void:
	for a: StringName in [&"active_use", &"active_select_1", &"active_select_2", &"active_select_3", &"fire", &"aim"]:
		Input.action_release(a)
	Settings.gore_level = _gore
	TimeControl.set_dilation(1.0, 1.0)
	Gore.clear()


## The Operator with `ids` installed; returns the last one's part.
func _equip(ids: Array[StringName]) -> ActivePart:
	var lo: BodyLoadout = player.loadout.copy()
	for id: StringName in ids:
		lo.install(lib.find(id))
	player.apply_loadout(lo)
	await wait_frames(2)
	var part: ActivePart = player.augments.find(ids[ids.size() - 1])
	assert_not_null(part, "installed")
	if part:
		assert_eq(part.offline_reason(), "", "online")
	return part


func _real_wait(seconds: float) -> void:
	var end: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await wait_frames(1)


func _deploy(part: ActivePart) -> void:
	player.augments.select(part.slot)
	player.augments.use_selected()
	await _real_wait(part.data.deploy_time + 0.15)


## Puts range target `i` at `at`, facing the operative; returns it.
func _target(i: int, at: Vector3) -> Enemy:
	var e: Enemy = room.shooting_range.targets[i]
	e.global_position = at
	e.face(0.0)
	return e


func _aim_at(point: Vector3) -> void:
	GunplayDemo.aim_at(player, point)


# ------------------------------------------------------------------ MW-7 whip

func test_the_whip_takes_the_right_hand_and_pays_out() -> void:
	var whip: Whip = await _equip([&"mw7_monofilament_whip"]) as Whip
	await _deploy(whip)
	assert_eq(whip.state, ActivePart.State.ACTIVE)
	assert_true(player.weapon().stowed, "the gun goes away")
	assert_true(whip.rig.visible)
	assert_not_null(whip.rig.anim, "the deploy clip was imported")
	assert_eq(whip.pts.size(), whip.cfg.segments + 1)
	await _real_wait(0.5)
	var length: float = 0.0
	for i: int in whip.pts.size() - 1:
		length += whip.pts[i].distance_to(whip.pts[i + 1])
	assert_almost_eq(length, whip.cfg.length, 1.2, "the filament has paid out")
	player.augments.use_selected()
	await _real_wait(whip.data.recover_time + whip.data.cooldown_time + 0.4)
	assert_false(player.weapon().stowed, "reeled in: the gun comes back")


func test_a_lash_cuts_a_man_in_reach() -> void:
	Settings.gore_level = 2
	var whip: Whip = await _equip([&"mw7_monofilament_whip"]) as Whip
	var e: Enemy = _target(0, Vector3(0.5, 0.0, 3.0))
	await wait_physics_frames(3)
	_aim_at(e.body.chest_position())
	await _deploy(whip)
	await _real_wait(0.4)
	var health: float = e.health
	for i: int in 4:
		whip.script_lash()
		await _real_wait(0.6)
		if whip.cuts > 0:
			break
	assert_gt(whip.cuts, 0, "the filament crossed him")
	assert_gt(whip.peak_tip_speed, whip.cfg.min_cut_speed, "fast enough to cut")
	assert_true(not e.alive or e.health < health, "and it hurt")


func test_lt_holds_the_view_for_the_stick() -> void:
	var whip: Whip = await _equip([&"mw7_monofilament_whip"]) as Whip
	await _deploy(whip)
	Input.action_press(&"aim")
	await wait_frames(4)
	assert_true(player.look_frozen, "LT: the right stick steers the whip, not the view")
	Input.action_release(&"aim")
	await wait_frames(4)
	assert_false(player.look_frozen)


# ------------------------------------------------------------------ NT-5 mesh arm

func test_the_mesh_arm_grabs_holds_and_throws() -> void:
	var arm: MeshArm = await _equip([&"nt5_mesh_arm"]) as MeshArm
	var e: Enemy = _target(0, Vector3(0.5, 0.0, -1.0))
	var other: Enemy = _target(2, Vector3(0.5, 0.0, -6.0))
	await wait_physics_frames(3)
	_aim_at(e.body.chest_position())
	await _deploy(arm)
	assert_eq(arm.mode, MeshArm.Mode.READY)
	var grabs: float = arm.charge
	arm.script_fire()
	await _real_wait(0.6)
	assert_eq(arm.mode, MeshArm.Mode.HOLDING, "it reached him")
	assert_true(e.held, "seized")
	assert_true(e.alive, "alive in its grip")
	assert_false(e.is_in_group(&"enemies"), "out of the fight")
	assert_almost_eq(arm.charge, grabs - 1.0, 0.01, "one grab spent")
	await _real_wait(0.8)
	var hold: Vector3 = player.camera().global_position + player.camera().global_basis * arm.cfg.hold_offset
	assert_lt(e.body.chest_position().distance_to(hold), 1.6, "hauled in front of the operative")
	_aim_at(other.body.chest_position() + Vector3.UP * 0.4)
	arm.script_fire()
	await wait_physics_frames(2)
	assert_false(e.held, "thrown")
	assert_eq(arm.throws, 1)
	await _real_wait(2.6)
	assert_false(e.alive, "he dies where he lands")
	assert_gt(arm.throw_speed(), arm.cfg.min_throw)


func test_folding_the_arm_drops_whoever_it_holds() -> void:
	var arm: MeshArm = await _equip([&"nt5_mesh_arm"]) as MeshArm
	var e: Enemy = _target(0, Vector3(0.5, 0.0, 0.0))
	await wait_physics_frames(3)
	_aim_at(e.body.chest_position())
	await _deploy(arm)
	arm.script_fire()
	await _real_wait(0.5)
	assert_true(e.held)
	player.augments.use_selected()
	await _real_wait(0.3)
	assert_false(e.held, "let go")


# ------------------------------------------------------------------ BW-6 shield

func test_the_shield_stops_rounds_from_the_front_only() -> void:
	player.invulnerable = false
	var shield: FanShield = await _equip([&"bw6_fan_shield"]) as FanShield
	await _deploy(shield)
	assert_eq(shield.state, ActivePart.State.ACTIVE)
	assert_true(player.weapon().stowed, "it takes the left hand")
	var fwd: Vector3 = -player.camera().global_basis.z
	var health: float = player.health
	var full: float = shield.charge
	var hit: BallisticHit = BallisticHit.new()
	hit.energy_in = 1800.0
	hit.direction = -fwd
	player.on_ballistic_hit(hit)
	assert_almost_eq(player.health, health, 0.001, "a rifle round from the front is stopped")
	assert_eq(shield.stopped, 1)
	assert_almost_eq(shield.charge, full - 1.8, 0.01, "and paid for in integrity")
	hit.direction = fwd
	player.on_ballistic_hit(hit)
	assert_lt(player.health, health, "from behind it isn't")


func test_the_shield_breaks_and_needs_time() -> void:
	player.invulnerable = false
	var shield: FanShield = await _equip([&"bw6_fan_shield"]) as FanShield
	await _deploy(shield)
	var hit: BallisticHit = BallisticHit.new()
	hit.energy_in = 30000.0
	hit.direction = player.camera().global_basis.z
	player.on_ballistic_hit(hit)
	assert_true(shield.broken)
	assert_false(shield.is_running(), "it folds")
	assert_true(shield.is_offline(), "and can't come up again yet")
	assert_almost_eq(player.melee.push_bonus, 1.0, 0.001, "no bash without it")


# ------------------------------------------------------------------ SD-3 drone

func test_the_drone_flies_from_its_own_camera_and_kills_with_its_warhead() -> void:
	Settings.gore_level = 2
	var drone: ShrikeDrone = await _equip([&"nl3_cortical_uplink", &"sd3_shrike_drone"]) as ShrikeDrone
	var e: Enemy = _target(0, Vector3(0.5, 0.0, -2.0))
	var own: Camera3D = player.camera()
	assert_eq(drone.hud_pips(), 3)
	await _deploy(drone)
	assert_true(drone.is_piloting())
	assert_false(player.input_enabled, "the operative stands still")
	assert_true(drone.cam.current, "the view is the drone's")
	assert_almost_eq(drone.charge, 2.0, 0.01, "one drone spent")
	assert_gt(drone.link, 0.9, "right next to the operative: full link")
	drone.craft.global_position = e.body.chest_position() + Vector3(0.0, 0.3, 1.5)
	await wait_physics_frames(25)
	drone.script_detonate()
	await _real_wait(0.3)
	assert_eq(drone.last_end, &"detonated")
	assert_false(e.alive, "inside the blast")
	assert_gt(drone.last_kills, 0)
	assert_true(own.current, "back behind his own eyes")
	assert_true(player.input_enabled)


func test_the_link_drops_out_of_range() -> void:
	var drone: ShrikeDrone = await _equip([&"nl3_cortical_uplink", &"sd3_shrike_drone"]) as ShrikeDrone
	await _deploy(drone)
	drone.craft.global_position = player.global_position + Vector3(0.0, 30.0, -player.body.link_range_m() - 5.0)
	await _real_wait(0.2)
	assert_eq(drone.last_end, &"range", "beyond connectivity × 40 m the link is gone")
	assert_true(player.camera().current)


# ------------------------------------------------------------------ AD-2 arc

func test_the_arc_chains_and_comes_out_of_the_reserve() -> void:
	var arc: ArcProjector = await _equip([&"pc3_power_cell", &"ad2_arc_projector"]) as ArcProjector
	var a: Enemy = _target(0, Vector3(0.5, 0.0, -2.0))
	var b: Enemy = _target(2, Vector3(3.0, 0.0, -4.0))
	await wait_physics_frames(3)
	_aim_at(a.body.chest_position())
	var reserve: float = player.body.power_j
	await _deploy(arc)
	await _real_wait(0.2)
	assert_eq(arc.discharges, 1, "LB raises it and fires")
	assert_false(player.weapon().stowed, "the gun stays in the hands")
	assert_eq(arc.last_targets.size(), 2, "the arc jumped to the second man")
	assert_eq(arc.last_targets[0], a)
	assert_true(arc.last_targets.has(b))
	assert_lt(player.body.power_j, reserve - arc.cfg.discharge_j * 0.9, "18 kJ out of the reserve")
	assert_false(a.alive, "the first body takes all of it")
	assert_almost_eq(arc.charge, 1.0, 0.05)
	assert_eq(arc.chain_count(), arc.cfg.chains, "base reserve: base chain")


# ------------------------------------------------------------------ KR-5 ram

func test_the_ram_throws_the_operative_through_a_man() -> void:
	var ram: RamThrusters = await _equip([&"kr5_ram_thrusters"]) as RamThrusters
	var e: Enemy = _target(0, Vector3(0.5, 0.0, 2.5))
	await wait_physics_frames(3)
	var start: Vector3 = player.global_position
	var heat: float = player.body.heat_j
	player.augments.select(ram.slot)
	player.augments.use_selected()
	await wait_physics_frames(3)
	assert_true(player.is_dashing())
	await _real_wait(0.6)
	assert_gt(start.z - player.global_position.z, 3.0, "thrown forward")
	assert_eq(ram.struck, 1, "through him")
	assert_gt(player.body.heat_j, heat, "each burn heats the body")
	assert_almost_eq(ram.charge, 1.0, 0.2, "one of two burns spent")
	assert_gt(ram.ram_push(), player.movement.slide_knock_speed, "harder than a slide")
	assert_false(e.alive, "the Operator's mass and strength break him")


# ------------------------------------------------------------------ TC-4 shroud

func test_the_shroud_hides_and_a_shot_breaks_it() -> void:
	var shroud: ThermopticShroud = await _equip([&"hp4_hyperoxic_lungs", &"tc4_thermoptic_shroud"]) as ThermopticShroud
	await _deploy(shroud)
	assert_eq(shroud.state, ActivePart.State.ACTIVE)
	assert_true(shroud.is_hidden())
	assert_almost_eq(player.body.cloak, 1.0, 0.01)
	assert_true(player.body.hidden_at(10.0))
	var charge: float = shroud.charge
	EventBus.shot_fired.emit(player, player.global_position, Vector3.FORWARD)
	await wait_frames(2)
	assert_false(shroud.is_hidden(), "firing shows where you are")
	assert_almost_eq(player.body.cloak, 0.0, 0.01)
	assert_lt(shroud.charge, charge - shroud.cfg.shot_cost * 0.9)
	await _real_wait(shroud.cfg.shot_reveal_time + 0.2)
	assert_true(shroud.is_hidden(), "and it closes again")
	player.augments.use_selected()
	await _real_wait(shroud.data.recover_time + 0.2)
	assert_almost_eq(player.body.cloak, 0.0, 0.01, "dropped")


func test_two_hands_two_parts() -> void:
	var whip: Whip = await _equip([&"mw7_monofilament_whip", &"bw6_fan_shield", &"mw7_monofilament_whip"]) as Whip
	var shield: FanShield = player.augments.find(&"bw6_fan_shield") as FanShield
	await _deploy(whip)
	await _deploy(shield)
	assert_true(whip.is_running(), "the whip in the right hand")
	assert_true(shield.is_running(), "the shield on the left arm")
	assert_true(player.weapon().stowed)
	player.augments.select(whip.slot)
	player.augments.use_selected()
	await _real_wait(whip.data.recover_time + whip.data.cooldown_time + 0.2)
	assert_true(player.weapon().stowed, "the shield still has the left hand")
	player.augments.select(shield.slot)
	player.augments.use_selected()
	await _real_wait(shield.data.recover_time + shield.data.cooldown_time + 0.5)
	assert_false(player.weapon().stowed, "both hands free: the gun comes back")
