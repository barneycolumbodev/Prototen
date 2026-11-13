class_name BlobShadows
extends MultiMeshInstance3D
## Soft dark discs at the feet of the living men (baked maps get no live
## shadows), all drawn in one call (optimization overhaul C-08) instead of
## one quad per man.

const CAPACITY: int = 32
const SIZE: Vector2 = Vector2(1.1, 1.1)
const LIFT: float = 0.03

var _men: Array[Enemy] = []


func _init() -> void:
	name = "BlobShadows"
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var quad: QuadMesh = QuadMesh.new()
	quad.size = SIZE
	quad.orientation = PlaneMesh.FACE_Y
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = preload("res://src/levels/blob_shadow.gdshader")
	quad.material = mat
	var mm: MultiMesh = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = quad
	mm.instance_count = CAPACITY
	mm.visible_instance_count = 0
	multimesh = mm
	# The discs go wherever the men are: never cull the whole set by its bounds.
	custom_aabb = AABB(Vector3(-5000, -5000, -5000), Vector3(10000, 10000, 10000))


## Gives `e` a disc until he dies.
func track(e: Enemy) -> void:
	if e not in _men:
		_men.append(e)


func count() -> int:
	return multimesh.visible_instance_count


func _process(_delta: float) -> void:
	refresh()


func refresh() -> void:
	var n: int = 0
	var i: int = 0
	while i < _men.size():
		var e: Enemy = _men[i]
		if not is_instance_valid(e) or not e.alive or not e.is_inside_tree():
			_men.remove_at(i)
			continue
		if n < CAPACITY:
			multimesh.set_instance_transform(n, Transform3D(Basis.IDENTITY, e.global_position + Vector3(0.0, LIFT, 0.0)))
			n += 1
		i += 1
	multimesh.visible_instance_count = n
