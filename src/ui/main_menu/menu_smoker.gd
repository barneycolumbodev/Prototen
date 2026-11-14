class_name MenuSmoker
extends Node3D
## The operative in the main menu (owner, 2026-11-14): helmet off, leaning
## back on the restaurant front with his right boot flat on the wall, left
## arm folded across his stomach under the right elbow, smoking. Every
## `config.cycle_seconds` the cigarette goes to his mouth, the ember flares
## while he draws on it, it comes down and he breathes the smoke out; smoke
## curls off the tip the whole time. The figure is a BodyAppearance, so the
## loadout screen can dress him in whatever is being built.
##
## The pose is procedural on the operative's skeleton (no clip): each bone
## gets a rotation in the model's rest frame carried by its parent (FK), the
## arms and legs are two-bone IK onto targets (hands to the mouth and the
## stomach, feet to the pavement and the wall), and the hands and feet are
## aimed. Lives under the figure's node; +Z is the street, -Z the wall.

## Lips on the bare head at rest (model space; from the head mesh).
const LIPS_REST: Vector3 = Vector3(0.0, 1.672, 0.11)
## The standing (left) ankle: the lean pivots about it.
const LEAN_PIVOT: Vector3 = Vector3(0.11, 0.09, 0.0)
## The wall, from his heels (m, -Z).
const WALL_Z: float = -0.34
## Cigarette (m): filter, paper, radius, and where the fingers hold it from the filter end.
const CIG_FILTER: float = 0.024
const CIG_PAPER: float = 0.068
const CIG_R: float = 0.0042
const CIG_HOLD: float = 0.03
const EMBER_COLOR: Color = Color(1.0, 0.42, 0.12)
const SMOKE_SHADER: Shader = preload("res://src/ui/main_menu/cig_smoke.gdshader")

var config: MenuSceneConfig
var appearance: BodyAppearance
var skeleton: Skeleton3D
## Where the camera is (for the head turn), world space.
var look_from: Vector3 = Vector3.INF
## Time into the current cycle (s), and the pose weights it gives.
var t: float = 0.0
var raise: float = 0.0
var drawing: float = 0.0
var exhaling: float = 0.0
## Holds the cycle at this time (lookdev and captures); < 0: runs.
var hold_t: float = -1.0

var cig: Node3D
var ember_light: OmniLight3D
var tip_smoke: GPUParticles3D
var breath_smoke: GPUParticles3D

var _ember_mat: StandardMaterial3D
var _rest_g: Array[Transform3D] = []
var _rest_l: Array[Transform3D] = []
var _parent: PackedInt32Array = PackedInt32Array()
var _order: PackedInt32Array = PackedInt32Array()
var _d: Array[Quaternion] = []
var _acc: Array[Transform3D] = []
var _b: Dictionary[StringName, int] = {}
## Wrist to the filter end (figure space) from the last solve: the hand is
## placed so the filter ends up on his lips.
var _filter_offset: Vector3 = Vector3(0.06, 0.04, -0.08)
var _clock: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _next_cycle: float = 10.0
var _flick: float = -1.0


func _ready() -> void:
	_rng.seed = 2026
	appearance = BodyAppearance.new()
	appearance.helmet_on = false
	add_child(appearance)
	skeleton = appearance.skeleton
	_read_rest()
	_build_cigarette()
	_build_smoke()
	_next_cycle = config.cycle_seconds
	# Start a little before a drag, so the first thing you see is him smoking.
	t = config.cycle_seconds - 1.2
	_solve()
	_solve()


