extends GutTest
## Enemies speak their callouts (VoiceLines) from their own heads, with the
## subtitle, and gunfire can't cut them off.

var room: TestRoom
var _heard: Array[String] = []


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	room.player.invulnerable = true
	_heard.clear()
	EventBus.callout.connect(_on_callout)
	await wait_physics_frames(10)


func after_each() -> void:
	EventBus.callout.disconnect(_on_callout)


func _on_callout(_speaker: String, text: String, _at: Vector3) -> void:
	_heard.append(text)


func _target(i: int = 0) -> Enemy:
	return room.shooting_range.targets[i]


func test_each_enemy_has_a_voice_at_his_head() -> void:
	var e: Enemy = _target()
	assert_has(VoiceLines.VOICES, e.voice)
	assert_not_null(e.mouth)
	assert_lt(e.mouth.global_position.distance_to(e.body.head_position()), 0.3, "the voice comes from his head")


func test_a_callout_is_spoken_and_subtitled() -> void:
	var e: Enemy = _target()
	var line: String = e.speak(&"contact", 2)
	assert_eq(line, VoiceLines.LINES[&"contact"][2])
	assert_true(e.mouth.playing, "the line plays")
	assert_eq(e.mouth.stream.resource_path, VoiceLines.path(e.voice, &"contact", 2))
	assert_has(_heard, line, "with its subtitle")


func test_gunfire_does_not_cut_a_voice_off() -> void:
	var e: Enemy = _target()
	e.speak(&"pinned", 0)
	for i: int in 40:
		Sfx.play_at(&"impact_concrete", e.global_position + Vector3(0.5, 0.2, 0.0), 0.0)
	await wait_physics_frames(3)
	assert_true(e.mouth.playing, "40 impacts later he's still talking")
	assert_eq(e.mouth.stream.resource_path, VoiceLines.path(e.voice, &"pinned", 0))


func test_the_dead_are_silent_but_their_last_cry_carries() -> void:
	var e: Enemy = _target()
	e.die(null, &"chest")
	assert_eq(e.speak(&"contact"), "", "the dead don't call out")


func test_the_squad_keeps_callouts_apart() -> void:
	var sq: Squad = Squad.new()
	add_child_autofree(sq)
	var a: Enemy = _target(0)
	var b: Enemy = _target(1)
	sq.callout(a, &"contact")
	sq.callout(b, &"reload")
	assert_eq(_heard.size(), 1, "the second waits for the gap")
	sq.callout(b, &"officer_down", true)
	assert_eq(_heard.size(), 2, "unless it's forced")
