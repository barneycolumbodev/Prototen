"""EM-2 Electroactive Myofibrils (docs/design.md §3.6): synthetic muscle bundles showing through vented housings.

Design: on the front of each forearm and each biceps, a black graft tray carries a bundle of fusiform polymer
strands (finely striated, smoky blue-black) between two machined side rails. Electric-blue light runs in the
channels between the strands: the part draws 60 W and you can see where it goes. Cross straps hold the bundle
down; gunmetal tendon anchors with hex bolts clamp each end, and the upper forearm anchor carries an EM-2 stencil
and a status light. The housings sit on the inner front of the arm, clear of the HS-5 fins on the outer side
(both are in the Operator preset).

Pieces ride on forearm.L/R and upper_arm.L/R.

Run:
  tools/blender.sh raw_assets/augments/passives/em2_myofibrils/build.py \\
      --out assets/augments/passives/em2_myofibrils/em2_myofibrils.gltf --preview docs/previews/em2_myofibrils
  Design check without the bake: --quick --preview /tmp/em2
"""
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Matrix  # noqa: F401

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "em2"
body = C.body_once()

TRAY = C.mat_metal("em2_tray", base=(0.022, 0.023, 0.026), rough=0.4, wear=(0.36, 0.37, 0.4), brushed=0.03)
RAIL = C.mat_metal("em2_rail", base=(0.1, 0.104, 0.11), rough=0.3, wear=(0.55, 0.56, 0.58), brushed=0.08)
FIBRE = hs.material("em2_fibre", (0.035, 0.05, 0.085), 0.3, 0.0, bump_scale=2200.0, bump_strength=0.2, coat=0.6)
GLOW = C.mat_glow("em2_glow", color=(0.16, 0.46, 1.0), strength=4.0)
LED = C.mat_glow("em2_led", color=(0.16, 0.46, 1.0), strength=2.5)
PAINT = C.mat_paint("em2_stencil", (0.6, 0.6, 0.56))
MATS = [TRAY, RAIL, FIBRE, GLOW, LED, PAINT]


