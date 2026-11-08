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
## Turned off while a benchmark or cutscene drives the camera.
@export var input_enabled: bool = true
## The weapon wheel is open: the right stick picks a gun instead of looking.
var look_blocked: bool = false

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

@onready var _head: Node3D = $Head
@onready var _camera: Camera3D = $Head/Camera3D
@onready var _collision: CollisionShape3D = $CollisionShape3D


func _ready() -> void:
	add_to_group(&"player")
	add_to_group(&"suppressible")
	set_meta(&"surface", &"flesh")
	set_meta(&"stops_rounds", true)
	body = BodyModel.new(body_config, loadout)
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
	# Snap down curbs and stairs instead of flying off them; constant speed on slopes.
	floor_snap_length = movement.step_height + 0.05
	floor_constant_speed = true
	floor_max_angle = deg_to_rad(46.0)
	Settings.changed.connect(_on_settings_changed)
	_on_settings_changed()


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


func on_near_miss(shooter: Node, _weapon: WeaponData, distance: float, point: Vector3) -> void:
	if shooter == self or dead:
		return
	suppression = minf(suppression + 0.25 * (1.0 - distance / Ballistics.NEAR_MISS_RADIUS), 1.0)
	Sfx.play_at(&"whizz", point, -2.0, 0.12)


func respawn() -> void:
	dead = false
	health = max_health()
	input_enabled = true
	suppression = 0.0
	global_position = spawn_point
	velocity = Vector3.ZERO
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
func set_camera_recoil(deg: Vector3) -> void:
	_camera.rotation = Vector3(deg_to_rad(deg.x), -deg_to_rad(deg.y), deg_to_rad(deg.z))


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
	if input_enabled and not look_blocked:
		var look: LookConfig = Settings.look_config()
		var raw: Vector2 = Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.0)
		_tilt_time = _tilt_time + look_dt if look.is_full_tilt(raw) else 0.0
		var rate: Vector2 = look.look_rate(raw, _tilt_time) * look_scale * Settings.look_sensitivity
		if aim_assist:
			rate = aim_assist.apply(self, rate, look_dt)
		set_view(yaw - deg_to_rad(rate.x) * look_dt, pitch - deg_to_rad(rate.y) * look_dt)
	_update_crouch_pose(delta)
	_camera.fov = Settings.vertical_fov * fov_scale * fov_extra_scale + fov_add_deg + fov_punch_deg
	if delta > 0.0:
		var measured: Vector2 = Vector2(-angle_difference(_last_yaw, yaw), angle_difference(_last_pitch, pitch)) / delta
		look_velocity = look_velocity.lerp(Vector2(rad_to_deg(measured.x), rad_to_deg(measured.y)), clampf(delta * 20.0, 0.0, 1.0))
	_last_yaw = yaw
	_last_pitch = pitch


