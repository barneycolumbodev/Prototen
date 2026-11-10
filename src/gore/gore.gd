extends Node3D
## Blood and gore (docs/design.md §5.5). Autoloaded as Gore.
##
## Everything is pooled and capped (CLAUDE.md §8):
## - Sprays: entry back-spatter, exit spray along the round, bigger bursts on
##   headshots, a mist cloud. CPUParticles3D, so they follow Engine.time_scale
##   and hold up in slow motion.
## - Splats on the world: one MultiMesh (one draw call), ≤ 48; when full the
##   oldest fades out. Exit sprays put a directional splat on the wall behind
##   the target after the blood's flight time; drips land on the floor.
## - Pools grow under bodies (≤ 8, MultiMesh).
## - Gibs: severed parts and chunks as pooled rigid bodies (≤ 14), frozen
##   after a few seconds; they bleed and splat where they land.
## Wounds on bodies are painted by the enemy shader (src/ai/triad.gdshader),
## so they stick to the skin exactly; see EnemyBody.add_wound().
## Settings.gore_level: OFF (no blood), STANDARD, MAXIMUM (dismemberment,
## head shots that destroy the head, more blood).

enum Level { OFF, STANDARD, MAXIMUM }

const MAX_SPLATS: int = 48
const MAX_POOLS: int = 8
const MAX_SPRAYS: int = 12
const MAX_GIBS: int = 14
const GIB_FREEZE_TIME: float = 4.0
const SPLAT_FADE_TIME: float = 1.0
const BLOOD_COLOR: Color = Color(0.42, 0.02, 0.02)
const DECAL_SHADER: Shader = preload("res://src/gore/blood_decal.gdshader")
const SPLAT_TEX: Texture2D = preload("res://assets/gore/splat_atlas.png")
const POOL_TEX: Texture2D = preload("res://assets/gore/pool.png")
const DROP_TEX: Texture2D = preload("res://assets/gore/drop.png")
const MIST_TEX: Texture2D = preload("res://assets/gore/mist.png")

## Tests switch effects off to stay deterministic.
var enabled: bool = true
## Counters for the debug overlay and tests.
var splats_placed: int = 0
var sprays_fired: int = 0

var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _splat_mm: MultiMesh
var _splat_alpha: PackedFloat32Array = PackedFloat32Array()
var _splat_used: int = 0
var _splat_next: int = 0
var _fading: Dictionary[int, float] = {}
var _pool_mm: MultiMesh
var _pools: Array[Pool] = []
var _pool_next: int = 0
var _sprays: Array[CPUParticles3D] = []
var _spray_next: int = 0
var _mists: Array[CPUParticles3D] = []
var _mist_next: int = 0
var _gibs: Array[RigidBody3D] = []
var _gib_age: Dictionary[RigidBody3D, float] = {}
var _gib_next: int = 0
## Splats waiting for the blood to arrive.
var _pending: Array[Pending] = []
var _drop_mat: StandardMaterial3D
var _mist_mat: StandardMaterial3D


class Pending:
	extends RefCounted
	var time_left: float = 0.0
	var point: Vector3
	var normal: Vector3
	var size: float = 0.2
	var along: Vector3

	func _init(t: float, p: Vector3, n: Vector3, s: float, a: Vector3) -> void:
		time_left = t
		point = p
		normal = n
		size = s
		along = a


class Pool:
	extends RefCounted
	var index: int = 0
	var basis: Basis
	var origin: Vector3
	var radius: float = 0.5
	var age: float = 0.0
	var grow_time: float = 6.0


