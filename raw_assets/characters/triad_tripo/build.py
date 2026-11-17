"""A Tripo3D man (tripo_generate.py) made into a triad body: fitted to the triad rig, skinned, cut for
dismemberment and exported as one whole-body "garment" the game dresses a man in (docs/design.md §5.6b).

No Tripo rig: the skeleton is the triad's own (raw_assets/characters/triad/common.py), so every triad
clip (rifle stances, the walk and run, cover, the chop, the boss's brute moves, the execution) plays on
him unchanged, the hands land on the same gun grips and the damage zones and cut planes line up.

Steps (all in this script, about 2-4 minutes a man on 4 cores):
  0. (--make-master, once) Tripo's GLB (about 1.9M triangles, 4K maps) -> <id>/master.glb (60k, 2K maps),
     which is committed; the download isn't (.gitignore).
  1. Import master.glb, merge its UV-split vertices, collapse to --tris.
  2. Stand him up: feet on z = 0, facing -Y (the triad's front), the arm span on X, sized so his
     shoulders are at the rig's shoulder height (1.418 m on a 1.75 m man).
  3. Find his joints from the mesh (he stands in a T-pose): the arm line and the wrist (the narrowest
     part of the forearm), the leg slices at the rig's hip, knee and ankle heights, the torso's centre line.
  4. A source armature with the triad's bones on HIS joints; bone-heat weights (Blender's automatic
     weights) on him.
  5. Pose that armature onto the triad rig's rest pose (arms down into its A-pose, limbs stretched a few
     per cent to the rig's lengths; head, hands and fingers keep their size) and apply it: the mesh now
     fits the rig, and keeps the weights, which are the triad bones' names.
  6. Cut him at the triad's joints with flesh caps (the planes and rules of triad/build.py cut_specs and
     split_parts), so a head, an arm or a shin comes off with whatever he wears on it.
  7. Textures: Tripo's maps with every UV island padded (no dark seams), squeezed to u < 0.94; the
     strip at u > 0.95 carries the triad atlas's flesh-cap disc. basecolor 2K, normal and ORM 1K
     (Tripo gives no AO: R = 1; G roughness, B metal).
  8. Export assets/characters/triad_tripo/<id>/<id>.gltf: the triad armature, w_tp_<id> (the whole man)
     and w_tp_<id>__<part> (body, head, upper_arm_L, ... as EnemyBody.SEGMENT_ORDER), no materials.

Run:
  tools/blender.sh raw_assets/characters/triad_tripo/build.py -- <id> [--tris 12000] [--preview <png>]
"""
import argparse
import json
import math
import os
import sys
import time

import bpy  # noqa: F401  (first: the PyPI bpy module provides bmesh/mathutils)
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "triad"))
V = Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
argv = [a for a in argv if a != "--"]
ap = argparse.ArgumentParser()
ap.add_argument("id")
ap.add_argument("--tris", type=int, default=12000)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--preview", default="")
ap.add_argument("--out", default="")
ap.add_argument("--make-master", action="store_true",
                help="write <id>/master.glb (60k triangles, 2K maps) from Tripo's download and stop")
args = ap.parse_args(argv)
CID = args.id
# Tripo's download (1.9M triangles, 4K maps, ~65 MB) isn't committed; master.glb (made from it with
# --make-master) is, and is what the committed game assets were built from.
SRC = os.path.join(HERE, CID, "tripo", "model.glb") if args.make_master else os.path.join(HERE, CID, "master.glb")
OUT_DIR = args.out or os.path.join(ROOT, "assets", "characters", "triad_tripo", CID)
T0 = time.time()


