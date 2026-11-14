extends GutTest
## Main menu (owner, 2026-11-14): the game opens on the operative, helmet
## off, leaning on the restaurant front smoking; the loadout screen dresses
## him in the scene; Begin starts Chinatown on the same map.

var map: ChinatownMap
var menu: MainMenu


func before_each() -> void:
	map = (load("res://src/levels/chinatown/chinatown.tscn") as PackedScene).instantiate() as ChinatownMap
	map.autostart_spawns = false
	map.force_menu = true
	add_child_autofree(map)
	menu = map.menu
	await wait_physics_frames(10)


func after_each() -> void:
	if PauseMenu.is_open():
		PauseMenu.close()
	get_tree().paused = false


func test_opens_on_the_menu_not_the_game() -> void:
	assert_not_null(menu, "the menu is up")
	assert_null(map.player, "no player yet")
	assert_true(menu.camera.current, "the menu camera")
	assert_false(menu.smoker.appearance.helmet_on, "helmet off: his face")
	assert_false(DebugOverlay.visible, "no debug numbers over the picture")


func test_he_smokes() -> void:
	var s: MenuSmoker = menu.smoker
	s.hold_t = 1.6  # drawing on it
	await wait_process_frames(4)
	var lips: Vector3 = s.global_transform * s.lips()
	var filter_end: Vector3 = s.cig.global_position
	assert_lt(filter_end.distance_to(lips), 0.03, "filter on his lips (%.3f m)" % filter_end.distance_to(lips))
	assert_gt(s.drawing, 0.9, "drawing")
	var drag_energy: float = s.ember_light.light_energy
	s.hold_t = 6.0  # idle
	await wait_process_frames(4)
	assert_gt(s.cig.global_position.distance_to(s.global_transform * s.lips()), 0.2, "down from his mouth")
	assert_gt(drag_energy, s.ember_light.light_energy * 2.0, "the ember flares on a drag")
	s.hold_t = 3.4  # breathing out
	await wait_process_frames(2)
	assert_true(s.breath_smoke.emitting, "smoke out of his mouth")


func test_he_leans_on_the_wall() -> void:
	var s: MenuSmoker = menu.smoker
	var left: Vector3 = s.bone_pose(&"foot.L").origin
	var right: Vector3 = s.bone_pose(&"foot.R").origin
	assert_lt(left.y, 0.15, "left boot on the pavement")
	assert_gt(right.y, 0.3, "right boot up")
	assert_almost_eq(right.z, MenuSmoker.WALL_Z + 0.1, 0.05, "against the wall")
	var chest: Vector3 = s.bone_pose(&"chest").origin
	assert_lt(chest.z, -0.15, "shoulders back on the wall")


func test_the_loadout_screen_dresses_him() -> void:
	menu.open_loadout()
	await wait_process_frames(2)
	assert_true(menu.status.visible, "loadout open")
	assert_false(get_tree().paused, "the scene keeps moving behind it")
	var before: int = menu.smoker.appearance.mounted.size()
	var jug: BodyLoadout = LoadoutStore.presets()[2]
	menu.status.select_preset(2)
	await wait_process_frames(2)
	assert_eq(menu.smoker.appearance.loadout.ids(), jug.ids(), "he wears the preset under the cursor")
	assert_ne(menu.smoker.appearance.mounted.size(), before, "and looks different")
	menu.status.activate()  # A: apply it
	menu.status.close()
	await wait_process_frames(2)
	assert_eq(menu.loadout.ids(), jug.ids(), "the menu keeps what was built")
	assert_eq(menu.smoker.appearance.loadout.ids(), jug.ids())
	assert_false(menu.status.visible)


func test_begin_starts_chinatown_here() -> void:
	menu.begin()
	var t: int = 0
	while map.player == null and t < 120:
		await wait_process_frames(1)
		t += 1
	assert_not_null(map.player, "the game started")
	# The game's navigation bake warns about voxel rounding (as in test_chinatown's setup).
	for e: GutTrackedError in get_errors():
		if str(e.code).contains("cell_height") or str(e.rationale).contains("cell_height"):
			e.handled = true
	await wait_process_frames(2)
	assert_false(is_instance_valid(menu), "the menu is gone")
	assert_true(map.player.camera().current, "through his eyes")
	assert_true(DebugOverlay.visible, "debug overlay back")


func test_options_opens_the_settings_only() -> void:
	PauseMenu.open_options()
	assert_true(PauseMenu.is_open())
	assert_true(PauseMenu.options_only)
	PauseMenu.close()
