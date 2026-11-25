"""First-person arms: the operative's prosthetic hands (owner, 2026-11-25), holding
Pistol 57 in a two-handed, thumbs-forward aiming grip.

The pose is computed around the pistol's real grip geometry (see
raw_assets/weapons/pistol_57/build.py), in the same space as the gun, so in
the game the arms and the gun share one viewmodel transform.

The pose is a joint chain per finger (and a palm sheet round the grip); the
hands built on it are raw_assets/_lib/prosthetic.py's: gloss shells over a dark
chassis, titanium knuckles, rubber pads, plated backs, a plated forearm with a
lit collar. HIGH (seams, bevels, screws) is baked onto LOW (the game mesh).

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


# ---------------------------------------------------------------- builders
def link(ob):
    col.objects.link(ob)
    return ob


# ---------------------------------------------------------------- prosthetic hands (owner, 2026-11-25)
# The hands are raw_assets/_lib/prosthetic.py's, built on the pose below (the joint chains and palm sheets
# the metaball gloves had).
import prosthetic  # noqa: E402

_hands = prosthetic.GunArms(globals())
finger, metaball, capsule, palm_shell, arm = _hands.finger, _hands.metaball, _hands.capsule, _hands.palm_shell, _hands.arm


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
        r_mcps.append(joints[0])
    idx = [V((-0.054, -0.0265, -0.043)), V((-0.016, -0.0255, -0.043)), V((0.001, -0.0145, -0.045)),
           V((0.004, -0.0015, -0.047))]
    idx_r = (0.0088, 0.0082, 0.0076)
    finger("R_index", idx, idx_r)
    r_mcps.insert(0, idx[0])
    # Thumb: from the web on the backstrap, across the top of the grip, forward along the left side.
    r_thumb = [grip(0.014, 172, 0.012), grip(-0.010, -150, 0.011), V((-0.056, 0.0262, -0.0215)),
               V((-0.031, 0.0262, -0.0195))]
    r_thumb_r = (0.0115, 0.0102, 0.0094)
    finger("R_thumb", r_thumb, r_thumb_r)

    palm_shell("R_palm", -0.004, 0.084, 104, 192, 0.018, 0.016)
    r_wrist = V((-0.127, -0.033, -0.097))
    arm("R", r_wrist, V((-0.44, -0.20, -0.25)), grip(0.05, 160, 0.02))

    # Back-of-hand plate on the palm shell.

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
        l_mcps.append(joints[0])
    l_thumb = [V((-0.080, 0.050, -0.076)), V((-0.052, 0.040, -0.052)), V((-0.020, 0.0285, -0.0405)),
               V((0.012, 0.0265, -0.037))]
    l_thumb_r = (0.0118, 0.0102, 0.0094)
    finger("L_thumb", l_thumb, l_thumb_r)

    palm_shell("L_palm", 0.006, 0.090, -108, -178, 0.034, 0.016)
    lthenar = metaball("L_thenar")
    capsule(lthenar, grip(0.030, -120, 0.032), l_thumb[0], 0.013)
    l_wrist = V((-0.118, 0.064, -0.118))
    arm("L", l_wrist, V((-0.44, 0.21, -0.28)), grip(0.06, -150, 0.035))


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
GAME_CAM = ((-0.36, 0.105, 0.085), (0.6, 0.07, 0.055))    # data/player/viewmodel_pistol57.tres in Blender axes


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
    # The in-game framing (data/player/viewmodel_pistol57.tres) on a phone-shaped frame, daylight-grey world.
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.2, 0.21, 0.23, 1)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 576
    shoot(cam, stem + "_game.png", GAME_CAM[0], GAME_CAM[1], fov_deg=60)
elif args.out:
    high = build(HIGH)
    low = build(LOW)
    print(f"fp_arms: high {bakeutil.tri_count(high)} tris, low {bakeutil.tri_count(low)} tris")
    bakeutil.unwrap(low, boost=prosthetic.UV_BOOST)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, _hands.materials, args.tex, tex_dir, "fp_arms", cage=0.0015, ray=0.005,
                                 log=print)
    bpy.data.objects.remove(high)
    bakeutil.apply_baked_material(low, tex, "fp_arms", emission_strength=1.5)
    bakeutil.export_gltf(low, args.out)
    print(f"fp_arms: exported {args.out} ({bakeutil.tri_count(low)} tris)")
    if args.preview or args.beauty:
        import_gun()
        render_finals()
