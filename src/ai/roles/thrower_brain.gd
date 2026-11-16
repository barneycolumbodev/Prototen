class_name ThrowerBrain
extends RefCounted
## Throwing (ThrowerConfig): the Firebomber's molotovs (docs/design.md
## §8.8c) and the anti-augment specialist's EMP grenades (§8.8g).
##
## - A throw goes at where the operative will be when it lands (he leads a
##   moving target), or where he was last seen: a bottle lobbed over cover
##   doesn't need a line of sight. It arcs (flight time from the distance),
##   lands a little off (spread), and he has to stand up and wind up to do
##   it: the window to shoot him.
## - Enough damage in the windup (interrupt) and he drops it: a lit bottle
##   breaks at his own feet.
## - The Firebomber (EnemyConfig.throw_only) fights by throwing alone: he
##   keeps his distance from cover to cover, pops up to throw, and runs when
##   he's out of bottles. The specialist throws between bursts of his rifle.

var e: Enemy
var cfg: EnemyConfig
var tcfg: ThrowerConfig
var left: int = 0
var thrown: int = 0
var drops: int = 0
## Seconds to the next throw.
var cool: float = 0.0
var winding: bool = false
var last: ThrownProjectile
var _t: float = 0.0
var _target: Vector3 = Vector3.INF
var _hurt: float = 0.0
var _known_for: float = 0.0
var _rag: CPUParticles3D
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(enemy: Enemy) -> void:
	e = enemy
	cfg = enemy.config
	tcfg = cfg.thrower
	left = tcfg.count
	_rng.randomize()
	cool = tcfg.first_delay


func out_of_throws() -> bool:
	return tcfg.count > 0 and left <= 0


func is_busy() -> bool:
	return winding


## Every physics frame he's in COMBAT (before shooting, for the specialist).
## Returns true while a throw is under way (nothing else this frame).
func update(delta: float) -> bool:
	var p: Player = _player()
	if winding:
		_wind(p, delta)
		return true
	if p == null or out_of_throws():
		return false
	if e.last_known != Vector3.INF:
		_known_for += delta
	cool -= delta
	if cool > 0.0 or _known_for < tcfg.first_delay:
		return false
	var target: Vector3 = p.global_position if e.sees_player else e.last_known
	if target == Vector3.INF or (not e.sees_player and e._unseen_for > 8.0):
		return false
	var d: float = _flat(target - e.global_position).length()
	if d < tcfg.min_range or d > tcfg.max_range:
		return false
	_start(p, target)
	return true


func _start(p: Player, target: Vector3) -> void:
	winding = true
	_t = 0.0
	_hurt = 0.0
	_target = target
	e._stop()
	e.tactic = Enemy.Tactic.PEEK
	var lob: bool = not cfg.throw_only
	if cfg.throw_only:
		e.body.set_stance(&"loco")
	e.body.play_throw(lob, tcfg.release_time)
	if tcfg.kind == ThrowerConfig.Kind.MOLOTOV:
		_light_rag(true)
		Sfx.play_at(&"burn", e.body.muzzle_transform().origin, -6.0, 0.1)
	if _rng.randf() < 0.6:
		e._callout(&"fire" if tcfg.kind == ThrowerConfig.Kind.MOLOTOV else &"emp")


func _wind(p: Player, delta: float) -> void:
	_t += delta
	# Face where it's going (he turns while he winds up, but only so fast).
	var to: Vector3 = _flat(_target - e.global_position)
	if to.length() > 0.1:
		e._turn_toward(atan2(to.x, to.z), delta)
	e.body.set_aim(0.0, 0.0, 0.0)
	if p and e.sees_player:
		_target = _target.lerp(p.global_position, minf(delta * 3.0, 1.0))
	if _t >= tcfg.release_time:
		winding = false
		_release(p)


