class_name Player
extends CharacterBody3D
## First-person controller: controller look with shaped sticks and
## full-tilt acceleration; walk, sprint (L3), crouch (hold B), jump (A).
## Movement tech (M1b): B while sprinting slides (keeps momentum, A out of it
## hops); airborne against a wall at your side while pushing forward
## wall-runs (A jumps off); A at a ledge up to 2.2 m mantles onto it.
## Tuning lives in data/player/movement_default.tres.

@export var movement: MovementConfig = preload("res://data/player/movement_default.tres")
@export var body_config: PlayerBodyConfig = preload("res://data/player/body_default.tres")
## Installed parts (docs/design.md §3). The loadout screen replaces this in M2.
@export var loadout: BodyLoadout = preload("res://data/body/loadout_default.tres")
## The body as numbers: frame + parts (stats, mass, power, heat).
var body: BodyModel
## Active parts on LB/RB/D-pad up.
var augments: Augments
## R3 strike.
var melee: PlayerMelee
## Turned off while a benchmark or cutscene drives the camera.
@export var input_enabled: bool = true
## The weapon wheel is open: the right stick picks a gun instead of looking.
var look_blocked: bool = false
## An active part has the right stick (the whip with LT held): the view holds still.
var look_frozen: bool = false
## Which running part has each hand (&"right", &"left"). The gun needs both
## hands, so it's put away while either is taken.
var hands: Dictionary[StringName, Node] = {}
## Running parts that take hits before the body does (the fan shield):
## func(hit: BallisticHit, amount: float) -> float, the damage left.
var hit_interceptors: Array[Callable] = []
## Speed multiplier from running parts (the shield slows you).
var aug_move_scale: float = 1.0
## Suit and hardware colours (the loadout screen's Colours page).
var colors: BodyColors
signal colors_changed

signal landed(fall_speed: float)
signal damaged(amount: float, from_dir: Vector3)
signal died
signal respawned

var health: float = 200.0
var dead: bool = false
## Off in tests and benchmarks.
var invulnerable: bool = false
## 0..1, rises with near misses (HUD and camera react).
var suppression: float = 0.0
var spawn_point: Vector3 = Vector3.ZERO
var _since_hit: float = 99.0
var _dead_time: float = 0.0

## Set by the weapon each frame: aiming scales FOV, look speed and move speed.
var fov_scale: float = 1.0
var look_scale: float = 1.0
var move_scale: float = 1.0
## Degrees added to the field of view (time dilation widens it a touch).
var fov_add_deg: float = 0.0
## A shot's field-of-view punch (degrees; the arm cannon), and an extra zoom
## from an active part's own aiming (1 = none).
var fov_punch_deg: float = 0.0
## Blast shake (add_shake): strength 0..2 and its clock (real seconds).
var _shake: float = 0.0
var _shake_time: float = 0.0
var fov_extra_scale: float = 1.0
## Set by the weapon: carrying a heavy gun cuts sprint speed and jump height.
var sprint_scale: float = 1.0
var jump_scale: float = 1.0
## While true (aiming) a sprint can't start.
var sprint_blocked: bool = false
## While true (trigger held) full tilt doesn't start a sprint by itself.
var auto_sprint_blocked: bool = false
## Look speed in degrees per second: x = turning right, y = looking up.
var look_velocity: Vector2 = Vector2.ZERO
## Aim assist (set up by the level; null = off).
var aim_assist: AimAssist

const PITCH_LIMIT: float = deg_to_rad(88.0)

var yaw: float = 0.0
var pitch: float = 0.0

enum MoveState { NORMAL, SLIDE, WALLRUN, MANTLE }
var move_state: MoveState = MoveState.NORMAL
## +1 = the wall is on the right, -1 = left (while wall-running).
var wall_side: float = 0.0
var _wall_normal: Vector3 = Vector3.ZERO
var _last_wall_normal: Vector3 = Vector3.ZERO
var _wall_time: float = 0.0
var _wall_cd: float = 0.0
var _slide_cd: float = 0.0
var _mantle_from: Vector3
var _mantle_to: Vector3
var _mantle_t: float = 0.0
var _roll: float = 0.0
## Enemies already shoved during this slide (each only once).
var _slide_hit: Array[Node] = []

var _dash_vel: Vector3 = Vector3.ZERO
var _dash_left: float = 0.0
var _dash_on_hit: Callable = Callable()
var _dash_struck: Array[Node] = []

var _tilt_time: float = 0.0
var _sprinting: bool = false
var _crouching: bool = false
var _crouch_blend: float = 0.0
var _coyote: float = 0.0
var _jump_buffer: float = 0.0
var _capsule: CapsuleShape3D
var _last_yaw: float = 0.0
## Camera offset that eases out after stepping up or down a curb (m).
var _step_offset: float = 0.0
var _full_tilt_time: float = 0.0
var _last_pitch: float = 0.0
## Where the body was at the last two physics ticks: the camera is drawn
## between them (MovementConfig.camera_interpolation).
var _tick_prev: Vector3 = Vector3.ZERO
var _tick_now: Vector3 = Vector3.ZERO
## Camera offset this frame from interpolation (m, world; tests read it).
var camera_lag: Vector3 = Vector3.ZERO
## B pressed in the air: slide on touchdown if fast enough.
var _slide_buffer: float = 0.0
var _jump_held: bool = false
var _land_spring: Spring
var _move_fov: float = 0.0
var _strafe_roll: float = 0.0
## Wall-run entry: velocity swings onto the wall over a moment.
var _wall_entry_left: float = 0.0
var _wall_entry_speed: float = 0.0
var _mantle_exit_speed: float = 0.0

