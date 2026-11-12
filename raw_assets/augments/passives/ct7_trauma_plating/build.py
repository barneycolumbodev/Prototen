"""CT-7 Ceramic Trauma Plating (docs/design.md §3.6): boron-carbide plates bolted over the GS-2 graft suit.

Design: heavier armour that goes on top of the suit, in the same language (flat facets, satin black, angular
outlines, thin seaglass light) but thicker (14 mm) and standing 12 mm off the suit plates, so it reads as a
separate layer: a breastplate split down the sternum with a chevron lower edge, two abdominal lames, a back
plate with a spine channel, shoulder pauldrons with a lower lame each, and collar guards over the traps. Hex
bolts at the corners, stencilled markings (CT-7, B4C CLASS IV, a serial), a short status light under the collar.
Cast ceramic: near-black with a faint mottle, pale chips where the edges have taken hits.

Pieces ride on chest (breastplate, back, collar), spine (lames) and upper_arm.L/R (pauldrons).

Run:
  tools/blender.sh raw_assets/augments/passives/ct7_trauma_plating/build.py \\
      --out assets/augments/passives/ct7_trauma_plating/ct7_trauma_plating.gltf --preview docs/previews/ct7_trauma_plating
  Design check without the bake: --quick --preview /tmp/ct7
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--quick", action="store_true")
ap.add_argument("--tex", type=int, default=1024)
ap.add_argument("--samples", type=int, default=40)
args = ap.parse_args(argv)
C.TAG = "ct7"

body = C.Body()
CER = C.mat_ceramic("ct7_ceramic")
MET = C.mat_metal("ct7_bolt", base=(0.16, 0.165, 0.17), rough=0.3)
PAINT = C.mat_paint("ct7_stencil", (0.58, 0.56, 0.5))
GLOW = C.mat_glow("ct7_glow")
MATS = [CER, MET, PAINT, GLOW]

GAP, THICK = 0.012, 0.014
FRONT = (V((0, -0.4, 0)), V((1, 0, 0)), V((0, 0, 1)))   # (x, z) seen from the front, rays +Y
BACK = (V((0, 0.4, 0)), V((1, 0, 0)), V((0, 0, 1)))     # (x, z) seen from behind, rays -Y
TOP = (V((0, 0, 1.9)), V((1, 0, 0)), V((0, 1, 0)))      # (x, y) seen from above, rays -Z


def mat_all(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


def mx(poly):
    return [(-u, v) for u, v in reversed(poly)]


def plate(name, bone, poly, frame, d, gap=GAP, thick=THICK, facet=7.0, smooth=0.03, bolts=(), which=("suit",)):
    hi, lo = C.plate(name, body, poly, frame, d, gap, thick, which, facet_deg=facet, smooth_r=smooth, bevel=0.0022)
    mat_all(hi, CER)
    mat_all(lo, CER)
    extra = []
    for (u, v) in bolts:
        for at, n in C.surface_points(hi, d, [(u, v)], frame):
            b = C.bolt(name + "_bolt", at, n)
            b.data.materials.append(MET)
            extra.append(C.apply_all(b))
    if extra:
        hi = C.join([hi] + extra, name + "_high")
    C.add_piece(name, bone, hi, lo)
    return hi, lo


# ---------------------------------------------------------------- breastplate (two halves, chevron bottom)
BREAST_L = [(0.008, 1.468), (0.062, 1.492), (0.142, 1.478), (0.176, 1.432), (0.178, 1.352), (0.158, 1.29),
            (0.118, 1.245), (0.056, 1.226), (0.008, 1.196)]
d_front = V((0, 1, 0))
for side, poly in (("L", BREAST_L), ("R", mx(BREAST_L))):
    s = 1 if side == "L" else -1
    hi, lo = plate("breast_" + side, "chest", poly, FRONT, d_front, facet=8.0, smooth=0.035,
                   bolts=[(0.135 * s, 1.462), (0.162 * s, 1.31), (0.05 * s, 1.235)])
    # A panel line across the upper chest.
    pts = [p for p, _n in C.surface_points(hi, d_front, [(0.03 * s, 1.43), (0.09 * s, 1.445), (0.155 * s, 1.425)], FRONT)]
    if len(pts) == 3:
        hi = C.groove(hi, d_front, pts, width=0.0018, depth=0.0014)
        C.PIECES[-1].high = hi

# Stencils and the status light on the breastplate (HIGH; through the bake).
for text, (u, v), size in (("CT-7", (0.1, 1.385), 0.022), ("B4C  CLASS IV", (0.1, 1.36), 0.0085),
                           ("CT7-0419", (-0.105, 1.39), 0.009), ("▲ MAX 14.5 kJ", (-0.105, 1.372), 0.0075)):
    tgt = C.PIECES[0].high if u > 0 else C.PIECES[1].high
    for at, n in C.surface_points(tgt, d_front, [(u, v)], FRONT):
        st = C.stencil("st_" + text[:4], text, at, n, (0, 0, 1), size, PAINT, target=tgt)
        C.PIECES[0 if u > 0 else 1].high = C.join([C.PIECES[0 if u > 0 else 1].high, C.apply_all(st)], "breast_high")
for side in ("L", "R"):
    s = 1 if side == "L" else -1
    i = 0 if side == "L" else 1
    for at, n in C.surface_points(C.PIECES[i].high, d_front, [(0.045 * s, 1.462)], FRONT):
        import bmesh
        from mathutils import Matrix
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        up = V((0, 0, 1))
        right = up.cross(n).normalized()
        m = C.basis4(right, up, n, at + n * 0.0006) @ Matrix.Diagonal((0.034, 0.0032, 0.0016, 1))
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
        import bpy
        me = bpy.data.meshes.new("light")
        bm.to_mesh(me)
        bm.free()
        lo_light = bpy.data.objects.new("light_" + side, me)
        bpy.context.scene.collection.objects.link(lo_light)
        lo_light.data.materials.append(GLOW)
        hi_light = lo_light.copy()
        hi_light.data = lo_light.data.copy()
        bpy.context.scene.collection.objects.link(hi_light)
        C.PIECES[i].high = C.join([C.PIECES[i].high, hi_light], "breast_high")
        C.PIECES[i].low = C.join([C.PIECES[i].low, lo_light], "breast_low")

# ---------------------------------------------------------------- abdominal lames
for k, (z0, z1, w0, w1) in enumerate(((1.128, 1.188, 0.118, 0.104), (1.064, 1.12, 0.104, 0.09))):
    poly = [(-w1, z0), (w1, z0), (w0, z1 - 0.012), (w0 - 0.016, z1), (-(w0 - 0.016), z1), (-w0, z1 - 0.012)]
    plate("lame_%d" % k, "spine", poly, FRONT, d_front, gap=0.006 + 0.002 * (1 - k), thick=0.01, facet=9.0, smooth=0.03,
          bolts=[(w1 - 0.014, z0 + 0.012), (-(w1 - 0.014), z0 + 0.012)])

# ---------------------------------------------------------------- back plate (spine channel down the middle)
BACK_L = [(0.012, 1.478), (0.07, 1.494), (0.148, 1.47), (0.168, 1.4), (0.16, 1.3), (0.122, 1.232), (0.012, 1.214)]
d_back = V((0, -1, 0))
for side, poly in (("L", BACK_L), ("R", mx(BACK_L))):
    s = 1 if side == "L" else -1
    hi, lo = plate("back_" + side, "chest", poly, BACK, d_back, facet=8.0, smooth=0.04,
                   bolts=[(0.14 * s, 1.455), (0.15 * s, 1.31), (0.03 * s, 1.235)])
for at, n in C.surface_points(C.PIECES[-2].high, d_back, [(0.085, 1.33)], BACK):
    st = C.stencil("st_back", "CT-7  •  DO NOT STAND BEHIND", at, n, (0, 0, 1), 0.0075, PAINT)
    C.PIECES[-2].high = C.join([C.PIECES[-2].high, C.apply_all(st)], "back_high")

# ---------------------------------------------------------------- pauldrons (on the upper arms) and collar guards
for side in ("L", "R"):
    s = 1 if side == "L" else -1
    sh = body.joint("upper_arm." + side)
    el = body.joint("forearm." + side)
    a = (el - sh).normalized()
    out = V((0.8 * s, 0, 0.6))
    out = (out - a * out.dot(a)).normalized()
    fwd = a.cross(out).normalized() * s
    for k, (u0, u1, half, gap) in enumerate(((-0.05, 0.085, 0.078, 0.016), (0.07, 0.13, 0.064, 0.024))):
        frame = (sh + a * 0.0 + out * 0.4, a, fwd)
        poly = [(u0 + 0.01, -half * 0.8), (u0, 0.0), (u0 + 0.01, half * 0.8), (u1 - 0.02, half), (u1, half * 0.45),
                (u1, -half * 0.45), (u1 - 0.02, -half)]
        if s < 0:
            poly = [(u, -v) for u, v in poly]
        plate("pauldron_%s%d" % (side, k), "upper_arm." + side, poly, frame, -out, gap=gap, thick=0.012 - 0.002 * k,
              facet=8.0, smooth=0.03, bolts=[(u1 - 0.022, 0.0)] if k == 0 else [])
    poly = [(0.058 * s, -0.045), (0.15 * s, -0.035), (0.165 * s, 0.03), (0.07 * s, 0.05)]
    plate("collar_" + side, "chest", poly, TOP, V((0, 0, -1)), gap=0.01, thick=0.01, facet=10.0, smooth=0.025)

C.log("pieces:", len(C.PIECES))

# ---------------------------------------------------------------- bake, export, previews
if not args.quick and args.out:
    out, high = C.bake_and_export("ct7_trauma_plating", os.path.join(C.ROOT, args.out), MATS, tex=args.tex)
else:
    for p in C.PIECES:
        p.low.hide_render = True
if args.preview:
    C.stage(body)
    views = (("front", (0.9, -4.6, 1.45), (0, 0, 1.25)), ("back", (-1.2, 4.4, 1.5), (0, 0, 1.28)),
             ("close", (0.55, -1.25, 1.52), (0.03, 0, 1.36)))
    paths = []
    for name, cam, tgt in views:
        pth = f"{os.path.join(C.ROOT, args.preview) if not args.preview.startswith('/') else args.preview}_{name}.png"
        os.makedirs(os.path.dirname(pth), exist_ok=True)
        C.render(pth, cam, tgt, lens=85 if name != "close" else 70, res=(720, 960), samples=args.samples)
        paths.append(pth)
    base = os.path.join(C.ROOT, args.preview) if not args.preview.startswith("/") else args.preview
    C.sheet(paths, base + ".png")
