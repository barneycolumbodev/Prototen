"""Enemy weapons (third person): Type 56 assault rifle, pump shotgun, compact SMG.

Low-poly hard-surface models seen at a distance in enemy hands. All three
share the hand positions so one set of character animations fits them:
  origin           = top of the pistol grip (right hand's web)
  SUPPORT (x 0.29) = where the left palm cups the handguard / forend
Axes: +X = muzzle, +Z = up, +Y = the gun's LEFT side, metres.
Materials are plain PBR factors (no textures): blued steel, worn wood, polymer.

Run:
  tools/blender.sh raw_assets/weapons/enemy_guns/build.py --out assets/weapons/enemy \
      --preview docs/previews/enemy_guns.png
Muzzle points (also in data/enemies/*.tres): type56 (0.635, 0, 0.047),
pump (0.66, 0, 0.052), smg (0.355, 0, 0.045).
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

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

STEEL = hs.material("enemy_steel", (0.045, 0.047, 0.05), 0.42, 0.85)
WOOD = hs.material("enemy_wood", (0.33, 0.15, 0.06), 0.62, 0.0)
POLY = hs.material("enemy_polymer", (0.035, 0.035, 0.037), 0.7, 0.0)
MAG = hs.material("enemy_mag", (0.06, 0.058, 0.055), 0.5, 0.6)

BORE_Z = 0.047


def tri(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def pistol_grip(mat, top=(0.005, 0.0), bottom=(-0.04, -0.105), w=0.03):
    hs.finish(hs.side_profile("grip", [(top[0] - 0.03, 0.005), (top[0] + 0.012, 0.005), (bottom[0] + 0.012, bottom[1]),
                                       (bottom[0] - 0.03, bottom[1] + 0.006)], w), mat, bevel=0.003, segments=1)


def type56():
    # Milled receiver with the dust cover, trigger guard, wooden furniture, curved magazine.
    hs.finish(hs.side_profile("receiver", [(-0.075, 0.0), (0.215, 0.0), (0.215, 0.062), (0.19, 0.074),
                                           (-0.06, 0.074), (-0.075, 0.064)], 0.042), STEEL, bevel=0.002, segments=1)
    hs.finish(hs.cyl_x("cover", 0.021, -0.07, 0.2, verts=12, z=0.068), STEEL, bevel=0.0)
    hs.finish(hs.side_profile("guard", [(-0.035, 0.0), (0.03, 0.0), (0.03, -0.03), (-0.035, -0.03), (-0.035, -0.024),
                                        (0.024, -0.024), (0.024, -0.004), (-0.035, -0.004)], 0.008), STEEL, bevel=0.0)
    pistol_grip(WOOD)
    hs.finish(hs.side_profile("stock", [(-0.07, 0.066), (-0.07, 0.012), (-0.15, 0.0), (-0.345, -0.062),
                                        (-0.36, -0.058), (-0.36, 0.035), (-0.345, 0.045), (-0.2, 0.058)], 0.038), WOOD, bevel=0.004, segments=1)
    hs.finish(hs.cyl_x("handguard", 0.024, 0.215, 0.415, verts=10, z=BORE_Z - 0.006), WOOD, bevel=0.0)
    hs.finish(hs.cyl_x("gas_tube", 0.012, 0.2, 0.43, verts=8, z=BORE_Z + 0.03), STEEL, bevel=0.0)
    hs.finish(hs.cyl_x("barrel", 0.0105, 0.4, 0.60, verts=10, z=BORE_Z), STEEL, bevel=0.0)
    hs.finish(hs.cyl_x("muzzle", 0.0125, 0.60, 0.635, verts=10, z=BORE_Z), STEEL, bevel=0.0)
    hs.finish(hs.side_profile("front_sight", [(0.555, BORE_Z), (0.595, BORE_Z), (0.59, BORE_Z + 0.05),
                                              (0.57, BORE_Z + 0.05)], 0.018), STEEL, bevel=0.0)
    hs.finish(hs.side_profile("rear_sight", [(0.19, 0.07), (0.235, 0.07), (0.235, 0.088), (0.2, 0.084)], 0.03),
              STEEL, bevel=0.0)
    # Curved 30-round magazine: a sweep of slanted slices.
    pts_front, pts_back = [], []
    for i in range(7):
        t = i / 6
        cx = 0.07 + 0.085 * t ** 1.5
        cz = -0.235 * t
        pts_front.append((cx + 0.045 + 0.018 * t, cz))
        pts_back.append((cx, cz + 0.006 * t))
    hs.finish(hs.side_profile("mag", pts_front + list(reversed(pts_back)), 0.026), MAG, bevel=0.002, segments=1)


def pump():
    hs.finish(hs.side_profile("receiver", [(-0.07, -0.005), (0.17, -0.005), (0.17, 0.072), (-0.07, 0.072)], 0.04),
              STEEL, bevel=0.003, segments=1)
    hs.finish(hs.side_profile("guard", [(-0.035, 0.0), (0.03, 0.0), (0.03, -0.03), (-0.035, -0.03), (-0.035, -0.024),
                                        (0.024, -0.024), (0.024, -0.004), (-0.035, -0.004)], 0.008), STEEL, bevel=0.0)
    pistol_grip(POLY)
    hs.finish(hs.side_profile("stock", [(-0.07, 0.065), (-0.07, 0.0), (-0.34, -0.058), (-0.36, -0.054),
                                        (-0.36, 0.05), (-0.25, 0.06)], 0.04), POLY, bevel=0.004, segments=1)
    hs.finish(hs.cyl_x("barrel", 0.0125, 0.17, 0.66, verts=12, z=0.052), STEEL, bevel=0.0)
    hs.finish(hs.cyl_x("tube", 0.012, 0.17, 0.57, verts=10, z=0.02), STEEL, bevel=0.0)
    hs.finish(hs.cyl_x("cap", 0.0135, 0.57, 0.59, verts=10, z=0.02), STEEL, bevel=0.0)
    # Ribbed pump forend under the barrel, centred on the support hand.
    hs.finish(hs.cyl_x("forend", 0.028, 0.215, 0.375, verts=12, z=0.026), POLY, bevel=0.0)
    for i in range(5):
        x = 0.24 + i * 0.028
        hs.finish(hs.cyl_x(f"rib{i}", 0.0295, x, x + 0.01, verts=12, z=0.026), POLY, bevel=0.0)
    hs.finish(hs.cyl_z("bead", 0.003, 0.008, (0.655, 0, 0.068), verts=6), STEEL, bevel=0.0)


def smg():
    hs.finish(hs.cyl_x("receiver", 0.026, -0.05, 0.25, verts=14, z=0.045), STEEL, bevel=0.0)
    hs.finish(hs.side_profile("lower", [(-0.05, 0.0), (0.12, 0.0), (0.12, 0.03), (-0.05, 0.03)], 0.034),
              POLY, bevel=0.003, segments=1)
    hs.finish(hs.side_profile("guard", [(-0.03, 0.0), (0.03, 0.0), (0.03, -0.028), (-0.03, -0.028), (-0.03, -0.022),
                                        (0.024, -0.022), (0.024, -0.004), (-0.03, -0.004)], 0.008), POLY, bevel=0.0)
    pistol_grip(POLY)
    hs.finish(hs.side_profile("handguard", [(0.2, 0.02), (0.33, 0.02), (0.33, 0.07), (0.2, 0.07)], 0.046),
              POLY, bevel=0.006, segments=1)
    hs.finish(hs.cyl_x("barrel", 0.01, 0.33, 0.355, verts=10, z=0.045), STEEL, bevel=0.0)
    hs.finish(hs.side_profile("mag", [(0.085, 0.0), (0.12, 0.0), (0.15, -0.2), (0.115, -0.2)], 0.024),
              MAG, bevel=0.002, segments=1)
    hs.finish(hs.side_profile("stock", [(-0.05, 0.06), (-0.05, 0.02), (-0.30, -0.01), (-0.315, -0.01),
                                        (-0.315, 0.07), (-0.30, 0.07)], 0.012), STEEL, bevel=0.0)
    hs.finish(hs.side_profile("sight", [(-0.02, 0.07), (0.01, 0.07), (0.01, 0.085), (-0.02, 0.085)], 0.03),
              STEEL, bevel=0.0)


def build(name, fn):
    fn()
    ob = hs.join_parts(name)
    return ob


os.makedirs(args.out, exist_ok=True)
guns = {}
for name, fn in (("type56", type56), ("pump", pump), ("smg", smg)):
    ob = build(name, fn)
    guns[name] = ob
    print(f"{name}: {tri(ob)} tris")
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(args.out, f"{name}.gltf"), export_format="GLTF_SEPARATE",
                              use_selection=True, export_apply=True)

if args.preview:
    scene = bpy.context.scene
    for i, ob in enumerate(guns.values()):
        ob.location = (0, 0, -0.3 * i)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = 1400, 900
    world = bpy.data.worlds.new("w")
    world.color = (0.5, 0.52, 0.55)
    scene.world = world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (0.15, -1.9, -0.25)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.lens = 50
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(30))
    scene.collection.objects.link(sun)
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("preview:", args.preview)
