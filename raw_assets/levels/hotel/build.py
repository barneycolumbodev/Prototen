"""The Golden Dragon Grand Hotel: an abandoned five-star lobby, still lit (map 2).

Owner brief (2026-11-18): a luxurious Chinese five-star hotel lobby, abandoned
but fully lit, all inside. Waves come down in the lifts and in from the
street. Tight corridors winding round a central atrium (hold choke points,
or slide through them on the offensive, in and out of cover) and the
atrium's long sight lines for stalking.

Run (Blender 5.2 / bpy):
    tools/blender.sh raw_assets/levels/hotel/build.py
    tools/blender.sh raw_assets/levels/hotel/bake.py -- [--size 4096] [--samples 128]

Writes raw_assets/levels/hotel/_build/hotel.blend (for the bake) and
assets/levels/hotel/layout.json (colliders, spawns, lifts, lights, cameras).

How it is authored: two cell grids, 1 m cells, one per storey (ground z = 0,
mezzanine z = 4.5). Rooms and corridors are painted in as rectangles of a
cell type (TYPES: walkable or not, ceiling height, floor, wall style).
`generate()` turns them into walls along every boundary between a walkable
cell and a solid one, headers where ceilings step, floors, ceilings,
balustrades along the atrium void, and merged box colliders. Furniture,
light fittings and set dressing are placed on top by hand.

Plan (Blender coordinates, metres: +X east, +Y north, +Z up; Godot: x, z, -y):

  y=33 ┌────────────── service corridor (staff only) ─────────────────┐
  y=26 │ west │  LIFT HALL: six lifts in the north wall      │ east   │
  y=20 │ wing ├──────── arcade under the mezzanine gallery ──┤ wing   │
       │ bar, │   ATRIUM 32 x 20, open 15 m: fountain,        │ rest-  │
       │ back │   reception, lounges, twin grand stairs       │ rooms, │
       │ stair│   up to the gallery                           │ stair  │
  y=-8 │      ├──── ENTRANCE HALL (7.5 m) ────────────────────┤        │
  y=-16└──────┴──── glass doors ────────────────────────────────┴────────┘
  y=-27        porte-cochère under the canopy (outside: spawns)
       x=-38                                                     x=38
"""
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
sys.path.insert(0, os.path.join(HERE, "..", "chinatown"))
from envkit import Kit, rot_x, rot_y, rot_z  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
MATS = os.path.join(ROOT, "assets", "env", "hotel", "materials.json")
OUT_DIR = os.path.join(ROOT, "assets", "levels", "hotel")
BUILD_DIR = os.path.join(HERE, "_build")

XMIN, XMAX, YMIN, YMAX = -38, 38, -28, 33
NX, NY = XMAX - XMIN, YMAX - YMIN
FLOOR2 = 4.5          # mezzanine floor
CEIL2 = 8.1           # mezzanine ceiling
ATRIUM_TOP = 15.0     # atrium ceiling
SOLID_TOP = 8.6       # top of wall colliders
RNG = np.random.default_rng(2026)

k = Kit(MATS, (XMIN, YMIN, XMAX, YMAX), chunks=(4, 3))
k.wet = 0.0  # indoors: the rain never reaches anything


def rnd(a, b):
    return float(RNG.uniform(a, b))


def frame(pos, yaw):
    R = rot_z(yaw)
    P = np.asarray(pos, np.float64)
    return R, (lambda local: P + R @ np.asarray(local, np.float64))


def light(pos, color, energy, radius=0.05, kind="POINT", dyn=False, spot=None, direction=None, rng=8.0):
    """energy: bake units (× LIGHT_SCALE in bake.py). dyn: also a runtime light for characters."""
    d = dict(color=[round(c, 3) for c in color], energy=energy, radius=radius, type=kind, dyn=dyn, range=rng)
    if spot:
        d["spot"] = spot
    if direction is not None:
        d["dir"] = [round(float(x), 3) for x in direction]
    k.marker("light", pos, **d)


WARM = (1.0, 0.78, 0.52)
GOLDLIGHT = (1.0, 0.72, 0.4)
COOL = (0.82, 0.95, 0.9)

# ====================================================================== cell types

# walk: walkable. ceil: ceiling height above the storey's floor (None = open
# void, up to `top`). floor/ceil materials and the wall style.
TYPES = {
    "#": dict(walk=False),
    "G": dict(walk=False, glass=True),
    "A": dict(walk=True, ceil=None, top=ATRIUM_TOP, floor=("marble", None), wall="marble", open=True),
    "S": dict(walk=True, ceil=None, top=CEIL2, floor=("carpet", (0.5, 0.5, 0.5)), wall="damask", open=True),
    "a": dict(walk=True, ceil=4.0, floor=("marble", None), ceiling=("plaster", (0.62, 0.58, 0.5)), wall="silk"),
    "h": dict(walk=True, ceil=7.5, floor=("marble", None), ceiling=("plaster", (0.62, 0.58, 0.5)), wall="marble"),
    "v": dict(walk=True, ceil=4.0, floor=("marble_dark", None), ceiling=("brass", (0.4, 0.38, 0.36)), wall="stone"),
    "l": dict(walk=True, ceil=4.0, floor=("marble", None), ceiling=("plaster", (0.6, 0.56, 0.48)), wall="liftmarble"),
    "e": dict(walk=True, ceil=2.6, floor=("carpet", (0.35, 0.35, 0.4)), ceiling=("brass", (0.45, 0.42, 0.38)), wall="car"),
    "c": dict(walk=True, ceil=3.0, floor=("carpet", None), ceiling=("plaster", (0.6, 0.57, 0.5)), wall="damask"),
    "b": dict(walk=True, ceil=3.4, floor=("darkwood", (0.42, 0.38, 0.36)), ceiling=("rosewood", (0.5, 0.5, 0.5)), wall="rosewood"),
    "s": dict(walk=True, ceil=2.8, floor=("epoxy", (0.42, 0.44, 0.42)), ceiling=("concrete", (0.5, 0.5, 0.5)), wall="service"),
    "r": dict(walk=True, ceil=2.8, floor=("terrazzo", None), ceiling=("plaster", (0.62, 0.6, 0.55)), wall="marble"),
    "k": dict(walk=True, ceil=2.8, floor=("epoxy", (0.38, 0.38, 0.4)), ceiling=("plaster", (0.5, 0.5, 0.48)), wall="office"),
    "o": dict(walk=True, ceil=None, top=0.0, floor=("stone", (0.45, 0.44, 0.42)), wall="stone", outside=True),
    # Stair landings in the atrium: mezzanine floor, open to the atrium roof.
    "p": dict(walk=True, ceil=ATRIUM_TOP - FLOOR2, floor=("marble", None), wall="silk", noceil=True),
    "g": dict(walk=True, ceil=CEIL2 - FLOOR2, floor=("carpet", None), ceiling=("plaster", (0.62, 0.58, 0.5)), wall="silk"),
    "t": dict(walk=True, ceil=CEIL2 - FLOOR2, floor=("carpet", (0.36, 0.42, 0.4)), ceiling=("rosewood", (0.5, 0.5, 0.5)), wall="damask"),
    "f": dict(walk=True, ceil=CEIL2 - FLOOR2, floor=("carpet", (0.42, 0.4, 0.5)), ceiling=("plaster", (0.62, 0.6, 0.55)), wall="silkpale"),
}

L1 = np.full((NY, NX), "#", dtype="<U1")
L2 = np.full((NY, NX), "#", dtype="<U1")
ROOMS = []  # (level, type, x0, x1, y0, y1) for light placement


def paint(L, ch, x0, x1, y0, y1, lights=True):
    L[y0 - YMIN:y1 - YMIN, x0 - XMIN:x1 - XMIN] = ch
    if lights:
        ROOMS.append((1 if L is L1 else 2, ch, x0, x1, y0, y1))


def cell(L, x, y):
    if x < XMIN or x >= XMAX or y < YMIN or y >= YMAX:
        return "#"
    return L[y - YMIN, x - XMIN]


# Stairs: x0, x1, y_bottom, y_top (the ramp rises from y_bottom to y_top), material.
STAIRS = [
    (-16, -13, 10, -2, "marble"),
    (13, 16, 10, -2, "marble"),
    (-34, -32, 1, 12, "carpet"),
    (32, 34, 1, 12, "carpet"),
]
LIFTS_X = [-10, -6, -2, 2, 6, 10]   # car centres; each 2 m wide, 3 m deep, doors on y = 26


def layout_cells():
    # ---- ground
    paint(L1, "a", -20, 20, -8, 20, lights=False)
    paint(L1, "A", -16, 16, -4, 16, lights=False)
    paint(L1, "h", -12, 12, -16, -8)
    # The facade: stone, glass panes, three door openings (the doors are long gone).
    paint(L1, "G", -12, 12, -17, -16, lights=False)
    for x0, x1 in ((-8, -5), (-2, 2), (5, 8)):
        paint(L1, "v", x0, x1, -17, -16, lights=False)
    paint(L1, "o", -30, 30, -27, -17, lights=False)
    # Lift hall and the six cars.
    paint(L1, "l", -14, 14, 20, 26)
    for cx in LIFTS_X:
        paint(L1, "e", cx - 1, cx + 1, 26, 29)
    # Service corridor behind the lifts, linking both wings.
    paint(L1, "s", -36, 36, 30, 32)
    for side in (-1, 1):
        def P(ch, x0, x1, y0, y1, L=L1):
            if side < 0:
                paint(L, ch, x0, x1, y0, y1)
            else:
                paint(L, ch, -x1, -x0, y0, y1)
        # Winding corridor: entrance hall -> south passage -> up the outer wall -> lift hall / service.
        P("c", -26, -12, -14, -12)       # from the entrance hall's side
        P("c", -28, -26, -14, 0)         # north
        P("c", -26, -20, -2, 0)          # a short cut into the arcade
        P("c", -37, -28, -2, 0)          # west, past the stair foot
        P("c", -37, -35, -2, 20)         # long run up the outer wall
        P("c", -37, -24, 18, 20)         # back east at the north end
        P("c", -26, -24, 20, 30)         # north to the service corridor
        P("c", -24, -14, 22, 24)         # into the lift hall
        P("c", -24, -20, 10, 12)         # a second way into the arcade
        P("c", -37, -30, -9, -7)         # dog-leg off the south passage (a dead end with a door)
        P("c", -31, -28, -12, -9)
        # Back stair shaft and its landing on the mezzanine.
        P("S", -34, -32, 0, 12)
        P("S", -34, -32, 0, 12, L2)
        P("g", -34, -30, 12, 14, L2)
        # Wing rooms.
        if side < 0:
            paint(L1, "b", -31, -22, 3, 16)          # the Dragon Bar
            paint(L1, "c", -22, -20, 5, 7)           # bar door to the arcade
            paint(L1, "c", -35, -31, 14, 16)         # bar's back door off the outer corridor
            paint(L1, "k", -24, -20, -11, -9)        # concierge office
            paint(L1, "c", -24, -22, -12, -11, lights=False)
        else:
            paint(L1, "r", 22, 31, 3, 9)             # restrooms
            paint(L1, "c", 20, 22, 5, 7)             # restroom door to the arcade
            paint(L1, "k", 22, 31, 11, 16)           # security office
            paint(L1, "c", 31, 35, 13, 15)           # office back door
            paint(L1, "k", 20, 24, -11, -9)          # luggage store
            paint(L1, "c", 22, 24, -12, -11, lights=False)
    # ---- mezzanine
    paint(L2, "g", -20, 20, -8, 20, lights=False)
    paint(L2, "A", -16, 16, -4, 16, lights=False)
    for x0, x1, yb, yt, _m in STAIRS[:2]:
        paint(L2, "S", x0, x1, min(yb, yt), max(yb, yt), lights=False)
        paint(L2, "p", x0, x1, -4, yt, lights=False)  # landing to the south gallery
    # West: tea lounge; east: ballroom foyer. Both open onto the gallery through two doors.
    paint(L2, "t", -30, -21, 4, 16)
    paint(L2, "g", -21, -20, 7, 9)
    paint(L2, "g", -21, -20, 12, 14)
    paint(L2, "g", -31, -30, 12, 14, lights=False)
    paint(L2, "f", 21, 30, 4, 16)
    paint(L2, "g", 20, 21, 7, 9)
    paint(L2, "g", 20, 21, 12, 14)
    paint(L2, "g", 30, 31, 12, 14, lights=False)
    # Galleries over the lift hall (a balcony looking down the atrium's long axis).
    paint(L2, "g", -14, 14, 20, 23)


