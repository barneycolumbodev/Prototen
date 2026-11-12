"""MP5-pattern 9 mm submachine gun with a red-dot sight, a suppressor and an
under-barrel green laser.

Owner brief (2026-11-12): "a very detailed mp5, with a red dot sight,
suppressor, under barrel green laser ... high mobility run and gun, contained
hipfire, which is accurate to the green laser".

Built: MP5A3 / Navy pattern. Stamped steel receiver with the rounded top,
bolt-guide grooves, ejection port (the bolt shows through it), magazine well
with the paddle and button releases. Cocking tube over the barrel with the
slotted left side, hold-open notch and the cocking handle. Drum rear sight,
hooded front post. Polymer trigger housing with ambidextrous selector and
bullet pictograms. Retractable stock (forks along the receiver, collapsed).
Curved 30-round steel magazine, top round visible when it drops. Wide polymer
handguard with a Picatinny strip underneath carrying the vertical foregrip
(the MG42's, same place: the arms builder's support hand fits) and, ahead of
it, the LA-9G green laser module with its pressure pad and cable. Picatinny
rail on the receiver top carrying an enclosed-emitter red-dot sight. Quick-
detach suppressor on the three-lug barrel.

Moving parts (separate nodes in the glTF, see src/player/viewmodel_rig.gd):
  body             everything that doesn't move
  slide            bolt and carrier, seen through the ejection port
  charging_handle  cocking handle (travels back along the tube and up into the notch)
  magazine         drops on reload
  stock            forks and butt plate
  lens             red-dot glass (the game gives it a transparent material)
  reticle          the dot (the game colours it)
  laser            the laser's emitter window (emissive; the game draws the beam from it)

The pistol grip is the Pistol 57 / MG42 grip profile at the same place and the
foregrip is the MG42's moved 8 mm down, so existing hand poses carry over.

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/mp5/build.py --out assets/weapons/mp5/mp5.gltf --tex 4096 \
      --preview docs/previews/mp5.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/mp5.png [--only side,fp]
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--emission-size", type=int, default=1024)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
PI = math.pi

# ---------------------------------------------------------------- materials
# HK black baked enamel over phosphated steel: satin, edges worn to steel.
M_STEEL = mat("black_enamel", (0.022, 0.023, 0.025), 0.40, 0.7, wear=(0.46, 0.46, 0.48), wear_rough=0.22,
              brushed=0.02, bump_scale=1500, bump_strength=0.035)
M_OXIDE = mat("black_oxide", (0.016, 0.017, 0.019), 0.5, 0.75, wear=(0.36, 0.36, 0.38), wear_rough=0.25,
              brushed=0.02, bump_scale=900, bump_strength=0.05)
M_BOLT = mat("bolt_steel", (0.2, 0.2, 0.205), 0.3, 1.0, wear=(0.6, 0.6, 0.62), wear_rough=0.18, brushed=0.05)
M_POLY = mat("black_polymer", (0.02, 0.02, 0.022), 0.6, 0.0, wear=(0.1, 0.1, 0.11), wear_rough=0.45,
             bump_scale=1600, bump_strength=0.14)
M_STIPPLE = mat("stippled_polymer", (0.018, 0.018, 0.02), 0.72, 0.0, bump_scale=2600, bump_strength=0.75)
M_ALU = mat("black_anodised", (0.02, 0.021, 0.024), 0.38, 0.8, wear=(0.62, 0.62, 0.64), wear_rough=0.3,
            bump_scale=2200, bump_strength=0.03)
M_CAN = mat("suppressor_coat", (0.04, 0.041, 0.043), 0.56, 0.45, wear=(0.42, 0.41, 0.4), wear_rough=0.3,
            brushed=0.035, bump_scale=1900, bump_strength=0.08)
M_RUBBER = mat("rubber", (0.018, 0.018, 0.019), 0.85, 0.0, bump_scale=600, bump_strength=0.3)
M_BORE = mat("bore_dark", (0.01, 0.01, 0.012), 0.5, 1.0)
M_BRASS = mat("brass", (0.8, 0.6, 0.3), 0.24, 1.0, wear=(0.95, 0.8, 0.5), wear_rough=0.14)
M_COPPER = mat("bullet_jacket", (0.72, 0.38, 0.22), 0.28, 1.0)
M_LENS = mat("lens_coated", (0.02, 0.012, 0.014), 0.04, 0.0, emission=((0.5, 0.12, 0.1), 0.25))
M_GREEN = mat("laser_window", (0.1, 0.9, 0.25), 0.1, 0.0, emission=((0.1, 1.0, 0.22), 8.0))
M_RED = mat("reticle_lamp", (0.9, 0.08, 0.04), 0.3, 0.0, emission=((1.0, 0.1, 0.04), 8.0))
M_MARK = mat("engraving", (0.5, 0.5, 0.5), 0.5, 0.6)
M_PAINT = mat("index_paint", (0.86, 0.84, 0.78), 0.6, 0.0)
M_REDPAINT = mat("red_paint", (0.62, 0.03, 0.02), 0.55, 0.0)
M_YELLOW = mat("warning_label", (0.85, 0.62, 0.04), 0.55, 0.0)
MATERIALS = [M_STEEL, M_OXIDE, M_BOLT, M_POLY, M_STIPPLE, M_ALU, M_CAN, M_RUBBER, M_BORE, M_BRASS, M_COPPER,
             M_LENS, M_GREEN, M_RED, M_MARK, M_PAINT, M_REDPAINT, M_YELLOW]

# ---------------------------------------------------------------- dimensions
REC_X0, REC_X1 = -0.165, 0.099      # stamped receiver
REC_HW = 0.0185                      # receiver half width
REC_ZB = -0.012                      # bottom edge of the receiver (the trigger housing hangs below it)
ARC_Z = 0.0245                       # centre of the receiver's rounded top
TOP_Z = ARC_Z + REC_HW               # 0.043
CT_Z, CT_R = 0.027, 0.0105           # cocking tube axis and radius
SLOT_A = math.radians(32)            # cocking slot: this far above horizontal on the left side
SIGHT_Z = 0.057                      # iron sight line
RAIL_Z = 0.0535                      # top of the receiver's Picatinny rail
DOT_Z = 0.0780                       # red-dot window centre
DOT_X0, DOT_X1 = -0.048, 0.008       # red-dot body
MAG_X0, MAG_X1 = 0.057, 0.089        # magazine (front to back, at the top)
MAG_TOP = -0.008
MAG_R = 0.45                         # curve radius
MAG_LEN = 0.200
MAG_HW = 0.0112
WELL_X0, WELL_X1 = 0.051, 0.097      # magazine well
PORT_X0, PORT_X1, PORT_Z0, PORT_Z1 = 0.040, 0.092, -0.007, 0.014
HG_X0, HG_X1 = 0.100, 0.258          # handguard
URAIL_Z = -0.0362                    # bottom face of the under-barrel rail
FS_X0, FS_X1 = 0.260, 0.283          # front sight tower
SUP_X0, SUP_X1, SUP_R = 0.285, 0.478, 0.0185
LASER_Z = -0.0505                    # laser emitter axis
LASER_X0, LASER_X1 = 0.222, 0.268
FG_DZ = -0.008                       # MG42 foregrip, moved down this much
HOUSING_HW = 0.0192                  # trigger housing half width
PART_IDS = {"body": 0, "slide": 1, "charging_handle": 2, "magazine": 3, "stock": 4, "lens": 5, "reticle": 6,
            "laser": 7}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def hi():
    """True while building HIGH: fine detail under ~1 mm proud that LOW gets through the bake."""
    return hs.D["text"]


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m=M_MARK, extrude=0.00012):
    ob = hs.text(name, body, size, loc, rot, m, extrude=extrude)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def arc(cy, cz, r, a0, a1, n):
    """Points (y, z) on a circle from angle a0 to a1 (degrees, 0 = +Y, 90 = +Z)."""
    return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def rec_section(grow=0.0, zb=REC_ZB):
    """The receiver's cross-section: flat bottom, straight sides, half-round top."""
    n = 28 if hi() else 16
    hw = REC_HW + grow
    return [(-hw, zb), (hw, zb)] + arc(0.0, ARC_Z, hw, 0, 180, n)


def pic_profile(z_face, z_base):
    """Picatinny cross-section (y, z). z_face = the outer face, z_base = where it meets the gun."""
    s = 1.0 if z_face > z_base else -1.0
    return [(-0.0078, z_base), (0.0078, z_base), (0.0078, z_face - s * 0.0056), (0.0106, z_face - s * 0.0028),
            (0.0078, z_face), (-0.0078, z_face), (-0.0106, z_face - s * 0.0028), (-0.0078, z_face - s * 0.0056)]


