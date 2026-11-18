class_name BossIntro
extends Node
## The Incense Master's entrance (docs/design.md §8.7a; owner, 2026-11-15:
## "a badass very short cutscene"). About four seconds, letterboxed:
##
## 1. A low camera in the street: he drops out of the sky (off a roof, behind
##    him) and lands in a crouch with the prosthetic driven into the ground.
##    A shockwave of dust, the camera shakes.
## 2. Close on his face from below: he rises and brings the fist up in front
##    of it; the Gauss coils light and whine.
## 3. Wide and low: he spreads his arms and roars. His name comes up.
##
## Then the camera is the operative's again, turned to face him, and the
## fight starts. The operative can't act or be hurt while it plays; the HUD
## is hidden. The landing is picked in front of where the operative is
## looking, on the navmesh, under open sky, in his line of sight
## (`pick_landing`). Real seconds: slow motion doesn't stretch it.

signal finished

var boss: Enemy
var player: Player
## Where he lands; INF picks a spot (pick_landing).
var landing: Vector3 = Vector3.INF
var done: bool = false
var t: float = 0.0

var cfg: BossConfig
var _cam: Camera3D
var _ui: CanvasLayer
var _bars: Array[ColorRect] = []
var _card: Control
var _hidden: Array[CanvasLayer] = []
var _start: Vector3
var _fwd: Vector3
var _side: Vector3
var _yaw: float = 0.0
var _landed: bool = false
var _flexed: bool = false
var _roared: bool = false
var _carded: bool = false
var _shake: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	cfg = boss.config.boss
	if not landing.is_finite():
		landing = pick_landing(player, cfg)
	var to_p: Vector3 = player.global_position - landing
	to_p.y = 0.0
	_fwd = to_p.normalized() if to_p.length() > 0.1 else Vector3.BACK
	_side = _fwd.cross(Vector3.UP).normalized()
	_yaw = atan2(_fwd.x, _fwd.z)
	_start = landing - _fwd * cfg.intro_drop_back + Vector3.UP * cfg.intro_drop_height
	boss.boss.phase = BossBrain.Phase.INTRO
	boss.global_position = _start
	boss.face(_yaw)
	boss.velocity = Vector3.ZERO
	boss.body.play_intro()
	if boss.boss.hw:
		boss.boss.hw.set_glow(cfg.glow_idle * 0.3)
	player.input_enabled = false
	player.invulnerable = true
	player.velocity = Vector3.ZERO
	_cam = Camera3D.new()
	_cam.name = "BossIntroCamera"
	_cam.fov = 55.0
	_cam.far = 400.0
	boss.get_parent().add_child(_cam)
	_cam.make_current()
	for n: Node in get_tree().root.find_children("*", "CanvasLayer", true, false):
		var cl: CanvasLayer = n as CanvasLayer
		if cl and cl.visible:
			cl.visible = false
			_hidden.append(cl)
	_build_ui()
	Sfx.play_ui(&"boss_swing", -2.0, 0.0)


## A spot in front of the operative for him to land: on the navmesh, open to
## the sky, in sight. Tries the middle first, then wider and nearer/farther.
static func pick_landing(p: Player, c: BossConfig) -> Vector3:
	var at: Vector3 = find_landing(p, c)
	if at.is_finite():
		return at
	var fwd: Vector3 = -p.camera().global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized() if fwd.length() > 0.05 else Vector3.FORWARD
	return p.global_position + fwd * minf(c.intro_distance, 8.0)


## A spot in front of the operative with open sky over it to drop onto, in
## view and with room round it; INF if there's none (indoors, a corridor).
static func find_landing(p: Player, c: BossConfig) -> Vector3:
	var fwd: Vector3 = -p.camera().global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized() if fwd.length() > 0.05 else Vector3.FORWARD
	var space: PhysicsDirectSpaceState3D = p.get_world_3d().direct_space_state
	var map: RID = p.get_world_3d().navigation_map
	var eye: Vector3 = p.camera().global_position
	var angles: Array[float] = [0.0]
	var step: float = 15.0
	while step <= c.intro_spread_deg:
		angles.append(step)
		angles.append(-step)
		step += 15.0
	for dist: float in [c.intro_distance, c.intro_distance * 0.8, c.intro_distance * 1.25, c.intro_distance * 0.6]:
		for a: float in angles:
			var cand: Vector3 = p.global_position + fwd.rotated(Vector3.UP, deg_to_rad(a)) * dist
			var at: Vector3 = cand
			if map.is_valid() and NavigationServer3D.map_get_iteration_id(map) > 0:
				at = NavigationServer3D.map_get_closest_point(map, cand)
				if Vector2(at.x - cand.x, at.z - cand.z).length() > 1.5 or absf(at.y - p.global_position.y) > 2.5:
					continue
			if not space.intersect_ray(PhysicsRayQueryParameters3D.create(at + Vector3.UP * 0.3, at + Vector3.UP * c.intro_drop_height, Ballistics.LAYER_WORLD)).is_empty():
				continue
			if not space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, at + Vector3.UP * 1.6, Ballistics.LAYER_WORLD)).is_empty():
				continue
			var roomy: bool = true
			for k: int in 6:
				var d: Vector3 = Vector3.FORWARD.rotated(Vector3.UP, TAU * k / 6.0)
				if not space.intersect_ray(PhysicsRayQueryParameters3D.create(at + Vector3.UP * 1.0, at + Vector3.UP * 1.0 + d * 1.3, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)).is_empty():
					roomy = false
					break
			if roomy:
				return at
	return Vector3.INF


