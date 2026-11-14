class_name LorentzCatcher
extends ActivePart
## LC-6 Lorentz Catcher (LorentzCatcherData; owner, 2026-11-13; docs/design.md
## §3.4d). Eight coil petals on a drive ring at the left wrist.
##
## HOLD LB (with it selected): the gun goes down, the left arm comes up and
## the petals bloom forward round the open hand. While LB is held
## (CATCHING) a catch field sits in front of the operative
## (BulletCatcher): enemy rounds that fly into it from the front are
## braked to a stop by eddy currents and held, hot, in a slowly turning
## cloud in front of the palm. Rounds that reach the body from the front are
## caught too (Player.hit_interceptors). Each catch puts part of the round's
## energy into the body as heat.
##
## LET GO of LB, or run out of hold time, or overheat, and it throws them
## back (RELEASING): the hand punches forward and the same coils fire every
## round it caught, in a quick ripple, as a spread over a wide disc at the
## aim point. Some go for the bodies inside the disc (perception). Exactly
## as many go out as came in: an empty field just folds.
##
## Stats: power supply sets how many it can hold; the power reserve pays to
## throw them (short of it they go slower); cooling decides how much it can
## soak before it overheats and lets go; perception steers more of the
## spread onto bodies.

enum Mode { CATCHING, RELEASING }

const PETALS: int = 8

const SLUG_SHADER: String = """
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;
uniform vec4 hot : source_color = vec4(1.0, 0.5, 0.16, 1.0);
varying float v_heat;
void vertex() {
	v_heat = INSTANCE_CUSTOM.r;
}
void fragment() {
	// A copper jacket heated by the eddy currents: lit along its edges, the
	// nose (UV.y near 0) glowing hottest. Kept under ~1.4 so bloom doesn't
	// turn it into a white blob.
	float rim = pow(1.0 - abs(dot(NORMAL, VIEW)), 1.5);
	vec3 metal = vec3(0.5, 0.28, 0.14) * (0.45 + 0.75 * rim);
	float nose = smoothstep(0.55, 0.0, UV.y);
	vec3 glow = hot.rgb * (0.35 + 0.95 * v_heat) * (0.6 + 0.6 * nose);
	ALBEDO = metal * (1.0 - 0.6 * v_heat) + glow * (0.35 + 0.65 * v_heat);
}
"""

const HALO_SHADER: String = """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;
uniform vec4 hot : source_color = vec4(1.0, 0.5, 0.16, 1.0);
varying float v_heat;
void vertex() {
	v_heat = INSTANCE_CUSTOM.r;
}
void fragment() {
	float r = length(UV - 0.5) * 2.0;
	float a = pow(max(1.0 - r, 0.0), 3.0) * (0.05 + 0.25 * v_heat);
	ALBEDO = mix(hot.rgb, vec3(1.0, 0.8, 0.5), v_heat * v_heat * 0.4) * a;
}
"""

const FIELD_SHADER: String = """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;
uniform vec4 glow : source_color = vec4(0.48, 0.78, 1.0, 1.0);
uniform float amount = 0.0;
uniform float pulse = 0.0;
uniform vec2 pulse_at = vec2(0.5);
uniform float pulse_age = 9.0;
uniform float fill = 0.0;
void fragment() {
	vec2 d = UV - 0.5;
	float r = length(d) * 2.0;
	float ang = atan(d.y, d.x);
	// The field: a faint lens with eight lobes from the petals, fine bands
	// drifting inward near the edge, and a thin rim.
	float lobes = 0.5 + 0.5 * cos(ang * 8.0 - TIME * 1.3);
	float bands = 0.5 + 0.5 * sin(r * 46.0 + TIME * 7.0);
	float edge = smoothstep(0.55, 0.92, r) * smoothstep(1.0, 0.92, r);
	float body = smoothstep(1.0, 0.3, r) * 0.025 + edge * bands * 0.05 * (0.5 + 0.5 * lobes);
	float rim = smoothstep(0.9, 0.96, r) * smoothstep(1.0, 0.96, r) * (0.12 + 0.2 * lobes);
	// A ripple where the last round was caught.
	float pr = length(UV - pulse_at) * 2.0;
	float wave = pulse * smoothstep(0.05, 0.0, abs(pr - pulse_age * 2.6)) * exp(-pulse_age * 7.0);
	float core = smoothstep(0.4, 0.0, r) * fill * 0.08;
	ALBEDO = glow.rgb * (body + rim + wave * 0.9 + core) * amount;
}
"""


