extends GutTest
## The rest of the triad roster (docs/design.md §8.8b-g, 2026-11-16): the
## Dao swordsman, the Firebomber, the Marksman, the Shield man, the Gunner
## and the anti-augment specialist. Each is checked for his kit (gear on the
## right bones, the right gun) and for the one thing that makes him him.

var room: TestRoom
var player: Player
var squad: Squad
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var rifle: WeaponData = preload("res://data/enemies/weapons/type56.tres")

const ROLES: Dictionary[String, Array] = {
	"dao_swordsman": ["dao.gltf", ["plate"]],
	"firebomber": ["molotov.gltf", ["satchel", "strap", "bandana"]],
	"marksman": ["type79.gltf", []],
	"shield_man": ["type54.gltf", ["shield", "helmet"]],
	"gunner": ["type80.gltf", ["belts"]],
	"anti_augment": ["qbz95.gltf", ["jammer", "rig", "mask"]],
}


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	await wait_physics_frames(10)
	room.shooting_range.clear_targets()
	room.wave_mode._build_navigation()
	squad = Squad.new()
	room.add_child(squad)
	squad.set_player(player)
	squad.build_cover(Vector3.ZERO, 15.5, room.get_world_3d())
	player.invulnerable = false
	player.input_enabled = false
	player.body_config = player.body_config.duplicate() as PlayerBodyConfig
	player.body_config.max_health = 5000.0
	player.health = 5000.0
	await wait_physics_frames(2)


func _spawn(role: String, at: Vector3, fight: bool = true) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/%s.tres" % role) as EnemyConfig
	squad.add(e)
	room.add_child(e)
	e.global_position = at
	var to: Vector3 = player.global_position - at
	e.face(atan2(to.x, to.z))
	if fight:
		e.awareness = 1.0
		e.last_known = player.global_position
		e._enter(Enemy.State.COMBAT)
	return e


func _place_player(at: Vector3, look: Vector3) -> void:
	player.global_position = at
	player.velocity = Vector3.ZERO
	var to: Vector3 = look - at
	player.set_view(atan2(-to.x, -to.z), 0.0)


func _wait_for(cond: Callable, seconds: float) -> bool:
	var frames: int = int(seconds * 60.0)
	for i: int in frames:
		if cond.call():
			return true
		await wait_physics_frames(1)
	return cond.call()


## Fires `w` from `from` at `to` and waits for it to land.
func _shoot(w: WeaponData, from: Vector3, to: Vector3) -> void:
	Ballistics.fire(w, from, (to - from).normalized(), player)
	await wait_physics_frames(4)


# ------------------------------------------------------------------ kits

func test_every_role_has_its_gun_and_gear() -> void:
	var x: float = -6.0
	for role: String in ROLES:
		var spec: Array = ROLES[role]
		var model: String = spec[0]
		var pieces: Array = spec[1]
		var e: Enemy = _spawn(role, Vector3(x, 0, 6), false)
		x += 2.2
		await wait_physics_frames(2)
		assert_not_null(e.body.gun, "%s holds something" % role)
		if e.body.gun:
			assert_true(e.body.gun.scene_file_path.ends_with(model), "%s: %s" % [role, e.body.gun.scene_file_path])
		for piece: String in pieces:
			var mi: MeshInstance3D = e.gear.piece(StringName(piece)) if e.gear else null
			assert_not_null(mi, "%s wears his %s" % [role, piece])
			if mi:
				assert_true(mi.get_parent() is BoneAttachment3D, "%s's %s rides on a bone" % [role, piece])


func test_survival_roster_brings_them_in_one_wave_at_a_time() -> void:
	var cfg: SurvivalConfig = load("res://data/run/survival.tres") as SurvivalConfig
	var first: Dictionary[String, int] = {}
	for we: WaveEnemy in cfg.roster:
		first[we.role] = we.first_wave
	for role: String in ROLES:
		assert_true(first.has(role), "%s is on the roster" % role)
	assert_eq(first["firebomber"] if first.has("firebomber") else 0, 6)
	assert_eq(first["marksman"] if first.has("marksman") else 0, 7)
	assert_eq(first["dao_swordsman"] if first.has("dao_swordsman") else 0, 8)
	assert_eq(first["shield_man"] if first.has("shield_man") else 0, 9)
	assert_eq(first["gunner"] if first.has("gunner") else 0, 11)
	assert_eq(first["anti_augment"] if first.has("anti_augment") else 0, 13)


