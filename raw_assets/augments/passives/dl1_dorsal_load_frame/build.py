"""DL-1 Dorsal Load Frame (docs/design.md §3.6): a spinal exoframe, shoulder outriggers and an ammunition feed.

Design: a twin-rail spine beam stands off the back, bolted to the vertebrae through standoffs (the CT-7 back plate
leaves a channel down the spine for them, so the frame clears the plating when both are worn). Vertebral clamp
blocks bind the rails every few centimetres. At the top a yoke crosses the shoulder blades to two outrigger hubs
behind the shoulders; from each hub a hooked arm goes over the shoulder and clamps to the front of the chest.
At the bottom a lumbar belt wraps to the hips and carries the load into the pelvis. An ammunition canister sits
on the right hip; its belt runs up an armoured chute beside the spine, over the right outrigger and the shoulder,
and ends in a feed mouth at the front of the right shoulder, where a machine gun's feed tray sits when it's
hip-fired. Dark olive-drab paint over gunmetal (it's a weapons mount), yellow-black hazard
bands at the feed mouth, stencils on the canister.

Pieces ride on chest (yoke, hooks, upper spine, chute), spine (lower spine) and hips (belt, canister).

Run:
  tools/blender.sh raw_assets/augments/passives/dl1_dorsal_load_frame/build.py \\
      --out assets/augments/passives/dl1_dorsal_load_frame/dl1_dorsal_load_frame.gltf --preview docs/previews/dl1_dorsal_load_frame
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _common as C  # noqa: E402
from _common import V, hs  # noqa: E402

args = C.args_parser()
C.TAG = "dl1"
body = C.body_once()
CT7 = C.add_obstacle(body, "ct7_trauma_plating", "ct7")
WHICH = ("suit", "ct7")

GUN = C.mat_metal("dl1_gunmetal", base=(0.07, 0.072, 0.076), rough=0.34, wear=(0.5, 0.5, 0.52), brushed=0.06)
OLIVE = hs.material("dl1_olive", (0.036, 0.04, 0.024), 0.55, 0.0, wear=(0.2, 0.2, 0.19), wear_rough=0.35,
                    bump_scale=1400.0, bump_strength=0.15)
CHROME = C.mat_chrome("dl1_chrome")
RUBBER = C.mat_rubber("dl1_rubber")
HAZARD = hs.material("dl1_hazard", (0.75, 0.55, 0.06), 0.5, 0.0)
PAINT = C.mat_paint("dl1_stencil", (0.78, 0.76, 0.66))
LED = C.mat_glow("dl1_led", color=(1.0, 0.55, 0.15), strength=3.0)
MATS = [GUN, OLIVE, CHROME, RUBBER, HAZARD, PAINT, LED]
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))


def back_y(x, z):
    """Outermost back surface (suit or CT-7) at (x, z)."""
    hit, _n = body.cast(V((x, 0.5, z)), -Y, WHICH, 0.45)
    return hit.y if hit is not None else 0.0


def spine_y(z):
    hit, _n = body.cast(V((0, 0.5, z)), -Y, ("suit",), 0.45)
    return hit.y if hit is not None else 0.1


Z0, Z1 = 1.1, 1.47
RAIL_Y = max(max(back_y(x, z) for x in (-0.05, -0.03, 0.03, 0.05) for z in (1.25, 1.3, 1.35, 1.4, 1.45)) + 0.016, 0.15)
C.log("rail y", RAIL_Y)
parts = {"chest": ([], []), "spine": ([], []), "hips": ([], [])}


def put(bone, det, ob):
    lst = parts[bone][0 if det else 1]
    if isinstance(ob, list):
        lst.extend(ob)
    else:
        lst.append(ob)


Z_SPLIT = 1.24     # below: spine bone
for det in (True, False):
    # ---- spine beam: twin rails, clamps, standoffs into the vertebrae
    for xr in (-0.017, 0.017):
        for (za, zb, bone) in ((Z0, Z_SPLIT - 0.004, "spine"), (Z_SPLIT + 0.004, Z1, "chest")):
            put(bone, det, C.slab("rail", V((xr, RAIL_Y, (za + zb) / 2)), (Z, X, Y), (zb - za, 0.011, 0.013), GUN, det, 0.0012))
    n_cl = 8
    for k in range(n_cl):
        z = Z0 + 0.012 + (Z1 - Z0 - 0.024) * k / (n_cl - 1)
        bone = "spine" if z < Z_SPLIT else "chest"
        outline = [(-0.03, -0.011), (0.03, -0.011), (0.034, -0.006), (0.034, 0.006), (0.03, 0.011), (-0.03, 0.011),
                   (-0.034, 0.006), (-0.034, -0.006)]
        put(bone, det, C.prism("clamp", outline, (V((0, RAIL_Y - 0.009, z)), X, Z, Y), 0.019, OLIVE, det, 0.0014))
        put(bone, det, C.slab("clamp_ridge", V((0, RAIL_Y + 0.0105, z)), (X, Z, Y), (0.016, 0.017, 0.003), GUN, det, 0.0006))
        if k % 2 == 0:
            sy = spine_y(z)
            put(bone, det, C.cyl("standoff", V((0, sy - 0.002, z)), V((0, RAIL_Y - 0.008, z)), 0.0065, CHROME, det, 16, 0.0004))
            put(bone, det, C.cyl("foot", V((0, sy - 0.003, z)), V((0, sy + 0.003, z)), 0.012, GUN, det, 20, 0.0008))
        if det:
            for xb in (-0.026, 0.026):
                bo = C.bolt("cb", V((xb, RAIL_Y + 0.01, z)), Y, r=0.0026, h=0.0018)
                put(bone, det, C.setmat(C.apply_all(bo), GUN))
    # ---- yoke across the shoulder blades to the outrigger hubs
    zy = Z1 + 0.012
    xs = [-0.2, -0.15, -0.1, -0.05, 0.0, 0.05, 0.1, 0.15, 0.2]
    pts = [V((x, max(back_y(x, zy), back_y(x, zy - 0.03)) + 0.02 if abs(x) > 0.02 else RAIL_Y, zy + abs(x) * 0.25)) for x in xs]
    pts[4] = V((0, RAIL_Y, zy))
    put("chest", det, C.sweep("yoke", pts, [Y] * len(pts), 0.009, lambda t: 0.016 + 0.006 * math.cos((t - 0.5) * math.pi),
                              OLIVE, det))
    for s in (-1, 1):
        hub = pts[0 if s < 0 else -1] + Y * 0.004
        put("chest", det, C.cyl("hub", hub - Y * 0.016, hub + Y * 0.014, 0.024, GUN, det, 32, 0.0014))
        put("chest", det, C.cyl("hub_cap", hub + Y * 0.012, hub + Y * 0.018, 0.015, CHROME, det, 32, 0.0006))
        put("chest", det, C.cyl("hub_led", hub + Y * 0.017, hub + Y * 0.019, 0.0035, LED, det, 12, 0.0))
        if det:
            for k in range(6):
                a = k * math.pi / 3
                bo = C.bolt("hb", hub + Y * 0.014 + V((math.cos(a), 0, math.sin(a))) * 0.0195, Y, r=0.0022, h=0.0014)
                put("chest", det, C.setmat(C.apply_all(bo), GUN))
        # Hooked arm over the shoulder to a chest clamp.
        x0 = hub.x
        top = [body.cast(V((x0 * 0.92, yy, 2.2)), -Z, WHICH + ("helmet",), 2.0)[0] for yy in (0.06, 0.0, -0.05)]
        hook = [hub + V((0, -0.01, 0.01)), V((x0 * 0.95, 0.08, top[0].z + 0.03 if top[0] else 1.62)),
                V((x0 * 0.93, 0.0, (top[1].z if top[1] else 1.59) + 0.03)), V((x0 * 0.92, -0.06, (top[2].z if top[2] else 1.57) + 0.012))]
        fr_hit, fr_n = body.cast(V((x0 * 0.9, -0.5, 1.5)), Y, WHICH, 0.6)
        pad = fr_hit + V((0, -0.012, 0)) if fr_hit is not None else V((x0 * 0.9, -0.1, 1.5))
        hook.append(pad + V((0, -0.002, 0.03)))
        nrm = [Y, Z, Z, Z * 0.5 - Y, -Y]
        put("chest", det, C.sweep("hook", hook, nrm, 0.0065, 0.014, OLIVE, det))
        put("chest", det, C.prism("chest_pad", C.chamfer_rect(0.024, 0.022, 0.008), (pad + Y * 0.006, X, Z, -Y), 0.011, GUN,
                                  det, 0.0014))
        put("chest", det, C.slab("pad_rubber", pad + Y * 0.008, (X, Z, -Y), (0.044, 0.04, 0.004), RUBBER, det, 0.0008))
        if det:
            for dx, dz in ((-0.014, -0.012), (0.014, -0.012), (-0.014, 0.012), (0.014, 0.012)):
                bo = C.bolt("pb", pad + V((dx, -0.005, dz)), -Y, r=0.0022, h=0.0015)
                put("chest", det, C.setmat(C.apply_all(bo), GUN))
    # ---- lumbar belt to the hips
    zb = 1.075
    bx = [-0.17, -0.13, -0.08, -0.04, 0.0, 0.04, 0.08, 0.13, 0.17]
    bpts, bn = [], []
    for x in bx:
        d = V((x * 4.0, 1.0, 0)).normalized()
        hit, n = body.cast(V((0, 0, zb)) + d * 0.5, -d, ("suit",), 0.6)
        bpts.append(hit + d * 0.012 if hit is not None else V((x, 0.1, zb)))
        bn.append(d)
    put("hips", det, C.sweep("belt", bpts, bn, 0.006, 0.022, OLIVE, det))
    put("hips", det, C.cyl("belt_link", V((0, RAIL_Y, Z0 - 0.004)), V((0, bpts[4].y + 0.004, Z0 - 0.004)), 0.011, GUN, det, 20, 0.001))
    put("hips", det, C.slab("belt_block", V((0, (RAIL_Y + bpts[4].y) / 2, zb + 0.005)), (X, Z, Y), (0.06, 0.05, RAIL_Y - bpts[4].y + 0.01),
                            GUN, det, 0.0016))
    for p, d in ((bpts[0], bn[0]), (bpts[-1], bn[-1])):
        put("hips", det, C.prism("hip_pad", C.chamfer_rect(0.02, 0.03, 0.008), (p - d * 0.006, d.cross(Z).normalized(), Z, d),
                                 0.012, GUN, det, 0.0014))
    # ---- ammunition canister on the right hip and its armoured feed chute
    can_c = V((-0.105, 0.0, 1.0))
    cy = max(back_y(x, z) for x in (-0.05, -0.1, -0.15) for z in (0.97, 1.0, 1.03, 1.06)) + 0.04
    can_c.y = cy
    can = C.prism("canister", C.chamfer_rect(0.07, 0.05, 0.012), (can_c - Y * 0.032, -X, Z, Y), 0.064, OLIVE, det, 0.0025)
    put("hips", det, can)
    put("hips", det, C.slab("lid", can_c + Z * 0.052 + Y * 0.0, (X, Y, Z), (0.13, 0.058, 0.008), GUN, det, 0.0016))
    put("hips", det, C.slab("latch", can_c + Y * 0.0335 + Z * 0.03 + X * 0.03, (X, Z, Y), (0.016, 0.024, 0.004), GUN, det, 0.0008))
    put("hips", det, C.slab("latch", can_c + Y * 0.0335 + Z * 0.03 - X * 0.03, (X, Z, Y), (0.016, 0.024, 0.004), GUN, det, 0.0008))
    for xx in (-0.06, 0.06):
        put("hips", det, C.slab("can_rib", can_c + X * xx + Y * 0.0, (Z, Y, X), (0.09, 0.066, 0.004), GUN, det, 0.0008))
    if det:
        st = C.stencil("st_can", "7.92 × 57\n250 LINKED", can_c + Y * 0.0325 - Z * 0.008, Y, Z, 0.0085, PAINT)
        put("hips", det, C.apply_all(st))
        st = C.stencil("st_dl1", "DL-1", V((0, RAIL_Y + 0.0066, Z1 - 0.07)), Y, Z, 0.009, PAINT)
        put("chest", det, C.apply_all(st))
    # Chute: canister top -> up beside the rails -> over the right outrigger -> over the shoulder -> feed mouth.
    hubR = pts[0]
    sh_top = body.cast(V((hubR.x * 0.8, 0.02, 2.2)), -Z, WHICH, 2.0)[0]
    fr_hit, _n = body.cast(V((hubR.x * 0.72, -0.5, 1.52)), Y, WHICH, 0.6)
    mouth = (fr_hit if fr_hit is not None else V((-0.15, -0.1, 1.52))) + V((0, -0.03, 0.0))
    path_lo = [can_c + Z * 0.06 + X * 0.03, V((-0.05, RAIL_Y + 0.006, 1.17)), V((-0.048, RAIL_Y + 0.008, Z_SPLIT))]
    path_hi = [V((-0.048, RAIL_Y + 0.008, Z_SPLIT)), V((-0.05, RAIL_Y + 0.01, 1.36)), V((-0.08, RAIL_Y + 0.006, Z1 + 0.04)),
               hubR + V((0.02, 0.02, 0.06)), V((hubR.x * 0.82, 0.035, (sh_top.z if sh_top else 1.6) + 0.045)),
               V((hubR.x * 0.76, -0.05, (sh_top.z if sh_top else 1.6) + 0.02)), mouth + V((0, 0.0, 0.035)), mouth]
    lo_links = C.link_chain("chute", path_lo, [Y, Y, Y], (0.015, 0.03, 0.012), 0.003, GUN, det, OLIVE)
    hi_links = C.link_chain("chute", path_hi, [Y, Y, Y, Y, Z, Z - Y * 0.6, -Y, -Y], (0.015, 0.03, 0.012), 0.003, GUN, det, OLIVE)
    put("spine", det, lo_links)
    put("chest", det, hi_links)
    # Feed mouth with hazard bands.
    put("chest", det, C.prism("mouth", C.chamfer_rect(0.024, 0.014, 0.004), (mouth - Z * 0.012, X, -Y, Z), 0.026, GUN, det, 0.0012))
    put("chest", det, C.slab("haz", mouth + Z * 0.0, (X, Y, Z), (0.05, 0.03, 0.006), HAZARD, det, 0.0006))
    if det:
        for k in range(4):
            put("chest", det, C.slab("haz_k", mouth + X * (-0.018 + 0.012 * k) - Y * 0.0151, (X, Z, -Y), (0.005, 0.006, 0.0006),
                                     RUBBER, False))

for bone, (hi, lo) in parts.items():
    C.add_piece("dl1_" + bone, bone, C.join(hi, "dl1_%s_high" % bone), C.join(lo, "dl1_%s_low" % bone))

C.run("dl1_dorsal_load_frame", args, MATS, (
    ("back", (-1.6, 4.2, 1.6), (0, 0, 1.2), 85),
    ("back_close", (-0.55, 0.95, 1.45), (-0.02, 0.1, 1.27), 50),
    ("shoulder", (-0.75, -0.6, 1.75), (-0.12, 0.0, 1.45), 55)), show=CT7)
