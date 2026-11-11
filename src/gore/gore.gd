extends Node3D
## Blood and gore (docs/design.md §5.5). Autoloaded as Gore.
##
## Blood is simulated as drops, not drawn as clouds (owner, 2026-11-11: "the
## blood is very simple and not simulated accurately, rather obnoxious light
## red clouds"):
## - In the air: BloodDrops. Every drop flies on its own path under gravity
##   and air drag (small drops stop and sink within half a metre, heavy ones
##   arc away), lit by the scene, one draw call for all of them. What leaves
##   a wound: fine back-spatter toward the shooter from the entry, a cone
##   along the round from the exit, a gout that carries to the wall behind;
##   a stump pumps a stream in beats (Enemy.Bleeder → spurt()); flying
##   pieces trail drops.
## - On surfaces: stains where the drops actually come down (they are traced
##   against the level when launched). A drop that lands square leaves a
##   round stain, one that lands at an angle a long one with its tail
##   pointing the way it was going (width ÷ length = the sine of the impact
##   angle, as in real bloodstain patterns); big ones on a wall run down it.
##   Stains start red and wet and dry dark. One MultiMesh: MAX_SPLATS big
##   stains and MAX_SPOTS single drops and runs; when a ring is full the
##   oldest fades out.
## - Pools grow under bodies (≤ 8, MultiMesh).
## - Gibs: severed parts and chunks as pooled rigid bodies (≤ 32), frozen
##   after a few seconds; they trail blood and stain where they land. A burst
##   body throws modelled pieces (ribs, spine, pelvis, organs, gut, meat;
##   assets/gore/gibs.gltf), a destroyed head its skull cap and jaw.
## Dismemberment rules and numbers: GoreConfig (data/gore/gore_default.tres).
## Wounds on bodies are painted by the enemy shader (src/ai/triad.gdshader),
## so they stick to the skin exactly; see EnemyBody.add_wound().
## Settings.gore_level: OFF (no blood), STANDARD, MAXIMUM (dismemberment,
## head shots that destroy the head, more blood).

enum Level { OFF, STANDARD, MAXIMUM }

## Big stains: spatter behind a wound, under a wounded man, round a burst.
const MAX_SPLATS: int = 48
## Small stains: single drops where they landed, runs down walls, smears.
const MAX_SPOTS: int = 144
const MAX_POOLS: int = 8
## Raised from 14 (2026-11-11) for whole-body gibbing: one burst throws ~20
## pieces. Each is one draw call until it's recycled; see the perf-budget
## skill. When full, small chunks go before limbs and heads (`big`).
const MAX_GIBS: int = 32
## A gib this big (radius, m) is a limb or a head: kept over chunks.
const BIG_GIB: float = 0.075
const GIB_FREEZE_TIME: float = 4.0
const SPLAT_FADE_TIME: float = 1.0
## A drop's stain is this many times wider than the drop.
const STAIN_PER_DROP: float = 4.0
## Atlas cells (assets/gore/splat_atlas.png, 4 × 4).
const CELLS_IMPACT: Array[int] = [0, 1, 2, 3]
const CELLS_FORWARD: Array[int] = [4, 5, 6, 7]
const CELLS_ROUND: Array[int] = [8, 9]
const CELLS_LONG: Array[int] = [10, 11]
const CELLS_RUN: Array[int] = [12, 13]
const CELLS_SMEAR: Array[int] = [14, 15]
const DECAL_SHADER: Shader = preload("res://src/gore/blood_decal.gdshader")
const SPLAT_TEX: Texture2D = preload("res://assets/gore/splat_atlas.png")
const POOL_TEX: Texture2D = preload("res://assets/gore/pool.png")
const GIBS_SCENE: PackedScene = preload("res://assets/gore/gibs.gltf")
const TORSO_GIBS: Array[StringName] = [&"gib_ribs", &"gib_spine", &"gib_pelvis", &"gib_organ_a", &"gib_organ_b",
		&"gib_gut", &"gib_meat_a", &"gib_meat_b", &"gib_meat_c", &"gib_ribs"]

