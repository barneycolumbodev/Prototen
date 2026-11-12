class_name BodyAppearance
extends Node3D
## The operative's body as it looks with the installed parts (docs/design.md
## §3.3, §9.2 "Appearance"): the base model in the GS-2 graft suit
## (assets/characters/operative, raw_assets/characters/operative/build.py)
## plus every PartVisual of every part, mounted on its socket (a bone).
## The model has three meshes: the suit, the helmet and the bare head; set
## `helmet_on` to swap the helmet for the head.
## `rebuild()` after the loadout changes. Used by the body-status screen
## now; later by the player's full body (shadows, reflections) and the
## loadout screen.

const MODEL: PackedScene = preload("res://assets/characters/operative/operative.gltf")

var loadout: BodyLoadout
var skeleton: Skeleton3D
## Helmet on (default) or off (the operative's own head and hair).
var helmet_on: bool = true:
	set(v):
		helmet_on = v
		_apply_helmet()
## Mounted part pieces (for tests and the loadout screen), and the part each belongs to.
var mounted: Array[Node3D] = []
var mounted_ids: Array[StringName] = []
## Suit and hardware colours (null: as built).
var colors: BodyColors

var _model: Node3D
var _attach: Dictionary[StringName, BoneAttachment3D] = {}
var _mats: Dictionary[String, Material] = {}


func _ready() -> void:
	_model = MODEL.instantiate() as Node3D
	add_child(_model)
	skeleton = _model.find_child("Skeleton3D", true, false) as Skeleton3D
	_mats = {
		"plate": _mat(Color(0.012, 0.012, 0.014), 0.24, 0.35, Color.BLACK),
		"hardware": _mat(Color(0.09, 0.095, 0.1), 0.38, 0.85, Color.BLACK),
		"glow": _mat(Color(0.36, 0.86, 0.78), 0.4, 0.0, Color(0.36, 0.86, 0.78) * 3.0),
	}
	_relax_arms()
	_apply_helmet()
	rebuild()


## The helmet and the bare head (mesh nodes in the model), or null.
func part_mesh(part_name: String) -> MeshInstance3D:
	if _model == null:
		return null
	return _model.find_child(part_name, true, false) as MeshInstance3D


func _apply_helmet() -> void:
	var helm: MeshInstance3D = part_mesh("operative_helmet")
	var head: MeshInstance3D = part_mesh("operative_head")
	if helm:
		helm.visible = helmet_on
	if head:
		head.visible = not helmet_on


static func _mat(albedo: Color, rough: float, metal: float, emission: Color) -> StandardMaterial3D:
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.albedo_color = albedo
	m.roughness = rough
	m.metallic = metal
	if emission != Color.BLACK:
		m.emission_enabled = true
		m.emission = emission
	return m


## Clears and re-mounts every part's visible hardware.
func rebuild() -> void:
	for n: Node3D in mounted:
		n.queue_free()
	mounted.clear()
	mounted_ids.clear()
	if loadout == null or skeleton == null:
		return
	for p: PartData in loadout.parts:
		for v: PartVisual in p.visuals:
			if v.scene and v.model_space:
				_mount_model_space(p, v)
				continue
			var node: Node3D = _make_visual(v)
			if node == null:
				continue
			node.name = "%s_%d" % [p.id, mounted.size()]
			_socket(v.socket).add_child(node)
			node.position = v.offset
			node.rotation_degrees = v.rotation_deg
			mounted.append(node)
			mounted_ids.append(p.id)
	repaint()


## Applies `colors` to the suit, the helmet and every mounted piece.
func repaint() -> void:
	if colors == null or _model == null:
		return
	colors.apply_to_model(_model, false)
	for i: int in mounted.size():
		if is_instance_valid(mounted[i]):
			colors.apply_to_part(mounted[i], mounted_ids[i])


## A piece modelled on the whole operative (raw_assets/augments/passives):
## each mesh named "B_<bone>__<piece>" goes on that bone, placed so it sits
## where it was modelled in the rest pose.
func _mount_model_space(p: PartData, v: PartVisual) -> void:
	var root: Node = v.scene.instantiate()
	for n: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		var bone: StringName = bone_from_node_name(mi.name)
		var bi: int = skeleton.find_bone(bone)
		if bi < 0:
			push_warning("BodyAppearance: %s piece %s has no bone '%s'" % [p.id, mi.name, bone])
			continue
		var model_xform: Transform3D = _model_space_xform(mi, root)
		mi.get_parent().remove_child(mi)
		mi.owner = null
		mi.name = "%s_%d" % [p.id, mounted.size()]
		_socket(bone).add_child(mi)
		# BoneAttachment3D sits at the bone's pose; undo its rest so the piece
		# lands where it was modelled (skeleton space = model space).
		mi.transform = skeleton.get_bone_global_rest(bi).affine_inverse() * model_xform
		mounted.append(mi)
		mounted_ids.append(p.id)
	root.free()


