class_name DropkickViewmodel
extends Node3D
## First-person GS-2 legs and combat boots for the midair dropkick
## (docs/design.md §5.7b). Instantiates `cfg.legs_scene` under the player's
## camera, collapses it with RigidMerge (one draw per material), and animates
## the articulated thighs, shins and boots procedurally:
##   1. Chamber: knees snap up tight toward the chest like a coiled spring.
##   2. Extension: asymmetric brutal double-boot thrust straight across the
##      lower third of the view (lead boot dead-forward, trail boot angled
##      slightly lower/beside; upper 60 % stays open for aiming and shooting).
##   3. Impact crunch: violent knee-buckle and pelvis recoil spring on contact.
##   4. Retract: legs fold cleanly below the screen on rebound or touchdown so
##      the view is completely clear for Max Payne / John Woo fall-back shots.
##
## Looking around mid-dive decouples gently from the legs: yaw trails toward
## the launch trajectory (clamped) and pitch is partially countered so aiming
## upward at a launched enemy looks over your boots instead of lifting them
## into the sky. Two sleek boot air-cut ribbons sweep during the snap kick.

const TRAIL_SHADER: String = """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;
void fragment() {
	float across = sin(UV.y * 3.14159265);
	ALBEDO = COLOR.rgb * across * COLOR.a;
}
"""
const TRAIL_POINTS: int = 12

enum State { IDLE, KICK, IMPACT_HOLD, RETRACT }

var cfg: DropkickConfig
var player: Player
var rig: Node3D
var model: Node3D
var state: State = State.IDLE

var _legs_root: Node3D
var _thigh_r: Node3D
var _shin_r: Node3D
var _boot_r: Node3D
var _sole_r: Node3D
var _heel_r: Node3D
var _thigh_l: Node3D
var _shin_l: Node3D
var _boot_l: Node3D
var _sole_l: Node3D
var _heel_l: Node3D

var _rest_root: Vector3 = Vector3.ZERO
var _t: float = 0.0
var _retract_t: float = 0.0
var _impact_hold_t: float = 0.0
## +1 = right lead leg (camera rolls left), -1 = left lead leg.
var _lead_sign: float = 1.0
var _lateral: bool = false
var _launch_yaw: float = 0.0
var _launch_pitch: float = 0.0
var _ads_drop: float = 0.0
var _impact_spring: Spring = Spring.new(11.0, 0.42)
var _knee_recoil: Spring = Spring.new(12.0, 0.45)

## Stored snapshot pose when retracting begins so retract blends smoothly from any frame.
var _snap_pos: Vector3 = Vector3.ZERO
var _snap_rot: Vector3 = Vector3.ZERO
var _snap_tr: Vector3 = Vector3.ZERO
var _snap_sr: float = 0.0
var _snap_br: Vector3 = Vector3.ZERO
var _snap_tl: Vector3 = Vector3.ZERO
var _snap_sl: float = 0.0
var _snap_bl: Vector3 = Vector3.ZERO

## Boot air-cut speed ribbons (drawn in camera space during the fast kick extension).
var _trail: MeshInstance3D
var _im: ImmediateMesh = ImmediateMesh.new()
var _hist_r_a: PackedVector3Array = PackedVector3Array()
var _hist_r_b: PackedVector3Array = PackedVector3Array()
var _hist_l_a: PackedVector3Array = PackedVector3Array()
var _hist_l_b: PackedVector3Array = PackedVector3Array()
var _hist_age: PackedFloat32Array = PackedFloat32Array()
var _hist_count: int = 0
var _glow_mats: Array[StandardMaterial3D] = []
var _glow_base: Color = Color(0.36, 0.86, 0.78)


