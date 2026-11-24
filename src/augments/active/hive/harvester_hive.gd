class_name HarvesterHive
extends ActivePart
## HV-3 Harvester Hive (HarvesterHiveData; owner, 2026-11-24; docs/design.md
## §3.4e). A hive in the left hand: an emergency heal that kills.
##
## LB (with it selected) picks whoever is nearest the crosshair (in reach,
## in sight) and raises the left hand: the forearm comes up palm-up, the
## iris in the palm blooms open, the wrist snaps back and the open vent
## faces him (the deploy clip, 0.35 s). Then (OUT) a few hundred harvester
## microdrones pour out of the palm in a stream that fans and bends, and
## (FEEDING) wrap him: he's out of the fight at once (the gun drops, he
## claws at himself screaming), and in 0.7 s they strip his clothes and
## skin away to the muscle (EnemyBody.set_flay). He drops, flayed. (RETURN)
## They stream back into the palm, dark and red with what they carry, and as
## they dock the hive's reactor turns it into repair nanites: 38 % of max
## health comes back over the last fraction of a second, the cells on the
## back of the hand lighting one by one. Then the vent closes and the gun
## comes back up.
##
## Whoever sees it loses his nerve. A boss isn't stripped whole: a third of
## him, a chunk of damage, the full heal. One swarm; the hive rebuilds it in
## about 22 s, faster with more cooling (the reactor's heat has to go).
## Stats: connectivity extends the reach; cooling the rebuild; the heal is a
## share of max health.

enum Phase { READY, OUT, FEEDING, RETURN, DONE }

const OVERLAY_SHADER: String = """
shader_type canvas_item;
uniform vec4 tint : source_color = vec4(0.9, 0.12, 0.08, 0.55);
uniform float amount = 0.0;
void fragment() {
	vec2 d = UV - 0.5;
	d.x *= 1.7;
	float r = length(d);
	// A rush of blood in from the edges.
	float edge = smoothstep(0.3, 0.95, r);
	COLOR = vec4(tint.rgb, clamp(edge * tint.a * amount, 0.0, 0.8));
}
"""


## The bracket on the target, the stripping progress, "NO TARGET" when there's nobody to take.
class TargetView:
	extends Control
	var part: HarvesterHive
	var font: Font
	var denied: float = 0.0
	var t: float = 0.0

	func _draw() -> void:
		var p: HarvesterHive = part
		if p.player == null:
			return
		var cam: Camera3D = p.player.camera()
		var vp: Vector2 = get_viewport_rect().size
		var col: Color = p.cfg.glow_color
		if denied > 0.0:
			draw_string(font, Vector2(0, vp.y * 0.5 + 48.0), "NO TARGET", HORIZONTAL_ALIGNMENT_CENTER, vp.x, 15, Color(col, denied))
		var tgt: Node3D = p.target if p.is_running() else p.hover
		if tgt == null or not is_instance_valid(tgt):
			return
		var at: Vector3 = HarvesterHive.chest_of(tgt)
		if cam.is_position_behind(at):
			return
		var sp: Vector2 = cam.unproject_position(at)
		var dist: float = cam.global_position.distance_to(at)
		var r: float = clampf(260.0 / maxf(dist, 1.0), 16.0, 64.0)
		var live: bool = p.is_running()
		var a: float = 0.95 if live else 0.45
		# A hex bracket that turns as it locks.
		var spin: float = t * (2.4 if live else 0.6)
		var pts: PackedVector2Array = PackedVector2Array()
		for k: int in 7:
			pts.append(sp + Vector2.from_angle(spin + k * TAU / 6.0) * r)
		for k: int in 6:
			var a0: Vector2 = pts[k]
			var a1: Vector2 = pts[k + 1]
			draw_line(a0, a0.lerp(a1, 0.3), Color(col, a), 2.0, true)
			draw_line(a1, a1.lerp(a0, 0.3), Color(col, a), 2.0, true)
		if p.phase == HarvesterHive.Phase.FEEDING or p.phase == HarvesterHive.Phase.RETURN:
			# How far they've stripped him.
			var k2: float = clampf(p.flay_now / maxf(p.flay_goal(), 0.01), 0.0, 1.0)
			draw_arc(sp, r + 6.0, -PI * 0.5, -PI * 0.5 + TAU * k2, 40, Color(col, 0.9), 3.0, true)
		var label: String = "HARVEST  %dm" % roundi(dist) if p.phase != HarvesterHive.Phase.RETURN else "HARVESTED"
		if not live:
			label = "LB  HARVEST"
		draw_string(font, sp + Vector2(r + 8.0, -r * 0.5), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(1, 1, 1, a * 0.85))