def log(*a):
    print(f"[tripo {CID} {time.time() - T0:6.1f}s]", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
import common  # noqa: E402
common.init()
from common import J as JT, BONES as BT, GRIP_R  # noqa: E402
COL = common.COL
scene = bpy.context.scene


def select_only(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def verts(ob):
    n = len(ob.data.vertices)
    P = np.empty(n * 3)
    ob.data.vertices.foreach_get("co", P)
    return P.reshape(-1, 3)


def set_verts(ob, P):
    ob.data.vertices.foreach_set("co", P.reshape(-1))
    ob.data.update()


# ====================================================================== 1. import and reduce
bpy.ops.import_scene.gltf(filepath=SRC, merge_vertices=True)
meshes = [o for o in scene.objects if o.type == "MESH"]
for o in meshes:
    o.data.transform(o.matrix_world)
    o.parent = None
    o.matrix_world = Matrix.Identity(4)
for o in [o for o in scene.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)
if len(meshes) > 1:
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
MAN = bpy.context.view_layer.objects.active if len(meshes) > 1 else meshes[0]
MAN.name = f"w_tp_{CID}"
MAN.data.name = MAN.name
# Tripo's material: keep its images, drop the slots (the game has its own shader).
IMAGES = {}
for mat in MAN.data.materials:
    if not mat or not mat.node_tree:
        continue
    for node in mat.node_tree.nodes:
        if node.type != "BSDF_PRINCIPLED":
            continue

        def img_of(sock, depth=0):
            if not sock.is_linked or depth > 4:
                return None
            n = sock.links[0].from_node
            if n.type == "TEX_IMAGE":
                return n.image
            for s in n.inputs:
                im = img_of(s, depth + 1)
                if im:
                    return im
            return None
        for key, sock in (("base", "Base Color"), ("rough", "Roughness"), ("metal", "Metallic"), ("normal", "Normal")):
            im = img_of(node.inputs[sock])
            if im and key not in IMAGES:
                IMAGES[key] = im
log("images", {k: (v.name, tuple(v.size)) for k, v in IMAGES.items()})


def reduce(target):
    MAN.data.calc_loop_triangles()
    n0 = len(MAN.data.loop_triangles)
    select_only(MAN)
    mod = MAN.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = min(1.0, target / n0)
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    MAN.data.calc_loop_triangles()
    log(f"reduced {n0} -> {len(MAN.data.loop_triangles)} tris, {len(MAN.data.vertices)} verts")


if args.make_master:
    reduce(60000)
    for im in {id(v): v for v in IMAGES.values()}.values():
        if im.size[0] > 2048:
            im.scale(2048, 2048)
    select_only(MAN)
    dst = os.path.join(HERE, CID, "master.glb")
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", use_selection=True, export_image_format="AUTO",
                              export_jpeg_quality=90, export_animations=False)
    log("master", dst, f"{os.path.getsize(dst) / 1e6:.1f} MB")
    sys.exit(0)
reduce(args.tris)
MAN.data.materials.clear()

# ====================================================================== 2. stand him up
P = verts(MAN)
ext = P.max(0) - P.min(0)
if ext[1] > ext[0]:  # arm span along Y: turn it onto X
    P = P[:, [1, 0, 2]] * np.array([-1.0, 1.0, 1.0])
P[:, 2] -= P[:, 2].min()
H = P[:, 2].max()
P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2
sole = P[P[:, 2] < 0.035 * H]
ank = P[(P[:, 2] > 0.09 * H) & (P[:, 2] < 0.14 * H) & (np.abs(P[:, 0]) < 0.2 * H)]
P[:, 1] -= ank[:, 1].mean()
if sole[:, 1].mean() > ank[:, 1].mean():  # toes toward +Y: turn him round to face -Y
    P[:, 0] *= -1.0
    P[:, 1] *= -1.0
log(f"height {H:.3f} (Tripo units)")


def chest_half_width(P, lo, hi):
    """The torso's half width in a height band: out from the middle to the first gap of 2.5 cm in |x|
    (arms that droop a little pass through the band further out)."""
    s = P[(P[:, 2] > lo) & (P[:, 2] < hi)]
    xs = np.sort(np.abs(s[:, 0]))
    gaps = np.nonzero(np.diff(xs) > 0.025 * (P[:, 2].max() / 1.8))[0]
    return float(xs[gaps[0]]) if len(gaps) else float(np.percentile(xs, 99.0))


def shoulder_height(P, H):
    xt = chest_half_width(P, 0.62 * H, 0.70 * H)
    a = P[(np.abs(P[:, 0]) > xt + 0.03 * H) & (np.abs(P[:, 0]) < xt + 0.09 * H) & (P[:, 2] > 0.65 * H)]
    return float(np.median(a[:, 2]))


sz = shoulder_height(P, H)
k = JT["shoulder.L"].z / sz
P *= k
H *= k
set_verts(MAN, P)
log(f"scaled x{k:.3f}: top of head {H:.3f} m, shoulders {sz * k:.3f} m")


# ====================================================================== 3. his joints
def slice_mean(Q, lo, hi, axis=2):
    s = Q[(Q[:, axis] > lo) & (Q[:, axis] < hi)]
    return s.mean(0) if len(s) else None


def find_joints(P):
    Jd = {}
    sh_z = JT["shoulder.L"].z
    xt = chest_half_width(P, 1.12, 1.28)
    # Heights of the leg joints: the rig's own (he is scaled to its shoulder height). Finding the crotch
    # from the mesh failed: thighs touch (in jeans down to 0.66 m), so the middle line has surface to the
    # knees. Where each joint sits across and front to back comes from his own leg slices.
    hip_z, knee_z, ankle_z = JT["hip.L"].z, JT["knee.L"].z, 0.09
    crotch = hip_z - 0.06
    log(f"chest half-width {xt:.3f}, hip {hip_z:.3f}, knee {knee_z:.3f}")
    torso = P[np.abs(P[:, 0]) < xt * 0.8]

    def mid_y(z, half=0.02, src=torso):
        m = slice_mean(src, z - half, z + half)
        return float(m[1]) if m is not None else 0.0
    neck_z = sh_z + (JT["neck"].z - JT["shoulder.L"].z)
    head_z = neck_z + (JT["head"].z - JT["neck"].z)
    hips_z = hip_z + (JT["hips"].z - JT["hip.L"].z)
    span = neck_z - hips_z
    rs = (JT["spine"].z - JT["hips"].z) / (JT["neck"].z - JT["hips"].z)
    rc = (JT["chest"].z - JT["hips"].z) / (JT["neck"].z - JT["hips"].z)
    headp = P[np.abs(P[:, 0]) < 0.11]
    Jd["root"] = V((0, 0, 0))
    Jd["hips"] = V((0, mid_y(hips_z), hips_z))
    Jd["spine"] = V((0, mid_y(hips_z + span * rs), hips_z + span * rs))
    Jd["chest"] = V((0, mid_y(hips_z + span * rc), hips_z + span * rc))
    Jd["neck"] = V((0, mid_y(neck_z, 0.02, headp), neck_z))
    Jd["head"] = V((0, mid_y(head_z, 0.02, headp), head_z))
    Jd["head_end"] = V((0, Jd["head"].y, float(P[:, 2].max())))
    Jd["chest_tail"] = V((0, Jd["chest"].y, neck_z - 0.022))
    for s, sx in (("L", 1.0), ("R", -1.0)):
        A = P[(P[:, 0] * sx > xt + 0.04) & (P[:, 2] > 1.05)]
        c = A.mean(0)
        _, _, vt = np.linalg.svd(A - c, full_matrices=False)
        d = vt[0] if vt[0][0] * sx > 0 else -vt[0]
        t = (A - c) @ d
        tip_t = float(t.max())
        perp = np.linalg.norm((A - c) - np.outer(t, d), axis=1)

        def centre(tt, half=0.02):
            m = np.abs(t - tt) < half
            return V(A[m].mean(0)) if m.any() else V(c + d * tt)
        # The wrist: the narrowest band 16-22 cm in from the fingertips (a hand is about 19 cm; a flat
        # T-pose hand is thinner than the wrist seen edge-on, so don't look inside it).
        best, wt = 1e9, tip_t - 0.19
        for tt in np.arange(tip_t - 0.22, tip_t - 0.155, 0.005):
            m = np.abs(t - tt) < 0.01
            if m.sum() < 6:
                continue
            r = float(np.median(perp[m]))
            if r < best:
                best, wt = r, float(tt)
        # The shoulder: on the arm line just inside the chest's edge.
        # Loose shirts and puffy jackets stand out past the body: a shoulder joint is never more than 23 cm out.
        st = (sx * min(xt - 0.025, 0.23) - c[0]) / d[0]
        sh = V(c + d * st)
        wr = centre(wt)
        el = centre(st + (wt - st) * (JT["elbow.L"] - JT["shoulder.L"]).length
                    / ((JT["elbow.L"] - JT["shoulder.L"]).length + (JT["wrist.L"] - JT["elbow.L"]).length))
        dv = V(d)
        Jd[f"clav.{s}"] = V((sx * 0.025, Jd["chest"].y, sh.z + 0.007))
        Jd[f"shoulder.{s}"] = sh
        Jd[f"elbow.{s}"] = el
        Jd[f"wrist.{s}"] = wr
        Jd[f"knuckle.{s}"] = wr + dv * 0.088
        Jd[f"tip.{s}"] = wr + dv * max(0.15, tip_t - wt)
        L = P[(P[:, 0] * sx > 0.005) & (P[:, 2] < crotch)]
        hp = slice_mean(L, crotch - 0.07, crotch - 0.03)
        kn = slice_mean(L, knee_z - 0.025, knee_z + 0.025)
        an = slice_mean(L, ankle_z - 0.02, ankle_z + 0.03)
        Jd[f"hip.{s}"] = V((hp[0], hp[1], hip_z))
        Jd[f"knee.{s}"] = V((kn[0], kn[1], knee_z))
        Jd[f"ankle.{s}"] = V((an[0], an[1], ankle_z))
        so = L[L[:, 2] < 0.035]
        heel, toe = float(so[:, 1].max()), float(so[:, 1].min())
        Jd[f"ball.{s}"] = V((float(so[:, 0].mean()), heel + (toe - heel) * 0.72, 0.022))
        log(f"{s}: shoulder {tuple(round(x, 3) for x in sh)} wrist {tuple(round(x, 3) for x in wr)} "
            f"(radius {best:.3f}) hand {tip_t - wt:.3f} knee {tuple(round(x, 3) for x in Jd[f'knee.{s}'])}")
    return Jd


JS = find_joints(P)


def bone_list(Jd, chest_tail, t_pose):
    B = [("root", V((0, 0, 0)), V((0, -0.2, 0)), None, V((0, 0, 1))),
         ("hips", Jd["hips"], Jd["spine"], "root", V((0, -1, 0))),
         ("spine", Jd["spine"], Jd["chest"], "hips", V((0, -1, 0))),
         ("chest", Jd["chest"], chest_tail, "spine", V((0, -1, 0))),
         ("neck", Jd["neck"], Jd["head"], "chest", V((0, -1, 0))),
         ("head", Jd["head"], Jd["head_end"], "neck", V((0, -1, 0)))]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        # The hand's Z is the back of the hand: outward in the rig's A-pose, up in the T-pose (palms down).
        hand_roll = V((0, 0, 1)) if t_pose else V((sx, 0, 0))
        B += [(f"clavicle.{s}", Jd[f"clav.{s}"], Jd[f"shoulder.{s}"], "chest", V((0, -1, 0))),
              (f"upper_arm.{s}", Jd[f"shoulder.{s}"], Jd[f"elbow.{s}"], f"clavicle.{s}", V((0, -1, 0))),
              (f"forearm.{s}", Jd[f"elbow.{s}"], Jd[f"wrist.{s}"], f"upper_arm.{s}", V((0, -1, 0))),
              (f"hand.{s}", Jd[f"wrist.{s}"], Jd[f"knuckle.{s}"], f"forearm.{s}", hand_roll),
              (f"fingers.{s}", Jd[f"knuckle.{s}"], Jd[f"tip.{s}"], f"hand.{s}", hand_roll),
              (f"thigh.{s}", Jd[f"hip.{s}"], Jd[f"knee.{s}"], "hips", V((0, -1, 0))),
              (f"shin.{s}", Jd[f"knee.{s}"], Jd[f"ankle.{s}"], f"thigh.{s}", V((0, -1, 0))),
              (f"foot.{s}", Jd[f"ankle.{s}"], Jd[f"ball.{s}"], f"shin.{s}", V((0, 0, 1)))]
    return B


def build_armature(name, bones, weapon):
    ad = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, ad)
    COL.objects.link(arm)
    select_only(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ad.edit_bones
    for bn, head, tail, parent, roll in bones:
        b = eb.new(bn)
        b.head, b.tail = head, tail
        b.align_roll(roll)
        if parent:
            b.parent = eb[parent]
            b.use_connect = False
    if weapon:  # as triad/build.py make_armature: the gun socket in the right hand at rest
        hand = eb["hand.R"]
        gun = hand.matrix.copy() @ GRIP_R.inverted()
        w = eb.new("weapon")
        w.head = gun.translation
        w.tail = gun.translation + gun.to_3x3() @ V((0.12, 0, 0))
        w.align_roll(gun.to_3x3() @ V((0, 0, 1)))
        w.parent = hand
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


# ====================================================================== 4. weights on his own joints
SRC_ARM = build_armature("src_rig", bone_list(JS, JS["chest_tail"], True), False)
bpy.ops.object.select_all(action="DESELECT")
MAN.select_set(True)
SRC_ARM.select_set(True)
bpy.context.view_layer.objects.active = SRC_ARM
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
W = np.zeros(len(MAN.data.vertices))
for v in MAN.data.vertices:
    W[v.index] = sum(g.weight for g in v.groups)
log(f"bone heat: {int((W <= 1e-6).sum())} of {len(W)} vertices unweighted")
if (W <= 1e-6).any():
    # Bone heat leaves islands it can't reach (a loose chain, an eyeball) empty: give each the weights of
    # the nearest weighted vertex.
    from mathutils.kdtree import KDTree
    good = np.nonzero(W > 1e-6)[0]
    kd = KDTree(len(good))
    for i, gi in enumerate(good):
        kd.insert(MAN.data.vertices[gi].co, i)
    kd.balance()
    vgs = MAN.vertex_groups
    for vi in np.nonzero(W <= 1e-6)[0]:
        _, i, _ = kd.find(MAN.data.vertices[vi].co)
        for g in MAN.data.vertices[good[i]].groups:
            vgs[g.group].add([int(vi)], g.weight, "REPLACE")

# ====================================================================== 5. onto the rig's rest pose
TGT_ARM = build_armature("triad_rig", BT, True)
REST = {b.name: b.matrix_local.copy() for b in TGT_ARM.data.bones}
KEEP_SIZE = {"head", "neck", "hand.L", "hand.R", "fingers.L", "fingers.R", "root"}
for b in SRC_ARM.data.bones:
    b.inherit_scale = "NONE"
select_only(SRC_ARM)
bpy.ops.object.mode_set(mode="POSE")
for pb in SRC_ARM.pose.bones:
    pb.rotation_mode = "QUATERNION"


def depth(b):
    return 0 if b.parent is None else 1 + depth(b.parent)


err = 0.0
for pb in sorted(SRC_ARM.pose.bones, key=lambda p: depth(p.bone)):
    ls = pb.bone.length
    lt = TGT_ARM.data.bones[pb.name].length
    kk = 1.0 if pb.name in KEEP_SIZE else lt / ls
    pb.matrix = REST[pb.name] @ Matrix.Diagonal((1.0, kk, 1.0, 1.0))
    bpy.context.view_layer.update()
for pb in SRC_ARM.pose.bones:
    err = max(err, (pb.matrix.translation - REST[pb.name].translation).length)
bpy.ops.object.mode_set(mode="OBJECT")
log(f"posed onto the rig (joint error {err * 1000:.2f} mm)")
select_only(MAN)
for m in MAN.modifiers:
    if m.type == "ARMATURE":
        bpy.ops.object.modifier_apply(modifier=m.name)
MAN.parent = None
MAN.matrix_parent_inverse = Matrix.Identity(4)
bpy.data.objects.remove(SRC_ARM, do_unlink=True)
bpy.context.view_layer.objects.active = MAN
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
for bn in [b.name for b in TGT_ARM.data.bones]:
    if bn not in MAN.vertex_groups:
        MAN.vertex_groups.new(name=bn)


def bind(ob):
    ob.parent = TGT_ARM
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = TGT_ARM


bind(MAN)
MAN.data.shade_smooth()

# ====================================================================== 7. textures (before the cut: the parts copy these UVs)
CAP_UV = (0.975, 0.05, 0.022)  # flesh-cap disc in the strip u > 0.95 (as triad/build.py)
U_SCALE = 0.94
uv = MAN.data.uv_layers.active.data
UV = np.empty(len(uv) * 2)
uv.foreach_get("uv", UV)
UV = UV.reshape(-1, 2)
UV[:, 0] = np.clip(UV[:, 0], 0.0, 1.0) * U_SCALE
uv.foreach_set("uv", UV.reshape(-1))


def img_np(im):
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1]  # rows top-down, like the PNG


