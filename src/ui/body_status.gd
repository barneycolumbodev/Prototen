class_name BodyStatus
extends CanvasLayer
## Body status (View button, CLAUDE.md §9.4; also Pause → Body status): the
## operative on a turntable as the installed parts make him look, and the
## numbers the parts system adds up: mass, constant power draw and heat,
## loadout capacity, every stat, and each installed part. Pauses the game.
## The loadout screen (M2) grows out of this.

const STUDIO_SKY: Shader = preload("res://src/ui/studio_sky.gdshader")

var player: Player
var appearance: BodyAppearance

var _viewport: SubViewport
var _pivot: Node3D
var _text: RichTextLabel


func _ready() -> void:
	layer = 60
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	var bg: ColorRect = ColorRect.new()
	bg.color = Color(0.02, 0.025, 0.03, 0.94)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var row: HBoxContainer = HBoxContainer.new()
	row.set_anchors_preset(Control.PRESET_FULL_RECT)
	row.add_theme_constant_override("separation", 24)
	add_child(row)
	var svc: SubViewportContainer = SubViewportContainer.new()
	svc.stretch = true
	svc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	svc.size_flags_stretch_ratio = 0.9
	row.add_child(svc)
	_viewport = SubViewport.new()
	_viewport.own_world_3d = true
	_viewport.transparent_bg = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_WHEN_VISIBLE
	svc.add_child(_viewport)
	# The 3D stage (model, lights) is built the first time the screen opens.
	var margin: MarginContainer = MarginContainer.new()
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for side: String in ["top", "bottom", "right"]:
		margin.add_theme_constant_override("margin_" + side, 28)
	row.add_child(margin)
	_text = RichTextLabel.new()
	_text.bbcode_enabled = true
	_text.fit_content = false
	_text.scroll_active = true
	_text.add_theme_font_size_override("normal_font_size", 15)
	_text.add_theme_font_size_override("bold_font_size", 17)
	margin.add_child(_text)


func _build_stage() -> void:
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.25, 0.28, 0.33)
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true
	# A studio sky that is only reflected (the background stays transparent):
	# softbox strips give the gloss carapace its highlights.
	var sky_mat: ShaderMaterial = ShaderMaterial.new()
	sky_mat.shader = STUDIO_SKY
	env.sky = Sky.new()
	env.sky.sky_material = sky_mat
	env.sky.radiance_size = Sky.RADIANCE_SIZE_128
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	var we: WorldEnvironment = WorldEnvironment.new()
	we.environment = env
	_viewport.add_child(we)
	var cam: Camera3D = Camera3D.new()
	cam.fov = 32.0
	cam.position = Vector3(0, 1.05, 5.2)
	cam.look_at_from_position(cam.position, Vector3(0, 0.98, 0))
	_viewport.add_child(cam)
	# Key (warm, front right), two cool rims from behind, a faint fill.
	for spec: Array in [[Vector3(-35, 35, 0), Color(1.0, 0.94, 0.87), 0.5], [Vector3(-20, 145, 0), Color(0.55, 0.85, 1.0), 0.75],
			[Vector3(-15, -140, 0), Color(0.8, 0.9, 1.0), 0.55], [Vector3(-5, -50, 0), Color(0.85, 0.85, 1.0), 0.1]]:
		var l: DirectionalLight3D = DirectionalLight3D.new()
		l.rotation_degrees = spec[0]
		l.light_color = spec[1]
		l.light_energy = spec[2]
		_viewport.add_child(l)
	_pivot = Node3D.new()
	_viewport.add_child(_pivot)
	appearance = BodyAppearance.new()
	_pivot.add_child(appearance)
	var floor_mesh: MeshInstance3D = MeshInstance3D.new()
	var disc: CylinderMesh = CylinderMesh.new()
	disc.top_radius = 0.6
	disc.bottom_radius = 0.62
	disc.height = 0.03
	floor_mesh.mesh = disc
	var fm: StandardMaterial3D = StandardMaterial3D.new()
	fm.albedo_color = Color(0.05, 0.055, 0.06)
	fm.roughness = 0.3
	fm.emission_enabled = true
	fm.emission = Color(0.36, 0.86, 0.78) * 0.08
	floor_mesh.material_override = fm
	floor_mesh.position.y = -0.015
	_viewport.add_child(floor_mesh)


