"""KB-1 combat knife in the operative's right hand: the first-person model for the R3 strike (CLAUDE.md §9.4).

The gun drops out of view, this hand comes in from the lower right with the knife, slashes across and leaves
(PlayerMelee drives it procedurally; the model itself is static). Grounded hardware: a 17 cm clip-point blade,
black-coated with a bright steel grind and edge, a gunmetal guard and pommel, a dark rubber grip. The hand and
forearm are the GS-2 graft suit's (raw_assets/augments/actives/_kit.py), so the suit colours apply.

Pose: hammer grip, the handle across the palm under the knuckles, the blade out of the thumb side, the wrist
bent 30 degrees toward the little finger so the blade leans forward along the forearm. Edge on the finger side.

The origin is the centre of the handle (the game pivots the slash there). Empties `blade_base` and `blade_tip`
mark the edge for the motion trail. In Godot axes: the blade points along (0.5, 0, -0.866), the edge faces -Y.

Run:
  tools/blender.sh raw_assets/weapons/knife/build.py --out assets/weapons/knife/knife_fp.gltf \
      --preview docs/previews/knife_fp.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "augments", "actives"))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Matrix  # noqa: E402

args = K.init("kb1", 0, "0", views_default="fp,hero")
K.mat("blade_coat", (0.035, 0.036, 0.038), 0.42, 0.75)
K.mat("blade_steel", (0.62, 0.63, 0.65), 0.16, 1.0)
K.mat("knife_grip", (0.03, 0.032, 0.03), 0.78, 0.0)

YAW = -30.0                       # wrist bend toward the little finger (about +Z)
HX, HZ = 0.09, -0.034             # handle axis (along Y) in the hand's frame
Y_GUARD, Y_BLADE, Y_TIP = 0.050, 0.058, 0.235
Z_SPINE, Z_EDGE, Z_TIP = -0.021, -0.057, -0.033

# ---------------------------------------------------------------- forearm and hand
arm = K.part("forearm", K.forearm(side=1))
wrist, palm, fingers, tsegs = K.hand(side=1)
CURL = {"index": (54, 92, 62), "middle": (58, 92, 62), "ring": (62, 94, 62), "little": (66, 96, 64)}
for fname, segs in fingers.items():
    for seg, a in zip(segs, CURL[fname]):
        seg.rotation_euler = (0.0, math.radians(a), 0.0)
r0 = tsegs[0].rotation_euler
tsegs[0].rotation_euler = (r0[0] + math.radians(14), r0[1] + math.radians(10), r0[2] - math.radians(44))
tsegs[1].rotation_euler = (0.0, math.radians(38), 0.0)
tsegs[2].rotation_euler = (0.0, math.radians(30), 0.0)


# ---------------------------------------------------------------- the knife
def blade_mesh():
    """Lofted clip-point blade: spine flats coated, a saber grind and the edge in bright steel."""
    bm = bmesh.new()
    rings, mats = [], []
    n = 16
    for i in range(n + 1):
        t = i / n
        y = Y_BLADE + (Y_TIP - Y_BLADE) * t
        last = i == n
        u_clip = max(0.0, (y - 0.168) / (Y_TIP - 0.168))
        u_belly = max(0.0, (y - 0.150) / (Y_TIP - 0.150))
        zs = Z_SPINE + (Z_TIP - Z_SPINE) * u_clip ** 1.25
        ze = Z_EDGE + (Z_TIP - Z_EDGE) * u_belly ** 2.2
        zg = ze + 0.40 * (zs - ze)
        th = 0.0050 * (1.0 - 0.75 * max(0.0, (t - 0.55) / 0.45))
        if last:
            zs = ze = zg = Z_TIP
            th = 0.0003
        e = 0.0002
        pts = [(-th / 2, zs), (th / 2, zs), (th / 2, zg), (e, ze), (-e, ze), (-th / 2, zg)]
        rings.append([bm.verts.new((HX + x, y, z)) for x, z in pts])
    # faces: 0 spine, 1 right flat, 2 right grind, 3 edge, 4 left grind, 5 left flat
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(6):
            j = (k + 1) % 6
            bm.faces.new((a[k], a[j], b[j], b[k]))
            mats.append(1 if k in (2, 3, 4) else 0)
    bm.faces.new(rings[0][::-1])
    mats.append(0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = hs.mesh_object("blade", bm)
    K.piece(ob, "blade_coat", bevel=0.0, smooth=False)
    ob.data.materials.append(K.M["blade_steel"])
    for p, m in zip(ob.data.polygons, mats):
        p.material_index = m
    return ob


kp = [blade_mesh(),
      K.piece(hs.box("guard", (0.024, 0.008, 0.052), (HX, Y_GUARD + 0.004, HZ - 0.003)), "gunmetal", bevel=0.0018),
      K.piece(hs.cyl_y("grip", 0.0128, 0.096, (HX, 0.002, HZ), verts=20), "knife_grip", bevel=0.0012),
      K.piece(hs.cyl_y("pommel", 0.0118, 0.014, (HX, -0.053, HZ), verts=20), "gunmetal", bevel=0.0015),
      K.piece(hs.cyl_between("breaker", (HX, -0.06, HZ), (HX, -0.068, HZ), 0.007, verts=12, radius2=0.0025), "blade_steel", bevel=0.0)]
for y in (-0.03, -0.012, 0.006, 0.024):
    kp.append(K.piece(hs.cyl_y("grip_ring", 0.0134, 0.0028, (HX, y, HZ), verts=20), "knife_grip", bevel=0.0004))
knife = K.part("knife", kp, pivot=(HX, 0.0, HZ))
K.parent(knife, palm)
base = K.empty("blade_base", (HX, Y_BLADE + 0.01, (Z_SPINE + Z_EDGE) / 2))
tip = K.empty("blade_tip", (HX, Y_TIP, Z_TIP))
K.parent(base, palm)
K.parent(tip, palm)

# ---------------------------------------------------------------- the wrist and the origin
wrist.rotation_euler = (0.0, 0.0, math.radians(YAW))
root = K.empty("kb1_root")
K.parent(arm, root)
K.parent(wrist, root)
h = Matrix.Rotation(math.radians(YAW), 4, "Z") @ V((HX, 0.0, HZ))
root.location = -h
outer = K.empty("knife_fp")
K.parent(root, outer)

VIEWS = {
    # Roughly the game's view: the hand low right, blade toward the screen centre.
    "fp": ((-0.30, -0.30, 0.18), (0.25, 0.12, -0.02), 62),
    "hero": ((0.10, -0.42, 0.12), (0.0, 0.03, -0.01), 0),
}
print(f"kb1: {K.tri_count()} triangles")
if args.preview:
    K.render_previews(args.preview.rsplit(".", 1)[0], VIEWS, aim=(0.0, 0.0, 0.0))
if args.out:
    K.export(args.out, animated=False)
