class_name BodyColors
extends Resource
## The operative's colours (docs/design.md §3.7; owner, 2026-11-10: "a full
## part by part color customizer for my character"). One colour and finish
## per suit piece (helmet, visor, undersuit, the plates of the torso, arms,
## hands and legs, boots, trim, lights) and per installed part (its
## hardware and its lights). A channel that isn't set keeps the look it was
## built with.
##
## The suit and the first-person arms are baked texture sets: they're
## recoloured by the paint shader with a region map
## (`<name>_regions.png`, tools/colors/build_regions.py). Part hardware is
## painted as one piece. Models with plain named materials (the active
## parts' first-person arms) are painted by material name.

enum Finish { DEFAULT, MATTE, SATIN, GLOSS, METAL }

const SHADER: Shader = preload("res://src/body/suit_paint.gdshader")
const SUIT_CHANNELS: Array[StringName] = [&"helmet", &"visor", &"undersuit", &"torso", &"arms", &"hands", &"legs", &"boots", &"trim", &"lights"]
const SUIT_LABELS: Array[String] = ["Helmet", "Visor", "Undersuit", "Torso plates", "Arm plates", "Hand plates", "Leg plates", "Boots", "Trim and hardpoints", "Suit lights"]
const FINISH_NAMES: Array[String] = ["as built", "matte", "satin", "gloss", "metal"]
## Roughness and metallic of each finish (DEFAULT keeps the baked values).
const FINISH_SURF: Array[Vector2] = [Vector2(-1, -1), Vector2(0.8, 0.0), Vector2(0.42, 0.0), Vector2(0.14, 0.0), Vector2(0.28, 1.0)]
## Luminance (linear) of each suit channel's own base colour: the baked
## albedo divided by this is the detail the new colour keeps.
const SUIT_REF: Array[float] = [0.009, 0.03, 0.017, 0.009, 0.009, 0.009, 0.009, 0.014, 0.125, 0.72]
## The arms' texture sets were baked from lighter materials.
const ARMS_REF: Array[float] = [0.024, 0.03, 0.047, 0.024, 0.047, 0.024, 0.024, 0.024, 0.032, 0.55]
## Material names on unbaked models (the actives' arms) -> suit channel.
const NAME_CHANNEL: Dictionary[String, StringName] = {
	"graft": &"arms", "weave": &"undersuit", "polymer": &"hands", "gunmetal": &"trim",
}
## Swatches for the quick palette (name, colour).
const PALETTE: Array[Array] = [
	["Graft black", Color(0.035, 0.036, 0.04)], ["Graphite", Color(0.16, 0.17, 0.18)], ["Gunmetal", Color(0.3, 0.32, 0.34)],
	["Steel", Color(0.55, 0.57, 0.6)], ["Arctic", Color(0.86, 0.88, 0.9)], ["Bone", Color(0.8, 0.74, 0.62)],
	["Desert tan", Color(0.62, 0.5, 0.34)], ["Coyote", Color(0.42, 0.32, 0.2)], ["Olive drab", Color(0.27, 0.29, 0.16)],
	["Ranger green", Color(0.16, 0.24, 0.15)], ["Forest", Color(0.07, 0.2, 0.1)], ["Seaglass", Color(0.36, 0.86, 0.78)],
	["Teal", Color(0.05, 0.4, 0.42)], ["Navy", Color(0.05, 0.09, 0.22)], ["Cobalt", Color(0.08, 0.25, 0.7)],
	["Ice blue", Color(0.45, 0.72, 1.0)], ["Violet", Color(0.36, 0.2, 0.62)], ["Magenta", Color(0.75, 0.12, 0.5)],
	["Crimson", Color(0.55, 0.04, 0.06)], ["Signal red", Color(0.9, 0.1, 0.08)], ["Rust", Color(0.5, 0.2, 0.08)],
	["Hazard orange", Color(1.0, 0.45, 0.05)], ["Amber", Color(1.0, 0.72, 0.3)], ["Hazard yellow", Color(0.95, 0.82, 0.1)],
	["Gold", Color(0.8, 0.6, 0.2)], ["Copper", Color(0.72, 0.4, 0.24)], ["White", Color(1.0, 1.0, 1.0)],
]

@export var colors: Dictionary[StringName, Color] = {}
@export var finishes: Dictionary[StringName, int] = {}

var _region_cache: Dictionary[String, Texture2D] = {}
var _lum_cache: Dictionary[String, float] = {}


static func part_key(id: StringName) -> StringName:
	return StringName("part:" + String(id))


static func glow_key(id: StringName) -> StringName:
	return StringName("glow:" + String(id))


func has(channel: StringName) -> bool:
	return colors.has(channel)


func color(channel: StringName, fallback: Color = Color.BLACK) -> Color:
	return colors.get(channel, fallback)


func finish(channel: StringName) -> int:
	return finishes.get(channel, Finish.DEFAULT)


