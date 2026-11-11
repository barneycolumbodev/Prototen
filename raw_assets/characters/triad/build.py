"""Triad gunmen: the body, the wardrobe and the animation (CLAUDE.md §7, docs/design.md §5.6, §6).

Owner, 2026-11-11: "The enemies are really hard to see and they lack a lot of
detail... they need tattoos. They also need clothes they can wear that are
randomly selected from a bank." Rebuilt from the single bomber-jacket man:

- body.py: an athletic man without clothes (metaball torso and limbs,
  sculpted head, hands curled for a grip), HIGH with muscle definition baked
  into LOW's normal map. Skin everywhere a garment leaves bare.
- wardrobe.py: a bank of clothes, hair, hats and jewellery, each a shell
  over the body (cut along its hems as zero lines of a field, pushed out,
  smoothed, kept clear of the skin), weighted from the body under it.
- paint.py: skin, face and every garment painted per texel; cloth painted
  neutral grey so the game tints it per man (mask), with prints allowed
  where the mask says; a height per texel turned into the cloth normal map.
- tattoos.py: three sets of black-and-grey triad tattoos on the skin.
- Severable parts for dismemberment (head; upper arms, forearms, hands;
  thighs, shins: a cut at every joint, nested) are cut from the body AND
  from every garment with the same planes, so whatever a man wears comes
  off with the limb. Flesh caps close the body's cuts; a sleeve just ends.
- Animation clips are posed with IK (hands on the gun's grips, feet
  planted) and baked to FK keys per frame (unchanged).

One atlas: the body (and its tattoo/facial-hair map, triad_skin.png) in
u < 0.5, the wardrobe in 0.5 < u < 0.95, the flesh-cap disc in the strip.

Outputs (--out assets/characters/triad/triad.gltf):
  triad.gltf           armature, the body ("triad" + part_*), the plate
                       carrier ("vest"), animations
  triad_wardrobe.gltf  every garment (w_<id>) and its parts (w_<id>__<part>),
                       skinned to the same armature, no animations
  textures/triad_{basecolor,normal,orm,mask,skin}.png

Axes: Blender Z up, the man faces -Y (glTF/Godot +Z), his left is +X.
Every long gun is held at the same two points (raw_assets/weapons/enemy_guns).

Run (about 25 minutes at --tex 4096 on 4 cores):
  tools/blender.sh raw_assets/characters/triad/build.py --out assets/characters/triad/triad.gltf --tex 4096 \
      --preview docs/previews/triad
  Fast check (no bakes, flat textures): add --fast --tex 512
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--preview", default="", help="prefix for preview PNGs")
ap.add_argument("--fast", action="store_true", help="no bakes: flat material colours")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--ao-samples", type=int, default=16)
ap.add_argument("--guns", default="assets/weapons/enemy")
ap.add_argument("--no-anim", action="store_true")
ap.add_argument("--only", default="", help="comma-separated garment ids (default: the whole wardrobe)")
ap.add_argument("--split-preview", default="", help="exploded view of the severable parts (PNG path, no .png)")
ap.add_argument("--tattoo-sheet", default="", help="PNG of the tattoo designs")
args = ap.parse_args(argv)

T0 = time.time()


def log(*a):
    print(f"[triad {time.time() - T0:6.1f}s]", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

import common  # noqa: E402
common.init()
from common import (J, BONES, frame, GRIP_R, GRIP_L, GUN_TO_BONE, MATS, MAT, Family, apply_mod, decimate,  # noqa: E402
                    tris, duplicate, verts_np, regions)
import body  # noqa: E402
import wardrobe  # noqa: E402
COL = common.COL


def make_armature():
    arm_data = bpy.data.armatures.new("triad_rig")
    arm = bpy.data.objects.new("triad_rig", arm_data)
    COL.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for name, head, tail, parent, roll_vec in BONES:
        b = eb.new(name)
        b.head, b.tail = head, tail
        b.align_roll(roll_vec)
        if parent:
            b.parent = eb[parent]
            b.use_connect = False
    # Weapon socket: where the gun sits in the right hand at rest.
    hand = eb["hand.R"]
    hand_m = hand.matrix.copy()
    gun = hand_m @ GRIP_R.inverted()
    w = eb.new("weapon")
    w.head = gun.translation
    w.tail = gun.translation + gun.to_3x3() @ V((0.12, 0, 0))
    w.align_roll(gun.to_3x3() @ V((0, 0, 1)))
    w.parent = hand
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


ARM = make_armature()
REST = {b.name: b.matrix_local.copy() for b in ARM.data.bones}
REST_HAND = {s: REST[f"hand.{s}"] for s in ("L", "R")}
log("armature:", len(ARM.data.bones), "bones")


# ====================================================================== the body
def join(obs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    # Merge material slots by name (each part brought its own two).
    names = []
    remap = []
    for m in ob.data.materials:
        if m.name not in names:
            names.append(m.name)
        remap.append(names.index(m.name))
    idx = np.zeros(len(ob.data.polygons), dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", idx)
    idx = np.array(remap, dtype=np.int32)[idx]
    ob.data.materials.clear()
    for n in MATS:
        ob.data.materials.append(MAT[n])
    order = np.array([MATS.index(n) for n in names], dtype=np.int32)
    ob.data.polygons.foreach_set("material_index", order[idx])
    return ob


BODY_BUDGET = {"body_low": 4400, "head": 2000, "hand_L": 640, "hand_R": 640}


def build_person(hi):
    if hi:
        parts = [body.build_body(True)]
    else:
        parts = [duplicate(BASE, "body_low")]
    parts += [body.build_head(hi)] + body.build_eyes() + [body.build_hand("L", hi, REST), body.build_hand("R", hi, REST)]
    if not hi:
        for ob in parts:
            if ob.name in BODY_BUDGET:
                decimate(ob, BODY_BUDGET[ob.name])
    out = join(parts, "triad_high" if hi else "triad")
    out.data.shade_smooth()
    return out


log("building the body")
BASE = body.build_body(False)          # dense; garments are cut from it
BVH = BVHTree.FromObject(BASE, bpy.context.evaluated_depsgraph_get())
LOW = build_person(False)
log(f"LOW: {tris(LOW)} tris")
HIGH = None
if not args.fast:
    HIGH = build_person(True)
    log(f"HIGH: {tris(HIGH)} tris")

log("building the wardrobe")
GIDS = [g for g in wardrobe.GARMENTS if not args.only or g in args.only.split(",")]
GARMENTS = {}
for gid in GIDS:
    GARMENTS[gid] = wardrobe.build_garment(gid, BASE, BVH)
    log(f"  {gid}: {tris(GARMENTS[gid])} tris ({wardrobe.GARMENTS[gid][1]})")
VEST = wardrobe.build_vest()
decimate(VEST, 700)
bpy.data.objects.remove(BASE)


# ====================================================================== skin weights
BONE_NAMES = [b.name for b in ARM.data.bones]


def ss(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def chain_weights(P, joints, bones, blends):
    """Weights along a polyline of `joints` (bones: one before, one per segment, one after)."""
    joints = [np.array(j[:]) for j in joints]
    seg_len = [np.linalg.norm(joints[i + 1] - joints[i]) for i in range(len(joints) - 1)]
    best_d = np.full(len(P), np.inf)
    u = np.zeros(len(P))
    acc = 0.0
    for i in range(len(joints) - 1):
        a, b = joints[i], joints[i + 1]
        d = b - a
        L = seg_len[i]
        t = ((P - a) @ d) / (L * L)
        lo = -np.inf if i == 0 else 0.0
        hi = np.inf if i == len(joints) - 2 else 1.0
        tc = np.clip(t, lo, hi)
        q = a + tc[:, None] * d
        dist = np.linalg.norm(P - q, axis=1)
        m = dist < best_d
        best_d[m] = dist[m]
        u[m] = acc + tc[m] * L
        acc += L
    marks = np.cumsum([0.0] + seg_len)
    W = {}
    carry = np.ones(len(P))
    for k, (Lk, bk) in enumerate(zip(marks, blends)):
        f = ss((u - Lk + bk) / (2 * bk))
        W[bones[k]] = W.get(bones[k], 0) + carry * (1 - f)
        carry = carry * f
    W[bones[len(marks)]] = W.get(bones[len(marks)], 0) + carry
    return W


def compute_weights(ob, hand_labels=None):
    me = ob.data
    n = len(me.vertices)
    P = np.empty(n * 3)
    me.vertices.foreach_get("co", P)
    P = P.reshape(-1, 3)
    mat_v = np.zeros(n, dtype=np.int32)  # material of each vertex (first face seen)
    for poly in me.polygons:
        for vi in poly.vertices:
            mat_v[vi] = poly.material_index
    W = np.zeros((n, len(BONE_NAMES)))
    bi = {b: i for i, b in enumerate(BONE_NAMES)}

    def add(mask, wdict):
        for b, w in wdict.items():
            W[mask, bi[b]] += (w if np.ndim(w) == 0 else w[mask])

    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    mats = {m: MATS.index(m) for m in MATS}
    side_L = x > 0
    # Region: head, torso, arms (incl. hands), legs (incl. shoes).
    def seg_dist(p, a, b):
        a, b = np.array(a[:]), np.array(b[:])
        d = b - a
        t = np.clip(((p - a) @ d) / (d @ d), 0, 1)
        return np.linalg.norm(p - (a + t[:, None] * d), axis=1)

    arm_d = np.minimum.reduce([np.minimum(seg_dist(P, J[f"shoulder.{s}"], J[f"elbow.{s}"]),
                                          seg_dist(P, J[f"elbow.{s}"], J[f"tip.{s}"])) for s in ("L", "R")])
    torso_score = np.sqrt((x / 0.19) ** 2 + (y / 0.13) ** 2)
    arm_region = (arm_d / 0.068 < torso_score) & (z < 1.47) & (z > 0.75)
    head_region = ((mat_v == mats["skin"]) | (mat_v == mats["hair"]) | (mat_v == mats["eye"])) & (z > 1.43) & ~arm_region
    leg_d = np.minimum.reduce([seg_dist(P, J[f"hip.{s}"], J[f"ankle.{s}"]) for s in ("L", "R")])
    pelvis_score = np.sqrt((x / 0.17) ** 2 + (y / 0.12) ** 2)
    leg_region = ~arm_region & ~head_region & ((z < 0.86) | ((leg_d / 0.095 < pelvis_score) & (z < 0.97)))
    torso_region = ~arm_region & ~head_region & ~leg_region

    # Torso: hips -> spine -> chest -> neck by height, clavicles toward the shoulders.
    tw = chain_weights(P, [V((0, 0, 1.02)), V((0, 0, 1.245)), V((0, 0, 1.47))],
                       ["hips", "spine", "chest", "neck"], [0.05, 0.05, 0.03])
    clav = ss((np.abs(x) - 0.07) / 0.09) * ss((z - 1.3) / 0.1) * 0.65
    chest_w = tw["chest"]
    tw["chest"] = chest_w * (1 - clav)
    tw["clavicle.L"] = chest_w * clav * side_L
    tw["clavicle.R"] = chest_w * clav * ~side_L
    add(torso_region, tw)
    # Head and neck.
    add(head_region, chain_weights(P, [V((0, 0, 1.47)), V((0, 0, 1.575))], ["chest", "neck", "head"], [0.03, 0.022]))
    # Arms.
    for s, m in (("L", side_L), ("R", ~side_L)):
        mask = arm_region & m
        aw = chain_weights(P, [J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"]],
                           [f"clavicle.{s}", f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}"], [0.06, 0.045, 0.02])
        if hand_labels is not None:
            fing = hand_labels & mask
            aw[f"fingers.{s}"] = fing.astype(float) * aw[f"hand.{s}"]
            aw[f"hand.{s}"] = aw[f"hand.{s}"] * (~fing)
        add(mask, aw)
        lmask = leg_region & m
        add(lmask, chain_weights(P, [J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"]],
                                 ["hips", f"thigh.{s}", f"shin.{s}", f"foot.{s}"], [0.07, 0.05, 0.03]))
    # Eyes are rigid to the head.
    W[mat_v == mats["eye"]] = 0
    W[mat_v == mats["eye"], bi["head"]] = 1
    # Smooth over the mesh (fixes seams between regions), keep the four strongest.
    edges = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    eye = mat_v == mats["eye"]
    for _ in range(4):
        acc = np.zeros_like(W)
        cnt = np.zeros(n)
        np.add.at(acc, edges[:, 0], W[edges[:, 1]])
        np.add.at(acc, edges[:, 1], W[edges[:, 0]])
        np.add.at(cnt, edges[:, 0], 1)
        np.add.at(cnt, edges[:, 1], 1)
        Wn = np.where(cnt[:, None] > 0, 0.5 * W + 0.5 * acc / np.maximum(cnt, 1)[:, None], W)
        Wn[eye] = W[eye]
        W = Wn
    order = np.argsort(-W, axis=1)
    W2 = np.zeros_like(W)
    rows = np.arange(n)[:, None]
    W2[rows, order[:, :4]] = W[rows, order[:, :4]]
    W2[W2 < 0.01] = 0
    W2 /= np.maximum(W2.sum(1, keepdims=True), 1e-9)
    ob.vertex_groups.clear()
    for j, b in enumerate(BONE_NAMES):
        vg = ob.vertex_groups.new(name=b)
        idx = np.nonzero(W2[:, j] > 0)[0]
        for i in idx:
            vg.add([int(i)], float(W2[i, j]), "REPLACE")
    return W2


def bind(ob):
    ob.parent = ARM
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = ARM


def finger_labels(ob):
    """Vertices on the fingers (not the thumb), from their position in each hand's frame."""
    me = ob.data
    n = len(me.vertices)
    P = np.empty(n * 3)
    me.vertices.foreach_get("co", P)
    P = P.reshape(-1, 3)
    lab = np.zeros(n, dtype=bool)
    for s, sx in (("L", 1.0), ("R", -1.0)):
        inv = np.array(REST[f"hand.{s}"].inverted())
        Q = P @ inv[:3, :3].T + inv[:3, 3]
        thumb = (Q[:, 0] * sx > 0.034) | ((Q[:, 0] * sx > 0.02) & (Q[:, 2] < -0.012) & (Q[:, 1] < 0.1))
        lab |= (Q[:, 1] > 0.082) & ~thumb & (np.abs(Q[:, 0]) < 0.06) & (np.abs(Q[:, 2]) < 0.08) & (np.abs(Q[:, 1]) < 0.2)
    return lab




