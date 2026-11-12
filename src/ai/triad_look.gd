class_name TriadLook
extends RefCounted
## What one triad member looks like: the garments he wears, their colours
## and prints, his skin tone, tattoos and facial hair. Picked at spawn from
## his role's outfits (EnemyConfig.outfits) and pushed into his material
## (triad.gdshader). Same seed, same man.

## Prints in assets/characters/triad/textures/triad_prints.png, one per channel.
enum Print { FLORAL, CAMO, CHECK, CLOUDS }
const SLOTS: int = 8
## Tattoo regions (bits): left arm, right arm, chest, back, neck, hands.
const TATTOO_REGIONS: int = 6

var garments: Array[Garment] = []
var main: PackedColorArray = PackedColorArray()
var trim: PackedColorArray = PackedColorArray()
var print_id: PackedInt32Array = PackedInt32Array()
var print_a: PackedColorArray = PackedColorArray()
var print_b: PackedColorArray = PackedColorArray()
var skin_tone: Color = Color(1, 1, 1)
## Per tattoo set: a bitmask of TATTOO_REGIONS.
var tattoos: PackedInt32Array = PackedInt32Array([0, 0, 0])
## 0 = clean, 1 = stubble, 2 = stubble with a goatee and moustache.
var beard: int = 0
var outfit_name: String = ""


func _init() -> void:
	main.resize(SLOTS)
	trim.resize(SLOTS)
	print_id.resize(SLOTS)
	print_a.resize(SLOTS)
	print_b.resize(SLOTS)
	for i: int in SLOTS:
		main[i] = Color(0.5, 0.5, 0.5)
		trim[i] = Color(0.3, 0.3, 0.3)
		print_id[i] = -1


## Mesh ids of everything he wears, in slot order (the cache key for merged meshes).
func key() -> String:
	var ids: PackedStringArray = PackedStringArray()
	for g: Garment in garments:
		ids.append(String(g.mesh))
	return ",".join(ids)


func has(mesh: StringName) -> bool:
	for g: Garment in garments:
		if g.mesh == mesh:
			return true
	return false


static func pick(outfits: Array[Outfit], rng: RandomNumberGenerator) -> TriadLook:
	var look: TriadLook = TriadLook.new()
	if outfits.is_empty():
		return look
	var total: float = 0.0
	for o: Outfit in outfits:
		total += o.weight
	var r: float = rng.randf() * total
	var outfit: Outfit = outfits[-1]
	for o: Outfit in outfits:
		r -= o.weight
		if r <= 0.0:
			outfit = o
			break
	look.outfit_name = outfit.display_name
	var top: Garment = _one(outfit.tops, rng)
	look._wear(top, rng)
	if top and top.mesh in outfit.open_tops and not outfit.inners.is_empty() and rng.randf() >= outfit.bare_chest_chance:
		look._wear(_one(outfit.inners, rng), rng)
	look._wear(_one(outfit.bottoms, rng), rng)
	look._wear(_one(outfit.shoes, rng), rng)
	var hat: Garment = _one(outfit.hats, rng) if rng.randf() < outfit.hat_chance else null
	if rng.randf() >= outfit.bald_chance:
		var hairs: Array[Garment] = []
		for h: Garment in outfit.hair:
			if hat == null or h.fits_under_hat:
				hairs.append(h)
		look._wear(_one(hairs, rng), rng)
	look._wear(hat, rng)
	for a: Garment in outfit.accessories:
		if rng.randf() < outfit.accessory_chance:
			look._wear(a, rng)
	if not outfit.skin_tones.is_empty():
		look.skin_tone = outfit.skin_tones[rng.randi() % outfit.skin_tones.size()]
	for i: int in 3:
		if rng.randf() < outfit.tattoo_chance:
			# A random handful of regions, at least one.
			var bits: int = 0
			while bits == 0:
				for b: int in TATTOO_REGIONS:
					if rng.randf() < 0.55:
						bits |= 1 << b
			look.tattoos[i] = bits
	if rng.randf() < outfit.stubble_chance:
		look.beard = 2 if rng.randf() < outfit.goatee_chance else 1
	return look


