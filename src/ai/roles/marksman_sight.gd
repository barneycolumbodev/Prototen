class_name MarksmanSight
extends RefCounted
## The Marksman's tell (docs/design.md §8.8d): before every shot a red laser
## from his scope finds the operative and a glint flashes off the lens. The
## laser follows him (only so fast) and stops `lock_time` before the shot:
## a step sideways then, or into cover, and the round goes where he was.
## Out of sight, the aim is lost and starts again. The round itself is a
## Type 79's 7.62x54R, made to count (WeaponData.player_damage_scale).
## After `shots_per_spot` shots from one place he moves.

var e: Enemy
var mcfg: MarksmanConfig
var aiming: bool = false
var locked: bool = false
var shots: int = 0
var _t: float = 0.0
var _aim_at: Vector3 = Vector3.INF
var _laser: MeshInstance3D
var _laser_mat: StandardMaterial3D
var _glint: MeshInstance3D
var _glint_mat: StandardMaterial3D
var _from_spot: int = 0


func _init(enemy: Enemy) -> void:
	e = enemy
	mcfg = enemy.config.marksman


func build() -> void:
	_laser = MeshInstance3D.new()
	_laser.name = "Laser"
	_laser.top_level = true
	var cyl: CylinderMesh = CylinderMesh.new()
	cyl.top_radius = 1.0
	cyl.bottom_radius = 1.0
	cyl.height = 1.0
	cyl.radial_segments = 5
	cyl.rings = 1
	cyl.cap_top = false
	cyl.cap_bottom = false
	_laser.mesh = cyl
	_laser_mat = StandardMaterial3D.new()
	_laser_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_laser_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_laser_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_laser_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_laser_mat.albedo_color = Color(mcfg.laser_color, 0.0)
	_laser.material_override = _laser_mat
	_laser.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_laser.visible = false
	e.add_child(_laser)
	_glint = MeshInstance3D.new()
	_glint.name = "Glint"
	_glint.top_level = true
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2.ONE
	_glint.mesh = q
	_glint_mat = StandardMaterial3D.new()
	_glint_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_glint_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_glint_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_glint_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	_glint_mat.no_depth_test = false
	_glint_mat.albedo_texture = preload("res://assets/gore/mist.png")
	_glint_mat.albedo_color = Color(mcfg.glint_color, 0.0)
	_glint.material_override = _glint_mat
	_glint.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_glint.visible = false
	e.add_child(_glint)


## Called instead of firing straight away (Enemy._try_fire). Returns true on
## the frame the shot should go, with `target()` where it goes.
func update(p: Player, delta: float, can_aim: bool) -> bool:
	if not can_aim or p == null:
		cancel()
		return false
	var want: Vector3 = p.camera().global_position - Vector3.UP * 0.25
	if not aiming:
		aiming = true
		locked = false
		_t = 0.0
		_aim_at = want + Vector3(randf_range(-1, 1), randf_range(-0.5, 0.5), randf_range(-1, 1))
		Sfx.play_at(&"m14_slide_release", e.body.chest_position(), -10.0, 0.05)
	_t += delta
	locked = _t >= mcfg.aim_time - mcfg.lock_time
	if not locked:
		# The dot drifts after him at track_deg.
		var origin: Vector3 = _scope()
		var cur: Vector3 = (_aim_at - origin).normalized()
		var tgt: Vector3 = (want - origin).normalized()
		var ang: float = cur.angle_to(tgt)
		var step: float = deg_to_rad(mcfg.track_deg) * delta
		var dist: float = origin.distance_to(want)
		if ang > 0.0001:
			var axis: Vector3 = cur.cross(tgt).normalized()
			if axis.length() > 0.5:
				cur = cur.rotated(axis, minf(step, ang))
		_aim_at = origin + cur * dist
	_draw(clampf(_t / mcfg.aim_time, 0.0, 1.0))
	if _t >= mcfg.aim_time:
		aiming = false
		shots += 1
		_from_spot += 1
		_hide()
		return true
	return false


## Where the shot goes (the locked aim point).
func target() -> Vector3:
	return _aim_at


## Moved on from this spot (shots_per_spot reached): Enemy picks new cover.
func wants_to_move() -> bool:
	if _from_spot >= mcfg.shots_per_spot:
		_from_spot = 0
		return true
	return false


func cancel() -> void:
	aiming = false
	locked = false
	_hide()


func _hide() -> void:
	if _laser:
		_laser.visible = false
	if _glint:
		_glint.visible = false


func _scope() -> Vector3:
	if e.body.gun:
		return e.body.gun.global_transform * mcfg.scope_front
	return e.body.head_position()


func _draw(k: float) -> void:
	var from: Vector3 = _scope()
	var dir: Vector3 = (_aim_at - from).normalized()
	var end: Vector3 = from + dir * 250.0
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, end, Ballistics.LAYER_WORLD | Ballistics.LAYER_PLAYER | Ballistics.LAYER_PROPS)
	var res: Dictionary = e.get_world_3d().direct_space_state.intersect_ray(q)
	if not res.is_empty():
		end = res["position"]
	var length: float = from.distance_to(end)
	if length > 0.2:
		_laser.visible = true
		var y: Vector3 = dir
		var x: Vector3 = y.cross(Vector3.UP if absf(y.y) < 0.95 else Vector3.RIGHT).normalized()
		var z: Vector3 = x.cross(y).normalized()
		var w: float = 0.004 + 0.004 * k
		_laser.global_transform = Transform3D(Basis(x * w, y * length, z * w), (from + end) * 0.5)
		var a: float = (0.25 + 0.55 * k) * (1.0 if locked else 0.75 + 0.25 * sin(_t * 30.0))
		_laser_mat.albedo_color = Color(mcfg.laser_color.lerp(Color(1, 1, 1), 0.25 * k), a)
	# The glint: strongest looking straight down the scope, kept a readable size with distance.
	var p: Player = e.squad.player() if e.squad else null
	if p:
		var cam: Vector3 = p.camera().global_position
		var to_cam: Vector3 = (cam - from).normalized()
		var facing: float = clampf((dir.dot(to_cam) - 0.85) / 0.15, 0.0, 1.0)
		var d: float = from.distance_to(cam)
		_glint.visible = facing > 0.0
		_glint.global_position = from + to_cam * 0.05
		_glint.scale = Vector3.ONE * mcfg.glint_size * maxf(d * 0.12, 1.0) * (0.6 + 0.6 * k)
		var flick: float = 0.75 + 0.25 * sin(_t * 47.0)
		_glint_mat.albedo_color = Color(mcfg.glint_color * 2.5, facing * flick)
