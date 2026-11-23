"""Smith & Wesson Model 629, .44 Magnum, 6" barrel, stainless with wood grips (owner, 2026-11-23).

Owner brief: "a beautiful looking 44 Magnum with ... reflective stainless steel
chrome, maybe a nice wooden handle ... a meaty fucking hand cannon that's
modeled after a real picture of one you get online ... follow the same process
you did for the other guns that you really traced."

Traced, not guessed: the outlines are in pixels of a left-side photo of a
real stainless 6" Model 629 (see "the trace" below and CREDITS.md), turned
into millimetres of the real gun (x forward from the cylinder's rear face, z up
from the bore) by `P()`, and checked with `--overlay`, which renders an
orthographic left view at the photo's scale and draws its outline over the
photo (docs/previews/magnum44_overlay.png). Widths, which a side photo can't
give, are the N frame's.

What it is (as the photo shows it): the stainless N frame (topstrap, recoil
shield, the hump behind the hammer, the grip frame under the wood), the 6"
barrel with its full-length underlug and the ejector rod's window on the left,
the flat rib, the black front ramp and the adjustable black rear sight, the
six-shot unfluted cylinder with its stop notches and the ejector star, the
crane it swings out on, the hammer with its checkered spur, the wide smooth
trigger, the trigger guard, the round checkered thumbpiece, the S&W emblem on
the left of the frame and the side-plate screws on the right, the markings
("SMITH & WESSON" on the left of the barrel, ".44 MAGNUM" on the right), and
the wood target grips (sculpted: the horn under the hammer, the filler behind
the trigger guard, the palm swell, the square butt, the S&W medallion). Six .44 Magnum rounds (JHP) in the
chambers, and a speedloader with six more.

Parts (per-face part id, split after the bake). The game turns and swings them
(WeaponData cylinder_axis, crane_hinge, crane_swing_deg; ViewmodelRig):
  body         everything that doesn't move
  cylinder     the cylinder and its ejector rod (turns a chamber a shot, swings out)
  crane        the yoke the cylinder swings out on
  round_0..5   a cartridge in each chamber (hidden when the chamber's empty)
  speedloader  six rounds in a loader, built where it seats on the swung-out cylinder

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin: the arms' grip
frame (raw_assets/characters/fp_arms: the shared pistol hands close on the
grip), so the bore is ORIGIN_Z above or below 0 (WeaponData muzzle_point and
cylinder_axis follow it). Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/magnum44/build.py --out assets/weapons/magnum44/magnum44.gltf --tex 4096 \\
      --preview docs/previews/magnum44.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/m44.png [--only side,fp]
  Photo match: --overlay /tmp/m44_overlay.png --photo <the reference photo>
  Numbers the game needs: --print-data
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402
import sdf  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--emission-size", type=int, default=256)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--overlay", default="", help="render the photo-scale side view to this png")
ap.add_argument("--photo", default="", help="the reference photo (outline drawn over it)")
ap.add_argument("--swung", action="store_true", help="previews with the cylinder swung out and the loader in")
ap.add_argument("--fast", action="store_true", help="coarser sculpts, fewer samples")
ap.add_argument("--print-data", action="store_true", help="print the WeaponData numbers and quit")
ap.add_argument("--from-gltf", default="", help="skip building: import this exported .gltf and render --preview")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
PI = math.pi
F32 = np.float32

# ---------------------------------------------------------------- the trace
# Reference: "Smith & Wesson Model 629-2.jpg" (Hmaag, Wikimedia Commons, CC0), a
# left-side photo of a stainless 6" Model 629 with checkered wood target grips,
# read off its 960 px copy with gridded crops and edge profiles (tools in the
# commit message of 2026-11-23). It is level (the rib and the lug's bottom are on
# one row along the barrel). Scale 2.77 px/mm: the barrel spans 420 px from the
# cylinder's front face to the muzzle (152.4 mm, 6") and the gun 819 px from
# muzzle to the back of the grip (295.3 mm, the factory 11 5/8"); both agree.
PX_MM = 2.77
X0_PX = 626.0         # the cylinder's rear face (gun x = 0)
BORE_PY = 125.0       # the bore axis (the ejector rod's slot is centred 14.3 mm below it)


def P(px, py):
    """Photo pixel -> gun mm (x forward from the cylinder's rear face, z up from the bore)."""
    return ((X0_PX - px) / PX_MM, (BORE_PY - py) / PX_MM)


def PT(pts):
    return [P(px, py) for px, py in pts]


# ---------------------------------------------------------------- the gun's own frame (mm)
CYL_L = 44.4          # cylinder: photo 503..626
CYL_R = 22.25         # 1.75" across (the photo's 130 px includes its dark rim)
CYL_Z = -14.3         # cylinder axis: the rod's slot, 152..176 px
CH_R = 5.95           # chamber (a .44 case is 11.6 mm across)
RIM_R = 6.55          # case rim, 13.1 mm
BBL_X0 = CYL_L + 0.2                          # barrel's rear face: the gap
WIN_X0, WIN_X1 = P(639, 0)[0], P(494, 0)[0]   # frame window, rear (recoil shield face) / front
WIN_TOP, WIN_BOT = P(0, 103)[1], P(0, 233)[1]
MUZZLE_X = P(74, 0)[0]                        # 199.3
LUG_FRONT = P(80, 0)[0]
FRAME_FRONT = P(443, 0)[0]                    # where the barrel enters the frame (66.1)
RIB_TOP = P(0, 91.5)[1]                       # 12.1
BBL_R0, BBL_R1 = 10.0, 9.7                    # barrel radius at the frame / the muzzle
BORE_R = 5.45                                 # .429" groove
RIB_HW = 4.6                                  # flat rib on top of the barrel
LUG_BOT = P(0, 179)[1]                        # -19.5: the full-length underlug
LUG_HW = 8.4
STRAP_TOP = P(0, 85.5)[1]                     # 14.3
STRAP_BOT = WIN_TOP
FRAME_HW = 11.6                               # frame side plates (half width; N frame)
STRAP_HW = 7.6
SHIELD_X = WIN_X0 - 2.0
# The crane's hinge pin (lower left of the cylinder, along X) and how far it swings.
HINGE_Y, HINGE_Z = 8.5, -38.5
SWING_DEG = -95.0

# Side outlines, traced (photo px -> mm).
FRAME = PT([
    (443, 91), (450, 87.5), (468, 85.5), (662, 85.5), (664, 96), (662, 104),          # topstrap
    (680, 138), (703, 158), (730, 173), (753, 183), (777, 188),                         # the hump behind the hammer
    (785, 200), (792, 250), (812, 300), (835, 370), (852, 430), (860, 465), (855, 478),  # backstrap (inside the wood)
    (800, 481), (735, 478), (729, 470), (727, 420), (722, 370), (708, 340),               # butt, front strap
    (688, 318), (672, 298), (666, 280), (654, 270),                                     # behind the trigger guard
    (547, 258), (526, 257), (455, 256), (450, 248), (450, 150), (443, 140),             # under the cylinder, front
])
GRIP = PT([  # the wood: horn at the top, the filler behind the guard, square butt
    (767, 190), (780, 210), (789, 238), (800, 255), (823, 300), (849, 350), (865, 400), (880, 450),
    (891, 480), (893, 489), (889, 496), (850, 495), (800, 493), (750, 491), (721, 489), (719, 470),
    (722, 450), (718, 400), (713, 352), (695, 333), (672, 318), (661, 300), (660, 282), (664, 273),
    (682, 266), (710, 255), (730, 202), (752, 193),
])
TRIGGER_GUARD = PT([
    (549, 257), (532, 275), (525, 295), (526, 315), (535, 333), (552, 346), (575, 354), (600, 356),
    (625, 350), (643, 338), (654, 320), (657, 300), (655, 282), (650, 266),
])
GUARD_HOLE = PT([
    (553, 262), (538, 278), (533, 298), (536, 318), (546, 334), (563, 343), (585, 347), (608, 346),
    (628, 339), (641, 325), (646, 305), (645, 285), (640, 270), (632, 262),
])
TRIGGER = PT([
    (582, 259), (589, 280), (596, 300), (597, 316), (590, 327), (578, 333), (568, 335), (580, 330),
    (592, 320), (600, 305), (605, 292), (612, 282), (625, 274), (632, 268), (630, 258),
])
HAMMER = PT([  # the spur points back, over the hump
    (660, 100), (687, 113), (697, 122), (710, 119), (730, 115), (747, 117), (752, 123), (743, 128),
    (720, 129), (705, 134), (695, 142), (682, 140), (670, 125), (662, 112),
])
REAR_SIGHT = PT([(620, 85.5), (620, 79), (659, 79), (659, 69), (664, 69), (668, 79), (668, 96), (664, 96)])
FRONT_SIGHT = PT([(147.5, 91.5), (147.5, 80), (97, 64), (95, 65), (95, 91.5)])
THUMBPIECE = P(706, 191)          # round, checkered, r 4.9 mm
LATCH = P(668, 192)
SW_LOGO = P(675, 237)             # the S&W emblem on the left of the frame, r 8 mm
MEDALLION = P(753, 277)           # on the wood, r 4.9 mm
GRIP_SCREW = P(805, 367)
ROD_SLOT = (P(333, 0)[0], P(0, 152)[1], P(0, 176)[1])   # rear end x / top / bottom of the rod's window

# The arms (raw_assets/characters/fp_arms, the shared pistol hands): their grip
# frame's backstrap top (GRIP_TOP - FWD * half depth) goes on this gun's
# backstrap under the wood's horn (photo 780, 210), less HAND_DROP: the hands
# ride that much lower on the tall target grip, or their thumbs (posed for the
# Five-seveN, whose sights sit 16 mm higher above the hand) cover the sights.
ARMS_WEB = (-0.0780, -0.0413)
WEB_MM = P(780, 210)
HAND_DROP = 0.012
ORIGIN_X = ARMS_WEB[0] - WEB_MM[0] / 1000.0
ORIGIN_Z = ARMS_WEB[1] - WEB_MM[1] / 1000.0 + HAND_DROP


def M(x, z):
    """Gun mm (x, z) -> weapon-space metres (x, z)."""
    return (x / 1000.0 + ORIGIN_X, z / 1000.0 + ORIGIN_Z)


def MX(x):
    return x / 1000.0 + ORIGIN_X


def MZ(z):
    return z / 1000.0 + ORIGIN_Z


def MM(v):
    return v / 1000.0


def W(x, y, z):
    """Gun mm (x, y, z) -> weapon-space metres (Blender: +Y left)."""
    return (MX(x), y / 1000.0, MZ(z))


# ---------------------------------------------------------------- materials
def wood_material(name, checkered=False):
    """Red rosewood / goncalo alves as in the photo: dark figured grain running down the grip, an oil
    finish. `checkered`: the grips' checkered panels (sharp pyramids, 1.3 mm pitch, through the bake)."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.45 if checkered else 0.3
    bsdf.inputs["Coat Weight"].default_value = 0.15 if checkered else 0.5
    bsdf.inputs["Coat Roughness"].default_value = 0.12
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    # Grain runs down the grip (about 22 deg back from vertical): bands across it.
    mp.inputs["Rotation"].default_value = (0.0, math.radians(-68.0), 0.0)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    wave = N.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 260.0
    wave.inputs["Distortion"].default_value = 5.0
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 0.9
    L.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fig = N.new("ShaderNodeTexNoise")
    fig.inputs["Scale"].default_value = 60.0
    fig.inputs["Detail"].default_value = 8.0
    L.new(mp.outputs["Vector"], fig.inputs["Vector"])
    mixf = N.new("ShaderNodeMath")
    mixf.operation = "MULTIPLY_ADD"
    mixf.inputs[1].default_value = 0.75
    L.new(wave.outputs["Fac"], mixf.inputs[0])
    L.new(fig.outputs["Fac"], mixf.inputs[2])
    ramp = N.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.3, (0.02, 0.004, 0.0025, 1)
    e[1].position, e[1].color = 0.95, (0.115, 0.024, 0.013, 1)
    mid = ramp.color_ramp.elements.new(0.6)
    mid.color = (0.05, 0.0105, 0.006, 1)
    L.new(mixf.outputs[0], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.0002
    if checkered:
        # Two sets of V grooves at +-45 degrees in the grip's side plane: diamonds.
        tris = []
        for ang in (45.0, -45.0):
            mp2 = N.new("ShaderNodeMapping")
            mp2.inputs["Rotation"].default_value = (0.0, math.radians(ang), 0.0)
            L.new(tc.outputs["Object"], mp2.inputs["Vector"])
            w2 = N.new("ShaderNodeTexWave")
            w2.wave_type = "BANDS"
            w2.bands_direction = "X"
            w2.wave_profile = "TRI"
            w2.inputs["Scale"].default_value = 770.0
            w2.inputs["Distortion"].default_value = 0.0
            L.new(mp2.outputs["Vector"], w2.inputs["Vector"])
            tris.append(w2)
        mn = N.new("ShaderNodeMath")
        mn.operation = "MINIMUM"
        L.new(tris[0].outputs["Fac"], mn.inputs[0])
        L.new(tris[1].outputs["Fac"], mn.inputs[1])
        bump.inputs["Strength"].default_value = 0.9
        bump.inputs["Distance"].default_value = 0.0005
        L.new(mn.outputs[0], bump.inputs["Height"])
        dark = N.new("ShaderNodeMix")
        dark.data_type = "RGBA"
        dark.inputs["B"].default_value = (0.012, 0.003, 0.002, 1)
        inv = N.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 0.6
        L.new(mn.outputs[0], inv.inputs[1])
        L.new(inv.outputs[0], dark.inputs["Factor"])
        L.new(ramp.outputs["Color"], dark.inputs["A"])
        L.new(dark.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        L.new(wave.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# Polished stainless: bright, a light brushed grain along the barrel and frame.
M_STAIN = mat("stainless", (0.66, 0.66, 0.67), 0.19, 1.0, wear=(0.76, 0.76, 0.77), wear_rough=0.1, brushed=0.08)
M_SATIN = mat("stainless_satin", (0.58, 0.58, 0.59), 0.3, 1.0, brushed=0.1)   # the bead-blasted rib, sight base
M_DARK = mat("dark_steel", (0.03, 0.03, 0.032), 0.4, 0.9)                   # sight blade, screws' slots
M_BORE = mat("bore", (0.006, 0.006, 0.007), 0.6, 0.6)
M_WOOD = wood_material("wood")
M_CHECK = wood_material("wood_checkered", checkered=True)
M_RED = mat("red_insert", (0.55, 0.02, 0.015), 0.35, 0.0, emission=((0.6, 0.02, 0.01), 0.4))
M_WHITE = mat("white_outline", (0.82, 0.82, 0.8), 0.5, 0.0)
M_GOLD = mat("medallion", (0.85, 0.62, 0.22), 0.25, 1.0)
M_BRASS = mat("brass", (0.80, 0.57, 0.25), 0.22, 1.0, wear=(0.9, 0.75, 0.45), wear_rough=0.15)
M_NICKEL = mat("primer", (0.62, 0.6, 0.56), 0.3, 1.0)
M_COPPER = mat("jacket", (0.75, 0.40, 0.22), 0.28, 1.0)
M_LEAD = mat("lead", (0.32, 0.32, 0.34), 0.55, 0.8)
M_LOADER = mat("loader_black", (0.02, 0.02, 0.021), 0.5, 0.2, bump_scale=2500, bump_strength=0.25)
M_MARK = mat("engraving", (0.12, 0.12, 0.125), 0.45, 1.0)
MATERIALS = [M_STAIN, M_SATIN, M_DARK, M_BORE, M_WOOD, M_CHECK, M_RED, M_WHITE, M_GOLD, M_BRASS, M_NICKEL, M_COPPER,
             M_LEAD, M_LOADER, M_MARK]

PART_IDS = {"body": 0, "cylinder": 1, "crane": 2, "speedloader": 3,
            "round_0": 4, "round_1": 5, "round_2": 6, "round_3": 7, "round_4": 8, "round_5": 9}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def hi():
    return hs.D["text"]


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m=M_MARK, extrude=0.00010):
    ob = hs.text(name, body, size, loc, rot, m, extrude=extrude)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def chaikin(pts, n=2, closed=True):
    p = np.asarray(pts, float)
    for _ in range(n):
        q = np.roll(p, -1, 0)
        p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p


def profile(name, pts_mm, width_mm, y_mm=0.0, smooth=1):
    """Side outline (mm) extruded across Y."""
    pts = chaikin(pts_mm, smooth) if smooth else np.asarray(pts_mm, float)
    return hs.side_profile(name, [M(x, z) for x, z in pts], MM(width_mm), y=MM(y_mm))


def cyl_x(name, r_mm, x0, x1, verts=48, z_mm=0.0, y_mm=0.0, r2_mm=None, fixed=False):
    return hs.cyl_x(name, MM(r_mm), MX(x0), MX(x1), verts=verts, z=MZ(z_mm), y=MM(y_mm),
                    radius2=None if r2_mm is None else MM(r2_mm), fixed=fixed)


def lathe(name, prof_mm, z_mm=0.0, y_mm=0.0, verts=48):
    ob = hs.lathe_x(name, [(MX(x), MM(r)) for x, r in prof_mm], verts=verts)
    ob.data.transform(Matrix.Translation((0, MM(y_mm), MZ(z_mm))))
    return ob


def sphere(name, r_mm, loc_mm, segs=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=hs.nverts(segs), ring_count=max(6, hs.nverts(segs) // 2),
                                         radius=MM(r_mm), location=W(*loc_mm))
    ob = bpy.context.active_object
    ob.name = name
    return ob


def box(name, size_mm, loc_mm, rot=(0, 0, 0)):
    return hs.box(name, tuple(MM(s) for s in size_mm), W(*loc_mm), rot)


# ---------------------------------------------------------------- SDF helpers (the grips)
def ss(e0, e1, t):
    t = np.clip((t - F32(e0)) / F32(e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rinter(a, b, r):
    a = a + F32(r)
    b = b + F32(r)
    return np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0) - F32(r)


def poly_sdf(x, z, V2):
    d = None
    s = None
    n = len(V2)
    for i in range(n):
        ax, az = V2[i]
        bx, bz = V2[i - 1]
        ex, ez = F32(bx - ax), F32(bz - az)
        wx, wz = x - F32(ax), z - F32(az)
        h = np.clip((wx * ex + wz * ez) / F32(ex * ex + ez * ez + 1e-12), 0.0, 1.0)
        dx, dz = wx - ex * h, wz - ez * h
        dd = dx * dx + dz * dz
        c1 = z >= F32(az)
        c2 = z < F32(bz)
        c3 = ex * wz > ez * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        if d is None:
            d = dd
            s = np.where(flip, F32(-1), F32(1))
        else:
            d = np.minimum(d, dd)
            s = np.where(flip, -s, s)
    return s * np.sqrt(d)


class FnPrim(sdf.Prim):
    def __init__(self, lo, hi_, f):
        self.lo, self.hi, self.f = np.asarray(lo, float), np.asarray(hi_, float), f

    def aabb(self):
        return self.lo, self.hi

    def __call__(self, x, y, z):
        return self.f(x, y, z)


def sculpt(name, lo, hi_, model, h, m):
    lo = tuple(v + h * k for v, k in zip(lo, (0.371, 0.413, 0.297)))
    grid = sdf.Grid(lo, hi_, h)
    print(f"magnum44: sculpting {name} on {grid.shape} ({grid.size / 1e6:.1f} M cells)")
    F = model.evaluate(grid)
    me = sdf.to_mesh(name, F, grid)
    del F
    ob = hs.link(bpy.data.objects.new(name, me))
    me.materials.append(m)
    me.shade_smooth()
    PART_OF[ob.name] = CURRENT[0]
    return ob


def decimated(ob, tris):
    dec = ob.modifiers.new("decimate", "DECIMATE")
    dec.ratio = min(1.0, tris / max(1, 2 * len(ob.data.polygons)))
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    return ob


# ---------------------------------------------------------------- frame
def build_frame():
    part("body")
    # Side plates: the traced outline at the frame's width, the cylinder window cut out.
    fr = profile("frame", FRAME, 2 * FRAME_HW, smooth=1)
    win = box("frame_window", (WIN_X1 - WIN_X0, 40.0, WIN_TOP - WIN_BOT),
              ((WIN_X0 + WIN_X1) / 2, 0.0, (WIN_TOP + WIN_BOT) / 2))
    hs.cut(fr, win)
    # The topstrap is narrower than the side plates: shave its sides above the window.
    for s_ in (1, -1):
        shave = box(f"strap_shave{s_}", (FRAME_FRONT - WIN_X0 + 4.0, 10.0, 14.0),
                    ((FRAME_FRONT + WIN_X0) / 2, s_ * (STRAP_HW + 5.0), STRAP_BOT + 7.0 - 0.01))
        hs.cut(fr, shave)
    # The barrel's way in at the front, and the crane's seat in the frame's lower front.
    hs.cut(fr, cyl_x("frame_bore", BBL_R0 + 0.3, WIN_X1 - 1.0, FRAME_FRONT + 1.0, verts=40))
    hs.cut(fr, box("crane_seat", (P(450, 0)[0] - WIN_X1 + 0.6, 2 * FRAME_HW + 2.0, 27.5),
                   ((WIN_X1 + P(450, 0)[0]) / 2 + 0.3, 0.0, -33.0)))
    finish(fr, M_STAIN, bevel=MM(1.1), segments=3)
    # Rounded topstrap.
    cap = cyl_x("strap_round", STRAP_HW, WIN_X0 - 2.0, FRAME_FRONT - 1.0, verts=40, z_mm=STRAP_TOP - STRAP_HW + 0.3)
    hs.cut(cap, box("strap_round_cut", (FRAME_FRONT - WIN_X0 + 8.0, 20.0, 20.0),
                    ((FRAME_FRONT + WIN_X0) / 2, 0.0, STRAP_TOP - STRAP_HW + 0.3 - 10.0)))
    finish(cap, M_SATIN, bevel=MM(0.4))
    # Recoil shield: the round boss behind the cylinder, the firing-pin bushing.
    sh = cyl_x("shield", CYL_R - 2.5, SHIELD_X, WIN_X0 + 0.3, verts=56, z_mm=CYL_Z)
    hs.cut(sh, box("shield_top", (12.0, 50.0, 20.0), (SHIELD_X / 2, 0.0, STRAP_BOT + 10.0)))
    finish(sh, M_STAIN, bevel=MM(1.2))
    finish(cyl_x("firing_pin_bush", 2.6, WIN_X0 - 0.2, WIN_X0 + 0.5, verts=20), M_SATIN, bevel=MM(0.2))
    if hi():
        finish(box("hammer_slot", (14.0, 7.4, 4.0), (-18.0, 0.0, 5.5)), M_BORE, bevel=0)
    # Thumbpiece (cylinder release), left side: round and checkered, and the latch's boss in front of it.
    tx, tz = THUMBPIECE
    finish(hs.cyl_y("thumbpiece", MM(4.9), MM(3.2), W(tx, FRAME_HW + 1.6, tz), verts=40), M_SATIN, bevel=MM(0.8))
    lx, lz = LATCH
    finish(hs.cyl_y("latch_boss", MM(4.6), MM(1.4), W(lx, FRAME_HW + 0.6, lz), verts=32), M_STAIN, bevel=MM(0.4))
    if hi():
        for i in range(-4, 5):
            for j in (0, 1):
                rib = box(f"tp_check{i}{j}", (0.45, 0.6, 9.0), (tx + i * 1.0, FRAME_HW + 3.25, tz),
                          rot=(0, math.radians(45 if j else -45), 0))
                finish(rib, M_DARK, bevel=0)
        finish(box("latch_slot", (5.5, 0.5, 0.7), (lx, FRAME_HW + 1.35, lz), rot=(0, math.radians(30), 0)), M_DARK,
               bevel=0)
    # The S&W emblem stamped on the left of the frame (a ring and the monogram).
    ex, ez = SW_LOGO
    if hi():
        ring = hs.cyl_y("emblem_ring", MM(8.0), MM(0.25), W(ex, FRAME_HW + 0.05, ez), verts=48)
        hs.cut(ring, hs.cyl_y("emblem_in", MM(7.2), MM(1.0), W(ex, FRAME_HW + 0.05, ez), verts=48))
        finish(ring, M_MARK, bevel=0)
        text("sw_logo", "S&W", MM(4.6), W(ex + 6.0, FRAME_HW + 0.12, ez - 1.6), (PI / 2, 0, PI), M_MARK)
    # Side plate (right): the seam and the screws.
    for (sx, sz) in (P(700, 240), P(660, 250), P(735, 175), P(690, 130)):
        y = -(FRAME_HW + 0.25)
        finish(hs.cyl_y(f"screw{sx:.0f}", MM(2.6), MM(0.7), W(sx, y, sz), verts=20), M_STAIN, bevel=MM(0.25))
        if hi():
            finish(box(f"screw_slot{sx:.0f}", (4.6, 0.5, 0.55), (sx, y - 0.35, sz), rot=(0, math.radians(20.0), 0)),
                   M_DARK, bevel=0)
    if hi():
        pts = [W(x, -(FRAME_HW + 0.02), z) for x, z in PT([(642, 128), (660, 112), (682, 132), (722, 162),
                                                           (748, 196), (735, 240), (690, 260), (645, 254)])]
        seam = hs.tube_path("sideplate_seam", pts, MM(0.22))
        PART_OF[seam.name] = CURRENT[0]
        finish(seam, M_DARK, bevel=0, smooth=False)
        text("model_no", "MOD. 629", MM(2.2), W(55.0, -(FRAME_HW + 0.12), -42.0), (PI / 2, 0, 0), M_MARK)


def build_guard_trigger_hammer():
    part("body")
    tg = profile("trigger_guard", TRIGGER_GUARD, 8.6, smooth=2)
    hs.cut(tg, profile("guard_hole", GUARD_HOLE, 14.0, smooth=2))
    finish(tg, M_STAIN, bevel=MM(1.6), segments=3)
    tr = profile("trigger", TRIGGER, 7.6, smooth=2)
    finish(tr, M_STAIN, bevel=MM(1.4), segments=3)
    hm = profile("hammer", HAMMER, 6.8, smooth=2)
    finish(hm, M_STAIN, bevel=MM(0.8), segments=3)
    # Checkering across the top of the spur (HIGH; baked into the normal map).
    if hi():
        (ax, az), (bx, bz) = P(699, 121), P(746, 116.5)
        for i in range(10):
            t = (i + 0.5) / 10
            cx, cz = ax + (bx - ax) * t, az + (bz - az) * t
            finish(box(f"spur_cut{i}", (0.55, 7.0, 0.8), (cx, 0.0, cz + 0.05), rot=(0, math.radians(-6.0), 0)),
                   M_DARK, bevel=0)


# ---------------------------------------------------------------- barrel, rib, lug, sights
def build_barrel():
    part("body")
    # The tube, tapering a little; the muzzle crowned and recessed.
    tube = lathe("barrel", [(BBL_X0, BBL_R0), (FRAME_FRONT, BBL_R0), (MUZZLE_X - 1.2, BBL_R1),
                            (MUZZLE_X, BBL_R1 - 0.9)], verts=64)
    hs.cut(tube, cyl_x("bore", BORE_R, BBL_X0 - 1.0, MUZZLE_X + 1.0, verts=36))
    finish(tube, M_STAIN, bevel=MM(0.5))
    finish(cyl_x("bore_dark", BORE_R + 0.05, MUZZLE_X - 6.0, MUZZLE_X - 1.0, verts=36), M_BORE, bevel=0)
    finish(lathe("crown", [(MUZZLE_X - 0.6, BORE_R + 0.6), (MUZZLE_X - 0.2, BBL_R1 - 1.2)], verts=48), M_SATIN,
           bevel=0)
    # Flat rib on top (bead blasted), from the frame to the muzzle.
    rib = box("rib", (MUZZLE_X - FRAME_FRONT + 0.5, 2 * RIB_HW, RIB_TOP - 4.0),
              ((MUZZLE_X + FRAME_FRONT) / 2 - 0.5, 0.0, (RIB_TOP + 4.0) / 2))
    finish(rib, M_SATIN, bevel=MM(0.6))
    web = box("rib_web", (MUZZLE_X - FRAME_FRONT - 0.5, 2 * (RIB_HW + 1.8), 5.0),
              ((MUZZLE_X + FRAME_FRONT) / 2 - 0.5, 0.0, RIB_TOP - 5.2))
    finish(web, M_STAIN, bevel=MM(1.8))
    # Full-length underlug, its front square to the muzzle with rounded corners.
    lx0 = P(450, 0)[0]
    lug = profile("underlug", [(lx0, -3.0), (LUG_FRONT, -3.0), (LUG_FRONT, LUG_BOT + 4.0),
                               (LUG_FRONT - 1.5, LUG_BOT + 0.8), (LUG_FRONT - 4.0, LUG_BOT), (lx0, LUG_BOT)],
                  2 * LUG_HW, smooth=0)
    hs.cut(lug, cyl_x("rod_channel", 3.4, lx0 - 1.0, LUG_FRONT - 7.0, verts=24, z_mm=CYL_Z))
    # The rod's window on the left, behind the frame-end of the lug (the crane's side).
    sx0, sz0, sz1 = ROD_SLOT
    r = (sz0 - sz1) / 2
    zc = (sz0 + sz1) / 2
    slot = cyl_x("rod_slot", r, lx0 - 2.0, sx0 - r, verts=24, z_mm=zc, y_mm=LUG_HW)
    slot_end = sphere("rod_slot_end", r, (sx0 - r, LUG_HW, zc))
    hs.cut(lug, slot)
    hs.cut(lug, slot_end)
    finish(lug, M_STAIN, bevel=MM(3.0), segments=4, angle=60.0)
    # Front sight: the black ramp; rear: the adjustable sight, its blade and notch at the back.
    fs = profile("front_sight", FRONT_SIGHT, 3.2, smooth=0)
    finish(fs, M_DARK, bevel=MM(0.3))
    rs = profile("rear_sight", REAR_SIGHT, 2 * 5.6, smooth=0)
    nx = P(661.5, 0)[0]
    hs.cut(rs, box("rear_notch", (8.0, 3.0, 3.2), (nx, 0.0, P(0, 69)[1])))
    finish(rs, M_DARK, bevel=MM(0.35))
    if hi():
        finish(hs.cyl_y("windage_screw", MM(1.4), MM(1.0), W(-6.0, -5.9, P(0, 82)[1]), verts=16), M_SATIN, bevel=0)
        finish(hs.cyl_z("elev_screw", MM(1.5), MM(0.8), W(-10.5, 0.0, P(0, 79)[1] + 0.3), verts=16), M_SATIN, bevel=0)
        # Markings: "SMITH & WESSON" on the left of the barrel (photo), ".44 MAGNUM" on the right.
        text("maker", "SMITH & WESSON", MM(3.4), W(P(345, 0)[0], LUG_HW + 0.15, P(0, 132)[1]), (PI / 2, 0, PI),
             M_MARK)
        text("cal", ".44 MAGNUM", MM(3.6), W(P(290, 0)[0], -(LUG_HW + 0.15), P(0, 132)[1]), (PI / 2, 0, 0), M_MARK)


# ---------------------------------------------------------------- the wood grips (sculpt)
GRIP_OUT = chaikin([M(x, z) for x, z in GRIP], 2)
GRIP_LO = (MX(P(898, 0)[0]), -0.024, MZ(P(0, 500)[1]))
GRIP_HI = (MX(P(655, 0)[0]), 0.024, MZ(P(0, 186)[1]))


def grip_hw(x, z):
    """Half width: 15 mm at the top round the frame, swelling to 18.5 at the palm, 16 at the butt."""
    zz = (z - F32(ORIGIN_Z)) * F32(1000.0)
    swell = ss(-35.0, -70.0, zz) * (F32(1.0) - ss(-100.0, -130.0, zz))
    return F32(0.0150) + F32(0.0035) * swell + F32(0.0012) * ss(-95.0, -125.0, zz)


def grip_f(x, y, z):
    return rinter(poly_sdf(x, z, GRIP_OUT), np.abs(y) - grip_hw(x, z), 0.0062)


def grip_model():
    m = sdf.Model()
    m.add(FnPrim(GRIP_LO, GRIP_HI, grip_f))
    return m


# The checkered panel on each side (photo px; a smooth border round it, below the medallion).
CHECK_PANEL = PT([(724, 303), (790, 296), (832, 335), (858, 400), (874, 466), (737, 470), (731, 400)])


def checker_panels(ob):
    """Faces on the grips' sides inside CHECK_PANEL get the checkered wood."""
    me = ob.data
    me.materials.append(M_CHECK)
    poly = [M(x, z) for x, z in CHECK_PANEL]

    def inside(px, pz):
        c = False
        for i in range(len(poly)):
            (ax, az), (bx, bz) = poly[i], poly[i - 1]
            if (az > pz) != (bz > pz) and px < (bx - ax) * (pz - az) / (bz - az) + ax:
                c = not c
        return c
    idx = []
    for f in me.polygons:
        if abs(f.normal.y) > 0.55 and inside(f.center.x, f.center.z):
            idx.append(1)
        else:
            idx.append(f.material_index)
    me.polygons.foreach_set("material_index", idx)


def build_grips():
    part("body")
    if hi():
        ob = sculpt("grip_high", GRIP_LO, GRIP_HI, grip_model(), 0.0009 if args.fast else 0.0004, M_WOOD)
    else:
        ob = decimated(sculpt("grip_low", GRIP_LO, GRIP_HI, grip_model(), 0.0010, M_WOOD), 2600)
    checker_panels(ob)
    hs.PARTS.append(ob)
    # The gold S&W medallions near the top of each panel, and the grip screw (left) / escutcheon (right).
    for s in (1, -1):
        x, z = MEDALLION
        y = s * (float(grip_hw(F32(MX(x)), F32(MZ(z)))) * 1000.0 + 0.05)
        finish(hs.cyl_y(f"medallion{s}", MM(5.6), MM(0.9), W(x, y, z), verts=40), M_GOLD, bevel=MM(0.3))
        if hi():
            text(f"med_sw{s}", "S&W", MM(4.2), W(x - 4.0 * s, y + s * 0.45, z - 1.4),
                 (PI / 2, 0, PI if s > 0 else 0), M_MARK)
        x2, z2 = GRIP_SCREW
        y2 = s * (float(grip_hw(F32(MX(x2)), F32(MZ(z2)))) * 1000.0 - 0.1)
        finish(hs.cyl_y(f"grip_screw{s}", MM(2.6), MM(1.0), W(x2, y2, z2), verts=24), M_STAIN, bevel=MM(0.3))


# ---------------------------------------------------------------- cylinder, crane, rounds
def chamber_yz(k, r=None):
    """Centre (y, z) mm of chamber k (0 on the bore), turning toward the gun's right."""
    r = -CYL_Z if r is None else r
    a = 2 * PI * k / 6
    return (-r * math.sin(a), CYL_Z + r * math.cos(a))


def build_cylinder():
    part("cylinder")
    cyl = lathe("cylinder", [(0.0, CYL_R - 1.2), (0.6, CYL_R), (CYL_L - 2.0, CYL_R), (CYL_L, CYL_R - 2.2)],
                z_mm=CYL_Z, verts=96)
    for k in range(6):
        y, z = chamber_yz(k)
        hs.cut(cyl, cyl_x(f"chamber{k}", CH_R, -1.0, CYL_L + 1.0, verts=32, z_mm=z, y_mm=y))
        # Counterbores for the rims at the rear.
        hs.cut(cyl, cyl_x(f"rimcut{k}", RIM_R + 0.25, -1.0, 1.4, verts=32, z_mm=z, y_mm=y))
        # Cylinder stop notches over each chamber, at the rear third.
        sy, sz = chamber_yz(k, CYL_R)
        hs.cut(cyl, hs.box(f"stop{k}", (MM(5.5), MM(2.8), MM(2.8)), W(P(610, 0)[0], sy, sz),
                           rot=(-2 * PI * k / 6, 0, 0)))
    finish(cyl, M_STAIN, bevel=MM(0.5), segments=3)
    # Ejector star at the rear (sits in the rim cuts) and the ratchet.
    star = cyl_x("star", 13.5, -0.05, 1.3, verts=48, z_mm=CYL_Z)
    for k in range(6):
        y, z = chamber_yz(k)
        hs.cut(star, cyl_x(f"star_ch{k}", RIM_R + 0.35, -1.0, 2.0, verts=32, z_mm=z, y_mm=y))
    finish(star, M_SATIN, bevel=MM(0.3))
    finish(cyl_x("ratchet", 4.2, -1.2, -0.05, verts=12, z_mm=CYL_Z, fixed=True), M_SATIN, bevel=MM(0.2))
    # The ejector rod forward under the barrel, its knurled tip at the lug's front.
    finish(cyl_x("ejector_rod", 2.9, CYL_L, MUZZLE_X - 6.0, verts=20, z_mm=CYL_Z), M_STAIN, bevel=MM(0.2))
    finish(cyl_x("rod_tip", 3.3, MUZZLE_X - 13.0, MUZZLE_X - 5.5, verts=24, z_mm=CYL_Z), M_SATIN, bevel=MM(0.5))


def build_crane():
    part("crane")
    # The yoke: a collar round the rod at the cylinder's front, an arm to the hinge pin, the pin's tube.
    finish(cyl_x("crane_collar", 7.6, CYL_L + 0.2, P(451, 0)[0], verts=40, z_mm=CYL_Z), M_STAIN, bevel=MM(0.6))
    p0 = V(W(CYL_L + 4.0, 0.0, CYL_Z))
    p1 = V(W(CYL_L + 4.0, HINGE_Y, HINGE_Z))
    d = p1 - p0
    arm = hs.box("crane_arm", (MM(7.0), MM(8.0), d.length), (0, 0, 0))
    arm.rotation_euler = (math.atan2(-d.y, d.z), 0, 0)
    arm.location = (p0 + p1) / 2
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True)
    finish(arm, M_STAIN, bevel=MM(1.5))
    finish(cyl_x("crane_pin", 4.2, CYL_L + 0.2, P(451, 0)[0], verts=28, z_mm=HINGE_Z, y_mm=HINGE_Y), M_STAIN,
           bevel=MM(0.5))
    # It fills the frame's lower front when shut (photo 450..494 px, under the lug).
    x0, x1 = WIN_X1, P(450.5, 0)[0]
    z0, z1 = P(0, 255)[1], LUG_BOT - 0.4
    fill = box("crane_fill", (x1 - x0, 2 * FRAME_HW - 0.6, z1 - z0), ((x0 + x1) / 2, 0.0, (z0 + z1) / 2))
    finish(fill, M_STAIN, bevel=MM(0.8))


