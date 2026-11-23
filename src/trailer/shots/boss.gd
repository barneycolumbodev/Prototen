extends TrailerShot
## scene: res://src/levels/hotel/hotel.tscn
## frames: 465
## The Incense Master in the Golden Dragon's atrium: he charges the Gauss
## prosthetic, takes the Governor, goes down on one knee, and the operative
## executes him (RB): the punches, the head goes, the fist shaken off.
## The edit uses two pieces: the charge and the shots, then the execution.

var boss: Enemy
var _down: int = -1
var _exec: int = -1
var _shots: int = 0
var _last_shot: int = -100
const BOSS_AT: Vector3 = Vector3(-1.8, 0.0, -2.2)


func setup() -> void:
	length = 900
	loadout(["rx9_reflex_overclock"])
	gun("The Governor")
	place_player(bv(-1.8, -5.4), BOSS_AT + Vector3.UP * 1.6)
	boss = Enemy.new()
	boss.config = load("res://data/enemies/incense_master.tres") as EnemyConfig
	boss.look_seed = 5
	squad.add(boss)
	map.add_child(boss)
	boss.global_position = BOSS_AT
	boss.face(0.0)
	boss.awareness = 1.0
	boss.last_known = player.global_position
	boss._enter(Enemy.State.COMBAT)
	boss.boss.phase = BossBrain.Phase.STAGGER
	boss.boss._t = -99.0
	men.append(boss)


func step() -> void:
	var b: BossBrain = boss.boss
	if _down < 0:
		aim(boss.body.chest_position() + Vector3.UP * 0.15, 8.0)
	if f == 12:
		b._start_cannon()
		print("trailer: cannon at ", f)
	# Rounds into him while it charges.
	var w: PlayerWeapon = player.weapon()
	if _down < 0 and f > 40 and _shots < 3 and w.lever_t < 0.0 and w._lever_wait < 0.0 and f - _last_shot > 24:
		trigger(true)
		_last_shot = f
		_shots += 1
		print("trailer: governor at %d, boss hp %.0f" % [f, boss.health])
	elif f == _last_shot + 2:
		trigger(false)
	if _down < 0 and f > 40 and (_shots >= 3 and f > _last_shot + 30):
		_down = f
		boss.health = 1.0
		boss.die(null, &"chest")
		print("trailer: down at ", f)
	if _down > 0 and f == _down + 50:
		# Cut point in the edit: the operative steps up to him.
		player.global_position = BOSS_AT + Vector3(0.0, 0.0, 2.8)
		player.velocity = Vector3.ZERO
		player.reset_camera_smoothing()
		stop_aim()
		player.set_view(0.0, -0.12)
		print("trailer: step up at ", f)
	if _down > 0 and f == _down + 100:
		var ex: BossExecution = b.execution
		print("trailer: execution can start %s" % (ex.can_start() if ex else false))
		if ex:
			ex.script_start()
			_exec = f
			print("trailer: execution at ", f)
	if _exec > 0:
		var ex2: BossExecution = b.execution
		if ex2 and ex2.head_gone and f % 10 == 0:
			print("trailer: head gone by ", f)
		if ex2 and ex2.done:
			print("trailer: execution done at ", f)
			finish()