var cfg: HarvesterHiveData
var rig: ArmRig
var weapon: WeaponData
var swarm: HarvesterSwarm
var phase: Phase = Phase.READY
## Who the swarm is for (an Enemy or an AttackDog), and who LB would take right now.
var target: Node3D
var hover: Node3D
## World seconds since the swarm left the vent (-1: in the hive).
var swarm_t: float = -1.0
## How far he's stripped (0..1), what's been healed this harvest, and in all.
var flay_now: float = 0.0
var healed: float = 0.0
var harvests: int = 0

var _t_out: float = 0.3
var _t_back: float = 0.3
var _t_ret: float = 1e6
var _strip_from: float = -1.0
var _goal_heal: float = 0.0
var _engulfed: bool = false
var _bitten: Vector3 = Vector3.INF
var _gore_t: float = 0.0
var _vent: Node3D
var _glow: StandardMaterial3D
var _cells: Array[StandardMaterial3D] = []
var _lit_cells: int = 6
var _buzz: AudioStreamPlayer3D
var _layer: CanvasLayer
var _view: TargetView
var _overlay: ColorRect
var _pulse: float = 0.0
var _steam: Array[Node3D] = []
var _steam_t: Array[float] = []
var _script_target: Node3D
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	super._ready()
	cfg = data as HarvesterHiveData
	_rng.randomize()
	weapon = AugHit.weapon_named("HV-3 Harvester Hive")
	rig = ArmRig.make(player, cfg.scene, cfg.viewmodel, "HiveRig")
	if player == null:
		add_child(rig)
	_vent = rig.part("vent")
	_glow = rig.drive("glow")
	if _glow:
		_glow.emission = cfg.glow_color
		_glow.emission_energy_multiplier = 0.3
	for k: int in 6:
		var m: StandardMaterial3D = rig.drive("cell%d" % k)
		if m:
			m.emission = cfg.glow_color
			_cells.append(m)
	swarm = HarvesterSwarm.new()
	swarm.setup(cfg.count, cfg)
	add_child(swarm)
	_buzz = AudioStreamPlayer3D.new()
	_buzz.bus = &"SFX"
	_buzz.unit_size = 5.0
	_buzz.max_distance = 60.0
	var loop: Array = Sfx.bank(&"hv3_swarm")
	if not loop.is_empty():
		_buzz.stream = loop[0]
	add_child(_buzz)
	_build_hud()
	state_changed.connect(_on_state_changed)


func _exit_tree() -> void:
	super._exit_tree()
	if is_instance_valid(rig) and rig.get_parent() != self:
		rig.queue_free()


func hand() -> StringName:
	return &"left"


func hud_pips() -> int:
	return roundi(charge_capacity())


func _drain(_real: float) -> void:
	pass


## How far the swarm reaches: connectivity extends it.
func reach() -> float:
	var c: float = body.stat(&"connectivity") if body else 0.0
	return minf(cfg.reach + cfg.reach_per_link * c, cfg.reach_max)


## The hive rebuilds the swarm faster the more heat the body can shed.
func regen_scale() -> float:
	if body == null:
		return 1.0
	return clampf(body.stat(&"heat_dissipation_w") / maxf(cfg.cooling_ref_w, 1.0), cfg.regen_min_scale, cfg.regen_max_scale)


