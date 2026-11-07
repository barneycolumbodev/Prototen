class_name GaussGore
extends Node3D
## The GX-4 arm cannon's wounds (owner, 2026-11-07: "a very special gore
## effect where it almost blows a spiral through them... a horrific
## electronic weapon"). Owned by Gore (Gore.special_hit), pooled and capped.
##
## - Corkscrew: the slug drags a twisting wake through the body. Blood
##   droplets and a red mist leave along a double helix that starts at the
##   entry wound, runs through the exit and a metre and a half beyond,
##   spinning outward (CPUParticles3D with directed emission points, so it
##   holds up in slow motion).
## - Electrocution: the coil discharge rides the slug. Blue arcs crawl
##   between the body's joints for a second and a half, sparks spit from the
##   wounds, smoke curls off them, and the corpse spasms (small impulses to
##   random ragdoll bones).
## Gore off: only the sparks and arcs (no blood).

const MAX_CORKSCREWS: int = 2
const MAX_SHOCKS: int = 3
const SHOCK_TIME: float = 1.5
const ARC_REFRESH: float = 0.045
const ARCS: int = 3
const ARC_SEGMENTS: int = 7
const ARC_WIDTH: float = 0.012
const ZONES: Array[StringName] = [&"head", &"neck", &"chest", &"stomach", &"pelvis", &"l_upper_arm", &"r_upper_arm",
		&"l_forearm", &"r_forearm", &"l_hand", &"r_hand", &"l_thigh", &"r_thigh", &"l_shin", &"r_shin"]
const SPASM_ZONES: Array[StringName] = [&"chest", &"head", &"l_forearm", &"r_forearm", &"l_shin", &"r_shin", &"pelvis"]

var blood: Array[CPUParticles3D] = []
var mists: Array[CPUParticles3D] = []
var _next: int = 0
var _shocks: Array[Shock] = []
var _shock_next: int = 0
var _arc_mat: StandardMaterial3D
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
## For tests and the overlay.
var corkscrews_fired: int = 0


class Shock:
	extends RefCounted
	var body: EnemyBody
	var left: float = 0.0
	var refresh: float = 0.0
	var spasm: float = 0.0
	var mesh: ImmediateMesh
	var node: MeshInstance3D


func _ready() -> void:
	_rng.randomize()
	_arc_mat = StandardMaterial3D.new()
	_arc_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_arc_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_arc_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_arc_mat.no_depth_test = false
	_arc_mat.vertex_color_use_as_albedo = true
	_arc_mat.albedo_color = Color(1, 1, 1)
	for i: int in MAX_SHOCKS:
		var s: Shock = Shock.new()
		s.mesh = ImmediateMesh.new()
		s.node = MeshInstance3D.new()
		s.node.mesh = s.mesh
		s.node.material_override = _arc_mat
		s.node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		s.node.top_level = true
		s.node.extra_cull_margin = 4.0
		add_child(s.node)
		_shocks.append(s)


## A GX-4 slug went through a body part of `body`.
func hit(hit: BallisticHit, body: EnemyBody) -> void:
	var entry: Vector3 = hit.point
	var dir: Vector3 = hit.direction.normalized()
	var exit: Vector3 = hit.exit_point if hit.result == BallisticHit.Result.PENETRATED else entry + dir * 0.3
	if Gore.is_on():
		corkscrew(entry, exit, dir)
	Fx._emit(&"sparks", entry, -dir, Color(0.6, 0.8, 1.0, 1.0), 14, 1.4)
	Fx._emit(&"sparks", exit, dir, Color(0.75, 0.9, 1.0, 1.0), 18, 2.0)
	Fx._emit(&"smoke", exit, Vector3.UP, Color(0.45, 0.45, 0.5, 0.18), 2, 0.4)
	if Gore.is_maximum() and hit.result == BallisticHit.Result.PENETRATED:
		Gore.burst_chunks(exit, dir, 3, 6.0)
	if body:
		electrocute(body)
	Sfx.play_at(&"gx4_zap", exit, -2.0, 0.1)


