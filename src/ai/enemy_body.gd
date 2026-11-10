class_name EnemyBody
extends Node3D
## The visible, hittable body of a triad enemy (assets/characters/triad):
## - the skinned model with a per-enemy material (role tints, painted wounds,
##   char), the gun in the right hand, the plate carrier for Enforcers;
## - 19 damage zones on bones (docs/design.md §5.1) that forward hits to the
##   owner (`on_part_hit`), plus steel plates in the carrier;
## - the animation tree (stance clips, walk blend space, reload and stumble
##   one-shots) and the procedural aim/flinch layer (EnemyPose);
## - a ragdoll (PhysicalBoneSimulator3D) for death, frozen after a few seconds;
## - dismemberment: swaps to pre-cut parts with flesh caps and throws the
##   severed part as a gib (Gore).
## Faces +Z; its left is +X.

signal ragdoll_frozen

const MODEL: PackedScene = preload("res://assets/characters/triad/triad.gltf")
const SHADER: Shader = preload("res://src/ai/triad.gdshader")
const TEX_BASE: Texture2D = preload("res://assets/characters/triad/textures/triad_basecolor.png")
const TEX_ORM: Texture2D = preload("res://assets/characters/triad/textures/triad_orm.png")
const TEX_NORMAL: Texture2D = preload("res://assets/characters/triad/textures/triad_normal.png")
const TEX_MASK: Texture2D = preload("res://assets/characters/triad/textures/triad_mask.png")
const MAX_WOUNDS: int = 8

## zone -> [bone, shape ("sphere" r | "capsule" r,h | "box" size), offset in bone space]
const ZONES: Dictionary[StringName, Array] = {
	&"head": [&"head", "sphere", Vector3(0.1, 0, 0), Vector3(0, 0.093, 0.012)],
	&"neck": [&"neck", "capsule", Vector3(0.052, 0.13, 0), Vector3(0, 0.05, 0)],
	&"chest": [&"chest", "box", Vector3(0.36, 0.23, 0.25), Vector3(0, 0.1, 0.01)],
	&"stomach": [&"spine", "box", Vector3(0.32, 0.17, 0.23), Vector3(0, 0.085, 0)],
	&"pelvis": [&"hips", "box", Vector3(0.34, 0.19, 0.23), Vector3(0, -0.005, 0)],
	&"l_upper_arm": [&"upper_arm.L", "capsule", Vector3(0.056, 0.32, 0), Vector3(0, 0.15, 0)],
	&"r_upper_arm": [&"upper_arm.R", "capsule", Vector3(0.056, 0.32, 0), Vector3(0, 0.15, 0)],
	&"l_forearm": [&"forearm.L", "capsule", Vector3(0.046, 0.29, 0), Vector3(0, 0.13, 0)],
	&"r_forearm": [&"forearm.R", "capsule", Vector3(0.046, 0.29, 0), Vector3(0, 0.13, 0)],
	&"l_hand": [&"hand.L", "capsule", Vector3(0.04, 0.17, 0), Vector3(0, 0.07, 0)],
	&"r_hand": [&"hand.R", "capsule", Vector3(0.04, 0.17, 0), Vector3(0, 0.07, 0)],
	&"l_thigh": [&"thigh.L", "capsule", Vector3(0.083, 0.46, 0), Vector3(0, 0.21, 0)],
	&"r_thigh": [&"thigh.R", "capsule", Vector3(0.083, 0.46, 0), Vector3(0, 0.21, 0)],
	&"l_shin": [&"shin.L", "capsule", Vector3(0.06, 0.44, 0), Vector3(0, 0.21, 0)],
	&"r_shin": [&"shin.R", "capsule", Vector3(0.06, 0.44, 0), Vector3(0, 0.21, 0)],
	&"l_foot": [&"foot.L", "capsule", Vector3(0.045, 0.22, 0), Vector3(0, 0.04, 0)],
	&"r_foot": [&"foot.R", "capsule", Vector3(0.045, 0.22, 0), Vector3(0, 0.04, 0)],
}

