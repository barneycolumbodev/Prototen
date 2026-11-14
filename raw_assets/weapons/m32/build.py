"""M32A1-pattern six-shot 40 mm revolving grenade launcher with a fire-control
sight (laser rangefinder + inductive fuze setter) for programmed airbursts.

Claude's choice (2026-11-14, design §4.8): the arsenal had no explosive
weapon; every gun fires straight-line bullets. This one throws 40x46 mm
low-velocity grenades in an arc, and when aimed the sight lases the range and
programs each round's fuze at the muzzle so it bursts just past the point
you lased: over a wall, onto the men behind it.

Built *(Claude's reading of the M32A1 pattern, not a measured copy)*:
  - Rear frame: recoil shield over the case heads, receiver with the double-
    action lockwork, the shared Pistol 57 grip profile and trigger guard (so the
    MG42 first-person arms fit unchanged), ambidextrous safety, sling swivel.
  - Six-chamber cylinder (40.6 mm chambers on a 46 mm pitch circle), fluted
    between the chambers, ratchet star, swinging out to the RIGHT on a crane
    hinged under it (the left hand is on the foregrip, the left forearm runs
    where a left swing-out would go).
  - Front frame with the barrel boss; top strap with a Picatinny rail joining the
    frames over the cylinder; lower frame bar carrying the crane hinge tube.
  - 300 mm rifled barrel, quad-rail handguard with vent slots, the MG42's
    clamp-on vertical foregrip in the same place.
  - FCS-40 sight: a tall reflex sight with a round window and a range drum on
    the left, a laser rangefinder pod (emitter and receiver lenses) under its
    nose on the right, and a cable forward along the handguard to the inductive
    fuze-setter ring at the muzzle.
  - Telescoping skeletal stock on a buffer tube, cheek riser, rubber pad.

Moving parts (separate nodes in the glTF, see src/player/viewmodel_rig.gd):
  body          everything that doesn't move
  crane         the yoke the cylinder swings out on (swing only)
  cylinder      the cylinder (swings out with the crane, indexes 60 deg a shot)
  round_0..5    a case head in each chamber (move with the cylinder; the game
                shows the live ones). Chamber 0 is at the top (on the bore).
  stock         hidden while aiming
  lens          sight glass (the game gives it a transparent material)
  reticle       the projected dot (the game colours it)
A second file, grenade_40mm.gltf, is the projectile seen in flight (+X = nose).

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis above
the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/m32/build.py --out assets/weapons/m32/m32.gltf --tex 2048 \
      --preview docs/previews/m32.png
  Fast look at the HIGH model (no bake): --preview /tmp/m32.png [--only side,fp] [--open 1]
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--emission-size", type=int, default=512)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
ap.add_argument("--open", type=float, default=0.0, help="preview with the cylinder swung out (0..1)")
ap.add_argument("--arms", default="", help="also import this arms glTF into the preview")
ap.add_argument("--reuse", action="store_true", help="with --out: skip the bake, render previews of the existing glTF")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
PI = math.pi

# ---------------------------------------------------------------- materials
# Dark olive-grey cerakote frame, hard-anodised black cylinder worn bright on
# the edges, blued barrel, black polymer furniture.
M_FRAME = mat("frame_cerakote", (0.034, 0.039, 0.029), 0.52, 0.25, wear=(0.38, 0.38, 0.36), wear_rough=0.28,
              bump_scale=1800, bump_strength=0.05)
M_ANOD = mat("black_anodised", (0.020, 0.021, 0.023), 0.36, 0.8, wear=(0.62, 0.62, 0.64), wear_rough=0.25,
             brushed=0.02, bump_scale=2200, bump_strength=0.03)
M_STEEL = mat("blued_steel", (0.026, 0.027, 0.030), 0.30, 1.0, wear=(0.5, 0.5, 0.52), wear_rough=0.2,
              brushed=0.04, bump_scale=1400, bump_strength=0.02)
M_BRIGHT = mat("bright_steel", (0.32, 0.32, 0.33), 0.26, 1.0, brushed=0.05)
M_POLY = mat("black_polymer", (0.021, 0.021, 0.023), 0.6, 0.0, wear=(0.1, 0.1, 0.11), wear_rough=0.45,
             bump_scale=1600, bump_strength=0.14)
M_STIPPLE = mat("stippled_polymer", (0.019, 0.019, 0.021), 0.72, 0.0, bump_scale=2600, bump_strength=0.75)
M_RUBBER = mat("rubber", (0.018, 0.018, 0.019), 0.85, 0.0, bump_scale=600, bump_strength=0.3)
M_BORE = mat("bore_dark", (0.008, 0.008, 0.009), 0.5, 1.0)
M_ALU_CASE = mat("aluminium_case", (0.62, 0.62, 0.6), 0.32, 1.0, wear=(0.8, 0.8, 0.78), wear_rough=0.2, brushed=0.04)
M_BRASS = mat("primer_brass", (0.8, 0.6, 0.3), 0.24, 1.0)
M_LENS = mat("lens_coated", (0.02, 0.012, 0.018), 0.04, 0.0, emission=((0.4, 0.1, 0.25), 0.2))
M_LRF = mat("lrf_lens", (0.06, 0.02, 0.09), 0.05, 0.3, emission=((0.5, 0.08, 0.6), 0.6))
M_RED = mat("reticle_lamp", (0.9, 0.08, 0.04), 0.3, 0.0, emission=((1.0, 0.1, 0.04), 8.0))
M_LED = mat("status_led", (0.1, 0.8, 0.5), 0.3, 0.0, emission=((0.1, 1.0, 0.55), 6.0))
M_MARK = mat("engraving", (0.5, 0.5, 0.5), 0.5, 0.6)
M_PAINT = mat("index_paint", (0.86, 0.84, 0.78), 0.6, 0.0)
M_REDPAINT = mat("red_paint", (0.62, 0.03, 0.02), 0.55, 0.0)
M_YELLOW = mat("warning_yellow", (0.85, 0.62, 0.04), 0.55, 0.0)
M_CABLE = mat("cable_jacket", (0.016, 0.016, 0.017), 0.7, 0.0, bump_scale=900, bump_strength=0.2)
MATERIALS = [M_FRAME, M_ANOD, M_STEEL, M_BRIGHT, M_POLY, M_STIPPLE, M_RUBBER, M_BORE, M_ALU_CASE, M_BRASS,
             M_LENS, M_LRF, M_RED, M_LED, M_MARK, M_PAINT, M_REDPAINT, M_YELLOW, M_CABLE]

# ---------------------------------------------------------------- dimensions
CY_Z = -0.046            # cylinder axis (the top chamber is on the bore)
PITCH = 0.046            # chamber pitch radius
CH_R = 0.0203            # chamber radius
CYL_R = 0.0715           # cylinder outer radius
CYL_X0, CYL_X1 = 0.057, 0.163
CRANE_X0, CRANE_X1 = 0.164, 0.170
FF_X0, FF_X1 = 0.164, 0.188   # front frame: the barrel boss (the lower front stays open for the crane)
RF_X0, RF_X1 = 0.038, 0.056   # recoil shield (the trigger guard runs into its back face)
HINGE_Z = CY_Z - 0.079   # crane hinge axis (y = 0)
REC_X0 = -0.112          # receiver back
REC_HW = 0.0175
STRAP_Z0, STRAP_Z1 = 0.0285, 0.0415
RAIL_Z = STRAP_Z1 + 0.0056
HG_X0, HG_X1 = 0.186, 0.412
HG_H = 0.0300            # handguard half size
BRL_R = 0.0245
BORE_R = 0.0200
URAIL_Z = -HG_H - 0.0056  # under rail face (-0.0356)
SIGHT_Z = 0.0900         # sight window centre (= the aimed eye height)
SX0, SX1 = 0.040, 0.114  # sight hood
WIN_R = 0.0185
MUZZLE_X = 0.486

PART_IDS = {"body": 0, "crane": 1, "cylinder": 2, "stock": 3, "lens": 4, "reticle": 5,
            "round_0": 6, "round_1": 7, "round_2": 8, "round_3": 9, "round_4": 10, "round_5": 11}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def hi():
    """True while building HIGH: fine detail LOW gets through the bake."""
    return hs.D["text"]


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m=M_MARK, extrude=0.00012):
    ob = hs.text(name, body, size, loc, rot, m, extrude=extrude)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def arc(cy, cz, r, a0, a1, n):
    """Points (y, z) on a circle from angle a0 to a1 (degrees, 0 = +Y, 90 = +Z)."""
    return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def chamber_yz(k):
    """Chamber k centre (y, z); 0 at the top, then clockwise seen from behind (toward -Y, the right).
    Firing turns the cylinder -60 deg about X, which brings chamber k + 1 to the top."""
    a = math.radians(60.0 * k)
    return (-PITCH * math.sin(a), CY_Z + PITCH * math.cos(a))


def facing(reading, up):
    """Euler rotation for text that reads along `reading` with `up` as its up (normal = reading x up)."""
    r, u = V(reading).normalized(), V(up).normalized()
    return Matrix((r, u, r.cross(u))).transposed().to_euler("XYZ")


def pic_profile(z_face, z_base):
    s = 1.0 if z_face > z_base else -1.0
    return [(-0.0078, z_base), (0.0078, z_base), (0.0078, z_face - s * 0.0056), (0.0106, z_face - s * 0.0028),
            (0.0078, z_face), (-0.0078, z_face), (-0.0106, z_face - s * 0.0028), (-0.0078, z_face - s * 0.0056)]


def pic_rail(name, x0, x1, z_face, z_base, m, first_slot, slots):
    """Picatinny rail along X on the top (z_face above z_base) or the bottom."""
    rail = hs.section(name, pic_profile(z_face, z_base), x0, x1)
    for i in range(slots):
        hs.cut(rail, hs.box(f"{name}_slot{i}", (0.00523, 0.03, 0.006), (first_slot + i * 0.010, 0, z_face)))
    return finish(rail, m, bevel=0.0004)


def screw(name, loc, axis, r, m=M_STEEL, proud=0.0008, slot="hex"):
    """A screw head with a dark socket; axis 'y+' / 'y-' / 'z+' / 'z-' / 'x+' / 'x-' = the way it faces."""
    x, y, z = loc
    sgn = 1.0 if axis[1] == "+" else -1.0
    if axis[0] == "y":
        finish(hs.cyl_y(name, r, proud, (x, y + sgn * proud / 2, z), verts=20), m, bevel=0.0003, segments=2)
        if hi():
            n = 6 if slot == "hex" else 20
            bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r * 0.55, depth=0.0003,
                                                location=(x, y + sgn * (proud + 0.00005), z), rotation=(PI / 2, 0, 0))
            s = bpy.context.active_object
            s.name = name + "_socket"
            finish(s, M_BORE, bevel=0, smooth=False)
    elif axis[0] == "z":
        finish(hs.cyl_z(name, r, proud, (x, y, z + sgn * proud / 2), verts=20), m, bevel=0.0003, segments=2)
        if hi():
            bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r * 0.55, depth=0.0003,
                                                location=(x, y, z + sgn * (proud + 0.00005)))
            s = bpy.context.active_object
            s.name = name + "_socket"
            finish(s, M_BORE, bevel=0, smooth=False)
    else:
        finish(hs.cyl_x(name, r, x, x + sgn * proud, verts=20, y=y, z=z), m, bevel=0.0003, segments=2)
        if hi():
            finish(hs.cyl_x(name + "_socket", r * 0.55, x + sgn * proud, x + sgn * (proud + 0.0002), verts=6,
                            fixed=True, y=y, z=z), M_BORE, bevel=0, smooth=False)


def lathe_loop(name, profile, verts=48):
    """Surface of revolution round X of a closed (x, r) loop: a tube wall with no end caps
    (hs.lathe_x caps both ends with discs, which would close a sight window or a bore)."""
    n = hs.nverts(verts)
    bm = bmesh.new()
    rings = []
    for x, r in profile:
        rings.append([bm.verts.new((x, r * math.cos(2 * PI * i / n), r * math.sin(2 * PI * i / n))) for i in range(n)])
    for ra, rb in zip(rings, rings[1:] + rings[:1]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def yz_plate(name, x0, x1, outline):
    """A plate along X from x0 to x1 with the (y, z) outline."""
    return hs.section(name, outline, x0, x1)


def disc_outline(cy, cz, r, n=None):
    n = n or (64 if hi() else 28)
    return arc(cy, cz, r, 0, 360, n)[:-1]


# ---------------------------------------------------------------- rear frame, receiver, lower
def grip_line(pts, z):
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        if z0 >= z >= z1:
            return x0 + (x1 - x0) * (z0 - z) / (z0 - z1)
    return pts[-1][0]


def build_rear_frame():
    # Recoil shield: covers the case heads, a firing-pin bushing on the bore, the hand
    # sweeps back into the receiver above and the trigger guard below.
    shield = yz_plate("recoil_shield", RF_X0, RF_X1, disc_outline(0.0, CY_Z, CYL_R - 0.0015))
    finish(shield, M_FRAME, bevel=0.0012)
    neck = hs.section("shield_neck", [(-0.026, -0.030), (0.026, -0.030), (0.026, STRAP_Z1), (-0.026, STRAP_Z1)],
                      RF_X0 - 0.004, RF_X1)
    finish(neck, M_FRAME, bevel=0.0015)
    finish(hs.cyl_x("firing_pin_bush", 0.0062, RF_X1 - 0.0006, RF_X1 + 0.0004, verts=24), M_BRIGHT, bevel=0.0002)
    if hi():
        finish(hs.cyl_x("firing_pin_hole", 0.0018, RF_X1 + 0.0004, RF_X1 + 0.0006, verts=12, fixed=True), M_BORE,
               bevel=0, smooth=False)
        # Machining rings on the shield face, cylinder-stop slot.
        for i, r in enumerate((0.030, 0.064)):
            bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=6, major_radius=r, minor_radius=0.0005,
                                             location=(RF_X1, 0, CY_Z), rotation=(0, PI / 2, 0))
            t = bpy.context.active_object
            t.name = f"shield_ring{i}"
            finish(t, M_BORE, bevel=0, smooth=False)
    # Receiver: the lockwork box behind the shield, sloping down into the grip.
    rec = hs.side_profile("receiver", [(REC_X0, STRAP_Z1), (RF_X0, STRAP_Z1), (RF_X0, -0.034), (-0.020, -0.034),
                                       (-0.090, -0.034), (-0.104, -0.026), (REC_X0, -0.010)], REC_HW * 2)
    finish(rec, M_FRAME, bevel=0.0020)
    # Side cover plates with the lockwork pins.
    for sy in (-1, 1):
        plate = hs.side_profile(f"rec_cover{sy}", [(-0.092, 0.030), (0.030, 0.030), (0.030, -0.028), (-0.080, -0.028),
                                                   (-0.092, -0.012)], 0.0016, y=sy * (REC_HW + 0.0006))
        hs.cut(plate, hs.side_profile(f"rec_pocket{sy}", [(-0.074, 0.022), (0.014, 0.022), (0.022, 0.014), (0.022, -0.016),
                                                          (0.014, -0.020), (-0.066, -0.020), (-0.074, -0.012)], 0.0016,
                                      y=sy * (REC_HW + 0.0016)))
        finish(plate, M_ANOD, bevel=0.0005)
        for i, (x, z) in enumerate(((-0.080, 0.018), (-0.010, 0.020), (0.020, -0.016), (-0.070, -0.016))):
            screw(f"rec_pin{sy}_{i}", (x, sy * (REC_HW + 0.0014), z), "y+" if sy > 0 else "y-", 0.0026, proud=0.0006,
                  slot="round")
    # Hammer spur peeking above the back of the receiver (double action only: bobbed).
    finish(hs.side_profile("hammer", [(-0.078, STRAP_Z1 - 0.002), (-0.058, STRAP_Z1 - 0.002), (-0.062, STRAP_Z1 + 0.006),
                                      (-0.076, STRAP_Z1 + 0.005)], 0.0090), M_STEEL, bevel=0.0008)
    # Ambidextrous safety: lever above the grip, S / F marks.
    for sy in (-1, 1):
        y = sy * (REC_HW + 0.0016)
        finish(hs.cyl_y(f"safety_pivot{sy}", 0.0058, 0.0030, (-0.046, y, 0.006), verts=24), M_STEEL, bevel=0.0007)
        lever = hs.box(f"safety_lever{sy}", (0.020, 0.0028, 0.0060), (0, 0, 0))
        a = math.radians(-28)
        lever.rotation_euler = (0, -a, 0)
        lever.location = (-0.046 + math.cos(a) * 0.009, sy * (REC_HW + 0.0030), 0.006 + math.sin(a) * 0.009)
        finish(lever, M_STEEL, bevel=0.0009)
        for nm, (dx, dz), m in (("S", (0.017, 0.016), M_PAINT), ("F", (0.019, -0.004), M_REDPAINT)):
            if hi():
                finish(hs.cyl_y(f"safety_dot_{nm}{sy}", 0.0017, 0.0003, (-0.046 + dx, sy * (REC_HW + 0.00015), 0.006 + dz),
                                verts=12), m, bevel=0)
            text(f"safety_txt_{nm}{sy}", nm, 0.0040, (-0.046 + dx + 0.004, sy * (REC_HW + 0.00005), 0.006 + dz - 0.002),
                 (PI / 2, 0, 0 if sy < 0 else PI), m=m)
    # Grip: the shared Pistol 57 front and back strap lines (as the MP5 and MG42).
    front = [(-0.0160, -0.0300), (-0.0170, -0.0330), (-0.0260, -0.0510), (-0.0560, -0.1340), (-0.0585, -0.1385)]
    back = [(-0.0890, -0.0300), (-0.0880, -0.0330), (-0.0810, -0.0460), (-0.1070, -0.1320), (-0.1055, -0.1385)]
    stations = []
    for i in range(15):
        z = -0.0300 - (0.1385 - 0.0300) * i / 14
        xf, xb = grip_line(front, z), grip_line(back, z)
        t = i / 14
        hw = 0.0152 + 0.0012 * math.sin(PI * min(1.0, t * 1.15))
        stations.append((((xf + xb) / 2, 0, z), (0, 1, 0), (1, 0, 0), hw, (xf - xb) / 2))
    finish(hs.loft("grip", stations, power=3.4), M_STIPPLE, bevel=0)
    for nm, line, sgn in (("grip_front_strap", front, 1), ("grip_back_strap", back, -1)):
        strap = []
        for i in range(12):
            z = -0.0400 - (0.1340 - 0.0400) * i / 11
            x = grip_line(line, z)
            strap.append(((x - sgn * 0.0016, 0, z), (0, 1, 0), (1, 0, 0), 0.0078, 0.0022))
        finish(hs.loft(nm, strap, n=16 if hi() else 8, power=2.6), M_POLY, bevel=0)
    cap = []
    for z, g in ((-0.1366, 0.0004), (-0.1385, 0.0016), (-0.1432, 0.0016), (-0.1448, 0.0002)):
        zz = max(z, -0.1385)
        xf, xb = grip_line(front, zz), grip_line(back, zz)
        cap.append((((xf + xb) / 2, 0, z), (0, 1, 0), (1, 0, 0), 0.0156 + g, (xf - xb) / 2 + g))
    finish(hs.loft("grip_cap", cap, power=3.4), M_POLY, bevel=0.0006, angle=50)
    # Trigger guard (the shared shape, a little deeper for gloves) and the long double-action trigger.
    guard = hs.side_profile("trigger_guard", [(-0.021, -0.0340), (-0.020, -0.054), (-0.013, -0.0600), (0.030, -0.0600),
                                              (RF_X0 + 0.0005, -0.054), (RF_X0 + 0.0005, -0.0340)], 0.0140)
    hs.cut(guard, hs.side_profile("guard_hole", [(-0.0150, -0.0300), (0.0330, -0.0300), (0.0330, -0.0500),
                                                 (0.0270, -0.0556), (-0.0100, -0.0556), (-0.0150, -0.050)], 0.05))
    finish(guard, M_FRAME, bevel=0.0012)
    finish(hs.side_profile("trigger", [(0.0105, -0.0340), (0.0185, -0.0340), (0.0172, -0.0430), (0.0215, -0.0525),
                                       (0.0165, -0.0548), (0.0078, -0.0430)], 0.0062), M_STEEL, bevel=0.0007)
    if hi():
        for i in range(5):
            finish(hs.box(f"trigger_groove{i}", (0.0006, 0.0064, 0.0011), (0.0188 - i * 0.0004, 0, -0.0445 - i * 0.0018),
                          (0, 0.4, 0)), M_BORE, bevel=0)
    # Lower frame bar under the cylinder, from the shield to the front frame, holding the crane hinge.
    bar = hs.section("lower_bar", [(-0.0130, HINGE_Z - 0.0105), (0.0130, HINGE_Z - 0.0105), (0.0150, HINGE_Z - 0.0040),
                                   (0.0150, HINGE_Z + 0.0020), (-0.0150, HINGE_Z + 0.0020), (-0.0150, HINGE_Z - 0.0040)],
                     RF_X0 + 0.004, CRANE_X1 + 0.004)
    hs.cut(bar, hs.cyl_x("hinge_bore", 0.0090, CYL_X0 - 0.002, CRANE_X1 + 0.0015, verts=32, z=HINGE_Z))
    finish(bar, M_FRAME, bevel=0.0012)
    finish(hs.cyl_x("hinge_tube", 0.0084, CYL_X0 - 0.002, CRANE_X1 + 0.0015, verts=32, z=HINGE_Z), M_STEEL, bevel=0.0006)
    # Crane latch: a thumb lever on the right side of the bar (pressed to swing the cylinder out).
    finish(hs.box("crane_latch", (0.022, 0.0040, 0.0070), (0.128, -0.0166, HINGE_Z - 0.003)), M_STEEL, bevel=0.0010)
    if hi():
        for i in range(6):
            finish(hs.box(f"latch_serr{i}", (0.0008, 0.0010, 0.0066), (0.119 + i * 0.0036, -0.0188, HINGE_Z - 0.003)),
                   M_BORE, bevel=0)
    text("frame_mark_l", "M32A1  MGL  40 MM", 0.0040, (0.160, 0.0151, HINGE_Z - 0.0075), (PI / 2, 0, PI))
    text("frame_mark_r", "LV ONLY  0417", 0.0036, (0.062, -0.0151, HINGE_Z - 0.0085), (PI / 2, 0, 0))
    # Top strap over the cylinder, with the rail.
    strap = hs.section("top_strap", [(-0.0160, STRAP_Z0), (0.0160, STRAP_Z0), (0.0175, STRAP_Z0 + 0.004),
                                     (0.0175, STRAP_Z1), (-0.0175, STRAP_Z1), (-0.0175, STRAP_Z0 + 0.004)],
                       REC_X0 + 0.004, FF_X1)
    finish(strap, M_FRAME, bevel=0.0012)
    pic_rail("top_rail", REC_X0 + 0.012, FF_X1 - 0.002, RAIL_Z, STRAP_Z1 - 0.0005, M_ANOD, REC_X0 + 0.018, 28)
    if hi():
        for i in range(28):
            if i % 2 == 0:
                text(f"rail_num{i}", str(i + 1), 0.0024, (REC_X0 + 0.0185 + i * 0.010, 0.0108, RAIL_Z - 0.0042),
                     (PI / 2, 0, PI), m=M_PAINT)
    # Sling swivel and QD cup on the left of the receiver.
    finish(hs.cyl_y("qd_cup", 0.0072, 0.0040, (-0.098, REC_HW + 0.0016, 0.012), verts=24), M_STEEL, bevel=0.0008)
    finish(hs.cyl_y("qd_hole", 0.0042, 0.0006, (-0.098, REC_HW + 0.0039, 0.012), verts=16), M_BORE, bevel=0)


# ---------------------------------------------------------------- cylinder, crane, rounds
def cylinder_outline_cut(tool_name, x0, x1, r, k):
    y, z = chamber_yz(k)
    return hs.cyl_x(tool_name, r, x0, x1, verts=48, y=y, z=z)


def build_cylinder():
    part("cylinder")
    cyl = hs.cyl_x("cylinder_body", CYL_R, CYL_X0, CYL_X1, verts=96, z=CY_Z)
    # Chambers bored through, flutes between them.
    for k in range(6):
        y, z = chamber_yz(k)
        hs.cut(cyl, hs.cyl_x(f"chamber{k}", CH_R, CYL_X0 - 0.01, CYL_X1 + 0.01, verts=48, y=y, z=z))
        b = math.radians(30.0 + 60.0 * k)
        ry, rz = -math.sin(b), math.cos(b)
        ty, tz = -math.cos(b), -math.sin(b)
        c = CYL_R + 0.006
        fy, fz = ry * c, CY_Z + rz * c
        flute = hs.loft(f"flute{k}", [((x, fy, fz), (0, ty, tz), (0, ry, rz), w, 0.0135)
                                      for x, w in ((CYL_X0 + 0.010, 0.0002), (CYL_X0 + 0.024, 0.0105),
                                                   (CYL_X1 - 0.024, 0.0105), (CYL_X1 - 0.010, 0.0002))],
                        n=24 if hi() else 12, power=2.0)
        hs.cut(cyl, flute)
    # Rear face relief round the case heads (the rims sit in it).
    for k in range(6):
        y, z = chamber_yz(k)
        hs.cut(cyl, hs.cyl_x(f"rim_recess{k}", CH_R + 0.0026, CYL_X0 - 0.002, CYL_X0 + 0.0016, verts=48, y=y, z=z))
    finish(cyl, M_ANOD, bevel=0.0009, angle=30)
    # Ratchet star round the axis on the rear face, the axis bushing in front.
    star = hs.cyl_x("ratchet", 0.0140, CYL_X0 - 0.0035, CYL_X0 + 0.0005, verts=12, fixed=True, z=CY_Z)
    finish(star, M_BRIGHT, bevel=0.0005, angle=20, smooth=False)
    finish(hs.cyl_x("cyl_axis_front", 0.0110, CYL_X1, CYL_X1 + 0.0010, verts=32, z=CY_Z), M_BRIGHT, bevel=0.0003)
    if hi():
        # Stop notches round the rim at each chamber.
        for k in range(6):
            b = math.radians(60.0 * k)
            y, z = -CYL_R * math.sin(b), CY_Z + CYL_R * math.cos(b)
            finish(hs.box(f"stop_notch{k}", (0.008, 0.005, 0.003), (CYL_X0 + 0.011, y, z), (b, 0, 0)), M_BORE, bevel=0)
    # Crane: hinge knuckle on the tube, arm up to the cylinder axis in front of the cylinder,
    # the clockwork spring housing on its face (wound as the cylinder is loaded).
    part("crane")
    pts = [(-0.0110, HINGE_Z - 0.0080), (0.0110, HINGE_Z - 0.0080), (0.0130, HINGE_Z + 0.004), (0.0120, CY_Z - 0.006),
           (0.0100, CY_Z + 0.006), (-0.0100, CY_Z + 0.006), (-0.0120, CY_Z - 0.006), (-0.0130, HINGE_Z + 0.004)]
    finish(hs.section("crane_arm", pts, CRANE_X0, CRANE_X1), M_STEEL, bevel=0.0008)
    finish(hs.cyl_x("crane_knuckle", 0.0108, CRANE_X0 - 0.0005, CRANE_X1 + 0.0005, verts=32, z=HINGE_Z), M_STEEL,
           bevel=0.0006)
    finish(hs.cyl_x("spring_housing", 0.0145, CRANE_X1, CRANE_X1 + 0.010, verts=48, z=CY_Z), M_ANOD, bevel=0.0010)
    finish(hs.cyl_x("spring_cap", 0.0100, CRANE_X1 + 0.010, CRANE_X1 + 0.0125, verts=6, fixed=True, z=CY_Z), M_BRIGHT,
           bevel=0.0004, smooth=False)
    if hi():
        for k in range(18):
            a = 2 * PI * k / 18
            finish(hs.box(f"spring_knurl{k}", (0.0085, 0.0011, 0.0011),
                          (CRANE_X1 + 0.005, 0.0146 * math.cos(a), CY_Z + 0.0146 * math.sin(a)), (a, 0, 0)), M_ANOD,
                   bevel=0)
    part("body")


def build_rounds():
    """A live case head in each chamber: aluminium with a rim, extractor groove, primer and headstamp."""
    for k in range(6):
        part(f"round_{k}")
        y, z = chamber_yz(k)
        x = CYL_X0 + 0.0002
        finish(hs.cyl_x(f"case_rim{k}", CH_R + 0.0018, x - 0.0016, x, verts=40, y=y, z=z), M_ALU_CASE, bevel=0.0003)
        finish(hs.cyl_x(f"case_body{k}", CH_R - 0.0002, x - 0.0001, x + 0.012, verts=40, y=y, z=z), M_ALU_CASE, bevel=0)
        finish(hs.cyl_x(f"primer{k}", 0.0042, x - 0.0019, x - 0.0014, verts=20, y=y, z=z), M_BRASS, bevel=0.0001)
        if hi():
            bpy.ops.mesh.primitive_torus_add(major_segments=40, minor_segments=6, major_radius=CH_R * 0.66,
                                             minor_radius=0.0003, location=(x - 0.0016, y, z), rotation=(0, PI / 2, 0))
            t = bpy.context.active_object
            t.name = f"case_ring{k}"
            finish(t, M_BORE, bevel=0, smooth=False)
            text(f"headstamp{k}", "40MM HEDP", 0.0024, (x - 0.00170, y + 0.008, z + 0.0085),
                 facing((0, -1, 0), (0, 0, 1)), m=M_BORE)
    part("body")


# ---------------------------------------------------------------- front frame, barrel, handguard
def build_front():
    # Front frame: the barrel boss, tied to the top strap. Below it the cylinder's front stays open
    # for the crane.
    finish(hs.section("ff_boss", [(-0.0300, -0.030), (0.0300, -0.030), (0.0300, 0.020), (0.0175, STRAP_Z1),
                                  (-0.0175, STRAP_Z1), (-0.0300, 0.020)], FF_X0, FF_X1), M_FRAME, bevel=0.0016)
    for sy in (-1, 1):
        screw(f"ff_screw{sy}", ((FF_X0 + FF_X1) / 2, sy * 0.0300, -0.012), "y+" if sy > 0 else "y-", 0.0030, proud=0.0006)
    # Barrel: blued steel, rifled bore, crowned muzzle.
    brl = hs.lathe_x("barrel", [(FF_X1 - 0.002, BRL_R + 0.003), (FF_X1 + 0.010, BRL_R + 0.003), (FF_X1 + 0.012, BRL_R),
                                (MUZZLE_X - 0.006, BRL_R), (MUZZLE_X - 0.003, BRL_R - 0.0015), (MUZZLE_X, BRL_R - 0.0025),
                                (MUZZLE_X, BORE_R + 0.0015), (MUZZLE_X - 0.002, BORE_R)], verts=64)
    hs.cut(brl, hs.cyl_x("bore", BORE_R, FF_X0, MUZZLE_X + 0.01, verts=64))
    finish(brl, M_STEEL, bevel=0.0005, angle=25)
    finish(hs.cyl_x("bore_back", BORE_R + 0.0005, MUZZLE_X - 0.060, MUZZLE_X - 0.059, verts=48), M_BORE, bevel=0,
           smooth=False)
    if hi():
        for k in range(8):
            a = 2 * PI * k / 8
            land = hs.box(f"land{k}", (0.058, 0.0030, 0.0012), (MUZZLE_X - 0.030, (BORE_R - 0.0005) * math.cos(a),
                                                                  (BORE_R - 0.0005) * math.sin(a)), (a + PI / 2, 0, 0))
            land.rotation_euler = (a + PI / 2 + 0.25, 0, 0)
            finish(land, M_BORE, bevel=0, smooth=False)
    # Inductive fuze setter ring at the muzzle (programs each round's burst range as it leaves).
    setter = lathe_loop("fuze_setter", [(MUZZLE_X - 0.034, BRL_R + 0.0005), (MUZZLE_X - 0.032, BRL_R + 0.0060),
                                        (MUZZLE_X - 0.008, BRL_R + 0.0060), (MUZZLE_X - 0.006, BRL_R + 0.0005)], verts=64)
    finish(setter, M_ANOD, bevel=0.0008)
    if hi():
        for k in range(10):
            bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=6, major_radius=BRL_R + 0.0060,
                                             minor_radius=0.0006, location=(MUZZLE_X - 0.0295 + k * 0.0022, 0, 0),
                                             rotation=(0, PI / 2, 0))
            rib = bpy.context.active_object
            rib.name = f"setter_rib{k}"
            finish(rib, M_ANOD, bevel=0)
    finish(hs.box("setter_box", (0.016, 0.010, 0.008), (MUZZLE_X - 0.020, -0.012, BRL_R + 0.0075)), M_ANOD, bevel=0.0010)
    finish(hs.cyl_y("setter_led", 0.0012, 0.0006, (MUZZLE_X - 0.014, -0.0172, BRL_R + 0.0075), verts=12), M_LED, bevel=0)
    # Quad-rail handguard with vent slots.
    hg = hs.loft_x("handguard", [(HG_X0, HG_H - 0.002, -HG_H + 0.002, HG_H - 0.002), (HG_X0 + 0.006, HG_H, -HG_H, HG_H),
                                 (HG_X1 - 0.006, HG_H, -HG_H, HG_H), (HG_X1, HG_H - 0.002, -HG_H + 0.002, HG_H - 0.002)],
                   power=5.0)
    hs.cut(hg, hs.cyl_x("hg_inner", BRL_R + 0.0015, HG_X0 - 0.01, HG_X1 + 0.01, verts=48))
    for sy in (-1, 1):
        for i in range(6):
            x = HG_X0 + 0.030 + i * 0.030
            hs.cut(hg, hs.loft_x(f"hg_vent{sy}_{i}", [(x - 0.010, 0.010, -0.010, 0.04), (x + 0.010, 0.010, -0.010, 0.04)],
                                 power=2.5))
    finish(hg, M_FRAME, bevel=0.0010)
    pic_rail("under_rail", HG_X0 + 0.003, HG_X1 - 0.012, URAIL_Z, -HG_H + 0.0005, M_ANOD, HG_X0 + 0.009, 21)
    for sy in (-1, 1):
        prof = [(sy * (HG_H - 0.0005), -0.0078), (sy * (HG_H - 0.0005), 0.0078), (sy * (HG_H + 0.0028), 0.0106),
                (sy * (HG_H + 0.0056), 0.0078), (sy * (HG_H + 0.0056), -0.0078), (sy * (HG_H + 0.0028), -0.0106)]
        rail = hs.section(f"side_rail{sy}", prof, HG_X1 - 0.090, HG_X1 - 0.010)
        for i in range(8):
            hs.cut(rail, hs.box(f"side_rail{sy}_slot{i}", (0.00523, 0.006, 0.03), (HG_X1 - 0.084 + i * 0.010,
                                                                                 sy * (HG_H + 0.0056), 0)))
        finish(rail, M_ANOD, bevel=0.0004)
    for i, x in enumerate((HG_X0 + 0.004, HG_X1 - 0.004)):
        finish(hs.loft_x(f"hg_band{i}", [(x - 0.003, HG_H + 0.0008, -HG_H - 0.0008, HG_H + 0.0008),
                                         (x + 0.003, HG_H + 0.0008, -HG_H - 0.0008, HG_H + 0.0008)], power=5.0),
               M_ANOD, bevel=0.0006)
    # Cable from the sight's rangefinder pod forward along the right of the handguard to the fuze setter.
    finish(hs.tube_path("fcs_cable", [(SX1 - 0.006, -0.020, SIGHT_Z - 0.030), (FF_X1 + 0.004, -0.030, 0.030),
                                      (HG_X0 + 0.040, -HG_H - 0.0045, 0.016), (HG_X1 - 0.040, -HG_H - 0.0045, 0.016),
                                      (MUZZLE_X - 0.040, -0.026, 0.020), (MUZZLE_X - 0.026, -0.014, BRL_R + 0.008)],
                         0.0024), M_CABLE, bevel=0)
    for i, x in enumerate((HG_X0 + 0.060, HG_X1 - 0.060)):
        finish(hs.box(f"cable_clip{i}", (0.008, 0.0040, 0.0090), (x, -HG_H - 0.0030, 0.016)), M_POLY, bevel=0.0008)


def build_foregrip():
    """The MG42's clamp-on vertical foregrip at its place (the arms' support hand fits)."""
    finish(hs.box("fg_clamp", (0.028, 0.0250, 0.0120), (0.203, 0, URAIL_Z - 0.0050)), M_ANOD, bevel=0.0012)
    finish(hs.cyl_y("fg_bolt", 0.003, 0.031, (0.203, 0, URAIL_Z - 0.0035), verts=16), M_STEEL, bevel=0.0004)
    finish(hs.cyl_y("fg_nut", 0.0055, 0.004, (0.203, -0.0160, URAIL_Z - 0.0035), verts=6), M_STEEL, bevel=0.0004)
    grip = hs.cyl_between("fg_grip", (0.2030, 0, -0.044), (0.211, 0, -0.130), 0.0165, verts=32)
    for i in range(4):
        z = -0.056 - i * 0.021
        bpy.ops.mesh.primitive_torus_add(major_segments=hs.nverts(32), minor_segments=8, major_radius=0.0172,
                                         minor_radius=0.0021, location=(0.203 + (z + 0.036) / -0.094 * 0.008, 0, z))
        hs.cut(grip, bpy.context.active_object)
    finish(grip, M_POLY, bevel=0.0012)
    finish(hs.cyl_between("fg_cap", (0.211, 0, -0.128), (0.2117, 0, -0.136), 0.0176, verts=32), M_ANOD, bevel=0.0015)


# ---------------------------------------------------------------- sight
def build_sight():
    """FCS-40: a tall reflex sight with a round window, a range drum on the left and a
    laser rangefinder pod under its nose on the right."""
    base_x0, base_x1 = SX0 - 0.004, SX1 - 0.010
    # Rail clamp base with two cross-bolts, and a riser.
    finish(hs.section("sight_base", [(-0.0140, RAIL_Z - 0.0062), (-0.0112, RAIL_Z - 0.0062), (-0.0112, RAIL_Z + 0.0002),
                                     (0.0112, RAIL_Z + 0.0002), (0.0112, RAIL_Z - 0.0030), (0.0140, RAIL_Z - 0.0030),
                                     (0.0150, RAIL_Z + 0.006), (-0.0150, RAIL_Z + 0.006)], base_x0, base_x1), M_ANOD,
           bevel=0.0007)
    for i, x in enumerate((base_x0 + 0.012, base_x1 - 0.012)):
        screw(f"sight_bolt{i}", (x, -0.0152, RAIL_Z - 0.0030), "y-", 0.0040, proud=0.0018)
    riser = hs.side_profile("sight_riser", [(base_x0 + 0.004, RAIL_Z + 0.005), (base_x1 - 0.002, RAIL_Z + 0.005),
                                            (base_x1 - 0.008, SIGHT_Z - WIN_R - 0.002), (base_x0 + 0.012, SIGHT_Z - WIN_R - 0.002)],
                            0.0240)
    hs.cut(riser, hs.cyl_y("riser_lightening", 0.0080, 0.04, ((base_x0 + base_x1) / 2, 0, RAIL_Z + 0.019), verts=32))
    finish(riser, M_ANOD, bevel=0.0010)
    # Hood: a short tube round the window, flared at the front.
    hood = lathe_loop("sight_hood", [(SX0, WIN_R + 0.0030), (SX0 + 0.004, WIN_R + 0.0050), (SX1 - 0.010, WIN_R + 0.0050),
                                     (SX1, WIN_R + 0.0068), (SX1, WIN_R + 0.0012), (SX0, WIN_R + 0.0008)], verts=64)
    hood.location = (0, 0, SIGHT_Z)
    bpy.ops.object.select_all(action="DESELECT")
    hood.select_set(True)
    bpy.context.view_layer.objects.active = hood
    bpy.ops.object.transform_apply(location=True)
    finish(hood, M_ANOD, bevel=0.0007, angle=30)
    # Range drum on the left (graduated in tens of metres; the FCS drives it) and the brightness knob on top.
    drum_x = (SX0 + SX1) / 2 - 0.006
    finish(hs.cyl_y("range_drum", 0.0125, 0.0090, (drum_x, WIN_R + 0.0095, SIGHT_Z - 0.006), verts=48), M_ANOD,
           bevel=0.0008)
    finish(hs.cyl_y("range_drum_cap", 0.0080, 0.0016, (drum_x, WIN_R + 0.0148, SIGHT_Z - 0.006), verts=32), M_STEEL,
           bevel=0.0004)
    if hi():
        for k in range(16):
            a = 2 * PI * k / 16
            r = 0.0125
            finish(hs.box(f"drum_tick{k}", (0.0006, 0.0004, 0.0024 if k % 2 == 0 else 0.0014),
                          (drum_x + r * math.cos(a), WIN_R + 0.0141, SIGHT_Z - 0.006 + r * math.sin(a)), (0, -a + PI / 2, 0)),
                   M_PAINT, bevel=0)
        text("drum_num", "50  100  150", 0.0024, (drum_x - 0.010, WIN_R + 0.0142, SIGHT_Z + 0.0085), (PI / 2, 0, PI),
             m=M_PAINT)
    finish(hs.cyl_z("bright_knob", 0.0060, 0.0050, (SX0 + 0.016, 0, SIGHT_Z + WIN_R + 0.0074), verts=32), M_ANOD,
           bevel=0.0006)
    if hi():
        for k in range(20):
            a = 2 * PI * k / 20
            finish(hs.box(f"bright_knurl{k}", (0.0008, 0.0008, 0.0046),
                          (SX0 + 0.016 + 0.0060 * math.cos(a), 0.0060 * math.sin(a), SIGHT_Z + WIN_R + 0.0074), (0, 0, a)),
                   M_ANOD, bevel=0)
    text("sight_mark", "FCS-40", 0.0036, (SX0 + 0.014, WIN_R + 0.0052, SIGHT_Z + 0.006), (PI / 2, 0, PI))
    # Laser rangefinder pod under the nose on the right: two lenses, a status LED, a fire button.
    pod_x0, pod_x1 = SX1 - 0.040, SX1 + 0.002
    pz = SIGHT_Z - WIN_R - 0.008
    finish(hs.loft_x("lrf_pod", [(pod_x0, pz + 0.008, pz - 0.009, 0.0110), (pod_x0 + 0.004, pz + 0.010, pz - 0.011, 0.0130),
                                 (pod_x1 - 0.003, pz + 0.010, pz - 0.011, 0.0130), (pod_x1, pz + 0.009, pz - 0.010, 0.0122)],
                     power=4.0), M_ANOD, bevel=0.0008)
    for i, (yy, r) in enumerate(((0.0050, 0.0042), (-0.0055, 0.0034))):
        finish(hs.cyl_x(f"lrf_bezel{i}", r + 0.0012, pod_x1 - 0.0005, pod_x1 + 0.0012, verts=32, y=yy, z=pz), M_STEEL,
               bevel=0.0003)
        finish(hs.cyl_x(f"lrf_lens{i}", r, pod_x1 + 0.0004, pod_x1 + 0.0014, verts=32, y=yy, z=pz), M_LRF, bevel=0.0002)
    finish(hs.cyl_y("lrf_led", 0.0011, 0.0006, (pod_x0 + 0.010, -0.0133, pz + 0.004), verts=12), M_LED, bevel=0)
    finish(hs.box("lrf_button", (0.008, 0.0030, 0.0060), (pod_x0 + 0.022, -0.0136, pz - 0.001)), M_RUBBER, bevel=0.0010)
    text("lrf_mark", "LRF", 0.0030, (pod_x0 + 0.004, -0.0131, pz - 0.006), (PI / 2, 0, 0), m=M_PAINT)
    if hi():
        text("lrf_warn", "CLASS 1M", 0.0020, (pod_x0 + 0.004, 0.0131, pz - 0.007), (PI / 2, 0, PI), m=M_YELLOW)
    # Glass: rear and front lens; the dot is projected onto the front one.
    part("lens")
    for i, x in enumerate((SX0 + 0.0030, SX1 - 0.0040)):
        finish(hs.cyl_x(f"sight_glass{i}", WIN_R + 0.0010, x, x + 0.0012, verts=48, z=SIGHT_Z), M_LENS, bevel=0)
    part("reticle")
    finish(hs.cyl_x("sight_dot", 0.00085, SX1 - 0.0046, SX1 - 0.0042, verts=12, fixed=True, z=SIGHT_Z), M_RED, bevel=0,
           smooth=False)
    bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=4, major_radius=0.0060,
                                     minor_radius=0.00028, location=(SX1 - 0.0044, 0, SIGHT_Z), rotation=(0, PI / 2, 0))
    t = bpy.context.active_object
    t.name = "sight_ring"
    finish(t, M_RED, bevel=0, smooth=False)
    part("body")


# ---------------------------------------------------------------- stock
def build_stock():
    part("stock")
    tube_z = 0.010
    k = 0.060   # collapsed: the stock body sits this far forward of full extension
    finish(hs.cyl_x("buffer_tube", 0.0150, -0.300 + k, REC_X0 + 0.004, verts=40, z=tube_z), M_ANOD, bevel=0.0008)
    finish(hs.cyl_x("castle_nut", 0.0185, REC_X0 - 0.004, REC_X0 + 0.004, verts=10, fixed=True, z=tube_z), M_STEEL,
           bevel=0.0006, smooth=False)
    if hi():
        for i in range(12):
            finish(hs.box(f"tube_rib{i}", (0.004, 0.0020, 0.0008), (-0.290 + k + i * 0.008, 0, tube_z - 0.0150)), M_ANOD,
                   bevel=0)
    # Skeletal stock body sliding on the tube, cheek riser, latch lever, rubber pad.
    body = hs.side_profile("stock_body", [(-0.300 + k, 0.034), (-0.200 + k, 0.030), (-0.188 + k, 0.020),
                                          (-0.188 + k, -0.004), (-0.230 + k, -0.040), (-0.300 + k, -0.088),
                                          (-0.318 + k, -0.088), (-0.318 + k, 0.040)], 0.034)
    hs.cut(body, hs.side_profile("stock_window", [(-0.290 + k, -0.008), (-0.236 + k, -0.010), (-0.292 + k, -0.070)], 0.06))
    hs.cut(body, hs.cyl_x("stock_tube_bore", 0.0152, -0.40, -0.10, verts=40, z=tube_z))
    finish(body, M_POLY, bevel=0.0020)
    finish(hs.loft_x("cheek_riser", [(-0.300 + k, 0.046, 0.030, 0.0150), (-0.292 + k, 0.050, 0.030, 0.0170),
                                     (-0.225 + k, 0.050, 0.030, 0.0170), (-0.210 + k, 0.044, 0.030, 0.0140)], power=4.0),
           M_POLY, bevel=0.0012)
    finish(hs.box("stock_latch", (0.030, 0.0080, 0.0060), (-0.214 + k, 0, -0.012)), M_POLY, bevel=0.0012)
    finish(hs.loft_x("butt_pad", [(-0.318 + k, 0.042, -0.090, 0.0172), (-0.326 + k, 0.044, -0.092, 0.0180),
                                  (-0.334 + k, 0.040, -0.088, 0.0168)], power=4.0), M_RUBBER, bevel=0.0015)
    if hi():
        for i in range(10):
            z = -0.080 + i * 0.0125
            finish(hs.box(f"pad_groove{i}", (0.0010, 0.036, 0.0012), (-0.3345 + k, 0, z)), M_BORE, bevel=0)
    part("body")


def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_rear_frame()
    build_cylinder()
    build_rounds()
    build_front()
    build_foregrip()
    build_sight()
    build_stock()
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
    print(f"m32 {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


def split_parts(low):
    objs = {}
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
        objs[pname] = ob
        print(f"m32: part {pname}: {bakeutil.tri_count(ob)} tris")
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


# ---------------------------------------------------------------- the grenade in flight
def flat(name, rgb, rough, metal, emit=None):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1)
        b.inputs["Emission Strength"].default_value = emit[1]
    return m


def build_grenade(path):
    """The 40 mm HEDP projectile as it flies: olive body, yellow marking band, bright
    fuze nose, copper rotating band. Factor materials (it's 4 cm across and moving)."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    hs.set_detail(hs.LOW)
    od = flat("grenade_olive", (0.11, 0.12, 0.07), 0.55, 0.1)
    yellow = flat("grenade_yellow", (0.75, 0.58, 0.05), 0.5, 0.0)
    nose = flat("grenade_fuze", (0.55, 0.52, 0.46), 0.35, 0.9)
    band = flat("grenade_band", (0.62, 0.33, 0.18), 0.3, 1.0)
    base = flat("grenade_base", (0.06, 0.06, 0.06), 0.5, 0.6)
    # +X = nose. Projectile length 55 mm from its base at x = -0.025.
    body = hs.lathe_x("grenade_body", [(-0.0250, 0.0150), (-0.0245, 0.0196), (0.0060, 0.0199), (0.0160, 0.0185),
                                       (0.0230, 0.0150)], verts=24)
    body.data.materials.append(od)
    hs.PARTS.append(body)
    ring = hs.lathe_x("grenade_ring", [(-0.0040, 0.0201), (0.0040, 0.0201)], verts=24)
    ring.data.materials.append(yellow)
    hs.PARTS.append(ring)
    rb = hs.lathe_x("grenade_rot_band", [(-0.0200, 0.0203), (-0.0150, 0.0203)], verts=24)
    rb.data.materials.append(band)
    hs.PARTS.append(rb)
    fz = hs.lathe_x("grenade_nose", [(0.0228, 0.0152), (0.0290, 0.0120), (0.0330, 0.0070), (0.0345, 0.0030),
                                     (0.0348, 0.0005)], verts=24)
    fz.data.materials.append(nose)
    hs.PARTS.append(fz)
    bs = hs.lathe_x("grenade_base_plug", [(-0.0256, 0.0005), (-0.0256, 0.0150)], verts=24)
    bs.data.materials.append(base)
    hs.PARTS.append(bs)
    for ob in hs.PARTS:
        ob.data.shade_smooth()
    g = hs.join_parts("grenade_40mm")
    bakeutil.export_gltf(g, path)
    print(f"m32: grenade {bakeutil.tri_count(g)} tris -> {path}")


# ---------------------------------------------------------------- preview
def preview_glass():
    g = bpy.data.materials.new("preview_glass")
    b = g.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.96, 0.9, 0.95, 1)
    b.inputs["Roughness"].default_value = 0.0
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.02
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Tint"].default_value = (1.0, 0.5, 0.75, 1)
    return g


