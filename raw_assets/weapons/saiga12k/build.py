"""Saiga-12K-style semi-automatic 12-gauge shotgun, milled black steel, with a
PSO-pattern 1x optic on a side mount.

Owner brief (2026-11-02): "a Saiga 12K semi-auto shotgun with an AK style
banana magazine and black steel milling ... choose what kind of rounds:
Dragon's Breath, double-aught buck or slugs ... a 1x magnification scope with
an interesting Russian SVD-like optic on there for the slug variant."

Built: AK-pattern gas-operated shotgun, 430 mm barrel. Milled black steel
receiver with lightening pockets, ribbed dust cover, tangent rear sight,
hooded front post, slotted brake. Milled steel handguards with vent slots, a
Picatinny strip under the lower one carrying a vertical foregrip (same grip as
the MG42's, so the support hand fits). Side-folding skeleton stock. 10-round
curved ("banana") polymer magazine, a strip of coloured tape round it that
shows the shell type loaded (tinted in game), and the top shell visible when
it drops out. Warsaw-pact side rail on the left; the optic is a PSO-1-style
long-eye-relief scope on its clamp bracket (rubber eyecup, sunshade, big
elevation drum, windage drum, illumination battery), 1x for this gun.

Moving parts (separate nodes in the glTF, see src/player/viewmodel_rig.gd):
  slide     bolt carrier + charging handle (travels back on each shot)
  magazine  drops on reload; children shell_hull and mag_tape are tinted per shell type
  stock     hidden while aiming
  optic     shown only while slugs are loaded

The pistol grip uses the Pistol 57 / MG42 grip frame and the foregrip is the
MG42's foregrip moved 50 mm forward and 8 mm down, so the arms builder's hand
poses carry over (raw_assets/characters/fp_arms_saiga/build.py).

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/saiga12k/build.py --out assets/weapons/saiga12k/saiga12k.gltf --tex 4096 \
      --preview docs/previews/saiga12k.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/saiga.png
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
ap.add_argument("--emission-size", type=int, default=512)
ap.add_argument("--preview", default="", help="preview sheet stem; renders <stem>_side/_beauty/_left/_receiver/_fp.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--no-optic", action="store_true", help="preview without the optic")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material

# ---------------------------------------------------------------- materials
# Milled black steel: dark, tight tool-mark streaks along X, edges worn to bright steel.
M_STEEL = mat("black_steel_milled", (0.03, 0.031, 0.034), 0.32, 0.85, wear=(0.5, 0.5, 0.52), wear_rough=0.2,
              brushed=0.045, bump_scale=1400, bump_strength=0.02)
M_OXIDE = mat("black_oxide", (0.018, 0.019, 0.021), 0.52, 0.7, wear=(0.36, 0.36, 0.38), wear_rough=0.25,
              brushed=0.02, bump_scale=900, bump_strength=0.05)
M_POLY = mat("black_polymer", (0.022, 0.022, 0.024), 0.62, 0.0, wear=(0.12, 0.12, 0.13), wear_rough=0.45,
             bump_scale=1600, bump_strength=0.14)
M_RUBBER = mat("rubber", (0.02, 0.02, 0.021), 0.85, 0.0, bump_scale=600, bump_strength=0.3)
M_BORE = mat("bore_dark", (0.012, 0.012, 0.014), 0.45, 1.0)
M_BRASS = mat("brass", (0.8, 0.6, 0.3), 0.24, 1.0, wear=(0.95, 0.8, 0.5), wear_rough=0.14)
M_ENAMEL = mat("optic_enamel", (0.016, 0.017, 0.018), 0.55, 0.2, wear=(0.3, 0.3, 0.31), wear_rough=0.3,
               bump_scale=2200, bump_strength=0.22)
M_LENS = mat("lens_coated", (0.006, 0.007, 0.012), 0.04, 0.0, emission=((0.32, 0.12, 0.55), 0.35))
M_GLASS = mat("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = mat("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_RED = mat("reticle_lamp", (0.8, 0.1, 0.05), 0.3, 0.0, emission=((1.0, 0.16, 0.06), 4.0))
M_MARK = mat("engraving", (0.3, 0.31, 0.32), 0.42, 1.0)
M_PAINT = mat("index_paint", (0.86, 0.84, 0.78), 0.6, 0.0)
MATERIALS = [M_STEEL, M_OXIDE, M_POLY, M_RUBBER, M_BORE, M_BRASS, M_ENAMEL, M_LENS, M_GLASS, M_AMBER, M_RED,
             M_MARK, M_PAINT]
# Tinted in game per shell type (not baked): the top shell's plastic hull and the tape band.
M_HULL = mat("shell_hull", (0.6, 0.05, 0.04), 0.45, 0.0)
M_TAPE = mat("mag_tape", (0.6, 0.05, 0.04), 0.7, 0.0)

# ---------------------------------------------------------------- dimensions
REC_X0, REC_X1 = -0.165, 0.150      # receiver
REC_HW = 0.0195                      # receiver half width (12-gauge AK receiver)
REC_Z0, REC_Z1 = -0.033, 0.024       # receiver bottom / top of the walls (the dust cover sits on top)
T = 0.003                            # milled wall thickness
SIGHT_Z = 0.046                      # iron sight line (rear notch = front post top)
OPTIC_Z = 0.074                      # optic axis
MAG_X0, MAG_X1 = 0.055, 0.135        # magazine well
MAG_R = 0.40                         # banana curve radius
MAG_LEN = 0.205                      # magazine length below the receiver along the curve
PORT_X0, PORT_X1, PORT_Z0, PORT_Z1 = 0.025, 0.120, -0.004, 0.019
CARRIER_TRAVEL = 0.075
MUZZLE_X = 0.625
PART_IDS = {"body": 0, "slide": 1, "magazine": 2, "stock": 3, "optic": 4}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m):
    ob = hs.text(name, body, size, loc, rot, m)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def plate(name, side, x0, x1, z0, z1, m=M_STEEL, inset=0.0, thick=T):
    """A receiver wall piece on the left (+1) or right (-1) side; `inset` pushes it inward (pocket floor)."""
    y_out = REC_HW - inset
    y0 = y_out - thick if side > 0 else -y_out
    return finish(hs.box(name, (x1 - x0, thick, z1 - z0), ((x0 + x1) / 2, y0 + thick / 2, (z0 + z1) / 2)), m,
                  bevel=0.0007)


def wall_with_hole(prefix, side, x0, x1, z0, z1, hx0, hx1, hz0, hz1, pocket=0.0):
    """Wall from (x0..x1, z0..z1) around a rectangular hole; with `pocket` > 0 the hole is a milled recess
    that deep instead of an opening."""
    plate(f"{prefix}_low", side, x0, x1, z0, hz0)
    plate(f"{prefix}_high", side, x0, x1, hz1, z1)
    plate(f"{prefix}_rear", side, x0, hx0, hz0, hz1)
    plate(f"{prefix}_front", side, hx1, x1, hz0, hz1)
    if pocket > 0:
        plate(f"{prefix}_pocket", side, hx0 - 0.0005, hx1 + 0.0005, hz0 - 0.0005, hz1 + 0.0005, inset=pocket,
              thick=0.0015)


# ---------------------------------------------------------------- receiver
def build_receiver():
    zw = REC_Z0 + 0.005
    # Dark core inside (behind the port and the well), so the openings read as depth.
    IN = REC_HW - T
    finish(hs.section("core_rear", [(-IN, REC_Z0 + 0.002), (IN, REC_Z0 + 0.002), (IN, -0.007), (-IN, -0.007)],
                      REC_X0 + 0.001, MAG_X0 - 0.002), M_BORE, bevel=0)
    finish(hs.section("core_front", [(-IN, REC_Z0 + 0.002), (IN, REC_Z0 + 0.002), (IN, REC_Z1 - 0.002),
                                     (-IN, REC_Z1 - 0.002)], PORT_X1 + 0.003, REC_X1 - 0.001), M_BORE, bevel=0)
    # Chamfered bottom rails either side of the magazine well.
    bottom = [(-0.015, REC_Z0), (0.015, REC_Z0), (REC_HW, zw), (-REC_HW, zw)]
    finish(hs.section("rec_bottom_rear", bottom, REC_X0, MAG_X0 - 0.002), M_STEEL, bevel=0.0009)
    finish(hs.section("rec_bottom_front", bottom, MAG_X1 + 0.002, REC_X1), M_STEEL, bevel=0.0009)
    # Magazine well lips.
    for sy in (-1, 1):
        finish(hs.box(f"well_lip{sy}", (MAG_X1 - MAG_X0 + 0.004, 0.003, 0.010),
                      ((MAG_X0 + MAG_X1) / 2, sy * (REC_HW - 0.0015), REC_Z0 + 0.003)), M_STEEL, bevel=0.0007)

    # Left wall: milled lightening pocket above the magazine well, and a smaller one at the rear.
    plate("wl_bottom", 1, REC_X0, REC_X1, zw, -0.027)
    wall_with_hole("wl_mid", 1, REC_X0, REC_X1, -0.027, REC_Z1, 0.050, 0.130, -0.022, -0.006, pocket=0.0018)
    finish(hs.box("wl_rear_pocket", (0.05, 0.0015, 0.012), (-0.120, REC_HW + 0.0002, -0.016)), M_STEEL, bevel=0.0005)
    # Right wall: ejection port (the carrier shows through it), pocket below it.
    plate("wr_bottom", -1, REC_X0, REC_X1, zw, -0.027)
    wall_with_hole("wr_lower", -1, REC_X0, REC_X1, -0.027, PORT_Z0, 0.050, 0.130, -0.022, -0.009, pocket=0.0018)
    plate("wr_port_rear", -1, REC_X0, PORT_X0, PORT_Z0, PORT_Z1)
    plate("wr_port_front", -1, PORT_X1, REC_X1, PORT_Z0, PORT_Z1)
    plate("wr_top", -1, REC_X0, REC_X1, PORT_Z1, REC_Z1)
    # Milled side rails the dust cover rides on.
    for sy in (-1, 1):
        finish(hs.box(f"cover_rail{sy}", (REC_X1 - REC_X0 - 0.03, 0.0022, 0.004),
                      ((REC_X0 + REC_X1) / 2 - 0.012, sy * (REC_HW + 0.0009), REC_Z1 - 0.0045)), M_STEEL, bevel=0.0006)
    # Trunnion rivet heads (milled receivers keep the pattern), left and right.
    for x, z in ((0.140, -0.016), (0.140, 0.006), (-0.150, -0.018), (-0.150, 0.004), (0.003, -0.026),
                 (0.032, -0.026), (-0.040, -0.026)):
        for sy in (-1, 1):
            if sy < 0 and PORT_X0 - 0.004 < x < PORT_X1 + 0.004 and z > PORT_Z0 - 0.004:
                continue
            r = hs.cyl_y(f"rivet_{x}_{z}_{sy}", 0.0022, 0.0018, (x, sy * (REC_HW + 0.0003), z), verts=16)
            finish(r, M_STEEL, bevel=0.0006, segments=2)

    # Dust cover: ribbed top, rear button of the recoil spring guide.
    cover = hs.section("dust_cover", [(-REC_HW - 0.0008, REC_Z1 - 0.003), (REC_HW + 0.0008, REC_Z1 - 0.003),
                                      (REC_HW + 0.0008, 0.031), (0.0145, 0.0385), (-0.0145, 0.0385),
                                      (-REC_HW - 0.0008, 0.031)], -0.160, 0.112)
    finish(cover, M_OXIDE, bevel=0.001)
    for i in range(3):
        rib = hs.box(f"cover_rib{i}", (0.006, 0.026, 0.0016), (-0.135 + i * 0.016, 0, 0.0389))
        finish(rib, M_OXIDE, bevel=0.0006)
    rib = hs.box("cover_long_rib", (0.150, 0.0035, 0.0012), (0.018, 0.0085, 0.0388))
    hs.mirror_y(rib)
    finish(rib, M_OXIDE, bevel=0.0004)
    finish(hs.box("spring_button", (0.008, 0.012, 0.010), (-0.164, 0, 0.030)), M_STEEL, bevel=0.0012)

    # Rear sight block on the front trunnion, tangent leaf, notch, slider.
    finish(hs.section("rs_block", [(-0.0175, REC_Z1 - 0.002), (0.0175, REC_Z1 - 0.002), (0.0175, 0.030),
                                   (0.011, 0.037), (-0.011, 0.037), (-0.0175, 0.030)], 0.112, 0.168),
           M_STEEL, bevel=0.0009)
    finish(hs.box("rs_leaf", (0.046, 0.013, 0.0022), (0.142, 0, 0.0388)), M_OXIDE, bevel=0.0004)
    notch = hs.box("rs_notch_block", (0.005, 0.014, SIGHT_Z - 0.037), (0.1215, 0, (SIGHT_Z + 0.037) / 2))
    hs.cut(notch, hs.box("rs_notch", (0.02, 0.0034, 0.008), (0.1215, 0, SIGHT_Z + 0.0005)))
    finish(notch, M_OXIDE, bevel=0.0004)
    finish(hs.box("rs_slider", (0.008, 0.017, 0.0045), (0.150, 0, 0.0405)), M_STEEL, bevel=0.0006)
    finish(hs.box("rs_dot", (0.0008, 0.0016, 0.0016), (0.1188, 0, SIGHT_Z - 0.0052)), M_AMBER, bevel=0)
    for i in range(5):
        finish(hs.box(f"rs_tick{i}", (0.0007, 0.0004, 0.0009), (0.128 + i * 0.006, 0.0066, 0.0399)), M_PAINT, bevel=0)

    # Front trunnion collar into the barrel.
    finish(hs.lathe_x("trunnion", [(REC_X1 - 0.002, 0.0175), (REC_X1 + 0.003, 0.0185), (0.172, 0.0185),
                                   (0.176, 0.0150)], verts=48), M_STEEL, bevel=0.0006)
    # Rear trunnion / stock hinge block, hinge knuckle on the right (the stock folds to the right).
    finish(hs.section("rear_trunnion", [(-0.0185, REC_Z0 + 0.001), (0.0185, REC_Z0 + 0.001), (0.0195, 0.0),
                                        (0.0185, 0.030), (-0.0185, 0.030), (-0.0195, 0.0)], REC_X0 - 0.020, REC_X0 + 0.001),
           M_STEEL, bevel=0.0012)
    finish(hs.cyl_z("hinge_knuckle", 0.0055, 0.040, (REC_X0 - 0.012, -0.0205, -0.004), verts=24), M_STEEL, bevel=0.0008)
    finish(hs.cyl_y("stock_button", 0.0048, 0.006, (REC_X0 - 0.010, 0.0215, 0.012), verts=20), M_OXIDE, bevel=0.0008)

    # Selector lever (right side): long flat plate with the finger tab at the front.
    sel = hs.prism("selector", [(-0.128, -REC_HW - 0.0007, 0.0105), (-0.030, -REC_HW - 0.0007, 0.0075),
                                (0.030, -REC_HW - 0.0007, 0.0060), (0.040, -REC_HW - 0.0007, 0.0035),
                                (0.041, -REC_HW - 0.0007, -0.0085), (0.033, -REC_HW - 0.0007, -0.0090),
                                (0.030, -REC_HW - 0.0007, 0.0005), (-0.030, -REC_HW - 0.0007, 0.0015),
                                (-0.128, -REC_HW - 0.0007, 0.0035)], (0, -0.0022, 0))
    finish(sel, M_STEEL, bevel=0.0005)
    finish(hs.cyl_y("selector_pivot", 0.0048, 0.0035, (-0.124, -REC_HW - 0.0018, 0.007), verts=24), M_STEEL,
           bevel=0.0006)
    # Paddle magazine release behind the well.
    finish(hs.side_profile("mag_release", [(0.046, REC_Z0 + 0.001), (0.052, REC_Z0 + 0.001), (0.050, -0.050),
                                           (0.044, -0.054), (0.041, -0.050)], 0.012), M_STEEL, bevel=0.0006)

    # Warsaw-pact side rail (left) for the optic bracket.
    rail = hs.section("side_rail", [(REC_HW - 0.0005, -0.005), (REC_HW + 0.0022, -0.005), (REC_HW + 0.0042, -0.002),
                                    (REC_HW + 0.0042, 0.011), (REC_HW + 0.0022, 0.014), (REC_HW - 0.0005, 0.014)],
                      -0.095, 0.045)
    finish(rail, M_STEEL, bevel=0.0005)
    for i, x in enumerate((-0.082, -0.035, 0.030)):
        finish(hs.cyl_y(f"rail_rivet{i}", 0.0024, 0.0012, (x, REC_HW + 0.0045, 0.0045), verts=16), M_STEEL,
               bevel=0.0004)

    # Fire-Control Link readout (left rear) and markings.
    finish(hs.box("fcl_glass", (0.030, 0.0014, 0.010), (-0.128, REC_HW + 0.0005, -0.0030)), M_GLASS, bevel=0.0004)
    for i, w in enumerate((0.005, 0.007, 0.003, 0.006)):
        finish(hs.box(f"fcl_seg{i}", (w, 0.0004, 0.0013), (-0.140 + i * 0.0062 + w / 2, REC_HW + 0.0013, -0.0005)),
               M_AMBER, bevel=0)
    finish(hs.box("fcl_bar", (0.020, 0.0004, 0.0008), (-0.130, REC_HW + 0.0013, -0.0055)), M_AMBER, bevel=0)
    text("mark_left", "SAIGA-12K   12/76", 0.0050, (0.128, REC_HW + 0.0001, 0.0040), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_serial", "GRF 1207", 0.0040, (-0.100, REC_HW + 0.0001, 0.0150), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_right", "AB  OD", 0.0045, (-0.004, -REC_HW - 0.0001, -0.0080), (math.pi / 2, 0, 0), M_MARK)


def build_carrier():
    """Bolt carrier (seen through the port) and the charging handle: the moving `slide` part."""
    part("slide")
    finish(hs.box("carrier", (0.150, 2 * (REC_HW - T) - 0.001, PORT_Z1 - PORT_Z0 + 0.004),
                  (0.050, 0, (PORT_Z0 + PORT_Z1) / 2)), M_STEEL, bevel=0.001)
    finish(hs.box("carrier_cut", (0.040, 0.0012, 0.008), (0.072, -REC_HW + T - 0.0002, 0.0075)), M_BORE, bevel=0)
    finish(hs.cyl_x("bolt_face", 0.0105, 0.124, 0.128, verts=32), M_BORE, bevel=0.0004)
    hx = PORT_X1 - 0.008
    finish(hs.box("ch_stem", (0.009, 0.020, 0.006), (hx, -REC_HW - 0.007, 0.0085)), M_STEEL, bevel=0.0007)
    finish(hs.cyl_y("ch_knob", 0.0058, 0.012, (hx + 0.001, -REC_HW - 0.021, 0.0085), verts=24), M_STEEL, bevel=0.0014)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=hs.nverts(24), ring_count=12, radius=0.0062,
                                         location=(hx + 0.001, -REC_HW - 0.0275, 0.0085))
    ball = bpy.context.active_object
    ball.name = "ch_ball"
    finish(ball, M_STEEL, bevel=0)
    part("body")


# ---------------------------------------------------------------- barrel, gas system, handguards, sights
def build_barrel():
    finish(hs.cyl_x("barrel", 0.0115, 0.170, 0.565, verts=40), M_STEEL, bevel=0.0004)
    # Gas tube and gas block with the two-position regulator.
    finish(hs.cyl_x("gas_tube", 0.0092, 0.170, 0.345, verts=32, z=0.0255), M_OXIDE, bevel=0.0004)
    gb = hs.section("gas_block", [(-0.0145, -0.012), (0.0145, -0.012), (0.0145, 0.026), (0.010, 0.0365),
                                  (-0.010, 0.0365), (-0.0145, 0.026)], 0.335, 0.378)
    finish(gb, M_STEEL, bevel=0.0012)
    finish(hs.cyl_x("gas_plug", 0.0075, 0.378, 0.392, verts=32, z=0.0255), M_STEEL, bevel=0.0008)
    finish(hs.box("regulator", (0.006, 0.018, 0.010), (0.389, 0.010, 0.0255)), M_OXIDE, bevel=0.0008)
    finish(hs.cyl_y("regulator_pin", 0.0026, 0.036, (0.357, 0, -0.004), verts=16), M_STEEL, bevel=0.0004)

    # Lower handguard: milled steel with vent slots, Picatinny strip underneath.
    lhg = hs.section("lower_handguard", [(-0.0215, -0.026), (-0.0175, -0.031), (0.0175, -0.031), (0.0215, -0.026),
                                         (0.0235, 0.002), (0.0215, 0.012), (-0.0215, 0.012), (-0.0235, 0.002)],
                     0.178, 0.330)
    hs.cut(lhg, hs.cyl_x("lhg_bore", 0.0165, 0.17, 0.34, verts=32))
    for i in range(5):
        x = 0.196 + i * 0.026
        s = hs.box(f"lhg_slot{i}", (0.016, 0.06, 0.0075), (x, 0, -0.008))
        hs.cut(lhg, s)
    finish(lhg, M_STEEL, bevel=0.0008)
    # Upper handguard over the gas tube.
    uhg = hs.section("upper_handguard", [(-0.0165, 0.012), (0.0165, 0.012), (0.0175, 0.030), (0.010, 0.0395),
                                         (-0.010, 0.0395), (-0.0175, 0.030)], 0.180, 0.330)
    hs.cut(uhg, hs.cyl_x("uhg_bore", 0.0108, 0.17, 0.34, verts=32, z=0.0255))
    for i in range(4):
        hs.cut(uhg, hs.box(f"uhg_slot{i}", (0.020, 0.010, 0.02), (0.205 + i * 0.033, 0, 0.040)))
    finish(uhg, M_STEEL, bevel=0.0008)
    # Retainer band at the rear, front cap.
    finish(hs.section("hg_retainer", [(-0.0245, -0.032), (0.0245, -0.032), (0.0255, 0.004), (0.022, 0.014),
                                      (-0.022, 0.014), (-0.0255, 0.004)], 0.170, 0.180), M_OXIDE, bevel=0.0009)
    finish(hs.box("retainer_lever", (0.006, 0.004, 0.022), (0.175, -0.0265, -0.006)), M_OXIDE, bevel=0.0006)
    finish(hs.section("hg_cap", [(-0.0225, -0.0315), (0.0225, -0.0315), (0.0235, 0.010), (-0.0235, 0.010)],
                      0.330, 0.336), M_OXIDE, bevel=0.0008)
    rail = hs.box("pic_rail", (0.110, 0.0156, 0.0055), (0.262, 0, -0.0335))
    for i in range(10):
        hs.cut(rail, hs.box(f"pic_slot{i}", (0.0052, 0.03, 0.004), (0.214 + i * 0.0106, 0, -0.0365)))
    finish(rail, M_STEEL, bevel=0.0005)

    # Front sight block: collar, tower, hood, post.
    finish(hs.lathe_x("fs_collar", [(0.520, 0.0132), (0.521, 0.0148), (0.544, 0.0148), (0.545, 0.0132)], verts=40),
           M_STEEL, bevel=0.0005)
    finish(hs.side_profile("fs_tower", [(0.523, 0.010), (0.542, 0.010), (0.540, 0.032), (0.526, 0.032)], 0.012),
           M_STEEL, bevel=0.0008)
    hood = hs.cyl_x("fs_hood", 0.0118, 0.526, 0.540, verts=32, z=SIGHT_Z - 0.004)
    hs.cut(hood, hs.cyl_x("fs_hood_in", 0.0100, 0.52, 0.55, verts=32, z=SIGHT_Z - 0.004))
    hs.cut(hood, hs.box("fs_hood_slot", (0.004, 0.006, 0.02), (0.533, 0, SIGHT_Z + 0.008)))
    finish(hood, M_STEEL, bevel=0.0004)
    finish(hs.box("fs_post", (0.0032, 0.0022, SIGHT_Z - 0.032), (0.533, 0, (SIGHT_Z + 0.032) / 2)), M_OXIDE,
           bevel=0.0003)
    finish(hs.box("fs_dot", (0.0008, 0.0016, 0.0016), (0.5312, 0, SIGHT_Z - 0.0012)), M_AMBER, bevel=0)

    # Slotted muzzle brake.
    brake = hs.lathe_x("brake", [(0.556, 0.0135), (0.560, 0.0158), (0.618, 0.0158), (MUZZLE_X, 0.0145)], verts=40)
    hs.cut(brake, hs.cyl_x("brake_bore", 0.0094, 0.55, 0.63, verts=32))
    for i in range(3):
        slot = hs.box(f"brake_slot{i}", (0.010, 0.05, 0.0105), (0.570 + i * 0.016, 0, 0.0))
        hs.cut(brake, slot)
    hs.cut(brake, hs.box("brake_top_port", (0.030, 0.006, 0.02), (0.592, 0, 0.0158)))
    finish(brake, M_OXIDE, bevel=0.0006)
    finish(hs.cyl_x("muzzle_dark", 0.0092, 0.553, 0.560, verts=32), M_BORE, bevel=0)


def build_foregrip():
    """The MG42's clamp-on vertical foregrip, moved +50 mm in X and -8 mm in Z (arms fit unchanged)."""
    dx, dz = 0.050, -0.008
    finish(hs.box("fg_block", (0.026, 0.022, 0.010), (0.202 + dx, 0, -0.033 + dz)), M_STEEL, bevel=0.0012)
    finish(hs.cyl_y("fg_bolt", 0.003, 0.028, (0.202 + dx, 0, -0.033 + dz), verts=16), M_STEEL, bevel=0.0004)
    finish(hs.cyl_y("fg_nut", 0.0055, 0.004, (0.202 + dx, -0.0145, -0.033 + dz), verts=6), M_STEEL, bevel=0.0004)
    grip = hs.cyl_between("fg_grip", (0.203 + dx, 0, -0.036 + dz), (0.211 + dx, 0, -0.130 + dz), 0.0165, verts=32)
    for i in range(4):
        z = -0.056 - i * 0.021
        bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(32), minor_segments=8, major_radius=0.0172,
                                         minor_radius=0.0021,
                                         location=(0.203 + dx + (z + 0.036) / -0.094 * 0.008, 0, z + dz))
        hs.cut(grip, bpy.context.active_object)
    finish(grip, M_POLY, bevel=0.0012)
    finish(hs.cyl_between("fg_cap", (0.211 + dx, 0, -0.128 + dz), (0.2117 + dx, 0, -0.136 + dz), 0.0176, verts=32),
           M_STEEL, bevel=0.0015)


