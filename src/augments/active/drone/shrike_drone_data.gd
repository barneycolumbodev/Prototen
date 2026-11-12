class_name ShrikeDroneData
extends ActivePartData
## SD-3 Shrike (owner, design §3.4: "Shoulder-launched suicide drone. A pod
## on your shoulder opens and launches the drone. You fly it from its
## camera and detonate it."). LB (with it selected) launches one: it leaves
## the pod over the left shoulder, unfolds, and the view cuts to its camera.
## Left stick flies, right stick looks, A/B climb and sink, RT detonates,
## LB cuts the link. Flying it into anything fast enough, or into anyone,
## sets it off. Your body stands where you left it. The neural link
## decides everything: connectivity gates it and sets how far it can go
## (BodyModel.link_range_m), and the picture breaks up near the limit.
## Tuning in data/body/parts/sd3_shrike_drone.tres.

@export var scene: PackedScene

@export_group("Flight")
## Top speed (m/s) and acceleration (m/s²).
@export var speed: float = 15.0
@export var accel: float = 34.0
## Climb and sink speed (m/s).
@export var lift_speed: float = 7.0
## Look rate (deg/s) at full stick; times processing ÷ `processing_ref`.
@export var turn_rate_deg: float = 170.0
@export var processing_ref: float = 1.0
## Seconds of flight.
@export var battery: float = 22.0
## Field of view of its camera (deg, vertical).
@export var camera_fov: float = 84.0
## Where it leaves the body, relative to the operative's camera (m).
@export var launch_offset: Vector3 = Vector3(-0.32, 0.22, 0.05)
## Where it hovers when the view cuts to it.
@export var handover_offset: Vector3 = Vector3(-0.15, 0.25, -1.9)

@export_group("Warhead")
@export var blast_radius: float = 6.5
@export var blast_damage: float = 300.0
## Seconds after launch before it can go off.
@export var arm_time: float = 0.35
## Hitting something at this speed (m/s) or more sets it off.
@export var impact_speed: float = 8.0

@export_group("Link")
## The link drops when the operative's health falls below this fraction.
@export_range(0.0, 1.0) var recall_health: float = 0.3
## Picture noise starts at this fraction of the link range.
@export_range(0.0, 1.0) var static_from: float = 0.6

@export_group("Look")
@export var hud_color: Color = Color(1.0, 0.72, 0.3)
