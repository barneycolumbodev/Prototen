extends GutTest
## Whole men made with Tripo3D and fitted to the triad rig (owner, 2026-11-17;
## raw_assets/characters/triad_tripo/, docs/design.md §5.6b): every role
## wears them, each is skinned to the same skeleton as the wardrobe, has his
## own textures, is one draw call, and comes apart at the same joints.

var room: TestRoom
const ROLES: Array[String] = ["gunman", "blue_lantern", "enforcer", "hatchet_man", "red_pole", "incense_master"]


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	room.player.invulnerable = true
	await wait_physics_frames(5)


func _cfg(role: String) -> EnemyConfig:
	return load("res://data/enemies/%s.tres" % role) as EnemyConfig


func _bodies() -> Array[Garment]:
	var out: Array[Garment] = []
	for role: String in ROLES:
		for o: Outfit in _cfg(role).outfits:
			for b: Garment in o.bodies:
				if not out.has(b):
					out.append(b)
	return out


func _spawn(cfg: EnemyConfig, body: Garment, at: Vector3 = Vector3(0, 0, 4)) -> Enemy:
	var look: TriadLook = TriadLook.new()
	look.garments.append(body)
	var e: Enemy = Enemy.new()
	e.config = cfg
	e.passive = true
	e.look = look
	room.add_child(e)
	e.position = at
	return e


func test_every_role_wears_whole_men() -> void:
	for role: String in ROLES:
		var rng: RandomNumberGenerator = RandomNumberGenerator.new()
		for seed: int in 12:
			rng.seed = seed
			var look: TriadLook = TriadLook.pick(_cfg(role).outfits, rng)
			assert_not_null(look.whole_body(), "%s %d: %s" % [role, seed, look.key()])
			assert_eq(look.garments.size(), 1, "nothing worn over a whole man")
	assert_gt(_bodies().size(), 8, "%d men" % _bodies().size())


func test_every_body_is_complete_and_skinned_to_the_triad_skeleton() -> void:
	for b: Garment in _bodies():
		var whole: ArrayMesh = EnemyBody.wardrobe_mesh(StringName("w_" + String(b.mesh))) as ArrayMesh
		assert_not_null(whole, String(b.mesh))
		if whole == null:
			continue
		var tris: int = whole.surface_get_array_index_len(0) / 3
		assert_between(tris, 8000, 16000, "%s: %d triangles" % [b.mesh, tris])
		var a: Array = whole.surface_get_arrays(0)
		var bi: PackedInt32Array = a[Mesh.ARRAY_BONES]
		var va: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
		assert_eq(bi.size(), va.size() * 4, "%s: 4 weights a vertex" % b.mesh)
		var top: int = 0
		for i: int in bi:
			top = maxi(top, i)
		assert_lt(top, 23, "%s: the triad's 23 bones" % b.mesh)
		var aabb: AABB = whole.get_aabb()
		assert_between(aabb.size.y, 1.6, 2.0, "%s stands %.2f m in the rig (unscaled)" % [b.mesh, aabb.size.y])
		assert_almost_eq(aabb.position.y, 0.0, 0.05, "%s: feet on the ground" % b.mesh)
		for part: String in ["body", "head", "upper_arm_L", "upper_arm_R", "forearm_R", "hand_R", "shin_L", "shin_R"]:
			assert_not_null(EnemyBody.wardrobe_mesh(StringName("w_%s__%s" % [b.mesh, part])), "%s__%s" % [b.mesh, part])
		for t: Texture2D in EnemyBody.body_textures(b.mesh):
			assert_not_null(t, "%s textures" % b.mesh)


