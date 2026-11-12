"""First-person arms holding the RC-6 rail carbine: right hand on the pistol
grip, index finger on the trigger; left hand wrapped around the raked support
grip under the rail shroud (inside the front loop).

Built from raw_assets/characters/fp_arms_mg42/build.py (same gloves and hand
builder); only the support grip frame, the left wrist/elbow and the preview
cameras differ. The RC-6 pistol grip is the Pistol 57 / MG42 grip profile at
the same place, so the right hand is unchanged.

Same gloves, materials and construction as raw_assets/characters/fp_arms/build.py
(metaball fingers and palms, hard-surface armour plates, cuffs, sleeves; HIGH has
the orange piping as geometry, LOW gets it through the bake). The difference is
that every hand is posed around a `Grip` frame, so one hand builder works on any
grip: the MG42's pistol grip uses the Pistol 57 grip frame (same profile, same
place, see raw_assets/weapons/mg42/build.py), the foregrip is a near-vertical
cylinder.

Axes (same as the gun): +X = muzzle, +Z = up, -Y = the gun's RIGHT side.

Run:
  tools/blender.sh raw_assets/characters/fp_arms_rail/build.py \
      --out assets/characters/fp_arms_rail/fp_arms_rail.gltf --tex 2048 --preview docs/previews/fp_arms_rail.png
  Pose check only (no bake, fast): --pose /tmp/pose.png
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import bakeutil  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--preview", default="", help="first-person view of the hold")
ap.add_argument("--pose", default="", help="fast unbaked pose check (writes <stem>_fp/_side/_left/_under)")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--gun", default="assets/weapons/rail_carbine/rail_carbine.gltf")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection
V = Vector

HIGH = {"name": "high", "mb_res": 0.0008, "lines": True, "seg": 3, "cyl": 48}
LOW = {"name": "low", "mb_res": 0.0032, "lines": False, "seg": 1, "cyl": 20}
D = HIGH
PARTS = []


class Grip:
    """A grip as an elliptical cylinder: `top` centre, `axis` down the grip,
    `fwd` toward the front strap, `right` toward the gun's right side."""

    def __init__(self, top, axis, half_depth, half_width, right=V((0.0, -1.0, 0.0))):
        self.top = V(top)
        self.axis = V(axis).normalized()
        self.right = right
        self.fwd = V((-self.axis.z, 0.0, self.axis.x))
        self.hd, self.hw = half_depth, half_width

    def at(self, h, theta_deg, extra):
        """Point at height h down the grip, angle theta (0 = front, +90 = right,
        180 = back, -90 = left), `extra` metres off the surface."""
        t = math.radians(theta_deg)
        return (self.top + self.axis * h + self.fwd * ((self.hd + extra) * math.cos(t))
                + self.right * ((self.hw + extra) * math.sin(t)))

    def out(self, theta_deg):
        t = math.radians(theta_deg)
        return (self.fwd * math.cos(t) + self.right * math.sin(t)).normalized()


# The Pistol 57 grip frame (the MG42 pistol grip is built on the same profile).
PISTOL_GRIP = Grip((-0.054, 0.0, -0.050), (-0.029, 0.0, -0.080), 0.0255, 0.0155)
# RC-6 support grip: raked loft from (0.168, 0, -0.036) along (0.022, 0, -0.094); the hand starts
# 12 mm down (below the mount block). Section about 33.6 x 31.6 mm.
_FORE_AXIS = V((0.022, 0.0, -0.094)).normalized()
FORE_GRIP = Grip(V((0.168, 0.0, -0.036)) + _FORE_AXIS * 0.012, _FORE_AXIS, 0.0168, 0.0158)