static func _one(list: Array[Garment], rng: RandomNumberGenerator) -> Garment:
	return list[rng.randi() % list.size()] if not list.is_empty() else null


func _wear(g: Garment, rng: RandomNumberGenerator) -> void:
	if g == null:
		return
	garments.append(g)
	var s: int = g.slot
	main[s] = g.colors[rng.randi() % g.colors.size()] if not g.colors.is_empty() else Color(0.5, 0.5, 0.5)
	trim[s] = g.trims[rng.randi() % g.trims.size()] if not g.trims.is_empty() else main[s].darkened(0.35)
	print_id[s] = -1
	if not g.prints.is_empty() and rng.randf() < g.print_chance:
		print_id[s] = g.prints[rng.randi() % g.prints.size()]
		var pc: PackedColorArray = g.print_colors if not g.print_colors.is_empty() else PackedColorArray([Color(0.9, 0.85, 0.75), Color(0.15, 0.15, 0.15)])
		print_a[s] = pc[rng.randi() % pc.size()]
		print_b[s] = pc[rng.randi() % pc.size()]


## Pushes the look into a triad.gdshader material.
func apply(m: ShaderMaterial) -> void:
	var mains: PackedVector3Array = PackedVector3Array()
	var trims: PackedVector3Array = PackedVector3Array()
	var pa: PackedVector3Array = PackedVector3Array()
	var pb: PackedVector3Array = PackedVector3Array()
	for i: int in SLOTS:
		mains.append(_lin(main[i]))
		trims.append(_lin(trim[i]))
		pa.append(_lin(print_a[i]))
		pb.append(_lin(print_b[i]))
	m.set_shader_parameter(&"tint_main", mains)
	m.set_shader_parameter(&"tint_trim", trims)
	m.set_shader_parameter(&"print_id", print_id)
	m.set_shader_parameter(&"print_a", pa)
	m.set_shader_parameter(&"print_b", pb)
	m.set_shader_parameter(&"skin_tint", Vector3(skin_tone.r, skin_tone.g, skin_tone.b))
	m.set_shader_parameter(&"tattoo_bits", tattoos)
	m.set_shader_parameter(&"beard", beard)
	m.set_shader_parameter(&"slot_inset", insets())
	var cover: Vector4 = coverage()
	m.set_shader_parameter(&"cover_arm", cover.x)
	m.set_shader_parameter(&"cover_leg", cover.y)
	m.set_shader_parameter(&"inset_torso", cover.z)
	m.set_shader_parameter(&"inset_limb", cover.w)


## What his clothes cover: x = metres down the arms from the shoulder, y =
## down the legs from the hip, z = extra inset of the skin under his top,
## w = under his sleeves and trouser legs.
func coverage() -> Vector4:
	var c: Vector4 = Vector4.ZERO
	for g: Garment in garments:
		if g.slot == Garment.Slot.TOP or g.slot == Garment.Slot.INNER:
			c.x = maxf(c.x, g.sleeve)
			c.z = maxf(c.z, g.inset)
			if g.sleeve > 0.0:
				c.w = maxf(c.w, g.inset)
		elif g.slot == Garment.Slot.BOTTOM:
			c.y = maxf(c.y, g.leg)
			c.w = maxf(c.w, g.inset)
			c.z = maxf(c.z, g.inset * 0.5)
	return c


## How far each slot is drawn inside its modelled shell: what's under
## another layer steps back so it can't show through it.
func insets() -> PackedFloat32Array:
	var out: PackedFloat32Array = PackedFloat32Array()
	out.resize(SLOTS)
	var worn: Dictionary[int, bool] = {}
	for g: Garment in garments:
		worn[int(g.slot)] = true
	if worn.has(Garment.Slot.TOP) and worn.has(Garment.Slot.INNER):
		out[Garment.Slot.INNER] = 0.009
	if worn.has(Garment.Slot.HAT) and worn.has(Garment.Slot.HAIR):
		out[Garment.Slot.HAIR] = 0.004
	return out


## Colours are picked as they look (sRGB); the shader works in linear light.
static func _lin(c: Color) -> Vector3:
	var l: Color = c.srgb_to_linear()
	return Vector3(l.r, l.g, l.b)