def coverage(h, w):
    """Texels any triangle covers, from the (unscaled) UVs."""
    from PIL import Image, ImageDraw
    m = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(m)
    me = MAN.data
    for tri in me.loop_triangles:
        pts = [(UV[li, 0] / U_SCALE * w, (1.0 - UV[li, 1]) * h) for li in tri.loops]
        dr.polygon(pts, fill=255)
    return np.array(m) > 0


def pad(arr, cov):
    from scipy import ndimage
    _, idx = ndimage.distance_transform_edt(~cov, return_indices=True)
    return arr[idx[0], idx[1]]


def squeeze(arr, size):
    """Into u < 0.94 of a size x size map (the flesh strip goes in the rest)."""
    from PIL import Image
    out = np.zeros((size, size, arr.shape[2]), dtype=np.float32)
    w = int(round(size * U_SCALE))
    im = Image.fromarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8))
    out[:, :w] = np.asarray(im.resize((w, size), Image.LANCZOS), dtype=np.float32) / 255.0
    return out


def strip_from(path, size, out):
    from PIL import Image
    im = Image.open(os.path.join(ROOT, path)).convert("RGB")
    W0, H0 = im.size
    x0 = int(W0 * 0.95)
    s = im.crop((x0, 0, W0, H0)).resize((size - int(size * 0.95), size), Image.LANCZOS)
    out[:, int(size * 0.95):, :3] = np.asarray(s, dtype=np.float32) / 255.0


