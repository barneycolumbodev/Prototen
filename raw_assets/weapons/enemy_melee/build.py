"""Enemy blades and throwables (third person), rebuilt 2026-11-16 with baked textures.

Owner, 2026-11-16: "Don't hesitate to make more or more detailed 3d models for enemy weapons."
Each model is built twice from the same code (HIGH with bevels and small parts, LOW) and HIGH is
baked onto LOW (base colour with cavity grime, ORM, normal; raw_assets/_lib/bakeutil.py).

  hatchet   hand hatchet: ash haft with a swelled pommel, forged head with a ground edge (Hatchet Man).
  cleaver   Chinese cleaver: taped grip, bolster, rivet (Hatchet Man).
  dao       willow-leaf dao (liuyedao): a 0.68 m curved blade with a fuller, a brass guard,
            a cord-wrapped grip in red, a ring pommel (the Dao swordsman, docs/design.md §8.8b).
  molotov   a baijiu bottle with a soaked rag in the mouth, held by the neck (the Firebomber).
  emp       an EMP grenade: steel body, copper coil bands, a pin and spoon, a status lamp (the
            anti-augment specialist). Origin at its centre (thrown, never held on the socket).

Held in the right hand on the same weapon socket as the enemy guns (raw_assets/weapons/enemy_guns):
the origin is the right hand's web, and the handle runs through the fist along the pistol-grip line,
so the triad rig's grip (common.GRIP_R) closes on it. The head sits above the thumb with the edge
forward, the way the knuckles point.
Axes: +X = forward (where the edge faces), +Z = up, +Y = the blade's LEFT side, metres.
Handle line U = (0.39, 0, 0.92) from the pommel up through the fist; edge direction E = (0.92, 0, -0.39).
Real sizes: hatchet 0.40 m overall with a 0.10 m bit; cleaver 0.32 m overall, blade 0.20 x 0.10 m;
dao 0.92 m overall; molotov 0.25 m (a 500 ml bottle); EMP grenade 0.13 x 0.055 m.

Run (about 3 minutes with bakes):
  tools/blender.sh raw_assets/weapons/enemy_melee/build.py --out assets/weapons/enemy \
      --preview docs/previews/enemy_melee.png
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="assets/weapons/enemy")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--tex", type=int, default=512)
ap.add_argument("--only", default="")
ap.add_argument("--fast", action="store_true", help="HIGH only, no bake/export")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)

STEEL = hs.material("melee_steel", (0.06, 0.058, 0.055), 0.5, 0.9, wear=(0.42, 0.42, 0.43), wear_rough=0.3,
                    bump_scale=700.0, bump_strength=0.15)
EDGE = hs.material("melee_edge", (0.62, 0.63, 0.65), 0.22, 1.0, brushed=0.08)
WOOD = hs.material("melee_wood", (0.22, 0.13, 0.065), 0.58, 0.0, wear=(0.36, 0.24, 0.14), bump_scale=400.0,
                   bump_strength=0.3)
TAPE = hs.material("melee_tape", (0.09, 0.08, 0.07), 0.85, 0.0, bump_scale=1600.0, bump_strength=0.4)
BRASS = hs.material("melee_brass", (0.62, 0.42, 0.16), 0.32, 1.0, wear=(0.9, 0.72, 0.4), wear_rough=0.18)
CORD = hs.material("melee_cord", (0.38, 0.03, 0.025), 0.8, 0.0, bump_scale=2500.0, bump_strength=0.6)
GLASS = hs.material("melee_glass", (0.07, 0.17, 0.07), 0.06, 0.0)
LABEL = hs.material("melee_label", (0.62, 0.08, 0.05), 0.6, 0.0)
RAG = hs.material("melee_rag", (0.42, 0.36, 0.26), 0.9, 0.0, bump_scale=900.0, bump_strength=0.6)
COPPER = hs.material("melee_copper", (0.8, 0.38, 0.18), 0.3, 1.0)
LAMP = hs.material("melee_lamp", (0.1, 0.5, 0.9), 0.3, 0.0, emission=((0.3, 0.7, 1.0), 4.0))
OLIVE = hs.material("melee_olive", (0.08, 0.09, 0.06), 0.55, 0.3, wear=(0.3, 0.3, 0.28))
MATERIALS = [STEEL, EDGE, WOOD, TAPE, BRASS, CORD, GLASS, LABEL, RAG, COPPER, LAMP, OLIVE]

# The handle's line in the hand: pistol-grip axis (raw_assets/weapons/enemy_guns, grip
# from (0.005, 0) down to (-0.04, -0.105)), its middle where the fist closes.
TILT = math.atan2(0.045, 0.105)          # about 23 degrees forward of vertical
GRIP_MID = Vector((-0.018, 0.0, -0.052))  # middle of the fist on the handle line
# Local frame: handle along +Z, edge toward +X, Z = 0 at the middle of the fist.
TO_GUN = Matrix.Translation(GRIP_MID) @ Matrix.Rotation(TILT, 4, "Y")


def tri(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def place(ob):
    """Into the gun frame: the object's own placement first (primitives keep theirs on the object)."""
    ob.data.transform(ob.matrix_basis)
    ob.matrix_basis = Matrix.Identity(4)
    ob.data.transform(TO_GUN)
    return ob