def cartridge(name, y, z, x0=-0.05, loader=False):
    """A .44 Magnum JHP: rim, case, bullet (x0 = rear of the rim, mm)."""
    obs = []
    rim = cyl_x(name + "_rim", RIM_R, x0, x0 + 1.4, verts=32, z_mm=z, y_mm=y)
    case = cyl_x(name + "_case", 5.8, x0 + 1.4, x0 + 32.6, verts=24, z_mm=z, y_mm=y)
    head = cyl_x(name + "_primer", 2.2, x0 - 0.05, x0 + 0.2, verts=16, z_mm=z, y_mm=y)
    nose = lathe(name + "_bullet", [(x0 + 32.4, 5.45), (x0 + 35.0, 5.45), (x0 + 38.6, 4.2), (x0 + 40.0, 2.4),
                                    (x0 + 40.2, 0.5)], z_mm=z, y_mm=y, verts=20)
    finish(rim, M_BRASS, bevel=MM(0.25))
    finish(case, M_BRASS, bevel=0)
    finish(head, M_NICKEL, bevel=0)
    finish(nose, M_COPPER, bevel=0)
    obs += [rim, case, head, nose]
    if hi():
        hp = cyl_x(name + "_hp", 1.5, x0 + 39.0, x0 + 40.4, verts=12, z_mm=z, y_mm=y)
        finish(hp, M_LEAD, bevel=0)
        text(name + "_stamp", "44 REM MAG", MM(1.1), W(x0 - 0.12, y + 4.6, z - 0.6),
             (0, -PI / 2, 0), M_MARK)
    return obs