## One round in the field.
class Held:
	extends RefCounted
	var weapon: WeaponData
	## How fast it was going when it was caught (m/s).
	var speed: float = 0.0
	## Where it is now and where it started, in the camera's space.
	var local: Vector3
	var from: Vector3
	## Its nose (camera space): the way it was flying.
	var nose: Vector3 = Vector3.BACK
	var slot: int = 0
	var age: float = 0.0
	var heat: float = 1.0
	## Where it goes on the release (world), and when (real seconds into it).
	var target: Vector3
	var launch_at: float = 0.0
	var gone: bool = false


var cfg: LorentzCatcherData
var rig: ArmRig
var mode: Mode = Mode.CATCHING
var held: Array[Held] = []
## Rounds caught and thrown since the part was built (tests, HUD).
var caught_total: int = 0
var thrown_total: int = 0
## The last release: how many went out, the aim point and the disc radius (tests).
var last_volley: int = 0
var last_aim: Vector3 = Vector3.ZERO
var last_radius: float = 0.0
var last_power_scale: float = 1.0
## Why the last release happened: &"button", &"time", &"heat" (tests, HUD).
var release_reason: StringName = &""
## Rounds turned away because it was full, since it came up.
var refused: int = 0

var _catcher: BulletCatcher
var _glow: StandardMaterial3D
var _petals: Array[Node3D] = []
var _focus: Node3D
var _slug_mm: MultiMesh
var _slug_node: MultiMeshInstance3D
var _halo_mm: MultiMesh
var _halo_node: MultiMeshInstance3D
var _field: MeshInstance3D
var _field_mat: ShaderMaterial
var _slot_z: PackedFloat32Array = PackedFloat32Array()
var _spin: float = 0.0
var _rel_t: float = -1.0
var _volley: int = 0
var _flash: float = 0.0
var _pulse_age: float = 9.0
var _last_catch_ms: int = 0
var _last_full_ms: int = 0
var _script_hold: bool = false
var _hum: AudioStreamPlayer
var _layer: CanvasLayer
var _view: CatchView
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


