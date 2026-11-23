extends GutTest
## Two game fixes that came with the trailer (docs/trailer.md): the enemy
## muzzle flash is UV-mapped and alpha-blended (it drew as a white card), and
## TimeControl's clock is the wall clock outside Movie Maker.


func test_enemy_muzzle_flash_has_uvs_and_blends() -> void:
	var room: TestRoom = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	await wait_physics_frames(5)
	var e: Enemy = room.shooting_range.targets[0]
	var flash: MeshInstance3D = e._flash
	assert_not_null(flash)
	var arrays: Array = flash.mesh.surface_get_arrays(0)
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	assert_gt(uvs.size(), 0, "the flash mesh has UVs")
	var spread: float = 0.0
	for uv: Vector2 in uvs:
		spread = maxf(spread, uv.length())
	assert_gt(spread, 0.9, "the UVs cover the texture, not one texel")
	var mat: StandardMaterial3D = flash.material_override as StandardMaterial3D
	assert_eq(mat.transparency, BaseMaterial3D.TRANSPARENCY_ALPHA)


func test_clock_is_the_wall_clock_outside_movie_maker() -> void:
	assert_false(OS.has_feature("movie"))
	assert_almost_eq(float(TimeControl.now_msec()), float(Time.get_ticks_msec()), 20.0)
