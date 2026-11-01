extends Node3D
## Shot and impact effects (docs/design.md §5.3), all pooled and capped
## (CLAUDE.md §8). Autoloaded as Fx. Listens to EventBus.ballistic_hit.
##
## - Muzzle flash: tiny for the suppressed pistol, plus a puff from the can
##   and one shared muzzle light (≤ 4 dynamic lights in the scene).
## - Shell casings: simple ballistic sim with bounces against the world.
## - Bullet holes: on static geometry they live in one MultiMesh (one draw
##   call for all of them); on anything that moves (targets marked with
##   metadata `dynamic_holes`, rigid bodies) they are quads parented to the
##   hit node so they ride along. Entry and exit holes. Both work in both
##   renderers (Decal nodes don't in Compatibility).
## - Impact particles by surface: dust, chalk, sparks, splinters, blood, glass.
## - Debris chunks: small rigid bodies for destruction, capped.

const MAX_HOLES: int = 24
const MAX_STATIC_HOLES: int = 128
const MAX_SHELLS: int = 24
const MAX_EMITTERS: int = 12
const MAX_DEBRIS: int = 28
const DEBRIS_LIFETIME: float = 5.0
const SHELL_LIFETIME: float = 6.0
const SHELL_RESTITUTION: float = 0.35

## Effects on/off per kind (tests turn them off to stay deterministic).
var enabled: bool = true

var _holes: Array[MeshInstance3D] = []
var _hole_next: int = 0
var _hole_mesh: QuadMesh
var _hole_tex: ImageTexture
var _hole_mats: Dictionary[Color, StandardMaterial3D] = {}
var _static_mm: MultiMesh
var _static_pos: PackedVector3Array = PackedVector3Array()
var _static_next: int = 0

var _emitters: Array[CPUParticles3D] = []
var _emit_next: int = 0
var _particle_mats: Dictionary[StringName, StandardMaterial3D] = {}

var _flash: MeshInstance3D
var _flash_time: float = 0.0
var _light: OmniLight3D
var _light_time: float = 0.0
var _light_energy: float = 0.0

var _shells: Array[Shell] = []
var _shell_next: int = 0

var _debris: Array[RigidBody3D] = []
var _debris_age: Dictionary[RigidBody3D, float] = {}
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _fade: Gradient
var _grow: Curve


class Shell:
	extends RefCounted
	var node: MeshInstance3D
	var velocity: Vector3
	var spin: Vector3
	var age: float = 999.0
	var bounces: int = 0
	var resting: bool = true


func _ready() -> void:
	_rng.randomize()
	_fade = Gradient.new()
	_fade.set_color(0, Color(1, 1, 1, 1))
	_fade.set_color(1, Color(1, 1, 1, 0))
	_grow = _grow_curve()
	_build_holes()
	_build_flash()
	_build_shells()
	for i: int in MAX_EMITTERS:
		var e: CPUParticles3D = CPUParticles3D.new()
		e.emitting = false
		e.one_shot = true
		e.explosiveness = 0.95
		e.local_coords = false
		var q: QuadMesh = QuadMesh.new()
		q.size = Vector2.ONE
		e.mesh = q
		add_child(e)
		_emitters.append(e)
	EventBus.ballistic_hit.connect(_on_hit)


# ------------------------------------------------------------------ muzzle

func muzzle_flash(muzzle: Transform3D, data: WeaponData) -> void:
	if not enabled:
		return
	_flash.global_transform = muzzle
	_flash.scale = Vector3.ONE * data.flash_scale * _rng.randf_range(0.8, 1.2)
	_flash.rotate_object_local(Vector3.RIGHT, _rng.randf() * TAU)
	_flash.visible = data.flash_scale > 0.0
	_flash_time = 0.035
	if data.flash_light_energy > 0.0:
		_light.global_position = muzzle.origin + muzzle.basis.x * 0.05
		_light_energy = data.flash_light_energy
		_light.light_energy = _light_energy
		_light.visible = true
		_light_time = 0.06
	# Suppressor puff.
	_emit(&"smoke", muzzle.origin, muzzle.basis.x, Color(0.75, 0.75, 0.75, 0.35), 4, 0.6)


