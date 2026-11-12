class_name ArcBolt
extends MeshInstance3D
## A lightning bolt through a list of points (the AD-2 arc projector): a
## jagged core and thinner branches, redrawn every few hundredths of a second
## so it writhes, fading out over `life`. Additive, unshaded, camera-facing
## ribbons. Frees itself.

var points: PackedVector3Array = PackedVector3Array()
var color: Color = Color(0.6, 0.8, 1.0)
var life: float = 0.3
var width: float = 0.05

var _age: float = 0.0
var _redraw: float = 0.0
var _im: ImmediateMesh = ImmediateMesh.new()
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


static func spawn(parent: Node, p_points: PackedVector3Array, p_color: Color, p_life: float = 0.3, p_width: float = 0.05) -> ArcBolt:
	var b: ArcBolt = ArcBolt.new()
	b.points = p_points
	b.color = p_color
	b.life = p_life
	b.width = p_width
	parent.add_child(b)
	return b


func _ready() -> void:
	_rng.randomize()
	top_level = true
	global_transform = Transform3D.IDENTITY
	mesh = _im
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.vertex_color_use_as_albedo = true
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.no_depth_test = false
	material_override = m
	_draw()


func _process(delta: float) -> void:
	_age += TimeControl.real_delta(delta)
	if _age >= life:
		queue_free()
		return
	_redraw -= TimeControl.real_delta(delta)
	if _redraw <= 0.0:
		_redraw = 0.035
		_draw()


func _draw() -> void:
	_im.clear_surfaces()
	if points.size() < 2:
		return
	var cam: Camera3D = get_viewport().get_camera_3d()
	var eye: Vector3 = cam.global_position if cam else Vector3.ZERO
	var fade: float = 1.0 - _age / life
	_im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for i: int in points.size() - 1:
		var a: Vector3 = points[i]
		var b: Vector3 = points[i + 1]
		var path: PackedVector3Array = _jag(a, b, 0.09)
		_ribbon(path, eye, width * (0.6 + 0.4 * fade), Color(color.r, color.g, color.b) * (1.6 * fade))
		_ribbon(path, eye, width * 0.3, Color(1, 1, 1) * fade)
		# A branch that wanders off and dies.
		if path.size() > 4:
			var k: int = _rng.randi_range(1, path.size() - 3)
			var off: Vector3 = Vector3(_rng.randf_range(-1, 1), _rng.randf_range(-0.3, 1), _rng.randf_range(-1, 1)) * a.distance_to(b) * 0.18
			_ribbon(_jag(path[k], path[k] + off, 0.2), eye, width * 0.35, Color(color.r, color.g, color.b) * fade)
	_im.surface_end()


func _jag(a: Vector3, b: Vector3, amount: float) -> PackedVector3Array:
	var out: PackedVector3Array = PackedVector3Array()
	var dist: float = a.distance_to(b)
	var n: int = clampi(roundi(dist / 0.45), 3, 22)
	for i: int in n + 1:
		var t: float = float(i) / n
		var p: Vector3 = a.lerp(b, t)
		if i > 0 and i < n:
			p += Vector3(_rng.randf_range(-1, 1), _rng.randf_range(-1, 1), _rng.randf_range(-1, 1)) * minf(dist * amount, 0.35) * sin(t * PI)
		out.append(p)
	return out


func _ribbon(path: PackedVector3Array, eye: Vector3, w: float, col: Color) -> void:
	for i: int in path.size() - 1:
		var a: Vector3 = path[i]
		var b: Vector3 = path[i + 1]
		# Thinner close to the eye, so the bolt is about as wide on screen along its whole length.
		var near: float = clampf(eye.distance_to(a.lerp(b, 0.5)) / 8.0, 0.18, 1.3)
		var side: Vector3 = (b - a).cross(eye - a).normalized() * w * 0.5 * near
		if side.length_squared() < 0.0000001:
			continue
		for v: Vector3 in [a - side, a + side, b + side, a - side, b + side, b - side]:
			_im.surface_set_color(col)
			_im.surface_add_vertex(v)
