class_name MeshArmData
extends ActivePartData
## NT-5 Prehensile Mesh Arm (owner, 2026-11-10: "ultra prehensile nanotech
## mesh arm thing that grabs and can throw enemies"). The left arm is a
## braid of carbon-nanotube muscle mesh. LB (with it selected) unbraids it;
## RT shoots it out at whoever is under the crosshair and wraps him; he's
## hauled in and held in front of you (he takes the rounds meant for you);
## RT again throws him where you're looking. LB folds the arm away (and
## drops whoever it holds). How far and how hard it throws comes from the
## body's usable strength and impact. Tuning in
## data/body/parts/nt5_mesh_arm.tres.

@export var scene: PackedScene
@export var viewmodel: ViewmodelConfig

@export_group("Reach")
## How far it shoots (m), how close to the crosshair the target has to be
## (deg), and how fast the tendril travels and reels (m/s).
@export var reach: float = 18.0
@export_range(1.0, 45.0) var cone_deg: float = 8.0
@export var shoot_speed: float = 75.0
@export var reel_speed: float = 40.0

@export_group("Hold")
## Where the body hangs, relative to the camera (m): left, down, forward.
@export var hold_offset: Vector3 = Vector3(-0.75, -0.35, -3.0)
## How firmly it's pulled there (1/s) and the fastest it's dragged (m/s).
@export var hold_rate: float = 10.0
@export var hold_max_speed: float = 26.0

@export_group("Throw")
## Throw speed (m/s) at `strength_ref` usable strength and impact ×1; it
## scales with usable strength ÷ ref × √impact, between the limits.
@export var throw_speed: float = 17.0
@export var strength_ref: float = 1.15
@export var min_throw: float = 9.0
@export var max_throw: float = 34.0
## Upward speed added to every throw (m/s).
@export var throw_lift: float = 2.5

@export_group("Feel")
@export var camera_kick_grab_deg: Vector3 = Vector3(-1.0, -0.8, -1.5)
@export var camera_kick_throw_deg: Vector3 = Vector3(2.2, 1.5, 2.5)
@export var rumble_grab: Vector3 = Vector3(0.5, 0.8, 0.18)
@export var rumble_throw: Vector3 = Vector3(0.8, 1.0, 0.22)

@export_group("Look")
@export var radius: float = 0.022
@export var glow_color: Color = Color(0.36, 0.86, 0.78)
