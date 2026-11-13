extends GutTest
## RigidMerge and GunFlatten (optimization overhaul C-07, C-08): fewer
## surfaces, the same triangles, and pieces that still move and hide.

const MODELS: Array[String] = [
	"res://assets/augments/gx4_gauss_arm/gx4_gauss_arm.gltf",
	"res://assets/augments/bw6_fan_shield/bw6_fan_shield.gltf",
	"res://assets/augments/mw7_monofilament_whip/mw7_monofilament_whip.gltf",
	"res://assets/augments/sd3_shrike_drone/sd3_shrike_drone.gltf",
	"res://assets/weapons/knife/knife_fp.gltf",
]


static func _surfaces(root: Node) -> int:
	var n: int = 0
	for c: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = c as MeshInstance3D
		if mi.mesh:
			n += mi.mesh.get_surface_count()
	return n


static func _triangles(root: Node) -> int:
	var n: int = 0
	for c: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = c as MeshInstance3D
		if mi.mesh == null:
			continue
		for s: int in mi.mesh.get_surface_count():
			var a: Array = mi.mesh.surface_get_arrays(s)
			var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX] if a[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
			var verts: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
			n += idx.size() / 3 if not idx.is_empty() else verts.size() / 3
	return n


func test_models_merge_to_one_draw_per_material() -> void:
	for path: String in MODELS:
		var model: Node3D = (load(path) as PackedScene).instantiate() as Node3D
		add_child_autofree(model)
		var before: int = _surfaces(model)
		var tris: int = _triangles(model)
		var rm: RigidMerge = RigidMerge.apply(model)
		assert_not_null(rm, path)
		if rm == null:
			continue
		var after: int = _surfaces(model)
		assert_lt(after, before, "%s: %d -> %d surfaces" % [path, before, after])
		assert_lte(after, 12, "%s: one surface per material" % path)
		assert_eq(_triangles(model), tris, "%s keeps every triangle" % path)
		gut.p("%s: %d -> %d surfaces, %d triangles" % [path.get_file(), before, after, tris])


func test_bones_follow_pieces() -> void:
	var model: Node3D = (load(MODELS[0]) as PackedScene).instantiate() as Node3D
	add_child_autofree(model)
	var rm: RigidMerge = RigidMerge.apply(model)
	var coil: Node3D = model.find_child("coil_1", true, false) as Node3D
	assert_not_null(coil, "pieces can still be found by name")
	assert_eq((coil as MeshInstance3D).mesh.get_surface_count(), 0, "the piece itself draws nothing")
	var b: int = -1
	for i: int in rm.skeleton.get_bone_count():
		if rm.skeleton.get_bone_name(i).ends_with("_coil_1"):
			b = i
	assert_gt(b, -1)
	coil.position += Vector3(0.1, 0.0, 0.0)
	rm.sync()
	var rel: Transform3D = model.global_transform.affine_inverse() * coil.global_transform
	assert_almost_eq(rm.skeleton.get_bone_pose(b).origin, rel.origin, Vector3.ONE * 1e-4, "bone moves with the piece")
	coil.visible = false
	rm.sync()
	assert_almost_eq(rm.skeleton.get_bone_pose_scale(b), Vector3.ZERO, Vector3.ONE * 1e-6, "hidden piece collapses")


func test_enemy_guns_flatten_to_one_surface() -> void:
	for gun_path: String in ["res://assets/weapons/enemy/type56.gltf", "res://assets/weapons/enemy/smg.gltf", "res://assets/weapons/enemy/pump.gltf"]:
		var gun: Node3D = (load(gun_path) as PackedScene).instantiate() as Node3D
		add_child_autofree(gun)
		var tris: int = _triangles(gun)
		GunFlatten.apply(gun)
		assert_eq(_surfaces(gun), 1, gun_path)
		assert_eq(_triangles(gun), tris, "%s keeps every triangle" % gun_path)
		var mi: MeshInstance3D = gun.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
		assert_true(mi.mesh.surface_get_material(0) is ShaderMaterial)
