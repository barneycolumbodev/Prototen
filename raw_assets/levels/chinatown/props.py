"""Props for the Chinatown docks map, built on envkit.Kit.

Every function takes the kit, a base position (x, y, z; z = floor height) and
a yaw in degrees (0 = the prop's front faces -Y, i.e. south), plus options.
Sizes are real-world. Props that block movement or bullets add colliders with
a ballistic surface (data/surfaces). Props that light the scene add `light`
markers, which the bake turns into Blender lights (and Godot may use for
character lighting).
"""
import math

import numpy as np

from envkit import rot_z, rot_x, rot_y

RNG = np.random.default_rng(1977)


def frame(pos, yaw):
    R = rot_z(yaw)
    P = np.asarray(pos, np.float64)
    return R, (lambda local: P + R @ np.asarray(local, np.float64))


def rnd(a, b):
    return float(RNG.uniform(a, b))


def pick(seq):
    return seq[int(RNG.integers(0, len(seq)))]


# ------------------------------------------------------------------ lights

def light(k, pos, color, energy, radius=0.05, kind="POINT", dyn=False, spot=None, direction=None, rng=8.0):
    """energy: watts for the bake. dyn: also a runtime light for characters (Godot)."""
    d = dict(color=[round(c, 3) for c in color], energy=energy, radius=radius, type=kind, dyn=dyn, range=rng)
    if spot:
        d["spot"] = spot
    if direction is not None:
        d["dir"] = [round(float(x), 3) for x in direction]
    k.marker("light", pos, **d)


# ------------------------------------------------------------------ crates, boxes, barrels

def crate(k, pos, yaw=0.0, size=(1.0, 0.8, 0.7), label=True, col=True):
    R, w = frame(pos, yaw)
    sx, sy, sz = size
    c = w((0, 0, sz / 2))
    tint = (rnd(0.42, 0.55), rnd(0.4, 0.5), rnd(0.36, 0.45))
    k.box(c, (sx - 0.04, sy - 0.04, sz - 0.04), "planks", tint, yaw=yaw, uv_scale=2.0)
    # corner posts and rim battens
    for ix in (-1, 1):
        for iy in (-1, 1):
            k.box(w((ix * (sx / 2 - 0.035), iy * (sy / 2 - 0.035), sz / 2)), (0.07, 0.07, sz), "darkwood", (0.75, 0.68, 0.6), yaw=yaw, chamfer=0.008)
    for z in (0.04, sz - 0.04):
        for iy in (-1, 1):
            k.box(w((0, iy * (sy / 2 - 0.01), z)), (sx, 0.03, 0.07), "darkwood", (0.75, 0.68, 0.6), yaw=yaw)
        for ix in (-1, 1):
            k.box(w((ix * (sx / 2 - 0.01), 0, z)), (0.03, sy, 0.07), "darkwood", (0.75, 0.68, 0.6), yaw=yaw)
    if label:
        n = R @ np.array([0, -1.0, 0])
        x = R @ np.array([1.0, 0, 0])
        f = w((0, -sy / 2 - 0.003, sz / 2))
        hw, hh = min(0.3, sx * 0.3), min(0.2, sz * 0.3)
        z = np.array([0, 0, 1.0])
        k.quad(f - x * hw - z * hh, f + x * hw - z * hh, f + x * hw + z * hh, f - x * hw + z * hh, "props", rect="crate")
    if col:
        k.collider(c, size, yaw, "crate")


def fish_crate(k, pos, yaw=0.0, tint=None, full=True, col=True):
    """Stackable plastic fish crate 0.6 x 0.4 x 0.25 with handle slots."""
    R, w = frame(pos, yaw)
    tint = tint or pick([(0.1, 0.25, 0.55), (0.55, 0.12, 0.1), (0.6, 0.5, 0.1), (0.15, 0.4, 0.3)])
    sx, sy, sz, t = 0.6, 0.4, 0.25, 0.025
    k.box(w((0, 0, 0.012)), (sx, sy, 0.024), "plastic", tint, yaw=yaw)
    for iy in (-1, 1):
        k.box(w((0, iy * (sy / 2 - t / 2), sz / 2)), (sx, t, sz), "plastic", tint, yaw=yaw, chamfer=0.006)
    for ix in (-1, 1):
        k.box(w((ix * (sx / 2 - t / 2), 0, sz / 2)), (t, sy - 2 * t, sz), "plastic", tint, yaw=yaw, chamfer=0.006)
        k.box(w((ix * (sx / 2 + 0.001), 0, sz - 0.06)), (0.004, 0.16, 0.04), "plastic", (0.02, 0.02, 0.02), yaw=yaw)
    if full:
        k.box(w((0, 0, sz - 0.05)), (sx - 2 * t, sy - 2 * t, 0.02), "props", (0.5, 0.5, 0.5), yaw=yaw)  # ice
    if col:
        k.collider(w((0, 0, sz / 2)), (sx, sy, sz), yaw, "crate")


def crate_stack(k, pos, yaw=0.0, rows=3, cols=1, tint=None):
    R, w = frame(pos, yaw)
    for c in range(cols):
        for r in range(rows):
            p = w((c * 0.62 - (cols - 1) * 0.31 + rnd(-0.02, 0.02), rnd(-0.02, 0.02), r * 0.25))
            fish_crate(k, p, yaw + rnd(-4, 4), tint=tint, full=(r == rows - 1), col=False)
    k.collider(w((0, 0, rows * 0.125)), (cols * 0.62, 0.42, rows * 0.25), yaw, "crate")


def styro_box(k, pos, yaw=0.0, lid=True, col=True):
    R, w = frame(pos, yaw)
    sx, sy, sz = 0.62, 0.42, 0.3
    k.box(w((0, 0, sz / 2)), (sx, sy, sz), "plastic", (0.47, 0.47, 0.46), yaw=yaw, chamfer=0.015)
    n = R @ np.array([0, -1.0, 0])
    x = R @ np.array([1.0, 0, 0])
    f = w((0, -sy / 2 - 0.003, sz / 2))
    z = np.array([0, 0, 1.0])
    k.quad(f - x * 0.24 - z * 0.12, f + x * 0.24 - z * 0.12, f + x * 0.24 + z * 0.12, f - x * 0.24 + z * 0.12, "props", uv=(0.56, 0.31, 0.72, 0.45))
    if lid:
        k.box(w((0, 0, sz + 0.02)), (sx + 0.02, sy + 0.02, 0.04), "plastic", (0.48, 0.48, 0.47), yaw=yaw + rnd(-3, 3), chamfer=0.01)
    if col:
        k.collider(w((0, 0, sz / 2)), (sx, sy, sz), yaw, "cardboard")


def styro_stack(k, pos, yaw=0.0, n=3):
    for i in range(n):
        styro_box(k, (pos[0] + rnd(-0.03, 0.03), pos[1] + rnd(-0.03, 0.03), pos[2] + i * 0.34), yaw + rnd(-5, 5), lid=True, col=False)
    k.collider((pos[0], pos[1], pos[2] + n * 0.17), (0.64, 0.44, n * 0.34), yaw, "cardboard")


def pallet(k, pos, yaw=0.0):
    R, w = frame(pos, yaw)
    for i in range(5):
        k.box(w((-0.48 + i * 0.24, 0, 0.13)), (0.1, 1.2, 0.022), "planks", (0.55, 0.5, 0.42), yaw=yaw, uv_scale=2)
    for i in range(3):
        k.box(w((0, -0.55 + i * 0.55, 0.06)), (1.0, 0.1, 0.1), "planks", (0.5, 0.45, 0.38), yaw=yaw, uv_scale=2)


