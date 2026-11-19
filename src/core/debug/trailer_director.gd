class_name TrailerDirector
extends Node
## Films one shot of the trailer (`-- --trailer=<shot>`, run with Godot's
## `--write-movie <file.png> --fixed-fps 30`; tools/trailer/render.sh).
## Builds the moment (men, dogs, the boss, a lift), flies a camera or drives
## the operative's gun on a script, hides the HUD, and quits when done.
## Prints "trailer: start <frame>" so the cut can drop the warm-up frames.

const FPS: float = 30.0
const WARM: int = 14

var map: ChinatownMap
var shot: String = ""

var cam: Camera3D
var p: Player
var men: Array[Enemy] = []
var dogs: Array[AttackDog] = []
var fwd: Vector3 = Vector3.FORWARD
var right: Vector3 = Vector3.RIGHT
var length: float = 4.0
var keep_ui: bool = false

var cam_from: Vector3
var cam_to: Vector3
var look_from: Vector3
var look_to: Vector3
var fov_from: float = 50.0
var fov_to: float = 50.0
var shake: float = 0.0

var _frame: int = -1
var _started: bool = false
var _hold: bool = false
var _ads: bool = false
var _taps: int = 0
var _aim_target: Vector3 = Vector3.INF
var _aim_now: Vector3 = Vector3.INF
var _aim_enemy: Enemy
var _aim_zone: StringName = &"chest"
var _aim_ease: float = 1.0
var _ev_t: Array[float] = []
var _ev_cb: Array[Callable] = []
var _drive_gun: bool = false
var _lead_dog_lunged: bool = false
var _aim_only: bool = false
var _lc: LorentzCatcher
var _lc_phase: int = 0
var _fire_acc: float = 0.0
var _shooters: Array[Enemy] = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_physics_priority = -20
	Settings.adaptive.held = true


func _process(_delta: float) -> void:
	_frame += 1
	if _frame == WARM:
		_setup()
		_started = true
		print("trailer: start %d" % _frame)
	if not _started:
		return
	var t: float = float(_frame - WARM) / FPS
	while not _ev_t.is_empty() and _ev_t[0] <= t:
		_ev_t.pop_front()
		var cb: Callable = _ev_cb.pop_front()
		cb.call()
	if shot == "ct_dogs":
		_watch_dogs()
	if shot == "ct_catch":
		_watch_catch()
	if cam and cam.current:
		var u: float = clampf(t / length, 0.0, 1.0)
		var k: float = lerpf(u, u * u * (3.0 - 2.0 * u), 0.55)
		var pos: Vector3 = cam_from.lerp(cam_to, k)
		pos += Vector3(sin(t * 1.9), sin(t * 2.7 + 1.3) * 0.6, sin(t * 1.3 + 0.7)) * shake
		cam.look_at_from_position(pos, look_from.lerp(look_to, k))
		cam.fov = lerpf(fov_from, fov_to, k)
	if not keep_ui:
		_hide_ui(get_tree().root)
	else:
		DebugOverlay.visible = false
	if t >= length:
		print("trailer: end %d" % _frame)
		get_tree().quit()


func _physics_process(delta: float) -> void:
	if not _started or p == null or not (_drive_gun or _aim_only):
		return
	if _lc_phase == 2:
		_fire_acc += delta
		while _fire_acc >= 1.0 / 14.0:
			_fire_acc -= 1.0 / 14.0
			_enemy_volley()
	if _aim_enemy and is_instance_valid(_aim_enemy) and _aim_enemy.body and _aim_enemy.body.hitboxes.has(_aim_zone):
		_aim_target = _aim_enemy.body.hitboxes[_aim_zone].global_position
	if _aim_target != Vector3.INF:
		_aim_now = _aim_target if _aim_now == Vector3.INF else _aim_now.lerp(_aim_target, _aim_ease)
		GunplayDemo.aim_at(p, _aim_now)
	if not _drive_gun:
		return
	var pull: bool = _hold or _taps > 0
	if _taps > 0 and not _hold:
		_taps -= 1
	p.weapon().script_input(pull, _ads)


