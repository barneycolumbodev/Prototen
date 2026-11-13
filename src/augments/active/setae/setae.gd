class_name Setae
extends ActivePart
## SX-8 Urticating Setae (SetaeData; owner, 2026-11-13; docs/design.md
## §3.4c). The left arm's setae bank.
##
## LB (with it selected): the gun goes down and the left arm comes forward
## (the deploy clip: the hand spreads into a claw, the gill plates lift);
## two fibres grow out of each of the 24 ports, and the world slows to a
## crawl (dead-eye: desaturated, muffled, an amber vignette). While it's up
## (MARKING) LT marks the body part under the crosshair (or the nearest one
## to it); each mark lights a share of the fibres, which stiffen and lean
## toward the targets. RT throws (THROWING): the arm draws back and whips
## across, and at the release the fibres leave the ports as needles; time
## comes back over half a second. The needles fan out, turn onto their
## marks and home in. A bundle's first needles puncture (hits of their
## own); a moment later the cavity opens: one heavy hit per mark (the
## temporary cavity of a bundle of needles at 150 m/s) that kills most men
## and, at Maximum gore, pulps heads, tears limbs off and bursts torsos.
## Some needles go on through and stick in the wall behind.
##
## When the marking time runs out it throws at what is marked (or folds if
## nothing is). LB while marking folds it without throwing (the fibres are
## kept). One throw stored; the fibres regrow in about 12 s, faster with
## spare power.
##
## Stats: perception gives the fifth mark; processing stretches the
## marking time; usable strength sets how fast the needles fly and how
## much energy each cavity carries.

enum Mode { MARKING, THROWING, SPENT }

const PORTS: int = 24
const STUCK_MAX: int = 96
const STUCK_LIFE: float = 9.0
## Real seconds into the forward sweep when the fibres let go.
const RELEASE_AFTER: float = 0.03

const HAIR_SHADER: String = """
shader_type spatial;
render_mode cull_disabled;
uniform vec4 glow : source_color = vec4(1.0, 0.46, 0.14, 1.0);
varying float v_t;
varying float v_glow;
varying float v_phase;
void vertex() {
	float t = UV.y;
	v_t = t;
	v_glow = INSTANCE_CUSTOM.a;
	v_phase = INSTANCE_CUSTOM.b;
	float limp = 1.0 - v_glow;
	// Curl toward the hand (custom.g, metres at the tip) and a slow sway: fibres
	// still soft from the assembler. Lit ones are stiff.
	VERTEX.x += INSTANCE_CUSTOM.g * t * t + sin(TIME * 2.3 + v_phase + t * 3.0) * 0.011 * t * t * limp;
	VERTEX.z += sin(TIME * 1.7 + v_phase * 1.3 + t * 2.0) * 0.007 * t * t * limp;
}
void fragment() {
	float fres = pow(1.0 - abs(dot(NORMAL, VIEW)), 2.0);
	// Thin-film sheen: the hue drifts along the fibre and with the angle.
	vec3 film = 0.5 + 0.5 * cos(6.2831 * (v_t * 1.3 + fres * 0.6 + v_phase * 0.05 + vec3(0.0, 0.33, 0.67)));
	ALBEDO = vec3(0.03, 0.028, 0.027) + film * 0.06;
	METALLIC = 0.85;
	ROUGHNESS = 0.2;
	float run = smoothstep(0.86, 1.0, fract(v_t * 1.4 - TIME * 1.9 + v_phase));
	float lit = v_glow * (0.7 + 2.6 * v_t * v_t);
	EMISSION = glow.rgb * ((0.1 + 0.9 * run) * (1.0 - v_glow) + lit + smoothstep(0.9, 1.0, v_t) * 1.2);
}
"""

const STREAK_SHADER: String = """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;
uniform vec4 glow : source_color = vec4(1.0, 0.46, 0.14, 1.0);
varying float v_t;
varying float v_body;
void vertex() {
	v_t = UV.y;
	// custom.r: the share of the length that is the needle (the rest is its blur).
	v_body = INSTANCE_CUSTOM.r;
	// Never thinner than about two pixels on a 720p screen, however far away.
	float d = length((MODELVIEW_MATRIX * vec4(VERTEX, 1.0)).xyz);
	VERTEX.xz *= max(1.0, d * 0.55);
}
void fragment() {
	float body = smoothstep(1.0 - v_body - 0.03, 1.0 - v_body, v_t);
	float a = max(body, v_t * v_t * 0.55);
	ALBEDO = mix(glow.rgb, vec3(1.0, 0.85, 0.6), body * 0.45) * (0.9 + 2.0 * body);
	ALPHA = a;
}
"""

const OVERLAY_SHADER: String = """
shader_type canvas_item;
uniform vec4 tint : source_color = vec4(0.55, 0.12, 0.04, 0.5);
uniform float amount = 0.0;
void fragment() {
	vec2 d = UV - 0.5;
	d.x *= 1.7;
	float r = length(d);
	float edge = smoothstep(0.22, 0.9, r);
	float band = 0.06 * sin(UV.y * 620.0 + TIME * 30.0);
	COLOR = vec4(tint.rgb * (1.0 - edge * 0.85), clamp((0.10 + edge * 0.9 + band * edge) * tint.a * amount, 0.0, 0.85));
}
"""


