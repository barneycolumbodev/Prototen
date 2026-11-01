extends CanvasLayer
## On-device gun tuning (docs/m1-gunplay-plan.md item 5, docs/design.md §5.4).
## Autoloaded as TuningMenu; opened from the pause menu. Every slider edits
## the live WeaponData / AimAssistConfig, so changes are felt immediately.
## Tuned values persist on the phone (user://tuning.cfg) and "Copy values"
## puts them on the clipboard in .tres form, ready to send back.
## Controller: D-pad/stick up-down to pick, left-right to change, B to close.

const SAVE_PATH: String = "user://tuning.cfg"

## [section, property, min, max, step, label]
const WEAPON_PARAMS: Array = [
	["Recoil", "kick_pitch_deg", 0.0, 4.0, 0.05, "Kick up (°)"],
	["Recoil", "kick_yaw_deg", 0.0, 2.0, 0.02, "Kick sideways (± °)"],
	["Recoil", "kick_yaw_bias_deg", -0.5, 0.5, 0.01, "Drift right (°/shot)"],
	["Recoil", "kick_permanent", 0.0, 1.0, 0.02, "Climb that stays"],
	["Recoil", "camera_spring_hz", 1.0, 20.0, 0.25, "Recovery speed (Hz)"],
	["Recoil", "camera_spring_damping", 0.2, 1.5, 0.05, "Recovery damping"],
	["Recoil", "ads_recoil_scale", 0.2, 1.5, 0.05, "Recoil when aimed"],
	["Gun motion", "vm_kick_back", 0.0, 0.08, 0.002, "Gun kick back (m)"],
	["Gun motion", "vm_kick_rise_deg", 0.0, 20.0, 0.5, "Muzzle flip (°)"],
	["Gun motion", "vm_kick_roll_deg", 0.0, 10.0, 0.25, "Roll (°)"],
	["Gun motion", "vm_spring_hz", 2.0, 25.0, 0.5, "Gun spring (Hz)"],
	["Gun motion", "vm_spring_damping", 0.1, 1.5, 0.05, "Gun spring damping"],
	["Gun motion", "sway_per_turn", 0.0, 0.05, 0.001, "Sway when turning"],
	["Gun motion", "bob_amount", 0.0, 0.03, 0.001, "Walk bob (m)"],
	["Aiming", "ads_time", 0.05, 0.5, 0.01, "Time to aim (s)"],
	["Aiming", "ads_fov_scale", 0.5, 1.0, 0.01, "Aimed zoom (FOV ×)"],
	["Aiming", "ads_sensitivity", 0.3, 1.5, 0.05, "Aimed look speed"],
	["Accuracy", "mechanical_moa", 0.0, 10.0, 0.25, "Precision aimed (MOA)"],
	["Accuracy", "hip_spread_deg", 0.0, 4.0, 0.05, "Hip spread (°)"],
	["Accuracy", "move_spread_deg", 0.0, 4.0, 0.05, "Moving spread (°)"],
	["Accuracy", "bloom_per_shot_deg", 0.0, 2.0, 0.05, "Bloom per shot (°)"],
	["Fire", "fire_interval", 0.05, 0.3, 0.005, "Fastest follow-up (s)"],
	["Fire", "fire_buffer", 0.0, 0.3, 0.01, "Trigger buffer (s)"],
	["Ballistics", "muzzle_velocity", 300.0, 900.0, 10.0, "Muzzle velocity (m/s)"],
	["Ballistics", "penetration_scale", 0.3, 3.0, 0.05, "Penetration power"],
	["Ballistics", "damage_per_joule", 0.05, 0.4, 0.005, "Damage per joule"],
	["Ballistics", "impulse_scale", 0.0, 80.0, 1.0, "Push on hit"],
	["Feedback", "hitstop_headshot", 0.0, 0.15, 0.005, "Hit-stop headshot (s)"],
	["Feedback", "hitstop_kill", 0.0, 0.15, 0.005, "Hit-stop kill (s)"],
]
const ASSIST_PARAMS: Array = [
	["Aim assist", "slowdown", 0.1, 1.0, 0.05, "Slowdown on target"],
	["Aim assist", "slowdown_radius_deg", 0.0, 10.0, 0.25, "Slowdown radius (°)"],
	["Aim assist", "pull_deg_s", 0.0, 20.0, 0.5, "Pull when aimed (°/s)"],
]

