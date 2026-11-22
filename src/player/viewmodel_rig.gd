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
##   `reticle`  a projected optic reticle: self-lit, coloured like every
##              reticle (seaglass, crimson over an enemy; ReticleStyle)
##   `optic`    shown only while the loaded shells use it (Saiga-12K slugs)
##   `shell_hull`, `mag_tape`  tinted with the loaded shell type's colour
##   `charging_handle`  travels −X while the bolt is held open (MP5 cocking handle)
##   `laser`    the laser's emitter window (self-lit; WeaponLaser draws the beam)
##   `cylinder` a revolver cylinder: turns about its axis a chamber a shot and
##              swings out on the crane to load (M32A1)
##   `crane`    the yoke the cylinder swings out on (swings, doesn't turn)
##   `round_<n>` the case head in chamber n (turns and swings with the cylinder)
##   `lever`    a lever action's lever: swings about a hinge along the gun's side
##   `bolt`     a lever action's bolt: runs back (−X) with the lever
##   `hammer`   an exposed hammer: falls forward on the shot, cocked by the lever
##   `load_round` the cartridge going in at a loading gate during a reload
##   `mag_shell`  a clear magazine's body: gets an amber, see-through material
##   `mag_rounds` the rounds inside it, one mesh: a shader hides the fired ones
##                (UV.x = slot from the top; mag_rounds.gdshader)
##   `mag_follower` rides up the magazine's curve under the last round
##   `pump`     a pump gun's fore-end: racked back (−X) and forward each shot
##   `support_arm` the support hand and arm (in the arms model): rides the pump

@export var config: ViewmodelConfig
@export var models: Array[PackedScene] = []
## Lazy model paths (used in player.tscn so unequipped guns stay out of VRAM).
@export var model_paths: PackedStringArray = PackedStringArray()

var _loaded: bool = false
var _model_nodes: Array[Node] = []
var _pending_colors: BodyColors
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
var _reticle: GeometryInstance3D
var _reticle_mat: StandardMaterial3D
var _optic: Node3D
var _handle: Node3D
var _handle_rest: Vector3
var _laser: GeometryInstance3D
var _cylinder: Node3D
var _cylinder_rest: Transform3D
var _crane: Node3D
var _crane_rest: Transform3D
var _lever: Node3D
var _lever_rest: Transform3D
var _bolt: Node3D
var _bolt_rest: Vector3
var _hammer: Node3D
var _hammer_rest: Transform3D
var _load_round: Node3D
var _load_rest: Vector3
var _pump: Node3D
var _pump_rest: Vector3
var _support: Node3D
var _support_rest: Vector3
## The arms (every model after the gun): their meshes, for the lever hand bend.
var _arm_roots: Array[Node] = []
var _bend_ready: bool = false
var _last_bend: float = 0.0
var _rounds: Array[Node3D] = []
var _round_rest: Array[Transform3D] = []
var _tinted: Array[GeometryInstance3D] = []
var _tint_mat: StandardMaterial3D
var _scoped: bool = false
var _mag_rounds: GeometryInstance3D
var _rounds_mat: ShaderMaterial
var _mag_follower: Node3D
var _follower_rest: Transform3D
var _shown_rounds: int = -1


func _ready() -> void:
	transform = config.weapon_transform()
	add_to_group(&"suit_painted")
	if visible or not models.is_empty():
		ensure_loaded()


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED and visible and not _loaded:
		ensure_loaded()


func is_loaded() -> bool:
	return _loaded


## Starts loading the gun and arm glTFs on a worker thread (called while the
## previous gun holsters so switching incurs no main-thread load hitch).
func preload_async() -> void:
	if _loaded:
		return
	for p: String in model_paths:
		if not p.is_empty() and not ResourceLoader.has_cached(p):
			ResourceLoader.load_threaded_request(p)


