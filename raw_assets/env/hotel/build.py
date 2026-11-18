"""Material library for the Golden Dragon hotel lobby (map 2, owner 2026-11-18).

Same contract as ../materials/build.py (one texture array per map, layer index
and tile size in materials.json, read by envkit and the world shader), but
its own array: the hotel only loads what it uses.

  - New procedural layers for a five-star Chinese lobby: polished Calacatta
    marble, Nero Marquina (black, white veins), polished brass, a red-and-gold
    medallion carpet, rosewood wall panelling, gold silk wall fabric with an
    auspicious-cloud weave, and back-lit amber onyx (emission mask).
  - A sign and art atlas: the hotel's name, wayfinding (reception, lifts,
    ballroom, bar, exit, staff only), lift indicators and call plates, two
    ink-landscape paintings, a calligraphy scroll. Real Traditional Chinese in
    the vendored Noto fonts (SIL OFL).
  - Layers shared with Chinatown (plaster, concrete, glass, lacquer...) are
    cut out of the existing world arrays, not rebuilt, so they match exactly.

Run: python3 raw_assets/env/hotel/build.py [--size 1024]
Writes assets/env/hotel/hotel_{albedo,normal,orm}.webp + materials.json, and a
contact sheet at raw_assets/env/hotel/_cache/contact.png.
"""
import importlib.util
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
from texsynth import Synth  # noqa: E402

S = 1024
for i, a in enumerate(sys.argv):
    if a == "--size":
        S = int(sys.argv[i + 1])
OUT = os.path.join(ROOT, "assets", "env", "hotel")
CACHE = os.path.join(HERE, "_cache")
WORLD = os.path.join(ROOT, "assets", "env", "world")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The world builder's helpers (result(), wood_grain()) and the atlas canvas.
W = _load("world_materials", os.path.join(HERE, "..", "materials", "build.py"))
A = _load("world_atlases", os.path.join(HERE, "..", "atlases", "build.py"))
result = W.result

# Layers reused from the Chinatown array, in this order first.
REUSED = ["plaster", "concrete", "darkwood", "lacquer", "glass", "emissive", "paint_metal", "galv", "grate",
          "epoxy", "canvas", "plastic", "cardboard", "terrazzo", "wallpaper", "stone", "lantern"]

MATS = []


def material(name, tile_m, tint=False, seed=0):
    def deco(fn):
        MATS.append(dict(name=name, tile_m=tile_m, tint=tint, fn=fn, seed=seed or (abs(hash(name)) % 9973)))
        return fn
    return deco


def veins(s, freq, warp, width, seed_shift=0.0):
    """Marble veins: thin bright lines along a warped diagonal field."""
    n1 = s.noise(beta=2.6, fmin=1) * warp
    n2 = s.noise(beta=1.8, fmin=3) * warp * 0.35
    # Integer cycles across the tile in x and y, so it tiles.
    f = (2.0 * s.x + s.y) / s.tile_m * freq + n1 + n2 + seed_shift
    line = np.abs(np.sin(f * math.pi))
    main = s.smooth(width, 0.0, line)
    fine = s.smooth(width * 0.35, 0.0, np.abs(np.sin((f * 3.0 + s.noise(beta=2.0, fmin=4) * 2.0) * math.pi)))
    return main, fine


def slabs(s, w, h, gap):
    cid, u, v, edge = s.grid(int(round(s.tile_m / w)), int(round(s.tile_m / h)), gap_m=gap)
    return cid, edge


# ===================================================================== stone