def save(arr, path, mode="RGB"):
    from PIL import Image
    ch = 3 if mode == "RGB" else 4
    Image.fromarray(np.clip(arr[:, :, :ch] * 255.0 + 0.5, 0, 255).astype(np.uint8), mode).save(path, optimize=True)


MAN.data.calc_loop_triangles()
os.makedirs(OUT_DIR, exist_ok=True)
base = img_np(IMAGES["base"])
cov = coverage(base.shape[0], base.shape[1])
log(f"texture {base.shape[1]}x{base.shape[0]}: islands cover {cov.mean() * 100:.0f} %")
B = squeeze(pad(base, cov), args.tex)
strip_from("assets/characters/triad/textures/triad_basecolor.png", args.tex, B)
save(B, os.path.join(OUT_DIR, f"{CID}_basecolor.png"))
small = args.tex // 2
if "normal" in IMAGES:
    nrm = img_np(IMAGES["normal"])
    nc = coverage(nrm.shape[0], nrm.shape[1])
    N = squeeze(pad(nrm, nc), small)
else:
    N = np.zeros((small, small, 4), np.float32)
    N[:, :, :3] = (0.5, 0.5, 1.0)
strip_from("assets/characters/triad/textures/triad_normal.png", small, N)
save(N, os.path.join(OUT_DIR, f"{CID}_normal.png"))
# glTF metallicRoughness: G roughness, B metal (one image, or one each).
rough = img_np(IMAGES["rough"]) if "rough" in IMAGES else None
metal = img_np(IMAGES["metal"]) if "metal" in IMAGES else None
ref = rough if rough is not None else (metal if metal is not None else None)
if ref is not None:
    oc = coverage(ref.shape[0], ref.shape[1])
    O = np.ones(ref.shape, np.float32)
    O[:, :, 1] = rough[:, :, 1] if rough is not None else 0.8
    O[:, :, 2] = metal[:, :, 2] if metal is not None else 0.0
    O = squeeze(pad(O, oc), small)