## Blood and mist leaving along a double helix from `entry` through `exit`.
func corkscrew(entry: Vector3, exit: Vector3, dir: Vector3) -> void:
	if blood.is_empty():
		_build_emitters()
	corkscrews_fired += 1
	var e: CPUParticles3D = blood[_next]
	var m: CPUParticles3D = mists[_next]
	_next = (_next + 1) % blood.size()
	var through: float = maxf(entry.distance_to(exit), 0.15)
	var length: float = through + 1.5
	var up: Vector3 = Vector3.UP if absf(dir.y) < 0.95 else Vector3.RIGHT
	var basis: Basis = Basis.looking_at(-dir, up)  # local +Z = along the shot
	var phase: float = _rng.randf() * TAU
	var pts: PackedVector3Array = PackedVector3Array()
	var nrm: PackedVector3Array = PackedVector3Array()
	var turns_per_m: float = 2.2
	var count: int = 26
	for strand: int in 2:
		for i: int in count:
			var z: float = length * float(i) / (count - 1)
			var a: float = phase + strand * PI + z * turns_per_m * TAU
			var radial: Vector3 = Vector3(cos(a), sin(a), 0.0)
			var tangent: Vector3 = Vector3(-sin(a), cos(a), 0.0)
			var r: float = lerpf(0.025, 0.16, clampf(z / length, 0.0, 1.0))
			pts.append(radial * r + Vector3(0, 0, z))
			# Spin round the axis, outward, and on along the shot (slower further out).
			nrm.append((tangent * 1.0 + radial * 0.45 + Vector3(0, 0, lerpf(1.1, 0.4, z / length))).normalized())
	for p: CPUParticles3D in [e, m]:
		p.global_transform = Transform3D(basis, entry)
		p.emission_points = pts
		p.emission_normals = nrm
	e.amount = pts.size()
	e.restart()
	m.amount = clampi(pts.size() / 3, 8, 18)
	m.restart()
	Gore.splat(exit + dir * 0.05, -dir, 0.1)


## Arcs crawl over `body` for SHOCK_TIME and the corpse jerks.
func electrocute(body: EnemyBody) -> void:
	for s: Shock in _shocks:
		if s.body == body and s.left > 0.0:
			s.left = SHOCK_TIME
			return
	var sh: Shock = _shocks[_shock_next]
	_shock_next = (_shock_next + 1) % _shocks.size()
	sh.body = body
	sh.left = SHOCK_TIME
	sh.refresh = 0.0
	sh.spasm = 0.05
	sh.node.visible = true


func live_shocks() -> int:
	var n: int = 0
	for s: Shock in _shocks:
		if s.left > 0.0:
			n += 1
	return n


func _process(delta: float) -> void:
	for s: Shock in _shocks:
		if s.left <= 0.0:
			continue
		s.left -= delta
		if s.left <= 0.0 or not is_instance_valid(s.body):
			s.left = 0.0
			s.mesh.clear_surfaces()
			s.node.visible = false
			s.body = null
			continue
		s.refresh -= delta
		if s.refresh <= 0.0:
			s.refresh = ARC_REFRESH
			_draw_arcs(s)
		s.spasm -= delta
		if s.spasm <= 0.0:
			s.spasm = _rng.randf_range(0.07, 0.16)
			_spasm(s)


func _zone_pos(body: EnemyBody, zone: StringName) -> Vector3:
	if body.hitboxes.has(zone):
		return body.hitboxes[zone].global_position
	return body.global_position + Vector3.UP


