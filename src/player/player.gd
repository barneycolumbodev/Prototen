class_name Player
extends CharacterBody3D
## M0 first-person controller: controller look with shaped sticks and
## full-tilt acceleration, walk/sprint/crouch/jump. Slide, wall-run, mantle
## and air dash come in M1. Tuning lives in data/ resources.

@export var movement: MovementConfig = preload("res://data/player/movement_default.tres")
@export var body_config: PlayerBodyConfig = preload("res://data/player/body_default.tres")
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
## Set by the weapon: carrying a heavy gun cuts sprint speed and jump height.
var sprint_scale: float = 1.0
var jump_scale: float = 1.0
## While true (aiming) a sprint can't start.
var sprint_blocked: bool = false
## Look speed in degrees per second: x = turning right, y = looking up.
var look_velocity: Vector2 = Vector2.ZERO
## Aim assist (set up by the level; null = off).
var aim_assist: AimAssist

const PITCH_LIMIT: float = deg_to_rad(88.0)

var yaw: float = 0.0
var pitch: float = 0.0

var _tilt_time: float = 0.0
var _sprinting: bool = false
var _crouching: bool = false
var _crouch_blend: float = 0.0
var _coyote: float = 0.0
var _jump_buffer: float = 0.0
var _capsule: CapsuleShape3D
var _last_yaw: float = 0.0
var _last_pitch: float = 0.0

@onready var _head: Node3D = $Head
@onready var _camera: Camera3D = $Head/Camera3D
@onready var _collision: CollisionShape3D = $CollisionShape3D


func _ready() -> void:
	add_to_group(&"player")
	add_to_group(&"suppressible")
	set_meta(&"surface", &"flesh")
	set_meta(&"stops_rounds", true)
	health = body_config.max_health
	collision_layer = Ballistics.LAYER_PLAYER
	# Corpses and moving hitboxes don't block; living enemies do (their capsules).
	collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_ENEMY
	_capsule = (_collision.shape as CapsuleShape3D).duplicate() as CapsuleShape3D
	_collision.shape = _capsule
	yaw = rotation.y
	pitch = _head.rotation.x
	_camera.make_current()
	Settings.changed.connect(_on_settings_changed)
	_on_settings_changed()


func is_sprinting() -> bool:
	return _sprinting


func is_crouching() -> bool:
	return _crouching


func camera() -> Camera3D:
	return _camera


func weapon() -> PlayerWeapon:
	return get_node_or_null(^"Weapon") as PlayerWeapon


## Enemy rounds land here (Ballistics hits the player's capsule).
func on_ballistic_hit(hit: BallisticHit) -> void:
	if dead or invulnerable or hit.shooter == self:
		return
	var amount: float = hit.energy_in * 0.001 * body_config.damage_per_kj
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
	health = body_config.max_health
	input_enabled = true
	suppression = 0.0
	global_position = spawn_point
	velocity = Vector3.ZERO
	respawned.emit()


func health_fraction() -> float:
	return health / body_config.max_health


func stop_sprint() -> void:
	_sprinting = false


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
	if input_enabled and not look_blocked:
		var look: LookConfig = Settings.look_config()
		var raw: Vector2 = Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.0)
		_tilt_time = _tilt_time + delta if look.is_full_tilt(raw) else 0.0
		var rate: Vector2 = look.look_rate(raw, _tilt_time) * look_scale * Settings.look_sensitivity
		if aim_assist:
			rate = aim_assist.apply(self, rate, delta)
		set_view(yaw - deg_to_rad(rate.x) * delta, pitch - deg_to_rad(rate.y) * delta)
	_update_crouch_pose(delta)
	_camera.fov = Settings.vertical_fov * fov_scale
	if delta > 0.0:
		var measured: Vector2 = Vector2(-angle_difference(_last_yaw, yaw), angle_difference(_last_pitch, pitch)) / delta
		look_velocity = look_velocity.lerp(Vector2(rad_to_deg(measured.x), rad_to_deg(measured.y)), clampf(delta * 20.0, 0.0, 1.0))
	_last_yaw = yaw
	_last_pitch = pitch


func _physics_process(delta: float) -> void:
	_since_hit += delta
	suppression = maxf(0.0, suppression - delta * 0.5)
	if dead:
		_dead_time += delta
		velocity = Vector3(0, velocity.y - movement.gravity * delta, 0) if not is_on_floor() else Vector3.ZERO
		move_and_slide()
		return
	if _since_hit > body_config.regen_delay and health < body_config.max_health:
		health = minf(health + body_config.regen_rate * delta, body_config.max_health)
	var cfg: MovementConfig = movement
	var stick: Vector2 = Vector2.ZERO
	if input_enabled:
		var raw: Vector2 = Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back", 0.0)
		stick = Stick.shape(raw, cfg.move_inner_deadzone, cfg.move_outer_deadzone, 1.0)

	# Sprint: press L3 to start; ends when the stick stops pushing forward.
	if input_enabled and Input.is_action_just_pressed(&"sprint") and not sprint_blocked:
		_sprinting = true
	if -stick.y < cfg.sprint_min_forward:
		_sprinting = false
	_crouching = input_enabled and Input.is_action_pressed(&"slide")
	if _crouching:
		_sprinting = false

	if sprint_blocked:
		_sprinting = false
	var speed: float = cfg.walk_speed
	if _sprinting:
		speed = cfg.sprint_speed * sprint_scale
	elif _crouching:
		speed = cfg.crouch_speed
	speed *= move_scale
	var wish: Vector3 = global_basis * Vector3(stick.x, 0.0, stick.y)
	wish.y = 0.0
	var horizontal: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	if is_on_floor():
		horizontal = MovementConfig.approach(horizontal, wish * speed, cfg.ground_accel, cfg.ground_decel, delta)
	else:
		horizontal = MovementConfig.approach(horizontal, wish * speed, cfg.air_accel, cfg.air_accel * 0.25, delta)

	_coyote = cfg.coyote_time if is_on_floor() else _coyote - delta
	_jump_buffer = cfg.jump_buffer if input_enabled and Input.is_action_just_pressed(&"jump") else _jump_buffer - delta
	var vy: float = velocity.y
	if not is_on_floor():
		vy -= cfg.gravity * delta
	if _jump_buffer > 0.0 and _coyote > 0.0:
		vy = cfg.jump_velocity * jump_scale
		_jump_buffer = 0.0
		_coyote = 0.0

	velocity = Vector3(horizontal.x, vy, horizontal.z)
	var was_on_floor: bool = is_on_floor()
	move_and_slide()
	if is_on_floor() and not was_on_floor and vy < -1.0:
		landed.emit(-vy)


func _apply_view() -> void:
	rotation.y = yaw
	_head.rotation.x = pitch


func _update_crouch_pose(delta: float) -> void:
	var cfg: MovementConfig = movement
	var target: float = 1.0 if _crouching else 0.0
	_crouch_blend = move_toward(_crouch_blend, target, cfg.crouch_transition_speed * delta)
	var height: float = lerpf(cfg.stand_height, cfg.crouch_height, _crouch_blend)
	_capsule.height = height
	_collision.position.y = height * 0.5
	_head.position.y = lerpf(cfg.stand_eye_height, cfg.crouch_eye_height, _crouch_blend)


func _on_settings_changed() -> void:
	_camera.fov = Settings.vertical_fov * fov_scale
