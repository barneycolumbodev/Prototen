"""The triad man's head, sculpted as a signed distance field (2026-11-16).

Owner, 2026-11-16: "Enemies and how they look is the absolute weakest part of the game so far." The
first head was a metaball egg with a few soft bumps for features: from the front it read as a shop
mannequin (no sockets, a slit for each eye, a nose like a knuckle). This one is built from the skull
out with raw_assets/_lib/sdf.py, the way a sculptor blocks in a head:

- the cranium and the back of the skull, the frontal bone and a brow ridge that overhangs the eyes;
- orbits carved under the brow, the eyeballs (body.build_eyes) sitting in them, and upper and lower
  lids that wrap the eyeball round an almond-shaped opening, with a fold over the upper lid;
- zygomatic bones and their arches back to the ears, the hollow under them;
- the maxilla and the mouth's barrel, the lips with a mouth line, the corners tucked in, a philtrum;
- the nose: a bony bridge, the cartilage to a rounded tip, the alar wings, nostrils carved under;
- the mandible: the body of the jaw to its angle, the ramus up to the ear, a square chin;
- ears with a helix rim, the concha and the lobe;
- the neck with the sternocleidomastoids and the Adam's apple, the trapezius behind.

Landmarks stay where the painted maps (paint.py) and the rig expect them: eyes at body.EYE (x ±0.031,
y -0.0815, z 1.667), the mouth line at z 1.5975, the chin near z 1.56, the cut at z 1.43.
Blender axes: +Z up, the man faces -Y, his left is +X. Metres.
"""
import math
import os
import sys

import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import sdf  # noqa: E402

V = Vector


def rot(axis, deg):
    return np.array(Matrix.Rotation(math.radians(deg), 3, axis), dtype=float)