# ---------------------------------------------------------------- materials (as fp_arms)
def material(name, base, rough, metal=0.0, coat=0.0, bump=0.0, bump_scale=600.0, emission=None):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.25
    if bump > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 6.0
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.0003
        nt.links.new(tex.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return mat


M_GLOVE = material("glove_polymer", (0.022, 0.024, 0.027), 0.34, coat=0.35, bump=0.04, bump_scale=900)
M_PLATE = material("glove_plate", (0.045, 0.047, 0.05), 0.42, metal=0.25, bump=0.03)
M_LINE = material("glove_piping", (1.0, 0.56, 0.24), 0.35, emission=((1.0, 0.5, 0.18), 1.2))
M_CUFF = material("glove_cuff", (0.03, 0.032, 0.035), 0.5, bump=0.08, bump_scale=500)
M_SLEEVE = material("sleeve_fabric", (0.045, 0.05, 0.04), 0.88, bump=0.35, bump_scale=350)
MATERIALS = [M_GLOVE, M_PLATE, M_LINE, M_CUFF, M_SLEEVE]


# ---------------------------------------------------------------- builders (as fp_arms, grip-relative)
def link(ob):
    col.objects.link(ob)
    return ob


def metaball(name):
    mb = bpy.data.metaballs.new(name)
    mb.resolution = D["mb_res"]
    mb.render_resolution = D["mb_res"]
    mb.threshold = 0.6
    ob = link(bpy.data.objects.new(name, mb))
    ob.data.materials.append(M_GLOVE)
    PARTS.append(ob)
    return mb


MB_SCALE = 1.0 / 0.52


def capsule(mb, p0, p1, r):
    e = mb.elements.new(type="CAPSULE")
    d = p1 - p0
    e.co = (p0 + p1) / 2
    e.radius = r * MB_SCALE
    e.size_x = max(d.length / 2 - r * 0.35, 0.0005)
    e.rotation = V((1, 0, 0)).rotation_difference(d.normalized())


def palm_shell(name, g, h0, h1, t0, t1, extra, thickness, bulge=0.004, nu=10, nv=8):
    bm = bmesh.new()
    grid = []
    for i in range(nu + 1):
        row = []
        for j in range(nv + 1):
            fu, fv = i / nu, j / nv
            mid = math.sin(math.pi * fu) * math.sin(math.pi * fv)
            row.append(bm.verts.new(g.at(h0 + (h1 - h0) * fu, t0 + (t1 - t0) * fv, extra + bulge * mid)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    centre = g.at((h0 + h1) / 2, (t0 + t1) / 2, extra)
    poly = me.polygons[len(me.polygons) // 2]
    if poly.normal.dot(centre - g.top - g.axis * ((h0 + h1) / 2)) < 0:
        for poly in me.polygons:
            poly.flip()
    sol = ob.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = -1.0
    sol.use_even_offset = True
    sub = ob.modifiers.new("smooth", "SUBSURF")
    sub.levels = 2 if D is HIGH else 1
    sub.render_levels = sub.levels
    ob.data.shade_smooth()
    ob.data.materials.append(M_GLOVE)
    PARTS.append(ob)
    return ob


def finger(family, joints, radii):
    mb = metaball(family)
    for i in range(len(joints) - 1):
        capsule(mb, joints[i], joints[i + 1], radii[min(i, len(radii) - 1)])
    return joints


def piping(name, pts, radius=0.00055, cyclic=False):
    if not D["lines"]:
        return
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_cyclic_u = cyclic
    ob = link(bpy.data.objects.new(name, cu))
    ob.data.materials.append(M_LINE)
    PARTS.append(ob)


def seam(joints, radii, up, out):
    pts = []
    for j, p in enumerate(joints):
        r = radii[min(j, len(radii) - 1)]
        u = up(j) if callable(up) else up
        o = out(j) if callable(out) else out
        pts.append(p + (u * 0.22 + o * 1.0).normalized() * (r * 0.99))
    return pts


def rounded_plate(name, center, u, v, n, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    m = Matrix((u, v, n)).transposed().to_4x4()
    m.translation = center
    ob.matrix_world = m
    b = ob.modifiers.new("bevel", "BEVEL")
    b.width = min(size[2] * 0.45, 0.0018)
    b.segments = max(1, D["seg"])
    ob.modifiers.new("smooth", "SUBSURF").levels = 1 if D is HIGH else 0
    ob.data.shade_smooth()
    ob.data.materials.append(mat)
    PARTS.append(ob)
    return ob


def plate_outline(center, u, v, n, size, inset=0.0012):
    hu, hv, ht = size[0] / 2 - inset, size[1] / 2 - inset, size[2] / 2 + 0.0002
    c = center + n * ht
    piping("plate_outline", [c + u * hu + v * hv, c - u * hu + v * hv, c - u * hu - v * hv, c + u * hu - v * hv],
           radius=0.00045, cyclic=True)


def finger_guard(name, joints, radii, normal):
    p0, p1 = joints[0], joints[1]
    u = (p1 - p0).normalized()
    n = normal - u * normal.dot(u)
    n.normalize()
    v = n.cross(u)
    r = radii[0]
    length = (p1 - p0).length
    centre = p0 + (p1 - p0) * 0.55 + n * (r * 0.93)
    size = (length * 0.62, r * 1.25, 0.0026)
    rounded_plate(name, centre, u, v, n, size, M_PLATE)
    plate_outline(centre, u, v, n, size, inset=0.0009)


def tube(name, p0, p1, r0, r1, mat, verts=None):
    d = p1 - p0
    bpy.ops.mesh.primitive_cone_add(vertices=verts or D["cyl"], radius1=r0, radius2=r1, depth=d.length,
                                    location=(p0 + p1) / 2)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = V((0, 0, 1)).rotation_difference(d.normalized())
    b = ob.modifiers.new("bevel", "BEVEL")
    b.width = 0.002
    b.segments = max(1, D["seg"])
    ob.data.shade_smooth()
    ob.data.materials.append(mat)
    PARTS.append(ob)
    return ob


def ring_points(p, axis, r, n=48):
    axis = axis.normalized()
    a = axis.orthogonal().normalized()
    b = axis.cross(a)
    return [p + (a * math.cos(2 * math.pi * i / n) + b * math.sin(2 * math.pi * i / n)) * r for i in range(n)]


def arm(side, wrist, elbow, hand_join):
    d = (elbow - wrist).normalized()
    cuff_end = wrist + d * 0.055
    tube(f"{side}_cuff", wrist - d * 0.004, cuff_end, 0.0292, 0.0322, M_CUFF)
    piping(f"{side}_cuff_ring", ring_points(wrist + d * 0.008, d, 0.0298), radius=0.0006, cyclic=True)
    tube(f"{side}_sleeve", cuff_end - d * 0.006, elbow, 0.0355, 0.047, M_SLEEVE)
    mb = metaball(f"{side}Wrist")
    capsule(mb, hand_join, wrist + d * 0.012, 0.0215)


def back_plate(name, g, h, theta, extra):
    bn = g.out(theta)
    bu = g.axis - bn * g.axis.dot(bn)
    bu.normalize()
    bv = bn.cross(bu)
    c = g.at(h, theta, extra)
    rounded_plate(name, c, bu, bv, bn, (0.046, 0.02, 0.003), M_PLATE)
    plate_outline(c, bu, bv, bn, (0.046, 0.02, 0.003))


def wrap_fingers(prefix, g, spec, extra_base=0.0):
    """Fingers wrapped around grip g: spec = {name: (h, radii, thetas)}."""
    for name, (h, radii, thetas) in spec.items():
        joints = [g.at(h, t, extra_base + radii[0]) for t in thetas]
        finger(f"{prefix}_{name}", joints, radii)
        finger_guard(f"{prefix}_{name}_guard", joints, radii, g.out((thetas[0] + thetas[1]) / 2))
        piping(f"{prefix}_{name}_seam", seam(joints, radii, -g.axis, lambda j, t=thetas: g.out(t[j]))[1:])


# ---------------------------------------------------------------- the pose
def build_hands():
    # ---- Firing (right) hand on the pistol grip: the Pistol 57 hold, thumb down the grip's left side
    # (the receiver sits where the pistol's thumb rested along the frame).
    g = PISTOL_GRIP
    wrap_fingers("R", g, {
        "middle": (0.031, (0.0094, 0.0089, 0.0082), (114, 40, -36, -82)),
        "ring": (0.050, (0.0090, 0.0085, 0.0078), (112, 40, -34, -78)),
        "pinky": (0.068, (0.0080, 0.0075, 0.0069), (108, 42, -28, -68)),
    })
    idx = [V((-0.054, -0.0265, -0.043)), V((-0.016, -0.0255, -0.043)), V((0.001, -0.0145, -0.045)),
           V((0.004, -0.0015, -0.047))]
    idx_r = (0.0088, 0.0082, 0.0076)
    finger("R_index", idx, idx_r)
    finger_guard("R_index_guard", idx, idx_r, (g.right + V((0, 0, 0.6))).normalized())
    piping("R_index_seam", seam(idx, idx_r, V((0, 0, 1)), (g.right + V((0, 0, 0.6))).normalized())[1:])
    r_thumb = [g.at(0.016, 172, 0.012), g.at(0.005, -140, 0.0112), V((-0.058, 0.0255, -0.0445)),
               V((-0.033, 0.0255, -0.0465))]
    r_thumb_r = (0.0115, 0.0102, 0.0094)
    finger("R_thumb", r_thumb, r_thumb_r)
    piping("R_thumb_seam", seam(r_thumb[1:], r_thumb_r[1:], V((0, 0, 1)), V((0, 1, 0))))
    palm_shell("R_palm", g, -0.004, 0.084, 104, 192, 0.018, 0.016)
    arm("R", V((-0.127, -0.033, -0.097)), V((-0.42, -0.21, -0.27)), g.at(0.05, 160, 0.02))
    back_plate("R_back_plate", g, 0.04, 150, 0.0228)

    # ---- Support (left) hand around the foregrip: the firing hand mirrored, fingers wrapping from
    # the left side round the front to the right, thumb round the back.
    f = FORE_GRIP
    wrap_fingers("L", f, {
        "index": (0.012, (0.0090, 0.0085, 0.0078), (-112, -40, 36, 84)),
        "middle": (0.031, (0.0094, 0.0089, 0.0082), (-114, -40, 36, 82)),
        "ring": (0.050, (0.0090, 0.0085, 0.0078), (-112, -40, 34, 78)),
        "pinky": (0.068, (0.0080, 0.0075, 0.0069), (-108, -42, 28, 68)),
    })
    l_thumb = [f.at(0.020, -168, 0.013), f.at(0.002, 172, 0.0112), f.at(-0.001, 130, 0.0102),
               f.at(0.003, 98, 0.0098)]
    l_thumb_r = (0.0118, 0.0104, 0.0094)
    finger("L_thumb", l_thumb, l_thumb_r)
    piping("L_thumb_seam", seam(l_thumb[1:], l_thumb_r[1:], V((0, 0, 1)), V((-1, 0, 0))))
    palm_shell("L_palm", f, -0.004, 0.082, -104, -192, 0.018, 0.016)
    thenar = metaball("L_thenar")
    capsule(thenar, f.at(0.03, -140, 0.022), l_thumb[0], 0.0125)
    # Wrist further left than on the MG42 so it clears the front loop below the hand.
    l_wrist = f.top + V((-0.064, 0.046, -0.070))
    arm("L", l_wrist, V((-0.09, 0.23, -0.30)), f.at(0.055, -160, 0.02))
    back_plate("L_back_plate", f, 0.04, -150, 0.0228)


def build(detail):
    global D
    D = detail
    PARTS.clear()
    build_hands()
    bpy.ops.object.select_all(action="DESELECT")
    for ob in PARTS:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.convert(target="MESH")
    meshes = [ob for ob in bpy.context.selected_objects if ob.type == "MESH" and len(ob.data.polygons) > 0]
    for ob in list(bpy.context.selected_objects):
        if ob not in meshes:
            bpy.data.objects.remove(ob)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = "fp_arms_rail" if detail is LOW else "fp_arms_rail_high"
    joined.data.shade_smooth()
    if detail is LOW:
        dec = joined.modifiers.new("decimate", "DECIMATE")
        dec.ratio = 0.55
        bpy.ops.object.modifier_apply(modifier="decimate")
    return joined


# ---------------------------------------------------------------- rendering
def setup_render(samples, res):
    w, h = (int(x) for x in res.split("x"))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("studio")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.032, 0.036, 1)
    scene.world = world

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.0, 0, -0.06)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.30, -0.55, 0.7), 25, 0.9)
    area("fill", (-0.5, 0.6, 0.2), 8, 1.0, (0.75, 0.85, 1.0))
    area("rim", (0.6, 0.3, 0.45), 14, 0.6, (1.0, 0.82, 0.62))
    area("under", (0.1, -0.2, -0.5), 3, 0.8, (0.9, 0.9, 1.0))
    cam_data = bpy.data.cameras.new("cam")
    cam = link(bpy.data.objects.new("cam", cam_data))
    scene.camera = cam
    return cam


def shoot(cam, path, loc, target, fov_deg=None, lens=None):
    data = cam.data
    if fov_deg:
        data.sensor_fit = "VERTICAL"
        data.angle = math.radians(fov_deg)
    if lens:
        data.sensor_fit = "AUTO"
        data.lens = lens
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    data.clip_start = 0.01
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"fp_arms_rail: rendered {path}")


