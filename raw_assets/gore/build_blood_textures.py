#!/usr/bin/env python3
"""Blood stain textures for the gore system (src/gore/gore.gd, blood_decal.gdshader).

All procedural (numpy). Shapes, not colours, straight alpha:
  R (= G = B) = how thick the blood is there (0 thin film .. 1 standing blood)
  A = coverage
The shader turns thickness into colour and gloss (thin is redder and lets the
surface through, thick is dark and wet) and dries it over time, so one set of
shapes serves fresh and old blood.

  splat_atlas.png  1024², 4x4 cells:
     row 0  impact spatter: a stain with spines and satellite drops (blood
            thrown flat against a surface; also under a wounded man)
     row 1  forward spatter: a fan of drops flying toward +X, the far ones
            long and thin (what leaves an exit wound and reaches the wall)
     row 2  single drops: two round (fell straight down, scalloped edge, a few
            satellites), two long with a tail toward +X (landed at an angle)
     row 3  two runs (a bead at the top that ran down a wall: +Y is down), two
            smears (dragged along +X: a crawling man, a body sliding)
  pool.png         512², an irregular pool, thicker at the rim where it stops
  mist.png         kept for the enemy muzzle flash (not blood)

Usage: python3 raw_assets/gore/build_blood_textures.py [out_dir]  (default assets/gore)
"""
import os
import sys

import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/gore"
CELL = 256
PAD = 0.07  # empty border of each cell, so neighbours don't bleed in the mipmaps


class Canvas:
    """One cell: thickness and coverage, drawn in 0..1 coordinates."""

    def __init__(self, n=CELL):
        self.n = n
        self.thick = np.zeros((n, n), np.float32)
        self.cov = np.zeros((n, n), np.float32)
        u = (np.arange(n) + 0.5) / n
        self.x, self.y = np.meshgrid(u, u)

    def _window(self, cx, cy, r):
        n = self.n
        x0, x1 = max(int((cx - r) * n) - 2, 0), min(int((cx + r) * n) + 3, n)
        y0, y1 = max(int((cy - r) * n) - 2, 0), min(int((cy + r) * n) + 3, n)
        return slice(y0, y1), slice(x0, x1)

    def stamp(self, sd, thick, win=(slice(None), slice(None))):
        """sd: signed distance in cell units (negative inside)."""
        aa = 1.2 / self.n
        c = np.clip(0.5 - sd / aa, 0.0, 1.0)
        self.cov[win] = np.maximum(self.cov[win], c)
        self.thick[win] = np.maximum(self.thick[win], c * thick)

    def ellipse(self, cx, cy, a, b, ang, thick):
        """Half-axes a (along ang) and b."""
        r = max(a, b)
        win = self._window(cx, cy, r)
        dx, dy = self.x[win] - cx, self.y[win] - cy
        ca, sa = np.cos(ang), np.sin(ang)
        u = (dx * ca + dy * sa) / a
        v = (-dx * sa + dy * ca) / b
        d = np.sqrt(u * u + v * v)
        self.stamp((d - 1.0) * min(a, b), thick * ring(d), win)

    def tear(self, cx, cy, length, width, ang, thick):
        """A drop that landed moving along `ang`: round at the back, a tail forward."""
        self.ellipse(cx, cy, length * 0.5, width * 0.5, ang, thick)
        ca, sa = np.cos(ang), np.sin(ang)
        steps = 7
        for i in range(1, steps + 1):
            f = i / steps
            w = width * 0.5 * (1.0 - f) ** 1.6 * 0.7
            if w * self.n < 0.35:
                break
            d = length * (0.35 + 0.55 * f)
            self.ellipse(cx + ca * d, cy + sa * d, max(w * 1.6, length * 0.09), w, ang, thick * 0.8)

    def done(self):
        keep = edge_mask(self.n)
        return self.thick * keep, self.cov * keep


def ring(d):
    """Thickness across a drop: a little thicker at the rim (where it dries last)."""
    return 0.72 + 0.28 * np.clip(d, 0.0, 1.0) ** 3


def edge_mask(n):
    u = (np.arange(n) + 0.5) / n
    m = np.clip(np.minimum(u, 1.0 - u) / PAD * 1.6 - 0.35, 0.0, 1.0)
    return np.minimum.outer(m, m).astype(np.float32)


def value_noise(n, cells, rng):
    g = rng.random((cells + 2, cells + 2))
    x = np.linspace(0, cells, n, endpoint=False)
    i = x.astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    a = g[i][:, i]
    b = g[i][:, i + 1]
    c = g[i + 1][:, i]
    d = g[i + 1][:, i + 1]
    top = a + (b - a) * f[None, :]
    bot = c + (d - c) * f[None, :]
    return (top + (bot - top) * f[:, None]).astype(np.float32)