def pic_rail(name, x0, x1, z_face, z_base, m, first_slot, slots):
    rail = hs.section(name, pic_profile(z_face, z_base), x0, x1)
    for i in range(slots):
        hs.cut(rail, hs.box(f"{name}_slot{i}", (0.00523, 0.03, 0.006), (first_slot + i * 0.010, 0, z_face)))
    return finish(rail, m, bevel=0.0004)


def side_pad(name, side, x0, x1, z0, z1, proud, m, hw=REC_HW, bevel=0.0005):
    """A raised pad on the left (+1) or right (-1) side wall."""
    return finish(hs.box(name, (x1 - x0, proud + 0.001, z1 - z0),
                         ((x0 + x1) / 2, side * (hw + (proud - 0.001) / 2), (z0 + z1) / 2)), m, bevel=bevel)


def screw(name, loc, axis, r, m=M_OXIDE, proud=0.0008, slot="hex"):
    """A screw head with a dark socket. axis: 'y+' / 'y-' / 'z+' / 'z-' / 'x+' = the way the head faces."""
    x, y, z = loc
    sgn = 1.0 if axis[1] == "+" else -1.0
    if axis[0] == "y":
        finish(hs.cyl_y(name, r, proud, (x, y + sgn * proud / 2, z), verts=20), m, bevel=0.0003, segments=2)
        if hi():
            n = 6 if slot == "hex" else 20
            bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r * 0.55, depth=0.0003,
                                                location=(x, y + sgn * (proud + 0.00005), z),
                                                rotation=(PI / 2, 0, 0))
            s = bpy.context.active_object
            s.name = name + "_socket"
            finish(s, M_BORE, bevel=0, smooth=False)
    elif axis[0] == "z":
        finish(hs.cyl_z(name, r, proud, (x, y, z + sgn * proud / 2), verts=20), m, bevel=0.0003, segments=2)
        if hi():
            bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r * 0.55, depth=0.0003,
                                                location=(x, y, z + sgn * (proud + 0.00005)))
            s = bpy.context.active_object
            s.name = name + "_socket"
            finish(s, M_BORE, bevel=0, smooth=False)
    else:
        finish(hs.cyl_x(name, r, x, x + sgn * proud, verts=20, y=y, z=z), m, bevel=0.0003, segments=2)
        if hi():
            finish(hs.cyl_x(name + "_socket", r * 0.55, x + sgn * proud, x + sgn * (proud + 0.0002), verts=6,
                            fixed=True, y=y, z=z), M_BORE, bevel=0, smooth=False)


# ---------------------------------------------------------------- receiver
def build_receiver():
    rec = hs.section("receiver", rec_section(), REC_X0, REC_X1)
    # Ejection port (right): a cavity the bolt sits in.
    hs.cut(rec, hs.box("port_cut", (PORT_X1 - PORT_X0, 0.030, PORT_Z1 - PORT_Z0),
                       ((PORT_X0 + PORT_X1) / 2, -REC_HW + 0.012, (PORT_Z0 + PORT_Z1) / 2)))
    # Pressed bolt-guide grooves along both sides.
    for sy in (-1, 1):
        x1 = 0.028 if sy < 0 else 0.070
        hs.cut(rec, hs.box(f"guide_groove{sy}", (x1 + 0.150, 0.0018, 0.0040), ((x1 - 0.150) / 2, sy * REC_HW, 0.0050)))
    finish(rec, M_STEEL, bevel=0.0008)
    # Stamped lip round the port.
    yr = -REC_HW - 0.0002
    for nm, sx, sz, cx, cz in (("port_lip_top", PORT_X1 - PORT_X0 + 0.005, 0.0018, (PORT_X0 + PORT_X1) / 2, PORT_Z1 + 0.0009),
                               ("port_lip_bot", PORT_X1 - PORT_X0 + 0.005, 0.0018, (PORT_X0 + PORT_X1) / 2, PORT_Z0 - 0.0009),
                               ("port_lip_rear", 0.0022, PORT_Z1 - PORT_Z0 + 0.003, PORT_X0 - 0.0011, (PORT_Z0 + PORT_Z1) / 2),
                               ("port_lip_front", 0.0022, PORT_Z1 - PORT_Z0 + 0.003, PORT_X1 + 0.0011, (PORT_Z0 + PORT_Z1) / 2)):
        finish(hs.box(nm, (sx, 0.0012, sz), (cx, yr, cz)), M_STEEL, bevel=0.0004)
    # Chamber face at the front of the port.
    finish(hs.cyl_x("chamber_face", 0.0088, PORT_X1 - 0.0012, PORT_X1 - 0.0004, verts=24), M_BORE, bevel=0)
    # Stamped stiffening pads over the magazine well and behind the port.
    for sy in (-1, 1):
        side_pad(f"stiff_rear{sy}", sy, -0.148, -0.060, -0.0085, -0.0015, 0.0007, M_STEEL)
        if sy > 0:
            side_pad("stiff_front", sy, 0.036, 0.090, -0.0085, -0.0015, 0.0007, M_STEEL)
        if hi():
            # Spot welds along the lower flange and the top seam.
            for i in range(9):
                x = -0.150 + i * 0.022
                if sy < 0 and x > PORT_X0 - 0.012:
                    continue
                finish(hs.cyl_y(f"weld{sy}_{i}", 0.0016, 0.0006, (x, sy * REC_HW, 0.0105), verts=12), M_STEEL,
                       bevel=0, smooth=False)
    # Receiver front: trunnion collar around barrel and cocking tube.
    finish(hs.section("trunnion", [(-0.0150, -0.0105), (0.0150, -0.0105), (0.0165, 0.004), (0.0150, 0.030),
                                   (0.0100, 0.0395), (-0.0100, 0.0395), (-0.0150, 0.030), (-0.0165, 0.004)],
                      REC_X1 - 0.001, REC_X1 + 0.004), M_STEEL, bevel=0.0008)

    # Magazine well, cut open underneath; mag release paddle and button.
    well = hs.side_profile("mag_well", [(WELL_X0, REC_ZB + 0.002), (WELL_X1, REC_ZB + 0.002), (WELL_X1 + 0.003, -0.066),
                                        (WELL_X0 - 0.001, -0.059)], 0.0312)
    hs.cut(well, hs.prism("well_hole", [(MAG_X0 - 0.0012, -0.0126, -0.080), (MAG_X1 + 0.0050, -0.0126, -0.080),
                                        (MAG_X1 + 0.0050, 0.0126, -0.080), (MAG_X0 - 0.0012, 0.0126, -0.080)],
                          (0, 0, 0.058)))
    finish(well, M_STEEL, bevel=0.0009)
    for sy in (-1, 1):
        side_pad(f"well_rib{sy}", sy, 0.0575, 0.0905, -0.052, -0.022, 0.0007, M_STEEL, hw=0.0156)
        # Rolled lip at the mouth of the well.
        finish(hs.cyl_between(f"well_lip{sy}", (WELL_X0 - 0.0005, sy * 0.0158, -0.0588), (WELL_X1 + 0.0028, sy * 0.0158, -0.0655),
                              0.0013, verts=10), M_STEEL, bevel=0)
    paddle = hs.side_profile("mag_paddle", [(0.0448, -0.0385), (0.0498, -0.0385), (0.0494, -0.066), (0.0462, -0.0735),
                                            (0.0425, -0.0725), (0.0440, -0.064)], 0.0125)
    finish(paddle, M_OXIDE, bevel=0.0006)
    if hi():
        for i in range(5):
            finish(hs.box(f"paddle_rib{i}", (0.0010, 0.0115, 0.0010), (0.0437 + i * 0.0002, 0, -0.0655 - i * 0.0016)),
                   M_OXIDE, bevel=0)
    finish(hs.cyl_y("mag_button", 0.0042, 0.0045, (0.0455, -0.0177, -0.0285), verts=20), M_OXIDE, bevel=0.0006)
    if hi():
        for i in range(4):
            finish(hs.box(f"mag_button_rib{i}", (0.0062 - abs(i - 1.5) * 0.0012, 0.0005, 0.0007),
                          (0.0455, -0.0201, -0.0308 + i * 0.0015)), M_OXIDE, bevel=0)

    # Housing pins and the two stock pins, heads on both sides.
    for nm, x, z, r in (("front_pin", 0.0400, -0.0190, 0.0032), ("stock_pin_a", -0.1560, -0.0040, 0.0030),
                        ("stock_pin_b", -0.1560, 0.0165, 0.0030)):
        hw = HOUSING_HW + 0.0010 if nm == "front_pin" else REC_HW + 0.0022
        finish(hs.cyl_y(nm, r, hw * 2, (x, 0, z), verts=20), M_OXIDE, bevel=0.0005, segments=2)
        if hi():
            finish(hs.cyl_y(nm + "_clip", r * 0.45, hw * 2 + 0.0006, (x, 0, z), verts=12), M_BORE, bevel=0)

    # Markings.
    yl = REC_HW + 0.00005
    text("mark_model", "MP5-N", 0.0050, (0.0925, 0.0156 + 0.0007, -0.0335), (PI / 2, 0, PI))
    text("mark_cal", "Kal. 9mm x 19", 0.0030, (0.0925, 0.0156 + 0.0007, -0.0425), (PI / 2, 0, PI))
    text("mark_serial", "GRF 0905", 0.0038, (0.0300, yl, -0.0015), (PI / 2, 0, PI))
    text("mark_proof", "11/26  AK", 0.0026, (-0.0900, yl, -0.0105), (PI / 2, 0, PI))
    text("mark_right", "GRAFT ARMS  9x19", 0.0028, (-0.1300, -yl, -0.0105), (PI / 2, 0, 0))


