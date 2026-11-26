class_name PromptCard
extends CanvasLayer
## The card in the top right that the boot camp and the Survival tips use
## (docs/design.md §8.11): a small heading ("BOOT CAMP 3/9", "TIP"), a title,
## a line or two of text, a checklist, and a bar along the bottom. It never
## takes input and never pauses anything: it sits clear of the debug numbers
## (top left), the wave banner (top centre) and the health and ammo (bottom).

const W: float = 420.0
const MARGIN: float = 24.0
## Above the drop screen (44) so a tip can explain it; under the pause menu (50).
const LAYER: int = 46

var heading: String = ""
var title: String = ""
var body: String = ""
## Checklist rows: [text, done].
var checks: Array[Array] = []
## Shown under the checklist in the warning colour (a nudge when stuck).
var hint: String = ""
## 0..1 along the bottom bar (-1 hides it).
var progress: float = -1.0
var accent: Color = RunUi.C_ACCENT

var _panel: PanelContainer
var _heading: Label
var _title: Label
var _body: Label
var _checks: VBoxContainer
var _hint: Label
var _bar: ColorRect
var _bar_back: ColorRect
var _flash: float = 0.0
var _shown: float = 0.0
var _want: bool = false


func _ready() -> void:
	layer = LAYER
	_panel = PanelContainer.new()
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb: StyleBoxFlat = RunUi.box(true, accent)
	sb.bg_color = RunUi.C_GLASS
	_panel.add_theme_stylebox_override("panel", sb)
	add_child(_panel)
	var v: VBoxContainer = VBoxContainer.new()
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_theme_constant_override("separation", 4)
	_panel.add_child(v)
	_heading = RunUi.label("", 13, accent)
	v.add_child(_heading)
	_title = RunUi.label("", 24, RunUi.C_TEXT)
	_title.add_theme_font_override("font", RunUi.title_font())
	v.add_child(_title)
	_body = RunUi.label("", 16, RunUi.C_TEXT, true)
	_body.custom_minimum_size = Vector2(W - 46.0, 0)
	v.add_child(_body)
	_checks = VBoxContainer.new()
	_checks.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_checks.add_theme_constant_override("separation", 1)
	v.add_child(_checks)
	_hint = RunUi.label("", 14, RunUi.C_WARN, true)
	_hint.custom_minimum_size = Vector2(W - 46.0, 0)
	v.add_child(_hint)
	_bar_back = ColorRect.new()
	_bar_back.color = Color(RunUi.C_DIM.r, RunUi.C_DIM.g, RunUi.C_DIM.b, 0.25)
	_bar_back.custom_minimum_size = Vector2(0, 4)
	_bar_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(_bar_back)
	_bar = ColorRect.new()
	_bar.color = accent
	_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bar_back.add_child(_bar)
	_panel.modulate.a = 0.0
	refresh()


## Shows the card with what's set now (fades in if it was hidden).
func present() -> void:
	_want = true
	refresh()


func dismiss() -> void:
	_want = false


func is_presented() -> bool:
	return _want


## A brief glow on the border (a step done, a tick on the checklist).
func flash() -> void:
	_flash = 1.0


func refresh() -> void:
	if _panel == null:
		return
	_heading.text = heading
	_heading.add_theme_color_override("font_color", accent)
	_title.text = title
	_body.text = body
	_body.visible = body != ""
	# One row per check: done in the accent, still to do in white.
	while _checks.get_child_count() < checks.size():
		_checks.add_child(RunUi.label("", 16, RunUi.C_TEXT, true))
	for i: int in _checks.get_child_count():
		var row: Label = _checks.get_child(i) as Label
		row.visible = i < checks.size()
		if not row.visible:
			continue
		var done: bool = checks[i][1]
		var text: String = checks[i][0]
		row.text = ("✓  " if done else "○  ") + text
		row.add_theme_color_override("font_color", accent if done else RunUi.C_TEXT)
	_checks.visible = not checks.is_empty()
	_hint.text = hint
	_hint.visible = hint != ""
	_bar_back.visible = progress >= 0.0
	_bar.color = accent


func _process(delta: float) -> void:
	var vp: Vector2 = get_viewport().get_visible_rect().size
	_panel.size = Vector2(W, 0)
	_panel.position = Vector2(vp.x - W - MARGIN, MARGIN)
	_shown = move_toward(_shown, 1.0 if _want else 0.0, delta * 4.0)
	_panel.modulate.a = _shown
	_panel.visible = _shown > 0.001
	if progress >= 0.0:
		_bar.size = Vector2(_bar_back.size.x * clampf(progress, 0.0, 1.0), 4.0)
	if _flash > 0.0:
		_flash = maxf(0.0, _flash - delta * 2.0)
	var sb: StyleBoxFlat = _panel.get_theme_stylebox("panel") as StyleBoxFlat
	if sb:
		sb.bg_color = RunUi.C_GLASS.lerp(Color(accent.r * 0.4, accent.g * 0.4, accent.b * 0.4, 0.9), _flash)
		sb.border_color = accent.lerp(Color.WHITE, _flash * 0.6)