## A marked body part. The point rides on the hitbox, so it follows the man.
class Mark:
	extends RefCounted
	var enemy: Enemy
	var part: HitboxPart
	var zone: StringName
	var local: Vector3
	var last: Vector3
	var landed: int = 0
	var hits: int = 0
	var cavity_at: float = -1.0
	var done: bool = false
	## Real seconds since it was placed (the HUD's lock-on flourish).
	var age: float = 0.0

	func point() -> Vector3:
		if part and is_instance_valid(part) and part.is_inside_tree():
			last = part.global_transform * local
		return last

	func label() -> String:
		var s: String = String(zone).replace("l_", "L ").replace("r_", "R ").replace("_", " ").to_upper()
		return "GUT" if s == "STOMACH" else s


class Needle:
	extends RefCounted
	var mark: Mark
	var start: Vector3
	var ctrl: Vector3
	var end: Vector3
	var t: float = 0.0
	var pos: Vector3
	var dir: Vector3
	var speed: float = 150.0
	var length: float = 0.25
	var streak: float = 0.0
	## Free flight: sticks where it ends (it hit a surface there).
	var sticks: bool = false
	var dead: bool = false


class MarkView:
	extends Control
	var part: Setae
	var font: Font

	func _draw() -> void:
		var p: Setae = part
		if p.player == null:
			return
		var cam: Camera3D = p.player.camera()
		var vp: Vector2 = get_viewport_rect().size
		var mid: Vector2 = vp * 0.5
		var mc: Color = p.cfg.mark_color
		var marking: bool = p.state == ActivePart.State.ACTIVE and p.mode == Setae.Mode.MARKING
		var fade: float = clampf(p.deadeye, 0.0, 1.0)
		if marking or p.state == ActivePart.State.DEPLOYING:
			# The reticle: a ring broken in four, ticks pointing in.
			var c: Color = Color(1.0, 0.9, 0.8, 0.85 * fade)
			for k: int in 4:
				var a0: float = k * PI * 0.5 + 0.35
				draw_arc(mid, 22.0, a0, a0 + PI * 0.5 - 0.7, 8, c, 1.5, true)
				var dirv: Vector2 = Vector2.from_angle(k * PI * 0.5 + PI * 0.25)
				draw_line(mid + dirv * 30.0, mid + dirv * 24.0, c, 1.5, true)
		# What LT would mark.
		var h: Setae.Mark = p.hover
		if marking and h and not cam.is_position_behind(h.point()):
			var hp: Vector2 = cam.unproject_position(h.point())
			var full: bool = p.marks.size() >= p.mark_limit()
			var hc: Color = Color(1, 1, 1, 0.9) if not full else Color(0.6, 0.6, 0.6, 0.6)
			var s: float = 16.0
			for corner: Vector2 in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]:
				var c0: Vector2 = hp + corner * s
				draw_line(c0, c0 - Vector2(corner.x * 7.0, 0), hc, 2.0)
				draw_line(c0, c0 - Vector2(0, corner.y * 7.0), hc, 2.0)
			draw_string(font, hp + Vector2(s + 6.0, -s + 10.0), h.label(), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, hc)
		# The marks: a diamond on each, numbered, joined in the order they were placed.
		var prev: Vector2 = Vector2.INF
		for i: int in p.marks.size():
			var m: Setae.Mark = p.marks[i]
			if m.done and m.landed > 0:
				continue
			var at: Vector3 = m.point()
			if cam.is_position_behind(at):
				prev = Vector2.INF
				continue
			var sp: Vector2 = cam.unproject_position(at)
			var grow: float = clampf(m.age / 0.18, 0.0, 1.0)
			var s2: float = lerpf(34.0, 11.0, grow)
			var alpha: float = 0.95 if m.landed == 0 else 0.5
			var col: Color = Color(mc, alpha * grow)
			var pts: PackedVector2Array = PackedVector2Array([sp + Vector2(0, -s2), sp + Vector2(s2, 0), sp + Vector2(0, s2), sp + Vector2(-s2, 0), sp + Vector2(0, -s2)])
			draw_polyline(pts, col, 2.5, true)
			draw_circle(sp, 2.5, col)
			draw_string(font, sp + Vector2(-4, -s2 - 6.0), str(i + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, col)
			if prev != Vector2.INF and marking:
				draw_dashed_line(prev, sp, Color(mc, 0.35), 1.0, 6.0)
			prev = sp
		if marking or p.state == ActivePart.State.DEPLOYING:
			var a: float = 0.9 * fade
			var limit: int = p.mark_limit()
			draw_string(font, Vector2(0, vp.y - 58), "MARKS  %d / %d" % [p.marks.size(), limit], HORIZONTAL_ALIGNMENT_CENTER, vp.x, 18, Color(mc, a))
			draw_string(font, Vector2(0, vp.y - 32), "LT  MARK      RT  THROW      LB  FOLD", HORIZONTAL_ALIGNMENT_CENTER, vp.x, 13, Color(1, 1, 1, 0.7 * a))
			# The marking time left: a bar that burns down from both ends.
			var w: float = 260.0 * clampf(p.window_left / maxf(p.window_seconds(), 0.01), 0.0, 1.0)
			draw_rect(Rect2(mid.x - 130.0, 58.0, 260.0, 3.0), Color(0, 0, 0, 0.4 * a))
			draw_rect(Rect2(mid.x - w * 0.5, 58.0, w, 3.0), Color(mc, a))


var cfg: SetaeData
var rig: ArmRig
var weapon: WeaponData
var mode: Mode = Mode.MARKING
var marks: Array[Mark] = []
## What LT would mark right now (null if nothing).
var hover: Mark
## Real seconds of marking left.
var window_left: float = 0.0
## 0..1: how far the dead-eye is in (time, colour, sound, vignette).
var deadeye: float = 0.0
var throws: int = 0
var cavities: int = 0
var needles: Array[Needle] = []
## Real seconds since the last release (-1 before it).
var released_for: float = -1.0

var _ports: Array[Node3D] = []
var _hair_port: PackedInt32Array = PackedInt32Array()
var _hair_dir: PackedVector3Array = PackedVector3Array()
var _hair_len: PackedFloat32Array = PackedFloat32Array()
var _hair_delay: PackedFloat32Array = PackedFloat32Array()
var _hair_phase: PackedFloat32Array = PackedFloat32Array()
var _hair_lock: PackedFloat32Array = PackedFloat32Array()
var _hair_order: PackedInt32Array = PackedInt32Array()
var _hair_mm: MultiMesh
var _hair_node: MultiMeshInstance3D
var _fly_mm: MultiMesh
var _fly_node: MultiMeshInstance3D
var _stuck_mm: MultiMesh
var _stuck_node: MultiMeshInstance3D
var _stuck: Array[Transform3D] = []
var _stuck_age: PackedFloat32Array = PackedFloat32Array()
var _stuck_next: int = 0
var _grown_for: float = -1.0
var _throw_t: float = -1.0
var _released: bool = false
var _ramp_t: float = -1.0
var _clock: float = 0.0
var _cavity_felt: bool = false
var _throw_from: Vector3
var _glow: StandardMaterial3D
var _layer: CanvasLayer
var _overlay: ColorRect
var _view: MarkView
var _env: Environment
var _base_saturation: float = 1.0
var _hum: AudioStreamPlayer
var _script_throw: bool = false
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	super._ready()
	cfg = data as SetaeData
	_rng.randomize()
	weapon = AugHit.weapon_named("SX-8 Urticating Setae")
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "SetaeRig")
	if player == null:
		add_child(rig)
	_glow = rig.drive("glow")
	if _glow:
		_glow.emission = cfg.glow_color
		_glow.emission_energy_multiplier = 0.3
	for k: int in PORTS:
		var n: Node3D = rig.part("port_%02d" % k)
		if n:
			_ports.append(n)
	_build_hairs()
	_build_needles()
	_build_hud()
	_hum = AudioStreamPlayer.new()
	_hum.bus = &"Master"
	_hum.volume_db = -12.0
	var loop: Array = Sfx.bank(&"sx8_loop")
	if not loop.is_empty():
		_hum.stream = loop[0]
	add_child(_hum)
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	if deadeye > 0.0 or _ramp_t >= 0.0:
		_apply_deadeye(0.0)
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()