def build_bolt():
    """Bolt head and carrier, seen through the ejection port: the moving `slide` part."""
    part("slide")
    finish(hs.box("carrier", (0.062, 0.0240, 0.0085), (0.058, -0.0052, 0.0098)), M_OXIDE, bevel=0.0008)
    finish(hs.box("bolt_head", (0.052, 0.0200, 0.0112), (0.0635, -0.0064, -0.0012)), M_BOLT, bevel=0.0012)
    # Flat on the bolt head with the extractor claw and its spring.
    finish(hs.box("extractor", (0.024, 0.0022, 0.0042), (0.0775, -0.0166, -0.0012)), M_OXIDE, bevel=0.0005)
    finish(hs.box("extractor_claw", (0.0030, 0.0030, 0.0046), (0.0893, -0.0162, -0.0012)), M_OXIDE, bevel=0.0004)
    if hi():
        finish(hs.cyl_y("extractor_pin", 0.0011, 0.0006, (0.0700, -0.0178, -0.0012), verts=10), M_BOLT, bevel=0)
        # Carrier lightening cut and wear line.
        finish(hs.box("carrier_cut", (0.030, 0.0006, 0.0030), (0.066, -0.0173, 0.0100)), M_BORE, bevel=0)
    part("body")


# ---------------------------------------------------------------- barrel, cocking tube, front sight
def build_front():
    finish(hs.cyl_x("barrel", 0.0078, REC_X1, SUP_X0 + 0.004, verts=24), M_OXIDE, bevel=0.0003)
    tube = hs.cyl_x("cocking_tube", CT_R, REC_X1, FS_X1 + 0.001, verts=40, z=CT_Z)
    # Slot down the left side for the cocking handle; hold-open notch at the rear.
    cy, cz = math.cos(SLOT_A), math.sin(SLOT_A)
    slot = hs.box("ct_slot", (0.126, 0.012, 0.0046), (0, 0, 0))
    slot.rotation_euler = (SLOT_A, 0, 0)
    slot.location = (0.190, cy * CT_R, CT_Z + cz * CT_R)
    hs.cut(tube, slot)
    notch = hs.box("ct_notch", (0.0085, 0.012, 0.0100), (0, 0, 0))
    notch.rotation_euler = (SLOT_A, 0, 0)
    notch.location = (0.1318, cy * CT_R - cz * 0.004, CT_Z + cz * CT_R + cy * 0.004)
    hs.cut(tube, notch)
    finish(tube, M_STEEL, bevel=0.0004)
    finish(hs.cyl_x("ct_core", CT_R - 0.0022, REC_X1 + 0.002, FS_X0, verts=24, z=CT_Z), M_BORE, bevel=0)
    finish(hs.lathe_x("ct_cap", [(FS_X1, CT_R + 0.0008), (FS_X1 + 0.0040, CT_R + 0.0008), (FS_X1 + 0.0072, CT_R - 0.0020),
                                 (FS_X1 + 0.0080, 0.0040)], verts=40), M_STEEL, bevel=0.0005).location = (0, 0, CT_Z)
    screw("ct_cap_screw", (FS_X1 + 0.0080, 0, CT_Z), "x+", 0.0034)
    finish(hs.lathe_x("ct_collar", [(REC_X1 + 0.003, CT_R + 0.0022), (REC_X1 + 0.0085, CT_R + 0.0022),
                                    (REC_X1 + 0.0100, CT_R + 0.0004)], verts=40), M_STEEL, bevel=0.0004).location = (0, 0, CT_Z)

    # Cocking handle (its own part).
    part("charging_handle")
    hx = 0.2440
    out = V((0.0, cy, cz))
    base = V((hx, 0.0, CT_Z))
    finish(hs.box("ch_block", (0.012, 0.004, 0.0042), (0, 0, 0)), M_OXIDE, bevel=0.0005)
    blk = bpy.data.objects["ch_block"]
    blk.rotation_euler = (SLOT_A, 0, 0)
    blk.location = base + out * (CT_R + 0.0004)
    finish(hs.cyl_between("ch_stem", base + out * (CT_R - 0.001), base + out * (CT_R + 0.0125) + V((0.002, 0, 0)), 0.0030,
                          verts=16), M_OXIDE, bevel=0.0004)
    k0 = base + out * (CT_R + 0.0095) + V((0.0015, 0, 0))
    k1 = base + out * (CT_R + 0.0345) + V((0.0060, 0, 0))
    finish(hs.cyl_between("ch_knob", k0, k1, 0.0052, verts=24, radius2=0.0046), M_POLY, bevel=0.0010)
    for i in range(5):
        t0 = 0.16 + i * 0.15
        a, b = k0.lerp(k1, t0), k0.lerp(k1, t0 + 0.07)
        finish(hs.cyl_between(f"ch_knob_ring{i}", a, b, 0.0057, verts=24), M_POLY, bevel=0)
    finish(hs.cyl_between("ch_knob_cap", k1, k1 + (k1 - k0).normalized() * 0.0016, 0.0050, verts=24), M_OXIDE, bevel=0.0005)
    part("body")

    # Front sight tower: casting round barrel and tube, hooded post on top, sling pin, handguard pin.
    finish(hs.section("fs_tower", [(-0.0118, -0.0125), (0.0118, -0.0125), (0.0140, 0.002), (0.0132, 0.036),
                                   (0.0080, 0.0465), (-0.0080, 0.0465), (-0.0132, 0.036), (-0.0140, 0.002)],
                      FS_X0, FS_X1), M_STEEL, bevel=0.0010)
    hood = hs.cyl_x("fs_hood", 0.0128, FS_X0 + 0.002, FS_X1 - 0.002, verts=40, z=SIGHT_Z)
    hs.cut(hood, hs.cyl_x("fs_hood_in", 0.0108, FS_X0 - 0.01, FS_X1 + 0.01, verts=40, z=SIGHT_Z))
    finish(hood, M_STEEL, bevel=0.0005)
    finish(hs.box("fs_post", (0.0036, 0.0020, 0.0125), (FS_X0 + 0.0115, 0, SIGHT_Z - 0.0060)), M_OXIDE, bevel=0.0003)
    finish(hs.box("fs_post_dot", (0.0005, 0.0013, 0.0020), (FS_X0 + 0.0095, 0, SIGHT_Z - 0.0012)), M_PAINT, bevel=0)
    finish(hs.cyl_y("fs_pin", 0.0026, 0.0305, (FS_X0 + 0.0115, 0, -0.0060), verts=16), M_OXIDE, bevel=0.0004)
    finish(hs.cyl_y("fs_sling_pin", 0.0022, 0.0400, (FS_X0 + 0.0115, 0, 0.0080), verts=14), M_OXIDE, bevel=0.0004)
    for sy in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(24), minor_segments=8 if hi() else 4, major_radius=0.0060,
                                         minor_radius=0.0012, location=(FS_X0 + 0.0115, sy * 0.0192, 0.0030),
                                         rotation=(0, PI / 2, 0))
        ring = bpy.context.active_object
        ring.name = f"fs_sling_ring{sy}"
        finish(ring, M_OXIDE, bevel=0)
        if sy > 0:
            break
    if hi():
        text("fs_mark", "9", 0.0036, (FS_X1 - 0.004, 0.0140, 0.020), (PI / 2, 0, PI))


