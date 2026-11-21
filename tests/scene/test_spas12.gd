extends GutTest
## The SPAS-12 in the real test room (owner, 2026-11-20): pump only; after
## every shot the gun comes up, the pump is racked back and slammed home, and
## the gun goes back down before the next. Against the Saiga-12K: slower,
## more damage, a little more range, a tighter pattern and a smaller ring.
## Eight in the tube and one chambered, loaded a shell at a time.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	player.invulnerable = true
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("SPAS-12"))
	await wait_physics_frames(3)


func after_each() -> void:
	weapon.end_script_input()
	Fx.enabled = true


func _saiga() -> WeaponData:
	return load("res://data/weapons/saiga12k.tres") as WeaponData


func _buck() -> AmmoData:
	return load("res://data/weapons/ammo/buck_00.tres") as AmmoData


func test_it_is_an_eight_plus_one_pump_gun() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.display_name, "SPAS-12")
	assert_eq(d.weapon_class, WeaponData.WeaponClass.SHOTGUN)
	assert_true(d.pump_action, "pump only")
	assert_false(d.automatic)
	assert_true(d.loads_singly(), "a shell at a time")
	assert_eq(weapon.mechanism.loaded(), 9, "8 in the tube + 1")
	assert_eq(d.pellets, 11, "a magnum 00 buck load: eleven pellets (owner 2026-11-21, walked back from twelve)")
	for part: StringName in [&"pump", &"support_arm", &"bolt", &"load_round"]:
		assert_true(weapon.rig().has_part(part), "has a %s" % part)
	assert_gte(d.fire_interval, d.pump_delay + d.pump_time, "the pump finishes before the next shot")


func test_slower_harder_further_tighter_than_the_saiga() -> void:
	var d: WeaponData = weapon.data
	var s: WeaponData = _buck().apply_to(_saiga())
	assert_gt(d.fire_interval, s.fire_interval * 3.0, "much slower: %.2f s vs %.2f s" % [d.fire_interval, s.fire_interval])
	var dmg: float = d.muzzle_energy() * d.damage_per_joule * d.pellets
	var sdmg: float = s.muzzle_energy() * s.damage_per_joule * s.pellets
	# Owner, 2026-11-21: "noticeably more lethal per shot than the Saiga"
	# (game balance, not ballistics: one pump shell against a second of fire).
	assert_gt(dmg / sdmg, 2.0, "far more damage per shell (%.0f vs %.0f)" % [dmg, sdmg])
	assert_gt(d.ragdoll_push, 2.0, "a kill throws the man")
	assert_gt(d.stagger_push, 0.0, "a shell that doesn't kill still staggers him")
	assert_gt(d.max_range, s.max_range, "a little more range")
	assert_lt(d.max_range, s.max_range * 1.4)
	assert_lt(d.drag_per_m, s.drag_per_m, "pellets keep their speed further")
	assert_lt(d.pattern_deg, s.pattern_deg, "tighter pattern")
	assert_gt(d.pattern_deg, s.pattern_deg * 0.6, "only slightly tighter")


func test_the_ring_is_smaller_than_the_saigas_and_stays_when_aimed() -> void:
	await wait_physics_frames(5)
	var mine: float = weapon.reticle_spread
	var hud_script: GDScript = load("res://src/ui/hud.gd") as GDScript
	var circle: int = hud_script.call(&"reticle_shape", weapon)
	weapon.select_now(weapon.index_of("Saiga-12K"))
	await wait_physics_frames(5)
	var saiga: float = weapon.reticle_spread
	var saiga_shape: int = hud_script.call(&"reticle_shape", weapon)
	assert_eq(circle, saiga_shape, "the same ring as the Saiga")
	assert_lt(mine, saiga * 0.85, "smaller ring (%.2f° vs %.2f°)" % [mine, saiga])
	assert_gt(mine, saiga * 0.5)
	weapon.select_now(weapon.index_of("SPAS-12"))
	assert_true(weapon.data.reticle_when_aimed, "the folded stock covers the sights: the ring stays")


func test_a_shot_raises_the_gun_and_racks_the_pump() -> void:
	var d: WeaponData = weapon.data
	var rest: Transform3D = weapon.rig().transform
	weapon.script_input(true, false)
	await wait_physics_frames(2)
	assert_eq(weapon.mechanism.loaded(), 8, "fired one")
	assert_true(weapon.hammer_down)
	# Wait to the back of the stroke.
	var waited: float = 0.0
	while weapon.pump_t < 0.44 and waited < 1.5:
		await wait_physics_frames(1)
		waited += 1.0 / Engine.physics_ticks_per_second
	assert_gt(weapon.pump_t, 0.4, "stroke under way")
	assert_lt(weapon.rig().pump_position().x, -d.pump_travel * 0.8, "pump racked back")
	assert_almost_eq(weapon.rig().support_position().x, weapon.rig().pump_position().x, 0.0001, "the hand rides it")
	var up: Transform3D = weapon.rig().transform
	var muzzle_rest: Vector3 = rest * d.muzzle_point
	var muzzle_up: Vector3 = up * d.muzzle_point
	assert_gt(muzzle_up.y - muzzle_rest.y, 0.08, "the barrel comes up (%.3f m)" % (muzzle_up.y - muzzle_rest.y))
	assert_false(weapon.hammer_down, "the stroke cocked it")
	await wait_seconds(d.pump_time * 0.65)
	assert_lt(weapon.pump_t, 0.0, "stroke done")
	assert_almost_eq(weapon.rig().pump_position().x, 0.0, 0.0001, "pump home")


