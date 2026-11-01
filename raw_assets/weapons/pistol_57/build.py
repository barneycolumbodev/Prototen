"""Pistol 57: FN Five-seveN-style 5.7x28mm pistol with a long suppressor.

Hard-surface model built to real dimensions (overall pistol length ~208 mm,
suppressor ~180 mm). Milsci touches: fluted suppressor with a hex mount
collar and machined flat, and the Fire-Control Link readout on the frame
(docs/design.md §3.5: "contact pads on the palm; readout on the gun").

Axes: +X = muzzle, +Z = up, -Y = the shooter's left side. Origin = bore axis
above the grip. Units: metres.

Run:  tools/blender.sh raw_assets/weapons/pistol_57/build.py \
        [--out assets/weapons/pistol_57/pistol_57.glb] [--preview out.png] [--samples 128]
"""
import argparse
import math
import sys

import bpy  # must come first: the PyPI bpy module provides bmesh/mathutils
import bmesh
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", default="1600x900")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection
PARTS = []  # objects that make up the weapon (exported); cutters are not listed


# ---------------------------------------------------------------- helpers
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


def cyl_x(name, radius, x0, x1, verts=48, z=0.0, y=0.0):
    """Cylinder along X from x0 to x1."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=x1 - x0,
                                        location=((x0 + x1) / 2, y, z), rotation=(0, math.pi / 2, 0))
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def cyl_y(name, radius, depth, loc, verts=32):
    """Cylinder along Y (across the gun)."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth,
                                        location=loc, rotation=(math.pi / 2, 0, 0))
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def cutter(ob):
    ob.display_type = "WIRE"
    ob.hide_render = True
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
        b.segments = segments
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
    pivot = bpy.data.objects.new(ob.name + "_pivot", None)
    link(pivot)
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
    m.mirror_object = None