def is_walk(ch):
    return TYPES[ch]["walk"]


def ceil_of(level, ch, x=None, y=None):
    """Absolute height of a cell's ceiling (open cells: their top)."""
    t = TYPES[ch]
    base = 0.0 if level == 1 else FLOOR2
    if t.get("open"):
        if ch == "A" or (x is not None and cell(L1, x, y) == "A"):
            return ATRIUM_TOP
        return CEIL2
    if t.get("outside"):
        return 0.0
    return base + t["ceil"]


# ====================================================================== wall styles

def wall_quad(a, b, z0, z1, mat, tint=None, emit=0.0, off=0.0, n=None):
    if z1 - z0 < 0.005:
        return
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    if off and n is not None:
        a = a + n * off
        b = b + n * off
    k.quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), mat, tint, emit)


def trim(a, b, n, z, h, depth, mat, tint=None, emit=0.0):
    """A horizontal moulding strip along a wall: box `h` tall, `depth` out."""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    c = (a + b) / 2 + n * depth / 2
    L = np.linalg.norm(b - a)
    yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    k.box((c[0], c[1], z + h / 2), (L, depth, h), mat, tint, yaw=yaw, faces=["+z", "-z", "+y", "-y"])


def wall_style(style, a, b, n, z0, z1, base):
    """Faces for a wall run from `a` to `b` (2D), facing `n`, from z0 to z1.
    `base`: the storey's floor (skirting and dado sit on it)."""
    full = abs(z0 - base) < 0.01
    if style in ("silk", "silkpale", "damask"):
        main = {"silk": ("silk", (0.55, 0.47, 0.32)), "silkpale": ("silk", (0.58, 0.55, 0.47)), "damask": ("wallpaper", None)}[style]
        if full and z1 - z0 > 2.0:
            wall_quad(a, b, z0, z0 + 1.0, "rosewood", None)
            trim(a, b, n, z0 + 0.98, 0.05, 0.03, "brass", None)
            trim(a, b, n, z0, 0.12, 0.02, "marble_dark", None)
            wall_quad(a, b, z0 + 1.0, z1 - 0.2, main[0], main[1])
            wall_quad(a, b, z1 - 0.2, z1, "rosewood", (0.45, 0.45, 0.45))
            trim(a, b, n, z1 - 0.22, 0.04, 0.03, "brass", None)
        else:
            wall_quad(a, b, z0, z1, main[0], main[1])
    elif style == "marble":
        wall_quad(a, b, z0, z1, "marble", None)
        if full:
            trim(a, b, n, z0, 0.14, 0.02, "marble_dark", None)
    elif style == "liftmarble":
        if full:
            wall_quad(a, b, z0, z0 + 2.9, "marble_dark", None)
            trim(a, b, n, z0 + 2.88, 0.06, 0.03, "brass", None)
            wall_quad(a, b, z0 + 2.9, z1, "marble", None)
        else:
            wall_quad(a, b, z0, z1, "marble", None)
    elif style == "rosewood":
        wall_quad(a, b, z0, z1, "rosewood", None)
        if full:
            trim(a, b, n, z0 + 2.4, 0.04, 0.03, "brass", None)
    elif style == "car":
        wall_quad(a, b, z0, z0 + 0.9, "brass", (0.42, 0.38, 0.34))
        wall_quad(a, b, z0 + 0.9, z1, "glass", (0.6, 0.55, 0.5))  # mirror
        trim(a, b, n, z0 + 0.88, 0.04, 0.05, "brass", None)
    elif style == "service":
        wall_quad(a, b, z0, z0 + 1.2, "plaster", (0.36, 0.4, 0.37))
        wall_quad(a, b, z0 + 1.2, z1, "plaster", (0.52, 0.52, 0.49))
        if full:
            trim(a, b, n, z0 + 0.4, 0.15, 0.03, "galv", None)  # trolley rail
    elif style == "office":
        wall_quad(a, b, z0, z1, "plaster", (0.5, 0.48, 0.44))
    elif style == "stone":
        wall_quad(a, b, z0, z1, "stone", (0.5, 0.48, 0.45))
    elif style == "upper":
        # The atrium above the gallery: rosewood with brass bands and a warm cove.
        wall_quad(a, b, z0, z1, "rosewood", (0.55, 0.5, 0.48))
        for z in np.arange(z0 + 2.2, z1 - 0.5, 2.3):
            trim(a, b, n, z, 0.08, 0.06, "brass", None)
            trim(a, b, n, z + 0.08, 0.03, 0.02, "emissive", (0.95, 0.65, 0.3), emit=4.0)
    elif style == "header":
        wall_quad(a, b, z0, z1, "plaster", (0.6, 0.56, 0.48))
        trim(a, b, n, z0 - 0.02, 0.06, 0.02, "brass", None)
    else:
        wall_quad(a, b, z0, z1, "plaster", None)


# ====================================================================== generation

DIRS = [((1, 0), "x+"), ((-1, 0), "x-"), ((0, 1), "y+"), ((0, -1), "y-")]


def edge_geom(x, y, d):
    """Boundary segment of cell (x, y) toward direction d, and the normal
    pointing back into the cell. Returns (a, b, n) with (b - a) x z = n."""
    dx, dy = d
    n = np.array([-dx, -dy, 0.0])
    cx, cy = x + 0.5, y + 0.5
    mid = np.array([cx + dx * 0.5, cy + dy * 0.5, 0.0])
    t = np.cross([0, 0, 1.0], n)
    return mid[:2] - t[:2] * 0.5, mid[:2] + t[:2] * 0.5, n


def stair_top_edge(x, y, d):
    """Is the edge from mezzanine cell (x, y) toward d the top exit of a stair?"""
    for x0, x1, yb, yt, _m in STAIRS:
        if not (x0 <= x < x1):
            continue
        if yt < yb and d == (0, 1) and y == yt - 1:
            return True
        if yt > yb and d == (0, -1) and y == yt:
            return True
    return False


def collect_edges():
    """Every wall piece as (key, line_coord, along_coord) for merging into runs."""
    runs = {}
    for level, L in ((1, L1), (2, L2)):
        base = 0.0 if level == 1 else FLOOR2
        for j in range(NY):
            for i in range(NX):
                ch = L[j, i]
                if not is_walk(ch):
                    continue
                x, y = XMIN + i, YMIN + j
                t = TYPES[ch]
                top = ceil_of(level, ch)
                for d, dname in DIRS:
                    nb = cell(L, x + d[0], y + d[1])
                    tn = TYPES[nb]
                    if t.get("outside"):
                        nx_, ny_ = x + d[0], y + d[1]
                        if nx_ < XMIN or nx_ >= XMAX or ny_ < YMIN or ny_ >= YMAX or tn.get("outside"):
                            continue
                        # Facade seen from the street: stone up to the parapet
                        # (over the glass, over the door openings).
                        z_from = 3.2 if tn.get("glass") else (ceil_of(1, nb) if tn["walk"] else 0.0)
                        add_run(runs, (1, "stone", z_from, 9.5, dname), x, y, d)
                        continue
                    if level == 2 and ch in "AS" and t.get("open"):
                        continue
                    if not tn["walk"]:
                        if tn.get("glass"):
                            add_run(runs, (level, "glasswall", base, top, dname), x, y, d)
                        elif t.get("open"):
                            # Open cells: the wall goes all the way up, unless the
                            # mezzanine above the neighbour is walkable (then the
                            # mezzanine level draws its own part).
                            nb2 = cell(L2, x + d[0], y + d[1]) if level == 1 else "#"
                            if level == 1 and is_walk(nb2) and not TYPES[nb2].get("open"):
                                add_run(runs, (1, t["wall"], base, FLOOR2, dname), x, y, d)
                            else:
                                add_run(runs, (level, t["wall"] if top <= CEIL2 + 0.1 else "marble", base, top, dname), x, y, d)
                        else:
                            add_run(runs, (level, t["wall"], base, top, dname), x, y, d)
                        continue
                    # Both walkable.
                    if tn.get("outside"):
                        continue
                    ntop = ceil_of(level, nb, x + d[0], y + d[1])
                    if tn.get("open") and not t.get("open"):
                        if level == 1:
                            add_run(runs, (1, "header", top, FLOOR2, "r" + dname), x, y, d)
                        else:
                            if not stair_top_edge(x, y, d):
                                add_run(runs, (2, "balustrade", base, base + 1.05, dname), x, y, d)
                            add_run(runs, (2, "upper", top, ntop, "r" + dname), x, y, d)
                    elif ntop > top + 0.01 and not t.get("open"):
                        add_run(runs, (level, "upper" if level == 2 and ntop > CEIL2 + 0.1 else "header", top, ntop, "r" + dname), x, y, d)
    # Void cells of the mezzanine against solid mezzanine walls: the atrium's upper walls.
    for j in range(NY):
        for i in range(NX):
            if L2[j, i] not in "AS":
                continue
            x, y = XMIN + i, YMIN + j
            top = ATRIUM_TOP if L1[j, i] == "A" else CEIL2
            for d, dname in DIRS:
                nb2 = cell(L2, x + d[0], y + d[1])
                nb1 = cell(L1, x + d[0], y + d[1])
                if is_walk(nb2):
                    continue
                if not is_walk(nb1):
                    continue  # the ground storey's wall already goes up to the top
                add_run(runs, (2, "upper" if top > CEIL2 + 0.1 else "damask", FLOOR2, top, dname), x, y, d)
    return runs


def add_run(runs, key, x, y, d):
    a, b, n = edge_geom(x, y, d)
    runs.setdefault(key, []).append((x, y, d))


