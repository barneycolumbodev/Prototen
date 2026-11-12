#!/usr/bin/env python3
"""Writes the wardrobe data: data/enemies/wardrobe/<garment>.tres (Garment) and
data/enemies/outfits/<outfit>.tres (Outfit), the bank each triad member's
clothes are drawn from (owner, 2026-11-11). Run once to (re)create the bank;
after that the .tres files are the source: tune colours and chances there.

Colours are sRGB, as they'll look. Many light and bright ones on purpose:
the docks are dark, and men in black vanished into them.

Usage: python3 raw_assets/characters/triad/wardrobe_data.py
"""
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
WDIR = os.path.join(ROOT, "data", "enemies", "wardrobe")
ODIR = os.path.join(ROOT, "data", "enemies", "outfits")

SLOT = {"skin": 0, "inner": 1, "top": 2, "bottom": 3, "shoes": 4, "hair": 5, "hat": 6, "accessory": 7}
FLORAL, CAMO, CHECK, CLOUDS = 0, 1, 2, 3

C = {
    "white": (0.92, 0.91, 0.88), "offwhite": (0.84, 0.81, 0.74), "lightgrey": (0.68, 0.68, 0.68),
    "heather": (0.5, 0.51, 0.53), "charcoal": (0.2, 0.2, 0.22), "black": (0.07, 0.07, 0.08),
    "red": (0.78, 0.1, 0.08), "crimson": (0.55, 0.05, 0.07), "maroon": (0.38, 0.07, 0.09),
    "orange": (0.92, 0.42, 0.08), "yellow": (0.93, 0.76, 0.15), "mustard": (0.75, 0.58, 0.14),
    "lime": (0.5, 0.75, 0.2), "green": (0.1, 0.45, 0.22), "teal": (0.08, 0.55, 0.55),
    "sky": (0.45, 0.66, 0.86), "royal": (0.12, 0.26, 0.72), "navy": (0.08, 0.1, 0.25),
    "purple": (0.38, 0.16, 0.5), "pink": (0.92, 0.5, 0.62), "olive": (0.36, 0.38, 0.2),
    "khaki": (0.62, 0.55, 0.38), "sand": (0.76, 0.68, 0.5), "brown": (0.3, 0.19, 0.11),
    "tan": (0.55, 0.38, 0.22), "oxblood": (0.3, 0.06, 0.06), "cream": (0.86, 0.8, 0.66),
    "indigo": (0.12, 0.19, 0.38), "denim": (0.22, 0.32, 0.52), "lightwash": (0.45, 0.56, 0.7),
    "gold": (0.95, 0.74, 0.32), "silver": (0.85, 0.86, 0.9), "gunmetal": (0.32, 0.32, 0.34),
    "hair_black": (0.13, 0.12, 0.12), "hair_brown": (0.22, 0.16, 0.12), "bleach": (0.9, 0.78, 0.48),
    "dyed_red": (0.6, 0.14, 0.08), "ash": (0.55, 0.55, 0.56),
    "camo_green": (0.3, 0.33, 0.2), "camo_brown": (0.33, 0.24, 0.15), "camo_tan": (0.6, 0.55, 0.4),
}


def cols(*names):
    return [C[n] for n in names]


