class_name NightAtmosphereConfig
extends Resource
## Look of a night map: exposure, fog, rain, glow, sky, water.
## data/levels/chinatown_night.tres holds the Chinatown values.

@export_group("Exposure")
@export var exposure: float = 1.0
@export var lightmap_gain: float = 1.0
@export var emission_gain: float = 1.0
@export var ambient_color: Color = Color(0.09, 0.1, 0.15)
@export var ambient_energy: float = 1.0
@export var saturation: float = 1.08
@export var contrast: float = 1.06

@export_group("Glow")
@export var glow_intensity: float = 0.9
@export var glow_bloom: float = 0.04
@export var glow_threshold: float = 0.9

@export_group("Fog")
@export var fog_color: Color = Color(0.07, 0.075, 0.1)
@export var fog_density: float = 0.016
@export var fog_sky_affect: float = 0.35
@export var fog_height: float = 0.6
@export var fog_height_density: float = 0.12

@export_group("Rain")
@export var rain_amount: int = 1400
@export var rain_wetness: float = 0.85
@export var puddles: float = 0.55
@export var rain_color: Color = Color(0.62, 0.66, 0.75, 0.22)
@export var rain_speed: float = 11.0
@export var rain_wind: Vector2 = Vector2(0.8, -0.4)

@export_group("Moon")
@export var moon_color: Color = Color(0.55, 0.65, 1.0)
@export var moon_energy: float = 0.18
@export var moon_dir_deg: Vector2 = Vector2(-40.0, 150.0)

@export_group("Water")
@export var water_color: Color = Color(0.008, 0.014, 0.018)
@export var water_reflect: float = 1.0
