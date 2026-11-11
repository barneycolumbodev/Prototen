"""Texture painting for the triad body and wardrobe (numpy, per texel).

Input: baked maps of the atlas (rest position, normal, material, object, AO)
for every texel a mesh covers. Output per texel: base colour, roughness,
metalness, the tint mask, a height for the cloth's normal detail, and for
skin the tattoo layers and facial hair.

Tint mask (triad.gdshader): R = the garment's main colour, G = its second
colour (rib knit, stripes, laces), B = where a print may go, A = skin.
Cloth is painted neutral grey (0.5) where it's tinted; the shader multiplies
by the colours each enemy draws from the wardrobe.
"""
import math

import numpy as np

from common import J, MATS, arm_coord, leg_coord, regions, ss, ARM_LEN, UPPER_ARM_LEN, THIGH_LEN, LEG_LEN
from body import EYE
import wardrobe


# ====================================================================== noise
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFF).astype(np.float32) / 65535.0


def vnoise(P, freq, seed=0):
    q = P * freq
    i = np.floor(q).astype(np.int64)
    f = (q - i).astype(np.float32)
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, freq, octaves=4, seed=0):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * vnoise(P, freq * (2 ** o), seed + o)
        norm += amp
        amp *= 0.5
    return total / norm


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def line(d, width):
    """1 on a line of half-width `width` at d = 0, soft edge."""
    return 1.0 - sstep(width * 0.5, width, np.abs(d))


def dashes(P, period=0.004):
    """Stitch dashes along any line (by position)."""
    return (np.sin((P[:, 0] + P[:, 1] + P[:, 2]) / period * math.pi) > -0.2).astype(np.float64)


class Out:
    """The painted channels for a set of texels."""

    def __init__(self, n):
        self.base = np.full((n, 3), 0.5)
        self.rough = np.full(n, 0.8)
        self.metal = np.zeros(n)
        self.mask = np.zeros((n, 4))
        self.height = np.zeros(n)
        self.skin = np.zeros((n, 4))   # tattoo sets (RGB), facial hair (A)


# ====================================================================== cloth helpers
def cloth(o, P, grain=900.0, amp=0.08, folds=0.0016, seed=1):
    """Neutral tinted cloth: fine grain, soft folds."""
    g = fbm(P, grain, 2, seed)
    lum = 0.5 * (1.0 + amp * (g - 0.5) * 2.0)
    o.base[:] = lum[:, None]
    o.mask[:, 0] = 1.0
    o.height += folds * (fbm(P, 22.0, 3, seed + 3) - 0.5) + 0.0003 * (g - 0.5)
    return lum


def seam(o, d, P, width=0.0022, depth=0.0005, dark=0.45):
    k = line(d, width)
    o.height -= depth * k
    o.base *= (1.0 - dark * k * (0.6 + 0.4 * dashes(P)))[:, None]


def stitch(o, d, P, width=0.0012, dark=0.3):
    k = line(d, width) * dashes(P)
    o.base *= (1.0 - dark * k)[:, None]
    o.height -= 0.00015 * k


def rib(o, P, mask, angle_coord, period=0.0035, dark=0.18):
    """Rib knit: ridges across `angle_coord` (m along the band)."""
    r = 0.5 + 0.5 * np.sin(angle_coord / period * 2 * math.pi)
    o.base *= np.where(mask, 1.0 - dark + dark * r, 1.0)[:, None]
    o.height += np.where(mask, 0.0004 * (r - 0.5), 0.0)
    o.rough = np.where(mask, 0.92, o.rough)


def sleeve_folds(o, P, amount=0.0012):
    """Rings of folds round the elbows and the inside of the arms."""
    reg = regions(P)
    for s in ("L", "R"):
        sa, _ = arm_coord(P, s)
        m = reg[f"arm_{s}"]
        near = np.exp(-0.5 * ((sa - UPPER_ARM_LEN) / 0.05) ** 2)
        o.height += np.where(m, amount * near * np.sin(sa / 0.022 * 2 * math.pi + 3 * fbm(P, 30, 2, 5)), 0.0)


def knee_folds(o, P, amount=0.0012):
    reg = regions(P)
    for s in ("L", "R"):
        sl, _ = leg_coord(P, s)
        m = reg[f"leg_{s}"]
        near = np.exp(-0.5 * ((sl - THIGH_LEN) / 0.05) ** 2) + 0.6 * np.exp(-0.5 * ((sl - 0.02) / 0.05) ** 2)
        o.height += np.where(m, amount * near * np.sin(sl / 0.025 * 2 * math.pi + 3 * fbm(P, 30, 2, 9)), 0.0)


def side_seams(o, P, where):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    seam(o, np.where(where & (np.abs(x) > 0.09), y - 0.004, 1.0), P)


def arm_band(P, s0, s1):
    """1 on both arms where s0 < distance along the arm < s1."""
    reg = regions(P)
    out = np.zeros(len(P), dtype=bool)
    for s in ("L", "R"):
        sa, _ = arm_coord(P, s)
        out |= reg[f"arm_{s}"] & (sa > s0) & (sa < s1)
    return out


