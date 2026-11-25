"""HV-3 Harvester Hive: the first-person left arm (owner, 2026-11-24: "your character holds up his hand, some cool
but very quick and functional animation plays... a vent opens up on his hand and a swarm of tiny robotic flies fly
out... they pick his skin clean... then they fly back into my vent" and it heals; docs/design.md §3.4e).

Design (hardware, no magic): a hive grafted into the left hand and wrist. The palm is a hexagonal vent: a
honeycomb of seven bays (each a docking bay for a stack of harvesters) under a six-petal iris. The harvesters
(~300 microdrones with carbide mandibles) sleep packed in a windowed canister along the inner forearm and feed
up into the bays through the wrist collar. Six hex cells on the back of the hand show how many are home: they go
dark as the swarm leaves and light again as it docks (the game drives `cell0`..`cell5`).

Deploy clip (60 fps, frames 0-21 = 0.35 s; the game raises the arm into view over the first third):
   0-9   the forearm comes up rolled palm-up (the player sees the palm); the fingers spread and stretch back
   3-13  the iris blooms: six petals one after another flip up out of the palm on their hinges and lock
         standing round the vent like a crown; the honeycomb lights red
   9-17  the forearm rolls over and the wrist snaps back: the palm, vent open, turns to face down range (a
         "stop" hand), the back of the hand and its six cells toward the eye
  17-21  settle

Parts (glTF nodes): arm (rolls) > forearm (static suit forearm), canister, wrist > palm (vent, honeycomb,
cells), petal_mount_N > petal_N, fingers, thumb. Materials: weave, graft, polymer, gunmetal (suit colours),
void, glow (vent and canister, driven by the game), cell0..cell5 (driven one by one).

Run:
  tools/blender.sh raw_assets/augments/actives/hv3_harvester_hive/build.py \
      --out assets/augments/hv3_harvester_hive/hv3_harvester_hive.gltf --preview docs/previews/hv3_harvester_hive.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

END = 21
args = K.init("hv3", END, "0,6,12,21", views_default="fp,palm,hero")
RED = (1.0, 0.16, 0.09)
K.mat("void", (0.004, 0.003, 0.003), 0.9, 0.0)
K.mat("glow", (0.12, 0.02, 0.015), 0.3, 0.0, emission=(RED, 3.0))
for k in range(6):
    K.mat(f"cell{k}", (0.1, 0.015, 0.012), 0.25, 0.0, emission=(RED, 2.4))

SIDE = -1  # left arm: +Y is the outer side, -Y the inner side (toward the eye)
PALM_HZ = K.PALM_HZ
CX = (K.PALM_X0 + K.PALM_X1) / 2 + 0.002  # the vent's centre on the palm
VR = 0.0205  # the vent's hex radius (corner)
HEX = [(math.cos(math.radians(60 * k + 30)), math.sin(math.radians(60 * k + 30))) for k in range(6)]


def radial(a_deg):
    a = math.radians(a_deg)
    return V((0.0, -math.sin(a), math.cos(a)))


def hexagon(name, r, depth, loc, axis="z"):
    """A six-sided cylinder (flat sides at ±Y on the Z axis)."""
    ob = hs.cyl_z(name, r, depth, loc, verts=6)
    ob.rotation_euler = (0, 0, math.radians(30))
    return ob


# ---------------------------------------------------------------- forearm and the canister of sleeping harvesters
fore = K.forearm(side=SIDE)
forearm = K.part("forearm", fore)

CA = 72.0  # the canister sits on the inner side, a little up
CX0, CX1 = -0.215, -0.035
n = radial(CA)
rc = 0.051
can = []
# A hexagonal body along the forearm, seated into it.
c0 = V((0, n.y * rc, n.z * rc))
tang = V((0, n.z, -n.y))  # across the canister face
pts = []
for k in range(6):
    a = math.radians(60 * k)
    p = c0 + n * (math.cos(a) * 0.0115) + tang * (math.sin(a) * 0.0115)
    pts.append((p.y, p.z))
can.append(K.piece(hs.section("can_body", pts, CX0, CX1), "graft", bevel=0.0009))
# End caps and a band round the middle.
for x0, x1 in ((CX0 - 0.006, CX0 + 0.004), (CX1 - 0.004, CX1 + 0.006), ((CX0 + CX1) / 2 - 0.004, (CX0 + CX1) / 2 + 0.004)):
    pts2 = []
    for k in range(6):
        a = math.radians(60 * k)
        p = c0 + n * (math.cos(a) * 0.0128) + tang * (math.sin(a) * 0.0128)
        pts2.append((p.y, p.z))
    can.append(K.piece(hs.section("can_cap", pts2, x0, x1), "gunmetal", bevel=0.0008))
# Three windows on the face toward the eye; harvesters packed nose to tail behind them, a red strip under them.
face = c0 + n * 0.0118
for w in range(3):
    wx0 = CX0 + 0.012 + w * 0.056
    wx1 = wx0 + 0.04
    if w == 1:
        wx0 += 0.008
        wx1 -= 0.002
    mid = (wx0 + wx1) / 2
    tilt = (-math.atan2(n.y, n.z), 0, 0)  # the box's thin side along n (hs.box bakes its location: rotate on creation)
    win = hs.box("window", (wx1 - wx0, 0.0125, 0.0016), (mid, face.y, face.z), rot=tilt)
    can.append(K.piece(win, "void", bevel=0.0004))
    for row in (-1, 1):
        for i in range(6):
            x = wx0 + 0.004 + i * (wx1 - wx0 - 0.008) / 5.0
            p = face + n * 0.0011 + tang * (row * 0.0032)
            d = hs.cyl_between("drone", (x - 0.0026, p.y, p.z), (x + 0.0026, p.y, p.z), 0.0013, verts=8)
            can.append(K.piece(d, "gunmetal", bevel=0.0))
            eye = hs.cyl_between("drone_eye", (x + 0.0024, p.y, p.z), (x + 0.0032, p.y, p.z), 0.0008, verts=6)
            can.append(K.piece(eye, "glow", bevel=0.0))
    strip = hs.box("strip", (wx1 - wx0 - 0.004, 0.0012, 0.0009), (mid, (face - tang * 0.0062).y, (face - tang * 0.0062).z))
    can.append(K.piece(strip, "glow", bevel=0.0))
# The feed: from the canister's wrist end under the collar into the heel of the palm.
end = c0 + n * 0.004
can.append(K.piece(hs.tube_path("feed", [(CX1 + 0.004, end.y, end.z), (CX1 + 0.018, end.y * 0.8, end.z * 0.6), (0.0, end.y * 0.6, -0.012),
                                          (0.014, end.y * 0.35, -0.016)], 0.0042), "polymer", bevel=0.0))
canister = K.part("canister", can, pivot=((CX0 + CX1) / 2, c0.y, c0.z))

# ---------------------------------------------------------------- the hand, and the hive in its palm
wrist, palm, fingers, thumb = K.hand(side=SIDE)
ZV = -PALM_HZ - 0.0012  # the palm's outer face

vent = []
# A raised gunmetal rim, then the honeycomb: a hex plate with seven bays cut through it.
rim = hexagon("vent_rim", VR + 0.0032, 0.0026, (CX, 0, ZV - 0.0004))
rim_cut = hexagon("vent_rim_cut", VR, 0.01, (CX, 0, ZV))
hs.cut(rim, rim_cut)
vent.append(K.piece(rim, "gunmetal", bevel=0.0005))
comb = hexagon("comb", VR, 0.0024, (CX, 0, ZV + 0.0004))
BAY = 0.0052
bays = [(0.0, 0.0)] + [(math.cos(math.radians(60 * k)) * BAY * 2.0, math.sin(math.radians(60 * k)) * BAY * 2.0) for k in range(6)]
for bx, by in bays:
    hs.cut(comb, hexagon("bay_cut", BAY - 0.0006, 0.01, (CX + bx, by, ZV)))
vent.append(K.piece(comb, "gunmetal", bevel=0.0003))
# Deep in each bay: the dark mouth of a docking stack and the red light behind it.
for bx, by in bays:
    vent.append(K.piece(hexagon("bay_floor", BAY - 0.0004, 0.0008, (CX + bx, by, ZV + 0.0018)), "glow", bevel=0.0))
    vent.append(K.piece(hs.cyl_z("bay_mouth", 0.0019, 0.0006, (CX + bx, by, ZV + 0.0013), verts=10), "void", bevel=0.0))

# Back of the hand: six cells in a ring round a boss, one per sixth of the swarm.
ZB = PALM_HZ + 0.0016
CBX = CX - 0.004
vent.append(K.piece(hexagon("cell_plate", 0.0185, 0.0014, (CBX, 0, ZB)), "gunmetal", bevel=0.0004))
vent.append(K.piece(hexagon("cell_boss", 0.0045, 0.0026, (CBX, 0, ZB + 0.0008)), "graft", bevel=0.0004))
for k in range(6):
    a = math.radians(60 * k + 30)
    vent.append(K.piece(hexagon(f"cell{k}", 0.0047, 0.0012, (CBX + math.cos(a) * 0.0108, math.sin(a) * 0.0108, ZB + 0.0007)), f"cell{k}", bevel=0.0002))
vent_part = K.part("vent", vent, pivot=(CX, 0, ZV))
K.parent(vent_part, palm)

# The iris: six petals, each a sixth of a hex plate hinged at its outer edge, built pointing +X from the vent's
# centre and then turned into place on its own mount (so the hinge is the mount's local Y).
petals = []
mounts = []
for k in range(6):
    R = VR + 0.0018
    a0, a1 = math.radians(-30), math.radians(30)
    outline = [(0.0012, 0.0), (R * math.cos(a0), R * math.sin(a0)), (R * math.cos(a1), R * math.sin(a1))]
    pl = K.poly_plate(f"petal{k}", outline, 0.0016, origin=(CX, 0, ZV - 0.0028), u=(1, 0, 0), v=(0, 1, 0))
    pcs = [K.piece(pl, "graft", bevel=0.0003)]
    # A lit edge along the hinge and a gunmetal knuckle.
    hx = CX + R * math.cos(a1) - 0.0008
    pcs.append(K.piece(hs.box("petal_glow", (0.0008, R * 0.85, 0.0006), (hx - 0.0028, 0, ZV - 0.0030)), "glow", bevel=0.0))
    pcs.append(K.piece(hs.cyl_y("petal_knuckle", 0.0011, R * 0.7, (hx, 0, ZV - 0.0016), verts=8), "gunmetal", bevel=0.0))
    petal = K.part(f"petal_{k}", pcs, pivot=(hx, 0, ZV - 0.0016))
    mount = K.empty(f"petal_mount_{k}", (CX, 0, ZV))
    K.parent(petal, mount)
    mount.rotation_euler = (0, 0, math.radians(60 * k))
    K.parent(mount, palm)
    petals.append(petal)
    mounts.append(mount)

# ---------------------------------------------------------------- the tree
arm = K.empty("arm", (-0.12, 0.0, 0.0))
for ob in (forearm, canister, wrist):
    K.parent(ob, arm)
root = K.empty("hv3_root")
K.parent(arm, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
for ob in (root, forearm, canister, palm, vent_part) + tuple(mounts):
    K.hold(ob, END)
# The forearm comes up rolled palm-up, holds while the iris blooms, then rolls over.
# (A left forearm supinates thumb-up through +Z: a negative roll about X here.)
K.track(arm, [(0, (0, 0, 0), (-152, 0, 0)), (9, (0, 0, 0.004), (-146, -4, 0)), (15, (0, 0, 0.0), (6, 0, 0)),
              (18, (0, 0, 0), (-3, 0, 0)), (END, (0, 0, 0), (0, 0, 0))])
# The wrist: easy while palm-up, then snapped back so the palm faces down range.
K.track(wrist, [(0, (0, 0, 0), (0, 10, 0)), (9, (0, 0, 0), (0, -6, 0)), (15, (0, 0, 0), (-4 * SIDE, -86, 0)),
                (18, (0, 0, 0), (-4 * SIDE, -74, 0)), (END, (0, 0, 0), (-4 * SIDE, -79, 0))])
# The iris: one petal after another flips out and up off the palm and locks standing round the vent.
for k, pt in enumerate(petals):
    f0 = 3 + k
    K.track(pt, [(0, (0, 0, 0), (0, 0, 0)), (f0, (0, 0, 0), (0, 0, 0)), (f0 + 4, (0.0026, 0, 0), (0, -92, 0)),
                 (f0 + 6, (0.0024, 0, 0), (0, -76, 0)), (END, (0.0024, 0, 0), (0, -80, 0))])
# Fingers: from loose to spread wide and stretched back, a hand held up to stop someone.
SPREAD = {"index": 10, "middle": 2, "ring": -6, "little": -14}
for i, (fname, segs) in enumerate(fingers.items()):
    f0 = 2 + i
    yaw = SPREAD[fname] * SIDE
    for k, seg in enumerate(segs):
        o = (10, 16, 10)[k] + i * 2
        stretch = (-14, -4, -2)[k]
        z = yaw if k == 0 else 0
        K.track(seg, [(0, (0, 0, 0), (0, o, 0)), (f0, (0, 0, 0), (0, o, 0)), (f0 + 6, (0, 0, 0), (0, stretch - 4, z * 1.25)),
                      (f0 + 9, (0, 0, 0), (0, stretch, z)), (END, (0, 0, 0), (0, stretch, z))])
# The thumb opens out in the plane of the palm.
K.track(thumb[0], [(0, (0, 0, 0), (0, 0, 0)), (2, (0, 0, 0), (0, 0, 0)), (10, (0, 0, 0), (8, -12, 16)), (END, (0, 0, 0), (8, -12, 16))])
K.track(thumb[1], [(0, (0, 0, 0), (0, 10, 0)), (10, (0, 0, 0), (0, -4, 0)), (END, (0, 0, 0), (0, -4, 0))])
K.track(thumb[2], [(0, (0, 0, 0), (0, 8, 0)), (10, (0, 0, 0), (0, -2, 0)), (END, (0, 0, 0), (0, -2, 0))])

VIEWS = {
    # The player's eye: behind, above and right of the left forearm.
    "fp": ((-0.5, -0.22, 0.2), (0.6, 0.08, 0.02), 62),
    # Close on the palm while it is turned up.
    "palm": ((0.1, -0.16, 0.2), (0.0, 0.0, 0.0), 0),
    "hero": ((0.24, -0.26, 0.12), (-0.02, 0.0, 0.03), 0),
}
K.finish([root], END, VIEWS)