@onready var _head: Node3D = $Head
@onready var _camera: Camera3D = $Head/Camera3D
@onready var _collision: CollisionShape3D = $CollisionShape3D


func _ready() -> void:
	add_to_group(&"player")
	add_to_group(&"suppressible")
	set_meta(&"surface", &"flesh")
	set_meta(&"stops_rounds", true)
	# The default loadout is replaced by the one saved from the loadout screen;
	# either way the player edits a copy, never the resource on disk.
	if loadout.resource_path == LoadoutStore.DEFAULT_PATH:
		loadout = LoadoutStore.load_saved(loadout)
	else:
		loadout = loadout.copy()
	body = BodyModel.new(body_config, loadout)
	colors = LoadoutStore.load_colors()
	health = max_health()
	collision_layer = Ballistics.LAYER_PLAYER
	# Corpses and moving hitboxes don't block; living enemies do (their capsules).
	collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_ENEMY | Ballistics.LAYER_CLIP
	_capsule = (_collision.shape as CapsuleShape3D).duplicate() as CapsuleShape3D
	_collision.shape = _capsule
	yaw = rotation.y
	pitch = _head.rotation.x
	_camera.make_current()
	augments = Augments.new()
	augments.name = "Augments"
	add_child(augments)
	melee = PlayerMelee.new()
	melee.name = "Melee"
	add_child(melee)
	# Snap down curbs and stairs instead of flying off them; constant speed on slopes.
	floor_snap_length = movement.step_height + 0.05
	floor_constant_speed = true
	floor_max_angle = deg_to_rad(46.0)
	Settings.changed.connect(_on_settings_changed)
	_on_settings_changed()
	_repaint.call_deferred()
	_land_spring = Spring.new(movement.land_spring_hz, movement.land_spring_damping)
	_tick_prev = global_position
	_tick_now = global_position


## New colours from the loadout screen: repaint the arms and part models.
func set_colors(c: BodyColors) -> void:
	colors = c
	_repaint()
	colors_changed.emit()


func _repaint() -> void:
	if is_inside_tree():
		get_tree().call_group(&"suit_painted", &"repaint", colors)


func is_sprinting() -> bool:
	return _sprinting


func is_crouching() -> bool:
	return _crouching


func is_sliding() -> bool:
	return move_state == MoveState.SLIDE


func is_wallrunning() -> bool:
	return move_state == MoveState.WALLRUN


func is_mantling() -> bool:
	return move_state == MoveState.MANTLE


func camera() -> Camera3D:
	return _camera


func weapon() -> PlayerWeapon:
	return get_node_or_null(^"Weapon") as PlayerWeapon


## Enemy rounds land here (Ballistics hits the player's capsule).
func on_ballistic_hit(hit: BallisticHit) -> void:
	if dead or invulnerable or hit.shooter == self:
		return
	var amount: float = hit.energy_in * 0.001 * body.stat(&"damage_per_kj")
	for f: Callable in hit_interceptors:
		amount = f.call(hit, amount)
	if amount > 0.0:
		take_damage(amount, -hit.direction)


func take_damage(amount: float, from_dir: Vector3) -> void:
	if dead or invulnerable:
		return
	health -= amount
	_since_hit = 0.0
	damaged.emit(amount, from_dir)
	EventBus.player_damaged.emit(amount, from_dir)
	if health <= 0.0:
		health = 0.0
		dead = true
		_dead_time = 0.0
		input_enabled = false
		died.emit()
		EventBus.player_died.emit()


func suppress_point() -> Vector3:
	return _camera.global_position


## True if `side` (&"right" or &"left") isn't held by another part.
func hand_free(side: StringName, by: Node) -> bool:
	return not hands.has(side) or hands[side] == by or not is_instance_valid(hands[side])


## A part takes a hand; the gun goes down. False if another part has it.
func claim_hand(side: StringName, by: Node) -> bool:
	if not hand_free(side, by):
		return false
	hands[side] = by
	_update_hands()
	return true


func release_hand(side: StringName, by: Node) -> void:
	if hands.get(side) == by:
		hands.erase(side)
		_update_hands()


func _update_hands() -> void:
	var w: PlayerWeapon = weapon()
	if w == null:
		return
	if hands.is_empty():
		w.unstow()
		return
	w.stow()
	# The HUD shows the rounds of the part in the right hand, if there is one.
	var owner_part: Node = hands.get(&"right", hands.values()[0])
	w.stowed_by = owner_part as ActivePart


## Thrown forward by a part (the ram thrusters): `velocity` for `seconds`,
## no steering, no gravity; `on_hit` is called for each living enemy struck.
func start_dash(dash_velocity: Vector3, seconds: float, on_hit: Callable = Callable()) -> void:
	_dash_vel = dash_velocity
	_dash_left = seconds
	_dash_on_hit = on_hit
	_dash_struck.clear()
	move_state = MoveState.NORMAL
	_crouching = false


func is_dashing() -> bool:
	return _dash_left > 0.0


