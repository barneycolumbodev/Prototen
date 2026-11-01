extends SceneTree
## Loads every GDScript under res://src and res://tests so parse errors and
## static-typing warnings (configured as errors) fail tools/check.sh.
## Run: godot --headless -s res://tools/validate_scripts.gd

const ROOTS: Array[String] = ["res://src", "res://tests"]


func _init() -> void:
	var paths: Array[String] = []
	for root: String in ROOTS:
		_collect(root, paths)
	var failed: int = 0
	for path: String in paths:
		var script: Resource = ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_IGNORE)
		var ok: bool = script is GDScript and (script as GDScript).can_instantiate()
		if ok:
			print("OK   ", path)
		else:
			failed += 1
			print("FAIL ", path)
	print("validate_scripts: %d scripts, %d failed" % [paths.size(), failed])
	quit(1 if failed > 0 else 0)


func _collect(dir_path: String, out: Array[String]) -> void:
	var dir: DirAccess = DirAccess.open(dir_path)
	if dir == null:
		return
	for sub: String in dir.get_directories():
		_collect(dir_path.path_join(sub), out)
	for file: String in dir.get_files():
		if file.ends_with(".gd"):
			out.append(dir_path.path_join(file))
