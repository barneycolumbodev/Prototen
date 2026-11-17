"""Build the game attack dog: Tripo's quadruped rig + our animations.

tools/blender.sh raw_assets/characters/attack_dog/build.py -- [out.glb] [--frames <dir>]

Input: tripo/rig/rigged.glb (Tripo auto-rig, quadruped, of the 15k game mesh;
Tripo normalises it to 1 m long, so it is scaled back to the real 1.28 m).
Output: assets/characters/attack_dog/attack_dog.glb with the skinned mesh,
2K PBR textures (islands padded so filtering never pulls in the black atlas
background: that was the dark cracks along the seams) and these actions:

  idle_snarl  2.0 s loop   crouched, breathing, jaw trembling, ears flat-ish
  run         0.40 s loop  rotary gallop, about 9-10 m/s
  trot        0.50 s loop  diagonal trot, about 3-5 m/s (circling)
  lunge       0.60 s       crouch, spring, fly with the jaw wide, snap shut, land
  bite        0.50 s       standing snaps and a head shake
  flinch      0.30 s       a hit: head and body jerk away
  death       0.90 s       legs fold, rolls onto its side, jaw slack

The model faces +X (Blender) = +X (Godot); AttackDog turns it to face +Z.
--frames <dir> also renders a few stills of each action there for review.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
argv = [a for a in argv if a != "--"]
frames_dir = None
if "--frames" in argv:
    i = argv.index("--frames")
    frames_dir = Path(argv[i + 1])
    del argv[i:i + 2]
OUT = Path(argv[0]) if argv else ROOT / "assets/characters/attack_dog/attack_dog.glb"
SRC = HERE / "tripo/rig/rigged.glb"
# Tripo's rig-check: normalize_scale 0.7833 (1 m long). Back to life size.
SCALE = 1.0 / 0.7833194732666016
FPS = 30

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
bpy.ops.import_scene.gltf(filepath=str(SRC))

for o in list(scene.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)
arm = next(o for o in scene.objects if o.type == "ARMATURE")
mesh = next(o for o in scene.objects if o.type == "MESH")
arm.name = "AttackDogRig"
mesh.name = "attack_dog"

# Real size, origin on the ground under the dog.
arm.scale = (SCALE, SCALE, SCALE)
arm.location = (0.0, 0.0, arm.location.z * SCALE)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

ws = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
lo = Vector([min(w[i] for w in ws) for i in range(3)])
hi = Vector([max(w[i] for w in ws) for i in range(3)])
print("SIZE", tuple(round(x, 3) for x in hi - lo), "LO", tuple(round(x, 3) for x in lo))

# --- Textures: pad the UV islands (push-pull fill) -------------------------


def uv_mask(size: int) -> np.ndarray:
    me = mesh.data
    me.calc_loop_triangles()
    uv = me.uv_layers.active.data
    m = np.zeros((size, size), dtype=bool)
    for t in me.loop_triangles:
        p = np.array([uv[li].uv[:] for li in t.loops], dtype=np.float64) * size
        x0, y0 = np.floor(p.min(axis=0)).astype(int) - 1
        x1, y1 = np.ceil(p.max(axis=0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
        l3 = 1.0 - l1 - l2
        e = -1.0 / max(abs(d), 1.0) * 2.0  # a pixel of slack
        inside = (l1 >= e) & (l2 >= e) & (l3 >= e)
        m[y0:y1 + 1, x0:x1 + 1] |= inside
    # Grow two pixels so bilinear taps at the edge stay on real colour.
    for _ in range(2):
        g = m.copy()
        g[1:, :] |= m[:-1, :]
        g[:-1, :] |= m[1:, :]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    return m


def push_pull(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fill pixels outside `mask` from the nearest island colour (mip push-pull)."""
    levels = []
    c = img * mask[..., None]
    w = mask.astype(np.float64)
    while c.shape[0] > 1:
        levels.append((c, w))
        h2 = c.shape[0] // 2
        c = c.reshape(h2, 2, h2, 2, -1).sum(axis=(1, 3))
        w = w.reshape(h2, 2, h2, 2).sum(axis=(1, 3))
        nz = w > 0
        c[nz] /= w[nz][:, None]
        w = nz.astype(np.float64)
    filled = c
    for c0, w0 in reversed(levels):
        up = np.repeat(np.repeat(filled, 2, axis=0), 2, axis=1)
        known = w0 > 0
        out = up.copy()
        out[known] = c0[known] / w0[known][:, None]
        filled = out
    return filled


