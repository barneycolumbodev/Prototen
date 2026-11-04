"""World material library for the environment (Chinatown docks and later maps).

Builds every tileable surface (brick, wet asphalt, pier planks, corrugated
sheet, mosaic tile, glazed roof tiles...) procedurally and packs them, with the
sign/window/prop atlases from ../atlases/build.py, into three layered images
that Godot imports as Texture2DArray (one draw call per chunk of the level,
whatever the mix of surfaces):

  world_albedo.webp RGB = base colour (sRGB), A = emission mask
  world_normal.webp tangent-space normal (OpenGL, Y+)
  world_orm.webp    R = ambient occlusion, G = roughness, B = metallic

Layer index, tile size in metres and the mean albedo (for light bounce in the
lightmap bake) go to materials.json, which the level generators read.
Tintable layers are neutral mid-grey: the shader multiplies by 2 × the vertex
colour, so a vertex colour of 0.5 grey leaves them unchanged.

Run: /opt/bpy-venv/bin/python raw_assets/env/materials/build.py [--only name,name] [--size 1024]
"""
import json
import os
import zlib
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
from texsynth import Synth  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "assets", "env", "world")
CACHE = os.path.join(HERE, "_cache")
S = 1024
for i, a in enumerate(sys.argv):
    if a == "--size":
        S = int(sys.argv[i + 1])

MATS = []


def material(name, tile_m, tint=False, seed=0):
    def deco(fn):
        MATS.append(dict(name=name, tile_m=tile_m, tint=tint, fn=fn, seed=seed or (zlib.crc32(name.encode()) % 9973)))
        return fn
    return deco


def result(albedo, height, rough, metal=0.0, s=None, ao_k=1.0, nstr=1.0, emit=None, extra_ao=None):
    ao = s.cavity(height) if ao_k > 0 else np.ones_like(height)
    ao = 1.0 - (1.0 - ao) * ao_k
    if extra_ao is not None:
        ao = ao * extra_ao
    metal = np.broadcast_to(np.float32(metal), height.shape) if np.ndim(metal) == 0 else metal
    rough = np.broadcast_to(np.float32(rough), height.shape) if np.ndim(rough) == 0 else rough
    ao = np.broadcast_to(ao, height.shape)
    return dict(albedo=np.clip(albedo, 0, 1), normal=s.normal_from_height(height, nstr),
                orm=np.stack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1), np.clip(metal, 0, 1)], -1),
                emit=emit if emit is not None else np.zeros_like(height))


# ===================================================================== masonry

@material("brick", 2.0)
def brick(s):
    rows, cols = 26, 9
    cid, u, v, edge = s.grid(cols, rows, offset_rows=0.5, gap_m=0.011)
    chip = s.noise(beta=1.6, fmin=8) * 0.0035
    inside = s.smooth(-0.0005, 0.003, edge + chip)
    # per-brick tone: reds, browns, a few burnt headers and pale ones
    tone = s.rand_per_id(cid)
    base = s.mix(s.col((0.36, 0.13, 0.08)), s.col((0.48, 0.22, 0.14)), s.smooth(0.0, 1.0, tone))
    burnt = (s.rand_per_id(cid) > 0.88).astype(np.float32)
    pale = (s.rand_per_id(cid) > 0.93).astype(np.float32)
    base = s.mix(base, s.col((0.17, 0.08, 0.06)), burnt * 0.8)
    base = s.mix(base, s.col((0.58, 0.38, 0.28)), pale * 0.7)
    grain = s.noise(beta=1.0, fmin=40) * 0.06 + s.noise(beta=2.0, fmin=6) * 0.05
    base = base * (1.0 + grain[..., None])
    mortar = s.fill((0.42, 0.40, 0.36)) * (1 + s.noise(beta=1.2, fmin=30)[..., None] * 0.08)
    alb = s.mix(mortar, base, inside)
    # soot, efflorescence, water runs
    soot = s.smooth(0.3, 1.6, s.noise(beta=2.6, fmin=1))
    alb = alb * (1 - 0.45 * soot[..., None])
    salt = s.smooth(1.2, 2.4, s.noise(beta=2.2, fmin=2)) * (1 - inside * 0.4)
    alb = s.mix(alb, s.col((0.62, 0.6, 0.55)), salt * 0.5)
    runs = s.streak(s.smooth(1.4, 2.6, s.noise(beta=1.8, fmin=3)), 60)
    alb = alb * (1 - 0.3 * np.clip(runs * 2, 0, 1)[..., None])
    tilt = (s.rand_per_id(cid, -1, 1) * (u - 0.5) + s.rand_per_id(cid, -1, 1) * (v - 0.5)) * 0.0015
    h = inside * 0.008 + tilt * inside + s.noise(beta=1.4, fmin=20) * 0.0006 + chip * 0.2 * inside
    rough = 0.82 + inside * 0.05 + soot * 0.05
    return result(alb, h, rough, s=s, nstr=1.4)


