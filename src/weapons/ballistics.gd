extends Node3D
## Ballistic simulation (docs/design.md §5.2). Autoloaded as Ballistics.
##
## Rounds are real projectiles stepped every physics tick with ray segments:
## gravity drop, air drag, travel time. At 650 m/s a segment is ~11 m, so it
## costs no more than hitscan but the physics are honest. The first step runs
## the instant the gun fires, so close shots land on the same frame.
##
## On contact the round either glances off (shallow angle on hard material),
## punches through (measured thickness × material resistance < its energy),
## or stops and dumps its energy. Exits are slower and slightly deflected.
## Whatever was hit gets `on_ballistic_hit(hit: BallisticHit)` if it has it;
## rigid bodies are pushed by the momentum the round lost.

## Physics layers (project.godot [layer_names]).
const LAYER_WORLD: int = 1
const LAYER_PLAYER: int = 2
const LAYER_HITBOX: int = 4
const LAYER_PROPS: int = 8
const LAYER_DEBRIS: int = 16
const BULLET_MASK: int = LAYER_WORLD | LAYER_HITBOX | LAYER_PROPS | LAYER_DEBRIS

const MAX_LIFETIME: float = 3.0
const MIN_SPEED: float = 40.0
const MAX_CONTACTS_PER_STEP: int = 10
const MAX_THICKNESS_PROBE: float = 1.2
const TRAJECTORY_KEEP: int = 14
## Pooled tracer streaks (CLAUDE.md §8: a tracer every few rounds).
const TRACER_POOL: int = 12
const TRACER_LENGTH: float = 7.0
const TRACER_WIDTH: float = 0.035
## Most speed one round can give a loose prop, m/s (keeps cans on the planet).
const MAX_PROP_DV: float = 9.0
## Railgun trails (WeaponData.beam_trail_time): pooled, a few segments each
## (one per stretch between surfaces), drawn up to TRAIL_MAX_LENGTH.
const TRAIL_POOL: int = 6
const TRAIL_SEGMENTS: int = 10
const TRAIL_MAX_LENGTH: float = 400.0
const TRAIL_SHADER: Shader = preload("res://src/vfx/rail_trail.gdshader")

## Draws the last few trajectories (tuning menu / range toggle).
var show_trajectories: bool = false:
	set(v):
		show_trajectories = v
		_lines.visible = v
		_dirty = true

var _live: Array[Projectile] = []
var _paths: Array[Projectile] = []
var _next_id: int = 1
var _lines: MeshInstance3D
var _mesh: ImmediateMesh
var _dirty: bool = false
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _tracers: Array[MeshInstance3D] = []
var _tracer_next: int = 0
## Tracers whose round stopped last frame: node -> round id.
var _tracer_fading: Dictionary[MeshInstance3D, int] = {}
var _trails: Array[Trail] = []
var _trail_next: int = 0


## One ionized-air trail: a chain of glowing cylinders sharing a material.
class Trail:
	extends RefCounted
	var segments: Array[MeshInstance3D] = []
	## Segment ends (start, end) in use, for re-widening as the trail ages.
	var ends: PackedVector3Array = PackedVector3Array()
	var used: int = 0
	var material: ShaderMaterial
	var age: float = 0.0
	var life: float = 0.0
	var width: float = 0.01
	var length: float = 0.0
	var owner_id: int = 0
	var last: Vector3

	func visible() -> bool:
		return used > 0 and age < life


class Projectile:
	extends RefCounted
	var id: int = 0
	var weapon: WeaponData
	var shooter: Node
	var position: Vector3
	var velocity: Vector3
	var mass_kg: float = 0.002
	var age: float = 0.0
	var travelled: float = 0.0
	var penetrations: int = 0
	var ricochets: int = 0
	var alive: bool = true
	## Trajectory for the debug view: point, then speed at that point.
	var path: PackedVector3Array = PackedVector3Array()
	var path_speed: PackedFloat32Array = PackedFloat32Array()
	var muzzle_speed: float = 1.0
	## Tracer streak drawn from `tracer_tail` (starts at the muzzle) to the round.
	var tracer: MeshInstance3D
	var tracer_tail: Vector3
	## Railgun trail and how far into `path` it has been drawn.
	var trail: Trail
	var trail_index: int = 1

	func energy() -> float:
		return 0.5 * mass_kg * velocity.length_squared()

	func record(p: Vector3) -> void:
		path.append(p)
		path_speed.append(velocity.length())