func is_open() -> bool:
	return visible


func open() -> void:
	if player == null:
		return
	if appearance == null:
		_build_stage()
	appearance.loadout = player.loadout
	appearance.rebuild()
	_text.text = describe(player.body)
	_pivot.rotation.y = 0.35
	visible = true
	get_tree().paused = true


func close() -> void:
	visible = false
	get_tree().paused = false


func _process(delta: float) -> void:
	# Cloud screenshots hold the front three-quarter view.
	if visible and _pivot and not CaptureDirector.is_capturing():
		_pivot.rotation.y += delta * 0.6


func _input(event: InputEvent) -> void:
	if event.is_action_pressed(&"body_status"):
		if visible:
			close()
		elif not get_tree().paused:
			open()
		get_viewport().set_input_as_handled()
	elif visible and (event.is_action_pressed(&"ui_cancel") or event.is_action_pressed(&"pause")):
		close()
		get_viewport().set_input_as_handled()


static func _bar(fraction: float, width: int = 18) -> String:
	var n: int = clampi(roundi(fraction * width), 0, width)
	return "[color=#5cdcc6]%s[/color][color=#30383a]%s[/color]" % ["|".repeat(n), "|".repeat(width - n)]


## The status text (BBCode). Static so tests can check it without a screen.
static func describe(b: BodyModel) -> String:
	var f: PlayerBodyConfig = b.frame
	var lines: PackedStringArray = PackedStringArray()
	lines.append("[b]BODY STATUS[/b]   %s" % b.loadout.display_name)
	lines.append("")
	lines.append("Mass        %5.1f kg   (frame %.0f kg)" % [b.mass_kg, f.base_mass_kg])
	lines.append("Capacity    %s  %d / %d" % [_bar(float(b.capacity_used) / f.capacity), b.capacity_used, f.capacity])
	lines.append("Power       %s  %.0f W of %.0f W   reserve %.0f%%" % [_bar(b.current_draw_w() / f.power_supply_w), b.current_draw_w(), f.power_supply_w, b.power_fraction() * 100.0])
	lines.append("Heat        %s  %+.0f W net   stored %.0f%%" % [_bar(b.heat_fraction()), b.heat_w - f.heat_dissipation_w, b.heat_fraction() * 100.0])
	lines.append("")
	lines.append("[b]INSTALLED[/b]")
	for p: PartData in b.loadout.parts:
		var kind: String = "ACTIVE (%s)" % Augments.BUTTONS[(p as ActivePartData).slot - 1] if p.is_active() else "passive"
		var loc: String = PartData.Location.keys()[p.location]
		lines.append("[color=#ffd28a]%s[/color]  [color=#8a9a9a]%s · %s[/color]" % [p.display_name, loc.to_lower(), kind])
		lines.append("    %.1f kg   %+.0f W   %+.0f W heat   cap %d" % [p.mass_kg, p.power_draw_w, p.heat_w, p.capacity])
	lines.append("")
	lines.append("[b]STATS[/b]")
	for s: StringName in BodyModel.STATS:
		var v: float = b.stat(s)
		var base: float = b.base(s)
		var mark: String = "" if is_equal_approx(v, base) else ("  [color=#5cdcc6](%+.0f%%)[/color]" % ((v / maxf(base, 0.0001) - 1.0) * 100.0))
		lines.append("%-14s %.2f%s" % [String(s).replace("_", " "), v, mark])
	lines.append("")
	lines.append("[color=#8a9a9a]View / B: close[/color]")
	return "\n".join(lines)
