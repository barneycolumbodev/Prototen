"""Triad gunman: the first enemy character (CLAUDE.md §7, docs/design.md §5).

One rigged, skinned, textured man in street clothes: nylon bomber jacket with
knit hem/cuffs/collar and a centre zip, cargo trousers, sneakers with white
soles, short faded black hair. Jacket and trousers are tinted per role in
Godot (mask texture), so one model serves the Gunman, the Enforcer (adds the
plate carrier) and the Red Pole (lieutenant).

Construction (all procedural, rebuildable):
- Each garment is a set of metaball families, converted, unioned with a voxel
  remesh, smoothed and cut with planes (crisp hems and cuffs). HIGH keeps the
  dense mesh for baking, LOW is decimated for the game.
- Skin weights come from bone chains with joint blends, then smoothed over
  the mesh, so joints bend cleanly.
- Severable parts for dismemberment (head; upper arms, forearms, hands;
  thighs, shins: a cut at every joint, nested) are cut from the
  same LOW mesh with the same UVs and weights, with flesh caps on both sides.
  The game shows the intact mesh until something is severed, then swaps to
  the parts. Caps sit inside closed volumes while attached.
- Textures are painted in numpy from baked position / normal / material-id
  maps (seams, zip, rib knit, pockets, face, stubble, hair), plus a normal map
  baked from HIGH and AO.
- Animation clips are posed with IK (hands on the gun's grips, feet planted)
  and baked to FK keys per frame.

Axes: Blender Z up, the man faces -Y (glTF/Godot +Z), his left is +X.
Every long gun is held at the same two points (raw_assets/weapons/enemy_guns).

Run:
  tools/blender.sh raw_assets/characters/triad/build.py --out assets/characters/triad/triad.gltf --tex 2048 \
      --preview docs/previews/triad
  Fast check (no bake, flat colours): add --fast
"""
import argparse
import math
import os
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Quaternion, Vector

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--preview", default="", help="prefix for preview PNGs")
ap.add_argument("--fast", action="store_true", help="no bake: flat material colours")
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--guns", default="assets/weapons/enemy")
ap.add_argument("--no-anim", action="store_true")
ap.add_argument("--split-preview", default="", help="exploded view of the severable parts (PNG path, no .png)")
args = ap.parse_args(argv)

T0 = time.time()