func _ready() -> void:
	process_physics_priority = -10  # step rounds before targets read their state
	_rng.randomize()
	_mesh = ImmediateMesh.new()
	_lines = MeshInstance3D.new()
	_lines.mesh = _mesh
	_lines.top_level = true
	_lines.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.vertex_color_use_as_albedo = true
	mat.no_depth_test = false
	_lines.material_override = mat
	_lines.visible = false
	add_child(_lines)
	var streak: BoxMesh = BoxMesh.new()
	streak.size = Vector3(TRACER_WIDTH, TRACER_WIDTH, 1.0)
	var glow: StandardMaterial3D = StandardMaterial3D.new()
	glow.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glow.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	glow.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glow.albedo_color = Color(1.0, 0.55, 0.22, 0.9)
	glow.disable_receive_shadows = true
	for i: int in TRACER_POOL:
		var t: MeshInstance3D = MeshInstance3D.new()
		t.mesh = streak
		t.material_override = glow
		t.top_level = true
		t.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		t.visible = false
		add_child(t)
		_tracers.append(t)
	# Camera-facing ribbon (turned in rail_trail.gdshader), 1 m long along Y.
	var tube: QuadMesh = QuadMesh.new()
	tube.size = Vector2.ONE
	for i: int in TRAIL_POOL:
		var trail: Trail = Trail.new()
		trail.material = ShaderMaterial.new()
		trail.material.shader = TRAIL_SHADER
		for k: int in TRAIL_SEGMENTS:
			var seg: MeshInstance3D = MeshInstance3D.new()
			seg.mesh = tube
			seg.material_override = trail.material
			seg.top_level = true
			seg.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			seg.extra_cull_margin = 1.0  # the shader turns the ribbon off its flat AABB
			seg.visible = false
			add_child(seg)
			trail.segments.append(seg)
		_trails.append(trail)


## Fires one round. `direction` is normalised. Returns the shot id.
## `tracer_from`: a finite point (the muzzle) makes this round a visible tracer
## (or, for guns with `beam_trail_time`, starts its ionized trail there).
## `power`: energy fraction (railgun capacitor charge); speed goes with √power.
func fire(weapon: WeaponData, origin: Vector3, direction: Vector3, shooter: Node = null,
		tracer_from: Vector3 = Vector3.INF, power: float = 1.0) -> int:
	var p: Projectile = Projectile.new()
	p.id = _next_id
	_next_id += 1
	p.weapon = weapon
	p.shooter = shooter
	p.position = origin
	var speed: float = weapon.muzzle_velocity * sqrt(clampf(power, 0.01, 4.0))
	p.velocity = direction.normalized() * speed
	p.mass_kg = weapon.bullet_mass_g * 0.001
	p.muzzle_speed = speed
	p.record(origin)
	if tracer_from.is_finite() and weapon.beam_trail_time > 0.0:
		p.trail = _claim_trail(p.id, weapon, tracer_from)
	elif tracer_from.is_finite():
		p.tracer = _tracers[_tracer_next]
		_tracer_next = (_tracer_next + 1) % _tracers.size()
		p.tracer_tail = tracer_from
	_live.append(p)
	_paths.append(p)
	if _paths.size() > TRAJECTORY_KEEP:
		_paths.pop_front()
	# Resolve the first tick now: point-blank shots land on the trigger frame.
	_step(p, 1.0 / Engine.physics_ticks_per_second * Engine.time_scale)
	_update_tracer(p)
	_extend_trail(p)
	if not p.alive:
		_live.erase(p)
	_dirty = true
	return p.id


