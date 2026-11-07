class_name InputBindings
extends RefCounted
## Default controls (CLAUDE.md §9.4), registered into the InputMap at startup.
## Keyboard and mouse bindings are for desktop testing only; the game targets
## a controller. Stick deadzones are applied in code (see Stick), so stick
## actions use a tiny action deadzone.

const STICK_DEADZONE: float = 0.02
const TRIGGER_DEADZONE: float = 0.3
const BUTTON_DEADZONE: float = 0.5
const ALL_DEVICES: int = -1


class Binding:
	var action: StringName
	var joy_button: JoyButton = JOY_BUTTON_INVALID
	var joy_axis: JoyAxis = JOY_AXIS_INVALID
	var axis_sign: float = 0.0
	var keys: Array[Key] = []
	var mouse_button: MouseButton = MOUSE_BUTTON_NONE
	var deadzone: float = BUTTON_DEADZONE

	func _init(p_action: StringName, p_keys: Array[Key]) -> void:
		action = p_action
		keys = p_keys


static func _button(action: StringName, button: JoyButton, keys: Array[Key], mouse: MouseButton = MOUSE_BUTTON_NONE) -> Binding:
	var b: Binding = Binding.new(action, keys)
	b.joy_button = button
	b.mouse_button = mouse
	return b


static func _axis(action: StringName, axis: JoyAxis, sign: float, keys: Array[Key], deadzone: float, mouse: MouseButton = MOUSE_BUTTON_NONE) -> Binding:
	var b: Binding = Binding.new(action, keys)
	b.joy_axis = axis
	b.axis_sign = sign
	b.deadzone = deadzone
	b.mouse_button = mouse
	return b


static func defaults() -> Array[Binding]:
	return [
		_axis(&"move_forward", JOY_AXIS_LEFT_Y, -1.0, [KEY_W], STICK_DEADZONE),
		_axis(&"move_back", JOY_AXIS_LEFT_Y, 1.0, [KEY_S], STICK_DEADZONE),
		_axis(&"move_left", JOY_AXIS_LEFT_X, -1.0, [KEY_A], STICK_DEADZONE),
		_axis(&"move_right", JOY_AXIS_LEFT_X, 1.0, [KEY_D], STICK_DEADZONE),
		_axis(&"look_up", JOY_AXIS_RIGHT_Y, -1.0, [KEY_UP], STICK_DEADZONE),
		_axis(&"look_down", JOY_AXIS_RIGHT_Y, 1.0, [KEY_DOWN], STICK_DEADZONE),
		_axis(&"look_left", JOY_AXIS_RIGHT_X, -1.0, [KEY_LEFT], STICK_DEADZONE),
		_axis(&"look_right", JOY_AXIS_RIGHT_X, 1.0, [KEY_RIGHT], STICK_DEADZONE),
		_axis(&"aim", JOY_AXIS_TRIGGER_LEFT, 1.0, [], TRIGGER_DEADZONE, MOUSE_BUTTON_RIGHT),
		_axis(&"fire", JOY_AXIS_TRIGGER_RIGHT, 1.0, [], TRIGGER_DEADZONE, MOUSE_BUTTON_LEFT),
		_button(&"sprint", JOY_BUTTON_LEFT_STICK, [KEY_SHIFT]),
		_button(&"melee", JOY_BUTTON_RIGHT_STICK, [KEY_V]),
		# Owner, 2026-11-07: up to three actives, all fired with LB; D-pad
		# left / down / right picks which one LB uses. RB is free for now.
		_button(&"active_use", JOY_BUTTON_LEFT_SHOULDER, [KEY_Q]),
		_button(&"active_select_1", JOY_BUTTON_DPAD_LEFT, [KEY_4]),
		_button(&"active_select_2", JOY_BUTTON_DPAD_DOWN, [KEY_5]),
		_button(&"active_select_3", JOY_BUTTON_DPAD_RIGHT, [KEY_6]),
		# Shell type on guns that take several (Saiga): D-pad up cycles.
		_button(&"item_next", JOY_BUTTON_DPAD_UP, [KEY_X]),
		_button(&"item_prev", JOY_BUTTON_INVALID, [KEY_Z]),
		_button(&"jump", JOY_BUTTON_A, [KEY_SPACE]),
		_button(&"slide", JOY_BUTTON_B, [KEY_C, KEY_CTRL]),
		_button(&"reload", JOY_BUTTON_X, [KEY_R]),
		_button(&"switch_weapon", JOY_BUTTON_Y, [KEY_1]),
		_button(&"pause", JOY_BUTTON_START, [KEY_ESCAPE]),
		_button(&"body_status", JOY_BUTTON_BACK, [KEY_TAB]),
		_button(&"toggle_overlay", JOY_BUTTON_INVALID, [KEY_F3]),
	]


## Controller buttons for Godot's built-in menu actions. Godot 4.7's defaults
## give ui_accept and ui_cancel no joypad button at all, so menus could be
## navigated with the D-pad but nothing could be pressed (playtest 2026-11-01).
const UI_BUTTONS: Dictionary[StringName, JoyButton] = {
	&"ui_accept": JOY_BUTTON_A,
	&"ui_cancel": JOY_BUTTON_B,
}


## Adds every default action that isn't in the InputMap yet, and the
## controller buttons for menus. Returns how many game actions were added.
static func register_defaults() -> int:
	register_ui_buttons()
	var added: int = 0
	for b: Binding in defaults():
		if InputMap.has_action(b.action):
			continue
		InputMap.add_action(b.action, b.deadzone)
		for event: InputEvent in events_for(b):
			InputMap.action_add_event(b.action, event)
		added += 1
	return added


## Makes A press menu buttons and B go back, without duplicating bindings.
static func register_ui_buttons() -> void:
	for action: StringName in UI_BUTTONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		var button: JoyButton = UI_BUTTONS[action]
		var bound: bool = false
		for ev: InputEvent in InputMap.action_get_events(action):
			var jb: InputEventJoypadButton = ev as InputEventJoypadButton
			if jb and jb.button_index == button:
				bound = true
		if not bound:
			var jb: InputEventJoypadButton = InputEventJoypadButton.new()
			jb.button_index = button
			jb.device = ALL_DEVICES
			InputMap.action_add_event(action, jb)


static func events_for(b: Binding) -> Array[InputEvent]:
	var events: Array[InputEvent] = []
	if b.joy_button != JOY_BUTTON_INVALID:
		var jb: InputEventJoypadButton = InputEventJoypadButton.new()
		jb.button_index = b.joy_button
		jb.device = ALL_DEVICES
		events.append(jb)
	if b.joy_axis != JOY_AXIS_INVALID:
		var jm: InputEventJoypadMotion = InputEventJoypadMotion.new()
		jm.axis = b.joy_axis
		jm.axis_value = b.axis_sign
		jm.device = ALL_DEVICES
		events.append(jm)
	for key: Key in b.keys:
		var k: InputEventKey = InputEventKey.new()
		k.physical_keycode = key
		k.device = ALL_DEVICES
		events.append(k)
	if b.mouse_button != MOUSE_BUTTON_NONE:
		var m: InputEventMouseButton = InputEventMouseButton.new()
		m.button_index = b.mouse_button
		m.device = ALL_DEVICES
		events.append(m)
	return events
