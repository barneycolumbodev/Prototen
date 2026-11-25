class_name CombatHud
extends CanvasLayer
## Combat layer of the HUD: health, where hits come from, suppression,
## enemy callouts (subtitles), the wave banner and the "down" screen.
## Near the end of a wave the last men are marked: a chevron over each one
## (through walls) and an arrow at the screen edge when he's off screen
## (owner, 2026-11-16; HuntConfig.mark_when_left).

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
var _last_vp: Vector2 = Vector2(-1.0, -1.0)
var _last_boss_vis: bool = false


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
	var burn: float = 0.0
	var _burn_clock: float = 0.0
	var arcs: Array[Vector2] = []  # x = screen angle (0 = ahead/top), y = alpha

	## The edge fade as textures: what STEPS stacked strips of falling alpha
	## add up to (2026-11-12: the 40 strips blended about five full screens
	## of pixels at the phone's native resolution in every fight; four
	## textured strips cover a tenth of that and look the same).
	const STEPS: int = 10
	const PROFILE_TEXELS: int = 64
	## Left, right, top, bottom: each fades from its screen edge inward.
	var _edges: Array[ImageTexture] = []
	var _profile_alpha: float = -1.0
	var _drawn_hurt: float = -1.0
	var _drawn_supp: float = -1.0
	var _drawn_burn: float = -1.0
	var _drawn_size: Vector2 = Vector2(-1.0, -1.0)
	var _drawn_had_arcs: bool = false

	## Redrawn only when something it shows changed (optimization overhaul U-07).
	func redraw_if_changed() -> void:
		var has_arcs: bool = not arcs.is_empty()
		if has_arcs or _drawn_had_arcs or burn > 0.01 or absf(hurt - _drawn_hurt) > 0.002 \
				or absf(suppression - _drawn_supp) > 0.002 or absf(burn - _drawn_burn) > 0.002 or size != _drawn_size:
			_drawn_hurt = hurt
			_drawn_supp = suppression
			_drawn_burn = burn
			_drawn_size = size
			_drawn_had_arcs = has_arcs
			queue_redraw()

	func _draw() -> void:
		var r: Rect2 = get_rect()
		var c: Vector2 = r.size * 0.5
		var flicker: float = 0.8 + 0.2 * sin(_burn_clock * 28.0) if burn > 0.01 else 1.0
		var a: float = clampf(hurt * 0.55 + suppression * 0.25 + burn * 0.5 * flicker, 0.0, 0.85)
		if a > 0.01:
			var col: Color = Color(0.55, 0.0, 0.0, 1.0) if hurt >= suppression * 0.5 else Color(0.0, 0.0, 0.0, 1.0)
			if burn > 0.05:
				var fire_col: Color = Color(1.0, 0.42, 0.06, 1.0)
				col = col.lerp(fire_col, clampf(burn * 0.9, 0.0, 0.92))
			_update_edges(a)
			var w: float = minf(r.size.x, r.size.y) * 0.16
			draw_texture_rect(_edges[0], Rect2(0, 0, w, r.size.y), false, col)
			draw_texture_rect(_edges[1], Rect2(r.size.x - w, 0, w, r.size.y), false, col)
			draw_texture_rect(_edges[2], Rect2(0, 0, r.size.x, w), false, col)
			draw_texture_rect(_edges[3], Rect2(0, r.size.y - w, r.size.x, w), false, col)
		var rad: float = minf(r.size.x, r.size.y) * 0.24
		for arc: Vector2 in arcs:
			var ang: float = arc.x - PI * 0.5
			draw_arc(c, rad, ang - 0.32, ang + 0.32, 18, Color(1.0, 0.18, 0.12, arc.y), 7.0, true)

	## Alpha across a strip (x = 0 at the screen edge, 1 at its inner side)
	## for overall alpha `a`: layer i covered the outer (1 - i/STEPS) of it at
	## a × (1 - i/STEPS) × 0.22, blended over the ones before.
	static func profile(a: float, x: float) -> float:
		var keep: float = 1.0
		for i: int in STEPS:
			var t: float = float(i) / STEPS
			if x < 1.0 - t:
				keep *= 1.0 - a * (1.0 - t) * 0.22
		return 1.0 - keep

	func _update_edges(a: float) -> void:
		if not _edges.is_empty() and absf(a - _profile_alpha) < 0.01:
			return
		_profile_alpha = a
		var n: int = PROFILE_TEXELS
		var imgs: Array[Image] = [Image.create(n, 1, false, Image.FORMAT_RGBA8), Image.create(n, 1, false, Image.FORMAT_RGBA8),
				Image.create(1, n, false, Image.FORMAT_RGBA8), Image.create(1, n, false, Image.FORMAT_RGBA8)]
		for j: int in n:
			var v: Color = Color(1, 1, 1, profile(a, (j + 0.5) / n))
			imgs[0].set_pixel(j, 0, v)
			imgs[1].set_pixel(n - 1 - j, 0, v)
			imgs[2].set_pixel(0, j, v)
			imgs[3].set_pixel(0, n - 1 - j, v)
		if _edges.is_empty():
			for img: Image in imgs:
				_edges.append(ImageTexture.create_from_image(img))
		else:
			for k: int in 4:
				_edges[k].update(imgs[k])


