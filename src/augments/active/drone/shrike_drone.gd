class_name ShrikeDrone
extends ActivePart
## SD-3 Shrike (ShrikeDroneData): a first-person kamikaze drone.
##
## Deploying (deploy_time): the drone leaves the pod over the left shoulder,
## flies out in front of the operative and unfolds (the model's clip,
## scrubbed from the blend). Active: the view is the drone's camera and the
## operative's controls are off; his body (BodyAppearance, in his colours
## and hardware) stands where he was, and enemies still shoot at it. The
## drone is a small CharacterBody3D flown with the sticks. It ends by
## detonating (RT, a hard impact, or touching an enemy: Explosion), by the
## link dropping (LB, out of range, battery flat, the operative badly
## hurt), or by the operative dying.

const VIEW_SHADER: String = """
shader_type canvas_item;
uniform vec4 tint : source_color = vec4(1.0, 0.72, 0.3, 1.0);
uniform float noise = 0.0;
uniform float alarm = 0.0;
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void fragment() {
	vec2 d = UV - 0.5;
	d.x *= 1.7;
	float r = length(d);
	float line = 0.5 + 0.5 * sin(UV.y * 720.0);
	float n = hash(floor(UV * vec2(320.0, 180.0)) + floor(TIME * 30.0));
	float tear = step(0.985 - noise * 0.2, hash(vec2(floor(UV.y * 40.0), floor(TIME * 18.0))));
	float a = smoothstep(0.45, 1.0, r) * 0.55 + line * 0.05 + n * (0.04 + 0.5 * noise) + tear * noise * 0.5;
	vec3 col = mix(tint.rgb * 0.25, vec3(1.0, 0.1, 0.05), alarm * (0.5 + 0.5 * sin(TIME * 20.0)) * smoothstep(0.25, 0.9, r));
	col = mix(col, vec3(n), clamp(noise * 0.8, 0.0, 1.0));
	COLOR = vec4(col, clamp(a, 0.0, 0.92));
}
"""

var cfg: ShrikeDroneData
var weapon: WeaponData
## The drone in flight, or null.
var craft: CharacterBody3D
var cam: Camera3D
## Seconds of battery left, distance from the operative (m), link quality 0..1.
var battery: float = 0.0
var distance: float = 0.0
var link: float = 1.0
## Kills by the last detonation; how the last flight ended.
var last_kills: int = 0
var last_end: StringName = &""

var _model: Node3D
var _anim: AnimationPlayer
var _clip: StringName = &""
var _clip_len: float = 1.0
var _flight_time: float = 0.0
var _yaw: float = 0.0
var _pitch: float = 0.0
var _stand_in: BodyAppearance
var _hidden: Array[Node3D] = []
var _layer: CanvasLayer
var _shade: ColorRect
var _view: DroneView
var _alarm: float = 0.0
var _rotor: AudioStreamPlayer
var _script_detonate: bool = false
var _launch_from: Vector3
var _launch_to: Vector3
var _input_was: bool = true


