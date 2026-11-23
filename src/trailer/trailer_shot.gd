class_name TrailerShot
extends Node
## One shot of the trailer (docs/trailer.md), rendered with Godot's Movie
## Maker by tools/trailer/render.sh: `--write-movie <png> --fixed-fps 60
## <map scene> -- --trailer=<shot>`. The map loads as in Sandbox with no
## spawns; the shot stages men on their marks and plays the operative with
## the same inputs a controller would give (Input actions, the weapon's and
## parts' script hooks), so everything that happens on screen is the game's
## own simulation. Cinematic shots fly their own cameras instead.
##
## A shot overrides `setup()` (once, after the map is ready) and `step()`
## (every physics frame; `f` counts them from 1). It ends after `length`
## frames, or when it calls `finish()`.

## Physics frames since the shot started.
var f: int = 0
## Frames before the shot quits (a safety net; shots normally call finish()).
var length: int = 600
var map: ChinatownMap
var player: Player
var squad: Squad
var men: Array[Enemy] = []
## The look the operative is being steered to (aim()).
var _aim_target: Vector3 = Vector3.INF
var _aim_rate: float = 10.0
var _held: Dictionary[StringName, int] = {}
var _done: bool = false
var cam: Camera3D


func _ready() -> void:
	process_physics_priority = -100
	process_priority = -100
	seed(1729)
	# Headroom: a fight sums past full scale on the master bus; Movie Maker
	# records that mix, so take it down before it clips (levelled in the edit).
	AudioServer.set_bus_volume_db(0, AudioServer.get_bus_volume_db(0) - 9.0)
	player = map.player
	player.invulnerable = true
	player.aim_assist = null
	squad = Squad.new()
	squad.name = "TrailerSquad"
	map.add_child(squad)
	squad.set_player(player)
	_hide_hud.call_deferred()
	(func() -> void:
		await get_tree().physics_frame
		await get_tree().physics_frame
		setup()
		_started = true).call()


var _started: bool = false


func _physics_process(_delta: float) -> void:
	if not _started or _done:
		return
	f += 1
	for a: StringName in _held.keys():
		_held[a] -= 1
		if _held[a] <= 0:
			Input.action_release(a)
			_held.erase(a)
	step()
	if _aim_target != Vector3.INF:
		_steer(_aim_target, _aim_rate)
	if f >= length:
		finish()


func setup() -> void:
	pass


func step() -> void:
	pass


func finish() -> void:
	if _done:
		return
	_done = true
	print("trailer: %s done at frame %d" % [name, f])
	get_tree().quit()


# ------------------------------------------------------------------ staging

## Blender layout coordinates (x east, y north, z up) to Godot's.
static func bv(x: float, y: float, z: float = 0.0) -> Vector3:
	return Vector3(x, z, -y)


## A triad man on his mark. `kind` is a data/enemies/<kind>.tres config;
## `look` picks which of the photographic men he is.
func spawn(kind: String, pos: Vector3, face_to: Vector3, look: int, passive: bool = true) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % kind) as EnemyConfig
	e.passive = passive
	e.look_seed = look
	squad.add(e)
	map.add_child(e)
	e.global_position = pos
	var d: Vector3 = face_to - pos
	e.face(atan2(d.x, d.z))
	men.append(e)
	return e


## Puts him straight into the fight: aware of the operative, guns up.
func alert(e: Enemy) -> void:
	e.awareness = 1.0
	e.sees_player = true
	e.last_known = player.global_position
	e._enter(Enemy.State.COMBAT)


## One round from his gun at `at` (flash, sound, tracer, the real round).
func enemy_fire(e: Enemy, at: Vector3, error_deg: float = 1.5) -> void:
	if e and e.alive and e.has_gun:
		e._fire_at(at, error_deg)


## The operative's body: these actives (and what they need) on the default
## body, in this D-pad order; the old actives come off.
func loadout(actives: Array[String], extra: Array[String] = []) -> void:
	var lo: BodyLoadout = player.loadout.copy()
	for a: ActivePartData in lo.actives():
		lo.remove(a.id)
	for id: String in extra + actives:
		var data: PartData = LoadoutStore.LIBRARY.find(StringName(id))
		if data == null:
			push_error("trailer: no part %s" % id)
			continue
		lo.install(data)
	player.apply_loadout(lo)
	for slot: int in player.augments.parts:
		var p: ActivePart = player.augments.part(slot)
		if p.is_offline():
			push_error("trailer: %s offline: %s" % [p.data.id, p.offline_reason()])


func part(id: String) -> ActivePart:
	return player.augments.find(StringName(id))


