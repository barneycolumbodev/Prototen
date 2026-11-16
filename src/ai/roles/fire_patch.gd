class_name FirePatch
extends Node3D
## Burning fuel on the ground where a molotov broke (docs/design.md §8.8c).
## It spreads to its radius in half a second, burns for `fire_time`, and
## dies down over the last two seconds. Anyone standing in it burns: the
## operative takes fire_dps (bare suit; armour scales it like a blade,
## Player.on_melee_hit's rule), a man catches fire (Enemy.ignite). It
## closes a street: the AI won't walk into it (Enemy._move steers out).
## At most MAX alive; a new one puts out the oldest. One flickering light
## each (perf budget: four dynamic lights, no shadows).

const MAX: int = 3
static var active: Array[FirePatch] = []

var radius: float = 2.4
var lifetime: float = 8.0
var dps: float = 22.0
var ignite_time: float = 4.0
var ignite_dps: float = 18.0
var shooter: Node
var age: float = 0.0
var _flames: CPUParticles3D
var _embers: CPUParticles3D
var _light: OmniLight3D
var _tick: float = 0.0
var _lit: Array[Node] = []
var _sound: AudioStreamPlayer3D


## A patch at `at` (on the ground), from `cfg`.
static func spawn(parent: Node, at: Vector3, normal: Vector3, cfg: ThrowerConfig, from: Node) -> FirePatch:
	while active.size() >= MAX:
		var old: FirePatch = active.pop_front()
		if is_instance_valid(old):
			old.queue_free()
	var f: FirePatch = FirePatch.new()
	f.radius = cfg.fire_radius
	f.lifetime = cfg.fire_time
	f.dps = cfg.fire_dps
	f.ignite_time = cfg.ignite_time
	f.ignite_dps = cfg.ignite_dps
	f.shooter = from
	parent.add_child(f)
	f.global_position = at + normal * 0.02
	active.append(f)
	Fx.scorch(at, normal, cfg.fire_radius * 1.6, 0.85)
	return f


## True if `p` is inside a burning patch (flat distance, near its height).
static func burning_at(p: Vector3, margin: float = 0.0) -> FirePatch:
	for f: FirePatch in active:
		if is_instance_valid(f) and f.covers(p, margin):
			return f
	return null


func covers(p: Vector3, margin: float = 0.0) -> bool:
	var d: Vector3 = p - global_position
	return absf(d.y) < 1.4 and Vector2(d.x, d.z).length() < current_radius() + margin


func current_radius() -> float:
	return radius * clampf(age / 0.5, 0.3, 1.0) * (clampf((lifetime - age) / 2.0, 0.0, 1.0) * 0.5 + 0.5)


func _ready() -> void:
	add_to_group(&"fire_patches")
	_flames = CPUParticles3D.new()
	_flames.amount = 64
	_flames.lifetime = 0.9
	_flames.local_coords = false
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2.ONE
	_flames.mesh = q
	_flames.material_override = Fx.fire_material()
	_flames.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	_flames.emission_sphere_radius = radius * 0.3
	_flames.direction = Vector3.UP
	_flames.spread = 12.0
	_flames.gravity = Vector3(0, 2.4, 0)
	_flames.initial_velocity_min = 0.4
	_flames.initial_velocity_max = 1.4
	_flames.scale_amount_min = 0.3
	_flames.scale_amount_max = 0.7
	_flames.scale_amount_curve = Fx.fire_shrink_curve()
	_flames.color_ramp = Fx.fire_ramp()
	_flames.scale = Vector3(1.0, 0.25, 1.0)
	add_child(_flames)
	_embers = CPUParticles3D.new()
	_embers.amount = 18
	_embers.lifetime = 1.6
	_embers.local_coords = false
	var e: QuadMesh = QuadMesh.new()
	e.size = Vector2.ONE * 0.03
	_embers.mesh = e
	_embers.material_override = Fx.fire_material()
	_embers.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	_embers.emission_sphere_radius = radius * 0.6
	_embers.direction = Vector3.UP
	_embers.spread = 30.0
	_embers.gravity = Vector3(0, 1.0, 0)
	_embers.initial_velocity_min = 1.0
	_embers.initial_velocity_max = 2.6
	add_child(_embers)
	_light = OmniLight3D.new()
	_light.light_color = Color(1.0, 0.55, 0.2)
	_light.omni_range = radius * 2.6
	_light.light_energy = 2.0
	_light.shadow_enabled = false
	_light.position = Vector3.UP * 0.6
	add_child(_light)
	_sound = AudioStreamPlayer3D.new()
	_sound.bus = &"SFX"
	_sound.unit_size = 6.0
	_sound.max_distance = 50.0
	var bank: Array = Sfx.bank(&"fire_loop")
	if bank.is_empty():
		bank = Sfx.bank(&"burn")
	if not bank.is_empty():
		var first: Resource = bank[0]
		var st: AudioStreamWAV = first as AudioStreamWAV
		if st:
			st = st.duplicate() as AudioStreamWAV
			st.loop_mode = AudioStreamWAV.LOOP_FORWARD
			st.loop_begin = 0
			st.loop_end = int(st.get_length() * float(st.mix_rate))
			_sound.stream = st
		else:
			_sound.stream = bank[0]
		add_child(_sound)
		_sound.play()
	Sfx.play_at(&"molotov_burst", global_position + Vector3.UP * 0.3, 3.0, 0.08)


func _exit_tree() -> void:
	active.erase(self)


func _physics_process(delta: float) -> void:
	age += delta
	var r: float = current_radius()
	_flames.emission_sphere_radius = r * 0.55
	_embers.emission_sphere_radius = r * 0.6
	var fade: float = clampf((lifetime - age) / 2.0, 0.0, 1.0)
	_flames.scale_amount_max = 0.7 * fade + 0.05
	_flames.scale_amount_min = 0.3 * fade + 0.02
	_light.light_energy = (1.6 + 0.6 * sin(age * 23.0) + 0.4 * sin(age * 7.3)) * fade
	if _sound and _sound.playing:
		_sound.volume_db = linear_to_db(maxf(fade, 0.001)) - 2.0
	if age >= lifetime:
		queue_free()
		return
	_tick -= delta
	if _tick > 0.0:
		return
	_tick = 0.2
	var p: Player = get_tree().get_first_node_in_group(&"player") as Player
	if p and not p.dead and covers(p.global_position):
		var per_kj: float = p.body.stat(&"damage_per_kj") if p.body else Player.BASE_DAMAGE_PER_KJ
		p.take_damage(dps * 0.2 * per_kj / Player.BASE_DAMAGE_PER_KJ, Vector3.DOWN)
		p.add_shake(0.08)
	for n: Node in get_tree().get_nodes_in_group(&"triad"):
		var en: Enemy = n as Enemy
		if en == null or not en.alive or en in _lit:
			continue
		if covers(en.global_position):
			_lit.append(en)
			en.ignite(ignite_time, ignite_dps, shooter)
