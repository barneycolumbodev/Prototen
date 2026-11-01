class_name PenPanel
extends Node3D
## Penetration test station: a panel of real thickness in front of a
## cardboard witness card. The sign counts how many rounds that hit the
## panel made it to the card behind, and the energy they had left.
## Faces +Z (the shooter stands on +Z).

@export var surface: StringName = &"drywall"
@export var label: String = "Drywall"
## Panel layers: thickness of each sheet in metres, with `gap` of air between.
@export var layers: PackedFloat32Array = PackedFloat32Array([0.0127])
@export var gap: float = 0.0
@export var size: Vector2 = Vector2(1.0, 1.6)
@export var color: Color = Color(0.85, 0.84, 0.8)

var hits: int = 0
var through: int = 0
var last_exit_j: float = 0.0

var _shots_hit: Dictionary[int, bool] = {}
var _sign: Label3D


func _ready() -> void:
	add_to_group(&"range_targets")
	_build()
	_update_sign()


func on_layer_hit(hit: BallisticHit) -> void:
	if not _shots_hit.has(hit.shot_id):
		_shots_hit[hit.shot_id] = true
		hits += 1
		_update_sign()


func on_witness_hit(hit: BallisticHit) -> void:
	if _shots_hit.has(hit.shot_id) and _shots_hit[hit.shot_id]:
		_shots_hit[hit.shot_id] = false  # count each round once
		through += 1
		last_exit_j = hit.energy_in
		_update_sign()


func _update_sign() -> void:
	var total: float = 0.0
	for t: float in layers:
		total += t
	var mm: String = "%.1f mm" % (total * 1000.0) if total < 0.05 else "%.0f cm" % (total * 100.0)
	if layers.size() > 1:
		mm = "%d × %.1f mm" % [layers.size(), layers[0] * 1000.0]
	var s: String = "%s\n%s" % [label, mm]
	if hits > 0:
		s += "\n%d / %d through" % [through, hits]
		if through > 0:
			s += "\n%d J left" % roundi(last_exit_j)
	_sign.text = s


func _build() -> void:
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.85
	if surface == &"sheet_metal" or surface == &"armor_plate":
		mat.metallic = 0.7
		mat.roughness = 0.45
	var z: float = 0.0
	for t: float in layers:
		var body: LayerBody = LayerBody.new()
		body.station = self
		body.set_meta(&"surface", surface)
		body.position = Vector3(0, size.y * 0.5 + 0.1, z - t * 0.5)
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = Vector3(size.x, size.y, t)
		cs.shape = box
		body.add_child(cs)
		var mi: MeshInstance3D = MeshInstance3D.new()
		var bm: BoxMesh = BoxMesh.new()
		bm.size = box.size
		mi.mesh = bm
		mi.material_override = mat
		body.add_child(mi)
		add_child(body)
		z -= t + gap
	# Frame posts either side.
	var frame: StaticBody3D = StaticBody3D.new()
	frame.set_meta(&"surface", &"sheet_metal")
	add_child(frame)
	var steel: StandardMaterial3D = StandardMaterial3D.new()
	steel.albedo_color = Color(0.15, 0.15, 0.16)
	steel.metallic = 0.6
	for side: float in [-1.0, 1.0]:
		var cs2: CollisionShape3D = CollisionShape3D.new()
		var post: BoxShape3D = BoxShape3D.new()
		post.size = Vector3(0.06, size.y + 0.2, 0.06)
		cs2.shape = post
		cs2.position = Vector3(side * (size.x * 0.5 + 0.03), (size.y + 0.2) * 0.5, z * 0.5)
		frame.add_child(cs2)
		var pm: MeshInstance3D = MeshInstance3D.new()
		var pbm: BoxMesh = BoxMesh.new()
		pbm.size = post.size
		pm.mesh = pbm
		pm.position = cs2.position
		pm.material_override = steel
		frame.add_child(pm)
	# Witness card just behind, as wide as the panel, so angled rounds still land on it.
	var card: WitnessBody = WitnessBody.new()
	card.station = self
	card.set_meta(&"surface", &"cardboard")
	card.position = Vector3(0, size.y * 0.5 + 0.1, z - 0.3)
	var ccs: CollisionShape3D = CollisionShape3D.new()
	var cbox: BoxShape3D = BoxShape3D.new()
	cbox.size = Vector3(size.x, size.y, 0.003)
	ccs.shape = cbox
	card.add_child(ccs)
	var cmi: MeshInstance3D = MeshInstance3D.new()
	var cbm: BoxMesh = BoxMesh.new()
	cbm.size = cbox.size
	cmi.mesh = cbm
	var cmat: StandardMaterial3D = StandardMaterial3D.new()
	cmat.albedo_color = Color(0.72, 0.6, 0.42)
	cmat.roughness = 1.0
	cmi.material_override = cmat
	card.add_child(cmi)
	add_child(card)
	_sign = Label3D.new()
	_sign.position = Vector3(0, size.y + 0.45, 0.05)
	_sign.font_size = 32
	_sign.pixel_size = 0.0022
	_sign.width = 400.0
	_sign.outline_size = 10
	_sign.modulate = Color(1, 0.95, 0.8)
	add_child(_sign)


class LayerBody:
	extends StaticBody3D
	var station: PenPanel

	func on_ballistic_hit(hit: BallisticHit) -> void:
		station.on_layer_hit(hit)


class WitnessBody:
	extends StaticBody3D
	var station: PenPanel

	func on_ballistic_hit(hit: BallisticHit) -> void:
		station.on_witness_hit(hit)
