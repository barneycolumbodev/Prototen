class_name HuntConfig
extends Resource
## How a squad in a wave mode hunts the operative and works together
## against him (owner, 2026-11-16; docs/design.md §5.6a). Loaded from
## data/enemies/hunt.tres. A squad without one (the range targets, the
## debug demos) doesn't hunt.

@export_group("Lookouts")
## Seconds nobody in the squad has seen him before the lookouts phone in
## where he is (his real position, give or take `intel_noise`).
@export var intel_refresh: float = 5.0
## How far off a lookout's tip can be (metres).
@export var intel_noise: float = 7.0
## With this many or fewer still fighting, the tips come faster and closer:
## the last men always come for him.
@export var last_count: int = 2
@export var last_refresh: float = 2.0
@export var last_noise: float = 2.0
## Arrived where he was and he's gone: search a point this far around the
## latest tip.
@export var search_radius: float = 6.0
## Hunters run when the place they're heading is farther than this.
@export var run_beyond: float = 10.0

@export_group("Pin and flank")
## Seconds between handing out roles.
@export var role_interval: float = 1.0
## Roles only while someone saw him within this many seconds.
@export var contact_fresh: float = 4.0
## Pinners: hold cover and keep firing where he went to keep his head down.
@export var pin_count: int = 2
## A pinner keeps firing at where he lost sight of him this long.
@export var pin_fire_time: float = 3.5
## Extra aim error on that fire (it's meant to keep his head down).
@export var pin_error_scale: float = 1.6
## Flankers: up to this many (never more than half the gunmen) run round
## to his side while the pinners hold him.
@export var flank_count: int = 2
## Off the line from the pinners to him (degrees).
@export var flank_angle_deg: float = 95.0
## How far from him the flank position is.
@export var flank_distance: float = 11.0
## Give up a flank this long after setting out and just fight.
@export var flank_timeout: float = 12.0

@export_group("Pressure")
## Everyone else pushes: after this long in one piece of cover he moves up
## to cover at least `push_step` nearer.
@export var push_after: float = 5.0
@export var push_step: float = 4.0
## A man who ran or froze turns back after this long when the squad is
## down to `last_count` (nowhere left to run).
@export var cornered_after: float = 5.0

## A hunter who hasn't got anywhere for this long (stuck on something, or
## thrown somewhere with no way back) is moved to a spawn point out of the
## operative's sight. 0: never.
@export var stuck_after: float = 6.0

@export_group("HUD")
## Mark the remaining men on the HUD (an arrow at the screen edge, a
## marker over them) once this many or fewer are left in a wave.
@export var mark_when_left: int = 1
