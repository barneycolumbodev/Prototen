"""M14/P battle rifle: an M14 action in a black polymer stock, suppressed, stubby foregrip.

Owner brief (2026-11-02): "a black polymer M14 style battle rifle, with a
suppressor and stubby foregrip".

Design reading: the M14A1 (M14E2) had a straight-line stock with a pistol
grip and a forward grip, so this is an M14 action in a one-piece black
polymer stock with a pistol grip, a stubby vertical grip on a short rail
under the fore-end, and a can in place of the flash suppressor. M14 parts
kept: open-top receiver with the rotating bolt visible, op rod and its
charging handle on the right, rear aperture sight with knobs and ears,
ventilated upper handguard, front band, gas cylinder and gas lock (carrying
the front sight post here, since the can covers the flash suppressor), a
20-round box magazine in front of the trigger guard, steel butt plate.

Real proportions: 330 mm length of pull, 559 mm barrel, 1.19 m with the can.

The pistol grip is the Pistol 57 / MG42 grip profile moved down by GRIP_DZ
(the rifle's trigger group sits lower under the bore); the arms script uses
the same offset (raw_assets/characters/fp_arms_m14p/build.py).

Parts (per-face part id, split after the bake):
  body      everything that doesn't move
  slide     bolt, op rod and charging handle (cycle back on every shot)
  magazine  the box magazine (drops during a reload)
  stock     the buttstock behind the receiver (hidden while aiming)

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis
above the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/m14p/build.py --out assets/weapons/m14p/m14p.gltf --tex 4096 \
      --preview /tmp/m14p.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/m14p.png
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
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_side/_beauty/_left/_detail/_fp.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material

# ---------------------------------------------------------------- materials
M_POLY = mat("black_polymer", (0.024, 0.025, 0.027), 0.58, 0.0, wear=(0.09, 0.09, 0.095), wear_rough=0.45,
             bump_scale=1400, bump_strength=0.12)
M_GRIPTEX = mat("polymer_stipple", (0.02, 0.021, 0.023), 0.75, 0.0, bump_scale=420, bump_strength=0.45)
M_PARK = mat("parkerized", (0.055, 0.058, 0.056), 0.52, 0.75, wear=(0.42, 0.42, 0.43), wear_rough=0.25,
             bump_scale=1100, bump_strength=0.05)
M_BLUED = mat("barrel_blued", (0.04, 0.042, 0.05), 0.4, 1.0, brushed=0.02)
M_STEEL = mat("bright_steel", (0.45, 0.46, 0.47), 0.3, 1.0, wear=(0.7, 0.7, 0.72), wear_rough=0.2, brushed=0.03)
M_CAN = mat("suppressor_cerakote", (0.028, 0.029, 0.031), 0.55, 0.25, wear=(0.3, 0.3, 0.31), wear_rough=0.35,
            bump_scale=1500, bump_strength=0.06)
M_DARK = mat("vent_dark", (0.004, 0.004, 0.005), 0.8, 0.0)
M_BRASS = mat("brass", (0.78, 0.56, 0.24), 0.26, 1.0)
M_COPPER = mat("gilding_metal", (0.72, 0.38, 0.22), 0.3, 1.0)
M_GLASS = mat("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = mat("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_MARK = mat("engraving", (0.3, 0.31, 0.32), 0.45, 1.0)
M_RUBBER = mat("rubber", (0.018, 0.018, 0.019), 0.85, 0.0, bump_scale=600, bump_strength=0.3)
MATERIALS = [M_POLY, M_GRIPTEX, M_PARK, M_BLUED, M_STEEL, M_CAN, M_DARK, M_BRASS, M_COPPER, M_GLASS, M_AMBER,
             M_MARK, M_RUBBER]

PART_IDS = {"body": 0, "slide": 1, "magazine": 2, "stock": 3}
CURRENT = ["body"]
PART_OF = {}

SIGHT_Z = 0.046            # sight line: rear aperture centre = front post tip
GRIP_DZ = -0.022           # the shared pistol-grip profile, moved down this much
REC_X0, REC_X1 = -0.13, 0.115
BARREL_X1 = 0.665
CAN_X0, CAN_X1, CAN_R = 0.672, 0.865, 0.0205
MUZZLE_X = CAN_X1

# Stock: (x, top z, bottom z, half width), butt to nose. The comb runs straight
# back from the receiver (M14A1 line); the fore-end stops at the front band.
STOCK = [
    (-0.322, 0.006, -0.124, 0.0195),
    (-0.312, 0.009, -0.128, 0.021),
    (-0.22, 0.011, -0.108, 0.0215),
    (-0.15, 0.010, -0.083, 0.0205),
    (-0.115, 0.003, -0.064, 0.0195),
    (-0.08, -0.008, -0.056, 0.0205),
    (0.12, -0.008, -0.054, 0.0205),
    (0.15, -0.004, -0.047, 0.0195),
    (0.40, -0.004, -0.041, 0.0172),
    (0.432, -0.002, -0.033, 0.0155),
]
BUTT_SPLIT = -0.15         # stock part behind here (hidden while aiming)


def part(name):
    CURRENT[0] = name


def high():
    return hs.D["name"] == "high"


def finish(ob, m, lb=True, **kw):
    """lb=False: no bevel on the LOW mesh (small repeated parts; the bake carries it)."""
    PART_OF[ob.name] = CURRENT[0]
    if not lb and not high():
        kw["bevel"] = 0
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m):
    ob = hs.text(name, body, size, loc, rot, m)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def at_x(stations, x):
    for a, b in zip(stations[:-1], stations[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(x if i == 0 else a[i] + (b[i] - a[i]) * t for i in range(4))
    return stations[0] if x < stations[0][0] else stations[-1]


def between(stations, x0, x1):
    return [at_x(stations, x0)] + [s for s in stations if x0 < s[0] < x1] + [at_x(stations, x1)]


def axis_loft(name, top, axis, st, power=2.3):
    """Loft along a (tilted) grip axis: st = [(h, half depth, half width)]."""
    axis = V(axis).normalized()
    fwd = V((-axis.z, 0.0, axis.x))
    right = V((0.0, -1.0, 0.0))
    return hs.loft(name, [(V(top) + axis * h, fwd, right, hd, hw) for h, hd, hw in st], power=power)


# ---------------------------------------------------------------- stock and grips
def build_stock():
    # Butt section and fore section are separate parts so the butt can hide while aiming.
    part("stock")
    finish(hs.loft_x("stock_butt", between(STOCK, STOCK[0][0], BUTT_SPLIT), power=4.0), M_POLY, bevel=0.0018,
           angle=40)
    # Butt plate (steel, M14 trap door) and a rubber pad strip.
    finish(hs.loft_x("butt_plate", [(-0.333, 0.004, -0.122, 0.0185), (-0.3215, 0.007, -0.127, 0.0212)], power=4.0),
           M_PARK, bevel=0.0012)
    finish(hs.box("trap_door", (0.002, 0.024, 0.05), (-0.3335, 0, -0.06)), M_PARK, bevel=0.0006)
    finish(hs.cyl_y("trap_hinge", 0.0024, 0.026, (-0.3345, 0, -0.033), verts=16), M_PARK, bevel=0.0004)
    # Raised cheek comb line and a stippled panel on each side of the butt.
    for sy in (1, -1):
        finish(hs.side_profile(f"butt_panel{sy}", [(-0.29, -0.03), (-0.19, -0.022), (-0.19, -0.07), (-0.29, -0.095)],
                               0.0012, y=sy * 0.0213), M_GRIPTEX, bevel=0.0004)
    finish(hs.cyl_y("swivel_rear", 0.0062, 0.0055, (-0.26, 0.0, -0.119), verts=20), M_PARK, bevel=0.0008)
    part("body")
    finish(hs.loft_x("stock_fore", between(STOCK, BUTT_SPLIT, STOCK[-1][0]), power=4.0), M_POLY, bevel=0.0016,
           angle=40)
    # Stock ferrule at the nose, receiver channel liner.
    finish(hs.loft_x("ferrule", [(0.425, 0.001, -0.031, 0.0158), (0.433, 0.0, -0.030, 0.0153)], power=4.0),
           M_PARK, bevel=0.0006)
    # Stippled grip panels on the fore-end where a hand would go.
    for sy in (1, -1):
        finish(hs.side_profile(f"fore_panel{sy}", [(0.26, -0.012), (0.37, -0.012), (0.37, -0.034), (0.26, -0.036)],
                               0.0012, y=sy * 0.0176), M_GRIPTEX, bevel=0.0004)

    # Pistol grip: the shared profile, moved down by GRIP_DZ (M14A1-style straight-line stock).
    d = GRIP_DZ
    gp = [(0.044, -0.031), (0.047, -0.052), (0.040, -0.061), (-0.020, -0.061), (-0.027, -0.054), (-0.056, -0.134),
          (-0.061, -0.138), (-0.103, -0.138), (-0.107, -0.132), (-0.081, -0.046), (-0.095, -0.031)]
    grip = hs.side_profile("grip", [(x, z + d) for x, z in gp], 0.030)
    hole = [(-0.018, -0.0345), (0.037, -0.0345), (0.039, -0.050), (0.033, -0.0555), (-0.014, -0.0555), (-0.023, -0.046)]
    hs.cut(grip, hs.side_profile("guard_hole", [(x, z + d) for x, z in hole], 0.05))
    groove = hs.cyl_y("finger_groove", 0.0068, 0.06, (-0.0300, 0, -0.0745 + d), verts=32)
    hs.linear_array(groove, 3, (-0.0071, 0, -0.0197))
    hs.cut(grip, groove)
    finish(grip, M_POLY, bevel=0.0012)
    for sy in (1, -1):
        finish(hs.side_profile(f"grip_stipple{sy}", [(-0.087, -0.062 + d), (-0.060, -0.062 + d), (-0.054, -0.118 + d),
                                                     (-0.098, -0.118 + d)], 0.0012, y=sy * 0.0152), M_GRIPTEX,
               bevel=0.0004)
    finish(hs.side_profile("grip_cap", [(-0.058, -0.137 + d), (-0.105, -0.137 + d), (-0.108, -0.1445 + d),
                                        (-0.055, -0.1445 + d)], 0.027), M_PARK, bevel=0.0008)
    finish(hs.side_profile("trigger", [(0.012, -0.033 + d), (0.018, -0.033 + d), (0.016, -0.041 + d),
                                       (0.021, -0.051 + d), (0.015, -0.053 + d), (0.008, -0.041 + d)], 0.0055),
           M_PARK, bevel=0.0005)
    # M14 safety: a tab at the front of the trigger guard.
    finish(hs.box("safety", (0.007, 0.007, 0.012), (0.041, 0, -0.040 + d)), M_PARK, bevel=0.0007)

    # Stubby foregrip on a short rail under the fore-end.
    finish(hs.box("rail_base", (0.075, 0.020, 0.006), (0.300, 0, -0.0432)), M_PARK, bevel=0.0008)
    for i in range(7):
        finish(hs.box(f"rail_slot{i}", (0.0052, 0.0215, 0.0032), (0.270 + i * 0.0102, 0, -0.0476)), M_PARK,
               bevel=0.0004, lb=False)
    stub = axis_loft("stub_grip", FORE_TOP, FORE_AXIS, [(-0.004, 0.0158, 0.0150), (0.006, 0.0150, 0.0142),
                                                         (0.030, 0.0154, 0.0146), (0.052, 0.0160, 0.0152),
                                                         (0.060, 0.0175, 0.0166), (0.066, 0.0168, 0.0158)])
    finish(stub, M_POLY, bevel=0.0014, angle=40)
    finish(hs.box("stub_clamp", (0.034, 0.024, 0.008), (FORE_TOP.x + 0.002, 0, -0.0505)), M_PARK, bevel=0.0009)
    for i in range(3):
        h = 0.016 + i * 0.013
        c = FORE_TOP + FORE_AXIS * h
        ring = hs.cyl_between(f"stub_ring{i}", c - FORE_AXIS * 0.0015, c + FORE_AXIS * 0.0015, 0.0162, verts=32)
        finish(ring, M_GRIPTEX, bevel=0.0004, lb=False)


FORE_TOP = V((0.300, 0.0, -0.051))
FORE_AXIS = V((0.010, 0.0, -0.060)).normalized()


# ---------------------------------------------------------------- receiver, bolt, op rod
def build_receiver():
    # Receiver: open on top over the bolt; the heel carries the rear sight.
    finish(hs.loft_x("receiver", [(REC_X0, 0.016, -0.012, 0.012), (REC_X0 + 0.01, 0.018, -0.012, 0.0135),
                                  (REC_X1 - 0.01, 0.017, -0.012, 0.0135), (REC_X1, 0.015, -0.012, 0.012)],
                     power=5.0), M_PARK, bevel=0.0009)
    # Top opening (dark) where the bolt rides, and the ejection side cut.
    finish(hs.box("bolt_well", (0.105, 0.017, 0.006), (0.02, 0, 0.0158)), M_DARK, bevel=0)
    # Receiver heel ribs and the clip guide in front of the rear sight.
    for sy in (1, -1):
        finish(hs.box(f"heel_rib{sy}", (0.05, 0.002, 0.008), (-0.10, sy * 0.0136, 0.006)), M_PARK, bevel=0.0005)
    finish(hs.box("clip_guide", (0.008, 0.02, 0.008), (-0.045, 0, 0.022)), M_PARK, bevel=0.0007)
    # Rear sight: base, protective ears, aperture disc with the peep hole, knobs.
    finish(hs.box("rs_base", (0.03, 0.022, 0.012), (-0.108, 0, 0.023)), M_PARK, bevel=0.0009)
    for sy in (1, -1):
        ear = hs.side_profile(f"rs_ear{sy}", [(-0.122, 0.028), (-0.096, 0.028), (-0.100, SIGHT_Z + 0.007),
                                              (-0.116, SIGHT_Z + 0.007)], 0.003, y=sy * 0.0115)
        finish(ear, M_PARK, bevel=0.0005)
    ap_disc = hs.cyl_x("rs_aperture", 0.0075, -0.110, -0.106, verts=32, z=SIGHT_Z)
    hs.cut(ap_disc, hs.cyl_x("rs_peep", 0.0024, -0.12, -0.09, verts=20, z=SIGHT_Z, fixed=True))
    finish(ap_disc, M_PARK, bevel=0.0004)
    # Stem below the disc only: it must not reach into the peep hole.
    stem_top = SIGHT_Z - 0.0050
    finish(hs.box("rs_stem", (0.004, 0.006, stem_top - 0.026), (-0.108, 0, (stem_top + 0.026) / 2)), M_PARK,
           bevel=0.0003)
    finish(hs.cyl_y("rs_knob_elev", 0.0085, 0.006, (-0.108, 0.0175, 0.025), verts=24), M_PARK, bevel=0.0008)
    finish(hs.cyl_y("rs_knob_wind", 0.0068, 0.005, (-0.108, -0.0165, 0.025), verts=24), M_PARK, bevel=0.0008)
    # Bolt stop on the left.
    finish(hs.box("bolt_stop", (0.014, 0.003, 0.007), (0.03, 0.0148, 0.002)), M_PARK, bevel=0.0005)
    # Fire-Control Link readout clipped to the left of the receiver heel.
    finish(hs.box("fcl_glass", (0.028, 0.0014, 0.009), (-0.085, 0.0145, -0.002)), M_GLASS, bevel=0.0004)
    for i, w in enumerate((0.004, 0.007, 0.003, 0.005)):
        finish(hs.box(f"fcl_seg{i}", (w, 0.0004, 0.0012), (-0.096 + i * 0.006 + w / 2, 0.0153, 0.0002)), M_AMBER, bevel=0)
    text("mark_heel", "M14/P  7.62 MM", 0.0042, (-0.052, 0.0137, -0.009), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_serial", "GRF 1404", 0.0034, (0.095, 0.0137, -0.009), (math.pi / 2, 0, math.pi), M_MARK)

    # Moving parts: bolt (top), op rod along the right, charging handle.
    part("slide")
    finish(hs.cyl_x("bolt", 0.0078, -0.035, 0.068, verts=24, z=0.012), M_STEEL, bevel=0.0008)
    finish(hs.box("bolt_lug", (0.012, 0.006, 0.006), (0.055, 0.007, 0.018)), M_STEEL, bevel=0.0005)
    finish(hs.box("bolt_roller", (0.01, 0.005, 0.005), (-0.02, -0.0085, 0.017)), M_STEEL, bevel=0.0005)
    oprod = hs.cyl_between("op_rod", (0.092, -0.0175, -0.0005), (0.45, -0.0155, -0.0045), 0.0042, verts=16)
    finish(oprod, M_PARK, bevel=0.0004)
    handle = hs.side_profile("op_handle", [(0.060, -0.006), (0.104, -0.006), (0.104, 0.008), (0.084, 0.010),
                                           (0.060, 0.004)], 0.007, y=-0.0185)
    finish(handle, M_PARK, bevel=0.0008)
    finish(hs.cyl_y("op_knob", 0.0055, 0.012, (0.071, -0.0265, 0.006), verts=20), M_PARK, bevel=0.0012)
    part("body")


# ---------------------------------------------------------------- barrel, gas system, sights, can
def build_barrel():
    finish(hs.cyl_x("barrel", 0.0098, REC_X1 - 0.005, 0.44, verts=32, radius2=0.0092), M_BLUED, bevel=0.0003)
    finish(hs.cyl_x("barrel_fwd", 0.0092, 0.44, BARREL_X1, verts=32, radius2=0.0084), M_BLUED, bevel=0.0003)
    # Upper handguard: ventilated polymer over the barrel, receiver to front band.
    hg = [(0.122, 0.0168, -0.003, 0.0138), (0.14, 0.0182, -0.003, 0.0150), (0.40, 0.0172, -0.003, 0.0143),
          (0.425, 0.0160, -0.003, 0.0132)]
    finish(hs.loft_x("handguard", hg, power=3.0), M_POLY, bevel=0.0012, angle=40)
    for i in range(6):
        x = 0.17 + i * 0.038
        for sy in (1, -1):
            finish(hs.box(f"hg_vent{i}{sy}", (0.022, 0.003, 0.0055), (x, sy * 0.0132, 0.0095)), M_DARK, bevel=0.0012,
                   segments=2, lb=False)
    # Front band (clamps barrel, gas cylinder and stock nose), sling swivel.
    finish(hs.loft_x("front_band", [(0.432, 0.013, -0.033, 0.0158), (0.452, 0.013, -0.033, 0.0158)], power=3.5),
           M_PARK, bevel=0.0009)
    finish(hs.cyl_y("swivel_front", 0.0058, 0.005, (0.442, 0.0, -0.038), verts=20), M_PARK, bevel=0.0007)
    # Gas cylinder under the barrel, gas lock (front sight base) and gas plug.
    finish(hs.cyl_x("gas_cyl", 0.0098, 0.452, 0.60, verts=32, z=-0.0215), M_PARK, bevel=0.0005)
    finish(hs.box("gas_bridge", (0.13, 0.008, 0.012), (0.525, 0, -0.011)), M_PARK, bevel=0.0005)
    finish(hs.cyl_x("gas_lock", 0.0112, 0.60, 0.616, verts=32, z=-0.0185), M_PARK, bevel=0.0006)
    finish(hs.cyl_x("gas_plug", 0.0075, 0.616, 0.624, verts=6, z=-0.0215), M_PARK, bevel=0.0006)
    # Front sight on the gas lock: base, ears, post.
    finish(hs.box("fs_base", (0.016, 0.014, 0.020), (0.608, 0, 0.012)), M_PARK, bevel=0.0008)
    finish(hs.box("fs_post", (0.0032, 0.0022, SIGHT_Z - 0.021), (0.608, 0, (SIGHT_Z + 0.021) / 2)), M_PARK,
           bevel=0.0003)
    for sy in (1, -1):
        ear = hs.side_profile(f"fs_ear{sy}", [(0.600, 0.020), (0.616, 0.020), (0.614, SIGHT_Z + 0.004),
                                              (0.602, SIGHT_Z + 0.004)], 0.002, y=sy * 0.0078)
        finish(ear, M_PARK, bevel=0.0004)
    # Suppressor: QD collar on the muzzle, ribbed body, end cap.
    finish(hs.lathe_x("can_mount", [(0.656, 0.0105), (0.658, 0.0145), (0.672, 0.0145), (0.674, 0.0170)], verts=40),
           M_CAN, bevel=0.0005)
    body = hs.lathe_x("can", [(CAN_X0, 0.0175), (CAN_X0 + 0.006, CAN_R), (CAN_X1 - 0.008, CAN_R),
                              (CAN_X1, CAN_R - 0.0045)], verts=48)
    finish(body, M_CAN, bevel=0.0008)
    for i in range(4):
        x = CAN_X0 + 0.016 + i * 0.008
        finish(hs.lathe_x(f"can_rib{i}", [(x, CAN_R), (x + 0.0006, CAN_R + 0.0011), (x + 0.0034, CAN_R + 0.0011),
                                          (x + 0.004, CAN_R)], verts=48), M_CAN, bevel=0, lb=False)
    finish(hs.cyl_x("can_bore", 0.0052, CAN_X1 - 0.002, CAN_X1 + 0.0002, verts=20), M_DARK, bevel=0)
    text("mark_can", "GRF SR-762", 0.0055, (CAN_X0 + 0.11, CAN_R + 0.0001, -0.002), (math.pi / 2, 0, math.pi), M_MARK)


# ---------------------------------------------------------------- magazine
MAG_X0, MAG_X1 = 0.054, 0.138


def build_magazine():
    part("magazine")
    # 20-round box: a slight forward curve, ribbed sides, floor plate.
    outline = [(MAG_X0, -0.040), (MAG_X1, -0.040), (MAG_X1 + 0.006, -0.155), (MAG_X0 + 0.010, -0.158)]
    finish(hs.side_profile("mag", outline, 0.026), M_PARK, bevel=0.0010)
    for sy in (1, -1):
        finish(hs.side_profile(f"mag_rib{sy}", [(MAG_X0 + 0.012, -0.062), (MAG_X1 - 0.010, -0.062),
                                                (MAG_X1 - 0.006, -0.140), (MAG_X0 + 0.018, -0.142)], 0.0012,
                               y=sy * 0.0131), M_PARK, bevel=0.0005)
    finish(hs.side_profile("mag_floor", [(MAG_X0 + 0.006, -0.156), (MAG_X1 + 0.009, -0.153),
                                         (MAG_X1 + 0.009, -0.164), (MAG_X0 + 0.006, -0.166)], 0.029), M_PARK,
           bevel=0.0010)
    # Top round in the feed lips, visible in the open receiver.
    finish(hs.cyl_x("mag_round", 0.0058, 0.035, 0.078, verts=16, z=-0.0005), M_BRASS, bevel=0, smooth=True)
    finish(hs.cyl_x("mag_bullet", 0.0040, 0.078, 0.104, verts=16, z=-0.0005, radius2=0.0012), M_COPPER, bevel=0)
    part("body")
    # Mag catch behind the magazine.
    finish(hs.box("mag_catch", (0.008, 0.012, 0.01), (MAG_X0 - 0.006, 0, -0.050)), M_PARK, bevel=0.0006)


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_stock()
    build_receiver()
    build_barrel()
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
    print(f"m14p {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


def split_parts(low):
    objs = []
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
        objs.append(ob)
        print(f"m14p: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.008, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.12, 0.125, 0.135, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world
    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, -0.19)
    floor.data.materials.append(mat("floor", (0.03, 0.031, 0.033), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.25, 0, -0.04), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.2, -1.3, 1.1), 55, 1.8, sy=0.5)
    area("strip_top", (0.25, 0.0, 1.1), 35, 2.4, sy=0.18)
    area("fill", (0.6, 1.4, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.7, -0.4, 0.5), 50, 0.8, (1.0, 0.85, 0.7))
    area("kick", (-1.3, 0.3, 0.2), 30, 1.0, (0.8, 0.9, 1.0))
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
    print(f"m14p: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((0.27, -2.3, 0.0), (0.27, 0, -0.04), 55, 0.0),
        "beauty": ((0.95, -1.0, 0.42), (0.18, 0, -0.04), 45, 8.0),
        "left": ((-0.25, 1.05, 0.35), (0.2, 0, -0.04), 40, 8.0),
        "detail": ((0.05, -0.40, 0.18), (0.02, 0.0, 0.0), 50, 4.0),
        "fp": ((-0.42, 0.10, 0.14), (0.8, -0.02, -0.05), 0, 0.0),
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
    high_ob = build(hs.HIGH, "m14p_high")
    low = build(hs.LOW, "m14p_low")
    bakeutil.unwrap(low, boost={M_POLY.name: 0.85, M_PARK.name: 1.25, M_STEEL.name: 1.3, M_MARK.name: 1.5,
                                M_CAN.name: 0.9, M_BRASS.name: 1.3})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high_ob, low, MATERIALS, args.tex, tex_dir, "m14p", cage=0.0012, ray=0.004,
                                 ao_distance=0.025, grime=0.35, log=print)
    bpy.data.objects.remove(high_ob)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "m14p", emission_strength=4.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"m14p: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "m14p_high")
    render_previews(args.preview.rsplit(".", 1)[0])