## Health a full harvest gives back.
func heal_amount() -> float:
	var m: float = player.max_health() if player else 200.0
	return m * cfg.heal_share


## How far this target gets stripped (a boss only partly).
func flay_goal() -> float:
	var e: Enemy = target as Enemy
	return cfg.boss_flay if e and e.boss else 1.0


func is_feeding() -> bool:
	return phase == Phase.FEEDING


## The swarm is out (between leaving the palm and the last one docking).
func swarm_out() -> bool:
	return phase == Phase.OUT or phase == Phase.FEEDING or phase == Phase.RETURN


## Sends the swarm at `t` instead of whoever is under the crosshair (tests, demos).
func script_target(t: Node3D) -> void:
	_script_target = t


# ------------------------------------------------------------------ targets

## The living enemy (a man or a dog) nearest the crosshair inside the cone, in reach and in sight.
func pick_target() -> Node3D:
	if _script_target and is_instance_valid(_script_target) and _alive(_script_target):
		return _script_target
	if player == null:
		return null
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var fwd: Vector3 = -cam.global_basis.z
	var space: PhysicsDirectSpaceState3D = player.get_world_3d().direct_space_state
	var best: Node3D = null
	var best_ang: float = INF
	var r: float = reach()
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var b: Node3D = n as Node3D
		if b == null or not _alive(b):
			continue
		var at: Vector3 = chest_of(b)
		var to: Vector3 = at - eye
		var d: float = to.length()
		if d > r or d < 0.3:
			continue
		# Wider up close: a man at arm's length fills the view.
		var ang: float = rad_to_deg(fwd.angle_to(to))
		if ang > cfg.cone_deg + 20.0 / maxf(d, 1.0) or ang >= best_ang:
			continue
		var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, at, Ballistics.LAYER_WORLD)
		if not space.intersect_ray(q).is_empty():
			continue
		best_ang = ang
		best = b
	return best


static func _alive(b: Node3D) -> bool:
	var e: Enemy = b as Enemy
	if e:
		return e.alive and not e.held and not e.engulfed and (e.boss == null or not e.boss.is_down())
	var d: AttackDog = b as AttackDog
	return d != null and d.alive and not d.engulfed


static func chest_of(b: Node3D) -> Vector3:
	var e: Enemy = b as Enemy
	if e:
		return e.body.chest_position()
	var d: AttackDog = b as AttackDog
	if d:
		return d.chest_position()
	return b.global_position + Vector3.UP


## The body the swarm wraps, as a capsule: [foot end, head end, radius]. Follows a ragdoll.
static func capsule_of(b: Node3D) -> Array:
	var e: Enemy = b as Enemy
	if e:
		var feet: Vector3 = (e.body.bone_position(&"foot.L") + e.body.bone_position(&"foot.R")) * 0.5
		var head: Vector3 = e.body.head_position()
		return [feet.lerp(head, 0.04), head + (head - feet).normalized() * 0.08, 0.26 * maxf(e.config.body_scale, 1.0)]
	var d: AttackDog = b as AttackDog
	if d:
		var head2: Vector3 = d.head_position()
		var chest: Vector3 = d.chest_position()
		return [chest + (chest - head2).normalized() * 0.55, head2, 0.2]
	return [b.global_position, b.global_position + Vector3.UP * 1.8, 0.3]


# ------------------------------------------------------------------ states

## LB: pick the target and raise the hand; nothing to take, nothing happens. Once
## the swarm is out it comes back by itself.
func toggle() -> void:
	if is_running():
		if phase == Phase.READY:
			stop()
		return
	if can_start():
		var t: Node3D = pick_target()
		if t == null:
			_view.denied = 1.0
			_on_denied()
			return
		target = t
	super.toggle()


