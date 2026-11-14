class_name MenuSceneConfig
extends Resource
## Staging of the main menu (owner, 2026-11-14): where the operative leans
## on the Chinatown restaurant front, the two camera framings and the
## cigarette's rhythm. Positions are Godot world coordinates on the
## Chinatown map. Values in data/levels/main_menu.tres.

@export_group("Figure")
## His feet (on the pavement), and which way he faces (deg, 0 = +Z, the street).
@export var figure_position: Vector3 = Vector3(-15.4, 0.0, -11.76)
@export var figure_yaw_deg: float = 0.0
## How far he leans back on the wall (deg).
@export var lean_deg: float = 12.0

@export_group("Camera")
@export var fov: float = 38.0
## The main menu: he stands right of centre, the menu on the left.
@export var main_cam_position: Vector3 = Vector3(-14.45, 1.45, -8.2)
@export var main_cam_target: Vector3 = Vector3(-16.1, 1.2, -11.9)
## The loadout screen: he stands in the clear left quarter of the screen.
@export var loadout_cam_position: Vector3 = Vector3(-15.2, 1.15, -7.7)
@export var loadout_cam_target: Vector3 = Vector3(-13.6, 0.95, -11.8)
## Seconds the camera takes between framings.
@export var cam_move_time: float = 0.7
## Slow drift of the camera (m) so the shot breathes.
@export var cam_drift: float = 0.03

@export_group("Cigarette")
## One cycle: raise, drag, lower, exhale, then idle until the next.
@export var cycle_seconds: float = 10.0
@export var raise_seconds: float = 0.9
@export var drag_seconds: float = 1.3
@export var lower_seconds: float = 0.9
@export var exhale_seconds: float = 2.0
## Ember light (one dynamic light, lights only him): idle and drawing.
@export var ember_energy_idle: float = 0.12
@export var ember_energy_drag: float = 0.55
@export var ember_range: float = 0.6

@export_group("Key light")
## A soft light from the street side on him only (the map is baked).
@export var key_position: Vector3 = Vector3(-13.2, 2.6, -9.6)
@export var key_color: Color = Color(0.62, 0.74, 1.0)
@export var key_energy: float = 1.3