else:
    O = np.ones((small, small, 4), np.float32)
    O[:, :, 1], O[:, :, 2] = 0.8, 0.0
O[:, :, 0] = 1.0
strip_from("assets/characters/triad/textures/triad_orm.png", small, O)
save(O, os.path.join(OUT_DIR, f"{CID}_orm.png"))
log("textures saved:", sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".png")))


# ====================================================================== 6. dismemberment cuts
def cut_specs():
    """triad/build.py cut_specs(), unchanged: every place the body comes apart, deepest parts first."""
    J = JT
    specs = [("head", V((0, 0.006, 1.525)), V((0, 0, 1)), V((0, 0.006, 1.62)), 0.17, 0.32, 0.17, "body",
              ("head", "neck"))]
    for s in ("L", "R"):
        arm = (f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}", f"fingers.{s}")
        leg = (f"thigh.{s}", f"shin.{s}", f"foot.{s}")
        sh, e, w, kn = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"], J[f"knuckle.{s}"]
        dw = (kn - w).normalized()
        specs.append((f"hand_{s}", w - dw * 0.012, dw, w - dw * 0.012, 0.075, 0.24, 0.1, f"forearm_{s}", arm))
        d = (w - e).normalized()
        c = e + (w - e) * 0.35
        specs.append((f"forearm_{s}", c, d, c, 0.12, 0.42, 0.16, f"upper_arm_{s}", arm))
        du = (e - sh).normalized()
        c = sh + (e - sh) * 0.6
        specs.append((f"upper_arm_{s}", c, du, c, 0.095, 0.3, 0.11, "body", arm))
        k, a = J[f"knee.{s}"], J[f"ankle.{s}"]
        d = (a - k).normalized()
        c = k + (a - k) * 0.3
        specs.append((f"shin_{s}", c, d, c, 0.13, 0.55, 0.16, f"thigh_{s}", leg))
        hp = J[f"hip.{s}"]
        dt = (k - hp).normalized()
        c = hp + (k - hp) * 0.65
        specs.append((f"thigh_{s}", c, dt, c, 0.12, 0.5, 0.14, "body", leg))
    return specs