## The HUD while it's up: what it holds, the heat, the hold time, and where
## the release would go (the disc at the aim point).
class CatchView:
	extends Control
	var part: LorentzCatcher
	var font: Font

	func _draw() -> void:
		var p: LorentzCatcher = part
		if p.player == null or not p.is_running():
			return
		var cam: Camera3D = p.player.camera()
		var vp: Vector2 = get_viewport_rect().size
		var mid: Vector2 = vp * 0.5
		var gc: Color = p.cfg.glow_color
		var a: float = clampf(p.blend, 0.0, 1.0)
		if p.mode == LorentzCatcher.Mode.CATCHING:
			# The release area: a dashed ring at the aim point, brighter on bodies.
			var aim: Array = p.aim_area()
			var at: Vector3 = aim[0]
			var r: float = aim[1]
			var fwd: Vector3 = -cam.global_basis.z
			var ax: Vector3 = cam.global_basis.x
			var ay: Vector3 = fwd.cross(ax).normalized()
			var pts: PackedVector2Array = PackedVector2Array()
			var ok: bool = true
			for k: int in 33:
				var ang: float = TAU * k / 32.0
				var w: Vector3 = at + (ax * cos(ang) + ay * sin(ang)) * r
				if cam.is_position_behind(w):
					ok = false
					break
				pts.append(cam.unproject_position(w))
			if ok:
				var bodies: int = p.bodies_in(at, r).size()
				var rc: Color = Color(1.0, 0.85, 0.6, 0.95 * a) if bodies > 0 else Color(gc, 0.75 * a)
				# A thin continuous ring with four ticks pointing in: not to be read as tracers.
				draw_polyline(pts, Color(0, 0, 0, 0.3 * a), 3.5, true)
				draw_polyline(pts, rc, 1.5, true)
				var c2: Vector2 = cam.unproject_position(at)
				for k: int in [0, 8, 16, 24]:
					var inward: Vector2 = (c2 - pts[k]).normalized()
					draw_line(pts[k], pts[k] + inward * 9.0, rc, 2.0, true)
				if bodies > 0:
					var low: Vector2 = pts[8]
					_text(Vector2(low.x - 60.0, low.y + 20.0), "%d IN AREA" % bodies, 120, 12, rc)
		# What it holds, the heat, the hold time.
		var cap: int = p.capacity()
		var n: int = p.held.size()
		var full: bool = n >= cap
		var col: Color = Color(1.0, 0.45, 0.25, a) if full else Color(gc, 0.95 * a)
		if p.mode == LorentzCatcher.Mode.RELEASING:
			_text(Vector2(0, vp.y - 98), "THROWING  %d" % p.last_volley, vp.x, 18, Color(1.0, 0.8, 0.55, a))
		else:
			_text(Vector2(0, vp.y - 98), ("FULL  %d / %d" if full else "CAUGHT  %d / %d") % [n, cap], vp.x, 18, col)
		if p.mode == LorentzCatcher.Mode.CATCHING:
			_text(Vector2(0, vp.y - 76), "LET GO OF LB TO THROW THEM BACK", vp.x, 12, Color(1, 1, 1, 0.8 * a))
		var w: float = 220.0 * clampf(p.charge_fraction(), 0.0, 1.0)
		draw_rect(Rect2(mid.x - 110.0, 58.0, 220.0, 3.0), Color(0, 0, 0, 0.4 * a))
		draw_rect(Rect2(mid.x - w * 0.5, 58.0, w, 3.0), Color(gc, a))
		if p.body:
			var h: float = clampf(p.body.heat_fraction(), 0.0, 1.0)
			var hc: Color = Color(1.0, 0.55 - 0.4 * h, 0.2, (0.5 + 0.5 * h) * a)
			draw_rect(Rect2(mid.x - 110.0, 66.0, 220.0, 2.0), Color(0, 0, 0, 0.35 * a))
			draw_rect(Rect2(mid.x - 110.0, 66.0, 220.0 * h, 2.0), hc)
			draw_string(font, Vector2(mid.x + 116.0, 71.0), "HEAT", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, hc)

	## Centred text with a dark drop shadow, readable on the bright range and the dark docks.
	func _text(at: Vector2, s: String, width: float, size: int, c: Color) -> void:
		draw_string(font, at + Vector2(1.0, 1.0), s, HORIZONTAL_ALIGNMENT_CENTER, width, size, Color(0, 0, 0, 0.6 * c.a))
		draw_string(font, at, s, HORIZONTAL_ALIGNMENT_CENTER, width, size, c)


func _ready() -> void:
	super._ready()
	cfg = data as LorentzCatcherData
	_rng.randomize()
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "CatcherRig")
	if player == null:
		add_child(rig)
	rig.raise_drop = 0.38
	_glow = rig.drive("glow")
	if _glow:
		_glow.emission = cfg.glow_color
		_glow.emission_energy_multiplier = cfg.glow_idle
	for k: int in PETALS:
		var n: Node3D = rig.part("petal_%d" % k)
		if n:
			_petals.append(n)
	_focus = rig.part("focus")
	_catcher = BulletCatcher.new()
	_catcher.owner = player
	_catcher.radius = cfg.field_radius
	_catcher.cos_arc = cos(deg_to_rad(cfg.arc_deg))
	_catcher.on_catch = _on_catch
	_build_cloud()
	_build_hud()
	_hum = AudioStreamPlayer.new()
	_hum.bus = &"SFX"
	_hum.volume_db = -10.0
	var loop: Array = Sfx.bank(&"lc6_loop")
	if not loop.is_empty():
		_hum.stream = loop[0]
	add_child(_hum)
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	_release_hooks()
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()
	for n: Node in [_slug_node, _halo_node, _field]:
		if is_instance_valid(n) and n.get_parent() != self:
			n.queue_free()


func hand() -> StringName:
	return &"left"


## Rounds it can hold: the coils keep as many in suspension as the supply feeds.
func capacity() -> int:
	var s: float = body.stat(&"power_supply_w") if body else cfg.power_ref_w
	return clampi(roundi(cfg.base_capacity * s / maxf(cfg.power_ref_w, 1.0)), cfg.min_capacity, cfg.max_capacity)


## Share of a release that goes for bodies inside the area.
func seek_share() -> float:
	var p: float = body.stat(&"perception") if body else 1.0
	return clampf(cfg.seek_per_perception * p, 0.0, cfg.seek_max)