func _read_rest() -> void:
	var n: int = skeleton.get_bone_count()
	_parent.resize(n)
	for i: int in n:
		_rest_g.append(skeleton.get_bone_global_rest(i))
		_rest_l.append(skeleton.get_bone_rest(i))
		_parent[i] = skeleton.get_bone_parent(i)
		_b[StringName(skeleton.get_bone_name(i))] = i
		_d.append(Quaternion.IDENTITY)
		_acc.append(Transform3D.IDENTITY)
	# Parents first; the head before the arms (the right hand goes to the
	# lips), the right arm before the left (the left hand goes under the
	# right elbow).
	var first: Array[StringName] = [&"root", &"hips", &"spine", &"chest", &"neck", &"head",
		&"thigh.L", &"shin.L", &"foot.L", &"thigh.R", &"shin.R", &"foot.R",
		&"clavicle.R", &"upper_arm.R", &"forearm.R", &"hand.R", &"fingers.R",
		&"clavicle.L", &"upper_arm.L", &"forearm.L", &"hand.L", &"fingers.L"]
	for nm: StringName in first:
		if _b.has(nm):
			_order.append(_b[nm])
	for i: int in n:
		if not _order.has(i):
			_order.append(i)


func bone(nm: StringName) -> int:
	return _b.get(nm, -1)


## Posed transform of a bone in the figure's space.
func bone_pose(nm: StringName) -> Transform3D:
	var i: int = bone(nm)
	return _acc[i] * _rest_g[i] if i >= 0 else Transform3D.IDENTITY


func lips() -> Vector3:
	return _acc[bone(&"head")] * LIPS_REST


func ember_position() -> Vector3:
	return cig.global_transform * Vector3(0, CIG_FILTER + CIG_PAPER + 0.003, 0)


func _process(delta: float) -> void:
	_clock += delta
	t += delta
	if t >= _next_cycle:
		t = 0.0
		_next_cycle = config.cycle_seconds * _rng.randf_range(0.85, 1.2)
		_flick = _rng.randf_range(4.5, 6.5)
	if hold_t >= 0.0:
		t = hold_t
	_weights()
	_solve()
	_update_effects()


## raise / drawing / exhaling from the time in the cycle.
func _weights() -> void:
	var c: MenuSceneConfig = config
	var up_end: float = c.raise_seconds
	var drag_end: float = up_end + c.drag_seconds
	var down_end: float = drag_end + c.lower_seconds
	if t < up_end:
		raise = _ease(t / up_end)
	elif t < drag_end:
		raise = 1.0
	elif t < down_end:
		raise = 1.0 - _ease((t - drag_end) / c.lower_seconds)
	else:
		raise = 0.0
	drawing = clampf((t - up_end * 0.8) / 0.4, 0.0, 1.0) * clampf((drag_end + 0.15 - t) / 0.3, 0.0, 1.0)
	var ex0: float = drag_end + 0.2
	exhaling = clampf((t - ex0) / 0.3, 0.0, 1.0) * clampf((ex0 + c.exhale_seconds - t) / 0.6, 0.0, 1.0)


static func _ease(x: float) -> float:
	var y: float = clampf(x, 0.0, 1.0)
	return y * y * (3.0 - 2.0 * y)


# ------------------------------------------------------------------ the pose

func _solve() -> void:
	var c: MenuSceneConfig = config
	var breathe: float = sin(_clock * TAU / 4.4)
	for i: int in _d.size():
		_d[i] = Quaternion.IDENTITY
	_d[bone(&"root")] = Quaternion(Vector3.RIGHT, -deg_to_rad(c.lean_deg + 0.35 * breathe))
	_d[bone(&"hips")] = Quaternion(Vector3.UP, deg_to_rad(-6.0)) * Quaternion(Vector3.BACK, deg_to_rad(2.5))
	_d[bone(&"spine")] = Quaternion(Vector3.RIGHT, deg_to_rad(3.0)) * Quaternion(Vector3.UP, deg_to_rad(4.0))
	_d[bone(&"chest")] = Quaternion(Vector3.RIGHT, deg_to_rad(3.0 + 1.0 * breathe - 3.0 * exhaling))
	# Head: chin a touch down, turned toward the camera; up while he breathes out.
	var yaw: float = deg_to_rad(10.0) + 0.06 * sin(_clock * 0.37)
	if look_from != Vector3.INF:
		var cam: Vector3 = global_transform.affine_inverse() * look_from
		yaw = clampf(atan2(cam.x, cam.z), -0.5, 0.5) * 0.55 + 0.05 * sin(_clock * 0.37)
	var pitch: float = deg_to_rad(9.0 - 16.0 * exhaling - 4.0 * raise)
	_d[bone(&"neck")] = Quaternion(Vector3.UP, yaw * 0.4) * Quaternion(Vector3.RIGHT, pitch * 0.5)
	_d[bone(&"head")] = Quaternion(Vector3.UP, yaw * 0.6) * Quaternion(Vector3.RIGHT, pitch * 0.5 + deg_to_rad(4.0))
	_d[bone(&"clavicle.R")] = Quaternion(Vector3.BACK, deg_to_rad(-4.0 * raise))
	for i: int in _order:
		_pose_bone(i)
	_apply()
	_place_cigarette()