func _physics_process(delta: float) -> void:
	# Time dilation: the player runs faster than the world (TimeControl).
	delta *= TimeControl.player_boost()
	_since_hit += delta
	suppression = maxf(0.0, suppression - delta * 0.5)
	if dead:
		_dead_time += delta
		velocity = Vector3(0, velocity.y - movement.gravity * delta, 0) if not is_on_floor() else Vector3.ZERO
		_slide_move()
		return
	body.tick(delta)
	if _since_hit > body.stat(&"regen_delay") and health < max_health():
		health = minf(health + body.stat(&"regen_rate") * delta, max_health())
	var cfg: MovementConfig = movement
	var stick: Vector2 = Vector2.ZERO
	if input_enabled:
		var raw: Vector2 = Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back", 0.0)
		stick = Stick.shape(raw, cfg.move_inner_deadzone, cfg.move_outer_deadzone, 1.0)
	var b_pressed: bool = input_enabled and Input.is_action_just_pressed(&"slide")
	var b_held: bool = input_enabled and Input.is_action_pressed(&"slide")
	_jump_buffer = cfg.jump_buffer if input_enabled and Input.is_action_just_pressed(&"jump") else _jump_buffer - delta
	_slide_cd -= delta
	_wall_cd -= delta
	var wish: Vector3 = global_basis * Vector3(stick.x, 0.0, stick.y)
	wish.y = 0.0
	var forward_push: float = -stick.y

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
	if forward_push < cfg.sprint_min_forward:
		_sprinting = false
	var horizontal: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	# Slide: B at speed on the ground.
	if b_pressed and is_on_floor() and horizontal.length() >= cfg.slide_min_speed * 0.9 and _slide_cd <= 0.0:
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
	speed *= move_scale * body.stat(&"move_speed")
	if is_on_floor():
		horizontal = MovementConfig.approach(horizontal, wish * speed, cfg.ground_accel, cfg.ground_decel, delta)
	else:
		horizontal = MovementConfig.approach(horizontal, wish * speed, cfg.air_accel, cfg.air_accel * 0.25, delta)

	_coyote = cfg.coyote_time if is_on_floor() else _coyote - delta
	var vy: float = velocity.y
	if not is_on_floor():
		vy -= cfg.gravity * delta
	# A at a ledge climbs it (from the ground or in the air).
	if _jump_buffer > 0.0 and forward_push > 0.2 and _try_mantle():
		_jump_buffer = 0.0
		return
	if _jump_buffer > 0.0 and _coyote > 0.0:
		vy = cfg.jump_velocity * jump_scale * sqrt(body.stat(&"jump"))
		_jump_buffer = 0.0
		_coyote = 0.0
	velocity = Vector3(horizontal.x, vy, horizontal.z)
	var was_on_floor: bool = is_on_floor()
	_move_with_steps(delta, was_on_floor)
	if is_on_floor():
		_last_wall_normal = Vector3.ZERO
	if is_on_floor() and not was_on_floor and vy < -1.0:
		landed.emit(-vy)
	# Airborne next to a wall, pushing forward at speed: run along it.
	if not is_on_floor() and forward_push > 0.5 and _wall_cd <= 0.0 and horizontal.length() >= cfg.wallrun_min_speed:
		_try_wallrun(horizontal)


## move_and_slide, plus walking up steps up to step_height (curbs, sills,
## stair treads) and easing the camera over steps up and down.
func _move_with_steps(delta: float, was_on_floor: bool) -> void:
	var before: Transform3D = global_transform
	var keep: Vector3 = velocity
	var want: Vector3 = Vector3(velocity.x, 0.0, velocity.z) * delta
	_slide_move()
	var after: Vector3 = global_position
	var moved: Vector3 = Vector3(after.x - before.origin.x, 0.0, after.z - before.origin.z)
	if was_on_floor and velocity.y <= 0.5 and want.length() > 0.001 and is_on_wall() and moved.length() < want.length() * 0.7:
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
	var speed: float = minf(horizontal.length() + cfg.slide_boost, cfg.slide_max_speed)
	var h: Vector3 = horizontal.normalized() * speed
	velocity = Vector3(h.x, velocity.y, h.z)
	_slide_hit.clear()
	Sfx.play_ui(&"slide", -6.0, 0.05)


func _slide(delta: float, wish: Vector3, b_pressed: bool, b_held: bool, stick: Vector2) -> void:
	var cfg: MovementConfig = movement
	_crouching = true
	var h: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	var speed: float = maxf(0.0, h.length() - cfg.slide_friction * delta)
	var dir: Vector3 = h.normalized() if h.length() > 0.01 else -global_basis.z
	# A little steering with the stick.
	if wish.length() > 0.2:
		var ang: float = dir.signed_angle_to(wish.normalized(), Vector3.UP)
		dir = dir.rotated(Vector3.UP, clampf(ang, -cfg.slide_steer * delta, cfg.slide_steer * delta))
	h = dir * speed
	var vy: float = velocity.y - cfg.gravity * delta if not is_on_floor() else -1.0
	if _jump_buffer > 0.0:
		# Slide-hop: keep the speed, jump out of it.
		_jump_buffer = 0.0
		move_state = MoveState.NORMAL
		_crouching = false
		_slide_cd = cfg.slide_cooldown
		velocity = Vector3(h.x, cfg.jump_velocity * jump_scale, h.z)
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
		var push: float = slide_knock_strength(cfg, body.mass_kg, body.stat(&"strength"), speed)
		# Mostly along the slide, partly away from the line of contact.
		var away: Vector3 = (dir * 0.7 + to.normalized() * 0.3).normalized() if to.length() > 0.05 else dir
		e.knock_back(away * push + Vector3.UP * push * 0.25, self, cfg.slide_knock_damage, cfg.slide_knock_morale)
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


