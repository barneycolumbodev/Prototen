class_name WeaponWheelView
extends Control
## The weapon wheel (hold Y), laid out like GTA V's (owner, 2026-11-20): one
## wedge per category (WeaponData.WheelCategory: pistols at the top, then
## clockwise SMGs, shotguns, rifles, heavy, special; PlayerWeapon.wheel_slot).
## The right stick highlights a category; D-pad left / right scrolls the guns
## in it; letting go of Y draws the gun shown. Each wedge shows its category,
## the gun it would draw (WeaponData.icon, rendered from the model by
## raw_assets/ui/weapon_icons) and a pip per gun in it; categories you carry
## nothing in are dimmed and skipped. The centre shows the highlighted gun in
## full and where it sits in its category. Seaglass like the reticles. Fades in
## and out in real time (the game is slowed while it's open).

const FADE_SEC: float = 0.08
const GAP_RAD: float = 0.035

var weapon: PlayerWeapon
var _open: float = 0.0
var _last_ms: int = 0


func _process(_delta: float) -> void:
	var now: int = TimeControl.now_msec()
	var dt: float = (now - _last_ms) * 0.001 if _last_ms > 0 else 0.0
	_last_ms = now
	var target: float = 1.0 if weapon and weapon.wheel_open else 0.0
	_open = move_toward(_open, target, dt / FADE_SEC)
	visible = _open > 0.001
	if visible:
		queue_redraw()


## 0..1 how far the wheel has faded in (tests).
func amount() -> float:
	return _open