def dominant_bones(bm, src):
    dl = bm.verts.layers.deform.active
    names = [vg.name for vg in src.vertex_groups]
    out = {}
    for f in bm.faces:
        acc = {}
        for v in f.verts:
            for gi, wt in v[dl].items():
                acc[gi] = acc.get(gi, 0.0) + wt
        out[f.index] = names[max(acc, key=acc.get)] if acc else ""
    return out


def cut_ring(bm, co, no, radius, prad, keep_face=None):
    """Faces the plane passes through that ring this limb (triad/build.py _cut_ring), only those
    `keep_face` accepts (legs: their own side)."""
    def side(v):
        return (v.co - co).dot(no)

    def perp(p):
        d = p - co
        return (d - no * d.dot(no)).length
    cand = set()
    for f in bm.faces:
        ds = [side(v) for v in f.verts]
        if min(ds) < 0 < max(ds) and (f.calc_center_median() - co).length < radius * 1.6 and (keep_face is None or keep_face(f)):
            cand.add(f)
    rings, left = [], set(cand)
    while left:
        f0 = left.pop()
        band, stack = [f0], [f0]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in left:
                        left.discard(g)
                        band.append(g)
                        stack.append(g)
        rings.append(band)
    keep = []
    for band in rings:
        mp = max(perp(v.co) for f in band for v in f.verts)
        if mp < prad * 1.5:
            keep += band
    return keep