def tapered_plate(name, outline, thick):
    """A flat piece in the local XZ plane: outline (x, z) points, each with its
    own full thickness across Y (thin at the edge, thick at the spine)."""
    bm = bmesh.new()
    front = [bm.verts.new((x, t / 2, z)) for (x, z), t in zip(outline, thick)]
    back = [bm.verts.new((x, -t / 2, z)) for (x, z), t in zip(outline, thick)]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([front[i], back[i], back[j], front[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def handle(name, z0, z1, r0, r1, mat, verts=10, flare=None):
    """Round handle along local Z from z0 to z1 (radius r0 -> r1); `flare`: (z, r) pommel swell."""
    prof = [(z0, r0 * 0.6), (z0 + 0.004, r0)]
    if flare:
        prof += [flare]
    prof += [(z1 - 0.004, r1), (z1, r1 * 0.8)]
    bm = bmesh.new()
    rings = []
    for z, r in prof:
        ring = [bm.verts.new((r * math.cos(a) * 1.15, r * math.sin(a), z))
                for a in (2 * math.pi * k / verts for k in range(verts))]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(verts):
            bm.faces.new([a[k], a[(k + 1) % verts], b[(k + 1) % verts], b[k]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def hatchet():
    # Ash handle, 0.40 m, swelling at the pommel; the head on top.
    hs.finish(place(handle("haft", -0.11, 0.28, 0.0145, 0.0125, WOOD, flare=(-0.085, 0.017))), WOOD, bevel=0.0)
    # Head: the eye round the haft, the poll behind, the cheek thinning to a flared bit.
    zc = 0.25
    head = [(-0.035, zc - 0.022), (0.02, zc - 0.02), (0.075, zc - 0.045), (0.105, zc - 0.062),
            (0.112, zc - 0.05), (0.112, zc + 0.03), (0.104, zc + 0.04), (0.07, zc + 0.024),
            (0.02, zc + 0.022), (-0.035, zc + 0.022), (-0.042, zc)]
    th = [0.03, 0.03, 0.012, 0.004, 0.003, 0.003, 0.004, 0.012, 0.03, 0.03, 0.03]
    hs.finish(place(tapered_plate("head", head, th)), STEEL, bevel=0.0015, segments=1)
    # Ground edge: a bright band along the bit.
    edge = [(0.1, zc - 0.058), (0.113, zc - 0.05), (0.113, zc + 0.03), (0.105, zc + 0.04), (0.098, zc + 0.032), (0.099, zc - 0.048)]
    hs.finish(place(tapered_plate("edge", edge, [0.0052, 0.0042, 0.0042, 0.0052, 0.0072, 0.0072])), EDGE, bevel=0.0)
    # Wedge at the top of the eye.
    hs.finish(place(hs.box("wedge", (0.022, 0.033, 0.006), (0.0, 0.0, zc + 0.025))), STEEL, bevel=0.0)


def cleaver():
    # Short round grip (cloth tape over wood), a steel bolster, the blade forward of the handle line.
    hs.finish(place(handle("grip", -0.07, 0.07, 0.0145, 0.0135, TAPE, verts=10, flare=(-0.05, 0.0155))), TAPE, bevel=0.0)
    hs.finish(place(handle("bolster", 0.068, 0.09, 0.012, 0.011, STEEL, verts=8)), STEEL, bevel=0.0)
    z0, z1, x0, x1 = 0.082, 0.285, -0.012, 0.098
    blade = [(x0, z0), (x1 - 0.004, z0 - 0.006), (x1, z0 + 0.01), (x1 + 0.003, z1 - 0.02), (x1 - 0.008, z1),
             (x0 + 0.006, z1 + 0.004), (x0, z1 - 0.01)]
    th = [0.006, 0.0018, 0.0016, 0.0016, 0.0018, 0.005, 0.006]
    hs.finish(place(tapered_plate("blade", blade, th)), STEEL, bevel=0.0008, segments=1)
    edge = [(x1 - 0.012, z0 - 0.004), (x1 - 0.004, z0 - 0.006), (x1, z0 + 0.01), (x1 + 0.003, z1 - 0.02),
            (x1 - 0.008, z1), (x1 - 0.016, z1 - 0.002), (x1 - 0.011, z1 - 0.02), (x1 - 0.014, z0 + 0.01)]
    hs.finish(place(tapered_plate("edge", edge, [0.0026, 0.0024, 0.0024, 0.0024, 0.0024, 0.0028, 0.0028, 0.0028])), EDGE, bevel=0.0)
    # A rivet near the spine-tip corner.
    hs.finish(place(hs.cyl_y("rivet", 0.008, 0.0068, (x0 + 0.018, 0.0, z1 - 0.022), verts=10)), STEEL, bevel=0.0)



def dao():
    """Willow-leaf dao: the blade curves back toward the tip with the edge on the convex side."""
    # Grip: cord-wrapped in red over wood, 0.2 m, with a steel ferrule and a ring pommel.
    hs.finish(place(handle("grip", -0.1, 0.06, 0.015, 0.0155, CORD, verts=12, flare=(-0.06, 0.0165))), CORD, bevel=0.0)
    if hs.D is hs.HIGH:
        for i in range(10):
            z = -0.09 + i * 0.016
            hs.finish(place(hs.box("wrap", (0.036, 0.034, 0.004), (0.0, 0.0, z), rot=(0.0, 0.35, 0.0))), CORD,
                      bevel=0.001)
    hs.finish(place(handle("ferrule", 0.055, 0.075, 0.0165, 0.016, BRASS, verts=12)), BRASS, bevel=0.0)
    hs.finish(place(handle("pommel", -0.122, -0.098, 0.017, 0.017, BRASS, verts=12)), BRASS, bevel=0.0)
    ring = hs.cyl_y("ring", 0.016, 0.006, (0.0, 0.0, -0.135), verts=16)
    hs.cut(ring, hs.cyl_y("ring_in", 0.0105, 0.05, (0.0, 0.0, -0.135), verts=16))
    hs.finish(place(ring), BRASS, bevel=0.0008)
    # Guard: an oval brass disc.
    g = hs.cyl_z("guard", 0.034, 0.008, (0.0, 0.0, 0.08), verts=24)
    g.scale = (1.0, 0.72, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    hs.finish(place(g), BRASS, bevel=0.0015)
    # Blade: spine and edge as curves from the guard to the tip, thick at the spine.
    n = 16
    L0, L1 = 0.086, 0.72
    spine, edge = [], []
    for i in range(n + 1):
        t = i / n
        z = L0 + (L1 - L0) * t
        back = -0.012 - 0.048 * t ** 2.4          # the curve sweeps back toward the tip
        width = 0.034 + 0.008 * math.sin(math.pi * min(t * 1.1, 1.0))
        if t > 0.86:
            width *= max(0.0, (1.0 - t) / 0.14) ** 0.7
        spine.append((back, z))
        edge.append((back + width, z))
    outline = edge + list(reversed(spine))
    th = [0.0022] * len(edge) + [0.0062] * len(spine)
    hs.finish(place(tapered_plate("blade", outline, th)), STEEL, bevel=0.0006, segments=1)
    bevel_band = [(x - 0.008, z) for x, z in edge]
    hs.finish(place(tapered_plate("edge", edge + list(reversed(bevel_band)),
                                  [0.0024] * len(edge) + [0.004] * len(edge))), EDGE, bevel=0.0)
    if hs.D is hs.HIGH:
        # The fuller: a groove along the blade near the spine (a strip of darker steel standing in).
        fuller = [(x + 0.006, z) for x, z in spine[1:-4]]
        fuller2 = [(x + 0.012, z) for x, z in spine[1:-4]]
        hs.finish(place(tapered_plate("fuller", fuller + list(reversed(fuller2)), [0.0066] * (2 * len(fuller)))),
                  OLIVE, bevel=0.0)


def molotov():
    """A 500 ml baijiu bottle held by the neck: the body above the fist, the rag hanging from the mouth."""
    prof = [(-0.085, 0.0), (-0.084, 0.0105), (-0.072, 0.011), (-0.068, 0.0125), (-0.04, 0.0135), (0.02, 0.016),
            (0.05, 0.03), (0.07, 0.036), (0.17, 0.036), (0.178, 0.034), (0.18, 0.0)]
    n = 24 if hs.D is hs.HIGH else 48  # nverts() halves LOW: the same 24 sides in both (see the bake)
    b = hs.lathe_x("bottle", prof, verts=n)
    b.data.transform(Matrix.Rotation(-math.pi / 2, 4, "Y"))
    hs.finish(place(b), GLASS, bevel=0.0)
    lab = hs.lathe_x("label", [(0.09, 0.0367), (0.15, 0.0367)], verts=n)
    lab.data.transform(Matrix.Rotation(-math.pi / 2, 4, "Y"))
    hs.finish(place(lab), LABEL, bevel=0.0)
    # The rag: stuffed in the mouth (under the fist), its tail hanging down.
    hs.finish(place(hs.cyl_z("rag_plug", 0.011, 0.03, (0.0, 0.0, -0.09), verts=10)), RAG, bevel=0.0)
    tail = hs.tube_path("rag_tail", [(0.0, 0.0, -0.1), (0.012, 0.004, -0.13), (0.01, -0.006, -0.16),
                                     (0.02, 0.0, -0.19)], 0.009, width_scale=0.45)
    hs.finish(place(tail), RAG, bevel=0.0)


def emp():
    """EMP grenade, centred on its origin, axis along Z."""
    hs.finish(hs.cyl_z("body", 0.026, 0.1, (0.0, 0.0, 0.0), verts=24), OLIVE, bevel=0.002)
    for z in (-0.03, -0.01, 0.01, 0.03):
        hs.finish(hs.cyl_z("coil", 0.0285, 0.012, (0.0, 0.0, z), verts=24), COPPER, bevel=0.0008)
    hs.finish(hs.cyl_z("cap", 0.02, 0.016, (0.0, 0.0, 0.058), verts=20), STEEL, bevel=0.0015)
    hs.finish(hs.cyl_z("base", 0.024, 0.01, (0.0, 0.0, -0.055), verts=20), STEEL, bevel=0.0015)
    hs.finish(hs.box("spoon", (0.012, 0.006, 0.075), (0.031, 0.0, 0.02), rot=(0.0, -0.08, 0.0)), STEEL, bevel=0.001)
    ring = hs.cyl_y("pin_ring", 0.012, 0.003, (0.03, 0.0, 0.074), verts=16)
    hs.cut(ring, hs.cyl_y("pin_in", 0.009, 0.02, (0.03, 0.0, 0.074), verts=16))
    hs.finish(ring, STEEL, bevel=0.0)
    hs.finish(hs.cyl_z("lamp", 0.006, 0.006, (0.0, 0.0, 0.068), verts=12), LAMP, bevel=0.0)


BLADES = {"hatchet": hatchet, "cleaver": cleaver, "dao": dao, "molotov": molotov, "emp": emp}


def build(name, fn, detail):
    hs.set_detail(detail)
    fn()
    return hs.join_parts(f"{name}_{detail['name']}")


os.makedirs(args.out, exist_ok=True)
blades = {}
for name, fn in BLADES.items():
    if args.only and name not in args.only.split(","):
        continue
    hi = build(name, fn, hs.HIGH)
    if args.fast:
        blades[name] = hi
        print(f"{name}: HIGH {tri(hi)} tris")
        continue
    lo = build(name, fn, hs.LOW)
    lo.name = name
    print(f"{name}: HIGH {tri(hi)} / LOW {tri(lo)} tris", flush=True)
    bakeutil.unwrap(lo, angle_deg=78.0, margin=0.006)
    tex = bakeutil.bake_textures(hi, lo, MATERIALS, args.tex, os.path.join(args.out, "textures"), f"em_{name}",
                                 cage=0.0006, ray=0.0015, ao_distance=0.02, grime=0.5)
    bakeutil.apply_baked_material(lo, tex, f"em_{name}", emission_strength=1.0)
    bakeutil.export_gltf(lo, os.path.join(args.out, f"{name}.gltf"))
    bpy.data.objects.remove(hi)
    blades[name] = lo

if args.preview:
    scene = bpy.context.scene
    for i, ob in enumerate(blades.values()):
        ob.location = (0.3 * i, 0, 0)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    world = bpy.data.worlds.new("w")
    world.color = (0.32, 0.33, 0.35)
    scene.world = world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (0.3 * (len(blades) - 1) / 2, -2.0, 0.3)
    cam.rotation_euler = (math.radians(88), 0, 0)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 0.3 * len(blades) + 0.15
    scene.camera = cam
    for rot, e in (((50, -20, 30), 3.5), ((70, 30, -140), 1.5)):
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = e
        sun.rotation_euler = tuple(math.radians(a) for a in rot)
        scene.collection.objects.link(sun)
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("preview:", args.preview)
