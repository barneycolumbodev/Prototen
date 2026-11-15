"""The operative's hands for the boss execution (docs/design.md §8.7b): first person, static.

- `fist_r`: the right forearm and a clenched fist (thumb locked over the index and middle fingers). It drives
  the punches; empty `knuckles` marks the striking face (blood builds up from there, the impacts happen there).
- `grip_l`: the left forearm and a hand hooked into a claw, for holding the kneeling man by the collar.

The forearms and hands are the GS-2 graft suit's (raw_assets/augments/actives/_kit.py), so the suit colours
apply. The game (BossExecution) moves them in camera space; the models never animate.
Axes (the kit's): +X forward along the forearm, +Z up, origin at the wrist. In Godot (x, z, -y).

Run (about 20 s, preview about 1 min):
  tools/blender.sh raw_assets/characters/fp_execution/build.py --out assets/characters/fp_execution/execution_hands.gltf \
      --preview docs/previews/execution_hands.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "augments", "actives"))
import _kit as K  # noqa: E402

args = K.init("execution_hands", 0, "0", views_default="fp")


def build(side, curl, thumb, name):
    arm = K.part(f"forearm_{name}", K.forearm(side=side))
    wrist, palm, fingers, tsegs = K.hand(side=side)
    for k, (fname, segs) in enumerate(fingers.items()):
        for seg, a in zip(segs, curl):
            seg.rotation_euler = (0.0, math.radians(a + k * 2), 0.0)
    r0 = tsegs[0].rotation_euler
    tsegs[0].rotation_euler = (r0[0] + math.radians(thumb[0] * side), r0[1] + math.radians(thumb[1]), r0[2] + math.radians(thumb[2] * side))
    tsegs[1].rotation_euler = (0.0, math.radians(thumb[3]), 0.0)
    tsegs[2].rotation_euler = (0.0, math.radians(thumb[4]), 0.0)
    root = K.empty(name)
    K.parent(arm, root)
    K.parent(wrist, root)
    return root, palm


# A hard fist: every finger shut tight, the thumb across the middle phalanges.
fist, fist_palm = build(1, (90, 100, 72), (22, 14, -58, 46, 32), "fist_r")
knuckles = K.empty("knuckles", (0.106, 0.0, 0.004))
K.parent(knuckles, fist_palm)
# A claw: hooked fingers, the thumb opposed, as if round a collar.
grip, grip_palm = build(-1, (42, 58, 40), (6, 4, -10, 22, 18), "grip_l")
grip.location = (0.0, 0.3, 0.0)

VIEWS = {
    "fp": ((-0.35, -0.12, 0.22), (0.05, 0.15, 0.0), 60),
    "hero": ((0.22, -0.32, 0.16), (0.04, 0.12, 0.0), 0),
}
print(f"execution hands: {K.tri_count()} triangles")
if args.preview:
    K.render_previews(args.preview.rsplit(".", 1)[0], VIEWS, aim=(0.05, 0.15, 0.0))
if args.out:
    grip.location = (0.0, 0.0, 0.0)
    K.export(args.out, animated=False)