class DroneView:
	extends Control
	var drone: ShrikeDrone
	var font: Font

	func _draw() -> void:
		var vp: Vector2 = get_viewport_rect().size
		var c: Color = drone.cfg.hud_color
		var mid: Vector2 = vp * 0.5
		# Reticle: a broken ring and a centre dot.
		for k: int in 4:
			draw_arc(mid, 26.0, k * PI * 0.5 + 0.25, k * PI * 0.5 + PI * 0.5 - 0.25, 10, Color(c, 0.8), 2.0)
		draw_circle(mid, 2.0, c)
		var blast: float = drone.cfg.blast_radius
		# Everyone it can see, boxed; inside the blast radius they're boxed in red.
		for n: Node in get_tree().get_nodes_in_group(&"enemies"):
			var e: Enemy = n as Enemy
			if e == null or not e.alive or drone.cam == null:
				continue
			var at: Vector3 = e.body.chest_position()
			if drone.cam.is_position_behind(at):
				continue
			var d: float = at.distance_to(drone.cam.global_position)
			if d > 70.0:
				continue
			var p: Vector2 = drone.cam.unproject_position(at)
			var s: float = clampf(520.0 / maxf(d, 1.0), 10.0, 150.0)
			var col: Color = Color(1.0, 0.25, 0.2, 0.95) if d < blast else Color(c, 0.7)
			var r: Rect2 = Rect2(p - Vector2(s * 0.35, s * 0.6), Vector2(s * 0.7, s * 1.2))
			var l: float = s * 0.2
			for corner: Vector2 in [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]:
				var sx: float = 1.0 if corner.x == r.position.x else -1.0
				var sy: float = 1.0 if corner.y == r.position.y else -1.0
				draw_line(corner, corner + Vector2(l * sx, 0), col, 2.0)
				draw_line(corner, corner + Vector2(0, l * sy), col, 2.0)
			draw_string(font, r.position + Vector2(0, -4), "%.0f m" % d, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, col)
		var range_m: float = drone.body.link_range_m() if drone.body else 0.0
		var top: String = "SD-3 SHRIKE    LINK %d%%    %.0f / %.0f m    BATTERY %.0f s" % [roundi(drone.link * 100.0), drone.distance, range_m, maxf(drone.battery, 0.0)]
		draw_string(font, Vector2(0, 46), top, HORIZONTAL_ALIGNMENT_CENTER, vp.x, 16, c)
		draw_string(font, Vector2(0, vp.y - 30), "RT  DETONATE      LB  CUT LINK      A / B  CLIMB / SINK", HORIZONTAL_ALIGNMENT_CENTER, vp.x, 14, Color(c, 0.75))
		if drone._alarm > 0.0:
			draw_string(font, Vector2(0, 84), "BODY UNDER FIRE", HORIZONTAL_ALIGNMENT_CENTER, vp.x, 22, Color(1.0, 0.25, 0.2, 0.6 + 0.4 * sin(Time.get_ticks_msec() * 0.02)))
		if drone.link < 0.35:
			draw_string(font, Vector2(0, 112), "LINK WEAK", HORIZONTAL_ALIGNMENT_CENTER, vp.x, 18, Color(1.0, 0.5, 0.2))


func _ready() -> void:
	super._ready()
	cfg = data as ShrikeDroneData
	weapon = AugHit.weapon_named("SD-3 Shrike")
	_layer = CanvasLayer.new()
	_layer.layer = 5
	_layer.visible = false
	add_child(_layer)
	_shade = ColorRect.new()
	_shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = VIEW_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"tint", cfg.hud_color)
	_shade.material = mat
	_layer.add_child(_shade)
	_view = DroneView.new()
	_view.drone = self
	_view.font = ThemeDB.fallback_font
	_view.set_anchors_preset(Control.PRESET_FULL_RECT)
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(_view)
	_rotor = AudioStreamPlayer.new()
	_rotor.bus = &"SFX"
	_rotor.volume_db = -10.0
	var loop: Array = Sfx.bank(&"sd3_rotor")
	if not loop.is_empty():
		_rotor.stream = loop[0]
	add_child(_rotor)
	state_changed.connect(_on_state_changed)
	if player:
		player.damaged.connect(_on_player_damaged)


func _exit_tree() -> void:
	super._exit_tree()
	_end_flight(&"gone", false)


func hud_pips() -> int:
	return roundi(charge_capacity())


## Each launch spends a drone; nothing drains over time.
func _drain(_real: float) -> void:
	pass


## Detonates on the next frame (tests, demos).
func script_detonate() -> void:
	_script_detonate = true


## Look rate (rad/s): a faster co-processor flies it more sharply.
func turn_rate() -> float:
	var k: float = body.stat(&"processing") / maxf(cfg.processing_ref, 0.1) if body else 1.0
	return deg_to_rad(cfg.turn_rate_deg) * clampf(k, 0.6, 1.6)


## Points the drone (radians), as the right stick would (tests, demos).
func set_view(yaw: float, pitch: float) -> void:
	_yaw = yaw
	_pitch = clampf(pitch, -1.35, 1.35)


func is_piloting() -> bool:
	return state == State.ACTIVE and craft != null