# id: slot, colours, trims, prints, print chance, print colours, fits under a hat
GARMENTS = {
    "singlet": ("inner", cols("white", "white", "white", "black", "lightgrey", "red", "yellow"), [], [], 0, [], True),
    "tee": ("inner", cols("white", "white", "lightgrey", "red", "yellow", "teal", "royal", "olive", "orange", "sky"),
            [], [CAMO, CHECK], 0.15, cols("camo_green", "camo_brown", "black", "white"), True),
    "shirt": ("top", cols("red", "royal", "white", "teal", "yellow", "maroon", "sky", "orange", "pink"), [],
              [FLORAL, FLORAL, FLORAL, CLOUDS, CHECK], 0.75,
              cols("white", "yellow", "pink", "green", "red", "black", "sky", "orange"), True),
    "shirt_open": ("top", cols("red", "royal", "white", "teal", "yellow", "maroon", "sky", "orange", "pink"), [],
                   [FLORAL, FLORAL, FLORAL, CLOUDS, CHECK], 0.75,
                   cols("white", "yellow", "pink", "green", "red", "black", "sky", "orange"), True),
    "bomber": ("top", cols("olive", "red", "orange", "sky", "sand", "royal", "white", "black"),
               cols("black", "black", "charcoal", "orange"), [CAMO], 0.15, cols("camo_green", "camo_brown", "black"), True),
    "hoodie": ("top", cols("white", "lightgrey", "heather", "red", "yellow", "royal", "olive", "pink", "orange", "black"),
               cols("white", "black", "red"), [CAMO], 0.2, cols("camo_green", "camo_brown", "camo_tan", "black"), True),
    "track": ("top", cols("red", "royal", "black", "teal", "yellow", "green", "white", "purple"),
              cols("white", "white", "yellow", "black", "red"), [], 0, [], True),
    "leather": ("top", cols("black", "brown", "oxblood", "tan", "tan", "oxblood"), [], [], 0, [], True),
    "cargo": ("bottom", cols("khaki", "olive", "black", "heather", "sand"), [], [CAMO], 0.35,
              cols("camo_green", "camo_brown", "camo_tan", "black", "charcoal"), True),
    "jeans": ("bottom", cols("indigo", "denim", "denim", "lightwash", "black", "heather"), [], [], 0, [], True),
    "trackpants": ("bottom", cols("black", "navy", "red", "heather", "royal", "green"),
                   cols("white", "white", "yellow", "red"), [], 0, [], True),
    "shorts": ("bottom", cols("khaki", "olive", "black", "navy", "heather", "sand"), [], [CAMO], 0.25,
               cols("camo_green", "camo_brown", "camo_tan"), True),
    "slacks": ("bottom", cols("black", "charcoal", "navy", "cream", "tan"), [], [], 0, [], True),
    "sneakers": ("shoes", cols("white", "white", "white", "black", "red", "lightgrey"),
                 cols("black", "red", "royal", "white", "yellow"), [], 0, [], True),
    "boots": ("shoes", cols("black", "black", "brown", "tan"), cols("black", "tan"), [], 0, [], True),
    "hair_fade": ("hair", cols("hair_black", "hair_black", "hair_black", "hair_brown", "bleach"), [], [], 0, [], True),
    "hair_slick": ("hair", cols("hair_black", "hair_black", "hair_brown", "ash"), [], [], 0, [], False),
    "hair_spiky": ("hair", cols("hair_black", "bleach", "bleach", "dyed_red", "hair_brown"), [], [], 0, [], False),
    "hair_buzz": ("hair", cols("hair_black", "hair_black", "hair_brown", "bleach"), [], [], 0, [], True),
    "cap": ("hat", cols("black", "red", "white", "royal", "olive", "yellow"), cols("black", "white", "red"), [], 0, [], True),
    "beanie": ("hat", cols("black", "heather", "red", "olive", "navy", "orange"), [], [], 0, [], True),
    "glasses": ("accessory", cols("gold", "silver", "gunmetal", "black"), [], [], 0, [], True),
    "chain": ("accessory", cols("gold", "gold", "silver"), [], [], 0, [], True),
    "watch": ("accessory", cols("gold", "silver", "gunmetal"), [], [], 0, [], True),
}

# name: role, weight, tops, inners, bottoms, shoes, hair, bald, hats, hat chance, accessories,
#       accessory chance, tattoo chance, bare chest chance
OUTFITS = {
    "street": (1.0, ["tee", "tee", "hoodie", "track", "bomber", "shirt_open"], ["singlet", "tee"],
               ["jeans", "cargo", "trackpants", "shorts"], ["sneakers", "sneakers", "boots"],
               ["hair_fade", "hair_spiky", "hair_buzz", "hair_slick"], 0.1, ["cap", "beanie"], 0.25,
               ["glasses", "chain", "watch"], 0.2, 0.6, 0.25),
    "summer": (0.8, ["singlet", "singlet", "tee", "shirt_open", "shirt"], ["singlet"],
               ["shorts", "jeans", "cargo", "trackpants"], ["sneakers"],
               ["hair_fade", "hair_spiky", "hair_buzz"], 0.2, ["cap"], 0.2,
               ["chain", "watch", "glasses"], 0.35, 0.85, 0.5),
    "muscle": (1.0, ["hoodie", "track", "tee", "bomber"], [], ["cargo", "cargo", "jeans", "trackpants"],
               ["boots", "sneakers"], ["hair_buzz", "hair_fade", "hair_spiky"], 0.25, ["beanie", "cap"], 0.3,
               ["chain", "watch"], 0.15, 0.55, 0.0),
    "boss": (1.0, ["shirt", "shirt_open", "leather", "shirt_open"], ["singlet", "tee"], ["slacks", "slacks", "jeans"],
             ["boots", "sneakers"], ["hair_slick", "hair_fade", "hair_buzz"], 0.1, [], 0.0,
             ["glasses", "chain", "watch"], 0.65, 0.7, 0.35),
}
ROLE_OUTFITS = {"gunman": ["street", "summer"], "enforcer": ["muscle"], "red_pole": ["boss"]}


