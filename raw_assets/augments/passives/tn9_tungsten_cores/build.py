"""TN-9 Tungsten Long-Bone Cores (docs/design.md §3.6): the cores show where the bones meet the world.

Design: tungsten is dense, dull and dark. Along the ulna edge of each forearm (the edge you block and strike
with) and down the front of each shin runs a faceted tungsten strike bar, flush-mounted on the bone. Each bar
is split in three, and the core shows in the two gaps: a dark rod with machined rings and steel collars. Just below each knee a
thick core cap closes the tibia's bore: a heavy disc with a hex drive, the element symbol and the alloy grade.
The finish is a heavy-metal grey with a bluish cast, satin, a little worn on the striking edges.

Pieces ride on forearm.L/R and shin.L/R. Elbows and knees stay clear of the HM-5 rams and anchors.

Run:
  tools/blender.sh raw_assets/augments/passives/tn9_tungsten_cores/build.py \\
      --out assets/augments/passives/tn9_tungsten_cores/tn9_tungsten_cores.gltf --preview docs/previews/tn9_tungsten_cores
"""
import os
import sys

import bpy
import bmesh

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "tn9"
body = C.body_once()

TUNG = C.mat_metal("tn9_tungsten", base=(0.2, 0.205, 0.22), rough=0.42, wear=(0.46, 0.47, 0.5), brushed=0.05)
CORE = C.mat_metal("tn9_core", base=(0.09, 0.09, 0.1), rough=0.3, wear=(0.36, 0.36, 0.38), brushed=0.12)
STEEL = C.mat_metal("tn9_steel", base=(0.62, 0.62, 0.64), rough=0.18)
PAINT = C.mat_paint("tn9_stencil", (0.7, 0.68, 0.6))
MATS = [TUNG, CORE, STEEL, PAINT]
parts = {}


def put(bone, det, ob):
    hi, lo = parts.setdefault(bone, ([], []))
    (hi if det else lo).extend(ob if isinstance(ob, list) else [ob])


def surf(p, d):
    hit, _n = body.cast(p + d * 0.4, -d, ("suit",), 0.8)
    return hit if hit is not None else p + d * 0.05