## Dismemberment and gibbing numbers.
var config: GoreConfig = preload("res://data/gore/gore_default.tres")
## Bodies blown apart (tests, overlay).
var bursts: int = 0

## Tests switch effects off to stay deterministic.
var enabled: bool = true
## Counters for the debug overlay and tests.
var splats_placed: int = 0
var sprays_fired: int = 0

## Blood in the air.
var drops: BloodDrops

var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _splat_mm: MultiMesh
var _splat_mat: ShaderMaterial
## The two rings of stains in the one MultiMesh: [first instance, size, used, next].
var _big: Array[int] = [0, MAX_SPLATS, 0, 0]
var _spots: Array[int] = [MAX_SPLATS, MAX_SPOTS, 0, 0]
var _fading: Dictionary[int, float] = {}
## What each stain slot holds (the MultiMesh's own copy can't be read back
## under the headless renderer): where, and [cell, alpha, clock, run time].
var _stain_xform: Array[Transform3D] = []
var _stain_data: PackedColorArray = PackedColorArray()
var _pool_mm: MultiMesh
var _pool_mat: ShaderMaterial
var _pools: Array[Pool] = []
var _pool_next: int = 0
var _gibs: Array[RigidBody3D] = []
var _gib_age: Dictionary[RigidBody3D, float] = {}
## Modelled gib pieces by name, and their shared wet material.
var _gib_lib: Dictionary[StringName, Mesh] = {}
var _gib_mat: StandardMaterial3D


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
	_splat_mm = _make_mm(MAX_SPLATS + MAX_SPOTS, SPLAT_TEX, 4.0, "BloodStains")
	_splat_mat = _splat_mm.mesh.surface_get_material(0) as ShaderMaterial
	_splat_mm.visible_instance_count = MAX_SPLATS + MAX_SPOTS
	_stain_xform.resize(MAX_SPLATS + MAX_SPOTS)
	_stain_data.resize(MAX_SPLATS + MAX_SPOTS)
	_pool_mm = _make_mm(MAX_POOLS, POOL_TEX, 1.0, "BloodPools")
	_pool_mat = _pool_mm.mesh.surface_get_material(0) as ShaderMaterial
	drops = BloodDrops.new()
	add_child(drops)


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


## Stains on the world now (big ones and single drops).
func splat_count() -> int:
	return _big[2] + _spots[2]


func pool_count() -> int:
	return _pools.size()


## Drops in the air now.
func drop_count() -> int:
	return drops.live_count()


func gib_count() -> int:
	var n: int = 0
	for g: RigidBody3D in _gibs:
		if is_instance_valid(g) and g.visible:
			n += 1
	return n


func _amount() -> float:
	return config.blood_amount * (1.3 if is_maximum() else 1.0)


## A round went into (and maybe out of) a body. `scale`: how violent (1 = a
## pistol round to the torso).
## - Entry: a little fine back-spatter toward the shooter.
## - Exit (the round went through): a cone of drops along the round, faster
##   and heavier with the energy it left; a fine spray on head shots and
##   heavy hits; a gout that carries on to whatever is behind and leaves the
##   big stain there.
## - No exit: sometimes a drop falls from the wound.
func flesh_hit(hit: BallisticHit, scale: float, headshot: bool) -> void:
	if not is_on():
		return
	sprays_fired += 1
	var k: float = clampf(scale, 0.3, 4.0) * _amount()
	var back: Vector3 = (hit.normal * 0.75 - hit.direction * 0.25).normalized()
	var floor_y: float = _floor_y(hit.point)
	drops.cone(hit.point, back, roundi(4.0 * k), 0.6, 2.2 + 0.8 * k, 34.0, 0.004, 0.011, 2.2,
			1 if k > 1.2 else 0, Vector3.ZERO, floor_y, 0.9)
	if hit.result == BallisticHit.Result.PENETRATED:
		var fast: float = sqrt(k)
		drops.cone(hit.exit_point, hit.direction, mini(roundi(9.0 * k), 36), 1.5, 4.5 + 4.5 * fast, 17.0, 0.006, 0.02,
				0.9, clampi(roundi(3.0 * k), 2, 7), Vector3.ZERO, floor_y)
		if headshot or k > 1.6:
			mist(hit.exit_point, hit.direction, k)
		# The gout: the bulk of what leaves, in one piece, to the wall behind.
		var out: Vector3 = (hit.direction + Vector3(0, _rng.randf_range(-0.03, 0.1), 0)).normalized()
		drops.emit(hit.exit_point, out * (6.0 + 2.5 * fast), 0.026 + 0.006 * k, 0.35, true, floor_y, BloodDrops.MAX_FLIGHT,
				0.26 + 0.15 * k)
	elif _rng.randf() < 0.5:
		drip(hit.point, 0.012 + 0.003 * k)
	if headshot:
		drops.cone(hit.point, back + Vector3.UP * 0.35, roundi(7.0 * k), 1.0, 4.0 + 1.5 * k, 40.0, 0.006, 0.018, 1.0,
				2, Vector3.ZERO, floor_y)


