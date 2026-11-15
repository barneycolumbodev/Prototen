class_name BossExecution
extends Node
## The execution (docs/design.md §8.7b; owner, 2026-11-15): the boss is down
## on one knee; walk up to him and RB ("execute") finishes him in first person.
##
## The operative steps in and takes his collar in the left hand, pulls him
## up, and the right fist goes into his face: three hard punches (his head
## snaps back, blood comes off with each, some of it onto the view), then a
## slower last one that takes the head apart in a beat of slow motion. The
## body goes over backwards. The operative lets go, lifts the fist and looks
## at it, blood running off the knuckles, shakes it off with three flicks and
## lowers it; the gun comes back up.
##
## Driven in real seconds (slow motion doesn't slow it); every time and
## distance is in the boss's BossConfig (Execution group). The hands are
## assets/characters/fp_execution/execution_hands.gltf (fist_r, grip_l), in
## the GS-2 suit's colours, moved in camera space; the operative can't be
## hurt while it plays.

signal finished

const HANDS: PackedScene = preload("res://assets/characters/fp_execution/execution_hands.gltf")
## Knuckles in the fist's space (the model's `knuckles` empty), and how far
## the wrist is behind them.
const KNUCKLES: Vector3 = Vector3(0.106, 0.004, 0.0)
## Where the knuckles wait between punches, and where they draw back to (camera space).
const FIST_REST: Vector3 = Vector3(0.17, -0.2, -0.42)
const FIST_COCK: Vector3 = Vector3(0.27, -0.17, -0.22)
const FIST_LOW: Vector3 = Vector3(0.3, -0.62, -0.3)
## The knuckles held up in front of the face for a look, and where the flicks start.
const FIST_LOOK: Vector3 = Vector3(0.03, -0.035, -0.36)
const FIST_SHAKE: Vector3 = Vector3(0.1, -0.12, -0.4)
## The shoulders (camera space): each forearm points from its shoulder to its hand.
const SHOULDER_R: Vector3 = Vector3(0.24, -0.5, 0.1)
const SHOULDER_L: Vector3 = Vector3(-0.24, -0.5, 0.1)
## The forearm's line while the fist is looked at: up, and tipped toward the eye.
const EXAMINE_AXIS: Vector3 = Vector3(-0.25, 0.85, 0.45)
## The left hand comes from here to his collar, and goes back.
const GRIP_FROM: Vector3 = Vector3(-0.32, -0.62, -0.25)
## Wet blood over the fist, building from the knuckles back toward the wrist.
const BLOOD_SHADER: String = """
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, shadows_disabled;
uniform float coat : hint_range(0.0, 1.0) = 0.0;
uniform float fresh : hint_range(0.0, 1.0) = 1.0;
uniform vec3 knuckles = vec3(0.0);
uniform vec3 along = vec3(1.0, 0.0, 0.0);
varying vec3 v_world;
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
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
	// Distance back from the striking face, in metres: the knuckles first, then
	// runs and smears back over the hand and the wrist as the coat builds.
	float back = dot(knuckles - v_world, along);
	float side = length((knuckles - v_world) - along * back);
	float n = noise(v_world * 70.0) * 0.6 + noise(v_world * 230.0) * 0.4;
	float reach = coat * 0.085 - max(back, 0.0) - side * 0.35 + (n - 0.5) * 0.06;
	float m = smoothstep(0.0, 0.015, reach);
	if (m < 0.01) {
		discard;
	}
	vec3 dried = vec3(0.09, 0.008, 0.006);
	vec3 wet = vec3(0.26, 0.008, 0.006);
	float w = clamp(fresh * 1.1 - n * 0.45, 0.0, 1.0);
	// Thinner at the edges of the coat: the suit shows through as a stain.
	ALBEDO = mix(dried, wet, w) * (0.7 + 0.5 * n);
	ROUGHNESS = mix(0.55, 0.06, w);
	SPECULAR = 0.8;
	ALPHA = m * mix(0.7, 0.97, smoothstep(0.0, 0.03, reach));
}
"""