func _ready() -> void:
	_rng.randomize()
	_splat_mm = _make_mm(MAX_SPLATS, SPLAT_TEX, 2.0, "BloodSplats")
	_splat_alpha.resize(MAX_SPLATS)
	_pool_mm = _make_mm(MAX_POOLS, POOL_TEX, 1.0, "BloodPools")
	_drop_mat = StandardMaterial3D.new()
	_drop_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_drop_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	_drop_mat.vertex_color_use_as_albedo = true
	_drop_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_drop_mat.albedo_texture = DROP_TEX
	_mist_mat = _drop_mat.duplicate() as StandardMaterial3D
	_mist_mat.albedo_texture = MIST_TEX
	var fade: Gradient = Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 1))
	fade.set_color(1, Color(1, 1, 1, 0))
	var grow: Curve = Curve.new()
	grow.add_point(Vector2(0, 0.35))
	grow.add_point(Vector2(1, 1.0))
	for i: int in MAX_SPRAYS:
		var e: CPUParticles3D = _make_emitter(_drop_mat)
		e.color_ramp = fade
		_sprays.append(e)
	for i: int in 3:
		var m: CPUParticles3D = _make_emitter(_mist_mat)
		m.color_ramp = fade
		m.scale_amount_curve = grow
		_mists.append(m)


## Weapon-specific gore (WeaponData.gore_style), e.g. the GX-4's corkscrew
## wound and electrocution. `body`: the enemy's body (null for props).
var gauss: GaussGore


## Arcs crawl over a body and it spasms (the Gauss slug, the arc projector).
func electrocute(body: EnemyBody) -> void:
	if not enabled or body == null:
		return
	if gauss == null:
		gauss = GaussGore.new()
		gauss.name = "GaussGore"
		add_child(gauss)
	gauss.electrocute(body)


func special_hit(hit: BallisticHit, body: EnemyBody) -> void:
	match hit.weapon.gore_style:
		&"gauss":
			if gauss == null:
				gauss = GaussGore.new()
				gauss.name = "GaussGore"
				add_child(gauss)
			gauss.hit(hit, body)


func level() -> int:
	return Settings.gore_level if enabled else Level.OFF


func is_on() -> bool:
	return level() != Level.OFF


func is_maximum() -> bool:
	return level() == Level.MAXIMUM


func splat_count() -> int:
	return _splat_used


func pool_count() -> int:
	return _pools.size()


func gib_count() -> int:
	var n: int = 0
	for g: RigidBody3D in _gibs:
		if is_instance_valid(g) and g.visible:
			n += 1
	return n


## A round went into (and maybe out of) a body. `scale`: how violent (1 = a
## pistol round to the torso). Sprays, wall splats behind, drips below.
func flesh_hit(hit: BallisticHit, scale: float, headshot: bool) -> void:
	if not is_on():
		return
	var k: float = clampf(scale, 0.3, 4.0) * (1.3 if is_maximum() else 1.0)
	var back: Vector3 = (hit.normal * 0.75 - hit.direction * 0.25).normalized()
	spray(hit.point, back, 0.7 * k, roundi(5 * k))
	if hit.result == BallisticHit.Result.PENETRATED:
		spray(hit.exit_point, hit.direction, 1.5 * k, roundi(12 * k))
		if headshot or k > 1.6:
			mist(hit.exit_point, hit.direction, k)
		_splat_behind(hit.exit_point, hit.direction, k)
	elif _rng.randf() < 0.5:
		_drip_below(hit.point, 0.12 + 0.04 * k)
	if headshot:
		spray(hit.point, back, 1.1 * k, roundi(8 * k))
		mist(hit.point, back, k * 0.8)


## Blood flung from `at` along `dir`. `strength` ~ speed scale.
func spray(at: Vector3, dir: Vector3, strength: float, count: int) -> void:
	if not is_on() or count <= 0:
		return
	sprays_fired += 1
	var e: CPUParticles3D = _sprays[_spray_next]
	_spray_next = (_spray_next + 1) % _sprays.size()
	e.global_position = at
	e.global_basis = _basis_facing(dir)
	e.amount = clampi(count, 1, 48)
	e.lifetime = 0.7
	e.spread = 22.0
	e.initial_velocity_min = 1.0 * strength
	e.initial_velocity_max = 5.5 * strength
	e.scale_amount_min = 0.012
	e.scale_amount_max = 0.04 + 0.01 * strength
	e.gravity = Vector3(0, -9.8, 0)
	e.color = BLOOD_COLOR
	e.restart()