def split_parts(src, prefix):
    bm = bmesh.new()
    bm.from_mesh(src.data)
    specs = cut_specs()
    cut_edges = []
    # Baggy trousers fuse the legs where they touch (Tripo makes one surface): split that contact down
    # the middle line below the crotch first, so each leg's thigh and shin rings close on their own.
    web = [f for f in bm.faces if f.calc_center_median().z < 0.75
           and min(v.co.x for v in f.verts) < 0.0 < max(v.co.x for v in f.verts)]
    if web:
        res = bmesh.ops.bisect_plane(bm, geom=list({v for f in web for v in f.verts}) + list({e for f in web for e in f.edges}) + web,
                                     dist=1e-6, plane_co=V((0, 0, 0)), plane_no=V((1, 0, 0)))
        cut_edges += [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
        log(f"  legs touch: split {len(web)} faces between them")
    for name, co, no, centre, radius, reach, prad, parent, bones in specs:
        # Legs: only faces on the leg's own side (thighs in trousers touch, and a plane across one thigh
        # would take the other's band too). Arms need no filter. The neck ring runs through collars and
        # bunched hoods: any band round the neck, however wide, so the head comes off with the hood.
        side = 1.0 if name.endswith("_L") else -1.0
        legs = name.startswith(("thigh", "shin"))
        ring = cut_ring(bm, co, no, radius, 0.4 if name == "head" else prad,
                        (lambda f, sd=side: f.calc_center_median().x * sd > 0.0) if legs else None)
        vs = list({v for f in ring for v in f.verts})
        es = list({e for f in ring for e in f.edges})
        res = bmesh.ops.bisect_plane(bm, geom=vs + es + ring, dist=1e-6, plane_co=co, plane_no=no)
        cut_edges += [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
    bmesh.ops.split_edges(bm, edges=list(set(cut_edges)))
    bm.faces.index_update()
    dom = dominant_bones(bm, src)

    def part_of(f):
        c = f.calc_center_median()
        for name, co, no, centre, radius, reach, prad, parent, bones in specs:
            if dom.get(f.index, "") not in bones:
                continue
            along = (c - co).dot(no)
            if 0 < along < reach and ((c - co) - no * along).length < prad * 1.5:
                return name
        return "body"
    owner, seen = {}, set()
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        island, stack = [], [f0]
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            island.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        votes = {}
        for f in island:
            kk = part_of(f)
            votes[kk] = votes.get(kk, 0.0) + f.calc_area()
        win = max(votes, key=votes.get)
        for f in island:
            owner[f.index] = win
    parts = {}
    for part in ["body"] + [sp[0] for sp in specs]:
        b2 = bm.copy()
        b2.faces.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if owner[f.index] != part], context="FACES")
        if not b2.faces:
            b2.free()
            log(f"  WARNING: no faces for {part}")
            continue
        uvl = b2.loops.layers.uv.active
        for name, co, no, centre, radius, reach, prad, parent, bones in specs:
            if part not in (parent, name):
                continue
            edges = [e for e in b2.edges if e.is_boundary and all(abs((v.co - co).dot(no)) < 2e-4 for v in e.verts)
                     and (e.verts[0].co - centre).length < radius * 1.6]
            if not edges:
                log(f"  WARNING: no cap edges for cut {name} on {part}")
                continue
            faces = bmesh.ops.holes_fill(b2, edges=edges, sides=0)["faces"]
            if not faces:
                # An open rim (legs split where they touched): a fan from its middle covers the hole.
                mid = sum((v.co for e in edges for v in e.verts), V((0, 0, 0))) / (2 * len(edges))
                cv = b2.verts.new(mid)
                for e in edges:
                    a, b = e.verts
                    try:
                        faces.append(b2.faces.new((a, b, cv)))
                    except ValueError:
                        pass
                if faces:  # the middle vertex takes a rim vertex's weights (its UVs are set below)
                    dl = b2.verts.layers.deform.active
                    for gi, wt in edges[0].verts[0][dl].items():
                        cv[dl][gi] = wt
            if not faces:
                log(f"  WARNING: cap fill failed for cut {name} on {part}")
                continue
            ref = no.orthogonal().normalized()
            ref2 = no.cross(ref)
            pts = [v.co for f in faces for v in f.verts]
            c = sum(pts, V((0, 0, 0))) / len(pts)
            rmax = max((p - c).length for p in pts) or 0.05
            for f in faces:
                for loop in f.loops:
                    d = loop.vert.co - c
                    loop[uvl].uv = (CAP_UV[0] + d.dot(ref) / rmax * CAP_UV[2] * 0.95,
                                    CAP_UV[1] + d.dot(ref2) / rmax * CAP_UV[2] * 0.95)
                want = no if part == parent else -no
                f.normal_update()
                if f.normal.dot(want) < 0:
                    f.normal_flip()
        me = bpy.data.meshes.new(f"{prefix}{part}")
        b2.to_mesh(me)
        b2.free()
        ob = bpy.data.objects.new(f"{prefix}{part}", me)
        COL.objects.link(ob)
        for vg in src.vertex_groups:
            ob.vertex_groups.new(name=vg.name)
        me.shade_smooth()
        bind(ob)
        me.calc_loop_triangles()
        parts[part] = ob
        log(f"  {prefix}{part}: {len(me.loop_triangles)} tris")
    bm.free()
    return parts