## Ragdoll bodies: bone -> [radius, length, joint, swing/upper deg, twist/lower deg, mass kg]
const RAGDOLL: Dictionary[StringName, Array] = {
	&"hips": [0.13, 0.2, "none", 0.0, 0.0, 11.0],
	&"spine": [0.12, 0.17, "cone", 22.0, 12.0, 7.0],
	&"chest": [0.14, 0.22, "cone", 18.0, 12.0, 11.0],
	&"head": [0.1, 0.2, "cone", 40.0, 35.0, 5.0],
	&"upper_arm.L": [0.055, 0.3, "cone", 75.0, 40.0, 2.4],
	&"upper_arm.R": [0.055, 0.3, "cone", 75.0, 40.0, 2.4],
	&"forearm.L": [0.045, 0.26, "hinge", 140.0, -2.0, 1.6],
	&"forearm.R": [0.045, 0.26, "hinge", 140.0, -2.0, 1.6],
	&"thigh.L": [0.08, 0.43, "cone", 55.0, 20.0, 8.5],
	&"thigh.R": [0.08, 0.43, "cone", 55.0, 20.0, 8.5],
	&"shin.L": [0.06, 0.42, "hinge", 2.0, -140.0, 4.0],
	&"shin.R": [0.06, 0.42, "hinge", 2.0, -140.0, 4.0],
}

## Severable parts: part -> [mesh node, bone the gib follows, zones it takes].
const PARTS: Dictionary[StringName, Array] = {
	&"head": [&"part_head", &"head", [&"head", &"neck"]],
	&"forearm_L": [&"part_forearm_L", &"forearm.L", [&"l_forearm", &"l_hand"]],
	&"forearm_R": [&"part_forearm_R", &"forearm.R", [&"r_forearm", &"r_hand"]],
	&"shin_L": [&"part_shin_L", &"shin.L", [&"l_shin", &"l_foot"]],
	&"shin_R": [&"part_shin_R", &"shin.R", [&"r_shin", &"r_foot"]],
}

const STANCES: Array[StringName] = [&"loco", &"run", &"idle", &"cover", &"crouch_aim", &"blind_fire",
		&"gut", &"crawl", &"surrender", &"flee", &"cower"]
const LOOPS: Array[StringName] = [&"aim", &"idle", &"walk_f", &"walk_b", &"walk_l", &"walk_r", &"run", &"cover",
		&"crouch_aim", &"blind_fire", &"gut", &"crawl", &"surrender", &"flee", &"cower"]
const UPPER_BONES: Array[StringName] = [&"spine", &"chest", &"neck", &"head", &"clavicle.L", &"clavicle.R",
		&"upper_arm.L", &"upper_arm.R", &"forearm.L", &"forearm.R", &"hand.L", &"hand.R", &"fingers.L", &"fingers.R", &"weapon"]
## Clip speeds (raw_assets/characters/triad/build.py): walk 1.4 m/s, run 4.6 m/s, flee 5.2, crawl 0.45.
const WALK_CLIP_SPEED: float = 1.4
const RUN_CLIP_SPEED: float = 4.6
const FLEE_CLIP_SPEED: float = 5.2
const CRAWL_CLIP_SPEED: float = 0.45

static var _rest_meshes: Dictionary[StringName, ArrayMesh] = {}

## The enemy that owns this body (gets on_part_hit / on_part_burn).
var owner_node: Node
var config: EnemyConfig
var skeleton: Skeleton3D
var pose: EnemyPose
var hitboxes: Dictionary[StringName, HitboxPart] = {}
var material: ShaderMaterial
var gun: Node3D
var stance: StringName = &"idle"
var ragdolling: bool = false
var frozen: bool = false
var severed: Dictionary[StringName, bool] = {}
## Held by the mesh arm (NT-5): the ragdoll never freezes while this is set.
var hold_awake: bool = false

var _model: Node3D
var _tree: AnimationTree
var _sim: PhysicalBoneSimulator3D
var _bones: Dictionary[StringName, PhysicalBone3D] = {}
var _meshes: Dictionary[StringName, MeshInstance3D] = {}
var _gun_socket: BoneAttachment3D
var _wounds: PackedVector4Array = PackedVector4Array()
var _wound_age: PackedFloat32Array = PackedFloat32Array()
var _ragdoll_time: float = 0.0
var _split: bool = false
var _plates: Array[StaticBody3D] = []
## Bone attachments by bone name. Their transforms include the ragdoll and
## the aim layer (Skeleton3D.get_bone_global_pose() doesn't, outside modifiers).
var _attach: Dictionary[StringName, BoneAttachment3D] = {}


func setup(p_owner: Node, p_config: EnemyConfig) -> void:
	owner_node = p_owner
	config = p_config