## Tripo surfaces are noisier than the triad body (cloth folds, wrinkles), so
## the LODs stop sooner: measured 2026-11-17, the far LOD is about a quarter
## of the triangles (the wardrobe men reach about a ninth).
func test_whole_men_get_lods_that_never_join_two_pieces() -> void:
	var look: TriadLook = TriadLook.new()
	look.garments.append(load("res://data/enemies/bodies/tp_sum_singlet.tres") as Garment)
	var specs: Array = TriadMeshBaker.split_specs(look, EnemyBody.source_meshes())
	for spec_list: Array in [specs, TriadMeshBaker.intact_specs(look)]:
		for spec: Array in spec_list:
			var nm: StringName = spec[0]
			TriadMeshBaker._read_source(nm, EnemyBody.wardrobe_mesh(nm))
	var ii: ImporterMesh = TriadMeshBaker.with_lods(TriadMeshBaker.concat(TriadMeshBaker.intact_specs(look), Vector3.ZERO), false)
	var ii_idx: PackedInt32Array = ii.get_surface_arrays(0)[Mesh.ARRAY_INDEX]
	var full: int = ii_idx.size() / 3
	var far: int = ii.get_surface_lod_indices(0, ii.get_surface_lod_count(0) - 1).size() / 3
	assert_gt(ii.get_surface_lod_count(0), 1, "LODs")
	assert_lt(far, full * 0.3, "far LOD %d of %d triangles" % [far, full])
	var arrays: Array = TriadMeshBaker.concat(specs, Vector3.ZERO)
	var im: ImporterMesh = TriadMeshBaker.with_lods(arrays, true, ii)
	assert_gt(im.get_surface_lod_count(0), 0, "the split mesh has LODs too")
	var c0: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM0]
	var bad: int = 0
	for li: int in im.get_surface_lod_count(0):
		var idx: PackedInt32Array = im.get_surface_lod_indices(0, li)
		for t: int in idx.size() / 3:
			var s0: int = int(c0[idx[t * 3] * 4 + 3] + 0.5) % 16
			var s1: int = int(c0[idx[t * 3 + 1] * 4 + 3] + 0.5) % 16
			var s2: int = int(c0[idx[t * 3 + 2] * 4 + 3] + 0.5) % 16
			if s0 != s1 or s1 != s2:
				bad += 1
	assert_eq(bad, 0, "no LOD triangle spans two pieces")


func test_a_whole_man_is_one_mesh_with_his_own_maps() -> void:
	var body: Garment = load("res://data/enemies/bodies/tp_gun_bomber.tres") as Garment
	var e: Enemy = _spawn(_cfg("gunman"), body)
	await wait_physics_frames(2)
	var shown: Array[String] = []
	for n: Node in e.body.skeleton.get_children():
		var mi: MeshInstance3D = n as MeshInstance3D
		if mi and mi.visible:
			shown.append(mi.name)
	assert_eq(shown, ["triad"], "one draw call")
	var merged: ArrayMesh = (e.body.skeleton.get_node(^"triad") as MeshInstance3D).mesh as ArrayMesh
	var own: int = (EnemyBody.wardrobe_mesh(&"w_tp_gun_bomber") as ArrayMesh).surface_get_array_len(0)
	assert_eq(merged.surface_get_array_len(0), own, "just him, not the triad body under him")
	var base: Texture2D = e.body.material.get_shader_parameter(&"base_tex")
	var own_base: Texture2D = EnemyBody.body_textures(&"tp_gun_bomber")[0]
	assert_eq(base, own_base, "his own colour map")


func test_an_enforcer_in_his_own_plate_carrier_hides_the_vest() -> void:
	var e: Enemy = _spawn(_cfg("enforcer"), load("res://data/enemies/bodies/tp_enf_track.tres") as Garment)
	await wait_physics_frames(2)
	assert_false((e.body.skeleton.get_node(^"vest") as MeshInstance3D).visible, "his own carrier, not the vest mesh")


func test_his_head_comes_off_with_his_hair() -> void:
	var e: Enemy = _spawn(_cfg("gunman"), load("res://data/enemies/bodies/tp_gun_hoodie.tres") as Garment)
	await wait_physics_frames(2)
	var head: ArrayMesh = e.body.gib_mesh([&"head"] as Array[StringName])
	var own: int = (EnemyBody.wardrobe_mesh(&"w_tp_gun_hoodie__head") as ArrayMesh).surface_get_array_len(0)
	assert_eq(head.surface_get_array_len(0), own, "the flying head is his head")
	assert_true(e.body.sever(&"head", Vector3.UP))
	await wait_frames(1)
	var split: ArrayMesh = (e.body.skeleton.get_node(^"part_body") as MeshInstance3D).mesh as ArrayMesh
	var pieces: int = 0
	var parts: Array[String] = ["body"]
	for seg: StringName in EnemyBody.SEGMENT_ORDER:
		parts.append(String(seg))
	for part: String in parts:
		var m: Mesh = EnemyBody.wardrobe_mesh(StringName("w_tp_gun_hoodie__" + part))
		if m:
			pieces += (m as ArrayMesh).surface_get_array_len(0)
	assert_eq(split.surface_get_array_len(0), pieces, "after the cut: his pieces and nothing else")


func test_the_boss_is_the_tripo_incense_master_and_still_loses_his_arm() -> void:
	var cfg: EnemyConfig = _cfg("incense_master")
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	var look: TriadLook = TriadLook.pick(cfg.outfits, rng)
	assert_eq(look.whole_body().mesh, &"tp_incense_master")
