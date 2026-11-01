class_name SurfaceMaterial
extends Resource
## How a material takes a bullet (docs/design.md §5.2). One .tres per
## material in data/surfaces/, collected in surface_library.tres.
##
## Penetration is energy based: crossing `t` centimetres costs
## `t * resistance_j_per_cm` joules. A round that can't pay stops inside and
## deposits all its energy; one that can exits slower and slightly deflected.

@export var id: StringName = &"concrete"
@export var display_name: String = "Concrete"

@export_group("Penetration")
## Joules lost per centimetre of material crossed.
@export_range(0.0, 20000.0) var resistance_j_per_cm: float = 1800.0
## Random change of direction on exit, degrees (wood grain, bone, rebar).
@export_range(0.0, 30.0) var exit_deflection_deg: float = 2.0
## Below this angle between the round and the surface the round may glance off.
@export_range(0.0, 45.0) var ricochet_max_angle_deg: float = 12.0
## Chance to ricochet when under the angle above (hard surfaces only).
@export_range(0.0, 1.0) var ricochet_chance: float = 0.6
## Fraction of energy a ricochet keeps.
@export_range(0.0, 1.0) var ricochet_energy_keep: float = 0.45

@export_group("Destruction")
## Multiplies damage the material itself takes (destructible panels, props).
@export_range(0.0, 10.0) var structural_damage_scale: float = 1.0
## Whether exits throw spall/debris from the far side.
@export var spalls: bool = false

@export_group("Look and sound")
@export var decal_color: Color = Color(0.12, 0.12, 0.12)
## Bullet hole radius in metres.
@export_range(0.001, 0.05) var decal_radius: float = 0.008
@export var particle_color: Color = Color(0.6, 0.6, 0.58)
## dust, sparks, splinters, chalk, blood
@export var particle_kind: StringName = &"dust"
@export_range(1, 40) var particle_count: int = 10
## Sound bank name in Sfx (impact_<name>).
@export var impact_sound: StringName = &"concrete"
@export var is_flesh: bool = false