# ---------------------------------------------------------------- grip, trigger, stock
def build_lower():
    # AK-style polymer pistol grip on the Pistol 57 grip frame (front strap / back strap lines match it).
    grip = hs.side_profile("grip", [(-0.017, REC_Z0 + 0.001), (-0.026, -0.051), (-0.056, -0.134), (-0.061, -0.138),
                                    (-0.103, -0.138), (-0.107, -0.132), (-0.081, -0.046), (-0.087, REC_Z0 + 0.001)],
                           0.030)
    ang = math.atan2(0.029, 0.080)  # grip rake
    for sy in (-1, 1):
        for i in range(4):
            g = hs.box(f"grip_rib{sy}_{i}", (0.0026, 0.004, 0.072), (0, 0, 0))
            g.rotation_euler = (0, ang, 0)
            g.location = (-0.078 + i * 0.0095 - 0.003, sy * 0.0153, -0.094)
            bpy.context.view_layer.update()
            hs.cut(grip, g)
    finish(grip, M_POLY, bevel=0.0012)
    finish(hs.side_profile("grip_cap", [(-0.058, -0.137), (-0.105, -0.137), (-0.108, -0.1445), (-0.055, -0.1445)],
                           0.027), M_STEEL, bevel=0.0008)
    finish(hs.cyl_y("grip_screw", 0.0028, 0.031, (-0.081, 0, -0.141), verts=16), M_STEEL, bevel=0.0004)
    # Stamped trigger guard loop.
    guard = hs.side_profile("trigger_guard", [(-0.021, REC_Z0 + 0.001), (-0.020, -0.054), (-0.013, -0.0585),
                                              (0.034, -0.0585), (0.042, -0.051), (0.044, REC_Z0 + 0.001)], 0.010)
    hs.cut(guard, hs.side_profile("guard_hole", [(-0.015, -0.0345), (0.038, -0.0345), (0.038, -0.050),
                                                 (0.032, -0.0545), (-0.010, -0.0545), (-0.015, -0.049)], 0.05))
    finish(guard, M_STEEL, bevel=0.0007)
    finish(hs.side_profile("trigger", [(0.012, -0.033), (0.018, -0.033), (0.016, -0.041), (0.021, -0.051),
                                       (0.015, -0.053), (0.008, -0.041)], 0.0055), M_STEEL, bevel=0.0005)
    finish(hs.cyl_y("trigger_pin", 0.0022, 0.040, (0.014, 0, -0.026), verts=16), M_STEEL, bevel=0.0004)

    # Side-folding skeleton stock (its own part: the viewmodel hides it while aiming).
    part("stock")
    x0 = REC_X0 - 0.020
    finish(hs.section("stock_block", [(-0.016, -0.034), (0.016, -0.034), (0.017, 0.022), (-0.017, 0.022)],
                      x0 - 0.028, x0), M_STEEL, bevel=0.0015)
    finish(hs.cyl_between("stock_top", (x0 - 0.026, 0, 0.012), (-0.505, 0, -0.012), 0.0085, verts=24), M_OXIDE,
           bevel=0.0006)
    finish(hs.cyl_between("stock_low", (x0 - 0.026, 0, -0.026), (-0.505, 0, -0.104), 0.0078, verts=24), M_OXIDE,
           bevel=0.0006)
    finish(hs.cyl_between("stock_brace", (-0.300, 0, 0.000), (-0.390, 0, -0.080), 0.0055, verts=16), M_OXIDE, bevel=0.0004)
    # Polymer cheek sleeve on the top tube.
    finish(hs.cyl_between("cheek_sleeve", (-0.300, 0, 0.004), (-0.440, 0, -0.008), 0.0128, verts=32), M_POLY,
           bevel=0.0012)
    for i in range(5):
        finish(hs.cyl_between(f"cheek_ring{i}", (-0.312 - i * 0.026, 0, 0.0031 - i * 0.0022),
                              (-0.316 - i * 0.026, 0, 0.0028 - i * 0.0022), 0.0134, verts=32), M_POLY, bevel=0)
    # Butt plate and rubber pad.
    finish(hs.loft_x("butt_plate", [(-0.512, 0.004, -0.122, 0.0185), (-0.500, 0.004, -0.122, 0.0185)]), M_STEEL,
           bevel=0.0012, segments=2, angle=60)
    finish(hs.loft_x("butt_pad", [(-0.530, 0.002, -0.120, 0.0172), (-0.5115, 0.004, -0.122, 0.0182)]), M_RUBBER,
           bevel=0.0015, segments=2, angle=60)
    finish(hs.cyl_y("sling_loop", 0.0055, 0.006, (-0.49, 0, -0.112), verts=20), M_STEEL, bevel=0.0008)
    part("body")