@material("marble", 2.4)
def marble(s):
    """Polished Calacatta: warm white, grey-gold veins, 1.2 m slabs with hairline joints."""
    cid, edge = slabs(s, 1.2, 1.2, 0.0016)
    main, fine = veins(s, 2, 2.2, 0.06)
    cloud = s.noise(beta=2.8, fmin=1) * 0.5 + s.noise(beta=1.5, fmin=10) * 0.5
    alb = s.fill((0.86, 0.84, 0.8)) * (1 + cloud[..., None] * 0.035)
    alb = s.mix(alb, s.col((0.52, 0.47, 0.4)), main * 0.75)
    alb = s.mix(alb, s.col((0.66, 0.62, 0.56)), fine * 0.45)
    gold = s.smooth(1.2, 2.2, s.noise(beta=2.2, fmin=2)) * main
    alb = s.mix(alb, s.col((0.62, 0.5, 0.3)), gold * 0.5)
    joint = s.smooth(0.0, 0.0012, edge)
    alb = alb * (0.55 + 0.45 * joint[..., None])
    # Abandoned: dust dulls it in patches, scuffs where feet went.
    dust = s.smooth(0.4, 2.2, s.noise(beta=2.5, fmin=1))
    scuff = s.smooth(2.0, 3.0, s.noise(beta=0.5, fmin=30, aniso=(1.0, 0.25)))
    alb = s.mix(alb, s.col((0.6, 0.58, 0.55)), dust * 0.12)
    h = -main * 0.00015 - (1 - joint) * 0.0008
    rough = 0.07 + dust * 0.22 + scuff * 0.15 + (1 - joint) * 0.4
    return result(alb, h, rough, s=s, ao_k=0.15, nstr=0.6)


@material("marble_dark", 2.4)
def marble_dark(s):
    """Nero Marquina: near-black with sharp white veins (borders, columns, the desk)."""
    cid, edge = slabs(s, 0.6, 1.2, 0.0016)
    main, fine = veins(s, 4, 3.0, 0.035, 1.3)
    alb = s.fill((0.035, 0.034, 0.036)) * (1 + s.noise(beta=2.4, fmin=2)[..., None] * 0.15)
    alb = s.mix(alb, s.col((0.78, 0.77, 0.74)), main * 0.85)
    alb = s.mix(alb, s.col((0.35, 0.34, 0.33)), fine * 0.5)
    joint = s.smooth(0.0, 0.0012, edge)
    dust = s.smooth(0.2, 2.2, s.noise(beta=2.5, fmin=1))
    alb = s.mix(alb, s.col((0.16, 0.155, 0.15)), dust * 0.25)
    h = -(1 - joint) * 0.0008
    rough = 0.06 + dust * 0.3 + (1 - joint) * 0.4
    return result(alb, h, rough, s=s, ao_k=0.1, nstr=0.6)


@material("onyx", 1.6)
def onyx(s):
    """Back-lit amber onyx: banded, translucent (the albedo alpha lets it glow)."""
    n = s.noise(beta=2.4, fmin=1) * 3.0 + s.noise(beta=1.6, fmin=4) * 0.6
    T = s.tile_m
    bands = 0.5 + 0.5 * np.sin((s.y / T * 4.0 + n) * math.pi)
    fine = 0.5 + 0.5 * np.sin((s.y / T * 24.0 + n * 3.0) * math.pi)
    alb = s.mix(s.fill((0.55, 0.25, 0.05)), s.col((0.95, 0.72, 0.38)), bands * 0.7 + fine * 0.3)
    crack = s.smooth(0.03, 0.0, np.abs(np.sin(((s.x + s.y) / T * 2.0 + n * 0.7) * math.pi)))
    alb = s.mix(alb, s.col((0.3, 0.12, 0.03)), crack * 0.6)
    emit = np.clip(0.55 + bands * 0.35 + fine * 0.1 - crack * 0.4, 0, 1)
    h = -crack * 0.0002
    return result(alb, h, 0.08, s=s, ao_k=0.0, emit=emit, nstr=0.4)


# ===================================================================== metal, wood, fabric

@material("brass", 1.0, tint=True)
def brass(s):
    """Polished brass (tint for bronze or dark gold): fine brushing, fingerprints, tarnish."""
    brush = s.noise(beta=0.6, fmin=200, aniso=(1.0, 0.02))
    alb = s.fill((0.78, 0.6, 0.3)) * (1 + brush[..., None] * 0.04)
    tarnish = s.smooth(0.6, 2.2, s.noise(beta=2.4, fmin=2))
    alb = s.mix(alb, s.col((0.36, 0.26, 0.12)), tarnish * 0.45)
    prints = s.smooth(2.2, 2.9, s.noise(beta=1.0, fmin=40))
    h = brush * 0.00003
    rough = 0.16 + tarnish * 0.25 + prints * 0.15 + np.abs(brush) * 0.04
    return result(alb, h, rough, metal=1.0, s=s, ao_k=0.0, nstr=0.4)