func _pose_bone(i: int) -> void:
	var par: int = _parent[i]
	var acc_p: Transform3D = _acc[par] if par >= 0 else Transform3D.IDENTITY
	var nm: StringName = StringName(skeleton.get_bone_name(i))
	match nm:
		&"thigh.L":
			_two_bone(i, bone(&"shin.L"), bone(&"foot.L"), acc_p, Vector3(0.13, 0.09, 0.05), Vector3(0.15, 0.0, 1.0))
		&"thigh.R":
			_two_bone(i, bone(&"shin.R"), bone(&"foot.R"), acc_p, Vector3(-0.2, 0.45, WALL_Z + 0.1), Vector3(-0.5, 0.15, 1.0))
		&"foot.L":
			_aim(i, acc_p, Vector3(0.18, -0.4, 0.9), Vector3(0.0, 0.9, 0.4), _rest_g[i].basis.y, Vector3(0.0, 0.89, 0.46))
		&"foot.R":
			_aim(i, acc_p, Vector3(-0.05, -1.0, -0.12), Vector3(0.0, 0.1, 1.0), _rest_g[i].basis.y, Vector3(0.0, 0.89, 0.46))
		&"upper_arm.R":
			_two_bone(i, bone(&"forearm.R"), bone(&"hand.R"), acc_p, _right_wrist_target(), _right_pole())
		&"upper_arm.L":
			# The left hand under the right elbow, or where it was folded.
			var chest: Transform3D = _acc[bone(&"chest")]
			var fold: Vector3 = chest * Vector3(-0.13, 1.16, 0.19)
			var elbow: Vector3 = bone_pose(&"forearm.R").origin + Vector3(0.03, -0.06, 0.03)
			var w: Vector3 = fold.lerp(elbow, clampf(1.0 - raise * 1.3, 0.0, 1.0) * 0.8)
			_two_bone(i, bone(&"forearm.L"), bone(&"hand.L"), acc_p, w, chest.basis * Vector3(1.0, -0.7, 0.2))
		&"hand.R":
			_aim_hand_r(i, acc_p)
		&"hand.L":
			var chest_b: Basis = _acc[bone(&"chest")].basis
			_aim(i, acc_p, chest_b * Vector3(-1.0, 0.1, 0.35), chest_b * Vector3(0.1, 1.0, -0.25), _hand_dir(i), Vector3(-1, 0, 0))
		&"fingers.R":
			_curl(i, bone(&"hand.R"), Vector3(1, 0, 0), deg_to_rad(22.0))
		&"fingers.L":
			_curl(i, bone(&"hand.L"), Vector3(-1, 0, 0), deg_to_rad(55.0))
	var b: Basis = Basis(_d[i])
	var pivot: Vector3 = LEAN_PIVOT if par < 0 else _rest_g[i].origin
	_acc[i] = acc_p * Transform3D(b, pivot - b * pivot)


