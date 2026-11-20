"""Steyr AUG A1 (Austrian Army StG 77 pattern): 5.56 mm bullpup assault rifle
with the integral 1.5x scope, the folding vertical foregrip and the clear
30-round magazine.

Owner brief (2026-11-20): "a really awesome AUG model ... super realistic. If
you need to look at reference pictures and superimpose them, do that."

Traced, not guessed: every outline below is in pixels of the reference photo
"Steyr AUG 5,56 mm.JPG" (MoserB, Wikimedia Commons, public domain; a left-side
shot of an StG 77 on a plain floor, the bore horizontal on row 1000), read off
zoomed crops at 4.82 px/mm (790 mm overall, muzzle at x 5, butt at x 3818).
`P(px, py)` turns them into metres. `--overlay` renders an orthographic left
view on top of the photo to check the match.

Built: the olive polymer stock is one signed-distance sculpt (raw_assets/_lib/
sdf.py) of the traced side outline, extruded with a width that changes along
the gun (narrow under the receiver, full at the cheek and magazine well, slim
grip, slimmer trigger-guard strut and bar) and rounded on every edge. The
trigger guard encloses the whole hand, as on the real gun. Black-painted
aluminium receiver with the two lightening slots and the cocking-handle slot,
the cast carry handle and the 1.5x scope on it (hex adjuster caps top and
bottom, recessed objective and eyepiece glass). Ribbed barrel, gas block with
its regulator, the three-prong flash hider on its nut, the hinged vertical
foregrip on the barrel. Crossbolt safety, takedown button, ejection port (open
on the right with the bolt behind it, covered by the strip on the left),
magazine catch behind the well, butt plate seam, both sling swivels, the
big trigger.

The magazine is clear polymer, so it is three things: the baked floor plate
and top (`magazine`), a see-through shell (`mag_shell`, no bake; the game
gives it an amber glass material) and the 30 rounds inside it as one mesh
(`mag_rounds`, no bake). Each round's UV.x is its slot from the top (0..29)
plus 0.25 for brass and 0.75 for the copper bullet, so the game's shader
hides the rounds that have been fired; the follower (`mag_follower`) rides up
the arc under the last one. `mag_*` are children of `magazine`, so they leave
with it on a reload.

Moving parts (separate nodes in the glTF, see src/player/viewmodel_rig.gd):
  body             everything that doesn't move
  magazine         drops on reload (floor plate and top; the shell, rounds and follower ride on it)
  charging_handle  the folding cocking handle on the left (runs back along its slot)
  mag_follower     the magazine follower (turns about MAG_CENTER as rounds are used)
  mag_shell        the clear magazine body (unbaked)
  mag_rounds       30 x 5.56 mm (unbaked, slot-coded UVs)

The pistol grip sits on the Pistol 57 grip line (top (-0.054, -0.050), 20
degree rake) so the arms builder's hand fits it; the AUG grip is slimmer
front to back (39 mm), see raw_assets/characters/fp_arms_aug/build.py.

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/aug/build.py --out assets/weapons/aug/aug.gltf --tex 4096 \
      --preview docs/previews/aug.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/aug.png [--only side,fp] [--fast]
  Photo match: --overlay /tmp/aug_overlay.png --photo <path to the reference photo>
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402
import sdf  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--emission-size", type=int, default=512)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
ap.add_argument("--fast", action="store_true", help="coarse sculpt and few samples (look only)")
ap.add_argument("--overlay", default="", help="render the left view for the photo match to this png")
ap.add_argument("--hide", default="", help="comma list of objects to hide in previews")
ap.add_argument("--low-tris", type=int, default=4600, help="stock triangles in LOW")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
PI = math.pi
F32 = np.float32

# ---------------------------------------------------------------- materials
# Steyr olive: a grey-green, slightly brown polymer, satin, a fine moulded grain.
OLIVE = (0.040, 0.041, 0.026)
M_STOCK = mat("olive_polymer", OLIVE, 0.58, 0.0, bump_scale=2600, bump_strength=0.10)
M_STOCK_WORN = mat("olive_polymer_worn", OLIVE, 0.5, 0.0, wear=(0.15, 0.155, 0.12), wear_rough=0.38,
                   bump_scale=2600, bump_strength=0.10)
# Black paint over cast aluminium. The edge-wear mask (pointiness) spreads across the big flat faces
# of these sparse hard-surface meshes, so the wear here is only a slightly lighter, smoother black;
# the scope tube (dense mesh) keeps its rubbed-through edges.
M_ALU = mat("black_paint_alu", (0.014, 0.014, 0.016), 0.5, 0.1, wear=(0.075, 0.075, 0.08), wear_rough=0.38,
            bump_scale=1700, bump_strength=0.05)
M_SCOPE = mat("scope_black", (0.016, 0.016, 0.018), 0.36, 0.4, wear=(0.56, 0.56, 0.58), wear_rough=0.25,
              bump_scale=1500, bump_strength=0.04)
M_STEEL = mat("phosphate_steel", (0.020, 0.020, 0.022), 0.55, 0.6, wear=(0.09, 0.09, 0.095), wear_rough=0.36,
              brushed=0.03, bump_scale=1400, bump_strength=0.05)
M_BRIGHT = mat("bright_steel", (0.50, 0.50, 0.52), 0.25, 1.0, brushed=0.04)
M_BORE = mat("bore_dark", (0.010, 0.010, 0.011), 0.5, 1.0)
M_BLACKPOLY = mat("black_polymer", (0.018, 0.018, 0.020), 0.55, 0.0, wear=(0.08, 0.08, 0.085), wear_rough=0.4,
                  bump_scale=2000, bump_strength=0.1)
M_LENS = mat("lens_coated", (0.010, 0.016, 0.022), 0.03, 0.0)
M_MARK = mat("engraving", (0.45, 0.45, 0.46), 0.45, 0.7)
M_PAINT = mat("index_paint", (0.82, 0.80, 0.74), 0.6, 0.0)
M_REDPAINT = mat("red_paint", (0.60, 0.03, 0.02), 0.55, 0.0)
M_BRASS = mat("brass", (0.80, 0.58, 0.28), 0.26, 1.0)
M_COPPER = mat("copper_jacket", (0.72, 0.38, 0.22), 0.3, 1.0)
MATERIALS = [M_STOCK, M_STOCK_WORN, M_ALU, M_SCOPE, M_STEEL, M_BRIGHT, M_BORE, M_BLACKPOLY, M_LENS, M_MARK,
             M_PAINT, M_REDPAINT, M_BRASS, M_COPPER]


def shell_material():
    """The magazine shell outside the bake: smoky amber clear polymer."""
    m = bpy.data.materials.new("mag_clear")
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.75, 0.55, 0.28, 0.32)
    b.inputs["Alpha"].default_value = 0.32
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["IOR"].default_value = 1.45
    m.surface_render_method = "BLENDED"
    return m


# ---------------------------------------------------------------- the trace
PX_MM = 4.82          # photo pixels per millimetre
X0_PX = 1847          # photo x of the weapon origin (bore axis above the grip)
BORE_PY = 1000        # photo row of the bore axis


def P(px, py):
    """Photo pixel -> (x, z) in metres, weapon space."""
    return ((X0_PX - px) / PX_MM / 1000.0, (BORE_PY - py) / PX_MM / 1000.0)


def PX(px):
    return (X0_PX - px) / PX_MM / 1000.0


def PZ(py):
    return (BORE_PY - py) / PX_MM / 1000.0


# Stock side outline, clockwise from the front under the receiver: along the receiver's
# bottom, up its back, the cheek line, the butt, the toe, the underside, the magazine well,
# the hand opening behind the grip, the grip, the trigger-guard bar and its front strut.
STOCK_OUTLINE = [
    (1441, 1080), (1950, 1080), (1954, 1000), (1956, 915), (1966, 893), (1985, 884), (2010, 884), (2040, 896),
    (2080, 902), (2600, 902), (3200, 902), (3690, 902), (3735, 908), (3772, 930), (3800, 965), (3816, 1010),
    (3816, 1080), (3806, 1160), (3790, 1231), (3760, 1350), (3733, 1469), (3705, 1565), (3684, 1625),
    (3660, 1662), (3628, 1681), (3590, 1684), (3371, 1682), (3340, 1672), (3315, 1655), (3302, 1630),
    (3303, 1605), (3316, 1575), (3310, 1550), (3290, 1528), (3264, 1507), (3193, 1452), (3125, 1404),
    (3040, 1385), (2950, 1364), (2880, 1352), (2582, 1346), (2574, 1300), (2568, 1255), (2552, 1228),
    (2520, 1210), (2470, 1200), (2400, 1193), (2300, 1182), (2245, 1184), (2215, 1195), (2200, 1215),
    (2212, 1270), (2232, 1323), (2262, 1380), (2286, 1432), (2305, 1485), (2318, 1532), (2326, 1580),
    (2327, 1625), (2318, 1660), (2300, 1678), (2270, 1683), (2160, 1683), (2050, 1683), (1985, 1680),
    (1955, 1666), (1935, 1641), (1905, 1597), (1823, 1505), (1750, 1414), (1680, 1330), (1640, 1281),
    (1605, 1232), (1560, 1185), (1500, 1130),
]
# The trigger-guard opening (the whole hand goes through it).
GUARD_OPENING = [
    (1705, 1177), (1959, 1177), (1966, 1195), (1972, 1225), (1962, 1258), (1972, 1290), (2010, 1320),
    (2050, 1359), (2080, 1405), (2114, 1459), (2140, 1515), (2150, 1559), (2140, 1590), (2114, 1609),
    (1995, 1609), (1965, 1600), (1950, 1586), (1873, 1505), (1795, 1414), (1745, 1345), (1715, 1290),
    (1700, 1240), (1698, 1200),
]
# Strut and bar centre line (where the guard is slim).
GUARD_LINE = [(1649, 1262), (1772, 1414), (1848, 1505), (1927, 1595), (1955, 1636), (1990, 1645), (2085, 1645)]
# Cast carry handle under the scope: both legs, base on the receiver; then its window.
BRIDGE_OUTLINE = [
    (1548, 690), (1552, 704), (1525, 735), (1460, 790), (1400, 840), (1365, 862), (1335, 880), (1330, 945),
    (1962, 945), (1964, 872), (1975, 836), (2000, 800), (2040, 766), (2090, 736), (2140, 713), (2190, 700),
    (2200, 690),
]
BRIDGE_WINDOW = [(1630, 738), (1972, 740), (1888, 922), (1860, 934), (1460, 932), (1445, 908), (1446, 893)]
TRIGGER = [(1872, 1170), (1900, 1170), (1893, 1195), (1888, 1225), (1895, 1255), (1910, 1281), (1902, 1291),
           (1880, 1278), (1863, 1247), (1858, 1212), (1864, 1184)]
MAG_CATCH = [(2952, 1358), (3008, 1378), (3050, 1415), (3075, 1432), (3100, 1428), (3122, 1404), (3112, 1392),
             (3060, 1380)]

# Derived dimensions (metres).
SCOPE_Z = PZ(665)                       # scope axis, 69.7 mm over the bore
SCOPE_R = 0.0141
SCOPE_X0, SCOPE_X1 = PX(2550), PX(1555)  # eyepiece end / objective end
REC_X0, REC_X1 = PX(1960), PX(1250)      # receiver: into the stock / front face
REC_ZB, REC_ZT = PZ(1090), PZ(935)       # receiver bottom / top between the handle legs
REC_HW = 0.0190
SLOT_Z0, SLOT_Z1 = -0.0076, 0.0010       # cocking handle slot (left)
STOCK_TOP = PZ(902)
MAG_X0, MAG_X1 = PX(2582), PX(2876)      # magazine front / back at the well
MAG_MOUTH = PZ(1346)
MAG_HD = (MAG_X0 - MAG_X1) / 2           # half depth (61 mm)
MAG_HW = 0.0123
MAG_R = 0.55                             # spine radius
MAG_A0 = math.radians(8.5)               # lean at the well (the spine tilts the bottom forward)
MAG_S0, MAG_S1 = -0.026, 0.153           # shell top (inside the stock) / floor plate
MAG_FLOOR = 0.0135
MAG_PITCH = 0.0052                       # round centres along the spine (double stack)
MAG_STAGGER = 0.0040
MAG_CAP = 30
GRIP_TOP = (-0.054, -0.050)              # Pistol 57 grip line
FG_X = PX(1220)                           # foregrip centre
PART_IDS = {"body": 0, "magazine": 1, "charging_handle": 2, "mag_follower": 3}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def hi():
    return hs.D["text"]


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m=M_MARK, extrude=0.00012):
    ob = hs.text(name, body, size, loc, rot, m, extrude=extrude)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def traced(pts):
    return [P(*p) for p in pts]


def chaikin(pts, n=2):
    """Corner-cutting subdivision of a closed outline (smooths the traced polyline)."""
    p = np.asarray(pts, float)
    for _ in range(n):
        q = np.roll(p, -1, 0)
        p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p


def profile(name, pts, width, y=0.0, smooth=1):
    """Side outline (photo px) extruded across Y."""
    xz = chaikin(traced(pts), smooth) if smooth else traced(pts)
    return hs.side_profile(name, [tuple(p) for p in xz], width, y=y)


# ---------------------------------------------------------------- SDF helpers
def ss(e0, e1, t):
    t = np.clip((t - F32(e0)) / F32(e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rinter(a, b, r):
    """Intersection with a rounded edge of radius r."""
    a = a + F32(r)
    b = b + F32(r)
    return np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0) - F32(r)


def poly_sdf(x, z, V2):
    """Signed distance to a closed 2D polygon (negative inside), broadcasting x and z."""
    d = None
    s = None
    n = len(V2)
    for i in range(n):
        ax, az = V2[i]
        bx, bz = V2[i - 1]
        ex, ez = F32(bx - ax), F32(bz - az)
        wx, wz = x - F32(ax), z - F32(az)
        h = np.clip((wx * ex + wz * ez) / F32(ex * ex + ez * ez + 1e-12), 0.0, 1.0)
        dx, dz = wx - ex * h, wz - ez * h
        dd = dx * dx + dz * dz
        c1 = z >= F32(az)
        c2 = z < F32(bz)
        c3 = ex * wz > ez * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        if d is None:
            d = dd
            s = np.where(flip, F32(-1), F32(1))
        else:
            d = np.minimum(d, dd)
            s = np.where(flip, -s, s)
    return s * np.sqrt(d)


def polyline_dist(x, z, pts):
    d = None
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        ex, ez = F32(bx - ax), F32(bz - az)
        wx, wz = x - F32(ax), z - F32(az)
        h = np.clip((wx * ex + wz * ez) / F32(ex * ex + ez * ez), 0.0, 1.0)
        dd = (wx - ex * h) ** 2 + (wz - ez * h) ** 2
        d = dd if d is None else np.minimum(d, dd)
    return np.sqrt(d)


class FnPrim(sdf.Prim):
    def __init__(self, lo, hi_, f):
        self.lo, self.hi, self.f = np.asarray(lo, float), np.asarray(hi_, float), f

    def aabb(self):
        return self.lo, self.hi

    def __call__(self, x, y, z):
        return self.f(x, y, z)


# ---------------------------------------------------------------- the stock (sculpt)
OUTLINE = chaikin(traced(STOCK_OUTLINE), 2)
OPENING = chaikin(traced(GUARD_OPENING), 2)
GLINE = traced(GUARD_LINE)


def stock_hw(x, z):
    """Half width of the stock at (x, z): 37 mm under the receiver, 47 mm at the cheek and well,
    45 mm at the butt, a 29 mm grip, a 16 mm guard strut and bar."""
    hw = F32(0.0185) + F32(0.0050) * ss(-0.030, -0.075, x) - F32(0.0012) * ss(-0.300, -0.380, x)
    below = ss(-0.036, -0.047, z)
    grip = below * ss(-0.113, -0.100, x)
    hw = hw + (F32(0.0145) - hw) * grip
    dg = polyline_dist(x, z, GLINE)
    guard = below * ss(0.017, 0.010, dg)
    return hw + (F32(0.0080) - hw) * guard


def stock_f(x, y, z):
    d2 = poly_sdf(x, z, OUTLINE)
    d2 = np.maximum(d2, -poly_sdf(x, z, OPENING))
    return rinter(d2, np.abs(y) - stock_hw(x, z), 0.0055)


def stock_model():
    m = sdf.Model()
    lo = (PX(3830), -0.03, PZ(1695))
    hi_ = (PX(1430), 0.03, PZ(875))
    m.add(FnPrim(lo, hi_, stock_f))
    # Magazine well: the clear magazine goes up into it.
    m.sub(sdf.RoundBox(((MAG_X0 + MAG_X1) / 2, 0.0, MAG_MOUTH + 0.020), (MAG_HD + 0.0008, MAG_HW + 0.0008, 0.030),
                       r=0.0030), k=0.0015)
    # Ejection port (right): the bolt shows through it.
    m.sub(sdf.RoundBox(((PX(3010) + PX(3420)) / 2, -0.0245, 0.0088), ((PX(3010) - PX(3420)) / 2, 0.0070, 0.0050),
                       r=0.0022), k=0.0012)
    # Port cover strip (left): a shallow recess the black strip sits in.
    m.sub(sdf.RoundBox(((PX(3020) + PX(3520)) / 2, 0.0245, 0.0088), ((PX(3020) - PX(3520)) / 2, 0.0016, 0.0052),
                       r=0.0016), k=0.0008)
    # Hollow under the front of the stock where the receiver's tail goes in (it is hidden; keeps the
    # bake from finding stock faces inside the receiver).
    if hi():
        # Butt plate seam: a fine groove parallel to the butt.
        ax_, az_ = P(3772, 948)
        bx_, bz_ = P(3640, 1672)
        tx, tz = bx_ - ax_, bz_ - az_
        ln = math.hypot(tx, tz)
        nx_, nz_ = tz / ln, -tx / ln

        def seam(f, x, y, z):
            slab = np.abs((x - F32(ax_)) * F32(nx_) + (z - F32(az_)) * F32(nz_)) - F32(0.00045)
            return np.maximum(f, np.minimum(-slab, f + F32(0.0006)))
        m.fn((PX(3830), -0.03, PZ(1700)), (PX(3620), 0.03, PZ(930)), seam)
        # Mould parting line along the top edges and the grip.

        def parting(f, x, y, z):
            band = np.abs(y) - F32(0.00025)
            return np.maximum(f, np.minimum(-band, f + F32(0.00025)))
        m.fn((PX(3830), -0.03, PZ(1695)), (PX(1430), 0.03, PZ(875)), parting)
    return m


STOCK_LO = (PX(3830), -0.030, PZ(1700))
STOCK_HI = (PX(1430), 0.030, PZ(870))


def stock_mesh(name, h):
    lo = tuple(v + h * f for v, f in zip(STOCK_LO, (0.371, 0.413, 0.297)))
    grid = sdf.Grid(lo, STOCK_HI, h)
    print(f"aug: sculpting the stock on {grid.shape} ({grid.size / 1e6:.1f} M cells)")
    F = stock_model().evaluate(grid)
    me = sdf.to_mesh(name, F, grid)
    del F
    ob = hs.link(bpy.data.objects.new(name, me))
    me.materials.append(M_STOCK)
    me.shade_smooth()
    PART_OF[ob.name] = "body"
    return ob


def low_sculpt(name, h, tris, builder):
    ob = builder(name, h)
    dec = ob.modifiers.new("decimate", "DECIMATE")
    dec.ratio = min(1.0, tris / max(1, 2 * len(ob.data.polygons)))
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    return ob


_SURF = {}


def stock_surface_y(x, z, side=1):
    """|y| of the stock surface at (x, z) (for buttons, screws and swivels that sit on it)."""
    key = (round(x, 5), round(z, 5), side)
    if key not in _SURF:
        m = stock_model()
        ys = np.linspace(0.0, 0.03, 601)
        Pp = np.stack([np.full_like(ys, x), ys * side, np.full_like(ys, z)], 1)
        f = m.evaluate_points(Pp)
        i = int(np.argmax(f > 0))
        _SURF[key] = float(ys[i])
    return _SURF[key]


# ---------------------------------------------------------------- stock furniture
def build_stock_parts():
    # Trigger: the big curved blade in the front of the guard (olive, like the stock).
    finish(profile("trigger", TRIGGER, 0.0068), M_STOCK, bevel=0.0012, angle=30)
    finish(hs.cyl_y("trigger_pin", 0.0018, 0.0398, (PX(1885), 0, PZ(1150)), verts=16), M_STEEL, bevel=0.0003)
    # Crossbolt safety above the grip: a squared ribbed head on the left, a round one on the right.
    sx, sz = P(2036, 1136)
    yl = stock_surface_y(sx, sz, 1)
    finish(hs.box("safety_left", (0.0095, 0.0040, 0.0095), (sx, yl + 0.0010, sz)), M_BLACKPOLY, bevel=0.0010)
    if hi():
        for i in range(5):
            finish(hs.box(f"safety_rib{i}", (0.0080, 0.0006, 0.0008), (sx, yl + 0.0032, sz - 0.0032 + i * 0.0016)),
                   M_BLACKPOLY, bevel=0)
    yr = stock_surface_y(sx, sz, -1)
    finish(hs.cyl_y("safety_right", 0.0046, 0.0036, (sx, -(yr + 0.0006), sz), verts=24), M_BLACKPOLY, bevel=0.0008)
    finish(hs.cyl_y("safety_right_band", 0.0047, 0.0010, (sx, -(yr + 0.0002), sz), verts=24), M_REDPAINT, bevel=0)
    # Takedown button over the front of the well: a ribbed plate with a round pin in it.
    tx, tz = P(2538, 1128)
    yt = stock_surface_y(tx, tz, 1)
    finish(hs.box("takedown", (0.0215, 0.0030, 0.0135), (tx, yt + 0.0006, tz)), M_STEEL, bevel=0.0010)
    if hi():
        for i in range(9):
            finish(hs.box(f"takedown_rib{i}", (0.0006, 0.0008, 0.0110), (tx - 0.0090 + i * 0.00225, yt + 0.0023, tz)),
                   M_STEEL, bevel=0)
    finish(hs.cyl_y("takedown_pin", 0.0038, 0.0020, (tx, yt + 0.0026, tz), verts=24), M_BRIGHT, bevel=0.0006)
    yt2 = stock_surface_y(tx, tz, -1)
    finish(hs.cyl_y("takedown_pin_r", 0.0040, 0.0016, (tx, -(yt2 + 0.0002), tz), verts=24), M_STEEL, bevel=0.0005)
    # Stock screw and the butt plate screws.
    for nm, px, py, r in (("stock_screw", 2981, 1279, 0.0042), ("butt_screw", 3543, 1645, 0.0024)):
        x, z = P(px, py)
        for side in (1, -1):
            ys = stock_surface_y(x, z, side)
            finish(hs.cyl_y(f"{nm}{side}", r, 0.0012, (x, side * (ys + 0.0001), z), verts=24), M_STEEL, bevel=0.0004)
            if hi():
                finish(hs.box(f"{nm}_slot{side}", (r * 1.9, 0.0008, 0.0008), (x, side * (ys + 0.0006), z),
                              rot=(0, math.radians(35), 0)), M_BORE, bevel=0)
    # Ejection port: the bolt carrier behind the opening on the right, the cover strip on the left.
    px0, px1 = PX(3010), PX(3420)
    finish(hs.box("bolt_face", (px0 - px1 - 0.004, 0.004, 0.0085), ((px0 + px1) / 2, -0.0188, 0.0088)), M_STEEL,
           bevel=0.0008)
    if hi():
        finish(hs.box("bolt_extractor", (0.012, 0.0012, 0.0030), (px0 - 0.012, -0.0208, 0.0098)), M_BRIGHT, bevel=0.0003)
        finish(hs.box("bolt_cut", (0.040, 0.0006, 0.0012), ((px0 + px1) / 2 - 0.010, -0.0209, 0.0062)), M_BORE, bevel=0)
    cx0, cx1 = PX(3020), PX(3520)
    finish(hs.box("port_cover", (cx0 - cx1 - 0.0030, 0.0020, 0.0080), ((cx0 + cx1) / 2, 0.0236, 0.0088)), M_BLACKPOLY,
           bevel=0.0009)
    # Magazine catch behind the well.
    finish(profile("mag_catch", MAG_CATCH, 0.0150), M_BLACKPOLY, bevel=0.0012)
    if hi():
        cx, cz = P(3085, 1418)
        for i in range(4):
            finish(hs.box(f"mag_catch_rib{i}", (0.0010, 0.0130, 0.0009), (cx - 0.003 + i * 0.0022, 0, cz - 0.0012)),
                   M_BLACKPOLY, bevel=0)
    # Rear sling swivel on the left of the butt: a riveted base and a D-ring hanging back.
    rx, rz = P(3600, 1236)
    yr = stock_surface_y(rx, rz, 1)
    finish(hs.cyl_y("rear_swivel_base", 0.0065, 0.0030, (rx, yr + 0.0010, rz), verts=24), M_STEEL, bevel=0.0007)
    finish(hs.cyl_y("rear_swivel_rivet", 0.0028, 0.0018, (rx, yr + 0.0030, rz), verts=16), M_BRIGHT, bevel=0.0004)
    d_ring("rear_swivel_ring", (rx - 0.0050, yr + 0.0040, rz - 0.0040), 0.0092, 0.0014, (0, 0, 0), M_STEEL)


def d_ring(name, centre, major, minor, rot, m):
    bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(28), minor_segments=8 if hi() else 5,
                                     major_radius=major, minor_radius=minor, location=centre, rotation=rot)
    ring = bpy.context.active_object
    ring.name = name
    finish(ring, m, bevel=0)
    return ring


# ---------------------------------------------------------------- receiver, carry handle, scope
def rrect(hw, zb, zt, rt, rb, n):
    """Cross-section (y, z): a rectangle with top corners of radius rt, bottom rb."""
    pts = []
    for cy, cz, r, a0 in ((hw - rb, zb + rb, rb, -90), (hw - rt, zt - rt, rt, 0), (-hw + rt, zt - rt, rt, 90),
                          (-hw + rb, zb + rb, rb, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def build_receiver():
    n = 6 if hi() else 2
    rec = hs.section("receiver", rrect(REC_HW, REC_ZB, REC_ZT, 0.0045, 0.0025, n), REC_X0, REC_X1)
    # Lightening slots in the upper rails, both sides.
    for sy in (1, -1):
        for xa, xb in ((PX(1420), PX(1490)), (PX(1525), PX(1730))):
            hs.cut(rec, hs.box(f"rec_lslot{sy}_{xa:.3f}", (xa - xb, 0.008, 0.0050),
                               ((xa + xb) / 2, sy * REC_HW, PZ(966))))
    # Cocking handle slot (left), its guide rod inside.
    hs.cut(rec, hs.box("rec_cslot", (PX(1320) - PX(1945), 0.012, SLOT_Z1 - SLOT_Z0),
                       ((PX(1320) + PX(1945)) / 2, REC_HW, (SLOT_Z0 + SLOT_Z1) / 2)))
    finish(rec, M_ALU, bevel=0.0007)
    finish(hs.cyl_x("guide_rod", 0.0030, PX(1955), REC_X1 + 0.002, verts=16, y=0.0125, z=(SLOT_Z0 + SLOT_Z1) / 2),
           M_BRIGHT, bevel=0.0002)
    finish(hs.box("slot_back", (PX(1320) - PX(1945), 0.0010, SLOT_Z1 - SLOT_Z0 + 0.002),
                  ((PX(1320) + PX(1945)) / 2, 0.0088, (SLOT_Z0 + SLOT_Z1) / 2)), M_BORE, bevel=0)
    for sy in (1, -1):
        for xa, xb in ((PX(1420), PX(1490)), (PX(1525), PX(1730))):
            finish(hs.box(f"lslot_back{sy}_{xa:.3f}", (xa - xb, 0.0010, 0.0052),
                          ((xa + xb) / 2, sy * (REC_HW - 0.0036), PZ(966))), M_BORE, bevel=0)
    # Lower rail under the slot (the bright ledge in the photo).
    finish(hs.box("rec_ledge", (PX(1330) - PX(1940), 0.0016, 0.0026), ((PX(1330) + PX(1940)) / 2, REC_HW + 0.0004,
                                                                           SLOT_Z0 - 0.0045)), M_ALU, bevel=0.0005)
    # Barrel locking flange on the front face.
    finish(hs.section("rec_flange", rrect(0.0172, PZ(1150), REC_ZT - 0.002, 0.004, 0.004, n), REC_X1 - 0.0010,
                      REC_X1 + 0.0045), M_STEEL, bevel=0.0006)
    # Carry handle (cast with the receiver) and its window.
    br = profile("bridge", BRIDGE_OUTLINE, 0.0170)
    win = profile("bridge_window", BRIDGE_WINDOW, 0.04)
    hs.cut(br, win)
    finish(br, M_ALU, bevel=0.0014, angle=40)
    # Front sling swivel on the handle's front leg.
    sx, sz = P(1335, 870)
    finish(hs.cyl_y("front_swivel_boss", 0.0045, 0.0060, (sx + 0.003, 0.0105, sz), verts=20), M_STEEL, bevel=0.0006)
    d_ring("front_swivel_ring", (sx - 0.0045, 0.0140, sz + 0.0060), 0.0090, 0.0014, (PI / 2, 0, math.radians(-25)),
           M_STEEL)
    # Markings on the left of the receiver.
    yl = REC_HW + 0.00005
    text("mark_model", "AUG", 0.0052, (PX(1900), yl, PZ(1076)), (PI / 2, 0, PI))
    text("mark_serial", "GRF 77 0412", 0.0030, (PX(1760), yl, PZ(1080)), (PI / 2, 0, PI))
    text("mark_right", "GRAFT ARMS  5,56", 0.0030, (PX(1600), -yl, PZ(1080)), (PI / 2, 0, 0))


def build_scope():
    z = SCOPE_Z
    x0, x1 = SCOPE_X0, SCOPE_X1
    ep = x0 + 0.0075                      # eyepiece ring front
    ob = x1 - 0.0095                      # objective bell rear
    prof = [(x0 + 0.0040, 0.0), (x0 + 0.0040, 0.0118), (x0, 0.0122), (x0, 0.0146), (x0 + 0.0006, 0.0152),
            (ep, 0.0152), (ep + 0.0006, SCOPE_R), (ob - 0.0006, SCOPE_R), (ob, 0.0153), (x1 - 0.0007, 0.0153),
            (x1, 0.0146), (x1, 0.0124), (x1 - 0.0050, 0.0120), (x1 - 0.0050, 0.0)]
    tube = hs.lathe_x("scope_tube", prof, verts=48 if hi() else 24)
    tube.location = (0, 0, z)
    finish(tube, M_SCOPE, bevel=0.0004, angle=30)
    finish(hs.cyl_x("eyepiece_glass", 0.0118, x0 + 0.0039, x0 + 0.0042, verts=40 if hi() else 20, z=z), M_LENS,
           bevel=0, smooth=True)
    finish(hs.cyl_x("objective_glass", 0.0120, x1 - 0.0053, x1 - 0.0049, verts=40 if hi() else 20, z=z), M_LENS,
           bevel=0, smooth=True)
    # Adjuster caps: hex on top (elevation), hex nut underneath.
    cx = PX(1830)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.0080, depth=0.0110, location=(cx, 0, z + SCOPE_R - 0.0010))
    top = bpy.context.active_object
    top.name = "scope_cap_top"
    finish(top, M_SCOPE, bevel=0.0009, angle=30)
    finish(hs.cyl_z("scope_cap_dome", 0.0058, 0.0024, (cx, 0, z + SCOPE_R + 0.0055), verts=28), M_SCOPE,
           bevel=0.0010)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.0072, depth=0.0110,
                                        location=(cx - 0.001, 0, z - SCOPE_R - 0.0030), rotation=(0, 0, PI / 6))
    bot = bpy.context.active_object
    bot.name = "scope_cap_bottom"
    finish(bot, M_SCOPE, bevel=0.0008, angle=30)
    finish(hs.cyl_z("scope_cap_stud", 0.0030, 0.0030, (cx - 0.001, 0, z - SCOPE_R - 0.0098), verts=16), M_STEEL,
           bevel=0.0004)
    # The "H" adjustment mark on the left of the tube, white-filled.
    text("scope_h", "<- H ->", 0.0042, (cx + 0.0105, SCOPE_R + 0.0001, z - 0.0040), (PI / 2, 0, PI), m=M_PAINT,
         extrude=0.00008)
    text("scope_mag", "1,5x", 0.0034, (PX(2330), -(SCOPE_R + 0.0001), z - 0.0030), (PI / 2, 0, 0), m=M_PAINT,
         extrude=0.00008)


def build_charging_handle():
    """The folding cocking handle at the front of its slot (left side)."""
    part("charging_handle")
    x0, x1 = PX(1430), PX(1285)
    finish(hs.box("ch_slide", (x1 - x0, 0.0060, SLOT_Z1 - SLOT_Z0 - 0.0010),
                  ((x0 + x1) / 2, REC_HW - 0.0010, (SLOT_Z0 + SLOT_Z1) / 2)), M_STEEL, bevel=0.0005)
    blk = hs.side_profile("ch_block", [(x0, SLOT_Z0 - 0.0015), (x1, SLOT_Z0 - 0.0015), (x1 + 0.0010, SLOT_Z1 + 0.0050),
                                       (x0 + 0.0040, SLOT_Z1 + 0.0050)], 0.0070, y=REC_HW + 0.0035)
    finish(blk, M_STOCK_WORN, bevel=0.0012)
    lever = hs.side_profile("ch_lever", [(x0 + 0.0030, SLOT_Z1 + 0.0030), (x1 - 0.0010, SLOT_Z1 + 0.0030),
                                         (x1 - 0.0030, PZ(905)), (x1 - 0.0090, PZ(882)), (x0 + 0.0060, PZ(880)),
                                         (x0 + 0.0020, PZ(910))], 0.0055, y=REC_HW + 0.0062)
    hs.cut(lever, hs.cyl_y("ch_lever_hole", 0.0026, 0.03, ((x0 + x1) / 2 + 0.002, REC_HW + 0.006, PZ(920)), verts=16))
    finish(lever, M_STOCK_WORN, bevel=0.0012)
    finish(hs.cyl_y("ch_hinge", 0.0022, 0.0110, (x1 - 0.0045, REC_HW + 0.0050, SLOT_Z1 + 0.0035), verts=16), M_STEEL,
           bevel=0.0004)
    part("body")


# ---------------------------------------------------------------- barrel, gas block, flash hider, foregrip
def build_front():
    nb = 32 if hi() else 16
    bx0 = REC_X1 + 0.004
    finish(hs.cyl_x("barrel", 0.0089, bx0, PX(388), verts=nb), M_STEEL, bevel=0.0003)
    if hi():
        # Cooling grooves on the front of the barrel (fine rings, baked into the normal map).
        prof = []
        xa, xb = PX(940), PX(392)
        k = int((xb - xa) / 0.0018)
        for i in range(k):
            x = xa + i * (xb - xa) / k
            prof += [(x, 0.0089), (x + 0.0004, 0.0084), (x + 0.0014, 0.0084), (x + 0.0018, 0.0089)]
        rib = hs.lathe_x("barrel_ribs", [(xa, 0.0)] + prof + [(xb, 0.0)], verts=48)
        finish(rib, M_STEEL, bevel=0)
    # Gas block / barrel sleeve and the gas cylinder under it with its regulator.
    sl0, sl1 = REC_X1 + 0.004, PX(1000)
    finish(hs.lathe_x("sleeve", [(sl0, 0.0), (sl0, 0.0104), (sl1 - 0.002, 0.0104), (sl1, 0.0096), (sl1, 0.0)],
                      verts=nb), M_STEEL, bevel=0.0004)
    finish(hs.cyl_x("gas_cyl", 0.0058, sl0, PX(1045), verts=nb // 2 + 4, z=-0.0124), M_STEEL, bevel=0.0005)
    finish(hs.box("gas_web", (PX(1045) - sl0, 0.0070, 0.0090), ((PX(1045) + sl0) / 2, 0, -0.0072)), M_STEEL,
           bevel=0.0006)
    rx0, rx1 = PX(1068), PX(1018)
    reg = hs.cyl_x("gas_regulator", 0.0060, rx0, rx1, verts=nb, z=-0.0124)
    finish(reg, M_STEEL, bevel=0.0005)
    if hi():
        for i, a in enumerate((60, 90, 120)):
            ra = math.radians(a)
            finish(hs.box(f"reg_index{i}", (0.0006, 0.0018, 0.0010),
                          (rx1 + 0.0002, 0.0050 * math.cos(ra), -0.0124 + 0.0050 * math.sin(ra) - 0.0010)), M_PAINT,
                   bevel=0)
        finish(hs.box("reg_flat", (rx0 - rx1, 0.0030, 0.0012), ((rx0 + rx1) / 2, 0.0062, -0.0124)), M_PAINT,
               bevel=0.0003)
    # Flash hider: rear base, lock nut (hex), slotted body, front ring.
    hx0, hx1 = PX(388), PX(5)
    finish(hs.lathe_x("fh_collar", [(PX(388), 0.0), (PX(388), 0.0108), (PX(342), 0.0108), (PX(342), 0.0)], verts=nb),
           M_STEEL, bevel=0.0005)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.0118, depth=PX(242) - PX(338),
                                        location=((PX(242) + PX(338)) / 2, 0, 0), rotation=(0, PI / 2, 0))
    nut = bpy.context.active_object
    nut.name = "fh_nut"
    finish(nut, M_STEEL, bevel=0.0008, angle=25)
    fh = hs.lathe_x("flash_hider", [(PX(240), 0.0), (PX(240), 0.0106), (PX(200), 0.0106), (PX(190), 0.0098),
                                    (PX(70), 0.0098), (PX(58), 0.0106), (PX(14), 0.0106), (hx1, 0.0098),
                                    (hx1, 0.0072), (hx1 - 0.002, 0.0068), (hx1 - 0.002, 0.0)], verts=nb)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        s = hs.box(f"fh_slot{i}", (PX(30) - PX(178), 0.0034, 0.020), (0, 0, 0))
        s.rotation_euler = (a, 0, 0)
        s.location = ((PX(30) + PX(178)) / 2, 0.0095 * math.sin(a) * 0, 0.0)
        # Slots run through one wall each: offset the cutter out along its own radial direction.
        s.location = ((PX(30) + PX(178)) / 2, -math.sin(a) * 0.0100, math.cos(a) * 0.0100)
        hs.cut(fh, s)
    finish(fh, M_STEEL, bevel=0.0005)
    finish(hs.cyl_x("fh_bore", 0.0034, hx1 - 0.0021, hx1 - 0.0018, verts=16), M_BORE, bevel=0)
    finish(hs.cyl_x("fh_core", 0.0068, PX(178), PX(30), verts=16), M_BORE, bevel=0)
    # Foregrip hinge under the flange: block, pivot pin, the round latch on the left.
    hx0, hx1 = PX(1305), PX(1195)
    finish(hs.box("fg_hinge", (hx1 - hx0, 0.0230, REC_ZB - PZ(1170)), ((hx0 + hx1) / 2, 0, (REC_ZB + PZ(1170)) / 2)),
           M_STEEL, bevel=0.0012)
    finish(hs.cyl_y("fg_pivot", 0.0034, 0.0262, (PX(1250), 0, PZ(1150)), verts=20), M_BRIGHT, bevel=0.0004)
    finish(hs.cyl_y("fg_latch", 0.0048, 0.0040, (PX(1290), 0.0130, PZ(1150)), verts=24), M_STEEL, bevel=0.0007)
    if hi():
        finish(hs.cyl_y("fg_latch_dimple", 0.0026, 0.0004, (PX(1290), 0.0151, PZ(1150)), verts=16), M_BORE, bevel=0)


def foregrip_model():
    m = sdf.Model()
    cx = FG_X
    m.add(sdf.RoundBox((cx, 0.0, PZ(1405)), (0.0182, 0.0146, 0.0470), r=0.0100))
    # Palm swell on the back, flared heel at the bottom, the neck into the hinge.
    m.add(sdf.Ellipsoid((cx - 0.0090, 0.0, PZ(1380)), (0.0110, 0.0150, 0.0300)), k=0.010)
    m.add(sdf.RoundBox((cx + 0.0004, 0.0, PZ(1632)), (0.0196, 0.0156, 0.0040), r=0.0036), k=0.006)
    m.add(sdf.RoundBox((cx + 0.0015, 0.0, PZ(1175)), (0.0130, 0.0112, 0.0060), r=0.0030), k=0.004)
    return m


FG_LO = (FG_X - 0.024, -0.020, PZ(1660))
FG_HI = (FG_X + 0.024, 0.020, PZ(1150))


def foregrip_mesh(name, h):
    lo = tuple(v + h * f for v, f in zip(FG_LO, (0.371, 0.413, 0.297)))
    grid = sdf.Grid(lo, FG_HI, h)
    F = foregrip_model().evaluate(grid)
    me = sdf.to_mesh(name, F, grid)
    ob = hs.link(bpy.data.objects.new(name, me))
    me.materials.append(M_STOCK_WORN if False else M_STOCK)
    me.shade_smooth()
    PART_OF[ob.name] = "body"
    return ob


# ---------------------------------------------------------------- magazine
MAG_TOP = V((-(MAG_HD) + MAG_X0, 0.0, MAG_MOUTH))     # spine at the well mouth
MAG_CENTER = (MAG_TOP.x + MAG_R * math.cos(MAG_A0), MAG_TOP.z + MAG_R * math.sin(MAG_A0))


def mag_frame(s):
    """Spine point `s` metres below the well mouth (negative = inside the stock), the unit vector
    down the spine and the unit vector toward the front of the magazine."""
    a = MAG_A0 + s / MAG_R
    p = V((MAG_TOP.x + MAG_R * (math.cos(MAG_A0) - math.cos(a)), 0.0,
           MAG_TOP.z - MAG_R * (math.sin(a) - math.sin(MAG_A0))))
    return p, V((math.sin(a), 0.0, -math.cos(a))), V((math.cos(a), 0.0, math.sin(a)))


def slot_s(k):
    return -0.0120 + k * MAG_PITCH


def build_magazine():
    """The opaque parts: floor plate, the top band and feed lips (inside the well), the follower."""
    part("magazine")
    fp = []
    for s, g in ((MAG_S1 - 0.0010, 0.0004), (MAG_S1 + 0.0010, 0.0016), (MAG_S1 + MAG_FLOOR - 0.0020, 0.0016),
                 (MAG_S1 + MAG_FLOOR, 0.0004)):
        p, d, f = mag_frame(s)
        fp.append((p, (0, 1, 0), f, MAG_HW + g, MAG_HD + g))
    finish(hs.loft("mag_floor", fp, power=7.0), M_STOCK_WORN, bevel=0.0012, angle=40)
    if hi():
        p, d, f = mag_frame(MAG_S1 + MAG_FLOOR)
        for i in range(5):
            finish(hs.box(f"mag_floor_rib{i}", (0.0012, 0.0200, 0.0008), (0, 0, 0)), M_STOCK_WORN, bevel=0)
            ob = bpy.data.objects[f"mag_floor_rib{i}"]
            ob.location = p + f * (-0.016 + i * 0.008) + d * 0.0003
            ob.rotation_euler = (0, -math.atan2(d.x, -d.z), 0)
    top = []
    for s, g in ((MAG_S0, -0.0006), (MAG_S0 + 0.0020, 0.0), (MAG_S0 + 0.0120, 0.0)):
        p, d, f = mag_frame(s)
        top.append((p, (0, 1, 0), f, MAG_HW + g, MAG_HD + g))
    finish(hs.loft("mag_top", top, power=7.0), M_BLACKPOLY, bevel=0.0008, angle=40)
    part("mag_follower")
    k = MAG_CAP - 1
    p, d, f = mag_frame(slot_s(k) + 0.0072)
    stations = []
    for t in (-0.0028, 0.0028):
        stations.append((p + d * t, (0, 1, 0), f, MAG_HW - 0.0018, MAG_HD - 0.0024))
    finish(hs.loft("follower", stations, power=6.0), M_BLACKPOLY, bevel=0.0008, angle=40)
    part("body")


def mag_shell(name):
    """The clear magazine body (no bake): rounded box down the curved spine, horizontal ribs at the
    round pitch, a lug down the front."""
    n = 20
    stations = []
    steps = 36
    for i in range(steps + 1):
        s = MAG_S0 + (MAG_S1 - MAG_S0 + 0.0008) * i / steps
        p, d, f = mag_frame(s)
        rib = 0.00030 * (0.5 + 0.5 * math.cos(2 * PI * (s - slot_s(0)) / (2 * MAG_PITCH * 1.9)))
        stations.append((p, (0, 1, 0), f, MAG_HW + rib, MAG_HD + rib * 0.5))
    ob = hs.loft(name, stations, n=n, power=7.0)
    ob.data.shade_smooth()
    return ob


def mag_rounds(name):
    """30 x 5.56x45: double stack, alternating sides, bullets forward. UV.x = slot + 0.25 brass / 0.75 copper."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    sides = 6
    # (x along the round from the case head, radius, copper?)
    case = [(0.0, 0.0), (0.0, 0.00470), (0.0390, 0.00450), (0.0415, 0.00320), (0.0447, 0.00320)]
    bullet = [(0.0447, 0.00285), (0.0515, 0.00220), (0.0574, 0.0)]
    for k in range(MAG_CAP):
        s = slot_s(k)
        p, d, f = mag_frame(s)
        y = MAG_STAGGER if k % 2 == 0 else -MAG_STAGGER
        base = p + V((0, y, 0)) - f * (MAG_HD - 0.0018)
        u = V((0, 1, 0))
        w = d

        for kind, prof in ((0.25, case), (0.75, bullet)):
            rings = []
            for x, r in prof:
                c = base + f * x
                if r <= 0.0:
                    rings.append([bm.verts.new(c)])
                    continue
                rings.append([bm.verts.new(c + (u * math.cos(2 * PI * j / sides) + w * math.sin(2 * PI * j / sides)) * r)
                              for j in range(sides)])
            faces = []
            for r0, r1 in zip(rings[:-1], rings[1:]):
                if len(r0) == 1 and len(r1) == 1:
                    continue
                if len(r0) == 1:
                    for j in range(sides):
                        faces.append(bm.faces.new((r0[0], r1[(j + 1) % sides], r1[j])))
                elif len(r1) == 1:
                    for j in range(sides):
                        faces.append(bm.faces.new((r0[j], r0[(j + 1) % sides], r1[0])))
                else:
                    for j in range(sides):
                        faces.append(bm.faces.new((r0[j], r0[(j + 1) % sides], r1[(j + 1) % sides], r1[j])))
            for fc in faces:
                for lp in fc.loops:
                    lp[uvl].uv = (k + kind, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = hs.mesh_object(name, bm)
    ob.data.shade_smooth()
    return ob


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    if detail is hs.HIGH:
        stock = stock_mesh("stock_high", 0.0011 if args.fast else 0.00055)
        fg = foregrip_mesh("foregrip_high", 0.0008 if args.fast else 0.0004)
    else:
        stock = low_sculpt("stock_low", 0.0013, args.low_tris, stock_mesh)
        fg = low_sculpt("foregrip_low", 0.0011, 900, foregrip_mesh)
    hs.PARTS.append(stock)
    hs.PARTS.append(fg)
    build_stock_parts()
    build_receiver()
    build_scope()
    build_charging_handle()
    build_front()
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
    if detail is not hs.HIGH:
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
        joined.data.shade_smooth()
        joined.data.set_sharp_from_angle(angle=math.radians(35))
        wn = joined.modifiers.new("wnormal", "WEIGHTED_NORMAL")
        wn.mode = "FACE_AREA"
        wn.weight = 100
        wn.keep_sharp = True
        bpy.ops.object.convert(target="MESH")
    print(f"aug {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


EXPLODE = {"body": 0.0, "magazine": -0.30, "charging_handle": 0.30, "mag_follower": -0.60}


def explode(ob, sign):
    """Moves the parts apart along Y for the bake (they sit within a millimetre of the stock)."""
    me = ob.data
    pid = np.empty(len(me.polygons), np.int32)
    me.attributes["part_id"].data.foreach_get("value", pid)
    loop_start = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_start", loop_start)
    loop_total = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", loop_total)
    loop_vert = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", loop_vert)
    vpart = np.zeros(len(me.vertices), np.int32)
    vpart[loop_vert] = np.repeat(pid, loop_total)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    for pname, i in PART_IDS.items():
        co[vpart == i, 1] += sign * EXPLODE[pname]
    me.vertices.foreach_set("co", co.ravel())
    me.update()


def split_parts(low):
    objs = {}
    for pname, pid in PART_IDS.items():
        ob = low.copy()
        ob.data = low.data.copy()
        ob.name = pname
        ob.data.name = pname
        scene.collection.objects.link(ob)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer = bm.faces.layers.int.get("part_id")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != pid], context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.attributes.remove(ob.data.attributes["part_id"])
        objs[pname] = ob
        print(f"aug: part {pname}: {bakeutil.tri_count(ob)} tris")
    bpy.data.objects.remove(low)
    return objs


def add_clear_magazine(objs):
    """The unbaked shell and rounds, parented (with the follower) to the magazine."""
    shell = mag_shell("mag_shell")
    shell.data.materials.append(shell_material())
    rounds = mag_rounds("mag_rounds")
    rounds.data.materials.append(M_BRASS)
    mag = objs["magazine"]
    for ob in (shell, rounds, objs["mag_follower"]):
        ob.parent = mag
        ob.matrix_parent_inverse = Matrix.Identity(4)
    print(f"aug: mag_shell {bakeutil.tri_count(shell)} tris, mag_rounds {bakeutil.tri_count(rounds)} tris")
    return [shell, rounds]


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True,
                              export_image_format="AUTO", export_attributes=False)


