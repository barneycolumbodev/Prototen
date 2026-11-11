extends GutTest
## Dismemberment and gibbing (docs/design.md §5.5, GoreConfig; owner,
## 2026-11-11: Soldier of Fortune style, by ballistic impact and location).

var room: TestRoom
var player: Player
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var rail: WeaponData = preload("res://data/weapons/rail_carbine.tres")
var m14: WeaponData = preload("res://data/weapons/m14p.tres")
var mg42: WeaponData = preload("res://data/weapons/mg42.tres")
var saiga: WeaponData = preload("res://data/weapons/saiga12k.tres")
var gauss: WeaponData = preload("res://data/weapons/gx4_slug.tres")
var _gore: int


func before_each() -> void:
	_gore = Settings.gore_level
	Settings.gore_level = Gore.Level.MAXIMUM
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	await wait_physics_frames(20)


func after_each() -> void:
	Settings.gore_level = _gore
	Gore.clear()


func _shoot(w: WeaponData, at: Vector3, from: Vector3 = Vector3(0, 1.6, 9.0)) -> void:
	Ballistics.fire(w, from, (at - from).normalized(), player)
	await wait_physics_frames(4)


## A whole shell: every pellet in its pattern, one volley (as PlayerWeapon fires it).
func _shell(w: WeaponData, at: Vector3, from: Vector3) -> void:
	var dir: Vector3 = (at - from).normalized()
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 7
	var volley: int = 0
	for i: int in w.pellets:
		var d: Vector3 = Ballistics.pattern_dir(dir, w.pattern_deg, i, w.pellets, 0.0, rng)
		var id: int = Ballistics.fire(w, from, d, player, Vector3.INF, volley)
		if volley == 0:
			volley = id
	await wait_physics_frames(4)


func _target(i: int = 0) -> Enemy:
	return room.shooting_range.targets[i]


## A point on the line between a cut and the far end of its segment, `t` of
## the way (0 = at the cut).
func _along(e: Enemy, seg: StringName, t: float) -> Vector3:
	var sp: Array = EnemyBody.SEGMENTS[seg]
	var end_bone: StringName = sp[4]
	return e.body.cut_point(seg).lerp(e.body.bone_position(end_bone), t)


func test_the_split_body_is_one_mesh() -> void:
	var e: Enemy = _target()
	var expected: int = 0
	for n: StringName in [&"part_body"] + EnemyBody.SEGMENT_ORDER.map(func(s: StringName) -> StringName: return EnemyBody.SEGMENTS[s][0]):
		var mi: MeshInstance3D = e.body.skeleton.get_node(NodePath(String(n))) as MeshInstance3D
		expected += (mi.mesh as ArrayMesh).surface_get_array_len(0)
	e.body.sever(&"hand_L", Vector3.UP)
	await wait_frames(1)
	var shown: Array[String] = []
	for n: Node in e.body.skeleton.get_children():
		var mi: MeshInstance3D = n as MeshInstance3D
		if mi and mi.visible:
			shown.append(mi.name)
	assert_eq(shown, ["part_body"] if not e.config.plate_carrier else ["part_body", "vest"], "one draw call for the body: %s" % ", ".join(shown))
	var body_mi: MeshInstance3D = e.body.skeleton.get_node(^"part_body") as MeshInstance3D
	var merged: ArrayMesh = body_mi.mesh as ArrayMesh
	assert_eq(merged.get_surface_count(), 1)
	assert_eq(merged.surface_get_array_len(0), expected, "every piece is in it")
	var mat: ShaderMaterial = e.body.material
	var mask: int = mat.get_shader_parameter(&"severed_mask")
	assert_eq(mask, 1 << EnemyBody.SEGMENT_ORDER.find(&"hand_L"), "the shader hides the hand")


