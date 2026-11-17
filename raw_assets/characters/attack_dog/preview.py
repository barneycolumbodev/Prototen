"""Inspect a Tripo dog GLB and render a four-view contact sheet.

tools/blender.sh raw_assets/characters/attack_dog/preview.py -- <model.glb> <out.png>

Prints triangle count, dimensions, materials and texture sizes, then renders
front / three-quarter / side / close-up of the head with Cycles on the CPU.
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
argv = [a for a in argv if a != "--"]
src, out = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]

tris = 0
lo = Vector((1e9, 1e9, 1e9))
hi = -lo
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    tris += len(me.loop_triangles)
    for v in o.bound_box:
        w = o.matrix_world @ Vector(v)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
size = hi - lo
print(f"STATS meshes={len(meshes)} tris={tris} size_m=({size.x:.3f},{size.y:.3f},{size.z:.3f})")
for m in bpy.data.materials:
    print("MAT", m.name)
for img in bpy.data.images:
    print("IMG", img.name, tuple(img.size))

center = (lo + hi) / 2
radius = size.length / 2

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"

world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.06, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
scene.world = world

# Floor
bpy.ops.mesh.primitive_plane_add(size=20, location=(center.x, center.y, lo.z))
floor = bpy.context.object
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.18, 0.18, 0.19, 1)
fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
floor.data.materials.append(fm)


def light(name, loc, energy, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    d = center - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)


r = max(radius, 0.3)
light("key", center + Vector((2.5 * r, -2.5 * r, 3 * r)), 400 * r * r, 2 * r)
light("fill", center + Vector((-3 * r, -1.5 * r, 1.5 * r)), 120 * r * r, 3 * r)
light("rim", center + Vector((0, 3 * r, 2.5 * r)), 250 * r * r, 2 * r)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 50
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# Find the head: the end of the longest horizontal axis with the highest points.
long_axis = 0 if size.x >= size.y else 1


def head_end():
    best = None
    for sign in (-1, 1):
        zmax = -1e9
        for o in meshes:
            for v in o.data.vertices:
                w = o.matrix_world @ v.co
                along = (w[long_axis] - center[long_axis]) * sign
                if along > size[long_axis] * 0.3:
                    zmax = max(zmax, w.z)
        if best is None or zmax > best[1]:
            best = (sign, zmax)
    return best[0]


hs = head_end()
fwd = Vector((0, 0, 0))
fwd[long_axis] = hs
side = Vector((0, 0, 1)).cross(fwd)
print("HEAD axis", "xy"[long_axis], "sign", hs)

# Head: centroid of the front-most 18 % of the body.
acc = Vector((0, 0, 0))
cnt = 0
for o in meshes:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        if (w[long_axis] - center[long_axis]) * hs > size[long_axis] * 0.32:
            acc += w
            cnt += 1
head = acc / max(cnt, 1)
head[long_axis] -= hs * size[long_axis] * 0.04

views = [
    ("front", center + fwd * 3.2 * r + Vector((0, 0, 0.6 * r)), center),
    ("threequarter", center + (fwd + side * 1.1).normalized() * 3.2 * r + Vector((0, 0, 0.9 * r)), center),
    ("side", center + side * 3.4 * r + Vector((0, 0, 0.3 * r)), center),
    ("head", head + (fwd * 1.0 + side * 0.75).normalized() * 0.75 + Vector((0, 0, 0.06)), head),
]
paths = []
for name, loc, target in views:
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    p = out.replace(".png", f"_{name}.png")
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    paths.append(p)
    print("RENDER", p)

# Contact sheet
try:
    import numpy as np
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    sheet = np.zeros((h * 2, w * 2, 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        row, col = 1 - i // 2, i % 2
        sheet[row * h:(row + 1) * h, col * w:(col + 1) * w] = a
    s = bpy.data.images.new("sheet", w * 2, h * 2)
    s.pixels = sheet.ravel()
    s.filepath_raw = out
    s.file_format = "PNG"
    s.save()
    print("SHEET", out)
except Exception as e:  # noqa: BLE001
    print("sheet failed", e)
