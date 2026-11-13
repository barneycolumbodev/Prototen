class_name RigidMerge
extends Node
## Draws a model built from many rigid pieces (the augment arms, the drone,
## the knife: glTFs whose fingers, coils and fan leaves are separate nodes
## moved by a clip or by code) as one skinned mesh per material, so it costs
## one draw call per material instead of one per piece per material
## (optimization overhaul C-07: the GX-4 was 107 draws, the fan shield 102).
##
## Every piece becomes a bone with weight 1 on its own vertices, so each
## moving piece stays separate. The original nodes stay where they were, with
## an empty mesh: the clip, the code that moves or hides them (coils, LEDs)
## and find_child() lookups work as before. Each frame the bones copy the
## pieces' transforms relative to the model; a hidden piece's bone is scaled
## to nothing. Runs after the parts' own _process (process_priority), and
## also while the game is paused, so a frozen capture shows the last pose.
##
## Done once when the model is built, not in the export, so the Blender
## generators and the code that drives the models stay as they are.

const PRIORITY: int = 100

static var _empty: ArrayMesh = ArrayMesh.new()

var model: Node3D
var skeleton: Skeleton3D
var merged: MeshInstance3D
## Every Node3D from the model down to the pieces, parents before children.
var _chain: Array[Node3D] = []
var _parent: PackedInt32Array = PackedInt32Array()
## Per bone: index into _chain of the piece it follows.
var _bone_node: PackedInt32Array = PackedInt32Array()
var _rel: Array[Transform3D] = []
var _vis: Array[bool] = []


## Merges the rigid pieces of `root`. Returns null (and leaves the model as
## it was) when there is nothing worth merging.
static func apply(root: Node3D) -> RigidMerge:
	var pieces: Array[MeshInstance3D] = []
	for n: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		if _mergeable(mi):
			pieces.append(mi)
	if pieces.size() < 2:
		return null
	var rm: RigidMerge = RigidMerge.new()
	rm.name = "RigidMerge"
	rm.model = root
	rm.process_priority = PRIORITY
	rm.process_mode = Node.PROCESS_MODE_ALWAYS
	rm._build(pieces)
	root.add_child(rm)
	return rm


static func _mergeable(mi: MeshInstance3D) -> bool:
	var mesh: ArrayMesh = mi.mesh as ArrayMesh
	if mesh == null or mesh == _empty or mi.skin != null or mi.material_override != null:
		return false
	if mesh.get_blend_shape_count() > 0:
		return false
	for i: int in mesh.get_surface_count():
		if mesh.surface_get_primitive_type(i) != Mesh.PRIMITIVE_TRIANGLES:
			return false
		if mi.get_surface_override_material(i) != null:
			return false
		var fmt: int = mesh.surface_get_format(i)
		if fmt & (Mesh.ARRAY_FORMAT_BONES | Mesh.ARRAY_FORMAT_CUSTOM0 | Mesh.ARRAY_FORMAT_CUSTOM1 | Mesh.ARRAY_FORMAT_CUSTOM2 | Mesh.ARRAY_FORMAT_CUSTOM3):
			return false
	return true


