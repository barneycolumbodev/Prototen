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
	assert_eq(meshes.size(), 1, "one mesh, one draw call")
	var mat: StandardMaterial3D = meshes[0].mesh.surface_get_material(0) as StandardMaterial3D
	assert_not_null(mat)
	assert_not_null(mat.albedo_texture, "base colour")
	assert_not_null(mat.normal_texture, "normal map")
	assert_not_null(mat.roughness_texture, "ORM roughness")
	assert_not_null(mat.emission_texture, "readout emission")
	assert_eq(mat.cull_mode, BaseMaterial3D.CULL_BACK, "single-sided")
	gun.free()


func test_textures_are_vram_compressed() -> void:
	for prefix: String in ["res://assets/weapons/pistol_57/textures/pistol_57", "res://assets/characters/fp_arms/textures/fp_arms"]:
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
