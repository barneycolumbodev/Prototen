class_name LoadoutStore
extends RefCounted
## Saves the loadout built on the body-status screen (user://loadout.cfg, the
## part ids) and loads it when the game starts. Tests and cloud captures
## don't read or write it, so they always see the default loadout.

const LIBRARY: PartLibrary = preload("res://data/body/part_library.tres")
const DEFAULT_PATH: String = "res://data/body/loadout_default.tres"
## Presets on the loadout screen, in order.
const PRESETS: Array[String] = [
	"res://data/body/loadout_default.tres",
	"res://data/body/presets/ghost.tres",
	"res://data/body/presets/juggernaut.tres",
	"res://data/body/presets/marksman.tres",
	"res://data/body/presets/reaper.tres",
	"res://data/body/presets/handler.tres",
	"res://data/body/presets/wraith.tres",
]

static var path: String = "user://loadout.cfg"


## False under GUT and during cloud captures.
static func enabled() -> bool:
	if CaptureDirector.is_capturing():
		return false
	for a: String in OS.get_cmdline_args():
		if a.contains("gut_cmdln"):
			return false
	return true


static func presets() -> Array[BodyLoadout]:
	var out: Array[BodyLoadout] = []
	for p: String in PRESETS:
		var lo: BodyLoadout = load(p) as BodyLoadout
		if lo:
			out.append(lo)
	return out


## The saved loadout, or a copy of `fallback` if nothing is saved.
static func load_saved(fallback: BodyLoadout) -> BodyLoadout:
	if not enabled():
		return fallback.copy()
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(path) != OK:
		return fallback.copy()
	var ids: PackedStringArray = cfg.get_value("loadout", "parts", PackedStringArray())
	var name: String = cfg.get_value("loadout", "name", "Custom")
	if ids.is_empty():
		return fallback.copy()
	return LIBRARY.loadout_from_ids(ids, name)


static func save(lo: BodyLoadout) -> void:
	if not enabled():
		return
	var cfg: ConfigFile = ConfigFile.new()
	cfg.load(path)  # keep the colours section
	cfg.set_value("loadout", "name", lo.display_name)
	cfg.set_value("loadout", "parts", lo.ids())
	var err: Error = cfg.save(path)
	if err != OK:
		push_warning("LoadoutStore: could not save (%s)" % error_string(err))


## The colours picked on the loadout screen's Colours page (same file).
static func load_colors() -> BodyColors:
	if not enabled():
		return BodyColors.new()
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(path) != OK:
		return BodyColors.new()
	var saved: Dictionary = cfg.get_value("colors", "channels", {})
	return BodyColors.from_dict(saved)


static func save_colors(colors: BodyColors) -> void:
	if not enabled():
		return
	var cfg: ConfigFile = ConfigFile.new()
	cfg.load(path)
	cfg.set_value("colors", "channels", colors.to_dict())
	var err: Error = cfg.save(path)
	if err != OK:
		push_warning("LoadoutStore: could not save colours (%s)" % error_string(err))