func _draw_arcs(s: Shock) -> void:
	var cam: Camera3D = get_viewport().get_camera_3d()
	var eye: Vector3 = cam.global_position if cam else Vector3.ZERO
	var k: float = clampf(s.left / SHOCK_TIME, 0.0, 1.0)
	s.mesh.clear_surfaces()
	s.mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var n_arcs: int = maxi(1, roundi(ARCS * (0.4 + 0.6 * k)))
	for a: int in n_arcs:
		var z0: StringName = ZONES[_rng.randi() % ZONES.size()]
		var z1: StringName = ZONES[_rng.randi() % ZONES.size()]
		var p0: Vector3 = _zone_pos(s.body, z0)
		var p1: Vector3 = _zone_pos(s.body, z1)
		if p0.distance_to(p1) < 0.12:
			p1 = p0 + Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(-0.1, 0.4), _rng.randf_range(-0.3, 0.3))
		var prev: Vector3 = p0
		var col: Color = Color(0.55, 0.78, 1.0) * (0.8 + 1.4 * k)
		for i: int in range(1, ARC_SEGMENTS + 1):
			var t: float = float(i) / ARC_SEGMENTS
			var p: Vector3 = p0.lerp(p1, t)
			if i < ARC_SEGMENTS:
				p += Vector3(_rng.randf_range(-1, 1), _rng.randf_range(-1, 1), _rng.randf_range(-1, 1)) * 0.05
			_ribbon(s.mesh, prev, p, eye, ARC_WIDTH * (0.6 + 0.8 * k), col)
			prev = p
	s.mesh.surface_end()


func _ribbon(m: ImmediateMesh, a: Vector3, b: Vector3, eye: Vector3, w: float, col: Color) -> void:
	var d: Vector3 = b - a
	var side: Vector3 = d.cross(eye - a)
	if side.length() < 0.00001:
		return
	side = side.normalized() * w * 0.5
	m.surface_set_color(col)
	m.surface_add_vertex(a - side)
	m.surface_add_vertex(a + side)
	m.surface_add_vertex(b + side)
	m.surface_add_vertex(a - side)
	m.surface_add_vertex(b + side)
	m.surface_add_vertex(b - side)


func _spasm(s: Shock) -> void:
	if not s.body.ragdolling:
		return
	var zone: StringName = SPASM_ZONES[_rng.randi() % SPASM_ZONES.size()]
	var k: float = clampf(s.left / SHOCK_TIME, 0.0, 1.0)
	var imp: Vector3 = Vector3(_rng.randf_range(-1, 1), _rng.randf_range(0.2, 1.0), _rng.randf_range(-1, 1)) * (2.5 + 5.0 * k)
	s.body.push_bone(zone, imp, _zone_pos(s.body, zone))
	if _rng.randf() < 0.35:
		Fx._emit(&"sparks", _zone_pos(s.body, zone), Vector3.UP, Color(0.6, 0.8, 1.0, 1.0), 6, 0.8)


func _build_emitters() -> void:
	var drop: StandardMaterial3D = Gore._drop_mat
	var mist: StandardMaterial3D = Gore._mist_mat
	var fade: Gradient = Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 1))
	fade.set_color(1, Color(1, 1, 1, 0))
	var grow: Curve = Curve.new()
	grow.add_point(Vector2(0, 0.4))
	grow.add_point(Vector2(1, 1.0))
	for i: int in MAX_CORKSCREWS:
		var e: CPUParticles3D = _emitter(drop)
		e.color = Gore.BLOOD_COLOR
		e.color_ramp = fade
		e.lifetime = 0.85
		e.initial_velocity_min = 3.5
		e.initial_velocity_max = 7.5
		e.scale_amount_min = 0.018
		e.scale_amount_max = 0.05
		e.gravity = Vector3(0, -9.8, 0)
		e.damping_min = 1.0
		e.damping_max = 2.5
		blood.append(e)
		var m: CPUParticles3D = _emitter(mist)
		m.color = Color(0.42, 0.03, 0.03, 0.5)
		m.color_ramp = fade
		m.scale_amount_curve = grow
		m.lifetime = 1.1
		m.initial_velocity_min = 0.6
		m.initial_velocity_max = 1.6
		m.scale_amount_min = 0.12
		m.scale_amount_max = 0.3
		m.gravity = Vector3(0, -0.5, 0)
		m.damping_min = 2.0
		m.damping_max = 3.5
		mists.append(m)


func _emitter(mat: Material) -> CPUParticles3D:
	var e: CPUParticles3D = CPUParticles3D.new()
	e.emitting = false
	e.one_shot = true
	e.explosiveness = 1.0
	e.local_coords = false
	e.emission_shape = CPUParticles3D.EMISSION_SHAPE_DIRECTED_POINTS
	e.spread = 4.0
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2.ONE
	e.mesh = q
	e.material_override = mat
	add_child(e)
	return e
