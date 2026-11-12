"""AD-2 Arc Projector: the shoulder electrolaser as seen from the operative's eye (2026-11-10; docs/design.md
§3.4).

Design (hardware, no magic): an electrolaser. A UV laser ionizes a thin channel of air to the target; a
capacitor bank then dumps down that channel. The emitter head rides a short mast on the right shoulder
hardpoint: a finned capacitor body, a quartz laser window in the nose, and three tungsten electrodes round it
that open like a chuck. Folded, the head lies back behind the shoulder. In first person it swings up into the
top right corner of the view and points where the operative looks (`muzzle_tip` marks the laser window).

Deploy clip (60 fps, frames 0-24 = 0.4 s):
   0-16  the mast swings the head up and forward over the shoulder (overshoots, settles)
   8-20  the head levels
  14-24  the three electrodes open; the window lights (the game drives `glow`)

Parts (glTF nodes): base (static: the shoulder hardpoint block), mast > head > prong_1..3, muzzle_tip.
Materials: graft, gunmetal (suit colours), steel, copper, tungsten, glow.

Axes: +X forward, +Z up; the origin is the head's centre when deployed.

Run:
  tools/blender.sh raw_assets/augments/actives/ad2_arc_projector/build.py \
      --out assets/augments/ad2_arc_projector/ad2_arc_projector.gltf --preview docs/previews/ad2_arc_projector.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

END = 24
args = K.init("ad2", END, "0,8,16,24")
K.mat("tungsten", (0.2, 0.2, 0.22), 0.3, 1.0)

HINGE = V((-0.2, 0.0, -0.09))
base = K.part("base", [K.piece(hs.box("block", (0.1, 0.07, 0.04), (HINGE.x - 0.01, 0.0, HINGE.z - 0.03)), "gunmetal", bevel=0.004),
                       K.piece(hs.box("pad", (0.12, 0.085, 0.01), (HINGE.x - 0.01, 0.0, HINGE.z - 0.052)), "graft", bevel=0.002),
                       K.piece(hs.cyl_y("hinge_pin", 0.012, 0.085, tuple(HINGE), verts=18), "steel", bevel=0.001),
                       K.piece(hs.box("status", (0.03, 0.0016, 0.004), (HINGE.x + 0.01, -0.0355, HINGE.z - 0.03)), "glow", bevel=0.0)])

# Mast: two struts from the hinge to the head's yoke, a cable between them.
mp = []
for s in (1, -1):
    mp.append(K.piece(hs.cyl_between("strut", (HINGE.x, s * 0.026, HINGE.z), (-0.05, s * 0.03, -0.012), 0.007, verts=12), "gunmetal", bevel=0.0006))
    mp.append(K.piece(hs.cyl_y("yoke_cap", 0.012, 0.008, (-0.05, s * 0.034, -0.012), verts=14), "steel", bevel=0.0008))
mp.append(K.piece(hs.tube_path("cable", [(HINGE.x + 0.01, 0.0, HINGE.z + 0.01), (-0.15, 0.006, -0.03), (-0.1, 0.0, -0.035), (-0.075, 0.0, -0.022)], 0.0045), "polymer", bevel=0.0))
mast = K.part("mast", mp, pivot=tuple(HINGE))

# Head: a finned capacitor body, a nose ring, the laser window.
hp = [K.piece(hs.lathe_x("body", [(-0.085, 0.0), (-0.085, 0.022), (-0.075, 0.028), (0.02, 0.028), (0.04, 0.022), (0.05, 0.022), (0.05, 0.0)], verts=24), "graft", bevel=0.0012),
      K.piece(K.ring("nose", 0.048, 0.062, 0.024, 0.012), "gunmetal", bevel=0.001),
      K.piece(hs.cyl_x("window", 0.012, 0.05, 0.056, verts=20), "glow", bevel=0.0),
      K.piece(hs.cyl_x("tail_cap", 0.016, -0.095, -0.083, verts=18), "copper", bevel=0.001)]
for k in range(9):
    x = -0.066 + k * 0.0095
    hp.append(K.piece(K.ring("fin", x, x + 0.0035, 0.034, 0.027, verts=24), "gunmetal", bevel=0.0005))
for k in range(3):
    a = math.radians(90 + k * 120)
    hp.append(K.piece(hs.box("seam", (0.07, 0.0016, 0.0016), (-0.02, 0.0345 * math.cos(a), 0.0345 * math.sin(a))), "glow", bevel=0.0))
head = K.part("head", hp, pivot=(-0.05, 0.0, -0.012))
K.parent(head, mast)

prongs = []
for k in range(3):
    a = math.radians(90 + k * 120)
    c, s = math.cos(a), math.sin(a)
    pp = [K.piece(hs.cyl_between("root", (0.03, 0.03 * c, 0.03 * s), (0.052, 0.03 * c, 0.03 * s), 0.0065, verts=10), "copper", bevel=0.0006),
          K.piece(hs.cyl_between("rod", (0.05, 0.03 * c, 0.03 * s), (0.12, 0.016 * c, 0.016 * s), 0.0042, verts=10, radius2=0.0022), "tungsten", bevel=0.0),
          K.piece(hs.cyl_between("tip", (0.118, 0.0165 * c, 0.0165 * s), (0.128, 0.0145 * c, 0.0145 * s), 0.0026, verts=8, radius2=0.0008), "steel", bevel=0.0)]
    ob = K.part(f"prong_{k + 1}", pp, pivot=(0.034, 0.03 * c, 0.03 * s))
    K.parent(ob, head)
    prongs.append((ob, c, s))
tip = K.empty("muzzle_tip", (0.062, 0.0, 0.0))
K.parent(tip, head)

root = K.empty("ad2_root")
K.parent(base, root)
K.parent(mast, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
K.hold(base, END)
K.hold(root, END)
K.hold(tip, END)
# Folded: the mast lies back (rotated about Y so the head goes back and down behind the shoulder).
K.track(mast, [(0, (0, 0, 0), (0, -118, 0)), (13, (0, 0, 0), (0, 7, 0)), (16, (0, 0, 0), (0, 0, 0)), (END, (0, 0, 0), (0, 0, 0))])
K.track(head, [(0, (0, 0, 0), (0, 70, 0)), (8, (0, 0, 0), (0, 50, 0)), (18, (0, 0, 0), (0, -4, 0)), (20, (0, 0, 0), (0, 0, 0)), (END, (0, 0, 0), (0, 0, 0))])
for ob, c, s in prongs:
    # Open: tilt outward about the tangent axis.
    ax = V((0, -s, c)) * 16.0
    K.track(ob, [(0, (0, 0, 0), (0, 0, 0)), (14, (0, 0, 0), (0, 0, 0)), (21, (0, 0, 0), (0, ax.y * 1.2, ax.z * 1.2)), (END, (0, 0, 0), (0, ax.y, ax.z))])

VIEWS = {
    # The player's eye: below, behind and left of the head (it sits over the right shoulder).
    "fp": ((-0.36, 0.3, -0.24), (0.7, 0.3, -0.3), 62),
    "hero": ((0.3, -0.34, 0.14), (-0.06, 0.0, -0.03), 0),
}
K.finish([root], END, VIEWS)