def transfer_weights(ob, rigid_head=False):
    """Weights from the body under each point (or all on the head)."""
    ob.vertex_groups.clear()
    for b in BONE_NAMES:
        ob.vertex_groups.new(name=b)
    if rigid_head:
        ob.vertex_groups["head"].add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        return
    m = ob.modifiers.new("dt", "DATA_TRANSFER")
    m.object = LOW
    m.use_vert_data = True
    m.data_types_verts = {"VGROUP_WEIGHTS"}
    m.vert_mapping = "POLYINTERP_NEAREST"
    m.layers_vgroup_select_src = "ALL"
    m.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


log("weights")
compute_weights(LOW, finger_labels(LOW))
bind(LOW)
for gid, ob in GARMENTS.items():
    transfer_weights(ob, rigid_head=wardrobe.GARMENTS[gid][1] in ("hair", "hat", "glasses"))
    bind(ob)
transfer_weights(VEST)
bind(VEST)
if HIGH is not None:
    HIGH.hide_render = False


# ====================================================================== animation
FPS = 30
scene.render.fps = FPS
PB = ARM.pose.bones
for p in PB:
    p.rotation_mode = "QUATERNION"


def empty(name):
    e = bpy.data.objects.new(name, None)
    COL.objects.link(e)
    return e


IK = {}


def setup_ik():
    for s in ("L", "R"):
        for kind, chain_bone, end_bone in (("hand", f"forearm.{s}", f"hand.{s}"), ("foot", f"shin.{s}", f"foot.{s}")):
            tgt, pole = empty(f"ik_{kind}.{s}"), empty(f"pole_{kind}.{s}")
            c = PB[chain_bone].constraints.new("IK")
            c.target, c.pole_target = tgt, pole
            c.chain_count = 2
            c.use_tail = True
            cr = PB[end_bone].constraints.new("COPY_ROTATION")
            cr.target = tgt
            IK[f"{kind}.{s}"] = (tgt, pole, c)
    calibrate_poles()


def bone_pose(name):
    return ARM.pose.bones[name].matrix.copy()


def calibrate_poles():
    """Finds each IK chain's pole angle: bends the chain and keeps the angle that
    points the elbow/knee at its pole."""
    for key, (tgt, pole, c) in IK.items():
        kind, s = key.split(".")
        sx = 1.0 if s == "L" else -1.0
        if kind == "hand":
            root, mid, end = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"]
            goal = root + V((0.12 * sx, -0.3, -0.2))
            pole_at = mid + V((0.3 * sx, 0.3, -0.3))
            mid_bone = f"forearm.{s}"
        else:
            root, mid, end = J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"]
            goal = root + V((0, 0.05, -0.62))
            pole_at = mid + V((0, -0.6, 0))
            mid_bone = f"shin.{s}"
        tgt.matrix_world = Matrix.Translation(goal) @ REST[f"{kind}.{s}"].to_3x3().to_4x4()
        pole.location = pole_at
        best, best_a = -9.0, 0.0
        for step in (45.0, 9.0, 1.0):
            cands = [best_a + step * k for k in range(-4, 5)] if step < 45 else [45.0 * k for k in range(8)]
            for a in cands:
                c.pole_angle = math.radians(a)
                bpy.context.view_layer.update()
                knee = bone_pose(mid_bone).translation
                line = (goal - root).normalized()
                off = knee - root - line * (knee - root).dot(line)
                want = pole_at - root - line * (pole_at - root).dot(line)
                score = off.normalized().dot(want.normalized()) if off.length > 1e-5 else -1
                if score > best:
                    best, best_a = score, a
        c.pole_angle = math.radians(best_a)
        log(f"pole {key}: {best_a:.0f} deg (fit {best:.3f})")