def lamp(name, colour, strength):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Emission Color"].default_value = (*colour, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


def swing_matrix(open_f):
    """The crane swing (cylinder out to the right) at 0..1 open, about the hinge axis."""
    a = math.radians(82.0) * open_f
    hinge = V((0.0, 0.0, HINGE_Z))
    return Matrix.Translation(hinge) @ Matrix.Rotation(a, 4, "X") @ Matrix.Translation(-hinge)


def pose_open(objs, open_f):
    if open_f <= 0:
        return
    m = swing_matrix(open_f)
    for ob in objs:
        ob.matrix_world = m @ ob.matrix_world


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
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.007, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.13, 0.135, 0.145, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world
    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, -0.17)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.1, 0, -0.03), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.3, -1.4, 1.2), 70, 1.8, sy=0.6)
    area("strip_top", (0.10, 0.0, 1.2), 40, 2.4, sy=0.2)
    area("fill", (0.5, 1.4, 0.3), 36, 1.5, (0.75, 0.85, 1.0))
    area("rim", (1.6, -0.4, 0.5), 60, 0.9, (1.0, 0.82, 0.62))
    area("kick", (-1.4, 0.3, 0.2), 30, 1.0, (0.9, 0.95, 1.0))
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
    print(f"m32: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((0.07, -2.4, -0.02), (0.07, 0, -0.03), 55, 0.0),
        "left_side": ((0.07, 2.4, -0.02), (0.07, 0, -0.03), 55, 0.0),
        "beauty": ((0.85, -0.85, 0.42), (0.08, 0, -0.03), 50, 8.0),
        "left": ((-0.40, 0.95, 0.38), (0.08, 0, -0.03), 45, 8.0),
        "cylinder": ((-0.05, -0.38, 0.10), (0.07, 0.0, -0.05), 50, 4.0),
        "rear": ((-0.30, -0.22, 0.10), (0.06, -0.02, -0.04), 50, 4.0),
        "sight": ((-0.18, 0.20, 0.16), (0.07, 0.0, 0.08), 50, 4.0),
        "front": ((0.75, 0.30, 0.02), (0.38, 0.0, -0.01), 50, 4.0),
        # Roughly the player's hip view: eye behind and left of the gun, above it.
        "fp": ((-0.50, 0.17, 0.16), (0.8, 0.10, 0.06), 0, 0.0),
    }
    only = [s for s in args.only.split(",") if s]
    for key, (loc, target, lens, fstop) in shots.items():
        if only and key not in only:
            continue
        if key == "fp":
            shoot(cam, f"{stem}_{key}.png", loc, target, fov_deg=60)
        else:
            shoot(cam, f"{stem}_{key}.png", loc, target, lens=lens, fstop=fstop)


