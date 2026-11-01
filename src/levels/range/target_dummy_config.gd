class_name TargetDummyConfig
extends Resource
## Range dummy tuning (data/targets/dummy.tres). Zone multipliers follow
## docs/design.md §5.1 and will be reused for enemy soldiers in M1c.

@export_range(1.0, 1000.0) var health: float = 100.0
## Damage multiplier per zone.
@export var zone_multipliers: Dictionary[StringName, float] = {
	&"head": 4.0, &"neck": 3.0, &"chest": 1.25, &"stomach": 1.0, &"pelvis": 1.0,
	&"l_upper_arm": 0.6, &"l_forearm": 0.5, &"r_upper_arm": 0.6, &"r_forearm": 0.5,
	&"l_thigh": 0.75, &"l_shin": 0.6, &"r_thigh": 0.75, &"r_shin": 0.6,
}
## Seconds lying down after a kill before it stands back up.
@export_range(0.5, 10.0) var reset_time: float = 2.5
## Wobble per hit, degrees per newton-second of impulse.
@export_range(0.0, 20.0) var wobble_per_impulse: float = 1.4
@export_range(0.5, 10.0) var wobble_hz: float = 2.2
@export_range(0.05, 1.0) var wobble_damping: float = 0.25
