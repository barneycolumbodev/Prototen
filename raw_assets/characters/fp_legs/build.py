"""GS-2 graft suit first-person legs and combat boots for the midair dropkick (docs/design.md §5.7b).

Built in standing rest pose in Blender (+X right, +Y forward, +Z up; exports to
Godot +X right, +Y up, -Z forward). Articulated rigid hierarchy driven at
runtime by DropkickViewmodel (src/player/dropkick_viewmodel.gd) and collapsed
by RigidMerge into one draw per material:

  legs_root
    thigh_r -> shin_r -> boot_r (empties: sole_r, heel_r)
    thigh_l -> shin_l -> boot_l (empties: sole_l, heel_l)

Materials follow BodyColors.NAME_CHANNEL so the player's custom suit colours
paint the leg plates (`leg_plate` -> legs), boots (`boot` -> boots), undersuit
(`weave` -> undersuit), trim (`gunmetal` -> trim) and glow seams (`glow` -> lights).

Run (about 15 s export, ~45 s with preview):
  tools/blender.sh raw_assets/characters/fp_legs/build.py \
      --out assets/characters/fp_legs/fp_legs.gltf \
      --preview docs/previews/fp_legs.png
"""
import math
import os
import sys

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "augments", "actives"))
import _kit as K  # noqa: E402
import hardsurface as hs  # noqa: E402

args = K.init("fp_legs", 1, "0,1", views_default="hero,fp,sole")

# Leg-specific suit paint materials (BodyColors.NAME_CHANNEL).
K.mat("leg_plate", (0.024, 0.026, 0.030), 0.32, 0.0, coat=0.45)
K.mat("boot", (0.020, 0.021, 0.024), 0.42, 0.0, coat=0.25)
K.mat("sole", (0.014, 0.014, 0.016), 0.88, 0.0)

HIP_X = 0.105
KNEE_Z = -0.435
KNEE_Y = 0.010
ANKLE_Z = -0.855
ANKLE_Y = -0.008
SOLE_Z = -0.945


