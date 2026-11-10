class_name MeshArm
extends ActivePart
## NT-5 Prehensile Mesh Arm (MeshArmData). While it's deployed it's in one
## of four modes: READY (the claw sits at the wrist), REACHING (the tendril
## is on its way to a target), HOLDING (a seized enemy hangs in front of
## the operative: Enemy.seize makes him a living ragdoll that the arm drags
## to the hold point every physics frame) and RETRACTING. RT shoots, RT
## again throws (Enemy.release: he flies, knocks down whoever he hits and
## dies where he lands).
##
## The forearm model plays the deploy clip; the tendril and its four-finger
## claw are drawn fresh each frame as tubes along a curve from the wrist to
## the tip (Tube).

enum Mode { READY, REACHING, HOLDING, RETRACTING }

const TENDRIL_SHADER: String = """
shader_type spatial;
uniform vec4 glow : source_color = vec4(0.36, 0.86, 0.78, 1.0);
uniform float pulse = 0.0;
void fragment() {
	// A braid: two sets of helical strands crossing, thin lit gaps between them.
	float a = fract(UV.x * 6.0 + UV.y * 9.0);
	float b = fract(UV.x * 6.0 - UV.y * 9.0);
	float gap_a = 1.0 - smoothstep(0.0, 0.1, a) * (1.0 - smoothstep(0.9, 1.0, a));
	float gap_b = 1.0 - smoothstep(0.0, 0.1, b) * (1.0 - smoothstep(0.9, 1.0, b));
	float gap = max(gap_a, gap_b);
	ALBEDO = mix(vec3(0.03, 0.032, 0.036), vec3(0.004), gap);
	ROUGHNESS = mix(0.38, 0.9, gap);
	METALLIC = 0.4 * (1.0 - gap);
	float run = smoothstep(0.75, 1.0, fract(UV.y * 0.6 - TIME * 1.8));
	EMISSION = glow.rgb * gap * (0.25 + 1.6 * run + 4.0 * pulse);
}
"""

var cfg: MeshArmData
var rig: ArmRig
var mode: Mode = Mode.READY
## Who it's reaching for or holding.
var victim: Enemy
## Tip of the tendril (world).
var tip: Vector3 = Vector3.ZERO
var grabs: int = 0
var throws: int = 0

var _root_node: Node3D
var _mesh: MeshInstance3D
var _im: ImmediateMesh = ImmediateMesh.new()
var _mat: ShaderMaterial
var _pulse: float = 0.0
var _grip: float = 0.0
var _script_fire: bool = false
var _miss_point: Vector3 = Vector3.INF


func _ready() -> void:
	super._ready()
	cfg = data as MeshArmData
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "MeshArmRig")
	if player == null:
		add_child(rig)
	_root_node = rig.part("tendril_root")
	_mesh = MeshInstance3D.new()
	_mesh.name = "Tendril"
	_mesh.top_level = true
	_mesh.mesh = _im
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_mat = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = TENDRIL_SHADER
	_mat.shader = sh
	_mat.set_shader_parameter(&"glow", cfg.glow_color)
	_mesh.material_override = _mat
	_mesh.visible = false
	add_child(_mesh)
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	_drop()
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()


func hand() -> StringName:
	return &"left"


func hud_pips() -> int:
	return roundi(charge_capacity())


func _drain(_real: float) -> void:
	pass


## RT as if pressed (tests, demos): shoot, or throw what it holds.
func script_fire() -> void:
	_script_fire = true


## How fast it throws (m/s): usable strength and impact.
func throw_speed() -> float:
	if body == null:
		return cfg.throw_speed
	var k: float = body.usable_strength() / maxf(cfg.strength_ref, 0.1) * sqrt(body.stat(&"impact"))
	return clampf(cfg.throw_speed * k, cfg.min_throw, cfg.max_throw)


func root() -> Vector3:
	if _root_node and _root_node.is_inside_tree():
		return _root_node.global_position
	var cam: Camera3D = player.camera()
	return cam.global_position + cam.global_basis * Vector3(-0.25, -0.22, -0.4)


func _rest_tip() -> Vector3:
	var cam: Camera3D = player.camera()
	return root() - cam.global_basis.z * 0.2 + cam.global_basis.y * 0.03


