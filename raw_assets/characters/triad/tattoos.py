"""Triad tattoos (owner, 2026-11-11: "They need tattoos").

Black-and-grey ink, the way Hong Kong triad work usually is: a dragon
winding down an arm through clouds, koi in waves, tiger stripes, Chinese
characters (loyalty, righteousness, brotherhood...), barbed wire and flame
bands, knuckle characters. Three sets, each a whole body's worth of pieces;
each enemy wears a random choice of sets and body regions (the shader picks
them per man, triad.gdshader), so no two men look the same.

Each design is drawn in 2D with PIL (designs repeat round the arm), then
wrapped onto the body: arms and the neck by angle round the limb and
distance along it, the chest and back flat from the front/back, the hands
on the back of the hand. ink(P, N, regions, rest) returns three ink
densities (0..1) per texel; the shader darkens skin with them.

Characters are drawn with Noto Serif TC Black (SIL OFL, raw_assets/env/fonts).
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))

from common import J, V, arm_coord, leg_coord, ss, ARM_LEN, UPPER_ARM_LEN  # noqa: E402

_FONTS = None


def fonts():
    global _FONTS
    if _FONTS is None:
        from cjk import FontSet
        _FONTS = FontSet("serif")
    return _FONTS


# ====================================================================== 2D drawing helpers
class Canvas:
    """Ink canvas (float 0..1). Wraps horizontally when `wrap` (round a limb)."""

    def __init__(self, w, h, wrap=False, ss_=2):
        self.w, self.h, self.wrap, self.k = w, h, wrap, ss_
        W = w * (3 if wrap else 1) * ss_
        self.img = Image.new("L", (W, h * ss_), 0)
        self.d = ImageDraw.Draw(self.img)

    def _xy(self, pts):
        off = self.w if self.wrap else 0
        return [((x + off) * self.k, y * self.k) for x, y in pts]

    def poly(self, pts, ink=255, outline=None, width=0):
        for dx in ((-self.w, 0, self.w) if self.wrap else (0,)):
            p = self._xy([(x + dx, y) for x, y in pts])
            self.d.polygon(p, fill=ink if ink is not None else None)
            if outline is not None and width:
                self.d.line(p + [p[0]], fill=outline, width=int(width * self.k), joint="curve")

    def line(self, pts, ink=255, width=2):
        for dx in ((-self.w, 0, self.w) if self.wrap else (0,)):
            self.d.line(self._xy([(x + dx, y) for x, y in pts]), fill=ink, width=max(1, int(width * self.k)),
                        joint="curve")

    def circle(self, x, y, r, ink=255, outline=None, width=0):
        for dx in ((-self.w, 0, self.w) if self.wrap else (0,)):
            (cx, cy), = self._xy([(x + dx, y)])
            rr = r * self.k
            self.d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=ink,
                           outline=outline, width=int(width * self.k) if width else 0)

    def arc(self, x, y, r, a0, a1, ink=255, width=2):
        for dx in ((-self.w, 0, self.w) if self.wrap else (0,)):
            (cx, cy), = self._xy([(x + dx, y)])
            rr = r * self.k
            self.d.arc((cx - rr, cy - rr, cx + rr, cy + rr), a0, a1, fill=ink, width=max(1, int(width * self.k)))

    def glyph(self, ch, x, y, size, ink=255):
        f = fonts().font(ch, int(size * self.k))
        for dx in ((-self.w, 0, self.w) if self.wrap else (0,)):
            (cx, cy), = self._xy([(x + dx, y)])
            self.d.text((cx, cy), ch, fill=ink, font=f, anchor="mm")

    def array(self):
        img = self.img.resize((self.img.width // self.k, self.img.height // self.k), Image.LANCZOS)
        a = np.asarray(img, dtype=np.float32) / 255.0
        if self.wrap:
            a = a[:, self.w:2 * self.w]
        return a


def _offset_path(path, widths):
    """Left and right edges of a thick curve."""
    path = np.asarray(path, dtype=np.float64)
    d = np.gradient(path, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    w = np.asarray(widths)[:, None]
    return path + n * w, path - n * w, n, d


def _cloud(c, x, y, s, ink=255, width=3):
    """A curling cloud: three lobes and a spiral tail."""
    for k, (dx, dy, r) in enumerate(((-0.9, 0.1, 0.55), (0.0, -0.25, 0.7), (0.95, 0.05, 0.5))):
        c.arc(x + dx * s, y + dy * s, r * s, 180, 360, ink, width)
    c.line([(x - 1.45 * s, y + 0.1 * s), (x + 1.45 * s, y + 0.05 * s)], ink, width)
    for i in range(14):
        t = i / 13
        a = 3.5 * math.pi * t
        r = 0.35 * s * (1 - t)
        p0 = (x + 1.45 * s - 0.35 * s + r * math.cos(a), y + 0.35 * s + r * math.sin(a))
        if i:
            c.line([prev, p0], ink, width * 0.8)
        prev = p0


def _wind_bar(c, x0, y0, length, thick, bend, ink=150):
    """A curved band of shading (the 'wind bars' between the pieces)."""
    xs = np.linspace(0, length, 24)
    top = [(x0 + x, y0 + bend * math.sin(x / length * math.pi)) for x in xs]
    bot = [(x0 + x, y0 + thick * math.sin(x / length * math.pi) ** 0.6 + bend * math.sin(x / length * math.pi))
           for x in xs[::-1]]
    c.poly(top + bot, ink)


# ====================================================================== designs
def dragon_sleeve(w=900, h=1500, seed=3):
    """A dragon winding down the arm through clouds and black wind bars.
    x = round the arm (wraps), y = down the arm (shoulder at 0). Bold lines
    and big black areas, so it reads from across a street."""
    rng = np.random.default_rng(seed)
    c = Canvas(w, h, wrap=True)
    for i in range(14):
        _wind_bar(c, rng.uniform(0, w), rng.uniform(0.0, 1.0) * h, rng.uniform(0.3, 0.55) * w,
                  rng.uniform(35, 70), rng.uniform(-45, 45), ink=255)
    for i in range(9):
        x, y, sc = rng.uniform(0, w), rng.uniform(0.08, 0.95) * h, rng.uniform(45, 70)
        for dx, dy, r in ((-0.9, 0.1, 0.55), (0.0, -0.25, 0.7), (0.95, 0.05, 0.5)):
            c.circle(x + dx * sc, y + dy * sc, r * sc, 0)
        _cloud(c, x, y, sc, 255, 7)
    n = 300
    t = np.linspace(0, 1, n)
    x = w * (0.1 + 1.6 * t) + 60 * np.sin(t * 9.0)
    y = h * (0.2 + 0.76 * t) + 40 * np.sin(t * 13.0)
    width = 100 * (1 - t) ** 0.75 + 14
    left, right, nrm, d = _offset_path(np.stack([x, y], 1), width)
    c.poly(list(map(tuple, left)) + list(map(tuple, right[::-1])), 60)   # grey wash body
    # Dark shading along the back, fading toward the belly.
    shade_in = np.stack([x, y], 1) + nrm * (width * 0.25)[:, None]
    c.poly(list(map(tuple, left)) + list(map(tuple, shade_in[::-1])), 170)
    for i in range(4, n - 6, 3):
        for k in (-0.5, 0.05, 0.6):
            p = np.array((x[i], y[i])) + nrm[i] * width[i] * k
            r = width[i] * 0.3
            ang = math.degrees(math.atan2(d[i][1], d[i][0]))
            c.arc(p[0], p[1], r, ang + 30, ang + 150, 255, 4)
    for i in range(5, n - 8, 4):
        a = np.array((x[i], y[i])) - nrm[i] * width[i] * 0.98
        b = np.array((x[i], y[i])) - nrm[i] * width[i] * 0.6
        c.line([tuple(a), tuple(b)], 255, 5)
    belly = np.stack([x, y], 1) - nrm * (width * 0.6)[:, None]
    c.line(list(map(tuple, belly)), 255, 4)
    for i in range(6, n - 10, 6):
        base = np.array((x[i], y[i])) + nrm[i] * width[i]
        tip = base + nrm[i] * (24 + 0.45 * width[i]) + d[i] * 12
        b2 = base + d[i] * 20
        c.poly([tuple(base), tuple(tip), tuple(b2)], 255)
    c.line(list(map(tuple, left)), 255, 11)
    c.line(list(map(tuple, right)), 255, 11)
    for i in (45, 135, 215):
        root = np.array((x[i], y[i])) - nrm[i] * width[i] * 0.8
        knee = root - nrm[i] * 60 + d[i] * 35
        foot = knee - nrm[i] * 26 - d[i] * 26
        c.line([tuple(root), tuple(knee), tuple(foot)], 255, 22)
        for a in (-0.7, 0.0, 0.7):
            cd = np.array((math.cos(a), math.sin(a)))
            claw = foot + (-nrm[i] * cd[0] + d[i] * cd[1]) * 34
            c.line([tuple(foot), tuple(claw)], 255, 9)
    hx, hy = x[0], y[0]
    dd = -d[0]
    nn = nrm[0]
    k = 1.6
    P = lambda a, b: (hx + (dd[0] * a + nn[0] * b) * k, hy + (dd[1] * a + nn[1] * b) * k)
    for j in range(7):                                                     # mane
        c.poly([P(10 + j * 10, 55), P(-40 + j * 8, 120 + j * 6), P(25 + j * 10, 62)], 255)
    c.poly([P(0, 70), P(70, 60), P(150, 30), P(165, 5), P(150, -5), P(100, 0), P(75, -10), P(0, -65)], 70, 255, 9)
    c.poly([P(80, -14), P(150, -30), P(160, -55), P(110, -45), P(60, -50)], 170, 255, 8)
    for j in range(5):
        c.poly([P(95 + j * 12, -2), P(100 + j * 12, -18), P(105 + j * 12, -2)], 255)
    c.circle(*P(75, 30), 15 * k, 0, 255, 6)
    c.circle(*P(75, 30), 7 * k, 255)
    c.line([P(40, 50), P(-30, 110), P(-80, 120)], 255, 14)
    c.line([P(30, 60), P(-20, 140), P(-60, 160)], 255, 11)
    c.line([P(150, 25), P(200, 70), P(230, 50), P(250, 90)], 255, 7)
    c.line([P(150, -20), P(210, -80), P(240, -60), P(260, -100)], 255, 7)
    return np.clip(c.array(), 0, 1)


def koi_sleeve(w=900, h=1500, seed=11):
    """Koi swimming up through waves."""
    rng = np.random.default_rng(seed)
    c = Canvas(w, h, wrap=True)
    # Waves: rows of overlapping arcs (seigaiha) with shaded crests.
    for row in range(0, h, 70):
        for col in range(-1, w // 80 + 2):
            x = col * 80 + (40 if (row // 70) % 2 else 0)
            c.circle(x, row + 40, 40, 0)
            for r in (38, 27):
                c.arc(x, row + 40, r, 180, 360, 255, 5)
            c.circle(x, row + 40, 15, 255)
    # Clear the fish and draw them.
    for i, (fx, fy, ang, L) in enumerate(((0.25, 0.25, 70, 300), (0.7, 0.6, 110, 330), (0.35, 0.85, 80, 260))):
        cx, cy = fx * w, fy * h
        a = math.radians(ang + rng.uniform(-10, 10))
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        pts = []
        for k in np.linspace(0, 1, 30):
            wdt = L * 0.2 * math.sin(math.pi * min(k * 1.15, 1.0)) ** 0.7
            pts.append((cx + dx * (k - 0.5) * L + nx * wdt, cy + dy * (k - 0.5) * L + ny * wdt))
        for k in np.linspace(1, 0, 30):
            wdt = L * 0.2 * math.sin(math.pi * min(k * 1.15, 1.0)) ** 0.7
            pts.append((cx + dx * (k - 0.5) * L - nx * wdt, cy + dy * (k - 0.5) * L - ny * wdt))
        c.poly(pts, 50, 255, 10)
        # Tail fin.
        tx, ty = cx + dx * 0.5 * L, cy + dy * 0.5 * L
        c.poly([(tx, ty), (tx + dx * 90 + nx * 70, ty + dy * 90 + ny * 70), (tx + dx * 60, ty + dy * 60),
                (tx + dx * 90 - nx * 70, ty + dy * 90 - ny * 70)], 120, 255, 8)
        for k in range(5):
            c.line([(tx, ty), (tx + dx * 80 + nx * (50 - 25 * k), ty + dy * 80 + ny * (50 - 25 * k))], 255, 2)
        # Scales.
        for k in np.linspace(-0.3, 0.35, 8):
            for j in np.linspace(-0.12, 0.12, 4):
                sx_, sy_ = cx + dx * k * L + nx * j * L, cy + dy * k * L + ny * j * L
                c.arc(sx_, sy_, 15, math.degrees(a) + 90, math.degrees(a) + 270, 255, 4)
        # Head, eye, fins, whiskers.
        hx, hy = cx - dx * 0.42 * L, cy - dy * 0.42 * L
        c.circle(hx + nx * 18, hy + ny * 18, 7, 255)
        for sgn in (1, -1):
            fx2, fy2 = cx - dx * 0.2 * L + nx * sgn * 0.18 * L, cy - dy * 0.2 * L + ny * sgn * 0.18 * L
            c.poly([(fx2, fy2), (fx2 + nx * sgn * 60 + dx * 40, fy2 + ny * sgn * 60 + dy * 40),
                    (fx2 + dx * 50, fy2 + dy * 50)], 0, 255, 4)
            c.line([(hx, hy), (hx - dx * 40 + nx * sgn * 30, hy - dy * 40 + ny * sgn * 30)], 255, 3)
        # A patch of solid shading (koi markings).
        c.circle(cx - dx * 0.05 * L + nx * 15, cy - dy * 0.05 * L + ny * 15, L * 0.09, 230)
        c.circle(cx + dx * 0.22 * L - nx * 10, cy + dy * 0.22 * L - ny * 10, L * 0.06, 230)
    return np.clip(c.array(), 0, 1)


def tiger_band(w=900, h=520, seed=5):
    """Tiger stripes round the upper arm: tapered black strokes."""
    rng = np.random.default_rng(seed)
    c = Canvas(w, h, wrap=True)
    for i in range(22):
        x = i * w / 22 + rng.uniform(-10, 10)
        y0 = rng.uniform(0.05, 0.3) * h
        y1 = rng.uniform(0.7, 0.95) * h
        pts_l, pts_r = [], []
        for k in np.linspace(0, 1, 16):
            y = y0 + (y1 - y0) * k
            xx = x + 28 * math.sin(k * 5 + i) + rng.uniform(-2, 2)
            wd = 13 * math.sin(math.pi * k) ** 0.6
            pts_l.append((xx - wd, y))
            pts_r.append((xx + wd, y))
        c.poly(pts_l + pts_r[::-1], 255)
        if i % 3 == 0:
            c.poly([(x + 15, y0 + 40), (x + 70, y0 + 70), (x + 18, y0 + 90)], 255)
    return np.clip(c.array(), 0, 1)


def chars_column(chars, w, h, size=None, frame=True):
    """Characters stacked top to bottom in a column (an inner forearm, the ribs)."""
    c = Canvas(w, h)
    size = size or min(w * 0.82, h / (len(chars) + 0.4))
    step = h / (len(chars) + 0.3)
    for i, ch in enumerate(chars):
        c.glyph(ch, w / 2, step * (i + 0.65), size)
    if frame:
        c.line([(w * 0.08, step * 0.08), (w * 0.08, h - step * 0.08)], 255, 3)
        c.line([(w * 0.92, step * 0.08), (w * 0.92, h - step * 0.08)], 255, 3)
    return np.clip(c.array(), 0, 1)


def chars_row(chars, w, h, size=None):
    c = Canvas(w, h)
    size = size or min(h * 0.85, w / (len(chars) + 0.3))
    step = w / len(chars)
    for i, ch in enumerate(chars):
        c.glyph(ch, step * (i + 0.5), h / 2, size)
    return np.clip(c.array(), 0, 1)


def emblem(ch, size=600):
    """A character in a double ring with rays (a chest piece)."""
    c = Canvas(size, size)
    m = size / 2
    c.circle(m, m, size * 0.46, None, 255, 10)
    c.circle(m, m, size * 0.4, None, 255, 4)
    for k in range(24):
        a = 2 * math.pi * k / 24
        c.line([(m + math.cos(a) * size * 0.4, m + math.sin(a) * size * 0.4),
                (m + math.cos(a) * size * 0.46, m + math.sin(a) * size * 0.46)], 255, 4)
    c.glyph(ch, m, m, size * 0.55)
    return np.clip(c.array(), 0, 1)


def barbed_band(w=900, h=160):
    c = Canvas(w, h, wrap=True)
    for ph in (0.0, math.pi):
        pts = [(x, h / 2 + h * 0.22 * math.sin(x / w * 2 * math.pi * 4 + ph)) for x in np.linspace(0, w, 120)]
        c.line(pts, 255, 9)
    for k in range(16):
        x = (k + 0.5) * w / 16
        y = h / 2
        c.line([(x - 16, y - 20), (x + 16, y + 20)], 255, 7)
        c.line([(x - 16, y + 20), (x + 16, y - 20)], 255, 7)
    return np.clip(c.array(), 0, 1)


def flame_band(w=900, h=420, seed=9):
    """Tribal flames licking up the arm."""
    rng = np.random.default_rng(seed)
    c = Canvas(w, h, wrap=True)
    for i in range(9):
        x = i * w / 9
        top = rng.uniform(0.05, 0.35) * h
        pts = [(x - 30, h), (x - 40, h * 0.7), (x - 10, h * 0.5), (x - 25, top + 40), (x + 5, top),
               (x + 10, h * 0.45), (x + 45, h * 0.6), (x + 40, h)]
        c.poly(pts, 255)
        c.poly([(x - 8, h * 0.95), (x - 12, h * 0.75), (x + 2, h * 0.62), (x + 15, h * 0.8), (x + 12, h * 0.95)], 0)
    return np.clip(c.array(), 0, 1)


def stripes_chest(w=800, h=600, seed=21):
    """Tiger stripes across the chest, from the sides in."""
    rng = np.random.default_rng(seed)
    c = Canvas(w, h)
    for side in (0, 1):
        for i in range(7):
            y = h * (0.12 + 0.12 * i) + rng.uniform(-8, 8)
            length = rng.uniform(0.18, 0.34) * w
            x0 = 0 if side == 0 else w
            sgn = 1 if side == 0 else -1
            pts_t, pts_b = [], []
            for k in np.linspace(0, 1, 14):
                x = x0 + sgn * length * k
                yy = y + 18 * math.sin(k * 4 + i)
                wd = 16 * (1 - k) ** 0.7
                pts_t.append((x, yy - wd))
                pts_b.append((x, yy + wd))
            c.poly(pts_t + pts_b[::-1], 255)
    return np.clip(c.array(), 0, 1)


# ====================================================================== mapping onto the body
def _sample(img, u, v):
    """Bilinear lookup; u, v in 0..1 (u wraps if the image wraps; outside = 0)."""
    h, w = img.shape
    x = u * (w - 1)
    y = v * (h - 1)
    inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
    x = np.clip(x, 0, w - 1)
    y = np.clip(y, 0, h - 1)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx, fy = x - x0, y - y0
    out = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy)
           + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)
    return np.where(inside, out, 0.0)


def _limb_angle(P, joints, front=(0.0, -1.0, 0.0)):
    """Angle round a limb (0..1, 0 = front), smooth across the joints."""
    s, _ = __import__("common").limb_coord(P, joints)
    js = [np.array(j[:]) for j in joints]
    lens = np.cumsum([0.0] + [np.linalg.norm(js[i + 1] - js[i]) for i in range(len(js) - 1)])
    seg = np.clip(np.searchsorted(lens, s) - 1, 0, len(js) - 2)
    a = np.array([js[i] for i in seg])
    b = np.array([js[i + 1] for i in seg])
    ax = (b - a) / np.linalg.norm(b - a, axis=1, keepdims=True)
    f = np.array(front)
    ref = f - (ax @ f)[:, None] * ax
    ref /= np.linalg.norm(ref, axis=1, keepdims=True)
    ref2 = np.cross(ax, ref)
    rel = P - a
    ang = np.arctan2(np.sum(rel * ref2, 1), np.sum(rel * ref, 1))
    return (ang / (2 * math.pi)) % 1.0, s


def ink(P, N, reg, rest_hand):
    """Three ink layers (sets) for body texels. P, N: (n, 3); reg: body regions."""
    n = len(P)
    out = np.zeros((n, 3), dtype=np.float32)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    designs = {
        "dragon": dragon_sleeve(),
        "koi": koi_sleeve(),
        "tiger": tiger_band(),
        "loyal": chars_column("忠義", 220, 520),
        "brothers": chars_column("兄弟", 220, 520, frame=False),
        "sky": chars_column("天地人", 200, 640, frame=False),
        "hung": emblem("洪"),
        "barbed": barbed_band(),
        "flames": flame_band(),
        "chest_stripes": stripes_chest(),
        "knuckles": chars_row("忠義仁勇", 800, 200),
        "neck1": chars_column("義", 200, 240, frame=False),
        "neck2": chars_column("勇", 200, 240, frame=False),
        "neck3": chars_column("殺", 200, 240, frame=False),
        "hand1": chars_row("忍", 240, 240),
        "hand2": emblem("龍", 400),
    }
    arms = {}
    for s in ("L", "R"):
        joints = [J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"]]
        theta, sa = _limb_angle(P, joints)
        if s == "R":
            theta = (1.0 - theta) % 1.0  # mirror: designs read the same way on both arms
        arms[s] = (theta, sa, reg[f"arm_{s}"])
    L = ARM_LEN["L"]
    up = UPPER_ARM_LEN

    def sleeve(img, s, s0, s1, th0=0.0, k=0):
        theta, sa, m = arms[s]
        v = (sa - s0) / (s1 - s0)
        val = _sample(img, (theta + th0) % 1.0, v) * m
        fade = ss((sa - s0) / 0.02) * ss((s1 - sa) / 0.02)
        out[:, k] = np.maximum(out[:, k], val * fade)

    def panel(img, s, s0, s1, th_c, th_w, k):
        """A flat design on part of a limb (characters on the inner forearm)."""
        theta, sa, m = arms[s]
        u = ((theta - th_c + 0.5) % 1.0 - 0.5) / th_w + 0.5
        v = (sa - s0) / (s1 - s0)
        out[:, k] = np.maximum(out[:, k], _sample(img, u, v) * m)

    # ---- set 0: dragon sleeve on the right arm, loyalty down the left forearm, a dragon on the back of
    # the right hand, 義 on the side of the neck, the 洪 emblem in the middle of the chest.
    sleeve(designs["dragon"], "R", 0.02, L - 0.02, 0.0, 0)
    panel(designs["loyal"], "L", up + 0.04, L - 0.03, 0.5, 0.22, 0)
    # ---- set 1: koi sleeve on the left arm, tiger stripes round the right upper arm, stripes across
    # the chest, 勇 on the back of the neck, knuckle characters on both hands.
    sleeve(designs["koi"], "L", 0.02, L - 0.02, 0.3, 1)
    sleeve(designs["tiger"], "R", 0.04, up - 0.02, 0.0, 1)
    # ---- set 2: flames on both upper arms, barbed wire under the elbows, 天地人 down the ribs,
    # 兄弟 on the outer right forearm, 殺 on the throat side.
    for s in ("L", "R"):
        sleeve(designs["flames"], s, 0.03, up * 0.75, 0.0, 2)
        sleeve(designs["barbed"], s, up + 0.03, up + 0.07, 0.0, 2)
    panel(designs["brothers"], "R", up + 0.06, L - 0.05, 0.0, 0.24, 2)
    # Chest and ribs (front, flat).
    tor = reg["torso"]
    fr = (N[:, 1] < -0.25) & tor
    u = (x + 0.12) / 0.24
    v = (1.44 - z) / 0.24
    out[:, 0] = np.maximum(out[:, 0], _sample(designs["hung"], (x + 0.09) / 0.18, (1.40 - z) / 0.18) * fr)
    out[:, 1] = np.maximum(out[:, 1], _sample(designs["chest_stripes"], (x + 0.17) / 0.34, (1.42 - z) / 0.26) * fr)
    side = tor & (np.abs(x) > 0.11) & (np.abs(N[:, 0]) > 0.5)
    out[:, 2] = np.maximum(out[:, 2], _sample(designs["sky"], (y + 0.05) / 0.1, (1.3 - z) / 0.3) * side * (x > 0))
    # Neck (the head mesh's neck and the base of the body's): angle round the neck, height.
    neck = (z > 1.43) & (z < 1.58) & (np.sqrt(x * x + (y - 0.01) ** 2) < 0.08)
    ang = (np.arctan2(x, -(y - 0.01)) / (2 * math.pi)) % 1.0       # 0 = throat, 0.25 = left side
    for k, key, centre in ((0, "neck1", 0.25), (1, "neck2", 0.5), (2, "neck3", 0.8)):
        uu = ((ang - centre + 0.5) % 1.0 - 0.5) / 0.14 + 0.5
        vv = (1.555 - z) / 0.09
        out[:, k] = np.maximum(out[:, k], _sample(designs[key], uu, vv) * neck)
    # Backs of the hands.
    for s, sx in (("L", 1.0), ("R", -1.0)):
        inv = np.array(rest_hand[s].inverted())
        Q = P @ inv[:3, :3].T + inv[:3, 3]
        back = (Q[:, 2] > 0.004) & (Q[:, 1] > -0.01) & (Q[:, 1] < 0.11) & (np.abs(Q[:, 0]) < 0.05)
        uu = (Q[:, 0] * sx + 0.04) / 0.08
        vv = (Q[:, 1] - 0.0) / 0.08
        if s == "R":
            out[:, 0] = np.maximum(out[:, 0], _sample(designs["hand2"], uu, vv) * back)
        knuck = (Q[:, 2] > 0.0) & (Q[:, 1] > 0.09) & (Q[:, 1] < 0.125)
        out[:, 1] = np.maximum(out[:, 1], _sample(designs["knuckles"], (Q[:, 0] * -sx + 0.04) / 0.08,
                                                  (Q[:, 1] - 0.09) / 0.035) * knuck)
    return np.clip(out, 0, 1)


def preview(path):
    """All the designs on one sheet (docs)."""
    tiles = [dragon_sleeve(), koi_sleeve(), np.pad(tiger_band(), ((490, 490), (0, 0))),
             np.pad(flame_band(), ((540, 540), (0, 0)))]
    sheet = np.concatenate(tiles, 1)
    Image.fromarray((255 - sheet * 255).astype(np.uint8)).resize((sheet.shape[1] // 3, sheet.shape[0] // 3)).save(path)
