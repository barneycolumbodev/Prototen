"""First-person arms: tactical smooth-polymer gloves with light-orange piping,
holding Pistol 57 in a two-handed, thumbs-forward aiming grip.

The pose is computed around the pistol's real grip geometry (see
raw_assets/weapons/pistol_57/build.py), in the same space as the gun, so in
the game the arms and the gun share one viewmodel transform.

Hands are metaball capsules (one family per finger, so fingers blend at their
own joints but never web together) plus a metaball palm; knuckle armour plates,
cuffs and sleeves are hard-surface meshes. HIGH carries the orange piping as
real geometry; LOW (game mesh) gets it through the bake.

Axes (same as the gun): +X = muzzle, +Z = up, -Y = the gun's RIGHT side.

Run:
  tools/blender.sh raw_assets/characters/fp_arms/build.py --out assets/characters/fp_arms/fp_arms.gltf \
      --tex 2048 --preview docs/previews/fp_arms_aim.png --beauty docs/previews/fp_arms_beauty.png
  Pose check only (no bake, fast): --pose /tmp/pose.png
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import bakeutil  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--preview", default="", help="first-person aiming shot (60 deg vertical FOV, like the game)")
ap.add_argument("--beauty", default="", help="three-quarter shot of the grip")
ap.add_argument("--pose", default="", help="fast unbaked pose check (writes <name>_aim/_side/_front)")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--gun", default="assets/weapons/pistol_57/pistol_57.gltf")
ap.add_argument("--render-only", default="", help="skip building: import this exported arms .gltf and render")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection
V = Vector

HIGH = {"name": "high", "mb_res": 0.0008, "lines": True, "seg": 3, "cyl": 48}
LOW = {"name": "low", "mb_res": 0.0032, "lines": False, "seg": 1, "cyl": 20}
D = HIGH
PARTS = []

# ---------------------------------------------------------------- grip frame (from the pistol's frame profile)
GRIP_TOP = V((-0.054, 0.0, -0.050))            # centre of the grip just under the slide
AXIS = V((-0.029, 0.0, -0.080)).normalized()   # down the grip (front strap angle)
FWD = V((-AXIS.z, 0.0, AXIS.x))                # toward the front strap, perpendicular to AXIS
RIGHT = V((0.0, -1.0, 0.0))                    # the gun's right side
HALF_DEPTH, HALF_WIDTH = 0.0255, 0.0155        # grip cross-section half sizes


def grip(h, theta_deg, extra):
    """Point around the grip at height h (m, down the grip), angle theta
    (0 = front strap, +90 = right side, 180 = backstrap, -90 = left side),
    `extra` metres off the grip surface."""
    t = math.radians(theta_deg)
    return GRIP_TOP + AXIS * h + FWD * ((HALF_DEPTH + extra) * math.cos(t)) + RIGHT * ((HALF_WIDTH + extra) * math.sin(t))


def outward(theta_deg):
    t = math.radians(theta_deg)
    return (FWD * math.cos(t) + RIGHT * math.sin(t)).normalized()


# ---------------------------------------------------------------- materials (procedural, HIGH)
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


# ---------------------------------------------------------------- builders
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


MB_SCALE = 1.0 / 0.52   # metaball radius for a wanted surface radius (calibrated, stiffness 2)


def capsule(mb, p0, p1, r):
    e = mb.elements.new(type="CAPSULE")
    d = p1 - p0
    e.co = (p0 + p1) / 2
    e.radius = r * MB_SCALE
    e.size_x = max(d.length / 2 - r * 0.35, 0.0005)
    e.rotation = V((1, 0, 0)).rotation_difference(d.normalized())


def ball(mb, p, r):
    e = mb.elements.new(type="BALL")
    e.co = p
    e.radius = r * MB_SCALE


def palm_shell(name, h0, h1, t0, t1, extra, thickness, bulge=0.004, nu=10, nv=8):
    """Curved palm: a sheet wrapped around the grip between heights h0..h1 and
    angles t0..t1, `extra` off the grip, solidified inward and subdivided."""
    import bmesh
    bm = bmesh.new()
    grid = []
    for i in range(nu + 1):
        row = []
        for j in range(nv + 1):
            fu, fv = i / nu, j / nv
            h = h0 + (h1 - h0) * fu
            t = t0 + (t1 - t0) * fv
            # Thicker in the middle of the palm, thinner at the edges.
            mid = math.sin(math.pi * fu) * math.sin(math.pi * fv)
            row.append(bm.verts.new(grip(h, t, extra + bulge * mid)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    # Make the sheet face outward (away from the grip) before solidifying inward.
    centre = grip((h0 + h1) / 2, (t0 + t1) / 2, extra)
    poly = me.polygons[len(me.polygons) // 2]
    if poly.normal.dot(centre - GRIP_TOP - AXIS * ((h0 + h1) / 2)) < 0:
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
    """Orange piping line (HIGH only): a thin tube along pts."""
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
    """Piping along the upper-outer side of a finger."""
    pts = []
    for j, p in enumerate(joints):
        r = radii[min(j, len(radii) - 1)]
        u = up(j) if callable(up) else up
        o = out(j) if callable(out) else out
        pts.append(p + (u * 0.22 + o * 1.0).normalized() * (r * 0.99))
    return pts


def rounded_plate(name, center, u, v, n, size, mat):
    """Bevelled armour plate: size = (along u, along v, thickness along n)."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    from mathutils import Matrix
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
    """Small armour guard on the back of a finger's first segment, with a piping edge."""
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
    """Tapered cylinder from p0 (radius r0) to p1 (radius r1)."""
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
    """Glove cuff (with piping ring) and sleeve from the wrist toward the elbow."""
    d = (elbow - wrist).normalized()
    cuff_end = wrist + d * 0.055
    tube(f"{side}_cuff", wrist - d * 0.004, cuff_end, 0.0292, 0.0322, M_CUFF)
    piping(f"{side}_cuff_ring", ring_points(wrist + d * 0.008, d, 0.0298), radius=0.0006, cyclic=True)
    tube(f"{side}_sleeve", cuff_end - d * 0.006, elbow, 0.0355, 0.047, M_SLEEVE)
    # Bridge from the palm into the cuff.
    mb = metaball(f"{side}Wrist")
    capsule(mb, hand_join, wrist + d * 0.012, 0.0215)