## Idle: the hand in front of his chest, the cigarette pointing out and down.
## Up: the filter on his lips.
func _right_wrist_target() -> Vector3:
	var chest: Transform3D = _acc[bone(&"chest")]
	var idle: Vector3 = chest * Vector3(-0.17, 1.33, 0.27)
	var flick: float = 0.0
	if _flick > 0.0:
		flick = maxf(0.0, 1.0 - absf(t - _flick) / 0.12)
	idle += chest.basis * Vector3(0.0, -0.03, 0.0) * flick
	var mouth: Vector3 = lips() - _filter_offset
	return idle.lerp(mouth, raise)


func _right_pole() -> Vector3:
	var chest_b: Basis = _acc[bone(&"chest")].basis
	return chest_b * Vector3(-0.6, -1.0, 0.1).lerp(Vector3(-0.8, -0.6, 0.0), raise)


## Fingers up beside his mouth with the palm to his face when it's up; at
## rest the palm faces in and a little up, so the cigarette points out.
func _aim_hand_r(i: int, acc_p: Transform3D) -> void:
	var chest_b: Basis = _acc[bone(&"chest")].basis
	var head_b: Basis = _acc[bone(&"head")].basis
	var wrist: Vector3 = acc_p * _rest_g[i].origin
	var fore: Vector3 = (wrist - bone_pose(&"forearm.R").origin).normalized()
	var dir_idle: Vector3 = (fore + chest_b * Vector3(0.1, 0.25, 0.2)).normalized()
	var palm_idle: Vector3 = chest_b * Vector3(0.75, 0.55, -0.2)
	# Off to his right of the mouth, so the face shows past the hand.
	var dir_up: Vector3 = head_b * Vector3(-0.4, 0.9, 0.15)
	var palm_up: Vector3 = head_b * Vector3(0.8, 0.0, -0.6)
	var k: float = _ease(raise)
	_aim(i, acc_p, dir_idle.slerp(dir_up.normalized(), k), palm_idle.normalized().slerp(palm_up.normalized(), k), _hand_dir(i), Vector3(1, 0, 0))


func _hand_dir(i: int) -> Vector3:
	var fingers: int = i + 1
	return (_rest_g[fingers].origin - _rest_g[i].origin).normalized()


## Fingers curled toward the palm by `angle`, in the hand's frame.
func _curl(i: int, hand: int, palm_rest: Vector3, angle: float) -> void:
	var hd: Vector3 = _hand_dir(hand)
	var palm: Vector3 = (palm_rest - hd * palm_rest.dot(hd)).normalized()
	_d[i] = Quaternion(hd.cross(palm).normalized(), angle)


## Two-bone IK: upper (head at the shoulder or hip) and lower so the end
## bone's head reaches `target`; the middle joint bends toward `pole`. Both
## in figure space; the solve runs in the parent's rest frame.
func _two_bone(upper: int, lower: int, end: int, acc_p: Transform3D, target: Vector3, pole: Vector3) -> void:
	var tr: Vector3 = acc_p.affine_inverse() * target
	var pl: Vector3 = (acc_p.basis.inverse() * pole).normalized()
	var s: Vector3 = _rest_g[upper].origin
	var e0: Vector3 = _rest_g[lower].origin
	var w0: Vector3 = _rest_g[end].origin
	var a: float = s.distance_to(e0)
	var b: float = e0.distance_to(w0)
	var to: Vector3 = tr - s
	var d: float = clampf(to.length(), absf(a - b) + 0.002, a + b - 0.002)
	var nrm: Vector3 = to.normalized()
	var cos_a: float = clampf((a * a + d * d - b * b) / (2.0 * a * d), -1.0, 1.0)
	var perp: Vector3 = pl - nrm * pl.dot(nrm)
	if perp.length() < 0.001:
		perp = nrm.cross(Vector3.RIGHT)
	perp = perp.normalized()
	var e: Vector3 = s + nrm * a * cos_a + perp * a * sqrt(1.0 - cos_a * cos_a)
	var w: Vector3 = s + nrm * d
	_d[upper] = Quaternion((e0 - s).normalized(), (e - s).normalized())
	var du: Basis = Basis(_d[upper])
	_d[lower] = Quaternion((w0 - e0).normalized(), (du.inverse() * (w - e)).normalized())


