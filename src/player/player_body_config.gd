class_name PlayerBodyConfig
extends Resource
## The augmented body's durability (data/player/body_default.tres). Parts will
## change these in M2 (trauma plating, nanoweave, hemostatic nanites).

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
## Loadout capacity budget (parts cost 1-4 each).
@export var capacity: int = 12
## What the body can carry before heavy weapons slow it (M3).
@export var carry_kg: float = 40.0
## The spinal power cell: reserve (J) and what it supplies (W).
@export var power_capacity_j: float = 60000.0
@export var power_supply_w: float = 450.0
## Heat the body can hold (J) and shed (W).
@export var heat_capacity_j: float = 90000.0
@export var heat_dissipation_w: float = 380.0
