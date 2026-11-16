class_name ThrownProjectile
extends Node3D
## A thrown molotov or EMP grenade in flight (ThrowerBrain): a ballistic arc
## under gravity, swept against the world, props and the operative each
## physics frame.
## - Molotov: breaks on whatever it hits first; the fuel spills under the
##   break (FirePatch). Lit rag: a flame rides on it all the way.
## - EMP: lands, skids to a stop, the lamp blinks for its fuse, then pulses:
##   inside emp_radius, with nothing solid between, the operative's actives
##   go down and stay down (ActivePart.jam) and a drone in the air loses its link.

const GRAVITY: float = 9.8
const MASK: int = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_PLAYER

var cfg: ThrowerConfig
var thrower: Node
var velocity: Vector3 = Vector3.ZERO
var landed: bool = false
var _fuse: float = -1.0
var _spin: Vector3
var _model: Node3D
var _flame: CPUParticles3D
var _age: float = 0.0
## Result for tests: &"burst" (a molotov broke), &"pulse" (an EMP went off).
var outcome: StringName = &""
static var last_pulse_hit_player: bool = false


static func launch(parent: Node, from: Vector3, v: Vector3, p_cfg: ThrowerConfig, by: Node) -> ThrownProjectile:
	var t: ThrownProjectile = ThrownProjectile.new()
	t.cfg = p_cfg
	t.thrower = by
	t.velocity = v
	parent.add_child(t)
	t.global_position = from
	return t


func _ready() -> void:
	add_to_group(&"thrown")
	if cfg.model:
		_model = cfg.model.instantiate() as Node3D
		add_child(_model)
		if cfg.kind == ThrowerConfig.Kind.MOLOTOV:
			# Held by the neck on the weapon socket: centre the bottle on the node.
			_model.position = Vector3(-0.03, -0.06, 0.0)
	_spin = Vector3(randf_range(-9, 9), randf_range(-4, 4), randf_range(-9, 9))
	if cfg.kind == ThrowerConfig.Kind.MOLOTOV:
		_flame = CPUParticles3D.new()
		_flame.amount = 16
		_flame.lifetime = 0.35
		_flame.local_coords = false
		var q: QuadMesh = QuadMesh.new()
		q.size = Vector2.ONE
		_flame.mesh = q
		_flame.material_override = Fx.fire_material()
		_flame.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
		_flame.emission_sphere_radius = 0.03
		_flame.direction = Vector3.UP
		_flame.spread = 25.0
		_flame.gravity = Vector3(0, 1.5, 0)
		_flame.initial_velocity_min = 0.2
		_flame.initial_velocity_max = 0.6
		_flame.scale_amount_min = 0.06
		_flame.scale_amount_max = 0.14
		_flame.color_ramp = Fx.fire_ramp()
		add_child(_flame)


func _physics_process(delta: float) -> void:
	_age += delta
	if _fuse >= 0.0:
		_fuse -= delta
		if _model:
			_model.visible = true
		if _fuse <= 0.0:
			_pulse()
		return
	if _age > 6.0:
		queue_free()
		return
	var from: Vector3 = global_position
	velocity.y -= GRAVITY * delta
	var to: Vector3 = from + velocity * delta
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(from, to, MASK)
	if thrower and thrower is CollisionObject3D:
		q.exclude = [(thrower as CollisionObject3D).get_rid()]
	var hit: Dictionary = space.intersect_ray(q) if _age > 0.05 else {}
	if hit.is_empty():
		global_position = to
		if _model:
			_model.rotation += _spin * delta
		return
	var at: Vector3 = hit["position"]
	var n: Vector3 = hit["normal"]
	global_position = at + n * 0.03
	var collider: Object = hit["collider"]
	if cfg.kind == ThrowerConfig.Kind.MOLOTOV:
		_burst(at, n, collider)
	else:
		_land(at, n)


func _burst(at: Vector3, n: Vector3, collider: Object) -> void:
	outcome = &"burst"
	Sfx.play_at(&"molotov_break", at, 3.0, 0.1)
	Fx._emit(&"sparks", at, n, Color(1.0, 0.6, 0.2, 1.0), 10, 1.4)
	# The fuel runs down to the ground under the break.
	var ground: Vector3 = at
	var gn: Vector3 = n
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var down: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(at + n * 0.1, at + Vector3.DOWN * 4.0, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS))
	if not down.is_empty():
		ground = down["position"]
		gn = down["normal"]
	FirePatch.spawn(get_parent(), ground, gn, cfg, thrower)
	if collider is Player:
		(collider as Player).take_damage(cfg.fire_dps * 0.5, -velocity.normalized())
	queue_free()


func _land(at: Vector3, n: Vector3) -> void:
	landed = true
	Sfx.play_at(&"m32_dud_bounce", at, -2.0, 0.1)
	global_position = at + n * 0.06
	_fuse = cfg.emp_fuse
	velocity = Vector3.ZERO


func _pulse() -> void:
	outcome = &"pulse"
	var at: Vector3 = global_position
	Sfx.play_at(&"emp_pulse", at, 6.0, 0.05)
	Fx._emit(&"sparks", at, Vector3.UP, Color(0.5, 0.8, 1.0, 1.0), 24, 2.0)
	Fx.explosion_fx().shockwave(at, Vector3.UP, cfg.emp_radius * 0.6)
	EventBus.emp_pulse.emit(at, cfg.emp_radius)
	var p: Player = get_tree().get_first_node_in_group(&"player") as Player
	last_pulse_hit_player = false
	if p and not p.dead:
		var eye: Vector3 = p.camera().global_position
		var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
		var clear: bool = space.intersect_ray(PhysicsRayQueryParameters3D.create(at + Vector3.UP * 0.2, eye, Ballistics.LAYER_WORLD)).is_empty()
		if eye.distance_to(at) <= cfg.emp_radius and clear:
			last_pulse_hit_player = true
			if p.augments:
				p.augments.jam(cfg.emp_stall)
			p.add_shake(0.4)
			EventBus.player_jammed.emit(cfg.emp_stall)
	queue_free()