def arm_s(P):
    reg = regions(P)
    s = np.full(len(P), -1.0)
    for side in ("L", "R"):
        sa, _ = arm_coord(P, side)
        s = np.where(reg[f"arm_{side}"], sa, s)
    return s


def leg_s(P):
    reg = regions(P)
    s = np.full(len(P), -1.0)
    for side in ("L", "R"):
        sl, _ = leg_coord(P, side)
        s = np.where(reg[f"leg_{side}"], sl, s)
    return s


def around(P):
    """Distance round the torso (m), for knit ribs on hems."""
    return np.arctan2(P[:, 1], P[:, 0]) * 0.16


def zip_down(o, P, x0=0.0, top=1.47, bottom=0.9, front=True):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    zone = (np.abs(x - x0) < 0.009) & ((y < -0.04) if front else True) & (z > bottom) & (z < top)
    teeth = zone & (np.abs(x - x0) < 0.003)
    tooth = 0.5 + 0.5 * np.sin(z / 0.0022 * math.pi)
    o.base = np.where((zone & ~teeth)[:, None], o.base * 0.6, o.base)
    o.base = np.where(teeth[:, None], (0.32 + 0.2 * tooth)[:, None] * np.array((1.0, 1.0, 1.0)), o.base)
    o.mask[teeth, 0] = 0.0
    o.mask[zone, 2] = 0.0
    o.metal[teeth] = 0.8
    o.rough[teeth] = 0.35
    o.height += np.where(teeth, 0.0008 * tooth, 0.0) - np.where(zone & ~teeth, 0.0004, 0.0)


def pocket_box(o, P, x0, x1, z0, z1, front=True, flap=0.0):
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    side = (y < -0.02) if front else (y > 0.02)
    inside = side & (x > x0) & (x < x1) & (z > z0) & (z < z1)
    edge = inside & ((np.abs(x - x0) < 0.003) | (np.abs(x - x1) < 0.003) | (np.abs(z - z0) < 0.003) | (np.abs(z - z1) < 0.003))
    o.base = np.where(edge[:, None], o.base * 0.62, o.base)
    o.height += np.where(edge, -0.0004, 0.0) + np.where(inside, 0.0003, 0.0)
    if flap:
        fl = inside & (np.abs(z - (z1 - flap)) < 0.0025)
        o.base = np.where(fl[:, None], o.base * 0.55, o.base)
    return inside


# ====================================================================== garments
def g_singlet(o, P, N):
    cloth(o, P, 1100, 0.05, 0.0008)
    f = wardrobe.COVERS["singlet"](P)
    rib(o, P, np.ones(len(P), bool), P[:, 0] + 0.2 * P[:, 1], 0.0025, 0.12)
    bind = f < 0.008
    o.base = np.where(bind[:, None], o.base * 0.9, o.base)
    stitch(o, f - 0.006, P)
    o.mask[:, 2] = 1.0
    o.rough[:] = 0.9