## Transform of `n` relative to `root`.
static func _model_space_xform(n: Node3D, root: Node) -> Transform3D:
	var t: Transform3D = n.transform
	var p: Node = n.get_parent()
	while p and p != root:
		var p3: Node3D = p as Node3D
		if p3:
			t = p3.transform * t
		p = p.get_parent()
	return t


## "B_forearm_L__fins" -> &"forearm.L"; "B_chest__plate" -> &"chest".
static func bone_from_node_name(n: String) -> StringName:
	var core: String = n.trim_prefix("B_").get_slice("__", 0)
	if core.ends_with("_L") or core.ends_with("_R"):
		core = core.substr(0, core.length() - 2) + "." + core.right(1)
	return StringName(core)


func _socket(bone: StringName) -> BoneAttachment3D:
	if not _attach.has(bone):
		var a: BoneAttachment3D = BoneAttachment3D.new()
		a.name = "Socket_" + String(bone).replace(".", "_")
		a.bone_name = bone
		skeleton.add_child(a)
		_attach[bone] = a
	return _attach[bone]


func _make_visual(v: PartVisual) -> Node3D:
	if skeleton.find_bone(v.socket) < 0:
		push_warning("BodyAppearance: no socket '%s'" % v.socket)
		return null
	if v.scene:
		return v.scene.instantiate() as Node3D
	var mesh: Mesh
	match v.shape:
		PartVisual.Shape.BOX:
			var b: BoxMesh = BoxMesh.new()
			b.size = v.size
			mesh = b
		PartVisual.Shape.CAPSULE:
			var c: CapsuleMesh = CapsuleMesh.new()
			c.radius = v.size.x
			c.height = maxf(v.size.y, v.size.x * 2.0)
			mesh = c
		PartVisual.Shape.CYLINDER:
			var y: CylinderMesh = CylinderMesh.new()
			y.top_radius = v.size.x
			y.bottom_radius = v.size.x
			y.height = v.size.y
			y.radial_segments = 12
			mesh = y
		_:
			return null
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _mats.get(v.finish, _mats["hardware"])
	return mi


## From the modelling A-pose to a relaxed stance: arms down at the sides,
## elbows slightly bent, fingers half curled.
func _relax_arms() -> void:
	for side: String in ["L", "R"]:
		var i: int = skeleton.find_bone("upper_arm." + side)
		if i < 0:
			continue
		var sx: float = 1.0 if side == "L" else -1.0
		# Rotate about the body's forward axis (+Z in model space).
		_rotate_bone(i, Vector3(0, 0, 1), -deg_to_rad(28.0) * sx)
		var fore: int = skeleton.find_bone("forearm." + side)
		var hand: int = skeleton.find_bone("hand." + side)
		var fingers: int = skeleton.find_bone("fingers." + side)
		if fore < 0 or hand < 0 or fingers < 0:
			continue
		var elbow: Vector3 = skeleton.get_bone_global_rest(fore).origin
		var wrist: Vector3 = skeleton.get_bone_global_rest(hand).origin
		var knuckle: Vector3 = skeleton.get_bone_global_rest(fingers).origin
		var fa: Vector3 = (wrist - elbow).normalized()
		_rotate_bone(fore, fa.cross(Vector3(0, 0, 1)), deg_to_rad(12.0))
		var hd: Vector3 = (knuckle - wrist).normalized()
		var inward: Vector3 = Vector3(-sx, 0, 0)
		var palm: Vector3 = (inward - hd * inward.dot(hd)).normalized()
		_rotate_bone(fingers, hd.cross(palm), deg_to_rad(38.0))


## Rotates bone `i` from its rest pose about a model-space (rest) axis.
func _rotate_bone(i: int, axis_model: Vector3, angle: float) -> void:
	var parent_g: Transform3D = skeleton.get_bone_global_rest(skeleton.get_bone_parent(i))
	var axis_local: Vector3 = (parent_g.basis.inverse() * axis_model).normalized()
	var rest: Quaternion = skeleton.get_bone_rest(i).basis.get_rotation_quaternion()
	skeleton.set_bone_pose_rotation(i, Quaternion(axis_local, angle) * rest)
