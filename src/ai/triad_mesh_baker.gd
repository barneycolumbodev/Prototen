class_name TriadMeshBaker
extends RefCounted
## Builds a triad man's merged meshes off the main thread (2026-11-12,
## owner: ~45 fps in Chinatown whatever the render scale).
##
## Each man is one mesh of his body and everything he wears (EnemyBody). On
## the main thread that merge cost 5 ms at spawn and 8–15 ms at his first
## cut, in the cloud; about three times that on the phone, so every spawn
## and every first limb off was a dropped frame or two. The merged meshes
## also had no LODs (the importer's only exist for the glTF's own meshes),
## so a man 30 m away drew all ~12.5k triangles. Here, for a look picked
## ahead of time (RollingSpawner, or EnemyBody on spawn):
## - the intact mesh with LODs,
## - the split mesh (every piece, for after the first cut) with LODs,
## - the flying piece for each first cut (a segment and what's still on it),
## are built on a WorkerThreadPool thread from vertex arrays read once on
## the main thread. The main thread only turns finished arrays into an
## ArrayMesh (well under a millisecond).
##
## LODs are generated with every segment moved far apart, so a simplified
## triangle never joins two pieces: after a cut the shader collapses the
## severed piece's vertices, and a triangle shared with the body would
## stretch across the screen. Same index LODs as the importer makes; Godot
## picks one by screen-space error (rendering/mesh_lod/lod_change/
## threshold_pixels), so up close nothing changes.

## How far apart segments are pushed while the LODs are generated (m).
const SEPARATE: float = 50.0
## Looks whose finished meshes wait to be taken. A man's are released when
## he's removed (EnemyBody); this only guards against leaks (~2 MB each).
const MAX_READY: int = 40

const FLAGS_CUSTOM: int = (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) \
		| (Mesh.ARRAY_CUSTOM_RGB_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)

static var _mutex: Mutex = Mutex.new()
## Source mesh name -> [verts, normals, tangents, uvs, bones, weights, indices, aabb, weights per vertex].
static var _src: Dictionary[StringName, Array] = {}
## Look key -> WorkerThreadPool task.
static var _jobs: Dictionary[String, int] = {}
## Look key -> finished results ("I", "S": ImporterMesh; "G|<group>": [arrays, flags, centre]).
static var _ready: Dictionary[String, Dictionary] = {}
static var _ready_order: Array[String] = []
## Off in tests that want the old synchronous path.
static var enabled: bool = true


## Starts building `look`'s meshes in the background. `parts`: the body's
## source meshes by node name (triad, part_body, part_head, ...). Main thread.
static func prefetch(look: TriadLook, parts: Dictionary[StringName, Mesh]) -> void:
	if not enabled or look == null:
		return
	var key: String = look.key()
	_mutex.lock()
	var known: bool = _jobs.has(key) or _ready.has(key)
	_mutex.unlock()
	if known:
		return
	var intact: Array = intact_specs(look)
	var split: Array = split_specs(look, parts)
	var gibs: Dictionary = {}
	for seg: StringName in EnemyBody.SEGMENT_ORDER:
		var group: Array[StringName] = EnemyBody.intact_group(seg)
		gibs[",".join(PackedStringArray(group))] = gib_specs(look, group, parts)
	for spec_list: Array in [intact, split] + gibs.values():
		for spec: Array in spec_list:
			var nm: StringName = spec[0]
			if not _src.has(nm):
				var m: Mesh = parts.get(nm, EnemyBody.wardrobe_mesh(nm))
				if m == null or not _read_source(nm, m):
					return  # something unexpected: the synchronous path still works
	var id: int = WorkerThreadPool.add_task(_bake.bind(key, intact, split, gibs), false, "triad meshes")
	_mutex.lock()
	_jobs[key] = id
	_mutex.unlock()


## Is `look`'s background build finished (or never started)? Main thread.
static func is_settled(look: TriadLook) -> bool:
	_mutex.lock()
	var id: int = _jobs.get(look.key(), -1)
	_mutex.unlock()
	return id < 0 or WorkerThreadPool.is_task_completed(id)


