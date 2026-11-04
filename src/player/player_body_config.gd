class_name PlayerBodyConfig
extends Resource
## The augmented body's durability (data/player/body_default.tres). Parts will
## change these in M2 (trauma plating, nanoweave, hemostatic nanites).

@export_range(10.0, 2000.0) var max_health: float = 200.0
## Damage per kJ of a round's energy when it hits (the subdermal armour
## spreads it): a Type 56 round (2 kJ) does 18, a 00 buck pellet (0.28 kJ) 2.5.
@export_range(0.5, 100.0) var damage_per_kj: float = 9.0
## Seconds without being hit before healing starts, and health per second after.
@export_range(0.0, 20.0) var regen_delay: float = 3.5
@export_range(0.0, 500.0) var regen_rate: float = 45.0
## Seconds dead before respawning.
@export_range(0.5, 10.0) var respawn_time: float = 3.0