def build_rounds():
    for k in range(6):
        part(f"round_{k}")
        y, z = chamber_yz(k)
        cartridge(f"round{k}", y, z)


def swing_matrix():
    """Rotation about the crane's hinge pin (a line along X), as the game swings it."""
    hinge = V(W(0.0, HINGE_Y, HINGE_Z))
    hinge.x = 0.0
    return Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(SWING_DEG), 4, "X") @ Matrix.Translation(-hinge)


def build_speedloader():
    """Six rounds held in a loader, seated in the cylinder as it sits swung out."""
    part("speedloader")
    obs = []
    for k in range(6):
        y, z = chamber_yz(k)
        obs += cartridge(f"sl{k}", y, z, x0=-0.4, loader=True)
    body = cyl_x("loader_body", 17.5, -11.5, -1.0, verts=48, z_mm=CYL_Z)
    for k in range(6):
        y, z = chamber_yz(k)
        hs.cut(body, cyl_x(f"loader_hole{k}", RIM_R + 0.3, -3.2, 0.0, verts=24, z_mm=z, y_mm=y))
    finish(body, M_LOADER, bevel=MM(1.2))
    knob = cyl_x("loader_knob", 7.0, -21.0, -11.0, verts=32, z_mm=CYL_Z)
    finish(knob, M_LOADER, bevel=MM(1.2))
    if hi():
        for i in range(18):
            rib = box(f"knob_rib{i}", (9.0, 1.0, 1.0), (-16.0, 0.0, CYL_Z + 7.0))
            rib.data.transform(Matrix.Translation(-V(W(-16.0, 0.0, CYL_Z))))
            rib.data.transform(Matrix.Rotation(2 * PI * i / 18, 4, "X"))
            rib.data.transform(Matrix.Translation(V(W(-16.0, 0.0, CYL_Z))))
            finish(rib, M_LOADER, bevel=0)
    for ob in list(hs.PARTS):
        if PART_OF.get(ob.name) == "speedloader":
            ob.matrix_world = swing_matrix() @ ob.matrix_world