func _release(p: Player) -> void:
	_light_rag(false)
	var from: Vector3 = _hand()
	var aim: Vector3 = _target
	var dist: float = _flat(aim - from).length()
	var flight: float = maxf(tcfg.flight_per_10m * dist / 10.0, 0.35)
	if p and e.sees_player:
		aim += _flat(p.velocity) * flight * tcfg.lead
	var off: float = tcfg.spread * dist / 20.0
	aim += Vector3(_rng.randf_range(-off, off), 0.0, _rng.randf_range(-off, off))
	var v: Vector3 = solve(from, aim, flight)
	last = ThrownProjectile.launch(e.get_parent(), from, v, tcfg, e)
	thrown += 1
	if tcfg.count > 0:
		left -= 1
	cool = _rng.randf_range(tcfg.cooldown.x, tcfg.cooldown.y)
	Sfx.play_at(&"mw7_swish", from, -4.0, 0.1)
	if cfg.throw_only and out_of_throws():
		# Nothing left to throw: he runs.
		e.morale = minf(e.morale, 0.15)


## Initial velocity to go from `a` to `b` in `t` seconds under gravity.
static func solve(a: Vector3, b: Vector3, t: float) -> Vector3:
	var g: Vector3 = Vector3.DOWN * ThrownProjectile.GRAVITY
	return (b - a - 0.5 * g * t * t) / t


## Damage while he winds up: enough and he drops it. Returns true if he did.
func on_hurt(damage: float) -> bool:
	if not winding:
		return false
	_hurt += damage
	if _hurt < tcfg.interrupt:
		return false
	drop_it()
	return true


## The throw goes wrong (hit in the windup, killed): it falls at his feet.
func drop_it() -> void:
	if not winding:
		return
	winding = false
	drops += 1
	e.body.cancel_chop()
	_light_rag(false)
	if tcfg.count > 0:
		left -= 1
	cool = _rng.randf_range(tcfg.cooldown.x, tcfg.cooldown.y)
	var at: Vector3 = e.global_position + e.global_basis.z * 0.4
	if tcfg.kind == ThrowerConfig.Kind.MOLOTOV:
		Sfx.play_at(&"molotov_break", at + Vector3.UP * 0.3, 2.0, 0.1)
		FirePatch.spawn(e.get_parent(), at, Vector3.UP, tcfg, e)
	else:
		last = ThrownProjectile.launch(e.get_parent(), at + Vector3.UP * 0.5, Vector3(0, -1, 0), tcfg, e)


## Where it leaves his hand.
func _hand() -> Vector3:
	return e.body.bone_position(&"hand.R") if cfg.throw_only else e.body.bone_position(&"hand.L")


## The rag on the bottle in his hand (the Firebomber's gun model is the bottle).
func _light_rag(on: bool) -> void:
	if tcfg.kind != ThrowerConfig.Kind.MOLOTOV:
		return
	if _rag == null and on and e.body.gun:
		_rag = CPUParticles3D.new()
		_rag.amount = 14
		_rag.lifetime = 0.35
		_rag.local_coords = false
		var q: QuadMesh = QuadMesh.new()
		q.size = Vector2.ONE
		_rag.mesh = q
		_rag.material_override = Fx.fire_material()
		_rag.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
		_rag.emission_sphere_radius = 0.02
		_rag.direction = Vector3.UP
		_rag.spread = 20.0
		_rag.gravity = Vector3(0, 1.6, 0)
		_rag.initial_velocity_min = 0.2
		_rag.initial_velocity_max = 0.5
		_rag.scale_amount_min = 0.05
		_rag.scale_amount_max = 0.11
		_rag.color_ramp = Fx.fire_ramp()
		e.body.gun.add_child(_rag)
		# The rag's end, in the bottle model's space (raw_assets/weapons/enemy_melee "molotov").
		_rag.position = Vector3(-0.07, -0.16, 0.0)
	if _rag:
		_rag.emitting = on


func _player() -> Player:
	return e.squad.player() if e.squad else null


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)
