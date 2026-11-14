class_name ActivesDemo
extends Node
## Cloud screenshots of the active parts (`-- --demo=active:<part id>`,
## tools/screenshot.sh with `--capture-only=active`). Installs the part (and
## whatever it needs) on the operative in the test room, deploys it and
## freezes the game so the capture sees one moment:
##   --stage=<0..1>   freeze part-way through the deploy
##   --act=<name>     after deploying, do the part's thing: lash (whip),
##                    grab / throw (mesh arm), fly / boom (drone), arc,
##                    ram, deadeye / mark / volley / impact (setae: fibres
##                    grown; four marks placed; needles in flight; the
##                    first cavity), catch / full / release (catcher: rounds
##                    streaming into the field; the field nearly full; just
##                    after letting go, the rounds on their way back)
##   --hold=<frames>  frames to let run after the act before freezing (default 6)
##   --paint=channel:rrggbb,...  suit colours (BodyColors channels)
##   --cam=x,y,z,tx,ty,tz  shoot from a camera at x,y,z looking at tx,ty,tz
##                    instead of the operative's eye
## The capture waits (group capture_busy) until it has frozen.

const NEEDS: Dictionary[String, Array] = {
	"sd3_shrike_drone": ["nl3_cortical_uplink"],
	"ad2_arc_projector": ["pc3_power_cell"],
	"tc4_thermoptic_shroud": ["hp4_hyperoxic_lungs"],
}

var room: TestRoom
var part_id: String = ""
var stage: float = 1.0
var act: String = ""
var hold: int = 6
var part: ActivePart
var _phase: int = 0
var _frames: int = 0
var _a: Enemy
var _b: Enemy
var _c: Enemy
var _d: Enemy
var _marked: bool = false
const SETAE_ACTS: Array[String] = ["deadeye", "mark", "volley", "impact"]
const CATCH_ACTS: Array[String] = ["catch", "full", "release"]
var _shots: int = 0
var _cam: Camera3D


func _ready() -> void:
	add_to_group(&"capture_busy")
	process_mode = Node.PROCESS_MODE_ALWAYS
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with("--stage="):
			stage = clampf(arg.trim_prefix("--stage=").to_float(), 0.0, 1.0)
		elif arg.begins_with("--act="):
			act = arg.trim_prefix("--act=")
		elif arg.begins_with("--hold="):
			hold = arg.trim_prefix("--hold=").to_int()
		elif arg.begins_with("--paint="):
			# channel:rrggbb,... on the operative (the first-person arms follow).
			var colors: BodyColors = BodyColors.new()
			for spec: String in arg.trim_prefix("--paint=").split(","):
				colors.set_color(StringName(spec.get_slice(":", 0)), Color.html(spec.get_slice(":", 1)))
			room.player.set_colors.call_deferred(colors)
		elif arg.begins_with("--cam="):
			var v: PackedFloat64Array = arg.trim_prefix("--cam=").split_floats(",")
			if v.size() == 6:
				var cam: Camera3D = Camera3D.new()
				cam.fov = 60.0
				add_child(cam)
				cam.look_at_from_position(Vector3(v[0], v[1], v[2]), Vector3(v[3], v[4], v[5]))
				_cam = cam
	var p: Player = room.player
	p.invulnerable = true
	p.global_position = Vector3(0.5, 0.0, 6.0)
	p.set_view(0.0, deg_to_rad(-2.0))
	var lo: BodyLoadout = p.loadout.copy()
	var ids: Array = NEEDS.get(part_id, []) + [part_id]
	for id: String in ids:
		var data: PartData = LoadoutStore.LIBRARY.find(StringName(id))
		if data:
			lo.install(data)
	p.apply_loadout(lo)


func _physics_process(_delta: float) -> void:
	if not act in SETAE_ACTS:
		_step()


## The setae's acts run per drawn frame: physics frames barely tick in their
## slowed time. Their --hold is milliseconds of the part's real time after the release.
func _process(_delta: float) -> void:
	if act in SETAE_ACTS:
		_step()


func _step() -> void:
	var p: Player = room.player
	_frames += 1
	match _phase:
		0:
			if _frames < 20:
				return
			part = p.augments.find(StringName(part_id))
			if part == null:
				push_error("ActivesDemo: %s isn't installed" % part_id)
				_freeze()
				return
			if part.is_offline():
				push_error("ActivesDemo: %s is offline: %s" % [part_id, part.offline_reason()])
			_a = room.shooting_range.targets[0]
			_b = room.shooting_range.targets[2]
			_place_targets()
			p.augments.select(part.slot)
			var lc: LorentzCatcher = part as LorentzCatcher
			if lc:
				lc.script_hold(true)
			p.augments.use_selected()
			_phase = 1
			_frames = 0
		1:
			if act == "":
				if part.blend >= stage - 0.001 and (part.state == ActivePart.State.ACTIVE or stage < 1.0):
					_freeze()
				return
			if part.state != ActivePart.State.ACTIVE and act != "ram" and act != "arc":
				return
			_act()
			_phase = 2
			_frames = 0
		2:
			if _acted() and _frames >= hold:
				_freeze()