# ------------------------------------------------------------------ shells

func eject_shell(at: Vector3, velocity: Vector3, gun_basis: Basis) -> void:
	if not enabled:
		return
	var s: Shell = _shells[_shell_next]
	_shell_next = (_shell_next + 1) % _shells.size()
	s.node.global_transform = Transform3D(gun_basis * Basis(Vector3.FORWARD, PI * 0.5), at)
	s.velocity = velocity + Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(-0.2, 0.4), _rng.randf_range(-0.3, 0.3))
	s.spin = Vector3(_rng.randf_range(-30, 30), _rng.randf_range(-10, 10), _rng.randf_range(15, 40))
	s.age = 0.0
	s.bounces = 0
	s.resting = false
	s.node.visible = true


func live_shells() -> int:
	var n: int = 0
	for s: Shell in _shells:
		if s.node.visible:
			n += 1
	return n


func _physics_process(delta: float) -> void:
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var g: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
	for s: Shell in _shells:
		if not s.node.visible:
			continue
		s.age += delta
		if s.age > SHELL_LIFETIME:
			s.node.visible = false
			continue
		if s.resting:
			continue
		s.velocity.y -= g * delta
		var from: Vector3 = s.node.global_position
		var to: Vector3 = from + s.velocity * delta
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
		var res: Dictionary = space.intersect_ray(q)
		if res.is_empty():
			s.node.global_position = to
			s.node.rotate_object_local(Vector3.RIGHT, s.spin.x * delta)
			s.node.rotate_object_local(Vector3.UP, s.spin.y * delta)
			s.node.rotate_object_local(Vector3.FORWARD, s.spin.z * delta)
			continue
		var n: Vector3 = res["normal"]
		var p: Vector3 = res["position"]
		var vn: Vector3 = n * s.velocity.dot(n)
		var vt: Vector3 = s.velocity - vn
		s.velocity = vt * 0.6 - vn * SHELL_RESTITUTION
		s.spin *= 0.5
		s.node.global_position = p + n * 0.004
		if s.bounces < 3 and s.velocity.length() > 0.3:
			Sfx.play_at(&"shell", p, -10.0 - s.bounces * 6.0)
		s.bounces += 1
		if s.velocity.length() < 0.35 or s.bounces > 6:
			s.resting = true
			# Lie on its side, rotated randomly about the surface normal.
			var axis: Vector3 = n.cross(Vector3.FORWARD if absf(n.z) < 0.9 else Vector3.RIGHT).normalized()
			axis = axis.rotated(n, _rng.randf() * TAU)
			s.node.global_basis = Basis(n.cross(axis), axis, n).orthonormalized() * Basis(Vector3.RIGHT, PI * 0.5)
	_age_debris(delta)


func _process(delta: float) -> void:
	if _flash_time > 0.0:
		_flash_time -= delta
		if _flash_time <= 0.0:
			_flash.visible = false
	if _light_time > 0.0:
		_light_time -= delta
		_light.light_energy = _light_energy * clampf(_light_time / 0.06, 0.0, 1.0)
		if _light_time <= 0.0:
			_light.visible = false


# ------------------------------------------------------------------ impacts