# ---------------------------------------------------------------- rear sight, top rail
def build_sights():
    # Rear sight base (welded to the receiver top) and the rotary diopter drum.
    finish(hs.section("rs_base", [(-0.0135, 0.0350), (0.0135, 0.0350), (0.0135, 0.0445), (0.0105, 0.0478),
                                  (-0.0105, 0.0478), (-0.0135, 0.0445)], -0.150, -0.106), M_STEEL, bevel=0.0009)
    for sy in (-1, 1):
        finish(hs.side_profile(f"rs_ear{sy}", [(-0.150, 0.0470), (-0.139, 0.0470), (-0.1405, 0.0545), (-0.1485, 0.0545)],
                               0.0026, y=sy * 0.0118), M_STEEL, bevel=0.0005)
    drum = hs.cyl_z("rs_drum", 0.0108, 0.0165, (-0.1245, 0, 0.0557), verts=40)
    hs.cut(drum, hs.cyl_x("rs_aperture", 0.0016, -0.14, -0.11, verts=16, z=SIGHT_Z))
    hs.cut(drum, hs.cyl_x("rs_aperture_cone", 0.0048, -0.1375, -0.1325, verts=20, z=SIGHT_Z, radius2=0.0016))
    hs.cut(drum, hs.box("rs_vnotch", (0.03, 0.0030, 0.004), (-0.1245, 0, 0.0645)))
    finish(drum, M_OXIDE, bevel=0.0007)
    screw("rs_elev_screw", (-0.1245, 0.0052, 0.0639), "z+", 0.0024, m=M_STEEL, proud=0.0005)
    finish(hs.cyl_y("rs_windage", 0.0034, 0.0040, (-0.1120, -0.0152, 0.0415), verts=16), M_OXIDE, bevel=0.0006)
    if hi():
        for k in range(4):
            a = math.radians(-60 + k * 40)
            finish(hs.box(f"rs_tick{k}", (0.0005, 0.0012, 0.0022 if k != 1 else 0.0034),
                          (-0.1245 - math.cos(a) * 0.01085, math.sin(a) * 0.01085, 0.0610), (0, 0, -a)), M_PAINT, bevel=0)
        finish(hs.box("rs_dot", (0.0005, 0.0014, 0.0014), (-0.13535, 0.0038, SIGHT_Z)), M_PAINT, bevel=0)
        finish(hs.box("rs_dot2", (0.0005, 0.0014, 0.0014), (-0.13535, -0.0038, SIGHT_Z)), M_PAINT, bevel=0)

    # Receiver top rail: saddle on the rounded top, clamp blocks, Picatinny strip.
    finish(hs.section("rail_saddle", [(-0.0150, 0.0345), (0.0150, 0.0345), (0.0150, 0.0440), (0.0110, 0.0470),
                                      (-0.0110, 0.0470), (-0.0150, 0.0440)], -0.100, 0.054), M_ALU, bevel=0.0008)
    pic_rail("top_rail", -0.098, 0.052, RAIL_Z, 0.0455, M_ALU, -0.090, 14)
    for i, x in enumerate((-0.082, 0.038)):
        for sy in (-1, 1):
            finish(hs.box(f"rail_claw{i}_{sy}", (0.020, 0.0050, 0.0130), (x, sy * 0.0163, 0.0372)), M_ALU, bevel=0.0010)
            screw(f"rail_claw_screw{i}_{sy}", (x, sy * 0.0188, 0.0385), "y+" if sy > 0 else "y-", 0.0028)
    if hi():
        for i in range(0, 14, 2):
            text(f"rail_no{i}", str(i + 1), 0.0026, (-0.0835 + i * 0.010, -0.0092, 0.04905), (PI / 4, 0, 0), M_PAINT,
                 extrude=0.00008)


# ---------------------------------------------------------------- red-dot sight
def build_red_dot():
    """Enclosed-emitter red dot on the top rail: big window, emitter in the roof."""
    z0, z1 = RAIL_Z + 0.0035, RAIL_Z + 0.0445          # body bottom / top
    hw = 0.0190
    wz0, wz1, whw = DOT_Z - 0.0125, DOT_Z + 0.0125, 0.0150   # window
    # Clamp base on the rail: fixed jaw left, clamp bar and two cross-bolts right.
    finish(hs.section("rds_base", [(-0.0135, RAIL_Z - 0.0062), (-0.0112, RAIL_Z - 0.0062), (-0.0112, RAIL_Z + 0.0002),
                                   (0.0112, RAIL_Z + 0.0002), (0.0112, RAIL_Z - 0.0030), (0.0135, RAIL_Z - 0.0030),
                                   (0.0150, z0 + 0.001), (-0.0150, z0 + 0.001)], DOT_X0 + 0.003, DOT_X1 - 0.003), M_ALU,
           bevel=0.0007)
    finish(hs.box("rds_clamp_bar", (0.042, 0.0040, 0.0078), ((DOT_X0 + DOT_X1) / 2, -0.0136, RAIL_Z - 0.0030)), M_ALU,
           bevel=0.0009)
    for i, x in enumerate((DOT_X0 + 0.014, DOT_X1 - 0.014)):
        screw(f"rds_clamp_bolt{i}", (x, -0.0156, RAIL_Z - 0.0030), "y-", 0.0036, proud=0.0018)
    # Body: rounded housing with the window bored through; front lip steps down.
    body = hs.loft_x("rds_body", [(DOT_X0, z1 - 0.0010, z0 + 0.0010, hw - 0.0010), (DOT_X0 + 0.0020, z1, z0, hw),
                                  (DOT_X1 - 0.0060, z1, z0, hw), (DOT_X1 - 0.0040, z1 - 0.0016, z0 + 0.0008, hw - 0.0012),
                                  (DOT_X1, z1 - 0.0022, z0 + 0.0012, hw - 0.0016)], power=6.0)
    hs.cut(body, hs.loft_x("rds_window", [(DOT_X0 - 0.01, wz1, wz0, whw), (DOT_X1 + 0.01, wz1, wz0, whw)], power=6.0))
    finish(body, M_ALU, bevel=0.0007)
    # Roof: emitter housing fins, elevation adjuster.
    for i in range(5):
        finish(hs.box(f"rds_fin{i}", (0.0022, 0.0250, 0.0012), (DOT_X0 + 0.0080 + i * 0.0044, 0, z1 + 0.0003)), M_ALU,
               bevel=0.0003)
    screw("rds_elev", (DOT_X1 - 0.0180, 0, z1), "z+", 0.0040, proud=0.0010)
    # Right side: battery cap, windage adjuster. Left side: brightness buttons.
    finish(hs.cyl_y("rds_batt", 0.0088, 0.0032, (DOT_X0 + 0.0170, -hw - 0.0013, z0 + 0.0125), verts=32), M_ALU, bevel=0.0008)
    finish(hs.box("rds_batt_slot", (0.0100, 0.0006, 0.0016), (DOT_X0 + 0.0170, -hw - 0.0029, z0 + 0.0125)), M_BORE, bevel=0)
    screw("rds_wind", (DOT_X1 - 0.0180, -hw, z1 - 0.0052), "y-", 0.0032, proud=0.0008)
    for i, sym in enumerate(("-", "+")):
        bx = DOT_X0 + 0.0160 + i * 0.0130
        finish(hs.box(f"rds_button{i}", (0.0090, 0.0016, 0.0058), (bx, hw + 0.0005, z0 + 0.0040)), M_RUBBER, bevel=0.0006)
        if hi():
            finish(hs.box(f"rds_sym{i}", (0.0030, 0.0003, 0.0007), (bx, hw + 0.0014, z0 + 0.0040)), M_PAINT, bevel=0)
            if sym == "+":
                finish(hs.box("rds_sym_v", (0.0007, 0.0003, 0.0030), (bx, hw + 0.0014, z0 + 0.0040)), M_PAINT, bevel=0)
    if hi():
        # Knurl on the battery cap, click marks round the adjusters.
        for k in range(28):
            a = 2 * PI * k / 28
            finish(hs.box(f"rds_batt_knurl{k}", (0.0009, 0.0026, 0.0009),
                          (DOT_X0 + 0.0170 + math.cos(a) * 0.0088, -hw - 0.0014, z0 + 0.0125 + math.sin(a) * 0.0088),
                          (0, -a, 0)), M_ALU, bevel=0)
        for k in range(12):
            a = 2 * PI * k / 12
            finish(hs.box(f"rds_elev_tick{k}", (0.0014, 0.0004, 0.0002),
                          (DOT_X1 - 0.0180 + math.cos(a) * 0.0056, math.sin(a) * 0.0056, z1 + 0.0001), (0, 0, a)),
                   M_PAINT, bevel=0)
    text("rds_mark", "RDS-2   2 MOA", 0.0030, (DOT_X1 - 0.0080, hw + 0.00005, z1 - 0.0062), (PI / 2, 0, PI))
    text("rds_mark_r", "GRF OPTRONIC", 0.0024, (DOT_X0 + 0.0290, -hw - 0.00005, z0 + 0.0030), (PI / 2, 0, 0))
    # Glass (the game makes it transparent) and the dot.
    part("lens")
    for i, (x, tilt) in enumerate(((DOT_X1 - 0.0085, 0.0010), (DOT_X0 + 0.0050, 0.0))):
        lens = hs.loft_x(f"rds_lens{i}", [(x, wz1 + 0.0004, wz0 - 0.0004, whw + 0.0004),
                                          (x + 0.0012, wz1 + 0.0004, wz0 - 0.0004, whw + 0.0004)], power=6.0)
        del tilt
        finish(lens, M_LENS, bevel=0)
    part("reticle")
    finish(hs.cyl_x("rds_dot", 0.00075, DOT_X1 - 0.0092, DOT_X1 - 0.0087, verts=12, fixed=True, z=DOT_Z), M_RED, bevel=0,
           smooth=False)
    part("body")


