"""Prosthetic hands and forearms for the first-person arms (owner, 2026-11-25: "significantly more high
fidelity ... a sleek prosthetic look"; they replace the metaball gloves).

The look: every phalanx is a gloss black composite shell (HIGH: a top plate and two side plates with seams
between them) over a dark anodised chassis link, a matte rubber pad under it, hinged on an exposed titanium
knuckle with steel axle caps. The back of the hand: a plate over the wrist half with a lit slit, a raised plate
along each metacarpal, a titanium knuckle band with a domed cap over every knuckle, all on a rounded chassis
palm. The wrist is a ribbed weave neck into a chassis collar with a lit ring; the forearm is a dorsal and a
ventral satin shell (each in two overlapping plates) with a piston down each open side channel and a lit strip,
then a chassis cuff and the suit's weave sleeve at the elbow.

Two users, one segment design:
- the gun-arm scripts (raw_assets/characters/fp_arms*/build.py) bind GunArms' finger / metaball / capsule /
  palm_shell / arm and call them with their poses (the joint chains and palm sheets round each grip, as the
  metaball gloves had them). HIGH is baked onto LOW.
- the actives' kit hand (raw_assets/augments/actives/_kit.py hand()) builds the same segments and palm in its
  own frame, unbaked, with the node names, pivots and segment lengths it always had, so the deploy clips need
  no change.

Bake rules learnt here: HIGH-only detail stays within a millimetre of a LOW surface (seams have a floor half a
millimetre down), big round LOW pieces get enough sides to stay inside the cage, and LOW's rims are marked sharp
so its normals already match HIGH's.

Frames: a phalanx is built along local +X (proximal knuckle at 0), +Z dorsal (back of the finger), +Y across.
"""
import math

import bpy
import bmesh
from mathutils import Matrix, Vector

V = Vector

# Detail: HIGH is the bake source, GAME an unbaked model used as built (the kit), LOW the bake target.
HIGH = {"name": "high", "around": 28, "along": 12, "bevel": 0.00028, "bseg": 2, "small": True, "panels": True, "cyl": 28, "grid": (14, 12)}
GAME = {"name": "game", "around": 10, "along": 4, "bevel": 0.00022, "bseg": 1, "small": True, "panels": False, "cyl": 10, "grid": (8, 6)}
LOW = {"name": "low", "around": 10, "along": 4, "bevel": 0.0, "bseg": 0, "small": False, "panels": False, "cyl": 10, "grid": (9, 7)}

# Material keys -> (name, base colour, roughness, metallic, extra). Roughness and metallic are what
# tools/colors/build_regions.py sorts the baked arms by: shell < 0.27 (hand plates), 0.27..0.45 (arm plates),
# dark metal >= 0.38 (chassis: trim), bright metal < 0.38 (joints: left alone), 0.45..0.75 (pads: left alone),
# >= 0.75 (weave: undersuit), lit (suit lights).
SPEC = {
    "shell": ("pro_shell", (0.030, 0.032, 0.036), 0.22, 0.0, {"coat": 0.6}),
    "arm_shell": ("pro_arm_shell", (0.034, 0.036, 0.040), 0.33, 0.0, {"coat": 0.3}),
    "frame": ("pro_frame", (0.40, 0.41, 0.43), 0.28, 1.0, {"brushed": 0.04}),
    "chassis": ("pro_chassis", (0.11, 0.115, 0.122), 0.44, 1.0, {}),
    "steel": ("pro_steel", (0.78, 0.79, 0.81), 0.16, 1.0, {}),
    "pad": ("pro_pad", (0.016, 0.016, 0.018), 0.62, 0.0, {"bump_scale": 1600.0, "bump_strength": 0.10}),
    "core": ("pro_core", (0.026, 0.027, 0.029), 0.86, 0.0, {"bump_scale": 900.0, "bump_strength": 0.12}),
    "glow": ("pro_glow", (1.0, 0.56, 0.24), 0.35, 0.0, {"emission": ((1.0, 0.5, 0.18), 4.0)}),
}
# UV space for the bake: the titanium joints are small and seen close, the hand shells are the most seen.
UV_BOOST = {SPEC["frame"][0]: 1.6, SPEC["shell"][0]: 1.3}
# The kit (unbaked, painted by material name: BodyColors.NAME_CHANNEL).
KIT_MATS = {"shell": "hand_shell", "arm_shell": "graft", "frame": "steel", "chassis": "gunmetal", "steel": "steel",
            "pad": "grip_pad", "core": "weave", "glow": "glow"}


class Piece:
    __slots__ = ("ob", "key", "bevel")

    def __init__(self, ob, key, bevel=0.0):
        self.ob, self.key, self.bevel = ob, key, bevel