class HealthBar:
	extends Control
	var fraction: float = 1.0
	var shown: float = 1.0
	## A heal (the HV-3's harvest): the bar glows from where it was and fades (1 → 0).
	var heal_glow: float = 0.0
	var heal_from: float = 1.0
	var heal_color: Color = Color(1.0, 0.3, 0.22)
	const W: float = 240.0
	const H: float = 10.0
	var _drawn_frac: float = -1.0
	var _drawn_shown: float = -1.0
	var _drawn_glow: float = -1.0

	## Redrawn only when something it shows changed (optimization overhaul U-07).
	func redraw_if_changed() -> void:
		if absf(fraction - _drawn_frac) > 0.0005 or absf(shown - _drawn_shown) > 0.0005 or absf(heal_glow - _drawn_glow) > 0.01:
			_drawn_frac = fraction
			_drawn_shown = shown
			_drawn_glow = heal_glow
			queue_redraw()

	func healed(from: float) -> void:
		heal_from = minf(from, heal_from) if heal_glow > 0.05 else from
		heal_glow = 1.0

	func _draw() -> void:
		draw_rect(Rect2(0, 0, W, H), Color(0, 0, 0, 0.45))
		draw_rect(Rect2(0, 0, W * shown, H), Color(0.85, 0.25, 0.2, 0.7))
		var col: Color = Color(0.36, 0.86, 0.78) if fraction > 0.35 else Color(1.0, 0.35, 0.3)
		draw_rect(Rect2(0, 0, W * fraction, H), col)
		if heal_glow > 0.0 and fraction > heal_from:
			# What came back, bright, cooling into the bar.
			var g: Color = heal_color.lerp(Color(1, 0.9, 0.85), heal_glow * 0.4)
			g.a = heal_glow
			draw_rect(Rect2(W * heal_from, 0, W * (fraction - heal_from), H), g)
			draw_rect(Rect2(-2, -2, W + 4, H + 4), Color(heal_color, 0.6 * heal_glow), false, 2.0)
		draw_rect(Rect2(0, 0, W, H), Color(1, 1, 1, 0.35), false, 1.0)