# ---------------------------------------------------------------- build
def build(detail, name, swung=False):
    hs.set_detail(detail)
    PART_OF.clear()
    build_frame()
    build_guard_trigger_hammer()
    build_barrel()
    build_grips()
    build_cylinder()
    build_crane()
    build_rounds()
    if swung or detail is not hs.HIGH or args.out:
        build_speedloader()
    if swung:
        for ob in hs.PARTS:
            if PART_OF.get(ob.name, "body") in ("cylinder", "crane") or PART_OF.get(ob.name, "").startswith("round_"):
                ob.matrix_world = swing_matrix() @ ob.matrix_world
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
    if detail is not hs.HIGH:
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
        joined.data.shade_smooth()
        joined.data.set_sharp_from_angle(angle=math.radians(35))
        wn = joined.modifiers.new("wnormal", "WEIGHTED_NORMAL")
        wn.mode = "FACE_AREA"
        wn.weight = 100
        wn.keep_sharp = True
        bpy.ops.object.convert(target="MESH")
    print(f"magnum44 {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


# Moved apart for the bake (the parts nest inside each other within a millimetre).
EXPLODE = {"body": 0.0, "cylinder": 0.3, "crane": 0.6, "speedloader": -0.6,
           "round_0": 0.9, "round_1": 1.0, "round_2": 1.1, "round_3": 1.2, "round_4": 1.3, "round_5": 1.4}


def explode(ob, sign):
    me = ob.data
    pid = np.empty(len(me.polygons), np.int32)
    me.attributes["part_id"].data.foreach_get("value", pid)
    loop_start = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_start", loop_start)
    loop_total = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", loop_total)
    loop_vert = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", loop_vert)
    vpart = np.zeros(len(me.vertices), np.int32)
    vpart[loop_vert] = np.repeat(pid, loop_total)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    for pname, i in PART_IDS.items():
        co[vpart == i, 1] += sign * EXPLODE[pname]
    me.vertices.foreach_set("co", co.ravel())
    me.update()


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
        print(f"magnum44: part {pname}: {bakeutil.tri_count(ob)} tris")
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


def print_data():
    """WeaponData numbers in Godot's weapon space (x, y = up, z = right)."""
    def g(x, y, z):
        bx, by, bz = W(x, y, z)
        return f"Vector3({bx:.4f}, {bz:.4f}, {-by:.4f})"
    print("muzzle_point =", g(MUZZLE_X, 0.0, 0.0))
    print("cylinder_axis =", g(-70.0, 0.0, CYL_Z), " # x: 60 mm ahead of it is the cylinder's rear face less 10")
    print("crane_hinge =", g(0.0, HINGE_Y, HINGE_Z))
    print("crane_swing_deg =", SWING_DEG)
    print("cylinder_gap_point =", g(CYL_L + 0.1, 0.0, 0.0))
    (rx, rz), (fx, fz) = P(661.5, 69), P(96, 64)
    k = (fz - rz) / (fx - rx)
    for name, x in (("ads_eye_position", -420.0), ("ads_look_target", 1000.0)):
        z = rz + (x - rx) * k
        print(name, "=", f"Vector3({MX(x):.4f}, {MZ(z):.4f}, 0)")
    print("grip_pivot =", g(*P(790, 330)[:1], 0.0, P(790, 330)[1]))
    print("overall length mm =", MUZZLE_X - P(893, 0)[0])


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
    # A studio with bright overhead softboxes: polished stainless needs something to reflect.
    # (The world's Generated Z is the view direction's z: -1 down .. 1 up.)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.22, 0.225, 0.235, 1)
    hz = ramp.color_ramp.elements.new(0.3)
    hz.color = (0.12, 0.122, 0.13, 1)
    ramp.color_ramp.elements[2].position = 0.75
    ramp.color_ramp.elements[2].color = (0.8, 0.81, 0.85, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world

    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, MZ(-140.0))
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.05, 0, -0.05), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.3, -1.0, 0.9), 40, 1.6, sy=0.5)
    area("strip_top", (0.05, 0.0, 0.9), 30, 2.0, sy=0.18)
    area("fill", (0.4, 1.1, 0.3), 30, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.2, -0.3, 0.4), 35, 0.7, (1.0, 0.82, 0.62))
    area("kick", (-1.0, 0.3, 0.1), 20, 0.8, (0.9, 0.95, 1.0))
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
    d.clip_start = 0.005
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"magnum44: rendered {path}")


