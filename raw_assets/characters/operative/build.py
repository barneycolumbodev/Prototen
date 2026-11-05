"""The operative: the player's base body in the CS-1 carapace (owner, 2026-11-05).

"A dude in a black synth suit... a really sleek-looking black carapace over
his body. That's what our baseline augmented soldiers should look like. The
different passives and actives can change the look." (Reference given: the
suit Lex Luthor wears under the mech in Injustice.)

Construction (all procedural, rebuildable):
- Same skeleton as the triad (bone names and A-pose), scaled to a 1.86 m
  heavily built man, so animations and ragdoll setups carry over.
- Undersuit: metaball families (athletic, heavily muscled), unioned with a
  voxel remesh, smoothed, decimated. Matte charcoal synthetic.
- Carapace: each plate is a patch of the body surface cut out with planes
  (bmesh bisect: clean, straight panel edges), lifted, given thickness and
  bevelled, so plates sit exactly on the body with gaps between them:
  chest halves, three abdominal bands, back plate and spine ridge, shoulder
  caps, upper-arm and forearm guards, hand backs, thigh plates, knee caps,
  shin guards, boot caps, and a closed helmet with a dark visor.
- Seam lights: thin seaglass strips in a few gaps (visor slit, collar, spine,
  forearms, waist) that echo the HUD.
- Skinned with bone-heat weights; plates are rigid on one bone each.
- Sockets for part hardware are the bones themselves (BodyAppearance).

Run:
  tools/blender.sh raw_assets/characters/operative/build.py -- --out assets/characters/operative/operative.gltf \\
      --preview docs/previews/operative
"""
import argparse
import math
import os
import sys
import time

import bpy
import bmesh
from mathutils import Matrix, Vector

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=32)
args = ap.parse_args(argv)
T0 = time.time()


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

# ====================================================================== materials
MATS = {
    # name: (base colour, roughness, metallic, emission strength)
    "suit": ((0.012, 0.013, 0.015), 0.55, 0.0, 0.0),
    "plate": ((0.012, 0.012, 0.014), 0.24, 0.35, 0.0),
    "visor": ((0.004, 0.006, 0.008), 0.06, 0.6, 0.0),
    "glow": ((0.36, 0.86, 0.78), 0.4, 0.0, 6.0),
}
MAT = {}
for n, (col, rough, metal, emit) in MATS.items():
    m = bpy.data.materials.new(n)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = emit
    MAT[n] = m

# ====================================================================== undersuit (metaballs)
MB = 1.0 / 0.52


class Family:
    def __init__(self, name, res=0.012):
        self.mb = bpy.data.metaballs.new(name)
        self.mb.resolution = res
        self.mb.render_resolution = res
        self.mb.threshold = 0.6
        self.ob = bpy.data.objects.new(name, self.mb)
        COL.objects.link(self.ob)

    def ball(self, p, r):
        e = self.mb.elements.new(type="BALL")
        e.co = V(p)
        e.radius = r * MB

    def taper(self, p0, p1, r0, r1, n=5):
        p0, p1 = V(p0), V(p1)
        for i in range(n + 1):
            t = i / n
            self.ball(p0.lerp(p1, t), r0 + (r1 - r0) * t)

    def ell(self, p, radii, along=None):
        """Ellipsoid; `along` turns its X radius along that direction."""
        e = self.mb.elements.new(type="ELLIPSOID")
        e.co = V(p)
        e.radius = MB
        e.size_x, e.size_y, e.size_z = radii
        if along is not None:
            e.rotation = V((1, 0, 0)).rotation_difference(V(along).normalized())


def P(x, y, z):
    return V((x, y, z)) * S


