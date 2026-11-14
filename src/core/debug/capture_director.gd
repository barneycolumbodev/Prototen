extends Node
## Cloud screenshot driver used by tools/screenshot.sh (CLAUDE.md §10.4).
##
## Does nothing unless the game is launched with `-- --capture-dir=<dir>`.
## Then it waits for the scene to settle, visits every Camera3D in the
## "capture_cameras" group (fixed positions in each test room), then the
## camera that was active at start, saves one PNG per camera and quits.
##
## Extra user args:
##   --capture-warmup=<frames>  frames to wait before each shot (default 30)
##   --capture-only=<name>      only shoot the camera with this node name
##   --capture-pause            open the pause menu before shooting
##   --capture-tuning           open the gun tuning menu before shooting
##   --capture-strike=<frames>  R3 strike, then the active shot that many frames later
## Nodes in the "capture_busy" group (e.g. GunplayDemo) delay the first shot.

const GROUP: StringName = &"capture_cameras"

var _dir: String = ""
var _warmup: int = 30
var _only: String = ""
var _open_pause: bool = false
var _open_tuning: bool = false
var _strike: int = -1


func _ready() -> void:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--capture-dir="):
			_dir = arg.trim_prefix("--capture-dir=")
		elif arg.begins_with("--capture-warmup="):
			_warmup = maxi(1, arg.trim_prefix("--capture-warmup=").to_int())
		elif arg.begins_with("--capture-only="):
			_only = arg.trim_prefix("--capture-only=")
		elif arg == "--capture-pause":
			_open_pause = true
		elif arg == "--capture-tuning":
			_open_tuning = true
		elif arg.begins_with("--capture-strike="):
			_strike = arg.trim_prefix("--capture-strike=").to_int()
	if _dir.is_empty():
		set_process(false)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	# Software rendering is slow: keep captures at full resolution.
	Settings.adaptive.held = true
	DirAccess.make_dir_recursive_absolute(_dir)
	_run.call_deferred()


func is_capturing() -> bool:
	return not _dir.is_empty()


func _run() -> void:
	await _frames(_warmup)
	# Scripted demos (GunplayDemo) hold the capture until they finish.
	while get_tree().get_node_count_in_group(&"capture_busy") > 0:
		await _frames(5)
	if _open_pause:
		get_node("/root/PauseMenu").call("open")
	if _open_tuning:
		get_node("/root/TuningMenu").call("open")
	var scene: Node = get_tree().current_scene
	var scene_name: String = scene.scene_file_path.get_file().get_basename() if scene else "scene"
	var start_cam: Camera3D = get_viewport().get_camera_3d()
	var shots: int = 0
	for node: Node in get_tree().get_nodes_in_group(GROUP):
		var cam: Camera3D = node as Camera3D
		if cam == null or (not _only.is_empty() and cam.name != _only):
			continue
		cam.make_current()
		await _frames(_warmup)
		shots += _save("%s_%s.png" % [scene_name, cam.name])
	if start_cam and (_only.is_empty() or _only == "active"):
		start_cam.make_current()
		await _frames(_warmup)
		if _strike >= 0:
			var p: Player = get_tree().get_first_node_in_group(&"player") as Player
			if p and p.melee:
				if p.melee.knife:
					for i: int in 4:
						p.melee.knife.cut(true)
				p.melee.script_strike()
				await _frames(_strike)
		shots += _save("%s_active.png" % scene_name)
	print("capture: %d screenshots in %s (renderer %s)" % [shots, _dir, RenderingServer.get_current_rendering_method()])
	get_tree().quit(0 if shots > 0 else 1)


func _save(file_name: String) -> int:
	var image: Image = get_viewport().get_texture().get_image()
	var path: String = _dir.path_join(file_name)
	var err: Error = image.save_png(path)
	if err != OK:
		push_error("capture: failed to save %s (%s)" % [path, error_string(err)])
		return 0
	print("capture: saved ", path)
	return 1


func _frames(count: int) -> void:
	for i: int in count:
		await get_tree().process_frame
