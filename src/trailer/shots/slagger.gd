extends TrailerShot
## scene: res://src/levels/chinatown/chinatown.tscn
## frames: 240
## Chinatown at night: the SL-9 Slagger charged to full in the rain, a
## gunman in front of the neon; the bolt burns a hole through his chest and
## he goes down burning. The man beside him catches the splash.

var a: Enemy
var b: Enemy
var _fired: int = -1


func setup() -> void:
	length = 520
	loadout(["rx9_reflex_overclock"])
	gun("SL-9 Slagger")
	var start: Vector3 = bv(9.4, 8.4)
	a = spawn("gunman", bv(5.6, 8.9), start, 5)
	b = spawn("gunman", bv(2.2, 10.4), start, 9)
	place_player(start, a.body.chest_position())
	# On their marks (passive, guns on the operative): the man behind must
	# not walk up or put rounds into his partner's back.
	for e: Enemy in [a, b]:
		e.sees_player = true


func step() -> void:
	var w: PlayerWeapon = player.weapon()
	if _fired < 0 and f > 10:
		for e: Enemy in [a]:
			if (f + e.look_seed) % 11 == 0:
				enemy_fire(e, player.camera().global_position + Vector3(0.0, -0.3, 0.6), 3.0)
	aim(a.body.chest_position() + Vector3(0.0, 0.05, 0.0) if _fired < 0 or f < _fired + 20 else a.global_position + Vector3.UP * 0.5, 10.0 if _fired < 0 else 4.0)
	if f == 12:
		w.script_hold(true)


	if _fired < 0 and f > 20 and w.plasma_charge() >= 1.0:
		w.script_hold(false)
		_fired = f
		print("trailer: slagger fired at %d" % f)
	if _fired > 0 and f == _fired + 30:
		print("trailer: a alive %s burning %s, b burning %s" % [a.alive, a.is_burning(), b.is_burning()])
	if _fired > 0 and f > _fired + 220:
		finish()