def slot_cut(target, centers, ax, nrm, size):
    """Pockets rectangular slots into `target` (HIGH)."""
    cut = []
    for c in centers:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        side = ax.cross(nrm).normalized()
        from mathutils import Matrix
        bmesh.ops.transform(bm, matrix=C.basis4(ax, side, nrm, c) @ Matrix.Diagonal((*size, 1)), verts=bm.verts)
        me = bpy.data.meshes.new("slot")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new("slot", me)
        bpy.context.scene.collection.objects.link(o)
        cut.append(o)
    tool = C.join(cut, "slot_tool")
    m = target.modifiers.new("slots", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = tool
    target = C.apply_all(target)
    bpy.data.objects.remove(tool)
    return target


def strike_bar(tag, bone, p0, p1, d, span, half_w, thick, det, stencil_up):
    ax = (p1 - p0).normalized()
    L = (p1 - p0).length
    d = (V(d) - ax * V(d).dot(ax)).normalized()
    t0, t1 = span
    n = 9
    pts, nrm = [], []
    for k in range(n):
        t = t0 + (t1 - t0) * k / (n - 1)
        pts.append(surf(p0 + ax * L * t, d) + d * (thick * 0.5 + 0.0025))
        nrm.append(d)
    # Smooth the surface wobble: a bar is rigid.
    sm = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, n - 1)] + [pts[-1]]
    sm = [p + d * max(0.0, (pts[i] - p).dot(d)) for i, p in enumerate(sm)]
    wfun = (lambda t: half_w * (0.72 + 0.28 * min(1.0, 4 * t, 4 * (1 - t))))
    dense = C.spline(sm, 16)
    nd = len(dense) - 1
    # Three segments with the core exposed in the two gaps between them.
    segs = ((0.0, 0.31), (0.39, 0.61), (0.69, 1.0))
    out = []
    for si, (f0, f1) in enumerate(segs):
        i0, i1 = int(round(f0 * nd)), int(round(f1 * nd))
        idx = [round(i0 + (i1 - i0) * k / 5) for k in range(6)]
        seg = C.sweep(tag + "_seg", [dense[i] for i in idx], [d] * 6, thick * 0.5,
                      (lambda f0=f0, f1=f1: (lambda tt: wfun(f0 + (f1 - f0) * tt)))(), TUNG, det, power=5.0)
        if det:
            seg = C.bev(seg, 0.0009, angle=40)
        out.append(seg)
    bar = out[0]
    for g0, g1 in ((0.31, 0.39), (0.61, 0.69)):
        pa, pb = dense[int(round(g0 * nd))], dense[int(round(g1 * nd))]
        rc_ = half_w * 0.36
        out.append(C.cyl(tag + "_core", pa - ax * 0.004, pb + ax * 0.004, rc_, CORE, det, 16, 0.0))
        if det:
            for k in range(5):
                q = pa.lerp(pb, (k + 1) / 6)
                out.append(C.cyl(tag + "_ring", q - ax * 0.0011, q + ax * 0.0011, rc_ * 1.18, STEEL, True, 16, 0.0002))
            for q in (pa, pb):
                out.append(C.cyl(tag + "_collar", q - ax * 0.0025, q + ax * 0.0025, rc_ * 1.45, STEEL, True, 20, 0.0004))
        else:
            for q in (pa, pb):
                out.append(C.cyl(tag + "_collar", q - ax * 0.0025, q + ax * 0.0025, rc_ * 1.45, STEEL, False, 20, 0.0))
    if det:
        side = ax.cross(d).normalized()
        for e in (sm[0].lerp(sm[1], 0.45), sm[-1].lerp(sm[-2], 0.45)):
            bo = C.bolt("bb", e + d * thick * 0.5, d, r=0.0026, h=0.0016)
            out.append(C.setmat(C.apply_all(bo), STEEL))
        st = C.stencil("st", "TN-9", dense[int(nd * 0.15)] + d * (thick * 0.5 + 0.0002), d, stencil_up, 0.0048, PAINT, target=bar)
        out.append(C.apply_all(st))
    return out


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    el, wr = body.joint("forearm." + side), body.joint("hand." + side)
    kn, an = body.joint("shin." + side), body.joint("foot." + side)
    for det in (True, False):
        fa_ax = (wr - el).normalized()
        put("forearm." + side, det, strike_bar("ulna", "forearm." + side, el, wr, (0.15 * s, 1.0, -0.35), (0.16, 0.84), 0.013, 0.009,
                                               det, -fa_ax))
        sh_ax = (an - kn).normalized()
        put("shin." + side, det, strike_bar("tibia", "shin." + side, kn, an, (0.05 * s, -1.0, 0.0), (0.16, 0.8), 0.016, 0.01,
                                            det, -sh_ax))
        # Core cap below the knee.
        d = V((0.05 * s, -1.0, 0.0))
        d = (d - sh_ax * d.dot(sh_ax)).normalized()
        c = surf(kn + sh_ax * 0.06, d)
        put("shin." + side, det, C.cyl("cap", c - d * 0.004, c + d * 0.013, 0.021, TUNG, det, 32, 0.0018))
        put("shin." + side, det, C.cyl("cap_ring", c + d * 0.011, c + d * 0.0145, 0.016, STEEL, det, 32, 0.0006))
        put("shin." + side, det, C.cyl("cap_hex", c + d * 0.0125, c + d * 0.0165, 0.0075, CORE, det, 6, 0.0004))
        if det:
            up = -sh_ax
            st = C.stencil("st_w", "W", c + d * 0.0131 + up * 0.0, d, up, 0.0, PAINT)
            bpy.data.objects.remove(st)
            for txt, off in (("74", 0.0118), ("W-Ni-Fe", -0.0118)):
                st = C.stencil("st_cap", txt, c + d * 0.0132 + up * off, d, up, 0.0036, PAINT)
                put("shin." + side, det, C.apply_all(st))

for bone, (hi, lo) in parts.items():
    C.add_piece("tn9_" + bone, bone, C.join(hi, "tn9_%s_high" % bone), C.join(lo, "tn9_%s_low" % bone))

kn = body.joint("shin.L")
fl = body.joint("forearm.R") * 0.5 + body.joint("hand.R") * 0.5
C.run("tn9_tungsten_cores", args, MATS, (
    ("front", (0.9, -4.6, 1.0), (0, 0, 0.9), 85),
    ("shin", kn + V((0.32, -0.55, -0.02)), kn + V((0.0, -0.04, -0.16)), 55),
    ("forearm", fl + V((-0.25, 0.5, -0.05)), fl + V((0, 0.02, 0)), 55),
    ("slot", kn + V((0.08, -0.22, -0.1)), kn + V((0.0, -0.05, -0.17)), 60)))
