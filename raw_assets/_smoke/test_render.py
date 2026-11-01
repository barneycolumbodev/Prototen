"""Blender smoke test (CLAUDE.md §10.4): build a bevelled cube, render one frame with Cycles on the CPU.

Run: blender -b --factory-startup --python raw_assets/_smoke/test_render.py -- /path/out.png
"""
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/blender_smoke.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.render.resolution_x, scene.render.resolution_y = 480, 320
scene.render.filepath = out

bpy.ops.mesh.primitive_cube_add(size=1.0)
cube = bpy.context.active_object
bevel = cube.modifiers.new("Bevel", "BEVEL")
bevel.width, bevel.segments = 0.08, 3
mat = bpy.data.materials.new("Steel")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.35, 0.37, 0.4, 1.0)
bsdf.inputs["Metallic"].default_value = 0.9
bsdf.inputs["Roughness"].default_value = 0.35
cube.data.materials.append(mat)

bpy.ops.object.light_add(type="SUN", rotation=(0.8, 0.2, 0.6))
bpy.context.active_object.data.energy = 4.0
bpy.ops.object.camera_add(location=(2.4, -2.4, 1.8), rotation=(1.1, 0.0, 0.785))
scene.camera = bpy.context.active_object
world = bpy.data.worlds.new("World")
world.color = (0.05, 0.05, 0.06)
scene.world = world

bpy.ops.render.render(write_still=True)
print(f"blender_smoke: wrote {out} with Blender {bpy.app.version_string}")