func hand() -> StringName:
	return &"left"


func hud_pips() -> int:
	return roundi(charge_capacity())


func _drain(_real: float) -> void:
	pass


## Marks this body can hold: perception gives the extra one.
func mark_limit() -> int:
	var extra: int = 1 if body and body.stat(&"perception") >= cfg.perception_extra - 0.001 else 0
	return clampi(cfg.base_marks + extra, 1, cfg.max_marks)


## Real seconds of marking: processing stretches it.
func window_seconds() -> float:
	var p: float = body.stat(&"processing") if body else cfg.processing_ref
	return clampf(cfg.mark_window * p / maxf(cfg.processing_ref, 0.01), cfg.window_min, cfg.window_max)


## Usable strength against the reference, clamped: the throw's power.
func strength_scale() -> float:
	if body == null:
		return 1.0
	return clampf(body.usable_strength() / maxf(cfg.strength_ref, 0.01), cfg.min_strength_scale, cfg.max_strength_scale)


func needle_speed() -> float:
	return cfg.needle_speed * sqrt(strength_scale())


func cavity_energy() -> float:
	return cfg.cavity_energy_j * strength_scale()


func regen_scale() -> float:
	if body == null:
		return 1.0
	return clampf(body.headroom_w() / maxf(cfg.power_ref_w, 1.0), cfg.regrow_min_scale, cfg.regrow_max_scale)


## How many fibres have grown out (tests).
func hairs_grown() -> int:
	if _grown_for < 0.0:
		return 0
	var n: int = 0
	for i: int in _hair_len.size():
		if _grow(i) >= 0.99:
			n += 1
	return n


func needles_in_flight() -> int:
	return needles.size()


## Marks `zone` on `e` as if LT were pressed on it (tests, demos).
func script_mark(e: Enemy, zone: StringName = &"chest") -> bool:
	var hb: HitboxPart = e.parts.get(zone)
	if hb == null:
		return false
	return _add_mark(_make_mark(e, hb, hb.global_position))


## RT as if pressed (tests, demos).
func script_throw() -> void:
	_script_throw = true


# ------------------------------------------------------------------ states

## LB: start; while marking, fold without throwing. Not mid-throw.
func toggle() -> void:
	if is_running() and mode == Mode.THROWING:
		return
	super.toggle()


func _on_start() -> void:
	mode = Mode.MARKING
	marks.clear()
	hover = null
	_released = false
	_throw_t = -1.0
	_cavity_felt = false
	_grown_for = 0.0
	window_left = window_seconds()
	rig.extra = Transform3D.IDENTITY
	rig.visible = true
	_shuffle_hairs()
	_hair_node.visible = true
	_env = _find_environment()
	if _env and deadeye <= 0.0 and _ramp_t < 0.0:
		_base_saturation = _env.adjustment_saturation if _env.adjustment_enabled else 1.0
		_env.adjustment_enabled = true
	_ramp_t = -1.0
	_layer.visible = true
	Sfx.play_ui(&"sx8_deploy", -2.0, 0.0)
	if _hum.stream:
		_hum.play()
	rumble(0.15, 0.3, 0.4)


