class_name BarrelSmoke
extends MultiMeshInstance3D
## Gun smoke (WeaponData.blast_smoke, barrel_smoke, cylinder_gap_point; the
## .44 Magnum). Three kinds of puff, simulated here (closed loops, no
## allocation) and drawn as one MultiMesh (one draw call, barrel_smoke.gdshader):
## - the blast: a cloud thrown out of the muzzle on the shot that billows,
##   slows in a metre or so and hangs, drifting up, for about two seconds;
## - the gap: two small jets spat sideways out of a revolver's cylinder gap;
## - the wisp: after the shot a thin thread keeps curling up out of the
##   barrel, thinning as the barrel cools (`heat` seconds, stacking per shot).
##   It's laid in world space, so it trails behind the muzzle when the gun moves.
## World space (top level); the weapon calls `shot()` and `follow()` each frame.

const MAX_PUFFS: int = 72

var heat: float = 0.0

var _pos: PackedVector3Array = PackedVector3Array()
var _vel: PackedVector3Array = PackedVector3Array()
## x = age (s), y = lifetime (s), z = size at birth (m), w = size at death (m).
var _life: PackedVector4Array = PackedVector4Array()
## x = opacity at full, y = seed, z = spin, w = drag (1/s).
var _look: PackedVector4Array = PackedVector4Array()
var _next: int = 0
var _live: int = 0
var _spawn_acc: float = 0.0
var _clock: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _mm: MultiMesh


func _ready() -> void:
	top_level = true
	global_transform = Transform3D.IDENTITY
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_pos.resize(MAX_PUFFS)
	_vel.resize(MAX_PUFFS)
	_life.resize(MAX_PUFFS)
	_look.resize(MAX_PUFFS)
	for i: int in MAX_PUFFS:
		_life[i] = Vector4(1.0, 0.0, 0.0, 0.0)
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_3D
	_mm.use_colors = true
	_mm.use_custom_data = true
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	_mm.mesh = quad
	_mm.instance_count = MAX_PUFFS
	_mm.visible_instance_count = 0
	multimesh = _mm
	var m: ShaderMaterial = ShaderMaterial.new()
	m.shader = preload("res://src/vfx/barrel_smoke.gdshader")
	material_override = m
	# Never culled by its (moving, world-space) bounds.
	custom_aabb = AABB(Vector3(-1e4, -1e4, -1e4), Vector3(2e4, 2e4, 2e4))


## Puffs alive now (tests, the debug overlay).
func live_puffs() -> int:
	return _live


## A shot: the blast cloud out of the muzzle (forward = `muzzle.basis.x`),
## the cylinder-gap jets (world point, ZERO-free: pass INF for none), and
## more heat in the barrel for the wisp.
func shot(muzzle: Transform3D, gap: Vector3, side: Vector3, data: WeaponData, carried: Vector3) -> void:
	var fwd: Vector3 = muzzle.basis.x.normalized()
	if data.blast_smoke > 0.0:
		var n: int = roundi(10.0 * data.blast_smoke)
		for i: int in n:
			var d: Vector3 = (fwd + _rand_dir() * 0.35).normalized()
			var sp: float = _rng.randf_range(2.5, 9.0) * data.blast_smoke
			_spawn(muzzle.origin + fwd * _rng.randf_range(0.0, 0.05), d * sp + carried,
					_rng.randf_range(1.4, 2.4), _rng.randf_range(0.03, 0.06), _rng.randf_range(0.22, 0.42) * data.blast_smoke,
					_rng.randf_range(0.22, 0.34), 5.5)
	if gap.is_finite():
		for s: float in [-1.0, 1.0]:
			for i: int in 3:
				var d: Vector3 = (side * s + fwd * 0.25 + _rand_dir() * 0.3).normalized()
				_spawn(gap, d * _rng.randf_range(1.5, 4.0) + carried, _rng.randf_range(0.7, 1.2),
						0.015, _rng.randf_range(0.07, 0.12), 0.18, 7.0)
	heat = minf(heat + data.barrel_smoke, data.barrel_smoke * 3.0)
	_spawn_acc = 0.0


## Each frame while the gun is out: the wisp rises from the muzzle as it is
## now (`muzzle` INF: the gun is away, no wisp), then every puff moves.
func follow(muzzle: Vector3, delta: float) -> void:
	_clock += delta
	if heat > 0.0:
		heat = maxf(0.0, heat - delta)
		if muzzle.is_finite():
			# Thick just after the shot, a thread as it cools: 4..24 puffs a second.
			var rate: float = lerpf(4.0, 24.0, clampf(heat / 1.5, 0.0, 1.0))
			_spawn_acc += rate * delta
			while _spawn_acc >= 1.0:
				_spawn_acc -= 1.0
				var up: Vector3 = Vector3(_rng.randf_range(-0.03, 0.03), _rng.randf_range(0.1, 0.22), _rng.randf_range(-0.03, 0.03))
				_spawn(muzzle + Vector3(0.0, 0.006, 0.0), up, _rng.randf_range(1.6, 2.6), 0.012, _rng.randf_range(0.07, 0.12),
						lerpf(0.14, 0.32, clampf(heat / 1.5, 0.0, 1.0)), 0.6)
	_step(delta)


func _rand_dir() -> Vector3:
	return Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0))


func _spawn(at: Vector3, vel: Vector3, life: float, size0: float, size1: float, alpha: float, drag: float) -> void:
	var i: int = _next
	_next = (_next + 1) % MAX_PUFFS
	_pos[i] = at
	_vel[i] = vel
	_life[i] = Vector4(0.0, life, size0, size1)
	_look[i] = Vector4(alpha, _rng.randf(), _rng.randf() * TAU, drag)


func _step(delta: float) -> void:
	var shown: int = 0
	for i: int in MAX_PUFFS:
		var l: Vector4 = _life[i]
		if l.x >= l.y:
			continue
		l.x += delta
		_life[i] = l
		if l.x >= l.y:
			continue
		var k: Vector4 = _look[i]
		var v: Vector3 = _vel[i]
		# Drag toward still air, buoyancy, and a slow curl so the thread waves.
		v *= exp(-k.w * delta)
		v.y += 0.35 * delta
		var ph: float = _clock * 2.1 + k.y * TAU
		v.x += sin(ph) * 0.12 * delta
		v.z += cos(ph * 0.8) * 0.12 * delta
		_vel[i] = v
		var p: Vector3 = _pos[i] + v * delta
		_pos[i] = p
		var u: float = l.x / l.y
		var size: float = lerpf(l.z, l.w, 1.0 - (1.0 - u) * (1.0 - u))
		# Fades in over the first tenth, out over the rest.
		var a: float = k.x * minf(u / 0.1, 1.0) * (1.0 - u) * (1.0 - u)
		_mm.set_instance_transform(shown, Transform3D(Basis.from_scale(Vector3.ONE * size), p))
		_mm.set_instance_color(shown, Color(1, 1, 1, a))
		_mm.set_instance_custom_data(shown, Color(u, k.y, k.z + l.x * (k.y - 0.5) * 0.6, 0.0))
		shown += 1
	_live = shown
	_mm.visible_instance_count = shown
