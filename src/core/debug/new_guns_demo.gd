class_name NewGunsDemo
extends Node
## Cloud screenshots of the Governor and the SL-9 Slagger (`-- --demo=newguns:<shot>`,
## tools/screenshot.sh with `--capture-only=Camera3D`). Freezes the game for the shot:
##   governor-hip     the Governor at the hip
##   governor-lever   fired, frozen with the lever thrown down
##   governor-reload  loading a round through the gate
##   slagger-charge   the Slagger at about 85 % charge
##   slagger-full     held past full (the field straining)
##   slagger-fire     a full charge just let go
##   slagger-hits     bolts into range targets: a burn-through, a limb, a graze; frozen after
## The capture waits (group capture_busy) until it has frozen.

var room: TestRoom
var shot: String = "governor-hip"
var _frames: int = 0
var _done: bool = false


func _ready() -> void:
	add_to_group(&"capture_busy")
	process_mode = Node.PROCESS_MODE_ALWAYS
	var p: Player = room.player
	p.invulnerable = true
	p.global_position = Vector3(0.5, 0.0, 6.0)
	p.set_view(0.0, deg_to_rad(-3.0))


func _weapon() -> PlayerWeapon:
	return room.player.weapon()


func _physics_process(_delta: float) -> void:
	if _done:
		return
	_frames += 1
	var w: PlayerWeapon = _weapon()
	if _frames == 10:
		w.select_now(w.index_of("The Governor" if shot.begins_with("governor") else "SL-9 Slagger"))
	match shot:
		"governor-hip":
			if _frames > 40:
				_freeze()
		"governor-lever":
			if _frames == 40:
				w.script_input(true, false)
			if _frames > 40 and w.lever_t > 0.4:
				_freeze()
		"governor-reload":
			if _frames == 40:
				w.script_input(true, false)
			if _frames == 90:
				w.script_input(false, false, true)
			if _frames > 90 and w.mechanism.round_progress() > 0.55:
				_freeze()
		"slagger-charge", "slagger-full", "slagger-fire":
			if _frames < 30:
				return
			if _frames >= 30:
				w.script_hold(true)
			var c: float = w.plasma_charge()
			if shot == "slagger-charge" and c > 0.85:
				_freeze()
			elif shot == "slagger-full" and w.plasma_held > w.data.plasma.full_charge_time + 1.6:
				_freeze()
			elif shot == "slagger-fire" and c >= 1.0 and w.plasma_charging:
				w.script_hold(false)
				_frames = 100000
			elif shot == "slagger-fire" and _frames > 100004:
				_freeze()
		"slagger-hits":
			_hits()
		"slagger-hole":
			_hole()


func _hits() -> void:
	var t: Array[Enemy] = room.shooting_range.targets
	var bolts: PlasmaBolts = PlasmaBolts.get_for(self)
	var w: PlayerWeapon = _weapon()
	if _frames == 20:
		t[0].global_position = Vector3(-0.8, 0.0, 1.5)
		t[1].global_position = Vector3(1.4, 0.0, 0.5)
		t[2].global_position = Vector3(3.0, 0.0, 2.5)
		for e: Enemy in t:
			e.face(0.0)
	if _frames == 30:
		var e: Enemy = t[0]
		var at: Vector3 = e.body.hitboxes[&"chest"].global_position
		bolts.launch(w.data, at + Vector3(-0.4, 0.1, 3.0), (at - (at + Vector3(-0.4, 0.1, 3.0))).normalized(), 1.0, room.player)
		var a: Vector3 = t[1].body.hitboxes[&"r_forearm"].global_position
		bolts.launch(w.data, a + Vector3(0.0, 0.0, 3.0), Vector3(0, 0, -1), 0.95, room.player)
		var g: Vector3 = t[2].body.hitboxes[&"chest"].global_position + Vector3(0.4, 0.0, 0.0)
		bolts.launch(w.data, g + Vector3(0.0, 0.0, 3.0), Vector3(0, 0, -1), 0.7, room.player)
	if _frames == 48:
		_freeze()


## One man 2.4 m away, a full charge through his chest from just beside the
## camera, frozen a moment later: you look through the burned-through tunnel.
func _hole() -> void:
	var t: Array[Enemy] = room.shooting_range.targets
	var p: Player = room.player
	if _frames == 20:
		for i: int in range(1, t.size()):
			t[i].global_position = Vector3(30.0 + i, 0.0, -20.0)
		t[0].global_position = Vector3(0.5, 0.0, 3.4)
		t[0].face(0.0)
		p.set_view(0.0, deg_to_rad(-6.0))
	if _frames == 30:
		var at: Vector3 = t[0].body.hitboxes[&"chest"].global_position
		var from: Vector3 = at + Vector3(0.3, 0.05, 3.0)
		PlasmaBolts.get_for(self).launch(_weapon().data, from, (at - from).normalized(), 1.0, p)
	if _frames == 44:
		_freeze()


func _freeze() -> void:
	_done = true
	get_tree().paused = true
	remove_from_group(&"capture_busy")
