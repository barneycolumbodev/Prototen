extends TrailerShot
## scene: res://src/levels/chinatown/chinatown.tscn
## frames: 150
## Chinatown street at night: the operative sprints at two gunmen who are
## already firing, kicks RX-9 on, slides into them and launches both into
## the air, brakes, and blasts each with the Saiga-12K while they hang there.

const SAIGA: String = "Saiga-12K"
const START: Vector3 = Vector3(16.0, 0.0, -8.6)
var a: Enemy
var b: Enemy
var _launched_at: int = -1
var _shot_at: Array[int] = []
var _target: Enemy


func setup() -> void:
	length = 520
	loadout(["rx9_reflex_overclock"], ["hm5_hydraulic_myomer"])
	gun(SAIGA)
	a = spawn("gunman", Vector3(5.0, 0.0, -8.55), START, 3)
	b = spawn("gunman", Vector3(2.6, 0.0, -10.0), START, 8)
	place_player(START, Vector3(5.0, 1.3, -8.6))
	for e: Enemy in [a, b]:
		alert(e)


func step() -> void:
	# They open up on him as he comes.
	if f > 6 and _launched_at < 0 and f % 6 == 0:
		enemy_fire(a, player.camera().global_position + Vector3(0.0, -0.2, 0.7), 2.0)
	if f > 9 and _launched_at < 0 and f % 8 == 0:
		enemy_fire(b, player.camera().global_position + Vector3(0.0, -0.1, -0.6), 2.0)
	if f == 4:
		press(&"move_forward")
		tap(&"sprint")
	if _launched_at < 0:
		aim(Vector3(4.5, 1.5, -8.9), 8.0)
	if f == 46:
		tap(&"slide")
	if _launched_at < 0 and (a.launched or b.launched):
		_launched_at = f
		print("trailer: launched at ", f)
	if _launched_at < 0:
		return
	var since: int = f - _launched_at
	if since == 12:
		use_part("rx9_reflex_overclock")
	if since == 3:
		release(&"move_forward")
		press(&"move_back", 60, 1.0)
	# First the higher man, then the other, then whoever is still alive.
	if _shot_at.is_empty():
		_target = a
	elif f == _shot_at[-1] + 1:
		var other: Enemy = b if _target == a else a
		if _shot_at.size() == 2 or not _target.alive:
			if other.alive:
				_target = other
	if _target and is_instance_valid(_target) and _shot_at.size() < 4:
		aim(_target.body.chest_position(), 30.0)
	var w: PlayerWeapon = player.weapon()
	var ready: bool = _shot_at.is_empty() or f - _shot_at[-1] >= 9
	if _target and _shot_at.size() < 4 and ready and since > 10:
		var up: float = _target.global_position.y
		var away: float = _target.global_position.distance_to(player.global_position)
		if (_shot_at.is_empty() and since >= 22) or not _shot_at.is_empty():
			trigger(true)
			_shot_at.append(f)
			print("trailer: fire at %d, %s %.2f m up, %.1f m away" % [f, _target.name, up,
				_target.global_position.distance_to(player.global_position)])
	if not _shot_at.is_empty() and f == _shot_at[-1] + 2:
		trigger(false)
	if not _shot_at.is_empty() and f == _shot_at[-1] + 6:
		print("trailer: after shot %d: a hp %.0f alive %s, b hp %.0f alive %s" % [_shot_at.size(), a.health, a.alive, b.health, b.alive])
	if _shot_at.size() == 4 and f == _shot_at[-1] + 150:
		print("trailer: a alive %s, b alive %s" % [a.alive, b.alive])
		finish()
