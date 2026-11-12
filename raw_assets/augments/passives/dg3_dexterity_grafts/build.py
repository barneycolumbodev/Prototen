"""DG-3 Dexterity Grafts (docs/design.md §3.6): micro-actuators on the finger tendons.

Design: on the back of each hand, over the extensor tendons, four slim micro-actuators run from a header block at
the wrist toward the knuckles, one per finger: satin black sleeves with steel collars and gold contact tips, each
with a fine teal status line. They stop short of the knuckles, so a TL-3 knuckle bar can sit in front of them.
A DG-3 stencil sits on the header.

Pieces ride on hand.L/R.

Run:
  tools/blender.sh raw_assets/augments/passives/dg3_dexterity_grafts/build.py \\
      --out assets/augments/passives/dg3_dexterity_grafts/dg3_dexterity_grafts.gltf --preview docs/previews/dg3_dexterity_grafts
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "dg3"
body = C.body_once()

SLEEVE = hs.material("dg3_sleeve", (0.025, 0.026, 0.03), 0.38, 0.2, coat=0.4)
STEEL = C.mat_metal("dg3_steel", base=(0.45, 0.45, 0.46), rough=0.22, wear=(0.65, 0.65, 0.66), brushed=0.1)
GOLD = hs.material("dg3_gold", (0.85, 0.62, 0.28), 0.22, 1.0)
HEADER = C.mat_metal("dg3_header", base=(0.07, 0.072, 0.077), rough=0.3, wear=(0.5, 0.5, 0.52), brushed=0.05)
GLOW = C.mat_glow("dg3_glow", color=(0.36, 0.86, 0.78), strength=3.5)
PAINT = C.mat_paint("dg3_stencil", (0.6, 0.6, 0.56))
MATS = [SLEEVE, STEEL, GOLD, HEADER, GLOW, PAINT]

for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    el, wr, fg = body.joint("forearm." + side), body.joint("hand." + side), body.joint("fingers." + side)
    a = (wr - el).normalized()
    out = V((s, 0.0, 0.25))
    h_ax = (fg - wr).normalized()
    hout = (out - h_ax * out.dot(h_ax)).normalized()
    hacross = h_ax.cross(hout).normalized()

    def back(p):
        hit, _n = body.cast(p + hout * 0.2, -hout, ("suit",), 0.4)
        return hit if hit is not None else p + hout * 0.02

    w0 = back(wr + h_ax * 0.012)
    k0 = back(fg + h_ax * 0.012)
    lift = max((back(wr.lerp(fg + h_ax * 0.012, t / 8) + hacross * w) - w0.lerp(k0, t / 8)).dot(hout)
               for t in range(9) for w in (-0.025, 0.0, 0.025))
    w0 += hout * (lift + 0.002)
    k0 += hout * (lift + 0.002)
    ax = (k0 - w0).normalized()
    n = ax.cross(hacross).normalized()
    if n.dot(hout) < 0:
        n = -n
    hi_l, lo_l = [], []
    for det, lst in ((True, hi_l), (False, lo_l)):
        hd = w0 + ax * 0.004
        lst.append(C.prism("header", C.chamfer_rect(0.008, 0.03, 0.004), (hd - n * 0.003, ax, hacross, n), 0.009, HEADER, det, 0.0012))
        lst.append(C.slab("led", hd + n * 0.0062 + ax * 0.004, (ax, hacross, n), (0.0018, 0.03, 0.0008), GLOW, False))
        for k in range(4):
            w = -0.0225 + 0.015 * k
            p0 = hd + hacross * w + n * 0.0028 + ax * 0.008
            p1 = k0 + hacross * w * 1.05 + n * 0.0028 - ax * 0.016
            lst.append(C.cyl("sleeve", p0, p1, 0.0029, SLEEVE, det, 16, 0.0004))
            for f in (0.3, 0.65):
                q = p0.lerp(p1, f)
                lst.append(C.cyl("collar", q - ax * 0.0012, q + ax * 0.0012, 0.0033, STEEL, det, 16, 0.0002))
            lst.append(C.cyl("tip", p1, p1 + ax * 0.004, 0.002, GOLD, det, 12, 0.0003))
            lst.append(C.slab("line", p0.lerp(p1, 0.48) + n * 0.0029, (ax, hacross, n), ((p1 - p0).length * 0.25, 0.0007, 0.0004), GLOW, False))
        if det:
            st = C.stencil("st", "DG-3", hd + n * 0.0061 - ax * 0.002, n, hacross * s, 0.004, PAINT)
            lst.append(C.apply_all(st))
    C.add_piece("dg3_" + side, "hand." + side, C.join(hi_l, "dg3_high"), C.join(lo_l, "dg3_low"))

hl = body.joint("hand.L")
C.run("dg3_dexterity_grafts", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("hand", hl + V((0.4, -0.18, 0.12)), hl + V((0.02, 0, -0.03)), 70),
    ("hand_top", hl + V((0.25, 0.22, 0.3)), hl + V((0.02, 0, -0.04)), 70)))