# ---------------------------------------------------------------- handguard, under rail, foregrip, laser
def build_handguard():
    hg = hs.loft_x("handguard", [(HG_X0, 0.0200, -0.0285, 0.0215), (HG_X0 + 0.010, 0.0222, -0.0300, 0.0262),
                                 (HG_X1 - 0.014, 0.0222, -0.0300, 0.0258), (HG_X1 - 0.004, 0.0210, -0.0292, 0.0236),
                                 (HG_X1, 0.0196, -0.0280, 0.0212)], power=4.2)
    # The cocking tube runs in an open channel along the top.
    hs.cut(hg, hs.box("hg_channel", (0.20, 0.0236, 0.03), ((HG_X0 + HG_X1) / 2, 0, 0.0155 + 0.0150)))
    finish(hg, M_POLY, bevel=0.0010)
    for sy in (-1, 1):
        for i, z in enumerate((-0.0175, -0.0090, -0.0005, 0.0080)):
            if sy > 0 and i == 0:
                continue   # the laser's pressure pad sits here on the left
            rib = hs.loft(f"hg_rib{sy}_{i}", [((x, sy * 0.0262, z), (0, 0, 1), (0, 1, 0), hz, 0.0016)
                                                for x, hz in ((0.122, 0.0006), (0.128, 0.0022), (0.236, 0.0022), (0.242, 0.0006))],
                          n=12 if hi() else 6, power=2.5)
            finish(rib, M_POLY, bevel=0)
    # Front and rear bands, the retaining pin.
    finish(hs.loft_x("hg_band_rear", [(HG_X0 - 0.0005, 0.0204, -0.0290, 0.0222), (HG_X0 + 0.0050, 0.0216, -0.0298, 0.0246)],
                     power=4.2), M_OXIDE, bevel=0.0006, angle=50)
    finish(hs.cyl_y("hg_pin", 0.0030, 0.0450, (HG_X1 - 0.0075, 0, -0.0190), verts=16), M_OXIDE, bevel=0.0005)

    # Under-barrel Picatinny strip on two stand-offs, three screws.
    finish(hs.box("urail_seat", (0.118, 0.0180, 0.0030), (0.211, 0, -0.0300)), M_ALU, bevel=0.0006)
    pic_rail("under_rail", 0.150, 0.272, URAIL_Z, -0.0298, M_ALU, 0.157, 12)
    if hi():
        for i, x in enumerate((0.162, 0.212, 0.262)):
            finish(hs.cyl_z(f"urail_screw{i}", 0.0019, 0.0004, (x, 0, URAIL_Z - 0.0001), verts=12), M_OXIDE, bevel=0)


def build_foregrip():
    """The MG42's clamp-on vertical foregrip, FG_DZ lower (the arms' support hand fits unchanged)."""
    dz = FG_DZ
    finish(hs.box("fg_block", (0.026, 0.0250, 0.0105), (0.202, 0, -0.0335 + dz)), M_ALU, bevel=0.0012)
    finish(hs.cyl_y("fg_bolt", 0.003, 0.031, (0.202, 0, -0.033 + dz), verts=16), M_OXIDE, bevel=0.0004)
    finish(hs.cyl_y("fg_nut", 0.0055, 0.004, (0.202, -0.0160, -0.033 + dz), verts=6), M_OXIDE, bevel=0.0004)
    grip = hs.cyl_between("fg_grip", (0.203, 0, -0.036 + dz), (0.211, 0, -0.130 + dz), 0.0165, verts=32)
    for i in range(4):
        z = -0.056 - i * 0.021
        bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(32), minor_segments=8, major_radius=0.0172,
                                         minor_radius=0.0021,
                                         location=(0.203 + (z + 0.036) / -0.094 * 0.008, 0, z + dz))
        hs.cut(grip, bpy.context.active_object)
    finish(grip, M_POLY, bevel=0.0012)
    finish(hs.cyl_between("fg_cap", (0.211, 0, -0.128 + dz), (0.2117, 0, -0.136 + dz), 0.0176, verts=32), M_OXIDE,
           bevel=0.0015)


def build_laser():
    """LA-9G green laser module on the under rail, ahead of the foregrip."""
    zt, zb, hw = URAIL_Z + 0.0036, -0.0640, 0.0148
    x0, x1 = LASER_X0, LASER_X1
    body = hs.loft_x("laser_body", [(x0, zt, zb + 0.0040, hw - 0.0020), (x0 + 0.0040, zt, zb, hw),
                                    (x1 - 0.0030, zt, zb, hw), (x1, zt, zb + 0.0016, hw - 0.0014)], power=5.0)
    # Rail channel through the top so the module reads as clamped on, not fused.
    hs.cut(body, hs.box("laser_rail_cut", (0.08, 0.0218, 0.0080), ((x0 + x1) / 2, 0, URAIL_Z + 0.0036)))
    finish(body, M_ALU, bevel=0.0008)
    # Clamp bar and cross-bolts (right side).
    finish(hs.box("laser_clamp", (0.034, 0.0036, 0.0070), ((x0 + x1) / 2, -hw - 0.0006, URAIL_Z + 0.0012)), M_ALU, bevel=0.0008)
    for i, x in enumerate((x0 + 0.0115, x1 - 0.0115)):
        screw(f"laser_bolt{i}", (x, -hw - 0.0024, URAIL_Z + 0.0012), "y-", 0.0030, proud=0.0014)
    # Emitter: bezel proud of the front face, the window (emissive, its own part), a recessed sensor beside it.
    bez = hs.lathe_x("laser_bezel", [(x1 - 0.0020, 0.0086), (x1 + 0.0030, 0.0086), (x1 + 0.0042, 0.0076)], verts=32)
    hs.cut(bez, hs.cyl_x("laser_bezel_bore", 0.0060, x1 - 0.01, x1 + 0.01, verts=24))
    bez.location = (0, 0.0030, LASER_Z)
    for c in bez.modifiers:
        c.object.location = (0, 0.0030, LASER_Z)
    finish(bez, M_OXIDE, bevel=0.0005)
    if hi():
        for k in range(24):
            a = 2 * PI * k / 24
            finish(hs.box(f"laser_bezel_knurl{k}", (0.0036, 0.0009, 0.0009),
                          (x1 + 0.0010, 0.0030 + math.cos(a) * 0.0086, LASER_Z + math.sin(a) * 0.0086), (a, 0, 0)),
                   M_OXIDE, bevel=0)
    part("laser")
    finish(hs.cyl_x("laser_window", 0.0061, x1 + 0.0012, x1 + 0.0020, verts=24, y=0.0030, z=LASER_Z), M_GREEN, bevel=0)
    part("body")
    finish(hs.cyl_x("laser_sensor", 0.0022, x1 - 0.0004, x1 + 0.0006, verts=14, y=-0.0088, z=LASER_Z - 0.0050), M_LENS,
           bevel=0)
    finish(hs.cyl_x("laser_led", 0.0010, x1 - 0.0004, x1 + 0.0004, verts=10, y=-0.0088, z=LASER_Z + 0.0052), M_GREEN,
           bevel=0)
    # Zeroing screws: windage on the right, elevation underneath. Mode switch on the left. Battery cap at the rear.
    screw("laser_wind", (x1 - 0.0120, -hw, LASER_Z), "y-", 0.0028, proud=0.0008)
    screw("laser_elev", (x1 - 0.0120, 0.0030, zb), "z-", 0.0028, proud=0.0008)
    finish(hs.box("laser_switch", (0.0110, 0.0020, 0.0070), (x0 + 0.0190, hw + 0.0006, LASER_Z - 0.0010)), M_RUBBER,
           bevel=0.0008)
    finish(hs.cyl_x("laser_batt", 0.0070, x0 - 0.0036, x0 + 0.002, verts=28, y=-0.0040, z=LASER_Z - 0.0010), M_ALU, bevel=0.0007)
    finish(hs.box("laser_batt_slot", (0.0005, 0.0086, 0.0014), (x0 - 0.0037, -0.0040, LASER_Z - 0.0010)), M_BORE, bevel=0)
    # Warning label and markings.
    finish(hs.box("laser_label", (0.0200, 0.0003, 0.0085), (x0 + 0.0240, -hw - 0.00005, LASER_Z - 0.0060)), M_YELLOW, bevel=0)
    text("laser_label_txt", "LASER 3R", 0.0026, (x0 + 0.0150, -hw - 0.0002, LASER_Z - 0.0052), (PI / 2, 0, 0), M_BORE,
         extrude=0.00006)
    text("laser_label_txt2", "520 nm <5 mW", 0.0017, (x0 + 0.0150, -hw - 0.0002, LASER_Z - 0.0086), (PI / 2, 0, 0), M_BORE,
         extrude=0.00006)
    text("laser_mark", "LA-9G", 0.0036, (x1 - 0.0100, hw + 0.00005, LASER_Z + 0.0052), (PI / 2, 0, PI))
    # Pressure pad on the left of the handguard, cable down to the module.
    px0, px1, pz = 0.128, 0.176, -0.0175
    finish(hs.loft("laser_pad", [((x, 0.0266, pz), (0, 0, 1), (0, 1, 0), hz, 0.0024)
                                 for x, hz in ((px0, 0.0030), (px0 + 0.004, 0.0056), (px1 - 0.004, 0.0056), (px1, 0.0030))],
                   n=16 if hi() else 8, power=3.0), M_RUBBER, bevel=0)
    if hi():
        for i in range(7):
            finish(hs.box(f"laser_pad_rib{i}", (0.0010, 0.0006, 0.0080), (px0 + 0.012 + i * 0.004, 0.0290, pz)), M_RUBBER,
                   bevel=0)
    cable = hs.tube_path("laser_cable", [(px1 - 0.001, 0.0272, pz), (px1 + 0.010, 0.0268, pz - 0.006),
                                         (px1 + 0.022, 0.0215, pz - 0.0185), (x0 + 0.004, 0.0165, LASER_Z + 0.004),
                                         (x0 + 0.012, hw + 0.0004, LASER_Z + 0.0050)], 0.0015)
    finish(cable, M_RUBBER, bevel=0)
    finish(hs.cyl_between("laser_cable_plug", (x0 + 0.0085, hw + 0.0016, LASER_Z + 0.0050),
                          (x0 + 0.0160, hw + 0.0010, LASER_Z + 0.0050), 0.0024, verts=12), M_OXIDE, bevel=0.0004)