func on_near_miss(shooter: Node, _weapon: WeaponData, distance: float, point: Vector3) -> void:
	if shooter == self or dead:
		return
	suppression = minf(suppression + 0.25 * (1.0 - distance / Ballistics.NEAR_MISS_RADIUS), 1.0)
	Sfx.play_at(&"whizz", point, -2.0, 0.12)


func respawn() -> void:
	dead = false
	_dash_left = 0.0
	health = max_health()
	input_enabled = true
	suppression = 0.0
	global_position = spawn_point
	velocity = Vector3.ZERO
	reset_camera_smoothing()
	respawned.emit()


func health_fraction() -> float:
	return health / max_health()


func max_health() -> float:
	return body.stat(&"max_health") if body else body_config.max_health


func stop_sprint() -> void:
	_sprinting = false
	# Auto-sprint waits a moment after a shot before it kicks back in.
	_full_tilt_time = -0.25


## Camera recoil offset on top of the view, degrees: x = up, y = right, z = roll.
## The blast shake (add_shake) rides on top.
func set_camera_recoil(deg: Vector3) -> void:
	var d: Vector3 = deg + shake_offset()
	_camera.rotation = Vector3(deg_to_rad(d.x), -deg_to_rad(d.y), deg_to_rad(d.z))


## Shakes the view (a blast close by): `amount` 1 is a grenade at arm's
## length. Decays over about a second of real time.
func add_shake(amount: float) -> void:
	_shake = clampf(maxf(_shake, amount) + amount * 0.25, 0.0, 2.0)


## The shake's turn of the view now, degrees (pitch, yaw, roll).
func shake_offset() -> Vector3:
	if _shake <= 0.001:
		return Vector3.ZERO
	var t: float = _shake_time
	var k: float = _shake * _shake
	return Vector3(sin(t * 41.0) + 0.5 * sin(t * 67.0 + 1.3), sin(t * 37.0 + 2.1) + 0.5 * sin(t * 59.0),
			sin(t * 29.0 + 0.7)) * Vector3(2.4, 1.8, 1.6) * k


## The camera jumps with the body (after a teleport: spawn, respawn).
func reset_camera_smoothing() -> void:
	_tick_prev = global_position
	_tick_now = global_position
	camera_lag = Vector3.ZERO


## Sets the view directly (radians). Used by the benchmark and spawn points.
func set_view(new_yaw: float, new_pitch: float) -> void:
	yaw = new_yaw
	pitch = clampf(new_pitch, -PITCH_LIMIT, PITCH_LIMIT)
	_apply_view()


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled or look_blocked:
		return
	var motion: InputEventMouseMotion = event as InputEventMouseMotion
	if motion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var k: float = deg_to_rad(Settings.look_config().mouse_deg_per_pixel) * look_scale
		set_view(yaw - motion.relative.x * k, pitch - motion.relative.y * k)
	var click: InputEventMouseButton = event as InputEventMouseButton
	if click and click.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not CaptureDirector.is_capturing():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _process(delta: float) -> void:
	# Looking is a reflex: real time, whatever the world's time scale.
	var look_dt: float = TimeControl.real_delta(delta)
	if _shake > 0.0:
		_shake_time += look_dt
		_shake = maxf(0.0, _shake - look_dt * (0.6 + _shake * 1.6))
	if input_enabled and not look_blocked and not look_frozen:
		var look: LookConfig = Settings.look_config()
		var raw: Vector2 = Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.0)
		_tilt_time = _tilt_time + look_dt if look.is_full_tilt(raw) else 0.0
		var rate: Vector2 = look.look_rate(raw, _tilt_time) * look_scale * Settings.look_sensitivity
		if aim_assist:
			rate = aim_assist.apply(self, rate, look_dt)
		set_view(yaw - deg_to_rad(rate.x) * look_dt, pitch - deg_to_rad(rate.y) * look_dt)
	_update_crouch_pose(delta)
	var real_dt: float = TimeControl.real_delta(delta)
	var h_speed: float = Vector2(velocity.x, velocity.z).length()
	var fov_target: float = 0.0
	if move_state == MoveState.SLIDE:
		fov_target = movement.slide_fov_deg
	elif _sprinting or (not is_on_floor() and h_speed > movement.walk_speed):
		fov_target = movement.sprint_fov_deg * clampf((h_speed - movement.walk_speed) / maxf(movement.sprint_speed - movement.walk_speed, 0.1), 0.0, 1.0)
	_move_fov = lerpf(_move_fov, fov_target * fov_scale, 1.0 - exp(-movement.fov_smooth * real_dt))
	_camera.fov = Settings.vertical_fov * fov_scale * fov_extra_scale + fov_add_deg + fov_punch_deg + _move_fov
	if delta > 0.0:
		var measured: Vector2 = Vector2(-angle_difference(_last_yaw, yaw), angle_difference(_last_pitch, pitch)) / delta
		look_velocity = look_velocity.lerp(Vector2(rad_to_deg(measured.x), rad_to_deg(measured.y)), clampf(delta * 20.0, 0.0, 1.0))
	_last_yaw = yaw
	_last_pitch = pitch