func _on_start() -> void:
	phase = Phase.READY
	swarm_t = -1.0
	flay_now = 0.0
	healed = 0.0
	_engulfed = false
	_t_ret = 1e6
	_strip_from = -1.0
	_bitten = Vector3.INF
	rig.extra = Transform3D.IDENTITY
	rig.visible = true
	_set_cells(6)
	Sfx.play_ui(&"hv3_deploy", -2.0, 0.0)
	rumble(0.12, 0.25, 0.3)


func _on_stop() -> void:
	if phase == Phase.READY:
		Sfx.play_ui(&"hv3_stow", -5.0, 0.0)


func _on_denied() -> void:
	Sfx.play_ui(&"hv3_denied", -6.0, 0.0)


func _on_state_changed(s: State) -> void:
	match s:
		State.RECOVERING:
			if phase == Phase.DONE:
				Sfx.play_ui(&"hv3_stow", -5.0, 0.0)
		State.COOLDOWN:
			rig.visible = false
			if phase != Phase.DONE:
				_abort(false)
			phase = Phase.READY


func interrupt() -> void:
	_abort(false)
	super.interrupt()


func _on_blend(a: float) -> void:
	rig.seek(a)
	if _glow:
		_glow.emission_energy_multiplier = 0.3 + 3.2 * a


func _on_active(_real: float) -> void:
	if phase == Phase.READY:
		_launch()


# ------------------------------------------------------------------ the harvest

func _launch() -> void:
	if target == null or not is_instance_valid(target) or not _alive(target):
		target = pick_target()
	if target == null:
		_view.denied = 1.0
		stop()
		return
	phase = Phase.OUT
	harvests += 1
	charge = maxf(charge - 1.0, 0.0)
	_since_stop = 0.0
	swarm_t = 0.0
	_t_ret = 1e6
	var from: Vector3 = vent_position()
	_t_out = maxf(from.distance_to(chest_of(target)) / maxf(cfg.speed_out, 1.0), cfg.min_trip)
	_goal_heal = heal_amount()
	swarm.visible = true
	_push_swarm()
	if _buzz.stream:
		_buzz.global_position = from
		_buzz.play()
	Sfx.play_ui(&"hv3_release", 0.0, 0.03)
	rumble(cfg.rumble_launch.x, cfg.rumble_launch.y, cfg.rumble_launch.z)
	rig.kick_pos.kick(Vector3(0.0, 0.006, -0.03))
	rig.kick_rot.kick(Vector3(deg_to_rad(-4.0), 0.0, 0.0))
	var w: PlayerWeapon = player.weapon()
	if w and w.cam_recoil:
		w.cam_recoil.kick(Vector3(-0.6, 0.4, 0.0))
	EventBus.shot_fired.emit(player, from, (chest_of(target) - from).normalized())


## Where the swarm leaves from and docks: the vent in the palm.
func vent_position() -> Vector3:
	if _vent and _vent.is_inside_tree():
		return _vent.global_position
	if player:
		return player.camera().global_position + player.camera().global_basis * Vector3(-0.2, -0.15, -0.5)
	return Vector3.ZERO


func _vent_dir() -> Vector3:
	var fwd: Vector3 = -player.camera().global_basis.z if player else Vector3.FORWARD
	if _vent and _vent.is_inside_tree():
		return (-_vent.global_basis.y).normalized().lerp(fwd, 0.5).normalized()
	return fwd


func _process(delta: float) -> void:
	super._process(delta)
	var real: float = TimeControl.real_delta(delta)
	if rig.visible:
		rig.tick(real, blend, player)
	if swarm_out():
		swarm_t += delta
		_harvest_frame(delta)
	_update_steam(delta)
	_pulse = maxf(_pulse - real * 1.6, 0.0)
	(_overlay.material as ShaderMaterial).set_shader_parameter(&"amount", _pulse)
	_overlay.visible = _pulse > 0.001
	_view.t += real
	_view.denied = maxf(_view.denied - real * 1.2, 0.0)
	# Show who LB would take while it's selected and ready.
	if not is_running() and player and player.augments and player.augments.selected_part() == self and charge >= data.min_to_start:
		hover = pick_target() if Engine.get_process_frames() % 6 == 0 else hover
	elif not is_running():
		hover = null
	_layer.visible = player != null and not player.dead and (is_running() or hover != null or _view.denied > 0.0 or _pulse > 0.0)
	if _layer.visible:
		_view.queue_redraw()


