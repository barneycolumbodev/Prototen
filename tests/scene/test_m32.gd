extends GutTest
## The M32A1 grenade launcher in the real test room (docs/design.md §4.8):
## six 40 mm rounds in a revolving cylinder; rounds that fly an arc, arm after
## a few metres and burst on what they hit, or in the air past the point the
## fire control lased; fragments that cover stops; a dud inside the arming
## distance; a cylinder that turns a chamber a shot and swings out to load a
## round at a time.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon
var _gore: int
const GRAVITY: float = 9.8


func before_each() -> void:
	Fx.enabled = false
	_gore = Settings.gore_level
	Settings.gore_level = Gore.Level.MAXIMUM
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("M32A1 MGL"))
	await wait_physics_frames(3)


func after_each() -> void:
	weapon.end_script_input()
	Grenades.clear()
	Settings.gore_level = _gore
	Gore.clear()
	Fx.enabled = true


func _target(i: int = 0) -> Enemy:
	return room.shooting_range.targets[i]


## Turns the view onto `point`.
func _look_at(point: Vector3) -> void:
	var d: Vector3 = (point - player.camera().global_position).normalized()
	player.set_view(atan2(-d.x, -d.z), asin(d.y))
	await wait_process_frames(2)


## A solid wall for cover: `size` m, centred at `at`.
func _wall(at: Vector3, size: Vector3) -> StaticBody3D:
	var body: StaticBody3D = StaticBody3D.new()
	body.collision_layer = Ballistics.LAYER_WORLD
	body.set_meta(SurfaceLibrary.META, &"concrete")
	var shape: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	room.add_child(body)
	body.global_position = at
	return body


## Launches a round straight at `target` (no spread) from `from`.
func _launch_at(from: Vector3, target: Vector3, fuze_at: float = -1.0) -> void:
	var g: GrenadeData = weapon.data.grenade
	var dir: Vector3 = g.solve_launch(from, target, GRAVITY)
	Grenades.launch(g, weapon.data, from, dir * g.muzzle_velocity, player, fuze_at)


func test_it_is_a_six_shot_40mm_revolver() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.display_name, "M32A1 MGL")
	assert_not_null(d.grenade, "launches grenades")
	assert_eq(weapon.mechanism.loaded(), 6, "six rounds")
	assert_eq(weapon.live_chambers(), 6, "a live round in every chamber")
	assert_true(d.loads_singly(), "loads a round at a time")
	for part: StringName in [&"cylinder", &"crane", &"stock", &"lens", &"reticle"]:
		assert_true(weapon.rig().has_part(part), "has a %s" % part)
	for k: int in 6:
		assert_true(weapon.rig().round_visible(k), "case head %d shows" % k)


func test_a_round_bursts_on_a_man_and_kills_him() -> void:
	var e: Enemy = _target(0)
	var chest: Vector3 = e.body.chest_position()
	var bursts: int = Grenades.bursts
	_launch_at(chest + (Vector3(0, 1.6, 12) - chest).normalized() * 16.0, chest)
	await wait_seconds(0.5)
	assert_eq(Grenades.bursts, bursts + 1, "it burst")
	assert_lt(Grenades.last_burst.distance_to(chest), 0.9, "on him (%.2f m from his chest)" % Grenades.last_burst.distance_to(chest))
	assert_false(e.alive, "and he's dead")


func test_inside_the_arming_distance_it_is_a_dud() -> void:
	var e: Enemy = _target(0)
	var chest: Vector3 = e.body.chest_position()
	var bursts: int = Grenades.bursts
	var duds: int = Grenades.duds
	_launch_at(chest + Vector3(0, 0.2, 5.0), chest)
	await wait_seconds(0.4)
	assert_eq(Grenades.bursts, bursts, "no burst at 5 m")
	assert_eq(Grenades.duds, duds + 1, "a dud")
	assert_true(e.alive, "a 230 g blow doesn't kill him")
	assert_lt(e.health, 100.0, "but it hurts (%.0f left)" % e.health)


func test_fragments_stop_at_a_wall() -> void:
	var e: Enemy = _target(0)
	var chest: Vector3 = e.body.chest_position()
	var burst: Vector3 = chest + Vector3(0, -0.6, 2.2)
	_wall(chest + Vector3(0, -0.2, 1.1), Vector3(3.0, 3.0, 0.3))
	await wait_physics_frames(2)
	var g: GrenadeData = weapon.data.grenade
	Explosion.fragments(room, burst, Vector3.UP, g, player, false)
	await wait_physics_frames(3)
	assert_gt(Explosion.last_aimed, 0, "fragments were sent at him")
	assert_eq(e.health, 100.0, "the wall took all of them")


func test_fragments_wound_a_man_in_the_open() -> void:
	var e: Enemy = _target(0)
	var chest: Vector3 = e.body.chest_position()
	var burst: Vector3 = chest + Vector3(0, -1.0, 2.0)
	var g: GrenadeData = weapon.data.grenade
	Explosion.fragments(room, burst, Vector3.UP, g, player, false)
	await wait_physics_frames(3)
	assert_gt(Explosion.last_aimed, 2, "several fragments at 2 m (%d)" % Explosion.last_aimed)
	assert_lt(e.health, 100.0, "they hit him")
	assert_gt(e.zone_hits.size(), 0, "in particular zones: %s" % e.zone_hits)