# ---------------------------------------------------------------- magazine
def mag_frame(s):
    """Point and axes along the magazine centreline, `s` metres below the receiver's bottom (may be < 0)."""
    phi = s / MAG_R
    cx, cz = (MAG_X0 + MAG_X1) / 2 + MAG_R, REC_Z0
    p = V((cx - MAG_R * math.cos(phi), 0.0, cz - MAG_R * math.sin(phi)))
    depth = V((math.cos(phi), 0.0, math.sin(phi)))   # toward the front of the magazine
    return p, depth


def build_magazine():
    part("magazine")
    half_d, half_w = (MAG_X1 - MAG_X0) / 2 - 0.001, 0.0172
    stations = []
    for i in range(13):
        s = -0.010 + (MAG_LEN + 0.010) * i / 12
        p, d = mag_frame(s)
        stations.append((p, (0, 1, 0), d, half_w, half_d))
    body = hs.loft("mag_body", stations, power=7.0)
    finish(body, M_POLY, bevel=0.0012, angle=50)
    # Raised side panels with ribs, the front spine and the rear catch lug.
    for sy in (-1, 1):
        panel = []
        for i in range(9):
            s = 0.030 + (MAG_LEN - 0.060) * i / 8
            p, d = mag_frame(s)
            panel.append((p + V((0, sy * (half_w + 0.0006), 0)), (0, 1, 0), d, 0.0012, half_d * 0.68))
        finish(hs.loft(f"mag_panel{sy}", panel, power=6.0), M_POLY, bevel=0.0005, angle=50)
        for k in range(5):
            s = 0.044 + k * 0.026
            p, d = mag_frame(s)
            up = V((-d.z, 0, d.x))
            rib = hs.cyl_between(f"mag_rib{sy}_{k}", p + d * (-half_d * 0.6) + V((0, sy * (half_w + 0.0016), 0)),
                                 p + d * (half_d * 0.6) + V((0, sy * (half_w + 0.0016), 0)), 0.0011, verts=8)
            del up
            finish(rib, M_POLY, bevel=0)
    spine = []
    for i in range(9):
        s = 0.004 + (MAG_LEN - 0.012) * i / 8
        p, d = mag_frame(s)
        spine.append((p + d * (half_d + 0.0008), (0, 1, 0), d, 0.0075, 0.0014))
    finish(hs.loft("mag_spine", spine, power=4.0), M_POLY, bevel=0.0004, angle=50)
    p, d = mag_frame(0.006)
    lug = hs.box("mag_catch_lug", (0.006, 0.014, 0.012), (0, 0, 0))
    lug.location = p - d * (half_d + 0.002)
    finish(lug, M_STEEL, bevel=0.0006)
    p, d = mag_frame(-0.004)
    flug = hs.box("mag_front_lug", (0.006, 0.010, 0.006), (0, 0, 0))
    flug.location = p + d * (half_d + 0.002)
    finish(flug, M_STEEL, bevel=0.0006)
    # Floor plate.
    fp = []
    for s in (MAG_LEN - 0.001, MAG_LEN + 0.007):
        p, d = mag_frame(s)
        fp.append((p, (0, 1, 0), d, half_w + 0.0016, half_d + 0.003))
    finish(hs.loft("mag_floor", fp, power=7.0), M_POLY, bevel=0.0012, angle=50)
    p, d = mag_frame(MAG_LEN + 0.0075)
    finish(hs.cyl_z("floor_button", 0.0035, 0.0015, (p.x - 0.020, 0, p.z - 0.0005), verts=16), M_STEEL, bevel=0.0003)
    # Brass head of the top shell (its plastic hull is added after the bake, tinted in game).
    head = hs.lathe_x("top_shell_head", [(MAG_X0 + 0.004, 0.0108), (MAG_X0 + 0.0055, 0.0112), (MAG_X0 + 0.0065, 0.0112),
                                         (MAG_X0 + 0.0075, 0.0104), (MAG_X0 + 0.018, 0.0104)], verts=32)
    head.location = (0, 0.0035, REC_Z0 + 0.0005)
    finish(head, M_BRASS, bevel=0)
    finish(hs.cyl_x("top_shell_primer", 0.0028, MAG_X0 + 0.0035, MAG_X0 + 0.0042, verts=16, y=0.0035,
                    z=REC_Z0 + 0.0005), M_BRASS, bevel=0)
    text("mag_mark", "12 x 10", 0.006, (mag_frame(0.150)[0].x + 0.02, half_w + 0.0019, mag_frame(0.150)[0].z),
         (math.pi / 2, 0, math.pi), M_MARK)
    part("body")