func _harvest_frame(delta: float) -> void:
	var gone: bool = target == null or not is_instance_valid(target) or _body_gone(target)
	if gone and phase != Phase.RETURN:
		# Nothing left to eat (blown apart): they come home empty, the swarm isn't spent.
		charge = minf(charge + 1.0, charge_capacity())
		_goal_heal = 0.0
		_begin_return()
	match phase:
		Phase.OUT:
			if swarm_t >= _t_out + cfg.engulf_after:
				_begin_feeding()
		Phase.FEEDING:
			_feed(delta)
		Phase.RETURN:
			_return_frame()
	if phase != Phase.DONE:
		_push_swarm()


static func _body_gone(b: Node3D) -> bool:
	var e: Enemy = b as Enemy
	return e != null and e.body.gibbed


func _begin_feeding() -> void:
	phase = Phase.FEEDING
	_strip_from = swarm_t
	_gore_t = 0.0
	var at: Vector3 = chest_of(target)
	var from: Vector3 = vent_position()
	_bitten = at + (from - at).normalized() * 0.12
	var e: Enemy = target as Enemy
	var dog: AttackDog = target as AttackDog
	if e and e.boss == null:
		_engulfed = e.engulf(player)
	elif dog:
		_engulfed = dog.engulf(player)
	_witnesses(at)
	Sfx.play_at(&"hv3_feed", at, 3.0, 0.05)
	rumble(cfg.rumble_feed.x, cfg.rumble_feed.y, cfg.rumble_feed.z)


## Triad who see a man eaten alive lose their nerve; the nearest says so.
func _witnesses(at: Vector3) -> void:
	var nearest: Enemy = null
	var nd: float = INF
	for n: Node in get_tree().get_nodes_in_group(&"triad"):
		var w: Enemy = n as Enemy
		if w == null or w == target or not w.alive or w.boss:
			continue
		var d: float = w.global_position.distance_to(at)
		if d > cfg.witness_m:
			continue
		var k: float = 1.0 - d / cfg.witness_m
		w.morale -= cfg.witness_morale * k
		w.suppression = minf(w.suppression + cfg.witness_suppression * k, 1.0)
		if d < nd:
			nd = d
			nearest = w
	if nearest:
		nearest.speak(&"flee")


func _feed(delta: float) -> void:
	var k: float = clampf((swarm_t - _strip_from) / maxf(cfg.strip_time, 0.01), 0.0, 1.0)
	# Fast at first (clothes and skin), slower into the deep tissue.
	var eased: float = 1.0 - pow(1.0 - k, 1.6)
	flay_now = eased * flay_goal()
	_set_flay(flay_now)
	swarm.set_param(&"squeeze", k)
	_gore_t -= delta
	if _gore_t <= 0.0 and k < 1.0:
		_gore_t = _rng.randf_range(0.05, 0.09)
		_spatter()
	if k >= 1.0:
		_finish_feeding()


func _set_flay(a: float) -> void:
	var e: Enemy = target as Enemy
	if e:
		e.body.set_flay(a, _bitten)
		return
	var dog: AttackDog = target as AttackDog
	if dog:
		dog.set_flay(a, _bitten)


## Blood mist and torn scraps thrown off wherever they're eating.
func _spatter() -> void:
	var e: Enemy = target as Enemy
	var at: Vector3
	if e:
		var zones: Array = e.body.hitboxes.keys()
		var hb: HitboxPart = e.body.hitboxes.get(zones[_rng.randi() % zones.size()])
		if hb == null or not is_instance_valid(hb) or not hb.is_inside_tree():
			return
		at = hb.global_position
	else:
		at = chest_of(target) + Vector3(_rng.randf_range(-0.2, 0.2), _rng.randf_range(-0.2, 0.15), _rng.randf_range(-0.2, 0.2))
	var out: Vector3 = (at - chest_of(target) + Vector3(_rng.randf_range(-0.4, 0.4), 0.3, _rng.randf_range(-0.4, 0.4))).normalized()
	Gore.mist(at, out, 0.9)
	if _rng.randf() < 0.6:
		Gore.spray(at, out, 0.7, 3)


