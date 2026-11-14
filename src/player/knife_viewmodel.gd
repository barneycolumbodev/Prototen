class_name KnifeViewmodel
extends Node3D
## The first-person knife for the R3 strike (PlayerMelee). The gun drops out of
## view, the operative's right hand comes up from the lower right with the
## KB-1 knife, cocks, slashes across the screen and leaves, and the gun comes
## back. The slash is keyframed in camera space in MeleeConfig (position,
## where the forearm comes from, which way the edge faces), interpolated with
## Catmull-Rom positions and slerped orientations, so it's tuned in the .tres.
## A trail ribbon is swept along the edge from the same curve (sampled at
## past times, so it's smooth however fast the swing and the frame rate).

const TRAIL_SAMPLES: int = 22
## Blood on the blade (owner 2026-11-14): every cut adds to it and it stays,
## creeping from the tip back toward the guard, fresh red over darker dried
## blood. Drawn as a second pass over the blade's own materials.
const BLOOD_SHADER: String = """
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, shadows_disabled;
uniform float coat : hint_range(0.0, 1.0) = 0.0;
uniform float fresh : hint_range(0.0, 1.0) = 0.0;
uniform vec3 tip = vec3(0.0);
uniform vec3 base = vec3(0.0, 0.0, 0.1);
varying vec3 v_local;
float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float noise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
			mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
void vertex() {
	v_local = VERTEX;
}
void fragment() {
	vec3 axis = tip - base;
	float along = clamp(dot(v_local - base, axis) / max(dot(axis, axis), 1e-6), 0.0, 1.0);
	float n = noise(v_local * 90.0) * 0.6 + noise(v_local * 260.0) * 0.4;
	// Tip first; streaks run back toward the guard as the coat builds.
	float reach = coat * 1.25 - (1.0 - along) * 0.9;
	float m = smoothstep(0.0, 0.12, reach + (n - 0.5) * 0.35);
	if (m < 0.01) {
		discard;
	}
	vec3 dried = vec3(0.16, 0.012, 0.01);
	vec3 wet = vec3(0.42, 0.015, 0.012);
	float w = clamp(fresh * 1.2 - n * 0.4, 0.0, 1.0);
	ALBEDO = mix(dried, wet, w);
	ROUGHNESS = mix(0.55, 0.12, w);
	METALLIC = 0.0;
	SPECULAR = 0.6;
	ALPHA = m * mix(0.85, 0.97, w);
}
"""
const TRAIL_SHADER: String = """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;
void fragment() {
	// UV.y: 0 at the hilt, 1 at the tip. Brightest just inside the edge line.
	float across = smoothstep(0.45, 0.9, UV.y) * (1.0 - smoothstep(0.96, 1.0, UV.y));
	ALBEDO = COLOR.rgb * across * COLOR.a;
}
"""

var cfg: MeleeConfig
var rig: ArmRig
## Strike time (s at melee_speed 1); < 0 when no strike is playing.
var t: float = -1.0
var speed: float = 1.0
var _tip_local: Vector3 = Vector3.ZERO
var _base_local: Vector3 = Vector3.ZERO
var _quats: Array[Quaternion] = []
var _trail: MeshInstance3D
var _im: ImmediateMesh = ImmediateMesh.new()
var _blood: float = 0.0
## How much blood the blade carries (0..1); grows with each cut, never resets.
var blood_coat: float = 0.0
## How fresh the newest blood is (1 just after a cut, fades over a minute).
var blood_fresh: float = 0.0
var _blood_mat: ShaderMaterial
var _blood_mats: Array[ShaderMaterial] = []