## Live railgun trails (tests, debug overlay).
func trail_count() -> int:
	var n: int = 0
	for t: Trail in _trails:
		if t.visible():
			n += 1
	return n


## Total drawn length of the newest trail, metres (tests).
func newest_trail_length() -> float:
	var t: Trail = _trails[(_trail_next - 1 + _trails.size()) % _trails.size()]
	return t.length


func _claim_trail(id: int, weapon: WeaponData, from: Vector3) -> Trail:
	var t: Trail = _trails[_trail_next]
	_trail_next = (_trail_next + 1) % _trails.size()
	for seg: MeshInstance3D in t.segments:
		seg.visible = false
	t.ends.clear()
	t.used = 0
	t.age = 0.0
	t.length = 0.0
	t.life = weapon.beam_trail_time
	t.width = weapon.beam_trail_width
	t.owner_id = id
	t.last = from
	t.material.set_shader_parameter(&"color", weapon.beam_trail_color)
	t.material.set_shader_parameter(&"fade", 1.0)
	t.material.set_shader_parameter(&"age", 0.0)
	return t


## Adds the round's newly recorded path points to its trail.
func _extend_trail(p: Projectile) -> void:
	var t: Trail = p.trail
	if t == null:
		return
	if t.owner_id != p.id:
		p.trail = null  # the pool slot went to a newer round
		return
	while p.trail_index < p.path.size() and t.length < TRAIL_MAX_LENGTH:
		var point: Vector3 = p.path[p.trail_index]
		p.trail_index += 1
		var span: Vector3 = point - t.last
		if span.length() < 0.01:
			continue
		var dir: Vector3 = span.normalized()
		# Straight on from the last segment (free flight, or a clean pass through): stretch it.
		if t.used > 0:
			var a: Vector3 = t.ends[(t.used - 1) * 2]
			var b: Vector3 = t.ends[(t.used - 1) * 2 + 1]
			if (b - a).normalized().dot(dir) > 0.99995:
				t.ends[(t.used - 1) * 2 + 1] = point
				t.length += span.length()
				t.last = point
				_place_segment(t, t.used - 1)
				continue
		if t.used >= t.segments.size():
			break
		t.ends.append(t.last)
		t.ends.append(point)
		t.used += 1
		t.length += span.length()
		t.last = point
		_place_segment(t, t.used - 1)
	if not p.alive:
		p.trail = null


func _place_segment(t: Trail, i: int) -> void:
	var a: Vector3 = t.ends[i * 2]
	var b: Vector3 = t.ends[i * 2 + 1]
	var span: Vector3 = b - a
	var length: float = span.length()
	if length < 0.001:
		return
	var y: Vector3 = span / length
	var helper: Vector3 = Vector3.UP if absf(y.y) < 0.95 else Vector3.RIGHT
	var x: Vector3 = helper.cross(y).normalized()
	var z: Vector3 = x.cross(y)
	# The trail spreads as the ionized air expands.
	var w: float = t.width * (1.0 + 2.5 * t.age / maxf(t.life, 0.01))
	var seg: MeshInstance3D = t.segments[i]
	seg.global_transform = Transform3D(Basis(x * w, y * length, z * w), a + span * 0.5)
	seg.visible = true


func _process(delta: float) -> void:
	for t: Trail in _trails:
		if t.used == 0:
			continue
		t.age += delta
		if t.age >= t.life:
			for seg: MeshInstance3D in t.segments:
				seg.visible = false
			t.used = 0
			continue
		var k: float = t.age / t.life
		t.material.set_shader_parameter(&"fade", (1.0 - k) * (1.0 - k))
		t.material.set_shader_parameter(&"age", t.age)
		for i: int in t.used:
			_place_segment(t, i)


## Live tracer streaks (debug overlay / tests).
func tracer_count() -> int:
	var n: int = 0
	for t: MeshInstance3D in _tracers:
		if t.visible:
			n += 1
	return n


