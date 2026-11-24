class_name HarvesterHiveData
extends ActivePartData
## HV-3 Harvester Hive (owner, 2026-11-24; docs/design.md §3.4e): a hive in
## the left hand. LB raises the hand and opens the vent in the palm; a swarm
## of harvester microdrones pours out at whoever is nearest the crosshair,
## engulfs him and strips him to the muscle in under a second, then streams
## back into the palm. What they bring back feeds the hive's reactor, which
## floods the operative's blood with repair nanites: a chunk of health. An
## emergency heal that kills. Tuning in data/body/parts/hv3_harvester_hive.tres.

@export var viewmodel: ViewmodelConfig

@export_group("Target")
## Reach at no connectivity (m); each point of connectivity adds `reach_per_link`, up to `reach_max`.
@export var reach: float = 16.0
@export var reach_per_link: float = 3.0
@export var reach_max: float = 30.0
## How far from the crosshair (deg) a body can be and still be picked.
@export var cone_deg: float = 14.0

@export_group("Swarm")
## Harvesters drawn (one draw call, moved by the GPU).
@export var count: int = 640
## Seconds over which they leave the vent, and over which they leave the body.
@export var launch_spread: float = 0.12
@export var return_spread: float = 0.14
## Flight speed out and back (m/s); the trip never takes less than `min_trip` s.
@export var speed_out: float = 42.0
@export var speed_back: float = 48.0
@export var min_trip: float = 0.12
## Seconds to strip a man to the muscle once the swarm is on him.
@export var strip_time: float = 0.7
## How long the flies have to be on him before he's engulfed (drops his gun, stops fighting).
@export var engulf_after: float = 0.04
## A harvester's length (m) and how many pixels it may shrink to at range.
@export var fly_size: float = 0.022
@export var min_pixels: float = 5.0

@export_group("Harvest")
## Health restored, as a share of the body's max health, as the swarm docks.
@export_range(0.0, 1.0) var heal_share: float = 0.38
## Heat into the body (J): the reactor digesting what they brought back.
@export var heat_j: float = 6000.0
## A boss isn't stripped whole: this much of him, this much damage, the full heal.
@export_range(0.0, 1.0) var boss_flay: float = 0.32
@export var boss_damage: float = 240.0
## Morale lost by triad within `witness_m` who see it (scaled by distance), and the suppression it adds.
@export var witness_m: float = 14.0
@export var witness_morale: float = 0.35
@export var witness_suppression: float = 0.5
## The rebuild rate scales with cooling ÷ this (W), between the limits.
@export var cooling_ref_w: float = 380.0
@export var regen_min_scale: float = 0.7
@export var regen_max_scale: float = 1.5

@export_group("Look")
@export var glow_color: Color = Color(1.0, 0.16, 0.09)
## The harvesters' eyes going out, and coming home full.
@export var eye_color: Color = Color(1.0, 0.22, 0.12)
@export var full_color: Color = Color(0.5, 0.02, 0.015)
@export var heal_color: Color = Color(0.9, 0.12, 0.08, 0.55)
@export var fov_kick_deg: float = 2.5
@export var rumble_launch: Vector3 = Vector3(0.35, 0.2, 0.18)
@export var rumble_feed: Vector3 = Vector3(0.25, 0.1, 0.5)
@export var rumble_heal: Vector3 = Vector3(0.5, 0.6, 0.22)