func _on_start() -> void:
	mode = Mode.READY
	victim = null
	rig.visible = true
	Sfx.play_ui(&"nt5_deploy", -2.0, 0.0)
	rumble(0.2, 0.3, 0.3)


func _on_stop() -> void:
	_drop()
	mode = Mode.READY
	Sfx.play_ui(&"nt5_stow", -4.0, 0.0)


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_state_changed(s: State) -> void:
	match s:
		State.ACTIVE:
			tip = _rest_tip()
			_mesh.visible = true
		State.COOLDOWN:
			rig.visible = false
			_mesh.visible = false


func _on_blend(a: float) -> void:
	rig.seek(a)


## Lets go of whoever it holds without throwing him.
func _drop() -> void:
	if victim and is_instance_valid(victim) and victim.held:
		victim.release(Vector3.ZERO, player)
	victim = null


## The living enemy nearest the crosshair inside the cone, in reach and in sight.
func target() -> Enemy:
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var best: Enemy = null
	var best_score: float = INF
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive or e.held:
			continue
		var at: Vector3 = e.body.chest_position()
		var to: Vector3 = at - eye
		var d: float = to.length()
		if d > cfg.reach:
			continue
		var ang: float = rad_to_deg(fwd.angle_to(to))
		# Close up the cone opens: he's right there.
		if ang > cfg.cone_deg + 60.0 / maxf(d, 1.0):
			continue
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, at, Ballistics.LAYER_WORLD)
		if not space.intersect_ray(q).is_empty():
			continue
		var score: float = ang + d * 0.2
		if score < best_score:
			best_score = score
			best = e
	return best


func _on_active(real: float) -> void:
	var dt: float = real * TimeControl.player_scale_now()
	var fire: bool = _script_fire or (can_input() and Input.is_action_just_pressed(&"fire"))
	_script_fire = false
	_pulse = maxf(0.0, _pulse - real * 3.0)
	match mode:
		Mode.READY:
			tip = tip.lerp(_rest_tip(), clampf(real * 20.0, 0.0, 1.0))
			_grip = move_toward(_grip, 0.0, real * 6.0)
			if fire and charge >= 1.0:
				_shoot()
			elif fire:
				_on_denied()
		Mode.REACHING:
			var goal: Vector3 = _miss_point
			if victim and is_instance_valid(victim) and victim.alive:
				goal = victim.body.chest_position()
			elif _miss_point == Vector3.INF:
				mode = Mode.RETRACTING
				return
			tip = tip.move_toward(goal, cfg.shoot_speed * dt)
			if tip.distance_to(goal) < 0.25:
				if victim and is_instance_valid(victim) and victim.seize(player):
					_seized()
				else:
					victim = null
					mode = Mode.RETRACTING
					Sfx.play_at(&"mw7_scrape", tip, -4.0, 0.1)
		Mode.HOLDING:
			_grip = move_toward(_grip, 1.0, real * 10.0)
			if victim == null or not is_instance_valid(victim):
				victim = null
				mode = Mode.RETRACTING
			else:
				tip = victim.body.chest_position()
				if fire:
					_throw()
		Mode.RETRACTING:
			_grip = move_toward(_grip, 0.0, real * 6.0)
			var home: Vector3 = _rest_tip()
			tip = tip.move_toward(home, cfg.reel_speed * dt)
			if tip.distance_to(home) < 0.1:
				mode = Mode.READY


func _physics_process(_delta: float) -> void:
	if mode == Mode.HOLDING and state == State.ACTIVE and victim and is_instance_valid(victim) and victim.held:
		var cam: Camera3D = player.camera()
		victim.body.drag_to(cam.global_position + cam.global_basis * cfg.hold_offset, cfg.hold_rate, cfg.hold_max_speed)


