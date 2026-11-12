extends GutTest
## Controls from CLAUDE.md §9.4 are registered.

const EXPECTED: Dictionary[StringName, JoyButton] = {
	&"sprint": JOY_BUTTON_LEFT_STICK,
	&"melee": JOY_BUTTON_RIGHT_STICK,
	&"active_use": JOY_BUTTON_LEFT_SHOULDER,
	&"active_select_1": JOY_BUTTON_DPAD_LEFT,
	&"active_select_2": JOY_BUTTON_DPAD_DOWN,
	&"active_select_3": JOY_BUTTON_DPAD_RIGHT,
	&"item_next": JOY_BUTTON_DPAD_UP,
	&"jump": JOY_BUTTON_A,
	&"slide": JOY_BUTTON_B,
	&"reload": JOY_BUTTON_X,
	&"switch_weapon": JOY_BUTTON_Y,
	&"pause": JOY_BUTTON_START,
	&"body_status": JOY_BUTTON_BACK,
	&"menu_jump": JOY_BUTTON_RIGHT_SHOULDER,
}


func test_buttons_match_spec() -> void:
	for action: StringName in EXPECTED:
		assert_true(InputMap.has_action(action), str(action))
		var ev: InputEventJoypadButton = InputEventJoypadButton.new()
		ev.button_index = EXPECTED[action]
		ev.pressed = true
		assert_true(InputMap.event_is_action(ev, action), "%s on button %d" % [action, EXPECTED[action]])


func test_triggers_aim_and_fire() -> void:
	var lt: InputEventJoypadMotion = InputEventJoypadMotion.new()
	lt.axis = JOY_AXIS_TRIGGER_LEFT
	lt.axis_value = 1.0
	assert_true(InputMap.event_is_action(lt, &"aim"))
	var rt: InputEventJoypadMotion = InputEventJoypadMotion.new()
	rt.axis = JOY_AXIS_TRIGGER_RIGHT
	rt.axis_value = 1.0
	assert_true(InputMap.event_is_action(rt, &"fire"))


func test_bindings_match_any_controller() -> void:
	var ev: InputEventJoypadButton = InputEventJoypadButton.new()
	ev.button_index = JOY_BUTTON_A
	ev.pressed = true
	ev.device = 3
	assert_true(InputMap.event_is_action(ev, &"jump"))


func test_register_is_idempotent() -> void:
	assert_eq(InputBindings.register_defaults(), 0)
