"""VS-1 Vestibular Stabilizer (docs/design.md §3.6): gyro pucks behind the ears.

Design: a gyroscopic inner-ear graft shows as a puck on each side of the head, just behind the ear, faired into
the helmet's side: a machined bezel around a recessed face where two gimbal rings sit at angles round a hub (the
gyro you'd see if you opened it). A horizon bar of teal light crosses the bezel either side of the gimbal; it is
the part's one tell. A teardrop fairing behind the puck blends it into the helmet; a small VS-1 stencil sits on
it. With the helmet off the pucks stay where the implant is, behind the ears.

Pieces ride on the head bone.

Run:
  tools/blender.sh raw_assets/augments/passives/vs1_vestibular_stabilizer/build.py \\
      --out assets/augments/passives/vs1_vestibular_stabilizer/vs1_vestibular_stabilizer.gltf \\
      --preview docs/previews/vs1_vestibular_stabilizer
"""
import math
import os
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "vs1"
body = C.body_once()

HOUSING = C.mat_metal("vs1_housing", base=(0.06, 0.062, 0.067), rough=0.3, wear=(0.48, 0.48, 0.5), brushed=0.05)
BEZEL = C.mat_metal("vs1_bezel", base=(0.3, 0.3, 0.31), rough=0.22, wear=(0.62, 0.62, 0.63), brushed=0.14)
BRASS = hs.material("vs1_gimbal", (0.62, 0.5, 0.3), 0.2, 1.0)
FACE = C.mat_metal("vs1_face", base=(0.02, 0.02, 0.022), rough=0.5)
GLOW = C.mat_glow("vs1_glow", color=(0.36, 0.86, 0.78), strength=5.0)
PAINT = C.mat_paint("vs1_stencil", (0.6, 0.6, 0.56))
MATS = [HOUSING, BEZEL, BRASS, FACE, GLOW, PAINT]


def torus(name, center, normal, R, r, det, mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40 if det else 14,
                                     minor_segments=10 if det else 4)
    ob = bpy.context.active_object
    ob.name = name
    rot = V(normal).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    ob.data.transform(Matrix.Translation(center) @ rot)
    C.setmat(ob, mat)
    ob.data.shade_smooth()
    return ob


ZC, ANG = 1.695, 22.0
hi_l, lo_l = [], []
for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    d = V((math.cos(math.radians(ANG)) * s, math.sin(math.radians(ANG)), 0.0))
    hit, n = body.cast(V((0, 0, ZC)) + d * 0.4, -d, ("helmet",), 0.5)
    o, U, Vv, N = C.frame_at(hit, d, V((0, 0, 1)))
    for det, lst in ((True, hi_l), (False, lo_l)):
        # Teardrop fairing behind the puck (toward the back of the head), then the puck.
        back = V((0, 1, 0)) - N * V((0, 1, 0)).dot(N)
        back.normalize()
        u_b = back
        v_b = N.cross(u_b).normalized()
        pts = [(math.cos(t) * 0.022, math.sin(t) * 0.022) for t in [math.radians(a) for a in range(90, 271, 30)]]
        pts += [(0.034, -0.01), (0.044, 0.0), (0.034, 0.01)]
        lst.append(C.prism("fairing", pts, (o - N * 0.004, u_b, v_b, N), 0.008, HOUSING, det, 0.0016, angle=28))
        lst.append(C.cyl("bezel", o + N * 0.002, o + N * 0.0115, 0.019, BEZEL, det, 40, 0.0012))
        lst.append(C.cyl("face", o + N * 0.0105, o + N * 0.0118, 0.0145, FACE, det, 40, 0.0))
        c = o + N * 0.0122
        lst.append(torus("gimbal_a", c, (N + Vv * 1.2).normalized(), 0.0115, 0.0011, det, BRASS))
        lst.append(torus("gimbal_b", c, (N + U * 1.0).normalized(), 0.0085, 0.001, det, BRASS))
        lst.append(C.cyl("hub", c - N * 0.002, c + N * 0.0035, 0.0034, BEZEL, det, 20, 0.0005))
        # Horizon bar either side of the gimbal.
        for w in (-1, 1):
            lst.append(C.slab("horizon", o + N * 0.0118 + U * w * 0.0163, (U, Vv, N), (0.0045, 0.0013, 0.0012), GLOW, False))
        if det:
            for k in range(8):
                a = k * math.pi / 4 + math.pi / 8
                bo = C.bolt("bb", o + N * 0.0115 + (U * math.cos(a) + Vv * math.sin(a)) * 0.0168, N, r=0.0011, h=0.0008)
                lst.append(C.setmat(C.apply_all(bo), HOUSING))
            st = C.stencil("st_vs1", "VS-1", o + N * 0.0042 + u_b * 0.031, N, v_b * -1 if s > 0 else v_b, 0.0036, PAINT)
            lst.append(C.apply_all(st))
C.add_piece("pucks", "head", C.join(hi_l, "vs1_high"), C.join(lo_l, "vs1_low"))

hd = V((0.0, 0.0, ZC))
C.run("vs1_vestibular_stabilizer", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("side", hd + V((0.42, -0.14, 0.03)), hd + V((0.05, 0.02, 0.0)), 70),
    ("bare", hd + V((-0.4, -0.2, 0.05)), hd + V((-0.05, 0.02, -0.01)), 70)))
