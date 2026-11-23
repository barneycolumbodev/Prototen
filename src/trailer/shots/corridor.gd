extends TrailerShot
## scene: res://src/levels/hotel/hotel.tscn
## frames: 220
## The Golden Dragon's west corridor (2 m wide, red damask): four triad men
## down its length. The operative walks it with the Governor, one man per
## round, the lever thrown between; rams the last with the KR-5 thrusters;
## then turns the corner and dropkicks the man waiting there into the one
## behind him.

var line: Array[Enemy] = []
var corner: Enemy
var behind: Enemy
var _stage: int = 0
var _last_shot: int = -100
var _stage_f: int = 0
var _jumped: int = -1
var _vault: int = -1
var _mantled: int = -1


func setup() -> void:
	length = 900
	loadout(["kr5_ram_thrusters"])
	gun("The Governor")
	var start: Vector3 = bv(-36.0, -1.2)
	line.append(spawn("gunman", bv(-36.45, 3.6), start, 2))
	line.append(spawn("gunman", bv(-35.5, 7.5), start, 5))
	line.append(spawn("gunman", bv(-36.4, 10.4), start, 9))
	line.append(spawn("gunman", bv(-35.8, 13.4), start, 11))
	corner = spawn("gunman", bv(-33.7, 19.55), bv(-36.0, 17.2), 6)
	behind = spawn("gunman", bv(-31.6, 19.3), bv(-36.0, 17.2), 4)
	place_player(start, line[0].body.chest_position())
	for e: Enemy in line + [corner, behind]:
		alert(e)


func _head(e: Enemy) -> Vector3:
	return e.body.hitboxes[&"head"].global_position


func _ready_to_fire() -> bool:
	var w: PlayerWeapon = player.weapon()
	return w.lever_t < 0.0 and w._lever_wait < 0.0 and f - _last_shot > 30


func step() -> void:
	var w: PlayerWeapon = player.weapon()
	# The men further down fire back now and then (muzzle light in the corridor).
	for i: int in line.size():
		var e: Enemy = line[i]
		if e.alive and i > 0 and (f + i * 11) % 29 == 0 and f > 20:
			enemy_fire(e, player.camera().global_position + Vector3(0.5 - i * 0.3, -0.2, 0.0), 3.0)
	if f == 2:
		press(&"move_forward", 0, 0.5)
	# Over the room-service trolley (by 5.5..6.5): a vault at a walk.
	var by: float = -player.global_position.z
	if _stage >= 3 and _vault < 0 and by > 4.3:
		_vault = f
		tap(&"jump")
		print("trailer: vault at %d" % f)
	if _stage >= 3 and f == _stage_f + 1:
		press(&"move_forward", 0, 1.0)
	if f % 20 == 0:
		print("trailer: f %d stage %d at %s" % [f, _stage, player.global_position])
	if _stage < 3:
		var t: Enemy = line[_stage]
		var at: Vector3 = _head(t) if _stage == 1 else t.body.chest_position() + Vector3.UP * 0.1
		aim(at, 12.0)
		if not t.alive:
			_stage += 1
			_stage_f = f
			return
		if f > 22 and _ready_to_fire() and f - _stage_f > 10:
			trigger(true)
			_last_shot = f
			print("trailer: governor at ", f, " on ", t.name)
		elif f == _last_shot + 2:
			trigger(false)
		return
	if _stage == 3:
		# The fourth man: the thrusters.
		aim(line[3].body.chest_position(), 14.0)
		if f == _last_shot + 2:
			trigger(false)
		var gap: float = player.global_position.distance_to(line[3].global_position)
		if _stage_f > 0 and gap < 5.0 and -player.global_position.z > 7.0:
			release(&"move_forward")
			use_part("kr5_ram_thrusters")
			print("trailer: ram at %d from %.1f m" % [f, gap])
			_stage_f = -f
		if _stage_f < 0 and f + _stage_f > 4 and not player.is_dashing():
			_stage = 4
			_stage_f = f
			print("trailer: ram done at %d, struck %d, man alive %s" % [f, (part("kr5_ram_thrusters") as RamThrusters).struck, line[3].alive])
		return
	if _stage == 4:
		# Over the sandbags at the end, then round the corner to the right:
		# jump, A again, boots first into the man waiting there.
		var since: int = f - _stage_f
		var by2: float = -player.global_position.z
		if false:
			print("trailer: s4 %d pos %s vel %s state %d dk %d" % [since, player.global_position, player.velocity, player.move_state, player._dk_phase])
		if _jumped < 0:
			if _mantled < 0:
				aim(bv(-35.9, 21.0, 1.3), 10.0)
				if since == 4:
					press(&"move_forward", 0, 1.0)
				if since == 8:
					tap(&"jump")
					print("trailer: sandbag vault at %d" % f)
				if since > 10 and player.move_state == Player.MoveState.NORMAL and player.global_position.y > 0.5:
					_mantled = f
					release(&"move_forward")
					print("trailer: on the sandbags at %d %s" % [f, player.global_position])
			else:
				aim(corner.body.chest_position(), 20.0)
				var to: Vector3 = corner.global_position - player.global_position
				var want: float = atan2(-to.x, -to.z)
				if absf(angle_difference(player.yaw, want)) < 0.1 or f - _mantled > 30:
					_jumped = f
					tap(&"jump")
					press(&"move_forward", 0, 1.0)
					print("trailer: jump at %d from %s" % [f, player.global_position])
		else:
			var sj: int = f - _jumped
			if sj == 9:
				tap(&"jump")
			if sj > 9 and corner.launched:
				aim(corner.body.chest_position(), 8.0)
			elif sj <= 9:
				aim(corner.body.chest_position(), 18.0)
			if sj == 16:
				release(&"move_forward")
			if sj == 12:
				print("trailer: dropkicking %s" % player.is_dropkicking())
			if sj == 150:
				print("trailer: corner alive %s launched %s, behind launched %s" % [corner.alive, corner.launched, behind.launched])
				finish()
		if since > 400:
			finish()
