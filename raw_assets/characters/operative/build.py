"""The operative: the player's base body in the CS-1 carapace.

Owner, 2026-11-05: "a dude in a black synth suit... a really sleek-looking
black carapace over his body. That's what our baseline augmented soldiers
should look like. The different passives and actives can change the look."
(Reference given: the suit Lex Luthor wears under the mech in Injustice.)
Second pass, same day, after "it looks like a crash test dummy": sleek,
baseline, polymer, badass.

Design (docs/design.md §3.4a):
- Silhouette first: heroic proportions (about 8 heads), broad shoulders and
  traps, V-taper to a narrow waist, heavy thighs, a thick neck in a high
  collar. The head is a helmet, not an egg: flat side panels, faceted
  faceplate with a V jaw and a raised keel, recessed chevron visor with a lit
  lower lip, crown panel lines, gunmetal ear pods, a nape guard, a respirator.
- Two blacks: a matte graphite polymer undersuit (panel seams, ribbed flex
  zones at the neck, waist, elbows and backs of the knees, striated flanks)
  under gloss-black ceramic-polymer plates with chamfered edges, flat facets,
  keel ridges and recessed panels. Gunmetal only on the sternum keel and the
  ear pods. Seaglass light (the HUD colour) used sparingly: visor lip,
  sternum, buckle, spine nodes, forearm keels, tassets, ear pods. No rings.
- Plates: one breastplate under a sternum keel, chevron abdominal lames, a hip
  band, serratus slats, scapula and lat plates, a six-node spine, lumbar
  plates, collar, layered pauldrons, upper-arm and elbow guards, forearm
  keels, hand and knuckle guards, hip tassets, thigh plates, diamond knee
  guards, keeled shins, armoured boots.

Construction (all procedural, rebuildable):
- Same skeleton as the triad (bone names and A-pose), scaled to 1.86 m, so
  animations, ragdolls and part sockets carry over.
- Everything is a signed distance field (raw_assets/_lib/sdf.py) meshed with
  surface nets (dual-contouring vertex placement keeps hard edges crisp). The anatomy field is smooth unions of ellipsoids, round cones
  and boxes. Each plate is a shell of that field (from 4 mm inside the suit to
  its thickness above), cut by its outline planes with chamfered edges, shaved
  by flat facets, with an optional recessed panel and light groove.
- HIGH (dense, all detail) is baked onto LOW (decimated game mesh): base
  colour with AO grime, ORM, tangent normal, emission; one material, one draw.
- The undersuit is skinned with analytic weights (as the triad); plates and the
  helmet are rigid on one bone each.

Run:
  tools/blender.sh raw_assets/characters/operative/build.py --out assets/characters/operative/operative.gltf \\
      --preview docs/previews/operative
  Design check without the bake (coarse, fast): --quick --preview /tmp/op
"""
import argparse
import math
import os
import subprocess
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import bakeutil  # noqa: E402
import sdf  # noqa: E402
from sdf import F32  # noqa: E402

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="", help="prefix for preview renders (<prefix>_<view>.png and <prefix>.png sheet)")
ap.add_argument("--quick", action="store_true", help="coarse fields, no bake: renders the unbaked HIGH")
ap.add_argument("--nobake", action="store_true", help="full-resolution HIGH, no bake: renders the unbaked HIGH")
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--views", default="front,back,side,hero,helmet")
args = ap.parse_args(argv)
QUICK = args.quick
T0 = time.time()

H_BODY = 0.005 if QUICK else 0.0025
H_PLATE = 0.0032 if QUICK else 0.0014
H_HELMET = 0.0025 if QUICK else 0.0011


