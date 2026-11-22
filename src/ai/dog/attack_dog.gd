class_name AttackDog
extends CharacterBody3D
## The triad's attack dog (docs/design.md §8.8b): a German shepherd that runs
## straight at the operative by scent, leaps the last few metres with its jaw
## open and bites, backs off a step and goes again. No gun, no cover, no
## morale: it has to be shot or cut down before it arrives.
##
## Model: Tripo3D mesh and quadruped rig, our animations
## (raw_assets/characters/attack_dog/build.py). Tuning: data/enemies/attack_dog.tres.
## Joins the "enemies" group like the men, but isn't an Enemy: code that casts
## to Enemy skips it; spawners, blasts and the R3 strike handle it by name.

signal died(dog: AttackDog)

const ROLE: String = "attack_dog"
const SCENE: String = "res://assets/characters/attack_dog/attack_dog.glb"
const GRAVITY: float = 20.0
const KNOCK_DECAY: float = 10.0
## Hit zones, attached to Tripo's bones: [zone, bone, kind, size, rest point
## in model space (+X forward, metres)].
const ZONES: Array = [
	[&"head", &"tripo__Head_0", "sphere", Vector3(0.105, 0, 0), Vector3(0.47, 0.31, 0.0)],
	[&"neck", &"tripo__Spine_4", "sphere", Vector3(0.1, 0, 0), Vector3(0.31, 0.39, 0.0)],
	[&"chest", &"tripo__Spine_2", "sphere", Vector3(0.155, 0, 0), Vector3(0.14, 0.42, 0.0)],
	[&"body", &"tripo__Spine_0", "capsule", Vector3(0.14, 0.42, 0), Vector3(-0.12, 0.43, 0.0)],
	[&"leg", &"tripo__0_Left_Limb_1", "capsule", Vector3(0.05, 0.3, 0), Vector3(0.15, 0.2, -0.12)],
	[&"leg", &"tripo__0_Right_Limb_1", "capsule", Vector3(0.05, 0.3, 0), Vector3(0.12, 0.2, 0.11)],
	[&"leg", &"tripo__1_Left_Limb_1", "capsule", Vector3(0.055, 0.32, 0), Vector3(-0.13, 0.22, -0.11)],
	[&"leg", &"tripo__1_Right_Limb_1", "capsule", Vector3(0.055, 0.32, 0), Vector3(-0.2, 0.22, 0.11)],
]
const LOOPS: Array[StringName] = [&"run", &"trot", &"idle_snarl"]
const SHADER: Shader = preload("res://src/ai/dog/dog.gdshader")

enum State { CHASE, WINDUP, LUNGE, RECOVER, BITE, FLINCH, DEAD }

@export var config: DogConfig

var state: State = State.CHASE
var health: float = 60.0
var alive: bool = true
var dead: bool:
	get:
		return not alive
var player: Player
var nav: NavigationAgent3D
var model: Node3D
var anim: AnimationPlayer
var skeleton: Skeleton3D
var hitboxes: Array[HitboxPart] = []
## Its coat (dog.gdshader): fill, rim, blood.
var coat: ShaderMaterial
## Bites that landed and whiffed (tests, tuning).
var bites: int = 0
var whiffs: int = 0
var last_hit: BallisticHit

var _t: float = 0.0
var _yaw: float = 0.0
var _cooldown: float = 0.0
var _bit_this: bool = false
var _growl_in: float = 0.5
var _knock: Vector3 = Vector3.ZERO
var _blood: float = 0.0
## Its own running velocity (flat); the shove is added on top.
var _run_vel: Vector3 = Vector3.ZERO
var _nav_refresh: float = 0.0
var _run_len: float = 0.5
var _trot_len: float = 0.7
var _clear_cache: bool = false
var _clear_timer: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()

static var _blob_mesh: QuadMesh
static var _blob_mat: StandardMaterial3D


