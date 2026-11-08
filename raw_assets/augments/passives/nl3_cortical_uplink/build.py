"""NL-3 Cortical Uplink (docs/design.md §3.6): the transceiver that gives the operative connectivity.

Design: a faceted transceiver housing on the nape, tucked under the helmet's rear edge, with two swept antenna
blades (a phased array) rising from its top corners along the back of the helmet and splaying outward, like a
pair of dorsal fins: it changes the operative's silhouette from behind and the side. Each blade has a seaglass
data light along its leading edge. A sheathed fibre trunk runs from the housing down the cervical spine to a
junction block between the shoulder blades, held by three clamp rings. Satin black polymer over a titanium
frame; three status LEDs and an NL-3 stencil on the housing.

Pieces: housing on neck, blades on head, trunk and junction on chest.

Run:
  tools/blender.sh raw_assets/augments/passives/nl3_cortical_uplink/build.py \\
      --out assets/augments/passives/nl3_cortical_uplink/nl3_cortical_uplink.gltf --preview docs/previews/nl3_cortical_uplink
  Design check without the bake: --quick --preview /tmp/nl3
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
C.TAG = "nl3"

body = C.Body()
POLY = hs.material("nl3_polymer", (0.016, 0.016, 0.018), 0.3, 0.0, wear=(0.2, 0.2, 0.21), wear_rough=0.5, bump_scale=1800.0,
                   bump_strength=0.08)
TI = C.mat_metal("nl3_titanium", base=(0.3, 0.3, 0.31), rough=0.3, wear=(0.62, 0.62, 0.63), brushed=0.08)
SHEATH = C.mat_rubber("nl3_sheath")
PAINT = C.mat_paint("nl3_stencil", (0.6, 0.6, 0.56))
GLOW = C.mat_glow("nl3_glow", strength=7.0)
MATS = [POLY, TI, SHEATH, PAINT, GLOW]
BACK = (V((0, 0.4, 0)), V((1, 0, 0)), V((0, 0, 1)))
D_BACK = V((0, -1, 0))


def setmat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


def solid_from_outline(name, pts, normal, thick, mat):
    """Closed slab: outline `pts` (3D, roughly planar) extruded by `thick` along `normal` (centred)."""
    bm = bmesh.new()
    vs = [bm.verts.new(V(p) - normal * thick * 0.5) for p in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=normal * thick)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return setmat(ob, mat)


def bevelled(ob, w, seg=2, angle=30):
    b = ob.modifiers.new("bevel", "BEVEL")
    b.width = w
    b.segments = seg
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(angle)
    b.harden_normals = True
    ob.data.shade_smooth()
    ob.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
    return C.apply_all(ob)


def box(name, center, axes, size, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=C.basis4(*axes, center) @ Matrix.Diagonal((*size, 1)), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return setmat(ob, mat)


# ---------------------------------------------------------------- housing on the nape
HOUSING = [(-0.034, 1.53), (-0.04, 1.565), (-0.036, 1.61), (-0.02, 1.622), (0.02, 1.622), (0.036, 1.61), (0.04, 1.565),
           (0.034, 1.53), (0.016, 1.518), (-0.016, 1.518)]
hi_h, lo_h = C.plate("housing", body, HOUSING, BACK, D_BACK, 0.002, 0.016, which=("suit",), facet_deg=5.0, smooth_r=0.015,
                     bevel=0.0022, crown=0.004)
setmat(hi_h, POLY)
setmat(lo_h, POLY)
extra_hi, extra_lo = [], []
# Titanium frame rails down both sides, LEDs and the stencil.
for s in (-1, 1):
    for at, n in C.surface_points(hi_h, D_BACK, [(0.031 * s, 1.568)], BACK):
        for lst, det in ((extra_hi, True), (extra_lo, False)):
            r = box("rail", at + n * 0.002, (V((0, 0, 1)), n.cross(V((0, 0, 1))).normalized(), n), (0.07, 0.006, 0.006), TI)
            lst.append(bevelled(r, 0.0012) if det else r)
        for z in (1.545, 1.59):
            for at2, n2 in C.surface_points(hi_h, D_BACK, [(0.031 * s, z)], BACK):
                b = C.bolt("bolt", at2 + n2 * 0.005, n2, r=0.0022, h=0.0016)
                extra_hi.append(setmat(C.apply_all(b), TI))
for k, x in enumerate((-0.012, 0.0, 0.012)):
    for at, n in C.surface_points(hi_h, D_BACK, [(x, 1.6)], BACK):
        for lst in (extra_hi, extra_lo):
            lst.append(box("led%d" % k, at + n * 0.0005, (V((1, 0, 0)), V((0, 0, 1)), n), (0.006, 0.0025, 0.0014), GLOW))
for at, n in C.surface_points(hi_h, D_BACK, [(0.0, 1.565)], BACK):
    extra_hi.append(C.stencil("st_nl3", "NL-3", at, n, (0, 0, 1), 0.011, PAINT, target=hi_h))
for at, n in C.surface_points(hi_h, D_BACK, [(0.0, 1.546)], BACK):
    extra_hi.append(C.stencil("st_nl3b", "UPLINK  •  6 GHz", at, n, (0, 0, 1), 0.0045, PAINT, target=hi_h))
C.add_piece("housing", "neck", C.join([hi_h] + extra_hi, "housing_high"), C.join([lo_h] + extra_lo, "housing_low"))

# ---------------------------------------------------------------- antenna blades on the back of the helmet
for s in (-1, 1):
    out = V((s * math.sin(math.radians(24)), math.cos(math.radians(24)), 0)).normalized()
    # Points along the helmet's back: t up the head (m), the root of the blade spreading outward.
    def surf(t):
        z = 1.612 + t
        x = s * (0.026 + t * 0.12)
        hit, _n = body.cast(V((x, 0.5, z)), V((0, -1, 0)), ("helmet", "suit"), 1.0)
        if hit is None:
            hit = V((x, 0.12, z))
        return hit + out * 0.003
    # A low swept fin: rises off the housing, runs up the helmet's back and tapers into it.
    outline = [(0.0, 0.0), (0.008, 0.013), (0.035, 0.02), (0.08, 0.019), (0.125, 0.012), (0.14, 0.006),
               (0.12, 0.003), (0.09, 0.0), (0.06, -0.001)]
    pts = [surf(t) + out * h for t, h in outline]
    tangent = (surf(0.09) - surf(0.0)).normalized()
    normal = tangent.cross(out).normalized()
    hi_b = bevelled(solid_from_outline("blade_hi", pts, normal, 0.0032, POLY), 0.001, 2, 25)
    lo_b = solid_from_outline("blade_lo", pts, normal, 0.0032, POLY)
    # Leading-edge data light and a titanium root collar.
    lead = [surf(t) + out * (h + 0.0008) for t, h in outline[1:6]]
    lights_hi, lights_lo = [], []
    for a, b in zip(lead[:-1], lead[1:]):
        mid = (a + b) / 2
        ax = (b - a).normalized()
        for lst in (lights_hi, lights_lo):
            lst.append(box("edge", mid, (ax, normal, ax.cross(normal).normalized()), ((b - a).length * 0.95, 0.0036, 0.0016), GLOW))
    root = surf(0.0)
    for lst, det in ((lights_hi, True), (lights_lo, False)):
        c = box("collar", root + out * 0.004 + tangent * 0.008, (tangent, normal, out), (0.03, 0.009, 0.01), TI)
        lst.append(bevelled(c, 0.0015) if det else c)
    C.add_piece("blade_%d" % s, "head", C.join([hi_b] + lights_hi, "blade_high"), C.join([lo_b] + lights_lo, "blade_low"))

# ---------------------------------------------------------------- fibre trunk and junction block on the upper back
path = []
for z in (1.522, 1.5, 1.475, 1.45, 1.425, 1.405):
    hit, _n = body.cast(V((0, 0.5, z)), V((0, -1, 0)), ("suit",), 1.0)
    path.append(hit + V((0, 0.012, 0)))
trunks = {}
for det, D in (("hi", hs.HIGH), ("lo", hs.LOW)):
    hs.set_detail(D)
    t = hs.tube_path("trunk_" + det, path, 0.0065, resolution=8)
    setmat(t, SHEATH)
    objs = [t]
    for k, f in enumerate((0.2, 0.5, 0.8)):
        i = int(f * (len(path) - 1))
        p0, p1 = path[i], path[min(i + 1, len(path) - 1)]
        c = p0.lerp(p1, (f * (len(path) - 1)) % 1.0)
        ax = (p1 - p0).normalized()
        ring = hs.cyl_between("ring%d" % k, c - ax * 0.004, c + ax * 0.004, 0.0085, verts=16)
        setmat(ring, TI)
        objs.append(bevelled(ring, 0.0008, 1, 40) if det == "hi" else ring)
    trunks[det] = objs
JUNCTION = [(-0.03, 1.375), (-0.034, 1.395), (-0.026, 1.412), (0.026, 1.412), (0.034, 1.395), (0.03, 1.375), (0.0, 1.364)]
hi_j, lo_j = C.plate("junction", body, JUNCTION, BACK, D_BACK, 0.003, 0.012, facet_deg=6.0, smooth_r=0.015, bevel=0.0018)
setmat(hi_j, POLY)
setmat(lo_j, POLY)
jl_hi, jl_lo = [], []
for x in (-0.016, 0.016):
    for at, n in C.surface_points(hi_j, D_BACK, [(x, 1.39)], BACK):
        for lst in (jl_hi, jl_lo):
            lst.append(box("jled", at + n * 0.0005, (V((1, 0, 0)), V((0, 0, 1)), n), (0.009, 0.002, 0.0014), GLOW))
C.add_piece("trunk", "chest", C.join([hi_j] + trunks["hi"] + jl_hi, "trunk_high"), C.join([lo_j] + trunks["lo"] + jl_lo, "trunk_low"))

C.log("pieces:", len(C.PIECES), "low tris", sum(C.tris(p.low) for p in C.PIECES))

if not args.quick and args.out:
    C.bake_and_export("nl3_cortical_uplink", os.path.join(C.ROOT, args.out), MATS, tex=args.tex, cage=0.0012, ray=0.005,
                      ao=0.015, emission_strength=3.0)
else:
    for p in C.PIECES:
        p.low.hide_render = True
if args.preview:
    C.stage(body)
    base = os.path.join(C.ROOT, args.preview) if not args.preview.startswith("/") else args.preview
    os.makedirs(os.path.dirname(base), exist_ok=True)
    nape = V((0, 0.1, 1.6))
    views = (("back", (-1.3, 4.0, 1.75), (0, 0, 1.45), 85), ("nape", nape + V((-0.38, 0.5, 0.14)), nape + V((0, 0, 0.03)), 70),
             ("side", nape + V((0.75, 0.1, 0.05)), nape + V((0, -0.03, 0.03)), 70))
    paths = []
    for name, cam, tgt, lens in views:
        pth = f"{base}_{name}.png"
        C.render(pth, cam, tgt, lens=lens, res=(720, 960), samples=args.samples)
        paths.append(pth)
    C.sheet(paths, base + ".png")