@material("plaster", 3.0, tint=True)
def plaster(s):
    trowel = s.noise(beta=2.2, fmin=4) * 0.6 + s.noise(beta=1.2, fmin=60) * 0.4
    alb = s.fill((0.52, 0.51, 0.49)) * (1 + trowel[..., None] * 0.035)
    patches = s.smooth(0.9, 1.3, s.noise(beta=2.8, fmin=2))
    alb = s.mix(alb, s.col((0.46, 0.45, 0.43)), patches * 0.6)
    f1, f2, _ = s.cells(14)
    crack = s.smooth(3.0, 0.0, f2 - f1) * s.smooth(0.6, 1.4, s.noise(beta=2.0, fmin=3))
    stain = s.streak(s.smooth(1.0, 2.2, s.noise(beta=1.6, fmin=4, aniso=(1, 0.3))), 120)
    alb = alb * (1 - np.clip(stain * 1.6, 0, 0.42)[..., None])
    alb = alb * (1 - crack[..., None] * 0.55)
    grime = s.smooth(-0.2, 1.8, s.noise(beta=2.4, fmin=1))
    alb = alb * (1 - grime[..., None] * 0.18)
    h = trowel * 0.0005 - crack * 0.0015 + patches * 0.0008
    rough = 0.88 - stain * 0.1
    return result(alb, h, rough, s=s, ao_k=0.8)


@material("concrete", 4.0)
def concrete(s):
    mott = s.noise(beta=2.4, fmin=2) * 0.5 + s.noise(beta=1.6, fmin=12) * 0.5
    alb = s.fill((0.34, 0.335, 0.32)) * (1 + mott[..., None] * 0.07)
    speck = s.smooth(2.3, 3.0, s.noise(beta=0.2, fmin=200))
    alb = s.mix(alb, s.col((0.5, 0.49, 0.47)), speck * 0.5)
    pits = s.smooth(2.4, 3.2, s.noise(beta=0.4, fmin=120))
    alb = alb * (1 - pits[..., None] * 0.5)
    stains = s.smooth(0.8, 2.0, s.noise(beta=2.6, fmin=2))
    alb = alb * (1 - stains[..., None] * 0.28)
    oil = s.smooth(2.0, 2.6, s.noise(beta=3.0, fmin=2))
    alb = s.mix(alb, s.col((0.07, 0.07, 0.07)), oil * 0.7)
    f1, f2, _ = s.cells(9)
    crack = s.smooth(2.5, 0.0, f2 - f1) * s.smooth(0.8, 1.6, s.noise(beta=2.0, fmin=2))
    alb = alb * (1 - crack[..., None] * 0.6)
    h = mott * 0.0008 - pits * 0.002 - crack * 0.003
    rough = 0.86 - stains * 0.15 - oil * 0.4
    return result(alb, h, rough, s=s)


@material("asphalt", 4.0)
def asphalt(s):
    f1, f2, cid = s.cells(int(9000 * (S / 1024) ** 2) + 2000)
    stone = s.smooth(f2.mean() * 0.0 + 3.5 * S / 1024, 0.8, f1)
    tone = s.rand_per_id(cid)
    agg = s.mix(s.col((0.1, 0.1, 0.1)), s.col((0.22, 0.21, 0.2)), tone)
    binder = s.fill((0.06, 0.06, 0.065))
    alb = s.mix(binder, agg, stone * s.smooth(0.3, 0.9, tone))
    wear = s.smooth(-0.5, 1.5, s.noise(beta=2.4, fmin=2))
    alb = alb * (0.85 + wear[..., None] * 0.35)
    patch = s.smooth(1.5, 1.7, s.noise(beta=3.2, fmin=1))
    alb = s.mix(alb, s.col((0.045, 0.045, 0.05)), patch * 0.8)
    g1, g2, _ = s.cells(6)
    crack = s.smooth(3.5, 0.0, g2 - g1) * s.smooth(1.0, 1.8, s.noise(beta=2.0, fmin=2))
    seal = s.smooth(9.0, 2.0, g2 - g1) * s.smooth(1.6, 2.0, s.noise(beta=2.0, fmin=2))
    alb = alb * (1 - crack[..., None] * 0.7)
    alb = s.mix(alb, s.col((0.025, 0.025, 0.03)), seal * 0.9)
    h = stone * 0.002 * tone - crack * 0.004
    rough = 0.78 - wear * 0.08 - seal * 0.45 - patch * 0.1
    return result(alb, h, rough, s=s, nstr=1.2)


@material("pavers", 2.0)
def pavers(s):
    cid, u, v, edge = s.grid(4, 4, gap_m=0.008)
    chip = s.noise(beta=1.5, fmin=10) * 0.004
    inside = s.smooth(0.0, 0.005, edge + chip)
    tone = s.rand_per_id(cid)
    alb = s.mix(s.col((0.27, 0.27, 0.26)), s.col((0.4, 0.39, 0.37)), tone)
    alb = alb * (1 + s.noise(beta=1.4, fmin=20)[..., None] * 0.06)
    joint = s.fill((0.1, 0.1, 0.09))
    alb = s.mix(joint, alb, inside)
    # chewing gum: small dark discs
    gum = s.smooth(2.9, 3.3, s.noise(beta=0.0, fmin=60, fmax=180))
    alb = s.mix(alb, s.col((0.12, 0.12, 0.12)), gum * 0.8)
    dirt = s.smooth(0.0, 1.8, s.noise(beta=2.6, fmin=2))
    alb = alb * (1 - dirt[..., None] * 0.3)
    tilt = (s.rand_per_id(cid, -1, 1) * (u - 0.5) + s.rand_per_id(cid, -1, 1) * (v - 0.5)) * 0.003
    h = inside * 0.006 + tilt * inside + gum * 0.0005
    rough = 0.82 - dirt * 0.1
    return result(alb, h, rough, s=s, nstr=1.3)


