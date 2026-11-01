extends GutTest
## The first-person viewmodel sits in front of the eye, where the Blender previews put it.


func test_weapon_is_in_front_of_and_below_the_eye() -> void:
	var cfg: ViewmodelConfig = load("res://data/player/viewmodel_pistol57.tres") as ViewmodelConfig
	var t: Transform3D = cfg.weapon_transform()
	# The weapon origin (bore axis above the grip) is ahead of the eye and near the line of sight;
	# the bottom of the grip hangs below it.
	assert_lt(t.origin.z, -0.2)
	assert_almost_eq(t.origin.y, 0.0, 0.05)
	assert_lt((t * Vector3(-0.08, -0.135, 0.0)).y, -0.05)
	# The look target lands on the camera's forward axis (screen centre).
	var target_in_cam: Vector3 = t * cfg.look_target
	assert_almost_eq(target_in_cam.x, 0.0, 0.0001)
	assert_almost_eq(target_in_cam.y, 0.0, 0.0001)
	assert_lt(target_in_cam.z, 0.0)
	# The muzzle points away from the camera.
	assert_lt((t.basis * Vector3.RIGHT).z, -0.8)


func test_player_has_gun_and_arms_without_shadows() -> void:
	var player: Player = (load("res://src/player/player.tscn") as PackedScene).instantiate() as Player
	add_child_autofree(player)
	var rig: ViewmodelRig = player.find_children("*", "ViewmodelRig", true, false)[0] as ViewmodelRig
	assert_not_null(rig)
	var meshes: Array[Node] = rig.find_children("*", "MeshInstance3D", true, false)
	assert_gte(meshes.size(), 2, "pistol + arms")
	for node: Node in meshes:
		assert_eq((node as GeometryInstance3D).cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF)