## A fine red cloud (head shots, heavy exits).
func mist(at: Vector3, dir: Vector3, strength: float) -> void:
	if not is_on():
		return
	var m: CPUParticles3D = _mists[_mist_next]
	_mist_next = (_mist_next + 1) % _mists.size()
	m.global_position = at
	m.global_basis = _basis_facing(dir)
	m.amount = clampi(roundi(6 * strength), 3, 16)
	m.lifetime = 0.9
	m.spread = 40.0
	m.initial_velocity_min = 0.3 * strength
	m.initial_velocity_max = 1.6 * strength
	m.damping_min = 2.0
	m.damping_max = 4.0
	m.scale_amount_min = 0.12 * strength
	m.scale_amount_max = 0.3 * strength
	m.gravity = Vector3(0, -0.6, 0)
	m.color = Color(0.45, 0.03, 0.03, 0.55)
	m.restart()


## A splat on the world at `point` (normal `normal`), `size` metres across,
## stretched along `along` when given.
func splat(point: Vector3, normal: Vector3, size: float, along: Vector3 = Vector3.ZERO) -> void:
	if not is_on():
		return
	var i: int = _splat_next
	_splat_next = (_splat_next + 1) % MAX_SPLATS
	if _splat_used < MAX_SPLATS:
		_splat_used += 1
	else:
		# Pool full: the next-oldest starts fading so the cap holds without pops.
		_fading[(i + 1) % MAX_SPLATS] = SPLAT_FADE_TIME
	_fading.erase(i)
	var n: Vector3 = normal.normalized()
	var x: Vector3 = along - n * along.dot(n)
	var directional: bool = x.length() > 0.05
	if not directional:
		var up: Vector3 = Vector3.UP if absf(n.y) < 0.95 else Vector3.RIGHT
		x = up.cross(n).rotated(n, _rng.randf() * TAU)
	x = x.normalized()
	var y: Vector3 = n.cross(x)
	var stretch: float = 1.35 if directional else 1.0
	var s: float = size * _rng.randf_range(0.85, 1.15)
	var offset: float = 0.002 + 0.00005 * float(i)
	_splat_mm.set_instance_transform(i, Transform3D(Basis(x * s * stretch, y * s, n), point + n * offset))
	var variant: int = (0 if _rng.randf() < 0.5 else 2) if directional else (1 if _rng.randf() < 0.5 else 3)
	_splat_alpha[i] = 1.0
	_splat_mm.set_instance_custom_data(i, Color(float(variant), 1.0, 0.0, 0.0))
	_splat_mm.set_instance_color(i, Color(1, 1, 1, 1))
	_splat_mm.visible_instance_count = _splat_used
	splats_placed += 1


## Starts a pool growing under `at` (ray down to the floor).
func pool_under(at: Vector3, radius: float) -> void:
	if not is_on():
		return
	var res: Dictionary = _ray(at + Vector3.UP * 0.3, at + Vector3.DOWN * 1.5)
	if res.is_empty():
		return
	var n: Vector3 = res["normal"]
	var p: Pool
	if _pools.size() < MAX_POOLS:
		p = Pool.new()
		p.index = _pools.size()
		_pools.append(p)
	else:
		p = _pools[_pool_next]
		_pool_next = (_pool_next + 1) % MAX_POOLS
	var up: Vector3 = Vector3.FORWARD if absf(n.y) > 0.95 else Vector3.UP
	var x: Vector3 = up.cross(n).normalized().rotated(n, _rng.randf() * TAU)
	p.basis = Basis(x, n.cross(x), n)
	var hit_at: Vector3 = res["position"]
	p.origin = hit_at + n * (0.0015 + 0.0002 * float(p.index))
	p.radius = radius * _rng.randf_range(0.85, 1.2)
	p.age = 0.0
	p.grow_time = 7.0 if is_maximum() else 9.0
	_pool_mm.visible_instance_count = _pools.size()
	_pool_mm.set_instance_custom_data(p.index, Color(0.0, 1.0, 0.0, 0.0))
	_pool_mm.set_instance_color(p.index, Color(1, 1, 1, 1))
	_place_pool(p)


