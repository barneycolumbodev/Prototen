"""Reduce a Tripo dog GLB to a target triangle count and texture size.

tools/blender.sh raw_assets/characters/attack_dog/reduce.py -- <in.glb> <out.glb> <tris> <tex_px>

Decimate (collapse) keeps the UVs, so Tripo's colour / normal / ORM maps stay
valid; they are scaled to tex_px and written as JPEG (colour) and PNG (normal,
ORM) inside the GLB. The dog is moved so its feet sit on z=0 and its chest is
over the origin, facing +X (Blender) = -Z in Godot after glTF's axis swap is
handled by the importer.
"""
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
argv = [a for a in argv if a != "--"]
src, dst, target, tex = argv[0], argv[1], int(argv[2]), int(argv[3])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obj = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

me = obj.data
me.calc_loop_triangles()
n = len(me.loop_triangles)
mod = obj.modifiers.new("dec", "DECIMATE")
mod.decimate_type = "COLLAPSE"
mod.ratio = min(1.0, target / n)
mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
obj.data.calc_loop_triangles()
print(f"REDUCE {n} -> {len(obj.data.loop_triangles)} tris")

# Pivot: feet on the ground, centred in plan.
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
ws = [v.co for v in obj.data.vertices]
lo = Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws)))
hi = Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))
off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
for v in obj.data.vertices:
    v.co -= off
obj.name = "attack_dog"
obj.data.name = "attack_dog"
print("SIZE", tuple(round(x, 3) for x in (hi - lo)))

for img in bpy.data.images:
    if img.size[0] > tex:
        img.scale(tex, tex)
    print("IMG", img.name, tuple(img.size))

bpy.ops.export_scene.gltf(
    filepath=dst,
    export_format="GLB",
    export_image_format="AUTO",
    export_jpeg_quality=88,
    use_selection=False,
    export_apply=True,
)
print("EXPORT", dst)
