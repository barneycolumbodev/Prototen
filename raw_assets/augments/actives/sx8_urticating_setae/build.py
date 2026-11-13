"""SX-8 Urticating Setae: the first-person left arm (owner, 2026-11-13: "a nanotech augmentation... a series of
vents on the side of the arm, little holes that are normally empty. When you activate it the guy brings his arm
forward and out of those holes long, very thin, razor-sharp hairs grow out"; docs/design.md §3.4c).

Design (hardware, no magic): a setae bank grafted along the back of the left forearm. It is a machined housing
with three rows of eight ports (24): each port is a ceramic collar round a bore that runs down into a nanite
assembler under the plate. Two feed lines carry feedstock (a carbon-boron slurry) back into the elbow sleeve.
When the bank fires, the assemblers extrude a pair of fibres out of each bore: long, hair-thin, flexible while
they grow, then stiffened into needles by a phase change in flight (the game draws the hairs: `port_00` ..
`port_23` mark the bores). Two gill plates either side of the bank lift to vent the assembler heat.

Deploy clip (60 fps, frames 0-30 = 0.5 s; the game raises the arm into view over the first third):
   0-14  the hand opens: fingers spread wide and hook into a claw, the wrist bends back
   4-16  the two gill plates lift and flare
  10-24  the bank rises a couple of millimetres off its seat (the bores clear the plate)

Parts (glTF nodes): forearm (static: suit forearm, feed lines), bank (housing, port collars, bores; the
port_NN empties ride on it), gill_in, gill_out, wrist > palm > fingers, thumb. Materials: weave, graft, polymer,
gunmetal (suit colours), ceramic, void (the bores), glow (the game drives it).

Run:
  tools/blender.sh raw_assets/augments/actives/sx8_urticating_setae/build.py \
      --out assets/augments/sx8_urticating_setae/sx8_urticating_setae.gltf --preview docs/previews/sx8_urticating_setae.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

END = 30
args = K.init("sx8", END, "0,10,20,30")
K.mat("ceramic", (0.78, 0.74, 0.66), 0.38, 0.0)
K.mat("void", (0.004, 0.004, 0.005), 0.9, 0.0)
K.mat("glow", (0.12, 0.05, 0.02), 0.3, 0.0, emission=((1.0, 0.45, 0.14), 2.5))

SIDE = -1  # left arm: +Y is the outer side
BX0, BX1 = -0.245, -0.05  # the bank, elbow end to wrist end
ROWS = (-30.0, -6.0, 18.0)  # angle from the top toward -Y (the inner side, toward the eye)
PER_ROW = 8


def radial(a_deg):
    a = math.radians(a_deg)
    return V((0.0, -math.sin(a), math.cos(a)))


# ---------------------------------------------------------------- forearm (no top plate: the bank sits there)
fore = K.forearm(side=SIDE, top_gap=True)
# Feed lines from the bank's elbow end into the sleeve.
for dy in (0.012, -0.014):
    fore.append(K.piece(hs.tube_path("feed", [(BX0 + 0.004, dy, 0.05), (BX0 - 0.03, dy * 1.2, 0.054), (-0.31, dy * 1.4, 0.055), (-0.35, dy * 1.2, 0.05)], 0.0032), "polymer", bevel=0.0))
fore.append(K.piece(K.ring("feed_clamp", BX0 - 0.034, BX0 - 0.022, 0.058, 0.05), "gunmetal", bevel=0.001))
forearm = K.part("forearm", fore)

# ---------------------------------------------------------------- the bank
bank_pcs = []
r0, r1 = K.r_at(BX0) + 0.0035, K.r_at(BX1) + 0.0035
bank_pcs.append(K.piece(K.shell("housing", BX0, BX1, r0 + 0.006, r1 + 0.006, -46, 34, 0.0085, seg=6), "gunmetal", bevel=0.0012))
# End caps: a chamfered lip at each end.
bank_pcs.append(K.piece(K.shell("cap_e", BX0 - 0.006, BX0 + 0.004, r0 + 0.004, r0 + 0.0065, -48, 36, 0.011, seg=6), "graft", bevel=0.001))
bank_pcs.append(K.piece(K.shell("cap_w", BX1 - 0.004, BX1 + 0.006, r1 + 0.0065, r1 + 0.004, -48, 36, 0.011, seg=6), "graft", bevel=0.001))
# Thin lit seams between the rows.
for a in (-18.0, 6.0):
    n = radial(a)
    for x0, x1 in ((BX0 + 0.008, BX1 - 0.008),):
        mid = (x0 + x1) / 2
        rr = K.r_at(mid) + 0.0035 + 0.0062
        bank_pcs.append(K.piece(hs.box("seam", (x1 - x0, 0.0012, 0.0008), (mid, n.y * rr, n.z * rr)), "glow", bevel=0.0))
ports = []
for ri, a in enumerate(ROWS):
    n = radial(a)
    for k in range(PER_ROW):
        # Staggered rows, like spiracles.
        t = (k + (0.5 if ri == 1 else 0.0)) / (PER_ROW - 0.5)
        x = BX0 + 0.014 + (BX1 - BX0 - 0.028) * t
        rr = K.r_at(x) + 0.0035 + 0.006
        base = V((x, 0, 0)) + n * (rr - 0.004)
        top = V((x, 0, 0)) + n * (rr + 0.0022)
        bank_pcs.append(K.piece(hs.cyl_between("collar", tuple(base), tuple(top), 0.0042, verts=14), "ceramic", bevel=0.0004))
        bank_pcs.append(K.piece(hs.cyl_between("bore", tuple(base + n * 0.002), tuple(top + n * 0.0003), 0.0026, verts=12), "void", bevel=0.0))
        bank_pcs.append(K.piece(hs.cyl_between("bore_glow", tuple(top - n * 0.0016), tuple(top - n * 0.0010), 0.0028, verts=12), "glow", bevel=0.0))
        ports.append(top + n * 0.0004)
bank = K.part("bank", bank_pcs, pivot=((BX0 + BX1) / 2, 0.0, K.r_at((BX0 + BX1) / 2)))
port_empties = []
for i, p in enumerate(ports):
    e = K.empty(f"port_{i:02d}", tuple(p))
    K.parent(e, bank)
    port_empties.append(e)

# ---------------------------------------------------------------- gill plates either side of the bank
gills = {}
for s, name, a0, a1 in ((1, "gill_in", 36, 64), (-1, "gill_out", -76, -48)):
    g = [K.piece(K.shell(name, BX0 + 0.02, BX1 - 0.02, K.r_at(BX0 + 0.02) + 0.0045, K.r_at(BX1 - 0.02) + 0.0045, a0, a1, 0.0035, seg=2), "graft", bevel=0.0008)]
    edge = a0 if s > 0 else a1
    n = radial(edge)
    mid = (BX0 + BX1) / 2
    rr = K.r_at(mid) + 0.0065
    g.append(K.piece(hs.box("gill_glow", (BX1 - BX0 - 0.06, 0.0012, 0.0012), (mid, n.y * rr, n.z * rr)), "glow", bevel=0.0))
    hinge = radial(a1 if s > 0 else a0) * (K.r_at(mid) + 0.004)
    gills[s] = K.part(name, g, pivot=(mid, hinge.y, hinge.z))

# ---------------------------------------------------------------- the hand
wrist, palm, fingers, thumb = K.hand(side=SIDE)

root = K.empty("sx8_root")
for ob in (forearm, bank, gills[1], gills[-1], wrist):
    K.parent(ob, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
K.hold(root, END)
K.hold(forearm, END)
K.hold(palm, END)
for e in port_empties:
    K.hold(e, END)
# Wrist: from relaxed to bent back and turned a little out (the back of the forearm toward the view).
K.track(wrist, [(0, (0, 0, 0), (0, 8, 0)), (4, (0, 0, 0), (0, 6, 0)), (14, (0, 0, 0), (-6, -22, 0)), (18, (0, 0, 0), (-5, -18, 0)), (END, (0, 0, 0), (-5, -18, 0))])
# Fingers: a spread, hooked claw.
SPREAD = {"index": 9, "middle": 2, "ring": -5, "little": -12}
for i, (fname, segs) in enumerate(fingers.items()):
    f0 = 1 + i
    yaw = SPREAD[fname] * SIDE
    hook = (22, 48, 38)
    for k, seg in enumerate(segs):
        o = (8, 12, 8)[k] + i * 2
        z = yaw if k == 0 else 0
        K.track(seg, [(0, (0, 0, 0), (0, o, 0)), (f0, (0, 0, 0), (0, o, 0)), (f0 + 7, (0, 0, 0), (0, -6 if k == 0 else 4, z * 1.2)),
                      (f0 + 13, (0, 0, 0), (0, hook[k] - (14 if k == 0 else 0), z)), (END, (0, 0, 0), (0, hook[k] - (14 if k == 0 else 0), z))])
K.track(thumb[0], [(0, (0, 0, 0), (0, 0, 0)), (2, (0, 0, 0), (0, 0, 0)), (12, (0, 0, 0), (-10 * SIDE, -10, 22 * SIDE)), (END, (0, 0, 0), (-10 * SIDE, -10, 22 * SIDE))])
K.track(thumb[1], [(0, (0, 0, 0), (0, 10, 0)), (12, (0, 0, 0), (0, 26, 0)), (END, (0, 0, 0), (0, 26, 0))])
K.track(thumb[2], [(0, (0, 0, 0), (0, 8, 0)), (12, (0, 0, 0), (0, 30, 0)), (END, (0, 0, 0), (0, 30, 0))])
for s in (1, -1):
    K.track(gills[s], [(0, (0, 0, 0), (0, 0, 0)), (4, (0, 0, 0), (0, 0, 0)), (13, (0, 0, 0), (-s * 34, 0, 0)), (16, (0, 0, 0), (-s * 28, 0, 0)), (END, (0, 0, 0), (-s * 28, 0, 0))])
lift = radial(-6.0) * 0.0024
K.track(bank, [(0, (0, 0, 0), (0, 0, 0)), (10, (0, 0, 0), (0, 0, 0)), (20, tuple(lift * 1.3), (0, 0, 0)), (24, tuple(lift), (0, 0, 0)), (END, tuple(lift), (0, 0, 0))])

VIEWS = {
    # The player's eye: behind, above and right of the left forearm.
    "fp": ((-0.46, -0.2, 0.2), (0.6, 0.06, -0.06), 62),
    "hero": ((0.12, -0.3, 0.28), (-0.12, 0.0, 0.02), 0),
}
K.finish([root], END, VIEWS)
