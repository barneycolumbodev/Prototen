"""Chinatown docks: a night-time city block on the harbour (GRAFT test map).

Run (Blender 5.2 / bpy):
    tools/blender.sh raw_assets/levels/chinatown/build.py -- [--preview out.png] [--blend out.blend]

Writes:
  raw_assets/levels/chinatown/_build/chinatown.blend   scene for the lightmap bake (bake.py)
  assets/levels/chinatown/layout.json                   colliders, spawns, lights, cameras

Plan (Blender coordinates, metres: +X east, +Y north, +Z up; Godot: x, z, -y):

   y=34 ┌──────────────── back tenements (boundary) ─────────────────┐
   y=28 │        back alley (dumpsters, fire escapes, kitchen doors)  │
   y=22 │ hotel │herbal│ SEA VIEW RESTAURANT │bakery│noodle│A│grocery│gold│tea  north row
   y=12 ├─ sidewalk ──────── HARBOUR STREET (lantern strings) ────────────────┤
   y=2  │  PIER 3 COLD STORE  │alley│   FISH MARKET HALL   │road│ tenement   │ south row
   y=-14├──────────────── QUAY (bollards, crates, containers, crane) ──────┤
   y=-24└─ water ── pier ── fishing boat ─────────────────────────────────┘
        x=-46                                                         x=46
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import buildings as B  # noqa: E402
import props as P  # noqa: E402
from envkit import Kit, rot_x, rot_z  # noqa: E402
from props import RNG, pick, rnd  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
MATS = os.path.join(ROOT, "assets", "env", "world", "materials.json")
OUT_DIR = os.path.join(ROOT, "assets", "levels", "chinatown")
BUILD_DIR = os.path.join(HERE, "_build")

XMIN, XMAX, YMIN, YMAX = -46.0, 46.0, -44.0, 34.0
QUAY_EDGE = -24.0
ROAD_Y0, ROAD_Y1 = 4.0, 10.0
ROAD_Z = -0.15
WATER_Z = -2.1

k = Kit(MATS, (XMIN, YMIN, XMAX, YMAX), chunks=(4, 3))


def clip_wall(c, s, yaw=0.0):
    """Invisible wall (blocks people, not bullets)."""
    k.colliders.append({"c": [float(x) for x in c], "s": [float(x) for x in s], "yaw": yaw, "surface": "concrete", "clip": True})


# ====================================================================== ground

def ground():
    k.wet = 1.0
    # street: sunken road, sidewalks at 0, curbs with ramps (no step-up in the controllers)
    k.box((0, (ROAD_Y0 + ROAD_Y1) / 2, ROAD_Z - 0.1), (XMAX - XMIN + 30, ROAD_Y1 - ROAD_Y0, 0.2), "asphalt", faces=["+z"])
    for y, s in ((ROAD_Y0, 1), (ROAD_Y1, -1)):
        k.box((0, y - s * 0.08, -0.075), (XMAX - XMIN + 30, 0.16, 0.15), "stone", (0.45, 0.44, 0.42), faces=["+z", "-y" if s > 0 else "+y", "+y" if s > 0 else "-y"])
        ang = math.degrees(math.atan2(0.15, 0.6))
        k.colliders.append({"c": [0.0, y + s * 0.3, -0.075 - 0.06], "s": [XMAX - XMIN, 0.62, 0.12], "yaw": 0.0, "rx": round(-s * ang, 2), "surface": "concrete"})
    # road markings: dashed centre line, faded
    for x in np.arange(XMIN - 10, XMAX + 10, 4.0):
        k.box((x, (ROAD_Y0 + ROAD_Y1) / 2, ROAD_Z + 0.001), (2.0, 0.12, 0.002), "paint_metal", (0.55, 0.5, 0.3), faces=["+z"])
    # sidewalks
    k.box((0, 3.0, -0.05), (XMAX - XMIN + 30, 2.0, 0.1), "pavers", faces=["+z"])
    k.box((0, 11.0, -0.05), (XMAX - XMIN + 30, 2.0, 0.1), "pavers", faces=["+z"])
    # quay and yards
    k.box((0, (QUAY_EDGE + 2.0) / 2, -0.25), (XMAX - XMIN + 30, 2.0 - QUAY_EDGE, 0.5), "concrete", faces=["+z"])
    # quay face, fender beams and tyres
    k.box((0, QUAY_EDGE - 0.15, -1.5), (XMAX - XMIN + 30, 0.3, 3.0), "concrete", (0.4, 0.42, 0.42), faces=["-y"])
    k.box((0, QUAY_EDGE - 0.35, -0.12), (XMAX - XMIN + 30, 0.4, 0.24), "concrete", (0.5, 0.5, 0.48))
    for x in np.arange(XMIN - 8, XMAX + 8, 3.0):
        if -31.5 < x < -24.5:
            continue
        k.box((x, QUAY_EDGE - 0.42, -1.2), (0.25, 0.25, 2.0), "planks", (0.4, 0.38, 0.33), uv_scale=1)
        if int(x) % 2 == 0:
            P.tyre(k, (x + 1.5, QUAY_EDGE - 0.55, -0.9), rot_z(0) @ rot_x(0), r=0.36, tube=0.12)
    # algae band at the waterline
    k.box((0, QUAY_EDGE - 0.32, WATER_Z + 0.3), (XMAX - XMIN + 30, 0.02, 0.8), "rust", (0.22, 0.3, 0.2), faces=["-y"])
    # back alley and lanes
    k.box((0, 25.0, -0.05), (62.0, 6.0, 0.1), "concrete", (0.42, 0.42, 0.42), faces=["+z"])
    k.box((4.5, 17.0, -0.05), (3.0, 10.0, 0.1), "concrete", (0.42, 0.42, 0.42), faces=["+z"])
    # the ground collider for the whole map (one big slab), the road slab a bit lower
    W = XMAX - XMIN + 30
    k.colliders.append({"c": [0.0, (QUAY_EDGE + ROAD_Y0) / 2, -0.5], "s": [W, ROAD_Y0 - QUAY_EDGE, 1.0], "yaw": 0, "surface": "concrete"})
    k.colliders.append({"c": [0.0, (ROAD_Y0 + ROAD_Y1) / 2, ROAD_Z - 0.5], "s": [W, ROAD_Y1 - ROAD_Y0, 1.0], "yaw": 0, "surface": "concrete"})
    k.colliders.append({"c": [0.0, (ROAD_Y1 + YMAX) / 2, -0.5], "s": [W, YMAX - ROAD_Y1, 1.0], "yaw": 0, "surface": "concrete"})
    # drains and manholes (wisps of steam come out of these in Godot)
    for x, y in ((-26.0, 7.0), (2.0, 6.2), (24.0, 7.6), (-6.0, -18.0), (14.0, 25.0)):
        z = ROAD_Z if ROAD_Y0 < y < ROAD_Y1 else 0.0
        k.cyl((x, y, z - 0.01), (x, y, z + 0.012), 0.38, "grate", (0.5, 0.5, 0.5), sides=16)
        k.marker("steam", (x, y, z + 0.05), rate=1.0)
    for x in np.arange(XMIN + 4, XMAX - 2, 9.0):
        for y in (ROAD_Y0 + 0.25, ROAD_Y1 - 0.25):
            k.box((x, y, ROAD_Z + 0.004), (0.9, 0.35, 0.01), "grate", faces=["+z"])


def water_walls():
    """Invisible walls along the quay edge, pier and boat so nobody falls in."""
    clip_wall(((XMIN + -31.2) / 2, QUAY_EDGE - 0.4, 1.0), (-31.2 - XMIN, 0.3, 4.0))
    clip_wall(((-25.0 + XMAX) / 2, QUAY_EDGE - 0.4, 1.0), (XMAX + 25.0, 0.3, 4.0))
    clip_wall((-31.2, -33.5, 1.0), (0.3, 19.0, 4.0))
    clip_wall((-28.0, -43.2, 1.0), (6.6, 0.3, 4.0))
    clip_wall((-24.8, -28.5, 1.0), (0.3, 9.0, 4.0))   # pier east edge north of the gangway
    clip_wall((-24.8, -40.0, 1.0), (0.3, 6.0, 4.0))   # south of the gangway
    for c, s in (((XMIN - 0.2, (YMIN + YMAX) / 2, 4), (0.3, YMAX - YMIN, 12)), ((XMAX + 0.2, (YMIN + YMAX) / 2, 4), (0.3, YMAX - YMIN, 12)),
                 ((0, YMAX + 0.2, 4), (XMAX - XMIN, 0.3, 12))):
        clip_wall(c, s)


# ====================================================================== the pier and the boat

def pier():
    x0, x1, y0, y1 = -31.0, -25.0, -43.0, QUAY_EDGE
    k.box(((x0 + x1) / 2, (y0 + y1) / 2, -0.12), (x1 - x0, y1 - y0, 0.24), "planks", (0.5, 0.48, 0.44), col="wood")
    for x in (x0 + 0.3, (x0 + x1) / 2, x1 - 0.3):
        for y in np.arange(y0 + 0.4, y1, 3.0):
            k.cyl((x, y, -3.5), (x, y, -0.24), 0.17, "darkwood", (0.5, 0.45, 0.42), sides=9)
            k.cyl((x, y, WATER_Z - 0.2), (x, y, WATER_Z + 0.5), 0.18, "rust", (0.25, 0.32, 0.22), sides=9)
    for y in np.arange(y0 + 0.4, y1, 3.0):
        k.box(((x0 + x1) / 2, y, -0.4), (x1 - x0, 0.2, 0.25), "darkwood", (0.5, 0.45, 0.42))
    # low timber kerb on the west edge, bollards and cleats
    k.box((x0 + 0.1, (y0 + y1) / 2, 0.08), (0.2, y1 - y0, 0.16), "darkwood", (0.55, 0.5, 0.45), col="wood")
    for y in (-27.0, -33.0, -39.0):
        P.bollard(k, (x1 - 0.5, y, 0.0))
    # lamp at the end of the pier
    P.street_lamp(k, (x0 + 0.5, y0 + 1.0, 0.0), yaw=90, height=5.0, reach=1.0)
    P.crate_stack(k, (x0 + 1.2, -30.0, 0.0), 90, rows=3, cols=2)
    P.net_pile(k, (x0 + 1.5, -36.0, 0.0), 1.6)
    P.rope_coil(k, (x1 - 1.2, -35.0, 0.0))
    P.styro_stack(k, (x0 + 0.9, -41.0, 0.0), 10, n=4)
    k.marker("spawn", (-28.0, -41.5, 0.0), name="pier_end")


def boat():
    """Steel-hulled fishing boat moored east of the pier; deck at z = -0.4."""
    cx, ys, yb = -20.6, -41.5, -26.5  # stern, bow
    L = yb - ys
    deck = -0.4
    top = deck + 0.9
    keel = WATER_Z - 1.6
    n = 14
    secs = []
    for i in range(n + 1):
        t = i / n
        hw = 2.4 * (1.0 if t < 0.55 else math.cos((t - 0.55) / 0.45 * math.pi / 2) ** 0.8)
        hw = max(hw, 0.05)
        sheer = top + 0.6 * max(0, t - 0.6) ** 2 * 2.5
        y = ys + t * L
        secs.append((y, hw, sheer))
    verts, faces_out, faces_in = [], [], []
    prof = lambda hw, sheer: [(-hw, sheer), (-hw * 0.99, WATER_Z + 0.3), (-hw * 0.8, keel + 0.8), (-hw * 0.3, keel + 0.15), (0.0, keel),
                              (hw * 0.3, keel + 0.15), (hw * 0.8, keel + 0.8), (hw * 0.99, WATER_Z + 0.3), (hw, sheer)]
    m = 9
    for (y, hw, sheer) in secs:
        for (x, z) in prof(hw, sheer):
            verts.append((cx + x, y, z))
    upper, lower = [], []
    for i in range(n):
        for j in range(m - 1):
            a, b = i * m + j, i * m + j + 1
            c, d = (i + 1) * m + j + 1, (i + 1) * m + j
            f = [a, d, c, b]
            (upper if j in (0, m - 2) else lower).append(f)
    V = np.array(verts)
    k.mesh(V, upper, np.eye(3), np.zeros(3), "paint_metal", (0.12, 0.3, 0.38), smooth=True, uv_origin=np.zeros(3))
    k.mesh(V, lower, np.eye(3), np.zeros(3), "paint_metal", (0.45, 0.1, 0.08), smooth=True, uv_origin=np.zeros(3))
    # transom
    y, hw, sheer = secs[0]
    k.quad((cx - hw, y, WATER_Z + 0.3), (cx + hw, y, WATER_Z + 0.3), (cx + hw, y, sheer), (cx - hw, y, sheer), "paint_metal", (0.12, 0.3, 0.38))
    # inner bulwark (inside faces) and deck
    for i in range(n):
        y0_, hw0, s0 = secs[i]
        y1_, hw1, s1 = secs[i + 1]
        for sgn in (-1, 1):
            a = (cx + sgn * (hw0 - 0.06), y0_, deck)
            b = (cx + sgn * (hw1 - 0.06), y1_, deck)
            c_ = (cx + sgn * (hw1 - 0.06), y1_, s1)
            d = (cx + sgn * (hw0 - 0.06), y0_, s0)
            if sgn < 0:  # inside faces look toward the centreline
                k.quad(a, b, c_, d, "paint_metal", (0.5, 0.5, 0.48))
            else:
                k.quad(b, a, d, c_, "paint_metal", (0.5, 0.5, 0.48))
            # rubbing strake
            k.tube([(cx + sgn * (hw0 + 0.02), y0_, s0 - 0.25), (cx + sgn * (hw1 + 0.02), y1_, s1 - 0.25)], 0.06, "darkwood", (0.4, 0.38, 0.35), sides=5)
        k.quad((cx - hw0 + 0.06, y0_, deck), (cx + hw0 - 0.06, y0_, deck), (cx + hw1 - 0.06, y1_, deck), (cx - hw1 + 0.06, y1_, deck), "planks", (0.45, 0.42, 0.38))
        k.box((cx, (y0_ + y1_) / 2, s0 + 0.03), (0.01, 0.01, 0.01), "galv")  # (keeps chunk extents sane)
    # colliders: deck, hull sides (walls)
    k.collider((cx, (ys + yb) / 2 - 1.0, deck - 0.3), (4.6, L - 2.0, 0.6), 0, "wood")
    k.collider((cx, yb - 1.2, deck - 0.3), (2.4, 2.4, 0.6), 0, "wood")
    for sgn in (-1, 1):
        k.collider((cx + sgn * 2.35, (ys + yb) / 2 - 1.5, deck + 0.45), (0.15, L - 3.0, 0.9), 0, "sheet_metal")
        clip_wall((cx + sgn * 2.5, (ys + yb) / 2, deck + 1.5), (0.2, L + 1.0, 3.0))
    k.collider((cx, ys + 0.05, deck + 0.45), (4.8, 0.15, 0.9), 0, "sheet_metal")
    clip_wall((cx, ys - 0.3, deck + 1.5), (5.0, 0.2, 3.0))
    clip_wall((cx, yb + 0.6, deck + 1.5), (2.0, 0.3, 3.0))
    # wheelhouse aft
    wy0, wy1 = ys + 1.2, ys + 4.6
    k.box((cx, (wy0 + wy1) / 2, deck + 1.15), (3.2, wy1 - wy0, 2.3), "paint_metal", (0.58, 0.58, 0.55), col="sheet_metal", chamfer=0.05)
    k.box((cx, (wy0 + wy1) / 2, deck + 2.36), (3.5, wy1 - wy0 + 0.4, 0.12), "paint_metal", (0.2, 0.32, 0.36), chamfer=0.03)
    for sgn in (-1, 1):
        k.quad((cx + sgn * 1.602, wy0 + 0.4 if sgn > 0 else wy1 - 0.4, deck + 1.25), (cx + sgn * 1.602, wy1 - 0.4 if sgn > 0 else wy0 + 0.4, deck + 1.25),
               (cx + sgn * 1.602, wy1 - 0.4 if sgn > 0 else wy0 + 0.4, deck + 2.0), (cx + sgn * 1.602, wy0 + 0.4 if sgn > 0 else wy1 - 0.4, deck + 2.0), "windows", rect="win_tv", emit=0.9)
    k.quad((cx + 1.4, wy1 + 0.002, deck + 1.3), (cx - 1.4, wy1 + 0.002, deck + 1.3), (cx - 1.4, wy1 + 0.002, deck + 2.05), (cx + 1.4, wy1 + 0.002, deck + 2.05), "windows",
           rect="win_kitchen", emit=0.9)
    k.quad((cx - 0.5, wy0 - 0.002, deck), (cx + 0.5, wy0 - 0.002, deck), (cx + 0.5, wy0 - 0.002, deck + 1.9), (cx - 0.5, wy0 - 0.002, deck + 1.9), "paint_metal", (0.2, 0.2, 0.2))
    P.light(k, (cx, wy1 + 0.6, deck + 1.6), (0.75, 0.85, 1.0), 20.0, radius=0.5)
    # mast, lights, radar, outriggers
    k.cyl((cx, wy0 + 1.5, deck + 2.4), (cx, wy0 + 1.5, deck + 8.0), 0.09, "paint_metal", (0.6, 0.6, 0.58), sides=8)
    k.cyl((cx - 1.6, wy0 + 1.5, deck + 6.0), (cx + 1.6, wy0 + 1.5, deck + 6.0), 0.05, "paint_metal", (0.6, 0.6, 0.58), sides=6)
    k.box((cx, wy0 + 1.5, deck + 2.7), (1.2, 0.25, 0.12), "plastic", (0.6, 0.6, 0.6))
    for (x, col) in ((cx, (1.0, 1.0, 0.9)), (cx - 1.6, (1.0, 0.1, 0.05)), (cx + 1.6, (0.1, 1.0, 0.3))):
        z = deck + 8.05 if x == cx else deck + 6.1
        k.lathe(np.array((x, wy0 + 1.5, z)), [(0.0, 0), (0.07, 0.02), (0.07, 0.14), (0.0, 0.16)], "emissive", tuple(c * 0.5 for c in col), sides=8, emit=10.0)
        P.light(k, (x, wy0 + 1.5, z + 0.08), col, 6.0, radius=0.05)
    for sgn in (-1, 1):
        k.tube([(cx + sgn * 0.3, wy0 + 1.5, deck + 7.0), (cx + sgn * 5.0, wy0 + 6.0, deck + 3.0)], 0.06, "paint_metal", (0.6, 0.6, 0.58), sides=6)
        k.tube([(cx + sgn * 0.1, wy0 + 1.5, deck + 8.0), (cx + sgn * 5.0, wy0 + 6.0, deck + 3.0)], 0.01, "galv", sides=3)
        k.tube([(cx, yb - 0.5, top + 0.5), (cx + sgn * 0.2, wy0 + 1.5, deck + 7.8)], 0.008, "galv", sides=3)
    # string of work lights along the mast stay
    for t in np.linspace(0.15, 0.85, 5):
        p = np.array((cx, yb - 0.5, top + 0.5)) * (1 - t) + np.array((cx, wy0 + 1.5, deck + 7.8)) * t
        P.bulb(k, tuple(p), (1.0, 0.85, 0.6), 4.0, cord=0.1)
    # deck clutter: net drum, crates, buoys, ropes, tyres over the side
    with k.atlas("props", "net"):
        k.cyl((cx - 1.2, wy1 + 1.6, deck + 0.75), (cx + 1.2, wy1 + 1.6, deck + 0.75), 0.6, "props", (0.3, 0.55, 0.45), sides=14)
    for sgn in (-1, 1):
        k.cyl((cx + sgn * 1.25, wy1 + 1.6, deck + 0.75), (cx + sgn * 1.32, wy1 + 1.6, deck + 0.75), 0.75, "rust", sides=14)
        k.box((cx + sgn * 1.3, wy1 + 1.6, deck + 0.35), (0.1, 0.4, 0.7), "rust")
    k.collider((cx, wy1 + 1.6, deck + 0.75), (2.7, 1.5, 1.5), 0, "sheet_metal")
    P.crate_stack(k, (cx - 1.2, wy1 + 4.0, deck), 0, rows=2, cols=1)
    P.crate_stack(k, (cx + 1.0, wy1 + 5.5, deck), 90, rows=3, cols=1)
    P.styro_stack(k, (cx - 0.9, wy1 + 7.0, deck), 15, n=2)
    P.rope_coil(k, (cx + 1.1, wy1 + 8.0, deck), r=0.4)
    for y in (ys + 6, ys + 10, ys + 13):
        for sgn in (-1, 1):
            P.tyre(k, (cx + sgn * 2.5, y, top - 0.6), rot_z(90), r=0.32, tube=0.1)
    # mooring lines to the pier bollards and the quay
    for (by, ay) in ((-27.0, yb - 1.5), (-39.0, ys + 2.0)):
        P.rope(k, P.catenary((-25.5, by, 0.55), (cx - 2.3, ay, top), 0.5, 8), 0.025)
    # gangplank from the pier to the deck
    k.box((-23.6, -34.0, -0.2), (2.6, 0.8, 0.06), "planks", (0.55, 0.5, 0.45), R=rot_z(0) @ np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1.0]]) @ _pitch_y(math.degrees(math.atan2(0.4, 2.6))))
    k.colliders.append({"c": [-23.6, -34.0, -0.26], "s": [2.8, 0.9, 0.08], "yaw": 0.0, "ry": round(math.degrees(math.atan2(0.4, 2.6)), 2), "surface": "wood"})
    for sgn in (-1, 1):
        k.tube([(-24.9, -34.0 + sgn * 0.42, 0.9), (-22.3, -34.0 + sgn * 0.42, 0.5)], 0.02, "rope" if False else "galv", sides=4)
    k.marker("spawn", (cx, wy0 - 0.8, deck), name="boat_stern")
    k.marker("spawn", (cx + 0.8, yb - 3.0, deck), name="boat_bow")


def _pitch_y(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


# ====================================================================== quay

def quay():
    for x in np.arange(XMIN + 3.0, XMAX, 7.5):
        if -32 < x < -24:
            continue
        P.bollard(k, (x, QUAY_EDGE + 0.6, 0.0))
    for x in (-38.0, -12.0, 6.0, 24.0):
        P.street_lamp(k, (x, QUAY_EDGE + 1.2, 0.0), yaw=0, height=6.0, reach=1.2)
    # crates, styro stacks, pallets, drums: cover in the open
    P.crate_stack(k, (-36.0, -19.0, 0.0), 10, rows=3, cols=2)
    P.crate_stack(k, (-34.6, -19.4, 0.0), 75, rows=2, cols=1)
    P.styro_stack(k, (-33.0, -21.0, 0.0), -8, n=3)
    P.styro_stack(k, (-32.3, -21.2, 0.0), 12, n=2)
    P.pallet(k, (-19.0, -18.5, 0.0), 5)
    P.crate(k, (-19.0, -18.5, 0.15), 5, size=(1.1, 1.1, 0.9))
    P.crate(k, (-17.6, -18.2, 0.0), -10, size=(1.0, 0.8, 0.7))
    P.crate(k, (-17.6, -18.3, 0.7), 4, size=(0.8, 0.6, 0.5))
    for i, (x, y) in enumerate(((-8.0, -20.5), (-7.3, -20.9), (-7.8, -21.6))):
        P.barrel(k, (x, y, 0.0), rust=(i == 2))
    P.hand_trolley(k, (-4.0, -17.0, 0.0), 40)
    P.crate_stack(k, (2.0, -19.5, 0.0), -5, rows=4, cols=2)
    P.crate_stack(k, (3.4, -18.6, 0.0), 80, rows=2, cols=1)
    P.net_pile(k, (10.5, -21.0, 0.0), 1.8)
    P.rope_coil(k, (12.5, -22.0, 0.0), r=0.45)
    P.styro_stack(k, (14.0, -18.0, 0.0), 20, n=3)
    P.pallet(k, (15.5, -19.5, 0.0), -12)
    P.styro_stack(k, (15.3, -19.4, 0.15), -12, n=2)
    P.styro_stack(k, (16.0, -19.9, 0.15), -8, n=2)
    # forklift parked by the cold store
    forklift((-27.0, -17.0, 0.0), 70)
    # east quay: containers and the crane
    P.container(k, (30.0, -19.0, 0.0), 90, (0.45, 0.12, 0.08))
    P.container(k, (33.2, -19.5, 0.0), 92, (0.12, 0.25, 0.45))
    P.container(k, (31.6, -19.2, 2.6), 88, (0.2, 0.4, 0.25))
    P.container(k, (40.0, -17.0, 0.0), 0, (0.55, 0.42, 0.12))
    P.container(k, (40.5, -21.0, 0.0), 3, (0.45, 0.45, 0.45))
    P.crate_stack(k, (36.0, -15.5, 0.0), 0, rows=3, cols=2)
    P.barrel(k, (27.0, -16.2, 0.0))
    P.barrel(k, (27.6, -15.6, 0.0))
    crane((37.0, -22.0))
    k.marker("spawn", (43.5, -19.0, 0.0), name="containers_east")
    k.marker("spawn", (36.5, -21.8, 0.0), name="crane_foot")


def forklift(pos, yaw):
    R, w = P.frame(pos, yaw)
    y = (0.6, 0.45, 0.06)
    k.box(w((0, 0, 0.75)), (1.1, 2.0, 0.8), "paint_metal", y, yaw=yaw, chamfer=0.05)
    k.box(w((0, 0.75, 0.75)), (1.1, 0.5, 0.9), "paint_metal", (0.25, 0.25, 0.25), yaw=yaw, chamfer=0.05)
    k.box(w((0, -0.1, 1.2)), (0.6, 0.5, 0.15), "plastic", (0.08, 0.08, 0.08), yaw=yaw)
    for s in (-1, 1):
        k.box(w((s * 0.45, -0.35, 1.6)), (0.06, 0.06, 1.4), "paint_metal", (0.1, 0.1, 0.1), yaw=yaw)
        k.box(w((s * 0.45, 0.55, 1.6)), (0.06, 0.06, 1.4), "paint_metal", (0.1, 0.1, 0.1), yaw=yaw)
        k.box(w((s * 0.3, -1.1, 0.95)), (0.08, 0.06, 1.9), "paint_metal", (0.15, 0.15, 0.15), yaw=yaw)
        k.box(w((s * 0.25, -1.65, 0.12)), (0.1, 1.1, 0.04), "galv", yaw=yaw)
        for yy in (-0.6, 0.55):
            c = w((s * 0.55, yy, 0.3))
            k.cyl(c - R @ np.array([0.1, 0, 0]), c + R @ np.array([0.1, 0, 0]), 0.3, "plastic", (0.04, 0.04, 0.04), sides=12)
    k.box(w((0, -0.1, 2.3)), (1.0, 1.0, 0.05), "paint_metal", (0.1, 0.1, 0.1), yaw=yaw)
    k.collider(w((0, 0, 0.8)), (1.2, 2.2, 1.6), yaw, "sheet_metal")
    P.pallet(k, w((0, -1.65, 0.15)), yaw)
    P.styro_stack(k, w((0, -1.65, 0.3)), yaw, n=2)


def crane(base):
    x, y = base
    t = (0.55, 0.42, 0.1)
    legs = [(x - 3, y - 0.5), (x + 3, y - 0.5), (x - 3, y + 5.5), (x + 3, y + 5.5)]
    for lx, ly in legs:
        k.box((lx, ly, 0.4), (0.9, 0.9, 0.8), "concrete", (0.45, 0.45, 0.45))
        k.box((lx, ly, 6.5), (0.5, 0.5, 12.0), "paint_metal", t, col="sheet_metal")
    for z in (4.0, 9.0, 12.5):
        k.box((x, y - 0.5, z), (6.5, 0.4, 0.5), "paint_metal", t)
        k.box((x, y + 5.5, z), (6.5, 0.4, 0.5), "paint_metal", t)
        k.box((x - 3, y + 2.5, z), (0.4, 6.4, 0.5), "paint_metal", t)
        k.box((x + 3, y + 2.5, z), (0.4, 6.4, 0.5), "paint_metal", t)
    for lx in (x - 3, x + 3):
        k.tube([(lx, y - 0.5, 4.0), (lx, y + 5.5, 9.0)], 0.12, "paint_metal", t, sides=6)
        k.tube([(lx, y + 5.5, 4.0), (lx, y - 0.5, 9.0)], 0.12, "paint_metal", t, sides=6)
    # cab and boom out over the water
    k.box((x, y + 2.5, 14.0), (4.0, 5.0, 2.5), "corrugated", (0.55, 0.45, 0.15), chamfer=0.05)
    k.quad((x - 1.5, y + 0.0 - 0.002, 13.6), (x + 1.5, y - 0.002, 13.6), (x + 1.5, y - 0.002, 14.8), (x - 1.5, y - 0.002, 14.8), "windows", rect="win_fluoro", emit=1.2)
    boom = [(x, y + 2.5, 15.2), (x - 2.0, y - 20.0, 23.0)]
    k.tube(boom, 0.45, "paint_metal", t, sides=4, smooth=False)
    k.tube([(x, y + 2.5, 17.5), (x - 2.0, y - 20.0, 23.0)], 0.04, "galv", sides=3)
    k.tube([(x, y + 6.5, 15.2), (x, y + 2.5, 19.0), (x - 2.0, y - 20.0, 23.0)], 0.03, "galv", sides=3)
    k.box((x, y + 7.0, 15.0), (2.5, 2.0, 2.0), "concrete", (0.4, 0.4, 0.4))
    hook = np.array((x - 1.7, y - 16.0, 8.0))
    k.cyl(hook, (x - 1.7, y - 16.0, 21.5), 0.02, "galv", sides=3)
    k.box(hook, (0.6, 0.4, 0.6), "paint_metal", (0.6, 0.5, 0.1))
    for p in ((x - 2.0, y - 20.0, 23.2), (x, y + 2.5, 19.2)):
        k.lathe(np.array(p), [(0.0, 0), (0.12, 0.05), (0.12, 0.2), (0.0, 0.25)], "emissive", (0.6, 0.04, 0.02), sides=8, emit=12.0)
        P.light(k, np.array(p) + (0, 0, 0.12), (1.0, 0.1, 0.05), 15.0, radius=0.1)
    P.light(k, (x, y + 2.5, 12.6), (1.0, 0.7, 0.4), 120.0, radius=0.3, kind="SPOT", spot=110, direction=(0, 0, -1))


# ====================================================================== fish market hall

MK_X0, MK_X1, MK_Y0, MK_Y1 = -14.0, 16.0, -13.0, 1.0


def market():
    eave, ridge = 5.0, 7.2
    yr = (MK_Y0 + MK_Y1) / 2
    k.wet = 0.0
    k.box(((MK_X0 + MK_X1) / 2, yr, 0.005), (MK_X1 - MK_X0 - 0.2, MK_Y1 - MK_Y0, 0.01), "epoxy", faces=["+z"])
    # drainage channel down the middle with a grate
    k.box(((MK_X0 + MK_X1) / 2, yr, 0.011), (MK_X1 - MK_X0 - 1.0, 0.3, 0.002), "grate", faces=["+z"])
    cols = np.arange(MK_X0, MK_X1 + 0.1, 6.0)
    steel = (0.2, 0.32, 0.3)
    ibeam = [(-0.1, -0.1), (0.1, -0.1), (0.1, -0.08), (0.02, -0.08), (0.02, 0.08), (0.1, 0.08), (0.1, 0.1), (-0.1, 0.1), (-0.1, 0.08), (-0.02, 0.08), (-0.02, -0.08), (-0.1, -0.08)]
    for x in cols:
        for y in (MK_Y0, MK_Y1):
            k.extrude(ibeam, (x, y, 0.0), (x, y, eave), "paint_metal", steel, up=(1, 0, 0))
            k.box((x, y, 0.1), (0.4, 0.4, 0.2), "concrete", (0.4, 0.4, 0.4))
            k.collider((x, y, eave / 2), (0.22, 0.22, eave), 0, "steel_post")
        # rafters to the ridge and a tie
        for (y0, y1) in ((MK_Y0 - 0.6, yr), (MK_Y1 + 0.6, yr)):
            z0 = eave - 0.25 * 0.6 / 1.0
            k.extrude(ibeam, (x, y0, eave - 0.1), (x, y1, ridge - 0.15), "paint_metal", steel, up=(0, 0, 1))
        k.tube([(x, MK_Y0, eave - 0.1), (x, MK_Y1, eave - 0.1)], 0.03, "paint_metal", steel, sides=5)
        k.tube([(x, MK_Y0 + 2.0, eave - 0.1 + 0.25), (x, yr, ridge - 0.25)], 0.025, "paint_metal", steel, sides=4)
        k.tube([(x, MK_Y1 - 2.0, eave - 0.1 + 0.25), (x, yr, ridge - 0.25)], 0.025, "paint_metal", steel, sides=4)
    # purlins and the corrugated roof (visible from below too), skylight strips
    k.detail = False
    for side in (-1, 1):
        ye = MK_Y0 - 0.8 if side < 0 else MK_Y1 + 0.8
        for t in np.linspace(0.0, 1.0, 7):
            y = ye + (yr - ye) * t
            z = eave + (ridge - eave) * t * ((yr - ye) / (yr - (MK_Y0 if side < 0 else MK_Y1))) - 0.05
            z = eave - 0.05 + (ridge - eave) * (y - ye) / (yr - ye) + 0.02 * 0
            k.box(((MK_X0 + MK_X1) / 2, y, z), (MK_X1 - MK_X0 + 1.6, 0.08, 0.15), "paint_metal", steel)
        pa = [(MK_X0 - 0.8, ye, eave), (MK_X1 + 0.8, ye, eave), (MK_X1 + 0.8, yr, ridge + 0.1), (MK_X0 - 0.8, yr, ridge + 0.1)]
        pa = [np.array(p) + (0, 0, 0.1) for p in pa]
        if side < 0:
            k.quad(pa[0], pa[1], pa[2], pa[3], "corrugated", (0.4, 0.42, 0.4))
            k.quad(pa[1], pa[0], pa[3], pa[2], "corrugated", (0.45, 0.45, 0.43))
        else:
            k.quad(pa[1], pa[0], pa[3], pa[2], "corrugated", (0.4, 0.42, 0.4))
            k.quad(pa[0], pa[1], pa[2], pa[3], "corrugated", (0.45, 0.45, 0.43))
        # gutters
        k.extrude([(-0.12, -0.12), (0.12, -0.12), (0.12, 0.05), (0.08, 0.05), (0.08, -0.08), (-0.08, -0.08), (-0.08, 0.05), (-0.12, 0.05)],
                  (MK_X0 - 0.8, ye, eave + 0.05), (MK_X1 + 0.8, ye, eave + 0.05), "galv")
        for x in (MK_X0 - 0.6, MK_X1 + 0.6):
            P.drainpipe(k, x, ye, 0.1, eave)
    # ridge cap and gable boards with the market sign
    k.box(((MK_X0 + MK_X1) / 2, yr, ridge + 0.18), (MK_X1 - MK_X0 + 1.6, 0.5, 0.1), "galv")
    for x, yaw in ((MK_X0 - 0.8, 0), (MK_X1 + 0.8, 0)):
        tri = [(x, MK_Y0 - 0.8, eave + 0.1), (x, MK_Y1 + 0.8, eave + 0.1), (x, yr, ridge + 0.2)]
        k.quad(tri[0], tri[1], tri[2], tri[2], "corrugated", (0.4, 0.42, 0.4), double=True)
    # big signs over both ends (street side and quay side)
    for y, yaw in ((MK_Y1 + 0.9, 180), (MK_Y0 - 0.9, 0)):
        k.sign((0.0, y, eave + 1.05), 8.0, 1.3, yaw, "signs_a", "fishmarket", depth=0.2, back_tint=(0.2, 0.2, 0.2))
        for xx in (-3.0, 3.0):
            k.cyl((xx, y, eave), (xx, y, eave + 0.4), 0.05, "galv", sides=5)
            n = -1 if yaw == 0 else 1
            P.light(k, (xx, y + n * 0.9, eave + 1.9), (1.0, 0.9, 0.75), 40.0, radius=0.1, kind="SPOT", spot=90, direction=(0, -n * 0.6, -1))
            k.tube([(xx, y + n * 0.1, eave + 1.8), (xx, y + n * 0.8, eave + 1.95)], 0.015, "paint_metal", (0.1, 0.1, 0.1), sides=4)
            k.lathe(np.array((xx, y + n * 0.85, eave + 1.88)), [(0.09, 0.0), (0.05, 0.08), (0.0, 0.1)], "paint_metal", (0.1, 0.1, 0.1), sides=8, cap_bottom=False)
    # low brick walls along parts of the long sides (cover), pillars stay open
    for (xa, xb) in ((MK_X0 + 0.3, MK_X0 + 5.7), (MK_X1 - 5.7, MK_X1 - 0.3)):
        for y in (MK_Y0, MK_Y1):
            k.box(((xa + xb) / 2, y, 0.55), (xb - xa, 0.3, 1.1), "brick", col="concrete")
            k.box(((xa + xb) / 2, y, 1.12), (xb - xa + 0.04, 0.36, 0.06), "concrete", (0.5, 0.5, 0.5))
    # stalls in three rows, aisles between
    for yrow in (-10.2, -6.0, -1.8):
        for x in np.arange(MK_X0 + 3.0, MK_X1 - 2.0, 5.0):
            if yrow == -10.2 and x > 9:
                continue  # the cold room is here
            sp = [pick(["fish_mackerel", "fish_snapper", "fish_grouper", "fish_pomfret"]) for _ in range(3)]
            P.stall(k, (x + 0.0, yrow, 0.0), 0 if yrow != -6.0 else 180, length=3.2, depth=1.25, species=sp)
            # red-shaded lamps over each stall: the market's signature light
            for dx in (-0.9, 0.9):
                P.bulb(k, (x + dx, yrow, eave - 0.1), (1.0, 0.25, 0.18), 20.0, cord=2.1, shade=(0.6, 0.06, 0.04))
            P.scale_hanging(k, (x + 1.6, yrow - 0.4, eave - 0.1))
    # live seafood tanks along the quay-side wall, hoses on the floor
    for x in (-11.0, -8.6, 5.0):
        P.seafood_tank(k, (x, MK_Y1 - 1.0, 0.0), 180, length=1.8)
    P.hose(k, [(-10.0, -4.0, 0.03), (-8.0, -4.5, 0.03), (-6.5, -3.6, 0.03), (-4.0, -4.2, 0.03), (-3.0, -5.6, 0.03)])
    P.hose(k, [(6.0, -8.3, 0.03), (7.5, -7.6, 0.03), (8.4, -8.4, 0.03), (9.5, -7.8, 0.03)])
    P.hand_trolley(k, (-4.5, -12.0, 0.0), 160)
    P.crate_stack(k, (-12.6, -4.0, 0.0), 90, rows=3, cols=1)
    P.crate_stack(k, (14.5, -3.0, 0.0), 90, rows=4, cols=1)
    P.styro_stack(k, (-12.5, -8.0, 0.0), 80, n=3)
    P.styro_stack(k, (-12.4, -8.7, 0.0), 95, n=2)
    for x in (-5.0, 7.0):
        k.box((x, -6.0, 0.4), (0.5, 0.5, 0.8), "plastic", (0.15, 0.3, 0.5), col="crate")  # bins
    # rows of fluorescent tubes hanging over the aisles
    for y in (-8.1, -3.9):
        for x in np.arange(MK_X0 + 2.0, MK_X1 - 1.0, 4.0):
            P.fluoro(k, (x, y, eave + 0.6), 0, length=1.5, energy=11.0, hang=1.4)
    # cold room (insulated box with strip curtain) in the south-east corner
    cx0, cx1, cy0, cy1 = 10.0, 15.7, -12.7, -8.0
    k.box(((cx0 + cx1) / 2, (cy0 + cy1) / 2, 1.5), (cx1 - cx0, cy1 - cy0, 3.0), "paint_metal", (0.62, 0.62, 0.6), col="thin_metal", faces=["+z", "-x", "+x", "-y"])
    for xx in (cx0 + 0.5, cx0 + 2.5):
        k.box((xx, cy1, 1.5), (1.0, 0.1, 3.0), "paint_metal", (0.62, 0.62, 0.6))
    k.box((cx0 + 4.4, cy1, 1.5), (2.6, 0.1, 3.0), "paint_metal", (0.62, 0.62, 0.6))
    k.collider((cx0 + 1.5, cy1, 1.5), (3.0, 0.15, 3.0), 0, "thin_metal")
    k.collider((cx0 + 4.4, cy1, 1.5), (2.6, 0.15, 3.0), 0, "thin_metal")
    for i in range(8):
        xx = cx0 + 1.05 + i * 0.13
        k.quad((xx, cy1 + 0.02, 0.05), (xx + 0.12, cy1 + 0.02, 0.05), (xx + 0.12, cy1 + 0.02, 2.4), (xx, cy1 + 0.02, 2.4), "glass", (0.6, 0.65, 0.65), double=True)
    k.box((cx0 + 1.5, cy1 + 0.05, 2.5), (1.2, 0.1, 0.15), "galv")
    k.quad((cx0 + 2.1, cy1 - 0.2, 0.0), (cx0 + 1.0, cy1 - 0.2, 0.0), (cx0 + 1.0, cy1 - 0.2, 2.4), (cx0 + 2.1, cy1 - 0.2, 2.4), "emissive", (0.12, 0.18, 0.22), emit=0.8)
    P.fluoro(k, (cx0 + 3.0, cy0 + 2.0, 2.95), 90, length=1.2, energy=20.0, color=(0.8, 0.9, 1.0))
    k.marker("spawn", (cx0 + 3.0, cy0 + 2.0, 0.0), name="cold_room")
    k.sign((cx0 + 4.4, cy1 + 0.07, 2.2), 1.2, 0.3, 180, "signs_b", "danger")
    k.sign((cx0 + 0.3, MK_Y1 - 0.25, 2.4), 1.0, 0.25, 180, "signs_b", "slippery")
    k.wet = 1.0


# ====================================================================== cold storage warehouse

WH_X0, WH_X1, WH_Y0, WH_Y1 = -46.0, -20.0, -14.0, 2.0


def warehouse():
    H = 8.0
    t = 0.35
    doors_s = [(-41.0, -37.0), (-29.0, -25.0)]
    doors_n = [(-36.0, -32.0)]
    door_e = (-7.6, -4.4)  # y range on the east wall
    dh = 4.2

    def wall_x(y, outward, doors, mat_lo="brick", mat_hi="corrugated"):
        """South or north wall along x with door openings."""
        xs = [WH_X0] + [v for d in doors for v in d] + [WH_X1]
        for i in range(0, len(xs), 2):
            a, b = xs[i], xs[i + 1]
            if b - a > 0.01:
                k.box(((a + b) / 2, y, 1.6), (b - a, t, 3.2), mat_lo, col="concrete")
        for (a, b) in doors:
            k.box(((a + b) / 2, y, (dh + 3.2) / 2 + 0.0), (b - a, t, 3.2 - dh) if dh < 3.2 else (0.01, 0.01, 0.01), mat_lo)
        k.box(((WH_X0 + WH_X1) / 2, y, (3.2 + H) / 2), (WH_X1 - WH_X0, t, H - 3.2), mat_hi, (0.38, 0.4, 0.42), col="sheet_metal")
        k.box(((WH_X0 + WH_X1) / 2, y + outward * 0.2, 3.25), (WH_X1 - WH_X0, 0.12, 0.12), "concrete", (0.45, 0.45, 0.45))
        for (a, b) in doors:
            # lintel, roller box and half-raised shutters
            k.box(((a + b) / 2, y, dh + 0.15), (b - a + 0.4, t + 0.1, 0.3), "concrete", (0.5, 0.5, 0.5))
            k.box(((a + b) / 2, y - outward * 0.3, dh + 0.35), (b - a + 0.2, 0.5, 0.5), "paint_metal", (0.3, 0.32, 0.3))
            for xx in (a + 0.05, b - 0.05):
                k.box((xx, y - outward * 0.1, dh / 2), (0.1, 0.14, dh), "paint_metal", (0.55, 0.45, 0.08))
                k.box((xx, y + outward * 0.15, 0.5), (0.12, 0.12, 1.0), "paint_metal", (0.6, 0.5, 0.05))  # bump post
            k.box(((a + b) / 2, y - outward * 0.1, dh - 0.35), (b - a, 0.06, 0.6), "shutter", (0.45, 0.47, 0.45))
            P.light(k, ((a + b) / 2, y + outward * 1.0, dh + 0.8), (1.0, 0.75, 0.45), 60.0, radius=0.1, kind="SPOT", spot=120, direction=(0, outward * 0.3, -1), dyn=False)
            k.lathe(np.array(((a + b) / 2, y + outward * 0.35, dh + 0.7)), [(0.0, 0.0), (0.18, 0.02), (0.14, 0.18), (0.05, 0.2)], "paint_metal", (0.15, 0.2, 0.15), sides=10)
            k.lathe(np.array(((a + b) / 2, y + outward * 0.35, dh + 0.68)), [(0.0, 0.0), (0.12, 0.02)], "emissive", (0.6, 0.4, 0.2), sides=10, emit=6.0)
    k.wet = 1.0
    wall_x(WH_Y0, -1, doors_s)
    wall_x(WH_Y1, 1, doors_n)
    # end walls
    for x, doors in ((WH_X0, []), (WH_X1, [door_e])):
        ys = [WH_Y0] + [v for d in doors for v in d] + [WH_Y1]
        for i in range(0, len(ys), 2):
            a, b = ys[i], ys[i + 1]
            k.box((x, (a + b) / 2, H / 2), (t, b - a, H), "brick" if x == WH_X1 else "corrugated", (0.38, 0.4, 0.42) if x == WH_X0 else None, col="concrete")
        for (a, b) in doors:
            k.box((x, (a + b) / 2, (2.6 + H) / 2), (t, b - a, H - 2.6), "brick")
            k.box((x + 0.1, (a + b) / 2, 1.3), (0.06, b - a - 0.2, 2.6), "paint_metal", (0.3, 0.35, 0.3)) if False else None
            P.bulb(k, (x + 0.5, (a + b) / 2, 3.2), (1.0, 0.75, 0.45), 30.0, cord=0.05, shade=(0.2, 0.22, 0.2))
    # roof (low pitch), parapet trim
    k.box(((WH_X0 + WH_X1) / 2, (WH_Y0 + WH_Y1) / 2, H + 0.1), (WH_X1 - WH_X0 + 0.6, WH_Y1 - WH_Y0 + 0.6, 0.2), "corrugated", (0.35, 0.37, 0.38))
    k.box(((WH_X0 + WH_X1) / 2, (WH_Y0 + WH_Y1) / 2, H - 0.01), (WH_X1 - WH_X0, WH_Y1 - WH_Y0, 0.02), "corrugated", (0.5, 0.5, 0.48), faces=["-z"])
    # signs: big board over the quay doors, painted letters
    k.sign((-33.0, WH_Y0 - 0.25, 5.4), 11.0, 1.4, 0, "signs_a", "warehouse", depth=0.15, back_tint=(0.2, 0.2, 0.2))
    k.sign((-33.0, WH_Y1 + 0.25, 5.4), 11.0, 1.4, 180, "signs_a", "warehouse", depth=0.15, back_tint=(0.2, 0.2, 0.2))
    k.sign((-23.0, WH_Y0 - 0.19, 2.2), 1.2, 0.3, 0, "signs_b", "pier3")
    k.sign((-34.0, WH_Y1 + 0.19, 2.6), 1.0, 0.25, 180, "signs_b", "nosmoke")
    k.sign((-27.0, WH_Y0 - 0.19, 4.9), 0.5, 0.25, 0, "signs_b", "exit", emit=3.0)
    k.sign((-30.0, WH_Y1 + 0.19, 1.8), 1.0, 1.0, 180, "signs_b", "notice")
    # interior
    k.wet = 0.0
    k.box(((WH_X0 + WH_X1) / 2, (WH_Y0 + WH_Y1) / 2, 0.006), (WH_X1 - WH_X0 - 0.4, WH_Y1 - WH_Y0 - 0.4, 0.01), "concrete", (0.5, 0.5, 0.52), faces=["+z"])
    for x in (-39.5, -33.0, -26.5):
        for y in (-8.7, -3.3):
            k.box((x, y, H / 2), (0.3, 0.3, H), "paint_metal", (0.5, 0.42, 0.1), col="steel_post")
            k.box((x, y, 0.6), (0.36, 0.36, 1.2), "paint_metal", (0.55, 0.5, 0.1))
        k.box((x, -6.0, H - 0.4), (0.25, WH_Y1 - WH_Y0, 0.5), "paint_metal", (0.3, 0.3, 0.3))
    for x in np.arange(-43.0, -21.0, 4.0):
        for y in (-10.0, -2.0):
            P.fluoro(k, (x, y, H - 0.2), 0, length=1.5, energy=9.0, hang=1.2)
    # pallet stacks: cover in aisles
    stacks = [(-43.0, -11.5, 0), (-43.2, -4.0, 90), (-37.5, -6.0, 10), (-35.5, -11.0, -5), (-31.0, -2.0, 85), (-29.5, -8.0, 0), (-24.0, -11.0, 30), (-23.5, -1.5, 0), (-40.0, -0.5, 0)]
    for (x, y, yaw) in stacks:
        P.pallet(k, (x, y, 0.0), yaw)
        if RNG.random() < 0.5:
            P.crate(k, (x, y, 0.15), yaw, size=(1.15, 1.15, rnd(0.9, 1.6)))
        else:
            for dx, dy in ((-0.32, -0.25), (0.32, 0.25), (-0.32, 0.25), (0.32, -0.25)):
                R = rot_z(yaw)
                o = R @ np.array((dx, dy, 0))
                P.styro_stack(k, (x + o[0], y + o[1], 0.15), yaw + 90, n=int(RNG.integers(2, 5)))
    forklift((-37.0, -1.8, 0.0), -100)
    # freezer room: west end
    k.box((-44.0, -6.0, 1.75), (3.6, 8.0, 3.5), "paint_metal", (0.65, 0.65, 0.63), col="thin_metal", faces=["+z", "+x", "-y", "+y"])
    k.sign((-42.18, -6.0, 2.4), 1.0, 0.3, 270, "signs_b", "danger")
    k.marker("spawn", (-43.5, -12.5, 0.0), name="warehouse_west")
    k.marker("spawn", (-34.0, 0.5, 0.0), name="warehouse_north_door")
    k.marker("spawn", (-22.0, -12.5, 0.0), name="warehouse_east")
    k.collider(((WH_X0 + WH_X1) / 2, (WH_Y0 + WH_Y1) / 2, H + 0.1), (WH_X1 - WH_X0, WH_Y1 - WH_Y0, 0.2), 0, "sheet_metal")
    k.wet = 1.0


# ====================================================================== the south row, east: tenement with a gallery

def east_tenement():
    b = B.Building(k, 22.0, 46.0, 2.0, 15.0, 4, facing=1, wall="mosaic", tint=(0.42, 0.48, 0.5), bay=3.0)
    # street front (north): laundry + travel agency + shutter
    b.shopfront("glass", sign="laundry", x_lo=-12.0, x_hi=-4.0, awning=(0.2, 0.35, 0.6), vsign="hotel_lb" if False else None)
    b.shopfront("shutter", sign="travel", x_lo=-4.0, x_hi=4.0)
    b.shopfront("open", sign="grocery", x_lo=4.0, x_hi=12.0, awning=(0.55, 0.45, 0.1), open_depth=2.4)
    P.produce_stand(k, b.w((8.0, -0.9, 0.0)), 180)
    b.upper_front(lit_chance=0.6)
    b.sides(left=True, right=False)
    # back: faces the quay (south). Ground floor: a chandlery with its shutters down.
    yb = b.depth
    hw = b.w_ / 2
    k.wet = 1.0
    b.lbox(-hw, hw, yb - B.WALL_T, yb, 0, b.gh)
    for f in range(1, b.floors):
        z0 = b.gh + (f - 1) * b.fh
        b.window_wall(z0, z0 + b.fh, yb, +1, lit_chance=0.45, extras=(f > 1))
    # gallery walkway on the first floor along the quay side, with stairs at the west end
    gz = b.gh - 0.25
    gy0, gy1 = -13.0 - 2.2, -13.0  # world y (back face is at y = 2 - 15 = -13)
    k.box((35.0, (gy0 + gy1) / 2, gz - 0.1), (20.0, gy1 - gy0, 0.2), "concrete", (0.45, 0.45, 0.45), col="concrete")
    for x in np.arange(25.5, 45.1, 3.0):
        k.box((x, gy0 + 0.15, gz / 2), (0.25, 0.25, gz), "concrete", (0.45, 0.45, 0.45), col="concrete")
    for x in np.arange(25.0, 45.01, 0.15):
        k.cyl((x, gy0 + 0.05, gz), (x, gy0 + 0.05, gz + 1.0), 0.01, "paint_metal", (0.2, 0.25, 0.22), sides=4, caps=False)
    k.box((35.0, gy0 + 0.05, gz + 1.0), (20.0, 0.08, 0.06), "paint_metal", (0.2, 0.25, 0.22))
    k.collider((35.0, gy0 + 0.05, gz + 0.55), (20.0, 0.1, 1.1), 0, "thin_metal")
    k.collider((45.0, (gy0 + gy1) / 2, gz + 0.55), (0.1, gy1 - gy0, 1.1), 0, "thin_metal")
    # stairs from the quay up to the gallery (west end)
    sx0, sx1 = 22.6, 25.0
    steps = 16
    for i in range(steps):
        z = (i + 1) * gz / steps
        y = gy0 + 2.2 - 0.0
        x = sx0 + 0.0
        k.box((24.0 - 0.0, gy0 - 0.0 - 0.0 + 1.1, 0.0), (0.01, 0.01, 0.01), "galv") if False else None
    run = 5.6
    for i in range(steps):
        z = (i + 1) * gz / steps
        yy = gy0 - 0.2 - run + (i + 0.5) * run / steps
        k.box((24.0, yy, z - 0.04), (1.4, run / steps + 0.02, 0.08), "grate")
    ang = math.degrees(math.atan2(gz, run))
    k.box((24.0, gy0 - 0.2 - run / 2, gz / 2 - 0.1), (1.4, math.hypot(run, gz), 0.1), "paint_metal", (0.2, 0.25, 0.22), R=rot_x(ang))
    k.colliders.append({"c": [24.0, gy0 - 0.2 - run / 2, gz / 2 - 0.12], "s": [1.4, math.hypot(run, gz), 0.12], "yaw": 0.0, "rx": round(ang, 2), "surface": "thin_metal"})
    for sx in (23.3, 24.7):
        k.tube([(sx, gy0 - 0.2 - run, 1.0), (sx, gy0 - 0.2, gz + 1.0)], 0.02, "paint_metal", (0.2, 0.25, 0.22), sides=5)
        k.collider((sx, gy0 - 0.2 - run / 2, gz / 2 + 0.5), (0.08, run, gz + 1.0), 0, "thin_metal")
    k.box((24.0, gy0 - 0.1, gz - 0.1), (1.6, 0.4, 0.2), "concrete", (0.45, 0.45, 0.45), col="concrete")
    # doors along the gallery (dark), lamps, plants, a chair: people live here
    for x in (28.0, 34.0, 40.0):
        k.quad((x - 0.5, gy1 - 0.002, gz), (x + 0.5, gy1 - 0.002, gz), (x + 0.5, gy1 - 0.002, gz + 2.1), (x - 0.5, gy1 - 0.002, gz + 2.1), "darkwood", (0.5, 0.3, 0.25))
        P.bulb(k, (x + 0.8, gy1 - 0.3, gz + 2.6), (1.0, 0.8, 0.5), 18.0, cord=0.05)
        P.potted_plant(k, (x - 1.0, gy1 - 0.4, gz), 0.9)
    P.chair(k, (31.0, gy1 - 0.6, gz), 200)
    P.laundry(k, (26.0, gy0 + 0.1, gz + 2.0), (32.0, gy0 + 0.1, gz + 2.0), sag=0.2)
    k.marker("spawn", (42.0, gy1 - 1.0, gz), name="gallery_east")
    # ground floor (quay side): chandlery shutters and a door
    for (xa, xb) in ((26.0, 31.0), (32.0, 37.0)):
        yb_world = -13.0 - 0.13
        k.quad((xa, yb_world, 0.0), (xb, yb_world, 0.0), (xb, yb_world, 3.0), (xa, yb_world, 3.0), "shutter", (0.35, 0.42, 0.45))
        k.box(((xa + xb) / 2, -13.0 - 0.3, 3.15), (xb - xa + 0.2, 0.4, 0.4), "paint_metal", (0.3, 0.3, 0.3))
    k.collider((34.0, -13.0 + 0.2, 2.0), (24.0, 0.5, 4.0), 0, "concrete")
    b.top()
    k.collider((34.0, -5.5, 7.0), (24.0, 14.0, 14.0), 0, "concrete")


def south_front_west():
    """Warehouse north wall is the street front; add clutter along the alley."""
    # the west alley between warehouse and market
    P.dumpster(k, (-17.5, -2.0, 0.0), 90)
    P.trash_bags(k, (-16.0, -0.5, 0.0), 5)
    P.crate_stack(k, (-18.8, -8.0, 0.0), 90, rows=4, cols=1)
    P.styro_stack(k, (-16.0, -10.5, 0.0), 30, n=4)
    P.bicycle(k, (-15.6, -6.0, 0.0), 95)
    P.gas_cylinder(k, (-19.3, -11.8, 0.0))
    P.gas_cylinder(k, (-19.0, -12.2, 0.0))
    P.lantern_string(k, (-20.0, -4.0, 4.0), (-14.0, -4.0, 4.5), n=3, sag=0.4)
    P.lantern_string(k, (-20.0, -9.5, 4.2), (-14.0, -9.5, 4.0), n=3, sag=0.5)
    # loading road: the box truck and pallets
    P.box_truck(k, (19.0, -5.0, 0.0), 92, tint=(0.62, 0.6, 0.58), box_tint=(0.55, 0.55, 0.52))
    P.pallet(k, (17.2, -11.5, 0.0), 10)
    P.crate(k, (17.2, -11.5, 0.15), 10, size=(1.1, 1.1, 1.0))
    P.barrel(k, (20.8, -11.8, 0.0))
    P.cone(k, (17.0, 0.5, 0.0))
    P.cone(k, (20.8, 1.0, 0.0))
    k.marker("spawn", (19.5, -12.0, 0.0), name="loading_road")


# ====================================================================== north row (the street's north side)

def north_row():
    k.wet = 1.0
    yf = 12.0
    # hotel with pawnshop (x -46..-32)
    b = B.Building(k, -46.0, -32.0, yf, 10.0, 5, wall="brick", bay=2.8)
    b.shopfront("glass", sign=None, x_lo=-7.0, x_hi=-1.5, interior_lit=True)
    k.sign(b.w((-4.25, -0.16, 3.45)), 5.0, 0.8, 0, "signs_b", "hotel_lb", emit=2.0, depth=0.15)
    doorway(b, 0.0, name="hotel_door")
    b.shopfront("shutter", sign=None, x_lo=1.5, x_hi=7.0, vsign="v_pawn")
    pawn_sign(b.w((6.6, -1.2, 4.6)))
    b.upper_front(lit_chance=0.6)
    vneon = b.w((-6.6, -0.8, 6.5))
    k.sign(vneon, 0.6, 3.6, 90, "signs_b", "v_hotel", emit=2.4, depth=0.25, double=True)
    b.sides(left=True, right=False)
    # herbal shop (x -32..-24)
    b = B.Building(k, -32.0, -24.0, yf, 10.0, 4, wall="plaster", tint=(0.5, 0.44, 0.34), bay=2.7)
    b.shopfront("open", sign="herbal", awning=(0.15, 0.3, 0.2), open_depth=2.6)
    b.upper_front()
    b.back(door_x=None, lit_chance=0.4)
    # Sea View restaurant (x -24..-12): handled by restaurant()
    restaurant(-24.0, -12.0, yf, 10.0)
    # bakery (x -12..-6)
    b = B.Building(k, -12.0, -6.0, yf, 10.0, 4, wall="mosaic", tint=(0.55, 0.5, 0.42), bay=3.0)
    b.shopfront("glass", sign="bakery", awning=(0.55, 0.1, 0.08), interior_lit=True)
    b.upper_front()
    b.back(door_x=0.5, fire_escape=True)
    # noodle shop (x -6..3)
    b = B.Building(k, -6.0, 3.0, yf, 10.0, 5, wall="plaster", tint=(0.42, 0.5, 0.45), bay=3.0)
    b.shopfront("open", sign="noodle", awning=(0.15, 0.4, 0.2), open_depth=2.2)
    b.upper_front()
    b.sides(left=False, right=True)
    b.back(door_x=-2.0)
    k.sign(b.w((4.1, -0.8, 6.8)), 0.6, 3.6, 90, "signs_b", "v_restaurant", emit=2.4, depth=0.25, double=True)
    # alley A (x 3..6): see alley_a()
    # grocery + mahjong club (x 6..16)
    b = B.Building(k, 6.0, 16.0, yf, 10.0, 4, wall="brick", bay=3.3)
    b.shopfront("open", sign="grocery", x_lo=-5.0, x_hi=1.5, awning=(0.6, 0.48, 0.1))
    P.produce_stand(k, b.w((-1.8, -0.9, 0.0)), 0)
    doorway(b, 3.2, name="mahjong_stairs")
    b.upper_front()
    b.sides(left=True, right=False)
    b.back(door_x=2.0)
    k.sign(b.w((0.0, -0.17, 5.7)), 4.6, 1.5, 0, "signs_a", "mahjong", emit=2.0, depth=0.2)
    # gold shop + pharmacy (x 16..28)
    b = B.Building(k, 16.0, 28.0, yf, 10.0, 4, wall="plaster", tint=(0.55, 0.52, 0.48), bay=3.0)
    b.shopfront("glass", sign=None, x_lo=-6.0, x_hi=0.0, interior_lit=True, vsign="v_gold")
    k.sign(b.w((-3.0, -0.16, 3.45)), 4.6, 0.75, 0, "signs_b", "welcome", depth=0.12)
    b.shopfront("glass", sign=None, x_lo=0.0, x_hi=6.0, interior_lit=True, vsign="v_pharmacy", awning=(0.15, 0.4, 0.25))
    b.upper_front()
    b.back(door_x=-3.0, fire_escape=True)
    # tea house / barber (x 28..46)
    b = B.Building(k, 28.0, 46.0, yf, 10.0, 5, wall="mosaic", tint=(0.5, 0.45, 0.38), bay=3.0)
    b.shopfront("shutter", x_lo=-9.0, x_hi=-3.0)
    doorway(b, -1.5, name="tenement_east_door")
    b.shopfront("glass", x_lo=0.0, x_hi=9.0, vsign="v_barber", awning=(0.6, 0.6, 0.6), interior_lit=True)
    b.upper_front()
    # colliders for the solid blocks (interiors that aren't open)
    for (x0, x1) in ((-46.0, -32.0), (-32.0, -24.0), (-12.0, -6.0), (-6.0, 3.0), (6.0, 16.0), (16.0, 28.0), (28.0, 46.0)):
        k.collider(((x0 + x1) / 2, yf + 0.55 + 4.725, 8.0), (x1 - x0, 9.45, 16.0), 0, "concrete")
        k.collider(((x0 + x1) / 2, yf + 0.25, 5.0 + 4.2), (x1 - x0, 0.5, 10.0), 0, "concrete")


def doorway(b, x, name):
    """Recessed tenement entrance: a dark stairwell people come out of."""
    w = 1.3
    # step back the wall and show a stair going up into darkness
    b.lbox(x - w / 2 - 0.25, x - w / 2, -0.05, 1.6, 0, 2.7, "mosaic", (0.4, 0.42, 0.38))
    b.lbox(x + w / 2, x + w / 2 + 0.25, -0.05, 1.6, 0, 2.7, "mosaic", (0.4, 0.42, 0.38))
    b.lbox(x - w / 2 - 0.25, x + w / 2 + 0.25, -0.05, 0.4, 2.7, b.gh - 1.15, "plaster", (0.35, 0.35, 0.33))
    for i in range(8):
        b.lbox(x - w / 2, x + w / 2, 1.0 + i * 0.25, 1.6, i * 0.18, (i + 1) * 0.18, "stone", (0.35, 0.35, 0.33))
    b.lbox(x - w / 2, x + w / 2, 1.6, 1.7, 0, 2.7, "plaster", (0.12, 0.12, 0.12))
    b.lquad(x - 0.3, x + 0.3, -0.06, 2.75, 2.95, "signs_b", rect="street")
    P.bulb(k, b.w((x, 0.5, 2.65)), (1.0, 0.85, 0.6), 12.0, cord=0.02)
    k.marker("spawn", b.w((x, 0.7, 0.0)), name=name)
    # couplets beside the door
    for xx, r in ((x - w / 2 - 0.13, "c1"), (x + w / 2 + 0.13, "c2")):
        b.lquad(xx - 0.09, xx + 0.09, -0.06, 0.9, 2.3, "signs_b", rect=r)
    b.lquad(x - 0.25, x + 0.25, -0.051, 2.3, 2.62, "signs_b", rect="poster")


def pawn_sign(pos):
    """The classic pawnshop sign: a bat holding a coin, hung out over the street."""
    x, y, z = pos
    k.cyl((x, y + 1.0, z + 0.9), (x, y - 0.2, z + 0.9), 0.03, "galv", sides=5)
    for s in (-1, 1):
        wing = [(x, y, z + 0.5), (x + s * 0.55, y, z + 0.85), (x + s * 0.7, y, z + 0.55), (x + s * 0.45, y, z + 0.35)]
        k.quad(wing[0], wing[1], wing[2], wing[3], "props", rect="red_pad", double=True)
    with k.atlas("props", "gold_pad"):
        k.cyl((x, y - 0.03, z + 0.2), (x, y + 0.03, z + 0.2), 0.32, "props", (0.5, 0.5, 0.5), sides=20)
    k.quad((x - 0.12, y - 0.035, z + 0.08), (x + 0.12, y - 0.035, z + 0.08), (x + 0.12, y - 0.035, z + 0.32), (x - 0.12, y - 0.035, z + 0.32), "signs_b", rect="v_pawn")
    k.cyl((x, y, z + 0.52), (x, y, z + 0.9), 0.01, "galv", sides=3)


# ====================================================================== the restaurant

def restaurant(x0, x1, yf, depth):
    b = B.Building(k, x0, x1, yf, depth, 4, wall="plaster", tint=(0.55, 0.42, 0.28), bay=3.0)
    hw = b.w_ / 2
    gh = b.gh
    k.wet = 1.0
    # front: pilasters, glass, centre doors open; roast-meat window on the left
    pil = 0.45
    op_top = gh - 1.15
    for xa, xb in ((-hw, -hw + pil), (hw - pil, hw), (-1.3, -0.9), (0.9, 1.3)):
        b.lbox(xa, xb, -0.08, B.WALL_T, 0, gh, "lacquer", (0.5, 0.5, 0.5))
        b.lbox(xa - 0.02, xb + 0.02, -0.1, B.WALL_T, 0, 0.35, "stone", (0.35, 0.34, 0.33))
    b.lbox(-hw + pil, hw - pil, 0.0, B.WALL_T, op_top, gh)
    # big sign with lamps
    b.lbox(-hw + 0.5, hw - 0.5, -0.2, 0.0, op_top + 0.08, gh - 0.02, "paint_metal", (0.1, 0.1, 0.1))
    b.lquad(-hw + 0.52, hw - 0.52, -0.205, op_top + 0.1, gh - 0.04, "signs_a", rect="seaview")
    for xx in np.linspace(-hw + 1.2, hw - 1.2, 4):
        P.light(k, b.w((xx, -0.6, gh + 0.15)), (1.0, 0.85, 0.6), 22.0, radius=0.05, kind="SPOT", spot=100, direction=(0, 0.4, -1))
        k.tube([b.w((xx, -0.2, gh + 0.1)), b.w((xx, -0.6, gh + 0.25))], 0.015, "paint_metal", (0.1, 0.1, 0.1), sides=4)
        k.lathe(b.w((xx, -0.62, gh + 0.18)), [(0.09, 0.0), (0.05, 0.08), (0.0, 0.1)], "paint_metal", (0.1, 0.1, 0.1), sides=8, cap_bottom=False)
    # windows either side of the door
    for (xa, xb) in ((-hw + pil, -1.3), (1.3, hw - pil)):
        b.lbox(xa, xb, 0.1, 0.35, 0, 0.55, "mosaic", (0.55, 0.12, 0.08))
        b.lquad(xa, xb, 0.12, 0.55, op_top, "glass")
        for xx in np.linspace(xa, xb, 3):
            b.lbox(xx - 0.03, xx + 0.03, 0.08, 0.16, 0.55, op_top, "galv", (0.5, 0.5, 0.5))
        k.collider(b.w(((xa + xb) / 2, 0.15, op_top / 2)), (xb - xa, 0.2, op_top), 0, "glass")
    b.lbox(-0.9, 0.9, 0.0, B.WALL_T, op_top, op_top + 0.02, "galv")
    k.sign(b.w((0.0, -0.06, op_top - 0.18)), 1.4, 0.3, 0, "signs_b", "open", emit=3.0)
    # red lanterns at the entrance
    for xx in (-1.6, 1.6):
        P.lantern(k, b.w((xx, -0.6, op_top + 0.05)), 0.26, energy=25.0, dyn=True)
        k.cyl(b.w((xx, 0.0, op_top + 0.05)), b.w((xx, -0.6, op_top + 0.05)), 0.015, "galv", sides=4)
    # couplets on the inner pilasters
    for xx, r in ((-1.1, "c3"), (1.1, "c4")):
        b.lquad(xx - 0.12, xx + 0.12, -0.09, 0.6, 2.6, "signs_b", rect=r)
    # neon over the door: a vertical sign and a fish
    k.sign(b.w((hw - 0.3, -0.8, gh + 2.4)), 0.6, 2.4, 90, "signs_b", "v_restaurant", emit=2.2, depth=0.22, double=True)
    neon_text("海景", b.w((0.0, -0.2, gh + 1.6)), 0.9, 0, (1.0, 0.15, 0.3), board=True)
    # upper floors
    b.upper_front(lit_chance=0.7)
    # interior
    k.wet = 0.0
    yi0, yi1 = yf + B.WALL_T, yf + depth - B.WALL_T
    xi0, xi1 = x0 + 0.3, x1 - 0.3
    ceil = gh - 0.2
    k.box(((xi0 + xi1) / 2, (yi0 + yi1) / 2, 0.005), (xi1 - xi0, yi1 - yi0, 0.01), "terrazzo", faces=["+z"])
    k.box(((xi0 + xi1) / 2, (yi0 + yi1) / 2, ceil + 0.05), (xi1 - xi0, yi1 - yi0, 0.1), "plaster", (0.5, 0.42, 0.32), faces=["-z"])
    # side walls (inside faces): wallpaper above a dark wood dado
    for x, sgn in ((xi0, 1), (xi1, -1)):
        k.box((x - sgn * 0.15, (yi0 + yi1) / 2, ceil / 2), (0.3, yi1 - yi0, ceil), "wallpaper", col="concrete", faces=["+x" if sgn > 0 else "-x"])
        k.box((x + sgn * 0.01, (yi0 + yi1) / 2, 0.55), (0.04, yi1 - yi0, 1.1), "darkwood")
        k.box((x - sgn * 0.15, (yi0 + yi1) / 2, (ceil + b.H) / 2 + 1), (0.3, depth, b.H - ceil), b.wall, b.tint)
    # kitchen partition with a doorway and a serving hatch
    yk = yf + 6.6
    k.box(((xi0 + -14.6) / 2, yk, ceil / 2), (-14.6 - xi0, 0.2, ceil), "wallpaper", col="drywall")
    k.box(((-13.4 + xi1) / 2, yk, ceil / 2), (xi1 + 13.4, 0.2, ceil), "wallpaper", col="drywall")
    k.box((-14.0, yk, (2.2 + ceil) / 2), (1.2, 0.2, ceil - 2.2), "wallpaper")
    k.box(((xi0 - 14.6) / 2, yk - 0.1, 0.55), (-14.6 - xi0, 0.04, 1.1), "darkwood")
    k.box((-19.5, yk - 0.12, 1.4), (2.2, 0.06, 0.7), "windows", rect=None) if False else None
    k.sign((-19.5, yk - 0.11, 2.0), 2.4, 1.2, 0, "signs_b", "menu", depth=0.04)
    # back wall with the kitchen door to the alley
    yb = yf + depth
    b.back(door_x=b.w((0, 0, 0))[0] - (-16.0) if False else -16.0 - (x0 + x1) / 2 + 0.0, fire_escape=True, lit_chance=0.5)
    k.box(((xi0 + xi1) / 2, yi1 + 0.01, ceil / 2), (xi1 - xi0, 0.02, ceil), "mosaic", (0.55, 0.55, 0.52), faces=["-y"])
    # tables, lanterns, the roast meat window, the fish tanks, the counter
    for (tx, ty) in ((-21.3, 14.8), (-17.4, 15.0), (-21.0, 17.6), (-14.8, 17.3)):
        P.round_table(k, (tx, ty, 0.0), seats=6, cloth=pick([(0.55, 0.06, 0.05), (0.6, 0.55, 0.45)]))
        P.lantern(k, (tx, ty, ceil), 0.3, energy=26.0, tassel=True)
    P.roast_rack(k, xi0 + 0.3, -19.5, yi0 + 0.45, 2.6, n=7)
    P.light(k, (-21.0, yi0 + 0.8, 3.0), (1.0, 0.7, 0.4), 30.0, radius=0.3)
    P.fish_tank_wall(k, -16.4, xi1 - 0.2, yi0 + 0.45, 0.0, facing=1)
    P.counter(k, -15.5, -13.0, yk - 1.0)
    k.box((-14.0, yk - 1.0, 1.15), (0.4, 0.35, 0.18), "plastic", (0.6, 0.55, 0.3))  # cash register
    P.potted_plant(k, (xi0 + 0.4, yk - 0.5, 0.0), 1.2)
    k.sign((xi1 - 0.02, 16.5, 2.3), 0.9, 0.9, 270, "signs_b", "poster")
    k.sign((xi0 + 0.02, 16.0, 2.3), 0.9, 0.9, 90, "signs_b", "poster")
    k.sign((-14.0, yk - 0.11, 2.45), 0.5, 0.25, 0, "signs_b", "exit", emit=3.0)
    # kitchen
    P.wok_station(k, (-19.5, yi1 - 0.45, 0.0), 180, length=4.0)
    P.counter(k, -23.4 + 0.2, -21.2, yk + 1.2, depth=0.7, height=0.9, front=(0.5, 0.5, 0.5))
    P.shelf_unit(k, (-13.0, yk + 1.5, 0.0), 90, w_=1.6, h=2.0, d=0.45, mat="galv")
    P.gas_cylinder(k, (-22.8, yi1 - 0.4, 0.0))
    P.fluoro(k, (-18.0, yk + 1.6, ceil), 0, length=1.5, energy=16.0)
    P.fluoro(k, (-14.5, yk + 1.6, ceil), 0, length=1.5, energy=16.0)
    P.styro_stack(k, (-15.0, yi1 - 0.5, 0.0), 0, n=3)
    k.marker("steam", (-19.5, yi1 + 0.6, 4.4), rate=1.5)
    k.marker("spawn", (-17.5, yk + 1.6, 0.0), name="restaurant_kitchen")
    k.marker("audio", (-18.0, 15.0, 2.0), sound="radio", volume=-8.0)
    # colliders: front pilasters, kitchen back wall pieces are boxes already; upper building mass
    k.collider(((x0 + x1) / 2, yf + depth / 2, ceil + (b.H - ceil) / 2 + 0.6), (x1 - x0, depth, b.H - ceil + 1.2), 0, "concrete")
    for xa, xb in ((-hw, -hw + pil), (hw - pil, hw), (-1.3, -0.9), (0.9, 1.3)):
        k.collider(b.w(((xa + xb) / 2, 0.1, gh / 2)), (xb - xa, 0.4, gh), 0, "concrete")
    k.collider(b.w((0, 0.15, (op_top + gh) / 2)), (b.w_, 0.3, gh - op_top), 0, "concrete")
    k.wet = 1.0


# ====================================================================== alley A and the back alley

def alley_a():
    x0, x1 = 3.0, 6.0
    k.wet = 1.0
    P.lantern_string(k, (x0, 14.0, 4.6), (x1, 14.0, 4.6), n=2, sag=0.3)
    P.lantern_string(k, (x0, 17.5, 4.8), (x1, 17.5, 4.6), n=2, sag=0.3)
    P.lantern_string(k, (x0, 20.5, 4.6), (x1, 20.5, 4.8), n=2, sag=0.3)
    P.trash_bin(k, (5.5, 13.0, 0.0))
    P.crate_stack(k, (3.4, 18.5, 0.0), 0, rows=3, cols=1)
    P.gas_cylinder(k, (5.6, 20.0, 0.0))
    P.laundry(k, (x0, 16.0, 7.5), (x1, 16.0, 7.6), sag=0.3)
    P.laundry(k, (x0, 19.0, 10.5), (x1, 19.0, 10.4), sag=0.3)
    neon_text("麻雀", (x0 + 0.05, 15.0, 7.0), 0.75, 90, (0.2, 1.0, 0.5), vertical=True, board=True)
    k.marker("spawn", (4.5, 21.0, 0.0), name="alley_a")


def back_alley():
    k.wet = 1.0
    y0, y1 = 22.0, 28.0
    # end walls: west brick wall with a gate, east chain-link + fence boards
    k.box((-30.0, 25.0, 1.6), (0.3, 6.0, 3.2), "brick", col="concrete")
    k.box((-30.0, 25.0, 3.25), (0.4, 6.2, 0.1), "concrete", (0.5, 0.5, 0.5))
    k.box((30.0, 25.0, 1.4), (0.1, 6.0, 2.8), "corrugated", (0.4, 0.3, 0.25), col="sheet_metal")
    # boundary building backs at y=28..34 (facing south)
    for (xa, xb, floors, wall, tint) in ((-30.0, -12.0, 5, "brick", None), (-12.0, 8.0, 6, "plaster", (0.45, 0.48, 0.42)), (8.0, 30.0, 5, "brick", None)):
        bb = B.Building(k, xa, xb, y1, 6.0, floors, facing=-1, wall=wall, tint=tint or (0.5, 0.5, 0.5), ground_h=3.6, bay=3.0)
        bb.shopfront("wall", x_lo=-bb.w_ / 2, x_hi=bb.w_ / 2)
        bb.upper_front(lit_chance=0.45)
        if floors > 3:
            mid = (xa + xb) / 2
            P.fire_escape(k, mid - 2.0, mid + 2.0, y1, floors - 1, z_first=3.6, floor_h=3.1, facing=-1, ladder_to_ground=True)
        k.collider(((xa + xb) / 2, y1 + 3.0, 8.0), (xb - xa, 6.0, 16.0), 0, "concrete")
    # clutter
    P.dumpster(k, (-25.0, 26.8, 0.0), 0)
    P.dumpster(k, (11.0, 26.9, 0.0), 0, tint=(0.15, 0.2, 0.35))
    P.trash_bags(k, (-22.6, 27.0, 0.0), 6)
    P.trash_bags(k, (13.3, 27.0, 0.0), 4)
    P.crate_stack(k, (-10.5, 23.0, 0.0), 0, rows=4, cols=2)
    P.styro_stack(k, (-14.0, 22.8, 0.0), 10, n=4)
    P.styro_stack(k, (-13.3, 22.7, 0.0), -5, n=3)
    for x in (-5.0, -4.4, 20.0):
        P.gas_cylinder(k, (x, 27.5, 0.0))
    P.barrel(k, (24.0, 27.2, 0.0), rust=True)
    P.barrel(k, (24.7, 26.6, 0.0))
    P.bicycle(k, (0.5, 27.4, 0.0), 0)
    P.hand_trolley(k, (-18.5, 23.0, 0.0), -20)
    P.crate(k, (17.0, 23.0, 0.0), 10)
    P.crate(k, (17.1, 23.1, 0.7), -5, size=(0.8, 0.7, 0.6))
    for x, y in ((-26.0, 22.2), (-6.0, 22.2), (9.0, 22.2), (22.0, 22.2)):
        P.ac_unit(k, (x, y, 2.6), 180)
    # kitchen exhaust fans with steam, overhead wires, laundry between the buildings
    for x in (-21.0, -9.0, 19.0):
        k.box((x, 22.15, 3.0), (0.7, 0.3, 0.7), "galv")
        k.cyl((x, 22.31, 3.0), (x, 22.33, 3.0), 0.3, "grate", (0.5, 0.5, 0.5), sides=12)
        k.marker("steam", (x, 22.5, 3.0), rate=0.8)
    for i, (xa, xb) in enumerate(((-28.0, -20.0), (-16.0, -6.0), (-2.0, 6.0), (10.0, 20.0), (22.0, 29.0))):
        P.laundry(k, (xa, y0 + 0.3, 7.0 + (i % 2) * 3.0), (xa, y1 - 0.3, 7.2 + (i % 2) * 3.0), sag=0.35)
        P.laundry(k, (xb, y0 + 0.3, 10.0), (xb, y1 - 0.3, 10.2), sag=0.3)
    for x in (-27.0, -12.0, 2.0, 18.0):
        k.tube(P.catenary((x, y0, 5.5), (x + 3.0, y1, 6.0), 0.5), 0.01, "plastic", (0.05, 0.05, 0.05), sides=3)
    for x in (-24.0, -6.0, 8.0, 24.0):
        P.bulb(k, (x, y1 - 0.4, 3.2), (1.0, 0.75, 0.45), 28.0, cord=0.05, shade=(0.2, 0.25, 0.22))
    P.lantern_string(k, (-20.0, y0, 4.3), (-20.0, y1, 4.6), n=3, sag=0.4)
    neon_text("宵夜", (-0.5, y1 - 0.05, 4.2), 0.7, 0, (1.0, 0.5, 0.1), board=True, facing=-1)
    k.marker("spawn", (-28.5, 25.0, 0.0), name="back_alley_west")
    k.marker("spawn", (28.5, 25.0, 0.0), name="back_alley_east")
    k.marker("audio", (-20.0, 23.0, 3.0), sound="exhaust", volume=-6.0)


# ====================================================================== the street itself

def street():
    k.wet = 1.0
    # lantern strings across the street, staggered heights
    for i, x in enumerate(np.arange(-34.0, 44.0, 6.0)):
        z0 = 6.0 + (i % 2) * 0.6
        P.lantern_string(k, (x, 2.2, z0), (x + rnd(-1, 1), 11.8, z0 + rnd(-0.4, 0.4)), n=5, sag=0.9, r=0.21, energy=10.0)
    # overhead cables
    for x in np.arange(-40.0, 44.0, 9.0):
        k.tube(P.catenary((x, 2.0, 8.5), (x + 4.0, 12.0, 9.0), 0.7), 0.012, "plastic", (0.05, 0.05, 0.05), sides=3)
    # street lamps on the north sidewalk, facing the road
    for x in (-30.0, -8.0, 12.0, 34.0):
        P.street_lamp(k, (x, 11.6, 0.0), yaw=0, height=6.2, reach=1.5)
    P.street_lamp(k, (-21.0, 2.4, 0.0), yaw=180, height=6.2, reach=1.5)
    P.street_lamp(k, (22.0, 2.4, 0.0), yaw=180, height=6.2, reach=1.5)
    # parked van and a car-ish delivery van: cover in the road
    P.van(k, (-6.0, 5.3, ROAD_Z), 0, tint=(0.62, 0.62, 0.6))
    P.van(k, (28.5, 8.7, ROAD_Z), 180, tint=(0.25, 0.32, 0.4))
    # street furniture
    P.hydrant(k, (-14.5, 11.4, 0.0))
    P.hydrant(k, (15.0, 2.6, 0.0))
    P.trash_bin(k, (-25.5, 2.5, 0.0))
    P.trash_bin(k, (9.8, 11.5, 0.0), (0.4, 0.15, 0.1))
    P.newspaper_stand(k, (-2.0, 11.3, 0.0), 0)
    P.bicycle(k, (-28.8, 11.4, 0.0), 0)
    P.bicycle(k, (19.5, 11.5, 0.0), 180)
    P.potted_plant(k, (-12.6, 11.5, 0.0), 1.2)
    P.potted_plant(k, (-23.4, 11.5, 0.0), 1.2)
    P.cone(k, (-10.5, 4.5, ROAD_Z))
    P.cone(k, (-10.2, 4.3, ROAD_Z))
    P.crate_stack(k, (13.8, 11.2, 0.0), 0, rows=2, cols=2)
    P.styro_stack(k, (-9.0, 2.7, 0.0), 5, n=3)
    P.styro_stack(k, (-8.3, 2.6, 0.0), -10, n=2)
    P.crate(k, (24.0, 2.8, 0.0), 30)
    # neon: big vertical "龍鳳" over the street and the market's fish
    neon_text("龍鳳", (-8.0, 12.0 - 0.3, 9.5), 1.1, 0, (1.0, 0.2, 0.45), vertical=True, board=True)
    neon_text("金華", (-9.0, 12.0 - 0.3, 5.2), 0.55, 0, (1.0, 0.75, 0.2), board=False)
    neon_text("冰室", (20.0, 12.0 - 0.3, 9.0), 0.9, 0, (0.2, 0.85, 1.0), vertical=True, board=True)
    neon_text("OPEN", (-1.5, 12.0 - 0.32, 3.55), 0.38, 0, (1.0, 0.1, 0.15), board=False, latin=True)
    k.marker("audio", (-20.0, 6.0, 4.0), sound="neon", volume=-10.0)
    k.marker("audio", (20.0, 6.0, 4.0), sound="neon", volume=-10.0)


def gate_and_ends():
    """Paifang gate over the west end of the street; barricades at both ends."""
    gx = -40.5
    red = (0.5, 0.5, 0.5)
    green = (0.2, 0.55, 0.4)
    k.wet = 1.0
    posts = [2.4, 5.0, 9.0, 11.6]
    for y in posts:
        k.box((gx, y, 0.35), (0.9, 0.9, 0.7), "stone", (0.5, 0.5, 0.5), col="concrete", chamfer=0.05)
        h = 8.2 if y in (5.0, 9.0) else 6.6
        k.cyl((gx, y, 0.7), (gx, y, h), 0.28, "lacquer", red, sides=14)
        k.collider((gx, y, h / 2), (0.56, 0.56, h), 0, "wood")
        # stone drum footings
        k.lathe(np.array((gx, y, 0.7)), [(0.36, 0.0), (0.4, 0.15), (0.36, 0.3), (0.28, 0.32)], "stone", (0.5, 0.5, 0.5), sides=14)
    # beams, lintels and the central plaque
    for (ya, yb, z) in ((2.4, 5.0, 5.9), (9.0, 11.6, 5.9), (5.0, 9.0, 7.0), (5.0, 9.0, 5.6)):
        k.box((gx, (ya + yb) / 2, z), (0.5, yb - ya + 0.6, 0.5), "lacquer", red, chamfer=0.03)
        with k.atlas("props", "gold_pad"):
            k.box((gx, (ya + yb) / 2, z + 0.3), (0.55, yb - ya + 0.6, 0.12), "props", (0.5, 0.5, 0.5))  # gold trim
    k.sign((gx - 0.27, 7.0, 6.3), 2.8, 0.95, 270, "signs_a", "gate", depth=0.1, back_tint=(0.4, 0.3, 0.1))
    k.sign((gx + 0.27, 7.0, 6.3), 2.8, 0.95, 90, "signs_a", "gate", depth=0.0)
    # bracket sets and green glazed roofs (three: centre higher)
    for (ya, yb, z, w) in ((1.8, 5.6, 6.6, 1.8), (8.4, 12.2, 6.6, 1.8), (4.4, 9.6, 8.2, 2.2)):
        for i, yy in enumerate(np.linspace(ya + 0.2, yb - 0.2, 7)):
            k.box((gx, yy, z - 0.25), (0.6 + 0.2 * (i % 2), 0.22, 0.25), "lacquer", (0.2, 0.45, 0.4), chamfer=0.02)
        roof_eave = z + 0.1
        roof_top = z + 0.9
        for s in (-1, 1):
            a = (gx + s * w, ya - 0.4, roof_eave)
            bb = (gx + s * w, yb + 0.4, roof_eave)
            c = (gx, yb + 0.2, roof_top)
            d = (gx, ya - 0.2, roof_top)
            # upturned corners: lift the eave ends
            a = (a[0], a[1], a[2] + 0.35)
            bb = (bb[0], bb[1], bb[2] + 0.35)
            if s < 0:  # tiles face up and out, the painted soffit faces down
                k.quad(bb, a, d, c, "rooftile", green)
                k.quad(a, bb, c, d, "lacquer", (0.2, 0.45, 0.4))
            else:
                k.quad(a, bb, c, d, "rooftile", green)
                k.quad(bb, a, d, c, "lacquer", (0.2, 0.45, 0.4))
        k.box((gx, (ya + yb) / 2, roof_top + 0.08), (0.3, yb - ya + 0.4, 0.22), "rooftile", green)
        for yy in (ya - 0.3, yb + 0.3):
            k.lathe(np.array((gx, yy, roof_top + 0.15)), [(0.0, 0), (0.12, 0.05), (0.08, 0.35), (0.14, 0.5), (0.0, 0.6)], "rooftile", green, sides=8)
        for s in (-1, 1):
            for yy in (ya - 0.4, yb + 0.4):
                P.lantern(k, (gx + s * (w - 0.2), yy, roof_eave + 0.2), 0.24, energy=22.0)
    # lion statues (simplified) either side of the gate on plinths
    for y in (0.9, 13.1):
        k.box((gx, y, 0.5), (1.0, 0.8, 1.0), "stone", (0.45, 0.45, 0.45), col="concrete", chamfer=0.04)
        k.lathe(np.array((gx, y, 1.0)), [(0.35, 0.0), (0.38, 0.2), (0.3, 0.6), (0.34, 0.8), (0.3, 1.0), (0.15, 1.15), (0.0, 1.18)], "stone", (0.5, 0.5, 0.48), sides=10)
        k.lathe(np.array((gx + 0.15, y, 1.75)), [(0.0, 0.0), (0.24, 0.05), (0.27, 0.25), (0.2, 0.42), (0.0, 0.46)], "stone", (0.5, 0.5, 0.48), sides=10)
    # beyond the gate: the street is closed (barriers, a parked truck)
    for y in (2.8, 5.0, 7.2, 9.4, 11.6):
        P.jersey(k, (-44.0, y, ROAD_Z if ROAD_Y0 < y < ROAD_Y1 else 0.0), 90 + rnd(-6, 6))
    P.box_truck(k, (-49.5, 7.0, ROAD_Z), 85, tint=(0.4, 0.42, 0.45), box_tint=(0.6, 0.6, 0.58))
    P.cone(k, (-42.5, 4.0, ROAD_Z))
    P.cone(k, (-42.8, 9.5, ROAD_Z))
    k.marker("spawn", (-44.5, 0.5 + 6.0, ROAD_Z), name="west_barrier")
    # east end: plywood hoarding and scaffold, posters
    hx = 45.5
    k.box((hx, 7.0, 1.5), (0.1, 10.5, 3.0), "planks", (0.55, 0.5, 0.42), col="wood")
    for y in (3.0, 6.0, 9.0, 11.5):
        k.quad((hx - 0.06, y + 0.6, 0.6), (hx - 0.06, y - 0.6, 0.6), (hx - 0.06, y - 0.6, 2.2), (hx - 0.06, y + 0.6, 2.2), "props", rect="posters")
    for y in np.arange(2.0, 12.5, 2.0):
        k.cyl((hx - 0.4, y, 0.0), (hx - 0.4, y, 6.0), 0.03, "galv", sides=5)
    for z in (2.0, 4.0, 6.0):
        k.cyl((hx - 0.4, 2.0, z), (hx - 0.4, 12.0, z), 0.03, "galv", sides=5)
    k.quad((hx - 0.45, 2.0, 3.0), (hx - 0.45, 12.0, 3.0), (hx - 0.45, 12.0, 6.5), (hx - 0.45, 2.0, 6.5), "canvas", (0.15, 0.35, 0.2), double=True)
    P.light(k, (hx - 1.0, 7.0, 3.2), (1.0, 0.4, 0.1), 15.0, radius=0.05)
    k.lathe(np.array((hx - 0.5, 7.0, 3.1)), [(0.0, 0), (0.06, 0.02), (0.06, 0.12), (0.0, 0.14)], "emissive", (0.6, 0.2, 0.02), sides=8, emit=10.0)
    k.marker("spawn", (43.5, 6.5, ROAD_Z), name="east_hoarding")
    # backdrop facades past the gate so the street reads as continuing
    bw = B.Building(k, -60.0, -47.0, 12.0, 8.0, 5, wall="brick", bay=3.0)
    bw.shopfront("shutter", x_lo=-6.5, x_hi=0.0, sign="noodle")
    bw.shopfront("glass", x_lo=0.0, x_hi=6.5, vsign="v_hotel")
    bw.upper_front(lit_chance=0.5)
    bs = B.Building(k, -60.0, -47.0, 2.0, 8.0, 4, facing=1, wall="plaster", tint=(0.45, 0.42, 0.4), bay=3.0)
    bs.shopfront("shutter", x_lo=-6.5, x_hi=6.5)
    bs.upper_front(lit_chance=0.5)


# ====================================================================== neon text

_FONT_CACHE = {}


def _blender_font(ch, latin=False):
    """Convert the woff2 chunk that holds `ch` to an .otf Blender can load."""
    from cjk import FontSet
    from fontTools.ttLib import TTFont
    fam = "sans"
    fs = _FONT_CACHE.setdefault(fam, FontSet(fam))
    src = fs.cmap[ord(ch)]
    os.makedirs(BUILD_DIR, exist_ok=True)
    dst = os.path.join(BUILD_DIR, os.path.basename(src).replace(".woff2", ".otf"))
    if not os.path.exists(dst):
        f = TTFont(src)
        f.flavor = None
        f.save(dst)
    key = ("bf", dst)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = bpy.data.fonts.load(dst)
    return _FONT_CACHE[key]


def neon_text(text, pos, size, yaw, color, vertical=False, board=True, latin=False, facing=-1):
    """Glowing glass tubes following each glyph's outline, on a dark backing board."""
    R = rot_z(yaw if facing < 0 else yaw + 180)
    n = R @ np.array([0, -1.0, 0])
    xax = R @ np.array([1.0, 0, 0])
    pos = np.asarray(pos, np.float64)
    step = size * (1.05 if not latin else 0.62)
    count = len(text)
    total = step * count
    objs = []
    for i, ch in enumerate(text):
        if vertical:
            off = np.array([0, 0, total / 2 - step * (i + 0.5)])
        else:
            off = xax * (-total / 2 + step * (i + 0.5))
        cu = bpy.data.curves.new("neon", "FONT")
        cu.body = ch
        cu.font = _blender_font(ch, latin)
        cu.size = size
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.fill_mode = "NONE"
        cu.bevel_depth = size * 0.018
        cu.bevel_resolution = 1
        cu.resolution_u = 2
        ob = bpy.data.objects.new("neon", cu)
        bpy.context.scene.collection.objects.link(ob)
        M = np.eye(4)
        Rm = R @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])  # text plane XY -> facade (x, z), facing -y
        M[:3, :3] = Rm
        M[:3, 3] = pos + off + n * 0.06
        ob.matrix_world = [list(r) for r in M]
        objs.append(ob)
    bpy.context.view_layer.update()
    tint = tuple(c * 0.5 for c in color)
    for ob in objs:
        k.add_object(ob, "emissive", tint, emit=7.0)
        bpy.data.objects.remove(ob)
    if board:
        w = (size * 1.25) if vertical else (total + size * 0.3)
        h = (total + size * 0.3) if vertical else (size * 1.25)
        k.sign(pos, w, h, yaw if facing < 0 else yaw + 180, "props", "black_pad", depth=0.06, back_tint=(0.08, 0.08, 0.08))
        for zz in (h * 0.3, -h * 0.3):
            k.cyl(pos + (0, 0, zz) - n * 0.0, pos + (0, 0, zz) - n * -0.4 + n * 0.0 - n * 0.4, 0.02, "galv", sides=4)
    light_pos = pos + n * 0.5
    P.light(k, light_pos, color, 30.0 * size * count, radius=size * count * 0.4, kind="AREA", dyn=True, rng=7.0)