## LB on this part (selects it first, like the D-pad would).
func use_part(id: String) -> void:
	var p: ActivePart = part(id)
	if p == null:
		push_error("trailer: %s not installed" % id)
		return
	player.augments.select(p.slot)
	player.augments.use_selected()


func gun(display_name: String) -> void:
	var w: PlayerWeapon = player.weapon()
	w.select_now(w.index_of(display_name))


## Puts the operative on a mark, looking at `look_at`.
func place_player(pos: Vector3, look_at: Vector3) -> void:
	player.global_position = pos
	player.velocity = Vector3.ZERO
	player.reset_camera_smoothing()
	_aim_target = Vector3.INF
	snap_aim(look_at)


# ------------------------------------------------------------------ the controller

## Holds an action for `frames` physics frames (0 = until release()).
func press(action: StringName, frames: int = 0, strength: float = 1.0) -> void:
	Input.action_press(action, strength)
	if frames > 0:
		_held[action] = frames


func release(action: StringName) -> void:
	Input.action_release(action)
	_held.erase(action)


func tap(action: StringName) -> void:
	press(action, 2)


## The trigger (and the aim trigger) through the weapon's script hook.
func trigger(pull: bool, ads: bool = false) -> void:
	player.weapon().script_input(pull, ads)


## Steers the operative's look toward a point, like a thumb on the right
## stick: an exponential approach at `rate` per second (of real time).
func aim(at: Vector3, rate: float = 10.0) -> void:
	_aim_target = at
	_aim_rate = rate


func stop_aim() -> void:
	_aim_target = Vector3.INF


func snap_aim(at: Vector3) -> void:
	var eye: Vector3 = player.camera().global_position
	var d: Vector3 = at - eye
	player.set_view(atan2(-d.x, -d.z), asin(clampf(d.y / maxf(d.length(), 0.001), -1.0, 1.0)))


func _steer(at: Vector3, rate: float) -> void:
	var eye: Vector3 = player.camera().global_position
	var d: Vector3 = at - eye
	if d.length() < 0.2:
		return
	var want_yaw: float = atan2(-d.x, -d.z)
	var want_pitch: float = asin(clampf(d.y / d.length(), -1.0, 1.0))
	var k: float = 1.0 - exp(-rate / 60.0)
	player.set_view(lerp_angle(player.yaw, want_yaw, k), lerpf(player.pitch, want_pitch, k))


# ------------------------------------------------------------------ cameras

## A cinematic camera (made current). Lens in vertical degrees.
func make_cam(fov: float = 40.0) -> Camera3D:
	var c: Camera3D = Camera3D.new()
	c.fov = fov
	c.near = 0.05
	c.far = 400.0
	map.add_child(c)
	c.make_current()
	cam = c
	return c


static func ease_io(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)


static func ease_out(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return 1.0 - pow(1.0 - t, 3.0)


## Catmull-Rom through `pts` at u in 0..1.
static func path(pts: Array[Vector3], u: float) -> Vector3:
	var n: int = pts.size() - 1
	var x: float = clampf(u, 0.0, 1.0) * n
	var i: int = mini(int(x), n - 1)
	var t: float = x - i
	var p0: Vector3 = pts[maxi(i - 1, 0)]
	var p1: Vector3 = pts[i]
	var p2: Vector3 = pts[i + 1]
	var p3: Vector3 = pts[mini(i + 2, n)]
	var t2: float = t * t
	var t3: float = t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)


## Hand-held drift: small, slow, layered sines (deterministic).
static func handheld(t: float, amount: float) -> Vector3:
	return Vector3(
		sin(t * 1.3) * 0.6 + sin(t * 2.9 + 1.0) * 0.4,
		sin(t * 1.7 + 2.0) * 0.6 + sin(t * 3.7) * 0.3,
		sin(t * 1.1 + 4.0) * 0.5) * amount


# ------------------------------------------------------------------ presentation

## No HUD in the trailer: the crosshair, ammo, the actives' bars, callout
## subtitles and the debug overlay go. Screen effects (dilation, the ram's
## streaks) stay: they aren't HUD.
func _hide_hud() -> void:
	for n: Node in [map.get("_hud"), map.combat_hud, player.augments.hud if player.augments else null,
			get_node_or_null("/root/DebugOverlay")]:
		var cl: CanvasLayer = n as CanvasLayer
		if cl:
			cl.visible = false
			cl.process_mode = Node.PROCESS_MODE_DISABLED if cl == get_node_or_null("/root/DebugOverlay") else cl.process_mode
		elif n is CanvasItem:
			(n as CanvasItem).visible = false
