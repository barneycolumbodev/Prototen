class_name ImpactBursts
extends MultiMeshInstance3D
## The burst of blood the moment a round goes into or out of a body (owner,
## 2026-11-13: "that moment of impact just needs more feedback, punch, and
## realism", above all in RX-9 slow motion). Owned by Gore, next to the drops:
## the drops are what flies on, this is the thick sheet thrown out of the
## wound in the first fraction of a second, which a few hundred drops can't
## show. Entry: a small burst all round, back toward the shooter. Exit: a
## fan along the round, longer and heavier with what it carried out.
## Drawn by impact_burst.gdshader from the launch state and the game clock
## (nothing is updated per frame), one MultiMesh, one draw call, MAX_BURSTS
## instances, the oldest reused.

const MAX_BURSTS: int = 24
const SHADER: Shader = preload("res://src/gore/impact_burst.gdshader")

## Bursts started (tests, overlay).
var emitted: int = 0

var _mm: MultiMesh
var _mat: ShaderMaterial
var _next: int = 0
var _ends: PackedFloat32Array = PackedFloat32Array()
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init() -> void:
	name = "ImpactBursts"
	_rng.randomize()
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2.ONE
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	quad.material = _mat
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_3D
	_mm.mesh = quad
	_mm.instance_count = MAX_BURSTS
	_mm.visible_instance_count = 0
	_ends.resize(MAX_BURSTS)
	multimesh = _mm
	top_level = true
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	custom_aabb = AABB(Vector3(-400, -100, -400), Vector3(800, 200, 800))


## Moves the burst clock on (Gore calls it with the drops' clock).
func set_clock(clock: float) -> void:
	_mat.set_shader_parameter(&"now", clock)


func live_count(clock: float) -> int:
	var n: int = 0
	for e: float in _ends:
		if e > clock:
			n += 1
	return n


func clear() -> void:
	_ends.fill(0.0)
	_mm.visible_instance_count = 0
	_next = 0


## A burst at `at` thrown along `dir`, `size` metres from the wound to the
## ends of its rays, over `life` seconds of game time (out to full length in
## `rise`). `fan`: thrown one way (an exit), else all round (an entry).
func emit(clock: float, at: Vector3, dir: Vector3, size: float, life: float, rise: float, fan: bool) -> void:
	var d: Vector3 = dir.normalized() if dir.length_squared() > 0.0001 else Vector3.UP
	var i: int = _next
	_next = (_next + 1) % MAX_BURSTS
	_mm.set_instance_transform(i, Transform3D(Basis(d, Vector3(clock, life, size),
			Vector3(1.0 if fan else 0.0, _rng.randf(), rise)), at))
	_ends[i] = clock + life
	_mm.visible_instance_count = maxi(_mm.visible_instance_count, i + 1)
	emitted += 1