# ---------------------------------------------------------------- suppressor
def build_suppressor():
    r = SUP_R
    # Locking collar on the three-lug mount.
    finish(hs.lathe_x("can_collar", [(SUP_X0, 0.0120), (SUP_X0 + 0.0015, 0.0160), (SUP_X0 + 0.0155, 0.0160),
                                     (SUP_X0 + 0.0170, 0.0145)], verts=48), M_OXIDE, bevel=0.0005)
    if hi():
        for k in range(44):
            a = 2 * PI * k / 44
            finish(hs.box(f"can_knurl{k}", (0.0110, 0.0010, 0.0010),
                          (SUP_X0 + 0.0085, math.cos(a) * 0.0160, math.sin(a) * 0.0160), (a, 0, 0)), M_OXIDE, bevel=0)
    # Tube with shallow grooves near each end, stepped front cap.
    xa = SUP_X0 + 0.0165
    prof = [(xa, 0.0150), (xa + 0.0012, r)]
    for gx in (xa + 0.012, xa + 0.017, SUP_X1 - 0.030):
        prof += [(gx, r), (gx + 0.0005, r - 0.0007), (gx + 0.0020, r - 0.0007), (gx + 0.0025, r)]
    prof += [(SUP_X1 - 0.0100, r), (SUP_X1 - 0.0090, r - 0.0010), (SUP_X1 - 0.0018, r - 0.0010), (SUP_X1, r - 0.0030)]
    tube = hs.lathe_x("can_tube", prof, verts=56)
    hs.cut(tube, hs.cyl_x("can_bore", 0.0056, SUP_X1 - 0.014, SUP_X1 + 0.01, verts=24))
    finish(tube, M_CAN, bevel=0.0005)
    finish(hs.cyl_x("can_bore_dark", 0.0055, SUP_X1 - 0.0145, SUP_X1 - 0.0135, verts=24), M_BORE, bevel=0)
    # Wrench flats on the front cap, pin holes in its face.
    for k in range(6):
        a = 2 * PI * k / 6 + PI / 6
        finish(hs.box(f"can_flat{k}", (0.0062, 0.0090, 0.0008), (SUP_X1 - 0.0054, math.cos(a) * (r - 0.0008), math.sin(a) * (r - 0.0008)),
                      (a - PI / 2, 0, 0)), M_CAN, bevel=0.0003)
    if hi():
        for k in range(2):
            a = PI * k + PI / 2
            finish(hs.cyl_x(f"can_pin{k}", 0.0013, SUP_X1 - 0.0012, SUP_X1 - 0.0006, verts=10,
                            y=math.cos(a) * 0.0105, z=math.sin(a) * 0.0105), M_BORE, bevel=0)
    text("can_mark", "SD-9N   9x19   QD", 0.0034, (SUP_X0 + 0.060, -r - 0.0001, -0.0012), (PI / 2, 0, 0), extrude=0.00016)
    text("can_serial", "No 30417", 0.0026, (SUP_X0 + 0.118, r + 0.0001, -0.0010), (PI / 2, 0, PI), extrude=0.00016)


# ---------------------------------------------------------------- trigger housing, grip, stock
def picto(name, x, z, side, m, scale=1.0):
    """A bullet pictogram on the housing side, tip toward the muzzle (HIGH only)."""
    if not hi():
        return
    L, h = 0.0046 * scale, 0.00075 * scale
    pts = [(-L / 2, -h), (L * 0.2, -h), (L / 2, 0.0), (L * 0.2, h), (-L / 2, h)]
    ob = hs.prism(name, [(x + px, side * HOUSING_HW, z + pz) for px, pz in pts], (0, side * 0.00025, 0))
    finish(ob, m, bevel=0, smooth=False)


def grip_line(pts, z):
    """x on a polyline of (x, z) points (z descending) at height z."""
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        if z0 >= z >= z1:
            return x0 + (x1 - x0) * (z0 - z) / (z0 - z1)
    return pts[-1][0]


