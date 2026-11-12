class_name PerfProbe
extends Node
## CPU cost probe for the cloud (`-- --perf=<seconds>` on Chinatown, best
## with --headless): rolling spawns on, the player invulnerable, and a bot
## that fires the M14 at a random man every BOT_GAP seconds from the
## player's eye, so the fight has hits, cuts, ragdolls, blood and respawns.
## After WARMUP seconds it records every frame for <seconds>, then prints
## one JSON line ("perf: {...}") and quits.
##
## Built 2026-11-11 when the phone held ~45 fps in Chinatown whatever the
## render scale: the frame wasn't paying for pixels. Scripts can add their
## own sections with PerfProbe.add(&"name", usec) (see `sections`).

const WARMUP: float = 6.0
const BOT_GAP: float = 0.45

static var sections: Dictionary[StringName, int] = {}
static var calls: Dictionary[StringName, int] = {}
static var worst: Dictionary[StringName, int] = {}
static var enabled: bool = false

var seconds: float = 20.0
## Cloud experiments (--perf-exp=<name>): switch one system off for every man
## to see what it costs. noanim, nopose, noai, nonav.
var experiment: String = ""
## No bot (--perf-calm): eight men alive the whole run, a steady load.
var calm: bool = false
var player: Player
var _t: float = 0.0
var _bot: float = 1.0
var _frames: PackedFloat32Array = PackedFloat32Array()
var _proc: PackedFloat32Array = PackedFloat32Array()
var _phys: PackedFloat32Array = PackedFloat32Array()
var _last_us: int = 0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _peak: Dictionary[String, int] = {}
var _snap: Dictionary[StringName, int] = {}
var _ticks: PackedInt32Array = PackedInt32Array()
## Rendering (not headless): draw calls, primitives, objects, render CPU/GPU ms per frame.
var _draws: PackedFloat32Array = PackedFloat32Array()
var _prims: PackedFloat32Array = PackedFloat32Array()
var _objs: PackedFloat32Array = PackedFloat32Array()
var _rcpu: PackedFloat32Array = PackedFloat32Array()
## Turn the view a full circle every SPIN_SECONDS (--perf-spin).
var spin: bool = false
var _yaw0: float = 0.0
var _last_tick: int = 0
var _slow: Array = []


static func add(key: StringName, usec: int) -> void:
	if enabled:
		sections[key] = sections.get(key, 0) + usec
		calls[key] = calls.get(key, 0) + 1
		var w: int = worst.get(key, 0)
		worst[key] = maxi(w, usec)


func _ready() -> void:
	_rng.seed = 99
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	process_priority = -1000


func _process(delta: float) -> void:
	_t += delta
	_bot -= delta
	if _bot <= 0.0 and not calm:
		_bot = BOT_GAP
		_shoot()
	var now: int = Time.get_ticks_usec()
	if _t < WARMUP:
		_last_us = now
		sections.clear()
		calls.clear()
		worst.clear()
		return
	if not enabled:
		# Uncapped: each frame then lasts as long as its work (no render
		# headless), so frames with no physics tick time the process side
		# alone and frames with one tick time process + physics.
		_yaw0 = player.rotation.y
		Engine.max_fps = 0
		OS.low_processor_usage_mode = false
		# Headless never draws, so the main loop sleeps this long every frame.
		OS.low_processor_usage_mode_sleep_usec = 0
		_last_tick = Engine.get_physics_frames()
		_last_us = now
		enabled = true
		return
	var ticks: int = Engine.get_physics_frames() - _last_tick
	_last_tick = Engine.get_physics_frames()
	_ticks.append(ticks)
	if not experiment.is_empty():
		_apply_experiment()
	_frames.append((now - _last_us) / 1000.0)
	_last_us = now
	var proc_ms: float = Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	var phys_ms: float = Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
	_proc.append(proc_ms)
	_phys.append(phys_ms)
	if _frames[-1] > 12.0:
		var top: Array = []
		for k: StringName in sections:
			var d: int = sections[k] - _snap.get(k, 0)
			if d > 500:
				top.append("%s %.1f" % [k, d / 1000.0])
		_slow.append(["%.1f ms, %d ticks" % [_frames[-1], ticks], top])
	_snap = sections.duplicate()
	if DisplayServer.get_name() != "headless":
		var vp: RID = get_viewport().get_viewport_rid()
		_draws.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		_prims.append(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME) / 1000.0)
		_objs.append(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME))
		_rcpu.append(RenderingServer.viewport_get_measured_render_time_cpu(vp))
	if spin:
		player.set_view(_yaw0 + TAU * (_t - WARMUP) / seconds, -0.05)
	_track(&"enemies")
	_track(&"ragdolls_active")
	if _t >= WARMUP + seconds:
		_report()


func _track(group: StringName) -> void:
	var n: int = get_tree().get_node_count_in_group(group)
	var prev: int = _peak.get(String(group), 0)
	_peak[String(group)] = maxi(prev, n)