## Blood flung from `at` along `dir` (a blow, a body hitting the ground, a
## piece torn off). `strength` ~ speed scale, `count` drops before the gore
## setting and the blood amount.
func spray(at: Vector3, dir: Vector3, strength: float, count: int) -> void:
	if not is_on() or count <= 0:
		return
	sprays_fired += 1
	var n: int = clampi(roundi(float(count) * _amount()), 1, 48)
	drops.cone(at, dir, n, 1.0 * strength, 5.5 * strength, 22.0, 0.006, 0.016 + 0.004 * strength, 0.9,
			clampi(n / 5, 1, 6), Vector3.ZERO, _floor_y(at))


## Blood pumped out of a cut artery: a tight stream from `at` along `dir` at
## `speed` (Enemy.Bleeder calls this through each heartbeat). `stains` of the
## `count` drops are traced and mark where the stream comes down.
func spurt(at: Vector3, dir: Vector3, speed: float, count: int, stains: int, inherit: Vector3 = Vector3.ZERO,
		floor_y: float = -INF) -> void:
	if not is_on() or count <= 0:
		return
	drops.cone(at, dir, count, speed * 0.85, speed * 1.1, 4.5, 0.009, 0.017, 0.5, stains, inherit, floor_y)


## A fine spray: drops so small the air stops them within half a metre and
## they sink (head shots, heavy exits, a piece destroyed). No stains.
func mist(at: Vector3, dir: Vector3, strength: float) -> void:
	if not is_on():
		return
	var n: int = clampi(roundi(12.0 * strength * config.blood_amount), 6, 44)
	drops.cone(at, dir, n, 1.5, 5.0 + 2.5 * strength, 46.0, 0.003, 0.007, 3.2, 0, Vector3.ZERO, _floor_y(at), 0.9)


## One drop falling from `from` (a wound on a man who is still moving).
func drip(from: Vector3, size: float = 0.014) -> void:
	if not is_on():
		return
	drops.emit(from, Vector3(_rng.randf_range(-0.25, 0.25), 0.0, _rng.randf_range(-0.25, 0.25)), size, 0.4, true, _floor_y(from))


## A big stain on the world at `point` (normal `normal`), `size` metres
## across. With `along` (a direction across the surface) it is a fan of
## spatter thrown that way from `point`; without, an impact stain.
func splat(point: Vector3, normal: Vector3, size: float, along: Vector3 = Vector3.ZERO) -> void:
	if not is_on():
		return
	var n: Vector3 = normal.normalized()
	var x: Vector3 = along - n * along.dot(n)
	var s: float = size * _rng.randf_range(0.85, 1.15)
	if x.length() > 0.05:
		x = x.normalized()
		# The fan starts at the left of its cell: move the quad so it starts at `point`.
		_stain(_big, point + x * s * 0.34, n, x, s * 1.25, s, CELLS_FORWARD[_rng.randi() % CELLS_FORWARD.size()], 0.0)
	else:
		_stain(_big, point, n, _any_tangent(n), s, s, CELLS_IMPACT[_rng.randi() % CELLS_IMPACT.size()], 0.0)


