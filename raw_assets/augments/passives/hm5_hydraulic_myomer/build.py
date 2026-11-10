"""HM-5 Hydraulic Myomer Bundles (docs/design.md §3.6): pressurised muscle you can see and hear.

Design: heavy, industrial, wet. On the front of each thigh two corrugated myomer bellows (black rubberised
sleeves, banded with steel rings) flank a chrome hydraulic ram, all clamped between a hip anchor and a knee
anchor. On the back of each upper arm a single big ram drives the elbow: a gunmetal cylinder, a chrome rod and a
clevis at the elbow. On each hip a pump unit (finned motor, reservoir with an amber pressure window, a gauge)
feeds braided hoses to the thigh anchors. Pressure ratings and arrows are stencilled on the pumps. The back and
shoulders stay clear for CT-7 plating and the DL-1 frame (all three are in the Juggernaut preset).

Pieces ride on thigh.L/R, upper_arm.L/R and hips.

Run:
  tools/blender.sh raw_assets/augments/passives/hm5_hydraulic_myomer/build.py \\
      --out assets/augments/passives/hm5_hydraulic_myomer/hm5_hydraulic_myomer.gltf --preview docs/previews/hm5_hydraulic_myomer
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "hm5"
body = C.body_once()
CT7 = C.add_obstacle(body, "ct7_trauma_plating", "ct7")

GUN = C.mat_metal("hm5_gunmetal", base=(0.075, 0.077, 0.082), rough=0.32, wear=(0.52, 0.52, 0.54), brushed=0.06)
CHROME = C.mat_chrome("hm5_chrome")
STEEL = C.mat_metal("hm5_steel", base=(0.4, 0.4, 0.41), rough=0.22, wear=(0.65, 0.65, 0.66), brushed=0.1)
RUBBER = hs.material("hm5_rubber", (0.022, 0.022, 0.024), 0.55, 0.0, bump_scale=1800.0, bump_strength=0.2, coat=0.3)
HOSE = hs.material("hm5_hose", (0.05, 0.05, 0.052), 0.45, 0.6, bump_scale=3500.0, bump_strength=0.6)
AMBER = C.mat_glow("hm5_amber", color=(1.0, 0.36, 0.03), strength=3.0)
PAINT = C.mat_paint("hm5_stencil", (0.72, 0.7, 0.64))
MATS = [GUN, CHROME, STEEL, RUBBER, HOSE, AMBER, PAINT]
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
parts = {}


def put(bone, det, ob):
    hi, lo = parts.setdefault(bone, ([], []))
    (hi if det else lo).extend(ob if isinstance(ob, list) else [ob])


def surf(p, d, which=("suit",)):
    hit, _n = body.cast(p + d * 0.4, -d, which, 0.8)
    return hit if hit is not None else p + d * 0.06


def bellows(name, p0, p1, r, det, n_folds=17):
    """Corrugated sleeve from p0 to p1, fusiform, with steel rings at the ends."""
    ax = (p1 - p0).normalized()
    u = ax.orthogonal().normalized()
    w = ax.cross(u)
    n_st = n_folds * 6 if det else 8
    st = []
    for k in range(n_st + 1):
        t = k / n_st
        prof = 0.62 + 0.38 * math.sin(math.pi * t) ** 0.8
        corr = (1.0 + 0.055 * math.cos(t * n_folds * 2 * math.pi)) if det else 1.0
        rr = r * prof * corr
        st.append((p0.lerp(p1, t), u, w, rr, rr))
    hs.set_detail(hs.HIGH if det else hs.LOW)
    ob = hs.loft(name, st, n=20 if det else 8, power=2.0)
    ob.data.shade_smooth()
    out = [C.setmat(ob, RUBBER)]
    for t in (0.0, 1.0):
        c = p0.lerp(p1, t)
        out.append(C.cyl(name + "_ring", c - ax * 0.004, c + ax * 0.004, r * 0.7, STEEL, det, 20, 0.0006))
    return out


def ram(name, p0, p1, r, det, body_frac=0.58):
    """Hydraulic ram: gunmetal cylinder from p0, chrome rod to p1, gland and end eyes."""
    ax = (p1 - p0).normalized()
    pm = p0.lerp(p1, body_frac)
    out = [C.cyl(name + "_body", p0, pm, r, GUN, det, 28, 0.0015),
           C.cyl(name + "_gland", pm - ax * 0.002, pm + ax * 0.006, r * 0.78, STEEL, det, 28, 0.0008),
           C.cyl(name + "_rod", pm, p1, r * 0.42, CHROME, det, 20, 0.0004),
           C.cyl(name + "_cap", p0 - ax * 0.006, p0 + ax * 0.004, r * 1.08, STEEL, det, 28, 0.001)]
    if det:
        for f in (0.25, 0.75):
            c = p0.lerp(pm, f)
            out.append(C.cyl(name + "_band", c - ax * 0.002, c + ax * 0.002, r * 1.04, STEEL, True, 28, 0.0004))
    return out


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    hip, knee = body.joint("thigh." + side), body.joint("shin." + side)
    a = (knee - hip).normalized()
    L = (knee - hip).length
    f = V((0.12 * s, -1.0, 0.0))
    f = (f - a * f.dot(a)).normalized()
    sd = a.cross(f).normalized() * s
    for det in (True, False):
        # ---- thigh bundle
        t0, t1 = 0.14, 0.82
        base0, base1 = surf(hip + a * L * t0, f), surf(hip + a * L * t1, f)
        lift = max((surf(hip + a * L * (t0 + (t1 - t0) * k / 8) + sd * w, f) - base0.lerp(base1, k / 8)).dot(f)
                   for k in range(9) for w in (-0.03, 0.0, 0.03))
        b0, b1 = base0 + f * (lift + 0.004), base1 + f * (lift + 0.004)
        r = 0.0125
        for w in (-1, 1):
            off = sd * w * 0.026 + f * r
            put("thigh." + side, det, bellows("bel", b0 + off + a * 0.02, b1 + off - a * 0.02, r, det))
        put("thigh." + side, det, ram("tram", b0 + f * 0.011 + a * 0.016, b1 + f * 0.011 - a * 0.02, 0.0085, det, 0.55))
        for e, bp in enumerate((b0, b1)):
            outline = [(-0.012, -0.046), (0.012, -0.046), (0.018, -0.036), (0.018, 0.036), (0.012, 0.046), (-0.012, 0.046),
                       (-0.018, 0.036), (-0.018, -0.036)]
            put("thigh." + side, det, C.prism("anchor", outline, (bp - f * 0.004, a, sd, f), 0.03, GUN, det, 0.0016))
            if det:
                for w in (-0.034, 0.034):
                    bo = C.bolt("ab", bp + f * 0.026 + sd * w, f, r=0.003, h=0.002)
                    put("thigh." + side, det, C.setmat(C.apply_all(bo), STEEL))
                if e == 0:
                    st = C.stencil("st", "HM-5", bp + f * 0.0262, f, -a, 0.0068, PAINT)
                    put("thigh." + side, det, C.apply_all(st))
        # Hose from the hip anchor up and round to the pump.
        hose_start = b0 + f * 0.02 + sd * s * 0.03 * s + a * -0.012
        pump_c = V((0.175 * s, -0.015, 1.02))
        pump_surf = surf(pump_c, V((s, -0.2, 0)).normalized())
        hose_end = pump_surf + V((s, -0.2, 0)).normalized() * 0.012 - Z * 0.03
        mid = hose_start.lerp(hose_end, 0.5) + V((s * 0.02, -0.03, 0.0))
        put("thigh." + side, det, C.cable("hose", [hose_start, mid, hose_end], 0.0042, HOSE, det))
        put("thigh." + side, det, C.cyl("fitting", hose_start - a * 0.004, hose_start + a * 0.008, 0.0062, STEEL, det, 6, 0.0004))
        # ---- hip pump
        pd = V((s, -0.25, 0.0)).normalized()
        pu = Z
        pv = pu.cross(pd).normalized()
        pc = pump_surf + pd * 0.03
        put("hips", det, C.prism("pump", C.chamfer_rect(0.03, 0.04, 0.008), (pump_surf - pd * 0.004, pv, pu, pd), 0.04, GUN, det, 0.002))
        put("hips", det, C.cyl("motor", pc + pu * 0.04 - pv * 0.012, pc + pu * 0.04 + pv * 0.022, 0.016, STEEL, det, 24, 0.0012))
        if det:
            for k in range(6):
                c = pc + pu * 0.04 + pv * (-0.006 + k * 0.005)
                put("hips", det, C.cyl("fin", c - pv * 0.0008, c + pv * 0.0008, 0.0195, GUN, True, 24, 0.0))
        put("hips", det, C.slab("window", pump_surf + pd * 0.0365 - pu * 0.012, (pv, pu, pd), (0.012, 0.042, 0.004), AMBER, False))
        put("hips", det, C.slab("window_frame", pump_surf + pd * 0.035 - pu * 0.012, (pv, pu, pd), (0.02, 0.05, 0.004), STEEL, det, 0.0006))
        gc = pump_surf + pd * 0.036 + pu * 0.022 + pv * 0.018
        put("hips", det, C.cyl("gauge", gc - pd * 0.004, gc + pd * 0.006, 0.009, STEEL, det, 24, 0.0006))
        put("hips", det, C.cyl("gauge_face", gc + pd * 0.006, gc + pd * 0.0068, 0.0072, PAINT, det, 24, 0.0))
        if det:
            st = C.stencil("st_p", "28 MPa", pump_surf + pd * 0.0403 - pu * 0.035 - pv * 0.012, pd, pu, 0.0045, PAINT)
            put("hips", det, C.apply_all(st))
        # ---- triceps ram
        sh, el = body.joint("upper_arm." + side), body.joint("forearm." + side)
        ua = (el - sh).normalized()
        ULen = (el - sh).length
        bk = V((0.25 * s, 1.0, 0.1))
        bk = (bk - ua * bk.dot(ua)).normalized()
        q0 = surf(sh + ua * ULen * 0.3, bk, ("suit", "ct7"))
        q1 = surf(sh + ua * ULen * 0.97, bk, ("suit",))
        liftu = max((surf(sh + ua * ULen * (0.3 + 0.67 * k / 6), bk, ("suit", "ct7")) - q0.lerp(q1, k / 6)).dot(bk) for k in range(7))
        r0 = q0 + bk * (liftu + 0.016)
        r1 = q1 + bk * (liftu * 0.5 + 0.014)
        put("upper_arm." + side, det, ram("arm", r0, r1, 0.0115, det, 0.6))
        sideu = ua.cross(bk).normalized()
        put("upper_arm." + side, det, C.prism("mount", C.chamfer_rect(0.022, 0.016, 0.005), (r0 - bk * (liftu + 0.02) - ua * 0.004, ua, sideu, bk),
                                              liftu + 0.016, GUN, det, 0.0014))
        put("upper_arm." + side, det, C.slab("clevis", r1 - bk * 0.006, (ua, sideu, bk), (0.022, 0.026, 0.02), GUN, det, 0.0014))
        put("upper_arm." + side, det, C.cyl("pin", r1 - sideu * 0.016, r1 + sideu * 0.016, 0.004, STEEL, det, 16, 0.0004))

for bone, (hi, lo) in parts.items():
    C.add_piece("hm5_" + bone, bone, C.join(hi, "hm5_%s_high" % bone), C.join(lo, "hm5_%s_low" % bone))

th = body.joint("thigh.L") * 0.5 + body.joint("shin.L") * 0.5
ua = body.joint("upper_arm.R") * 0.5 + body.joint("forearm.R") * 0.5
C.run("hm5_hydraulic_myomer", args, MATS, (
    ("front", (0.9, -4.6, 1.2), (0, 0, 1.0), 85),
    ("thigh", th + V((0.45, -0.6, 0.22)), th + V((0.0, -0.05, 0.08)), 55),
    ("arm", ua + V((-0.35, 0.55, 0.15)), ua + V((0, 0.03, 0)), 55)), show=CT7)
