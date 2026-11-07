"""GX-4 Gauss arm: the operative's right forearm is a prosthetic that folds
open into a coilgun (owner, 2026-11-07).

Owner brief: "the augmentation is like a prosthetic arm that's also a Gauss
cannon, so the character basically lifts up his hand and it badassly,
complexly cyber transforms into this almost Doom-like Gauss cannon... a
horrific electronic weapon. It's very loud and it's really powerful and can
overpenetrate too... like the golden gun in Destiny... with a badass
prosthetic on your hand."

Design reading (grounded hardware, no magic):
- A coilgun: a stack of drive coils (copper windings in black housings)
  fires a ferromagnetic slug down a guide bore; capacitor banks dump into the
  coils in sequence. In the arm the coils sit packed inside the forearm; to
  fire, they slide forward along two guide rails that telescope out through
  the hand, which splits open into a two-pronged muzzle fork.
- The forearm looks like the GS-2 graft suit's plates (satin black, flat
  facets, thin glowing seams) over a gunmetal chassis with pistons, so the
  arm reads as part of the same body.
- Three dorsal heat-sink fins stand up when it's armed. A strip of ten LEDs
  on the top plate shows the rounds left.

Transformation (one keyframed animation, 60 fps, frames 0-96 = 1.6 s; the
game plays it forward to deploy and backward, faster, to stow). The game
raises the arm into view over the first ~0.35 s; the open hand holds for 12
frames, then (frame numbers below + 12):
   0- 22  fingers curl into a fist (index first), thumb folds over
  14- 34  the wrist turns from palm-in (raised to look at it) to straight
  24- 44  the forearm's side plates swing open, the top plate lifts
  30- 46  the fist splits into two jaws that swing apart: the muzzle fork
  36- 60  the rails and bore telescope forward through the fork
  40- 78  six coil rings slide forward one by one and lock (slight overshoot)
  52- 70  the muzzle ring slides to the tip
  62- 80  the dorsal fins stand up

Parts (glTF nodes, all animated by node transform; no skinning):
  sleeve, chassis                 static
  plate_top (fin_1..3, led_0..9)  plate_out, plate_in
  coil_1..6, rails, muzzle (muzzle_tip: where rounds leave)
  wrist > jaw_in (thumb_1..3, index_1..3, middle_1..3), jaw_out (ring_1..3, little_1..3)
Materials: graft (satin black), gunmetal, rail (copper-tungsten), copper,
polymer (finger pads), weave (sleeve), glow (coil lips, seams: the game drives
it), led (the round counter: the game hides spent ones).

Axes: +X = forward along the forearm, +Z = up, -Y = the arm's outer (right)
side. Origin = the wrist. Metres.

Run:
  tools/blender.sh raw_assets/augments/gx4_gauss_arm/build.py \
      --out assets/augments/gx4_gauss_arm/gx4_gauss_arm.gltf --preview docs/previews/gx4_gauss_arm.png
  Preview only: --preview /tmp/gx4.png  (--frames 0,30,84 --samples 32)
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
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--frames", default="0,12,24,36,48,60,72,84")
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--res", default="960x540")
ap.add_argument("--views", default="fp,hero,hand")
ap.add_argument("--rest", action="store_true", help="preview the build pose (no animation)")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 60
scene.frame_start = 0
# The raised open hand holds for SHIFT frames before the fingers curl, so you
# see the hand before it becomes the gun (in-game check, 2026-11-07).
SHIFT = 12
END = 84 + SHIFT
scene.frame_end = END
V = Vector
hs.set_detail(hs.HIGH)
FPS = 60

# ---------------------------------------------------------------- materials
M_GRAFT = hs.material("graft", (0.022, 0.023, 0.026), 0.34, 0.0, coat=0.4)
M_GUN = hs.material("gunmetal", (0.10, 0.105, 0.11), 0.36, 1.0)
M_RAIL = hs.material("rail", (0.55, 0.45, 0.40), 0.24, 1.0)
M_COPPER = hs.material("copper", (0.86, 0.46, 0.26), 0.30, 1.0)
M_POLY = hs.material("polymer", (0.035, 0.036, 0.04), 0.6, 0.0)
M_WEAVE = hs.material("weave", (0.013, 0.013, 0.015), 0.82, 0.0)
GLOW_RGB = (0.45, 0.72, 1.0)
M_GLOW = hs.material("glow", (0.05, 0.08, 0.12), 0.3, 0.0, emission=(GLOW_RGB, 2.5))
M_LED = hs.material("led", (0.05, 0.08, 0.12), 0.3, 0.0, emission=(GLOW_RGB, 3.0))


# ---------------------------------------------------------------- helpers
def piece(ob, mat, bevel=0.0006, segments=2, angle=35.0, smooth=True):
    """hs.finish() without adding to hs.PARTS (each part joins its own pieces)."""
    hs.finish(ob, mat, bevel=bevel, segments=segments, angle=angle, smooth=smooth)
    hs.PARTS.remove(ob)
    return ob


def part(name, pieces, pivot=(0, 0, 0)):
    """Applies modifiers, joins `pieces` into one object named `name` whose
    origin is `pivot` (the hinge it turns about)."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(pieces) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    p = V(pivot)
    ob.data.transform(Matrix.Translation(-p))
    ob.location = p
    for h in hs.HELPERS:
        bpy.data.objects.remove(h)
    hs.HELPERS.clear()
    return ob


