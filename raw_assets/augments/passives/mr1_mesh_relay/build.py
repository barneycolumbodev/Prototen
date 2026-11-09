"""MR-1 Mesh Relay Lattice (docs/design.md §3.6): a filament lattice over the motor cortex.

Design: a fine geodesic lattice of raised filaments laid over the crown of the head, above the motor cortex
where the implant sits. Each node is a small relay stud with a teal light; the filaments are thin gunmetal
tracks that follow the skull. The forehead stays clear, and the lattice ends above the NL-3's antenna blades.
It's quiet hardware: low, fine and regular,
and it leaks a little light (the RF leak in its stats).

Pieces ride on the head bone.

Run:
  tools/blender.sh raw_assets/augments/passives/mr1_mesh_relay/build.py \\
      --out assets/augments/passives/mr1_mesh_relay/mr1_mesh_relay.gltf --preview docs/previews/mr1_mesh_relay
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V  # noqa: E402

args = C.args_parser()
C.TAG = "mr1"
body = C.body_once()

TRACK = C.mat_metal("mr1_track", base=(0.16, 0.165, 0.17), rough=0.26, wear=(0.55, 0.55, 0.57), brushed=0.08)
STUD = C.mat_metal("mr1_stud", base=(0.06, 0.062, 0.067), rough=0.3, wear=(0.45, 0.45, 0.47))
GLOW = C.mat_glow("mr1_glow", color=(0.36, 0.86, 0.78), strength=4.0)
MATS = [TRACK, STUD, GLOW]
import math  # noqa: E402

CEN = V((0.0, 0.012, 1.74))   # centre of the skull dome


def ray_dir(polar, az):
    """Direction from the dome centre: polar from straight up, azimuth from the back (+Y) toward +X."""
    p, a = math.radians(polar), math.radians(az)
    return V((math.sin(p) * math.sin(a), math.sin(p) * math.cos(a), math.cos(p)))


def on_dome(d):
    hit, n = body.cast(CEN + d * 0.4, -d, ("helmet",), 0.5)
    return hit, n


# Geodesic-ish lattice: a top node, a ring of 6, and a ring of 12 that leaves the forehead clear.
nodes = {("t", 0): ray_dir(0, 0)}
for k in range(6):
    nodes[("a", k)] = ray_dir(24, 30 + 60 * k)
for k in range(12):
    az = 15 + 30 * k
    if 120 < az < 240:          # the front (forehead): keep clear
        continue
    nodes[("b", k)] = ray_dir(44, az)
edges = [(("t", 0), ("a", k)) for k in range(6)]
edges += [(("a", k), ("a", (k + 1) % 6)) for k in range(6)]
for k in range(6):
    for j in (2 * k, (2 * k + 1) % 12):
        if ("b", j) in nodes:
            edges.append((("a", k), ("b", j)))
edges += [(("b", k), ("b", (k + 1) % 12)) for k in range(12) if ("b", k) in nodes and ("b", (k + 1) % 12) in nodes]
C.log(len(nodes), "nodes", len(edges), "edges")

hi_l, lo_l = [], []
for det, lst in ((True, hi_l), (False, lo_l)):
    for a, b in edges:
        da, db = nodes[a], nodes[b]
        pts = []
        for k in range(5):
            d = da.slerp(db, k / 4) if hasattr(da, "slerp") else da.lerp(db, k / 4).normalized()
            hit, n = on_dome(d)
            if hit is not None:
                pts.append(hit + n * 0.0015)
        for p0, p1 in zip(pts[:-1], pts[1:]):
            lst.append(C.cyl("track", p0, p1, 0.0011, TRACK, det, 6, 0.0))
    for d in nodes.values():
        p, n = on_dome(d)
        if p is None:
            continue
        lst.append(C.cyl("stud", p - n * 0.001, p + n * 0.003, 0.0032, STUD, det, 16, 0.0004))
        lst.append(C.cyl("node", p + n * 0.0028, p + n * 0.0034, 0.0016, GLOW, det, 12, 0.0))
C.add_piece("lattice", "head", C.join(hi_l, "mr1_high"), C.join(lo_l, "mr1_low"))

hd = V((0.0, 0.0, 1.86))
C.run("mr1_mesh_relay", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("top", hd + V((0.25, -0.3, 0.3)), hd + V((0.0, 0.0, -0.01)), 60),
    ("back", hd + V((-0.25, 0.4, 0.15)), hd + V((0.0, 0.02, -0.03)), 60)))
