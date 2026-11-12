"""Glock 22: .40 S&W service pistol with a dropped-in auto sear ("switch") and a
22-round factory extended magazine (owner, 2026-11-12).

Built on the Five-seveN's grip frame (GRIP_TOP/AXIS, 25.5 x 15.5 mm half sizes)
so the first-person hands in raw_assets/characters/fp_arms/build.py close on it
the same way, and on the same sight line (z = 0.0262) so the ADS eye point in
data/weapons/glock22.tres still lines up. No suppressor: the muzzle is the slide
nose at x = 0.093.

Glock details: boxy flat-topped slide with a small top chamfer, straight rear
serrations, U-notch rear and dot front night sights (tritium green), barrel hood
in the ejection port and the crown in the square nose, polymer frame with finger
grooves, accessory rail, safe-action trigger with its blade, takedown tabs, left
magazine catch. The switch replaces the slide cover plate: a steel back plate
with a selector lever sticking out to the right. It moves with the slide.

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:  tools/blender.sh raw_assets/weapons/glock22/build.py \
        --out assets/weapons/glock22/glock22.gltf --tex 2048 --preview docs/previews/glock22.png
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


BLACK = (0.021, 0.021, 0.023)
BLACK_WEAR = (0.075, 0.075, 0.08)
M_SLIDE = mat("slide_nitride", (0.028, 0.029, 0.031), 0.4, 0.8, wear=(0.42, 0.42, 0.43), wear_rough=0.24,
              brushed=0.05, bump_scale=900, bump_strength=0.04)
M_FRAME = mat("frame_polymer", BLACK, 0.58, 0.0, wear=BLACK_WEAR, wear_rough=0.64, bump_scale=1600, bump_strength=0.12)
M_GRIP = stippled("grip_texture", BLACK, 0.74, BLACK_WEAR)
M_STEEL = mat("steel_dark", (0.06, 0.06, 0.065), 0.3, 1.0, wear=(0.5, 0.5, 0.52))
M_BARREL = mat("barrel_steel", (0.12, 0.12, 0.125), 0.28, 1.0, wear=(0.55, 0.55, 0.56))
M_WHITE = mat("sight_white", (0.75, 0.75, 0.72), 0.5, 0.0)
M_TRITIUM = mat("tritium", (0.3, 1.0, 0.35), 0.4, 0.0, emission=((0.3, 1.0, 0.32), 6.0))
M_MARK = mat("engraving", (0.34, 0.35, 0.36), 0.5, 1.0)
MATERIALS = [M_SLIDE, M_FRAME, M_GRIP, M_STEEL, M_BARREL, M_WHITE, M_TRITIUM, M_MARK]

# ---------------------------------------------------------------- dimensions (grip and sight line from the Five-seveN)
SLIDE_HALF = 0.01275
SLIDE_X0, SLIDE_X1 = -0.100, 0.093
FRAME_HW = 0.015
SIGHT_Z = 0.0262
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
    h = SLIDE_HALF
    slide = hs.section("slide", [(-h + 0.001, -0.010), (h - 0.001, -0.010), (h, -0.009), (h, 0.0165),
                                 (0.0105, 0.020), (-0.0105, 0.020), (-h, 0.0165), (-h, -0.009)], SLIDE_X0, SLIDE_X1)
    # Chamfered nose (top and underneath) and rear face.
    hs.cut(slide, hs.box("nose_under", (0.012, 0.05, 0.02), (SLIDE_X1 + 0.004, 0, -0.015), (0, math.radians(-40), 0)))
    hs.cut(slide, hs.box("nose_top", (0.008, 0.05, 0.02), (SLIDE_X1 + 0.003, 0, 0.026), (0, math.radians(40), 0)))
    hs.cut(slide, hs.box("rear_bevel", (0.008, 0.05, 0.02), (SLIDE_X0 - 0.003, 0, 0.026), (0, math.radians(-40), 0)))
    # Muzzle opening, ejection port.
    hs.cut(slide, hs.cyl_x("slide_bore", 0.0068, 0.080, SLIDE_X1 + 0.01, verts=32))
    hs.cut(slide, hs.box("ejection_port", (0.034, 0.012, 0.012), (0.012, 0.009, 0.019)))
    # Straight rear serrations.
    s = hs.box("rear_serr", (0.0016, 0.0026, 0.020), (-0.094, h + 0.0001, 0.003))
    hs.linear_array(s, 8, (0.004, 0, 0))
    hs.mirror_y(s)
    hs.cut(slide, s)
    finish(slide, M_SLIDE, bevel=0.0006)

    # U-notch rear sight and dot front sight on the same line as the Five-seveN (z = 0.0262).
    rear = hs.box("rear_sight", (0.009, 0.020, 0.0075), (-0.088, 0, 0.0235))
    hs.cut(rear, hs.box("rear_notch", (0.02, 0.0036, 0.004), (-0.088, 0, 0.0275)))
    finish(rear, M_STEEL, bevel=0.0005)
    for sy in (-1, 1):
        finish(hs.box(f"rear_ring{sy}", (0.0004, 0.0032, 0.0032), (-0.0834, sy * 0.0048, 0.0247)), M_WHITE, bevel=0)
        finish(hs.box(f"rear_dot{sy}", (0.0004, 0.0015, 0.0015), (-0.0831, sy * 0.0048, 0.0247)), M_TRITIUM, bevel=0)
    front = hs.box("front_sight", (0.006, 0.0032, 0.0065), (0.084, 0, 0.0228))
    finish(front, M_STEEL, bevel=0.0004)
    finish(hs.box("front_ring", (0.0004, 0.003, 0.003), (0.0808, 0, 0.0243)), M_WHITE, bevel=0)
    finish(hs.box("front_dot", (0.0004, 0.0014, 0.0014), (0.0805, 0, 0.0243)), M_TRITIUM, bevel=0)

    # Extractor (right side).
    finish(hs.box("extractor", (0.020, 0.0012, 0.0038), (0.010, -h - 0.0004, 0.0065)), M_STEEL, bevel=0.0003)
    # The switch: back plate in place of the slide cover, selector lever out to the right.
    finish(hs.box("switch_plate", (0.0022, 0.0175, 0.019), (SLIDE_X0 - 0.0011, 0, 0.0025)), M_STEEL, bevel=0.0005)
    finish(hs.box("switch_body", (0.004, 0.009, 0.007), (SLIDE_X0 - 0.0035, -0.004, 0.006)), M_STEEL, bevel=0.0006)
    finish(hs.box("switch_lever", (0.0035, 0.012, 0.0032), (SLIDE_X0 - 0.0045, -0.0135, 0.008)), M_STEEL, bevel=0.0007)
    finish(hs.cyl_x("switch_pin", 0.0012, SLIDE_X0 - 0.007, SLIDE_X0 - 0.005, verts=12, z=0.006), M_BARREL, bevel=0)
    if hs.D["text"]:
        text("mark_left", "GLOCK 22", 0.0052, (-0.030, h + 0.0001, -0.0045), (math.pi / 2, 0, math.pi), M_MARK)
        text("mark_cal", "AUSTRIA  .40", 0.0034, (0.050, h + 0.0001, -0.0055), (math.pi / 2, 0, math.pi), M_MARK)
    part("body")


# ---------------------------------------------------------------- frame and grip
def build_frame():
    # Dust cover: squared, slightly rounded underneath, ends short of the slide nose.
    upper = hs.loft_x("frame_upper", [(-0.100, -0.0095, -0.022, 0.0135), (-0.088, -0.0095, -0.0305, 0.0150),
                                      (0.000, -0.0095, -0.0305, 0.0150), (0.046, -0.0095, -0.0295, 0.0150),
                                      (0.078, -0.0095, -0.0285, 0.0148), (0.086, -0.0105, -0.0250, 0.0132)],
                      power=5.0)
    finish(upper, M_FRAME, bevel=0.0008, angle=40)

    stations = []
    for hh, sd, sw in ((-0.032, 0.92, 0.94), (-0.012, 0.97, 0.97), (0.030, 1.0, 1.0), (0.060, 1.0, 1.0),
                       (0.082, 1.02, 1.03), (0.104, 1.03, 1.04)):
        stations.append((GRIP_TOP + AXIS * hh, FWD, RIGHT, GRIP_HD * sd, GRIP_HW * sw))
    grip = hs.loft("grip", stations, power=2.8)
    for i, hh in enumerate((0.031, 0.050, 0.068)):
        c = GRIP_TOP + AXIS * hh + FWD * (GRIP_HD + 0.0062)
        hs.cut(grip, hs.cyl_y(f"finger_groove{i}", 0.0072, 0.06, tuple(c), verts=32))
    hs.cut(grip, hs.box("grip_floor", (0.12, 0.06, 0.04), (-0.085, 0, -0.1372 - 0.02)))
    finish(grip, M_GRIP, bevel=0.0012, segments=2, angle=50)

    # Short tang over the web of the hand.
    tang = hs.loft_x("tang", [(-0.082, -0.0100, -0.036, 0.0140), (-0.098, -0.0105, -0.0315, 0.0130),
                              (-0.106, -0.0125, -0.0265, 0.0100), (-0.109, -0.0150, -0.0235, 0.0050)], power=3.0)
    finish(tang, M_FRAME, bevel=0.0)

    guard = hs.tube_path("trigger_guard", [(-0.026, 0, -0.050), (-0.014, 0, -0.0585), (0.012, 0, -0.0592),
                                           (0.034, 0, -0.0585), (0.0425, 0, -0.0525), (0.0425, 0, -0.038),
                                           (0.041, 0, -0.028)], 0.0034, width_scale=2.4)
    finish(guard, M_FRAME, bevel=0.0, smooth=True)
    rail = hs.box("rail", (0.034, 0.019, 0.0045), (0.064, 0, -0.0305))
    slot = hs.box("rail_slot", (0.0028, 0.03, 0.003), (0.054, 0, -0.0328))
    hs.linear_array(slot, 3, (0.0095, 0, 0))
    hs.cut(rail, slot)
    finish(rail, M_FRAME, bevel=0.0004)

    # Safe-action trigger and its blade; slide stop, takedown tabs, left magazine catch.
    finish(hs.side_profile("trigger", [(0.012, -0.029), (0.018, -0.029), (0.0165, -0.037), (0.019, -0.046),
                                       (0.021, -0.051), (0.0155, -0.0535), (0.0105, -0.045), (0.008, -0.037)], 0.0058),
           M_FRAME, bevel=0.0007, angle=30)
    finish(hs.box("trigger_blade", (0.004, 0.0018, 0.012), (0.0148, 0, -0.043), (0, math.radians(-14), 0)),
           M_STEEL, bevel=0.0003)
    finish(hs.box("slide_stop", (0.018, 0.0022, 0.004), (-0.022, FRAME_HW + 0.0007, -0.0125)), M_STEEL, bevel=0.0006)
    finish(hs.box("takedown", (0.008, FRAME_HW * 2 + 0.002, 0.0028), (0.030, 0, -0.0165)), M_STEEL, bevel=0.0005)
    finish(hs.box("mag_catch", (0.007, 0.0022, 0.0065), (-0.0215, FRAME_HW + 0.0004, -0.036)), M_FRAME, bevel=0.0006)

    # Magazine: 22-round extended body out of the grip along the rake, then the baseplate (moves on reload).
    part("magazine")
    mag = hs.loft("mag_body", [(GRIP_TOP + AXIS * hh, FWD, RIGHT, 0.0168, 0.0112)
                               for hh in (0.088, 0.110, 0.137)], power=3.5)
    hs.cut(mag, hs.box("mag_floor", (0.12, 0.06, 0.04), (-0.10, 0, -0.1765 - 0.02)))
    holes = hs.cyl_y("witness", 0.0016, 0.04, tuple(GRIP_TOP + AXIS * 0.145 - FWD * 0.0105), verts=12)
    hs.cut(mag, holes)
    finish(mag, M_STEEL, bevel=0.0006, angle=40)
    dx, dz = -0.0141, -0.0400
    base = hs.loft_x("mag_base", [(x + dx, t + dz, b + dz, w) for x, t, b, w in (
        (-0.1150, -0.1365, -0.1455, 0.0118), (-0.1110, -0.1360, -0.1465, 0.0136),
        (-0.0640, -0.1360, -0.1465, 0.0136), (-0.0580, -0.1365, -0.1445, 0.0120),
        (-0.0555, -0.1380, -0.1425, 0.0090))], power=4.0)
    finish(base, M_FRAME, bevel=0.0005, angle=40)
    part("body")


# ---------------------------------------------------------------- barrel
def build_barrel():
    barrel = hs.cyl_x("barrel", 0.0064, 0.0, SLIDE_X1 - 0.0015, verts=32)
    hs.cut(barrel, hs.cyl_x("bore", 0.0051, 0.05, SLIDE_X1 + 0.01, verts=24))
    finish(barrel, M_BARREL, bevel=0.0003)
    finish(hs.box("barrel_hood", (0.033, 0.0105, 0.004), (0.012, 0.003, 0.0145)), M_BARREL, bevel=0.0004)
    if hs.D["text"]:
        text("mark_hood", "40", 0.003, (0.006, 0.003, 0.0166), (0, 0, 0), M_MARK)


# ---------------------------------------------------------------- build / split / export
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_slide()
    build_frame()
    build_barrel()
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
    print(f"glock22 {detail['name']}: {bakeutil.tri_count(joined)} tris")
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
        print(f"glock22: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    floor.location = (0.0, 0, -0.19)
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
    print(f"glock22: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shoot(cam, stem + "_side.png", (-0.005, -0.80, 0.18), (-0.005, 0, -0.075), lens=70, fstop=8.0)
    shoot(cam, stem + "_beauty.png", (0.26, -0.36, 0.14), (-0.02, 0, -0.06), lens=50, fstop=5.6)
    shoot(cam, stem + "_detail.png", (-0.30, -0.22, 0.10), (-0.09, 0, 0.0), lens=100, fstop=5.6)
    shoot(cam, stem + "_top.png", (-0.33, 0.10, 0.12), (0.05, 0, -0.01), lens=40, fstop=5.6)


# ---------------------------------------------------------------- run
if args.out:
    high = build(hs.HIGH, "glock22_high")
    low = build(hs.LOW, "glock22_low")
    # The slide and sights get the most texels (always in view), then the grip.
    bakeutil.unwrap(low, boost={M_SLIDE.name: 1.8, M_STEEL.name: 1.4, M_GRIP.name: 1.3, M_MARK.name: 1.6,
                                M_TRITIUM.name: 1.2})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "glock22", cage=0.0008, ray=0.003,
                                 ao_distance=0.015, grime=0.3, log=print)
    bpy.data.objects.remove(high)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "glock22", emission_strength=4.0)
    export(split_parts(low), args.out)
    print(f"glock22: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "glock22_high")
    render_previews(args.preview.rsplit(".", 1)[0])
