"""PC-3 Betavoltaic Power Cell (docs/design.md §3.6): a sealed tritium cell under the ribs.

Design: the cell sits on the left flank under the ribs, outside the suit where it can be swapped and shielded:
a vertical sealed cylinder in a conformal cradle, clamped by two bands. A window down its length shows the
phosphor glow of the tritium (green: the one green light on the body, so a hot PC-3 is easy to spot).
Yellow radiation band at the top with a trefoil, H-3 / BETAVOLTAIC / 200 W stencilling, knurled end caps and
an armoured conduit from the top cap into the suit at the ribs. The left flank is clear of the DL-1 canister
(right hip) and the HM-5 pumps (lower on the hips).

Pieces ride on the spine bone.

Run:
  tools/blender.sh raw_assets/augments/passives/pc3_power_cell/build.py \\
      --out assets/augments/passives/pc3_power_cell/pc3_power_cell.gltf --preview docs/previews/pc3_power_cell
"""
import math
import os
import sys

import bpy
import bmesh

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "pc3"
body = C.body_once()

SHELL = C.mat_metal("pc3_shell", base=(0.32, 0.33, 0.34), rough=0.26, wear=(0.6, 0.6, 0.62), brushed=0.1)
CRADLE = C.mat_metal("pc3_cradle", base=(0.05, 0.052, 0.056), rough=0.36, wear=(0.42, 0.42, 0.44), brushed=0.04)
YELLOW = hs.material("pc3_yellow", (0.85, 0.52, 0.015), 0.48, 0.0, wear=(0.3, 0.3, 0.3), wear_rough=0.6)
BLACK = hs.material("pc3_black", (0.015, 0.015, 0.016), 0.5, 0.0)
GLOW = C.mat_glow("pc3_tritium", color=(0.42, 1.0, 0.3), strength=4.0)
HOSE = hs.material("pc3_conduit", (0.04, 0.04, 0.042), 0.4, 0.7, bump_scale=3000.0, bump_strength=0.5)
PAINT = C.mat_paint("pc3_stencil", (0.08, 0.08, 0.08), rough=0.6)
PAINT_W = C.mat_paint("pc3_stencil_w", (0.72, 0.7, 0.64))
MATS = [SHELL, CRADLE, YELLOW, BLACK, GLOW, HOSE, PAINT, PAINT_W]


def trefoil(name, c, n, up, r):
    """The radiation trefoil: three 60° blades and a dot, flat on the surface (HIGH)."""
    n = V(n).normalized()
    u = (V(up) - n * V(up).dot(n)).normalized()
    w = u.cross(n)
    bm = bmesh.new()
    for k in range(3):
        a0 = math.radians(90 + 120 * k - 30)
        pts = []
        for j in range(7):
            a = a0 + math.radians(60) * j / 6
            pts.append((math.cos(a) * r, math.sin(a) * r))
        for j in range(6, -1, -1):
            a = a0 + math.radians(60) * j / 6
            pts.append((math.cos(a) * r * 0.3, math.sin(a) * r * 0.3))
        bm.faces.new([bm.verts.new(c + w * x + u * y) for x, y in pts])
    ring = [bm.verts.new(c + w * math.cos(t) * r * 0.2 + u * math.sin(t) * r * 0.2) for t in [k * math.pi / 8 for k in range(16)]]
    bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.dot(n) < 0:
            f.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=n * 0.0004)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return C.setmat(ob, BLACK)