var _root: Control
var _list: VBoxContainer
var _readout: TextEdit
var _first_focus: Control
var _weapon: PlayerWeapon
var _assist: AimAssistConfig


func _ready() -> void:
	layer = 110  # above the debug overlay
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.visible = false
	add_child(_root)


func is_open() -> bool:
	return _root.visible


func open() -> void:
	var player: Player = get_tree().get_first_node_in_group(&"player") as Player
	if player == null or player.weapon() == null:
		return
	_weapon = player.weapon()
	_assist = player.aim_assist.config if player.aim_assist else null
	_build()
	_root.visible = true
	DebugOverlay.visible = false
	get_tree().paused = true
	if _first_focus:
		_first_focus.grab_focus()


func close() -> void:
	_root.visible = false
	DebugOverlay.visible = true
	get_tree().paused = false
	save()


func _unhandled_input(event: InputEvent) -> void:
	if is_open() and (event.is_action_pressed(&"ui_cancel") or event.is_action_pressed(&"pause")):
		close()
		get_viewport().set_input_as_handled()


## Writes every tunable value to user://tuning.cfg.
func save() -> void:
	if _weapon == null:
		return
	var cfg: ConfigFile = ConfigFile.new()
	for p: Array in WEAPON_PARAMS:
		var prop: String = p[1]
		cfg.set_value("weapon", prop, _weapon.data.get(prop))
	if _assist:
		cfg.set_value("aim_assist", "enabled", _assist.enabled)
		for p: Array in ASSIST_PARAMS:
			var prop: String = p[1]
			cfg.set_value("aim_assist", prop, _assist.get(prop))
	cfg.save(SAVE_PATH)


## Applies saved tuning to a weapon and aim assist (call at spawn).
static func load_saved(data: WeaponData, assist: AimAssistConfig) -> void:
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(SAVE_PATH) != OK:
		return
	for prop: String in cfg.get_section_keys("weapon") if cfg.has_section("weapon") else PackedStringArray():
		if prop in data:
			data.set(prop, cfg.get_value("weapon", prop))
	if assist and cfg.has_section("aim_assist"):
		for prop: String in cfg.get_section_keys("aim_assist"):
			if prop in assist:
				assist.set(prop, cfg.get_value("aim_assist", prop))


## Tuned values as .tres lines (what "Copy values" puts on the clipboard).
func values_text() -> String:
	var lines: PackedStringArray = PackedStringArray(["# %s (data/weapons)" % _weapon.data.display_name])
	for p: Array in WEAPON_PARAMS:
		var prop: String = p[1]
		lines.append("%s = %s" % [prop, var_to_str(_weapon.data.get(prop))])
	if _assist:
		lines.append("# aim assist (data/input/aim_assist.tres)")
		lines.append("enabled = %s" % var_to_str(_assist.enabled))
		for p: Array in ASSIST_PARAMS:
			var prop: String = p[1]
			lines.append("%s = %s" % [prop, var_to_str(_assist.get(prop))])
	return "\n".join(lines)


