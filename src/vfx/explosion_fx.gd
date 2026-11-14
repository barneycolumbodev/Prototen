class_name ExplosionFx
extends Node3D
## How a blast looks (docs/design.md §4.8): a white-hot flash that swells into
## a lumpy fireball, cools through yellow and orange to soot and breaks up;
## three smoke lobes that rise and swell for about three seconds, glowing from
## inside at first; on the ground a ring of dust thrown out along the surface;
## a scorch burnt into the surface with embers in it for the first seconds.
##
## Everything is meshes in two MultiMeshes (one draw call for every puff of
## every live burst, one for every scorch), animated on the GPU from a birth
## time in game seconds (`now`), so RX-9 slow motion slows it. Opaque with a
## noise dissolve, not blended billboards: no overdraw sorting, and no "light
## clouds" (the owner's complaint about the old blood, 2026-11-11).
## Owned by Fx (`Fx.explosion`).

const PUFFS: int = 40
const SCORCHES: int = 10
const PUFF_SHADER: Shader = preload("res://src/vfx/explosion.gdshader")
const SCORCH_SHADER: Shader = preload("res://src/vfx/scorch.gdshader")

## Game seconds since this node started (the shaders' clock).
var now: float = 0.0
var _puffs: MultiMeshInstance3D
var _puff_mat: ShaderMaterial
var _scorches: MultiMeshInstance3D
var _scorch_mat: ShaderMaterial
var _next_puff: int = 0
var _next_scorch: int = 0
## Game time the last live puff ends (the puff mesh hides after it).
var _puffs_until: float = -1.0
var _scorch_count: int = 0
## Each puff's birth and end (game seconds), kept here too: the GPU buffer
## can't be read back on every renderer.
var _puff_birth: PackedFloat32Array = PackedFloat32Array()
var _puff_end: PackedFloat32Array = PackedFloat32Array()
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
## Bursts drawn since start (tests).
var bursts: int = 0


func _ready() -> void:
	_rng.randomize()
	var sphere: SphereMesh = SphereMesh.new()
	sphere.radius = 1.0
	sphere.height = 2.0
	sphere.radial_segments = 22
	sphere.rings = 11
	_puff_mat = ShaderMaterial.new()
	_puff_mat.shader = PUFF_SHADER
	sphere.material = _puff_mat
	var mm: MultiMesh = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = sphere
	mm.instance_count = PUFFS
	_puff_birth.resize(PUFFS)
	_puff_end.resize(PUFFS)
	for i: int in PUFFS:
		mm.set_instance_transform(i, Transform3D(Basis.from_scale(Vector3.ONE * 0.001), Vector3(0, -1000, 0)))
		mm.set_instance_custom_data(i, Color(-100.0, 0.0, 0.0, 0.0))
		_puff_birth[i] = -100.0
		_puff_end[i] = -100.0
	_puffs = MultiMeshInstance3D.new()
	_puffs.multimesh = mm
	_puffs.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_puffs.custom_aabb = AABB(Vector3(-500, -500, -500), Vector3(1000, 1000, 1000))
	_puffs.visible = false
	add_child(_puffs)

	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2.ONE
	quad.orientation = PlaneMesh.FACE_Y
	_scorch_mat = ShaderMaterial.new()
	_scorch_mat.shader = SCORCH_SHADER
	_scorch_mat.render_priority = -1
	quad.material = _scorch_mat
	var sm: MultiMesh = MultiMesh.new()
	sm.transform_format = MultiMesh.TRANSFORM_3D
	sm.use_custom_data = true
	sm.mesh = quad
	sm.instance_count = SCORCHES
	sm.visible_instance_count = 0
	_scorches = MultiMeshInstance3D.new()
	_scorches.multimesh = sm
	_scorches.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_scorches.custom_aabb = AABB(Vector3(-500, -500, -500), Vector3(1000, 1000, 1000))
	add_child(_scorches)


func _process(delta: float) -> void:
	now += delta
	_puff_mat.set_shader_parameter(&"now", now)
	_scorch_mat.set_shader_parameter(&"now", now)
	_puffs.visible = now < _puffs_until