def empty(name, loc=(0, 0, 0)):
    ob = hs.link(bpy.data.objects.new(name, None))
    ob.empty_display_size = 0.02
    ob.location = loc
    return ob


def parent(child, par):
    bpy.context.view_layer.update()  # matrix_world is stale right after edits
    w = child.matrix_world.copy()
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()
    child.matrix_world = w


def shell(name, x0, x1, r0, r1, phi0, phi1, thick, seg=4, power=2.0):
    """A faceted arc plate around the X axis: angles (deg) from +Z toward -Y
    (the outer side), radius r0 at x0 to r1 at x1, `seg` flat facets."""
    bm = bmesh.new()
    rings = []
    for x, r in ((x0, r0), (x1, r1)):
        outer, inner = [], []
        for i in range(seg + 1):
            a = math.radians(phi0 + (phi1 - phi0) * i / seg)
            y, z = -math.sin(a), math.cos(a)
            outer.append(bm.verts.new((x, y * r, z * r)))
            inner.append(bm.verts.new((x, y * (r - thick), z * (r - thick))))
        rings.append((outer, inner))
    (o0, i0), (o1, i1) = rings
    for k in range(seg):
        bm.faces.new((o0[k], o1[k], o1[k + 1], o0[k + 1]))
        bm.faces.new((i0[k + 1], i1[k + 1], i1[k], i0[k]))
    for o, i in ((o0, i0), (o1, i1)):
        for k in range(seg):
            bm.faces.new((o[k], o[k + 1], i[k + 1], i[k]))
    bm.faces.new((o0[0], i0[0], i1[0], o1[0]))
    bm.faces.new((o1[-1], i1[-1], i0[-1], o0[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def revolve_closed(name, loop, verts=32):
    """A closed (x, r) profile loop revolved around X: a hollow ring, no caps."""
    n = hs.nverts(verts)
    bm = bmesh.new()
    rings = []
    for x, r in loop:
        rv = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rv.append(bm.verts.new((x, r * math.cos(a), r * math.sin(a))))
        rings.append(rv)
    m = len(rings)
    for k in range(m):
        a, b = rings[k], rings[(k + 1) % m]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def ring(name, x0, x1, r_out, r_in, verts=32):
    """A short tube along X (washer / collar / housing)."""
    return revolve_closed(name, [(x0, r_in), (x0, r_out), (x1, r_out), (x1, r_in)], verts=verts)


def rbox(name, size, loc):
    return hs.box(name, size, loc)


# ---------------------------------------------------------------- forearm
# Forearm radius tapers elbow -> wrist.
X_ELBOW, X_WRIST = -0.29, -0.012
R_ELBOW, R_WRIST = 0.050, 0.041


def r_at(x):
    t = (x - X_ELBOW) / (X_WRIST - X_ELBOW)
    return R_ELBOW + (R_WRIST - R_ELBOW) * t


objs = {}

# Suit sleeve over the elbow (static, mostly off-screen).
sl = hs.lathe_x("sleeve_m", [(-0.47, 0.0), (-0.47, 0.056), (-0.40, 0.057), (-0.33, 0.055), (-0.285, 0.052), (-0.285, 0.0)], verts=28)
objs["sleeve"] = part("sleeve", [piece(sl, M_WEAVE, bevel=0.0)])

# Chassis: elbow cuff, keel, spars, wrist collar, pistons, seam glow.
ch = []
ch.append(piece(ring("cuff", -0.300, -0.272, 0.055, 0.030, 28), M_GUN, bevel=0.0012))
for k in range(6):
    a = math.radians(30 + k * 60)
    ch.append(piece(hs.cyl_x(f"cuff_bolt{k}", 0.0035, -0.302, -0.270, verts=10, y=-math.sin(a) * 0.054, z=math.cos(a) * 0.054), M_GRAFT, bevel=0.0004))
ch.append(piece(shell("keel", X_ELBOW + 0.01, X_WRIST, r_at(X_ELBOW) - 0.001, R_WRIST - 0.001, 128, 232, 0.009, seg=5), M_GUN, bevel=0.0008))
for s in (1, -1):
    ch.append(piece(rbox(f"spar{s}", (0.27, 0.006, 0.010), (-0.15, s * 0.034, -0.016)), M_GUN, bevel=0.0008))
    # Seam light strips along the spars (show when the side plates open).
    ch.append(piece(rbox(f"seam{s}", (0.24, 0.0016, 0.0022), (-0.15, s * 0.0372, -0.010)), M_GLOW, bevel=0.0))
    # Pistons under the forearm.
    ch.append(piece(hs.cyl_between(f"pist{s}", (-0.262, s * 0.018, -0.047), (-0.12, s * 0.017, -0.043), 0.0055, verts=14), M_GUN, bevel=0.0005))
    ch.append(piece(hs.cyl_between(f"rod{s}", (-0.12, s * 0.017, -0.043), (-0.04, s * 0.016, -0.040), 0.0028, verts=12), M_RAIL, bevel=0.0))
ch.append(piece(ring("collar", -0.020, 0.006, 0.043, 0.0325, 32), M_GUN, bevel=0.0010))
ch.append(piece(ring("collar_glow", 0.0055, 0.0068, 0.0355, 0.0328, 32), M_GLOW, bevel=0.0))
# Spine block between the coils and the elbow (the capacitor bank housing).
ch.append(piece(hs.lathe_x("capbank", [(-0.285, 0.0), (-0.285, 0.036), (-0.255, 0.038), (-0.238, 0.034), (-0.238, 0.0)], verts=24), M_GUN, bevel=0.0006))
for k in range(5):
    ch.append(piece(ring(f"capband{k}", -0.282 + k * 0.009, -0.278 + k * 0.009, 0.0395, 0.03, 24), M_COPPER, bevel=0.0))
objs["chassis"] = part("chassis", ch)

# Armour plates (graft black), split by small gaps; hinges on the long edges.
PT = 0.0042
pt = [piece(shell("pt", -0.262, -0.035, r_at(-0.262) + 0.006, r_at(-0.035) + 0.005, -52, 52, PT, seg=4), M_GRAFT, bevel=0.0007)]
# A raised ridge down the middle of the top plate.
pt.append(piece(hs.prism("pt_ridge", [(-0.25, -0.006, 0.0), (-0.05, -0.004, 0.0), (-0.05, 0.004, 0.0), (-0.25, 0.006, 0.0)], (0, 0, 0.004)), M_GRAFT, bevel=0.0005))
pt[-1].location = (0, 0, r_at(-0.15) + 0.004)
objs["plate_top"] = part("plate_top", pt, pivot=(-0.035, 0.0, r_at(-0.035) + 0.005))
for side, name in ((1, "plate_out"), (-1, "plate_in")):
    # side 1: outer (-Y) plate from 56 to 126 deg; side -1 mirrored.
    a0, a1 = (56, 126) if side == 1 else (-126, -56)
    sp = [piece(shell(name + "_m", -0.255, -0.030, r_at(-0.255) + 0.005, r_at(-0.030) + 0.004, a0, a1, PT, seg=3), M_GRAFT, bevel=0.0007)]
    # Hinge along the lower edge (at 126 deg).
    hinge_a = math.radians(a1 if side == 1 else a0)
    rr = r_at(-0.14) + 0.003
    pivot = (-0.14, -math.sin(hinge_a) * rr, math.cos(hinge_a) * rr)
    objs[name] = part(name, sp, pivot=pivot)

# Dorsal heat-sink fins on the top plate (built folded flat, pointing back).
for k in range(3):
    xf = -0.105 - k * 0.055
    zt = r_at(xf) + 0.0095
    pts = [(xf, -0.016, zt), (xf, 0.016, zt), (xf - 0.032, 0.011, zt), (xf - 0.032, -0.011, zt)]
    fin = hs.prism(f"fin{k}", pts, (0, 0, 0.0026))
    fl = [piece(fin, M_GRAFT, bevel=0.0005)]
    fl.append(piece(rbox(f"fin_glow{k}", (0.0016, 0.02, 0.0028), (xf - 0.031, 0.0, zt + 0.0013)), M_GLOW, bevel=0.0))
    fl.append(piece(hs.cyl_y(f"fin_pin{k}", 0.0022, 0.009, (xf - 0.002, 0.0, zt + 0.0012), verts=10), M_GUN, bevel=0.0))
    objs[f"fin_{k + 1}"] = part(f"fin_{k + 1}", fl, pivot=(xf - 0.002, 0.0, zt + 0.0012))

# Round counter: ten LEDs on the top plate's inner flank (facing the eye).
for k in range(10):
    x = -0.205 + k * 0.0145
    a = math.radians(-34)
    r = r_at(x) + 0.0052
    led = rbox(f"led{k}", (0.008, 0.0022, 0.0035), (0, 0, 0))
    led.rotation_euler = (a, 0, 0)
    bpy.context.view_layer.objects.active = led
    bpy.ops.object.select_all(action="DESELECT")
    led.select_set(True)
    bpy.ops.object.transform_apply(rotation=True)
    led.location = (x, -math.sin(a) * r, math.cos(a) * r)
    bpy.ops.object.transform_apply(location=True)
    objs[f"led_{k}"] = part(f"led_{k}", [piece(led, M_LED, bevel=0.0)], pivot=(x, 0, 0))

# ---------------------------------------------------------------- the gun inside
COIL_W = 0.026
COIL_PACKED = [-0.226 + i * 0.0305 for i in range(6)]
COIL_ARMED = [-0.200 + i * 0.080 for i in range(6)]
for i, x in enumerate(COIL_PACKED):
    x0, x1 = x - COIL_W / 2, x + COIL_W / 2
    c = []
    # Windings: a ridged copper band between two black flanges.
    loop = [(x0 + 0.0025, 0.0120)]
    n = 10
    for k in range(n + 1):
        xx = x0 + 0.0025 + (COIL_W - 0.005) * k / n
        loop.append((xx, 0.0262 if k % 2 == 0 else 0.0250))
    loop.append((x1 - 0.0025, 0.0120))
    c.append(piece(revolve_closed(f"c{i}_wind", loop, verts=28), M_COPPER, bevel=0.0, smooth=True))
    c.append(piece(ring(f"c{i}_flange0", x0, x0 + 0.0028, 0.0300, 0.0110, 28), M_GUN, bevel=0.0004))
    c.append(piece(ring(f"c{i}_flange1", x1 - 0.0028, x1, 0.0300, 0.0110, 28), M_GUN, bevel=0.0004))
    for s2 in (1, -1):
        c.append(piece(rbox(f"c{i}_strap{s2}", (COIL_W, 0.006, 0.0035), (x, 0.0, s2 * 0.0275)), M_GUN, bevel=0.0004))
    c.append(piece(ring(f"c{i}_lip", x1 - 0.0004, x1 + 0.0006, 0.0128, 0.0108, 24), M_GLOW, bevel=0.0))
    # Shoes that ride the rails (top and bottom).
    for s in (1, -1):
        c.append(piece(rbox(f"c{i}_shoe{s}", (0.016, 0.012, 0.004), (x, 0.0, s * 0.0315)), M_GUN, bevel=0.0005))
    objs[f"coil_{i + 1}"] = part(f"coil_{i + 1}", c, pivot=(x, 0, 0))

RAIL_BACK, RAIL_FRONT = -0.245, 0.300
RAIL_RETRACT = -0.33
rl = []
for s in (1, -1):
    rl.append(piece(rbox(f"rail{s}", (RAIL_FRONT - RAIL_BACK, 0.009, 0.0055), ((RAIL_BACK + RAIL_FRONT) / 2, 0.0, s * 0.0360)), M_RAIL, bevel=0.0006))
    rl.append(piece(rbox(f"rail_glow{s}", (RAIL_FRONT - RAIL_BACK - 0.01, 0.0018, 0.0012), ((RAIL_BACK + RAIL_FRONT) / 2, 0.0, s * 0.0333)), M_GLOW, bevel=0.0))
    rl.append(piece(rbox(f"guide{s}", (RAIL_FRONT - RAIL_BACK - 0.02, 0.003, 0.003), ((RAIL_BACK + RAIL_FRONT) / 2 - 0.01, s * 0.0118, 0.0)), M_GUN, bevel=0.0))
rl.append(piece(hs.lathe_x("bore", [(RAIL_BACK, 0.0), (RAIL_BACK, 0.0085), (RAIL_FRONT - 0.01, 0.0085), (RAIL_FRONT - 0.01, 0.0)], verts=20), M_GUN, bevel=0.0))
# Rails sit retracted in the build pose.
for ob in rl:
    ob.location.x += RAIL_RETRACT
objs["rails"] = part("rails", rl, pivot=(RAIL_RETRACT, 0, 0))

MZ_BUILD, MZ_ARMED = -0.060, 0.292
mz = []
mz.append(piece(ring("mz_ring", MZ_BUILD - 0.014, MZ_BUILD + 0.014, 0.031, 0.0125, 28), M_GUN, bevel=0.0008))
mz.append(piece(ring("mz_glow", MZ_BUILD + 0.0138, MZ_BUILD + 0.0148, 0.0175, 0.0128, 24), M_GLOW, bevel=0.0))
for k in range(3):
    a = math.radians(90 + k * 120)
    y, z = -math.sin(a), math.cos(a)
    prong = hs.prism(f"prong{k}", [(MZ_BUILD + 0.012, -0.004, 0.0), (MZ_BUILD + 0.040, -0.002, 0.0), (MZ_BUILD + 0.040, 0.002, 0.0), (MZ_BUILD + 0.012, 0.004, 0.0)], (0, 0, 0.007))
    prong.location = (0, 0, 0.024)
    bpy.context.view_layer.objects.active = prong
    bpy.ops.object.select_all(action="DESELECT")
    prong.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    prong.rotation_euler = (a, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    mz.append(piece(prong, M_GRAFT, bevel=0.0005))
objs["muzzle"] = part("muzzle", mz, pivot=(MZ_BUILD, 0, 0))

# ---------------------------------------------------------------- the hand
PALM_X0, PALM_X1 = 0.006, 0.090
PALM_HZ = 0.0165
HINGE_Y = 0.041


def palm_half(side):
    """side +1 = inner (thumb) half, -1 = outer half."""
    y0, y1 = (0.0012, 0.042) if side > 0 else (-0.042, -0.0012)
    pcs = []
    pcs.append(piece(rbox("palm_core", (PALM_X1 - PALM_X0 - 0.006, y1 - y0 - 0.004, PALM_HZ * 2 - 0.006),
                          ((PALM_X0 + PALM_X1) / 2, (y0 + y1) / 2, 0.0)), M_GUN, bevel=0.0012))
    # Back-of-hand plates (two facets) and a palm pad.
    pcs.append(piece(rbox("back_plate", (PALM_X1 - PALM_X0 - 0.012, y1 - y0 - 0.006, 0.004),
                          ((PALM_X0 + PALM_X1) / 2 - 0.002, (y0 + y1) / 2, PALM_HZ - 0.0005)), M_GRAFT, bevel=0.0008))
    pcs.append(piece(rbox("palm_pad", (PALM_X1 - PALM_X0 - 0.016, y1 - y0 - 0.008, 0.004),
                          ((PALM_X0 + PALM_X1) / 2, (y0 + y1) / 2, -PALM_HZ + 0.0005)), M_POLY, bevel=0.0012))
    pcs.append(piece(rbox("knuckle_glow", (0.0016, y1 - y0 - 0.010, 0.0014), (PALM_X1 - 0.010, (y0 + y1) / 2, PALM_HZ + 0.0016)), M_GLOW, bevel=0.0))
    # Inner face of the jaw: a rail channel that grips the bore when open.
    pcs.append(piece(rbox("jaw_face", (PALM_X1 - PALM_X0 - 0.01, 0.003, PALM_HZ * 1.4), ((PALM_X0 + PALM_X1) / 2, y0 + 0.0015 * side, 0.0)), M_RAIL, bevel=0.0004))
    if side > 0:
        # Thumb mount.
        pcs.append(piece(hs.cyl_between("thumb_mount", (0.016, 0.041, -0.004), (0.034, 0.047, -0.010), 0.0085, verts=14), M_GUN, bevel=0.0006))
    return pcs


FINGERS = {
    # name: (y, z, [segment lengths], side)
    "index": (0.0295, 0.002, [0.044, 0.027, 0.021], 1),
    "middle": (0.0105, 0.002, [0.048, 0.030, 0.022], 1),
    "ring": (-0.0095, 0.002, [0.045, 0.028, 0.021], -1),
    "little": (-0.0285, 0.0, [0.036, 0.022, 0.018], -1),
}
FW, FH = 0.0172, 0.0162


def finger_segment(name, x0, length, y, z, w, h, tip):
    pcs = []
    # Joint barrel at the base.
    pcs.append(piece(hs.cyl_y(name + "_joint", h * 0.42, w * 0.92, (x0, y, z), verts=12), M_GUN, bevel=0.0004))
    # Core and a graft shell on top, polymer pad underneath.
    pcs.append(piece(rbox(name + "_core", (length - 0.004, w * 0.78, h * 0.72), (x0 + length / 2, y, z)), M_GUN, bevel=0.0010))
    top = rbox(name + "_shell", (length - 0.006, w * 0.94, h * 0.34), (x0 + length / 2, y, z + h * 0.30))
    pcs.append(piece(top, M_GRAFT, bevel=0.0010))
    pcs.append(piece(rbox(name + "_pad", (length - 0.008, w * 0.80, h * 0.26), (x0 + length / 2, y, z - h * 0.33)), M_POLY, bevel=0.0012))
    if tip:
        pcs.append(piece(hs.cyl_y(name + "_tip", h * 0.40, w * 0.82, (x0 + length - 0.002, y, z), verts=12), M_GRAFT, bevel=0.0004))
    return pcs


wrist = empty("wrist", (0.0, 0.0, 0.0))
jaws = {}
for side, name in ((1, "jaw_in"), (-1, "jaw_out")):
    jaws[side] = part(name, palm_half(side), pivot=(PALM_X0, side * HINGE_Y, 0.0))
    objs[name] = jaws[side]
    parent(jaws[side], wrist)

fingers = {}
for fname, (y, z, lens, side) in FINGERS.items():
    x = PALM_X1
    prev = jaws[side]
    segs = []
    for k, L in enumerate(lens):
        w = FW * (1.0 - 0.06 * k)
        h = FH * (1.0 - 0.08 * k)
        seg = part(f"{fname}_{k + 1}", finger_segment(f"{fname}{k}", x, L, y, z, w, h, k == len(lens) - 1), pivot=(x, y, z))
        parent(seg, prev)
        objs[seg.name] = seg
        segs.append(seg)
        prev = seg
        x += L
    fingers[fname] = segs

# Thumb: built along +X at its base, then turned to point forward, in and down.
THUMB_BASE = V((0.030, 0.046, -0.008))
thumb_lens = [0.040, 0.030, 0.024]
tx = THUMB_BASE.x
tsegs = []
prev = jaws[1]
for k, L in enumerate(thumb_lens):
    w = 0.019 * (1.0 - 0.05 * k)
    h = 0.017 * (1.0 - 0.06 * k)
    seg = part(f"thumb_{k + 1}", finger_segment(f"thumb{k}", tx, L, THUMB_BASE.y, THUMB_BASE.z, w, h, k == 2),
               pivot=(tx, THUMB_BASE.y, THUMB_BASE.z))
    tsegs.append(seg)
    objs[seg.name] = seg
    tx += L
# Chain them, then aim the base.
for k in (1, 2):
    parent(tsegs[k], tsegs[k - 1])
THUMB_REST = (math.radians(-20), math.radians(18), math.radians(38))
tsegs[0].rotation_euler = THUMB_REST
parent(tsegs[0], jaws[1])

# Muzzle tip marker (rounds leave here).
tip = empty("muzzle_tip", (MZ_BUILD + 0.042, 0.0, 0.0))
parent(tip, objs["muzzle"])

# Hierarchy under one root.
root = empty("gx4_root")
for name in ("sleeve", "chassis", "plate_top", "plate_out", "plate_in", "rails", "muzzle") + tuple(f"coil_{i + 1}" for i in range(6)):
    parent(objs[name], root)
parent(wrist, root)
for k in range(3):
    parent(objs[f"fin_{k + 1}"], objs["plate_top"])
for k in range(10):
    parent(objs[f"led_{k}"], objs["plate_top"])

# ---------------------------------------------------------------- animation
REST = {}
for ob in bpy.data.objects:
    ob.rotation_mode = "XYZ"
    REST[ob.name] = (ob.location.copy(), ob.rotation_euler.copy())


def key(ob, frame, dloc=(0, 0, 0), drot=(0, 0, 0), interp="BEZIER"):
    """Keys `ob` at `frame` as rest + offset (location m, rotation deg)."""
    loc, rot = REST[ob.name]
    frame = frame if frame == 0 else frame + SHIFT
    ob.location = loc + V(dloc)
    ob.rotation_euler = (rot[0] + math.radians(drot[0]), rot[1] + math.radians(drot[1]), rot[2] + math.radians(drot[2]))
    ob.keyframe_insert("location", frame=frame)
    ob.keyframe_insert("rotation_euler", frame=frame)


def track(ob, keys):
    """keys: [(frame, dloc, drot)]"""
    for f, dl, dr in keys:
        key(ob, f, dl, dr)


# Fingers: relaxed in the hand pose, a fist by ~frame 22 (index first).
RELAX = [8, 12, 8]
FIST = [88, 98, 62]
for i, fname in enumerate(("index", "middle", "ring", "little")):
    f0 = 2 + i * 2
    for k, seg in enumerate(fingers[fname]):
        track(seg, [(0, (0, 0, 0), (0, RELAX[k] + i * 2, 0)), (f0, (0, 0, 0), (0, RELAX[k] + i * 2, 0)),
                    (f0 + 16, (0, 0, 0), (0, FIST[k] + 4, 0)), (f0 + 20, (0, 0, 0), (0, FIST[k], 0)), (84, (0, 0, 0), (0, FIST[k], 0))])
# Thumb: across the fist.
track(tsegs[0], [(0, (0, 0, 0), (0, 0, 0)), (8, (0, 0, 0), (0, 0, 0)), (24, (0, 0, 0), (18, 6, -40)), (84, (0, 0, 0), (18, 6, -40))])
track(tsegs[1], [(0, (0, 0, 0), (0, 10, 0)), (10, (0, 0, 0), (0, 10, 0)), (24, (0, 0, 0), (0, 40, 0)), (84, (0, 0, 0), (0, 40, 0))])
track(tsegs[2], [(0, (0, 0, 0), (0, 8, 0)), (12, (0, 0, 0), (0, 8, 0)), (24, (0, 0, 0), (0, 35, 0)), (84, (0, 0, 0), (0, 35, 0))])
# Wrist: palm turned in and the hand tilted up (raised to look at it), then straight.
track(wrist, [(0, (0, 0, 0), (72, -16, 8)), (14, (0, 0, 0), (66, -14, 6)), (34, (0, 0, 0), (-4, 2, 0)), (40, (0, 0, 0), (0, 0, 0)), (84, (0, 0, 0), (0, 0, 0))])
# Jaws: the fist splits into a fork.
JAW_DEG, JAW_DY = 14.0, 0.031
for side in (1, -1):
    track(jaws[side], [(0, (0, 0, 0), (0, 0, 0)), (30, (0, 0, 0), (0, 0, 0)),
                       (44, (0, side * JAW_DY * 1.06, 0), (0, 0, side * (JAW_DEG + 2.5))),
                       (48, (0, side * JAW_DY, 0), (0, 0, side * JAW_DEG)), (84, (0, side * JAW_DY, 0), (0, 0, side * JAW_DEG))])
# Plates open.
track(objs["plate_top"], [(0, (0, 0, 0), (0, 0, 0)), (24, (0, 0, 0), (0, 0, 0)), (40, (-0.004, 0, 0.016), (0, 3.5, 0)), (44, (-0.004, 0, 0.0145), (0, 3.0, 0)), (84, (-0.004, 0, 0.0145), (0, 3.0, 0))])
track(objs["plate_out"], [(0, (0, 0, 0), (0, 0, 0)), (26, (0, 0, 0), (0, 0, 0)), (42, (0, 0, 0), (-40, 0, 0)), (46, (0, 0, 0), (-36, 0, 0)), (84, (0, 0, 0), (-36, 0, 0))])
track(objs["plate_in"], [(0, (0, 0, 0), (0, 0, 0)), (28, (0, 0, 0), (0, 0, 0)), (44, (0, 0, 0), (40, 0, 0)), (48, (0, 0, 0), (36, 0, 0)), (84, (0, 0, 0), (36, 0, 0))])
# Rails telescope out through the fork.
RX = -RAIL_RETRACT
track(objs["rails"], [(0, (0, 0, 0), (0, 0, 0)), (36, (0, 0, 0), (0, 0, 0)), (56, (RX + 0.006, 0, 0), (0, 0, 0)), (60, (RX, 0, 0), (0, 0, 0)), (84, (RX, 0, 0), (0, 0, 0))])
# Coils slide out one by one, front coil first, each overshooting a touch and locking.
for i in range(6):
    ob = objs[f"coil_{i + 1}"]
    d = COIL_ARMED[i] - COIL_PACKED[i]
    f0 = 40 + (5 - i) * 5
    track(ob, [(0, (0, 0, 0), (0, 0, 0)), (f0, (0, 0, 0), (0, 0, 0)), (f0 + 11, (d + 0.005, 0, 0), (32, 0, 0)), (f0 + 14, (d, 0, 0), (30, 0, 0)), (84, (d, 0, 0), (30, 0, 0))])
# Muzzle ring last.
track(objs["muzzle"], [(0, (0, 0, 0), (0, 0, 0)), (52, (0, 0, 0), (0, 0, 0)), (66, (MZ_ARMED - MZ_BUILD + 0.006, 0, 0), (0, 0, 0)), (70, (MZ_ARMED - MZ_BUILD, 0, 0), (0, 0, 0)), (84, (MZ_ARMED - MZ_BUILD, 0, 0), (0, 0, 0))])
# Fins stand up.
for k in range(3):
    f0 = 62 + k * 3
    track(objs[f"fin_{k + 1}"], [(0, (0, 0, 0), (0, 0, 0)), (f0, (0, 0, 0), (0, 0, 0)), (f0 + 12, (0, 0, 0), (0, 64, 0)), (f0 + 15, (0, 0, 0), (0, 58, 0)), (84, (0, 0, 0), (0, 58, 0))])

# Static parts still need a key so every node is in the one clip.
for name in ("sleeve", "chassis"):
    track(objs[name], [(0, (0, 0, 0), (0, 0, 0)), (84, (0, 0, 0), (0, 0, 0))])

action_count = len(bpy.data.actions)


def to_nla(name="deploy"):
    """Every part's keys onto an NLA track named `name`, so the glTF exporter
    merges them into one clip (otherwise it writes one animation per part)."""
    for ob in bpy.data.objects:
        ad = ob.animation_data
        if ad is None or ad.action is None:
            continue
        act = ad.action
        slot = ad.action_slot
        track = ad.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 0, act)
        if slot is not None and hasattr(strip, "action_slot"):
            strip.action_slot = slot
        ad.action = None


def tri_count():
    n = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            n += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return n


print(f"gx4: {tri_count()} triangles, {action_count} actions")


# ---------------------------------------------------------------- export
def export(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    to_nla()
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_apply=True,
                              export_animations=True, export_animation_mode="NLA_TRACKS",
                              export_merge_animation="NLA_TRACK",
                              export_force_sampling=True, export_frame_range=True,
                              export_optimize_animation_size=False, export_extras=False,
                              export_yup=True, export_cameras=False, export_lights=False)
    print(f"gx4: exported {path}")


# ---------------------------------------------------------------- preview
def setup_render():
    w, h = (int(x) for x in args.res.split("x"))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("night")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.012, 0.018, 1)
    scene.world = world

    def area(name, loc, energy, size, color=(1, 1, 1), aim=(-0.05, 0, 0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color, ld.size = energy, color, size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.3, -0.9, 0.8), 30, 1.0, (1.0, 0.9, 0.85))
    area("neon_l", (0.4, 0.9, 0.3), 18, 0.8, (1.0, 0.35, 0.45))
    area("neon_r", (0.6, -0.8, -0.1), 14, 0.8, (0.35, 0.7, 1.0))
    area("top", (0.0, 0.0, 0.9), 10, 1.2, (0.8, 0.85, 1.0))
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    return cam


VIEWS = {
    # Roughly the player's eye: behind, above and left of the right forearm.
    "fp": ((-0.46, 0.17, 0.17), (0.55, -0.03, -0.06), 62),
    "hero": ((0.42, -0.42, 0.20), (-0.04, 0.0, 0.0), 0),
    "hand": ((0.26, 0.16, 0.12), (0.04, 0.0, 0.0), 0),
    "top": ((0.0, -0.0001, 0.6), (0.0, 0.0, 0.0), 0),
    "tophand": ((0.06, -0.0001, 0.3), (0.06, 0.0, 0.0), 0),
    "side": ((0.06, -0.3, 0.0), (0.06, 0.0, 0.0), 0),
}


def render_previews(stem):
    cam = setup_render()
    frames = [int(f) for f in args.frames.split(",") if f]
    for view in [v for v in args.views.split(",") if v]:
        loc, target, fov = VIEWS[view]
        d = cam.data
        d.clip_start = 0.01
        if fov:
            d.sensor_fit = "VERTICAL"
            d.angle = math.radians(fov)
        else:
            d.sensor_fit = "AUTO"
            d.lens = 40
        cam.location = loc
        cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
        for f in frames:
            scene.frame_set(f)
            scene.render.filepath = f"{stem}_{view}_{f:02d}.png"
            bpy.ops.render.render(write_still=True)
            print(f"gx4: rendered {scene.render.filepath}")


if args.rest:
    for ob in bpy.data.objects:
        ob.animation_data_clear()
        if ob.name in REST:
            ob.location, ob.rotation_euler = REST[ob.name]
if args.out:
    export(args.out)
if args.preview:
    render_previews(args.preview.rsplit(".", 1)[0])
if os.environ.get("GX4_DEBUG"):
    bpy.context.view_layer.update()
    for n in ("thumb_1", "thumb_3", "index_1", "index_3", "jaw_in", "jaw_out"):
        ob = bpy.data.objects[n]
        print("DBG", n, tuple(round(v, 3) for v in ob.matrix_world.translation), tuple(round(math.degrees(a), 1) for a in ob.matrix_world.to_euler()))
