"""SL-9 "Slagger": a plasma pistol, the first energy weapon (owner, 2026-11-18).

Owner brief: "a small pistol, it needs an almost makeshift or industrial look,
a hybrid of a pistol frame and some kind of industrial welder. It requires
charge before firing ... angry orange almost stellar looking red orange
plasma at the tip, barely contained by a magnetic field."

Design reading: a polymer pistol frame (the Five-seveN's grip line, so the
shared pistol hands close on it) with the slide gone; bolted on top, the
guts of a plasma cutter in a chipped safety-yellow housing: welded seams,
cooling fins, a pressure gauge, a braided feed hose looping to the front.
Out front, a scorched torch nozzle inside three copper containment coils
and an open emitter cup: the plasma gathers just ahead of it (the game
draws it, src/vfx/plasma_charge.gd). The power cell is the grip's magazine,
wrapped in friction tape. Real proportions: about 230 mm long.

Parts (per-face part id, split after the bake):
  body      everything that doesn't move
  magazine  the power cell (drops during a reload)
  glow      the coil windows and vent slits (self-lit; the game sets colour
            and brightness from the charge)

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis
above the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/slagger/build.py --out assets/weapons/slagger/slagger.gltf --tex 2048 \
      --preview /tmp/slagger.png
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
ap.add_argument("--emission-size", type=int, default=256)
ap.add_argument("--preview", default="", help="preview stem")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material

# ---------------------------------------------------------------- materials
M_FRAME = mat("frame_polymer", (0.03, 0.031, 0.032), 0.6, 0.0, wear=(0.1, 0.1, 0.1), wear_rough=0.5,
              bump_scale=1600, bump_strength=0.12)
M_TAPE = mat("friction_tape", (0.018, 0.018, 0.017), 0.92, 0.0, bump_scale=700, bump_strength=0.35)
M_PAINT = mat("safety_yellow", (0.62, 0.42, 0.05), 0.55, 0.0, wear=(0.2, 0.2, 0.2), wear_rough=0.35,
              bump_scale=900, bump_strength=0.08)
M_STEEL = mat("raw_steel", (0.28, 0.28, 0.29), 0.42, 1.0, wear=(0.55, 0.55, 0.56), wear_rough=0.25, brushed=0.05)
M_SCORCH = mat("scorched_steel", (0.035, 0.03, 0.03), 0.55, 0.9, wear=(0.25, 0.18, 0.12), wear_rough=0.4,
               bump_scale=1300, bump_strength=0.1)
M_COPPER = mat("copper_coil", (0.75, 0.38, 0.2), 0.3, 1.0, brushed=0.05)
M_CERAMIC = mat("ceramic", (0.62, 0.6, 0.55), 0.6, 0.0)
M_HOSE = mat("braided_hose", (0.05, 0.05, 0.055), 0.65, 0.4, bump_scale=2400, bump_strength=0.4)
M_DARK = mat("vent_dark", (0.004, 0.004, 0.005), 0.8, 0.0)
M_GAUGE = mat("gauge_face", (0.85, 0.83, 0.76), 0.4, 0.0)
M_RED = mat("needle_red", (0.6, 0.04, 0.03), 0.4, 0.0)
M_MARK = mat("stencil", (0.04, 0.035, 0.03), 0.6, 0.0)
M_GLOW = mat("glow_window", (0.9, 0.4, 0.1), 0.3, 0.0, emission=((1.0, 0.4, 0.08), 6.0))
MATERIALS = [M_FRAME, M_TAPE, M_PAINT, M_STEEL, M_SCORCH, M_COPPER, M_CERAMIC, M_HOSE, M_DARK, M_GAUGE, M_RED,
             M_MARK, M_GLOW]
M_PARK = M_STEEL

PART_IDS = {"body": 0, "magazine": 1, "glow": 2}
CURRENT = ["body"]
PART_OF = {}

GRIP_TOP = V((-0.054, 0.0, -0.050))
AXIS = V((-0.029, 0.0, -0.080)).normalized()
FWD = V((-AXIS.z, 0.0, AXIS.x))
RIGHT = V((0.0, -1.0, 0.0))
GRIP_HD, GRIP_HW = 0.0255, 0.0155
SIGHT_Z = 0.046
HOUSE_X0, HOUSE_X1 = -0.104, 0.062
EMIT_X = 0.165             # the plasma gathers here (WeaponData.muzzle_point)


def part(name):
    CURRENT[0] = name


def high():
    return hs.D["name"] == "high"


def finish(ob, m, lb=True, **kw):
    """lb=False: no bevel on the LOW mesh (small repeated parts; the bake carries it)."""
    PART_OF[ob.name] = CURRENT[0]
    if not lb and not high():
        kw["bevel"] = 0
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m):
    ob = hs.text(name, body, size, loc, rot, m)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def at_x(stations, x):
    for a, b in zip(stations[:-1], stations[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(x if i == 0 else a[i] + (b[i] - a[i]) * t for i in range(4))
    return stations[0] if x < stations[0][0] else stations[-1]


def between(stations, x0, x1):
    return [at_x(stations, x0)] + [s for s in stations if x0 < s[0] < x1] + [at_x(stations, x1)]


def axis_loft(name, top, axis, st, power=2.3):
    """Loft along a (tilted) grip axis: st = [(h, half depth, half width)]."""
    axis = V(axis).normalized()
    fwd = V((-axis.z, 0.0, axis.x))
    right = V((0.0, -1.0, 0.0))
    return hs.loft(name, [(V(top) + axis * h, fwd, right, hd, hw) for h, hd, hw in st], power=power)


# ---------------------------------------------------------------- frame and grip (on the Five-seveN's line)
def build_frame():
    upper = hs.loft_x("frame_upper", [(-0.100, -0.0095, -0.022, 0.0135), (-0.088, -0.0095, -0.0305, 0.0150),
                                      (0.000, -0.0095, -0.0305, 0.0150), (0.046, -0.0095, -0.0290, 0.0150),
                                      (0.070, -0.0095, -0.0268, 0.0146), (0.078, -0.0105, -0.0235, 0.0128)], power=4.0)
    finish(upper, M_FRAME, bevel=0.0008, angle=40)
    stations = []
    for h, sd, sw in ((-0.032, 0.92, 0.94), (-0.012, 0.97, 0.97), (0.030, 1.0, 1.0), (0.060, 1.0, 1.0),
                      (0.082, 1.02, 1.03), (0.104, 1.02, 1.03)):
        stations.append((GRIP_TOP + AXIS * h, FWD, RIGHT, GRIP_HD * sd, GRIP_HW * sw))
    grip = hs.loft("grip", stations, power=2.3)
    hs.cut(grip, hs.box("grip_floor", (0.12, 0.06, 0.04), (-0.085, 0, -0.1372 - 0.02)))
    finish(grip, M_FRAME, bevel=0.0012, segments=2, angle=50)
    # Friction tape wrapped round the grip in three bands (makeshift).
    for i, (h0, h1) in enumerate(((0.012, 0.030), (0.036, 0.054), (0.060, 0.078))):
        c0 = GRIP_TOP + AXIS * h0
        c1 = GRIP_TOP + AXIS * h1
        band = hs.loft(f"tape{i}", [(c0, FWD, RIGHT, GRIP_HD + 0.0012, GRIP_HW + 0.0012),
                                    (c1, FWD, RIGHT, GRIP_HD + 0.0014, GRIP_HW + 0.0014)], power=2.3)
        finish(band, M_TAPE, bevel=0.0006)
    finish(hs.loft_x("beavertail", [(-0.082, -0.0100, -0.036, 0.0145), (-0.098, -0.0105, -0.0315, 0.0135),
                                    (-0.108, -0.0125, -0.0255, 0.0110), (-0.1125, -0.0165, -0.0215, 0.0065)], power=3.0),
           M_FRAME, bevel=0.0)
    guard = hs.tube_path("trigger_guard", [(-0.026, 0, -0.050), (-0.014, 0, -0.0585), (0.012, 0, -0.0592),
                                           (0.036, 0, -0.0578), (0.0425, 0, -0.0505), (0.0435, 0, -0.038),
                                           (0.042, 0, -0.027)], 0.0034, width_scale=2.3)
    finish(guard, M_FRAME, bevel=0.0, smooth=True)
    finish(hs.side_profile("trigger", [(0.012, -0.029), (0.018, -0.029), (0.0165, -0.037), (0.019, -0.046),
                                       (0.021, -0.051), (0.0155, -0.0535), (0.0105, -0.045), (0.008, -0.037)], 0.0055),
           M_STEEL, bevel=0.0007, angle=30)
    # A hose clamp holding the housing's earth strap to the frame (it's a welder).
    finish(hs.loft_x("clamp", [(0.020, -0.006, -0.032, 0.0158), (0.028, -0.006, -0.032, 0.0158)], power=6.0), M_STEEL,
           bevel=0.0004)
    finish(hs.box("clamp_screw", (0.008, 0.006, 0.006), (0.024, -0.0175, -0.020)), M_STEEL, bevel=0.0006)


# ---------------------------------------------------------------- the welder housing on top
def build_housing():
    house = hs.loft_x("housing", [(HOUSE_X0, 0.026, -0.010, 0.0150), (HOUSE_X0 + 0.010, 0.034, -0.010, 0.0168),
                                  (HOUSE_X1 - 0.012, 0.034, -0.010, 0.0168), (HOUSE_X1, 0.024, -0.010, 0.0150)], power=7.0)
    finish(house, M_PAINT, bevel=0.0012)
    # Welded seam along the top edges and a bead at the front.
    for sy in (1, -1):
        finish(hs.cyl_x(f"seam{sy}", 0.0013, HOUSE_X0 + 0.01, HOUSE_X1 - 0.012, verts=8, y=sy * 0.0160, z=0.033),
               M_SCORCH, bevel=0)
    # Cooling fins on both sides, a vent slit between each (glows when hot).
    for i in range(7):
        x = -0.07 + i * 0.012
        for sy in (1, -1):
            finish(hs.box(f"fin{i}{sy}", (0.0035, 0.004, 0.026), (x, sy * 0.0185, 0.012)), M_STEEL, bevel=0.0004, lb=False)
    part("glow")
    for i in range(6):
        x = -0.064 + i * 0.012
        for sy in (1, -1):
            finish(hs.box(f"slit{i}{sy}", (0.004, 0.0008, 0.018), (x, sy * 0.0169, 0.012)), M_GLOW, bevel=0)
    part("body")
    # Bolts at the corners, a stencilled warning, a sight notch and post.
    for x in (HOUSE_X0 + 0.008, HOUSE_X1 - 0.010):
        for sy in (1, -1):
            finish(hs.cyl_y(f"bolt{x}{sy}", 0.0028, 0.002, (x, sy * 0.0172, 0.026), verts=6), M_STEEL, bevel=0.0003)
    text("mark_name", "SL-9", 0.007, (-0.030, 0.0169, 0.022), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_warn", "HIGH VOLTAGE", 0.0032, (-0.034, -0.0169, 0.024), (math.pi / 2, 0, 0), M_MARK)
    finish(hs.box("rear_sight", (0.010, 0.020, 0.010), (-0.092, 0, 0.039)), M_STEEL, bevel=0.0006)
    finish(hs.box("rear_notch", (0.012, 0.004, 0.006), (-0.092, 0, 0.044)), M_DARK, bevel=0)
    finish(hs.box("front_post", (0.004, 0.003, 0.012), (0.052, 0, 0.040)), M_STEEL, bevel=0.0003)
    # Capacitor can on the right, pressure gauge on the left.
    finish(hs.cyl_x("cap_can", 0.0085, -0.085, -0.020, verts=24, y=-0.022, z=0.020), M_STEEL, bevel=0.0006)
    for i in range(4):
        finish(hs.cyl_x(f"cap_band{i}", 0.0091, -0.078 + i * 0.016, -0.074 + i * 0.016, verts=24, y=-0.022, z=0.020),
               M_COPPER, bevel=0, lb=False)
    finish(hs.cyl_y("gauge_body", 0.0105, 0.010, (-0.050, 0.023, 0.026), verts=28), M_STEEL, bevel=0.0007)
    finish(hs.cyl_y("gauge_face", 0.0088, 0.0012, (-0.050, 0.0285, 0.026), verts=28), M_GAUGE, bevel=0)
    needle = hs.box("gauge_needle", (0.0075, 0.0008, 0.0012), (0.0, 0.0, 0.0))
    needle.location = (-0.0475, 0.0293, 0.0275)
    needle.rotation_euler = (0.0, -0.6, 0.0)
    finish(needle, M_RED, bevel=0)
    # The feed hose: from the back of the housing, round the left, into the torch.
    hose = hs.tube_path("hose", [V((-0.098, 0.012, 0.005)), V((-0.105, 0.030, 0.015)), V((-0.06, 0.036, 0.040)),
                                 V((0.010, 0.030, 0.046)), V((0.060, 0.022, 0.030)), V((0.078, 0.010, 0.018))], 0.0045,
                        resolution=14)
    finish(hose, M_HOSE, bevel=0, smooth=True)
    for x, y, z in ((-0.101, 0.020, 0.008), (0.074, 0.013, 0.021)):
        finish(hs.cyl_between(f"ferrule{x}", V((x - 0.004, y, z)), V((x + 0.004, y, z)), 0.0058, verts=16), M_COPPER, bevel=0.0004)


# ---------------------------------------------------------------- torch and containment coils
def build_emitter():
    # Torch body: steel collar off the housing, then a scorched nozzle.
    finish(hs.lathe_x("collar", [(HOUSE_X1 - 0.004, 0.0), (HOUSE_X1 - 0.004, 0.0135), (HOUSE_X1 + 0.012, 0.0135),
                                 (HOUSE_X1 + 0.014, 0.011)], verts=32), M_STEEL, bevel=0.0006)
    finish(hs.lathe_x("nozzle", [(0.074, 0.011), (0.078, 0.0115), (0.128, 0.0098), (0.140, 0.0072), (0.144, 0.0048)],
                      verts=32), M_SCORCH, bevel=0.0005)
    finish(hs.lathe_x("insulator", [(0.140, 0.0049), (0.146, 0.0042), (0.149, 0.0030)], verts=20), M_CERAMIC, bevel=0)
    finish(hs.cyl_x("electrode", 0.0016, 0.145, 0.153, verts=12), M_COPPER, bevel=0)
    # Three containment coils: copper windings on a steel former, a window glowing between turns.
    for i, x in enumerate((0.086, 0.104, 0.122)):
        r = 0.0185 - i * 0.0012
        finish(hs.lathe_x(f"coil{i}", [(x - 0.006, r - 0.004), (x - 0.006, r), (x + 0.006, r), (x + 0.006, r - 0.004)],
                          verts=36), M_COPPER, bevel=0.0004)
        for k in range(5):
            xx = x - 0.0048 + k * 0.0024
            finish(hs.lathe_x(f"turn{i}{k}", [(xx - 0.0008, r), (xx - 0.0006, r + 0.0009), (xx + 0.0006, r + 0.0009),
                                               (xx + 0.0008, r)], verts=36), M_COPPER, bevel=0, lb=False)
        part("glow")
        finish(hs.lathe_x(f"coil_window{i}", [(x + 0.0062, r - 0.0035), (x + 0.0062, r - 0.0005), (x + 0.0072, r - 0.0005),
                                               (x + 0.0072, r - 0.0035)], verts=36), M_GLOW, bevel=0)
        part("body")
    # Three standoff rods tying the coils, and the open emitter cup they hold.
    for k in range(3):
        a = k * 2 * math.pi / 3 + math.pi / 2
        y, z = math.cos(a) * 0.0205, math.sin(a) * 0.0205
        finish(hs.cyl_between(f"rod{k}", V((0.074, y, z)), V((0.150, y, z)), 0.0016, verts=8), M_STEEL, bevel=0)
    cup = hs.cyl_x("cup", 0.0235, 0.146, 0.1555, verts=40)
    hs.cut(cup, hs.cyl_x("cup_bore", 0.0185, 0.140, 0.162, verts=40, fixed=True))
    finish(cup, M_SCORCH, bevel=0.0006)
    part("glow")
    lip = hs.cyl_x("cup_lip", 0.0212, 0.1553, 0.1563, verts=40)
    hs.cut(lip, hs.cyl_x("lip_bore", 0.0188, 0.150, 0.160, verts=40, fixed=True))
    finish(lip, M_GLOW, bevel=0)
    part("body")


# ---------------------------------------------------------------- power cell (the magazine)
def build_cell():
    part("magazine")
    st = []
    for h, k in ((0.0, 0.9), (0.10, 0.9), (0.112, 1.0)):
        st.append((GRIP_TOP + AXIS * h + V((0.0, 0.0, -0.002)), FWD, RIGHT, GRIP_HD * 0.62 * k, GRIP_HW * 0.62 * k))
    cell = hs.loft("cell", st, power=3.0)
    finish(cell, M_STEEL, bevel=0.0006)
    base = GRIP_TOP + AXIS * 0.112
    finish(hs.loft("cell_cap", [(base, FWD, RIGHT, GRIP_HD * 1.04, GRIP_HW * 1.06),
                                (base + AXIS * 0.012, FWD, RIGHT, GRIP_HD * 1.0, GRIP_HW * 1.02)], power=3.0), M_PAINT,
           bevel=0.0012)
    part("glow")
    finish(hs.box("cell_led", (0.010, 0.0015, 0.003), tuple(base + AXIS * 0.006 + V((0.0, -0.017, 0.0)))), M_GLOW, bevel=0)
    part("body")


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_frame()
    build_housing()
    build_emitter()
    build_cell()
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
    print(f"slagger {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


def split_parts(low):
    objs = []
    for pname, pid in PART_IDS.items():
        ob = low.copy()
        ob.data = low.data.copy()
        ob.name = pname
        ob.data.name = pname
        bpy.context.scene.collection.objects.link(ob)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer = bm.faces.layers.int.get("part_id")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != pid], context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.attributes.remove(ob.data.attributes["part_id"])
        objs.append(ob)
        print(f"slagger: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.008, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.12, 0.125, 0.135, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world
    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, -0.16)
    floor.data.materials.append(mat("floor", (0.03, 0.031, 0.033), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.25, 0, -0.04), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.2, -1.3, 1.1), 55, 1.8, sy=0.5)
    area("strip_top", (0.25, 0.0, 1.1), 35, 2.4, sy=0.18)
    area("fill", (0.6, 1.4, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.7, -0.4, 0.5), 50, 0.8, (1.0, 0.85, 0.7))
    area("kick", (-1.3, 0.3, 0.2), 30, 1.0, (0.8, 0.9, 1.0))
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
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
    print(f"slagger: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((0.03, -0.75, -0.01), (0.03, 0, -0.03), 55, 0.0),
        "beauty": ((0.40, -0.42, 0.18), (0.02, 0, -0.02), 45, 5.0),
        "left": ((-0.18, 0.42, 0.14), (0.04, 0, -0.02), 40, 5.0),
        "detail": ((0.20, -0.20, 0.06), (0.10, 0.0, 0.0), 50, 3.0),
        "fp": ((-0.32, -0.02, 0.10), (0.6, 0.06, -0.08), 0, 0.0),
    }
    only = [s for s in args.only.split(",") if s]
    for key, (loc, target, lens, fstop) in shots.items():
        if only and key not in only:
            continue
        if key == "fp":
            shoot(cam, f"{stem}_{key}.png", loc, target, fov_deg=60)
        else:
            shoot(cam, f"{stem}_{key}.png", loc, target, lens=lens, fstop=fstop)


# ---------------------------------------------------------------- run
if args.out:
    high_ob = build(hs.HIGH, "slagger_high")
    low = build(hs.LOW, "slagger_low")
    bakeutil.unwrap(low, boost={M_FRAME.name: 0.9, M_PAINT.name: 1.2, M_STEEL.name: 1.3, M_MARK.name: 1.6,
                                M_COPPER.name: 1.3, M_GAUGE.name: 1.6})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high_ob, low, MATERIALS, args.tex, tex_dir, "slagger", cage=0.0012, ray=0.004,
                                 ao_distance=0.025, grime=0.35, log=print)
    bpy.data.objects.remove(high_ob)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "slagger", emission_strength=4.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"slagger: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "slagger_high")
    render_previews(args.preview.rsplit(".", 1)[0])
