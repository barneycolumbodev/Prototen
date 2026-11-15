extends GutTest
## Survival waves (docs/design.md §8.6): the threat budget, debuts, caps,
## lieutenant waves.

var cfg: SurvivalConfig = preload("res://data/run/survival.tres")


func _rng(s: int) -> RandomNumberGenerator:
	var r: RandomNumberGenerator = RandomNumberGenerator.new()
	r.seed = s
	return r


func test_roster_roles_exist() -> void:
	for e: WaveEnemy in cfg.roster:
		assert_true(ResourceLoader.exists("res://data/enemies/%s.tres" % e.role), e.role)
	assert_not_null(load("res://data/enemies/blue_lantern.tres") as EnemyConfig)


func test_budget_climbs_with_a_dip_after_bosses() -> void:
	assert_lt(SurvivalWaves.budget(1, cfg), SurvivalWaves.budget(4, cfg))
	assert_lt(SurvivalWaves.budget(6, cfg), SurvivalWaves.budget(5, cfg) * 1.0)
	assert_gt(SurvivalWaves.budget(9, cfg), SurvivalWaves.budget(5, cfg))


func test_wave_one_is_a_handful_of_cheap_men() -> void:
	for s: int in range(1, 20):
		var w: Array[String] = SurvivalWaves.compose(1, cfg, _rng(s))
		assert_between(w.size(), 3, 5, "seed %d: %s" % [s, w])
		assert_true("blue_lantern" in w and "gunman" in w, "both debut")
		assert_false("enforcer" in w or "red_pole" in w)


func test_types_debut_on_their_wave() -> void:
	for e: WaveEnemy in cfg.roster:
		var w: Array[String] = SurvivalWaves.compose(e.first_wave, cfg, _rng(3))
		assert_true(e.role in w, "%s on wave %d" % [e.role, e.first_wave])
		if e.first_wave > 1:
			assert_false(e.role in SurvivalWaves.compose(e.first_wave - 1, cfg, _rng(3)))


func test_sizes_grow() -> void:
	var sizes: Array[int] = []
	for n: int in [1, 4, 8, 12, 16, 20]:
		sizes.append(SurvivalWaves.compose(n, cfg, _rng(11)).size())
	gut.p("wave sizes 1/4/8/12/16/20: %s" % [sizes])
	for i: int in sizes.size() - 1:
		assert_lt(sizes[i], sizes[i + 1])


func test_red_pole_cap() -> void:
	for s: int in range(1, 30):
		var w: Array[String] = SurvivalWaves.compose(8, cfg, _rng(s))
		assert_lte(w.count("red_pole"), 1, "one Red Pole before wave 10")


func test_wave_5_is_the_incense_master_with_escorts() -> void:
	assert_true(cfg.is_boss_wave(5))
	assert_false(cfg.is_boss_wave(4))
	assert_eq(cfg.boss_for(5), "incense_master", "the triad map's first boss (owner, 2026-11-15)")
	assert_eq(cfg.boss_for(4), "")
	var w: Array[String] = SurvivalWaves.compose(5, cfg, _rng(1))
	assert_false("incense_master" in w, "the director brings him in himself, with his entrance")
	assert_lt(w.size(), SurvivalWaves.compose(4, cfg, _rng(1)).size(), "a lighter escort than a full wave")
	assert_gt(w.size(), 0, "but not alone")


func test_lieutenant_wave_after_the_last_boss() -> void:
	assert_eq(cfg.boss_for(10), "", "no second boss yet")
	var w: Array[String] = SurvivalWaves.compose(10, cfg, _rng(1))
	assert_eq(w[0], "red_pole")
	assert_eq(w[1], "red_pole")
