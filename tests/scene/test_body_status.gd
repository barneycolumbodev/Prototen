extends GutTest
## The operative model, part hardware on sockets, and the body-status screen.


func test_operative_model_has_the_shared_skeleton() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	add_child_autofree(a)
	await wait_frames(1)
	assert_not_null(a.skeleton)
	for bone: String in ["hips", "chest", "head", "forearm.L", "hand.R", "shin.L"]:
		assert_gt(a.skeleton.find_bone(bone), -1, "bone %s (same rig as the triad)" % bone)


func test_parts_mount_their_hardware() -> void:
	var a: BodyAppearance = BodyAppearance.new()
	var lo: BodyLoadout = BodyLoadout.new()
	lo.parts = [load("res://data/body/parts/rx9_reflex_overclock.tres"), load("res://data/body/parts/hs5_heat_sinks.tres")]
	a.loadout = lo
	add_child_autofree(a)
	await wait_frames(1)
	var expected: int = 0
	for p: PartData in lo.parts:
		expected += p.visuals.size()
	assert_eq(a.mounted.size(), expected, "every visual mounted")
	lo.parts = [load("res://data/body/parts/cs1_carapace.tres")]
	a.rebuild()
	await wait_frames(1)
	assert_eq(a.mounted.size(), 0, "rebuilt with the new loadout")


func test_status_text_lists_parts_and_totals() -> void:
	var frame: PlayerBodyConfig = load("res://data/player/body_default.tres")
	var lo: BodyLoadout = load("res://data/body/loadout_default.tres")
	var b: BodyModel = BodyModel.new(frame, lo)
	var t: String = BodyStatus.describe(b)
	assert_string_contains(t, "RX-9 Reflex Overclock")
	assert_string_contains(t, "ACTIVE (LB)")
	assert_string_contains(t, "%.1f kg" % b.mass_kg)