hi_l, lo_l = [], []
ANG, Z0, Z1 = 32.0, 1.13, 1.235
d = V((math.cos(math.radians(ANG)), math.sin(math.radians(ANG)), 0.0))
zm = (Z0 + Z1) / 2
hit, _n = body.cast(V((0, 0, zm)) + d * 0.4, -d, ("suit",), 0.5)
lift = max(((body.cast(V((0, 0, z)) + d * 0.4, -d, ("suit",), 0.5)[0] or hit) - V((0, 0, z))).dot(d) for z in (Z0, zm, Z1))
R = 0.021
axis_c = V((0, 0, 0)) + d * (lift + 0.006 + R)
side = V((0, 0, 1)).cross(d).normalized()
p0, p1 = V((axis_c.x, axis_c.y, Z0)), V((axis_c.x, axis_c.y, Z1))
Zv = V((0, 0, 1))
for det, lst in ((True, hi_l), (False, lo_l)):
    # Cradle: a conformal back plate with two clamp bands.
    if det:
        hp, lp = C.plate("cradle", body, C.chamfer_rect(0.036, 0.07, 0.01), (V((0, 0, zm)) + d * 0.5, side, Zv), -d, 0.002, 0.004,
                         facet_deg=8.0, smooth_r=0.015, bevel=0.0012)
        C.setmat(hp, CRADLE)
        C.setmat(lp, CRADLE)
        hi_l.append(hp)
        lo_l.append(lp)
    lst.append(C.cyl("cell", p0, p1, R, SHELL, det, 32, 0.0012))
    for e, (pa, sgn) in enumerate(((p0, -1), (p1, 1))):
        lst.append(C.cyl("cap", pa - Zv * sgn * 0.002, pa + Zv * sgn * 0.012, R * 1.08, CRADLE, det, 32, 0.0012))
        if det:
            for k in range(24):
                a = k * 2 * math.pi / 24
                q = pa + Zv * sgn * 0.005 + (d * math.cos(a) + side * math.sin(a)) * R * 1.08
                lst.append(C.slab("knurl", q, (Zv, side * math.cos(a) - d * math.sin(a), d * math.cos(a) + side * math.sin(a)),
                                  (0.009, 0.0016, 0.0012), CRADLE, False))
    lst.append(C.cyl("band_y", p1 - Zv * 0.026, p1 - Zv * 0.004, R * 1.012, YELLOW, det, 32, 0.0))
    for z in (Z0 + 0.03, Z1 - 0.035):
        c = V((axis_c.x, axis_c.y, z))
        lst.append(C.cyl("clamp", c - Zv * 0.004, c + Zv * 0.004, R * 1.14, CRADLE, det, 32, 0.0008))
        lst.append(C.slab("clamp_foot", c - d * (R + 0.002), (Zv, side, d), (0.008, R * 2.8, 0.008), CRADLE, det, 0.0008))
    # Tritium window down the outer face.
    win_c = (p0 + p1) * 0.5 - Zv * 0.012 + d * (R + 0.0004)
    lst.append(C.slab("window_frame", win_c, (Zv, side, d), (0.05, 0.012, 0.0016), CRADLE, det, 0.0005))
    lst.append(C.slab("window", win_c + d * 0.0008, (Zv, side, d), (0.044, 0.0068, 0.0012), GLOW, False))
    # Conduit from the top cap into the ribs.
    top = p1 + Zv * 0.012
    rib, _n = body.cast(V((0, 0, Z1 + 0.06)) + d.lerp(V((0, 1, 0)), 0.4).normalized() * 0.4,
                        -d.lerp(V((0, 1, 0)), 0.4).normalized(), ("suit",), 0.5)
    rib = rib if rib is not None else top + Zv * 0.05
    lst.append(C.cable("conduit", [top, top + Zv * 0.02 + d * 0.005, rib + d * 0.004], 0.0045, HOSE, det))
    lst.append(C.cyl("gland", rib - d * 0.002, rib + d * 0.008, 0.0075, CRADLE, det, 16, 0.0006))
if True:
    n_out = d
    tc = p1 - Zv * 0.015 + n_out * (R * 1.012 + 0.0002)
    hi_l.append(trefoil("trefoil", tc, n_out, Zv, 0.0082))
    for txt, z, mat, size in (("H-3  BETAVOLTAIC", -0.003, PAINT_W, 0.0046), ("200 W", -0.042, PAINT_W, 0.006)):
        st = C.stencil("st", txt, (p0 + p1) * 0.5 + Zv * z + n_out * (R + 0.0003) + side * 0.0115, n_out, Zv, size, mat)
        st.rotation_euler = (0, 0, 0)
        hi_l.append(C.apply_all(st))
C.add_piece("cell", "spine", C.join(hi_l, "pc3_high"), C.join(lo_l, "pc3_low"))

cc = (p0 + p1) * 0.5
C.run("pc3_power_cell", args, MATS, (
    ("front", (2.4, -3.8, 1.3), (0, 0, 1.15), 85),
    ("cell", cc + d * 0.42 + V((0, -0.08, 0.06)), cc, 60),
    ("cell_top", cc + d * 0.3 + V((0, 0.12, 0.2)), cc + Zv * 0.02, 60)))