func _update_tracer(p: Projectile) -> void:
	if p.tracer == null:
		return
	var owner_id: int = p.tracer.get_meta(&"owner", 0)
	if owner_id != 0 and owner_id != p.id:
		p.tracer = null  # the pool slot went to a newer round
		return
	var head: Vector3 = p.position
	var span: Vector3 = head - p.tracer_tail
	var length: float = span.length()
	if length > 0.05:
		if length > TRACER_LENGTH:
			p.tracer_tail = head - span / length * TRACER_LENGTH
			length = TRACER_LENGTH
		var dir: Vector3 = span / span.length()
		var up: Vector3 = Vector3.UP if absf(dir.y) < 0.95 else Vector3.RIGHT
		var basis: Basis = Basis.looking_at(dir, up)
		basis.z = basis.z * length  # the streak mesh is 1 m long along its local Z
		p.tracer.global_transform = Transform3D(basis, head - dir * length * 0.5)
		p.tracer.set_meta(&"owner", p.id)
		p.tracer.visible = true
		# Next frame the streak starts behind where this one's head is.
		p.tracer_tail = head - dir * minf(length, TRACER_LENGTH * 0.6)
	if not p.alive:
		# Show the last segment (to the impact) for one frame, then hide.
		_tracer_fading[p.tracer] = p.id
		p.tracer = null


func live_count() -> int:
	return _live.size()


func clear() -> void:
	_live.clear()
	_paths.clear()
	_dirty = true


func _physics_process(delta: float) -> void:
	for t: MeshInstance3D in _tracer_fading:
		if t.get_meta(&"owner", 0) == _tracer_fading[t]:
			t.visible = false
			t.set_meta(&"owner", 0)
	_tracer_fading.clear()
	if not _live.is_empty():
		for p: Projectile in _live:
			_step(p, delta)
			_update_tracer(p)
			_extend_trail(p)
		var still: Array[Projectile] = []
		for p: Projectile in _live:
			if p.alive:
				still.append(p)
		_live = still
		_dirty = true
	if _dirty and show_trajectories:
		_rebuild_lines()
	_dirty = false


func _step(p: Projectile, delta: float) -> void:
	if not p.alive or delta <= 0.0:
		return
	var w: WeaponData = p.weapon
	var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
	# Drag: dv/dt = -k v², integrated exactly over the step for the speed.
	var speed: float = p.velocity.length()
	var new_speed: float = speed / (1.0 + w.drag_per_m * speed * delta)
	p.velocity = p.velocity * (new_speed / maxf(speed, 0.001))
	p.velocity.y -= gravity * w.gravity_scale * delta
	var remaining: float = p.velocity.length() * delta
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var contacts: int = 0
	while remaining > 0.0005 and p.alive and contacts < MAX_CONTACTS_PER_STEP:
		var dir: Vector3 = p.velocity.normalized()
		var to: Vector3 = p.position + dir * remaining
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(p.position, to, BULLET_MASK)
		q.hit_back_faces = false
		q.collide_with_areas = false
		var res: Dictionary = space.intersect_ray(q)
		if res.is_empty():
			p.travelled += remaining
			p.position = to
			break
		contacts += 1
		var point: Vector3 = res["position"]
		var travelled: float = p.position.distance_to(point)
		p.travelled += travelled
		remaining -= travelled
		p.position = point
		p.record(point)
		var after: Vector3 = _contact(p, res, space)
		# Spend what's left of this tick's travel along the new direction.
		var used: float = p.position.distance_to(after)
		p.position = after
		remaining = maxf(0.0, remaining - used) * (p.velocity.length() / maxf(speed, 1.0))
	p.age += delta
	if p.alive:
		p.record(p.position)
	if p.age > MAX_LIFETIME or p.travelled > w.max_range or p.velocity.length() < MIN_SPEED:
		p.alive = false


