class_name ViewmodelConfig
extends Resource
## Where the first-person weapon and arms sit relative to the eye. Positions are
## in the weapon's model space (glTF axes: +X muzzle, +Y up, +Z the gun's right
## side; origin on the bore axis above the grip), so they match the camera
## used for the Blender previews (raw_assets/characters/fp_arms/build.py).

## Eye position in weapon space.
@export var eye_position: Vector3 = Vector3(-0.31, 0.05, -0.058)
## Point in weapon space the eye looks at (screen centre).
@export var look_target: Vector3 = Vector3(0.35, -0.07, -0.004)


## Transform of the weapon relative to the camera.
func weapon_transform() -> Transform3D:
	var eye_in_weapon: Transform3D = Transform3D(Basis.looking_at(look_target - eye_position, Vector3.UP), eye_position)
	return eye_in_weapon.affine_inverse()
