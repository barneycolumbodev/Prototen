"""SA-2 Synaptic Accelerator (docs/design.md §3.6): the co-processor's two spools on the sides of the neck.

Design: the accelerator wraps the brainstem; what shows are its two signal spools, one each side of the neck
under the jaw seal, where the vagus and accessory nerves run. Each spool is a faceted gunmetal capsule with a
long window: inside, a stack of pearl-white myelin discs (the co-processor's sheath windings) with teal light
between them, like the suit's seam light. A fibre lead leaves the bottom of each capsule and curves back round
the neck toward the spine. A small SA-2 stencil and a three-dot status bar sit on the capsule's shoulder.

Pieces ride on the neck bone.

Run:
  tools/blender.sh raw_assets/augments/passives/sa2_synaptic_accelerator/build.py \\
      --out assets/augments/passives/sa2_synaptic_accelerator/sa2_synaptic_accelerator.gltf \\
      --preview docs/previews/sa2_synaptic_accelerator
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "sa2"
body = C.body_once()

HOUSING = C.mat_metal("sa2_housing", base=(0.055, 0.057, 0.062), rough=0.3, wear=(0.45, 0.46, 0.48), brushed=0.05)
FRAME = C.mat_metal("sa2_frame", base=(0.16, 0.165, 0.17), rough=0.26, wear=(0.6, 0.6, 0.62), brushed=0.08)
PEARL = hs.material("sa2_myelin", (0.78, 0.76, 0.7), 0.22, 0.0, coat=0.8)
GLOW = C.mat_glow("sa2_glow", color=(0.36, 0.86, 0.78), strength=5.0)
LED = C.mat_glow("sa2_led", color=(0.36, 0.86, 0.78), strength=2.5)
FIBRE = C.mat_rubber("sa2_fibre")
PAINT = C.mat_paint("sa2_stencil", (0.6, 0.6, 0.56))
MATS = [HOUSING, FRAME, PEARL, GLOW, LED, FIBRE, PAINT]

ZC = 1.588          # height of the spool centre
H = 0.04           # capsule height
hi_l, lo_l = [], []
for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    d = V((0.78 * s, -0.62, 0.0)).normalized()
    hit, n = body.cast(V((0, 0.0, ZC)) + d * 0.3, -d, ("suit",), 0.5)
    if hit is None:
        hit = V((0, 0, ZC)) + d * 0.066
    up = V((0, 0, 1))
    o, U, Vv, N = C.frame_at(hit, d, up)
    for det, lst in ((True, hi_l), (False, lo_l)):
        # Capsule: a faceted lozenge, back face on the neck.
        outline = [(-0.009, -H / 2), (0.009, -H / 2), (0.0125, -H / 2 + 0.006), (0.0125, H / 2 - 0.008), (0.006, H / 2),
                   (-0.006, H / 2), (-0.0125, H / 2 - 0.008), (-0.0125, -H / 2 + 0.006)]
        lst.append(C.prism("capsule", outline, (o - N * 0.002, U, Vv, N), 0.0085, HOUSING, det, 0.0014, angle=30))
        # Window frame and the myelin stack inside it.
        win = C.chamfer_rect(0.0072, H / 2 - 0.0075, 0.002)
        lst.append(C.prism("frame", win, (o + N * 0.0062, U, Vv, N), 0.0032, FRAME, det, 0.0006))
        n_disc = 7
        for k in range(n_disc):
            z = -H / 2 + 0.0085 + (H - 0.017) * k / (n_disc - 1)
            c = o + N * 0.0085 + Vv * z
            lst.append(C.cyl("disc", c - Vv * 0.0013, c + Vv * 0.0013, 0.0058, PEARL, det, 20, 0.0004))
            if k < n_disc - 1:
                g = c + Vv * (H - 0.017) / (n_disc - 1) * 0.5
                lst.append(C.cyl("gap", g - Vv * 0.0009, g + Vv * 0.0009, 0.0045, GLOW, det, 16, 0.0))
        lst.append(C.cyl("core", o + N * 0.0085 - Vv * (H / 2 - 0.007), o + N * 0.0085 + Vv * (H / 2 - 0.007), 0.0022, FRAME,
                         det, 12, 0.0))
        # Status bar on the top shoulder of the capsule.
        for k in range(3):
            lst.append(C.slab("led", o + N * 0.0068 + Vv * (H / 2 - 0.0035) + U * (k - 1) * 0.0034, (U, Vv, N),
                              (0.0022, 0.0012, 0.0008), LED, False))
        # Fibre lead: from the bottom of the capsule, back round the neck and down toward the spine.
        start = o + N * 0.003 - Vv * (H / 2 + 0.001)
        pts = [start]
        for k, (ang, dz, lift) in enumerate([(0, -0.006, 0.005)] + [(a, -0.008 - 0.012 * a / 105, 0.0032)
                                                                       for a in (15, 30, 45, 60, 75, 90, 105)]):
            dd = V((math.sin(math.radians(ang)) * 0.0, 0, 0))
            th = math.atan2(d.y, d.x) + math.radians(ang) * s
            ray = V((math.cos(th), math.sin(th), 0))
            hp, _n = body.cast(V((0, 0, ZC - H / 2 + dz)) + ray * 0.3, -ray, ("suit",), 0.5)
            if hp is None:
                continue
            pts.append(hp + ray * lift + dd)
        lst.append(C.cable("lead", pts, 0.0022, FIBRE, det))
        if det:
            for p in pts[1:3]:
                lst.append(C.cyl("clip", p - V((0, 0, 0.0016)), p + V((0, 0, 0.0016)), 0.0032, FRAME, True, 12, 0.0))
            st = C.stencil("st_sa2", "SA-2", o + N * 0.0067 - Vv * (H / 2 - 0.004), N, Vv, 0.0034, PAINT)
            hi_l.append(C.apply_all(st))
C.add_piece("spools", "neck", C.join(hi_l, "sa2_high"), C.join(lo_l, "sa2_low"))

nk = V((0.0, -0.06, ZC))
C.run("sa2_synaptic_accelerator", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("neck", nk + V((0.28, -0.32, 0.02)), nk + V((0.03, 0.03, -0.005)), 70),
    ("neck_low", nk + V((-0.2, -0.3, -0.12)), nk + V((-0.02, 0.03, 0.0)), 70)))
