"""RC-6 "Lance" personal rail carbine: a bullpup electromagnetic railgun.

Owner brief (2026-11-02): "a personal rail carbine. Sleek industrial bullpup
design, unique sound, functions with the enhanced lethality and insane
ballistic power of a railgun in real life. Imagine a P90 crossed with the
Halo 4 railgun, and maybe the design of Tau weaponry. Possibly the signature
weapon of the game."

Design reading:
- P90: compact bullpup, smooth organic shell, a top-mounted magazine running
  front to back with a window onto slugs lying across the gun, an integrated
  reflex optic, a forward support grip joined to the trigger guard by a loop.
- Halo 4 railgun: the barrel is two exposed rails forming an open fork at the
  muzzle; the rails glow; a top shroud lifts to vent heat.
- Tau: layered pale ceramic armour plates over a dark frame, separated by
  seams, some of which glow; swept sensor vanes on the sides.
- Real railgun hardware: copper-tungsten rails that heat-tint toward the
  muzzle, a capacitor bank (in the stock, with heat-sink fins), heat fins
  along the rails, tungsten slugs in discarding sabots, no case, no gas.

Parts (per-face part id, split after the bake):
  body      everything that doesn't move
  magazine  the top magazine (pulls back and up during a reload)
  vent      the top rail shroud (lifts while the rails vent heat)
  glow      emissive faces: rail faces, seams, heat fins. The game
            drives their brightness and colour from capacitor charge and heat.
  lens      optic glass (the game gives it a transparent material)
  reticle   the reflex ring and dot (the game colours it: seaglass, crimson over an enemy)

The pistol grip is the Pistol 57 / MG42 grip profile at the same place, so
the firing hand from the existing arms fits it exactly.

Axes: +X = muzzle, +Z = up, -Y = the gun's RIGHT side. Origin = bore axis
above the grip. Units: metres.

Run:
  tools/blender.sh raw_assets/weapons/rail_carbine/build.py \
      --out assets/weapons/rail_carbine/rail_carbine.gltf --tex 4096 --preview docs/previews/rail_carbine.png
  Fast look at the procedural HIGH model (no bake): --preview /tmp/rail.png
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
ap.add_argument("--tex", type=int, default=4096)
ap.add_argument("--emission-size", type=int, default=1024)
ap.add_argument("--preview", default="", help="preview stem; renders <stem>_side/_beauty/_left/_detail/_fp.png")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1600x900")
ap.add_argument("--only", default="", help="comma list of preview shots to render")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
V = Vector
mat = hs.material

# ---------------------------------------------------------------- materials
M_CER = mat("ceramic", (0.13, 0.128, 0.12), 0.5, 0.0, wear=(0.055, 0.055, 0.053), wear_rough=0.6,
            bump_scale=900, bump_strength=0.06)
M_CER2 = mat("ceramic_dark", (0.045, 0.047, 0.05), 0.48, 0.1, wear=(0.36, 0.36, 0.35), wear_rough=0.5,
             bump_scale=900, bump_strength=0.05)
M_GRAPH = mat("graphite", (0.045, 0.048, 0.053), 0.36, 0.85, wear=(0.4, 0.41, 0.43), wear_rough=0.22,
              brushed=0.03, bump_scale=900, bump_strength=0.03)
M_POLY = mat("polymer", (0.028, 0.029, 0.031), 0.62, 0.0, bump_scale=1600, bump_strength=0.2)
M_SMOKE = mat("smoked_polymer", (0.03, 0.045, 0.055), 0.14, 0.0, coat=0.6)
M_SABOT = mat("sabot", (0.4, 0.5, 0.56), 0.42, 0.0)
M_TUNG = mat("tungsten", (0.32, 0.32, 0.33), 0.28, 1.0)
M_GLOW = mat("glow", (0.3, 0.85, 1.0), 0.3, 0.0, emission=((0.35, 0.85, 1.0), 8.0))
M_GLASS = mat("glass", (0.01, 0.015, 0.02), 0.05, 0.0)
M_AMBER = mat("readout_amber", (1.0, 0.45, 0.08), 0.4, 0.0, emission=((1.0, 0.42, 0.06), 6.0))
M_PAINT = mat("hazard_paint", (0.85, 0.6, 0.07), 0.55, 0.0, wear=(0.1, 0.1, 0.1), wear_rough=0.5)
M_MARK = mat("print", (0.1, 0.1, 0.1), 0.55, 0.0)
M_RUBBER = mat("rubber", (0.02, 0.02, 0.021), 0.85, 0.0, bump_scale=600, bump_strength=0.3)


def rail_material():
    """Copper-tungsten rail that heat-tints straw -> purple -> blue toward the muzzle."""
    m = mat("rail_copper", (0.8, 0.46, 0.3), 0.24, 1.0, wear=(0.95, 0.72, 0.55), wear_rough=0.15)
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    src = bsdf.inputs["Base Color"].links[0].from_socket
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 120.0
    add = N.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.012
    L.new(noise.outputs["Fac"], add.inputs[0])
    L.new(sep.outputs["X"], add.inputs[2])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.315
    mr.inputs["From Max"].default_value = 0.404
    L.new(add.outputs[0], mr.inputs["Value"])
    ramp = N.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.8, 0.46, 0.3, 1)
    els[1].position, els[1].color = 1.0, (0.16, 0.24, 0.55, 1)
    for pos, c in ((0.35, (0.86, 0.64, 0.3)), (0.62, (0.5, 0.24, 0.42))):
        e = els.new(pos)
        e.color = (*c, 1)
    L.new(mr.outputs["Result"], ramp.inputs["Fac"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = 1.0
    L.new(src, mix.inputs["A"])
    L.new(ramp.outputs["Color"], mix.inputs["B"])
    gate = N.new("ShaderNodeMath")
    gate.operation = "GREATER_THAN"
    gate.inputs[1].default_value = 0.0
    L.new(mr.outputs["Result"], gate.inputs[0])
    L.new(gate.outputs[0], mix.inputs["Factor"])
    L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return m


M_RAIL = rail_material()
MATERIALS = [M_CER, M_CER2, M_GRAPH, M_POLY, M_SMOKE, M_SABOT, M_TUNG, M_GLOW, M_GLASS, M_AMBER, M_PAINT, M_MARK,
             M_RUBBER, M_RAIL]

PART_IDS = {"body": 0, "magazine": 1, "vent": 2, "glow": 3, "lens": 4, "reticle": 5}
CURRENT = ["body"]
PART_OF = {}

SIGHT_Z = 0.088  # optic axis (reticle centre) above the bore
MUZZLE_X = 0.402
POWER = 3.2      # superellipse power of the shell sections (2 = ellipse, higher = boxier)

# Core shell: (x, top z, bottom z, half width), butt to muzzle. The bottom
# stays high behind the grip so the firing hand's wrist clears it.
CORE = [
    (-0.432, 0.027, -0.094, 0.021),
    (-0.425, 0.031, -0.1, 0.025),
    (-0.40, 0.032, -0.102, 0.027),
    (-0.30, 0.033, -0.098, 0.0285),
    (-0.22, 0.033, -0.078, 0.029),
    (-0.165, 0.033, -0.054, 0.029),
    (-0.12, 0.033, -0.037, 0.029),
    (-0.06, 0.033, -0.033, 0.029),
    (0.00, 0.034, -0.034, 0.029),
    (0.045, 0.037, -0.037, 0.0285),
    (0.12, 0.037, -0.04, 0.0275),
    (0.22, 0.032, -0.036, 0.025),
    (0.28, 0.026, -0.03, 0.021),
    (0.312, 0.021, -0.026, 0.018),
]


def part(name):
    CURRENT[0] = name


def finish(ob, m, lb=True, **kw):
    """lb=False: no bevel on the LOW mesh (small repeated parts; the bake carries the bevel)."""
    PART_OF[ob.name] = CURRENT[0]
    if not lb and not high():
        kw["bevel"] = 0
    return hs.finish(ob, m, **kw)


def text(name, body, size, loc, rot, m):
    ob = hs.text(name, body, size, loc, rot, m)
    if ob:
        PART_OF[ob.name] = CURRENT[0]
    return ob


def high():
    return hs.D["name"] == "high"


# ---------------------------------------------------------------- shape helpers
def se_point(a_deg, hw, zt, zb, off=0.0, power=POWER):
    """Point on a superellipse section at angle a (0 = left/+Y, 90 = top, 180 = right, 270 = bottom)."""
    a = math.radians(a_deg)
    c, s = math.cos(a), math.sin(a)
    hh = (zt - zb) / 2
    zc = (zt + zb) / 2
    y = (hw + off) * math.copysign(abs(c) ** (2 / power), c)
    z = zc + (hh + off) * math.copysign(abs(s) ** (2 / power), s)
    return y, z


def stations_between(stations, x0, x1):
    """Core stations clipped to [x0, x1], with interpolated end stations."""
    def at(x):
        for a, b in zip(stations[:-1], stations[1:]):
            if a[0] <= x <= b[0]:
                t = (x - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
                return tuple(a[i] + (b[i] - a[i]) * t if i else x for i in range(4))
        return stations[0] if x < stations[0][0] else stations[-1]
    inner = [s for s in stations if x0 < s[0] < x1]
    return [at(x0)] + inner + [at(x1)]


def loft_rings(name, rings, cap=True):
    """Bridges a list of rings (each a list of 3D points, same count) into a closed solid."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(vr[0])
    for r0, r1 in zip(vr[:-1], vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if cap:
        bm.faces.new(list(reversed(vr[0])))
        bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def shell(name, stations, power=POWER, n=None):
    n = n or hs.nverts(44)
    rings = []
    for x, zt, zb, hw in stations:
        rings.append([(x, *se_point(360 * i / n, hw, zt, zb, 0, power)) for i in range(n)])
    return loft_rings(name, rings)


def band(name, x0, x1, a0, a1, off_in, off_out, stations=CORE, power=POWER, steps=None):
    """A plate following the core between angles a0..a1, off_in..off_out above its surface."""
    steps = steps or max(3, int(abs(a1 - a0) / (6 if high() else 12)))
    rings = []
    for x, zt, zb, hw in stations_between(stations, x0, x1):
        outer = [(x, *se_point(a0 + (a1 - a0) * i / steps, hw, zt, zb, off_out, power)) for i in range(steps + 1)]
        inner = [(x, *se_point(a1 - (a1 - a0) * i / steps, hw, zt, zb, off_in, power)) for i in range(steps + 1)]
        rings.append(outer + inner)
    return loft_rings(name, rings)


def ring_loft(name, stations, n=None, power=3.5):
    """Tube along X: stations (x, cz, outer hw, outer hh, inner hw, inner hh)."""
    n = n or hs.nverts(40)
    bm = bmesh.new()
    outer, inner = [], []
    for x, cz, ao, bo, ai, bi in stations:
        outer.append([bm.verts.new((x, *se_point(360 * i / n, ao, cz + bo, cz - bo, 0, power))) for i in range(n)])
        inner.append([bm.verts.new((x, *se_point(360 * i / n, ai, cz + bi, cz - bi, 0, power))) for i in range(n)])
    for rings, flip in ((outer, False), (inner, True)):
        for r0, r1 in zip(rings[:-1], rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                f = (r0[i], r0[j], r1[j], r1[i])
                bm.faces.new(tuple(reversed(f)) if flip else f)
    for k, flip in ((0, True), (-1, False)):
        for i in range(n):
            j = (i + 1) % n
            f = (outer[k][i], outer[k][j], inner[k][j], inner[k][i])
            bm.faces.new(tuple(reversed(f)) if flip else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def bar_xz(name, pts, thick, width, y=0.0):
    """Bar of `thick` along a polyline in the XZ plane, `width` across Y."""
    pts = [V((p[0], p[1])) for p in pts]
    normals = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        d = (b - a).normalized()
        normals.append(V((-d.y, d.x)))
    upper = [p + n * thick / 2 for p, n in zip(pts, normals)]
    lower = [p - n * thick / 2 for p, n in zip(pts, normals)]
    outline = [(p.x, p.y) for p in upper] + [(p.x, p.y) for p in reversed(lower)]
    return hs.side_profile(name, outline, width, y)


# ---------------------------------------------------------------- body shell
def build_shell():
    finish(shell("core", CORE), M_GRAPH, bevel=0.0012, angle=40)
    # Butt pad.
    finish(shell("butt_pad", [(-0.4445, 0.024, -0.091, 0.019), (-0.432, 0.026, -0.093, 0.0205)]),
           M_RUBBER, bevel=0.0015, angle=40)

    # Rear: cheek plate behind the magazine, two stock side panels around the capacitor vents.
    finish(band("cheek_plate", -0.428, -0.342, 32, 148, 0.0004, 0.0032), M_CER, bevel=0.0009)
    for side, (a0, a1) in (("l", (-72, 27)), ("r", (153, 252))):
        finish(band(f"stock_rear_{side}", -0.426, -0.374, a0, a1, 0.0004, 0.0034), M_CER, bevel=0.0009)
        finish(band(f"stock_front_{side}", -0.238, -0.128, a0 + (16 if side == "l" else 0),
                    a1 - (0 if side == "l" else 16), 0.0004, 0.0034), M_CER, bevel=0.0009)
    # Capacitor bank vents between the stock panels: a glowing well with heat-sink fins across it.
    part("glow")
    for side, (a0, a1) in (("l", (-40, 10)), ("r", (170, 220))):
        finish(band(f"cap_glow_{side}", -0.370, -0.242, a0, a1, -0.0006, 0.0004), M_GLOW, bevel=0)
    part("body")
    # Dark well around the glow, then the fins.
    for side, (a0, a1) in (("l", (-62, -40)), ("l", (10, 22)), ("r", (158, 170)), ("r", (220, 242))):
        finish(band(f"cap_well_{side}{a0}", -0.372, -0.238, a0, a1, -0.0004, 0.0008), M_GRAPH, bevel=0)
    for i in range(17):
        x = -0.369 + i * 0.0078
        for side, (a0, a1) in (("l", (-62, 22)), ("r", (158, 242))):
            finish(band(f"cap_fin_{side}{i}", x, x + 0.0046, a0, a1, 0.0, 0.0044, steps=None if high() else 3), M_GRAPH,
                       bevel=0.0005, lb=False)
    # Second layer of plates (Tau style): dark inset plates on the stock and shroud.
    for side, (a0, a1) in (("l", (-26, 16)), ("r", (164, 206))):
        finish(band(f"stock_layer_{side}", -0.226, -0.152, a0, a1, 0.0034, 0.0056), M_CER2, bevel=0.0008)
        finish(band(f"stock_rear_layer_{side}", -0.421, -0.392, a0 - 20 if side == "l" else a0, a1 if side == "l" else a1 + 20,
                    0.0034, 0.0052), M_CER2, bevel=0.0008)
    for side, (a0, a1) in (("l", (-38, -14)), ("r", (194, 218))):
        finish(band(f"shroud_layer_{side}", 0.07, 0.165, a0, a1, 0.0034, 0.0054), M_CER2, bevel=0.0008)
    # Power cell in the butt: end cap with a charge indicator.
    finish(hs.cyl_x("cell_cap", 0.0135, -0.4475, -0.4415, verts=32, z=-0.056), M_GRAPH, bevel=0.0012)
    finish(hs.cyl_x("cell_knurl", 0.0105, -0.4495, -0.4475, verts=12, z=-0.056), M_POLY, bevel=0.0006)
    for k in range(4):
        finish(hs.box(f"cell_led{k}", (0.0006, 0.0028, 0.0016), (-0.4449, -0.006 + k * 0.004, -0.032)), M_AMBER, bevel=0)
    # Spine over the vents, under the magazine edge.
    for side, (a0, a1) in (("l", (24, 31)), ("r", (149, 156))):
        finish(band(f"spine_{side}", -0.376, -0.236, a0, a1, 0.0, 0.0036), M_CER, bevel=0.0007)

    # Receiver plates above the grip (left one carries the Fire-Control Link readout).
    finish(band("rec_plate_l", -0.124, 0.040, -16, 24, 0.0004, 0.0032), M_CER, bevel=0.0009)
    finish(band("rec_plate_r", -0.124, 0.040, 156, 196, 0.0004, 0.0032), M_CER, bevel=0.0009)
    # Accent line along the upper edges, just under the magazine.
    part("glow")
    for side, (a0, a1) in (("l", (27.5, 30.5)), ("r", (149.5, 152.5))):
        finish(band(f"accent_{side}", -0.336, 0.040, a0, a1, -0.0004, 0.0009), M_GLOW, bevel=0)
    part("body")

    # Front shroud: upper and lower side plates, bottom plate, the top plate under the optic.
    finish(band("shroud_top_rear", 0.042, 0.112, 37, 143, 0.0004, 0.0032), M_CER, bevel=0.0009)
    finish(band("shroud_up_l", 0.044, 0.302, 9, 34, 0.0004, 0.0032), M_CER, bevel=0.0009)
    finish(band("shroud_up_r", 0.044, 0.302, 146, 171, 0.0004, 0.0032), M_CER, bevel=0.0009)
    finish(band("shroud_lo_l", 0.044, 0.294, -44, 1, 0.0004, 0.0034), M_CER, bevel=0.0009)
    finish(band("shroud_lo_r", 0.044, 0.294, 179, 224, 0.0004, 0.0034), M_CER, bevel=0.0009)
    finish(band("shroud_bottom", 0.044, 0.272, 230, 310, 0.0004, 0.0030), M_CER, bevel=0.0009)
    # Glowing seam between the upper and lower side plates: the rails showing through.
    part("glow")
    for side, (a0, a1) in (("l", (2.5, 7.5)), ("r", (172.5, 177.5))):
        finish(band(f"rail_seam_{side}", 0.06, 0.288, a0, a1, -0.0005, 0.0010), M_GLOW, bevel=0)
    # Hot well under the vent shroud, with fins across it.
    finish(band("vent_glow", 0.12, 0.296, 40, 140, -0.0005, 0.0006), M_GLOW, bevel=0)
    part("body")
    for i in range(14):
        x = 0.126 + i * 0.0122
        finish(band(f"vent_fin{i}", x, x + 0.0042, 38, 142, 0.0, 0.0024, steps=None if high() else 4), M_GRAPH,
               bevel=0.0004, lb=False)
    # Vent shroud: the top plate, floating over the fins. Lifts while venting.
    part("vent")
    finish(band("vent_shroud", 0.114, 0.302, 36, 144, 0.0042, 0.0072), M_CER, bevel=0.0010)
    for i, x in enumerate((0.13, 0.285)):
        finish(band(f"vent_strap{i}", x, x + 0.006, 50, 130, 0.0072, 0.0085), M_GRAPH, bevel=0.0005)
    part("body")

    # Tau-style sensor vanes, swept back along each side of the shroud.
    for sy in (1, -1):
        pts = [(0.168, sy * 0.024, -0.0055), (0.292, sy * 0.018, -0.0055), (0.300, sy * 0.0335, -0.0055),
               (0.214, sy * 0.0375, -0.0055)]
        if sy < 0:
            pts = list(reversed(pts))
        finish(hs.prism(f"vane{sy}", pts, (0, 0, 0.0032)), M_CER, bevel=0.0008)
        finish(hs.prism(f"vane_root{sy}", [(0.17, sy * 0.020, -0.0075), (0.24, sy * 0.020, -0.0075),
                                            (0.24, sy * 0.031, -0.0075), (0.19, sy * 0.031, -0.0075)][::sy],
                        (0, 0, 0.0072)), M_GRAPH, bevel=0.0006)


# ---------------------------------------------------------------- rails and muzzle fork
def build_rails():
    # Two rails along the bore: copper-tungsten bars in graphite housings, open fork at the muzzle.
    for sz in (1, -1):
        rail = hs.box(f"rail{sz}", (MUZZLE_X - 0.006 - 0.24, 0.014, 0.0105),
                      ((MUZZLE_X - 0.006 + 0.24) / 2, 0, sz * 0.0088))
        finish(rail, M_RAIL, bevel=0.0005)
        outline = [(0.296, 0.0138), (MUZZLE_X - 0.011, 0.0138), (MUZZLE_X, 0.0176), (MUZZLE_X - 0.008, 0.0246),
                   (0.352, 0.0262), (0.330, 0.0292), (0.296, 0.0292)]
        housing = hs.side_profile(f"prong{sz}", [(x, sz * z) for x, z in outline][::sz], 0.0215)
        finish(housing, M_GRAPH, bevel=0.0008)
        # Hazard stripes on the outer side of each prong.
        for k in range(3):
            for sy in (1, -1):
                s = hs.box(f"stripe{sz}{k}{sy}", (0.0028, 0.0006, 0.013),
                           (0.322 + k * 0.012, sy * 0.01085, sz * 0.020), (0, math.radians(35 * sz), 0))
                finish(s, M_PAINT, bevel=0)
        # Bolts holding rail to housing.
        for x in (0.312, 0.345, 0.378):
            for sy in (1, -1):
                finish(hs.cyl_y(f"bolt{sz}{x}{sy}", 0.0019, 0.0016, (x, sy * 0.0112, sz * 0.0195), verts=12),
                       M_GRAPH, bevel=0.0004, segments=2, lb=False)
    part("glow")
    for sz in (1, -1):
        finish(hs.box(f"rail_face{sz}", (MUZZLE_X - 0.31, 0.0085, 0.0008), ((MUZZLE_X + 0.31) / 2, 0, sz * 0.0039)),
               M_GLOW, bevel=0)
    part("body")
    # Breech face of the fork with the bore.
    finish(hs.box("fork_face", (0.006, 0.034, 0.05), (0.311, 0, -0.001)), M_GRAPH, bevel=0.0012)
    finish(hs.cyl_x("bore_dark", 0.0034, 0.306, 0.3152, verts=20), M_TUNG, bevel=0)


# ---------------------------------------------------------------- magazine (top, P90 style)
MAG_X0, MAG_X1 = -0.336, 0.038
MAG_ZB, MAG_ZT, MAG_HW = 0.0315, 0.067, 0.0255
WIN_X0, WIN_X1 = -0.282, -0.036
WIN_Z0, WIN_Z1 = 0.0385, 0.0590


def build_magazine():
    part("magazine")
    p = 4.0
    # Ends: rear cap and tapered front cap, full height.
    finish(shell("mag_rear", [(MAG_X0, MAG_ZT - 0.004, MAG_ZB, MAG_HW - 0.003), (MAG_X0 + 0.004, MAG_ZT, MAG_ZB, MAG_HW),
                              (WIN_X0, MAG_ZT, MAG_ZB, MAG_HW)], power=p), M_SMOKE, bevel=0.0011)
    finish(shell("mag_front", [(WIN_X1, MAG_ZT, MAG_ZB, MAG_HW), (MAG_X1 - 0.016, MAG_ZT, MAG_ZB, MAG_HW),
                               (MAG_X1, MAG_ZT - 0.009, MAG_ZB, MAG_HW - 0.005)], power=p), M_SMOKE, bevel=0.0011)
    # Top and bottom rails of the clear body, a dark spine in the middle.
    finish(shell("mag_top", [(WIN_X0, MAG_ZT, WIN_Z1, MAG_HW), (WIN_X1, MAG_ZT, WIN_Z1, MAG_HW)], power=p),
           M_SMOKE, bevel=0.0009)
    finish(hs.box("mag_tray", (WIN_X1 - WIN_X0, 2 * MAG_HW, WIN_Z0 - MAG_ZB),
                  ((WIN_X0 + WIN_X1) / 2, 0, (WIN_Z0 + MAG_ZB) / 2)), M_SMOKE, bevel=0.0009)
    finish(hs.box("mag_spine", (WIN_X1 - WIN_X0, 0.020, WIN_Z1 - WIN_Z0 + 0.001),
                  ((WIN_X0 + WIN_X1) / 2, 0, (WIN_Z0 + WIN_Z1) / 2)), M_GRAPH, bevel=0)
    # Slugs lying across the gun in two staggered columns (P90 style), seen through the windows.
    pitch = 0.0099
    count = 0
    for row, z in enumerate((0.0435, 0.0538)):
        x = WIN_X0 + 0.006 + row * pitch / 2
        while x < WIN_X1 - 0.005:
            for sy in (1, -1):
                y0, y1 = 0.0098, 0.0232
                slug = hs.cyl_y(f"slug{row}_{count}_{sy}", 0.0046, y1 - y0, (x, sy * (y0 + y1) / 2, z), verts=12)
                finish(slug, M_SABOT, bevel=0.0004, segments=2, lb=False)
                if high():
                    finish(hs.cyl_y(f"slug_core{row}_{count}_{sy}", 0.0019, 0.0016, (x, sy * (y1 + 0.0004), z),
                                    verts=12), M_TUNG, bevel=0.0002)
            x += pitch
            count += 1
    # Latch at the rear, and the round count printed on top.
    finish(hs.box("mag_latch", (0.008, 0.026, 0.016), (MAG_X0 - 0.002, 0, 0.049)), M_GRAPH, bevel=0.0012)
    finish(hs.box("mag_latch_grip", (0.003, 0.028, 0.004), (MAG_X0 - 0.0055, 0, 0.055)), M_POLY, bevel=0.0008)
    text("mag_count", "40 x 7G W", 0.006, (-0.31, -0.0105, MAG_ZT + 0.0001), (0, 0, 0), M_PAINT)
    part("body")
    return count


# ---------------------------------------------------------------- optic
def build_optic():
    # Mount on the shroud top.
    finish(shell("optic_base", [(0.048, 0.066, 0.030, 0.0105), (0.056, 0.068, 0.030, 0.0125),
                                (0.098, 0.068, 0.030, 0.0125), (0.106, 0.064, 0.030, 0.0105)]), M_GRAPH, bevel=0.0009)
    # Housing: a hood, flared at the front.
    hood = ring_loft("optic_hood", [(0.026, SIGHT_Z, 0.0235, 0.0225, 0.0185, 0.0170),
                                    (0.032, SIGHT_Z, 0.0250, 0.0240, 0.0185, 0.0170),
                                    (0.100, SIGHT_Z + 0.001, 0.0265, 0.0255, 0.0195, 0.0180),
                                    (0.114, SIGHT_Z + 0.0015, 0.0270, 0.0262, 0.0215, 0.0200)])
    finish(hood, M_GRAPH, bevel=0.0008)
    # Ceramic cap plate along the top of the hood.
    hood_st = [(0.032, SIGHT_Z + 0.0240, SIGHT_Z - 0.0240, 0.0250), (0.100, SIGHT_Z + 0.0265, SIGHT_Z - 0.0245, 0.0265)]
    finish(band("optic_cap", 0.036, 0.098, 30, 150, 0.0003, 0.0028, stations=hood_st, power=3.5), M_CER, bevel=0.0008)
    # Rangefinder pod on the left, controls on the right.
    finish(hs.cyl_x("rf_pod", 0.0062, 0.046, 0.094, verts=24, y=0.0305, z=SIGHT_Z - 0.006), M_GRAPH, bevel=0.0009)
    finish(hs.cyl_x("rf_ring", 0.0067, 0.088, 0.093, verts=24, y=0.0305, z=SIGHT_Z - 0.006), M_CER, bevel=0.0005)
    for i, x in enumerate((0.054, 0.066)):
        finish(hs.box(f"optic_btn{i}", (0.008, 0.004, 0.005), (x, -0.0275, SIGHT_Z - 0.004)), M_POLY, bevel=0.0009)
    part("glow")
    finish(hs.cyl_x("rf_lens", 0.0042, 0.0935, 0.0950, verts=20, y=0.0305, z=SIGHT_Z - 0.006), M_GLOW, bevel=0)
    # Reflex reticle: ring and centre dot just behind the front glass. Its own part: the game
    # colours it like every reticle (seaglass, crimson over an enemy).
    part("reticle")
    reticle = ring_loft("reticle_ring", [(0.1035, SIGHT_Z, 0.0058, 0.0058, 0.0047, 0.0047),
                                         (0.1043, SIGHT_Z, 0.0058, 0.0058, 0.0047, 0.0047)], n=hs.nverts(48), power=2.0)
    finish(reticle, M_GLOW, bevel=0, smooth=False)
    finish(hs.cyl_x("reticle_dot", 0.0009, 0.1035, 0.1043, verts=12, z=SIGHT_Z), M_GLOW, bevel=0, smooth=False)
    for k in range(4):  # short ticks at 12/3/6/9 o'clock outside the ring
        a = math.radians(90 * k)
        cy, cz = math.cos(a) * 0.0078, math.sin(a) * 0.0078
        size = (0.0008, 0.0024 if k % 2 == 0 else 0.0007, 0.0007 if k % 2 == 0 else 0.0024)
        finish(hs.box(f"reticle_tick{k}", size, (0.1039, cy, SIGHT_Z + cz)), M_GLOW, bevel=0, smooth=False)
    part("lens")
    for i, x in enumerate((0.031, 0.107)):
        lens = shell(f"lens{i}", [(x, SIGHT_Z + 0.0172, SIGHT_Z - 0.0172, 0.0188),
                                  (x + 0.0012, SIGHT_Z + 0.0172, SIGHT_Z - 0.0172, 0.0188)], power=3.5)
        finish(lens, M_GLASS, bevel=0)
    part("body")


# ---------------------------------------------------------------- grip, trigger, front loop and foregrip
REC_Z0 = -0.032  # the Pistol 57 / MG42 grip profile hangs from here


def build_lower():
    grip = hs.side_profile("grip", [
        (0.044, REC_Z0 + 0.001), (0.047, -0.052), (0.040, -0.061), (-0.020, -0.061), (-0.027, -0.054),
        (-0.056, -0.134), (-0.061, -0.138), (-0.103, -0.138), (-0.107, -0.132), (-0.081, -0.046),
        (-0.095, REC_Z0 + 0.001)], 0.030)
    hs.cut(grip, hs.side_profile("guard_hole", [(-0.018, -0.0345), (0.037, -0.0345), (0.039, -0.050), (0.033, -0.0555),
                                                (-0.014, -0.0555), (-0.023, -0.046)], 0.05))
    groove = hs.cyl_y("finger_groove", 0.0068, 0.06, (-0.0300, 0, -0.0745), verts=32)
    hs.linear_array(groove, 3, (-0.0071, 0, -0.0197))
    hs.cut(grip, groove)
    finish(grip, M_POLY, bevel=0.0012)
    finish(hs.side_profile("grip_cap", [(-0.058, -0.137), (-0.105, -0.137), (-0.108, -0.1445), (-0.055, -0.1445)], 0.027),
           M_GRAPH, bevel=0.0008)
    # Ceramic side panels on the grip (inset, above the hand).
    for sy in (1, -1):
        panel = hs.side_profile(f"grip_panel{sy}", [(-0.084, -0.046), (-0.040, -0.046), (-0.046, -0.058), (-0.079, -0.058)],
                                0.0012, y=sy * 0.0153)
        finish(panel, M_CER, bevel=0.0004)
    finish(hs.side_profile("trigger", [(0.012, -0.033), (0.018, -0.033), (0.016, -0.041), (0.021, -0.051),
                                       (0.015, -0.053), (0.008, -0.041)], 0.0055), M_GRAPH, bevel=0.0005)
    # Selector (ambidextrous) above the grip.
    for sy in (1, -1):
        finish(hs.cyl_y(f"selector{sy}", 0.0055, 0.003, (-0.012, sy * 0.0315, -0.021), verts=24), M_GRAPH, bevel=0.0008)
        finish(hs.box(f"selector_lever{sy}", (0.012, 0.002, 0.0035), (-0.006, sy * 0.0332, -0.019), (0, math.radians(-20), 0)),
               M_GRAPH, bevel=0.0006)

    # Front loop: from the trigger guard down and forward to the foot of the support grip.
    loop = bar_xz("front_loop", [(0.041, -0.046), (0.047, -0.088), (0.056, -0.118), (0.074, -0.1335),
                                 (0.100, -0.1385), (0.188, -0.1385)], 0.0115, 0.020)
    finish(loop, M_POLY, bevel=0.0018, segments=3, angle=30)
    # Raked support grip under the shroud.
    top, axis = FORE_TOP, FORE_AXIS
    fwd = V((-axis.z, 0.0, axis.x))
    right = V((0.0, -1.0, 0.0))
    st = []
    for h, hd, hw in ((-0.012, 0.0175, 0.0165), (0.006, 0.0163, 0.0153), (0.03, 0.0168, 0.0158), (0.06, 0.0170, 0.0160),
                      (0.088, 0.0172, 0.0162), (0.098, 0.0198, 0.0182), (0.104, 0.0190, 0.0175)):
        st.append((top + axis * h, fwd, right, hd, hw))
    fg = hs.loft("foregrip", st, power=2.4)
    finish(fg, M_POLY, bevel=0.0015, angle=40)
    finish(hs.box("fg_mount", (0.05, 0.026, 0.012), (0.172, 0, -0.040)), M_GRAPH, bevel=0.0012)
    # Ceramic strip down the front of the support grip.
    strip = []
    for h in (0.004, 0.09):
        c = top + axis * h + fwd * 0.0172
        strip.append((c, fwd, right, 0.0025, 0.009))
    finish(hs.loft("fg_strip", strip, power=3.0), M_CER, bevel=0.0006)


FORE_TOP = V((0.168, 0.0, -0.036))
FORE_AXIS = V((0.022, 0.0, -0.094)).normalized()


# ---------------------------------------------------------------- details, readouts, markings
def build_details():
    # Fire-Control Link readout on the left of the receiver (the player sees this side).
    y = 0.0322
    finish(hs.box("fcl_glass", (0.040, 0.0016, 0.0115), (-0.064, y + 0.0002, 0.0085)), M_GLASS, bevel=0.0004)
    for i, w in enumerate((0.005, 0.008, 0.003, 0.006, 0.004)):
        finish(hs.box(f"fcl_seg{i}", (w, 0.0004, 0.0014), (-0.081 + i * 0.0068 + w / 2, y + 0.0011, 0.0112)),
               M_AMBER, bevel=0)
    finish(hs.box("fcl_bar", (0.026, 0.0004, 0.0009), (-0.071, y + 0.0011, 0.0062)), M_AMBER, bevel=0)
    # Sling points.
    finish(hs.cyl_y("qd_rear", 0.0058, 0.006, (-0.41, 0.0, -0.096), verts=20), M_GRAPH, bevel=0.0008)
    for sy in (1, -1):
        finish(hs.cyl_y(f"qd_front{sy}", 0.0045, 0.004, (0.07, sy * 0.0325, -0.022), verts=20), M_GRAPH, bevel=0.0007)
    # Hex bolts on the shroud plates and stock.
    for x, z in ((0.07, -0.012), (0.255, -0.010), (-0.40, -0.040), (-0.15, -0.012)):
        for sy in (1, -1):
            cz = z
            finish(hs.cyl_y(f"hex{x}{sy}", 0.0024, 0.0016, (x, sy * 0.0328, cz), verts=6), M_GRAPH, bevel=0.0003,
                   segments=1, lb=False)
    # Markings (HIGH only; LOW gets them through the bake).
    yl = 0.0324
    text("mark_name", "RC-6  LANCE", 0.0068, (-0.135, yl, -0.028), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_spec", "7 G  W-CORE    2600 M/S", 0.0042, (0.262, 0.0318, -0.019), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_serial", "GRF 0611", 0.0038, (-0.135, yl, -0.0365), (math.pi / 2, 0, math.pi), M_MARK)
    text("mark_right", "DANGER  HV  18 kV", 0.0045, (0.08, -0.0318, -0.019), (math.pi / 2, 0, 0), M_PAINT)
    text("mark_cap", "CAP BANK  // NO STEP", 0.004, (-0.236, -yl, -0.06), (math.pi / 2, 0, 0), M_MARK)
    text("mark_sel", "S   1", 0.004, (-0.024, 0.0335, -0.033), (math.pi / 2, 0, math.pi), M_MARK)


# ---------------------------------------------------------------- build
def build(detail, name):
    hs.set_detail(detail)
    PART_OF.clear()
    part("body")
    build_shell()
    build_rails()
    slugs = build_magazine()
    build_optic()
    build_lower()
    build_details()
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
    print(f"rail_carbine {detail['name']}: {bakeutil.tri_count(joined)} tris, {slugs} slug columns")
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
        print(f"rail_carbine: part {pname}: {bakeutil.tri_count(ob)} tris")
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
    ramp.color_ramp.elements[1].color = (0.10, 0.11, 0.13, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    scene.world = world

    floor = hs.link(bpy.data.objects.new("floor", bpy.data.meshes.new("floor")))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(floor.data)
    bm.free()
    floor.location = (0, 0, -0.16)
    floor.data.materials.append(mat("floor", (0.008, 0.0085, 0.009), 0.55, 0.0))

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(-0.03, 0, -0.03), sy=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color = energy, color
        ld.shape = "RECTANGLE"
        ld.size = size
        ld.size_y = sy or size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.4, -1.2, 1.1), 40, 1.6, sy=0.5)
    area("strip_top", (0.0, 0.0, 1.1), 26, 2.0, sy=0.18)
    area("fill", (0.4, 1.3, 0.3), 26, 1.4, (0.75, 0.85, 1.0))
    area("rim", (1.3, -0.4, 0.5), 40, 0.8, (1.0, 0.85, 0.7))
    area("kick", (-1.3, 0.3, 0.2), 22, 1.0, (0.8, 0.9, 1.0))
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
    print(f"rail_carbine: rendered {path}")


def render_previews(stem):
    cam = setup_render(args.samples, args.res)
    shots = {
        "side": ((-0.03, -1.75, 0.0), (-0.03, 0, -0.025), 55, 0.0),
        "beauty": ((0.62, -0.78, 0.36), (-0.02, 0, -0.02), 45, 8.0),
        "left": ((-0.3, 0.85, 0.32), (0.0, 0, -0.02), 42, 8.0),
        "detail": ((0.52, 0.2, 0.16), (0.24, 0.0, 0.01), 50, 4.0),
        "top": ((-0.38, 0.12, 0.2), (0.12, 0.0, 0.03), 40, 5.0),
        # Roughly the player's hip view: eye behind and left of the gun, above it.
        "fp": ((-0.36, 0.085, 0.13), (0.6, -0.02, -0.04), 0, 0.0),
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
    high_ob = build(hs.HIGH, "rail_high")
    low = build(hs.LOW, "rail_low")
    bakeutil.unwrap(low, boost={M_CER.name: 1.15, M_GRAPH.name: 1.0, M_POLY.name: 0.7, M_SABOT.name: 1.3,
                                M_SMOKE.name: 1.1, M_RAIL.name: 1.4, M_PAINT.name: 1.4, M_MARK.name: 1.4})
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "textures")
    tex = bakeutil.bake_textures(high_ob, low, MATERIALS, args.tex, tex_dir, "rail_carbine", cage=0.0012, ray=0.004,
                                 ao_distance=0.025, grime=0.35, log=print)
    bpy.data.objects.remove(high_ob)
    em = tex["emission"]
    em.scale(args.emission_size, args.emission_size)
    em.save()
    bakeutil.apply_baked_material(low, tex, "rail_carbine", emission_strength=4.0)
    objs = split_parts(low)
    export(objs, args.out)
    print(f"rail_carbine: exported {args.out}")
    if args.preview:
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        g = bpy.data.node_groups.get("glTF Material Output")
        if g:
            bpy.data.node_groups.remove(g)
        bpy.ops.import_scene.gltf(filepath=args.out)
        render_previews(args.preview.rsplit(".", 1)[0])
elif args.preview:
    build(hs.HIGH, "rail_high")
    render_previews(args.preview.rsplit(".", 1)[0])