def emit_runs(runs):
    walls = 0
    for key, cells in runs.items():
        level, style, z0, z1, dname = key
        rev = dname.startswith("r")
        dn = dname[1:] if rev else dname
        d = {"x+": (1, 0), "x-": (-1, 0), "y+": (0, 1), "y-": (0, -1)}[dn]
        # group by line, merge consecutive cells
        lines = {}
        for x, y, _d in cells:
            if d[0] != 0:
                lines.setdefault(x, []).append(y)
            else:
                lines.setdefault(y, []).append(x)
        for line, along in lines.items():
            along = sorted(set(along))
            start = prev = along[0]
            segs = []
            for v in along[1:]:
                if v == prev + 1:
                    prev = v
                    continue
                segs.append((start, prev))
                start = prev = v
            segs.append((start, prev))
            for s0, s1 in segs:
                if d[0] != 0:
                    xa, ya = line, s0
                    xb, yb = line, s1
                else:
                    xa, ya = s0, line
                    xb, yb = s1, line
                a0, b0, n = edge_geom(xa, ya, d)
                a1, b1, _ = edge_geom(xb, yb, d)
                pts = [a0, b0, a1, b1]
                t = np.cross([0, 0, 1.0], n)[:2]
                proj = [float(np.dot(p, t)) for p in pts]
                a = pts[int(np.argmin(proj))]
                b = pts[int(np.argmax(proj))]
                if rev:
                    # Header seen from the taller neighbour: flip to face it.
                    n = -n
                    a, b = b, a
                base = 0.0 if level == 1 else FLOOR2
                if style == "glasswall":
                    glass_wall(a, b, n, z0, z1)
                elif style == "balustrade":
                    balustrade(a, b, n, z0)
                else:
                    wall_style(style, a, b, n[:2], z0, z1, base)
                walls += 1
    return walls


def glass_wall(a, b, n, z0, z1):
    """Shopfront-style glazing: bronze mullions every metre, a transom at 3 m."""
    a = np.asarray(a)
    b = np.asarray(b)
    mid_off = -n[:2] * 0.5  # in the middle of the solid cell
    a2, b2 = a + mid_off, b + mid_off
    k.quad((b2[0], b2[1], z0), (a2[0], a2[1], z0), (a2[0], a2[1], 3.2), (b2[0], b2[1], 3.2), "glass", (0.55, 0.6, 0.62))
    k.quad((a2[0], a2[1], z0), (b2[0], b2[1], z0), (b2[0], b2[1], 3.2), (a2[0], a2[1], 3.2), "glass", (0.55, 0.6, 0.62))
    wall_quad(a, b, 3.2, z1, "marble", None)
    L = np.linalg.norm(b2 - a2)
    tvec = (b2 - a2) / L
    for s in np.arange(0, L + 0.01, 1.0):
        p = a2 + tvec * s
        k.box((p[0], p[1], 1.6), (0.07, 0.07, 3.2), "brass", (0.3, 0.25, 0.2))
    trim(a2 - n[:2] * 0.04, b2 - n[:2] * 0.04, n[:2], 3.1, 0.12, 0.08, "brass", (0.3, 0.25, 0.2))


def balustrade(a, b, n, z0):
    """Gallery edge: marble plinth, glass panels, a brass handrail (chest high, you shoot over it)."""
    a = np.asarray(a)
    b = np.asarray(b)
    off = -n[:2] * 0.08
    a2, b2 = a + off, b + off
    L = np.linalg.norm(b2 - a2)
    c = (a2 + b2) / 2
    yaw = math.degrees(math.atan2(b2[1] - a2[1], b2[0] - a2[0]))
    k.box((c[0], c[1], z0 + 0.06), (L, 0.16, 0.12), "marble_dark", None, yaw=yaw)
    k.quad((a2[0], a2[1], z0 + 0.12), (b2[0], b2[1], z0 + 0.12), (b2[0], b2[1], z0 + 0.98), (a2[0], a2[1], z0 + 0.98), "glass", (0.6, 0.62, 0.6))
    k.quad((b2[0], b2[1], z0 + 0.12), (a2[0], a2[1], z0 + 0.12), (a2[0], a2[1], z0 + 0.98), (b2[0], b2[1], z0 + 0.98), "glass", (0.6, 0.62, 0.6))
    k.cyl((a2[0], a2[1], z0 + 1.03), (b2[0], b2[1], z0 + 1.03), 0.035, "brass", None, sides=8)
    k.colliders.append({"c": [float(c[0]), float(c[1]), z0 + 0.55], "s": [float(L) if abs(n[1]) > 0.5 else 0.16, 0.16 if abs(n[1]) > 0.5 else float(L), 1.1],
                        "yaw": 0.0, "surface": "glass"})


def greedy_rects(mask):
    """Cover a boolean grid with rectangles (rows then columns)."""
    m = mask.copy()
    out = []
    H, W = m.shape
    for j in range(H):
        i = 0
        while i < W:
            if not m[j, i]:
                i += 1
                continue
            i1 = i
            while i1 < W and m[j, i1]:
                i1 += 1
            j1 = j + 1
            while j1 < H and m[j1, i:i1].all():
                j1 += 1
            m[j:j1, i:i1] = False
            out.append((i, i1, j, j1))
            i = i1
    return out


def floors_and_ceilings():
    for level, L in ((1, L1), (2, L2)):
        z = 0.0 if level == 1 else FLOOR2
        keys = {}
        for j in range(NY):
            for i in range(NX):
                ch = L[j, i]
                if not is_walk(ch):
                    continue
                if level == 2 and ch in "AS":
                    continue
                if level == 1 and ch == "S":
                    keys.setdefault(("floor",) + TYPES[ch]["floor"], np.zeros((NY, NX), bool))[j, i] = True
                    continue
                keys.setdefault(("floor",) + TYPES[ch]["floor"], np.zeros((NY, NX), bool))[j, i] = True
                t = TYPES[ch]
                if not t.get("open") and not t.get("outside") and not t.get("noceil"):
                    keys.setdefault(("ceil", ch), np.zeros((NY, NX), bool))[j, i] = True
        for key, mask in keys.items():
            for i0, i1, j0, j1 in greedy_rects(mask):
                x0, x1, y0, y1 = XMIN + i0, XMIN + i1, YMIN + j0, YMIN + j1
                if key[0] == "floor":
                    mat, tint = key[1], key[2]
                    k.quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), mat, tint)
                else:
                    ch = key[1]
                    zc = ceil_of(level, ch)
                    mat, tint = TYPES[ch]["ceiling"]
                    k.quad((x0, y1, zc), (x1, y1, zc), (x1, y0, zc), (x0, y0, zc), mat, tint)
    # The back-stair shafts' own ceilings, at the mezzanine ceiling.
    for x0, x1, yb, yt, _m in STAIRS[2:]:
        y0, y1 = min(yb, yt) - 1, max(yb, yt)
        k.quad((x0, y1, CEIL2), (x1, y1, CEIL2), (x1, y0, CEIL2), (x0, y0, CEIL2), "plaster", (0.6, 0.57, 0.5))


def colliders():
    """Merged boxes for everything solid: walls, slabs, the roof."""
    stacks = {}
    for j in range(NY):
        for i in range(NX):
            c1, c2 = L1[j, i], L2[j, i]
            t1, t2 = TYPES[c1], TYPES[c2]
            st = []
            if not t1["walk"]:
                if t1.get("glass"):
                    st.append((0.0, 3.2, "glass"))
                    st.append((3.2, SOLID_TOP, "concrete"))
                elif t2["walk"] and not t2.get("open"):
                    st.append((0.0, FLOOR2, "wall"))
                else:
                    st.append((0.0, SOLID_TOP, "wall"))
            elif t1.get("outside"):
                pass
            elif not t1.get("open"):
                zc = ceil_of(1, c1)
                if t2["walk"] and not t2.get("open"):
                    st.append((zc, FLOOR2, "concrete"))
                elif not t2["walk"]:
                    st.append((zc, SOLID_TOP, "concrete"))
            if t1.get("open") and t2["walk"] and not t2.get("open"):
                st.append((FLOOR2 - 0.4, FLOOR2, "concrete"))
            if t2["walk"] and not t2.get("open") and not t2.get("noceil"):
                st.append((CEIL2, SOLID_TOP, "concrete"))
            if t1.get("open") and c1 == "A":
                st.append((ATRIUM_TOP, ATRIUM_TOP + 0.5, "concrete"))
            if st:
                stacks.setdefault(tuple(st), np.zeros((NY, NX), bool))[j, i] = True
    n = 0
    for st, mask in stacks.items():
        for i0, i1, j0, j1 in greedy_rects(mask):
            x0, x1, y0, y1 = XMIN + i0, XMIN + i1, YMIN + j0, YMIN + j1
            for z0, z1, surf in st:
                if surf == "wall":
                    # Partitions a metre thick or less are drywall: big rounds go through.
                    surf = "drywall" if min(x1 - x0, y1 - y0) <= 1 and is_interior(x0, x1, y0, y1) else "concrete"
                k.colliders.append({"c": [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], "s": [x1 - x0, y1 - y0, z1 - z0],
                                    "yaw": 0.0, "surface": surf})
                n += 1
    # The ground under everything.
    k.colliders.append({"c": [0.0, (YMIN + YMAX) / 2, -0.5], "s": [NX + 4, NY + 4, 1.0], "yaw": 0.0, "surface": "concrete"})
    # Invisible walls round the street outside.
    for c, s in (((0, -27.6, 3), (64, 0.4, 8)), ((-30.4, -22, 3), (0.4, 12, 8)), ((30.4, -22, 3), (0.4, 12, 8))):
        k.colliders.append({"c": list(c), "s": list(s), "yaw": 0.0, "surface": "concrete", "clip": True})
    return n


def is_interior(x0, x1, y0, y1):
    """Walkable (not outside) on both sides of a thin wall."""
    for x, y in ((x0 - 1, y0), (x1, y0), (x0, y0 - 1), (x0, y1)):
        if TYPES[cell(L1, x, y)].get("outside"):
            return False
    return x0 > XMIN and x1 < XMAX and y0 > YMIN and y1 < YMAX - 1


# ====================================================================== stairs

def tri(p0, p1, p2, mat, tint=None):
    k.mesh(np.array([p0, p1, p2], np.float64), [[0, 1, 2]], np.eye(3), np.zeros(3), mat, tint, uv_origin=np.zeros(3))


