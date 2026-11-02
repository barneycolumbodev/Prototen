"""Shared hard-surface modelling helpers for weapon generator scripts (CLAUDE.md §7).

Used by raw_assets/weapons/pistol_57/build.py and mg42/build.py. Conventions:
+X = muzzle, +Z = up, -Y = the gun's RIGHT side, metres. Build at a detail level
(HIGH/LOW dicts), call `finish()` on every part, then `join_parts()` to apply
modifiers and get one mesh.

Note: box/cyl helpers bake their location into the mesh (object origin at the
world origin). To rotate a part about its own centre, build it at (0, 0, 0),
then set `location` and `rotation_euler`.

    import hardsurface as hs
    hs.set_detail(hs.HIGH)
    hs.finish(hs.box("plate", (0.1, 0.01, 0.02), (0, 0, 0)), mat)
    gun = hs.join_parts("gun_high")
"""
import math

import bpy
import bmesh
from mathutils import Matrix, Vector

HIGH = {"name": "high", "seg": 3, "cyl": 1.0, "text": True}
LOW = {"name": "low", "seg": 1, "cyl": 0.5, "text": False}
D = HIGH
PARTS = []
HELPERS = []


def set_detail(detail):
    global D
    D = detail
    PARTS.clear()


def col():
    return bpy.context.scene.collection


def link(ob):
    col().objects.link(ob)
    return ob


def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def prism(name, pts, vec):
    """Polygon `pts` (3D) extruded by `vec` into a closed solid."""
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new(p) for p in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=vec)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


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


def cyl_x(name, radius, x0, x1, verts=48, z=0.0, y=0.0, fixed=False, radius2=None):
    """Cylinder (or cone, with radius2 at x1) along X from x0 to x1."""
    n = verts if fixed else nverts(verts)
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=radius, depth=x1 - x0,
                                            location=((x0 + x1) / 2, y, z), rotation=(0, math.pi / 2, 0))
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=radius, radius2=radius2, depth=x1 - x0,
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


def cyl_z(name, radius, depth, loc, verts=32, radius2=None):
    """Cylinder (or cone, radius2 at the bottom) along Z."""
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=nverts(verts), radius=radius, depth=depth, location=loc)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=nverts(verts), radius1=radius2, radius2=radius, depth=depth,
                                        location=loc)
    ob = bpy.context.active_object
    ob.name = name
    return ob


def cyl_between(name, p0, p1, radius, verts=16, radius2=None):
    """Cylinder/cone from p0 to p1 (any direction)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=nverts(verts), radius=radius, depth=d.length,
                                            location=(p0 + p1) / 2)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=nverts(verts), radius1=radius, radius2=radius2,
                                        depth=d.length, location=(p0 + p1) / 2)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def lathe_x(name, profile, verts=48):
    """Surface of revolution around the X axis. profile: [(x, r), ...] from back to front."""
    n = nverts(verts)
    bm = bmesh.new()
    rings = []
    for x, r in profile:
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ring.append(bm.verts.new((x, r * math.cos(a), r * math.sin(a))))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


def cutter(ob):
    ob.display_type = "WIRE"
    ob.hide_render = True
    if ob not in HELPERS:
        HELPERS.append(ob)
    return ob


def cut(target, tool, operation="DIFFERENCE"):
    cutter(tool)
    m = target.modifiers.new(f"cut_{tool.name}", "BOOLEAN")
    m.operation = operation
    m.solver = "EXACT"
    m.object = tool
    return m


def finish(ob, mat, bevel=0.0006, segments=3, angle=35.0, smooth=True):
    """Bevel + weighted normals for clean hard-surface shading."""
    if bevel > 0:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = max(1, min(segments, D["seg"]))
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(angle)
        b.harden_normals = True
    if smooth and ob.type == "MESH":
        ob.data.shade_smooth()
        w = ob.modifiers.new("wnormal", "WEIGHTED_NORMAL")
        w.keep_sharp = True
    ob.data.materials.append(mat)
    PARTS.append(ob)
    return ob


def radial_array(ob, count, center_x, center=(0.0, 0.0)):
    """Repeat `ob` around the X axis through (center_x, center)."""
    c = Vector((center_x, center[0], center[1]))
    offset = ob.location - c
    ob.data.transform(Matrix.Translation(offset))
    ob.location = c
    pivot = link(bpy.data.objects.new(ob.name + "_pivot", None))
    HELPERS.append(pivot)
    pivot.location = c
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
    return a


def mirror_y(ob):
    m = ob.modifiers.new("mirror", "MIRROR")
    m.use_axis = (False, True, False)
    return m


def text(name, body, size, loc, rot, mat, extrude=0.00012):
    """Raised lettering (HIGH only; LOW gets it through the bake)."""
    if not D["text"]:
        return None
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 4
    ob = link(bpy.data.objects.new(name, cu))
    ob.location = loc
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    PARTS.append(ob)
    return ob


def join_parts(name):
    """Applies every modifier, converts text, joins PARTS into one mesh and removes helpers."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in PARTS:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    for ob in HELPERS:
        bpy.data.objects.remove(ob)
    HELPERS.clear()
    PARTS.clear()
    return joined