def build_body():
    fams = []
    t = Family("torso")
    t.ell(P(0, 0.004, 0.982), (0.138, 0.1, 0.1))           # pelvis
    t.ell(P(0, -0.004, 1.1), (0.128, 0.094, 0.115))         # waist
    t.ell(P(0, 0.006, 1.27), (0.168, 0.112, 0.15))          # ribcage
    for sx in (1, -1):
        t.ell(P(0.072 * sx, -0.058, 1.33), (0.078, 0.045, 0.058))   # pecs
        t.ell(P(0.1 * sx, 0.036, 1.28), (0.07, 0.052, 0.11))        # lats (V-taper)
        t.ell(P(0.062 * sx, 0.05, 0.94), (0.064, 0.058, 0.07))      # glutes
        t.ball(P(0.172 * sx, 0.016, 1.415), 0.058)                  # deltoid
        t.ell(P(0.045 * sx, -0.08, 1.16), (0.042, 0.026, 0.085))    # abdominal wall
    t.ell(P(0, 0.035, 1.422), (0.12, 0.058, 0.05))          # trapezius
    t.taper(P(0, 0.016, 1.4), P(0, 0.008, 1.56), 0.054, 0.048, 4)  # neck
    fams.append(t)
    h = Family("head")
    h.ell(P(0, 0.006, 1.668), (0.079, 0.094, 0.104))
    h.ell(P(0, -0.03, 1.606), (0.064, 0.068, 0.052))        # jaw
    fams.append(h)
    for s, sx in (("L", 1), ("R", -1)):
        a = Family(f"arm_{s}")
        sh, el, wr = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"]
        kn, tp = J[f"knuckle.{s}"], J[f"tip.{s}"]
        a.taper(sh, el, 0.046 * S, 0.034 * S)
        a.ell(sh.lerp(el, 0.42), (0.1 * S, 0.043 * S, 0.046 * S), along=el - sh)       # biceps/triceps
        a.taper(el, wr, 0.036 * S, 0.026 * S)
        a.ell(el.lerp(wr, 0.28), (0.09 * S, 0.04 * S, 0.036 * S), along=wr - el)       # forearm
        palm = wr.lerp(kn, 0.55)
        a.ell(palm, (0.05 * S, 0.04 * S, 0.017 * S), along=kn - wr)
        a.taper(kn, tp, 0.019 * S, 0.014 * S, 3)
        thumb0 = wr.lerp(kn, 0.3) + V((0, -0.03, 0)) * S
        a.taper(thumb0, thumb0 + (kn - wr).normalized() * 0.065 * S + V((0, -0.02, 0)), 0.014 * S, 0.012 * S, 3)
        fams.append(a)
        g = Family(f"leg_{s}")
        hp, kn2, an, bl = J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"], J[f"ball.{s}"]
        g.taper(hp + V((0, 0, 0.02)) * S, kn2, 0.078 * S, 0.048 * S)
        g.ell(hp.lerp(kn2, 0.38) + V((0, -0.016, 0)) * S, (0.19 * S, 0.06 * S, 0.06 * S), along=kn2 - hp)  # quads
        g.ball(kn2, 0.047 * S)
        g.taper(kn2, an, 0.046 * S, 0.033 * S)
        g.ell(kn2.lerp(an, 0.3) + V((0, 0.018, 0)) * S, (0.12 * S, 0.045 * S, 0.045 * S), along=an - kn2)  # calf
        g.ell(an.lerp(bl, 0.45) + V((0, 0, 0.004)) * S, (0.11 * S, 0.044 * S, 0.036 * S), along=bl - an)  # boot
        g.ball(an + V((0, 0.026, -0.035)) * S, 0.038 * S)                                                    # heel
        fams.append(g)
    obs = []
    for f in fams:
        bpy.ops.object.select_all(action="DESELECT")
        f.ob.select_set(True)
        bpy.context.view_layer.objects.active = f.ob
        bpy.ops.object.convert(target="MESH")
        obs.append(bpy.context.active_object)
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = "suit"
    apply_mod(body, "REMESH", mode="VOXEL", voxel_size=0.009, adaptivity=0.0)
    apply_mod(body, "SMOOTH", factor=0.6, iterations=6)
    return body


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


def decimate(ob, target):
    n = tris(ob)
    if n > target:
        apply_mod(ob, "DECIMATE", ratio=target / n)


BODY = build_body()
log("undersuit:", tris(BODY), "tris (dense)")
# Plates are cut from an even quad remesh of the smooth body (decimated
# patches left sliver triangles that shaded as dark streaks; bevelling a
# decimated body rounded every edge). The suit itself is decimated last.
PLATE_SRC = BODY.copy()
PLATE_SRC.data = BODY.data.copy()
COL.objects.link(PLATE_SRC)
apply_mod(PLATE_SRC, "REMESH", mode="VOXEL", voxel_size=0.02, adaptivity=0.0)
apply_mod(PLATE_SRC, "SMOOTH", factor=0.5, iterations=2)
log("plate source:", tris(PLATE_SRC), "tris")