def log(*a):
    print(f"[operative {time.time() - T0:6.1f}s]", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COL = scene.collection

S = 1.065  # 1.75 m triad rig -> ~1.86 m operative

# ====================================================================== skeleton (same as triad)
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
for k in J:
    J[k] = J[k] * S

BONES = [
    ("root", V((0, 0, 0)), V((0, -0.2, 0)), None, V((0, 0, 1))),
    ("hips", J["hips"], J["spine"], "root", V((0, -1, 0))),
    ("spine", J["spine"], J["chest"], "hips", V((0, -1, 0))),
    ("chest", J["chest"], V((0, 0.0, 1.44 * S)), "spine", V((0, -1, 0))),
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
BONE_NAMES = [b[0] for b in BONES]


def make_armature():
    data = bpy.data.armatures.new("operative_rig")
    arm = bpy.data.objects.new("operative_rig", data)
    COL.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = data.edit_bones
    for name, head, tail, parent, roll in BONES:
        b = eb.new(name)
        b.head, b.tail = head, tail
        b.align_roll(roll)
        if parent:
            b.parent = eb[parent]
            b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


ARM = make_armature()
log("armature:", len(ARM.data.bones), "bones")

# ====================================================================== maths helpers
A = {k: np.array(v[:], dtype=float) for k, v in J.items()}
SIDES = (("L", 1.0), ("R", -1.0))
FWD = np.array((0.0, -1.0, 0.0))
UP = np.array((0.0, 0.0, 1.0))


def nrm(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def perp(v, axis):
    v = np.asarray(v, float)
    return nrm(v - axis * (v @ axis))


def lerp(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


def comp(x, y, z, o, v):
    """Component of (p - o) along v (broadcasting arrays)."""
    return (x - F32(o[0])) * F32(v[0]) + (y - F32(o[1])) * F32(v[1]) + (z - F32(o[2])) * F32(v[2])


def H(o, n):
    """Region: keep the side of the plane through o that n points away from."""
    n = nrm(n)
    o = np.asarray(o, float)
    return lambda x, y, z: comp(x, y, z, o, n)


def band(o, n, lo, hi):
    n = nrm(n)
    o = np.asarray(o, float)

    def f(x, y, z):
        c = comp(x, y, z, o, n)
        return np.maximum(F32(lo) - c, c - F32(hi))
    return f


def AND(*fs):
    def f(x, y, z):
        d = fs[0](x, y, z)
        for g in fs[1:]:
            d = np.maximum(d, g(x, y, z))
        return d
    return f


def MX(f):
    """Mirror across x = 0 (one definition, both sides)."""
    return lambda x, y, z: f(np.abs(x), y, z)


def seg(a, b, r):
    """Region: within r of the segment a-b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    u = b - a
    L2 = float(u @ u)

    def f(x, y, z):
        t = np.clip(comp(x, y, z, a, u) / F32(L2), 0.0, 1.0)
        px = x - F32(a[0]) - t * F32(u[0])
        py = y - F32(a[1]) - t * F32(u[1])
        pz = z - F32(a[2]) - t * F32(u[2])
        return np.sqrt(px * px + py * py + pz * pz) - F32(r)
    return f


def ball(c, r):
    return sdf.Sphere(c, r)


# Limb frames (A-pose). "out" is the limb's outer face, "fr" its front face.
LIMB = {}
for s, sx in SIDES:
    X_ = np.array((sx, 0.0, 0.0))
    sh, el, wr, kn = A[f"shoulder.{s}"], A[f"elbow.{s}"], A[f"wrist.{s}"], A[f"knuckle.{s}"]
    hp, kne, an, bl = A[f"hip.{s}"], A[f"knee.{s}"], A[f"ankle.{s}"], A[f"ball.{s}"]
    L = {"sx": sx, "sh": sh, "el": el, "wr": wr, "kn": kn, "hp": hp, "knee": kne, "an": an, "ball": bl}
    for key, (a, b) in {"ua": (sh, el), "fa": (el, wr), "th": (hp, kne), "sv": (kne, an)}.items():
        u = nrm(b - a)
        out = perp(X_, u)
        fr = nrm(np.cross(u, out))
        if fr @ FWD < 0:
            fr = -fr
        L[key], L[key + "_out"], L[key + "_fr"] = u, out, fr
    hd = nrm(kn - wr)
    pn = perp(-X_, hd)                  # palm normal: toward the body
    w = nrm(np.cross(hd, pn))           # across the hand, thumb side forward
    if w @ FWD < 0:
        w = -w
    L["hd"], L["pn"], L["hw"] = hd, pn, w
    LIMB[s] = L

# ====================================================================== materials (HIGH, procedural)
SEAGLASS = (0.36, 0.86, 0.78)


def material(name, base, rough, metal=0.0, emission=None, bump=0.0, bump_scale=900.0):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if bump > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.0002
        nt.links.new(tex.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


MAT = {
    "suit": material("op_suit", (0.017, 0.018, 0.02), 0.52, bump=0.06, bump_scale=700),
    "plate": material("op_plate", (0.0075, 0.008, 0.009), 0.17),
    "trim": material("op_trim", (0.12, 0.125, 0.13), 0.34, metal=0.95),
    "visor": material("op_visor", (0.003, 0.004, 0.005), 0.04, emission=((0.004, 0.011, 0.01), 1.0)),
    "glow": material("op_glow", SEAGLASS, 0.3, emission=(SEAGLASS, 4.0)),
    "sole": material("op_sole", (0.016, 0.016, 0.017), 0.88, bump=0.3, bump_scale=300),
}
MAT_ORDER = ["suit", "plate", "trim", "visor", "glow", "sole"]
MI = {k: i for i, k in enumerate(MAT_ORDER)}

# ====================================================================== anatomy (BASE field)
E, RC, RB = sdf.Ellipsoid, sdf.RoundCone, sdf.RoundBox
BASE = sdf.Model()
add = BASE.add


def ry(deg):
    return sdf.rot((0, 1, 0), deg)


# Torso: a broad ribcage and shoulder girdle over a narrow waist.
add(E((0, 0.012, 1.31), (0.152, 0.116, 0.17)))                       # ribcage
add(E((0, 0.018, 1.44), (0.178, 0.1, 0.082)), k=0.04)                # shoulder girdle
add(E((0, 0.004, 1.13), (0.128, 0.094, 0.12)), k=0.05)               # waist
add(E((0, 0.014, 0.99), (0.15, 0.106, 0.1)), k=0.05)                 # pelvis
add(E((0, -0.056, 1.17), (0.096, 0.045, 0.13)), k=0.03)              # abdominal wall
add(RC((0, 0.016, 1.47), (0, 0.008, 1.7), 0.08, 0.071), k=0.03)     # neck
for s, sx in SIDES:
    add(E((0.115 * sx, 0.035, 1.3), (0.074, 0.072, 0.145), ry(15 * sx)), k=0.03)     # lats (V-taper)
    add(E((0.08 * sx, -0.064, 1.372), (0.096, 0.042, 0.058), ry(-14 * sx)), k=0.02)   # pectorals
    add(RC((0, 0.05, 1.565), (0.155 * sx, 0.03, 1.475), 0.05, 0.036), k=0.04)        # trapezius
    add(RC((0.045 * sx, 0.02, 1.64), (0.016 * sx, -0.044, 1.49), 0.024, 0.019), k=0.015)  # neck tendons
    add(E((0.11 * sx, -0.022, 1.11), (0.045, 0.065, 0.09)), k=0.03)                   # obliques
    add(E((0.07 * sx, 0.062, 0.955), (0.074, 0.064, 0.08)), k=0.03)                   # glutes
    add(E((0.085 * sx, 0.098, 1.37), (0.07, 0.03, 0.085)), k=0.03)                    # shoulder blades
    add(E((0.035 * sx, 0.082, 1.13), (0.034, 0.035, 0.16)), k=0.03)                   # spinal erectors

# Arms.
FINGERS = {}
for s, sx in SIDES:
    L = LIMB[s]
    sh, el, wr, kn = L["sh"], L["el"], L["wr"], L["kn"]
    ua, uo, uf = L["ua"], L["ua_out"], L["ua_fr"]
    fa, fo = L["fa"], L["fa_out"]
    add(E(sh + ua * 0.035 + uo * 0.012, (0.094, 0.066, 0.066), sdf.frame(ua, uo)), k=0.025)   # deltoid
    add(RC(sh, el, 0.05, 0.04), k=0.02)
    add(E(sh + ua * 0.165 + uf * 0.016, (0.1, 0.046, 0.046), sdf.frame(ua, uo)), k=0.015)   # biceps
    add(E(sh + ua * 0.125 - uf * 0.019, (0.11, 0.047, 0.045), sdf.frame(ua, uo)), k=0.015)  # triceps
    add(sdf.Sphere(el + uf * 0.004, 0.041), k=0.02)
    add(RC(el, wr, 0.044, 0.029), k=0.015)
    add(E(el + fa * 0.075 + fo * 0.006, (0.095, 0.05, 0.043), sdf.frame(fa, fo)), k=0.02)   # forearm mass
    hd, pn, hw = L["hd"], L["pn"], L["hw"]
    add(RC(wr - hd * 0.012, wr + hd * 0.015, 0.03, 0.028), k=0.01)                         # wrist
    add(RB(wr + hd * 0.05, (0.052, 0.046, 0.017), np.stack([hd, hw, pn], 1), 0.014), k=0.012)  # palm
    segs = []
    for off, length in ((0.029, 0.08), (0.0095, 0.087), (-0.0095, 0.083), (-0.028, 0.068)):
        base = kn + hw * off - hd * 0.006
        mid = base + hd * length * 0.5
        tip = mid + nrm(hd * math.cos(math.radians(30)) + pn * math.sin(math.radians(30))) * length * 0.5
        add(RC(base, mid, 0.0105, 0.0098), k=0.004)
        add(RC(mid, tip, 0.0098, 0.0085), k=0.003)
        segs += [(base, mid), (mid, tip)]
    t0 = wr + hd * 0.022 + hw * 0.03 + pn * 0.01
    t1 = t0 + nrm(hd * 0.55 + hw * 0.5 + pn * 0.55) * 0.04
    t2 = t1 + nrm(hd * 0.8 + pn * 0.5) * 0.032
    add(RC(t0, t1, 0.016, 0.0125), k=0.012)
    add(RC(t1, t2, 0.0125, 0.0105), k=0.004)
    FINGERS[s] = {"fingers": segs, "thumb": [(t0, t1), (t1, t2)]}

# Legs and boots.
for s, sx in SIDES:
    L = LIMB[s]
    hp, kne, an = L["hp"], L["knee"], L["an"]
    th, sv = L["th"], L["sv"]
    add(RC(hp + UP * 0.03, kne, 0.086, 0.055), k=0.04)
    add(E(lerp(hp, kne, 0.42) + FWD * 0.022, (0.2, 0.068, 0.07), sdf.frame(th)), k=0.02)                 # quads
    add(E(lerp(hp, kne, 0.48) + np.array((0.03 * sx, 0.004, 0)), (0.19, 0.058, 0.058), sdf.frame(th)), k=0.02)  # outer sweep
    add(E(lerp(hp, kne, 0.8) + np.array((-0.026 * sx, -0.024, 0)), (0.07, 0.04, 0.042), sdf.frame(th)), k=0.015)  # teardrop
    add(E(lerp(hp, kne, 0.45) - FWD * 0.03, (0.19, 0.06, 0.058), sdf.frame(th)), k=0.02)                  # hamstrings
    add(E(lerp(hp, kne, 0.22) + np.array((-0.032 * sx, 0.004, 0)), (0.13, 0.055, 0.06), sdf.frame(th)), k=0.02)  # adductors
    add(sdf.Sphere(kne + FWD * 0.008, 0.05), k=0.02)
    add(RC(kne, an, 0.05, 0.034), k=0.015)
    add(E(lerp(kne, an, 0.28) + np.array((-0.01 * sx, 0.03, 0)), (0.13, 0.054, 0.05), sdf.frame(sv)), k=0.02)   # calf
    add(E(lerp(kne, an, 0.36) + np.array((0.006 * sx, -0.026, 0)), (0.12, 0.028, 0.03), sdf.frame(sv)), k=0.015)  # shin muscle
    add(RC(an + np.array((0, 0.004, -0.02)), an + UP * 0.09, 0.048, 0.043), k=0.02)   # boot cuff
    add(E((an[0], -0.045, 0.055), (0.052, 0.125, 0.052)), k=0.03)                       # boot upper
    add(E((an[0] + 0.004 * sx, -0.135, 0.035), (0.046, 0.06, 0.03)), k=0.02)              # toe box
    add(RB((an[0] + 0.002 * sx, -0.055, 0.021), (0.055, 0.143, 0.021), None, 0.012), k=0.01)  # sole
BASE.fn((-0.4, -0.4, -0.06), (0.4, 0.4, 0.01), lambda f, x, y, z: np.maximum(f, -z))      # flat soles

# ====================================================================== undersuit detail (HIGH only)
DETAIL = BASE.copy()


def ribs(f, t, period, amp, window):
    return f + F32(amp) * (0.5 - 0.5 * np.cos(F32(2 * math.pi / period) * t)) * window


def groove(f, g, width, depth):
    """Rounded channel where |g| < width."""
    return f + F32(depth) * np.maximum(0.0, 1.0 - (g / F32(width)) ** 2)


# Ribbed flex zones: neck, waist, elbows, backs of the knees.
DETAIL.fn((-0.12, -0.12, 1.5), (0.12, 0.12, 1.7),
          lambda f, x, y, z: ribs(f, z - 1.5, 0.0105, 0.001, sdf.ss((z - 1.52) / 0.01) * sdf.ss((1.68 - z) / 0.01)))
DETAIL.fn((-0.25, -0.2, 1.02), (0.25, 0.2, 1.14),
          lambda f, x, y, z: ribs(f, z - 1.03, 0.011, 0.0012,
                                  sdf.ss((z - 1.035) / 0.012) * sdf.ss((1.125 - z) / 0.012) * sdf.ss((np.abs(x) - 0.06) / 0.03)))
for s, sx in SIDES:
    L = LIMB[s]
    ax = nrm(L["ua"] + L["fa"])
    el = L["el"]

    def elbow(f, x, y, z, el=el, ax=ax):
        t = comp(x, y, z, el, ax)
        return ribs(f, t, 0.0095, 0.0011, sdf.ss((0.034 - np.abs(t)) / 0.01))
    DETAIL.fn(el - 0.07, el + 0.07, elbow)
    kne = L["knee"]
    kax = nrm(L["th"] + L["sv"])

    def knee(f, x, y, z, kne=kne, kax=kax):
        t = comp(x, y, z, kne, kax)
        back = sdf.ss((y - F32(kne[1]) + 0.005) / 0.02)
        return ribs(f, t, 0.0105, 0.0013, sdf.ss((0.05 - np.abs(t)) / 0.012) * back)
    DETAIL.fn(kne - 0.09, kne + 0.09, knee)
    # Striated flanks (serratus/obliques), diagonal.
    sd = nrm((0.0, -0.55, 0.835))

    def flank(f, x, y, z, sx=sx, sd=sd):
        u = comp(x, y, z, (0, 0, 0), sd)
        w = sdf.ss((np.abs(x) - 0.1) / 0.02) * sdf.ss((z - 1.04) / 0.03) * sdf.ss((1.2 - z) / 0.03) * sdf.ss((0.05 - y) / 0.02)
        return ribs(f, u, 0.0105, 0.0009, w)
    DETAIL.fn((0.05 * sx - 0.2, -0.15, 1.0), (0.05 * sx + 0.2, 0.1, 1.25), flank)
    # Panel seams: outer leg, inner arm.
    hp, an = L["hp"], L["an"]

    def leg_seam(f, x, y, z, hp=hp, an=an, sx=sx):
        yc = F32(hp[1]) + (z - F32(hp[2])) * F32((an[1] - hp[1]) / (an[2] - hp[2]))
        w = sdf.ss((x * F32(sx) - 0.12) / 0.015) * sdf.ss((z - 0.14) / 0.03) * sdf.ss((0.93 - z) / 0.03)
        return groove(f, y - yc, 0.0028, 0.0016 * w)
    DETAIL.fn((0.0 if sx > 0 else -0.35, -0.2, 0.1), (0.35 if sx > 0 else 0.0, 0.2, 1.0), leg_seam)
    sh = L["sh"]

    def arm_seam(f, x, y, z, sh=sh, ua=L["ua"], uf=L["ua_fr"], uo=L["ua_out"]):
        t = comp(x, y, z, sh, ua)
        g = comp(x, y, z, sh, uf)
        w = sdf.ss((t - 0.09) / 0.02) * sdf.ss((0.27 - t) / 0.02) * sdf.ss(-comp(x, y, z, sh, uo) / 0.01)
        return groove(f, g, 0.0026, 0.0015 * w)
    DETAIL.fn(np.minimum(sh, L["el"]) - 0.08, np.maximum(sh, L["el"]) + 0.08, arm_seam)
# Back-of-leg seams (hamstrings, calves) and the glute panel line.
for s, sx in SIDES:
    L = LIMB[s]

    def back_leg(f, x, y, z, L=L):
        hp, an = L["hp"], L["an"]
        xc = F32(hp[0]) + (z - F32(hp[2])) * F32((an[0] - hp[0]) / (an[2] - hp[2]))
        w = sdf.ss((y - 0.02) / 0.015) * sdf.ss((z - 0.16) / 0.03) * sdf.ss((0.86 - z) / 0.03)
        return groove(f, x - xc, 0.0028, 0.0016 * w)
    DETAIL.fn((L["hp"][0] - 0.15, -0.1, 0.1), (L["hp"][0] + 0.15, 0.2, 0.9), back_leg)
DETAIL.fn((-0.25, 0.0, 0.84), (0.25, 0.2, 1.08),
          lambda f, x, y, z: groove(f, z - (0.905 + 0.25 * np.abs(np.abs(x) - 0.07)), 0.0028,
                                    0.0016 * sdf.ss((y - 0.04) / 0.02) * sdf.ss((np.abs(x) - 0.012) / 0.01)))
# Torso side seams.
DETAIL.fn((-0.3, -0.1, 0.92), (0.3, 0.12, 1.5),
          lambda f, x, y, z: groove(f, y - 0.014, 0.0028,
                                    0.0016 * sdf.ss((np.abs(x) - 0.1) / 0.02) * sdf.ss((1.46 - z) / 0.03) * sdf.ss((z - 0.95) / 0.03)))
# Inguinal V seams (hip bone to groin) and the sole welt.
DETAIL.fn((-0.2, -0.2, 0.86), (0.2, 0.05, 1.1),
          lambda f, x, y, z: groove(f, 0.86 * (np.abs(x) - 0.03) - 0.5 * (z - 0.92), 0.0028,
                                    0.0016 * sdf.ss((0.0 - y) / 0.02) * sdf.ss((1.06 - z) / 0.02) * sdf.ss((np.abs(x) - 0.035) / 0.01)))
DETAIL.fn((-0.3, -0.3, -0.01), (0.3, 0.2, 0.06), lambda f, x, y, z: groove(f, z - 0.043, 0.0025, 0.0015))

# ====================================================================== suit HIGH
_coarse_grid = sdf.Grid((-0.7, -0.24, -0.02), (0.7, 0.24, 1.92), 0.006)
_coarse = None


def coarse_base():
    global _coarse
    if _coarse is None:
        _coarse = BASE.evaluate(_coarse_grid)
    return _coarse


def link(ob):
    COL.objects.link(ob)
    return ob


def apply_mod(ob, kind, **kw):
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(m, k, v)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def face_centers(me):
    c = np.empty(len(me.polygons) * 3, dtype=np.float32)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def set_materials(ob, mat_idx):
    ob.data.materials.clear()
    for k in MAT_ORDER:
        ob.data.materials.append(MAT[k])
    ob.data.polygons.foreach_set("material_index", np.asarray(mat_idx, dtype=np.int32))


log("suit field")
g = sdf.Grid((-0.68, -0.23, -0.012), (0.68, 0.23, 1.74), H_BODY)
F = DETAIL.evaluate(g)
SUIT = link(bpy.data.objects.new("suit_high", sdf.to_mesh("suit_high", F, g)))
del F
c = face_centers(SUIT.data)
mi = np.full(len(c), MI["suit"])
mi[c[:, 2] < 0.036] = MI["sole"]
set_materials(SUIT, mi)
log("suit HIGH:", len(SUIT.data.polygons), "quads")

# ====================================================================== carapace plates
PLATES = []


def plate(name, bone, region, T=0.009, B=-0.004, ch=0.0022, facets=(), inset=None, glow=None, mat="plate",
          side="L", near=None):
    """`region` <= 0 inside (outline). `facets`: (normal, depth[, mirrored]) flat cuts `depth` below the
    plate's extreme along normal. `inset`: (margin, depth) recessed panel. `glow`: region of a light groove.
    `near`: (a, b, r) keep within r of a bone segment. `side` "L" is mirrored to "R"; None = centre."""
    if near is not None:
        region = AND(region, seg(*near))
    PLATES.append(dict(name=name, bone=bone, region=region, T=T, B=B, ch=ch, facets=facets, inset=inset,
                       glow=glow, mat=mat, side=side))


def plate_box(sp):
    cg = _coarse_grid
    db = coarse_base()
    X, Y, Z = cg.coords()
    inside = (db < sp["T"] + 0.002) & (db > sp["B"] - 0.002) & (sp["region"](X, Y, Z) < 0.003)
    idx = np.nonzero(inside)
    if len(idx[0]) == 0:
        return None
    lo = np.array([cg.axes[i][idx[i].min()] for i in range(3)]) - 0.012
    hi = np.array([cg.axes[i][idx[i].max()] for i in range(3)]) + 0.012
    return lo, hi


def plate_field(sp, h):
    box = plate_box(sp)
    if box is None:
        return None, None, None
    lo, hi = box
    g = sdf.Grid(lo - 3 * h, hi + 3 * h, h)
    X, Y, Z = g.coords()
    db = BASE.evaluate(g)
    d = np.maximum(db - F32(sp["T"]), F32(sp["B"]) - db)
    R = sp["region"](X, Y, Z)
    d = sdf.cmax(d, R, sp["ch"])
    d = np.maximum(d, sdf.RoundBox((lo + hi) / 2, (hi - lo) / 2)(X, Y, Z))
    for fc in sp["facets"]:
        n, depth = nrm(fc[0]), fc[1]
        mx = len(fc) > 2 and fc[2]
        pl = (np.abs(X) if mx else X) * F32(n[0]) + Y * F32(n[1]) + Z * F32(n[2])
        inside = d < 0
        if not inside.any():
            break
        top = float(pl[inside].max())
        d = sdf.cmax(d, pl - F32(top - depth), sp["ch"] * 0.8)
    if sp["inset"]:
        margin, depth = sp["inset"]
        d = carve(d, R + F32(margin), depth, k=0.0011)
    if sp["glow"]:
        d = carve(d, sp["glow"](X, Y, Z), 0.0014, k=0.0)
    return d, g, db


def build_plate(sp):
    d, g, _db = plate_field(sp, H_PLATE)
    if d is None or not (d < 0).any():
        log("  empty plate", sp["name"])
        return None
    ob = link(bpy.data.objects.new(sp["name"], sdf.to_mesh(sp["name"], d, g)))
    c = face_centers(ob.data)
    mi = np.full(len(c), MI[sp["mat"]])
    if sp["glow"]:
        dbc = BASE.evaluate_points(c)
        gl = (sp["glow"](c[:, 0], c[:, 1], c[:, 2]) < 0.0003) & (dbc > sp["T"] * 0.4)
        mi[gl] = MI["glow"]
    set_materials(ob, mi)
    sp["high"] = ob
    return ob


def mx(arrs):
    out = arrs[0]
    for a in arrs[1:]:
        out = np.maximum(out, a)
    return out


def carve(d, region, depth, k=0.0012):
    """Remove a `depth` skin of d inside `region` (a recess that follows the surface). Edges are
    rounded by k: perfectly sharp concave creases stair-step in surface nets."""
    return sdf.smax(d, -np.maximum(region, -(d + F32(depth))), k)


# ---------------------------------------------------------------- torso front
X1, Y1, Z1 = np.eye(3)
_LA = LIMB["L"]
_off_arm = MX(lambda x, y, z: -seg(_LA["sh"] + _LA["ua"] * 0.03, _LA["el"] + _LA["fa"] * 0.1, 0.085)(x, y, z))
OFF_ARM = AND(_off_arm, MX(H((0.2, 0, 0), X1)))   # torso plates stay on the torso, off the arms
plate("chest", "chest", AND(MX(H((0, 0, 1.472), (-0.12, 0, 1))), MX(H((0, 0, 1.288), (0.25, 0, -1))),
                            H((0, -0.018, 0), Y1), MX(H((0.172, 0, 1.3), (1, 0, -0.35))), OFF_ARM),
      T=0.012, side=None, facets=(((0.0, -0.6, 0.8), 0.009), ((0.0, -0.8, -0.6), 0.009), ((0.72, -0.69, 0.0), 0.007, True),
                                  ((0.28, -0.96, 0.0), 0.008, True)))
plate("sternum", "chest", AND(MX(H((0.0085, 0, 0), X1)), H((0, 0, 1.462), Z1), H((0, 0, 1.296), -Z1), H((0, -0.03, 0), Y1),
                              OFF_ARM),
      T=0.018, mat="trim", side=None, facets=(((0.6, -0.8, 0.0), 0.003, True),),
      glow=AND(MX(H((0.0016, 0, 0), X1)), H((0, 0, 1.44), Z1), H((0, 0, 1.32), -Z1)))
for i, (zc, bone) in enumerate(((1.248, "spine"), (1.181, "spine"), (1.114, "hips"))):
    plate(f"lame{i}", bone, AND(MX(H((0, 0, zc + 0.029), (-0.2, 0, 1))), MX(H((0, 0, zc - 0.029), (0.2, 0, -1))),
                                MX(H((0.112 - 0.012 * i, 0, 0), X1)), H((0, -0.03, 0), Y1), OFF_ARM),
          T=0.009, side=None, facets=(((0.0, -1.0, 0.0), 0.004), ((0.62, -0.78, 0.0), 0.003, True),
                                      ((0.0, -0.6, -0.8), 0.0025)))
plate("hipband", "hips", AND(MX(H((0, 0, 1.052), (-0.12, 0, 1))), MX(H((0, 0, 1.0), (0.12, 0, -1))), H((0, 0.045, 0), Y1),
                             OFF_ARM),
      T=0.0095, side=None, facets=(((0.0, -1.0, 0.0), 0.004), ((0.7, -0.7, 0.0), 0.004, True)),
      glow=AND(MX(H((0.0055, 0, 0), X1)), H((0, 0, 1.033), Z1), H((0, 0, 1.019), -Z1)))
SERR = nrm((0.0, -0.55, 0.835))
for i in range(3):
    plate(f"serratus{i}", "chest" if i < 2 else "spine",
          AND(band((0, 0, 1.3 - 0.037 * i), SERR, -0.0115, 0.0115), H((0.1, 0, 0), -X1), H((0, -0.088, 0), -Y1),
              H((0, 0.03, 0), Y1), H((0, -0.01, 1.36), (0, 0.6, 1)), OFF_ARM),
          T=0.008, facets=(((1, -0.3, 0), 0.002),))
# ---------------------------------------------------------------- torso back
plate("scapula", "chest", AND(H((0.016, 0, 0), -X1), H((0, 0.035, 0), -Y1), H((0, 0, 1.5), (0.22, 0, 1)),
                              H((0.016, 0, 1.36), (-0.6, 0, -1)), H((0.172, 0, 0), X1), OFF_ARM),
      T=0.012, inset=(0.009, 0.0013), facets=(((0.55, 0.83, 0.0), 0.004), ((0, 0.75, 0.66), 0.004)))
plate("lat", "spine", AND(H((0.034, 0, 0), -X1), H((0, 0.03, 0), -Y1), H((0.016, 0, 1.348), (0.6, 0, 1)),
                          H((0, 0, 1.2), (0.3, 0, -1)), H((0.165, 0, 0), X1), OFF_ARM),
      T=0.01, facets=(((0.6, 0.8, 0.0), 0.004),))
for i, zc in enumerate((1.44, 1.376, 1.312, 1.248, 1.184, 1.12)):
    bone = "chest" if zc > 1.3 else ("spine" if zc > 1.15 else "hips")
    plate(f"spine{i}", bone, AND(MX(H((0.03, 0, 0), X1)), H((0, 0, zc + 0.024), Z1), MX(H((0, 0, zc - 0.03), (1.0, 0, -1))),
                                 H((0, 0.06, 0), -Y1), OFF_ARM),
          T=0.014, side=None, facets=(((0.7, 0.7, 0.0), 0.004, True),),
          glow=AND(MX(H((0.0022, 0, 0), X1)), H((0, 0, zc + 0.008), Z1), H((0, 0, zc - 0.008), -Z1)))
plate("lumbar", "hips", AND(H((0.034, 0, 0), -X1), H((0.11, 0, 0), X1), H((0, 0, 1.17), (-0.2, 0, 1)),
                             H((0, 0, 1.07), -Z1), H((0, 0.045, 0), -Y1), OFF_ARM),
      T=0.009, facets=(((0.5, 0.86, 0), 0.0025),))
plate("gorget", "chest", AND(band((0, 0, 1.528), (0, -0.4, 1), -0.05, 0.072),
                             lambda x, y, z: np.sqrt(x * x + (y - 0.012) ** 2) - 0.112, OFF_ARM),
      T=0.009, side=None, ch=0.0025, facets=(((0, 0, 1), 0.004),))
# ---------------------------------------------------------------- arms
for s, sx in (("L", 1.0),):
    L = LIMB[s]
    sh, el, wr, kn = L["sh"], L["el"], L["wr"], L["kn"]
    ua, uo, uf = L["ua"], L["ua_out"], L["ua_fr"]
    fa, fo, ff = L["fa"], L["fa_out"], L["fa_fr"]
    hd, pn, hw = L["hd"], L["pn"], L["hw"]
    plate("pauldron", "upper_arm.L", AND(H(sh + ua * 0.085, ua), H(sh - uo * 0.012, -uo), H((0.135, 0, 0), -X1),
                                         band(sh, uf, -0.075, 0.075)),
          T=0.015, facets=(((0.3, 0, 1), 0.008), ((1, 0, 0.1), 0.007), ((0.35, -0.9, 0.3), 0.007), ((0.35, 0.9, 0.3), 0.006),
                           ((0.75, 0, 0.66), 0.004)),
          near=(sh, el, 0.11))
    plate("lame", "upper_arm.L", AND(band(sh, ua, 0.093, 0.133), H(sh + uo * 0.004, -uo), band(sh, uf, -0.06, 0.06)),
          T=0.012, facets=((uo, 0.003),), near=(sh, el, 0.09))
    plate("upperarm", "upper_arm.L", AND(band(sh, ua, 0.146, 0.248), H(sh + uo * 0.0, -uo), band(sh, uf, -0.045, 0.045)),
          T=0.0095, facets=((uo + 0.75 * uf, 0.0025), (uo - 0.75 * uf, 0.0025)), near=(sh, el, 0.09))
    plate("elbow", "forearm.L", ball(el - uf * 0.036 + uo * 0.006, 0.025),
          T=0.011, facets=((-uf + 0.8 * uo, 0.005), (-uf - 0.8 * uo, 0.005), (-uf + 0.8 * ua, 0.005), (-uf - 0.8 * ua, 0.005)),
          near=(el - ua * 0.05, el + fa * 0.05, 0.08))
    taper = lambda x, y, z, el=el, fa=fa, ff=ff: (np.abs(comp(x, y, z, el, ff))
                                                  - (0.045 - 0.065 * np.clip(comp(x, y, z, el, fa) - 0.045, 0, 0.2)))
    plate("forearm", "forearm.L", AND(band(el, fa, 0.045, 0.236), H(el - fo * 0.008, -fo), taper),
          T=0.011, facets=((fo + 0.75 * ff, 0.003), (fo - 0.75 * ff, 0.003)), near=(el, wr, 0.08),
          glow=AND(lambda x, y, z: np.abs(comp(x, y, z, el, ff)) - 0.0017, band(el, fa, 0.075, 0.2)))
    plate("hand", "hand.L", AND(band(wr, hd, 0.02, 0.09), H(wr - pn * 0.004, pn), band(wr, hw, -0.04, 0.04)),
          T=0.0075, facets=((-pn, 0.0015),), near=(wr, kn, 0.06))
    plate("knuckles", "fingers.L", AND(band(kn, hd, 0.004, 0.032), H(kn - pn * 0.002, pn), band(kn, hw, -0.042, 0.042)),
          T=0.0068, facets=((-pn + 0.5 * hd, 0.0015),), near=(kn - hd * 0.02, kn + hd * 0.06, 0.05))
# ---------------------------------------------------------------- legs
for s, sx in (("L", 1.0),):
    L = LIMB[s]
    hp, kne, an, bl = L["hp"], L["knee"], L["an"], L["ball"]
    th, to, tf = L["th"], L["th_out"], L["th_fr"]
    sv, so, sf = L["sv"], L["sv_out"], L["sv_fr"]
    thigh_taper = lambda x, y, z, hp=hp, th=th, to=to: (np.abs(comp(x, y, z, hp, to) - 0.008)
                                                         - (0.064 - 0.11 * np.clip(comp(x, y, z, hp, th) - 0.15, 0, 0.25)))
    plate("thigh", "thigh.L", AND(lambda x, y, z: (0.14 - 0.55 * comp(x, y, z, hp, to)) - comp(x, y, z, hp, th),
                                  H(hp + th * 0.37, th), H(hp, -tf), thigh_taper),
          T=0.012, inset=(0.009, 0.0012), facets=((tf + 0.6 * to, 0.005), (tf - 0.6 * to, 0.005)), near=(hp, kne, 0.13))
    plate("tasset", "thigh.L", AND(band(hp, th, -0.05, 0.175), H(hp + to * 0.02, -to), band(hp, tf, -0.055, 0.05),
                                   H(hp + th * 0.1, -th + 0.5 * tf)),
          T=0.012, facets=((to, 0.003), (to + 0.6 * th, 0.003)), near=(hp - th * 0.08, kne, 0.14),
          glow=AND(lambda x, y, z: np.abs(comp(x, y, z, hp, tf) + 0.004) - 0.0017, band(hp, th, 0.0, 0.13)))
    diamond = lambda x, y, z, kne=kne, th=th, to=to: (np.abs(comp(x, y, z, kne, to)) / 0.042
                                                      + np.abs(comp(x, y, z, kne, th) + 0.004) / 0.06 - 1.0) * 0.03
    plate("knee", "shin.L", AND(diamond, H(kne + tf * 0.012, -tf)),
          T=0.014, facets=((tf + 0.8 * to, 0.006), (tf - 0.8 * to, 0.006), (tf - 0.6 * th, 0.006), (tf + 0.6 * th, 0.006)),
          near=(kne - th * 0.08, kne + sv * 0.08, 0.1))
    plate("shin", "shin.L", AND(band(kne, sv, 0.075, 0.37), H(kne, -sf),
                                lambda x, y, z, kne=kne, sv=sv, so=so: (np.abs(comp(x, y, z, kne, so))
                                                                       - (0.05 - 0.07 * np.clip(comp(x, y, z, kne, sv) - 0.075, 0, 0.3)))),
          T=0.012, facets=((sf + 0.7 * so, 0.005), (sf - 0.7 * so, 0.005), (sf - 0.5 * sv, 0.003)), near=(kne, an, 0.09))
    foot = (an + UP * -0.03, np.array((an[0], -0.17, 0.04)), 0.085)
    plate("boot", "foot.L", AND(H((0, 0, 0.047), -Z1), H((0, 0, 0.128), Z1 + 0.25 * Y1)),
          T=0.0075, ch=0.002, facets=(((0, -0.55, 0.83), 0.004), ((1, -0.2, 0.25), 0.003), ((-1, -0.2, 0.25), 0.003)),
          near=foot)
    plate("ankle", "foot.L", AND(ball(an + X1 * 0.046 + UP * 0.016, 0.026), H(an + X1 * 0.02, -X1)),
          T=0.009, facets=((X1, 0.0025), (X1 + 0.7 * UP, 0.002), (X1 - 0.7 * Y1, 0.002)),
          near=(an - UP * 0.05, an + UP * 0.08, 0.08))

log("plates:", len(PLATES), "definitions")
for sp in PLATES:
    build_plate(sp)
log("plates HIGH:", sum(len(sp["high"].data.polygons) for sp in PLATES if sp.get("high")), "quads")

# ====================================================================== helmet
HC = np.array((0.0, 0.02, 1.762))   # cranium centre


def visor_band(x, y, z):
    ax = np.abs(x)
    top = z - (1.766 + 0.16 * ax)
    bot = (1.743 + 0.12 * ax + 0.5 * np.maximum(y + 0.05, 0)) - z
    return np.maximum(np.maximum(top, bot), y - 0.03)


def respirator(x, y, z):
    ax = np.abs(x)
    return np.maximum(np.maximum(np.abs(ax - 0.027) - 0.0145, np.abs(z - 1.672) - 0.021), y + 0.05)


def helmet_field(g):
    X, Y, Z = g.coords()
    AX = np.abs(X)
    d = sdf.Ellipsoid(HC, (0.092, 0.118, 0.103))(X, Y, Z)
    jaw = sdf.Ellipsoid((0, -0.03, 1.684), (0.074, 0.086, 0.084))(X, Y, Z)
    d = sdf.smin(d, jaw, 0.03)
    nape = sdf.RoundBox((0, 0.098, 1.66), (0.076, 0.022, 0.062), sdf.rot((1, 0, 0), 22), 0.01)(X, Y, Z)
    d = sdf.smin(d, nape, 0.02)
    smooth = d
    front = 0.03 - Y
    d = sdf.cmax(d, AX - 0.086, 0.005)                                                   # flat side panels
    d = sdf.cmax(d, np.minimum(0.8 * (AX - 0.06) - 0.6 * (Y + 0.08), front), 0.004)     # cheek facets
    d = sdf.cmax(d, np.minimum(0.88 * (AX - 0.068) - 0.47 * (Z - 1.69), front), 0.004)  # V jaw
    d = sdf.cmax(d, -0.8 * (Y + 0.1) + 0.6 * (Z - 1.8), 0.004)                          # forehead plane
    d = sdf.cmax(d, -0.5 * (Y + 0.1) - 0.866 * (Z - 1.632), 0.004)                     # chin underside
    d = np.maximum(d, (1.602 + 0.1 * (Y + 0.11)) - Z)                                  # flat bottom
    # Raised crest along the top, raised keel down the faceplate, ear pods.
    keel = mx([AX - 0.0062, Z - 1.738, d - 0.003, Y + 0.05])
    d = sdf.cmin(d, keel, 0.001)
    pod = np.maximum(sdf.RoundBox((0, 0.024, 1.742), (0.092, 0.03, 0.028), None, 0.008)(X, Y, Z), 0.05 - AX)
    d = sdf.cmin(d, pod, 0.002)
    # Recesses: visor, respirator, panel line round the faceplate, nape line, pod slit.
    d = carve(d, visor_band(X, Y, Z), 0.0045, k=0.0)
    d = carve(d, mx([np.abs(AX - 0.02) - 0.0011, 1.79 - Z, -(Y + 0.07)]), 0.0014, k=0.0)       # crown panel lines
    d = carve(d, respirator(X, Y, Z), 0.0022)
    for zc in (1.66, 1.672, 1.684):
        d = carve(d, np.maximum(respirator(X, Y, Z) + 0.002, np.abs(Z - zc) - 0.0018), 0.0038)
    d = carve(d, np.maximum(np.abs(Z - (1.7 + 0.2 * (Y - 0.08))) - 0.0012, 0.04 - Y), 0.0015)
    slit = mx([np.abs(Z - 1.742) - 0.0017, np.abs(Y - 0.024) - 0.017, 0.0935 - AX])
    d = carve(d, slit, 0.0016, k=0.0)
    return d


def helmet_materials(c):
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    ax = np.abs(x)
    mi = np.full(len(c), MI["plate"])
    # Material edges sit on geometric creases (faces never straddle a crease), so they stay crisp.
    vb = visor_band(x, y, z)
    mi[vb < 0.0003] = MI["visor"]
    bot = (1.743 + 0.12 * ax + 0.5 * np.maximum(y + 0.05, 0)) - z
    lit = (np.abs(vb) < 0.0003) & (np.abs(bot - vb) < 1e-6)       # the recess's lower wall
    mi[lit] = MI["glow"]
    mi[(ax > 0.0905) & (np.abs(z - 1.742) < 0.02) & (np.abs(y - 0.024) < 0.022)] = MI["trim"]
    slit = mx([np.abs(z - 1.742) - 0.0017, np.abs(y - 0.024) - 0.017, 0.0935 - ax])
    mi[slit < 0.0003] = MI["glow"]
    return mi


log("helmet field")
hg = sdf.Grid((-0.125, -0.15, 1.6), (0.125, 0.17, 1.9), H_HELMET)
HELMET = link(bpy.data.objects.new("helmet_high", sdf.to_mesh("helmet_high", helmet_field(hg), hg)))
set_materials(HELMET, helmet_materials(face_centers(HELMET.data)))
log("helmet HIGH:", len(HELMET.data.polygons), "quads")


# ====================================================================== mirror right-side plates
def mirrored(ob, name):
    me = ob.data.copy()
    me.name = name
    me.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def r_bone(b):
    return b[:-2] + ".R" if b.endswith(".L") else b


RIGID = []   # (high object, bone, low target scale)
for sp in PLATES:
    if not sp.get("high"):
        continue
    RIGID.append((sp["high"], sp["bone"], sp))
    if sp["side"] == "L":
        RIGID.append((mirrored(sp["high"], sp["name"] + "_R"), r_bone(sp["bone"]), sp))
        sp["high"].name = sp["name"] + "_L"
HIGH_PARTS = [SUIT, HELMET] + [r[0] for r in RIGID]


# ====================================================================== preview
def look(cam, loc, target):
    cam.location = V(loc)
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()


def stage():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 20 if QUICK else args.samples
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:  # noqa: BLE001
        sc.cycles.use_denoising = False
    sc.render.resolution_x = 560 if QUICK else 900
    sc.render.resolution_y = 840 if QUICK else 1350
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.6   # black on black: readable on a phone screen
    world = bpy.data.worlds.new("w")
    sc.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.012, 0.014, 0.018, 1)
    bg.inputs[1].default_value = 1.0
    lights = (("key", (2.4, -3.0, 3.0), 170, 1.6, (1.0, 0.93, 0.86)),
              ("rim_l", (-2.4, 2.2, 2.4), 420, 0.6, (0.55, 0.85, 1.0)),
              ("rim_r", (2.6, 2.4, 1.6), 300, 0.6, (0.85, 0.92, 1.0)),
              ("fill", (-3.0, -2.4, 1.0), 25, 3.0, (0.8, 0.85, 1.0)))
    for name, loc, energy, size, colr in lights:
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = colr
        lo = link(bpy.data.objects.new(name, ld))
        look(lo, loc, (0, 0, 1.1))
    floor = bpy.data.meshes.new("floor")
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=64, radius=3.0)
    bm.to_mesh(floor)
    bm.free()
    fo = link(bpy.data.objects.new("floor", floor))
    fm = bpy.data.materials.new("floor")
    fb = fm.node_tree.nodes["Principled BSDF"]
    fb.inputs["Base Color"].default_value = (0.012, 0.013, 0.015, 1)
    fb.inputs["Roughness"].default_value = 0.25
    floor.materials.append(fm)
    cd = bpy.data.cameras.new("cam")
    cam = link(bpy.data.objects.new("cam", cd))
    sc.camera = cam
    return cam


VIEWS = {
    "front": (75, (-22, 4.6, 1.0), 0.97),
    "back": (75, (158, 4.6, 1.0), 0.97),
    "side": (75, (90, 4.6, 1.0), 0.97),
    "hero": (50, (-38, 3.4, 0.45), 1.05),
    "helmet": (100, (-28, 1.15, 1.72), 1.66),
}


def render_views(prefix):
    cam = stage()
    paths = []
    for name in [v for v in args.views.split(",") if v in VIEWS]:
        lens, (ang, dist, h), tz = VIEWS[name]
        cam.data.lens = lens
        a = math.radians(ang)
        look(cam, (math.sin(a) * dist, -math.cos(a) * dist, h), (0, 0, tz))
        path = os.path.abspath(f"{prefix}_{name}.png")
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        log("rendered", path)
    if len(paths) > 1:
        sheet = os.path.abspath(f"{prefix}.png")
        try:
            subprocess.run(["convert", *paths, "+append", "-resize", "x960", sheet], check=True)
            log("sheet", sheet)
        except Exception as e:  # noqa: BLE001
            log("no sheet:", e)
    return paths


if QUICK or args.nobake:
    if args.preview:
        os.makedirs(os.path.dirname(os.path.abspath(args.preview)) or ".", exist_ok=True)
        render_views(args.preview)
    log("quick done")
    sys.exit(0)


# ====================================================================== LOW
def decimate_to(ob, target, symmetric=False):
    n = tris(ob)
    if n > target:
        m = ob.modifiers.new("dec", "DECIMATE")
        m.ratio = target / n
        if symmetric:
            m.use_symmetry = True
            m.symmetry_axis = "X"
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=m.name)


def low_copy(ob, name):
    me = ob.data.copy()
    me.name = name
    return link(bpy.data.objects.new(name, me))


def drop_hidden(ob, below=-0.0012):
    """Delete plate faces that lie wholly inside the suit (the undersides)."""
    me = ob.data
    P = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", P)
    d = BASE.evaluate_points(P.reshape(-1, 3))
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    dead = [f for f in bm.faces if all(d[v.index] < below for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(me)
    bm.free()


def plate_area(ob):
    return sum(p.area for p in ob.data.polygons)


log("LOW")
SUIT_LOW = low_copy(SUIT, "suit_low")
decimate_to(SUIT_LOW, 15000, symmetric=True)
HELMET_LOW = low_copy(HELMET, "helmet_low")
decimate_to(HELMET_LOW, 5200, symmetric=True)
RIGID_LOW = []
low_of = {}
for ob, bone, sp in RIGID:
    if ob.name.endswith("_R"):
        continue
    lo_ob = low_copy(ob, ob.name + "_low")
    drop_hidden(lo_ob)
    target = int(np.clip(plate_area(lo_ob) * 15000, 50, 650))
    decimate_to(lo_ob, target, symmetric=sp["side"] is None)
    low_of[ob.name] = lo_ob
    RIGID_LOW.append((lo_ob, bone))
    if sp["side"] == "L":
        RIGID_LOW.append((mirrored(lo_ob, sp["name"] + "_R_low"), r_bone(bone)))
for ob in [SUIT_LOW]:
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
for ob in [HELMET_LOW] + [r[0] for r in RIGID_LOW]:
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(34))
# Guard: every rigid piece must sit on its bone. (A plate outline that also caught an A-pose arm
# left pieces hanging in the air once the arms came down.)
_SEG = {name: (np.array(head[:]), np.array(tail[:])) for name, head, tail, _p, _r in BONES}
for ob, bone in RIGID_LOW:
    Pv = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", Pv)
    Pv = Pv.reshape(-1, 3)
    a_, b_ = _SEG[bone]
    dv = b_ - a_
    tt = np.clip(((Pv - a_) @ dv) / (dv @ dv), 0, 1)
    far = np.linalg.norm(Pv - (a_ + tt[:, None] * dv), axis=1).max()
    if far > 0.25:
        raise RuntimeError(f"{ob.name} strays {far:.2f} m from bone {bone}")
log("LOW tris: suit", tris(SUIT_LOW), "helmet", tris(HELMET_LOW), "plates", sum(tris(o) for o, _b in RIGID_LOW))


# ====================================================================== weights
def ss(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def chain_weights(P, joints, bones, blends):
    """Weights along a polyline of `joints` (bones: one before, one per segment, one after)."""
    joints = [np.asarray(j, float) for j in joints]
    seg_len = [np.linalg.norm(joints[i + 1] - joints[i]) for i in range(len(joints) - 1)]
    best_d = np.full(len(P), np.inf)
    u = np.zeros(len(P))
    acc = 0.0
    for i in range(len(joints) - 1):
        a, b = joints[i], joints[i + 1]
        dv = b - a
        Ln = seg_len[i]
        t = ((P - a) @ dv) / (Ln * Ln)
        lo = -np.inf if i == 0 else 0.0
        hi = np.inf if i == len(joints) - 2 else 1.0
        tc = np.clip(t, lo, hi)
        dist = np.linalg.norm(P - (a + tc[:, None] * dv), axis=1)
        m = dist < best_d
        best_d[m] = dist[m]
        u[m] = acc + tc[m] * Ln
        acc += Ln
    marks = np.cumsum([0.0] + seg_len)
    W = {}
    carry = np.ones(len(P))
    for k, (Lk, bk) in enumerate(zip(marks, blends)):
        f = ss((u - Lk + bk) / (2 * bk))
        W[bones[k]] = W.get(bones[k], 0) + carry * (1 - f)
        carry = carry * f
    W[bones[len(marks)]] = W.get(bones[len(marks)], 0) + carry
    return W


def seg_dist_np(P, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    dv = b - a
    t = np.clip(((P - a) @ dv) / (dv @ dv), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * dv), axis=1)


def suit_weights(ob):
    me = ob.data
    n = len(me.vertices)
    P = np.empty(n * 3)
    me.vertices.foreach_get("co", P)
    P = P.reshape(-1, 3)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    W = np.zeros((n, len(BONE_NAMES)))
    bi = {b: i for i, b in enumerate(BONE_NAMES)}

    def add_w(mask, wd):
        for b, w in wd.items():
            W[mask, bi[b]] += (w if np.ndim(w) == 0 else w[mask])

    side_L = x > 0
    arm_d = np.minimum.reduce([np.minimum(seg_dist_np(P, A[f"shoulder.{s}"], A[f"elbow.{s}"]),
                                          seg_dist_np(P, A[f"elbow.{s}"], A[f"tip.{s}"])) for s, _ in SIDES])
    torso_score = np.sqrt((x / 0.2) ** 2 + (y / 0.14) ** 2)
    arm_region = (arm_d / 0.078 < torso_score) & (z < 1.56) & (z > 0.75)
    leg_d = np.minimum.reduce([seg_dist_np(P, A[f"hip.{s}"], A[f"ankle.{s}"]) for s, _ in SIDES])
    pelvis_score = np.sqrt((x / 0.18) ** 2 + (y / 0.13) ** 2)
    leg_region = ~arm_region & ((z < 0.88) | ((leg_d / 0.1 < pelvis_score) & (z < 1.0)))
    torso_region = ~arm_region & ~leg_region
    tw = chain_weights(P, [(0, 0, 1.09), (0, 0, 1.27), (0, 0, 1.535), (0, 0, 1.635)],
                       ["hips", "spine", "chest", "neck", "head"], [0.05, 0.05, 0.03, 0.02])
    clav = ss((np.abs(x) - 0.075) / 0.1) * ss((z - 1.33) / 0.1) * 0.65
    chest_w = tw["chest"]
    tw["chest"] = chest_w * (1 - clav)
    tw["clavicle.L"] = chest_w * clav * side_L
    tw["clavicle.R"] = chest_w * clav * ~side_L
    add_w(torso_region, tw)
    for s, m in (("L", side_L), ("R", ~side_L)):
        mask = arm_region & m
        aw = chain_weights(P, [A[f"shoulder.{s}"], A[f"elbow.{s}"], A[f"wrist.{s}"]],
                           [f"clavicle.{s}", f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}"], [0.06, 0.045, 0.02])
        fd = np.minimum.reduce([seg_dist_np(P, a, b) for a, b in FINGERS[s]["fingers"]])
        tdist = np.minimum.reduce([seg_dist_np(P, a, b) for a, b in FINGERS[s]["thumb"]])
        tk = (P - LIMB[s]["kn"]) @ LIMB[s]["hd"]
        fing = mask & (fd < tdist) & (fd < 0.016) & (tk > -0.008)
        fw = ss((tk + 0.008) / 0.012) * fing
        aw[f"fingers.{s}"] = fw * aw[f"hand.{s}"]
        aw[f"hand.{s}"] = aw[f"hand.{s}"] * (1 - fw)
        add_w(mask, aw)
        lmask = leg_region & m
        add_w(lmask, chain_weights(P, [A[f"hip.{s}"], A[f"knee.{s}"], A[f"ankle.{s}"]],
                                   ["hips", f"thigh.{s}", f"shin.{s}", f"foot.{s}"], [0.07, 0.05, 0.03]))
    edges = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    for _ in range(3):
        acc = np.zeros_like(W)
        cnt = np.zeros(n)
        np.add.at(acc, edges[:, 0], W[edges[:, 1]])
        np.add.at(acc, edges[:, 1], W[edges[:, 0]])
        np.add.at(cnt, edges[:, 0], 1)
        np.add.at(cnt, edges[:, 1], 1)
        W = np.where(cnt[:, None] > 0, 0.5 * W + 0.5 * acc / np.maximum(cnt, 1)[:, None], W)
    order = np.argsort(-W, axis=1)
    W2 = np.zeros_like(W)
    rows = np.arange(n)[:, None]
    W2[rows, order[:, :4]] = W[rows, order[:, :4]]
    W2[W2 < 0.01] = 0
    W2 /= np.maximum(W2.sum(1, keepdims=True), 1e-9)
    ob.vertex_groups.clear()
    for j, b in enumerate(BONE_NAMES):
        vg = ob.vertex_groups.new(name=b)
        for i in np.nonzero(W2[:, j] > 0)[0]:
            vg.add([int(i)], float(W2[i, j]), "REPLACE")


def rigid(ob, bone):
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")


log("weights")
suit_weights(SUIT_LOW)
rigid(HELMET_LOW, "head")
for ob, bone in RIGID_LOW:
    rigid(ob, bone)


# ====================================================================== join, unwrap, bake
def join(obs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = name
    j.data.name = name
    return j


LOW = join([SUIT_LOW, HELMET_LOW] + [r[0] for r in RIGID_LOW], "operative")
bm = bmesh.new()
bm.from_mesh(LOW.data)
bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
bm.to_mesh(LOW.data)
bm.free()
log("LOW validate fixed something:", LOW.data.validate(verbose=True))
HIGH = join(HIGH_PARTS, "operative_high")
log("LOW", tris(LOW), "tris; HIGH", tris(HIGH), "tris")


def unwrap(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    # More texels for the helmet and the plates (seen most), fewer under the soles.
    me = ob.data
    uv = me.uv_layers.active.data
    P = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", P)
    P = P.reshape(-1, 3)
    for poly in me.polygons:
        zc = P[list(poly.vertices), 2].mean()
        mname = MAT_ORDER[poly.material_index]
        f = 1.0
        if zc > 1.62 and mname != "suit":
            f = 1.8
        elif mname in ("plate", "trim", "glow"):
            f = 1.15
        elif mname == "sole":
            f = 0.5
        if f != 1.0:
            for li in poly.loop_indices:
                uv[li].uv = uv[li].uv * f
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


log("unwrap")
unwrap(LOW)
tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out or "/tmp/operative/x.gltf")), "textures")
log("bake", args.tex)
TEX = bakeutil.bake_textures(HIGH, LOW, [MAT[k] for k in MAT_ORDER], args.tex, tex_dir, "operative",
                             cage=0.004, ray=0.011, ao_distance=0.035, grime=0.5, log=log)
bakeutil.apply_baked_material(LOW, TEX, "operative", emission_strength=2.5)
HIGH.hide_render = True
HIGH.hide_set(True)
LOW.parent = ARM
mod = LOW.modifiers.new("Armature", "ARMATURE")
mod.object = ARM


# ====================================================================== pose for the preview
def rot_world(bone, axis, deg):
    pb = ARM.pose.bones[bone]
    rest = ARM.data.bones[bone].matrix_local.to_quaternion()
    q = Quaternion(V(axis).normalized(), math.radians(deg))
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = rest.inverted() @ q @ rest


def relaxed_pose():
    for s, sx in SIDES:
        Ls = LIMB[s]
        rot_world(f"upper_arm.{s}", (0, 1, 0), 28 * sx)          # as BodyAppearance._relax_arms
        rot_world(f"forearm.{s}", np.cross(Ls["fa"], FWD), 12)
        rot_world(f"fingers.{s}", np.cross(Ls["hd"], Ls["pn"]), 38)
    bpy.context.view_layer.update()


if args.out:
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ARM.select_set(True)
    LOW.select_set(True)
    bpy.context.view_layer.objects.active = ARM
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(args.out), export_format="GLTF_SEPARATE",
                              export_texture_dir="textures", use_selection=True, export_apply=False,
                              export_skins=True, export_animations=False, export_tangents=True,
                              export_image_format="AUTO", export_yup=True)
    log("exported", args.out)

if args.preview:
    os.makedirs(os.path.dirname(os.path.abspath(args.preview)) or ".", exist_ok=True)
    relaxed_pose()
    render_views(args.preview)
log("done")
