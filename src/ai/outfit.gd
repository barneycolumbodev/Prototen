class_name Outfit
extends Resource
## A style a triad member dresses in: which garments it draws from for each
## slot and how often the extras turn up (data/enemies/outfits/*.tres). Each
## role (EnemyConfig.outfits) has a few; TriadLook picks one per man and then
## a garment for each slot, the colours, prints, tattoos and facial hair.

@export var display_name: String = "Street"
## Relative chance among the role's outfits.
@export_range(0.0, 10.0) var weight: float = 1.0
## The outer top (a tee, a hoodie, an open shirt...).
@export var tops: Array[Garment] = []
## Worn under an open top (a singlet under an open shirt, a tee under a
## leather jacket). Only used if the top picked is in `open_tops`.
@export var inners: Array[Garment] = []
@export var open_tops: Array[StringName] = [&"shirt_open", &"leather"]
## Chance of nothing under an open top (bare chest).
@export_range(0.0, 1.0) var bare_chest_chance: float = 0.2
@export var bottoms: Array[Garment] = []
@export var shoes: Array[Garment] = []
@export var hair: Array[Garment] = []
@export_range(0.0, 1.0) var bald_chance: float = 0.1
@export var hats: Array[Garment] = []
@export_range(0.0, 1.0) var hat_chance: float = 0.2
## Each rolled on its own with accessory_chance (sunglasses, a chain, a watch).
@export var accessories: Array[Garment] = []
@export_range(0.0, 1.0) var accessory_chance: float = 0.3
## Chance of each tattoo set (three sets, each over a random choice of body regions).
@export_range(0.0, 1.0) var tattoo_chance: float = 0.6
## Multiplies the painted skin (one per man).
@export var skin_tones: PackedColorArray = PackedColorArray([Color(1, 1, 1), Color(0.93, 0.9, 0.86),
		Color(1.04, 0.98, 0.9), Color(0.84, 0.76, 0.68), Color(0.96, 0.9, 0.8)])
## Chance of stubble, then of a goatee and moustache on top.
@export_range(0.0, 1.0) var stubble_chance: float = 0.6
@export_range(0.0, 1.0) var goatee_chance: float = 0.25
