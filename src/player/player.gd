class_name Player
extends CharacterBody3D
## M0 first-person controller: controller look with shaped sticks and
## full-tilt acceleration, walk/sprint/crouch/jump. Slide, wall-run, mantle
## and air dash come in M1. Tuning lives in data/ resources.

@export var movement: MovementConfig = preload("res://data/player/movement_default.tres")
## Turned off while a benchmark or cutscene drives the camera.
@export var input_enabled: bool = true

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

@onready var _head: Node3D = $Head
@onready var _camera: Camera3D = $Head/Camera3D
@onready var _collision: CollisionShape3D = $CollisionShape3D


func _ready() -> void:
	add_to_group(&"player")
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


## Sets the view directly (radians). Used by the benchmark and spawn points.
func set_view(new_yaw: float, new_pitch: float) -> void:
	yaw = new_yaw
	pitch = clampf(new_pitch, -PITCH_LIMIT, PITCH_LIMIT)
	_apply_view()


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled:
		return
	var motion: InputEventMouseMotion = event as InputEventMouseMotion
	if motion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var k: float = deg_to_rad(Settings.look_config().mouse_deg_per_pixel)
		set_view(yaw - motion.relative.x * k, pitch - motion.relative.y * k)
	var click: InputEventMouseButton = event as InputEventMouseButton
	if click and click.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not CaptureDirector.is_capturing():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _process(delta: float) -> void:
	if input_enabled:
		var look: LookConfig = Settings.look_config()
		var raw: Vector2 = Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down", 0.0)
		_tilt_time = _tilt_time + delta if look.is_full_tilt(raw) else 0.0
		var rate: Vector2 = look.look_rate(raw, _tilt_time)
		set_view(yaw - deg_to_rad(rate.x) * delta, pitch - deg_to_rad(rate.y) * delta)
	_update_crouch_pose(delta)


func _physics_process(delta: float) -> void:
	var cfg: MovementConfig = movement
	var stick: Vector2 = Vector2.ZERO
	if input_enabled:
		var raw: Vector2 = Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back", 0.0)
		stick = Stick.shape(raw, cfg.move_inner_deadzone, cfg.move_outer_deadzone, 1.0)

	# Sprint: press L3 to start; ends when the stick stops pushing forward.
	if input_enabled and Input.is_action_just_pressed(&"sprint"):
		_sprinting = true
	if -stick.y < cfg.sprint_min_forward:
		_sprinting = false
	_crouching = input_enabled and Input.is_action_pressed(&"slide")
	if _crouching:
		_sprinting = false

	var speed: float = cfg.walk_speed
	if _sprinting:
		speed = cfg.sprint_speed
	elif _crouching:
		speed = cfg.crouch_speed
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
		vy = cfg.jump_velocity
		_jump_buffer = 0.0
		_coyote = 0.0

	velocity = Vector3(horizontal.x, vy, horizontal.z)
	move_and_slide()


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
	_camera.fov = Settings.vertical_fov
