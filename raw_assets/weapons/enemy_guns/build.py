"""Enemy guns (third person), rebuilt 2026-11-16 with real detail and baked textures.

Owner, 2026-11-16: "Don't hesitate to make more or more detailed 3d models for enemy weapons...
Enemies and how they look is the absolute weakest part of the game so far." The first set were a
handful of flat-coloured boxes. Each gun is now modelled twice from the same code (HIGH: bevels,
lettering, small parts; LOW: fewer segments), and HIGH is baked onto LOW (base colour with cavity
grime, ORM, normal) like the player's guns (raw_assets/_lib/bakeutil.py). One material, one draw.

Guns (Chinese service and commercial patterns, what a Hong Kong triad would run):
  type56   Type 56 assault rifle (AK pattern): milled receiver, hooded front sight, folded spike
           bayonet, laminated wood, ribbed steel magazine. Gunman.
  pump     Norinco 982-style pump shotgun (870 pattern): ejection port, magazine tube, ribbed forend,
           pistol-grip stock with a recoil pad. Enforcer.
  smg      Type 85 submachine gun: tube receiver, perforated barrel jacket, folding wire stock.
           Blue Lantern, Red Pole.
  type79   Type 79 / NDM-86 marksman rifle (Dragunov pattern): skeleton thumbhole stock with a cheek
           rest, long barrel, slotted flash hider, side-mounted 4x scope with a sunshade. Marksman.
  type80   Type 80 general-purpose machine gun (PK pattern): skeleton stock, fluted barrel, carry
           handle, folded bipod, 100-round box with the belt running up into the feed. Gunner.
  qbz95    QBZ-95 bullpup carbine: polymer shell, carry-handle sight, magazine behind the grip,
           yellow-banded armour-piercing magazine. Anti-augment specialist.
  type54   Type 54 pistol (Tokarev pattern): slide serrations, star-in-circle grips. Shield man.

Hand positions are shared so one set of character clips fits every long gun:
  origin           = top of the pistol grip (right hand's web)
  SUPPORT (x ~0.25-0.29) = where the left palm cups the handguard / forend
The pistol is held at the same origin (right hand); the shield man's clips put the left hand on his shield.
Axes: +X = muzzle, +Z = up, +Y = the gun's LEFT side, metres.

Muzzle points (also in data/enemies/*.tres, Godot axes x, z, -y -> x, y, z):
  type56 (0.635, 0.047)   pump (0.66, 0.052)   smg (0.355, 0.045)   type79 (0.865, 0.047)
  type80 (0.79, 0.058)    qbz95 (0.445, 0.058) type54 (0.158, 0.026)
The Type 79's scope objective is at (0.245, 0.104, +0.012 left): the game puts the glint there.

Run (about 8 minutes with bakes on 4 cores; --fast renders HIGH only, no bake or export):
  tools/blender.sh raw_assets/weapons/enemy_guns/build.py --out assets/weapons/enemy \
      --preview docs/previews/enemy_guns.png
  One gun: --only type79
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--tex", type=int, default=1024)
ap.add_argument("--only", default="")
ap.add_argument("--fast", action="store_true", help="HIGH only, no bake/export (shape checks)")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
V = Vector


# ---------------------------------------------------------------- materials
def wood_material(name, base, dark, rough=0.5, scale=60.0):
    """Wood with grain along X (wave rings stretched along the stock) and a lacquer sheen."""
    mat = hs.material(name, base, rough, 0.0, wear=tuple(min(1.0, c * 1.6) for c in base), wear_rough=0.35)
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.08, 1.0, 1.0)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    wave = N.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    L.new(mp.outputs["Vector"], wave.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*base, 1)
    ramp.color_ramp.elements[0].position = 0.25
    L.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    # Keep the edge-wear mix if there is one: grain feeds its A input.
    mix = next((n for n in N if n.bl_idname == "ShaderNodeMix"), None)
    if mix:
        L.new(ramp.outputs["Color"], mix.inputs["A"])
    else:
        L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


M = {
    "steel": hs.material("eg_steel", (0.042, 0.044, 0.048), 0.4, 0.9, wear=(0.42, 0.42, 0.43), wear_rough=0.22,
                         bump_scale=900.0, bump_strength=0.08, brushed=0.04),
    "black": hs.material("eg_black", (0.022, 0.022, 0.024), 0.55, 0.6, wear=(0.3, 0.3, 0.31), wear_rough=0.3,
                         bump_scale=1400.0, bump_strength=0.12),
    "poly": hs.material("eg_poly", (0.03, 0.031, 0.032), 0.72, 0.0, wear=(0.09, 0.09, 0.09), wear_rough=0.5,
                        bump_scale=2200.0, bump_strength=0.25),
    "olive": hs.material("eg_olive", (0.07, 0.075, 0.05), 0.7, 0.0, wear=(0.16, 0.16, 0.12), wear_rough=0.5,
                         bump_scale=2200.0, bump_strength=0.2),
    "wood": wood_material("eg_wood", (0.36, 0.14, 0.05), (0.16, 0.05, 0.018)),
    "wood_pale": wood_material("eg_wood_pale", (0.42, 0.24, 0.11), (0.2, 0.09, 0.035), scale=45.0),
    "bakelite": hs.material("eg_bakelite", (0.09, 0.03, 0.02), 0.45, 0.0, wear=(0.2, 0.08, 0.05)),
    "rubber": hs.material("eg_rubber", (0.018, 0.018, 0.018), 0.85, 0.0, bump_scale=3000.0, bump_strength=0.3),
    "brass": hs.material("eg_brass", (0.75, 0.52, 0.2), 0.3, 1.0),
    "lens": hs.material("eg_lens", (0.02, 0.05, 0.08), 0.03, 0.0, emission=((0.25, 0.5, 0.75), 0.6)),
    "yellow": hs.material("eg_yellow", (0.8, 0.6, 0.05), 0.5, 0.0, wear=(0.3, 0.25, 0.1)),
    "red": hs.material("eg_red", (0.55, 0.04, 0.03), 0.5, 0.0),
    "white": hs.material("eg_white", (0.75, 0.74, 0.7), 0.5, 0.0),
}
MATERIALS = list(M.values())


def F(ob, mat, bevel=0.0012, seg=2, angle=40.0):
    return hs.finish(ob, M[mat] if isinstance(mat, str) else mat, bevel=bevel, segments=seg, angle=angle)


def prof(name, mat, xz, w, y=0.0, bevel=0.0015):
    return F(hs.side_profile(name, xz, w, y), mat, bevel=bevel)


def cylx(name, mat, r, x0, x1, z, y=0.0, verts=16, bevel=0.0006, r2=None):
    return F(hs.cyl_x(name, r, x0, x1, verts=verts, z=z, y=y, radius2=r2), mat, bevel=bevel)


def box(name, mat, size, loc, rot=(0, 0, 0), bevel=0.0012):
    return F(hs.box(name, size, loc, rot), mat, bevel=bevel)


def cutbox(target, size, loc, rot=(0, 0, 0)):
    hs.cut(target, hs.box(target.name + "_cut", size, loc, rot))


def high():
    return hs.D is hs.HIGH


def pistol_grip(mat, top=0.005, bottom=(-0.042, -0.108), w=0.031, swell=0.004):
    """A raked pistol grip from the receiver bottom to `bottom` (x, z), a little fuller at the palm swell."""
    bx, bz = bottom
    pts = [(top - 0.034, 0.004), (top + 0.014, 0.004), (bx + 0.016 + swell, bz * 0.45), (bx + 0.014, bz),
           (bx - 0.032, bz + 0.004), (bx - 0.03 - swell, bz * 0.5)]
    g = prof("grip", mat, pts, w, bevel=0.004)
    return g


def trigger_guard(x0=-0.035, x1=0.032, depth=0.03, mat="steel", w=0.008):
    prof("guard", mat, [(x0, 0.0), (x1, 0.0), (x1, -depth), (x0, -depth), (x0, -depth + 0.005),
                        (x1 - 0.006, -depth + 0.005), (x1 - 0.006, -0.004), (x0, -0.004)], w, bevel=0.0008)
    prof("trigger", "steel", [(0.006, 0.0), (0.012, 0.0), (0.004, -0.022), (-0.002, -0.021)], 0.005, bevel=0.0005)


def screw(x, z, y, r=0.0035, mat="steel"):
    s = hs.cyl_y("screw", r, 0.003, (x, y, z), verts=10)
    F(s, mat, bevel=0.0004)


def slots_x(target, x0, x1, n, z, h, y=0.0, depth=0.1, w=0.004):
    """n vertical slots across X (cooling holes, serrations) cut through `target`."""
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        cutbox(target, (w, depth, h), (x, y, z))


# ---------------------------------------------------------------- Type 56
def type56():
    BZ = 0.047
    rec = prof("receiver", "steel", [(-0.075, 0.0), (0.215, 0.0), (0.215, 0.06), (-0.075, 0.06)], 0.044)
    # Milled lightening cuts above the magazine well, both sides; the ejection port on the right.
    for y in (0.0225, -0.0225):
        cutbox(rec, (0.06, 0.004, 0.022), (0.105, y, 0.028))
    cutbox(rec, (0.085, 0.012, 0.012), (0.115, -0.022, 0.054))
    # Dust cover: rounded top, the ribbed back with the release button.
    hs.finish(hs.loft_x("cover", [(-0.072, 0.076, 0.056, 0.0205), (0.18, 0.08, 0.056, 0.0205),
                                  (0.2, 0.074, 0.056, 0.019)], power=2.6), M["steel"], bevel=0.0)
    for i in range(3):
        box(f"cover_rib{i}", "steel", (0.004, 0.044, 0.01), (-0.062 + i * 0.012, 0.0, 0.075), bevel=0.0008)
    cylx("cover_button", "steel", 0.006, -0.082, -0.074, 0.066)
    # Rear sight block and leaf.
    prof("rsight_base", "steel", [(0.19, 0.06), (0.255, 0.06), (0.255, 0.07), (0.205, 0.084), (0.19, 0.084)], 0.032)
    prof("rsight_leaf", "steel", [(0.2, 0.084), (0.265, 0.074), (0.265, 0.079), (0.2, 0.089)], 0.022)
    box("rsight_slider", "steel", (0.008, 0.026, 0.008), (0.235, 0.0, 0.081), bevel=0.0008)
    # Charging handle (right side) and the bolt carrier showing through the port.
    cylx("bolt_carrier", "steel", 0.008, 0.08, 0.17, 0.052, y=-0.014, verts=10)
    F(hs.cyl_y("charge_stem", 0.0045, 0.03, (0.175, -0.032, 0.052), verts=10), "steel", bevel=0.0004)
    F(hs.cyl_y("charge_knob", 0.008, 0.012, (0.175, -0.05, 0.052), verts=12), "steel", bevel=0.0012)
    # Selector lever, the long flat plate on the right.
    prof("selector", "steel", [(-0.062, 0.048), (0.07, 0.054), (0.07, 0.06), (-0.062, 0.058)], 0.003, y=-0.0235,
         bevel=0.0006)
    box("selector_tab", "steel", (0.016, 0.006, 0.012), (-0.06, -0.026, 0.05), bevel=0.0008)
    for x in (-0.05, 0.18, 0.05):
        screw(x, 0.02, -0.0225, 0.003)
        screw(x, 0.02, 0.0225, 0.003)
    trigger_guard()
    prof("mag_release", "steel", [(0.058, 0.0), (0.066, 0.0), (0.066, -0.024), (0.06, -0.024)], 0.014, bevel=0.0006)
    pistol_grip("wood")
    # Stock: the classic drop, a steel butt plate and the sling swivel.
    prof("stock", "wood", [(-0.07, 0.056), (-0.07, 0.004), (-0.15, -0.012), (-0.345, -0.08), (-0.35, -0.078),
                           (-0.35, 0.026), (-0.335, 0.032), (-0.2, 0.046)], 0.038, bevel=0.005)
    prof("buttplate", "steel", [(-0.35, -0.078), (-0.358, -0.08), (-0.358, 0.03), (-0.35, 0.028)], 0.04,
         bevel=0.002)
    cylx("trap_door", "steel", 0.008, -0.359, -0.357, -0.01, verts=12)
    F(hs.cyl_y("swivel", 0.008, 0.004, (-0.25, 0.0, -0.045), verts=12), "steel", bevel=0.0005)
    # Lower handguard with finger grooves, held by the retainer band; the upper over the gas tube.
    lower = hs.loft_x("handguard", [(0.215, BZ + 0.012, BZ - 0.034, 0.024), (0.24, BZ + 0.014, BZ - 0.036, 0.026),
                                    (0.395, BZ + 0.014, BZ - 0.032, 0.024), (0.405, BZ + 0.012, BZ - 0.03, 0.021)],
                      power=2.8)
    F(lower, "wood", bevel=0.0)
    for x in (0.27, 0.31, 0.35):
        cutbox(lower, (0.008, 0.06, 0.008), (x, 0.0, BZ - 0.035))
    hs.finish(hs.loft_x("upper_hg", [(0.215, BZ + 0.044, BZ + 0.014, 0.018), (0.395, BZ + 0.044, BZ + 0.014, 0.017)],
                        power=2.2), M["wood"], bevel=0.0)
    cylx("band_rear", "steel", 0.027, 0.212, 0.22, BZ - 0.012, verts=16)
    cylx("band_front", "steel", 0.026, 0.4, 0.41, BZ - 0.01, verts=16)
    cylx("gas_tube", "steel", 0.012, 0.395, 0.44, BZ + 0.031, verts=12)
    # Gas block with the angled port up to the tube; the hooded front sight.
    prof("gas_block", "steel", [(0.425, BZ - 0.012), (0.46, BZ - 0.012), (0.46, BZ + 0.045), (0.435, BZ + 0.045)],
         0.026)
    cylx("barrel", "steel", 0.0105, 0.405, 0.605, BZ, verts=14)
    prof("fsb", "steel", [(0.552, BZ - 0.016), (0.598, BZ - 0.016), (0.598, BZ + 0.012), (0.588, BZ + 0.036),
                          (0.566, BZ + 0.036), (0.552, BZ + 0.012)], 0.022)
    hood = hs.cyl_x("fs_hood", 0.016, 0.566, 0.59, verts=16, z=BZ + 0.05)
    F(hood, "steel", bevel=0.0005)
    hs.cut(hood, hs.cyl_x("fs_hood_in", 0.013, 0.55, 0.61, verts=16, z=BZ + 0.05))
    cutbox(hood, (0.05, 0.04, 0.02), (0.578, 0.0, BZ + 0.035))
    box("fs_post", "steel", (0.004, 0.003, 0.02), (0.578, 0.0, BZ + 0.048), bevel=0.0)
    cylx("muzzle_nut", "steel", 0.0125, 0.605, 0.635, BZ, verts=14)
    # Folded spike bayonet: hinge under the front sight, the spike back along the barrel.
    F(hs.cyl_y("bay_hinge", 0.008, 0.02, (0.575, 0.0, BZ - 0.022), verts=12), "steel", bevel=0.0006)
    spike = hs.cyl_x("bayonet", 0.0055, -0.12, 0.12, verts=4, radius2=0.0028)
    spike.location = (0.455, 0.0, BZ - 0.024)
    spike.rotation_euler.x = math.radians(45)
    F(spike, "steel", bevel=0.0004)
    prof("bay_lock", "steel", [(0.32, BZ - 0.036), (0.345, BZ - 0.036), (0.345, BZ - 0.016), (0.32, BZ - 0.016)],
         0.014)
    cylx("cleaning_rod", "steel", 0.003, 0.405, 0.552, BZ - 0.014, y=0.012, verts=8)
    # Curved steel magazine with stamped ribs and the follower lip.
    pts_front, pts_back = [], []
    for i in range(9):
        t = i / 8
        cx = 0.07 + 0.09 * t ** 1.5
        cz = -0.235 * t
        pts_front.append((cx + 0.045 + 0.016 * t, cz))
        pts_back.append((cx, cz + 0.006 * t))
    mag = prof("mag", "black", pts_front + list(reversed(pts_back)), 0.026, bevel=0.0018)
    box("mag_base", "black", (0.06, 0.03, 0.008), (0.155 + 0.02, 0.0, -0.236), rot=(0, math.radians(-30), 0))
    if high():
        hs.text("mark", "56式", 0.012, (-0.02, 0.0222, 0.035), (math.radians(90), 0, math.radians(180)), M["steel"])
        hs.text("serial", "1 7 3 4 8 2 9", 0.005, (0.03, 0.0222, 0.006), (math.radians(90), 0, math.radians(180)),
                M["steel"])


# ---------------------------------------------------------------- pump shotgun
def pump():
    rec = prof("receiver", "steel", [(-0.07, -0.006), (0.17, -0.006), (0.17, 0.074), (-0.04, 0.074), (-0.07, 0.066)],
               0.04, bevel=0.0025)
    cutbox(rec, (0.08, 0.02, 0.026), (0.07, -0.02, 0.046))       # ejection port (right)
    cutbox(rec, (0.085, 0.024, 0.02), (0.075, 0.0, -0.006))      # loading port
    box("bolt", "steel", (0.07, 0.006, 0.022), (0.07, -0.014, 0.046), bevel=0.0006)
    box("rib_top", "steel", (0.2, 0.01, 0.004), (0.06, 0.0, 0.076), bevel=0.0006)
    for x in (-0.03, 0.12):
        screw(x, 0.012, 0.0205, 0.004)
        screw(x, 0.012, -0.0205, 0.004)
    F(hs.cyl_y("safety", 0.004, 0.044, (-0.038, 0.0, 0.004), verts=10), "steel", bevel=0.0004)
    trigger_guard(mat="poly", w=0.01)
    prof("slide_release", "steel", [(0.035, -0.006), (0.05, -0.006), (0.05, -0.016), (0.04, -0.018)], 0.006, y=0.016)
    pistol_grip("poly")
    st = prof("stock", "poly", [(-0.07, 0.066), (-0.07, 0.002), (-0.15, -0.012), (-0.325, -0.06), (-0.34, -0.058),
                                (-0.34, 0.054), (-0.24, 0.066)], 0.04, bevel=0.005)
    cutbox(st, (0.12, 0.05, 0.012), (-0.22, 0.0, 0.02), rot=(0, math.radians(-12), 0))
    prof("recoil_pad", "rubber", [(-0.34, -0.06), (-0.362, -0.062), (-0.362, 0.058), (-0.34, 0.056)], 0.042,
         bevel=0.004)
    for z in (-0.04, -0.015, 0.01, 0.035):
        box("pad_rib", "rubber", (0.003, 0.043, 0.004), (-0.363, 0.0, z), bevel=0.0)
    cylx("barrel", "steel", 0.0125, 0.17, 0.66, 0.052, verts=16)
    cylx("barrel_ring", "steel", 0.0145, 0.555, 0.575, 0.04, verts=14)
    box("ring_web", "steel", (0.02, 0.012, 0.024), (0.565, 0.0, 0.034), bevel=0.0006)
    cylx("tube", "steel", 0.0125, 0.17, 0.56, 0.02, verts=14)
    cylx("cap", "steel", 0.0145, 0.56, 0.6, 0.02, verts=14)
    cylx("cap_nub", "steel", 0.008, 0.6, 0.608, 0.02, verts=10)
    for y in (0.0105, -0.0105):
        box("action_bar", "steel", (0.12, 0.003, 0.005), (0.2, y, 0.024), bevel=0.0)
    fe = hs.cyl_x("forend", 0.027, 0.2, 0.37, verts=20, z=0.026)
    fe.scale = (1.0, 1.0, 1.0)
    F(fe, "poly", bevel=0.002)
    for i in range(7):
        x = 0.215 + i * 0.022
        cylx(f"rib{i}", "poly", 0.0295, x, x + 0.008, 0.026, verts=20, bevel=0.0012)
    F(hs.cyl_z("bead", 0.0028, 0.007, (0.652, 0, 0.067), verts=8), "brass", bevel=0.0)
    if high():
        hs.text("mark", "NORINCO  982  12GA", 0.0065, (-0.03, 0.0202, 0.03), (math.radians(90), 0, math.radians(180)),
                M["steel"])


# ---------------------------------------------------------------- Type 85 SMG
def smg():
    BZ = 0.045
    rec = cylx("receiver", "black", 0.026, -0.05, 0.215, BZ, verts=20, bevel=0.0012)
    cutbox(rec, (0.06, 0.02, 0.012), (0.1, -0.024, BZ + 0.012))
    cylx("end_cap", "black", 0.0275, -0.058, -0.048, BZ, verts=20)
    for x in (-0.03, 0.18):
        cylx("band", "black", 0.0272, x, x + 0.006, BZ, verts=20)
    F(hs.cyl_y("cocking", 0.005, 0.03, (0.13, -0.035, BZ + 0.012), verts=10), "steel", bevel=0.0004)
    prof("lower", "black", [(-0.05, -0.004), (0.12, -0.004), (0.12, 0.03), (-0.05, 0.03)], 0.034, bevel=0.002)
    trigger_guard(-0.03, 0.03, 0.028, mat="black")
    pistol_grip("bakelite", bottom=(-0.038, -0.1))
    # Perforated barrel jacket.
    jacket = cylx("jacket", "black", 0.019, 0.215, 0.335, BZ, verts=18, bevel=0.0008)
    for i in range(5):
        x = 0.228 + i * 0.022
        hs.cut(jacket, hs.cyl_y("hole", 0.0055, 0.08, (x, 0.0, BZ), verts=10))
        hs.cut(jacket, hs.cyl_z("hole_v", 0.0055, 0.08, (x + 0.011, 0.0, BZ), verts=10))
    cylx("barrel", "steel", 0.0095, 0.2, 0.345, BZ, verts=12)
    cylx("muzzle", "black", 0.012, 0.335, 0.355, BZ, verts=14)
    prof("fsight", "black", [(0.315, BZ + 0.016), (0.335, BZ + 0.016), (0.332, BZ + 0.034), (0.322, BZ + 0.034)],
         0.008)
    prof("rsight", "black", [(-0.02, BZ + 0.022), (0.015, BZ + 0.022), (0.012, BZ + 0.042), (-0.016, BZ + 0.042)],
         0.022)
    prof("mag", "black", [(0.082, -0.004), (0.122, -0.004), (0.142, -0.2), (0.106, -0.2)], 0.024, bevel=0.0015)
    box("mag_base", "black", (0.044, 0.028, 0.008), (0.124, 0.0, -0.202), rot=(0, math.radians(-6), 0))
    # Folding wire stock, folded out: two rods and a butt bar.
    for y in (0.016, -0.016):
        F(hs.cyl_between("stock_rod", (-0.05, y, 0.03), (-0.3, y, -0.012), 0.0042, verts=8), "steel", bevel=0.0)
        F(hs.cyl_between("stock_rod2", (-0.05, y, 0.058), (-0.3, y, 0.05), 0.0042, verts=8), "steel", bevel=0.0)
    box("butt", "steel", (0.008, 0.04, 0.075), (-0.304, 0.0, 0.019), bevel=0.0015)
    box("hinge", "steel", (0.016, 0.044, 0.018), (-0.055, 0.0, 0.045), bevel=0.001)


# ---------------------------------------------------------------- Type 79 marksman rifle
def type79():
    BZ = 0.047
    rec = prof("receiver", "steel", [(-0.07, 0.0), (0.21, 0.0), (0.21, 0.06), (-0.07, 0.06)], 0.042)
    cutbox(rec, (0.08, 0.012, 0.012), (0.11, -0.021, 0.054))
    hs.finish(hs.loft_x("cover", [(-0.066, 0.074, 0.056, 0.0195), (0.19, 0.078, 0.056, 0.0195)], power=2.6),
              M["steel"], bevel=0.0)
    F(hs.cyl_y("charge", 0.007, 0.034, (0.17, -0.036, 0.052), verts=12), "steel", bevel=0.0008)
    prof("selector", "steel", [(-0.058, 0.048), (0.06, 0.053), (0.06, 0.058), (-0.058, 0.057)], 0.003, y=-0.0225)
    trigger_guard()
    # Skeleton thumbhole stock: the grip and the butt in one piece, the cheek rest on top.
    st = prof("stock", "wood", [(0.0, 0.0), (-0.07, 0.006), (-0.07, 0.058), (-0.2, 0.052), (-0.52, 0.042),
                                (-0.54, 0.04), (-0.545, -0.11), (-0.52, -0.112), (-0.33, -0.07), (-0.2, -0.05),
                                (-0.08, -0.115), (-0.04, -0.108), (0.016, 0.0)], 0.036, bevel=0.005)
    hs.cut(st, hs.side_profile("thumbhole", [(-0.075, -0.012), (-0.18, -0.006), (-0.2, -0.03), (-0.1, -0.075)], 0.1))
    hs.cut(st, hs.side_profile("butt_hole", [(-0.25, 0.02), (-0.49, 0.012), (-0.49, -0.07), (-0.34, -0.05),
                                             (-0.25, -0.03)], 0.1))
    prof("cheek", "wood", [(-0.2, 0.046), (-0.43, 0.036), (-0.43, 0.062), (-0.27, 0.068)], 0.03, y=0.006, bevel=0.006)
    prof("buttplate", "rubber", [(-0.545, -0.11), (-0.56, -0.112), (-0.56, 0.042), (-0.545, 0.04)], 0.038)
    # Vented handguard (two halves), the gas block, the long barrel.
    hg = hs.loft_x("handguard", [(0.21, BZ + 0.03, BZ - 0.03, 0.025), (0.45, BZ + 0.028, BZ - 0.028, 0.023)],
                   power=2.4)
    F(hg, "wood", bevel=0.0)
    for i in range(6):
        cutbox(hg, (0.022, 0.06, 0.006), (0.24 + i * 0.034, 0.0, BZ + 0.004))
    cylx("hg_cap", "steel", 0.026, 0.45, 0.46, BZ, verts=16)
    cylx("gas_block", "steel", 0.016, 0.46, 0.5, BZ + 0.004, verts=14)
    cylx("barrel", "steel", 0.0105, 0.46, 0.79, BZ, verts=14)
    prof("fsb", "steel", [(0.762, BZ - 0.012), (0.79, BZ - 0.012), (0.79, BZ + 0.03), (0.77, BZ + 0.03)], 0.016)
    box("bay_lug", "steel", (0.03, 0.01, 0.012), (0.775, 0.0, BZ - 0.018))
    fh = cylx("flash_hider", "steel", 0.0125, 0.79, 0.865, BZ, verts=16)
    for k in range(5):
        a = k * 2 * math.pi / 5
        cutbox(fh, (0.05, 0.0035, 0.03), (0.84, math.sin(a) * 0.012, BZ + math.cos(a) * 0.012),
               rot=(a, 0, 0))
    # Ten-round magazine.
    prof("mag", "black", [(0.07, 0.0), (0.12, 0.0), (0.138, -0.11), (0.084, -0.112)], 0.024, bevel=0.0016)
    for z in (-0.04, -0.075):
        box("mag_rib", "black", (0.04, 0.026, 0.004), (0.104, 0.0, z), rot=(0, math.radians(-9), 0), bevel=0.0004)
    # Side rail on the left and the 4x scope (PSO pattern) offset over it.
    box("side_rail", "steel", (0.14, 0.006, 0.026), (0.07, 0.024, 0.036), bevel=0.0008)
    prof("mount", "steel", [(0.02, 0.03), (0.16, 0.03), (0.15, 0.09), (0.03, 0.09)], 0.012, y=0.03, bevel=0.0015)
    box("mount_lever", "steel", (0.008, 0.006, 0.04), (0.13, 0.04, 0.05), bevel=0.0008)
    SZ, SY = 0.104, 0.012
    cylx("scope_tube", "black", 0.0135, -0.02, 0.2, SZ, y=SY, verts=20)
    cylx("ocular", "black", 0.019, -0.085, -0.03, SZ, y=SY, verts=20, r2=0.0145)
    cylx("eyecup", "rubber", 0.0215, -0.115, -0.085, SZ, y=SY, verts=20)
    cylx("objective", "black", 0.0165, 0.19, 0.215, SZ, y=SY, verts=20, r2=0.0215)
    cylx("sunshade", "black", 0.0225, 0.215, 0.26, SZ, y=SY, verts=20)
    shade = hs.cyl_x("sunshade_in", 0.019, 0.22, 0.27, verts=20, z=SZ, y=SY)
    hs.cut(PARTS_LAST(), shade)
    cylx("lens", "lens", 0.0195, 0.243, 0.246, SZ, y=SY, verts=20, bevel=0.0)
    cylx("lens_rear", "lens", 0.015, -0.112, -0.11, SZ, y=SY, verts=16, bevel=0.0)
    turret = hs.cyl_z("turret", 0.012, 0.024, (0.085, SY, SZ + 0.018), verts=16)
    F(turret, "black", bevel=0.001)
    F(hs.cyl_y("turret_side", 0.011, 0.022, (0.085, SY + 0.018, SZ), verts=16), "black", bevel=0.001)
    box("battery", "black", (0.02, 0.016, 0.016), (0.02, SY + 0.018, SZ - 0.006), bevel=0.001)


def PARTS_LAST():
    return hs.PARTS[-1]


# ---------------------------------------------------------------- Type 80 GPMG
def type80():
    BZ = 0.058
    rec = prof("receiver", "steel", [(-0.095, -0.004), (0.22, -0.004), (0.22, 0.074), (-0.095, 0.074)], 0.046)
    for y in (0.0235, -0.0235):
        cutbox(rec, (0.13, 0.004, 0.03), (0.07, y, 0.03))
    # Top cover with the feed tray hinge, the rear sight leaf, the cover latch.
    top = hs.loft_x("cover", [(-0.09, 0.088, 0.072, 0.024), (0.2, 0.094, 0.072, 0.024)], power=3.0)
    F(top, "steel", bevel=0.0)
    for i in range(4):
        box(f"cover_rib{i}", "steel", (0.03, 0.05, 0.003), (-0.04 + i * 0.06, 0.0, 0.094), bevel=0.0005)
    F(hs.cyl_y("cover_hinge", 0.006, 0.05, (0.2, 0.0, 0.086), verts=12), "steel", bevel=0.0006)
    prof("rsight", "steel", [(0.16, 0.094), (0.21, 0.094), (0.21, 0.104), (0.17, 0.114)], 0.028)
    box("latch", "steel", (0.018, 0.03, 0.012), (-0.088, 0.0, 0.094), bevel=0.001)
    # Feed tray opening on the right with the belt going in.
    box("feed_tray", "steel", (0.05, 0.02, 0.022), (0.04, -0.033, 0.06), bevel=0.001)
    trigger_guard(-0.04, 0.035, 0.034)
    pistol_grip("wood", bottom=(-0.046, -0.112))
    # Skeleton stock with the butt plate and the shoulder strap loop.
    st = prof("stock", "wood", [(-0.095, 0.072), (-0.095, 0.004), (-0.18, -0.012), (-0.41, -0.07), (-0.43, -0.07),
                                (-0.43, 0.056), (-0.3, 0.07), (-0.18, 0.072)], 0.036, bevel=0.005)
    hs.cut(st, hs.side_profile("stock_hole", [(-0.18, 0.05), (-0.39, 0.042), (-0.39, -0.044), (-0.2, 0.008)], 0.1))
    prof("butt", "steel", [(-0.43, -0.07), (-0.44, -0.072), (-0.44, 0.058), (-0.43, 0.056)], 0.04, bevel=0.002)
    # Fluted barrel, gas tube under it, gas regulator; the carry handle; folded bipod; front sight; flash hider.
    bar = cylx("barrel", "steel", 0.0125, 0.22, 0.72, BZ, verts=16)
    for k in range(6):
        a = k * math.pi / 3
        cutbox(bar, (0.3, 0.004, 0.004), (0.42, math.sin(a) * 0.0128, BZ + math.cos(a) * 0.0128), rot=(a, 0, 0))
    cylx("trunnion", "steel", 0.02, 0.22, 0.26, BZ, verts=16)
    cylx("gas_tube", "steel", 0.0105, 0.22, 0.51, BZ - 0.03, verts=14)
    prof("gas_block", "steel", [(0.5, BZ - 0.045), (0.535, BZ - 0.045), (0.535, BZ + 0.014), (0.5, BZ + 0.014)], 0.026)
    F(hs.cyl_y("regulator", 0.009, 0.032, (0.52, 0.0, BZ - 0.03), verts=12), "steel", bevel=0.0006)
    # Carry handle: a steel arm up from the barrel collar to a wooden grip along the gun.
    cylx("handle_collar", "steel", 0.016, 0.31, 0.34, BZ, verts=14)
    prof("handle_arm", "steel", [(0.315, BZ + 0.012), (0.335, BZ + 0.012), (0.3, BZ + 0.07), (0.28, BZ + 0.07)],
         0.01)
    cylx("handle_grip", "wood", 0.011, 0.2, 0.31, BZ + 0.075, verts=12, bevel=0.003)
    # Bipod, folded back under the barrel.
    F(hs.cyl_y("bipod_hinge", 0.007, 0.03, (0.56, 0.0, BZ - 0.02), verts=12), "steel", bevel=0.0006)
    for y in (0.011, -0.011):
        F(hs.cyl_between("bipod_leg", (0.56, y, BZ - 0.026), (0.33, y, BZ - 0.036), 0.0052, verts=8),
          M["steel"], bevel=0.0)
        box("bipod_foot", "steel", (0.016, 0.01, 0.02), (0.327, y, BZ - 0.04), bevel=0.001)
    prof("fsb", "steel", [(0.68, BZ - 0.012), (0.705, BZ - 0.012), (0.705, BZ + 0.04), (0.69, BZ + 0.04)], 0.016)
    fh = cylx("flash_hider", "steel", 0.0135, 0.72, 0.79, BZ, verts=16)
    for k in range(5):
        a = k * 2 * math.pi / 5
        cutbox(fh, (0.045, 0.0035, 0.03), (0.765, math.sin(a) * 0.013, BZ + math.cos(a) * 0.013), rot=(a, 0, 0))
    # 100-round box on the right, under the feed, with the belt running up into the gun.
    box_ = box("ammo_box", "olive", (0.1, 0.065, 0.13), (0.07, -0.04, -0.07), bevel=0.003)
    box("box_lid", "olive", (0.104, 0.068, 0.012), (0.07, -0.04, -0.003), bevel=0.002)
    box("box_latch", "steel", (0.02, 0.004, 0.024), (0.07, -0.074, -0.03), bevel=0.0006)
    F(hs.cyl_x("box_handle", 0.0035, 0.04, 0.1, verts=8, z=0.012, y=-0.04), "steel", bevel=0.0)
    if high():
        hs.text("box_mark", "7.62 × 100", 0.009, (0.04, -0.0729, -0.06), (math.radians(90), 0, 0), M["yellow"])
    # The belt: brass cartridges in steel links, a short loop from the box to the feed.
    path = [(0.05, -0.045, 0.003), (0.045, -0.06, 0.03), (0.042, -0.05, 0.055)]
    for i in range(7):
        t = i / 6
        a = V(path[0]).lerp(V(path[1]), min(t * 2, 1.0)) if t < 0.5 else V(path[1]).lerp(V(path[2]), (t - 0.5) * 2)
        c = hs.cyl_x("round", 0.0055, a.x - 0.003, a.x + 0.047, verts=8, z=a.z, y=a.y + 0.0)
        F(c, "brass", bevel=0.0)
        F(hs.cyl_x("link", 0.0068, a.x + 0.006, a.x + 0.016, verts=8, z=a.z, y=a.y), "black", bevel=0.0)


# ---------------------------------------------------------------- QBZ-95 bullpup
def qbz95():
    BZ = 0.058
    # The shell: one rounded loft from the butt to the muzzle end of the handguard.
    shell = hs.loft_x("shell", [(-0.385, 0.06, -0.075, 0.022), (-0.36, 0.068, -0.082, 0.026),
                                (-0.1, 0.07, -0.016, 0.027), (0.0, 0.07, 0.006, 0.026),
                                (0.2, 0.072, 0.012, 0.025), (0.265, 0.07, 0.022, 0.023), (0.275, 0.065, 0.03, 0.02)],
                      power=3.0)
    F(shell, "poly", bevel=0.0)
    cutbox(shell, (0.06, 0.02, 0.016), (-0.2, -0.026, 0.045))     # ejection port (right)
    box("bolt", "steel", (0.05, 0.004, 0.012), (-0.2, -0.019, 0.045), bevel=0.0005)
    prof("butt_pad", "rubber", [(-0.385, -0.075), (-0.398, -0.077), (-0.398, 0.062), (-0.385, 0.06)], 0.044)
    # Carry handle with the aperture sight at the back.
    prof("handle", "poly", [(-0.09, 0.07), (0.17, 0.07), (0.17, 0.084), (0.14, 0.112), (-0.06, 0.112),
                            (-0.09, 0.094)], 0.022, bevel=0.003)
    hh = hs.side_profile("handle_hole", [(-0.03, 0.068), (0.12, 0.068), (0.11, 0.095), (-0.02, 0.095)], 0.05)
    hs.cut(PARTS_LAST(), hh)
    F(hs.cyl_y("rear_aperture", 0.008, 0.024, (-0.075, 0.0, 0.118), verts=12), "poly", bevel=0.0008)
    prof("front_post", "poly", [(0.15, 0.112), (0.17, 0.112), (0.168, 0.128), (0.155, 0.128)], 0.012)
    # The grip and the enclosed trigger guard forward of the magazine.
    pistol_grip("poly", bottom=(-0.03, -0.11))
    prof("guard", "poly", [(-0.04, 0.0), (0.1, 0.012), (0.1, -0.02), (0.02, -0.04), (-0.02, -0.04)], 0.026)
    hs.cut(PARTS_LAST(), hs.side_profile("guard_hole", [(-0.01, -0.004), (0.07, 0.004), (0.06, -0.014),
                                                        (0.0, -0.03)], 0.05))
    prof("trigger", "steel", [(0.006, 0.0), (0.012, 0.0), (0.004, -0.02), (-0.002, -0.02)], 0.005)
    # Magazine behind the grip; the armour-piercing band in yellow.
    pts_f, pts_b = [], []
    for i in range(7):
        t = i / 6
        cx = -0.17 + 0.05 * t ** 1.5
        cz = -0.02 - 0.19 * t
        pts_f.append((cx + 0.05 + 0.012 * t, cz))
        pts_b.append((cx, cz + 0.004 * t))
    prof("mag", "black", pts_f + list(reversed(pts_b)), 0.025, bevel=0.0016)
    box("ap_band", "yellow", (0.064, 0.0262, 0.012), (-0.135, 0.0, -0.06), rot=(0, math.radians(-12), 0),
        bevel=0.0004)
    # Barrel, gas block, flash hider; the bayonet lug.
    cylx("barrel", "steel", 0.0095, 0.27, 0.42, BZ - 0.004, verts=14)
    cylx("gas", "steel", 0.0065, 0.26, 0.33, BZ + 0.012, verts=10)
    fh = cylx("flash_hider", "steel", 0.0125, 0.39, 0.445, BZ - 0.004, verts=16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        cutbox(fh, (0.03, 0.0032, 0.03), (0.425, math.sin(a) * 0.012, BZ - 0.004 + math.cos(a) * 0.012),
               rot=(a, 0, 0))
    box("lug", "steel", (0.02, 0.008, 0.012), (0.36, 0.0, BZ - 0.02), bevel=0.0006)
    F(hs.cyl_y("selector", 0.008, 0.052, (-0.3, 0.0, -0.02), verts=12), "poly", bevel=0.0008)
    if high():
        hs.text("mark", "QBZ-95  5.8mm", 0.007, (-0.3, 0.0275, 0.02), (math.radians(90), 0, math.radians(180)),
                M["white"])


# ---------------------------------------------------------------- Type 54 pistol
def type54():
    BZ = 0.026
    sl = prof("slide", "steel", [(-0.042, 0.004), (0.155, 0.004), (0.155, 0.04), (-0.036, 0.04), (-0.042, 0.034)],
              0.025, bevel=0.0018)
    for i in range(9):
        cutbox(sl, (0.0022, 0.04, 0.022), (-0.03 + i * 0.0045, 0.0, 0.026))
    for i in range(6):
        cutbox(sl, (0.002, 0.04, 0.014), (0.11 + i * 0.006, 0.0, 0.03))
    cutbox(sl, (0.03, 0.012, 0.01), (0.02, -0.013, 0.034))       # ejection port
    hs.cut(sl, hs.cyl_x("bore", 0.0045, 0.14, 0.17, verts=12, z=BZ))
    prof("rsight", "steel", [(-0.03, 0.04), (-0.016, 0.04), (-0.016, 0.046), (-0.03, 0.046)], 0.012)
    prof("fsight", "steel", [(0.14, 0.04), (0.15, 0.04), (0.149, 0.046), (0.142, 0.046)], 0.004)
    prof("frame", "steel", [(-0.04, -0.004), (0.152, -0.004), (0.152, 0.006), (-0.04, 0.006)], 0.023)
    prof("dust", "steel", [(0.06, -0.004), (0.152, -0.004), (0.152, -0.016), (0.07, -0.016)], 0.022)
    box("barrel_bush", "steel", (0.006, 0.02, 0.014), (0.153, 0.0, 0.018), bevel=0.0005)
    prof("hammer", "steel", [(-0.046, 0.022), (-0.04, 0.022), (-0.048, 0.044), (-0.056, 0.042)], 0.008)
    trigger_guard(-0.022, 0.04, 0.026, w=0.007)
    prof("grip_frame", "steel", [(-0.042, 0.0), (0.012, 0.0), (-0.008, -0.11), (-0.048, -0.11), (-0.052, -0.06)],
         0.022, bevel=0.0018)
    for y in (0.0122, -0.0122):
        g = prof("grip_panel", "bakelite", [(-0.04, -0.012), (0.004, -0.012), (-0.01, -0.1), (-0.044, -0.1),
                                            (-0.046, -0.06)], 0.004, y=y, bevel=0.0012)
        if high():
            F(hs.cyl_y("star_ring", 0.009, 0.0016, (-0.021, y * 1.18, -0.04), verts=20), "bakelite", bevel=0.0)
            hs.text("star", "★", 0.012, (-0.027, y * 1.22, -0.046), (math.radians(90), 0, 0 if y > 0 else math.radians(180)),
                    M["bakelite"])
    box("mag_base", "steel", (0.042, 0.022, 0.006), (-0.026, 0.0, -0.113), bevel=0.001)
    box("lanyard", "steel", (0.006, 0.01, 0.01), (-0.046, 0.0, -0.11), bevel=0.0006)
    F(hs.cyl_y("slide_stop", 0.004, 0.026, (0.05, 0.0, 0.0), verts=10), "steel", bevel=0.0004)
    if high():
        hs.text("mark", "54式", 0.007, (0.06, 0.0127, 0.012), (math.radians(90), 0, math.radians(180)), M["steel"])


GUNS = {"type56": type56, "pump": pump, "smg": smg, "type79": type79, "type80": type80, "qbz95": qbz95,
        "type54": type54}
TEX = {"type54": 512, "smg": 1024}


def build(name, fn, detail):
    hs.set_detail(detail)
    fn()
    ob = hs.join_parts(f"{name}_{detail['name']}")
    return ob


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)


names = [n for n in GUNS if not args.only or n in args.only.split(",")]
done = {}
for name in names:
    if args.fast:
        hi = build(name, GUNS[name], hs.HIGH)
        done[name] = hi
        print(f"{name}: HIGH {tris(hi)} tris")
        continue
    hi = build(name, GUNS[name], hs.HIGH)
    lo = build(name, GUNS[name], hs.LOW)
    lo.name = name
    print(f"{name}: HIGH {tris(hi)} / LOW {tris(lo)} tris", flush=True)
    if args.out:
        size = min(args.tex, TEX.get(name, args.tex))
        bakeutil.unwrap(lo, boost={M["steel"].name: 1.3})
        tex = bakeutil.bake_textures(hi, lo, MATERIALS, size, os.path.join(args.out, "textures"), f"eg_{name}",
                                     cage=0.001, ray=0.003, ao_distance=0.025, grime=0.5)
        bakeutil.apply_baked_material(lo, tex, f"eg_{name}", emission_strength=1.0)
        bakeutil.export_gltf(lo, os.path.join(args.out, f"{name}.gltf"))
        print(f"{name}: exported", flush=True)
    bpy.data.objects.remove(hi)
    done[name] = lo


if args.preview:
    scene = bpy.context.scene
    obs = list(done.values())
    y = 0.0
    for ob in obs:
        ob.location = (0, 0, -y)
        y += 0.32 if "type54" not in ob.name else 0.22
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1800
    world = bpy.data.worlds.new("w")
    world.color = (0.32, 0.33, 0.35)
    scene.world = world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (0.15, -3.0, -y / 2 + 0.14)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(1.2, y + 0.25)
    scene.camera = cam
    for rot, e in (((50, -20, 30), 3.5), ((70, 30, -140), 1.5)):
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = e
        sun.rotation_euler = tuple(math.radians(a) for a in rot)
        scene.collection.objects.link(sun)
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("preview:", args.preview)