## Blood wiped along the ground from `point` toward `along` (a crawling man).
func smear(point: Vector3, normal: Vector3, along: Vector3, length: float, width: float) -> void:
	if not is_on():
		return
	var n: Vector3 = normal.normalized()
	var x: Vector3 = along - n * along.dot(n)
	if x.length() < 0.01:
		return
	x = x.normalized()
	_stain(_spots, point + x * length * 0.3, n, x, length, width, CELLS_SMEAR[_rng.randi() % CELLS_SMEAR.size()], 0.0)


## A drop reached a surface: the stain it leaves there. Its shape comes from
## how it hit: square on, a round stain; at an angle, a long one whose
## length is its width over the sine of the impact angle, tail pointing the
## way it was travelling. On a wall the bigger ones run.
func _on_landing(l: BloodDrops.Landing) -> void:
	var n: Vector3 = l.normal.normalized()
	var v: Vector3 = l.velocity
	var along: Vector3 = v - n * v.dot(n)
	var sin_a: float = clampf(absf(v.dot(n)) / maxf(v.length(), 0.01), 0.22, 1.0)
	if l.stain > 0.0:
		splat(l.point, n, l.stain, along if sin_a < 0.8 else Vector3.ZERO)
		if absf(n.y) < 0.5:
			_run(l.point, n, l.stain * 0.09)
		return
	var w: float = l.size * STAIN_PER_DROP * _rng.randf_range(0.85, 1.25)
	if sin_a > 0.8 or along.length() < 0.05:
		# The round drop fills 0.45 of its cell.
		_stain(_spots, l.point, n, _any_tangent(n), w / 0.45, w / 0.45, CELLS_ROUND[_rng.randi() % CELLS_ROUND.size()], 0.0)
	else:
		var x: Vector3 = along.normalized()
		var length: float = minf(w / sin_a, w * 4.5)
		# The long drop's body is 0.46 of its cell long and 0.22 wide, centred at 0.36.
		var qx: float = length / 0.46
		_stain(_spots, l.point + x * qx * 0.14, n, x, qx, w / 0.22, CELLS_LONG[_rng.randi() % CELLS_LONG.size()], 0.0)
	if absf(n.y) < 0.5 and l.size >= 0.013 and _rng.randf() < 0.6:
		_run(l.point, n, w)


## Blood running down a wall from `point`: uncovered from the top over a few seconds.
func _run(point: Vector3, n: Vector3, width: float) -> void:
	var up: Vector3 = Vector3.UP - n * n.y
	if up.length() < 0.2:
		return
	up = up.normalized()
	var x: Vector3 = up.cross(n).normalized()
	var h: float = clampf(width * _rng.randf_range(7.0, 13.0), 0.12, 0.7)
	# The run's bead sits 0.13 down its cell, its trail is 0.1 of the cell wide.
	_stain(_spots, point - up * h * 0.37, n, x, maxf(width * 4.0, 0.08), h, CELLS_RUN[_rng.randi() % CELLS_RUN.size()],
			_rng.randf_range(2.5, 5.0), up)


## Writes a stain into a ring. `x`: its +X on the surface, `sx`/`sy`: size
## across (m), `run_time`: seconds a run takes to reach its end (0: all at
## once), `y`: its up, when it must be exact (runs).
func _stain(ring: Array[int], point: Vector3, n: Vector3, x: Vector3, sx: float, sy: float, cell: int, run_time: float,
		y: Vector3 = Vector3.ZERO) -> void:
	var size: int = ring[1]
	var i: int = ring[0] + ring[3]
	ring[3] = (ring[3] + 1) % size
	if ring[2] < size:
		ring[2] += 1
	else:
		# Ring full: the next-oldest starts fading so the cap holds without pops.
		_fading[ring[0] + ring[3]] = SPLAT_FADE_TIME
	_fading.erase(i)
	var yy: Vector3 = y if y != Vector3.ZERO else n.cross(x)
	_stain_xform[i] = Transform3D(Basis(x * sx, yy * sy, n), point + n * 0.003)
	_stain_data[i] = Color(float(cell), 1.0, drops.clock, run_time)
	_splat_mm.set_instance_transform(i, _stain_xform[i])
	_splat_mm.set_instance_custom_data(i, _stain_data[i])
	splats_placed += 1