@material("rosewood", 2.4)
def rosewood(s):
    """Lacquered rosewood wall panels: 0.6 m boards, V-grooves, deep red-brown."""
    cid, u, v, edge = s.grid(4, 1, gap_m=0.006)
    n = s.noise(beta=2.0, fmin=1, aniso=(1.0, 0.15))
    g = np.sin((s.x / s.tile_m * 40.0 + n * 1.5) * np.pi * 2) * 0.5 + 0.5
    g = np.clip(g * 0.8 + s.noise(beta=1.0, fmin=30, aniso=(1.0, 0.08)) * 0.15, 0, 1)
    tone = s.rand_per_id(cid)
    alb = s.mix(s.col((0.12, 0.035, 0.02)), s.col((0.24, 0.08, 0.035)), g)
    alb = alb * (0.85 + tone[..., None] * 0.3)
    groove = s.smooth(0.0, 0.004, edge)
    alb = alb * (0.35 + 0.65 * groove[..., None])
    dust = s.smooth(0.8, 2.4, s.noise(beta=2.4, fmin=2))
    alb = s.mix(alb, s.col((0.2, 0.16, 0.13)), dust * 0.15)
    h = groove * 0.003 + g * 0.0002
    rough = 0.22 + (1 - g) * 0.1 + dust * 0.3 + (1 - groove) * 0.4
    return result(alb, h, rough, s=s, ao_k=0.6, nstr=1.2)


@material("carpet", 2.0)
def carpet(s):
    """Hotel carpet: deep red, a gold medallion every metre, dark-red lattice, worn paths."""
    lx = ((s.x + 0.5) % 1.0) - 0.5
    ly = ((s.y + 0.5) % 1.0) - 0.5
    r = np.sqrt(lx ** 2 + ly ** 2)
    th = np.arctan2(ly, lx)
    petals = s.smooth(0.015, 0.0, r - (0.12 + 0.05 * np.abs(np.cos(th * 4))))
    ring = s.smooth(0.01, 0.0, np.abs(r - 0.24 - 0.015 * np.cos(th * 16)))
    core = s.smooth(0.05, 0.03, r)
    lat = s.smooth(0.012, 0.0, np.abs(np.abs(lx) + np.abs(ly) - 0.5))
    gold = np.clip(petals * 0.9 + ring + core, 0, 1)
    pile = s.noise(beta=0.0, fmin=250) * 0.5 + s.noise(beta=1.0, fmin=60) * 0.5
    base = s.fill((0.28, 0.03, 0.035)) * (1 + pile[..., None] * 0.12)
    alb = s.mix(base, s.col((0.12, 0.012, 0.016)), lat * 0.9)
    alb = s.mix(alb, s.col((0.62, 0.43, 0.14)), gold * 0.9)
    alb = s.mix(alb, s.col((0.05, 0.02, 0.02)), (petals * (1 - core)) * 0.25)
    wear = s.smooth(0.5, 2.0, s.noise(beta=2.6, fmin=1))
    alb = s.mix(alb, alb * 0.65 + 0.03, wear * 0.4)
    h = pile * 0.0006 + gold * 0.0005
    rough = 0.95
    return result(alb, h, rough, s=s, ao_k=0.5, nstr=1.0)


@material("silk", 1.0, tint=True)
def silk(s):
    """Gold silk wall fabric with a woven auspicious-cloud motif (tintable)."""
    cw, chh = 0.25, 0.25
    row = np.floor(s.y / chh)
    lx = ((s.x / cw + (row % 2) * 0.5) % 1.0) - 0.5
    ly = (s.y / chh % 1.0) - 0.5
    # cloud: three lobes and a curl
    c1 = np.sqrt((lx + 0.12) ** 2 + (ly * 1.2) ** 2)
    c2 = np.sqrt((lx - 0.1) ** 2 + ((ly + 0.06) * 1.2) ** 2)
    c3 = np.sqrt(lx ** 2 + ((ly - 0.1) * 1.2) ** 2)
    rim = s.smooth(0.012, 0.0, np.abs(np.minimum(np.minimum(c1 - 0.11, c2 - 0.09), c3 - 0.08)))
    weave = np.sin(s.x / 0.00125 * np.pi) * 0.5 + np.sin(s.y / 0.001 * np.pi) * 0.5
    alb = s.fill((0.6, 0.5, 0.3)) * (1 + weave[..., None] * 0.03)
    alb = s.mix(alb, s.col((0.78, 0.66, 0.38)), rim * 0.7)
    stain = s.streak(s.smooth(1.2, 2.4, s.noise(beta=1.8, fmin=3)), 90)
    alb = alb * (1 - np.clip(stain * 1.5, 0, 0.35)[..., None])
    h = rim * 0.0002 + weave * 0.00002
    rough = 0.55 - rim * 0.2
    return result(alb, h, rough, metal=rim * 0.3, s=s, ao_k=0.2)


