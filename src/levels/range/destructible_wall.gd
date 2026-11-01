class_name DestructibleWall
extends Node3D
## A wall that shoots apart (ballistic destruction). Built from a grid of
## cells, each its own collider sharing one MultiMesh draw call. Every
## round damages the cell it hit by the energy it left in it (scaled by the
## material's structural factor) and cracks the neighbours; a broken cell
## disappears and throws debris along the round's path, so sustained fire
## opens real holes you can see and shoot through.
## Faces +Z; centred on X, standing on Y = 0.

@export var surface: StringName = &"drywall"
@export var size: Vector2 = Vector2(3.0, 2.4)
@export var thickness: float = 0.025
@export var cell: float = 0.25
## Structural toughness of one cell in joules (before the material's scale).
@export var cell_strength: float = 110.0
## Flat damage per hit on top of the energy (shock, cracking).
@export var hit_shock: float = 18.0
## Fraction of a hit's damage passed to the four neighbours.
@export_range(0.0, 1.0) var crack_spread: float = 0.35
@export var color: Color = Color(0.86, 0.85, 0.81)
@export var debris_per_cell: int = 3

var cols: int = 0
var rows: int = 0
var broken: int = 0

var _hp: PackedFloat32Array = PackedFloat32Array()
var _bodies: Array[StaticBody3D] = []
var _index: Dictionary[StaticBody3D, int] = {}
var _mm: MultiMesh
var _tint: PackedFloat32Array = PackedFloat32Array()


func _ready() -> void:
	add_to_group(&"range_targets")
	_build()
	EventBus.ballistic_hit.connect(_on_hit)


func cell_count() -> int:
	return cols * rows


func is_broken(i: int) -> bool:
	return _hp[i] <= 0.0


func _on_hit(hit: BallisticHit) -> void:
	var body: StaticBody3D = hit.collider as StaticBody3D
	if body == null or not _index.has(body):
		return
	var i: int = _index[body]
	var s: SurfaceMaterial = hit.surface
	var dmg: float = (hit.deposited() + hit_shock) * s.structural_damage_scale
	_damage(i, dmg, hit)
	var c: int = i % cols
	var r: int = i / cols
	for n: Vector2i in [Vector2i(c - 1, r), Vector2i(c + 1, r), Vector2i(c, r - 1), Vector2i(c, r + 1)]:
		if n.x >= 0 and n.x < cols and n.y >= 0 and n.y < rows:
			_damage(n.y * cols + n.x, dmg * crack_spread, hit)


func _damage(i: int, amount: float, hit: BallisticHit) -> void:
	if _hp[i] <= 0.0:
		return
	_hp[i] -= amount
	# Darken as it cracks.
	var health: float = clampf(_hp[i] / cell_strength, 0.0, 1.0)
	_mm.set_instance_color(i, color.darkened((1.0 - health) * 0.35))
	if _hp[i] <= 0.0:
		_break(i, hit)


func _break(i: int, hit: BallisticHit) -> void:
	broken += 1
	var body: StaticBody3D = _bodies[i]
	var at: Vector3 = body.global_position
	_index.erase(body)
	body.queue_free()
	Fx.clear_holes_near(at, cell * 0.75)
	_mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO))
	var push: Vector3 = hit.direction * 2.5 + Vector3.UP * 0.5
	Fx.debris(at, push, color, cell * 0.45, debris_per_cell, 0.6, surface)
	Sfx.play_at(&"impact_" + String(hit.surface.impact_sound), at, -4.0)
	# A cell with nothing left above or beside it can't hang in the air: drop the
	# ones directly above that lost all support.
	var c: int = i % cols
	var r: int = i / cols
	if r + 1 < rows:
		var above: int = (r + 1) * cols + c
		if _hp[above] > 0.0 and _unsupported(above):
			_hp[above] = 0.0
			_break(above, hit)


func _unsupported(i: int) -> bool:
	var c: int = i % cols
	var r: int = i / cols
	var below: bool = r == 0 or _hp[(r - 1) * cols + c] > 0.0
	var left: bool = c > 0 and _hp[r * cols + c - 1] > 0.0
	var right: bool = c < cols - 1 and _hp[r * cols + c + 1] > 0.0
	var top: bool = r == rows - 1  # top row is held by the frame
	return not (below or left or right or top)


func _build() -> void:
	cols = maxi(1, roundi(size.x / cell))
	rows = maxi(1, roundi(size.y / cell))
	var cw: float = size.x / cols
	var ch: float = size.y / rows
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_3D
	_mm.use_colors = true
	var box_mesh: BoxMesh = BoxMesh.new()
	box_mesh.size = Vector3(cw * 0.995, ch * 0.995, thickness)
	_mm.mesh = box_mesh
	_mm.instance_count = cols * rows
	var mmi: MultiMeshInstance3D = MultiMeshInstance3D.new()
	mmi.multimesh = _mm
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.9
	mmi.material_override = mat
	add_child(mmi)
	var shape: BoxShape3D = BoxShape3D.new()
	shape.size = Vector3(cw, ch, thickness)
	_hp.resize(cols * rows)
	for r: int in rows:
		for c: int in cols:
			var i: int = r * cols + c
			var pos: Vector3 = Vector3(-size.x * 0.5 + cw * (c + 0.5), ch * (r + 0.5), 0.0)
			var body: StaticBody3D = StaticBody3D.new()
			body.position = pos
			body.set_meta(&"surface", surface)
			var cs: CollisionShape3D = CollisionShape3D.new()
			cs.shape = shape
			body.add_child(cs)
			add_child(body)
			_bodies.append(body)
			_index[body] = i
			_hp[i] = cell_strength
			_mm.set_instance_transform(i, Transform3D(Basis(), pos))
			_mm.set_instance_color(i, color.darkened(randf() * 0.04))
	# Frame: top beam and side studs (steel, indestructible).
	var frame: StaticBody3D = StaticBody3D.new()
	frame.set_meta(&"surface", &"sheet_metal")
	add_child(frame)
	var steel: StandardMaterial3D = StandardMaterial3D.new()
	steel.albedo_color = Color(0.3, 0.31, 0.33)
	steel.metallic = 0.5
	for spec: Array in [[Vector3(size.x + 0.16, 0.08, 0.1), Vector3(0, size.y + 0.04, 0)],
			[Vector3(0.08, size.y + 0.08, 0.1), Vector3(-size.x * 0.5 - 0.04, (size.y + 0.08) * 0.5, 0)],
			[Vector3(0.08, size.y + 0.08, 0.1), Vector3(size.x * 0.5 + 0.04, (size.y + 0.08) * 0.5, 0)]]:
		var dims: Vector3 = spec[0]
		var at: Vector3 = spec[1]
		var cs2: CollisionShape3D = CollisionShape3D.new()
		var b: BoxShape3D = BoxShape3D.new()
		b.size = dims
		cs2.shape = b
		cs2.position = at
		frame.add_child(cs2)
		var mi: MeshInstance3D = MeshInstance3D.new()
		var bm: BoxMesh = BoxMesh.new()
		bm.size = dims
		mi.mesh = bm
		mi.position = at
		mi.material_override = steel
		frame.add_child(mi)
