class_name ArmRig
extends Node3D
## A first-person arm for an active part (the whip, the mesh arm, the fan
## shield): the model (a glTF with one deploy clip), parented to the camera
## where its ViewmodelConfig puts it. The part scrubs the clip from its
## deploy blend, so the animation always matches the state machine. Adds the
## shared motion: the arm rising into view, sway against the look speed, a
## little bob, and kick springs.

var model: Node3D
var anim: AnimationPlayer
var clip: StringName = &""
var clip_len: float = 1.0
var view: ViewmodelConfig
var kick_pos: Spring = Spring.new(7.0, 0.5)
var kick_rot: Spring = Spring.new(7.0, 0.5)
var sway: Spring = Spring.new(5.0, 0.7)
## The arm comes up from this far below (m) over the first `raise_share` of the deploy.
var raise_drop: float = 0.34
var raise_share: float = 0.3
## Extra placement the part adds each frame (aim follow, ADS shift).
var extra: Transform3D = Transform3D.IDENTITY

var _bob_t: float = 0.0
var _drive: Dictionary[String, StandardMaterial3D] = {}


static func make(player: Player, scene: PackedScene, p_view: ViewmodelConfig, rig_name: String) -> ArmRig:
	var r: ArmRig = ArmRig.new()
	r.name = rig_name
	r.view = p_view
	r.visible = false
	if player:
		player.camera().add_child(r)
	r.model = scene.instantiate() as Node3D
	r.add_child(r.model)
	for n: Node in r.model.find_children("*", "AnimationPlayer", true, false):
		r.anim = n as AnimationPlayer
		break
	if r.anim:
		var names: PackedStringArray = r.anim.get_animation_list()
		if not names.is_empty():
			r.clip = StringName(names[0])
			r.clip_len = r.anim.get_animation(r.clip).length
			r.anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
			r.anim.play(r.clip)
			r.anim.seek(0.0, true)
	for n: Node in r.model.find_children("*", "MeshInstance3D", true, false):
		(n as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	r.add_to_group(&"suit_painted")
	if player and player.colors:
		r.repaint(player.colors)
	return r


## The suit colours changed: the arm's plates, weave and pads follow them.
func repaint(colors: BodyColors) -> void:
	if colors and model:
		colors.apply_to_model(model, true)


## Scrubs the deploy clip: 0 = folded, 1 = deployed.
func seek(fraction: float) -> void:
	if anim and clip != &"":
		anim.seek(clampf(fraction, 0.0, 1.0) * clip_len, true)


func part(node_name: String) -> Node3D:
	return model.find_child(node_name, true, false) as Node3D


## One shared material for every surface whose material is called `mat_name`
## ("glow"), so the part can drive its light. Returns null if none has it.
func drive(mat_name: String) -> StandardMaterial3D:
	if _drive.has(mat_name):
		return _drive[mat_name]
	var shared: StandardMaterial3D = null
	for n: Node in model.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		for i: int in mi.mesh.get_surface_count():
			var m: Material = mi.get_surface_override_material(i)
			if m == null:
				m = mi.mesh.surface_get_material(i)
			if m == null or m.resource_name != mat_name:
				continue
			if shared == null:
				shared = (m as StandardMaterial3D).duplicate() as StandardMaterial3D
				shared.resource_name = mat_name
			mi.set_surface_override_material(i, shared)
	_drive[mat_name] = shared
	return shared


## Places the arm for this frame. `real_dt`: real seconds; `blend`: the
## part's deploy blend (0..1).
func tick(real_dt: float, blend: float, player: Player) -> void:
	var dt: float = real_dt * TimeControl.player_scale_now()
	var up: float = clampf(blend / maxf(raise_share, 0.01), 0.0, 1.0)
	up = 1.0 - pow(1.0 - up, 3.0)
	var raise: Vector3 = Vector3(0.0, -raise_drop * (1.0 - up), 0.06 * (1.0 - up))
	var tilt: Vector3 = Vector3(deg_to_rad(-25.0) * (1.0 - up), 0.0, 0.0)
	var lv: Vector2 = player.look_velocity if player else Vector2.ZERO
	sway.target = Vector3(clampf(-lv.y * 0.0006, -0.06, 0.06), clampf(lv.x * 0.0008, -0.08, 0.08), 0.0)
	sway.step(dt)
	var speed: float = 0.0
	if player:
		speed = Vector2(player.velocity.x, player.velocity.z).length()
	_bob_t += dt * (1.6 + speed * 0.18)
	var bob: float = sin(_bob_t * TAU) * clampf(speed / 11.0, 0.0, 1.0) * 0.008
	kick_pos.step(dt)
	kick_rot.step(dt)
	var off: Transform3D = Transform3D(Basis.from_euler(tilt + sway.value + kick_rot.value), raise + Vector3(0.0, bob, 0.0) + kick_pos.value)
	transform = extra * off * view.weapon_transform()
