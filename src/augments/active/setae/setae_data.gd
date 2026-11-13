class_name SetaeData
extends ActivePartData
## SX-8 Urticating Setae (owner, 2026-11-13): a bank of 24 ports along the
## back of the left forearm. LB brings the arm forward; nanite assemblers
## grow two long, hair-thin fibres out of every port, and the world slows to
## a crawl (a dead-eye). LT marks the body part under the crosshair (up to
## four men, five with sharper perception; a man can take several marks).
## RT throws: time comes back, the arm whips across and the fibres stiffen
## into needles in flight, home on their marks and leave cavitation wounds
## that take most men apart. Tuning in data/body/parts/sx8_urticating_setae.tres.

@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Dead-eye")
## How fast the world runs while marking, and the operative.
@export_range(0.05, 1.0) var world_scale: float = 0.06
@export_range(0.05, 1.0) var player_scale: float = 0.3
## Real seconds of marking at `processing_ref`; scales with processing, between the limits.
@export var mark_window: float = 5.0
@export var processing_ref: float = 1.2
@export var window_min: float = 3.0
@export var window_max: float = 8.0
## Marks with ordinary perception, one more from `perception_extra` up, never more than `max_marks`.
@export var base_marks: int = 4
@export var perception_extra: float = 1.2
@export var max_marks: int = 5
## How far a mark reaches (m) and how close to the crosshair a body snaps (deg; opens up close in).
@export var reach: float = 45.0
@export var snap_deg: float = 3.5

@export_group("Hairs")
## Fibres per port (24 ports).
@export var per_port: int = 2
## Length (m) and random spread (fraction) of a grown fibre.
@export var hair_length: float = 0.24
@export_range(0.0, 0.6) var length_jitter: float = 0.25
## Width at the root (m).
@export var hair_width: float = 0.0024
## Seconds for one fibre to grow out, and the spread of when they start.
@export var grow_time: float = 0.42
@export var grow_stagger: float = 0.32
## How far (deg) the fibres lean from the port's normal toward the hand.
@export var lean_deg: float = 55.0

@export_group("Throw")
## Real seconds: windup until release, release until the arm is through, follow-through.
@export var windup: float = 0.16
@export var follow: float = 0.38
## Needle speed (m/s) at `strength_ref` usable strength; it scales with √(usable strength ÷ ref).
@export var needle_speed: float = 150.0
@export var strength_ref: float = 1.15
@export var min_strength_scale: float = 0.6
@export var max_strength_scale: float = 1.6
## Real seconds for time to come back after the release.
@export var time_ramp: float = 0.5
## How far (fraction of the distance) the fibres fan out before they turn onto their mark.
@export var fan: float = 0.16

@export_group("Wound")
## The first `hits_per_mark` needles of each bundle are hits of their own (punctures).
@export var hits_per_mark: int = 3
@export var needle_damage: float = 18.0
@export var needle_energy_j: float = 260.0
## The cavity: one hit per mark `cavity_delay` world seconds after the first needle lands. Its energy
## scales with usable strength ÷ ref (the needles carry more); ~12 kJ of violence bursts a torso at Maximum gore.
@export var cavity_delay: float = 0.04
@export var cavity_damage: float = 340.0
@export var cavity_energy_j: float = 11000.0
@export var cavity_impulse: float = 16.0
## Heat into the body per throw (J).
@export var heat_j: float = 4000.0
## Fibres regrow at regen_per_s × headroom ÷ this (W), between the limits.
@export var power_ref_w: float = 250.0
@export var regrow_min_scale: float = 0.5
@export var regrow_max_scale: float = 1.6

@export_group("Look")
@export var glow_color: Color = Color(1.0, 0.46, 0.14)
@export var mark_color: Color = Color(1.0, 0.32, 0.12)
@export var tint: Color = Color(0.55, 0.12, 0.04, 0.5)
@export_range(0.0, 1.0) var saturation: float = 0.18
@export var lowpass_hz: float = 900.0
@export var fov_kick_deg: float = -5.0
@export var camera_kick_deg: Vector3 = Vector3(-1.8, -3.0, -4.0)
@export var rumble_throw: Vector3 = Vector3(0.6, 0.9, 0.25)
@export var rumble_cavity: Vector3 = Vector3(0.4, 0.7, 0.12)