@material("stone", 2.0)
def stone(s):
    speck = s.noise(beta=0.0, fmin=150)
    alb = s.fill((0.36, 0.35, 0.34))
    alb = s.mix(alb, s.col((0.12, 0.12, 0.13)), s.smooth(1.0, 2.0, speck))
    alb = s.mix(alb, s.col((0.62, 0.6, 0.58)), s.smooth(1.4, 2.4, -speck))
    alb = s.mix(alb, s.col((0.42, 0.33, 0.3)), s.smooth(1.6, 2.6, s.noise(beta=0.3, fmin=120)) * 0.6)
    weather = s.smooth(0.0, 2.0, s.noise(beta=2.5, fmin=2))
    alb = alb * (1 - weather[..., None] * 0.25)
    h = s.noise(beta=1.2, fmin=40) * 0.0004
    rough = 0.6 + weather * 0.25
    return result(alb, h, rough, s=s, ao_k=0.5)


@material("terrazzo", 2.0)
def terrazzo(s):
    f1, f2, cid = s.cells(9000, 1.0)
    chip = s.smooth(4.0, 2.0, f1) * (s.rand_per_id(cid) > 0.35)
    pal = np.array([(0.6, 0.55, 0.48), (0.25, 0.23, 0.22), (0.55, 0.32, 0.25), (0.82, 0.8, 0.75), (0.35, 0.4, 0.38)], np.float32)
    pick = pal[(s.rand_per_id(cid) * 4.999).astype(np.int32)]
    alb = s.mix(s.fill((0.68, 0.64, 0.56)), pick, chip.astype(np.float32))
    # brass divider strips on a 1 m grid
    d = np.minimum(np.abs(((s.x + 0.5) % 1.0) - 0.5), np.abs(((s.y + 0.5) % 1.0) - 0.5))
    strip = s.smooth(0.003, 0.0015, d)
    alb = s.mix(alb, s.col((0.55, 0.42, 0.2)), strip)
    wear = s.smooth(0.0, 2.0, s.noise(beta=2.4, fmin=2))
    alb = alb * (1 - wear[..., None] * 0.15)
    h = -strip * 0.0002 + s.noise(beta=1.0, fmin=80) * 0.00005
    rough = 0.18 + wear * 0.25 + strip * 0.1
    return result(alb, h, rough, metal=strip * 0.9, s=s, ao_k=0.3)


# ===================================================================== wood

def wood_grain(s, axis_stretch=10.0, rings=22.0):
    n = s.noise(beta=2.0, fmin=1, aniso=(0.2, 1.0 * axis_stretch / 10))
    g = np.sin((s.y / s.tile_m * rings + n * 1.5) * np.pi * 2) * 0.5 + 0.5
    fine = s.noise(beta=1.0, fmin=30, aniso=(0.08, 1.0))
    return g, fine


@material("planks", 2.0)
def planks(s):
    rows = 10
    ch = s.tile_m / rows
    row = np.floor(s.y / ch).astype(np.int32)
    v = s.y / ch - row
    # one butt joint per plank per tile, at a random x
    jx = s.rng.uniform(0, s.tile_m, rows).astype(np.float32)[row % rows]
    dx = np.abs(((s.x - jx + s.tile_m / 2) % s.tile_m) - s.tile_m / 2)
    edge = np.minimum(np.minimum(v, 1 - v) * ch, dx) - 0.004
    inside = s.smooth(-0.001, 0.004, edge + s.noise(beta=1.5, fmin=12) * 0.002)
    seg = row * 2 + (((s.x - jx) % s.tile_m) > s.tile_m / 2)
    tone = s.rand_per_id(seg)
    n = s.noise(beta=2.6, fmin=1, fmax=12, aniso=(1.0, 0.12))
    grain = np.sin((v * 3 + n * 2.5 + tone * 7) * np.pi * 2) * 0.5 + 0.5
    fine = s.noise(beta=0.8, fmin=40, aniso=(1.0, 0.06))
    alb = s.mix(s.col((0.25, 0.23, 0.2)), s.col((0.42, 0.39, 0.34)), s.smooth(0, 1, tone))
    fibres = s.noise(beta=1.4, fmin=8, aniso=(1.0, 0.04))
    alb = alb * (0.78 + grain[..., None] ** 3 * 0.3 + fine[..., None] * 0.06 + fibres[..., None] * 0.07)
    # knots
    f1, _, kid = s.cells(26)
    knot = s.smooth(9, 2, f1) * (s.rand_per_id(kid) > 0.5)
    alb = s.mix(alb, s.col((0.13, 0.11, 0.09)), knot * 0.7)
    # nails at joists every 0.5 m, two per plank
    nx = np.abs(((s.x + 0.25) % 0.5) - 0.25)
    for vy in (0.28, 0.72):
        nail = s.smooth(0.0065, 0.004, np.sqrt(nx ** 2 + ((v - vy) * ch) ** 2))
        alb = s.mix(alb, s.col((0.12, 0.08, 0.06)), nail)
        rust = s.smooth(0.03, 0.0, np.sqrt(nx ** 2 + ((v - vy) * ch) ** 2)) * 0.35
        alb = s.mix(alb, s.col((0.3, 0.14, 0.06)), rust * s.noise01(beta=1, fmin=40))
    gap = s.fill((0.03, 0.03, 0.03))
    alb = s.mix(gap, alb, inside)
    weather = s.smooth(-0.5, 2.0, s.noise(beta=2.4, fmin=1))
    alb = s.mix(alb, alb.mean(-1, keepdims=True) * s.col((1.0, 1.0, 1.05)), weather * 0.5)
    h = inside * 0.01 + grain ** 3 * 0.0012 * inside + fine * 0.0003 + fibres * 0.0004 - knot * 0.0005
    rough = 0.78 + fine * 0.04 - knot * 0.1
    return result(alb, h, rough, s=s, nstr=1.2)


