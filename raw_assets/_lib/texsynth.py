"""Tileable texture synthesis helpers (numpy/scipy) for environment materials.

Everything here wraps around the image edges, so every texture tiles.
Heights are in metres; `normal_from_height` needs the tile's size in metres.
Images are float arrays: (H, W) for greyscale, (H, W, 3) for colour (sRGB 0..1).
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree


class Synth:
    def __init__(self, size, tile_m, seed):
        self.S = size
        self.tile_m = tile_m
        self.rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        # Coordinates in metres across the tile: x right, y down.
        self.x = (xx + 0.5) / size * tile_m
        self.y = (yy + 0.5) / size * tile_m

    # ----------------------------------------------------------- noise
    def noise(self, beta=2.0, fmin=1.0, fmax=None, aniso=(1.0, 1.0)):
        """Periodic power-law noise, zero mean, unit std. `fmin`/`fmax` in cycles per tile.
        aniso=(ax, ay): ax > ay stretches features along y (vertical streaks)."""
        S = self.S
        k = np.fft.fftfreq(S) * S
        kx, ky = np.meshgrid(k, k)
        kk = np.sqrt((kx * aniso[0]) ** 2 + (ky * aniso[1]) ** 2)
        amp = np.zeros_like(kk)
        band = kk >= fmin
        if fmax:
            band &= kk <= fmax
        amp[band] = kk[band] ** (-beta / 2.0)
        phase = self.rng.uniform(0, 2 * np.pi, kk.shape)
        n = np.real(np.fft.ifft2(amp * np.exp(1j * phase)))
        n -= n.mean()
        return (n / (n.std() + 1e-9)).astype(np.float32)

    def noise01(self, **kw):
        n = self.noise(**kw)
        return np.clip(n * 0.18 + 0.5, 0, 1)

    def cells(self, count, jitter=1.0):
        """Periodic Voronoi: returns (f1, f2, id) with distances in pixels."""
        S = self.S
        g = int(np.ceil(np.sqrt(count)))
        base = (np.stack(np.meshgrid(np.arange(g), np.arange(g)), -1).reshape(-1, 2) + 0.5) / g
        pts = (base + self.rng.uniform(-0.5, 0.5, base.shape) * jitter / g) % 1.0
        pts = pts[: max(count, 1)] * S if count < len(pts) else pts * S
        ids = np.arange(len(pts))
        offs = [(dx, dy) for dx in (-S, 0, S) for dy in (-S, 0, S)]
        allp = np.concatenate([pts + np.array(o) for o in offs])
        allid = np.concatenate([ids for _ in offs])
        tree = cKDTree(allp)
        yy, xx = np.mgrid[0:S, 0:S]
        q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], -1)
        d, i = tree.query(q, k=2)
        f1 = d[:, 0].reshape(S, S).astype(np.float32)
        f2 = d[:, 1].reshape(S, S).astype(np.float32)
        cid = allid[i[:, 0]].reshape(S, S)
        return f1, f2, cid

    def rand_per_id(self, ids, lo=0.0, hi=1.0):
        table = self.rng.uniform(lo, hi, int(ids.max()) + 1).astype(np.float32)
        return table[ids]

    # ----------------------------------------------------------- filters
    def blur(self, img, sigma_px):
        if img.ndim == 3:
            return np.stack([ndimage.gaussian_filter(img[..., c], sigma_px, mode="wrap") for c in range(img.shape[2])], -1)
        return ndimage.gaussian_filter(img, sigma_px, mode="wrap")

    def streak(self, img, length_px, axis=0):
        """Run `img` down (axis 0) like water: a one-sided box blur."""
        k = np.zeros(int(length_px) * 2 + 1, np.float32)
        k[int(length_px):] = 1.0  # pixels below take the values above them
        k /= k.sum()
        return ndimage.convolve1d(img, k[::-1], axis=axis, mode="wrap")

    def cavity(self, h, radii_px=(2, 6, 16), k=None):
        """AO-ish term from height (metres): 1 in the open, darker in recesses."""
        k = k or 1.0 / (self.tile_m / self.S) / 4.0
        ao = np.ones_like(h)
        for r in radii_px:
            d = self.blur(h, r) - h
            ao *= np.clip(1.0 - np.maximum(d, 0) * k / len(radii_px) * 4.0 / max(r, 1) ** 0.5, 0.0, 1.0)
        return ao

    def normal_from_height(self, h, strength=1.0):
        px = self.tile_m / self.S
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px) * strength
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px) * strength
        n = np.stack([-dx, dy, np.ones_like(h)], -1)  # OpenGL (Y+) convention
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return n * 0.5 + 0.5

    # ----------------------------------------------------------- helpers
    @staticmethod
    def smooth(e0, e1, x):
        t = np.clip((x - e0) / (e1 - e0), 0, 1)
        return t * t * (3 - 2 * t)

    @staticmethod
    def mix(a, b, t):
        if a.ndim == 3 or (hasattr(b, "ndim") and np.ndim(b) == 3) or np.ndim(a) == 1:
            t = t[..., None] if np.ndim(t) == 2 else t
        return a * (1 - t) + b * t

    @staticmethod
    def col(rgb):
        return np.array(rgb, np.float32)

    def fill(self, rgb):
        return np.broadcast_to(self.col(rgb), (self.S, self.S, 3)).copy()

    def grid(self, cols, rows, offset_rows=0.0, gap_m=0.0, seed_jitter=0.0):
        """Rectangular tiling (bricks, slabs, tiles). Returns (id, u, v, edge_m) where
        u, v are 0..1 inside each cell and edge_m is the distance (m) to the cell edge
        minus half the gap (negative inside the joint)."""
        cw = self.tile_m / cols
        ch = self.tile_m / rows
        row = np.floor(self.y / ch).astype(np.int32)
        xs = self.x + (row % 2) * offset_rows * cw
        if seed_jitter:
            jit = self.rng.uniform(0, seed_jitter, rows).astype(np.float32)
            xs = xs + jit[row % rows] * cw
        xs = np.mod(xs, self.tile_m)
        col = np.floor(xs / cw).astype(np.int32)
        u = xs / cw - col
        v = self.y / ch - row
        ex = np.minimum(u, 1 - u) * cw
        ey = np.minimum(v, 1 - v) * ch
        edge = np.minimum(ex, ey) - gap_m / 2
        cid = (row % rows) * (cols + 1) + (col % cols)
        return cid, u, v, edge
