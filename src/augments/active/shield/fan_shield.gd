class_name FanShield
extends ActivePart
## BW-6 Bulwark Fan Shield (FanShieldData). The left forearm's leaves fan
## out (the deploy clip, scrubbed from the blend). While it's up, hits from
## the front go to Player.hit_interceptors -> _intercept(): the round is
## stopped, sparks fly, the arm jolts, and the shield's integrity (the
## charge) pays for it. Integrity scales with the skeleton (structure).

var cfg: FanShieldData
var rig: ArmRig
## Rounds stopped since it came up (tests, HUD).
var stopped: int = 0
var broken: bool = false

var _glow: StandardMaterial3D
var _flash: float = 0.0
var _break_left: float = 0.0


func _ready() -> void:
	super._ready()
	cfg = data as FanShieldData
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "FanShieldRig")
	if player == null:
		add_child(rig)
	rig.raise_drop = 0.4
	_glow = rig.drive("glow")
	if _glow:
		_glow.emission = cfg.glow_color
		_glow.emission_energy_multiplier = cfg.glow_idle
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	_release()
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()


func hand() -> StringName:
	return &"left"


func charge_capacity() -> float:
	if body == null:
		return data.charge_max
	var c: FanShieldData = data as FanShieldData
	return data.charge_max * clampf(body.stat(&"structure") / maxf(c.structure_ref, 0.1), 0.5, 2.0)


## Integrity isn't spent over time, only by what it stops.
func _drain(_real: float) -> void:
	pass


func offline_reason() -> String:
	var why: String = super.offline_reason()
	if why == "" and _break_left > 0.0:
		return "broken: %.0f s" % ceilf(_break_left)
	return why


func _on_start() -> void:
	stopped = 0
	broken = false
	rig.visible = true
	if player:
		if not player.hit_interceptors.has(_intercept):
			player.hit_interceptors.append(_intercept)
		player.aug_move_scale = cfg.move_scale
		if player.melee:
			player.melee.push_bonus = cfg.bash_bonus
	Sfx.play_ui(&"bw6_deploy", -2.0, 0.0)
	rumble(0.2, 0.4, 0.25)


func _on_stop() -> void:
	_release()
	Sfx.play_ui(&"bw6_stow", -4.0, 0.0)


func _release() -> void:
	if player and is_instance_valid(player):
		player.hit_interceptors.erase(_intercept)
		player.aug_move_scale = 1.0
		if player.melee:
			player.melee.push_bonus = 1.0


func _on_denied() -> void:
	Sfx.play_ui(&"gx4_dry", -8.0, 0.0)


func _on_state_changed(s: State) -> void:
	if s == State.COOLDOWN:
		rig.visible = false


func _on_blend(a: float) -> void:
	rig.seek(a)


## Whether a round travelling along `direction` would meet the shield.
func covers(direction: Vector3) -> bool:
	if state != State.ACTIVE and not (state == State.DEPLOYING and blend > 0.6):
		return false
	var fwd: Vector3 = -player.camera().global_basis.z
	return rad_to_deg(fwd.angle_to(-direction)) <= cfg.arc_deg


func _intercept(hit: BallisticHit, amount: float) -> float:
	if not covers(hit.direction):
		return amount
	stopped += 1
	charge -= hit.energy_in * 0.001 * cfg.loss_per_kj
	_flash = 1.0
	var cam: Camera3D = player.camera()
	var at: Vector3 = cam.global_position - hit.direction * 0.55 - cam.global_basis.x * 0.12
	Fx._emit(&"sparks", at, -hit.direction, Color(1.0, 0.8, 0.5, 1.0), 4, 1.0)
	Sfx.play_ui(&"bw6_hit", -2.0, 0.08)
	rig.kick_pos.kick(Vector3(0.0, 0.0, 0.035))
	rig.kick_rot.kick(Vector3(deg_to_rad(3.0), 0.0, deg_to_rad(randf_range(-2.0, 2.0))))
	rumble(0.5, 0.7, 0.1)
	if charge <= 0.0:
		charge = 0.0
		broken = true
		_break_left = cfg.break_cooldown
		Sfx.play_ui(&"bw6_break", 0.0, 0.0)
		rumble(1.0, 1.0, 0.35)
		stop()
	return amount * cfg.leak


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	_break_left = maxf(0.0, _break_left - real)
	if rig.visible:
		rig.tick(real, blend, player)
		_flash = maxf(0.0, _flash - real * 5.0)
		if _glow:
			var k: float = clampf(charge_fraction(), 0.0, 1.0)
			_glow.emission_energy_multiplier = lerpf(0.3, cfg.glow_idle, k) * blend + cfg.glow_hit * _flash * _flash
			_glow.emission = cfg.glow_color.lerp(Color(1.0, 0.2, 0.1), 1.0 - k)