func _finish_feeding() -> void:
	var at: Vector3 = chest_of(target)
	var dir: Vector3 = (at - vent_position()).normalized()
	var e: Enemy = target as Enemy
	var dog: AttackDog = target as AttackDog
	var hit: BallisticHit = _hit(at, dir)
	if e and e.boss:
		# He's too big to eat whole: a chunk of him.
		e.health -= cfg.boss_damage
		e.boss.on_hurt(cfg.boss_damage, hit)
		EventBus.target_hit.emit(&"hit", hit)
		if e.health <= 0.0:
			e.die(hit, &"chest")
	elif e:
		if e.alive:
			e.swarm_kill(hit)
		Gore.mist(at, Vector3.UP, 2.0)
		Gore.pool_under(at, 0.5)
		_steam_on(e.body)
	elif dog:
		if dog.alive:
			dog.swarm_kill(hit)
		Gore.mist(at, Vector3.UP, 1.4)
		_steam_on(dog)
	Sfx.play_at(&"hv3_drop", at, 0.0, 0.08)
	_begin_return()


## A hit record for the kill feed and the kill confirm (nothing is struck).
func _hit(at: Vector3, dir: Vector3) -> BallisticHit:
	var hit: BallisticHit = BallisticHit.new()
	hit.weapon = weapon
	hit.shooter = player
	hit.point = at
	hit.direction = dir
	hit.normal = -dir
	var e: Enemy = target as Enemy
	if e:
		hit.collider = e.body.hitboxes.get(&"chest")
	var d: DamageInfo = DamageInfo.new()
	d.amount = cfg.boss_damage
	d.type = DamageInfo.Type.BLADE
	d.impulse = 1.5
	d.zone = &"chest"
	d.point = at
	d.normal = -dir
	d.source = player
	hit.damage = d
	return hit


func _begin_return() -> void:
	phase = Phase.RETURN
	_t_ret = swarm_t
	var from: Vector3 = chest_of(target) if target and is_instance_valid(target) else vent_position()
	_t_back = maxf(from.distance_to(vent_position()) / maxf(cfg.speed_back, 1.0), cfg.min_trip)
	swarm.set_param(&"squeeze", 1.0)
	Sfx.play_ui(&"hv3_return", -2.0, 0.03)


## They dock over `return_spread` after the trip back; each share heals as it lands.
func _return_frame() -> void:
	var docked: float = clampf((swarm_t - _t_ret - _t_back) / maxf(cfg.return_spread, 0.01), 0.0, 1.0)
	var lit: int = clampi(floori(docked * 6.0 + 0.001), 0, 6)
	if lit > _lit_cells:
		_set_cells(lit)
		rig.kick_pos.kick(Vector3(0.0, 0.0, 0.006))
	if docked > 0.0 and healed <= 0.0 and _goal_heal > 0.0:
		# The first of them home: the reactor kicks in.
		_pulse = 1.0
		Sfx.play_ui(&"hv3_heal", 0.0, 0.0)
		rumble(cfg.rumble_heal.x, cfg.rumble_heal.y, cfg.rumble_heal.z)
	var owed: float = _goal_heal * docked - healed
	if owed > 0.0 and player:
		healed += owed
		player.heal(owed)
	if docked >= 1.0:
		_done()


func _done() -> void:
	phase = Phase.DONE
	swarm.visible = false
	swarm_t = -1.0
	_buzz.stop()
	if body and _goal_heal > 0.0:
		body.heat_j = minf(body.heat_j + cfg.heat_j, body.frame.heat_capacity_j)
	target = null
	stop()