def build_lower():
    # Polymer trigger housing: box under the receiver with the beavertail, grip, trigger guard.
    box = hs.side_profile("housing", [(-0.112, REC_ZB + 0.0005), (0.0505, REC_ZB + 0.0005), (0.0505, -0.0315),
                                      (0.0445, -0.0372), (-0.0890, -0.0372), (-0.1010, -0.0345), (-0.112, -0.0270)],
                          HOUSING_HW * 2)
    finish(box, M_POLY, bevel=0.0022)
    # Grip: the shared Pistol 57 front and back strap lines, lofted through rounded sections; stippled.
    front = [(-0.0160, -0.0300), (-0.0170, -0.0330), (-0.0260, -0.0510), (-0.0560, -0.1340), (-0.0585, -0.1385)]
    back = [(-0.0890, -0.0300), (-0.0880, -0.0330), (-0.0810, -0.0460), (-0.1070, -0.1320), (-0.1055, -0.1385)]
    stations = []
    for i in range(15):
        z = -0.0300 - (0.1385 - 0.0300) * i / 14
        xf, xb = grip_line(front, z), grip_line(back, z)
        t = i / 14
        hw = 0.0152 + 0.0012 * math.sin(PI * min(1.0, t * 1.15))
        stations.append((((xf + xb) / 2, 0, z), (0, 1, 0), (1, 0, 0), hw, (xf - xb) / 2))
    finish(hs.loft("grip", stations, power=3.4), M_STIPPLE, bevel=0)
    # Smooth front and back straps over the stipple, flared grip cap.
    for nm, line, sgn in (("grip_front_strap", front, 1), ("grip_back_strap", back, -1)):
        strap = []
        for i in range(12):
            z = -0.0400 - (0.1340 - 0.0400) * i / 11
            x = grip_line(line, z)
            strap.append(((x - sgn * 0.0016, 0, z), (0, 1, 0), (1, 0, 0), 0.0078, 0.0022))
        finish(hs.loft(nm, strap, n=16 if hi() else 8, power=2.6), M_POLY, bevel=0)
    cap = []
    for z, g in ((-0.1366, 0.0004), (-0.1385, 0.0016), (-0.1432, 0.0016), (-0.1448, 0.0002)):
        zz = max(z, -0.1385)
        xf, xb = grip_line(front, zz), grip_line(back, zz)
        cap.append((((xf + xb) / 2, 0, z), (0, 1, 0), (1, 0, 0), 0.0156 + g, (xf - xb) / 2 + g))
    finish(hs.loft("grip_cap", cap, power=3.4), M_POLY, bevel=0.0006, angle=50)
    guard = hs.side_profile("trigger_guard", [(-0.021, -0.0340), (-0.020, -0.054), (-0.013, -0.0590), (0.034, -0.0590),
                                              (0.0425, -0.051), (0.0445, -0.0340)], 0.0140)
    hs.cut(guard, hs.side_profile("guard_hole", [(-0.0150, -0.0300), (0.0385, -0.0300), (0.0385, -0.0495),
                                                 (0.0320, -0.0548), (-0.0100, -0.0548), (-0.0150, -0.049)], 0.05))
    finish(guard, M_POLY, bevel=0.0012)
    finish(hs.side_profile("trigger", [(0.0115, -0.0340), (0.0180, -0.0340), (0.0165, -0.0420), (0.0205, -0.0510),
                                       (0.0160, -0.0535), (0.0085, -0.0420)], 0.0060), M_OXIDE, bevel=0.0007)

    # Ambidextrous selector with bullet pictograms (set to automatic).
    px, pz = -0.0420, -0.0178
    lever_a = math.radians(-50)
    for sy in (-1, 1):
        finish(hs.cyl_y(f"sel_pivot{sy}", 0.0052, 0.0030, (px, sy * (HOUSING_HW + 0.0012), pz), verts=24), M_OXIDE,
               bevel=0.0007)
        lever = hs.box(f"sel_lever{sy}", (0.0180 if sy > 0 else 0.0120, 0.0026, 0.0054), (0, 0, 0))
        lever.rotation_euler = (0, -lever_a, 0)
        ll = 0.0080 if sy > 0 else 0.0050
        lever.location = (px + math.cos(lever_a) * ll, sy * (HOUSING_HW + 0.0025), pz + math.sin(lever_a) * ll)
        finish(lever, M_OXIDE, bevel=0.0009)
        if hi():
            screw(f"sel_screw{sy}", (px, sy * (HOUSING_HW + 0.0027), pz), "y+" if sy > 0 else "y-", 0.0024, proud=0.0004,
                  slot="round")
        # Pictograms on an arc ahead of the pivot: safe (white, struck through), single (red), automatic (red, three).
        for nm, a_deg, m, n in (("safe", 6, M_PAINT, 1), ("semi", -22, M_REDPAINT, 1), ("auto", -50, M_REDPAINT, 3)):
            a = math.radians(a_deg)
            cx, cz = px + math.cos(a) * 0.0225, pz + math.sin(a) * 0.0225
            for k in range(n):
                picto(f"picto_{nm}{sy}_{k}", cx, cz + (k - (n - 1) / 2) * 0.0019, sy, m)
            if hi() and nm == "safe":
                bar = hs.box(f"picto_safe_bar{sy}", (0.0060, 0.0003, 0.0005), (cx, sy * (HOUSING_HW + 0.0002), cz), (0, 0.6, 0))
                finish(bar, M_PAINT, bevel=0, smooth=False)
    if hi():
        # Moulding line round the housing, pin bosses.
        for sy in (-1, 1):
            finish(hs.box(f"housing_line{sy}", (0.150, 0.0006, 0.0008), (-0.030, sy * HOUSING_HW, -0.0145)), M_POLY, bevel=0)
    text("housing_mark", "9mm", 0.0030, (-0.0760, HOUSING_HW + 0.00005, -0.0260), (PI / 2, 0, PI))

    # Back plate (stock base) with the release lever and the rear sling loop.
    plate = hs.section("back_plate", rec_section(grow=0.0016, zb=-0.0385), REC_X0 - 0.0130, REC_X0 + 0.0050)
    finish(plate, M_STEEL, bevel=0.0012)
    finish(hs.side_profile("stock_latch", [(REC_X0 - 0.0120, -0.0385), (REC_X0 + 0.0040, -0.0385), (REC_X0 + 0.0060, -0.0470),
                                           (REC_X0 - 0.0040, -0.0500), (REC_X0 - 0.0110, -0.0455)], 0.0150), M_OXIDE, bevel=0.0008)
    bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(24), minor_segments=8 if hi() else 4, major_radius=0.0062,
                                     minor_radius=0.0013, location=(REC_X0 - 0.0040, 0.0222, -0.0200), rotation=(0, PI / 2, 0))
    loop = bpy.context.active_object
    loop.name = "rear_sling_loop"
    finish(loop, M_OXIDE, bevel=0)
    finish(hs.box("rear_sling_lug", (0.0070, 0.0040, 0.0070), (REC_X0 - 0.0040, 0.0205, -0.0145)), M_STEEL, bevel=0.0008)

    # Retractable stock, collapsed: two forks along the receiver, butt plate.
    part("stock")
    for sy in (-1, 1):
        finish(hs.box(f"stock_fork{sy}", (0.218, 0.0036, 0.0098), (-0.084, sy * (REC_HW + 0.0018), 0.0182)), M_STEEL,
               bevel=0.0008)
        finish(hs.box(f"stock_fork_tip{sy}", (0.0080, 0.0042, 0.0110), (0.0235, sy * (REC_HW + 0.0018), 0.0182)), M_OXIDE,
               bevel=0.0008)
        if hi():
            for i in range(3):
                finish(hs.cyl_y(f"stock_detent{sy}_{i}", 0.0016, 0.0004, (-0.060 + i * 0.030, sy * (REC_HW + 0.0037), 0.0182),
                                verts=10), M_BORE, bevel=0)
    stations = []
    zc, half = -0.0060, 0.0575
    for i in range(13):
        t = -1 + 2 * i / 12
        z = zc + t * half
        x = -0.1915 - 0.0090 * t * t
        w = 0.0200 * (1 - 0.35 * abs(t) ** 3)
        stations.append(((x, 0, z), (0, 1, 0), (1, 0, 0), w, 0.0090 - 0.0030 * abs(t) ** 2))
    finish(hs.loft("butt_plate", stations, power=3.5), M_POLY, bevel=0.0010, angle=50)
    for sy in (-1, 1):
        finish(hs.box(f"butt_boss{sy}", (0.0120, 0.0050, 0.0150), (-0.1880, sy * (REC_HW + 0.0012), 0.0182)), M_STEEL,
               bevel=0.0012)
    if hi():
        for i in range(9):
            z = zc - 0.040 + i * 0.010
            finish(hs.box(f"butt_groove{i}", (0.0008, 0.0240, 0.0011), (-0.2004 - 0.0090 * ((z - zc) / half) ** 2 + 0.0030 * ((z - zc) / half) ** 2, 0, z)),
                   M_BORE, bevel=0)
    part("body")


# ---------------------------------------------------------------- magazine
def mag_frame(s):
    """Point on the magazine centreline `s` metres below its top, and the unit vector toward its front."""
    phi = s / MAG_R
    cx = (MAG_X0 + MAG_X1) / 2 + MAG_R
    p = V((cx - MAG_R * math.cos(phi), 0.0, MAG_TOP - MAG_R * math.sin(phi)))
    return p, V((math.cos(phi), 0.0, math.sin(phi)))


