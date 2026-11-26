class_name TutorialStore
extends RefCounted
## What the player has already been shown (docs/design.md §8.11): the
## Survival tips seen once, and whether boot camp was finished. Saved in
## user://tutorial.cfg. Under tests and cloud captures nothing is read or
## written to disk: the flags live in memory for that run only.

const PATH: String = "user://tutorial.cfg"
const SECTION: String = "seen"

static var _mem: Dictionary[StringName, bool] = {}
static var _loaded: bool = false


static func persistent() -> bool:
	return LoadoutStore.enabled()


static func _load() -> void:
	if _loaded:
		return
	_loaded = true
	if not persistent():
		return
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(PATH) != OK or not cfg.has_section(SECTION):
		return
	for k: String in cfg.get_section_keys(SECTION):
		_mem[StringName(k)] = cfg.get_value(SECTION, k, false) == true


static func _save() -> void:
	if not persistent():
		return
	var cfg: ConfigFile = ConfigFile.new()
	for k: StringName in _mem:
		cfg.set_value(SECTION, String(k), _mem[k])
	var err: Error = cfg.save(PATH)
	if err != OK:
		push_warning("TutorialStore: could not save (%s)" % error_string(err))


static func seen(id: StringName) -> bool:
	_load()
	return _mem.get(id, false)


static func mark(id: StringName) -> void:
	_load()
	if _mem.get(id, false):
		return
	_mem[id] = true
	_save()


static func boot_camp_done() -> bool:
	return seen(&"boot_camp_done")


## Pause → Options → Tips: show again. Every tip comes back (boot camp stays done).
static func reset_tips() -> void:
	_load()
	var keep: bool = _mem.get(&"boot_camp_done", false)
	_mem.clear()
	if keep:
		_mem[&"boot_camp_done"] = true
	_save()


## Tests: forget everything in memory.
static func clear_for_tests() -> void:
	_mem.clear()
	_loaded = true
