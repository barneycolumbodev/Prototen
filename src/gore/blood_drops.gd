class_name BloodDrops
extends MultiMeshInstance3D
## Blood in the air (docs/design.md §5.5). Owned by Gore.
##
## Every drop is a small mass on a ballistic path: gravity plus air drag that
## is stronger the smaller the drop, so a fine spray stops within half a
## metre and sinks while the heavy drops carry on in an arc. The path has a
## closed form (linear drag):
##     vt   = g / k                      (terminal velocity)
##     p(t) = p0 + vt·t + (v0 − vt)·(1 − e^(−kt)) / k
##     v(t) = vt + (v0 − vt)·e^(−kt)
## so nothing is integrated per frame. The shader (blood_drop.gdshader) draws
## each drop from its launch state and the clock; this script only works out,
## once, when the drop is launched, where its path meets the level:
## - Drops that stain are traced against the world with a ray per STEP of
##   flight. Where one lands, a Landing (point, surface normal, velocity at
##   impact, size) is queued for the moment it gets there; Gore turns it into
##   a stain shaped by the impact angle.
## - The rest end on the floor found under the wound (one ray per burst),
##   without a trace.
## One MultiMesh, one draw call, MAX_DROPS instances; the oldest slot is
## reused. The clock is game time, so slow motion slows the drops with
## everything else (design: "blood... still look right at 25 % speed").

const MAX_DROPS: int = 320
const GRAVITY: float = 9.8
## Seconds of flight between ray samples (the chord sags < 1 cm).
const STEP: float = 0.07
const MAX_FLIGHT: float = 1.8
## Trace rays allowed per frame; past it, drops fall back to the floor rule.
const RAYS_PER_FRAME: int = 110
const SHADER: Shader = preload("res://src/gore/blood_drop.gdshader")


## A drop reaching a surface.
class Landing:
	extends RefCounted
	var time: float = 0.0
	var point: Vector3
	var normal: Vector3
	var velocity: Vector3
	var size: float = 0.01
	## Metres across of the stain it leaves, when it isn't a single drop's
	## (a gout: the bulk of what left a wound). 0: from the drop's size.
	var stain: float = 0.0

	func _init(t: float, p: Vector3, n: Vector3, v: Vector3, s: float, big: float = 0.0) -> void:
		time = t
		point = p
		normal = n
		velocity = v
		size = s
		stain = big


## Game time, seconds (scaled by Engine.time_scale through delta).
var clock: float = 0.0
## Landings that haven't happened yet.
var landings: Array[Landing] = []
## Counters for the overlay and tests.
var emitted: int = 0
var rays_cast: int = 0

var _mm: MultiMesh
var _mat: ShaderMaterial
var _next: int = 0
var _ends: PackedFloat32Array = PackedFloat32Array()
var _rays_left: int = RAYS_PER_FRAME
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _query: PhysicsRayQueryParameters3D


func _init() -> void:
	name = "BloodDrops"
	_rng.randomize()
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2.ONE
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	quad.material = _mat
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_3D
	_mm.mesh = quad
	_mm.instance_count = MAX_DROPS
	_mm.visible_instance_count = 0
	for i: int in MAX_DROPS:
		_mm.set_instance_transform(i, Transform3D(Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO), Vector3.ZERO))
	_ends.resize(MAX_DROPS)
	multimesh = _mm
	top_level = true
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	custom_aabb = AABB(Vector3(-400, -100, -400), Vector3(800, 200, 800))
	_query = PhysicsRayQueryParameters3D.new()
	_query.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS
	_query.collide_with_areas = false


## Advances the clock. Returns the landings that are due (removed from the queue).
func advance(delta: float) -> Array[Landing]:
	clock += delta
	_rays_left = RAYS_PER_FRAME
	_mat.set_shader_parameter(&"now", clock)
	var due: Array[Landing] = []
	if landings.is_empty():
		return due
	var later: Array[Landing] = []
	for l: Landing in landings:
		if l.time <= clock:
			due.append(l)
		else:
			later.append(l)
	landings = later
	return due


func live_count() -> int:
	var n: int = 0
	for e: float in _ends:
		if e > clock:
			n += 1
	return n


func clear() -> void:
	landings.clear()
	_ends.fill(0.0)
	_mm.visible_instance_count = 0
	_next = 0


## Where a drop launched from `p0` at `v0` with drag `k` is after `t` seconds.
static func position_at(p0: Vector3, v0: Vector3, k: float, t: float) -> Vector3:
	var vt: Vector3 = Vector3(0.0, -GRAVITY / k, 0.0)
	return p0 + vt * t + (v0 - vt) * ((1.0 - exp(-k * t)) / k)


## Its velocity then.
static func velocity_at(v0: Vector3, k: float, t: float) -> Vector3:
	var vt: Vector3 = Vector3(0.0, -GRAVITY / k, 0.0)
	return vt + (v0 - vt) * exp(-k * t)