func _ready() -> void:
	_model = MODEL.instantiate() as Node3D
	# Uniform scale: the skinned mesh, hitboxes, gun and ragdoll joints follow
	# it (test_enemies_are_bigger_and_ragdoll_keeps_proportions).
	_model.scale = Vector3.ONE * config.body_scale
	add_child(_model)
	skeleton = _model.find_child("Skeleton3D", true, false) as Skeleton3D
	_setup_meshes()
	_setup_hitboxes()
	_setup_gun()
	_setup_animation()
	pose = EnemyPose.new()
	pose.name = "EnemyPose"
	skeleton.add_child(pose)
	_setup_ragdoll()


# ------------------------------------------------------------------ public

func set_stance(s: StringName) -> void:
	if ragdolling or (s == stance and _tree.get(&"parameters/stance/current_state") == String(s)):
		return
	stance = s
	_tree.set(&"parameters/stance/transition_request", String(s))


## Movement in the body's space (x = his left, z = forward), m/s.
func set_motion(local_velocity: Vector3) -> void:
	if ragdolling:
		return
	var speed: float = Vector2(local_velocity.x, local_velocity.z).length()
	var dir: Vector2 = Vector2(local_velocity.x, local_velocity.z) / maxf(speed, 0.001)
	var amount: float = clampf(speed / WALK_CLIP_SPEED, 0.0, 1.0)
	_tree.set(&"parameters/walk/blend_position", dir * amount)
	_tree.set(&"parameters/walk_speed/scale", clampf(speed / WALK_CLIP_SPEED, 0.6, 1.6) if speed > 0.2 else 1.0)
	var run_scale: float = speed / (FLEE_CLIP_SPEED if stance == &"flee" else RUN_CLIP_SPEED)
	_tree.set(&"parameters/run_speed/scale", clampf(run_scale, 0.5, 1.4))
	_tree.set(&"parameters/run_speed_flee/scale", clampf(run_scale, 0.5, 1.4))
	_tree.set(&"parameters/crawl_speed/scale", clampf(speed / CRAWL_CLIP_SPEED, 0.2, 1.6) if speed > 0.05 else 0.25)