log("cutting")
PARTS = split_parts(MAN, f"w_tp_{CID}__")


# ====================================================================== 8. export
def triangulate(ob):
    m = ob.modifiers.new("tri", "TRIANGULATE")
    m.keep_custom_normals = True
    select_only(ob)
    bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
    bpy.ops.object.modifier_apply(modifier=m.name)


objs = [MAN] + list(PARTS.values())
for ob in objs:
    triangulate(ob)
bpy.ops.object.select_all(action="DESELECT")
TGT_ARM.select_set(True)
for ob in objs:
    ob.select_set(True)
bpy.context.view_layer.objects.active = TGT_ARM
gltf = os.path.join(OUT_DIR, f"{CID}.gltf")
bpy.ops.export_scene.gltf(filepath=gltf, export_format="GLTF_SEPARATE", use_selection=True, export_apply=False,
                          export_skins=True, export_materials="NONE", export_tangents=True, export_animations=False)
g = json.load(open(gltf))
joints = [g["nodes"][j]["name"] for j in g["skins"][0]["joints"]]
ref = json.load(open(os.path.join(ROOT, "assets/characters/triad/triad.gltf")))
ref_joints = [ref["nodes"][j]["name"] for j in ref["skins"][0]["joints"]]
assert joints == ref_joints, f"joint order differs from triad.gltf: {joints} vs {ref_joints}"
log("exported", gltf, "(joint order matches triad.gltf)")
info = {"id": CID, "tris": len(MAN.data.loop_triangles), "joints_found": {k: [round(x, 4) for x in v] for k, v in JS.items()},
        "parts": sorted(PARTS)}
json.dump(info, open(os.path.join(HERE, CID, "build_info.json"), "w"), indent=1)

# ====================================================================== preview
if args.preview:
    from mathutils import Euler
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "CYCLES"
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 24
        scene.cycles.device = "CPU"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    mat = bpy.data.materials.new("prev")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(OUT_DIR, f"{CID}_basecolor.png"))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    for ob in objs:
        ob.data.materials.clear()
        ob.data.materials.append(mat)
    for ob in PARTS.values():
        ob.hide_render = True
    # Three copies side by side: front, three-quarter, side.
    MAN.hide_render = False
    copies = []
    for i, yaw in enumerate((0.0, 35.0, 90.0)):
        c = MAN.copy()
        c.data = MAN.data.copy()
        COL.objects.link(c)
        c.parent = None
        c.modifiers.clear()
        c.matrix_world = Matrix.Translation(V(((i - 1) * 1.1, 0, 0))) @ Euler((0, 0, math.radians(yaw))).to_matrix().to_4x4()
        copies.append(c)
    MAN.hide_render = True
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.36, 0.38, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    scene.world = w
    for loc, en in (((3, -4, 4), 400), ((-4, -2, 3), 200)):
        ld = bpy.data.lights.new("l", "AREA")
        ld.energy = en
        ld.size = 3
        lo = bpy.data.objects.new("l", ld)
        lo.location = loc
        lo.rotation_euler = (V((0, 0, 1)) - V(loc)).to_track_quat("-Z", "Y").to_euler()
        COL.objects.link(lo)
    cd = bpy.data.cameras.new("c")
    cd.lens = 50
    cam = bpy.data.objects.new("c", cd)
    cam.location = (0, -6.0, 1.0)
    cam.rotation_euler = (math.radians(88), 0, 0)
    COL.objects.link(cam)
    scene.camera = cam
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    log("preview", args.preview)