# ---------------------------------------------------------------- preview
def preview_shell():
    g = bpy.data.materials.new("preview_shell")
    b = g.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.98, 0.86, 0.66, 1)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.15
    return g


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
    floor.location = (0, 0, -0.30)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(-0.02, 0, -0.05), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.4, -1.3, 1.2), 70, 1.8, sy=0.6)
    area("key_l", (-0.2, 1.4, 1.0), 55, 1.8, sy=0.6)
    area("strip_top", (0.0, 0.0, 1.2), 40, 2.4, sy=0.2)
    area("fill", (0.6, 1.3, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.6, -0.4, 0.5), 50, 0.8, (1.0, 0.82, 0.62))
    area("kick", (-1.4, 0.3, 0.2), 28, 1.0, (0.9, 0.95, 1.0))
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    return cam


def shoot(cam, path, loc, target, lens=50, fov_deg=None, fstop=0.0):
    d = cam.data
    d.type = "PERSP"
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
    print(f"aug: rendered {path}")


def render_previews(stem):
    for nm in [n for n in args.hide.split(",") if n]:
        ob = bpy.data.objects.get(nm)
        if ob:
            ob.hide_render = True
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((-0.015, -1.75, -0.06), (-0.015, 0, -0.07), 85, 0.0),
        "left_side": ((-0.015, 1.75, -0.06), (-0.015, 0, -0.07), 85, 0.0),
        "beauty": ((0.70, 1.05, 0.40), (-0.02, 0, -0.05), 50, 8.0),
        "rear": ((-0.75, 0.75, 0.30), (-0.05, 0, -0.03), 45, 8.0),
        "receiver": ((0.14, 0.40, 0.14), (0.04, 0.0, 0.02), 50, 4.0),
        "mag": ((-0.10, 0.42, -0.14), (-0.17, 0.0, -0.13), 50, 4.0),
        "grip": ((0.05, -0.42, -0.12), (-0.04, 0.0, -0.08), 50, 4.0),
        "front": ((0.62, 0.30, 0.02), (0.25, 0.0, -0.02), 50, 4.0),
        # Roughly the player's hip view: eye behind and left of the gun, above it.
        "fp": ((-0.47, 0.19, 0.17), (0.75, -0.14, 0.09), 0, 0.0),
    }
    only = [s for s in args.only.split(",") if s]
    for key, (loc, target, lens, fstop) in shots.items():
        if only and key not in only:
            continue
        if key == "fp":
            shoot(cam, f"{stem}_{key}.png", loc, target, fov_deg=60)
        else:
            shoot(cam, f"{stem}_{key}.png", loc, target, lens=lens, fstop=fstop)


