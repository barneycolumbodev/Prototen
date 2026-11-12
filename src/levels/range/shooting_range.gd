class_name ShootingRange
extends Node3D
## M1a shooting range inside the test room (docs/m1-gunplay-plan.md item 3).
## Laid out around the spawn's sightlines (spawn at 0,0,12 facing north):
## - Steel poppers at ~19 m, one far plate on the mezzanine at ~25 m.
## - Triad members standing at the target spots (passive: they react, bleed,
##   fall, but never fire back), in the open, behind a drywall wall and behind
##   a fence. A new one walks up to an empty spot a while after a kill;
##   bodies stay until there are too many.
## - Penetration lane (east): six materials, each with a witness card behind.
## - Destructible drywall wall and plank fence.
## - A table of cans and bottles, a stack of crates.

const LOOK_FROM: Vector3 = Vector3(0, 0, 12)

const PLATES: Array = [
	# position, plate height, round
	[Vector3(-7.0, 0, -6.5), 1.0, false],
	[Vector3(-5.5, 0, -6.5), 1.3, false],
	[Vector3(-4.0, 0, -6.5), 1.1, true],
	[Vector3(-2.5, 0, -6.5), 1.5, false],
	[Vector3(-1.0, 0, -6.5), 1.2, true],
	[Vector3(-0.5, 3.5, -13.0), 1.2, false],
]

const TARGET_RESPAWN: float = 9.0
const MAX_BODIES: int = 6
const ROLES: Array[String] = ["gunman", "enforcer", "gunman", "red_pole"]
const DUMMIES: Array[Vector3] = [
	Vector3(1.5, 0, -1.0),
	Vector3(-5.5, 0, 4.0),
	Vector3(5.5, 0, -7.2),
	Vector3(-7.5, 0, -0.6),
]

const PEN_LANE: Array = [
	# surface, label, layers (m), gap (m), colour
	[&"drywall", "Drywall wall", [0.0127, 0.0127], 0.09, Color(0.86, 0.85, 0.8)],
	[&"wood", "Plywood", [0.019, 0.019], 0.0, Color(0.7, 0.55, 0.35)],
	[&"sheet_metal", "Car door (steel)", [0.0009, 0.0009], 0.1, Color(0.35, 0.4, 0.45)],
	[&"wood", "Pine timber", [0.05], 0.0, Color(0.78, 0.62, 0.4)],
	[&"concrete", "Concrete block", [0.15], 0.0, Color(0.6, 0.6, 0.58)],
	[&"armor_plate", "AR500 plate", [0.006], 0.0, Color(0.3, 0.32, 0.3)],
]

var stats: RangeStats
## Range targets, one per DUMMIES spot (null while respawning).
var targets: Array[Enemy] = []
var squad: Squad
var bodies: Array[Enemy] = []
var _respawn: Array[float] = []
var plates: Array[SteelPlate] = []
var panels: Array[PenPanel] = []
var walls: Array[DestructibleWall] = []


func _ready() -> void:
	stats = RangeStats.new()
	stats.name = "RangeStats"
	add_child(stats)
	for spec: Array in PLATES:
		var plate: SteelPlate = SteelPlate.new()
		plate.height = spec[1]
		plate.round_plate = spec[2]
		if plate.round_plate:
			plate.plate_size = Vector2(0.3, 0.3)
		add_child(plate)
		plate.position = spec[0]
		plates.append(plate)
	squad = Squad.new()
	squad.name = "RangeSquad"
	add_child(squad)
	for i: int in DUMMIES.size():
		targets.append(null)
		_respawn.append(0.0)
		spawn_target(i)
	for i: int in PEN_LANE.size():
		var spec: Array = PEN_LANE[i]
		var p: PenPanel = PenPanel.new()
		p.surface = spec[0]
		p.label = spec[1]
		var layers: PackedFloat32Array = PackedFloat32Array()
		for t: float in spec[2]:
			layers.append(t)
		p.layers = layers
		p.gap = spec[3]
		p.color = spec[4]
		p.size = Vector2(1.0, 1.5)
		add_child(p)
		p.position = Vector3(6.0 + i * 1.4, 0, 3.0)
		panels.append(p)
	var drywall: DestructibleWall = DestructibleWall.new()
	drywall.surface = &"drywall"
	drywall.size = Vector2(3.0, 2.4)
	drywall.thickness = 0.026
	drywall.cell = 0.2
	add_child(drywall)
	drywall.position = Vector3(5.5, 0, -5.6)
	walls.append(drywall)
	var fence: DestructibleWall = DestructibleWall.new()
	fence.surface = &"wood"
	fence.size = Vector2(2.4, 1.8)
	fence.thickness = 0.022
	fence.cell = 0.3
	fence.cell_strength = 180.0
	fence.color = Color(0.62, 0.45, 0.27)
	add_child(fence)
	fence.position = Vector3(-7.5, 0, 1.0)
	walls.append(fence)
	_build_table(Vector3(-2.5, 0, 6.0))
	_build_crates(Vector3(2.6, 0, 5.4))


## Puts a fresh triad member on target spot `i`.
func spawn_target(i: int) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % ROLES[i % ROLES.size()]) as EnemyConfig
	e.passive = true
	e.name = "Target%d" % i
	squad.add(e)
	add_child(e)
	e.position = DUMMIES[i]
	e.face(_face_spawn(DUMMIES[i]))
	e.died.connect(_on_target_died.bind(i))
	targets[i] = e
	return e