func _build() -> void:
	for c: Node in _root.get_children():
		c.queue_free()
	var dim: ColorRect = ColorRect.new()
	dim.color = Color(0, 0, 0, 0.72)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)
	var margin: MarginContainer = MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side: String in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 24)
	_root.add_child(margin)
	var columns: HBoxContainer = HBoxContainer.new()
	columns.add_theme_constant_override("separation", 24)
	margin.add_child(columns)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_stretch_ratio = 1.6
	scroll.follow_focus = true
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	columns.add_child(scroll)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_list)
	_first_focus = null

	var title: Label = Label.new()
	title.text = "GUN TUNING — %s" % _weapon.data.display_name
	title.add_theme_font_size_override("font_size", 22)
	_list.add_child(title)
	_button("Close (B)", close)
	_button("Copy values", _on_copy)
	_toggle("Show bullet paths", Ballistics.show_trajectories, func(on: bool) -> void: Ballistics.show_trajectories = on)
	if _assist:
		_toggle("Aim assist", _assist.enabled, func(on: bool) -> void: _assist.enabled = on)
	_toggle("Infinite reserve", _weapon.data.infinite_reserve, func(on: bool) -> void: _weapon.data.infinite_reserve = on)
	_button("Reset range stats", func() -> void:
		var stats: RangeStats = get_tree().get_first_node_in_group(&"range_stats") as RangeStats
		if stats:
			stats.reset())
	_button("Restore defaults", _on_defaults)
	var section: String = ""
	for p: Array in WEAPON_PARAMS + (ASSIST_PARAMS if _assist else []):
		var sec: String = p[0]
		if sec != section:
			section = sec
			var head: Label = Label.new()
			head.text = sec.to_upper()
			head.add_theme_color_override("font_color", Color(1.0, 0.75, 0.4))
			head.add_theme_font_size_override("font_size", 15)
			_list.add_child(head)
		var target: Resource = _assist if sec == "Aim assist" else _weapon.data
		var prop: String = p[1]
		var lo: float = p[2]
		var hi: float = p[3]
		var step: float = p[4]
		var text: String = p[5]
		_slider(target, prop, lo, hi, step, text)

	var right: VBoxContainer = VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(right)
	var hint: Label = Label.new()
	hint.text = "Changes apply live. They're saved on this phone.\n\"Copy values\" puts them on the clipboard — paste them into a message to send them back."
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_theme_font_size_override("font_size", 13)
	right.add_child(hint)
	_readout = TextEdit.new()
	_readout.editable = false
	_readout.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_readout.add_theme_font_size_override("font_size", 12)
	_readout.focus_mode = Control.FOCUS_NONE
	right.add_child(_readout)
	_readout.text = values_text()


func _slider(target: Resource, prop: String, lo: float, hi: float, step: float, text: String) -> void:
	var row: HBoxContainer = HBoxContainer.new()
	_list.add_child(row)
	var name_label: Label = Label.new()
	name_label.text = text
	name_label.custom_minimum_size = Vector2(210, 0)
	name_label.add_theme_font_size_override("font_size", 14)
	row.add_child(name_label)
	var slider: HSlider = HSlider.new()
	slider.min_value = lo
	slider.max_value = hi
	slider.step = step
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.custom_minimum_size = Vector2(160, 28)
	var current: float = target.get(prop)
	slider.value = current
	row.add_child(slider)
	var value_label: Label = Label.new()
	value_label.custom_minimum_size = Vector2(70, 0)
	value_label.add_theme_font_size_override("font_size", 14)
	value_label.text = _fmt(slider.value, step)
	row.add_child(value_label)
	slider.value_changed.connect(func(v: float) -> void:
		target.set(prop, v)
		value_label.text = _fmt(v, step)
		_weapon.apply_tuning()
		if _readout:
			_readout.text = values_text())
	if _first_focus == null:
		_first_focus = slider


func _button(text: String, action: Callable) -> void:
	var b: Button = Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 34)
	b.pressed.connect(action)
	_list.add_child(b)
	if _first_focus == null:
		_first_focus = b


func _toggle(text: String, on: bool, action: Callable) -> void:
	var c: CheckButton = CheckButton.new()
	c.text = text
	c.button_pressed = on
	c.toggled.connect(action)
	_list.add_child(c)


func _on_copy() -> void:
	DisplayServer.clipboard_set(values_text())
	_readout.text = "Copied to the clipboard.\n\n" + values_text()


func _on_defaults() -> void:
	var fresh: WeaponData = ResourceLoader.load(_weapon.data.resource_path, "", ResourceLoader.CACHE_MODE_IGNORE) as WeaponData
	if fresh:
		for p: Array in WEAPON_PARAMS:
			var prop: String = p[1]
			_weapon.data.set(prop, fresh.get(prop))
	if _assist:
		var fresh_assist: AimAssistConfig = ResourceLoader.load(_assist.resource_path, "", ResourceLoader.CACHE_MODE_IGNORE) as AimAssistConfig
		if fresh_assist:
			_assist.enabled = fresh_assist.enabled
			for p: Array in ASSIST_PARAMS:
				var prop: String = p[1]
				_assist.set(prop, fresh_assist.get(prop))
	_weapon.apply_tuning()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))
	_build()
	if _first_focus:
		_first_focus.grab_focus()


static func _fmt(v: float, step: float) -> String:
	if step >= 1.0:
		return "%d" % roundi(v)
	var decimals: int = clampi(ceili(-log(step) / log(10.0)), 1, 4)
	return String.num(v, decimals)
