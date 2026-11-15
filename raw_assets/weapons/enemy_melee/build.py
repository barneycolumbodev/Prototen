"""Hatchet Man blades (third person): a hand hatchet and a Chinese cleaver (docs/design.md §8.8).

Held in the right hand on the same weapon socket as the enemy guns
(raw_assets/weapons/enemy_guns): the origin is the right hand's web, and the
handle runs through the fist along the pistol-grip line, so the triad rig's
grip (common.GRIP_R) closes on it. The head sits above the thumb with the
edge forward, the way the knuckles point.
Axes: +X = forward (where the edge faces), +Z = up, +Y = the blade's LEFT side, metres.
Handle line U = (0.39, 0, 0.92) from the pommel up through the fist; edge
direction E = (0.92, 0, -0.39). Real sizes: hatchet 0.40 m overall with a
0.10 m bit; cleaver 0.32 m overall, blade 0.20 x 0.10 m.

Plain PBR factors (no textures): forged steel with a ground bright edge,
oiled ash, a cloth-taped grip.

Run:
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
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="assets/weapons/enemy")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=48)
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
hs.set_detail(hs.LOW)

STEEL = hs.material("melee_steel", (0.06, 0.058, 0.055), 0.5, 0.9, wear=(0.42, 0.42, 0.43), wear_rough=0.3)
EDGE = hs.material("melee_edge", (0.62, 0.63, 0.65), 0.22, 1.0)
WOOD = hs.material("melee_wood", (0.22, 0.13, 0.065), 0.58, 0.0)
TAPE = hs.material("melee_tape", (0.09, 0.08, 0.07), 0.85, 0.0)

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


os.makedirs(args.out, exist_ok=True)
blades = {}
for name, fn in (("hatchet", hatchet), ("cleaver", cleaver)):
    fn()
    ob = hs.join_parts(name)
    blades[name] = ob
    print(f"{name}: {tri(ob)} tris")
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(args.out, f"{name}.gltf"), export_format="GLTF_SEPARATE",
                              use_selection=True, export_apply=True)

if args.preview:
    scene = bpy.context.scene
    for i, ob in enumerate(blades.values()):
        ob.location = (0.32 * i, 0, 0)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    world = bpy.data.worlds.new("w")
    world.color = (0.5, 0.52, 0.55)
    scene.world = world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (0.2, -1.05, 0.12)
    cam.rotation_euler = (math.radians(88), 0, 0)
    cam.data.lens = 50
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(30))
    scene.collection.objects.link(sun)
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("preview:", args.preview)