# ====================================================================== cameras and player start

def gameplay_markers():
    # On the quay, facing the fish market with the lantern street behind it (Godot yaw 0 = north).
    k.marker("player_start", (-5.0, -21.5, 0.0), yaw=-12.0)
    cams = {
        "CapQuay": ((-30.0, -21.0, 1.7), (-5.0, -8.0, 2.5)),
        "CapMarket": ((-11.0, -11.5, 1.7), (8.0, -2.0, 1.5)),
        "CapStreetWest": ((-36.0, 7.0, 1.75), (0.0, 8.0, 4.0)),
        "CapStreetEast": ((30.0, 6.0, 1.75), (-4.0, 9.0, 4.5)),
        "CapRestaurant": ((-14.0, 13.6, 1.6), (-22.0, 18.0, 1.2)),
        "CapBackAlley": ((25.0, 25.0, 1.7), (-10.0, 24.0, 3.0)),
        "CapBoat": ((-27.0, -30.0, 1.7), (-19.0, -40.0, 2.0)),
        "CapGallery": ((26.0, -15.5, 5.3), (0.0, -10.0, 1.5)),
        "CapOverview": ((10.0, -40.0, 22.0), (-2.0, 2.0, 0.0)),
        "CapGate": ((-25.0, 6.5, 1.7), (-41.0, 7.0, 5.0)),
    }
    for name, (p, t) in cams.items():
        k.marker("camera", p, name=name, target=[float(x) for x in t])


# ====================================================================== export

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ground()
    water_walls()
    pier()
    boat()
    quay()
    market()
    warehouse()
    east_tenement()
    south_front_west()
    north_row()
    alley_a()
    back_alley()
    street()
    gate_and_ends()
    gameplay_markers()
    print("kit:", k.stats(), flush=True)

    def group(attrs, centre, kit):
        emit = attrs[2]
        detail = attrs[4]
        ch = kit.chunk_of(centre)
        if emit > 0.5 and attrs[0] == kit.L("emissive"):
            return "c%02d_glow" % ch
        if attrs[0] == kit.L("glass"):
            return "c%02d_glass" % ch
        return "c%02d_%s" % (ch, "detail" if detail else "main")

    objs = k.build_objects("ct", group)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    import json
    with open(os.path.join(OUT_DIR, "layout.json"), "w") as f:
        json.dump({"bounds": [XMIN, YMIN, XMAX, YMAX], "water_z": WATER_Z, "road_z": ROAD_Z,
                   "colliders": k.colliders, "markers": k.markers}, f, indent=0)
    blend = os.path.join(BUILD_DIR, "chinatown.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("objects:", len(objs), "saved", blend)


if __name__ == "__main__":
    main()