func _on_hit(hit: BallisticHit) -> void:
	if not enabled:
		return
	var s: SurfaceMaterial = hit.surface
	var target: Node3D = hit.collider as Node3D
	var reflect: Vector3 = hit.direction.bounce(hit.normal).normalized()
	match hit.result:
		BallisticHit.Result.RICOCHET:
			_emit(&"sparks", hit.point, reflect, Color(1.0, 0.8, 0.45), 10, 1.0)
			bullet_hole(target, hit.point, hit.normal, s, 0.7)
		_:
			bullet_hole(target, hit.point, hit.normal, s, 1.0)
			var spray: Vector3 = (hit.normal * 0.7 + reflect * 0.3).normalized()
			_emit(s.particle_kind, hit.point, spray, s.particle_color, s.particle_count, 1.0)
			if s.particle_kind == &"dust" or s.particle_kind == &"chalk":
				_emit(&"sparks" if s.id == &"concrete" else &"chalk", hit.point, spray, s.particle_color.lightened(0.3), 3, 0.6)
	if hit.result == BallisticHit.Result.PENETRATED:
		bullet_hole(target, hit.exit_point, hit.exit_normal, s, 1.6)
		# Exit spall flies along the round's path.
		_emit(s.particle_kind, hit.exit_point, hit.direction, s.particle_color, s.particle_count + 4, 1.3)


## Puts a bullet hole on `target` at `point`.
func bullet_hole(target: Node3D, point: Vector3, normal: Vector3, s: SurfaceMaterial, size_scale: float) -> void:
	if not enabled or target == null or not target.is_inside_tree():
		return
	var up: Vector3 = Vector3.UP if absf(normal.y) < 0.95 else Vector3.RIGHT
	var x: Vector3 = up.cross(normal).normalized().rotated(normal, _rng.randf() * TAU)
	var y: Vector3 = normal.cross(x)
	var r: float = s.decal_radius * size_scale * _rng.randf_range(0.85, 1.2) * 2.0
	var xform: Transform3D = Transform3D(Basis(x * r, y * r, normal), point + normal * 0.0015)
	if not _is_dynamic(target):
		var i: int = _static_next
		_static_next = (_static_next + 1) % MAX_STATIC_HOLES
		_static_mm.set_instance_transform(i, xform)
		_static_mm.set_instance_color(i, s.decal_color)
		_static_pos[i] = point
		return
	var q: MeshInstance3D = _holes[_hole_next]
	if not is_instance_valid(q):
		q = _new_hole()
		_holes[_hole_next] = q
	_hole_next = (_hole_next + 1) % MAX_HOLES
	if q.get_parent() != target:
		if q.get_parent():
			q.get_parent().remove_child(q)
		target.add_child(q)
	q.material_override = _hole_material(s.decal_color)
	q.global_transform = xform
	q.visible = true


## Removes static holes within `radius` of `center` (a wall cell broke away).
func clear_holes_near(center: Vector3, radius: float) -> void:
	for i: int in MAX_STATIC_HOLES:
		if _static_pos[i].distance_squared_to(center) < radius * radius:
			_static_mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO))
			_static_pos[i] = Vector3(0, -1000, 0)


func hole_count() -> int:
	var n: int = 0
	for q: MeshInstance3D in _holes:
		if is_instance_valid(q) and q.visible and q.is_inside_tree() and q.get_parent() != self:
			n += 1
	for p: Vector3 in _static_pos:
		if p.y > -999.0:
			n += 1
	return n


static func _is_dynamic(node: Node) -> bool:
	var n: Node = node
	for i: int in 4:
		if n == null:
			return false
		if n is RigidBody3D or n.has_meta(&"dynamic_holes"):
			return true
		n = n.get_parent()
	return false


# ------------------------------------------------------------------ debris