## A burst at `at` with a fireball of `radius` m. `normal`: the surface it
## burst on (dust ring along it, scorch on it); `airburst`: in the air (no
## ring; a faint scorch on the ground if it was close to it).
func spawn(at: Vector3, normal: Vector3, radius: float, airburst: bool) -> void:
	bursts += 1
	var n: Vector3 = normal.normalized() if normal.length() > 0.01 else Vector3.UP
	var r: float = maxf(radius, 0.1)
	var seed: float = _rng.randf() * 10.0
	# Fireball, centred a little off the surface.
	var centre: Vector3 = at + (Vector3.ZERO if airburst else n * r * 0.3)
	_puff(centre, Basis.from_scale(Vector3.ONE * r), 0.0, 0.0, seed, 0.5)
	# Smoke lobes: up and out from the surface, a beat after the flash.
	var up: Vector3 = (n + Vector3.UP).normalized() if not airburst else Vector3.UP
	for i: int in 3:
		var side: Vector3 = Vector3(_rng.randf_range(-1, 1), 0.0, _rng.randf_range(-1, 1)) * r * 0.45
		var p: Vector3 = centre + up * r * _rng.randf_range(0.15, 0.55) + side
		var s: float = r * _rng.randf_range(0.95, 1.3)
		_puff(p, Basis.from_scale(Vector3.ONE * s), _rng.randf_range(0.03, 0.09), 1.0, seed + 1.7 * float(i + 1),
				_rng.randf_range(2.4, 3.3))
	if not airburst:
		# Dust thrown out along the surface by the shock.
		_puff(at + n * 0.04, _flat_basis(n, r * 2.3, r * 0.2), 0.0, 2.0, seed + 9.1, 1.15)
		_scorch(at - n * 0.03, n, r * 1.9, 1.0)
	else:
		var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(at, at + Vector3.DOWN * 1.6, Ballistics.LAYER_WORLD)
		var hit: Dictionary = space.intersect_ray(q)
		if not hit.is_empty():
			var ground: Vector3 = hit["position"]
			var gn: Vector3 = hit["normal"]
			var k: float = 1.0 - at.distance_to(ground) / 1.6
			_puff(ground + gn * 0.04, _flat_basis(gn, r * 2.0 * (0.5 + 0.5 * k), r * 0.16), 0.03, 2.0, seed + 4.4, 1.0)
			_scorch(ground, gn, r * 1.6, 0.25 + 0.4 * k)


## Puffs alive now or about to be born (tests).
func live_puffs() -> int:
	var n: int = 0
	for i: int in PUFFS:
		if now >= _puff_birth[i] - 0.2 and now <= _puff_end[i]:
			n += 1
	return n


func scorch_count() -> int:
	return _scorch_count


func _puff(at: Vector3, basis: Basis, delay: float, kind: float, seed: float, life: float) -> void:
	var mm: MultiMesh = _puffs.multimesh
	mm.set_instance_transform(_next_puff, Transform3D(basis, at))
	mm.set_instance_custom_data(_next_puff, Color(now + delay, seed, kind, life))
	_puff_birth[_next_puff] = now + delay
	_puff_end[_next_puff] = now + delay + life
	_next_puff = (_next_puff + 1) % PUFFS
	_puffs_until = maxf(_puffs_until, now + delay + life)
	_puffs.visible = true


func _scorch(at: Vector3, n: Vector3, size: float, strength: float) -> void:
	var mm: MultiMesh = _scorches.multimesh
	var b: Basis = Basis(n.normalized(), _rng.randf() * TAU) * _flat_basis(n, size, 1.0)
	mm.set_instance_transform(_next_scorch, Transform3D(b, at + n * 0.012))
	mm.set_instance_custom_data(_next_scorch, Color(now, _rng.randf() * 10.0, strength, 0.0))
	_next_scorch = (_next_scorch + 1) % SCORCHES
	_scorch_count = mini(_scorch_count + 1, SCORCHES)
	mm.visible_instance_count = _scorch_count


## A basis with Y along `n`, scaled `across` in its plane and `thick` along it.
static func _flat_basis(n: Vector3, across: float, thick: float) -> Basis:
	var y: Vector3 = n.normalized()
	var ref: Vector3 = Vector3.RIGHT if absf(y.x) < 0.9 else Vector3.FORWARD
	var x: Vector3 = ref.cross(y).normalized()
	var z: Vector3 = x.cross(y).normalized()
	return Basis(x * across, y * thick, z * across)