masks = {}
for img in bpy.data.images:
    if img.size[0] == 0:
        continue
    s = img.size[0]
    if s not in masks:
        masks[s] = uv_mask(s)
        print("MASK", s, f"{masks[s].mean() * 100:.1f}% used")
    px = np.array(img.pixels[:], dtype=np.float64).reshape(s, s, 4)
    rgb = push_pull(px[..., :3], masks[s])
    px[..., :3] = rgb
    px[..., 3] = 1.0
    img.pixels = px.astype(np.float32).ravel()
    img.update()
    # Colour and ORM ship as JPEG (as Tripo sent them); the normal map stays
    # PNG. Saved to a file first so the exporter takes those bytes as they are.
    normal = "Normal" in img.name
    tmp = Path(bpy.app.tempdir or "/tmp") / ("%s.%s" % (img.name, "png" if normal else "jpg"))
    img.filepath_raw = str(tmp)
    img.file_format = "PNG" if normal else "JPEG"
    scene.render.image_settings.quality = 90
    img.save(filepath=str(tmp), quality=90)
    img.source = "FILE"
    img.reload()
    img.pack()
    print("PADDED", img.name)

# --- Animation helpers ---------------------------------------------------

pb = arm.pose.bones
REST = {b.name: b.bone.matrix_local.to_quaternion() for b in pb}
REST_HEAD = {b.name: b.bone.head_local.copy() for b in pb}
for b in pb:
    b.rotation_mode = "QUATERNION"

FL = ["tripo::0_Left_Limb_%d" % i for i in range(4)]
FR = ["tripo::0_Right_Limb_%d" % i for i in range(4)]
HL = ["tripo::1_Left_Limb_%d" % i for i in range(4)]
HR = ["tripo::1_Right_Limb_%d" % i for i in range(4)]
SPINE = ["tripo::Spine_%d" % i for i in range(5)]
HEAD, JAW = "tripo::Head_0", "tripo::Head_1"
TAIL = ["tripo::Tail_%d" % i for i in range(3)]
EARS = ["bone_22", "bone_24"]
ROOTB = "tripo::Root"
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def rot(name: str, pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0) -> None:
    """Rotate a bone about armature axes (degrees): pitch about Y (+ = nose/leg
    down-and-back), yaw about Z (+ = to the dog's left), roll about X."""
    q = Quaternion(Z, math.radians(yaw)) @ Quaternion(Y, math.radians(pitch)) @ Quaternion(X, math.radians(roll))
    r = REST[name]
    pb[name].rotation_quaternion = r.inverted() @ q @ r


def move(name: str, offset: Vector) -> None:
    pb[name].location = REST[name].inverted() @ offset


def clear() -> None:
    for b in pb:
        b.rotation_quaternion = Quaternion()
        b.location = Vector()


def key(frame: int) -> None:
    for b in pb:
        b.keyframe_insert("rotation_quaternion", frame=frame)
        b.keyframe_insert("location", frame=frame)


def new_action(name: str) -> bpy.types.Action:
    if arm.animation_data is None:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    return act


def finish(act: bpy.types.Action, cyclic: bool) -> None:
    for fc in _fcurves(act):
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER" if not cyclic else "LINEAR"
    track = arm.animation_data.nla_tracks.new()
    track.name = act.name
    track.strips.new(act.name, 1, act)
    track.mute = True
    arm.animation_data.action = None


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])) > 0:
        return act.fcurves
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def leg(chain: list, swing: float, bend: float, front: bool, paw: float = 0.0) -> None:
    """swing: + back. bend: flexes the joints (front: elbow back / wrist; hind: stifle and hock)."""
    s = 1.0 if front else -1.0
    rot(chain[0], pitch=swing)
    rot(chain[1], pitch=-bend * 0.5 * s)
    rot(chain[2], pitch=bend * s)
    rot(chain[3], pitch=paw - bend * 0.6 * s)


def wave(t: float, phase: float) -> float:
    return math.sin(2 * math.pi * (t + phase))


# --- Actions --------------------------------------------------------------


def make_idle() -> None:
    act = new_action("idle_snarl")
    n = 60
    for f in range(n + 1):
        t = f / n
        clear()
        br = wave(t * 3, 0)  # breathing, three per loop
        tr = math.sin(2 * math.pi * t * 14)  # jaw tremble
        move(ROOTB, Vector((0, 0, -0.008 + br * 0.004)))
        rot(SPINE[1], pitch=br * 1.2)
        rot(SPINE[3], pitch=-br * 0.8)
        rot(HEAD, pitch=2 + wave(t, 0.1) * 2.0, yaw=wave(t, 0.3) * 4.0)
        rot(JAW, pitch=-(6 + tr * 2.5 + br * 2))
        for e in EARS:
            rot(e, pitch=-6 + wave(t * 2, 0.2) * 3)
        rot(TAIL[0], pitch=-4, yaw=wave(t, 0.5) * 3)
        key(f + 1)
    finish(act, True)


