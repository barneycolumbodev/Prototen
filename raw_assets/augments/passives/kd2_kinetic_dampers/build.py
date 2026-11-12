"""KD-2 Kinetic Dampers (docs/design.md §3.6): magnetorheological dampers at the knees and ankles.

Design: on the outer side of each knee, a machined hub over the joint (a seaglass ring light, six bolts) with a
titanium link plate running up the thigh to a pinned mount; from the hub a polished chrome piston rod drops into
a black anodised damper body along the outer shin, clamped by two bands, ending in a conformal lower mount. A
smaller rod-and-cylinder damper runs down the back of the ankle along the Achilles. Silent landings, long slides:
the hardware should look like suspension.

Pieces: hub, shin damper and ankle damper on shin.L/R; link plate on thigh.L/R.

Run:
  tools/blender.sh raw_assets/augments/passives/kd2_kinetic_dampers/build.py \\
      --out assets/augments/passives/kd2_kinetic_dampers/kd2_kinetic_dampers.gltf --preview docs/previews/kd2_kinetic_dampers
  Design check without the bake: --quick --preview /tmp/kd2
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--quick", action="store_true")
ap.add_argument("--tex", type=int, default=1024)
ap.add_argument("--samples", type=int, default=40)
args = ap.parse_args(argv)
C.TAG = "kd2"

body = C.Body()
ANOD = C.mat_metal("kd2_anodised", base=(0.025, 0.026, 0.03), rough=0.32, wear=(0.4, 0.41, 0.43), brushed=0.05)
CHROME = C.mat_chrome("kd2_chrome")
TI = C.mat_metal("kd2_titanium", base=(0.28, 0.28, 0.29), rough=0.28, wear=(0.6, 0.6, 0.61), brushed=0.1)
PAINT = C.mat_paint("kd2_stencil", (0.6, 0.6, 0.56))
GLOW = C.mat_glow("kd2_glow", strength=6.0)
MATS = [ANOD, CHROME, TI, PAINT, GLOW]


def setmat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


def bev(ob, w, seg=2, angle=35):
    b = ob.modifiers.new("bevel", "BEVEL")
    b.width = w
    b.segments = seg
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(angle)
    b.harden_normals = True
    ob.data.shade_smooth()
    ob.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
    return C.apply_all(ob)


def cyl(name, p0, p1, r, mat, det, verts=24, w=0.0008):
    hs.set_detail(hs.HIGH if det else hs.LOW)
    ob = setmat(hs.cyl_between(name, p0, p1, r, verts=verts), mat)
    return bev(ob, w) if det else ob


def slab(name, center, axes, size, mat, det, w=0.0012):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=C.basis4(*axes, center) @ Matrix.Diagonal((*size, 1)), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    setmat(ob, mat)
    return bev(ob, w) if det else ob


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    hip, knee, ankle = body.joint("thigh." + side), body.joint("shin." + side), body.joint("foot." + side)
    shin_ax = (ankle - knee).normalized()
    thigh_ax = (knee - hip).normalized()

    def outer(c, axis_dir=None, which=("suit",)):
        """The leg's outer surface at the height of point c: (point, normal)."""
        hit, n = body.cast(V((c.x + 0.4 * s, c.y, c.z)), V((-s, 0, 0)), which, 0.8)
        return hit, n

    def behind(c):
        hit, n = body.cast(V((c.x, c.y + 0.4, c.z)), V((0, -1, 0)), ("suit",), 0.8)
        return hit, n

    shin_hi, shin_lo, thigh_hi, thigh_lo = [], [], [], []
    hub_c, hub_n = outer(knee + shin_ax * 0.012)
    hub_n = V((s, 0, 0))
    hub = hub_c + hub_n * 0.012
    for det, lst in ((True, shin_hi), (False, shin_lo)):
        # Knee hub: a machined disc, a light ring, six bolts.
        lst.append(cyl("hub", hub - hub_n * 0.01, hub + hub_n * 0.008, 0.026, ANOD, det, 32, 0.0015))
        lst.append(cyl("hub_cap", hub + hub_n * 0.006, hub + hub_n * 0.012, 0.016, TI, det, 32, 0.0008))
        lst.append(cyl("hub_ring", hub + hub_n * 0.0075, hub + hub_n * 0.0088, 0.0205, GLOW, det, 32, 0.0))
        if det:
            for k in range(6):
                a = k * math.pi / 3
                off = V((0, math.cos(a), math.sin(a))) * 0.0215
                b = C.bolt("hb", hub + hub_n * 0.008 + off, hub_n, r=0.0018, h=0.0014)
                lst.append(setmat(C.apply_all(b), TI))
        # Shin damper: rod from the hub into the damper body, two clamp bands, a lower mount.
        top = hub + shin_ax * 0.02
        # Follow the shin's outer surface (keep the damper off the suit).
        sh_mid, _ = outer(knee + shin_ax * 0.16)
        lift = (sh_mid + V((s * 0.016, 0, 0))) - (knee + shin_ax * 0.16)
        body_top = knee + shin_ax * 0.085 + lift
        body_bot = knee + shin_ax * 0.235 + lift
        lst.append(cyl("rod", top, body_top + shin_ax * 0.01, 0.0055, CHROME, det, 20, 0.0004))
        lst.append(cyl("damper", body_top, body_bot, 0.0145, ANOD, det, 28, 0.0012))
        lst.append(cyl("seal", body_top - shin_ax * 0.004, body_top + shin_ax * 0.003, 0.0105, TI, det, 28, 0.0006))
        for f in (0.3, 0.75):
            p = body_top.lerp(body_bot, f)
            lst.append(cyl("band", p - shin_ax * 0.004, p + shin_ax * 0.004, 0.016, TI, det, 28, 0.0006))
        mount = body_bot + shin_ax * 0.014
        lst.append(slab("mount", mount - V((s * 0.006, 0, 0)), (shin_ax, V((0, 1, 0)), V((s, 0, 0))), (0.026, 0.017, 0.012), TI, det))
        # Ankle damper down the back of the leg.
        a_top_c, _ = behind(knee + shin_ax * 0.3)
        a_bot_c, _ = behind(knee + shin_ax * 0.4)
        if a_top_c is not None and a_bot_c is not None:
            at = a_top_c + V((0, 0.012, 0))
            ab = a_bot_c + V((0, 0.012, 0))
            lst.append(cyl("a_body", at, at.lerp(ab, 0.55), 0.0085, ANOD, det, 20, 0.001))
            lst.append(cyl("a_rod", at.lerp(ab, 0.5), ab, 0.0042, CHROME, det, 16, 0.0003))
            lst.append(cyl("a_cap", ab - (ab - at).normalized() * 0.003, ab + (ab - at).normalized() * 0.004, 0.0075, TI, det, 16, 0.0005))
        # Thigh link: a titanium plate from the hub up to a pinned mount.
        link_top_c, _ = outer(knee - thigh_ax * 0.13)
        link_top = (link_top_c if link_top_c is not None else knee - thigh_ax * 0.13) + V((s * 0.009, 0, 0))
        mid = hub.lerp(link_top, 0.5)
        ax = (link_top - hub).normalized()
        tl = thigh_hi if det else thigh_lo
        tl.append(slab("link", mid, (ax, V((0, 1, 0)), V((s, 0, 0))), ((link_top - hub).length + 0.01, 0.018, 0.005), TI, det, 0.0016))
        tl.append(cyl("pin", link_top - V((s * 0.004, 0, 0)), link_top + V((s * 0.008, 0, 0)), 0.0075, ANOD, det, 20, 0.0008))
    C.add_piece("shin_" + side, "shin." + side, C.join(shin_hi, "shin_high"), C.join(shin_lo, "shin_low"))
    C.add_piece("thigh_" + side, "thigh." + side, C.join(thigh_hi, "thigh_high"), C.join(thigh_lo, "thigh_low"))

C.log("pieces:", len(C.PIECES), "low tris", sum(C.tris(p.low) for p in C.PIECES))

if not args.quick and args.out:
    C.bake_and_export("kd2_kinetic_dampers", os.path.join(C.ROOT, args.out), MATS, tex=args.tex, cage=0.001, ray=0.004,
                      ao=0.012, emission_strength=3.0)
else:
    for p in C.PIECES:
        p.low.hide_render = True
if args.preview:
    C.stage(body)
    base = os.path.join(C.ROOT, args.preview) if not args.preview.startswith("/") else args.preview
    os.makedirs(os.path.dirname(base), exist_ok=True)
    kn = body.joint("shin.L")
    views = (("front", (0.9, -4.6, 1.0), (0, 0, 0.8), 85), ("knee", kn + V((0.55, -0.42, 0.05)), kn + V((0.02, 0, -0.06)), 60),
             ("back", kn + V((0.35, 0.55, -0.1)), kn + V((0.0, 0.02, -0.2)), 60))
    paths = []
    for name, cam, tgt, lens in views:
        pth = f"{base}_{name}.png"
        C.render(pth, cam, tgt, lens=lens, res=(720, 960), samples=args.samples)
        paths.append(pth)
    C.sheet(paths, base + ".png")
