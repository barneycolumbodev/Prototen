extends CanvasLayer
## In-game HUD: spread reticle (sized from the real spread cone, hidden when
## aimed so the iron sights do the work), hit markers (white hit, gold
## headshot, red kill), ammo, reload bar, controller prompt, benchmark status.

var bench: FrameBench
## Set by the level.
var weapon: PlayerWeapon:
	set(w):
		weapon = w
		if w:
			w.ammo_changed.connect(_on_ammo_changed)

var _status: Label
var _pad_notice: Label
var _ammo: Label
var _reticle: Reticle


class Reticle:
	extends Control
	var gap_px: float = 6.0
	var alpha: float = 1.0
	var marker_time: float = 0.0
	var marker_color: Color = Color.WHITE
	var marker_scale: float = 1.0
	var reload: float = 0.0
	const MARKER_SEC: float = 0.28

	func _process(delta: float) -> void:
		marker_time = maxf(0.0, marker_time - delta)
		queue_redraw()

	func _draw() -> void:
		var c: Vector2 = size * 0.5
		var col: Color = Color(1, 1, 1, 0.9 * alpha)
		var shadow: Color = Color(0, 0, 0, 0.5 * alpha)
		if alpha > 0.01:
			var g: float = gap_px
			var l: float = 7.0
			for d: Vector2 in [Vector2.UP, Vector2.DOWN, Vector2.LEFT, Vector2.RIGHT]:
				draw_line(c + d * g + Vector2(1, 1), c + d * (g + l) + Vector2(1, 1), shadow, 2.0)
				draw_line(c + d * g, c + d * (g + l), col, 2.0)
			draw_rect(Rect2(c - Vector2(1, 1), Vector2(2, 2)), col)
		if marker_time > 0.0:
			var k: float = marker_time / MARKER_SEC
			var m: Color = marker_color
			m.a = clampf(k * 1.5, 0.0, 1.0)
			var r0: float = (8.0 + (1.0 - k) * 4.0) * marker_scale
			var r1: float = r0 + 9.0 * marker_scale
			for d: Vector2 in [Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1)]:
				var n: Vector2 = d.normalized()
				draw_line(c + n * r0, c + n * r1, Color(0, 0, 0, m.a * 0.6), 4.0)
				draw_line(c + n * r0, c + n * r1, m, 2.5)
		if reload > 0.0:
			var w: float = 70.0
			var y: float = c.y + 34.0
			draw_rect(Rect2(c.x - w * 0.5, y, w, 4), Color(0, 0, 0, 0.5))
			draw_rect(Rect2(c.x - w * 0.5, y, w * reload, 4), Color(1, 1, 1, 0.85))

	func show_marker(kind: StringName) -> void:
		marker_time = MARKER_SEC
		match kind:
			&"headshot":
				marker_color = Color(1.0, 0.78, 0.25)
				marker_scale = 1.35
			&"kill":
				marker_color = Color(1.0, 0.22, 0.18)
				marker_scale = 1.5
			&"armor":
				marker_color = Color(0.55, 0.75, 1.0)
				marker_scale = 0.9
			_:
				marker_color = Color.WHITE
				marker_scale = 1.0


func _ready() -> void:
	_reticle = Reticle.new()
	_reticle.set_anchors_preset(Control.PRESET_FULL_RECT)
	_reticle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_reticle)
	_status = _make_label(Control.PRESET_CENTER_TOP, 18)
	_pad_notice = _make_label(Control.PRESET_CENTER_BOTTOM, 15)
	_pad_notice.text = "No controller detected. Connect one to play."
	_ammo = _make_label(Control.PRESET_BOTTOM_RIGHT, 26)
	_ammo.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_ammo.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_ammo.grow_vertical = Control.GROW_DIRECTION_BEGIN
	Input.joy_connection_changed.connect(func(_device: int, _connected: bool) -> void: _update_pad_notice())
	EventBus.target_hit.connect(_on_target_hit)
	_update_pad_notice()


func _process(_delta: float) -> void:
	if bench and bench.is_running():
		_status.text = "BENCHMARK %d%%  (don't touch the controller)" % roundi(bench.progress() * 100.0)
	elif not _status.text.is_empty() and not _status.text.begins_with("Benchmark done"):
		_status.text = ""
	if weapon:
		var cam: Camera3D = get_viewport().get_camera_3d()
		if cam:
			_reticle.gap_px = spread_to_pixels(weapon.spread, cam.fov, _reticle.size.y) + 3.0
		_reticle.alpha = clampf(1.0 - weapon.ads_visual() * 2.0, 0.0, 1.0)
		_reticle.reload = weapon.mechanism.reload_progress()


## Half the spread cone in screen pixels (vertical FOV, viewport height).
static func spread_to_pixels(spread_deg: float, fov_deg: float, height_px: float) -> float:
	return tan(deg_to_rad(spread_deg) * 0.5) / tan(deg_to_rad(fov_deg) * 0.5) * height_px * 0.5


func show_bench_done(result: Dictionary) -> void:
	_status.text = "Benchmark done: avg %.1f ms, p95 %.1f ms (%s). Saved; see debug overlay." % [
		result.get("avg_ms", 0.0), result.get("p95_ms", 0.0), result.get("renderer", "")]
	get_tree().create_timer(8.0).timeout.connect(func() -> void: _status.text = "")


func _on_ammo_changed(loaded: int, reserve: int) -> void:
	var res: String = "∞" if weapon and weapon.data.infinite_reserve else str(reserve)
	_ammo.text = "%d  |  %s" % [loaded, res]
	var low: bool = weapon != null and loaded <= weapon.data.magazine_size / 4
	_ammo.add_theme_color_override("font_color", Color(1.0, 0.45, 0.35) if low else Color(0.95, 0.95, 0.95))


func _on_target_hit(kind: StringName, hit: BallisticHit) -> void:
	if hit.shooter and hit.shooter.is_in_group(&"player"):
		_reticle.show_marker(kind)


func _update_pad_notice() -> void:
	_pad_notice.visible = Input.get_connected_joypads().is_empty() and OS.has_feature("mobile")


func _make_label(preset: Control.LayoutPreset, size: int) -> Label:
	var label: Label = Label.new()
	label.set_anchors_and_offsets_preset(preset, Control.PRESET_MODE_KEEP_SIZE, 24)
	label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 4)
	add_child(label)
	return label
