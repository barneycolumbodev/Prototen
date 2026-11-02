"""Pistol 57: FN Five-seveN-style 5.7x28mm pistol with a long suppressor.

Rebuilt 2026-11-01 (owner: "doesn't look nearly as good as the MG42"; keep the
olive finish, make every other improvement). Same size and the same key points
as the first version, so the arms, sights, muzzle and gameplay still line up:
pistol ~208 mm, suppressor ~180 mm, sight line z = 0.0262, muzzle x = 0.284,
grip frame GRIP_TOP/AXIS with 25.5 x 15.5 mm half sizes (the hands in
raw_assets/characters/fp_arms/build.py are posed around exactly that ellipse).

What changed from v1:
  - Frame and grip are lofted rounded sections instead of flat slab extrusions:
    the grip is an oval that follows the 20° rake and flares at the bottom, the
    dust cover is rounded underneath and narrows to the nose, a beavertail
    covers the web of the hand, the trigger guard is a squared, rounded loop.
  - Slide: lower chamfers, tapered nose, top sight channel, extractor, firing
    pin cap, chamber indicator; barrel hood visible in the ejection port.
  - Grip has its own stippled olive material; the smooth frame gets edge wear,
    the slide machining marks; lighter cavity grime in the bake.
  - Moving parts (body / slide / magazine) come straight from a per-face part
    id, so split_parts.py is no longer needed.
  - Shared helpers: raw_assets/_lib/hardsurface.py and bakeutil.py.

Milsci touches as before: fluted suppressor with hex mount collar, heat band and
data plate; the Fire-Control Link readout and palm contact pads (docs/design.md §3.5).

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:  tools/blender.sh raw_assets/weapons/pistol_57/build.py \
        --out assets/weapons/pistol_57/pistol_57.gltf --tex 2048 --preview docs/previews/pistol_57.png
      Without --out the procedural HIGH model is rendered (fast look).
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--emission-size", type=int, default=512)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_side/_beauty/_detail/_top.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material


# ---------------------------------------------------------------- materials
def stippled(name, base, rough, wear):
    """Olive polymer with a voronoi stipple texture over the whole surface."""
    m = mat(name, base, rough, 0.0, wear=wear, wear_rough=min(1.0, rough + 0.1))
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1300.0
    L.new(tc.outputs["Object"], vor.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2600.0
    mix = N.new("ShaderNodeMath")
    mix.operation = "MULTIPLY_ADD"
    mix.inputs[2].default_value = 0.0
    L.new(vor.outputs["Distance"], mix.inputs[0])
    mix.inputs[1].default_value = 1.0
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.75
    bump.inputs["Distance"].default_value = 0.0004
    L.new(mix.outputs[0], bump.inputs["Height"])
    bump2 = N.new("ShaderNodeBump")
    bump2.inputs["Strength"].default_value = 0.2
    bump2.inputs["Distance"].default_value = 0.0001
    L.new(noise.outputs["Fac"], bump2.inputs["Height"])
    L.new(bump2.outputs["Normal"], bump.inputs["Normal"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


OLIVE = (0.062, 0.066, 0.052)
OLIVE_WEAR = (0.15, 0.155, 0.128)
M_SLIDE = mat("slide_nitride", (0.04, 0.042, 0.045), 0.38, 0.8, wear=(0.45, 0.45, 0.46), wear_rough=0.22,
              brushed=0.06, bump_scale=900, bump_strength=0.04)
M_FRAME = mat("frame_polymer", OLIVE, 0.55, 0.0, wear=OLIVE_WEAR, wear_rough=0.62, bump_scale=1600, bump_strength=0.12)
M_GRIP = stippled("grip_stipple", OLIVE, 0.72, OLIVE_WEAR)
M_STEEL = mat("steel_dark", (0.06, 0.06, 0.065), 0.3, 1.0, wear=(0.5, 0.5, 0.52))
M_CAN = mat("suppressor_cerakote", (0.13, 0.135, 0.14), 0.38, 1.0, wear=(0.55, 0.55, 0.56),
            bump_scale=700, bump_strength=0.04)
M_BAND = mat("heat_band", (0.16, 0.12, 0.07), 0.45, 1.0)
M_GLASS = mat("readout_glass", (0.01, 0.012, 0.014), 0.08, 0.0)
M_AMBER = mat("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_PAD = mat("contact_pad", (0.55, 0.32, 0.18), 0.3, 1.0)
M_MARK = mat("engraving", (0.34, 0.35, 0.36), 0.5, 1.0)
M_RED = mat("indicator_red", (0.5, 0.04, 0.03), 0.4, 0.0)
MATERIALS = [M_SLIDE, M_FRAME, M_GRIP, M_STEEL, M_CAN, M_BAND, M_GLASS, M_AMBER, M_PAD, M_MARK, M_RED]

# ---------------------------------------------------------------- dimensions (unchanged from v1)
SLIDE_HALF = 0.01275
SLIDE_X0, SLIDE_X1 = -0.100, 0.098
FRAME_HW = 0.015
SIGHT_Z = 0.0262
CAN_R = 0.0182
X_COLLAR0, X_COLLAR1 = 0.104, 0.126
X_TUBE1, X_CAP1 = 0.262, 0.284
GRIP_TOP = V((-0.054, 0.0, -0.050))
AXIS = V((-0.029, 0.0, -0.080)).normalized()
FWD = V((-AXIS.z, 0.0, AXIS.x))
RIGHT = V((0.0, -1.0, 0.0))
GRIP_HD, GRIP_HW = 0.0255, 0.0155

PART_IDS = {"body": 0, "slide": 1, "magazine": 2}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m):
    ob = hs.text(name, body, size, loc, rot, m)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def grip_point(h, theta_deg, extra=0.0):
    t = math.radians(theta_deg)
    return GRIP_TOP + AXIS * h + FWD * ((GRIP_HD + extra) * math.cos(t)) + RIGHT * ((GRIP_HW + extra) * math.sin(t))


# ---------------------------------------------------------------- slide
def build_slide():
    part("slide")
    slide = hs.section("slide", [(-SLIDE_HALF + 0.0015, -0.010), (SLIDE_HALF - 0.0015, -0.010), (SLIDE_HALF, -0.0085),
                                 (SLIDE_HALF, 0.013), (0.0085, 0.020), (-0.0085, 0.020), (-SLIDE_HALF, 0.013),
                                 (-SLIDE_HALF, -0.0085)], SLIDE_X0, SLIDE_X1)
    # Sloped nose underneath, tapered nose in plan view.
    hs.cut(slide, hs.box("slide_front_cut", (0.03, 0.05, 0.02), (0.108, 0, -0.016), (0, math.radians(-38), 0)))
    for sy in (-1, 1):
        hs.cut(slide, hs.box(f"nose_taper{sy}", (0.04, 0.01, 0.05), (0.104, sy * (SLIDE_HALF + 0.0035), 0.0),
                             (0, 0, math.radians(-sy * 14))))
    # Rear face bevel, ejection port, top sight channel.
    hs.cut(slide, hs.box("rear_bevel", (0.01, 0.05, 0.02), (SLIDE_X0 - 0.003, 0, 0.022), (0, math.radians(35), 0)))
    hs.cut(slide, hs.box("ejection_port", (0.034, 0.012, 0.012), (0.012, 0.009, 0.019)))
    hs.cut(slide, hs.box("sight_channel", (0.15, 0.0045, 0.002), (0.0, 0, 0.0205)))
    for name, x0, n in (("rear_serr", -0.094, 8), ("front_serr", 0.056, 6)):
        s = hs.box(name, (0.0014, 0.0026, 0.016), (x0, SLIDE_HALF + 0.0001, 0.003), (0, math.radians(-8), 0))
        hs.linear_array(s, n, (0.0038, 0, 0))
        hs.mirror_y(s)
        hs.cut(slide, s)
    hs.cut(slide, hs.box("slide_flat", (0.07, 0.004, 0.004), (0.010, -SLIDE_HALF - 0.0005, 0.0145),
                         (math.radians(-35), 0, 0)))
    finish(slide, M_SLIDE, bevel=0.0007)

    # Sights: same heights as v1 (sight line z = 0.0262), with tritium-style dots.
    rear = hs.box("rear_sight", (0.012, 0.018, 0.0075), (-0.086, 0, 0.0235))
    hs.cut(rear, hs.box("rear_notch", (0.02, 0.0035, 0.004), (-0.086, 0, 0.0275)))
    hs.cut(rear, hs.box("rear_ramp", (0.012, 0.03, 0.01), (-0.094, 0, 0.0275), (0, math.radians(-30), 0)))
    finish(rear, M_STEEL, bevel=0.0004)
    for sy in (-1, 1):
        finish(hs.box(f"rear_dot{sy}", (0.0004, 0.0016, 0.0016), (-0.0802, sy * 0.0042, 0.0247)), M_AMBER, bevel=0)
    front = hs.box("front_sight", (0.006, 0.003, 0.0065), (0.090, 0, 0.0228))
    finish(front, M_STEEL, bevel=0.0004)
    finish(hs.box("front_dot", (0.0004, 0.0015, 0.0015), (0.0868, 0, 0.0243)), M_AMBER, bevel=0)

    # Extractor (right), chamber indicator (top), firing pin cap (rear).
    finish(hs.box("extractor", (0.018, 0.0012, 0.0035), (0.012, -SLIDE_HALF - 0.0004, 0.0065)), M_STEEL, bevel=0.0003)
    finish(hs.box("chamber_ind", (0.006, 0.003, 0.0012), (0.034, 0, 0.0203)), M_RED, bevel=0.0003)
    finish(hs.box("fp_cap", (0.0015, 0.016, 0.014), (SLIDE_X0 - 0.0006, 0, 0.002)), M_STEEL, bevel=0.0005)
    if hs.D["text"]:
        text("mark_model", "SP-57  //  5.7x28", 0.0042, (-0.040, -SLIDE_HALF - 0.0001, -0.0055), (math.pi / 2, 0, 0), M_MARK)
        text("mark_left", "GRAFT ARMS", 0.0034, (0.030, SLIDE_HALF + 0.0001, -0.0045), (math.pi / 2, 0, math.pi), M_MARK)
    part("body")


# ---------------------------------------------------------------- frame and grip
def build_frame():
    # Dust cover / upper frame: rounded underneath, narrowing to the nose.
    upper = hs.loft_x("frame_upper", [(-0.100, -0.0095, -0.022, 0.0135), (-0.088, -0.0095, -0.0305, 0.0150),
                                      (0.000, -0.0095, -0.0305, 0.0150), (0.046, -0.0095, -0.0290, 0.0150),
                                      (0.088, -0.0095, -0.0268, 0.0146), (0.097, -0.0105, -0.0235, 0.0128)],
                      power=4.0)
    finish(upper, M_FRAME, bevel=0.0008, angle=40)

    # Grip: oval sections along the rake, on the frame the hands were posed around.
    stations = []
    # Starts inside the dust cover (no gap under the frame), runs long and is cut flat at the bottom.
    for h, sd, sw in ((-0.032, 0.92, 0.94), (-0.012, 0.97, 0.97), (0.030, 1.0, 1.0), (0.060, 1.0, 1.0),
                      (0.082, 1.02, 1.03), (0.104, 1.02, 1.03)):
        stations.append((GRIP_TOP + AXIS * h, FWD, RIGHT, GRIP_HD * sd, GRIP_HW * sw))
    grip = hs.loft("grip", stations, power=2.3)
    # Finger grooves where the firing hand's middle, ring and little fingers sit.
    for i, h in enumerate((0.031, 0.050, 0.068)):
        c = GRIP_TOP + AXIS * h + FWD * (GRIP_HD + 0.0057)
        g = hs.cyl_y(f"finger_groove{i}", 0.0072, 0.06, tuple(c), verts=32)
        hs.cut(grip, g)
    hs.cut(grip, hs.box("grip_floor", (0.12, 0.06, 0.04), (-0.085, 0, -0.1372 - 0.02)))
    finish(grip, M_GRIP, bevel=0.0012, segments=2, angle=50)

    # Beavertail over the web of the hand.
    beaver = hs.loft_x("beavertail", [(-0.082, -0.0100, -0.036, 0.0145), (-0.098, -0.0105, -0.0315, 0.0135),
                                      (-0.108, -0.0125, -0.0255, 0.0110), (-0.1125, -0.0165, -0.0215, 0.0065),
                                      (-0.1135, -0.0178, -0.0203, 0.0030)],
                       power=3.0)
    finish(beaver, M_FRAME, bevel=0.0)

    # Squared, rounded trigger guard (a flattened tube), joining the grip and the dust cover.
    guard = hs.tube_path("trigger_guard", [(-0.026, 0, -0.050), (-0.014, 0, -0.0585), (0.012, 0, -0.0592),
                                           (0.036, 0, -0.0578), (0.0425, 0, -0.0505), (0.0435, 0, -0.038),
                                           (0.042, 0, -0.027)], 0.0034, width_scale=2.3)
    finish(guard, M_FRAME, bevel=0.0, smooth=True)
    # Accessory rail under the dust cover.
    rail = hs.box("rail", (0.040, 0.019, 0.0045), (0.069, 0, -0.0292))
    slot = hs.box("rail_slot", (0.0026, 0.03, 0.003), (0.052, 0, -0.0315))
    hs.linear_array(slot, 7, (0.0052, 0, 0))
    hs.cut(rail, slot)
    finish(rail, M_FRAME, bevel=0.0004)

    # Trigger (curved face), slide stop, takedown pin, magazine releases, ambi safety.
    finish(hs.side_profile("trigger", [(0.012, -0.029), (0.018, -0.029), (0.0165, -0.037), (0.019, -0.046),
                                       (0.021, -0.051), (0.0155, -0.0535), (0.0105, -0.045), (0.008, -0.037)], 0.0055),
           M_STEEL, bevel=0.0007, angle=30)
    finish(hs.box("slide_stop", (0.020, 0.0025, 0.0045), (-0.020, -FRAME_HW - 0.0008, -0.0125)), M_STEEL, bevel=0.0007)
    finish(hs.cyl_y("takedown", 0.0028, FRAME_HW * 2 + 0.002, (0.032, 0, -0.016), verts=20), M_STEEL, bevel=0.0004)
    for sy in (-1, 1):
        finish(hs.cyl_y(f"mag_release_{sy}", 0.0034, 0.0022, (-0.0215, sy * (FRAME_HW + 0.0003), -0.036), verts=24),
               M_STEEL, bevel=0.0004)

    # Fire-Control Link readout + palm contact strips (positions from v1, the arms expect them).
    finish(hs.box("fcl_readout", (0.022, 0.0012, 0.0055), (-0.050, -FRAME_HW - 0.0004, -0.0175)), M_GLASS, bevel=0.0003)
    for i, w in enumerate((0.004, 0.007, 0.0025, 0.005)):
        finish(hs.box(f"fcl_seg{i}", (w, 0.0004, 0.0011), (-0.058 + i * 0.0052 + w / 2, -FRAME_HW - 0.0011, -0.0168)),
               M_AMBER, bevel=0)
    finish(hs.box("fcl_bar", (0.016, 0.0004, 0.0006), (-0.052, -FRAME_HW - 0.0011, -0.0192)), M_AMBER, bevel=0)
    for i in range(3):
        h = 0.012 + i * 0.019
        p = grip_point(h, 180, -0.0003)  # seated into the curved backstrap
        # hs.box bakes its location into the mesh, so build at the origin, then place and turn it.
        pad = hs.box(f"palm_pad{i}", (0.0012, 0.009, 0.006), (0, 0, 0))
        pad.location = p
        pad.rotation_euler = (0, math.radians(20), 0)  # thin axis along the backstrap normal
        finish(pad, M_PAD, bevel=0.0003)

    # Magazine baseplate with a finger lip (moves on reload).
    part("magazine")
    base = hs.loft_x("mag_base", [(-0.1150, -0.1365, -0.1455, 0.0118), (-0.1110, -0.1360, -0.1465, 0.0138),
                                  (-0.0640, -0.1360, -0.1465, 0.0138), (-0.0580, -0.1365, -0.1445, 0.0122),
                                  (-0.0555, -0.1380, -0.1425, 0.0092)], power=4.0)
    finish(base, M_STEEL, bevel=0.0005, angle=40)
    part("body")


# ---------------------------------------------------------------- barrel and suppressor
def build_suppressor():
    finish(hs.cyl_x("barrel", 0.0066, 0.080, 0.106, verts=32), M_STEEL, bevel=0.0003)
    finish(hs.box("barrel_hood", (0.033, 0.0105, 0.004), (0.012, 0.003, 0.0145)), M_STEEL, bevel=0.0004)
    collar = hs.cyl_x("can_collar", 0.0196, X_COLLAR0, X_COLLAR1, verts=6, fixed=True)
    collar.rotation_euler = (math.radians(30), 0, 0)
    finish(collar, M_CAN, bevel=0.0009, segments=2)

    tube = hs.cyl_x("can_tube", CAN_R, X_COLLAR1, X_TUBE1, verts=64)
    flute = hs.cyl_x("flute", 0.0028, 0.146, 0.236, verts=16, z=CAN_R + 0.0013)
    hs.radial_array(flute, 8, (0.146 + 0.236) / 2)
    hs.cut(tube, flute)
    hs.cut(tube, hs.box("can_flat", (0.050, 0.006, 0.02), (0.186, -CAN_R - 0.0016, 0.0)))
    finish(tube, M_CAN, bevel=0.0005)
    # Grip rings behind the flutes: raised, not cut (torus cuts deleted the whole tube at LOW resolution).
    for i in range(3):
        x = 0.1295 + i * 0.0038
        finish(hs.lathe_x(f"can_ring{i}", [(x, CAN_R - 0.0002), (x + 0.0003, CAN_R + 0.0007), (x + 0.0017, CAN_R + 0.0007),
                                           (x + 0.002, CAN_R - 0.0002)], verts=64), M_CAN, bevel=0)

    finish(hs.cyl_x("can_band", CAN_R + 0.0003, 0.248, 0.252, verts=64), M_BAND, bevel=0.0002)
    cap = hs.lathe_x("can_cap", [(X_TUBE1, 0.0186), (X_CAP1 - 0.004, 0.0186), (X_CAP1, 0.0172)], verts=64)
    hs.cut(cap, hs.cyl_x("bore", 0.0042, X_TUBE1 - 0.01, X_CAP1 + 0.01, verts=24))
    notch = hs.box("crown_notch", (0.006, 0.004, 0.012), (X_CAP1, 0, 0.016))
    hs.radial_array(notch, 6, X_CAP1)
    hs.cut(cap, notch)
    finish(cap, M_CAN, bevel=0.0012, segments=3)

    finish(hs.box("can_plate", (0.042, 0.0008, 0.0085), (0.186, -CAN_R + 0.0013, 0.0)), M_SLIDE, bevel=0.0003)
    text("mark_can", "SR-57S  SUPPRESSOR", 0.0028, (0.1655, -CAN_R + 0.0008, -0.0009), (math.pi / 2, 0, 0), M_MARK)
    finish(hs.box("can_led", (0.0025, 0.0005, 0.0012), (0.2045, -CAN_R + 0.0007, 0.0024)), M_AMBER, bevel=0)


# ---------------------------------------------------------------- build / split / export
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_slide()
    build_frame()
    build_suppressor()
    bpy.ops.object.select_all(action="DESELECT")
    for ob in hs.PARTS:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = hs.PARTS[0]
    bpy.ops.object.convert(target="MESH")
    for ob in list(hs.PARTS):
        pid = PART_IDS[PART_OF.get(ob.name, "body")]
        attr = ob.data.attributes.new("part_id", "INT", "FACE")
        attr.data.foreach_set("value", [pid] * len(ob.data.polygons))
    joined = hs.join_parts(name)
    print(f"pistol_57 {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


def split_parts(low):
    objs = []
    for pname, pid in PART_IDS.items():
        ob = low.copy()
        ob.data = low.data.copy()
        ob.name = pname
        ob.data.name = pname
        scene.collection.objects.link(ob)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer = bm.faces.layers.int.get("part_id")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != pid], context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.attributes.remove(ob.data.attributes["part_id"])
        objs.append(ob)
        print(f"pistol_57: part {pname}: {bakeutil.tri_count(ob)} tris")
    bpy.data.objects.remove(low)
    return objs


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True,
                              export_image_format="AUTO", export_attributes=False)


# ---------------------------------------------------------------- preview
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
    nt = world.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.007, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.1, 0.105, 0.115, 1)
    nt.links.new(ramp.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    scene.world = world
    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0.09, 0, -0.16)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.5, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.06, 0, -0.04), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.25, -0.6, 0.55), 12, 0.7, sy=0.35)
    area("strip", (0.08, -0.05, 0.6), 6, 1.0, sy=0.1)
    area("fill", (0.6, -0.55, -0.05), 2.0, 0.8, (0.75, 0.85, 1.0))
    area("rim", (0.3, 0.6, 0.35), 8, 0.5, (1.0, 0.82, 0.62))
    area("kick", (-0.6, 0.2, 0.1), 3, 0.6)
    cam_data = bpy.data.cameras.new("cam")
    cam = hs.link(bpy.data.objects.new("cam", cam_data))
    scene.camera = cam
    return cam


def shoot(cam, path, loc, target, lens=50, fov_deg=None, fstop=0.0):
    d = cam.data
    if fov_deg:
        d.sensor_fit = "VERTICAL"
        d.angle = math.radians(fov_deg)
    else:
        d.sensor_fit = "AUTO"
        d.lens = lens
    d.dof.use_dof = fstop > 0
    if fstop:
        d.dof.aperture_fstop = fstop
        d.dof.focus_distance = (V(target) - V(loc)).length
    d.clip_start = 0.01
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"pistol_57: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shoot(cam, stem + "_side.png", (0.088, -0.97, 0.24), (0.088, 0, -0.058), lens=70, fstop=8.0)
    shoot(cam, stem + "_beauty.png", (0.33, -0.42, 0.20), (0.0, 0, -0.04), lens=50, fstop=5.6)
    shoot(cam, stem + "_detail.png", (0.11, -0.38, 0.12), (-0.04, 0, -0.045), lens=100, fstop=5.6)
    shoot(cam, stem + "_top.png", (-0.33, 0.10, 0.12), (0.05, 0, -0.01), lens=40, fstop=5.6)


# ---------------------------------------------------------------- run
if args.out:
    high = build(hs.HIGH, "pistol_57_high")
    low = build(hs.LOW, "pistol_57_low")
    # The slide and sights get the most texels (always in view), then the grip.
    bakeutil.unwrap(low, boost={M_SLIDE.name: 1.8, M_STEEL.name: 1.4, M_GRIP.name: 1.3, M_MARK.name: 1.6,
                                M_AMBER.name: 1.2})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "pistol_57", cage=0.0008, ray=0.003,
                                 ao_distance=0.015, grime=0.3, log=print)
    bpy.data.objects.remove(high)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "pistol_57", emission_strength=4.0)
    export(split_parts(low), args.out)
    print(f"pistol_57: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "pistol_57_high")
    render_previews(args.preview.rsplit(".", 1)[0])
