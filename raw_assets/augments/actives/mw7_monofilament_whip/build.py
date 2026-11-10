"""MW-7 Monofilament Whip: the first-person right arm with the reel (owner, 2026-11-10: "mono filament razor
whip"; docs/design.md §3.4).

Design (hardware, no magic): a monomolecular filament can't be held, so it lives on a sealed reel on the back
of the right wrist. A feed boom runs forward from the reel over the back of the hand to a ceramic nozzle; the
filament and its tungsten bead leave from there (the game draws them: `emitter` marks the nozzle mouth). Two
blade guards stand up either side of the boom so the filament can't fall back across the knuckles. The hand
makes a two-finger point along the boom: that's the handle the operative swings.

Deploy clip (60 fps, frames 0-36 = 0.6 s; the game raises the arm into view over the first third):
   0-14  ring and little fingers curl, thumb folds over them; index and middle stay out along the boom
   6-20  the two guards swing up and out
  10-28  the boom slides forward over the knuckles (a touch of overshoot)
  22-34  the nozzle's two jaws open; the reel turns as it pays out

Parts (glTF nodes): forearm (static), reel (drum: turns), boom > nozzle_l, nozzle_r, emitter; guard_in,
guard_out; wrist > palm > fingers. Materials: graft, weave, polymer, gunmetal (the suit colours repaint
these), steel, copper, ceramic, glow (the game drives it).

Run:
  tools/blender.sh raw_assets/augments/actives/mw7_monofilament_whip/build.py \
      --out assets/augments/mw7_monofilament_whip/mw7_monofilament_whip.gltf --preview docs/previews/mw7_monofilament_whip.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

END = 36
args = K.init("mw7", END, "0,12,24,36")
K.mat("ceramic", (0.82, 0.8, 0.74), 0.35, 0.0)

# ---------------------------------------------------------------- forearm, reel
fore = K.forearm(side=1, top_gap=True)
# Saddle the reel sits in (replaces the top plate near the wrist).
fore.append(K.piece(hs.box("saddle", (0.105, 0.062, 0.012), (-0.085, 0.0, 0.046)), "gunmetal", bevel=0.002))
fore.append(K.piece(K.shell("top_plate", K.X_ELBOW + 0.02, -0.15, K.r_at(K.X_ELBOW + 0.02) + 0.0015, K.r_at(-0.15) + 0.0015, -38, 38, 0.0045, seg=3), "graft", bevel=0.0008))
for s in (1, -1):
    fore.append(K.piece(hs.box("cheek", (0.07, 0.004, 0.05), (-0.085, s * 0.031, 0.066)), "graft", bevel=0.0012))
    fore.append(K.piece(hs.cyl_y("axle_cap", 0.009, 0.006, (-0.085, s * 0.035, 0.07), verts=14), "steel", bevel=0.0008))
# Feed cable from the reel housing back into the sleeve.
fore.append(K.piece(hs.tube_path("feed", [(-0.13, 0.012, 0.058), (-0.18, 0.016, 0.056), (-0.24, 0.012, 0.052), (-0.285, 0.006, 0.046)], 0.0035), "polymer", bevel=0.0))
forearm = K.part("forearm", fore)

# The drum: copper windings between two flanges, a glow ring on each face.
drum = [K.piece(hs.cyl_y("drum_core", 0.021, 0.05, (-0.085, 0.0, 0.07), verts=28), "copper", bevel=0.0006)]
for s in (1, -1):
    drum.append(K.piece(hs.cyl_y("flange", 0.026, 0.004, (-0.085, s * 0.026, 0.07), verts=28), "gunmetal", bevel=0.0008))
    drum.append(K.piece(hs.cyl_y("ring_glow", 0.0235, 0.0012, (-0.085, s * 0.0288, 0.07), verts=28), "glow", bevel=0.0))
for k in range(6):
    a = k * math.pi / 3
    drum.append(K.piece(hs.cyl_y("spoke", 0.0028, 0.058, (-0.085 + 0.015 * math.cos(a), 0.0, 0.07 + 0.015 * math.sin(a)), verts=8), "steel", bevel=0.0))
reel = K.part("reel", drum, pivot=(-0.085, 0.0, 0.07))

# ---------------------------------------------------------------- boom, nozzle, guards
BX0, BX1, BZ = -0.06, 0.075, 0.052
bm = [K.piece(hs.box("boom_rail", (BX1 - BX0, 0.012, 0.008), ((BX0 + BX1) / 2, 0.0, BZ)), "gunmetal", bevel=0.0014),
      K.piece(hs.box("boom_top", (BX1 - BX0 - 0.02, 0.016, 0.003), ((BX0 + BX1) / 2 - 0.004, 0.0, BZ + 0.0052)), "graft", bevel=0.0008),
      K.piece(hs.box("boom_glow", (BX1 - BX0 - 0.04, 0.0016, 0.0012), ((BX0 + BX1) / 2, 0.0, BZ + 0.0072)), "glow", bevel=0.0),
      K.piece(hs.cyl_x("nozzle_body", 0.0085, BX1 - 0.004, BX1 + 0.018, verts=18, z=BZ), "steel", bevel=0.0008),
      K.piece(hs.cyl_x("nozzle_throat", 0.0045, BX1 + 0.016, BX1 + 0.026, verts=14, z=BZ), "ceramic", bevel=0.0004)]
boom = K.part("boom", bm, pivot=(BX0, 0.0, BZ))
jaws = {}
for s, name in ((1, "nozzle_l"), (-1, "nozzle_r")):
    j = [K.piece(hs.box("jaw", (0.02, 0.005, 0.012), (BX1 + 0.03, s * 0.0045, BZ)), "ceramic", bevel=0.001),
         K.piece(hs.box("jaw_lip", (0.004, 0.006, 0.014), (BX1 + 0.041, s * 0.004, BZ)), "steel", bevel=0.0008)]
    jaws[s] = K.part(name, j, pivot=(BX1 + 0.02, s * 0.007, BZ))
    K.parent(jaws[s], boom)
emitter = K.empty("emitter", (BX1 + 0.044, 0.0, BZ))
K.parent(emitter, boom)

guards = {}
for s, name in ((1, "guard_in"), (-1, "guard_out")):
    # A swept blade lying flat beside the boom; it stands up and leans out.
    pts = [(0.0, 0.0), (0.085, 0.0), (0.105, 0.012), (0.07, 0.03), (0.01, 0.022)]
    g = [K.piece(K.poly_plate("blade", pts, 0.003, origin=(-0.035, s * 0.02, 0.05), u=(1, 0, 0), v=(0, s, 0)), "graft", bevel=0.0008),
         K.piece(hs.cyl_x("hinge", 0.004, -0.037, -0.02, verts=10, y=s * 0.02, z=0.0515), "steel", bevel=0.0004),
         K.piece(K.poly_plate("edge", [(0.02, 0.024), (0.07, 0.031), (0.07, 0.033), (0.02, 0.026)], 0.0034, origin=(-0.035, s * 0.02, 0.0498), u=(1, 0, 0), v=(0, s, 0)), "glow", bevel=0.0)]
    guards[s] = K.part(name, g, pivot=(-0.035, s * 0.02, 0.0515))

wrist, palm, fingers, thumb = K.hand(side=1)

root = K.empty("mw7_root")
for ob in (forearm, reel, boom, guards[1], guards[-1], wrist):
    K.parent(ob, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
K.curl(fingers, thumb, 0, 14, END, which=("ring", "little"))
K.track(wrist, [(0, (0, 0, 0), (0, -6, 0)), (14, (0, 0, 0), (0, 4, 0)), (END, (0, 0, 0), (0, 4, 0))])
K.hold(palm, END)
for s in (1, -1):
    K.track(guards[s], [(0, (0, 0, 0), (0, 0, 0)), (6, (0, 0, 0), (0, 0, 0)), (17, (0, 0, 0), (s * 76, 0, 0)), (20, (0, 0, 0), (s * 68, 0, 0)), (END, (0, 0, 0), (s * 68, 0, 0))])
SLIDE = 0.052
K.track(boom, [(0, (-SLIDE, 0, 0), (0, 0, 0)), (10, (-SLIDE, 0, 0), (0, 0, 0)), (25, (0.005, 0, 0), (0, 3, 0)), (28, (0, 0, 0), (0, 2, 0)), (END, (0, 0, 0), (0, 2, 0))])
for s in (1, -1):
    K.track(jaws[s], [(0, (0, 0, 0), (0, 0, 0)), (22, (0, 0, 0), (0, 0, 0)), (31, (0, 0, 0), (0, 0, s * 34)), (34, (0, 0, 0), (0, 0, s * 28)), (END, (0, 0, 0), (0, 0, s * 28))])
K.hold(emitter, END)
K.track(reel, [(0, (0, 0, 0), (0, 0, 0)), (10, (0, 0, 0), (0, 0, 0)), (END, (0, 0, 0), (0, 540, 0))])
K.hold(forearm, END)
K.hold(root, END)

VIEWS = {
    # The player's eye: behind, above and left of the right forearm.
    "fp": ((-0.46, 0.2, 0.2), (0.6, -0.06, -0.06), 62),
    "hero": ((0.34, -0.36, 0.24), (-0.03, 0.0, 0.03), 0),
}
K.finish([root], END, VIEWS)