func _process(delta: float) -> void:
	if done:
		return
	var real: float = TimeControl.real_delta(delta)
	t += real
	var fall: float = cfg.intro_fall
	var ct: float = t - fall
	# 1. The drop: along and down, faster as he falls.
	if t < fall:
		var u: float = t / fall
		var at: Vector3 = _start.lerp(landing, u)
		at.y = landing.y + cfg.intro_drop_height * (1.0 - u * u)
		boss.global_position = at
	elif not _landed:
		_land()
	if _landed:
		player.velocity = Vector3.ZERO
		_glow(ct)
		if not _flexed and ct >= 1.05:
			_flexed = true
			Sfx.play_at(&"boss_flex", boss.body.chest_position(), 4.0, 0.02)
		if not _roared and ct >= 1.85:
			_roared = true
			Sfx.play_at(&"boss_roar", boss.body.head_position(), 8.0, 0.0)
			_shake = maxf(_shake, 0.5)
			_rumble(0.4, 0.7, 0.6)
		if not _carded and ct >= 1.95:
			_carded = true
			_show_card()
	_place_camera(real)
	_update_ui(real)
	if t >= cfg.intro_length:
		_end()


func _land() -> void:
	_landed = true
	boss.global_position = landing
	boss.body.set_intro_speed(1.0)
	var pp: Array = boss.boss.pound_point()
	var at: Vector3 = pp[0]
	var n: Vector3 = pp[1]
	boss.boss.shockwave(at, n, cfg.intro_shock_radius, 0.0, 0.0, 3.0, 5.0, player)
	Sfx.play_at(&"boss_land", landing, 8.0, 0.0)
	_shake = 1.3
	_rumble(1.0, 1.0, 0.5)


func _glow(ct: float) -> void:
	var hw: BossHardware = boss.boss.hw
	if hw == null:
		return
	var g: float = cfg.glow_idle * 0.3
	if ct >= 1.05:
		g = lerpf(cfg.glow_idle, cfg.glow_charged, clampf((ct - 1.05) / 0.5, 0.0, 1.0))
	if ct >= 1.85:
		g = lerpf(cfg.glow_flash, cfg.glow_idle * 1.5, clampf((ct - 1.85) / 1.0, 0.0, 1.0))
	hw.set_glow(g)


## The three shots, cut between.
func _place_camera(real: float) -> void:
	var fall: float = cfg.intro_fall
	var ct: float = t - fall
	var head: Vector3 = boss.body.head_position()
	var chest: Vector3 = boss.body.chest_position()
	var pos: Vector3
	var look: Vector3
	if ct < 0.95:
		# Low in the street in front of him, looking up as he comes down.
		pos = landing + _fwd * 6.5 + _side * 2.2 + Vector3.UP * 0.3
		look = chest.lerp(landing + Vector3.UP * 1.2, 0.3)
		# Long lens on him while he's up in the sky, wide once he's down.
		_cam.fov = lerpf(34.0, 58.0, clampf((ct + 0.25) / 0.3, 0.0, 1.0))
	elif ct < 1.8:
		# Close from below on his face and the fist; creeping in.
		var k: float = (ct - 0.95) / 0.85
		pos = head + _fwd * (2.5 - 0.5 * k) - _side * 0.75 + Vector3.DOWN * 0.6
		look = head + Vector3.DOWN * 0.25 - _side * 0.1
		_cam.fov = 42.0
	else:
		# Wide and low for the roar; easing back.
		var k2: float = clampf((ct - 1.8) / 2.0, 0.0, 1.0)
		pos = landing + _fwd * (3.5 + 0.7 * k2) + _side * 1.0 + Vector3.UP * 0.35
		look = chest + Vector3.UP * 0.45
		_cam.fov = 56.0
	_shake = maxf(0.0, _shake - real * (0.8 + _shake * 1.5))
	var s: float = _shake * _shake
	var jitter: Vector3 = Vector3(sin(t * 47.0), sin(t * 39.0 + 1.3), sin(t * 53.0 + 2.1)) * 0.07 * s
	_cam.global_position = pos + jitter
	_cam.look_at(look + jitter * 0.5, Vector3.UP)