def pack(tag, bone, p0, p1, front, span, width, n_str, r_str):
    """One muscle pack on the arm segment p0 -> p1, on the side facing `front`."""
    a = (p1 - p0).normalized()
    L = (p1 - p0).length
    f = (V(front) - a * V(front).dot(a)).normalized()
    side = a.cross(f).normalized()
    t0, t1 = span

    def surf(t, w):
        c = p0 + a * L * t + side * w
        hit, _n = body.cast(c + f * 0.3, -f, ("suit",), 0.6)
        return hit if hit is not None else c + f * 0.045

    def line(w, lift):
        """A straight line from t0 to t1 over the surface at lateral w, `lift` clear of its highest point."""
        s0, s1 = surf(t0, w), surf(t1, w)
        bulge = max((surf(t0 + (t1 - t0) * k / 8, w) - s0.lerp(s1, k / 8)).dot(f) for k in range(9))
        off = f * (max(bulge, 0.0) + lift)
        return s0 + off, s1 + off

    hi_l, lo_l = [], []
    mid = p0 + a * L * (t0 + t1) * 0.5
    hu = L * (t1 - t0) * 0.5 + 0.016
    hv = width * 0.5 + 0.009
    hi_t, lo_t = C.plate(tag + "_tray", body, C.chamfer_rect(hu, hv, 0.008), (mid + f * 0.3, a, side), -f, 0.002, 0.0028,
                         facet_deg=5.0, smooth_r=0.01, bevel=0.0009)
    for o in (hi_t, lo_t):
        C.setmat(o, TRAY)
    hi_l.append(hi_t)
    lo_l.append(lo_t)
    base_lift = 0.0048 + r_str
    for det, lst in ((True, hi_l), (False, lo_l)):
        # Side rails.
        for w in (-1, 1):
            q0, q1 = line(w * (width * 0.5 + 0.004), 0.0)
            h = base_lift + r_str + 0.002
            c = (q0 + q1) * 0.5 + f * h * 0.5
            ax = (q1 - q0).normalized()
            lst.append(C.slab(tag + "_rail", c, (ax, side, f), ((q1 - q0).length + 0.006, 0.0045, h), RAIL, det, 0.0009))
        # Strands: fusiform, striated in HIGH.
        for i in range(n_str):
            w = -width * 0.5 + width * (i + 0.5) / n_str
            q0, q1 = line(w, base_lift)
            ax = (q1 - q0).normalized()
            u = ax.cross(f).normalized()
            n_st = 120 if det else 9
            stations = []
            for k in range(n_st + 1):
                t = k / n_st
                prof = 0.45 + 0.55 * math.sin(math.pi * t) ** 0.7
                stri = 1.0 + (0.04 * math.sin(t * 2 * math.pi * 38 + i) if det and 0.04 < t < 0.96 else 0.0)
                r = r_str * prof * stri
                stations.append((q0.lerp(q1, t), u, f, r, r * 0.92))
            hs.set_detail(hs.HIGH if det else hs.LOW)
            st = hs.loft(tag + "_strand", stations, n=16 if det else 6, power=2.0)
            st.data.shade_smooth()
            lst.append(C.setmat(st, FIBRE))
            # Light in the channel next to each strand.
            if i < n_str - 1:
                wg = -width * 0.5 + width * (i + 1) / n_str
                g0, g1 = line(wg, base_lift - r_str * 0.55)
                lst.append(C.cyl(tag + "_glow", g0.lerp(g1, 0.06), g0.lerp(g1, 0.94), r_str * 0.32, GLOW, det, 8, 0.0))
        # Cross straps over the bundle.
        n_strap = 3
        for k in range(n_strap):
            t = 0.22 + 0.56 * k / (n_strap - 1)
            ql0, ql1 = line(-(width * 0.5 + 0.004), 0.0)
            qr0, qr1 = line(width * 0.5 + 0.004, 0.0)
            pl, pr = ql0.lerp(ql1, t), qr0.lerp(qr1, t)
            ax = (ql1 - ql0).normalized()
            c = (pl + pr) * 0.5 + f * (base_lift + r_str + 0.0035)
            lst.append(C.slab(tag + "_strap", c, (ax, side, f), (0.0075, width + 0.016, 0.003), RAIL, det, 0.0008))
            if det:
                for w in (-1, 1):
                    bo = C.bolt("sb", c + side * w * (width * 0.5 + 0.004) + f * 0.0015, f, r=0.0018, h=0.0012)
                    lst.append(C.setmat(C.apply_all(bo), RAIL))
        # Tendon anchors at both ends.
        for e, t in ((0, t0 - 0.02), (1, t1 + 0.02)):
            s0 = surf(t, 0.0)
            lift = max((surf(t, w) - s0).dot(f) for w in (-width * 0.5, 0.0, width * 0.5))
            o = s0 + f * max(lift, 0.0)
            hgt = base_lift + r_str + 0.004
            outline = [(-0.009, -hv + 0.002), (0.009, -hv + 0.002), (0.013, -hv + 0.008), (0.013, hv - 0.008),
                       (0.009, hv - 0.002), (-0.009, hv - 0.002), (-0.013, hv - 0.008), (-0.013, -hv + 0.008)]
            blk = C.prism(tag + "_anchor", outline, (o - f * 0.003, a, side, f), hgt + 0.003, RAIL, det, 0.0012)
            lst.append(blk)
            top = o + f * hgt
            if det:
                for w in (-1, 1):
                    bo = C.bolt("ab", top + side * w * (hv - 0.007), f, r=0.0024, h=0.0016)
                    lst.append(C.setmat(C.apply_all(bo), TRAY))
                inward = 1.0 if e == 0 else -1.0
                lst.append(C.slab(tag + "_led", top + a * inward * 0.0075 + f * 0.0002,
                                  (a, side, f), (0.0018, 0.009, 0.001), LED, False))
                if e == 0 and bone.startswith("forearm"):
                    st = C.stencil("st_em2", "EM-2", top - a * 0.003 + f * 0.0002, f, -a, 0.0048, PAINT, target=blk)
                    lst.append(C.apply_all(st))
    C.add_piece(tag, bone, C.join(hi_l, tag + "_high"), C.join(lo_l, tag + "_low"))


for side in ("L", "R"):
    s = 1.0 if side == "L" else -1.0
    sh, el, wr = body.joint("upper_arm." + side), body.joint("forearm." + side), body.joint("hand." + side)
    pack("fa_" + side, "forearm." + side, el, wr, (-0.3 * s, -1.0, -0.12), (0.2, 0.74), 0.034, 4, 0.0052)
    pack("ua_" + side, "upper_arm." + side, sh, el, (-0.1 * s, -1.0, 0.05), (0.3, 0.78), 0.032, 3, 0.0058)

fl = body.joint("forearm.L") * 0.6 + body.joint("hand.L") * 0.4
ua = body.joint("upper_arm.L") * 0.45 + body.joint("forearm.L") * 0.55
C.run("em2_myofibrils", args, MATS, (
    ("front", (0.9, -4.6, 1.3), (0, 0, 1.15), 85),
    ("forearm", fl + V((0.05, -0.5, -0.12)), fl + V((0, -0.03, 0)), 60),
    ("biceps", ua + V((-0.25, -0.45, 0.1)), ua + V((0, -0.03, 0)), 60)))
