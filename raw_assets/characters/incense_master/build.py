"""The Incense Master's hardware (docs/design.md §8.7a): the black-market Gauss arm that replaces his right arm
from the middle of the upper arm, and his gold-and-diamond pendant on a heavy Cuban chain.

Third person, on the triad rig (raw_assets/characters/triad/common.py BONES). Every piece is modelled in the
local frame of the bone it rides on, so the game hangs it on a BoneAttachment3D with no offset:
  arm_upper  on upper_arm.R  (Y: shoulder -> elbow, 0.30 m; Z: front of the arm; X: outward)
  arm_fore   on forearm.R    (Y: elbow -> wrist, 0.265 m; X: outward, where the rails run)
  arm_hand   on hand.R       (Y: wrist -> knuckles, 0.088 m; Z: back of the hand)
  pendant    on chest        (Y: up the chest; Z: forward; the sternum is about Z = 0.13)
Sizes are the unscaled rig's; the game scales the whole man (EnemyConfig.body_scale). The arm is built a size
up from a human one (forearm ~17 cm across against ~9) so it reads as a weapon at 40 m on a phone.

The slug leaves the muzzle block at the end of the rails: empty `muzzle` (forearm frame) marks it.
Materials (plain factors; the game drives `im_glow` and replaces `im_diamond` with a glint shader):
  im_steel   dark blued gunmetal, the housings and plates
  im_gold    polished gold: trim rings, the knuckle duster, the chain and the pendant
  im_copper  the coil windings
  im_chrome  piston rods
  im_rubber  hoses, the socket gasket
  im_glow    the coils' light and the vents (cyan-blue, like the GX-4's)
  im_diamond the stones

Axes: glTF/Godot. Pieces are built in bone space with Blender's axes standing in for the bone's (Y along the
bone), then turned +90 deg about X before export, so they come out in bone space in Godot (+Y up).

Run (about 30 s, preview about 1 min):
  tools/blender.sh raw_assets/characters/incense_master/build.py --out assets/characters/incense_master/hardware.gltf \
      --preview docs/previews/incense_master_arm.png
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import hardsurface as hs  # noqa: E402

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="assets/characters/incense_master/hardware.gltf")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=48)
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
hs.set_detail(hs.LOW)
scene = bpy.context.scene

M = {
    "steel": hs.material("im_steel", (0.035, 0.038, 0.045), 0.32, 1.0),
    "gold": hs.material("im_gold", (1.0, 0.7, 0.28), 0.16, 1.0),
    "copper": hs.material("im_copper", (0.82, 0.38, 0.18), 0.3, 1.0),
    "chrome": hs.material("im_chrome", (0.8, 0.8, 0.82), 0.08, 1.0),
    "rubber": hs.material("im_rubber", (0.02, 0.02, 0.022), 0.75, 0.0),
    "glow": hs.material("im_glow", (0.05, 0.1, 0.14), 0.3, 0.0, emission=((0.45, 0.8, 1.0), 6.0)),
    "diamond": hs.material("im_diamond", (0.92, 0.95, 1.0), 0.02, 0.0),
}
PIECES = []


def fin(ob, mat, bevel=0.0018, smooth=True):
    hs.finish(ob, M[mat], bevel=bevel, segments=1, angle=40.0, smooth=smooth)
    hs.PARTS.remove(ob)
    PIECES.append(ob)
    return ob


def join(name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in PIECES:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = PIECES[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    PIECES.clear()
    for h in hs.HELPERS:
        bpy.data.objects.remove(h)
    hs.HELPERS.clear()
    return ob


def loft_y(name, stations, n=16, power=2.0):
    """Closed loft along Y: stations (y, half x, half z[, centre x, centre z])."""
    st = []
    for s in stations:
        y, ax, az = s[0], s[1], s[2]
        cx = s[3] if len(s) > 3 else 0.0
        cz = s[4] if len(s) > 4 else 0.0
        st.append(((cx, y, cz), (1, 0, 0), (0, 0, 1), ax, az))
    return hs.loft(name, st, n=n, power=power)


def ring_y(name, y0, y1, r_out, r_in, verts=20, cx=0.0, cz=0.0):
    bm = bmesh.new()
    rings = []
    for y, r in ((y0, r_out), (y1, r_out), (y1, r_in), (y0, r_in)):
        ring = []
        for i in range(verts):
            a = 2 * math.pi * i / verts
            ring.append(bm.verts.new((cx + r * math.cos(a), y, cz + r * math.sin(a))))
        rings.append(ring)
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for i in range(verts):
            j = (i + 1) % verts
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def torus(name, centre, axis, major, minor, seg=10, ring=6):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=seg, minor_segments=ring,
                                     location=centre)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = V((0, 0, 1)).rotation_difference(V(axis).normalized())
    bpy.ops.object.transform_apply(rotation=True)
    return ob


def gem(name, loc, r):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    return ob


# ====================================================================== upper arm (upper_arm.R)
def build_upper():
    # The socket clamps the stump at the cut (0.6 along the bone): a gasket, a gold band, the clamp ring.
    fin(ring_y("gasket", 0.13, 0.155, 0.066, 0.05), "rubber", 0.0)
    fin(ring_y("socket", 0.15, 0.19, 0.078, 0.055), "steel")
    fin(ring_y("band", 0.155, 0.168, 0.081, 0.07), "gold", 0.001)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        fin(hs.cyl_between("bolt", (math.cos(a) * 0.079, 0.177, math.sin(a) * 0.079),
                           (math.cos(a) * 0.088, 0.177, math.sin(a) * 0.088), 0.008, verts=8), "chrome", 0.0)
    # Housing down to the elbow, slab-sided.
    fin(loft_y("housing", [(0.185, 0.072, 0.07), (0.23, 0.075, 0.072), (0.285, 0.066, 0.064), (0.3, 0.06, 0.058)],
               n=16, power=3.0), "steel")
    # Front armour plate and a vent with the glow behind it.
    fin(hs.box("plate_front", (0.1, 0.11, 0.012), (0.0, 0.235, 0.074)), "steel")
    fin(hs.box("vent", (0.05, 0.05, 0.004), (0.0, 0.235, 0.0815)), "glow", 0.0)
    for k in range(4):
        fin(hs.box("vent_slat", (0.056, 0.006, 0.006), (0.0, 0.215 + k * 0.013, 0.083)), "steel", 0.0)
    # The elbow actuator: a hydraulic ram down the back, a chrome rod into the forearm.
    fin(hs.cyl_between("ram", (0.0, 0.19, -0.078), (0.0, 0.29, -0.074), 0.02, verts=10), "steel")
    fin(hs.cyl_between("ram_rod", (0.0, 0.28, -0.074), (0.0, 0.33, -0.07), 0.009, verts=8), "chrome", 0.0)
    # Hoses over the outside, from the socket into the elbow.
    fin(hs.tube_path("hose_a", [V((0.075, 0.17, 0.02)), V((0.095, 0.23, 0.03)), V((0.08, 0.3, 0.02))], 0.011), "rubber", 0.0)
    fin(hs.tube_path("hose_b", [V((0.072, 0.18, -0.03)), V((0.09, 0.24, -0.04)), V((0.075, 0.305, -0.03))], 0.009), "rubber", 0.0)
    # Elbow yoke cheeks either side of the forearm's ball.
    for sx in (1, -1):
        fin(hs.box("yoke", (0.02, 0.07, 0.09), (sx * 0.066, 0.3, 0.0)), "steel")
        fin(hs.cyl_between("pin", (sx * 0.075, 0.3, 0.0), (sx * 0.083, 0.3, 0.0), 0.03, verts=12), "gold", 0.001)
    return join("arm_upper")


# ====================================================================== forearm (forearm.R)
def build_fore():
    fin(hs.cyl_between("elbow_ball", (-0.056, 0.0, 0.0), (0.056, 0.0, 0.0), 0.058, verts=16), "steel")
    fin(loft_y("housing", [(0.02, 0.072, 0.07), (0.07, 0.084, 0.08), (0.15, 0.086, 0.082), (0.22, 0.074, 0.07),
                            (0.255, 0.066, 0.062)], n=16, power=3.2), "steel")
    # The coils: four copper windings round the housing, lit between.
    for k, y in enumerate((0.075, 0.11, 0.145, 0.18)):
        fin(ring_y("coil", y - 0.011, y + 0.011, 0.099, 0.08, verts=18), "copper", 0.001)
        fin(ring_y("coil_band", y - 0.004, y + 0.004, 0.1015, 0.098, verts=18), "gold" if k % 2 == 0 else "steel", 0.0)
        if k < 3:
            fin(ring_y("glow_ring", y + 0.011, y + 0.024, 0.088, 0.08, verts=18), "glow", 0.0)
    # Rails along the outside (+X), past the wrist, and the muzzle block between them.
    for sz in (1, -1):
        fin(hs.box("rail", (0.018, 0.29, 0.016), (0.104, 0.155, sz * 0.026)), "steel")
        fin(hs.box("rail_glow", (0.004, 0.24, 0.004), (0.114, 0.15, sz * 0.026)), "glow", 0.0)
    fin(hs.box("muzzle_block", (0.036, 0.04, 0.074), (0.104, 0.3, 0.0)), "steel")
    fin(ring_y("muzzle_ring", 0.318, 0.326, 0.02, 0.012, verts=12, cx=0.104), "gold", 0.0)
    fin(hs.cyl_between("bore_glow", (0.104, 0.318, 0.0), (0.104, 0.321, 0.0), 0.0125, verts=12), "glow", 0.0)
    # Armour over the back of the forearm, a capacitor bank on the inside.
    fin(hs.box("plate_back", (0.09, 0.15, 0.014), (0.0, 0.13, -0.088)), "steel")
    fin(hs.box("cap_bank", (0.03, 0.12, 0.05), (-0.09, 0.13, 0.0)), "steel")
    for k in range(3):
        fin(hs.cyl_between("cap", (-0.1, 0.09 + k * 0.04, -0.016), (-0.1, 0.09 + k * 0.04, 0.016), 0.012, verts=10), "copper", 0.0)
    fin(hs.tube_path("hose_c", [V((-0.075, 0.03, 0.05)), V((-0.1, 0.12, 0.07)), V((-0.07, 0.24, 0.05))], 0.01), "rubber", 0.0)
    # Wrist collar.
    fin(ring_y("wrist", 0.245, 0.27, 0.07, 0.04, verts=18), "steel")
    fin(ring_y("wrist_band", 0.252, 0.262, 0.073, 0.06, verts=18), "gold", 0.0)
    return join("arm_fore")


# ====================================================================== fist (hand.R): Z = back of the hand
def build_hand():
    fin(hs.cyl_between("wrist_joint", (-0.045, 0.0, 0.0), (0.045, 0.0, 0.0), 0.04, verts=12), "steel")
    fin(loft_y("palm", [(0.008, 0.055, 0.038), (0.06, 0.066, 0.045), (0.098, 0.068, 0.046)], n=14, power=3.5), "steel")
    # Four thick fingers curled into a fist: proximal down the front, the rest folded under.
    for k, x in enumerate((-0.045, -0.015, 0.015, 0.045)):
        fin(hs.box("f1", (0.027, 0.036, 0.05), (x, 0.118, 0.01)), "steel")
        fin(hs.box("f2", (0.025, 0.04, 0.026), (x, 0.108, -0.042)), "steel")
        fin(hs.box("f3", (0.023, 0.032, 0.022), (x, 0.08, -0.05)), "steel")
        fin(hs.cyl_between("knuckle", (x - 0.013, 0.118, 0.037), (x + 0.013, 0.118, 0.037), 0.015, verts=10), "steel")
    # The knuckle duster: a gold bar across the front with four studs.
    fin(hs.box("duster", (0.124, 0.03, 0.026), (0.0, 0.14, 0.022)), "gold", 0.002)
    for x in (-0.045, -0.015, 0.015, 0.045):
        fin(hs.cyl_between("stud", (x, 0.152, 0.022), (x, 0.166, 0.022), 0.011, radius2=0.004, verts=8), "gold", 0.0)
    # Thumb over the front of the fingers on the inner side.
    fin(hs.cyl_between("thumb_a", (-0.06, 0.03, -0.02), (-0.066, 0.075, -0.045), 0.017, verts=10), "steel")
    fin(hs.cyl_between("thumb_b", (-0.066, 0.075, -0.045), (-0.035, 0.105, -0.058), 0.015, verts=10), "steel")
    # A plate and a lit seam on the back of the hand.
    fin(hs.box("back_plate", (0.11, 0.08, 0.012), (0.0, 0.055, 0.048)), "steel")
    fin(hs.box("back_glow", (0.08, 0.004, 0.004), (0.0, 0.088, 0.055)), "glow", 0.0)
    return join("arm_hand")


# ====================================================================== pendant (chest): Z = forward
def build_pendant():
    # A heavy Cuban chain from behind the neck down the collarbones to the medallion.
    def chain_point(t, sx):
        # t 0: at the side of the neck (high, back), 1: at the medallion's bail.
        y = 0.2 - 0.12 * t * t
        x = sx * 0.085 * (1.0 - t) ** 0.8
        z = 0.06 + 0.088 * math.sin(t * math.pi * 0.5)
        return V((x, y, z))
    for sx in (1, -1):
        n = 17
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            a, b = chain_point(t0, sx), chain_point(t1, sx)
            mid = (a + b) * 0.5
            axis = (b - a).normalized().cross(V((0, 0, 1)))
            if i % 2:
                axis = (b - a).normalized()
            fin(torus("link", mid, axis if axis.length > 0.01 else V((1, 0, 0)), 0.0078, 0.0033), "gold", 0.0)
            if i % 4 == 2:
                fin(gem("ice", mid + V((0, 0, 0.005)), 0.0032), "diamond", 0.0)
    # Bail and medallion: a gold disc with a raised rim, a ring of stones and a big one in the middle.
    c = V((0.0, 0.05, 0.148))
    fin(torus("bail", c + V((0, 0.036, 0.0)), (1, 0, 0), 0.008, 0.0028), "gold", 0.0)
    fin(hs.cyl_between("disc", c - V((0, 0, 0.004)), c + V((0, 0, 0.004)), 0.032, verts=24), "gold", 0.001)
    fin(torus("rim", c + V((0, 0, 0.004)), (0, 0, 1), 0.03, 0.003, seg=24), "gold", 0.0)
    for k in range(12):
        a = 2 * math.pi * k / 12
        fin(gem("stone", c + V((math.cos(a) * 0.022, math.sin(a) * 0.022, 0.0065)), 0.0042), "diamond", 0.0)
    fin(torus("inner_rim", c + V((0, 0, 0.005)), (0, 0, 1), 0.0145, 0.0022, seg=20), "gold", 0.0)
    for k in range(8):
        a = 2 * math.pi * k / 8 + 0.39
        fin(hs.box("ray", (0.003, 0.012, 0.003), c + V((math.cos(a) * 0.0085, math.sin(a) * 0.0085, 0.005)),
                   rot=(0, 0, a - math.pi / 2)), "gold", 0.0)
    fin(gem("centre", c + V((0, 0, 0.009)), 0.0075), "diamond", 0.0)
    return join("pendant")


def to_godot(ob):
    """Bone space in Blender axes -> bone space in Godot after the glTF Y-up conversion."""
    ob.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))


parts = [build_upper(), build_fore(), build_hand(), build_pendant()]
muzzle = hs.link(bpy.data.objects.new("muzzle", None))
muzzle.location = (0.104, 0.322, 0.0)
tris = 0
for ob in parts:
    ob.data.calc_loop_triangles()
    tris += len(ob.data.loop_triangles)
    print(f"{ob.name}: {len(ob.data.loop_triangles)} triangles")
print(f"total: {tris} triangles")


def render_preview(path):
    """The arm assembled in a raised, bent pose with the pendant beside it."""
    up = parts[0]
    fore = parts[1]
    hand = parts[2]
    pend = parts[3]
    # Upper arm hanging forward-down, forearm bent up 75 deg toward the camera's left.
    # Seen from outside (bone X toward the camera), hanging, the forearm bent 80 deg forward.
    m_up = Matrix(((0, 0, 1, 0), (-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
    m_fore = m_up @ Matrix.Translation((0, 0.3, 0)) @ Matrix.Rotation(math.radians(80), 4, "X")
    m_hand = m_fore @ Matrix.Translation((0, 0.265, 0)) @ Matrix.Rotation(math.radians(10), 4, "X")
    up.matrix_world = m_up
    fore.matrix_world = m_fore
    hand.matrix_world = m_hand
    pend.matrix_world = Matrix.Translation((0.62, 0.0, -0.32)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Scale(1.6, 4)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("night")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.022, 0.03, 1)
    scene.world = world
    aim = V((0.25, 0.0, -0.22))

    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color, ld.size = energy, color, size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (aim - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.6, -1.2, 0.6), 90, 1.2, (1.0, 0.9, 0.85))
    area("neon_l", (1.0, 0.9, 0.3), 50, 0.8, (1.0, 0.35, 0.45))
    area("neon_r", (0.9, -1.0, -0.4), 40, 0.8, (0.35, 0.7, 1.0))
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    cam.data.lens = 45
    cam.location = (0.3, -1.55, 0.05)
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("preview", path)
    for ob in parts:
        ob.matrix_world = Matrix.Identity(4)


if args.preview:
    render_preview(args.preview)

if args.out:
    for ob in parts:
        to_godot(ob)
    muzzle.location = Matrix.Rotation(math.radians(90), 4, "X") @ muzzle.location
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=args.out, export_format="GLTF_SEPARATE", export_apply=True,
                              export_animations=False, export_extras=False, export_yup=True,
                              export_cameras=False, export_lights=False)
    print("exported", args.out)
