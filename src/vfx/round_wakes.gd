class_name RoundWakes
extends MultiMeshInstance3D
## Wakes behind the operative's rounds while the world is slowed (RX-9),
## drawn by round_wake.gdshader. Owned by Ballistics, which claims one when
## it fires a round with the world dilated and moves its head as the round
## flies. One MultiMesh, one draw call, MAX_WAKES instances, the oldest
## reused. The clock is game time, so a wake fades four times slower in
## slow motion, which is the only time they are drawn.

const MAX_WAKES: int = 16
## Longest wake drawn behind a round (m).
const MAX_LENGTH: float = 6.0
const WIDTH: float = 0.006
## Seconds of game time a wake takes to fade once its round has stopped.
const FADE: float = 0.3
## Dilation (TimeControl.dilation_amount) past which rounds leave a wake.
const MIN_DILATION: float = 0.25
const SHADER: Shader = preload("res://src/vfx/round_wake.gdshader")
const FLYING: float = 1.0e9

var clock: float = 0.0
var _mm: MultiMesh
var _mat: ShaderMaterial
var _next: int = 0
## Projectile id owning each slot (0 = free), its tail and when it stopped.
var _owner: PackedInt64Array = PackedInt64Array()
var _tail: PackedVector3Array = PackedVector3Array()
var _stopped: PackedFloat32Array = PackedFloat32Array()


func _init() -> void:
	name = "RoundWakes"
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2.ONE
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	quad.material = _mat
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_3D
	_mm.mesh = quad
	_mm.instance_count = MAX_WAKES
	_mm.visible_instance_count = 0
	multimesh = _mm
	top_level = true
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	custom_aabb = AABB(Vector3(-400, -100, -400), Vector3(800, 200, 800))
	_owner.resize(MAX_WAKES)
	_tail.resize(MAX_WAKES)
	_stopped.resize(MAX_WAKES)
	_stopped.fill(-1.0)


func advance(delta: float) -> void:
	clock += delta
	_mat.set_shader_parameter(&"now", clock)


## Wakes flying or fading now (tests, overlay).
func live_count() -> int:
	var n: int = 0
	for i: int in MAX_WAKES:
		if _owner[i] != 0 and (_stopped[i] < 0.0 or clock - _stopped[i] < FADE):
			n += 1
	return n


## A slot for round `id` fired from `from`. Returns the slot.
func claim(id: int, from: Vector3) -> int:
	var i: int = _next
	_next = (_next + 1) % MAX_WAKES
	_owner[i] = id
	_tail[i] = from
	_stopped[i] = -1.0
	_mm.visible_instance_count = maxi(_mm.visible_instance_count, i + 1)
	return i


## The round in slot `slot` is at `head`; `alive` false once it has stopped.
## Returns false if the slot has gone to a newer round.
func update(slot: int, id: int, head: Vector3, alive: bool) -> bool:
	if slot < 0 or _owner[slot] != id:
		return false
	var tail: Vector3 = _tail[slot]
	var span: Vector3 = head - tail
	if span.length() > MAX_LENGTH:
		tail = head - span.normalized() * MAX_LENGTH
		_tail[slot] = tail
		span = head - tail
	if not alive:
		_stopped[slot] = clock
	_mm.set_instance_transform(slot, Transform3D(Basis(span, Vector3(FLYING if alive else clock, WIDTH, FADE),
			Vector3.ZERO), tail))
	return true


func clear() -> void:
	_owner.fill(0)
	_stopped.fill(-1.0)
	_mm.visible_instance_count = 0
	_next = 0