## Handles one contact. Returns where the round continues from.
func _contact(p: Projectile, res: Dictionary, space: PhysicsDirectSpaceState3D) -> Vector3:
	var w: WeaponData = p.weapon
	var collider: Object = res["collider"]
	var surface: SurfaceMaterial = SurfaceLibrary.shared().for_collider(collider)
	var normal: Vector3 = res["normal"]
	var point: Vector3 = res["position"]
	var dir: Vector3 = p.velocity.normalized()

	var hit: BallisticHit = BallisticHit.new()
	hit.shot_id = p.id
	hit.weapon = w
	hit.shooter = p.shooter
	hit.collider = collider
	hit.surface = surface
	hit.point = point
	hit.normal = normal
	hit.direction = dir
	hit.speed_in = p.velocity.length()
	hit.energy_in = p.energy()
	hit.prior_penetrations = p.penetrations
	hit.distance = p.travelled

	var next_pos: Vector3 = point + normal * 0.002
	# Glancing angle: 0 = skimming the surface, 90 = straight in.
	var graze_deg: float = 90.0 - rad_to_deg(dir.angle_to(-normal))
	var can_ricochet: bool = surface.ricochet_chance > 0.0 and p.ricochets < w.max_ricochets \
			and graze_deg < surface.ricochet_max_angle_deg
	if can_ricochet and _rng.randf() < surface.ricochet_chance * (1.0 - graze_deg / maxf(surface.ricochet_max_angle_deg, 0.01)):
		hit.result = BallisticHit.Result.RICOCHET
		var out_dir: Vector3 = dir.bounce(normal).normalized()
		out_dir = _scatter(out_dir, 4.0).normalized()
		if out_dir.dot(normal) < 0.02:
			out_dir = (out_dir + normal * 0.05).normalized()
		hit.energy_out = hit.energy_in * surface.ricochet_energy_keep
		p.velocity = out_dir * sqrt(2.0 * hit.energy_out / p.mass_kg)
		p.ricochets += 1
	else:
		var exit: Dictionary = {}
		if p.penetrations < w.max_penetrations and surface.resistance_j_per_cm > 0.0:
			exit = _find_exit(space, collider, point, dir, hit.energy_in, w, surface, hit.speed_in)
		elif surface.resistance_j_per_cm <= 0.0:
			exit = {"position": point + dir * 0.001, "normal": -normal}
		if exit.is_empty():
			hit.result = BallisticHit.Result.STOPPED
			hit.energy_out = 0.0
			p.velocity = Vector3.ZERO
			p.alive = false
		else:
			var exit_point: Vector3 = exit["position"]
			hit.result = BallisticHit.Result.PENETRATED
			hit.exit_point = exit_point
			hit.exit_normal = exit["normal"]
			hit.thickness = point.distance_to(exit_point)
			hit.energy_out = maxf(0.0, hit.energy_in - w.penetration_cost(surface, hit.thickness, hit.speed_in))
			var out_dir: Vector3 = _scatter(dir, surface.exit_deflection_deg * (1.0 - hit.energy_out / hit.energy_in))
			p.velocity = out_dir * sqrt(2.0 * hit.energy_out / p.mass_kg)
			p.penetrations += 1
			next_pos = exit_point + out_dir * 0.002
			p.record(exit_point)
	hit.speed_out = p.velocity.length()
	hit.damage = _make_damage(hit, collider)
	_push(collider, hit, p.mass_kg)
	if collider.has_method(&"on_ballistic_hit"):
		collider.call(&"on_ballistic_hit", hit)
	EventBus.ballistic_hit.emit(hit)
	return next_pos


## Finds where the round would leave `collider`: casts back from the far end
## of the furthest it could possibly travel inside the material.
func _find_exit(space: PhysicsDirectSpaceState3D, collider: Object, point: Vector3, dir: Vector3,
		energy: float, w: WeaponData, surface: SurfaceMaterial, speed: float = 0.0) -> Dictionary:
	var max_t: float = minf(energy / maxf(w.penetration_cost(surface, 1.0, speed), 0.001), MAX_THICKNESS_PROBE)
	if max_t < 0.0005:
		return {}
	var far: Vector3 = point + dir * (max_t + 0.002)
	var near: Vector3 = point + dir * 0.0005
	var exclude: Array[RID] = []
	for i: int in 6:
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(far, near, BULLET_MASK, exclude)
		q.hit_back_faces = false
		q.collide_with_areas = false
		var res: Dictionary = space.intersect_ray(q)
		if res.is_empty():
			return {}
		if res["collider"] == collider:
			return res
		var rid: RID = res["rid"]
		exclude.append(rid)
	return {}


