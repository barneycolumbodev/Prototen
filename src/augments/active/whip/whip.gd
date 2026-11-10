class_name Whip
extends ActivePart
## MW-7 Monofilament Whip (WhipData). The filament is a chain of points
## simulated in the world: the reel on the wrist is its root, the handle
## direction drags it (strongly near the hand, weakly at the bead, so the
## tip lags and cracks), and each link keeps its length. Anything a fast
## link passes through is cut: living bodies and corpses take an AugHit on
## the hitbox it crossed (so limbs and heads come off at Maximum gore); the
## world throws sparks.
##
## Steering: with LT held the view is frozen and the right stick places the
## handle (full stick = max_yaw/pitch off centre). RT sweeps it across the
## crosshair, alternating sides. Without either it hangs low on the right.
## Speed comes from the melee speed stat, bite from melee power.

## One sample of the swoosh behind the bead.
class TrailPoint:
	extends RefCounted
	var tip: Vector3
	var mid: Vector3
	var age: float = 0.0


var cfg: WhipData
var rig: ArmRig
var weapon: WeaponData
## Points of the filament, root first (world space).
var pts: PackedVector3Array = PackedVector3Array()
## Cuts landed since it was drawn (tests, HUD).
var cuts: int = 0
## Fastest the bead has gone since it was drawn (m/s).
var peak_tip_speed: float = 0.0

var _prev: PackedVector3Array = PackedVector3Array()
var _aim: Vector2 = Vector2.ZERO  # radians: x = right, y = up
var _lash_t: float = -1.0
var _lash_dir: float = 1.0
var _lash_cd: float = 0.0
var _script_lash: bool = false
var _recut: Dictionary[int, float] = {}
var _line: MeshInstance3D
var _im: ImmediateMesh = ImmediateMesh.new()
var _bead: MeshInstance3D
var _trail: Array[TrailPoint] = []
var _emitter: Node3D
var _swish_cd: float = 0.0
var _crack_cd: float = 0.0
var _spark_cd: float = 0.0
var _live: bool = false


func _ready() -> void:
	super._ready()
	cfg = data as WhipData
	weapon = AugHit.weapon_named("MW-7 Monofilament Whip")
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "WhipRig")
	if player == null:
		add_child(rig)
	_emitter = rig.part("emitter")
	_line = MeshInstance3D.new()
	_line.name = "Filament"
	_line.top_level = true
	_line.mesh = _im
	_line.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.vertex_color_use_as_albedo = true
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	_line.material_override = m
	_line.visible = false
	add_child(_line)
	_bead = MeshInstance3D.new()
	_bead.top_level = true
	var sphere: SphereMesh = SphereMesh.new()
	sphere.radius = 0.014
	sphere.height = 0.036
	sphere.radial_segments = 10
	sphere.rings = 5
	_bead.mesh = sphere
	var bm: StandardMaterial3D = StandardMaterial3D.new()
	bm.albedo_color = Color(0.3, 0.32, 0.36)
	bm.metallic = 1.0
	bm.roughness = 0.25
	bm.emission_enabled = true
	bm.emission = cfg.filament_color
	bm.emission_energy_multiplier = 1.5
	_bead.material_override = bm
	_bead.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_bead.visible = false
	add_child(_bead)
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	if player and is_instance_valid(player):
		player.look_frozen = false
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()


func hand() -> StringName:
	return &"right"


func _drain(_real: float) -> void:
	pass


## Damage of one cut: the filament does the cutting, the arm sets how deep.
func cut_damage() -> float:
	return cfg.damage * sqrt(body.stat(&"melee_power") if body else 1.0)


## How fast the handle swings (rad/s) and the lash lands: the melee speed stat.
func swing_rate() -> float:
	return deg_to_rad(cfg.swing_rate_deg) * (body.stat(&"melee_speed") if body else 1.0)


## A lash as if RT was pressed (tests, demos).
func script_lash() -> void:
	_script_lash = true


## Points the handle (radians right, up), as the stick would.
func set_aim(yaw: float, pitch: float) -> void:
	_aim = Vector2(yaw, pitch)