@material("darkwood", 1.0)
def darkwood(s):
    n = s.noise(beta=3.0, fmin=1, fmax=10, aniso=(1.0, 0.15))
    grain = np.sin((s.y / s.tile_m * 14 + n * 0.9) * np.pi * 2) * 0.5 + 0.5
    fine = s.noise(beta=1.2, fmin=20, aniso=(1.0, 0.05))
    alb = s.mix(s.col((0.1, 0.05, 0.028)), s.col((0.3, 0.16, 0.08)), np.clip(grain ** 2 * 0.8 + 0.12 * fine + 0.1, 0, 1))
    scuff = s.smooth(1.4, 2.6, s.noise(beta=1.4, fmin=8))
    alb = s.mix(alb, s.col((0.3, 0.2, 0.14)), scuff * 0.4)
    h = grain * 0.0002 + fine * 0.0001
    rough = 0.32 + scuff * 0.3 + fine * 0.03
    return result(alb, h, rough, s=s, ao_k=0.3)


@material("lacquer", 1.0)
def lacquer(s):
    f1, f2, _ = s.cells(220)
    craze = s.smooth(1.6, 0.0, f2 - f1)
    alb = s.fill((0.42, 0.04, 0.03)) * (1 + s.noise(beta=2.2, fmin=2)[..., None] * 0.08)
    wear = s.smooth(1.2, 2.4, s.noise(beta=1.8, fmin=4))
    alb = s.mix(alb, s.col((0.16, 0.06, 0.04)), wear * 0.6)
    alb = alb * (1 - craze[..., None] * 0.35)
    h = -craze * 0.0002
    rough = 0.28 + wear * 0.35 + craze * 0.2
    return result(alb, h, rough, s=s, ao_k=0.4)


@material("cardboard", 1.0)
def cardboard(s):
    flute = np.sin(s.y / 0.006 * np.pi * 2) * 0.5 + 0.5
    alb = s.fill((0.42, 0.3, 0.18)) * (1 + s.noise(beta=1.4, fmin=8)[..., None] * 0.07)
    water = s.smooth(1.0, 2.0, s.noise(beta=2.4, fmin=2))
    alb = alb * (1 - water[..., None] * 0.35)
    tape = s.smooth(0.03, 0.028, np.abs(s.x - 0.5))
    alb = s.mix(alb, s.col((0.55, 0.42, 0.25)), tape * 0.8)
    crease = s.smooth(0.004, 0.0, np.abs(s.y - 0.25)) + s.smooth(0.004, 0.0, np.abs(s.y - 0.75))
    h = flute * 0.00015 - crease * 0.001 + water * 0.0004
    rough = 0.9 - tape * 0.5
    return result(alb, h, rough, s=s, ao_k=0.6)


# ===================================================================== metal

def paint_wear(s, scale=1.0):
    chips = s.smooth(1.45, 1.75, s.noise(beta=2.7, fmin=2 * scale) * 0.85 + s.noise(beta=1.2, fmin=24 * scale) * 0.4)
    scratches = s.smooth(2.8, 3.4, s.noise(beta=0.5, fmin=50, aniso=(1.0, 0.04)))
    return chips, scratches


def rust_colour(s):
    n = s.noise01(beta=1.4, fmin=16)
    return s.mix(s.col((0.22, 0.08, 0.03)), s.col((0.45, 0.2, 0.07)), n)


@material("corrugated", 2.0, tint=True)
def corrugated(s):
    ribs = 26
    prof = np.sin(s.x / s.tile_m * ribs * np.pi * 2)
    h = prof * 0.009
    paint = s.fill((0.5, 0.5, 0.5)) * (1 + s.noise(beta=2.0, fmin=3)[..., None] * 0.05)
    chips, scratches = paint_wear(s)
    # fastener rows every 0.5 m (on the ridges) bleeding rust downwards
    fy = np.abs(((s.y + 0.25) % 0.5) - 0.25)
    rx = np.abs(((s.x / s.tile_m * ribs + 0.25) % 1.0) - 0.5) * s.tile_m / ribs
    screw = s.smooth(0.006, 0.004, np.sqrt(rx ** 2 + fy ** 2)) * ((np.floor(s.x / s.tile_m * ribs) % 3) == 0)
    bleed = s.streak(screw.astype(np.float32) * 3 + s.smooth(2.2, 2.8, s.noise(beta=1.2, fmin=20)) * 0.4, 70)
    bleed = np.clip(bleed * 5 * (0.5 + 0.5 * s.noise01(beta=2.0, fmin=6, aniso=(1.0, 0.2))), 0, 1)
    rust = rust_colour(s)
    alb = s.mix(paint, rust, np.clip(chips + bleed * 0.8, 0, 1))
    alb = s.mix(alb, s.col((0.62, 0.6, 0.58)), scratches * 0.4)
    alb = s.mix(alb, s.col((0.25, 0.25, 0.26)), screw.astype(np.float32))
    dirt = s.smooth(0.0, 1.0, -prof) * 0.25 + s.smooth(0.5, 2.0, s.noise(beta=2.4, fmin=2)) * 0.25
    alb = alb * (1 - dirt[..., None])
    h = h + chips * -0.0002 + screw * 0.002
    rough = 0.55 + chips * 0.35 + bleed * 0.25 - scratches * 0.2
    return result(alb, h, rough, metal=screw * 0.8 + scratches * 0.5, s=s, ao_k=0.6)


