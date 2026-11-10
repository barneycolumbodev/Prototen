class_name ThermopticShroud
extends ActivePart
## TC-4 Thermoptic Shroud: active camouflage (ThermopticShroudData). While
## it's up BodyModel.cloak is 1: enemies stop seeing the operative
## (Enemy._update_perception) unless he's within the reveal distance, has
## just fired or has just been hit. Your own arms and gun go see-through
## and the edge of the view shimmers.

const OVERLAY_SHADER: String = """
shader_type canvas_item;
uniform vec4 tint : source_color = vec4(0.5, 0.75, 1.0, 0.2);
uniform float amount = 0.0;
uniform float broken = 0.0;
void fragment() {
	vec2 d = UV - 0.5;
	d.x *= 1.7;
	float r = length(d);
	// A hexagonal lattice crawling at the edge of the view.
	vec2 p = UV * vec2(64.0, 36.0);
	p.x += 0.5 * mod(floor(p.y), 2.0);
	vec2 c = fract(p) - 0.5;
	float cell = smoothstep(0.42, 0.5, max(abs(c.x), abs(c.y)));
	float wave = 0.5 + 0.5 * sin(TIME * 2.3 + r * 22.0);
	float edge = smoothstep(0.38, 0.95, r);
	float a = edge * (0.45 + 0.55 * cell * wave) * tint.a * 2.4 * amount;
	a += broken * 0.18 * (0.5 + 0.5 * sin(TIME * 90.0));
	COLOR = vec4(mix(tint.rgb, vec3(1.0, 0.5, 0.3), broken), min(a, 0.6));
}
"""

## What your own arms and gun look like under the shroud: a glassy outline.
const BODY_SHADER: String = """
shader_type spatial;
render_mode unshaded, depth_draw_always, cull_back;
uniform vec4 tint : source_color = vec4(0.5, 0.75, 1.0, 0.2);
uniform float solid = 0.0;
void fragment() {
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.2);
	float wave = 0.5 + 0.5 * sin(TIME * 5.0 + FRAGCOORD.y * 0.05);
	ALBEDO = tint.rgb * (0.35 + 1.2 * rim + 0.5 * solid);
	ALPHA = clamp(0.05 + 0.5 * rim + 0.04 * wave + 0.45 * solid, 0.0, 1.0);
}
"""

var cfg: ThermopticShroudData
var _reveal: float = 0.0
var _ghost: ShaderMaterial
var _was: Dictionary[GeometryInstance3D, Material] = {}
var _ghosted: bool = false
var _overlay: ColorRect
var _geo: Array[GeometryInstance3D] = []
var _hum: AudioStreamPlayer


func _ready() -> void:
	super._ready()
	cfg = data as ThermopticShroudData
	var layer: CanvasLayer = CanvasLayer.new()
	layer.layer = 4
	add_child(layer)
	_overlay = ColorRect.new()
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = OVERLAY_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"tint", cfg.tint)
	_overlay.material = mat
	_overlay.visible = false
	layer.add_child(_overlay)
	_ghost = ShaderMaterial.new()
	var body_shader: Shader = Shader.new()
	body_shader.code = BODY_SHADER
	_ghost.shader = body_shader
	_ghost.set_shader_parameter(&"tint", cfg.tint)
	_hum = AudioStreamPlayer.new()
	_hum.bus = &"SFX"
	_hum.volume_db = -20.0
	var loop: Array = Sfx.bank(&"tc4_loop")
	if not loop.is_empty():
		_hum.stream = loop[0]
	add_child(_hum)
	EventBus.shot_fired.connect(_on_shot)
	if player:
		player.damaged.connect(_on_damaged)


func _exit_tree() -> void:
	super._exit_tree()
	if body:
		body.cloak = 0.0
	_set_arms(0.0)


## How far away (m) enemies start to see through it: a hot, loud signature
## shimmers from further off.
func reveal_distance() -> float:
	if body == null:
		return cfg.reveal_m
	return cfg.reveal_m * clampf(body.stat(&"signature"), 0.5, 2.5)


## Hidden right now (up and not just revealed).
func is_hidden() -> bool:
	return is_running() and _reveal <= 0.0


func _on_start() -> void:
	_reveal = 0.0
	_geo.clear()
	if player:
		for n: Node in player.camera().find_children("*", "GeometryInstance3D", true, false):
			_geo.append(n as GeometryInstance3D)
	if body:
		body.cloak_reveal_m = reveal_distance()
	_overlay.visible = true
	Sfx.play_ui(&"tc4_on", -4.0, 0.0)
	if _hum.stream:
		_hum.play()


func _on_stop() -> void:
	Sfx.play_ui(&"tc4_off", -5.0, 0.0)
	_hum.stop()


func _on_denied() -> void:
	Sfx.play_ui(&"td_denied", -8.0, 0.0)


func _on_blend(a: float) -> void:
	_apply(a)
	if a <= 0.001:
		_overlay.visible = false


func _on_active(real: float) -> void:
	_reveal = maxf(0.0, _reveal - real)
	_apply(1.0)
	if _hum.stream and not _hum.playing:
		_hum.play()
	if body and body.overheated():
		# The trapped heat has nowhere left to go.
		Sfx.play_ui(&"tc4_fail", -2.0, 0.0)
		stop()


func _apply(a: float) -> void:
	var hidden: float = a * (0.0 if _reveal > 0.0 else 1.0)
	if body:
		body.cloak = hidden
	var m: ShaderMaterial = _overlay.material as ShaderMaterial
	m.set_shader_parameter(&"amount", a)
	m.set_shader_parameter(&"broken", clampf(_reveal / maxf(cfg.shot_reveal_time, 0.01), 0.0, 1.0) * a)
	_set_arms(cfg.arm_transparency * a * (0.35 if _reveal > 0.0 else 1.0))


## Your own arms and gun: glass while hidden (more solid for a moment when
## the shroud is broken), back to normal when `t` is 0.
func _set_arms(t: float) -> void:
	var ghost: bool = t > 0.3 * cfg.arm_transparency
	_ghost.set_shader_parameter(&"solid", clampf(1.0 - t / maxf(cfg.arm_transparency, 0.01), 0.0, 1.0))
	if ghost == _ghosted:
		return
	_ghosted = ghost
	if ghost:
		_was.clear()
		for g: GeometryInstance3D in _geo:
			if is_instance_valid(g):
				_was[g] = g.material_override
				g.material_override = _ghost
	else:
		for g: GeometryInstance3D in _was:
			if is_instance_valid(g):
				g.material_override = _was[g]
		_was.clear()


func _on_shot(shooter: Node, _origin: Vector3, _dir: Vector3) -> void:
	if shooter == player and is_running():
		_reveal = maxf(_reveal, cfg.shot_reveal_time)
		charge = maxf(charge - cfg.shot_cost, 0.0)


func _on_damaged(_amount: float, _from: Vector3) -> void:
	if is_running():
		_reveal = maxf(_reveal, cfg.hit_reveal_time)
