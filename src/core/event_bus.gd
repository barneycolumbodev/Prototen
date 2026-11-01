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