func _ready() -> void:
	_rng.randomize()
	if config == null:
		config = load("res://data/enemies/%s.tres" % ROLE) as DogConfig
	health = config.health
	add_to_group(&"enemies")
	add_to_group(&"dogs")
	add_to_group(&"aim_assist_targets")
	collision_layer = Ballistics.LAYER_ENEMY
	collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS | Ballistics.LAYER_ENEMY | Ballistics.LAYER_CLIP
	var cs: CollisionShape3D = CollisionShape3D.new()
	cs.name = "Capsule"
	var cap: CapsuleShape3D = CapsuleShape3D.new()
	cap.radius = 0.28
	cap.height = 0.62
	cs.shape = cap
	cs.position = Vector3(0, 0.33, 0)
	add_child(cs)
	_build_model()
	nav = NavigationAgent3D.new()
	nav.path_desired_distance = 0.6
	nav.target_desired_distance = 0.5
	nav.radius = 0.3
	nav.avoidance_enabled = false
	add_child(nav)
	_yaw = rotation.y
	_play(&"run")
	_growl_in = _rng.randf_range(0.2, 1.0)


## Starts loading the dog model and its textures on a worker thread so the
## first dog spawn never stalls the main thread.
static func prefetch() -> void:
	if not ResourceLoader.has_cached(SCENE) \
			and ResourceLoader.load_threaded_get_status(SCENE) == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
		ResourceLoader.load_threaded_request(SCENE)


func _build_model() -> void:
	var ps: PackedScene
	if ResourceLoader.load_threaded_get_status(SCENE) != ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
		ps = ResourceLoader.load_threaded_get(SCENE) as PackedScene
	else:
		ps = load(SCENE) as PackedScene
	model = ps.instantiate() as Node3D
	model.name = "Model"
	# The model faces +X; the dog faces +Z like every other body here.
	model.rotation_degrees = Vector3(0, -90, 0)
	add_child(model)
	anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	skeleton = model.find_child("Skeleton3D", true, false) as Skeleton3D
	for n: StringName in LOOPS:
		if anim.has_animation(n):
			anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	if anim.has_animation(&"run"):
		_run_len = anim.get_animation(&"run").length
	if anim.has_animation(&"trot"):
		_trot_len = anim.get_animation(&"trot").length
	for mi: Node in model.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = mi as MeshInstance3D
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_dress(m)
	_build_blob()
	_build_hitboxes()


## Swaps Tripo's material for the coat shader, keeping its maps. One
## material per dog (blood and the death fade are its own).
func _dress(m: MeshInstance3D) -> void:
	var std: StandardMaterial3D = m.mesh.surface_get_material(0) as StandardMaterial3D
	if std == null:
		return
	coat = ShaderMaterial.new()
	coat.shader = SHADER
	coat.render_priority = EnemyBody.RENDER_PRIORITY
	coat.set_shader_parameter(&"base_tex", std.albedo_texture)
	coat.set_shader_parameter(&"orm_tex", std.roughness_texture)
	coat.set_shader_parameter(&"normal_tex", std.normal_texture)
	coat.set_shader_parameter(&"fill_light", config.fill_light)
	coat.set_shader_parameter(&"rim_strength", config.rim_strength)
	m.material_override = coat


func _set_coat(param: StringName, v: float) -> void:
	if coat:
		coat.set_shader_parameter(param, v)


func _set_rim(v: float) -> void:
	_set_coat(&"rim_alive", v)


## A soft contact shadow under it (shared quad/material across all dogs).
func _build_blob() -> void:
	if _blob_mesh == null:
		_blob_mesh = QuadMesh.new()
		_blob_mesh.size = Vector2(0.7, 1.35)
		_blob_mesh.orientation = PlaneMesh.FACE_Y
		var g: GradientTexture2D = GradientTexture2D.new()
		g.fill = GradientTexture2D.FILL_RADIAL
		g.fill_from = Vector2(0.5, 0.5)
		g.fill_to = Vector2(0.5, 0.0)
		g.width = 64
		g.height = 64
		var gr: Gradient = Gradient.new()
		gr.set_color(0, Color(0, 0, 0, 0.55))
		gr.set_color(1, Color(0, 0, 0, 0.0))
		g.gradient = gr
		_blob_mat = StandardMaterial3D.new()
		_blob_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_blob_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_blob_mat.albedo_texture = g
		_blob_mat.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.name = "Blob"
	mi.mesh = _blob_mesh
	mi.material_override = _blob_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.position = Vector3(0, 0.02, 0)
	add_child(mi)