# ------------------------------------------------------------------ helpers

func _at(t: float, cb: Callable) -> void:
	var i: int = 0
	while i < _ev_t.size() and _ev_t[i] <= t:
		i += 1
	_ev_t.insert(i, t)
	_ev_cb.insert(i, cb)


func _b(x: float, y: float, z: float) -> Vector3:
	return ChinatownMap.b2g([x, y, z])


func _ground(v: Vector3) -> Vector3:
	var at: Vector3 = NavigationServer3D.map_get_closest_point(map.get_world_3d().navigation_map, v)
	if at == Vector3.ZERO or absf(at.y - v.y) > 1.5 or Vector2(at.x - v.x, at.z - v.z).length() > 1.0:
		return v
	return at


func _man(at: Vector3, role: String, passive: bool, face_to: Vector3, look: int = -1) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % role) as EnemyConfig
	e.passive = passive
	if look >= 0:
		e.look_seed = look
	map.add_child(e)
	e.global_position = at
	var to: Vector3 = face_to - at
	e.face(atan2(to.x, to.z))
	men.append(e)
	return e


func _gun(file: String) -> void:
	var w: PlayerWeapon = p.weapon()
	for i: int in w.slots.size():
		if w.slots[i].data.resource_path.get_file() == file:
			w.select_now(i)
			return
	push_warning("trailer: no gun %s" % file)


func _slow(s: float) -> void:
	TimeControl.set_slowmo(s)
	Engine.physics_ticks_per_second = clampi(roundi(60.0 / s), 60, 300)
	Engine.max_physics_steps_per_frame = 16


func _aim(e: Enemy, zone: StringName, ease_k: float = 1.0) -> void:
	_aim_enemy = e
	_aim_zone = zone
	_aim_ease = ease_k


func _tap() -> void:
	_taps = 1


func _new_cam(fov: float) -> void:
	cam = Camera3D.new()
	cam.fov = fov
	cam.far = 400.0
	map.add_child(cam)
	cam.make_current()
	fov_from = fov
	fov_to = fov
	map.atmos.follow(cam)
	if p:
		for c: Node in p.camera().get_children():
			if c is Node3D:
				(c as Node3D).visible = false


func _hide_ui(n: Node) -> void:
	for c: Node in n.get_children():
		if c is BossIntro:
			continue
		if c is CanvasLayer:
			(c as CanvasLayer).visible = false
		_hide_ui(c)


func _player_frame() -> void:
	p = map.player
	p.input_enabled = false
	p.invulnerable = true
	var f: Vector3 = -p.camera().global_basis.z
	f.y = 0.0
	fwd = f.normalized()
	right = fwd.cross(Vector3.UP).normalized()


## Puts the operative in the open street west of the gate, looking east.
func _to_street() -> void:
	p.global_position = _ground(_b(-31.0, 8.0, 0.5))
	var d: Vector3 = _b(0.0, 8.0, 0.0) - _b(-31.0, 8.0, 0.0)
	p.set_view(atan2(-d.x, -d.z), 0.0)
	fwd = d.normalized()
	right = fwd.cross(Vector3.UP).normalized()


# ------------------------------------------------------------------ shots

func _setup() -> void:
	match shot:
		"menu":
			_menu()
		"ct_street":
			_ct_street()
		"ct_slowmo":
			_ct_slowmo()
		"ct_mg":
			_ct_mg()
		"ct_boss":
			_ct_boss()
		"ct_dogs":
			_ct_dogs()
		"ho_atrium":
			_ho_atrium()
		"ho_lift":
			_ho_lift()
		"ho_slagger":
			_ho_slagger()
		"ho_governor":
			_ho_governor()
		"ct_catch":
			_ct_catch()
		_:
			push_error("trailer: unknown shot %s" % shot)