## Air drag (1/s) for a drop `size` metres across: `base` for a 12 mm drop,
## more for smaller ones (their area-to-mass ratio).
static func drag_for(size: float, base: float) -> float:
	return clampf(base * 0.012 / maxf(size, 0.001), 0.05, 30.0)


## When a drop reaches height `floor_y` (seconds; `life` if it doesn't in time).
static func time_to_height(p0: Vector3, v0: Vector3, k: float, floor_y: float, life: float) -> float:
	var a: float = 0.0
	var b: float = 0.0
	var found: bool = false
	while b < life:
		a = b
		b = minf(b + 0.12, life)
		if position_at(p0, v0, k, b).y <= floor_y:
			found = true
			break
	if not found:
		return life
	for i: int in 7:
		var m: float = (a + b) * 0.5
		if position_at(p0, v0, k, m).y <= floor_y:
			b = m
		else:
			a = m
	return b


## Launches one drop. `stain`: trace it and queue a Landing where it comes
## down. `floor_y`: the floor under the wound, where untraced drops end
## (-INF: unknown, they live out `life`). `stain_size`: see Landing.stain.
## Returns the flight time.
func emit(origin: Vector3, velocity: Vector3, size: float, drag: float, stain: bool, floor_y: float = -INF,
		life: float = MAX_FLIGHT, stain_size: float = 0.0) -> float:
	var k: float = maxf(drag, 0.05)
	var end: float = life
	var traced: bool = false
	if stain and _rays_left > 0 and is_inside_tree():
		traced = true
		var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
		var a: Vector3 = origin
		var t: float = 0.0
		while t < life and _rays_left > 0:
			var t2: float = minf(t + STEP, life)
			var b: Vector3 = position_at(origin, velocity, k, t2)
			_query.from = a
			_query.to = b
			_rays_left -= 1
			rays_cast += 1
			var res: Dictionary = space.intersect_ray(_query)
			if not res.is_empty():
				var p: Vector3 = res["position"]
				var n: Vector3 = res["normal"]
				end = t + (t2 - t) * clampf(a.distance_to(p) / maxf(a.distance_to(b), 0.0001), 0.0, 1.0)
				landings.append(Landing.new(clock + end, p, n, velocity_at(velocity, k, end), size, stain_size))
				t = life
				break
			a = b
			t = t2
		# Out of rays part-way: finish it by the floor rule.
		traced = t >= life
	if not traced and floor_y > -INF:
		end = time_to_height(origin, velocity, k, floor_y, life)
		if stain and end < life:
			var p: Vector3 = position_at(origin, velocity, k, end)
			landings.append(Landing.new(clock + end, Vector3(p.x, floor_y, p.z), Vector3.UP, velocity_at(velocity, k, end), size, stain_size))
	var i: int = _next
	_next = (_next + 1) % MAX_DROPS
	# The shader reads the launch state out of the instance transform:
	# X = launch velocity, Y = (launch time, end time, size), Z = (drag, seed, 0).
	_mm.set_instance_transform(i, Transform3D(Basis(velocity, Vector3(clock, clock + end, size), Vector3(k, _rng.randf(), 0.0)), origin))
	_ends[i] = clock + end
	if _mm.visible_instance_count < MAX_DROPS:
		_mm.visible_instance_count = maxi(_mm.visible_instance_count, i + 1)
	emitted += 1
	return end


## A cone of `count` drops from `at` along `dir`. Speeds between the two
## given, most of them slow; sizes between the two given, the big ones few;
## the `stains` biggest are traced and leave stains. `inherit`: the velocity
## of what they left (a flying limb, a moving stump).
func cone(at: Vector3, dir: Vector3, count: int, speed_min: float, speed_max: float, spread_deg: float,
		size_min: float, size_max: float, drag_base: float, stains: int, inherit: Vector3 = Vector3.ZERO,
		floor_y: float = -INF, life: float = MAX_FLIGHT) -> void:
	if count <= 0:
		return
	var z: Vector3 = dir.normalized() if dir.length_squared() > 0.0001 else Vector3.UP
	var up: Vector3 = Vector3.UP if absf(z.y) < 0.95 else Vector3.RIGHT
	var x: Vector3 = up.cross(z).normalized()
	var y: Vector3 = z.cross(x)
	var tan_spread: float = tan(deg_to_rad(clampf(spread_deg, 0.0, 85.0)))
	for i: int in count:
		var big: bool = i < stains
		var u: float = _rng.randf()
		# Few big drops, many small: the stainers come from the top of the range.
		var size: float = lerpf(size_min, size_max, (0.55 + 0.45 * u) if big else u * u)
		var a: float = _rng.randf() * TAU
		var r: float = sqrt(_rng.randf()) * tan_spread
		var d: Vector3 = (z + (x * cos(a) + y * sin(a)) * r).normalized()
		var s: float = lerpf(speed_min, speed_max, pow(_rng.randf(), 1.6))
		emit(at, d * s + inherit, size, drag_for(size, drag_base), big, floor_y, life)