func _build_hitboxes() -> void:
	var atts: Dictionary[StringName, BoneAttachment3D] = {}
	for spec: Array in ZONES:
		var zone: StringName = spec[0]
		var bone: StringName = spec[1]
		var idx: int = skeleton.find_bone(bone)
		if idx < 0:
			push_warning("AttackDog: no bone %s" % bone)
			continue
		if not atts.has(bone):
			var att: BoneAttachment3D = BoneAttachment3D.new()
			att.name = "Att_" + String(bone)
			att.bone_name = bone
			skeleton.add_child(att)
			atts[bone] = att
		var rest: Transform3D = skeleton.get_bone_global_rest(idx)
		var part: HitboxPart = HitboxPart.new()
		part.name = "%s_%d" % [zone, hitboxes.size()]
		part.target = self
		part.collision_layer = Ballistics.LAYER_HITBOX
		part.collision_mask = 0
		part.set_meta(&"zone", zone)
		part.set_meta(&"surface", &"flesh")
		part.set_meta(&"bone", bone)
		part.add_to_group(&"gore_body")
		var at: Vector3 = spec[4]
		part.transform = rest.affine_inverse() * Transform3D(Basis(), at)
		var cs: CollisionShape3D = CollisionShape3D.new()
		var dims: Vector3 = spec[3]
		if spec[2] == "sphere":
			var sp: SphereShape3D = SphereShape3D.new()
			sp.radius = dims.x
			cs.shape = sp
		else:
			var c: CapsuleShape3D = CapsuleShape3D.new()
			c.radius = dims.x
			c.height = maxf(dims.y, dims.x * 2.0 + 0.01)
			cs.shape = c
			# The part sits in model space at rest: legs stand, the body
			# capsule lies along the spine (+X).
			if zone == &"body":
				cs.basis = Basis(Vector3.BACK, PI * 0.5)
		part.add_child(cs)
		atts[bone].add_child(part)
		hitboxes.append(part)


# ------------------------------------------------------------------ queries

func aim_points() -> PackedVector3Array:
	if not alive:
		return PackedVector3Array()
	return PackedVector3Array([head_position(), chest_position()])


func head_position() -> Vector3:
	return _zone_position(&"head", global_position + Vector3.UP * 0.35 + global_basis.z * 0.5)


func chest_position() -> Vector3:
	return _zone_position(&"chest", global_position + Vector3.UP * 0.42 + global_basis.z * 0.15)


func _zone_position(zone: StringName, fallback: Vector3) -> Vector3:
	for h: HitboxPart in hitboxes:
		if h.get_meta(&"zone") == zone:
			return h.global_position
	return fallback


func part(zone: StringName) -> HitboxPart:
	for h: HitboxPart in hitboxes:
		if h.get_meta(&"zone") == zone:
			return h
	return null


func ballistic_exclude() -> Array[RID]:
	var out: Array[RID] = [get_rid()]
	for h: HitboxPart in hitboxes:
		out.append(h.get_rid())
	return out


func is_threat() -> bool:
	return alive


func state_name() -> String:
	return State.keys()[state]


func is_winding_up() -> bool:
	return state == State.WINDUP


## Faces `yaw` at once (spawning).
func face(yaw: float) -> void:
	_yaw = yaw
	rotation.y = yaw


# ------------------------------------------------------------------ hits

