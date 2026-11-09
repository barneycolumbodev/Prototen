class_name TimeDilation
extends ActivePart
## RX-9 Reflex Overclock: time slowdown on LB (owner, 2026-11-05).
## Press to start, press again to stop, or it runs until the charge is gone;
## the charge refills over time like health. While it's on the world runs at
## `world_scale` and the operative at `player_scale` (move, shoot, reload);
## looking stays real time. The world loses colour, sound is muffled and
## pitched down, the view widens a touch, and hits land harder.

const OVERLAY_SHADER: String = """
shader_type canvas_item;
uniform vec4 tint : source_color = vec4(0.45, 0.85, 0.95, 0.16);
uniform float amount = 0.0;
void fragment() {
	vec2 d = UV - 0.5;
	d.x *= 1.6;
	float r = length(d);
	float edge = smoothstep(0.35, 0.95, r);
	COLOR = vec4(tint.rgb, (edge * 0.9 + 0.1) * tint.a * 3.0 * amount);
	COLOR.a = min(COLOR.a, 0.6);
}
"""

var cfg: TimeDilationData
var _env: Environment
var _base_saturation: float = 1.0
var _overlay: ColorRect
var _layer: CanvasLayer
var _hum: AudioStreamPlayer


func _ready() -> void:
	super._ready()
	cfg = data as TimeDilationData
	TimeControl.dilation_impact_boost = cfg.impact_boost
	_layer = CanvasLayer.new()
	_layer.layer = 4
	add_child(_layer)
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
	_layer.add_child(_overlay)
	_hum = AudioStreamPlayer.new()
	_hum.bus = &"Master"
	_hum.volume_db = -14.0
	var loop: Array = Sfx.bank(&"td_loop")
	if not loop.is_empty():
		_hum.stream = loop[0]
	add_child(_hum)


func _exit_tree() -> void:
	# Never leave the world slowed or muffled (scene change, death, tests).
	TimeControl.set_dilation(1.0, 1.0)
	_set_lowpass(1.0)
	if _env:
		_env.adjustment_saturation = _base_saturation


func _on_start() -> void:
	_env = _find_environment()
	if _env:
		_base_saturation = _env.adjustment_saturation if _env.adjustment_enabled else 1.0
		_env.adjustment_enabled = true
	Sfx.play_ui(&"td_in", -3.0, 0.0)
	_overlay.visible = true
	if _hum.stream:
		_hum.play()


func _on_stop() -> void:
	Sfx.play_ui(&"td_out", -5.0, 0.0)
	_hum.stop()


func _on_denied() -> void:
	Sfx.play_ui(&"td_denied", -8.0, 0.0)


## Body processing relative to the tuning reference (1 without a body).
func processing_ratio() -> float:
	var c: TimeDilationData = data as TimeDilationData
	if body == null or c == null:
		return 1.0
	return body.stat(&"processing") / maxf(c.processing_ref, 0.01)


## How fast the operative runs while dilated: faster with more processing.
func player_scale_now() -> float:
	var c: TimeDilationData = data as TimeDilationData
	return clampf(c.player_scale * (1.0 + c.processing_speed_share * (processing_ratio() - 1.0)), c.world_scale, c.max_player_scale)


func charge_capacity() -> float:
	return data.charge_max * processing_ratio()


func _on_blend(a: float) -> void:
	var e: float = a * a * (3.0 - 2.0 * a)
	TimeControl.set_dilation(lerpf(1.0, cfg.world_scale, e), lerpf(1.0, player_scale_now(), e))
	if _env:
		_env.adjustment_saturation = lerpf(_base_saturation, _base_saturation * cfg.saturation, e)
	(_overlay.material as ShaderMaterial).set_shader_parameter(&"amount", e)
	_overlay.visible = e > 0.001
	_set_lowpass(1.0 - e)
	if player:
		player.fov_add_deg = cfg.fov_kick_deg * e
	if e <= 0.001 and state == State.COOLDOWN:
		_overlay.visible = false


func _on_active(_real_delta: float) -> void:
	if _hum.stream and not _hum.playing:
		_hum.play()
	_hum.pitch_scale = 1.0


## 1 = open (no filter), 0 = fully muffled.
func _set_lowpass(open: float) -> void:
	Sfx.set_muffle(1.0 - open, cfg.lowpass_hz)


func _find_environment() -> Environment:
	var vp: Viewport = get_viewport()
	if vp and vp.world_3d and vp.world_3d.environment:
		return vp.world_3d.environment
	var scene: Node = get_tree().current_scene
	if scene:
		for n: Node in scene.find_children("*", "WorldEnvironment", true, false):
			var we: WorldEnvironment = n as WorldEnvironment
			if we and we.environment:
				return we.environment
	return null
