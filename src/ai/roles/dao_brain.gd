class_name DaoBrain
extends MeleeBrain
## The Dao swordsman (docs/design.md §8.8b): the melee elite. He comes in
## like the Hatchet Man (MeleeBrain: cover to cover, then straight in, over
## low walls), but once he's looked at he walks in behind his guard: the
## steel plate grafted into his left forearm, up across his face. Rounds
## from the front that hit it are turned aside (Ballistics: a collider with
## the "deflects" meta ricochets anything up to DaoConfig.deflect_max).
##
## - The guard takes so much (guard_energy, J of rounds turned aside) before
##   it breaks: he staggers and fights without it for broken_time. It comes
##   back at guard_regen J/s. A round past deflect_max (the GX-4's slug)
##   goes through the plate and breaks it at once.
## - It only covers the front, from the hips up: his legs, his sides and his
##   back are open; flank him, shoot low, or make him attack.
## - His cuts drop the guard: the slash (close: a wide diagonal, 2.3 m) and
##   the lunge (from further out: he covers ~4 m in under half a second, a
##   narrow thrust). Both have a tell; the lunge is the one to sidestep.
## Tuning: data/enemies/dao_swordsman.tres (DaoConfig).

var dcfg: DaoConfig
## J of rounds the guard can still turn aside.
var guard_left: float = 0.0
## Seconds until a broken guard comes back up.
var broken: float = 0.0
var guarding: bool = false
var deflected: int = 0
var guard_breaks: int = 0
var lunges: int = 0
var slashes: int = 0
var guard_box: StaticBody3D
var _lunge: bool = false


func _init(enemy: Enemy) -> void:
	super(enemy)
	dcfg = cfg.dao
	guard_left = dcfg.guard_energy


## The guard's hitbox on the chest bone (on only while he holds the guard).
func build_guard() -> void:
	guard_box = StaticBody3D.new()
	guard_box.name = "Guard"
	guard_box.collision_layer = 0
	guard_box.collision_mask = 0
	guard_box.set_meta(&"surface", &"armor_plate")
	guard_box.set_meta(&"armor", true)
	guard_box.set_meta(&"guard", true)
	guard_box.set_meta(&"deflects", dcfg.deflect_max)
	guard_box.set_script(preload("res://src/ai/armor_plate.gd"))
	guard_box.set(&"target", e)
	var cs: CollisionShape3D = CollisionShape3D.new()
	var b: BoxShape3D = BoxShape3D.new()
	b.size = dcfg.guard_size
	cs.shape = b
	guard_box.add_child(cs)
	guard_box.position = dcfg.guard_center
	e.body.bone_attachment(&"chest").add_child(guard_box)


func reset() -> void:
	super()
	_set_guard(false)


## Every frame he's alive (Enemy._physics_process): the guard's state.
func update_guard(delta: float) -> void:
	if broken > 0.0:
		broken -= delta
	else:
		guard_left = minf(guard_left + dcfg.guard_regen * delta, dcfg.guard_energy)
	var p: Player = _player()
	var want: bool = broken <= 0.0 and e.alive and not e.launched and e.state == Enemy.State.COMBAT \
			and phase in [Phase.APPROACH, Phase.CHARGE, Phase.HOLD] and p != null and e.sees_player \
			and _flat(p.global_position - e.global_position).length() < 24.0
	_set_guard(want)


func _set_guard(on: bool) -> void:
	if on == guarding:
		return
	guarding = on
	e.body.guarding = on
	if on and _rng.randf() < 0.35:
		e._callout(&"challenge")
	if guard_box:
		guard_box.collision_layer = Ballistics.LAYER_HITBOX if on else 0
	# Re-pick the stance so the guard clip comes in (or goes) now.
	if phase in [Phase.APPROACH, Phase.CHARGE]:
		e.body.set_stance(&"run")
	elif phase == Phase.HOLD:
		e.body.set_stance(&"cover")


## A round hit the guard (Enemy.on_plate_hit): turned aside, or through it.
func on_guard_hit(hit: BallisticHit) -> void:
	if not guarding:
		return
	if hit.result == BallisticHit.Result.RICOCHET:
		deflected += 1
		guard_left -= hit.energy_in
		e.body.flinch(hit.direction, clampf(hit.energy_in / 1500.0, 0.2, 1.2), false)
		Sfx.play_at(&"impact_steel", hit.point, 2.0, 0.15)
		if guard_left <= 0.0:
			_break_guard()
	else:
		# Through the plate (or stopped by it, too heavy to turn): the guard's gone.
		_break_guard()


func _break_guard() -> void:
	guard_breaks += 1
	guard_left = 0.0
	broken = dcfg.broken_time
	_set_guard(false)
	e.body.play_stumble()
	e.vocal(&"enemy_pain", 1.0, 0.1)
	if phase == Phase.WINDUP:
		e.body.cancel_chop()
	_enter(Phase.RECOVER, minf(dcfg.broken_time * 0.5, 1.0))


func speed() -> float:
	return (dcfg.guard_speed if guarding else cfg.run_speed) * (0.5 if e.limping else 1.0)


## The slash inside slash_range; the lunge from further out, up to lunge_range.
func _attack_ready(d: float) -> bool:
	if d <= dcfg.slash_range:
		_lunge = false
		atk_windup = dcfg.slash_windup
		atk_reach = dcfg.slash_reach
		atk_arc = dcfg.slash_arc_deg
		atk_damage = dcfg.slash_damage
		atk_lunge = cfg.melee_lunge_speed
		atk_recovery = cfg.melee_recovery
		return true
	if d <= dcfg.lunge_range and e.sees_player:
		_lunge = true
		atk_windup = dcfg.lunge_windup
		atk_reach = dcfg.lunge_reach
		atk_arc = dcfg.lunge_arc_deg
		atk_damage = dcfg.lunge_damage
		atk_lunge = dcfg.lunge_speed
		atk_recovery = cfg.melee_recovery + 0.2
		return true
	return false


func _play_attack() -> void:
	_set_guard(false)
	if _lunge:
		lunges += 1
	else:
		slashes += 1
	e.body.play_cut(_lunge, atk_windup)


func is_lunging() -> bool:
	return phase == Phase.WINDUP and _lunge