def render_previews(stem):
    # The loader is only shown in the game during a reload.
    for ob in bpy.data.objects:
        if ob.name.split(".")[0] == "speedloader" and not args.swung:
            ob.hide_render = True
    cam = setup_render(args.samples, args.res)
    c = V(W(40.0, 0.0, -45.0))
    shots = {
        "side": ((c.x, -1.3, c.z), (c.x, 0, c.z), 60, None, 0.0),
        "left": ((c.x, 1.3, c.z), (c.x, 0, c.z), 60, None, 0.0),
        "beauty": ((c.x + 0.42, -0.55, c.z + 0.25), (c.x, 0, c.z), 50, None, 5.6),
        "beauty_left": ((c.x - 0.25, 0.55, c.z + 0.22), (c.x, 0, c.z), 50, None, 5.6),
        "cylinder": ((MX(-30.0), 0.24, MZ(40.0)), W(20.0, 0.0, -14.0), 50, None, 4.0),
        "muzzle": ((MX(330.0), 0.12, MZ(30.0)), W(170.0, 0.0, -5.0), 50, None, 4.0),
        # Roughly the player's hip view (viewmodel_magnum44.tres eye, glTF -> Blender).
        "fp": ((-0.36, 0.105, 0.085), (0.6, 0.07, 0.055), None, 60, 0.0),
    }
    only = [s for s in args.only.split(",") if s]
    for key, (loc, target, lens, fov, fstop) in shots.items():
        if only and key not in only:
            continue
        shoot(cam, f"{stem}_{key}.png", loc, target, lens=lens or 50, fov_deg=fov, fstop=fstop)