# ---------------------------------------------------------------- procedural materials
def material(name, base, rough, metal, wear=None, wear_rough=0.25, bump_scale=0.0, bump_strength=0.0,
             emission=None, brushed=0.0, coat=0.0):
    """Principled material with optional edge wear (pointiness), brushed
    streaks along X (roughness variation) and fine bump noise."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.08
    rough_socket = None
    if wear:
        geo = N.new("ShaderNodeNewGeometry")
        ramp = N.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.52
        ramp.color_ramp.elements[1].position = 0.6
        noise = N.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 300.0
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
        rmix.inputs["To Max"].default_value = wear_rough
        L.new(mult.outputs[0], rmix.inputs["Value"])
        rough_socket = rmix.outputs["Result"]
    if brushed > 0:
        tc = N.new("ShaderNodeTexCoord")
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.015, 1.0, 1.0)
        streak = N.new("ShaderNodeTexNoise")
        streak.inputs["Scale"].default_value = 700.0
        streak.inputs["Detail"].default_value = 3.0
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        L.new(mp.outputs["Vector"], streak.inputs["Vector"])
        add = N.new("ShaderNodeMath")
        add.operation = "MULTIPLY_ADD"
        add.inputs[1].default_value = brushed * 2.0
        add.inputs[2].default_value = -brushed
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
    if bump_strength > 0:
        tex = N.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 4.0
        bump = N.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.0002
        L.new(tex.outputs["Fac"], bump.inputs["Height"])
        L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


def loft(name, stations, n=None, power=2.5, cap=True):
    """Closed loft through superellipse sections. Each station is
    (centre, u, v, a, b): centre point, two unit axes of the section plane and
    the half sizes along them. power 2 = ellipse, higher = boxier."""
    n = n or nverts(40)
    bm = bmesh.new()
    rings = []
    for centre, u, v, a, b in stations:
        centre, u, v = Vector(centre), Vector(u), Vector(v)
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            c, s = math.cos(t), math.sin(t)
            cu = math.copysign(abs(c) ** (2 / power), c)
            sv = math.copysign(abs(s) ** (2 / power), s)
            ring.append(bm.verts.new(centre + u * (a * cu) + v * (b * sv)))
        rings.append(ring)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


def loft_x(name, stations, n=None, power=5.0):
    """Loft along X through rounded-rectangle sections: (x, top z, bottom z, half width)."""
    return loft(name, [((x, 0.0, (zt + zb) / 2), (0, 1, 0), (0, 0, 1), hw, (zt - zb) / 2)
                       for x, zt, zb, hw in stations], n=n, power=power)


def tube_path(name, pts, radius, width_scale=1.0, resolution=6):
    """Round tube along a smooth path (bezier through pts), optionally squashed across Y."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3 if D["seg"] > 1 else 1
    cu.resolution_u = resolution if D["seg"] > 1 else 3
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = link(bpy.data.objects.new(name, cu))
    ob.scale = (1.0, width_scale, 1.0)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.transform_apply(scale=True)
    return bpy.context.active_object
