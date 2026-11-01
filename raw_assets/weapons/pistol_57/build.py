"""Pistol 57: FN Five-seveN-style 5.7x28mm pistol with a long suppressor.

Hard-surface model built to real dimensions (pistol ~208 mm, suppressor
~180 mm). Milsci touches: fluted suppressor with hex mount collar, heat band
and data plate; the Fire-Control Link readout and palm contact pads from
docs/design.md §3.5 ("contact pads on the palm; readout on the gun").

Pipeline (CLAUDE.md §7):
  1. Build the gun twice from the same code: HIGH (smooth bevels, dense
     cylinders, embossed lettering) and LOW (game mesh).
  2. UV-unwrap LOW. Bake HIGH -> LOW with Cycles on the CPU: base colour
     (with AO cavity grime), occlusion/roughness/metallic packed as ORM,
     tangent-space normal, emission.
  3. Export LOW with the baked textures as glTF (separate .gltf/.bin/PNGs).
  4. Optionally render a preview of the exported (baked) material.

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side (+Y = left). Origin = bore axis
above the grip. Units: metres.

Run:  tools/blender.sh raw_assets/weapons/pistol_57/build.py \
        --out assets/weapons/pistol_57/pistol_57.gltf --tex 2048 \
        --preview docs/previews/pistol_57.png --samples 160
      Without --out the procedural (unbaked) HIGH model is rendered instead.
"""
import argparse
import math
import os
import sys

import bpy  # must come first: the PyPI bpy module provides bmesh/mathutils
import bmesh
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=2048, help="baked texture size")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--detail", default="", help="also render a close-up of the grip/readout here")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

HIGH = {"name": "high", "seg": 3, "cyl": 1.0, "text": True}
LOW = {"name": "low", "seg": 1, "cyl": 0.5, "text": False}
D = HIGH          # detail level used by the helpers while building
PARTS = []        # parts of the build in progress
HELPERS = []      # cutters and pivots, deleted after the build is applied


# ---------------------------------------------------------------- geometry helpers
def link(ob):
    col.objects.link(ob)
    return ob


def prism(name, pts, vec):
    """Polygon `pts` (3D) extruded by `vec` into a closed solid."""
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new(p) for p in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=vec)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def side_profile(name, xz, width, y=0.0):
    """Side-view outline (x, z) extruded across Y, centred on y."""
    return prism(name, [(x, y - width / 2, z) for x, z in xz], (0, width, 0))


def section(name, yz, x0, x1):
    """Cross-section (y, z) extruded along X from x0 to x1."""
    return prism(name, [(x0, y, z) for y, z in yz], (x1 - x0, 0, 0))


def box(name, size, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return ob


def nverts(n):
    return max(6, int(round(n * D["cyl"])))


def cyl_x(name, radius, x0, x1, verts=48, z=0.0, y=0.0, fixed=False):
    """Cylinder along X from x0 to x1."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts if fixed else nverts(verts), radius=radius, depth=x1 - x0,
                                        location=((x0 + x1) / 2, y, z), rotation=(0, math.pi / 2, 0))
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def cyl_y(name, radius, depth, loc, verts=32):
    """Cylinder along Y (across the gun)."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=nverts(verts), radius=radius, depth=depth,
                                        location=loc, rotation=(math.pi / 2, 0, 0))
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def cutter(ob):
    ob.display_type = "WIRE"
    ob.hide_render = True
    if ob not in HELPERS:
        HELPERS.append(ob)
    return ob