# ---------------------------------------------------------------- the pose
def build_hands():
    # ---- Firing (right) hand: palm on the right side and backstrap, index on the trigger.
    r_fingers = {
        "middle": (0.031, (0.0094, 0.0089, 0.0082), (114, 40, -36, -82)),
        "ring": (0.050, (0.0090, 0.0085, 0.0078), (112, 40, -34, -78)),
        "pinky": (0.068, (0.0080, 0.0075, 0.0069), (108, 42, -28, -68)),
    }
    r_mcps = []
    for name, (h, radii, thetas) in r_fingers.items():
        joints = [grip(h, t, radii[0]) for t in thetas]
        finger(f"R_{name}", joints, radii)
        finger_guard(f"R_{name}_guard", joints, radii, outward((thetas[0] + thetas[1]) / 2))
        r_mcps.append(joints[0])
        piping(f"R_{name}_seam", seam(joints, radii, -AXIS, lambda j, t=thetas: outward(t[j]))[1:])
    idx = [V((-0.054, -0.0265, -0.043)), V((-0.016, -0.0255, -0.043)), V((0.001, -0.0145, -0.045)),
           V((0.004, -0.0015, -0.047))]
    idx_r = (0.0088, 0.0082, 0.0076)
    finger("R_index", idx, idx_r)
    finger_guard("R_index_guard", idx, idx_r, (RIGHT + V((0, 0, 0.6))).normalized())
    piping("R_index_seam", seam(idx, idx_r, V((0, 0, 1)), (RIGHT + V((0, 0, 0.6))).normalized())[1:])
    r_mcps.insert(0, idx[0])
    # Thumb: from the web on the backstrap, across the top of the grip, forward along the left side.
    r_thumb = [grip(0.014, 172, 0.012), grip(-0.010, -150, 0.011), V((-0.056, 0.0262, -0.0215)),
               V((-0.031, 0.0262, -0.0195))]
    r_thumb_r = (0.0115, 0.0102, 0.0094)
    finger("R_thumb", r_thumb, r_thumb_r)
    piping("R_thumb_seam", seam(r_thumb[1:], r_thumb_r[1:], V((0, 0, 1)), V((0, 1, 0))))

    palm_shell("R_palm", -0.004, 0.084, 104, 192, 0.018, 0.016)
    r_wrist = V((-0.127, -0.033, -0.097))
    arm("R", r_wrist, V((-0.44, -0.20, -0.25)), grip(0.05, 160, 0.02))

    # Back-of-hand plate on the palm shell.
    bn = outward(150)
    bu = AXIS - bn * AXIS.dot(bn)
    bu.normalize()
    bv = bn.cross(bu)
    back_c = grip(0.04, 150, 0.0228)
    rounded_plate("R_back_plate", back_c, bu, bv, bn, (0.046, 0.02, 0.003), M_PLATE)
    plate_outline(back_c, bu, bv, bn, (0.046, 0.02, 0.003))

    # ---- Support (left) hand: fingers over the firing fingers, thumb forward under the firing thumb.
    l_fingers = {
        "index": (0.022, (0.0088, 0.0083, 0.0077), (-114, -42, 34, 80)),
        "middle": (0.040, (0.0092, 0.0087, 0.008), (-114, -42, 34, 80)),
        "ring": (0.058, (0.0088, 0.0083, 0.0076), (-112, -42, 32, 76)),
        "pinky": (0.075, (0.0078, 0.0073, 0.0067), (-108, -42, 28, 66)),
    }
    l_mcps = []
    for name, (h, radii, thetas) in l_fingers.items():
        extra = 0.0158 + radii[0]
        joints = [grip(h, t, extra) for t in thetas]
        finger(f"L_{name}", joints, radii)
        finger_guard(f"L_{name}_guard", joints, radii, outward((thetas[0] + thetas[1]) / 2))
        l_mcps.append(joints[0])
        piping(f"L_{name}_seam", seam(joints, radii, -AXIS, lambda j, t=thetas: outward(t[j]))[1:])
    l_thumb = [V((-0.080, 0.050, -0.076)), V((-0.052, 0.040, -0.052)), V((-0.020, 0.0285, -0.0405)),
               V((0.012, 0.0265, -0.037))]
    l_thumb_r = (0.0118, 0.0102, 0.0094)
    finger("L_thumb", l_thumb, l_thumb_r)
    piping("L_thumb_seam", seam(l_thumb[1:], l_thumb_r[1:], V((0, 0, 1)), V((0, 1, 0))))

    palm_shell("L_palm", 0.006, 0.090, -108, -178, 0.034, 0.016)
    lthenar = metaball("L_thenar")
    capsule(lthenar, grip(0.030, -120, 0.032), l_thumb[0], 0.013)
    l_wrist = V((-0.118, 0.064, -0.118))
    arm("L", l_wrist, V((-0.44, 0.21, -0.28)), grip(0.06, -150, 0.035))
    bn = outward(-145)
    bu = AXIS - bn * AXIS.dot(bn)
    bu.normalize()
    bv = bn.cross(bu)
    back_c = grip(0.048, -145, 0.0385)
    rounded_plate("L_back_plate", back_c, bu, bv, bn, (0.046, 0.02, 0.003), M_PLATE)
    plate_outline(back_c, bu, bv, bn, (0.046, 0.02, 0.003))



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
    # Converting a metaball family leaves the other family members as empty objects.
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
    joined.name = "fp_arms" if detail is LOW else "fp_arms_high"
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
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.016, 0.017, 0.02, 1)
    scene.world = world

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(-0.03, 0, -0.06)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.30, -0.45, 0.55), 10, 0.7)
    area("fill", (-0.5, 0.45, 0.1), 2.5, 0.9, (0.75, 0.85, 1.0))
    area("rim", (0.35, 0.3, 0.35), 6, 0.5, (1.0, 0.82, 0.62))
    area("under", (0.1, -0.2, -0.45), 1.2, 0.8, (0.9, 0.9, 1.0))
    cam_data = bpy.data.cameras.new("cam")
    cam = link(bpy.data.objects.new("cam", cam_data))
    scene.camera = cam
    return cam


