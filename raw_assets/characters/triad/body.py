"""The triad man's own body (no clothes): torso and limbs, head, eyes, hands.

Built from metaball families (torso, each arm, each leg) unioned by a voxel
remesh. HIGH adds muscle definition (pecs, abs, deltoids, forearm veins,
knees, spine) as small displacements along the normals; it's only used to
bake the normal map onto LOW. Clothes (wardrobe.py) are shells over this
body, so everything a garment doesn't cover is skin, ready for tattoos.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

from common import (J, V, Family, apply_mod, cut, keep_where, remesh, set_material, to_mesh, verts_np,
                    set_verts_np, arm_coord, leg_coord, regions, ss)
import common

# ---------------------------------------------------------------- torso and limbs


def body_families(res):
    t = Family("body_torso", res)
    t.ellipsoid((0, 0.016, 0.955), (0.132, 0.096, 0.09))           # pelvis
    for sx in (1, -1):
        t.ellipsoid((0.058 * sx, 0.052, 0.91), (0.058, 0.055, 0.075))   # glutes
    t.ellipsoid((0, 0.006, 1.06), (0.128, 0.09, 0.10))             # waist
    t.ellipsoid((0, -0.004, 1.17), (0.146, 0.1, 0.10))             # lower ribcage
    t.ellipsoid((0, 0.002, 1.3), (0.162, 0.108, 0.12))             # upper ribcage
    t.ellipsoid((0, -0.046, 1.12), (0.08, 0.048, 0.12))            # abdomen
    for sx in (1, -1):
        t.ellipsoid((0.07 * sx, -0.064, 1.335), (0.074, 0.042, 0.06))   # pecs
        t.ellipsoid((0.124 * sx, 0.028, 1.27), (0.05, 0.066, 0.11))     # lats
        t.ellipsoid((0.068 * sx, 0.062, 1.33), (0.066, 0.038, 0.09))    # shoulder blades
        t.ellipsoid((0.07 * sx, 0.03, 1.415), (0.07, 0.05, 0.034),
                    Quaternion((0, 1, 0), math.radians(-14 * sx)))      # trapezius, sloping
        t.ball((0.148 * sx, 0.012, 1.375), 0.054)                       # shoulder joint
    t.ellipsoid((0, 0.026, 1.44), (0.056, 0.046, 0.036))           # neck base
    fams = [t]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        a = Family(f"body_arm{s}", res)
        sh, el, wr, kn = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"], J[f"knuckle.{s}"]
        a.along(sh, el, 0.1, (0.052, 0.058, 0.075), off=(0.01 * sx, 0.0, -0.004))   # deltoid
        a.cone(sh, el, 0.042, 0.034)
        a.along(sh, el, 0.5, (0.03, 0.032, 0.08), off=(0, -0.014, 0))      # biceps
        a.along(sh, el, 0.42, (0.03, 0.03, 0.085), off=(0, 0.014, 0))      # triceps
        a.ball(el, 0.032)
        a.cone(el, wr, 0.036, 0.024)
        a.along(el, wr, 0.25, (0.036, 0.031, 0.07))                        # forearm muscles
        a.capsule(wr, wr + (kn - wr) * 0.5, 0.022)                          # into the hand
        fams.append(a)
        g = Family(f"body_leg{s}", res)
        hp, kn_, an = J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"]
        g.cone(hp + V((0, 0, 0.03)), kn_, 0.074, 0.05)
        g.along(hp, kn_, 0.45, (0.05, 0.046, 0.16), off=(0.004 * sx, -0.016, 0))     # quads
        g.along(hp, kn_, 0.5, (0.046, 0.044, 0.15), off=(0, 0.018, 0))               # hamstrings
        g.ball(kn_, 0.044)
        g.ellipsoid(kn_ + V((0, -0.036, 0.006)), (0.026, 0.018, 0.03))                # kneecap
        g.cone(kn_, an, 0.042, 0.028)
        g.along(kn_, an, 0.3, (0.038, 0.042, 0.1), off=(0, 0.02, 0))                 # calf
        g.ball(an, 0.028)
        x = an.x
        g.ellipsoid((x, 0.03, 0.045), (0.032, 0.04, 0.04))                           # heel
        g.ellipsoid((x + 0.003 * sx, -0.045, 0.034), (0.036, 0.058, 0.028))           # foot
        g.ellipsoid((x + 0.005 * sx, -0.112, 0.024), (0.033, 0.038, 0.02))            # toes
        fams.append(g)
    return fams


def _bvh(ob):
    return BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())


def _normals(ob):
    return np.array([v.normal[:] for v in ob.data.vertices])


def definition(P, N):
    """Muscle definition for HIGH: displacement (m) along the normal at each vertex."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    reg = regions(P)
    front = ss((-N[:, 1] - 0.2) / 0.4)
    back = ss((N[:, 1] - 0.2) / 0.4)
    d = np.zeros(len(P))

    def g(u, w):
        return np.exp(-0.5 * (u / w) ** 2)

    tor = reg["torso"]
    # Sternum and the line between the pecs, the pecs' lower edge.
    d -= 0.0022 * g(x, 0.006) * ss((z - 1.24) / 0.03) * ss((1.43 - z) / 0.03) * front * tor
    pec_edge = 1.275 + 0.03 * np.clip(1 - np.abs(x) / 0.13, 0, 1) ** 0.5
    d -= 0.0028 * g(z - pec_edge, 0.008) * (np.abs(x) < 0.15) * front * tor
    # Abs: the middle line and three tendinous bands, obliques' edge.
    absz = (z > 0.99) & (z < 1.25) & (np.abs(x) < 0.07)
    d -= 0.0018 * g(x, 0.005) * absz * front * tor
    for zz in (1.075, 1.135, 1.195):
        d -= 0.0013 * g(z - zz - 0.004 * np.abs(x) / 0.06, 0.005) * absz * front * tor
    d -= 0.0016 * g(np.abs(x) - 0.072 - 0.1 * (1.2 - z), 0.006) * (z > 0.98) * (z < 1.22) * front * tor
    # Iliac line (the V at the hips).
    vline = np.abs(x) - (0.07 + 0.45 * (z - 0.95))
    d -= 0.0018 * g(vline, 0.006) * (z > 0.92) * (z < 1.02) * front * tor
    # Spine groove, shoulder-blade edges.
    d -= 0.0022 * g(x, 0.007) * (z > 0.98) * (z < 1.42) * back * tor
    d += 0.0016 * g(np.abs(x) - 0.095, 0.01) * g(z - 1.33, 0.05) * back * tor
    # Collarbones.
    clav = 1.425 - 0.06 * np.clip(np.abs(x) - 0.03, 0, 1)
    d += 0.0016 * g(z - clav, 0.005) * (np.abs(x) > 0.025) * (np.abs(x) < 0.15) * front * tor
    for s, sx in (("L", 1), ("R", -1)):
        arm = reg[f"arm_{s}"]
        sa, da = arm_coord(P, s)
        ua = common.UPPER_ARM_LEN
        # Deltoid's lower edge, biceps/triceps split, elbow point.
        d -= 0.002 * g(sa - 0.13, 0.008) * arm
        d += 0.0015 * g(sa - ua, 0.012) * back * arm
        # Forearm veins: two ridges running down the inside of the forearm.
        el, wr = J[f"elbow.{s}"], J[f"wrist.{s}"]
        ax = (wr - el).normalized()
        ref = ax.cross(V((0, 0, 1))).normalized()
        ref2 = ax.cross(ref)
        rel = P - np.array(el[:])
        ang = np.arctan2(rel @ np.array(ref2[:]), rel @ np.array(ref[:]))
        fore = arm & (sa > ua + 0.03) & (sa < ua + 0.24)
        for a0, wob in ((0.6, 0.15), (1.4, 0.2)):
            path = a0 * sx + wob * np.sin((sa - ua) * 40.0)
            d += 0.0011 * g(ang - path, 0.07) * fore
    for s in ("L", "R"):
        leg = reg[f"leg_{s}"]
        sl, dl = leg_coord(P, s)
        th = common.THIGH_LEN
        d -= 0.0015 * g(sl - th + 0.06, 0.01) * front * leg     # above the kneecap
        d -= 0.0012 * g(sl - th - 0.12, 0.02) * back * leg      # calf split
    return d