@material("paint_metal", 2.0, tint=True)
def paint_metal(s):
    peel = s.noise(beta=1.0, fmin=60) * 0.00004
    paint = s.fill((0.5, 0.5, 0.5)) * (1 + s.noise(beta=2.2, fmin=2)[..., None] * 0.06)
    chips, scratches = paint_wear(s, 1.3)
    primer = s.col((0.36, 0.16, 0.1))
    rust = rust_colour(s)
    deep = chips * s.smooth(1.0, 1.6, s.noise(beta=2.2, fmin=4))
    alb = s.mix(paint, primer, chips)
    alb = s.mix(alb, rust, deep)
    run = np.clip(s.streak(deep, 90) * 3.0, 0, 1) * (0.5 + 0.5 * s.noise01(beta=2.0, fmin=6, aniso=(1.0, 0.2)))
    alb = s.mix(alb, rust * 0.8, run * 0.8)
    alb = s.mix(alb, s.col((0.55, 0.55, 0.56)), scratches * 0.5)
    grime = s.smooth(0.0, 2.0, s.noise(beta=2.5, fmin=2))
    alb = alb * (1 - grime[..., None] * 0.2)
    h = peel - chips * 0.00015 - deep * 0.0002
    rough = 0.45 + chips * 0.3 + deep * 0.3 + grime * 0.1 - scratches * 0.15
    return result(alb, h, rough, metal=scratches * 0.7, s=s, ao_k=0.5)


@material("shutter", 2.0, tint=True)
def shutter(s):
    slats = 27
    t = (s.y / s.tile_m * slats) % 1.0
    prof = np.where(t < 0.2, -np.sin(t / 0.2 * np.pi), np.sin((t - 0.2) / 0.8 * np.pi) * 0.6)
    h = prof * 0.006
    paint = s.fill((0.5, 0.5, 0.5)) * (1 + s.noise(beta=2.0, fmin=2)[..., None] * 0.05)
    chips, scratches = paint_wear(s, 1.0)
    alb = s.mix(paint, rust_colour(s), chips * 0.8)
    groove = s.smooth(0.2, 0.05, t) * s.smooth(0.0, 0.05, t)
    alb = alb * (1 - groove[..., None] * 0.6)
    streaks = s.streak(s.smooth(1.4, 2.6, s.noise(beta=1.2, fmin=6)), 100)
    alb = alb * (1 - np.clip(streaks * 2, 0, 0.4)[..., None])
    h = h - chips * 0.0002
    rough = 0.5 + chips * 0.3 + streaks * 0.2
    return result(alb, h, rough, metal=0.15, s=s, ao_k=0.7)


@material("rust", 2.0)
def rust(s):
    n1 = s.noise(beta=1.4, fmin=8)
    n2 = s.noise(beta=2.2, fmin=1)
    alb = s.mix(s.col((0.18, 0.07, 0.03)), s.col((0.42, 0.19, 0.07)), s.smooth(-1.2, 1.5, n1 + n2 * 0.5))
    flakes = s.smooth(1.5, 2.2, s.noise(beta=0.8, fmin=40))
    alb = s.mix(alb, s.col((0.55, 0.28, 0.1)), flakes * 0.5)
    paint = s.smooth(1.2, 1.6, n2)
    alb = s.mix(alb, s.col((0.12, 0.14, 0.13)), paint * 0.85)
    pits = s.smooth(2.0, 3.0, s.noise(beta=0.3, fmin=150))
    h = n1 * 0.0006 + flakes * 0.0004 - pits * 0.0008 + paint * 0.0003
    rough = 0.88 - paint * 0.35
    return result(alb, h, rough, metal=paint * 0.1, s=s, nstr=1.4)