## Throws a gib: `mesh` posed at `xform`, with velocity, bleeding as it flies.
## Returns the body (or null when gore is off).
func throw_gib(mesh: Mesh, xform: Transform3D, velocity: Vector3, spin: Vector3, radius: float,
		material: Material = null) -> RigidBody3D:
	if not is_on() or mesh == null:
		return null
	var g: RigidBody3D
	if _gibs.size() < MAX_GIBS:
		g = _new_gib()
		_gibs.append(g)
	else:
		g = _gibs[_gib_next]
		_gib_next = (_gib_next + 1) % MAX_GIBS
	var mi: MeshInstance3D = g.get_node(^"Mesh") as MeshInstance3D
	mi.mesh = mesh
	mi.material_override = material
	var shape: SphereShape3D = (g.get_node(^"Shape") as CollisionShape3D).shape as SphereShape3D
	shape.radius = clampf(radius, 0.03, 0.2)
	g.freeze = false
	g.visible = true
	g.global_transform = xform
	g.linear_velocity = velocity
	g.angular_velocity = spin
	g.mass = clampf(radius * 20.0, 0.3, 5.0)
	g.set_meta(&"splatted", false)
	_gib_age[g] = 0.0
	return g


## Chunks of bone and flesh (a head destroyed by a heavy round).
func burst_chunks(at: Vector3, dir: Vector3, count: int, speed: float) -> void:
	if not is_maximum():
		return
	var box: BoxMesh = BoxMesh.new()
	for i: int in count:
		box = BoxMesh.new()
		var sz: float = _rng.randf_range(0.015, 0.04)
		box.size = Vector3(sz, sz * _rng.randf_range(0.5, 1.0), sz * _rng.randf_range(0.6, 1.2))
		var v: Vector3 = (dir.normalized() + Vector3(_rng.randf_range(-0.8, 0.8), _rng.randf_range(-0.2, 1.0), _rng.randf_range(-0.8, 0.8))).normalized()
		var mat: StandardMaterial3D = _chunk_material(i % 3 == 0)
		throw_gib(box, Transform3D(Basis.from_euler(Vector3(_rng.randf() * TAU, _rng.randf() * TAU, 0)), at),
				v * speed * _rng.randf_range(0.4, 1.0), Vector3(_rng.randf_range(-20, 20), _rng.randf_range(-20, 20), 0), sz, mat)


func clear() -> void:
	_splat_used = 0
	_splat_next = 0
	_fading.clear()
	_splat_mm.visible_instance_count = 0
	_pools.clear()
	_pool_mm.visible_instance_count = 0
	_pending.clear()
	for g: RigidBody3D in _gibs:
		if is_instance_valid(g):
			g.visible = false
			g.freeze = true


func _process(delta: float) -> void:
	if not _pending.is_empty():
		var still: Array[Pending] = []
		for p: Pending in _pending:
			p.time_left -= delta
			if p.time_left <= 0.0:
				splat(p.point, p.normal, p.size, p.along)
			else:
				still.append(p)
		_pending = still
	if not _fading.is_empty():
		for i: int in _fading.keys():
			var left: float = _fading[i] - delta
			_splat_mm.set_instance_custom_data(i, Color(_splat_mm.get_instance_custom_data(i).r, maxf(left / SPLAT_FADE_TIME, 0.0), 0, 0))
			if left <= 0.0:
				_fading.erase(i)
			else:
				_fading[i] = left
	for p: Pool in _pools:
		if p.age < p.grow_time:
			p.age += delta
			_place_pool(p)
	_age_gibs(delta)


func _place_pool(p: Pool) -> void:
	var t: float = clampf(p.age / p.grow_time, 0.0, 1.0)
	var r: float = p.radius * (0.15 + 0.85 * (1.0 - pow(1.0 - t, 2.5)))
	_pool_mm.set_instance_transform(p.index, Transform3D(Basis(p.basis.x * r * 2.0, p.basis.y * r * 2.0, p.basis.z), p.origin))


func _age_gibs(delta: float) -> void:
	for g: RigidBody3D in _gibs:
		if not is_instance_valid(g) or not g.visible or g.freeze:
			continue
		var age: float = _gib_age.get(g, 0.0) + delta
		_gib_age[g] = age
		var splatted: bool = g.get_meta(&"splatted", false)
		if not splatted and g.get_contact_count() > 0 and age > 0.05:
			g.set_meta(&"splatted", true)
			var res: Dictionary = _ray(g.global_position + Vector3.UP * 0.2, g.global_position + Vector3.DOWN * 0.6)
			if not res.is_empty():
				var shape: SphereShape3D = (g.get_node(^"Shape") as CollisionShape3D).shape as SphereShape3D
				var at: Vector3 = res["position"]
				var nrm: Vector3 = res["normal"]
				splat(at, nrm, 0.16 + 0.3 * shape.radius, g.linear_velocity)
		if age > GIB_FREEZE_TIME and g.linear_velocity.length() < 0.6:
			g.freeze = true


