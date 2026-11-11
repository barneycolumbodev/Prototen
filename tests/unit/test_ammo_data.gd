extends GutTest
## Shell types (AmmoData) and the Saiga-12K's loads: each load's round data,
## realistic energies, the slug's drop (the optic's holdover chevrons), and
## the pellet pattern.

var saiga: WeaponData


func before_each() -> void:
	saiga = load("res://data/weapons/saiga12k.tres") as WeaponData


func test_saiga_takes_buck_slugs_and_dragons_breath() -> void:
	assert_eq(saiga.ammo_types.size(), 3)
	var names: PackedStringArray = PackedStringArray()
	for a: AmmoData in saiga.ammo_types:
		names.append(a.display_name)
	assert_eq(names, PackedStringArray(["00 Buck", "Slug", "Dragon's Breath"]))
	assert_true(saiga.shotshell)
	assert_eq(saiga.magazine_size, 10)
	assert_false(saiga.automatic, "semi-auto")


func test_only_slugs_mount_the_optic() -> void:
	assert_false(saiga.ammo_types[0].use_optic)
	assert_true(saiga.ammo_types[1].use_optic)
	assert_false(saiga.ammo_types[2].use_optic)


func test_round_data_takes_the_load_and_keeps_the_guns_handling() -> void:
	var buck: AmmoData = saiga.ammo_types[0]
	var slug: AmmoData = saiga.ammo_types[1]
	var r: WeaponData = slug.apply_to(saiga)
	assert_eq(r.pellets, 1)
	assert_eq(r.bullet_mass_g, slug.pellet_mass_g)
	assert_eq(r.muzzle_velocity, slug.muzzle_velocity)
	assert_eq(r.ads_time, saiga.ads_time, "handling stays the gun's")
	assert_eq(r.magazine_size, saiga.magazine_size)
	assert_almost_eq(r.kick_pitch_deg, saiga.kick_pitch_deg * slug.recoil_scale, 0.0001)
	var b: WeaponData = buck.apply_to(saiga)
	assert_eq(b.pellets, 9)
	assert_gt(b.pattern_deg, 2.0)
	assert_eq(b.sound_prefix, "saiga_", "buck uses the gun's shot sound")
	var db: WeaponData = saiga.ammo_types[2].apply_to(saiga)
	assert_true(db.embers)
	assert_gt(db.burn_dps * db.burn_time, 40.0, "the fire does real damage")
	assert_eq(db.sound_prefix, "saiga_db_")
	assert_false(saiga.embers, "the gun's own data is untouched")


func test_shell_energies_are_twelve_gauge() -> void:
	# Real 12-gauge: ~2.5-3.5 kJ for full-power buck and slugs; Dragon's Breath far less.
	var buck: float = saiga.ammo_types[0].shell_energy()
	var slug: float = saiga.ammo_types[1].shell_energy()
	var db: float = saiga.ammo_types[2].shell_energy()
	assert_between(buck, 2000.0, 3500.0, "buck %.0f J" % buck)
	assert_between(slug, 2400.0, 3800.0, "slug %.0f J" % slug)
	assert_lt(db, 1000.0, "dragon's breath %.0f J" % db)


func test_slug_drops_like_a_slug() -> void:
	var slug: AmmoData = saiga.ammo_types[1]
	var d100: float = slug.drop_at(100.0)
	var d200: float = slug.drop_at(200.0)
	var d300: float = slug.drop_at(300.0)
	assert_between(d100, 0.15, 0.5, "100 m: %.2f m" % d100)
	assert_gt(d200, d100 * 3.0, "drop grows faster than range (drag): %.2f m" % d200)
	assert_gt(d300, d200 * 1.8, "300 m: %.2f m" % d300)


