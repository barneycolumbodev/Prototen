class_name Lift
extends Node3D
## One of the hotel's six lifts (HotelMap): a pair of brass doors on the lift
## hall side of a car. `call_down()` (someone spawned in the car): the arrival
## lantern lights, the chime sounds, and after `CHIME_TO_OPEN` the doors roll
## apart. They stay open at least `HOLD_OPEN` and until the car is empty (the
## operative included: the doors never close on him), then close.
##
## The doors are moving physics bodies on the world layer: they stop people
## and bullets punch through them like sheet metal, and they hide the car
## from the spawner's line-of-sight test while shut.

enum State { CLOSED, ARRIVING, OPENING, OPEN, CLOSING }

const CHIME_TO_OPEN: float = 1.1
const OPEN_TIME: float = 1.0
const CLOSE_TIME: float = 1.4
const HOLD_OPEN: float = 3.5
const DOOR_THICK: float = 0.06

## Door line centre on the floor, car centre on the floor (Godot space), opening size.
var door_centre: Vector3
var car_centre: Vector3
var width: float = 2.0
var height: float = 2.6

var state: State = State.CLOSED
## 0 shut .. 1 open.
var open_amount: float = 0.0
var leaves: Array[AnimatableBody3D] = []
var _time: float = 0.0
var _lantern: MeshInstance3D
var _lantern_mat: StandardMaterial3D
var _along: Vector3 = Vector3.RIGHT

static var _brass: StandardMaterial3D


func _ready() -> void:
	# The doors run along the line across the car's mouth.
	var into: Vector3 = (car_centre - door_centre)
	into.y = 0.0
	into = into.normalized()
	_along = into.cross(Vector3.UP).normalized()
	if _brass == null:
		_brass = StandardMaterial3D.new()
		_brass.albedo_color = Color(0.74, 0.56, 0.3)
		_brass.metallic = 0.65
		_brass.roughness = 0.32
		_brass.metallic_specular = 0.6
		# The doors aren't in the baked lightmap: a little warm self-light stands
		# in for the lift hall's downlights, so they read as brass, not black.
		_brass.emission_enabled = true
		_brass.emission = Color(0.36, 0.25, 0.12)
		_brass.emission_energy_multiplier = 0.6
	for s: int in [-1, 1]:
		var b: AnimatableBody3D = AnimatableBody3D.new()
		b.name = "Leaf%s" % ("L" if s < 0 else "R")
		b.collision_layer = Ballistics.LAYER_WORLD
		b.collision_mask = 0
		b.sync_to_physics = false
		b.set_meta(&"surface", &"sheet_metal")
		var cs: CollisionShape3D = CollisionShape3D.new()
		var box: BoxShape3D = BoxShape3D.new()
		box.size = Vector3(width * 0.5, height, DOOR_THICK)
		cs.shape = box
		b.add_child(cs)
		var mi: MeshInstance3D = MeshInstance3D.new()
		var bm: BoxMesh = BoxMesh.new()
		bm.size = Vector3(width * 0.5 - 0.01, height - 0.01, DOOR_THICK)
		mi.mesh = bm
		mi.material_override = _brass
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		b.add_child(mi)
		# A hairline seam and a kick plate, so they read as lift doors.
		var plate: MeshInstance3D = MeshInstance3D.new()
		var pm: BoxMesh = BoxMesh.new()
		pm.size = Vector3(width * 0.5 - 0.06, 0.3, DOOR_THICK + 0.01)
		plate.mesh = pm
		plate.position = Vector3(0, -height * 0.5 + 0.2, 0)
		var dark: StandardMaterial3D = StandardMaterial3D.new()
		dark.albedo_color = Color(0.3, 0.22, 0.12)
		dark.metallic = 1.0
		dark.roughness = 0.45
		plate.material_override = dark
		b.add_child(plate)
		add_child(b)
		b.global_basis = Basis(_along, Vector3.UP, _along.cross(Vector3.UP))
		leaves.append(b)
	_lantern = MeshInstance3D.new()
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2(0.16, 0.12)
	_lantern.mesh = q
	_lantern_mat = StandardMaterial3D.new()
	_lantern_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_lantern_mat.albedo_color = Color(1.0, 0.25, 0.1)
	_lantern.material_override = _lantern_mat
	_lantern.visible = false
	add_child(_lantern)
	_lantern.global_position = door_centre + Vector3.UP * 3.25 - into * 0.215 - _along * 0.45
	_lantern.global_basis = Basis(_along, Vector3.UP, -into)
	_place()


## Someone is in the car: chime, then open.
func call_down() -> void:
	match state:
		State.CLOSED:
			state = State.ARRIVING
			_time = 0.0
			_lantern.visible = true
			Sfx.play_at(&"lift_ding", door_centre + Vector3.UP * 2.4, -2.0, 0.02)
		State.CLOSING:
			state = State.OPENING
			Sfx.play_at(&"lift_door", door_centre + Vector3.UP * 1.3, -6.0)
		State.OPEN:
			_time = 0.0


func is_open() -> bool:
	return state == State.OPEN or (state == State.OPENING and open_amount > 0.5)


## Is `p` inside the car (or in its doorway)?
func contains(p: Vector3) -> bool:
	var into: Vector3 = (car_centre - door_centre)
	into.y = 0.0
	var depth: float = into.length() * 2.0
	var local: Vector3 = p - door_centre
	var a: float = local.dot(_along)
	var d: float = local.dot(into.normalized())
	return absf(a) < width * 0.5 + 0.1 and d > -0.35 and d < depth + 0.2 and p.y > door_centre.y - 0.5 and p.y < door_centre.y + height


func _occupied() -> bool:
	for n: Node in get_tree().get_nodes_in_group(&"enemies"):
		var e: Node3D = n as Node3D
		if e and contains(e.global_position):
			return true
	for n: Node in get_tree().get_nodes_in_group(&"player"):
		var pl: Node3D = n as Node3D
		if pl and contains(pl.global_position):
			return true
	return false


func _physics_process(delta: float) -> void:
	_time += delta
	match state:
		State.CLOSED:
			return
		State.ARRIVING:
			if _time >= CHIME_TO_OPEN:
				state = State.OPENING
				_time = 0.0
				Sfx.play_at(&"lift_door", door_centre + Vector3.UP * 1.3, -4.0)
		State.OPENING:
			open_amount = minf(open_amount + delta / OPEN_TIME, 1.0)
			if open_amount >= 1.0:
				state = State.OPEN
				_time = 0.0
		State.OPEN:
			if _time >= HOLD_OPEN and not _occupied():
				state = State.CLOSING
				_lantern.visible = false
				Sfx.play_at(&"lift_door", door_centre + Vector3.UP * 1.3, -6.0)
		State.CLOSING:
			if _occupied():
				call_down()  # the safety edge: back open
			else:
				open_amount = maxf(open_amount - delta / CLOSE_TIME, 0.0)
				if open_amount <= 0.0:
					state = State.CLOSED
	_place()


func _place() -> void:
	# Eased: the doors start slow, run, and settle.
	var k: float = open_amount * open_amount * (3.0 - 2.0 * open_amount)
	for i: int in leaves.size():
		var s: float = -1.0 if i == 0 else 1.0
		var rest: Vector3 = door_centre + Vector3.UP * height * 0.5 + _along * s * width * 0.25
		leaves[i].global_position = rest + _along * s * (width * 0.5 - 0.04) * k
