class_name SurfaceLibrary
extends Resource
## Every SurfaceMaterial, looked up by id. Colliders name their material with
## metadata `surface` (a StringName); anything without it uses `fallback`.

const PATH: String = "res://data/surfaces/surface_library.tres"
const META: StringName = &"surface"

@export var materials: Array[SurfaceMaterial] = []
@export var fallback: StringName = &"concrete"

var _by_id: Dictionary[StringName, SurfaceMaterial] = {}

static var _shared: SurfaceLibrary


static func shared() -> SurfaceLibrary:
	if _shared == null:
		_shared = load(PATH) as SurfaceLibrary
	return _shared


func get_material(id: StringName) -> SurfaceMaterial:
	if _by_id.size() != materials.size():
		_by_id.clear()
		for m: SurfaceMaterial in materials:
			_by_id[m.id] = m
	if _by_id.has(id):
		return _by_id[id]
	return _by_id.get(fallback, materials[0] if not materials.is_empty() else SurfaceMaterial.new())


## Material of whatever a ray hit. Checks the collider, then its parent
## (so a mesh's StaticBody can inherit the surface of the prop it belongs to).
func for_collider(collider: Object) -> SurfaceMaterial:
	var node: Node = collider as Node
	while node != null:
		if node.has_meta(META):
			var id: StringName = node.get_meta(META)
			return get_material(id)
		node = node.get_parent()
		if node is Viewport:
			break
	return get_material(fallback)
