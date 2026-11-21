extends GutTest
## Weapon wheel and reticles in the real test room (owner, 2026-11-02):
## tap Y swaps back to the previous gun, hold Y opens the wheel (time slows,
## look stops, the stick picks a category, the D-pad scrolls the guns in it
## (owner, 2026-11-20: GTA V's wheel), letting go draws the pick; reticles are
## seaglass and turn crimson over an enemy; the shotgun's reticle is a
## circle, a dot with slugs.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var hud: Node


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	weapon = player.weapon()
	for child: Node in room.get_children():
		if child.has_method(&"reticle_state"):
			hud = child
	await wait_physics_frames(int(weapon.data.draw_time * 60.0) + 10)


func after_each() -> void:
	weapon.end_script_input()
	for action: StringName in [&"aim", &"fire", &"switch_weapon"]:
		Input.action_release(action)
	TimeControl.set_slowmo(1.0)
	Fx.enabled = true
	Engine.time_scale = 1.0


func _reticle_shape() -> int:
	var st: Dictionary = hud.call(&"reticle_state")
	var shape: int = st["shape"]
	return shape


func _reticle_color() -> Color:
	var st: Dictionary = hud.call(&"reticle_state")
	var c: Color = st["color"]
	return c


## Two process frames: `process_frame` is emitted before nodes' _process runs.
func _frames() -> void:
	await get_tree().process_frame
	await get_tree().process_frame


func _real_wait(seconds: float) -> void:
	var until: int = Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < until:
		await get_tree().process_frame


## Holds Y with the stick on a category's wedge.
func _point_at(category: int) -> void:
	var ang: float = category * TAU / PlayerWeapon.wheel_categories()
	weapon.script_wheel(true, Vector2(sin(ang), -cos(ang)))
	await _frames()


func _names(slots_in: Array[int]) -> PackedStringArray:
	var out: PackedStringArray = PackedStringArray()
	for i: int in slots_in:
		out.append(weapon.slots[i].data.display_name)
	return out


func test_guns_are_grouped_by_category() -> void:
	assert_eq(PlayerWeapon.wheel_categories(), 6)
	assert_eq(_names(weapon.wheel_guns(WeaponData.WheelCategory.PISTOLS)), PackedStringArray(["Five-seveN SR", "Glock 22 (switch)"]))
	assert_eq(_names(weapon.wheel_guns(WeaponData.WheelCategory.SMGS)), PackedStringArray(["MP5/SD-L"]))
	assert_eq(_names(weapon.wheel_guns(WeaponData.WheelCategory.SHOTGUNS)), PackedStringArray(["Saiga-12K", "SPAS-12"]))
	assert_eq(_names(weapon.wheel_guns(WeaponData.WheelCategory.RIFLES)), PackedStringArray(["M14/P", "The Governor", "AUG A1"]))
	assert_eq(_names(weapon.wheel_guns(WeaponData.WheelCategory.HEAVY)), PackedStringArray(["MG42/A", "M32A1 MGL"]))
	assert_eq(_names(weapon.wheel_guns(WeaponData.WheelCategory.SPECIAL)), PackedStringArray(["RC-6 Lance", "SL-9 Slagger"]))
	var total: int = 0
	for c: int in PlayerWeapon.wheel_categories():
		total += weapon.wheel_guns(c).size()
	assert_eq(total, weapon.slots.size(), "every gun is in exactly one category")


func test_dpad_scrolls_the_guns_in_a_category() -> void:
	weapon.script_wheel(true)
	await _real_wait(weapon.wheel_config.hold_time + 0.1)
	assert_true(weapon.wheel_open)
	await _point_at(WeaponData.WheelCategory.RIFLES)
	assert_eq(weapon.slots[weapon.wheel_pick].data.display_name, "M14/P", "first rifle shown")
	var order: PackedStringArray = PackedStringArray()
	for step: int in [1, 1, 1, -1]:
		weapon.script_wheel_cycle(step)
		await _frames()
		order.append(weapon.slots[weapon.wheel_pick].data.display_name)
	assert_eq(order, PackedStringArray(["The Governor", "AUG A1", "M14/P", "AUG A1"]), "right, right, wraps, left")
	assert_eq(weapon.wheel_category, WeaponData.WheelCategory.RIFLES, "the D-pad stays in the category")
	weapon.script_wheel(false)
	await wait_seconds(weapon.data.holster_time + weapon.loadout[weapon.index_of("AUG A1")].draw_time + 0.3)
	assert_eq(weapon.data.display_name, "AUG A1", "letting go draws the gun shown")
	# Back on the wheel: the rifles remember the AUG, the pistols the Five-seveN.
	weapon.script_wheel(true)
	await _real_wait(weapon.wheel_config.hold_time + 0.1)
	await _point_at(WeaponData.WheelCategory.PISTOLS)
	assert_eq(weapon.slots[weapon.wheel_pick].data.display_name, "Five-seveN SR")
	await _point_at(WeaponData.WheelCategory.RIFLES)
	assert_eq(weapon.slots[weapon.wheel_pick].data.display_name, "AUG A1", "the category remembers its last pick")
	weapon.script_wheel(false)


