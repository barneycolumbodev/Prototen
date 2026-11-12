class_name GaussGore
extends Node3D
## The GX-4 arm cannon's wounds (owner, 2026-11-07: "a very special gore
## effect where it almost blows a spiral through them... a horrific
## electronic weapon"). Owned by Gore (Gore.special_hit), pooled and capped.
##
## - Corkscrew: the slug drags a twisting wake through the body. Blood
##   drops and a fine spray leave along a double helix that starts at the
##   entry wound, runs through the exit and a metre and a half beyond,
##   spinning outward (Gore.drops: each one flies, falls and stains, and
##   they run on game time, so they hold up in slow motion).
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


## Blood leaving along a double helix from `entry` through `exit`: drops
## launched from points on the helix, spinning round the slug's axis,
## outward and on along the shot (Gore.drops, so they fall, land and stain
## like any other blood), with a finer spray between them.
func corkscrew(entry: Vector3, exit: Vector3, dir: Vector3) -> void:
	corkscrews_fired += 1
	var through: float = maxf(entry.distance_to(exit), 0.15)
	var length: float = through + 1.5
	var up: Vector3 = Vector3.UP if absf(dir.y) < 0.95 else Vector3.RIGHT
	var basis: Basis = Basis.looking_at(-dir, up)  # local +Z = along the shot
	var phase: float = _rng.randf() * TAU
	var turns_per_m: float = 2.2
	var count: int = roundi(26.0 * clampf(Gore.config.blood_amount, 0.3, 1.5))
	var floor_y: float = Gore._floor_y(entry)
	var drops: BloodDrops = Gore.drops
	for strand: int in 2:
		for i: int in count:
			var z: float = length * float(i) / float(count - 1)
			var a: float = phase + strand * PI + z * turns_per_m * TAU
			var radial: Vector3 = Vector3(cos(a), sin(a), 0.0)
			var tangent: Vector3 = Vector3(-sin(a), cos(a), 0.0)
			var r: float = lerpf(0.025, 0.16, clampf(z / length, 0.0, 1.0))
			var at: Vector3 = entry + basis * (radial * r + Vector3(0, 0, z))
			# Spin round the axis, outward, and on along the shot (slower further out).
			var v: Vector3 = basis * (tangent * 1.0 + radial * 0.45 + Vector3(0, 0, lerpf(1.1, 0.4, z / length))).normalized()
			var size: float = _rng.randf_range(0.008, 0.022)
			drops.emit(at, v * _rng.randf_range(3.5, 7.5), size, BloodDrops.drag_for(size, 1.6), i % 5 == 2, floor_y)
			if i % 3 == 0:
				var fine: float = _rng.randf_range(0.003, 0.006)
				drops.emit(at, v * _rng.randf_range(1.5, 4.0), fine, BloodDrops.drag_for(fine, 3.2), false, floor_y, 0.9)
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
		# A body blown apart has nothing left for the arcs to crawl over.
		if s.left <= 0.0 or not is_instance_valid(s.body) or s.body.gibbed:
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
