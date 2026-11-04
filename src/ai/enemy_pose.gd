class_name EnemyPose
extends SkeletonModifier3D
## Procedural layer on top of the enemy's animation clips (docs/design.md §5.4/§5.5):
## - Aim: turns spine, chest, neck and head toward `aim_yaw`/`aim_pitch`
##   (radians, relative to the body's facing), so the clips only need to
##   point the gun straight ahead.
## - Flinch: every hit kicks a spring on the torso and one on the head away
##   from the round; the clip springs back through it.
## Runs after the AnimationTree, before the ragdoll simulator.

const BONES: Array[StringName] = [&"spine", &"chest", &"neck", &"head"]
## How much of the aim each bone takes (yaw, pitch).
const YAW_SHARE: Array[float] = [0.3, 0.4, 0.15, 0.15]
const PITCH_SHARE: Array[float] = [0.25, 0.45, 0.1, 0.2]

var aim_yaw: float = 0.0
var aim_pitch: float = 0.0
## 0 = clips only, 1 = full aim.
var aim_weight: float = 1.0
## Spring rotations (radians, skeleton-space axis × angle).
var torso_flinch: Spring = Spring.new(3.2, 0.42)
var head_flinch: Spring = Spring.new(4.0, 0.38)

var _ids: Array[int] = []
var _parent_ids: Array[int] = []


func _ready() -> void:
	_bind()


func _bind() -> void:
	var sk: Skeleton3D = get_skeleton()
	_ids.clear()
	_parent_ids.clear()
	if sk == null:
		return
	for b: StringName in BONES:
		var i: int = sk.find_bone(b)
		_ids.append(i)
		_parent_ids.append(sk.get_bone_parent(i) if i >= 0 else -1)


## A hit: `dir` is the round's direction in skeleton space, `torso`/`head`
## how hard (radians) each part is knocked.
func flinch(dir: Vector3, torso: float, head: float) -> void:
	var axis: Vector3 = Vector3.UP.cross(Vector3(dir.x, 0.0, dir.z).normalized())
	if axis.length_squared() < 0.01:
		axis = Vector3.RIGHT
	torso_flinch.kick(axis.normalized() * torso + Vector3.UP * randf_range(-0.5, 0.5) * torso)
	head_flinch.kick(axis.normalized() * head + Vector3.UP * randf_range(-0.6, 0.6) * head)


func step_springs(delta: float) -> void:
	torso_flinch.step(delta)
	head_flinch.step(delta)


func _process_modification() -> void:
	var sk: Skeleton3D = get_skeleton()
	if sk == null:
		return
	if _ids.size() != BONES.size() or _ids[0] < 0:
		_bind()
		if _ids.is_empty() or _ids[0] < 0:
			return
	var yaw: float = aim_yaw * aim_weight
	var pitch: float = aim_pitch * aim_weight
	# Global (skeleton-space) basis of the first parent; the chain is updated as we go.
	var parent_basis: Basis = sk.get_bone_global_pose(_parent_ids[0]).basis.orthonormalized()
	var yawed_right: Vector3 = Vector3.RIGHT.rotated(Vector3.UP, yaw)
	for k: int in _ids.size():
		var i: int = _ids[k]
		var local: Quaternion = sk.get_bone_pose_rotation(i)
		var delta_rot: Basis = Basis(Vector3.UP, yaw * YAW_SHARE[k]) * Basis(yawed_right, -pitch * PITCH_SHARE[k])
		var spring: Vector3 = Vector3.ZERO
		if k == 0:
			spring = torso_flinch.value * 0.4
		elif k == 1:
			spring = torso_flinch.value * 0.6
		elif k == 3:
			spring = head_flinch.value
		if spring.length_squared() > 1e-8:
			delta_rot = Basis(spring.normalized(), spring.length()) * delta_rot
		# Rotate the bone in skeleton space: new_global = delta * global.
		var global_basis: Basis = parent_basis * Basis(local)
		var new_global: Basis = (delta_rot * global_basis).orthonormalized()
		var new_local: Quaternion = (parent_basis.inverse() * new_global).get_rotation_quaternion()
		sk.set_bone_pose_rotation(i, new_local)
		if k + 1 < _ids.size():
			# The next bone's parent: this one, unless the chain skips (neck's parent is chest).
			if _parent_ids[k + 1] == i:
				parent_basis = new_global
			else:
				parent_basis = sk.get_bone_global_pose(_parent_ids[k + 1]).basis.orthonormalized()