def barrel(k, pos, tint=None, rust=False, col=True):
    tint = tint or pick([(0.1, 0.2, 0.45), (0.5, 0.1, 0.08), (0.12, 0.3, 0.15), (0.45, 0.45, 0.45)])
    mat = "rust" if rust else "paint_metal"
    prof = [(0.28, 0.0), (0.29, 0.02), (0.29, 0.28), (0.3, 0.29), (0.29, 0.3), (0.29, 0.58), (0.3, 0.59), (0.29, 0.6), (0.29, 0.86), (0.28, 0.88), (0.26, 0.88)]
    k.lathe(np.asarray(pos), prof, mat, tint if not rust else None, sides=16)
    k.cyl((pos[0] + 0.12, pos[1], pos[2] + 0.87), (pos[0] + 0.12, pos[1], pos[2] + 0.9), 0.03, "galv", sides=8)
    if col:
        k.collider((pos[0], pos[1], pos[2] + 0.44), (0.58, 0.58, 0.88), 0, "sheet_metal")


def gas_cylinder(k, pos):
    prof = [(0.15, 0), (0.16, 0.05), (0.16, 0.95), (0.12, 1.08), (0.04, 1.12), (0.04, 1.2)]
    k.lathe(np.asarray(pos), prof, "paint_metal", pick([(0.5, 0.45, 0.1), (0.2, 0.35, 0.6), (0.6, 0.15, 0.1)]), sides=12)
    k.cyl((pos[0], pos[1], pos[2] + 1.2), (pos[0], pos[1], pos[2] + 1.28), 0.05, "galv", sides=8)


def bollard(k, pos):
    prof = [(0.22, 0.0), (0.2, 0.05), (0.15, 0.1), (0.13, 0.35), (0.16, 0.42), (0.19, 0.5), (0.2, 0.56), (0.17, 0.6), (0.0, 0.62)]
    k.lathe(np.asarray(pos), prof, "paint_metal", (0.1, 0.1, 0.1), sides=14)
    k.box((pos[0], pos[1], pos[2] + 0.015), (0.5, 0.5, 0.03), "rust")
    k.collider((pos[0], pos[1], pos[2] + 0.3), (0.4, 0.4, 0.6), 0, "steel_target")


def tyre(k, centre, R, r=0.38, tube=0.11, sides=14):
    pts = [np.asarray(centre) + R @ np.array([math.cos(a) * r, 0, math.sin(a) * r]) for a in np.linspace(0, 2 * math.pi, sides, endpoint=False)]
    k.tube(pts, tube, "plastic", (0.05, 0.05, 0.05), sides=8, closed=True)


def rope(k, pts, r=0.02, tint=(0.5, 0.45, 0.35)):
    k.tube(pts, r, "props", tint, sides=5)


def catenary(p0, p1, sag, n=12):
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    out = []
    for i in range(n + 1):
        t = i / n
        p = p0 * (1 - t) + p1 * t
        p[2] -= sag * 4 * t * (1 - t)
        out.append(p)
    return out