func on_part_hit(p: HitboxPart, hit: BallisticHit) -> void:
	var zone: StringName = p.get_meta(&"zone")
	last_hit = hit
	var head: bool = zone == &"head" or zone == &"neck"
	var dep: float = hit.deposited()
	_blood += config.blood_per_hit
	_set_coat(&"bloodied", minf(_blood, 1.0))
	Gore.flesh_hit(hit, sqrt(maxf(dep, 30.0) / 300.0) * config.gore_scale, head)
	if not alive:
		_knock += _flat(hit.direction) * clampf(hit.damage.impulse * 0.05, 0.0, 1.5)
		set_physics_process(true)
		return
	var mult: float = config.zone_multipliers.get(zone, 1.0)
	var dmg: float = hit.damage.amount * mult
	var push: Vector3 = _flat(hit.direction) * clampf(hit.damage.impulse * config.knock_per_impulse * TimeControl.impact_multiplier(), 0.0, 6.0)
	_hurt(dmg, push, hit.shooter, hit)
	EventBus.target_hit.emit(&"kill" if not alive else (&"headshot" if head else &"hit"), hit)
	EventBus.damage_applied.emit(hit.damage, self)


## Embers set it alight: one burst of damage, no lasting fire on a dog.
func on_part_burn(_p: HitboxPart, hit: BallisticHit) -> void:
	if alive:
		_hurt(hit.damage.amount * 0.6, Vector3.ZERO, hit.shooter, hit)


## A blast (Explosion.detonate) or a blow (the R3 strike). `push` in m/s.
func strike(damage: float, push: Vector3, from: Node) -> void:
	if not alive:
		_knock += push * 0.5
		set_physics_process(true)
		return
	_hurt(damage, push, from, null)


func _hurt(dmg: float, push: Vector3, _from: Node, hit: BallisticHit) -> void:
	health -= dmg
	_knock += push
	if health <= 0.0:
		die(hit)
		return
	if dmg >= config.flinch_damage and state != State.LUNGE:
		_enter(State.FLINCH)
		_play(&"flinch", 0.04)
		Sfx.play_at(&"dog_yelp", head_position(), 0.0, 0.1)


func die(hit: BallisticHit = null) -> void:
	if not alive:
		return
	alive = false
	_enter(State.DEAD)
	remove_from_group(&"enemies")
	remove_from_group(&"aim_assist_targets")
	collision_layer = 0
	collision_mask = Ballistics.LAYER_WORLD | Ballistics.LAYER_CLIP
	if hit:
		_knock += _flat(hit.direction) * clampf(hit.damage.impulse * 0.12, 0.5, 4.0)
	_play(&"death", 0.06)
	if coat:
		create_tween().tween_method(_set_rim, 1.0, 0.0, 0.8)
	_run_vel = Vector3(velocity.x, 0.0, velocity.z) * 0.5
	Sfx.play_at(&"dog_death", head_position(), -1.0, 0.08)
	EventBus.killed.emit(self, hit.damage if hit else null)
	died.emit(self)


# ------------------------------------------------------------------ behaviour

func _physics_process(delta: float) -> void:
	_t += delta
	_cooldown = maxf(_cooldown - delta, 0.0)
	if player == null or not is_instance_valid(player):
		player = get_tree().get_first_node_in_group(&"player") as Player
	var want: Vector3 = Vector3.ZERO
	match state:
		State.CHASE:
			want = _chase(delta)
		State.WINDUP:
			want = Vector3.ZERO
			_face_player(delta, 2.0)
			if _t >= config.lunge_windup:
				_spring()
		State.LUNGE:
			want = Vector3.INF
			_lunge_contact()
			if _t > 0.15 and is_on_floor():
				_enter(State.RECOVER)
				_cooldown = config.lunge_cooldown
				_play(&"trot", 0.15)
		State.RECOVER:
			# A step back off the operative, then in again.
			var away: Vector3 = _flat(global_position - _player_pos())
			want = away.normalized() * config.trot_speed * 0.6 if away.length() < 2.0 else Vector3.ZERO
			_face_player(delta, 1.0)
			if _t > 0.5:
				_enter(State.CHASE)
		State.BITE:
			want = Vector3.ZERO
			_face_player(delta, 1.5)
			if not _bit_this and _t >= config.bite_at:
				_bit_this = true
				_resolve_bite(config.bite_damage, config.bite_push, config.bite_range + 0.25)
			if _t >= 0.5:
				_cooldown = config.bite_cooldown
				_enter(State.CHASE)
		State.FLINCH:
			want = Vector3.ZERO
			if _t >= config.flinch_time:
				_enter(State.CHASE)
		State.DEAD:
			want = Vector3.ZERO
	_move(want, delta)
	_voice(delta)


