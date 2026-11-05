extends Node
## The one combat event bus (CLAUDE.md §9.2). Systems emit here instead of
## holding references to each other. Autoloaded as EventBus.

@warning_ignore("unused_signal")
signal damage_applied(info: DamageInfo, victim: Node)
@warning_ignore("unused_signal")
signal shot_fired(shooter: Node, origin: Vector3, direction: Vector3)
@warning_ignore("unused_signal")
signal killed(victim: Node, info: DamageInfo)
@warning_ignore("unused_signal")
signal benchmark_requested(duration_sec: float)
@warning_ignore("unused_signal")
signal benchmark_finished(result: Dictionary)
## Every bullet contact (ballistics.gd): effects, sound, stats and targets listen.
@warning_ignore("unused_signal")
signal ballistic_hit(hit: BallisticHit)
## A target reports what a hit did to it (hit markers, stats).
## kind: &"hit", &"headshot", &"kill", &"armor"
@warning_ignore("unused_signal")
signal target_hit(kind: StringName, hit: BallisticHit)
## An enemy shouts (subtitles): speaker callsign, line, where.
@warning_ignore("unused_signal")
signal callout(speaker: String, text: String, at: Vector3)
## The player was hit: damage after armour, direction it came from (world).
@warning_ignore("unused_signal")
signal player_damaged(amount: float, from_dir: Vector3)
@warning_ignore("unused_signal")
signal player_died
## Wave mode: wave number, enemies left (-1 = between waves).
@warning_ignore("unused_signal")
signal wave_changed(wave: int, left: int)
## Pause menu: start or stop wave mode.
@warning_ignore("unused_signal")
signal wave_mode_requested
## Rolling spawns (open maps): kills so far, enemies in the fight or on their way.
@warning_ignore("unused_signal")
signal score_changed(kills: int, hostiles: int)