## Instantiates the gun and arm models if they haven't been loaded yet.
func ensure_loaded() -> void:
	if _loaded:
		return
	var scenes: Array[PackedScene] = []
	if not models.is_empty():
		scenes = models
	else:
		for p: String in model_paths:
			if p.is_empty():
				continue
			var ps: PackedScene
			if ResourceLoader.load_threaded_get_status(p) != ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
				ps = ResourceLoader.load_threaded_get(p) as PackedScene
			else:
				ps = load(p) as PackedScene
			if ps:
				scenes.append(ps)
	if scenes.is_empty():
		return
	_loaded = true
	for idx: int in scenes.size():
		var scene: PackedScene = scenes[idx]
		var model: Node = scene.instantiate()
		add_child(model)
		_model_nodes.append(model)
		if idx > 0:
			_arm_roots.append(model)
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
		if _reticle == null:
			_reticle = model.find_child("reticle", true, false) as GeometryInstance3D
		if _optic == null:
			_optic = model.find_child("optic", true, false) as Node3D
		if _handle == null:
			_handle = model.find_child("charging_handle", true, false) as Node3D
		if _laser == null:
			_laser = model.find_child("laser", true, false) as GeometryInstance3D
		if _cylinder == null:
			_cylinder = model.find_child("cylinder", true, false) as Node3D
			_crane = model.find_child("crane", true, false) as Node3D
			for k: int in 12:
				var r: Node3D = model.find_child("round_%d" % k, true, false) as Node3D
				if r == null:
					break
				_rounds.append(r)
				_round_rest.append(r.transform)
		if _lever == null:
			_lever = model.find_child("lever", true, false) as Node3D
		if _bolt == null:
			_bolt = model.find_child("bolt", true, false) as Node3D
		if _hammer == null:
			_hammer = model.find_child("hammer", true, false) as Node3D
		if _load_round == null:
			_load_round = model.find_child("load_round", true, false) as Node3D
		if _pump == null:
			_pump = model.find_child("pump", true, false) as Node3D
		if _support == null:
			_support = model.find_child("support_arm", true, false) as Node3D
		if _mag_rounds == null:
			_mag_rounds = model.find_child("mag_rounds", true, false) as GeometryInstance3D
			_mag_follower = model.find_child("mag_follower", true, false) as Node3D
			var shell: GeometryInstance3D = model.find_child("mag_shell", true, false) as GeometryInstance3D
			if shell:
				shell.material_override = _clear_polymer()
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
	if _vent:
		_vent_rest = _vent.position
	if _handle:
		_handle_rest = _handle.position
	if _lever:
		_lever_rest = _lever.transform
	if _bolt:
		_bolt_rest = _bolt.position
	if _hammer:
		_hammer_rest = _hammer.transform
	if _pump:
		_pump_rest = _pump.position
	if _support:
		_support_rest = _support.position
	if _load_round:
		_load_rest = _load_round.position
		_load_round.visible = false
	if _cylinder:
		_cylinder_rest = _cylinder.transform
	if _mag_rounds:
		_rounds_mat = ShaderMaterial.new()
		_rounds_mat.shader = preload("res://src/weapons/mag_rounds.gdshader")
		_mag_rounds.material_override = _rounds_mat
	if _mag_follower:
		_follower_rest = _mag_follower.transform
	if _crane:
		_crane_rest = _crane.transform
	if _laser:
		# The emitter window glows in the laser's colour whatever the bake did.
		var lit: StandardMaterial3D = StandardMaterial3D.new()
		lit.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		lit.albedo_color = Color(0.45, 1.0, 0.5)
		_laser.material_override = lit
	if _glow:
		# Self-lit strips: no texture needed, the game sets colour and energy.
		_glow_mat = StandardMaterial3D.new()
		_glow_mat.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
		_glow_mat.albedo_color = Color(0.02, 0.03, 0.035)
		_glow_mat.roughness = 0.4
		_glow_mat.emission_enabled = true
		_glow_mat.emission = Color(0.35, 0.85, 1.0)
		_glow_mat.emission_energy_multiplier = 2.0
		_glow.material_override = _glow_mat
	if _reticle:
		_reticle_mat = StandardMaterial3D.new()
		_reticle_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_reticle_mat.albedo_color = ReticleStyle.SEAGLASS
		_reticle.material_override = _reticle_mat
	if _lens:
		var glass: StandardMaterial3D = StandardMaterial3D.new()
		glass.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
		glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		glass.albedo_color = Color(0.45, 0.6, 0.75, 0.12)
		glass.metallic = 0.6
		glass.roughness = 0.05
		glass.cull_mode = BaseMaterial3D.CULL_DISABLED
		_lens.material_override = glass
	if _pending_colors:
		_pending_colors.apply_to_model(self, false)
	if _scoped:
		for n: Node in _model_nodes:
			var n3: Node3D = n as Node3D
			if n3:
				n3.visible = false