def color_array(cs):
    return "PackedColorArray(" + ", ".join(f"{r:.3g}, {g:.3g}, {b:.3g}, 1" for r, g, b in cs) + ")"


# Coverage (wardrobe.py's fields): metres down the arm from the shoulder, down
# the leg from the hip, and how far the skin under it is drawn further in.
COVER = {
    "singlet": (0.0, 0.0, 0.0), "tee": (0.185, 0.0, 0.004), "shirt": (0.21, 0.0, 0.008),
    "shirt_open": (0.21, 0.0, 0.008), "bomber": (0.553, 0.0, 0.012), "hoodie": (0.553, 0.0, 0.012),
    "track": (0.553, 0.0, 0.008), "leather": (0.553, 0.0, 0.012),
    "cargo": (0.0, 0.809, 0.008), "jeans": (0.0, 0.809, 0.003), "trackpants": (0.0, 0.809, 0.006),
    "shorts": (0.0, 0.475, 0.008), "slacks": (0.0, 0.819, 0.005),
}


def write_garment(gid, spec):
    slot, colours, trims, prints, chance, pcols, hat_ok = spec
    sleeve, leg, inset = COVER.get(gid, (0.0, 0.0, 0.0))
    lines = [
        '[gd_resource type="Resource" script_class="Garment" load_steps=2 format=3]',
        "",
        '[ext_resource type="Script" path="res://src/ai/garment.gd" id="1"]',
        "",
        "[resource]",
        'script = ExtResource("1")',
        f'mesh = &"{gid}"',
        f"slot = {SLOT[slot]}",
        f"colors = {color_array(colours)}",
        f"trims = {color_array(trims)}",
        "prints = PackedInt32Array(" + ", ".join(str(p) for p in prints) + ")",
        f"print_chance = {chance}",
        f"print_colors = {color_array(pcols)}",
        f"fits_under_hat = {'true' if hat_ok else 'false'}",
        f"sleeve = {sleeve}",
        f"leg = {leg}",
        f"inset = {inset}",
        "",
    ]
    with open(os.path.join(WDIR, f"{gid}.tres"), "w") as f:
        f.write("\n".join(lines))


def write_outfit(name, spec):
    (weight, tops, inners, bottoms, shoes, hair, bald, hats, hat_chance, acc, acc_chance, tat,
     bare) = spec
    used = []
    for lst in (tops, inners, bottoms, shoes, hair, hats, acc):
        for g in lst:
            if g not in used:
                used.append(g)
    ids = {g: str(i + 3) for i, g in enumerate(used)}
    lines = [f'[gd_resource type="Resource" script_class="Outfit" load_steps={len(used) + 3} format=3]', "",
             '[ext_resource type="Script" path="res://src/ai/outfit.gd" id="1"]',
             '[ext_resource type="Script" path="res://src/ai/garment.gd" id="2"]']
    for g in used:
        lines.append(f'[ext_resource type="Resource" path="res://data/enemies/wardrobe/{g}.tres" id="{ids[g]}"]')

    def arr(lst):
        return 'Array[ExtResource("2")]([' + ", ".join(f'ExtResource("{ids[g]}")' for g in lst) + "])"
    lines += ["", "[resource]", 'script = ExtResource("1")', f'display_name = "{name.capitalize()}"',
              f"weight = {weight}", f"tops = {arr(tops)}", f"inners = {arr(inners)}", f"bottoms = {arr(bottoms)}",
              f"shoes = {arr(shoes)}", f"hair = {arr(hair)}", f"bald_chance = {bald}", f"hats = {arr(hats)}",
              f"hat_chance = {hat_chance}", f"accessories = {arr(acc)}", f"accessory_chance = {acc_chance}",
              f"tattoo_chance = {tat}", f"bare_chest_chance = {bare}", ""]
    with open(os.path.join(ODIR, f"{name}.tres"), "w") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(WDIR, exist_ok=True)
    os.makedirs(ODIR, exist_ok=True)
    for gid, spec in GARMENTS.items():
        write_garment(gid, spec)
    for name, spec in OUTFITS.items():
        write_outfit(name, spec)
    print(f"{len(GARMENTS)} garments, {len(OUTFITS)} outfits")


if __name__ == "__main__":
    main()