func _build(pieces: Array[MeshInstance3D]) -> void:
	# The chain of transforms from the model to each piece.
	var index: Dictionary[Node3D, int] = {}
	for mi: MeshInstance3D in pieces:
		var path: Array[Node3D] = []
		var n: Node = mi
		while n != model and n != null:
			if n is Node3D:
				path.push_front(n as Node3D)
			n = n.get_parent()
		var parent_i: int = -1
		for p: Node3D in path:
			if not index.has(p):
				index[p] = _chain.size()
				_chain.append(p)
				_parent.append(parent_i)
			parent_i = index[p]
	_rel.resize(_chain.size())
	_vis.resize(_chain.size())
	_walk()

	skeleton = Skeleton3D.new()
	skeleton.name = "MergedSkeleton"
	model.add_child(skeleton)
	var skin: Skin = Skin.new()
	# Material -> [arrays being built]
	var groups: Dictionary[Material, Dictionary] = {}
	var order: Array[Material] = []
	var null_key: Material = StandardMaterial3D.new()  # stands in for "no material"
	for mi: MeshInstance3D in pieces:
		var ci: int = index[mi]
		var rest: Transform3D = _rel[ci]
		var bone: int = skeleton.add_bone("%d_%s" % [skeleton.get_bone_count(), mi.name])
		skeleton.set_bone_rest(bone, rest)
		skin.add_bind(bone, rest.affine_inverse())
		_bone_node.append(ci)
		var mesh: ArrayMesh = mi.mesh as ArrayMesh
		for s: int in mesh.get_surface_count():
			var mat: Material = mesh.surface_get_material(s)
			var key: Material = mat if mat else null_key
			if not groups.has(key):
				groups[key] = _new_group()
				order.append(key)
			_append(groups[key], mesh.surface_get_arrays(s), mesh.surface_get_format(s), rest, bone)
		mi.mesh = _empty
	var out: ArrayMesh = ArrayMesh.new()
	for key: Material in order:
		var g: Dictionary = groups[key]
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, _finish(g))
		var surf: int = out.get_surface_count() - 1
		if key != null_key:
			out.surface_set_material(surf, key)
			out.surface_set_name(surf, key.resource_name)
	merged = MeshInstance3D.new()
	merged.name = "MergedMesh"
	merged.mesh = out
	merged.skin = skin
	merged.layers = pieces[0].layers
	merged.cast_shadow = pieces[0].cast_shadow
	skeleton.add_child(merged)
	merged.skeleton = NodePath("..")
	sync()


static func _new_group() -> Dictionary:
	return {
		"v": PackedVector3Array(), "n": PackedVector3Array(), "t": PackedFloat32Array(),
		"c": PackedColorArray(), "uv": PackedVector2Array(), "uv2": PackedVector2Array(),
		"b": PackedInt32Array(), "w": PackedFloat32Array(), "i": PackedInt32Array(),
		"has_t": false, "has_c": false, "has_uv": false, "has_uv2": false,
	}


static func _append(g: Dictionary, a: Array, fmt: int, rest: Transform3D, bone: int) -> void:
	var verts: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	var count: int = verts.size()
	var existing: PackedVector3Array = g["v"]
	var base: int = existing.size()
	# An attribute only some pieces have: earlier pieces get a neutral value.
	var flags: Dictionary[String, int] = {"has_t": Mesh.ARRAY_FORMAT_TANGENT, "has_c": Mesh.ARRAY_FORMAT_COLOR,
			"has_uv": Mesh.ARRAY_FORMAT_TEX_UV, "has_uv2": Mesh.ARRAY_FORMAT_TEX_UV2}
	for key: String in flags:
		if (fmt & flags[key]) and not g[key]:
			g[key] = true
			_backfill(g, key, base)
	var nb: Basis = rest.basis.inverse().transposed()
	var mirrored: bool = rest.basis.determinant() < 0.0
	var v: PackedVector3Array = g["v"]
	var nrm: PackedVector3Array = g["n"]
	var tan: PackedFloat32Array = g["t"]
	var col: PackedColorArray = g["c"]
	var uv: PackedVector2Array = g["uv"]
	var uv2: PackedVector2Array = g["uv2"]
	var bones: PackedInt32Array = g["b"]
	var weights: PackedFloat32Array = g["w"]
	var idx: PackedInt32Array = g["i"]
	var src_n: PackedVector3Array = a[Mesh.ARRAY_NORMAL] if fmt & Mesh.ARRAY_FORMAT_NORMAL else PackedVector3Array()
	var src_t: PackedFloat32Array = a[Mesh.ARRAY_TANGENT] if fmt & Mesh.ARRAY_FORMAT_TANGENT else PackedFloat32Array()
	var src_c: PackedColorArray = a[Mesh.ARRAY_COLOR] if fmt & Mesh.ARRAY_FORMAT_COLOR else PackedColorArray()
	var src_uv: PackedVector2Array = a[Mesh.ARRAY_TEX_UV] if fmt & Mesh.ARRAY_FORMAT_TEX_UV else PackedVector2Array()
	var src_uv2: PackedVector2Array = a[Mesh.ARRAY_TEX_UV2] if fmt & Mesh.ARRAY_FORMAT_TEX_UV2 else PackedVector2Array()
	for k: int in count:
		v.append(rest * verts[k])
		nrm.append((nb * src_n[k]).normalized() if not src_n.is_empty() else Vector3.UP)
		if g["has_t"]:
			if not src_t.is_empty():
				var t: Vector3 = (rest.basis * Vector3(src_t[k * 4], src_t[k * 4 + 1], src_t[k * 4 + 2])).normalized()
				tan.append_array([t.x, t.y, t.z, src_t[k * 4 + 3] * (-1.0 if mirrored else 1.0)])
			else:
				tan.append_array([1.0, 0.0, 0.0, 1.0])
		if g["has_c"]:
			col.append(src_c[k] if not src_c.is_empty() else Color.WHITE)
		if g["has_uv"]:
			uv.append(src_uv[k] if not src_uv.is_empty() else Vector2.ZERO)
		if g["has_uv2"]:
			uv2.append(src_uv2[k] if not src_uv2.is_empty() else Vector2.ZERO)
		bones.append_array([bone, 0, 0, 0])
		weights.append_array([1.0, 0.0, 0.0, 0.0])
	var src_i: PackedInt32Array = a[Mesh.ARRAY_INDEX] if fmt & Mesh.ARRAY_FORMAT_INDEX else PackedInt32Array()
	if src_i.is_empty():
		for k: int in count:
			src_i.append(k)
	# A mirrored piece's triangles are wound the other way once its transform
	# is baked in: flip them so they still face out.
	for k: int in range(0, src_i.size() - 2, 3):
		idx.append(base + src_i[k])
		if mirrored:
			idx.append(base + src_i[k + 2])
			idx.append(base + src_i[k + 1])
		else:
			idx.append(base + src_i[k + 1])
			idx.append(base + src_i[k + 2])
	g["v"] = v
	g["n"] = nrm
	g["t"] = tan
	g["c"] = col
	g["uv"] = uv
	g["uv2"] = uv2
	g["b"] = bones
	g["w"] = weights
	g["i"] = idx