## Hold time is spent only while catching.
func _drain(real: float) -> void:
	if state == State.ACTIVE and mode == Mode.CATCHING:
		charge = maxf(charge - data.drain_per_s * real, 0.0)
		if charge <= 0.0:
			_begin_release(&"time")


## Holds the field up without the button (tests, demos).
func script_hold(on: bool) -> void:
	_script_hold = on


func _holding() -> bool:
	if _script_hold:
		return true
	return can_input() and Input.is_action_pressed(Augments.USE)


## LB pressed: start. Pressed while catching (a scripted press; a held
## button can't be pressed again): throw.
func toggle() -> void:
	if is_running():
		if mode == Mode.CATCHING and state == State.ACTIVE:
			_begin_release(&"button")
		return
	super.toggle()


# ------------------------------------------------------------------ states

func _on_start() -> void:
	mode = Mode.CATCHING
	held.clear()
	refused = 0
	release_reason = &""
	_rel_t = -1.0
	_flash = 0.0
	rig.extra = Transform3D.IDENTITY
	rig.visible = true
	_slug_node.visible = true
	_halo_node.visible = true
	_field.visible = true
	if player:
		if not player.hit_interceptors.has(_intercept):
			player.hit_interceptors.append(_intercept)
		player.aug_move_scale = cfg.move_scale
	_update_catcher()
	Ballistics.add_catcher(_catcher)
	_layer.visible = true
	Sfx.play_ui(&"lc6_deploy", -3.0, 0.0)
	if _hum.stream:
		_hum.play()
	rumble(0.15, 0.3, 0.25)


func _on_stop() -> void:
	_release_hooks()
	_hum.stop()
	if mode == Mode.CATCHING:
		Sfx.play_ui(&"lc6_stow", -5.0, 0.0)


func _release_hooks() -> void:
	Ballistics.remove_catcher(_catcher)
	if player and is_instance_valid(player):
		player.hit_interceptors.erase(_intercept)
		player.aug_move_scale = 1.0
		if player.fov_punch_deg > 0.0:
			player.fov_punch_deg = 0.0


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_state_changed(s: State) -> void:
	if s == State.COOLDOWN:
		rig.visible = false
		_slug_node.visible = false
		_halo_node.visible = false
		_field.visible = false
		_layer.visible = false
		rig.extra = Transform3D.IDENTITY
		# Interrupted (death, loadout change) with rounds still in the field: they drop.
		held.clear()
		_release_hooks()


func _on_blend(a: float) -> void:
	rig.seek(a)


func _on_active(real: float) -> void:
	match mode:
		Mode.CATCHING:
			if not _holding():
				_begin_release(&"button")
		Mode.RELEASING:
			_release_frame(real)


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if not rig.visible:
		return
	rig.tick(real, blend, player)
	_flash = maxf(0.0, _flash - real * 4.0)
	_pulse_age += real
	_update_catcher()
	_update_cloud(real)
	_update_glow()
	if _view and _layer.visible:
		_view.queue_redraw()
	if player:
		player.fov_punch_deg = move_toward(player.fov_punch_deg, 0.0, player.fov_punch_deg * 6.0 * real + real)


# ------------------------------------------------------------------ catching

## The sphere follows the view: in front of the eye, a little low.
func _update_catcher() -> void:
	if player == null:
		return
	var cam: Camera3D = player.camera()
	var fwd: Vector3 = -cam.global_basis.z
	_catcher.facing = fwd
	_catcher.center = cam.global_position + fwd * cfg.field_ahead + Vector3.DOWN * cfg.field_drop
	_catcher.radius = cfg.field_radius
	_catcher.enabled = mode == Mode.CATCHING and (state == State.ACTIVE or (state == State.DEPLOYING and blend > 0.5))


## Ballistics: a round flew into the field. True = taken.
func _on_catch(weapon: WeaponData, point: Vector3, velocity: Vector3, _shooter: Node) -> bool:
	if not _catcher.enabled:
		return false
	return _take(weapon, point, velocity)


## Rounds that reach the body from the front (under the field): caught too.
func _intercept(hit: BallisticHit, amount: float) -> float:
	if not _catcher.enabled or player == null:
		return amount
	var fwd: Vector3 = -player.camera().global_basis.z
	if fwd.dot(-hit.direction) < _catcher.cos_arc:
		return amount
	if _take(hit.weapon, hit.point, hit.direction * hit.speed_in):
		return 0.0
	return amount