# ===================================================================== atlas

GOLD = A.GOLD
C = A.C


def painting(cv, name, x0, y0, x1, y1, seed, mist=(232, 226, 210)):
    """A shan shui: layered ink mountains, mist bands, a pine, in a gold frame."""
    cv.rect(name, x0, y0, x1, y1)
    cv.box(x0, y0, x1, y1, col=GOLD, h=90, r=90, m=200)
    b = 16
    cv.box(x0 + b, y0 + b, x1 - b, y1 - b, col=C(*mist), h=30, r=200, m=0)
    rng = np.random.default_rng(seed)
    w, hgt = x1 - x0 - 2 * b, y1 - y0 - 2 * b
    for layer in range(5):
        base = y0 + b + hgt * (0.35 + layer * 0.14)
        tone = int(170 - layer * 32)
        pts = [(x0 + b, y1 - b)]
        n = 14
        ph = rng.uniform(0, 6)
        for i in range(n + 1):
            x = x0 + b + w * i / n
            peak = math.sin(i * 0.9 + ph) * 0.5 + math.sin(i * 2.3 + ph * 2) * 0.25 + rng.uniform(-0.15, 0.15)
            y = base - hgt * (0.12 + 0.18 * max(peak, -0.3)) * (1.1 - layer * 0.12)
            pts.append((x, y))
        pts.append((x1 - b, y1 - b))
        cv.dc.polygon([tuple(cv.px(*p)) for p in pts], fill=C(tone * 0.85, tone * 0.86, tone * 0.82))
        cv.dh.polygon([tuple(cv.px(*p)) for p in pts], fill=20 + layer * 6)
    # seal
    cv.box(x1 - b - 46, y0 + b + 20, x1 - b - 20, y0 + b + 46, col=C(170, 20, 18), h=50)
    cv.weather(x0, y0, x1, y1, 0.4, streaks=False)