def build_magazine():
    part("magazine")
    half_d = (MAG_X1 - MAG_X0) / 2
    stations = []
    for i in range(15):
        s = MAG_LEN * i / 14
        p, d = mag_frame(s)
        stations.append((p, (0, 1, 0), d, MAG_HW, half_d))
    finish(hs.loft("mag_body", stations, power=6.5), M_STEEL, bevel=0.0010, angle=50)
    # Two pressed ribs down each side, the back seam, the floor plate.
    for sy in (-1, 1):
        for j, off in enumerate((-0.0068, 0.0058)):
            rib = []
            for i in range(11):
                s = 0.058 + (MAG_LEN - 0.074) * i / 10
                p, d = mag_frame(s)
                w = 0.0026 if 0 < i < 10 else 0.0008
                rib.append((p + d * off + V((0, sy * (MAG_HW - 0.0002), 0)), (0, 1, 0), d, 0.0011, w))
            finish(hs.loft(f"mag_rib{sy}_{j}", rib, n=12 if hi() else 6, power=2.5), M_STEEL, bevel=0)
    seam = []
    for i in range(9):
        p, d = mag_frame(0.004 + (MAG_LEN - 0.010) * i / 8)
        seam.append((p - d * (half_d + 0.0002), (0, 1, 0), d, 0.0042, 0.0009))
    finish(hs.loft("mag_seam", seam, n=12 if hi() else 6, power=4.0), M_STEEL, bevel=0)
    fp = []
    for s, g in ((MAG_LEN - 0.0015, 0.0012), (MAG_LEN + 0.0010, 0.0020), (MAG_LEN + 0.0048, 0.0020), (MAG_LEN + 0.0062, 0.0008)):
        p, d = mag_frame(s)
        fp.append((p, (0, 1, 0), d, MAG_HW + g, half_d + g))
    finish(hs.loft("mag_floor", fp, power=6.5), M_OXIDE, bevel=0.0006, angle=50)
    p, d = mag_frame(MAG_LEN + 0.0064)
    finish(hs.cyl_between("mag_floor_stud", p - d * 0.006, p - d * 0.006 + V((0, 0, -0.0008)), 0.0028, verts=14), M_STEEL,
           bevel=0.0003)
    # Feed lips, follower and the top round.
    for sy in (-1, 1):
        finish(hs.box(f"mag_lip{sy}", (0.0240, 0.0030, 0.0040), (MAG_X0 + 0.0135, sy * 0.0072, MAG_TOP + 0.0030)), M_STEEL,
               bevel=0.0006)
    finish(hs.box("mag_top_dark", (0.0300, 0.0190, 0.0006), ((MAG_X0 + MAG_X1) / 2, 0, MAG_TOP + 0.0002)), M_BORE, bevel=0)
    case = hs.lathe_x("round_case", [(0.0, 0.0040), (0.0006, 0.00495), (0.0012, 0.00495), (0.0015, 0.0044),
                                     (0.0022, 0.0044), (0.0026, 0.00495), (0.0188, 0.00490), (0.0192, 0.0046)], verts=24)
    case.location = (MAG_X0 + 0.0012, 0, MAG_TOP + 0.0030)
    finish(case, M_BRASS, bevel=0)
    bullet = hs.lathe_x("round_bullet", [(0.0190, 0.0045), (0.0225, 0.0044), (0.0255, 0.0037), (0.0280, 0.0024),
                                         (0.0293, 0.0009)], verts=24)
    bullet.location = (MAG_X0 + 0.0012, 0, MAG_TOP + 0.0030)
    finish(bullet, M_COPPER, bevel=0)
    pm, dm = mag_frame(MAG_LEN - 0.030)
    text("mag_mark", "9x19", 0.0042, (pm.x + 0.0050, MAG_HW + 0.00005, pm.z + 0.004), (PI / 2, 0, PI))
    text("mag_mark2", "30", 0.0050, (pm.x + 0.0030, MAG_HW + 0.00005, pm.z - 0.004), (PI / 2, 0, PI))
    del dm
    part("body")


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_receiver()
    build_bolt()
    build_front()
    build_sights()
    build_red_dot()
    build_handguard()
    build_foregrip()
    build_laser()
    build_suppressor()
    build_lower()
    build_magazine()
    bpy.ops.object.select_all(action="DESELECT")
    for ob in hs.PARTS:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = hs.PARTS[0]
    bpy.ops.object.convert(target="MESH")
    for ob in list(hs.PARTS):
        pid = PART_IDS[PART_OF.get(ob.name, "body")]
        attr = ob.data.attributes.new("part_id", "INT", "FACE")
        attr.data.foreach_set("value", [pid] * len(ob.data.polygons))
    joined = hs.join_parts(name)
    print(f"mp5 {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


def split_parts(low):
    """Separates LOW into one object per part id (shared material)."""
    objs = {}
    for pname, pid in PART_IDS.items():
        ob = low.copy()
        ob.data = low.data.copy()
        ob.name = pname
        ob.data.name = pname
        bpy.context.scene.collection.objects.link(ob)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer = bm.faces.layers.int.get("part_id")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != pid], context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.attributes.remove(ob.data.attributes["part_id"])
        objs[pname] = ob
        print(f"mp5: part {pname}: {bakeutil.tri_count(ob)} tris")
    bpy.data.objects.remove(low)
    return objs


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True,
                              export_image_format="AUTO", export_attributes=False)


# ---------------------------------------------------------------- preview
def preview_glass():
    """What the game does with the lens / reticle / laser parts: clear glass, lit dot, lit emitter."""
    g = bpy.data.materials.new("preview_glass")
    b = g.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.96, 0.9, 0.9, 1)
    b.inputs["Roughness"].default_value = 0.0
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.02
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Tint"].default_value = (1.0, 0.45, 0.35, 1)
    return g


def lamp(name, colour, strength):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Emission Color"].default_value = (*colour, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


def setup_render(samples, res):
    w, h = (int(x) for x in res.split("x"))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("studio")
    nt = world.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.007, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.13, 0.135, 0.145, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world

    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, -0.26)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.1, 0, -0.03), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.3, -1.2, 1.1), 55, 1.6, sy=0.5)
    area("strip_top", (0.15, 0.0, 1.1), 36, 2.2, sy=0.18)
    area("fill", (0.5, 1.3, 0.3), 32, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.5, -0.4, 0.5), 50, 0.8, (1.0, 0.82, 0.62))
    area("kick", (-1.3, 0.3, 0.2), 28, 1.0, (0.9, 0.95, 1.0))
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    return cam


def shoot(cam, path, loc, target, lens=50, fov_deg=None, fstop=0.0):
    d = cam.data
    if fov_deg:
        d.sensor_fit = "VERTICAL"
        d.angle = math.radians(fov_deg)
    else:
        d.sensor_fit = "AUTO"
        d.lens = lens
    d.dof.use_dof = fstop > 0
    if fstop:
        d.dof.aperture_fstop = fstop
        d.dof.focus_distance = (V(target) - V(loc)).length
    d.clip_start = 0.01
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"mp5: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((0.13, -2.05, -0.03), (0.13, 0, -0.045), 55, 0.0),
        "left_side": ((0.13, 2.05, -0.03), (0.13, 0, -0.045), 55, 0.0),
        "beauty": ((0.80, -0.80, 0.40), (0.14, 0, -0.03), 50, 8.0),
        "left": ((-0.34, 0.92, 0.36), (0.12, 0, -0.03), 45, 8.0),
        "receiver": ((0.16, -0.36, 0.17), (0.0, 0.0, 0.015), 50, 4.0),
        "optic": ((-0.20, 0.22, 0.16), (-0.02, 0.0, 0.055), 50, 4.0),
        "front": ((0.62, 0.30, -0.02), (0.30, 0.0, -0.01), 50, 4.0),
        "under": ((0.42, -0.34, -0.20), (0.22, 0.0, -0.035), 50, 4.0),
        # Roughly the player's hip view: eye behind and left of the gun, above it.
        "fp": ((-0.36, 0.10, 0.13), (0.6, -0.03, -0.04), 0, 0.0),
    }
    only = [s for s in args.only.split(",") if s]
    for key, (loc, target, lens, fstop) in shots.items():
        if only and key not in only:
            continue
        if key == "fp":
            shoot(cam, f"{stem}_{key}.png", loc, target, fov_deg=60)
        else:
            shoot(cam, f"{stem}_{key}.png", loc, target, lens=lens, fstop=fstop)


# ---------------------------------------------------------------- run
if args.out:
    high = build(hs.HIGH, "mp5_high")
    low = build(hs.LOW, "mp5_low")
    bakeutil.unwrap(low, boost={M_STEEL.name: 1.1, M_ALU.name: 1.2, M_OXIDE.name: 1.1, M_CAN.name: 0.9, M_BRASS.name: 1.3,
                                M_MARK.name: 1.5, M_PAINT.name: 1.5, M_POLY.name: 0.9, M_RUBBER.name: 0.9,
                                M_BORE.name: 0.6})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "mp5", cage=0.0012, ray=0.004,
                                 ao_distance=0.03, grime=0.35, log=print)
    bpy.data.objects.remove(high)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "mp5", emission_strength=4.0)
    objs = split_parts(low)
    export(list(objs.values()), args.out)
    print(f"mp5: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        for nm, m in (("lens", preview_glass()), ("reticle", lamp("preview_dot", (1.0, 0.1, 0.04), 12.0)),
                      ("laser", lamp("preview_laser", (0.1, 1.0, 0.22), 12.0))):
            ob = bpy.data.objects.get(nm)
            if ob:
                ob.data.materials.clear()
                ob.data.materials.append(m)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    high = build(hs.HIGH, "mp5_high")
    glass = preview_glass()
    for i, slot in enumerate(high.data.materials):
        if slot == M_LENS:
            high.data.materials[i] = glass
    render_previews(args.preview.rsplit(".", 1)[0])