func _draw() -> void:
	if weapon == null or weapon.slots.is_empty():
		return
	var a: float = _open
	var c: Vector2 = size * 0.5
	var n: int = PlayerWeapon.wheel_categories()
	var r1: float = minf(size.x, size.y) * 0.42
	var r0: float = r1 * 0.42
	var font: Font = ThemeDB.fallback_font
	var sea: Color = ReticleStyle.SEAGLASS
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.02, 0.03, 0.42 * a))
	var step: float = TAU / n
	for cat: int in n:
		var mid: float = cat * step - PI * 0.5
		var guns: Array[int] = weapon.wheel_guns(cat)
		var empty: bool = guns.is_empty()
		var lit: bool = cat == weapon.wheel_category and not empty
		var pts: PackedVector2Array = _wedge(c, r0, r1, mid - step * 0.5 + GAP_RAD, mid + step * 0.5 - GAP_RAD)
		var fill: Color = Color(sea.r, sea.g, sea.b, 0.32 * a) if lit else Color(0.02, 0.04, 0.05, (0.35 if empty else 0.62) * a)
		draw_colored_polygon(pts, fill)
		var edge: Color = Color(sea.r, sea.g, sea.b, (0.95 if lit else (0.15 if empty else 0.35)) * a)
		pts.append(pts[0])
		draw_polyline(pts, edge, 2.4 if lit else 1.2, true)
		var dir: Vector2 = Vector2(cos(mid), sin(mid))
		var p: Vector2 = c + dir * (r0 + r1) * 0.5
		var box: Vector2 = Vector2((r1 - r0) * 1.05, (r1 - r0) * 0.38)
		var tint: Color = Color(1, 1, 1, a) if lit else Color(0.75, 0.85, 0.85, (0.3 if empty else 0.75) * a)
		# Category name above the icon.
		var title: String = WeaponData.WHEEL_NAMES[cat]
		_centered(font, p + Vector2(0, -box.y * 0.5 - 14.0), title, 12,
				Color(sea.r, sea.g, sea.b, (1.0 if lit else (0.25 if empty else 0.6)) * a))
		if empty:
			_centered(font, p + Vector2(0, 5), "-", 15, tint)
			continue
		var shown: int = weapon.wheel_pick if lit else weapon.wheel_shown(cat)
		var d: WeaponData = weapon.slots[shown].data
		if d.icon:
			var tex_size: Vector2 = d.icon.get_size()
			var k: float = minf(box.x / tex_size.x, box.y / tex_size.y)
			var draw_size: Vector2 = tex_size * k
			draw_texture_rect(d.icon, Rect2(p - draw_size * 0.5 - Vector2(0, 4), draw_size), false, tint)
		_centered(font, p + Vector2(0, box.y * 0.5 + 12.0), d.display_name, 14, tint)
		# A pip per gun in the category, the one shown lit; arrows when the D-pad can scroll it.
		if guns.size() > 1:
			var gap: float = 9.0
			var x0: float = -gap * (guns.size() - 1) * 0.5
			for g: int in guns.size():
				var at: Vector2 = p + Vector2(x0 + g * gap, box.y * 0.5 + 24.0)
				var on: bool = guns[g] == shown
				draw_circle(at, 2.6 if on else 2.0, Color(sea.r, sea.g, sea.b, (0.95 if on else 0.35) * a), true, -1.0, true)
			if lit:
				var off: float = box.x * 0.5 + 6.0
				_chevron(p + Vector2(-off, -4), -1.0, Color(1, 1, 1, a))
				_chevron(p + Vector2(off, -4), 1.0, Color(1, 1, 1, a))
	# Centre: the highlighted gun, its calibre and rounds, its place in the category.
	draw_circle(c, r0 * 0.9, Color(0.01, 0.03, 0.04, 0.7 * a), true, -1.0, true)
	draw_arc(c, r0 * 0.9, 0.0, TAU, 64, Color(sea.r, sea.g, sea.b, 0.5 * a), 1.2, true)
	var pick_i: int = clampi(weapon.wheel_pick, 0, weapon.slots.size() - 1)
	var pick: WeaponData = weapon.slots[pick_i].data
	_centered(font, c + Vector2(0, -14), pick.display_name, 19, Color(1, 1, 1, a))
	_centered(font, c + Vector2(0, 6), pick.caliber, 13, Color(sea.r, sea.g, sea.b, 0.9 * a))
	var ammo: String = "%d loaded" % weapon.slots[pick_i].mechanism.loaded()
	if pick_i == weapon.current:
		ammo = "in hand"
	_centered(font, c + Vector2(0, 24), ammo, 12, Color(0.8, 0.9, 0.9, 0.8 * a))
	var in_cat: Array[int] = weapon.wheel_guns(weapon.wheel_category)
	if in_cat.size() > 1:
		var hint: String = "D-pad   %d / %d" % [in_cat.find(pick_i) + 1, in_cat.size()]
		_centered(font, c + Vector2(0, 44), hint, 12, Color(sea.r, sea.g, sea.b, 0.85 * a))
		var hw: float = font.get_string_size(hint, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x * 0.5
		_chevron(c + Vector2(-hw - 8.0, 40), -1.0, Color(sea.r, sea.g, sea.b, 0.85 * a))
		_chevron(c + Vector2(hw + 8.0, 40), 1.0, Color(sea.r, sea.g, sea.b, 0.85 * a))


## A small arrow pointing left (side -1) or right (+1).
func _chevron(at: Vector2, side: float, color: Color) -> void:
	var pts: PackedVector2Array = PackedVector2Array([at + Vector2(-side * 4.0, -6.0), at + Vector2(side * 3.0, 0.0),
			at + Vector2(-side * 4.0, 6.0)])
	draw_polyline(pts, color, 2.0, true)


func _centered(font: Font, at: Vector2, text: String, font_size: int, color: Color) -> void:
	var w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	draw_string(font, at - Vector2(w * 0.5, 0), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)


static func _wedge(c: Vector2, r0: float, r1: float, a0: float, a1: float) -> PackedVector2Array:
	var pts: PackedVector2Array = PackedVector2Array()
	var steps: int = 18
	for k: int in steps + 1:
		var ang: float = lerpf(a0, a1, float(k) / steps)
		pts.append(c + Vector2(cos(ang), sin(ang)) * r1)
	for k: int in steps + 1:
		var ang: float = lerpf(a1, a0, float(k) / steps)
		pts.append(c + Vector2(cos(ang), sin(ang)) * r0)
	return pts
