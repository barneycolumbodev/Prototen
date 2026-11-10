"""KS-2 Kinetic Striker Rams (docs/design.md §3.6): pneumatic rams that drive the fist.

Design: on the inner side of each forearm (the side the other forearm parts leave free: HS-5 fins on the
outside, EM-2 on the front, TN-9 on the ulna edge, FC-1 at the inner wrist), two short fat pneumatic rams lie
side by side, fed from a valve block at the elbow end and a slim air bottle laid between them, and braced at the
wrist end by a striker yoke: a heavy steel crosshead the rods drive into, which the fist rides on at impact. Gunmetal bodies with red
safety bands, chrome rods, a red-orange ready light on the valve block and a KS-2 stencil.

Pieces ride on forearm.L/R.

Run:
  tools/blender.sh raw_assets/augments/passives/ks2_striker_rams/build.py \\
      --out assets/augments/passives/ks2_striker_rams/ks2_striker_rams.gltf --preview docs/previews/ks2_striker_rams
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "ks2"
body = C.body_once()

GUN = C.mat_metal("ks2_gunmetal", base=(0.075, 0.077, 0.082), rough=0.32, wear=(0.52, 0.52, 0.54), brushed=0.06)
CHROME = C.mat_chrome("ks2_chrome")
STEEL = C.mat_metal("ks2_steel", base=(0.42, 0.42, 0.43), rough=0.24, wear=(0.65, 0.65, 0.66), brushed=0.1)
RED = hs.material("ks2_red", (0.2, 0.02, 0.014), 0.45, 0.0, wear=(0.5, 0.5, 0.5), wear_rough=0.3)
GLOW = C.mat_glow("ks2_ready", color=(1.0, 0.28, 0.06), strength=4.0)
PAINT = C.mat_paint("ks2_stencil", (0.72, 0.7, 0.64))
MATS = [GUN, CHROME, STEEL, RED, GLOW, PAINT]


def surf(p, d):
    hit, _n = body.cast(p + d * 0.1, -d, ("suit",), 0.2)
    return hit if hit is not None else p + d * 0.045


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    el, wr = body.joint("forearm." + side), body.joint("hand." + side)
    a = (wr - el).normalized()
    L = (wr - el).length
    out = V((s, 0.0, 0.25))
    inner = -(out - a * out.dot(a)).normalized()
    sd = a.cross(inner).normalized()
    t0, t1 = 0.14, 0.7
    s0, s1 = surf(el + a * L * t0, inner), surf(el + a * L * t1, inner)
    lift = max((surf(el + a * L * (t0 + (t1 - t0) * k / 8) + sd * w, inner) - s0.lerp(s1, k / 8)).dot(inner)
               for k in range(9) for w in (-0.016, 0.0, 0.016))
    b0, b1 = s0 + inner * (lift + 0.003), s1 + inner * (lift + 0.003)
    hi_l, lo_l = [], []
    for det, lst in ((True, hi_l), (False, lo_l)):
        r = 0.0085
        for w in (-1, 1):
            p0 = b0 + inner * r + sd * w * 0.0105 + a * 0.03
            p1 = b1 + inner * r + sd * w * 0.0105 - a * 0.012
            pm = p0.lerp(p1, 0.62)
            lst.append(C.cyl("body", p0, pm, r, GUN, det, 24, 0.0012))
            lst.append(C.cyl("band", pm - a * 0.012, pm - a * 0.004, r * 1.02, RED, det, 24, 0.0))
            lst.append(C.cyl("gland", pm - a * 0.002, pm + a * 0.005, r * 0.8, STEEL, det, 24, 0.0006))
            lst.append(C.cyl("rod", pm, p1, r * 0.45, CHROME, det, 16, 0.0003))
        # Valve block and air bottle at the elbow end.
        vb = b0 + a * 0.014
        lst.append(C.prism("valve", C.chamfer_rect(0.017, 0.022, 0.005), (vb - inner * 0.003, a, sd, inner), 0.024, GUN, det, 0.0014))
        lst.append(C.slab("ready", vb + inner * 0.0212, (a, sd, inner), (0.004, 0.012, 0.001), GLOW, False))
        bt = vb + inner * 0.0275
        lst.append(C.cyl("bottle", bt + a * 0.022, bt + a * 0.07, 0.0062, RED, det, 20, 0.0012))
        lst.append(C.cyl("bottle_cap", bt + a * 0.016, bt + a * 0.023, 0.0045, STEEL, det, 20, 0.0005))
        # Striker yoke at the wrist end.
        yk = b1 + inner * 0.009 - a * 0.004
        lst.append(C.slab("yoke", yk, (a, sd, inner), (0.012, 0.042, 0.02), STEEL, det, 0.0018))
        lst.append(C.slab("yoke_face", yk + a * 0.0068, (a, sd, inner), (0.0025, 0.036, 0.016), GUN, det, 0.0006))
        if det:
            for w in (-0.014, 0.014):
                bo = C.bolt("yb", yk + inner * 0.01 + sd * w, inner, r=0.0024, h=0.0016)
                lst.append(C.setmat(C.apply_all(bo), GUN))
            st = C.stencil("st", "KS-2", vb + inner * 0.0212 - a * 0.008, inner, sd * s, 0.0052, PAINT)
            lst.append(C.apply_all(st))
    C.add_piece("ks2_" + side, "forearm." + side, C.join(hi_l, "ks2_high"), C.join(lo_l, "ks2_low"))

fl = body.joint("forearm.L") * 0.55 + body.joint("hand.L") * 0.45
C.run("ks2_striker_rams", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("inner", fl + V((-0.42, -0.25, -0.08)), fl + V((-0.02, 0.0, 0.0)), 60),
    ("under", fl + V((-0.25, 0.2, -0.38)), fl + V((-0.02, 0.0, 0.0)), 60)))