def build_tinted_parts():
    """Shell hull and tape band: plain materials (not baked) the game tints per shell type."""
    hull = hs.lathe_x("shell_hull", [(MAG_X0 + 0.0178, 0.0101), (MAG_X1 - 0.006, 0.0101), (MAG_X1 - 0.004, 0.0096),
                                     (MAG_X1 - 0.003, 0.0060), (MAG_X1 - 0.0029, 0.0)], verts=24)
    hull.location = (0, 0.0035, REC_Z0 + 0.0005)
    hull.data.materials.append(M_HULL)
    hull.data.shade_smooth()
    half_d, half_w = (MAG_X1 - MAG_X0) / 2 - 0.001, 0.0172
    band = []
    for s in (0.150, 0.150 + 0.026):
        p, d = mag_frame(s)
        band.append((p, (0, 1, 0), d, half_w + 0.0026, half_d + 0.0012))
    tape = hs.loft("mag_tape", band, n=40, power=7.0, cap=False)
    sol = tape.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.0006
    bpy.ops.object.select_all(action="DESELECT")
    tape.select_set(True)
    bpy.context.view_layer.objects.active = tape
    bpy.ops.object.modifier_apply(modifier="solid")
    tape.data.materials.append(M_TAPE)
    tape.data.shade_smooth()
    return [hull, tape]