func set_color(channel: StringName, c: Color) -> void:
	colors[channel] = Color(c.r, c.g, c.b)


func set_finish(channel: StringName, f: int) -> void:
	if f == Finish.DEFAULT:
		finishes.erase(channel)
	else:
		finishes[channel] = clampi(f, 0, FINISH_NAMES.size() - 1)


## Back to the look it was built with.
func clear(channel: StringName) -> void:
	colors.erase(channel)
	finishes.erase(channel)


func is_default() -> bool:
	return colors.is_empty() and finishes.is_empty()


func copy() -> BodyColors:
	var c: BodyColors = BodyColors.new()
	c.colors = colors.duplicate()
	c.finishes = finishes.duplicate()
	return c


# ------------------------------------------------------------------ applying

## Paints a model: every baked surface that has a region map beside its
## albedo texture (the operative, the first-person arms), and, with `named`,
## plain materials by name (the actives' arms). Surfaces it doesn't know
## are left alone. Safe to call again after the colours change.
func apply_to_model(root: Node, named: bool = true) -> void:
	for n: Node in root.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = n as MeshInstance3D
		if mi.mesh == null:
			continue
		for i: int in mi.mesh.get_surface_count():
			var src: BaseMaterial3D = mi.mesh.surface_get_material(i) as BaseMaterial3D
			if src == null:
				continue
			var regions: Texture2D = _regions_for(src)
			if regions:
				var arms: bool = src.albedo_texture.resource_path.contains("fp_arms")
				mi.set_surface_override_material(i, _suit_material(src, regions, ARMS_REF if arms else SUIT_REF))
			elif named and src.albedo_texture == null and NAME_CHANNEL.has(src.resource_name):
				var ch: StringName = NAME_CHANNEL[src.resource_name]
				if has(ch) or finish(ch) != Finish.DEFAULT:
					mi.set_surface_override_material(i, _plain(src, ch, true))
				else:
					mi.set_surface_override_material(i, null)


## Paints the mounted hardware of one part (`part:<id>` and `glow:<id>`).
func apply_to_part(node: Node, id: StringName) -> void:
	var key: StringName = part_key(id)
	var gkey: StringName = glow_key(id)
	if not has(key) and not has(gkey) and finish(key) == Finish.DEFAULT:
		return
	var meshes: Array[Node] = node.find_children("*", "MeshInstance3D", true, false)
	if node is MeshInstance3D:
		meshes.append(node)
	for n: Node in meshes:
		var mi: MeshInstance3D = n as MeshInstance3D
		if mi.mesh == null:
			continue
		for i: int in mi.mesh.get_surface_count():
			var src: BaseMaterial3D = mi.mesh.surface_get_material(i) as BaseMaterial3D
			if src == null:
				src = mi.material_override as BaseMaterial3D
			if src == null:
				continue
			if src.albedo_texture:
				mi.set_surface_override_material(i, _part_material(src, key, gkey))
			else:
				var lit: bool = src.emission_enabled
				var m: StandardMaterial3D = src.duplicate() as StandardMaterial3D
				if lit and has(gkey):
					m.emission = color(gkey)
					m.albedo_color = color(gkey)
				elif not lit:
					m = _plain(src, key, false)
				mi.set_surface_override_material(i, m)
				if mi.material_override:
					mi.material_override = m


func _regions_for(src: BaseMaterial3D) -> Texture2D:
	if src.albedo_texture == null:
		return null
	var path: String = src.albedo_texture.resource_path
	if not path.ends_with("_basecolor.png"):
		return null
	var rp: String = path.replace("_basecolor.png", "_regions.png")
	if not _region_cache.has(rp):
		_region_cache[rp] = load(rp) as Texture2D if ResourceLoader.exists(rp) else null
	return _region_cache[rp]


func _base_material(src: BaseMaterial3D) -> ShaderMaterial:
	var m: ShaderMaterial = ShaderMaterial.new()
	m.shader = SHADER
	m.resource_name = src.resource_name
	m.set_shader_parameter(&"tex_albedo", src.albedo_texture)
	var ac: Color = src.albedo_color
	m.set_shader_parameter(&"albedo_factor", Vector4(ac.r, ac.g, ac.b, ac.a))
	var orm: Texture2D = src.roughness_texture if src.roughness_texture else src.metallic_texture
	if orm:
		m.set_shader_parameter(&"tex_orm", orm)
	m.set_shader_parameter(&"rough_factor", src.roughness)
	m.set_shader_parameter(&"metal_factor", src.metallic)
	m.set_shader_parameter(&"use_normal", src.normal_enabled and src.normal_texture != null)
	if src.normal_texture:
		m.set_shader_parameter(&"tex_normal", src.normal_texture)
	if src.emission_enabled and src.emission_texture:
		m.set_shader_parameter(&"tex_emission", src.emission_texture)
		m.set_shader_parameter(&"emission_energy", src.emission_energy_multiplier)
	else:
		m.set_shader_parameter(&"emission_energy", 0.0)
	return m


