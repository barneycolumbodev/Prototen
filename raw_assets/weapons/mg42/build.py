"""MG42-style belt-fed machine gun, 7.62x51 (.308), chrome and black steel.

Owner brief (2026-11-01): "MG42 light gun", chrome and black steel, 1,200 rpm,
.308-class round, built for an augmented carrier (docs/design.md §4.2).

Real proportions: ~1.22 m long, 533 mm barrel inside a perforated jacket with
the barrel-change window on the right, muzzle booster, folding bipod, top
feed cover hinged at the rear, downward ejection, cocking handle on the right,
angled stock. Additions for the carrier: a clamp-on vertical foregrip (hip
fire), a 150-round box on the left feeding a short visible belt, and the
Fire-Control Link readout on the left of the receiver (docs/design.md §3.5).

Finish: polished chrome receiver, jacket and trunnion; blackened steel cover,
grip, stock, booster, bipod, sights and box.

The pistol grip/trigger group uses the same profile and position as the
Pistol 57 frame, so the firing hand from the pistol arms fits it exactly.

Pipeline (CLAUDE.md §7): HIGH and LOW built from the same code, LOW unwrapped,
HIGH baked onto LOW (bakeutil), LOW split into parts by a per-face part id
(body / cover / magazine / belt / stock), exported as one glTF.

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/mg42/build.py --out assets/weapons/mg42/mg42.gltf --tex 4096 \
      --preview docs/previews/mg42.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/mg42.png
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
ap.add_argument("--emission-size", type=int, default=512, help="emission map is mostly black: store it small")
ap.add_argument("--preview", default="", help="preview sheet stem; renders <stem>_side/_beauty/_receiver/_fp.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material

# ---------------------------------------------------------------- materials
M_CHROME = mat("chrome", (0.88, 0.89, 0.9), 0.07, 1.0, wear=(0.6, 0.6, 0.62), wear_rough=0.22,
               brushed=0.025, bump_scale=1200, bump_strength=0.015)
M_BLACK = mat("black_steel", (0.022, 0.023, 0.025), 0.4, 0.75, wear=(0.42, 0.43, 0.45), wear_rough=0.22,
              brushed=0.03, bump_scale=900, bump_strength=0.04)
M_FURN = mat("black_furniture", (0.02, 0.02, 0.022), 0.6, 0.15, wear=(0.3, 0.3, 0.32), wear_rough=0.3,
             bump_scale=1500, bump_strength=0.16)
M_BLUED = mat("barrel_blued", (0.05, 0.05, 0.065), 0.42, 1.0)
M_BRASS = mat("brass", (0.78, 0.56, 0.24), 0.26, 1.0, wear=(0.9, 0.75, 0.45), wear_rough=0.15)
M_COPPER = mat("gilding_metal", (0.72, 0.38, 0.22), 0.3, 1.0)
M_GLASS = mat("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = mat("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_PAINT = mat("stencil_paint", (0.62, 0.5, 0.12), 0.65, 0.0)
M_MARK = mat("engraving", (0.28, 0.29, 0.3), 0.45, 1.0)
M_RUBBER = mat("rubber", (0.02, 0.02, 0.021), 0.85, 0.0, bump_scale=600, bump_strength=0.3)
MATERIALS = [M_CHROME, M_BLACK, M_FURN, M_BLUED, M_BRASS, M_COPPER, M_GLASS, M_AMBER, M_PAINT, M_MARK, M_RUBBER]

# ---------------------------------------------------------------- dimensions
REC_X0, REC_X1 = -0.175, 0.125      # receiver
REC_HW = 0.027                       # receiver half width
REC_Z0, REC_Z1 = -0.032, 0.029       # receiver bottom/top (the cover sits on top from 0.030)
COVER_X0, COVER_X1 = -0.168, 0.100
JK_X0, JK_X1 = 0.125, 0.505          # barrel jacket
JK_R, JK_T = 0.0245, 0.0016          # jacket radius, wall thickness
SIGHT_Z = 0.0615                     # sight line (rear leaf top = front post top)
FEED_X0, FEED_X1 = -0.022, 0.058     # feed opening in the left wall
CART_X0 = -0.0185                    # rear of a belted cartridge (71 mm long)
PART_IDS = {"body": 0, "cover": 1, "magazine": 2, "belt": 3, "stock": 4}
CURRENT = ["body"]
PART_OF = {}                         # object name -> part


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


# ---------------------------------------------------------------- receiver
def build_receiver():
    # Built from plates around a dark core so the feed opening and the cocking slot are real
    # openings without booleans on the big flat walls (booleans there shaded badly).
    T = 0.0025                      # wall thickness
    IN = REC_HW - T
    Z0W = REC_Z0 + 0.005            # walls start above the chamfered bottom
    FZ0, FZ1 = 0.0035, 0.0275       # feed opening height
    CZ0, CZ1 = 0.0015, 0.0068       # cocking slot height
    CX0, CX1 = -0.073, 0.097
    finish(hs.section("rec_core", [(-IN, REC_Z0 + 0.002), (IN, REC_Z0 + 0.002), (IN, REC_Z1), (-IN, REC_Z1)],
                      REC_X0 + 0.001, REC_X1 - 0.001), M_BLUED, bevel=0)
    finish(hs.section("rec_bottom", [(-0.022, REC_Z0), (0.022, REC_Z0), (REC_HW, Z0W), (-REC_HW, Z0W)], REC_X0, REC_X1),
           M_CHROME, bevel=0.0008)

    def wall(name, side, x0, x1, z0, z1):
        y0 = IN if side > 0 else -REC_HW
        finish(hs.box(name, (x1 - x0, T, z1 - z0), ((x0 + x1) / 2, y0 + T / 2, (z0 + z1) / 2)), M_CHROME, bevel=0.0007)

    # Left wall around the feed opening.
    wall("wl_low", 1, REC_X0, REC_X1, Z0W, FZ0)
    wall("wl_high", 1, REC_X0, REC_X1, FZ1, REC_Z1)
    wall("wl_rear", 1, REC_X0, FEED_X0, FZ0, FZ1)
    wall("wl_front", 1, FEED_X1, REC_X1, FZ0, FZ1)
    # Right wall around the cocking slot.
    wall("wr_low", -1, REC_X0, REC_X1, Z0W, CZ0)
    wall("wr_high", -1, REC_X0, REC_X1, CZ1, REC_Z1)
    wall("wr_rear", -1, REC_X0, CX0, CZ0, CZ1)
    wall("wr_front", -1, CX1, REC_X1, CZ0, CZ1)
    # Top deck ahead of the cover, and the ejection port plate underneath.
    finish(hs.box("rec_deck", (REC_X1 - COVER_X1 + 0.004, 2 * REC_HW, 0.002), ((REC_X1 + COVER_X1) / 2, 0, REC_Z1 - 0.001)),
           M_CHROME, bevel=0.0006)
    finish(hs.box("eject_port", (0.06, 0.02, 0.0016), (0.058, 0, REC_Z0 - 0.0004)), M_BLUED, bevel=0.0004)
    # Raised stamped panels behind the feed area.
    pan = hs.box("side_panel", (0.07, 0.0012, 0.016), (-0.112, REC_HW + 0.0006, -0.010))
    hs.mirror_y(pan)
    finish(pan, M_CHROME, bevel=0.0005)

    # Pressed reinforcement ridge along both sides.
    ridge = hs.box("ridge", (0.29, 0.0016, 0.0035), (-0.025, REC_HW + 0.0006, -0.022))
    hs.mirror_y(ridge)
    finish(ridge, M_CHROME, bevel=0.0005)

    # Rivets (kept out of the box/bracket region on the left).
    for x, z in ((-0.155, 0.021), (-0.10, 0.021), (-0.065, 0.021), (0.085, 0.021), (0.11, 0.021),
                 (-0.155, -0.026), (-0.068, -0.026), (0.112, -0.026)):
        for sy in (-1, 1):
            if sy < 0 and abs(x - 0.03) < 0.075 and z > 0:
                continue  # cocking slot on the right
            r = hs.cyl_y(f"rivet_{x}_{z}_{sy}", 0.0021, 0.0024, (x, sy * (REC_HW + 0.0004), z), verts=16)
            finish(r, M_CHROME, bevel=0.0006, segments=2)

    # Front trunnion collar into the jacket.
    finish(hs.lathe_x("trunnion", [(0.112, 0.0275), (0.116, 0.0292), (0.136, 0.0292), (0.140, 0.0262)], verts=48),
           M_CHROME, bevel=0.0006)
    # Rear end cap / buffer and the stock latch.
    finish(hs.section("end_cap", [(-0.025, -0.030), (0.025, -0.030), (0.0275, 0.0), (0.025, 0.031), (-0.025, 0.031),
                                  (-0.0275, 0.0)], REC_X0 - 0.012, REC_X0 + 0.002), M_BLACK, bevel=0.0012)
    finish(hs.box("stock_latch", (0.014, 0.012, 0.010), (REC_X0 - 0.004, 0, REC_Z0 - 0.003)), M_BLACK, bevel=0.0008)

    # Cocking handle: stem through the slot, knurled knob.
    finish(hs.box("cock_stem", (0.008, 0.016, 0.0045), (0.088, -REC_HW - 0.006, 0.004)), M_BLACK, bevel=0.0006)
    knob = hs.cyl_z("cock_knob", 0.0062, 0.013, (0.088, -REC_HW - 0.016, 0.004), verts=24)
    finish(knob, M_BLACK, bevel=0.0012, segments=3)

    # Feed tray lip under the belt entry.
    finish(hs.box("feed_lip", (FEED_X1 - FEED_X0 + 0.006, 0.006, 0.003), ((FEED_X0 + FEED_X1) / 2, REC_HW + 0.002, 0.0025)),
           M_BLACK, bevel=0.0006)
    # Belt guide pawls visible in the opening.
    for i, x in enumerate((-0.004, 0.036)):
        finish(hs.box(f"feed_pawl{i}", (0.006, 0.010, 0.006), (x, REC_HW - 0.006, 0.022)), M_BLACK, bevel=0.0005)

    # Fire-Control Link readout (left rear) and markings.
    finish(hs.box("fcl_glass", (0.032, 0.0014, 0.011), (-0.135, REC_HW + 0.0005, 0.009)), M_GLASS, bevel=0.0004)
    for i, w in enumerate((0.005, 0.008, 0.003, 0.006, 0.004)):
        finish(hs.box(f"fcl_seg{i}", (w, 0.0004, 0.0014), (-0.148 + i * 0.0058 + w / 2, REC_HW + 0.0013, 0.0115)),
               M_AMBER, bevel=0)
    finish(hs.box("fcl_bar", (0.022, 0.0004, 0.0008), (-0.138, REC_HW + 0.0013, 0.0065)), M_AMBER, bevel=0)
    # Left side: reads front-to-back from the left (rotation flips the text to face +Y).
    text("mark_left", "MG 42/A   7,62x51", 0.0058, (0.100, REC_HW + 0.0001, -0.0175), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_serial", "GRF 0417", 0.0042, (-0.105, REC_HW + 0.0001, 0.0175), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_right", "S  F", 0.006, (-0.05, -REC_HW - 0.0001, -0.019), (math.pi / 2, 0, 0), M_MARK)


def build_cover():
    part("cover")
    cover = hs.section("cover", [(-0.0275, 0.030), (0.0275, 0.030), (0.0275, 0.036), (0.020, 0.0445),
                                 (-0.020, 0.0445), (-0.0275, 0.036)], COVER_X0, COVER_X1)
    hs.cut(cover, hs.box("cover_nose", (0.04, 0.08, 0.03), (COVER_X1 + 0.012, 0, 0.047), (0, math.radians(35), 0)))
    finish(cover, M_BLACK, bevel=0.0009)
    rib = hs.box("cover_rib", (0.205, 0.0045, 0.0018), (-0.04, 0.0105, 0.0452))
    hs.mirror_y(rib)
    finish(rib, M_BLACK, bevel=0.0006)
    # Hinge knuckles at the rear, latch at the front.
    for i, (y, w) in enumerate(((-0.019, 0.012), (0.0, 0.016), (0.019, 0.012))):
        k = hs.cyl_y(f"hinge{i}", 0.0048, w - 0.001, (COVER_X0 - 0.002, y, 0.037), verts=24)
        finish(k, M_BLACK, bevel=0.0006, segments=2)
    finish(hs.box("cover_latch", (0.012, 0.018, 0.006), (COVER_X1 - 0.016, 0, 0.040)), M_BLACK, bevel=0.0009)
    finish(hs.cyl_y("latch_pin", 0.0022, 0.06, (COVER_X1 - 0.016, 0, 0.034), verts=16), M_CHROME, bevel=0.0004)
    part("body")


# ---------------------------------------------------------------- jacket, barrel, booster, sights
def build_barrel():
    jacket = hs.cyl_x("jacket", JK_R, JK_X0, JK_X1, verts=64)
    hs.cut(jacket, hs.cyl_x("jacket_bore", JK_R - JK_T, JK_X0 - 0.01, JK_X1 + 0.01, verts=64))

    def slot_row(name, angle_deg, x0, count, step, length, width):
        """Row of oval cooling slots at `angle` around the bore (0 = top, +90 = left, -90 = right)."""
        bpy.ops.mesh.primitive_cylinder_add(vertices=hs.nverts(24), radius=1.0, depth=0.03)
        c = bpy.context.active_object
        c.name = name
        c.scale = (length / 2, width / 2, 1.0)
        a = math.radians(angle_deg)
        c.rotation_euler = (-a, 0, 0)  # +Z turns to (0, sin a, cos a)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        c.location = (x0, math.sin(a) * JK_R, math.cos(a) * JK_R)
        hs.linear_array(c, count, (step, 0, 0))
        hs.cut(jacket, c)

    slot_row("slots_top", 0, 0.160, 8, 0.042, 0.016, 0.0105)
    slot_row("slots_upper_left", 55, 0.170, 7, 0.046, 0.030, 0.0115)
    slot_row("slots_lower_left", 120, 0.170, 7, 0.046, 0.030, 0.0115)
    slot_row("slots_bottom", 180, 0.240, 5, 0.046, 0.012, 0.009)
    slot_row("slots_lower_right", -130, 0.420, 2, 0.040, 0.022, 0.010)
    # Barrel-change window, right side.
    hs.cut(jacket, hs.box("bc_window", (0.25, 0.03, 0.022), (0.285, -JK_R, 0.0)))
    finish(jacket, M_CHROME, bevel=0.0005, segments=2)

    # Jacket front bushing and the bands where the bipod and foregrip clamp.
    finish(hs.lathe_x("jk_front", [(0.495, 0.0258), (0.497, 0.0266), (0.512, 0.0266), (0.514, 0.0258)], verts=64),
           M_CHROME, bevel=0.0004)
    # Barrel (blued) visible through the slots; barrel bearing ring near the front.
    finish(hs.cyl_x("barrel", 0.0088, 0.12, 0.52, verts=32), M_BLUED, bevel=0.0003)
    finish(hs.cyl_x("barrel_ring", 0.0125, 0.475, 0.49, verts=32), M_BLUED, bevel=0.0004)
    # Barrel-change catch (right rear of the jacket).
    finish(hs.box("bc_catch", (0.028, 0.006, 0.012), (0.146, -JK_R - 0.002, 0.004)), M_BLACK, bevel=0.0008)
    finish(hs.cyl_y("bc_catch_knob", 0.004, 0.008, (0.158, -JK_R - 0.007, 0.004), verts=16), M_BLACK, bevel=0.0008)

    # Muzzle booster and flash cone.
    booster = hs.lathe_x("booster", [(0.512, 0.0215), (0.518, 0.0222), (0.552, 0.0222), (0.556, 0.0232),
                                     (0.562, 0.0232), (0.586, 0.0188), (0.600, 0.0168)], verts=48)
    hs.cut(booster, hs.cyl_x("booster_bore", 0.0062, 0.50, 0.61, verts=24))
    vent = hs.box("booster_vent", (0.012, 0.0042, 0.008), (0.535, 0, 0.0222))
    hs.radial_array(vent, 6, 0.535)
    hs.cut(booster, vent)
    finish(booster, M_BLACK, bevel=0.0007)
    finish(hs.cyl_x("muzzle_bore_dark", 0.0061, 0.585, 0.596, verts=24), M_BLUED, bevel=0)

    # Rear sight: base on the jacket, leaf with a U notch, range slider.
    finish(hs.box("rs_base", (0.036, 0.020, 0.010), (0.155, 0, 0.0265)), M_BLACK, bevel=0.0008)
    leaf = hs.box("rs_leaf", (0.004, 0.019, SIGHT_Z - 0.028), (0.152, 0, (SIGHT_Z + 0.028) / 2))
    hs.cut(leaf, hs.box("rs_notch", (0.02, 0.0036, 0.014), (0.152, 0, SIGHT_Z + 0.001)))
    finish(leaf, M_BLACK, bevel=0.0004)
    finish(hs.box("rs_slider", (0.008, 0.022, 0.005), (0.152, 0, 0.040)), M_BLACK, bevel=0.0006)
    finish(hs.box("rs_dot", (0.0008, 0.0016, 0.0016), (0.1497, 0, SIGHT_Z - 0.0075)), M_AMBER, bevel=0)

    # Front sight: base, post, protective ears.
    finish(hs.box("fs_base", (0.018, 0.018, 0.010), (0.486, 0, 0.0265)), M_BLACK, bevel=0.0008)
    finish(hs.box("fs_post", (0.0035, 0.0024, SIGHT_Z - 0.029), (0.486, 0, (SIGHT_Z + 0.029) / 2)), M_BLACK, bevel=0.0003)
    for sy in (-1, 1):
        ear = hs.box(f"fs_ear{sy}", (0.012, 0.002, SIGHT_Z - 0.026), (0.486, sy * 0.0085, (SIGHT_Z + 0.026) / 2 + 0.001))
        finish(ear, M_BLACK, bevel=0.0005)
    finish(hs.box("fs_dot", (0.0008, 0.0016, 0.0016), (0.4842, 0, SIGHT_Z - 0.0012)), M_AMBER, bevel=0)

    # Bipod (folded back under the jacket).
    finish(hs.lathe_x("bp_collar", [(0.452, 0.0262), (0.453, 0.0274), (0.469, 0.0274), (0.470, 0.0262)], verts=48),
           M_BLACK, bevel=0.0004)
    finish(hs.box("bp_hinge", (0.018, 0.026, 0.010), (0.461, 0, -0.030)), M_BLACK, bevel=0.0009)
    for sy in (-1, 1):
        finish(hs.cyl_between(f"bp_leg{sy}", (0.458, sy * 0.010, -0.034), (0.29, sy * 0.016, -0.0345), 0.0034, verts=16),
               M_BLACK, bevel=0.0003)
        finish(hs.box(f"bp_foot{sy}", (0.022, 0.012, 0.004), (0.289, sy * 0.017, -0.0365), (0, math.radians(-6), 0)),
               M_BLACK, bevel=0.0008)
    finish(hs.cyl_between("bp_brace", (0.40, -0.012, -0.035), (0.40, 0.012, -0.035), 0.0022, verts=12), M_BLACK, bevel=0)

    # Clamp-on vertical foregrip (carrier modification).
    clamp = hs.lathe_x("fg_clamp", [(0.186, 0.0255), (0.187, 0.0285), (0.217, 0.0285), (0.218, 0.0255)], verts=48)
    finish(clamp, M_BLACK, bevel=0.0005)
    finish(hs.box("fg_block", (0.026, 0.022, 0.014), (0.202, 0, -0.031)), M_BLACK, bevel=0.0012)
    finish(hs.cyl_y("fg_bolt", 0.003, 0.064, (0.202, 0, -0.029), verts=16), M_CHROME, bevel=0.0004)
    grip = hs.cyl_between("fg_grip", (0.203, 0, -0.036), (0.211, 0, -0.130), 0.0165, verts=32)
    for i in range(4):
        z = -0.056 - i * 0.021
        bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(32), minor_segments=8, major_radius=0.0172,
                                         minor_radius=0.0021, location=(0.203 + (z + 0.036) / -0.094 * 0.008, 0, z))
        hs.cut(grip, bpy.context.active_object)
    finish(grip, M_FURN, bevel=0.0012)
    finish(hs.cyl_between("fg_cap", (0.211, 0, -0.128), (0.2117, 0, -0.136), 0.0176, verts=32), M_BLACK, bevel=0.0015)


# ---------------------------------------------------------------- grip, trigger, stock
def loft_x(name, stations, n=None, power=5.0):
    """Closed loft along X through rounded-rectangle (superellipse) sections."""
    n = n or hs.nverts(40)
    bm = bmesh.new()
    rings = []
    for x, zt, zb, hw in stations:
        zc, hh = (zt + zb) / 2, (zt - zb) / 2
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            c, sn = math.cos(t), math.sin(t)
            yy = hw * math.copysign(abs(c) ** (2 / power), c)
            zz = zc + hh * math.copysign(abs(sn) ** (2 / power), sn)
            ring.append(bm.verts.new((x, yy, zz)))
        rings.append(ring)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def build_lower():
    # Trigger group + pistol grip: same profile/placement as the Pistol 57 frame below the slide.
    grip = hs.side_profile("grip", [
        (0.044, REC_Z0 + 0.001), (0.047, -0.052), (0.040, -0.061), (-0.020, -0.061), (-0.027, -0.054),
        (-0.056, -0.134), (-0.061, -0.138), (-0.103, -0.138), (-0.107, -0.132), (-0.081, -0.046),
        (-0.095, REC_Z0 + 0.001)], 0.030)
    hs.cut(grip, hs.side_profile("guard_hole", [(-0.018, -0.0345), (0.037, -0.0345), (0.039, -0.050), (0.033, -0.0555),
                                                (-0.014, -0.0555), (-0.023, -0.046)], 0.05))
    groove = hs.cyl_y("finger_groove", 0.0068, 0.06, (-0.0300, 0, -0.0745), verts=32)
    hs.linear_array(groove, 3, (-0.0071, 0, -0.0197))
    hs.cut(grip, groove)
    finish(grip, M_FURN, bevel=0.0012)
    finish(hs.side_profile("grip_cap", [(-0.058, -0.137), (-0.105, -0.137), (-0.108, -0.1445), (-0.055, -0.1445)], 0.027),
           M_BLACK, bevel=0.0008)
    finish(hs.side_profile("trigger", [(0.012, -0.033), (0.018, -0.033), (0.016, -0.041), (0.021, -0.051),
                                       (0.015, -0.053), (0.008, -0.041)], 0.0055), M_CHROME, bevel=0.0005)
    # Cross-bolt safety above the grip.
    finish(hs.cyl_y("safety", 0.0042, 0.038, (-0.030, 0, -0.038), verts=24), M_BLACK, bevel=0.0008)

    # Stock: tapered, angled down, rubber butt pad, chrome joint ring.
    # The stock is its own part: the viewmodel hides it while aiming (it would sit against the cheek).
    part("stock")
    # (x, top z, bottom z, half width), rear to front.
    stock = loft_x("stock", [(-0.552, 0.002, -0.128, 0.0195), (-0.537, 0.005, -0.127, 0.021),
                             (-0.50, 0.007, -0.117, 0.0215), (-0.43, 0.011, -0.096, 0.021),
                             (-0.33, 0.016, -0.069, 0.0205), (-0.25, 0.022, -0.047, 0.0205),
                             (REC_X0 - 0.010, 0.026, -0.031, 0.0215)])
    finish(stock, M_FURN, bevel=0.002, segments=2, angle=60)
    finish(loft_x("butt_pad", [(-0.566, -0.001, -0.125, 0.017), (-0.5515, 0.002, -0.128, 0.0192)]),
           M_RUBBER, bevel=0.0015, segments=2, angle=60)
    finish(hs.side_profile("stock_rest", [(-0.42, 0.0105), (-0.52, 0.0055), (-0.52, 0.010), (-0.42, 0.0155)], 0.030),
           M_BLACK, bevel=0.0012)
    finish(hs.cyl_y("sling_swivel", 0.006, 0.006, (-0.47, 0, -0.118), verts=20), M_CHROME, bevel=0.0008)
    part("body")


# ---------------------------------------------------------------- ammo box and belt
BOX_X0, BOX_X1 = -0.048, 0.086
BOX_Y0, BOX_Y1 = 0.031, 0.083
BOX_Z0, BOX_Z1 = -0.126, -0.016


def build_box():
    part("magazine")
    bx = hs.box("ammo_box", (BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_Z1 - BOX_Z0),
                ((BOX_X0 + BOX_X1) / 2, (BOX_Y0 + BOX_Y1) / 2, (BOX_Z0 + BOX_Z1) / 2))
    hs.cut(bx, hs.box("box_mouth", (0.078, 0.026, 0.02), (0.018, 0.058, BOX_Z1)))
    finish(bx, M_BLACK, bevel=0.0018)
    # Stamped ribs on the outer face, lid seam, latch, handle.
    for i, z in enumerate((-0.050, -0.098)):
        finish(hs.box(f"box_rib{i}", (0.12, 0.002, 0.006), (0.019, BOX_Y1 + 0.0006, z)), M_BLACK, bevel=0.0008)
    finish(hs.box("box_lid", (BOX_X1 - BOX_X0 + 0.003, BOX_Y1 - BOX_Y0 + 0.003, 0.004),
                  ((BOX_X0 + BOX_X1) / 2, (BOX_Y0 + BOX_Y1) / 2, BOX_Z1 - 0.008)), M_BLACK, bevel=0.0012)
    finish(hs.box("box_latch", (0.006, 0.010, 0.016), (BOX_X1 + 0.0025, 0.067, -0.030)), M_CHROME, bevel=0.0008)
    finish(hs.cyl_between("box_handle", (-0.03, BOX_Y1 + 0.006, -0.124), (0.07, BOX_Y1 + 0.006, -0.124), 0.0028,
                          verts=12), M_BLACK, bevel=0)
    # Mounting rail into the receiver's left side.
    finish(hs.box("box_rail", (0.07, BOX_Y0 - REC_HW + 0.001, 0.016), (0.02, (BOX_Y0 + REC_HW) / 2, -0.024)),
           M_BLACK, bevel=0.0008)
    # Stencil on the outer face (bake only).
    text("box_stencil", "7.62 x 51   150", 0.0085, (0.072, BOX_Y1 + 0.0001, -0.080), (math.pi / 2, 0, math.pi), M_PAINT)
    text("box_stencil2", "LINKED  4:1  T", 0.0055, (0.072, BOX_Y1 + 0.0001, -0.068), (math.pi / 2, 0, math.pi), M_PAINT)
    # Rounds waiting in the mouth.
    for i, y in enumerate((0.048, 0.062)):
        cartridge(f"box_round{i}", V((0.0, y, BOX_Z1 - 0.004)), links=True)
    part("body")


def cartridge(name, centre_yz, links=True):
    """A belted .308 round, axis along +X, at (y, z) of `centre_yz` (x ignored)."""
    y, z = centre_yz.y, centre_yz.z
    case = hs.lathe_x(f"{name}_case", [(CART_X0, 0.0050), (CART_X0 + 0.0008, 0.0060), (CART_X0 + 0.0016, 0.0060),
                                       (CART_X0 + 0.0020, 0.0051), (CART_X0 + 0.0030, 0.0051), (CART_X0 + 0.0036, 0.0059),
                                       (CART_X0 + 0.0390, 0.0057), (CART_X0 + 0.0430, 0.0044),
                                       (CART_X0 + 0.0505, 0.0044)], verts=20)
    case.location = (0, y, z)
    finish(case, M_BRASS, bevel=0, smooth=True)
    bullet = hs.lathe_x(f"{name}_bullet", [(CART_X0 + 0.0500, 0.0039), (CART_X0 + 0.0560, 0.0039),
                                           (CART_X0 + 0.0640, 0.0030), (CART_X0 + 0.0690, 0.0015),
                                           (CART_X0 + 0.0712, 0.0005)], verts=16)
    bullet.location = (0, y, z)
    finish(bullet, M_COPPER, bevel=0, smooth=True)
    if links:
        link = hs.lathe_x(f"{name}_link", [(CART_X0 + 0.010, 0.0063), (CART_X0 + 0.018, 0.0063)], verts=16)
        link.location = (0, y, z)
        finish(link, M_BLACK, bevel=0)
        link2 = hs.lathe_x(f"{name}_link2", [(CART_X0 + 0.031, 0.0062), (CART_X0 + 0.037, 0.0062)], verts=16)
        link2.location = (0, y, z)
        finish(link2, M_BLACK, bevel=0)


def bezier(p0, p1, p2, t):
    return p0 * (1 - t) ** 2 + p1 * 2 * (1 - t) * t + p2 * t * t


def build_belt():
    """Short belt from the box mouth up into the feed opening, rounds 12.6 mm apart."""
    part("belt")
    p0, p1, p2 = V((0, 0.020, 0.0125)), V((0, 0.085, 0.020)), V((0, 0.060, BOX_Z1 - 0.003))
    pts = [bezier(p0, p1, p2, i / 400) for i in range(401)]
    pitch, acc, last = 0.0126, 0.0, pts[0]
    centres = [pts[0]]
    for p in pts[1:]:
        acc += (p - last).length
        last = p
        if acc >= pitch:
            centres.append(p)
            acc = 0.0
    centres = centres[:-1]  # the last one would sit in the box mouth's lip
    for i, c in enumerate(centres):
        cartridge(f"belt{i}", c)
        if i + 1 < len(centres):
            n = centres[i + 1]
            # Connecting strap between neighbouring links.
            finish(hs.cyl_between(f"belt_strap{i}", (CART_X0 + 0.014, c.y, c.z), (CART_X0 + 0.014, n.y, n.z), 0.0016,
                                  verts=8), M_BLACK, bevel=0)
    part("body")
    return len(centres)


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_receiver()
    build_cover()
    build_barrel()
    build_lower()
    build_box()
    rounds = build_belt()
    # Per-face part id, so the baked LOW mesh can be split into moving parts.
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
    print(f"mg42 {detail['name']}: {bakeutil.tri_count(joined)} tris, {rounds} belt rounds")
    return joined


def split_parts(low):
    """Separates LOW into one object per part id (shared material)."""
    objs = []
    ids = list(low.data.attributes["part_id"].data)
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
        print(f"mg42: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    # Studio world: dark with a soft bright band, so chrome has something to reflect.
    world = bpy.data.worlds.new("studio")
    nt = world.node_tree
    bg = nt.nodes["Background"]
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "LINEAR"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.007, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.12, 0.125, 0.135, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world

    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, -0.16)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.0, 0, -0.03), shape="RECTANGLE", sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = shape
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.4, -1.2, 1.1), 45, 1.6, sy=0.5)
    area("strip_top", (0.05, 0.0, 1.1), 30, 2.2, sy=0.18)
    area("fill", (0.4, 1.3, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.4, -0.4, 0.5), 45, 0.8, (1.0, 0.82, 0.62))
    area("kick", (-1.4, 0.3, 0.2), 25, 1.0, (0.9, 0.95, 1.0))
    cam_data = bpy.data.cameras.new("cam")
    cam = hs.link(bpy.data.objects.new("cam", cam_data))
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
    print(f"mg42: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shoot(cam, stem + "_side.png", (0.0, -2.4, 0.0), (0.0, 0, -0.03), lens=55)
    shoot(cam, stem + "_beauty.png", (0.65, -0.95, 0.42), (0.03, 0, -0.03), lens=50, fstop=8.0)
    shoot(cam, stem + "_left.png", (-0.25, 1.05, 0.38), (0.06, 0, -0.04), lens=45, fstop=8.0)
    shoot(cam, stem + "_receiver.png", (-0.30, 0.30, 0.20), (0.02, 0.02, -0.01), lens=50, fstop=4.0)
    # Roughly what the player sees: eye behind/above the receiver, gun to the lower right.
    shoot(cam, stem + "_fp.png", (-0.36, 0.09, 0.15), (0.6, -0.02, -0.06), fov_deg=60)


# ---------------------------------------------------------------- run
if args.out:
    high = build(hs.HIGH, "mg42_high")
    low = build(hs.LOW, "mg42_low")
    # Texel density: the receiver/cover/sights get the most (always on screen), the stock the least.
    bakeutil.unwrap(low, boost={M_FURN.name: 0.75, M_BRASS.name: 1.4, M_COPPER.name: 1.4, M_BLACK.name: 1.1,
                                M_PAINT.name: 1.5, M_MARK.name: 1.5})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "mg42", cage=0.0012, ray=0.004,
                                 ao_distance=0.03, grime=0.35, log=print)
    bpy.data.objects.remove(high)
    # The emission map only carries the readout: store it small.
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "mg42", emission_strength=4.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"mg42: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "mg42_high")
    render_previews(args.preview.rsplit(".", 1)[0])