# The in-game hip hold (data/player/viewmodel_rail.tres), in Blender axes (glTF z = -Blender y).
FP_CAM = ((-0.30, 0.12, 0.17), (0.7, 0.03, 0.02))
SIDE_CAM = ((0.0, -1.1, -0.06), (0.0, 0.0, -0.06))
LEFT_CAM = ((0.05, 0.9, -0.02), (0.05, 0.0, -0.07))
UNDER_CAM = ((0.15, -0.45, -0.40), (0.05, 0.0, -0.07))


def import_gun():
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is not None:
        bpy.data.node_groups.remove(group)
    bpy.ops.import_scene.gltf(filepath=args.gun)


if args.pose:
    build(HIGH)
    import_gun()
    cam = setup_render(16, "960x540")
    stem = args.pose.rsplit(".", 1)[0]
    shoot(cam, stem + "_fp.png", FP_CAM[0], FP_CAM[1], fov_deg=60)
    shoot(cam, stem + "_side.png", SIDE_CAM[0], SIDE_CAM[1], lens=40)
    shoot(cam, stem + "_left.png", LEFT_CAM[0], LEFT_CAM[1], lens=40)
    shoot(cam, stem + "_under.png", UNDER_CAM[0], UNDER_CAM[1], lens=40)
elif args.out:
    high = build(HIGH)
    low = build(LOW)
    print(f"fp_arms_rail: high {bakeutil.tri_count(high)} tris, low {bakeutil.tri_count(low)} tris")
    bakeutil.unwrap(low, boost={M_PLATE.name: 1.6, M_GLOVE.name: 1.3})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "fp_arms_rail", cage=0.0015, ray=0.005,
                                 log=print)
    bpy.data.objects.remove(high)
    bakeutil.apply_baked_material(low, tex, "fp_arms_rail", emission_strength=1.5)
    bakeutil.export_gltf(low, args.out)
    print(f"fp_arms_rail: exported {args.out} ({bakeutil.tri_count(low)} tris)")
    if args.preview:
        import_gun()
        cam = setup_render(args.samples, args.res)
        shoot(cam, args.preview, FP_CAM[0], FP_CAM[1], fov_deg=60)
