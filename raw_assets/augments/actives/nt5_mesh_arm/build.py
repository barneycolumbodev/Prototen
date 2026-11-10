"""NT-5 Prehensile Mesh Arm: the first-person left arm (owner, 2026-11-10: "ultra prehensile nanotech mesh arm
thing that grabs and can throw enemies"; docs/design.md §3.4).

Design (hardware, no magic): the left forearm isn't a limb with bones, it's a braid: twelve strands of
carbon-nanotube muscle mesh wound round a core, each a bundle of electroactive fibres that contracts when
driven. Braided tight it's an arm with a five-fingered hand (each finger a strand's end). Unbraided, the strands
slide past each other and the whole thing pays out as one long tendril with a four-fingered claw on the end
(the game draws the tendril and the claw: `tendril_root` marks where it leaves the wrist). Three thin graft
plates clamp the braid along the forearm and let go when it deploys; a gunmetal driver collar at the elbow and
a slip ring at the wrist carry the drive current (lit seams between the strands).

Deploy clip (60 fps, frames 0-42 = 0.7 s; the game raises the arm into view over the first third):
   0-12  the hand opens flat, fingers together
   8-22  the three clamp plates lift off the braid and swing back toward the elbow
  14-32  the braid loosens (swells) and turns; the lit strands brighten
  20-40  the fingers draw together into one strand and withdraw into the wrist ring (the claw takes over)

Parts (glTF nodes): elbow (static: sleeve, driver collar), braid (the strands: swells and turns), plate_1..3,
slip_ring, tendril_root, hand (the five strand fingers: withdraws). Materials: weave, graft, gunmetal (suit
colours), mesh (the strands), glow (the game drives it).

Run:
  tools/blender.sh raw_assets/augments/actives/nt5_mesh_arm/build.py \
      --out assets/augments/nt5_mesh_arm/nt5_mesh_arm.gltf --preview docs/previews/nt5_mesh_arm.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402

END = 42
args = K.init("nt5", END, "0,14,28,42")
K.mat("mesh", (0.028, 0.03, 0.034), 0.42, 0.55)

X0, X1 = K.X_ELBOW, -0.02

# ---------------------------------------------------------------- elbow: sleeve and driver collar
el = [K.piece(hs.lathe_x("sleeve_m", [(-0.47, 0.0), (-0.47, 0.056), (-0.40, 0.057), (-0.33, 0.055), (-0.30, 0.053), (-0.30, 0.0)], verts=28), "weave", bevel=0.0),
      K.piece(K.ring("driver", -0.305, -0.272, 0.058, 0.03), "gunmetal", bevel=0.0014),
      K.piece(K.ring("driver_glow", -0.2735, -0.2715, 0.0545, 0.05), "glow", bevel=0.0)]
for k in range(8):
    a = k * math.pi / 4
    el.append(K.piece(hs.cyl_x("drv_bolt", 0.0035, -0.307, -0.27, verts=10, y=math.cos(a) * 0.052, z=math.sin(a) * 0.052), "graft", bevel=0.0004))
elbow = K.part("elbow", el)

# ---------------------------------------------------------------- the braid
strands = []
N = 12
for k in range(N):
    turns = 1.6 if k % 2 == 0 else -1.6
    ph = k * 2 * math.pi / N
    ob = K.helix(f"strand{k}", X0 + 0.012, X1, 0.037, 0.03, turns, ph, 0.0085, steps=26, sides=6)
    strands.append(K.piece(ob, "mesh", bevel=0.0, smooth=True))
for k in range(4):
    ob = K.helix(f"lit{k}", X0 + 0.012, X1, 0.0335, 0.027, 1.6, k * math.pi / 2 + 0.26, 0.0028, steps=26, sides=4)
    strands.append(K.piece(ob, "glow", bevel=0.0))
strands.append(K.piece(hs.lathe_x("braid_core", [(X0, 0.0), (X0, 0.03), (X1, 0.024), (X1, 0.0)], verts=20), "weave", bevel=0.0))
braid = K.part("braid", strands, pivot=(X0, 0.0, 0.0))

plates = []
for k, (a0, a1) in enumerate(((-50, 50), (70, 170), (190, 290))):
    p = [K.piece(K.shell(f"clamp{k}", -0.25, -0.07, 0.049, 0.044, a0, a1, 0.0045, seg=3), "graft", bevel=0.0008)]
    am = math.radians((a0 + a1) / 2)
    y, z = -math.sin(am), math.cos(am)
    p.append(K.piece(hs.box("clamp_glow", (0.13, 0.0014, 0.0014), (-0.16, y * 0.0495, z * 0.0495)), "glow", bevel=0.0))
    ob = K.part(f"plate_{k + 1}", p, pivot=(-0.25, y * 0.046, z * 0.046))
    plates.append((ob, y, z))

slip = K.part("slip_ring", [K.piece(K.ring("slip", X1 - 0.008, X1 + 0.012, 0.039, 0.019), "gunmetal", bevel=0.0012),
                              K.piece(K.ring("slip_glow", X1 + 0.012, X1 + 0.0135, 0.034, 0.021), "glow", bevel=0.0)])
troot = K.empty("tendril_root", (X1 + 0.02, 0.0, 0.0))

# ---------------------------------------------------------------- the hand: five strand fingers
fs = []
SPEC = [(0.032, 0.004, 0.115, 0.0075), (0.011, 0.006, 0.125, 0.008), (-0.011, 0.005, 0.118, 0.0078), (-0.031, 0.001, 0.098, 0.007)]
for y, z, L, r in SPEC:
    pts = [(X1 + 0.005, y * 0.45, z * 0.3), (0.03, y * 0.8, z), (0.07, y, z + 0.002), (0.07 + L * 0.5, y * 1.04, z - 0.004), (0.07 + L, y * 1.06, z - 0.016)]
    fine = [tuple(V(pts[i]).lerp(V(pts[i + 1]), t)) for i in range(len(pts) - 1) for t in (0.0, 0.5)] + [pts[-1]]
    fs.append(K.piece(K.tube("finger", fine, r, 8, radius_end=r * 0.7), "mesh", bevel=0.0))
    fs.append(K.piece(K.tube("finger_lit", [(p[0], p[1], p[2] + r * 0.8) for p in fine[2:]], 0.0016, 4), "glow", bevel=0.0))
# Thumb on the inner side (left arm: the inner side is -Y).
tp = [(X1 + 0.008, -0.012, -0.004), (0.02, -0.035, -0.008), (0.05, -0.052, -0.012), (0.085, -0.058, -0.02)]
fs.append(K.piece(K.tube("thumb", tp, 0.0085, 8, radius_end=0.006), "mesh", bevel=0.0))
# The palm: the strands lying side by side.
fs.append(K.piece(hs.box("palm", (0.06, 0.07, 0.022), (0.035, 0.0, 0.002)), "mesh", bevel=0.006, segments=3))
hand = K.part("hand", fs, pivot=(X1 + 0.012, 0.0, 0.0))

root = K.empty("nt5_root")
for ob in (elbow, braid, slip, troot, hand):
    K.parent(ob, root)
for ob, _y, _z in plates:
    K.parent(ob, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
K.hold(elbow, END)
K.hold(slip, END)
K.hold(troot, END)
K.hold(root, END)
for i, (ob, y, z) in enumerate(plates):
    f0 = 8 + i * 2
    out = V((0, y, z)) * 0.02
    K.track(ob, [(0, (0, 0, 0), (0, 0, 0)), (f0, (0, 0, 0), (0, 0, 0)), (f0 + 8, tuple(out), (0, 0, 0)),
                 (f0 + 14, (-0.045 + out.x, out.y * 1.3, out.z * 1.3), (0, 0, 0)), (END, (-0.045, out.y * 1.3, out.z * 1.3), (0, 0, 0))])
K.track(braid, [(0, (0, 0, 0), (0, 0, 0), 1.0), (14, (0, 0, 0), (0, 0, 0), 1.0), (30, (0, 0, 0), (55, 0, 0), (1.0, 1.2, 1.2)),
                (34, (0, 0, 0), (48, 0, 0), (1.0, 1.14, 1.14)), (END, (0, 0, 0), (48, 0, 0), (1.0, 1.14, 1.14))])
K.track(hand, [(0, (0, 0, 0), (0, 14, 0), 1.0), (12, (0, 0, 0), (0, 0, 0), 1.0), (20, (0, 0, 0), (0, 0, 0), 1.0),
               (32, (0, 0, 0), (60, 0, 0), (0.7, 0.35, 0.5)), (40, (-0.01, 0, 0), (120, 0, 0), (0.05, 0.1, 0.1)), (END, (-0.01, 0, 0), (120, 0, 0), (0.02, 0.05, 0.05))])

VIEWS = {
    # The player's eye: behind, above and right of the left forearm.
    "fp": ((-0.46, -0.2, 0.2), (0.6, 0.06, -0.06), 62),
    "hero": ((0.34, 0.36, 0.24), (-0.05, 0.0, 0.0), 0),
}
K.finish([root], END, VIEWS)