## The swarm is lost (the operative went down, the part was knocked out).
func _abort(_refund: bool) -> void:
	if swarm_out():
		var e: Enemy = target as Enemy
		if e and e.engulfed and e.alive:
			e.swarm_kill(_hit(chest_of(e), Vector3.DOWN))
	swarm.visible = false
	swarm_t = -1.0
	_buzz.stop()
	if phase != Phase.READY:
		phase = Phase.DONE
	target = null


func _push_swarm() -> void:
	var from: Vector3 = vent_position()
	swarm.set_param(&"vent", from)
	swarm.set_param(&"vent_dir", _vent_dir())
	swarm.set_param(&"t", swarm_t)
	swarm.set_param(&"t_out", _t_out)
	swarm.set_param(&"t_ret", _t_ret)
	swarm.set_param(&"t_back", _t_back)
	if target and is_instance_valid(target):
		var cap: Array = capsule_of(target)
		swarm.set_param(&"cap_a", cap[0])
		swarm.set_param(&"cap_b", cap[1])
		swarm.set_param(&"cap_r", cap[2])
	if phase == Phase.OUT:
		swarm.set_param(&"squeeze", 0.0)
	# The buzz follows the bulk of them.
	var mid: Vector3 = chest_of(target) if target and is_instance_valid(target) else from
	var k: float = 1.0
	if phase == Phase.OUT:
		k = clampf(swarm_t / maxf(_t_out, 0.01), 0.0, 1.0)
	elif phase == Phase.RETURN:
		k = 1.0 - clampf((swarm_t - _t_ret) / maxf(_t_back + cfg.return_spread, 0.01), 0.0, 1.0)
	_buzz.global_position = from.lerp(mid, k)
	# The cells go dark as they leave.
	if phase == Phase.OUT:
		_set_cells(6 - clampi(floori(swarm_t / maxf(cfg.launch_spread, 0.01) * 6.0), 0, 6))


func _set_cells(n: int) -> void:
	_lit_cells = n
	for k: int in _cells.size():
		_cells[k].emission_energy_multiplier = 2.6 if k < n else 0.04


## The flayed body steams for a few seconds (the Colossal Titan's kind of steam: heat off raw tissue).
func _steam_on(b: Node3D) -> void:
	_steam.append(b)
	_steam_t.append(3.5)


func _update_steam(delta: float) -> void:
	var i: int = _steam.size() - 1
	while i >= 0:
		_steam_t[i] -= delta
		var b: Node3D = _steam[i]
		if _steam_t[i] <= 0.0 or not is_instance_valid(b):
			_steam.remove_at(i)
			_steam_t.remove_at(i)
		elif _rng.randf() < delta * 6.0 and Fx.enabled:
			var at: Vector3 = b.global_position
			if b is EnemyBody:
				at = (b as EnemyBody).chest_position()
			elif b is AttackDog:
				at = (b as AttackDog).chest_position()
			Fx._emit(&"smoke", at + Vector3(_rng.randf_range(-0.25, 0.25), 0.0, _rng.randf_range(-0.25, 0.25)), Vector3.UP,
					Color(0.82, 0.78, 0.76, 0.22 * clampf(_steam_t[i], 0.0, 1.0)), 3, 0.5)
		i -= 1


# ------------------------------------------------------------------ HUD

func _build_hud() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = 5
	_layer.visible = false
	add_child(_layer)
	_overlay = ColorRect.new()
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat: ShaderMaterial = ShaderMaterial.new()
	var sh: Shader = Shader.new()
	sh.code = OVERLAY_SHADER
	mat.shader = sh
	mat.set_shader_parameter(&"tint", cfg.heal_color)
	_overlay.material = mat
	_overlay.visible = false
	_layer.add_child(_overlay)
	_view = TargetView.new()
	_view.part = self
	_view.font = ThemeDB.fallback_font
	_view.set_anchors_preset(Control.PRESET_FULL_RECT)
	_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(_view)