static func make(player: Player, p_cfg: MeleeConfig) -> KnifeViewmodel:
	var k: KnifeViewmodel = KnifeViewmodel.new()
	k.name = "KnifeViewmodel"
	k.cfg = p_cfg
	k._build_keys()
	var cam: Camera3D = player.camera() if player else null
	k.rig = ArmRig.make(player, p_cfg.knife_scene, null, "KnifeRig", false)
	if cam == null:
		k.add_child(k.rig)
	var tip: Node3D = k.rig.part("blade_tip")
	var base: Node3D = k.rig.part("blade_base")
	if tip and base:
		k._tip_local = _local_to(tip, k.rig).origin
		k._base_local = _local_to(base, k.rig).origin
	k._coat_blade()
	k._trail = MeshInstance3D.new()
	k._trail.name = "KnifeTrail"
	k._trail.mesh = k._im
	k._trail.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	k._trail.ignore_occlusion_culling = true
	k._trail.extra_cull_margin = 2.0
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = TRAIL_SHADER
	mat.shader = sh
	k._trail.material_override = mat
	if cam:
		cam.add_child(k._trail)
	else:
		k.add_child(k._trail)
	return k


## `node`'s transform relative to `ancestor` (works before entering the tree).
static func _local_to(node: Node3D, ancestor: Node3D) -> Transform3D:
	var x: Transform3D = Transform3D.IDENTITY
	var n: Node = node
	while n != null and n != ancestor:
		if n is Node3D:
			x = (n as Node3D).transform * x
		n = n.get_parent()
	return x


## Puts the blood pass on the blade's surfaces (blade_steel, blade_coat).
func _coat_blade() -> void:
	_blood_mat = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = BLOOD_SHADER
	_blood_mat.shader = sh
	_blood_mat.render_priority = 1
	for node: Node in rig.model.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = node as MeshInstance3D
		if mi.mesh == null:
			continue
		var to_mesh: Transform3D = _local_to(mi, rig).affine_inverse()
		var bm: ShaderMaterial = null
		for i: int in mi.mesh.get_surface_count():
			var m: Material = mi.get_active_material(i)
			if m == null or not (m.resource_name.begins_with("blade_")):
				continue
			var own: Material = m.duplicate() as Material
			# One blood pass per mesh: the blade's tip and base in that mesh's own coordinates.
			if bm == null:
				bm = _blood_mat.duplicate() as ShaderMaterial
				bm.set_shader_parameter(&"tip", to_mesh * _tip_local)
				bm.set_shader_parameter(&"base", to_mesh * _base_local)
				_blood_mats.append(bm)
			own.next_pass = bm
			mi.set_surface_override_material(i, own)
	_apply_blood()


func blood_materials() -> Array[ShaderMaterial]:
	return _blood_mats


func _apply_blood() -> void:
	for bm: ShaderMaterial in blood_materials():
		bm.set_shader_parameter(&"coat", blood_coat)
		bm.set_shader_parameter(&"fresh", blood_fresh)


func _exit_tree() -> void:
	if is_instance_valid(rig):
		rig.queue_free()
	if is_instance_valid(_trail):
		_trail.queue_free()


func _build_keys() -> void:
	_quats.clear()
	for i: int in cfg.knife_times.size():
		_quats.append(_key_basis(cfg.knife_forearm[i], cfg.knife_edge[i]).get_rotation_quaternion())


## Model axes (Godot): forearm runs to −X, the edge faces −Y, the thumb −Z.
static func _key_basis(forearm: Vector3, edge: Vector3) -> Basis:
	var f: Vector3 = forearm.normalized()
	var e: Vector3 = (edge - f * edge.dot(f)).normalized()
	var th: Vector3 = e.cross(f)
	return Basis(-f, -e, -th).orthonormalized()


func length() -> float:
	return cfg.knife_times[cfg.knife_times.size() - 1]


func playing() -> bool:
	return t >= 0.0


## Starts the slash; `p_speed` = the body's melee_speed (the clip runs faster).
func play(p_speed: float) -> void:
	t = 0.0
	speed = maxf(p_speed, 0.1)
	_blood = 0.0
	rig.visible = true


