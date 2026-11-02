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
##   `vent`     lifts (+Y) while a railgun vents heat
##   `glow`     emissive faces; their colour and brightness are set live (charge, heat)
##   `lens`     optic glass: gets a transparent, slightly reflective material

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
var _vent: Node3D
var _vent_rest: Vector3
var _glow: GeometryInstance3D
var _glow_mat: StandardMaterial3D
var _lens: GeometryInstance3D


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
		if _vent == null:
			_vent = model.find_child("vent", true, false) as Node3D
		if _glow == null:
			_glow = model.find_child("glow", true, false) as GeometryInstance3D
		if _lens == null:
			_lens = model.find_child("lens", true, false) as GeometryInstance3D
	if _slide:
		_slide_rest = _slide.position
	if _magazine:
		_mag_rest = _magazine.position
	if _cover:
		_cover_rest = _cover.transform
	if _belt:
		_belt_rest = _belt.position
	if _vent:
		_vent_rest = _vent.position
	if _glow:
		# Self-lit strips: no texture needed, the game sets colour and energy.
		_glow_mat = StandardMaterial3D.new()
		_glow_mat.albedo_color = Color(0.02, 0.03, 0.035)
		_glow_mat.roughness = 0.4
		_glow_mat.emission_enabled = true
		_glow_mat.emission = Color(0.35, 0.85, 1.0)
		_glow_mat.emission_energy_multiplier = 2.0
		_glow.material_override = _glow_mat
	if _lens:
		var glass: StandardMaterial3D = StandardMaterial3D.new()
		glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		glass.albedo_color = Color(0.45, 0.6, 0.75, 0.12)
		glass.metallic = 0.6
		glass.roughness = 0.05
		glass.cull_mode = BaseMaterial3D.CULL_DISABLED
		_lens.material_override = glass


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
		&"vent":
			return _vent != null
		&"glow":
			return _glow != null
		&"lens":
			return _lens != null
	return false


## Slide travel back from rest, metres (weapon space −X).
func set_slide(back: float) -> void:
	if _slide:
		_slide.position = _slide_rest + Vector3(-back, 0.0, 0.0)


## Magazine travel away from the gun, metres, along `direction` (weapon
## space; down for a pistol). The belt leaves with the box.
func set_magazine_out(down: float, direction: Vector3 = Vector3.DOWN) -> void:
	if _magazine:
		_magazine.position = _mag_rest + direction.normalized() * down
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


## Vent shroud lift above its rest position, metres.
func set_vent(lift: float) -> void:
	if _vent:
		_vent.position = _vent_rest + Vector3(0.0, lift, 0.0)


## Glow strips: emission colour and energy.
func set_glow(color: Color, energy: float) -> void:
	if _glow_mat:
		_glow_mat.emission = color
		_glow_mat.emission_energy_multiplier = energy


func glow_energy() -> float:
	return _glow_mat.emission_energy_multiplier if _glow_mat else 0.0


## Belt offset from rest (weapon space), for the feed shake.
func set_belt_offset(offset: Vector3) -> void:
	if _belt:
		_belt.position = _belt_rest + offset