## A finished mesh for `look`, or null if it isn't ready (never blocks).
## `what`: "I" intact, "S" split, or "G|<segments>" a flying piece; for a
## piece `centre` gets where its middle was in the rest pose. Main thread.
static func take(look: TriadLook, what: String, centre: Array[Vector3] = []) -> ArrayMesh:
	var key: String = look.key()
	_reap(key)
	_mutex.lock()
	var res: Dictionary = _ready.get(key, {})
	var item: Variant = res.get(what)
	res.erase(what)
	_mutex.unlock()
	if item == null:
		return null
	if item is ImporterMesh:
		var im: ImporterMesh = item
		return im.get_mesh()
	var g: Array = item
	var arrays: Array = g[0]
	var flags: int = g[1]
	var c: Vector3 = g[2]
	centre.append(c)
	var m: ArrayMesh = ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
	return m


## Drops what's left of `look`'s meshes (the man is gone). Main thread.
static func release(look: TriadLook) -> void:
	if look == null:
		return
	var key: String = look.key()
	_reap(key)
	_mutex.lock()
	_ready.erase(key)
	_ready_order.erase(key)
	_mutex.unlock()


## Waits for every build in flight (tests, and before quitting).
static func finish_all() -> void:
	_mutex.lock()
	var keys: Array[String] = _jobs.keys()
	_mutex.unlock()
	for k: String in keys:
		_mutex.lock()
		var id: int = _jobs.get(k, -1)
		_mutex.unlock()
		if id >= 0:
			WorkerThreadPool.wait_for_task_completion(id)
			_mutex.lock()
			_jobs.erase(k)
			_mutex.unlock()


static func _reap(key: String) -> void:
	_mutex.lock()
	var id: int = _jobs.get(key, -1)
	_mutex.unlock()
	if id < 0 or not WorkerThreadPool.is_task_completed(id):
		return
	WorkerThreadPool.wait_for_task_completion(id)
	_mutex.lock()
	_jobs.erase(key)
	_mutex.unlock()


# ------------------------------------------------------------------ specs ([name, segment, slot])

static func intact_specs(look: TriadLook) -> Array:
	var out: Array = [[&"triad", 0, 0]]
	for g: Garment in look.garments:
		var name: StringName = StringName("w_" + String(g.mesh))
		if EnemyBody.wardrobe_mesh(name) != null:
			out.append([name, 0, int(g.slot)])
	return out


static func split_specs(look: TriadLook, parts: Dictionary[StringName, Mesh]) -> Array:
	var out: Array = []
	for i: int in EnemyBody.SEGMENT_ORDER.size() + 1:
		var part: String = "body" if i == 0 else String(EnemyBody.SEGMENT_ORDER[i - 1])
		var pn: StringName = StringName("part_" + part)
		if parts.has(pn):
			out.append([pn, i, 0])
		for g: Garment in look.garments:
			var name: StringName = StringName("w_%s__%s" % [g.mesh, part])
			if EnemyBody.wardrobe_mesh(name) != null:
				out.append([name, i, int(g.slot)])
	return out


static func gib_specs(look: TriadLook, group: Array[StringName], parts: Dictionary[StringName, Mesh]) -> Array:
	var out: Array = []
	for seg: StringName in group:
		var pn: StringName = EnemyBody.SEGMENTS[seg][0]
		if parts.has(pn):
			out.append([pn, 0, 0])  # segment 0: never masked, it's the flying piece
		for g: Garment in look.garments:
			var name: StringName = StringName("w_%s__%s" % [g.mesh, seg])
			if EnemyBody.wardrobe_mesh(name) != null:
				out.append([name, 0, int(g.slot)])
	return out


# ------------------------------------------------------------------ sources (main thread)

## Reads `mesh`'s vertex arrays once (a GPU readback on some drivers, so
## never from a worker thread).
static func _read_source(name: StringName, mesh: Mesh) -> bool:
	if mesh.get_surface_count() < 1:
		return false
	var a: Array = mesh.surface_get_arrays(0)
	var verts: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	if not (a[Mesh.ARRAY_NORMAL] is PackedVector3Array and a[Mesh.ARRAY_TANGENT] is PackedFloat32Array
			and a[Mesh.ARRAY_TEX_UV] is PackedVector2Array and a[Mesh.ARRAY_BONES] is PackedInt32Array
			and a[Mesh.ARRAY_WEIGHTS] is PackedFloat32Array and a[Mesh.ARRAY_INDEX] is PackedInt32Array):
		return false
	var bones: PackedInt32Array = a[Mesh.ARRAY_BONES]
	var per: int = bones.size() / maxi(verts.size(), 1)
	if per != 4 and per != 8:
		return false
	_mutex.lock()
	_src[name] = [verts, a[Mesh.ARRAY_NORMAL], a[Mesh.ARRAY_TANGENT], a[Mesh.ARRAY_TEX_UV], bones,
			a[Mesh.ARRAY_WEIGHTS], a[Mesh.ARRAY_INDEX], mesh.get_aabb(), per]
	_mutex.unlock()
	return true