var boss: Enemy
var cfg: BossConfig
var player: Player
var running: bool = false
var done: bool = false
## The prompt is up (the HUD reads this).
var prompt: bool = false
## Real seconds into the execution.
var t: float = 0.0
## Punches landed (tests).
var punches: int = 0
var head_gone: bool = false
var flicks: int = 0

var _hands: Node3D
var _fist: Node3D
var _grip: Node3D
var _blood: ShaderMaterial
var _coat: float = 0.0
var _fresh: float = 1.0
var _from: Vector3
var _to: Vector3
var _boss_yaw0: float = 0.0
var _boss_yaw1: float = 0.0
var _look_at: Vector3
var _yaw0: float = 0.0
var _pitch0: float = 0.0
var _contact: Vector3
var _slowmo_left: float = -1.0
var _drip: float = 0.0
var _released: bool = false
var _look_k: float = 0.0
var _splat: ScreenBlood
var _script_go: bool = false
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	cfg = boss.config.boss
	process_mode = Node.PROCESS_MODE_PAUSABLE


func _player() -> Player:
	if player == null or not is_instance_valid(player):
		player = boss.squad.player() if boss and boss.squad else get_tree().get_first_node_in_group(&"player") as Player
	return player


## Tests and captures: as if RB was pressed now (ignores range and facing).
func script_start() -> void:
	_script_go = true


## True if the operative could start it now: close, looking at him, alive.
func can_start() -> bool:
	var p: Player = _player()
	if p == null or p.dead or not is_instance_valid(boss) or not boss.boss or not boss.boss.is_down():
		return false
	var to: Vector3 = boss.body.head_position() - p.camera().global_position
	var flat: Vector3 = Vector3(to.x, 0.0, to.z)
	if flat.length() > cfg.execute_range:
		return false
	var fwd: Vector3 = -p.camera().global_basis.z
	return rad_to_deg(fwd.angle_to(to.normalized())) <= cfg.execute_view_deg


func _process(delta: float) -> void:
	if done:
		return
	var real: float = TimeControl.real_delta(delta)
	if not running:
		if not is_instance_valid(boss) or not boss.boss or not boss.boss.is_down():
			prompt = false
			return
		prompt = can_start()
		if _script_go or (prompt and Input.is_action_just_pressed(&"execute")):
			_start()
		return
	t += real
	_step(real)


# ------------------------------------------------------------------ start

func _start() -> void:
	var p: Player = _player()
	if p == null:
		return
	running = true
	prompt = false
	t = 0.0
	p.input_enabled = false
	p.invulnerable = true
	p.velocity = Vector3.ZERO
	if p.augments:
		for part: ActivePart in p.augments.parts.values():
			if part.is_running():
				part.stop()
	p.hands.clear()
	p.claim_hand(&"right", self)
	p.claim_hand(&"left", self)
	var away: Vector3 = p.global_position - boss.global_position
	away.y = 0.0
	away = away.normalized() if away.length() > 0.05 else boss.global_basis.z
	_from = p.global_position
	# Close enough that the knuckles reach his face: his head, then back toward the operative.
	var head: Vector3 = boss.body.head_position()
	_to = Vector3(head.x, p.global_position.y, head.z) + away * cfg.execute_stand
	_boss_yaw0 = boss._yaw
	_boss_yaw1 = atan2(away.x, away.z)
	_yaw0 = p.yaw
	_pitch0 = p.pitch
	_look_at = boss.body.head_position()
	_build_hands(p)
	_splat = ScreenBlood.new()
	add_child(_splat)
	boss.vocal(&"enemy_pain", 0.0, 0.05)


func _build_hands(p: Player) -> void:
	_hands = HANDS.instantiate() as Node3D
	_hands.name = "ExecutionHands"
	p.camera().add_child(_hands)
	_fist = _hands.find_child("fist_r", true, false) as Node3D
	_grip = _hands.find_child("grip_l", true, false) as Node3D
	if p.colors:
		p.colors.apply_to_model(_hands, true)
	_blood = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = BLOOD_SHADER
	_blood.shader = sh
	for n: Node in _hands.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if _fist and _fist.is_ancestor_of(mi):
			mi.material_overlay = _blood
	_fist.visible = false
	_grip.visible = false


