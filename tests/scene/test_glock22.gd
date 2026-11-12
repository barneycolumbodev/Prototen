extends GutTest
## The switched Glock 22 (owner, 2026-11-12: "a Glock with a dropped in switch
## with a realistic but high fire rate chambered in .40 Smith & Wesson"): on the
## wheel, full auto at ~1,200 rpm, .40 S&W ballistics, a 22-round magazine,
## and holding the trigger empties it in about a second.

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
	weapon.select_now(weapon.index_of("Glock 22 (switch)"))
	await wait_physics_frames(3)


func after_each() -> void:
	Input.action_release(&"fire")
	Fx.enabled = true


func test_it_is_a_full_auto_40_sw() -> void:
	var d: WeaponData = weapon.data
	assert_eq(d.display_name, "Glock 22 (switch)")
	assert_eq(d.caliber, ".40 S&W")
	assert_true(d.automatic, "the switch makes it full auto")
	var rpm: float = 60.0 / d.fire_interval
	assert_between(rpm, 1100.0, 1300.0, "switched Glocks run ~1,100-1,300 rpm")
	assert_eq(weapon.mechanism.loaded(), 23, "22 + 1")
	# 180 gr at ~300 m/s: heavier and slower than the 5.7, more energy.
	assert_between(d.bullet_mass_g, 11.0, 12.5)
	assert_between(d.muzzle_velocity, 280.0, 320.0)
	assert_eq(d.sound_prefix, "glock_")


func test_holding_the_trigger_dumps_the_magazine() -> void:
	var before: int = weapon.mechanism.loaded()
	Input.action_press(&"fire")
	await wait_seconds(0.5)
	Input.action_release(&"fire")
	var fired: int = before - weapon.mechanism.loaded()
	assert_between(fired, 7, 12, "about ten rounds in half a second (fired %d)" % fired)