func _on_stop() -> void:
	_hum.stop()
	if not _released:
		marks.clear()
		hover = null
		Sfx.play_ui(&"sx8_stow", -5.0, 0.0)


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_state_changed(s: State) -> void:
	match s:
		State.ACTIVE:
			mode = Mode.MARKING
		State.COOLDOWN:
			rig.visible = false
			_hair_node.visible = false
			_grown_for = -1.0
			rig.extra = Transform3D.IDENTITY
			if _ramp_t < 0.0:
				_apply_deadeye(0.0)


func _on_blend(a: float) -> void:
	rig.seek(a)
	if _glow:
		_glow.emission_energy_multiplier = 0.3 + 3.5 * a
	# Thrown: the ramp brings time back, not the fold.
	if _ramp_t < 0.0 and not _released:
		_apply_deadeye(a * a * (3.0 - 2.0 * a))


func _on_active(real: float) -> void:
	match mode:
		Mode.MARKING:
			_mark_frame(real)
		Mode.THROWING:
			_throw_frame(real)


func _mark_frame(real: float) -> void:
	window_left -= real
	for m: Mark in marks:
		m.age += real
	# Something else (RX-9 folding) may have moved time: hold it here.
	if TimeControl.dilation_scale > cfg.world_scale + 0.001:
		_apply_deadeye(1.0)
	hover = _probe()
	var mark_pressed: bool = can_input() and Input.is_action_just_pressed(&"aim")
	var throw_pressed: bool = _script_throw or (can_input() and Input.is_action_just_pressed(&"fire"))
	_script_throw = false
	if mark_pressed:
		if hover and _add_mark(hover):
			hover = null
		else:
			Sfx.play_ui(&"sx8_denied", -8.0, 0.0)
	if throw_pressed:
		_begin_throw()
	elif window_left <= 0.0:
		if marks.is_empty():
			stop()
		else:
			_begin_throw()


func _add_mark(m: Mark) -> bool:
	if m == null or marks.size() >= mark_limit():
		return false
	marks.append(m)
	var p: AudioStreamPlayer = Sfx.play_ui(&"sx8_mark", -3.0, 0.0)
	if p:
		# Crisp in slow time: each mark a step higher.
		p.pitch_scale = 1.0 + 0.08 * (marks.size() - 1)
	rumble(0.25, 0.0, 0.06)
	rig.kick_pos.kick(Vector3(0.0, 0.004, 0.012))
	return true


## The body part under the crosshair, or the one nearest it within the snap cone.
func _probe() -> Mark:
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, eye + fwd * cfg.reach, Ballistics.LAYER_WORLD | Ballistics.LAYER_HITBOX)
	var res: Dictionary = space.intersect_ray(q)
	if not res.is_empty():
		var col: Object = res["collider"]
		var hb: HitboxPart = col as HitboxPart
		if hb:
			var tgt: Enemy = hb.target as Enemy
			if tgt and tgt.alive:
				var at_hit: Vector3 = res["position"]
				return _make_mark(tgt, hb, at_hit)
	var best: Mark = null
	var best_ang: float = INF
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive:
			continue
		for zone: StringName in [&"head", &"chest", &"stomach"]:
			var hb2: HitboxPart = e.parts.get(zone)
			if hb2 == null:
				continue
			var at: Vector3 = hb2.global_position
			var to: Vector3 = at - eye
			var d: float = to.length()
			if d > cfg.reach or d < 0.2:
				continue
			var ang: float = rad_to_deg(fwd.angle_to(to))
			if ang > cfg.snap_deg + 20.0 / maxf(d, 1.0) or ang >= best_ang:
				continue
			var los: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, at, Ballistics.LAYER_WORLD)
			if not space.intersect_ray(los).is_empty():
				continue
			best_ang = ang
			best = _make_mark(e, hb2, at)
	return best


func _make_mark(e: Enemy, hb: HitboxPart, at: Vector3) -> Mark:
	var m: Mark = Mark.new()
	m.enemy = e
	m.part = hb
	m.zone = hb.get_meta(&"zone", &"chest")
	m.local = hb.global_transform.affine_inverse() * at
	m.last = at
	return m


# ------------------------------------------------------------------ the throw

func _begin_throw() -> void:
	mode = Mode.THROWING
	_throw_t = 0.0
	hover = null
	Sfx.play_ui(&"sx8_windup", -2.0, 0.0)


func _throw_frame(real: float) -> void:
	_throw_t += real
	rig.extra = _throw_pose(_throw_t)
	if not _released and _throw_t >= cfg.windup + RELEASE_AFTER:
		_release()
	if _throw_t >= cfg.windup + cfg.follow:
		mode = Mode.SPENT
		stop()


## The arm about the shoulder (camera space): drawn back and in, whipped
## across to the right, through and down.
func _throw_pose(t: float) -> Transform3D:
	# time, yaw, pitch, roll (deg), offset x, y, z (m)
	var w: float = cfg.windup
	var keys: Array[PackedFloat32Array] = [
		PackedFloat32Array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
		PackedFloat32Array([w * 0.8, 17.0, 7.0, 18.0, -0.02, 0.025, 0.07]),
		PackedFloat32Array([w, 12.0, 4.0, 10.0, -0.01, 0.015, 0.03]),
		PackedFloat32Array([w + 0.07, -22.0, 2.0, -16.0, 0.03, 0.0, -0.12]),
		PackedFloat32Array([w + 0.17, -36.0, -3.0, -26.0, 0.06, -0.03, -0.1]),
		PackedFloat32Array([w + cfg.follow, -46.0, -22.0, -30.0, 0.08, -0.18, 0.0]),
	]
	var a: PackedFloat32Array = keys[0]
	var b: PackedFloat32Array = keys[keys.size() - 1]
	for i: int in keys.size() - 1:
		if t <= keys[i + 1][0]:
			a = keys[i]
			b = keys[i + 1]
			break
	var span: float = maxf(b[0] - a[0], 0.001)
	var k: float = clampf((t - a[0]) / span, 0.0, 1.0)
	k = k * k * (3.0 - 2.0 * k)
	var yaw: float = deg_to_rad(lerpf(a[1], b[1], k))
	var pitch: float = deg_to_rad(lerpf(a[2], b[2], k))
	var roll: float = deg_to_rad(lerpf(a[3], b[3], k))
	var off: Vector3 = Vector3(a[4], a[5], a[6]).lerp(Vector3(b[4], b[5], b[6]), k)
	var pivot: Vector3 = Vector3(-0.2, -0.32, 0.18)
	var rot: Transform3D = Transform3D(Basis.from_euler(Vector3(pitch, yaw, roll)), Vector3.ZERO)
	return Transform3D(Basis.IDENTITY, pivot + off) * rot * Transform3D(Basis.IDENTITY, -pivot)