def model(low=False):
    """The head. `low`: the version LOW is cut from: no small carved details (nostrils, creases,
    the ear's bowl, the mouth line) and thicker lids, so decimation has nothing thin to tear;
    HIGH's detail comes back through the baked normal map."""
    m = sdf.Model()
    E, S, RC = sdf.Ellipsoid, sdf.Sphere, sdf.RoundCone

    # ---------------------------------------------------------------- skull
    m.add(E((0.0, 0.012, 1.69), (0.073, 0.09, 0.08)))                     # cranium
    m.add(E((0.0, 0.05, 1.655), (0.058, 0.048, 0.048)), k=0.03)           # occiput
    m.add(E((0.0, -0.036, 1.705), (0.064, 0.052, 0.052)), k=0.025)        # frontal bone
    for sx in (1, -1):
        m.add(E((0.06 * sx, -0.012, 1.686), (0.016, 0.05, 0.045)), k=0.02)  # parietal sides (squarer skull)
    # Brow ridge: overhangs the eyes, strongest over the inner half.
    for sx in (1, -1):
        m.add(RC((0.008 * sx, -0.084, 1.689), (0.05 * sx, -0.073, 1.688), 0.0085, 0.0065), k=0.014)
    m.add(E((0.0, -0.088, 1.688), (0.014, 0.008, 0.008)), k=0.006)       # glabella

    # ---------------------------------------------------------------- mid face
    m.add(E((0.0, -0.036, 1.638), (0.062, 0.06, 0.078)), k=0.03)          # the face's mass, under the skull
    m.add(E((0.0, -0.066, 1.62), (0.042, 0.034, 0.04)), k=0.024)          # maxilla / mouth barrel
    for sx in (1, -1):
        m.add(E((0.05 * sx, -0.058, 1.648), (0.019, 0.024, 0.013), rot("Z", -22 * sx)), k=0.018)  # cheekbone
        m.add(RC((0.056 * sx, -0.048, 1.648), (0.068 * sx, -0.006, 1.652), 0.0065, 0.0055), k=0.02)  # arch
        m.add(E((0.04 * sx, -0.062, 1.615), (0.018, 0.02, 0.02)), k=0.018)   # cheek flesh

    # ---------------------------------------------------------------- jaw
    for sx in (1, -1):
        m.add(RC((0.016 * sx, -0.074, 1.567), (0.059 * sx, -0.014, 1.586), 0.016, 0.017), k=0.018)  # body
        m.add(RC((0.059 * sx, -0.014, 1.586), (0.061 * sx, 0.004, 1.638), 0.015, 0.011), k=0.018)    # ramus
        m.add(E((0.05 * sx, -0.03, 1.602), (0.013, 0.02, 0.022)), k=0.016)                          # masseter
    m.add(E((0.0, -0.08, 1.562), (0.026, 0.017, 0.018)), k=0.014)         # chin
    m.add(E((0.0, -0.06, 1.552), (0.026, 0.028, 0.01)), k=0.012)          # under the chin

    # ---------------------------------------------------------------- nose
    m.add(RC((0.0, -0.09, 1.678), (0.0, -0.104, 1.652), 0.0065, 0.0075), k=0.006)   # nasal bones
    m.add(RC((0.0, -0.104, 1.652), (0.0, -0.116, 1.632), 0.0075, 0.0095), k=0.005)  # cartilage
    m.add(S((0.0, -0.116, 1.629), 0.0118), k=0.005)                       # tip
    for sx in (1, -1):
        m.add(E((0.0135 * sx, -0.106, 1.623), (0.0085, 0.0095, 0.0078)), k=0.004)   # alar wing
    m.add(RC((0.0, -0.118, 1.622), (0.0, -0.104, 1.616), 0.004, 0.0045), k=0.003)  # columella
    for sx in (1, -1):
        if not low:
            m.sub(E((0.0072 * sx, -0.11, 1.6185), (0.0042, 0.0058, 0.0028)), k=0.002)  # nostrils
            m.sub(E((0.022 * sx, -0.1, 1.622), (0.0035, 0.008, 0.008)), k=0.004)       # alar crease
    if not low:
        m.sub(E((0.0, -0.1, 1.609), (0.0038, 0.004, 0.006)), k=0.003)     # philtrum

    # ---------------------------------------------------------------- mouth
    m.add(RC((-0.019, -0.092, 1.6015), (0.019, -0.092, 1.6015), 0.0044, 0.0044), k=0.007)   # upper lip
    m.add(E((0.0, -0.0948, 1.602), (0.012, 0.0045, 0.0045)), k=0.005)    # its fullness at the middle
    m.add(RC((-0.016, -0.0905, 1.5915), (0.016, -0.0905, 1.5915), 0.0052, 0.0052), k=0.007)  # lower lip
    m.add(E((0.0, -0.0935, 1.5915), (0.011, 0.005, 0.0052)), k=0.005)
    if not low:
        m.sub(sdf.RoundBox((0.0, -0.1, 1.5972), (0.0215, 0.012, 0.0006), r=0.0), k=0.0016)   # mouth line
    for sx in (1, -1):
        m.sub(S((0.0225 * sx, -0.09, 1.597), 0.0032), k=0.003)           # corners
    m.sub(E((0.0, -0.092, 1.58), (0.014, 0.006, 0.0035)), k=0.004)        # under the lower lip

    # ---------------------------------------------------------------- eyes: orbits and lids
    from body import EYE
    for s, c in EYE.items():
        cx, cy, cz = c
        sx = 1 if s == "L" else -1
        # The orbit, carved under the brow (deeper at the inner corner, open to the side).
        m.sub(E((cx + 0.002 * sx, cy - 0.006, cz + 0.002), (0.017, 0.012, 0.0125)), k=0.008)
        # Lids: a shell just over the eyeball, cut open in an almond (the eyeball, a separate mesh, shows).
        if not low:
            m.add(_Lids(c, sx), k=0.003)  # LOW: the eyeball sits in the orbit; the lids come from the bake
        # The fold over the upper lid and the bag under the lower.
        m.add(RC((cx - 0.012 * sx, cy - 0.006, cz + 0.0098), (cx + 0.013 * sx, cy - 0.004, cz + 0.0094), 0.0028,
                 0.0026), k=0.003)
        m.add(RC((cx - 0.009 * sx, cy - 0.0075, cz - 0.0098), (cx + 0.012 * sx, cy - 0.005, cz - 0.0102), 0.0024,
                 0.0022), k=0.004)

    # ---------------------------------------------------------------- ears
    for sx in (1, -1):
        R = rot("Z", 16 * sx) @ rot("Y", -8 * sx)
        m.add(E((0.075 * sx, 0.006, 1.656), (0.0075, 0.019, 0.031), R), k=0.006)       # the ear's plate
        m.add(RC((0.079 * sx, -0.006, 1.683), (0.081 * sx, 0.02, 1.672), 0.0045, 0.0045), k=0.004)  # helix top
        m.add(RC((0.081 * sx, 0.02, 1.672), (0.08 * sx, 0.022, 1.64), 0.0045, 0.0042), k=0.004)     # helix back
        m.add(S((0.077 * sx, 0.006, 1.628), 0.0072), k=0.005)                         # lobe
        if not low:
            m.sub(E((0.082 * sx, 0.004, 1.652), (0.006, 0.009, 0.011)), k=0.004)      # concha
        m.add(S((0.075 * sx, -0.012, 1.652), 0.005), k=0.004)                         # tragus

    # ---------------------------------------------------------------- neck
    m.add(RC((0.0, 0.02, 1.43), (0.0, 0.008, 1.6), 0.057, 0.05), k=0.02)
    for sx in (1, -1):
        m.add(RC((0.058 * sx, 0.026, 1.628), (0.014 * sx, -0.038, 1.47), 0.0125, 0.012), k=0.016)  # SCM
    m.add(E((0.0, -0.041, 1.532), (0.0105, 0.009, 0.013)), k=0.008)      # Adam's apple
    m.add(E((0.0, 0.045, 1.47), (0.07, 0.04, 0.035)), k=0.03)            # trapezius / neck base
    return m


