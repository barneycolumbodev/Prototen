extends GutTest
## Survival from the main menu (docs/design.md §8.2): the kit screen picks a
## doctrine, a gun and an active the doctrine can run, and starts the run on
## the menu's map.

var map: ChinatownMap
var cfg: SurvivalConfig = preload("res://data/run/survival.tres")


func before_each() -> void:
	map = (load("res://src/levels/chinatown/chinatown.tscn") as PackedScene).instantiate() as ChinatownMap
	map.force_menu = true
	add_child_autofree(map)
	await wait_physics_frames(10)


func test_survival_is_first_and_starts_a_run() -> void:
	var m: MainMenu = map.menu
	assert_not_null(m)
	assert_eq(m._list.get_child(0), m._buttons["survival"], "Survival first")
	assert_eq(m._buttons["begin"].text, "SANDBOX")
	m.open_kit()
	assert_true(m.kit.visible)
	m.kit.move(2)
	m.kit.cycle(1)
	assert_eq(m.kit.active(), cfg.doctrines[0].starter_actives[1])
	m.kit.move(-2)
	m.kit.cycle(1)
	assert_eq(m.kit.doctrine().display_name, "Reaper")
	assert_eq(m.kit.active(), m.kit.doctrine().starter_actives[0], "a new doctrine starts on its first active")
	m.kit.confirm()
	await wait_until(func() -> bool: return map.survival != null and map.survival.state != null, 4.0)
	assert_not_null(map.survival, "Survival starts on this map")
	# The game's navigation bake warns about voxel rounding (as in test_main_menu).
	for e: GutTrackedError in get_errors():
		if str(e.code).contains("cell_height") or str(e.rationale).contains("cell_height"):
			e.handled = true
	assert_eq(map.survival.state.doctrine.display_name, "Reaper")
	assert_null(map.menu, "the menu is gone")


func test_kit_back_returns_to_the_menu() -> void:
	var m: MainMenu = map.menu
	m.open_kit()
	m.kit.cancelled.emit()
	assert_false(m.kit.visible)
	assert_true(m._panel.visible)