def make_gait(name: str, cycle_s: float, phases: dict, swing: float, lift: float, flex: float, bounce: float,
              head_bob: float, jaw: float) -> None:
    act = new_action(name)
    n = max(6, round(cycle_s * FPS))
    for f in range(n + 1):
        t = f / n
        clear()
        for chain, ph, front in ((FL, phases["fl"], True), (FR, phases["fr"], True),
                                 (HL, phases["hl"], False), (HR, phases["hr"], False)):
            sw = wave(t, ph)  # + = leg back (stance pushing), - = reaching forward
            # Fold the leg on the way forward (swing phase), straight in stance.
            fold = max(0.0, math.cos(2 * math.pi * (t + ph))) * lift
            leg(chain, swing * sw, fold, front, paw=fold * 0.4)
        # Spine: gathered when the hind legs reach forward, stretched when they push.
        sp = wave(t, phases["hl"] + 0.25) * flex
        rot(SPINE[0], pitch=-sp)
        rot(SPINE[1], pitch=-sp * 0.7)
        rot(SPINE[3], pitch=sp * 0.5)
        move(ROOTB, Vector((0, 0, bounce * (abs(wave(t, phases["hl"])) - 0.5))))
        rot(ROOTB, pitch=wave(t, phases["hl"] + 0.25) * flex * 0.35)
        rot(HEAD, pitch=-4 + wave(t, phases["fl"] + 0.1) * head_bob)
        rot(JAW, pitch=-jaw - abs(wave(t, 0.0)) * jaw * 0.3)
        for e in EARS:
            rot(e, pitch=10)  # pinned back at speed
        rot(TAIL[0], pitch=-8 + wave(t, 0.3) * 6)
        rot(TAIL[1], pitch=wave(t, 0.45) * 8)
        key(f + 1)
    finish(act, True)


def make_lunge() -> None:
    act = new_action("lunge")
    n = 18  # 0.6 s
    for f in range(n + 1):
        t = f / n
        clear()
        if t < 0.25:  # load: sink, hind legs gather
            k = t / 0.25
            move(ROOTB, Vector((-0.04 * k, 0, -0.06 * k)))
            leg(HL, -12 * k, 22 * k, False)
            leg(HR, -12 * k, 22 * k, False)
            leg(FL, 6 * k, 18 * k, True)
            leg(FR, 6 * k, 18 * k, True)
            rot(HEAD, pitch=6 * k)
            rot(JAW, pitch=-10 - 8 * k)
        elif t < 0.75:  # spring and fly, jaw wide, snap at 0.65
            k = (t - 0.25) / 0.5
            arc = math.sin(math.pi * k)
            move(ROOTB, Vector((0.05, 0, 0.02 + 0.22 * arc)))
            rot(ROOTB, pitch=-14 * arc)
            leg(HL, 34 * min(1, k * 2), 4, False)
            leg(HR, 30 * min(1, k * 2), 4, False)
            leg(FL, -48 * arc, 10 * (1 - arc), True, paw=20 * arc)
            leg(FR, -44 * arc, 10 * (1 - arc), True, paw=20 * arc)
            rot(SPINE[1], pitch=8 * arc)
            rot(SPINE[3], pitch=-6 * arc)
            rot(HEAD, pitch=-16 * arc)
            jaw = 38 if t < 0.62 else 4
            rot(JAW, pitch=-jaw)
            for e in EARS:
                rot(e, pitch=18)
        else:  # land, absorb
            k = (t - 0.75) / 0.25
            move(ROOTB, Vector((0.03 * (1 - k), 0, -0.05 * (1 - k))))
            leg(FL, 10 * (1 - k), 24 * (1 - k), True)
            leg(FR, 10 * (1 - k), 24 * (1 - k), True)
            leg(HL, 8 * (1 - k), 10 * (1 - k), False)
            leg(HR, 8 * (1 - k), 10 * (1 - k), False)
            rot(HEAD, pitch=4 * (1 - k), yaw=10 * math.sin(k * math.pi * 2))
            rot(JAW, pitch=-4 - 6 * k)
        key(f + 1)
    finish(act, False)


