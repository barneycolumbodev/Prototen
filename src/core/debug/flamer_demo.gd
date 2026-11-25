class_name FlamerDemo
extends Node
## Cloud screenshots of the Triad Flamer (`-- --demo=flamer`, run with Godot's
## `--fixed-fps 60`; docs/design.md §8.8c):
## 1. flamer_approach (+ _side): Flamer rushing in holding the red/yellow aerosol can & lit Zippo lighter
## 2. flamer_spray (+ _side): roaring flame stream spraying at the operative
## 3. flamer_fireball (+ _side): precision shot hits the aerosol can -> billowing fireball engulfing Flamer & allies
## 4. flamer_aftermath: Flamer collapsed charred & burning on the spot, nearby ally flailing in flames

const PLAYER_AT: Vector3 = Vector3(0.0, 0.0, 12.2)
const FLAMER_AT: Vector3 = Vector3(0.0, 0.0, 5.4)

var room: TestRoom
var _dir: String = ""
var _flamer: Enemy
var _ally1: Enemy
var _ally2: Enemy
var _squad: Squad
var _side: Camera3D
var _close: Camera3D
var _frame: int = 0
var _done: Dictionary[String, bool] = {}
var _shot_frame: int = -1
var _pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")


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
	p.set_view(0.0, -0.05)
	room.shooting_range.clear_targets()
	room.wave_mode._build_navigation()
	_squad = Squad.new()
	room.add_child(_squad)
	_squad.set_player(p)
	_squad.build_cover(Vector3.ZERO, 15.5, room.get_world_3d())
	_side = Camera3D.new()
	_side.fov = 54.0
	room.add_child(_side)
	_side.look_at_from_position(Vector3(5.6, 1.9, 8.6), Vector3(0.0, 1.15, 7.6))
	_close = Camera3D.new()
	_close.fov = 42.0
	room.add_child(_close)


func _physics_process(_delta: float) -> void:
	_frame += 1
	if _frame == 8:
		_flamer = Enemy.new()
		_flamer.config = load("res://data/enemies/flamer.tres") as EnemyConfig
		_flamer.look_seed = 7
		_squad.add(_flamer)
		room.add_child(_flamer)
		_flamer.global_position = FLAMER_AT
		_flamer.face(0.0)
		_flamer.awareness = 1.0
		_flamer.last_known = room.player.global_position
		_flamer._enter(Enemy.State.COMBAT)
		# Two triad allies nearby to show fireball splash ignition!
		_ally1 = Enemy.new()
		_ally1.config = load("res://data/enemies/gunman.tres") as EnemyConfig
		_ally1.passive = true
		_ally1.look_seed = 11
		_squad.add(_ally1)
		room.add_child(_ally1)
		_ally1.global_position = Vector3(-1.6, 0.0, 7.0)
		_ally1.face(0.15)
		_ally2 = Enemy.new()
		_ally2.config = load("res://data/enemies/gunman.tres") as EnemyConfig
		_ally2.passive = true
		_ally2.look_seed = 19
		_squad.add(_ally2)
		room.add_child(_ally2)
		_ally2.global_position = Vector3(1.7, 0.0, 7.2)
		_ally2.face(-0.15)
	if _flamer == null:
		return
	# Keep player facing the Flamer cleanly for dramatic shots.
	var to_f: Vector3 = _flamer.body.chest_position() - room.player.camera().global_position
	room.player.set_view(atan2(-to_f.x, -to_f.z), atan2(to_f.y, Vector2(to_f.x, to_f.z).length()))
	var fb: FlamerBrain = _flamer.flamer
	if _frame == 18:
		# Close-up of the Flamer holding the red/yellow can + lit Zippo lighter.
		var hand_mid: Vector3 = _flamer.body.chest_position() + _flamer.global_basis.z * 0.25
		_close.look_at_from_position(hand_mid + _flamer.global_basis.z * 1.45 + _flamer.global_basis.x * 0.95 + Vector3.UP * 0.2, hand_mid)
		_snap("approach", true)
	if fb.is_spraying() and fb._t >= 0.35 and not _done.has("spray"):
		var mid: Vector3 = (_flamer.body.chest_position() + room.player.global_position + Vector3.UP) * 0.5
		_side.look_at_from_position(mid + Vector3(5.6, 1.3, 0.6), mid)
		_snap("spray", false)
	if fb.is_spraying() and fb._t >= 0.65 and _shot_frame < 0:
		# Precision shot straight into the aerosol can!
		_shot_frame = _frame
		var from: Vector3 = room.player.camera().global_position
		var can_at: Vector3 = fb.can_world_position()
		Ballistics.fire(_pistol, from, (can_at - from).normalized(), room.player)
	if _shot_frame > 0 and _frame == _shot_frame + 3:
		var blast_c: Vector3 = _flamer.global_position + Vector3.UP * 1.15
		_side.look_at_from_position(blast_c + Vector3(-5.0, 1.4, 2.2), blast_c)
		_snap("fireball", false)
	if _shot_frame > 0 and _frame == _shot_frame + 24:
		var aft_c: Vector3 = _flamer.global_position + Vector3.UP * 0.9
		_side.look_at_from_position(aft_c + Vector3(-4.8, 1.5, 2.4), aft_c)
		_snap("aftermath", false)
	if _frame > 300 or (_shot_frame > 0 and _frame > _shot_frame + 30):
		print("flamer demo: sprays=%d ticks=%d detonated=%s splash=%d" % [
				fb.sprays, fb.fire_ticks, str(fb.can_detonated), fb.splash_ignited])
		set_physics_process(false)
		await get_tree().create_timer(0.2).timeout
		remove_from_group(&"capture_busy")


func _snap(moment: String, use_close: bool) -> void:
	if _done.has(moment):
		return
	_done[moment] = true
	_shoot.call_deferred(moment, use_close)


func _shoot(moment: String, use_close: bool) -> void:
	if _dir.is_empty():
		return
	get_tree().paused = true
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("flamer_%s.png" % moment))
	var alt: Camera3D = _close if use_close else _side
	alt.make_current()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join("flamer_%s_%s.png" % [moment, "close" if use_close else "side"]))
	room.player.camera().make_current()
	get_tree().paused = false
	print("capture flamer_%s" % moment)
