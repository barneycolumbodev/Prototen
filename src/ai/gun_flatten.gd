class_name GunFlatten
extends RefCounted
## Turns an enemy gun's mesh (one surface per untextured material) into one
## surface with one material (optimization overhaul C-08: up to 24 fewer
## draws with twelve men). Built once per gun model and shared.

const SHADER: Shader = preload("res://src/ai/enemy_gun.gdshader")

static var _cache: Dictionary[Mesh, ArrayMesh] = {}


## Swaps every MeshInstance3D under `gun` to its flattened mesh. Meshes
## that can't be flattened (textures, emission, transparency) stay.
static func apply(gun: Node) -> void:
	for n: Node in gun.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		var flat: ArrayMesh = flattened(mi.mesh)
		if flat:
			mi.mesh = flat


static func flattened(src: Mesh) -> ArrayMesh:
	if src == null:
		return null
	if _cache.has(src):
		return _cache[src]
	var out: ArrayMesh = _build(src as ArrayMesh)
	_cache[src] = out
	return out


static func _build(src: ArrayMesh) -> ArrayMesh:
	var count: int = src.get_surface_count() if src else 0
	if count < 2:
		return null
	var v: PackedVector3Array = PackedVector3Array()
	var nrm: PackedVector3Array = PackedVector3Array()
	var uv: PackedVector2Array = PackedVector2Array()  # x = palette column
	var idx: PackedInt32Array = PackedInt32Array()
	var palette: Image = Image.create(count, 2, false, Image.FORMAT_RGBAF)
	for s: int in count:
		var m: StandardMaterial3D = src.surface_get_material(s) as StandardMaterial3D
		if m == null or src.surface_get_primitive_type(s) != Mesh.PRIMITIVE_TRIANGLES:
			return null
		if m.albedo_texture or m.normal_enabled or m.emission_enabled or m.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED \
				or m.metallic_texture or m.roughness_texture or m.vertex_color_use_as_albedo:
			return null
		var lin: Color = m.albedo_color.srgb_to_linear()
		palette.set_pixel(s, 0, Color(lin.r, lin.g, lin.b, m.metallic))
		palette.set_pixel(s, 1, Color(m.roughness, m.metallic_specular, 0.0, 0.0))
		var a: Array = src.surface_get_arrays(s)
		var base: int = v.size()
		var sv: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
		var sn: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
		v.append_array(sv)
		nrm.append_array(sn)
		for k: int in sv.size():
			uv.append(Vector2(float(s), 0.0))
		var si: PackedInt32Array = a[Mesh.ARRAY_INDEX] if a[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
		if si.is_empty():
			for k: int in sv.size():
				si.append(k)
		for k: int in si.size():
			idx.append(base + si[k])
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = SHADER
	mat.set_shader_parameter(&"palette", ImageTexture.create_from_image(palette))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = v
	arrays[Mesh.ARRAY_NORMAL] = nrm
	arrays[Mesh.ARRAY_TEX_UV] = uv
	arrays[Mesh.ARRAY_INDEX] = idx
	# Through ImporterMesh to get LODs back, as the import had them.
	var im: ImporterMesh = ImporterMesh.new()
	im.add_surface(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, mat, "gun")
	im.generate_lods(60.0, 25.0, [])
	return im.get_mesh()
