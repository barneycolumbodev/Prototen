"""Franchi SPAS-12 with the folding stock folded over the top, hook up (owner, 2026-11-20).

Owner brief: "Just the way you found the picture and made that AUG model ... do
the same thing for the SPAS 12. Our version of the SPAS 12 is going to have the
stock folded up and be iconic ... it needs to be one-to-one with the actual
SPAS 12." Pump only in the game (design §4.11).

Traced, not guessed: every outline below is in pixels of the reference photo
"Franchi SPAS 12-P5120256-white.jpg" (Rama, Wikimedia Commons, CC BY-SA 3.0 FR;
a left-side studio shot of a SPAS-12 with the 21.5" barrel and the folding
stock folded, hook up), read off gridded crops of the 3840 px wide copy turned
0.52 degrees so the bore is level (row 918.5). Scale: 810 mm folded length
(the factory figure) over 3596 px = 4.44 px/mm, which gives a 20 mm barrel and
a 25.7 mm magazine tube, as the real gun has. `P(px, py)` turns photo pixels
into metres. `--overlay` renders an orthographic left view at the photo's scale
for the match (tools: composite it over the photo).

What it is: the black anodised aluminium receiver (ejection port and bolt
handle on the right, loading port underneath, bolt release on the left, the
Franchi markings), the grey perforated heat shield over the barrel that runs
back over the action, the big ribbed polymer pump (a signed-distance sculpt of
the traced side outline: rounded section, the six short grooves in front, the
eight that wrap round the hand), the 21.5" barrel with the knurled thread
protector and the tall front sight, the 8-shot magazine tube with its knurled
nut and sling flange, the aluminium trigger group with the lever safety, the
polymer pistol grip and stock housing (sculpted, with its six grooves), and the
stamped-steel folding stock folded over the top: two side plates with four
lightening holes and the pressed rib, the pivot hubs, the butt plate standing
up at the front and the arm hook over it.

Parts (per-face part id, split after the bake):
  body       everything that doesn't move
  pump       the fore-end: racked back and forward after every shot
  bolt       the bolt and its handle in the ejection port: run back with the pump
  load_round a 00 buck shell at the loading port (pushed into the tube on reloads)

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the front of the grip (photo x 3300). Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/spas12/build.py --out assets/weapons/spas12/spas12.gltf --tex 4096 \
      --preview docs/previews/spas12.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/spas.png [--only side,fp] [--fast]
  Photo match: --overlay /tmp/spas_overlay.png
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402
import sdf  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--emission-size", type=int, default=256)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
ap.add_argument("--fast", action="store_true", help="coarse sculpt and few samples (look only)")
ap.add_argument("--overlay", default="", help="render the left view for the photo match to this png")
ap.add_argument("--low-fore", type=int, default=2600, help="pump sculpt triangles in LOW")
ap.add_argument("--low-grip", type=int, default=2200, help="grip sculpt triangles in LOW")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
PI = math.pi
F32 = np.float32

# ---------------------------------------------------------------- materials
M_REC = mat("black_anodised", (0.016, 0.016, 0.018), 0.42, 0.55, wear=(0.20, 0.20, 0.21), wear_rough=0.3,
            bump_scale=1600, bump_strength=0.03)
# The heat shield and the stock are phosphated steel, a dark warm grey that reads lighter than the receiver.
M_SHIELD = mat("phosphate_grey", (0.055, 0.056, 0.058), 0.5, 0.75, wear=(0.24, 0.24, 0.25), wear_rough=0.3,
               bump_scale=1300, bump_strength=0.05)
M_STOCK = mat("stamped_steel", (0.048, 0.049, 0.051), 0.46, 0.8, wear=(0.30, 0.30, 0.31), wear_rough=0.26,
              bump_scale=1200, bump_strength=0.05)
M_BARREL = mat("barrel_park", (0.034, 0.035, 0.038), 0.4, 0.85, wear=(0.28, 0.28, 0.29), wear_rough=0.24,
               brushed=0.02, bump_scale=1100, bump_strength=0.02)
M_POLY = mat("black_polymer", (0.020, 0.021, 0.023), 0.58, 0.0, wear=(0.07, 0.07, 0.075), wear_rough=0.42,
             bump_scale=2200, bump_strength=0.12)
M_GRIPTEX = mat("polymer_texture", (0.018, 0.019, 0.021), 0.74, 0.0, bump_scale=520, bump_strength=0.35)
M_ALU = mat("bare_aluminium", (0.40, 0.40, 0.41), 0.34, 0.95, brushed=0.04)
M_STEEL = mat("bright_steel", (0.52, 0.52, 0.53), 0.26, 1.0, brushed=0.04)
M_DARK = mat("bore_dark", (0.006, 0.006, 0.007), 0.7, 0.3)
M_MARK = mat("engraving", (0.42, 0.42, 0.43), 0.45, 0.8)
M_BRASS = mat("brass", (0.80, 0.58, 0.28), 0.26, 1.0)
M_HULL = mat("hull_red", (0.48, 0.035, 0.025), 0.42, 0.0)
MATERIALS = [M_REC, M_SHIELD, M_STOCK, M_BARREL, M_POLY, M_GRIPTEX, M_ALU, M_STEEL, M_DARK, M_MARK, M_BRASS,
             M_HULL]

# ---------------------------------------------------------------- the trace
PX_MM = 4.44          # photo pixels per millimetre (810 mm folded over 3596 px)
X0_PX = 3300          # photo x of the weapon origin (bore axis above the front of the grip)
BORE_PY = 918.5       # photo row of the bore axis (levelled copy)


def P(px, py):
    """Photo pixel -> (x, z) in metres, weapon space."""
    return ((X0_PX - px) / PX_MM / 1000.0, (BORE_PY - py) / PX_MM / 1000.0)


def PX(px):
    return (X0_PX - px) / PX_MM / 1000.0


def PZ(py):
    return (BORE_PY - py) / PX_MM / 1000.0


def MM(px):
    """A length in photo pixels, in metres."""
    return px / PX_MM / 1000.0


MUZZLE_PX = 115
MUZZLE_X = PX(MUZZLE_PX)
BARREL_R = MM(44.5)                     # 20 mm barrel
BORE_R = 0.0093                         # 12 gauge, 18.5 mm
TUBE_Z = PZ(1056.5)
TUBE_R = MM(56.5)                       # 25.4 mm magazine tube
REC_X0, REC_X1 = PX(3450), PX(2525)      # receiver: into the housing / under the heat shield
REC_ZT, REC_ZB = PZ(833), PZ(1118)
REC_HW = 0.0165
SHIELD_HW = 0.0215
SIGHT_TOP = PZ(777)

# Heat shield side outline: the long top over the barrel, the step up behind it, its rear edge
# over the receiver and the deep part that covers the action bars, the front cap.
SHIELD = [(1048, 846), (1955, 846), (2050, 818), (2528, 818), (2537, 830), (2537, 1140), (2525, 1152),
          (2190, 1152), (2190, 992), (1005, 992), (968, 968), (952, 915), (968, 872), (1000, 852)]
SHIELD_TOP_SLOTS = [(1125, 1270), (1300, 1445), (1475, 1620), (1650, 1790), (1820, 1965), (1993, 2138),
                    (2152, 2290), (2365, 2510)]
SHIELD_LOW_SLOTS = [(2245, 2400, 1010), (2195, 2325, 1065), (2370, 2505, 1065), (2250, 2390, 1110)]
# The pump (fore-end): top, rear lip, the hand section, the step, the belly under the tube, the nose.
FORE = [(1040, 911), (2160, 904), (2186, 910), (2196, 932), (2198, 1150), (2190, 1205), (2168, 1218),
        (2145, 1205), (2118, 1190), (2080, 1181), (1720, 1179), (1680, 1180), (1640, 1190), (1600, 1202),
        (1520, 1212), (1440, 1225), (1360, 1227), (1280, 1219), (1200, 1207), (1120, 1197), (1012, 1196),
        (994, 1186), (986, 1160), (996, 1110), (1012, 1010), (1026, 940)]
FORE_GROOVES_FRONT = [1365, 1420, 1475, 1530, 1585, 1640]
FORE_GROOVES_REAR = [1752, 1806, 1858, 1910, 1965, 2017, 2070, 2125]
# Stock housing and pistol grip, clockwise from the top front.
GRIP = [(3432, 852), (3520, 842), (3604, 860), (3644, 900), (3680, 920), (3694, 945), (3705, 1000), (3708, 1040),
        (3698, 1065), (3678, 1100), (3658, 1125), (3619, 1150), (3586, 1175), (3574, 1200), (3570, 1225),
        (3576, 1250), (3594, 1275), (3612, 1300), (3644, 1350), (3670, 1400), (3693, 1450), (3710, 1500),
        (3712, 1525), (3709, 1550), (3701, 1575), (3688, 1600), (3660, 1611), (3560, 1613), (3450, 1610),
        (3422, 1598), (3413, 1575), (3425, 1550), (3435, 1525), (3436, 1500), (3424, 1450), (3407, 1400),
        (3386, 1350), (3361, 1300), (3347, 1275), (3330, 1250), (3306, 1218), (3302, 1140), (3318, 1121),
        (3400, 1119), (3432, 1110)]
GRIP_GROOVES = [(1279, 3445, 3554), (1332, 3475, 3590), (1386, 3497, 3624), (1438, 3517, 3650),
                (1491, 3529, 3673), (1544, 3531, 3681)]
# Folded stock: one side plate (stamped steel), its holes and the pressed rib.
STOCK_PLATE = [(2350, 655), (2800, 654), (2860, 661), (2920, 677), (3040, 714), (3160, 751), (3280, 789),
               (3400, 827), (3460, 846), (3510, 862), (3555, 888), (3572, 935), (3560, 985), (3520, 1003),
               (3480, 995), (3460, 969), (3340, 930), (3220, 893), (3100, 854), (2980, 818), (2860, 810),
               (2800, 810), (2430, 810), (2350, 806)]
STOCK_LIP = [(2350, 655), (2800, 654), (2860, 661), (3040, 714), (3280, 789), (3400, 827)]
STOCK_HOLES = [2434, 2548, 2664, 2779]
STOCK_HOLE_PY = 731
STOCK_HOLE_R = MM(37)
STOCK_RIB = ((2935, 742), (3450, 900))
PIVOT = (3515, 945)
STOCK_HW = 0.0222          # outer face of the side plates
PLATE_T = 0.0022
BUTT = [(2226, 358), (2360, 361), (2371, 380), (2366, 460), (2342, 640), (2338, 720), (2334, 790), (2172, 788),
        (2165, 772), (2186, 640), (2213, 400)]
HOOK = [(2296, 362), (2298, 320), (2302, 300), (2309, 280), (2318, 260), (2330, 240), (2350, 220), (2380, 193),
        (2420, 176), (2460, 168), (2500, 165), (2540, 166), (2580, 172), (2620, 182), (2660, 197), (2700, 218),
        (2727, 240), (2752, 260), (2773, 280), (2789, 300), (2810, 340), (2821, 380), (2824, 430), (2821, 490),
        (2817, 532)]
HOOK_R = MM(32)
TRIGGER_PLATE = [(2902, 1112), (3105, 1112), (3105, 1205), (3040, 1202), (2965, 1182), (2935, 1152), (2905, 1126)]
SAFETY = [(3105, 1112), (3150, 1112), (3152, 1180), (3148, 1204), (3128, 1212), (3106, 1204)]
TRIGGER = [(3275, 1114), (3299, 1114), (3297, 1160), (3291, 1200), (3279, 1230), (3256, 1245), (3250, 1236),
           (3264, 1214), (3273, 1190), (3276, 1150)]
GUARD = [(3120, 1200), (3118, 1226), (3136, 1254), (3176, 1277), (3218, 1279), (3260, 1263), (3292, 1238),
         (3306, 1200), (3307, 1145), (3303, 1116)]
FRONT_SIGHT = [(365, 864), (370, 778), (437, 777), (450, 862)]

PART_IDS = {"body": 0, "pump": 1, "bolt": 2, "load_round": 3}
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


def chaikin(pts, n=2, closed=True):
    p = np.asarray(pts, float)
    for _ in range(n):
        q = np.roll(p, -1, 0)
        p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p


def profile(name, pts, width, y=0.0, smooth=1):
    """Side outline (photo px) extruded across Y."""
    xz = chaikin(traced(pts), smooth) if smooth else traced(pts)
    return hs.side_profile(name, [tuple(p) for p in xz], width, y=y)


def stadium(name, a, b, half_h, y, depth, verts=12):
    """A slot with round ends from photo point a to b (px), half height half_h (m), cut depth across Y."""
    ax, az = P(*a)
    bx, bz = P(*b)
    tx, tz = bx - ax, bz - az
    ln = math.hypot(tx, tz)
    ux, uz = tx / ln, tz / ln
    nx, nz = -uz, ux
    pts = []
    n = max(4, verts // 2)
    for (cx, cz), a0 in (((bx, bz), -90), ((ax, az), 90)):
        for i in range(n + 1):
            t = math.radians(a0 + 180 * i / n)
            c, s = math.cos(t), math.sin(t)
            pts.append((cx + (ux * c + nx * s) * half_h, cz + (uz * c + nz * s) * half_h))
    return hs.side_profile(name, pts, depth, y=y)


# ---------------------------------------------------------------- SDF helpers
def ss(e0, e1, t):
    t = np.clip((t - F32(e0)) / F32(e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rinter(a, b, r):
    a = a + F32(r)
    b = b + F32(r)
    return np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0) - F32(r)


def poly_sdf(x, z, V2):
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


class FnPrim(sdf.Prim):
    def __init__(self, lo, hi_, f):
        self.lo, self.hi, self.f = np.asarray(lo, float), np.asarray(hi_, float), f

    def aabb(self):
        return self.lo, self.hi

    def __call__(self, x, y, z):
        return self.f(x, y, z)


def carve(f, band, depth):
    """Cuts a groove `depth` deep where band < 0 (band: signed distance to the groove's sides)."""
    return np.maximum(f, np.minimum(-band, f + F32(depth)))


def sculpt(name, lo, hi_, model, h, m):
    lo = tuple(v + h * k for v, k in zip(lo, (0.371, 0.413, 0.297)))
    grid = sdf.Grid(lo, hi_, h)
    print(f"spas12: sculpting {name} on {grid.shape} ({grid.size / 1e6:.1f} M cells)")
    F = model.evaluate(grid)
    me = sdf.to_mesh(name, F, grid)
    del F
    ob = hs.link(bpy.data.objects.new(name, me))
    me.materials.append(m)
    me.shade_smooth()
    PART_OF[ob.name] = CURRENT[0]
    return ob


def decimated(ob, tris):
    dec = ob.modifiers.new("decimate", "DECIMATE")
    dec.ratio = min(1.0, tris / max(1, 2 * len(ob.data.polygons)))
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    return ob


# ---------------------------------------------------------------- the pump (sculpt)
FORE_OUT = chaikin(traced(FORE), 2)
FORE_LO = (PX(2205), -0.032, PZ(1230))
FORE_HI = (PX(1005), 0.032, PZ(896))


def fore_hw(x, z):
    """Half width: 50 mm across the nose, 57 mm round the hand, the lip a little proud."""
    hw = F32(0.0250) + F32(0.0035) * ss(PX(1600), PX(1720), x)
    return hw + F32(0.0012) * ss(PX(2140), PX(2175), x)


def fore_f(x, y, z):
    d2 = poly_sdf(x, z, FORE_OUT)
    f = rinter(d2, np.abs(y) - fore_hw(x, z), 0.0105)
    # The tube runs through it (keeps the bake off hidden faces).
    tube = np.sqrt((z - F32(TUBE_Z)) ** 2 + y * y) - F32(TUBE_R + 0.0006)
    return np.maximum(f, -tube)


def fore_model():
    m = sdf.Model()
    m.add(FnPrim(FORE_LO, FORE_HI, fore_f))
    z_short = PZ(1110)

    def grooves(f, x, y, z):
        for px in FORE_GROOVES_FRONT:
            band = np.abs(x - F32(PX(px))) - F32(0.00095)
            band = np.where(z > F32(z_short), band, F32(1.0))
            f = carve(f, band, 0.0016)
        for px in FORE_GROOVES_REAR:
            band = np.abs(x - F32(PX(px))) - F32(0.00095)
            f = carve(f, band, 0.0018)
        # The selector hole on the left side, and its pin on the right.
        hx, hz = P(1395, 1155)
        band = np.sqrt((x - F32(hx)) ** 2 + (z - F32(hz)) ** 2) - F32(MM(19))
        f = carve(f, np.where(y > 0, band, F32(1.0)), 0.004)
        return f
    m.fn(FORE_LO, FORE_HI, grooves)
    return m


def build_pump():
    part("pump")
    if hi():
        ob = sculpt("pump_high", FORE_LO, FORE_HI, fore_model(), 0.0010 if args.fast else 0.00045, M_POLY)
    else:
        ob = decimated(sculpt("pump_low", FORE_LO, FORE_HI, fore_model(), 0.0011, M_POLY), args.low_fore)
    hs.PARTS.append(ob)
    # The selector button in its hole (left) and the pin through (right).
    hx, hz = P(1395, 1155)
    finish(hs.cyl_y("selector", MM(15), 0.004, (hx, 0.0245, hz), verts=24), M_REC, bevel=0.0007)
    finish(hs.cyl_y("selector_pin", 0.0028, 0.002, (PX(1583), -0.0262, PZ(1180)), verts=16), M_STEEL, bevel=0.0004)
    # Action bars from the back of the pump into the receiver (seen when it is racked).
    for sy in (1, -1):
        finish(hs.box(f"action_bar{sy}", (MM(560), 0.0022, 0.0055),
                      ((PX(2190) + PX(2750)) / 2, sy * 0.0128, PZ(1105))), M_STEEL, bevel=0.0004)
    part("body")


# ---------------------------------------------------------------- grip and stock housing (sculpt)
GRIP_OUT = chaikin(traced(GRIP), 2)
GRIP_LO = (PX(3765), -0.026, PZ(1625))
GRIP_HI = (PX(3395), 0.026, PZ(828))


def grip_hw(x, z):
    """Housing 38 mm wide (it wraps the receiver's tail), the grip 31 mm."""
    below = ss(PZ(1205), PZ(1265), z)
    return F32(0.0190) + (F32(0.0155) - F32(0.0190)) * below


def grip_f(x, y, z):
    return rinter(poly_sdf(x, z, GRIP_OUT), np.abs(y) - grip_hw(x, z), 0.0068)


def grip_model():
    m = sdf.Model()
    m.add(FnPrim(GRIP_LO, GRIP_HI, grip_f))

    def grooves(f, x, y, z):
        for py, xa, xb in GRIP_GROOVES:
            band = np.abs(z - F32(PZ(py))) - F32(0.0008)
            inside = (x < F32(PX(xa))) & (x > F32(PX(xb)))
            f = carve(f, np.where(inside, band, F32(1.0)), 0.0012)
        return f
    m.fn(GRIP_LO, GRIP_HI, grooves)
    return m


def build_grip():
    if hi():
        ob = sculpt("grip_high", GRIP_LO, GRIP_HI, grip_model(), 0.0009 if args.fast else 0.00042, M_POLY)
    else:
        ob = decimated(sculpt("grip_low", GRIP_LO, GRIP_HI, grip_model(), 0.0010, M_POLY), args.low_grip)
    hs.PARTS.append(ob)
    for px, py in ((3580, 1190), (3700, 1515)):
        x, z = P(px, py)
        for side in (1, -1):
            yy = side * (grip_hw(F32(x), F32(z)) + 0.0002)
            finish(hs.cyl_y(f"grip_screw{px}{side}", 0.0034, 0.0012, (x, float(yy), z), verts=20), M_STEEL,
                   bevel=0.0004)
            if hi():
                finish(hs.box(f"grip_slot{px}{side}", (0.0062, 0.0008, 0.0008), (x, float(yy) + side * 0.0005, z),
                              rot=(0, math.radians(-10), 0)), M_DARK, bevel=0)
    # Stock latch on top of the housing.
    finish(hs.box("stock_latch", (0.010, 0.012, 0.004), (PX(3552), 0, PZ(838))), M_REC, bevel=0.0012)


# ---------------------------------------------------------------- receiver, trigger group
def rrect(hw, zb, zt, rt, rb, n):
    pts = []
    for cy, cz, r, a0 in ((hw - rb, zb + rb, rb, -90), (hw - rt, zt - rt, rt, 0), (-hw + rt, zt - rt, rt, 90),
                          (-hw + rb, zb + rb, rb, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def build_receiver():
    n = 5 if hi() else 2
    rec = hs.section("receiver", rrect(REC_HW, REC_ZB, REC_ZT, 0.0040, 0.0020, n), REC_X0, REC_X1)
    # Ejection port on the right, loading port underneath.
    hs.cut(rec, hs.box("eject_port", (PX(2640) - PX(2900), 0.012, PZ(865) - PZ(960)),
                       ((PX(2640) + PX(2900)) / 2, -REC_HW, (PZ(865) + PZ(960)) / 2)))
    hs.cut(rec, hs.box("load_port", (PX(2560) - PX(2895), 0.023, 0.016),
                       ((PX(2560) + PX(2895)) / 2, 0, REC_ZB)))
    finish(rec, M_REC, bevel=0.0007)
    # Inside the ports: the dark action, the shell lifter.
    finish(hs.box("port_inside", (PX(2645) - PX(2895), 0.004, PZ(868) - PZ(958)),
                  ((PX(2645) + PX(2895)) / 2, -0.0095, (PZ(868) + PZ(958)) / 2)), M_DARK, bevel=0)
    finish(hs.box("lifter", (PX(2565) - PX(2890), 0.021, 0.003), ((PX(2565) + PX(2890)) / 2, 0, REC_ZB + 0.0075)),
           M_STEEL, bevel=0.0004)
    # The bare aluminium lower edge strip.
    finish(hs.box("rec_strip", (REC_X1 - REC_X0 - 0.002, 2 * REC_HW + 0.0004, PZ(1086) - PZ(1100)),
                  ((REC_X0 + REC_X1) / 2, 0, (PZ(1086) + PZ(1100)) / 2)), M_ALU, bevel=0.0005)
    # Bolt release (left), pins.
    bx, bz = P(2610, 1050)
    finish(hs.cyl_y("bolt_release", MM(22), 0.003, (bx, REC_HW + 0.0010, bz), verts=28), M_STEEL, bevel=0.0009)
    for px in (3110, 3270):
        for side in (1, -1):
            finish(hs.cyl_y(f"rec_pin{px}{side}", MM(8), 0.0012, (PX(px), side * (REC_HW + 0.0002), PZ(1055)),
                            verts=16), M_STEEL, bevel=0.0003)
    text("mark_left", "SPAS 12 - L.FRANCHI S.p.A. - BRESCIA - MADE IN ITALY", 0.0033,
         (PX(2620), REC_HW + 0.00005, PZ(905)), (PI / 2, 0, PI), M_MARK)
    text("mark_serial", "FRANCHI", 0.0042, (PX(3060), -REC_HW - 0.00005, PZ(1000)), (PI / 2, 0, 0), M_MARK)

    # Trigger group: the bare aluminium plate, the lever safety, trigger and guard.
    finish(profile("trigger_plate", TRIGGER_PLATE, 0.021), M_ALU, bevel=0.0010)
    finish(hs.cyl_y("tg_pin", MM(22), 0.0218, (PX(3020), 0, PZ(1132)), verts=24), M_ALU, bevel=0.0006)
    finish(hs.cyl_y("tg_pin2", MM(9), 0.0216, (PX(3015), 0, PZ(1175)), verts=12), M_STEEL, bevel=0.0003)
    finish(profile("safety", SAFETY, 0.010), M_REC, bevel=0.0012)
    finish(profile("trigger", TRIGGER, 0.0062), M_REC, bevel=0.0010)
    guard = hs.tube_path("guard", [V((PX(px), 0, PZ(py))) for px, py in GUARD], MM(8), width_scale=2.0,
                         resolution=8)
    finish(guard, M_ALU, bevel=0, smooth=True)


def build_bolt():
    part("bolt")
    x0, x1 = PX(2895), PX(2648)
    finish(hs.box("bolt_body", (x1 - x0, 0.004, PZ(872) - PZ(955)), ((x0 + x1) / 2, -0.0128, PZ(913))), M_STEEL,
           bevel=0.0008)
    if hi():
        finish(hs.box("extractor", (0.012, 0.001, 0.003), (x1 - 0.008, -0.0151, PZ(895))), M_STEEL, bevel=0.0003)
    hx = PX(2700)
    finish(hs.cyl_y("bolt_handle", 0.0036, 0.016, (hx, -0.0215, PZ(913)), verts=16), M_STEEL, bevel=0.0006)
    finish(hs.cyl_y("bolt_knob", 0.0058, 0.008, (hx, -0.0315, PZ(913)), verts=24), M_STEEL, bevel=0.0018)
    part("body")


# ---------------------------------------------------------------- heat shield, barrel, tube, sights
def build_front():
    sh = profile("shield", SHIELD, 2 * SHIELD_HW, smooth=1)
    for sy in (1, -1):
        for i, (a, b) in enumerate(SHIELD_TOP_SLOTS):
            hs.cut(sh, stadium(f"shield_slot{sy}_{i}", (a + 10, 885), (b - 10, 885), MM(10), sy * SHIELD_HW,
                               0.006))
        for i, (a, b, py) in enumerate(SHIELD_LOW_SLOTS):
            hs.cut(sh, stadium(f"shield_low{sy}_{i}", (a + 10, py), (b - 10, py), MM(10), sy * SHIELD_HW, 0.006))
    finish(sh, M_SHIELD, bevel=0.0022, angle=40)
    finish(hs.box("shield_lug", (MM(36), 0.010, MM(12)), (PX(1102), 0, PZ(842))), M_SHIELD, bevel=0.0008)
    # Dark backing inside the slots (the barrel and the bars behind them).
    finish(hs.box("shield_core", (PX(1100) - PX(2530), 2 * SHIELD_HW - 0.0058, PZ(870) - PZ(990)),
                  ((PX(1100) + PX(2530)) / 2, 0, (PZ(870) + PZ(990)) / 2)), M_DARK, bevel=0)
    finish(hs.box("shield_core_low", (PX(2192) - PX(2530), 2 * SHIELD_HW - 0.0058, PZ(990) - PZ(1140)),
                  ((PX(2192) + PX(2530)) / 2, 0, (PZ(990) + PZ(1140)) / 2)), M_DARK, bevel=0)

    # Barrel, the knurled thread protector, the bore.
    finish(hs.cyl_x("barrel", BARREL_R, PX(2200), PX(335), verts=40), M_BARREL, bevel=0.0003)
    choke = hs.lathe_x("choke", [(PX(338), BARREL_R + 0.0002), (PX(330), MM(54)), (PX(300), MM(54.5)),
                                 (PX(296), MM(52.5)), (PX(250), MM(52.5)), (PX(246), MM(56.5)),
                                 (PX(152), MM(56.5)), (PX(140), MM(55.5)), (PX(120), MM(52)),
                                 (MUZZLE_X, MM(48))], verts=48)
    finish(choke, M_BARREL, bevel=0.0004)
    if hi():
        for i in range(36):
            a = 2 * PI * i / 36
            r = MM(56.5)
            finish(hs.box(f"knurl{i}", ((PX(155) - PX(242)), 0.0012, 0.0012),
                          ((PX(155) + PX(242)) / 2, r * math.cos(a), r * math.sin(a)), rot=(a, 0, 0)), M_BARREL,
                   bevel=0)
    finish(hs.box("choke_notch", (MM(18), 0.003, MM(18)), (PX(280), MM(52), PZ(918))), M_DARK, bevel=0)
    finish(hs.cyl_x("bore", BORE_R, MUZZLE_X - 0.03, MUZZLE_X + 0.0002, verts=32), M_DARK, bevel=0)

    # Front sight: a band round the barrel and the tall post.
    finish(hs.cyl_x("fs_band", BARREL_R + 0.0014, PX(452), PX(345), verts=40), M_BARREL, bevel=0.0006)
    finish(profile("fs_post", FRONT_SIGHT, 0.0045, smooth=0), M_BARREL, bevel=0.0006)

    # Magazine tube, its domed cap, the barrel band (sling flange and lug) and the knurled nut.
    finish(hs.cyl_x("mag_tube", TUBE_R, PX(2200), PX(185), verts=40, z=TUBE_Z), M_BARREL, bevel=0.0004)
    cap = hs.lathe_x("tube_cap", [(PX(186), TUBE_R), (PX(176), TUBE_R - 0.0008), (PX(169), TUBE_R - 0.004),
                                  (PX(166), 0.0001)], verts=40)
    cap.location.z = TUBE_Z
    bpy.ops.object.select_all(action="DESELECT")
    cap.select_set(True)
    bpy.context.view_layer.objects.active = cap
    bpy.ops.object.transform_apply(location=True)
    finish(cap, M_BARREL, bevel=0)
    finish(hs.cyl_x("band_flange", MM(70), PX(840), PX(800), verts=40, z=TUBE_Z), M_BARREL, bevel=0.0008)
    finish(hs.cyl_x("band_ring", MM(60), PX(860), PX(838), verts=40, z=TUBE_Z), M_BARREL, bevel=0.0005)
    finish(profile("band_lug", [(832, 1110), (872, 1110), (868, 1168), (852, 1178), (836, 1168)], 0.006),
           M_BARREL, bevel=0.0010)
    finish(hs.cyl_y("band_lug_hole", MM(9), 0.0064, (PX(852), 0, PZ(1150)), verts=16), M_DARK, bevel=0)
    for i, (a, b) in enumerate(((862, 922), (930, 990))):
        finish(hs.cyl_x(f"nut{i}", MM(65), PX(b), PX(a), verts=40, z=TUBE_Z), M_BARREL, bevel=0.0006)
        if hi():
            for k in range(30):
                t = 2 * PI * k / 30
                r = MM(65)
                finish(hs.box(f"nut{i}_knurl{k}", (PX(a + 4) - PX(b - 4), 0.0014, 0.0012),
                              ((PX(a) + PX(b)) / 2, r * math.cos(t), TUBE_Z + r * math.sin(t)), rot=(t, 0, 0)),
                       M_BARREL, bevel=0)


# ---------------------------------------------------------------- the folded stock
def build_stock():
    for sy in (1, -1):
        y = sy * (STOCK_HW - PLATE_T / 2)
        plate = profile(f"stock_plate{sy}", STOCK_PLATE, PLATE_T, y=y, smooth=1)
        for i, px in enumerate(STOCK_HOLES):
            x, z = P(px, STOCK_HOLE_PY)
            hs.cut(plate, hs.cyl_y(f"stock_hole{sy}{i}", STOCK_HOLE_R, 0.01, (x, y, z), verts=40))
        # The pressed rib: a shallow groove on the outside.
        hs.cut(plate, stadium(f"stock_rib{sy}", *STOCK_RIB, MM(27), sy * STOCK_HW, 0.0016, verts=20))
        finish(plate, M_STOCK, bevel=0.0006)
        # Rolled lip along the top edge, bent inward.
        for k, (a, b) in enumerate(zip(STOCK_LIP[:-1], STOCK_LIP[1:])):
            ax, az = P(*a)
            bx, bz = P(*b)
            ang = math.atan2(bz - az, bx - ax)
            finish(hs.box(f"stock_lip{sy}{k}", (math.hypot(bx - ax, bz - az) + 0.002, 0.0060, 0.0018),
                          ((ax + bx) / 2, sy * (STOCK_HW - 0.0030), (az + bz) / 2 - 0.0009), rot=(0, -ang, 0)),
                   M_STOCK, bevel=0.0005)
        # Pivot hub and its pin.
        px, pz = P(*PIVOT)
        finish(hs.cyl_y(f"pivot_hub{sy}", MM(52), 0.0030, (px, sy * (STOCK_HW + 0.0010), pz), verts=40), M_STOCK,
               bevel=0.0009)
        finish(hs.cyl_y(f"pivot_pin{sy}", MM(28), 0.0020, (px, sy * (STOCK_HW + 0.0030), pz), verts=28), M_STEEL,
               bevel=0.0006)
    # Cross web behind the butt plate.
    finish(hs.box("stock_web", (0.006, 2 * STOCK_HW - 0.002, PZ(660) - PZ(795)),
                  (PX(2360), 0, (PZ(660) + PZ(795)) / 2)), M_STOCK, bevel=0.0006)
    # The butt plate, standing up at the front, and the arm hook over it.
    butt = profile("butt_plate", BUTT, 0.044, smooth=1)
    finish(butt, M_STOCK, bevel=0.0026, angle=40)
    for px in (2235, 2298):
        finish(hs.box(f"butt_slot{px}", (MM(26), 0.0446, MM(7)), (PX(px), 0, PZ(620))), M_DARK, bevel=0)
    finish(hs.cyl_y("butt_rivet", MM(17), 0.0452, (PX(2222), 0, PZ(746)), verts=24), M_STEEL, bevel=0.0008)
    hook = hs.tube_path("hook", [V((PX(px), 0, PZ(py))) for px, py in HOOK], HOOK_R, resolution=10)
    finish(hook, M_STOCK, bevel=0, smooth=True)
    finish(hs.cyl_z("hook_cap", HOOK_R + MM(4), MM(16), (PX(2817), 0, PZ(538)), verts=24), M_POLY, bevel=0.0012)
    finish(hs.cyl_z("hook_collar", HOOK_R + MM(6), MM(26), (PX(2296), 0, PZ(368)), verts=24), M_STOCK, bevel=0.0010)


# ---------------------------------------------------------------- the shell at the loading port
def build_round():
    part("load_round")
    x0 = PX(2925)                       # head at the back of the port, nose toward the tube
    z = TUBE_Z
    finish(hs.cyl_x("hull", 0.0101, x0 + 0.014, x0 + 0.070, verts=24, z=z), M_HULL, bevel=0.0005)
    finish(hs.cyl_x("head", 0.0104, x0, x0 + 0.016, verts=24, z=z), M_BRASS, bevel=0.0004)
    finish(hs.cyl_x("rim", 0.0112, x0 - 0.0012, x0 + 0.0002, verts=24, z=z), M_BRASS, bevel=0.0002)
    finish(hs.cyl_x("crimp", 0.0060, x0 + 0.070, x0 + 0.0703, verts=16, z=z), M_DARK, bevel=0)
    part("body")


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_grip()
    build_receiver()
    build_bolt()
    build_front()
    build_pump()
    build_stock()
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
    print(f"spas12 {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


EXPLODE = {"body": 0.0, "pump": -0.35, "bolt": 0.35, "load_round": -0.7}


def explode(ob, sign):
    """Moves the parts apart along Y for the bake (they sit within a millimetre of the body)."""
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
    objs = []
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
        objs.append(ob)
        print(f"spas12: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    floor.location = (0, 0, -0.17)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.25, 0, -0.02), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.2, -1.3, 1.2), 70, 1.8, sy=0.6)
    area("key_l", (0.0, 1.4, 1.0), 60, 1.8, sy=0.6)
    area("strip_top", (0.25, 0.0, 1.2), 40, 2.4, sy=0.2)
    area("fill", (0.8, 1.3, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.8, -0.4, 0.5), 50, 0.8, (1.0, 0.82, 0.62))
    area("kick", (-1.3, 0.3, 0.2), 28, 1.0, (0.9, 0.95, 1.0))
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
    print(f"spas12: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((0.30, -2.2, 0.0), (0.30, 0, -0.01), 70, 0.0),
        "left_side": ((0.30, 2.2, 0.0), (0.30, 0, -0.01), 70, 0.0),
        "beauty": ((0.95, 1.05, 0.45), (0.25, 0, -0.01), 45, 8.0),
        "rear": ((-0.55, -0.85, 0.40), (0.15, 0, 0.0), 40, 8.0),
        "stock": ((0.05, 0.55, 0.25), (-0.02, 0.0, 0.05), 50, 4.0),
        "pump": ((0.35, 0.50, -0.12), (0.33, 0.0, -0.035), 50, 4.0),
        "front": ((0.95, 0.35, 0.05), (0.55, 0.0, -0.01), 50, 4.0),
        # Roughly the player's hip view: eye behind and left of the gun, above it.
        "fp": ((-0.50, 0.17, 0.17), (0.80, 0.10, 0.13), 0, 0.0),
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
    scene.render.resolution_x, scene.render.resolution_y = 1920, 879
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
    cx, cz = P(1920, 878.5)
    cam.location = (cx, 1.0, cz)
    cam.rotation_euler = (V((cx, 0, cz)) - V((cx, 1.0, cz))).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"spas12: overlay {path}")


# ---------------------------------------------------------------- run
if args.fast:
    args.samples = min(args.samples, 24)
if args.out:
    high = build(hs.HIGH, "spas12_high")
    low = build(hs.LOW, "spas12_low")
    bakeutil.unwrap(low, boost={M_REC.name: 1.35, M_SHIELD.name: 1.1, M_STOCK.name: 1.15, M_BARREL.name: 1.0,
                                M_POLY.name: 1.0, M_GRIPTEX.name: 1.0, M_ALU.name: 1.2, M_STEEL.name: 1.2,
                                M_MARK.name: 1.6, M_DARK.name: 0.4, M_BRASS.name: 1.2, M_HULL.name: 1.0},
                    angle_deg=35.0)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    explode(high, 1)
    explode(low, 1)
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "spas12", cage=0.0015, ray=0.005,
                                 ao_distance=0.02, grime=0.35, log=print)
    bpy.data.objects.remove(high)
    explode(low, -1)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "spas12", emission_strength=1.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"spas12: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview or args.overlay:
    high = build(hs.HIGH, "spas12_high")
    if args.overlay:
        render_overlay(args.overlay)
    else:
        render_previews(args.preview.rsplit(".", 1)[0])