def gun_frame(origin, fwd, up=(0, 0, 1)):
    """Gun matrix: +X = fwd (muzzle), +Z = up (orthogonalised), +Y = its left."""
    x = V(fwd).normalized()
    y = V(up).cross(x).normalized()
    z = x.cross(y)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(origin)
    return m


def hand_matrix(pos, along, dorsal):
    """Hand bone matrix: Y = wrist->knuckles, Z = back of the hand."""
    return frame(pos, along, dorsal)


def euler(x=0.0, y=0.0, z=0.0):
    return Matrix.Rotation(math.radians(z), 3, "Z") @ Matrix.Rotation(math.radians(y), 3, "Y") @ \
        Matrix.Rotation(math.radians(x), 3, "X")


FK_BONES = ["hips", "spine", "chest", "neck", "head", "clavicle.L", "clavicle.R"]


def set_fk(pose):
    for b in FK_BONES:
        R = REST[b].to_3x3()
        q = pose.get(b, Matrix.Identity(3))
        PB[b].rotation_quaternion = (R.inverted() @ q @ R).to_quaternion()
    PB["hips"].location = REST["hips"].to_3x3().inverted() @ V(pose.get("hips_loc", (0, 0, 0)))


def ankle_target(s, pos, yaw=0.0, pitch=0.0):
    R = REST[f"foot.{s}"].to_3x3()
    m = (euler(z=yaw) @ euler(x=pitch) @ R).to_4x4()
    m.translation = V(pos)
    return m


def default_poles():
    out = {}
    for s, sx in (("L", 1.0), ("R", -1.0)):
        out[f"hand.{s}"] = V((0.55 * sx, 0.35, 0.95))
        out[f"foot.{s}"] = V((0.12 * sx, -1.0, 0.5))
    return out


def evaluate(pose):
    """Poses the rig for one frame; returns {bone: (loc, quat)} basis values."""
    set_fk(pose)
    for s in ("L", "R"):
        # Fingers are modelled curled round a grip; opening rotates them about the hand's X.
        PB[f"fingers.{s}"].rotation_quaternion = Quaternion((1, 0, 0), pose.get(f"open.{s}", 0.0))
    bpy.context.view_layer.update()
    gun = None
    if "gun_chest" in pose:  # the gun rides on the chest
        gun = bone_pose("chest") @ pose["gun_chest"]
    elif "gun" in pose:
        gun = pose["gun"]
    poles = default_poles()
    poles.update(pose.get("poles", {}))
    for s in ("L", "R"):
        key = f"hand.{s}"
        if pose.get(key) is not None:
            hm = pose[key]
        elif gun is not None:
            hm = gun @ (GRIP_R if s == "R" else GRIP_L)
        else:
            hm = Matrix.Translation(J[f"wrist.{s}"]) @ REST[key].to_3x3().to_4x4()
        IK[key][0].matrix_world = hm
        IK[key][1].location = poles[key]
        IK[f"foot.{s}"][0].matrix_world = pose[f"foot.{s}"]
        IK[f"foot.{s}"][1].location = poles[f"foot.{s}"]
    bpy.context.view_layer.update()
    out = {}
    mats = {b.name: b.matrix.copy() for b in PB}
    for b in ARM.data.bones:
        rest = b.matrix_local
        if b.parent:
            basis = rest.inverted() @ b.parent.matrix_local @ mats[b.parent.name].inverted() @ mats[b.name]
        else:
            basis = rest.inverted() @ mats[b.name]
        loc, rot, _ = basis.decompose()
        out[b.name] = (loc, rot)
    return out


# ---------------------------------------------------------------- poses
STAND = {"L": V((0.12, -0.02, 0.088)), "R": V((-0.12, 0.02, 0.088))}
AIM_GUN = gun_frame((-0.115, -0.355, 1.43), (0, -1, 0))


def feet(l_pos, r_pos, l_yaw=0.0, r_yaw=0.0, l_pitch=0.0, r_pitch=0.0):
    return {"foot.L": ankle_target("L", l_pos, l_yaw, l_pitch), "foot.R": ankle_target("R", r_pos, r_yaw, r_pitch)}


def aim_body(breath=0.0, crouch=0.0):
    p = {
        "hips": euler(z=-18, x=4 + 6 * crouch),
        "hips_loc": (0.0, 0.02 + 0.06 * crouch, -0.025 - 0.3 * crouch),
        "spine": euler(z=8, x=4 + 3 * breath + 6 * crouch),
        "chest": euler(z=9, x=3 + 2 * breath),
        "neck": euler(x=6, z=2),
        "head": euler(x=8, y=-5, z=1),
    }
    p.update(feet(V((0.11, -0.12, 0.088)), V((-0.16, 0.14, 0.088)), l_yaw=-20, r_yaw=-45))
    if crouch:
        p.update(feet(V((0.17, -0.22, 0.088)), V((-0.2, 0.2, 0.088)), l_yaw=-20, r_yaw=-50))
    return p


def low_ready_body(breath=0.0):
    p = {
        "hips": euler(z=-6), "hips_loc": (0, 0, -0.01),
        "spine": euler(x=2 + 2 * breath, z=3), "chest": euler(x=1 + 1.5 * breath, z=3),
        "neck": euler(x=2), "head": euler(x=3, z=1),
    }
    p.update(feet(V((0.13, -0.05, 0.088)), V((-0.13, 0.05, 0.088)), l_yaw=-8, r_yaw=-20))
    return p


LOW_GUN = gun_frame((-0.11, -0.27, 1.17), (0.25, -0.8, -0.55), (0, -0.4, 1))
PORT_GUN = gun_frame((-0.1, -0.29, 1.16), (0.22, -0.85, -0.3), (0, -0.3, 1))


def chest_relative(body, gun):
    """The gun's matrix in the chest bone's space for a body pose."""
    set_fk(body)
    bpy.context.view_layer.update()
    return bone_pose("chest").inverted() @ gun


def gait(t, T, direction, stride, duty, lift, width=0.12):
    """Foot targets and hip bob for a gait cycle. direction: unit (x, y) in the rig's space."""
    d = V((direction[0], direction[1], 0)).normalized()
    out = {}
    phase = (t / T) % 1.0
    for s, off, sx in (("L", 0.0, 1.0), ("R", 0.5, -1.0)):
        ph = (phase + off) % 1.0
        base = V((width * sx, 0.0, 0.088))
        if ph < duty:
            k = ph / duty
            pos = base + d * (stride / 2 - stride * k)
            up, pitch = 0.0, 0.0
        else:
            k = (ph - duty) / (1 - duty)
            e = k * k * (3 - 2 * k)
            pos = base + d * (-stride / 2 + stride * e)
            up = lift * math.sin(math.pi * k)
            pitch = -22 * math.sin(math.pi * k * 0.8) + 12 * math.sin(math.pi * min(k * 1.4, 1.0)) * (1 - k)
        pos.z += up
        out[f"foot.{s}"] = ankle_target(s, pos, 0.0, pitch if direction[1] < 0 else -pitch * 0.4)
    bob = math.cos(4 * math.pi * phase)
    sway = math.sin(2 * math.pi * phase)
    return out, bob, sway


CLIPS = {}


def clip(name, seconds, loop=True):
    def deco(fn):
        CLIPS[name] = (seconds, loop, fn)
        return fn
    return deco


@clip("idle", 3.0)
def _idle(t):
    b = math.sin(2 * math.pi * t / 3.0)
    p = low_ready_body(b)
    p["gun_chest"] = GUN_LOW_CHEST
    return p


@clip("aim", 2.0)
def _aim(t):
    b = math.sin(2 * math.pi * t / 2.0)
    p = aim_body(b)
    p["gun_chest"] = GUN_AIM_CHEST
    return p


WALK_T, WALK_SPEED = 0.9, 1.4
RUN_T, RUN_SPEED = 0.66, 4.6


