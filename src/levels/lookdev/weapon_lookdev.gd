class_name WeaponLookdev
extends Node3D
## Look-dev stage for weapon assets: studio lighting on the Mobile renderer
## plus fixed capture cameras for tools/screenshot.sh. Run:
##   tools/screenshot.sh res://src/levels/lookdev/weapon_lookdev.tscn <out_dir>

@export var model: PackedScene = preload("res://assets/weapons/pistol_57/pistol_57.gltf")

## Capture cameras: name -> [position, look-at target]. Model axes: +X muzzle, +Y up, +Z its left side.
const CAMERAS: Dictionary[String, Array] = {
	"CapHero": [Vector3(0.15, 0.17, 0.97), Vector3(0.088, -0.058, 0.0)],
	"CapFirstPerson": [Vector3(-0.32, 0.075, 0.075), Vector3(0.2, -0.01, -0.01)],
	"CapDetail": [Vector3(0.11, 0.09, 0.40), Vector3(-0.03, -0.04, 0.0)],
}


func _ready() -> void:
	var overlay: CanvasLayer = get_node_or_null("/root/DebugOverlay") as CanvasLayer
	if overlay:
		overlay.visible = false
	add_child(model.instantiate())
	_build_environment()
	_build_lights()
	_build_floor()
	_build_cameras()


func _build_environment() -> void:
	var sky_mat: ProceduralSkyMaterial = ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.10, 0.11, 0.13)
	sky_mat.sky_horizon_color = Color(0.32, 0.30, 0.28)
	sky_mat.ground_horizon_color = Color(0.12, 0.11, 0.10)
	sky_mat.ground_bottom_color = Color(0.02, 0.02, 0.02)
	var sky: Sky = Sky.new()
	sky.sky_material = sky_mat
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.012, 0.013, 0.015)
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.ambient_light_energy = 0.3
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true
	env.glow_intensity = 0.5
	var world_env: WorldEnvironment = WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)


func _build_lights() -> void:
	var key: DirectionalLight3D = DirectionalLight3D.new()
	key.light_energy = 1.3
	key.shadow_enabled = true
	key.directional_shadow_max_distance = 3.0
	add_child(key)
	key.look_at_from_position(Vector3(-0.25, 0.55, 0.55), Vector3(0.09, -0.05, 0.0))
	for spec: Array in [[Vector3(0.25, 0.4, -0.6), Color(1.0, 0.82, 0.62), 1.2], [Vector3(0.6, -0.02, 0.6), Color(0.75, 0.85, 1.0), 0.35]]:
		var omni: OmniLight3D = OmniLight3D.new()
		omni.position = spec[0]
		omni.light_color = spec[1]
		omni.light_energy = spec[2]
		omni.omni_range = 2.0
		add_child(omni)


func _build_floor() -> void:
	var floor_mesh: PlaneMesh = PlaneMesh.new()
	floor_mesh.size = Vector2(4, 4)
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.albedo_color = Color(0.015, 0.015, 0.016)
	mat.roughness = 0.7
	floor_mesh.material = mat
	var floor_node: MeshInstance3D = MeshInstance3D.new()
	floor_node.mesh = floor_mesh
	floor_node.position = Vector3(0.09, -0.175, 0.0)
	add_child(floor_node)


func _build_cameras() -> void:
	for cam_name: String in CAMERAS:
		var spec: Array = CAMERAS[cam_name]
		var from: Vector3 = spec[0]
		var target: Vector3 = spec[1]
		var cam: Camera3D = Camera3D.new()
		cam.name = cam_name
		cam.fov = 22.0
		cam.near = 0.01
		add_child(cam)
		cam.look_at_from_position(from, target)
		cam.add_to_group(&"capture_cameras")
	(get_node("CapHero") as Camera3D).make_current()
