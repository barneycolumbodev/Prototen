"""HS-5 Subdermal Heat Sinks (docs/design.md §3.6): copper-graphene spreaders venting through fins on the forearms.

Design: on the outer side of each forearm, a black anodised spreader plate conformal to the suit, carrying a
stack of thin fins that follow the arm's curve (taller in the middle of the arc, a rounded fin outline).
The fins are copper at the root, tempered through straw and violet to blue at the tips: they read as
hardware that gets hot. A narrow amber slot glows along the plate under the fins (the hot core), and two
gunmetal end blocks clamp the stack with hex bolts; the front block is stencilled HS-5.

Pieces ride on forearm.L / forearm.R. The fins are modelled at full size (they're the part's silhouette).

Run:
  tools/blender.sh raw_assets/augments/passives/hs5_heat_sinks/build.py \\
      --out assets/augments/passives/hs5_heat_sinks/hs5_heat_sinks.gltf --preview docs/previews/hs5_heat_sinks
  Design check without the bake: --quick --preview /tmp/hs5
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Quaternion

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
C.TAG = "hs5"

body = C.Body()
BASE = C.mat_metal("hs5_anodised", base=(0.03, 0.031, 0.034), rough=0.38, wear=(0.42, 0.43, 0.45), brushed=0.04)
BLOCK = C.mat_metal("hs5_block", base=(0.12, 0.125, 0.13), rough=0.3)
PAINT = C.mat_paint("hs5_stencil", (0.62, 0.6, 0.55))
HOT = C.mat_glow("hs5_hot", color=(1.0, 0.42, 0.12), strength=5.0)
FIN_MATS = []

N_FINS = 13
SPAN = (0.24, 0.8)        # along the forearm (fraction of elbow -> wrist)
ARC = 52.0                # half-angle of the fin arc around the arm (degrees)
FIN_T = 0.0016
PLATE_GAP, PLATE_T = 0.004, 0.0035


def poly_solid(name, pts, axis, thick, mat):
    """Closed fin: planar polygon `pts` extruded by `thick` along `axis` (centred)."""
    bm = bmesh.new()
    vs = [bm.verts.new(p - axis * thick * 0.5) for p in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=axis * thick)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def box(name, center, axes, size, mat, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    x, y, z = axes
    bmesh.ops.transform(bm, matrix=C.basis4(x, y, z, center) @ Matrix.Diagonal((*size, 1)), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if bevel:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = 2
        ob = C.apply_all(ob)
    return ob


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    el, wr = body.joint("forearm." + side), body.joint("hand." + side)
    a = (wr - el).normalized()
    length = (wr - el).length
    out = V((0.85 * s, 0.1, 0.5))
    out = (out - a * out.dot(a)).normalized()
    side_ax = a.cross(out).normalized()
    mid = el + a * length * (SPAN[0] + SPAN[1]) * 0.5
    fin_mat = C.mat_heat_tint("hs5_fins_" + side, mid + out * 0.044, out, 0.024)
    FIN_MATS.append(fin_mat)
    # The spreader plate: conformal to the forearm's outer side.
    half_u = length * (SPAN[1] - SPAN[0]) * 0.5 + 0.012
    poly = [(-half_u, -0.022), (-half_u + 0.01, -0.03), (half_u - 0.012, -0.03), (half_u, -0.02), (half_u, 0.02),
            (half_u - 0.012, 0.03), (-half_u + 0.01, 0.03), (-half_u, 0.022)]
    frame = (mid + out * 0.3, a, side_ax)
    hi_p, lo_p = C.plate("plate_" + side, body, poly, frame, -out, PLATE_GAP, PLATE_T, facet_deg=4.0, smooth_r=0.012,
                         bevel=0.001)
    for o in (hi_p, lo_p):
        o.data.materials.clear()
        o.data.materials.append(BASE)
    bvh_plate = C.Body._bvh(hi_p)
    highs, lows = [hi_p], [lo_p]
    # Fins: a ring cast around the arm at each station.
    for k in range(N_FINS):
        f = SPAN[0] + (SPAN[1] - SPAN[0]) * k / (N_FINS - 1)
        c = el + a * length * f
        swell = math.sin(math.pi * (0.15 + 0.7 * k / (N_FINS - 1)))
        for detail, n_arc, objs in (("hi", 11, highs), ("lo", 5, lows)):
            inner, outer = [], []
            for j in range(n_arc):
                th = math.radians(-ARC + 2 * ARC * j / (n_arc - 1))
                d = Quaternion(a, th) @ out
                hit, _n = (None, None)
                loc, _nn, _i, _t = bvh_plate.ray_cast(c + d * 0.25, -d, 0.5)
                if loc is None:
                    hit, _n = body.cast(c + d * 0.25, -d, ("suit",), 0.5)
                    loc = hit + d * (PLATE_GAP + PLATE_T) if hit is not None else c + d * 0.05
                prof = math.cos(th / math.radians(ARC) * math.pi * 0.5) ** 0.6
                h = (0.006 + 0.012 * prof) * (0.75 + 0.25 * swell)
                inner.append(loc - d * 0.0008)
                outer.append(loc + d * h)
            pts = inner + list(reversed(outer))
            fin = poly_solid("fin_%s%d_%s" % (side, k, detail), pts, a, FIN_T, fin_mat)
            if detail == "hi":
                b = fin.modifiers.new("bevel", "BEVEL")
                b.width = 0.0004
                b.segments = 2
                fin = C.apply_all(fin)
            objs.append(fin)
    # The hot slot under the fins, and the end blocks with bolts.
    for detail, objs in (("hi", highs), ("lo", lows)):
        loc, _n, _i, _t = bvh_plate.ray_cast(mid + out * 0.25, -out, 0.5)
        if loc is not None:
            objs.append(box("hot_%s_%s" % (side, detail), loc + out * 0.0004, (a, side_ax, out),
                            (length * (SPAN[1] - SPAN[0]) + 0.006, 0.0035, 0.0012), HOT))
        for e, f in ((0, SPAN[0] - 0.045), (1, SPAN[1] + 0.045)):
            c = el + a * length * f
            loc, _n, _i, _t = bvh_plate.ray_cast(c + out * 0.25, -out, 0.5)
            if loc is None:
                continue
            blk = box("end_%s%d_%s" % (side, e, detail), loc + out * 0.004, (a, side_ax, out), (0.012, 0.05, 0.008), BLOCK,
                      bevel=0.0012 if detail == "hi" else 0.0)
            objs.append(blk)
            if detail == "hi":
                for v in (-0.016, 0.016):
                    bo = C.bolt("bolt", loc + out * 0.008 + side_ax * v, out, r=0.0028, h=0.0018)
                    bo.data.materials.append(BLOCK)
                    objs.append(C.apply_all(bo))
                if e == 0:
                    st = C.stencil("st_hs5", "HS-5", loc + out * 0.0081, out, a * s, 0.0065, PAINT, target=blk)
                    objs.append(C.apply_all(st))
    hi = C.join(highs, "hs5_%s_high" % side)
    lo = C.join(lows, "hs5_%s_low" % side)
    C.add_piece("hs5_" + side, "forearm." + side, hi, lo)

MATS = [BASE, BLOCK, PAINT, HOT] + FIN_MATS
C.log("pieces:", len(C.PIECES), "low tris", sum(C.tris(p.low) for p in C.PIECES))

if not args.quick and args.out:
    C.bake_and_export("hs5_heat_sinks", os.path.join(C.ROOT, args.out), MATS, tex=args.tex, cage=0.001, ray=0.004,
                      ao=0.012, emission_strength=3.0)
else:
    for p in C.PIECES:
        p.low.hide_render = True
if args.preview:
    C.stage(body)
    base = os.path.join(C.ROOT, args.preview) if not args.preview.startswith("/") else args.preview
    os.makedirs(os.path.dirname(base), exist_ok=True)
    fl = body.joint("forearm.L") * 0.5 + body.joint("hand.L") * 0.5
    views = (("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85), ("arm", fl + V((0.42, -0.28, 0.16)), fl, 60),
             ("arm_top", fl + V((0.2, 0.15, 0.45)), fl, 60))
    paths = []
    for name, cam, tgt, lens in views:
        pth = f"{base}_{name}.png"
        C.render(pth, cam, tgt, lens=lens, res=(720, 960), samples=args.samples)
        paths.append(pth)
    C.sheet(paths, base + ".png")
