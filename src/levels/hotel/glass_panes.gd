class_name GlassPanes
extends Node3D
## The hotel's breakable glass (owner, 2026-11-18): the gallery balustrade
## and the glass front. Panes come from layout.json "pane" markers (Blender
## centre, width, height, thickness, yaw). Tempered glass: the first round,
## bolt or blast through a pane bursts all of it into falling shards; the
## opening is left clear (a man knocked into it goes over the edge).
##
## All intact panes are one MultiMesh (one draw); each has its own thin
## static body on the world layer (surface "glass": rounds go through it,
## it stops people) that `on_ballistic_hit` breaks.

var map: ChinatownMap
var mm: MultiMesh
var bodies: Array[Pane] = []
var broken: int = 0
var _xforms: Array[Transform3D] = []
var _sizes: Array[Vector3] = []

static var _mat: StandardMaterial3D


class Pane:
	extends StaticBody3D
	var panes: GlassPanes
	var index: int = 0

	func on_ballistic_hit(hit: BallisticHit) -> void:
		panes.shatter(index, hit.direction, hit.point)


func _ready() -> void:
	if _mat == null:
		_mat = StandardMaterial3D.new()
		_mat.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
		_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_mat.albedo_color = Color(0.62, 0.72, 0.74, 0.16)
		_mat.metallic = 0.4
		_mat.roughness = 0.04
		_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		_mat.render_priority = 3
	for m: Dictionary in map.layout["markers"]:
		if ChinatownMap.fstr(m, "kind") != "pane":
			continue
		var size: Vector3 = Vector3(ChinatownMap.fnum(m, "w"), ChinatownMap.fnum(m, "h"), ChinatownMap.fnum(m, "t", 0.02))
		# Blender yaw about +Z is the same turn about Godot's +Y.
		var b: Basis = Basis(Vector3.UP, deg_to_rad(ChinatownMap.fnum(m, "yaw")))
		var xf: Transform3D = Transform3D(b, ChinatownMap.fpos(m))
		_xforms.append(xf)
		_sizes.append(size)
		var body: Pane = Pane.new()
		body.panes = self
		body.index = bodies.size()
		body.collision_layer = Ballistics.LAYER_WORLD
		body.collision_mask = 0
		body.set_meta(&"surface", &"glass")
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = Vector3(size.x, size.y, maxf(size.z, 0.04))
		cs.shape = box
		body.add_child(cs)
		add_child(body)
		body.global_transform = xf
		bodies.append(body)
	var bm: BoxMesh = BoxMesh.new()
	bm.size = Vector3.ONE
	mm = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = bm
	mm.instance_count = _xforms.size()
	for i: int in _xforms.size():
		mm.set_instance_transform(i, _scaled(i))
	var mi: MultiMeshInstance3D = MultiMeshInstance3D.new()
	mi.name = "Glass"
	mi.multimesh = mm
	mi.material_override = _mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)


func _scaled(i: int) -> Transform3D:
	var xf: Transform3D = _xforms[i]
	return Transform3D(xf.basis.scaled_local(_sizes[i]), xf.origin)


func count() -> int:
	return bodies.size()


func is_broken(i: int) -> bool:
	return bodies[i].collision_layer == 0


## Bursts pane `i`: shards fall from all of it, pushed along `dir`.
func shatter(i: int, dir: Vector3, at: Vector3) -> void:
	if i < 0 or i >= bodies.size() or is_broken(i):
		return
	broken += 1
	bodies[i].collision_layer = 0
	mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ZERO), _xforms[i].origin))
	var c: Vector3 = _xforms[i].origin
	var size: Vector3 = _sizes[i]
	var across: Vector3 = _xforms[i].basis.x
	var push: Vector3 = dir.normalized() * 2.2
	var n: int = clampi(roundi(size.x * size.y * 7.0), 4, 12)
	for k: int in n:
		var p: Vector3 = c + across * randf_range(-0.45, 0.45) * size.x + Vector3.UP * randf_range(-0.45, 0.45) * size.y
		Fx.debris(p, push * randf_range(0.3, 1.0), Color(0.75, 0.85, 0.86), 0.05, 1, 0.5, &"glass")
	Fx._emit(&"sparks", at, dir, Color(0.85, 0.95, 1.0, 1.0), 14, 1.4)
	Sfx.play_at(&"glass_shatter", at, 0.0, 0.08)