## Throws `count` small chunks (destruction). Oldest chunks are recycled.
func debris(at: Vector3, push: Vector3, color: Color, size: float, count: int, spread: float = 1.0, surface: StringName = &"concrete") -> void:
	if not enabled:
		return
	for i: int in count:
		var body: RigidBody3D
		if _debris.size() < MAX_DEBRIS:
			body = _new_debris()
		else:
			body = _debris.pop_front()
			if not is_instance_valid(body):
				body = _new_debris()
		_debris.append(body)
		var mesh: MeshInstance3D = body.get_child(0) as MeshInstance3D
		var shape: CollisionShape3D = body.get_child(1) as CollisionShape3D
		var dims: Vector3 = Vector3(_rng.randf_range(0.5, 1.0), _rng.randf_range(0.3, 0.8), _rng.randf_range(0.5, 1.2)) * size
		(mesh.mesh as BoxMesh).size = dims
		(shape.shape as BoxShape3D).size = dims
		var mat: StandardMaterial3D = mesh.material_override as StandardMaterial3D
		mat.albedo_color = color.darkened(_rng.randf_range(0.0, 0.25))
		body.global_position = at + Vector3(_rng.randf_range(-1, 1), _rng.randf_range(-1, 1), _rng.randf_range(-1, 1)) * size * spread
		body.rotation = Vector3(_rng.randf() * TAU, _rng.randf() * TAU, _rng.randf() * TAU)
		body.mass = maxf(0.02, dims.x * dims.y * dims.z * 600.0)
		body.linear_velocity = push + Vector3(_rng.randf_range(-1, 1), _rng.randf_range(0, 1.5), _rng.randf_range(-1, 1)) * push.length() * 0.35 * spread
		body.angular_velocity = Vector3(_rng.randf_range(-12, 12), _rng.randf_range(-12, 12), _rng.randf_range(-12, 12))
		body.freeze = false
		body.sleeping = false
		body.visible = true
		body.process_mode = Node.PROCESS_MODE_INHERIT
		body.set_meta(&"surface", surface)
		_debris_age[body] = 0.0


func debris_count() -> int:
	var n: int = 0
	for b: RigidBody3D in _debris:
		if is_instance_valid(b) and b.visible:
			n += 1
	return n


func _age_debris(delta: float) -> void:
	for b: RigidBody3D in _debris:
		if not b.visible:
			continue
		var age: float = _debris_age.get(b, 0.0) + delta
		_debris_age[b] = age
		if age > DEBRIS_LIFETIME:
			b.visible = false
			b.freeze = true
			b.global_position = Vector3(0, -500, 0)


# ------------------------------------------------------------------ builders

func _emit(kind: StringName, at: Vector3, dir: Vector3, color: Color, count: int, strength: float) -> void:
	var e: CPUParticles3D = _emitters[_emit_next]
	_emit_next = (_emit_next + 1) % _emitters.size()
	e.global_position = at
	e.amount = clampi(count, 1, 40)
	e.direction = Vector3(0, 0, 1)
	e.global_basis = _basis_facing(dir)
	e.color = color
	e.color_ramp = _fade
	e.material_override = _particle_material(kind)
	e.gravity = Vector3(0, -9.8, 0)
	e.damping_min = 0.0
	e.damping_max = 0.0
	e.scale_amount_curve = null
	match kind:
		&"sparks":
			e.lifetime = 0.35
			e.spread = 55.0
			e.initial_velocity_min = 3.0 * strength
			e.initial_velocity_max = 9.0 * strength
			e.scale_amount_min = 0.006
			e.scale_amount_max = 0.014
		&"splinters":
			e.lifetime = 0.9
			e.spread = 40.0
			e.initial_velocity_min = 1.5 * strength
			e.initial_velocity_max = 5.0 * strength
			e.scale_amount_min = 0.008
			e.scale_amount_max = 0.022
		&"blood":
			e.lifetime = 0.6
			e.spread = 30.0
			e.initial_velocity_min = 1.0 * strength
			e.initial_velocity_max = 4.5 * strength
			e.scale_amount_min = 0.012
			e.scale_amount_max = 0.05
			e.gravity = Vector3(0, -7.0, 0)
		&"glass":
			e.lifetime = 0.7
			e.spread = 60.0
			e.initial_velocity_min = 2.0 * strength
			e.initial_velocity_max = 6.0 * strength
			e.scale_amount_min = 0.006
			e.scale_amount_max = 0.02
		&"smoke":
			e.lifetime = 0.7
			e.spread = 15.0
			e.initial_velocity_min = 0.3
			e.initial_velocity_max = 0.9
			e.scale_amount_min = 0.02
			e.scale_amount_max = 0.05
			e.gravity = Vector3(0, 0.3, 0)
			e.damping_min = 1.5
			e.damping_max = 2.5
			e.scale_amount_curve = _grow
		_:  # dust, chalk
			e.lifetime = 1.1 if kind == &"chalk" else 0.9
			e.spread = 35.0
			e.initial_velocity_min = 1.0 * strength
			e.initial_velocity_max = 4.0 * strength
			e.scale_amount_min = 0.025
			e.scale_amount_max = 0.07 if kind == &"chalk" else 0.055
			e.gravity = Vector3(0, -1.5, 0)
			e.damping_min = 2.0
			e.damping_max = 4.0
			e.scale_amount_curve = _grow
	e.restart()