@material("galv", 1.0)
def galv(s):
    brush = s.noise(beta=0.6, fmin=20, aniso=(1.0, 0.02))
    f1, f2, cid = s.cells(60, 1.0)
    spangle = s.rand_per_id(cid) * 0.06
    brush2 = s.noise(beta=1.2, fmin=6, aniso=(1.0, 0.03))
    alb = s.fill((0.6, 0.61, 0.62)) * (1 + (brush * 0.07 + brush2 * 0.05 + spangle)[..., None])
    scratches = s.smooth(2.6, 3.2, s.noise(beta=0.4, fmin=60, aniso=(0.3, 1.0)))
    smudge = s.smooth(0.5, 2.5, s.noise(beta=2.4, fmin=2)) * 0.6
    white = s.smooth(1.9, 2.6, s.noise(beta=1.6, fmin=6))  # white rust
    alb = s.mix(alb, s.col((0.7, 0.7, 0.68)), white * 0.5)
    alb = alb * (1 - smudge[..., None] * 0.25)
    h = brush * 0.00002 - scratches * 0.00005
    rough = 0.3 + smudge * 0.25 + white * 0.4 + spangle + brush * 0.04 - scratches * 0.1
    metal = 1.0 - white * 0.6
    return result(alb, h, rough, metal=metal, s=s, ao_k=0.2)


@material("grate", 1.0)
def grate(s):
    bars = 20
    t = (s.x / s.tile_m * bars) % 1.0
    cross = (s.y / s.tile_m * 5) % 1.0
    bar = s.smooth(0.42, 0.36, np.abs(t - 0.5)) * 0 + s.smooth(0.36, 0.3, np.abs(t - 0.5))
    xb = s.smooth(0.06, 0.04, np.abs(cross - 0.5))
    solid = np.clip(bar + xb, 0, 1)
    alb = s.mix(s.fill((0.01, 0.01, 0.01)), rust_colour(s) * 0.7 + s.col((0.05, 0.05, 0.05)), solid)
    h = solid * 0.02
    rough = 0.7
    return result(alb, h, rough, metal=solid * 0.4, s=s, ao_k=1.0)


# ===================================================================== tiles, roof

@material("mosaic", 1.0, tint=True)
def mosaic(s):
    cid, u, v, edge = s.grid(40, 40, gap_m=0.003)
    inside = s.smooth(0.0, 0.002, edge)
    tone = s.rand_per_id(cid)
    odd = (s.rand_per_id(cid) > 0.97)
    alb = s.fill((0.5, 0.5, 0.5)) * (0.9 + tone[..., None] * 0.18)
    alb = s.mix(alb, s.col((0.62, 0.62, 0.6)), odd.astype(np.float32) * 0.8)
    grout = s.fill((0.3, 0.29, 0.27)) * (1 - s.smooth(0.0, 2.0, s.noise(beta=2.2, fmin=3))[..., None] * 0.4)
    alb = s.mix(grout, alb, inside)
    missing = (s.rand_per_id(cid) > 0.995)
    alb = s.mix(alb, s.col((0.25, 0.24, 0.22)), missing.astype(np.float32) * inside)
    grime = s.smooth(0.0, 2.0, s.noise(beta=2.4, fmin=1))
    alb = alb * (1 - grime[..., None] * 0.2)
    dome = (1 - ((u - 0.5) ** 2 + (v - 0.5) ** 2) * 1.5) * 0.0006
    h = inside * (0.0015 + dome) - missing * 0.002
    rough = np.where(inside > 0.5, 0.18 + grime * 0.2, 0.9)
    return result(alb, h, rough, s=s, nstr=1.0, ao_k=0.6)


@material("rooftile", 2.0, tint=True)
def rooftile(s):
    ch = 10
    t = (s.x / s.tile_m * ch) % 1.0
    # alternating pan (concave, wide) and cap (convex, narrow) tiles
    cap = s.smooth(0.2, 0.12, np.abs(t - 0.5))
    pan = -np.cos((t) * np.pi * 2) * 0.5
    seg = (s.y / s.tile_m * 8) % 1.0
    step = seg * 0.006
    h = pan * 0.02 * (1 - cap) + cap * (0.035 + np.sqrt(np.clip(1 - ((np.abs(t - 0.5)) / 0.2) ** 2, 0, 1)) * 0.02) + step
    lip = s.smooth(0.05, 0.0, seg)
    glaze = s.fill((0.5, 0.5, 0.5)) * (1 + s.noise(beta=2.0, fmin=4)[..., None] * 0.08)
    dirt = s.smooth(-0.3, 0.3, -pan) * (1 - cap) * 0.5 + lip * 0.3
    lichen = s.smooth(1.4, 2.2, s.noise(beta=1.6, fmin=6))
    alb = glaze * (1 - dirt[..., None] * 0.6)
    alb = s.mix(alb, s.col((0.3, 0.32, 0.25)), lichen * 0.5)
    rough = 0.25 + dirt * 0.5 + lichen * 0.4
    return result(alb, h, rough, s=s, nstr=1.0, ao_k=1.0)


@material("roofing", 3.0)
def roofing(s):
    alb = s.fill((0.1, 0.1, 0.1)) * (1 + s.noise(beta=1.6, fmin=10)[..., None] * 0.1)
    gravel = s.smooth(1.4, 2.2, s.noise(beta=0.2, fmin=250))
    alb = s.mix(alb, s.col((0.3, 0.29, 0.27)), gravel * 0.6)
    seams = s.smooth(0.01, 0.0, np.abs(((s.y + 0.5) % 1.0) - 0.5))
    puddle = s.smooth(1.8, 2.2, s.noise(beta=3.0, fmin=1))
    h = gravel * 0.0008 + seams * 0.002
    rough = 0.9 - puddle * 0.7
    return result(alb, h, rough, s=s)


