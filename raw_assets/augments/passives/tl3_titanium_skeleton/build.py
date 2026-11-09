"""TL-3 Titanium-Lattice Skeleton (docs/design.md §3.6): where the lattice anchors through the suit.

Design: the bones are inside, so what shows is where the lattice is anchored: at each wrist, a brushed titanium
anchor saddle on the back of the wrist with a printed hex lattice pocketed into it (the same lattice that laces
the bones) and three gold-anodised anchor bolts through it; across the knuckles, a titanium bar with four
anchor bolts, one per metacarpal, and a ridge that takes the impact of a punch. Lettering on the saddle: TL-3 and the lattice code.

Pieces ride on forearm.L/R (saddles) and hand.L/R (knuckle bar).

Run:
  tools/blender.sh raw_assets/augments/passives/tl3_titanium_skeleton/build.py \\
      --out assets/augments/passives/tl3_titanium_skeleton/tl3_titanium_skeleton.gltf --preview docs/previews/tl3_titanium_skeleton
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "tl3"
body = C.body_once()

TI = C.mat_metal("tl3_titanium", base=(0.36, 0.36, 0.37), rough=0.3, wear=(0.5, 0.5, 0.51), brushed=0.08)
TI_DARK = C.mat_metal("tl3_ti_dark", base=(0.07, 0.072, 0.078), rough=0.36, wear=(0.42, 0.43, 0.45), brushed=0.05)
GOLD = hs.material("tl3_gold", (0.66, 0.48, 0.22), 0.26, 1.0, wear=(0.8, 0.72, 0.55), wear_rough=0.18)
PAINT = C.mat_paint("tl3_stencil", (0.6, 0.6, 0.56))
MATS = [TI, TI_DARK, GOLD, PAINT]


def hex_pockets(target, frame, n_dir, cells, r, depth):
    """Pockets a hex lattice into `target`'s outer face (HIGH): one hex prism per (u, v) cell."""
    o, U, Vv = frame
    cutters = []
    bvh = C.Body._bvh(target)
    for u, v in cells:
        p = o + U * u + Vv * v
        loc, nrm, _i, _t = bvh.ray_cast(p + n_dir * 0.05, -n_dir, 0.1)
        if loc is None:
            continue
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r, depth=depth * 2)
        rot = V(nrm).to_track_quat("Z", "Y").to_matrix().to_4x4()
        spin = Matrix.Rotation(math.radians(30), 4, "Z")
        bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ rot @ spin, verts=bm.verts)
        me = bpy.data.meshes.new("hex")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("hex", me)
        bpy.context.scene.collection.objects.link(ob)
        cutters.append(ob)
    if not cutters:
        return target
    tool = C.join(cutters, "hex_tool")
    m = target.modifiers.new("hex", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = tool
    target = C.apply_all(target)
    bpy.data.objects.remove(tool)
    return target


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    el, wr, fg = body.joint("forearm." + side), body.joint("hand." + side), body.joint("fingers." + side)
    a = (wr - el).normalized()
    out = V((s, 0.0, 0.25))
    out = (out - a * out.dot(a)).normalized()
    across = a.cross(out).normalized()
    # ---- wrist saddle (forearm bone)
    c = wr - a * 0.03
    poly = [(-0.017, -0.026), (0.012, -0.03), (0.019, -0.022), (0.019, 0.022), (0.012, 0.03), (-0.017, 0.026)]
    frame = (c + out * 0.3, a, across)
    hi, lo = C.plate("saddle_" + side, body, poly, frame, -out, 0.0025, 0.0045, facet_deg=9.0, smooth_r=0.012, bevel=0.0012)
    C.setmat(hi, TI)
    C.setmat(lo, TI)
    cells = []
    for row in range(-2, 3):
        for col in range(-1, 2):
            cells.append((col * 0.0085 + (0.00425 if row % 2 else 0.0) - 0.004, row * 0.0074))
    hi = hex_pockets(hi, (c, a, across), out, cells, 0.0036, 0.0016)
    hi_l, lo_l = [hi], [lo]
    pts = C.surface_points(hi, -out, [(0.011, -0.015), (0.011, 0.0), (0.011, 0.015)], (c + out * 0.3, a, across))
    for det, lst in ((True, hi_l), (False, lo_l)):
        for loc, nrm in pts:
            lst.append(C.cyl("washer", loc - nrm * 0.0005, loc + nrm * 0.0012, 0.0046, TI_DARK, det, 20, 0.0004))
            if det:
                bo = C.bolt("ab", loc + nrm * 0.0012, nrm, r=0.0034, h=0.0024)
                lst.append(C.setmat(C.apply_all(bo), GOLD))
                lst.append(C.cyl("socket", loc + nrm * 0.0022, loc + nrm * 0.0042, 0.0013, TI_DARK, True, 6, 0.0))
            else:
                lst.append(C.cyl("ab", loc + nrm * 0.0012, loc + nrm * 0.0036, 0.0034, GOLD, False, 6, 0.0))
    if True:
        loc, nrm = C.surface_points(hi, -out, [(-0.014, 0.0)], (c + out * 0.3, a, across))[0]
        st = C.stencil("st_tl3", "TL-3", loc, nrm, across * s, 0.0042, PAINT, target=hi)
        hi_l.append(C.apply_all(st))
    C.add_piece("saddle_" + side, "forearm." + side, C.join(hi_l, "saddle_high"), C.join(lo_l, "saddle_low"))

    # ---- splint and knuckle bar (hand bone)
    h_ax = (fg - wr).normalized()
    hout = (out - h_ax * out.dot(h_ax)).normalized()
    hacross = h_ax.cross(hout).normalized()
    hi_l, lo_l = [], []

    def back_of_hand(p):
        hit, n = body.cast(p + hout * 0.2, -hout, ("suit",), 0.4)
        return hit if hit is not None else p + hout * 0.02

    k0 = back_of_hand(fg + h_ax * 0.012)
    w0 = back_of_hand(wr + h_ax * 0.012)
    lift = max((back_of_hand(wr.lerp(fg + h_ax * 0.012, t / 6)) - w0.lerp(k0, t / 6)).dot(hout) for t in range(7))
    w0 += hout * (lift + 0.0025)
    k0 += hout * (lift + 0.0025)
    for det, lst in ((True, hi_l), (False, lo_l)):
        ax = (k0 - w0).normalized()
        n = ax.cross(hacross).normalized()
        if n.dot(hout) < 0:
            n = -n
        # Knuckle bar: a shallow arc across the four knuckles.
        bar_c = k0 + n * 0.003
        outline = [(-0.009, -0.043), (0.004, -0.045), (0.009, -0.038), (0.009, 0.038), (0.004, 0.045), (-0.009, 0.043),
                   (-0.011, 0.03), (-0.011, -0.03)]
        lst.append(C.prism("bar", outline, (bar_c - n * 0.004, ax, hacross, n), 0.0065, TI, det, 0.0012))
        lst.append(C.prism("ridge", [(0.003, -0.04), (0.0085, -0.036), (0.0085, 0.036), (0.003, 0.04)],
                           (bar_c + n * 0.0024, ax, hacross, n), 0.0028, TI_DARK, det, 0.0006))
        for k in range(4):
            p = bar_c + hacross * (-0.03 + 0.02 * k) - ax * 0.002 + n * 0.0025
            if det:
                bo = C.bolt("kb", p, n, r=0.0028, h=0.002)
                lst.append(C.setmat(C.apply_all(bo), GOLD))
                lst.append(C.cyl("ks", p + n * 0.0019, p + n * 0.0034, 0.001, TI_DARK, True, 6, 0.0))
            else:
                lst.append(C.cyl("kb", p - n * 0.0005, p + n * 0.0022, 0.0028, GOLD, False, 6, 0.0))
    C.add_piece("hand_" + side, "hand." + side, C.join(hi_l, "hand_high"), C.join(lo_l, "hand_low"))

hl = body.joint("hand.L")
C.run("tl3_titanium_skeleton", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("hand", hl + V((0.4, -0.18, 0.12)), hl + V((0.02, 0, -0.03)), 70),
    ("hand_top", hl + V((0.25, 0.22, 0.3)), hl + V((0.02, 0, -0.04)), 70)))
