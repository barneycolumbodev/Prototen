extends GutTest
## TriadMeshBaker (2026-11-12): a man's merged meshes built off the main
## thread, with LODs, the same vertices as the synchronous merge, and no LOD
## triangle joining two pieces that can be cut apart.

var gunman: EnemyConfig = load("res://data/enemies/gunman.tres") as EnemyConfig


func _look(seed: int) -> TriadLook:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = seed
	return TriadLook.pick(gunman.outfits, rng)


func _lod_count(m: ArrayMesh) -> int:
	var surf: Dictionary = RenderingServer.mesh_get_surface(m.get_rid(), 0)
	var lods: Array = surf.get("lods", [])
	return lods.size()


func test_baked_intact_matches_the_merge_and_has_lods() -> void:
	var look: TriadLook = _look(11)
	TriadMeshBaker.prefetch(look, EnemyBody.source_meshes())
	TriadMeshBaker.finish_all()
	var baked: ArrayMesh = TriadMeshBaker.take(look, "I")
	assert_not_null(baked, "built in the background")
	var srcs: Array[Array] = []
	for spec: Array in TriadMeshBaker.intact_specs(look):
		var nm: StringName = spec[0]
		var m: Mesh = EnemyBody.source_meshes().get(nm, EnemyBody.wardrobe_mesh(nm))
		var sl: int = spec[2]
		srcs.append([nm, m, 0, sl])
	var merged: ArrayMesh = EnemyBody._merge(srcs)
	assert_eq(baked.surface_get_array_len(0), merged.surface_get_array_len(0), "same vertices")
	assert_eq(baked.surface_get_array_index_len(0), merged.surface_get_array_index_len(0), "same triangles")
	assert_eq(baked.surface_get_format(0) & Mesh.ARRAY_FORMAT_CUSTOM_BASE, merged.surface_get_format(0) & Mesh.ARRAY_FORMAT_CUSTOM_BASE)
	assert_gt(_lod_count(baked), 2, "LODs for distance")
	assert_eq(_lod_count(merged), 0, "the old merge had none")
	# Rest positions and codes as EnemyBody.prepared writes them.
	var a: Array = baked.surface_get_arrays(0)
	var b: Array = merged.surface_get_arrays(0)
	var ca: PackedFloat32Array = a[Mesh.ARRAY_CUSTOM0]
	var cb: PackedFloat32Array = b[Mesh.ARRAY_CUSTOM0]
	var worst: float = 0.0
	for i: int in mini(ca.size(), cb.size()):
		worst = maxf(worst, absf(ca[i] - cb[i]))
	assert_lt(worst, 0.002, "CUSTOM0 matches (worst %.4f)" % worst)


func test_split_lods_never_join_two_pieces() -> void:
	var look: TriadLook = _look(23)
	var specs: Array = TriadMeshBaker.split_specs(look, EnemyBody.source_meshes())
	for spec: Array in specs:
		var nm: StringName = spec[0]
		var src: Mesh = EnemyBody.source_meshes().get(nm, EnemyBody.wardrobe_mesh(nm))
		TriadMeshBaker._read_source(nm, src)
	for spec: Array in TriadMeshBaker.intact_specs(look):
		var nm: StringName = spec[0]
		var src: Mesh = EnemyBody.source_meshes().get(nm, EnemyBody.wardrobe_mesh(nm))
		TriadMeshBaker._read_source(nm, src)
	var ii: ImporterMesh = TriadMeshBaker.with_lods(TriadMeshBaker.concat(TriadMeshBaker.intact_specs(look), Vector3.ZERO), false)
	var arrays: Array = TriadMeshBaker.concat(specs, Vector3.ZERO)
	var im: ImporterMesh = TriadMeshBaker.with_lods(arrays, true, ii)
	assert_gt(im.get_surface_lod_count(0), 2, "the split mesh has LODs too")
	var c0: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM0]
	var bad: int = 0
	var tris: int = 0
	for li: int in im.get_surface_lod_count(0):
		var idx: PackedInt32Array = im.get_surface_lod_indices(0, li)
		for t: int in idx.size() / 3:
			var s0: int = int(c0[idx[t * 3] * 4 + 3] + 0.5) % 16
			var s1: int = int(c0[idx[t * 3 + 1] * 4 + 3] + 0.5) % 16
			var s2: int = int(c0[idx[t * 3 + 2] * 4 + 3] + 0.5) % 16
			tris += 1
			if s0 != s1 or s1 != s2:
				bad += 1
	assert_eq(bad, 0, "%d of %d LOD triangles span two segments" % [bad, tris])
	var full_idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var full: int = full_idx.size() / 3
	var last: int = im.get_surface_lod_indices(0, im.get_surface_lod_count(0) - 1).size() / 3
	assert_lt(last, full / 4, "the far LOD is a fraction of %d triangles (%d)" % [full, last])
	# Error sizes follow the intact man's: at the same share of triangles, about the same size.
	for li: int in im.get_surface_lod_count(0):
		var r: float = im.get_surface_lod_indices(0, li).size() / 3.0 / full
		var sz: float = im.get_surface_lod_size(0, li)
		assert_lt(sz, 2.0, "LOD %d (%.2f of the triangles) error %.3f is sane" % [li, r, sz])
	gut.p("split LODs: %s" % ", ".join(PackedStringArray(range(im.get_surface_lod_count(0)).map(
			func(li: int) -> String: return "%.3f:%d" % [im.get_surface_lod_size(0, li), im.get_surface_lod_indices(0, li).size() / 3]))))
	gut.p("intact LODs: %s" % ", ".join(PackedStringArray(range(ii.get_surface_lod_count(0)).map(
			func(li: int) -> String: return "%.3f:%d" % [ii.get_surface_lod_size(0, li), ii.get_surface_lod_indices(0, li).size() / 3]))))


