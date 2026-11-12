"""Glock 22 Gen 4: .40 S&W service pistol with a dropped-in auto sear ("switch")
and a 22-round extended magazine (owner, 2026-11-12). Second version, same day:
the owner called the first one "a piece of polygon chunk" and asked for a faithful,
detailed Glock on the Five-seveN's level of realism.

Real dimensions (Glock's published figures for the G22 Gen 4): slide 186.5 mm
long and 25.5 mm wide, barrel 114 mm, sight radius 165 mm, height with a flush
magazine 138 mm. The bore sits ~10 mm under the slide top (Glock's low bore axis),
front post 6.1 mm and rear sight 6.5 mm tall.

How it is built:
- Polymer frame: one signed-distance sculpt (raw_assets/_lib/sdf.py) so the grip,
  dust cover, beavertail and trigger guard blend into each other like a moulded
  part: Gen 4 finger grooves, the backstrap "hump", flared magazine well with the
  side cut-outs, squared trigger guard, single-slot accessory rail, rough-texture
  (RTF) panels on the grip as a pyramid stipple in the material.
- Steel: the slide, sights, barrel, controls and switch are hard-surface parts
  (booleans + bevels) from raw_assets/_lib/hardsurface.py.

The grip is on the Five-seveN's grip line (GRIP_TOP/AXIS, 25.5 x 15 mm half sizes)
so the shared first-person hands (raw_assets/characters/fp_arms/build.py) close on it,
and the trigger face sits where their index finger is (x ~ -0.005).

Moving parts (glTF nodes): body, slide (with sights, extractor and the switch: it
replaces the slide cover plate), magazine (with the top round, seen on reloads).

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis. Metres.

Run:  tools/blender.sh raw_assets/weapons/glock22/build.py \
        --out assets/weapons/glock22/glock22.gltf --tex 4096 --preview docs/previews/glock22.png
      Without --out the procedural HIGH model is rendered (fast look; add --fast).
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402
import sdf  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="", help=".gltf path; enables bake + export")
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--emission-size", type=int, default=512)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_<shot>.png")
ap.add_argument("--shots", default="side,left,beauty,rear,detail,under", help="which preview shots")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--fast", action="store_true", help="coarse frame sculpt and few samples (shape checks)")
ap.add_argument("--low-tris", type=int, default=7000, help="target triangles for the LOW frame")
ap.add_argument("--diagnose", action="store_true", help="check the LOW frame against the HIGH sculpt")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material
F32 = np.float32


# ---------------------------------------------------------------- materials
def rtf_polymer(name, base, rough):
    """Gen 4 'rough textured frame': a field of small square pyramids. Chebychev voronoi in 2D
    (square, slightly irregular cells) projected three ways and blended by the surface normal,
    so the pattern is even on the sides, front strap and backstrap alike."""
    m = mat(name, base, rough, 0.0)  # no edge wear: the sculpted mesh is too fine for a pointiness mask
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    geo = N.new("ShaderNodeNewGeometry")
    nsep = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], nsep.inputs["Vector"])

    def proj(a, b):
        comb = N.new("ShaderNodeCombineXYZ")
        L.new(sep.outputs[a], comb.inputs["X"])
        L.new(sep.outputs[b], comb.inputs["Y"])
        vor = N.new("ShaderNodeTexVoronoi")
        vor.voronoi_dimensions = "2D"
        vor.distance = "CHEBYCHEV"
        vor.inputs["Scale"].default_value = 900.0
        vor.inputs["Randomness"].default_value = 0.2
        L.new(comb.outputs["Vector"], vor.inputs["Vector"])
        return vor.outputs["Distance"]

    def weight(axis):
        p = N.new("ShaderNodeMath")
        p.operation = "POWER"
        ab = N.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        L.new(nsep.outputs[axis], ab.inputs[0])
        L.new(ab.outputs[0], p.inputs[0])
        p.inputs[1].default_value = 4.0
        return p.outputs[0]

    total = None
    wsum = None
    for axis, (a, b) in (("X", ("Y", "Z")), ("Y", ("X", "Z")), ("Z", ("X", "Y"))):
        w = weight(axis)
        mul = N.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        L.new(proj(a, b), mul.inputs[0])
        L.new(w, mul.inputs[1])
        if total is None:
            total, wsum = mul.outputs[0], w
            continue
        add = N.new("ShaderNodeMath")
        add.operation = "ADD"
        L.new(total, add.inputs[0])
        L.new(mul.outputs[0], add.inputs[1])
        total = add.outputs[0]
        addw = N.new("ShaderNodeMath")
        addw.operation = "ADD"
        L.new(wsum, addw.inputs[0])
        L.new(w, addw.inputs[1])
        wsum = addw.outputs[0]
    div = N.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    L.new(total, div.inputs[0])
    L.new(wsum, div.inputs[1])
    inv = N.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L.new(div.outputs[0], inv.inputs[1])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.00025
    L.new(inv.outputs[0], bump.inputs["Height"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3200.0
    bump2 = N.new("ShaderNodeBump")
    bump2.inputs["Strength"].default_value = 0.25
    bump2.inputs["Distance"].default_value = 0.0001
    L.new(noise.outputs["Fac"], bump2.inputs["Height"])
    L.new(bump2.outputs["Normal"], bump.inputs["Normal"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


POLY = (0.020, 0.020, 0.021)
POLY_WEAR = (0.06, 0.06, 0.062)
# Glock's nitrided slide: near-black, a faint metallic sheen, edges worn to grey steel.
M_SLIDE = mat("slide_nitride", (0.030, 0.030, 0.032), 0.42, 0.75, wear=(0.38, 0.38, 0.39), wear_rough=0.26,
              brushed=0.04, bump_scale=1100, bump_strength=0.035)
M_FRAME = mat("frame_polymer", POLY, 0.6, 0.0, bump_scale=2200, bump_strength=0.08)
M_GRIP = rtf_polymer("grip_rtf", POLY, 0.84)
M_STEEL = mat("steel_dark", (0.05, 0.05, 0.053), 0.34, 1.0, wear=(0.42, 0.42, 0.44), wear_rough=0.22)
M_BARREL = mat("barrel_nitride", (0.055, 0.055, 0.058), 0.5, 1.0, wear=(0.42, 0.42, 0.43), wear_rough=0.26)
M_BRIGHT = mat("crown_bright", (0.55, 0.55, 0.56), 0.18, 1.0)
M_BORE = mat("bore_dark", (0.012, 0.012, 0.013), 0.45, 1.0)
M_SWITCH = mat("switch_black", (0.032, 0.033, 0.037), 0.36, 0.9, wear=(0.62, 0.62, 0.64), wear_rough=0.2)
M_WHITE = mat("sight_white", (0.78, 0.78, 0.74), 0.5, 0.0)
M_TRITIUM = mat("tritium", (0.3, 1.0, 0.35), 0.4, 0.0, emission=((0.3, 1.0, 0.32), 6.0))
M_MARK = mat("engraving", (0.30, 0.30, 0.31), 0.55, 0.85)
M_LOGO = mat("logo_polymer", (0.05, 0.05, 0.052), 0.5, 0.0)
M_MAG = mat("mag_polymer", (0.022, 0.022, 0.023), 0.5, 0.0, wear=POLY_WEAR, wear_rough=0.55,
            bump_scale=2400, bump_strength=0.06)
M_BRASS = mat("brass", (0.62, 0.42, 0.16), 0.25, 1.0)
M_COPPER = mat("copper_jacket", (0.66, 0.33, 0.20), 0.3, 1.0)
MATERIALS = [M_SLIDE, M_FRAME, M_GRIP, M_STEEL, M_BARREL, M_BRIGHT, M_BORE, M_SWITCH, M_WHITE, M_TRITIUM,
             M_MARK, M_LOGO, M_MAG, M_BRASS, M_COPPER]

# ---------------------------------------------------------------- dimensions
SH = 0.01275                  # slide half width (25.5 mm)
X0, X1 = -0.0935, 0.0930      # slide rear / muzzle face (186.5 mm)
ZT, ZB = 0.0100, -0.0185      # slide top / bottom (28.5 mm tall, bore 10 mm under the top)
FRAME_TOP = -0.0188
FRAME_HW = 0.0119             # frame half width under the slide
DUST_BOT = -0.0325            # dust cover / rail bottom
FRAME_FRONT = 0.0790
GT = np.array((-0.054, 0.0, -0.050))          # grip line (shared with the Five-seveN and the hands)
_ax = np.array((-0.029, 0.0, -0.080))
AX = _ax / np.linalg.norm(_ax)                # down the grip
FW = np.array((-AX[2], 0.0, AX[0]))           # toward the front strap
HB = 0.066                                    # grip bottom (distance down the grip line)
LOW_SHARP_DEG = 35.0
MAG_DROP = 0.040                              # the 22-round magazine sticks out this far
SIGHT_Z = ZT + 0.0063                         # sight line (top of the front post / rear blade)

PART_IDS = {"body": 0, "slide": 1, "magazine": 2}
CURRENT = ["body"]
PART_OF = {}


def part(name):
    CURRENT[0] = name


def finish(ob, m, **kw):
    PART_OF[ob.name] = CURRENT[0]
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m, extrude=0.00008):
    ob = hs.text(name, body, size, loc, rot, m, extrude=extrude)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def gp(h, u=0.0, v=0.0):
    """World point at distance h down the grip line, u toward the front strap, v to the LEFT (+Y)."""
    p = GT + AX * h + FW * u
    return V((float(p[0]), float(v), float(p[2])))


def joined_cutter(name, obs):
    """Joins helper solids into one boolean cutter (keeps one modifier per cut)."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def wedge_xz(name, p1, p2, far, width=0.08, y=0.0):
    """Cutter for a chamfer: the triangle beyond the line p1-p2 (side view), across Y."""
    p1, p2 = V((p1[0], 0, p1[1])), V((p2[0], 0, p2[1]))
    d = p2 - p1
    a, b = p1 - d * 0.6, p2 + d * 0.6
    return hs.side_profile(name, [(a.x, a.z), (b.x, b.z), far], width, y=y)


