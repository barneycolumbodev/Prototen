class_name WeaponWheelView
extends Control
## The weapon wheel (hold Y). One wedge per gun in the loadout, slot 0 at the
## top and then clockwise (PlayerWeapon.wheel_slot); the right stick
## highlights one, letting go of Y draws it. Each wedge shows the gun's icon
## (WeaponData.icon, rendered from its model by raw_assets/ui/weapon_icons),
## its name and rounds loaded; the centre shows the highlighted gun in full.
## Seaglass like the reticles. Fades in and out in real time (the game is
## slowed while it's open).

const FADE_SEC: float = 0.08
const GAP_RAD: float = 0.035

var weapon: PlayerWeapon
var _open: float = 0.0
var _last_ms: int = 0


func _process(_delta: float) -> void:
	var now: int = Time.get_ticks_msec()
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
	var n: int = weapon.slots.size()
	var r1: float = minf(size.x, size.y) * 0.42
	var r0: float = r1 * 0.46
	var font: Font = ThemeDB.fallback_font
	var sea: Color = ReticleStyle.SEAGLASS
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.02, 0.03, 0.42 * a))
	var step: float = TAU / n
	for i: int in n:
		var mid: float = i * step - PI * 0.5
		var lit: bool = i == weapon.wheel_pick
		var held: bool = i == weapon.current
		var pts: PackedVector2Array = _wedge(c, r0, r1, mid - step * 0.5 + GAP_RAD, mid + step * 0.5 - GAP_RAD)
		var fill: Color = Color(sea.r, sea.g, sea.b, 0.32 * a) if lit else Color(0.02, 0.04, 0.05, 0.62 * a)
		draw_colored_polygon(pts, fill)
		var edge: Color = Color(sea.r, sea.g, sea.b, (0.95 if lit else 0.35) * a)
		pts.append(pts[0])
		draw_polyline(pts, edge, 2.4 if lit else 1.2, true)
		# Icon, name and ammo in the middle of the wedge.
		var dir: Vector2 = Vector2(cos(mid), sin(mid))
		var p: Vector2 = c + dir * (r0 + r1) * 0.5
		var d: WeaponData = weapon.slots[i].data
		var tint: Color = Color(1, 1, 1, a) if lit else Color(0.75, 0.85, 0.85, 0.75 * a)
		var box: Vector2 = Vector2((r1 - r0) * 1.05, (r1 - r0) * 0.42)
		if d.icon:
			var tex_size: Vector2 = d.icon.get_size()
			var k: float = minf(box.x / tex_size.x, box.y / tex_size.y)
			var draw_size: Vector2 = tex_size * k
			draw_texture_rect(d.icon, Rect2(p - draw_size * 0.5 - Vector2(0, 8), draw_size), false, tint)
		var label: String = d.display_name
		var w: float = font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x
		draw_string(font, p + Vector2(-w * 0.5, box.y * 0.5 + 10.0), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, tint)
		var ammo: String = "%d" % weapon.slots[i].mechanism.loaded()
		if held:
			ammo += "  (in hand)"
		var aw: float = font.get_string_size(ammo, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
		draw_string(font, p + Vector2(-aw * 0.5, box.y * 0.5 + 26.0), ammo, HORIZONTAL_ALIGNMENT_LEFT, -1, 12,
				Color(tint.r, tint.g, tint.b, tint.a * 0.8))
	# Centre: the highlighted gun.
	draw_circle(c, r0 * 0.9, Color(0.01, 0.03, 0.04, 0.7 * a), true, -1.0, true)
	draw_arc(c, r0 * 0.9, 0.0, TAU, 64, Color(sea.r, sea.g, sea.b, 0.5 * a), 1.2, true)
	var pick: WeaponData = weapon.slots[clampi(weapon.wheel_pick, 0, n - 1)].data
	_centered(font, c + Vector2(0, -4), pick.display_name, 19, Color(1, 1, 1, a))
	_centered(font, c + Vector2(0, 18), pick.caliber, 13, Color(sea.r, sea.g, sea.b, 0.9 * a))


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