## The operative smoking against the restaurant front, a slow push in.
func _menu() -> void:
	length = 4.5
	var menu: MainMenu = map.menu
	var cfg: MenuSceneConfig = menu.config
	_new_cam(menu.camera.fov)
	var head: Vector3 = cfg.main_cam_target + Vector3.UP * 0.45
	cam_from = cfg.main_cam_position + (cfg.main_cam_position - head).normalized() * 0.7 + Vector3.DOWN * 0.2
	cam_to = cfg.main_cam_position.lerp(head, 0.2) + Vector3.UP * 0.05
	look_from = head + Vector3.DOWN * 0.35
	look_to = head + Vector3.DOWN * 0.12
	fov_from = menu.camera.fov
	fov_to = menu.camera.fov - 3.0
	shake = 0.006


## Chinatown in the rain: a crane down the street, three men waiting.
func _ct_street() -> void:
	length = 4.5
	_player_frame()
	p.global_position = _b(5.0, -30.0, 0.0)
	_new_cam(55.0)
	for v: Vector3 in [_b(-12.0, 7.0, 0.0), _b(-10.5, 8.6, 0.0), _b(-13.2, 9.2, 0.0)]:
		_man(_ground(v + Vector3.UP), "gunman", true, _b(-36.0, 7.0, 0.0), men.size() + 2)
	cam_from = _b(-37.0, 6.5, 7.5)
	cam_to = _b(-27.0, 7.4, 2.4)
	look_from = _b(-2.0, 8.0, 2.0)
	look_to = _b(-9.0, 8.2, 1.4)
	fov_from = 58.0
	fov_to = 44.0
	shake = 0.01


## Slow motion from the side: a head off, a chest through, a leg chewed off.
func _ct_slowmo() -> void:
	length = 5.0
	_player_frame()
	_to_street()
	_drive_gun = true
	var base: Vector3 = p.global_position
	var a: Enemy = _man(_ground(base + fwd * 8.0 + right * 0.6 + Vector3.UP), "gunman", true, base, 3)
	var b: Enemy = _man(_ground(base + fwd * 11.0 - right * 1.0 + Vector3.UP), "enforcer", true, base, 6)
	var c: Enemy = _man(_ground(base + fwd * 14.0 + right * 0.2 + Vector3.UP), "red_pole", true, base, 8)
	_new_cam(40.0)
	var m1: Vector3 = a.global_position
	cam_from = m1 + right * 3.4 - fwd * 2.4 + Vector3.UP * 1.05
	cam_to = m1 + right * 2.7 - fwd * 1.2 + Vector3.UP * 1.3
	look_from = m1 + fwd * 2.5 + Vector3.UP * 1.2
	look_to = m1 + fwd * 3.0 + Vector3.UP * 1.25
	shake = 0.006
	_gun("rail_carbine.tres")
	_aim(a, &"neck")
	_at(0.5, _slow.bind(0.2))
	_at(0.9, _tap)
	_at(1.7, _gun.bind("m14p.tres"))
	_at(1.75, _aim.bind(b, &"chest"))
	_at(2.0, _tap)
	_at(2.8, _gun.bind("mg42.tres"))
	_at(2.85, _aim.bind(c, &"r_thigh"))
	_at(3.0, func() -> void: _hold = true)
	_at(4.1, func() -> void: _hold = false)


## First person: the MG42 hosing a crowd in the street, the HUD gone.
func _ct_mg() -> void:
	length = 3.6
	_player_frame()
	_to_street()
	_drive_gun = true
	var base: Vector3 = p.global_position
	var spots: Array[Vector3] = [fwd * 7.0 - right * 2.2, fwd * 8.5 - right * 0.4, fwd * 7.5 + right * 1.6, fwd * 10.5 + right * 2.6, fwd * 11.0 - right * 1.4]
	var roles: Array[String] = ["gunman", "enforcer", "gunman", "red_pole", "gunman"]
	for i: int in spots.size():
		_man(_ground(base + spots[i] + Vector3.UP), roles[i], true, base, i + 1)
	_gun("mg42.tres")
	_aim(men[0], &"chest", 0.18)
	_at(0.35, func() -> void: _hold = true)
	_at(0.95, _aim.bind(men[1], &"chest", 0.18))
	_at(1.5, _aim.bind(men[2], &"stomach", 0.18))
	_at(2.05, _aim.bind(men[3], &"chest", 0.18))
	_at(2.6, _aim.bind(men[4], &"head", 0.18))
	_at(3.3, func() -> void: _hold = false)


