"""RX-9 Reflex Overclock (docs/design.md §3.4): the co-processor module at the base of the skull.

Design: a slim vertical module on the back of the head over the occipital keel, above the nape, narrow enough to
sit between the NL-3's antenna blades when both are fitted: a faceted gunmetal housing with a cold white slit
crossed by three ticks (an escapement, the clock it overclocks), small heat-sink ribs down each side, a hex
access screw at top and bottom, and two fibre leads that drop from its base into the nape. RX-9 stencil.

Mounted like the passive hardware (raw_assets/augments/passives/_common.py, model space on the head bone).

Run:
  tools/blender.sh raw_assets/augments/rx9_reflex_overclock/build.py \\
      --out assets/augments/rx9_reflex_overclock/rx9_reflex_overclock.gltf --preview docs/previews/rx9_reflex_overclock
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "passives"))
import _common as C  # noqa: E402
from _common import V  # noqa: E402

args = C.args_parser()
C.TAG = "rx9"
body = C.body_once()
NL3 = C.add_obstacle(body, "nl3_cortical_uplink", "nl3")

HOUSING = C.mat_metal("rx9_housing", base=(0.055, 0.057, 0.062), rough=0.3, wear=(0.48, 0.48, 0.5), brushed=0.05)
RIB = C.mat_metal("rx9_rib", base=(0.2, 0.2, 0.21), rough=0.24, wear=(0.6, 0.6, 0.62), brushed=0.1)
GLOW = C.mat_glow("rx9_glow", color=(0.7, 0.88, 1.0), strength=5.0)
FIBRE = C.mat_rubber("rx9_fibre")
PAINT = C.mat_paint("rx9_stencil", (0.6, 0.6, 0.56))
MATS = [HOUSING, RIB, GLOW, FIBRE, PAINT]
Y, Z, X = V((0, 1, 0)), V((0, 0, 1)), V((1, 0, 0))


def back(x, z):
    hit, _n = body.cast(V((x, 0.5, z)), -Y, ("helmet",), 0.6)
    return hit


Z0, Z1 = 1.705, 1.785
y0 = max(back(x, z).y for x in (-0.02, 0.0, 0.02) for z in (Z0, (Z0 + Z1) / 2, Z1))
o = V((0.0, y0 - 0.006, (Z0 + Z1) / 2))
hi_l, lo_l = [], []
for det, lst in ((True, hi_l), (False, lo_l)):
    outline = [(-0.016, -0.04), (0.016, -0.04), (0.02, -0.032), (0.02, 0.03), (0.01, 0.041), (-0.01, 0.041), (-0.02, 0.03), (-0.02, -0.032)]
    lst.append(C.prism("housing", outline, (o, X, Z, Y), 0.017, HOUSING, det, 0.0016, angle=30))
    face = o + Y * 0.017
    lst.append(C.slab("slit_frame", face + Z * -0.002, (X, Z, Y), (0.008, 0.058, 0.0016), RIB, det, 0.0004))
    lst.append(C.slab("slit", face + Z * -0.002 + Y * 0.0009, (X, Z, Y), (0.0034, 0.052, 0.001), GLOW, False))
    for k in (-1, 0, 1):
        lst.append(C.slab("tick", face + Z * (-0.002 + k * 0.016) + Y * 0.0011, (X, Z, Y), (0.011, 0.0015, 0.0009), GLOW, False))
    for sx in (-1, 1):
        for k in range(5):
            z = -0.026 + 0.012 * k
            lst.append(C.slab("rib", o + Y * 0.011 + X * sx * 0.0215 + Z * z, (X, Z, Y), (0.004, 0.0045, 0.012), RIB, det, 0.0004))
    for zz in (-0.033, 0.034):
        lst.append(C.cyl("screw", face + Z * zz - Y * 0.001, face + Z * zz + Y * 0.0012, 0.0026, RIB, det, 6, 0.0002))
    for sx in (-1, 1):
        start = o + Y * 0.006 + X * sx * 0.008 - Z * 0.04
        nape = back(sx * 0.008, 1.66)
        end = nape + Y * 0.003 if nape is not None else start - Z * 0.05
        lst.append(C.cable("lead", [start, start - Z * 0.015 + Y * 0.002, end], 0.0018, FIBRE, det))
st = C.stencil("st", "RX-9", o + Y * 0.0171 + Z * 0.026 + X * 0.0, Y, Z, 0.0042, PAINT)
hi_l.append(C.apply_all(st))
C.add_piece("module", "head", C.join(hi_l, "rx9_high"), C.join(lo_l, "rx9_low"))

hd = V((0.0, 0.1, 1.72))
C.run("rx9_reflex_overclock", args, MATS, (
    ("back", (-1.6, 4.2, 1.6), (0, 0, 1.4), 85),
    ("nape", hd + V((-0.12, 0.42, 0.04)), hd + V((0, 0.02, 0.0)), 70),
    ("with_nl3", hd + V((0.28, 0.35, 0.02)), hd + V((0, 0.02, -0.02)), 70)), show=NL3)