## The fibres leave the arm: one needle per fibre, shared out over the marks.
func _release() -> void:
	_released = true
	released_for = 0.0
	throws += 1
	charge = maxf(charge - 1.0, 0.0)
	_since_stop = 0.0
	if body:
		body.heat_j = minf(body.heat_j + cfg.heat_j, body.frame.heat_capacity_j)
	var cam: Camera3D = player.camera()
	_throw_from = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	if marks.is_empty():
		var h: Mark = _probe()
		if h:
			marks.append(h)
	var free_end: Vector3 = _throw_from + fwd * cfg.reach
	var free_sticks: bool = false
	if marks.is_empty():
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(_throw_from, free_end, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
		var res: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
		if not res.is_empty():
			free_end = res["position"]
			free_sticks = true
	var to_world: Transform3D = rig.global_transform
	var speed: float = needle_speed()
	var right: Vector3 = cam.global_basis.x
	var up: Vector3 = cam.global_basis.y
	for k: int in _hair_order.size():
		var i: int = _hair_order[k]
		var root: Transform3D = to_world * _hair_xform(i)
		var n: Needle = Needle.new()
		n.length = _hair_len[i]
		n.dir = root.basis.y.normalized()
		n.pos = root.origin + root.basis.y
		n.start = n.pos
		n.speed = speed * _rng.randf_range(0.9, 1.1)
		var goal: Vector3
		if marks.is_empty():
			n.end = free_end + Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(-0.3, 0.3), _rng.randf_range(-0.3, 0.3))
			n.sticks = free_sticks
			goal = n.end
		else:
			n.mark = marks[k % marks.size()]
			goal = n.mark.point()
		var dist: float = n.start.distance_to(goal)
		# Fan out from the sweep (out to the right of it), then turn onto the mark.
		var spread: Vector3 = right * _rng.randf_range(-0.6, 1.0) + up * _rng.randf_range(-0.5, 0.8)
		n.ctrl = n.start + fwd * dist * 0.35 + spread * dist * cfg.fan
		needles.append(n)
	_hair_node.visible = false
	_fly_node.visible = true
	_ramp_t = 0.0
	Sfx.play_ui(&"sx8_throw", 0.0, 0.03)
	_flash(to_world.origin)
	rumble(cfg.rumble_throw.x, cfg.rumble_throw.y, cfg.rumble_throw.z)
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(cfg.camera_kick_deg)
	EventBus.shot_fired.emit(player, _throw_from, fwd)


func _fly(dt: float) -> void:
	for n: Needle in needles:
		var goal: Vector3 = n.mark.point() if n.mark else n.end
		var length: float = n.start.distance_to(n.ctrl) + n.ctrl.distance_to(goal)
		n.t = minf(n.t + n.speed * dt / maxf(length, 0.01), 1.0)
		var t: float = n.t
		var p: Vector3 = n.start.lerp(n.ctrl, t).lerp(n.ctrl.lerp(goal, t), t)
		var step: Vector3 = p - n.pos
		if step.length_squared() > 1e-8:
			n.dir = step.normalized()
		n.streak = clampf(step.length() * 1.6, 0.0, 2.5)
		n.pos = p
		if n.t >= 1.0:
			_arrive(n)
	var live: Array[Needle] = []
	for n: Needle in needles:
		if not n.dead:
			live.append(n)
	needles = live