def shoot(cam, path, loc, target, fov_deg=None, lens=None, fstop=0.0):
    data = cam.data
    if fov_deg:
        data.sensor_fit = "VERTICAL"
        data.angle = math.radians(fov_deg)
    if lens:
        data.sensor_fit = "AUTO"
        data.lens = lens
    data.dof.use_dof = fstop > 0
    if fstop:
        data.dof.aperture_fstop = fstop
        data.dof.focus_distance = (V(target) - V(loc)).length
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    data.clip_start = 0.01
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"fp_arms: rendered {path}")


AIM_CAM = ((-0.30, 0.0, 0.0285), (0.6, 0.0, 0.0255))     # sights aligned
OVER_CAM = ((-0.31, 0.058, 0.05), (0.35, 0.004, -0.07))   # classic viewmodel: gun centred, seen from just above-left
BEAUTY_CAM = ((0.30, -0.42, 0.20), (-0.04, 0.0, -0.06))
SIDE_CAM = ((-0.03, -0.75, -0.05), (-0.03, 0.0, -0.06))
FRONT_CAM = ((-0.03, 0.75, -0.05), (-0.03, 0.0, -0.06))  # straight-on left side


def import_gun():
    # Our minimal "glTF Material Output" group (used for export) confuses the importer.
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is not None:
        bpy.data.node_groups.remove(group)
    bpy.ops.import_scene.gltf(filepath=args.gun)