def walk_clip(name, direction, stride):
    duty = 0.6
    T = stride / (duty * WALK_SPEED)

    @clip(name, T)
    def _w(t):
        f, bob, sway = gait(t, T, direction, stride, duty, 0.075, 0.12 if direction[0] == 0 else 0.15)
        lean = 4 * direction[0]
        p = {
            "hips": euler(z=-8 * sway * abs(direction[1]), y=-lean * 0.5), "hips_loc": (0.015 * sway * abs(direction[1]), 0, -0.03 - 0.016 * bob),
            "spine": euler(x=5 + 2 * direction[1] * -1, z=6 * sway * abs(direction[1])),
            "chest": euler(x=2, z=2 * sway * abs(direction[1])),
            "neck": euler(x=4), "head": euler(x=6),
        }
        p.update(f)
        p["gun_chest"] = GUN_WALK_CHEST
        return p


@clip("run", RUN_T)
def _run(t):
    stride = RUN_SPEED * 0.38 * RUN_T
    f, bob, sway = gait(t, RUN_T, (0, -1), stride, 0.38, 0.16)
    p = {
        "hips": euler(x=12, z=-10 * sway), "hips_loc": (0.012 * sway, -0.02, -0.05 - 0.03 * bob),
        "spine": euler(x=6, z=12 * sway), "chest": euler(x=3, z=5 * sway),
        "neck": euler(x=-8), "head": euler(x=-6),
    }
    p.update(f)
    p["gun_chest"] = GUN_PORT_CHEST
    return p


def kneel(hips_z=0.5, hunch=24.0):
    p = {
        "hips": euler(x=hunch * 0.4, z=-10), "hips_loc": (0.0, 0.04, hips_z - 0.965),
        "spine": euler(x=hunch * 0.4), "chest": euler(x=hunch * 0.3),
        "neck": euler(x=-hunch * 0.3), "head": euler(x=-hunch * 0.2),
    }
    p.update(feet(V((0.15, -0.3, 0.088)), V((-0.13, 0.36, 0.07)), l_yaw=-10, r_yaw=-10, r_pitch=-60))
    p["poles"] = {"foot.R": V((-0.13, -0.6, -0.2))}
    return p


@clip("cover", 2.4)
def _cover(t):
    b = math.sin(2 * math.pi * t / 2.4)
    p = kneel(0.52 + 0.006 * b)
    p["gun_chest"] = GUN_COVER_CHEST
    return p


@clip("crouch_aim", 2.0)
def _crouch_aim(t):
    b = math.sin(2 * math.pi * t / 2.0)
    p = aim_body(b, crouch=1.0)
    p["gun_chest"] = GUN_AIM_CHEST
    return p


@clip("blind_fire", 1.2)
def _blind(t):
    j = math.sin(2 * math.pi * t / 1.2 * 3) * 0.01
    p = kneel(0.5, 30)
    p["chest"] = euler(x=10)
    p["head"] = euler(x=15)
    p["gun"] = gun_frame((-0.08 + j, -0.3, 1.36 + j), (0, -1, -0.12))
    p["poles"].update({"hand.L": V((0.5, -0.2, 1.3)), "hand.R": V((-0.5, -0.2, 1.3))})
    return p


@clip("reload", 2.4, loop=False)
def _reload(t):
    p = aim_body(0.0)
    tilt = ss(np.array(t / 0.3)) * (1 - ss(np.array((t - 2.1) / 0.3)))
    tilt = float(tilt)
    g = gun_frame((-0.11, -0.31, 1.33), (0.05, -1, -0.15), (0.45, 0, 1))
    gun = Matrix.lerp(AIM_GUN_ARM, g, tilt) if hasattr(Matrix, "lerp") else (AIM_GUN_ARM if tilt < 0.5 else g)
    p["gun"] = gun
    keys = [  # time, left hand in gun space (pos), or 'belt'
        (0.0, None), (0.35, (0.08, 0.05, -0.1)), (0.6, (0.07, 0.07, -0.2)), (1.0, "belt"),
        (1.35, "belt"), (1.7, (0.08, 0.06, -0.12)), (1.9, (0.08, 0.05, -0.08)), (2.05, (0.1, -0.06, 0.06)),
        (2.15, (0.0, -0.07, 0.06)), (2.4, None)]
    belt = hand_matrix(V((0.17, -0.03, 1.0)), (0.2, -0.4, -1), (1, 0.2, 0))

    def left_at(k):
        v = keys[k][1]
        if v is None:
            return gun @ GRIP_L
        if v == "belt":
            return belt
        return gun @ (Matrix.Translation(V(v)) @ frame((0, 0, 0), (0.2, -0.3, 1), (0, 1, 0)))
    for k in range(len(keys) - 1):
        if keys[k][0] <= t <= keys[k + 1][0]:
            u = (t - keys[k][0]) / (keys[k + 1][0] - keys[k][0])
            u = u * u * (3 - 2 * u)
            a, b = left_at(k), left_at(k + 1)
            la, ra, _ = a.decompose()
            lb, rb, _ = b.decompose()
            p["hand.L"] = Matrix.Translation(la.lerp(lb, u)) @ ra.slerp(rb, u).to_matrix().to_4x4()
            break
    p["poles"] = {"hand.L": V((0.5, -0.1, 0.9))}
    return p


@clip("stumble", 0.9, loop=False)
def _stumble(t):
    k = math.sin(math.pi * min(t / 0.9, 1.0))
    e = min(t / 0.25, 1.0)
    p = aim_body(0.0)
    p["hips"] = euler(z=-18 + 10 * k, x=4 - 12 * k, y=14 * k)
    p["hips_loc"] = (0.1 * k, 0.12 * k, -0.025 - 0.1 * k)
    p["spine"] = euler(x=-10 * k, y=8 * k)
    p["chest"] = euler(x=-8 * k, z=-6 * k)
    p["head"] = euler(x=-15 * k * e, z=10 * k)
    p.update(feet(V((0.11 + 0.15 * k, -0.12 + 0.1 * k, 0.088 + 0.05 * k * (1 - e))), V((-0.16, 0.14 + 0.18 * k, 0.088)),
                  l_yaw=-20, r_yaw=-45))
    p["gun_chest"] = Matrix.Translation(V((0, 0, 0))) @ GUN_AIM_CHEST
    p["gun_chest"] = GUN_LOW_CHEST if k > 0.4 else GUN_AIM_CHEST
    return p


@clip("gut", 2.0)
def _gut(t):
    b = math.sin(2 * math.pi * t / 2.0)
    p = {
        "hips": euler(x=28 + 2 * b), "hips_loc": (0, 0.1, -0.16),
        "spine": euler(x=22 + 3 * b), "chest": euler(x=12 + 2 * b), "neck": euler(x=-14), "head": euler(x=-10),
    }
    p.update(feet(V((0.14, -0.06, 0.088)), V((-0.12, 0.1, 0.088)), l_yaw=-5, r_yaw=-15))
    set_fk(p)
    bpy.context.view_layer.update()
    sp = bone_pose("spine")
    # Spine bone space: X = his left, Y = up the spine, Z = forward.
    p["hand.L"] = sp @ hand_matrix(V((0.05, 0.04, 0.17)), (-1, -0.2, 0.15), (0, 0, 1))
    p["gun"] = gun_frame((-0.24, -0.14, 0.86), (0.1, -0.5, -1), (0, -1, 0))
    return p


@clip("crawl", 2.4)
def _crawl(t):
    ph = t / 2.4
    s1 = math.sin(2 * math.pi * ph)
    p = {
        "hips": euler(x=78), "hips_loc": (0.04 * s1, -0.1, 0.2 - 0.965),
        "spine": euler(x=-6, z=8 * s1), "chest": euler(x=-10, z=6 * s1), "neck": euler(x=-30), "head": euler(x=-25),
    }
    knee_l = max(0.0, s1)
    knee_r = max(0.0, -s1)
    p.update(feet(V((0.18 + 0.12 * knee_l, 0.85 - 0.3 * knee_l, 0.07 + 0.04 * knee_l)),
                  V((-0.18 - 0.12 * knee_r, 0.85 - 0.3 * knee_r, 0.07 + 0.04 * knee_r)), l_pitch=-70, r_pitch=-70))
    p["poles"] = {"foot.L": V((0.5, 0.4, -1.0)), "foot.R": V((-0.5, 0.4, -1.0)),
                  "hand.L": V((0.8, 0.2, 0.6)), "hand.R": V((-0.8, 0.2, 0.6))}
    for s, sx, sgn in (("L", 1, 1), ("R", -1, -1)):
        reach = 0.5 + 0.5 * math.sin(2 * math.pi * ph + (0 if s == "L" else math.pi))
        p[f"hand.{s}"] = hand_matrix(V((0.24 * sx, -0.75 - 0.25 * reach, 0.05 + 0.08 * max(0.0, math.cos(2 * math.pi * ph + (0 if s == 'L' else math.pi))))),
                                     (0.2 * sx, -1, -0.3), (0, 0, 1))
        p[f"open.{s}"] = 0.6
    return p