def hotel_atlas(S):
    cv = A.Canvas(S, 31)
    SERIF, SANS = A.SERIF, A.SANS
    # Row 0: the hotel's name, gold on black lacquer (over the desk and outside).
    A.board(cv, "logo", 0, 0, 1024, 176, C(14, 12, 12), GOLD, "金龍大酒店", "GOLDEN DRAGON GRAND HOTEL")
    # Row 1: wayfinding, brass letters on black.
    A.board(cv, "reception", 0, 176, 512, 272, C(16, 14, 14), GOLD, "接待處", "RECEPTION")
    A.board(cv, "lifts", 512, 176, 1024, 272, C(16, 14, 14), GOLD, "電梯", "LIFTS")
    A.board(cv, "ballroom", 0, 272, 512, 368, C(16, 14, 14), GOLD, "宴會廳", "GRAND BALLROOM")
    A.board(cv, "bar", 512, 272, 1024, 368, C(16, 14, 14), GOLD, "龍吧", "DRAGON BAR  ·  LOUNGE")
    A.board(cv, "exit", 0, 368, 256, 448, C(20, 150, 70), C(240, 255, 240), "出口", "EXIT", font=SANS,
            frame=C(230, 240, 230), lightbox=True)
    A.board(cv, "staff", 256, 368, 640, 448, C(225, 222, 210), C(150, 20, 18), "員工專用", "STAFF ONLY", font=SANS,
            frame=C(150, 20, 18))
    A.board(cv, "toilets", 640, 368, 1024, 448, C(16, 14, 14), GOLD, "洗手間", "RESTROOMS")
    # Lift hall lanterns and indicators: black glass, red LED.
    for i, (lab, x) in enumerate((("ind_up", 0), ("ind_down", 128), ("ind_l", 256), ("ind_9", 384))):
        cv.rect(lab, x, 448, x + 128, 528)
        cv.box(x, 448, x + 128, 528, col=GOLD, h=60, r=100, m=200)
        cv.box(x + 6, 454, x + 122, 522, col=C(8, 6, 6), h=30, r=40, e=0)
        txt = {"ind_up": "▲", "ind_down": "▼", "ind_l": "L", "ind_9": "9"}[lab]
        font = SANS if lab != "ind_up" and lab != "ind_down" else SANS
        if lab in ("ind_up", "ind_down"):
            cx, cy = x + 64, 488
            pts = [(cx - 22, cy + 14), (cx + 22, cy + 14), (cx, cy - 18)] if lab == "ind_up" else [(cx - 22, cy - 14), (cx + 22, cy - 14), (cx, cy + 18)]
            cv.dc.polygon([tuple(cv.px(*p)) for p in pts], fill=C(255, 60, 30))
            cv.de.polygon([tuple(cv.px(*p)) for p in pts], fill=255)
        else:
            cv.text(font, (x + 64, 490), txt, 54, col=C(255, 60, 30), e=255)
    # Call plate: brushed brass with two lit buttons.
    cv.rect("callplate", 512, 448, 640, 640)
    cv.box(512, 448, 640, 640, col=C(190, 150, 80), h=60, r=70, m=230)
    for k, cy in enumerate((510, 580)):
        cv.dc.ellipse(cv.px(556, cy - 20, 596, cy + 20), fill=C(250, 240, 220))
        cv.de.ellipse(cv.px(560, cy - 16, 592, cy + 16), fill=255 if k == 0 else 120)
        cv.dh.ellipse(cv.px(556, cy - 20, 596, cy + 20), fill=110)
    # Scroll: calligraphy 福壽 on cream silk, dark rods.
    cv.rect("scroll", 640, 448, 768, 1024)
    cv.box(640, 448, 768, 1024, col=C(60, 30, 18), h=80, r=120)
    cv.box(650, 470, 758, 1002, col=C(226, 214, 186), h=30, r=200)
    cv.text(SERIF, (704, 650), "福", 96, col=C(20, 18, 16), h=60)
    cv.text(SERIF, (704, 820), "壽", 96, col=C(20, 18, 16), h=60)
    cv.box(712, 920, 732, 940, col=C(170, 20, 18))
    cv.weather(640, 448, 768, 1024, 0.5, streaks=False)
    # Paintings.
    painting(cv, "art_a", 0, 528, 512, 800, 3)
    painting(cv, "art_b", 0, 800, 384, 1024, 9, mist=(220, 214, 196))
    # Lacquer panel with a gold dragon roundel (lift doors, the bar back).
    cv.rect("roundel", 768, 448, 1024, 704)
    cv.box(768, 448, 1024, 704, col=C(110, 14, 12), h=40, r=60)
    cx, cy = 896, 576
    for rr, w_ in ((110, 8), (92, 4), (40, 6)):
        cv.dc.ellipse(cv.px(cx - rr, cy - rr, cx + rr, cy + rr), outline=GOLD, width=int(w_ * cv.k))
        cv.dm.ellipse(cv.px(cx - rr, cy - rr, cx + rr, cy + rr), outline=220, width=int(w_ * cv.k))
        cv.dh.ellipse(cv.px(cx - rr, cy - rr, cx + rr, cy + rr), outline=120, width=int(w_ * cv.k))
    cv.text(SERIF, (cx, cy), "龍", 120, col=GOLD, h=140, m=220, r=80)
    # Floor plan board.
    A.board(cv, "welcome", 384, 800, 640, 1024, C(18, 16, 14), GOLD, "歡迎", "WELCOME", han_size=90)
    # Door plate.
    A.board(cv, "lounge", 768, 704, 1024, 784, C(16, 14, 14), GOLD, "茶室", "TEA LOUNGE")
    A.board(cv, "level2", 768, 784, 1024, 864, C(16, 14, 14), GOLD, "二樓 宴會廳", "LEVEL 2 · BALLROOM")
    A.board(cv, "concierge", 768, 864, 1024, 944, C(16, 14, 14), GOLD, "禮賓部", "CONCIERGE")
    A.board(cv, "guests", 768, 944, 1024, 1024, C(225, 222, 210), C(150, 20, 18), "嘉賓", "GUESTS ONLY", font=SANS,
            frame=C(150, 20, 18))
    return cv.finish()


# ===================================================================== build

def build_layer(m):
    s = Synth(S, m["tile_m"], m["seed"])
    return m["fn"](s)