static func slide_knock_strength(cfg: MovementConfig, mass_kg: float, strength: float, speed: float) -> float:
	return cfg.slide_knock_speed * (mass_kg / 100.0) * strength * clampf(speed / cfg.slide_knock_ref_speed, 0.5, 1.4)


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
	var speed: float = maxf(horizontal.length(), movement.wallrun_speed)
	velocity = t * speed + Vector3.UP * maxf(velocity.y, 1.5)


func _wallrun(delta: float, forward_push: float) -> void:
	var cfg: MovementConfig = movement
	_wall_time += delta
	var res: Dictionary = _side_wall()
	var off: bool = res.is_empty() or forward_push < 0.3 or _wall_time > cfg.wallrun_time or is_on_floor()
	if _jump_buffer > 0.0:
		# Jump off the wall: away from it, up, and on along it.
		_jump_buffer = 0.0
		var h: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
		velocity = h * 0.9 + _wall_normal * cfg.wallrun_jump_out + Vector3.UP * cfg.wallrun_jump_up * jump_scale
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
	var k: float = clampf(_wall_time / cfg.wallrun_time, 0.0, 1.0)
	var g: float = cfg.gravity * lerpf(cfg.wallrun_gravity_scale, 1.0, k * k)
	var vy: float = velocity.y - g * delta
	var speed: float = maxf(h2.length(), cfg.wallrun_speed * move_scale)
	# Hug the wall a little so small gaps don't drop you.
	velocity = t * speed - _wall_normal * 0.8 + Vector3.UP * vy
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
	var probe: Vector3 = Vector3(wall_at.x, feet.y + cfg.mantle_max_height + 0.3, wall_at.z) + fwd * 0.4
	var down: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(probe, Vector3(probe.x, feet.y + cfg.mantle_min_height - 0.05, probe.z), Ballistics.LAYER_WORLD)
	var top: Dictionary = space.intersect_ray(down)
	if top.is_empty():
		return false
	var top_at: Vector3 = top["position"]
	var top_n: Vector3 = top["normal"]
	var height: float = top_at.y - feet.y
	if top_n.y < 0.7 or height < cfg.mantle_min_height or height > cfg.mantle_max_height:
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
	_sprinting = false
	velocity = Vector3.ZERO
	Sfx.play_ui(&"mantle", -6.0, 0.05)
	return true


func _mantle(delta: float) -> void:
	var cfg: MovementConfig = movement
	var height: float = maxf(_mantle_to.y - _mantle_from.y, 0.1)
	_mantle_t = minf(_mantle_t + delta / (cfg.mantle_time * (0.7 + 0.3 * height / cfg.mantle_max_height)), 1.0)
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
		velocity = Vector3(fwd.x, 0.0, fwd.z) * 3.0


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
	_roll = lerpf(_roll, roll, clampf(delta * 8.0, 0.0, 1.0))
	_head.rotation.z = _roll
	_crouch_blend = move_toward(_crouch_blend, target, cfg.crouch_transition_speed * delta)
	var height: float = lerpf(cfg.stand_height, cfg.crouch_height, _crouch_blend)
	_capsule.height = height
	_collision.position.y = height * 0.5
	_step_offset = lerpf(_step_offset, 0.0, 1.0 - exp(-cfg.step_smooth * delta))
	_head.position.y = lerpf(cfg.stand_eye_height, cfg.crouch_eye_height, _crouch_blend) + _step_offset


func _on_settings_changed() -> void:
	_camera.fov = Settings.vertical_fov * fov_scale