@material("epoxy", 4.0)
def epoxy(s):
    paint = s.fill((0.2, 0.27, 0.25))
    wear = s.smooth(0.6, 1.8, s.noise(beta=1.8, fmin=3) + s.noise(beta=1.0, fmin=30) * 0.4)
    conc = s.fill((0.33, 0.32, 0.3)) * (1 + s.noise(beta=1.4, fmin=12)[..., None] * 0.08)
    alb = s.mix(paint, conc, wear)
    stains = s.smooth(0.8, 2.0, s.noise(beta=2.5, fmin=2))
    alb = alb * (1 - stains[..., None] * 0.3)
    scuffs = s.smooth(2.5, 3.2, s.noise(beta=0.4, fmin=40, aniso=(1.0, 0.1)))
    alb = alb * (1 - scuffs[..., None] * 0.2)
    h = -wear * 0.0003
    rough = 0.35 + wear * 0.4 + scuffs * 0.1
    return result(alb, h, rough, s=s, ao_k=0.4)


# ===================================================================== fabric, plastic, glass

@material("canvas", 1.0, tint=True)
def canvas(s):
    weave = (np.sin(s.x / 0.002 * np.pi) * np.sin(s.y / 0.002 * np.pi)) * 0.5
    folds = s.noise(beta=3.0, fmin=1, aniso=(1.0, 0.3))
    alb = s.fill((0.5, 0.5, 0.5)) * (1 + weave[..., None] * 0.04 + folds[..., None] * 0.04)
    stains = s.streak(s.smooth(1.0, 2.2, s.noise(beta=1.8, fmin=3)), 60)
    alb = alb * (1 - np.clip(stains * 1.5, 0, 0.45)[..., None])
    mould = s.smooth(1.5, 2.5, s.noise(beta=1.2, fmin=12))
    alb = s.mix(alb, s.col((0.12, 0.13, 0.1)), mould * 0.35)
    h = folds * 0.003 + weave * 0.0001
    rough = 0.9
    return result(alb, h, rough, s=s, ao_k=0.3)


@material("plastic", 1.0, tint=True)
def plastic(s):
    alb = s.fill((0.5, 0.5, 0.5)) * (1 + s.noise(beta=2.0, fmin=3)[..., None] * 0.03)
    scuff = s.smooth(1.6, 2.6, s.noise(beta=1.0, fmin=20, aniso=(1.0, 0.3)))
    alb = s.mix(alb, s.col((0.6, 0.6, 0.6)), scuff * 0.25)
    dirt = s.smooth(0.0, 2.0, s.noise(beta=2.4, fmin=2))
    alb = alb * (1 - dirt[..., None] * 0.2)
    h = s.noise(beta=1.0, fmin=40) * 0.00002
    rough = 0.38 + scuff * 0.3 + dirt * 0.15
    return result(alb, h, rough, s=s, ao_k=0.0)


@material("glass", 2.0)
def glass(s):
    alb = s.fill((0.035, 0.04, 0.045))
    smudge = s.smooth(0.0, 2.0, s.noise(beta=2.0, fmin=3))
    runs = s.streak(s.smooth(1.4, 2.4, s.noise(beta=1.2, fmin=10)), 120)
    dirt = np.clip(smudge * 0.6 + runs * 2, 0, 1)
    alb = s.mix(alb, s.col((0.2, 0.19, 0.17)), dirt * 0.35)
    h = s.noise(beta=3.0, fmin=1) * 0.0003
    rough = 0.04 + dirt * 0.4
    return result(alb, h, rough, s=s, ao_k=0.0, nstr=0.3)


@material("wallpaper", 1.0)
def wallpaper(s):
    # red damask: a floral medallion on a half-drop lattice, gold ink
    cw, chh = 0.25, 0.333333
    row = np.floor(s.y / chh)
    lx = ((s.x / cw + (row % 2) * 0.5) % 1.0) - 0.5
    ly = (s.y / chh % 1.0) - 0.5
    r = np.sqrt(lx ** 2 + (ly * 0.75) ** 2)
    th = np.arctan2(ly, lx)
    petals = s.smooth(0.02, 0.0, r - (0.1 + 0.07 * np.abs(np.cos(th * 3)))) * s.smooth(0.03, 0.05, r)
    ring = s.smooth(0.012, 0.0, np.abs(r - 0.2 - 0.02 * np.cos(th * 8)))
    leaf = s.smooth(0.02, 0.0, np.abs(lx) * 2.2 + (np.abs(ly) - 0.42) ** 2 * 8 - 0.06)
    dot = s.smooth(0.03, 0.02, r)
    ink = np.clip(petals + ring * 0.9 + leaf + dot, 0, 1)
    base = s.fill((0.3, 0.025, 0.025)) * (1 + s.noise(beta=1.6, fmin=8)[..., None] * 0.05)
    alb = s.mix(base, s.col((0.58, 0.4, 0.15)), ink * 0.85)
    fade = s.smooth(0.5, 2.0, s.noise(beta=2.4, fmin=1))
    alb = s.mix(alb, alb * 0.7 + 0.06, fade * 0.3)
    seam = s.smooth(0.0015, 0.0, np.abs(((s.x + 0.25) % 0.5) - 0.25))
    h = ink * 0.0001 - seam * 0.0003
    rough = 0.75 - ink * 0.35
    return result(alb, h, rough, metal=ink * 0.5, s=s, ao_k=0.2)