def build_body(hi):
    res = 0.0035 if hi else 0.0055
    ob = to_mesh(body_families(res), "body")
    remesh(ob, 0.003 if hi else 0.0055, smooth=2)
    if hi:
        P = verts_np(ob)
        N = _normals(ob)
        set_verts_np(ob, P + N * definition(P, N)[:, None])
        apply_mod(ob, "SMOOTH", factor=0.3, iterations=1)
    # The neck goes on in the head mesh, which sits in this closed top.
    set_material(ob, "skin")
    return ob


# ---------------------------------------------------------------- head, eyes
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
        f.capsule((0.035 * sx, 0.005, 1.47), (0.012 * sx, -0.02, 1.575), 0.012)  # neck muscles
    f.capsule((0, 0.018, 1.44), (0, 0.006, 1.6), 0.054)              # neck
    f.ellipsoid((0, 0.03, 1.46), (0.08, 0.05, 0.03))                 # neck base
    f.ellipsoid((0, -0.035, 1.53), (0.016, 0.02, 0.014))             # Adam's apple
    return [f]


# Soft "brushes" that sculpt the face onto the base head: centre, sigma (x, y, z),
# amount (m, + = out along the normal). Nose and lips push toward -Y (forward).
FACE_BRUSHES = [
    ((0, -0.085, 1.692), (0.05, 0.02, 0.009), 0.0045, "n"),   # brow ridge
    ((0, -0.093, 1.712), (0.04, 0.02, 0.02), 0.002, "n"),      # forehead
    ((0, -0.095, 1.676), (0.006, 0.02, 0.008), 0.004, "f"),    # nose root
    ((0, -0.1, 1.652), (0.0068, 0.02, 0.017), 0.0135, "f"),    # nose bridge
    ((0, -0.104, 1.629), (0.011, 0.02, 0.011), 0.02, "f"),     # nose tip
    ((0, -0.098, 1.618), (0.013, 0.02, 0.006), 0.005, "f"),    # under the nose
    ((0, -0.092, 1.601), (0.019, 0.02, 0.0055), 0.0045, "f"),  # upper lip
    ((0, -0.09, 1.5875), (0.0155, 0.02, 0.005), 0.0048, "f"),  # lower lip
    ((0, -0.091, 1.5945), (0.022, 0.03, 0.0016), -0.0026, "f"),  # mouth line
    ((0, -0.085, 1.578), (0.018, 0.02, 0.005), -0.002, "f"),   # chin crease
    ((0, -0.082, 1.562), (0.017, 0.02, 0.012), 0.005, "n"),    # chin
]
for _sx in (1, -1):
    FACE_BRUSHES += [
        ((0.031 * _sx, -0.088, 1.667), (0.016, 0.03, 0.0105), -0.0058, "n"),  # eye sockets
        ((0.032 * _sx, -0.088, 1.6795), (0.014, 0.03, 0.003), 0.0016, "n"),   # upper lids
        ((0.031 * _sx, -0.09, 1.6575), (0.012, 0.03, 0.0025), 0.0012, "n"),   # lower lids
        ((0.014 * _sx, -0.096, 1.621), (0.0075, 0.02, 0.0065), 0.0055, "n"),  # nostril wings
        ((0.047 * _sx, -0.062, 1.642), (0.017, 0.02, 0.013), 0.0055, "n"),    # cheekbones
        ((0.04 * _sx, -0.07, 1.612), (0.012, 0.02, 0.016), -0.002, "n"),      # under the cheekbones
        ((0.066 * _sx, -0.035, 1.698), (0.012, 0.02, 0.014), -0.003, "n"),    # temples
        ((0.026 * _sx, -0.083, 1.596), (0.007, 0.02, 0.009), -0.0018, "n"),   # mouth corners
        ((0.021 * _sx, -0.088, 1.612), (0.004, 0.02, 0.012), -0.0016, "n"),   # smile lines
        ((0.05 * _sx, -0.04, 1.585), (0.012, 0.03, 0.01), 0.0016, "n"),       # jaw muscle
    ]