# ====================================================================== carapace plates


BONE_SEG = {name: (head, tail) for name, head, tail, _p, _r in BONES}
TORSO_BONES = {"hips", "spine", "chest", "neck", "head"}


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def cut_patch(src, planes, name, bone=None):
    """Copy of `src` keeping only the side of every plane its normal points to,
    and (with `bone`) only faces near that bone: plane slabs are unbounded and
    would otherwise also slice bits off other limbs or the head."""
    bm = bmesh.new()
    bm.from_mesh(src.data)
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=V(co), plane_no=V(no).normalized(), clear_inner=True)
    if bone in BONE_SEG:
        a, b = BONE_SEG[bone]
        r = (0.25 if bone in TORSO_BONES else 0.12) * S
        far = [f for f in bm.faces if seg_dist(f.calc_center_median(), a, b) > r]
        bmesh.ops.delete(bm, geom=far, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    return ob


def slab(axis_point, axis_normal, lo, hi):
    """Two planes keeping lo <= dot(p - axis_point, n) <= hi."""
    n = V(axis_normal).normalized()
    p = V(axis_point)
    return [(p + n * lo, n), (p + n * hi, -n)]


PLATES = []  # (object, bone, material)
PLATE_RATIO = 0.16


def plate(name, planes, bone, thick=0.009, lift=0.0025, mat="plate", bevel=0.0035):
    planes = [(V(c) * 1.0, V(n)) for c, n in planes]
    ob = cut_patch(PLATE_SRC, planes, name, bone)
    if len(ob.data.polygons) < 4:
        log("  (empty plate", name, ")")
        bpy.data.objects.remove(ob)
        return None
    apply_mod(ob, "DISPLACE", strength=lift, mid_level=0.0)
    apply_mod(ob, "SOLIDIFY", thickness=thick, offset=1.0, use_rim=True, use_even_offset=False, thickness_clamp=2.0)
    if bevel > 0:
        apply_mod(ob, "BEVEL", width=bevel, segments=1, limit_method="ANGLE", angle_limit=math.radians(70))
    ob.data.materials.clear()
    ob.data.materials.append(MAT[mat])
    PLATES.append((ob, bone, mat))
    return ob


X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
GAP = 0.006 * S


def zcut(lo, hi):
    return slab(V((0, 0, 0)), Z, lo * S, hi * S)


log("plates")
# Chest: two halves split at the sternum, front only.
for sx, s in ((1, "L"), (-1, "R")):
    plate(f"chest_{s}", zcut(1.255, 1.415) + [(V((0, -0.035 * S, 0)), -Y), (V((0.012 * S * sx, 0, 0)), X * sx),
                                               (V((0.19 * S * sx, 0, 0)), -X * sx)], "chest", thick=0.011)
# Abdomen: three bands front, gaps between.
for i, (lo, hi) in enumerate(((1.175, 1.245), (1.1, 1.168), (1.03, 1.093))):
    plate(f"abs_{i}", zcut(lo, hi) + [(V((0, -0.05 * S, 0)), -Y), (V((0.125 * S, 0, 0)), -X), (V((-0.125 * S, 0, 0)), X)],
          "spine" if i < 2 else "hips", thick=0.008)
# Back plate (two halves) and spine ridge.
for sx, s in ((1, "L"), (-1, "R")):
    plate(f"back_{s}", zcut(1.17, 1.43) + [(V((0, 0.04 * S, 0)), Y), (V((0.016 * S * sx, 0, 0)), X * sx),
                                             (V((0.17 * S * sx, 0, 0)), -X * sx)], "chest", thick=0.011)
plate("spine_ridge", zcut(1.0, 1.42) + [(V((0, 0.07 * S, 0)), Y), (V((0.009 * S, 0, 0)), -X), (V((-0.009 * S, 0, 0)), X)],
      "spine", thick=0.012, lift=0.008)
# Hips / belt plates at the sides.
for sx, s in ((1, "L"), (-1, "R")):
    plate(f"hip_{s}", zcut(0.94, 1.02) + [(V((0.11 * S * sx, 0, 0)), X * sx)], "hips", thick=0.008)
# Limbs.
for s, sx in (("L", 1.0), ("R", -1.0)):
    side = [(V((0.02 * S * sx, 0, 0)), X * sx)]  # this side only (limb slabs are unbounded sideways)
    sh, el, wr, kn = J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"], J[f"knuckle.{s}"]
    ua = (el - sh).normalized()
    fa = (wr - el).normalized()
    # Shoulder cap: the top of the deltoid.
    plate(f"shoulder_{s}", [(sh + V((0, 0, -0.035 * S)), Z * 0.6 + X * sx * 0.8), (V((0.13 * S * sx, 0, 0)), X * sx)] + side,
          f"upper_arm.{s}", thick=0.012)
    # Upper-arm guard: outer side, between deltoid and elbow.
    out = V((sx, 0.0, 0.25)).normalized()
    plate(f"upperarm_{s}", slab(sh, ua, 0.085 * S, 0.24 * S) + [(sh, out)] + side, f"upper_arm.{s}", thick=0.008)
    # Forearm guard: wraps the top/outer forearm.
    top = (fa.cross(Y * -1.0) * sx).normalized()
    plate(f"forearm_{s}", slab(el, fa, 0.05 * S, 0.215 * S) + [(el - top * 0.012 * S, top)] + side, f"forearm.{s}", thick=0.01)
    # Back of the hand.
    plate(f"hand_{s}", slab(wr, (kn - wr), 0.012 * S, 0.08 * S) + [(wr, V((sx * 0.3, 0.2, 0.0)) + top)] + side, f"hand.{s}", thick=0.006)
    hp, kne, an, bl = J[f"hip.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"], J[f"ball.{s}"]
    th = (kne - hp).normalized()
    sh_ = (an - kne).normalized()
    # Thigh: front plate and outer plate.
    plate(f"thigh_front_{s}", slab(hp, th, 0.07 * S, 0.33 * S) + [(hp + V((0, -0.018 * S, 0)), -Y)] + side,
          f"thigh.{s}", thick=0.01)
    plate(f"thigh_side_{s}", slab(hp, th, 0.06 * S, 0.3 * S) + [(hp + V((0.05 * S * sx, 0, 0)), X * sx),
                                                               (hp + V((0, -0.004 * S, 0)), Y)] + side, f"thigh.{s}", thick=0.009)
    # Knee cap.
    plate(f"knee_{s}", slab(kne, th, -0.045 * S, 0.04 * S) + [(kne + V((0, -0.02 * S, 0)), -Y)] + side, f"shin.{s}", thick=0.013)
    # Shin guard: front of the shin.
    plate(f"shin_{s}", slab(kne, sh_, 0.07 * S, 0.33 * S) + [(kne + V((0, -0.01 * S, 0)), -Y)] + side, f"shin.{s}", thick=0.01)
    # Boot: toe cap and heel cup.
    plate(f"toe_{s}", [(an + (bl - an) * 0.45, (bl - an).normalized()), (V((0, 0, 0.09 * S)), -Z)] + side, f"foot.{s}", thick=0.007)
    plate(f"heel_{s}", [(an + V((0, 0.012 * S, 0)), Y), (V((0, 0, 0.11 * S)), -Z)] + side, f"foot.{s}", thick=0.007)
# Helmet: everything above the neck seam, then the visor band on the face.
helmet_planes = [(V((0, 0, 1.545 * S)), Z)]
plate("helmet", helmet_planes, "head", thick=0.013, lift=0.004, bevel=0.0)
plate("visor", slab(V((0, 0, 1.66 * S)), Z, -0.022 * S, 0.02 * S) + [(V((0, -0.04 * S, 0)), -Y)],
      "head", thick=0.012, lift=0.017, mat="visor", bevel=0.003)
# Seam lights (seaglass).
plate("glow_visor", slab(V((0, 0, 1.662 * S)), Z, -0.0018 * S, 0.0018 * S) + [(V((0, -0.06 * S, 0)), -Y)],
      "head", thick=0.004, lift=0.03, mat="glow", bevel=0.0)
plate("glow_spine", zcut(1.08, 1.4) + [(V((0, 0.07 * S, 0)), Y), (V((0.0022 * S, 0, 0)), -X), (V((-0.0022 * S, 0, 0)), X)],
      "spine", thick=0.004, lift=0.021, mat="glow", bevel=0.0)
plate("glow_waist", zcut(1.022, 1.028), "hips", thick=0.003, lift=0.004, mat="glow", bevel=0.0)
plate("glow_collar", zcut(1.508, 1.514), "neck", thick=0.003, lift=0.004, mat="glow", bevel=0.0)
for s, sx in (("L", 1.0), ("R", -1.0)):
    el, wr = J[f"elbow.{s}"], J[f"wrist.{s}"]
    fa = (wr - el).normalized()
    plate(f"glow_cuff_{s}", slab(el, fa, 0.228 * S, 0.233 * S), f"forearm.{s}", thick=0.003, lift=0.004, mat="glow", bevel=0.0)
log("plates:", len(PLATES))
bpy.data.objects.remove(PLATE_SRC)

# ====================================================================== finish, weights, export
BODY.data.materials.clear()
BODY.data.materials.append(MAT["suit"])
decimate(BODY, 9000)
log("undersuit:", tris(BODY), "tris")


def smooth_by_angle(ob, deg):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(deg))