## A boss's name and health across the top (docs/design.md §8.7a), and
## the execution prompt when he's down on one knee. Reads the "boss" group.
class BossBar:
	extends Control
	const W_SHARE: float = 0.46
	var boss: Enemy
	var shown: float = 1.0
	var font: Font
	var t: float = 0.0

	func step(delta: float) -> void:
		t += delta
		if boss == null or not is_instance_valid(boss) or not boss.is_in_group(&"boss"):
			boss = get_tree().get_first_node_in_group(&"boss") as Enemy
		visible = boss != null and boss.boss != null and boss.boss.phase != BossBrain.Phase.INTRO
		if not visible:
			return
		var f: float = boss.boss.health_fraction()
		shown = move_toward(shown, f, delta * 0.35) if shown > f else f
		queue_redraw()

	func _draw() -> void:
		if boss == null or boss.boss == null:
			return
		var vp: Vector2 = get_viewport_rect().size
		var b: BossBrain = boss.boss
		var w: float = vp.x * W_SHARE
		var x0: float = (vp.x - w) * 0.5
		var y0: float = 40.0
		var gold: Color = Color(1.0, 0.82, 0.42)
		draw_string(font, Vector2(x0 + 1.0, 33.0), b.cfg.title, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(0, 0, 0, 0.7))
		draw_string(font, Vector2(x0, 32.0), b.cfg.title, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, gold)
		var f: float = b.health_fraction()
		draw_rect(Rect2(x0 - 2.0, y0 - 2.0, w + 4.0, 14.0), Color(0, 0, 0, 0.55))
		draw_rect(Rect2(x0, y0, w * shown, 10.0), Color(0.85, 0.25, 0.2, 0.75))
		var col: Color = Color(1.0, 0.42, 0.18) if b.enraged else gold
		draw_rect(Rect2(x0, y0, w * f, 10.0), col)
		# Notches every tenth, and the rage mark.
		for k: int in range(1, 10):
			draw_line(Vector2(x0 + w * k / 10.0, y0), Vector2(x0 + w * k / 10.0, y0 + 10.0), Color(0, 0, 0, 0.35), 1.0)
		var rx: float = x0 + w * b.cfg.rage_at
		draw_line(Vector2(rx, y0 - 3.0), Vector2(rx, y0 + 13.0), Color(1.0, 0.5, 0.3, 0.9), 2.0)
		draw_rect(Rect2(x0 - 2.0, y0 - 2.0, w + 4.0, 14.0), Color(1, 1, 1, 0.3), false, 1.0)
		var tag: String = ""
		if b.is_down():
			tag = "ON HIS KNEES"
		elif b.phase == BossBrain.Phase.STAGGER:
			tag = "STAGGERED"
		elif b.enraged:
			tag = "ENRAGED"
		if tag != "":
			var a: float = 0.6 + 0.4 * sin(t * 6.0)
			draw_string(font, Vector2(x0, y0 + 30.0), tag, HORIZONTAL_ALIGNMENT_RIGHT, w, 13, Color(1.0, 0.55, 0.35, a))
		var ex: BossExecution = b.execution
		if ex and ex.prompt and not ex.running:
			# The prompt, under the crosshair.
			var cy: float = vp.y * 0.62
			var label: String = "EXECUTE"
			var tw: float = font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 22).x
			var bw: float = 46.0
			var total: float = bw + 12.0 + tw
			var cx: float = (vp.x - total) * 0.5
			var pulse: float = 0.75 + 0.25 * sin(t * 8.0)
			draw_rect(Rect2(cx, cy - 20.0, bw, 28.0), Color(0, 0, 0, 0.6))
			draw_rect(Rect2(cx, cy - 20.0, bw, 28.0), Color(gold, pulse), false, 2.0)
			draw_string(font, Vector2(cx, cy + 1.0), "RB", HORIZONTAL_ALIGNMENT_CENTER, bw, 18, Color(gold, pulse))
			draw_string(font, Vector2(cx + bw + 13.0, cy + 3.0), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0, 0, 0, 0.7))
			draw_string(font, Vector2(cx + bw + 12.0, cy + 2.0), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(1, 1, 1, pulse))


var _boss_bar: BossBar