def cut(target, tool):
    cutter(tool)
    m = target.modifiers.new(f"cut_{tool.name}", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = tool


def finish(ob, mat, bevel=0.0006, segments=3, angle=35.0):
    """Bevel + weighted normals for clean hard-surface shading."""
    if bevel > 0:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = max(1, min(segments, D["seg"]))
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(angle)
        b.harden_normals = True
    ob.data.shade_smooth()
    w = ob.modifiers.new("wnormal", "WEIGHTED_NORMAL")
    w.keep_sharp = True
    ob.data.materials.append(mat)
    PARTS.append(ob)
    return ob


def radial_array(ob, count, center_x):
    """Repeat `ob` around the X axis. Moves ob's origin onto the axis at
    center_x without moving its geometry."""
    offset = ob.location - Vector((center_x, 0, 0))
    ob.data.transform(Matrix.Translation(offset))
    ob.location = (center_x, 0, 0)
    pivot = link(bpy.data.objects.new(ob.name + "_pivot", None))
    HELPERS.append(pivot)
    pivot.location = (center_x, 0, 0)
    pivot.rotation_euler = (2 * math.pi / count, 0, 0)
    a = ob.modifiers.new("radial", "ARRAY")
    a.count = count
    a.use_relative_offset = False
    a.use_object_offset = True
    a.offset_object = pivot


def linear_array(ob, count, step):
    a = ob.modifiers.new("array", "ARRAY")
    a.count = count
    a.use_relative_offset = False
    a.use_constant_offset = True
    a.constant_offset_displace = step


def mirror_y(ob):
    m = ob.modifiers.new("mirror", "MIRROR")
    m.use_axis = (False, True, False)


# ---------------------------------------------------------------- procedural materials
def material(name, base, rough, metal, wear=None, bump_scale=0.0, bump_strength=0.0, emission=None,
             stipple=False, machining=False):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    rough_socket = None
    if wear:
        # Edge wear: convex edges (high pointiness) show bare, smoother metal.
        geo = N.new("ShaderNodeNewGeometry")
        ramp = N.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.52
        ramp.color_ramp.elements[1].position = 0.6
        noise = N.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 400.0
        mult = N.new("ShaderNodeMath")
        mult.operation = "MULTIPLY"
        L.new(geo.outputs["Pointiness"], ramp.inputs["Fac"])
        L.new(ramp.outputs["Color"], mult.inputs[0])
        L.new(noise.outputs["Fac"], mult.inputs[1])
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*base, 1)
        mix.inputs["B"].default_value = (*wear, 1)
        L.new(mult.outputs[0], mix.inputs["Factor"])
        L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        rmix = N.new("ShaderNodeMapRange")
        rmix.inputs["To Min"].default_value = rough
        rmix.inputs["To Max"].default_value = 0.25
        L.new(mult.outputs[0], rmix.inputs["Value"])
        rough_socket = rmix.outputs["Result"]
    if machining:
        # Fine streaks along the slide (milling marks) vary the roughness.
        tc = N.new("ShaderNodeTexCoord")
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.02, 1.0, 1.0)
        streak = N.new("ShaderNodeTexNoise")
        streak.inputs["Scale"].default_value = 900.0
        streak.inputs["Detail"].default_value = 2.0
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        L.new(mp.outputs["Vector"], streak.inputs["Vector"])
        add = N.new("ShaderNodeMath")
        add.operation = "MULTIPLY_ADD"
        add.inputs[1].default_value = 0.14
        add.inputs[2].default_value = -0.07
        L.new(streak.outputs["Fac"], add.inputs[0])
        total = N.new("ShaderNodeMath")
        total.operation = "ADD"
        total.use_clamp = True
        if rough_socket:
            L.new(rough_socket, total.inputs[0])
        else:
            total.inputs[0].default_value = rough
        L.new(add.outputs[0], total.inputs[1])
        rough_socket = total.outputs[0]
    if rough_socket:
        L.new(rough_socket, bsdf.inputs["Roughness"])
    normal_socket = None
    if bump_strength > 0:
        tex = N.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        bump = N.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.0002
        L.new(tex.outputs["Fac"], bump.inputs["Height"])
        normal_socket = bump.outputs["Normal"]
    if stipple:
        # Stippled grip panel: voronoi dimples, only on the grip below the slide line.
        tc = N.new("ShaderNodeTexCoord")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(tc.outputs["Object"], sep.inputs["Vector"])
        below = N.new("ShaderNodeMath")
        below.operation = "LESS_THAN"
        below.inputs[1].default_value = -0.052
        L.new(sep.outputs["Z"], below.inputs[0])
        behind = N.new("ShaderNodeMath")
        behind.operation = "LESS_THAN"
        behind.inputs[1].default_value = -0.03
        L.new(sep.outputs["X"], behind.inputs[0])
        above_mag = N.new("ShaderNodeMath")
        above_mag.operation = "GREATER_THAN"
        above_mag.inputs[1].default_value = -0.13
        L.new(sep.outputs["Z"], above_mag.inputs[0])
        m1 = N.new("ShaderNodeMath")
        m1.operation = "MULTIPLY"
        L.new(below.outputs[0], m1.inputs[0])
        L.new(behind.outputs[0], m1.inputs[1])
        mask = N.new("ShaderNodeMath")
        mask.operation = "MULTIPLY"
        L.new(m1.outputs[0], mask.inputs[0])
        L.new(above_mag.outputs[0], mask.inputs[1])
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 1100.0
        L.new(tc.outputs["Object"], vor.inputs["Vector"])
        height = N.new("ShaderNodeMath")
        height.operation = "MULTIPLY"
        L.new(vor.outputs["Distance"], height.inputs[0])
        L.new(mask.outputs[0], height.inputs[1])
        bump2 = N.new("ShaderNodeBump")
        bump2.inputs["Strength"].default_value = 0.6
        bump2.inputs["Distance"].default_value = 0.0004
        L.new(height.outputs[0], bump2.inputs["Height"])
        if normal_socket:
            L.new(normal_socket, bump2.inputs["Normal"])
        normal_socket = bump2.outputs["Normal"]
        # Stippled area is rougher.
        rmask = N.new("ShaderNodeMapRange")
        rmask.inputs["To Min"].default_value = rough
        rmask.inputs["To Max"].default_value = min(1.0, rough + 0.18)
        L.new(mask.outputs[0], rmask.inputs["Value"])
        L.new(rmask.outputs["Result"], bsdf.inputs["Roughness"])
    if normal_socket:
        L.new(normal_socket, bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


M_SLIDE = material("slide_nitride", (0.045, 0.047, 0.05), 0.4, 0.75, wear=(0.42, 0.42, 0.43),
                   bump_scale=900, bump_strength=0.05, machining=True)
M_FRAME = material("frame_polymer", (0.062, 0.066, 0.052), 0.6, 0.0, bump_scale=1400, bump_strength=0.18,
                   stipple=True)
M_STEEL = material("steel_dark", (0.07, 0.07, 0.075), 0.3, 1.0, wear=(0.5, 0.5, 0.52))
M_CAN = material("suppressor_cerakote", (0.13, 0.135, 0.14), 0.38, 1.0, wear=(0.55, 0.55, 0.56),
                 bump_scale=700, bump_strength=0.04)
M_BAND = material("heat_band", (0.16, 0.12, 0.07), 0.45, 1.0)
M_GLASS = material("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = material("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_PAD = material("contact_pad", (0.55, 0.32, 0.18), 0.3, 1.0)
M_MARK = material("engraving", (0.34, 0.35, 0.36), 0.5, 1.0)
SOURCE_MATERIALS = [M_SLIDE, M_FRAME, M_STEEL, M_CAN, M_BAND, M_GLASS, M_AMBER, M_PAD, M_MARK]


# ---------------------------------------------------------------- the gun
SLIDE_HALF = 0.01275
FRAME_W = 0.030
CAN_R = 0.0182
X_COLLAR0, X_COLLAR1 = 0.104, 0.126
X_TUBE1 = 0.262
X_CAP1 = 0.284


def text(name, body, size, loc):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = 0.00012
    cu.resolution_u = 4
    ob = link(bpy.data.objects.new(name, cu))
    ob.location = loc
    ob.rotation_euler = (math.pi / 2, 0, 0)
    ob.data.materials.append(M_MARK)
    PARTS.append(ob)
    return ob


def build_gun():
    # Slide
    slide = section("slide", [(-SLIDE_HALF, -0.010), (SLIDE_HALF, -0.010), (SLIDE_HALF, 0.013),
                              (0.0085, 0.020), (-0.0085, 0.020), (-SLIDE_HALF, 0.013)], -0.100, 0.098)
    cut(slide, box("slide_front_cut", (0.03, 0.05, 0.02), (0.108, 0, -0.016), (0, math.radians(-38), 0)))
    cut(slide, box("ejection_port", (0.034, 0.012, 0.012), (0.012, 0.009, 0.019)))
    for name, x0, n in (("rear_serr", -0.094, 8), ("front_serr", 0.056, 6)):
        s = box(name, (0.0014, 0.0026, 0.016), (x0, SLIDE_HALF + 0.0001, 0.003), (0, math.radians(-8), 0))
        linear_array(s, n, (0.0038, 0, 0))
        mirror_y(s)
        cut(slide, s)
    cut(slide, box("slide_flat", (0.07, 0.004, 0.004), (0.010, -SLIDE_HALF - 0.0005, 0.0145), (math.radians(-35), 0, 0)))
    finish(slide, M_SLIDE)

    # Sights
    rear = box("rear_sight", (0.012, 0.018, 0.0075), (-0.086, 0, 0.0235))
    cut(rear, box("rear_notch", (0.02, 0.0035, 0.004), (-0.086, 0, 0.0275)))
    finish(rear, M_STEEL, bevel=0.0004)
    finish(box("front_sight", (0.006, 0.003, 0.0065), (0.090, 0, 0.0228)), M_STEEL, bevel=0.0004)

    # Frame
    frame = side_profile("frame", [
        (-0.096, -0.010), (0.094, -0.010), (0.097, -0.015), (0.094, -0.027),
        (0.046, -0.027), (0.047, -0.052), (0.040, -0.061),
        (-0.020, -0.061), (-0.027, -0.054),
        (-0.056, -0.134), (-0.061, -0.138), (-0.103, -0.138), (-0.107, -0.132),
        (-0.081, -0.046), (-0.094, -0.031), (-0.105, -0.023), (-0.105, -0.013),
    ], FRAME_W)
    cut(frame, side_profile("guard_hole", [(-0.018, -0.030), (0.037, -0.030), (0.039, -0.050),
                                           (0.033, -0.0555), (-0.014, -0.0555), (-0.023, -0.046)], 0.05))
    # Front strap runs from (-0.027, -0.054) to (-0.056, -0.134); groove centres sit just outside it.
    groove = cyl_y("finger_groove", 0.0068, 0.06, (-0.0300, 0, -0.0745), verts=32)
    linear_array(groove, 3, (-0.0071, 0, -0.0197))
    cut(frame, groove)
    finish(frame, M_FRAME, bevel=0.0012, segments=3)

    # Accessory rail
    rail = box("rail", (0.040, 0.019, 0.0045), (0.069, 0, -0.0292))
    slot = box("rail_slot", (0.0026, 0.03, 0.003), (0.052, 0, -0.0315))
    linear_array(slot, 7, (0.0052, 0, 0))
    cut(rail, slot)
    finish(rail, M_FRAME, bevel=0.0004)

    finish(side_profile("mag_base", [(-0.058, -0.137), (-0.105, -0.137), (-0.108, -0.1465), (-0.055, -0.1465)], 0.027),
           M_STEEL, bevel=0.0008)
    finish(side_profile("trigger", [(0.012, -0.029), (0.018, -0.029), (0.016, -0.040), (0.021, -0.051),
                                    (0.015, -0.053), (0.008, -0.041)], 0.0055), M_STEEL, bevel=0.0005)

    # Controls
    finish(box("slide_stop", (0.020, 0.0025, 0.0045), (-0.020, -FRAME_W / 2 - 0.0008, -0.0125)), M_STEEL, bevel=0.0005)
    for sy in (-1, 1):
        finish(cyl_y(f"mag_release_{sy}", 0.0034, 0.0022, (-0.0215, sy * (FRAME_W / 2 + 0.0003), -0.036), verts=24),
               M_STEEL, bevel=0.0003)

    # Fire-Control Link: readout window on the left of the frame + palm contact strips
    finish(box("fcl_readout", (0.022, 0.0012, 0.0055), (-0.050, -FRAME_W / 2 - 0.0004, -0.0175)), M_GLASS, bevel=0.0003)
    for i, w in enumerate((0.004, 0.007, 0.0025, 0.005)):
        finish(box(f"fcl_seg{i}", (w, 0.0004, 0.0011), (-0.058 + i * 0.0052 + w / 2, -FRAME_W / 2 - 0.0011, -0.0168)),
               M_AMBER, bevel=0)
    finish(box("fcl_bar", (0.016, 0.0004, 0.0006), (-0.052, -FRAME_W / 2 - 0.0011, -0.0192)), M_AMBER, bevel=0)
    for i in range(3):
        t = 0.22 + i * 0.2
        pad = box(f"palm_pad{i}", (0.0012, 0.022, 0.006), (0, 0, 0))
        pad.location = (-0.081 + (-0.107 + 0.081) * t - 0.0002, 0, -0.046 + (-0.132 + 0.046) * t)
        pad.rotation_euler = (0, math.radians(16.8), 0)
        finish(pad, M_PAD, bevel=0.0003)

    if D["text"]:
        text("mark_model", "SP-57  //  5.7x28", 0.0042, (-0.040, -SLIDE_HALF - 0.0001, -0.0055))

    # Barrel + suppressor
    finish(cyl_x("barrel", 0.0066, 0.080, 0.106, verts=32), M_STEEL, bevel=0.0003)
    collar = cyl_x("can_collar", 0.0196, X_COLLAR0, X_COLLAR1, verts=6, fixed=True)
    collar.rotation_euler = (math.radians(30), 0, 0)
    finish(collar, M_CAN, bevel=0.0008, segments=2)

    tube = cyl_x("can_tube", CAN_R, X_COLLAR1, X_TUBE1, verts=64)
    flute = cyl_x("flute", 0.0028, 0.146, 0.236, verts=16, z=CAN_R + 0.0013)
    radial_array(flute, 8, (0.146 + 0.236) / 2)
    cut(tube, flute)
    cut(tube, box("can_flat", (0.050, 0.006, 0.02), (0.186, -CAN_R - 0.0016, 0.0)))
    fin = cyl_x("fin_cut", CAN_R + 0.002, 0.130, 0.1315, verts=48)
    linear_array(fin, 3, (0.0035, 0, 0))
    b = fin.modifiers.new("hollow", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.solver = "EXACT"
    b.object = cutter(cyl_x("fin_core", CAN_R - 0.0011, 0.120, 0.145, verts=48))
    cut(tube, fin)
    finish(tube, M_CAN, bevel=0.0005)

    finish(cyl_x("can_band", CAN_R + 0.0003, 0.248, 0.252, verts=64), M_BAND, bevel=0.0002)
    cap = cyl_x("can_cap", 0.0186, X_TUBE1, X_CAP1, verts=64)
    cut(cap, cyl_x("bore", 0.0042, X_TUBE1 - 0.01, X_CAP1 + 0.01, verts=24))
    notch = box("crown_notch", (0.006, 0.004, 0.012), (X_CAP1, 0, 0.016))
    radial_array(notch, 6, X_CAP1)
    cut(cap, notch)
    finish(cap, M_CAN, bevel=0.0012, segments=3)

    finish(box("can_plate", (0.042, 0.0008, 0.0085), (0.186, -CAN_R + 0.0013, 0.0)), M_SLIDE, bevel=0.0003)
    if D["text"]:
        text("mark_can", "SR-57S  SUPPRESSOR", 0.0028, (0.1655, -CAN_R + 0.0008, -0.0009))
    finish(box("can_led", (0.0025, 0.0005, 0.0012), (0.2045, -CAN_R + 0.0007, 0.0024)), M_AMBER, bevel=0)


def build(detail):
    """Builds the gun at a detail level and returns it as one joined mesh object."""
    global D
    D = detail
    PARTS.clear()
    build_gun()
    bpy.ops.object.select_all(action="DESELECT")
    for ob in PARTS:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.convert(target="MESH")  # applies modifiers, turns text into mesh
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = "pistol_57" if detail is LOW else "pistol_57_high"
    for ob in HELPERS:
        bpy.data.objects.remove(ob)
    HELPERS.clear()
    return joined


def tri_count(ob):
    me = ob.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


# ---------------------------------------------------------------- baking
def new_image(name, size, non_color):
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def set_bake_target(image):
    for mat in SOURCE_MATERIALS:
        nt = mat.node_tree
        node = nt.nodes.get("bake_target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "bake_target"
        node.image = image
        nt.nodes.active = node


def route_to_emission(channel):
    """Temporarily shows one Principled input as emission so EMIT bakes it."""
    for mat in SOURCE_MATERIALS:
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        out = nt.nodes["Material Output"]
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.name = "bake_emit"
        emit.inputs["Strength"].default_value = 1.0
        if channel == "Emission":
            strength = bsdf.inputs["Emission Strength"].default_value
            c = bsdf.inputs["Emission Color"].default_value if strength > 0 else (0, 0, 0, 1)
            emit.inputs["Color"].default_value = c
        else:
            src = bsdf.inputs[channel]
            if src.is_linked:
                nt.links.new(src.links[0].from_socket, emit.inputs["Color"])
            else:
                v = src.default_value
                emit.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1)
        nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])


def restore_shading():
    for mat in SOURCE_MATERIALS:
        nt = mat.node_tree
        nt.links.new(nt.nodes["Principled BSDF"].outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
        emit = nt.nodes.get("bake_emit")
        if emit:
            nt.nodes.remove(emit)


def bake(kind, image, samples):
    set_bake_target(image)
    scene.cycles.samples = samples
    bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=0.0006,
                        max_ray_distance=0.003, margin=12, use_clear=True)


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


def bake_textures(high, low, size, tex_dir):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.bake.use_selected_to_active = True
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    # LOW must use the same materials so the bake target node is found; give it all source materials.
    imgs = {}
    for ch, non_color in (("base", False), ("rough", True), ("metal", True), ("emit", False)):
        imgs[ch] = new_image(f"pistol_57_{ch}", size, non_color)
        route_to_emission({"base": "Base Color", "rough": "Roughness", "metal": "Metallic", "emit": "Emission"}[ch])
        bake("EMIT", imgs[ch], 1)
        restore_shading()
        print(f"pistol_57: baked {ch}")
    imgs["ao"] = new_image("pistol_57_ao", size, True)
    scene.world.light_settings.distance = 0.02
    bake("AO", imgs["ao"], 48)
    print("pistol_57: baked ao")
    imgs["normal"] = new_image("pistol_57_normal", size, True)
    bake("NORMAL", imgs["normal"], 8)
    print("pistol_57: baked normal")

    ao = pixels(imgs["ao"])[:, 0]
    # Cavity grime: darken the albedo where AO is low (mobile has no SSAO by default).
    base = pixels(imgs["base"])
    base[:, :3] *= (0.55 + 0.45 * ao)[:, None]
    out_base = new_image("pistol_57_basecolor", size, False)
    out_base.pixels.foreach_set(base.ravel())
    orm = np.ones((size * size, 4), dtype=np.float32)
    orm[:, 0] = ao
    orm[:, 1] = pixels(imgs["rough"])[:, 0]
    orm[:, 2] = pixels(imgs["metal"])[:, 0]
    out_orm = new_image("pistol_57_orm", size, True)
    out_orm.pixels.foreach_set(orm.ravel())

    os.makedirs(tex_dir, exist_ok=True)
    final = {"basecolor": out_base, "orm": out_orm, "normal": imgs["normal"], "emission": imgs["emit"]}
    for key, img in final.items():
        img.filepath_raw = os.path.join(tex_dir, f"pistol_57_{key}.png")
        img.file_format = "PNG"
        img.save()
    return final


def gltf_output_group():
    """Node group the glTF exporter reads the occlusion texture from."""
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return g


def baked_material(tex):
    mat = bpy.data.materials.new("pistol_57")
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]

    def image_node(img):
        n = N.new("ShaderNodeTexImage")
        n.image = img
        return n

    L.new(image_node(tex["basecolor"]).outputs["Color"], bsdf.inputs["Base Color"])
    orm = image_node(tex["orm"])
    sep = N.new("ShaderNodeSeparateColor")
    L.new(orm.outputs["Color"], sep.inputs["Color"])
    L.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    L.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    occl = N.new("ShaderNodeGroup")
    occl.node_tree = gltf_output_group()
    L.new(sep.outputs["Red"], occl.inputs["Occlusion"])
    nmap = N.new("ShaderNodeNormalMap")
    L.new(image_node(tex["normal"]).outputs["Color"], nmap.inputs["Color"])
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    L.new(image_node(tex["emission"]).outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 4.0
    mat.use_backface_culling = True  # exported as single-sided
    return mat


# ---------------------------------------------------------------- run
if args.out:
    high = build(HIGH)
    low = build(LOW)
    print(f"pistol_57: high {tri_count(high)} tris, low {tri_count(low)} tris")
    # UV-unwrap the game mesh.
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    # Double the texel density of the slide and data plate (most visible in first person,
    # and they carry the lettering). Packing keeps relative island sizes.
    slide_slot = [m.name if m else "" for m in low.data.materials].index(M_SLIDE.name)
    uv = low.data.uv_layers.active.data
    for poly in low.data.polygons:
        if poly.material_index == slide_slot:
            for li in poly.loop_indices:
                uv[li].uv = uv[li].uv * 2.0
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake_world")
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    textures = bake_textures(high, low, args.tex, tex_dir)
    bpy.data.objects.remove(high)
    final_mat = baked_material(textures)
    low.data.materials.clear()
    low.data.materials.append(final_mat)
    for poly in low.data.polygons:
        poly.material_index = 0
    for img in textures.values():  # point the exporter at the saved PNGs
        img.filepath = img.filepath_raw
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.export_scene.gltf(filepath=args.out, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True,
                              export_image_format="AUTO")
    print(f"pistol_57: exported {args.out} ({tri_count(low)} triangles, {args.tex}px textures)")
else:
    build(HIGH)

# ---------------------------------------------------------------- preview render
if args.preview:
    w, h = (int(v) for v in args.res.split("x"))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.filepath = args.preview
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"

    world = bpy.data.worlds.new("studio")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.013, 0.015, 1)
    scene.world = world

    floor = link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0.09, 0, -0.175)
    floor.data.materials.append(material("floor", (0.008, 0.0085, 0.009), 0.22, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.09, 0, -0.05)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = color
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return ob

    area("key", (-0.25, -0.55, 0.55), 9, 0.6)
    area("fill", (0.6, -0.6, -0.02), 1.6, 0.8, (0.75, 0.85, 1.0))
    area("rim", (0.25, 0.6, 0.4), 7, 0.5, (1.0, 0.82, 0.62))
    area("top", (0.1, 0.0, 0.7), 2.5, 1.0)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.dof.use_dof = True
    cam = link(bpy.data.objects.new("cam", cam_data))
    scene.camera = cam

    def shoot(path, lens, fstop, target, offset):
        cam_data.lens = lens
        cam_data.dof.aperture_fstop = fstop
        target = Vector(target)
        cam.location = target + Vector(offset)
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam_data.dof.focus_distance = (target - cam.location).length
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"pistol_57: preview {path}")

    shoot(args.preview, 70, 8.0, (0.088, 0, -0.058), (0.06, -0.97, 0.24))
    if args.detail:  # close-up: grip stippling, FCL readout, slide lettering
        shoot(args.detail, 100, 5.6, (-0.03, 0, -0.04), (0.14, -0.40, 0.13))