# ------------------------------------------------------------------ the sequence

func _step(real: float) -> void:
	var p: Player = _player()
	var cam: Camera3D = p.camera()
	var times: PackedFloat32Array = cfg.punch_times
	var last_t: float = times[times.size() - 1]
	var release_at: float = last_t + 0.15
	var examine_at: float = release_at + cfg.release_time
	var shake_at: float = examine_at + cfg.examine_time
	var lower_at: float = shake_at + cfg.shake_time
	var end_at: float = lower_at + cfg.lower_time
	# Step in, turn him to face the operative, look at his face.
	var a: float = _smooth(t / 0.45)
	p.global_position = _from.lerp(_to, a)
	p.velocity = Vector3.ZERO
	if not head_gone and is_instance_valid(boss):
		boss.face(lerp_angle(_boss_yaw0, _boss_yaw1, _smooth(t / 0.4)))
		boss.body.set_aim(0.0, 0.35 + 0.15 * a, 1.0)
		# A little under his face, so the hand on his collar is in view too.
		_look_at = _look_at.lerp(boss.body.head_position() + Vector3.DOWN * 0.12, clampf(real * 6.0, 0.0, 1.0))
	var d: Vector3 = _look_at - cam.global_position
	var want_yaw: float = atan2(-d.x, -d.z)
	var want_pitch: float = atan2(d.y, Vector2(d.x, d.z).length()) - (deg_to_rad(8.0) * _smooth((t - examine_at) / 0.6) if head_gone else 0.0)
	p.set_view(lerp_angle(_yaw0, want_yaw, a), lerpf(_pitch0, want_pitch, a))
	_left_hand(cam, release_at)
	_right_hand(cam, times, release_at, examine_at, shake_at, lower_at)
	if _slowmo_left >= 0.0:
		_slowmo_left -= real
		if _slowmo_left < 0.0:
			TimeControl.set_slowmo(1.0)
	_blood.set_shader_parameter(&"coat", _coat)
	_fresh = maxf(0.0, _fresh - real * 0.04)
	_blood.set_shader_parameter(&"fresh", _fresh)
	if _fist:
		var kn: Transform3D = _fist.global_transform
		_blood.set_shader_parameter(&"knuckles", kn * KNUCKLES)
		_blood.set_shader_parameter(&"along", kn.basis.x.normalized())
	if t >= end_at:
		_finish()


func _left_hand(cam: Camera3D, release_at: float) -> void:
	if _grip == null:
		return
	if head_gone and t > release_at + cfg.release_time:
		_grip.visible = false
		return
	var collar: Vector3
	if is_instance_valid(boss) and not head_gone:
		var to_cam: Vector3 = (cam.global_position - boss.body.chest_position()).normalized()
		collar = boss.body.bone_position(&"neck") + to_cam * 0.16 * boss.config.body_scale + Vector3.DOWN * 0.08
		_contact = collar
	else:
		collar = _contact
	var held: Vector3 = cam.global_transform.affine_inverse() * collar
	var k: float = _smooth((t - 0.3) / 0.35)
	if t > release_at:
		k = 1.0 - _smooth((t - release_at) / cfg.release_time)
	_grip.visible = k > 0.01
	if not _released and t >= 0.62:
		_released = true
		Sfx.play_ui(&"exec_grab", -2.0, 0.05)
		if is_instance_valid(boss):
			boss.body.flinch(cam.global_position - boss.body.chest_position(), 1.5, false)
	# Not further than an arm reaches: the collar, or as far toward it as the arm goes.
	if held.length() > 0.5:
		held = held.normalized() * 0.5
	var hand: Vector3 = GRIP_FROM.lerp(held, k)
	# The forearm comes in from the left shoulder; the claw closes on the collar, palm toward him.
	var x: Vector3 = (hand - SHOULDER_L).normalized()
	var y: Vector3 = Vector3(0.5, 1.0, 0.4).normalized()
	y = (y - x * y.dot(x)).normalized()
	_grip.transform = Transform3D(Basis(x, y, x.cross(y)), hand - x * 0.07)