def render_finals():
    cam = setup_render(args.samples, args.res)
    if args.preview:
        shoot(cam, args.preview, OVER_CAM[0], OVER_CAM[1], fov_deg=60)
    if args.beauty:
        shoot(cam, args.beauty, BEAUTY_CAM[0], BEAUTY_CAM[1], lens=55, fstop=6.0)


# ---------------------------------------------------------------- run
if args.render_only:
    bpy.ops.import_scene.gltf(filepath=args.render_only)
    import_gun()
    render_finals()
elif args.pose:
    build(HIGH)
    import_gun()
    cam = setup_render(16, "960x540")
    stem = args.pose.rsplit(".", 1)[0]
    shoot(cam, stem + "_aim.png", AIM_CAM[0], AIM_CAM[1], fov_deg=60)
    shoot(cam, stem + "_side.png", SIDE_CAM[0], SIDE_CAM[1], lens=60)
    shoot(cam, stem + "_front.png", FRONT_CAM[0], FRONT_CAM[1], lens=60)
    shoot(cam, stem + "_beauty.png", OVER_CAM[0], OVER_CAM[1], fov_deg=60)
elif args.out:
    high = build(HIGH)
    low = build(LOW)
    print(f"fp_arms: high {bakeutil.tri_count(high)} tris, low {bakeutil.tri_count(low)} tris")
    bakeutil.unwrap(low, boost={M_PLATE.name: 1.6, M_GLOVE.name: 1.3})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "fp_arms", cage=0.0015, ray=0.005,
                                 log=print)
    bpy.data.objects.remove(high)
    bakeutil.apply_baked_material(low, tex, "fp_arms", emission_strength=1.5)
    bakeutil.export_gltf(low, args.out)
    print(f"fp_arms: exported {args.out} ({bakeutil.tri_count(low)} tris)")
    if args.preview or args.beauty:
        import_gun()
        render_finals()