func _take(weapon: WeaponData, point: Vector3, velocity: Vector3) -> bool:
	if weapon == null:
		return false
	var now: int = Time.get_ticks_msec()
	if held.size() >= capacity():
		refused += 1
		if now - _last_full_ms > 400:
			_last_full_ms = now
			Sfx.play_ui(&"lc6_full", -8.0, 0.0)
		return false
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var h: Held = Held.new()
	h.weapon = weapon
	h.speed = velocity.length()
	h.slot = held.size()
	# It appears where it was caught on screen, at the cloud's depth, and drifts in.
	var into: Vector3 = (point - eye).normalized()
	var to_cam: Transform3D = cam.global_transform.affine_inverse()
	h.from = to_cam * (eye + into * cfg.cloud_depth)
	h.local = h.from
	h.nose = (to_cam.basis * velocity.normalized()).normalized()
	held.append(h)
	caught_total += 1
	# Eddy braking: the round's energy comes out as heat in the coils.
	var energy: float = 0.5 * weapon.bullet_mass_g * 0.001 * h.speed * h.speed
	if body:
		body.heat_j = minf(body.heat_j + energy * cfg.heat_share, body.frame.heat_capacity_j)
	_flash = minf(_flash + 0.5, 1.0)
	_pulse_age = 0.0
	var rel: Vector3 = h.from - _cloud_center()
	var uv: Vector2 = Vector2(0.5 + rel.x / 0.4, 0.5 - rel.y / 0.4)
	_field_mat.set_shader_parameter(&"pulse_at", uv)
	_field_mat.set_shader_parameter(&"pulse", 1.0)
	if now - _last_catch_ms > 35:
		_last_catch_ms = now
		Sfx.play_ui(&"lc6_catch", -6.0, 0.12)
		Fx._emit(&"sparks", eye + into * minf(cfg.cloud_depth + 0.4, eye.distance_to(point)), -velocity.normalized(), Color(0.7, 0.85, 1.0), 3, 0.6)
		rumble(cfg.rumble_catch.x, cfg.rumble_catch.y, cfg.rumble_catch.z)
	if body and body.overheated():
		# The coils can't shed any more: the field lets go of everything at once.
		_begin_release(&"heat")
	return true


# ------------------------------------------------------------------ the release

## Where the release goes: [aim point, disc radius (m)].
func aim_area() -> Array:
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var dist: float = cfg.aim_default
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, eye + fwd * cfg.aim_reach, Ballistics.BULLET_MASK, [player.get_rid()])
	var res: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
	if not res.is_empty():
		var hit: Vector3 = res["position"]
		dist = maxf(eye.distance_to(hit), 1.0)
	var r: float = clampf(cfg.spread_radius, dist * tan(deg_to_rad(cfg.spread_min_deg)), dist * tan(deg_to_rad(cfg.spread_max_deg)))
	return [eye + fwd * dist, r]


## Living enemies with a body part inside the disc round `at`.
func bodies_in(at: Vector3, radius: float) -> Array[Enemy]:
	var out: Array[Enemy] = []
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive:
			continue
		var c: HitboxPart = e.parts.get(&"chest")
		var p: Vector3 = c.global_position if c else e.global_position + Vector3.UP * 1.2
		if p.distance_to(at) <= radius * 1.25:
			out.append(e)
	return out


