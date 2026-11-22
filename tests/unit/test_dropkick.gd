extends GutTest
## Dropkick math and asset checks (docs/design.md §5.7b).

var cfg: DropkickConfig
var move: MovementConfig


func before_each() -> void:
	cfg = load("res://data/player/dropkick_default.tres") as DropkickConfig
	move = load("res://data/player/movement_default.tres") as MovementConfig


func test_dropkick_knockback_and_damage_scale_with_body() -> void:
	var base: float = Player.dropkick_strength(cfg, 100.0, 1.0, cfg.knock_ref_speed)
	assert_almost_eq(base, cfg.knock_speed, 0.001, "reference: 100 kg, strength 1")
	assert_gt(Player.dropkick_strength(cfg, 160.0, 1.0, cfg.knock_ref_speed), base, "heavier body kicks harder")
	assert_gt(Player.dropkick_strength(cfg, 100.0, 1.5, cfg.knock_ref_speed), base, "stronger body kicks harder")
	# Launches further and higher than a slide, while bounded ("far, not crazy far").
	var dk_v: Vector3 = Player.dropkick_launch_velocity(cfg, base * 1.4, Vector3.FORWARD)
	var sl_v: Vector3 = Player.slide_launch_velocity(move, move.slide_knock_speed * 1.4, Vector3.FORWARD)
	assert_gt(Vector2(dk_v.x, dk_v.z).length(), Vector2(sl_v.x, sl_v.z).length(), "launches further than a slide")
	assert_gt(dk_v.y, sl_v.y, "launches higher than a slide")
	var capped: Vector3 = Player.dropkick_launch_velocity(cfg, 99.0, Vector3.FORWARD)
	assert_lt(Vector2(capped.x, capped.z).length(), cfg.launch_max_speed, "horizontal launch stays bounded")
	# Blunt impact damage scales with push and breaks bodies past lethal_push.
	var dmg: float = Player.dropkick_damage(cfg, base)
	assert_between(dmg, 20.0, 75.0, "healthy enemy survives to fly through the air (%.1f)" % dmg)
	assert_gt(Player.dropkick_damage(cfg, cfg.lethal_push), 1000.0, "past lethal_push breaks the body")
	assert_lt(Player.dropkick_damage(cfg, cfg.lethal_push * 1.5, true), 100.0, "RX-9 slow-mo never kills outright: he flies to be shot")


func test_dropkick_config_and_assets_load() -> void:
	assert_not_null(cfg, "dropkick_default.tres loads")
	assert_not_null(cfg.legs_scene, "fp_legs.gltf scene is assigned")
	for bank: StringName in [&"dropkick_launch", &"dropkick_hit", &"dropkick_land", &"dropkick_draw"]:
		assert_gt(Sfx.bank(bank).size(), 0, "SFX bank %s loaded" % bank)
