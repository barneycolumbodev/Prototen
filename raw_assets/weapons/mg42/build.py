"""MG42, traced from a photo of a real one (owner, 2026-11-23), 7.62x51 in the game.

Owner brief (2026-11-23): "the way you used a photo reference to make the AUG
and the SPAS 12 look dead on realistic ... change the MG42 model in the same
way ... it's missing something that makes it identifiable as that gun." Don't
change any gameplay. (The first model, 2026-11-01, was a chrome-and-black
"MG42-style" gun with a round, MG34-like jacket.)

Traced, not guessed: every outline below is in pixels of the reference photo
"MG42 1 noBG.jpg" (Phanatic, Wikimedia Commons, CC BY-SA 4.0; a left-side shot
of a real MG42 with its background removed, 3008 x 1332). The photo is turned
0.36 degrees (the jacket's top edge climbs 4 px over 630), so `P()` levels it
by a shear: py_level = py + (px - 55) * TILT. Bore axis: row 345.5 (the centre
of the flash hider). Scale: 1,220 mm overall (the factory figure) over 2,864 px
= 2.3475 px/mm, which gives the real 46-52 mm jacket and a 17.5 mm round hole.
`P(px, py)` turns photo pixels into metres. `--overlay out.png --photo <jpg>`
renders an orthographic left view at the photo's scale and draws its outline
over the photo, for the match.

What makes it an MG42 (and was missing): the squarish stamped barrel jacket
with one round hole and six long oval slots down each side and the big
barrel-change opening at the right rear; the ribbed recoil booster and conical
flash hider; the tall folding front sight on its sloped base; the tangent rear
sight on the jacket; the stamped receiver with the long feed cover hinged at
the front (three domed heads over the feed, the hump, the latch at the rear);
the angled pistol grip, a steel frame with red-brown bakelite panels, the big
trigger guard; the slim black bakelite stock with its fishtail butt; the bipod
on the jacket front, legs folded back.

Kept for the game (not on a real MG42): the clamp-on vertical foregrip (hip
fire; the left hand of fp_arms_mg42 holds it, so it stays exactly where it
was), the 150-round box on the left feeding a short visible belt, and the
Fire-Control Link readout (design §3.5). The pistol grip sits where the right
hand of fp_arms_mg42 holds it (the photo is placed so the grip's centre line
meets the arms' grip frame 50 mm under the bore).

Finish: the real one (owner wanted it "dead on realistic"): phosphated and
painted dark grey steel, a blued barrel, red-brown bakelite grip panels, a
black bakelite stock, a bright steel stock ring.

Parts (per-face part id, split after the bake):
  body       everything that doesn't move
  cover      the feed cover (hinged at its front: the rear swings up on reloads)
  magazine   the ammo box
  belt       the rounds between the box and the feed tray
  stock      hidden while aiming

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip (photo x 1857). Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/mg42/build.py --out assets/weapons/mg42/mg42.gltf --tex 4096 \
      --preview docs/previews/mg42.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/mg42.png [--only side,fp]
  Photo match: --overlay /tmp/mg42_overlay.png --photo <path to MG42_1_noBG.jpg>
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
ap.add_argument("--emission-size", type=int, default=256, help="emission map is mostly black: store it small")
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--overlay", default="", help="render the left view for the photo match to this png")
ap.add_argument("--photo", default="", help="the reference photo (outline drawn over it)")
ap.add_argument("--count", action="store_true", help="build LOW only and print its triangle count")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
PI = math.pi

# ---------------------------------------------------------------- materials
M_STEEL = mat("phosphate_steel", (0.040, 0.041, 0.044), 0.55, 0.6, wear=(0.36, 0.36, 0.37), wear_rough=0.28,
              bump_scale=1300, bump_strength=0.05)
M_DARK = mat("dark_steel", (0.022, 0.022, 0.024), 0.48, 0.7, wear=(0.30, 0.30, 0.31), wear_rough=0.25,
             bump_scale=1000, bump_strength=0.04)
M_BLUED = mat("barrel_blued", (0.03, 0.031, 0.036), 0.38, 1.0, wear=(0.25, 0.25, 0.27), wear_rough=0.2)
M_BORE = mat("bore_dark", (0.005, 0.005, 0.006), 0.7, 0.3)
M_BRIGHT = mat("bright_steel", (0.62, 0.62, 0.63), 0.22, 1.0, brushed=0.04)
M_GRIP = mat("bakelite_red", (0.105, 0.028, 0.016), 0.38, 0.0, wear=(0.20, 0.07, 0.045), wear_rough=0.3,
             bump_scale=1800, bump_strength=0.06)
M_STOCK = mat("bakelite_black", (0.022, 0.021, 0.021), 0.46, 0.0, wear=(0.16, 0.14, 0.12), wear_rough=0.4,
              bump_scale=1500, bump_strength=0.08)
M_BRASS = mat("brass", (0.78, 0.56, 0.24), 0.26, 1.0, wear=(0.9, 0.75, 0.45), wear_rough=0.15)
M_COPPER = mat("gilding_metal", (0.72, 0.38, 0.22), 0.3, 1.0)
M_GLASS = mat("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = mat("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_PAINT = mat("stencil_paint", (0.62, 0.5, 0.12), 0.65, 0.0)
M_MARK = mat("engraving", (0.30, 0.30, 0.31), 0.45, 0.8)
M_BOX = mat("box_olive", (0.055, 0.058, 0.040), 0.6, 0.35, wear=(0.30, 0.30, 0.28), wear_rough=0.3,
            bump_scale=1200, bump_strength=0.05)
MATERIALS = [M_STEEL, M_DARK, M_BLUED, M_BORE, M_BRIGHT, M_GRIP, M_STOCK, M_BRASS, M_COPPER, M_GLASS, M_AMBER,
             M_PAINT, M_MARK, M_BOX]

# ---------------------------------------------------------------- the trace
PX_MM = 2.3475        # photo pixels per millimetre (1,220 mm over 2,864 px)
X0_PX = 1857          # photo x of the weapon origin (bore axis above the grip)
BORE_PY = 345.5       # levelled photo row of the bore axis
TILT = 0.0063         # the photo's turn: rows to add per column to level it


def is_high():
    """Small details that only need to reach the LOW model through the bake."""
    return hs.D["seg"] > 1


def P(px, py):
    """Photo pixel -> (x, z) in metres, weapon space."""
    return ((X0_PX - px) / PX_MM / 1000.0, (BORE_PY - (py + (px - 55) * TILT)) / PX_MM / 1000.0)


def PX(px):
    return (X0_PX - px) / PX_MM / 1000.0


def MM(px_len):
    return px_len / PX_MM / 1000.0


def trace(pts):
    return [P(px, py) for px, py in pts]


# Key stations (metres).
MUZZLE_X = PX(49)                      # 0.770
JK_X0, JK_X1 = PX(1450), PX(300)       # barrel jacket, rear / front
JK_TOP, JK_BOT = 0.0218, -0.0300       # jacket top / bottom (levelled rows 294 / 416)
JK_HW = 0.0228                         # jacket half width
JK_T = 0.0016                          # jacket wall
REC_X0, REC_X1 = PX(2490), PX(1450)    # receiver, rear end / front
REC_HW = 0.0245
REC_BOT = -0.0305
SIGHT_Z = 0.0705                       # sight line (front post top 69.9, rear notch top 71.0 mm)
FEED_X0, FEED_X1 = PX(1790), PX(1555)  # feed opening in the left wall
TRAY_Z = P(1650, 310)[1]               # top of the feed tray (z 0.0108)
COVER_LOW_Z = P(1650, 270)[1]          # underside of the cover over the feed (z 0.0277)
SEAM_Z = P(2050, 322)[1]               # cover / receiver seam behind the feed (z 0.0048)
CART_X0 = FEED_X0 + 0.011              # rear of a belted cartridge (71 mm long)
PART_IDS = {"body": 0, "cover": 1, "magazine": 2, "belt": 3, "stock": 4}
CURRENT = ["body"]
PART_OF = {}                           # object name -> part


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


def rrect(hw, zt, zb, rt, rb, n):
    """Rounded-rectangle section (y, z), corner radii rt (top) and rb (bottom), resampled to n points
    by angle about the centre, so sections of different shapes loft cleanly."""
    pts = []
    k = max(3, n // 16)
    for cy, cz, r, a0 in ((-hw + rb, zb + rb, rb, PI), (hw - rb, zb + rb, rb, 1.5 * PI),
                          (hw - rt, zt - rt, rt, 0.0), (-hw + rt, zt - rt, rt, 0.5 * PI)):
        for i in range(k + 1):
            a = a0 + 0.5 * PI * i / k
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    zc = (zt + zb) / 2
    return resample(pts, n, zc)


def circle(r, zc, n):
    return [(r * math.cos(2 * PI * i / n - PI), zc + r * math.sin(2 * PI * i / n - PI)) for i in range(n)]


def resample(pts, n, zc):
    """Polygon -> n points at even angles about (0, zc) (rays from the centre)."""
    out = []
    m = len(pts)
    for i in range(n):
        a = 2 * PI * i / n - PI
        d = V((math.cos(a), math.sin(a)))
        best = None
        for j in range(m):
            p0, p1 = V((pts[j][0], pts[j][1] - zc)), V((pts[(j + 1) % m][0], pts[(j + 1) % m][1] - zc))
            e = p1 - p0
            den = d.x * e.y - d.y * e.x
            if abs(den) < 1e-12:
                continue
            t = (p0.x * e.y - p0.y * e.x) / den
            u = (p0.x * d.y - p0.y * d.x) / den
            if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
                best = t
        out.append((d.x * best, zc + d.y * best))
    return out


def loft_rings(name, stations):
    """Closed loft along X: stations = [(x, [(y, z) * n]), ...] (same n), rear to front."""
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for y, z in ring] for x, ring in stations]
    n = len(rings[0])
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def stadium(name, cx, cz, length, height, y0, y1):
    """A slot with round ends in the XZ plane, cut through Y from y0 to y1."""
    r = height / 2
    pts = []
    k = 10
    for i in range(k + 1):
        a = -PI / 2 + PI * i / k
        pts.append((cx + length / 2 - r + r * math.cos(a), cz + r * math.sin(a)))
    for i in range(k + 1):
        a = PI / 2 + PI * i / k
        pts.append((cx - length / 2 + r + r * math.cos(a), cz + r * math.sin(a)))
    return hs.side_profile(name, pts, y1 - y0, y=(y0 + y1) / 2)


# ---------------------------------------------------------------- jacket, barrel, booster, sights
def build_jacket():
    n = hs.nverts(64)
    zc = (JK_TOP + JK_BOT) / 2
    outer = rrect(JK_HW, JK_TOP, JK_BOT, 0.005, 0.013, n)
    inner = rrect(JK_HW - JK_T, JK_TOP - JK_T, JK_BOT + JK_T, 0.0035, 0.0115, n)
    # The jacket's nose is pressed round into the booster socket (r 22.4 mm on the bore).
    nose = circle(0.0224, 0.0, n)
    nose_in = circle(0.0224 - JK_T, 0.0, n)

    def blend(a, b, t):
        return [(pa[0] * (1 - t) + pb[0] * t, pa[1] * (1 - t) + pb[1] * t) for pa, pb in zip(a, b)]

    xs = [JK_X0, PX(330), PX(312), PX(300), PX(288)]
    ts = [0.0, 0.0, 0.45, 0.85, 1.0]
    jacket = loft_rings("jacket", [(x, blend(outer, nose, t)) for x, t in zip(xs, ts)])
    hole = loft_rings("jacket_in", [(x, blend(inner, nose_in, t)) for x, t in
                                    zip([JK_X0 - 0.01] + xs[1:-1] + [PX(280)], ts)])
    hs.cut(jacket, hole)
    # Left side (the photo): one round hole, then six oval slots on a 53.8 mm pitch.
    hz = P(440, 347)[1]
    hs.cut(jacket, hs.cyl_y("hole_round_l", MM(20.5), 0.03, (PX(440), JK_HW, hz), verts=32))
    ovals = [(487, 583), (610, 708), (735, 833), (862, 962), (988, 1090), (1115, 1218)]
    for i, (a, b) in enumerate(ovals):
        cx = PX((a + b) / 2)
        hs.cut(jacket, stadium(f"slot_l{i}", cx, hz, MM(b - a), MM(42), 0.005, 0.04))
        if i < 5:  # the right side has the same slots ahead of the barrel-change opening
            hs.cut(jacket, stadium(f"slot_r{i}", cx, hz, MM(b - a), MM(42), -0.04, -0.005))
    hs.cut(jacket, hs.cyl_y("hole_round_r", MM(20.5), 0.03, (PX(440), -JK_HW, hz), verts=32))
    # Barrel-change opening, right rear: the barrel's breech swings out through it.
    hs.cut(jacket, stadium("bc_window", (PX(1440) + PX(1215)) / 2 - 0.0, -0.001, PX(1215) - PX(1440) + 0.0,
                           0.030, -0.04, -0.008))
    # Small round holes along the bottom.
    for i in range(5 if is_high() else 0):
        hs.cut(jacket, hs.cyl_z(f"hole_bot{i}", 0.0042, 0.02, (PX(560 + 125 * i), 0, JK_BOT), verts=16))
    finish(jacket, M_STEEL, bevel=0.0005, segments=2)

    # Left rear of the jacket: the barrel-catch slot and its pivot stud (photo 1260-1286, 1299).
    finish(hs.box("bc_slot_plate", (MM(26), 0.0006, MM(52)), (PX(1273), JK_HW + 0.0001, P(1273, 344)[1])),
           M_DARK, bevel=0.0002)
    finish(hs.cyl_y("bc_stud_l", MM(12), 0.004, (PX(1299), JK_HW + 0.0012, P(1299, 342)[1]), verts=24),
           M_STEEL, bevel=0.0007, segments=2)
    # Barrel-change catch lever on the right rear.
    finish(hs.box("bc_lever", (0.040, 0.004, 0.012), (PX(1300), -JK_HW - 0.002, 0.003)), M_STEEL, bevel=0.0008)
    finish(hs.cyl_y("bc_pivot_r", 0.0045, 0.006, (PX(1299), -JK_HW - 0.003, P(1299, 342)[1]), verts=20),
           M_STEEL, bevel=0.0006)
    # Raised plate where the jacket meets the receiver (photo 1447-1500).
    for sy in (1, -1):
        finish(hs.box(f"jk_rear_plate{sy}", (MM(53), 0.0012, MM(62)),
                      ((PX(1447) + PX(1500)) / 2, sy * (JK_HW + 0.0006), P(1470, 349)[1])), M_STEEL, bevel=0.0004)

    # Barrel (blued) seen through the slots, its bearing ring at the front.
    finish(hs.cyl_x("barrel", 0.0092, JK_X0 - 0.01, PX(250), verts=32), M_BLUED, bevel=0.0003)
    finish(hs.cyl_x("barrel_breech", 0.0125, JK_X0 - 0.01, PX(1330), verts=32), M_BLUED, bevel=0.0004)

    # Booster socket (round end of the jacket), the ribbed recoil booster, the flash hider.
    finish(hs.lathe_x("socket", [(PX(300), 0.0222), (PX(286), 0.0226), (PX(272), 0.0226), (PX(270), 0.0236),
                                 (PX(262), 0.0236), (PX(255), 0.0228)], verts=64), M_STEEL, bevel=0.0004)
    prof = [(PX(255), 0.0222), (PX(210), 0.0222)]
    x = 210
    for i in range(4):  # four fins, 3 grooves (photo 150-210)
        prof += [(PX(x), 0.0238), (PX(x - 11), 0.0238), (PX(x - 11), 0.0196), (PX(x - 16), 0.0196)]
        x -= 16
    prof = prof[:-2] + [(PX(150), 0.0238), (PX(148), 0.0150)]
    booster = hs.lathe_x("booster", prof, verts=64)
    hs.cut(booster, hs.cyl_x("booster_bore", 0.0062, PX(260), PX(140), verts=24))
    for xp in (219, 237):
        vent = hs.cyl_z(f"booster_vent{xp}", MM(6), 0.014, (PX(xp), 0, 0.021), verts=12)
        hs.radial_array(vent, 8, PX(xp))
        hs.cut(booster, vent)
    finish(booster, M_DARK, bevel=0.0004)
    hider = hs.lathe_x("flash_hider", [(PX(150), 0.0115), (PX(140), 0.0117), (PX(100), 0.0135), (PX(60), 0.0151),
                                        (PX(55), 0.0153), (PX(50), 0.0146), (PX(49), 0.0128)], verts=48)
    hs.cut(hider, hs.lathe_x("hider_mouth", [(PX(130), 0.0), (PX(130), 0.0052), (PX(60), 0.0110),
                                             (PX(40), 0.0124), (PX(40), 0.0)], verts=48))
    finish(hider, M_DARK, bevel=0.0005)
    finish(hs.cyl_x("muzzle_dark", 0.0068, PX(132), PX(128), verts=24), M_BORE, bevel=0)

    # Front sight: the sloped base on the jacket nose (two screws), the folding post (photo 255-460).
    base = hs.side_profile("fs_base", trace([(258, 300), (300, 292), (460, 272), (468, 276), (468, 296),
                                             (300, 302), (262, 306)]), 0.016)
    finish(base, M_STEEL, bevel=0.0008)
    for xp in (390, 435):
        finish(hs.cyl_y(f"fs_screw{xp}", MM(7), 0.0170, (PX(xp), 0, P(xp, 285)[1]), verts=16), M_DARK,
               bevel=0.0004)
    post = hs.side_profile("fs_post", trace([(427, 276), (460, 276), (460, 186), (452, 179), (430, 179),
                                             (427, 184), (436, 190), (444, 190), (444, 270), (427, 270)]), 0.0045)
    finish(post, M_DARK, bevel=0.0004)
    finish(hs.box("fs_blade", (0.0018, 0.0016, MM(18)), (PX(434), 0, SIGHT_Z - MM(8))), M_DARK, bevel=0.0002)
    finish(hs.cyl_y("fs_hinge", MM(9), 0.012, (PX(450), 0, P(450, 270)[1]), verts=20), M_STEEL, bevel=0.0004)

    # Rear sight on the jacket top (photo 1210-1440): base block, graduated tangent leaf, slider, notch.
    rs = hs.side_profile("rs_base", trace([(1210, 293), (1210, 245), (1222, 232), (1300, 232), (1427, 236),
                                           (1427, 293)]), 0.020)
    hs.cut(rs, hs.side_profile("rs_slot", trace([(1270, 272), (1370, 272), (1370, 284), (1270, 284)]), 0.03))
    finish(rs, M_STEEL, bevel=0.0008)
    for (xp, yp, r) in ((1397, 258, 13), (1385, 270, 8), (1415, 276, 8)):
        finish(hs.cyl_y(f"rs_hole{xp}", MM(r), 0.0206, (PX(xp), 0, P(xp, yp)[1]), verts=20), M_DARK, bevel=0)
    finish(hs.cyl_y("rs_screw", MM(9), 0.021, (PX(1247), 0, P(1247, 251)[1]), verts=16), M_DARK, bevel=0.0004)
    leaf = hs.side_profile("rs_leaf", trace([(1222, 233), (1427, 219), (1427, 228), (1222, 238)]), 0.014)
    finish(leaf, M_DARK, bevel=0.0004)
    for i in range(14 if is_high() else 0):  # range graduations on the leaf
        xp = 1270 + i * 10.5
        finish(hs.box(f"rs_grad{i}", (0.0010, 0.0146, 0.0012), (PX(xp), 0, P(xp, 228 - i * 0.68)[1] + 0.0006)),
               M_DARK, bevel=0)
    finish(hs.cyl_y("rs_slider", MM(11), 0.024, (PX(1400), 0, P(1400, 225)[1]), verts=24), M_STEEL,
           bevel=0.0008, segments=2)
    notch = hs.side_profile("rs_notch", trace([(1418, 232), (1438, 232), (1442, 175), (1436, 169), (1424, 172),
                                               (1418, 182)]), 0.014)
    hs.cut(notch, hs.box("rs_v", (0.02, 0.0034, 0.010), (PX(1430), 0, SIGHT_Z - 0.001), (0, 0, 0)))
    finish(notch, M_DARK, bevel=0.0003)

    # Bipod on the jacket front: clamp, hinge, legs folded back under the jacket, feet.
    clamp_x0, clamp_x1 = PX(470), PX(380)
    finish(loft_rings("bp_clamp", [(clamp_x0, rrect(JK_HW + 0.0022, JK_TOP + 0.0022, JK_BOT - 0.0022, 0.006, 0.014,
                                                    hs.nverts(48))),
                                   (clamp_x1, rrect(JK_HW + 0.0022, JK_TOP + 0.0022, JK_BOT - 0.0022, 0.006, 0.014,
                                                    hs.nverts(48)))]), M_DARK, bevel=0.0006)
    hx = PX(428)
    finish(hs.box("bp_hinge", (0.026, 0.034, 0.012), (hx, 0, JK_BOT - 0.008)), M_DARK, bevel=0.001)
    finish(hs.cyl_y("bp_pivot", 0.0058, 0.040, (hx, 0, JK_BOT - 0.010), verts=24), M_STEEL, bevel=0.0006)
    leg_len = MM(670)
    for sy in (-1, 1):
        p0 = (hx - 0.004, sy * 0.012, JK_BOT - 0.012)
        p1 = (hx - leg_len, sy * 0.0135, JK_BOT - 0.011)
        finish(hs.cyl_between(f"bp_leg{sy}", p0, p1, 0.0042, verts=16), M_DARK, bevel=0.0003)
        finish(hs.cyl_between(f"bp_leg_in{sy}", (p1[0] + 0.12, p1[1], p1[2]), (p1[0] + 0.02, p1[1], p1[2]),
                              0.0050, verts=16), M_DARK, bevel=0.0004)
        foot = hs.side_profile(f"bp_foot{sy}", [(p1[0] + 0.018, p1[2] + 0.006), (p1[0] - 0.012, p1[2] + 0.004),
                                                (p1[0] - 0.016, p1[2] - 0.007), (p1[0] + 0.020, p1[2] - 0.006)],
                               0.010, y=sy * 0.0145)
        finish(foot, M_DARK, bevel=0.0012)
    # Sling hook under the front, sling bar under the middle (photo 970-1050).
    finish(hs.box("sling_bar", (MM(80), 0.010, 0.004), (PX(1010), 0, JK_BOT - 0.003)), M_STEEL, bevel=0.0008)
    finish(hs.cyl_between("sling_hook", (PX(495), 0, JK_BOT - 0.002), (PX(500), 0, JK_BOT - 0.012), 0.0022,
                          verts=12), M_DARK, bevel=0)

    # Clamp-on vertical foregrip (carrier modification; the left hand holds it here). A U clamp under the
    # jacket, clear of the rear sight on top.
    fx0, fx1 = 0.186, 0.218
    clamp = hs.section("fg_clamp", [(-JK_HW - 0.003, 0.004), (-JK_HW - 0.003, JK_BOT - 0.002),
                                    (-0.012, JK_BOT - 0.008), (0.012, JK_BOT - 0.008),
                                    (JK_HW + 0.003, JK_BOT - 0.002), (JK_HW + 0.003, 0.004),
                                    (JK_HW + 0.0005, 0.004), (JK_HW + 0.0005, JK_BOT + 0.004),
                                    (-JK_HW - 0.0005, JK_BOT + 0.004), (-JK_HW - 0.0005, 0.004)], fx0, fx1)
    finish(clamp, M_DARK, bevel=0.0006)
    finish(hs.cyl_y("fg_bolt", 0.0028, 2 * JK_HW + 0.012, ((fx0 + fx1) / 2, 0, -0.001), verts=16), M_STEEL,
           bevel=0.0004)
    finish(hs.box("fg_block", (0.026, 0.022, 0.012), (0.202, 0, -0.034)), M_DARK, bevel=0.0012)
    grip = hs.cyl_between("fg_grip", (0.203, 0, -0.036), (0.211, 0, -0.130), 0.0165, verts=32)
    for i in range(4):
        z = -0.056 - i * 0.021
        bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(32), minor_segments=8, major_radius=0.0172,
                                         minor_radius=0.0021, location=(0.203 + (z + 0.036) / -0.094 * 0.008, 0, z))
        hs.cut(grip, bpy.context.active_object)
    finish(grip, M_STOCK, bevel=0.0012)
    finish(hs.cyl_between("fg_cap", (0.211, 0, -0.128), (0.2117, 0, -0.136), 0.0176, verts=32), M_DARK,
           bevel=0.0015)


# ---------------------------------------------------------------- receiver and cover
def build_receiver():
    # The stamped box: left and right walls, bottom, with the feed opening on the left and the
    # cocking slot on the right as real openings.
    T = 0.0022
    front_top = P(1500, 258)[1]                       # front block (receiver head) top
    rear_top = P(2420, 287)[1]                        # behind the cover
    # Side outline of a wall (x, z): front head, feed tray, the seam under the cover, the rear end.
    wall_pts = [(REC_X1, REC_BOT), (REC_X1, front_top), (FEED_X1, front_top), (FEED_X1, TRAY_Z),
                (FEED_X0, TRAY_Z), (FEED_X0 - 0.004, SEAM_Z), (PX(2338), SEAM_Z), (PX(2338), rear_top),
                (REC_X0, rear_top), (REC_X0, REC_BOT + 0.004), (REC_X0 + 0.004, REC_BOT)]
    for sy in (1, -1):
        w = hs.side_profile(f"rec_wall{sy}", wall_pts, T, y=sy * (REC_HW - T / 2))
        if sy < 0:  # cocking slot, right side
            hs.cut(w, hs.box("cock_slot", (0.150, 0.01, 0.0055), (0.050, -REC_HW, -0.010)))
        finish(w, M_STEEL, bevel=0.0006)
    # Right side above the tray is open too (the links leave there); the core fills the rest.
    core = [(REC_X1 - 0.001, REC_BOT + 0.002), (REC_X1 - 0.001, front_top - 0.001), (FEED_X1, front_top - 0.001),
            (FEED_X1, TRAY_Z - 0.001), (FEED_X0, TRAY_Z - 0.001), (FEED_X0 - 0.004, SEAM_Z - 0.001),
            (PX(2338), SEAM_Z - 0.001), (PX(2338), rear_top - 0.001), (REC_X0 + 0.001, rear_top - 0.001),
            (REC_X0 + 0.001, REC_BOT + 0.002)]
    finish(hs.side_profile("rec_core", core, 2 * (REC_HW - T)), M_DARK, bevel=0)
    finish(hs.section("rec_bottom", [(-REC_HW + 0.004, REC_BOT - 0.0012), (REC_HW - 0.004, REC_BOT - 0.0012),
                                     (REC_HW, REC_BOT + 0.003), (-REC_HW, REC_BOT + 0.003)], REC_X0, REC_X1),
           M_STEEL, bevel=0.0006)
    # Feed tray lip (photo: the light rounded strip under the opening) and the pawls in the opening.
    finish(hs.side_profile("tray_lip", [(FEED_X1, TRAY_Z), (FEED_X0 + 0.006, TRAY_Z), (FEED_X0 + 0.001, TRAY_Z - 0.006),
                                        (FEED_X0 + 0.004, P(1780, 340)[1]), (FEED_X1, P(1555, 340)[1])], 0.004,
                           y=REC_HW + 0.001), M_STEEL, bevel=0.0008)
    for i, xp in enumerate((1600, 1700)):
        finish(hs.box(f"feed_pawl{i}", (0.006, 0.012, 0.007), (PX(xp), REC_HW - 0.007, TRAY_Z + 0.006)), M_DARK,
               bevel=0.0005)
    # The vertical bars at the front of the feed (photo 1505-1520 bright, 1537-1550 dark).
    finish(hs.box("feed_bar_front", (MM(15), 0.0016, MM(120)), (PX(1512), REC_HW + 0.0008, P(1512, 330)[1])),
           M_BRIGHT, bevel=0.0004)
    finish(hs.box("feed_bar_back", (MM(13), 0.0014, MM(140)), (PX(1543), REC_HW + 0.0007, P(1543, 320)[1])),
           M_DARK, bevel=0.0004)
    # Ejection port underneath, behind the feed, with its spring cover.
    finish(hs.box("eject_port", (0.07, 0.020, 0.0012), (0.070, 0, REC_BOT - 0.0012)), M_BORE, bevel=0)
    finish(hs.box("eject_cover", (0.074, 0.022, 0.0012), (0.070, 0, REC_BOT - 0.0024)), M_DARK, bevel=0.0004)
    # Rivets (photo 1885/2085/2285 and the small one at 1595).
    for xp, yp, r in ((1885, 347, 12), (2085, 348, 12), (2285, 350, 12), (1595, 383, 9)):
        for sy in (1, -1):
            rv = hs.cyl_y(f"rivet{xp}{sy}", MM(r), 0.0024, (PX(xp), sy * (REC_HW + 0.0004), P(xp, yp)[1]), verts=16)
            finish(rv, M_STEEL, bevel=0.0007, segments=2)
    # Cocking handle at the front of its slot (right side).
    finish(hs.box("cock_stem", (0.010, 0.014, 0.0045), (0.112, -REC_HW - 0.005, -0.010)), M_DARK, bevel=0.0006)
    knob = hs.cyl_y("cock_knob", 0.0068, 0.012, (0.112, -REC_HW - 0.015, -0.010), verts=24)
    finish(knob, M_DARK, bevel=0.0012, segments=3)
    # Rear end: the stock latch block and the dark buffer collar, the bright stock ring.
    finish(hs.section("buffer", [(-0.021, REC_BOT + 0.002), (0.021, REC_BOT + 0.002), (0.023, 0.0),
                                 (0.021, rear_top - 0.001), (-0.021, rear_top - 0.001), (-0.023, 0.0)],
                      PX(2520), REC_X0 + 0.001), M_DARK, bevel=0.0008)
    finish(hs.section("stock_ring", [(-0.0205, REC_BOT + 0.0035), (0.0205, REC_BOT + 0.0035), (0.0215, 0.0),
                                     (0.0205, rear_top - 0.0005), (-0.0205, rear_top - 0.0005), (-0.0215, 0.0)],
                      PX(2535), PX(2520)), M_BRIGHT, bevel=0.0004)
    # Rear sling swivel on top (photo 2318-2355): a D ring on a hinge block.
    finish(hs.box("swivel_block", (MM(30), 0.014, 0.004), (PX(2336), 0, rear_top + 0.0018)), M_DARK, bevel=0.0006)
    bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(24), minor_segments=8, major_radius=MM(17),
                                     minor_radius=0.0013, location=(PX(2336), 0, rear_top + 0.0115),
                                     rotation=(PI / 2, 0, 0))
    finish(bpy.context.active_object, M_STEEL, bevel=0, smooth=True)

    # Fire-Control Link readout (left rear, between the rivets) and the markings.
    fx = (PX(1885) + PX(2085)) / 2
    finish(hs.box("fcl_glass", (0.034, 0.0014, 0.011), (fx, REC_HW + 0.0005, -0.0135)), M_GLASS, bevel=0.0004)
    for i, w in enumerate((0.005, 0.008, 0.003, 0.006, 0.004)):
        finish(hs.box(f"fcl_seg{i}", (w, 0.0004, 0.0014), (fx - 0.014 + i * 0.0058 + w / 2, REC_HW + 0.0013, -0.0112)),
               M_AMBER, bevel=0)
    finish(hs.box("fcl_bar", (0.022, 0.0004, 0.0008), (fx - 0.003, REC_HW + 0.0013, -0.0158)), M_AMBER, bevel=0)
    # Left side reads front-to-back from the left (rotation flips the text to face +Y).
    text("mark_left", "MG 42/A", 0.0056, (PX(2340), REC_HW + 0.0001, -0.002), (PI / 2, 0, PI), M_MARK)
    text("mark_cal", "7,62x51", 0.0048, (PX(2340), REC_HW + 0.0001, -0.010), (PI / 2, 0, PI), M_MARK)
    text("mark_serial", "GRF 0417", 0.0042, (PX(2340), REC_HW + 0.0001, -0.0185), (PI / 2, 0, PI), M_MARK)
    text("mark_right", "D   E", 0.006, (PX(2300), -REC_HW - 0.0001, -0.019), (PI / 2, 0, 0), M_MARK)


def build_cover():
    part("cover")
    hw = REC_HW - 0.0008
    # Side outline traced: the front over the feed, the hump, the long slope back to the latch.
    pts = trace([(1553, 268), (1556, 246), (1566, 238), (1760, 237), (1800, 232), (1840, 228), (1895, 236),
                 (1905, 250), (2050, 266), (2200, 281), (2330, 276), (2338, 280)])
    pts += [(PX(2338), SEAM_Z), (FEED_X0 - 0.004, SEAM_Z), (FEED_X0 - 0.004, COVER_LOW_Z), (PX(1553), COVER_LOW_Z)]
    cover = hs.side_profile("cover", pts, 2 * hw)
    finish(cover, M_STEEL, bevel=0.0012, segments=3, angle=40)
    # The three domed heads over the feed (photo 1600 / 1660 / 1722), both sides.
    for xp in (1600, 1660, 1722):
        for sy in (1, -1):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=hs.nverts(20), ring_count=10, radius=MM(15),
                                                 location=(PX(xp), sy * (hw - 0.002), P(xp, 252)[1]))
            dome = bpy.context.active_object
            dome.scale = (1, 0.55, 1)
            bpy.ops.object.transform_apply(scale=True)
            finish(dome, M_STEEL, bevel=0, smooth=True)
    # Front hinge knuckles, the rear latch knob (photo 2200-2240) and the pressed side rib.
    for i, (y, w) in enumerate(((-0.017, 0.010), (0.0, 0.014), (0.017, 0.010))):
        finish(hs.cyl_y(f"cover_hinge{i}", 0.0042, w - 0.001, (PX(1560), y, COVER_LOW_Z + 0.004), verts=20),
               M_STEEL, bevel=0.0005, segments=2)
    finish(hs.box("cover_latch", (MM(42), 0.016, 0.006), (PX(2220), 0, P(2220, 272)[1])), M_DARK, bevel=0.0012)
    rib = hs.box("cover_rib", (PX(1905) - PX(2320), 0.0012, 0.0024), ((PX(1905) + PX(2320)) / 2, hw, SEAM_Z + 0.006))
    hs.mirror_y(rib)
    finish(rib, M_STEEL, bevel=0.0004)
    part("body")


# ---------------------------------------------------------------- grip, trigger, stock
def build_lower():
    # Trigger housing: a steel frame traced from the photo, with the big guard.
    frame = trace([(1822, 412), (2240, 412), (2240, 466), (2100, 468), (2085, 472), (2080, 500), (2085, 530),
                   (2100, 565), (2118, 605), (2131, 640), (2136, 665), (2132, 690), (2120, 707), (2040, 708),
                   (2032, 690), (2030, 665), (2022, 635), (2005, 605), (1985, 575), (1962, 548), (1945, 557),
                   (1920, 562), (1870, 561), (1845, 551), (1830, 535), (1823, 505), (1822, 470)])
    housing = hs.side_profile("trigger_housing", frame, 0.022)
    guard = trace([(1838, 500), (1845, 478), (1862, 463), (1885, 458), (1915, 462), (1940, 475), (1953, 495),
                   (1950, 520), (1935, 540), (1905, 548), (1870, 546), (1848, 532)])
    hs.cut(housing, hs.side_profile("guard_hole", guard, 0.05))
    finish(housing, M_STEEL, bevel=0.0009)
    # Bakelite grip panels, both sides, with the horizontal grooves.
    panel = trace([(1905, 423), (2067, 427), (2070, 487), (2083, 530), (2103, 580), (2123, 630), (2127, 657),
                   (2120, 690), (2083, 697), (2047, 697), (2035, 680), (2027, 647), (2013, 613), (1997, 580),
                   (1977, 547), (1963, 520), (1960, 480), (1947, 463), (1923, 450), (1907, 437)])
    for sy in (1, -1):
        p = hs.side_profile(f"grip_panel{sy}", panel, 0.0045, y=sy * 0.0128)
        for i in range(22 if is_high() else 0):
            py = 488 + i * 8.7
            g = hs.box(f"groove{sy}_{i}", (0.07, 0.0016, 0.0011), (PX(2060), sy * 0.0152, P(2060, py)[1]),
                       (0, 0, 0))
            g.rotation_euler = (0, 0, 0)
            hs.cut(p, g)
        finish(p, M_GRIP, bevel=0.0012, segments=3, angle=40)
        # Grip screw, lower screw, the oval medallion.
        finish(hs.cyl_y(f"grip_screw{sy}", MM(12), 0.003, (PX(2005), sy * 0.0152, P(2005, 505)[1]), verts=20),
               M_STEEL, bevel=0.0006)
        finish(hs.cyl_y(f"grip_screw2{sy}", MM(11), 0.003, (PX(2084), sy * 0.0152, P(2084, 645)[1]), verts=20),
               M_STEEL, bevel=0.0006)
        finish(hs.cyl_y(f"grip_medal{sy}", MM(15), 0.0026, (PX(2033), sy * 0.0151, P(2033, 452)[1]), verts=24),
               M_STEEL, bevel=0.0005)
    # Tang screw and pin behind the grip.
    finish(hs.cyl_y("tang_screw", MM(13), 0.0236, (PX(2120), 0, P(2120, 452)[1]), verts=20), M_STEEL, bevel=0.0006)
    finish(hs.cyl_y("tang_pin", MM(12), 0.0236, (PX(2210), 0, P(2210, 445)[1]), verts=20), M_STEEL, bevel=0.0006)
    finish(hs.box("tang_slot", (0.0008, 0.0238, MM(20)), (PX(2120), 0, P(2120, 452)[1])), M_BORE, bevel=0)
    # Trigger: the curved blade (photo).
    trig = trace([(1906, 458), (1918, 460), (1925, 472), (1922, 495), (1910, 518), (1893, 537), (1884, 535),
                  (1898, 517), (1909, 495), (1911, 474)])
    finish(hs.side_profile("trigger", trig, 0.0065), M_STEEL, bevel=0.0007)
    # Safety (push button through the housing).
    finish(hs.cyl_y("safety", MM(11), 0.030, (PX(1960), 0, P(1960, 430)[1]), verts=20), M_DARK, bevel=0.0006)

    # Stock: black bakelite, traced; the stock is its own part (the viewmodel hides it while aiming).
    part("stock")
    outline = trace([(2533, 288), (2600, 286), (2650, 282), (2700, 271), (2750, 256), (2790, 240), (2820, 228),
                     (2850, 220), (2880, 217), (2900, 222), (2910, 232), (2912, 248), (2900, 270), (2886, 300),
                     (2878, 340), (2876, 400), (2879, 460), (2884, 520), (2886, 545), (2875, 560), (2850, 567),
                     (2800, 556), (2750, 540), (2700, 522), (2672, 508), (2662, 480), (2656, 450), (2645, 436),
                     (2620, 431), (2580, 428), (2555, 418), (2533, 405)])
    stock = hs.side_profile("stock", outline, 0.040)
    finish(stock, M_STOCK, bevel=0.0075 if hs.D["seg"] > 1 else 0.006, segments=5, angle=50)
    # Butt plate (the steel cap on the rear face) and the stock's front socket.
    butt = trace([(2912, 248), (2900, 270), (2886, 300), (2878, 340), (2876, 400), (2879, 460), (2884, 520),
                  (2886, 545), (2892, 545), (2890, 520), (2885, 460), (2882, 400), (2884, 340), (2892, 300),
                  (2906, 270), (2917, 250)])
    finish(hs.side_profile("butt_plate", butt, 0.036), M_DARK, bevel=0.0012)
    finish(hs.cyl_y("stock_swivel", 0.0055, 0.006, (PX(2565), 0, P(2565, 434)[1]), verts=20), M_STEEL, bevel=0.0006)
    part("body")


# ---------------------------------------------------------------- ammo box and belt
BOX_X0, BOX_X1 = FEED_X0 - 0.006, FEED_X1 + 0.024
BOX_Y0, BOX_Y1 = 0.033, 0.083
BOX_Z0, BOX_Z1 = -0.122, -0.014


def build_box():
    part("magazine")
    bx = hs.box("ammo_box", (BOX_X1 - BOX_X0, BOX_Y1 - BOX_Y0, BOX_Z1 - BOX_Z0),
                ((BOX_X0 + BOX_X1) / 2, (BOX_Y0 + BOX_Y1) / 2, (BOX_Z0 + BOX_Z1) / 2))
    mx = (FEED_X0 + FEED_X1) / 2
    hs.cut(bx, hs.box("box_mouth", (0.080, 0.026, 0.02), (mx, 0.058, BOX_Z1)))
    finish(bx, M_BOX, bevel=0.0018)
    for i, z in enumerate((-0.048, -0.094)):
        finish(hs.box(f"box_rib{i}", (BOX_X1 - BOX_X0 - 0.014, 0.002, 0.006), ((BOX_X0 + BOX_X1) / 2, BOX_Y1 + 0.0006, z)),
               M_BOX, bevel=0.0008)
    finish(hs.box("box_lid", (BOX_X1 - BOX_X0 + 0.003, BOX_Y1 - BOX_Y0 + 0.003, 0.004),
                  ((BOX_X0 + BOX_X1) / 2, (BOX_Y0 + BOX_Y1) / 2, BOX_Z1 - 0.008)), M_BOX, bevel=0.0012)
    finish(hs.box("box_latch", (0.006, 0.010, 0.016), (BOX_X1 + 0.0025, 0.067, -0.028)), M_DARK, bevel=0.0008)
    finish(hs.cyl_between("box_handle", (BOX_X0 + 0.02, BOX_Y1 + 0.006, -0.120), (BOX_X1 - 0.02, BOX_Y1 + 0.006, -0.120),
                          0.0028, verts=12), M_DARK, bevel=0)
    # Mounting bracket into the receiver's left side, under the feed tray.
    finish(hs.box("box_rail", (0.07, BOX_Y0 - REC_HW + 0.001, 0.014), (mx, (BOX_Y0 + REC_HW) / 2, -0.021)),
           M_DARK, bevel=0.0008)
    text("box_stencil", "7.62 x 51   150", 0.0085, (BOX_X1 - 0.008, BOX_Y1 + 0.0001, -0.078), (PI / 2, 0, PI), M_PAINT)
    text("box_stencil2", "GURT  4:1  L", 0.0055, (BOX_X1 - 0.008, BOX_Y1 + 0.0001, -0.066), (PI / 2, 0, PI), M_PAINT)
    for i, y in enumerate((0.048, 0.062)):
        cartridge(f"box_round{i}", V((0.0, y, BOX_Z1 - 0.004)))
    part("body")


def cartridge(name, centre_yz, links=True):
    """A belted 7.62x51 round, axis along +X, at (y, z) of `centre_yz` (x ignored)."""
    y, z = centre_yz.y, centre_yz.z
    c0 = CART_X0
    case = hs.lathe_x(f"{name}_case", [(c0, 0.0050), (c0 + 0.0008, 0.0060), (c0 + 0.0016, 0.0060),
                                       (c0 + 0.0020, 0.0051), (c0 + 0.0030, 0.0051), (c0 + 0.0036, 0.0059),
                                       (c0 + 0.0390, 0.0057), (c0 + 0.0430, 0.0044), (c0 + 0.0505, 0.0044)], verts=20)
    case.location = (0, y, z)
    finish(case, M_BRASS, bevel=0, smooth=True)
    bullet = hs.lathe_x(f"{name}_bullet", [(c0 + 0.0500, 0.0039), (c0 + 0.0560, 0.0039), (c0 + 0.0640, 0.0030),
                                           (c0 + 0.0690, 0.0015), (c0 + 0.0712, 0.0005)], verts=16)
    bullet.location = (0, y, z)
    finish(bullet, M_COPPER, bevel=0, smooth=True)
    if links:
        for k, (a, b, r) in enumerate(((0.010, 0.018, 0.0063), (0.031, 0.037, 0.0062))):
            link = hs.lathe_x(f"{name}_link{k}", [(c0 + a, r), (c0 + b, r)], verts=16)
            link.location = (0, y, z)
            finish(link, M_DARK, bevel=0)


def bezier(p0, p1, p2, t):
    return p0 * (1 - t) ** 2 + p1 * 2 * (1 - t) * t + p2 * t * t


def build_belt():
    """Short belt from the box mouth up into the feed opening, rounds 12.6 mm apart."""
    part("belt")
    zf = (TRAY_Z + COVER_LOW_Z) / 2
    p0, p1, p2 = V((0, 0.012, zf)), V((0, 0.088, zf + 0.006)), V((0, 0.060, BOX_Z1 - 0.003))
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
            finish(hs.cyl_between(f"belt_strap{i}", (CART_X0 + 0.014, c.y, c.z), (CART_X0 + 0.014, n.y, n.z), 0.0016,
                                  verts=8), M_DARK, bevel=0)
    part("body")
    return len(centres)


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_jacket()
    build_receiver()
    build_cover()
    build_lower()
    build_box()
    rounds = build_belt()
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

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.15, 0, -0.03), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.3, -1.2, 1.1), 55, 1.8, sy=0.6)
    area("strip_top", (0.15, 0.0, 1.1), 35, 2.4, sy=0.2)
    area("fill", (0.5, 1.3, 0.3), 40, 1.6, (0.75, 0.85, 1.0))
    area("rim", (1.6, -0.4, 0.5), 45, 0.8, (1.0, 0.82, 0.62))
    area("kick", (-1.4, 0.3, 0.2), 25, 1.0, (0.9, 0.95, 1.0))
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
    print(f"mg42: rendered {path}")


SHOTS = {
    "left": ((0.16, 2.6, -0.02), (0.16, 0, -0.02), 55, None, 0.0),
    "side": ((0.16, -2.6, -0.02), (0.16, 0, -0.02), 55, None, 0.0),
    "beauty": ((0.85, -1.05, 0.45), (0.12, 0, -0.03), 50, None, 8.0),
    "beauty_left": ((-0.2, 1.15, 0.40), (0.16, 0, -0.04), 45, None, 8.0),
    "receiver": ((-0.20, 0.36, 0.20), (0.07, 0.02, -0.01), 50, None, 4.0),
    "muzzle": ((0.95, 0.30, 0.16), (0.55, 0, 0.0), 50, None, 4.0),
    # What the player sees at the hip: data/player/viewmodel_mg42.tres (eye (-0.56, 0.15, -0.15) in
    # glTF axes = Blender (-0.56, 0.15, 0.15)).
    "fp": ((-0.56, 0.15, 0.15), (0.8, 0.05, 0.05), None, 60, 0.0),
    # Aimed: the sight line.
    "ads": ((-0.45, 0.0, SIGHT_Z), (1.0, 0.0, SIGHT_Z), None, 30, 0.0),
}


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    only = [s for s in args.only.split(",") if s]
    for name, (loc, target, lens, fov, fstop) in SHOTS.items():
        if only and name not in only:
            continue
        shoot(cam, f"{stem}_{name}.png", loc, target, lens=lens or 50, fov_deg=fov, fstop=fstop)


def render_overlay(path):
    """Orthographic left view at the photo's scale (levelled); with --photo, its outline drawn over the photo."""
    scene.render.engine = "CYCLES"  # (Workbench/EEVEE need a GPU context)
    scene.cycles.device = "CPU"
    scene.cycles.samples = 2
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    W, H = 3008, 1332
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.view_settings.view_transform = "Standard"
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = W / PX_MM / 1000.0
    cx, cz = PX(W / 2), (BORE_PY - H / 2) / PX_MM / 1000.0
    cam.location = (cx, 1.0, cz)
    cam.rotation_euler = (V((cx, 0, cz)) - V((cx, 1.0, cz))).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"mg42: overlay render {path}")
    if not args.photo:
        return
    import numpy as np
    img = bpy.data.images.load(path)
    a = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1, :, 3]
    photo = bpy.data.images.load(os.path.abspath(args.photo))
    pw, ph = photo.size
    pp = np.array(photo.pixels[:], dtype=np.float32).reshape(ph, pw, photo.channels)[::-1, :, :3]
    # The render is levelled: column px of the photo sits TILT * (px - 55) rows higher.
    m = a > 0.5
    shifted = np.zeros_like(m)
    for px in range(W):
        s = int(round((px - 55) * TILT))
        if s > 0:
            shifted[:-s, px] = m[s:, px]
        else:
            shifted[:, px] = m[:, px]
    edge = shifted & ~(np.roll(shifted, 1, 0) & np.roll(shifted, -1, 0) & np.roll(shifted, 1, 1) &
                       np.roll(shifted, -1, 1))
    edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 1, 1)
    out = pp.copy()
    out[shifted] = out[shifted] * 0.75 + np.array([0.0, 0.25, 0.35]) * 0.25
    out[edge] = (1.0, 0.0, 0.0)
    res = bpy.data.images.new("overlay", W, H, alpha=True)
    rgba = np.concatenate([out, np.ones((H, W, 1), np.float32)], axis=2)[::-1]
    res.pixels = rgba.ravel().tolist()
    res.filepath_raw = path
    res.file_format = "PNG"
    res.save()
    print(f"mg42: overlay over the photo {path}")


# ---------------------------------------------------------------- run
if args.count:
    build(hs.LOW, "mg42_low")
elif args.out:
    high = build(hs.HIGH, "mg42_high")
    low = build(hs.LOW, "mg42_low")
    # Texel density: the receiver/cover/sights get the most (always on screen), the stock the least.
    bakeutil.unwrap(low, boost={M_STOCK.name: 0.8, M_BRASS.name: 1.4, M_COPPER.name: 1.4, M_STEEL.name: 1.1,
                                M_PAINT.name: 1.5, M_MARK.name: 1.5, M_GRIP.name: 1.2, M_BORE.name: 0.4,
                                M_BOX.name: 0.8})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "mg42", cage=0.0012, ray=0.004,
                                 ao_distance=0.03, grime=0.35, log=print)
    bpy.data.objects.remove(high)
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
elif args.preview or args.overlay:
    build(hs.HIGH, "mg42_high")
    if args.overlay:
        render_overlay(args.overlay)
    if args.preview:
        render_previews(args.preview.rsplit(".", 1)[0])