## The Incense Master's entrance, his own cutscene.
func _ct_boss() -> void:
	length = 4.8
	keep_ui = true
	_player_frame()
	var boss: Enemy = Enemy.new()
	boss.config = load("res://data/enemies/incense_master.tres") as EnemyConfig
	boss.look_seed = 5
	map.add_child(boss)
	boss.global_position = p.global_position + fwd * 10.0
	boss.awareness = 1.0
	boss.last_known = p.global_position
	var intro: BossIntro = BossIntro.new()
	intro.boss = boss
	intro.player = p
	map.add_child(intro)


## First person: the pack charges, the lead dog leaps, slow motion, two shots.
func _ct_dogs() -> void:
	length = 6.0
	_player_frame()
	_drive_gun = true
	_gun("pistol_57.tres")
	_ads = true
	var base: Vector3 = p.global_position + fwd * 17.0
	for o: Vector3 in [Vector3.ZERO, right * 1.4 + fwd * 1.6, -right * 1.3 + fwd * 2.8]:
		var d: AttackDog = AttackDog.new()
		d.player = p
		map.add_child(d)
		d.global_position = base + o + Vector3.UP * 0.1
		var to: Vector3 = p.global_position - d.global_position
		d.face(atan2(to.x, to.z))
		dogs.append(d)
	p.set_view(atan2(-fwd.x, -fwd.z), -0.1)
	_aim_target = p.camera().global_position + fwd * 10.0 + Vector3.DOWN * 0.9
	_aim_ease = 0.25


func _watch_dogs() -> void:
	if dogs.is_empty() or _lead_dog_lunged:
		return
	var lead: AttackDog = dogs[0]
	if lead.state == AttackDog.State.LUNGE:
		_lead_dog_lunged = true
		var t: float = float(_frame - WARM) / FPS
		length = t + 3.0
		_slow(0.22)
		_aim_ease = 0.5
		var follow: Callable = func() -> void:
			if is_instance_valid(lead):
				_aim_target = lead.global_position + Vector3.UP * 0.55 + (p.global_position - lead.global_position).normalized() * 0.35
		_at(t + 0.05, follow)
		_at(t + 0.5, follow)
		_at(t + 0.55, _tap)
		_at(t + 1.1, follow)
		_at(t + 1.15, _tap)
		_at(t + 2.2, _slow.bind(1.0))


## The atrium from the gallery: a slow truck along the balustrade.
func _ho_atrium() -> void:
	length = 4.5
	_player_frame()
	_new_cam(60.0)
	cam_from = _b(-18.5, -6.5, 6.2)
	cam_to = _b(-15.0, -8.2, 6.5)
	look_from = _b(8.0, 14.0, 1.5)
	look_to = _b(9.5, 12.5, 1.8)
	fov_from = 62.0
	fov_to = 56.0
	shake = 0.006


## Two cars chime and open; they come out.
func _ho_lift() -> void:
	length = 5.0
	_player_frame()
	var hotel: HotelMap = map as HotelMap
	var look: int = 2
	for li: int in [2, 3]:
		var l: Lift = hotel.lifts[li]
		var along: Vector3 = Vector3.RIGHT
		for s: float in [-0.45, 0.45]:
			_man(l.car_centre + along * s + Vector3.UP * 0.05, "gunman" if s < 0.0 else "enforcer", false, _b(0.0, 15.0, 0.0), look)
			look += 1
		l.call_down()
	_new_cam(48.0)
	cam_from = _b(0.0, 19.5, 0.85)
	cam_to = _b(0.0, 21.8, 1.05)
	look_from = _b(0.0, 27.0, 1.7)
	look_to = _b(0.0, 27.0, 1.45)
	shake = 0.01