def g_tee(o, P, N):
    cloth(o, P, 1300, 0.06, 0.0018)
    f = wardrobe.COVERS["tee"](P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    rho = np.sqrt(x * x + (y - 0.015) ** 2)
    neckband = (z > 1.38) & (rho < 0.105) & (f < 0.016)
    rib(o, P, neckband, around(P), 0.003, 0.15)
    stitch(o, np.where(neckband, 1.0, f - 0.016), P)
    stitch(o, f - 0.01, P)
    side_seams(o, P, regions(P)["torso"])
    sa = arm_s(P)
    seam(o, np.where(sa > 0, sa - 0.035, 1.0), P)
    sleeve_folds(o, P, 0.0006)
    o.height += 0.0012 * np.sin(z / 0.03 * 2 * math.pi + 4 * fbm(P, 20, 2, 3)) * ss((1.02 - z) / 0.08) * regions(P)["torso"]
    o.mask[:, 2] = np.where(neckband, 0.0, 1.0)
    o.rough[:] = 0.88


def _shirt(o, P, N, gid, open_front):
    cloth(o, P, 1500, 0.05, 0.0018, seed=4)
    f = wardrobe.COVERS[gid](P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    fr = y < -0.03
    if open_front:
        gap = 0.045 + 0.05 * ss((z - 1.12) / 0.26)
        placket = fr & (np.abs(x) - gap < 0.022) & (z < 1.36)
        stitch(o, np.where(fr, np.abs(x) - gap - 0.02, 1.0), P)
        buttons = placket & (np.abs(np.abs(x) - gap - 0.01) < 0.0055) & (np.abs(((z - 0.95) % 0.085) - 0.04) < 0.0055) & (x < 0)
    else:
        placket = fr & (np.abs(x) < 0.016) & (z < 1.37)
        seam(o, np.where(fr, np.abs(x) - 0.016, 1.0), P, 0.0018, 0.0003, 0.3)
        buttons = placket & (np.abs(x) < 0.0055) & (np.abs(((z - 0.95) % 0.085) - 0.04) < 0.0055) & (z < 1.33)
    o.base = np.where(buttons[:, None], np.array((0.82, 0.8, 0.74)), o.base)
    o.mask[buttons, 0] = 0.0
    o.height += np.where(buttons, 0.0012, 0.0)
    rho = np.sqrt(x * x + (y - 0.015) ** 2)
    collar = (z > 1.37) & (rho < 0.125)
    stitch(o, np.where(collar, f - 0.012, 1.0), P)
    seam(o, np.where(collar, rho - 0.1, 1.0), P, 0.002, 0.0006, 0.35)
    stitch(o, f - 0.012, P)
    if not open_front:
        pocket_box(o, P, 0.035, 0.1, 1.2, 1.29)
    side_seams(o, P, regions(P)["torso"])
    sa = arm_s(P)
    seam(o, np.where(sa > 0, sa - 0.04, 1.0), P)
    o.height += 0.0014 * np.sin(z / 0.04 * 2 * math.pi + 4 * fbm(P, 15, 2, 7)) * ss((1.05 - z) / 0.1)
    o.mask[:, 2] = np.where(buttons, 0.0, 1.0)
    o.rough[:] = 0.8


def g_shirt(o, P, N):
    _shirt(o, P, N, "shirt", False)


def g_shirt_open(o, P, N):
    _shirt(o, P, N, "shirt_open", True)


def g_bomber(o, P, N):
    cloth(o, P, 700, 0.06, 0.0028, seed=6)
    f = wardrobe.COVERS["bomber"](P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sa = arm_s(P)
    hem = (z < 0.975) & (sa < 0)
    cuff = sa > wardrobe.CUFF_S - 0.065
    collar = z > 1.43
    knit = hem | cuff | collar
    rib(o, P, knit, np.where(cuff, (P[:, 0] + P[:, 1]) * 0.7, around(P)), 0.0035, 0.2)
    o.mask[knit, 0] = 0.0
    o.mask[knit, 1] = 1.0
    zip_down(o, P, 0.0, 1.47, 0.9)
    side_seams(o, P, regions(P)["torso"] & ~hem)
    seam(o, np.where(sa > 0, sa - 0.06, 1.0), P)
    # MA-1 sleeve pocket on the left arm.
    reg = regions(P)
    sl, _ = arm_coord(P, "L")
    pk = reg["arm_L"] & (sl > 0.07) & (sl < 0.15) & (y < 0.0) & (y > -0.045)
    edge = pk & ((np.abs(sl - 0.07) < 0.003) | (np.abs(sl - 0.15) < 0.003) | (np.abs(y + 0.045) < 0.003) | (np.abs(y) < 0.003))
    o.base = np.where(edge[:, None], o.base * 0.6, o.base)
    sleeve_folds(o, P, 0.0018)
    o.height += 0.0018 * np.sin(z / 0.035 * 2 * math.pi + 3 * fbm(P, 18, 2, 2)) * ss((1.06 - z) / 0.08) * ~knit
    o.rough[:] = np.where(knit, 0.92, 0.42 + 0.1 * fbm(P, 60, 2, 8))
    o.mask[:, 2] = 0.0


def g_hoodie(o, P, N):
    cloth(o, P, 1600, 0.05, 0.0025, seed=8)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sa = arm_s(P)
    hem = (z < 0.96) & (sa < 0)
    cuff = sa > wardrobe.CUFF_S - 0.06
    knit = hem | cuff
    rib(o, P, knit, np.where(cuff, (P[:, 0] + P[:, 1]) * 0.7, around(P)), 0.003, 0.18)
    stitch(o, np.where(hem, z - 0.96, np.where(cuff, sa - (wardrobe.CUFF_S - 0.06), 1.0)), P)
    # Kangaroo pocket: slanted openings, a stitched outline.
    fr = y < -0.03
    pk = fr & (np.abs(x) < 0.1 - 0.25 * (z - 0.95).clip(0)) & (z > 0.955) & (z < 1.1)
    edge = pk & ((np.abs(z - 1.1) < 0.003) | (np.abs(np.abs(x) - (0.1 - 0.25 * (z - 0.95).clip(0))) < 0.0035))
    o.base = np.where(edge[:, None], o.base * 0.6, o.base)
    o.height += np.where(edge, -0.0006, 0.0)
    # Hood: the inside shows darker, drawstrings hang from the neck (second colour).
    hood = (z > 1.42) & (y > -0.02) | ((z > 1.38) & (y > 0.06))
    o.base = np.where(hood[:, None], o.base * 0.85, o.base)
    for sx in (1, -1):
        cord = fr & (np.abs(x - 0.03 * sx) < 0.0035) & (z > 1.22) & (z < 1.43)
        o.mask[cord, 0] = 0.0
        o.mask[cord, 1] = 1.0
        o.height += np.where(cord, 0.0012, 0.0)
        tip = fr & (np.abs(x - 0.03 * sx) < 0.005) & (np.abs(z - 1.225) < 0.012)
        o.base = np.where(tip[:, None], np.array((0.2, 0.2, 0.2)), o.base)
        o.mask[tip, 0:2] = 0.0
    side_seams(o, P, regions(P)["torso"] & ~hem)
    sleeve_folds(o, P, 0.0018)
    o.height += 0.0016 * np.sin(z / 0.03 * 2 * math.pi + 3 * fbm(P, 18, 2, 4)) * ss((1.02 - z) / 0.06) * ~knit
    o.rough[:] = 0.95
    o.mask[:, 2] = np.where(knit | hood, 0.0, 1.0)


def g_track(o, P, N):
    cloth(o, P, 1800, 0.04, 0.0016, seed=10)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sa = arm_s(P)
    zip_down(o, P, 0.0, 1.48, 0.9)
    # Two stripes down the outside of each sleeve and over the shoulders (second colour).
    reg = regions(P)
    for s, sx in (("L", 1), ("R", -1)):
        el, wr = J[f"elbow.{s}"], J[f"wrist.{s}"]
        sl, _ = arm_coord(P, s)
        m = reg[f"arm_{s}"]
        # Outer side of the arm: away from the body (+x for L), measured round the limb.
        outer = (P[:, 0] * sx - (J[f"shoulder.{s}"].x * sx + 0.6 * sl * 0.85))
        ang = np.arctan2(P[:, 1] - J[f"shoulder.{s}"].y, (P[:, 0] - J[f"shoulder.{s}"].x) * sx)
        for c0 in (-0.12, 0.12):
            st = m & (np.abs(ang - c0) < 0.07)
            o.mask[st, 0] = 0.0
            o.mask[st, 1] = 1.0
    collar = z > 1.43
    hem = (z < 0.955) & (sa < 0)
    cuff = sa > wardrobe.CUFF_S - 0.05
    rib(o, P, hem | cuff, np.where(cuff, (P[:, 0] + P[:, 1]) * 0.7, around(P)), 0.003, 0.14)
    stitch(o, np.where(collar, z - 1.445, 1.0), P)
    side_seams(o, P, reg["torso"])
    sleeve_folds(o, P, 0.0012)
    o.rough[:] = 0.38 + 0.08 * fbm(P, 80, 2, 3)
    o.mask[:, 2] = 0.0


def g_leather(o, P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    g = fbm(P, 2600, 2, 12)
    crack = fbm(P, 400, 3, 13)
    lum = 0.5 * (0.9 + 0.16 * (g - 0.5) + 0.18 * (crack - 0.5))
    o.base[:] = lum[:, None]
    o.mask[:, 0] = 1.0
    o.height += 0.0002 * (g - 0.5) + 0.0016 * (fbm(P, 20, 3, 14) - 0.5)
    f = wardrobe.COVERS["leather"](P)
    stitch(o, f - 0.007, P, 0.0012, 0.35)
    rho = np.sqrt(x * x + (y - 0.015) ** 2)
    lapel = (z > 1.25) & (y < -0.02) & (f < 0.07)
    seam(o, np.where(lapel, f - 0.06, 1.0), P, 0.003, 0.0008, 0.5)
    seam(o, np.where(z > 1.4, rho - 0.11, 1.0), P, 0.003, 0.0008, 0.4)
    side_seams(o, P, regions(P)["torso"])
    sa = arm_s(P)
    seam(o, np.where(sa > 0, sa - 0.06, 1.0), P)
    sleeve_folds(o, P, 0.002)
    # Worn: lighter on the creases and edges.
    o.base *= (1.0 + 0.25 * (1.0 - sstep(0.0, 0.01, f)))[:, None]
    o.rough[:] = 0.38 + 0.2 * crack
    o.mask[:, 2] = 0.0


def g_cargo(o, P, N):
    cloth(o, P, 1400, 0.07, 0.0022, seed=14)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    tw = 0.5 + 0.5 * np.sin((x * 0.7 + z) / 0.0016 * math.pi)
    o.base *= (0.96 + 0.05 * tw)[:, None]
    f = wardrobe.COVERS["cargo"](P)
    sl = leg_s(P)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        s, _ = leg_coord(P, side)
        outer = (x * sx > 0.115)
        pk = outer & (s > 0.2) & (s < 0.42) & (np.abs(y) < 0.06)
        edge = pk & ((np.abs(s - 0.2) < 0.003) | (np.abs(s - 0.42) < 0.003) | (np.abs(np.abs(y) - 0.06) < 0.003))
        flap = pk & (np.abs(s - 0.245) < 0.0025)
        o.base = np.where((edge | flap)[:, None], o.base * 0.58, o.base)
        o.height += np.where(edge | flap, -0.0005, 0.0)
    o.base = np.where((z > 1.0)[:, None] & (z < 1.045)[:, None], o.base * 0.92, o.base)
    stitch(o, z - 1.0, P)
    seam(o, np.where((sl > 0) & (np.abs(x) > 0.12), y, 1.0), P)
    stitch(o, f - 0.008, P)
    knee_folds(o, P, 0.0018)
    o.rough[:] = 0.88
    o.mask[:, 2] = 1.0


def g_jeans(o, P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    tw = 0.5 + 0.5 * np.sin((x * 0.9 + z * 1.1 + y * 0.3) / 0.0012 * math.pi)
    g = fbm(P, 1500, 2, 15)
    lum = 0.5 * (0.88 + 0.1 * tw + 0.08 * (g - 0.5))
    # Fading: whiskers at the hips, lighter on the thighs' fronts and the knees.
    sl = leg_s(P)
    fade = 0.25 * ss((-y - 0.0) / 0.06) * np.exp(-0.5 * ((sl - 0.25) / 0.12) ** 2) * (sl > 0)
    fade += 0.15 * np.exp(-0.5 * ((sl - THIGH_LEN) / 0.05) ** 2) * (sl > 0)
    whisk = (sl > 0) & (sl < 0.12) & (y < -0.03)
    fade += whisk * 0.2 * (np.sin((z + np.abs(x) * 0.8) / 0.012 * math.pi) > 0.6)
    lum = lum * (1.0 + fade)
    o.base[:] = lum[:, None]
    o.mask[:, 0] = 1.0
    o.height += 0.0014 * (fbm(P, 22, 3, 16) - 0.5) + 0.0002 * (tw - 0.5)
    f = wardrobe.COVERS["jeans"](P)
    # Gold stitching (not tinted), back pockets, belt.
    gold = np.array((0.75, 0.55, 0.25))
    def gstitch(d):
        k = line(d, 0.0013) * dashes(P)
        o.base[:] = o.base * (1 - k[:, None]) + gold * k[:, None]
        o.mask[:, 0] *= 1 - k
    gstitch(f - 0.008)
    for sx in (1, -1):
        bp = (y > 0.04) & (np.abs(x - 0.07 * sx) < 0.045) & (z > 0.86) & (z < 0.96)
        gstitch(np.where(bp, np.minimum(np.abs(np.abs(x - 0.07 * sx) - 0.04), np.abs(z - 0.865)), 1.0))
    gstitch(np.where(sl > 0, (np.abs(x) - 0.17) * 3, 1.0))
    belt = (z > 1.005) & (z < 1.04)
    o.base = np.where(belt[:, None], np.array((0.09, 0.06, 0.045)), o.base)
    o.mask[belt, 0] = 0.0
    o.rough[belt] = 0.5
    buckle = belt & (y < -0.06) & (np.abs(x) < 0.022)
    o.base = np.where(buckle[:, None], np.array((0.7, 0.68, 0.62)), o.base)
    o.metal[buckle] = 0.9
    o.rough[buckle] = 0.3
    knee_folds(o, P, 0.0016)
    o.rough[:] = np.where(belt, o.rough, 0.9)
    o.mask[:, 2] = 0.0


def g_trackpants(o, P, N):
    cloth(o, P, 1800, 0.04, 0.0018, seed=17)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sl = leg_s(P)
    for sx in (1, -1):
        stripe = (sl > 0) & (x * sx > 0) & (np.abs(y + 0.0) < 0.009) & (np.abs(x) > 0.1)
        stripe2 = (sl > 0) & (x * sx > 0) & (np.abs(np.abs(y) - 0.016) < 0.004) & (np.abs(x) > 0.1)
        st = stripe | stripe2
        o.mask[st, 0] = 0.0
        o.mask[st, 1] = 1.0
    cuff = sl > wardrobe.ANKLE_S - 0.05
    rib(o, P, cuff, around(P), 0.003, 0.12)
    waist = z > 1.0
    rib(o, P, waist, around(P), 0.004, 0.1)
    knee_folds(o, P, 0.0016)
    o.rough[:] = 0.45
    o.mask[:, 2] = 0.0


def g_shorts(o, P, N):
    cloth(o, P, 1400, 0.07, 0.0018, seed=18)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    f = wardrobe.COVERS["shorts"](P)
    stitch(o, f - 0.012, P)
    stitch(o, z - 1.0, P)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        s, _ = leg_coord(P, side)
        pk = (x * sx > 0.115) & (s > 0.2) & (s < 0.38) & (np.abs(y) < 0.055)
        edge = pk & ((np.abs(s - 0.2) < 0.003) | (np.abs(s - 0.38) < 0.003) | (np.abs(np.abs(y) - 0.055) < 0.003))
        o.base = np.where(edge[:, None], o.base * 0.6, o.base)
    o.rough[:] = 0.88
    o.mask[:, 2] = 1.0


def g_slacks(o, P, N):
    cloth(o, P, 2400, 0.03, 0.0012, seed=19)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sl = leg_s(P)
    crease = (sl > 0) & (y < -0.02)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        cx = J[f"knee.{side}"].x
        k = line(np.where(crease & (x * sx > 0), x - cx * 1.0, 1.0), 0.003)
        o.height += 0.0006 * k
        o.base *= (1.0 + 0.08 * k)[:, None]
    belt = (z > 1.005) & (z < 1.04)
    o.base = np.where(belt[:, None], np.array((0.05, 0.04, 0.035)), o.base)
    o.mask[belt, 0] = 0.0
    buckle = belt & (y < -0.06) & (np.abs(x) < 0.018)
    o.base = np.where(buckle[:, None], np.array((0.78, 0.66, 0.4)), o.base)
    o.metal[buckle] = 0.9
    o.rough[:] = np.where(buckle, 0.3, np.where(belt, 0.45, 0.7))
    knee_folds(o, P, 0.001)
    o.mask[:, 2] = 0.0


def _shoe(o, P, N, boot):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    g = fbm(P, 1200, 2, 31)
    o.base[:] = (0.5 * (0.88 + 0.2 * (g - 0.5)))[:, None]
    o.mask[:, 0] = 1.0
    sole_top = 0.032 if boot else 0.027
    sole = z < sole_top
    o.base = np.where(sole[:, None], np.array((0.06, 0.055, 0.05)) if boot else np.array((0.85, 0.83, 0.78)), o.base)
    o.mask[sole, 0] = 0.0
    k = line(z - sole_top, 0.002)
    o.base *= (1.0 - 0.5 * k)[:, None]
    for s in ("L", "R"):
        cx = J[f"ankle.{s}"].x + 0.004 * (1 if s == "L" else -1)
        lace = (np.abs(x - cx) < 0.014) & (y > -0.095) & (y < 0.0) & (N[:, 2] > 0.5) & (z > 0.05)
        bars = lace & (np.sin(y / 0.0075 * math.pi) > 0.1)
        o.mask[bars, 0] = 0.0
        o.mask[bars, 1] = 1.0
        o.height += np.where(bars, 0.0008, 0.0)
        if not boot:
            # A swoosh-free side stripe in the second colour.
            st = (np.abs(x - cx) > 0.03) & (np.abs(z - 0.055 - 0.25 * (y + 0.05)) < 0.006) & (y > -0.1) & (y < 0.04)
            o.mask[st, 0] = 0.0
            o.mask[st, 1] = 1.0
    o.rough[:] = np.where(sole, 0.85, 0.5 if boot else 0.6)
    o.mask[:, 2] = 0.0


def g_sneakers(o, P, N):
    _shoe(o, P, N, False)


def g_boots(o, P, N):
    _shoe(o, P, N, True)


def _hair(o, P, N, scale=1.0):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    streak = vnoise(P * np.array((3.0, 0.4, 1.0)), 700.0, 21)
    lum = 0.5 * (0.7 + 0.5 * streak) * scale
    front = sstep(0.03, 0.08, -y)
    back = sstep(0.03, 0.1, y)
    centre = 1.0 - sstep(0.03, 0.065, np.abs(x))
    line_z = 1.69 + front * (0.02 + 0.028 * centre) - back * 0.07
    fade = sstep(0.0, 0.035, z - line_z) * (1 - front) + front
    o.base[:] = lum[:, None]
    o.mask[:, 0] = 0.4 + 0.6 * fade
    o.base = o.base * fade[:, None] + (1 - fade[:, None]) * np.array((0.36, 0.3, 0.27))
    o.height += 0.0004 * (streak - 0.5)
    o.rough[:] = 0.6


def g_hair_fade(o, P, N):
    _hair(o, P, N)


def g_hair_slick(o, P, N):
    _hair(o, P, N, 1.1)
    o.rough[:] = 0.35


def g_hair_spiky(o, P, N):
    _hair(o, P, N, 1.0)


def g_hair_buzz(o, P, N):
    g = vnoise(P, 3000.0, 5)
    o.base[:] = (0.5 * (0.6 + 0.6 * g))[:, None]
    o.mask[:, 0] = 0.75
    o.rough[:] = 0.8


def g_cap(o, P, N):
    cloth(o, P, 1400, 0.05, 0.0006, seed=22)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    brim = (y < -0.09) & (z < 1.7)
    o.mask[brim, 0] = 0.0
    o.mask[brim, 1] = 1.0
    for a in np.linspace(-2.6, 2.6, 6):
        d = np.abs(np.arctan2(x, -y) - a) * 0.08
        seam(o, np.where(~brim & (z > 1.7), d, 1.0), P, 0.0018, 0.0003, 0.3)
    button = (z > 1.788) & (np.abs(x) < 0.008) & (np.abs(y - 0.008) < 0.008)
    o.mask[button, 0] = 0.0
    o.mask[button, 1] = 1.0
    stitch(o, np.where(brim, ((x * x + (y + 0.012) ** 2) ** 0.5 - 0.14), 1.0), P)
    o.rough[:] = 0.85
    o.mask[:, 2] = np.where(brim, 0.0, 1.0)


def g_beanie(o, P, N):
    cloth(o, P, 1000, 0.05, 0.0004, seed=23)
    rib(o, P, np.ones(len(P), bool), np.arctan2(P[:, 1], P[:, 0]) * 0.09, 0.003, 0.25)
    fold = P[:, 2] < 1.685
    o.base = np.where(fold[:, None], o.base * 0.9, o.base)
    o.rough[:] = 0.95


def g_glasses(o, P, N, mid):
    lens = mid == MATS.index("lens")
    # Dark lenses with a faint gradient (lighter at the bottom), glossy.
    grad = np.clip((1.68 - P[:, 2]) / 0.03, 0, 1)
    o.base[:] = np.where(lens[:, None], np.array((0.03, 0.035, 0.045)) + grad[:, None] * 0.06, np.array((0.5, 0.5, 0.5)))
    o.mask[:, 0] = np.where(lens, 0.0, 1.0)
    o.rough[:] = np.where(lens, 0.04, 0.3)
    o.metal[:] = np.where(lens, 0.0, 0.9)


def g_chain(o, P, N):
    g = 0.5 + 0.5 * np.sin((P[:, 0] * 3 + P[:, 2] * 2) / 0.004 * math.pi)
    o.base[:] = (0.5 * (0.75 + 0.35 * g))[:, None]
    o.mask[:, 0] = 1.0
    o.metal[:] = 1.0
    o.rough[:] = 0.25
    o.height += 0.0005 * (g - 0.5)


def g_watch(o, P, N):
    g_chain(o, P, N)
    face = N[:, 2] > 0.6
    o.rough[face] = 0.1


def g_vest(o, P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    grain = fbm(P, 180.0, 3, 1)
    vest = 0.05 * (0.9 + 0.2 * grain)
    row = (np.mod(z - 1.05, 0.038) < 0.025) & (np.abs(x) < 0.15) & (z < 1.36)
    slot = row & (np.mod(x + 0.5, 0.038) < 0.004)
    vest = np.where(row, vest * 1.6, vest)
    vest = np.where(slot, vest * 0.4, vest)
    o.base[:] = vest[:, None]
    o.height += np.where(row, 0.0012, 0.0) - np.where(slot, 0.001, 0.0)
    o.rough[:] = 0.8


PAINTERS = {k[2:]: v for k, v in globals().items() if k.startswith("g_")}


# ====================================================================== body
def paint_body(o, P, N, mid, rest_hand):
    n = len(P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    M = {m: mid == MATS.index(m) for m in MATS}
    grain = fbm(P, 180.0, 3, 1)
    fine = vnoise(P, 900.0, 7)
    pores = vnoise(P, 4000.0, 8)
    reg = regions(P)
    skin = np.array((0.8, 0.62, 0.49)) * (0.94 + 0.1 * grain[:, None]) * (0.97 + 0.05 * fine[:, None])
    skin *= (0.985 + 0.03 * pores[:, None])
    red = np.array((0.05, -0.015, -0.02))
    # Redder at the knuckles, elbows, knees, ears, nose, cheeks; paler on the inner arms.
    sa = arm_s(P)
    knuckles = np.zeros(n)
    for s in ("L", "R"):
        inv = np.array(rest_hand[s].inverted())
        Q = P @ inv[:3, :3].T + inv[:3, 3]
        knuckles += np.exp(-0.5 * ((Q[:, 1] - 0.086) / 0.012) ** 2) * (Q[:, 2] > 0) * (np.abs(Q[:, 0]) < 0.05)
        # Nails: lighter, pinker patches at the backs of the fingertips.
        tips = (Q[:, 1] > 0.14) & (Q[:, 2] > -0.005) & (np.abs(Q[:, 0]) < 0.04)
        skin = np.where(tips[:, None], skin * np.array((1.05, 0.95, 0.95)) + 0.04, skin)
    elbow = np.exp(-0.5 * ((sa - UPPER_ARM_LEN) / 0.03) ** 2) * (sa > 0) * (N[:, 1] > 0)
    face = (z > 1.54) & (y < -0.02)
    cheeks = np.exp(-(((np.abs(x) - 0.042) / 0.02) ** 2 + ((z - 1.632) / 0.018) ** 2)) * face
    nose = np.exp(-((x / 0.012) ** 2 + ((z - 1.632) / 0.015) ** 2)) * face
    ears = ((np.abs(x) > 0.07) & (z > 1.62) & (z < 1.7) & (np.abs(y) < 0.04)).astype(float)
    sl = leg_s(P)
    knees = np.exp(-0.5 * ((sl - THIGH_LEN) / 0.035) ** 2) * (sl > 0) * (N[:, 1] < 0)
    skin += (knuckles * 0.9 + elbow * 0.6 + cheeks + nose * 0.8 + ears * 0.8 + knees * 0.6)[:, None] * red
    inner = (sa > 0) & (N[:, 1] < -0.2)
    skin = np.where(inner[:, None], skin * 1.03, skin)
    # Nipples, navel, armpits.
    for sx in (1, -1):
        nip = np.exp(-(((x - 0.088 * sx) / 0.008) ** 2 + ((z - 1.31) / 0.008) ** 2)) * (y < -0.05)
        skin = skin * (1 - 0.35 * nip[:, None]) + nip[:, None] * np.array((0.45, 0.28, 0.24)) * 0.35
        pit = np.exp(-(((np.abs(x) - 0.15) / 0.02) ** 2 + ((z - 1.3) / 0.03) ** 2)) * (np.abs(y) < 0.05)
        skin = skin * (1 - 0.35 * (pit * (vnoise(P, 2500, 12) > 0.45))[:, None])
    navel = np.exp(-((x / 0.006) ** 2 + ((z - 1.04) / 0.008) ** 2)) * (y < -0.04)
    skin = skin * (1 - 0.5 * navel[:, None])
    # Forearm veins (where HIGH has them), faintly blue-green.
    lips = face & (np.abs(x) < 0.021 - 25 * (z - 1.594) ** 2) & (z > 1.581) & (z < 1.606) & (y < -0.085)
    skin = np.where(lips[:, None], skin * np.array((0.88, 0.7, 0.68)), skin)
    mouth = face & (line(z - 1.5945, 0.0012) > 0.5) & (np.abs(x) < 0.02) & (y < -0.085)
    skin = np.where(mouth[:, None], skin * 0.45, skin)
    nostril = face & (np.abs(np.abs(x) - 0.009) < 0.004) & (np.abs(z - 1.618) < 0.0035) & (y < -0.09)
    skin = np.where(nostril[:, None], skin * 0.4, skin)
    for sx in (1, -1):
        bx = x * sx
        centre = 1.6875 + 0.006 * np.cos(np.clip((bx - 0.031) / 0.024, -1.5, 1.5)) - 0.003
        width = 0.0048 * (1.0 - 0.5 * sstep(0.03, 0.055, bx))
        brow = face & (bx > 0.01) & (bx < 0.057) & (np.abs(z - centre) < width) & (y < -0.07)
        brow_n = brow & (vnoise(P, 2200.0, 11 + sx) > 0.22)
        skin = np.where(brow_n[:, None], np.array((0.06, 0.05, 0.045)), skin)
        e = np.array(EYE["L" if sx > 0 else "R"][:])
        de = np.linalg.norm(P - e, axis=1)
        lash = face & (de < 0.0155) & (de > 0.0118) & (z > e[2] - 0.004)
        skin = np.where(lash[:, None], skin * 0.3, skin)
        under = face & (de < 0.02) & (de > 0.013) & (z < e[2] - 0.004)
        skin = np.where(under[:, None], skin * 0.9, skin)
    # Shaved scalp: a faint blue-grey shadow where hair would grow (shows on bald men).
    front = sstep(0.03, 0.08, -y)
    back = sstep(0.03, 0.1, y)
    cen = 1.0 - sstep(0.03, 0.065, np.abs(x))
    line_z = 1.69 + front * (0.02 + 0.028 * cen) - back * 0.07
    scalp = sstep(-0.005, 0.01, z - line_z) * (z > 1.6)
    skin = skin * (1 - 0.18 * scalp[:, None]) + scalp[:, None] * np.array((0.02, 0.025, 0.03))
    eye = M["eye"]
    eye_col = np.tile(np.array((0.8, 0.77, 0.72)), (n, 1))
    lid = np.zeros(n, dtype=bool)
    for s in ("L", "R"):
        e = np.array(EYE[s][:])
        rel = P - e
        d = rel / np.maximum(np.linalg.norm(rel, axis=1, keepdims=True), 1e-9)
        ang = np.degrees(np.arccos(np.clip(-d[:, 1], -1, 1)))
        near = np.linalg.norm(rel, axis=1) < 0.02
        eye_col = np.where((near & (ang < 18))[:, None], np.array((0.32, 0.2, 0.12)) * (0.8 + 0.4 * fine[:, None]), eye_col)
        eye_col = np.where((near & (ang < 15.5) & (ang > 14.0))[:, None], np.array((0.12, 0.08, 0.05)), eye_col)
        eye_col = np.where((near & (ang < 7))[:, None], np.array((0.02, 0.02, 0.02)), eye_col)
        # The lids cover the eyeball outside an almond-shaped opening (a little
        # higher at the outer corner); the upper lid's edge carries the lashes.
        sx = 1.0 if s == "L" else -1.0
        dx = rel[:, 0] * sx
        half = 0.0058 * np.sqrt(np.clip(1.0 - (dx / 0.0135) ** 2, 0.0, 1.0))
        mid = 0.0004 + 0.0012 * (dx / 0.0135)
        dz = rel[:, 2] - mid
        lid |= near & (np.abs(dz) > half)
        lash = near & (dz > half - 0.0012) & (dz < half + 0.0008) & (rel[:, 1] < -0.004)
        eye_col = np.where(lash[:, None], np.array((0.03, 0.025, 0.02)), eye_col)
    lid &= eye
    eye_col = np.where(lid[:, None], np.array((0.74, 0.56, 0.44)), eye_col)
    o.base[:] = np.where(eye[:, None], eye_col, skin)
    o.rough[:] = np.where(eye & ~lid, 0.12, np.where(lips, 0.4, 0.55 - 0.08 * face))
    o.mask[:, 3] = np.where(eye & ~lid, 0.0, 1.0)
    # Facial hair density (skin map A): stubble 0.3-0.5 over the jaw and lip,
    # 0.75+ where a goatee and moustache would be. The shader thresholds it.
    # Beard area: chin and jaw below the mouth corners, back along the jawline, and the upper lip.
    jawline = 1.6 - 0.25 * np.clip(np.abs(x) - 0.03, 0, None)
    jaw = face & (np.abs(x) < 0.075) & ~lips & ((z < jawline) | ((np.abs(x) < 0.026) & (z > 1.6) & (z < 1.613)))
    stub = jaw * sstep(0.0, 0.008, np.maximum(jawline - z, 0.0) + (z > 1.6) * 0.01) * (0.6 + 0.4 * vnoise(P, 1500.0, 3))
    neckbeard = (z > 1.52) & (z < 1.58) & (y < -0.02) & (np.abs(x) < 0.06)
    goatee = face & (np.abs(x) < 0.02) & (z < 1.585) & (z > 1.55)
    stache = face & (np.abs(x) < 0.028 - 0.6 * (1.61 - z).clip(0)) & (z > 1.6) & (z < 1.612) & (y < -0.08)
    hairy = np.maximum(stub * 0.45, neckbeard * 0.25 * (vnoise(P, 1500, 4) > 0.3))
    hairy = np.maximum(hairy, (goatee | stache) * (0.8 + 0.2 * vnoise(P, 2500, 6)))
    o.skin[:, 3] = hairy * (vnoise(P, 3000.0, 9) > 0.18)
