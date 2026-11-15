class_name BossDemo
extends Node
## Cloud screenshots of the Incense Master (`-- --demo=boss`, run with
## Godot's `--fixed-fps 60`; docs/design.md §8.7a/b) in the test room: he
## stands in front of the operative, then is made to do each move in turn
## (the Gauss shot charging, the ground pound's fists up and the impact, the
## haymaker cocked), goes down on one knee, and the execution plays. Saves
## boss_<moment>.png from the operative's eyes and boss_<moment>_side.png
## from a camera beside them (the operative can't be hurt).
## `-- --demo=boss-intro` plays the entrance instead (BossIntro), saving
## boss_intro_<n>.png at moments through it.

const PLAYER_AT: Vector3 = Vector3(2.0, 0.0, 5.0)
const BOSS_AT: Vector3 = Vector3(2.0, 0.0, 12.5)

var room: TestRoom
var intro: bool = false
var _dir: String = ""
var _boss: Enemy
var _squad: Squad
var _side: Camera3D
var _face: Camera3D
var _frame: int = 0
var _step: int = 0
var _step_frame: int = 0
var _done: Dictionary[String, bool] = {}
var _intro_node: BossIntro


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	var p: Player = room.player
	p.input_enabled = false
	p.invulnerable = true
	p.global_position = PLAYER_AT
	p.set_view(PI, 0.02)
	room.shooting_range.clear_targets()
	room.wave_mode._build_navigation()
	_squad = Squad.new()
	room.add_child(_squad)
	_squad.set_player(p)
	_squad.build_cover(Vector3.ZERO, 15.5, room.get_world_3d())
	_side = Camera3D.new()
	_side.fov = 55.0
	room.add_child(_side)
	_side.look_at_from_position(Vector3(7.0, 2.0, 12.5), Vector3(2.0, 1.3, 10.0))
	_face = Camera3D.new()
	_face.fov = 40.0
	room.add_child(_face)
	p.camera().make_current.call_deferred()


