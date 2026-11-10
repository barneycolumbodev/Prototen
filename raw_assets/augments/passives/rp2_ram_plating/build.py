"""RP-2 Reactive Ram Plating (docs/design.md §3.6): wedge plates for going through people.

Design: a ram, not a shield. Over each shoulder a thick faceted wedge with its point forward and out, crowned so
it reads as a solid slab; down the sternum a keeled prow plate. Each carries reactive tiles: rows of bolted
tiles that fire outward on contact (explosive reactive armour scaled down to a person), with yellow-black
chevrons on their faces and a red firing strip along the plate edge. Gunmetal, worn on the leading edges.
RP-2 shares the torso armour slot with CT-7, so it takes CT-7's place; the forearms are left to the arm parts.

Pieces ride on upper_arm.L/R (shoulder wedges) and chest (prow).

Run:
  tools/blender.sh raw_assets/augments/passives/rp2_ram_plating/build.py \\
      --out assets/augments/passives/rp2_ram_plating/rp2_ram_plating.gltf --preview docs/previews/rp2_ram_plating
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "rp2"
body = C.body_once()

PLATE = C.mat_metal("rp2_plate", base=(0.06, 0.062, 0.066), rough=0.4, wear=(0.5, 0.5, 0.52), brushed=0.03)
TILE = C.mat_metal("rp2_tile", base=(0.1, 0.103, 0.1), rough=0.45, wear=(0.5, 0.5, 0.5), brushed=0.02)
HAZ = hs.material("rp2_hazard", (0.8, 0.52, 0.02), 0.5, 0.0, wear=(0.25, 0.25, 0.25), wear_rough=0.6)
BLACK = hs.material("rp2_black", (0.015, 0.015, 0.016), 0.55, 0.0)
FIRE = C.mat_glow("rp2_strip", color=(1.0, 0.16, 0.05), strength=3.0)
STEEL = C.mat_metal("rp2_steel", base=(0.42, 0.42, 0.43), rough=0.24)
PAINT = C.mat_paint("rp2_stencil", (0.72, 0.7, 0.64))
MATS = [PLATE, TILE, HAZ, BLACK, FIRE, STEEL, PAINT]
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
parts = {}


def put(bone, det, ob):
    hi, lo = parts.setdefault(bone, ([], []))
    (hi if det else lo).extend(ob if isinstance(ob, list) else [ob])


def tiles(bone, plate_hi, frame, n_dir, cells, size, up):
    """Reactive tiles standing on the plate's outer face, with chevrons (HIGH) and bolts."""
    pts = C.surface_points(plate_hi, -n_dir, cells, frame)
    for loc, nrm in pts:
        u = (up - nrm * up.dot(nrm)).normalized()
        w = u.cross(nrm).normalized()
        for det in (True, False):
            put(bone, det, C.slab("tile", loc + nrm * size[2] * 0.5, (w, u, nrm), size, TILE, det, 0.0012))
            put(bone, det, C.slab("tile_face", loc + nrm * (size[2] + 0.0004), (w, u, nrm), (size[0] * 0.62, size[1] * 0.5, 0.0008), HAZ, False))
            if det:
                for k in (-1, 0, 1):
                    c = loc + nrm * (size[2] + 0.0009) + w * k * size[0] * 0.2
                    put(bone, det, C.prism("chev", [(-0.0026, -0.004), (0.0, -0.001), (0.0026, -0.004), (0.0026, -0.0015), (0.0, 0.0015),
                                                    (-0.0026, -0.0015)], (c, w, u, nrm), 0.0003, BLACK, False))
                for sx in (-1, 1):
                    bo = C.bolt("tb", loc + nrm * size[2] + w * sx * size[0] * 0.42 + u * size[1] * 0.3, nrm, r=0.0016, h=0.0012)
                    put(bone, det, C.setmat(C.apply_all(bo), STEEL))


# ---- shoulder wedges
for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    sh = body.joint("upper_arm." + side)
    out = V((s, -0.12, 0.38)).normalized()
    fwd = (-Y - out * (-Y).dot(out)).normalized()
    lat = fwd.cross(out).normalized()
    c = sh + V((s * 0.03, -0.0, 0.0))
    poly = [(-0.062, -0.052), (0.035, -0.066), (0.085, -0.012), (0.085, 0.012), (0.035, 0.066), (-0.062, 0.052), (-0.074, 0.0)]
    frame = (c + out * 0.35, fwd, lat)
    hi, lo = C.plate("wedge_" + side, body, poly, frame, -out, 0.008, 0.009, facet_deg=12.0, smooth_r=0.035, bevel=0.0025, crown=0.012)
    C.setmat(hi, PLATE)
    C.setmat(lo, PLATE)
    far = max((v.co - c).length for v in lo.data.vertices)
    C.log("wedge", side, "max reach", round(far, 3))
    assert far < 0.16, "wedge projection ran off the body"
    put("upper_arm." + side, True, hi)
    put("upper_arm." + side, False, lo)
    tiles("upper_arm." + side, hi, (c + out * 0.35, fwd, lat), out,
          [(-0.03, -0.024), (-0.03, 0.024), (0.008, -0.026), (0.008, 0.026)], (0.026, 0.03, 0.006), fwd)
    # Firing strip along the leading edge.
    pts = C.surface_points(hi, -out, [(0.062, -0.03), (0.062, 0.03)], (c + out * 0.35, fwd, lat))
    if len(pts) == 2:
        (pa, na), (pb, nb) = pts
        nn = (na + nb).normalized()
        for det in (True, False):
            put("upper_arm." + side, det, C.slab("strip", (pa + pb) * 0.5 + nn * 0.0006, ((pb - pa).normalized(), fwd, nn),
                                                ((pb - pa).length, 0.003, 0.0012), FIRE, False))

# ---- sternum prow
hit, _n = body.cast(V((0, -0.5, 1.38)), Y, ("suit",), 0.6)
pc = hit if hit is not None else V((0, -0.13, 1.38))
poly = [(0.0, -0.125), (0.062, -0.05), (0.068, 0.055), (0.03, 0.095), (-0.03, 0.095), (-0.068, 0.055), (-0.062, -0.05)]
frame = (V((0, -0.4, pc.z)), X, Z)
hi, lo = C.plate("prow", body, poly, frame, Y, 0.007, 0.01, facet_deg=10.0, smooth_r=0.03, bevel=0.0025, crown=0.02)
C.setmat(hi, PLATE)
C.setmat(lo, PLATE)
put("chest", True, hi)
put("chest", False, lo)
tiles("chest", hi, frame, -Y, [(x, z) for z in (0.052, 0.014, -0.024) for x in (-0.03, 0.03)], (0.028, 0.032, 0.0065), Z)
kp = C.surface_points(hi, Y, [(0.0, -0.07)], frame)
if kp:
    pa, na = kp[0]
    st = C.stencil("st", "RP-2", pa - Y * 0.0002, -Y, Z, 0.009, PAINT, target=hi)
    put("chest", True, C.apply_all(st))

for bone, (h, l) in parts.items():
    C.add_piece("rp2_" + bone.replace(".", "_"), bone, C.join(h, "rp2_%s_high" % bone), C.join(l, "rp2_%s_low" % bone))

sh = body.joint("upper_arm.L")
C.run("rp2_ram_plating", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("shoulder", sh + V((0.45, -0.55, 0.25)), sh + V((0.03, -0.02, 0.0)), 55),
    ("chest", (0.25, -0.75, 1.5), (0.0, -0.1, 1.38), 55)))