func test_baked_gib_matches_the_merge() -> void:
	var look: TriadLook = _look(31)
	TriadMeshBaker.prefetch(look, EnemyBody.source_meshes())
	TriadMeshBaker.finish_all()
	var group: Array[StringName] = EnemyBody.intact_group(&"upper_arm_R")
	var want: Array[StringName] = [&"upper_arm_R", &"forearm_R", &"hand_R"]
	assert_eq(group, want)
	var centre: Array[Vector3] = []
	var baked: ArrayMesh = TriadMeshBaker.take(look, "G|" + ",".join(PackedStringArray(group)), centre)
	assert_not_null(baked)
	assert_eq(centre.size(), 1)
	var expected: int = 0
	for spec: Array in TriadMeshBaker.gib_specs(look, group, EnemyBody.source_meshes()):
		var nm: StringName = spec[0]
		var m: Mesh = EnemyBody.source_meshes().get(nm, EnemyBody.wardrobe_mesh(nm))
		var am: ArrayMesh = m as ArrayMesh
		expected += am.surface_get_array_len(0)
	assert_eq(baked.surface_get_array_len(0), expected, "arm, forearm, hand and their sleeves")
	assert_lt(baked.get_aabb().get_center().length(), 0.05, "stored centred on its middle")


func test_spawner_prefetches_and_men_end_up_with_lods() -> void:
	var room: Node3D = Node3D.new()
	add_child_autofree(room)
	var floor_body: StaticBody3D = StaticBody3D.new()
	floor_body.collision_layer = Ballistics.LAYER_WORLD
	var cs: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(60, 1, 60)
	cs.shape = box
	cs.position = Vector3(0, -0.5, 0)
	floor_body.add_child(cs)
	room.add_child(floor_body)
	var men: Array[Enemy] = []
	for i: int in 3:
		var e: Enemy = Enemy.new()
		e.config = gunman
		e.passive = true
		e.look = _look(100 + i)
		TriadMeshBaker.prefetch(e.look, EnemyBody.source_meshes())
		men.append(e)
	TriadMeshBaker.finish_all()
	for i: int in men.size():
		room.add_child(men[i])
		men[i].position = Vector3(i * 2.0, 0, 0)
	await wait_physics_frames(3)
	for e: Enemy in men:
		var mi: MeshInstance3D = e.body.skeleton.get_node(^"triad") as MeshInstance3D
		assert_gt(_lod_count(mi.mesh as ArrayMesh), 2, "%s spawned with LODs" % e.body.look.key())
	# One without a prefetch: shown at once (merged here), LODs swapped in when they arrive.
	var late: Enemy = Enemy.new()
	late.config = gunman
	late.passive = true
	late.look = _look(777)
	room.add_child(late)
	late.position = Vector3(-3, 0, 0)
	var first: ArrayMesh = (late.body.skeleton.get_node(^"triad") as MeshInstance3D).mesh as ArrayMesh
	assert_not_null(first)
	TriadMeshBaker.finish_all()
	await wait_seconds(0.2)
	var later: ArrayMesh = (late.body.skeleton.get_node(^"triad") as MeshInstance3D).mesh as ArrayMesh
	assert_gt(_lod_count(later), 2, "swapped for the baked one")
	assert_eq(later.surface_get_array_len(0), first.surface_get_array_len(0))
