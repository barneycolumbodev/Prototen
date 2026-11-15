class_name HatchetDemo
extends Node
## Cloud screenshots of the Hatchet Man (`-- --demo=hatchet`, run with Godot's
## `--fixed-fps 60`; docs/design.md §8.8): the operative stands behind the
## low crate in the test room; a Hatchet Man charges from beyond it, vaults
## it and chops. Saves hatchet_<moment>.png from the operative's eyes and
## hatchet_<moment>_side.png from beside: run (sprinting in), vault (over the
## crate), cocked (the blade up: the tell), blow (the hit), then lets
## CaptureDirector finish.

const PLAYER_AT: Vector3 = Vector3(8.0, 0.0, 9.4)
const MAN_AT: Vector3 = Vector3(7.0, 0.0, 15.2)

var room: TestRoom
var _dir: String = ""
var _man: Enemy
var _squad: Squad
var _side: Camera3D
var _frame: int = 0
var _done: Dictionary[String, bool] = {}
var _hit_frame: int = -1


func _ready() -> void:
	add_to_group(&"capture_busy")
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
	var p: Player = room.player
	p.input_enabled = false
	p.body_config = p.body_config.duplicate() as PlayerBodyConfig
	p.body_config.max_health = 5000.0
	p.health = 5000.0
	p.global_position = PLAYER_AT
	p.set_view(PI, -0.04)
	room.shooting_range.clear_targets()
	room.wave_mode._build_navigation()
	_squad = Squad.new()
	room.add_child(_squad)
	_squad.set_player(p)
	_squad.build_cover(Vector3.ZERO, 15.5, room.get_world_3d())
	_side = Camera3D.new()
	_side.fov = 55.0
	room.add_child(_side)
	_side.look_at_from_position(Vector3(12.2, 1.5, 11.8), Vector3(7.6, 1.0, 11.2))


func _physics_process(_delta: float) -> void:
	_frame += 1
	if _frame == 30:
		_man = Enemy.new()
		_man.config = load("res://data/enemies/hatchet_man.tres") as EnemyConfig
		_man.look_seed = 23
		_squad.add(_man)
		room.add_child(_man)
		_man.global_position = MAN_AT
		_man.face(PI)
		_man.awareness = 1.0
		_man.last_known = room.player.global_position
		_man._enter(Enemy.State.COMBAT)
	if _man == null:
		return
	var m: MeleeBrain = _man.melee
	if _frame == 48:
		_snap("run")
	if m.is_vaulting() and m._t >= _man.config.vault_time * 0.4:
		_snap("vault")
	if m.is_winding_up() and m._t >= 0.3 * _man.config.melee_windup / 0.46:
		_snap("cocked")
	if m.hits > 0 and _hit_frame < 0:
		_hit_frame = _frame
	if _hit_frame > 0 and _frame == _hit_frame + 2:
		_snap("blow")
	if _frame > 400 or (_hit_frame > 0 and _frame > _hit_frame + 30):
		print("hatchet demo: vaults %d strikes %d hits %d whiffs %d" % [m.vaults, m.strikes, m.hits, m.whiffs])
		set_physics_process(false)
		await get_tree().create_timer(0.5).timeout
		remove_from_group(&"capture_busy")


func _snap(moment: String) -> void:
	if _done.has(moment):
		return
	_done[moment] = true
	_shoot.call_deferred(moment)


func _shoot(moment: String) -> void:
	if _dir.is_empty():
		return
	get_tree().paused = true
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("hatchet_%s.png" % moment))
	_side.make_current()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("hatchet_%s_side.png" % moment))
	room.player.camera().make_current()
	get_tree().paused = false
	print("capture hatchet_%s" % moment)