func _on_start() -> void:
	charge = maxf(charge - 1.0, 0.0)
	last_kills = 0
	last_end = &""
	battery = cfg.battery
	_flight_time = 0.0
	_alarm = 0.0
	var pc: Camera3D = player.camera()
	_launch_from = pc.global_position + pc.global_basis * cfg.launch_offset
	_launch_to = pc.global_position + pc.global_basis * cfg.handover_offset
	_yaw = player.yaw
	_pitch = 0.0
	_build_craft()
	craft.global_position = _launch_from
	Sfx.play_ui(&"sd3_launch", -1.0, 0.0)
	rumble(0.3, 0.6, 0.25)


func _build_craft() -> void:
	craft = CharacterBody3D.new()
	craft.name = "ShrikeDrone"
	craft.top_level = true
	craft.collision_layer = 0
	craft.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_ENEMY
	craft.motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	var cs: CollisionShape3D = CollisionShape3D.new()
	var sphere: SphereShape3D = SphereShape3D.new()
	sphere.radius = 0.17
	cs.shape = sphere
	craft.add_child(cs)
	_model = cfg.scene.instantiate() as Node3D
	craft.add_child(_model)
	_anim = null
	for n: Node in _model.find_children("*", "AnimationPlayer", true, false):
		_anim = n as AnimationPlayer
		break
	if _anim and not _anim.get_animation_list().is_empty():
		_clip = StringName(_anim.get_animation_list()[0])
		_clip_len = _anim.get_animation(_clip).length
		_anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		_anim.play(_clip)
		_anim.seek(0.0, true)
	# One draw per material instead of one per piece (optimization overhaul C-07).
	RigidMerge.apply(_model)
	cam = Camera3D.new()
	cam.fov = cfg.camera_fov
	cam.near = 0.05
	# Just above and behind the nose, so the warhead and the front arms frame the view.
	cam.position = Vector3(0.0, 0.085, 0.06)
	craft.add_child(cam)
	world().add_child(craft)


func _on_blend(a: float) -> void:
	if state != State.DEPLOYING or craft == null:
		return
	# Out of the pod, up and forward, unfolding as it goes.
	var e: float = a * a * (3.0 - 2.0 * a)
	var arc: Vector3 = Vector3.UP * sin(a * PI) * 0.35
	craft.global_position = _launch_from.lerp(_launch_to, e) + arc
	craft.global_basis = Basis(Vector3.UP, _yaw)
	if _anim and _clip != &"":
		_anim.seek(clampf(a * 1.15, 0.0, 1.0) * _clip_len, true)


func _on_state_changed(s: State) -> void:
	if s == State.ACTIVE:
		_take_control()
	elif s == State.RECOVERING or s == State.COOLDOWN:
		_end_flight(last_end if last_end != &"" else &"cut", false)


func _take_control() -> void:
	_input_was = player.input_enabled
	player.input_enabled = false
	_hidden.clear()
	for c: Node in player.camera().get_children():
		var n3: Node3D = c as Node3D
		if n3 and n3.visible:
			n3.visible = false
			_hidden.append(n3)
	# The operative, standing where he was.
	if _stand_in == null:
		_stand_in = BodyAppearance.new()
		_stand_in.name = "OperativeStandIn"
		_stand_in.loadout = player.loadout
		_stand_in.colors = player.colors
		player.add_child(_stand_in)
		_stand_in.rotation.y = PI
	else:
		_stand_in.loadout = player.loadout
		_stand_in.colors = player.colors
		_stand_in.rebuild()
	_stand_in.visible = true
	cam.make_current()
	_layer.visible = true
	if _rotor.stream:
		_rotor.play()
	Sfx.play_ui(&"sd3_link", -4.0, 0.0)