## Marks the last hostiles of a wave: a chevron and the distance over each
## one on screen, an arrow on the screen edge pointing at each one off it.
class HostileMarker:
	extends Control
	const MARGIN: float = 70.0
	const COLOR: Color = Color(1.0, 0.16, 0.12)
	const TEXT: Color = Color(1.0, 0.94, 0.9)
	var cam: Camera3D
	var targets: Array[Enemy] = []
	var font: Font
	var t: float = 0.0

	## Where the marker for `e` goes: [screen point, on screen, edge direction].
	func place(e: Enemy, vp: Vector2) -> Array:
		var at: Vector3 = e.body.head_position() + Vector3.UP * 0.45
		var local: Vector3 = cam.global_transform.affine_inverse() * at
		var sp: Vector2 = cam.unproject_position(at)
		var inner: Rect2 = Rect2(Vector2(MARGIN, MARGIN), vp - Vector2(MARGIN, MARGIN) * 2.0)
		if local.z < -0.1 and inner.has_point(sp):
			return [sp, true, Vector2.ZERO]
		var dir: Vector2 = Vector2(local.x, -local.y)
		if local.z > -0.1:
			# Behind him: the arrow goes to the bottom edge, on his side.
			dir = Vector2(local.x, maxf(-local.y, 0.0) + local.z * 0.8)
		if dir.length_squared() < 0.0001:
			dir = Vector2(0.0, 1.0)
		dir = dir.normalized()
		var half: Vector2 = vp * 0.5 - Vector2(MARGIN, MARGIN)
		var kx: float = half.x / absf(dir.x) if absf(dir.x) > 0.0001 else INF
		var ky: float = half.y / absf(dir.y) if absf(dir.y) > 0.0001 else INF
		return [vp * 0.5 + dir * minf(kx, ky), false, dir]

	func _draw() -> void:
		if cam == null:
			return
		var vp: Vector2 = get_viewport_rect().size
		var pulse: float = 0.85 + 0.15 * sin(t * 6.0)
		var col: Color = Color(COLOR, pulse)
		var shade: Color = Color(0, 0, 0, 0.75)
		for e: Enemy in targets:
			if not is_instance_valid(e) or not e.alive:
				continue
			var where: Array = place(e, vp)
			var pos: Vector2 = where[0]
			var dist: String = "%d m" % roundi(cam.global_position.distance_to(e.global_position))
			var tw: float = font.get_string_size(dist, HORIZONTAL_ALIGNMENT_LEFT, -1, FONT).x
			var on_screen: bool = where[1]
			if on_screen:
				# A chevron over his head, bobbing, with the distance above it.
				var s: float = 17.0
				var tip: Vector2 = pos + Vector2(0.0, sin(t * 4.0) * 4.0)
				var pts: PackedVector2Array = PackedVector2Array([tip + Vector2(-s, -s * 1.5), tip + Vector2(0.0, -s * 0.9), tip + Vector2(s, -s * 1.5), tip])
				_shape(pts, col, shade)
				_label(dist, tip + Vector2(-tw * 0.5, -s * 1.5 - 10.0), col, shade)
			else:
				# An arrow on the screen edge pointing at him, the distance inside it.
				var dir: Vector2 = where[2]
				var perp: Vector2 = Vector2(-dir.y, dir.x)
				var tip2: Vector2 = pos + dir * 26.0
				var arrow: PackedVector2Array = PackedVector2Array([tip2, pos - dir * 12.0 + perp * 22.0, pos - dir * 3.0, pos - dir * 12.0 - perp * 22.0])
				_shape(arrow, col, shade)
				var label_at: Vector2 = pos - dir * 44.0 + Vector2(-tw * 0.5, FONT * 0.35)
				_label(dist, label_at, col, shade)

	const FONT: int = 22

	func _shape(pts: PackedVector2Array, col: Color, shade: Color) -> void:
		var ring: PackedVector2Array = pts.duplicate()
		ring.append(pts[0])
		draw_polyline(ring, shade, 6.0, true)
		draw_colored_polygon(pts, col)
		draw_polyline(ring, Color(TEXT, col.a), 2.0, true)

	func _label(text: String, at: Vector2, col: Color, shade: Color) -> void:
		draw_string_outline(font, at, text, HORIZONTAL_ALIGNMENT_LEFT, -1, FONT, 6, shade)
		draw_string(font, at, text, HORIZONTAL_ALIGNMENT_LEFT, -1, FONT, Color(TEXT, col.a))


var _marker: HostileMarker
var _hunt: HuntConfig = preload("res://data/enemies/hunt.tres")
var _left: int = 0
var _scan: float = 0.0


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
	_boss_bar = BossBar.new()
	_boss_bar.font = ThemeDB.fallback_font
	_boss_bar.set_anchors_preset(Control.PRESET_FULL_RECT)
	_boss_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_boss_bar.visible = false
	_root.add_child(_boss_bar)
	_marker = HostileMarker.new()
	_marker.font = ThemeDB.fallback_font
	_marker.set_anchors_preset(Control.PRESET_FULL_RECT)
	_marker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_marker)
	EventBus.callout.connect(_on_callout)
	EventBus.player_damaged.connect(_on_damaged)
	EventBus.player_died.connect(func() -> void: _down.visible = true)
	EventBus.wave_changed.connect(_on_wave)
	EventBus.score_changed.connect(_on_score)