func _on_start() -> void:
	cuts = 0
	peak_tip_speed = 0.0
	_lash_t = -1.0
	_aim = Vector2(deg_to_rad(cfg.rest_aim_deg.x), deg_to_rad(cfg.rest_aim_deg.y))
	rig.visible = true
	_live = false
	Sfx.play_ui(&"mw7_deploy", -2.0, 0.0)
	rumble(0.2, 0.2, 0.2)


func _on_stop() -> void:
	Sfx.play_ui(&"mw7_stow", -4.0, 0.0)
	if player:
		player.look_frozen = false


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_state_changed(s: State) -> void:
	match s:
		State.ACTIVE:
			_spawn_filament()
		State.RECOVERING:
			pass
		State.COOLDOWN:
			rig.visible = false
			_live = false
			_line.visible = false
			_bead.visible = false
			_trail.clear()


func _on_blend(a: float) -> void:
	rig.seek(a)


## Root of the filament: the reel's nozzle.
func root() -> Vector3:
	if _emitter and _emitter.is_inside_tree():
		return _emitter.global_position
	var cam: Camera3D = player.camera()
	return cam.global_position + cam.global_basis * Vector3(0.22, -0.2, -0.45)


## Where the handle points (world).
func aim_dir() -> Vector3:
	var cam: Camera3D = player.camera()
	var b: Basis = cam.global_basis * Basis(Vector3.UP, -_aim.x) * Basis(Vector3.RIGHT, _aim.y)
	return -b.z


func _spawn_filament() -> void:
	pts.resize(cfg.segments + 1)
	_prev.resize(cfg.segments + 1)
	var r: Vector3 = root()
	var d: Vector3 = aim_dir()
	var seg: float = cfg.length / cfg.segments
	for i: int in cfg.segments + 1:
		# Starts bunched at the reel and pays out as the links pull apart.
		pts[i] = r + d * seg * i * 0.15
		_prev[i] = pts[i]
	_live = true
	_line.visible = true
	_bead.visible = true
	_trail.clear()


func _on_active(real: float) -> void:
	var dt: float = minf(real * TimeControl.player_scale_now(), 1.0 / 30.0)
	if dt <= 0.0:
		return
	_steer(dt)
	_simulate(dt)
	_cut(dt)
	_sounds(dt)


func _steer(dt: float) -> void:
	var ok: bool = can_input()
	var held: bool = ok and Input.is_action_pressed(&"aim")
	player.look_frozen = held
	_lash_cd -= dt
	var want_lash: bool = _script_lash or (ok and Input.is_action_just_pressed(&"fire"))
	_script_lash = false
	if want_lash and _lash_t < 0.0 and _lash_cd <= 0.0:
		_lash_t = 0.0
		_lash_dir = -_lash_dir
		_lash_cd = (cfg.lash_time + cfg.lash_recover) / maxf(body.stat(&"melee_speed") if body else 1.0, 0.1)
		Sfx.play_ui(&"mw7_swish", -2.0, 0.08)
		rig.kick_rot.kick(Vector3(0.0, deg_to_rad(14.0) * _lash_dir, deg_to_rad(8.0) * _lash_dir))
	var target: Vector2 = Vector2(deg_to_rad(cfg.rest_aim_deg.x), deg_to_rad(cfg.rest_aim_deg.y))
	var rate: float = swing_rate()
	if _lash_t >= 0.0:
		var span: float = cfg.lash_time / maxf(body.stat(&"melee_speed") if body else 1.0, 0.1)
		_lash_t += dt
		var k: float = clampf(_lash_t / span, 0.0, 1.0)
		var half: float = deg_to_rad(cfg.lash_sweep_deg) * 0.5
		# Wind back to one side, then through the crosshair to the other.
		target = Vector2(lerpf(half, -half, k) * _lash_dir, deg_to_rad(4.0) * sin(k * PI))
		rate = deg_to_rad(cfg.lash_sweep_deg) / span * 1.6
		if _lash_t > span + 0.06:
			_lash_t = -1.0
	elif held:
		var stick: Vector2 = Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.12)
		target = Vector2(stick.x * deg_to_rad(cfg.max_yaw_deg), -stick.y * deg_to_rad(cfg.max_pitch_deg))
	_aim = _aim.move_toward(target, rate * dt)
	# The forearm follows the handle part of the way.
	rig.extra = Transform3D(Basis.from_euler(Vector3(_aim.y * 0.4, -_aim.x * 0.4, 0.0)), Vector3(-_aim.x * 0.06, _aim.y * 0.03, 0.0))


