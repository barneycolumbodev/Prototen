extends GutTest
## Modelled passive hardware (docs/design.md §3.6): every mesh names a bone of
## the operative, stays in budget, uses its baked textures, and mounts on
## the body where it was modelled.

const PARTS: Array[String] = [
	"ct7_trauma_plating", "hs5_heat_sinks", "nl3_cortical_uplink", "kd2_kinetic_dampers",
	"em2_myofibrils", "tl3_titanium_skeleton", "sa2_synaptic_accelerator", "dl1_dorsal_load_frame",
	"hm5_hydraulic_myomer", "tn9_tungsten_cores", "fc1_fire_control", "vs1_vestibular_stabilizer",
	"pc3_power_cell", "sp6_sprint_pistons", "ks2_striker_rams", "rp2_ram_plating",
	"ob5_ocular_ballistics", "mr1_mesh_relay", "cm1_chromatophore_mesh", "dg3_dexterity_grafts",
]


func _tris(mi: MeshInstance3D) -> int:
	var t: int = 0
	for s: int in mi.mesh.get_surface_count():
		var indices: PackedInt32Array = mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX]
		t += indices.size() / 3
	return t


func test_meshes_name_bones_and_stay_in_budget() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	add_child_autofree(a)
	await wait_process_frames(1)
	for id: String in PARTS:
		var root: Node = (load("res://assets/augments/passives/%s/%s.gltf" % [id, id]) as PackedScene).instantiate()
		var total: int = 0
		var meshes: Array[Node] = root.find_children("*", "MeshInstance3D", true, false)
		assert_gt(meshes.size(), 0, id)
		for n: Node in meshes:
			var mi: MeshInstance3D = n as MeshInstance3D
			var bone: StringName = BodyAppearance.bone_from_node_name(mi.name)
			assert_gt(a.skeleton.find_bone(bone), -1, "%s: %s -> bone %s" % [id, mi.name, bone])
			var mat: StandardMaterial3D = mi.mesh.surface_get_material(0) as StandardMaterial3D
			assert_not_null(mat, id)
			if mat:
				assert_not_null(mat.albedo_texture, "%s baked base colour" % id)
				assert_not_null(mat.normal_texture, "%s baked normal map" % id)
			total += _tris(mi)
		assert_between(total, 300, 6000, "%s triangles" % id)
		root.free()
	for id: String in PARTS:
		for ch: String in ["basecolor", "normal", "orm", "emission"]:
			var cfg: ConfigFile = ConfigFile.new()
			assert_eq(cfg.load("res://assets/augments/passives/%s/textures/%s_%s.png.import" % [id, id, ch]), OK)
			var mode: int = cfg.get_value("params", "compress/mode", -1)
			assert_eq(mode, 2, "%s %s VRAM compressed" % [id, ch])


func test_plating_mounts_on_the_chest_where_it_was_modelled() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	var lo: BodyLoadout = BodyLoadout.new()
	lo.parts = [load("res://data/body/parts/ct7_trauma_plating.tres") as PartData]
	a.loadout = lo
	add_child_autofree(a)
	await wait_process_frames(2)
	assert_gt(a.mounted.size(), 2)
	var chest: Vector3 = a.skeleton.get_bone_global_pose(a.skeleton.find_bone(&"chest")).origin
	for n: Node3D in a.mounted:
		var mi: MeshInstance3D = n as MeshInstance3D
		var c: Vector3 = a.skeleton.global_transform.affine_inverse() * mi.global_transform * mi.get_aabb().get_center()
		assert_lt(c.distance_to(chest), 0.45, "%s sits on the upper body (%s)" % [mi.name, c])


func test_part_data_uses_the_modelled_scene() -> void:
	for id: String in PARTS:
		var p: PartData = load("res://data/body/parts/%s.tres" % id) as PartData
		assert_not_null(p, id)
		var scenes: int = 0
		for v: PartVisual in p.visuals:
			if v.scene and v.model_space:
				scenes += 1
			assert_eq(v.shape, PartVisual.Shape.NONE, "%s: no placeholder shapes once modelled" % id)
		assert_eq(scenes, 1, "%s mounts its glTF" % id)


func test_every_preset_part_with_hardware_is_modelled() -> void:
	for lo: BodyLoadout in LoadoutStore.presets():
		for p: PartData in lo.parts:
			for v: PartVisual in p.visuals:
				assert_true(v.scene != null and v.model_space, "%s (%s): finished hardware, not a placeholder" % [p.id, lo.display_name])
