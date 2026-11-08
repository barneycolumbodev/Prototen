class_name PlayerBodyConfig
extends Resource
## The augmented body before any parts (data/player/body_default.tres): the
## base values of every stat (docs/design.md §3.6; Stats.DEFS lists them) and
## the tuning of the derived values (load, structure cap, link range, heat).

@export_range(10.0, 2000.0) var max_health: float = 200.0
## Damage per kJ of a round's energy when it hits (the subdermal armour
## spreads it): a Type 56 round (2 kJ) does 14, a 00 buck pellet (0.28 kJ) 2.
@export_range(0.5, 100.0) var damage_per_kj: float = 7.0
## Seconds without being hit before healing starts, and health per second after.
@export_range(0.0, 20.0) var regen_delay: float = 3.5
@export_range(0.0, 500.0) var regen_rate: float = 45.0
## Seconds dead before respawning.
@export_range(0.5, 10.0) var respawn_time: float = 3.0

@export_group("Frame (docs/design.md §3.2)")
## The operative before any parts: a heavily built man in the base carapace.
@export var base_mass_kg: float = 96.0
## Loadout capacity budget (parts cost 0-4 each; the `capacity` stat's base).
@export var capacity: int = 16
## What the body can carry before heavy weapons slow it (M3).
@export var carry_kg: float = 40.0
## The spinal power cell: reserve (J) and what it supplies (W).
@export var power_capacity_j: float = 60000.0
@export var power_supply_w: float = 450.0
## Heat the body can hold (J) and shed (W).
@export var heat_capacity_j: float = 30000.0
@export var heat_dissipation_w: float = 380.0

@export_group("Other stat bases")
## Base values of the stats without a field above (agility, profile,
## connectivity...). Missing ones use Stats.DEFS (1.0 for multipliers).
@export var stat_bases: Dictionary[StringName, float] = {}

@export_group("Load (mass vs strength)")
## The load the muscles feel is mass ÷ usable strength. Up to load_free_kg
## nothing changes; over it, speed, jump and wall-run fall off linearly
## until load_free_kg + load_span_kg, where they're down by load_max_penalty.
@export var load_free_kg: float = 104.0
@export var load_span_kg: float = 70.0
@export_range(0.0, 0.9) var load_max_penalty: float = 0.4
## Below load_free_kg the body is light on its feet: up to this bonus at
## load_light_kg or less.
@export var load_light_kg: float = 88.0
@export_range(0.0, 0.3) var load_light_bonus: float = 0.06

@export_group("Structure")
## Usable strength is at most structure × this: muscles stronger than the
## bones can take are throttled.
@export var strength_per_structure: float = 1.3

@export_group("Neural link")
## Metres of drone/remote link range per point of connectivity.
@export var link_m_per_connectivity: float = 40.0

@export_group("Heat")
## Stored heat raises your signature: × (1 + this × heat fraction).
@export var heat_signature: float = 1.0
## At full stored heat (overheated) health stops regenerating.
@export var overheat_stops_regen: bool = true
