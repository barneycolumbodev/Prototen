class_name ActivePartData
extends PartData
## A part assigned to a button (docs/design.md §3.4). Its behaviour is an
## ActivePart node (`behaviour`), driven through idle → deploying → active →
## recovering → cooldown.
##
## Many actives run on a charge that drains while they're on and refills
## over time, like health (owner, 2026-11-05, for the time slowdown): press
## to start, press again to stop, or it stops when the charge runs out.

@export var behaviour: Script
## Which button: 1 = LB, 2 = RB, 3 = D-pad up.
@export_range(1, 3) var slot: int = 1

@export_group("Timing (s)")
@export var deploy_time: float = 0.12
@export var recover_time: float = 0.25
@export var cooldown_time: float = 0.4

@export_group("Charge (seconds of use)")
@export var charge_max: float = 8.0
## Charge used per second while active (real time).
@export var drain_per_s: float = 1.0
## Charge refilled per second once `regen_delay` has passed since it stopped.
@export var regen_per_s: float = 0.5
@export var regen_delay: float = 1.5
## Can't start with less than this.
@export var min_to_start: float = 1.0
## Extra power drawn while active (W), on top of power_draw_w.
@export var active_power_w: float = 0.0
## Extra heat while active (W).
@export var active_heat_w: float = 0.0


func is_active() -> bool:
	return true