func _physics_process(delta: float) -> void:
	# Time dilation: the player runs faster than the world (TimeControl).
	delta *= TimeControl.player_boost()
	# Moved since the last tick by something other than a tick (a spawn,
	# a respawn, a test or a cutscene putting the body somewhere): the
	# camera goes straight there instead of gliding.
	_tick_prev = _tick_now if global_position.is_equal_approx(_tick_now) else global_position
	_physics_body(delta)
	_tick_now = global_position


func _physics_body(delta: float) -> void:
	_since_hit += delta
	suppression = maxf(0.0, suppression - delta * 0.5)
	if dead:
		_dead_time += delta
		velocity = Vector3(0, velocity.y - movement.gravity * delta, 0) if not is_on_floor() else Vector3.ZERO
		_slide_move()
		return
	body.tick(delta)
	var can_regen: bool = not (body.frame.overheat_stops_regen and body.overheated())
	if can_regen and _since_hit > body.stat(&"regen_delay") and health < max_health():
		health = minf(health + body.stat(&"regen_rate") * delta, max_health())
	var cfg: MovementConfig = movement
	var stick: Vector2 = Vector2.ZERO
	if input_enabled:
		var raw: Vector2 = Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back", 0.0)
		stick = Stick.shape(raw, cfg.move_inner_deadzone, cfg.move_outer_deadzone, 1.0)
	var b_pressed: bool = input_enabled and Input.is_action_just_pressed(&"slide")
	var b_held: bool = input_enabled and Input.is_action_pressed(&"slide")
	_jump_buffer = cfg.jump_buffer if input_enabled and Input.is_action_just_pressed(&"jump") else _jump_buffer - delta
	_jump_held = input_enabled and Input.is_action_pressed(&"jump")
	_slide_buffer = cfg.slide_buffer if b_pressed and not is_on_floor() else _slide_buffer - delta
	_slide_cd -= delta
	_wall_cd -= delta
	var wish: Vector3 = global_basis * Vector3(stick.x, 0.0, stick.y)
	wish.y = 0.0
	var forward_push: float = -stick.y

	if _dash_left > 0.0:
		_dash(delta)
		return
	match move_state:
		MoveState.MANTLE:
			_mantle(delta)
			return
		MoveState.SLIDE:
			_slide(delta, wish, b_pressed, b_held, stick)
			return
		MoveState.WALLRUN:
			_wallrun(delta, forward_push)
			return

	# Sprint: press L3 to start; ends when the stick stops pushing forward.
	if input_enabled and Input.is_action_just_pressed(&"sprint") and not sprint_blocked:
		_sprinting = true
	if forward_push < cfg.auto_sprint_tilt or auto_sprint_blocked:
		_full_tilt_time = minf(_full_tilt_time, 0.0)
	else:
		_full_tilt_time += delta
	if cfg.auto_sprint and _full_tilt_time >= cfg.auto_sprint_delay and not sprint_blocked and is_on_floor():
		_sprinting = true
	if not cfg.sprint_holds(stick):
		_sprinting = false
	var horizontal: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	# Slide: B at speed on the ground (or B just before touching down).
	var slide_now: bool = b_pressed or (_slide_buffer > 0.0 and b_held)
	if slide_now and is_on_floor() and horizontal.length() >= cfg.slide_min_speed * 0.9 and _slide_cd <= 0.0:
		_slide_buffer = 0.0
		_start_slide(horizontal)
		return
	_crouching = b_held
	if _crouching or sprint_blocked:
		_sprinting = false
	var speed: float = cfg.walk_speed
	if _sprinting:
		speed = cfg.sprint_speed * sprint_scale
	elif _crouching:
		speed = cfg.crouch_speed
	speed *= move_scale * aug_move_scale * speed_factor()
	var agility: float = body.stat(&"agility")
	if is_on_floor():
		# Momentum above a full sprint carries; anything slower (aiming,
		# crouching, the shield) brakes normally.
		var carry: float = cfg.sprint_speed * sprint_scale * aug_move_scale * speed_factor()
		horizontal = cfg.ground_step(horizontal, wish, speed, agility, delta, carry)
	else:
		horizontal = cfg.air_step(horizontal, wish, maxf(speed, cfg.walk_speed * move_scale * aug_move_scale * speed_factor()), agility, delta)

	_coyote = cfg.coyote_time if is_on_floor() else _coyote - delta
	var vy: float = velocity.y
	if not is_on_floor():
		vy = maxf(vy - cfg.gravity * cfg.gravity_scale(vy, _jump_held) * delta, -cfg.max_fall_speed)
	# A at a ledge climbs it (from the ground or in the air).
	if _jump_buffer > 0.0 and forward_push > 0.2 and _try_mantle():
		_jump_buffer = 0.0
		return
	if _jump_buffer > 0.0 and _coyote > 0.0:
		vy = jump_velocity()
		_jump_buffer = 0.0
		_coyote = 0.0
	velocity = Vector3(horizontal.x, vy, horizontal.z)
	var was_on_floor: bool = is_on_floor()
	_move_with_steps(delta, was_on_floor)
	if is_on_floor():
		_last_wall_normal = Vector3.ZERO
	if is_on_floor() and not was_on_floor and vy < -1.0:
		_on_landed(-vy)
	# Airborne next to a wall, pushing forward at speed: run along it.
	if not is_on_floor() and forward_push > 0.5 and _wall_cd <= 0.0 and horizontal.length() >= cfg.wallrun_min_speed and wallrun_time() > 0.05:
		_try_wallrun(horizontal)


