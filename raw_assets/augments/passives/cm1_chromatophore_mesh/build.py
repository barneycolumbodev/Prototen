"""CM-1 Chromatophore Skin Mesh (docs/design.md §3.6): electrochromic cells that match the background.

Design: the mesh lies under the suit, but it surfaces in panels where the plates used to bond (the part's
tradeoff: thinner there). On the outer side of each upper arm and on each flank under the arm, a thin panel of
hexagonal chromatophore cells, each a slightly different dark tone (slate, olive, charcoal, blue-grey) like the
pixels of an active camouflage caught mid-change, framed by a fine seam with two driver nodes. Low and flat:
nothing for a light to catch.

The game mesh is the panel; the cells reach it through the bake. Pieces ride on upper_arm.L/R and chest.

Run:
  tools/blender.sh raw_assets/augments/passives/cm1_chromatophore_mesh/build.py \\
      --out assets/augments/passives/cm1_chromatophore_mesh/cm1_chromatophore_mesh.gltf \\
      --preview docs/previews/cm1_chromatophore_mesh
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "cm1"
body = C.body_once()
random.seed(11)

BACK = C.mat_metal("cm1_backing", base=(0.03, 0.032, 0.035), rough=0.5, wear=(0.2, 0.2, 0.21))
TONES = [hs.material("cm1_c%d" % i, col, 0.42, 0.0) for i, col in enumerate(
    ((0.045, 0.05, 0.055), (0.05, 0.055, 0.035), (0.03, 0.03, 0.032), (0.04, 0.05, 0.065), (0.07, 0.072, 0.065)))]
NODE = C.mat_glow("cm1_node", color=(0.36, 0.86, 0.78), strength=2.0)
MATS = [BACK, NODE] + TONES
parts = {}


def put(bone, det, ob):
    hi, lo = parts.setdefault(bone, ([], []))
    (hi if det else lo).extend(ob if isinstance(ob, list) else [ob])


def hex_cell(loc, nrm, up, r, h, mat):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r * 0.92, depth=h)
    rot = V(nrm).to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc + nrm * h * 0.5) @ rot @ Matrix.Rotation(math.radians(30), 4, "Z"),
                        verts=bm.verts)
    me = bpy.data.meshes.new("cell")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("cell", me)
    bpy.context.scene.collection.objects.link(ob)
    return C.setmat(ob, mat)


def panel(bone, center, out, up, hu, hv, tag, reach=0.3, gap=0.0015):
    out = V(out).normalized()
    up = (V(up) - out * V(up).dot(out)).normalized()
    side = up.cross(out).normalized()
    # Rays start `reach` + 0.5 m out from the sheet (C.project_onto), and C.surface_points 0.4 m out from its frame:
    # on the flank the arm hangs close, so those starts must sit between the torso and the arm.
    frame = (center + out * reach, up, side)
    sframe = (center + out * (reach + 0.1 if reach < 0 else reach), up, side)
    poly = C.chamfer_rect(hu, hv, min(hu, hv) * 0.35)
    hi, lo = C.plate(tag, body, poly, frame, -out, gap, 0.0016 + gap * 0.5, facet_deg=5.0, smooth_r=0.012, bevel=0.0006)
    C.setmat(hi, BACK)
    C.setmat(lo, BACK)
    put(bone, True, hi)
    put(bone, False, lo)
    r = 0.0046
    cells = []
    du, dv = r * 1.5, r * math.sqrt(3)
    nu = int(hu * 2 / du)
    for i in range(-nu // 2, nu // 2 + 1):
        for j in range(-int(hv / dv) - 1, int(hv / dv) + 2):
            u = i * du
            v = j * dv + (dv * 0.5 if i % 2 else 0.0)
            if abs(u) < hu - 0.006 and abs(v) < hv - 0.006:
                cells.append((u, v))
    pts = C.surface_points(hi, -out, cells, sframe)
    cell_obs = [hex_cell(loc, nrm, up, r * 0.86, 0.0007, random.choice(TONES)) for loc, nrm in pts]
    put(bone, True, C.join(cell_obs, tag + "_cells"))
    for v in (-1, 1):
        q = C.surface_points(hi, -out, [(hu - 0.0035, v * (hv - 0.006))], sframe)
        if q:
            loc, nrm = q[0]
            for det in (True, False):
                put(bone, det, C.cyl("node", loc, loc + nrm * 0.0016, 0.0022, NODE, det, 12, 0.0))


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    sh, el = body.joint("upper_arm." + side), body.joint("forearm." + side)
    ax = (el - sh).normalized()
    out = V((s, -0.2, 0.3))
    out = (out - ax * out.dot(ax)).normalized()
    # The suit has a raised strip on the outer arm: the panel bridges over it.
    panel("upper_arm." + side, sh.lerp(el, 0.58), out, -ax, 0.05, 0.026, "arm_" + side, gap=0.006)
    panel("chest", V((0.17 * s, 0.065, 1.29)), V((s, 0.4, 0.0)), V((0, 0, 1)), 0.055, 0.03, "flank_" + side, reach=-0.45)

for bone, (h, l) in parts.items():
    C.add_piece("cm1_" + bone.replace(".", "_"), bone, C.join(h, "cm1_%s_high" % bone), C.join(l, "cm1_%s_low" % bone))

ua = body.joint("upper_arm.L") * 0.4 + body.joint("forearm.L") * 0.6
C.run("cm1_chromatophore_mesh", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("arm", ua + V((0.42, -0.22, 0.12)), ua + V((0.02, 0, 0)), 60),
    ("flank", V((0.58, 0.05, 1.34)), V((0.16, 0.06, 1.29)), 60)))
