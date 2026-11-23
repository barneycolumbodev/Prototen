extends TrailerShot
## scene: res://src/levels/hotel/hotel.tscn
## frames: 290
## The Golden Dragon's lift hall: three gunmen fire on the operative and he
## holds LB, catching their rounds in the LC-6's field in front of his left
## hand. A lift chimes and opens on a Hatchet Man who charges; the operative
## lets go and every caught round goes back out into him.

var gunmen: Array[Enemy] = []
var hatchet: Enemy
var lift: Lift
var _released: int = -1
var _opened: int = -1


func setup() -> void:
	length = 700
	loadout(["lc6_lorentz_catcher"])
	gun("Five-seveN SR")
	var start: Vector3 = bv(-9.6, 21.2)
	gunmen.append(spawn("gunman", bv(-0.6, 19.2), start, 3))
	gunmen.append(spawn("gunman", bv(2.6, 20.4), start, 8))
	gunmen.append(spawn("gunman", bv(1.2, 18.1), start, 12))
	place_player(start, bv(0.5, 20.6, 1.3))
	for e: Enemy in gunmen:
		alert(e)
	var hm: HotelMap = map as HotelMap
	lift = hm.lifts[2] if hm.lifts.size() > 2 else null
	hatchet = Enemy.new()
	hatchet.config = load("res://data/enemies/hatchet_man.tres") as EnemyConfig
	hatchet.look_seed = 23
	squad.add(hatchet)
	map.add_child(hatchet)
	hatchet.global_position = lift.car_centre if lift else bv(0.0, 26.0)
	hatchet.face(PI)
	men.append(hatchet)


func step() -> void:
	var eye: Vector3 = player.camera().global_position
	(part("lc6_lorentz_catcher") as LorentzCatcher)._layer.visible = false
	if f == 8:
		var lc: LorentzCatcher = part("lc6_lorentz_catcher") as LorentzCatcher
		lc.script_hold(true)
		use_part("lc6_lorentz_catcher")
	# The gunmen pour it on while the field is up.
	if _released < 0 and f > 20 and f < 150:
		for i: int in gunmen.size():
			var e: Enemy = gunmen[i]
			if (f + i * 2) % 5 == 0:
				enemy_fire(e, eye + Vector3(randf_range(-0.35, 0.35), randf_range(-0.45, 0.1), 0.0), 0.8)
	if _released < 0:
		aim(bv(0.5, 20.6, 1.3) if f < 135 else hatchet.body.chest_position(), 6.0 if f < 135 else 7.0)
	if f == 60 and lift:
		lift.call_down()
		print("trailer: lift called at ", f)
	if _opened < 0 and f > 60 and lift and lift.state != Lift.State.CLOSED:
		_opened = f
	if f == 120:
		alert(hatchet)
	var lc2: LorentzCatcher = part("lc6_lorentz_catcher") as LorentzCatcher
	if f % 20 == 0:
		print("trailer: f %d held %d hatchet %.1f m state %s" % [f, lc2.held.size(), hatchet.global_position.distance_to(player.global_position), hatchet.state_name()])
	if _released < 0 and f > 130 and hatchet.alive and hatchet.global_position.distance_to(player.global_position) < 4.5:
		aim(hatchet.body.chest_position(), 30.0)
		_released = f
	if _released > 0 and f == _released + 3:
		lc2.script_hold(false)
		print("trailer: released %d rounds at %d" % [lc2.held.size(), f])
	if _released > 0:
		aim(hatchet.body.chest_position() if hatchet.alive else hatchet.global_position + Vector3.UP * 0.6, 8.0)
	if _released > 0 and f == _released + 40:
		print("trailer: hatchet alive %s hp %.0f" % [hatchet.alive, hatchet.health])
	if _released > 0 and f > _released + 200:
		finish()
	if f > 650:
		finish()
