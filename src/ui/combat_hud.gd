class_name CombatHud
extends CanvasLayer
## Combat layer of the HUD: health, where hits come from, suppression,
## enemy callouts (subtitles), the wave banner and the "down" screen.

const CALLOUT_TIME: float = 2.6
const MAX_CALLOUTS: int = 3
const INDICATOR_TIME: float = 1.4

var player: Player

var _root: Control
var _vignette: Vignette
var _health: HealthBar
var _callouts: VBoxContainer
var _wave: Label
var _wave_sub: Label
var _down: Label
var _hits: Array[Indicator] = []
var _banner_time: float = 0.0


class Indicator:
	extends RefCounted
	var dir: Vector3
	var age: float = 0.0
	var strength: float = 1.0


## Red edges when hurt, darker and tighter when suppressed; hit arcs show
## where rounds came from.
class Vignette:
	extends Control
	var hurt: float = 0.0
	var suppression: float = 0.0
	var arcs: Array[Vector2] = []  # x = screen angle (0 = ahead/top), y = alpha

	func _draw() -> void:
		var r: Rect2 = get_rect()
		var c: Vector2 = r.size * 0.5
		var a: float = clampf(hurt * 0.55 + suppression * 0.25, 0.0, 0.8)
		if a > 0.01:
			var col: Color = Color(0.55, 0.0, 0.0, a) if hurt >= suppression * 0.5 else Color(0.0, 0.0, 0.0, a)
			var steps: int = 10
			for i: int in steps:
				var t: float = float(i) / steps
				var w: float = (1.0 - t) * minf(r.size.x, r.size.y) * 0.16
				var fade: Color = Color(col.r, col.g, col.b, col.a * (1.0 - t) * 0.22)
				draw_rect(Rect2(0, 0, r.size.x, w), fade)
				draw_rect(Rect2(0, r.size.y - w, r.size.x, w), fade)
				draw_rect(Rect2(0, 0, w, r.size.y), fade)
				draw_rect(Rect2(r.size.x - w, 0, w, r.size.y), fade)
		var rad: float = minf(r.size.x, r.size.y) * 0.24
		for arc: Vector2 in arcs:
			var ang: float = arc.x - PI * 0.5
			draw_arc(c, rad, ang - 0.32, ang + 0.32, 18, Color(1.0, 0.18, 0.12, arc.y), 7.0, true)


class HealthBar:
	extends Control
	var fraction: float = 1.0
	var shown: float = 1.0
	const W: float = 240.0
	const H: float = 10.0

	func _draw() -> void:
		draw_rect(Rect2(0, 0, W, H), Color(0, 0, 0, 0.45))
		draw_rect(Rect2(0, 0, W * shown, H), Color(0.85, 0.25, 0.2, 0.7))
		var col: Color = Color(0.36, 0.86, 0.78) if fraction > 0.35 else Color(1.0, 0.35, 0.3)
		draw_rect(Rect2(0, 0, W * fraction, H), col)
		draw_rect(Rect2(0, 0, W, H), Color(1, 1, 1, 0.35), false, 1.0)


func _ready() -> void:
	layer = 5
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_vignette = Vignette.new()
	_vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	_vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_vignette)
	_health = HealthBar.new()
	_health.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_health.size = Vector2(HealthBar.W, HealthBar.H)
	_root.add_child(_health)
	_callouts = VBoxContainer.new()
	_callouts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_callouts.alignment = BoxContainer.ALIGNMENT_END
	_root.add_child(_callouts)
	_wave = _label(30)
	_wave_sub = _label(16)
	_down = _label(40)
	_down.text = "DOWN"
	_down.visible = false
	EventBus.callout.connect(_on_callout)
	EventBus.player_damaged.connect(_on_damaged)
	EventBus.player_died.connect(func() -> void: _down.visible = true)
	EventBus.wave_changed.connect(_on_wave)


func _label(size: int) -> Label:
	var l: Label = Label.new()
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 5)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(l)
	return l


func _process(delta: float) -> void:
	var vp: Vector2 = _root.get_viewport_rect().size
	_health.position = Vector2(26.0, vp.y - 34.0)
	_callouts.position = Vector2(vp.x * 0.5 - 320.0, vp.y - 170.0)
	_callouts.size = Vector2(640.0, 120.0)
	_wave.position = Vector2(0, 54)
	_wave.size = Vector2(vp.x, 40)
	_wave_sub.position = Vector2(0, 90)
	_wave_sub.size = Vector2(vp.x, 24)
	_down.position = Vector2(0, vp.y * 0.42)
	_down.size = Vector2(vp.x, 50)
	if player:
		_health.fraction = player.health_fraction()
		_health.shown = move_toward(_health.shown, _health.fraction, delta * 0.4)
		_vignette.hurt = clampf(1.0 - player.health_fraction() * 1.4, 0.0, 1.0)
		_vignette.suppression = player.suppression
		if not player.dead:
			_down.visible = false
	_health.queue_redraw()
	_banner_time -= delta
	_wave.modulate.a = clampf(_banner_time, 0.25, 1.0) if _banner_time > -999.0 else 1.0
	_update_arcs(delta)
	for c: Node in _callouts.get_children():
		var l: Label = c as Label
		var age: float = l.get_meta(&"age", 0.0)
		age += delta
		l.set_meta(&"age", age)
		l.modulate.a = clampf((CALLOUT_TIME - age) / 0.5, 0.0, 1.0)
		if age > CALLOUT_TIME:
			l.queue_free()


func _update_arcs(delta: float) -> void:
	var cam: Camera3D = player.camera() if player else null
	var arcs: Array[Vector2] = []
	var still: Array[Indicator] = []
	for ind: Indicator in _hits:
		ind.age += delta
		if ind.age > INDICATOR_TIME:
			continue
		still.append(ind)
		if cam:
			var local: Vector3 = cam.global_basis.inverse() * ind.dir
			var ang: float = atan2(local.x, -local.z)
			arcs.append(Vector2(ang, (1.0 - ind.age / INDICATOR_TIME) * clampf(ind.strength, 0.4, 1.0)))
	_hits = still
	_vignette.arcs = arcs
	_vignette.queue_redraw()


func _on_damaged(amount: float, from_dir: Vector3) -> void:
	var ind: Indicator = Indicator.new()
	ind.dir = from_dir.normalized()
	ind.strength = amount / 20.0
	_hits.append(ind)
	if _hits.size() > 6:
		_hits.pop_front()


func _on_callout(speaker: String, text: String, _at: Vector3) -> void:
	var l: Label = Label.new()
	l.text = "%s:  %s" % [speaker, text]
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", 17)
	l.add_theme_color_override("font_color", Color(1.0, 0.86, 0.62))
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 4)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_callouts.add_child(l)
	while _callouts.get_child_count() > MAX_CALLOUTS:
		var old: Node = _callouts.get_child(0)
		_callouts.remove_child(old)
		old.queue_free()


func callout_count() -> int:
	return _callouts.get_child_count()


func _on_wave(wave: int, left: int) -> void:
	if wave <= 0:
		_wave.text = ""
		_wave_sub.text = ""
		return
	if left < 0:
		_wave.text = "WAVE %d" % wave
		_wave_sub.text = "incoming"
		_banner_time = 3.0
	elif left == 0:
		_wave.text = "WAVE %d CLEARED" % wave
		_wave_sub.text = ""
		_banner_time = 3.0
	else:
		_wave_sub.text = "%d left" % left