func _chase(delta: float) -> Vector3:
	if player == null or player.dead:
		_play(&"idle_snarl", 0.25)
		return Vector3.ZERO
	var target: Vector3 = _player_pos()
	var to: Vector3 = _flat(target - global_position)
	var d: float = to.length()
	_clear_timer -= delta
	if _clear_timer <= 0.0 or d < 4.0:
		_clear_timer = 0.15
		_clear_cache = _clear_to(target)
	var clear: bool = _clear_cache
	if _cooldown <= 0.0 and clear:
		if d <= config.bite_range:
			_enter(State.BITE)
			_play(&"bite", 0.06)
			Sfx.play_at(&"dog_snarl", head_position(), -2.0, 0.1)
			return Vector3.ZERO
		if d <= config.lunge_range and d >= config.lunge_min and _facing(target) > 0.8:
			_enter(State.WINDUP)
			_play(&"lunge", 0.05)
			Sfx.play_at(&"dog_snarl", head_position(), 1.0, 0.1)
			return Vector3.ZERO
	var dir: Vector3
	if clear or d < 3.0:
		dir = to.normalized() if d > 0.05 else Vector3.ZERO
	else:
		_nav_refresh -= delta
		if _nav_refresh <= 0.0:
			_nav_refresh = 0.4
			nav.target_position = target
		var next: Vector3 = nav.get_next_path_position() if nav.get_navigation_map().is_valid() and not nav.is_navigation_finished() else target
		var t2: Vector3 = _flat(next - global_position)
		dir = t2.normalized() if t2.length() > 0.05 else to.normalized()
	# Gallop in; trot the last couple of metres while the leap recharges.
	var speed: float = config.run_speed if (d > 3.0 or _cooldown <= 0.0) else config.trot_speed
	if d < 1.0:
		speed = 0.0
	return dir * speed


func _spring() -> void:
	var to: Vector3 = _flat(_player_pos() - global_position)
	var d: float = to.length()
	# Far enough to arrive, not much past him.
	# Flight time of the arc: 2 * up / g.
	var flight: float = 2.0 * config.lunge_up / GRAVITY
	var speed: float = minf(config.lunge_speed, (d + 0.2) / flight)
	_run_vel = to.normalized() * speed
	velocity = _run_vel + Vector3.UP * config.lunge_up
	_bit_this = false
	_enter(State.LUNGE)


func _lunge_contact() -> void:
	if _bit_this or player == null:
		return
	var mouth: Vector3 = head_position()
	var chest: Vector3 = player.global_position + Vector3.UP * 0.9
	if mouth.distance_to(chest) <= config.lunge_reach or _flat(mouth - chest).length() < 0.5:
		_bit_this = true
		_resolve_bite(config.lunge_damage, config.lunge_push, 99.0)
		# It hangs on for a moment, then drops off.
		_run_vel *= 0.15
		velocity = Vector3(_run_vel.x, minf(velocity.y, 0.0), _run_vel.z)


