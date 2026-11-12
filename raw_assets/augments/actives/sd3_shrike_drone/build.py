"""SD-3 Shrike: the shoulder-launched suicide drone (owner, docs/design.md §3.4: "A pod on your shoulder opens
and launches the drone. You fly it from its camera and detonate it.").

Design (hardware, no magic): a tube-launched quadcopter munition the size of a forearm. An octagonal carbon
fuselage; a shaped-charge warhead in the nose (olive drab, a hazard band, a copper liner showing at the tip,
four contact fuze whiskers); the camera ball slung under the nose; a battery and the link antenna in the tail.
Four arms fold back flat along the fuselage to fit the launch tube and swing out to an X when it leaves; each
ends in a shrouded rotor. Status light strips along the spine (the game leaves `glow` as built).

Unfold clip (60 fps, frames 0-24 = 0.4 s; the game scrubs it while the drone flies out of the pod):
   0-14  the four arms swing out from along the fuselage to the X (front pair first), overshoot and lock
  10-22  the fuze whiskers spring out; the antenna stands up
  the rotors spin up over the whole clip

Parts (glTF nodes): body (static), arm_1..4 > prop_1..4, whisker_1..4, antenna. Materials: carbon, olive,
hazard, copper, steel, gunmetal, lens, glow.

Axes: built nose toward +Y (Blender), so in Godot the nose points along -Z, the way a camera looks. +Z up.

Run:
  tools/blender.sh raw_assets/augments/actives/sd3_shrike_drone/build.py \
      --out assets/augments/sd3_shrike_drone/sd3_shrike_drone.gltf --preview docs/previews/sd3_shrike_drone.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _kit as K  # noqa: E402
from _kit import V, hs  # noqa: E402
from mathutils import Matrix  # noqa: E402

END = 24
args = K.init("sd3", END, "0,8,16,24")
K.mat("carbon", (0.02, 0.021, 0.024), 0.4, 0.0, coat=0.3)
K.mat("olive", (0.13, 0.15, 0.08), 0.6, 0.0)
K.mat("hazard", (0.85, 0.62, 0.05), 0.5, 0.0)
K.mat("lens", (0.01, 0.01, 0.02), 0.05, 1.0)
ROT = Matrix.Rotation(math.pi / 2, 4, "Z")   # the kit builds along +X; the drone flies along +Y


def turn(ob):
    ob.data.transform(ROT)
    return ob


# ---------------------------------------------------------------- fuselage (built along +X, then turned)
bp = [K.piece(turn(hs.lathe_x("fuselage", [(-0.12, 0.0), (-0.12, 0.022), (-0.105, 0.03), (0.04, 0.03), (0.055, 0.027), (0.055, 0.0)], verts=8)), "carbon", bevel=0.0016),
      K.piece(turn(hs.lathe_x("warhead", [(0.055, 0.0), (0.055, 0.0275), (0.095, 0.0275), (0.125, 0.017), (0.132, 0.0)], verts=20)), "olive", bevel=0.0008),
      K.piece(turn(K.ring("band", 0.066, 0.076, 0.0283, 0.02, verts=20)), "hazard", bevel=0.0),
      K.piece(turn(hs.lathe_x("liner", [(0.13, 0.0), (0.13, 0.011), (0.138, 0.006), (0.14, 0.0)], verts=14)), "copper", bevel=0.0),
      K.piece(turn(hs.box("battery", (0.07, 0.04, 0.018), (-0.07, 0.0, 0.033))), "gunmetal", bevel=0.002),
      K.piece(turn(hs.box("spine_glow", (0.09, 0.003, 0.0016), (-0.01, 0.0, 0.0307))), "glow", bevel=0.0),
      K.piece(turn(hs.box("tail_glow", (0.0016, 0.03, 0.008), (-0.1205, 0.0, 0.0))), "glow", bevel=0.0),
      K.piece(turn(hs.cyl_between("cam_stalk", (0.03, 0.0, -0.028), (0.04, 0.0, -0.04), 0.007, verts=10)), "gunmetal", bevel=0.0006)]
ball = K.piece(turn(hs.lathe_x("cam_ball", [(0.026, 0.0), (0.03, 0.012), (0.042, 0.016), (0.054, 0.012), (0.058, 0.0)], verts=14)), "gunmetal", bevel=0.0)
ball.data.transform(Matrix.Translation((0.0, 0.0, -0.046)))
bp.append(ball)
eye = K.piece(turn(hs.cyl_x("cam_eye", 0.0075, 0.054, 0.06, verts=14, z=-0.046)), "lens", bevel=0.0006)
bp.append(eye)
body = K.part("body", bp)

# ---------------------------------------------------------------- arms and rotors
ARM_L = 0.135
arms, props = [], []
# (pivot x, pivot y, folded yaw deg, deployed yaw deg): yaw measured from +X about +Z.
SPEC = [(0.028, 0.045, 270, 35), (-0.028, 0.045, 270, 145), (0.028, -0.075, 270, -35), (-0.028, -0.075, 270, -145)]
for k, (px, py, fold, out) in enumerate(SPEC):
    # Built pointing along +X from the pivot.
    ap = [K.piece(hs.box("boom", (ARM_L, 0.012, 0.008), (ARM_L / 2, 0.0, 0.0)), "carbon", bevel=0.0016),
          K.piece(hs.cyl_z("pivot", 0.011, 0.016, (0.0, 0.0, 0.0), verts=14), "gunmetal", bevel=0.001),
          K.piece(hs.cyl_z("motor", 0.012, 0.02, (ARM_L, 0.0, 0.004), verts=14), "gunmetal", bevel=0.001)]
    # Shroud: a thin ring round the rotor.
    sh = K.ring("shroud", -0.006, 0.006, 0.052, 0.049, verts=24)
    sh.data.transform(Matrix.Translation((ARM_L, 0.0, 0.012)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    ap.append(K.piece(sh, "carbon", bevel=0.0))
    for a in (0, 120, 240):
        ap.append(K.piece(hs.cyl_between("stay", (ARM_L, 0.0, 0.006), (ARM_L + 0.05 * math.cos(math.radians(a)), 0.05 * math.sin(math.radians(a)), 0.01), 0.0018, verts=6), "gunmetal", bevel=0.0))
    arm = K.part(f"arm_{k + 1}", ap, pivot=(0.0, 0.0, 0.0))
    pr = [K.piece(hs.box("blade", (0.092, 0.011, 0.0016), (ARM_L, 0.0, 0.017), rot=(math.radians(8), 0, 0)), "carbon", bevel=0.0004),
          K.piece(hs.cyl_z("hub", 0.006, 0.008, (ARM_L, 0.0, 0.018), verts=10), "steel", bevel=0.0006)]
    prop = K.part(f"prop_{k + 1}", pr, pivot=(ARM_L, 0.0, 0.017))
    K.parent(prop, arm)
    arm.location = (px, py, 0.012 if k < 2 else 0.0)
    arm.rotation_euler = (0.0, 0.0, math.radians(fold))
    arms.append((arm, fold, out))
    props.append(prop)

whiskers = []
for k in range(4):
    a = math.radians(45 + k * 90)
    c, s = math.cos(a), math.sin(a)
    w = K.part(f"whisker_{k + 1}", [K.piece(hs.cyl_between("w", (0.02 * c, 0.1, 0.02 * s), (0.024 * c, 0.15, 0.024 * s), 0.0012, verts=6), "steel", bevel=0.0)],
               pivot=(0.02 * c, 0.1, 0.02 * s))
    whiskers.append((w, c, s))
antenna = K.part("antenna", [K.piece(hs.cyl_between("mast", (0.0, -0.105, 0.03), (0.0, -0.105, 0.11), 0.0016, verts=6), "steel", bevel=0.0),
                              K.piece(hs.cyl_z("ant_base", 0.005, 0.008, (0.0, -0.105, 0.034), verts=10), "gunmetal", bevel=0.0006)], pivot=(0.0, -0.105, 0.03))

root = K.empty("sd3_root")
for ob in [body, antenna] + [a for a, _f, _o in arms] + [w for w, _c, _s in whiskers]:
    K.parent(ob, root)

# ---------------------------------------------------------------- animation
K.capture_rest()
K.hold(body, END)
K.hold(root, END)
for k, (arm, fold, out) in enumerate(arms):
    d = out - fold
    # The short way round.
    while d > 180:
        d -= 360
    while d < -180:
        d += 360
    f0 = 0 if k < 2 else 3
    K.track(arm, [(0, (0, 0, 0), (0, 0, 0)), (f0, (0, 0, 0), (0, 0, 0)), (f0 + 9, (0, 0, 0), (0, 0, d * 1.08)), (f0 + 12, (0, 0, 0), (0, 0, d)), (END, (0, 0, 0), (0, 0, d))])
for k, prop in enumerate(props):
    K.track(prop, [(0, (0, 0, 0), (0, 0, 0)), (8, (0, 0, 0), (0, 0, 90 * (1 if k % 2 else -1))), (END, (0, 0, 0), (0, 0, 1500 * (1 if k % 2 else -1)))])
for w, c, s in whiskers:
    # Folded back along the warhead; they spring out and forward.
    K.track(w, [(0, (0, 0, 0), (-s * 150, 0, c * 150)), (10, (0, 0, 0), (-s * 150, 0, c * 150)), (19, (0, 0, 0), (s * 14, 0, -c * 14)), (22, (0, 0, 0), (0, 0, 0)), (END, (0, 0, 0), (0, 0, 0))])
K.track(antenna, [(0, (0, 0, 0), (88, 0, 0)), (12, (0, 0, 0), (88, 0, 0)), (20, (0, 0, 0), (-8, 0, 0)), (22, (0, 0, 0), (0, 0, 0)), (END, (0, 0, 0), (0, 0, 0))])

VIEWS = {
    "fp": ((0.0, -0.06, 0.085), (0.0, 1.0, -0.1), 84),
    "hero": ((0.34, 0.3, 0.2), (0.0, 0.0, 0.0), 0),
}
K.finish([root], END, VIEWS)