func _physics_process(_delta: float) -> void:
	_frame += 1
	if _frame == 20:
		# The capture setup turns the operative after _ready: put him back.
		room.player.global_position = PLAYER_AT
		room.player.set_view(PI, 0.02)
		room.player.camera().make_current()
		_boss = Enemy.new()
		_boss.config = load("res://data/enemies/incense_master.tres") as EnemyConfig
		_boss.look_seed = 5
		_squad.add(_boss)
		room.add_child(_boss)
		_boss.global_position = BOSS_AT
		_boss.face(PI)
		_boss.awareness = 1.0
		_boss.last_known = room.player.global_position
		if intro:
			_intro_node = BossIntro.new()
			_intro_node.boss = _boss
			_intro_node.player = room.player
			_intro_node.landing = BOSS_AT
			room.add_child(_intro_node)
		else:
			_boss._enter(Enemy.State.COMBAT)
			_boss.boss.phase = BossBrain.Phase.STAGGER
			_boss.boss._t = -99.0
	if _boss == null:
		return
	if intro:
		_intro_frames()
		return
	var b: BossBrain = _boss.boss
	var since: int = _frame - _step_frame
	match _step:
		0:
			if since == 40:
				_face.look_at_from_position(_boss.body.head_position() + Vector3(-0.9, -0.15, -1.9), _boss.body.chest_position() + Vector3.UP * 0.25)
				_snap("stand", true)
				_next()
		1:
			if since == 2:
				b._start_cannon()
			if b.phase == BossBrain.Phase.CANNON and b._t >= b.cfg.cannon_charge * 0.85:
				_snap("cannon")
			if b.shots > 0 and since > 2:
				_snap("cannon_fire")
				_next()
		2:
			if since == 50:
				b.phase = BossBrain.Phase.HUNT
				b._start_pound()
			if b.phase == BossBrain.Phase.POUND and b._t >= b.cfg.pound_windup * 0.72:
				_snap("pound_up")
			if b.phase == BossBrain.Phase.POUND and b._struck and b._t >= b.cfg.pound_windup + 0.05:
				_snap("pound_hit")
				_next()
		3:
			if since == 60:
				b.phase = BossBrain.Phase.HUNT
				room.player.global_position = BOSS_AT + Vector3(0.0, 0.0, -3.0)
				b._start_swing()
			if b.phase == BossBrain.Phase.SWING and b._t >= b.cfg.swing_windup * 0.45:
				_snap("swing")
			if b.phase == BossBrain.Phase.SWING and b._t >= b.cfg.swing_windup + 0.05:
				_snap("swing_hit")
				_next()
		4:
			if since == 50:
				room.player.global_position = BOSS_AT + Vector3(0.0, 0.0, -2.8)
				room.player.velocity = Vector3.ZERO
				room.player.set_view(PI, -0.12)
				_boss.health = 1.0
				_boss.die(null, &"chest")
			if since == 110:
				_face.look_at_from_position(_boss.body.head_position() + Vector3(-0.8, 0.2, -1.6), _boss.body.head_position() + Vector3.DOWN * 0.5)
				_snap("kneel", true)
				_next()
		5:
			var ex: BossExecution = b.execution
			if since == 6:
				_snap("prompt", false, false)
			if since == 10:
				print("boss demo: prompt %s" % ex.can_start())
				ex.script_start()
			if ex == null or not ex.running and not ex.done:
				return
			var times: PackedFloat32Array = b.cfg.punch_times
			if ex.t >= 0.7:
				_snap("grab")
			if ex.punches >= 1 and ex.t >= times[0] + 0.02:
				_snap("punch")
			if ex.punches >= 3 and ex.t >= times[2] + 0.03:
				_snap("punch3")
			if ex.head_gone and ex.t >= times[times.size() - 1] + 0.06:
				_snap("skull")
			var examine_at: float = times[times.size() - 1] + 0.15 + b.cfg.release_time
			if ex.t >= examine_at + b.cfg.examine_time * 0.6:
				_snap("examine")
			if ex.flicks >= 1 and ex.t >= examine_at + b.cfg.examine_time + b.cfg.shake_time * 0.18:
				_snap("shake")
			if ex.done:
				print("boss demo: punches %d head %s flicks %d shots %d pounds %d swings %d" % [ex.punches, ex.head_gone, ex.flicks, b.shots, b.pounds, b.swings])
				_next()
		6:
			if since == 30:
				_snap("after")
			if since == 60:
				set_physics_process(false)
				remove_from_group(&"capture_busy")


func _intro_frames() -> void:
	var t: float = float(_frame - 20) / 60.0
	for k: float in [0.4, 0.95, 1.15, 1.6, 2.2, 2.9, 3.4, 4.0]:
		if t >= k:
			_snap("intro_%02d" % roundi(k * 10.0), false, false)
	if _intro_node and _intro_node.done and t > 4.8:
		_snap("intro_after", false, false)
		if t > 5.2:
			set_physics_process(false)
			remove_from_group(&"capture_busy")


func _next() -> void:
	_step += 1
	_step_frame = _frame


func _snap(moment: String, face: bool = false, side: bool = true) -> void:
	if _done.has(moment):
		return
	_done[moment] = true
	_shoot.call_deferred(moment, face, side)


func _shoot(moment: String, face: bool, side: bool) -> void:
	if _dir.is_empty():
		return
	get_tree().paused = true
	var cam: Camera3D = get_viewport().get_camera_3d()
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("boss_%s.png" % moment))
	if side:
		_side.make_current()
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(_dir.path_join("boss_%s_side.png" % moment))
	if face:
		_face.make_current()
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(_dir.path_join("boss_%s_face.png" % moment))
	if cam:
		cam.make_current()
	get_tree().paused = false
	print("capture boss_%s" % moment)