func _simulate(dt: float) -> void:
	var n: int = cfg.segments
	var seg: float = cfg.length / n
	var r: Vector3 = root()
	var d: Vector3 = aim_dir()
	var keep: float = pow(cfg.damping, dt * 60.0)
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	var before: PackedVector3Array = pts.duplicate()
	for i: int in range(1, n + 1):
		var t: float = float(i) / n
		var v: Vector3 = (pts[i] - _prev[i]) * keep
		var p: Vector3 = pts[i] + v + Vector3.DOWN * cfg.gravity * dt * dt
		# The handle drags each link toward the straight line it points along.
		var follow: float = lerpf(cfg.root_follow, cfg.tip_follow, t)
		p += (r + d * seg * i - p) * clampf(follow * dt, 0.0, 1.0)
		pts[i] = p
	_prev = before
	pts[0] = r
	_prev[0] = r
	# The world stops the outer half (floors, walls): sparks where the bead drags.
	_spark_cd -= dt
	for i: int in range(n / 2, n + 1, 2 if n > 8 else 1):
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(_prev[i], pts[i], Ballistics.LAYER_WORLD)
		var res: Dictionary = space.intersect_ray(q)
		if res.is_empty():
			continue
		var nrm: Vector3 = res["normal"]
		var speed: float = pts[i].distance_to(_prev[i]) / dt
		var where: Vector3 = res["position"]
		pts[i] = where + nrm * 0.03
		if speed > cfg.min_cut_speed and _spark_cd <= 0.0:
			_spark_cd = 0.06
			Fx._emit(&"sparks", pts[i], nrm, Color(1.0, 0.85, 0.6, 1.0), 3, 1.0)
			Sfx.play_at(&"mw7_scrape", pts[i], -8.0, 0.2)
	# Every link keeps its length (after the world has had its say).
	for _pass: int in 2:
		for i: int in range(1, n + 1):
			var link: Vector3 = pts[i] - pts[i - 1]
			var l: float = link.length()
			if l > seg:
				pts[i] = pts[i - 1] + link * (seg / l)
	var tip_speed: float = pts[n].distance_to(_prev[n]) / dt
	peak_tip_speed = maxf(peak_tip_speed, tip_speed)


## Hitboxes crossed by fast links: along each link's path this frame and
## along the link itself.
func _cut(dt: float) -> void:
	var n: int = cfg.segments
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	for k: int in _recut.keys():
		_recut[k] -= dt
		if _recut[k] <= 0.0:
			_recut.erase(k)
	var done: int = 0
	for i: int in range(maxi(n / 3, 1), n + 1):
		var motion: Vector3 = pts[i] - _prev[i]
		var speed: float = motion.length() / dt
		if speed < cfg.min_cut_speed:
			continue
		for ray: Array in [[_prev[i], pts[i]], [pts[i - 1], pts[i]]]:
			var a: Vector3 = ray[0]
			var b: Vector3 = ray[1]
			if a.distance_squared_to(b) < 0.0004:
				continue
			var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(a, b, Ballistics.LAYER_HITBOX)
			var res: Dictionary = space.intersect_ray(q)
			if res.is_empty():
				continue
			var collider: Object = res["collider"]
			var part: HitboxPart = collider as HitboxPart
			if part == null or part.target == player:
				continue
			var key: int = part.get_instance_id()
			if _recut.has(key):
				continue
			_recut[key] = cfg.recut_time
			var at: Vector3 = res["position"]
			_land_cut(part, at, motion.normalized(), speed)
			done += 1
			break
		if done >= cfg.max_cuts_per_frame:
			return