# ------------------------------------------------------------------ the frame and the name

func _build_ui() -> void:
	_ui = CanvasLayer.new()
	_ui.layer = 60
	add_child(_ui)
	for k: int in 2:
		var r: ColorRect = ColorRect.new()
		r.color = Color(0, 0, 0, 1)
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_ui.add_child(r)
		_bars.append(r)
	_card = Control.new()
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_card.modulate.a = 0.0
	_ui.add_child(_card)
	var title: Label = RunUi.label(cfg.title, 46, RunUi.C_GOLD)
	title.add_theme_font_override(&"font", RunUi.title_font())
	title.add_theme_color_override(&"font_shadow_color", Color(0, 0, 0, 0.8))
	title.add_theme_constant_override(&"shadow_offset_x", 2)
	title.add_theme_constant_override(&"shadow_offset_y", 2)
	title.name = "Title"
	_card.add_child(title)
	var line: ColorRect = ColorRect.new()
	line.name = "Line"
	line.color = RunUi.C_GOLD
	line.size = Vector2(0, 2)
	_card.add_child(line)
	var sub: Label = RunUi.label(cfg.subtitle, 17, RunUi.C_TEXT)
	sub.name = "Sub"
	sub.add_theme_color_override(&"font_shadow_color", Color(0, 0, 0, 0.8))
	_card.add_child(sub)


func _show_card() -> void:
	Sfx.play_ui(&"wheel_open", -6.0, 0.0)


func _update_ui(real: float) -> void:
	var vp: Vector2 = _ui.get_viewport().get_visible_rect().size if _ui.is_inside_tree() else Vector2(1280, 720)
	var into: float = clampf(t / 0.35, 0.0, 1.0)
	var out: float = clampf((cfg.intro_length - t) / 0.3, 0.0, 1.0)
	var h: float = vp.y * 0.11 * minf(into, out)
	_bars[0].position = Vector2.ZERO
	_bars[0].size = Vector2(vp.x, h)
	_bars[1].position = Vector2(0.0, vp.y - h)
	_bars[1].size = Vector2(vp.x, h)
	if _carded:
		_card.modulate.a = minf(_card.modulate.a + real * 4.0, 1.0) * out
		var title: Label = _card.get_node(^"Title") as Label
		var line: ColorRect = _card.get_node(^"Line") as ColorRect
		var sub: Label = _card.get_node(^"Sub") as Label
		var x0: float = vp.x * 0.07
		var y0: float = vp.y * 0.6
		var slide: float = (1.0 - _card.modulate.a) * 40.0
		title.position = Vector2(x0 - slide, y0)
		line.position = Vector2(x0, y0 + 62.0)
		line.size = Vector2(minf(line.size.x + real * 1400.0, vp.x * 0.42), 2.0)
		sub.position = Vector2(x0 + slide * 0.5, y0 + 72.0)


func _end() -> void:
	done = true
	for cl: CanvasLayer in _hidden:
		if is_instance_valid(cl):
			cl.visible = true
	_hidden.clear()
	if is_instance_valid(player):
		player.camera().make_current()
		var to: Vector3 = boss.body.chest_position() - player.camera().global_position
		player.set_view(atan2(-to.x, -to.z), clampf(atan2(to.y, Vector2(to.x, to.z).length()), -0.3, 0.3))
		player.reset_camera_smoothing()
		player.input_enabled = true
		player.invulnerable = false
	if is_instance_valid(boss) and boss.alive:
		boss.boss.phase = BossBrain.Phase.HUNT
		boss.awareness = 1.0
		boss.last_known = player.global_position if player else boss.last_known
		boss._enter(Enemy.State.COMBAT)
		if boss.boss.hw:
			boss.boss.hw.set_glow(cfg.glow_idle)
	if _cam:
		_cam.queue_free()
	finished.emit()
	queue_free()


func _exit_tree() -> void:
	if not done:
		for cl: CanvasLayer in _hidden:
			if is_instance_valid(cl):
				cl.visible = true
		if is_instance_valid(player):
			player.input_enabled = true
			player.invulnerable = false
		if _cam and is_instance_valid(_cam):
			_cam.queue_free()


func _rumble(weak: float, strong: float, seconds: float) -> void:
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, weak, strong, seconds)