def moving_objects():
    return [ob for ob in bpy.data.objects if ob.name.split(".")[0] in ("crane", "cylinder")
            or ob.name.startswith("round_")]


# ---------------------------------------------------------------- run
if args.out and not args.reuse:
    high = build(hs.HIGH, "m32_high")
    low = build(hs.LOW, "m32_low")
    bakeutil.unwrap(low, boost={M_FRAME.name: 1.1, M_ANOD.name: 1.1, M_STEEL.name: 1.0, M_MARK.name: 1.6,
                                M_PAINT.name: 1.5, M_POLY.name: 0.8, M_RUBBER.name: 0.8, M_BORE.name: 0.5,
                                M_ALU_CASE.name: 1.3})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "m32", cage=0.0012, ray=0.004,
                                 ao_distance=0.03, grime=0.35, log=print)
    bpy.data.objects.remove(high)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "m32", emission_strength=4.0)
    objs = split_parts(low)
    export(list(objs.values()), args.out)
    print(f"m32: exported {args.out}")
    build_grenade(os.path.join(os.path.dirname(os.path.abspath(args.out)), "grenade_40mm.gltf"))
if args.out and args.preview:
    if True:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        for nm, m in (("lens", preview_glass()), ("reticle", lamp("preview_dot", (1.0, 0.1, 0.04), 12.0))):
            ob = bpy.data.objects.get(nm)
            if ob:
                ob.data.materials.clear()
                ob.data.materials.append(m)
        if args.arms:
            bpy.ops.import_scene.gltf(filepath=args.arms)
        pose_open(moving_objects(), args.open)
        render_previews(args.preview.rsplit(".", 1)[0])
if args.preview and not args.out:
    high = build(hs.HIGH, "m32_high")
    glass = preview_glass()
    for i, slot in enumerate(high.data.materials):
        if slot == M_LENS:
            high.data.materials[i] = glass
    if args.arms:
        bpy.ops.import_scene.gltf(filepath=args.arms)
    render_previews(args.preview.rsplit(".", 1)[0])