func _make_damage(hit: BallisticHit, collider: Object) -> DamageInfo:
	var info: DamageInfo = DamageInfo.new()
	info.type = DamageInfo.Type.BALLISTIC
	info.penetration = hit.energy_in
	info.amount = hit.weapon.damage_for(hit.deposited())
	info.impulse = hit.weapon.bullet_mass_g * 0.001 * (hit.speed_in - hit.speed_out) * hit.weapon.impulse_scale
	var node: Node = collider as Node
	if node and node.has_meta(&"zone"):
		var zone: StringName = node.get_meta(&"zone")
		info.zone = zone
	info.point = hit.point
	info.normal = hit.normal
	info.source = hit.shooter
	if hit.prior_penetrations > 0:
		info.flags |= DamageInfo.Flags.PENETRATED
	if hit.result == BallisticHit.Result.PENETRATED:
		info.flags |= DamageInfo.Flags.PASS_THROUGH
	if info.zone == &"head" or info.zone == &"neck":
		info.flags |= DamageInfo.Flags.HEADSHOT | DamageInfo.Flags.HEAVY
	return info


func _push(collider: Object, hit: BallisticHit, mass_kg: float) -> void:
	var body: RigidBody3D = collider as RigidBody3D
	if body == null:
		return
	var lost: Vector3 = hit.direction * hit.speed_in - hit.direction * hit.speed_out
	if hit.result == BallisticHit.Result.RICOCHET:
		lost = hit.direction * hit.speed_in * 0.6
	var impulse: Vector3 = (lost * mass_kg * hit.weapon.impulse_scale).limit_length(body.mass * MAX_PROP_DV)
	body.apply_impulse(impulse, hit.point - body.global_position)


## Random direction within a cone of `cone_deg` (full width) around `dir`.
func _scatter(dir: Vector3, cone_deg: float) -> Vector3:
	return random_in_cone(dir, cone_deg, _rng)


static func random_in_cone(dir: Vector3, cone_deg: float, rng: RandomNumberGenerator) -> Vector3:
	if cone_deg <= 0.0:
		return dir
	var half: float = deg_to_rad(cone_deg) * 0.5
	# Uniform over the cone's cap (not clumped in the middle like a gaussian).
	var cos_t: float = lerpf(1.0, cos(half), rng.randf())
	var sin_t: float = sqrt(1.0 - cos_t * cos_t)
	var phi: float = rng.randf() * TAU
	var up: Vector3 = Vector3.UP if absf(dir.y) < 0.99 else Vector3.RIGHT
	var right: Vector3 = dir.cross(up).normalized()
	var up2: Vector3 = right.cross(dir).normalized()
	return (dir * cos_t + right * sin_t * cos(phi) + up2 * sin_t * sin(phi)).normalized()


func _rebuild_lines() -> void:
	_mesh.clear_surfaces()
	var verts: PackedVector3Array = PackedVector3Array()
	var colors: PackedColorArray = PackedColorArray()
	for p: Projectile in _paths:
		for i: int in range(1, p.path.size()):
			var a: Vector3 = p.path[i - 1]
			var b: Vector3 = p.path[i]
			if a.is_equal_approx(b):
				continue
			# Yellow at full speed, turning red as the round loses energy.
			var t: float = clampf(p.path_speed[i - 1] / p.muzzle_speed, 0.0, 1.0)
			var c: Color = Color(1.0, 0.15 + 0.8 * t * t, 0.1, 1.0)
			verts.append(a)
			verts.append(b)
			colors.append(c)
			colors.append(c)
	if verts.is_empty():
		return
	_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	for i: int in verts.size():
		_mesh.surface_set_color(colors[i])
		_mesh.surface_add_vertex(verts[i])
	_mesh.surface_end()
