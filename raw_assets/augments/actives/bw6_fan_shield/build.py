"""BW-6 Bulwark Fan Shield: the first-person left arm with the shield (2026-11-10; docs/design.md §3.4).

Design (hardware, no magic): seven boron-carbide leaves on one hub on the outer side of the left forearm.
Folded, they lie stacked along the forearm and past the fist like the blade of a tonfa. A torsion motor in the
hub throws them round into a fan: half a disc 0.4 m in radius above and either side of the forearm, each leaf
latching to the next. The operative holds the forearm across his chest and looks over the top edge. Leaves are
satin black graft ceramic with a lit seam along the rim and a row of latch studs; the hub is gunmetal with a
light ring that shows how much the shield has left (the game drives `glow`).

The camera looks at the inner faces (the side toward the body), with the forearm and fist in front of them.

Deploy clip (60 fps, frames 0-30 = 0.5 s; the game raises the arm into view over the first third):
   0-10  the fist closes
   4-26  the leaves swing round the hub one after another (the last one first), each overshooting and latching
   0-26  the hub turns

Parts (glTF nodes): forearm (static: sleeve, plates, hub mount), hub (turns), leaf_1..7, wrist > palm > fingers.
Materials: graft, weave, polymer, gunmetal (suit colours), steel, glow.

Axes: left arm, +Y is the outer side. The hub's axis is Y; the fan lies in the XZ plane.

Run:
  tools/blender.sh raw_assets/augments/actives/bw6_fan_shield/build.py \
      --out assets/augments/bw6_fan_shield/bw6_fan_shield.gltf --preview docs/previews/bw6_fan_shield.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

END = 30
args = K.init("bw6", END, "0,10,20,30")

HUB = V((-0.15, 0.058, 0.0))
R = 0.40
LEAVES = 7
STEP = 30.0   # degrees between leaves, fanned from 0 (along +X) to 180

fore = K.forearm(side=-1)
# Hub mount: a bracket from the forearm's outer plate.
fore.append(K.piece(hs.box("mount", (0.11, 0.016, 0.05), (HUB.x, 0.05, 0.0)), "gunmetal", bevel=0.003))
for dx in (-0.04, 0.04):
    fore.append(K.piece(hs.cyl_y("mount_bolt", 0.005, 0.02, (HUB.x + dx, 0.052, 0.016), verts=10), "steel", bevel=0.0006))
    fore.append(K.piece(hs.cyl_y("mount_bolt", 0.005, 0.02, (HUB.x + dx, 0.052, -0.016), verts=10), "steel", bevel=0.0006))
forearm = K.part("forearm", fore)

hub_p = [K.piece(hs.cyl_y("hub_drum", 0.034, 0.05, (HUB.x, HUB.y + 0.022, 0.0), verts=32), "gunmetal", bevel=0.0016),
         K.piece(hs.cyl_y("hub_cap", 0.026, 0.006, (HUB.x, HUB.y - 0.004, 0.0), verts=32), "graft", bevel=0.001),
         K.piece(hs.cyl_y("hub_ring", 0.031, 0.0016, (HUB.x, HUB.y - 0.0062, 0.0), verts=32), "glow", bevel=0.0)]
for k in range(6):
    a = k * math.pi / 3
    hub_p.append(K.piece(hs.cyl_y("hub_stud", 0.0035, 0.01, (HUB.x + 0.018 * math.cos(a), HUB.y - 0.006, 0.018 * math.sin(a)), verts=8), "steel", bevel=0.0004))
hub = K.part("hub", hub_p, pivot=(HUB.x, HUB.y, 0.0))

# One leaf: a tapered blade from the hub out to the rim, pointing along +X when folded.
half = math.radians(STEP * 0.5 + 2.5)
leaves = []
for i in range(LEAVES):
    y = HUB.y + 0.004 + i * 0.0048
    r0, r1 = 0.03, R - i * 0.004
    w0, w1 = r0 * math.tan(half) + 0.006, r1 * math.tan(half)
    pts = [(r0, -w0), (r1 * 0.9, -w1 * 0.92), (r1, -w1 * 0.55), (r1 + 0.012, 0.0), (r1, w1 * 0.55), (r1 * 0.9, w1 * 0.92), (r0, w0)]
    pcs = [K.piece(K.poly_plate("leaf", pts, 0.004, origin=(HUB.x, y, 0.0), u=(1, 0, 0), v=(0, 0, 1)), "graft", bevel=0.0012)]
    # Lit seam along the rim and a spine rib (on the inner face, toward the camera).
    rim = [(r1 * 0.9, -w1 * 0.8), (r1 * 0.985, -w1 * 0.5), (r1 * 0.995, 0.0), (r1 * 0.985, w1 * 0.5), (r1 * 0.9, w1 * 0.8),
           (r1 * 0.885, w1 * 0.78), (r1 * 0.97, w1 * 0.48), (r1 * 0.98, 0.0), (r1 * 0.97, -w1 * 0.48), (r1 * 0.885, -w1 * 0.78)]
    pcs.append(K.piece(K.poly_plate("rim", rim, 0.0052, origin=(HUB.x, y - 0.0006, 0.0), u=(1, 0, 0), v=(0, 0, 1)), "glow", bevel=0.0))
    pcs.append(K.piece(hs.box("rib", (r1 * 0.7, 0.003, 0.012), (HUB.x + r0 + r1 * 0.38, y - 0.0052, 0.0)), "gunmetal", bevel=0.001))
    for t in (0.35, 0.55, 0.75):
        pcs.append(K.piece(hs.cyl_y("stud", 0.0045, 0.004, (HUB.x + r1 * t, y - 0.005, w1 * t * 0.62), verts=8), "steel", bevel=0.0004))
        pcs.append(K.piece(hs.cyl_y("stud", 0.0045, 0.004, (HUB.x + r1 * t, y - 0.005, -w1 * t * 0.62), verts=8), "steel", bevel=0.0004))
    leaves.append(K.part(f"leaf_{i + 1}", pcs, pivot=(HUB.x, y, 0.0)))

wrist, palm, fingers, thumb = K.hand(side=-1)
root = K.empty("bw6_root")
for ob in [forearm, hub, wrist] + leaves:
    K.parent(ob, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
K.hold(forearm, END)
K.hold(root, END)
K.hold(palm, END)
K.curl(fingers, thumb, 0, 8, END, stagger=1)
K.track(wrist, [(0, (0, 0, 0), (0, 0, 0)), (10, (0, 0, 0), (0, 8, 0)), (END, (0, 0, 0), (0, 8, 0))])
K.track(hub, [(0, (0, 0, 0), (0, 0, 0)), (26, (0, 0, 0), (0, -200, 0)), (END, (0, 0, 0), (0, -180, 0))])
for i, ob in enumerate(leaves):
    # Rotating about +Y by a negative angle swings +X up toward +Z.
    ang = -STEP * i
    f0 = 4 + (LEAVES - 1 - i) * 1.5
    f1 = f0 + 8 + i * 1.2
    K.track(ob, [(0, (0, 0, 0), (0, 0, 0)), (int(f0), (0, 0, 0), (0, 0, 0)), (int(f1), (0, 0, 0), (0, ang * 1.07, 0)),
                 (int(f1) + 3, (0, 0, 0), (0, ang, 0)), (END, (0, 0, 0), (0, ang, 0))])

VIEWS = {
    # The player's eye: behind the forearm (the body side, -Y), looking out through the shield plane.
    "fp": ((0.02, -0.5, 0.3), (0.02, 0.5, 0.12), 70),
    "hero": ((0.25, 0.75, 0.35), (-0.12, 0.0, 0.12), 0),
}
K.finish([root], END, VIEWS)