# The photo's scale and where the gun's mm frame sits in it (set from the trace).
REF = {"px_mm": PX_MM, "x0_px": X0_PX, "bore_py": BORE_PY, "w": 960, "h": 562}


def render_overlay(path):
    """Orthographic left view at the photo's scale; with --photo, its outline drawn over the photo."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 2
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    Wd, Hd = REF["w"], REF["h"]
    scene.render.resolution_x, scene.render.resolution_y = Wd, Hd
    scene.view_settings.view_transform = "Standard"
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = Wd / REF["px_mm"] / 1000.0
    # Photo pixel (px, py) <-> gun mm: x = (REF.x0 - px) / px_mm for a left-side photo (muzzle to the left).
    cx_mm = (REF["x0_px"] - Wd / 2) / REF["px_mm"]
    cz_mm = (REF["bore_py"] - Hd / 2) / REF["px_mm"]
    cx, cz = MX(cx_mm), MZ(cz_mm)
    cam.location = (cx, 1.0, cz)
    cam.rotation_euler = (V((cx, 0, cz)) - V((cx, 1.0, cz))).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"magnum44: overlay render {path}")
    if not args.photo:
        return
    img = bpy.data.images.load(path)
    a = np.array(img.pixels[:], dtype=np.float32).reshape(Hd, Wd, 4)[::-1, :, 3]
    photo = bpy.data.images.load(os.path.abspath(args.photo))
    pw, ph = photo.size
    pp = np.array(photo.pixels[:], dtype=np.float32).reshape(ph, pw, photo.channels)[::-1, :, :3]
    pp = pp[:Hd, :Wd]
    m = a > 0.5
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 1, 1)
    out = pp.copy()
    out[m] = out[m] * 0.75 + np.array([0.0, 0.25, 0.35]) * 0.25
    out[edge] = (1.0, 0.0, 0.0)
    res = bpy.data.images.new("overlay", Wd, Hd, alpha=True)
    rgba = np.concatenate([out, np.ones((Hd, Wd, 1), np.float32)], axis=2)[::-1]
    res.pixels = rgba.ravel().tolist()
    res.filepath_raw = path
    res.file_format = "PNG"
    res.save()
    print(f"magnum44: overlay over the photo {path}")


# ---------------------------------------------------------------- run
if args.fast:
    args.samples = min(args.samples, 24)
if args.print_data:
    print_data()
elif args.from_gltf:
    bpy.ops.import_scene.gltf(filepath=args.from_gltf)
    render_previews(args.preview.rsplit(".", 1)[0])
elif args.out:
    high = build(hs.HIGH, "magnum44_high")
    low = build(hs.LOW, "magnum44_low")
    bakeutil.unwrap(low, boost={M_STAIN.name: 1.3, M_SATIN.name: 1.2, M_WOOD.name: 1.2, M_DARK.name: 0.8,
                                M_BORE.name: 0.3, M_RED.name: 1.0, M_WHITE.name: 1.0, M_GOLD.name: 1.4,
                                M_BRASS.name: 0.7, M_NICKEL.name: 0.7, M_COPPER.name: 0.6, M_LEAD.name: 0.5,
                                M_LOADER.name: 0.7, M_MARK.name: 1.5}, angle_deg=35.0)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    explode(high, 1)
    explode(low, 1)
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "magnum44", cage=0.0010, ray=0.004,
                                 ao_distance=0.015, grime=0.25, log=print)
    bpy.data.objects.remove(high)
    explode(low, -1)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "magnum44", emission_strength=1.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"magnum44: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        if args.swung:
            pass
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview or args.overlay:
    high = build(hs.HIGH, "magnum44_high", swung=args.swung)
    if args.overlay:
        render_overlay(args.overlay)
    else:
        render_previews(args.preview.rsplit(".", 1)[0])