func _on_landed(fall_speed: float) -> void:
	landed.emit(fall_speed)
	_land_spring.kick(Vector3(0.0, -minf(fall_speed * movement.land_dip_per_mps, movement.land_dip_max), 0.0))


## A thruster dash: straight along _dash_vel; living enemies in the way are
## reported to the part that started it. Ends early against a wall.
func _dash(delta: float) -> void:
	_dash_left -= delta
	velocity = _dash_vel
	_sprinting = false
	var before: Vector3 = global_position
	_slide_move()
	var moved: float = (global_position - before).length()
	var dir: Vector3 = _dash_vel.normalized()
	if _dash_on_hit.is_valid():
		for n: Node in get_tree().get_nodes_in_group(&"enemies"):
			var e: Enemy = n as Enemy
			if e == null or not e.alive or n in _dash_struck:
				continue
			var to: Vector3 = e.global_position + Vector3.UP * 0.9 - (global_position + Vector3.UP * 0.9)
			if to.length() < 1.5 and (to.length() < 0.6 or to.normalized().dot(dir) > 0.1):
				_dash_struck.append(n)
				_dash_on_hit.call(e)
	if moved < _dash_vel.length() * delta * 0.25 * TimeControl.player_boost():
		_dash_left = 0.0
	if _dash_left <= 0.0:
		# Come out of it running, not flying.
		var h: Vector3 = Vector3(_dash_vel.x, 0.0, _dash_vel.z)
		velocity = h.normalized() * minf(h.length(), movement.sprint_speed * 1.2) + Vector3.UP * minf(velocity.y, 2.0)


## move_and_slide, plus walking up steps up to step_height (curbs, sills,
## stair treads) and easing the camera over steps up and down.
func _move_with_steps(delta: float, was_on_floor: bool) -> void:
	var before: Transform3D = global_transform
	var keep: Vector3 = velocity
	var want: Vector3 = Vector3(velocity.x, 0.0, velocity.z) * delta
	_slide_move()
	var after: Vector3 = global_position
	var moved: Vector3 = Vector3(after.x - before.origin.x, 0.0, after.z - before.origin.z)
	# On the ground, or coming down onto a lip (landing on a curb shouldn't snag).
	if (was_on_floor or keep.y <= 0.0) and velocity.y <= 0.5 and want.length() > 0.001 and is_on_wall() and moved.length() < want.length() * 0.7:
		var stepped: Vector3 = _step_up(before, want)
		if stepped != Vector3.INF:
			_step_offset -= stepped.y - before.origin.y
			global_position = stepped
			# The curb didn't stop you: keep the speed you had.
			velocity = Vector3(keep.x, 0.0, keep.z)
			apply_floor_snap()
			return
	# Stepping down a curb on foot: ease the camera down too.
	if was_on_floor and is_on_floor():
		var drop: float = before.origin.y - global_position.y
		if drop > 0.04 and drop <= movement.step_height + 0.06:
			_step_offset += drop


## Where the body ends up if it lifts by step_height, moves `want`, and drops
## back onto walkable ground; Vector3.INF if it can't (wall too tall, ceiling,
## no floor there).
func _step_up(from: Transform3D, want: Vector3) -> Vector3:
	var up: Vector3 = Vector3.UP * movement.step_height
	if test_move(from, up):
		return Vector3.INF
	var fwd: Vector3 = want
	if fwd.length() < 0.06:
		fwd = fwd.normalized() * 0.06  # enough to get the capsule over a sill
	var raised: Transform3D = from.translated(up)
	if test_move(raised, fwd):
		return Vector3.INF
	var over: Transform3D = raised.translated(fwd)
	var hit: KinematicCollision3D = KinematicCollision3D.new()
	if not test_move(over, -up - Vector3.UP * 0.05, hit):
		return Vector3.INF
	if hit.get_normal().angle_to(Vector3.UP) > floor_max_angle:
		return Vector3.INF
	var land: Vector3 = over.origin + hit.get_travel()
	if land.y - from.origin.y < 0.02:
		return Vector3.INF
	return land


## move_and_slide in the player's own time: while the world is dilated the
## player covers player_boost() times more ground per world second.
func _slide_move() -> void:
	var boost: float = TimeControl.player_boost()
	if is_equal_approx(boost, 1.0):
		move_and_slide()
		return
	velocity *= boost
	move_and_slide()
	velocity /= boost


func _start_slide(horizontal: Vector3) -> void:
	var cfg: MovementConfig = movement
	move_state = MoveState.SLIDE
	_sprinting = false
	_crouching = true
	var slide: float = body.stat(&"slide")
	var speed: float = minf(horizontal.length() + cfg.slide_boost * slide, cfg.slide_max_speed * sqrt(slide))
	var h: Vector3 = horizontal.normalized() * speed
	velocity = Vector3(h.x, velocity.y, h.z)
	_slide_hit.clear()
	Sfx.play_ui(&"slide", -6.0, 0.05)


