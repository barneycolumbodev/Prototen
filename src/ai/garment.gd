class_name Garment
extends Resource
## One item of the triad wardrobe (owner, 2026-11-11: "clothes they can wear
## that are randomly selected from a bank"). The meshes are in
## assets/characters/triad/triad_wardrobe.gltf (w_<mesh> and its severable
## parts w_<mesh>__<part>), built by raw_assets/characters/triad/wardrobe.py.
## Colours are drawn per man from these lists; data/enemies/wardrobe/*.tres.
##
## A whole-body garment (whole_body) is a complete man made with Tripo3D and
## fitted to the triad rig (raw_assets/characters/triad_tripo/, docs/design.md
## §5.6b): his clothes, skin, face and tattoos in one mesh with its own
## textures, worn instead of the body and the rest of the wardrobe.
## data/enemies/bodies/*.tres.

## Shader slot (triad.gdshader tints and prints are per slot).
enum Slot { SKIN, INNER, TOP, BOTTOM, SHOES, HAIR, HAT, ACCESSORY }

## Mesh id in the wardrobe glTF (without the w_ prefix). A whole body's is
## tp_<id>: its glTF and textures are in assets/characters/triad_tripo/<id>/.
@export var mesh: StringName
@export var slot: Slot = Slot.TOP
## Main colour: one is picked per man. Cloth is painted mid-grey, so these are
## the colours as they'll look.
@export var colors: PackedColorArray = PackedColorArray([Color(0.5, 0.5, 0.5)])
## Second colour (rib knit, stripes, laces, the cap's peak). Empty: a darker main.
@export var trims: PackedColorArray = PackedColorArray()
## Prints this garment can carry (TriadLook.PRINTS); empty: always plain.
@export var prints: PackedInt32Array = PackedInt32Array()
@export_range(0.0, 1.0) var print_chance: float = 0.0
## Colours a print's motifs are drawn in (two per print are picked).
@export var print_colors: PackedColorArray = PackedColorArray()
## Hair that a cap or beanie can go over.
@export var fits_under_hat: bool = true

@export_group("Coverage")
## How far down the arm it covers, metres from the shoulder (0: none; a
## tee 0.185, long sleeves 0.55). Tops and inners.
@export_range(0.0, 0.6) var sleeve: float = 0.0
## How far down the leg it covers, metres from the hip joint (shorts 0.48,
## trousers 0.81). Bottoms.
@export_range(0.0, 0.9) var leg: float = 0.0
## How much further in the skin it covers is drawn (loose cloth needs more),
## so the body never shows through it where joints bend (triad.gdshader).
@export_range(0.0, 0.03) var inset: float = 0.006

@export_group("Whole body")
## A complete man (skin, face, clothes) in one mesh with his own textures:
## the triad body and every other garment are left off.
@export var whole_body: bool = false
## He wears his own plate carrier, so the role's vest mesh stays hidden.
@export var own_vest: bool = false
