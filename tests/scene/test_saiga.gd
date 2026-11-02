extends GutTest
## The Saiga-12K in the real test room, driven through the controller actions:
## buck fires a pattern of pellets that counts as one shot, the D-pad swaps
## shell types (slugs mount the optic and tint the magazine tape), aiming with
## slugs goes through the PSO-pattern scope, and Dragon's Breath sets a dummy
## alight.

const BUCK: int = 0
const SLUG: int = 1
const DB: int = 2

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var dummy: TargetDummy


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	weapon = player.weapon()
	await wait_physics_frames(5)
	weapon.select_now(weapon.index_of("Saiga-12K"))
	dummy = room.shooting_range.dummies[0]
	# Stand 5 m in front of the first dummy (it faces +Z).
	player.global_position = dummy.global_position + dummy.global_basis.z * 5.0
	await wait_physics_frames(3)
	GunplayDemo.aim_at(player, dummy.parts[&"chest"].global_position)
	await wait_physics_frames(2)


func after_each() -> void:
	for action: StringName in [&"aim", &"fire", &"reload", &"switch_weapon", &"item_next", &"item_prev"]:
		Input.action_release(action)
	Fx.enabled = true
	Engine.time_scale = 1.0


func _shell_text() -> String:
	for child: Node in room.get_children():
		if child.has_method(&"shell_text"):
			return str(child.call(&"shell_text"))
	return "<no hud>"


func _press(action: StringName) -> void:
	Input.action_press(action)
	await wait_physics_frames(2)
	Input.action_release(action)


func test_saiga_is_in_the_loadout_with_buck_loaded() -> void:
	assert_eq(weapon.data.display_name, "Saiga-12K")
	assert_eq(weapon.chamber_ammo().display_name, "00 Buck")
	assert_eq(weapon.mechanism.loaded(), 11)
	assert_false(weapon.rig().optic_mounted(), "no optic on buck")
	assert_eq(_shell_text(), "00 BUCK")


func test_one_buck_shell_is_nine_pellets_and_one_shot() -> void:
	var stats: RangeStats = room.shooting_range.stats
	stats.reset()
	var before: int = Ballistics.rounds_fired
	var health: float = dummy.health
	await _press(&"fire")
	await wait_physics_frames(8)
	assert_eq(Ballistics.rounds_fired - before, 9, "nine 00 pellets")
	assert_eq(stats.shots, 1)
	assert_eq(stats.hits, 1, "several pellets hit, it counts once")
	assert_true(dummy.dead or dummy.health < health - 60.0, "at 5 m the pattern lands together (%.0f HP left)" % dummy.health)
	assert_eq(weapon.mechanism.loaded(), 10)


func test_dpad_swaps_to_slugs_mounts_the_optic_and_tints_the_magazine() -> void:
	await _press(&"item_next")
	assert_eq(weapon.selected_ammo().display_name, "Slug")
	assert_eq(weapon.chamber_ammo().display_name, "00 Buck", "nothing changes until the delay is up")
	assert_true(_shell_text().contains("SLUG"), "HUD shows what's coming: %s" % _shell_text())
	await wait_seconds(weapon.data.ammo_select_delay + 0.1)
	assert_true(weapon.is_reloading(), "swap under way")
	await wait_seconds(weapon.data.reload_empty_time + 0.2)
	assert_false(weapon.is_reloading())
	assert_eq(weapon.chamber_ammo().display_name, "Slug")
	assert_eq(weapon.magazine_ammo().display_name, "Slug")
	assert_true(weapon.rig().optic_mounted(), "PSO-pattern optic on")
	assert_true(weapon.rig().shell_color().is_equal_approx(weapon.data.ammo_types[SLUG].color), "tape shows the slug colour")
	assert_eq(_shell_text(), "SLUG")
	var before: int = Ballistics.rounds_fired
	await _press(&"fire")
	assert_eq(Ballistics.rounds_fired - before, 1, "one slug")


func test_two_quick_presses_skip_to_dragons_breath() -> void:
	await _press(&"item_next")
	await _press(&"item_next")
	await wait_seconds(weapon.data.ammo_select_delay + weapon.data.reload_empty_time + 0.3)
	assert_eq(weapon.chamber_ammo().display_name, "Dragon's Breath")
	assert_false(weapon.rig().optic_mounted())


func test_aiming_with_slugs_looks_through_the_scope() -> void:
	weapon.select_ammo_now(SLUG)
	await wait_physics_frames(2)
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.optic_ads_time + 0.25)
	assert_almost_eq(weapon.scope_amount(), 1.0, 0.01)
	assert_true(weapon.rig().is_scoped(), "viewmodel steps aside for the scope view")
	assert_almost_eq(player.fov_scale, weapon.data.optic_fov_scale, 0.01, "1x optic: barely any zoom")
	assert_lt(weapon.spread, 0.1, "slugs group tight when aimed")
	Input.action_release(&"aim")
	await wait_seconds(weapon.data.optic_ads_time + 0.1)
	assert_false(weapon.rig().is_scoped())


func test_buck_aims_over_the_irons_without_the_scope() -> void:
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.2)
	assert_eq(weapon.scope_amount(), 0.0)
	assert_false(weapon.rig().is_scoped())
	assert_gt(weapon.reticle_spread, weapon.data.ammo_types[BUCK].pattern_deg * 0.99, "the pattern stays when aimed")


func test_dragons_breath_sets_the_dummy_alight() -> void:
	weapon.select_ammo_now(DB)
	await wait_physics_frames(2)
	var before: int = Ballistics.rounds_fired
	await _press(&"fire")
	assert_eq(Ballistics.rounds_fired - before, 14)
	var embers_seen: int = 0
	for i: int in 6:
		await wait_physics_frames(1)
		embers_seen = maxi(embers_seen, Ballistics.ember_count())
	assert_gt(embers_seen, 0, "embers drawn as glowing streaks")
	assert_true(dummy.is_burning() or dummy.dead, "the dummy caught fire")
	var hp: float = dummy.health
	await wait_seconds(1.0)
	assert_true(dummy.dead or dummy.health < hp - 10.0, "it keeps burning (%.0f -> %.0f HP)" % [hp, dummy.health])
