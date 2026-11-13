"""The active parts' hardware on the operative's body (docs/design.md §3.4, 2026-11-10): what the loadout screen
and the drone's view of the operative show. The first-person models are separate (one build.py per part beside
this file); this is each part folded away, modelled on the operative's real surface with the passive-hardware
kit (raw_assets/augments/passives/_common.py: HIGH and LOW pieces per bone, baked to one 1024² set per part,
exported as B_<bone>__<part> meshes that BodyAppearance mounts on the bones).

  sd3_shrike_drone      three launch tubes in a cradle behind the left shoulder, hazard-banded lids, a feed cable
  ad2_arc_projector     the emitter head stowed nose-down behind the right shoulder on its mast and base block
  kr5_ram_thrusters     two thruster nacelles on the shoulder blades, a bell nozzle under each, a gas bottle between
  tc4_thermoptic_shroud hexagonal emitter studs across the chest, back, shoulders, arms and legs
  mw7_monofilament_whip the reel and its folded boom on the back of the right wrist
  nt5_mesh_arm          the braid sleeved over the left forearm between a driver collar and a slip ring
  bw6_fan_shield        the seven leaves folded in a stack along the outer left forearm on their hub
  sx8_urticating_setae  the setae bank on the back of the left forearm: 24 ceramic ports, gill plates, feed lines

Run (one part per run; they bake independently):
  tools/blender.sh raw_assets/augments/actives/body_hardware.py --part sd3_shrike_drone \\
      --out assets/augments/actives_body/sd3_shrike_drone/sd3_shrike_drone.gltf --preview docs/previews/sd3_shrike_drone_body
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "passives"))
if "--part" in sys.argv:
    i = sys.argv.index("--part")
    PART = sys.argv[i + 1]
    del sys.argv[i:i + 2]
else:
    PART = "sd3_shrike_drone"
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = PART[:3]
body = C.body_once()

GRAFT = C.mat_ceramic(PART + "_graft", base=(0.022, 0.023, 0.026))
METAL = C.mat_metal(PART + "_metal")
STEEL = C.mat_metal(PART + "_steel", base=(0.42, 0.43, 0.45), rough=0.26, wear=(0.7, 0.7, 0.72), brushed=0.12)
COPPER = hs.material(PART + "_copper", (0.86, 0.46, 0.26), 0.3, 1.0)
RUBBER = C.mat_rubber(PART + "_rubber")
GLOW = C.mat_glow(PART + "_glow")
OLIVE = C.mat_paint(PART + "_olive", (0.13, 0.15, 0.08), 0.6)
HAZARD = C.mat_paint(PART + "_hazard", (0.85, 0.62, 0.05), 0.5)
MATS = [GRAFT, METAL, STEEL, COPPER, RUBBER, GLOW, OLIVE, HAZARD]
Z = V((0, 0, 1))
X = V((1, 0, 0))
Y = V((0, 1, 0))


def both(build):
    """Runs `build(det, out)` for HIGH and LOW and returns the two joined objects."""
    hi, lo = [], []
    build(True, hi)
    build(False, lo)
    return C.join(hi, PART + "_hi"), C.join(lo, PART + "_lo")


def arm_frame(side, t):
    """A frame on the forearm of `side` ("L"/"R") at fraction t from elbow to wrist: (point on the surface of
    the back of the arm, along the arm, across it, outward normal)."""
    a, b = body.joint("forearm." + side), body.joint("hand." + side)
    d = (b - a).normalized()
    out = V((1.0 if side == "L" else -1.0, 0.0, 0.0))
    n = (out - d * out.dot(d)).normalized()
    p = a.lerp(b, t)
    hit, _n = body.cast(p + n * 0.25, -n, ("suit",), 0.5)
    return (hit if hit else p + n * 0.045), d, d.cross(n).normalized(), n


views = (("back", (0.9, 3.4, 1.9), (0.0, 0.0, 1.35), 85), ("front", (-1.0, -3.4, 1.7), (0.0, 0.0, 1.3), 85))

# ====================================================================== SD-3 drone pod
if PART == "sd3_shrike_drone":
    tilt = (Z + Y * 0.22).normalized()          # tubes lean back a little
    side = X
    back = side.cross(tilt).normalized() * -1.0  # away from the body
    base = V((0.125, 0.165, 1.36))

    def build(det, out):
        out.append(C.slab("cradle", base + tilt * 0.06 - back * 0.022, (side, tilt, back), (0.19, 0.14, 0.03), METAL, det, 0.004))
        for k in range(3):
            c = base + side * (k - 1) * 0.058
            out.append(C.cyl("tube", c, c + tilt * 0.235, 0.0265, OLIVE, det, 24, 0.0015))
            out.append(C.cyl("band", c + tilt * 0.205, c + tilt * 0.222, 0.0272, HAZARD, det, 24, 0.0))
            out.append(C.cyl("lid", c + tilt * 0.235, c + tilt * 0.243, 0.0275, GRAFT, det, 24, 0.0012))
            out.append(C.cyl("lid_light", c + tilt * 0.243 + back * 0.012, c + tilt * 0.2445 + back * 0.012, 0.005, GLOW, False, 10, 0.0))
            out.append(C.cyl("breech", c - tilt * 0.012, c, 0.0285, METAL, det, 24, 0.0012))
        out.append(C.slab("strap_hi", base + tilt * 0.17 + back * 0.004, (side, tilt, back), (0.2, 0.014, 0.062), GRAFT, det, 0.002))
        out.append(C.slab("strap_lo", base + tilt * 0.035 + back * 0.004, (side, tilt, back), (0.2, 0.014, 0.062), GRAFT, det, 0.002))
        out.append(C.slab("status", base + tilt * 0.1 + back * 0.0285, (side, tilt, back), (0.012, 0.05, 0.002), GLOW, False))
        if det:
            out.append(C.cable("feed", [base - tilt * 0.01 - side * 0.03, base - tilt * 0.06 - side * 0.07 - back * 0.02, V((0.02, 0.135, 1.27)), V((0.0, 0.125, 1.22))], 0.006, RUBBER, True))
        for k in (-1, 1):
            p = base + side * k * 0.08 + tilt * 0.1 - back * 0.03
            out.append(C.cyl("standoff", p, p - back * 0.03, 0.008, STEEL, det, 12, 0.0006))

    hi, lo = both(build)
    C.add_piece("pod", "chest", hi, lo)
    views = (("back", (1.2, 3.2, 2.2), (0.1, 0.1, 1.45), 85), ("close", (0.75, 1.1, 1.75), (0.12, 0.15, 1.47), 60))

# ====================================================================== AD-2 arc projector, stowed
elif PART == "ad2_arc_projector":
    hinge = V((-0.14, 0.14, 1.585))
    head_top = hinge + V((0.0, 0.055, -0.01))
    down = V((0.0, 0.1, -1.0)).normalized()

    def build(det, out):
        out.append(C.slab("block", hinge - Z * 0.03 - Y * 0.02, (X, Y, Z), (0.085, 0.07, 0.045), METAL, det, 0.004))
        out.append(C.slab("pad", hinge - Z * 0.055 - Y * 0.02, (X, Y, Z), (0.1, 0.085, 0.01), GRAFT, det, 0.002))
        out.append(C.cyl("pin", hinge - X * 0.045, hinge + X * 0.045, 0.011, STEEL, det, 16, 0.001))
        for s in (-1, 1):
            out.append(C.cyl("strut", hinge + X * s * 0.028, head_top + X * s * 0.03, 0.0065, METAL, det, 10, 0.0006))
        out.append(C.cyl("body", head_top, head_top + down * 0.11, 0.027, GRAFT, det, 24, 0.0012))
        out.append(C.cyl("tail", head_top - down * 0.012, head_top, 0.016, COPPER, det, 16, 0.001))
        if det:
            for k in range(8):
                p = head_top + down * (0.018 + k * 0.0095)
                out.append(C.cyl("fin", p, p + down * 0.0035, 0.033, METAL, True, 24, 0.0004))
        nose = head_top + down * 0.11
        out.append(C.cyl("nose", nose, nose + down * 0.014, 0.023, METAL, det, 20, 0.001))
        out.append(C.cyl("window", nose + down * 0.014, nose + down * 0.0155, 0.012, GLOW, False, 14, 0.0))
        u = down.cross(X).normalized()
        for k in range(3):
            a = math.radians(90 + k * 120)
            r = X * math.cos(a) + u * math.sin(a)
            out.append(C.cyl("prong", nose - down * 0.02 + r * 0.029, nose + down * 0.07 + r * 0.016, 0.004, STEEL, det, 8, 0.0, r2=0.0015))
            out.append(C.cyl("prong_root", nose - down * 0.035 + r * 0.03, nose - down * 0.015 + r * 0.03, 0.006, COPPER, det, 10, 0.0005))
        out.append(C.slab("status", hinge - Z * 0.03 + Y * 0.0155, (X, Z, Y), (0.03, 0.005, 0.002), GLOW, False))

    hi, lo = both(build)
    C.add_piece("turret", "chest", hi, lo)
    views = (("back", (-1.2, 3.2, 2.2), (-0.1, 0.1, 1.45), 85), ("close", (-0.75, 1.1, 1.75), (-0.13, 0.15, 1.5), 60))

# ====================================================================== KR-5 ram thrusters
elif PART == "kr5_ram_thrusters":
    def build(det, out):
        for s in (-1, 1):
            top = V((s * 0.085, 0.175, 1.5))
            axis = V((s * 0.12, 0.1, -1.0)).normalized()
            bot = top + axis * 0.2
            out.append(C.cyl("nacelle", top, bot, 0.04, GRAFT, det, 24, 0.002, r2=0.046))
            out.append(C.cyl("intake", top - axis * 0.012, top, 0.034, METAL, det, 20, 0.001))
            out.append(C.cyl("throat", bot, bot + axis * 0.02, 0.03, STEEL, det, 20, 0.001))
            out.append(C.cyl("bell", bot + axis * 0.02, bot + axis * 0.075, 0.03, STEEL, det, 24, 0.001, r2=0.052))
            out.append(C.cyl("glow", bot + axis * 0.068, bot + axis * 0.07, 0.044, GLOW, False, 20, 0.0))
            if det:
                for k in range(5):
                    p = top + axis * (0.03 + k * 0.03)
                    out.append(C.cyl("rib", p, p + axis * 0.006, 0.043 + k * 0.0016, METAL, True, 24, 0.0006))
            mid = top + axis * 0.1
            out.append(C.cyl("mount", mid - Y * 0.035, mid - Y * 0.062, 0.014, METAL, det, 12, 0.001))
            out.append(C.slab("seam", mid + Y * 0.0435 + axis * 0.0, (X, axis, Y), (0.003, 0.11, 0.002), GLOW, False))
        out.append(C.cyl("bottle", V((0.0, 0.165, 1.5)), V((0.0, 0.16, 1.36)), 0.028, OLIVE, det, 20, 0.004))
        out.append(C.cyl("bottle_band", V((0.0, 0.1645, 1.47)), V((0.0, 0.164, 1.455)), 0.0287, HAZARD, det, 20, 0.0))
        out.append(C.cyl("valve", V((0.0, 0.165, 1.5)), V((0.0, 0.166, 1.52)), 0.012, STEEL, det, 12, 0.001))
        out.append(C.cyl("manifold", V((-0.085, 0.17, 1.49)), V((0.085, 0.17, 1.49)), 0.009, STEEL, det, 10, 0.0006))

    hi, lo = both(build)
    C.add_piece("thrusters", "chest", hi, lo)
    views = (("back", (0.9, 3.2, 2.0), (0.0, 0.1, 1.4), 85), ("close", (0.6, 1.2, 1.55), (0.0, 0.15, 1.42), 60))

# ====================================================================== TC-4 thermoptic shroud
elif PART == "tc4_thermoptic_shroud":
    # (bone, point outside the body, direction to cast)
    SPOTS = []
    for sx in (-1, 1):
        SPOTS += [("chest", (sx * 0.085, -0.6, 1.47), (0, 1, 0)), ("chest", (sx * 0.06, -0.6, 1.33), (0, 1, 0)),
                  ("spine", (sx * 0.07, -0.6, 1.2), (0, 1, 0)), ("chest", (sx * 0.1, 0.6, 1.45), (0, -1, 0)),
                  ("chest", (sx * 0.06, 0.6, 1.3), (0, -1, 0)), ("spine", (sx * 0.07, 0.6, 1.17), (0, -1, 0)),
                  ("thigh." + ("L" if sx > 0 else "R"), (sx * 0.1, -0.6, 0.8), (0, 1, 0)),
                  ("thigh." + ("L" if sx > 0 else "R"), (sx * 0.5, 0.0, 0.72), (-sx, 0, 0)),
                  ("shin." + ("L" if sx > 0 else "R"), (sx * 0.11, -0.6, 0.38), (0, 1, 0)),
                  ("shin." + ("L" if sx > 0 else "R"), (sx * 0.5, 0.0, 0.3), (-sx, 0, 0))]
        side = "L" if sx > 0 else "R"
        a, b, c = body.joint("upper_arm." + side), body.joint("forearm." + side), body.joint("hand." + side)
        for bone, p0, p1, ts in (("upper_arm." + side, a, b, (0.35, 0.7)), ("forearm." + side, b, c, (0.3, 0.65))):
            d = (p1 - p0).normalized()
            for t in ts:
                for n0 in (V((sx, 0, 0)), V((0, -1, 0))):
                    n = (n0 - d * n0.dot(d)).normalized()
                    p = p0.lerp(p1, t)
                    SPOTS.append((bone, tuple(p + n * 0.3), tuple(-n)))
    by_bone = {}
    for bone, o, d in SPOTS:
        hit, n = body.cast(V(o), V(d), ("suit",), 1.0)
        if hit is None:
            continue
        by_bone.setdefault(bone, []).append((hit, n))
    hexagon = [(math.cos(math.radians(60 * k)) * 0.016, math.sin(math.radians(60 * k)) * 0.016) for k in range(6)]
    inner = [(x * 0.55, y * 0.55) for x, y in hexagon]
    for bone, pts in by_bone.items():
        def build(det, out, pts=pts):
            for hit, n in pts:
                fr = C.frame_at(hit - n * 0.001, n, Z if abs(n.z) < 0.9 else Y)
                out.append(C.prism("stud", hexagon, fr, 0.0055, METAL, det, 0.001))
                o, U, Vv, N = fr
                out.append(C.prism("lens", inner, (o + N * 0.0055, U, Vv, N), 0.0012, GLOW, False))
        hi, lo = both(build)
        C.add_piece("studs_" + bone.replace(".", "_"), bone, hi, lo)
    views = (("front", (0.9, -3.6, 1.5), (0.0, 0.0, 1.1), 85), ("back", (-0.9, 3.6, 1.5), (0.0, 0.0, 1.1), 85))

# ====================================================================== MW-7 whip reel
elif PART == "mw7_monofilament_whip":
    o, d, w, n = arm_frame("R", 0.78)

    def build(det, out):
        out.append(C.slab("saddle", o + n * 0.004, (d, w, n), (0.1, 0.06, 0.012), METAL, det, 0.002))
        c = o + n * 0.034
        out.append(C.cyl("drum", c - w * 0.024, c + w * 0.024, 0.021, COPPER, det, 24, 0.0006))
        for s in (-1, 1):
            out.append(C.cyl("flange", c + w * s * 0.024, c + w * s * 0.028, 0.026, METAL, det, 24, 0.0008))
            out.append(C.slab("cheek", c + w * s * 0.0315 - n * 0.006, (d, w, n), (0.066, 0.004, 0.05), GRAFT, det, 0.0012))
            out.append(C.cyl("cap", c + w * s * 0.0335, c + w * s * 0.0365, 0.009, STEEL, det, 12, 0.0008))
            out.append(C.cyl("ring", c + w * s * 0.0282, c + w * s * 0.0286, 0.0235, GLOW, False, 20, 0.0))
        b0 = o + d * 0.02 + n * 0.018
        out.append(C.slab("boom", b0 + d * 0.035, (d, w, n), (0.1, 0.012, 0.008), METAL, det, 0.0014))
        out.append(C.cyl("nozzle", b0 + d * 0.083, b0 + d * 0.104, 0.008, STEEL, det, 14, 0.0008))
        out.append(C.slab("boom_glow", b0 + d * 0.035 + n * 0.0046, (d, w, n), (0.07, 0.0016, 0.0012), GLOW, False))

    hi, lo = both(build)
    C.add_piece("reel", "forearm.R", hi, lo)
    views = (("side", (-1.3, -1.3, 1.25), (-0.47, 0.0, 1.08), 60), ("front", (-1.0, -3.4, 1.7), (0.0, 0.0, 1.3), 85))

# ====================================================================== NT-5 mesh arm
elif PART == "nt5_mesh_arm":
    a, b = body.joint("forearm.L"), body.joint("hand.L")
    d = (b - a).normalized()
    u = d.cross(Z).normalized()
    v = d.cross(u).normalized()
    L = (b - a).length
    R0, R1 = 0.055, 0.044

    def build(det, out):
        out.append(C.cyl("sleeve", a + d * 0.02, a + d * (L - 0.01), R0 - 0.006, RUBBER, det, 20, 0.0, r2=R1 - 0.006))
        out.append(C.cyl("driver", a + d * 0.0, a + d * 0.03, R0 + 0.004, METAL, det, 24, 0.0014))
        out.append(C.cyl("driver_glow", a + d * 0.03, a + d * 0.0315, R0 + 0.001, GLOW, False, 24, 0.0))
        out.append(C.cyl("slip", a + d * (L - 0.025), a + d * (L - 0.005), R1 + 0.002, METAL, det, 24, 0.0012))
        out.append(C.cyl("slip_glow", a + d * (L - 0.005), a + d * (L - 0.0035), R1 - 0.002, GLOW, False, 20, 0.0))
        if det:
            for k in range(12):
                turns = 1.6 if k % 2 == 0 else -1.6
                pts = []
                for i in range(19):
                    t = i / 18
                    ang = k * 2 * math.pi / 12 + turns * 2 * math.pi * t
                    r = (R0 + (R1 - R0) * t) - 0.002
                    pts.append(a + d * (0.032 + (L - 0.06) * t) + (u * math.cos(ang) + v * math.sin(ang)) * r)
                out.append(C.cable("strand", pts, 0.0075, GRAFT, True))
        else:
            out.append(C.cyl("braid", a + d * 0.032, a + d * (L - 0.028), R0 + 0.004, GRAFT, False, 20, 0.0, r2=R1 + 0.004))
        for k in range(3):
            ang = math.radians(k * 120 + 30)
            r = u * math.cos(ang) + v * math.sin(ang)
            out.append(C.slab("clamp", a + d * (L * 0.48) + r * ((R0 + R1) / 2 + 0.006), (d, d.cross(r).normalized(), r), (L * 0.55, 0.034, 0.005), GRAFT, det, 0.0012))
            out.append(C.slab("clamp_glow", a + d * (L * 0.48) + r * ((R0 + R1) / 2 + 0.009), (d, d.cross(r).normalized(), r), (L * 0.36, 0.0018, 0.0012), GLOW, False))

    hi, lo = both(build)
    C.add_piece("braid", "forearm.L", hi, lo)
    views = (("side", (1.3, -1.3, 1.25), (0.45, 0.0, 1.13), 60), ("front", (1.0, -3.4, 1.7), (0.0, 0.0, 1.3), 85))

# ====================================================================== BW-6 fan shield, folded
elif PART == "bw6_fan_shield":
    o, d, w, n = arm_frame("L", 0.45)

    def build(det, out):
        hub = o + n * 0.02
        out.append(C.slab("mount", o + n * 0.008, (d, w, n), (0.11, 0.05, 0.016), METAL, det, 0.003))
        out.append(C.cyl("hub", hub, hub + n * 0.05, 0.034, METAL, det, 28, 0.0016))
        out.append(C.cyl("hub_cap", hub + n * 0.05, hub + n * 0.056, 0.026, GRAFT, det, 28, 0.001))
        out.append(C.cyl("hub_ring", hub + n * 0.056, hub + n * 0.0575, 0.031, GLOW, False, 24, 0.0))
        # The folded leaves: a stack of blades pointing past the hand.
        count = 7 if det else 1
        for k in range(count):
            thick = 0.004 if det else 0.004 * 7 + 0.0008 * 6
            lift = 0.012 + k * 0.0048 if det else 0.012 + 0.0145
            pts = [(0.03, -0.022), (0.36, -0.085), (0.4, -0.05), (0.412, 0.0), (0.4, 0.05), (0.36, 0.085), (0.03, 0.022)]
            out.append(C.prism("leaf", pts, (hub + n * lift, d, w, n), thick, GRAFT, det, 0.0012))
        out.append(C.slab("rim", hub + n * 0.0475 + d * 0.385, (d, w, n), (0.004, 0.1, 0.002), GLOW, False))
        out.append(C.slab("rib", hub + n * 0.0478 + d * 0.2, (d, w, n), (0.28, 0.012, 0.003), METAL, det, 0.001))

    hi, lo = both(build)
    C.add_piece("shield", "forearm.L", hi, lo)
    views = (("side", (1.5, -1.5, 1.2), (0.5, 0.0, 1.05), 60), ("front", (1.0, -3.4, 1.7), (0.0, 0.0, 1.3), 85))

# ====================================================================== SX-8 setae bank
elif PART == "sx8_urticating_setae":
    CERAMIC = C.mat_paint(PART + "_ceramic", (0.78, 0.74, 0.66), 0.38)
    MATS.append(CERAMIC)
    o0, d, w, n = arm_frame("L", 0.2)
    o1, _d, _w, _n = arm_frame("L", 0.86)
    L = (o1 - o0).length

    def build(det, out):
        mid = o0.lerp(o1, 0.5)
        out.append(C.slab("bank", mid + n * 0.006, (d, w, n), (L, 0.046, 0.012), METAL, det, 0.003))
        for s in (-1, 1):
            out.append(C.slab("gill", mid + n * 0.002 + w * s * 0.031, (d, w, n), (L * 0.8, 0.014, 0.004), GRAFT, det, 0.001))
            out.append(C.slab("gill_glow", mid + n * 0.0045 + w * s * 0.025, (d, w, n), (L * 0.7, 0.0016, 0.0012), GLOW, False))
        if det:
            for r, ws in enumerate((-0.013, 0.0, 0.013)):
                for k in range(8):
                    t = (k + (0.5 if r == 1 else 0.0)) / 7.5
                    p = o0 + d * (0.012 + (L - 0.024) * t) + w * ws + n * 0.012
                    out.append(C.cyl("port", p, p + n * 0.003, 0.0042, CERAMIC, True, 12, 0.0004))
                    out.append(C.cyl("bore", p + n * 0.0026, p + n * 0.0032, 0.0025, RUBBER, False, 10, 0.0))
            for s in (-1, 1):
                out.append(C.cable("feed", [o0 + w * s * 0.012 + n * 0.008, o0 - d * 0.04 + w * s * 0.014 + n * 0.012, o0 - d * 0.09 + w * s * 0.016 + n * 0.006], 0.0035, RUBBER, True))
        else:
            out.append(C.slab("ports", mid + n * 0.0125, (d, w, n), (L - 0.02, 0.036, 0.002), CERAMIC, False))

    hi, lo = both(build)
    C.add_piece("bank", "forearm.L", hi, lo)
    views = (("side", (1.3, -1.3, 1.25), (0.45, 0.0, 1.13), 60), ("front", (1.0, -3.4, 1.7), (0.0, 0.0, 1.3), 85))

else:
    raise SystemExit("unknown part " + PART)

C.run(PART, args, MATS, views)