# ------------------------------------------------------------------ Dao swordsman

func test_dao_guard_turns_rounds_aside_from_the_front_but_not_from_behind() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("dao_swordsman", Vector3(0, 0, 0))
	var dao: DaoBrain = e.melee as DaoBrain
	assert_not_null(dao, "a DaoBrain")
	var up: bool = await _wait_for(func() -> bool: return dao.guarding, 2.0)
	assert_true(up, "the guard comes up when he's looked at")
	e.set_physics_process(false)  # hold him still for the shots
	var hp: float = e.health
	var chest: Vector3 = e.body.chest_position()
	await _shoot(pistol, chest + (player.global_position - chest).normalized() * 6.0 + Vector3.UP * 0.1, chest)
	assert_gt(dao.deflected, 0, "the round was turned aside")
	assert_eq(e.health, hp, "and did nothing to him")
	# From behind: no guard there.
	var back: Vector3 = chest - e.global_basis.z * 6.0
	await _shoot(pistol, back, chest)
	assert_lt(e.health, hp, "a round in the back hurts (%.0f)" % e.health)


func test_dao_guard_breaks_under_sustained_fire() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("dao_swordsman", Vector3(0, 0, 0))
	var dao: DaoBrain = e.melee as DaoBrain
	await _wait_for(func() -> bool: return dao.guarding, 2.0)
	e.set_physics_process(false)
	var chest: Vector3 = e.body.chest_position()
	var from: Vector3 = chest + (player.global_position - chest).normalized() * 6.0
	for i: int in 8:
		await _shoot(rifle, from, chest)
		if dao.guard_breaks > 0:
			break
	assert_eq(dao.guard_breaks, 1, "rifle rounds wore the guard down (%d deflected)" % dao.deflected)
	assert_false(dao.guarding, "and it's down")


func test_dao_lunges_from_five_metres() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 1, 0))
	var e: Enemy = _spawn("dao_swordsman", Vector3(0, 0, 8.2))
	var lunged: bool = await _wait_for(func() -> bool: return (e.melee as DaoBrain).lunges > 0, 3.0)
	assert_true(lunged, "a lunge from %.1f m" % e.global_position.distance_to(player.global_position))
	var hit: bool = await _wait_for(func() -> bool: return e.melee.hits > 0, 1.5)
	assert_true(hit, "and it landed")


# ------------------------------------------------------------------ Shield man

func test_shield_stops_rounds_and_a_heavy_one_staggers_him() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("shield_man", Vector3(0, 0, 4))
	await wait_physics_frames(30)
	e.set_physics_process(false)
	var hp: float = e.health
	var chest: Vector3 = e.body.chest_position()
	var from: Vector3 = chest + (player.global_position - chest).normalized() * 6.0
	await _shoot(pistol, from, chest)
	assert_gt(e.shield.hits, 0, "the round hit the shield")
	assert_eq(e.health, hp, "and stopped there")
	var slug: WeaponData = preload("res://data/weapons/mg42.tres")
	await _shoot(slug, from, chest)
	assert_true(e.shield.staggers > 0, "an MG42 round knocks the shield aside (%.0f J)" % slug.muzzle_energy())


func test_shield_wears_out_and_he_throws_it_down() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("shield_man", Vector3(0, 0, 4))
	await wait_physics_frames(10)
	e.set_physics_process(false)
	e.shield.absorbed = e.config.shield.integrity - 10.0
	var chest: Vector3 = e.body.chest_position()
	await _shoot(pistol, chest + (player.global_position - chest).normalized() * 6.0, chest)
	assert_false(e.shield.has_shield, "cracked and thrown down")
	assert_null(e.gear.piece(&"shield"), "off his body")


func test_gunmen_fall_in_behind_a_shield() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var s: Enemy = _spawn("shield_man", Vector3(0, 0, 2))
	var g: Enemy = _spawn("gunman", Vector3(2, 0, 0))
	await wait_physics_frames(5)
	var at: Vector3 = squad.stack_point(g, player)
	assert_ne(at, Vector3.INF, "a place behind him")
	assert_lt(at.z, s.global_position.z, "on the far side from the operative (%.2f vs %.2f)" % [at.z, s.global_position.z])


# ------------------------------------------------------------------ Firebomber