# ---------------------------------------------------------------- optic
def build_optic():
    """PSO-1-pattern scope (1x) on its side bracket."""
    part("optic")
    z = OPTIC_Z
    # Bracket: clamp block on the side rail, web up the left side, saddle, two rings.
    yl = REC_HW + 0.0045
    finish(hs.box("br_clamp", (0.112, 0.0105, 0.024), (-0.025, yl + 0.0052, 0.0045)), M_ENAMEL, bevel=0.0012)
    web = hs.prism("br_web", [(-0.075, yl + 0.0025, 0.016), (0.030, yl + 0.0025, 0.016), (0.056, yl + 0.0025, z - 0.014),
                              (-0.066, yl + 0.0025, z - 0.014)], (0, 0.007, 0))
    hs.cut(web, hs.box("br_web_window", (0.062, 0.03, 0.017), (-0.016, yl + 0.006, 0.0395)))
    finish(web, M_ENAMEL, bevel=0.0012)
    finish(hs.box("br_web_floor", (0.064, 0.0016, 0.019), (-0.016, yl + 0.0034, 0.0395)), M_ENAMEL, bevel=0.0004)
    finish(hs.box("br_saddle", (0.122, yl + 0.012, 0.007), (-0.005, (yl + 0.0095) / 2 - 0.006, z - 0.0165)),
           M_ENAMEL, bevel=0.0012)
    for i, x in enumerate((-0.060, 0.048)):
        ring = hs.lathe_x(f"br_ring{i}", [(x - 0.007, 0.0130), (x - 0.0065, 0.0162), (x + 0.0065, 0.0162),
                                          (x + 0.007, 0.0130)], verts=48)
        ring.location = (0, 0, z)
        finish(ring, M_ENAMEL, bevel=0.0006)
        finish(hs.box(f"br_ring_foot{i}", (0.014, 0.020, 0.008), (x, 0, z - 0.0145)), M_ENAMEL, bevel=0.0008)
        finish(hs.cyl_z(f"br_ring_screw{i}", 0.0024, 0.003, (x, 0.0, z + 0.0170), verts=12), M_STEEL, bevel=0.0003)
    # Clamp lever along the outside of the bracket, and the tension knob.
    finish(hs.box("br_lever", (0.080, 0.003, 0.006), (-0.034, yl + 0.0122, 0.0045)), M_STEEL, bevel=0.0008)
    finish(hs.cyl_y("br_lever_knob", 0.0052, 0.008, (-0.074, yl + 0.0145, 0.0045), verts=24), M_STEEL, bevel=0.0012)
    finish(hs.cyl_y("br_tension", 0.0068, 0.006, (0.020, yl + 0.0135, 0.0045), verts=24), M_ENAMEL, bevel=0.0012)
    for k in range(10):
        a = 2 * math.pi * k / 10
        finish(hs.box(f"br_tension_flute{k}", (0.0016, 0.0058, 0.0016),
                      (0.020 + math.cos(a) * 0.0068, yl + 0.0135, 0.0045 + math.sin(a) * 0.0068),
                      (0, -a, 0)), M_ENAMEL, bevel=0)

    def scope_lathe(name, profile, m, verts=48, bevel=0.0006):
        ob = hs.lathe_x(name, profile, verts=verts)
        ob.location = (0, 0, z)
        return finish(ob, m, bevel=bevel)

    # Rubber eyecup (long PSO eyecup), ocular bell, tube, objective bell, sunshade.
    cup = hs.lathe_x("eyecup", [(-0.170, 0.0175), (-0.169, 0.0205), (-0.166, 0.0215), (-0.152, 0.0208),
                                (-0.142, 0.0192), (-0.134, 0.0178)], verts=48)
    cup.location = (0, 0, z)
    hs.cut(cup, hs.cyl_x("eyecup_hole", 0.0148, -0.175, -0.137, verts=48, z=z))
    finish(cup, M_RUBBER, bevel=0.0008)
    for k in range(3):
        scope_lathe(f"eyecup_ridge{k}", [(-0.1615 + k * 0.007, 0.0208), (-0.1605 + k * 0.007, 0.0216),
                                         (-0.1585 + k * 0.007, 0.0216), (-0.1575 + k * 0.007, 0.0206)], M_RUBBER, bevel=0)
    scope_lathe("ocular_lens", [(-0.1385, 0.0), (-0.1385, 0.0149), (-0.1375, 0.0149), (-0.1375, 0.0)], M_LENS, bevel=0)
    scope_lathe("ocular_bell", [(-0.137, 0.0176), (-0.133, 0.0182), (-0.112, 0.0182), (-0.106, 0.0160),
                                (-0.098, 0.0134)], M_ENAMEL)
    for k in range(14):
        scope_lathe(f"focus_knurl{k}", [(-0.131 + k * 0.0012, 0.0182), (-0.1306 + k * 0.0012, 0.0186),
                                        (-0.1302 + k * 0.0012, 0.0182)], M_ENAMEL, verts=48, bevel=0)
    finish(hs.cyl_x("tube", 0.0130, -0.100, 0.084, verts=48, z=z), M_ENAMEL, bevel=0.0004)
    scope_lathe("objective_bell", [(0.082, 0.0131), (0.090, 0.0140), (0.100, 0.0168), (0.106, 0.0174)], M_ENAMEL)
    shade = hs.lathe_x("sunshade", [(0.104, 0.0168), (0.105, 0.0176), (0.143, 0.0176), (0.144, 0.0168)], verts=48)
    shade.location = (0, 0, z)
    hs.cut(shade, hs.cyl_x("sunshade_bore", 0.0157, 0.106, 0.150, verts=48, z=z))
    finish(shade, M_ENAMEL, bevel=0.0005)
    scope_lathe("objective_lens", [(0.1065, 0.0), (0.1065, 0.0158), (0.1075, 0.0158), (0.1075, 0.0)], M_LENS, bevel=0)

    # Turret housing with the big elevation drum on top and the windage drum on the left.
    finish(hs.loft_x("turret_saddle", [(-0.024, z + 0.0125, z - 0.0115, 0.0150), (-0.020, z + 0.0158, z - 0.0128, 0.0162),
                                       (0.020, z + 0.0158, z - 0.0128, 0.0162), (0.024, z + 0.0125, z - 0.0115, 0.0150)],
                       power=4.0), M_ENAMEL, bevel=0.0008)

    def drum(name, centre, axis, r, h):
        if axis == "z":
            d = hs.cyl_z(name, r, h, centre, verts=48)
        else:
            d = hs.cyl_y(name, r, h, centre, verts=48)
        finish(d, M_ENAMEL, bevel=0.0010)
        for k in range(24):
            a = 2 * math.pi * k / 24
            if axis == "z":
                loc = (centre[0] + math.cos(a) * r, centre[1] + math.sin(a) * r, centre[2] - h * 0.12)
                ridge = hs.box(f"{name}_ridge{k}", (0.0014, 0.0014, h * 0.62), loc, (0, 0, a))
            else:
                loc = (centre[0] + math.cos(a) * r, centre[1] + h * 0.12, centre[2] + math.sin(a) * r)
                ridge = hs.box(f"{name}_ridge{k}", (0.0014, h * 0.62, 0.0014), loc, (0, -a, 0))
            finish(ridge, M_ENAMEL, bevel=0)

    drum("elev_drum", (0.0, 0.0, z + 0.0158 + 0.009), "z", 0.0142, 0.018)
    finish(hs.cyl_z("elev_cap", 0.0108, 0.003, (0.0, 0.0, z + 0.0158 + 0.0195), verts=40), M_ENAMEL, bevel=0.0008)
    finish(hs.box("elev_index", (0.003, 0.0008, 0.0006), (-0.0158, 0.0, z + 0.0160)), M_PAINT, bevel=0)
    for k, a in enumerate((-60, -30, 0, 30, 60)):
        r = math.radians(180 + a)
        finish(hs.box(f"elev_mark{k}", (0.0006, 0.0006, 0.003 if a else 0.005),
                      (math.cos(r) * 0.01435, math.sin(r) * 0.01435, z + 0.0158 + 0.0148), (0, 0, r)),
               M_PAINT, bevel=0)
    drum("wind_drum", (0.0, 0.0162 + 0.0065, z), "y", 0.0102, 0.013)
    finish(hs.cyl_y("wind_cap", 0.0078, 0.003, (0.0, 0.0162 + 0.0145, z), verts=40), M_ENAMEL, bevel=0.0008)
    finish(hs.box("wind_index", (0.0008, 0.004, 0.0012), (0.0, 0.0175, z + 0.0108)), M_PAINT, bevel=0)
    # Illumination: battery housing at the left rear of the saddle, lamp switch, red lamp window.
    finish(hs.cyl_y("lamp_housing", 0.0062, 0.010, (-0.036, 0.0165, z - 0.004), verts=32), M_ENAMEL, bevel=0.0008)
    finish(hs.cyl_y("lamp_cap", 0.0068, 0.003, (-0.036, 0.0225, z - 0.004), verts=32), M_ENAMEL, bevel=0.0008)
    finish(hs.box("lamp_switch", (0.0025, 0.004, 0.006), (-0.036, 0.0170, z + 0.0035), (0.0, 0.3, 0.0)), M_STEEL,
           bevel=0.0005)
    finish(hs.cyl_y("lamp_window", 0.0022, 0.0010, (-0.036, 0.0242, z - 0.004), verts=16), M_RED, bevel=0)
    # Markings on the left of the tube.
    text("optic_mark", "PSO-1X   1P-G", 0.0040, (0.074, 0.01325, z - 0.0020), (math.pi / 2, 0, math.pi), M_MARK)
    text("optic_serial", "No 7412", 0.0032, (-0.050, 0.01325, z - 0.0030), (math.pi / 2, 0, math.pi), M_MARK)
    part("body")