## First person: the Slagger charges, lets go, burns through two men.
func _ho_slagger() -> void:
	length = 5.2
	_player_frame()
	_drive_gun = true
	p.global_position = _ground(_b(-4.0, -2.0, 0.5))
	var a: Enemy = _man(_ground(_b(-4.0, 4.0, 0.5)), "enforcer", true, p.global_position, 4)
	_man(_ground(_b(-3.7, 9.0, 0.5)), "gunman", true, p.global_position, 7)
	_gun("slagger.tres")
	_aim(a, &"chest", 0.2)
	_at(0.3, func() -> void: _hold = true)
	_at(3.15, func() -> void: _hold = false)
	_at(3.12, _slow.bind(0.3))
	_at(4.6, _slow.bind(1.0))


## First person, from the hip: the Governor drops a man, the lever throws, the next one.
func _ho_governor() -> void:
	length = 4.0
	_player_frame()
	_drive_gun = true
	p.global_position = _ground(_b(-4.0, -2.0, 0.5))
	var a: Enemy = _man(_ground(_b(-4.3, 3.5, 0.5)), "gunman", true, p.global_position, 9)
	var b: Enemy = _man(_ground(_b(-2.4, 6.0, 0.5)), "red_pole", true, p.global_position, 10)
	_gun("governor.tres")
	_aim(a, &"chest", 0.3)
	_at(0.55, _slow.bind(0.3))
	_at(0.6, _tap)
	_at(1.7, _slow.bind(1.0))
	_at(2.3, _aim.bind(b, &"head", 0.3))
	_at(2.85, _tap)


## First person: the LC-6 catches two men's rounds in slow motion, then throws
## them back down the street.
func _ct_catch() -> void:
	length = 12.0
	_player_frame()
	_to_street()
	var base: Vector3 = p.global_position
	var a: Enemy = _man(_ground(base + fwd * 9.0 - right * 2.4 + Vector3.UP), "gunman", true, base, 3)
	var c: Enemy = _man(_ground(base + fwd * 10.5 + right * 2.2 + Vector3.UP), "enforcer", true, base, 6)
	var b: Enemy = _man(_ground(base + fwd * 15.0 + right * 0.4 + Vector3.UP), "red_pole", true, base, 8)
	_shooters = [a, c]
	var lo: BodyLoadout = p.loadout.copy()
	var data: PartData = LoadoutStore.LIBRARY.find(&"lc6_lorentz_catcher")
	if data:
		lo.install(data)
	p.apply_loadout(lo)
	_aim(b, &"chest", 0.3)
	_aim_only = true


func _watch_catch() -> void:
	var t: float = float(_frame - WARM) / FPS
	match _lc_phase:
		0:
			if t < 0.4:
				return
			_lc = p.augments.find(&"lc6_lorentz_catcher") as LorentzCatcher
			if _lc == null:
				push_error("trailer: LC-6 not installed")
				length = t
				_lc_phase = 9
				return
			p.augments.select(_lc.slot)
			_lc.script_hold(true)
			p.augments.use_selected()
			_lc_phase = 1
		1:
			if _lc.state == ActivePart.State.ACTIVE and _lc.mode == LorentzCatcher.Mode.CATCHING:
				_lc_phase = 2
				_slow(0.4)
		2:
			if _lc.held.size() >= 30 or t > 9.0:
				_lc.script_hold(false)
				_slow(0.3)
				_lc_phase = 3
				length = t + 2.4
				_at(t + 1.7, _slow.bind(1.0))


func _enemy_volley() -> void:
	var eye: Vector3 = p.camera().global_position
	for e: Enemy in _shooters:
		if e == null or not is_instance_valid(e) or not e.alive:
			continue
		var from: Vector3 = e.body.chest_position() + Vector3(0.0, 0.25, 0.0) + (eye - e.global_position).normalized() * 0.6
		var at: Vector3 = eye + Vector3(randf_range(-0.3, 0.3), randf_range(-0.5, 0.15), 0.0)
		Ballistics.fire(e.config.weapon, from, (at - from).normalized(), e, from)