def stairs():
    for x0, x1, yb, yt, mat in STAIRS:
        rise = FLOOR2
        run = abs(yt - yb)
        sgn = 1 if yt > yb else -1
        n = int(round(rise / 0.18))
        step_run = run / n
        w = x1 - x0
        xc = (x0 + x1) / 2
        for s in range(n):
            ya = yb + sgn * s * step_run
            yc = ya + sgn * step_run / 2
            z = (s + 1) * rise / n
            k.box((xc, yc, z / 2), (w, step_run, z), "marble" if mat == "marble" else "carpet", None if mat == "marble" else (0.45, 0.42, 0.42),
                  faces=["+z", "-y" if sgn > 0 else "+y"])
            if mat == "marble":
                # carpet runner and brass stair rods
                k.box((xc, yc, z + 0.004), (w * 0.62, step_run, 0.008), "carpet", None, faces=["+z"])
                k.cyl((xc - w * 0.31, ya + sgn * 0.02, z + 0.01), (xc + w * 0.31, ya + sgn * 0.02, z + 0.01), 0.01, "brass", None, sides=5)
        # Ramp collider (people walk up a slope; the steps are only drawn).
        ang = math.degrees(math.atan2(rise, run))
        L = math.hypot(rise, run)
        yc = (yb + yt) / 2
        thick = 0.3
        # Normal of the ramp surface, to sink the box by half its thickness.
        nrm = np.array([0.0, -sgn * math.sin(math.radians(ang)), math.cos(math.radians(ang))])
        c = np.array([xc, yc, rise / 2]) - nrm * thick / 2
        k.colliders.append({"c": [round(float(v), 3) for v in c], "s": [w, L, thick], "yaw": 0.0,
                            "rx": round(sgn * ang, 2), "surface": "concrete"})
        if mat == "marble":
            # The landing slab between the stair head and the south gallery.
            k.box((xc, (yt - 4) / 2, FLOOR2 - 0.2), (w, abs(yt + 4), 0.4), "marble_dark", None, faces=["-z", "+x", "-x", "+y"])
            # Open sides: marble stringers and brass rails; blocked underneath.
            for xs in (x0, x1):
                inner = xs == x0
                pts = []
                for s in range(n + 1):
                    pts.append((xs + (0.08 if inner else -0.08), yb + sgn * s * step_run, s * rise / n + 1.0))
                k.tube([(p[0], p[1], p[2]) for p in pts[::4]] + [pts[-1]], 0.035, "brass", None, sides=8)
                for s in range(0, n + 1, 3):
                    p = pts[s]
                    k.cyl((p[0], p[1], p[2] - 1.0), (p[0], p[1], p[2]), 0.018, "brass", None, sides=6)
                ya_, yb_ = yb, yt
                tri((xs, ya_, 0.0), (xs, yb_, 0.0), (xs, yb_, rise), "marble_dark")
                tri((xs, yb_, rise), (xs, yb_, 0.0), (xs, ya_, 0.0), "marble_dark")
                k.colliders.append({"c": [xs, yc, rise / 2 + 0.55], "s": [0.1, L, 1.2], "yaw": 0.0, "rx": round(sgn * ang, 2),
                                    "surface": "glass"})
        if True:
            # Under the high half: blocked (no hiding underneath).
            for s in range(3):
                f0, f1 = 0.3 + s * 0.23, 0.53 + s * 0.23
                ya = yb + sgn * run * f0
                yz = yb + sgn * run * f1
                h = rise * f0 - 0.3
                k.colliders.append({"c": [xc, (ya + yz) / 2, h / 2], "s": [w, abs(yz - ya), h], "yaw": 0.0, "surface": "concrete"})


# ====================================================================== furniture and fittings

def column(x, y, z0, z1, r=0.42):
    k.lathe(np.array((x, y, z0)), [(r + 0.12, 0.0), (r + 0.12, 0.18), (r + 0.04, 0.24), (r + 0.04, 0.3), (r, 0.34)], "brass", (0.45, 0.4, 0.33), sides=16)
    k.cyl((x, y, z0 + 0.34), (x, y, z1 - 0.42), r, "marble", None, sides=18, caps=False)
    k.lathe(np.array((x, y, z1 - 0.42)), [(r, 0.0), (r + 0.06, 0.1), (r + 0.06, 0.16), (r + 0.18, 0.3), (r + 0.18, 0.42)], "brass", None, sides=16)
    k.collider((x, y, (z0 + z1) / 2), (2 * r, 2 * r, z1 - z0), 0, "concrete")


def sofa(pos, yaw, length=2.2, tint=(0.42, 0.08, 0.08), col=True):
    R, w = frame(pos, yaw)
    k.box(w((0, 0, 0.22)), (length, 0.9, 0.3), "canvas", tint, yaw=yaw, chamfer=0.04)
    k.box(w((0, 0.0, 0.42)), (length - 0.3, 0.75, 0.14), "canvas", tuple(c * 1.1 for c in tint), yaw=yaw, chamfer=0.05)
    k.box(w((0, 0.36, 0.62)), (length, 0.2, 0.55), "canvas", tint, yaw=yaw, chamfer=0.06)
    for s in (-1, 1):
        k.box(w((s * (length / 2 - 0.1), 0, 0.5)), (0.2, 0.9, 0.36), "canvas", tint, yaw=yaw, chamfer=0.05)
        for f in (-1, 1):
            k.cyl(w((s * (length / 2 - 0.12), f * 0.35, 0.0)), w((s * (length / 2 - 0.12), f * 0.35, 0.07)), 0.03, "brass", None, sides=6)
    if col:
        k.collider(w((0, 0, 0.45)), (length, 0.9, 0.9), yaw, "wood")


def armchair(pos, yaw, tint=(0.42, 0.08, 0.08)):
    sofa(pos, yaw, 0.95, tint)


def coffee_table(pos, yaw, w_=1.3, d=0.7):
    R, w = frame(pos, yaw)
    k.box(w((0, 0, 0.42)), (w_, d, 0.05), "marble_dark", None, yaw=yaw, chamfer=0.01)
    k.box(w((0, 0, 0.36)), (w_ - 0.1, d - 0.1, 0.06), "brass", None, yaw=yaw)
    for ix in (-1, 1):
        for iy in (-1, 1):
            k.box(w((ix * (w_ / 2 - 0.08), iy * (d / 2 - 0.08), 0.18)), (0.04, 0.04, 0.36), "brass", None, yaw=yaw)
    k.collider(w((0, 0, 0.22)), (w_, d, 0.45), yaw, "wood")


def planter(pos, size=1.0, dead=True):
    x, y, z = pos
    k.lathe(np.array(pos), [(0.3 * size, 0), (0.42 * size, 0.2 * size), (0.46 * size, 0.6 * size), (0.4 * size, 0.85 * size),
                            (0.43 * size, 0.9 * size), (0.0, 0.86 * size)], "lacquer", (0.1, 0.16, 0.3), sides=14)
    k.cyl((x, y, z + 0.5 * size), (x, y, z + 0.52 * size), 0.462 * size, "brass", None, sides=14, caps=False)
    leaf = (0.32, 0.27, 0.12) if dead else (0.15, 0.3, 0.12)
    for i in range(9):
        a = i / 9 * 6.28 + rnd(-0.3, 0.3)
        reach = rnd(0.5, 0.9) * size
        mid = (x + math.cos(a) * reach * 0.4, y + math.sin(a) * reach * 0.4, z + (1.4 + rnd(0, 0.4)) * size)
        tip = (x + math.cos(a) * reach, y + math.sin(a) * reach, z + (1.0 + rnd(-0.3, 0.2)) * size)
        k.tube([(x, y, z + 0.8 * size), mid, tip], 0.035 * size, "canvas", leaf, sides=4)
    k.collider((x, y, z + 0.45 * size), (0.85 * size, 0.85 * size, 0.9 * size), 0, "wood")


def luggage_cart(pos, yaw):
    R, w = frame(pos, yaw)
    k.box(w((0, 0, 0.2)), (1.2, 0.65, 0.06), "carpet", None, yaw=yaw)
    for s in (-1, 1):
        k.cyl(w((s * 0.55, 0, 0.2)), w((s * 0.55, 0, 1.85)), 0.025, "brass", None, sides=8)
        k.cyl(w((s * 0.55, -0.3, 0.1)), w((s * 0.55, 0.3, 0.1)), 0.06, "plastic", (0.06, 0.06, 0.06), sides=8)
    k.tube([w((-0.55, 0, 1.85)), w((-0.45, 0, 2.0)), w((0.45, 0, 2.0)), w((0.55, 0, 1.85))], 0.025, "brass", None, sides=8)
    for i in range(int(rnd(1, 4))):
        sz = (rnd(0.5, 0.8), rnd(0.25, 0.35), rnd(0.4, 0.6))
        k.box(w((rnd(-0.3, 0.3), 0, 0.23 + sz[2] / 2 + i * 0.02)), sz, "plastic", (rnd(0.1, 0.5), rnd(0.08, 0.2), rnd(0.05, 0.15)), yaw=yaw + rnd(-15, 15), chamfer=0.03)
    k.collider(w((0, 0, 0.6)), (1.25, 0.7, 1.2), yaw, "thin_metal")


def chandelier(pos, r=1.6, tiers=3, energy=200.0, dyn=False):
    x, y, ztop = pos
    k.cyl((x, y, ztop), (x, y, ztop - 1.2), 0.02, "brass", (0.3, 0.26, 0.2), sides=5, caps=False)
    z = ztop - 1.2
    k.lathe(np.array((x, y, z - 0.1)), [(0.0, 0.0), (0.18, 0.02), (0.22, 0.1), (0.0, 0.14)], "brass", None, sides=10)
    for t in range(tiers):
        rr = r * (1.0 - t * 0.28)
        zt = z - 0.5 - t * 0.75
        k.lathe(np.array((x, y, zt)), [(rr, 0.0), (rr + 0.05, 0.04), (rr, 0.08), (rr - 0.05, 0.04)], "brass", None, sides=24)
        nd = int(10 + rr * 8)
        for i in range(nd):
            a = i / nd * math.tau
            px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
            ln = rnd(0.35, 0.6)
            k.cyl((px, py, zt), (px, py, zt - ln), 0.02, "emissive", (0.95, 0.85, 0.7), sides=4, emit=6.0, caps=False)
            k.cyl((px, py, zt + 0.05), (px, py, zt + 0.16), 0.022, "emissive", (1.0, 0.82, 0.55), sides=5, emit=14.0)
        for i in range(4):
            a = i / 4 * math.tau + 0.4
            k.cyl((x, y, zt + 0.7), (x + math.cos(a) * rr, y + math.sin(a) * rr, zt), 0.012, "brass", None, sides=4, caps=False)
    zl = z - 0.6 - (tiers - 1) * 0.4
    k.lathe(np.array((x, y, zl - 0.9)), [(0.0, 0.0), (0.25, 0.3), (0.3, 0.6), (0.2, 0.9), (0.0, 1.0)], "emissive", (1.0, 0.88, 0.7), sides=10, emit=9.0)
    light((x, y, zl - 0.2), WARM, energy, radius=r * 0.8, dyn=dyn, rng=22.0)


def downlight(x, y, z, energy=14.0, color=WARM, dyn=False):
    k.cyl((x, y, z + 0.004), (x, y, z - 0.01), 0.1, "emissive", (1.0, 0.85, 0.65), sides=10, emit=14.0)
    k.cyl((x, y, z + 0.001), (x, y, z - 0.004), 0.13, "brass", None, sides=10, caps=False)
    light((x, y, z - 0.25), color, energy, radius=0.08, dyn=dyn, rng=6.0)


def sconce(p, n, energy=6.0):
    p = np.asarray(p, np.float64)
    n = np.asarray(n, np.float64)
    k.box(tuple(p + n * 0.03), (0.12, 0.12, 0.2) if abs(n[0]) > 0.5 else (0.12, 0.12, 0.2), "brass", None)
    k.lathe(p + n * 0.14, [(0.05, -0.12), (0.11, 0.0), (0.09, 0.14), (0.0, 0.16)], "lantern", (0.95, 0.75, 0.5), sides=10, emit=6.0)
    light(tuple(p + n * 0.25 + np.array([0, 0, 0.05])), GOLDLIGHT, energy, radius=0.1, rng=5.0)


