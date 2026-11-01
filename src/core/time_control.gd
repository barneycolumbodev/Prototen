extends Node
## Global time scale (CLAUDE.md §9.2). Autoloaded as TimeControl.
## Hit-stop freezes the world for a few real-time frames on headshots and
## kills; slow motion (M2) will set `slowmo_scale`. Engine.time_scale is the
## product of both, and audio pitch can follow `scale()`.

var slowmo_scale: float = 1.0
var _hitstop_scale: float = 1.0
var _hitstop_until_ms: int = 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


## Freezes time to `time_scale` for `seconds` of real time. Overlapping calls
## keep the longest end and the lowest scale.
func hitstop(seconds: float, time_scale: float) -> void:
	if seconds <= 0.0:
		return
	var until: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	if until > _hitstop_until_ms:
		_hitstop_until_ms = until
	_hitstop_scale = minf(_hitstop_scale, time_scale) if is_hitstopped() else time_scale
	_apply()


func is_hitstopped() -> bool:
	return Time.get_ticks_msec() < _hitstop_until_ms


func scale() -> float:
	return Engine.time_scale


func _process(_delta: float) -> void:
	if _hitstop_scale < 1.0 and not is_hitstopped():
		_hitstop_scale = 1.0
		_apply()


func _apply() -> void:
	Engine.time_scale = maxf(0.001, slowmo_scale * _hitstop_scale)