# ------------------------------------------------------------------ worker

static func _bake(key: String, intact: Array, split: Array, gibs: Dictionary) -> void:
	var res: Dictionary = {}
	var a_i: Array = concat(intact, Vector3.ZERO)
	if not a_i.is_empty():
		res["I"] = with_lods(a_i, false)
	var a_s: Array = concat(split, Vector3.ZERO)
	if not a_s.is_empty():
		var ref: ImporterMesh = res.get("I")
		res["S"] = with_lods(a_s, true, ref)
	for gk: String in gibs:
		var specs: Array = gibs[gk]
		if specs.is_empty():
			continue
		var whole: AABB = AABB()
		var first: bool = true
		_mutex.lock()
		for spec: Array in specs:
			var sname: StringName = spec[0]
			var entry: Array = _src[sname]
			var box: AABB = entry[7]
			whole = box if first else whole.merge(box)
			first = false
		_mutex.unlock()
		var centre: Vector3 = whole.get_center()
		var a_g: Array = concat(specs, -centre)
		if not a_g.is_empty():
			res["G|" + gk] = [a_g, flags_for(a_g), centre]
	_mutex.lock()
	_ready[key] = res
	_ready_order.append(key)
	while _ready_order.size() > MAX_READY:
		_ready.erase(_ready_order.pop_front())
	_mutex.unlock()


static func flags_for(arrays: Array) -> int:
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
	return FLAGS_CUSTOM | (Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS if bones.size() == verts.size() * 8 else 0)


## Concatenates sources into one surface, with CUSTOM0 = rest position and
## segment + 16 × slot, CUSTOM1 = rest normal (as EnemyBody.prepared does).
## `shift` moves the vertices, not their rest positions. Empty on a mismatch.
static func concat(specs: Array, shift: Vector3) -> Array:
	var verts: PackedVector3Array = PackedVector3Array()
	var normals: PackedVector3Array = PackedVector3Array()
	var tangents: PackedFloat32Array = PackedFloat32Array()
	var uvs: PackedVector2Array = PackedVector2Array()
	var bones: PackedInt32Array = PackedInt32Array()
	var weights: PackedFloat32Array = PackedFloat32Array()
	var custom0: PackedFloat32Array = PackedFloat32Array()
	var custom1: PackedFloat32Array = PackedFloat32Array()
	var indices: PackedInt32Array = PackedInt32Array()
	var per: int = 0
	for spec: Array in specs:
		_mutex.lock()
		var spec_name: StringName = spec[0]
		var s: Array = _src.get(spec_name, [])
		_mutex.unlock()
		if s.is_empty():
			return []
		var sp: int = s[8]
		if per == 0:
			per = sp
		elif sp != per:
			return []
		var seg_i: int = spec[1]
		var slot_i: int = spec[2]
		var code: float = float(seg_i + 16 * slot_i)
		var sv: PackedVector3Array = s[0]
		var sn: PackedVector3Array = s[1]
		var st: PackedFloat32Array = s[2]
		var su: PackedVector2Array = s[3]
		var sb: PackedInt32Array = s[4]
		var sw: PackedFloat32Array = s[5]
		var si: PackedInt32Array = s[6]
		var base: int = verts.size()
		var n: int = sv.size()
		verts.append_array(sv)
		normals.append_array(sn)
		tangents.append_array(st)
		uvs.append_array(su)
		bones.append_array(sb)
		weights.append_array(sw)
		var c0: int = custom0.size()
		custom0.resize(c0 + n * 4)
		var c1: int = custom1.size()
		custom1.resize(c1 + n * 3)
		for i: int in n:
			var v: Vector3 = sv[i]
			var nr: Vector3 = sn[i]
			custom0[c0 + i * 4] = v.x
			custom0[c0 + i * 4 + 1] = v.y
			custom0[c0 + i * 4 + 2] = v.z
			custom0[c0 + i * 4 + 3] = code
			custom1[c1 + i * 3] = nr.x
			custom1[c1 + i * 3 + 1] = nr.y
			custom1[c1 + i * 3 + 2] = nr.z
		var i0: int = indices.size()
		indices.append_array(si)
		if base > 0:
			for i: int in si.size():
				indices[i0 + i] += base
	if verts.is_empty():
		return []
	if shift != Vector3.ZERO:
		for i: int in verts.size():
			verts[i] += shift
	var out: Array = []
	out.resize(Mesh.ARRAY_MAX)
	out[Mesh.ARRAY_VERTEX] = verts
	out[Mesh.ARRAY_NORMAL] = normals
	out[Mesh.ARRAY_TANGENT] = tangents
	out[Mesh.ARRAY_TEX_UV] = uvs
	out[Mesh.ARRAY_BONES] = bones
	out[Mesh.ARRAY_WEIGHTS] = weights
	out[Mesh.ARRAY_CUSTOM0] = custom0
	out[Mesh.ARRAY_CUSTOM1] = custom1
	out[Mesh.ARRAY_INDEX] = indices
	return out


