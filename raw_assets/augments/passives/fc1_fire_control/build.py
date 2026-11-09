"""FC-1 Fire-Control Link (docs/design.md §3.6): palm contacts that talk to the gun.

Design: in each palm, a thin graft pad shaped to the grip with a grid of gold contact pads (the grip's
fire-control chip touches them) inside a teal light ring that shows the link is live. A shielded fibre runs from
the heel of the palm round the wrist to a slim link module on the inner wrist: a faceted housing with a small
readout window (a column of teal bars: the bore-alignment readout) and an FC-1 stencil. FC-1 needs a neural link
(connectivity 1); its light matches the NL-3 and the suit's seams.

Pieces ride on hand.L/R (pads, fibre) and forearm.L/R (modules).

Run:
  tools/blender.sh raw_assets/augments/passives/fc1_fire_control/build.py \\
      --out assets/augments/passives/fc1_fire_control/fc1_fire_control.gltf --preview docs/previews/fc1_fire_control
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "fc1"
body = C.body_once()

PAD = C.mat_metal("fc1_pad", base=(0.04, 0.042, 0.046), rough=0.45, wear=(0.3, 0.3, 0.32), brushed=0.02)
GOLD = hs.material("fc1_gold", (0.85, 0.62, 0.28), 0.22, 1.0)
HOUSING = C.mat_metal("fc1_housing", base=(0.07, 0.072, 0.077), rough=0.3, wear=(0.5, 0.5, 0.52), brushed=0.05)
GLOW = C.mat_glow("fc1_glow", color=(0.36, 0.86, 0.78), strength=4.0)
FIBRE = C.mat_rubber("fc1_fibre")
PAINT = C.mat_paint("fc1_stencil", (0.6, 0.6, 0.56))
MATS = [PAD, GOLD, HOUSING, GLOW, FIBRE, PAINT]
parts = {}


def put(bone, det, ob):
    hi, lo = parts.setdefault(bone, ([], []))
    (hi if det else lo).extend(ob if isinstance(ob, list) else [ob])


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    el, wr, fg = body.joint("forearm." + side), body.joint("hand." + side), body.joint("fingers." + side)
    h_ax = (fg - wr).normalized()
    out = V((s, 0.0, 0.25))
    palm = -(out - h_ax * out.dot(h_ax)).normalized()
    across = h_ax.cross(palm).normalized()
    # ---- palm pad (conformal) with contacts and the light ring
    pc = wr.lerp(fg, 0.5)
    outline = [(-0.026, -0.022), (0.02, -0.026), (0.03, -0.018), (0.03, 0.018), (0.02, 0.026), (-0.026, 0.022), (-0.032, 0.0)]
    hi, lo = C.plate("palm_" + side, body, outline, (pc - palm * 0.35, h_ax, across), -palm, 0.0012, 0.0022, facet_deg=8.0,
                     smooth_r=0.01, bevel=0.0007)
    C.setmat(hi, PAD)
    C.setmat(lo, PAD)
    put("hand." + side, True, hi)
    put("hand." + side, False, lo)
    cells = [(u * 0.0085, v * 0.0085) for u in (-1, 0, 1, 2) for v in (-1, 0, 1)]
    pts = C.surface_points(hi, -palm, cells, (pc - palm * 0.35, h_ax, across))
    C.log(side, "contacts", len(pts))
    hp = C.surface_points(hi, -palm, [(-0.019, 0.0)], (pc - palm * 0.35, h_ax, across))
    heel_pt = (hp[0][0] + hp[0][1] * 0.0015) if hp else pc - h_ax * 0.019 - palm * 0.0
    for det in (True, False):
        for loc, nrm in pts:
            put("hand." + side, det, C.slab("contact", loc + nrm * 0.0003, (h_ax, across, nrm), (0.0058, 0.0058, 0.0009), GOLD, det, 0.0004))
        # Light ring: four thin bars framing the contact grid.
        loc0 = sum((p for p, _n in pts), V()) / len(pts)
        n0 = sum((n for _p, n in pts), V()).normalized()
        for du, dv, lu, lv in ((0.0, -0.0145, 0.036, 0.0012), (0.0, 0.0145, 0.036, 0.0012), (-0.0175, 0.0, 0.0012, 0.03),
                               (0.0255, 0.0, 0.0012, 0.03)):
            c = loc0 + h_ax * du + across * dv + n0 * 0.0002
            put("hand." + side, det, C.slab("ring", c, (h_ax, across, n0), (lu, lv, 0.0008), GLOW, False))
    # ---- inner-wrist link module (forearm bone)
    a = (wr - el).normalized()
    inner = -(out - a * out.dot(a)).normalized()
    inner = (inner + V((0, -0.35, 0))).normalized()
    inner = (inner - a * inner.dot(a)).normalized()
    acr = a.cross(inner).normalized()
    hit, _n = body.cast(wr - a * 0.045 + inner * 0.3, -inner, ("suit",), 0.6)
    mc = hit if hit is not None else wr - a * 0.045 + inner * 0.04
    for det in (True, False):
        outline = [(-0.024, -0.011), (0.018, -0.013), (0.024, -0.008), (0.024, 0.008), (0.018, 0.013), (-0.024, 0.011)]
        put("forearm." + side, det, C.prism("module", outline, (mc - inner * 0.002, a, acr, inner), 0.0085, HOUSING, det, 0.0012, angle=30))
        put("forearm." + side, det, C.slab("window", mc + inner * 0.0066 + a * 0.005, (a, acr, inner), (0.026, 0.012, 0.0012), PAD, det, 0.0003))
        for k in range(5):
            put("forearm." + side, det, C.slab("bar", mc + inner * 0.0073 + a * (-0.004 + 0.0045 * k), (a, acr, inner),
                                               (0.0025, 0.004 + 0.0012 * ((k * 3) % 5), 0.0006), GLOW, False))
        # Fibre: module end -> round the wrist edge -> heel of the palm.
        heel = heel_pt
        p0 = mc + a * 0.024 + inner * 0.003
        mid = (p0 + heel) * 0.5 + inner * 0.012
        put("hand." + side, det, C.cable("fibre", [p0, mid, heel], 0.0016, FIBRE, det))
    if True:
        st = C.stencil("st_fc1", "FC-1", mc + inner * 0.0068 - a * 0.016, inner, acr * s, 0.0042, PAINT)
        put("forearm." + side, True, C.apply_all(st))

for bone, (hi, lo) in parts.items():
    C.add_piece("fc1_" + bone, bone, C.join(hi, "fc1_%s_high" % bone), C.join(lo, "fc1_%s_low" % bone))

hl = body.joint("hand.L")
C.run("fc1_fire_control", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("palm", hl + V((-0.32, -0.22, -0.02)), hl + V((0.03, -0.01, -0.04)), 70),
    ("wrist", hl + V((-0.2, -0.3, 0.12)), hl + V((-0.01, -0.01, 0.03)), 70)))