func _slide(delta: float, wish: Vector3, b_pressed: bool, b_held: bool, stick: Vector2) -> void:
	var cfg: MovementConfig = movement
	_crouching = true
	var h: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	var speed: float = maxf(0.0, h.length() - cfg.slide_friction / maxf(body.stat(&"slide"), 0.1) * delta)
	if is_on_floor() and h.length() > 0.1:
		# Downhill pulls the slide along; uphill slows it.
		var n: Vector3 = get_floor_normal()
		var downhill: Vector3 = Vector3(n.x, 0.0, n.z)
		speed = maxf(0.0, speed + downhill.dot(h.normalized()) * cfg.gravity * cfg.slide_slope_accel * delta)
	var dir: Vector3 = h.normalized() if h.length() > 0.01 else -global_basis.z
	# A little steering with the stick.
	if wish.length() > 0.2:
		var ang: float = dir.signed_angle_to(wish.normalized(), Vector3.UP)
		var steer: float = cfg.slide_steer * body.stat(&"agility")
		dir = dir.rotated(Vector3.UP, clampf(ang, -steer * delta, steer * delta))
	h = dir * speed
	var vy: float = velocity.y - cfg.gravity * delta if not is_on_floor() else -1.0
	if _jump_buffer > 0.0:
		# Slide-hop: keep the speed, jump out of it.
		_jump_buffer = 0.0
		move_state = MoveState.NORMAL
		_crouching = false
		_slide_cd = cfg.slide_cooldown
		velocity = Vector3(h.x, jump_velocity(), h.z)
		_slide_move()
		return
	velocity = Vector3(h.x, vy, h.z)
	_move_with_steps(delta, is_on_floor())
	_slide_knock(dir, speed)
	var released: bool = not b_held if cfg.slide_hold else b_pressed
	var braked: bool = stick.y > cfg.slide_brake_stick
	if speed <= cfg.slide_end_speed or released or braked or not is_on_floor():
		move_state = MoveState.NORMAL
		_slide_cd = cfg.slide_cooldown
		_crouching = b_held and is_on_floor() and not b_pressed


## Sliding into a living enemy: shove him along the slide, stagger him, lose
## a little speed. Strength scales with the body's mass and `strength` stat.
func _slide_knock(dir: Vector3, speed: float) -> void:
	var cfg: MovementConfig = movement
	if speed < cfg.slide_knock_min_speed:
		return
	var me: Vector3 = global_position
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Enemy = n as Enemy
		if e == null or not e.alive or n in _slide_hit:
			continue
		var to: Vector3 = e.global_position - me
		if absf(to.y) > 1.2:
			continue
		to.y = 0.0
		if to.length() > cfg.slide_knock_reach or (to.length() > 0.2 and to.normalized().dot(dir) < 0.15):
			continue
		_slide_hit.append(n)
		var push: float = slide_knock_strength(cfg, body.mass_kg, body.usable_strength() * body.stat(&"impact"), speed)
		# Mostly along the slide, partly away from the line of contact.
		var away: Vector3 = (dir * 0.7 + to.normalized() * 0.3).normalized() if to.length() > 0.05 else dir
		var dmg: float = slide_knock_damage(cfg, push)
		e.knock_back(away * push + Vector3.UP * push * 0.25, self, dmg, cfg.slide_knock_morale)
		var keep: float = 1.0 - cfg.slide_knock_speed_loss
		velocity.x *= keep
		velocity.z *= keep
		EventBus.slide_impact.emit(e, push)
		# Feel it: a hard thump in the pads and a short hit-stop.
		TimeControl.hitstop(0.05, 0.1)
		for pad: int in Input.get_connected_joypads():
			Input.start_joy_vibration(pad, 0.6, 0.9, 0.16)
		var w: PlayerWeapon = weapon()
		if w and w.cam_recoil:
			w.cam_recoil.kick(Vector3(-1.2, 0.0, 2.0 * signf(to.x if absf(to.x) > 0.01 else 1.0)))


## Speed (m/s) a slide gives the enemy it hits: momentum of the operative
## (mass × slide speed) × strength × impact (docs/design.md §3.6).
static func slide_knock_strength(cfg: MovementConfig, mass_kg: float, strength: float, speed: float) -> float:
	return cfg.slide_knock_speed * (mass_kg / 100.0) * strength * clampf(speed / cfg.slide_knock_ref_speed, 0.5, 1.4)


## Damage of a slide hit: grows with the square of the shove (energy). At
## slide_knock_lethal_speed and above it breaks the body (lethal).
static func slide_knock_damage(cfg: MovementConfig, push: float) -> float:
	if push >= cfg.slide_knock_lethal_speed:
		return 9999.0
	var k: float = push / maxf(cfg.slide_knock_speed, 0.1)
	return cfg.slide_knock_damage * k * k


## What the body does to ground speed: the move_speed stat × the load.
func speed_factor() -> float:
	return body.stat(&"move_speed") * body.load_scale()


## Jump take-off speed: jump height scales with the jump stat and the load.
func jump_velocity() -> float:
	return movement.jump_velocity * jump_scale * sqrt(body.stat(&"jump") * body.load_scale())


## How long a wall-run lasts (0: the body can't wall-run, e.g. the DL-1 frame).
func wallrun_time() -> float:
	return movement.wallrun_time * body.stat(&"wallrun") * body.load_scale()