func test_dpad_on_the_wheel_scrolls_and_leaves_the_actives_alone() -> void:
	var before: int = player.augments.selected
	weapon.script_wheel(true)
	await _real_wait(weapon.wheel_config.hold_time + 0.1)
	await _point_at(WeaponData.WheelCategory.RIFLES)
	var first: int = weapon.wheel_pick
	Input.action_press(&"active_select_3")
	await wait_physics_frames(2)
	Input.action_release(&"active_select_3")
	await _frames()
	assert_ne(weapon.wheel_pick, first, "D-pad right scrolled the rifles")
	assert_eq(player.augments.selected, before, "the active part selection didn't change")
	weapon.script_wheel(false)


func test_an_empty_category_is_skipped() -> void:
	var keep: Array[WeaponData] = [weapon.loadout[weapon.index_of("Five-seveN SR")],
			weapon.loadout[weapon.index_of("AUG A1")], weapon.loadout[weapon.index_of("MG42/A")]]
	weapon.set_guns(keep)
	await wait_seconds(0.6)
	weapon.script_wheel(true)
	await _real_wait(weapon.wheel_config.hold_time + 0.1)
	assert_true(weapon.wheel_open)
	await _point_at(WeaponData.WheelCategory.RIFLES)
	assert_eq(weapon.slots[weapon.wheel_pick].data.display_name, "AUG A1")
	await _point_at(WeaponData.WheelCategory.SHOTGUNS)
	assert_eq(weapon.wheel_category, WeaponData.WheelCategory.RIFLES, "no shotgun carried: the highlight stays")
	weapon.script_wheel(false)


func test_stick_directions_map_to_wheel_slots() -> void:
	assert_eq(PlayerWeapon.wheel_slot(Vector2(0, -1), 5), 0, "up = slot 0")
	assert_eq(PlayerWeapon.wheel_slot(Vector2(1, -0.3), 5), 1, "right-ish = next clockwise")
	assert_eq(PlayerWeapon.wheel_slot(Vector2(-1, -0.3), 5), 4, "left-ish = last")
	assert_eq(PlayerWeapon.wheel_slot(Vector2(0, -1), 4), 0)
	assert_eq(PlayerWeapon.wheel_slot(Vector2(1, 0), 4), 1)
	assert_eq(PlayerWeapon.wheel_slot(Vector2(0, 1), 4), 2)
	assert_eq(PlayerWeapon.wheel_slot(Vector2(-1, 0), 4), 3)


func test_every_gun_is_on_the_wheel() -> void:
	var names: PackedStringArray = PackedStringArray()
	for s: PlayerWeapon.Slot in weapon.slots:
		names.append(s.data.display_name)
	for want: String in ["Five-seveN SR", "MG42/A", "Saiga-12K", "RC-6 Lance", "M14/P", "MP5/SD-L", "M32A1 MGL"]:
		assert_true(names.has(want), "%s in the loadout %s" % [want, names])


func test_tap_y_swaps_to_the_previous_gun_and_back() -> void:
	var rail: int = weapon.index_of("RC-6 Lance")
	weapon.select_now(rail)
	weapon.select_now(weapon.index_of("Saiga-12K"))
	weapon.script_wheel(true)
	await _frames()
	weapon.script_wheel(false)
	await wait_seconds(weapon.data.holster_time + weapon.loadout[rail].draw_time + 0.2)
	assert_false(weapon.wheel_open, "a tap never opens the wheel")
	assert_eq(weapon.data.display_name, "RC-6 Lance", "tap went back to the previous gun")