## The stain in slot `i` (0 .. MAX_SPLATS - 1 big ones, then the single
## drops): its quad on the surface; a zero basis if the slot is empty.
func stain_transform(i: int) -> Transform3D:
	return _stain_xform[i]


## Its atlas cell (see CELLS_*), and the seconds a run takes (0: not a run).
func stain_cell(i: int) -> int:
	return roundi(_stain_data[i].r)


func stain_run_time(i: int) -> float:
	return _stain_data[i].a


func _any_tangent(n: Vector3) -> Vector3:
	var up: Vector3 = Vector3.UP if absf(n.y) < 0.95 else Vector3.RIGHT
	return up.cross(n).normalized().rotated(n, _rng.randf() * TAU)


## Height of the floor under `at` (-INF if there is none within 3 m).
func _floor_y(at: Vector3) -> float:
	var res: Dictionary = _ray(at + Vector3.UP * 0.1, at + Vector3.DOWN * 3.0)
	if res.is_empty():
		return -INF
	var p: Vector3 = res["position"]
	return p.y


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
	p.origin = hit_at + n * (0.0035 + 0.0002 * float(p.index))
	p.radius = radius * _rng.randf_range(0.85, 1.2)
	p.age = 0.0
	p.grow_time = 7.0 if is_maximum() else 9.0
	_pool_mm.visible_instance_count = _pools.size()
	_pool_mm.set_instance_custom_data(p.index, Color(0.0, 1.0, drops.clock, 0.0))
	_place_pool(p)


## Throws a gib: `mesh` posed at `xform`, with velocity, bleeding as it flies.
## Returns the body (or null when gore is off).
func throw_gib(mesh: Mesh, xform: Transform3D, velocity: Vector3, spin: Vector3, radius: float,
		material: Material = null, mesh_scale: float = 1.0) -> RigidBody3D:
	if not is_on() or mesh == null:
		return null
	var g: RigidBody3D
	if _gibs.size() < MAX_GIBS:
		g = _new_gib()
		_gibs.append(g)
	else:
		g = _oldest_gib(radius < BIG_GIB)
		if g == null:
			return null  # every slot holds a limb or a head: skip the chunk
	_gib_serial += 1
	g.set_meta(&"born", _gib_serial)
	g.set_meta(&"thrown_at", drops.clock)
	g.set_meta(&"big", radius >= BIG_GIB)
	var mi: MeshInstance3D = g.get_node(^"Mesh") as MeshInstance3D
	mi.mesh = mesh
	mi.material_override = material
	mi.scale = Vector3.ONE * mesh_scale
	# A box the size of the piece, round its middle (gib meshes are centred
	# on their own middle: EnemyBody.gib_mesh), so it lands and stops
	# where it looks like it should instead of rolling on a ball.
	var cs: CollisionShape3D = g.get_node(^"Shape") as CollisionShape3D
	var box: BoxShape3D = cs.shape as BoxShape3D
	var aabb: AABB = mesh.get_aabb()
	box.size = (aabb.size * mesh_scale).max(Vector3.ONE * 0.04)
	cs.position = aabb.get_center() * mesh_scale
	g.set_meta(&"radius", radius)
	g.freeze = false
	g.visible = true
	g.collision_layer = Ballistics.LAYER_DEBRIS
	g.global_transform = xform
	g.linear_velocity = velocity
	g.angular_velocity = spin
	g.mass = clampf(radius * 20.0, 0.3, 5.0)
	g.set_meta(&"splatted", false)
	g.set_meta(&"trail", 0.0)
	g.set_meta(&"floor_y", _floor_y(xform.origin))
	_gib_age[g] = 0.0
	return g


