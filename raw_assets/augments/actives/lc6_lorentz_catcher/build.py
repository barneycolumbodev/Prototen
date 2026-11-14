"""LC-6 Lorentz Catcher: the first-person left arm (owner, 2026-11-13: an augment that "collects the bullets fired
at" you while LB is held, then "releases a cloud of them in a large area of effect where you are aiming"; it "can
only shoot as many back as it picked up"; docs/design.md §3.4d).

Design (hardware, no magic): rounds are copper-jacketed lead, and a strong, fast-changing magnetic field drags on
any conductor (eddy currents; the force is the Lorentz force on the induced currents). Eight coil petals ride on a
drive ring behind the left wrist. Folded, they lie back along the forearm like a slatted sleeve. On deploy they
swing forward through about 150 degrees and lock flared round the open hand, a crown of copper windings whose
pulsed field reaches out in front of the palm: rounds flying into it are braked to a stop and held, hot, in
suspension. The same coils, run as a coilgun, throw them back out.

Each petal: a satin graft slat with a copper winding pack (seven turns) on its outer face, a lit strip down its
inner face, a gunmetal tip shoe and a hinge knuckle. The drive ring: a gunmetal collar with eight hinge lugs and a
lit seam; a power conduit runs from it back along the inner forearm into the sleeve.

Deploy clip (60 fps, frames 0-24 = 0.4 s; the game raises the arm into view over the first third):
   0-12  the hand opens: fingers spread and hook a little, the thumb swings out, the wrist tips up
   2-22  the petals swing forward one after another (alternate sides), overshoot open and settle

Parts (glTF nodes): forearm (static: suit forearm, conduit), ring (static), hinge_0..7 (static, turned round the
arm) > petal_0..7 (the hinge is the node's Y axis), wrist > palm > fingers, thumb; `focus` (an empty 0.36 m in front
of the palm: the middle of the field). Materials: weave, graft, polymer, gunmetal (suit colours), copper, glow (the
game drives it).

Run:
  tools/blender.sh raw_assets/augments/actives/lc6_lorentz_catcher/build.py \
      --out assets/augments/lc6_lorentz_catcher/lc6_lorentz_catcher.gltf --preview docs/previews/lc6_lorentz_catcher.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import hs  # noqa: E402

END = 24
args = K.init("lc6", END, "0,8,14,24")
K.mat("glow", (0.05, 0.08, 0.12), 0.3, 0.0, emission=((0.48, 0.78, 1.0), 2.5))
K.mat("winding", (0.80, 0.42, 0.22), 0.26, 1.0)

SIDE = -1  # left arm: +Y is the outer side
N = 8
HINGE_X = -0.034  # the drive ring's hinge line
HINGE_R = 0.061
PET_L = 0.19      # petal length
PET_W = 0.027     # petal width (round the arm)
PET_T = 0.0055    # slat thickness
FLARE = 19.0      # deployed: degrees out from the arm's axis
STOW = -150.0     # extra rotation (deg about the hinge) that lays a petal back along the forearm

# ---------------------------------------------------------------- forearm and conduit
fore = K.forearm(side=SIDE)
# A power conduit from the ring back along the inner underside of the forearm into the sleeve.
a = math.radians(205.0)
cy, cz = -math.sin(a) * SIDE * -1.0, math.cos(a)
pts = [(HINGE_X - 0.02, 0.054 * cy, 0.054 * cz), (-0.12, 0.057 * cy, 0.057 * cz), (-0.25, 0.06 * cy, 0.06 * cz), (-0.33, 0.06 * cy, 0.06 * cz)]
fore.append(K.piece(hs.tube_path("conduit", pts, 0.0045), "polymer", bevel=0.0))
for x in (-0.11, -0.21):
    fore.append(K.piece(K.ring("conduit_clip", x - 0.005, x + 0.005, 0.0545, 0.049), "gunmetal", bevel=0.0008))
forearm = K.part("forearm", fore)

# ---------------------------------------------------------------- drive ring
ring_pcs = [K.piece(K.ring("ring", HINGE_X - 0.016, HINGE_X + 0.013, 0.058, 0.041, verts=32), "gunmetal", bevel=0.0012),
            K.piece(K.ring("ring_seam", HINGE_X - 0.0035, HINGE_X + 0.0005, 0.0588, 0.05, verts=32), "glow", bevel=0.0),
            K.piece(K.ring("ring_lip", HINGE_X + 0.013, HINGE_X + 0.018, 0.052, 0.042, verts=32), "graft", bevel=0.0006)]
for k in range(N):
    th = math.radians(22.5 + 45.0 * k)
    y, z = -math.sin(th), math.cos(th)
    # Two lugs either side of each knuckle.
    for s in (-1, 1):
        off = s * (PET_W * 0.5 + 0.0022)
        ty, tz = math.cos(th), math.sin(th)  # tangent round the arm
        c = (HINGE_X, y * (HINGE_R - 0.004) + ty * off, z * (HINGE_R - 0.004) + tz * off)
        ring_pcs.append(K.piece(hs.box("lug", (0.014, 0.003, 0.010), c, rot=(-th, 0, 0)), "gunmetal", bevel=0.0006))
ring = K.part("ring", ring_pcs, pivot=(HINGE_X, 0.0, 0.0))


# ---------------------------------------------------------------- petals
def petal_pieces(k):
    """One petal built at the top of the arm (+Z), pointing straight forward from its hinge at the origin."""
    pcs = []
    # The slat, and a shallow keel along its back.
    pcs.append(K.piece(hs.box("slat", (PET_L, PET_W, PET_T), (PET_L * 0.5, 0.0, 0.0)), "graft", bevel=0.0012))
    pcs.append(K.piece(hs.box("keel", (PET_L * 0.8, 0.006, 0.003), (PET_L * 0.45, 0.0, PET_T * 0.5 + 0.0012)), "graft", bevel=0.0008))
    # The winding pack: seven turns of flat copper round the slat's middle.
    for i in range(7):
        x = 0.056 + i * 0.0102
        pcs.append(K.piece(hs.box("turn", (0.0072, PET_W + 0.0034, PET_T + 0.0042), (x, 0.0, 0.0)), "winding", bevel=0.0007))
    pcs.append(K.piece(hs.box("pack_core", (0.074, PET_W + 0.001, PET_T + 0.0022), (0.0866, 0.0, 0.0)), "gunmetal", bevel=0.0005))
    # The lit strip on the inner face (toward the arm), and the tip shoe.
    pcs.append(K.piece(hs.box("strip", (PET_L * 0.86, 0.0032, 0.0012), (PET_L * 0.5, 0.0, -PET_T * 0.5 - 0.0004)), "glow", bevel=0.0))
    pcs.append(K.piece(hs.box("shoe", (0.016, PET_W * 0.86, PET_T + 0.002), (PET_L - 0.006, 0.0, 0.0)), "gunmetal", bevel=0.0012))
    pcs.append(K.piece(hs.box("shoe_glow", (0.0016, PET_W * 0.6, 0.0012), (PET_L + 0.0022, 0.0, 0.0)), "glow", bevel=0.0))
    # The hinge knuckle (along Y: the hinge axis).
    pcs.append(K.piece(hs.cyl_y("knuckle", 0.0045, PET_W - 0.002, (0.0, 0.0, 0.0), verts=14), "gunmetal", bevel=0.0005))
    return pcs


hinges, petals = [], []
for k in range(N):
    h = K.empty(f"hinge_{k}", (HINGE_X, 0.0, 0.0))
    p = K.part(f"petal_{k}", petal_pieces(k))
    p.location = (HINGE_X, 0.0, HINGE_R)
    p.rotation_euler = (0.0, math.radians(-FLARE), 0.0)
    K.parent(p, h)
    h.rotation_euler = (math.radians(22.5 + 45.0 * k), 0.0, 0.0)
    hinges.append(h)
    petals.append(p)

# ---------------------------------------------------------------- hand and the field's middle
wrist, palm, fingers, thumb = K.hand(side=SIDE)
focus = K.empty("focus", (0.36, 0.0, 0.03))

root = K.empty("lc6_root")
for ob in [forearm, ring, wrist, focus] + hinges:
    K.parent(ob, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
for ob in [root, forearm, ring, palm, focus] + hinges:
    K.hold(ob, END)
# The petals swing forward in alternating order round the ring, overshoot open, settle.
ORDER = [0, 4, 2, 6, 1, 5, 3, 7]
for i, k in enumerate(ORDER):
    f0 = 2 + i * 1.4
    f0 = int(round(f0))
    K.track(petals[k], [(0, (0, 0, 0), (0, STOW, 0)), (f0, (0, 0, 0), (0, STOW, 0)), (f0 + 7, (0, 0, 0), (0, -9, 0)),
                        (f0 + 10, (0, 0, 0), (0, 3, 0)), (min(f0 + 13, END), (0, 0, 0), (0, 0, 0)), (END, (0, 0, 0), (0, 0, 0))])
# Wrist tips up a little; the hand opens wide.
K.track(wrist, [(0, (0, 0, 0), (0, 6, 0)), (3, (0, 0, 0), (0, 4, 0)), (12, (0, 0, 0), (0, -16, 0)), (16, (0, 0, 0), (0, -13, 0)), (END, (0, 0, 0), (0, -13, 0))])
SPREAD = {"index": 10, "middle": 3, "ring": -4, "little": -11}
for i, (fname, segs) in enumerate(fingers.items()):
    f0 = 1 + i
    yaw = SPREAD[fname] * SIDE
    for k2, seg in enumerate(segs):
        o = (8, 12, 8)[k2] + i * 2
        z = yaw if k2 == 0 else 0
        hook = (2, 14, 12)[k2]
        K.track(seg, [(0, (0, 0, 0), (0, o, 0)), (f0, (0, 0, 0), (0, o, 0)), (f0 + 8, (0, 0, 0), (0, -8 if k2 == 0 else 0, z * 1.15)),
                      (f0 + 12, (0, 0, 0), (0, hook, z)), (END, (0, 0, 0), (0, hook, z))])
K.track(thumb[0], [(0, (0, 0, 0), (0, 0, 0)), (2, (0, 0, 0), (0, 0, 0)), (11, (0, 0, 0), (-14 * SIDE, -8, 30 * SIDE)), (END, (0, 0, 0), (-14 * SIDE, -8, 30 * SIDE))])
K.track(thumb[1], [(0, (0, 0, 0), (0, 10, 0)), (11, (0, 0, 0), (0, 8, 0)), (END, (0, 0, 0), (0, 8, 0))])
K.track(thumb[2], [(0, (0, 0, 0), (0, 8, 0)), (11, (0, 0, 0), (0, 10, 0)), (END, (0, 0, 0), (0, 10, 0))])

VIEWS = {
    # The player's eye: behind, above and right of the left forearm.
    "fp": ((-0.5, -0.22, 0.14), (0.4, 0.04, 0.0), 62),
    "hero": ((0.38, -0.32, 0.2), (0.0, 0.0, 0.0), 0),
}
K.finish([root], END, VIEWS)