func test_hold_y_opens_the_wheel_slows_time_and_the_stick_picks() -> void:
	var start_pitch: float = player.pitch
	weapon.script_wheel(true)
	await _real_wait(weapon.wheel_config.hold_time + 0.1)
	assert_true(weapon.wheel_open, "holding Y opens the wheel")
	assert_almost_eq(Engine.time_scale, weapon.wheel_config.time_scale, 0.01, "game slowed")
	assert_true(player.look_blocked, "the right stick picks instead of looking")
	var target: int = weapon.index_of("Saiga-12K")
	await _point_at(WeaponData.WheelCategory.SHOTGUNS)
	assert_eq(weapon.wheel_category, WeaponData.WheelCategory.SHOTGUNS, "stick points at the shotguns")
	assert_eq(weapon.wheel_pick, target, "the Saiga is the shotgun shown")
	# Firing is held while the wheel is up.
	var loaded: int = weapon.mechanism.loaded()
	Input.action_press(&"fire")
	await wait_physics_frames(3)
	Input.action_release(&"fire")
	assert_eq(weapon.mechanism.loaded(), loaded, "no shot while picking")
	weapon.script_wheel(false)
	await _frames()
	assert_false(weapon.wheel_open)
	assert_almost_eq(Engine.time_scale, 1.0, 0.01, "full speed again")
	assert_false(player.look_blocked)
	assert_almost_eq(player.pitch, start_pitch, 0.0001)
	await wait_seconds(weapon.loadout[0].holster_time + weapon.loadout[target].draw_time + 0.2)
	assert_eq(weapon.data.display_name, "Saiga-12K", "letting go draws the pick")


func test_releasing_on_the_gun_in_hand_keeps_it() -> void:
	weapon.script_wheel(true)
	await _real_wait(weapon.wheel_config.hold_time + 0.1)
	assert_true(weapon.wheel_open)
	weapon.script_wheel(false)
	await wait_physics_frames(5)
	assert_false(weapon.is_switching(), "no stick input = stay on the current gun")


func test_reticle_is_seaglass_and_turns_crimson_over_an_enemy() -> void:
	assert_not_null(hud, "HUD in the room")
	GunplayDemo.aim_at(player, Vector3(-30.0, 3.0, -40.0))  # empty wall
	await wait_physics_frames(4)
	await get_tree().process_frame
	assert_false(weapon.over_enemy)
	var calm: Color = _reticle_color()
	assert_almost_eq(calm.g, ReticleStyle.SEAGLASS.g, 0.02, "seaglass by default")
	var d: Enemy = room.shooting_range.targets[0]
	GunplayDemo.aim_at(player, d.parts[&"chest"].global_position)
	await wait_physics_frames(4)
	await wait_seconds(0.15)
	assert_true(weapon.over_enemy, "line of sight on the dummy")
	var hot: Color = _reticle_color()
	assert_almost_eq(hot.r, ReticleStyle.CRIMSON.r, 0.02, "crimson over an enemy")
	assert_almost_eq(hot.g, ReticleStyle.CRIMSON.g, 0.02)


func test_shotgun_reticle_is_a_circle_and_a_dot_with_slugs() -> void:
	assert_eq(_reticle_shape(), 0, "pistol: cross")
	weapon.select_now(weapon.index_of("Saiga-12K"))
	await wait_physics_frames(2)
	await get_tree().process_frame
	assert_eq(_reticle_shape(), 1, "buck: circle")
	weapon.select_ammo_now(1)  # slug
	await wait_physics_frames(2)
	await get_tree().process_frame
	assert_eq(weapon.round_data().pellets, 1)
	assert_eq(_reticle_shape(), 2, "slugs: dot")


func test_rail_reflex_reticle_follows_the_enemy_colour() -> void:
	weapon.select_now(weapon.index_of("RC-6 Lance"))
	var rig: ViewmodelRig = weapon.rig()
	assert_true(rig.has_part(&"reticle"), "rail carbine reticle is its own part")
	GunplayDemo.aim_at(player, room.shooting_range.targets[0].parts[&"chest"].global_position)
	await wait_physics_frames(4)
	await wait_seconds(0.15)
	assert_almost_eq(rig.reticle_color().r, ReticleStyle.CRIMSON.r, 0.02)