func _shoot() -> void:
	victim = target()
	_miss_point = Vector3.INF
	if victim == null:
		# Nobody there: it lashes out to its reach (or the wall) and comes back.
		var cam: Camera3D = player.camera()
		var end: Vector3 = cam.global_position - cam.global_basis.z * cfg.reach
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(cam.global_position, end, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
		var res: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
		if not res.is_empty():
			end = res["position"]
		_miss_point = end
	mode = Mode.REACHING
	Sfx.play_ui(&"nt5_shoot", -1.0, 0.06)
	rig.kick_pos.kick(Vector3(0.0, 0.0, -0.05))
	rumble(0.3, 0.2, 0.1)


func _seized() -> void:
	charge = maxf(charge - 1.0, 0.0)
	_since_stop = 0.0
	grabs += 1
	mode = Mode.HOLDING
	_pulse = 1.0
	Sfx.play_ui(&"nt5_grab", 0.0, 0.05)
	rumble(cfg.rumble_grab.x, cfg.rumble_grab.y, cfg.rumble_grab.z)
	TimeControl.hitstop(0.04, 0.2)
	rig.kick_pos.kick(Vector3(0.0, 0.0, 0.06))
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(cfg.camera_kick_grab_deg)


func _throw() -> void:
	var cam: Camera3D = player.camera()
	var v: Vector3 = -cam.global_basis.z * throw_speed() + Vector3.UP * cfg.throw_lift
	victim.release(v, player)
	victim = null
	throws += 1
	mode = Mode.RETRACTING
	_pulse = 1.0
	Sfx.play_ui(&"nt5_throw", 0.0, 0.05)
	rumble(cfg.rumble_throw.x, cfg.rumble_throw.y, cfg.rumble_throw.z)
	rig.kick_pos.kick(Vector3(0.0, 0.02, -0.09))
	rig.kick_rot.kick(Vector3(deg_to_rad(-10.0), 0.0, 0.0))
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(cfg.camera_kick_throw_deg)


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if not rig.visible:
		return
	rig.tick(real, blend, player)
	if state == State.RECOVERING:
		tip = tip.lerp(root(), clampf(real * 16.0, 0.0, 1.0))
	if _mesh.visible:
		_draw()


func _draw() -> void:
	var r: Vector3 = root()
	var cam: Camera3D = player.camera()
	var span: float = r.distance_to(tip)
	# The tendril sags a little and bows out to the left on the way.
	var mid: Vector3 = r.lerp(tip, 0.5) + Vector3.DOWN * minf(span * 0.06, 0.5) - cam.global_basis.x * minf(span * 0.05, 0.4)
	var path: PackedVector3Array = Tube.bezier(r, mid, tip, clampi(roundi(span * 3.0) + 4, 4, 26))
	var radii: PackedFloat32Array = PackedFloat32Array()
	for i: int in path.size():
		var t: float = float(i) / (path.size() - 1)
		# Thinner as it stretches; a swell at the wrist and at the claw.
		radii.append(cfg.radius * (1.0 / (1.0 + span * 0.04)) * (1.0 + 0.35 * pow(1.0 - t, 6.0) + 0.3 * pow(t, 8.0)))
	_mat.set_shader_parameter(&"pulse", _pulse)
	_im.clear_surfaces()
	_im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	Tube.add(_im, path, radii, 8, 6.0)
	# The claw: four fingers that splay open or wrap round what it holds.
	var fwd: Vector3 = (tip - path[path.size() - 2]).normalized()
	var up: Vector3 = fwd.cross(Vector3.UP if absf(fwd.y) < 0.9 else Vector3.RIGHT).normalized()
	var side: Vector3 = fwd.cross(up)
	var wrap: float = 0.34 if mode == Mode.HOLDING else 0.09
	for k: int in 4:
		var a: float = TAU * k / 4.0 + 0.6
		var out: Vector3 = up * cos(a) + side * sin(a)
		var open: float = lerpf(0.9, 0.15, _grip)
		var p0: Vector3 = tip
		var p1: Vector3 = tip + out * wrap * (0.55 + 0.45 * open) + fwd * wrap * 0.35
		var p2: Vector3 = tip + out * wrap * open + fwd * wrap * lerpf(1.0, 0.55, _grip) - out * wrap * 0.9 * _grip
		Tube.add(_im, Tube.bezier(p0, p1, p2, 5), PackedFloat32Array([cfg.radius * 0.6, cfg.radius * 0.55, cfg.radius * 0.45, cfg.radius * 0.35, cfg.radius * 0.25, cfg.radius * 0.12]), 5, 6.0)
	_im.surface_end()
