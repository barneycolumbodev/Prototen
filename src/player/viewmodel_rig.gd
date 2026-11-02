class_name ViewmodelRig
extends Node3D
## First-person weapon + arms, parented to the player camera. Instances each
## model in `models` (all authored in the same weapon space) and places them
## with the ViewmodelConfig. The weapon controller moves the whole rig each
## frame (PlayerWeapon / ViewmodelMotion). Viewmodel meshes don't cast shadows.
##
## Moving parts are found by node name in the models. All optional; a model
## without them just doesn't move that part:
##   `slide`    travels −X when the gun cycles (pistol)
##   `magazine` drops −Y during a reload (pistol magazine, MG ammo box)
##   `cover`    swings open about a hinge during a reload (MG feed cover)
##   `belt`     shakes as the gun feeds, and leaves with the box (MG belt)
##   `stock`    hidden while aiming (it would sit against the cheek, filling the screen)
##   `optic`    shown only while the loaded shells use it (Saiga-12K slugs)
##   `shell_hull`, `mag_tape`  tinted with the loaded shell type's colour

@export var config: ViewmodelConfig
@export var models: Array[PackedScene] = []

var _slide: Node3D
var _slide_rest: Vector3
var _magazine: Node3D
var _mag_rest: Vector3
var _cover: Node3D
var _cover_rest: Transform3D
var _belt: Node3D
var _belt_rest: Vector3
var _stock: Node3D
var _optic: Node3D
var _tinted: Array[GeometryInstance3D] = []
var _tint_mat: StandardMaterial3D
var _scoped: bool = false


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
		if _cover == null:
			_cover = model.find_child("cover", true, false) as Node3D
		if _belt == null:
			_belt = model.find_child("belt", true, false) as Node3D
		if _stock == null:
			_stock = model.find_child("stock", true, false) as Node3D
		if _optic == null:
			_optic = model.find_child("optic", true, false) as Node3D
		for part: String in ["shell_hull", "mag_tape"]:
			var g: GeometryInstance3D = model.find_child(part, true, false) as GeometryInstance3D
			if g:
				_tinted.append(g)
	if _slide:
		_slide_rest = _slide.position
	if _magazine:
		_mag_rest = _magazine.position
	if _cover:
		_cover_rest = _cover.transform
	if _belt:
		_belt_rest = _belt.position


func has_moving_slide() -> bool:
	return _slide != null


func has_part(part_name: StringName) -> bool:
	match part_name:
		&"slide":
			return _slide != null
		&"magazine":
			return _magazine != null
		&"cover":
			return _cover != null
		&"belt":
			return _belt != null
		&"stock":
			return _stock != null
		&"optic":
			return _optic != null
	return false


## Slide travel back from rest, metres (weapon space −X).
func set_slide(back: float) -> void:
	if _slide:
		_slide.position = _slide_rest + Vector3(-back, 0.0, 0.0)


## Magazine drop below the grip, metres. The belt leaves with the box.
func set_magazine_out(down: float) -> void:
	if _magazine:
		_magazine.position = _mag_rest + Vector3(0.0, -down, 0.0)
		_magazine.visible = down < 0.18
	if _belt:
		_belt.visible = down < 0.02


## Feed cover open angle (degrees, swinging the front up about `hinge`).
func set_cover_open(angle_deg: float, hinge: Vector3) -> void:
	if _cover:
		var r: Transform3D = Transform3D(Basis(Vector3(0, 0, 1), deg_to_rad(angle_deg)), Vector3.ZERO)
		_cover.transform = Transform3D(Basis(), hinge) * r * Transform3D(Basis(), -hinge) * _cover_rest


## Shows the stock at the hip, hides it once the sights are mostly up.
func set_aimed(ads: float) -> void:
	if _stock:
		_stock.visible = ads < 0.6


## Mounts or removes the optic.
func set_optic(mounted: bool) -> void:
	if _optic:
		_optic.visible = mounted


func optic_mounted() -> bool:
	return _optic != null and _optic.visible


## Colours the loaded-shell markers (top shell hull, magazine tape).
func set_shell_color(color: Color) -> void:
	if _tinted.is_empty():
		return
	if _tint_mat == null:
		_tint_mat = StandardMaterial3D.new()
		_tint_mat.roughness = 0.55
		for g: GeometryInstance3D in _tinted:
			g.material_override = _tint_mat
	_tint_mat.albedo_color = color


func shell_color() -> Color:
	return _tint_mat.albedo_color if _tint_mat else Color.WHITE


## Looking through the optic: the whole viewmodel steps aside for the HUD's scope view.
func set_scoped(scoped: bool) -> void:
	if scoped == _scoped:
		return
	_scoped = scoped
	for child: Node in get_children():
		var n: Node3D = child as Node3D
		if n:
			n.visible = not scoped


func is_scoped() -> bool:
	return _scoped


## Belt offset from rest (weapon space), for the feed shake.
func set_belt_offset(offset: Vector3) -> void:
	if _belt:
		_belt.position = _belt_rest + offset