def render_overlay(path):
    """Orthographic left view at the photo's scale (half size), transparent background, for the match."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1097
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("flat")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.6, 0.6, 1)
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    so = hs.link(bpy.data.objects.new("sun", sun))
    so.rotation_euler = (math.radians(-60), 0, 0)
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 3840 / PX_MM / 1000.0
    cx, cz = P(1920, 1097)
    cam.location = (cx, 1.0, cz)
    cam.rotation_euler = (V((cx, 0, cz)) - V((cx, 1.0, cz))).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"aug: overlay {path}")


# ---------------------------------------------------------------- run
if args.fast:
    args.samples = min(args.samples, 24)
if args.out:
    high = build(hs.HIGH, "aug_high")
    low = build(hs.LOW, "aug_low")
    bakeutil.unwrap(low, boost={M_SCOPE.name: 1.5, M_ALU.name: 1.35, M_STEEL.name: 1.15, M_STOCK.name: 1.0,
                                M_STOCK_WORN.name: 1.1, M_MARK.name: 1.6, M_PAINT.name: 1.6, M_LENS.name: 0.8,
                                M_BORE.name: 0.5, M_BLACKPOLY.name: 1.1, M_BRIGHT.name: 1.1},
                    angle_deg=35.0)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    explode(high, 1)
    explode(low, 1)
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "aug", cage=0.0015, ray=0.005,
                                 ao_distance=0.02, grime=0.32, log=print)
    bpy.data.objects.remove(high)
    explode(low, -1)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "aug", emission_strength=1.0)
    objs = split_parts(low)
    extra = add_clear_magazine(objs)
    export(list(objs.values()) + extra, args.out)
    print(f"aug: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        sh = bpy.data.objects.get("mag_shell")
        if sh:
            sh.data.materials.clear()
            sh.data.materials.append(preview_shell())
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview or args.overlay:
    high = build(hs.HIGH, "aug_high")
    shell = mag_shell("mag_shell")
    shell.data.materials.append(preview_shell())
    rounds = mag_rounds("mag_rounds")
    rounds.data.materials.append(M_BRASS)
    if args.overlay:
        shell.hide_render = True
        rounds.hide_render = True
        render_overlay(args.overlay)
    else:
        render_previews(args.preview.rsplit(".", 1)[0])