@clip("surrender", 3.0)
def _surrender(t):
    b = math.sin(2 * math.pi * t / 3.0)
    tremble = math.sin(2 * math.pi * t * 7) * 0.004
    p = {
        "hips": euler(x=-4), "hips_loc": (0, 0.1, 0.5 - 0.965),
        "spine": euler(x=-2 + b), "chest": euler(x=-2), "neck": euler(x=10), "head": euler(x=12),
    }
    p.update(feet(V((0.14, 0.42, 0.06)), V((-0.14, 0.42, 0.06)), l_pitch=-75, r_pitch=-75))
    p["poles"] = {"foot.L": V((0.14, -0.6, 0.0)), "foot.R": V((-0.14, -0.6, 0.0)),
                  "hand.L": V((0.8, 0.3, 1.0)), "hand.R": V((-0.8, 0.3, 1.0))}
    for s, sx in (("L", 1), ("R", -1)):
        p[f"hand.{s}"] = hand_matrix(V((0.27 * sx + tremble, 0.02, 1.36 + tremble)), (0.15 * sx, -0.1, 1), (0, 1, 0))
        p[f"open.{s}"] = 0.9
    return p


@clip("flee", RUN_T)
def _flee(t):
    stride = (RUN_SPEED + 0.6) * 0.38 * RUN_T
    f, bob, sway = gait(t, RUN_T, (0, -1), stride, 0.38, 0.17)
    ph = (t / RUN_T) % 1.0
    p = {
        "hips": euler(x=14, z=-12 * sway), "hips_loc": (0.012 * sway, -0.02, -0.05 - 0.03 * bob),
        "spine": euler(x=8, z=14 * sway), "chest": euler(x=4, z=6 * sway), "neck": euler(x=-10), "head": euler(x=-8),
    }
    p.update(f)
    set_fk(p)
    bpy.context.view_layer.update()
    ch = bone_pose("chest")
    for s, sx in (("L", 1), ("R", -1)):
        sw = math.sin(2 * math.pi * ph + (math.pi if s == "L" else 0.0))
        # Chest bone space: X = his left, Y = up, Z = forward.
        pos = V((0.19 * sx, -0.12 + 0.12 * sw, 0.04 + 0.22 * sw))
        p[f"hand.{s}"] = ch @ hand_matrix(pos, (-0.25 * sx, 0.55, 0.8), (sx, 0, 0))
        p["poles"] = {"hand.L": V((0.5, 0.6, 0.9)), "hand.R": V((-0.5, 0.6, 0.9))}
    return p


@clip("cower", 2.0)
def _cower(t):
    b = math.sin(2 * math.pi * t / 2.0 * 2)
    p = {
        "hips": euler(x=30), "hips_loc": (0, 0.14, 0.42 - 0.965),
        "spine": euler(x=24 + 2 * b), "chest": euler(x=16), "neck": euler(x=20), "head": euler(x=18),
    }
    p.update(feet(V((0.16, -0.12, 0.088)), V((-0.16, -0.06, 0.088)), l_yaw=10, r_yaw=-10))
    set_fk(p)
    bpy.context.view_layer.update()
    hd = bone_pose("head")
    for s, sx in (("L", 1), ("R", -1)):
        p[f"hand.{s}"] = hd @ hand_matrix(V((0.07 * sx, 0.12, 0.02)), (-0.4 * sx, 0.3, 0.7), (0.2 * sx, -1, 0.3))
    p["poles"] = {"hand.L": V((0.5, -0.8, 1.0)), "hand.R": V((-0.5, -0.8, 1.0))}
    return p


