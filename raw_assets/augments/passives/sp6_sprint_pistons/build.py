"""SP-6 Calf Sprint Pistons (docs/design.md §3.6): gas pistons that kick on every stride.

Design: down the back of each calf, two gas pistons run side by side from a manifold block under the back of the
knee to a heel spur: gunmetal cylinders with cooling grooves, chrome rods, clevis ends. On the outer side of the
calf a gas reservoir (a pressure bottle in a clamp) feeds the manifold through a braided line; its exhaust block
has a row of ports with heat-tinted, sooty lips (it is loud and it runs hot). A red-orange firing light on the
manifold. Stencils: SP-6 and a pressure rating.

Pieces ride on shin.L/R (pistons, manifold, reservoir) and foot.L/R (heel spurs).

Run:
  tools/blender.sh raw_assets/augments/passives/sp6_sprint_pistons/build.py \\
      --out assets/augments/passives/sp6_sprint_pistons/sp6_sprint_pistons.gltf --preview docs/previews/sp6_sprint_pistons
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "sp6"
body = C.body_once()

GUN = C.mat_metal("sp6_gunmetal", base=(0.07, 0.072, 0.076), rough=0.32, wear=(0.5, 0.5, 0.52), brushed=0.06)
CHROME = C.mat_chrome("sp6_chrome")
STEEL = C.mat_metal("sp6_steel", base=(0.42, 0.42, 0.43), rough=0.24, wear=(0.65, 0.65, 0.66), brushed=0.1)
BOTTLE = hs.material("sp6_bottle", (0.17, 0.03, 0.018), 0.45, 0.0, wear=(0.5, 0.5, 0.5), wear_rough=0.3)
HOSE = hs.material("sp6_hose", (0.05, 0.05, 0.052), 0.45, 0.6, bump_scale=3500.0, bump_strength=0.6)
SOOT = hs.material("sp6_soot", (0.012, 0.011, 0.01), 0.85, 0.0)
GLOW = C.mat_glow("sp6_fire", color=(1.0, 0.28, 0.06), strength=4.0)
PAINT = C.mat_paint("sp6_stencil", (0.72, 0.7, 0.64))
MATS = [GUN, CHROME, STEEL, BOTTLE, HOSE, SOOT, GLOW, PAINT]
parts = {}


def put(bone, det, ob):
    hi, lo = parts.setdefault(bone, ([], []))
    (hi if det else lo).extend(ob if isinstance(ob, list) else [ob])


def surf(p, d):
    hit, _n = body.cast(p + d * 0.4, -d, ("suit",), 0.8)
    return hit if hit is not None else p + d * 0.05


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    kn, an = body.joint("shin." + side), body.joint("foot." + side)
    ax = (an - kn).normalized()
    L = (an - kn).length
    bk = V((0.0, 1.0, 0.0))
    bk = (bk - ax * bk.dot(ax)).normalized()
    sd = ax.cross(bk).normalized()
    t0, t1 = 0.12, 0.86
    base0, base1 = surf(kn + ax * L * t0, bk), surf(kn + ax * L * t1, bk)
    lift = max((surf(kn + ax * L * (t0 + (t1 - t0) * k / 10) + sd * w, bk) - base0.lerp(base1, k / 10)).dot(bk)
               for k in range(11) for w in (-0.025, 0.0, 0.025))
    b0, b1 = base0 + bk * (lift + 0.012), base1 + bk * (lift * 0.4 + 0.012)
    out_d = (sd * s if sd.x * s > 0 else -sd * s).normalized() if False else (sd if sd.x * s > 0 else -sd)
    for det in (True, False):
        # Manifold block under the back of the knee.
        put("shin." + side, det, C.prism("manifold", C.chamfer_rect(0.034, 0.016, 0.006), (b0 - bk * (lift + 0.012) - ax * 0.008, sd, -ax, bk),
                                         lift + 0.026, GUN, det, 0.0016))
        put("shin." + side, det, C.slab("fire", b0 + bk * 0.0142 - ax * 0.008 + sd * 0.0, (sd, ax, bk), (0.014, 0.003, 0.001), GLOW, False))
        for w in (-1, 1):
            p0 = b0 + sd * w * 0.014 + ax * 0.012
            p1 = b1 + sd * w * 0.014
            pm = p0.lerp(p1, 0.58)
            put("shin." + side, det, C.cyl("body", p0, pm, 0.0088, GUN, det, 24, 0.0012))
            put("shin." + side, det, C.cyl("gland", pm - ax * 0.002, pm + ax * 0.006, 0.0072, STEEL, det, 24, 0.0006))
            put("shin." + side, det, C.cyl("rod", pm, p1, 0.0042, CHROME, det, 16, 0.0003))
            put("shin." + side, det, C.slab("clevis", p1 + ax * 0.004, (ax, sd, bk), (0.012, 0.011, 0.012), STEEL, det, 0.0008))
            if det:
                for k in range(6):
                    c = p0.lerp(pm, 0.15 + 0.12 * k)
                    put("shin." + side, det, C.cyl("groove", c - ax * 0.0009, c + ax * 0.0009, 0.0093, GUN, True, 24, 0.0))
        # Heel spur on the foot.
        heel, _n = body.cast(an + bk * 0.4 + ax * 0.02, -bk, ("suit",), 0.6)
        heel = heel if heel is not None else an + bk * 0.04
        spur = heel + bk * 0.012 - ax * 0.0
        put("foot." + side, det, C.prism("spur", C.chamfer_rect(0.022, 0.01, 0.004), (heel - bk * 0.004, sd, -ax, bk), 0.018, STEEL, det, 0.0012))
        put("foot." + side, det, C.cyl("spur_pin", spur - sd * 0.024, spur + sd * 0.024, 0.0035, CHROME, det, 12, 0.0003))
        # Gas bottle on the outer calf with its exhaust block.
        oc = surf(kn + ax * L * 0.38, out_d)
        o0 = oc + out_d * 0.022 - ax * 0.05
        o1 = oc + out_d * 0.022 + ax * 0.04
        put("shin." + side, det, C.cyl("bottle", o0, o1, 0.016, BOTTLE, det, 28, 0.003))
        put("shin." + side, det, C.cyl("valve", o0 - ax * 0.012, o0 + ax * 0.002, 0.007, STEEL, det, 20, 0.0006))
        for f in (0.25, 0.75):
            c = o0.lerp(o1, f)
            put("shin." + side, det, C.cyl("strap", c - ax * 0.004, c + ax * 0.004, 0.0168, GUN, det, 28, 0.0005))
        ex = o1 + ax * 0.022
        put("shin." + side, det, C.slab("exhaust", ex, (ax, out_d.cross(ax).normalized(), out_d), (0.028, 0.026, 0.022), GUN, det, 0.0016))
        for k in range(4):
            pc = ex + out_d * 0.0112 + ax * (-0.009 + 0.006 * k)
            put("shin." + side, det, C.slab("port", pc, (ax, out_d.cross(ax).normalized(), out_d), (0.0028, 0.018, 0.0014), SOOT, False))
        put("shin." + side, det, C.cable("line", [o0 - ax * 0.012, o0 - ax * 0.03 + bk * 0.02, b0 + sd * s * 0.0 + out_d * 0.03 + bk * 0.004],
                                          0.0032, HOSE, det))
        if det:
            st = C.stencil("st", "SP-6", b0 + bk * 0.0142 - ax * 0.0 + ax * 0.008, bk, -ax, 0.0058, PAINT)
            st2 = C.stencil("st2", "30 MPa", o0.lerp(o1, 0.5) + out_d * 0.0162, out_d, -ax, 0.005, PAINT)
            put("shin." + side, det, [C.apply_all(st), C.apply_all(st2)])

for bone, (hi, lo) in parts.items():
    C.add_piece("sp6_" + bone, bone, C.join(hi, "sp6_%s_high" % bone), C.join(lo, "sp6_%s_low" % bone))

kn = body.joint("shin.L")
C.run("sp6_sprint_pistons", args, MATS, (
    ("back", (1.6, 3.8, 0.9), (0, 0, 0.75), 85),
    ("calf", kn + V((0.25, 0.55, -0.12)), kn + V((0.0, 0.05, -0.2)), 55),
    ("outer", kn + V((0.55, -0.15, -0.1)), kn + V((0.02, 0.0, -0.2)), 55)))
