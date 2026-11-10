class_name ArcProjectorData
extends ActivePartData
## AD-2 Arc Projector (2026-11-10): an electrolaser on a mast over the right
## shoulder. A UV laser ionizes a channel through the air to whoever the
## operative is looking at and a capacitor bank dumps down it; the arc then
## jumps to the next body within reach, and the next. The gun stays in the
## hands: LB (with it selected) raises the mast and fires; LB again fires
## the next charge; it folds away by itself. Each discharge takes
## `discharge_j` straight out of the power reserve. Tuning in
## data/body/parts/ad2_arc_projector.tres.

@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Discharge")
## How far the first arc reaches (m) and the half-angle (deg) of the cone it finds a target in.
@export var reach: float = 22.0
@export_range(1.0, 60.0) var cone_deg: float = 16.0
## How far (m) the arc jumps from one body to the next.
@export var chain_reach: float = 7.0
## Bodies after the first one, with the base power reserve; one more per
## `chain_per_j` of extra reserve (an FB-1 fuel bladder).
@export var chains: int = 2
@export var chain_per_j: float = 30000.0
@export var max_chains: int = 6
## Damage to the first body, and what's left for each one after it.
@export var damage: float = 130.0
@export_range(0.1, 1.0) var chain_falloff: float = 0.7
## Joules from the power reserve per discharge.
@export var discharge_j: float = 18000.0
## Heat into the body per discharge (J).
@export var heat_j: float = 3000.0
## Seconds between discharges while the mast is up, and how long it stays
## up after the last one.
@export var refire: float = 0.55
@export var linger: float = 2.2
## Charges refill at regen_per_s × headroom ÷ this (W), between the limits.
@export var power_ref_w: float = 300.0
@export var recharge_min_scale: float = 0.35
@export var recharge_max_scale: float = 1.8

@export_group("Look")
@export var bolt_color: Color = Color(0.55, 0.75, 1.0)
@export var glow_idle: float = 2.0
@export var glow_flash: float = 16.0
@export var camera_kick_deg: Vector3 = Vector3(1.6, 0.5, 1.2)
@export var rumble_fire: Vector3 = Vector3(0.8, 0.6, 0.18)
