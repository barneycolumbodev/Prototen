class_name AugmentHud
extends CanvasLayer
## The active parts above the health bar (owner, 2026-11-07: three actives,
## LB fires the one the D-pad picked). One row per installed part: its
## D-pad direction, short name and charge. The selected row is bright and
## tagged LB; the others are dim. Parts that spend charge per use (the arm
## cannon's rounds) show it as pips instead of a bar.
## Bright amber while running, seaglass when ready, dim red when it can't
## start yet.

var augments: Augments
var _view: View
var _flash: float = 0.0


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
		for slot: int in [3, 2, 1]:
			if not parts.has(slot):
				continue
			var p: ActivePart = parts[slot]
			var sel: bool = slot == hud.augments.selected
			var y: float = -i * ROW
			var running: bool = p.is_running()
			var ready: bool = p.charge >= p.data.min_to_start and p.state == ActivePart.State.IDLE
			var col: Color = Color(1.0, 0.72, 0.3) if running else (Color(0.36, 0.86, 0.78) if ready else Color(0.75, 0.3, 0.25))
			var alpha: float = 0.95 if sel else 0.45
			var x0: float = 0.0
			if sel:
				var pulse: float = hud._flash
				draw_rect(Rect2(-6, y - 17, W + 12, ROW + 2), Color(col, 0.10 + 0.25 * pulse))
				draw_string(font, Vector2(0, y - 3), "LB", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(1, 1, 1, 0.95))
			x0 = 24.0
			var label: String = "%s  %s" % [Augments.SLOT_ARROWS[slot - 1], p.hud_name()]
			draw_string(font, Vector2(x0, y - 3), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(col, alpha))
			var w: float = W - x0
			var pips: int = p.hud_pips()
			if pips > 0:
				var gap: float = 3.0
				var pw: float = (w - gap * (pips - 1)) / pips
				var full: int = floori(p.charge + 0.001)
				for k: int in pips:
					var r: Rect2 = Rect2(x0 + k * (pw + gap), y, pw, H)
					draw_rect(r, Color(0, 0, 0, 0.45))
					if k < full:
						draw_rect(r, Color(col, 0.9 * alpha + 0.05))
					elif k == full:
						draw_rect(Rect2(r.position, Vector2(pw * (p.charge - full), H)), Color(col, 0.35 * alpha))
			else:
				draw_rect(Rect2(x0, y, w, H), Color(0, 0, 0, 0.45))
				draw_rect(Rect2(x0, y, w * p.charge_fraction(), H), Color(col, 0.9 * alpha + 0.05))
				# Where it can start again.
				var mx: float = x0 + w * p.data.min_to_start / p.data.charge_max
				draw_line(Vector2(mx, y - 1), Vector2(mx, y + H + 1), Color(1, 1, 1, 0.4), 1.0)
				draw_rect(Rect2(x0, y, w, H), Color(1, 1, 1, 0.3 if sel else 0.15), false, 1.0)
			i += 1


func _ready() -> void:
	layer = 6
	_view = View.new()
	_view.hud = self
	_view.font = ThemeDB.fallback_font
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_view)


## The D-pad picked a part: pulse its row.
func flash_selection() -> void:
	_flash = 1.0


func _process(delta: float) -> void:
	_flash = maxf(0.0, _flash - TimeControl.real_delta(delta) * 3.0)
	var vp: Vector2 = get_viewport().get_visible_rect().size
	_view.position = Vector2(26.0, vp.y - 34.0 - 22.0)
	_view.queue_redraw()