def fbm(n, rng, base=3, octaves=4):
    out = np.zeros((n, n), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        out += amp * value_noise(n, base * 2 ** o, rng)
        total += amp
        amp *= 0.5
    return out / total


def blob(c, cx, cy, r0, rng, lobes=7, rough=0.22, thick=0.9, spines=0):
    """An irregular stain; `spines` thin rays off its rim."""
    dx, dy = c.x - cx, c.y - cy
    d = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    r = np.full_like(d, r0)
    for k in range(2, lobes + 2):
        r += r0 * rough / (k - 0.5) * np.cos(k * th + rng.random() * 6.283)
    inner = np.clip(d / np.maximum(r, 1e-4), 0.0, 1.0)
    c.stamp(d - r, thick * (0.7 + 0.3 * inner ** 4))
    for _ in range(spines):
        a = rng.random() * 6.283
        length = r0 * rng.uniform(0.25, 0.9)
        w = r0 * rng.uniform(0.035, 0.08)
        for i in range(10):
            f = i / 9.0
            rr = r0 * 0.9 + length * f
            ww = w * (1.0 - 0.75 * f)
            c.ellipse(cx + np.cos(a) * rr, cy + np.sin(a) * rr, max(ww * 2.0, length * 0.08), ww, a, thick * 0.75)
        if rng.random() < 0.7:  # the drop that left the spine
            rr = r0 * 0.9 + length * rng.uniform(1.15, 1.5)
            c.ellipse(cx + np.cos(a) * rr, cy + np.sin(a) * rr, w * 1.6, w * 1.1, a, thick * 0.8)


def impact_spatter(seed):
    rng = np.random.default_rng(seed)
    c = Canvas()
    cx, cy = 0.5 + rng.uniform(-0.03, 0.03), 0.5 + rng.uniform(-0.03, 0.03)
    r0 = rng.uniform(0.13, 0.17)
    blob(c, cx, cy, r0, rng, lobes=8, rough=0.3, thick=0.95, spines=int(rng.integers(7, 12)))
    for _ in range(int(rng.integers(70, 110))):
        a = rng.random() * 6.283
        dist = r0 * (1.1 + rng.exponential(0.55))
        if dist > 0.41:
            continue
        size = rng.uniform(0.003, 0.013) * (1.0 - 0.6 * dist / 0.41)
        stretch = 1.0 + 2.5 * (dist / 0.41) * rng.random()
        c.ellipse(cx + np.cos(a) * dist, cy + np.sin(a) * dist, size * stretch, size, a, rng.uniform(0.35, 0.8))
    return c.done()


def forward_spatter(seed):
    rng = np.random.default_rng(seed)
    c = Canvas()
    ox, oy = 0.16, 0.5 + rng.uniform(-0.04, 0.04)
    blob(c, ox + 0.03, oy, rng.uniform(0.045, 0.065), rng, lobes=6, rough=0.35, thick=0.9, spines=0)
    for _ in range(int(rng.integers(150, 210))):
        a = rng.normal(0.0, 0.3)
        dist = rng.uniform(0.02, 0.74) ** 0.8 * 0.76
        px, py = ox + np.cos(a) * dist, oy + np.sin(a) * dist
        if not (PAD < px < 1 - PAD and PAD < py < 1 - PAD):
            continue
        f = dist / 0.76
        size = rng.uniform(0.0035, 0.012) * (1.15 - 0.75 * f)
        stretch = 1.4 + 5.0 * f * rng.uniform(0.5, 1.0)
        if rng.random() < 0.18:
            c.tear(px, py, size * stretch * 2.0, size * 2.0, a, rng.uniform(0.5, 0.9))
        else:
            c.ellipse(px, py, size * stretch, size, a, rng.uniform(0.35, 0.8))
    return c.done()


def round_drop(seed):
    rng = np.random.default_rng(seed)
    c = Canvas()
    r0 = rng.uniform(0.2, 0.25)
    dx, dy = c.x - 0.5, c.y - 0.5
    d = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    lobes = int(rng.integers(14, 22))
    r = r0 * (1.0 + 0.05 * np.cos(lobes * th + rng.random() * 6.283) + 0.04 * np.cos(3 * th + rng.random() * 6.283))
    c.stamp(d - r, 0.85 * ring(d / r))
    for _ in range(int(rng.integers(5, 12))):
        a = rng.random() * 6.283
        dist = r0 * rng.uniform(1.25, 1.75)
        s = rng.uniform(0.008, 0.02)
        c.ellipse(0.5 + np.cos(a) * dist, 0.5 + np.sin(a) * dist, s * rng.uniform(1.0, 1.8), s, a, 0.6)
    return c.done()


def long_drop(seed):
    rng = np.random.default_rng(seed)
    c = Canvas()
    width = rng.uniform(0.2, 0.25)
    c.tear(0.36, 0.5, 0.46, width, rng.normal(0.0, 0.03), 0.85)
    c.ellipse(0.9 - rng.uniform(0.0, 0.04), 0.5 + rng.uniform(-0.02, 0.02), 0.022, 0.014, 0.0, 0.7)
    for _ in range(int(rng.integers(3, 7))):
        c.ellipse(rng.uniform(0.55, 0.9), 0.5 + rng.normal(0.0, 0.07), rng.uniform(0.008, 0.02), rng.uniform(0.005, 0.009), 0.0, 0.5)
    return c.done()


def run(seed):
    rng = np.random.default_rng(seed)
    c = Canvas()
    for k in range(int(rng.integers(2, 4))):
        x = 0.5 + (0.0 if k == 0 else rng.uniform(-0.2, 0.2))
        top = rng.uniform(0.1, 0.16)
        length = (0.76 if k == 0 else rng.uniform(0.25, 0.6))
        w = (0.05 if k == 0 else rng.uniform(0.02, 0.035))
        c.ellipse(x, top, w * 1.5, w * 1.2, 0.0, 0.9)  # where it started
        steps = int(length * CELL / 2)
        wob = rng.uniform(-1, 1, 4)
        for i in range(steps):
            f = i / max(steps - 1, 1)
            y = top + length * f
            xx = x + 0.012 * (wob[0] * np.sin(f * 7 + wob[1] * 3) + wob[2] * np.sin(f * 17 + wob[3] * 3))
            ww = w * (0.55 - 0.25 * f + 0.08 * np.sin(f * 23 + wob[1] * 6))
            c.ellipse(xx, y, ww, ww * 1.3, 1.5708, 0.55 + 0.3 * f)
        c.ellipse(x + 0.012 * wob[0] * np.sin(7 + wob[1] * 3), top + length, w * 0.75, w * 1.05, 1.5708, 1.0)  # the bead
    return c.done()


def smear(seed):
    rng = np.random.default_rng(seed)
    c = Canvas()
    # Many thin streaks side by side, starting and stopping raggedly.
    for _ in range(int(rng.integers(70, 95))):
        y = 0.5 + rng.normal(0.0, 0.085)
        length = rng.uniform(0.12, 0.55)
        x = rng.uniform(0.2, 0.88 - length * 0.5)
        w = rng.uniform(0.003, 0.011)
        c.ellipse(x + length * 0.5, y, length * 0.5, w, rng.normal(0.0, 0.02), rng.uniform(0.25, 0.7))
    blob(c, 0.2, 0.5, 0.07, rng, lobes=6, rough=0.3, thick=0.85)
    return c.done()


def pool(n=512):
    rng = np.random.default_rng(77)
    c = Canvas(n)
    dx, dy = c.x - 0.5, c.y - 0.5
    d = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    r = np.full_like(d, 0.37)
    for k in range(2, 9):
        r += 0.37 * 0.2 / (k - 0.7) * np.cos(k * th + rng.random() * 6.283)
    f = np.clip(d / r, 0.0, 1.0)
    # Flat and deep in the middle, a raised edge where surface tension holds it.
    thick = 0.78 + 0.22 * np.clip((f - 0.86) / 0.1, 0.0, 1.0) - 0.35 * np.clip((f - 0.96) / 0.04, 0.0, 1.0)
    c.stamp(d - r, 1.0)
    c.thick = (c.cov * thick).astype(np.float32)
    return c.done()


def save_la(path, thick, cov):
    # RGBA (thickness in R, G and B): Godot's two-channel import came out
    # striped on the Mobile renderer.
    t = np.clip(thick, 0, 1)
    rgba = np.stack([t, t, t, np.clip(cov, 0, 1)], axis=-1)
    Image.fromarray((rgba * 255.0 + 0.5).astype(np.uint8), "RGBA").save(path, optimize=True)
    print("wrote", path, rgba.shape)


def main():
    os.makedirs(OUT, exist_ok=True)
    cells = [
        impact_spatter(11), impact_spatter(12), impact_spatter(13), impact_spatter(14),
        forward_spatter(21), forward_spatter(22), forward_spatter(23), forward_spatter(24),
        round_drop(31), round_drop(32), long_drop(33), long_drop(34),
        run(41), run(42), smear(43), smear(44),
    ]
    thick = np.zeros((CELL * 4, CELL * 4), np.float32)
    cov = np.zeros_like(thick)
    for i, (t, a) in enumerate(cells):
        y, x = (i // 4) * CELL, (i % 4) * CELL
        thick[y:y + CELL, x:x + CELL] = t
        cov[y:y + CELL, x:x + CELL] = a
    save_la(os.path.join(OUT, "splat_atlas.png"), thick, cov)
    t, a = pool()
    save_la(os.path.join(OUT, "pool.png"), t, a)
    # A sheet to look at: dark blood on a pale floor, thickness as colour.
    thin = np.array((0.50, 0.03, 0.02))
    deep = np.array((0.13, 0.0, 0.005))
    rgb = thin[None, None, :] + (deep - thin)[None, None, :] * thick[:, :, None]
    bg = np.full((CELL * 4, CELL * 4, 3), 0.62)
    al = (cov * (0.72 + 0.28 * thick))[:, :, None]
    sheet = bg * (1 - al) + rgb * al
    prev = os.environ.get("BLOOD_PREVIEW")
    if prev:
        Image.fromarray((np.clip(sheet, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).save(prev)
        print("wrote", prev)


if __name__ == "__main__":
    main()
