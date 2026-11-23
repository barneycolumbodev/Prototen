extends TrailerShot
## scene: res://src/levels/hotel/hotel.tscn
## frames: 135
## The Golden Dragon's atrium, under the chandeliers: the operative comes
## through the arch from the entrance hall at a run, jumps, pops RX-9 and
## dropkicks the gunman at the fortifications into the man behind him,
## then shoots him with the Governor while both are still in the air.

var a: Enemy
var b: Enemy
var c: Enemy
var _jump: int = -1
var _impact: int = -1
var _shots: int = 0
var _last_shot: int = -100


func setup() -> void:
	length = 700
	loadout(["rx9_reflex_overclock"], ["hm5_hydraulic_myomer"])
	gun("The Governor")
	var start: Vector3 = bv(0.3, -12.0)
	a = spawn("gunman", bv(-1.9, -1.6), start, 7)
	b = spawn("gunman", bv(-1.2, 1.3), start, 10)
	c = spawn("gunman", bv(2.4, 3.2), start, 1)
	place_player(start, a.body.chest_position())
	for e: Enemy in [a, b, c]:
		alert(e)
	EventBus.dropkick_impact.connect(func(_v: Node, _p: float) -> void:
		if _impact < 0:
			_impact = f
			print("trailer: impact at ", f))


func _ready_to_fire() -> bool:
	var w: PlayerWeapon = player.weapon()
	return w.lever_t < 0.0 and w._lever_wait < 0.0 and f - _last_shot > 10


func step() -> void:
	if _jump < 0:
		for e: Enemy in [a, c]:
			if e.alive and (f + e.look_seed * 3) % 13 == 0 and f > 6:
				enemy_fire(e, player.camera().global_position + Vector3(0.4, -0.2, 0.0), 2.5)
	if f == 3:
		press(&"move_forward")
		tap(&"sprint")
	if _jump < 0:
		aim(a.body.chest_position(), 10.0)
		if player.global_position.distance_to(a.global_position) < 5.2:
			_jump = f
			tap(&"jump")
			print("trailer: jump at ", f)
		return
	var sj: int = f - _jump
	if sj < 70 and sj % 2 == 0:
		var to: Vector3 = a.global_position - player.global_position
		print("trailer: sj %d phase %d dist %.2f dy %.2f a.launched %s hp %.0f ts %.2f" % [sj, player._dk_phase, Vector2(to.x, to.z).length(), to.y, a.launched, a.health, Engine.time_scale])
	if sj == 4:
		use_part("rx9_reflex_overclock")
	if sj == 9:
		tap(&"jump")
	if sj == 14:
		release(&"move_forward")
	if _impact < 0:
		aim(a.body.chest_position(), 14.0)
		return
	var since: int = f - _impact
	var target: Enemy = a
	if not a.alive:
		aim(a.global_position + Vector3.UP * 0.4, 5.0)
		if since > 200:
			finish()
		return
	aim(target.body.chest_position(), 18.0)
	if since > 14 and _ready_to_fire() and _shots < 4:
		trigger(true)
		_last_shot = f
		_shots += 1
		print("trailer: governor %d at %d on %s (%.1f m up)" % [_shots, f, target.name, target.global_position.y])
	elif f == _last_shot + 2:
		trigger(false)
	if since > 320:
		finish()