# ---------------------------------------------------------------- materials
def material(name, base, rough, metal, wear=None, bump_scale=0.0, bump_strength=0.0, emission=None):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if wear:
        # Edge wear: convex edges (high pointiness) show bare, smoother metal.
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.52
        ramp.color_ramp.elements[1].position = 0.6
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 400.0
        mult = nt.nodes.new("ShaderNodeMath")
        mult.operation = "MULTIPLY"
        nt.links.new(geo.outputs["Pointiness"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], mult.inputs[0])
        nt.links.new(noise.outputs["Fac"], mult.inputs[1])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*base, 1)
        mix.inputs["B"].default_value = (*wear, 1)
        nt.links.new(mult.outputs[0], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        rmix = nt.nodes.new("ShaderNodeMapRange")
        rmix.inputs["To Min"].default_value = rough
        rmix.inputs["To Max"].default_value = 0.25
        nt.links.new(mult.outputs[0], rmix.inputs["Value"])
        nt.links.new(rmix.outputs["Result"], bsdf.inputs["Roughness"])
    if bump_strength > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.0002
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


M_SLIDE = material("slide_cerakote", (0.045, 0.047, 0.05), 0.42, 0.75, wear=(0.42, 0.42, 0.43), bump_scale=900, bump_strength=0.05)
M_FRAME = material("frame_polymer", (0.062, 0.066, 0.052), 0.62, 0.0, bump_scale=1400, bump_strength=0.18)
M_STEEL = material("steel_dark", (0.07, 0.07, 0.075), 0.3, 1.0, wear=(0.5, 0.5, 0.52))
M_CAN = material("suppressor_tungsten", (0.13, 0.135, 0.14), 0.38, 1.0, wear=(0.55, 0.55, 0.56), bump_scale=700, bump_strength=0.04)
M_BAND = material("heat_band", (0.16, 0.12, 0.07), 0.45, 1.0)
M_GLASS = material("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = material("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_PAD = material("contact_pad", (0.55, 0.32, 0.18), 0.3, 1.0)
M_MARK = material("engraving", (0.32, 0.33, 0.34), 0.5, 1.0)

# ---------------------------------------------------------------- slide
SLIDE_HALF = 0.01275
slide = section("slide", [(-SLIDE_HALF, -0.010), (SLIDE_HALF, -0.010), (SLIDE_HALF, 0.013),
                          (0.0085, 0.020), (-0.0085, 0.020), (-SLIDE_HALF, 0.013)], -0.100, 0.098)
cut(slide, box("slide_front_cut", (0.03, 0.05, 0.02), (0.108, 0, -0.016), (0, math.radians(-38), 0)))
cut(slide, box("ejection_port", (0.034, 0.012, 0.012), (0.012, 0.009, 0.019)))
# Serrations, rear and front, both sides.
for name, x0, n in (("rear_serr", -0.094, 8), ("front_serr", 0.056, 6)):
    s = box(name, (0.0014, 0.0026, 0.016), (x0, SLIDE_HALF + 0.0001, 0.003), (0, math.radians(-8), 0))
    linear_array(s, n, (0.0038, 0, 0))
    mirror_y(s)
    cut(slide, s)
# Machined lightening flat along the upper flank (milsci hint).
flat = box("slide_flat", (0.07, 0.004, 0.004), (0.010, -SLIDE_HALF - 0.0005, 0.0145), (math.radians(-35), 0, 0))
cut(slide, flat)
finish(slide, M_SLIDE)

# Sights
rear = box("rear_sight", (0.012, 0.018, 0.0075), (-0.086, 0, 0.0235))
cut(rear, box("rear_notch", (0.02, 0.0035, 0.004), (-0.086, 0, 0.0275)))
finish(rear, M_STEEL, bevel=0.0004)
finish(box("front_sight", (0.006, 0.003, 0.0065), (0.090, 0, 0.0228)), M_STEEL, bevel=0.0004)

# ---------------------------------------------------------------- frame
FRAME_W = 0.030
frame = side_profile("frame", [
    (-0.096, -0.010), (0.094, -0.010), (0.097, -0.015), (0.094, -0.027),
    (0.046, -0.027), (0.047, -0.052), (0.040, -0.061),
    (-0.020, -0.061), (-0.027, -0.054),
    (-0.056, -0.134), (-0.061, -0.138), (-0.103, -0.138), (-0.107, -0.132),
    (-0.081, -0.046), (-0.094, -0.031), (-0.105, -0.023), (-0.105, -0.013),
], FRAME_W)
guard = side_profile("guard_hole", [(-0.018, -0.030), (0.037, -0.030), (0.039, -0.050),
                                    (0.033, -0.0555), (-0.014, -0.0555), (-0.023, -0.046)], 0.05)
cut(frame, guard)
# Finger grooves on the front strap, subtle.
# Front strap runs from (-0.027, -0.054) to (-0.056, -0.134); groove centres sit just outside it.
groove = cyl_y("finger_groove", 0.0068, 0.06, (-0.0300, 0, -0.0745), verts=32)
linear_array(groove, 3, (-0.0071, 0, -0.0197))
cut(frame, groove)
finish(frame, M_FRAME, bevel=0.0012, segments=3)

# Accessory rail under the dust cover
rail = box("rail", (0.040, 0.019, 0.0045), (0.069, 0, -0.0292))
slot = box("rail_slot", (0.0026, 0.03, 0.003), (0.052, 0, -0.0315))
linear_array(slot, 7, (0.0052, 0, 0))
cut(rail, slot)
finish(rail, M_FRAME, bevel=0.0004)

# Magazine baseplate
finish(side_profile("mag_base", [(-0.058, -0.137), (-0.105, -0.137), (-0.108, -0.1465), (-0.055, -0.1465)], 0.027), M_STEEL, bevel=0.0008)

# Trigger
finish(side_profile("trigger", [(0.012, -0.029), (0.018, -0.029), (0.016, -0.040), (0.021, -0.051),
                                (0.015, -0.053), (0.008, -0.041)], 0.0055), M_STEEL, bevel=0.0005)

# Controls: slide stop (left side), magazine release buttons (both sides), safety
finish(box("slide_stop", (0.020, 0.0025, 0.0045), (-0.020, -FRAME_W / 2 - 0.0008, -0.0125)), M_STEEL, bevel=0.0005)
for sy in (-1, 1):
    finish(cyl_y(f"mag_release_{sy}", 0.0034, 0.0022, (-0.0215, sy * (FRAME_W / 2 + 0.0003), -0.036), verts=24), M_STEEL, bevel=0.0003)

# Fire-Control Link: readout window on the left side of the frame + palm contact pads
readout = box("fcl_readout", (0.022, 0.0012, 0.0055), (-0.050, -FRAME_W / 2 - 0.0004, -0.0175))
finish(readout, M_GLASS, bevel=0.0003)
for i, w in enumerate((0.004, 0.007, 0.0025, 0.005)):
    seg = box(f"fcl_seg{i}", (w, 0.0004, 0.0011), (-0.058 + i * 0.0052 + w / 2, -FRAME_W / 2 - 0.0011, -0.0168))
    finish(seg, M_AMBER, bevel=0)
seg = box("fcl_bar", (0.016, 0.0004, 0.0006), (-0.052, -FRAME_W / 2 - 0.0011, -0.0192))
finish(seg, M_AMBER, bevel=0)
for i in range(3):
    # Flush contact strips across the backstrap, 0.4 mm proud of the surface.
    t = 0.22 + i * 0.2
    pad = box(f"palm_pad{i}", (0.0012, 0.022, 0.006), (0, 0, 0))
    pad.location = (-0.081 + (-0.107 + 0.081) * t - 0.0002, 0, -0.046 + (-0.132 + 0.046) * t)
    pad.rotation_euler = (0, math.radians(16.8), 0)
    finish(pad, M_PAD, bevel=0.0003)

# Markings (fictional), left side of the slide
def text(name, body, size, loc):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = 0.00012
    cu.align_x = "LEFT"
    ob = link(bpy.data.objects.new(name, cu))
    ob.location = loc
    ob.rotation_euler = (math.pi / 2, 0, 0)
    ob.data.materials.append(M_MARK)
    PARTS.append(ob)
    return ob

text("mark_model", "SP-57  //  5.7x28", 0.0036, (-0.040, -SLIDE_HALF - 0.0001, -0.0055))

# ---------------------------------------------------------------- barrel + suppressor
finish(cyl_x("barrel", 0.0066, 0.080, 0.106, verts=32), M_STEEL, bevel=0.0003)

CAN_R = 0.0182
X_COLLAR0, X_COLLAR1 = 0.104, 0.126
X_TUBE1 = 0.262
X_CAP1 = 0.284

collar = cyl_x("can_collar", 0.0196, X_COLLAR0, X_COLLAR1, verts=6)
collar.rotation_euler = (math.radians(30), 0, 0)
finish(collar, M_CAN, bevel=0.0008, segments=2)

tube = cyl_x("can_tube", CAN_R, X_COLLAR1, X_TUBE1, verts=64)
flute = cyl_x("flute", 0.0028, 0.146, 0.236, verts=16, z=CAN_R + 0.0013)
radial_array(flute, 8, (0.146 + 0.236) / 2)
cut(tube, flute)
# Machined flat for the data plate on the left side
cut(tube, box("can_flat", (0.050, 0.006, 0.02), (0.186, -CAN_R - 0.0016, 0.0)))
# Ring grooves at the rear of the tube (heat-sink fins)
fin = cyl_x("fin_cut", CAN_R + 0.002, 0.130, 0.1315, verts=48)
fin_core = cyl_x("fin_core", CAN_R - 0.0011, 0.120, 0.145, verts=48)
fin_cut_obj = fin
linear_array(fin_cut_obj, 3, (0.0035, 0, 0))
b = fin_cut_obj.modifiers.new("hollow", "BOOLEAN")
b.operation = "DIFFERENCE"
b.solver = "EXACT"
b.object = cutter(fin_core)
cut(tube, fin_cut_obj)
finish(tube, M_CAN, bevel=0.0005)

# Heat band ring (thin, darker bronze-ish anodizing) just behind the cap
finish(cyl_x("can_band", CAN_R + 0.0003, 0.248, 0.252, verts=64), M_BAND, bevel=0.0002)

cap = cyl_x("can_cap", 0.0186, X_TUBE1, X_CAP1, verts=64)
cut(cap, cyl_x("bore", 0.0042, X_TUBE1 - 0.01, X_CAP1 + 0.01, verts=24))
notch = box("crown_notch", (0.006, 0.004, 0.012), (X_CAP1, 0, 0.016))
radial_array(notch, 6, X_CAP1)
cut(cap, notch)
finish(cap, M_CAN, bevel=0.0012, segments=3)

# Data plate on the suppressor flat
plate = box("can_plate", (0.042, 0.0008, 0.0085), (0.186, -CAN_R + 0.0013, 0.0))
finish(plate, M_SLIDE, bevel=0.0003)
text("mark_can", "SR-57S  SUPPRESSOR", 0.0024, (0.168, -CAN_R + 0.0008, -0.0009))
led = box("can_led", (0.0025, 0.0005, 0.0012), (0.2045, -CAN_R + 0.0007, 0.0024))
finish(led, M_AMBER, bevel=0)

# ---------------------------------------------------------------- export
weapon = bpy.data.objects.new("pistol_57", None)
link(weapon)
for ob in PARTS:
    ob.parent = weapon

if args.out:
    bpy.ops.object.select_all(action="DESELECT")
    weapon.select_set(True)
    for ob in PARTS:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=args.out, use_selection=True, export_apply=True)
    deps = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for ob in PARTS:
        if ob.type == "MESH":
            me = ob.evaluated_get(deps).to_mesh()
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
    print(f"pistol_57: exported {args.out} ({tris} triangles in {len(PARTS)} parts)")

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
    world.color = (0.012, 0.013, 0.015)
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.013, 0.015, 1)
    scene.world = world

    floor = link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0.09, 0, -0.175)
    floor.data.materials.append(material("floor", (0.008, 0.0085, 0.009), 0.22, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = color
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc
        d = Vector((0.09, 0, -0.05)) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return ob

    area("key", (-0.25, -0.55, 0.55), 9, 0.6)
    area("fill", (0.6, -0.6, -0.02), 1.6, 0.8, (0.75, 0.85, 1.0))
    area("rim", (0.25, 0.6, 0.4), 7, 0.5, (1.0, 0.82, 0.62))
    area("top", (0.1, 0.0, 0.7), 2.5, 1.0)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 70
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 8.0
    cam = link(bpy.data.objects.new("cam", cam_data))
    target = Vector((0.088, 0, -0.058))
    cam.location = target + Vector((0.06, -0.97, 0.24))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.dof.focus_distance = (target - cam.location).length
    scene.camera = cam
    bpy.ops.render.render(write_still=True)
    print(f"pistol_57: preview {args.preview}")
