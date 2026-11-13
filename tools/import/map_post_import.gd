@tool
extends EditorScenePostImport
## Post-import for the map glTFs (assets/levels/<map>, optimization overhaul
## W-10). The importer stores TEXCOORD_2 (the world shader's data: emission
## strength and the outdoor flag) as CUSTOM0 in two 32-bit floats a vertex;
## half floats hold both exactly enough (a 0/1 flag and a strength of a few
## units), so every surface is rebuilt with CUSTOM0 as RG_HALF. Everything
## else (attributes, compression, LODs, material, name) is kept. Shadow
## meshes are switched off in the .import file: nothing casts shadows here.


func _post_import(scene: Node) -> Object:
	var done: int = 0
	for n: Node in scene.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		var src: ArrayMesh = mi.mesh as ArrayMesh
		if src == null:
			continue
		var out: ArrayMesh = slim(src)
		if out:
			mi.mesh = out
			done += 1
	print("map_post_import: CUSTOM0 to half floats on %d meshes" % done)
	return scene


## A copy of `src` with CUSTOM0 as RG_HALF, or null if it has no RG_FLOAT CUSTOM0.
static func slim(src: ArrayMesh) -> ArrayMesh:
	var out: ArrayMesh = ArrayMesh.new()
	out.resource_name = src.resource_name
	for s: int in src.get_surface_count():
		var fmt: int = src.surface_get_format(s)
		var custom: int = (fmt >> Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) & Mesh.ARRAY_FORMAT_CUSTOM_MASK
		if not (fmt & Mesh.ARRAY_FORMAT_CUSTOM0) or custom != Mesh.ARRAY_CUSTOM_RG_FLOAT:
			return null
		var arrays: Array = src.surface_get_arrays(s)
		var data: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM0]
		var half: PackedByteArray = PackedByteArray()
		half.resize(data.size() * 2)
		for i: int in data.size():
			half.encode_half(i * 2, data[i])
		arrays[Mesh.ARRAY_CUSTOM0] = half
		var lods: Dictionary = {}
		var surf: Dictionary = RenderingServer.mesh_get_surface(src.get_rid(), s)
		var vcount: int = surf.get("vertex_count", 0)
		var lod_list: Array = surf.get("lods", [])
		for lod: Variant in lod_list:
			var ld: Dictionary = lod
			var bytes: PackedByteArray = ld.get("index_data", PackedByteArray())
			var idx: PackedInt32Array = PackedInt32Array()
			if vcount <= 65535:
				idx.resize(bytes.size() / 2)
				for k: int in idx.size():
					idx[k] = bytes.decode_u16(k * 2)
			else:
				idx = bytes.to_int32_array()
			var edge: float = ld.get("edge_length", 0.0)
			lods[edge] = idx
		var keep: int = fmt & (Mesh.ARRAY_FLAG_COMPRESS_ATTRIBUTES | Mesh.ARRAY_FLAG_USE_2D_VERTICES | Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS)
		var flags: int = keep | (Mesh.ARRAY_CUSTOM_RG_HALF << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT)
		out.add_surface_from_arrays(src.surface_get_primitive_type(s), arrays, [], lods, flags)
		out.surface_set_material(s, src.surface_get_material(s))
		out.surface_set_name(s, src.surface_get_name(s))
	return out
