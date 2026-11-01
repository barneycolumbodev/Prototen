extends GutTest
## First-person hold (playtest 2026-11-01: the crosshair sat on top of a centred,
## upward-angled pistol and looked wrong). Hip-fire guns sit to the lower right
## of the crosshair and point forward, like most console shooters.

const CONFIGS: Array[String] = ["res://data/player/viewmodel_pistol57.tres", "res://data/player/viewmodel_mg42.tres"]


func test_guns_sit_lower_right_of_the_crosshair_pointing_forward() -> void:
	for path: String in CONFIGS:
		var cfg: ViewmodelConfig = load(path) as ViewmodelConfig
		var t: Transform3D = cfg.weapon_transform()
		# Weapon origin (bore above the grip): ahead of the eye, right of and below the line of sight.
		assert_lt(t.origin.z, -0.2, path)
		assert_gt(t.origin.x, 0.05, "%s: gun is right of the crosshair" % path)
		assert_lt(t.origin.y, -0.05, "%s: gun is below the crosshair" % path)
		# The look target lands on the camera's forward axis (screen centre).
		var target_in_cam: Vector3 = t * cfg.look_target
		assert_almost_eq(target_in_cam.x, 0.0, 0.0001, path)
		assert_almost_eq(target_in_cam.y, 0.0, 0.0001, path)
		assert_lt(target_in_cam.z, 0.0, path)
		# The muzzle points forward (within ~12° of the view direction), not up at the crosshair.
		var bore: Vector3 = t.basis * Vector3.RIGHT
		assert_lt(bore.z, -0.97, "%s: bore nearly parallel to the view (%s)" % [path, bore])


func test_player_has_both_guns_and_arms_without_shadows() -> void:
	var player: Player = (load("res://src/player/player.tscn") as PackedScene).instantiate() as Player
	add_child_autofree(player)
	var rigs: Array[Node] = player.find_children("*", "ViewmodelRig", true, false)
	assert_eq(rigs.size(), 2, "pistol rig + MG42 rig")
	for r: Node in rigs:
		var meshes: Array[Node] = r.find_children("*", "MeshInstance3D", true, false)
		assert_gte(meshes.size(), 2, "%s: gun + arms" % r.name)
		for node: Node in meshes:
			assert_eq((node as GeometryInstance3D).cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF)
	var mg: ViewmodelRig = player.get_node(^"Head/Camera3D/ViewmodelMG42") as ViewmodelRig
	for part: StringName in [&"cover", &"magazine", &"belt", &"stock"]:
		assert_true(mg.has_part(part), "MG42 has a moving %s" % part)