var _gib_serial: int = 0


## A limb or head that has lain this long (s) can be recycled for a chunk.
const GIB_KEEP_TIME: float = 20.0


## The gib to recycle. One that was cleared away first. Else the oldest
## small one. Else, for a limb or a head, the oldest of all; for a chunk,
## the oldest limb that has lain for GIB_KEEP_TIME (a chunk never pushes
## out a limb that just landed, but a long fight mustn't end with every
## slot held by old limbs and nothing left for a burst to throw).
func _oldest_gib(small: bool) -> RigidBody3D:
	var best: RigidBody3D = null
	var best_any: RigidBody3D = null
	var best_born: int = 0
	var any_born: int = 0
	for g: RigidBody3D in _gibs:
		if not g.visible:
			return g
		var born: int = g.get_meta(&"born", 0)
		var big: bool = g.get_meta(&"big", false)
		if best_any == null or born < any_born:
			best_any = g
			any_born = born
		if not big and (best == null or born < best_born):
			best = g
			best_born = born
	if best:
		return best
	if small:
		var landed: float = best_any.get_meta(&"thrown_at", 0.0)
		return best_any if drops.clock - landed > GIB_KEEP_TIME else null
	return best_any


## The modelled gib meshes (loaded once).
func gib_piece(name: StringName) -> Mesh:
	if _gib_lib.is_empty():
		var root: Node = GIBS_SCENE.instantiate()
		for n: Node in root.find_children("*", "MeshInstance3D", true, false):
			var mi: MeshInstance3D = n as MeshInstance3D
			_gib_lib[StringName(mi.name)] = mi.mesh
		root.free()
		_gib_mat = StandardMaterial3D.new()
		_gib_mat.vertex_color_use_as_albedo = true
		_gib_mat.roughness = 0.28
		_gib_mat.metallic_specular = 0.6
	return _gib_lib.get(name)


func _gib_radius(m: Mesh) -> float:
	return clampf(m.get_aabb().size.length() * 0.35, 0.03, 0.12)


## A head blown apart: skull cap, jaw and chunks thrown, blood up and out in
## every direction (it comes down as a ring of drops), a fine spray.
func burst_head(at: Vector3, velocity: Vector3) -> void:
	if not is_maximum():
		return
	var dir: Vector3 = velocity.normalized() if velocity.length() > 0.1 else Vector3.UP
	for piece: StringName in [&"gib_skull", &"gib_jaw"]:
		var m: Mesh = gib_piece(piece)
		if m:
			var v: Vector3 = (dir + Vector3(_rng.randf_range(-0.6, 0.6), _rng.randf_range(0.2, 0.9), _rng.randf_range(-0.6, 0.6))).normalized()
			throw_gib(m, Transform3D(Basis.from_euler(Vector3(_rng.randf() * TAU, _rng.randf() * TAU, 0)), at),
					v * maxf(velocity.length(), 4.0) * _rng.randf_range(0.6, 1.1), _spin(18.0), _gib_radius(m), _gib_mat)
	burst_chunks(at, dir + Vector3.UP * 0.3, 5, 6.0)
	sprays_fired += 1
	var k: float = config.blood_amount
	var floor_y: float = _floor_y(at)
	drops.cone(at, dir + Vector3.UP * 0.5, roundi(34.0 * k), 1.5, 8.0, 60.0, 0.007, 0.024, 0.8, 9, Vector3.ZERO, floor_y)
	drops.cone(at, Vector3.UP, roundi(14.0 * k), 1.0, 4.5, 80.0, 0.007, 0.02, 0.8, 4, Vector3.ZERO, floor_y)
	mist(at, dir, 2.2)
	drops.emit(at, (dir + Vector3.UP * 0.25).normalized() * 7.0, 0.032, 0.35, true, floor_y, BloodDrops.MAX_FLIGHT, 0.5)