class _Lids(sdf.Prim):
    """A shell around the eyeball (radius `r` + `t`) with an almond-shaped opening facing forward."""

    def __init__(self, c, sx, r=0.0122, t=0.0026):
        self.c = np.asarray(c, float)
        self.sx = sx
        self.r = r
        self.t = t

    def aabb(self):
        e = self.r + self.t + 0.004
        return self.c - e, self.c + e

    def __call__(self, x, y, z):
        cx, cy, cz = self.c
        dx, dy, dz = x - cx, y - cy, z - cz
        d = np.sqrt(dx * dx + dy * dy + dz * dz)
        shell = np.abs(d - (self.r + self.t * 0.5)) - self.t * 0.5
        # The opening, seen from the front: an almond 0.027 wide, 0.0105 tall, the outer corner a
        # little higher (a slight canthal tilt). Only on the front half.
        u = dx * self.sx            # + toward the outer corner
        half_w = 0.0135
        tilt = 0.0012 * (u / half_w)
        k = np.clip(1.0 - (u / half_w) ** 2, 0.0, 1.0)
        top = 0.0052 * np.sqrt(k) + tilt
        bot = -0.0038 * np.sqrt(k) + tilt
        inside = np.maximum(dz - top, bot - dz)          # < 0 inside the almond (vertically)
        front = -dy - 0.004                               # > 0 on the front of the eyeball
        hole = np.maximum(inside, -front)
        return np.maximum(shell, -hole)


def build_mesh(name, h, low=False):
    """Surface-nets mesh of the head at grid step `h` (bpy mesh datablock)."""
    g = sdf.Grid((-0.1, -0.14, 1.4), (0.1, 0.13, 1.8), h)
    F = evaluate(model(low), g)
    # Close the neck flat at 1.415 (inside the grid): a closed mesh survives the voxel remesh.
    z = g.coords()[2]
    F = np.maximum(F, (1.415 - z).astype(np.float32))
    return sdf.to_mesh(name, F, g)


def evaluate(m, grid, far=1.0):
    """sdf.Model.evaluate with wider blocks: the ellipsoids' distances are only estimates, and big
    blends (k up to 0.03) left a seam where a block ended."""
    F = np.full(grid.shape, np.float32(far), dtype=np.float32)
    for kind, prim, k in m.ops:
        lo, hi = prim.aabb()
        mg = 2.0 * k + 3 * grid.h + 0.01
        sl = grid.block(lo - mg, hi + mg)
        if sl is None:
            continue
        d = prim(*grid.coords(sl))
        F[sl] = sdf.smin(F[sl], d, k) if kind == "add" else sdf.smax(F[sl], -d, k)
    return F