## Teeth close: lands if the operative is still in reach and in front.
func _resolve_bite(damage: float, push: float, reach: float) -> void:
	if player == null or player.dead:
		return
	var to: Vector3 = _flat(_player_pos() - global_position)
	if to.length() > reach or (reach < 50.0 and _facing(_player_pos()) < 0.3):
		whiffs += 1
		Sfx.play_at(&"dog_bite", head_position(), -6.0, 0.1)
		return
	var dealt: float = player.on_melee_hit(self, damage, to.normalized(), push)
	Sfx.play_at(&"dog_bite", head_position(), 2.0, 0.1)
	if dealt > 0.0:
		bites += 1
		Sfx.play_at(&"impact_flesh", player.camera().global_position - Vector3.UP * 0.6, 0.0, 0.1)
		player.add_shake(0.3)
		for pad: int in Input.get_connected_joypads():
			Input.start_joy_vibration(pad, 0.6, 0.9, 0.18)
	else:
		whiffs += 1


func _move(want: Vector3, delta: float) -> void:
	if want != Vector3.INF:
		var accel: float = config.acceleration if alive else 6.0
		_run_vel = _run_vel.move_toward(want, accel * delta)
	var vy: float = velocity.y - GRAVITY * delta if (not is_on_floor() or velocity.y > 0.0) else -0.5
	velocity = Vector3(_run_vel.x + _knock.x, vy, _run_vel.z + _knock.z)
	move_and_slide()
	_knock = _knock.move_toward(Vector3.ZERO, KNOCK_DECAY * delta)
	if get_slide_collision_count() > 0 and want != Vector3.INF:
		# Ran into something: its own speed is what it actually made.
		var real: Vector3 = Vector3(velocity.x, 0.0, velocity.z) - Vector3(_knock.x, 0.0, _knock.z)
		if real.length() < _run_vel.length():
			_run_vel = real
	if not alive:
		if is_on_floor() and _knock.length_squared() < 0.001 and _run_vel.length_squared() < 0.001:
			set_physics_process(false)
		return
	var flat: Vector3 = _run_vel
	var spd: float = flat.length()
	if state == State.CHASE:
		if spd > 0.3:
			_turn_toward(atan2(flat.x, flat.z), delta)
		if spd > config.trot_speed + 1.0:
			_play(&"run", 0.15, spd / (config.run_stride / _run_len))
		elif spd > 0.4:
			_play(&"trot", 0.15, spd / (config.trot_stride / _trot_len))
		else:
			_play(&"idle_snarl", 0.2)
	elif state == State.RECOVER and spd > 0.4:
		_play(&"trot", 0.15, maxf(spd / (config.trot_stride / _trot_len), 0.6))


func _voice(delta: float) -> void:
	if not alive or state != State.CHASE:
		return
	_growl_in -= delta
	if _growl_in <= 0.0:
		_growl_in = _rng.randf_range(config.growl_gap.x, config.growl_gap.y)
		var bark: bool = _rng.randf() < config.bark_chance
		Sfx.play_at(&"dog_bark" if bark else &"dog_growl", head_position(), 0.0 if bark else -3.0, 0.1)


# ------------------------------------------------------------------ helpers

func _enter(s: State) -> void:
	state = s
	_t = 0.0


func _play(n: StringName, blend: float = 0.15, speed: float = 1.0) -> void:
	if anim == null or not anim.has_animation(n):
		return
	if anim.current_animation != n:
		anim.play(n, blend)
	anim.speed_scale = speed


func _player_pos() -> Vector3:
	return player.global_position if player else global_position + global_basis.z


func _face_player(delta: float, rate: float) -> void:
	var to: Vector3 = _flat(_player_pos() - global_position)
	if to.length() > 0.05:
		_turn_toward(atan2(to.x, to.z), delta * rate)


func _turn_toward(yaw: float, delta: float) -> void:
	_yaw = rotate_toward(_yaw, yaw, deg_to_rad(config.turn_speed_deg) * delta)
	rotation.y = _yaw


## How squarely it faces `p` (1 = straight at it).
func _facing(p: Vector3) -> float:
	var to: Vector3 = _flat(p - global_position)
	if to.length() < 0.05:
		return 1.0
	return global_basis.z.dot(to.normalized())


## Nothing solid between it and `p` at its own height.
func _clear_to(p: Vector3) -> bool:
	var mask: int = Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.4, p + Vector3.UP * 0.4, mask)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)