func _grow_curve() -> Curve:
	var c: Curve = Curve.new()
	c.add_point(Vector2(0, 0.4))
	c.add_point(Vector2(1, 1.6))
	c.max_value = 2.0
	return c


static func _basis_facing(dir: Vector3) -> Basis:
	var z: Vector3 = dir.normalized()
	var up: Vector3 = Vector3.UP if absf(z.y) < 0.95 else Vector3.RIGHT
	var x: Vector3 = up.cross(z).normalized()
	return Basis(x, z.cross(x), z)


func _particle_material(kind: StringName) -> StandardMaterial3D:
	if _particle_mats.has(kind):
		return _particle_mats[kind]
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = _soft_dot()
	if kind == &"sparks":
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.albedo_color = Color(2.5, 2.0, 1.4)
	_particle_mats[kind] = m
	return m


func _build_holes() -> void:
	_hole_tex = ImageTexture.create_from_image(_hole_image(64))
	_hole_mesh = QuadMesh.new()
	_hole_mesh.size = Vector2.ONE
	for i: int in MAX_HOLES:
		_holes.append(_new_hole())
	_static_mm = MultiMesh.new()
	_static_mm.transform_format = MultiMesh.TRANSFORM_3D
	_static_mm.use_colors = true
	_static_mm.mesh = _hole_mesh
	_static_mm.instance_count = MAX_STATIC_HOLES
	_static_pos.resize(MAX_STATIC_HOLES)
	for i: int in MAX_STATIC_HOLES:
		_static_mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ZERO), Vector3.ZERO))
		_static_pos[i] = Vector3(0, -1000, 0)
	var mmi: MultiMeshInstance3D = MultiMeshInstance3D.new()
	mmi.multimesh = _static_mm
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.top_level = true
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.albedo_texture = _hole_tex
	m.vertex_color_use_as_albedo = true
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.4
	m.roughness = 1.0
	mmi.material_override = m
	add_child(mmi)


func _new_hole() -> MeshInstance3D:
	var q: MeshInstance3D = MeshInstance3D.new()
	q.mesh = _hole_mesh
	q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	q.visible = false
	add_child(q)
	return q


func _hole_material(color: Color) -> StandardMaterial3D:
	if _hole_mats.has(color):
		return _hole_mats[color]
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.albedo_texture = _hole_tex
	m.albedo_color = color
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.4
	m.roughness = 1.0
	m.cull_mode = BaseMaterial3D.CULL_BACK
	_hole_mats[color] = m
	return m


