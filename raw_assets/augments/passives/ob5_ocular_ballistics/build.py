"""OB-5 Ocular Ballistics Suite (docs/design.md §3.6): the rangefinder that feeds the eyes.

Design: the eyes are inside, so what shows is what feeds them: a laser rangefinder pod on the right brow above the
outer end of the visor (the shooting eye's side), and a smaller ballistic sensor on the left. The pod is a short
machined barrel with cooling rings in a faceted cradle clamped to the helmet: a deep violet-blue coated objective
lens, a small red emitter dot beside it, and an amber ready light on top. The left sensor is a flat lozenge with
a single coated lens. With the helmet off they stay where the implants surface, at the brow.

Pieces ride on the head bone.

Run:
  tools/blender.sh raw_assets/augments/passives/ob5_ocular_ballistics/build.py \\
      --out assets/augments/passives/ob5_ocular_ballistics/ob5_ocular_ballistics.gltf --preview docs/previews/ob5_ocular_ballistics
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "ob5"
body = C.body_once()

HOUSING = C.mat_metal("ob5_housing", base=(0.06, 0.062, 0.067), rough=0.3, wear=(0.48, 0.48, 0.5), brushed=0.05)
RING = C.mat_metal("ob5_ring", base=(0.28, 0.28, 0.29), rough=0.22, wear=(0.6, 0.6, 0.62), brushed=0.12)
LENS = hs.material("ob5_lens", (0.03, 0.02, 0.09), 0.04, 0.0, emission=((0.3, 0.16, 0.85), 1.6), coat=1.0)
LASER = C.mat_glow("ob5_laser", color=(1.0, 0.08, 0.05), strength=5.0)
READY = C.mat_glow("ob5_ready", color=(1.0, 0.55, 0.12), strength=3.0)
PAINT = C.mat_paint("ob5_stencil", (0.6, 0.6, 0.56))
MATS = [HOUSING, RING, LENS, LASER, READY, PAINT]
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
hi_l, lo_l = [], []


def helmet_front(x, z):
    hit, n = body.cast(V((x, -0.5, z)), Y, ("helmet",), 0.6)
    return hit, n


for det, lst in ((True, hi_l), (False, lo_l)):
    # ---- right brow: the rangefinder (operative's right = -X)
    base, n = helmet_front(-0.064, 1.779)
    axis = V((-0.12, -1.0, 0.02)).normalized()
    c = base + V((-0.012, -0.004, 0.006))
    rear, front = c - axis * 0.0, c + axis * 0.03
    lst.append(C.prism("cradle", C.chamfer_rect(0.017, 0.009, 0.003), (base - axis * 0.002 + X * -0.004, -X, Z, axis),
                       0.014, HOUSING, det, 0.0012))
    lst.append(C.cyl("barrel", rear, front, 0.0088, HOUSING, det, 28, 0.001))
    lst.append(C.cyl("bezel", front - axis * 0.004, front + axis * 0.0015, 0.0098, RING, det, 28, 0.0006))
    lst.append(C.cyl("lens", front, front + axis * 0.0012, 0.0068, LENS, det, 28, 0.0))
    if det:
        for k in range(4):
            q = rear.lerp(front, 0.2 + 0.15 * k)
            lst.append(C.cyl("fin", q - axis * 0.0007, q + axis * 0.0007, 0.0099, RING, True, 28, 0.0))
    emit = front + X * 0.0 + Z * -0.0128 + axis * -0.002
    lst.append(C.cyl("emitter", emit - axis * 0.004, emit + axis * 0.0012, 0.0028, RING, det, 16, 0.0003))
    lst.append(C.cyl("emitter_dot", emit + axis * 0.0012, emit + axis * 0.0018, 0.0014, LASER, det, 12, 0.0))
    lst.append(C.slab("ready", rear.lerp(front, 0.75) + Z * 0.0091, (axis, X, Z), (0.006, 0.0022, 0.0008), READY, False))
    # ---- left brow: the ballistic sensor
    base2, n2 = helmet_front(0.064, 1.779)
    ax2 = V((0.12, -1.0, 0.02)).normalized()
    c2 = base2 + V((0.006, -0.002, 0.004))
    lst.append(C.prism("sensor", C.chamfer_rect(0.012, 0.007, 0.004), (c2 - ax2 * 0.004, X, Z, ax2), 0.011, HOUSING, det, 0.001))
    lst.append(C.cyl("s_lens", c2 + ax2 * 0.006, c2 + ax2 * 0.0075, 0.0042, LENS, det, 20, 0.0))
    lst.append(C.cyl("s_bezel", c2 + ax2 * 0.0055, c2 + ax2 * 0.0072, 0.0053, RING, det, 20, 0.0003))
if True:
    st = C.stencil("st", "OB-5", c + Z * 0.0005 + axis * 0.012 + X * -0.0089, X * -1, Z, 0.0032, PAINT)
    hi_l.append(C.apply_all(st))
C.add_piece("optics", "head", C.join(hi_l, "ob5_high"), C.join(lo_l, "ob5_low"))

hd = V((0.0, -0.06, 1.74))
C.run("ob5_ocular_ballistics", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("face", hd + V((-0.12, -0.42, 0.05)), hd + V((-0.02, 0, 0.0)), 70),
    ("side", hd + V((-0.35, -0.2, 0.08)), hd + V((-0.05, 0.0, 0.0)), 70)))