func _begin_release(reason: StringName) -> void:
	if mode != Mode.CATCHING or not is_running():
		return
	release_reason = reason
	_catcher.enabled = false
	Ballistics.remove_catcher(_catcher)
	if held.is_empty():
		# Nothing caught: nothing to throw. It just folds.
		last_volley = 0
		stop()
		return
	mode = Mode.RELEASING
	_rel_t = 0.0
	_volley = 0
	var area: Array = aim_area()
	last_aim = area[0]
	last_radius = area[1]
	last_volley = held.size()
	var cam: Camera3D = player.camera()
	var fwd: Vector3 = -cam.global_basis.z
	var ax: Vector3 = cam.global_basis.x
	var ay: Vector3 = fwd.cross(ax).normalized()
	var bodies: Array[Enemy] = bodies_in(last_aim, last_radius)
	var seek: float = seek_share()
	var zones: Array[StringName] = [&"head", &"chest", &"chest", &"stomach", &"stomach", &"pelvis", &"l_thigh", &"r_thigh", &"l_upper_arm", &"r_upper_arm"]
	var order: Array[int] = []
	for i: int in held.size():
		order.append(i)
	order.shuffle()
	for k: int in order.size():
		var h: Held = held[order[k]]
		h.launch_at = cfg.push_time + cfg.ripple * float(k) / maxf(order.size() - 1, 1)
		var target: Vector3 = Vector3.INF
		if not bodies.is_empty() and _rng.randf() < seek:
			var e: Enemy = bodies[_rng.randi() % bodies.size()]
			var hb: HitboxPart = e.parts.get(zones[_rng.randi() % zones.size()])
			if hb:
				target = hb.global_position + Vector3(_rng.randf_range(-0.08, 0.08), _rng.randf_range(-0.08, 0.08), _rng.randf_range(-0.08, 0.08))
		if not target.is_finite():
			# Even cover of the disc (√ for the radius), a little deeper or shallower.
			var ang: float = _rng.randf() * TAU
			var rr: float = last_radius * sqrt(_rng.randf())
			target = last_aim + (ax * cos(ang) + ay * sin(ang)) * rr + fwd * _rng.randf_range(-1.0, 1.0)
		h.target = target
	# The reserve pays to throw them; short of it they go slower.
	var need: float = 0.0
	for h: Held in held:
		var v: float = h.speed * cfg.return_speed
		need += 0.5 * h.weapon.bullet_mass_g * 0.001 * v * v * cfg.power_per_j
	last_power_scale = 1.0
	if body:
		var have: float = body.power_j
		if need > have:
			last_power_scale = maxf(sqrt(have / maxf(need, 1.0)), cfg.min_power_scale)
		body.power_j = maxf(have - need * last_power_scale * last_power_scale, 0.0)
	Sfx.play_ui(&"lc6_release", 0.0, 0.0)
	_hum.stop()


func _release_frame(real: float) -> void:
	_rel_t += real
	# The hand punches forward and comes back.
	var push: float = clampf(_rel_t / maxf(cfg.push_time, 0.01), 0.0, 1.0)
	var back: float = clampf((_rel_t - cfg.push_time - cfg.ripple) / maxf(cfg.after, 0.01), 0.0, 1.0)
	var out: float = (1.0 - pow(1.0 - push, 3.0)) * (1.0 - back * back * (3.0 - 2.0 * back))
	rig.extra = Transform3D(Basis.IDENTITY, Vector3(0.02 * out, 0.015 * out, -0.11 * out))
	var cam: Camera3D = player.camera()
	var fired_now: int = 0
	for h: Held in held:
		if h.gone or _rel_t < h.launch_at:
			continue
		h.gone = true
		_launch(h, cam)
		fired_now += 1
	if _rel_t >= cfg.push_time + cfg.ripple + cfg.after:
		held.clear()
		stop()


func _launch(h: Held, cam: Camera3D) -> void:
	var eye: Vector3 = cam.global_position
	var origin: Vector3 = cam.global_transform * h.local
	# Never from inside a wall: if the cloud is through one, from the eye.
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, origin, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
	if not space.intersect_ray(q).is_empty():
		origin = eye
	var dir: Vector3 = (h.target - origin).normalized()
	var v: float = h.speed * cfg.return_speed * last_power_scale
	var power: float = pow(v / maxf(h.weapon.muzzle_velocity, 1.0), 2.0)
	var first: bool = _volley == 0
	# Every round draws its own hot streak (Ballistics' glow rounds): no tracers needed.
	var id: int = Ballistics.fire(h.weapon, origin, dir, player, Vector3.INF, _volley, power, cfg.return_color)
	if first:
		_volley = id
		_on_first_launch(dir)
	thrown_total += 1
	if thrown_total % 3 == 0:
		Sfx.play_ui(&"lc6_zip", -10.0, 0.15)


