class_name ScreenBlood
extends CanvasLayer
## Blood thrown onto the view (the boss execution, docs/design.md §8.7b): a
## spatter of drops, each a cluster of overlapping blobs, that run down a
## little and fade. Drawn with plain circles on one Control; nothing is kept
## once the last drop has gone.

const LIFE: float = 2.6

class Drop:
	extends RefCounted
	var at: Vector2
	var r: float
	var age: float = 0.0
	var run: float = 0.0
	var run_speed: float = 0.0
	var shade: float = 1.0
	## Satellites: offsets (×r) and radii (×r).
	var bits: PackedVector3Array = PackedVector3Array()

var drops: Array[Drop] = []
var _view: Control


func _ready() -> void:
	layer = 40
	_view = Control.new()
	_view.set_anchors_preset(Control.PRESET_FULL_RECT)
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_view.draw.connect(_draw_drops)
	add_child(_view)


## Throws blood at the view: `amount` 0..1 (a punch ~0.4, the head ~1).
func splash(amount: float, rng: RandomNumberGenerator) -> void:
	var vp: Vector2 = _view.get_viewport_rect().size if _view.is_inside_tree() else Vector2(1280, 720)
	var n: int = 1 + roundi(amount * amount * 12.0 + amount * 3.0)
	# Thrown from the middle of the view, most of it off to the edges.
	for i: int in n:
		var d: Drop = Drop.new()
		var ang: float = rng.randf() * TAU
		var dist: float = 0.15 + pow(rng.randf(), 0.7) * 0.45
		d.at = vp * 0.5 + Vector2(cos(ang) * vp.x, sin(ang) * vp.y) * dist
		d.r = vp.y * rng.randf_range(0.004, 0.02) * (0.5 + amount) * (2.0 if rng.randf() < 0.12 else 1.0)
		d.run_speed = rng.randf_range(0.0, 0.06) * vp.y * (1.0 if d.r > vp.y * 0.015 else 0.2)
		d.shade = rng.randf_range(0.75, 1.0)
		for k: int in rng.randi_range(2, 6):
			var a2: float = rng.randf() * TAU
			d.bits.append(Vector3(cos(a2) * rng.randf_range(0.6, 1.6), sin(a2) * rng.randf_range(0.6, 1.6), rng.randf_range(0.15, 0.5)))
		drops.append(d)
	set_process(true)


func _process(delta: float) -> void:
	var real: float = TimeControl.real_delta(delta)
	var keep: Array[Drop] = []
	for d: Drop in drops:
		d.age += real
		d.run = minf(d.run + d.run_speed * real * (1.0 - d.age / LIFE), d.r * 6.0)
		if d.age < LIFE:
			keep.append(d)
	drops = keep
	_view.queue_redraw()
	if drops.is_empty():
		set_process(false)


func _draw_drops() -> void:
	for d: Drop in drops:
		var fade: float = 1.0 - clampf((d.age - LIFE * 0.45) / (LIFE * 0.55), 0.0, 1.0)
		var wet: float = clampf(1.0 - d.age / 1.2, 0.0, 1.0)
		var c: Color = Color(0.32 + 0.16 * wet, 0.0, 0.0, 0.85 * fade).darkened(1.0 - d.shade)
		_view.draw_circle(d.at, d.r, c)
		for b: Vector3 in d.bits:
			_view.draw_circle(d.at + Vector2(b.x, b.y) * d.r, d.r * b.z, c)
		if d.run > 1.0:
			_view.draw_rect(Rect2(d.at.x - d.r * 0.3, d.at.y, d.r * 0.6, d.run), c)
			_view.draw_circle(d.at + Vector2(0.0, d.run), d.r * 0.35, c)
		# A glint on the wet ones.
		if wet > 0.05:
			_view.draw_circle(d.at + Vector2(-0.3, -0.35) * d.r, d.r * 0.22, Color(1.0, 0.75, 0.7, 0.35 * wet * fade))