func _land_cut(part: HitboxPart, at: Vector3, dir: Vector3, speed: float) -> void:
	cuts += 1
	var k: float = clampf(speed / (cfg.min_cut_speed * 2.5), 0.6, 1.5)
	AugHit.strike(part, weapon, player, at, dir, cut_damage() * k, cfg.impulse, cfg.energy_j * k, DamageInfo.Type.BLADE, true)
	Sfx.play_at(&"mw7_cut", at, 1.0, 0.1)
	rumble(cfg.rumble_cut.x, cfg.rumble_cut.y, cfg.rumble_cut.z)
	TimeControl.hitstop(0.025, 0.25)


func _sounds(dt: float) -> void:
	var n: int = cfg.segments
	var tip_speed: float = pts[n].distance_to(_prev[n]) / dt
	_swish_cd -= dt
	_crack_cd -= dt
	if tip_speed > 26.0 and _swish_cd <= 0.0:
		_swish_cd = 0.22
		Sfx.play_ui(&"mw7_swish", linear_to_db(clampf(tip_speed / 70.0, 0.25, 1.0)), 0.12)
	if tip_speed > 75.0 and _crack_cd <= 0.0:
		_crack_cd = 0.45
		Sfx.play_at(&"mw7_crack", pts[n], 0.0, 0.08)
		Fx._emit(&"sparks", pts[n], Vector3.UP, Color(0.8, 0.95, 1.0, 1.0), 2, 0.6)


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if not rig.visible:
		return
	rig.tick(real, blend, player)
	if state == State.RECOVERING and _live:
		# Reeling in: the filament shortens into the nozzle.
		var r: Vector3 = root()
		for i: int in pts.size():
			pts[i] = pts[i].lerp(r, clampf(real * 14.0, 0.0, 1.0))
		_prev = pts.duplicate()
	if _live:
		_draw(real)


func _draw(real: float) -> void:
	var n: int = pts.size() - 1
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	_bead.global_position = pts[n]
	# The swoosh behind the outer third.
	var sample: TrailPoint = TrailPoint.new()
	sample.tip = pts[n]
	sample.mid = pts[maxi(n - n / 3, 0)]
	_trail.push_front(sample)
	for t: TrailPoint in _trail:
		t.age += real
	while _trail.size() > 12 or (not _trail.is_empty() and _trail[_trail.size() - 1].age > 0.16):
		_trail.pop_back()
	_im.clear_surfaces()
	_im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var core: Color = cfg.filament_color
	for i: int in n:
		var a: Vector3 = pts[i]
		var b: Vector3 = pts[i + 1]
		var side: Vector3 = (b - a).cross(eye - a).normalized()
		if side.length_squared() < 0.0001:
			continue
		# Wider with distance so it stays about a pixel or two across.
		var w: float = cfg.filament_width * (0.5 + 0.08 * eye.distance_to(a))
		for layer: int in 2:
			var s: Vector3 = side * (w * 3.5 if layer == 0 else w) * 0.5
			var col: Color = core * (0.16 if layer == 0 else 0.95)
			for v: Vector3 in [a - s, a + s, b + s, a - s, b + s, b - s]:
				_im.surface_set_color(col)
				_im.surface_add_vertex(v)
	for i: int in _trail.size() - 1:
		var t0: TrailPoint = _trail[i]
		var t1: TrailPoint = _trail[i + 1]
		var tip0: Vector3 = t0.tip
		var tip1: Vector3 = t1.tip
		var speed: float = tip0.distance_to(tip1) / maxf(real, 0.001)
		var alpha: float = clampf(speed / 60.0, 0.0, 1.0) * (1.0 - t0.age / 0.16) * cfg.trail_color.a
		if alpha < 0.01:
			continue
		var col: Color = Color(cfg.trail_color.r, cfg.trail_color.g, cfg.trail_color.b) * alpha
		var m0: Vector3 = t0.mid
		var m1: Vector3 = t1.mid
		for v: Vector3 in [tip0, tip1, m1, tip0, m1, m0]:
			_im.surface_set_color(col)
			_im.surface_add_vertex(v)
	_im.surface_end()