def world_slices():
    meta = json.load(open(os.path.join(WORLD, "materials.json")))
    ws, cols = meta["size"], meta["cols"]
    alb = np.asarray(Image.open(os.path.join(WORLD, "world_albedo.webp")).convert("RGBA"))
    nrm = np.asarray(Image.open(os.path.join(WORLD, "world_normal.webp")).convert("RGB"))
    orm = np.asarray(Image.open(os.path.join(WORLD, "world_orm.webp")).convert("RGB"))
    out = []
    for name in REUSED:
        L = meta["layers"][name]
        i = L["index"]
        y, x = (i // cols) * ws, (i % cols) * ws
        cut = [arr[y:y + ws, x:x + ws] for arr in (alb, nrm, orm)]
        if ws != S:
            cut = [np.asarray(Image.fromarray(c).resize((S, S), Image.LANCZOS)) for c in cut]
        out.append((name, L, cut))
    return out


def to8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    reused = world_slices()
    new = []
    for m in MATS:
        print("material", m["name"], flush=True)
        new.append((m, build_layer(m)))
    print("atlas hotel", flush=True)
    atlas = hotel_atlas(S)
    total = len(reused) + len(new) + 1
    cols = 6
    rows = (total + cols - 1) // cols
    alb = np.zeros((rows * S, cols * S, 4), np.uint8)
    nrm = np.zeros((rows * S, cols * S, 3), np.uint8)
    nrm[..., :] = (128, 128, 255)
    orm = np.zeros((rows * S, cols * S, 3), np.uint8)
    orm[..., :] = (255, 255, 0)
    meta = {"size": S, "cols": cols, "rows": rows, "layers": {}}
    i = 0
    thumbs = []

    def place(name, a8, n8, o8, info):
        nonlocal i
        y, x = (i // cols) * S, (i % cols) * S
        alb[y:y + S, x:x + S] = a8
        nrm[y:y + S, x:x + S] = n8
        orm[y:y + S, x:x + S] = o8
        info = dict(info)
        info["index"] = i
        meta["layers"][name] = info
        t = Image.new("RGB", (512, 256))
        t.paste(Image.fromarray(a8[..., :3]).resize((256, 256)), (0, 0))
        t.paste(Image.fromarray(o8).resize((256, 256)), (256, 0))
        thumbs.append(t)
        i += 1

    for name, L, (a8, n8, o8) in reused:
        place(name, a8, n8, o8, {k: v for k, v in L.items() if k != "index"})
    for m, r in new + [(dict(name="hotel_atlas", tile_m=1.0, tint=False), atlas)]:
        a8 = np.concatenate([to8(r["albedo"]), to8(r["emit"])[..., None]], -1)
        lin = np.clip(r["albedo"], 0, 1) ** 2.2
        info = {"tile_m": m["tile_m"], "tint": m["tint"],
                "mean_linear": [round(float(c), 4) for c in lin.reshape(-1, 3).mean(0)],
                "rough": round(float(r["orm"][..., 1].mean()), 3)}
        if "rects" in r:
            info["rects"] = r["rects"]
        place(m["name"], a8, to8(r["normal"]), to8(r["orm"]), info)
    Image.fromarray(alb, "RGBA").save(os.path.join(OUT, "hotel_albedo.webp"), quality=92, method=5, exact=True)
    Image.fromarray(nrm, "RGB").save(os.path.join(OUT, "hotel_normal.webp"), quality=94, method=5)
    Image.fromarray(orm, "RGB").save(os.path.join(OUT, "hotel_orm.webp"), quality=92, method=5)
    with open(os.path.join(OUT, "materials.json"), "w") as f:
        json.dump(meta, f, indent=1)
    sheet = Image.new("RGB", (512 * 4, 256 * ((len(thumbs) + 3) // 4)))
    for k, t in enumerate(thumbs):
        sheet.paste(t, ((k % 4) * 512, (k // 4) * 256))
    sheet.save(os.path.join(CACHE, "contact.png"))
    Image.fromarray(alb[-S * (1 if i % cols else 1):, :, :3][:S, ((i - 1) % cols) * S:((i - 1) % cols + 1) * S]).save(
        os.path.join(CACHE, "atlas.png"))
    print("layers:", i, "grid", cols, "x", rows)


if __name__ == "__main__":
    main()