## Where zone `zone` of target `i` is now (its spot at chest height while it respawns).
func target_point(i: int, zone: StringName = &"chest") -> Vector3:
	var e: Enemy = targets[i] if i < targets.size() else null
	if e and is_instance_valid(e) and e.body and e.body.hitboxes.has(zone):
		return e.body.hitboxes[zone].global_position
	return DUMMIES[i] + Vector3.UP * 1.3


## Removes every range target and body (wave mode clears the range).
func clear_targets() -> void:
	for e: Enemy in targets + bodies:
		if is_instance_valid(e):
			e.queue_free()
	bodies.clear()
	for i: int in targets.size():
		targets[i] = null
		_respawn[i] = -1.0


func restore_targets() -> void:
	for i: int in targets.size():
		if targets[i] == null:
			spawn_target(i)


func _on_target_died(_e: Enemy, i: int) -> void:
	bodies.append(targets[i])
	targets[i] = null
	_respawn[i] = TARGET_RESPAWN
	while bodies.size() > MAX_BODIES:
		var old: Enemy = bodies.pop_front()
		if is_instance_valid(old):
			old.queue_free()


func _process(delta: float) -> void:
	for i: int in _respawn.size():
		if targets[i] == null and _respawn[i] > 0.0:
			_respawn[i] -= delta
			if _respawn[i] <= 0.0:
				var e: Enemy = spawn_target(i)
				# Step aside from a body lying on the spot.
				for b: Enemy in bodies:
					if is_instance_valid(b) and b.body.bone_position(&"hips").distance_to(DUMMIES[i]) < 0.9:
						e.position = DUMMIES[i] + Vector3(1.1, 0, 0.3)
						break


func _face_spawn(at: Vector3) -> float:
	var d: Vector3 = LOOK_FROM - at
	return atan2(d.x, d.z)


func _build_table(at: Vector3) -> void:
	var table: StaticBody3D = StaticBody3D.new()
	table.set_meta(&"surface", &"wood")
	add_child(table)
	table.position = at
	var wood: StandardMaterial3D = StandardMaterial3D.new()
	wood.albedo_color = Color(0.42, 0.3, 0.2)
	wood.roughness = 0.8
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var parts: Array = [[Vector3(1.6, 0.05, 0.7), Vector3(0, 0.875, 0)]]
	for sx: float in [-0.72, 0.72]:
		for sz: float in [-0.28, 0.28]:
			parts.append([Vector3(0.06, 0.85, 0.06), Vector3(sx, 0.425, sz)])
	for spec: Array in parts:
		var size: Vector3 = spec[0]
		var pos: Vector3 = spec[1]
		var bm: BoxMesh = BoxMesh.new()
		bm.size = size
		st.append_from(bm, 0, Transform3D(Basis(), pos))
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = size
		cs.shape = box
		cs.position = pos
		table.add_child(cs)
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = wood
	table.add_child(mi)
	var can_mat: StandardMaterial3D = StandardMaterial3D.new()
	can_mat.albedo_color = Color(0.75, 0.2, 0.15)
	can_mat.metallic = 0.8
	can_mat.roughness = 0.35
	var glass: StandardMaterial3D = StandardMaterial3D.new()
	glass.albedo_color = Color(0.25, 0.5, 0.3, 0.75)
	glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass.roughness = 0.1
	glass.metallic_specular = 0.9
	for i: int in 7:
		var bottle: bool = i % 2 == 1
		var prop: RangeProp = RangeProp.new()
		prop.breakable = bottle
		prop.mass = 0.35 if bottle else 0.04
		prop.set_meta(&"surface", &"glass" if bottle else &"thin_metal")
		var r: float = 0.035 if bottle else 0.033
		var h: float = 0.26 if bottle else 0.12
		var cs2: CollisionShape3D = CollisionShape3D.new()
		var cyl: CylinderShape3D = CylinderShape3D.new()
		cyl.radius = r
		cyl.height = h
		cs2.shape = cyl
		prop.add_child(cs2)
		var m: MeshInstance3D = MeshInstance3D.new()
		var cm: CylinderMesh = CylinderMesh.new()
		cm.top_radius = r * (0.45 if bottle else 1.0)
		cm.bottom_radius = r
		cm.height = h
		cm.radial_segments = 12
		m.mesh = cm
		m.material_override = glass if bottle else can_mat
		prop.add_child(m)
		prop.position = at + Vector3(-0.66 + i * 0.22, 0.9 + h * 0.5 + 0.002, 0.0)
		add_child(prop)


func _build_crates(at: Vector3) -> void:
	var wood: StandardMaterial3D = StandardMaterial3D.new()
	wood.albedo_color = Color(0.6, 0.44, 0.25)
	wood.roughness = 0.85
	var spots: Array[Vector3] = [Vector3(0, 0.225, 0), Vector3(0.48, 0.225, 0.05), Vector3(0.22, 0.675, 0.02)]
	for p: Vector3 in spots:
		var crate: RangeProp = RangeProp.new()
		crate.mass = 6.0
		crate.respawn_time = 10.0
		crate.set_meta(&"surface", &"crate")
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = Vector3(0.45, 0.45, 0.45)
		cs.shape = box
		crate.add_child(cs)
		var m: MeshInstance3D = MeshInstance3D.new()
		var bm: BoxMesh = BoxMesh.new()
		bm.size = box.size
		m.mesh = bm
		m.material_override = wood
		crate.add_child(m)
		crate.position = at + p
		add_child(crate)