func _suit_material(src: BaseMaterial3D, regions: Texture2D, ref: Array[float]) -> ShaderMaterial:
	var m: ShaderMaterial = _base_material(src)
	m.set_shader_parameter(&"tex_region", regions)
	var paint: PackedVector4Array = PackedVector4Array()
	var surf: PackedVector4Array = PackedVector4Array()
	paint.resize(12)
	surf.resize(12)
	surf.fill(Vector4(-1, -1, 1, 0))
	for k: int in SUIT_CHANNELS.size():
		var ch: StringName = SUIT_CHANNELS[k]
		var f: Vector2 = FINISH_SURF[finish(ch)]
		surf[k + 1] = Vector4(f.x, f.y, ref[k], 0.0)
		if has(ch):
			var c: Color = color(ch).srgb_to_linear()
			paint[k + 1] = Vector4(c.r, c.g, c.b, 1.0)
	m.set_shader_parameter(&"paint", paint)
	m.set_shader_parameter(&"surf", surf)
	if has(&"lights"):
		m.set_shader_parameter(&"glow_paint", _glow(color(&"lights")))
	return m


func _part_material(src: BaseMaterial3D, key: StringName, gkey: StringName) -> ShaderMaterial:
	var m: ShaderMaterial = _base_material(src)
	m.set_shader_parameter(&"single_region", 1)
	var paint: PackedVector4Array = PackedVector4Array()
	var surf: PackedVector4Array = PackedVector4Array()
	paint.resize(12)
	surf.resize(12)
	var f: Vector2 = FINISH_SURF[finish(key)]
	surf.fill(Vector4(f.x, f.y, _average_luminance(src.albedo_texture), 0.0))
	if has(key):
		var c: Color = color(key).srgb_to_linear()
		# Mostly the new paint; a little of the baked colour stays so mixed materials still read.
		paint[1] = Vector4(c.r, c.g, c.b, 0.88)
	m.set_shader_parameter(&"paint", paint)
	m.set_shader_parameter(&"surf", surf)
	if has(gkey):
		m.set_shader_parameter(&"glow_paint", _glow(color(gkey)))
	return m


## A plain (untextured) material in a channel's colour. `exact`: the colour
## as picked; otherwise scaled by how light the material was, so a part's
## dark and bright pieces stay apart.
func _plain(src: BaseMaterial3D, ch: StringName, exact: bool) -> StandardMaterial3D:
	var m: StandardMaterial3D = src.duplicate() as StandardMaterial3D
	if has(ch):
		var c: Color = color(ch)
		if not exact:
			var k: float = clampf(sqrt(maxf(src.albedo_color.get_luminance(), 0.001) / 0.06), 0.45, 1.8)
			c = Color(c.r * k, c.g * k, c.b * k)
		m.albedo_color = c
	var f: Vector2 = FINISH_SURF[finish(ch)]
	if f.x >= 0.0:
		m.roughness = f.x
		m.metallic = f.y
	return m


static func _glow(c: Color) -> Vector4:
	var l: Color = c.srgb_to_linear()
	var peak: float = maxf(maxf(l.r, l.g), maxf(l.b, 0.02))
	return Vector4(l.r / peak, l.g / peak, l.b / peak, 1.0)


func _average_luminance(tex: Texture2D) -> float:
	var key: String = tex.resource_path
	if not _lum_cache.has(key):
		var lum: float = 0.08
		var img: Image = tex.get_image()
		if img:
			if img.is_compressed():
				img.decompress()
			img.resize(8, 8, Image.INTERPOLATE_LANCZOS)
			var sum: float = 0.0
			var n: int = 0
			for y: int in 8:
				for x: int in 8:
					var px: float = img.get_pixel(x, y).srgb_to_linear().get_luminance()
					# Unused atlas space is black: leave it out of the average.
					if px > 0.002:
						sum += px
						n += 1
			if n > 0:
				lum = sum / n
		_lum_cache[key] = lum
	return _lum_cache[key]


# ------------------------------------------------------------------ saving

func to_dict() -> Dictionary:
	var out: Dictionary = {}
	for k: StringName in colors:
		out[String(k)] = colors[k].to_html(false)
	for k: StringName in finishes:
		out["finish:" + String(k)] = finishes[k]
	return out


static func from_dict(d: Dictionary) -> BodyColors:
	var c: BodyColors = BodyColors.new()
	for k: Variant in d:
		var key: String = str(k)
		if key.begins_with("finish:"):
			var f: int = d[k]
			c.finishes[StringName(key.trim_prefix("finish:"))] = f
		else:
			var hex: String = d[k]
			c.colors[StringName(key)] = Color.html(hex)
	return c