def sculpt_face(ob):
    me = ob.data
    co = verts_np(ob)
    nor = np.array([v.normal[:] for v in me.vertices], dtype=np.float64)
    out = co.copy()
    front = np.clip((-co[:, 1] - 0.03) / 0.04, 0.0, 1.0)[:, None]  # brushes act on the face only
    for c, sig, amount, mode in FACE_BRUSHES:
        d = (co - np.array(c)) / np.array(sig)
        w = np.exp(-0.5 * (d * d).sum(1))[:, None] * amount * front
        if mode == "f":
            out += w * np.array((0.0, -1.0, 0.0))
        else:
            out += w * nor
    set_verts_np(ob, out)


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


def build_eyes():
    import bmesh
    obs = []
    for s, c in EYE.items():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=0.0122)
        bmesh.ops.translate(bm, verts=bm.verts, vec=c)
        me = bpy.data.meshes.new(f"eye_{s}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"eye_{s}", me)
        common.COL.objects.link(ob)
        me.shade_smooth()
        set_material(ob, "eye")
        obs.append(ob)
    return obs


# ---------------------------------------------------------------- hands (built in the hand bone's frame)
def build_hand(s, hi, rest):
    m = rest[f"hand.{s}"]
    sx = 1.0 if s == "L" else -1.0
    thumb = V((sx, 0, 0))  # thumb side in the hand frame (+X left hand, -X right hand)
    f = Family(f"hand{s}", 0.0022 if hi else 0.0035)

    def P(x, y, z):
        return m @ V((x, y, z))

    f.ellipsoid(P(0.0, 0.045, -0.002), (0.039, 0.05, 0.0145))      # palm
    f.ellipsoid(P(0.0, 0.004, 0.0), (0.03, 0.025, 0.02))           # heel of the hand / wrist
    f.capsule(P(0, -0.07, 0.0), P(0, 0.0, 0.0), 0.026)             # wrist (into the forearm)
    for i, kx in enumerate((0.027, 0.009, -0.009, -0.025)):
        f.ellipsoid(P(thumb.x * kx, 0.084, 0.004), (0.0085, 0.008, 0.007))  # knuckles
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
            dk = (Matrix.Rotation(-ang, 3, V((1, 0, 0))) @ d).normalized()
            q = p + dk * lengths[i][k]
            f.capsule(P(*p), P(*q), radii[i] * (1.0 - 0.08 * k))
            p = q
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
