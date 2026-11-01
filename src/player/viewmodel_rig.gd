class_name ViewmodelRig
extends Node3D
## First-person weapon + arms, parented to the player camera. Instances each
## model in `models` (all authored in the same weapon space) and places them
## with the ViewmodelConfig. The weapon controller moves the whole rig each
## frame (PlayerWeapon / ViewmodelMotion). Viewmodel meshes don't cast shadows.
##
## Moving parts are found by node name in the models: `slide` (travels −X
## when the gun cycles) and `magazine` (drops −Y during a reload). The
## models work without them; the parts just don't move.

@export var config: ViewmodelConfig
@export var models: Array[PackedScene] = []

var _slide: Node3D
var _slide_rest: Vector3
var _magazine: Node3D
var _mag_rest: Vector3


func _ready() -> void:
	transform = config.weapon_transform()
	for scene: PackedScene in models:
		var model: Node = scene.instantiate()
		add_child(model)
		for node: Node in model.find_children("*", "GeometryInstance3D", true, false):
			var geo: GeometryInstance3D = node as GeometryInstance3D
			geo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if _slide == null:
			_slide = model.find_child("slide", true, false) as Node3D
		if _magazine == null:
			_magazine = model.find_child("magazine", true, false) as Node3D
	if _slide:
		_slide_rest = _slide.position
	if _magazine:
		_mag_rest = _magazine.position


func has_moving_slide() -> bool:
	return _slide != null


## Slide travel back from rest, metres (weapon space −X).
func set_slide(back: float) -> void:
	if _slide:
		_slide.position = _slide_rest + Vector3(-back, 0.0, 0.0)


## Magazine drop below the grip, metres.
func set_magazine_out(down: float) -> void:
	if _magazine:
		_magazine.position = _mag_rest + Vector3(0.0, -down, 0.0)
		_magazine.visible = down < 0.18
