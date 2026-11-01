class_name RangeProp
extends RigidBody3D
## Loose physics prop for the range: tin cans, glass bottles, small crates.
## Bullets push it with the momentum they lose (Ballistics caps the speed).
## Breakable props (bottles) shatter into debris when hit; everything
## respawns where it started after `respawn_time` once disturbed.

@export var breakable: bool = false
@export var shard_color: Color = Color(0.45, 0.6, 0.45)
@export var respawn_time: float = 6.0

var _home: Transform3D
var _disturbed: float = -1.0


func _ready() -> void:
	add_to_group(&"range_targets")
	collision_layer = Ballistics.LAYER_PROPS
	collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_DEBRIS
	_home = global_transform


func on_ballistic_hit(hit: BallisticHit) -> void:
	_disturbed = 0.0
	EventBus.target_hit.emit(&"hit", hit)
	if breakable and visible:
		visible = false
		set_deferred(&"freeze", true)
		collision_layer = 0
		Fx.debris(global_position, hit.direction * 3.0 + Vector3.UP, shard_color, 0.03, 6, 0.8, &"glass")


func _physics_process(delta: float) -> void:
	if _disturbed < 0.0:
		if linear_velocity.length() > 0.5:
			_disturbed = 0.0
		return
	_disturbed += delta
	if _disturbed > respawn_time:
		_disturbed = -1.0
		freeze = false
		visible = true
		collision_layer = Ballistics.LAYER_PROPS
		linear_velocity = Vector3.ZERO
		angular_velocity = Vector3.ZERO
		global_transform = _home