## An ImporterMesh of `arrays` with index LODs. `separate`: generate them
## with each segment (CUSTOM0.w % 16) moved SEPARATE m apart, so no LOD
## triangle joins two pieces; the vertices themselves are left as they are.
static func with_lods(arrays: Array, separate: bool, reference: ImporterMesh = null) -> ImporterMesh:
	var flags: int = flags_for(arrays)
	var work: Array = arrays
	if separate:
		work = arrays.duplicate()
		var src_v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var verts: PackedVector3Array = src_v.duplicate()
		var c0: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM0]
		for i: int in verts.size():
			var seg: int = int(c0[i * 4 + 3] + 0.5) % 16
			verts[i].x += SEPARATE * seg
		work[Mesh.ARRAY_VERTEX] = verts
	var gen: ImporterMesh = ImporterMesh.new()
	gen.add_surface(Mesh.PRIMITIVE_TRIANGLES, work, [], {}, null, "", flags)
	gen.generate_lods(25.0, 60.0, [])
	if not separate:
		return gen
	var gen_arrays: Array = gen.get_surface_arrays(0)
	var gen_verts: PackedVector3Array = gen_arrays[Mesh.ARRAY_VERTEX]
	var src_verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var out: ImporterMesh = ImporterMesh.new()
	var lods: Dictionary = {}
	if gen_verts.size() == src_verts.size():
		var all_idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var full: float = all_idx.size() / 3.0
		for li: int in gen.get_surface_lod_count(0):
			var idx: PackedInt32Array = gen.get_surface_lod_indices(0, li)
			# Sizes measured on the spread-out mesh come out inflated (its
			# extent is hundreds of metres): take the intact man's error at
			# the same share of triangles instead. Without one, keep them
			# (too cautious, never too coarse).
			var size: float = gen.get_surface_lod_size(0, li)
			if reference:
				size = _error_at(reference, idx.size() / 3.0 / full)
				if size < 0.0:
					continue
			lods[size] = idx
	out.add_surface(Mesh.PRIMITIVE_TRIANGLES, arrays, [], lods, null, "", flags)
	return out


## The reference mesh's LOD error at `ratio` of its triangles (log-linear
## between its LODs; 0 at full detail). -1 below its coarsest LOD.
static func _error_at(ref: ImporterMesh, ratio: float) -> float:
	var ref_arrays: Array = ref.get_surface_arrays(0)
	var ref_idx: PackedInt32Array = ref_arrays[Mesh.ARRAY_INDEX]
	var full: float = ref_idx.size() / 3.0
	var prev_r: float = 1.0
	var prev_e: float = 0.0
	for li: int in ref.get_surface_lod_count(0):
		var r: float = ref.get_surface_lod_indices(0, li).size() / 3.0 / full
		var e: float = ref.get_surface_lod_size(0, li)
		if ratio >= r:
			var t: float = clampf(log(prev_r / ratio) / maxf(log(prev_r / r), 1e-4), 0.0, 1.0)
			return lerpf(prev_e, e, t)
		prev_r = r
		prev_e = e
	return -1.0