# ---------------------------------------------------------------- mesh primitives
def _obj(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def frame_from(origin, x, z_hint):
    """Right-handed frame at `origin`: +X along `x`, +Z as close to `z_hint` as it can be."""
    x = V(x).normalized()
    z = V(z_hint) - x * V(z_hint).dot(x)
    if z.length < 1e-6:
        z = x.orthogonal()
    z.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(origin)
    return m


def _se(a, power):
    """Superellipse direction for angle a (0 = +Z, +90 deg = +Y): (y, z)."""
    s, c = math.sin(a), math.cos(a)
    e = 2.0 / power
    return math.copysign(abs(s) ** e, s), math.copysign(abs(c) ** e, c)


def loft(name, frame, stations, n, power=2.4, cap=True):
    """Closed loft along local X. stations: (x, half width (Y), half height (Z), z centre[, y centre])."""
    bm = bmesh.new()
    rings = []
    for st in stations:
        x, hw, hh, zc = st[:4]
        yc = st[4] if len(st) > 4 else 0.0
        hw, hh = max(hw, 2e-5), max(hh, 2e-5)
        ring = []
        for i in range(n):
            y, z = _se(2 * math.pi * i / n, power)
            ring.append(bm.verts.new(frame @ V((x, yc + y * hw, zc + z * hh))))
        rings.append(ring)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return _obj(name, bm)


def shell(name, frame, stations, a0, a1, thick, n, power=2.6):
    """Open arc shell along local X from angle a0 to a1 (deg, 0 = +Z, +90 = +Y), `thick` deep, closed solid.
    stations: (x, outer half width, outer half height, z centre)."""
    a0, a1 = math.radians(a0), math.radians(a1)
    bm = bmesh.new()
    outer, inner = [], []
    for x, hw, hh, zc in stations:
        o, i_ = [], []
        for k in range(n + 1):
            y, z = _se(a0 + (a1 - a0) * k / n, power)
            o.append(bm.verts.new(frame @ V((x, y * hw, zc + z * hh))))
            i_.append(bm.verts.new(frame @ V((x, y * max(hw - thick, 1e-4), zc + z * max(hh - thick, 1e-4)))))
        outer.append(o)
        inner.append(i_)
    s_n = len(stations)
    for s in range(s_n - 1):
        for k in range(n):
            bm.faces.new((outer[s][k], outer[s + 1][k], outer[s + 1][k + 1], outer[s][k + 1]))
            bm.faces.new((inner[s][k + 1], inner[s + 1][k + 1], inner[s + 1][k], inner[s][k]))
        bm.faces.new((outer[s][0], inner[s][0], inner[s + 1][0], outer[s + 1][0]))
        bm.faces.new((outer[s + 1][n], inner[s + 1][n], inner[s][n], outer[s][n]))
    for s in (0, s_n - 1):
        for k in range(n):
            bm.faces.new((outer[s][k], outer[s][k + 1], inner[s][k + 1], inner[s][k]))
    return _obj(name, bm)


def cyl(name, p0, p1, r, n, r1=None, power=2.0, z_hint=None):
    """Cylinder (cone with r1) from p0 to p1."""
    p0, p1 = V(p0), V(p1)
    d = p1 - p0
    f = frame_from(p0, d, z_hint if z_hint is not None else d.orthogonal())
    return loft(name, f, [(0.0, r, r, 0.0), (d.length, r1 if r1 is not None else r, r1 if r1 is not None else r, 0.0)], n,
                power=power)


def param_solid(name, outer_fn, inner_fn, nu, nv):
    """Closed solid between two parametric sheets over (fu, fv) in [0, 1]^2."""
    bm = bmesh.new()
    og = [[bm.verts.new(outer_fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    ig = [[bm.verts.new(inner_fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((og[i][j], og[i + 1][j], og[i + 1][j + 1], og[i][j + 1]))
            bm.faces.new((ig[i][j + 1], ig[i + 1][j + 1], ig[i + 1][j], ig[i][j]))
    for i in range(nu):
        bm.faces.new((og[i][0], ig[i][0], ig[i + 1][0], og[i + 1][0]))
        bm.faces.new((og[i + 1][nv], ig[i + 1][nv], ig[i][nv], og[i][nv]))
    for j in range(nv):
        bm.faces.new((og[0][j + 1], ig[0][j + 1], ig[0][j], og[0][j]))
        bm.faces.new((og[nu][j], ig[nu][j], ig[nu][j + 1], og[nu][j + 1]))
    return _obj(name, bm)


def _edge_round(fu, fv, band=0.14):
    """0 in the middle of a sheet, rising to 1 at its edges (for rounding the rims down)."""
    e = min(fu, 1.0 - fu, fv, 1.0 - fv)
    t = max(0.0, 1.0 - e / band)
    return t * t


def _ends(t, band, drop):
    """Scale near both ends of a run (t in 0..1): 1 in the middle, 1 - drop at the very ends."""
    a = max(0.0, 1.0 - t / band)
    b = max(0.0, 1.0 - (1.0 - t) / band)
    return 1.0 - drop * (a * a + b * b)


def slab(name, frame, x0, x1, y0, y1, z0, z1, det, dome=0.0, round_=0.0012):
    """A plate in the frame's XY plane from z0 (flat underside) to z1 (top, domed, rims rounded down)."""
    nu, nv = det["grid"]

    def top(fu, fv):
        mid = math.sin(math.pi * fu) * math.sin(math.pi * fv)
        z = z1 + dome * mid - round_ * _edge_round(fu, fv)
        return frame @ V((x0 + (x1 - x0) * fu, y0 + (y1 - y0) * fv, z))

    def bot(fu, fv):
        return frame @ V((x0 + (x1 - x0) * fu, y0 + (y1 - y0) * fv, z0))

    return param_solid(name, top, bot, max(2, nu // 2), max(2, nv // 2))


# ---------------------------------------------------------------- one finger segment
def phalanx(prefix, frame, L, w, h, tip, det, hinge=True):
    """A finger segment from its knuckle (local x = 0) to the next one (x = L)."""
    pcs = []
    n, m = det["around"], det["along"]
    bev = det["bevel"]
    hw, hh = w / 2.0, h / 2.0
    rh = 0.36 * h
    # The link: a slim machined bar from knuckle to knuckle (seen in the channel between shell and pad).
    end = L + (0.20 * h if tip else 0.0)
    pcs.append(Piece(loft(prefix + "_link", frame, [(-0.1 * h, hw * 0.50, hh * 0.52, 0.0), (end, hw * 0.46, hh * 0.48, 0.0)],
                          max(6, n // 2), power=3.0), "chassis", bev if det["panels"] else 0.0))
    # The shell over the back and sides.
    x0 = 0.55 * rh
    x1 = L + 0.30 * h if tip else L - 0.05 * rh
    st = []
    steps = m + (3 if tip else 0)
    for i in range(steps + 1):
        t = i / steps
        k = (1.0 - (0.10 if tip else 0.06) * t) * _ends(t, 0.14, 0.09 if not tip else 0.0)
        if tip:
            k *= _ends(t, 0.14, 0.09) if t < 0.5 else 1.0
            if t > 0.62:
                q = (t - 0.62) / 0.38
                k *= math.sqrt(max(1.0 - 0.93 * q * q, 0.0))
        zc = -0.10 * hh * ((t - 0.62) / 0.38) ** 2 if tip and t > 0.62 else 0.0
        st.append((x0 + (x1 - x0) * t, hw * k, hh * k, zc))
    arc = 118.0 if tip else 104.0
    if det["panels"]:
        # Seams between the top plate and the side plates (HIGH only: they bake into LOW's maps).
        for a0, a1, k in ((-arc, -41.0, n // 3), (-38.0, 38.0, n // 2), (41.0, arc, n // 3)):
            pcs.append(Piece(shell(prefix + "_shell", frame, st, a0, a1, 0.095 * h, max(4, k), power=3.0), "shell", bev))
        # The floor of the seams, half a millimetre down (a seam deeper than that is lost in the bake).
        under = [(x, a - 0.0005, b - 0.0005, z) for x, a, b, z in st]
        pcs.append(Piece(shell(prefix + "_under", frame, under[1:-1], -arc + 2.0, arc - 2.0, 0.07 * h, n, power=3.0), "shell", 0.0))
    else:
        pcs.append(Piece(shell(prefix + "_shell", frame, st, -arc, arc, 0.095 * h, n, power=3.0), "shell", bev))
    # The grip pad underneath.
    p0 = 0.55 * rh + 0.08 * h
    p1 = L + 0.26 * h if tip else L - 0.45 * rh
    ps = []
    psteps = max(3, m - 1) + (2 if tip else 0)
    for i in range(psteps + 1):
        t = i / psteps
        k = _ends(t, 0.22, 0.45)
        if tip and t > 0.5:
            k = math.sqrt(max(1.0 - ((t - 0.5) / 0.5) ** 2 * 0.9, 0.0))
        ps.append((p0 + (p1 - p0) * t, w * (0.40 if tip else 0.37) * max(k, 0.3), h * (0.19 if tip else 0.15) * max(k, 0.3),
                   -h * (0.30 if tip else 0.33)))
    pcs.append(Piece(loft(prefix + "_pad", frame, ps, max(8, n - 2), power=2.6), "pad", bev if det["panels"] else 0.0))
    if hinge:
        pcs.extend(knuckle(prefix, frame, w, rh, det))
    return pcs


def knuckle(prefix, frame, w, rh, det):
    """The hinge at local x = 0: a gunmetal barrel across the finger, steel axle caps, a groove ring."""
    c = det["cyl"]
    y = frame.col[1].to_3d().normalized()
    o = frame.translation.copy()
    zh = frame.col[2].to_3d()
    pcs = [Piece(cyl(prefix + "_hinge", o - y * (w * 0.43), o + y * (w * 0.43), rh, c, z_hint=zh), "frame", det["bevel"])]
    if det["small"]:
        for s in (-1, 1):
            pcs.append(Piece(cyl(prefix + "_axle", o + y * (s * w * 0.42), o + y * (s * w * 0.475), rh * 0.46, max(6, c // 2),
                                 z_hint=zh), "steel", det["bevel"] * 0.6 if det["panels"] else 0.0))
            if det["panels"]:
                pcs.append(Piece(cyl(prefix + "_rim", o + y * (s * w * 0.30), o + y * (s * w * 0.34), rh * 1.04, c, z_hint=zh),
                                 "frame", 0.0))
    return pcs


def capsule_shell(prefix, p0, p1, r, det, z_hint=V((0, 0, 1)), key="shell"):
    """A pill-shaped shell (the thenar pad)."""
    d = V(p1) - V(p0)
    f = frame_from(p0, d, z_hint)
    L = d.length
    st = []
    for x, k in ((-0.75 * r, 0.32), (-0.55 * r, 0.72), (-0.28 * r, 0.93), (0.0, 1.0), (L * 0.5, 1.02), (L, 1.0),
                 (L + 0.28 * r, 0.93), (L + 0.55 * r, 0.72), (L + 0.75 * r, 0.32)):
        st.append((x, r * k, r * 0.86 * k, 0.0))
    return [Piece(loft(prefix, f, st, det["around"], power=2.3), key, det["bevel"])]


# ---------------------------------------------------------------- the forearm
def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def forearm(prefix, wrist, elbow, hand_join, dorsal_hint, det):
    """Wrist mechanism from the hand (`hand_join`, inside the palm) to the collar at `wrist`, then the forearm to
    `elbow` (world points)."""
    pcs = []
    n = det["around"]
    nb = max(n, 20)  # big round pieces: LOW's flat faces must stay within a millimetre of HIGH's round
    bev = det["bevel"]
    wrist, elbow, hand_join = V(wrist), V(elbow), V(hand_join)
    F = frame_from(wrist, elbow - wrist, dorsal_hint)
    Lf = (elbow - wrist).length
    ax, ay, az = F.col[0].to_3d(), F.col[1].to_3d(), F.col[2].to_3d()

    def a_at(x):  # half width across
        t = x / Lf
        return 0.0285 + 0.0145 * _smooth(t / 0.62) + 0.002 * _smooth((t - 0.62) / 0.38)

    def b_at(x):  # half height (dorsal-ventral)
        t = x / Lf
        return 0.0235 + 0.0130 * _smooth(t / 0.62) + 0.003 * _smooth((t - 0.62) / 0.38)

    # ---- wrist: the ribbed neck from the palm into the collar.
    nf = frame_from(hand_join, wrist - hand_join, az)
    nl = (wrist - hand_join).length
    pcs.append(Piece(loft(prefix + "_neck", nf, [(0.0, 0.016, 0.013, 0.0), (nl * 0.5, 0.0175, 0.0145, 0.0), (nl + 0.008, 0.021, 0.018, 0.0)],
                          max(n, 14), power=2.4), "core", bev))
    for k in range(3):
        x = nl * (0.3 + 0.25 * k)
        r = 0.016 + (0.021 - 0.016) * x / nl
        pcs.append(Piece(loft(prefix + "_rib", nf, [(x - 0.0016, r + 0.0010, r * 0.84 + 0.0010, 0.0), (x + 0.0016, r + 0.0010, r * 0.84 + 0.0010, 0.0)],
                              max(n, 14), power=2.4), "frame", bev))
    # ---- collar: a chassis band (HIGH: two, with a shallow groove), then a lit ring.
    bands = ((-0.006, 0.0032), (0.0044, 0.012)) if det["panels"] else ((-0.006, 0.012),)
    for x0, x1 in bands:
        pcs.append(Piece(loft(prefix + "_collar", F, [(x0, a_at(0.0) - 0.0005, b_at(0.0) - 0.0005, 0.0), (x1, a_at(0.0) + 0.0003, b_at(0.0) + 0.0003, 0.0)],
                              det["cyl"] + 4, power=2.6), "chassis", bev))
    if det["panels"]:
        pcs.append(Piece(loft(prefix + "_groove", F, [(0.0028, a_at(0.0) - 0.0012, b_at(0.0) - 0.0012, 0.0), (0.0048, a_at(0.0) - 0.0012, b_at(0.0) - 0.0012, 0.0)],
                              det["cyl"], power=2.6), "chassis", 0.0))
    pcs.append(Piece(loft(prefix + "_ring_glow", F, [(0.0122, a_at(0.013) - 0.0003, b_at(0.013) - 0.0003, 0.0), (0.0152, a_at(0.015) - 0.0003, b_at(0.015) - 0.0003, 0.0)],
                          det["cyl"] + 4, power=2.6), "glow", 0.0))
    # ---- core and shells.
    x_end = Lf - 0.072
    ncore = det["along"] + 3
    pcs.append(Piece(loft(prefix + "_core", F, [(0.010 + (x_end + 0.02 - 0.010) * i / ncore, a_at(0.010 + (x_end + 0.02) * i / ncore) - 0.0045,
                                                   b_at(0.010 + (x_end + 0.02) * i / ncore) - 0.0045, 0.0) for i in range(ncore + 1)],
                          nb, power=2.4), "core", 0.0))
    split = 0.44 * x_end
    for (sx0, sx1, grow) in ((0.0156, split, 0.0), (split - 0.006, x_end, 0.0013)):
        stn = []
        steps = max(3, det["along"])
        for i in range(steps + 1):
            t = i / steps
            x = sx0 + (sx1 - sx0) * t
            k = _ends(t, 0.10, 0.05)
            stn.append((x, (a_at(x) + grow) * k, (b_at(x) + grow) * k, 0.0))
        for a0, a1 in ((-76.0, 76.0), (104.0, 256.0)):
            pcs.append(Piece(shell(prefix + "_shell", F, stn, a0, a1, 0.0026, max(10, n - 2), power=2.5), "arm_shell", bev))
    # ---- side channels: a piston down each side, a lit strip on the outer one.
    for s in (-1, 1):
        def at(x, inset=0.0042):
            return wrist + ax * x + ay * (s * (a_at(x) - inset))
        pcs.append(Piece(cyl(prefix + "_piston_rod", at(0.022), at(0.14), 0.0021, max(8, det["cyl"] // 2), z_hint=az), "steel", bev * 0.6))
        pcs.append(Piece(cyl(prefix + "_piston", at(0.125, 0.0052), at(x_end - 0.02, 0.0052), 0.0040, det["cyl"], z_hint=az), "frame", bev))
        pcs.append(Piece(cyl(prefix + "_piston_cap", at(0.121, 0.0052), at(0.127, 0.0052), 0.0047, det["cyl"], z_hint=az), "frame", bev))
    gx0, gx1 = 0.03, split - 0.02
    ga = math.radians(-80.0)
    gpts = []
    for x in (gx0, gx1):
        y, z = _se(ga, 2.5)
        gpts.append(wrist + ax * x + ay * (y * (a_at(x) - 0.0016)) + az * (z * (b_at(x) - 0.0016)))
    pcs.append(Piece(loft(prefix + "_strip_glow", frame_from(gpts[0], gpts[1] - gpts[0], ay * math.sin(ga) + az * math.cos(ga)),
                          [(0.0, 0.0009, 0.0007, 0.0), ((gpts[1] - gpts[0]).length, 0.0009, 0.0007, 0.0)], 8, power=4.0), "glow", 0.0))
    # ---- the elbow: a gunmetal cuff and the suit's weave sleeve.
    pcs.append(Piece(loft(prefix + "_cuff", F, [(x_end - 0.004, a_at(x_end) + 0.0028, b_at(x_end) + 0.0028, 0.0), (x_end + 0.006, a_at(x_end) + 0.0032, b_at(x_end) + 0.0032, 0.0)],
                          nb, power=2.4), "chassis", bev))
    sl = []
    for i in range(5):
        x = x_end + 0.004 + (Lf + 0.03 - x_end) * i / 4
        sl.append((x, a_at(min(x, Lf)) + 0.0045 + 0.002 * i / 4, b_at(min(x, Lf)) + 0.0045 + 0.002 * i / 4, 0.0))
    pcs.append(Piece(loft(prefix + "_sleeve", F, sl, nb, power=2.2), "core", bev))
    return pcs


# ---------------------------------------------------------------- finishing
def finish(pieces, mats, det):
    """Material, bevel and normals on every piece; returns the objects."""
    obs = []
    for p in pieces:
        ob = p.ob
        if p.bevel > 0 and det["bseg"] > 0:
            b = ob.modifiers.new("bevel", "BEVEL")
            b.width = p.bevel
            b.segments = det["bseg"]
            b.limit_method = "ANGLE"
            b.angle_limit = math.radians(40.0)
            b.harden_normals = True
        ob.data.shade_smooth()
        if det["bseg"] == 0:
            _mark_sharp(ob, 50.0)
        wn = ob.modifiers.new("wnormal", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        ob.data.materials.append(mats[p.key])
        obs.append(ob)
    return obs


def _mark_sharp(ob, angle_deg):
    """Hard edges on an unbevelled (LOW) piece: rims sharp, the round of a loft (finer than `angle_deg`) smooth,
    so the low normals already match the high ones and the normal map only carries the fine detail."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lim = math.radians(angle_deg)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    bm.to_mesh(ob.data)
    bm.free()


def join(obs, name):
    """Applies modifiers and joins `obs` into one object."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def make_materials():
    import hardsurface as hs
    out = {}
    for key, (name, base, rough, metal, extra) in SPEC.items():
        out[key] = hs.material(name, base, rough, metal, **extra)
    return out


# ---------------------------------------------------------------- the gun-arm scripts
class _GripAdapter:
    """The pistol script's module-level grip frame as a Grip-like object."""

    def __init__(self, ns):
        self.top, self.axis, self.fwd, self.right = ns["GRIP_TOP"], ns["AXIS"], ns["FWD"], ns["RIGHT"]
        self.hd, self.hw = ns["HALF_DEPTH"], ns["HALF_WIDTH"]

    def at(self, h, theta_deg, extra):
        t = math.radians(theta_deg)
        return self.top + self.axis * h + self.fwd * ((self.hd + extra) * math.cos(t)) + self.right * ((self.hw + extra) * math.sin(t))

    def out(self, theta_deg):
        t = math.radians(theta_deg)
        return (self.fwd * math.cos(t) + self.right * math.sin(t)).normalized()


def _theta_on(g, p):
    v = V(p) - g.top
    h = v.dot(g.axis)
    r = v - g.axis * h
    e = max(r.length - (g.hd + g.hw) / 2.0, 0.0)
    return math.degrees(math.atan2(r.dot(g.right) / (g.hw + e), r.dot(g.fwd) / (g.hd + e))), h


def _wrap_near(a, ref):
    while a - ref > 180.0:
        a -= 360.0
    while a - ref < -180.0:
        a += 360.0
    return a


def _dorsal_normals(pts):
    """Per segment: the convex side of the finger's curl (the back of the finger)."""
    n_seg = len(pts) - 1
    conv = [V((0, 0, 0))] * len(pts)
    for j in range(1, len(pts) - 1):
        conv[j] = pts[j] - (pts[j - 1] + pts[j + 1]) * 0.5
    total = sum(conv, V((0, 0, 0)))
    out = []
    for i in range(n_seg):
        u = (pts[i + 1] - pts[i]).normalized()
        c = conv[i] + conv[i + 1]
        c = c - u * c.dot(u)
        if c.length < 1e-4:
            c = total - u * total.dot(u)
        if c.length < 1e-5:
            c = V((0, 0, 1)) - u * u.z
        out.append(c.normalized())
    return out


class GunArms:
    """The builders a gun-arm script poses its hands with. `ns` is the script's globals: its detail switch `D`
    (HIGH/LOW), its `PARTS` list (what build() joins) and its `Grip` class (or the pistol's module-level grip)."""

    def __init__(self, ns):
        self.ns = ns
        self.mats = make_materials()
        self.materials = list(self.mats.values())
        self.fingers = {}       # hand prefix ("R"/"L") -> [joints, ...] of the four fingers (no thumb)
        self.grip = ns["Grip"] if "Grip" in ns else None
        self.adapter = None if self.grip else _GripAdapter(ns)

    # -- helpers
    def det(self):
        return HIGH if self.ns["D"]["name"] == "high" else LOW

    def _fresh(self):
        if not self.ns["PARTS"]:
            self.fingers = {}

    def _add(self, pieces):
        det = self.det()
        obs = finish(pieces, self.mats, det)
        self.ns["PARTS"].extend(obs)
        return obs

    # -- the builders the poses call
    def finger(self, family, joints, radii):
        self._fresh()
        pts = [V(p) for p in joints]
        det = self.det()
        if "thumb" not in family:
            self.fingers.setdefault(family.split("_")[0], []).append(pts)
        normals = _dorsal_normals(pts)
        pieces = []
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            r = radii[min(i, len(radii) - 1)]
            f = frame_from(p0, p1 - p0, normals[i])
            pieces += phalanx(f"{family}_{i}", f, (p1 - p0).length, 2.1 * r, 1.92 * r, i == len(pts) - 2, det)
        self._add(pieces)
        return joints

    def metaball(self, name):
        self._fresh()
        return {"name": name}

    def capsule(self, mb, p0, p1, r):
        self._fresh()
        self._add(capsule_shell(mb["name"], V(p0), V(p1), r, self.det()))

    def palm_shell(self, name, *a, **kw):
        self._fresh()
        if a and hasattr(a[0], "at"):
            g, a = a[0], a[1:]
        else:
            g = self.adapter
        args = list(a) + [None] * (6 - len(a))
        h0, h1, t0, t1, extra, thickness = args[:6]
        bulge = kw.get("bulge", 0.004)
        det = self.det()
        prefix = name.split("_")[0]
        pieces = []
        nu, nv = det["grid"]
        # Where the knuckles are: the mean MCP angle, and which way the fingers leave the palm.
        mcps = [f[0] for f in self.fingers.get(prefix, [])]
        mid_t = (t0 + t1) / 2.0
        if mcps:
            thetas = [_wrap_near(_theta_on(g, p)[0], mid_t) for p in mcps]
            tk = sum(thetas) / len(thetas)
            nxt = [_wrap_near(_theta_on(g, f[1])[0], tk) for f in self.fingers[prefix]]
            s = 1.0 if sum(nxt) / len(nxt) > tk else -1.0
        else:
            tk, s = t0, (1.0 if t0 < t1 else -1.0) * -1.0
        # The wrist end of the palm is the end the fingers point away from.
        t_wrist = t0 if (t0 - tk) * s < (t1 - tk) * s else t1

        def mid(fu, fv):
            return math.sin(math.pi * fu) * math.sin(math.pi * fv)

        def P(fu, fv, ta, tb, ha, hb, e):
            return g.at(ha + (hb - ha) * fu, ta + (tb - ta) * fv, e)

        # The chassis: the whole palm as a pillow, its rims rounded right over (no flat end faces).
        def pillow(fu, fv):
            d = min(fu, 1.0 - fu, fv, 1.0 - fv)
            return math.sqrt(max(0.0, 1.0 - (1.0 - min(d / 0.2, 1.0)) ** 2))

        def core_out(fu, fv):
            e_in = extra - thickness + 0.0015
            e_top = extra - 0.0016 + bulge * mid(fu, fv)
            return P(fu, fv, t0, t1, h0, h1, e_in + (e_top - e_in) * (0.5 + 0.5 * pillow(fu, fv)))

        def core_in(fu, fv):
            e_in = extra - thickness + 0.0015
            e_top = extra - 0.0016 + bulge * mid(fu, fv)
            return P(fu, fv, t0, t1, h0, h1, e_in + (e_top - e_in) * (0.5 - 0.5 * pillow(fu, fv)))
        pieces.append(Piece(param_solid(name + "_core", core_out, core_in, nu + 4, nv + 2), "chassis", det["bevel"]))
        # The back of the hand: a plate over the wrist half, then a raised plate along each finger's
        # metacarpal up to the knuckle band.
        tp0 = t_wrist + (tk - t_wrist) * 0.03
        tp1 = tk - s * 8.0
        tm = tp1 + (tp0 - tp1) * 0.56
        gap_t = 1.6 * (1.0 if tp0 > tp1 else -1.0)

        def plate(pname, ta, tb, ha, hb, lift, ridge, depth=0.0026):
            def g01(fu, fv):
                return ((ha + (hb - ha) * fu) - h0) / (h1 - h0), ((ta + (tb - ta) * fv) - t0) / (t1 - t0)

            def outer(fu, fv):
                gu, gv = g01(fu, fv)
                r = ridge * math.sin(math.pi * fu) ** 0.7
                return P(fu, fv, ta, tb, ha, hb, extra + lift + bulge * mid(gu, gv) + r - 0.0017 * _edge_round(fu, fv, 0.22))

            def inner(fu, fv):
                gu, gv = g01(fu, fv)
                return P(fu, fv, ta, tb, ha, hb, extra + lift - depth + bulge * mid(gu, gv))
            pieces.append(Piece(param_solid(pname, outer, inner, max(3, nu // 2 + 1), max(3, nv // 2 + 1)), "shell", det["bevel"]))

        plate(name + "_plate", tp0, tm + gap_t, h0 + 0.003, h1 - 0.003, 0.0010, 0.0008)
        hs_m = sorted(_theta_on(g, p)[1] for p in mcps) if mcps else [h0 + (h1 - h0) * (k + 0.5) / 4 for k in range(4)]
        for k, hm_ in enumerate(hs_m):
            half = 0.0084
            ha, hb = max(h0 + 0.002, hm_ - half), min(h1 - 0.002, hm_ + half)
            plate(f"{name}_meta{k}", tm - gap_t, tp1, ha, hb, 0.0016, 0.0011, depth=0.0034)
        # A lit slit across the wrist plate.
        hc = (h0 + h1) / 2.0
        tc = tp0 + (tm - tp0) * 0.45
        e = extra + 0.0010 + bulge * mid(0.5, (tc - t0) / (t1 - t0)) + 0.0001
        e += 0.0008
        a_ = g.at(hc - 0.008, tc, e)
        b_ = g.at(hc + 0.008, tc, e)
        pieces.append(Piece(loft(name + "_slit", frame_from(a_, b_ - a_, g.out(tc)), [(0.0, 0.0010, 0.0005, 0.0), ((b_ - a_).length, 0.0010, 0.0005, 0.0)],
                                 8, power=4.0), "glow", 0.0))
        # The knuckle band, and a domed cap over each knuckle.
        tb0, tb1 = tk - s * 7.0, tk + s * 4.0

        def band_out(fu, fv):
            gu = fu
            gv = ((tb0 + (tb1 - tb0) * fv) - t0) / (t1 - t0)
            return P(fu, fv, tb0, tb1, h0 + 0.002, h1 - 0.002, extra + 0.0002 + bulge * mid(gu, gv) - 0.0012 * _edge_round(fu, fv, 0.2))

        def band_in(fu, fv):
            gv = ((tb0 + (tb1 - tb0) * fv) - t0) / (t1 - t0)
            return P(fu, fv, tb0, tb1, h0 + 0.002, h1 - 0.002, extra - 0.0035 + bulge * mid(fu, gv))
        pieces.append(Piece(param_solid(name + "_band", band_out, band_in, nu, 2), "frame", det["bevel"]))
        for k, p in enumerate(mcps):
            th, hh = _theta_on(g, p)
            th = _wrap_near(th, tk)
            gv = (th - t0) / (t1 - t0)
            gu = (hh - h0) / (h1 - h0)
            e = extra + 0.0004 + bulge * mid(min(max(gu, 0), 1), min(max(gv, 0), 1))
            c = g.at(hh, th, e)
            nrm = g.out(th)
            along = (g.at(hh, th + s * 5.0, e) - c).normalized()
            f = frame_from(c - along * 0.0055, along, nrm)
            st = [(0.0, 0.0045, 0.0012, 0.0), (0.0025, 0.0072, 0.0024, 0.0), (0.0085, 0.0074, 0.0026, 0.0), (0.011, 0.0048, 0.0012, 0.0)]
            pieces.append(Piece(loft(f"{name}_kcap{k}", f, st, det["around"], power=2.6), "shell", det["bevel"]))
        self._add(pieces)

    def arm(self, side, wrist, elbow, hand_join):
        self._fresh()
        out = V((0, -1, 0)) if str(side).startswith("R") else V((0, 1, 0))
        hint = (out + V((0, 0, 1.0))).normalized()
        det = self.det()
        obs = finish(forearm(f"{side}_arm", wrist, elbow, hand_join, hint, det), self.mats, det)
        # One object per arm, so a script that sorts pieces by their centre (the SPAS-12's pump arm) keeps it whole.
        self.ns["PARTS"].append(join(obs, f"{side}_arm"))


# ---------------------------------------------------------------- the kit hand (raw_assets/augments/actives/_kit.py)
def kit_segment(x0, L, y, z, w, h, tip):
    """A kit finger segment at its rest pivot (x0, y, z), pointing +X, back +Z: (piece objects, material names)."""
    f = Matrix.Translation(V((x0, y, z)))
    return phalanx("seg", f, L, w, h, tip, GAME)


def kit_palm(side, x0, x1, half_w, hz, fingers, thumb_mount):
    """The kit palm between x0 and x1 (wrist at the origin), `fingers` = [(y, z, w)] at x1, back +Z. Keeps the
    old envelope: the back plates top out about hz + 1.2 mm, the palm face sits at -hz - 1.5 mm (the hive's
    vent and cells sit on them)."""
    det = GAME
    pcs = []
    n = det["around"]
    I = Matrix.Identity(4)
    # Wrist knuckle: a gunmetal barrel across the wrist the hand pivots on.
    pcs.append(Piece(cyl("wrist_barrel", V((0.0, -half_w * 0.78, 0.0)), V((0.0, half_w * 0.78, 0.0)), 0.0145, det["cyl"] + 4, z_hint=V((0, 0, 1))),
                     "frame", det["bevel"]))
    # Rubber-cored body, slightly fuller under the palm (the hive's vent sits on it).
    st = []
    for xx, kw, kh in ((x0 - 0.002, 0.80, 0.80), (x0 + 0.008, 0.95, 0.96), ((x0 + x1) / 2, 1.0, 1.0), (x1 - 0.006, 0.99, 0.97), (x1 + 0.002, 0.90, 0.80)):
        st.append((xx, half_w * kw, (hz + 0.0002) * kh, -0.0012))
    pcs.append(Piece(loft("palm_core", I, st, n + 6, power=3.4), "pad", det["bevel"]))
    # Two shell plates on the back, split down the middle of the hand.
    for y0, y1 in ((0.0008, half_w - 0.003), (-half_w + 0.003, -0.0008)):
        pcs.append(Piece(slab("back_plate", I, x0 + 0.010, x1 - 0.016, y0, y1, hz - 0.0026, hz + 0.0010, det, dome=0.0006, round_=0.0014),
                         "shell", det["bevel"]))
    # Knuckle band, a lit line ahead of the plates, a domed cap over each knuckle.
    pcs.append(Piece(slab("knuckle_band", I, x1 - 0.0125, x1 + 0.0005, -half_w + 0.0015, half_w - 0.0015, hz - 0.004, hz - 0.0002, det,
                          round_=0.0010), "frame", det["bevel"]))
    pcs.append(Piece(loft("knuckle_glow", frame_from(V((x1 - 0.0148, -half_w * 0.84, hz - 0.0006)), V((0, 1, 0)), V((0, 0, 1))),
                          [(0.0, 0.0006, 0.0008, 0.0), (half_w * 1.68, 0.0006, 0.0008, 0.0)], 8, power=4.0), "glow", 0.0))
    for y, z, w in fingers:
        f = frame_from(V((x1 - 0.0115, y, hz - 0.0016)), V((1, 0, 0)), V((0, 0, 1)))
        cst = [(0.0, w * 0.26, 0.0012, 0.0), (0.0025, w * 0.42, 0.0024, 0.0), (0.0085, w * 0.43, 0.0027, 0.0), (0.0112, w * 0.28, 0.0013, 0.0)]
        pcs.append(Piece(loft("knuckle_cap", f, cst, n, power=2.6), "shell", det["bevel"]))
    # Thumb mount, and the shell over the heel of the thumb.
    a, b = thumb_mount
    pcs.append(Piece(cyl("thumb_mount", V(a), V(b), 0.0085, det["cyl"], z_hint=V((0, 0, 1))), "frame", det["bevel"]))
    heel0 = V((x0 + 0.004, side * (half_w - 0.008), -0.006))
    pcs += capsule_shell("thenar", heel0, V(a) + (V(b) - V(a)) * 0.4, 0.0105, det, z_hint=V((0, side * 1.0, -0.4)))
    return pcs


def kit_finish(pieces, piece_fn):
    """Hands the kit's own piece() each object with its kit material name."""
    out = []
    for p in pieces:
        out.append(piece_fn(p.ob, KIT_MATS[p.key], bevel=p.bevel, segments=GAME["bseg"]))
    return out