def banner(x, y, ztop, length, yaw, han_tint=(0.6, 0.06, 0.05)):
    R, w = frame((x, y, ztop), yaw)
    a, b = w((-0.6, 0, 0)), w((0.6, 0, 0))
    a2, b2 = w((-0.6, 0, -length)), w((0.6, 0, -length))
    k.quad(a2, b2, b, a, "canvas", han_tint)
    k.quad(b2, a2, a, b, "canvas", han_tint)
    k.cyl(w((-0.75, 0, 0.02)), w((0.75, 0, 0.02)), 0.03, "brass", None, sides=6)
    for s in (-1, 1):
        k.box(w((s * 0.58, 0.0, -length / 2)), (0.05, 0.03, length), "brass", (0.5, 0.42, 0.3), yaw=yaw)
    k.tube([w((-0.6, 0, -length)), w((0, 0, -length - 0.3)), w((0.6, 0, -length))], 0.012, "brass", None, sides=4)


def fountain(cx, cy):
    """Octagonal marble basin with a three-tier brass and onyx centrepiece."""
    r_out, r_in = 3.4, 3.0
    oct8 = [(cx + r_out * math.cos(a), cy + r_out * math.sin(a)) for a in np.linspace(0, math.tau, 9)[:-1] + math.pi / 8]
    k.prism(oct8, 0.0, 0.55, "marble_dark", None, top=True)
    inner = [(cx + r_in * math.cos(a), cy + r_in * math.sin(a)) for a in np.linspace(0, math.tau, 9)[:-1] + math.pi / 8]
    k.prism(inner, 0.0, 0.57, "glass", (0.15, 0.28, 0.3), top=True, sides=False)  # still water
    for i in range(8):
        p0, p1 = oct8[i], oct8[(i + 1) % 8]
        k.box(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, 0.6), (math.dist(p0, p1) + 0.05, 0.42, 0.1), "marble", None,
              yaw=math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])))
    k.lathe(np.array((cx, cy, 0.5)), [(0.7, 0.0), (0.55, 0.4), (0.35, 0.9), (1.6, 1.1), (1.7, 1.25), (0.3, 1.3), (0.25, 2.2),
                                       (1.0, 2.35), (1.05, 2.45), (0.2, 2.5), (0.16, 3.2), (0.5, 3.3), (0.0, 3.4)], "brass", None, sides=20)
    k.lathe(np.array((cx, cy, 1.85)), [(0.0, 0.0), (0.28, 0.0), (0.3, 0.4), (0.0, 0.4)], "onyx", None, sides=14, emit=3.0)
    k.lathe(np.array((cx, cy, 3.9)), [(0.0, 0.0), (0.22, 0.1), (0.12, 0.5), (0.0, 0.6)], "brass", None, sides=12)
    light((cx, cy, 2.6), (1.0, 0.65, 0.3), 30.0, radius=0.4, rng=6.0)
    for s in range(4):
        a = s * math.tau / 4 + math.pi / 4
        k.collider((cx + math.cos(a) * 2.3, cy + math.sin(a) * 2.3, 0.4), (2.9, 2.9, 0.8), math.degrees(a), "concrete")
    k.collider((cx, cy, 2.0), (1.0, 1.0, 4.0), 0, "steel_post")
    k.marker("audio", (cx, cy, 1.0), sound="fountain", volume=-8.0)


def reception():
    """Desk across the north of the atrium: back-lit onyx front, black marble top;
    a rosewood screen behind it carries the hotel's name."""
    y = 12.8
    x0, x1 = -6.0, 6.0
    k.box(((x0 + x1) / 2, y, 0.55), (x1 - x0, 0.9, 1.1), "onyx", None, emit=2.2)
    k.box(((x0 + x1) / 2, y, 1.13), (x1 - x0 + 0.2, 1.05, 0.06), "marble_dark", None)
    k.box(((x0 + x1) / 2, y + 0.9, 0.42), (x1 - x0, 0.8, 0.84), "rosewood", None)
    k.box(((x0 + x1) / 2, y, 0.05), (x1 - x0 + 0.1, 0.95, 0.1), "brass", (0.35, 0.3, 0.25))
    light(((x0 + x1) / 2, y - 0.8, 0.5), (1.0, 0.62, 0.25), 25.0, kind="AREA", radius=6.0, rng=5.0)
    k.collider(((x0 + x1) / 2, y + 0.4, 0.57), (x1 - x0 + 0.2, 1.8, 1.15), 0, "concrete")
    for xm in (-4.0, -1.0, 2.5):
        k.box((xm, y + 0.7, 1.35), (0.5, 0.04, 0.32), "plastic", (0.05, 0.05, 0.05))
        k.box((xm, y + 0.69, 1.35), (0.46, 0.01, 0.28), "emissive", (0.15, 0.2, 0.3), emit=1.5)
    k.lathe(np.array((0.6, y - 0.2, 1.16)), [(0.0, 0.0), (0.06, 0.0), (0.05, 0.05), (0.0, 0.07)], "brass", None, sides=10)
    # Screen wall behind (cover from the lift hall's line of sight).
    sx0, sx1, sy = -7.0, 7.0, 15.4
    k.box(((sx0 + sx1) / 2, sy, 1.6), (sx1 - sx0, 0.3, 3.2), "rosewood", None)
    k.box(((sx0 + sx1) / 2, sy, 3.25), (sx1 - sx0 + 0.2, 0.36, 0.12), "brass", None)
    k.sign((0.0, sy - 0.16, 2.3), 6.0, 1.03, 0.0, "hotel_atlas", "logo", emit=1.6, depth=0.04, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((0.0, sy + 0.16, 2.3), 2.4, 2.4, 180.0, "hotel_atlas", "roundel", depth=0.04, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.collider(((sx0 + sx1) / 2, sy, 1.6), (sx1 - sx0, 0.3, 3.2), 0, "wood")
    light((0.0, sy - 1.5, 3.6), WARM, 20.0, kind="SPOT", spot=70, direction=(0, 0.5, -1), rng=8.0)
    k.sign((-17.0, 19.97, 2.6), 3.0, 0.56, 0.0, "hotel_atlas", "reception", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))


def lounge_cluster(cx, cy, yaw, tint):
    R, w = frame((cx, cy, 0), yaw)
    k.quad(w((-2.2, -1.8, 0.004)), w((2.2, -1.8, 0.004)), w((2.2, 1.8, 0.004)), w((-2.2, 1.8, 0.004)), "carpet", (0.36, 0.42, 0.42))
    sofa(w((0, 1.1, 0)), yaw + 180, 2.4, tint)
    armchair(w((-1.6, -0.2, 0)), yaw + 90 + rnd(-10, 10), tint)
    armchair(w((1.6, -0.2, 0)), yaw - 90 + rnd(-30, 10), tint)
    coffee_table(w((0, 0, 0)), yaw)


def toppled_sofa(pos, yaw, tint):
    """A sofa pushed over on its back: chest-high cover."""
    R = rot_z(yaw) @ rot_x(80)
    p = np.asarray(pos)
    k.box(tuple(p + rot_z(yaw) @ np.array([0, 0, 0.45])), (2.2, 0.9, 0.85), "canvas", tint, R=R, chamfer=0.05)
    k.collider(tuple(p + np.array([0, 0, 0.5])), (2.2, 0.9, 1.0), yaw, "wood")


def sandbags(x0, y0, x1, y1, rows=3):
    L = math.hypot(x1 - x0, y1 - y0)
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    n = max(int(L / 0.55), 1)
    for r in range(rows):
        for i in range(n):
            f = (i + 0.5 + (0.5 if r % 2 else 0.0)) / n
            if f > 1.0:
                continue
            p = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, 0.13 + r * 0.22)
            k.box(p, (0.56, 0.36, 0.22), "canvas", (0.36, 0.33, 0.25), yaw=yaw + rnd(-6, 6), chamfer=0.07)
    k.collider(((x0 + x1) / 2, (y0 + y1) / 2, rows * 0.11), (L, 0.4, rows * 0.22), yaw, "sandbag")


def crates(x, y, yaw, n=3):
    R, w = frame((x, y, 0), yaw)
    for i in range(n):
        sz = (0.6, 0.45, 0.4)
        z = 0.2 + (0.4 if i >= 2 else 0)
        k.box(w((0.32 * (i % 2) - 0.16, 0, z)), sz, "cardboard", None, yaw=yaw + rnd(-8, 8))
    k.collider(w((0, 0, 0.4)), (1.0, 0.5, 0.8), yaw, "cardboard")


def piano(x, y, yaw):
    R, w = frame((x, y, 0), yaw)
    body = [(-0.75, -0.7), (0.75, -0.7), (0.75, 0.2), (0.45, 0.9), (0.0, 1.15), (-0.4, 0.95), (-0.75, 0.5)]
    pts = [tuple(w((px, py, 0))[:2]) for px, py in body]
    k.prism(pts, 0.62, 1.0, "lacquer", (0.06, 0.06, 0.06), top=True, bottom=True)
    lid = [w((px, py, 1.02)) for px, py in body[:4]]
    k.quad(w((-0.75, -0.6, 1.02)), w((0.75, -0.6, 1.02)), w((0.6, 0.6, 1.9)), w((-0.6, 0.6, 1.9)), "lacquer", (0.06, 0.06, 0.06))
    k.box(w((0, -0.85, 0.78)), (1.5, 0.3, 0.12), "lacquer", (0.06, 0.06, 0.06), yaw=yaw)
    k.box(w((0, -0.85, 0.85)), (1.4, 0.2, 0.02), "plastic", (0.9, 0.9, 0.88), yaw=yaw)
    for lx, ly in ((-0.6, -0.55), (0.6, -0.55), (0.0, 0.85)):
        k.cyl(w((lx, ly, 0)), w((lx, ly, 0.62)), 0.06, "lacquer", (0.06, 0.06, 0.06), sides=8)
    k.collider(w((0, 0.2, 0.5)), (1.5, 1.8, 1.0), yaw, "wood")


def papers(cx, cy, n, spread):
    for i in range(n):
        x, y = cx + rnd(-spread, spread), cy + rnd(-spread, spread)
        a = rnd(0, 360)
        R = rot_z(a)
        s = 0.12
        pts = [np.array((x, y, 0.004)) + R @ np.array(v) for v in ((-s, -s * 1.4, 0), (s, -s * 1.4, 0), (s, s * 1.4, 0), (-s, s * 1.4, 0))]
        k.quad(*pts, "canvas", (0.62, 0.6, 0.55))


# ====================================================================== rooms

