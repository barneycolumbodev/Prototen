#!/usr/bin/env python3
"""Blood and wound textures for the gore system (src/gore/gore.gd).

All procedural (numpy), RGBA PNGs with straight alpha:
  splat_atlas.png  2x2 splatter variants (wall/floor spatter, directional: the
                   spray runs toward +X, so the decal is turned along the shot)
  pool.png         irregular pool with a darker rim (grows under bodies)
  drop.png         soft droplet for spray particles
  mist.png         soft cloud for headshot mist

Usage: python3 raw_assets/gore/build_blood_textures.py [out_dir]  (default assets/gore)
"""
import os
import sys

import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/gore"
rng = np.random.default_rng(1337)
BLOOD = np.array((0.36, 0.012, 0.012))
DARK = np.array((0.16, 0.0, 0.005))


def grid(n):
    u = (np.arange(n) + 0.5) / n * 2 - 1
    return np.meshgrid(u, u)


def value_noise(n, cells, seed):
    r = np.random.default_rng(seed)
    g = r.random((cells + 1, cells + 1))
    x = np.linspace(0, cells, n, endpoint=False)
    i = x.astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    a = g[i][:, i]
    b = g[i][:, i + 1]
    c = g[i + 1][:, i]
    d = g[i + 1][:, i + 1]
    fx = f[None, :]
    fy = f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(n, cells, seed, octaves=4):
    out = np.zeros((n, n))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        out += amp * value_noise(n, cells * 2 ** o, seed + o)
        total += amp
        amp *= 0.5
    return out / total


def soft(d, edge):
    return np.clip(0.5 - d / edge, 0, 1)


def to_img(rgb, a):
    arr = np.concatenate([np.clip(rgb, 0, 1), np.clip(a, 0, 1)[..., None]], -1)
    return Image.fromarray((arr * 255).astype(np.uint8), "RGBA")


def splat(n, seed, directional):
    X, Y = grid(n)
    r = np.random.default_rng(seed)
    noise = fbm(n, 6, seed)
    R = np.sqrt(X * X + Y * Y)
    ang = np.arctan2(Y, X)
    # Main blob with a lobed edge.
    lobes = 0.05 * np.sin(ang * r.integers(4, 7) + r.random() * 6) + 0.035 * np.sin(ang * 11 + r.random() * 6)
    core = 0.34 + lobes + 0.18 * (noise - 0.5)
    if directional:
        core = core * (1 + 0.5 * np.clip(np.cos(ang), 0, 1))
    a = soft(R - core, 0.03)
    # Droplets flung outward (mostly along +X when directional), with tails.
    for _ in range(70 if directional else 45):
        th = r.normal(0, 0.55) if directional else r.random() * 2 * np.pi
        dist = r.uniform(0.35, 0.95)
        size = r.uniform(0.008, 0.035) * (1.2 - dist)
        cx, cy = np.cos(th) * dist, np.sin(th) * dist
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        a = np.maximum(a, soft(d - size, 0.012))
        if directional and r.random() < 0.6:
            # Elongated streak behind the drop, back toward the centre.
            for k in range(1, 6):
                t = k * size * 0.9
                d2 = np.sqrt((X - cx + np.cos(th) * t) ** 2 + (Y - cy + np.sin(th) * t) ** 2)
                a = np.maximum(a, soft(d2 - size * (1 - k / 7), 0.01))
    a *= soft(R - 0.98, 0.04) * 2
    a = np.clip(a, 0, 1)
    thick = np.clip(a * (0.7 + 0.6 * noise), 0, 1)
    rgb = BLOOD[None, None, :] * (0.65 + 0.5 * thick[..., None]) + DARK * (1 - thick[..., None]) * 0.3
    return rgb, a * (0.75 + 0.25 * thick)


def pool(n):
    X, Y = grid(n)
    noise = fbm(n, 5, 99)
    R = np.sqrt(X * X + Y * Y)
    ang = np.arctan2(Y, X)
    edge = 0.78 + 0.1 * np.sin(ang * 5 + 1.3) + 0.06 * np.sin(ang * 11) + 0.12 * (noise - 0.5)
    a = soft(R - edge, 0.03)
    rim = soft(np.abs(R - edge + 0.04), 0.08)
    rgb = BLOOD * (0.8 + 0.25 * noise[..., None]) * (1 - 0.45 * rim[..., None])
    return rgb, a


def blob(n, edge):
    X, Y = grid(n)
    R = np.sqrt(X * X + Y * Y)
    a = np.clip(1 - R, 0, 1) ** edge
    return np.ones((n, n, 3)), a


def main():
    os.makedirs(OUT, exist_ok=True)
    n = 256
    atlas = Image.new("RGBA", (n * 2, n * 2))
    for i in range(4):
        rgb, a = splat(n, 10 + i, directional=(i % 2 == 0))
        atlas.paste(to_img(rgb, a), ((i % 2) * n, (i // 2) * n))
    atlas.save(os.path.join(OUT, "splat_atlas.png"))
    rgb, a = pool(256)
    to_img(rgb, a).save(os.path.join(OUT, "pool.png"))
    rgb, a = blob(64, 1.6)
    to_img(rgb, a).save(os.path.join(OUT, "drop.png"))
    X, Y = grid(128)
    rgb, a = blob(128, 2.2)
    a = a * (0.6 + 0.4 * fbm(128, 4, 5))
    to_img(rgb, a).save(os.path.join(OUT, "mist.png"))
    print("blood textures in", OUT)


main()