func test_drop_matches_the_ballistics_simulation() -> void:
	# Fire a slug level in an empty world and compare where it is at 100 m with drop_at().
	var slug: AmmoData = saiga.ammo_types[1]
	var r: WeaponData = slug.apply_to(saiga)
	var y: float = 0.0
	var x: float = 0.0
	var vx: float = r.muzzle_velocity
	var vy: float = 0.0
	var dt: float = 1.0 / 60.0
	while x < 100.0:
		var speed: float = sqrt(vx * vx + vy * vy)
		var k: float = (speed / (1.0 + r.drag_per_m * speed * dt)) / speed
		vx *= k
		vy = vy * k - 9.8 * dt
		x += vx * dt
		y += vy * dt
	# 60 Hz overshoots 100 m by up to one step (~7 m); compare at the same distance.
	assert_almost_eq(-y, slug.drop_at(x), 0.03, "60 Hz sim vs 240 Hz table at %.1f m" % x)


func test_pellet_pattern_fills_the_cone_without_clumping() -> void:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 7
	var fwd: Vector3 = Vector3(0, 0, -1)
	var cone: float = 3.4
	var dirs: Array[Vector3] = []
	for i: int in 9:
		dirs.append(Ballistics.pattern_dir(fwd, cone, i, 9, 0.5, rng))
	var widest: float = 0.0
	for d: Vector3 in dirs:
		var ang: float = rad_to_deg(d.angle_to(fwd))
		assert_lte(ang, cone * 0.5 + 0.001, "inside the cone")
		widest = maxf(widest, ang)
	assert_gt(widest, cone * 0.35, "spreads out (widest %.2f°)" % widest)
	# No two pellets on top of each other.
	for i: int in dirs.size():
		for j: int in range(i + 1, dirs.size()):
			assert_gt(rad_to_deg(dirs[i].angle_to(dirs[j])), 0.05)


func test_dismemberment_thresholds() -> void:
	var cfg: GoreConfig = load("res://data/gore/gore_default.tres")
	assert_eq(Dismemberment.outcome(cfg, &"forearm_L", cfg.forearm_j - 1.0, 0.0), Dismemberment.Outcome.NONE)
	assert_eq(Dismemberment.outcome(cfg, &"forearm_L", cfg.forearm_j, 0.0), Dismemberment.Outcome.SEVER)
	var pulp: float = cfg.forearm_j * cfg.pulp_factor
	assert_eq(Dismemberment.outcome(cfg, &"forearm_L", pulp, 0.0, pulp), Dismemberment.Outcome.PULP, "that much left in it destroys it")
	assert_eq(Dismemberment.outcome(cfg, &"forearm_L", pulp, 0.0, cfg.forearm_j), Dismemberment.Outcome.SEVER,
			"a round that carries its energy on through cuts it off whole")
	assert_eq(Dismemberment.outcome(cfg, &"head", cfg.head_j * 10.0, 0.0), Dismemberment.Outcome.SEVER, "a neck hit takes the head off whole")
	assert_eq(Dismemberment.outcome(cfg, &"head", cfg.head_destroy_j, 0.0, 0.0, true), Dismemberment.Outcome.PULP, "a hit on the head breaks it")
	assert_eq(Dismemberment.outcome(cfg, &"head", cfg.head_j, 0.0, 0.0, true), Dismemberment.Outcome.SEVER, "a lighter one knocks it off")
	assert_eq(Dismemberment.outcome(cfg, &"hand_L", 10.0, cfg.hand_j * cfg.accumulate_factor), Dismemberment.Outcome.SEVER, "hits add up")
	assert_false(Dismemberment.adds_up(cfg, &"thigh_L", cfg.thigh_j * cfg.min_share * 0.9), "scratches don't add up")
	assert_gt(Dismemberment.violence(cfg, 100.0, 1000.0, DamageInfo.Type.BLADE), Dismemberment.violence(cfg, 100.0, 1000.0, DamageInfo.Type.BALLISTIC), "blades cut")
	assert_almost_eq(cfg.falloff(0.0), 1.0, 0.001)
	assert_almost_eq(cfg.falloff(cfg.reach_m), 0.0, 0.001)
	# Toughness scales every threshold (Pause → Tuning → Gore).
	var tough: GoreConfig = cfg.duplicate() as GoreConfig
	tough.toughness = 2.0
	assert_eq(Dismemberment.outcome(tough, &"forearm_L", cfg.forearm_j, 0.0), Dismemberment.Outcome.NONE)
	assert_eq(Dismemberment.outcome(tough, &"forearm_L", cfg.forearm_j * 2.0, 0.0), Dismemberment.Outcome.SEVER)
