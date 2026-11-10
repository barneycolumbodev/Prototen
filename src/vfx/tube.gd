class_name Tube
extends RefCounted
## Adds a round tube along a path to an ImmediateMesh (the mesh arm's
## tendril and claw, drawn fresh every frame). Normals and UVs included:
## u runs round the tube, v along it in metres × `v_per_m`.


## `im` must be inside surface_begin(PRIMITIVE_TRIANGLES). `radii`: one per
## point (or a single value for all).
static func add(im: ImmediateMesh, pts: PackedVector3Array, radii: PackedFloat32Array, sides: int = 8, v_per_m: float = 1.0, v0: float = 0.0) -> void:
	var n: int = pts.size()
	if n < 2:
		return
	# Parallel-transport frames so the tube doesn't twist.
	var t0: Vector3 = (pts[1] - pts[0]).normalized()
	var up: Vector3 = t0.cross(Vector3.UP if absf(t0.y) < 0.95 else Vector3.RIGHT).normalized()
	var rings: Array[PackedVector3Array] = []
	var normals: Array[PackedVector3Array] = []
	var vs: PackedFloat32Array = PackedFloat32Array()
	var v: float = v0
	for i: int in n:
		var t: Vector3 = (pts[mini(i + 1, n - 1)] - pts[maxi(i - 1, 0)]).normalized()
		up = (up - t * up.dot(t)).normalized()
		if up.length_squared() < 0.0001:
			up = t.cross(Vector3.UP if absf(t.y) < 0.95 else Vector3.RIGHT).normalized()
		var side: Vector3 = t.cross(up)
		var r: float = radii[mini(i, radii.size() - 1)]
		var ring: PackedVector3Array = PackedVector3Array()
		var nrm: PackedVector3Array = PackedVector3Array()
		for k: int in sides + 1:
			var a: float = TAU * k / sides
			var d: Vector3 = up * cos(a) + side * sin(a)
			nrm.append(d)
			ring.append(pts[i] + d * r)
		rings.append(ring)
		normals.append(nrm)
		if i > 0:
			v += pts[i].distance_to(pts[i - 1]) * v_per_m
		vs.append(v)
	for i: int in n - 1:
		for k: int in sides:
			var u0: float = float(k) / sides
			var u1: float = float(k + 1) / sides
			_vert(im, rings[i][k], normals[i][k], Vector2(u0, vs[i]))
			_vert(im, rings[i + 1][k], normals[i + 1][k], Vector2(u0, vs[i + 1]))
			_vert(im, rings[i + 1][k + 1], normals[i + 1][k + 1], Vector2(u1, vs[i + 1]))
			_vert(im, rings[i][k], normals[i][k], Vector2(u0, vs[i]))
			_vert(im, rings[i + 1][k + 1], normals[i + 1][k + 1], Vector2(u1, vs[i + 1]))
			_vert(im, rings[i][k + 1], normals[i][k + 1], Vector2(u1, vs[i]))


static func _vert(im: ImmediateMesh, p: Vector3, n: Vector3, uv: Vector2) -> void:
	im.surface_set_normal(n)
	im.surface_set_uv(uv)
	im.surface_add_vertex(p)


## Points on a quadratic Bézier from `a` through control `c` to `b`.
static func bezier(a: Vector3, c: Vector3, b: Vector3, count: int) -> PackedVector3Array:
	var out: PackedVector3Array = PackedVector3Array()
	for i: int in count + 1:
		var t: float = float(i) / count
		out.append(a.lerp(c, t).lerp(c.lerp(b, t), t))
	return out