static func make(p_player: Player, p_cfg: DropkickConfig) -> DropkickViewmodel:
	var vm: DropkickViewmodel = DropkickViewmodel.new()
	vm.name = "DropkickViewmodel"
	vm.player = p_player
	vm.cfg = p_cfg
	vm.rig = Node3D.new()
	vm.rig.name = "DropkickLegsRig"
	vm.rig.visible = false
	var cam: Camera3D = p_player.camera() if p_player else null
	if cam:
		cam.add_child(vm.rig)
	else:
		vm.add_child(vm.rig)
	if p_cfg and p_cfg.legs_scene:
		vm.model = p_cfg.legs_scene.instantiate() as Node3D
		vm.rig.add_child(vm.model)
		vm._bind_parts()
		RigidMerge.apply(vm.model)
		for n: Node in vm.model.find_children("*", "MeshInstance3D", true, false):
			(n as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		vm._cache_glow_mats()
		vm.add_to_group(&"suit_painted")
		if p_player and p_player.colors:
			vm.repaint(p_player.colors)
	vm._trail = MeshInstance3D.new()
	vm._trail.name = "DropkickTrail"
	vm._trail.mesh = vm._im
	vm._trail.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = TRAIL_SHADER
	mat.shader = sh
	vm._trail.material_override = mat
	if cam:
		cam.add_child(vm._trail)
	else:
		vm.add_child(vm._trail)
	vm._hist_r_a.resize(TRAIL_POINTS)
	vm._hist_r_b.resize(TRAIL_POINTS)
	vm._hist_l_a.resize(TRAIL_POINTS)
	vm._hist_l_b.resize(TRAIL_POINTS)
	vm._hist_age.resize(TRAIL_POINTS)
	return vm


func _exit_tree() -> void:
	if is_instance_valid(rig):
		rig.queue_free()
	if is_instance_valid(_trail):
		_trail.queue_free()


func _bind_parts() -> void:
	if model == null:
		return
	_legs_root = model.find_child("legs_root", true, false) as Node3D
	_thigh_r = model.find_child("thigh_r", true, false) as Node3D
	_shin_r = model.find_child("shin_r", true, false) as Node3D
	_boot_r = model.find_child("boot_r", true, false) as Node3D
	_sole_r = model.find_child("sole_r", true, false) as Node3D
	_heel_r = model.find_child("heel_r", true, false) as Node3D
	_thigh_l = model.find_child("thigh_l", true, false) as Node3D
	_shin_l = model.find_child("shin_l", true, false) as Node3D
	_boot_l = model.find_child("boot_l", true, false) as Node3D
	_sole_l = model.find_child("sole_l", true, false) as Node3D
	_heel_l = model.find_child("heel_l", true, false) as Node3D
	if _legs_root:
		_rest_root = _legs_root.position


func _cache_glow_mats() -> void:
	_glow_mats.clear()
	if model == null:
		return
	for n: Node in model.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		if mi.mesh == null:
			continue
		for i: int in mi.mesh.get_surface_count():
			var m: StandardMaterial3D = mi.mesh.surface_get_material(i) as StandardMaterial3D
			if m and m.resource_name == "glow":
				var dup: StandardMaterial3D = m.duplicate() as StandardMaterial3D
				dup.resource_name = "glow"
				_glow_base = dup.emission
				mi.set_surface_override_material(i, dup)
				_glow_mats.append(dup)


## Repaints leg plates, boots, undersuit, trim and glowing seams from BodyColors.
func repaint(colors: BodyColors) -> void:
	if colors == null or model == null:
		return
	colors.apply_to_model(model, true)
	var c: Color = colors.color(&"lights", _glow_base) if colors.has(&"lights") else _glow_base
	for gm: StandardMaterial3D in _glow_mats:
		gm.emission = c


func is_active() -> bool:
	return state != State.IDLE


## Begins the kick animation. `lead_sign`: +1 right leg leads, -1 left leg leads.
## `lateral`: true for a sideways/backward Max Payne dive (lower, brisker leg sweep).
func start(launch_yaw: float, launch_pitch: float, lead_sign: float = 1.0, lateral: bool = false) -> void:
	state = State.KICK
	_t = 0.0
	_retract_t = 0.0
	_impact_hold_t = 0.0
	_lead_sign = 1.0 if lead_sign >= 0.0 else -1.0
	_lateral = lateral
	_launch_yaw = launch_yaw
	_launch_pitch = launch_pitch
	_impact_spring.reset()
	_knee_recoil.reset()
	_hist_count = 0
	_im.clear_surfaces()
	rig.visible = true
	_apply_kick_pose(0.0)


## Violent boot compression & recoil crunch on connecting with an enemy.
func on_impact() -> void:
	if state == State.IDLE:
		return
	state = State.IMPACT_HOLD
	_impact_hold_t = 0.0
	# Slam pelvis back & buckle knees hard to sell the weight of impact.
	_impact_spring.kick(Vector3(0.0, -0.04, 0.19))
	_knee_recoil.kick(Vector3(-42.0, -34.0, 0.0))


## Smoothly folds the legs below the viewport (rebound fall-back or landing).
func begin_retract() -> void:
	if state == State.IDLE or state == State.RETRACT:
		return
	_snapshot_current()
	state = State.RETRACT
	_retract_t = 0.0


## Immediate hide (respawn, death, state abort).
func stop() -> void:
	state = State.IDLE
	rig.visible = false
	_hist_count = 0
	_im.clear_surfaces()


## World-space position of the leading boot sole (for impact burst VFX).
func lead_sole_world() -> Vector3:
	var n: Node3D = _sole_r if _lead_sign > 0.0 else _sole_l
	if n and n.is_inside_tree():
		return n.global_position
	var cam: Camera3D = player.camera() if player else null
	return cam.global_position - cam.global_basis.z * 0.9 - cam.global_basis.y * 0.25 if cam else Vector3.ZERO


func tick(delta: float, ads: float) -> void:
	if state == State.IDLE:
		return
	_ads_drop = lerpf(_ads_drop, ads, 1.0 - exp(-18.0 * delta))
	_impact_spring.step(delta)
	_knee_recoil.step(delta)
	match state:
		State.KICK:
			_t += delta
			_apply_kick_pose(_t)
			# On a lateral/backward Max Payne dive, fold legs away quickly after the initial leap
			# so the screen stays crisp and wide open for shooting.
			if _lateral and _t >= cfg.chamber_time + cfg.extend_time + 0.08:
				begin_retract()
		State.IMPACT_HOLD:
			_t += delta
			_impact_hold_t += delta
			_apply_kick_pose(_t)
			if _impact_hold_t >= 0.075:
				begin_retract()
		State.RETRACT:
			_retract_t += delta
			var u: float = clampf(_retract_t / maxf(cfg.retract_time, 0.04), 0.0, 1.0)
			_apply_retract_pose(u)
			if u >= 1.0:
				stop()
				return
	_update_rig_decoupling()
	_update_trails(delta)


## Keeps the legs gently anchored toward the launch flight vector while the player
## looks around freely to shoot mid-dive.
func _update_rig_decoupling() -> void:
	if player == null:
		return
	var max_yaw: float = deg_to_rad(cfg.yaw_follow_max_deg)
	var dyaw: float = clampf(angle_difference(player.yaw, _launch_yaw), -max_yaw, max_yaw)
	var dpitch: float = clampf((_launch_pitch - player.pitch) * cfg.pitch_counter_share, deg_to_rad(-32.0), deg_to_rad(28.0))
	# Slight courtesy drop when ADS so boots never crowd iron sights or optics.
	var ads_off: Vector3 = Vector3(0.0, -0.09 * _ads_drop, 0.03 * _ads_drop)
	rig.transform = Transform3D(Basis.from_euler(Vector3(dpitch, dyaw, 0.0)), ads_off + _impact_spring.value)


## Cubic ease-out with slight energetic overshoot for the brutal kick snap.
static func _snap_out(u: float) -> float:
	var c: float = u - 1.0
	var s: float = 1.45
	return 1.0 + c * c * ((s + 1.0) * c + s)


static func _smooth(u: float) -> float:
	return u * u * (3.0 - 2.0 * u)


func _apply_kick_pose(t: float) -> void:
	var s: float = _lead_sign
	var lat_y: float = -0.11 if _lateral else 0.0
	# Key poses: 0 = hidden low, 1 = tight coiled chamber, 2 = explosive double-boot extension.
	var p0: Vector3 = Vector3(0.0, -0.64 + lat_y, 0.25)
	var p1: Vector3 = Vector3(-0.01 * s, -0.27 + lat_y, 0.15)
	var p2: Vector3 = Vector3(-0.008 * s, -0.24 + lat_y, 0.09)

	var r0: Vector3 = Vector3(-16.0, 0.0, 0.0)
	var r1: Vector3 = Vector3(-6.0, 0.0, 4.0 * s)
	var r2: Vector3 = Vector3(-3.0, 0.0, 5.0 * s)

	# Lead leg (right when s = +1) & trail leg (left when s = +1): twin armored boots
	# driving forward together below the crosshair with slight martial stagger.
	var lead_th0: Vector3 = Vector3(44.0, -1.0 * s, 1.0 * s)
	var lead_th1: Vector3 = Vector3(102.0, -1.0 * s, 1.0 * s)
	var lead_th2: Vector3 = Vector3(84.0, -1.0 * s, 1.0 * s)
	var lead_sh0: float = -110.0
	var lead_sh1: float = -96.0
	var lead_sh2: float = -8.0
	var lead_bt0: Vector3 = Vector3(16.0, 0.0, 0.0)
	var lead_bt1: Vector3 = Vector3(22.0, 0.0, -3.0 * s)
	var lead_bt2: Vector3 = Vector3(14.0, -4.0 * s, -8.0 * s)

	var trail_th0: Vector3 = Vector3(40.0, 1.0 * s, -1.0 * s)
	var trail_th1: Vector3 = Vector3(98.0, 1.0 * s, -1.0 * s)
	var trail_th2: Vector3 = Vector3(81.0, 1.0 * s, -1.0 * s)
	var trail_sh0: float = -114.0
	var trail_sh1: float = -102.0
	var trail_sh2: float = -13.0
	var trail_bt0: Vector3 = Vector3(14.0, 0.0, 0.0)
	var trail_bt1: Vector3 = Vector3(18.0, 3.0 * s, 4.0 * s)
	var trail_bt2: Vector3 = Vector3(12.0, 4.0 * s, 8.0 * s)

	var root_pos: Vector3
	var root_rot: Vector3
	var l_th: Vector3
	var l_sh: float
	var l_bt: Vector3
	var t_th: Vector3
	var t_sh: float
	var t_bt: Vector3

	var tc: float = maxf(cfg.chamber_time, 0.02)
	var te: float = maxf(cfg.extend_time, 0.02)
	if t < tc:
		var u: float = _smooth(clampf(t / tc, 0.0, 1.0))
		root_pos = p0.lerp(p1, u)
		root_rot = r0.lerp(r1, u)
		l_th = lead_th0.lerp(lead_th1, u)
		l_sh = lerpf(lead_sh0, lead_sh1, u)
		l_bt = lead_bt0.lerp(lead_bt1, u)
		t_th = trail_th0.lerp(trail_th1, u)
		t_sh = lerpf(trail_sh0, trail_sh1, u)
		t_bt = trail_bt0.lerp(trail_bt1, u)
	elif t < tc + te:
		var raw: float = clampf((t - tc) / te, 0.0, 1.0)
		var u: float = _snap_out(raw)
		# Trail leg fires a beat behind lead leg (~10 ms stagger) for organic martial power.
		var u_trail: float = _snap_out(clampf((raw - 0.09) / 0.91, 0.0, 1.0))
		root_pos = p1.lerp(p2, clampf(u, 0.0, 1.15))
		root_rot = r1.lerp(r2, clampf(u, 0.0, 1.12))
		l_th = lead_th1.lerp(lead_th2, u)
		l_sh = clampf(lerpf(lead_sh1, lead_sh2, u), -125.0, -2.0)
		l_bt = lead_bt1.lerp(lead_bt2, clampf(u, 0.0, 1.1))
		t_th = trail_th1.lerp(trail_th2, u_trail)
		t_sh = clampf(lerpf(trail_sh1, trail_sh2, u_trail), -125.0, -5.0)
		t_bt = trail_bt1.lerp(trail_bt2, clampf(u_trail, 0.0, 1.1))
	else:
		# Extended flight hold: subtle lowering to open sight picture + crisp wind buffet.
		var hold: float = t - (tc + te)
		var settle: float = 1.0 - exp(-hold * 4.0)
		var buffet: float = sin(hold * 34.0) * 0.8 + sin(hold * 53.0) * 0.45
		root_pos = p2 + Vector3(0.0, -0.055 * settle, 0.02 * settle)
		root_rot = r2 + Vector3(-3.0 * settle, 0.0, 0.0)
		l_th = lead_th2 + Vector3(-4.0 * settle + buffet * 0.45, 0.0, 0.0)
		l_sh = lead_sh2 - 4.0 * settle - buffet * 0.6
		l_bt = lead_bt2 + Vector3(buffet * 0.8, 0.0, 0.0)
		t_th = trail_th2 + Vector3(-5.0 * settle - buffet * 0.4, 0.0, 0.0)
		t_sh = trail_sh2 - 5.0 * settle + buffet * 0.5
		t_bt = trail_bt2 - Vector3(buffet * 0.7, 0.0, 0.0)

	# Impact compression recoil buckles both knees back hard on contact.
	l_sh = clampf(l_sh + _knee_recoil.value.x, -128.0, -2.0)
	t_sh = clampf(t_sh + _knee_recoil.value.y, -128.0, -4.0)
	l_th.x += -_knee_recoil.value.x * 0.35
	t_th.x += -_knee_recoil.value.y * 0.35

	if s > 0.0:
		_set_pose(root_pos, root_rot, l_th, l_sh, l_bt, t_th, t_sh, t_bt)
	else:
		_set_pose(root_pos, root_rot, t_th, t_sh, t_bt, l_th, l_sh, l_bt)


func _snapshot_current() -> void:
	if _legs_root == null:
		return
	_snap_pos = _legs_root.position - _rest_root
	_snap_rot = _legs_root.rotation * (180.0 / PI)
	if _thigh_r:
		_snap_tr = _thigh_r.rotation * (180.0 / PI)
	if _shin_r:
		_snap_sr = rad_to_deg(_shin_r.rotation.x)
	if _boot_r:
		_snap_br = _boot_r.rotation * (180.0 / PI)
	if _thigh_l:
		_snap_tl = _thigh_l.rotation * (180.0 / PI)
	if _shin_l:
		_snap_sl = rad_to_deg(_shin_l.rotation.x)
	if _boot_l:
		_snap_bl = _boot_l.rotation * (180.0 / PI)


func _apply_retract_pose(u: float) -> void:
	var k: float = u * u * (3.0 - 2.0 * u)
	var end_pos: Vector3 = Vector3(0.0, -0.78, 0.28)
	var end_rot: Vector3 = Vector3(-24.0, 0.0, 0.0)
	var end_tr: Vector3 = Vector3(30.0, -4.0, 2.0)
	var end_tl: Vector3 = Vector3(28.0, 4.0, -2.0)
	_set_pose(
		_snap_pos.lerp(end_pos, k),
		_snap_rot.lerp(end_rot, k),
		_snap_tr.lerp(end_tr, k),
		lerpf(_snap_sr, -115.0, k),
		_snap_br.lerp(Vector3(10.0, 0.0, 0.0), k),
		_snap_tl.lerp(end_tl, k),
		lerpf(_snap_sl, -115.0, k),
		_snap_bl.lerp(Vector3(10.0, 0.0, 0.0), k),
	)


func _set_pose(root_pos: Vector3, root_rot_deg: Vector3,
		tr_deg: Vector3, sr_x_deg: float, br_deg: Vector3,
		tl_deg: Vector3, sl_x_deg: float, bl_deg: Vector3) -> void:
	if _legs_root == null:
		return
	_legs_root.position = _rest_root + root_pos
	_legs_root.rotation = root_rot_deg * (PI / 180.0)
	if _thigh_r:
		_thigh_r.rotation = tr_deg * (PI / 180.0)
	if _shin_r:
		_shin_r.rotation = Vector3(deg_to_rad(sr_x_deg), 0.0, 0.0)
	if _boot_r:
		_boot_r.rotation = br_deg * (PI / 180.0)
	if _thigh_l:
		_thigh_l.rotation = tl_deg * (PI / 180.0)
	if _shin_l:
		_shin_l.rotation = Vector3(deg_to_rad(sl_x_deg), 0.0, 0.0)
	if _boot_l:
		_boot_l.rotation = bl_deg * (PI / 180.0)


## Sweeps subtle translucent air-cut ribbons behind both boots during the rapid
## kick snap (fades cleanly once extended or retracting).
func _update_trails(delta: float) -> void:
	_im.clear_surfaces()
	if _sole_r == null or _heel_r == null or _sole_l == null or _heel_l == null:
		return
	var cam: Camera3D = player.camera() if player else null
	if cam == null or not cam.is_inside_tree():
		return
	# Age existing samples and drop expired ones.
	var span: float = maxf(cfg.trail_time, 0.01)
	var keep: int = 0
	for i: int in _hist_count:
		var age: float = _hist_age[i] + delta
		if age < span:
			_hist_r_a[keep] = _hist_r_a[i]
			_hist_r_b[keep] = _hist_r_b[i]
			_hist_l_a[keep] = _hist_l_a[i]
			_hist_l_b[keep] = _hist_l_b[i]
			_hist_age[keep] = age
			keep += 1
	_hist_count = keep
	# Emit new samples only during the active snap extension window.
	var snap_end: float = cfg.chamber_time + cfg.extend_time + 0.06
	if state == State.KICK and _t >= cfg.chamber_time * 0.6 and _t <= snap_end:
		if _hist_count >= TRAIL_POINTS:
			for i: int in TRAIL_POINTS - 1:
				_hist_r_a[i] = _hist_r_a[i + 1]
				_hist_r_b[i] = _hist_r_b[i + 1]
				_hist_l_a[i] = _hist_l_a[i + 1]
				_hist_l_b[i] = _hist_l_b[i + 1]
				_hist_age[i] = _hist_age[i + 1]
			_hist_count = TRAIL_POINTS - 1
		var inv_cam: Transform3D = cam.global_transform.affine_inverse()
		_hist_r_a[_hist_count] = inv_cam * _sole_r.global_position
		_hist_r_b[_hist_count] = inv_cam * _heel_r.global_position
		_hist_l_a[_hist_count] = inv_cam * _sole_l.global_position
		_hist_l_b[_hist_count] = inv_cam * _heel_l.global_position
		_hist_age[_hist_count] = 0.0
		_hist_count += 1
	if _hist_count < 2:
		return
	_draw_ribbon(_hist_r_a, _hist_r_b, span, 1.0)
	_draw_ribbon(_hist_l_a, _hist_l_b, span, 0.75)


func _draw_ribbon(pts_a: PackedVector3Array, pts_b: PackedVector3Array, span: float, strength: float) -> void:
	var col: Color = cfg.trail_color
	_im.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	for i: int in _hist_count:
		var fade: float = pow(clampf(1.0 - _hist_age[i] / span, 0.0, 1.0), 1.5)
		var c: Color = Color(col.r, col.g, col.b, col.a * fade * strength)
		var u: float = float(i) / maxf(float(_hist_count - 1), 1.0)
		_im.surface_set_color(c)
		_im.surface_set_uv(Vector2(u, 0.0))
		_im.surface_add_vertex(pts_b[i])
		_im.surface_set_color(c)
		_im.surface_set_uv(Vector2(u, 1.0))
		_im.surface_add_vertex(pts_a[i])
	_im.surface_end()