func _splat_behind(from: Vector3, dir: Vector3, k: float) -> void:
	var res: Dictionary = _ray(from + dir * 0.05, from + dir * (2.2 + k))
	if res.is_empty():
		_drip_below(from + dir * 0.8, 0.18 + 0.05 * k)
		return
	var p: Vector3 = res["position"]
	var flight: float = from.distance_to(p) / (7.0 + 3.0 * k)
	var nrm: Vector3 = res["normal"]
	_pending.append(Pending.new(flight, p, nrm, 0.28 + 0.16 * k, dir))


func _drip_below(at: Vector3, size: float) -> void:
	var res: Dictionary = _ray(at, at + Vector3.DOWN * 2.5)
	if res.is_empty():
		return
	var p: Vector3 = res["position"]
	var nrm: Vector3 = res["normal"]
	_pending.append(Pending.new(sqrt(2.0 * maxf(at.y - p.y, 0.01) / 9.8), p, nrm, size, Vector3.ZERO))


func _ray(from: Vector3, to: Vector3) -> Dictionary:
	if not is_inside_tree():
		return {}
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
	q.collide_with_areas = false
	return get_world_3d().direct_space_state.intersect_ray(q)


func _make_mm(count: int, tex: Texture2D, cells: float, node_name: String) -> MultiMesh:
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2.ONE
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = DECAL_SHADER
	mat.set_shader_parameter(&"atlas", tex)
	mat.set_shader_parameter(&"cells", cells)
	quad.material = mat
	var mm: MultiMesh = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = quad
	mm.instance_count = count
	mm.visible_instance_count = 0
	var mmi: MultiMeshInstance3D = MultiMeshInstance3D.new()
	mmi.name = node_name
	mmi.multimesh = mm
	mmi.top_level = true
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.custom_aabb = AABB(Vector3(-200, -50, -200), Vector3(400, 100, 400))
	add_child(mmi)
	return mm


func _make_emitter(mat: Material) -> CPUParticles3D:
	var e: CPUParticles3D = CPUParticles3D.new()
	e.emitting = false
	e.one_shot = true
	e.explosiveness = 0.9
	e.local_coords = false
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2.ONE
	e.mesh = q
	e.material_override = mat
	e.direction = Vector3(0, 0, 1)
	add_child(e)
	return e


func _new_gib() -> RigidBody3D:
	var g: RigidBody3D = RigidBody3D.new()
	g.collision_layer = Ballistics.LAYER_DEBRIS
	g.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	g.contact_monitor = true
	g.max_contacts_reported = 2
	g.continuous_cd = true
	g.set_meta(&"surface", &"flesh")
	var cs: CollisionShape3D = CollisionShape3D.new()
	cs.name = "Shape"
	cs.shape = SphereShape3D.new()
	g.add_child(cs)
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.name = "Mesh"
	g.add_child(mi)
	g.top_level = true
	add_child(g)
	return g


var _chunk_mats: Array[StandardMaterial3D] = []


func _chunk_material(bone: bool) -> StandardMaterial3D:
	if _chunk_mats.is_empty():
		for c: Color in [Color(0.38, 0.03, 0.03), Color(0.8, 0.74, 0.62)]:
			var m: StandardMaterial3D = StandardMaterial3D.new()
			m.albedo_color = c
			m.roughness = 0.3
			_chunk_mats.append(m)
	return _chunk_mats[1 if bone else 0]


static func _basis_facing(dir: Vector3) -> Basis:
	var z: Vector3 = dir.normalized()
	var up: Vector3 = Vector3.UP if absf(z.y) < 0.95 else Vector3.RIGHT
	var x: Vector3 = up.cross(z).normalized()
	return Basis(x, z.cross(x), z)