## A torso blown apart: ribs, spine, pelvis, organs, gut and meat flung out,
## blood thrown all round (it lands on everything near), a pool where it stood.
func burst_torso(at: Vector3, velocity: Vector3) -> void:
	if not is_on():
		return
	bursts += 1
	sprays_fired += 1
	var push: Vector3 = velocity.limit_length(8.0)
	if is_maximum():
		var n: int = mini(config.gib_torso_pieces, TORSO_GIBS.size())
		for i: int in n:
			var m: Mesh = gib_piece(TORSO_GIBS[i])
			if m == null:
				continue
			var out: Vector3 = Vector3(_rng.randf_range(-1, 1), _rng.randf_range(0.1, 1.0), _rng.randf_range(-1, 1)).normalized()
			var v: Vector3 = push * 0.5 + out * config.gib_speed * _rng.randf_range(0.5, 1.2)
			var at_i: Vector3 = at + out * 0.12 + Vector3.DOWN * 0.1 * float(i % 3)
			throw_gib(m, Transform3D(Basis.from_euler(Vector3(_rng.randf() * TAU, _rng.randf() * TAU, _rng.randf() * TAU)), at_i),
					v, _spin(14.0), _gib_radius(m), _gib_mat)
		burst_chunks(at, push.normalized() + Vector3.UP * 0.4, 4, config.gib_speed)
	var k: float = _amount()
	var floor_y: float = _floor_y(at)
	# All round and upward: three wide cones a third of a turn apart, carried by the push.
	var turn: float = _rng.randf() * TAU
	for i: int in 3:
		var a: float = turn + TAU * float(i) / 3.0
		var d: Vector3 = Vector3(cos(a), _rng.randf_range(0.3, 0.9), sin(a)).normalized()
		drops.cone(at, d, roundi(26.0 * k), 2.0, 9.5, 55.0, 0.008, 0.026, 0.7, 5, push * 0.4, floor_y)
		# A gout each way: the big stains on the walls and floor round it.
		drops.emit(at, d * _rng.randf_range(5.0, 8.0) + push * 0.4, 0.034, 0.35, true, floor_y, BloodDrops.MAX_FLIGHT,
				_rng.randf_range(0.4, 0.65))
	mist(at, Vector3.UP, 2.4)
	pool_under(at, 0.8)


func _spin(k: float) -> Vector3:
	return Vector3(_rng.randf_range(-k, k), _rng.randf_range(-k, k), _rng.randf_range(-k, k))


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
		var mesh: Mesh = box
		var scale: float = 1.0
		if i % 3 == 1 and gib_piece(&"gib_meat_b"):
			# Every third a torn piece of meat, shrunk to the chunk's size.
			var meat: Array[StringName] = [&"gib_meat_a", &"gib_meat_b", &"gib_meat_c"]
			mesh = gib_piece(meat[i % 3 + (i / 3) % 2])
			mat = _gib_mat
			scale = sz / 0.05
		throw_gib(mesh, Transform3D(Basis.from_euler(Vector3(_rng.randf() * TAU, _rng.randf() * TAU, 0)), at),
				v * speed * _rng.randf_range(0.4, 1.0), Vector3(_rng.randf_range(-20, 20), _rng.randf_range(-20, 20), 0), sz, mat, scale)


func clear() -> void:
	_big[2] = 0
	_big[3] = 0
	_spots[2] = 0
	_spots[3] = 0
	_fading.clear()
	var gone: Transform3D = Transform3D(Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO), Vector3.ZERO)
	for i: int in MAX_SPLATS + MAX_SPOTS:
		_splat_mm.set_instance_transform(i, gone)
		_stain_xform[i] = gone
	_pools.clear()
	_pool_mm.visible_instance_count = 0
	drops.clear()
	for g: RigidBody3D in _gibs:
		if is_instance_valid(g):
			g.visible = false
			g.freeze = true
			g.collision_layer = 0  # hidden gibs mustn't stop rounds (throw_gib turns it back on)