# ===================================================================== emissive

@material("emissive", 1.0, tint=True)
def emissive(s):
    alb = s.fill((0.5, 0.5, 0.5))
    h = np.zeros((s.S, s.S), np.float32)
    return result(alb, h, 0.2, s=s, ao_k=0.0, emit=np.ones_like(h))


@material("lantern", 1.0, tint=True)
def lantern(s):
    # paper over bamboo ribs: ribs run around (along x), glow through the paper
    rib = s.smooth(0.006, 0.002, np.abs(((s.y + 0.04) % 0.08) - 0.04))
    fibre = s.noise(beta=0.8, fmin=60, aniso=(0.3, 1.0)) * 0.05
    alb = s.fill((0.5, 0.5, 0.5)) * (1 + fibre[..., None])
    alb = s.mix(alb, s.col((0.12, 0.08, 0.05)), rib * 0.8)
    soot = s.smooth(0.5, 2.0, s.noise(beta=2.6, fmin=1))
    emit = np.clip((1 - rib * 0.85) * (0.85 + fibre * 2) * (1 - soot * 0.25), 0, 1)
    h = rib * 0.002
    return result(alb, h, 0.8, s=s, ao_k=0.0, emit=emit)


# ===================================================================== build

def build_layer(m):
    path = os.path.join(CACHE, "%s_%d.npz" % (m["name"], S))
    src_mtime = os.path.getmtime(__file__)
    if os.path.exists(path) and os.path.getmtime(path) > src_mtime and "--force" not in sys.argv:
        d = np.load(path)
        return {k: d[k] for k in d.files}
    s = Synth(S, m["tile_m"], m["seed"])
    r = m["fn"](s)
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(path, **r)
    return r


def to8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    import importlib.util
    only = None
    for i, a in enumerate(sys.argv):
        if a == "--only":
            only = set(sys.argv[i + 1].split(","))
    # Atlases (signs, windows, props) are drawn by ../atlases/build.py.
    spec = importlib.util.spec_from_file_location("atlases", os.path.join(HERE, "..", "atlases", "build.py"))
    atl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(atl)
    layers = []
    for m in MATS:
        if only and m["name"] not in only:
            continue
        print("material", m["name"], flush=True)
        layers.append((m, build_layer(m)))
    for a in atl.ATLASES:
        print("atlas", a["name"], flush=True)
        layers.append((dict(name=a["name"], tile_m=1.0, tint=False), atl.build(a["name"], S)))
    cols = 6
    rows = (len(layers) + cols - 1) // cols
    alb = np.zeros((rows * S, cols * S, 4), np.uint8)
    nrm = np.zeros((rows * S, cols * S, 3), np.uint8)
    nrm[..., :] = (128, 128, 255)
    orm = np.zeros((rows * S, cols * S, 3), np.uint8)
    orm[..., :] = (255, 255, 0)
    meta = {"size": S, "cols": cols, "rows": rows, "layers": {}}
    for i, (m, r) in enumerate(layers):
        y, x = (i // cols) * S, (i % cols) * S
        alb[y:y + S, x:x + S, :3] = to8(r["albedo"])
        alb[y:y + S, x:x + S, 3] = to8(r["emit"])
        nrm[y:y + S, x:x + S] = to8(r["normal"])
        orm[y:y + S, x:x + S] = to8(r["orm"])
        lin = np.clip(r["albedo"], 0, 1) ** 2.2
        meta["layers"][m["name"]] = {"index": i, "tile_m": m["tile_m"], "tint": m["tint"],
                                     "mean_linear": [round(float(c), 4) for c in lin.reshape(-1, 3).mean(0)],
                                     "rough": round(float(r["orm"][..., 1].mean()), 3)}
        if "rects" in r:
            meta["layers"][m["name"]]["rects"] = r["rects"]
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(alb, "RGBA").save(os.path.join(OUT, "world_albedo.webp"), quality=92, method=5, exact=True)  # exact: keep colour where alpha (emission) is 0
    Image.fromarray(nrm, "RGB").save(os.path.join(OUT, "world_normal.webp"), quality=94, method=5)
    Image.fromarray(orm, "RGB").save(os.path.join(OUT, "world_orm.webp"), quality=92, method=5)
    with open(os.path.join(OUT, "materials.json"), "w") as f:
        json.dump(meta, f, indent=1)
    # contact sheet for review
    thumbs = []
    for m, r in layers:
        a = Image.fromarray(to8(r["albedo"])).resize((256, 256), Image.LANCZOS)
        n = Image.fromarray(to8(r["normal"])).resize((256, 256), Image.LANCZOS)
        o = Image.fromarray(to8(r["orm"])).resize((256, 256), Image.LANCZOS)
        t = Image.new("RGB", (256 * 3, 256))
        t.paste(a, (0, 0)); t.paste(n, (256, 0)); t.paste(o, (512, 0))
        thumbs.append(t)
    sheet = Image.new("RGB", (768 * 2, 256 * ((len(thumbs) + 1) // 2)))
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % 2) * 768, (i // 2) * 256))
    sheet.save(os.path.join(CACHE, "contact.png"))
    print("layers:", len(layers), "grid", cols, "x", rows)


if __name__ == "__main__":
    main()