func _right_hand(cam: Camera3D, times: PackedFloat32Array, release_at: float, examine_at: float, shake_at: float, lower_at: float) -> void:
	if _fist == null:
		return
	var inv: Transform3D = cam.global_transform.affine_inverse()
	var pos: Vector3 = FIST_LOW
	var roll: float = 0.0
	var face_eye: bool = false
	if t < release_at:
		# Up from below, then each punch: draw back, drive into the face, come off it.
		var up_k: float = _smooth((t - 0.35) / 0.4)
		pos = FIST_LOW.lerp(FIST_REST, up_k)
		for i: int in times.size():
			var last: bool = i == times.size() - 1
			var hit_t: float = times[i]
			var wind: float = cfg.punch_last_windup if last else cfg.punch_windup
			var draw0: float = hit_t - wind - 0.14
			if t < draw0 or t > hit_t + cfg.punch_recover:
				continue
			var head: Vector3 = inv * _head_point(cam)
			if head.length() > 0.62:
				head = head.normalized() * 0.62
			if t < hit_t - wind:
				pos = FIST_REST.lerp(FIST_COCK, _smooth((t - draw0) / 0.14))
			elif t < hit_t:
				var u: float = (t - (hit_t - wind)) / wind
				pos = FIST_COCK.lerp(head, u * u * u)
				roll = deg_to_rad(-30.0 if i % 2 == 0 else 20.0) * u
			else:
				pos = head.lerp(FIST_REST, _smooth((t - hit_t) / cfg.punch_recover))
			if t >= hit_t and punches == i:
				_land(i, last, cam)
		if head_gone:
			pos = pos.lerp(FIST_LOW, _smooth((t - times[times.size() - 1]) / 0.3))
	elif t < examine_at:
		pos = FIST_LOW
	elif t < shake_at:
		# Up in front of the face, the knuckles and the back of the hand turned to the eye; the wrist turns slowly.
		var k: float = _smooth((t - examine_at) / 0.45)
		pos = FIST_LOW.lerp(FIST_LOOK, k)
		face_eye = k > 0.0
		_look_k = k
		roll = deg_to_rad(-25.0 + 45.0 * _smooth((t - examine_at) / cfg.examine_time)) * k
		_drip -= get_process_delta_time()
		if _drip <= 0.0 and k > 0.5:
			_drip = 0.12
			Gore.drip(_fist.global_transform * KNUCKLES + cam.global_basis.y * -0.03, 0.012)
	elif t < lower_at:
		# Three flicks down and out: the blood comes off in strings.
		var u2: float = (t - shake_at) / cfg.shake_time
		var phase: float = u2 * 3.0
		var k2: int = mini(int(phase), 2)
		var f: float = phase - float(k2)
		var pulse: float = sin(PI * clampf(f / 0.55, 0.0, 1.0))
		var into: float = _smooth(u2 * 4.0)
		pos = FIST_LOOK.lerp(FIST_SHAKE, into) + Vector3(0.12, -0.16, 0.0) * pulse
		face_eye = true
		_look_k = 1.0 - 0.6 * pulse
		roll = deg_to_rad(20.0 - 60.0 * pulse)
		if f >= 0.3 and flicks == k2:
			flicks += 1
			var kn: Vector3 = _fist.global_transform * KNUCKLES
			var fling: Vector3 = (cam.global_basis * Vector3(0.6, -0.8, -0.3)).normalized()
			Gore.spurt(kn, fling, 4.5, 7, 3)
			Sfx.play_ui(&"exec_flick", -3.0, 0.08)
			_fresh = maxf(_fresh - 0.15, 0.3)
			_coat = maxf(_coat - 0.05, 0.45)
	else:
		pos = FIST_SHAKE.lerp(FIST_LOW, _smooth((t - lower_at) / cfg.lower_time))
	_fist.visible = t >= 0.35
	# The forearm runs from the right shoulder to the fist; for the look it
	# stands up in front of the chest with the fist tipped back, so the
	# knuckles face the eye.
	var x: Vector3 = (pos - SHOULDER_R).normalized()
	if face_eye:
		x = x.lerp(EXAMINE_AXIS, _look_k).normalized()
	var want_y: Vector3 = Vector3.BACK if face_eye else Vector3.UP
	var y: Vector3 = want_y - x * want_y.dot(x)
	if y.length_squared() < 0.01:
		y = Vector3.UP - x * x.y
	y = y.normalized().rotated(x, roll)
	var b: Basis = Basis(x, y, x.cross(y)).orthonormalized()
	_fist.transform = Transform3D(b, pos - b * KNUCKLES)


