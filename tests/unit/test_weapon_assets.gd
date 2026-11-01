extends GutTest
## Finished weapon assets stay inside the mobile budget (CLAUDE.md §8, perf-budget skill).

const PISTOL: String = "res://assets/weapons/pistol_57/pistol_57.gltf"
const MAX_FP_WEAPON_TRIS: int = 15000


func _meshes(root: Node) -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	for node: Node in root.find_children("*", "MeshInstance3D", true, false):
		out.append(node as MeshInstance3D)
	return out


func test_pistol_triangle_budget() -> void:
	var gun: Node = (load(PISTOL) as PackedScene).instantiate()
	var tris: int = 0
	for mi: MeshInstance3D in _meshes(gun):
		for s: int in mi.mesh.get_surface_count():
			var arrays: Array = mi.mesh.surface_get_arrays(s)
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			tris += indices.size() / 3
	gun.free()
	assert_gt(tris, 1000)
	assert_lt(tris, MAX_FP_WEAPON_TRIS)


func test_pistol_uses_baked_pbr_textures() -> void:
	var gun: Node = (load(PISTOL) as PackedScene).instantiate()
	var meshes: Array[MeshInstance3D] = _meshes(gun)
	# Body, slide and magazine move separately (split_parts.py) but share one baked material.
	var names: PackedStringArray = PackedStringArray()
	for mi: MeshInstance3D in meshes:
		names.append(mi.name)
	assert_eq(meshes.size(), 3, "body + slide + magazine: %s" % [names])
	for part: String in ["body", "slide", "magazine"]:
		assert_true(gun.find_child(part, true, false) != null, "has a %s node" % part)
	var mat: StandardMaterial3D = meshes[0].mesh.surface_get_material(0) as StandardMaterial3D
	for mi: MeshInstance3D in meshes:
		assert_eq(mi.mesh.surface_get_material(0), mat, "one shared material")
	assert_not_null(mat)
	assert_not_null(mat.albedo_texture, "base colour")
	assert_not_null(mat.normal_texture, "normal map")
	assert_not_null(mat.roughness_texture, "ORM roughness")
	assert_not_null(mat.emission_texture, "readout emission")
	assert_eq(mat.cull_mode, BaseMaterial3D.CULL_BACK, "single-sided")
	gun.free()


func test_textures_are_vram_compressed() -> void:
	for prefix: String in ["res://assets/weapons/pistol_57/textures/pistol_57", "res://assets/characters/fp_arms/textures/fp_arms",
			"res://assets/weapons/mg42/textures/mg42", "res://assets/characters/fp_arms_mg42/textures/fp_arms_mg42"]:
		for name: String in ["basecolor", "orm", "normal", "emission"]:
			var cfg: ConfigFile = ConfigFile.new()
			var path: String = "%s_%s.png.import" % [prefix, name]
			assert_eq(cfg.load(path), OK, path)
			var mode: int = cfg.get_value("params", "compress/mode", -1)
			assert_eq(mode, 2, "%s uses VRAM compression" % path)


func test_arms_triangle_budget() -> void:
	var arms: Node = (load("res://assets/characters/fp_arms/fp_arms.gltf") as PackedScene).instantiate()
	var tris: int = 0
	for mi: MeshInstance3D in _meshes(arms):
		for s: int in mi.mesh.get_surface_count():
			var indices: PackedInt32Array = mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX]
			tris += indices.size() / 3
	arms.free()
	assert_lt(tris, 12000, "first-person arms")


func _tris(root: Node) -> int:
	var tris: int = 0
	for mi: MeshInstance3D in _meshes(root):
		for s: int in mi.mesh.get_surface_count():
			var indices: PackedInt32Array = mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX]
			tris += indices.size() / 3
	return tris


func test_mg42_parts_budget_and_baked_material() -> void:
	var gun: Node = (load("res://assets/weapons/mg42/mg42.gltf") as PackedScene).instantiate()
	var meshes: Array[MeshInstance3D] = _meshes(gun)
	# Body plus the parts that move: feed cover, ammo box, belt. One shared baked material.
	for part: String in ["body", "cover", "magazine", "belt", "stock"]:
		assert_true(gun.find_child(part, true, false) != null, "has a %s node" % part)
	var mat: StandardMaterial3D = meshes[0].mesh.surface_get_material(0) as StandardMaterial3D
	for mi: MeshInstance3D in meshes:
		assert_eq(mi.mesh.surface_get_material(0), mat, "one shared material")
	assert_not_null(mat.albedo_texture)
	assert_not_null(mat.normal_texture)
	assert_not_null(mat.roughness_texture)
	assert_not_null(mat.metallic_texture, "chrome vs black steel comes from the metal map")
	var tris: int = _tris(gun)
	gun.free()
	assert_between(tris, 8000, 25000, "first-person MG42 (%d tris)" % tris)


func test_mg42_arms_budget() -> void:
	var arms: Node = (load("res://assets/characters/fp_arms_mg42/fp_arms_mg42.gltf") as PackedScene).instantiate()
	var tris: int = _tris(arms)
	arms.free()
	assert_lt(tris, 12000, "first-person arms (MG42 hold)")