# ---------------------------------------------------------------- build
def build(detail, name, optic=True):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_receiver()
    build_carrier()
    build_barrel()
    build_foregrip()
    build_lower()
    build_magazine()
    if optic:
        build_optic()
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
    print(f"saiga12k {detail['name']}: {bakeutil.tri_count(joined)} tris")
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
        print(f"saiga12k: part {pname}: {bakeutil.tri_count(ob)} tris")
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

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.0, 0, -0.03), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.4, -1.2, 1.1), 50, 1.6, sy=0.5)
    area("strip_top", (0.05, 0.0, 1.1), 34, 2.2, sy=0.18)
    area("fill", (0.4, 1.3, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.4, -0.4, 0.5), 50, 0.8, (1.0, 0.82, 0.62))
    area("kick", (-1.4, 0.3, 0.2), 28, 1.0, (0.9, 0.95, 1.0))
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
    print(f"saiga12k: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shoot(cam, stem + "_side.png", (0.03, -2.2, -0.03), (0.03, 0, -0.06), lens=55)
    shoot(cam, stem + "_beauty.png", (0.62, -0.92, 0.40), (0.06, 0, -0.04), lens=50, fstop=8.0)
    shoot(cam, stem + "_left.png", (-0.20, 1.0, 0.36), (0.08, 0, -0.03), lens=45, fstop=8.0)
    shoot(cam, stem + "_receiver.png", (0.12, -0.36, 0.20), (0.0, 0.0, 0.01), lens=50, fstop=4.0)
    shoot(cam, stem + "_optic.png", (-0.06, 0.30, 0.17), (0.0, 0.0, 0.05), lens=50, fstop=4.0)
    # Roughly the player's hip view: eye behind/above the receiver, gun to the lower right.
    shoot(cam, stem + "_fp.png", (-0.34, 0.11, 0.13), (0.6, -0.03, -0.04), fov_deg=60)


# ---------------------------------------------------------------- run
if args.out:
    high = build(hs.HIGH, "saiga_high")
    low = build(hs.LOW, "saiga_low")
    bakeutil.unwrap(low, boost={M_STEEL.name: 1.1, M_OXIDE.name: 1.1, M_ENAMEL.name: 1.15, M_BRASS.name: 1.4,
                                M_MARK.name: 1.5, M_PAINT.name: 1.5, M_POLY.name: 0.85, M_RUBBER.name: 0.8})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "saiga12k", cage=0.0012, ray=0.004,
                                 ao_distance=0.03, grime=0.35, log=print)
    bpy.data.objects.remove(high)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "saiga12k", emission_strength=4.0)
    objs = split_parts(low)
    for ob in build_tinted_parts():
        ob.parent = objs["magazine"]
        objs[ob.name] = ob
    export(list(objs.values()), args.out)
    print(f"saiga12k: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "saiga_high", optic=not args.no_optic)
    build_tinted_parts()
    render_previews(args.preview.rsplit(".", 1)[0])