func _arrive(n: Needle) -> void:
	var m: Mark = n.mark
	if m == null:
		n.dead = true
		if n.sticks:
			_stick(n.pos, n.dir)
		return
	m.landed += 1
	var at: Vector3 = n.pos
	var hb: HitboxPart = _live_part(m)
	if m.landed == 1:
		m.cavity_at = _clock + cfg.cavity_delay
		Sfx.play_at(&"sx8_hit", at, 0.0, 0.08)
	if hb and m.hits < cfg.hits_per_mark:
		m.hits += 1
		AugHit.strike(hb, weapon, player, at, n.dir, cfg.needle_damage, 1.0, cfg.needle_energy_j, DamageInfo.Type.BALLISTIC, true)
	# Some go on through and stick in whatever is behind.
	if _rng.randf() < 0.45:
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(at + n.dir * 0.25, at + n.dir * 9.0, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
		var res: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
		if not res.is_empty():
			n.mark = null
			n.start = at
			n.end = res["position"]
			n.ctrl = at.lerp(n.end, 0.5)
			n.t = 0.0
			n.sticks = true
			return
	n.dead = true


## The marked hitbox, or (if that piece is gone) the chest; null if there's nothing left to hit.
func _live_part(m: Mark) -> HitboxPart:
	if m.part and is_instance_valid(m.part) and m.part.is_inside_tree():
		return m.part
	if m.enemy and is_instance_valid(m.enemy):
		var c: HitboxPart = m.enemy.parts.get(&"chest")
		if c and is_instance_valid(c):
			return c
	return null


## The cavity: the bundle's energy dumped into the tissue at once.
func _cavitate(m: Mark) -> void:
	m.done = true
	cavities += 1
	var at: Vector3 = m.point()
	var dir: Vector3 = (at - _throw_from).normalized()
	var hb: HitboxPart = _live_part(m)
	if hb and m.enemy and is_instance_valid(m.enemy) and not m.enemy.body.gibbed:
		AugHit.strike(hb, weapon, player, at, dir, cfg.cavity_damage, cfg.cavity_impulse, cavity_energy(), DamageInfo.Type.BALLISTIC, true)
	# The cavity bursts out of the wound in every direction, most of it out of the back.
	Gore.mist(at, dir, 3.5)
	Gore.mist(at, -dir, 2.2)
	Gore.spray(at, (dir + Vector3.UP * 0.25).normalized(), 1.7, 20)
	Gore.spray(at, (-dir + Vector3.UP * 0.4).normalized(), 1.0, 8)
	Sfx.play_at(&"sx8_cavity", at, 0.0, 0.08)
	if not _cavity_felt:
		_cavity_felt = true
		TimeControl.hitstop(0.05, 0.2)
		rumble(cfg.rumble_cavity.x, cfg.rumble_cavity.y, cfg.rumble_cavity.z)


## The fibres harden as they leave: a short amber flash off the arm.
func _flash(at: Vector3) -> void:
	if not Fx.enabled:
		return
	var l: OmniLight3D = OmniLight3D.new()
	l.light_color = cfg.glow_color
	l.light_energy = 5.0
	l.omni_range = 4.0
	l.shadow_enabled = false
	world().add_child(l)
	l.global_position = at
	var tw: Tween = l.create_tween()
	tw.set_ignore_time_scale(true)
	tw.tween_property(l, ^"light_energy", 0.0, 0.16)
	tw.tween_callback(l.queue_free)


func _stick(at: Vector3, dir: Vector3) -> void:
	var size: float = 0.12 + _rng.randf() * 0.08
	# Driven in at a slight angle; what shows sticks out back toward the throw.
	var y: Vector3 = (-dir + Vector3(_rng.randf_range(-0.08, 0.08), _rng.randf_range(-0.08, 0.08), _rng.randf_range(-0.08, 0.08))).normalized()
	var x: Vector3 = y.cross(Vector3.UP if absf(y.y) < 0.95 else Vector3.RIGHT).normalized()
	var xf: Transform3D = Transform3D(Basis(x, y * size, x.cross(y)), at - y * 0.02)
	if _stuck.size() < STUCK_MAX:
		_stuck.append(xf)
		_stuck_age.append(0.0)
	else:
		_stuck[_stuck_next] = xf
		_stuck_age[_stuck_next] = 0.0
		_stuck_next = (_stuck_next + 1) % STUCK_MAX


# ------------------------------------------------------------------ per frame

func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	_clock += delta
	if released_for >= 0.0:
		released_for += real
	if rig.visible:
		rig.tick(real, blend, player)
		_draw_hairs(real)
	if not needles.is_empty():
		_fly(delta)
	for m: Mark in marks:
		if not m.done and m.cavity_at >= 0.0 and _clock >= m.cavity_at:
			_cavitate(m)
	if _ramp_t >= 0.0:
		_ramp_t += real
		var k: float = clampf(_ramp_t / maxf(cfg.time_ramp, 0.01), 0.0, 1.0)
		k = k * k * (3.0 - 2.0 * k)
		_apply_deadeye(1.0 - k)
		if k >= 1.0:
			_ramp_t = -1.0
	_draw_needles(delta)
	if _layer.visible:
		_view.queue_redraw()
		if not is_running() and _ramp_t < 0.0 and needles.is_empty() and _pending_cavities() == 0:
			_layer.visible = false
			marks.clear()


func _pending_cavities() -> int:
	var n: int = 0
	for m: Mark in marks:
		if not m.done:
			n += 1
	return n


## Dead-eye at strength `e` (0..1) on top of whatever RX-9 is doing.
func _apply_deadeye(e: float) -> void:
	deadeye = e
	var tw: float = 1.0
	var tp: float = 1.0
	var td: TimeDilation = _rx9()
	if td:
		var b: float = td.blend * td.blend * (3.0 - 2.0 * td.blend)
		tw = lerpf(1.0, td.cfg.world_scale, b)
		tp = lerpf(1.0, td.player_scale_now(), b)
	TimeControl.set_dilation(lerpf(tw, cfg.world_scale, e), lerpf(tp, cfg.player_scale, e))
	if _env:
		_env.adjustment_saturation = lerpf(_base_saturation, _base_saturation * cfg.saturation, e)
	(_overlay.material as ShaderMaterial).set_shader_parameter(&"amount", e)
	_overlay.visible = e > 0.001
	Sfx.set_muffle(e, cfg.lowpass_hz)
	if player:
		player.fov_add_deg = cfg.fov_kick_deg * e
	_hum.volume_db = linear_to_db(maxf(e, 0.001)) - 12.0
	if e <= 0.001 and td:
		# Hand time, colour and sound back to RX-9.
		td._on_blend(td.blend)


func _rx9() -> TimeDilation:
	if player == null or player.augments == null:
		return null
	for p: ActivePart in player.augments.parts.values():
		var td: TimeDilation = p as TimeDilation
		if td and td.is_running():
			return td
	return null


# ------------------------------------------------------------------ fibres

func _build_hairs() -> void:
	_hair_port.clear()
	for p: int in _ports.size():
		var pos: Vector3 = _in_rig(_ports[p]).origin
		# Bristling up in a crest along the arm rather than splaying out round it.
		var nrm: Vector3 = (Vector3(0.0, pos.y, pos.z).normalized() + Vector3.UP * 0.8).normalized()
		var along: Vector3 = Vector3.RIGHT
		var side: Vector3 = nrm.cross(along).normalized()
		var lean: float = deg_to_rad(cfg.lean_deg)
		for j: int in cfg.per_port:
			var s: float = -1.0 if j % 2 == 0 else 1.0
			var dir: Vector3 = (nrm * cos(lean) + along * sin(lean) + side * s * 0.16
					+ Vector3(_rng.randf_range(-0.06, 0.06), _rng.randf_range(-0.06, 0.06), _rng.randf_range(-0.06, 0.06))).normalized()
			_hair_port.append(p)
			_hair_dir.append(dir)
			_hair_len.append(cfg.hair_length * _rng.randf_range(1.0 - cfg.length_jitter, 1.0 + cfg.length_jitter * 0.5))
			# They come out from the elbow end first, a ripple toward the hand.
			var x01: float = clampf(inverse_lerp(-0.25, -0.05, pos.x), 0.0, 1.0)
			_hair_delay.append(0.12 + cfg.grow_stagger * (0.6 * x01 + 0.4 * _rng.randf()))
			_hair_phase.append(_rng.randf() * TAU)
			_hair_lock.append(0.0)
	_hair_mm = MultiMesh.new()
	_hair_mm.transform_format = MultiMesh.TRANSFORM_3D
	_hair_mm.use_custom_data = true
	_hair_mm.mesh = _strip_mesh(cfg.hair_width, false)
	_hair_mm.instance_count = _hair_len.size()
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = HAIR_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"glow", cfg.glow_color)
	_hair_node = MultiMeshInstance3D.new()
	_hair_node.name = "Setae"
	_hair_node.multimesh = _hair_mm
	_hair_node.material_override = mat
	_hair_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_hair_node.custom_aabb = AABB(Vector3(-2, -2, -2), Vector3(4, 4, 4))
	_hair_node.visible = false
	rig.add_child(_hair_node)
	_shuffle_hairs()