func test_a_cut_takes_everything_below_it() -> void:
	var e: Enemy = _target()
	assert_eq(e.body.attached(&"upper_arm_R"), [&"upper_arm_R", &"forearm_R", &"hand_R"] as Array[StringName])
	e.body.sever(&"upper_arm_R", Vector3(1, 1, 0))
	for seg: StringName in [&"upper_arm_R", &"forearm_R", &"hand_R"]:
		assert_true(e.body.is_severed(seg), "%s went with the arm" % seg)
	assert_eq(e.body.hitboxes[&"r_hand"].collision_layer, 0, "its zones are gone")
	assert_false(e.body.is_severed(&"forearm_L"))
	assert_null(e.body.gun, "the gun hand went: the gun dropped")


func test_the_cut_nearest_the_hit_is_the_one_that_goes() -> void:
	var cfg: GoreConfig = Gore.config
	var e: Enemy = _target()
	var cuts: Dictionary[StringName, Vector3] = e.body.cut_points()
	var none: Dictionary[StringName, bool] = {}
	var near_hip: Array = Dismemberment.nearest_cut(cfg, &"l_thigh", cuts[&"thigh_L"] + Vector3.UP * 0.03, cuts, none)
	var near_hip_seg: StringName = near_hip[0]
	assert_eq(near_hip_seg, &"thigh_L", "above the knee: the leg at the thigh")
	var near_knee: Array = Dismemberment.nearest_cut(cfg, &"l_shin", cuts[&"shin_L"], cuts, none)
	var near_knee_seg: StringName = near_knee[0]
	assert_eq(near_knee_seg, &"shin_L", "below the knee: the shin")
	var elbow: Array = Dismemberment.nearest_cut(cfg, &"l_forearm", _along(e, &"forearm_L", 0.1), cuts, none)
	var elbow_seg: StringName = elbow[0]
	assert_eq(elbow_seg, &"forearm_L")
	var wrist: Array = Dismemberment.nearest_cut(cfg, &"l_hand", cuts[&"hand_L"], cuts, none)
	var wrist_seg: StringName = wrist[0]
	assert_eq(wrist_seg, &"hand_L")
	# A limb's cut 30 cm from the hit is out of reach.
	var far_cuts: Dictionary[StringName, Vector3] = {&"upper_arm_L": Vector3(0.3, 0, 0)}
	var mid_chest: Array = Dismemberment.nearest_cut(cfg, &"chest", Vector3.ZERO, far_cuts, none)
	var mid_chest_seg: StringName = mid_chest[0]
	assert_eq(mid_chest_seg, &"", "the middle of the chest has no limb in reach")


func test_a_rail_round_through_the_upper_arm_takes_the_arm() -> void:
	var e: Enemy = _target(2)
	var at: Vector3 = _along(e, &"upper_arm_L", 0.15)
	await _shoot(rail, at, at + Vector3(-0.15, 0.05, 6.0))
	assert_true(e.body.is_severed(&"upper_arm_L"), "off at the upper arm")
	assert_true(e.body.is_severed(&"hand_L"), "the forearm and hand with it")
	assert_false(e.body.is_severed(&"forearm_R"))


func test_a_rail_round_through_the_thigh_takes_the_leg_and_he_crawls() -> void:
	var e: Enemy = _target(2)
	var at: Vector3 = _along(e, &"thigh_R", 0.1)
	await _shoot(rail, at, at + Vector3(0.1, 0.1, 6.0))
	assert_true(e.body.is_severed(&"thigh_R"), "off above the knee")
	assert_true(e.body.is_severed(&"shin_R"), "the shin with it")
	if e.alive:
		assert_eq(e.state, Enemy.State.CRAWL, "he crawls")


func test_a_pistol_round_takes_nothing_off() -> void:
	for zone: StringName in [&"l_hand", &"l_forearm", &"head"]:
		var e: Enemy = _target(1)
		await _shoot(pistol, e.body.hitboxes[zone].global_position)
		assert_true(e.body.severed.is_empty(), "one 5.7 mm round to the %s severs nothing" % zone)


func test_buckshot_point_blank_takes_the_forearm_off() -> void:
	var e: Enemy = _target(1)
	var at: Vector3 = _along(e, &"forearm_R", 0.3)
	await _shell(saiga, at, at + Vector3(0, 0.05, 0.8))
	assert_true(e.body.is_severed(&"forearm_R") or e.body.is_severed(&"hand_R") or e.body.is_severed(&"upper_arm_R"),
			"nine pellets together take the arm off at the forearm")