## Where the knuckles meet his face: the front of the head, toward the eye.
func _head_point(cam: Camera3D) -> Vector3:
	if is_instance_valid(boss) and not head_gone:
		var h: Vector3 = boss.body.head_position()
		var to_cam: Vector3 = (cam.global_position - h).normalized()
		_contact = h + to_cam * 0.1 * boss.config.body_scale
	return _contact


func _land(i: int, last: bool, cam: Camera3D) -> void:
	punches += 1
	var h: Vector3 = boss.body.head_position()
	var dir: Vector3 = (h - cam.global_position).normalized()
	var p: Player = _player()
	_coat = minf(_coat + (0.3 if last else 0.2), 0.9)
	_fresh = 1.0
	if not last:
		boss.body.flinch(dir + Vector3.UP * 0.15 + cam.global_basis.x * (0.5 if i % 2 == 0 else -0.3), 3.6, true)
		boss.body.add_wound(&"head", _contact, 0.03 + 0.008 * i, false)
		boss.body.set_bloodied(0.08 * float(i + 1))
		Gore.spray(h, dir + Vector3.UP * 0.25, 1.6, 20)
		Gore.spray(h, -dir + Vector3.UP * 0.4, 0.7, 6)
		Gore.mist(h, dir, 1.2)
		Sfx.play_at(&"exec_punch", h, 4.0, 0.06)
		Sfx.play_at(&"impact_flesh", h, 0.0, 0.1)
		TimeControl.hitstop(0.07, 0.05)
		p.add_shake(0.55)
		_rumble(0.8, 1.0, 0.16)
		_splat.splash(0.35 + 0.12 * float(i), _rng)
		boss.vocal(&"enemy_pain", 3.0, 0.08)
		return
	# The last one: the head goes.
	head_gone = true
	_contact = h
	boss.boss.finish()
	boss.sever(&"head", dir * 7.0 + Vector3.UP * 2.5, true, null, &"head")
	boss.body.push_bone(&"chest", (dir * 160.0 + Vector3.UP * 30.0), boss.body.chest_position())
	Gore.spray(h, dir + Vector3.UP * 0.3, 2.4, 40)
	Gore.spray(h, -dir + Vector3.UP * 0.5, 1.2, 14)
	Sfx.play_at(&"exec_skull", h, 6.0, 0.03)
	Sfx.play_at(&"gore_sever", h, 2.0, 0.05)
	TimeControl.hitstop(0.1, 0.05)
	TimeControl.set_slowmo(cfg.finish_slowmo)
	_slowmo_left = cfg.finish_slowmo_time
	p.add_shake(1.1)
	_rumble(1.0, 1.0, 0.4)
	_splat.splash(1.0, _rng)


func _finish() -> void:
	var p: Player = _player()
	running = false
	done = true
	TimeControl.set_slowmo(1.0)
	if p:
		p.release_hand(&"right", self)
		p.release_hand(&"left", self)
		p.input_enabled = true
		p.invulnerable = false
	if _hands:
		_hands.queue_free()
	finished.emit()
	# The blood on the view runs on and fades by itself.
	get_tree().create_timer(3.0).timeout.connect(queue_free)


func _exit_tree() -> void:
	if running:
		TimeControl.set_slowmo(1.0)
		var p: Player = _player()
		if p and is_instance_valid(p):
			p.input_enabled = true
			p.invulnerable = false
			p.release_hand(&"right", self)
			p.release_hand(&"left", self)
		if _hands and is_instance_valid(_hands):
			_hands.queue_free()


static func _smooth(x: float) -> float:
	var u: float = clampf(x, 0.0, 1.0)
	return u * u * (3.0 - 2.0 * u)


func _rumble(weak: float, strong: float, seconds: float) -> void:
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, weak, strong, seconds)