func test_aimed_it_bursts_over_the_wall_onto_the_man_behind() -> void:
	var e: Enemy = _target(0)
	var feet: Vector3 = e.global_position
	# A wall 1.2 m high, 2.4 m in front of him (toward the player).
	var to_player: Vector3 = (Vector3(0, 0, 12) - feet)
	to_player.y = 0.0
	to_player = to_player.normalized()
	var wall_at: Vector3 = feet + to_player * 2.4
	_wall(wall_at + Vector3(0, 0.6, 0), Vector3(3.0, 1.2, 0.25))
	await wait_physics_frames(2)
	# Aim at the wall's face just under the top edge.
	await _look_at(wall_at + to_player * 0.13 + Vector3(0, 1.05, 0))
	var chest: Vector3 = e.body.chest_position()
	weapon.script_input(false, true)
	for i: int in 40:
		weapon.script_input(false, true)
		await wait_physics_frames(1)
	assert_true(weapon.fcs_locked, "the fire control has a solution")
	assert_false(weapon.fcs_on_body, "lased the wall")
	assert_between(weapon.fcs_range, 9.0, 20.0, "range %.1f m" % weapon.fcs_range)
	var bursts: int = Grenades.bursts
	weapon.script_input(true, true)
	await wait_seconds(0.6)
	assert_eq(Grenades.bursts, bursts + 1, "it burst")
	assert_true(Grenades.last_burst_airburst, "in the air")
	var past: float = (Grenades.last_burst - wall_at).dot(-to_player)
	assert_between(past, 0.3, 2.4, "past the wall, short of him (%.2f m beyond it)" % past)
	assert_lt(Grenades.last_burst.distance_to(chest), 2.5, "close over him")
	assert_false(e.alive, "and it killed him behind his cover")


func test_the_cylinder_turns_a_chamber_a_shot() -> void:
	await _look_at(Vector3(0, 0.0, -10.0))
	var before: Transform3D = weapon.rig().cylinder_transform()
	weapon.script_input(true, false)
	await wait_seconds(0.3)
	assert_eq(weapon.mechanism.loaded(), 5)
	assert_eq(weapon.live_chambers(), 5)
	var after: Transform3D = weapon.rig().cylinder_transform()
	var turned: float = rad_to_deg(before.basis.get_euler().x - after.basis.get_euler().x)
	assert_almost_eq(absf(wrapf(turned, -180.0, 180.0)), 60.0, 2.0, "turned a sixth (%.1f°)" % turned)


func test_reload_swings_out_and_fills_each_chamber() -> void:
	await _look_at(Vector3(0, 0.0, -10.0))
	for i: int in 3:
		weapon.script_input(true, false)
		await wait_seconds(weapon.data.fire_interval + 0.05)
	await wait_seconds(0.4)
	assert_eq(weapon.mechanism.loaded(), 3)
	weapon.script_input(false, false, true)
	await wait_seconds(weapon.data.reload_open_time + 0.1)
	assert_gt(weapon.mechanism.open_amount(), 0.9, "swung out")
	var cyl: Transform3D = weapon.rig().cylinder_transform()
	assert_gt(cyl.origin.length(), 0.03, "the cylinder moved out on the crane")
	var shown: int = 0
	for k: int in 6:
		if weapon.rig().round_visible(k):
			shown += 1
	assert_eq(shown, 3, "spent cases out: three live rounds left")
	await wait_seconds(weapon.data.round_load_time * 3.0 + weapon.data.reload_close_time + 0.3)
	assert_eq(weapon.mechanism.loaded(), 6, "full")
	assert_eq(weapon.live_chambers(), 6)
	assert_eq(weapon.mechanism.open_amount(), 0.0, "shut")


func test_the_hip_marker_shows_where_it_lands() -> void:
	# A wall 14 m out, square to the view (on the floor a grazing hit turns half a
	# degree of spread into a metre along the ground).
	var eye: Vector3 = player.camera().global_position
	var wall_at: Vector3 = Vector3(eye.x, 1.5, eye.z - 14.0)
	_wall(wall_at, Vector3(6.0, 3.0, 0.3))
	await wait_physics_frames(2)
	await _look_at(wall_at + Vector3(0, 0.6, 0.15))
	await wait_physics_frames(4)
	var predicted: Vector3 = weapon.impact_point
	assert_true(predicted.is_finite(), "a landing point")
	assert_lt(predicted.y, wall_at.y + 0.6, "below the aim point: it drops on the way")
	weapon.script_input(true, false)
	await wait_seconds(0.5)
	assert_true(Grenades.last_burst.is_finite())
	assert_lt(Grenades.last_burst.distance_to(predicted), 0.6,
			"burst %.2f m from the marker" % Grenades.last_burst.distance_to(predicted))


func test_a_burst_draws_fire_smoke_dust_and_a_scorch() -> void:
	Fx.enabled = true
	var fx: ExplosionFx = Fx.explosion_fx()
	var scorches: int = fx.scorch_count()
	Explosion.grenade(room, Vector3(0, 0.05, 2.0), Vector3.UP, weapon.data.grenade, weapon.data, player, false)
	await wait_process_frames(3)
	assert_gte(fx.live_puffs(), 5, "fireball, three smoke lobes, a dust ring")
	assert_gt(fx.scorch_count(), scorches, "a scorch on the floor")