## 0..1+ how much noise the operative makes moving (enemies hear it):
## speed relative to a sprint × the noise stat; crouching is quieter.
func noise_level() -> float:
	if dead:
		return 0.0
	var h: float = Vector3(velocity.x, 0.0, velocity.z).length()
	var n: float = clampf(h / movement.sprint_speed, 0.0, 1.5)
	if _crouching and move_state != MoveState.SLIDE:
		n *= 0.4
	if not is_on_floor() and move_state != MoveState.WALLRUN:
		n *= 0.3
	return n * body.stat(&"noise")


## Rebuilds everything that depends on the body after the loadout changed
## (the loadout screen): stats, actives, health kept in proportion.
func apply_loadout(lo: BodyLoadout) -> void:
	var frac: float = health_fraction()
	loadout = lo
	body.loadout = lo
	body.rebuild()
	health = max_health() * frac
	if augments:
		augments.rebuild()


func _side_wall() -> Dictionary:
	var cfg: MovementConfig = movement
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var from: Vector3 = global_position + Vector3.UP * 1.0
	var right: Vector3 = global_basis.x
	for side: float in [1.0, -1.0]:
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, from + right * side * (_capsule.radius + cfg.wallrun_detect), Ballistics.LAYER_WORLD)
		var res: Dictionary = space.intersect_ray(q)
		if not res.is_empty():
			var n: Vector3 = res["normal"]
			if absf(n.y) < 0.3:
				res["side"] = side
				return res
	return {}


func _try_wallrun(horizontal: Vector3) -> void:
	var res: Dictionary = _side_wall()
	if res.is_empty():
		return
	var n: Vector3 = res["normal"]
	if _last_wall_normal != Vector3.ZERO and n.dot(_last_wall_normal) > 0.9:
		return  # same wall again: touch the floor or another wall first
	move_state = MoveState.WALLRUN
	_wall_normal = Vector3(n.x, 0.0, n.z).normalized()
	wall_side = res["side"]
	_wall_time = 0.0
	_sprinting = false
	var t: Vector3 = _wall_normal.cross(Vector3.UP)
	if t.dot(horizontal) < 0.0:
		t = -t
	_wall_entry_speed = maxf(horizontal.length(), movement.wallrun_speed)
	_wall_entry_left = movement.wallrun_entry_time
	# Swing onto the wall over a moment (see _wallrun) instead of snapping.
	velocity = velocity.lerp(t * _wall_entry_speed, 0.35)
	velocity.y = maxf(velocity.y, 1.5)


func _wallrun(delta: float, forward_push: float) -> void:
	var cfg: MovementConfig = movement
	_wall_time += delta
	var res: Dictionary = _side_wall()
	var run_time: float = wallrun_time()
	var off: bool = res.is_empty() or forward_push < 0.3 or _wall_time > run_time or is_on_floor()
	if _jump_buffer > 0.0:
		# Jump off the wall: away from it, up, and on along it.
		_jump_buffer = 0.0
		var h: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
		velocity = h * 0.9 + _wall_normal * cfg.wallrun_jump_out + Vector3.UP * cfg.wallrun_jump_up * jump_scale * sqrt(body.stat(&"jump") * body.load_scale())
		_end_wallrun()
		_slide_move()
		return
	if off:
		_end_wallrun()
		_slide_move()
		return
	var wn: Vector3 = res["normal"]
	_wall_normal = Vector3(wn.x, 0.0, wn.z).normalized()
	var t: Vector3 = _wall_normal.cross(Vector3.UP)
	var h2: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	if t.dot(h2) < 0.0:
		t = -t
	var k: float = clampf(_wall_time / maxf(run_time, 0.05), 0.0, 1.0)
	var g: float = cfg.gravity * lerpf(cfg.wallrun_gravity_scale, 1.0, k * k)
	var vy: float = velocity.y - g * delta
	var speed: float = maxf(h2.length(), cfg.wallrun_speed * move_scale)
	var along: Vector3 = t * speed
	if _wall_entry_left > 0.0:
		_wall_entry_left -= delta
		var k2: float = clampf(delta / maxf(_wall_entry_left + delta, 0.001), 0.0, 1.0)
		along = h2.lerp(t * maxf(_wall_entry_speed, speed), k2)
	# Hug the wall a little so small gaps don't drop you.
	velocity = along - _wall_normal * 0.8 + Vector3.UP * vy
	_slide_move()


func _end_wallrun() -> void:
	move_state = MoveState.NORMAL
	_last_wall_normal = _wall_normal
	_wall_cd = movement.wallrun_cooldown
	wall_side = 0.0