func _shoot() -> void:
	var men: Array[Node] = get_tree().get_nodes_in_group(&"enemies")
	if men.is_empty() or player == null:
		return
	var e: Enemy = men[_rng.randi() % men.size()] as Enemy
	if e == null or not e.alive:
		return
	var zones: Array[StringName] = [&"chest", &"head", &"l_upper_arm", &"r_thigh", &"stomach", &"r_forearm"]
	var z: StringName = zones[_rng.randi() % zones.size()]
	var hb: HitboxPart = e.parts.get(z, null)
	var at: Vector3 = hb.global_position if hb else e.body.chest_position()
	var from: Vector3 = at + (player.camera().global_position - at).normalized() * 6.0
	var w: WeaponData = load("res://data/weapons/m14p.tres") as WeaponData
	Ballistics.fire(w, from, (at - from).normalized(), player)


func _apply_experiment() -> void:
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or e.body == null:
			continue
		match experiment:
			"noanim":
				e.body._tree.active = false
			"nopose":
				e.body.pose.active = false
			"noai":
				e.set_physics_process(false)
			"nonav":
				e.nav.avoidance_enabled = false
			"hide":
				e.body.visible = false
			"hidemap":
				(get_parent() as ChinatownMap).map_root.visible = false
			"noskel":
				e.body.skeleton.process_mode = Node.PROCESS_MODE_DISABLED


func _split(n: int) -> PackedFloat32Array:
	var out: PackedFloat32Array = PackedFloat32Array()
	for i: int in _ticks.size():
		if _ticks[i] == n:
			out.append(_frames[i])
	return out


## Visible geometry by kind (cloud check of what the renderer has to cull and draw).
func _dump() -> void:
	var kinds: Dictionary[String, int] = {}
	var tris: Dictionary[String, int] = {}
	for n: Node in get_tree().root.find_children("*", "GeometryInstance3D", true, false):
		var g: GeometryInstance3D = n as GeometryInstance3D
		if not g.is_visible_in_tree():
			continue
		var owner_name: String = String(g.get_parent().name) if g.get_parent() else ""
		var key: String = "%s/%s" % [g.get_class(), String(g.name).rstrip("0123456789")]
		if g is MeshInstance3D and (g as MeshInstance3D).mesh is ArrayMesh:
			var am: ArrayMesh = (g as MeshInstance3D).mesh as ArrayMesh
			var t: int = 0
			for si: int in am.get_surface_count():
				t += am.surface_get_array_index_len(si) / 3 if am.surface_get_array_index_len(si) > 0 else am.surface_get_array_len(si) / 3
			tris[key] = tris.get(key, 0) + t
		kinds[key] = kinds.get(key, 0) + 1
		owner_name = owner_name
	var keys: Array = kinds.keys()
	keys.sort_custom(func(a: String, b: String) -> bool: return kinds[a] > kinds[b])
	for k: String in keys.slice(0, 40):
		print("dump: %5d  %-50s tris %d" % [kinds[k], k, tris.get(k, 0)])


static func _stats(a: PackedFloat32Array) -> Dictionary:
	var s: PackedFloat32Array = a.duplicate()
	s.sort()
	var sum: float = 0.0
	for v: float in s:
		sum += v
	var n: int = maxi(s.size(), 1)
	var p95: float = s[mini(int(n * 0.95), s.size() - 1)] if s.size() > 0 else 0.0
	return {"avg": snappedf(sum / n, 0.01), "p95": snappedf(p95, 0.01)}


func _report() -> void:
	enabled = false
	var n: int = maxi(_frames.size(), 1)
	var per: Dictionary = {}
	var keys: Array = sections.keys()
	keys.sort_custom(func(a: StringName, b: StringName) -> bool: return sections[a] > sections[b])
	for k: StringName in keys:
		var us: int = sections[k]
		var c: int = calls[k]
		var w: int = worst[k]
		per[String(k)] = [snappedf(us / 1000.0 / n, 0.001), c, snappedf(w / 1000.0, 0.01)]
	var out: Dictionary = {
		"frames": _frames.size(),
		"frame_ms": _stats(_frames),
		"no_tick_ms": _stats(_split(0)),
		"one_tick_ms": _stats(_split(1)),
		"process_ms": _stats(_proc),
		"physics_ms": _stats(_phys),
		"sections_ms_per_frame": per,
		"peak": _peak,
		"nodes": Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
		"physics_active": Performance.get_monitor(Performance.PHYSICS_3D_ACTIVE_OBJECTS),
		"physics_pairs": Performance.get_monitor(Performance.PHYSICS_3D_COLLISION_PAIRS),
		"gibs": Gore.gib_count(),
		"drops": Gore.drop_count(),
		"stains": Gore.splat_count(),
		"experiment": experiment,
		"draws": _stats(_draws),
		"prims_k": _stats(_prims),
		"objects": _stats(_objs),
		"render_cpu_ms": _stats(_rcpu),
		"slow_frames": _slow.slice(0, 40),
		"slow_count": _slow.size(),
	}
	print("perf: " + JSON.stringify(out))
	if "--perf-dump" in OS.get_cmdline_user_args():
		_dump()
	get_tree().quit(0)
