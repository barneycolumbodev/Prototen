class_name EnemyGear
extends RefCounted
## What a role wears on his body (EnemyConfig.gear; raw_assets/characters/
## triad_gear): the Shield man's shield and helmet, the Dao swordsman's
## forearm graft, the anti-augment specialist's jammer pack, chest rig and
## respirator, the Gunner's bandoliers, the Firebomber's satchel and bandana.
##
## Every piece is modelled in the local frame of the bone it rides on and
## named "<piece>__<bone>" in the glTF ("." written "_"), so it hangs on a
## BoneAttachment3D with no offset and follows the clips, the aim layer and
## the ragdoll. Pieces on a part that comes off (a severed head or arm) go
## with it; a body blown apart loses them all.

var pieces: Dictionary[StringName, MeshInstance3D] = {}
## The bone each piece rides on.
var bones: Dictionary[StringName, StringName] = {}


static func fit(body: EnemyBody, scene: PackedScene) -> EnemyGear:
	var g: EnemyGear = EnemyGear.new()
	if scene == null:
		return g
	var root: Node3D = scene.instantiate() as Node3D
	for n: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		var parts: PackedStringArray = String(mi.name).split("__")
		if parts.size() < 2:
			continue
		var bone: StringName = bone_name(parts[1])
		if body.skeleton.find_bone(String(bone)) < 0:
			continue
		var xf: Transform3D = BossHardware._local_to(root, mi)
		mi.owner = null
		mi.get_parent().remove_child(mi)
		body.bone_attachment(bone).add_child(mi)
		mi.transform = xf
		mi.name = parts[0]
		# Only the big pieces cast a shadow (perf budget: one shadow light, many men).
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if parts[0] in ["shield", "jammer"] \
				else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		g.pieces[StringName(parts[0])] = mi
		g.bones[StringName(parts[0])] = bone
	root.free()
	return g


## "forearm_L" -> &"forearm.L".
static func bone_name(s: String) -> StringName:
	if s.ends_with("_L") or s.ends_with("_R"):
		return StringName(s.substr(0, s.length() - 2) + "." + s.right(1))
	return StringName(s)


func piece(name: StringName) -> MeshInstance3D:
	var mi: MeshInstance3D = pieces.get(name)
	return mi if mi and is_instance_valid(mi) else null


## A part of the body came off: the pieces on its bones go with it (hidden;
## the gib carries no gear).
func on_severed(bones_off: Array[StringName]) -> void:
	for k: StringName in pieces:
		if bones.get(k, &"") in bones_off:
			var mi: MeshInstance3D = piece(k)
			if mi:
				mi.visible = false


func hide_all() -> void:
	for k: StringName in pieces:
		var mi: MeshInstance3D = piece(k)
		if mi:
			mi.visible = false


## Takes `name` off the body and drops it into the level as a loose rigid
## body (the Shield man's shield when he dies or throws it down).
func drop(name: StringName, level: Node, velocity: Vector3, mass: float, box: Vector3, center: Vector3) -> RigidBody3D:
	var mi: MeshInstance3D = piece(name)
	if mi == null or not mi.visible or level == null:
		return null
	var xf: Transform3D = mi.global_transform
	# Bodies can't be scaled: the man's scale goes on the mesh and the box.
	var sc: Vector3 = xf.basis.get_scale()
	var rb: RigidBody3D = RigidBody3D.new()
	rb.collision_layer = Ballistics.LAYER_DEBRIS
	rb.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	rb.mass = mass
	rb.set_meta(&"surface", &"armor_plate")
	var cs: CollisionShape3D = CollisionShape3D.new()
	var b: BoxShape3D = BoxShape3D.new()
	b.size = box * sc
	cs.shape = b
	cs.position = center * sc
	rb.add_child(cs)
	mi.get_parent().remove_child(mi)
	rb.add_child(mi)
	mi.transform = Transform3D(Basis.from_scale(sc), Vector3.ZERO)
	level.add_child(rb)
	rb.global_transform = Transform3D(xf.basis.orthonormalized(), xf.origin)
	rb.linear_velocity = velocity
	rb.angular_velocity = Vector3(randf_range(-2, 2), randf_range(-2, 2), randf_range(-2, 2))
	rb.add_to_group(&"dropped_guns")
	pieces.erase(name)
	return rb