func _try_mantle() -> bool:
	var cfg: MovementConfig = movement
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var fwd: Vector3 = -global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	var feet: Vector3 = global_position
	var wall: Dictionary = {}
	for h: float in [0.5, 1.1, 1.7]:
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(feet + Vector3.UP * h, feet + Vector3.UP * h + fwd * (_capsule.radius + cfg.mantle_reach), Ballistics.LAYER_WORLD)
		wall = space.intersect_ray(q)
		if not wall.is_empty():
			break
	if wall.is_empty():
		return false
	var wall_at: Vector3 = wall["position"]
	var max_h: float = cfg.mantle_max_height * body.stat(&"climb")
	var probe: Vector3 = Vector3(wall_at.x, feet.y + max_h + 0.3, wall_at.z) + fwd * 0.4
	var down: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(probe, Vector3(probe.x, feet.y + cfg.mantle_min_height - 0.05, probe.z), Ballistics.LAYER_WORLD)
	var top: Dictionary = space.intersect_ray(down)
	if top.is_empty():
		return false
	var top_at: Vector3 = top["position"]
	var top_n: Vector3 = top["normal"]
	var height: float = top_at.y - feet.y
	if top_n.y < 0.7 or height < cfg.mantle_min_height or height > max_h:
		return false
	# Room to stand up there?
	var shape: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	var cap: CapsuleShape3D = CapsuleShape3D.new()
	cap.radius = _capsule.radius * 0.9
	cap.height = cfg.stand_height * 0.95
	shape.shape = cap
	shape.transform = Transform3D(Basis(), top_at + Vector3.UP * (cfg.stand_height * 0.5 + 0.06))
	shape.collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS
	if not space.intersect_shape(shape, 1).is_empty():
		return false
	move_state = MoveState.MANTLE
	_mantle_from = global_position
	_mantle_to = top_at + Vector3.UP * 0.02
	_mantle_t = 0.0
	_mantle_exit_speed = maxf(Vector2(velocity.x, velocity.z).length() * cfg.mantle_keep_speed, 3.0)
	_sprinting = false
	velocity = Vector3.ZERO
	Sfx.play_ui(&"mantle", -6.0, 0.05)
	return true


func _mantle(delta: float) -> void:
	var cfg: MovementConfig = movement
	var height: float = maxf(_mantle_to.y - _mantle_from.y, 0.1)
	var vault: float = clampf(_mantle_exit_speed / maxf(cfg.sprint_speed, 0.1), 0.6, 1.25)
	_mantle_t = minf(_mantle_t + delta * body.stat(&"agility") * vault / (cfg.mantle_time * (0.7 + 0.3 * height / cfg.mantle_max_height)), 1.0)
	# Up first, then over the edge.
	var up: float = clampf(_mantle_t / 0.65, 0.0, 1.0)
	var over: float = clampf((_mantle_t - 0.45) / 0.55, 0.0, 1.0)
	up = 1.0 - (1.0 - up) * (1.0 - up)
	over = over * over * (3.0 - 2.0 * over)
	var p: Vector3 = _mantle_from.lerp(Vector3(_mantle_to.x, _mantle_from.y, _mantle_to.z), over)
	p.y = lerpf(_mantle_from.y, _mantle_to.y, up)
	global_position = p
	if _mantle_t >= 1.0:
		move_state = MoveState.NORMAL
		var fwd: Vector3 = -global_basis.z
		fwd = Vector3(fwd.x, 0.0, fwd.z).normalized()
		# Come over the top still moving: a vault at a run, a climb from a stand.
		velocity = fwd * _mantle_exit_speed
		_sprinting = _mantle_exit_speed > cfg.walk_speed


func _apply_view() -> void:
	rotation.y = yaw
	_head.rotation.x = pitch


func _update_crouch_pose(delta: float) -> void:
	var cfg: MovementConfig = movement
	var target: float = 1.0 if _crouching else 0.0
	# Camera roll: into the slide a little, away from the wall on a wall-run.
	var roll: float = 0.0
	if move_state == MoveState.SLIDE:
		roll = deg_to_rad(cfg.slide_tilt_deg)
	elif move_state == MoveState.WALLRUN:
		roll = deg_to_rad(cfg.wallrun_tilt_deg) * wall_side
	# A slight lean into a strafe.
	var side: float = velocity.dot(global_basis.x) / maxf(cfg.sprint_speed, 0.1)
	var strafe: float = -deg_to_rad(cfg.strafe_roll_deg) * clampf(side, -1.0, 1.0) if move_state == MoveState.NORMAL and is_on_floor() else 0.0
	_strafe_roll = lerpf(_strafe_roll, strafe, 1.0 - exp(-6.0 * delta))
	_roll = lerpf(_roll, roll, 1.0 - exp(-9.0 * delta))
	_head.rotation.z = _roll + _strafe_roll
	_crouch_blend = move_toward(_crouch_blend, target, cfg.crouch_transition_speed * delta)
	# Eased in and out (smoothstep), so the camera doesn't drop at a constant rate.
	var ease_c: float = _crouch_blend * _crouch_blend * (3.0 - 2.0 * _crouch_blend)
	var height: float = lerpf(cfg.stand_height, cfg.crouch_height, _crouch_blend)
	_capsule.height = height
	_collision.position.y = height * 0.5
	_step_offset = lerpf(_step_offset, 0.0, 1.0 - exp(-cfg.step_smooth * delta))
	_land_spring.step(delta)
	# Draw the camera between the last two physics ticks.
	camera_lag = Vector3.ZERO
	if cfg.camera_interpolation and not dead:
		var f: float = clampf(Engine.get_physics_interpolation_fraction(), 0.0, 1.0)
		camera_lag = _tick_prev.lerp(_tick_now, f) - global_position
		if camera_lag.length() > 1.0 or not global_position.is_equal_approx(_tick_now):
			camera_lag = Vector3.ZERO  # teleported this frame
	var local_lag: Vector3 = global_basis.inverse() * camera_lag
	_head.position = Vector3(local_lag.x, lerpf(cfg.stand_eye_height, cfg.crouch_eye_height, ease_c) + _step_offset + _land_spring.value.y + local_lag.y, local_lag.z)


func _on_settings_changed() -> void:
	_camera.fov = Settings.vertical_fov * fov_scale
