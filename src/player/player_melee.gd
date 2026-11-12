class_name PlayerMelee
extends Node
## R3 melee strike (CLAUDE.md §9.4). A short lunge, then a blow to the
## enemy nearest the centre of view within reach. How hard it lands comes
## from the body (docs/design.md §3.6): damage = config × melee_power ×
## usable strength; the shove = config × mass/100 × usable strength × impact
## (a heavy, strong, plated operative sends people flying, and past
## `lethal_push` breaks them); recovery ÷ melee_speed.

signal struck(target: Node, damage: float, push: float)

var player: Player
var cfg: MeleeConfig = preload("res://data/player/melee_default.tres")
## Seconds until the next strike can start.
var cooldown: float = 0.0
## Counting down to the blow landing (-1: no strike in progress).
var windup_left: float = -1.0
var _scripted: bool = false
## Multiplier on the shove from a running part (the fan shield: a shield bash).
var push_bonus: float = 1.0
## The first-person knife that plays the strike (null in bare tests without a camera).
var knife: KnifeViewmodel


func _ready() -> void:
	player = get_parent() as Player
	_make_knife.call_deferred()


func _make_knife() -> void:
	if player and cfg.knife_scene and player.camera() and cfg.knife_times.size() >= 2:
		knife = KnifeViewmodel.make(player, cfg)
		add_child(knife)


func _process(delta: float) -> void:
	if knife:
		knife.tick(delta * TimeControl.player_boost())


## 0..1: how far the gun is lowered out of the knife's way.
func gun_away() -> float:
	return knife.gun_away() if knife else 0.0


## Tests and demos: strike as if R3 was pressed.
func script_strike() -> void:
	_scripted = true


func damage() -> float:
	return cfg.damage * player.body.stat(&"melee_power") * player.body.usable_strength()


func push_speed() -> float:
	var b: BodyModel = player.body
	return cfg.push * (b.mass_kg / 100.0) * b.usable_strength() * b.stat(&"impact") * push_bonus


func recovery() -> float:
	return cfg.recovery / maxf(player.body.stat(&"melee_speed"), 0.1)


func _physics_process(delta: float) -> void:
	if player == null or player.body == null:
		return
	delta *= TimeControl.player_boost()
	cooldown -= delta
	var pressed: bool = _scripted or (player.input_enabled and not player.look_blocked and Input.is_action_just_pressed(&"melee"))
	_scripted = false
	if pressed and cooldown <= 0.0 and windup_left < 0.0 and not player.dead and not player.is_mantling():
		_start()
	if windup_left >= 0.0:
		windup_left -= delta
		var t: Enemy = target()
		if t and cfg.lunge_speed > 0.0:
			var to: Vector3 = t.global_position - player.global_position
			to.y = 0.0
			if to.length() > 1.0:
				var dir: Vector3 = to.normalized()
				var along: float = Vector3(player.velocity.x, 0.0, player.velocity.z).dot(dir)
				if along < cfg.lunge_speed:
					player.velocity += dir * (cfg.lunge_speed - along)
		if windup_left < 0.0:
			_land()


func _start() -> void:
	windup_left = cfg.windup / maxf(player.body.stat(&"melee_speed"), 0.1)
	cooldown = windup_left + recovery()
	player.stop_sprint()
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(cfg.windup_kick_deg)
	if knife:
		knife.play(player.body.stat(&"melee_speed"))
	Sfx.play_ui(&"mw7_swish", -7.0, 0.12)


## The living enemy the blow would land on, or null.
func target() -> Enemy:
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var best: Enemy = null
	var best_score: float = INF
	for n: Node in player.get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive:
			continue
		var at: Vector3 = e.global_position + Vector3.UP * 1.2
		var to: Vector3 = at - eye
		var d: float = to.length()
		if d > cfg.reach + 0.4:
			continue
		var ang: float = rad_to_deg(fwd.angle_to(to))
		if ang > cfg.cone_deg * 0.5 and d > 0.9:
			continue
		var score: float = ang + d * 10.0
		if score < best_score:
			best_score = score
			best = e
	return best


func _land() -> void:
	var e: Enemy = target()
	var cam: Camera3D = player.camera()
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(cfg.camera_kick_deg * (1.0 if e else 0.4))
	if e == null:
		return
	var dmg: float = damage()
	var push: float = push_speed()
	var dir: Vector3 = (e.global_position - player.global_position)
	dir.y = 0.0
	dir = dir.normalized() if dir.length() > 0.05 else -cam.global_basis.z
	var lethal: bool = push >= cfg.lethal_push or dmg >= e.health
	var hit_at: Vector3 = e.global_position + Vector3.UP * 1.3
	e.knock_back(dir * push + Vector3.UP * push * 0.3, player, 9999.0 if lethal else dmg, cfg.morale_loss)
	Sfx.play_at(&"impact_flesh", hit_at, 2.0, 0.08)
	Sfx.play_at(&"mw7_cut", hit_at, 0.0, 0.1)
	if knife:
		knife.cut(lethal)
	# The blood leaves along the slash: right to left across the view, a little down.
	var across: Vector3 = (-cam.global_basis.x - cam.global_basis.y * 0.35 + dir * 0.6).normalized()
	Gore.spray(hit_at, across, clampf(push / 8.0, 0.5, 2.0), 8 if lethal else 5)
	Gore.mist(hit_at, across, 1.0 if lethal else 0.6)
	TimeControl.hitstop(cfg.hitstop_time * (1.6 if lethal else 1.0), cfg.hitstop_scale)
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, cfg.rumble.x, cfg.rumble.y, cfg.rumble.z)
	EventBus.slide_impact.emit(e, push)
	struck.emit(e, dmg, push)
