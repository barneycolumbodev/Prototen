#!/usr/bin/env python3
"""Tileable print patterns for triad clothes: assets/characters/triad/textures/triad_prints.png.

One pattern per channel, each with three levels: 0 = the garment's own
colour, 0.5 = print colour A, 1 = print colour B (TriadLook / triad.gdshader):
  R  Hawaiian floral: hibiscus flowers (B) with leaves (A)
  G  woodland camo: three-tone blobs
  B  check: stripes (A) crossing (B)
  A  auspicious clouds: curling cloud motifs (B) on a lattice (A)
Every pattern wraps at the edges (drawn three by three and folded).

Usage: python3 raw_assets/characters/triad/build_prints.py [size]
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(ROOT, "assets", "characters", "triad", "textures", "triad_prints.png")


class Tile:
    """Draws into a 3x3 tiling and keeps the middle: everything wraps."""

    def __init__(self, n):
        self.n = n
        self.img = Image.new("L", (n * 3, n * 3), 0)
        self.d = ImageDraw.Draw(self.img)

    def each(self, fn):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                fn(self.n * (1 + dx), self.n * (1 + dy))

    def poly(self, pts, v):
        self.each(lambda ox, oy: self.d.polygon([(x + ox, y + oy) for x, y in pts], fill=v))

    def ellipse(self, x, y, rx, ry, v):
        self.each(lambda ox, oy: self.d.ellipse((x - rx + ox, y - ry + oy, x + rx + ox, y + ry + oy), fill=v))

    def line(self, pts, v, w):
        self.each(lambda ox, oy: self.d.line([(x + ox, y + oy) for x, y in pts], fill=v, width=w))

    def arc(self, x, y, r, a0, a1, v, w):
        self.each(lambda ox, oy: self.d.arc((x - r + ox, y - r + oy, x + r + ox, y + r + oy), a0, a1, fill=v, width=w))

    def array(self):
        a = np.asarray(self.img, dtype=np.float32)[self.n:2 * self.n, self.n:2 * self.n] / 255.0
        return a


def floral(n, rng):
    t = Tile(n)
    for _ in range(28):  # leaves
        x, y = rng.uniform(0, n, 2)
        a = rng.uniform(0, 2 * math.pi)
        L = n * rng.uniform(0.08, 0.13)
        pts = []
        for k in np.linspace(0, 1, 12):
            w = L * 0.35 * math.sin(math.pi * k)
            pts.append((x + math.cos(a) * L * k - math.sin(a) * w, y + math.sin(a) * L * k + math.cos(a) * w))
        for k in np.linspace(1, 0, 12):
            w = -L * 0.35 * math.sin(math.pi * k)
            pts.append((x + math.cos(a) * L * k - math.sin(a) * w, y + math.sin(a) * L * k + math.cos(a) * w))
        t.poly(pts, 128)
    for _ in range(17):  # hibiscus: five round petals and a dark centre
        x, y = rng.uniform(0, n, 2)
        r = n * rng.uniform(0.045, 0.07)
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(5):
            a = a0 + 2 * math.pi * k / 5
            t.ellipse(x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9, r * 0.75, r * 0.75, 255)
        t.ellipse(x, y, r * 0.3, r * 0.3, 128)
    return t.array()


def camo(n, rng):
    from scipy import ndimage
    out = np.zeros((n, n), np.float32)
    for level, thr, sig in ((0.5, 0.52, n * 0.035), (1.0, 0.56, n * 0.03)):
        noise = rng.standard_normal((n, n))
        sm = ndimage.gaussian_filter(noise, sig, mode="wrap")
        sm = (sm - sm.min()) / (sm.max() - sm.min())
        out = np.where(sm > thr, level, out)
    return out


def check(n, rng):
    out = np.zeros((n, n), np.float32)
    k = 8
    w = n // (k * 3)
    for i in range(k):
        c = int((i + 0.5) * n / k)
        out[:, max(c - w, 0):c + w] += 0.5
        out[max(c - w, 0):c + w, :] += 0.5
    thin = n // (k * 12)
    for i in range(k):
        c = int((i + 0.0) * n / k)
        out[:, c:c + thin] = np.maximum(out[:, c:c + thin], 0.5)
        out[c:c + thin, :] = np.maximum(out[c:c + thin, :], 0.5)
    return np.clip(out, 0, 1)


def clouds(n, rng):
    t = Tile(n)
    step = n // 4
    for i in range(5):
        for j in range(5):
            t.line([(i * step, 0), (i * step, n)], 128, max(2, n // 256))
            t.line([(0, j * step), (n, j * step)], 128, max(2, n // 256))
    for i in range(4):
        for j in range(4):
            x = (i + 0.5) * step + (step * 0.5 if j % 2 else 0)
            y = (j + 0.5) * step
            s = step * 0.22
            w = max(3, n // 120)
            for dx, dy, r in ((-0.9, 0.1, 0.55), (0.0, -0.25, 0.7), (0.95, 0.05, 0.5)):
                t.arc(x + dx * s, y + dy * s, r * s, 180, 360, 255, w)
            t.line([(x - 1.45 * s, y + 0.1 * s), (x + 1.45 * s, y + 0.05 * s)], 255, w)
            prev = None
            for k in range(14):
                tt = k / 13
                a = 3.5 * math.pi * tt
                r = 0.35 * s * (1 - tt)
                p = (x + 1.1 * s + r * math.cos(a), y + 0.35 * s + r * math.sin(a))
                if prev:
                    t.line([prev, p], 255, w)
                prev = p
    return t.array()


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    rng = np.random.default_rng(2026)
    chans = [floral(n, rng), camo(n, rng), check(n, rng), clouds(n, rng)]
    a = np.stack(chans, -1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(OUT, optimize=True)
    print("saved", OUT)


if __name__ == "__main__":
    main()
