extends GutTest
## Pause and tuning menus driven with controller buttons, the way the phone
## does it (playtest 2026-11-01: "Gun tuning" could be highlighted but A did nothing).

var room: TestRoom


func before_each() -> void:
	room = (load("res://src/levels/test_room.tscn") as PackedScene).instantiate() as TestRoom
	add_child_autofree(room)
	await wait_physics_frames(5)


func after_each() -> void:
	if TuningMenu.is_open():
		TuningMenu.close()
	if PauseMenu.is_open():
		PauseMenu.close()
	get_tree().paused = false


## Process frames even while the tree is paused (GUT's own waits pause with it).
func _frames(n: int) -> void:
	for i: int in n:
		await get_tree().process_frame


func _pad(button: JoyButton) -> void:
	for pressed: bool in [true, false]:
		var ev: InputEventJoypadButton = InputEventJoypadButton.new()
		ev.device = 0
		ev.button_index = button
		ev.pressed = pressed
		ev.pressure = 1.0 if pressed else 0.0
		Input.parse_input_event(ev)
		await _frames(3)


func test_start_opens_pause_and_a_opens_gun_tuning() -> void:
	await _pad(JOY_BUTTON_START)
	assert_true(PauseMenu.is_open(), "Start opens the pause menu")
	await _pad(JOY_BUTTON_DPAD_DOWN)
	var focused: Control = get_viewport().gui_get_focus_owner()
	assert_not_null(focused)
	assert_eq((focused as Button).text if focused is Button else "", "Gun tuning", "D-pad down highlights Gun tuning")
	await _pad(JOY_BUTTON_A)
	assert_true(TuningMenu.is_open(), "A opens the tuning menu")
	assert_false(PauseMenu.is_open(), "pause menu hides under it")
	assert_true(get_tree().paused, "game stays paused")


func test_tuning_slider_moves_with_dpad_and_b_goes_back() -> void:
	await _pad(JOY_BUTTON_START)
	await _pad(JOY_BUTTON_DPAD_DOWN)
	await _pad(JOY_BUTTON_A)
	assert_true(TuningMenu.is_open())
	# Walk down to the first slider and nudge it right.
	var slider: HSlider = null
	for i: int in 12:
		await _pad(JOY_BUTTON_DPAD_DOWN)
		slider = get_viewport().gui_get_focus_owner() as HSlider
		if slider:
			break
	assert_not_null(slider, "D-pad reaches the sliders")
	if slider:
		var before: float = slider.value
		await _pad(JOY_BUTTON_DPAD_RIGHT)
		assert_gt(slider.value, before, "D-pad right raises the value")
	await _pad(JOY_BUTTON_B)
	assert_false(TuningMenu.is_open(), "B closes tuning")
	assert_true(PauseMenu.is_open(), "B returns to the pause menu")
