extends GutTest
## The attack dog (docs/design.md §8.8b): a German shepherd that gallops in
## by scent, leaps the last metres and bites. Tripo model and rig, our
## animations; hit zones on the bones; counted by the spawners like a man.

var room: TestRoom
var player: Player
var pistol: WeaponData = preload("res://data/weapons/pistol_57.tres")
var cfg: DogConfig = preload("res://data/enemies/attack_dog.tres")


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	await wait_physics_frames(10)
	room.shooting_range.clear_targets()
	room.wave_mode._build_navigation()
	player.invulnerable = false
	player.input_enabled = false
	player.body_config = player.body_config.duplicate() as PlayerBodyConfig
	player.body_config.max_health = 5000.0
	player.health = 5000.0
	await wait_physics_frames(2)


func _spawn(at: Vector3) -> AttackDog:
	var d: AttackDog = AttackDog.new()
	d.player = player
	room.add_child(d)
	d.global_position = at
	var to: Vector3 = player.global_position - at
	d.face(atan2(to.x, to.z))
	return d


func _place_player(at: Vector3, look: Vector3) -> void:
	player.global_position = at
	player.velocity = Vector3.ZERO
	var to: Vector3 = look - at
	player.set_view(atan2(-to.x, -to.z), 0.0)


func _wait_for(cond: Callable, seconds: float) -> bool:
	for i: int in int(seconds * 60.0):
		if cond.call():
			return true
		await wait_physics_frames(1)
	return cond.call()


func test_model_rig_animations_and_zones() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 0.5, 0))
	var d: AttackDog = _spawn(Vector3(0, 0, 0))
	d.set_physics_process(false)
	await wait_physics_frames(2)
	assert_not_null(d.anim, "an AnimationPlayer from the GLB")
	for n: StringName in [&"idle_snarl", &"run", &"trot", &"lunge", &"bite", &"flinch", &"death"]:
		assert_true(d.anim.has_animation(n), "animation %s" % n)
	assert_eq(d.anim.get_animation(&"run").loop_mode, Animation.LOOP_LINEAR, "the gallop loops")
	assert_eq(d.hitboxes.size(), AttackDog.ZONES.size(), "every zone built on its bone")
	assert_true(d.is_in_group(&"enemies") and d.is_in_group(&"dogs"))
	# It faces the operative (+Z here): the head is in front of the chest, at dog height.
	var head: Vector3 = d.head_position()
	var chest: Vector3 = d.chest_position()
	gut.p("head %s chest %s" % [head, chest])
	assert_gt(head.z - d.global_position.z, 0.25, "head forward")
	assert_gt(head.z, chest.z, "head ahead of the chest")
	assert_between(head.y, 0.15, 0.5, "head at a dog's height")
	assert_between(chest.y, 0.25, 0.6)


func test_it_gallops_in_and_bites() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 0.5, 0))
	var d: AttackDog = _spawn(Vector3(0, 0, 0))
	var top: Array[float] = [0.0]
	var health: float = player.health
	var bit: bool = await _wait_for(func() -> bool:
		top[0] = maxf(top[0], Vector3(d.velocity.x, 0, d.velocity.z).length())
		return d.bites > 0, 4.0)
	gut.p("top speed %.1f m/s, bites %d, whiffs %d, state %s" % [top[0], d.bites, d.whiffs, d.state_name()])
	assert_true(bit, "it closed 13 m and bit")
	assert_gt(top[0], cfg.run_speed - 1.5, "at a gallop")
	assert_lt(player.health, health, "the bite hurt")


func test_a_head_shot_kills_it() -> void:
	_place_player(Vector3(0, 0, 9), Vector3(0, 0.4, 0))
	var d: AttackDog = _spawn(Vector3(0, 0, 0))
	d.set_physics_process(false)
	await wait_physics_frames(3)
	var died: Array[bool] = [false]
	d.died.connect(func(_x: AttackDog) -> void: died[0] = true)
	var from: Vector3 = player.camera().global_position
	for i: int in 3:
		if not d.alive:
			break
		var head: Vector3 = d.head_position()
		Ballistics.fire(pistol, from, (head - from).normalized(), player)
		await wait_physics_frames(2)
	assert_false(d.alive, "dead (hp %.0f)" % d.health)
	assert_true(died[0], "died signal")
	assert_false(d.is_in_group(&"enemies"), "out of the fight")
	d.set_physics_process(true)
	await wait_seconds(0.5)
	assert_eq(d.anim.current_animation, &"death", "plays its death")


func test_a_blast_kills_it() -> void:
	_place_player(Vector3(0, 0, 12), Vector3(0, 0.5, 0))
	var d: AttackDog = _spawn(Vector3(0, 0, 0))
	d.set_physics_process(false)
	await wait_physics_frames(2)
	var kills: int = Explosion.detonate(room, d.chest_position() + Vector3(0.8, 0.2, 0), 4.0, 200.0, player, pistol, 0.0, false)
	assert_eq(kills, 1)
	assert_false(d.alive)


func test_spawner_counts_dogs_as_fighting() -> void:
	var sp: RollingSpawner = RollingSpawner.new()
	sp.config = (load("res://data/levels/chinatown_spawns.tres") as RollingSpawnConfig).duplicate() as RollingSpawnConfig
	sp.level = room
	sp.player = player
	room.add_child(sp)
	sp._build_squad()
	_place_player(Vector3(0, 0, 13), Vector3(0, 0.5, 0))
	var d: AttackDog = sp._spawn_dog(Vector3(0, 0, -6))
	await wait_physics_frames(2)
	assert_eq(sp.fighting(), 1, "a living dog is fighting")
	assert_eq(sp.alive(), 1)
	d.die()
	assert_eq(sp.fighting(), 0)
	assert_eq(sp.kills, 1, "its death counts")


func test_role_weights_pick_dogs() -> void:
	var c: RollingSpawnConfig = RollingSpawnConfig.new()
	c.gunman_weight = 0.0
	c.enforcer_weight = 0.0
	c.red_pole_weight = 0.0
	c.hatchet_man_weight = 0.0
	c.attack_dog_weight = 1.0
	assert_eq(c.pick_role(0.5), AttackDog.ROLE)
	var china: RollingSpawnConfig = load("res://data/levels/chinatown_spawns.tres") as RollingSpawnConfig
	assert_gt(china.attack_dog_weight, 0.0, "dogs on the Chinatown docks")


func test_a_sidestep_makes_the_leap_miss() -> void:
	_place_player(Vector3(0, 0, 13), Vector3(0, 0.5, 0))
	var d: AttackDog = _spawn(Vector3(0, 0, 6))
	var crouched: bool = await _wait_for(func() -> bool: return d.is_winding_up(), 3.0)
	assert_true(crouched, "it crouched to spring")
	var health: float = player.health
	_place_player(player.global_position + Vector3(4.0, 0, 0), d.global_position)
	await wait_seconds(0.6)
	assert_eq(d.bites, 0, "leapt at air")
	assert_eq(player.health, health)