def log(*a):
    print(f"[triad {time.time() - T0:6.1f}s]", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COL = scene.collection

# ====================================================================== skeleton
# Rest pose: relaxed A-pose. Joint positions in metres (1.75 m man).
J = {
    "root": V((0, 0, 0)),
    "hips": V((0, 0.0, 0.965)),
    "spine": V((0, 0.0, 1.075)),
    "chest": V((0, 0.0, 1.245)),
    "neck": V((0, 0.012, 1.462)),
    "head": V((0, 0.004, 1.572)),
    "head_end": V((0, 0.004, 1.76)),
}
for s, sx in (("L", 1.0), ("R", -1.0)):
    J[f"clav.{s}"] = V((0.025 * sx, -0.005, 1.425))
    J[f"shoulder.{s}"] = V((0.172 * sx, 0.018, 1.418))
    up = V((0.6 * sx, 0.06, -0.8)).normalized()
    J[f"elbow.{s}"] = J[f"shoulder.{s}"] + up * 0.30
    fo = V((0.5 * sx, -0.16, -0.85)).normalized()
    J[f"wrist.{s}"] = J[f"elbow.{s}"] + fo * 0.265
    J[f"knuckle.{s}"] = J[f"wrist.{s}"] + fo * 0.088
    J[f"tip.{s}"] = J[f"knuckle.{s}"] + fo * 0.085
    J[f"hip.{s}"] = V((0.092 * sx, 0.0, 0.93))
    J[f"knee.{s}"] = V((0.102 * sx, -0.012, 0.505))
    J[f"ankle.{s}"] = V((0.106 * sx, 0.022, 0.088))
    J[f"ball.{s}"] = V((0.112 * sx, -0.105, 0.022))

# name, head, tail, parent, roll-align vector (bone Z axis points along it)
BONES = [
    ("root", V((0, 0, 0)), V((0, -0.2, 0)), None, V((0, 0, 1))),
    ("hips", J["hips"], J["spine"], "root", V((0, -1, 0))),
    ("spine", J["spine"], J["chest"], "hips", V((0, -1, 0))),
    ("chest", J["chest"], V((0, 0.0, 1.44)), "spine", V((0, -1, 0))),
    ("neck", J["neck"], J["head"], "chest", V((0, -1, 0))),
    ("head", J["head"], J["head_end"], "neck", V((0, -1, 0))),
]
for s, sx in (("L", 1.0), ("R", -1.0)):
    BONES += [
        (f"clavicle.{s}", J[f"clav.{s}"], J[f"shoulder.{s}"], "chest", V((0, -1, 0))),
        (f"upper_arm.{s}", J[f"shoulder.{s}"], J[f"elbow.{s}"], f"clavicle.{s}", V((0, -1, 0))),
        (f"forearm.{s}", J[f"elbow.{s}"], J[f"wrist.{s}"], f"upper_arm.{s}", V((0, -1, 0))),
        (f"hand.{s}", J[f"wrist.{s}"], J[f"knuckle.{s}"], f"forearm.{s}", V((sx, 0, 0))),
        (f"fingers.{s}", J[f"knuckle.{s}"], J[f"tip.{s}"], f"hand.{s}", V((sx, 0, 0))),
        (f"thigh.{s}", J[f"hip.{s}"], J[f"knee.{s}"], "hips", V((0, -1, 0))),
        (f"shin.{s}", J[f"knee.{s}"], J[f"ankle.{s}"], f"thigh.{s}", V((0, -1, 0))),
        (f"foot.{s}", J[f"ankle.{s}"], J[f"ball.{s}"], f"shin.{s}", V((0, 0, 1))),
    ]

# The gun, in its own space: +X muzzle, +Y its left, +Z up, origin = top of the
# pistol grip. Where each hand's bone frame sits on it (hand bone: Y = wrist ->
# knuckles, Z = back of the hand).
def frame(origin, y_axis, z_hint):
    y = V(y_axis).normalized()
    x = y.cross(V(z_hint)).normalized()
    z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(origin)
    return m


GRIP_R = frame((-0.072, -0.016, -0.018), (1.0, 0.05, -0.32), (0.0, -1.0, 0.25))
GRIP_L = frame((0.248, 0.062, -0.012), (0.42, -0.9, 0.05), (0.0, 0.25, -1.0))
# Gun -> weapon bone (bone Y along the barrel, bone Z up).
GUN_TO_BONE = Matrix(((0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))


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
log("armature:", len(ARM.data.bones), "bones")

# ====================================================================== garments
MB_SCALE = 1.0 / 0.52  # metaball radius for a wanted surface radius (stiffness 2, threshold 0.6)
MATS = ["skin", "hair", "jacket", "trousers", "shoes", "eye", "inner", "cap", "vest"]
FLAT = {"skin": (0.58, 0.42, 0.32), "hair": (0.03, 0.028, 0.026), "jacket": (0.06, 0.062, 0.066),
        "trousers": (0.12, 0.12, 0.11), "shoes": (0.05, 0.05, 0.05), "eye": (0.8, 0.78, 0.74),
        "inner": (0.03, 0.03, 0.03), "cap": (0.4, 0.05, 0.04), "vest": (0.04, 0.04, 0.04)}
MAT = {}
for i, n in enumerate(MATS):
    m = bpy.data.materials.new(n)
    m.diffuse_color = (*FLAT[n], 1)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*FLAT[n], 1)
    bsdf.inputs["Roughness"].default_value = 0.7
    MAT[n] = m


class Family:
    """One metaball object: its elements blend with each other only."""

    def __init__(self, name, res):
        self.mb = bpy.data.metaballs.new(name)
        self.mb.resolution = res
        self.mb.render_resolution = res
        self.mb.threshold = 0.6
        self.ob = bpy.data.objects.new(name, self.mb)
        COL.objects.link(self.ob)

    def ball(self, p, r, neg=False):
        e = self.mb.elements.new(type="BALL")
        e.co = V(p)
        e.radius = r * MB_SCALE
        e.use_negative = neg
        return e

    def capsule(self, p0, p1, r):
        p0, p1 = V(p0), V(p1)
        e = self.mb.elements.new(type="CAPSULE")
        d = p1 - p0
        e.co = (p0 + p1) / 2
        e.radius = r * MB_SCALE
        e.size_x = max(d.length / 2 - r * 0.35, 0.0005)
        e.rotation = V((1, 0, 0)).rotation_difference(d.normalized())
        return e

    def taper(self, p0, p1, r0, r1, n=4):
        """Chain of balls from p0 (radius r0) to p1 (r1)."""
        p0, p1 = V(p0), V(p1)
        for i in range(n + 1):
            t = i / n
            self.ball(p0.lerp(p1, t), r0 + (r1 - r0) * t)

    def ellipsoid(self, p, radii, rot=None):
        e = self.mb.elements.new(type="ELLIPSOID")
        e.co = V(p)
        e.radius = MB_SCALE
        e.size_x, e.size_y, e.size_z = radii
        if rot is not None:
            e.rotation = rot
        return e


def to_mesh(families, name):
    """Converts metaball families to meshes and joins them."""
    meshes = []
    for fam in families:
        bpy.ops.object.select_all(action="DESELECT")
        fam.ob.select_set(True)
        bpy.context.view_layer.objects.active = fam.ob
        bpy.ops.object.convert(target="MESH")
        ob = bpy.context.active_object
        if ob.type == "MESH" and len(ob.data.polygons) > 0:
            meshes.append(ob)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def apply_mod(ob, kind, **kw):
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(m, k, v)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


def remesh(ob, voxel, smooth=0):
    apply_mod(ob, "REMESH", mode="VOXEL", voxel_size=voxel, adaptivity=0.0, use_smooth_shade=True)
    if smooth:
        apply_mod(ob, "SMOOTH", factor=0.5, iterations=smooth)


def cut(ob, co, no, fill=False, fill_mat=1):
    """Keeps the side of the plane (co, no) that `no` points to. `fill` closes the hole."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=V(co), plane_no=-V(no), clear_outer=True)
    if fill:
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            out = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            for f in out["faces"]:
                f.material_index = fill_mat  # slot 1 = the 'inner' material
    bm.to_mesh(ob.data)
    bm.free()


def keep_where(ob, fn):
    """Deletes faces whose centre fails fn(Vector)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if not fn(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def set_material(ob, name, inner=None):
    ob.data.materials.clear()
    ob.data.materials.append(MAT[name])
    ob.data.materials.append(MAT[inner or "inner"])


# ---------------------------------------------------------------- head, neck, hair, eyes
EYE = {s: V((0.031 * sx, -0.0815, 1.667)) for s, sx in (("L", 1), ("R", -1))}


def head_families(res):
    """Smooth base head (no features): cranium, face mass, jaw, neck, ears."""
    f = Family("skin_head", res)
    f.ellipsoid((0, 0.012, 1.686), (0.074, 0.092, 0.09))            # cranium
    f.ellipsoid((0, -0.03, 1.648), (0.066, 0.066, 0.068))           # face mass
    f.ellipsoid((0, -0.03, 1.598), (0.06, 0.06, 0.045))             # jaw
    f.ellipsoid((0, -0.066, 1.598), (0.036, 0.028, 0.03))           # mouth
    f.ellipsoid((0, -0.064, 1.568), (0.026, 0.022, 0.018))          # chin
    for sx in (1, -1):
        f.ellipsoid((0.048 * sx, -0.012, 1.592), (0.02, 0.03, 0.024))   # jaw angle
        f.ellipsoid((0.08 * sx, 0.01, 1.656), (0.009, 0.024, 0.032),
                    Quaternion((0, 0, 1), math.radians(18 * sx)))   # ears
        f.ellipsoid((0.074 * sx, 0.0, 1.652), (0.008, 0.012, 0.016))  # ear roots
    f.capsule((0, 0.018, 1.44), (0, 0.006, 1.6), 0.054)              # neck
    f.ellipsoid((0, 0.03, 1.46), (0.08, 0.05, 0.03))                 # neck base
    return [f]


# Soft "brushes" that sculpt the face onto the base head: centre, sigma (x, y, z),
# amount (m, + = out along the normal). Nose and lips push toward -Y (forward).
FACE_BRUSHES = [
    ((0, -0.085, 1.692), (0.05, 0.02, 0.009), 0.0035, "n"),   # brow ridge
    ((0, -0.093, 1.712), (0.04, 0.02, 0.02), 0.002, "n"),      # forehead
    ((0, -0.095, 1.676), (0.006, 0.02, 0.008), 0.004, "f"),    # nose root
    ((0, -0.1, 1.652), (0.0065, 0.02, 0.016), 0.011, "f"),     # nose bridge
    ((0, -0.104, 1.629), (0.0105, 0.02, 0.0105), 0.017, "f"),  # nose tip
    ((0, -0.098, 1.618), (0.013, 0.02, 0.006), 0.005, "f"),    # under the nose
    ((0, -0.092, 1.601), (0.019, 0.02, 0.0055), 0.0045, "f"),  # upper lip
    ((0, -0.09, 1.5875), (0.0155, 0.02, 0.005), 0.0048, "f"),  # lower lip
    ((0, -0.091, 1.5945), (0.022, 0.03, 0.0016), -0.0026, "f"),  # mouth line
    ((0, -0.085, 1.578), (0.018, 0.02, 0.005), -0.002, "f"),   # chin crease
    ((0, -0.082, 1.562), (0.017, 0.02, 0.012), 0.005, "n"),    # chin
]
for _sx in (1, -1):
    FACE_BRUSHES += [
        ((0.031 * _sx, -0.088, 1.667), (0.016, 0.03, 0.0105), -0.0075, "n"),  # eye sockets
        ((0.032 * _sx, -0.088, 1.6795), (0.014, 0.03, 0.003), 0.0016, "n"),   # upper lids
        ((0.014 * _sx, -0.096, 1.621), (0.0075, 0.02, 0.0065), 0.0055, "n"),  # nostril wings
        ((0.047 * _sx, -0.062, 1.642), (0.017, 0.02, 0.013), 0.0055, "n"),    # cheekbones
        ((0.04 * _sx, -0.07, 1.612), (0.012, 0.02, 0.016), -0.002, "n"),      # under the cheekbones
        ((0.066 * _sx, -0.035, 1.698), (0.012, 0.02, 0.014), -0.003, "n"),    # temples
        ((0.026 * _sx, -0.083, 1.596), (0.007, 0.02, 0.009), -0.0018, "n"),   # mouth corners
    ]


def sculpt_face(ob):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    nor = np.array([v.vector[:] for v in me.vertex_normals], dtype=np.float64)
    out = co.copy()
    front = np.clip((-co[:, 1] - 0.03) / 0.04, 0.0, 1.0)[:, None]  # brushes act on the face only
    for c, sig, amount, mode in FACE_BRUSHES:
        d = (co - np.array(c)) / np.array(sig)
        w = np.exp(-0.5 * (d * d).sum(1))[:, None] * amount * front
        if mode == "f":
            out += w * np.array((0.0, -1.0, 0.0))
        else:
            out += w * nor
    me.vertices.foreach_set("co", out.ravel())
    me.update()


def build_head(hi):
    res = 0.0025 if hi else 0.004
    ob = to_mesh(head_families(res), "head")
    remesh(ob, 0.0018 if hi else 0.0025)
    sculpt_face(ob)
    apply_mod(ob, "SMOOTH", factor=0.4, iterations=2)
    if not hi:
        remesh(ob, 0.0032)
    cut(ob, (0, 0, 1.43), (0, 0, 1))
    set_material(ob, "skin")
    return ob


def build_hair(hi):
    f = Family("hair", 0.003 if hi else 0.005)
    f.ellipsoid((0, 0.009, 1.688), (0.081, 0.099, 0.0935))
    f.ellipsoid((0, 0.03, 1.66), (0.079, 0.09, 0.07))
    ob = to_mesh([f], "hair")
    remesh(ob, 0.003 if hi else 0.004)

    def ss(t):
        t = min(max(t, 0.0), 1.0)
        return t * t * (3 - 2 * t)

    def keep(p):
        front = ss((-p.y - 0.03) / 0.05)
        back = ss((p.y - 0.03) / 0.07)
        center = 1.0 - ss((abs(p.x) - 0.03) / 0.035)
        return p.z > 1.69 + front * (0.02 + 0.028 * center) - back * 0.07

    keep_where(ob, keep)
    set_material(ob, "hair")
    return ob


def build_eyes():
    obs = []
    for s, c in EYE.items():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=0.0122)
        bmesh.ops.translate(bm, verts=bm.verts, vec=c)
        me = bpy.data.meshes.new(f"eye_{s}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"eye_{s}", me)
        COL.objects.link(ob)
        me.shade_smooth()
        set_material(ob, "eye")
        obs.append(ob)
    return obs


# ---------------------------------------------------------------- hands (built in the hand bone's frame)
def hand_frame(s):
    return REST[f"hand.{s}"]


def build_hand(s, hi):
    m = hand_frame(s)
    sx = 1.0 if s == "L" else -1.0
    thumb = V((sx, 0, 0))  # thumb side in the hand frame (+X left hand, -X right hand)
    f = Family(f"hand{s}", 0.0022 if hi else 0.0035)

    def P(x, y, z):
        return m @ V((x, y, z))

    f.ellipsoid(P(0.0, 0.045, -0.002), (0.039, 0.05, 0.0145))      # palm
    f.ellipsoid(P(0.0, 0.004, 0.0), (0.03, 0.025, 0.02))           # heel of the hand / wrist
    f.capsule(P(0, -0.07, 0.0), P(0, 0.0, 0.0), 0.026)             # wrist (under the cuff)
    # Fingers: index (thumb side) to pinky, curled around a grip.
    spread = [0.027, 0.009, -0.009, -0.025]
    lengths = [(0.042, 0.025, 0.02), (0.046, 0.028, 0.021), (0.043, 0.026, 0.02), (0.034, 0.02, 0.018)]
    radii = [0.0092, 0.0095, 0.009, 0.008]
    curl = [math.radians(a) for a in (48, 62, 42)]
    for i in range(4):
        base = V((thumb.x * spread[i], 0.086, -0.002))
        d = V((thumb.x * 0.04 * (i - 1.5) / 1.5, 1, 0)).normalized()
        ang = 0.0
        p = base
        for k in range(3):
            ang += curl[k]
            # Curl toward the palm (-Z) around the hand's X axis.
            dk = (Matrix.Rotation(-ang, 3, V((1, 0, 0))) @ d).normalized()
            q = p + dk * lengths[i][k]
            f.capsule(P(*p), P(*q), radii[i] * (1.0 - 0.08 * k))
            p = q
    # Thumb: from the base of the palm, along the grip's side.
    t0 = V((thumb.x * 0.028, 0.012, -0.012))
    t1 = t0 + V((thumb.x * 0.016, 0.03, -0.016))
    t2 = t1 + V((thumb.x * 0.004, 0.026, -0.012))
    t3 = t2 + V((-thumb.x * 0.004, 0.02, -0.008))
    f.capsule(P(*t0), P(*t1), 0.0125)
    f.capsule(P(*t1), P(*t2), 0.0105)
    f.capsule(P(*t2), P(*t3), 0.0095)
    ob = to_mesh([f], f"hand_{s}")
    remesh(ob, 0.0022 if hi else 0.0032)
    set_material(ob, "skin")
    return ob


# ---------------------------------------------------------------- jacket (bomber)
HEM_Z = 0.925
COLLAR_Z = 1.462


def cuff_plane(s):
    """Plane across the forearm just above the wrist (point, direction toward the elbow)."""
    e, w = J[f"elbow.{s}"], J[f"wrist.{s}"]
    d = (e - w).normalized()
    return w + d * 0.012, d


def build_jacket(hi):
    res = 0.005 if hi else 0.007
    torso = Family("jacket_torso", res)
    torso.ellipsoid((0, 0.008, 0.99), (0.172, 0.12, 0.11))
    torso.ellipsoid((0, -0.004, 1.13), (0.168, 0.122, 0.12))
    torso.ellipsoid((0, -0.008, 1.29), (0.188, 0.13, 0.13))
    torso.ellipsoid((0, 0.012, 1.395), (0.198, 0.112, 0.075))
    torso.ellipsoid((0, 0.026, 1.44), (0.1, 0.07, 0.045))           # trapezius / collar base
    for sx in (1, -1):
        torso.ball((0.172 * sx, 0.016, 1.405), 0.066)                # shoulder caps
    fams = [torso]
    for s in ("L", "R"):
        sl = Family(f"jacket_sleeve{s}", res)
        sh, el, wr = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"]
        sl.taper(sh + (sh - el).normalized() * 0.01, el, 0.064, 0.054, 5)
        sl.taper(el, wr + (wr - el).normalized() * 0.03, 0.053, 0.044, 5)
        fams.append(sl)
    ob = to_mesh(fams, "jacket")
    remesh(ob, 0.0045 if hi else 0.006, smooth=3)
    set_material(ob, "jacket")
    cut(ob, (0, 0, HEM_Z), (0, 0, 1), fill=True)
    for s in ("L", "R"):
        co, d = cuff_plane(s)
        # Restrict the cuff cut to the forearm: a plane through the wrist only.
        _cut_near(ob, co, d, J[f"wrist.{s}"], 0.12, fill=True)
    # Neck opening.
    keep_where(ob, lambda p: not (p.z > COLLAR_Z - 0.008 and (p.x * p.x + (p.y - 0.012) ** 2) < 0.068 ** 2))
    return ob


def _cut_near(ob, co, keep_dir, center, radius, fill=False):
    """Bisects only geometry within `radius` of `center`; deletes the far side there."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    near = [f for f in bm.faces if (f.calc_center_median() - center).length < radius]
    verts = {v for f in near for v in f.verts}
    edges = {e for f in near for e in f.edges}
    res = bmesh.ops.bisect_plane(bm, geom=list(verts) + list(edges) + near, dist=1e-6,
                                 plane_co=V(co), plane_no=V(keep_dir))
    dead = [f for f in bm.faces if (f.calc_center_median() - center).length < radius
            and (f.calc_center_median() - V(co)).dot(V(keep_dir)) < 0]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    if fill:
        edges = [e for e in bm.edges if e.is_boundary and abs((e.verts[0].co - V(co)).dot(V(keep_dir))) < 1e-4
                 and (e.verts[0].co - center).length < radius]
        if edges:
            out = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            for f in out["faces"]:
                f.material_index = 1
    bm.to_mesh(ob.data)
    bm.free()


def build_collar(hi):
    """Rib-knit band round the neck opening (a short tapered tube, closed on its inside)."""
    bm = bmesh.new()
    n = 40 if hi else 22
    rings = []
    for z, r, dy in ((COLLAR_Z - 0.03, 0.092, 0.018), (COLLAR_Z + 0.012, 0.08, 0.018),
                     (COLLAR_Z + 0.04, 0.069, 0.018), (COLLAR_Z + 0.04, 0.062, 0.018),
                     (COLLAR_Z - 0.005, 0.064, 0.016)):
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ring.append(bm.verts.new((r * math.cos(a), dy + r * 1.08 * math.sin(a), z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(n):
            a, b = rings[k][i], rings[k][(i + 1) % n]
            c, d = rings[k + 1][(i + 1) % n], rings[k + 1][i]
            bm.faces.new((a, b, c, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("collar")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("collar", me)
    COL.objects.link(ob)
    me.shade_smooth()
    if hi:
        apply_mod(ob, "SUBSURF", levels=1)
    set_material(ob, "jacket")
    return ob


# ---------------------------------------------------------------- trousers and shoes
def build_trousers(hi):
    res = 0.006 if hi else 0.008
    pelvis = Family("trousers_pelvis", res)
    pelvis.ellipsoid((0, 0.01, 0.96), (0.163, 0.114, 0.105))
    pelvis.ellipsoid((0, 0.03, 0.9), (0.15, 0.1, 0.07))              # seat
    fams = [pelvis]
    for s in ("L", "R"):
        leg = Family(f"trousers_leg{s}", res)
        hp, kn, an = J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"]
        leg.taper(hp + V((0, 0, 0.02)), kn, 0.092, 0.064, 6)
        leg.taper(kn, an + V((0, -0.005, 0.0)), 0.062, 0.054, 6)
        fams.append(leg)
    ob = to_mesh(fams, "trousers")
    remesh(ob, 0.005 if hi else 0.007, smooth=3)
    cut(ob, (0, 0, 1.06), (0, 0, -1))
    cut(ob, (0, 0, 0.118), (0, 0, 1))
    set_material(ob, "trousers")
    return ob


def build_shoe(s, hi):
    sx = 1.0 if s == "L" else -1.0
    x = J[f"ankle.{s}"].x
    f = Family(f"shoe{s}", 0.004 if hi else 0.006)
    f.ellipsoid((x, 0.03, 0.045), (0.044, 0.05, 0.05))               # heel
    f.ellipsoid((x + 0.004 * sx, -0.045, 0.04), (0.047, 0.065, 0.04))  # midfoot
    f.ellipsoid((x + 0.006 * sx, -0.12, 0.032), (0.043, 0.045, 0.03))  # toe box
    f.capsule((x, 0.02, 0.06), (x, 0.022, 0.135), 0.05)               # ankle collar
    ob = to_mesh([f], f"shoe_{s}")
    remesh(ob, 0.004 if hi else 0.0055, smooth=2)
    cut(ob, (0, 0, 0.0), (0, 0, 1), fill=True, fill_mat=0)
    cut(ob, (0, 0, 0.14), (0, 0, -1))
    set_material(ob, "shoes")
    return ob


# ---------------------------------------------------------------- plate carrier (Enforcer)
def build_vest(hi):
    res = 0.006 if hi else 0.009
    f = Family("vest", res)
    f.ellipsoid((0, -0.012, 1.25), (0.19, 0.142, 0.17))
    f.ellipsoid((0, -0.02, 1.09), (0.178, 0.136, 0.07))
    ob = to_mesh([f], "vest")
    remesh(ob, 0.006 if hi else 0.009, smooth=2)
    # Front and back plates with open sides; shoulder straps stay.
    def keep(p):
        if p.z < 1.0 or p.z > 1.44:
            return False
        side = abs(p.x) > 0.15 and abs(p.y + 0.01) < 0.06
        armhole = abs(p.x) > 0.11 and p.z > 1.34 and abs(p.y + 0.01) < 0.11
        strap = abs(abs(p.x) - 0.1) < 0.03
        return not side and (not armhole or strap)
    keep_where(ob, keep)
    apply_mod(ob, "SOLIDIFY", thickness=0.012, offset=1.0)
    set_material(ob, "vest")
    return ob


def build_all(hi):
    parts = [build_head(hi), build_hair(hi), build_jacket(hi), build_collar(hi), build_trousers(hi)]
    parts += build_eyes()
    for s in ("L", "R"):
        parts.append(build_hand(s, hi))
        parts.append(build_shoe(s, hi))
    return parts


def join(obs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
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


def decimate(ob, target_tris):
    ob.data.calc_loop_triangles()
    n = len(ob.data.loop_triangles)
    if n > target_tris:
        apply_mod(ob, "DECIMATE", ratio=target_tris / n)


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


# Budgets (LOW): the whole man ~10k triangles.
LOW_BUDGET = {"head": 2300, "hair": 700, "jacket": 2700, "collar": 300, "trousers": 1700,
              "hand_L": 750, "hand_R": 750, "shoe_L": 360, "shoe_R": 360, "vest": 700}


def build_detail(hi):
    parts = build_all(hi)
    vest = build_vest(hi)
    if not hi:
        for ob in parts + [vest]:
            if ob.name in LOW_BUDGET:
                decimate(ob, LOW_BUDGET[ob.name])
    body = join(parts, "triad_high" if hi else "triad")
    body.data.shade_smooth()
    vest.data.materials.clear()
    for n in MATS:
        vest.data.materials.append(MAT[n])
    for p in vest.data.polygons:
        p.material_index = MATS.index("vest")
    vest.name = "vest_high" if hi else "vest"
    vest.data.shade_smooth()
    return body, vest


log("building LOW")
LOW, VEST = build_detail(False)
log(f"LOW: {tris(LOW)} tris, vest {tris(VEST)}")
if not args.fast:
    log("building HIGH")
    HIGH, VEST_HIGH = build_detail(True)
    log(f"HIGH: {tris(HIGH)} tris")


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


log("weights")
compute_weights(LOW, finger_labels(LOW))
bind(LOW)
compute_weights(VEST)
bind(VEST)


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
CAP_UV = (0.95, 0.05, 0.045)  # disc in the reserved strip (u > 0.9): centre u, v, radius


def unwrap(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    # More texels for the face and hands.
    for ob in objs:
        uv = ob.data.uv_layers.active.data
        for poly in ob.data.polygons:
            name = MATS[poly.material_index]
            c = poly.center
            k = 1.0
            if name in ("skin", "eye") and c.z > 1.54 and c.y < 0.0:
                k = 2.4
            elif name in ("skin", "eye", "hair"):
                k = 1.4
            if k != 1.0:
                for li in poly.loop_indices:
                    uv[li].uv = uv[li].uv * k
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    for ob in objs:
        uv = ob.data.uv_layers.active.data
        a = np.empty(len(uv) * 2)
        uv.foreach_get("uv", a)
        a = a.reshape(-1, 2)
        a[:, 0] *= 0.9  # free a strip on the right for the flesh caps
        uv.foreach_set("uv", a.ravel())


def _bake_targets(img):
    for m in MAT.values():
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


def bake_maps(size):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake")
    low = [LOW, VEST]
    maps = {}

    def bake_self(kind, img, samples, btype="EMIT"):
        bpy.ops.object.select_all(action="DESELECT")
        for ob in low:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = LOW
        _bake_targets(img)
        scene.cycles.samples = samples
        bpy.ops.object.bake(type=btype, margin=6, use_clear=True)

    for kind in ("pos", "nor", "matid"):
        img = bpy.data.images.new(f"triad_{kind}", size, size, alpha=True, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        _emit(kind)
        bake_self(kind, img, 1)
        maps[kind] = px(img)
        log(f"baked {kind}")
    _restore()
    ao = bpy.data.images.new("triad_ao_raw", size, size, alpha=False, float_buffer=True)
    ao.colorspace_settings.name = "Non-Color"
    scene.world.light_settings.distance = 0.12
    # The HIGH meshes sit on the same surface, and the vest would shade the
    # whole torso: keep them out of the AO rays.
    _bake_targets(ao)
    scene.cycles.samples = 24
    for ob, hidden in ((LOW, (HIGH, VEST_HIGH, VEST)), (VEST, (HIGH, VEST_HIGH))):
        for h in hidden:
            h.hide_render = True
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(type="AO", margin=6, use_clear=(ob is LOW))
        for h in hidden:
            h.hide_render = False
    maps["ao"] = px(ao)[:, :, 0]
    log("baked ao")
    nimg = bpy.data.images.new("triad_normal", size, size, alpha=False)
    nimg.colorspace_settings.name = "Non-Color"
    _bake_targets(nimg)
    scene.cycles.samples = 4
    first = True
    for hi, lo in ((HIGH, LOW), (VEST_HIGH, VEST)):
        bpy.ops.object.select_all(action="DESELECT")
        hi.select_set(True)
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo
        bpy.ops.object.bake(type="NORMAL", use_selected_to_active=True, cage_extrusion=0.004,
                            max_ray_distance=0.014, margin=6, use_clear=first)
        first = False
    log("baked normal")
    maps["normal_img"] = nimg
    return maps


# ---------------------------------------------------------------- numpy painting
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFF).astype(np.float32) / 65535.0


def vnoise(P, freq, seed=0):
    q = P * freq
    i = np.floor(q).astype(np.int64)
    f = (q - i).astype(np.float32)
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, freq, octaves=4, seed=0):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * vnoise(P, freq * (2 ** o), seed + o)
        norm += amp
        amp *= 0.5
    return total / norm


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def line(d, width):
    """1 on a line of half-width `width` at d = 0, soft edge."""
    return 1.0 - sstep(width * 0.5, width, np.abs(d))


def paint(maps, size):
    pos = maps["pos"]
    cover = pos[:, :, 3] > 0.5
    P = (pos[:, :, :3][cover].astype(np.float64) - np.array((0.5, 0.5, 0.0))) * 2.0
    Nn = (maps["nor"][:, :, :3][cover].astype(np.float64) - 0.5) * 2.0
    mid = np.clip((maps["matid"][:, :, 0][cover] * 16.0).astype(np.int32), 0, len(MATS) - 1)
    ao = maps["ao"][cover]
    n = len(P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    base = np.zeros((n, 3))
    rough = np.full(n, 0.7)
    metal = np.zeros(n)
    mask = np.zeros((n, 3))
    M = {m: mid == MATS.index(m) for m in MATS}
    grain = fbm(P, 180.0, 3, 1)
    fine = vnoise(P, 900.0, 7)

    # Skin.
    sk = M["skin"]
    skin = np.array((0.76, 0.58, 0.45)) * (0.94 + 0.1 * grain[:, None]) * (0.97 + 0.06 * fine[:, None])
    face = (z > 1.54) & (y < -0.02)
    cheeks = np.exp(-(((np.abs(x) - 0.042) / 0.02) ** 2 + ((z - 1.632) / 0.018) ** 2)) * face
    skin = skin + cheeks[:, None] * np.array((0.04, -0.01, -0.015))
    ears = (np.abs(x) > 0.07) & (z > 1.62) & (z < 1.7) & (np.abs(y) < 0.04)
    skin = skin + ears[:, None] * np.array((0.04, -0.015, -0.02))
    lips = face & (np.abs(x) < 0.021 - 25 * (z - 1.594) ** 2) & (z > 1.581) & (z < 1.606) & (y < -0.085)
    skin = np.where(lips[:, None], skin * np.array((0.88, 0.7, 0.68)), skin)
    mouth = face & line(z - 1.5945, 0.0012) .astype(bool) & (np.abs(x) < 0.02) & (y < -0.085)
    skin = np.where(mouth[:, None], skin * 0.45, skin)
    # Stubble on the jaw, chin and upper lip.
    jaw = face & (z < 1.625) & (np.abs(x) < 0.07) & ~lips
    stub = jaw * sstep(1.63, 1.6, z) * (0.6 + 0.4 * vnoise(P, 1500.0, 3))
    skin = skin * (1 - 0.22 * stub[:, None]) + stub[:, None] * np.array((0.02, 0.02, 0.03))
    # Eyebrows.
    for sx in (1, -1):
        bx = x * sx
        centre = 1.6875 + 0.006 * np.cos(np.clip((bx - 0.031) / 0.024, -1.5, 1.5)) - 0.003
        width = 0.0042 * (1.0 - 0.5 * sstep(0.03, 0.055, bx))
        brow = face & (bx > 0.011) & (bx < 0.056) & (np.abs(z - centre) < width) & (y < -0.07)
        brow_n = brow & (vnoise(P, 2200.0, 11 + sx) > 0.25)
        skin = np.where(brow_n[:, None], np.array((0.07, 0.055, 0.05)), skin)
        # Lash line round the eye opening.
        e = np.array(EYE["L" if sx > 0 else "R"][:])
        de = np.linalg.norm(P - e, axis=1)
        lash = face & (de < 0.0152) & (de > 0.0118) & (z > e[2] - 0.004)
        skin = np.where(lash[:, None], skin * 0.35, skin)
    base[sk] = skin[sk]
    rough[sk] = np.where(lips[sk], 0.4, 0.55)
    mask[sk, 2] = 1.0

    # Eyes: sclera, iris and pupil looking forward (-Y).
    ey = M["eye"]
    eye_col = np.tile(np.array((0.86, 0.84, 0.8)), (n, 1))
    for s in ("L", "R"):
        e = np.array(EYE[s][:])
        d = P - e
        d = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
        ang = np.degrees(np.arccos(np.clip(-d[:, 1], -1, 1)))
        near = np.linalg.norm(P - e, axis=1) < 0.02
        eye_col = np.where((near & (ang < 30))[:, None], np.array((0.17, 0.1, 0.06)), eye_col)
        eye_col = np.where((near & (ang < 13))[:, None], np.array((0.02, 0.02, 0.02)), eye_col)
    base[ey] = eye_col[ey]
    rough[ey] = 0.12

    # Hair: dark, combed streaks, a fade on the sides and back.
    hr = M["hair"]
    streak = vnoise(P * np.array((3.0, 0.4, 1.0)), 700.0, 21)
    hair = np.array((0.045, 0.038, 0.034))[None, :] * (0.7 + 0.6 * streak[:, None])
    front = sstep(0.03, 0.08, -y)
    back = sstep(0.03, 0.1, y)
    centre = 1.0 - sstep(0.03, 0.065, np.abs(x))
    line_z = 1.69 + front * (0.02 + 0.028 * centre) - back * 0.07
    fade = sstep(0.0, 0.035, z - line_z) * (1 - front) + front
    hair = hair * fade[:, None] + (1 - fade[:, None]) * np.array((0.36, 0.3, 0.27))
    base[hr] = hair[hr]
    rough[hr] = 0.62

    # Jacket: neutral grey (tinted per role in the game), rib knit, zip, seams.
    jk = M["jacket"]
    jac = 0.5 * (0.93 + 0.12 * grain) * (0.97 + 0.05 * fine)
    jr = np.full(n, 0.5)
    rib = np.zeros(n, dtype=bool)
    hem = z < HEM_Z + 0.055
    collar = (z > 1.44) & (np.sqrt(x * x + (y - 0.015) ** 2) < 0.1)
    rib |= hem | collar
    ang_t = np.arctan2(y, x)
    rib_s = 0.5 + 0.5 * np.sin(ang_t * 0.16 / 0.0035)
    for s in ("L", "R"):
        co, d = cuff_plane(s)
        co, d = np.array(co[:]), np.array(d[:])
        along = (P - co) @ d
        radial = P - co - along[:, None] * d
        cuff = (along > -0.01) & (along < 0.06) & (np.linalg.norm(radial, axis=1) < 0.08)
        rib |= cuff
        ref = np.cross(d, (0, 0, 1))
        ref /= np.linalg.norm(ref)
        a = np.arctan2(radial @ np.cross(d, ref), radial @ ref)
        rib_s = np.where(cuff, 0.5 + 0.5 * np.sin(a * 0.05 / 0.0035), rib_s)
    jac = np.where(rib, jac * (0.78 + 0.16 * rib_s), jac)
    jr = np.where(rib, 0.88, jr)
    # Zip down the front, with a placket shadow either side.
    zip_zone = (np.abs(x) < 0.0105) & (y < -0.04) & (z > HEM_Z) & (z < 1.47) & ~collar
    teeth = zip_zone & (np.abs(x) < 0.0032)
    tooth_s = 0.5 + 0.5 * np.sin(z / 0.0022 * math.pi)
    jac = np.where(zip_zone & ~teeth, jac * 0.62, jac)
    jac = np.where(teeth, 0.32 + 0.18 * tooth_s, jac)
    metal_zip = teeth
    # Seams: sides, shoulders, armholes.
    side = line(y - 0.005, 0.0022) * (np.abs(x) > 0.11) * (z < 1.36) * ~rib
    shoulder = line(y - 0.02, 0.0022) * (z > 1.4) * (np.abs(x) > 0.07) * (np.abs(x) < 0.2)
    seams = np.maximum(side, shoulder)
    for s in ("L", "R"):
        sh = np.array(J[f"shoulder.{s}"][:])
        seams = np.maximum(seams, line(np.linalg.norm(P - sh, axis=1) - 0.072, 0.0022) * (np.abs(x) > 0.12))
    stitch = 0.6 + 0.4 * (np.sin((x + y + z) / 0.003 * math.pi) > 0)
    jac = jac * (1 - 0.45 * seams * stitch)
    base[jk] = np.repeat(jac[jk][:, None], 3, axis=1)
    rough[jk] = jr[jk]
    metal[jk & metal_zip] = 0.7
    rough[jk & metal_zip] = 0.35
    mask[jk, 0] = np.where(metal_zip[jk], 0.0, 1.0)

    # Trousers: twill, cargo pockets on the outer thighs.
    tr = M["trousers"]
    twill = 0.5 + 0.5 * np.sin((x * 0.7 + z) / 0.0016 * math.pi)
    tro = 0.5 * (0.92 + 0.12 * grain) * (0.96 + 0.05 * twill)
    out_side = np.zeros(n, dtype=bool)
    for s, sx in (("L", 1.0), ("R", -1.0)):
        hipx = J[f"hip.{s}"].x
        outer = (x * sx > abs(hipx) + 0.035)
        pocket = outer & (z > 0.52) & (z < 0.72) & (y > -0.06) & (y < 0.05)
        edge = pocket & ((np.abs(z - 0.52) < 0.003) | (np.abs(z - 0.72) < 0.003) | (np.abs(y + 0.06) < 0.003)
                         | (np.abs(y - 0.05) < 0.003) | (np.abs(z - 0.69) < 0.0022))
        tro = np.where(pocket, tro * 1.05, tro)
        tro = np.where(edge, tro * 0.6, tro)
        out_side |= outer
    tro = np.where(z < 0.135, tro * 0.85, tro)
    base[tr] = np.repeat(tro[tr][:, None], 3, axis=1)
    rough[tr] = 0.86
    mask[tr, 1] = 1.0

    # Shoes: black uppers, white cupsoles, laces.
    sh = M["shoes"]
    upper = np.array((0.055, 0.055, 0.058)) * (0.85 + 0.3 * vnoise(P, 1200.0, 31)[:, None])
    sole = z < 0.027
    stripe = line(z - 0.027, 0.0016)
    shoe = np.where(sole[:, None], np.array((0.82, 0.8, 0.76)) * (0.95 + 0.05 * grain[:, None]), upper)
    shoe = shoe * (1 - 0.5 * stripe[:, None])
    for s in ("L", "R"):
        cx = J[f"ankle.{s}"].x + 0.004 * (1 if s == "L" else -1)
        lace = (np.abs(x - cx) < 0.014) & (y > -0.095) & (y < 0.0) & (Nn[:, 2] > 0.55) & (z > 0.05)
        bars = lace & (np.sin(y / 0.0075 * math.pi) > 0.1)
        shoe = np.where(bars[:, None], np.array((0.42, 0.42, 0.42)), shoe)
    base[sh] = shoe[sh]
    rough[sh] = np.where(sole[sh], 0.8, 0.55)

    # Plate carrier: black nylon with MOLLE webbing rows.
    vs = M["vest"]
    vest = 0.05 * (0.9 + 0.2 * grain)
    row = (np.mod(z - 1.05, 0.038) < 0.025) & (np.abs(x) < 0.15) & (z < 1.36)
    slot = row & (np.mod(x + 0.5, 0.038) < 0.004)
    vest = np.where(row, vest * 1.6, vest)
    vest = np.where(slot, vest * 0.4, vest)
    base[vs] = np.repeat(vest[vs][:, None], 3, axis=1)
    rough[vs] = 0.8

    inn = M["inner"]
    base[inn] = 0.035
    rough[inn] = 0.95

    # Cavity grime from AO.
    base = base * (0.55 + 0.45 * ao[:, None])

    out_base = np.zeros((size, size, 4), dtype=np.float32)
    out_base[..., 3] = 1
    out_base[cover, :3] = np.clip(base, 0, 1)
    out_orm = np.ones((size, size, 4), dtype=np.float32)
    out_orm[cover, 0] = ao
    out_orm[cover, 1] = rough
    out_orm[cover, 2] = metal
    out_mask = np.zeros((size, size, 4), dtype=np.float32)
    out_mask[..., 3] = 1
    out_mask[cover, :3] = mask
    paint_cap(out_base, out_orm, size)
    return out_base, out_orm, out_mask


def paint_cap(out_base, out_orm, size):
    """The flesh cap disc in the reserved strip: skin edge, fat, muscle, bone."""
    cu, cv, cr = CAP_UV
    u = (np.arange(size) + 0.5) / size
    U, Vv = np.meshgrid(u, u)
    r = np.sqrt((U - cu) ** 2 + (Vv - cv) ** 2) / cr
    zone = r < 1.15
    P3 = np.stack([U * 3, Vv * 3, np.zeros_like(U)], -1).reshape(-1, 3)
    nz = fbm(P3, 60.0, 3, 41).reshape(size, size)
    muscle = np.stack([0.42 + 0.12 * nz, 0.05 + 0.03 * nz, 0.045 + 0.02 * nz], -1)
    col = muscle
    col = np.where((r > 0.84)[..., None], np.array((0.78, 0.66, 0.42)), col)
    col = np.where((r > 0.93)[..., None], np.array((0.3, 0.12, 0.1)), col)
    col = np.where((r < 0.27)[..., None], np.array((0.84, 0.8, 0.7)), col)
    col = np.where((r < 0.12)[..., None], np.array((0.35, 0.05, 0.04)), col)
    col = np.where(((r > 0.27) & (r < 0.33))[..., None], np.array((0.25, 0.02, 0.02)), col)
    out_base[zone, :3] = col[zone]
    out_orm[zone, 1] = 0.22
    out_orm[zone, 2] = 0.0


def save_png(arr, name, tex_dir, non_color):
    size = arr.shape[0]
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    img.pixels.foreach_set(arr.ravel())
    img.filepath_raw = os.path.join(tex_dir, f"{name}.png")
    img.file_format = "PNG"
    img.save()
    img.filepath = img.filepath_raw
    return img


def game_material(tex):
    mat = bpy.data.materials.new("triad")
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]

    def img(i):
        node = N.new("ShaderNodeTexImage")
        node.image = i
        return node
    L.new(img(tex["basecolor"]).outputs["Color"], bsdf.inputs["Base Color"])
    sep = N.new("ShaderNodeSeparateColor")
    L.new(img(tex["orm"]).outputs["Color"], sep.inputs["Color"])
    L.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    L.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nmap = N.new("ShaderNodeNormalMap")
    L.new(img(tex["normal"]).outputs["Color"], nmap.inputs["Color"])
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    mat.use_backface_culling = True
    return mat


def flat_textures(size):
    """--fast: tiny flat-colour atlas so the export still works."""
    return None


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


def split_parts(src):
    """Cuts the severable parts out of `src` (same UVs and weights) and caps every cut.

    Parts nest (hand < forearm < upper arm < body; shin < thigh < body): each
    cut is capped on both sides, on the part it frees and on its parent.
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
        uvl = b2.loops.layers.uv.active
        for name, co, no, centre, radius, reach, prad, parent, bones in specs:
            if part not in (parent, name):
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
        me = bpy.data.meshes.new(f"part_{part}")
        b2.to_mesh(me)
        b2.free()
        ob = bpy.data.objects.new(f"part_{part}", me)
        COL.objects.link(ob)
        for vg in src.vertex_groups:
            ob.vertex_groups.new(name=vg.name)
        ob.data.materials.clear()
        for m in src.data.materials:
            ob.data.materials.append(m)
        me.shade_smooth()
        bind(ob)
        me_parts[part] = ob
        log(f"part {part}: {tris(ob)} tris")
    bm.free()
    return me_parts


def preview_split(path):
    """Exploded view: every part pushed out along its cut, rendered from the front and the side."""
    specs = {sp[0]: sp for sp in cut_specs()}
    saved = {}
    for name, ob in PARTS.items():
        if name == "body":
            continue
        off = V((0, 0, 0))
        n = name
        while n in specs:
            off += specs[n][2] * 0.12
            n = specs[n][7]
        saved[name] = ob.location.copy()
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
    for name, loc in saved.items():
        PARTS[name].location = loc
    LOW.hide_render = False


# ====================================================================== export
def export(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ARM.select_set(True)
    for ob in [LOW, VEST] + list(PARTS.values()):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = ARM
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=False, export_skins=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True,
                              export_frame_range=False, export_tangents=True, export_image_format="AUTO")
    log("exported", path)


PARTS = {}
TEX_DIR = os.path.join(os.path.dirname(args.out), "textures") if args.out else ""
unwrap([LOW, VEST])
if not args.fast:
    maps = bake_maps(args.tex)
    b, orm, msk = paint(maps, args.tex)
    tex = {"basecolor": save_png(b, "triad_basecolor", TEX_DIR, False),
           "orm": save_png(orm, "triad_orm", TEX_DIR, True),
           "mask": save_png(msk, "triad_mask", TEX_DIR, True)}
    nimg = maps["normal_img"]
    nimg.filepath_raw = os.path.join(TEX_DIR, "triad_normal.png")
    nimg.file_format = "PNG"
    nimg.save()
    nimg.filepath = nimg.filepath_raw
    tex["normal"] = nimg
    gm = game_material(tex)
    for ob in (LOW, VEST):
        mi = np.zeros(len(ob.data.polygons), dtype=np.int32)
        ob.data.polygons.foreach_get("material_index", mi)
        ob.data.materials.clear()
        ob.data.materials.append(gm)
        ob.data.polygons.foreach_set("material_index", np.zeros_like(mi))
        ob.data.update()
        ob["mat_ids"] = mi.tolist()
    for o in (HIGH, VEST_HIGH):
        bpy.data.objects.remove(o)
    log("textures saved")
PARTS = split_parts(LOW)
if not args.fast:
    for ob in PARTS.values():
        ob.data.materials.clear()
        ob.data.materials.append(gm)
        for p_ in ob.data.polygons:
            p_.material_index = 0
LOW.name = "triad"
if args.out:
    export(args.out)


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


def preview_poses(prefix, guns):
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


if args.split_preview:
    preview_split(args.split_preview)
if args.preview:
    os.makedirs(os.path.dirname(args.preview) or ".", exist_ok=True)
    GUNS = import_guns()
    setup_render(args.samples, 420, 600)
    VEST.hide_render = True
    if BAKED:
        preview_poses(args.preview, GUNS)
log("done")
