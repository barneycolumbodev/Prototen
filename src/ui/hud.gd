extends CanvasLayer
## In-game HUD: spread reticle (sized from the real spread cone plus the
## pellet pattern, hidden when aimed so the iron sights do the work), hit
## markers (white hit, gold headshot, red kill), ammo, the loaded shell type
## (and the one being swapped to), reload bar, the scope view through the
## Saiga's PSO-pattern optic, controller prompt, benchmark status.

var bench: FrameBench
## Set by the level.
var weapon: PlayerWeapon:
	set(w):
		weapon = w
		if w:
			w.ammo_changed.connect(_on_ammo_changed)
			w.weapon_changed.connect(_on_weapon_changed)

var _status: Label
var _pad_notice: Label
var _ammo: Label
var _weapon_name: Label
var _shell: Label
var _name_time: float = 0.0
var _blink: float = 0.0
var _reticle: Reticle
var _scope: ScopeView


## What you see through the 1x PSO-pattern optic: the field of view inside the
## eyepiece, the world outside it dimmed (both eyes open), and the
## illuminated reticle: main chevron, holdover chevrons for 100/200/300 m
## computed from the loaded slug's drop, windage scale, and the stadiametric
## rangefinder curve for a 1.7 m man in the lower left.
class ScopeView:
	extends Control
	var amount: float = 0.0
	var fov_deg: float = 60.0
	var ammo: AmmoData
	const LIT: Color = Color(1.0, 0.32, 0.12)
	const MARKS: Array[float] = [100.0, 200.0, 300.0]
	var _drops: Dictionary[float, float] = {}
	var _drops_for: AmmoData

	func _process(_delta: float) -> void:
		visible = amount > 0.001
		if visible:
			queue_redraw()

	## Pixels below the centre for an angle `rad` below the line of sight.
	func px(rad: float) -> float:
		return tan(rad) / tan(deg_to_rad(fov_deg) * 0.5) * size.y * 0.5

	## Holdover (radians below the line of sight) at `distance` for the loaded slug.
	func holdover(distance: float) -> float:
		if ammo == null:
			return 0.0
		if _drops_for != ammo:
			_drops.clear()
			_drops_for = ammo
		if not _drops.has(distance):
			_drops[distance] = atan(ammo.drop_at(distance) / distance)
		return _drops[distance]

	func _draw() -> void:
		var c: Vector2 = size * 0.5
		var a: float = amount
		var r: float = minf(size.x, size.y) * 0.44
		# Outside the eyepiece: dimmed, not black (1x, both eyes open). Inside: a faint lens tint.
		var far: float = c.length() + 4.0
		draw_arc(c, (r + far) * 0.5, 0.0, TAU, 96, Color(0.0, 0.0, 0.0, 0.62 * a), far - r, true)
		draw_circle(c, r, Color(0.35, 0.22, 0.12, 0.05 * a), true, -1.0, true)
		# Eyepiece rim: rubber, with a thin glint on the upper edge.
		draw_arc(c, r + 7.0, 0.0, TAU, 96, Color(0.02, 0.02, 0.025, 0.95 * a), 14.0, true)
		draw_arc(c, r + 1.0, PI * 1.15, PI * 1.85, 48, Color(0.5, 0.5, 0.55, 0.25 * a), 1.5, true)
		var lit: Color = LIT
		lit.a = a
		var glow: Color = LIT
		glow.a = 0.22 * a
		# Main chevron: the tip is the aim point.
		_chevron(c, 9.0, 10.0, lit, glow, 2.0)
		# Holdover marks at their true drop (small at 1x), numbered in hundreds
		# of metres; the labels step out to the right so they never overlap.
		var font: Font = ThemeDB.fallback_font
		var last: float = 0.0
		for i: int in MARKS.size():
			var y: float = px(holdover(MARKS[i]))
			var h: float = clampf(y - last - 1.5, 2.0, 6.0)
			var tip: Vector2 = c + Vector2(0, y)
			draw_line(tip + Vector2(-16.0, 0), tip + Vector2(-5.0, 0), lit, 1.2, true)
			draw_line(tip + Vector2(5.0, 0), tip + Vector2(16.0, 0), lit, 1.2, true)
			if y > 11.0:
				_chevron(tip, h * 0.85, h, lit, glow, 1.3)
			draw_string(font, tip + Vector2(20.0 + i * 9.0, 4.0), str(i + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, lit)
			last = y
		# Windage scale left and right of the main chevron, ticks every 10 mil.
		var mil: float = px(0.001)
		var gap: float = 20.0
		var reach: float = r * 0.78
		for sx: float in [-1.0, 1.0]:
			draw_line(c + Vector2(sx * gap, 0), c + Vector2(sx * reach, 0), glow, 4.0, true)
			draw_line(c + Vector2(sx * gap, 0), c + Vector2(sx * reach, 0), lit, 1.4, true)
			var k: int = 1
			while gap + k * 10.0 * mil < reach and k < 40:
				var x: float = sx * (k * 10.0 * mil)
				if absf(x) > gap:
					var tall: float = 7.0 if k % 5 == 0 else 4.0
					draw_line(c + Vector2(x, 0), c + Vector2(x, -tall), lit, 1.2, true)
				k += 1
		# Rangefinder: base line and the curve 1.7 m tall at each range, 50 to 300 m.
		var base_y: float = c.y + r * 0.5
		var x0: float = c.x - r * 0.78
		var x1: float = c.x - r * 0.14
		var pts: PackedVector2Array = PackedVector2Array()
		for i: int in 26:
			var d: float = lerpf(50.0, 300.0, i / 25.0)
			var x: float = lerpf(x0, x1, (d - 50.0) / 250.0)
			pts.append(Vector2(x, base_y - px(atan(1.7 / d))))
		draw_polyline(pts, glow, 4.0, true)
		draw_polyline(pts, lit, 1.3, true)
		draw_line(Vector2(x0, base_y), Vector2(x1, base_y), lit, 1.3, true)
		for i: int in 3:
			var x: float = lerpf(x0, x1, (MARKS[i] - 50.0) / 250.0)
			draw_line(Vector2(x, base_y), Vector2(x, base_y + 4.0), lit, 1.2, true)
			draw_string(font, Vector2(x - 3.0, base_y + 16.0), str(i + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, lit)

	func _chevron(tip: Vector2, w: float, h: float, lit: Color, glow: Color, width: float) -> void:
		var pts: PackedVector2Array = PackedVector2Array([tip + Vector2(-w, h), tip, tip + Vector2(w, h)])
		draw_polyline(pts, glow, width + 3.0, true)
		draw_polyline(pts, lit, width, true)


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
			# Four thin ticks whose gap shows the real spread cone, plus a small centre dot.
			var g: float = gap_px
			var l: float = 6.0
			for d: Vector2 in [Vector2.UP, Vector2.DOWN, Vector2.LEFT, Vector2.RIGHT]:
				draw_line(c + d * (g - 0.5), c + d * (g + l + 0.5), shadow, 3.5, true)
				draw_line(c + d * g, c + d * (g + l), col, 1.6, true)
			draw_circle(c, 2.0, shadow, true, -1.0, true)
			draw_circle(c, 1.2, col, true, -1.0, true)
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
	_scope = ScopeView.new()
	_scope.set_anchors_preset(Control.PRESET_FULL_RECT)
	_scope.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_scope.visible = false
	add_child(_scope)
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
	_weapon_name = _make_label(Control.PRESET_BOTTOM_RIGHT, 16)
	_weapon_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_weapon_name.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_weapon_name.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_weapon_name.position.y -= 62
	_shell = _make_label(Control.PRESET_BOTTOM_RIGHT, 16)
	_shell.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_shell.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_shell.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_shell.position.y -= 34
	Input.joy_connection_changed.connect(func(_device: int, _connected: bool) -> void: _update_pad_notice())
	EventBus.target_hit.connect(_on_target_hit)
	_update_pad_notice()


func _process(delta: float) -> void:
	_name_time = maxf(0.0, _name_time - delta)
	_weapon_name.modulate.a = clampf(_name_time, 0.0, 1.0)
	if bench and bench.is_running():
		_status.text = "BENCHMARK %d%%  (don't touch the controller)" % roundi(bench.progress() * 100.0)
	elif not _status.text.is_empty() and not _status.text.begins_with("Benchmark done"):
		_status.text = ""
	if weapon:
		var cam: Camera3D = get_viewport().get_camera_3d()
		if cam:
			_reticle.gap_px = spread_to_pixels(weapon.reticle_spread, cam.fov, _reticle.size.y) + 3.0
			_scope.fov_deg = cam.fov
		_reticle.alpha = clampf(1.0 - weapon.ads_visual() * 2.0, 0.0, 1.0)
		_reticle.reload = weapon.mechanism.reload_progress()
		_scope.amount = weapon.scope_amount()
		_scope.ammo = weapon.magazine_ammo()
		_update_shell(delta)


## Loaded shell type; while a swap is pending, the one coming in (blinking).
func _update_shell(delta: float) -> void:
	var loaded: AmmoData = weapon.chamber_ammo()
	_shell.visible = loaded != null
	if loaded == null:
		return
	var selected: AmmoData = weapon.selected_ammo()
	if weapon.swap_pending() and selected != loaded:
		_blink += delta
		_shell.text = "%s  >  %s" % [loaded.short_name, selected.short_name]
		_shell.modulate = selected.color.lerp(Color.WHITE, 0.35) if fmod(_blink, 0.5) < 0.32 else Color(1, 1, 1, 0.8)
	else:
		_blink = 0.0
		_shell.text = loaded.short_name
		_shell.modulate = loaded.color.lerp(Color.WHITE, 0.35)


## Shell-type text shown (tests).
func shell_text() -> String:
	return _shell.text if _shell.visible else ""


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


func _on_weapon_changed(data: WeaponData) -> void:
	_weapon_name.text = "%s   %s" % [data.display_name, data.caliber]
	_name_time = 2.5


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
