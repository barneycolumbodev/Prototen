"""The operative: the player's base body in the GS-2 graft suit, with and without the helmet.

History (docs/design.md §3.4a): first pass "a crash test dummy"; second pass a gloss carapace; third
pass an undersuit with interface hardware. Fourth pass (owner, 2026-11-05): "the whole design needs to be
more synthetic, nano-weave, smooth, flat plates grafted together on a nylon base and an undersuit, rather
than bulky, mechanical, pre-configured metal shell... a lethal undersuit". No rounded chest plating ("the
massive titties"), no ribbed neck tube. The helmet: "more angular and predatory, maybe like the bottom of
an Oni mask". Plus a version without the helmet, with the owner's own face (owner, 2026-11-05: "I want
the operative to have my face"; physique from the owner's reference photo: heavy traps, capped delts,
wide lats, narrow waist).

Design:
- Undersuit: matte black nanoweave (a fine diagonal weave in the normal map) over the whole body, with
  panel seams. No ribbed flex zones.
- Grafted plates: thin (3-5 mm), flat-faceted, angular outlines, satin black, each one a separate piece
  with a gap of bare weave around it: split pectoral plates with straight lower edges, paired abdominal
  plates, serratus slats, trap yoke plates, scapula and lat plates, segmented spine, deltoid caps,
  triceps and forearm strips, back-of-hand and knuckle plates, split quad plates, outer thigh strips,
  diamond knees, shin strips, faceted boots. Gunmetal hardpoint pads with a light dot (shoulders,
  forearms, thighs) where part hardware docks.
- Neck: bare weave up to a clean seal under the jaw, low angular collar plates. No rings.
- Helmet: low faceted cranium with a central ridge, a hard brow over a narrow V visor (inner corners
  low), and an oni-style lower mask: two cheek planes meeting at a keel, flared cheek ridges, a snarl-shaped
  mouth recess with vertical vent slots, a pointed chin; flat nape lames at the back.
- Head (helmet off): the owner's face from raw_assets/characters/operative/likeness (MediaPipe landmarks
  averaged over his photos; the front photo unwrapped and re-toned, see likeness/capture.py), on a
  sculpted skull with ears and a neck that disappears into the seal; curly hair as clustered curl volumes.

Construction (all procedural, rebuildable):
- Same skeleton as the triad (bone names and A-pose), scaled to 1.86 m, so animations, ragdolls and part
  sockets carry over.
- Signed distance fields (raw_assets/_lib/sdf.py) meshed with surface nets. Plates are shells of the
  anatomy field cut by outline planes, chamfered, with flat facets.
- The head's front is the base skull shrink-projected onto the landmark face mesh, weighted by how far the
  photo can be trusted; its colour is computed per texel (photo inside the face, procedural skin and hair
  elsewhere).
- Three meshes, two materials: suit + helmet share one baked atlas (the helmet is its own mesh so it can be
  hidden), the head has its own (base colour, ORM, normal). Suit skinned with analytic weights; plates
  rigid on one bone each; helmet rigid on the head; head blends head/neck.

Run:
  tools/blender.sh raw_assets/characters/operative/build.py --out assets/characters/operative/operative.gltf \
      --preview docs/previews/operative
  Design check without the bake (coarse, fast): --quick --preview /tmp/op [--only helmet,head]
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
from mathutils.bvhtree import BVHTree  # noqa: E402
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
ap.add_argument("--views", default="front,back,side,hero,bare,helmet,head")
ap.add_argument("--only", default="suit,helmet,head", help="parts to build (design iteration)")
args = ap.parse_args(argv)
QUICK = args.quick
ONLY = set(args.only.split(","))
HERE = os.path.dirname(os.path.abspath(__file__))
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


def material(name, base, rough, metal=0.0, emission=None, bump=0.0, bump_scale=900.0, weave=0.0):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    N, Lk = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    height = None
    if bump > 0:
        tex = N.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        height = tex.outputs["Fac"]
    if weave > 0:
        # Nanoweave: two diagonal band sets (x+y+z and -x+y+z) multiplied into a fine diamond weave.
        tc = N.new("ShaderNodeTexCoord")
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (-1.0, 1.0, 1.0)
        Lk.new(tc.outputs["Object"], mp.inputs["Vector"])
        w1, w2 = N.new("ShaderNodeTexWave"), N.new("ShaderNodeTexWave")
        for w in (w1, w2):
            w.bands_direction = "DIAGONAL"
            w.inputs["Scale"].default_value = weave
            w.inputs["Distortion"].default_value = 0.0
            w.inputs["Detail"].default_value = 0.0
        Lk.new(tc.outputs["Object"], w1.inputs["Vector"])
        Lk.new(mp.outputs["Vector"], w2.inputs["Vector"])
        mul = N.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        Lk.new(w1.outputs["Fac"], mul.inputs[0])
        Lk.new(w2.outputs["Fac"], mul.inputs[1])
        height = mul.outputs["Value"]
        bump = bump or 0.25
    if height is not None:
        b = N.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.0004 if weave else 0.0002
        Lk.new(height, b.inputs["Height"])
        Lk.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


MAT = {
    "suit": material("op_weave", (0.016, 0.017, 0.019), 0.6, weave=70.0, bump=0.35),
    "plate": material("op_plate", (0.0085, 0.009, 0.0102), 0.34),
    "trim": material("op_trim", (0.12, 0.125, 0.13), 0.34, metal=0.95),
    "visor": material("op_visor", (0.03, 0.03, 0.036), 0.04, metal=1.0),
    "glow": material("op_glow", SEAGLASS, 0.3, emission=(SEAGLASS, 4.0)),
    "sole": material("op_sole", (0.016, 0.016, 0.017), 0.88, bump=0.3, bump_scale=300),
    "seal": material("op_seal", (0.02, 0.021, 0.024), 0.45),
}
MAT_ORDER = ["suit", "plate", "trim", "visor", "glow", "sole", "seal"]
MI = {k: i for i, k in enumerate(MAT_ORDER)}

# ====================================================================== anatomy (BASE field)
E, RC, RB = sdf.Ellipsoid, sdf.RoundCone, sdf.RoundBox
BASE = sdf.Model()
add = BASE.add


def ry(deg):
    return sdf.rot((0, 1, 0), deg)


# Torso (owner's reference: heavy traps, capped delts, wide lats, a narrow waist). The pectorals are broad
# and flat-fronted (a box, not an ellipsoid) so nothing reads as a bust under the plates.
add(E((0, 0.012, 1.31), (0.152, 0.114, 0.17)))                       # ribcage
add(E((0, 0.02, 1.44), (0.182, 0.1, 0.082)), k=0.04)                 # shoulder girdle
add(E((0, 0.006, 1.13), (0.122, 0.09, 0.12)), k=0.05)                # waist
add(E((0, 0.014, 0.99), (0.148, 0.104, 0.1)), k=0.05)                # pelvis
add(E((0, -0.052, 1.17), (0.092, 0.042, 0.13)), k=0.03)              # abdominal wall
add(RC((0, 0.018, 1.47), (0, 0.012, 1.66), 0.084, 0.07), k=0.03)    # neck (thick)
for s, sx in SIDES:
    add(E((0.118 * sx, 0.035, 1.3), (0.08, 0.075, 0.15), ry(16 * sx)), k=0.03)      # lats (V-taper)
    add(RB((0.078 * sx, -0.064, 1.385), (0.072, 0.022, 0.05), ry(-12 * sx), 0.022), k=0.03)  # pectorals: flat slabs
    add(RC((0, 0.052, 1.585), (0.165 * sx, 0.032, 1.48), 0.058, 0.04), k=0.045)     # trapezius (heavy)
    add(E((0.11 * sx, -0.022, 1.11), (0.045, 0.062, 0.09)), k=0.03)                   # obliques
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
    add(E(sh + ua * 0.035 + uo * 0.016, (0.1, 0.072, 0.072), sdf.frame(ua, uo)), k=0.025)   # deltoid (capped)
    add(RC(sh, el, 0.052, 0.041), k=0.02)
    add(E(sh + ua * 0.165 + uf * 0.017, (0.1, 0.049, 0.048), sdf.frame(ua, uo)), k=0.015)   # biceps
    add(E(sh + ua * 0.125 - uf * 0.02, (0.11, 0.05, 0.047), sdf.frame(ua, uo)), k=0.015)    # triceps
    add(sdf.Sphere(el + uf * 0.004, 0.041), k=0.02)
    add(RC(el, wr, 0.045, 0.029), k=0.015)
    add(E(el + fa * 0.075 + fo * 0.006, (0.095, 0.052, 0.044), sdf.frame(fa, fo)), k=0.02)  # forearm mass
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


# The neck seal: the suit ends in a clean, slightly flared lip under the jaw (front low, back high).
def seal_z(y):
    return 1.618 + 0.3 * y


SUITF = BASE.copy()
SUITF.fn((-0.2, -0.2, 1.5), (0.2, 0.2, 1.75),
         lambda f, x, y, z: sdf.cmax(f, z - F32(1.0) * seal_z(y), 0.003))

# ====================================================================== undersuit detail (HIGH only)
DETAIL = SUITF.copy()


def groove(f, g, width, depth):
    """Rounded channel where |g| < width."""
    return f + F32(depth) * np.maximum(0.0, 1.0 - (g / F32(width)) ** 2)


# Panel seams: outer leg, inner arm, back of leg, glutes, torso sides, inguinal V, sole welt, and a
# seam ring a little below the neck seal.
for s, sx in SIDES:
    L = LIMB[s]
    hp, an = L["hp"], L["an"]

    def leg_seam(f, x, y, z, hp=hp, an=an, sx=sx):
        yc = F32(hp[1]) + (z - F32(hp[2])) * F32((an[1] - hp[1]) / (an[2] - hp[2]))
        w = sdf.ss((x * F32(sx) - 0.12) / 0.015) * sdf.ss((z - 0.14) / 0.03) * sdf.ss((0.93 - z) / 0.03)
        return groove(f, y - yc, 0.0022, 0.0013 * w)
    DETAIL.fn((0.0 if sx > 0 else -0.35, -0.2, 0.1), (0.35 if sx > 0 else 0.0, 0.2, 1.0), leg_seam)
    sh = L["sh"]

    def arm_seam(f, x, y, z, sh=sh, ua=L["ua"], uf=L["ua_fr"], uo=L["ua_out"]):
        t = comp(x, y, z, sh, ua)
        g = comp(x, y, z, sh, uf)
        w = sdf.ss((t - 0.09) / 0.02) * sdf.ss((0.27 - t) / 0.02) * sdf.ss(-comp(x, y, z, sh, uo) / 0.01)
        return groove(f, g, 0.0022, 0.0013 * w)
    DETAIL.fn(np.minimum(sh, L["el"]) - 0.08, np.maximum(sh, L["el"]) + 0.08, arm_seam)

    def back_leg(f, x, y, z, L=L):
        hp, an = L["hp"], L["an"]
        xc = F32(hp[0]) + (z - F32(hp[2])) * F32((an[0] - hp[0]) / (an[2] - hp[2]))
        w = sdf.ss((y - 0.02) / 0.015) * sdf.ss((z - 0.16) / 0.03) * sdf.ss((0.86 - z) / 0.03)
        return groove(f, x - xc, 0.0022, 0.0013 * w)
    DETAIL.fn((L["hp"][0] - 0.15, -0.1, 0.1), (L["hp"][0] + 0.15, 0.2, 0.9), back_leg)
DETAIL.fn((-0.25, 0.0, 0.84), (0.25, 0.2, 1.08),
          lambda f, x, y, z: groove(f, z - (0.905 + 0.25 * np.abs(np.abs(x) - 0.07)), 0.0022,
                                    0.0013 * sdf.ss((y - 0.04) / 0.02) * sdf.ss((np.abs(x) - 0.012) / 0.01)))
DETAIL.fn((-0.3, -0.1, 0.92), (0.3, 0.12, 1.5),
          lambda f, x, y, z: groove(f, y - 0.014, 0.0022,
                                    0.0013 * sdf.ss((np.abs(x) - 0.1) / 0.02) * sdf.ss((1.46 - z) / 0.03) * sdf.ss((z - 0.95) / 0.03)))
DETAIL.fn((-0.2, -0.2, 0.86), (0.2, 0.05, 1.1),
          lambda f, x, y, z: groove(f, 0.86 * (np.abs(x) - 0.03) - 0.5 * (z - 0.92), 0.0022,
                                    0.0013 * sdf.ss((0.0 - y) / 0.02) * sdf.ss((1.06 - z) / 0.02) * sdf.ss((np.abs(x) - 0.035) / 0.01)))
DETAIL.fn((-0.3, -0.3, -0.01), (0.3, 0.2, 0.06), lambda f, x, y, z: groove(f, z - 0.043, 0.0025, 0.0015))
DETAIL.fn((-0.15, -0.15, 1.5), (0.15, 0.15, 1.72),
          lambda f, x, y, z: groove(f, z - (seal_z(y) - 0.016), 0.0016, 0.0011))

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


def set_materials(ob, mat_idx, mats=None, order=None):
    mats, order = mats or MAT, order or MAT_ORDER
    ob.data.materials.clear()
    for k in order:
        ob.data.materials.append(mats[k])
    ob.data.polygons.foreach_set("material_index", np.asarray(mat_idx, dtype=np.int32))


SUIT = None
if "suit" in ONLY:
    log("suit field")
    g = sdf.Grid((-0.68, -0.23, -0.012), (0.68, 0.23, 1.72), H_BODY)
    F = DETAIL.evaluate(g)
    SUIT = link(bpy.data.objects.new("suit_high", sdf.to_mesh("suit_high", F, g)))
    del F
    c = face_centers(SUIT.data)
    mi = np.full(len(c), MI["suit"])
    mi[c[:, 2] < 0.036] = MI["sole"]
    mi[c[:, 2] > seal_z(c[:, 1]) - 0.0035] = MI["seal"]
    set_materials(SUIT, mi)
    log("suit HIGH:", len(SUIT.data.polygons), "quads")

# ====================================================================== grafted plates
PLATES = []


def plate(name, bone, region, T=0.0045, B=-0.004, ch=0.0016, facets=(), inset=None, glow=None, mat="plate",
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


def mx(arrs):
    out = arrs[0]
    for a in arrs[1:]:
        out = np.maximum(out, a)
    return out


def carve(d, region, depth, k=0.0012):
    """Remove a `depth` skin of d inside `region` (a recess that follows the surface). Edges are
    rounded by k: perfectly sharp concave creases stair-step in surface nets."""
    return sdf.smax(d, -np.maximum(region, -(d + F32(depth))), k)


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
        mxd = len(fc) > 2 and fc[2]
        pl = (np.abs(X) if mxd else X) * F32(n[0]) + Y * F32(n[1]) + Z * F32(n[2])
        inside = d < 0
        if not inside.any():
            break
        top = float(pl[inside].max())
        d = sdf.cmax(d, pl - F32(top - depth), sp["ch"] * 0.8)
    if sp["inset"]:
        margin, depth = sp["inset"]
        d = carve(d, R + F32(margin), depth, k=0.0009)
    if sp["glow"]:
        d = carve(d, sp["glow"](X, Y, Z), 0.0012, k=0.0)
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


X1, Y1, Z1 = np.eye(3)
_LA = LIMB["L"]
_off_arm = MX(lambda x, y, z: -seg(_LA["sh"] + _LA["ua"] * 0.03, _LA["el"] + _LA["fa"] * 0.1, 0.085)(x, y, z))
OFF_ARM = AND(_off_arm, MX(H((0.2, 0, 0), X1)))   # torso plates stay on the torso, off the arms


def off_neck(r):
    return lambda x, y, z: F32(r) - np.sqrt(x * x + (y - 0.015) ** 2)


FLAT = ((0.0, -1.0, 0.0), 0.006)
# ---------------------------------------------------------------- torso front
# Pectoral plates: one flat sheet per side with a straight lower edge rising to the armpit, a
# channel of bare weave down the sternum. Faceted into planes, never a rounded cup.
plate("pec", "chest", AND(H((0.011, 0, 0), -X1), H((0, 0, 1.452), (-0.15, 0, 1)), H((0, 0, 1.322), (0.32, 0, -1)),
                          H((0.152, 0, 1.4), (1, 0, -0.3)), H((0, -0.02, 0), Y1), OFF_ARM, off_neck(0.09)),
      T=0.0048, facets=(((0.0, -1.0, 0.0), 0.007), ((0.55, -0.83, 0.0), 0.004), ((0.0, -0.72, 0.7), 0.005),
                        ((0.0, -0.8, -0.6), 0.004)))
plate("clav", "chest", AND(H((0.03, 0, 0), -X1), H((0, 0, 1.462), (0.15, 0, -1)), H((0, 0, 1.51), (-0.1, 0, 1)),
                           H((0.135, 0, 0), X1), H((0, -0.012, 0), Y1), off_neck(0.092), OFF_ARM),
      T=0.004, facets=(((0.0, -0.5, 0.86), 0.004),))
for i in range(3):
    zc = 1.262 - 0.066 * i
    plate(f"abs{i}", "spine" if i < 2 else "hips",
          AND(H((0.009, 0, 0), -X1), H((0, 0, zc + 0.028), (0.14, 0, 1)), H((0, 0, zc - 0.026), (-0.14, 0, -1)),
              H((0.074 - 0.004 * i, 0, zc), (1, 0, -0.35)), H((0, -0.02, 0), Y1), OFF_ARM),
          T=0.0042, facets=(((0.0, -1.0, 0.0), 0.004), ((0.62, -0.78, 0.0), 0.003), ((0.0, -0.7, -0.7), 0.003)))
SERR = nrm((0.0, -0.55, 0.835))
for i in range(3):
    plate(f"serratus{i}", "chest" if i < 2 else "spine",
          AND(band((0, 0, 1.3 - 0.037 * i), SERR, -0.0105, 0.0105), H((0.102, 0, 0), -X1), H((0, -0.088, 0), -Y1),
              H((0, 0.03, 0), Y1), H((0, -0.01, 1.36), (0, 0.6, 1)), OFF_ARM),
          T=0.0038, facets=(((1, -0.3, 0), 0.002),))
# ---------------------------------------------------------------- yoke, back
plate("trap", "chest", AND(H((0, 0, 1.468), -Z1), H((0.168, 0, 0), X1), H((0, -0.03, 0), -Y1), H((0, 0.085, 0), Y1),
                           off_neck(0.094), OFF_ARM),
      T=0.0046, facets=(((0.38, 0.0, 0.92), 0.005), ((0.0, -0.6, 0.8), 0.004), ((0.0, 0.6, 0.8), 0.004)))
plate("scapula", "chest", AND(H((0.02, 0, 0), -X1), H((0, 0.035, 0), -Y1), H((0, 0, 1.462), (0.22, 0, 1)),
                              H((0.02, 0, 1.36), (-0.6, 0, -1)), H((0.168, 0, 0), X1), OFF_ARM),
      T=0.0048, facets=(((0.55, 0.83, 0.0), 0.004), ((0, 0.75, 0.66), 0.004), ((0.0, 1.0, 0.0), 0.006)))
plate("lat", "spine", AND(H((0.036, 0, 0), -X1), H((0, 0.03, 0), -Y1), H((0.018, 0, 1.338), (0.6, 0, 1)),
                          H((0, 0, 1.2), (0.3, 0, -1)), H((0.165, 0, 0), X1), OFF_ARM),
      T=0.0042, facets=(((0.6, 0.8, 0.0), 0.004),))
for i, zc in enumerate((1.44, 1.376, 1.312, 1.248, 1.184, 1.12)):
    bone = "chest" if zc > 1.3 else ("spine" if zc > 1.15 else "hips")
    plate(f"spine{i}", bone, AND(MX(H((0.02, 0, 0), X1)), H((0, 0, zc + 0.024), Z1), MX(H((0, 0, zc - 0.028), (1.0, 0, -1))),
                                 H((0, 0.06, 0), -Y1), OFF_ARM),
          T=0.0052, side=None, facets=(((0.7, 0.7, 0.0), 0.002, True), ((0.0, 1.0, 0.0), 0.003)))
plate("lumbar", "hips", AND(H((0.03, 0, 0), -X1), H((0.11, 0, 0), X1), H((0, 0, 1.17), (-0.2, 0, 1)),
                             H((0, 0, 1.07), -Z1), H((0, 0.045, 0), -Y1), OFF_ARM),
      T=0.004, facets=(((0.5, 0.86, 0), 0.0025),))
# ---------------------------------------------------------------- arms
for s, sx in (("L", 1.0),):
    L = LIMB[s]
    sh, el, wr, kn = L["sh"], L["el"], L["wr"], L["kn"]
    ua, uo, uf = L["ua"], L["ua_out"], L["ua_fr"]
    fa, fo, ff = L["fa"], L["fa_out"], L["fa_fr"]
    hd, pn, hw = L["hd"], L["pn"], L["hw"]
    plate("delt", "upper_arm.L", AND(H(sh + ua * 0.082, ua), H(sh - uo * 0.012, -uo), H((0.138, 0, 0), -X1),
                                     band(sh, uf, -0.07, 0.07)),
          T=0.0058, facets=(((0.3, 0, 1), 0.005), ((1, 0, 0.1), 0.005), ((0.35, -0.9, 0.3), 0.005),
                            ((0.35, 0.9, 0.3), 0.005)),
          near=(sh, el, 0.11))
    plate("delt_lame", "upper_arm.L", AND(band(sh, ua, 0.092, 0.128), H(sh + uo * 0.004, -uo), band(sh, uf, -0.055, 0.055)),
          T=0.0048, facets=((uo, 0.003),), near=(sh, el, 0.09))
    plate("tricep", "upper_arm.L", AND(band(sh, ua, 0.145, 0.25), H(sh + uo * 0.0, -uo), band(sh, uf, -0.042, 0.03)),
          T=0.0042, facets=((uo + 0.75 * uf, 0.0025), (uo - 0.75 * uf, 0.0025)), near=(sh, el, 0.09))
    plate("elbow", "forearm.L", ball(el - uf * 0.036 + uo * 0.006, 0.024),
          T=0.006, facets=((-uf + 0.8 * uo, 0.004), (-uf - 0.8 * uo, 0.004), (-uf + 0.8 * ua, 0.004), (-uf - 0.8 * ua, 0.004)),
          near=(el - ua * 0.05, el + fa * 0.05, 0.08))
    taper = lambda x, y, z, el=el, fa=fa, ff=ff: (np.abs(comp(x, y, z, el, ff))
                                                  - (0.042 - 0.06 * np.clip(comp(x, y, z, el, fa) - 0.045, 0, 0.2)))
    plate("forearm", "forearm.L", AND(band(el, fa, 0.05, 0.236), H(el - fo * 0.008, -fo), taper),
          T=0.0046, facets=((fo + 0.75 * ff, 0.003), (fo - 0.75 * ff, 0.003)), near=(el, wr, 0.08))
    plate("hand", "hand.L", AND(band(wr, hd, 0.02, 0.09), H(wr - pn * 0.004, pn), band(wr, hw, -0.04, 0.04)),
          T=0.004, facets=((-pn, 0.0015),), near=(wr, kn, 0.06))
    plate("knuckles", "fingers.L", AND(band(kn, hd, 0.004, 0.032), H(kn - pn * 0.002, pn), band(kn, hw, -0.042, 0.042)),
          T=0.0038, facets=((-pn + 0.5 * hd, 0.0015),), near=(kn - hd * 0.02, kn + hd * 0.06, 0.05))
# ---------------------------------------------------------------- legs
for s, sx in (("L", 1.0),):
    L = LIMB[s]
    hp, kne, an, bl = L["hp"], L["knee"], L["an"], L["ball"]
    th, to, tf = L["th"], L["th_out"], L["th_fr"]
    sv, so, sf = L["sv"], L["sv_out"], L["sv_fr"]
    thigh_taper = lambda x, y, z, hp=hp, th=th, to=to: (np.abs(comp(x, y, z, hp, to) - 0.008)
                                                         - (0.062 - 0.1 * np.clip(comp(x, y, z, hp, th) - 0.15, 0, 0.25)))
    quad = AND(lambda x, y, z: (0.15 - 0.55 * comp(x, y, z, hp, to)) - comp(x, y, z, hp, th),
               H(hp + th * 0.375, th), H(hp, -tf), thigh_taper)
    split = lambda x, y, z, hp=hp, to=to: comp(x, y, z, hp, to) - 0.008
    plate("quad_out", "thigh.L", AND(quad, lambda x, y, z, f=split: F32(0.004) - f(x, y, z)),
          T=0.0048, facets=((tf + 0.6 * to, 0.005), (tf, 0.004)), near=(hp, kne, 0.13))
    plate("quad_in", "thigh.L", AND(quad, lambda x, y, z, f=split: f(x, y, z) + F32(0.004)),
          T=0.0048, facets=((tf - 0.6 * to, 0.005), (tf, 0.004)), near=(hp, kne, 0.13))
    plate("thigh_side", "thigh.L", AND(band(hp, th, 0.23, 0.36), H(hp + to * 0.02, -to), band(hp, tf, -0.045, 0.04)),
          T=0.0045, facets=((to, 0.003), (to + 0.6 * th, 0.002)), near=(hp, kne, 0.14))
    diamond = lambda x, y, z, kne=kne, th=th, to=to: (np.abs(comp(x, y, z, kne, to)) / 0.04
                                                      + np.abs(comp(x, y, z, kne, th) + 0.004) / 0.058 - 1.0) * 0.03
    plate("knee", "shin.L", AND(diamond, H(kne + tf * 0.012, -tf)),
          T=0.0065, facets=((tf + 0.8 * to, 0.005), (tf - 0.8 * to, 0.005), (tf - 0.6 * th, 0.005), (tf + 0.6 * th, 0.005)),
          near=(kne - th * 0.08, kne + sv * 0.08, 0.1))
    plate("shin", "shin.L", AND(band(kne, sv, 0.08, 0.37), H(kne, -sf),
                                lambda x, y, z, kne=kne, sv=sv, so=so: (np.abs(comp(x, y, z, kne, so))
                                                                       - (0.044 - 0.06 * np.clip(comp(x, y, z, kne, sv) - 0.08, 0, 0.3)))),
          T=0.0048, facets=((sf + 0.7 * so, 0.004), (sf - 0.7 * so, 0.004), (sf - 0.5 * sv, 0.003)), near=(kne, an, 0.09))
    foot = (an + UP * -0.03, np.array((an[0], -0.17, 0.04)), 0.085)
    plate("boot", "foot.L", AND(H((0, 0, 0.047), -Z1), H((0, 0, 0.128), Z1 + 0.25 * Y1)),
          T=0.0055, ch=0.0018, facets=(((0, -0.55, 0.83), 0.004), ((1, -0.2, 0.25), 0.003), ((-1, -0.2, 0.25), 0.003)),
          near=foot)
    plate("ankle", "foot.L", AND(ball(an + X1 * 0.046 + UP * 0.016, 0.026), H(an + X1 * 0.02, -X1)),
          T=0.0055, facets=((X1, 0.0025), (X1 + 0.7 * UP, 0.002), (X1 - 0.7 * Y1, 0.002)),
          near=(an - UP * 0.05, an + UP * 0.08, 0.08))


def _out(c, near):
    a, b = np.asarray(near[0], float), np.asarray(near[1], float)
    u = b - a
    t = np.clip((c - a) @ u / (u @ u), 0, 1)
    return nrm(c - (a + t * u))


def hardpoint(name, bone, c, r, near):
    """A flat gunmetal mounting pad with a light dot, standing proud of the plate it sits on."""
    c = np.asarray(c, float)
    plate(name, bone, ball(c, r), T=0.0088, ch=0.0012, mat="trim", facets=((_out(c, near), 0.0025),),
          glow=ball(c + _out(c, near) * 0.009, 0.0028), near=near)


_L = LIMB["L"]
hardpoint("hp_shoulder", "upper_arm.L", _L["sh"] + _L["ua"] * 0.04 + _L["ua_out"] * 0.092, 0.017, (_L["sh"], _L["el"], 0.1))
hardpoint("hp_forearm", "forearm.L", _L["el"] + _L["fa"] * 0.14 + _L["fa_out"] * 0.04, 0.014, (_L["el"], _L["wr"], 0.07))
hardpoint("hp_thigh", "thigh.L", _L["hp"] + _L["th"] * 0.29 + _L["th_out"] * 0.075, 0.018, (_L["hp"], _L["knee"], 0.12))
if "suit" in ONLY:
    log("plates:", len(PLATES), "definitions")
    for sp in PLATES:
        build_plate(sp)
    log("plates HIGH:", sum(len(sp["high"].data.polygons) for sp in PLATES if sp.get("high")), "quads")

# ====================================================================== helmet
def visor_v(x, y, z):
    """The V visor: brow line falls toward the centre (inner corners low), two eye slits split by a
    thin bridge, wrapping round to the sides."""
    ax = np.abs(x)
    top = z - (1.751 + 0.3 * ax)
    bot = (1.7355 + 0.36 * ax) - z
    return mx([top, bot, y + 0.004, 0.0045 - ax])


def mouth_region(x, y, z):
    """Snarl-shaped mouth recess: corners turned down, the lower edge pointed under the centre."""
    ax = np.abs(x)
    top = z - (1.705 - 0.32 * ax)
    bot = (1.679 - 0.2 * ax + 0.5 * np.maximum(0.0, 0.016 - ax)) - z
    return mx([top, bot, ax - 0.04, y + 0.075])


FANGS = (0.0, 0.0115, 0.023)


def fang_fins(x):
    ax = np.abs(x)
    d = np.abs(ax - F32(FANGS[0])) - 0.0021
    for xi in FANGS[1:]:
        d = np.minimum(d, np.abs(ax - F32(xi)) - 0.0021)
    return d


def side_panel(x, y, z):
    ax = np.abs(x)
    u, v = y - 0.02, z - 1.758
    return mx([np.abs(u) - 0.034, np.abs(v) - 0.022, 0.72 * np.abs(u) + np.abs(v) - 0.036, 0.07 - ax])


def menpo(X, Y, Z, AX):
    """The oni-style lower mask: a faceted muzzle with flared cheeks (planes, chamfered edges)."""
    planes = [
        0.75 * AX - 0.66 * (Y + 0.15),                       # prow: cheek planes meeting at a keel
        0.95 * (AX - 0.085) - 0.31 * (Y + 0.02),             # flared cheeks
        0.6 * (AX - 0.058) - 0.8 * (Z - 1.652),              # cheek flare narrows to the jaw
        -0.94 * (Y + 0.15) - 0.34 * (Z - 1.708),             # front face: nose forward, chin back
        -0.55 * (Y + 0.132) - 0.835 * (Z - 1.642),           # chin underside
        0.62 * AX - 0.2 * (Y + 0.124) - 0.76 * (Z - 1.636),  # V jaw: chin bevels (pointed chin)
        (1.612 + 0.1 * (Y + 0.1)) - Z,                       # jaw line
        Z - (1.749 + 0.42 * np.minimum(Y + 0.07, 0.0) - 0.25 * AX),  # top: nose bridge down to the tip, cheekbones
        Y - 0.05,
    ]
    d = planes[0]
    for pl in planes[1:]:
        d = sdf.cmax(d, pl, 0.0035)
    return d


def cut(d, plane, ch=0.004):
    return sdf.cmax(d, plane, ch)


def helmet_sdf(X, Y, Z):
    AX = np.abs(X)
    d = sdf.Ellipsoid((0, 0.016, 1.778), (0.096, 0.122, 0.114))(X, Y, Z)
    nape = sdf.RoundBox((0, 0.086, 1.678), (0.08, 0.036, 0.064), sdf.rot((1, 0, 0), 14), 0.01)(X, Y, Z)
    d = sdf.smin(d, nape, 0.02)
    jaw = sdf.Ellipsoid((0, 0.0, 1.69), (0.084, 0.07, 0.07))(X, Y, Z)
    d = sdf.smin(d, jaw, 0.02)
    # A faceted skull: flat sides, a roof on a central ridge, bevelled upper sides and corners, and a
    # forehead that is itself a keel (recedes at the sides), so the brow points forward like a prow.
    d = cut(d, AX - 0.091, 0.005)
    d = cut(d, 0.4 * AX + 0.916 * (Z - 1.893))
    d = cut(d, 0.8 * (AX - 0.083) + 0.6 * (Z - 1.835))
    d = cut(d, 0.45 * (AX - 0.05) - 0.55 * (Y + 0.088) + 0.7 * (Z - 1.85))
    d = cut(d, -0.72 * (Y + 0.106) + 0.58 * (Z - 1.79) + 0.38 * AX)
    d = cut(d, 0.7 * (AX - 0.083) - 0.71 * (Y + 0.055))
    d = cut(d, 0.65 * (Y - 0.085) + 0.76 * (Z - 1.855))
    d = cut(d, 0.6 * (AX - 0.072) + 0.8 * (Y - 0.085))
    d = cut(d, 0.9 * (Y - 0.114) - 0.43 * (Z - 1.66))
    d = np.maximum(d, (1.612 + 0.1 * (Y + 0.1)) - Z)
    d = sdf.cmin(d, menpo(X, Y, Z, AX), 0.003)
    shell = d
    # Raised: crown keel, nose keel down the prow, oni cheek ridges (mouth corner up to the cheekbone).
    keel = mx([AX - 0.0055, shell - 0.0028, 1.79 - Z, Y - 0.1])
    d = sdf.cmin(d, keel, 0.0008)
    nose = mx([AX - 0.0045, shell - 0.0025, Z - 1.738, 1.712 - Z])
    d = sdf.cmin(d, nose, 0.0008)
    ridge = np.maximum(seg((0.04, -0.118, 1.684), (0.076, -0.07, 1.724), 0.006)(AX, Y, Z), shell - 0.0042)
    d = sdf.cmin(d, ridge, 0.001)
    jawr = np.maximum(seg((0.05, -0.1, 1.648), (0.088, -0.02, 1.64), 0.005)(AX, Y, Z), shell - 0.003)
    d = sdf.cmin(d, jawr, 0.001)
    # Recesses: visor (deep, under the brow), mouth with vanes, side sensor panels, the mask seam, nape
    # lame steps.
    d = carve(d, visor_v(X, Y, Z), 0.0078, k=0.0)
    d = carve(d, np.maximum(mouth_region(X, Y, Z), -fang_fins(X)), 0.0065, k=0.0006)
    d = carve(d, mouth_region(X, Y, Z), 0.0018, k=0.0)
    d = carve(d, np.abs(side_panel(X, Y, Z)) - 0.0011, 0.0013, k=0.0)
    seam = mx([np.abs(0.8 * (Y + 0.0) + 0.6 * (Z - 1.744)) - 0.0011, 0.06 - AX, 1.66 - Z])
    d = carve(d, seam, 0.0014, k=0.0)
    for zc in (1.668, 1.642):
        d = carve(d, mx([np.abs(Z - zc - 0.15 * (Y - 0.09)) - 0.0012, 0.05 - Y]), 0.0016, k=0.0)
    return d


def helmet_materials(c):
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    ax = np.abs(x)
    mi = np.full(len(c), MI["plate"])
    vb = visor_v(x, y, z)
    mi[vb < 0.0003] = MI["visor"]
    bot = (1.7355 + 0.36 * ax) - z
    lit = (np.abs(vb) < 0.0003) & (np.abs(bot - vb) < 1e-6) & (ax > 0.012)
    mi[lit] = MI["glow"]
    mouth = np.maximum(mouth_region(x, y, z), -fang_fins(x))
    mi[(mouth < 0.0003) & (y > -0.125)] = MI["trim"]
    sp = side_panel(x, y, z)
    mi[(sp < -0.0012) & (ax > 0.085)] = MI["trim"]
    slit = mx([np.abs(z - 1.762) - 0.0016, np.abs(y - 0.006) - 0.014, 0.0885 - ax])
    mi[slit < 0.0] = MI["glow"]
    return mi


HELMET = None
if "helmet" in ONLY:
    log("helmet field")
    hg = sdf.Grid((-0.11, -0.145, 1.595), (0.11, 0.16, 1.915), H_HELMET)
    HX, HY, HZ = hg.coords()
    hd = helmet_sdf(HX, HY, HZ)
    # Sensor slit: a shallow cut in the side panel.
    hd = carve(hd, mx([np.abs(HZ - 1.762) - 0.0016, np.abs(HY - 0.006) - 0.014, 0.0885 - np.abs(HX)]), 0.0012, k=0.0)
    HELMET = link(bpy.data.objects.new("helmet_high", sdf.to_mesh("helmet_high", hd, hg)))
    del hd, HX, HY, HZ
    set_materials(HELMET, helmet_materials(face_centers(HELMET.data)))
    log("helmet HIGH:", len(HELMET.data.polygons), "quads")

# ====================================================================== head (helmet off): the owner's face
LIKE = os.path.join(HERE, "likeness")
FACE_O = np.array((0.0, -0.082, 1.762))     # where the landmark frame's origin (between the eyes) sits
HAIR_LO = (0.16, 0.105, 0.065)                # sRGB, from the owner's photos: brown roots, golden tips
HAIR_HI = (0.52, 0.4, 0.27)
HMAT = {
    "skin": material("op_skin", (0.25, 0.15, 0.13), 0.5, bump=0.06, bump_scale=2200),
    "hair": material("op_hair", (0.08, 0.05, 0.03), 0.62),
}
HMAT_ORDER = ["skin", "hair"]


class Torus(sdf.Prim):
    """Ring of radius R about axis n through c, tube radius r (a curl loop)."""

    def __init__(self, c, n, R, r):
        self.c, self.n, self.R, self.r = np.asarray(c, float), nrm(n), float(R), float(r)

    def aabb(self):
        m = self.R + self.r
        return self.c - m, self.c + m

    def __call__(self, x, y, z):
        px, py, pz = x - F32(self.c[0]), y - F32(self.c[1]), z - F32(self.c[2])
        h = px * F32(self.n[0]) + py * F32(self.n[1]) + pz * F32(self.n[2])
        q = np.sqrt(np.maximum(px * px + py * py + pz * pz - h * h, 0.0)) - F32(self.R)
        return np.sqrt(q * q + h * h) - F32(self.r)


def face_mesh():
    """The owner's landmark face (likeness/face_shape.npy) with eyes and mouth closed over, canonical UVs,
    smoothed by two subdivision levels."""
    P = np.load(os.path.join(LIKE, "face_shape.npy")).astype(float) + FACE_O
    T = np.load(os.path.join(LIKE, "face_tris.npy"))
    UVc = np.load(os.path.join(LIKE, "face_uv.npy"))
    me = bpy.data.meshes.new("face_ref")
    me.from_pydata([tuple(p) for p in P], [], [tuple(int(i) for i in t) for t in T])
    bm = bmesh.new()
    bm.from_mesh(me)
    # The canonical mesh is wound toward +Y in Blender's frame; normals must face forward (-Y).
    bm.normal_update()
    if np.mean([f.normal.y for f in bm.faces]) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=30)          # eyes and mouth, not the outer rim
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = tuple(UVc[lp.vert.index])
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new("face_ref", me))
    apply_mod(ob, "SUBSURF", levels=2, render_levels=2, uv_smooth="PRESERVE_BOUNDARIES")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.hide_render = True
    return ob


def load_face_tex():
    """likeness/face_tex.png as an (h, w, 4) array of raw sRGB-encoded values, row 0 = v 0."""
    img = bpy.data.images.load(os.path.join(LIKE, "face_tex.png"))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def face_data(ob):
    me = ob.data
    nv = len(me.vertices)
    V3 = np.empty(nv * 3)
    me.vertices.foreach_get("co", V3)
    V3 = V3.reshape(-1, 3)
    LV = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", LV)
    LUV = np.empty(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", LUV)
    LUV = LUV.reshape(-1, 2)
    LS = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", LS)
    tri_v = np.stack([LV[LS + i] for i in range(3)], 1)
    tri_uv = np.stack([LUV[LS + i] for i in range(3)], 1)
    bvh = BVHTree.FromPolygons([tuple(v) for v in V3], [tuple(t) for t in tri_v])
    return dict(V=V3, tri_v=tri_v, tri_uv=tri_uv, bvh=bvh)


FACE_TEX = None


def face_sample(fd, P, max_dist=0.03):
    """For points P: (uv (N,2), dist (N,), normal (N,3), hit mask)."""
    n = len(P)
    loc = np.zeros((n, 3))
    idx = np.full(n, -1, np.int64)
    dist = np.full(n, np.inf)
    nor = np.zeros((n, 3))
    bvh = fd["bvh"]
    for i in range(n):
        r = bvh.find_nearest(V(P[i]), max_dist)
        if r[0] is not None:
            loc[i] = r[0][:]
            nor[i] = r[1][:]
            idx[i] = r[2]
            dist[i] = r[3]
    hit = idx >= 0
    uv = np.zeros((n, 2))
    if hit.any():
        tv = fd["V"][fd["tri_v"][idx[hit]]]                 # (m, 3, 3)
        p = loc[hit]
        v0, v1, v2 = tv[:, 0], tv[:, 1], tv[:, 2]
        e0, e1, ep = v1 - v0, v2 - v0, p - v0
        d00, d01, d11 = (e0 * e0).sum(1), (e0 * e1).sum(1), (e1 * e1).sum(1)
        d20, d21 = (ep * e0).sum(1), (ep * e1).sum(1)
        den = np.maximum(d00 * d11 - d01 * d01, 1e-18)
        b1 = (d11 * d20 - d01 * d21) / den
        b2 = (d00 * d21 - d01 * d20) / den
        b0 = 1 - b1 - b2
        tuv = fd["tri_uv"][idx[hit]]
        uv[hit] = tuv[:, 0] * b0[:, None] + tuv[:, 1] * b1[:, None] + tuv[:, 2] * b2[:, None]
    return uv, dist, nor, hit


def tex_lookup(T, uv):
    """Bilinear lookup in an (h, w, c) array with v = 0 at row 0."""
    h, w = T.shape[:2]
    x = np.clip(uv[:, 0] * w - 0.5, 0, w - 1.001)
    y = np.clip(uv[:, 1] * h - 0.5, 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    a = T[y0, x0] * (1 - fx) + T[y0, x0 + 1] * fx
    b = T[y0 + 1, x0] * (1 - fx) + T[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
             176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]


def skull_model():
    m = sdf.Model()
    m.add(E((0, 0.012, 1.79), (0.078, 0.1, 0.098)))                       # cranium
    # Jaw and cheek sides from the owner's own face outline: capsules from each lower outline point
    # (inset) back to the ear line and down to the neck, so the sculpted sides meet the real jawline.
    P = np.load(os.path.join(LIKE, "face_shape.npy")).astype(float) + FACE_O
    centre = np.array((0.0, 0.0, 1.73))
    for i in FACE_OVAL:
        p = P[i]
        if p[2] > 1.775:
            continue
        p_in = p + nrm(centre - p) * 0.012
        q = np.array((p[0] * 0.8, 0.03, max(p[2], 1.66) + 0.01))
        m.add(RC(p_in, q, 0.011, 0.03), k=0.012)
    m.add(E((0, -0.03, 1.72), (0.064, 0.056, 0.08)), k=0.03)              # face mass (sits behind the face)
    m.add(RC((0, 0.024, 1.53), (0, 0.03, 1.7), 0.064, 0.054), k=0.03)     # neck (ends inside the seal)
    for sx in (1.0, -1.0):
        Rear = sdf.rot((0, 0, 1), 22 * sx) @ sdf.rot((0, 1, 0), 8 * sx)
        ear_c = np.array((0.079 * sx, 0.016, 1.748))
        m.add(E(ear_c, (0.0065, 0.021, 0.031), Rear), k=0.004)                                # ear
        m.sub(E(ear_c + np.array((0.0055 * sx, -0.003, -0.004)), (0.0035, 0.012, 0.016), Rear), k=0.002)  # concha
        m.add(E((0.073 * sx, 0.006, 1.742), (0.007, 0.012, 0.016)), k=0.006)   # ear root
    return m


def hairline(x, y):
    h = np.interp(y, [-0.14, -0.085, -0.055, -0.02, 0.035, 0.07, 0.14], [1.8, 1.8, 1.792, 1.786, 1.78, 1.725, 1.69])
    temple = sdf.ss((np.abs(x) - 0.04) / 0.03) * sdf.ss((-y - 0.03) / 0.03) * 0.008
    return h + temple


def hair_cap(x, y, z):
    """Hair volume over the cranium: thin at the hairline, thick on top."""
    hl = hairline(x, y)
    t = 0.004 + 0.021 * sdf.ss((z - hl) / 0.05)
    cap = sdf.Ellipsoid((0, 0.012, 1.79), (0.077, 0.1, 0.098))(x, y, z) - t
    return sdf.smax(cap, F32(1.0) * (hl - z), 0.004)


def hair_model(rng):
    m = sdf.Model()
    m.fn((-0.12, -0.14, 1.62), (0.12, 0.15, 1.96), lambda f, x, y, z: np.minimum(f, hair_cap(x, y, z) + 0.003))
    # Curl volumes on the cap (Fibonacci-spread, jittered), then small ringlet loops among them.
    C0, R0 = np.array((0, 0.012, 1.79)), np.array((0.077, 0.1, 0.098))
    n = 2400
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n)
    th = math.pi * (1 + 5 ** 0.5) * k
    U = np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), np.cos(phi)], 1)
    base = C0 + U * R0
    keep = base[:, 2] > hairline(base[:, 0], base[:, 1]) - 0.01
    cnt = 0
    for p0, u in zip(base[keep], U[keep]):
        nv_ = nrm(u / R0)
        hl = hairline(np.array([p0[0]]), np.array([p0[1]]))[0]
        t = 0.004 + 0.021 * float(sdf.ss(np.array((p0[2] - hl) / 0.05)))
        p = p0 + nv_ * t
        r = rng.uniform(0.0052, 0.0072) * (0.75 + 0.35 * t / 0.025)
        m.add(sdf.Sphere(p + rng.normal(0, 0.0025, 3), r), k=0.0024)
        cnt += 1
        if rng.random() < 0.6:
            ax = nrm(nv_ + rng.normal(0, 0.8, 3))
            m.add(Torus(p + nv_ * r * 0.7 + rng.normal(0, 0.002, 3), ax,
                        rng.uniform(0.0034, 0.0046), rng.uniform(0.0012, 0.0016)), k=0.0014)
    log("hair curls:", cnt)
    return m


def upsample2(c, shape):
    """Linear 2x upsampling of a coarse field sampled at fine[::2, ::2, ::2] back to `shape`."""
    out = c
    for ax in range(3):
        n = shape[ax]
        a = np.moveaxis(out, ax, 0)
        f = np.empty((n,) + a.shape[1:], a.dtype)
        f[0::2] = a[:(n + 1) // 2]
        mid = 0.5 * (a[:-1] + a[1:])
        f[1::2] = mid[:n // 2] if len(mid) >= n // 2 else np.concatenate([mid, a[-1:]])[:n // 2]
        out = np.moveaxis(f, 0, ax)
    return out


def face_field(fd, X, Y, Z, S):
    """Signed distance to the owner's face surface and the photo's trust at the nearest point, for
    grid points near the front of the skull field S (others: +1 and 0)."""
    sel = np.nonzero((np.abs(S) < 0.04) & (Y < 0.05) & (Z > 1.6) & (Z < 1.85))
    P = np.stack([X[sel], Y[sel], Z[sel]], 1).astype(float)
    n = len(P)
    dist = np.full(n, 1.0)
    sgn = np.ones(n)
    loc = np.zeros((n, 3))
    idx = np.full(n, -1, np.int64)
    bvh = fd["bvh"]
    for i in range(n):
        r = bvh.find_nearest(V(P[i]), 0.05)
        if r[0] is not None:
            loc[i] = r[0][:]
            dist[i] = r[3]
            idx[i] = r[2]
            sgn[i] = 1.0 if (V(P[i]) - r[0]).dot(r[1]) >= 0 else -1.0
    hit = idx >= 0
    uv, _d, _n, _h = face_sample(fd, loc[hit], 1e-4) if hit.any() else (np.zeros((0, 2)), 0, 0, 0)
    alpha = np.zeros(n)
    alpha[hit] = tex_lookup(FACE_TEX[..., 3:4], uv)[:, 0]
    Df = np.ones(X.shape, np.float32)
    A = np.zeros(X.shape, np.float32)
    Df[sel] = sgn * dist
    A[sel] = np.clip(alpha * 1.25, 0, 1) * sdf.ss((0.045 - dist) / 0.015)
    return Df, A


HEAD = HAIR = FACE = None
if "head" in ONLY:
    log("head")
    rng = np.random.default_rng(7)
    FACE_TEX = load_face_tex()
    FACE = face_mesh()
    FD = face_data(FACE)
    skull = skull_model()
    hh = 0.0012 if not QUICK else 0.002
    gh = sdf.Grid((-0.11, -0.16, 1.55), (0.11, 0.14, 1.9), hh)
    S = skull.evaluate(gh)
    X, Y, Z = (np.broadcast_to(c, S.shape) for c in gh.coords())
    # The face: a 35 mm slab behind the owner's face surface, morphed in over the skull by the photo's
    # trust (the rim of the landmark mesh fades back to the sculpted skull). Evaluated at half
    # resolution (BVH queries) and upsampled.
    sl = (slice(None, None, 2),) * 3
    Dc, Ac = face_field(FD, X[sl], Y[sl], Z[sl], S[sl])
    Df, Wf = upsample2(Dc, S.shape), upsample2(Ac, S.shape)
    slab = np.maximum(Df, -(Df + 0.035))
    Hf = (1 - Wf) * S + Wf * np.minimum(slab, S + 0.014)
    del Df, Wf, slab, X, Y, Z
    HEAD = link(bpy.data.objects.new("head_high", sdf.to_mesh("head_high", Hf, gh)))
    del Hf, S
    log("head HIGH:", len(HEAD.data.polygons), "quads")
    log("hair field")
    hm = hair_model(rng)
    ghh = sdf.Grid((-0.12, -0.14, 1.66), (0.12, 0.15, 1.97), 0.0011 if not QUICK else 0.0018)
    HAIR = link(bpy.data.objects.new("hair_high", sdf.to_mesh("hair_high", hm.evaluate(ghh), ghh)))
    log("hair HIGH:", len(HAIR.data.polygons), "quads")
    set_materials(HEAD, np.zeros(len(HEAD.data.polygons)), HMAT, HMAT_ORDER)
    set_materials(HAIR, np.ones(len(HAIR.data.polygons)), HMAT, HMAT_ORDER)

# ---------------------------------------------------------------- head colour (per point: texels or verts)
EYE_RINGS = ([33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
             [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466])
LIP_RING = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]


def noise3(P, scale, seed=0):
    """Value noise in [0, 1] (trilinear over a hashed lattice)."""
    Q = np.asarray(P, float) * scale + seed * 17.13
    i = np.floor(Q).astype(np.int64)
    f = Q - i
    f = f * f * (3 - 2 * f)

    def h(dx, dy, dz):
        n = (i[:, 0] + dx) * 73856093 ^ (i[:, 1] + dy) * 19349663 ^ (i[:, 2] + dz) * 83492791 ^ (seed * 2654435761)
        n = (n ^ (n >> 13)) * 1274126177
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * h(dx, dy, dz)
    return out


def in_poly(uv, poly):
    x, y = uv[:, 0], uv[:, 1]
    inside = np.zeros(len(uv), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cross = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0)
        inside ^= cross
    return inside


def head_colour(P, hair):
    """sRGB colour (N, 3) and roughness (N,) for head points P; `hair` marks hair points."""
    tex = FACE_TEX
    trusted = tex[..., 3] > 0.9
    skin0 = tex[..., :3][trusted].mean(0)
    n = len(P)
    col = np.tile(skin0, (n, 1))
    rough = np.full(n, 0.5)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    col *= (1 + 0.07 * (noise3(P, 70, 1) - 0.5))[:, None] * np.array((0.95, 0.86, 0.84))
    fr = np.clip((noise3(P, 1100, 2) - 0.66) / 0.12, 0, 1) * (0.35 + 0.4 * noise3(P, 40, 3))
    col = col * (1 - 0.32 * fr[:, None]) + np.array((0.08, 0.02, -0.01)) * fr[:, None]
    ear = sdf.ss((np.abs(x) - 0.066) / 0.01) * sdf.ss((1.79 - z) / 0.01) * sdf.ss((z - 1.7) / 0.01)
    col *= (1 + np.stack([0.06 * ear, -0.03 * ear, -0.03 * ear], 1))
    stub = sdf.ss((1.668 - z) / 0.02) * sdf.ss((z - 1.6) / 0.025) * sdf.ss((0.035 - y) / 0.03)
    sn = np.clip((noise3(P, 2600, 4) - 0.45) / 0.3, 0, 1)
    col = col * (1 - (0.3 * stub * sn)[:, None]) + (np.array((0.44, 0.31, 0.22)) * (0.3 * stub * sn)[:, None])
    # The face itself, from the photo.
    sk = ~hair
    if sk.any():
        uv, dist, _n, hit = face_sample(FD, P[sk], 0.008)
        a = tex_lookup(tex[..., 3:4], uv)[:, 0] * hit * sdf.ss((0.008 - np.where(hit, dist, 1)) / 0.004)
        fc = tex_lookup(tex[..., :3], uv)
        cs = col[sk]
        col[sk] = cs * (1 - a[:, None]) + fc * a[:, None]
        UVc = np.load(os.path.join(LIKE, "face_uv.npy"))
        rs = rough[sk]
        for ring in EYE_RINGS:
            rs[in_poly(uv, UVc[ring]) & hit] = 0.12
        rs[in_poly(uv, UVc[LIP_RING]) & hit] = 0.36
        rough[sk] = rs
    if hair.any():
        Ph = P[hair]
        t = np.clip((hair_cap(Ph[:, 0], Ph[:, 1], Ph[:, 2]) + 0.002) / 0.014, 0, 1) ** 0.8
        lo, hi = np.array(HAIR_LO), np.array(HAIR_HI)
        hc = lo + (hi - lo) * t[:, None]
        hc *= (0.82 + 0.36 * noise3(Ph, 500, 5))[:, None]
        hc *= (0.9 + 0.2 * noise3(Ph * np.array((1, 1, 0.25)), 3000, 6))[:, None]   # strand streaks
        col[hair] = hc
        rough[hair] = 0.6
    return np.clip(col, 0, 1), rough


def paint_vertices(ob, hair):
    """Preview only: head colour as a vertex colour attribute read by the HIGH materials."""
    me = ob.data
    P = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", P)
    P = P.reshape(-1, 3)
    col, _r = head_colour(P, np.full(len(P), hair))
    lin = np.where(col <= 0.04045, col / 12.92, ((col + 0.055) / 1.055) ** 2.4)
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", np.hstack([lin, np.ones((len(lin), 1))]).astype(np.float32).ravel())
    for m in HMAT.values():
        nt = m.node_tree
        if not nt.nodes.get("vcol"):
            a = nt.nodes.new("ShaderNodeVertexColor")
            a.name = "vcol"
            a.layer_name = "Col"
            nt.links.new(a.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])


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


RIGID = []   # (high object, bone, plate spec)
for sp in PLATES:
    if not sp.get("high"):
        continue
    RIGID.append((sp["high"], sp["bone"], sp))
    if sp["side"] == "L":
        RIGID.append((mirrored(sp["high"], sp["name"] + "_R"), r_bone(sp["bone"]), sp))
        sp["high"].name = sp["name"] + "_L"
SUIT_PARTS = ([SUIT] if SUIT else []) + [r[0] for r in RIGID]
VIS = {"suit": SUIT_PARTS, "helmet": [HELMET] if HELMET else [], "head": [o for o in (HEAD, HAIR) if o]}


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


# name: (lens, (angle, distance, height), target z, show helmet)
VIEWS = {
    "front": (75, (-22, 4.6, 1.0), 0.97, True),
    "back": (75, (158, 4.6, 1.0), 0.97, True),
    "side": (75, (90, 4.6, 1.0), 0.97, True),
    "hero": (50, (-38, 3.4, 0.45), 1.05, True),
    "bare": (50, (-38, 3.4, 0.45), 1.05, False),
    "helmet": (100, (-32, 1.2, 1.78), 1.755, True),
    "head": (100, (-24, 1.15, 1.79), 1.765, False),
    "helmet_front": (100, (-4, 1.2, 1.77), 1.755, True),
    "helmet_side": (100, (78, 1.2, 1.77), 1.755, True),
    "head_side": (100, (70, 1.15, 1.79), 1.765, False),
}


def render_views(prefix):
    cam = stage()
    paths = []
    for name in [v for v in args.views.split(",") if v in VIEWS]:
        lens, (ang, dist, h), tz, helm = VIEWS[name]
        if not VIS["helmet" if helm else "head"]:
            continue
        for o in VIS["helmet"]:
            o.hide_render = not helm
        for o in VIS["head"]:
            o.hide_render = helm
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
    if HEAD:
        paint_vertices(HEAD, False)
        paint_vertices(HAIR, True)
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


def smooth(obs, angle=None):
    for ob in obs:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        if angle is None:
            bpy.ops.object.shade_smooth()
        else:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


log("LOW")
SUIT_LOW = low_copy(SUIT, "suit_low")
decimate_to(SUIT_LOW, 15000, symmetric=True)
HELMET_LOW = low_copy(HELMET, "helmet_low")
decimate_to(HELMET_LOW, 6000, symmetric=True)
HEAD_LOW = low_copy(HEAD, "head_low")
decimate_to(HEAD_LOW, 5200)
HAIR_LOW = low_copy(HAIR, "hair_low")
apply_mod(HAIR_LOW, "REMESH", mode="VOXEL", voxel_size=0.0028)   # curl loops would block the decimator
decimate_to(HAIR_LOW, 4200)
RIGID_LOW = []
for ob, bone, sp in RIGID:
    if ob.name.endswith("_R"):
        continue
    lo_ob = low_copy(ob, ob.name + "_low")
    drop_hidden(lo_ob)
    if len(lo_ob.data.polygons) == 0:
        log("  plate hidden under the suit, dropped:", ob.name)
        bpy.data.objects.remove(lo_ob)
        continue
    target = int(np.clip(plate_area(lo_ob) * 15000, 50, 600))
    decimate_to(lo_ob, target, symmetric=sp["side"] is None)
    RIGID_LOW.append((lo_ob, bone))
    if sp["side"] == "L":
        RIGID_LOW.append((mirrored(lo_ob, sp["name"] + "_R_low"), r_bone(bone)))
smooth([SUIT_LOW, HEAD_LOW, HAIR_LOW])
smooth([HELMET_LOW] + [r[0] for r in RIGID_LOW], 34)
# Guard: every rigid piece must sit on its bone.
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
log("LOW tris: suit", tris(SUIT_LOW), "plates", sum(tris(o) for o, _b in RIGID_LOW), "helmet", tris(HELMET_LOW),
    "head", tris(HEAD_LOW), "hair", tris(HAIR_LOW))


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


def write_weights(ob, W):
    me = ob.data
    n = len(me.vertices)
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


def verts(ob):
    P = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", P)
    return P.reshape(-1, 3)


def suit_weights(ob):
    P = verts(ob)
    n = len(P)
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
    tw = chain_weights(P, [(0, 0, 1.09), (0, 0, 1.27), (0, 0, 1.535), (0, 0, 1.66)],
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
    write_weights(ob, W)


def head_weights(ob):
    """Head mesh: the head bone, blending to the neck down where the neck enters the seal."""
    P = verts(ob)
    W = np.zeros((len(P), len(BONE_NAMES)))
    h = ss((P[:, 2] - 1.6) / 0.06)
    W[:, BONE_NAMES.index("head")] = h
    W[:, BONE_NAMES.index("neck")] = 1 - h
    write_weights(ob, W)


def rigid(ob, bone):
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")


log("weights")
suit_weights(SUIT_LOW)
rigid(HELMET_LOW, "head")
head_weights(HEAD_LOW)
rigid(HAIR_LOW, "head")
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


def clean(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.validate()


def tag(ob, value):
    a = ob.data.attributes.new("part", "INT", "FACE")
    a.data.foreach_set("value", np.full(len(ob.data.polygons), value, np.int32))


def unwrap(ob, boost):
    """Smart-project, scale islands by boost(poly centre, material name), pack."""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    me = ob.data
    uv = me.uv_layers.active.data
    names = [m.name for m in me.materials]
    C = face_centers(me)
    for poly, c in zip(me.polygons, C):
        f = boost(c, names[poly.material_index])
        if f != 1.0:
            for li in poly.loop_indices:
                uv[li].uv = uv[li].uv * f
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def body_boost(c, mname):
    if c[2] > 1.6 and mname != "op_weave":
        return 1.7          # helmet
    if mname in ("op_plate", "op_trim", "op_glow"):
        return 1.15
    if mname == "op_sole":
        return 0.5
    return 1.0


def head_boost(c, mname):
    if mname == "op_skin" and c[1] < -0.03 and 1.63 < c[2] < 1.83:
        return 2.2          # the face
    if mname == "op_hair":
        return 0.8
    return 1.0


tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out or "/tmp/operative/x.gltf")), "textures")
BODY_PARTS = [SUIT_LOW] + [r[0] for r in RIGID_LOW]
for o in BODY_PARTS:
    tag(o, 0)
tag(HELMET_LOW, 1)
ATLAS = join(BODY_PARTS + [HELMET_LOW], "operative")
clean(ATLAS)
HIGH = join(SUIT_PARTS + [HELMET], "operative_high")
log("atlas LOW", tris(ATLAS), "tris; HIGH", tris(HIGH), "tris")
unwrap(ATLAS, body_boost)
log("bake body", args.tex)
TEX = bakeutil.bake_textures(HIGH, ATLAS, [MAT[k] for k in MAT_ORDER], args.tex, tex_dir, "operative",
                             cage=0.004, ray=0.011, ao_distance=0.035, grime=0.5, log=log)
bakeutil.apply_baked_material(ATLAS, TEX, "operative", emission_strength=2.5)
HIGH.hide_render = True
HIGH.hide_set(True)

# Split the helmet back out (same material and atlas; its own mesh so the game can take it off).
bpy.ops.object.select_all(action="DESELECT")
ATLAS.select_set(True)
bpy.context.view_layer.objects.active = ATLAS
part = np.empty(len(ATLAS.data.polygons), np.int32)
ATLAS.data.attributes["part"].data.foreach_get("value", part)
ATLAS.data.polygons.foreach_set("select", part == 1)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
BODY = ATLAS
HELM = [o for o in bpy.context.selected_objects if o is not BODY][0]
HELM.name = HELM.data.name = "operative_helmet"
for o in (BODY, HELM):
    o.data.attributes.remove(o.data.attributes["part"])
log("split: body", tris(BODY), "helmet", tris(HELM))

# ---------------------------------------------------------------- head: bake normal/AO, colour per texel
HEADM = join([HEAD_LOW, HAIR_LOW], "operative_head")
clean(HEADM)
HEAD_HIGH = join([HEAD, HAIR], "head_high_all")
unwrap(HEADM, head_boost)
HSIZE = args.tex
log("bake head", HSIZE)
for m in HMAT.values():   # the preview vertex-colour node is not used in the bake
    v = m.node_tree.nodes.get("vcol")
    if v:
        m.node_tree.nodes.remove(v)
HTEX = bakeutil.bake_textures(HEAD_HIGH, HEADM, [HMAT[k] for k in HMAT_ORDER], HSIZE, tex_dir, "operative_head",
                              cage=0.004, ray=0.012, ao_distance=0.03, grime=0.0, log=log)
HEAD_HIGH.hide_render = True
HEAD_HIGH.hide_set(True)


def bake_attr(ob, mats, img, mode):
    """Emission bake of the LOW's own geometry: 'position' (world, float) or 'hair' (1 on hair)."""
    sc = bpy.context.scene
    for m in mats:
        nt = m.node_tree
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "attr_emit"
        if mode == "position":
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            geo.name = "attr_geo"
            nt.links.new(geo.outputs["Position"], em.inputs["Color"])
        else:
            v = 1.0 if m.name == "op_hair" else 0.0
            em.inputs["Color"].default_value = (v, v, v, 1)
        nt.links.new(em.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
        node = nt.nodes.get("bake_target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "bake_target"
        node.image = img
        nt.nodes.active = node
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc.cycles.samples = 1
    bpy.ops.object.bake(type="EMIT", use_selected_to_active=False, margin=12, use_clear=True)
    for m in mats:
        nt = m.node_tree
        nt.links.new(nt.nodes["Principled BSDF"].outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
        for nm in ("attr_emit", "attr_geo"):
            if nt.nodes.get(nm):
                nt.nodes.remove(nt.nodes[nm])
    a = np.empty(HSIZE * HSIZE * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


pos_img = bpy.data.images.new("head_pos", HSIZE, HSIZE, alpha=False, float_buffer=True)
pos_img.colorspace_settings.name = "Non-Color"
POS = bake_attr(HEADM, [HMAT[k] for k in HMAT_ORDER], pos_img, "position")[:, :3]
msk_img = bpy.data.images.new("head_mask", HSIZE, HSIZE, alpha=False, float_buffer=True)
msk_img.colorspace_settings.name = "Non-Color"
HAIRMASK = bake_attr(HEADM, [HMAT[k] for k in HMAT_ORDER], msk_img, "hair")[:, 0] > 0.5
valid = np.linalg.norm(POS, axis=1) > 0.5
log("head texels:", int(valid.sum()), "hair:", int((HAIRMASK & valid).sum()))
colour = np.zeros((HSIZE * HSIZE, 3))
rough = np.full(HSIZE * HSIZE, 0.5)
idx = np.nonzero(valid)[0]
for chunk in np.array_split(idx, 16):
    c_, r_ = head_colour(POS[chunk], HAIRMASK[chunk])
    colour[chunk], rough[chunk] = c_, r_
ao = np.empty(HSIZE * HSIZE * 4, np.float32)
HTEX["orm"].pixels.foreach_get(ao)
ao = ao.reshape(-1, 4)
colour *= (0.7 + 0.3 * ao[:, 0])[:, None]
base_px = np.ones((HSIZE * HSIZE, 4), np.float32)
base_px[:, :3] = colour
HTEX["basecolor"].pixels.foreach_set(base_px.ravel())
HTEX["basecolor"].save()
ao[:, 1] = rough
ao[:, 2] = 0.0
HTEX["orm"].pixels.foreach_set(ao.ravel())
HTEX["orm"].save()
os.remove(HTEX["emission"].filepath_raw)


def apply_head_material(ob, tex):
    mat = bpy.data.materials.new("operative_head")
    nt = mat.node_tree
    N, L_ = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]

    def img(i):
        n = N.new("ShaderNodeTexImage")
        n.image = i
        return n
    L_.new(img(tex["basecolor"]).outputs["Color"], bsdf.inputs["Base Color"])
    sep = N.new("ShaderNodeSeparateColor")
    L_.new(img(tex["orm"]).outputs["Color"], sep.inputs["Color"])
    L_.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    L_.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    occl = N.new("ShaderNodeGroup")
    occl.node_tree = bakeutil._gltf_output_group()
    L_.new(sep.outputs["Red"], occl.inputs["Occlusion"])
    nmap = N.new("ShaderNodeNormalMap")
    L_.new(img(tex["normal"]).outputs["Color"], nmap.inputs["Color"])
    L_.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    try:
        bsdf.inputs["Subsurface Weight"].default_value = 0.0
    except KeyError:
        pass
    mat.use_backface_culling = True
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.material_index = 0


apply_head_material(HEADM, HTEX)
for o in (BODY, HELM, HEADM):
    o.parent = ARM
    md = o.modifiers.new("Armature", "ARMATURE")
    md.object = ARM
FACE.hide_render = True
log("final tris: body", tris(BODY), "helmet", tris(HELM), "head", tris(HEADM))


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
    for o in (ARM, BODY, HELM, HEADM):
        o.select_set(True)
    bpy.context.view_layer.objects.active = ARM
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(args.out), export_format="GLTF_SEPARATE",
                              export_texture_dir="textures", use_selection=True, export_apply=False,
                              export_skins=True, export_animations=False, export_tangents=True,
                              export_image_format="AUTO", export_yup=True)
    log("exported", args.out)

if args.preview:
    os.makedirs(os.path.dirname(os.path.abspath(args.preview)) or ".", exist_ok=True)
    VIS.update({"suit": [BODY], "helmet": [HELM], "head": [HEADM]})
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in (BODY, HELM, HEADM) and o.name != "floor":
            o.hide_render = True
    relaxed_pose()
    render_views(args.preview)
log("done")