## Frees the instantiated weapon and arm models when this rig hasn't been used
## recently (keeps weapon VRAM bounded on 4 GB phones). Only runs while hidden.
func unload_models() -> void:
	if not _loaded or visible or not models.is_empty():
		return
	for n: Node in _model_nodes:
		if is_instance_valid(n):
			n.queue_free()
	_model_nodes.clear()
	_arm_roots.clear()
	_rounds.clear()
	_round_rest.clear()
	_tinted.clear()
	_slide = null
	_magazine = null
	_cover = null
	_belt = null
	_stock = null
	_vent = null
	_glow = null
	_glow_mat = null
	_lens = null
	_reticle = null
	_reticle_mat = null
	_optic = null
	_handle = null
	_laser = null
	_cylinder = null
	_crane = null
	_lever = null
	_bolt = null
	_hammer = null
	_load_round = null
	_pump = null
	_support = null
	_tint_mat = null
	_mag_rounds = null
	_rounds_mat = null
	_mag_follower = null
	_bend_ready = false
	_last_bend = 0.0
	_shown_rounds = -1
	_scoped = false
	_loaded = false


## The suit colours changed (BodyColors): repaint the arms. The guns have no
## region maps, so they're left alone.
func repaint(colors: BodyColors) -> void:
	_pending_colors = colors
	if colors and _loaded:
		colors.apply_to_model(self, false)


func has_moving_slide() -> bool:
	ensure_loaded()
	return _slide != null


func has_part(part_name: StringName) -> bool:
	ensure_loaded()
	match part_name:
		&"lever":
			return _lever != null
		&"bolt":
			return _bolt != null
		&"hammer":
			return _hammer != null
		&"load_round":
			return _load_round != null
		&"pump":
			return _pump != null
		&"support_arm":
			return _support != null
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
		&"reticle":
			return _reticle != null
		&"optic":
			return _optic != null
		&"charging_handle":
			return _handle != null
		&"laser":
			return _laser != null
		&"cylinder":
			return _cylinder != null
		&"crane":
			return _crane != null
		&"mag_rounds":
			return _mag_rounds != null
		&"mag_follower":
			return _mag_follower != null
	return false


## A clear magazine's body: smoky amber polymer you can see the rounds through.
static func _clear_polymer() -> StandardMaterial3D:
	var m: StandardMaterial3D = StandardMaterial3D.new()
	m.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(0.62, 0.46, 0.26, 0.34)
	m.roughness = 0.16
	m.metallic_specular = 0.6
	m.rim_enabled = true
	m.rim = 0.35
	m.rim_tint = 0.6
	return m


## Rounds shown in a clear magazine (the fired ones hidden), and the follower
## turned up the magazine's curve (`step_deg` per round gone, about the line
## along Z through `center`, magazine space).
func set_mag_rounds(count: int, capacity: int, center: Vector3, step_deg: float) -> void:
	if _rounds_mat == null or count == _shown_rounds:
		return
	_shown_rounds = count
	_rounds_mat.set_shader_parameter(&"rounds", float(count))
	if _mag_follower:
		var a: float = deg_to_rad(step_deg) * float(maxi(capacity - count, 0))
		_mag_follower.transform = Transform3D(Basis(), center) * Transform3D(Basis(Vector3(0, 0, 1), a), Vector3.ZERO) \
				* Transform3D(Basis(), -center) * _follower_rest


func mag_rounds_shown() -> int:
	return _shown_rounds


func follower_transform() -> Transform3D:
	return _mag_follower.transform if _mag_follower else Transform3D()


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


## Lever swung `angle_deg` about the line along the gun's side (Z) through `hinge`.
func set_lever(angle_deg: float, hinge: Vector3) -> void:
	if _lever:
		_lever.transform = _hinged(angle_deg, hinge) * _lever_rest


func lever_transform() -> Transform3D:
	return _lever.transform if _lever else Transform3D()


## Pump (fore-end) travel back from rest, metres (weapon space −X); the
## support arm goes with it.
func set_pump(back: float) -> void:
	if _pump:
		_pump.position = _pump_rest + Vector3(-back, 0.0, 0.0)
	if _support:
		_support.position = _support_rest + Vector3(-back, 0.0, 0.0)


func pump_position() -> Vector3:
	return _pump.position - _pump_rest if _pump else Vector3.ZERO


func support_position() -> Vector3:
	return _support.position - _support_rest if _support else Vector3.ZERO


## Bolt travel back from rest, metres (weapon space −X).
func set_bolt(back: float) -> void:
	if _bolt:
		_bolt.position = _bolt_rest + Vector3(-back, 0.0, 0.0)