func _on_first_launch(dir: Vector3) -> void:
	_flash = 1.0
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(Vector3(cfg.camera_kick_deg.x, cfg.camera_kick_deg.y * _rng.randf_range(-1.0, 1.0), cfg.camera_kick_deg.z * _rng.randf_range(-1.0, 1.0)))
	player.fov_punch_deg = cfg.fov_kick_deg
	rig.kick_rot.kick(Vector3(deg_to_rad(-4.0), 0.0, deg_to_rad(3.0)))
	rumble(cfg.rumble_release.x, cfg.rumble_release.y, cfg.rumble_release.z)
	EventBus.shot_fired.emit(player, player.camera().global_position, dir)
	var cam: Camera3D = player.camera()
	Fx._emit(&"sparks", cam.global_transform * _cloud_center(), dir, Color(0.75, 0.9, 1.0), 10, 1.4)


# ------------------------------------------------------------------ the cloud

func _build_cloud() -> void:
	var cap: int = cfg.max_capacity
	_slot_z.resize(cap)
	for i: int in cap:
		_slot_z[i] = _rng.randf_range(-0.05, 0.05)
	var slug: CapsuleMesh = CapsuleMesh.new()
	slug.radius = cfg.slug_width * 0.5
	slug.height = cfg.slug_length
	slug.radial_segments = 8
	slug.rings = 2
	var sm: ShaderMaterial = ShaderMaterial.new()
	sm.shader = Shader.new()
	sm.shader.code = SLUG_SHADER
	sm.set_shader_parameter(&"hot", cfg.hot_color)
	slug.material = sm
	_slug_mm = MultiMesh.new()
	_slug_mm.transform_format = MultiMesh.TRANSFORM_3D
	_slug_mm.use_custom_data = true
	_slug_mm.mesh = slug
	_slug_mm.instance_count = cap
	_slug_mm.visible_instance_count = 0
	_slug_node = MultiMeshInstance3D.new()
	_slug_node.name = "CatcherCloud"
	_slug_node.multimesh = _slug_mm
	_slug_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_slug_node.custom_aabb = AABB(Vector3(-2, -2, -3), Vector3(4, 4, 4))
	_slug_node.visible = false
	var halo: QuadMesh = QuadMesh.new()
	halo.size = Vector2(0.034, 0.034)
	var hm: ShaderMaterial = ShaderMaterial.new()
	hm.shader = Shader.new()
	hm.shader.code = HALO_SHADER
	hm.set_shader_parameter(&"hot", cfg.hot_color)
	halo.material = hm
	_halo_mm = MultiMesh.new()
	_halo_mm.transform_format = MultiMesh.TRANSFORM_3D
	_halo_mm.use_custom_data = true
	_halo_mm.mesh = halo
	_halo_mm.instance_count = cap
	_halo_mm.visible_instance_count = 0
	_halo_node = MultiMeshInstance3D.new()
	_halo_node.name = "CatcherHalos"
	_halo_node.multimesh = _halo_mm
	_halo_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_halo_node.custom_aabb = _slug_node.custom_aabb
	_halo_node.visible = false
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2(0.4, 0.4)
	_field_mat = ShaderMaterial.new()
	_field_mat.shader = Shader.new()
	_field_mat.shader.code = FIELD_SHADER
	_field_mat.set_shader_parameter(&"glow", cfg.glow_color)
	_field = MeshInstance3D.new()
	_field.name = "CatcherField"
	_field.mesh = quad
	_field.material_override = _field_mat
	_field.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_field.visible = false
	var parent: Node = player.camera() if player else self
	parent.add_child(_field)
	parent.add_child(_halo_node)
	parent.add_child(_slug_node)


## The middle of the cloud in camera space: in front of the hand.
func _cloud_center() -> Vector3:
	if _focus and player and _focus.is_inside_tree():
		var c: Vector3 = player.camera().global_transform.affine_inverse() * _focus.global_position
		# Keep it at the cloud's depth whatever the arm is doing.
		return c * (cfg.cloud_depth / maxf(-c.z, 0.2)) if c.z < -0.1 else Vector3(-0.08, -0.06, -cfg.cloud_depth)
	return Vector3(-0.08, -0.06, -cfg.cloud_depth)


func _slot(i: int, center: Vector3) -> Vector3:
	var cap: float = float(maxi(capacity(), 1))
	var r: float = cfg.cloud_radius * sqrt((float(i) + 0.5) / cap)
	var ang: float = float(i) * 2.39996 + _spin * (1.0 - 0.5 * r / maxf(cfg.cloud_radius, 0.01))
	return center + Vector3(cos(ang) * r, sin(ang) * r * 0.8, _slot_z[i % _slot_z.size()])


