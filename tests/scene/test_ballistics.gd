extends GutTest
## Fires real rounds through a row of material panels and checks the physics.

var weapon: WeaponData
var root: Node3D
var hits: Array[BallisticHit] = []


func before_each() -> void:
	weapon = (load("res://data/weapons/pistol_57.tres") as WeaponData).duplicate() as WeaponData
	root = Node3D.new()
	add_child_autofree(root)
	hits.clear()
	EventBus.ballistic_hit.connect(_on_hit)
	Ballistics.clear()


func after_each() -> void:
	EventBus.ballistic_hit.disconnect(_on_hit)


func _on_hit(hit: BallisticHit) -> void:
	hits.append(hit)


## Panel facing the shooter (who looks down -Z), centred at z.
func _panel(surface: StringName, z: float, thickness: float, layer: int = Ballistics.LAYER_WORLD) -> StaticBody3D:
	var body: StaticBody3D = StaticBody3D.new()
	body.collision_layer = layer
	body.set_meta(&"surface", surface)
	var shape: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = Vector3(2, 2, thickness)
	shape.shape = box
	body.add_child(shape)
	root.add_child(body)
	body.global_position = Vector3(0, 1, z)
	return body


func _fire(dir: Vector3 = Vector3.FORWARD) -> void:
	await wait_physics_frames(2)
	Ballistics.fire(weapon, Vector3(0, 1, 0), dir)
	await wait_physics_frames(20)


func test_muzzle_energy_is_realistic() -> void:
	# 2.0 g at 650 m/s = 422.5 J (real SS190: ~400-520 J depending on barrel).
	assert_almost_eq(weapon.muzzle_energy(), 422.5, 0.1)


func test_goes_through_drywall_and_stops_in_concrete() -> void:
	_panel(&"drywall", -3.0, 0.0127)
	_panel(&"concrete", -8.0, 0.2)
	await _fire()
	assert_eq(hits.size(), 2, "two contacts")
	assert_eq(hits[0].surface.id, &"drywall")
	assert_eq(hits[0].result, BallisticHit.Result.PENETRATED)
	assert_almost_eq(hits[0].thickness, 0.0127, 0.001, "measured the sheet")
	assert_lt(hits[0].energy_out, hits[0].energy_in, "lost energy")
	assert_gt(hits[0].energy_out, hits[0].energy_in * 0.9, "drywall barely slows it")
	assert_eq(hits[1].surface.id, &"concrete")
	assert_eq(hits[1].result, BallisticHit.Result.STOPPED)
	assert_eq(Ballistics.live_count(), 0)


func test_armor_plate_stops_it_and_sheet_metal_does_not() -> void:
	_panel(&"sheet_metal", -3.0, 0.0015)
	_panel(&"armor_plate", -6.0, 0.006)
	await _fire()
	assert_eq(hits.size(), 2)
	assert_eq(hits[0].result, BallisticHit.Result.PENETRATED)
	assert_eq(hits[1].result, BallisticHit.Result.STOPPED)
	assert_almost_eq(hits[1].deposited(), hits[1].energy_in, 0.01)


func test_overpenetrates_a_body_into_the_next() -> void:
	_panel(&"flesh", -4.0, 0.25, Ballistics.LAYER_HITBOX)
	_panel(&"flesh", -6.0, 0.25, Ballistics.LAYER_HITBOX)
	await _fire()
	assert_eq(hits.size(), 2, "hit both")
	assert_eq(hits[0].result, BallisticHit.Result.PENETRATED)
	assert_true(hits[1].damage.has_flag(DamageInfo.Flags.PENETRATED), "second victim knows it went through someone")
	assert_gt(hits[0].damage.amount, hits[1].damage.amount * 0.5)


func test_penetration_scale_lets_it_through_more() -> void:
	weapon.penetration_scale = 0.2
	_panel(&"wood", -3.0, 0.1)
	await _fire()
	assert_eq(hits[0].result, BallisticHit.Result.STOPPED, "weak round stops in 10 cm of wood")


func test_bullet_drops_and_takes_time_to_arrive() -> void:
	_panel(&"concrete", -60.0, 0.3)
	await wait_physics_frames(2)
	Ballistics.fire(weapon, Vector3(0, 1, 0), Vector3.FORWARD)
	assert_eq(hits.size(), 0, "60 m away: not there on the trigger frame")
	await wait_physics_frames(20)
	assert_eq(hits.size(), 1)
	# ~0.093 s flight → ~4 cm of drop.
	assert_between(1.0 - hits[0].point.y, 0.02, 0.07, "gravity drop over 60 m")
	assert_lt(hits[0].speed_in, weapon.muzzle_velocity * 0.97, "air drag")


func test_shallow_hit_on_steel_can_ricochet() -> void:
	weapon.max_ricochets = 2
	var steel: StaticBody3D = _panel(&"armor_plate", -5.0, 0.02)
	steel.rotation_degrees = Vector3(0, 85, 0)  # nearly edge-on
	steel.global_position = Vector3(0.05, 1, -5)
	var ricochets: int = 0
	for i: int in 30:
		hits.clear()
		await _fire(Vector3(0.0, 0.0, -1.0))
		for h: BallisticHit in hits:
			if h.result == BallisticHit.Result.RICOCHET:
				ricochets += 1
	assert_gt(ricochets, 0, "grazing shots glance off hard steel")


func test_cone_sampling_stays_inside_the_cone() -> void:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 7
	var widest: float = 0.0
	for i: int in 2000:
		var d: Vector3 = Ballistics.random_in_cone(Vector3.FORWARD, 2.0, rng)
		widest = maxf(widest, rad_to_deg(d.angle_to(Vector3.FORWARD)))
	assert_lt(widest, 1.0001)
	assert_gt(widest, 0.9)