## Turns bone i so its rest direction points along `dir` and the rest
## `up_rest` side faces `up` (both figure space).
func _aim(i: int, acc_p: Transform3D, dir: Vector3, up: Vector3, dir_rest: Vector3, up_rest: Vector3) -> void:
	var inv: Basis = acc_p.basis.inverse()
	var tb: Basis = _frame(inv * dir, inv * up)
	var rb: Basis = _frame(dir_rest, up_rest)
	_d[i] = (tb * rb.inverse()).get_rotation_quaternion()


static func _frame(fwd: Vector3, up: Vector3) -> Basis:
	var y: Vector3 = fwd.normalized()
	var z: Vector3 = up - y * up.dot(y)
	z = z.normalized() if z.length() > 0.0001 else y.cross(Vector3.RIGHT).normalized()
	return Basis(y.cross(z), y, z)


func _apply() -> void:
	for i: int in _order:
		var par: int = _parent[i]
		if par < 0:
			var g: Transform3D = _acc[i] * _rest_g[i]
			skeleton.set_bone_pose_position(i, g.origin)
			skeleton.set_bone_pose_rotation(i, g.basis.get_rotation_quaternion())
			continue
		var lb: Basis = _rest_g[par].basis.inverse() * Basis(_d[i]) * _rest_g[i].basis
		skeleton.set_bone_pose_position(i, _rest_l[i].origin)
		skeleton.set_bone_pose_rotation(i, lb.get_rotation_quaternion())


# ------------------------------------------------------------------ cigarette and smoke

func _build_cigarette() -> void:
	cig = Node3D.new()
	cig.name = "Cigarette"
	add_child(cig)
	var parts: Array[Array] = [
		[CIG_FILTER, CIG_FILTER * 0.5, Color(0.78, 0.52, 0.26), 0.6],
		[CIG_PAPER, CIG_FILTER + CIG_PAPER * 0.5, Color(0.93, 0.91, 0.87), 0.8],
		[0.006, CIG_FILTER + CIG_PAPER + 0.003, Color(0.32, 0.31, 0.3), 1.0],
	]
	for p: Array in parts:
		var h: float = p[0]
		var y: float = p[1]
		var col: Color = p[2]
		var rough: float = p[3]
		var mi: MeshInstance3D = MeshInstance3D.new()
		var cm: CylinderMesh = CylinderMesh.new()
		cm.top_radius = CIG_R
		cm.bottom_radius = CIG_R
		cm.height = h
		cm.radial_segments = 8
		cm.rings = 1
		mi.mesh = cm
		var m: StandardMaterial3D = StandardMaterial3D.new()
		m.albedo_color = col
		m.roughness = rough
		mi.material_override = m
		mi.position.y = y
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		cig.add_child(mi)
	var ember: MeshInstance3D = MeshInstance3D.new()
	var em: CylinderMesh = CylinderMesh.new()
	em.top_radius = CIG_R * 0.85
	em.bottom_radius = CIG_R * 0.98
	em.height = 0.004
	em.radial_segments = 8
	em.rings = 1
	ember.mesh = em
	_ember_mat = StandardMaterial3D.new()
	_ember_mat.albedo_color = Color(0.2, 0.05, 0.02)
	_ember_mat.emission_enabled = true
	_ember_mat.emission = EMBER_COLOR
	_ember_mat.emission_energy_multiplier = 2.0
	ember.material_override = _ember_mat
	ember.position.y = CIG_FILTER + CIG_PAPER + 0.008
	ember.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	cig.add_child(ember)
	ember_light = OmniLight3D.new()
	ember_light.light_color = EMBER_COLOR
	ember_light.omni_range = config.ember_range
	ember_light.light_energy = config.ember_energy_idle
	ember_light.position.y = CIG_FILTER + CIG_PAPER + 0.015
	# Only the figure (the map's lighting is baked).
	ember_light.light_cull_mask = 0xFFFFF & ~ChinatownMap.MAP_LAYER
	cig.add_child(ember_light)