func _shuffle_hairs() -> void:
	_hair_order.clear()
	var idx: Array[int] = []
	for i: int in _hair_len.size():
		idx.append(i)
		_hair_lock[i] = 0.0
	idx.shuffle()
	for i: int in idx:
		_hair_order.append(i)


## A port's transform in the rig's space (works before the rig is in the tree).
func _in_rig(n: Node3D) -> Transform3D:
	var t: Transform3D = Transform3D.IDENTITY
	var cur: Node3D = n
	while cur and cur != rig:
		t = cur.transform * t
		cur = cur.get_parent() as Node3D
	return t


func _grow(i: int) -> float:
	var g: float = clampf((_grown_for - _hair_delay[i]) / maxf(cfg.grow_time, 0.01), 0.0, 1.0)
	return 1.0 - pow(1.0 - g, 3.0)


## Fibre `i` in rig space: origin at its port, Y along it (its length), X the way it curls.
func _hair_xform(i: int) -> Transform3D:
	var port: Transform3D = _in_rig(_ports[_hair_port[i]])
	var dir: Vector3 = _hair_dir[i]
	var lock: float = _hair_lock[i]
	if lock > 0.0:
		# Locked fibres lean out toward the marks (ahead of the camera).
		var ahead: Vector3 = (rig.transform.basis.inverse() * Vector3.FORWARD).normalized()
		dir = dir.lerp((dir + ahead * 1.4).normalized(), lock * 0.6).normalized()
	if _throw_t >= 0.0 and not _released:
		# Drawn back with the windup: they trail toward the elbow.
		dir = (dir - Vector3.RIGHT * 0.25 * clampf(_throw_t / cfg.windup, 0.0, 1.0)).normalized()
	var x: Vector3 = (Vector3.RIGHT - dir * dir.dot(Vector3.RIGHT)).normalized()
	var g: float = maxf(_grow(i), 0.002)
	var length: float = _hair_len[i] * g * (1.0 + 0.1 * lock)
	return Transform3D(Basis(x, dir * length, x.cross(dir)), port.origin)


func _draw_hairs(real: float) -> void:
	if _grown_for < 0.0 or _released:
		return
	_grown_for += real
	var locked: int = 0
	if not marks.is_empty():
		locked = roundi(float(_hair_order.size()) * marks.size() / maxf(mark_limit(), 1.0))
	var windup: float = clampf(_throw_t / cfg.windup, 0.0, 1.0) if _throw_t >= 0.0 else 0.0
	for k: int in _hair_order.size():
		var i: int = _hair_order[k]
		var want: float = 1.0 if k < locked or windup > 0.0 else 0.0
		_hair_lock[i] = move_toward(_hair_lock[i], want, real * 6.0)
		_hair_mm.set_instance_transform(i, _hair_xform(i))
		var lock: float = maxf(_hair_lock[i], windup)
		var curl: float = lerpf(0.05, 0.004, lock) - 0.05 * windup
		_hair_mm.set_instance_custom_data(i, Color(_grow(i), curl, _hair_phase[i], lock))


# ------------------------------------------------------------------ needles

