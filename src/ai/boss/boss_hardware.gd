class_name BossHardware
extends RefCounted
## The Incense Master's hardware on his body (docs/design.md §8.7a): the
## Gauss prosthetic in place of his right arm from the middle of the upper
## arm down, and the gold pendant on its Cuban chain. Every piece rides on
## its bone (raw_assets/characters/incense_master/build.py models them in
## bone space), so it follows the clips, the aim layer and the ragdoll.
##
## The coils' light is one shared material (`glow`), driven by the brain:
## idle, rising while the arm charges, a flash on the shot. The stones get a
## glint shader. The forearm and the fist are steel: rounds that hit them
## spark off (Enemy.on_plate_hit: a little blunt damage, no wound).

## A view-dependent glint for the diamonds: mostly white-blue fire with hard
## sparkles that flick as he moves or the camera does.
const DIAMOND_SHADER: String = """
shader_type spatial;
render_mode cull_back, shadows_disabled;
varying vec3 v_obj;
float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
void vertex() {
	v_obj = VERTEX;
}
void fragment() {
	float facet = hash(floor(NORMAL * 6.0 + v_obj * 300.0));
	float ndv = abs(dot(NORMAL, VIEW));
	float glint = pow(max(sin(facet * 40.0 + ndv * 30.0 + TIME * 1.7), 0.0), 24.0);
	ALBEDO = vec3(0.86, 0.9, 0.96);
	ROUGHNESS = 0.02;
	METALLIC = 0.2;
	SPECULAR = 1.0;
	EMISSION = vec3(0.7, 0.85, 1.0) * (0.08 + glint * 3.5);
}
"""

## Pieces: node name in the glTF -> the bone it rides on.
const PIECES: Dictionary[StringName, StringName] = {
	&"arm_upper": &"upper_arm.R", &"arm_fore": &"forearm.R", &"arm_hand": &"hand.R", &"pendant": &"chest",
}
## Steel hitboxes over the prosthetic: bone -> [size, centre] in bone space (unscaled rig metres).
const PLATES: Dictionary[StringName, Array] = {
	&"forearm.R": [Vector3(0.2, 0.3, 0.19), Vector3(0.0, 0.14, 0.0)],
	&"hand.R": [Vector3(0.14, 0.17, 0.12), Vector3(0.0, 0.08, 0.0)],
}

var glow: StandardMaterial3D
## Where the slug leaves the rails (follows the forearm).
var muzzle: Node3D
var pieces: Array[MeshInstance3D] = []
var plates: Array[StaticBody3D] = []


static func fit(e: Enemy, cfg: BossConfig) -> BossHardware:
	var hw: BossHardware = BossHardware.new()
	var body: EnemyBody = e.body
	body.replace_right_arm()
	var root: Node3D = cfg.hardware.instantiate() as Node3D
	var diamond: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = DIAMOND_SHADER
	diamond.shader = sh
	for piece: StringName in PIECES:
		var mi: MeshInstance3D = root.find_child(String(piece), true, false) as MeshInstance3D
		if mi == null:
			continue
		var xf: Transform3D = _local_to(root, mi)
		mi.owner = null
		mi.get_parent().remove_child(mi)
		var att: BoneAttachment3D = body.bone_attachment(PIECES[piece])
		att.add_child(mi)
		mi.transform = xf
		if piece == &"pendant":
			mi.position += cfg.pendant_offset
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i: int in mi.mesh.get_surface_count():
			var m: Material = mi.mesh.surface_get_material(i)
			if m == null:
				continue
			if m.resource_name == "im_glow":
				if hw.glow == null:
					hw.glow = (m as StandardMaterial3D).duplicate() as StandardMaterial3D
					hw.glow.emission_enabled = true
					hw.glow.emission = cfg.glow_color
					hw.glow.emission_energy_multiplier = cfg.glow_idle
				mi.set_surface_override_material(i, hw.glow)
			elif m.resource_name == "im_diamond":
				mi.set_surface_override_material(i, diamond)
		hw.pieces.append(mi)
	var mz: Node3D = root.find_child("muzzle", true, false) as Node3D
	if mz:
		var mxf: Transform3D = _local_to(root, mz)
		mz.owner = null
		mz.get_parent().remove_child(mz)
		var fore: BoneAttachment3D = body.bone_attachment(&"forearm.R")
		fore.add_child(mz)
		mz.transform = mxf
		hw.muzzle = mz
	root.free()
	for bone: StringName in PLATES:
		var spec: Array = PLATES[bone]
		var plate: StaticBody3D = StaticBody3D.new()
		plate.name = "Prosthetic_" + String(bone).replace(".", "_")
		plate.collision_layer = Ballistics.LAYER_HITBOX
		plate.collision_mask = 0
		plate.set_meta(&"surface", &"armor_plate")
		plate.set_meta(&"armor", true)
		plate.set_meta(&"prosthetic", true)
		plate.set_script(preload("res://src/ai/armor_plate.gd"))
		plate.set(&"target", e)
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = spec[0]
		cs.shape = box
		plate.add_child(cs)
		plate.position = spec[1]
		body.bone_attachment(bone).add_child(plate)
		body.add_plate(plate)
		hw.plates.append(plate)
	return hw


## `node`'s transform relative to `root` (neither in the tree).
static func _local_to(root: Node3D, node: Node3D) -> Transform3D:
	var t: Transform3D = node.transform
	var p: Node = node.get_parent()
	while p != null and p != root:
		var n3: Node3D = p as Node3D
		if n3:
			t = n3.transform * t
		p = p.get_parent()
	return t


## The coils' light (energy multiplier).
func set_glow(energy: float) -> void:
	if glow:
		glow.emission_energy_multiplier = energy


func glow_energy() -> float:
	return glow.emission_energy_multiplier if glow else 0.0


## The slug's start and the way the rails point (world).
func muzzle_transform() -> Transform3D:
	if muzzle and muzzle.is_inside_tree():
		return muzzle.global_transform
	return Transform3D.IDENTITY


## Off: the plates stop taking hits (he's gone; burst() turns off the body's own).
func disable_plates() -> void:
	for p: StaticBody3D in plates:
		p.collision_layer = 0
