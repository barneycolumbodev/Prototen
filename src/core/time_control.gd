extends Node
## Global time scale (CLAUDE.md §9.2). Autoloaded as TimeControl.
## Hit-stop freezes the world for a few real-time frames on headshots and
## kills; the weapon wheel sets `slowmo_scale`; the time-dilation part sets
## `dilation_scale` and a separate scale for the player (§9.2: "a global time
## scale for slowdown, with a separate scale for the player").
## Engine.time_scale is the product of the three. The player's own movement,
## gun and look run `player_boost()` times faster than the world, so while
## dilated the world runs at dilation_scale and you at dilation_player_scale.

var slowmo_scale: float = 1.0
var dilation_scale: float = 1.0
var dilation_player_scale: float = 1.0
## How much heavier hits land at full dilation (set by the part's data).
var dilation_impact_boost: float = 1.0
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


## Slow motion (weapon wheel now, the time-slowdown part in M2). 1 = normal.
func set_slowmo(time_scale: float) -> void:
	slowmo_scale = clampf(time_scale, 0.01, 1.0)
	_apply()


## Time dilation (ActivePart TimeDilation). `world` = how fast the world
## runs, `player` = how fast the player runs (both 0..1, 1 = normal).
func set_dilation(world: float, player: float) -> void:
	dilation_scale = clampf(world, 0.05, 1.0)
	dilation_player_scale = clampf(player, dilation_scale, 1.0)
	_apply()


## 0 = no dilation, 1 = fully dilated (for effects that scale with it).
func dilation_amount() -> float:
	return clampf((1.0 - dilation_scale) / 0.7, 0.0, 1.0)


## Multiplier for ragdoll/limb impulses right now (1 when not dilated).
func impact_multiplier() -> float:
	return lerpf(1.0, dilation_impact_boost, dilation_amount())


## How much faster the player runs than the world (1 when not dilated).
func player_boost() -> float:
	return dilation_player_scale / dilation_scale


## Real seconds for a frame whose (scaled) delta is `delta`. Capped, so a
## hitch or a near-frozen hit-stop can't produce a huge step.
func real_delta(delta: float) -> float:
	return minf(delta / maxf(Engine.time_scale, 0.001), 0.1)


## Pitch for the player's own sounds (their gun): world pitch × boost.
func player_pitch() -> float:
	return clampf(Engine.time_scale * player_boost(), 0.25, 1.0)


func is_hitstopped() -> bool:
	return Time.get_ticks_msec() < _hitstop_until_ms


func scale() -> float:
	return Engine.time_scale


func _process(_delta: float) -> void:
	if _hitstop_scale < 1.0 and not is_hitstopped():
		_hitstop_scale = 1.0
		_apply()


func _apply() -> void:
	Engine.time_scale = maxf(0.001, slowmo_scale * _hitstop_scale * dilation_scale)
