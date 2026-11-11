extends GutTest
## The triad wardrobe (owner, 2026-11-11: "clothes they can wear that are
## randomly selected from a bank", tattoos): looks are picked from the
## role's outfits, every garment exists and is cut like the body, a man is
## one mesh before and after a cut, and a severed limb takes its sleeve.

var room: TestRoom
var gunman: EnemyConfig = preload("res://data/enemies/gunman.tres")
var enforcer: EnemyConfig = preload("res://data/enemies/enforcer.tres")
var red_pole: EnemyConfig = preload("res://data/enemies/red_pole.tres")


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	room.player.invulnerable = true
	await wait_physics_frames(5)


func _look(cfg: EnemyConfig, seed: int) -> TriadLook:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = seed
	return TriadLook.pick(cfg.outfits, rng)


func _spawn(cfg: EnemyConfig, seed: int, at: Vector3 = Vector3(0, 0, 4)) -> Enemy:
	var e: Enemy = Enemy.new()
	e.config = cfg
	e.passive = true
	e.look_seed = seed
	room.add_child(e)
	e.position = at
	return e


func test_every_role_has_outfits() -> void:
	for cfg: EnemyConfig in [gunman, enforcer, red_pole]:
		assert_false(cfg.outfits.is_empty(), cfg.display_name)


func test_every_garment_is_in_the_wardrobe_and_cut_like_the_body() -> void:
	var seen: Dictionary[StringName, bool] = {}
	for cfg: EnemyConfig in [gunman, enforcer, red_pole]:
		for o: Outfit in cfg.outfits:
			for list: Array[Garment] in [o.tops, o.inners, o.bottoms, o.shoes, o.hair, o.hats, o.accessories]:
				for g: Garment in list:
					seen[g.mesh] = true
	assert_gt(seen.size(), 20, "a real bank: %d garments" % seen.size())
	for id: StringName in seen:
		assert_not_null(EnemyBody.wardrobe_mesh(StringName("w_" + String(id))), "w_%s" % id)
	# A long-sleeved top has a piece for each arm segment it covers.
	for part: String in ["body", "upper_arm_L", "forearm_L", "upper_arm_R", "forearm_R"]:
		assert_not_null(EnemyBody.wardrobe_mesh(StringName("w_hoodie__" + part)), "w_hoodie__" + part)
	assert_not_null(EnemyBody.wardrobe_mesh(&"w_hair_fade__head"), "hair goes with the head")
	assert_not_null(EnemyBody.wardrobe_mesh(&"w_sneakers__shin_L"), "a shoe goes with the shin")


func test_a_look_is_complete_and_repeatable() -> void:
	for seed: int in 40:
		var look: TriadLook = _look(gunman, seed)
		var slots: Array[int] = []
		for g: Garment in look.garments:
			slots.append(int(g.slot))
		assert_true(slots.has(Garment.Slot.TOP) or slots.has(Garment.Slot.INNER), "a top (%s)" % look.key())
		assert_true(slots.has(Garment.Slot.BOTTOM), "trousers (%s)" % look.key())
		assert_true(slots.has(Garment.Slot.SHOES), "shoes (%s)" % look.key())
		assert_eq(_look(gunman, seed).key(), look.key(), "same seed, same man")
		if slots.has(Garment.Slot.HAT):
			for g: Garment in look.garments:
				if g.slot == Garment.Slot.HAIR:
					assert_true(g.fits_under_hat, "%s under a hat" % g.mesh)


func test_looks_vary() -> void:
	var keys: Dictionary[String, bool] = {}
	var tattooed: int = 0
	var printed: int = 0
	for seed: int in 60:
		var look: TriadLook = _look(gunman, seed)
		keys[look.key()] = true
		if look.tattoos[0] | look.tattoos[1] | look.tattoos[2]:
			tattooed += 1
		for p: int in look.print_id:
			if p >= 0:
				printed += 1
				break
	assert_gt(keys.size(), 30, "60 gunmen, %d different sets of clothes" % keys.size())
	assert_gt(tattooed, 30, "most have tattoos (%d of 60)" % tattooed)
	assert_gt(printed, 5, "some wear prints (%d of 60)" % printed)


func test_a_man_is_one_mesh_with_his_clothes() -> void:
	var e: Enemy = _spawn(gunman, 7)
	await wait_physics_frames(2)
	var shown: Array[String] = []
	for n: Node in e.body.skeleton.get_children():
		var mi: MeshInstance3D = n as MeshInstance3D
		if mi and mi.visible:
			shown.append(mi.name)
	assert_eq(shown, ["triad"], "one draw call")
	var expected: int = EnemyBody.prepared(&"triad", null, 0, 0).surface_get_array_len(0)
	for g: Garment in e.body.look.garments:
		expected += (EnemyBody.wardrobe_mesh(StringName("w_" + String(g.mesh))) as ArrayMesh).surface_get_array_len(0)
	var merged: ArrayMesh = (e.body.skeleton.get_node(^"triad") as MeshInstance3D).mesh as ArrayMesh
	assert_eq(merged.get_surface_count(), 1)
	assert_eq(merged.surface_get_array_len(0), expected, "the body and %s" % e.body.look.key())


func test_a_severed_arm_takes_its_sleeve() -> void:
	var look: TriadLook = TriadLook.new()
	look.garments.append(load("res://data/enemies/wardrobe/hoodie.tres") as Garment)
	look.garments.append(load("res://data/enemies/wardrobe/jeans.tres") as Garment)
	var e: Enemy = Enemy.new()
	e.config = gunman
	e.passive = true
	room.add_child(e)
	e.body.look = look
	var group: Array[StringName] = [&"forearm_R", &"hand_R"]
	var with_sleeve: ArrayMesh = e.body.gib_mesh(group)
	var bare: int = 0
	for seg: StringName in group:
		bare += (e.body._meshes[EnemyBody.SEGMENTS[seg][0]].mesh as ArrayMesh).surface_get_array_len(0)
	var sleeve: int = (EnemyBody.wardrobe_mesh(&"w_hoodie__forearm_R") as ArrayMesh).surface_get_array_len(0)
	assert_eq(with_sleeve.surface_get_array_len(0), bare + sleeve, "the forearm flies off in its sleeve")