## A heal (not the slow regen): the bar glows over what came back.
func _on_healed(amount: float) -> void:
	_health.healed(player.health_fraction() - amount / maxf(player.max_health(), 1.0))


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
	_boss_bar.step(delta)
	var vp: Vector2 = _root.get_viewport_rect().size
	if vp != _last_vp or _boss_bar.visible != _last_boss_vis:
		_last_vp = vp
		_last_boss_vis = _boss_bar.visible
		_health.position = Vector2(26.0, vp.y - 34.0)
		_callouts.position = Vector2(vp.x * 0.5 - 320.0, vp.y - 170.0)
		_callouts.size = Vector2(640.0, 120.0)
		# Under the boss's bar while he's up.
		var drop: float = 52.0 if _boss_bar.visible else 0.0
		_wave.position = Vector2(0, 54 + drop)
		_wave.size = Vector2(vp.x, 40)
		_wave_sub.position = Vector2(0, 90 + drop)
		_wave_sub.size = Vector2(vp.x, 24)
		_down.position = Vector2(0, vp.y * 0.42)
		_down.size = Vector2(vp.x, 50)
	if player:
		if not player.healed.is_connected(_on_healed):
			player.healed.connect(_on_healed)
		_health.fraction = player.health_fraction()
		_health.heal_glow = maxf(_health.heal_glow - delta * 0.9, 0.0)
		# The damage trail falls slowly; a heal fills it at once.
		_health.shown = move_toward(_health.shown, _health.fraction, delta * 0.4) if _health.shown > _health.fraction else _health.fraction
		_vignette.hurt = clampf(1.0 - player.health_fraction() * 1.4, 0.0, 1.0)
		_vignette.suppression = player.suppression
		_vignette.burn = player.burn_intensity()
		if _vignette.burn > 0.01:
			_vignette._burn_clock += delta
		if not player.dead and _down.visible:
			_down.visible = false
	_health.redraw_if_changed()
	if _banner_time > -999.0:
		_banner_time -= delta
		_wave.modulate.a = clampf(_banner_time, 0.25, 1.0)
	_update_arcs(delta)
	_update_marker(delta)
	if _callouts.get_child_count() > 0:
		for c: Node in _callouts.get_children():
			var l: Label = c as Label
			var age: float = l.get_meta(&"age", 0.0)
			age += delta
			l.set_meta(&"age", age)
			l.modulate.a = clampf((CALLOUT_TIME - age) / 0.5, 0.0, 1.0)
			if age > CALLOUT_TIME:
				l.queue_free()


func _update_arcs(delta: float) -> void:
	if _hits.is_empty():
		if not _vignette.arcs.is_empty():
			_vignette.arcs.clear()
		_vignette.redraw_if_changed()
		return
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
	_vignette.redraw_if_changed()


## The last few of a wave: who to mark.
func _update_marker(delta: float) -> void:
	_scan -= delta
	if _scan <= 0.0:
		_scan = 0.25
		_marker.targets = marked_hostiles()
	_marker.cam = player.camera() if player else null
	_marker.visible = not _marker.targets.is_empty() and _marker.cam != null and not (player and player.dead)
	if _marker.visible:
		_marker.t += delta
		_marker.queue_redraw()


## The men still fighting, once a wave is down to `mark_when_left` or fewer.
func marked_hostiles() -> Array[Enemy]:
	var out: Array[Enemy] = []
	if _left <= 0 or _left > _hunt.mark_when_left:
		return out
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e and e.alive and not e.passive and e.state != Enemy.State.SURRENDER and e.state != Enemy.State.CRAWL:
			out.append(e)
	return out


func marker() -> HostileMarker:
	return _marker


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


## Rolling spawns: a quiet counter instead of the wave banner.
func _on_score(kills: int, hostiles: int) -> void:
	_banner_time = -1000.0
	_left = 0
	_wave.text = ""
	_wave_sub.text = "KILLS %d    HOSTILES %d" % [kills, hostiles]


func _on_wave(wave: int, left: int) -> void:
	_left = left if wave > 0 else 0
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
	elif left <= _hunt.mark_when_left:
		_wave_sub.text = "LAST HOSTILE" if left == 1 else "LAST %d" % left
	else:
		_wave_sub.text = "%d left" % left
