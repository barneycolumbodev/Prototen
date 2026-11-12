extends GutTest
## The operative model, part hardware on sockets, and the body-status screen.


func test_operative_model_has_the_shared_skeleton() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	add_child_autofree(a)
	await wait_frames(1)
	assert_not_null(a.skeleton)
	for bone: String in ["hips", "chest", "head", "forearm.L", "hand.R", "shin.L"]:
		assert_gt(a.skeleton.find_bone(bone), -1, "bone %s (same rig as the triad)" % bone)


func _tris(mi: MeshInstance3D) -> int:
	var tris: int = 0
	for s: int in mi.mesh.get_surface_count():
		var indices: PackedInt32Array = mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX]
		tris += indices.size() / 3
	return tris


func test_operative_is_suit_helmet_and_head_in_budget() -> void:
	var model: Node = (load("res://assets/characters/operative/operative.gltf") as PackedScene).instantiate()
	var meshes: Array[Node] = model.find_children("*", "MeshInstance3D", true, false)
	var names: PackedStringArray = PackedStringArray()
	for n: Node in meshes:
		names.append(n.name)
	assert_eq(meshes.size(), 3, "suit, helmet, bare head: %s" % ", ".join(names))
	var total: int = 0
	for part: String in ["operative", "operative_helmet", "operative_head"]:
		var mi: MeshInstance3D = model.find_child(part, true, false) as MeshInstance3D
		assert_not_null(mi, part)
		if mi == null:
			continue
		assert_not_null(mi.skin, "%s skinned to the shared skeleton" % part)
		var mat: StandardMaterial3D = mi.mesh.surface_get_material(0) as StandardMaterial3D
		assert_not_null(mat, part)
		assert_not_null(mat.albedo_texture, "%s baked base colour" % part)
		assert_not_null(mat.normal_texture, "%s baked normal map" % part)
		assert_not_null(mat.roughness_texture, "%s ORM" % part)
		total += _tris(mi)
	var suit: MeshInstance3D = model.find_child("operative", true, false) as MeshInstance3D
	var helm: MeshInstance3D = model.find_child("operative_helmet", true, false) as MeshInstance3D
	if suit and helm:
		var sm: StandardMaterial3D = suit.mesh.surface_get_material(0) as StandardMaterial3D
		assert_not_null(sm.emission_texture, "seam lights")
		assert_eq(helm.mesh.surface_get_material(0).resource_name, sm.resource_name, "helmet shares the suit atlas")
	# Shown at once: suit + helmet or suit + head.
	assert_between(total, 20000, 48000, "player body triangles (all three meshes)")
	model.free()


func test_helmet_toggle_swaps_helmet_for_head() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	add_child_autofree(a)
	await wait_frames(1)
	var helm: MeshInstance3D = a.part_mesh("operative_helmet")
	var head: MeshInstance3D = a.part_mesh("operative_head")
	assert_not_null(helm)
	assert_not_null(head)
	if helm == null or head == null:
		return
	assert_true(helm.visible and not head.visible, "helmet on by default")
	a.helmet_on = false
	assert_true(head.visible and not helm.visible, "helmet off shows the face")
	a.helmet_on = true
	assert_true(helm.visible and not head.visible)


func test_parts_mount_their_hardware() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	var lo: BodyLoadout = BodyLoadout.new()
	lo.parts = [load("res://data/body/parts/rx9_reflex_overclock.tres"), load("res://data/body/parts/hs5_heat_sinks.tres")]
	a.loadout = lo
	add_child_autofree(a)
	await wait_frames(1)
	var expected: int = 0
	for p: PartData in lo.parts:
		for v: PartVisual in p.visuals:
			if v.scene and v.model_space:
				# A modelled part: one piece per bone it rides on.
				var root: Node = v.scene.instantiate()
				expected += root.find_children("*", "MeshInstance3D", true, false).size()
				root.free()
			else:
				expected += 1
	assert_eq(a.mounted.size(), expected, "every visual mounted")
	lo.parts = [load("res://data/body/parts/cs1_carapace.tres")]
	a.rebuild()
	await wait_frames(1)
	assert_eq(a.mounted.size(), 0, "rebuilt with the new loadout")


func test_status_text_lists_parts_and_totals() -> void:
	var frame: PlayerBodyConfig = load("res://data/player/body_default.tres")
	var lo: BodyLoadout = load("res://data/body/loadout_default.tres")
	var b: BodyModel = BodyModel.new(frame, lo)
	var t: String = BodyStatus.describe(b)
	assert_string_contains(t, "RX-9 Reflex Overclock")
	assert_string_contains(t, "ACTIVE (LB, D-LEFT)")
	assert_string_contains(t, "%.0f kg" % b.mass_kg)