## The firing hand goes with a lever: turned `angle_rad` about the line
## along Z through `pivot` (weapon space), bending at the wrist
## (suit_paint.gdshader). 0 puts it back on the grip.
func set_hand_bend(angle_rad: float, pivot: Vector3) -> void:
	if _arm_roots.is_empty() or is_equal_approx(angle_rad, _last_bend):
		return
	_last_bend = angle_rad
	if not _bend_ready:
		if angle_rad == 0.0:
			return
		_bend_ready = true
		# Unpainted arms still wear the baked StandardMaterial: give them the
		# suit shader (no colours: the baked look) so they can bend.
		for root: Node in _arm_roots:
			for n: Node in root.find_children("*", "MeshInstance3D", true, false):
				var mi: MeshInstance3D = n as MeshInstance3D
				if mi.get_surface_override_material(0) == null:
					BodyColors.new().apply_to_model(root, false)
					break
	for root: Node in _arm_roots:
		for n: Node in root.find_children("*", "MeshInstance3D", true, false):
			var mi: MeshInstance3D = n as MeshInstance3D
			var to_w: Transform3D = global_transform.affine_inverse() * mi.global_transform
			for i: int in mi.get_surface_override_material_count():
				var m: ShaderMaterial = mi.get_surface_override_material(i) as ShaderMaterial
				if m == null:
					continue
				m.set_shader_parameter(&"bend_angle", angle_rad)
				m.set_shader_parameter(&"bend_pivot", pivot)
				m.set_shader_parameter(&"bend_to_weapon", Projection(to_w))
				m.set_shader_parameter(&"bend_from_weapon", Projection(to_w.affine_inverse()))


## Hammer turned `angle_deg` from cocked about the line along Z through `hinge`.
func set_hammer(angle_deg: float, hinge: Vector3) -> void:
	if _hammer:
		_hammer.transform = _hinged(angle_deg, hinge) * _hammer_rest


## The round at the loading gate: hidden at `t` < 0, else on its way in
## from `from` (weapon-space offset) at t = 0 to home at t = 1.
func set_load_round(t: float, from: Vector3) -> void:
	if _load_round == null:
		return
	_load_round.visible = t >= 0.0 and t < 0.98
	if t >= 0.0:
		var k: float = smoothstep(0.0, 1.0, t)
		_load_round.position = _load_rest + from * (1.0 - k)


func has_lever() -> bool:
	ensure_loaded()
	return _lever != null


static func _hinged(angle_deg: float, hinge: Vector3) -> Transform3D:
	return Transform3D(Basis(), hinge) * Transform3D(Basis(Vector3(0, 0, 1), deg_to_rad(angle_deg)), Vector3.ZERO) \
			* Transform3D(Basis(), -hinge)


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


## Optic reticle colour (seaglass / crimson).
func set_reticle_color(color: Color) -> void:
	if _reticle_mat:
		_reticle_mat.albedo_color = color


func reticle_color() -> Color:
	return _reticle_mat.albedo_color if _reticle_mat else Color.WHITE


func glow_energy() -> float:
	return _glow_mat.emission_energy_multiplier if _glow_mat else 0.0
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
		_tint_mat.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
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


## Cocking handle travel back from rest, metres (weapon space −X).
func set_charging_handle(back: float) -> void:
	if _handle:
		_handle.position = _handle_rest + Vector3(-back, 0.0, 0.0)


func charging_handle_back() -> float:
	return _handle_rest.x - _handle.position.x if _handle else 0.0


## Belt offset from rest (weapon space), for the feed shake.
func set_belt_offset(offset: Vector3) -> void:
	if _belt:
		_belt.position = _belt_rest + offset


## Revolver cylinder: turned `index_deg` about the line along X through
## `axis` (weapon space), and swung out `swing_deg` with the crane about the
## line along X through `hinge`. The case heads go with it.
func set_cylinder(index_deg: float, swing_deg: float, axis: Vector3, hinge: Vector3) -> void:
	if _cylinder == null:
		return
	var spin: Transform3D = Transform3D(Basis(), axis) * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(index_deg)), Vector3.ZERO) \
			* Transform3D(Basis(), -axis)
	var swing: Transform3D = Transform3D(Basis(), hinge) * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(swing_deg)), Vector3.ZERO) \
			* Transform3D(Basis(), -hinge)
	_cylinder.transform = swing * spin * _cylinder_rest
	if _crane:
		_crane.transform = swing * _crane_rest
	for k: int in _rounds.size():
		_rounds[k].transform = swing * spin * _round_rest[k]


## Shows or hides the case head in chamber `k`.
func set_round_visible(k: int, shown: bool) -> void:
	if k >= 0 and k < _rounds.size():
		_rounds[k].visible = shown


func round_visible(k: int) -> bool:
	return k >= 0 and k < _rounds.size() and _rounds[k].visible


## The cylinder's transform in weapon space (tests).
func cylinder_transform() -> Transform3D:
	return _cylinder.transform if _cylinder else Transform3D()
