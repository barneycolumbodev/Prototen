class_name AugmentHud
extends CanvasLayer
## Charge bars for the active parts, stacked above the health bar: button,
## short name, a bar that drains while the part runs and refills after.
## Bright amber while running, seaglass when ready, dim red when it can't
## start yet.

var augments: Augments
var _view: View


class View:
	extends Control
	var hud: AugmentHud
	var font: Font
	const W: float = 240.0
	const H: float = 6.0
	const ROW: float = 22.0

	func _draw() -> void:
		var parts: Dictionary[int, ActivePart] = hud.augments.parts
		var i: int = 0
		for slot: int in [1, 2, 3]:
			if not parts.has(slot):
				continue
			var p: ActivePart = parts[slot]
			var y: float = -i * ROW
			var running: bool = p.is_running()
			var ready: bool = p.charge >= p.data.min_to_start and p.state == ActivePart.State.IDLE
			var col: Color = Color(1.0, 0.72, 0.3) if running else (Color(0.36, 0.86, 0.78) if ready else Color(0.75, 0.3, 0.25))
			var label: String = "%s  %s" % [Augments.BUTTONS[slot - 1], p.data.display_name.get_slice(" ", 0)]
			draw_string(font, Vector2(0, y - 3), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(col, 0.95))
			draw_rect(Rect2(0, y, W, H), Color(0, 0, 0, 0.45))
			draw_rect(Rect2(0, y, W * p.charge_fraction(), H), Color(col, 0.9))
			# Where it can start again.
			var mx: float = W * p.data.min_to_start / p.data.charge_max
			draw_line(Vector2(mx, y - 1), Vector2(mx, y + H + 1), Color(1, 1, 1, 0.4), 1.0)
			draw_rect(Rect2(0, y, W, H), Color(1, 1, 1, 0.3), false, 1.0)
			i += 1


func _ready() -> void:
	layer = 6
	_view = View.new()
	_view.hud = self
	_view.font = ThemeDB.fallback_font
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_view)


func _process(_delta: float) -> void:
	var vp: Vector2 = get_viewport().get_visible_rect().size
	_view.position = Vector2(26.0, vp.y - 34.0 - 22.0)
	_view.queue_redraw()