func _on_active(real: float) -> void:
	if craft == null:
		stop()
		return
	_alarm = maxf(0.0, _alarm - real)
	# Looking is real time, like the operative's own view.
	if not get_tree().paused:
		var look: Vector2 = Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.12)
		var rate: float = turn_rate()
		_yaw -= look.x * rate * real
		_pitch = clampf(_pitch - look.y * rate * real, -1.35, 1.35)
	craft.global_basis = Basis(Vector3.UP, _yaw) * Basis(Vector3.RIGHT, _pitch)
	distance = craft.global_position.distance_to(player.global_position)
	var range_m: float = maxf(body.link_range_m(), 1.0) if body else 100.0
	var far: float = distance / range_m
	link = clampf(1.0 - far * far, 0.0, 1.0)
	var noise: float = clampf((far - cfg.static_from) / maxf(1.0 - cfg.static_from, 0.01), 0.0, 1.0)
	var m: ShaderMaterial = _shade.material as ShaderMaterial
	m.set_shader_parameter(&"noise", noise)
	m.set_shader_parameter(&"alarm", clampf(_alarm, 0.0, 1.0))
	_view.queue_redraw()
	if _rotor.playing:
		_rotor.pitch_scale = clampf(0.85 + craft.velocity.length() / cfg.speed * 0.5, 0.5, 2.0) * clampf(Engine.time_scale, 0.3, 1.0)
	var armed: bool = _flight_time >= cfg.arm_time
	if armed and (_script_detonate or (not get_tree().paused and Input.is_action_just_pressed(&"fire"))):
		_script_detonate = false
		detonate()
		return
	if not get_tree().paused and Input.is_action_just_pressed(&"active_use") and _flight_time > 0.2:
		_lose(&"cut")
		return
	if far >= 1.0:
		_lose(&"range")
	elif battery <= 0.0:
		_lose(&"battery")
	elif player.health_fraction() < cfg.recall_health:
		_lose(&"recalled")


func _physics_process(delta: float) -> void:
	if state != State.ACTIVE or craft == null:
		return
	_flight_time += delta
	battery -= delta
	var move: Vector2 = Vector2.ZERO
	var lift: float = 0.0
	if not get_tree().paused:
		move = Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back", 0.15)
		lift = Input.get_action_strength(&"jump") - Input.get_action_strength(&"slide")
	var want: Vector3 = craft.global_basis * Vector3(move.x, 0.0, move.y) * cfg.speed + Vector3.UP * lift * cfg.lift_speed
	craft.velocity = craft.velocity.move_toward(want, cfg.accel * delta)
	var before: float = craft.velocity.length()
	craft.move_and_slide()
	for i: int in craft.get_slide_collision_count():
		var col: KinematicCollision3D = craft.get_slide_collision(i)
		if _flight_time < cfg.arm_time:
			continue
		if col.get_collider() is Enemy or before >= cfg.impact_speed:
			detonate()
			return


## The warhead goes off where the drone is.
func detonate() -> void:
	if craft == null:
		return
	var at: Vector3 = craft.global_position
	last_end = &"detonated"
	_end_flight(&"detonated", true)
	last_kills = Explosion.detonate(player, at, cfg.blast_radius, cfg.blast_damage, player, weapon)
	stop()


## The link is gone: the drone drops out of the air, unexploded.
func _lose(why: StringName) -> void:
	last_end = why
	if craft:
		Fx._emit(&"sparks", craft.global_position, Vector3.UP, Color(1.0, 0.8, 0.5, 1.0), 4, 1.0)
		Sfx.play_at(&"sd3_lost", craft.global_position, -4.0, 0.05)
	Sfx.play_ui(&"sd3_lost", -6.0, 0.0)
	stop()


## Back to the operative's own eyes.
func _end_flight(why: StringName, blast: bool) -> void:
	if last_end == &"":
		last_end = why
	_rotor.stop()
	if _layer:
		_layer.visible = false
	if _stand_in:
		_stand_in.visible = false
	for n: Node3D in _hidden:
		if is_instance_valid(n):
			n.visible = true
	_hidden.clear()
	if craft and is_instance_valid(craft):
		if cam and cam.current and player and is_instance_valid(player):
			player.camera().make_current()
			if not player.dead:
				player.input_enabled = _input_was
			if not blast:
				Sfx.play_ui(&"sd3_link", -8.0, 0.0)
		craft.queue_free()
	craft = null
	cam = null


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_player_damaged(_amount: float, _from: Vector3) -> void:
	if is_piloting():
		_alarm = 1.5
		Sfx.play_ui(&"sd3_alarm", -6.0, 0.0)
