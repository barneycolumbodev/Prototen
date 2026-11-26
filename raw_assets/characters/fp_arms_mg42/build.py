"""First-person arms holding the MG42: right hand on the pistol grip, index
finger on the trigger; left hand wrapped around the clamp-on vertical foregrip.

Same prosthetic hands (raw_assets/_lib/prosthetic.py, 2026-11-25) as
raw_assets/characters/fp_arms/build.py; HIGH is baked onto LOW. The difference is
that every hand is posed around a `Grip` frame, so one hand builder works on any
grip: the MG42's pistol grip uses the Pistol 57 grip frame (same profile, same
place, see raw_assets/weapons/mg42/build.py), the foregrip is a near-vertical
cylinder.

Axes (same as the gun): +X = muzzle, +Z = up, -Y = the gun's RIGHT side.

Run:
  tools/blender.sh raw_assets/characters/fp_arms_mg42/build.py \
      --out assets/characters/fp_arms_mg42/fp_arms_mg42.gltf --tex 2048 --preview docs/previews/fp_arms_mg42.png
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
ap.add_argument("--preview", default="", help="first-person view of the hold")
ap.add_argument("--pose", default="", help="fast unbaked pose check (writes <stem>_fp/_side/_left/_under)")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--gun", default="assets/weapons/mg42/mg42.gltf")
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
# Clamp-on foregrip: cylinder from (0.203, 0, -0.036) to (0.211, 0, -0.130), r 16.5 mm.
FORE_GRIP = Grip((0.2039, 0.0, -0.046), (0.008, 0.0, -0.094), 0.0165, 0.0165)


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
    r_thumb = [g.at(0.016, 172, 0.012), g.at(0.005, -140, 0.0112), V((-0.058, 0.0255, -0.0445)),
               V((-0.033, 0.0255, -0.0465))]
    r_thumb_r = (0.0115, 0.0102, 0.0094)
    finger("R_thumb", r_thumb, r_thumb_r)
    palm_shell("R_palm", g, -0.004, 0.084, 104, 192, 0.018, 0.016)
    arm("R", V((-0.127, -0.033, -0.097)), V((-0.42, -0.21, -0.27)), g.at(0.05, 160, 0.02))

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
    palm_shell("L_palm", f, -0.004, 0.082, -104, -192, 0.018, 0.016)
    thenar = metaball("L_thenar")
    capsule(thenar, f.at(0.03, -140, 0.022), l_thumb[0], 0.0125)
    l_wrist = f.top + V((-0.068, 0.036, -0.072))
    arm("L", l_wrist, V((-0.06, 0.20, -0.30)), f.at(0.055, -160, 0.02))


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
    joined.name = "fp_arms_mg42" if detail is LOW else "fp_arms_mg42_high"
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
    print(f"fp_arms_mg42: rendered {path}")


# The in-game hip hold (data/player/viewmodel_mg42.tres), in Blender axes (glTF z = -Blender y).
FP_CAM = ((-0.40, 0.115, 0.115), (0.7, 0.07, 0.03))
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
    print(f"fp_arms_mg42: high {bakeutil.tri_count(high)} tris, low {bakeutil.tri_count(low)} tris")
    bakeutil.unwrap(low, boost=prosthetic.UV_BOOST)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, _hands.materials, args.tex, tex_dir, "fp_arms_mg42", cage=0.0015, ray=0.005,
                                 log=print)
    bpy.data.objects.remove(high)
    bakeutil.apply_baked_material(low, tex, "fp_arms_mg42", emission_strength=1.5)
    bakeutil.export_gltf(low, args.out)
    print(f"fp_arms_mg42: exported {args.out} ({bakeutil.tri_count(low)} tris)")
    if args.preview:
        import_gun()
        cam = setup_render(args.samples, args.res)
        shoot(cam, args.preview, FP_CAM[0], FP_CAM[1], fov_deg=60)