smooth_by_angle(BODY, 60)
for ob, _b, _m in PLATES:
    smooth_by_angle(ob, 35)

# Undersuit: bone-heat weights.
bpy.ops.object.select_all(action="DESELECT")
BODY.select_set(True)
ARM.select_set(True)
bpy.context.view_layer.objects.active = ARM
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
log("undersuit weighted:", len(BODY.vertex_groups), "groups")
# Plates: rigid on their bone.
for ob, bone, _m in PLATES:
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
    ob.parent = ARM
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = ARM

# Join plates by material into a few meshes (fewer draws).
groups = {}
for ob, _b, mat in PLATES:
    groups.setdefault(mat, []).append(ob)
JOINED = [BODY]
for mat, obs in groups.items():
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = "carapace" if mat == "plate" else mat
    JOINED.append(j)
total = sum(tris(o) for o in JOINED)
log("meshes:", [(o.name, tris(o)) for o in JOINED], "total", total)


def preview(prefix):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x = 640
    sc.render.resolution_y = 960
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.035, 0.045, 1)
    sc.world = world
    for name, loc, energy, size, col in (("key", (2.2, -2.8, 3.2), 900, 2.5, (1.0, 0.95, 0.9)),
                                         ("rim", (-2.5, 2.6, 2.6), 1100, 1.5, (0.6, 0.85, 1.0)),
                                         ("fill", (-2.8, -2.0, 1.2), 250, 3.0, (0.9, 0.85, 1.0))):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = col
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        COL.objects.link(lo)
        lo.rotation_euler = (V((0, 0, 1.0)) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    floor = bpy.data.meshes.new("floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4)
    bm.to_mesh(floor)
    fo = bpy.data.objects.new("floor", floor)
    COL.objects.link(fo)
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.055, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.35
    floor.materials.append(fm)
    cd = bpy.data.cameras.new("cam")
    cd.lens = 70
    cam = bpy.data.objects.new("cam", cd)
    COL.objects.link(cam)
    sc.camera = cam
    target = V((0, 0, 1.0 * S))
    paths = []
    for i, ang in enumerate((-25, 155, 70, -10)):
        r = 4.8 if i < 3 else 1.6
        tgt = target if i < 3 else V((0, 0, 1.6 * S))
        a = math.radians(ang)
        cam.location = tgt + V((math.sin(a) * r, -math.cos(a) * r, 0.25 if i < 3 else 0.05))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        path = f"{prefix}_{i}.png"
        sc.render.filepath = os.path.abspath(path)
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        log("rendered", path)
    return paths


if args.preview:
    os.makedirs(os.path.dirname(os.path.abspath(args.preview)) or ".", exist_ok=True)
    preview(args.preview)

if args.out:
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ARM.select_set(True)
    for o in JOINED:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(args.out), use_selection=True, export_format="GLTF_SEPARATE",
                              export_yup=True, export_apply=False, export_skins=True, export_animations=False,
                              export_materials="EXPORT", export_normals=True)
    log("exported", args.out)