func _place_targets() -> void:
	if _a == null or _b == null:
		return
	match act:
		"lash":
			_a.global_position = Vector3(0.2, 0.0, 2.6)
			_b.global_position = Vector3(1.4, 0.0, 2.2)
		"grab", "throw":
			_a.global_position = Vector3(0.6, 0.0, -1.0)
			_b.global_position = Vector3(1.0, 0.0, -7.0)
		"boom", "fly":
			_a.global_position = Vector3(0.0, 0.0, -4.0)
			_b.global_position = Vector3(1.6, 0.0, -5.0)
		"arc":
			_a.global_position = Vector3(0.0, 0.0, -2.0)
			_b.global_position = Vector3(2.5, 0.0, -5.0)
		"ram":
			_a.global_position = Vector3(0.5, 0.0, 1.5)
			_b.global_position = Vector3(0.9, 0.0, -1.0)
		"deadeye", "mark", "volley", "impact":
			_a.global_position = Vector3(-1.4, 0.0, -2.5)
			_b.global_position = Vector3(1.3, 0.0, -4.5)
			_c = room.shooting_range.targets[1]
			_d = room.shooting_range.targets[3]
			if _c and _d:
				_c.global_position = Vector3(3.2, 0.0, -1.5)
				_d.global_position = Vector3(-0.2, 0.0, -7.5)
				_c.face(0.0)
				_d.face(0.0)
		"catch", "full", "release":
			_a.global_position = Vector3(-2.6, 0.0, -5.0)
			_b.global_position = Vector3(1.0, 0.0, -11.0)
			_c = room.shooting_range.targets[1]
			if _c:
				_c.global_position = Vector3(2.4, 0.0, -6.5)
				_c.face(0.0)
		_:
			return
	_a.face(0.0)
	_b.face(0.0)
	if act in CATCH_ACTS:
		# The gunmen turn to the operative; the crosshair is on the man down range.
		for e: Enemy in [_a, _c]:
			if e:
				var d: Vector3 = room.player.global_position - e.global_position
				e.face(atan2(-d.x, -d.z))
		GunplayDemo.aim_at(room.player, _b.body.chest_position() + Vector3(-1.2, 0.0, 0.0))
		return
	GunplayDemo.aim_at(room.player, _a.body.chest_position())


func _act() -> void:
	match act:
		"lash":
			(part as Whip).script_lash()
		"grab", "throw":
			(part as MeshArm).script_fire()
		"boom":
			var d: ShrikeDrone = part as ShrikeDrone
			d.craft.global_position = Vector3(0.6, 1.6, -1.0)
			d.set_view(0.0, -0.25)
		"fly":
			var d2: ShrikeDrone = part as ShrikeDrone
			d2.craft.global_position = Vector3(3.5, 2.6, 1.5)
			d2.set_view(deg_to_rad(-30.0), -0.3)


## The act has reached the moment worth a picture (the hold counts from here).
func _acted() -> bool:
	match act:
		"grab":
			if (part as MeshArm).mode != MeshArm.Mode.HOLDING:
				_frames = 0
				return false
		"throw":
			var m: MeshArm = part as MeshArm
			if m.mode == MeshArm.Mode.HOLDING and m.throws == 0:
				if _frames > 25:
					GunplayDemo.aim_at(room.player, _b.body.chest_position() + Vector3.UP * 0.3)
					m.script_fire()
				return false
			if m.throws == 0:
				_frames = 0
				return false
		"boom":
			var d: ShrikeDrone = part as ShrikeDrone
			if d.last_end == &"":
				if _frames > 12:
					d.craft.global_position = _a.body.chest_position() + Vector3(0.5, 0.4, 1.2)
					d.script_detonate()
				_frames = mini(_frames, 13)
				return false
		"arc":
			if (part as ArcProjector).discharges == 0:
				_frames = 0
				return false
		"ram":
			if (part as RamThrusters).struck == 0 and _frames < 40:
				return false
		"catch", "full", "release":
			var lc: LorentzCatcher = part as LorentzCatcher
			if lc.mode == LorentzCatcher.Mode.CATCHING:
				_shoot_at_player()
				var want: int = 14 if act == "catch" else 34
				if lc.held.size() < want:
					_frames = 0
					return false
				if act == "release":
					GunplayDemo.aim_at(room.player, _b.body.chest_position())
					lc.script_hold(false)
					_frames = 0
					return false
				return true
			return lc.mode == LorentzCatcher.Mode.RELEASING
		"deadeye", "mark", "volley", "impact":
			var st: Setae = part as Setae
			if st.throws == 0 and st.hairs_grown() < st.needles.size() + 40:
				_frames = 0
				return false
			if act == "deadeye":
				return true
			if not _marked:
				_marked = true
				st.script_mark(_a, &"head")
				st.script_mark(_b, &"chest")
				if _c and _d:
					st.script_mark(_c, &"chest")
					st.script_mark(_d, &"head")
				_frames = 0
				return false
			if act == "mark":
				return true
			if st.throws == 0:
				if _frames > 8:
					st.script_throw()
				return false
			if act == "impact" and st.cavities == 0:
				return false
			_frames = hold
			return st.released_for * 1000.0 >= hold
	return true


## The two gunmen fire at the operative's eye, one round each every other frame, with tracers.
func _shoot_at_player() -> void:
	_shots += 1
	if _shots % 2 != 0:
		return
	var eye: Vector3 = room.player.camera().global_position
	for e: Enemy in [_a, _c]:
		if e == null or not e.alive:
			continue
		var from: Vector3 = e.body.chest_position() + Vector3(0.0, 0.25, 0.0) + (eye - e.global_position).normalized() * 0.6
		var at: Vector3 = eye + Vector3(randf_range(-0.3, 0.3), randf_range(-0.5, 0.15), 0.0)
		Ballistics.fire(e.config.weapon, from, (at - from).normalized(), e, from)


func _freeze() -> void:
	_phase = 9
	var st: Setae = part as Setae
	if st:
		print("capture: setae mode %d state %d throw_t %.2f deadeye %.2f needles %d cavities %d time %.3f" % [st.mode, st.state,
			st._throw_t, st.deadeye, st.needles.size(), st.cavities, Engine.time_scale])
	if _cam:
		_cam.make_current()
	get_tree().paused = true
	remove_from_group(&"capture_busy")