def atrium():
    # Inlaid floor: black marble border and a compass rose under the fountain.
    for (x0, y0, x1, y1) in ((-16, -4, 16, -3.6), (-16, 15.6, 16, 16), (-16, -4, -15.6, 16), (15.6, -4, 16, 16)):
        k.quad((x0, y0, 0.003), (x1, y0, 0.003), (x1, y1, 0.003), (x0, y1, 0.003), "marble_dark", None)
    for r in (5.2, 5.5):
        ring = [(math.cos(a) * r, 6 + math.sin(a) * r) for a in np.linspace(0, math.tau, 33)]
        for i in range(32):
            a0, a1 = ring[i], ring[i + 1]
            nrm = np.array([a1[1] - a0[1], -(a1[0] - a0[0])])
            nrm /= np.linalg.norm(nrm)
            w_ = 0.06
            k.quad((a0[0] - nrm[0] * w_, a0[1] - nrm[1] * w_, 0.004), (a0[0] + nrm[0] * w_, a0[1] + nrm[1] * w_, 0.004),
                   (a1[0] + nrm[0] * w_, a1[1] + nrm[1] * w_, 0.004), (a1[0] - nrm[0] * w_, a1[1] - nrm[1] * w_, 0.004), "brass", None)
    fountain(0.0, 6.0)
    reception()
    # Arcade columns along the atrium edge, both storeys.
    for x in range(-16, 17, 4):
        for y in (-4, 16):
            column(x, y, 0.0, 4.0)
            column(x, y, FLOOR2, CEIL2, 0.34)
    for y in range(12, 16, 4):  # the grand stairs run along the sides further south
        for x in (-16, 16):
            column(x, y, 0.0, 4.0)
            column(x, y, FLOOR2, CEIL2, 0.34)
    # Entrance-hall line: four big columns.
    for x in (-8, -3, 3, 8):
        column(x, -8.0, 0.0, 7.5, 0.55)
    # Chandeliers: one great one over the fountain, two smaller.
    chandelier((0.0, 6.0, ATRIUM_TOP), 2.4, 4, energy=380.0, dyn=True)
    chandelier((-9.0, 6.0, ATRIUM_TOP), 1.5, 3, energy=160.0)
    chandelier((9.0, 6.0, ATRIUM_TOP), 1.5, 3, energy=160.0)
    # Coffered ceiling: rosewood field, brass grid, warm coves round the edge.
    k.quad((-16, 16, ATRIUM_TOP - 0.002), (16, 16, ATRIUM_TOP - 0.002), (16, -4, ATRIUM_TOP - 0.002), (-16, -4, ATRIUM_TOP - 0.002), "rosewood", (0.55, 0.5, 0.5))
    for x in range(-16, 17, 4):
        k.box((x, 6.0, ATRIUM_TOP - 0.25), (0.25, 20.0, 0.5), "brass", (0.42, 0.36, 0.28))
    for y in range(-4, 17, 4):
        k.box((0.0, y, ATRIUM_TOP - 0.25), (32.0, 0.25, 0.5), "brass", (0.42, 0.36, 0.28))
    for x in range(-14, 15, 4):
        for y in range(-2, 15, 4):
            k.box((x, y, ATRIUM_TOP - 0.06), (2.6, 2.6, 0.04), "silk", (0.56, 0.46, 0.3))
    # Recessed spots in the coffers: a 15 m atrium needs light from the ceiling, not just the chandeliers.
    for x in range(-12, 13, 8):
        for y in (0, 12):
            k.cyl((x, y, ATRIUM_TOP - 0.03), (x, y, ATRIUM_TOP - 0.06), 0.16, "emissive", (1.0, 0.86, 0.66), sides=12, emit=14.0)
            light((x, y, ATRIUM_TOP - 0.3), WARM, 140.0, radius=0.15, kind="SPOT", spot=55, direction=(0, 0, -1), rng=20.0)
    # Red silk banners down the void.
    for x, y, yaw in ((-12.0, -3.5, 0), (12.0, -3.5, 0), (-12.0, 15.5, 0), (12.0, 15.5, 0)):
        banner(x, y, ATRIUM_TOP - 0.5, 7.0, yaw)
    # Uplights on the upper walls.
    for x in (-12, -4, 4, 12):
        light((x, -3.0, 9.0), GOLDLIGHT, 30.0, radius=0.3, rng=10.0)
        light((x, 15.0, 9.0), GOLDLIGHT, 30.0, radius=0.3, rng=10.0)
    for y in (2, 10):
        light((-15.0, y, 9.0), GOLDLIGHT, 30.0, radius=0.3, rng=10.0)
        light((15.0, y, 9.0), GOLDLIGHT, 30.0, radius=0.3, rng=10.0)
    # Lounges at the four corners; a grand piano; abandon and fortify.
    lounge_cluster(-10.0, 0.5, 0, (0.4, 0.07, 0.07))
    lounge_cluster(10.0, 0.5, 0, (0.08, 0.2, 0.18))
    lounge_cluster(-9.5, 11.0, 180, (0.08, 0.2, 0.18))
    piano(9.5, 10.5, 200)
    planter((-6.5, -2.5, 0), 1.2)
    planter((6.5, -2.5, 0), 1.2)
    planter((-14.5, 7.5, 0), 1.1)
    planter((14.5, 7.5, 0), 1.1)
    toppled_sofa((4.5, 1.0, 0), 25, (0.4, 0.07, 0.07))
    luggage_cart((-4.0, 1.5, 0), -30)
    luggage_cart((12.5, 4.5, 0), 80)
    sandbags(-3.0, 9.8, 3.0, 9.8)
    crates(-12.5, 6.0, 90)
    papers(0.0, 2.0, 18, 7.0)
    k.marker("audio", (0.0, 6.0, 8.0), sound="lobby_music", volume=-12.0)