func test_firebomber_lobs_a_molotov_that_burns_where_you_stand() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("firebomber", Vector3(0, 0, 0))
	e.thrower.cool = 0.0
	e.thrower._known_for = 10.0
	var thrown: bool = await _wait_for(func() -> bool: return e.thrower.thrown > 0, 4.0)
	assert_true(thrown, "he threw")
	var burning: bool = await _wait_for(func() -> bool: return not FirePatch.active.is_empty(), 4.0)
	assert_true(burning, "it broke and burns")
	if burning:
		var f: FirePatch = FirePatch.active[-1]
		assert_lt(Vector2(f.global_position.x - 0.0, f.global_position.z - 14.0).length(), 4.5, "near the operative")
		player.global_position = f.global_position
		var hp: float = player.health
		await wait_seconds(0.7)
		assert_lt(player.health, hp, "standing in it hurts")


func test_shot_in_the_windup_he_drops_it_at_his_feet() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("firebomber", Vector3(0, 0, 0))
	e.thrower.cool = 0.0
	e.thrower._known_for = 10.0
	var winding: bool = await _wait_for(func() -> bool: return e.thrower.winding, 4.0)
	assert_true(winding)
	e.thrower.on_hurt(100.0)
	assert_eq(e.thrower.drops, 1, "dropped")
	assert_false(FirePatch.active.is_empty(), "fire at his feet")
	if not FirePatch.active.is_empty():
		assert_lt(FirePatch.active[-1].global_position.distance_to(e.global_position), 1.5)


# ------------------------------------------------------------------ Marksman

func test_marksman_lasers_then_fires_and_a_step_aside_dodges_it() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("marksman", Vector3(0, 0, -10))
	e._seen_for = 5.0
	var aiming: bool = await _wait_for(func() -> bool: return e.sight.aiming, 4.0)
	assert_true(aiming, "the laser is on")
	assert_true(e.sight._laser.visible, "and drawn")
	var locked: bool = await _wait_for(func() -> bool: return e.sight.locked, 3.0)
	assert_true(locked, "it locks before the shot")
	var hp: float = player.health
	_place_player(player.global_position + Vector3(3.0, 0, 0), e.global_position)
	await _wait_for(func() -> bool: return e.sight.shots > 0, 1.0)
	await wait_physics_frames(10)
	assert_eq(e.sight.shots, 1, "he fired")
	assert_eq(player.health, hp, "where the operative was, not where he is")


# ------------------------------------------------------------------ Gunner

func test_gunner_keeps_firing_where_you_were() -> void:
	_place_player(Vector3(0, 0, 14), Vector3(0, 1, 0))
	var e: Enemy = _spawn("gunner", Vector3(0, 0, -6))
	e.sees_player = false
	e._unseen_for = 1.0
	e.tactic = Enemy.Tactic.HOLD
	var before: int = e.ammo
	e._try_suppress(0.016)
	assert_lt(e.ammo, before, "a round into where he was")


# ------------------------------------------------------------------ anti-augment specialist

func test_emp_knocks_out_the_operatives_actives() -> void:
	_place_player(Vector3(0, 0, 10), Vector3(0, 1, 0))
	var e: Enemy = _spawn("anti_augment", Vector3(0, 0, 0), false)
	await wait_physics_frames(2)
	var t: ThrownProjectile = ThrownProjectile.launch(room, player.global_position + Vector3(0, 0.3, -1.0), Vector3.DOWN,
			e.config.thrower, e)
	var ref: WeakRef = weakref(t)
	t = null
	var gone: bool = await _wait_for(func() -> bool: return ref.get_ref() == null, 3.0)
	assert_true(gone, "it went off")
	assert_true(ThrownProjectile.last_pulse_hit_player, "the operative was in it")
	var any: ActivePart = null
	for part: ActivePart in player.augments.parts.values():
		any = part
		assert_true(part.jammed > 0.0, "%s jammed" % part.data.id)
		assert_false(part.can_start(), "and can't start")
	assert_not_null(any, "the operative has actives to jam")


func test_shooting_the_pack_kills_the_jammer() -> void:
	_place_player(Vector3(0, 0, 10), Vector3(0, 1, 0))
	var e: Enemy = _spawn("anti_augment", Vector3(0, 0, 0), false)
	await wait_physics_frames(2)
	e.set_physics_process(false)
	var pack: Vector3 = e.jammer.box.global_position
	var behind: Vector3 = pack - e.global_basis.z * 5.0
	for i: int in 6:
		await _shoot(rifle, behind, pack)
		if not e.jammer.alive:
			break
	assert_false(e.jammer.alive, "the pack is dead")
	assert_false(e.jammer.is_jamming())