func _build_needles() -> void:
	_fly_mm = MultiMesh.new()
	_fly_mm.transform_format = MultiMesh.TRANSFORM_3D
	_fly_mm.use_custom_data = true
	_fly_mm.mesh = _strip_mesh(cfg.hair_width * 1.6, true)
	_fly_mm.instance_count = PORTS * cfg.per_port
	_fly_mm.visible_instance_count = 0
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = STREAK_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"glow", cfg.glow_color)
	_fly_node = MultiMeshInstance3D.new()
	_fly_node.name = "Needles"
	_fly_node.top_level = true
	_fly_node.multimesh = _fly_mm
	_fly_node.material_override = mat
	_fly_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_fly_node.custom_aabb = AABB(Vector3(-500, -500, -500), Vector3(1000, 1000, 1000))
	add_child(_fly_node)
	_stuck_mm = MultiMesh.new()
	_stuck_mm.transform_format = MultiMesh.TRANSFORM_3D
	_stuck_mm.use_custom_data = true
	_stuck_mm.mesh = _strip_mesh(cfg.hair_width * 1.2, false)
	_stuck_mm.instance_count = STUCK_MAX
	_stuck_mm.visible_instance_count = 0
	_stuck_node = MultiMeshInstance3D.new()
	_stuck_node.name = "StuckNeedles"
	_stuck_node.top_level = true
	_stuck_node.multimesh = _stuck_mm
	_stuck_node.material_override = _hair_node.material_override
	_stuck_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_stuck_node.custom_aabb = AABB(Vector3(-500, -500, -500), Vector3(1000, 1000, 1000))
	add_child(_stuck_node)


func _draw_needles(dt: float) -> void:
	var n: int = mini(needles.size(), _fly_mm.instance_count)
	_fly_mm.visible_instance_count = n
	for k: int in n:
		var nd: Needle = needles[k]
		var total: float = nd.length + nd.streak
		var y: Vector3 = nd.dir
		var x: Vector3 = y.cross(Vector3.UP if absf(y.y) < 0.95 else Vector3.RIGHT).normalized()
		_fly_mm.set_instance_transform(k, Transform3D(Basis(x, y * total, x.cross(y)), nd.pos - y * total))
		_fly_mm.set_instance_custom_data(k, Color(nd.length / maxf(total, 0.001), 0.0, 0.0, 1.0))
	_fly_node.visible = n > 0
	var s: int = _stuck.size()
	_stuck_mm.visible_instance_count = s
	for k: int in s:
		_stuck_age[k] += dt
		var age: float = _stuck_age[k]
		var xf: Transform3D = _stuck[k]
		if age > STUCK_LIFE:
			xf = Transform3D(Basis().scaled(Vector3.ONE * 0.0001), xf.origin)
		_stuck_mm.set_instance_transform(k, xf)
		# Glowing hot when they land, cooling to dull fibre.
		_stuck_mm.set_instance_custom_data(k, Color(1.0, 0.0, float(k), clampf(1.0 - age / 2.5, 0.0, 1.0) * 0.8))
	_stuck_node.visible = s > 0


## Two crossed strips along +Y from 0 to 1, `width` across (m). `streak`:
## thin at the tail, full near the tip, a point at the tip (flying needles);
## otherwise full at the root tapering to the tip (fibres).
static func _strip_mesh(width: float, streak: bool) -> ArrayMesh:
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var seg: int = 8
	for plane: int in 2:
		var ax: Vector3 = Vector3.RIGHT if plane == 0 else Vector3.BACK
		var nrm: Vector3 = Vector3.BACK if plane == 0 else Vector3.RIGHT
		for i: int in seg:
			var t0: float = float(i) / seg
			var t1: float = float(i + 1) / seg
			var w0: float = width * 0.5 * _profile(t0, streak)
			var w1: float = width * 0.5 * _profile(t1, streak)
			var a: Vector3 = -ax * w0 + Vector3.UP * t0
			var b: Vector3 = ax * w0 + Vector3.UP * t0
			var c: Vector3 = ax * w1 + Vector3.UP * t1
			var d: Vector3 = -ax * w1 + Vector3.UP * t1
			var pts: PackedVector3Array = PackedVector3Array([a, b, c, a, c, d])
			var uvs: PackedVector2Array = PackedVector2Array([Vector2(0, t0), Vector2(1, t0), Vector2(1, t1), Vector2(0, t0), Vector2(1, t1), Vector2(0, t1)])
			for v: int in 6:
				st.set_normal(nrm)
				st.set_uv(uvs[v])
				st.add_vertex(pts[v])
	return st.commit()


static func _profile(t: float, streak: bool) -> float:
	if streak:
		return lerpf(0.15, 1.0, clampf(t / 0.85, 0.0, 1.0)) * (1.0 if t < 0.9 else (1.0 - t) / 0.1)
	return 1.0 - 0.9 * t


# ------------------------------------------------------------------ HUD

func _build_hud() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = 4
	_layer.visible = false
	add_child(_layer)
	_overlay = ColorRect.new()
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = OVERLAY_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"tint", cfg.tint)
	_overlay.material = mat
	_overlay.visible = false
	_layer.add_child(_overlay)
	_view = MarkView.new()
	_view.part = self
	_view.font = ThemeDB.fallback_font
	_view.set_anchors_preset(Control.PRESET_FULL_RECT)
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(_view)


func _find_environment() -> Environment:
	var vp: Viewport = get_viewport()
	if vp and vp.world_3d and vp.world_3d.environment:
		return vp.world_3d.environment
	var scene: Node = get_tree().current_scene
	if scene:
		for n: Node in scene.find_children("*", "WorldEnvironment", true, false):
			var we: WorldEnvironment = n as WorldEnvironment
			if we and we.environment:
				return we.environment
	return null