## Filter end at the fingers (palm side), along the back of the hand.
func _place_cigarette() -> void:
	var hand: Transform3D = bone_pose(&"hand.R")
	var fingers: Transform3D = bone_pose(&"fingers.R")
	var hb: Basis = _acc[bone(&"hand.R")].basis
	var hd: Vector3 = _hand_dir(bone(&"hand.R"))
	var palm_rest: Vector3 = (Vector3(1, 0, 0) - hd * hd.x).normalized()
	var palm: Vector3 = (hb * palm_rest).normalized()
	var along: Vector3 = (fingers.origin - hand.origin).normalized()
	var hold: Vector3 = fingers.origin + along * 0.03
	var filter_end: Vector3 = hold + palm * CIG_HOLD
	var axis: Vector3 = -palm
	var side: Vector3 = along.cross(axis).normalized()
	cig.transform = Transform3D(Basis(side, axis, side.cross(axis)), filter_end)
	_filter_offset = filter_end - hand.origin


func _build_smoke() -> void:
	tip_smoke = _smoke_emitter(18, 2.8, 0.035, Vector3(0.02, 0.09, 0.0), 0.05, 0.12, 0.3, 2.2, 0.28)
	breath_smoke = _smoke_emitter(36, 2.4, 0.07, Vector3(0.01, 0.05, 0.0), 0.35, 0.75, 0.5, 2.6, 0.22)
	breath_smoke.emitting = false
	tip_smoke.emitting = true


func _smoke_emitter(amount: int, life: float, size: float, gravity: Vector3, v_min: float, v_max: float,
		scale0: float, scale1: float, opacity: float) -> GPUParticles3D:
	var pm: ParticleProcessMaterial = ParticleProcessMaterial.new()
	pm.direction = Vector3.UP
	pm.spread = 14.0
	pm.initial_velocity_min = v_min
	pm.initial_velocity_max = v_max
	pm.gravity = gravity
	pm.damping_min = 0.4
	pm.damping_max = 0.9
	pm.scale_min = 0.8
	pm.scale_max = 1.3
	var curve: CurveTexture = CurveTexture.new()
	var cv: Curve = Curve.new()
	cv.max_value = 4.0
	cv.add_point(Vector2(0, scale0))
	cv.add_point(Vector2(1, scale1))
	curve.curve = cv
	pm.scale_curve = curve
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2(size, size)
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = SMOKE_SHADER
	mat.set_shader_parameter(&"opacity", opacity)
	q.material = mat
	var p: GPUParticles3D = GPUParticles3D.new()
	p.amount = amount
	p.lifetime = life
	p.local_coords = false
	p.process_material = pm
	p.draw_pass_1 = q
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.visibility_aabb = AABB(Vector3(-2, -1, -2), Vector3(4, 4, 4))
	add_child(p)
	return p


func _update_effects() -> void:
	var c: MenuSceneConfig = config
	var flicker: float = 0.85 + 0.15 * sin(_clock * 23.0) * sin(_clock * 7.3)
	var e: float = lerpf(c.ember_energy_idle, c.ember_energy_drag, drawing) * flicker
	ember_light.light_energy = e
	_ember_mat.emission_energy_multiplier = lerpf(1.6, 9.0, drawing) * flicker
	tip_smoke.global_position = ember_position()
	# He's drawing: no smoke off the tip (it goes into him).
	tip_smoke.amount_ratio = 1.0 - drawing * 0.8
	var mouth_xf: Transform3D = global_transform * _acc[bone(&"head")]
	breath_smoke.global_position = global_transform * lips() + mouth_xf.basis * Vector3(0, -0.005, 0.02)
	var out: Vector3 = (mouth_xf.basis * Vector3(0.05, -0.35, 1.0)).normalized()
	var pm: ParticleProcessMaterial = breath_smoke.process_material as ParticleProcessMaterial
	pm.direction = out
	breath_smoke.emitting = exhaling > 0.2
	breath_smoke.amount_ratio = clampf(exhaling, 0.0, 1.0)