func test_no_second_shot_until_the_pump_is_done() -> void:
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	weapon.script_input(true, false)
	await wait_physics_frames(2)
	await wait_seconds(0.3)
	weapon.script_input(true, false)
	await wait_physics_frames(2)
	assert_eq(shots[0], 1, "mid-pump the trigger does nothing")
	await wait_seconds(weapon.data.fire_interval)
	weapon.script_input(true, false)
	await wait_physics_frames(2)
	assert_eq(shots[0], 2, "ready again after the pump")


func test_reload_a_shell_at_a_time_and_an_empty_gun_is_pumped() -> void:
	weapon.mechanism.magazine = 0
	weapon.mechanism.chambered = false
	weapon.script_input(false, false, true)
	await wait_physics_frames(2)
	assert_true(weapon.is_reloading())
	var d: WeaponData = weapon.data
	await wait_seconds(d.reload_open_time + d.round_load_time * 2.5)
	assert_between(weapon.mechanism.loaded(), 2, 3, "two shells in so far")
	var waited: float = 0.0
	while weapon.is_reloading() and waited < 6.0:
		await wait_physics_frames(1)
		waited += 1.0 / Engine.physics_ticks_per_second
	assert_eq(weapon.mechanism.loaded(), 9, "full: 8 + 1")
	assert_false(weapon.is_reloading())
	# It went in empty: the pump is worked to chamber a shell.
	var saw_stroke: bool = false
	waited = 0.0
	while not saw_stroke and waited < 0.4:
		saw_stroke = weapon.pump_t >= 0.0
		await wait_physics_frames(1)
		waited += 1.0 / Engine.physics_ticks_per_second
	assert_true(saw_stroke, "the pump is worked after an empty reload")


func test_buckshot_at_ten_metres_kills_a_man() -> void:
	var e: Enemy = room.shooting_range.targets[0]
	var at: Vector3 = e.body.hitboxes[&"chest"].global_position
	var from: Vector3 = at + Vector3(0, 0.1, 10.0)
	var dir: Vector3 = (at - from).normalized()
	var d: WeaponData = weapon.data
	var volley: int = 0
	for i: int in d.pellets:
		var id: int = Ballistics.fire(d, from, Ballistics.pattern_dir(dir, d.pattern_deg, i, d.pellets, 0.0,
				RandomNumberGenerator.new()), player, Vector3.INF, volley)
		if volley == 0:
			volley = id
	await wait_physics_frames(6)
	assert_false(e.alive, "one shell to the chest at 10 m")


## Damage one shell from the hip at `dist` m into `zone` does to a gunman who
## can't die of it (so every pellet counts).
func _hip_shell_damage(d: WeaponData, dist: float, zone: StringName, rng: RandomNumberGenerator) -> float:
	var sr: ShootingRange = room.shooting_range
	sr.clear_targets()
	await wait_physics_frames(1)
	var e: Enemy = sr.spawn_target(0)
	await wait_physics_frames(3)
	e.health = 1.0e6
	var at: Vector3 = e.body.hitboxes[zone].global_position
	var from: Vector3 = at + Vector3(0, 0.15, dist)
	var dir: Vector3 = Ballistics.random_in_cone((at - from).normalized(), d.spread_deg(0.0, 0.0, false, 0.0), rng)
	var volley: int = 0
	var phase: float = rng.randf() * TAU
	for i: int in d.pellets:
		var id: int = Ballistics.fire(d, from, Ballistics.pattern_dir(dir, d.pattern_deg, i, d.pellets, phase, rng),
				player, Vector3.INF, volley)
		if volley == 0:
			volley = id
	await wait_physics_frames(8)
	var dmg: float = 0.0
	for z: StringName in e.zone_damage:
		dmg += e.zone_damage[z]
	return dmg


func test_a_shell_does_far_more_damage_than_a_saiga_shell() -> void:
	# Owner, 2026-11-21: "noticeably more lethal per shot than the Saiga".
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var saiga: WeaponData = _buck().apply_to(_saiga())
	for dist: float in [6.0, 14.0]:
		var mine: float = 0.0
		var theirs: float = 0.0
		for t: int in 4:
			mine += await _hip_shell_damage(weapon.data, dist, &"stomach", rng)
			theirs += await _hip_shell_damage(saiga, dist, &"stomach", rng)
		gut.p("%.0f m: SPAS-12 %.0f, Saiga %.0f per shell" % [dist, mine / 4.0, theirs / 4.0])
		assert_gt(mine / 4.0, 100.0 * 2.5, "at %.0f m a shell is several men's worth (%.0f)" % [dist, mine / 4.0])
		assert_gt(mine, theirs * 1.25, "at %.0f m: %.0f vs %.0f" % [dist, mine / 4.0, theirs / 4.0])
