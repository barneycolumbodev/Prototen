"""The Governor: a full-size .45-70 Government lever-action rifle in black polymer (owner, 2026-11-18).

Owner brief: "a tactical black polymer full size 45-70 lever action rifle ...
intense sound, harsh recoil, devastating ballistic impact, and the satisfying
haptic and audio clunk of the lever being drawn."

Design reading: a modern big-bore "tactical lever" (the Marlin 1895 Dark /
SBL family): a flat-sided receiver in black nitride with a top rail and a
ghost-ring rear sight, a big lever loop round the trigger, an exposed hammer,
a side loading gate on the right, a full-length tube magazine under an
18.5-inch barrel, an M-LOK polymer fore-end and a stubby vertical grip, a
ported muzzle brake, a straight polymer stock with a cheek riser and a thick
recoil pad. Real proportions: 470 mm barrel, about 0.97 m overall.

The pistol grip and the stubby grip are exactly where the M14/P has them
(raw_assets/weapons/m14p/build.py: GRIP_DZ, FORE_TOP), so the M14/P's
first-person arms hold this gun too.

Parts (per-face part id, split after the bake):
  body       everything that doesn't move
  lever      the lever loop: swings down and forward about LEVER_PIVOT on every cycle
  bolt       the bolt and its handle: run back while the lever is down
  hammer     the hammer: falls on the shot, the lever cocks it back
  stock      the butt behind BUTT_SPLIT (hidden while aiming)
  load_round a cartridge at the loading gate, shown going in during reloads

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis
above the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/governor/build.py --out assets/weapons/governor/governor.gltf --tex 2048 \
      --preview /tmp/governor.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/governor.png
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
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--emission-size", type=int, default=256)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_side/_beauty/_left/_detail/_fp.png")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material

# ---------------------------------------------------------------- materials
M_POLY = mat("black_polymer", (0.022, 0.023, 0.025), 0.6, 0.0, wear=(0.08, 0.08, 0.085), wear_rough=0.45,
             bump_scale=1400, bump_strength=0.12)
M_GRIPTEX = mat("polymer_stipple", (0.019, 0.02, 0.022), 0.78, 0.0, bump_scale=420, bump_strength=0.45)
M_NITRIDE = mat("black_nitride", (0.03, 0.031, 0.033), 0.42, 0.85, wear=(0.36, 0.36, 0.37), wear_rough=0.22,
                bump_scale=1200, bump_strength=0.03)
M_BLUED = mat("barrel_nitride", (0.025, 0.026, 0.03), 0.36, 1.0, brushed=0.02)
M_STEEL = mat("bright_steel", (0.5, 0.5, 0.51), 0.28, 1.0, wear=(0.7, 0.7, 0.72), wear_rough=0.2, brushed=0.03)
M_DARK = mat("port_dark", (0.004, 0.004, 0.005), 0.8, 0.0)
M_BRASS = mat("brass", (0.8, 0.58, 0.25), 0.25, 1.0)
M_LEAD = mat("lead", (0.32, 0.32, 0.34), 0.5, 0.6)
M_MARK = mat("engraving", (0.34, 0.35, 0.36), 0.45, 1.0)
M_RUBBER = mat("rubber", (0.016, 0.016, 0.017), 0.88, 0.0, bump_scale=600, bump_strength=0.3)
M_TRITIUM = mat("tritium", (0.6, 1.0, 0.4), 0.4, 0.0, emission=((0.45, 1.0, 0.3), 8.0))
MATERIALS = [M_POLY, M_GRIPTEX, M_NITRIDE, M_BLUED, M_STEEL, M_DARK, M_BRASS, M_LEAD, M_MARK, M_RUBBER, M_TRITIUM]
M_PARK = M_NITRIDE

PART_IDS = {"body": 0, "lever": 1, "bolt": 2, "hammer": 3, "stock": 4, "load_round": 5}
CURRENT = ["body"]
PART_OF = {}

SIGHT_Z = 0.040            # sight line: ghost ring centre = front post tip
GRIP_DZ = -0.022           # the shared pistol-grip profile, moved down this much (as the M14/P)
REC_X0, REC_X1 = -0.108, 0.095
BARREL_X1 = 0.470
BRAKE_X0, BRAKE_X1 = 0.466, 0.532
MUZZLE_X = BRAKE_X1
TUBE_Z, TUBE_R = -0.0255, 0.0098
LEVER_PIVOT = V((0.062, 0.0, -0.036))
HAMMER_PIVOT = V((-0.082, 0.0, 0.002))
FORE_TOP = V((0.300, 0.0, -0.051))
FORE_AXIS = V((0.010, 0.0, -0.060)).normalized()

# Stock: (x, top z, bottom z, half width), butt to the receiver.
STOCK = [
    (-0.348, 0.010, -0.122, 0.0195),
    (-0.334, 0.012, -0.126, 0.0210),
    (-0.25, 0.013, -0.104, 0.0205),
    (-0.17, 0.010, -0.072, 0.0180),
    (-0.135, 0.008, -0.058, 0.0165),
    (-0.112, 0.010, -0.050, 0.0150),
]
BUTT_SPLIT = -0.16         # stock part behind here (hidden while aiming)


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
    part("stock")
    finish(hs.loft_x("stock_butt", between(STOCK, STOCK[0][0], BUTT_SPLIT), power=4.0), M_POLY, bevel=0.0018, angle=40)
    # Thick recoil pad (a .45-70 needs one) and its black spacer.
    finish(hs.loft_x("pad", [(-0.372, 0.008, -0.120, 0.019), (-0.352, 0.0105, -0.125, 0.0205)], power=4.0), M_RUBBER,
           bevel=0.003)
    finish(hs.loft_x("pad_spacer", [(-0.352, 0.0105, -0.125, 0.0207), (-0.348, 0.010, -0.122, 0.0197)], power=4.0), M_NITRIDE,
           bevel=0.0006)
    for i in range(5):
        finish(hs.box(f"pad_rib{i}", (0.016, 0.0415, 0.0016), (-0.362, 0, -0.018 - i * 0.02)), M_RUBBER, bevel=0.0004, lb=False)
    # Cheek riser, stippled panels, a QD sling cup.
    finish(hs.loft_x("riser", [(-0.30, 0.024, 0.008, 0.017), (-0.18, 0.026, 0.010, 0.017)], power=3.0), M_POLY,
           bevel=0.0025, angle=40)
    for sy in (1, -1):
        finish(hs.side_profile(f"butt_panel{sy}", [(-0.30, -0.030), (-0.22, -0.026), (-0.22, -0.070), (-0.30, -0.092)],
                               0.0012, y=sy * 0.0206), M_GRIPTEX, bevel=0.0004)
    finish(hs.cyl_y("qd_cup", 0.0075, 0.043, (-0.30, 0.0, -0.10), verts=24), M_NITRIDE, bevel=0.0008)
    part("body")
    finish(hs.loft_x("stock_fore", between(STOCK, BUTT_SPLIT, STOCK[-1][0]), power=4.0), M_POLY, bevel=0.0016, angle=40)

    # Pistol grip: the shared profile behind the trigger (the lever loop is the guard).
    d = GRIP_DZ
    gp = [(-0.024, -0.034), (-0.027, -0.054), (-0.056, -0.134), (-0.061, -0.138), (-0.103, -0.138), (-0.107, -0.132),
          (-0.081, -0.046), (-0.100, -0.026)]
    grip = hs.side_profile("grip", [(x, z + d) for x, z in gp], 0.030)
    groove = hs.cyl_y("finger_groove", 0.0068, 0.06, (-0.0300, 0, -0.0745 + d), verts=32)
    hs.linear_array(groove, 3, (-0.0071, 0, -0.0197))
    hs.cut(grip, groove)
    finish(grip, M_POLY, bevel=0.0012)
    for sy in (1, -1):
        finish(hs.side_profile(f"grip_stipple{sy}", [(-0.087, -0.062 + d), (-0.060, -0.062 + d), (-0.054, -0.118 + d),
                                                     (-0.098, -0.118 + d)], 0.0012, y=sy * 0.0152), M_GRIPTEX,
               bevel=0.0004)
    finish(hs.side_profile("grip_cap", [(-0.058, -0.137 + d), (-0.105, -0.137 + d), (-0.108, -0.1445 + d),
                                        (-0.055, -0.1445 + d)], 0.027), M_NITRIDE, bevel=0.0008)
    # Lower tang / trigger plate between the receiver and the grip.
    finish(hs.side_profile("trigger_plate", [(-0.034, -0.036), (0.070, -0.036), (0.066, -0.051), (-0.026, -0.053)], 0.016),
           M_NITRIDE, bevel=0.0008)
    finish(hs.side_profile("trigger", [(0.012, -0.050 + d * 0.2), (0.019, -0.050 + d * 0.2), (0.017, -0.058 + d),
                                       (0.022, -0.069 + d), (0.016, -0.072 + d), (0.009, -0.059 + d)], 0.0055),
           M_STEEL, bevel=0.0005)
    # Cross-bolt safety above the trigger.
    finish(hs.cyl_y("safety", 0.0035, 0.024, (0.004, 0, -0.044), verts=16), M_NITRIDE, bevel=0.0005)

    # Stubby foregrip on a short rail under the fore-end (where the M14/P has its).
    finish(hs.box("rail_base", (0.075, 0.020, 0.006), (0.300, 0, -0.0432)), M_NITRIDE, bevel=0.0008)
    for i in range(7):
        finish(hs.box(f"rail_slot{i}", (0.0052, 0.0215, 0.0032), (0.270 + i * 0.0102, 0, -0.0476)), M_NITRIDE,
               bevel=0.0004, lb=False)
    stub = axis_loft("stub_grip", FORE_TOP, FORE_AXIS, [(-0.004, 0.0158, 0.0150), (0.006, 0.0150, 0.0142),
                                                         (0.030, 0.0154, 0.0146), (0.052, 0.0160, 0.0152),
                                                         (0.060, 0.0175, 0.0166), (0.066, 0.0168, 0.0158)])
    finish(stub, M_POLY, bevel=0.0014, angle=40)
    finish(hs.box("stub_clamp", (0.034, 0.024, 0.008), (FORE_TOP.x + 0.002, 0, -0.0505)), M_NITRIDE, bevel=0.0009)
    for i in range(3):
        h = 0.016 + i * 0.013
        c = FORE_TOP + FORE_AXIS * h
        ring = hs.cyl_between(f"stub_ring{i}", c - FORE_AXIS * 0.0015, c + FORE_AXIS * 0.0015, 0.0162, verts=32)
        finish(ring, M_GRIPTEX, bevel=0.0004, lb=False)


# ---------------------------------------------------------------- receiver, bolt, hammer, sights
def build_receiver():
    finish(hs.loft_x("receiver", [(REC_X0, 0.012, -0.036, 0.0128), (REC_X0 + 0.012, 0.020, -0.038, 0.0145),
                                  (REC_X1 - 0.01, 0.020, -0.038, 0.0145), (REC_X1, 0.016, -0.034, 0.0132)],
                     power=6.0), M_NITRIDE, bevel=0.0010)
    # Ejection port on top (open: the bolt shows) and the loading gate on the right.
    finish(hs.box("eject_port", (0.07, 0.016, 0.004), (0.01, -0.002, 0.0195)), M_DARK, bevel=0)
    gate = hs.side_profile("gate", [(0.028, -0.026), (0.070, -0.026), (0.072, -0.010), (0.030, -0.008)], 0.0016, y=-0.0150)
    finish(gate, M_STEEL, bevel=0.0005)
    finish(hs.cyl_y("gate_screw", 0.0022, 0.002, (0.064, -0.0158, -0.018), verts=12), M_STEEL, bevel=0.0003)
    for sy in (1, -1):
        finish(hs.cyl_y(f"lever_screw{sy}", 0.0034, 0.0016, (LEVER_PIVOT.x, sy * 0.0152, LEVER_PIVOT.z + 0.002), verts=16),
               M_STEEL, bevel=0.0004)
        finish(hs.cyl_y(f"hammer_screw{sy}", 0.0026, 0.0016, (HAMMER_PIVOT.x, sy * 0.0150, HAMMER_PIVOT.z - 0.006), verts=12),
               M_STEEL, bevel=0.0003)
    # Top rail and the ghost-ring rear sight on it.
    finish(hs.box("top_rail", (0.17, 0.016, 0.006), (-0.015, 0, 0.023)), M_NITRIDE, bevel=0.0006)
    for i in range(12):
        finish(hs.box(f"top_slot{i}", (0.0045, 0.0165, 0.0026), (-0.092 + i * 0.0142, 0, 0.0262)), M_NITRIDE,
               bevel=0.0003, lb=False)
    finish(hs.box("gr_base", (0.026, 0.020, 0.008), (-0.075, 0, 0.030)), M_NITRIDE, bevel=0.0008)
    ring = hs.cyl_x("ghost_ring", 0.0095, -0.079, -0.073, verts=32, z=SIGHT_Z)
    hs.cut(ring, hs.cyl_x("ghost_hole", 0.0055, -0.09, -0.06, verts=24, z=SIGHT_Z, fixed=True))
    finish(ring, M_NITRIDE, bevel=0.0005)
    for sy in (1, -1):
        finish(hs.side_profile(f"gr_ear{sy}", [(-0.086, 0.032), (-0.066, 0.032), (-0.070, SIGHT_Z + 0.009),
                                               (-0.082, SIGHT_Z + 0.009)], 0.0026, y=sy * 0.0112), M_NITRIDE, bevel=0.0005)
    text("mark_name", "GOVERNOR", 0.0068, (0.000, 0.0146, -0.018), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_cal", ".45-70 GOVT", 0.0036, (0.040, 0.0146, -0.029), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_maker", "GRF ARMS", 0.0034, (0.050, -0.0146, 0.008), (math.pi / 2, 0, 0), M_MARK)

    part("bolt")
    finish(hs.cyl_x("bolt", 0.0062, -0.088, 0.020, verts=24, z=0.010), M_STEEL, bevel=0.0007)
    finish(hs.box("bolt_top", (0.10, 0.006, 0.004), (-0.035, 0, 0.0165)), M_STEEL, bevel=0.0004)
    finish(hs.cyl_y("bolt_handle", 0.0042, 0.012, (-0.040, -0.0192, 0.011), verts=16), M_STEEL, bevel=0.0012)
    part("hammer")
    ham = hs.side_profile("hammer", [(-0.086, -0.002), (-0.077, -0.002), (-0.080, 0.022), (-0.095, 0.034), (-0.108, 0.034),
                                     (-0.109, 0.029), (-0.092, 0.019)], 0.0062)
    finish(ham, M_STEEL, bevel=0.0006)
    finish(hs.box("hammer_spur", (0.016, 0.014, 0.003), (-0.103, 0, 0.0345)), M_NITRIDE, bevel=0.0006)
    part("body")


def build_lever():
    part("lever")
    d = GRIP_DZ
    p = LEVER_PIVOT
    loop = [(p.x, 0, p.z), (0.060, 0, -0.054 + d * 0.3), (0.048, 0, -0.076 + d * 0.4), (0.022, 0, -0.088 + d * 0.4),
            (-0.006, 0, -0.084 + d * 0.4), (-0.022, 0, -0.068 + d * 0.3), (-0.022, 0, -0.052)]
    finish(hs.tube_path("lever_loop", [V(q) for q in loop], 0.0046, width_scale=1.25, resolution=10), M_NITRIDE,
           bevel=0, smooth=True)
    finish(hs.side_profile("lever_tang", [(p.x - 0.006, p.z + 0.004), (p.x + 0.006, p.z + 0.004), (0.058, -0.052),
                                          (0.046, -0.050)], 0.0075), M_NITRIDE, bevel=0.0006)
    finish(hs.side_profile("lever_link", [(-0.026, -0.040), (0.050, -0.040), (0.050, -0.046), (-0.024, -0.048)], 0.006),
           M_NITRIDE, bevel=0.0005)
    part("body")


# ---------------------------------------------------------------- barrel, tube, fore-end, sights, brake
def build_barrel():
    finish(hs.cyl_x("barrel", 0.0110, REC_X1 - 0.005, BARREL_X1, verts=32, radius2=0.0104), M_BLUED, bevel=0.0003)
    finish(hs.cyl_x("mag_tube", TUBE_R, REC_X1 - 0.002, 0.420, verts=32, z=TUBE_Z), M_NITRIDE, bevel=0.0004)
    cap = hs.cyl_x("tube_cap", TUBE_R + 0.0008, 0.420, 0.438, verts=32, z=TUBE_Z)
    finish(cap, M_NITRIDE, bevel=0.0008)
    for i in range(10):
        finish(hs.box(f"cap_knurl{i}", (0.014, 0.0022, 0.0022), (0.429, 0, TUBE_Z)), M_NITRIDE, bevel=0, lb=False)
    finish(hs.loft_x("band", [(0.408, 0.0125, -0.0365, 0.0125), (0.420, 0.0125, -0.0365, 0.0125)], power=4.0), M_NITRIDE,
           bevel=0.0008)
    # M-LOK fore-end: a polymer shell round the barrel and the tube.
    fe = [(0.100, 0.017, -0.039, 0.0195), (0.112, 0.0185, -0.0405, 0.0215), (0.390, 0.0185, -0.0405, 0.0215),
          (0.402, 0.016, -0.038, 0.0192)]
    finish(hs.loft_x("fore_end", fe, power=4.5), M_POLY, bevel=0.0014, angle=40)
    for i in range(5):
        x = 0.135 + i * 0.048
        for sy in (1, -1):
            finish(hs.box(f"mlok{i}{sy}", (0.032, 0.003, 0.0072), (x, sy * 0.0205, -0.012)), M_DARK, bevel=0.0012,
                   segments=2, lb=False)
    finish(hs.cyl_y("qd_front", 0.0068, 0.045, (0.37, 0, -0.032), verts=24), M_NITRIDE, bevel=0.0008)
    # Front sight: clamp on the barrel, protected post with a tritium dot.
    finish(hs.cyl_x("fs_clamp", 0.0128, 0.432, 0.452, verts=32), M_NITRIDE, bevel=0.0006)
    finish(hs.box("fs_base", (0.018, 0.010, 0.020), (0.442, 0, 0.018)), M_NITRIDE, bevel=0.0007)
    finish(hs.box("fs_post", (0.003, 0.0026, SIGHT_Z - 0.026), (0.442, 0, (SIGHT_Z + 0.026) / 2)), M_NITRIDE, bevel=0.0003)
    finish(hs.cyl_x("fs_dot", 0.0013, 0.4405, 0.4435, verts=12, z=SIGHT_Z - 0.0015), M_TRITIUM, bevel=0)
    for sy in (1, -1):
        finish(hs.side_profile(f"fs_ear{sy}", [(0.434, 0.026), (0.450, 0.026), (0.448, SIGHT_Z + 0.005),
                                               (0.436, SIGHT_Z + 0.005)], 0.002, y=sy * 0.0074), M_NITRIDE, bevel=0.0004)
    # Ported muzzle brake.
    brake = hs.lathe_x("brake", [(BRAKE_X0, 0.0118), (BRAKE_X0 + 0.003, 0.0150), (BRAKE_X1 - 0.004, 0.0150),
                                 (BRAKE_X1, 0.0128)], verts=40)
    for i in range(3):
        x = BRAKE_X0 + 0.016 + i * 0.016
        hs.cut(brake, hs.box(f"port{i}", (0.009, 0.05, 0.016), (x, 0, 0.002)))
    finish(brake, M_NITRIDE, bevel=0.0006)
    finish(hs.cyl_x("brake_core", 0.0085, BRAKE_X0, BRAKE_X1 - 0.001, verts=24), M_DARK, bevel=0)
    finish(hs.cyl_x("bore", 0.0058, BRAKE_X1 - 0.002, BRAKE_X1 + 0.0002, verts=20), M_DARK, bevel=0)


def build_round():
    """A .45-70 at the loading gate (moved in by the rig during a reload)."""
    part("load_round")
    y, z = -0.0215, -0.017
    finish(hs.cyl_x("case", 0.0064, 0.000, 0.053, verts=20, y=y, z=z, radius2=0.0061), M_BRASS, bevel=0, smooth=True)
    finish(hs.cyl_x("rim", 0.0076, -0.0018, 0.000, verts=20, y=y, z=z), M_BRASS, bevel=0)
    finish(hs.cyl_x("slug", 0.0059, 0.053, 0.068, verts=20, y=y, z=z, radius2=0.0028), M_LEAD, bevel=0, smooth=True)
    part("body")


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_stock()
    build_receiver()
    build_lever()
    build_barrel()
    build_round()
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
    print(f"governor {detail['name']}: {bakeutil.tri_count(joined)} tris")
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
        print(f"governor: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    print(f"governor: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((0.10, -2.0, 0.0), (0.10, 0, -0.04), 55, 0.0),
        "beauty": ((0.80, -0.95, 0.40), (0.05, 0, -0.04), 45, 8.0),
        "left": ((-0.30, 1.0, 0.33), (0.08, 0, -0.04), 40, 8.0),
        "detail": ((0.0, -0.38, 0.06), (0.0, 0.0, -0.04), 50, 4.0),
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
    high_ob = build(hs.HIGH, "governor_high")
    low = build(hs.LOW, "governor_low")
    bakeutil.unwrap(low, boost={M_POLY.name: 0.85, M_PARK.name: 1.25, M_STEEL.name: 1.3, M_MARK.name: 1.5,
                                M_BRASS.name: 1.4})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high_ob, low, MATERIALS, args.tex, tex_dir, "governor", cage=0.0012, ray=0.004,
                                 ao_distance=0.025, grime=0.35, log=print)
    bpy.data.objects.remove(high_ob)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "governor", emission_strength=4.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"governor: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "governor_high")
    render_previews(args.preview.rsplit(".", 1)[0])
