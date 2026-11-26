"""First-person arms holding the SPAS-12: right hand on the polymer pistol
grip, index finger on the trigger; left hand wrapped round the ribbed pump,
palm and thumb on the left, fingers under it and up its right side. Derived
from raw_assets/characters/fp_arms_spas12/build.py. The SPAS grip is the Pistol
57 grip's size but sits 20 mm further forward, 25 mm lower and raked 6 degrees
more (raw_assets/weapons/spas12/build.py, traced from the photo), so the right
hand is built in the Pistol 57 frame and moved onto it; the index finger is
laid on the SPAS trigger.

Two nodes: `fp_arms_spas12` (the right arm) and `support_arm` (the left hand
and arm). The game slides `support_arm` with the pump (ViewmodelRig.set_pump),
so the hand racks it. They are baked together and split after.

Same prosthetic hands (raw_assets/_lib/prosthetic.py, 2026-11-25) as
raw_assets/characters/fp_arms/build.py; HIGH is baked onto LOW. The difference is
that every hand is posed around a `Grip` frame, so one hand builder works on any
grip: the pistol grip uses the Pistol 57 grip frame, the foregrip is a
near-vertical cylinder.

Axes (same as the gun): +X = muzzle, +Z = up, -Y = the gun's RIGHT side.

Run:
  tools/blender.sh raw_assets/characters/fp_arms_spas12/build.py \
      --out assets/characters/fp_arms_spas12/fp_arms_spas12.gltf --tex 2048 --preview docs/previews/fp_arms_spas12.png
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
ap.add_argument("--gun", default="assets/weapons/spas12/spas12.gltf")
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


# The right hand is posed on the Pistol 57 grip frame, then carried onto the SPAS grip:
# P57 top (-0.054, -0.050), axis (-0.029, -0.080); SPAS grip centre line from the trace,
# photo (3445, 1235) to (3573, 1500) at 4.44 px/mm about x 3300, row 918.5.
PISTOL_GRIP = Grip((-0.054, 0.0, -0.050), (-0.029, 0.0, -0.080), 0.0250, 0.0155)
SPAS_TOP = V((-0.0327, 0.0, -0.0713))
SPAS_AXIS = V((-0.0288, 0.0, -0.0597)).normalized()
# The pump's hand section as a horizontal grip: axis +X from its rear lip, `fwd` is up.
# Centre z -0.028, 62 mm tall, 57 mm wide (raw_assets/weapons/spas12/build.py FORE).
PUMP = Grip((0.262, 0.0, -0.0285), (1.0, 0.0, 0.0), 0.0312, 0.0290)
SUPPORT_X = 0.08          # parts whose centre lies forward of this are the support arm


# ---------------------------------------------------------------- builders (as fp_arms, grip-relative)
def link(ob):
    col.objects.link(ob)
    return ob


def wrap_fingers(prefix, g, spec, extra_base=0.0):
    """Fingers wrapped around grip g: spec = {name: (h, radii, thetas)}."""
    for name, (h, radii, thetas) in spec.items():
        joints = [g.at(h, t, extra_base + radii[0]) for t in thetas]
        finger(f"{prefix}_{name}", joints, radii)


# ---------------------------------------------------------------- prosthetic hands (owner, 2026-11-25)
# The hands are raw_assets/_lib/prosthetic.py's, built on the pose below (the joint chains and palm sheets
# the metaball gloves had).
import prosthetic  # noqa: E402

_hands = prosthetic.GunArms(globals())
finger, metaball, capsule, palm_shell, arm = _hands.finger, _hands.metaball, _hands.capsule, _hands.palm_shell, _hands.arm


# ---------------------------------------------------------------- the pose
def grip_transform():
    """The rigid move from the Pistol 57 grip frame onto the SPAS grip (rotation about Y + shift)."""
    a1 = math.atan2(-PISTOL_GRIP.axis.x, -PISTOL_GRIP.axis.z)
    a2 = math.atan2(-SPAS_AXIS.x, -SPAS_AXIS.z)
    rot = Matrix.Rotation(a1 - a2, 4, "Y")
    return Matrix.Translation(SPAS_TOP) @ rot @ Matrix.Translation(-PISTOL_GRIP.top)


def build_hands():
    # ---- Firing (right) hand on the pistol grip: the Pistol 57 hold, moved onto the SPAS grip.
    first = len(PARTS)
    g = PISTOL_GRIP
    wrap_fingers("R", g, {
        "middle": (0.031, (0.0094, 0.0089, 0.0082), (114, 40, -36, -82)),
        "ring": (0.050, (0.0090, 0.0085, 0.0078), (112, 40, -34, -78)),
        "pinky": (0.068, (0.0080, 0.0075, 0.0069), (108, 42, -28, -68)),
    })
    r_thumb = [g.at(0.016, 172, 0.012), g.at(0.005, -140, 0.0112), V((-0.058, 0.0262, -0.0445)),
               V((-0.033, 0.0262, -0.0465))]
    r_thumb_r = (0.0115, 0.0102, 0.0094)
    finger("R_thumb", r_thumb, r_thumb_r)
    palm_shell("R_palm", g, -0.004, 0.084, 104, 192, 0.018, 0.016)
    arm("R", V((-0.127, -0.033, -0.097)), V((-0.42, -0.21, -0.27)), g.at(0.05, 160, 0.02))
    m = grip_transform()
    for ob in PARTS[first:]:
        ob.matrix_world = m @ ob.matrix_world
    # Index finger along the right of the housing onto the trigger (blade x 0.0 to 0.011, z -0.045 to -0.074).
    knuckle = m @ V((-0.054, -0.0262, -0.043))
    idx = [knuckle, V((-0.018, -0.0245, -0.0625)), V((-0.002, -0.0135, -0.0645)), V((0.0035, -0.0010, -0.0660))]
    idx_r = (0.0088, 0.0082, 0.0076)
    finger("R_index", idx, idx_r)

    # ---- Support (left) hand round the pump: palm on the lower left, fingers under it and up the right
    # side (index forward), thumb along the upper left pointing at the muzzle.
    f = PUMP
    wrap_fingers("L", f, {
        "pinky": (0.012, (0.0080, 0.0075, 0.0069), (-128, -172, 150, 112)),
        "ring": (0.031, (0.0090, 0.0085, 0.0078), (-130, -174, 146, 106)),
        "middle": (0.050, (0.0094, 0.0089, 0.0082), (-132, -176, 144, 102)),
        "index": (0.069, (0.0090, 0.0085, 0.0078), (-130, -174, 146, 108)),
    })
    l_thumb = [f.at(0.020, -112, 0.012), f.at(0.046, -84, 0.0104), f.at(0.068, -70, 0.0096),
               f.at(0.088, -62, 0.0092)]
    l_thumb_r = (0.0118, 0.0104, 0.0094)
    finger("L_thumb", l_thumb, l_thumb_r)
    palm_shell("L_palm", f, -0.002, 0.082, -96, -150, 0.017, 0.016)
    thenar = metaball("L_thenar")
    capsule(thenar, f.at(0.016, -130, 0.022), l_thumb[0], 0.0125)
    l_wrist = V((0.238, 0.050, -0.072))
    arm("L", l_wrist, V((-0.02, 0.22, -0.30)), f.at(0.010, -140, 0.02))


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
    # Tag every piece: 1 = the support (left) arm, 0 = the firing arm.
    for ob in meshes:
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for ob in meshes:
        c = sum((ob.matrix_world @ v.co for v in ob.data.vertices), V()) / len(ob.data.vertices)
        attr = ob.data.attributes.new("part_id", "INT", "FACE")
        attr.data.foreach_set("value", [1 if c.x > SUPPORT_X else 0] * len(ob.data.polygons))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = "fp_arms_spas12" if detail is LOW else "fp_arms_spas12_high"
    joined.data.shade_smooth()
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
    print(f"fp_arms_spas12: rendered {path}")


# The in-game hip hold (data/player/viewmodel_spas12.tres), in Blender axes (glTF z = -Blender y).
FP_CAM = ((-0.50, 0.17, 0.17), (0.80, 0.10, 0.13))
SIDE_CAM = ((0.0, -1.1, -0.06), (0.0, 0.0, -0.06))
LEFT_CAM = ((0.05, 0.9, -0.02), (0.05, 0.0, -0.07))
UNDER_CAM = ((0.15, -0.45, -0.40), (0.05, 0.0, -0.07))


def split_support(low):
    """Moves the support arm's faces (part_id 1) into their own object, `support_arm`."""
    sup = low.copy()
    sup.data = low.data.copy()
    sup.name = sup.data.name = "support_arm"
    col.objects.link(sup)
    for ob, keep in ((low, 0), (sup, 1)):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer = bm.faces.layers.int.get("part_id")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != keep], context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.attributes.remove(ob.data.attributes["part_id"])
        print(f"fp_arms_spas12: {ob.name}: {bakeutil.tri_count(ob)} tris")
    return sup


def export_both(low, sup, path):
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    sup.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True,
                              export_image_format="AUTO", export_attributes=False)


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
    print(f"fp_arms_spas12: high {bakeutil.tri_count(high)} tris, low {bakeutil.tri_count(low)} tris")
    bakeutil.unwrap(low, boost=prosthetic.UV_BOOST)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, _hands.materials, args.tex, tex_dir, "fp_arms_spas12", cage=0.0015, ray=0.005,
                                 log=print)
    bpy.data.objects.remove(high)
    bakeutil.apply_baked_material(low, tex, "fp_arms_spas12", emission_strength=1.5)
    support = split_support(low)
    export_both(low, support, args.out)
    print(f"fp_arms_spas12: exported {args.out} ({bakeutil.tri_count(low)} tris)")
    if args.preview:
        import_gun()
        cam = setup_render(args.samples, args.res)
        shoot(cam, args.preview, FP_CAM[0], FP_CAM[1], fov_deg=60)
