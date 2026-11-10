class_name RamThrusters
extends ActivePart
## KR-5 Ram Thrusters: a burst dash that breaks bodies (RamThrustersData).
## One press, one burn; two burns stored, refilling one at a time. Each burn
## takes energy from the power reserve and dumps heat into the body, so a
## brown-out or an overheated body can't fire them.

const STREAK_SHADER: String = """
shader_type canvas_item;
uniform vec4 tint : source_color = vec4(0.75, 0.9, 1.0, 0.5);
uniform float amount = 0.0;
float hash(float n) { return fract(sin(n) * 43758.5453); }
void fragment() {
	vec2 d = UV - 0.5;
	d.x *= 1.7;
	float r = length(d);
	float a = atan(d.y, d.x);
	float ray = hash(floor(a * 60.0));
	float streak = smoothstep(0.72, 1.0, ray) * smoothstep(0.22, 0.75, r);
	float flick = 0.6 + 0.4 * sin(TIME * 70.0 + ray * 40.0);
	COLOR = vec4(tint.rgb, streak * flick * tint.a * amount + smoothstep(0.5, 1.0, r) * 0.12 * amount);
}
"""

var cfg: RamThrustersData
## Enemies struck by the last burn (tests, HUD).
var struck: int = 0
var kills: int = 0

var _dir: Vector3 = Vector3.FORWARD
var _speed: float = 0.0
var _punch: float = 0.0
var _streak: float = 0.0
var _overlay: ColorRect


func _ready() -> void:
	super._ready()
	cfg = data as RamThrustersData
	var layer: CanvasLayer = CanvasLayer.new()
	layer.layer = 3
	add_child(layer)
	_overlay = ColorRect.new()
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = STREAK_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"tint", cfg.streak_color)
	_overlay.material = mat
	_overlay.visible = false
	layer.add_child(_overlay)


func _exit_tree() -> void:
	super._exit_tree()
	if player and is_instance_valid(player) and _punch > 0.0:
		player.fov_punch_deg = 0.0


func hud_pips() -> int:
	return roundi(charge_capacity())


## Each burn spends one stored charge; nothing drains over time.
func _drain(_real: float) -> void:
	pass


func offline_reason() -> String:
	var why: String = super.offline_reason()
	if why == "" and body and body.power_j < cfg.energy_j:
		return "reserve below %.0f kJ" % (cfg.energy_j / 1000.0)
	if why == "" and body and body.overheated():
		return "overheated"
	return why


## Dash speed for this body (m/s): lighter flies faster.
func dash_speed() -> float:
	var mass: float = body.mass_kg if body else cfg.ref_mass_kg
	return cfg.dash_speed * clampf(sqrt(cfg.ref_mass_kg / maxf(mass, 1.0)), cfg.min_speed_scale, cfg.max_speed_scale)


## Speed (m/s) the burn gives a body it hits: the slide hit × ram_multiplier.
func ram_push() -> float:
	if player == null or body == null:
		return 0.0
	return player.movement.slide_knock_speed * (body.mass_kg / 100.0) * body.usable_strength() * body.stat(&"impact") * cfg.ram_multiplier


func _on_start() -> void:
	charge = maxf(charge - 1.0, 0.0)
	struck = 0
	kills = 0
	if body:
		body.power_j = maxf(body.power_j - cfg.energy_j, 0.0)
		body.heat_j = minf(body.heat_j + cfg.heat_j, body.frame.heat_capacity_j)
	var cam: Camera3D = player.camera()
	var fwd: Vector3 = -cam.global_basis.z
	var flat: Vector3 = Vector3(fwd.x, 0.0, fwd.z).normalized()
	var pitch: float = clampf(asin(clampf(fwd.y, -1.0, 1.0)), -deg_to_rad(cfg.max_dive_deg), deg_to_rad(cfg.max_climb_deg))
	_dir = (flat * cos(pitch) + Vector3.UP * sin(pitch)).normalized()
	_speed = dash_speed()
	player.start_dash(_dir * _speed, cfg.dash_time, _on_ram_hit)
	_punch = cfg.fov_punch_deg
	_streak = 1.0
	_overlay.visible = true
	Sfx.play_ui(&"kr5_fire", 0.0, 0.04)
	EventBus.shot_fired.emit(player, player.global_position, _dir)
	rumble(cfg.rumble_fire.x, cfg.rumble_fire.y, cfg.rumble_fire.z)
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(cfg.camera_kick_deg)


func _on_denied() -> void:
	Sfx.play_ui(&"kr5_denied", -6.0, 0.0)


func _on_active(_real: float) -> void:
	if not player.is_dashing():
		stop()


func _on_ram_hit(e: Enemy) -> void:
	var push: float = ram_push()
	var dmg: float = Player.slide_knock_damage(player.movement, push)
	var lethal: bool = dmg >= e.health
	var to: Vector3 = e.global_position - player.global_position
	to.y = 0.0
	var away: Vector3 = (_dir * 0.75 + (to.normalized() if to.length() > 0.05 else _dir) * 0.25).normalized()
	var at: Vector3 = e.global_position + Vector3.UP * 1.2
	e.knock_back(away * push + Vector3.UP * push * 0.3, player, dmg, cfg.morale_loss)
	struck += 1
	if not e.alive:
		kills += 1
	Sfx.play_at(&"impact_flesh", at, 4.0, 0.08)
	Sfx.play_ui(&"kr5_hit", -1.0, 0.06)
	Gore.spray(at, away, clampf(push / 7.0, 0.5, 2.5), 10 if lethal else 4)
	EventBus.slide_impact.emit(e, push)
	TimeControl.hitstop(0.07 if lethal else 0.04, 0.1)
	rumble(0.7, 1.0, 0.2)
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(Vector3(1.8, 0.0, 2.2 * (1.0 if to.cross(_dir).y > 0.0 else -1.0)))
	player._dash_vel *= cfg.speed_kept


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if _punch > 0.0 and player:
		_punch = maxf(0.0, _punch - (_punch * cfg.fov_recover + 2.0) * real)
		player.fov_punch_deg = _punch
	if _streak > 0.0:
		_streak = maxf(0.0, _streak - real / maxf(cfg.dash_time * 2.2, 0.05))
		(_overlay.material as ShaderMaterial).set_shader_parameter(&"amount", _streak)
		_overlay.visible = _streak > 0.0
