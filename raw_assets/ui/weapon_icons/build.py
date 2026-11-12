"""Weapon wheel icons: one side-view render per gun, from its game model.

Cycles on the CPU at low samples (the bpy module has no GPU context for
Workbench): one light-grey material on every part, a soft key/rim setup,
transparent background, muzzle to the right. The wheel tints them
(src/ui/weapon_wheel_view.gd).

Run:
  tools/blender.sh raw_assets/ui/weapon_icons/build.py --out assets/ui/weapon_icons
  One gun: --only m14p
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="assets/ui/weapon_icons")
ap.add_argument("--only", default="")
ap.add_argument("--size", default="512x192")
args = ap.parse_args(argv)

GUNS = {
    "pistol_57": "assets/weapons/pistol_57/pistol_57.gltf",
    "mg42": "assets/weapons/mg42/mg42.gltf",
    "saiga12k": "assets/weapons/saiga12k/saiga12k.gltf",
    "rail_carbine": "assets/weapons/rail_carbine/rail_carbine.gltf",
    "m14p": "assets/weapons/m14p/m14p.gltf",
    "glock22": "assets/weapons/glock22/glock22.gltf",
}
# Parts left out of the icon (shown only in some states in game).
HIDE = {"lens", "reticle"}


def render(name, path, out_dir, w, h):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in scene.objects if o.type == "MESH"]
    for o in meshes:
        if o.name.split(".")[0] in HIDE:
            o.hide_render = True
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in meshes:
        if o.hide_render:
            continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    centre = (lo + hi) / 2
    span_x, span_z = hi.x - lo.x, hi.z - lo.z
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.13, 0.13, 1)
    scene.world = world
    flat = bpy.data.materials.new("icon")
    bsdf = flat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.72, 0.76, 0.76, 1)
    bsdf.inputs["Roughness"].default_value = 0.55
    for o in meshes:
        o.data.materials.clear()
        o.data.materials.append(flat)
    for lname, loc, energy in (("key", (0.3, -2.0, 1.6), 55.0), ("rim", (-1.5, 1.0, 0.8), 30.0),
                               ("under", (0.2, -1.0, -1.4), 12.0)):
        ld = bpy.data.lights.new(lname, "AREA")
        ld.energy = energy
        ld.size = 2.0
        lo_ob = bpy.data.objects.new(lname, ld)
        scene.collection.objects.link(lo_ob)
        lo_ob.location = centre + Vector(loc)
        lo_ob.rotation_euler = (centre - lo_ob.location).to_track_quat("-Z", "Y").to_euler()
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(span_x, span_z * w / h) * 1.06
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    # From the gun's right side (-Y): +X (muzzle) lands on the right of the frame.
    cam.location = centre + Vector((0.0, -3.0, 0.0))
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    os.makedirs(out_dir, exist_ok=True)
    scene.render.filepath = os.path.join(out_dir, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"weapon_icons: {name} -> {scene.render.filepath}")


w, h = (int(x) for x in args.size.split("x"))
for key, src in GUNS.items():
    if args.only and key not in args.only.split(","):
        continue
    if not os.path.exists(src):
        print(f"weapon_icons: skip {key} (no {src})")
        continue
    render(key, src, args.out, w, h)