def wedge_xy(name, p1, p2, far, height=0.08, z=0.0):
    """Cutter for a vertical-edge chamfer: the triangle beyond p1-p2 (top view), along Z."""
    a = V((p1[0], p1[1], 0))
    b = V((p2[0], p2[1], 0))
    d = b - a
    a, b = a - d * 0.6, b + d * 0.6
    return hs.prism(name, [(a.x, a.y, z - height / 2), (b.x, b.y, z - height / 2), (far[0], far[1], z - height / 2)],
                    (0, 0, height))


def rounded_rect_yz(name, y0, y1, z0, z1, r, x0, x1, seg=6):
    """Rounded rectangle (rear view) extruded along X."""
    pts = []
    for cy, cz, a0 in ((y1 - r, z1 - r, 0), (y0 + r, z1 - r, 90), (y0 + r, z0 + r, 180), (y1 - r, z0 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return hs.section(name, pts, x0, x1)


# ---------------------------------------------------------------- frame: signed-distance sculpt
def ss(e0, e1, t):
    t = np.clip((t - F32(e0)) / F32(e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bump(t):
    t = np.clip(np.abs(t), 0.0, 1.0)
    return np.cos(t * F32(math.pi / 2)) ** 2


def rrect(px, py, ax, ay, r):
    qx = np.abs(px) - (ax - r)
    qy = np.abs(py) - (ay - r)
    return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r


def rinter(a, b, r):
    """Intersection with a rounded edge of radius r."""
    a = a + F32(r)
    b = b + F32(r)
    return np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0) - F32(r)


def g_local(x, z):
    dx = x - F32(GT[0])
    dz = z - F32(GT[2])
    return dx * F32(AX[0]) + dz * F32(AX[2]), dx * F32(FW[0]) + dz * F32(FW[2])


class FnPrim(sdf.Prim):
    def __init__(self, lo, hi, f):
        self.lo, self.hi, self.f = np.asarray(lo, float), np.asarray(hi, float), f

    def aabb(self):
        return self.lo, self.hi

    def __call__(self, x, y, z):
        return self.f(x, y, z)


def grip_front(h):
    """Front strap offset: three Gen 4 finger grooves (the hands' fingers sit in them)."""
    g = bump((h - F32(0.0300)) / F32(0.0082)) + bump((h - F32(0.0490)) / F32(0.0082)) \
        + F32(0.75) * bump((h - F32(0.0672)) / F32(0.0080))
    return F32(0.0255) - F32(0.0019) * g


def grip_back(h):
    """Backstrap offset with the Glock 'hump' low on the backstrap."""
    return F32(0.0255) + F32(0.0022) * bump((h - F32(0.046)) / F32(0.026))


def grip_width(h):
    """Half width: the narrow frame at the top widens into the grip, a slight flare at the bottom."""
    return F32(FRAME_HW) + F32(0.0031) * ss(-0.024, -0.004, h) + F32(0.0006) * ss(0.045, HB, h)


def grip_f(x, y, z):
    h, u = g_local(x, z)
    uf, ub, w = grip_front(h), grip_back(h), grip_width(h)
    c = (uf - ub) * F32(0.5)
    a = (uf + ub) * F32(0.5)
    pu = u - c
    r = np.where(pu > 0, F32(0.0088), F32(0.0079))
    d2 = rrect(pu, y, a, w, r)
    d = rinter(d2, h - F32(HB), 0.0016)
    return np.maximum(d, F32(-0.050) - h)


def guard_f(x, y, z):
    # Squared Glock trigger guard: flat front, straight bottom, a soft corner between.
    d2 = rrect(x - F32(-0.00025), z - F32(-0.04525), F32(0.03375), F32(0.01525), F32(0.0058))
    w = F32(0.0057) + F32(0.0045) * ss(-0.0405, -0.0335, z)
    return rinter(d2, np.abs(y) - w, 0.0021)


def opening_f(x, y, z):
    h, u = g_local(x, z)
    box = rrect(x - F32(-0.0100), z - F32(-0.0440), F32(0.0375), F32(0.0116), F32(0.0040))
    strap = F32(0.0255) - u
    return sdf.smax(box, strap, 0.006) + y * F32(0.0)


def magwell_f(x, y, z):
    h, u = g_local(x, z)
    fl = np.maximum(h - F32(HB - 0.0045), 0) * F32(0.7)
    d2 = rrect(u - F32(-0.0008), y, F32(0.0172) + fl, F32(0.0118) + fl, F32(0.0035))
    return np.maximum(d2, F32(0.030) - h)


def grip_bounds():
    pts = [GT + AX * h + FW * u for h in (-0.05, HB + 0.004) for u in (-0.031, 0.029)]
    lo = np.min(pts, 0) - 0.002
    hi = np.max(pts, 0) + 0.002
    lo[1], hi[1] = -0.018, 0.018
    return lo, hi


def frame_model():
    m = sdf.Model()
    # Dust cover and the frame rails over the grip.
    m.add(sdf.RoundBox(((-0.068 + FRAME_FRONT) / 2, 0.0, (DUST_BOT - 0.0150) / 2),
                       ((FRAME_FRONT + 0.068) / 2, FRAME_HW, (-0.0150 - DUST_BOT) / 2), r=0.0017))
    # Grip.
    lo, hi = grip_bounds()
    m.add(FnPrim(lo, hi, grip_f), k=0.0035)
    # Beavertail: a short tang over the web of the hand, just past the slide.
    m.add(sdf.RoundBox((-0.0838, 0.0, -0.0214), (0.0142, 0.0116, 0.0043), R=sdf.rot((0, 1, 0), 10.0), r=0.0036),
          k=0.0055)
    # Trigger guard ring, then its opening (the rear wall is the front strap).
    m.add(FnPrim((-0.036, -0.013, -0.062), (0.035, 0.013, -0.028), guard_f), k=0.003)
    m.sub(FnPrim((-0.050, -0.02, -0.058), (0.030, 0.02, -0.030), opening_f), k=0.0008)
    # Trigger slot in the underside of the frame.
    m.sub(sdf.RoundBox((-0.0072, 0.0, -0.0315), (0.0072, 0.0043, 0.0032), r=0.0008), k=0.0005)
    # Magazine well and the Gen 4 cut-outs on both sides of its front edge.
    m.sub(FnPrim(np.minimum(lo, 0) - 0.01, hi + 0.01, magwell_f), k=0.0007)
    for side in (-1, 1):
        c = gp(HB + 0.0012, 0.0205, side * 0.0162)
        m.sub(sdf.Sphere(tuple(c), 0.0062), k=0.0012)
    # Accessory rail: a groove along each side of the dust cover and Glock's single cross slot.
    for side in (-1, 1):
        m.sub(sdf.RoundBox((0.0580, side * 0.0139, -0.0292), (0.0255, 0.0040, 0.00105), r=0.0003), k=0.0003)
    m.sub(sdf.RoundBox((0.0598, 0.0, -0.0338), (0.0020, 0.016, 0.0030), r=0.0004), k=0.0003)
    # Everything ends at the frame top, under the slide.
    m.fn((-1, -1, -1), (1, 1, 1), lambda f, x, y, z: rinter(f, z - F32(FRAME_TOP), 0.0006))
    return m


FRAME_LO = (-0.1045, -0.0180, -0.1265)
FRAME_HI = (0.0815, 0.0180, -0.0165)


def frame_mesh(name, h):
    # Offset the lattice by odd fractions of a cell: flat faces that land exactly on grid
    # planes (the grip sides at +-15.0 mm) make the mesher emit stair-step slivers.
    lo = tuple(v + h * f for v, f in zip(FRAME_LO, (0.371, 0.413, 0.297)))
    grid = sdf.Grid(lo, FRAME_HI, h)
    print(f"glock22: sculpting the frame on {grid.shape} ({grid.size / 1e6:.1f} M cells)")
    F = frame_model().evaluate(grid)
    me = sdf.to_mesh(name, F, grid)
    del F
    ob = hs.link(bpy.data.objects.new(name, me))
    # Materials: smooth polymer, RTF texture on the grip (sides, front strap and backstrap).
    me.materials.append(M_FRAME)
    me.materials.append(M_GRIP)
    cen = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("center", cen)
    cen = cen.reshape(-1, 3).astype(float)
    d = cen - GT
    h, u, y = d @ AX, d @ FW, cen[:, 1]
    thr = 0.0035 - 0.015 * np.clip((-u - 0.008) / 0.012, 0, 1)
    tex = (h > thr) & (h < HB - 0.0028)
    fl = np.maximum(h - (HB - 0.0045), 0) * 0.7
    inside = (h > 0.028) & (np.abs(u + 0.0008) < 0.0176 + fl) & (np.abs(y) < 0.0122 + fl)
    tex &= ~inside
    me.polygons.foreach_set("material_index", tex.astype(np.int32))
    me.shade_smooth()
    PART_OF[ob.name] = "body"
    return ob


def frame_surface_y(x, z, side=1):
    """|y| of the frame surface at (x, z) (for pins and buttons that sit on it)."""
    m = frame_model()
    ys = np.linspace(0.0, 0.02, 401)
    P = np.stack([np.full_like(ys, x), ys * side, np.full_like(ys, z)], 1)
    f = m.evaluate_points(P)
    i = int(np.argmax(f > 0))
    return float(ys[i])


# ---------------------------------------------------------------- slide
def build_slide():
    part("slide")
    h, c = SH, 0.0032
    slide = hs.section("slide", [(-h + 0.0008, ZB), (h - 0.0008, ZB), (h, ZB + 0.0008), (h, ZT - c), (h - c, ZT),
                                 (-h + c, ZT), (-h, ZT - c), (-h, ZB + 0.0008)], X0, X1)
    # Nose: Gen 4's big lower bevel, small top and side bevels; rear: top and side bevels.
    hs.cut(slide, wedge_xz("nose_low", (X1, ZB + 0.0062), (X1 - 0.0058, ZB), (X1 + 0.02, ZB - 0.02)))
    hs.cut(slide, wedge_xz("nose_top", (X1, ZT - 0.0013), (X1 - 0.0013, ZT), (X1 + 0.02, ZT + 0.02)))
    hs.cut(slide, wedge_xz("rear_top", (X0, ZT - 0.0011), (X0 + 0.0011, ZT), (X0 - 0.02, ZT + 0.02)))
    for s in (-1, 1):
        hs.cut(slide, wedge_xy(f"nose_side{s}", (X1, s * (h - 0.0012)), (X1 - 0.0012, s * h), (X1 + 0.02, s * 0.03)))
        hs.cut(slide, wedge_xy(f"rear_side{s}", (X0, s * (h - 0.0007)), (X0 + 0.0007, s * h), (X0 - 0.02, s * 0.03)))
    # Muzzle and the recoil-spring hole under it.
    hs.cut(slide, hs.cyl_x("muzzle_hole", 0.0072, X1 - 0.03, X1 + 0.01, verts=48))
    hs.cut(slide, hs.cyl_x("rod_hole", 0.0042, X1 - 0.02, X1 + 0.01, verts=32, z=-0.0119))
    # Ejection port: top right, rear edge = breech face.
    hs.cut(slide, hs.box("ejection_port", (0.0395, 0.0235, 0.022), (-0.01125, -0.00825, 0.0090)))
    # Nine vertical V-grooves at the rear, both sides (Gen 4).
    grooves = []
    for s in (-1, 1):
        for i in range(9):
            g = hs.box(f"serr{s}_{i}", (0.0014, 0.0014, 0.0232), (X0 + 0.0060 + i * 0.0036, s * h, -0.0054),
                       (0, 0, math.pi / 4))
            grooves.append(g)
    hs.cut(slide, joined_cutter("serrations", grooves))
    # Slide-stop notch on the lower left edge.
    hs.cut(slide, hs.box("stop_notch", (0.0072, 0.0030, 0.0030), (-0.0300, h, ZB + 0.0006)))
    finish(slide, M_SLIDE, bevel=0.00035, angle=30)

    # Rear sight: steel night sight, U notch, two tritium dots in white rings.
    rear = hs.section("rear_sight", [(-0.0090, ZT - 0.0004), (0.0090, ZT - 0.0004), (0.0075, ZT + 0.0065),
                                     (-0.0075, ZT + 0.0065)], -0.0856, -0.0779)
    hs.cut(rear, hs.box("rear_notch", (0.02, 0.0036, 0.0030), (-0.0816, 0.0, ZT + 0.0068)))
    hs.cut(rear, hs.cyl_x("rear_notch_u", 0.0018, -0.10, -0.06, verts=24, z=ZT + 0.0053))
    hs.cut(rear, wedge_xz("rear_ramp", (-0.0779, ZT + 0.0022), (-0.0803, ZT + 0.0065), (-0.06, ZT + 0.02)))
    finish(rear, M_STEEL, bevel=0.0003, angle=30)
    for s in (-1, 1):
        finish(hs.cyl_x(f"rear_ring{s}", 0.0016, -0.0860, -0.0854, verts=24, y=s * 0.0050, z=ZT + 0.0034),
               M_WHITE, bevel=0.0001)
        finish(hs.cyl_x(f"rear_vial{s}", 0.00085, -0.0862, -0.0858, verts=16, y=s * 0.0050, z=ZT + 0.0034),
               M_TRITIUM, bevel=0)
    # Front sight: 3.4 mm post on a small base, one dot facing the shooter.
    front = hs.section("front_sight", [(-0.0017, ZT - 0.0004), (0.0017, ZT - 0.0004), (0.0017, SIGHT_Z),
                                       (-0.0017, SIGHT_Z)], 0.0806, 0.0866)
    hs.cut(front, wedge_xz("front_ramp", (0.0866, ZT + 0.0018), (0.0838, SIGHT_Z), (0.10, SIGHT_Z + 0.02)))
    finish(front, M_STEEL, bevel=0.00025, angle=30)
    finish(hs.box("front_base", (0.0088, 0.0052, 0.0009), (0.0836, 0.0, ZT + 0.0002)), M_STEEL, bevel=0.0003)
    finish(hs.cyl_x("front_ring", 0.00135, 0.0802, 0.0808, verts=24, z=ZT + 0.0040), M_WHITE, bevel=0.0001)
    finish(hs.cyl_x("front_vial", 0.0008, 0.0800, 0.0804, verts=16, z=ZT + 0.0040), M_TRITIUM, bevel=0)

    # Extractor (right side, behind the port) with its loaded-chamber bump.
    finish(hs.box("extractor", (0.0272, 0.0006, 0.0056), (-0.0449, -h - 0.00005, 0.0026)), M_SLIDE, bevel=0.00025)
    finish(hs.box("extractor_lci", (0.0042, 0.0006, 0.0020), (-0.0336, -h - 0.0003, 0.0026)), M_SLIDE,
           bevel=0.00025)

    # The switch: a machined back plate in place of the slide cover plate, the sear block on it
    # and the selector lever reaching out past the right side of the slide.
    plate = rounded_rect_yz("switch_plate", -0.0080, 0.0080, -0.0130, 0.0050, 0.0018, X0 - 0.0026, X0 + 0.0002)
    finish(plate, M_SWITCH, bevel=0.0004)
    blk = rounded_rect_yz("switch_block", -0.0042, 0.0058, -0.0098, 0.0012, 0.0012, X0 - 0.0046, X0 - 0.0020)
    finish(blk, M_SWITCH, bevel=0.0004)
    arm = hs.prism("switch_lever", [(X0 - 0.0062, -0.0030, 0.0002), (X0 - 0.0062, -0.0030, 0.0046),
                                    (X0 - 0.0062, -0.0172, 0.0058), (X0 - 0.0062, -0.0192, 0.0040),
                                    (X0 - 0.0062, -0.0172, 0.0020)], (0.0024, 0, 0))
    finish(arm, M_SWITCH, bevel=0.0004, angle=25)
    for i in range(3):
        finish(hs.box(f"lever_rib{i}", (0.0030, 0.0005, 0.0030), (X0 - 0.0050, -0.0160 - i * 0.0011, 0.0040)),
               M_SWITCH, bevel=0.0001)
    finish(hs.cyl_x("switch_pivot", 0.0021, X0 - 0.0072, X0 - 0.0060, verts=24, y=-0.0040, z=0.0024), M_STEEL,
           bevel=0.0003)
    finish(hs.box("pivot_slot", (0.0002, 0.0030, 0.0005), (X0 - 0.00722, -0.0040, 0.0024)), M_BORE, bevel=0)
    for (yy, zz) in ((0.0058, 0.0030), (0.0058, -0.0108), (-0.0060, -0.0108)):
        finish(hs.cyl_x(f"plate_screw{yy}{zz}", 0.0010, X0 - 0.0030, X0 - 0.0024, verts=12, y=yy, z=zz), M_STEEL,
               bevel=0.0001)

    # Markings: GLOCK 22 Gen4 / AUSTRIA .40 on the left, the serial number on the right.
    if hs.D["text"]:
        text("mark_model", "GLOCK  22 Gen4", 0.0043, (0.006, h + 0.00005, -0.0118), (math.pi / 2, 0, math.pi), M_MARK)
        text("mark_austria", "AUSTRIA  .40", 0.0031, (0.066, h + 0.00005, -0.0114), (math.pi / 2, 0, math.pi),
             M_MARK)
        text("mark_serial", "BXRM417", 0.0030, (0.040, -h - 0.00005, -0.0115), (math.pi / 2, 0, 0), M_MARK)
    part("body")


# ---------------------------------------------------------------- barrel and recoil spring
def build_barrel():
    hood = hs.box("barrel_hood", (0.0270, 0.0128, 0.0098), (-0.0170, 0.0, 0.0049))
    finish(hood, M_BARREL, bevel=0.0004)
    finish(hs.cyl_x("chamber", 0.0079, -0.0305, 0.0110, verts=48), M_BARREL, bevel=0.0003)
    tube = hs.lathe_x("barrel_tube", [(0.0105, 0.0079), (0.0135, 0.0071), (X1 - 0.0016, 0.0069),
                                      (X1 - 0.0010, 0.0066), (X1 - 0.0008, 0.0060)], verts=48)
    hs.cut(tube, hs.cyl_x("bore", 0.0051, 0.03, X1 + 0.01, verts=32))
    finish(tube, M_BARREL, bevel=0.0)
    crown = hs.cyl_x("crown", 0.0061, X1 - 0.0011, X1 - 0.0007, verts=48)
    hs.cut(crown, hs.cyl_x("crown_hole", 0.0052, X1 - 0.003, X1 + 0.003, verts=32))
    finish(crown, M_BRIGHT, bevel=0.0001)
    finish(hs.cyl_x("bore_dark", 0.0050, 0.05, X1 - 0.0040, verts=32), M_BORE, bevel=0)
    # Guide rod tip and the end cap of the captive spring in the hole under the muzzle.
    finish(hs.cyl_x("rod_cap", 0.0033, X1 - 0.0100, X1 - 0.0034, verts=32, z=-0.0119), M_STEEL, bevel=0.0003)
    finish(hs.cyl_x("rod_tip", 0.0019, X1 - 0.0040, X1 - 0.0012, verts=24, z=-0.0119), M_STEEL, bevel=0.0003)
    if hs.D["text"]:
        text("mark_hood", ".40", 0.0030, (-0.0255, -0.0040, 0.00985), (0, 0, 0), M_MARK)
        text("mark_hood_sn", "BXRM417", 0.0017, (-0.0255, 0.0018, 0.00985), (0, 0, 0), M_MARK)


# ---------------------------------------------------------------- controls on the frame
def build_controls():
    # Trigger: Gen 4 smooth-faced shoe with the safety blade in its face.
    shoe = hs.side_profile("trigger", [(-0.0046, -0.0320), (-0.0054, -0.0370), (-0.0056, -0.0430),
                                       (-0.0042, -0.0480), (-0.0006, -0.0522), (-0.0016, -0.0538),
                                       (-0.0064, -0.0512), (-0.0098, -0.0450), (-0.0110, -0.0385),
                                       (-0.0108, -0.0320)], 0.0068)
    hs.cut(shoe, hs.box("blade_slot", (0.004, 0.0020, 0.0170), (-0.0050, 0.0, -0.0430)))
    finish(shoe, M_FRAME, bevel=0.0009, angle=25)
    finish(hs.side_profile("trigger_blade", [(-0.0062, -0.0360), (-0.0040, -0.0365), (-0.0040, -0.0440),
                                             (-0.0030, -0.0490), (-0.0050, -0.0495), (-0.0064, -0.0440)], 0.0016),
           M_FRAME, bevel=0.0003, angle=25)
    # Slide stop lever on the left, its serrated tab under the slide's notch.
    yl = FRAME_HW + 0.0004
    finish(hs.box("slide_stop", (0.0300, 0.0010, 0.0020), (-0.0175, yl, -0.0206)), M_STEEL, bevel=0.0003)
    tab = hs.side_profile("stop_tab", [(-0.0335, -0.0216), (-0.0265, -0.0216), (-0.0268, -0.0186),
                                       (-0.0330, -0.0186)], 0.0024, y=FRAME_HW + 0.0010)
    finish(tab, M_STEEL, bevel=0.0003)
    for i in range(3):
        finish(hs.box(f"stop_rib{i}", (0.0008, 0.0006, 0.0026), (-0.0322 + i * 0.0021, FRAME_HW + 0.0023, -0.0201)),
               M_STEEL, bevel=0.0001)
    # Takedown lever tabs, both sides, just under the slide over the trigger guard.
    for s in (-1, 1):
        finish(hs.box(f"takedown{s}", (0.0078, 0.0010, 0.0022), (0.0160, s * (FRAME_HW + 0.0003), -0.0201)),
               M_STEEL, bevel=0.0003)
        for i in range(3):
            finish(hs.box(f"td_rib{s}{i}", (0.0007, 0.0005, 0.0022), (0.0135 + i * 0.0025, s * (FRAME_HW + 0.0009),
                                                                     -0.0201)), M_STEEL, bevel=0.0001)
    # Pins: locking block, trigger and trigger-housing pins, flush on both sides.
    for name, x, z in (("lb_pin", 0.0140, -0.0262), ("trig_pin", -0.0036, -0.0258), ("th_pin", -0.0655, -0.0240)):
        yw = frame_surface_y(x, z)
        finish(hs.cyl_y(f"{name}", 0.00155, 2 * yw + 0.0001, (x, 0.0, z), verts=20), M_STEEL, bevel=0.0001)
    # Magazine catch: a squared button on the left, behind the trigger guard.
    c = gp(-0.0170, 0.0212)
    yw = frame_surface_y(c.x, c.z)
    btn = hs.box("mag_catch", (0.0072, 0.0026, 0.0066), (0, 0, 0))
    btn.location = (c.x, yw + 0.0005, c.z)
    btn.rotation_euler = (0, math.atan2(-AX[0], -AX[2]), 0)
    finish(btn, M_FRAME, bevel=0.0007)
    for i in range(3):
        rib = hs.box(f"catch_rib{i}", (0.0060, 0.0005, 0.0006), (0, 0, 0))
        rib.location = (c.x + (i - 1) * 0.0018 * float(AX[0]), yw + 0.0018, c.z + (i - 1) * 0.0018 * float(AX[2]))
        rib.rotation_euler = btn.rotation_euler
        finish(rib, M_FRAME, bevel=0.0001)
    # The Glock emblem moulded on both sides of the grip, above the texture.
    for s in (-1, 1):
        p = gp(-0.0045, -0.0065)
        yw = frame_surface_y(p.x, p.z) - 0.00005
        ring = hs.cyl_y(f"emblem_ring{s}", 0.0046, 0.0006, (p.x, s * yw, p.z), verts=40)
        hs.cut(ring, hs.cyl_y(f"emblem_hole{s}", 0.0038, 0.004, (p.x, s * yw, p.z), verts=40))
        finish(ring, M_LOGO, bevel=0.0001)
        if hs.D["text"]:
            rot = (math.pi / 2, 0, math.pi) if s > 0 else (math.pi / 2, 0, 0)
            g = text(f"emblem_g{s}", "G", 0.0058, (p.x, s * (yw + 0.0001), p.z - 0.0021), rot, M_LOGO, extrude=0.0001)
            if g:
                g.data.align_x = "CENTER"


# ---------------------------------------------------------------- magazine
def build_magazine():
    part("magazine")
    top, bot = -0.0255, HB + MAG_DROP
    st = [(tuple(gp(hh, -0.0010)), tuple(V(FW)), (0, -1, 0), a, b)
          for hh, a, b in ((top, 0.0150, 0.0105), (top + 0.004, 0.0165, 0.0113), (bot - 0.002, 0.0165, 0.0113),
                           (bot, 0.0162, 0.0110))]
    body = hs.loft("mag_body", st, power=3.4)
    # Witness holes on the back of the extended part.
    holes = [hs.cyl_between(f"witness{i}", gp(hh, -0.0215), gp(hh, -0.0120), 0.0011, verts=16)
             for i, hh in enumerate((HB + 0.006, HB + 0.016, HB + 0.026, HB + 0.034))]
    w = joined_cutter("witness_holes", holes)
    hs.cut(body, w)
    finish(body, M_MAG, bevel=0.0005, angle=40)
    # Front rib that runs down the extended body, as on Glock's own long magazines.
    rib0, rib1 = gp(HB - 0.004, 0.0150), gp(bot - 0.002, 0.0150)
    finish(hs.cyl_between("mag_rib", rib0, rib1, 0.0018, verts=16), M_MAG, bevel=0)
    # Floor plate: a moulded cap, slightly bigger than the body, lips front and back.
    fp = [(tuple(gp(hh, -0.0005)), tuple(V(FW)), (0, -1, 0), a, b)
          for hh, a, b in ((bot - 0.0006, 0.0170, 0.0116), (bot + 0.0010, 0.0186, 0.0124),
                           (bot + 0.0046, 0.0186, 0.0124), (bot + 0.0058, 0.0176, 0.0115))]
    plate = hs.loft("mag_floor", fp, power=3.6)
    finish(plate, M_MAG, bevel=0.0004, angle=35)
    c = gp(bot + 0.0059, -0.002)
    dimple = hs.cyl_between("floor_dimple", c - V(AX) * 0.0004, c + V(AX) * 0.0006, 0.0017, verts=16)
    finish(dimple, M_BORE, bevel=0)
    # Feed lips and the top round (seen when the magazine comes out).
    lips = hs.box("feed_lips", (0.020, 0.0185, 0.0030), (0, 0, 0))
    lips.location = gp(top + 0.0010, -0.0055)
    lips.rotation_euler = (0, math.atan2(-AX[0], -AX[2]), 0)
    finish(lips, M_MAG, bevel=0.0006)
    rc = gp(top - 0.0040, -0.0010)
    finish(hs.cyl_x("round_case", 0.00537, rc.x - 0.0125, rc.x + 0.0090, verts=24, z=rc.z), M_BRASS, bevel=0.0002)
    bullet = hs.lathe_x("round_bullet", [(rc.x + 0.0088, 0.0051), (rc.x + 0.0135, 0.0050), (rc.x + 0.0158, 0.0040),
                                          (rc.x + 0.0170, 0.0022), (rc.x + 0.0173, 0.0006)], verts=24)
    bullet.location.z = rc.z
    finish(bullet, M_COPPER, bevel=0)
    part("body")


# ---------------------------------------------------------------- build / split / export
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    fast = args.fast
    if detail is hs.HIGH:
        frame = frame_mesh("frame_high", 0.0005 if fast else 0.00025)
    else:
        # 0.9 mm sculpt, one decimation pass, no symmetry option: the combination that leaves
        # no fold-overs (--diagnose counts them; folds show as z-fighting slivers).
        frame = low_frame(0.0009, symmetry=False, steps=1)
    hs.PARTS.append(frame)
    build_slide()
    build_barrel()
    build_controls()
    build_magazine()
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
        # Flat shading over hard edges so the normal map only carries detail (no long-triangle gradients).
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
        joined.data.shade_smooth()
        joined.data.set_sharp_from_angle(angle=math.radians(LOW_SHARP_DEG))
        # Area-weighted normals: big flat faces shade flat, so long decimated triangles next to
        # rounded edges don't smear gradients across the dust cover and grip.
        wn = joined.modifiers.new("wnormal", "WEIGHTED_NORMAL")
        wn.mode = "FACE_AREA"
        wn.weight = 100
        wn.keep_sharp = True
        bpy.ops.object.convert(target="MESH")
    print(f"glock22 {detail['name']}: {bakeutil.tri_count(joined)} tris")
    return joined


EXPLODE = {"body": 0.0, "slide": 0.25, "magazine": -0.25}


def explode(ob, sign):
    """Moves the slide and magazine apart along Y (sign 1) or back (sign -1), so the bake never
    picks up a neighbouring part's surface (they sit a fraction of a millimetre apart)."""
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
    for name, i in PART_IDS.items():
        co[vpart == i, 1] += sign * EXPLODE[name]
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
    ramp.color_ramp.elements[1].color = (0.12, 0.125, 0.135, 1)
    nt.links.new(ramp.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    scene.world = world
    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0.0, 0, -0.185)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.5, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(0.0, 0, -0.04), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.25, -0.6, 0.55), 12, 0.7, sy=0.35)
    area("strip", (0.05, -0.05, 0.6), 7, 1.0, sy=0.1)
    area("fill", (0.6, -0.55, -0.05), 2.2, 0.8, (0.75, 0.85, 1.0))
    area("rim", (0.3, 0.6, 0.35), 8, 0.5, (1.0, 0.82, 0.62))
    area("kick", (-0.6, 0.2, 0.1), 3, 0.6)
    area("left", (-0.1, 0.65, 0.2), 6, 0.8)
    cam_data = bpy.data.cameras.new("cam")
    cam = hs.link(bpy.data.objects.new("cam", cam_data))
    scene.camera = cam
    return cam


def shoot(cam, path, loc, target, lens=50, fstop=0.0):
    d = cam.data
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


SHOTS = {
    # name: (camera, target, lens, f-stop)
    "side": ((-0.006, -0.85, -0.045), (-0.006, 0, -0.045), 75, 0.0),
    "left": ((-0.006, 0.85, -0.045), (-0.006, 0, -0.045), 75, 0.0),
    "beauty": ((0.26, -0.36, 0.14), (-0.02, 0, -0.05), 50, 5.6),
    "rear": ((-0.30, -0.075, 0.075), (0.05, 0.0, -0.005), 40, 11.0),
    "detail": ((-0.27, 0.20, 0.10), (-0.07, 0, -0.01), 90, 5.6),
    "under": ((0.16, -0.30, -0.15), (-0.03, 0, -0.07), 55, 8.0),
}


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    for name in args.shots.split(","):
        loc, target, lens, fstop = SHOTS[name]
        shoot(cam, f"{stem}_{name}.png", loc, target, lens=lens, fstop=fstop)


# ---------------------------------------------------------------- diagnosis
def low_frame(h=0.0006, symmetry=True, steps=1):
    """The LOW frame: a coarser sculpt, decimated (optionally in several passes) to --low-tris."""
    lo = frame_mesh("frame_low", h)
    target = args.low_tris
    for i in range(steps):
        cur = 2 * len(lo.data.polygons) if i == 0 else len(lo.data.polygons)
        goal = target * (2 ** (steps - 1 - i))
        dec = lo.modifiers.new("decimate", "DECIMATE")
        dec.ratio = min(1.0, goal / max(1, cur))
        dec.use_symmetry = symmetry
        dec.symmetry_axis = "Y"
        bpy.ops.object.select_all(action="DESELECT")
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo
        bpy.ops.object.convert(target="MESH")
    return lo


def count_folds(lo, m):
    """Faces whose normal points into the sculpt (fold-overs from decimation)."""
    flip = 0
    for poly in lo.data.polygons:
        c, n = poly.center, poly.normal
        f = m.evaluate_points(np.array([c + n * 0.0006, c - n * 0.0006]))
        if f[0] < f[1]:
            flip += 1
    return flip


def diagnose():
    hs.set_detail(hs.HIGH)
    m = frame_model()
    for h, sym, steps in ((0.0006, True, 1), (0.0006, False, 1), (0.0006, False, 3), (0.0009, False, 1),
                          (0.0009, False, 3)):
        lo = low_frame(h, sym, steps)
        print(f"diagnose h={h} sym={sym} steps={steps}: {len(lo.data.polygons)} faces, folds {count_folds(lo, m)}")
        bpy.data.objects.remove(lo)


# ---------------------------------------------------------------- run
if args.diagnose:
    diagnose()
    sys.exit(0)
if args.fast:
    args.samples = min(args.samples, 24)
if args.out:
    high = build(hs.HIGH, "glock22_high")
    low = build(hs.LOW, "glock22_low")
    # The slide and sights get the most texels (always in view), then the grip.
    bakeutil.unwrap(low, boost={M_SLIDE.name: 1.8, M_STEEL.name: 1.5, M_SWITCH.name: 1.6, M_MARK.name: 1.6,
                                M_TRITIUM.name: 1.2, M_WHITE.name: 1.4, M_GRIP.name: 1.15, M_BARREL.name: 1.3},
                    angle_deg=LOW_SHARP_DEG)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    explode(high, 1)
    explode(low, 1)
    tex = bakeutil.bake_textures(high, low, MATERIALS, args.tex, tex_dir, "glock22", cage=0.0012, ray=0.004,
                                 ao_distance=0.012, grime=0.3, log=print)
    bpy.data.objects.remove(high)
    explode(low, -1)
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