## Bullet hole: black core, darker scorched ring, a few radial cracks.
static func _hole_image(size: int) -> Image:
	var img: Image = Image.create_empty(size, size, false, Image.FORMAT_RGBA8)
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 57
	var cracks: PackedFloat32Array = PackedFloat32Array()
	for i: int in 7:
		cracks.append(rng.randf() * TAU)
	var c: float = (size - 1) * 0.5
	for y: int in size:
		for x: int in size:
			var dx: float = (x - c) / c
			var dy: float = (y - c) / c
			var r: float = sqrt(dx * dx + dy * dy)
			var ang: float = atan2(dy, dx)
			var crack: float = 0.0
			for a: float in cracks:
				var d: float = absf(angle_difference(ang, a))
				crack = maxf(crack, (1.0 - smoothstep(0.0, 0.07, d)) * (1.0 - smoothstep(0.3, 0.95, r)))
			var core: float = 1.0 - smoothstep(0.18, 0.26, r)
			var ring: float = (1.0 - smoothstep(0.26, 0.6, r)) * 0.8
			var alpha: float = clampf(maxf(maxf(core, ring), crack * 0.9), 0.0, 1.0)
			var shade: float = lerpf(1.0, 0.15, core)  # tinted by the surface colour; core near black
			img.set_pixel(x, y, Color(shade, shade, shade, alpha))
	return img


static func _soft_dot() -> ImageTexture:
	var size: int = 32
	var img: Image = Image.create_empty(size, size, false, Image.FORMAT_RGBA8)
	var c: float = (size - 1) * 0.5
	for y: int in size:
		for x: int in size:
			var r: float = Vector2(x - c, y - c).length() / c
			img.set_pixel(x, y, Color(1, 1, 1, clampf(1.0 - r, 0.0, 1.0) ** 1.5))
	return ImageTexture.create_from_image(img)


func _build_flash() -> void:
	var img: Image = Image.create_empty(64, 64, false, Image.FORMAT_RGBA8)
	for y: int in 64:
		for x: int in 64:
			var p: Vector2 = Vector2(x - 31.5, y - 31.5) / 31.5
			var r: float = p.length()
			var star: float = absf(cos(atan2(p.y, p.x) * 3.0)) * 0.6 + 0.4
			var a: float = clampf((1.0 - r / star), 0.0, 1.0) ** 2.0
			img.set_pixel(x, y, Color(1.0, 0.85, 0.55, a))
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = ImageTexture.create_from_image(img)
	m.albedo_color = Color(2.0, 1.6, 1.1)
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.no_depth_test = true
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2(0.09, 0.09)
	_flash = MeshInstance3D.new()
	_flash.mesh = q
	_flash.material_override = m
	_flash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_flash.visible = false
	add_child(_flash)
	_light = OmniLight3D.new()
	_light.light_color = Color(1.0, 0.78, 0.5)
	_light.omni_range = 4.0
	_light.shadow_enabled = false
	_light.visible = false
	add_child(_light)


func _build_shells() -> void:
	var mesh: CylinderMesh = CylinderMesh.new()
	mesh.top_radius = 0.0032  # 5.7×28: 7.9 mm rim, 6.4 mm shoulder-ish body, 28.8 mm long
	mesh.bottom_radius = 0.0039
	mesh.height = 0.0288
	mesh.radial_segments = 8
	mesh.rings = 1
	var brass: StandardMaterial3D = StandardMaterial3D.new()
	brass.albedo_color = Color(0.85, 0.66, 0.33)
	brass.metallic = 1.0
	brass.roughness = 0.32
	for i: int in MAX_SHELLS:
		var s: Shell = Shell.new()
		s.node = MeshInstance3D.new()
		s.node.mesh = mesh
		s.node.material_override = brass
		s.node.visible = false
		s.node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(s.node)
		_shells.append(s)


func _new_debris() -> RigidBody3D:
	var body: RigidBody3D = RigidBody3D.new()
	body.collision_layer = Ballistics.LAYER_DEBRIS
	body.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	body.continuous_cd = false
	body.can_sleep = true
	var mesh: MeshInstance3D = MeshInstance3D.new()
	mesh.mesh = BoxMesh.new()
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.roughness = 0.9
	mesh.material_override = mat
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(mesh)
	var shape: CollisionShape3D = CollisionShape3D.new()
	shape.shape = BoxShape3D.new()
	body.add_child(shape)
	body.set_meta(&"surface", &"concrete")
	add_child(body)
	return body