## The blade went through someone: the trail and the swing after it run red.
func cut(lethal: bool) -> void:
	_blood = 1.0 if lethal else 0.75
	blood_coat = minf(blood_coat + (cfg.blood_per_kill if lethal else cfg.blood_per_cut), 1.0)
	blood_fresh = 1.0
	_apply_blood()


## Camera-space pose of the hand (the handle centre) at strike time `at`.
func pose(at: float) -> Transform3D:
	var times: PackedFloat32Array = cfg.knife_times
	var n: int = times.size()
	at = clampf(at, times[0], times[n - 1])
	var i: int = 0
	while i < n - 2 and at > times[i + 1]:
		i += 1
	var span: float = maxf(times[i + 1] - times[i], 0.0001)
	var u: float = clampf((at - times[i]) / span, 0.0, 1.0)
	var p: PackedVector3Array = cfg.knife_pos
	var p0: Vector3 = p[maxi(i - 1, 0)]
	var p3: Vector3 = p[mini(i + 2, n - 1)]
	var pos: Vector3 = p[i].cubic_interpolate(p[i + 1], p0, p3, u)
	var q: Quaternion = _quats[i].slerp(_quats[i + 1], u * u * (3.0 - 2.0 * u))
	return Transform3D(Basis(q), pos)


## How far the gun is out of the way (0 = in place, 1 = fully down).
func gun_away() -> float:
	if t < 0.0:
		return 0.0
	var down: float = clampf(t / maxf(cfg.gun_away_in, 0.001), 0.0, 1.0)
	var up: float = clampf((t - cfg.gun_return_at) / maxf(length() - cfg.gun_return_at, 0.001), 0.0, 1.0)
	return smoothstep(0.0, 1.0, down) * (1.0 - smoothstep(0.0, 1.0, up))


## Advances the clip. Call every frame with the player's delta.
func tick(delta: float) -> void:
	_im.clear_surfaces()
	if blood_fresh > 0.0:
		blood_fresh = maxf(blood_fresh - delta / maxf(cfg.blood_dry_time, 0.1), 0.0)
		if rig.visible:
			_apply_blood()
	if t < 0.0:
		return
	t += delta * speed
	if t >= length():
		t = -1.0
		rig.visible = false
		return
	rig.transform = pose(t)
	_draw_trail()


func _draw_trail() -> void:
	var span: float = cfg.trail_time
	var pts_tip: PackedVector3Array = []
	var pts_base: PackedVector3Array = []
	var alpha: PackedFloat32Array = []
	var prev_tip: Vector3 = Vector3.INF
	var any: bool = false
	for k: int in TRAIL_SAMPLES + 1:
		var at: float = t - span * (1.0 - float(k) / TRAIL_SAMPLES)
		if at < 0.0:
			continue
		var x: Transform3D = pose(at)
		var tip: Vector3 = x * _tip_local
		var spd: float = 0.0
		if prev_tip != Vector3.INF:
			spd = tip.distance_to(prev_tip) / (span / TRAIL_SAMPLES)
		prev_tip = tip
		var a: float = clampf((spd - cfg.trail_min_speed) / maxf(cfg.trail_min_speed, 0.01), 0.0, 1.0)
		a *= pow(float(k) / TRAIL_SAMPLES, 1.6)
		any = any or a > 0.01
		pts_tip.append(tip)
		pts_base.append(x * _base_local)
		alpha.append(a)
	if not any or pts_tip.size() < 2:
		return
	var col: Color = cfg.trail_color.lerp(cfg.trail_blood_color, _blood)
	_im.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	for k: int in pts_tip.size():
		var c: Color = Color(col.r, col.g, col.b, alpha[k] * col.a)
		_im.surface_set_color(c)
		_im.surface_set_uv(Vector2(float(k) / pts_tip.size(), 0.0))
		_im.surface_add_vertex(pts_base[k])
		_im.surface_set_color(c)
		_im.surface_set_uv(Vector2(float(k) / pts_tip.size(), 1.0))
		_im.surface_add_vertex(pts_tip[k])
	_im.surface_end()