func _process(delta: float) -> void:
	for l: BloodDrops.Landing in drops.advance(delta):
		_on_landing(l)
	_splat_mat.set_shader_parameter(&"now", drops.clock)
	_pool_mat.set_shader_parameter(&"now", drops.clock)
	if not _fading.is_empty():
		for i: int in _fading.keys():
			var left: float = _fading[i] - delta
			var c: Color = _stain_data[i]
			c.g = maxf(left / SPLAT_FADE_TIME, 0.0)
			_stain_data[i] = c
			_splat_mm.set_instance_custom_data(i, c)
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


## Flying pieces trail drops for their first second and a half (more the
## bigger and faster they are) and stain where they first touch down.
func _age_gibs(delta: float) -> void:
	for g: RigidBody3D in _gibs:
		if not is_instance_valid(g) or not g.visible or g.freeze:
			continue
		var age: float = _gib_age.get(g, 0.0) + delta
		_gib_age[g] = age
		var gib_r: float = g.get_meta(&"radius", 0.05)
		var v: Vector3 = g.linear_velocity
		var splatted: bool = g.get_meta(&"splatted", false)
		if age < 1.5 and gib_r >= 0.03 and v.length() > 1.5:
			var trail: float = g.get_meta(&"trail", 0.0)
			trail += delta * (10.0 + 160.0 * gib_r) * config.blood_amount
			while trail >= 1.0:
				trail -= 1.0
				var side: Vector3 = Vector3(_rng.randf_range(-1, 1), _rng.randf_range(-0.3, 1), _rng.randf_range(-1, 1)) * 0.8
				var size: float = _rng.randf_range(0.006, 0.014)
				var floor_y: float = g.get_meta(&"floor_y", -INF)
				drops.emit(g.global_position, v * 0.55 + side, size, BloodDrops.drag_for(size, 0.9), _rng.randf() < 0.25, floor_y)
			g.set_meta(&"trail", trail)
		if not splatted and g.get_contact_count() > 0 and age > 0.05:
			g.set_meta(&"splatted", true)
			var res: Dictionary = _ray(g.global_position + Vector3.UP * 0.2, g.global_position + Vector3.DOWN * 0.6)
			if not res.is_empty():
				var at: Vector3 = res["position"]
				var nrm: Vector3 = res["normal"]
				splat(at, nrm, 0.16 + 0.3 * gib_r, v if v.length() > 2.0 else Vector3.ZERO)
		if age > GIB_FREEZE_TIME and v.length() < 0.6:
			g.freeze = true


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
	mm.use_custom_data = true
	mm.mesh = quad
	mm.instance_count = count
	mm.visible_instance_count = 0
	for i: int in count:
		mm.set_instance_transform(i, Transform3D(Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO), Vector3.ZERO))
	var mmi: MultiMeshInstance3D = MultiMeshInstance3D.new()
	mmi.name = node_name
	mmi.multimesh = mm
	mmi.top_level = true
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.custom_aabb = AABB(Vector3(-200, -50, -200), Vector3(400, 100, 400))
	add_child(mmi)
	return mm


func _new_gib() -> RigidBody3D:
	var g: RigidBody3D = RigidBody3D.new()
	g.collision_layer = Ballistics.LAYER_DEBRIS
	g.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	g.contact_monitor = true
	g.max_contacts_reported = 2
	g.continuous_cd = true
	g.set_meta(&"surface", &"flesh")
	# Wet meat: grips, doesn't bounce, stops tumbling soon.
	var pm: PhysicsMaterial = PhysicsMaterial.new()
	pm.friction = 1.0
	pm.bounce = 0.05
	pm.rough = true
	g.physics_material_override = pm
	g.angular_damp = 1.5
	g.linear_damp = 0.2
	var cs: CollisionShape3D = CollisionShape3D.new()
	cs.name = "Shape"
	cs.shape = BoxShape3D.new()
	g.add_child(cs)
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.name = "Mesh"
	# No shadows: up to 32 gibs would add a shadow pass draw each.
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
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
