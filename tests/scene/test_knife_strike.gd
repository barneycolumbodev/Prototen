extends GutTest
## The R3 strike plays the KB-1 knife slash (owner 2026-11-14: in game it
## still played the old gun jolt) and the blade keeps the blood it draws.


func _player() -> Player:
	var player: Player = (load("res://src/player/player.tscn") as PackedScene).instantiate() as Player
	add_child_autofree(player)
	return player


func test_strike_plays_the_knife() -> void:
	var p: Player = _player()
	await wait_frames(3)
	gut.p("knife=%s" % p.melee.knife)
	assert_not_null(p.melee.knife, "the knife viewmodel is built")
	if p.melee.knife == null:
		return
	p.melee.script_strike()
	await wait_physics_frames(4)
	await wait_frames(2)
	gut.p("playing=%s vis=%s t=%s parent=%s" % [p.melee.knife.playing(), p.melee.knife.rig.visible, p.melee.knife.t, p.melee.knife.rig.get_parent()])
	assert_true(p.melee.knife.playing(), "slash playing")
	assert_true(p.melee.knife.rig.is_visible_in_tree(), "knife on screen")


## Owner 2026-11-14 (second report): still no knife on the phone. Its pieces
## draw as plain meshes like the guns, not one merged skinned mesh, and
## nothing on it is occlusion-culled.
func test_knife_is_drawn_plain() -> void:
	var p: Player = _player()
	await wait_frames(3)
	var rig: ArmRig = p.melee.knife.rig
	assert_null(rig.model.find_child("MergedMesh", true, false), "not merged into a skinned mesh")
	var shown: int = 0
	for n: Node in rig.model.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		assert_null(mi.skin, "no skinning")
		assert_true(mi.ignore_occlusion_culling, "never occlusion-culled")
		if mi.mesh and mi.mesh.get_surface_count() > 0:
			shown += 1
	assert_gt(shown, 5, "the hand and knife pieces have their meshes")


func test_one_cut_kills_a_triad() -> void:
	var p: Player = _player()
	await wait_frames(2)
	assert_gte(p.melee.damage(), 100.0, "the knife kills an unaugmented man (100 hp) in one cut")


func test_blood_builds_up_on_the_blade() -> void:
	var p: Player = _player()
	await wait_frames(3)
	var k: KnifeViewmodel = p.melee.knife
	assert_gt(k.blood_materials().size(), 0, "the blade has a blood pass")
	assert_eq(k.blood_coat, 0.0)
	k.cut(true)
	var one: float = k.blood_coat
	k.cut(false)
	k.cut(true)
	assert_gt(one, 0.0)
	assert_gt(k.blood_coat, one, "more cuts, more blood")
	var before: float = k.blood_coat
	k.play(1.0)
	assert_eq(k.blood_coat, before, "a new slash keeps the blood")
	var coat: float = k.blood_materials()[0].get_shader_parameter(&"coat")
	assert_almost_eq(coat, k.blood_coat, 0.001)