def arcade_and_gallery():
    # Downlights round the arcade (ground) and the gallery (mezzanine).
    for z, energy in ((4.0, 9.0), (CEIL2, 8.0)):
        for x in range(-18, 19, 4):
            for y in (-6, 18):
                downlight(x, y, z, energy)
        for y in range(-2, 17, 4):
            for x in (-18, 18):
                downlight(x, y, z, energy)
    # Sconces on the arcade's outer walls.
    for x in (-14, -6, 6, 14):
        sconce((x, 19.98, 2.3), (0, -1, 0))
    for y in (2, 10, 14):
        sconce((-19.98, y, 2.3), (1, 0, 0))
        sconce((19.98, y, 2.3), (-1, 0, 0))
    # Gallery furniture: benches and planters, some cover for the stalker upstairs.
    for x in (-12, 0, 12):
        sofa((x, 19.0, FLOOR2), 180, 1.8, (0.42, 0.08, 0.08))
    planter((-19.0, -7.0, FLOOR2), 1.0)
    planter((19.0, -7.0, FLOOR2), 1.0)
    planter((-19.0, 19.0, FLOOR2), 1.0)
    planter((19.0, 19.0, FLOOR2), 1.0)
    for x in (-8, 8):
        crates(x, -7.2, 0, 2)
    luggage_cart((-18.0, 6.0, FLOOR2), 90)
    sandbags(17.2, 2.0, 17.2, 6.0, 2)
    # Gallery over the lift hall: a balcony toward the reception screen.
    for x in range(-12, 13, 4):
        downlight(x, 21.5, CEIL2, 8.0)
    k.sign((0.0, 22.97, 6.4), 3.6, 0.68, 0.0, "hotel_atlas", "level2", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    # Paintings on the gallery's outer walls.
    for x, rect in ((-6, "art_a"), (6, "art_b")):
        k.sign((x, -7.97, 6.4), 3.0, 1.6 if rect == "art_a" else 1.75, 0.0 + 180.0, "hotel_atlas", rect, depth=0.04, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((-19.97, 3.0, 6.4), 2.2, 1.3, 90.0, "hotel_atlas", "art_b", depth=0.04, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((19.97, 3.0, 6.4), 2.2, 1.2, -90.0, "hotel_atlas", "art_a", depth=0.04, back_mat="brass", back_tint=(0.4, 0.33, 0.24))


def entrance():
    # Double-height hall: two big chandeliers, the welcome board, a concierge podium.
    chandelier((-5.0, -12.0, 7.5), 1.4, 2, energy=140.0)
    chandelier((5.0, -12.0, 7.5), 1.4, 2, energy=140.0)
    k.sign((-11.97, -12.0, 2.4), 1.2, 1.05, 90.0, "hotel_atlas", "welcome", depth=0.04, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((0.0, -8.05, 5.8), 7.0, 1.2, 0.0, "hotel_atlas", "logo", emit=1.2, depth=0.05, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.box((7.0, -11.0, 0.55), (1.4, 0.7, 1.1), "rosewood", None)
    k.box((7.0, -11.0, 1.12), (1.5, 0.8, 0.05), "marble_dark", None)
    k.collider((7.0, -11.0, 0.55), (1.5, 0.8, 1.1), 0, "wood")
    k.sign((7.0, -11.36, 0.75), 1.0, 0.31, 0.0, "hotel_atlas", "concierge", depth=0.0)
    for x in (-10.0, 10.0):
        planter((x, -15.0, 0), 1.3)
    luggage_cart((-6.0, -13.5, 0), 15)
    toppled_sofa((-2.0, -10.0, 0), -10, (0.08, 0.2, 0.18))
    sandbags(1.0, -14.0, 4.5, -13.0)
    papers(0.0, -12.0, 12, 5.0)
    light((0.0, -16.5, 3.5), WARM, 25.0, kind="AREA", radius=4.0, rng=6.0)
    # Vestibule: brass soffit downlights in each door opening.
    for x in (-6.5, 0.0, 6.5):
        downlight(x, -16.5, 4.0, 12.0)
    for x in (-10.0, -3.5, 3.5, 10.0):
        k.sign((x, -15.9, 3.6), 1.2, 0.25, 0.0 + 180.0, "hotel_atlas", "exit", emit=3.0, depth=0.03) if x in (-10.0, 10.0) else None


def outside():
    """The porte-cochère: a canopy over the drive, the hotel car left at the door."""
    k.quad((-30, -27, -0.001), (30, -27, -0.001), (30, -17, -0.001), (-30, -17, -0.001), "concrete", (0.32, 0.32, 0.33))
    # Canopy
    k.box((0.0, -21.5, 5.2), (26.0, 9.0, 0.5), "marble_dark", None)
    k.box((0.0, -21.5, 4.92), (25.6, 8.6, 0.06), "brass", (0.3, 0.25, 0.2))
    k.collider((0.0, -21.5, 5.2), (26.0, 9.0, 0.5), 0, "concrete")
    k.sign((0.0, -26.02, 5.2), 9.0, 0.47, 0.0, "hotel_atlas", "logo", emit=2.5, depth=0.0)
    for x in (-12.0, -4.0, 4.0, 12.0):
        column(x, -25.6, 0.0, 4.95, 0.35)
        for y in (-19.0, -24.0):
            downlight(x, y, 4.89, 12.0, (1.0, 0.8, 0.55))
    # The car: a long black sedan with its doors shut and the boot open.
    car(-4.0, -21.0, 0.0)
    # Planters and stone bollards: what the men coming in duck behind.
    for x in (-22.0, -17.0, 17.0, 22.0):
        k.box((x, -20.0, 0.45), (3.0, 1.2, 0.9), "stone", (0.42, 0.42, 0.4), col="concrete")
        for i in range(4):
            k.tube([(x - 1.2 + i * 0.8, -20.0, 0.9), (x - 1.0 + i * 0.8, -20.2, 1.6)], 0.15, "canvas", (0.12, 0.22, 0.1), sides=5)
    for x in (-27.0, -14.0, 14.0, 27.0):
        k.lathe(np.array((x, -26.0, 0.0)), [(0.18, 0.0), (0.16, 0.9), (0.2, 0.95), (0.0, 1.0)], "stone", (0.45, 0.45, 0.42), sides=10)
        k.collider((x, -26.0, 0.5), (0.4, 0.4, 1.0), 0, "concrete")
    # Hedge wall at the street edge, street lamps beyond.
    k.box((0.0, -27.3, 0.6), (60.0, 0.6, 1.2), "canvas", (0.08, 0.14, 0.07), chamfer=0.1)
    for x in (-24.0, 0.0, 24.0):
        k.cyl((x, -29.0, 0.0), (x, -29.0, 6.0), 0.08, "paint_metal", (0.1, 0.1, 0.1), sides=8)
        k.cyl((x, -29.0, 6.0), (x, -28.0, 6.2), 0.05, "paint_metal", (0.1, 0.1, 0.1), sides=6)
        k.lathe(np.array((x, -28.0, 6.05)), [(0.0, 0.0), (0.22, 0.05), (0.25, 0.15), (0.0, 0.2)], "emissive", (1.0, 0.6, 0.25), sides=10, emit=12.0)
        light((x, -27.8, 5.8), (1.0, 0.55, 0.22), 45.0, radius=0.2, rng=12.0)
    k.marker("audio", (0.0, -24.0, 2.0), sound="rain", volume=-14.0)


def car(x, y, z):
    tint = (0.04, 0.04, 0.045)
    k.box((x, y, z + 0.5), (5.6, 1.95, 0.7), "paint_metal", tint, chamfer=0.12)
    k.box((x - 0.2, y, z + 1.1), (3.0, 1.75, 0.55), "glass", (0.25, 0.26, 0.28), chamfer=0.1)
    k.box((x - 0.2, y, z + 1.4), (2.9, 1.7, 0.06), "paint_metal", tint)
    for dx in (-1.8, 1.8):
        for dy in (-0.95, 0.95):
            k.cyl((x + dx, y + dy - 0.1 * np.sign(dy), z + 0.36), (x + dx, y + dy + 0.1 * np.sign(dy), z + 0.36), 0.36, "plastic", (0.04, 0.04, 0.04), sides=14)
    for dy in (-0.6, 0.6):
        k.box((x + 2.81, y + dy, z + 0.62), (0.03, 0.3, 0.12), "emissive", (1.0, 0.95, 0.85), emit=4.0)
        k.box((x - 2.81, y + dy, z + 0.66), (0.03, 0.35, 0.1), "emissive", (0.9, 0.05, 0.03), emit=4.0)
    k.box((x + 2.82, y, z + 0.55), (0.04, 0.6, 0.25), "brass", (0.5, 0.5, 0.5))
    k.collider((x, y, z + 0.75), (5.6, 1.95, 1.5), 0, "sheet_metal")
    light((x + 4.5, y, z + 0.6), (1.0, 0.95, 0.85), 18.0, kind="SPOT", spot=60, direction=(1, 0, -0.15), rng=12.0)


def lift_hall():
    for i, cx in enumerate(LIFTS_X):
        # Portal: black marble jambs and header, indicator, call plate between doors.
        for s in (-1, 1):
            k.box((cx + s * 1.12, 25.9, 1.4), (0.24, 0.2, 2.8), "marble_dark", None)
        k.box((cx, 25.9, 2.75), (2.48, 0.2, 0.3), "brass", (0.45, 0.38, 0.3))
        k.sign((cx, 25.8, 3.25), 0.5, 0.31, 0.0, "hotel_atlas", "ind_l" if i % 2 == 0 else "ind_9", emit=4.0, depth=0.02)
        k.sign((cx + 0.45, 25.8, 3.25), 0.3, 0.19, 0.0, "hotel_atlas", "ind_down", emit=3.0, depth=0.0)
        if i < len(LIFTS_X) - 1:
            k.sign((cx + 2.0, 25.97, 1.2), 0.22, 0.33, 0.0, "hotel_atlas", "callplate", emit=1.5, depth=0.02)
        # The car: brass and mirror (walls from the generator), a light panel.
        k.box((cx, 27.5, 2.58), (1.6, 2.4, 0.03), "emissive", (1.0, 0.88, 0.7), emit=6.0)
        light((cx, 27.5, 2.2), WARM, 14.0, radius=0.5, kind="AREA", rng=4.0)
        k.box((cx + 0.97, 26.4, 1.2), (0.04, 0.14, 0.3), "brass", None)
        k.marker("lift", (cx, 26.0, 0.0), width=2.0, height=2.6, car=[cx, 27.5, 0.0], index=i)
        k.marker("spawn", (cx - 0.5, 28.4, 0.0), name="lift_%d_a" % i, lift=i)
        k.marker("spawn", (cx + 0.5, 26.9, 0.0), name="lift_%d_b" % i, lift=i)
    k.sign((-13.97, 23.0, 2.6), 2.4, 0.45, 90.0, "hotel_atlas", "lifts", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((13.97, 23.0, 2.6), 2.4, 0.45, -90.0, "hotel_atlas", "lifts", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    for x in (-12, -8, -4, 0, 4, 8, 12):
        downlight(x, 24.5, 4.0, 9.0, dyn=x == 0)
    for x in (-12.0, 12.0):
        planter((x, 21.0, 0), 1.0)
    k.box((0.0, 22.0, 0.25), (3.0, 0.8, 0.5), "marble_dark", None, col="concrete")
    luggage_cart((-4.0, 21.5, 0.0), 10)


def wings():
    # Dragon Bar (west): counter along its west wall, back-lit shelves, booths.
    k.box((-29.6, 9.5, 0.55), (0.8, 9.0, 1.1), "rosewood", None)
    k.box((-29.6, 9.5, 1.12), (1.0, 9.2, 0.06), "marble_dark", None)
    k.collider((-29.6, 9.5, 0.56), (1.0, 9.2, 1.12), 0, "wood")
    k.box((-30.95, 9.5, 1.9), (0.08, 8.0, 1.6), "onyx", None, emit=2.0)
    for z in (1.4, 2.0, 2.6):
        k.box((-30.75, 9.5, z), (0.3, 8.0, 0.03), "glass", (0.7, 0.7, 0.7))
        for i in range(24):
            yb = 5.8 + i * 0.32 + rnd(-0.05, 0.05)
            k.cyl((-30.75, yb, z + 0.02), (-30.75, yb, z + rnd(0.24, 0.34)), 0.035, "glass", (rnd(0.2, 0.6), rnd(0.25, 0.5), rnd(0.1, 0.3)), sides=6)
    light((-30.0, 9.5, 2.2), (1.0, 0.6, 0.25), 25.0, kind="AREA", radius=6.0, rng=6.0)
    for yb in (5.0, 7.5, 10.0, 12.5):
        k.cyl((-28.6, yb, 0.0), (-28.6, yb, 0.75), 0.03, "brass", None, sides=6)
        k.cyl((-28.6, yb, 0.75), (-28.6, yb, 0.8), 0.2, "canvas", (0.4, 0.07, 0.07), sides=10)
    for x, y in ((-25.0, 5.5), (-25.0, 10.0), (-25.0, 14.5)):
        k.lathe(np.array((x, y, 0.0)), [(0.3, 0), (0.05, 0.05), (0.04, 0.72), (0.5, 0.74), (0.5, 0.78), (0.0, 0.78)], "lacquer", (0.25, 0.05, 0.04), sides=14)
        k.collider((x, y, 0.39), (0.9, 0.9, 0.78), 0, "wood")
        armchair((x - 0.9, y, 0.0), -90, (0.45, 0.32, 0.12))
        armchair((x + 0.9, y, 0.0), 90, (0.45, 0.32, 0.12))
    for x, y in ((-28.0, 4.0), (-24.0, 4.0), (-28.0, 15.0), (-24.0, 15.0)):
        downlight(x, y, 3.4, 8.0, (1.0, 0.6, 0.3))
    for y in (6.5, 9.5, 12.5):
        downlight(-29.6, y, 3.4, 9.0, (1.0, 0.6, 0.3))
    k.sign((-19.97, 6.0, 3.45), 2.0, 0.37, 90.0, "hotel_atlas", "bar", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.marker("audio", (-26.0, 10.0, 2.5), sound="bar_music", volume=-12.0)
    # Restrooms (east): vanity counter and mirrors.
    k.box((30.6, 6.0, 0.85), (0.6, 5.0, 0.12), "marble_dark", None)
    k.collider((30.6, 6.0, 0.45), (0.6, 5.0, 0.9), 0, "concrete")
    k.quad((30.98, 8.4, 1.1), (30.98, 3.6, 1.1), (30.98, 3.6, 2.4), (30.98, 8.4, 2.4), "glass", (0.65, 0.62, 0.58))
    for y in (4.5, 6.0, 7.5):
        k.lathe(np.array((30.6, y, 0.91)), [(0.0, 0.0), (0.22, 0.0), (0.2, 0.06), (0.0, 0.04)], "plastic", (0.85, 0.85, 0.82), sides=12)
        downlight(30.0, y, 2.8, 7.0)
    k.sign((19.97, 6.0, 3.45), 2.0, 0.42, -90.0, "hotel_atlas", "toilets", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    # Security office: desks, monitors (still on), filing cabinets.
    for y in (12.0, 14.5):
        k.box((26.0, y, 0.38), (3.0, 0.8, 0.76), "darkwood", (0.4, 0.4, 0.4), col="wood")
        for i in range(3):
            k.box((25.0 + i, y + 0.2, 0.98), (0.55, 0.06, 0.4), "plastic", (0.05, 0.05, 0.05))
            k.box((25.0 + i, y + 0.16, 0.98), (0.5, 0.01, 0.34), "emissive", (0.2, 0.32, 0.25), emit=2.5)
    for y in (11.5, 13.0, 14.5):
        k.box((30.5, y, 0.7), (0.6, 0.9, 1.4), "paint_metal", (0.35, 0.36, 0.34), col="sheet_metal")
    # Offices by the entrance: concierge (west), luggage store (east).
    for x in (-22.0, 22.0):
        k.box((x, -9.6, 0.38), (1.6, 0.6, 0.76), "darkwood", (0.4, 0.4, 0.4), col="wood")
        crates(x + (-1.3 if x < 0 else 1.3), -10.4, 90, 2)
    # Corridor dressing: room-service trolleys, a fallen planter, sandbag stops at the corners.
    for x, y, yaw in ((-36.0, 6.0, 90), (36.0, 12.0, 90), (-20.0, -13.0, 0), (34.0, -1.0, 0)):
        trolley(x, y, yaw)
    sandbags(-36.8, 17.0, -35.2, 17.0, 3)
    sandbags(35.2, -1.0, 36.8, -1.0, 3)
    sandbags(-27.8, -6.0, -26.2, -6.0, 2)
    # Paintings and scrolls along the corridors.
    for p, yaw, rect, w, h in (((-36.97, 8.0, 1.8), 90, "art_a", 1.6, 0.85), ((36.97, 8.0, 1.8), -90, "art_b", 1.4, 0.8),
                               ((-27.97, -6.0, 1.8), 90, "scroll", 0.3, 1.35), ((27.97, -6.0, 1.8), -90, "scroll", 0.3, 1.35),
                               ((-19.0, -12.03, 1.8), 0, "art_b", 1.2, 0.7), ((19.0, -12.03, 1.8), 0, "art_a", 1.2, 0.65)):
        k.sign(p, w, h, yaw, "hotel_atlas", rect, depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((-36.97, -1.0, 2.4), 0.8, 0.25, 90.0, "hotel_atlas", "exit", emit=3.0, depth=0.03)
    k.sign((36.97, -1.0, 2.4), 0.8, 0.25, -90.0, "hotel_atlas", "exit", emit=3.0, depth=0.03)
    k.sign((-24.03, 28.0, 1.8), 1.6, 0.42, -90.0, "hotel_atlas", "staff", depth=0.02)
    k.sign((24.03, 28.0, 1.8), 1.6, 0.42, 90.0, "hotel_atlas", "staff", depth=0.02)
    # Mezzanine: tea lounge (west) and ballroom foyer (east).
    for x, y in ((-27.0, 7.0), (-24.0, 11.0), (-27.0, 14.0)):
        k.lathe(np.array((x, y, FLOOR2)), [(0.3, 0), (0.05, 0.05), (0.04, 0.72), (0.6, 0.74), (0.6, 0.78), (0.0, 0.78)], "lacquer", (0.25, 0.05, 0.04), sides=14)
        k.collider((x, y, FLOOR2 + 0.39), (1.1, 1.1, 0.78), 0, "wood")
        armchair((x, y - 1.0, FLOOR2), 0, (0.08, 0.2, 0.18))
        armchair((x, y + 1.0, FLOOR2), 180, (0.08, 0.2, 0.18))
    k.sign((-29.97, 10.0, FLOOR2 + 1.9), 0.3, 1.35, 90.0, "hotel_atlas", "scroll", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    k.sign((-19.97, 10.5, FLOOR2 + 2.6), 2.0, 0.37, 90.0, "hotel_atlas", "lounge", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    for x, y in ((-28.0, 5.5), (-23.0, 5.5), (-28.0, 15.0), (-23.0, 15.0)):
        downlight(x, y, CEIL2, 8.0, (1.0, 0.7, 0.4))
    chandelier((25.5, 10.0, CEIL2), 1.2, 2, energy=110.0)
    for y in (6.0, 14.0):
        downlight(25.5, y, CEIL2, 8.0)
    k.sign((29.97, 10.0, FLOOR2 + 2.0), 3.4, 0.64, -90.0, "hotel_atlas", "ballroom", depth=0.03, back_mat="brass", back_tint=(0.4, 0.33, 0.24))
    for y in (7.0, 10.0, 13.0):
        k.box((29.9, y, FLOOR2 + 1.3), (0.1, 1.6, 2.6), "lacquer", (0.4, 0.06, 0.05))
        k.box((29.85, y, FLOOR2 + 1.3), (0.02, 0.1, 0.4), "brass", None)
    for x, y in ((23.0, 6.0), (23.0, 14.0)):
        k.box((x, y, FLOOR2 + 0.38), (1.8, 0.8, 0.76), "canvas", (0.55, 0.52, 0.48), col="wood")
    crates(27.0, 6.0, 30, 3)
    sandbags(24.0, 12.0, 27.0, 12.5, 2)


def trolley(x, y, yaw):
    R, w = frame((x, y, 0), yaw)
    k.box(w((0, 0, 0.75)), (0.9, 0.55, 0.04), "canvas", (0.6, 0.58, 0.55), yaw=yaw)
    k.box(w((0, 0, 0.4)), (0.86, 0.5, 0.6), "canvas", (0.58, 0.56, 0.52), yaw=yaw)
    for ix in (-1, 1):
        for iy in (-1, 1):
            k.cyl(w((ix * 0.4, iy * 0.22, 0.0)), w((ix * 0.4, iy * 0.22, 0.75)), 0.015, "brass", None, sides=5)
    k.lathe(w((0.15, 0.0, 0.77)), [(0.0, 0.0), (0.2, 0.0), (0.2, 0.15), (0.12, 0.25), (0.0, 0.26)], "brass", None, sides=12)
    k.collider(w((0, 0, 0.4)), (0.95, 0.6, 0.8), yaw, "thin_metal")


def service():
    for x in range(-34, 35, 5):
        fluoro_light(x + 0.5, 31.0, 2.8)
    k.cyl((-36.0, 31.7, 2.55), (36.0, 31.7, 2.55), 0.08, "galv", None, sides=8)
    k.cyl((-36.0, 31.45, 2.6), (36.0, 31.45, 2.6), 0.05, "galv", (0.3, 0.45, 0.35), sides=6)
    for x, n in ((-30.0, 3), (-12.0, 2), (8.0, 3), (28.0, 2)):
        crates(x, 31.6, 0, n)
    for x in (-20.0, 16.0):
        k.box((x, 30.6, 0.55), (1.2, 0.7, 1.0), "canvas", (0.45, 0.45, 0.48), chamfer=0.05)
        k.box((x, 30.6, 0.06), (1.2, 0.7, 0.12), "galv", None)
        k.collider((x, 30.6, 0.55), (1.2, 0.7, 1.1), 0, "thin_metal")
    k.marker("audio", (0.0, 31.0, 2.0), sound="hum", volume=-14.0)


def fluoro_light(x, y, z, energy=22.0):
    k.box((x, y, z - 0.03), (1.26, 0.14, 0.05), "galv", None)
    k.cyl((x - 0.6, y, z - 0.075), (x + 0.6, y, z - 0.075), 0.016, "emissive", (0.85, 1.0, 0.92), sides=6, emit=9.0)
    light((x, y, z - 0.15), COOL, energy, kind="AREA", radius=1.2, rng=6.0)


def room_lights():
    """Downlights for every corridor rectangle, along its long axis."""
    for level, ch, x0, x1, y0, y1 in ROOMS:
        if ch not in "crk":
            continue
        z = (0.0 if level == 1 else FLOOR2) + TYPES[ch]["ceil"]
        w, h = x1 - x0, y1 - y0
        if w >= h:
            n = max(int(round(w / 4.0)), 1)
            for i in range(n):
                downlight(x0 + (i + 0.5) * w / n, (y0 + y1) / 2, z, 9.0 if ch == "c" else 7.0)
        else:
            n = max(int(round(h / 4.0)), 1)
            for i in range(n):
                downlight((x0 + x1) / 2, y0 + (i + 0.5) * h / n, z, 9.0 if ch == "c" else 7.0)


# ====================================================================== gameplay markers

def gameplay_markers():
    # In the entrance hall facing the atrium (Godot yaw 0 = north).
    k.marker("player_start", (0.0, -12.5, 0.0), yaw=0.0)
    # Outside: the far ends of the drive, behind the planters and the stone facade.
    for x, y, name in ((-27.0, -22.5, "drive_w1"), (-24.0, -18.5, "drive_w2"), (-28.5, -18.5, "drive_w3"),
                       (27.0, -22.5, "drive_e1"), (24.0, -18.5, "drive_e2"), (28.5, -18.5, "drive_e3")):
        k.marker("spawn", (x, y, 0.0), name=name)
    cams = {
        "CapAtrium": ((0.0, -6.5, 1.7), (0.0, 12.0, 3.0)),
        "CapGallery": ((-18.5, -6.5, FLOOR2 + 1.7), (8.0, 14.0, 1.5)),
        "CapLifts": ((0.0, 19.0, 1.7), (0.0, 27.0, 1.5)),
        "CapCorridor": ((-36.0, -1.0, 1.6), (-36.0, 16.0, 1.4)),
        "CapBar": ((-23.0, 3.5, 1.7), (-30.0, 12.0, 1.3)),
        "CapEntrance": ((0.0, 2.0, 1.7), (0.0, -20.0, 1.5)),
        "CapDrive": ((-20.0, -24.0, 1.7), (5.0, -16.0, 2.0)),
        "CapUp": ((0.0, 0.0, 1.0), (0.0, 6.0, 14.0)),
        "CapService": ((-34.0, 31.0, 1.6), (0.0, 31.0, 1.3)),
        "CapStair": ((-14.5, 11.5, 1.7), (-14.5, -4.0, 4.5)),
        "CapOverview": ((14.0, -6.0, 11.0), (-4.0, 12.0, 0.0)),
    }
    for name, (p, t) in cams.items():
        k.marker("camera", p, name=name, target=[float(x) for x in t])
    # Reflection probes (box-projected, rendered once): polished marble picks up the chandeliers.
    for c, sz in (((0.0, 6.0, 7.5), (32.0, 20.0, 15.0)), ((0.0, -6.0, 2.0), (40.0, 4.0, 4.0)), ((0.0, 18.0, 2.0), (40.0, 4.0, 4.0)),
                  ((-18.0, 6.0, 2.0), (4.0, 28.0, 4.0)), ((18.0, 6.0, 2.0), (4.0, 28.0, 4.0)), ((0.0, -12.0, 3.75), (24.0, 8.0, 7.5)),
                  ((0.0, 23.0, 2.0), (28.0, 6.0, 4.0)), ((0.0, 6.0, 6.3), (40.0, 28.0, 3.6))):
        k.marker("probe", c, s=list(sz))


# ====================================================================== export

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    layout_cells()
    runs = collect_edges()
    nw = emit_runs(runs)
    floors_and_ceilings()
    ncol = colliders()
    stairs()
    atrium()
    arcade_and_gallery()
    entrance()
    outside()
    lift_hall()
    wings()
    service()
    room_lights()
    gameplay_markers()
    print("walls:", nw, "cell colliders:", ncol, "kit:", k.stats(), flush=True)

    def group(attrs, centre, kit):
        emit = attrs[2]
        detail = attrs[4]
        ch = kit.chunk_of(centre)
        if emit > 0.5 and attrs[0] == kit.L("emissive"):
            return "c%02d_glow" % ch
        if attrs[0] == kit.L("glass"):
            return "c%02d_glass" % ch
        return "c%02d_%s" % (ch, "detail" if detail else "main")

    objs = k.build_objects("ht", group)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "layout.json"), "w") as f:
        json.dump({"bounds": [XMIN, YMIN, XMAX, YMAX], "floor2": FLOOR2, "colliders": k.colliders, "markers": k.markers,
                   "cells": {"l1": ["".join(r) for r in L1[::-1]], "l2": ["".join(r) for r in L2[::-1]], "origin": [XMIN, YMAX]}},
                  f, indent=0)
    if "--plan" in sys.argv:
        plan_png()
    blend = os.path.join(BUILD_DIR, "hotel.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("objects:", len(objs), "saved", blend)


def plan_png():
    """Top-down plan of both storeys for review (cells, colliders, markers)."""
    from PIL import Image, ImageDraw
    S = 12
    img = Image.new("RGB", (NX * S * 2 + 20, NY * S), (20, 20, 20))
    d = ImageDraw.Draw(img)
    colors = {"#": (40, 40, 40), "G": (90, 140, 160), "A": (230, 220, 200), "S": (200, 120, 60), "a": (200, 190, 170),
              "h": (215, 205, 185), "v": (120, 120, 120), "l": (180, 170, 150), "e": (220, 180, 80), "c": (150, 40, 40),
              "b": (110, 60, 40), "s": (90, 110, 95), "r": (160, 170, 180), "k": (120, 120, 140), "o": (70, 80, 90),
              "g": (170, 60, 60), "t": (60, 110, 100), "f": (120, 100, 150)}
    for off, L in ((0, L1), (NX * S + 20, L2)):
        for j in range(NY):
            for i in range(NX):
                y = (NY - 1 - j) * S
                d.rectangle([off + i * S, y, off + i * S + S - 1, y + S - 1], fill=colors[L[j, i]])
    for m in k.markers:
        if m["kind"] in ("spawn", "player_start"):
            x, y = m["p"][0], m["p"][1]
            px, py = (x - XMIN) * S, (YMAX - y) * S
            d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(0, 255, 0) if m["kind"] == "spawn" else (0, 120, 255))
    img.save(os.path.join(BUILD_DIR, "plan.png"))


if __name__ == "__main__":
    main()
