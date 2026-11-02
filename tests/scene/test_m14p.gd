extends GutTest
## The M14/P battle rifle in the real test room (owner, 2026-11-02: "a black
## polymer M14 style battle rifle, with a suppressor and stubby foregrip"):
## on the wheel, semi-auto 7.62×51, 20+1, the bolt and op rod cycle on every
## shot, the buttstock hides while aiming, a tactical reload keeps the
## chambered round, and a chest hit goes through a dummy.

var room: TestRoom
var player: Player
var weapon: PlayerWeapon


func before_each() -> void:
	Fx.enabled = false
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	player = room.player
	weapon = player.weapon()
	await wait_physics_frames(10)
	weapon.select_now(weapon.index_of("M14/P"))
	await wait_physics_frames(3)


func after_each() -> void:
	for action: StringName in [&"aim", &"fire", &"reload"]:
		Input.action_release(action)
	Fx.enabled = true


func _press(action: StringName) -> void:
	Input.action_press(action)
	await wait_physics_frames(2)
	Input.action_release(action)


func test_it_is_a_suppressed_semi_auto_7_62() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.display_name, "M14/P")
	assert_false(d.automatic, "semi-auto")
	assert_eq(weapon.mechanism.loaded(), 21, "20 + 1")
	assert_between(d.muzzle_energy(), 3000.0, 3800.0, "7.62×51 ball, %.0f J" % d.muzzle_energy())
	assert_lt(d.flash_scale, 0.5, "suppressed: small flash")
	for part: StringName in [&"slide", &"magazine", &"stock"]:
		assert_true(weapon.rig().has_part(part), "has a moving %s" % part)


func test_holding_rt_fires_once_and_the_action_cycles() -> void:
	var slide: Node3D = weapon.rig().find_child("slide", true, false) as Node3D
	var rest: float = slide.position.x
	var shots: Array[int] = [0]
	weapon.fired.connect(func() -> void: shots[0] += 1)
	Input.action_press(&"fire")
	var back: float = 0.0
	for i: int in 30:
		await get_tree().process_frame
		back = maxf(back, rest - slide.position.x)
	Input.action_release(&"fire")
	assert_eq(shots[0], 1, "one shot per pull")
	assert_gt(back, 0.02, "bolt and op rod run back (%.3f m)" % back)


func test_stock_hides_when_aimed() -> void:
	var stock: Node3D = weapon.rig().find_child("stock", true, false) as Node3D
	assert_true(stock.visible)
	Input.action_press(&"aim")
	await wait_seconds(weapon.data.ads_time + 0.2)
	assert_false(stock.visible, "buttstock out of the way of the sights")
	Input.action_release(&"aim")


func test_tactical_reload_keeps_the_chambered_round() -> void:
	await _press(&"fire")
	await wait_physics_frames(10)
	assert_eq(weapon.mechanism.loaded(), 20)
	await _press(&"reload")
	await wait_seconds(weapon.data.reload_tactical_time + 0.2)
	assert_eq(weapon.mechanism.loaded(), 21)


func test_a_chest_hit_goes_through_a_dummy() -> void:
	var d: TargetDummy = room.shooting_range.dummies[0]
	var hits: Array[BallisticHit] = []
	var cb: Callable = func(h: BallisticHit) -> void: hits.append(h)
	EventBus.ballistic_hit.connect(cb)
	var from: Vector3 = Vector3(0, 1.6, 10)
	Ballistics.fire(weapon.data, from, (d.parts[&"chest"].global_position - from).normalized(), player)
	await wait_physics_frames(6)
	EventBus.ballistic_hit.disconnect(cb)
	var through: bool = false
	for h: BallisticHit in hits:
		if h.surface.is_flesh and h.result == BallisticHit.Result.PENETRATED:
			through = true
	assert_true(through, ".308 passes through a torso")
	assert_lt(d.health, d.config.health)