def lathe_z(name, profile, cx=0.0, cy=0.0, verts=22):
    """Vertical elliptical tube along Z. `profile`: [(z, rx, ry, dy_shift), ...]."""
    n = hs.nverts(verts)
    bm = bmesh.new()
    rings = []
    for z, rx, ry, dy in profile:
        if rx <= 1e-5 and ry <= 1e-5:
            rings.append([bm.verts.new((cx, cy + dy, z))])
        else:
            ring = []
            for i in range(n):
                a = 2.0 * math.pi * i / n
                ring.append(bm.verts.new((cx + rx * math.cos(a), cy + dy + ry * math.sin(a), z)))
            rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) > 1:
            for i in range(len(b)):
                bm.faces.new((a[0], b[(i + 1) % len(b)], b[i]))
        elif len(b) == 1 and len(a) > 1:
            for i in range(len(a)):
                bm.faces.new((a[i], a[(i + 1) % len(a)], b[0]))
        elif len(a) > 1 and len(b) > 1:
            for i in range(len(a)):
                j = (i + 1) % len(a)
                bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def shell_z(name, z0, z1, rx0, ry0, rx1, ry1, phi0_deg, phi1_deg, thick, cx=0.0, cy0=0.0, cy1=0.0, seg=5):
    """Faceted curved armor plate around Z. phi = 0 is +Y (front), +90 is +X (right)."""
    bm = bmesh.new()
    rings = []
    for z, rx, ry, cy in ((z0, rx0, ry0, cy0), (z1, rx1, ry1, cy1)):
        outer, inner = [], []
        for i in range(seg + 1):
            a = math.radians(phi0_deg + (phi1_deg - phi0_deg) * i / seg)
            sx, sy = math.sin(a), math.cos(a)
            outer.append(bm.verts.new((cx + sx * rx, cy + sy * ry, z)))
            inner.append(bm.verts.new((cx + sx * max(rx - thick, 0.005), cy + sy * max(ry - thick, 0.005), z)))
        rings.append((outer, inner))
    (o0, i0), (o1, i1) = rings
    for k in range(seg):
        bm.faces.new((o0[k], o1[k], o1[k + 1], o0[k + 1]))
        bm.faces.new((i0[k + 1], i1[k + 1], i1[k], i0[k]))
    for o, i in ((o0, i0), (o1, i1)):
        for k in range(seg):
            bm.faces.new((o[k], o[k + 1], i[k + 1], i[k]))
    bm.faces.new((o0[0], i0[0], i1[0], o1[0]))
    bm.faces.new((o1[-1], i1[-1], i0[-1], o0[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def ridge_plate_z(name, z0, z1, w0, w1, y0, y1, ridge_y, thick, cx=0.0):
    """Chamfered V-creased front plate (shin greave / quad crest) facing +Y."""
    bm = bmesh.new()
    # Profile across X: left wing -> center ridge -> right wing (outer & inner).
    o0 = [
        bm.verts.new((cx - w0, y0 - 0.012, z0)),
        bm.verts.new((cx - w0 * 0.45, y0 + ridge_y * 0.65, z0)),
        bm.verts.new((cx, y0 + ridge_y, z0)),
        bm.verts.new((cx + w0 * 0.45, y0 + ridge_y * 0.65, z0)),
        bm.verts.new((cx + w0, y0 - 0.012, z0)),
    ]
    o1 = [
        bm.verts.new((cx - w1, y1 - 0.010, z1)),
        bm.verts.new((cx - w1 * 0.45, y1 + ridge_y * 0.55, z1)),
        bm.verts.new((cx, y1 + ridge_y * 0.85, z1)),
        bm.verts.new((cx + w1 * 0.45, y1 + ridge_y * 0.55, z1)),
        bm.verts.new((cx + w1, y1 - 0.010, z1)),
    ]
    i0 = [bm.verts.new((v.co.x, v.co.y - thick, v.co.z)) for v in o0]
    i1 = [bm.verts.new((v.co.x, v.co.y - thick, v.co.z)) for v in o1]
    n = len(o0) - 1
    for k in range(n):
        bm.faces.new((o0[k], o0[k + 1], o1[k + 1], o1[k]))
        bm.faces.new((i0[k + 1], i0[k], i1[k], i1[k + 1]))
        bm.faces.new((o0[k + 1], o0[k], i0[k], i0[k + 1]))
        bm.faces.new((o1[k], o1[k + 1], i1[k + 1], i1[k]))
    bm.faces.new((o0[0], o1[0], i1[0], i0[0]))
    bm.faces.new((o0[-1], i0[-1], i1[-1], o1[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def build_thigh(side, tag):
    """Upper leg from hip (0) to knee (KNEE_Z), including pelvic overlap so no seam ever shows."""
    cx = HIP_X * side
    pcs = []
    # Muscular weave undersuit core (extends +0.13 m above hip so bottom screen edge is solid).
    pcs.append(K.piece(lathe_z(f"thigh_core_{tag}", [
        (0.13, 0.0, 0.0, 0.0),
        (0.12, 0.092, 0.088, -0.004),
        (0.02, 0.090, 0.088, 0.0),
        (-0.14, 0.082, 0.084, 0.008),
        (-0.29, 0.070, 0.072, 0.010),
        (KNEE_Z + 0.015, 0.058, 0.060, KNEE_Y),
        (KNEE_Z - 0.015, 0.052, 0.054, KNEE_Y),
        (KNEE_Z - 0.020, 0.0, 0.0, KNEE_Y),
    ], cx=cx, verts=16), "weave", bevel=0.0))

    # Split front quad armor plates (outer + inner separated by dark channel + lit seam).
    a_out = (8 * side, 56 * side) if side > 0 else (-56, -8)
    a_in = (-46 * side, -8 * side) if side > 0 else (8, 46)
    pcs.append(K.piece(shell_z(f"quad_out_{tag}", -0.03, -0.355, 0.095, 0.097, 0.072, 0.075,
                               a_out[0], a_out[1], 0.008, cx=cx, cy0=0.002, cy1=0.010, seg=4),
                       "leg_plate", bevel=0.0014, segments=1))
    pcs.append(K.piece(shell_z(f"quad_in_{tag}", -0.05, -0.345, 0.093, 0.095, 0.070, 0.073,
                               a_in[0], a_in[1], 0.007, cx=cx, cy0=0.002, cy1=0.010, seg=4),
                       "leg_plate", bevel=0.0014, segments=1))

    # Lit cyan seam tucked between the split quad plates.
    pcs.append(K.piece(hs.cyl_between(f"quad_glow_{tag}",
                                      (cx, 0.093, -0.065), (cx, 0.078, -0.325), 0.0020, verts=6),
                       "glow", bevel=0.0))

    # Outer thigh tactical strip + hardpoint puck with indicator dot (matches operative/build.py).
    a_side = (64, 118) if side > 0 else (-118, -64)
    pcs.append(K.piece(shell_z(f"thigh_side_{tag}", -0.09, -0.34, 0.092, 0.090, 0.072, 0.072,
                               a_side[0], a_side[1], 0.007, cx=cx, cy0=0.0, cy1=0.006, seg=3),
                       "leg_plate", bevel=0.0012, segments=1))
    hp_x = cx + 0.088 * side
    pcs.append(K.piece(hs.cyl_x(f"thigh_hp_{tag}", 0.022, hp_x - 0.008 * side, hp_x + 0.008 * side,
                                verts=14, y=0.006, z=-0.21) if side > 0 else
                       hs.cyl_x(f"thigh_hp_{tag}", 0.022, hp_x + 0.008 * side, hp_x - 0.008 * side,
                                verts=14, y=0.006, z=-0.21),
                       "gunmetal", bevel=0.0010, segments=1))
    pcs.append(K.piece(hs.box(f"thigh_hp_dot_{tag}", (0.004, 0.009, 0.004),
                              (hp_x + 0.009 * side, 0.006, -0.21)), "glow", bevel=0.0))

    # Outer hydraulic myomer damper driving into the knee hinge.
    px = cx + 0.074 * side
    pcs.append(K.piece(hs.cyl_between(f"thigh_cyl_{tag}", (px, -0.004, -0.25), (px - 0.004 * side, 0.004, -0.365),
                                      0.011, verts=10), "gunmetal", bevel=0.0008, segments=1))
    pcs.append(K.piece(hs.cyl_between(f"thigh_rod_{tag}", (px - 0.004 * side, 0.004, -0.35),
                                      (cx + 0.064 * side, KNEE_Y, KNEE_Z + 0.01), 0.006, verts=8),
                       "steel", bevel=0.0))

    # Thigh compression strap above the knee.
    pcs.append(K.piece(shell_z(f"thigh_strap_{tag}", -0.365, -0.395, 0.067, 0.069, 0.064, 0.066,
                               -155, 155, 0.004, cx=cx, cy0=0.009, cy1=0.010, seg=10),
                       "polymer", bevel=0.0005, segments=1))

    return K.part(f"thigh_{tag}", pcs, pivot=(cx, 0.0, 0.0))


def build_shin(side, tag):
    """Knee cap, calf weave, chamfered shin greave, glowing seams, ankle actuators."""
    cx = HIP_X * side
    pcs = []
    # Muscular calf weave core.
    pcs.append(K.piece(lathe_z(f"shin_core_{tag}", [
        (KNEE_Z + 0.025, 0.0, 0.0, KNEE_Y),
        (KNEE_Z + 0.015, 0.054, 0.056, KNEE_Y),
        (KNEE_Z - 0.055, 0.053, 0.058, 0.000),
        (KNEE_Z - 0.145, 0.060, 0.066, -0.016),  # calf muscle belly
        (KNEE_Z - 0.275, 0.048, 0.052, -0.012),
        (ANKLE_Z + 0.030, 0.042, 0.044, ANKLE_Y),
        (ANKLE_Z - 0.010, 0.040, 0.042, ANKLE_Y),
        (ANKLE_Z - 0.015, 0.0, 0.0, ANKLE_Y),
    ], cx=cx, verts=16), "weave", bevel=0.0))

    # Faceted diamond knee cap guard + gunmetal hinge pins + steel impact brow.
    pcs.append(K.piece(ridge_plate_z(f"knee_cap_{tag}", KNEE_Z + 0.048, KNEE_Z - 0.064,
                                     0.048, 0.040, KNEE_Y + 0.060, KNEE_Y + 0.055, 0.022, 0.012, cx=cx),
                       "leg_plate", bevel=0.0018, segments=1))
    pcs.append(K.piece(hs.box(f"knee_brow_{tag}", (0.044, 0.012, 0.016),
                              (cx, KNEE_Y + 0.076, KNEE_Z + 0.006)), "steel", bevel=0.0014, segments=1))
    # Side knee joint hinge discs.
    for sgn in (-1, 1):
        hx = cx + 0.058 * sgn
        x0, x1 = (hx - 0.008, hx + 0.008)
        pcs.append(K.piece(hs.cyl_x(f"knee_hinge_{tag}_{sgn}", 0.022, x0, x1, verts=14, y=KNEE_Y + 0.004, z=KNEE_Z),
                           "gunmetal", bevel=0.0012, segments=1))
        pcs.append(K.piece(hs.cyl_x(f"knee_bolt_{tag}_{sgn}", 0.010, x0 - 0.003, x1 + 0.003, verts=10, y=KNEE_Y + 0.004, z=KNEE_Z),
                           "steel", bevel=0.0))

    # Heavy chamfered front shin greave armor (high-visibility in first-person kick!).
    pcs.append(K.piece(ridge_plate_z(f"shin_greave_{tag}", KNEE_Z - 0.072, ANKLE_Z + 0.055,
                                     0.052, 0.040, 0.062, 0.044, 0.022, 0.012, cx=cx),
                       "leg_plate", bevel=0.0016, segments=1))
    # Dual glowing seam strips running down the flanks of the shin greave.
    for sgn in (-1, 1):
        pcs.append(K.piece(hs.cyl_between(
            f"shin_glow_{tag}_{sgn}",
            (cx + 0.038 * sgn, 0.062, KNEE_Z - 0.088),
            (cx + 0.030 * sgn, 0.044, ANKLE_Z + 0.072),
            0.0019, verts=6), "glow", bevel=0.0))

    # Outer & back calf armor plates + straps.
    a_calf = (56, 138) if side > 0 else (-138, -56)
    pcs.append(K.piece(shell_z(f"calf_out_{tag}", KNEE_Z - 0.08, ANKLE_Z + 0.11,
                               0.064, 0.070, 0.052, 0.054, a_calf[0], a_calf[1], 0.007,
                               cx=cx, cy0=-0.012, cy1=-0.012, seg=4),
                       "leg_plate", bevel=0.0012, segments=1))
    for sz in (KNEE_Z - 0.13, KNEE_Z - 0.28):
        pcs.append(K.piece(shell_z(f"shin_strap_{tag}_{int(-sz*100)}", sz, sz - 0.024,
                                   0.059, 0.067, 0.058, 0.066, -170, 170, 0.004,
                                   cx=cx, cy0=-0.012, cy1=-0.012, seg=10),
                           "polymer", bevel=0.0005, segments=1))

    # Ankle stabilizer hydraulic struts (left & right of the shin).
    for sgn in (-1, 1):
        sx = cx + 0.048 * sgn
        pcs.append(K.piece(hs.cyl_between(f"ankle_cyl_{tag}_{sgn}",
                                          (sx, -0.018, KNEE_Z - 0.21), (sx - 0.004 * sgn, -0.010, ANKLE_Z + 0.09),
                                          0.0085, verts=8), "gunmetal", bevel=0.0006, segments=1))
        pcs.append(K.piece(hs.cyl_between(f"ankle_rod_{tag}_{sgn}",
                                          (sx - 0.004 * sgn, -0.010, ANKLE_Z + 0.10), (cx + 0.046 * sgn, ANKLE_Y, ANKLE_Z + 0.005),
                                          0.0048, verts=6), "steel", bevel=0.0))

    return K.part(f"shin_{tag}", pcs, pivot=(cx, KNEE_Y, KNEE_Z))


def build_boot(side, tag):
    """Heavy armored GS-2 combat boot with deep chevron tread lugs & titanium strike cleats."""
    cx = HIP_X * side
    pcs = []

    # Armored boot cuff around the ankle.
    pcs.append(K.piece(lathe_z(f"boot_cuff_{tag}", [
        (ANKLE_Z + 0.075, 0.0, 0.0, ANKLE_Y),
        (ANKLE_Z + 0.070, 0.052, 0.056, ANKLE_Y + 0.002),
        (ANKLE_Z + 0.010, 0.053, 0.060, ANKLE_Y + 0.006),
        (ANKLE_Z - 0.035, 0.054, 0.064, ANKLE_Y + 0.012),
        (ANKLE_Z - 0.040, 0.0, 0.0, ANKLE_Y + 0.012),
    ], cx=cx, verts=14), "boot", bevel=0.0))

    # Ankle pivot discs (gunmetal).
    for sgn in (-1, 1):
        ax = cx + 0.054 * sgn
        pcs.append(K.piece(hs.cyl_x(f"ankle_disc_{tag}_{sgn}", 0.018, ax - 0.007, ax + 0.007,
                                    verts=12, y=ANKLE_Y + 0.004, z=ANKLE_Z + 0.008),
                           "gunmetal", bevel=0.0009, segments=1))

    # Main boot upper body (sculpted side profile extruded across boot width).
    z_mid = SOLE_Z + 0.028
    upper_yz = [
        (-0.072, z_mid),
        (0.194, z_mid),
        (0.202, z_mid + 0.024),
        (0.168, z_mid + 0.050),
        (0.088, z_mid + 0.076),
        (0.030, ANKLE_Z + 0.048),
        (-0.048, ANKLE_Z + 0.042),
        (-0.074, z_mid + 0.058),
    ]
    boot_w = 0.104
    pcs.append(K.piece(hs.prism(f"boot_upper_{tag}",
                                [(cx - boot_w * 0.5, y, z) for y, z in upper_yz],
                                (boot_w, 0.0, 0.0)), "boot", bevel=0.0065, segments=2))

    # Faceted armored instep guard plate + twin buckle bars.
    instep_yz = [
        (0.042, z_mid + 0.072),
        (0.132, z_mid + 0.050),
        (0.124, z_mid + 0.068),
        (0.036, z_mid + 0.095),
    ]
    pcs.append(K.piece(hs.prism(f"boot_instep_{tag}",
                                [(cx - 0.044, y, z) for y, z in instep_yz],
                                (0.088, 0.0, 0.0)), "leg_plate", bevel=0.0020, segments=1))
    for by, bz in ((0.064, z_mid + 0.078), (0.106, z_mid + 0.064)):
        pcs.append(K.piece(hs.box(f"boot_strap_{tag}_{int(by*100)}", (0.112, 0.016, 0.010),
                                  (cx, by, bz), rot=(math.radians(-18), 0, 0)),
                           "gunmetal", bevel=0.0012, segments=1))

    # Reinforced beveled steel toe-cap (catches specular highlights during kick!).
    toe_yz = [
        (0.138, z_mid + 0.002),
        (0.205, z_mid + 0.004),
        (0.210, z_mid + 0.026),
        (0.180, z_mid + 0.052),
        (0.132, z_mid + 0.058),
    ]
    pcs.append(K.piece(hs.prism(f"boot_toecap_{tag}",
                                [(cx - 0.055, y, z) for y, z in toe_yz],
                                (0.110, 0.0, 0.0)), "gunmetal", bevel=0.0045, segments=1))
    # Bright steel bumper lip right at the front tip of the toe.
    pcs.append(K.piece(hs.box(f"boot_toelip_{tag}", (0.086, 0.016, 0.020),
                              (cx, 0.204, z_mid + 0.016)), "steel", bevel=0.0022, segments=1))

    # Armored heel counter & metallic impact heel spur.
    pcs.append(K.piece(hs.box(f"boot_heel_{tag}", (0.108, 0.042, 0.062),
                              (cx, -0.058, z_mid + 0.032)), "leg_plate", bevel=0.0032, segments=1))
    pcs.append(K.piece(hs.box(f"boot_spur_{tag}", (0.066, 0.018, 0.020),
                              (cx, -0.078, z_mid + 0.012)), "steel", bevel=0.0018, segments=1))

    # Heavy vulcanized rubber outsole base (slightly wider than upper for aggressive silhouette).
    sole_w = 0.116
    sole_yz = [
        (-0.082, SOLE_Z + 0.008),
        (0.214, SOLE_Z + 0.008),
        (0.212, z_mid + 0.004),
        (-0.080, z_mid + 0.004),
    ]
    pcs.append(K.piece(hs.prism(f"sole_base_{tag}",
                                [(cx - sole_w * 0.5, y, z) for y, z in sole_yz],
                                (sole_w, 0.0, 0.0)), "sole", bevel=0.0028, segments=1))

    # Deep aggressive chevron tread lugs across the underside of the sole.
    lug_ys = (-0.062, -0.032, 0.042, 0.074, 0.106, 0.138, 0.172, 0.198)
    for k, ly in enumerate(lug_ys):
        w = 0.044 if k < 7 else 0.036
        for sgn in (-1, 1):
            pcs.append(K.piece(hs.box(f"lug_{tag}_{k}_{sgn}", (w, 0.018, 0.012),
                                      (cx + 0.028 * sgn, ly, SOLE_Z + 0.004),
                                      rot=(0.0, 0.0, math.radians(-16.0 * sgn))),
                               "sole", bevel=0.0010, segments=1))

    # Beveled titanium strike cleats bolted into the ball of the foot and heel edge.
    pcs.append(K.piece(hs.box(f"cleat_ball_{tag}", (0.076, 0.044, 0.009),
                              (cx, 0.112, SOLE_Z + 0.003)), "steel", bevel=0.0014, segments=1))
    pcs.append(K.piece(hs.box(f"cleat_heel_{tag}", (0.072, 0.034, 0.009),
                              (cx, -0.048, SOLE_Z + 0.003)), "gunmetal", bevel=0.0014, segments=1))
    # Tiny glowing heel/arch status bar on the outer welt.
    pcs.append(K.piece(hs.box(f"boot_glow_{tag}", (0.004, 0.048, 0.004),
                              (cx + (sole_w * 0.5 + 0.001) * side, 0.020, z_mid + 0.002)),
                       "glow", bevel=0.0))

    boot = K.part(f"boot_{tag}", pcs, pivot=(cx, ANKLE_Y, ANKLE_Z))
    sole_pt = K.empty(f"sole_{tag}", (cx, 0.105, SOLE_Z))
    heel_pt = K.empty(f"heel_{tag}", (cx, -0.048, SOLE_Z))
    K.parent(sole_pt, boot)
    K.parent(heel_pt, boot)
    return boot


root = K.empty("legs_root", (0.0, 0.0, 0.0))
RIG = {}
for side, tag in ((1, "r"), (-1, "l")):
    th = build_thigh(side, tag)
    sh = build_shin(side, tag)
    bt = build_boot(side, tag)
    K.parent(th, root)
    K.parent(sh, th)
    K.parent(bt, sh)
    RIG[tag] = (th, sh, bt)

# Frame 0 = standing rest pose; Frame 1 = brutal first-person dropkick pose (preview only).
K.capture_rest()
for tag in ("r", "l"):
    for ob in RIG[tag]:
        K.key(ob, 0)
K.key(root, 0)

# Frame 1 preview pose: right boot drives forward straight ahead, left leg angled slightly lower.
K.key(root, 1, dloc=(0.0, -0.18, -0.18), drot=(0.0, -10.0, 4.0))
K.key(RIG["r"][0], 1, drot=(86.0, -4.0, -6.0))
K.key(RIG["r"][1], 1, drot=(-12.0, 0.0, 0.0))
K.key(RIG["r"][2], 1, drot=(14.0, 0.0, 6.0))
K.key(RIG["l"][0], 1, drot=(74.0, 8.0, 12.0))
K.key(RIG["l"][1], 1, drot=(-24.0, 0.0, 0.0))
K.key(RIG["l"][2], 1, drot=(10.0, -10.0, -12.0))

VIEWS = {
    # 3/4 view showing both GS-2 legs in rest and kick poses.
    "hero": ((1.15, 1.35, -0.35), (0.0, 0.15, -0.46), 0),
    # Simulated first-person operative eye view (60 deg vertical FOV looking along +Y).
    "fp": ((0.0, -0.22, 0.06), (0.0, 0.85, -0.16), 60),
    # Low front close-up of the boots, tread lugs and strike cleats.
    "sole": ((0.38, 1.35, -0.62), (0.02, 0.18, -0.58), 0),
}

print(f"fp_legs: {K.tri_count()} triangles")
if args.preview:
    K.render_previews(args.preview.rsplit(".", 1)[0], VIEWS, aim=(0.0, 0.25, -0.45))
if args.out:
    # Reset cleanly to rest pose (frame 0) and strip preview animation before exporting static rig.
    K.scene.frame_set(0)
    for ob in bpy.data.objects:
        if ob.animation_data:
            ob.animation_data_clear()
    K.export(args.out, animated=False)
