class_name ShieldBrain
extends RefCounted
## The Shield man (docs/design.md §8.8e): a stolen police ballistic shield
## and a Type 54. He walks the shield at the operative, turns it after him
## (only so fast: flanking works), and fires the pistol round its right edge.
## Men with guns near him fall in behind it (Squad.stack_point).
##
## - The shield is a hitbox of its own on his chest (surface
##   ballistic_shield: ~8 kJ to get through, so the GX-4's slug does and
##   nothing else carried does). Every round on it is felt: a heavy one
##   (stagger_energy) knocks it aside and he staggers, open, for stagger_time.
## - It wears out: past `integrity` J it cracks and he throws it down; with
##   the shield gone his nerve goes with it.
## - What it doesn't cover: his legs and feet, his sides and back, anything
##   that comes over the top (the M32's airburst, the drone, the setae's
##   marks). The slide launches him like anyone, shield and all; the mesh
##   arm tears him away from it.
## - Too close and he bashes you back with it.
## Tuning: data/enemies/shield_man.tres (ShieldConfig).

var e: Enemy
var cfg: EnemyConfig
var scfg: ShieldConfig
var plate: StaticBody3D
var has_shield: bool = true
var absorbed: float = 0.0
var hits: int = 0
var staggers: int = 0
var bashes: int = 0
var _stagger: float = 0.0
var _bash_cool: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(enemy: Enemy) -> void:
	e = enemy
	cfg = enemy.config
	scfg = cfg.shield
	_rng.randomize()


## The shield's hitbox on the chest bone.
func build() -> void:
	plate = StaticBody3D.new()
	plate.name = "Shield"
	plate.collision_layer = Ballistics.LAYER_HITBOX
	plate.collision_mask = 0
	plate.set_meta(&"surface", &"ballistic_shield")
	plate.set_meta(&"dynamic_holes", true)
	plate.set_meta(&"armor", true)
	plate.set_meta(&"shield", true)
	plate.set_script(preload("res://src/ai/armor_plate.gd"))
	plate.set(&"target", e)
	var cs: CollisionShape3D = CollisionShape3D.new()
	var b: BoxShape3D = BoxShape3D.new()
	b.size = scfg.box_size
	cs.shape = b
	plate.add_child(cs)
	plate.position = scfg.box_center
	e.body.bone_attachment(&"chest").add_child(plate)
	e.body.add_plate(plate)


func is_staggered() -> bool:
	return _stagger > 0.0


## A round hit the shield (Enemy.on_plate_hit).
func on_shield_hit(hit: BallisticHit) -> void:
	if not has_shield or not e.alive:
		return
	hits += 1
	absorbed += hit.energy_in
	e._alerted_by(hit.shooter)
	e.body.flinch(hit.direction, clampf(hit.energy_in / 2500.0, 0.15, 1.4), false)
	if hit.energy_in >= scfg.stagger_energy and _stagger <= 0.0:
		staggers += 1
		_stagger = scfg.stagger_time
		e.body.play_stumble()
		e.vocal(&"enemy_pain", -1.0, 0.1)
	if absorbed >= scfg.integrity:
		throw_down(hit.direction * 1.5 + Vector3.UP * 1.5)
		e.speak(&"limb_off")
		e.morale = minf(e.morale, 0.15)
	elif hit.result == BallisticHit.Result.PENETRATED:
		e.suppression = minf(e.suppression + 0.3, 1.0)


## The shield comes off: dropped into the level (he died, it broke, the mesh arm took him).
func throw_down(velocity: Vector3) -> void:
	if not has_shield:
		return
	has_shield = false
	if plate:
		plate.collision_layer = 0
	if e.gear:
		var level: Node = e.get_parent()
		e.gear.drop(&"shield", level, velocity, 7.0, scfg.box_size, scfg.box_center)
	e.body.stance_override = &"rifle"
	e.body.set_stance(&"loco")


## On the enemy's think tick in COMBAT.
func decide() -> void:
	var p: Player = _player()
	if p == null:
		return
	if not has_shield:
		e._decide_combat()
		return
	var d: float = _flat(p.global_position - e.global_position).length()
	e.tactic = Enemy.Tactic.ADVANCE
	if _stagger > 0.0:
		e._stop()
		return
	if e.sees_player and _rng.randf() < 0.12:
		e._callout(&"shield")
	var target: Vector3 = p.global_position if e.sees_player or e.last_known == Vector3.INF else e.last_known
	if d > scfg.hold_range or not e.sees_player:
		e._go(target + (e.global_position - target).normalized() * minf(scfg.hold_range * 0.8, d))
	else:
		e._stop()


## Every physics frame in COMBAT: turn the shield after him, fire, bash.
func act(delta: float) -> void:
	var p: Player = _player()
	_stagger = maxf(0.0, _stagger - delta)
	_bash_cool = maxf(0.0, _bash_cool - delta)
	if not has_shield:
		return
	e.body.set_stance(&"loco")
	if p == null:
		return
	var look_at_pos: Vector3 = p.camera().global_position - Vector3.UP * 0.3 if e.sees_player else e.last_known + Vector3.UP * 1.3
	if e.last_known == Vector3.INF and not e.sees_player:
		return
	var to: Vector3 = look_at_pos - e.body.chest_position()
	var want_yaw: float = atan2(to.x, to.z)
	if _stagger <= 0.0:
		e._yaw = rotate_toward(e._yaw, want_yaw, deg_to_rad(scfg.turn_deg) * delta)
		e.rotation.y = e._yaw
	var rel: float = wrapf(want_yaw - e._yaw, -PI, PI)
	# The pistol swings round the edge; the shield (on the chest) follows only part of it.
	e.body.set_aim(clampf(rel, -0.5, 0.5), atan2(to.y, Vector2(to.x, to.z).length()), 0.7)
	var d: float = _flat(p.global_position - e.global_position).length()
	if d <= scfg.bash_range and _bash_cool <= 0.0 and _stagger <= 0.0 and absf(rel) < 0.6 and not p.dead:
		_bash(p)
		return
	if _stagger <= 0.0 and absf(rel) < 0.35 and e.has_gun:
		e._try_fire(p, delta)


## Shoves the operative back with the shield.
func _bash(p: Player) -> void:
	bashes += 1
	_bash_cool = scfg.bash_cooldown
	var dir: Vector3 = _flat(p.global_position - e.global_position).normalized()
	e.body.flinch(-dir, 1.5, false)
	var dealt: float = p.on_melee_hit(e, scfg.bash_damage, dir, scfg.bash_push)
	if dealt > 0.0:
		Sfx.play_at(&"impact_metal", p.camera().global_position, 3.0, 0.1)
		p.add_shake(0.5)
		for pad: int in Input.get_connected_joypads():
			Input.start_joy_vibration(pad, 0.6, 0.9, 0.2)


## The speed he walks the shield forward at (Enemy._move).
func speed() -> float:
	return cfg.walk_speed * (0.5 if e.limping else 1.0) * (0.0 if _stagger > 0.0 else 1.0)


func _player() -> Player:
	return e.squad.player() if e.squad else null


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)