def ss_f(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def bake_clips():
    global GUN_AIM_CHEST, GUN_LOW_CHEST, GUN_WALK_CHEST, GUN_PORT_CHEST, GUN_COVER_CHEST, AIM_GUN_ARM
    setup_ik()
    GUN_AIM_CHEST = chest_relative(aim_body(), AIM_GUN)
    AIM_GUN_ARM = AIM_GUN
    GUN_LOW_CHEST = chest_relative(low_ready_body(), LOW_GUN)
    walk_ref = {"spine": euler(x=5), "chest": euler(x=2), "neck": euler(x=4), "head": euler(x=6),
                "hips_loc": (0, 0, -0.03)}
    GUN_WALK_CHEST = chest_relative(walk_ref, gun_frame((-0.115, -0.37, 1.41), (0, -1, 0)))
    GUN_PORT_CHEST = chest_relative({"hips": euler(x=12), "spine": euler(x=6), "chest": euler(x=3),
                                     "hips_loc": (0, -0.02, -0.05)}, PORT_GUN)
    GUN_COVER_CHEST = chest_relative(kneel(0.52), gun_frame((-0.1, -0.34, 0.86), (0.2, -0.85, -0.3)))
    for name, d, stride in (("walk_f", (0, -1), 0.74), ("walk_b", (0, 1), 0.62), ("walk_l", (1, 0), 0.5), ("walk_r", (-1, 0), 0.5)):
        walk_clip(name, d, stride)
    baked = {}
    for name, (seconds, loop, fn) in CLIPS.items():
        frames = max(2, int(round(seconds * FPS)))
        data = []
        for f in range(frames + (0 if loop else 1)):
            data.append(evaluate(fn(f / FPS)))
        baked[name] = (data, loop)
        log(f"clip {name}: {frames} frames")
    # Constraints off, then write keys.
    for p in PB:
        for c in list(p.constraints):
            p.constraints.remove(c)
    for e in [o for o in COL.objects if o.type == "EMPTY"]:
        bpy.data.objects.remove(e)
    ARM.animation_data_create()
    for name, (data, loop) in baked.items():
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        ARM.animation_data.action = act
        prev = {}
        for f, frame_pose in enumerate(data + ([data[0]] if loop else [])):
            for b, (loc, rot) in frame_pose.items():
                if b in prev and prev[b].dot(rot) < 0:
                    rot = -rot
                prev[b] = rot
                PB[b].rotation_quaternion = rot
                PB[b].keyframe_insert("rotation_quaternion", frame=f + 1)
                if b in ("hips", "root"):
                    PB[b].location = loc
                    PB[b].keyframe_insert("location", frame=f + 1)
    ARM.animation_data.action = None
    for p in PB:
        p.rotation_quaternion = (1, 0, 0, 0)
        p.location = (0, 0, 0)
    return baked


GUN_AIM_CHEST = GUN_LOW_CHEST = GUN_WALK_CHEST = GUN_PORT_CHEST = GUN_COVER_CHEST = AIM_GUN_ARM = None
BAKED = {}
if not args.no_anim:
    BAKED = bake_clips()



# ====================================================================== UVs, textures
BODY_BOX = (0.0, 0.0, 0.5, 1.0)      # the body: tattoo/facial-hair map (triad_skin.png) covers this half
WARD_BOX = (0.5, 0.0, 0.95, 1.0)     # the wardrobe
CAP_UV = (0.975, 0.05, 0.022)        # flesh-cap disc in the strip u > 0.95: centre u, v, radius


def _uv_np(ob):
    uv = ob.data.uv_layers.active.data
    a = np.empty(len(uv) * 2)
    uv.foreach_get("uv", a)
    return a.reshape(-1, 2)


def _set_uv(ob, a):
    ob.data.uv_layers.active.data.foreach_set("uv", np.asarray(a).ravel())


def unwrap_group(objs, box, boost=False):
    """Smart-projects `objs` and packs their islands into `box` (u0, v0, u1, v1)."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        if not ob.data.uv_layers:
            ob.data.uv_layers.new()
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    if boost:
        # More texels for the face, then the rest of the skin.
        for ob in objs:
            uv = ob.data.uv_layers.active.data
            for poly in ob.data.polygons:
                name = MATS[poly.material_index]
                c = poly.center
                k = 1.0
                if name in ("skin", "eye") and c.z > 1.54 and c.y < 0.0:
                    k = 2.4
                elif name in ("skin", "eye", "hair"):
                    k = 1.25
                if k != 1.0:
                    for li in poly.loop_indices:
                        uv[li].uv = uv[li].uv * k
    # Shrink everything into the box's corner and anchor its far corner, then
    # pack into that bounding box (shapes keep their proportions).
    u0, v0, u1, v1 = box
    side = min(u1 - u0, v1 - v0) * 0.5
    for ob in objs:
        a = _uv_np(ob)
        a = (a - a.min(0)) / max(np.ptp(a, 0).max(), 1e-9) * side + np.array((u0, v0))
        _set_uv(ob, a)
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in ((0, 0, -5), (0.001, 0, -5), (0, 0.001, -5))]
    bm.faces.new(vs)
    me = bpy.data.meshes.new("uv_anchor")
    bm.to_mesh(me)
    bm.free()
    anc = bpy.data.objects.new("uv_anchor", me)
    COL.objects.link(anc)
    uvl = me.uv_layers.new()
    for i, c in enumerate(((u1 - 0.002, v1 - 0.002), (u1, v1 - 0.002), (u1, v1))):
        uvl.data[i].uv = c
    anc.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="ORIGINAL_AABB", rotate=True, margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.data.objects.remove(anc)
    for ob in objs:
        a = _uv_np(ob)
        log(f"  uv {ob.name}: u {a[:, 0].min():.3f}-{a[:, 0].max():.3f} v {a[:, 1].min():.3f}-{a[:, 1].max():.3f}")


ALL_LOW = [LOW, VEST] + list(GARMENTS.values())


def _bake_targets(img):
    for m in bpy.data.materials:
        if not m.use_nodes or m.node_tree is None:
            continue
        nt = m.node_tree
        node = nt.nodes.get("bake_target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "bake_target"
        node.image = img
        nt.nodes.active = node


def _emit(kind):
    """Routes every material's output to an emission of `kind`."""
    for i, n in enumerate(MATS):
        nt = MAT[n].node_tree
        N, L = nt.nodes, nt.links
        for old in [x for x in N if x.name.startswith("tmp_")]:
            N.remove(old)
        em = N.new("ShaderNodeEmission")
        em.name = "tmp_emit"
        if kind == "matid":
            em.inputs["Color"].default_value = ((i + 0.5) / 16.0, 0, 0, 1)
        elif kind == "objid":
            info = N.new("ShaderNodeObjectInfo")
            info.name = "tmp_info"
            div = N.new("ShaderNodeMath")
            div.name = "tmp_div"
            div.operation = "DIVIDE"
            div.inputs[1].default_value = 64.0
            L.new(info.outputs["Object Index"], div.inputs[0])
            L.new(div.outputs[0], em.inputs["Color"])
        else:
            geo = N.new("ShaderNodeNewGeometry")
            geo.name = "tmp_geo"
            ma = N.new("ShaderNodeVectorMath")
            ma.name = "tmp_ma"
            ma.operation = "MULTIPLY_ADD"
            ma.inputs[1].default_value = (0.5, 0.5, 0.5)
            ma.inputs[2].default_value = (0.5, 0.5, 0.0) if kind == "pos" else (0.5, 0.5, 0.5)
            L.new(geo.outputs["Position" if kind == "pos" else "Normal"], ma.inputs[0])
            L.new(ma.outputs[0], em.inputs["Color"])
        L.new(em.outputs[0], N["Material Output"].inputs["Surface"])


def _restore():
    for m in MAT.values():
        nt = m.node_tree
        for x in [x for x in nt.nodes if x.name.startswith("tmp_")]:
            nt.nodes.remove(x)
        nt.links.new(nt.nodes["Principled BSDF"].outputs[0], nt.nodes["Material Output"].inputs["Surface"])


def px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def _select(obs, active):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = active


def bake_maps(size):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake")
    maps = {}
    for i, ob in enumerate(ALL_LOW):
        ob.pass_index = i
    if HIGH is not None:
        HIGH.hide_render = True
    for kind in ("pos", "nor", "matid", "objid"):
        img = bpy.data.images.new(f"triad_{kind}", size, size, alpha=True, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        _emit(kind)
        _select(ALL_LOW, LOW)
        _bake_targets(img)
        scene.cycles.samples = 1
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        maps[kind] = px(img)
        log(f"baked {kind}")
    _restore()
    # AO: each piece alone with the body (a garment isn't shaded by another it
    # may never be worn with; the body isn't shaded by clothes at all).
    ao = bpy.data.images.new("triad_ao_raw", size, size, alpha=False, float_buffer=True)
    ao.colorspace_settings.name = "Non-Color"
    scene.world.light_settings.distance = 0.12
    _bake_targets(ao)
    scene.cycles.samples = args.ao_samples
    first = True
    for ob in ALL_LOW:
        for o2 in ALL_LOW:
            o2.hide_render = not (o2 is ob or o2 is LOW)
        _select([ob], ob)
        bpy.ops.object.bake(type="AO", margin=4, use_clear=first)
        first = False
    for o2 in ALL_LOW:
        o2.hide_render = False
    maps["ao"] = px(ao)[:, :, 0]
    log("baked ao")
    nimg = bpy.data.images.new("triad_normal", size, size, alpha=False, float_buffer=True)
    nimg.colorspace_settings.name = "Non-Color"
    _bake_targets(nimg)
    scene.cycles.samples = 4
    HIGH.hide_render = False
    for o2 in ALL_LOW:
        o2.hide_render = o2 is not LOW
    _select([HIGH, LOW], LOW)
    bpy.ops.object.bake(type="NORMAL", use_selected_to_active=True, cage_extrusion=0.004,
                        max_ray_distance=0.014, margin=4, use_clear=True)
    for o2 in ALL_LOW:
        o2.hide_render = False
    maps["normal"] = px(nimg)
    log("baked normal")
    return maps


def _dilate(arr, cover):
    """Fills every texel outside `cover` with the nearest covered one (no dark seams in the mips)."""
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(~cover, return_distances=False, return_indices=True)
    return arr[idx[0], idx[1]]


def paint_atlas(maps, size):
    import paint
    import tattoos
    pos = maps["pos"]
    cover = pos[:, :, 3] > 0.5
    P = (pos[:, :, :3][cover].astype(np.float64) - np.array((0.5, 0.5, 0.0))) * 2.0
    Nn = (maps["nor"][:, :, :3][cover].astype(np.float64) - 0.5) * 2.0
    mid = np.clip((maps["matid"][:, :, 0][cover] * 16.0).astype(np.int32), 0, len(MATS) - 1)
    oid = np.clip(np.round(maps["objid"][:, :, 0][cover] * 64.0).astype(np.int32), 0, len(ALL_LOW) - 1)
    ao = maps["ao"][cover]
    n = len(P)
    base = np.zeros((n, 3))
    rough = np.full(n, 0.8)
    metal = np.zeros(n)
    mask = np.zeros((n, 4))
    height = np.zeros(n)
    skin = np.zeros((n, 4))
    names = [ob.name for ob in ALL_LOW]
    for i, name in enumerate(names):
        sel = oid == i
        if not sel.any():
            continue
        o = paint.Out(int(sel.sum()))
        if name == "triad":
            paint.paint_body(o, P[sel], Nn[sel], mid[sel], REST_HAND)
            o.skin[:, :3] = tattoos.ink(P[sel], Nn[sel], regions(P[sel]), REST_HAND)
        else:
            gid = "vest" if name == "vest" else name[2:]
            fn = paint.PAINTERS[gid]
            if gid == "glasses":
                fn(o, P[sel], Nn[sel], mid[sel])
            else:
                fn(o, P[sel], Nn[sel])
        base[sel], rough[sel], metal[sel], mask[sel], height[sel], skin[sel] = \
            o.base, o.rough, o.metal, o.mask, o.height, o.skin
        log(f"  painted {name}: {sel.sum()} texels")
    # Cavity shading from AO (cloth folds, armpits, under the jaw); none on the
    # eyes and glasses, which sit deep in their sockets and would go black.
    clear = (mid == MATS.index("eye")) | (mid == MATS.index("lens"))
    ao = np.where(clear, np.maximum(ao, 0.9), ao)
    base = base * (0.55 + 0.45 * ao[:, None])
    full = lambda k: np.zeros((size, size, k))
    B, ORM, MSK, SKN = full(3), np.ones((size, size, 3)), full(4), full(4)
    B[cover], MSK[cover], SKN[cover] = np.clip(base, 0, 1), mask, skin
    ORM[cover] = np.stack([ao, rough, metal], 1)
    # Cloth normals from the painted height: slope per metre along the atlas axes.
    H = np.zeros((size, size))
    H[cover] = height
    Pfull = np.zeros((size, size, 3))
    Pfull[cover] = P
    du = np.zeros((size, size))
    dv = np.zeros((size, size))
    du[:, 1:-1] = (H[:, 2:] - H[:, :-2])
    dv[1:-1, :] = (H[2:, :] - H[:-2, :])
    lu = np.zeros((size, size))
    lv = np.zeros((size, size))
    lu[:, 1:-1] = np.linalg.norm(Pfull[:, 2:] - Pfull[:, :-2], axis=2)
    lv[1:-1, :] = np.linalg.norm(Pfull[2:, :] - Pfull[:-2, :], axis=2)
    ok_u = np.zeros((size, size), bool)
    ok_v = np.zeros((size, size), bool)
    ok_u[:, 1:-1] = cover[:, 2:] & cover[:, :-2]
    ok_v[1:-1, :] = cover[2:, :] & cover[:-2, :]
    texel = 2.0 * (1.0 / size)
    su = np.where(ok_u & (lu < 0.02), du / np.maximum(lu, 1e-6), 0.0)
    sv = np.where(ok_v & (lv < 0.02), dv / np.maximum(lv, 1e-6), 0.0)
    nrm = np.stack([-su, -sv, np.ones_like(su)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    NRM = maps["normal"][:, :, :3].astype(np.float64)
    body_texels = np.zeros((size, size), bool)
    body_texels[cover] = oid == 0
    NRM = np.where((cover & ~body_texels)[..., None], nrm * 0.5 + 0.5, NRM)
    paint_cap(B, ORM, MSK, size)
    capzone = np.zeros((size, size), bool)
    u = (np.arange(size) + 0.5) / size
    U, Vv = np.meshgrid(u, u)
    capzone = np.sqrt((U - CAP_UV[0]) ** 2 + (Vv - CAP_UV[1]) ** 2) < CAP_UV[2] * 1.15
    NRM[capzone & ~cover] = (0.5, 0.5, 1.0)
    SKN[capzone & ~cover] = 0.0
    filled = cover | capzone
    B, ORM, MSK, SKN, NRM = (_dilate(a, filled) for a in (B, ORM, MSK, SKN, NRM))
    return B, ORM, MSK, SKN, NRM


def paint_cap(B, ORM, MSK, size):
    """The flesh cap disc in the strip: skin edge, fat, muscle, bone."""
    import paint
    cu, cv, cr = CAP_UV
    u = (np.arange(size) + 0.5) / size
    U, Vv = np.meshgrid(u, u)
    r = np.sqrt((U - cu) ** 2 + (Vv - cv) ** 2) / cr
    zone = r < 1.15
    P3 = np.stack([U * 3, Vv * 3, np.zeros_like(U)], -1).reshape(-1, 3)
    nz = paint.fbm(P3, 60.0, 3, 41).reshape(size, size)
    col = np.stack([0.42 + 0.12 * nz, 0.05 + 0.03 * nz, 0.045 + 0.02 * nz], -1)
    col = np.where((r > 0.84)[..., None], np.array((0.78, 0.66, 0.42)), col)
    col = np.where((r > 0.93)[..., None], np.array((0.3, 0.12, 0.1)), col)
    col = np.where((r < 0.27)[..., None], np.array((0.84, 0.8, 0.7)), col)
    col = np.where((r < 0.12)[..., None], np.array((0.35, 0.05, 0.04)), col)
    col = np.where(((r > 0.27) & (r < 0.33))[..., None], np.array((0.25, 0.02, 0.02)), col)
    B[zone] = col[zone]
    ORM[zone, 0] = 1.0
    ORM[zone, 1] = 0.22
    ORM[zone, 2] = 0.0
    MSK[zone] = 0.0


def save_png(arr, path, size=None, mode="RGB"):
    from PIL import Image
    a = np.flipud(np.clip(arr, 0, 1))  # Blender rows run bottom-up
    img = Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode)
    if size and size != img.size:
        # Channel by channel: Pillow premultiplies RGBA by alpha when it
        # resizes, which would wipe the mask's tint channels wherever A = 0.
        img = Image.merge(mode, [c.resize(size, Image.LANCZOS) for c in img.split()])
    img.save(path, optimize=True)
    log("saved", path, img.size)


def flat_atlas(size):
    """--fast: flat colours by material and object, so the export works without bakes."""
    B = np.full((size, size, 3), 0.5)
    ORM = np.ones((size, size, 3))
    ORM[..., 1] = 0.8
    ORM[..., 2] = 0.0
    MSK = np.zeros((size, size, 4))
    MSK[..., 0] = 1.0
    MSK[:, : size // 2, 0] = 0.0
    MSK[:, : size // 2, 3] = 1.0
    B[:, : size // 2] = (0.8, 0.62, 0.49)
    SKN = np.zeros((size, size, 4))
    NRM = np.zeros((size, size, 3))
    NRM[...] = (0.5, 0.5, 1.0)
    return B, ORM, MSK, SKN, NRM


# ====================================================================== severable parts
def cut_specs():
    """Every place the body can come apart (2026-11-11: a cut at every joint).

    (name, plane point, plane normal pointing away from the body, centre of the
    bisect, bisect radius, reach along the normal, part radius, parent part,
    bones the part may take faces from). Deepest parts first: a face goes to
    the first part that claims it, so the hand is checked before the forearm,
    the forearm before the upper arm. Every part's faces must also be weighted
    mostly to its own limb chain, so a plane never grabs the flank or the
    other leg.
    """
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
        c = sh + (e - sh) * 0.6  # not higher: the sleeve is fused to the flank above this
        specs.append((f"upper_arm_{s}", c, du, c, 0.095, 0.3, 0.11, "body", arm))
        k, a = J[f"knee.{s}"], J[f"ankle.{s}"]
        d = (a - k).normalized()
        c = k + (a - k) * 0.3
        specs.append((f"shin_{s}", c, d, c, 0.13, 0.55, 0.16, f"thigh_{s}", leg))
        hp = J[f"hip.{s}"]
        dt = (k - hp).normalized()
        c = hp + (k - hp) * 0.65  # not higher: the trouser legs are fused above this
        specs.append((f"thigh_{s}", c, dt, c, 0.12, 0.5, 0.14, "body", leg))
    return specs


def _dominant_bones(bm, src):
    """Face index -> the vertex group with the most total weight over its corners."""
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


def _cut_ring(bm, co, no, radius, prad):
    """Faces the cut plane passes through that ring this limb: connected bands
    of straddling faces near the plane point, every face within `prad` of the
    limb's axis. The plane also crosses the torso or the other leg somewhere;
    those bands aren't connected to the limb's and are left alone."""
    def side(v):
        return (v.co - co).dot(no)

    def perp(p):
        d = p - co
        return (d - no * d.dot(no)).length
    cand = set()
    for f in bm.faces:
        ds = [side(v) for v in f.verts]
        if min(ds) < 0 < max(ds) and (f.calc_center_median() - co).length < radius * 1.6:
            cand.add(f)
    rings = []
    left = set(cand)
    while left:
        f0 = left.pop()
        band = [f0]
        stack = [f0]
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
        mn = min(perp(v.co) for f in band for v in f.verts)
        if os.environ.get("CUT_DEBUG"):
            log(f"  band {len(band)} faces perp {mn:.3f}-{mp:.3f} {'KEEP' if mp < prad else ''}")
        if mp < prad:
            keep += band
    return keep


def split_parts(src, prefix="part_", caps=True):
    """Cuts the severable parts out of `src` (same UVs and weights) and caps every cut.

    Parts nest (hand < forearm < upper arm < body; shin < thigh < body): each
    cut is capped on both sides, on the part it frees and on its parent.
    Garments (caps=False) are cut with the same planes but left open: the
    body's own cap closes the limb, the sleeve just ends there. Parts a
    garment has no faces in are skipped.
    """
    bm = bmesh.new()
    bm.from_mesh(src.data)
    specs = cut_specs()
    cut_edges = []
    for name, co, no, centre, radius, reach, prad, parent, bones in specs:
        if os.environ.get("CUT_DEBUG"):
            log(f"cut {name}")
        ring = _cut_ring(bm, co, no, radius, prad)
        verts = list({v for f in ring for v in f.verts})
        edges = list({e for f in ring for e in f.edges})
        res = bmesh.ops.bisect_plane(bm, geom=verts + edges + ring, dist=1e-6, plane_co=co, plane_no=no)
        cut_edges += [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
    bmesh.ops.split_edges(bm, edges=list(set(cut_edges)))
    bm.faces.index_update()
    dom = _dominant_bones(bm, src)

    def part_of(f):
        c = f.calc_center_median()
        for name, co, no, centre, radius, reach, prad, parent, bones in specs:
            if dom.get(f.index, "") not in bones:
                continue
            along = (c - co).dot(no)
            if along > 0 and along < reach and ((c - co) - no * along).length < prad:
                return name
        return "body"

    # The cuts split the mesh into islands bounded by cut rings (and garment
    # edges). Each island goes wholesale to the part most of its faces vote
    # for, so no part ends in a ragged edge.
    owner = {}
    seen = set()
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        island = []
        stack = [f0]
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
            k = part_of(f)
            votes[k] = votes.get(k, 0.0) + f.calc_area()
        win = max(votes, key=votes.get)
        for f in island:
            owner[f.index] = win
    cap_mat = MATS.index("cap")
    me_parts = {}
    for part in ["body"] + [sp[0] for sp in specs]:
        b2 = bm.copy()
        b2.faces.ensure_lookup_table()
        dead = [f for f in b2.faces if owner[f.index] != part]
        bmesh.ops.delete(b2, geom=dead, context="FACES")
        if not b2.faces:
            b2.free()
            continue
        uvl = b2.loops.layers.uv.active
        for name, co, no, centre, radius, reach, prad, parent, bones in specs:
            if not caps or part not in (parent, name):
                continue
            edges = [e for e in b2.edges if e.is_boundary and all(abs((v.co - co).dot(no)) < 2e-4 for v in e.verts)
                     and (e.verts[0].co - centre).length < radius]
            if not edges:
                log(f"WARNING: no cap edges for cut {name} on {part}")
                continue
            out = bmesh.ops.holes_fill(b2, edges=edges, sides=0)
            faces = out["faces"]
            if not faces:
                log(f"WARNING: cap fill failed for cut {name} on {part}")
                continue
            ref = no.orthogonal().normalized()
            ref2 = no.cross(ref)
            pts = [v.co for f in faces for v in f.verts]
            c = sum(pts, V((0, 0, 0))) / len(pts)
            rmax = max((p - c).length for p in pts) or 0.05
            for f in faces:
                f.material_index = cap_mat
                for loop in f.loops:
                    d = loop.vert.co - c
                    loop[uvl].uv = (CAP_UV[0] + d.dot(ref) / rmax * CAP_UV[2] * 0.95,
                                    CAP_UV[1] + d.dot(ref2) / rmax * CAP_UV[2] * 0.95)
            # The parent's cap faces where the part was (+no); the part's cap faces the parent (-no).
            for f in faces:
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
        ob.data.materials.clear()
        for m in src.data.materials:
            ob.data.materials.append(m)
        me.shade_smooth()
        bind(ob)
        me_parts[part] = ob
        log(f"  {prefix}{part}: {tris(ob)} tris")
    bm.free()
    return me_parts


def preview_split(path):
    """Exploded view: every part pushed out along its cut, rendered from the front and the side."""
    specs = {sp[0]: sp for sp in cut_specs()}
    saved = {}
    groups = [PARTS] + [WPARTS[g] for g in PREVIEW_OUTFIT if g in WPARTS]
    for parts in groups:
        for name, ob in parts.items():
            if name == "body":
                continue
            off = V((0, 0, 0))
            n = name
            while n in specs:
                off += specs[n][2] * 0.12
                n = specs[n][7]
            saved[ob] = ob.location.copy()
            ob.location = ob.location + off
    LOW.hide_render = True
    VEST.hide_render = True
    setup_render(24, 700, 900)
    tmp = []
    for i, (loc, tgt) in enumerate((((0, -3.6, 1.0), (0, 0, 0.95)), ((3.2, -1.8, 1.2), (0, 0, 0.95)), ((0, 3.6, 1.0), (0, 0, 0.95)))):
        camera(loc, tgt, 50)
        tmp.append(render(f"{path}_{i}.png"))
    sheet(tmp, 3, f"{path}.png")
    for p in tmp:
        os.remove(p)
    for ob, loc in saved.items():
        ob.location = loc
    LOW.hide_render = False




# ====================================================================== export
def triangulate(ob):
    m = ob.modifiers.new("tri", "TRIANGULATE")
    m.keep_custom_normals = True
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    # The armature modifier sits first; triangulate goes in front of it.
    bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
    bpy.ops.object.modifier_apply(modifier=m.name)


def export(path, objs, animations):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    for ob in objs:
        triangulate(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ARM.select_set(True)
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = ARM
    kw = dict(filepath=path, export_format="GLTF_SEPARATE", use_selection=True, export_apply=False,
              export_skins=True, export_materials="NONE", export_tangents=True)
    if animations:
        kw.update(export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_range=False)
    else:
        kw.update(export_animations=False)
    bpy.ops.export_scene.gltf(**kw)
    log("exported", path)


TEX_DIR = os.path.join(os.path.dirname(args.out), "textures") if args.out else ""
log("unwrap")
unwrap_group([LOW], BODY_BOX, boost=True)
unwrap_group([VEST] + list(GARMENTS.values()), WARD_BOX)
if args.fast:
    B, ORM, MSK, SKN, NRM = flat_atlas(args.tex)
else:
    maps = bake_maps(args.tex)
    log("painting")
    B, ORM, MSK, SKN, NRM = paint_atlas(maps, args.tex)
    bpy.data.objects.remove(HIGH)
    HIGH = None
if TEX_DIR:
    os.makedirs(TEX_DIR, exist_ok=True)
    half = (args.tex // 2, args.tex // 2) if args.tex > 2048 else None
    save_png(B, os.path.join(TEX_DIR, "triad_basecolor.png"))
    save_png(NRM, os.path.join(TEX_DIR, "triad_normal.png"), half)
    save_png(ORM, os.path.join(TEX_DIR, "triad_orm.png"), half)
    save_png(MSK, os.path.join(TEX_DIR, "triad_mask.png"), half, "RGBA")
    # The skin map covers the body's half of the atlas (u < 0.5) at full resolution.
    save_png(SKN[:, : args.tex // 2], os.path.join(TEX_DIR, "triad_skin.png"), None, "RGBA")
log("textures done")

log("splitting")
PARTS = split_parts(LOW, "part_", caps=True)
WPARTS = {}
for gid, ob in GARMENTS.items():
    WPARTS[gid] = split_parts(ob, f"w_{gid}__", caps=False)
LOW.name = "triad"
if args.out:
    export(args.out, [LOW, VEST] + list(PARTS.values()), True)
    wpath = os.path.join(os.path.dirname(args.out), "triad_wardrobe.gltf")
    wobjs = list(GARMENTS.values()) + [p for d in WPARTS.values() for p in d.values()]
    export(wpath, wobjs, False)


# ====================================================================== previews
def import_guns():
    guns = {}
    for name in ("type56", "pump", "smg"):
        path = os.path.join(args.guns, f"{name}.gltf")
        if not os.path.exists(path):
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        if new:
            guns[name] = new[0]
            new[0].hide_render = True
    return guns


def setup_render(samples, w, h):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.44, 0.47, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
    key.data.energy = 3.2
    key.data.angle = math.radians(8)
    key.rotation_euler = (math.radians(50), 0, math.radians(-35))
    COL.objects.link(key)
    rim = bpy.data.objects.new("rim", bpy.data.lights.new("rim", "SUN"))
    rim.data.energy = 1.5
    rim.rotation_euler = (math.radians(60), 0, math.radians(150))
    COL.objects.link(rim)
    floor = bpy.data.meshes.new("floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6)
    bm.to_mesh(floor)
    bm.free()
    fl = bpy.data.objects.new("floor", floor)
    fm = bpy.data.materials.new("floor")
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.25, 0.26, 1)
    floor.materials.append(fm)
    COL.objects.link(fl)


def camera(loc, target, lens):
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    COL.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.camera = cam
    return cam


def render(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def sheet(paths, cols, out):
    from PIL import Image
    ims = [Image.open(p) for p in paths]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    s = Image.new("RGB", (w * cols, h * rows))
    for i, im in enumerate(ims):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    s.save(out)
    log("preview:", out)


POSE_SHOTS = [("aim", 0, "type56"), ("idle", 0, "type56"), ("walk_f", 6, "type56"), ("run", 5, "type56"),
              ("crouch_aim", 0, "pump"), ("cover", 0, "type56"), ("blind_fire", 0, "smg"), ("reload", 30, "type56"),
              ("stumble", 12, "type56"), ("gut", 0, "smg"), ("crawl", 18, None), ("surrender", 0, None),
              ("flee", 5, None), ("cower", 0, None)]


PREVIEW_OUTFIT = ("bomber", "cargo", "sneakers", "hair_fade")


def preview_poses(prefix, guns):
    for gid, ob in GARMENTS.items():
        ob.hide_render = gid not in PREVIEW_OUTFIT
    tmp = []
    for name, frame_no, gun in POSE_SHOTS:
        if name not in BAKED:
            continue
        ARM.animation_data.action = bpy.data.actions[name]
        scene.frame_set(frame_no + 1)
        bpy.context.view_layer.update()
        for g in guns.values():
            g.hide_render = True
        if gun and gun in guns:
            g = guns[gun]
            g.hide_render = False
            g.matrix_world = ARM.matrix_world @ PB["weapon"].matrix @ GUN_TO_BONE
        camera((1.9, -2.6, 1.25), (0, -0.1, 0.8), 50)
        tmp.append(render(f"{prefix}_pose_{name}.png"))
    sheet(tmp, 7, f"{prefix}_poses.png")
    for p in tmp:
        os.remove(p)
    ARM.animation_data.action = None
    for g in guns.values():
        g.hide_render = True


if args.tattoo_sheet:
    import tattoos
    tattoos.preview(args.tattoo_sheet)
for parts in [PARTS] + list(WPARTS.values()):
    for ob in parts.values():
        ob.hide_render = True
if args.split_preview:
    for parts in [PARTS] + [WPARTS[g] for g in PREVIEW_OUTFIT if g in WPARTS]:
        for ob in parts.values():
            ob.hide_render = False
    for ob in GARMENTS.values():
        ob.hide_render = True
    preview_split(args.split_preview)
if args.preview:
    os.makedirs(os.path.dirname(args.preview) or ".", exist_ok=True)
    GUNS = import_guns()
    setup_render(args.samples, 420, 600)
    VEST.hide_render = True
    if BAKED:
        preview_poses(args.preview, GUNS)

log("done")
