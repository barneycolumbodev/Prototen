#!/usr/bin/env python3
"""Pre-renders the harbour night sky to an equirectangular panorama.

Replaces the procedural sky shader (playtest 2026-11-05): that shader used
TIME, so Godot re-rendered the sky's radiance cubemap every frame on the
phone, and the owner found the sky read as flat black. This one is a low
rain-cloud deck lit from below by the city: sodium amber toward the far
shore across the bay (south, +Z in Godot), cooler magenta-violet where the
neon of Chinatown itself bounces off it, a hazy moon, a few gaps showing a
darker sky, and a bright band of haze at the horizon where rain hides the
distance. Rendered once; Godot samples one texture and computes radiance once.

Godot's panorama: u = 0.5 looks down -Z; u increases turning toward +X
(checked in-game with a capture looking south over the water).

Usage: python3 raw_assets/env/sky/build_night_sky.py [out.png] [--w 2048]
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "assets", "env", "sky", "harbour_night.png")

rng = np.random.default_rng(1997)


def value_noise(x, y, period):
    """Tileable 2D value noise; x wraps with `period` cells."""
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    xf = x - xi
    yf = y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    size = 1024
    table = rng.random((size, size)) if not hasattr(value_noise, "t") else value_noise.t
    value_noise.t = table

    def h(ix, iy):
        return table[iy % size, ix % period % size]

    a = h(xi, yi)
    b = h(xi + 1, yi)
    c = h(xi, yi + 1)
    d = h(xi + 1, yi + 1)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, period, octaves=6, gain=0.52):
    s = np.zeros_like(x)
    amp = 0.5
    norm = 0.0
    for o in range(octaves):
        f = 2 ** o
        s += value_noise(x * f + o * 17.3, y * f + o * 9.1, period * f) * amp
        norm += amp
        amp *= gain
    return s / norm


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def render(w=2048):
    h = w // 2
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    phi = (U - 0.5) * 2 * np.pi            # azimuth, 0 = -Z
    theta = (0.5 - V) * np.pi               # elevation
    dx = np.cos(theta) * np.sin(phi)
    dy = np.sin(theta)
    dz = -np.cos(theta) * np.cos(phi)

    # Colours (linear).
    zenith = np.array([0.020, 0.022, 0.038])
    gap = np.array([0.010, 0.012, 0.024])
    sodium = np.array([0.42, 0.20, 0.085])      # city glow on the cloud base
    neon = np.array([0.20, 0.08, 0.20])         # Chinatown's own neon, overhead
    haze = np.array([0.36, 0.22, 0.15])          # rain haze at the horizon
    moon_c = np.array([0.55, 0.60, 0.72])

    up = np.clip(dy, 0, 1)
    # Toward the far shore (south, +Z) the cloud base is brighter and warmer.
    south = np.clip(dz * 0.5 + 0.5, 0, 1) ** 1.5
    # Cloud deck: project onto a plane above, fbm, stretched by the wind.
    k = 1.0 / (up + 0.08)
    px = dx * k * 1.4
    pz = dz * k * 1.4
    # Wrap the azimuthal period so the image tiles at u = 0/1: sample in a
    # rotated frame with polar coords instead of plane coords for x.
    ang = (phi / (2 * np.pi) + 0.5) * 12.0      # 12 noise cells around
    rad = np.log1p(np.hypot(px, pz)) * 2.2
    n = fbm(ang + rad * 0.35, rad * 1.1, 12, octaves=5, gain=0.5)
    n2 = fbm(ang * 3.0 + 3.1, rad * 3.4 + 5.0, 36, octaves=4)
    # Detail fades toward the horizon (distance blurs the deck into haze).
    far = smooth(0.25, 0.02, up)
    nn = n * 0.85 + n2 * 0.15 * (1 - far)
    nn = nn * (1 - far) + 0.62 * far
    cloud = smooth(0.32, 0.58, nn)               # mostly overcast, a few breaks
    thick = smooth(0.5, 0.8, nn)

    # Light from below: strongest low in the sky, fades toward the zenith.
    E = lambda a: a[..., None]  # noqa: E731  per-pixel scalar -> broadcast over RGB
    low = smooth(0.85, 0.0, up)
    glow = sodium * E((0.35 + 0.9 * south) * low) + neon * E((0.6 - 0.4 * south) * (0.35 + 0.65 * low))
    base = zenith * E(1 - low) + glow * 0.5
    lit_cloud = glow * E(0.55 + 0.6 * thick) + zenith * 0.6
    # Cloud undersides: darker in thick cores (self-shadow), bright at thin edges.
    edge = cloud * (1 - thick)
    col = base * E(1 - cloud) + lit_cloud * E(cloud)
    col += glow * E(edge) * 0.35
    col = col * E(1 - (1 - cloud) * 0.5) + gap * E(1 - cloud) * 0.5

    # Moon behind thin cloud, high in the north-east.
    md = np.array([0.45, 0.62, -0.64])
    md /= np.linalg.norm(md)
    m = dx * md[0] + dy * md[1] + dz * md[2]
    thin = 1 - thick
    col += moon_c * (smooth(0.9990, 0.9996, m) * (0.1 + 0.5 * thin) * 0.7)[..., None]
    col += moon_c * (np.clip(m, 0, 1) ** 40 * 0.22 * (0.4 + 0.6 * thin))[..., None]

    # Horizon haze band, and below the horizon the dark bay / distant shore.
    hz = np.exp(-np.abs(dy) * 14.0)
    col = col * (1 - hz[..., None] * 0.7) + haze * (0.55 + 0.6 * south)[..., None] * hz[..., None] * 0.8
    below = smooth(0.0, -0.12, dy)
    col = col * (1 - below[..., None]) + (haze * 0.25 * (0.5 + 0.5 * south)[..., None] * (1 - smooth(-0.02, -0.4, dy))[..., None]
                                          + np.array([0.004, 0.005, 0.007])) * below[..., None]
    # Rain: a faint veil that softens everything near the horizon.
    col += np.array([0.02, 0.02, 0.025]) * hz[..., None]
    # Light dithering (8-bit banding on a dark gradient).
    col = np.clip(col, 0, None)
    srgb = np.where(col <= 0.0031308, col * 12.92, 1.055 * np.power(col, 1 / 2.4) - 0.055)
    srgb = srgb + (rng.random(srgb.shape) - 0.5) / 255.0
    return (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    args = sys.argv[1:]
    width = 2048
    if "--w" in args:
        i = args.index("--w")
        width = int(args[i + 1])
        del args[i:i + 2]
    out = args[0] if args else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img = render(width)
    from PIL import Image
    Image.fromarray(img, "RGB").save(out, optimize=True)
    print("sky:", out, img.shape)