def make_bite() -> None:
    act = new_action("bite")
    n = 15  # 0.5 s
    for f in range(n + 1):
        t = f / n
        clear()
        lunge = math.sin(math.pi * min(1.0, t * 2.2))
        move(ROOTB, Vector((0.10 * lunge, 0, 0.02 * lunge)))
        snap = abs(math.sin(2 * math.pi * t * 2))  # opens twice
        rot(JAW, pitch=-(4 + 34 * snap))
        rot(HEAD, pitch=-14 * lunge, yaw=24 * math.sin(2 * math.pi * t * 3) * (1 - t * 0.6))
        rot(SPINE[3], pitch=-6 * lunge)
        leg(FL, -10 * lunge, 6, True)
        leg(FR, -8 * lunge, 6, True)
        for e in EARS:
            rot(e, pitch=14)
        key(f + 1)
    finish(act, False)


def make_flinch() -> None:
    act = new_action("flinch")
    n = 9
    for f in range(n + 1):
        t = f / n
        clear()
        k = math.sin(math.pi * t) * (1 - t * 0.3)
        move(ROOTB, Vector((-0.05 * k, 0.03 * k, -0.03 * k)))
        rot(ROOTB, roll=8 * k)
        rot(SPINE[2], yaw=-8 * k)
        rot(HEAD, pitch=-12 * k, yaw=-20 * k)
        rot(JAW, pitch=-(10 + 20 * k))
        for e in EARS:
            rot(e, pitch=22 * k)
        key(f + 1)
    finish(act, False)


def make_death() -> None:
    act = new_action("death")
    n = 27
    for f in range(n + 1):
        t = f / n
        clear()
        k = min(1.0, t / 0.55)
        e_in = k * k * (3 - 2 * k)
        rf = min(1.0, max(0.0, (t - 0.2) / 0.6)) ** 1.5
        roll = 86 * rf
        # Legs buckle first (sink), then it rolls onto its left side about the
        # ground under it: lifted by half its width so nothing ends underground,
        # and slid back under the origin as the back swings over.
        sink = 0.09 * e_in * (1.0 - rf)
        move(ROOTB, Vector((-0.02 * e_in, -0.14 * rf, -sink + 0.19 * rf)))
        rot(ROOTB, roll=-roll)
        for chain, front in ((FL, True), (FR, True), (HL, False), (HR, False)):
            leg(chain, (-20 if front else 18) * e_in, 30 * e_in, front)
        rot(SPINE[3], pitch=10 * e_in, yaw=-10 * e_in)
        rot(HEAD, pitch=18 * e_in, roll=-15 * e_in)
        rot(JAW, pitch=-14 * e_in)
        for e in EARS:
            rot(e, pitch=-10 * e_in)
        rot(TAIL[0], pitch=12 * e_in)
        key(f + 1)
    finish(act, False)


make_idle()
# Rotary gallop: hind left, hind right, then front left, front right.
make_gait("run", 0.40, {"hl": 0.0, "hr": 0.10, "fl": 0.50, "fr": 0.60},
          swing=34, lift=40, flex=11, bounce=0.035, head_bob=5, jaw=16)
# Trot: diagonal pairs.
make_gait("trot", 0.50, {"hl": 0.0, "fr": 0.0, "hr": 0.5, "fl": 0.5},
          swing=20, lift=26, flex=3, bounce=0.015, head_bob=3, jaw=10)
make_lunge()
make_bite()
make_flinch()
make_death()

clear()
arm.animation_data.action = None

# --- Review stills -------------------------------------------------------

if frames_dir:
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.engine = "CYCLES"  # no EGL in the cloud box for EEVEE
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 400
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.37, 0.4, 1)
    scene.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.7, 0.2, 0.8)
    scene.collection.objects.link(sun)
    bpy.ops.mesh.primitive_plane_add(size=10)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (0.3, -2.6, 0.6)
    cam.rotation_euler = (math.radians(82), 0, 0)
    for act in bpy.data.actions:
        arm.animation_data.action = act
        a, b = (int(x) for x in act.frame_range)
        for i, fr in enumerate(np.linspace(a, b, 4).round().astype(int)):
            scene.frame_set(int(fr))
            scene.render.filepath = str(frames_dir / f"{act.name}_{i}.png")
            bpy.ops.render.render(write_still=True)
        print("FRAMES", act.name, a, b)
    arm.animation_data.action = None
    # The review set stays out of the game file.
    for o in list(scene.objects):
        if o not in (arm, mesh):
            bpy.data.objects.remove(o, do_unlink=True)

for act in bpy.data.actions:
    a, b = act.frame_range
    print("ACTION", act.name, f"{(b - a) / FPS:.2f}s")

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT),
    export_format="GLB",
    export_image_format="AUTO",
    export_jpeg_quality=90,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_frame_step=1,
    export_skins=True,
    export_def_bones=False,
    export_apply=False,
)
print("EXPORT", OUT)