def rope_coil(k, pos, r=0.35, turns=5):
    pts = []
    for i in range(turns * 14):
        a = i / 14 * 2 * math.pi
        rr = r - (i // 14) * 0.035
        pts.append((pos[0] + math.cos(a) * rr, pos[1] + math.sin(a) * rr, pos[2] + 0.03 + (i // 14) * 0.03))
    rope(k, pts, 0.028)


def net_pile(k, pos, size=1.2, tint=(0.3, 0.55, 0.45)):
    """Lumpy heap of netting with floats."""
    pts = []
    a = np.linspace(0, 2 * math.pi, 13)[:-1]
    prof = [(size * 0.5, 0.0), (size * 0.55, 0.08), (size * 0.45, 0.22), (size * 0.28, 0.36), (0.0, 0.42)]
    k.lathe(np.asarray(pos), prof, "props", tint, sides=12, R=rot_z(rnd(0, 90)))
    for i in range(7):
        ang = rnd(0, 6.28)
        rr = rnd(0.1, size * 0.45)
        p = (pos[0] + math.cos(ang) * rr, pos[1] + math.sin(ang) * rr, pos[2] + 0.42 * (1 - rr / (size * 0.55)) + 0.04)
        k.lathe(np.asarray(p), [(0.0, -0.05), (0.06, -0.03), (0.06, 0.03), (0.0, 0.05)], "plastic", pick([(0.6, 0.35, 0.05), (0.6, 0.6, 0.6), (0.55, 0.1, 0.05)]), sides=8)
    k.collider((pos[0], pos[1], pos[2] + 0.2), (size, size, 0.4), 0, "sandbag")


# ------------------------------------------------------------------ lamps and lanterns

def lantern(k, pos, r=0.22, tint=(0.75, 0.08, 0.05), energy=18.0, tassel=True, dyn=False):
    """Red paper lantern hanging from `pos` (its top)."""
    h = r * 1.9
    cx, cy, cz = pos
    base = np.array((cx, cy, cz - 0.08 - h))
    prof = [(r * 0.55, 0.0)] + [(r * math.sin(math.pi * (0.12 + 0.76 * t)), h * t) for t in np.linspace(0.04, 0.96, 9)] + [(r * 0.55, h)]
    k.lathe(base, prof, "lantern", tint, sides=14, emit=2.6, cap_top=False, cap_bottom=False)
    gold = (0.55, 0.42, 0.18)
    k.cyl(base + (0, 0, h - 0.005), base + (0, 0, h + 0.04), r * 0.58, "props", gold, sides=12)
    k.cyl(base + (0, 0, -0.04), base + (0, 0, 0.005), r * 0.58, "props", gold, sides=12)
    k.cyl(base + (0, 0, h + 0.04), (cx, cy, cz), 0.006, "galv", sides=4, caps=False)
    if tassel:
        k.cyl(base + (0, 0, -0.04), base + (0, 0, -0.06 - r * 0.9), 0.025, "lantern", tint, sides=6, emit=0.4, r1=0.04)
    light(k, base + (0, 0, h * 0.5), (1.0, 0.32, 0.16), energy, radius=r * 0.8, dyn=dyn, rng=5.0)


def lantern_string(k, p0, p1, n=5, sag=0.6, r=0.2, tint=(0.75, 0.08, 0.05), energy=10.0):
    pts = catenary(p0, p1, sag, 16)
    k.tube(pts, 0.008, "galv", (0.2, 0.2, 0.2), sides=4)
    for i in range(n):
        t = (i + 1) / (n + 1)
        idx = t * 16
        a = pts[int(idx)]
        b = pts[min(int(idx) + 1, 16)]
        p = a + (b - a) * (idx - int(idx))
        lantern(k, p, r * rnd(0.9, 1.1), tint, energy=energy, tassel=True)


def street_lamp(k, pos, yaw=0.0, height=6.5, reach=1.6):
    """Hooked sodium street lamp, arm toward local -Y."""
    R, w = frame(pos, yaw)
    k.lathe(np.asarray(pos), [(0.16, 0), (0.15, 0.3), (0.1, 0.4), (0.08, 0.5)], "paint_metal", (0.16, 0.2, 0.18), sides=10)
    k.cyl(w((0, 0, 0.4)), w((0, 0, height)), 0.07, "paint_metal", (0.16, 0.2, 0.18), sides=10, r1=0.055)
    arm = [w((0, 0, height - 0.3)), w((0, -0.4, height + 0.05)), w((0, -reach * 0.7, height + 0.15)), w((0, -reach, height + 0.1))]
    k.tube(arm, 0.045, "paint_metal", (0.16, 0.2, 0.18), sides=8)
    head = w((0, -reach - 0.25, height))
    k.box(head + (0, 0, 0.06), (0.32, 0.6, 0.14), "paint_metal", (0.16, 0.2, 0.18), yaw=yaw, chamfer=0.03)
    k.box(head - (0, 0, 0.02), (0.26, 0.5, 0.03), "emissive", (1.0, 0.55, 0.2), yaw=yaw, emit=7.0)
    light(k, head - (0, 0, 0.25), (1.0, 0.62, 0.3), 260.0, radius=0.15, kind="SPOT", spot=120, direction=(0, 0, -1), dyn=True, rng=14.0)
    k.collider(w((0, 0, 1.5)), (0.25, 0.25, 3.0), yaw, "steel_target")


def bulb(k, pos, color=(1.0, 0.75, 0.45), energy=25.0, cord=0.4, shade=None, dyn=False):
    x, y, z = pos
    k.cyl((x, y, z), (x, y, z - cord), 0.005, "plastic", (0.05, 0.05, 0.05), sides=4, caps=False)
    if shade is not None:
        k.lathe(np.array((x, y, z - cord - 0.2)), [(0.25, 0.0), (0.24, 0.02), (0.1, 0.17), (0.04, 0.2)], "paint_metal", shade, sides=14, cap_bottom=False)
    k.lathe(np.array((x, y, z - cord - 0.12)), [(0.0, -0.06), (0.035, -0.04), (0.035, 0.0), (0.015, 0.03)], "emissive", tuple(c * 0.5 for c in color), sides=8, emit=12.0)
    light(k, (x, y, z - cord - 0.14), color, energy, radius=0.04, dyn=dyn, rng=6.0)


def fluoro(k, pos, yaw=0.0, length=1.2, energy=40.0, color=(0.85, 1.0, 0.92), dyn=False, hang=0.0):
    R, w = frame(pos, yaw)
    if hang > 0:
        for s in (-1, 1):
            k.cyl(w((s * length * 0.4, 0, 0)), w((s * length * 0.4, 0, -hang)), 0.004, "galv", sides=4, caps=False)
    c = w((0, 0, -hang - 0.03))
    k.box(c, (length + 0.06, 0.12, 0.05), "galv", yaw=yaw)
    k.cyl(w((-length / 2, 0, -hang - 0.075)), w((length / 2, 0, -hang - 0.075)), 0.016, "emissive", tuple(x * 0.5 for x in color), sides=6, emit=9.0)
    light(k, w((0, 0, -hang - 0.15)), color, energy, kind="AREA", radius=length, dyn=dyn, rng=6.0)


# ------------------------------------------------------------------ building furniture

def ac_unit(k, pos, yaw=0.0, drip=True):
    """Window/split AC condenser on a bracket; pos = centre of its back face on the wall."""
    R, w = frame(pos, yaw)
    sx, sy, sz = 0.78, 0.3, 0.55
    c = w((0, -sy / 2, 0))
    k.box(c, (sx, sy, sz), "plastic", (0.45, 0.45, 0.43), yaw=yaw, chamfer=0.02)
    n = R @ np.array([0, -1.0, 0])
    x = R @ np.array([1.0, 0, 0])
    f = w((0, -sy - 0.003, 0))
    z = np.array([0, 0, 1.0])
    k.quad(f - x * sx / 2 * 0.96 - z * sz / 2 * 0.94, f + x * sx / 2 * 0.96 - z * sz / 2 * 0.94, f + x * sx / 2 * 0.96 + z * sz / 2 * 0.94, f - x * sx / 2 * 0.96 + z * sz / 2 * 0.94, "props", rect="ac_front")
    for s in (-1, 1):
        k.extrude([(-0.02, 0), (0.02, 0), (0.02, 0.03), (-0.02, 0.03)], w((s * 0.3, 0, -sz / 2 - 0.03)), w((s * 0.3, -sy - 0.05, -sz / 2 - 0.03)), "rust")
        k.tube([w((s * 0.3, 0, -sz / 2 - 0.35)), w((s * 0.3, -sy, -sz / 2 - 0.02))], 0.012, "rust", sides=4)
    if drip:
        k.tube([w((sx / 2 - 0.05, -0.1, -sz / 2)), w((sx / 2 - 0.05, -0.05, -sz / 2 - 0.4)), w((sx / 2 + 0.1, 0.0, -sz / 2 - 1.2))], 0.008, "plastic", (0.4, 0.4, 0.4), sides=4)


def drainpipe(k, x, y, z0, z1, r=0.05):
    k.cyl((x, y, z0), (x, y, z1), r, "paint_metal", (0.25, 0.25, 0.24), sides=8)
    z = z0 + 0.8
    while z < z1:
        k.cyl((x, y, z - 0.03), (x, y, z + 0.03), r + 0.012, "rust", sides=8)
        z += 2.0
    k.tube([(x, y, z0), (x, y - 0.15, z0 - 0.05), (x, y - 0.25, z0 - 0.12)], r, "paint_metal", (0.25, 0.25, 0.24), sides=8)


def awning(k, x0, x1, y, z, depth=1.4, drop=0.45, tint=(0.6, 0.12, 0.08), facing=-1, stripes=False):
    """Sloped canvas awning along x on a facade at y, projecting toward `facing` (-1 = south)."""
    yo = y + facing * depth
    zl = z - drop
    if facing < 0:
        k.quad((x0, yo, zl), (x1, yo, zl), (x1, y, z), (x0, y, z), "canvas" if not stripes else "props", tint, uv=None if not stripes else (0.5, 0.82, 1.0, 1.0))
        k.quad((x1, yo, zl), (x0, yo, zl), (x0, y, z), (x1, y, z), "canvas", tuple(c * 0.6 for c in tint))
        k.quad((x0, yo, zl - 0.25), (x1, yo, zl - 0.25), (x1, yo, zl), (x0, yo, zl), "canvas", tint, double=True)
    else:
        k.quad((x1, yo, zl), (x0, yo, zl), (x0, y, z), (x1, y, z), "canvas", tint)
        k.quad((x0, yo, zl), (x1, yo, zl), (x1, y, z), (x0, y, z), "canvas", tuple(c * 0.6 for c in tint))
        k.quad((x1, yo, zl - 0.25), (x0, yo, zl - 0.25), (x0, yo, zl), (x1, yo, zl), "canvas", tint, double=True)
    for xx in (x0 + 0.05, x1 - 0.05):
        k.tube([(xx, y, z), (xx, yo, zl)], 0.015, "galv", sides=4)
        k.tube([(xx, y, z - 0.7), (xx, yo, zl)], 0.012, "galv", sides=4)


def laundry(k, p0, p1, sag=0.15):
    pts = catenary(p0, p1, sag, 8)
    k.tube(pts, 0.006, "plastic", (0.6, 0.6, 0.6), sides=3)
    L = np.linalg.norm(np.asarray(p1) - np.asarray(p0))
    d = (np.asarray(p1) - np.asarray(p0)) / L
    t = 0.15
    while t < L - 0.4:
        w_ = rnd(0.3, 0.6)
        hgt = rnd(0.4, 0.8)
        frac = (t + w_ / 2) / L
        p = np.asarray(p0) + d * t
        p[2] -= sag * 4 * frac * (1 - frac)
        q = p + d * w_
        tint = pick([(0.7, 0.7, 0.68), (0.2, 0.3, 0.55), (0.6, 0.15, 0.12), (0.55, 0.5, 0.2), (0.25, 0.45, 0.3), (0.65, 0.4, 0.5)])
        k.quad(p - (0, 0, hgt), q - (0, 0, hgt), q, p, "canvas", tint, double=True)
        t += w_ + rnd(0.05, 0.25)


def window_cage(k, x0, x1, y, z0, z1, facing=-1):
    """Hong Kong style window cage: a steel grille box bolted over a window."""
    d = 0.45 * facing
    tint = (0.22, 0.24, 0.22)
    for xx in np.linspace(x0, x1, int((x1 - x0) / 0.15) + 1):
        k.cyl((xx, y + d, z0), (xx, y + d, z1), 0.008, "paint_metal", tint, sides=4, caps=False)
    for zz in (z0, z1, (z0 + z1) / 2):
        k.cyl((x0, y + d, zz), (x1, y + d, zz), 0.012, "paint_metal", tint, sides=4, caps=False)
        for xx in (x0, x1):
            k.cyl((xx, y, zz), (xx, y + d, zz), 0.012, "paint_metal", tint, sides=4, caps=False)
    k.box(((x0 + x1) / 2, y + d / 2, z0 - 0.02), (x1 - x0, abs(d), 0.03), "paint_metal", tint)
    # pots and boxes on the cage floor
    for i in range(int(RNG.integers(0, 3))):
        xx = rnd(x0 + 0.2, x1 - 0.2)
        k.lathe(np.array((xx, y + d / 2, z0)), [(0.08, 0), (0.11, 0.18), (0.0, 0.18)], "plastic", pick([(0.5, 0.25, 0.15), (0.4, 0.4, 0.4)]), sides=8)
        k.lathe(np.array((xx, y + d / 2, z0 + 0.18)), [(0.0, 0), (0.18, 0.1), (0.12, 0.28), (0.0, 0.32)], "canvas", (0.12, 0.28, 0.1), sides=7)


# ------------------------------------------------------------------ street furniture

def hydrant(k, pos):
    prof = [(0.14, 0), (0.12, 0.05), (0.1, 0.08), (0.1, 0.55), (0.12, 0.58), (0.11, 0.62), (0.07, 0.72), (0.03, 0.78)]
    k.lathe(np.asarray(pos), prof, "paint_metal", (0.6, 0.6, 0.1), sides=12)
    for yaw in (0, 180):
        R = rot_z(yaw)
        a = np.asarray(pos) + R @ np.array([0.08, 0, 0.45])
        b = np.asarray(pos) + R @ np.array([0.18, 0, 0.45])
        k.cyl(a, b, 0.04, "paint_metal", (0.6, 0.6, 0.1), sides=8)
    k.collider((pos[0], pos[1], pos[2] + 0.38), (0.3, 0.3, 0.76), 0, "steel_target")


def trash_bin(k, pos, tint=(0.15, 0.3, 0.18)):
    prof = [(0.24, 0), (0.27, 0.9), (0.29, 0.92), (0.29, 0.98), (0.0, 1.0)]
    k.lathe(np.asarray(pos), prof, "plastic", tint, sides=12)
    k.collider((pos[0], pos[1], pos[2] + 0.5), (0.56, 0.56, 1.0), 0, "thin_metal")


def trash_bags(k, pos, n=4):
    for i in range(n):
        p = (pos[0] + rnd(-0.5, 0.5), pos[1] + rnd(-0.4, 0.4), pos[2])
        s = rnd(0.25, 0.38)
        prof = [(s * 0.7, 0), (s, s * 0.4), (s * 0.9, s * 0.9), (s * 0.4, s * 1.25), (s * 0.12, s * 1.4), (s * 0.06, s * 1.55)]
        k.lathe(np.asarray(p), prof, "plastic", pick([(0.04, 0.04, 0.045), (0.05, 0.05, 0.06), (0.3, 0.28, 0.1)]), sides=9, R=rot_z(rnd(0, 360)) @ rot_x(rnd(-12, 12)))
    k.collider((pos[0], pos[1], pos[2] + 0.25), (1.3, 1.1, 0.5), 0, "sandbag")


def dumpster(k, pos, yaw=0.0, tint=(0.12, 0.28, 0.16)):
    R, w = frame(pos, yaw)
    sx, sy, sz = 1.9, 1.1, 1.15
    k.box(w((0, 0, 0.2 + sz / 2)), (sx, sy, sz), "paint_metal", tint, yaw=yaw, chamfer=0.03)
    k.box(w((0, -0.05, 0.2 + sz + 0.04)), (sx + 0.06, sy + 0.1, 0.06), "plastic", (0.06, 0.06, 0.06), yaw=yaw)
    for i in (-1, 0, 1):
        k.box(w((i * 0.6, -sy / 2 - 0.02, 0.2 + sz * 0.55)), (0.06, 0.05, sz * 0.8), "paint_metal", tint, yaw=yaw)
    k.box(w((0, -sy / 2 - 0.03, 0.2 + sz - 0.08)), (sx, 0.06, 0.1), "paint_metal", tint, yaw=yaw)
    for ix in (-1, 1):
        for iy in (-1, 1):
            c = w((ix * (sx / 2 - 0.15), iy * (sy / 2 - 0.15), 0.09))
            k.cyl(c - R @ np.array([0.03, 0, 0]), c + R @ np.array([0.03, 0, 0]), 0.09, "plastic", (0.05, 0.05, 0.05), sides=10)
    k.collider(w((0, 0, 0.2 + sz / 2)), (sx, sy, sz + 0.2), yaw, "sheet_metal")


def jersey(k, pos, yaw=0.0, tint=(0.5, 0.5, 0.5)):
    R, w = frame(pos, yaw)
    prof = [(-0.3, 0), (0.3, 0), (0.3, 0.08), (0.15, 0.3), (0.1, 0.81), (-0.1, 0.81), (-0.15, 0.3), (-0.3, 0.08)]
    k.extrude(prof, w((-1.0, 0, 0)), w((1.0, 0, 0)), "concrete", tint, up=(0, 0, 1))
    k.collider(w((0, 0, 0.4)), (2.0, 0.6, 0.81), yaw, "concrete")


def cone(k, pos):
    k.box((pos[0], pos[1], pos[2] + 0.015), (0.36, 0.36, 0.03), "plastic", (0.06, 0.06, 0.06))
    k.lathe(np.asarray(pos), [(0.14, 0.03), (0.03, 0.7), (0.0, 0.72)], "plastic", (0.7, 0.25, 0.04), sides=10)


def produce_stand(k, pos, yaw=0.0):
    """Sloped stand of crates of oranges, cabbages and lychees outside the grocery."""
    R, w = frame(pos, yaw)
    k.box(w((0, 0, 0.35)), (2.2, 0.9, 0.7), "darkwood", (0.6, 0.55, 0.5), yaw=yaw, col="wood")
    fruit = [((0.6, 0.27, 0.04), 0.04), ((0.3, 0.45, 0.15), 0.07), ((0.45, 0.08, 0.06), 0.025), ((0.62, 0.55, 0.1), 0.035)]
    for i in range(4):
        cx = -0.82 + i * 0.55
        for row in range(2):
            base = w((cx, -0.2 + row * 0.38, 0.7 + row * 0.12))
            k.box(base + (0, 0, 0.06), (0.5, 0.36, 0.12), "planks", (0.55, 0.48, 0.38), yaw=yaw)
            tint, r = fruit[(i + row) % 4]
            nx, ny = int(0.42 / (r * 2)), int(0.28 / (r * 2))
            for a in range(nx):
                for b in range(ny):
                    p = base + R @ np.array([-0.21 + r + a * r * 2, -0.14 + r + b * r * 2, 0.12 + r * 0.8])
                    k.lathe(p - (0, 0, r), [(0.0, 0), (r * 0.8, r * 0.3), (r, r), (r * 0.8, r * 1.7), (0.0, r * 2)], "plastic",
                            tuple(c * rnd(0.85, 1.1) for c in tint), sides=6)


def bicycle(k, pos, yaw=0.0):
    R, w = frame(pos, yaw)
    t = (0.08, 0.08, 0.08)
    for x in (-0.52, 0.52):
        pts = [w((x + math.cos(a) * 0.33, 0, 0.34 + math.sin(a) * 0.33)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        k.tube(pts, 0.02, "plastic", (0.03, 0.03, 0.03), sides=5, closed=True)
    fr = [w((-0.52, 0, 0.34)), w((-0.05, 0, 0.36)), w((0.42, 0, 0.82)), w((0.52, 0, 0.34))]
    k.tube(fr, 0.016, "paint_metal", (0.12, 0.3, 0.45), sides=5)
    k.tube([w((-0.05, 0, 0.36)), w((-0.2, 0, 0.82)), w((0.42, 0, 0.82))], 0.016, "paint_metal", (0.12, 0.3, 0.45), sides=5)
    k.tube([w((-0.52, 0, 0.34)), w((-0.2, 0, 0.82))], 0.012, "paint_metal", (0.12, 0.3, 0.45), sides=5)
    k.box(w((-0.22, 0, 0.88)), (0.22, 0.09, 0.05), "plastic", t, yaw=yaw)
    k.tube([w((0.42, -0.25, 0.98)), w((0.42, 0, 0.95)), w((0.42, 0.25, 0.98))], 0.012, "galv", sides=5)
    k.box(w((0.62, 0, 0.75)), (0.3, 0.32, 0.22), "plastic", (0.45, 0.42, 0.3), yaw=yaw)  # basket


def newspaper_stand(k, pos, yaw=0.0):
    R, w = frame(pos, yaw)
    k.box(w((0, 0, 0.6)), (1.2, 0.5, 1.2), "paint_metal", (0.12, 0.25, 0.12), yaw=yaw, col="thin_metal")
    for i in range(4):
        p = w((-0.42 + i * 0.28, -0.26, 0.9))
        x = R @ np.array([1.0, 0, 0])
        k.quad(p - x * 0.12 + (0, 0, -0.17) + R @ np.array([0, 0, 0]), p + x * 0.12 + (0, 0, -0.17), p + x * 0.12 + (0, 0, 0.17), p - x * 0.12 + (0, 0, 0.17), "props", rect="newspaper")
    k.box(w((0, 0.05, 1.25)), (1.4, 0.75, 0.05), "paint_metal", (0.12, 0.25, 0.12), yaw=yaw)


# ------------------------------------------------------------------ market

def fish(k, pos, yaw, length, species, lying=True):
    """A fish on its side (lying) as a lofted body with tail fin, mapped to its skin rect."""
    R, w = frame(pos, yaw)
    u0, v0, u1, v1 = k.rect("props", species)
    n_len, n_rad = 7, 8
    L = length
    hmax = L * (0.32 if species == "fish_pomfret" else 0.22)
    wmax = L * 0.07
    verts, uvs_v = [], []
    for i in range(n_len + 1):
        t = i / n_len
        x = -L / 2 + t * L * 0.84
        prof = math.sin(math.pi * min(1.0, (t * 0.96 + 0.04))) ** 0.7
        hh, ww = hmax * prof / 2, wmax * prof
        for j in range(n_rad):
            a = j / n_rad * 2 * math.pi
            verts.append((x, math.sin(a) * ww, math.cos(a) * hh))
    faces, uvs = [], []
    for i in range(n_len):
        for j in range(n_rad):
            a, b = i * n_rad + j, i * n_rad + (j + 1) % n_rad
            c, d = (i + 1) * n_rad + (j + 1) % n_rad, (i + 1) * n_rad + j
            faces.append([a, b, c, d])
            fu = []
            for vi in (a, b, c, d):
                vx, vy, vz = verts[vi]
                uu = u0 + (vx + L / 2) / L * (u1 - u0)
                vv = v0 + (0.5 - vz / (hmax * 1.1)) * (v1 - v0)
                fu.append((uu, 1.0 - vv))
            uvs.append(fu)
    tail0 = len(verts)
    xt = -L / 2 + L * 0.84
    verts += [(xt, 0, 0), (L / 2, 0, hmax * 0.4), (L / 2, 0, -hmax * 0.4)]
    faces.append([tail0, tail0 + 1, tail0 + 2])
    uvs.append([(u0 + 0.9 * (u1 - u0), 1 - (v0 + 0.5 * (v1 - v0))), (u1, 1 - v0), (u1, 1 - v1)])
    faces.append([tail0, tail0 + 2, tail0 + 1])
    uvs.append([(u0 + 0.9 * (u1 - u0), 1 - (v0 + 0.5 * (v1 - v0))), (u1, 1 - v1), (u1, 1 - v0)])
    verts = np.array(verts)
    if lying:
        Rl = R @ rot_x(90 + rnd(-10, 10))
        T = np.asarray(pos) + (0, 0, wmax * 0.8)
    else:
        Rl = R
        T = np.asarray(pos)
    k.mesh(verts, faces, Rl, T, "props", uvs=[np.array(u) for u in uvs], smooth=True)


def stall(k, pos, yaw=0.0, length=3.0, depth=1.2, species=None):
    """Market stall: stainless table, ice bed with fish in rows, price tags, boxes under."""
    R, w = frame(pos, yaw)
    top = 0.88
    k.box(w((0, 0, top - 0.02)), (length, depth, 0.04), "galv", yaw=yaw, chamfer=0.01)
    k.box(w((0, -depth / 2 + 0.02, top + 0.05)), (length, 0.03, 0.14), "galv", yaw=yaw)
    k.box(w((0, depth / 2 - 0.02, top + 0.05)), (length, 0.03, 0.14), "galv", yaw=yaw)
    for ix in (-1, 1):
        for iy in (-1, 1):
            k.cyl(w((ix * (length / 2 - 0.08), iy * (depth / 2 - 0.08), 0)), w((ix * (length / 2 - 0.08), iy * (depth / 2 - 0.08), top - 0.04)), 0.025, "galv", sides=8)
    k.box(w((0, 0, 0.18)), (length - 0.1, depth - 0.1, 0.02), "galv", yaw=yaw)  # shelf
    # crushed ice: a lumpy slab
    k.box(w((0, 0, top + 0.04)), (length - 0.08, depth - 0.08, 0.06), "props", (0.55, 0.55, 0.55), yaw=yaw)
    k.extrude([(-depth / 2 + 0.06, 0), (depth / 2 - 0.06, 0), (depth / 2 - 0.2, 0.08), (-depth / 2 + 0.2, 0.08)], w((-length / 2 + 0.06, 0, top + 0.07)), w((length / 2 - 0.06, 0, top + 0.07)), "props", (0.55, 0.55, 0.55))
    species = species or ["fish_mackerel", "fish_snapper", "fish_grouper", "fish_pomfret"]
    nsec = max(1, int(length / 0.75))
    for s in range(nsec):
        sp = species[s % len(species)]
        x0 = -length / 2 + (s + 0.5) * length / nsec
        size = {"fish_mackerel": 0.32, "fish_snapper": 0.4, "fish_grouper": 0.5, "fish_pomfret": 0.25}[sp]
        for r in range(3):
            for c in range(2):
                p = w((x0 + (c - 0.5) * size * 0.55 + rnd(-0.03, 0.03), -depth / 2 + 0.25 + r * (depth - 0.4) / 2, top + 0.11 + rnd(0, 0.03)))
                fish(k, p, yaw + 90 + rnd(-15, 15) + (180 if c else 0), size * rnd(0.85, 1.1), sp)
        # price tag on a stick
        tag = w((x0, -depth / 2 + 0.05, top + 0.28))
        x = R @ np.array([1.0, 0, 0])
        z = np.array([0, 0, 1.0])
        k.quad(tag - x * 0.08 - z * 0.08, tag + x * 0.08 - z * 0.08, tag + x * 0.08 + z * 0.08, tag - x * 0.08 + z * 0.08, "signs_b", rect="tag%d" % int(RNG.integers(0, 8)), double=True)
        k.cyl(tag - z * 0.08, tag - z * 0.2, 0.004, "darkwood", sides=3, caps=False)
    for i in range(int(length / 0.7)):
        styro_box(k, w((-length / 2 + 0.4 + i * 0.68, 0, 0.2)), yaw + rnd(-4, 4), lid=bool(RNG.integers(0, 2)), col=False)
    k.collider(w((0, 0, top / 2 + 0.05)), (length, depth, top + 0.1), yaw, "thin_metal")


def seafood_tank(k, pos, yaw=0.0, length=1.6):
    """Aerated tank of live seafood: glass box glowing blue, bubbles, crabs as lumps."""
    R, w = frame(pos, yaw)
    h = 0.7
    k.box(w((0, 0, 0.3)), (length, 0.7, 0.6), "galv", yaw=yaw, col="thin_metal")
    k.box(w((0, 0, 0.6 + h / 2)), (length - 0.04, 0.66, h - 0.06), "emissive", (0.12, 0.35, 0.5), yaw=yaw, emit=1.6)
    k.box(w((0, 0, 0.6 + h - 0.02)), (length, 0.7, 0.04), "galv", yaw=yaw)
    for i in range(6):
        p = w((rnd(-length / 2 + 0.15, length / 2 - 0.15), rnd(-0.25, 0.25), 0.62))
        k.lathe(np.asarray(p), [(0.0, 0), (0.09, 0.02), (0.07, 0.06), (0.0, 0.07)], "plastic", (0.45, 0.12, 0.05), sides=7)
    k.tube([w((length / 2 - 0.1, 0.2, 0.6 + h)), w((length / 2 - 0.1, 0.2, 0.6 + h + 0.3)), w((length / 2 + 0.1, 0.25, 0.6 + h + 0.35))], 0.008, "plastic", (0.6, 0.6, 0.6), sides=4)
    light(k, w((0, -0.5, 0.9)), (0.3, 0.7, 1.0), 12.0, radius=0.3)


def hand_trolley(k, pos, yaw=0.0):
    R, w = frame(pos, yaw)
    k.tube([w((-0.2, 0, 0.1)), w((-0.2, 0.15, 1.2)), w((0.2, 0.15, 1.2)), w((0.2, 0, 0.1))], 0.016, "paint_metal", (0.5, 0.12, 0.08), sides=5)
    k.box(w((0, -0.12, 0.03)), (0.45, 0.25, 0.02), "paint_metal", (0.5, 0.12, 0.08), yaw=yaw)
    for s in (-1, 1):
        c = w((s * 0.25, 0.05, 0.12))
        k.cyl(c - R @ np.array([0.03, 0, 0]), c + R @ np.array([0.03, 0, 0]), 0.12, "plastic", (0.04, 0.04, 0.04), sides=10)


def hose(k, pts):
    k.tube(pts, 0.022, "plastic", (0.08, 0.3, 0.14), sides=5)


def scale_hanging(k, pos):
    x, y, z = pos
    k.cyl((x, y, z), (x, y, z - 0.4), 0.004, "galv", sides=3, caps=False)
    k.lathe(np.array((x, y, z - 0.62)), [(0.0, 0.0), (0.12, 0.0), (0.12, 0.03), (0.13, 0.2), (0.0, 0.22)], "paint_metal", (0.55, 0.12, 0.1), sides=12, R=rot_x(90))
    k.lathe(np.array((x, y, z - 0.95)), [(0.0, 0.0), (0.2, 0.02), (0.22, 0.06)], "galv", sides=12, cap_top=False)


# ------------------------------------------------------------------ vehicles

def van(k, pos, yaw=0.0, tint=(0.62, 0.62, 0.6)):
    """Small boxy delivery van (Toyota HiAce-ish proportions, unbranded)."""
    R, w = frame(pos, yaw)
    L, W, H = 4.7, 1.7, 1.95
    k.box(w((0.25, 0, 0.35 + (H - 0.35) / 2)), (L - 0.5, W, H - 0.35), "paint_metal", tint, yaw=yaw, chamfer=0.06)
    k.box(w((-L / 2 + 0.25, 0, 0.75)), (0.5, W, 0.8), "paint_metal", tint, yaw=yaw, chamfer=0.08)  # nose
    # windscreen and side windows
    xw = -L / 2 + 0.53
    Rw = R @ rot_y(-12)
    k.box(w((xw, 0, 1.55)), (0.04, W - 0.12, 0.62), "glass", yaw=yaw, R=Rw)
    for s in (-1, 1):
        k.box(w((-L / 2 + 1.0, s * (W / 2 + 0.002), 1.5)), (0.75, 0.01, 0.5), "glass", yaw=yaw)
        k.box(w((0.7, s * (W / 2 + 0.002), 1.45)), (2.0, 0.01, 0.38), "glass", yaw=yaw)
        for x in (-L / 2 + 0.8, L / 2 - 0.75):
            c = w((x, s * (W / 2 - 0.12), 0.32))
            k.cyl(c - R @ np.array([0, 0.12, 0]), c + R @ np.array([0, 0.12, 0]), 0.32, "plastic", (0.04, 0.04, 0.04), sides=12)
            k.cyl(c + R @ np.array([0, s * 0.121, 0]), c + R @ np.array([0, s * 0.125, 0]), 0.18, "galv", sides=10)
    k.box(w((-L / 2 - 0.02, 0, 0.45)), (0.08, W + 0.04, 0.18), "plastic", (0.06, 0.06, 0.06), yaw=yaw)
    k.box(w((L / 2 + 0.02, 0, 0.45)), (0.08, W + 0.04, 0.18), "plastic", (0.06, 0.06, 0.06), yaw=yaw)
    for s in (-1, 1):
        k.box(w((-L / 2 + 0.01, s * 0.62, 0.78)), (0.03, 0.22, 0.14), "emissive", (0.9, 0.85, 0.7), yaw=yaw, emit=1.2)
        k.box(w((L / 2 - 0.01, s * 0.7, 0.9)), (0.03, 0.12, 0.3), "emissive", (0.6, 0.05, 0.03), yaw=yaw, emit=0.8)
    k.collider(w((0, 0, 1.0)), (L, W, H - 0.1), yaw, "sheet_metal")


def box_truck(k, pos, yaw=0.0, tint=(0.62, 0.62, 0.6), box_tint=(0.6, 0.58, 0.55)):
    R, w = frame(pos, yaw)
    k.box(w((-2.4, 0, 1.25)), (1.6, 2.1, 1.7), "paint_metal", tint, yaw=yaw, chamfer=0.08)
    k.box(w((-3.22, 0, 1.45)), (0.04, 1.9, 0.75), "glass", yaw=yaw)
    for s in (-1, 1):
        k.box(w((-2.5, s * 1.052, 1.65)), (0.9, 0.01, 0.6), "glass", yaw=yaw)
    k.box(w((1.0, 0, 1.9)), (5.0, 2.3, 2.6), "corrugated", box_tint, yaw=yaw, uv_scale=1.0)
    k.box(w((0.0, 0, 0.55)), (6.6, 1.0, 0.25), "paint_metal", (0.08, 0.08, 0.08), yaw=yaw)
    for x in (-2.4, 0.9, 2.1):
        for s in (-1, 1):
            c = w((x, s * 0.92, 0.45))
            k.cyl(c - R @ np.array([0, 0.15, 0]), c + R @ np.array([0, 0.15, 0]), 0.45, "plastic", (0.04, 0.04, 0.04), sides=14)
            k.cyl(c + R @ np.array([0, s * 0.151, 0]), c + R @ np.array([0, s * 0.155, 0]), 0.26, "galv", sides=10)
    k.collider(w((1.0, 0, 1.9)), (5.0, 2.3, 2.6), yaw, "sheet_metal")
    k.collider(w((-2.4, 0, 1.2)), (1.7, 2.1, 1.9), yaw, "sheet_metal")


def container(k, pos, yaw=0.0, tint=(0.45, 0.12, 0.08), length=6.06):
    R, w = frame(pos, yaw)
    W, H = 2.44, 2.59
    k.box(w((0, 0, H / 2)), (length - 0.1, W - 0.06, H - 0.12), "corrugated", tint, yaw=yaw, R=R @ rot_x(90) if False else None)
    # frame: corner posts and rails
    for ix in (-1, 1):
        for iy in (-1, 1):
            k.box(w((ix * (length / 2 - 0.08), iy * (W / 2 - 0.08), H / 2)), (0.16, 0.16, H), "paint_metal", tint, yaw=yaw)
            k.box(w((ix * (length / 2 - 0.09), iy * (W / 2 - 0.09), 0.06)), (0.18, 0.18, 0.12), "rust", yaw=yaw)
            k.box(w((ix * (length / 2 - 0.09), iy * (W / 2 - 0.09), H - 0.06)), (0.18, 0.18, 0.12), "rust", yaw=yaw)
    for z in (0.06, H - 0.06):
        for iy in (-1, 1):
            k.box(w((0, iy * (W / 2 - 0.05), z)), (length, 0.1, 0.12), "paint_metal", tint, yaw=yaw)
    # door end: bars and handles
    for iy in (-0.75, -0.3, 0.3, 0.75):
        k.cyl(w((length / 2 + 0.02, iy, 0.15)), w((length / 2 + 0.02, iy, H - 0.15)), 0.02, "galv", sides=6)
    k.collider(w((0, 0, H / 2)), (length, W, H), yaw, "sheet_metal")


# ------------------------------------------------------------------ interiors

def round_table(k, pos, seats=6, cloth=(0.55, 0.06, 0.05)):
    x, y, z = pos
    k.lathe(np.array(pos), [(0.25, 0), (0.06, 0.05), (0.04, 0.72)], "darkwood", sides=10)
    k.lathe(np.array((x, y, z + 0.72)), [(0.0, 0.0), (0.72, 0.0), (0.74, -0.25), (0.75, -0.26), (0.76, 0.03), (0.0, 0.04)], "canvas", cloth, sides=20)
    k.lathe(np.array((x, y, z + 0.76)), [(0.0, 0.0), (0.4, 0.0), (0.4, 0.02), (0.0, 0.025)], "glass", sides=16)  # lazy susan
    for i in range(seats):
        a = i / seats * 2 * math.pi + rnd(-0.1, 0.1)
        cp = (x + math.cos(a) * 1.0, y + math.sin(a) * 1.0, z)
        chair(k, cp, math.degrees(a) + 90 + rnd(-8, 8))
        # bowl and chopsticks
        bp = np.array((x + math.cos(a) * 0.55, y + math.sin(a) * 0.55, z + 0.76))
        k.lathe(bp, [(0.0, 0), (0.035, 0.0), (0.06, 0.05), (0.055, 0.052), (0.0, 0.01)], "plastic", (0.62, 0.62, 0.6), sides=8, cap_top=False)
    for i in range(3):
        a = rnd(0, 6.28)
        k.lathe(np.array((x + math.cos(a) * 0.2, y + math.sin(a) * 0.2, z + 0.785)), [(0.0, 0), (0.14, 0.0), (0.16, 0.03), (0.0, 0.01)], "plastic", (0.62, 0.62, 0.6), sides=12)
    k.collider((x, y, z + 0.38), (1.4, 1.4, 0.76), 0, "wood")


def chair(k, pos, yaw):
    R, w = frame(pos, yaw)
    t = (0.5, 0.12, 0.08)
    k.box(w((0, 0, 0.45)), (0.42, 0.42, 0.05), "lacquer", t, yaw=yaw, chamfer=0.01)
    for ix in (-1, 1):
        for iy in (-1, 1):
            k.box(w((ix * 0.18, iy * 0.18, 0.22)), (0.035, 0.035, 0.45), "lacquer", t, yaw=yaw)
    for ix in (-1, 1):
        k.box(w((ix * 0.18, 0.19, 0.7)), (0.035, 0.035, 0.5), "lacquer", t, yaw=yaw)
    k.box(w((0, 0.19, 0.85)), (0.4, 0.03, 0.12), "lacquer", t, yaw=yaw)


def roast_rack(k, x0, x1, y, z, n=5):
    k.cyl((x0, y, z), (x1, y, z), 0.012, "galv", sides=6)
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        k.cyl((x, y, z), (x, y, z - 0.12), 0.003, "galv", sides=3, caps=False)
        if i % 2 == 0:
            prof = [(0.0, 0.0), (0.06, 0.04), (0.12, 0.16), (0.13, 0.3), (0.09, 0.42), (0.03, 0.5), (0.0, 0.52)]
            k.lathe(np.array((x, y, z - 0.64)), prof, "props", (0.5, 0.5, 0.5), sides=9, R=rot_z(rnd(0, 360)))
        else:
            k.box((x, y, z - 0.3), (0.06, 0.08, 0.32), "props", (0.5, 0.5, 0.5))


def fish_tank_wall(k, x0, x1, y, z0, facing=-1):
    """Restaurant display tanks: stacked glowing tanks with fish."""
    L = x1 - x0
    for row in range(2):
        zc = z0 + 0.45 + row * 0.62
        k.box(((x0 + x1) / 2, y, zc), (L, 0.6, 0.55), "emissive", (0.1, 0.3, 0.42), emit=1.4)
        k.box(((x0 + x1) / 2, y, zc + 0.3), (L + 0.04, 0.64, 0.05), "galv")
        for i in range(int(L / 0.5)):
            p = (x0 + 0.3 + i * 0.5 + rnd(-0.1, 0.1), y + facing * 0.31, zc + rnd(-0.12, 0.12))
            fish(k, p, 90 * facing + rnd(-20, 20), rnd(0.25, 0.4), pick(["fish_grouper", "fish_snapper"]), lying=False)
    k.box(((x0 + x1) / 2, y, z0 + 0.1), (L + 0.04, 0.64, 0.2), "galv")
    light(k, ((x0 + x1) / 2, y + facing * 0.8, z0 + 0.9), (0.3, 0.75, 1.0), 25.0, radius=0.4)
    k.collider(((x0 + x1) / 2, y, z0 + 0.7), (L, 0.64, 1.4), 0, "glass")


def counter(k, x0, x1, y, depth=0.6, height=1.05, front=(0.5, 0.12, 0.08)):
    k.box(((x0 + x1) / 2, y, height / 2), (x1 - x0, depth, height), "lacquer", front, col="wood")
    k.box(((x0 + x1) / 2, y, height + 0.02), (x1 - x0 + 0.06, depth + 0.06, 0.04), "stone", (0.4, 0.38, 0.36))


def wok_station(k, pos, yaw=0.0, length=2.4):
    R, w = frame(pos, yaw)
    k.box(w((0, 0, 0.45)), (length, 0.8, 0.9), "galv", yaw=yaw, col="thin_metal")
    for i in range(int(length / 0.8)):
        c = w((-length / 2 + 0.4 + i * 0.8, 0, 0.9))
        k.lathe(c, [(0.0, 0.02), (0.18, 0.08), (0.24, 0.16), (0.25, 0.17)], "rust", sides=14, cap_top=False)
        k.cyl(c + R @ np.array([0.25, 0, 0.15]), c + R @ np.array([0.45, 0, 0.2]), 0.012, "darkwood", sides=4)
        k.lathe(c - (0, 0, 0.0), [(0.12, -0.02), (0.15, 0.0)], "emissive", (0.2, 0.4, 0.9), sides=10, emit=2.0, cap_top=False)
    # extraction hood
    k.box(w((0, 0.1, 2.1)), (length + 0.2, 1.0, 0.5), "galv", yaw=yaw)
    k.box(w((0, 0.3, 2.8)), (0.5, 0.5, 0.9), "galv", yaw=yaw)


def shelf_unit(k, pos, yaw=0.0, w_=1.2, h=2.0, d=0.4, goods=True, mat="darkwood"):
    R, w = frame(pos, yaw)
    for s in (-1, 1):
        k.box(w((s * w_ / 2, 0, h / 2)), (0.03, d, h), mat, yaw=yaw)
    for i in range(5):
        z = 0.1 + i * (h - 0.15) / 4
        k.box(w((0, 0, z)), (w_, d, 0.025), mat, yaw=yaw)
        if goods and i < 4:
            x = -w_ / 2 + 0.06
            while x < w_ / 2 - 0.1:
                kind = int(RNG.integers(0, 4))
                if kind == 0:  # jars
                    r = rnd(0.04, 0.06)
                    k.lathe(w((x + r, 0, z + 0.013)), [(r, 0), (r, r * 3), (r * 0.6, r * 3.4), (r * 0.6, r * 3.8)], "glass", sides=8)
                    k.cyl(w((x + r, 0, z + 0.013 + r * 3.8)), w((x + r, 0, z + 0.03 + r * 3.8)), r * 0.62, "plastic", pick([(0.6, 0.1, 0.08), (0.6, 0.5, 0.1)]), sides=8)
                    x += r * 2 + 0.02
                elif kind == 1:  # boxes
                    bw = rnd(0.12, 0.25)
                    bh = rnd(0.12, (h - 0.15) / 4 - 0.05)
                    k.box(w((x + bw / 2, 0, z + 0.013 + bh / 2)), (bw, d * 0.8, bh), "props", pick([(0.5, 0.5, 0.5)]), yaw=yaw)
                    x += bw + 0.02
                elif kind == 2:  # tins
                    r = 0.04
                    for j in range(2):
                        k.cyl(w((x + r, 0, z + 0.013 + j * 0.11)), w((x + r, 0, z + 0.013 + j * 0.11 + 0.1)), r, "plastic", pick([(0.6, 0.15, 0.1), (0.15, 0.3, 0.5), (0.6, 0.55, 0.2)]), sides=8)
                    x += r * 2 + 0.02
                else:  # bags of dried goods
                    bw = rnd(0.15, 0.25)
                    k.lathe(w((x + bw / 2, 0, z + 0.013)), [(bw / 2, 0), (bw / 2 * 1.05, 0.08), (bw / 2 * 0.7, 0.18), (0.02, 0.22)], "canvas", pick([(0.6, 0.5, 0.35), (0.5, 0.15, 0.1), (0.55, 0.55, 0.5)]), sides=7)
                    x += bw + 0.02
    k.collider(w((0, 0, h / 2)), (w_, d, h), yaw, "wood")


def fire_escape(k, x0, x1, y, floors, z_first=4.0, floor_h=3.0, facing=1, ladder_to_ground=False):
    """Steel balconies with grating floors and stairs between them on a back facade."""
    d = 1.2 * facing
    tint = (0.18, 0.18, 0.17)
    for f in range(floors):
        z = z_first + f * floor_h
        k.box(((x0 + x1) / 2, y + d / 2, z), (x1 - x0, abs(d), 0.05), "grate", uv_scale=1.0)
        for xx in np.arange(x0, x1 + 0.01, 0.12):
            k.cyl((xx, y + d, z), (xx, y + d, z + 1.0), 0.008, "paint_metal", tint, sides=3, caps=False)
        k.cyl((x0, y + d, z + 1.0), (x1, y + d, z + 1.0), 0.025, "paint_metal", tint, sides=6)
        k.cyl((x0, y + d, z + 0.05), (x1, y + d, z + 0.05), 0.02, "paint_metal", tint, sides=6)
        for xx in (x0, x1):
            k.cyl((xx, y, z + 1.0), (xx, y + d, z + 1.0), 0.025, "paint_metal", tint, sides=6)
            k.tube([(xx, y, z - 0.9), (xx, y + d, z - 0.02)], 0.02, "paint_metal", tint, sides=5)
        if f < floors - 1:
            # stair to the next floor, along x
            sx0, sx1 = x0 + 0.3, x0 + 0.3 + floor_h * 0.9
            k.tube([(sx0, y + d * 0.5, z), (sx1, y + d * 0.5, z + floor_h)], 0.02, "paint_metal", tint, sides=5)
            for i in range(12):
                t = (i + 0.5) / 12
                k.box((sx0 + (sx1 - sx0) * t, y + d * 0.5, z + floor_h * t), (0.22, abs(d) * 0.7, 0.03), "grate")
    if ladder_to_ground:
        xl = x1 - 0.4
        for s in (-0.2, 0.2):
            k.cyl((xl + s, y + d * 0.8, 1.8), (xl + s, y + d * 0.8, z_first), 0.02, "paint_metal", tint, sides=5)
        for zz in np.arange(1.9, z_first, 0.3):
            k.cyl((xl - 0.2, y + d * 0.8, zz), (xl + 0.2, y + d * 0.8, zz), 0.012, "paint_metal", tint, sides=4)


def water_tank(k, pos):
    x, y, z = pos
    for dx in (-0.6, 0.6):
        for dy in (-0.6, 0.6):
            k.box((x + dx, y + dy, z + 0.5), (0.1, 0.1, 1.0), "rust")
    k.box((x, y, z + 1.02), (1.5, 1.5, 0.05), "rust")
    k.lathe(np.array((x, y, z + 1.05)), [(0.8, 0), (0.8, 1.6), (0.6, 1.8), (0.0, 1.9)], "rust", sides=16)


def antenna(k, pos, h=3.0):
    x, y, z = pos
    k.cyl((x, y, z), (x, y, z + h), 0.02, "galv", sides=4)
    for i in range(5):
        zz = z + h * 0.5 + i * 0.25
        w_ = 0.8 - i * 0.12
        k.cyl((x - w_, y, zz), (x + w_, y, zz), 0.008, "galv", sides=3, caps=False)
    k.tube([(x, y, z + h * 0.8), (x + 2.0, y + 1.0, z)], 0.004, "galv", sides=3)


def potted_plant(k, pos, size=1.0):
    x, y, z = pos
    k.lathe(np.array(pos), [(0.14 * size, 0), (0.2 * size, 0.35 * size), (0.22 * size, 0.38 * size), (0.0, 0.36 * size)], "plastic", (0.45, 0.2, 0.12), sides=10)
    for i in range(7):
        a = i / 7 * 6.28 + rnd(-0.3, 0.3)
        tip = (x + math.cos(a) * 0.45 * size, y + math.sin(a) * 0.45 * size, z + rnd(0.7, 1.1) * size)
        mid = (x + math.cos(a) * 0.2 * size, y + math.sin(a) * 0.2 * size, z + 0.7 * size)
        k.tube([(x, y, z + 0.35 * size), mid, tip], 0.03 * size, "canvas", (0.15, 0.3, 0.12), sides=4)


def mahjong_table(k, pos):
    x, y, z = pos
    k.box((x, y, z + 0.72), (0.9, 0.9, 0.06), "canvas", (0.1, 0.35, 0.2))
    for dx in (-0.4, 0.4):
        for dy in (-0.4, 0.4):
            k.box((x + dx, y + dy, z + 0.35), (0.05, 0.05, 0.7), "darkwood")
    for side in range(4):
        R = rot_z(side * 90)
        for i in range(10):
            p = np.array((x, y, z + 0.765)) + R @ np.array([-0.3 + i * 0.065, -0.32, 0])
            k.box(p, (0.03, 0.022, 0.04), "plastic", (0.6, 0.6, 0.55), R=R)
        chair(k, np.array((x, y, z)) + R @ np.array([0, -0.75, 0]), side * 90 + 180)