func play_reload() -> void:
	_tree.set(&"parameters/reload/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func play_stumble() -> void:
	_tree.set(&"parameters/react/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func set_aim(yaw: float, pitch: float, weight: float = 1.0) -> void:
	pose.aim_yaw = clampf(yaw, -1.2, 1.2)
	pose.aim_pitch = clampf(pitch, -0.9, 0.9)
	pose.aim_weight = weight


## Global transform of the muzzle (gun forward = +X of the model).
func muzzle_transform() -> Transform3D:
	if gun == null:
		return global_transform
	var t: Transform3D = gun.global_transform
	return Transform3D(t.basis, t * config.muzzle)


func muzzle_direction() -> Vector3:
	return gun.global_basis.x.normalized() if gun else global_basis.z


func bone_position(bone: StringName) -> Vector3:
	return bone_global(bone).origin


## The bone's world transform as shown (animation, aim layer and ragdoll included).
func bone_global(bone: StringName) -> Transform3D:
	if _attach.has(bone):
		return _attach[bone].global_transform
	var i: int = skeleton.find_bone(bone)
	var parent: int = skeleton.get_bone_parent(i)
	if parent >= 0:
		return bone_global(skeleton.get_bone_name(parent)) * skeleton.get_bone_pose(i)
	return skeleton.global_transform * skeleton.get_bone_global_pose(i)


func head_position() -> Vector3:
	return hitboxes[&"head"].global_position


func chest_position() -> Vector3:
	return hitboxes[&"chest"].global_position


## Bullets of this enemy's own gun must not hit his own body.
func ballistic_exclude() -> Array[RID]:
	var out: Array[RID] = []
	for h: HitboxPart in hitboxes.values():
		out.append(h.get_rid())
	for p: StaticBody3D in _plates:
		out.append(p.get_rid())
	return out


func set_char(amount: float) -> void:
	material.set_shader_parameter(&"char_amount", clampf(amount, 0.0, 1.0))


## 1 = rim light on (alive), 0 = off. Tweened by the enemy when he dies.
func set_rim(amount: float) -> void:
	material.set_shader_parameter(&"rim_alive", clampf(amount, 0.0, 1.0))


func set_bloodied(amount: float) -> void:
	material.set_shader_parameter(&"bloodied", clampf(amount, 0.0, 1.0))


## Paints a wound where `hit_point` is on zone `zone` (radius m; exit = torn open).
func add_wound(zone: StringName, hit_point: Vector3, radius: float, exit_wound: bool) -> void:
	if not Gore.is_on():
		return
	var spec: Array = ZONES.get(zone, [])
	if spec.is_empty():
		return
	var zone_bone: StringName = spec[0]
	var bi: int = skeleton.find_bone(zone_bone)
	# Back into the rest pose: rest_global * pose_global⁻¹ * skeleton⁻¹.
	var to_rest: Transform3D = skeleton.global_transform * skeleton.get_bone_global_rest(bi)
	to_rest = skeleton.global_transform.affine_inverse() * to_rest * bone_global(zone_bone).affine_inverse()
	var p: Vector3 = to_rest * hit_point
	var w: Vector4 = Vector4(p.x, p.y, p.z, -radius if exit_wound else radius)
	if _wounds.size() >= MAX_WOUNDS:
		# Merge into the nearest one instead of dropping it: bigger, fresher.
		var best: int = 0
		var best_d: float = INF
		for i: int in _wounds.size():
			var d: float = Vector3(_wounds[i].x, _wounds[i].y, _wounds[i].z).distance_to(p)
			if d < best_d:
				best_d = d
				best = i
		var old: Vector4 = _wounds[best]
		_wounds[best] = Vector4(old.x, old.y, old.z, signf(old.w) * minf(absf(old.w) * 1.15 + radius * 0.3, 0.05))
	else:
		_wounds.append(w)
		_wound_age.append(0.0)
	_push_wounds()


func wound_count() -> int:
	return _wounds.size()


func flinch(dir: Vector3, strength: float, head: bool) -> void:
	var local_dir: Vector3 = skeleton.global_basis.inverse() * dir
	pose.flinch(local_dir, (0.12 if head else 0.2) * strength, (0.35 if head else 0.1) * strength)


# ------------------------------------------------------------------ ragdoll

## Goes limp. `impulse` (N·s, world) is applied at `point` on the bone nearest `zone`.
func ragdoll(impulse: Vector3, point: Vector3, zone: StringName) -> void:
	if ragdolling:
		return
	ragdolling = true
	frozen = false
	_ragdoll_time = 0.0
	# The tree keeps running underneath: it keeps the skeleton updating, and
	# the simulator (influence 1) overrides it.
	pose.active = false
	_sim.active = true
	_sim.influence = 1.0
	_sim.physical_bones_start_simulation()
	add_to_group(&"ragdolls_active")
	RagdollBudget.started(self)
	push_bone(zone, impulse, point)


## Pushes the ragdoll (a corpse being shot). Wakes it if it was frozen.
func push_bone(zone: StringName, impulse: Vector3, point: Vector3) -> void:
	if not ragdolling:
		return
	if frozen:
		unfreeze()
	var pb: PhysicalBone3D = _nearest_body(zone, point)
	if pb:
		pb.apply_impulse(impulse, point - pb.global_position)


## The ragdoll's chest (what the mesh arm holds), or null.
func chest_body() -> PhysicalBone3D:
	return _bones.get(&"chest", _bones.get(&"spine"))


## Pulls the ragdoll's chest toward `target`; the limbs trail behind.
func drag_to(target: Vector3, rate: float, max_speed: float) -> void:
	var pb: PhysicalBone3D = chest_body()
	if pb == null or not ragdolling:
		return
	if frozen:
		unfreeze()
	pb.linear_velocity = ((target - pb.global_position) * rate).limit_length(max_speed)
	pb.angular_velocity *= 0.9


## Throws the whole ragdoll.
func fling(velocity: Vector3) -> void:
	if not ragdolling:
		return
	if frozen:
		unfreeze()
	for pb: PhysicalBone3D in _bones.values():
		pb.linear_velocity = velocity


func chest_velocity() -> Vector3:
	var pb: PhysicalBone3D = chest_body()
	return pb.linear_velocity if pb and ragdolling else Vector3.ZERO


func is_simulating() -> bool:
	return ragdolling and not frozen


## Stops simulating but keeps the pose (cheap from here on).
func freeze() -> void:
	if not ragdolling or frozen or hold_awake:
		return
	# Local poses from what's shown (the simulated bones), parents first.
	var inv: Transform3D = skeleton.global_transform.affine_inverse()
	var globals: Array[Transform3D] = []
	var poses: Array[Transform3D] = []
	for i: int in skeleton.get_bone_count():
		var name_i: StringName = skeleton.get_bone_name(i)
		var parent: int = skeleton.get_bone_parent(i)
		var g: Transform3D
		if _attach.has(name_i):
			g = inv * _attach[name_i].global_transform
		elif parent >= 0:
			g = globals[parent] * skeleton.get_bone_pose(i)
		else:
			g = skeleton.get_bone_global_pose(i)
		globals.append(g)
		poses.append(globals[parent].affine_inverse() * g if parent >= 0 else g)
	_sim.physical_bones_stop_simulation()
	_sim.active = false
	_tree.active = false
	for i: int in skeleton.get_bone_count():
		skeleton.set_bone_pose(i, poses[i])
	frozen = true
	remove_from_group(&"ragdolls_active")
	RagdollBudget.stopped(self)
	ragdoll_frozen.emit()


func unfreeze() -> void:
	if not frozen:
		return
	frozen = false
	_ragdoll_time = 0.0
	_tree.active = true
	_sim.active = true
	_sim.physical_bones_start_simulation()
	add_to_group(&"ragdolls_active")
	RagdollBudget.started(self)


func _process(delta: float) -> void:
	pose.step_springs(delta)
	if ragdolling and not frozen:
		_ragdoll_time += delta
		if _ragdoll_time > RagdollBudget.FREEZE_AFTER and _settled():
			freeze()
		elif _ragdoll_time > RagdollBudget.FREEZE_AFTER * 2.0:
			freeze()
	if not _wounds.is_empty():
		for i: int in _wound_age.size():
			_wound_age[i] += delta
		material.set_shader_parameter(&"wound_age", _wound_age)


func _settled() -> bool:
	for pb: PhysicalBone3D in _bones.values():
		if pb.linear_velocity.length() > 0.35:
			return false
	return true


func _nearest_body(zone: StringName, point: Vector3) -> PhysicalBone3D:
	var spec: Array = ZONES.get(zone, [])
	var bone: StringName = spec[0] if not spec.is_empty() else &"chest"
	var chain: StringName = bone
	while not _bones.has(chain):
		var i: int = skeleton.find_bone(chain)
		var parent: int = skeleton.get_bone_parent(i) if i >= 0 else -1
		if parent < 0:
			break
		chain = skeleton.get_bone_name(parent)
	if _bones.has(chain):
		return _bones[chain]
	var best: PhysicalBone3D
	var best_d: float = INF
	for pb: PhysicalBone3D in _bones.values():
		var d: float = pb.global_position.distance_to(point)
		if d < best_d:
			best_d = d
			best = pb
	return best


# ------------------------------------------------------------------ dismemberment

## Cuts `part` off. `destroy` = blown apart (head shots from heavy rounds):
## no gib, chunks instead. Returns false if already gone.
func sever(part: StringName, velocity: Vector3, destroy: bool) -> bool:
	if severed.has(part) or not PARTS.has(part):
		return false
	severed[part] = true
	if not _split:
		_split = true
		_meshes[&"triad"].visible = false
		for p: StringName in [&"part_body", &"part_head", &"part_forearm_L", &"part_forearm_R", &"part_shin_L", &"part_shin_R"]:
			_meshes[p].visible = true
	var spec: Array = PARTS[part]
	var mesh_name: StringName = spec[0]
	var mi: MeshInstance3D = _meshes[mesh_name]
	mi.visible = false
	for z: StringName in spec[2]:
		if hitboxes.has(z):
			hitboxes[z].collision_layer = 0
	var bone: StringName = spec[1]
	var bi: int = skeleton.find_bone(bone)
	var shown: Transform3D = bone_global(bone)
	var xform: Transform3D = shown * skeleton.get_bone_global_rest(bi).affine_inverse()
	var at: Vector3 = shown.origin
	if destroy:
		Gore.burst_chunks(at + Vector3.UP * 0.08, velocity.normalized() + Vector3.UP * 0.3, 10, 6.0)
		Gore.mist(at + Vector3.UP * 0.08, velocity.normalized(), 2.5)
		Gore.spray(at + Vector3.UP * 0.08, velocity.normalized() + Vector3.UP * 0.4, 2.2, 40)
	else:
		var radius: float = 0.11 if part == &"head" else 0.06
		Gore.throw_gib(mi.mesh, xform, velocity, Vector3(randf_range(-8, 8), randf_range(-8, 8), randf_range(-8, 8)), radius, material)
	if part == &"forearm_R" and gun:
		drop_gun(velocity * 0.3)
	return true


func is_severed(part: StringName) -> bool:
	return severed.has(part)


## Where the stump of `part` is and which way it points (for bleeding).
func stump(part: StringName) -> Transform3D:
	var spec: Array = PARTS[part]
	var bone: StringName = spec[1]
	var t: Transform3D = bone_global(bone)
	if part == &"head":
		# The head bone's parent (neck) is what bleeds.
		t = bone_global(&"neck")
		t.origin = t * Vector3(0, 0.06, 0)
		return t
	t.origin = t * Vector3(0, 0.09, 0)
	t.basis = Basis(t.basis.x, -t.basis.y, -t.basis.z)
	return t


# ------------------------------------------------------------------ gun

func drop_gun(velocity: Vector3) -> RigidBody3D:
	if gun == null:
		return null
	var xform: Transform3D = gun.global_transform
	var body: RigidBody3D = RigidBody3D.new()
	body.collision_layer = Ballistics.LAYER_DEBRIS
	body.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	body.mass = 3.5
	body.set_meta(&"surface", &"sheet_metal")
	var cs: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(0.75, 0.12, 0.05)
	cs.shape = box
	cs.position = Vector3(0.12, 0.0, 0.0)
	body.add_child(cs)
	gun.get_parent().remove_child(gun)
	body.add_child(gun)
	gun.transform = Transform3D.IDENTITY
	# Into the level (the enemy's parent), so it outlives the enemy.
	var level: Node = owner_node.get_parent() if owner_node and owner_node.get_parent() else get_tree().root
	level.add_child(body)
	body.global_transform = xform
	body.linear_velocity = velocity
	body.angular_velocity = Vector3(randf_range(-4, 4), randf_range(-4, 4), randf_range(-4, 4))
	body.add_to_group(&"dropped_guns")
	gun = null
	return body


# ------------------------------------------------------------------ build

func _setup_meshes() -> void:
	material = ShaderMaterial.new()
	material.shader = SHADER
	material.set_shader_parameter(&"base_tex", TEX_BASE)
	material.set_shader_parameter(&"orm_tex", TEX_ORM)
	material.set_shader_parameter(&"normal_tex", TEX_NORMAL)
	material.set_shader_parameter(&"mask_tex", TEX_MASK)
	material.set_shader_parameter(&"jacket_tint", config.jacket_tint)
	material.set_shader_parameter(&"trousers_tint", config.trousers_tint)
	material.set_shader_parameter(&"skin_tint", config.skin_tint)
	material.set_shader_parameter(&"wound_count", 0)
	material.set_shader_parameter(&"rim_color", config.rim_color)
	material.set_shader_parameter(&"rim_strength", config.rim_strength)
	var empty_w: PackedVector4Array = PackedVector4Array()
	empty_w.resize(MAX_WOUNDS)
	material.set_shader_parameter(&"wounds", empty_w)
	for child: Node in skeleton.get_children():
		var mi: MeshInstance3D = child as MeshInstance3D
		if mi == null:
			continue
		mi.mesh = rest_mesh(StringName(mi.name), mi.mesh)
		mi.material_override = material
		_meshes[StringName(mi.name)] = mi
		mi.visible = mi.name == "triad" or (mi.name == "vest" and config.plate_carrier)


## A copy of `mesh` with every vertex's rest position in CUSTOM0 (the shader
## paints wounds in rest space). Built once per mesh and shared.
static func rest_mesh(key: StringName, mesh: Mesh) -> ArrayMesh:
	if _rest_meshes.has(key):
		return _rest_meshes[key]
	var out: ArrayMesh = ArrayMesh.new()
	for s: int in mesh.get_surface_count():
		var arrays: Array = mesh.surface_get_arrays(s)
		var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var custom: PackedFloat32Array = PackedFloat32Array()
		custom.resize(verts.size() * 3)
		for i: int in verts.size():
			custom[i * 3] = verts[i].x
			custom[i * 3 + 1] = verts[i].y
			custom[i * 3 + 2] = verts[i].z
		arrays[Mesh.ARRAY_CUSTOM0] = custom
		var flags: int = Mesh.ARRAY_CUSTOM_RGB_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
		var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES] if arrays[Mesh.ARRAY_BONES] is PackedInt32Array else PackedInt32Array()
		if bones.size() == verts.size() * 8:
			flags |= Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
	_rest_meshes[key] = out
	return out


func _push_wounds() -> void:
	var w: PackedVector4Array = _wounds.duplicate()
	w.resize(MAX_WOUNDS)
	var a: PackedFloat32Array = _wound_age.duplicate()
	a.resize(MAX_WOUNDS)
	material.set_shader_parameter(&"wounds", w)
	material.set_shader_parameter(&"wound_age", a)
	material.set_shader_parameter(&"wound_count", _wounds.size())


func _setup_hitboxes() -> void:
	var attachments: Dictionary[StringName, BoneAttachment3D] = {}
	for zone: StringName in ZONES:
		var spec: Array = ZONES[zone]
		var bone: StringName = spec[0]
		var att: BoneAttachment3D = attachments.get(bone)
		if att == null:
			att = BoneAttachment3D.new()
			att.name = "Att_" + String(bone).replace(".", "_")
			att.bone_name = bone
			skeleton.add_child(att)
			attachments[bone] = att
			_attach[bone] = att
		var part: HitboxPart = HitboxPart.new()
		part.name = String(zone)
		part.target = owner_node
		part.collision_layer = Ballistics.LAYER_HITBOX
		part.collision_mask = 0
		part.set_meta(&"zone", zone)
		part.set_meta(&"surface", &"flesh")
		part.set_meta(&"bone", bone)
		part.add_to_group(&"gore_body")
		part.position = spec[3]
		var cs: CollisionShape3D = CollisionShape3D.new()
		var dims: Vector3 = spec[2]
		var kind: String = spec[1]
		match kind:
			"sphere":
				var sp: SphereShape3D = SphereShape3D.new()
				sp.radius = dims.x
				cs.shape = sp
			"capsule":
				var c: CapsuleShape3D = CapsuleShape3D.new()
				c.radius = dims.x
				c.height = maxf(dims.y, dims.x * 2.0 + 0.01)
				cs.shape = c
			_:
				var b: BoxShape3D = BoxShape3D.new()
				b.size = dims
				cs.shape = b
		part.add_child(cs)
		att.add_child(part)
		hitboxes[zone] = part
	if config.plate_carrier:
		# Steel plates in the carrier, front and back (data/surfaces/armor_plate.tres).
		var att_chest: BoneAttachment3D = attachments[&"chest"]
		for z: float in [0.158, -0.152]:
			var plate: StaticBody3D = StaticBody3D.new()
			plate.name = "Plate" + ("Front" if z > 0 else "Back")
			plate.collision_layer = Ballistics.LAYER_HITBOX
			plate.collision_mask = 0
			plate.set_meta(&"surface", &"armor_plate")
			plate.set_meta(&"dynamic_holes", true)
			plate.set_meta(&"armor", true)
			plate.set_script(preload("res://src/ai/armor_plate.gd"))
			plate.set(&"target", owner_node)
			var cs: CollisionShape3D = CollisionShape3D.new()
			var b: BoxShape3D = BoxShape3D.new()
			b.size = Vector3(0.26, 0.31, 0.008)
			cs.shape = b
			plate.add_child(cs)
			plate.position = Vector3(0, 0.03, z)
			att_chest.add_child(plate)
			_plates.append(plate)


func _setup_gun() -> void:
	_gun_socket = BoneAttachment3D.new()
	_gun_socket.name = "GunSocket"
	_gun_socket.bone_name = &"weapon"
	skeleton.add_child(_gun_socket)
	_attach[&"weapon"] = _gun_socket
	if config.gun_scene:
		gun = config.gun_scene.instantiate() as Node3D
		# Gun model: +X muzzle, +Y up, +Z its right. Weapon bone: +Y along the barrel, +Z up, +X right.
		gun.transform = Transform3D(Basis(Vector3(0, 1, 0), Vector3(0, 0, 1), Vector3(1, 0, 0)), Vector3.ZERO)
		_gun_socket.add_child(gun)


func _setup_animation() -> void:
	var ap: AnimationPlayer = _model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	for clip: StringName in LOOPS:
		if ap.has_animation(clip):
			ap.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	var root: AnimationNodeBlendTree = AnimationNodeBlendTree.new()
	var walk: AnimationNodeBlendSpace2D = AnimationNodeBlendSpace2D.new()
	walk.add_blend_point(_anim(&"aim"), Vector2.ZERO, -1, &"aim")
	walk.add_blend_point(_anim(&"walk_f"), Vector2(0, 1), -1, &"walk_f")
	walk.add_blend_point(_anim(&"walk_b"), Vector2(0, -1), -1, &"walk_b")
	walk.add_blend_point(_anim(&"walk_l"), Vector2(1, 0), -1, &"walk_l")
	walk.add_blend_point(_anim(&"walk_r"), Vector2(-1, 0), -1, &"walk_r")
	root.add_node(&"walk", walk)
	root.add_node(&"walk_speed", AnimationNodeTimeScale.new())
	root.connect_node(&"walk_speed", 0, &"walk")
	var trans: AnimationNodeTransition = AnimationNodeTransition.new()
	trans.xfade_time = 0.3
	for s: StringName in STANCES:
		trans.add_input(String(s))
	root.add_node(&"stance", trans)
	root.connect_node(&"stance", 0, &"walk_speed")
	for i: int in STANCES.size():
		var s: StringName = STANCES[i]
		if s == &"loco":
			continue
		var clip_node: StringName = StringName("clip_" + String(s))
		root.add_node(clip_node, _anim(s))
		var src: StringName = clip_node
		if s == &"run" or s == &"flee" or s == &"crawl":
			var ts_name: StringName = &"crawl_speed" if s == &"crawl" else StringName(String(s) + "_speed")
			if s == &"flee":
				ts_name = &"run_speed_flee"
			root.add_node(ts_name, AnimationNodeTimeScale.new())
			root.connect_node(ts_name, 0, clip_node)
			src = ts_name
		root.connect_node(&"stance", i, src)
	var react: AnimationNodeOneShot = AnimationNodeOneShot.new()
	react.fadein_time = 0.08
	react.fadeout_time = 0.25
	root.add_node(&"react", react)
	root.add_node(&"clip_stumble", _anim(&"stumble"))
	root.connect_node(&"react", 0, &"stance")
	root.connect_node(&"react", 1, &"clip_stumble")
	var reload: AnimationNodeOneShot = AnimationNodeOneShot.new()
	reload.fadein_time = 0.15
	reload.fadeout_time = 0.2
	reload.filter_enabled = true
	var sk_path: String = String(_model.get_path_to(skeleton))
	for b: StringName in UPPER_BONES:
		reload.set_filter_path(NodePath(sk_path + ":" + String(b)), true)
	root.add_node(&"reload", reload)
	root.add_node(&"clip_reload", _anim(&"reload"))
	root.connect_node(&"reload", 0, &"react")
	root.connect_node(&"reload", 1, &"clip_reload")
	root.connect_node(&"output", 0, &"reload")
	_tree = AnimationTree.new()
	_tree.name = "AnimationTree"
	_tree.tree_root = root
	_model.add_child(_tree)
	_tree.root_node = NodePath("..")
	_tree.anim_player = _tree.get_path_to(ap)
	_tree.active = true
	_tree.set(&"parameters/stance/transition_request", String(stance))


func _anim(clip: StringName) -> AnimationNodeAnimation:
	var a: AnimationNodeAnimation = AnimationNodeAnimation.new()
	a.animation = clip
	return a


func _setup_ragdoll() -> void:
	_sim = PhysicalBoneSimulator3D.new()
	_sim.name = "Ragdoll"
	skeleton.add_child(_sim)
	for bone: StringName in RAGDOLL:
		var spec: Array = RAGDOLL[bone]
		var radius: float = spec[0]
		var length: float = spec[1]
		var pb: PhysicalBone3D = PhysicalBone3D.new()
		pb.name = "PB_" + String(bone).replace(".", "_")
		pb.set(&"bone_name", String(bone))
		pb.mass = spec[5]
		pb.friction = 0.8
		pb.linear_damp = 0.1
		pb.angular_damp = 1.2
		pb.collision_layer = Ballistics.LAYER_RAGDOLL
		pb.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS
		# Body at the bone's middle, same orientation as the bone (capsule along Y).
		pb.body_offset = Transform3D(Basis(), Vector3(0, length * 0.5, 0))
		pb.joint_offset = Transform3D(Basis(), Vector3(0, -length * 0.5, 0))
		var cs: CollisionShape3D = CollisionShape3D.new()
		var cap: CapsuleShape3D = CapsuleShape3D.new()
		cap.radius = radius
		cap.height = maxf(length, radius * 2.0 + 0.01)
		cs.shape = cap
		pb.add_child(cs)
		var joint: String = spec[2]
		match joint:
			"cone":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_CONE
				pb.joint_rotation = Vector3(0, 0, PI * 0.5)  # twist axis (X) along the bone
				pb.set(&"joint_constraints/swing_span", spec[3])
				pb.set(&"joint_constraints/twist_span", spec[4])
			"hinge":
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_HINGE
				pb.joint_rotation = Vector3(0, PI * 0.5, 0)  # hinge axis (Z) across the bone
				pb.set(&"joint_constraints/angular_limit_enabled", true)
				pb.set(&"joint_constraints/angular_limit_upper", spec[3])
				pb.set(&"joint_constraints/angular_limit_lower", spec[4])
			_:
				pb.joint_type = PhysicalBone3D.JOINT_TYPE_NONE
		_sim.add_child(pb)
		_bones[bone] = pb
	_sim.active = false