func _update_cloud(real: float) -> void:
	_spin += cfg.cloud_spin * real
	var center: Vector3 = _cloud_center()
	var n: int = 0
	var fill: float = float(held.size()) / float(maxi(capacity(), 1))
	for h: Held in held:
		if h.gone:
			continue
		h.age += real
		var k: float = clampf(h.age / maxf(cfg.settle_time, 0.01), 0.0, 1.0)
		k = 1.0 - pow(1.0 - k, 3.0)
		var slot: Vector3 = _slot(h.slot, center)
		var pos: Vector3 = h.from.lerp(slot, k)
		if mode == Mode.RELEASING:
			# Pulled in toward the palm and heated white just before they go.
			var pre: float = clampf((_rel_t + 0.12 - h.launch_at) / 0.12, 0.0, 1.0)
			pos = pos.lerp(center + (pos - center) * 0.4, pre * 0.6)
			h.heat = maxf(h.heat, pre)
		else:
			# Cooling in the field, with a slow shiver.
			h.heat = maxf(0.35, 1.0 - h.age * 0.25)
			pos += Vector3(sin(h.age * 7.0 + h.slot), cos(h.age * 6.0 + h.slot * 1.7), 0.0) * 0.0015
		h.local = pos
		# Nose: the way it was going (at you), settling into a slow tumble round
		# that so its length shows: a field of bullets, not of dots.
		var at_eye: Vector3 = -pos.normalized()
		var side: Vector3 = at_eye.cross(Vector3.UP).normalized().rotated(at_eye, float(h.slot) * 2.1 + h.age * 0.9)
		var tumble: Vector3 = at_eye.rotated(side, deg_to_rad(52.0 + 14.0 * sin(h.age * 1.3 + h.slot)))
		var nose: Vector3 = h.nose.slerp(tumble, k).normalized()
		if mode == Mode.RELEASING:
			# Turned to face down range just before they go.
			var out: Vector3 = Vector3.FORWARD
			nose = nose.slerp(out, clampf((_rel_t + 0.12 - h.launch_at) / 0.12, 0.0, 1.0)).normalized()
		var up: Vector3 = Vector3.UP if absf(nose.y) < 0.95 else Vector3.RIGHT
		var b: Basis = Basis.looking_at(nose, up) * Basis(Vector3.RIGHT, -PI * 0.5)
		_slug_mm.set_instance_transform(n, Transform3D(b, pos))
		_slug_mm.set_instance_custom_data(n, Color(h.heat, 0, 0, 0))
		_halo_mm.set_instance_transform(n, Transform3D(Basis.IDENTITY, pos + at_eye * 0.004))
		_halo_mm.set_instance_custom_data(n, Color(h.heat, 0, 0, 0))
		n += 1
	_slug_mm.visible_instance_count = n
	_halo_mm.visible_instance_count = n
	_field.position = center + Vector3(0.0, 0.0, -0.02)
	_field.basis = Basis.IDENTITY
	var on: float = blend if mode == Mode.CATCHING else maxf(0.0, 1.0 - _rel_t / maxf(cfg.push_time + cfg.ripple, 0.01))
	_field_mat.set_shader_parameter(&"amount", on * (0.9 + 0.6 * _flash))
	_field_mat.set_shader_parameter(&"pulse_age", _pulse_age)
	_field_mat.set_shader_parameter(&"fill", fill)


func _update_glow() -> void:
	if _glow == null:
		return
	var e: float = lerpf(cfg.glow_idle, cfg.glow_on, blend)
	e += cfg.glow_on * 0.8 * _flash
	if mode == Mode.RELEASING:
		e += cfg.glow_release * exp(-maxf(_rel_t - cfg.push_time, 0.0) * 6.0) * float(_rel_t >= cfg.push_time)
	var h: float = body.heat_fraction() if body else 0.0
	_glow.emission = cfg.glow_color.lerp(Color(1.0, 0.45, 0.2), clampf((h - 0.6) / 0.4, 0.0, 1.0))
	_glow.emission_energy_multiplier = e


func _build_hud() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = 4
	_layer.visible = false
	add_child(_layer)
	_view = CatchView.new()
	_view.part = self
	_view.font = ThemeDB.fallback_font
	_view.set_anchors_preset(Control.PRESET_FULL_RECT)
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(_view)