static func _backfill(g: Dictionary, which: String, count: int) -> void:
	match which:
		"has_t":
			var t: PackedFloat32Array = g["t"]
			for k: int in count:
				t.append_array([1.0, 0.0, 0.0, 1.0])
			g["t"] = t
		"has_c":
			var c: PackedColorArray = g["c"]
			for k: int in count:
				c.append(Color.WHITE)
			g["c"] = c
		"has_uv":
			var u: PackedVector2Array = g["uv"]
			u.resize(count)
			g["uv"] = u
		"has_uv2":
			var u2: PackedVector2Array = g["uv2"]
			u2.resize(count)
			g["uv2"] = u2


static func _finish(g: Dictionary) -> Array:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = g["v"]
	arrays[Mesh.ARRAY_NORMAL] = g["n"]
	if g["has_t"]:
		arrays[Mesh.ARRAY_TANGENT] = g["t"]
	if g["has_c"]:
		arrays[Mesh.ARRAY_COLOR] = g["c"]
	if g["has_uv"]:
		arrays[Mesh.ARRAY_TEX_UV] = g["uv"]
	if g["has_uv2"]:
		arrays[Mesh.ARRAY_TEX_UV2] = g["uv2"]
	arrays[Mesh.ARRAY_BONES] = g["b"]
	arrays[Mesh.ARRAY_WEIGHTS] = g["w"]
	arrays[Mesh.ARRAY_INDEX] = g["i"]
	return arrays


## Transforms and visibility of every chain node relative to the model.
func _walk() -> void:
	for i: int in _chain.size():
		var n: Node3D = _chain[i]
		var p: int = _parent[i]
		if p < 0:
			_rel[i] = n.transform
			_vis[i] = n.visible
		else:
			_rel[i] = _rel[p] * n.transform
			_vis[i] = _vis[p] and n.visible


## Copies the pieces' current transforms to the bones.
func sync() -> void:
	if skeleton == null:
		return
	_walk()
	for b: int in _bone_node.size():
		var ci: int = _bone_node[b]
		if _vis[ci]:
			skeleton.set_bone_pose(b, _rel[ci])
		else:
			skeleton.set_bone_pose_position(b, _rel[ci].origin)
			skeleton.set_bone_pose_scale(b, Vector3.ZERO)


func _process(_delta: float) -> void:
	if model and model.is_visible_in_tree():
		sync()