func test_buckshot_at_range_does_not() -> void:
	var e: Enemy = _target(1)
	var at: Vector3 = _along(e, &"forearm_R", 0.3)
	await _shell(saiga, at, at + Vector3(0, 0.3, 9.0))
	assert_true(e.body.severed.is_empty(), "spread out at 9 m, the pellets don't")


func test_sustained_fire_saws_a_limb_off() -> void:
	var e: Enemy = _target(1)
	e.die(null, &"chest")
	await wait_physics_frames(2)
	var shots: int = 0
	while not e.body.is_severed(&"shin_L") and not e.body.is_severed(&"thigh_L") and shots < 12:
		var at: Vector3 = _along(e, &"shin_L", 0.15)
		await _shoot(m14, at, at + Vector3(0, 2.0, 5.0))
		shots += 1
	assert_true(e.body.is_severed(&"shin_L") or e.body.is_severed(&"thigh_L"), "the leg comes off after %d rifle rounds" % shots)
	assert_gt(shots, 1, "but not from the first")


func test_the_gauss_slug_bursts_a_man() -> void:
	var e: Enemy = _target(0)
	var before: int = Gore.bursts
	await _shoot(gauss, e.body.chest_position())
	assert_true(e.dead)
	assert_true(e.body.gibbed, "blown apart")
	assert_eq(Gore.bursts, before + 1)
	for seg: StringName in [&"head", &"upper_arm_L", &"upper_arm_R", &"thigh_L", &"thigh_R"]:
		assert_true(e.body.is_severed(seg), "%s flew off" % seg)
	assert_gt(Gore.gib_count(), 8, "ribs, organs, meat and limbs in the air")
	assert_lte(Gore.gib_count(), Gore.MAX_GIBS)


func test_a_corpse_shot_to_pieces_bursts() -> void:
	var e: Enemy = _target(0)
	e.die(null, &"chest")
	await wait_physics_frames(2)
	var shots: int = 0
	while not e.body.gibbed and shots < 30:
		await _shoot(mg42, e.body.chest_position() + Vector3(0, 0.05, 0), Vector3(0, 2.5, 6.0))
		shots += 1
	assert_true(e.body.gibbed, "a body under the MG42 comes apart (%d rounds)" % shots)


func test_a_blast_tears_by_distance() -> void:
	var near: Enemy = _target(0)
	var at: Vector3 = near.body.chest_position() + Vector3(0, -0.3, 0.3)
	Explosion.detonate(room, at, 6.0, 400.0, player, gauss)
	await wait_physics_frames(2)
	assert_true(near.body.gibbed, "at the blast: burst")
	var far_away: int = 0
	for e: Enemy in room.shooting_range.targets:
		if e != null and e != near and e.body.cut_points().size() == EnemyBody.SEGMENT_ORDER.size():
			far_away += 1
	assert_gt(far_away, 0, "men far from it keep their limbs")


func test_bursts_stay_under_the_gib_cap() -> void:
	for i: int in 3:
		_target(i).burst(Vector3.UP)
	await wait_physics_frames(2)
	assert_lte(Gore.gib_count(), Gore.MAX_GIBS)


func test_gore_off_takes_nothing_apart() -> void:
	Settings.gore_level = Gore.Level.OFF
	var e: Enemy = _target(0)
	var before: int = Gore.bursts
	await _shoot(gauss, e.body.chest_position())
	assert_false(e.body.gibbed)
	assert_true(e.body.severed.is_empty())
	assert_eq(Gore.bursts, before)
	assert_eq(Gore.gib_count(), 0)


func test_standard_gore_keeps_bodies_whole() -> void:
	Settings.gore_level = Gore.Level.STANDARD
	var e: Enemy = _target(0)
	await _shoot(gauss, e.body.chest_position())
	assert_false(e.body.gibbed)
	assert_true(e.body.severed.is_empty())
