"""The triad wardrobe: clothes, hair, hats and jewellery (owner, 2026-11-11:
"clothes they can wear that are randomly selected from a bank").

Every garment is a shell over the body (body.py): the body's surface is cut
along the garment's edges (hems, cuffs, necklines, armholes, an open front)
as zero lines of a scalar field, pushed out along the normals by how loose
the cloth is, smoothed, and kept at least a few millimetres clear of the
skin. Hems get a thickness (a rim folded inward). Collars, hoods and pockets
are extra shapes or bumps in the offset. Skin weights come from the body
under each point, so a garment bends exactly like the man inside it.

Layering: closed tops sit 4-20 mm out; open tops (the camp shirt, the
leather jacket) sit further out than any inner top, and a top's hem sits
outside the waistband of every pair of trousers, so it hangs over them.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

import common
from common import (J, V, Family, apply_mod, arm_coord, leg_coord, regions, ss, verts_np, set_verts_np,
                    field_cut, duplicate, decimate, remesh, to_mesh, cut, keep_where, all_materials, MATS,
                    ARM_LEN, UPPER_ARM_LEN, THIGH_LEN, LEG_LEN)

# Wrist end of a long sleeve (distance from the shoulder along the arm).
CUFF_S = ARM_LEN["L"] - 0.012
ANKLE_S = LEG_LEN - 0.035


def _vnormals(ob):
    return np.array([v.normal[:] for v in ob.data.vertices])


def _push_out(ob, bvh, min_off, max_push=0.015):
    """Moves vertices out along their own normals until they're `min_off`
    outside the body (by the nearest body point; at most `max_push`, so a
    point in a crease isn't thrown across to the next limb)."""
    P = verts_np(ob)
    N = _vnormals(ob)
    for _ in range(2):
        for i in range(len(P)):
            loc, nor, _, _ = bvh.find_nearest(V(P[i]))
            if loc is None:
                continue
            d = (V(P[i]) - loc).dot(nor)
            if d < min_off:
                P[i] = P[i] + N[i] * min(min_off - d, max_push)
    set_verts_np(ob, P)


def _pin_group(ob):
    """Vertex group 'free': 1 inside, 0 on open edges (smoothing leaves hems in place)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    edge = {v.index for v in bm.verts if v.is_boundary}
    bm.free()
    g = ob.vertex_groups.new(name="free")
    g.add([i for i in range(len(ob.data.vertices)) if i not in edge], 1.0, "REPLACE")
    return g


def shell(base, bvh, name, cover, offset, smooth=0, min_off=0.004, hem=0.004, mat="cloth"):
    """A garment shell from the body mesh `base`.

    cover(P) > 0 where the garment is; offset(P) = how far out (m) along the normal.
    """
    ob = duplicate(base, name)
    ob.vertex_groups.clear()
    field_cut(ob, cover)
    P = verts_np(ob)
    N = _vnormals(ob)
    set_verts_np(ob, P + N * offset(P)[:, None])
    if smooth:
        _pin_group(ob)
        apply_mod(ob, "SMOOTH", factor=0.5, iterations=smooth, vertex_group="free")
        ob.vertex_groups.remove(ob.vertex_groups["free"])
    _push_out(ob, bvh, min_off)
    if hem:
        apply_mod(ob, "SOLIDIFY", thickness=hem, offset=-1.0, use_rim=True, use_rim_only=True)
    all_materials(ob, mat)
    ob.data.shade_smooth()
    return ob


def blob_mesh(families, name, voxel, mat, smooth=2):
    ob = to_mesh(families, name)
    remesh(ob, voxel, smooth=smooth)
    all_materials(ob, mat)
    ob.data.shade_smooth()
    return ob


def join_into(dst, srcs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in srcs:
        o.select_set(True)
    dst.select_set(True)
    bpy.context.view_layer.objects.active = dst
    bpy.ops.object.join()
    return dst


def tube(name, pts, r, ring=8, closed=True, mat="metal"):
    """A round tube through points (closed loop or open)."""
    bm = bmesh.new()
    pts = [V(p) for p in pts]
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        if closed:
            d = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        else:
            d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(t) + b * math.sin(t)) * r)
                      for t in np.linspace(0, 2 * math.pi, ring, endpoint=False)])
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(ring):
            bm.faces.new((r0[k], r0[(k + 1) % ring], r1[(k + 1) % ring], r1[k]))
    if not closed:
        for rr in (rings[0], rings[-1]):
            bm.faces.new(rr if rr is rings[-1] else list(reversed(rr)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = common.new_mesh_object(name, bm)
    bm.free()
    all_materials(ob, mat)
    ob.data.shade_smooth()
    return ob


# ====================================================================== fields
def _front(y, k=0.06):
    return np.clip(-y / k, 0.0, 1.0)


def neck_field(P, r=0.075, z0=1.43, dip_front=0.0, vneck=0.0, dip_back=0.0):
    """> 0 below the neckline (crew, scoop or V)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    rho = np.sqrt(x * x + (y - 0.015) ** 2)
    fr = _front(y + 0.01)
    bk = np.clip((y - 0.01) / 0.05, 0, 1)
    zn = z0 - dip_front * fr * np.clip(1 - np.abs(x) / 0.12, 0, 1) ** 0.7 \
        - vneck * fr * np.clip(1 - np.abs(x) / 0.075, 0, 1) - dip_back * bk * np.clip(1 - np.abs(x) / 0.1, 0, 1)
    side = rho - r - 0.2 * (fr if (dip_front or vneck) else 0.0)
    return np.maximum(zn - z, side)


def top_cover(hem, sleeve, neck=None, open_gap=None, singlet=False):
    """Field for a top: torso from `hem` up to the neckline, arms down `sleeve` metres."""
    def f(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        reg = regions(P)
        torso = np.minimum(z - hem, neck(P) if neck else neck_field(P))
        out = np.where(reg["head"], -1.0, torso)
        for s in ("L", "R"):
            sa, _ = arm_coord(P, s)
            out = np.where(reg[f"arm_{s}"], (sleeve - sa) if sleeve > 0 else -1.0, out)
        if singlet:
            lim = 0.19 - 0.075 * ss((z - 1.21) / 0.13)
            out = np.minimum(out, lim - np.abs(x))
        if open_gap is not None:
            front_open = np.abs(x) - open_gap(z) + 4.0 * np.clip(y + 0.03, 0, None)
            out = np.where(reg["torso"], np.minimum(out, front_open), out)
        out = np.where(reg["leg_L"] | reg["leg_R"], np.minimum(out, z - hem), out)
        return out
    return f


def bottom_cover(waist, leg_len):
    def f(P):
        z = P[:, 2]
        reg = regions(P)
        out = np.where(reg["torso"], waist - z, -1.0)
        for s in ("L", "R"):
            sl, _ = leg_coord(P, s)
            out = np.where(reg[f"leg_{s}"], np.minimum(leg_len - sl, waist - z), out)
        return out
    return f


def _arm_s(P):
    """Distance along whichever arm is nearer, and 1 on arms / 0 elsewhere."""
    reg = regions(P)
    s = np.zeros(len(P))
    on = np.zeros(len(P))
    for side in ("L", "R"):
        sa, _ = arm_coord(P, side)
        m = reg[f"arm_{side}"]
        s[m] = sa[m]
        on[m] = 1.0
    return s, on


def _leg_s(P):
    reg = regions(P)
    s = np.zeros(len(P))
    on = np.zeros(len(P))
    for side in ("L", "R"):
        sl, _ = leg_coord(P, side)
        m = reg[f"leg_{side}"]
        s[m] = sl[m]
        on[m] = 1.0
    return s, on


def _box(P, x0, x1, z0, z1, front=True, soft=0.008):
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    k = ss((x - x0) / soft) * ss((x1 - x) / soft) * ss((z - z0) / soft) * ss((z1 - z) / soft)
    return k * (_front(y) if front else np.clip(y / 0.06, 0, 1))


# Where each shell garment is (> 0 inside; roughly the distance to its edge in metres).
def _shirt_gap(z):
    return 0.045 + 0.05 * ss((z - 1.12) / 0.26)


def _leather_gap(z):
    return 0.055 + 0.03 * ss((z - 1.2) / 0.2)


COVERS = {
    "singlet": top_cover(0.93, 0.0, neck=lambda P: neck_field(P, r=0.088, z0=1.44, dip_front=0.075, dip_back=0.02),
                         singlet=True),
    "tee": top_cover(0.895, 0.185, neck=lambda P: neck_field(P, r=0.074, z0=1.435)),
    "shirt": top_cover(0.885, 0.21, neck=lambda P: neck_field(P, r=0.08, z0=1.44, vneck=0.07)),
    "shirt_open": top_cover(0.885, 0.21, neck=lambda P: neck_field(P, r=0.082, z0=1.445), open_gap=_shirt_gap),
    "bomber": top_cover(0.9, CUFF_S, neck=lambda P: neck_field(P, r=0.078, z0=1.43)),
    "hoodie": top_cover(0.885, CUFF_S, neck=lambda P: neck_field(P, r=0.078, z0=1.44)),
    "track": top_cover(0.9, CUFF_S, neck=lambda P: neck_field(P, r=0.078, z0=1.43)),
    "leather": top_cover(0.9, CUFF_S, neck=lambda P: neck_field(P, r=0.085, z0=1.45), open_gap=_leather_gap),
    "cargo": bottom_cover(1.045, ANKLE_S),
    "jeans": bottom_cover(1.045, ANKLE_S),
    "trackpants": bottom_cover(1.045, ANKLE_S),
    "shorts": bottom_cover(1.045, THIGH_LEN + 0.05),
    "slacks": bottom_cover(1.045, ANKLE_S + 0.01),
}


# ====================================================================== tops
def rib_collar(name, z0, h, r0, r1, dy=0.016, hi=False, mat="rib"):
    """Knit band round the neck: a short tapered tube, closed on its inside."""
    bm = bmesh.new()
    n = 36 if hi else 22
    rings = []
    for z, r in ((z0 - 0.022, r0 + 0.012), (z0, r0), (z0 + h, r1), (z0 + h, r1 - 0.007), (z0 - 0.01, r0 - 0.006)):
        rings.append([bm.verts.new((r * math.cos(a), dy + r * 1.08 * math.sin(a), z))
                      for a in (2 * math.pi * i / n for i in range(n))])
    for k in range(len(rings) - 1):
        for i in range(n):
            bm.faces.new((rings[k][i], rings[k][(i + 1) % n], rings[k + 1][(i + 1) % n], rings[k + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = common.new_mesh_object(name, bm)
    bm.free()
    all_materials(ob, mat)
    ob.data.shade_smooth()
    return ob


def g_singlet(base, bvh):
    return shell(base, bvh, "w_singlet",
                 COVERS["singlet"],
                 lambda P: np.full(len(P), 0.0045), smooth=1, min_off=0.004, hem=0.003)


def g_tee(base, bvh):
    def off(P):
        s, on = _arm_s(P)
        z = P[:, 2]
        loose = 0.008 + 0.012 * ss((1.12 - z) / 0.2)                   # hangs looser toward the hem
        sleeve = 0.009 + 0.007 * ss((s - 0.06) / 0.1)                  # sleeves stand off the arm
        return np.where(on > 0, sleeve, loose)
    return shell(base, bvh, "w_tee", COVERS["tee"],
                 off, smooth=3, min_off=0.006, hem=0.003)


def g_bomber(base, bvh):
    def off(P):
        s, on = _arm_s(P)
        z = P[:, 2]
        body = 0.022 - 0.006 * ss((0.975 - z) / 0.05)                    # elastic hem pulls in
        sleeve = 0.017 - 0.011 * ss((s - (CUFF_S - 0.06)) / 0.04)       # knit cuffs
        return np.where(on > 0, sleeve, body)
    ob = shell(base, bvh, "w_bomber", COVERS["bomber"],
               off, smooth=4, min_off=0.012, hem=0.005)
    collar = rib_collar("w_bomber_collar", 1.435, 0.04, 0.094, 0.082)
    return join_into(ob, [collar])


def g_hoodie(base, bvh, hi=False):
    def off(P):
        s, on = _arm_s(P)
        z = P[:, 2]
        body = 0.022 - 0.006 * ss((0.96 - z) / 0.05)
        body = body + 0.009 * _box(P, -0.01, 0.105, 0.95, 1.1)        # kangaroo pocket
        sleeve = 0.018 - 0.012 * ss((s - (CUFF_S - 0.06)) / 0.04)
        return np.where(on > 0, sleeve, body)
    ob = shell(base, bvh, "w_hoodie", COVERS["hoodie"],
               off, smooth=4, min_off=0.012, hem=0.005)
    # The hood, down: a thick roll of cloth round the back and sides of the neck.
    f = Family("hood", 0.006)
    for a in np.linspace(-1.15, 1.15, 9):
        r = 0.105 + 0.012 * math.cos(a)
        p = (r * math.sin(a), 0.02 + r * math.cos(a) * 0.95, 1.455 + 0.035 * math.cos(a) ** 2)
        f.ball(p, 0.03 + 0.014 * math.cos(a))
    f.ellipsoid((0, 0.1, 1.42), (0.085, 0.035, 0.07))                    # the hood's back hanging down
    hood = blob_mesh([f], "w_hoodie_hood", 0.006, "cloth")
    return join_into(ob, [hood])


def g_track(base, bvh):
    def off(P):
        s, on = _arm_s(P)
        z = P[:, 2]
        body = 0.016 - 0.002 * ss((0.955 - z) / 0.04)
        sleeve = 0.012 - 0.007 * ss((s - (CUFF_S - 0.05)) / 0.035)
        return np.where(on > 0, sleeve, body)
    ob = shell(base, bvh, "w_track", COVERS["track"],
               off, smooth=3, min_off=0.01, hem=0.004)
    collar = rib_collar("w_track_collar", 1.43, 0.05, 0.09, 0.083, mat="cloth")
    return join_into(ob, [collar])


def _shirt_off(P, base_off):
    s, on = _arm_s(P)
    z = P[:, 2]
    x, y = P[:, 0], P[:, 1]
    body = base_off + 0.01 * ss((1.15 - z) / 0.2)
    # The collar rolled over along the opening and round the back of the neck.
    rho = np.sqrt(x * x + (y - 0.015) ** 2)
    collar = 0.007 * ss((z - 1.37) / 0.03) * ss((0.12 - rho) / 0.03)
    sleeve = base_off + 0.006 + 0.014 * ss((s - 0.06) / 0.12)
    return np.where(on > 0, sleeve, body + collar)


def g_shirt(base, bvh):
    """Short-sleeved camp shirt, buttoned up to the second button."""
    return shell(base, bvh, "w_shirt",
                 COVERS["shirt"],
                 lambda P: _shirt_off(P, 0.012), smooth=3, min_off=0.009, hem=0.004)


def g_shirt_open(base, bvh):
    """The same shirt worn open over a singlet or bare chest."""
    return shell(base, bvh, "w_shirt_open", COVERS["shirt_open"],
                 lambda P: _shirt_off(P, 0.016), smooth=3, min_off=0.013, hem=0.004)


def g_leather(base, bvh):
    """Open leather jacket (worn over a tee or a singlet)."""
    def off(P):
        s, on = _arm_s(P)
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        rho = np.sqrt(x * x + (y - 0.015) ** 2)
        lapel = 0.01 * ss((z - 1.25) / 0.06) * ss((0.15 - np.abs(x)) / 0.03) * _front(y) \
            + 0.012 * ss((z - 1.4) / 0.03) * ss((0.115 - rho) / 0.02)
        body = 0.023 + lapel
        sleeve = 0.025 - 0.004 * ss((s - (CUFF_S - 0.05)) / 0.04)
        return np.where(on > 0, sleeve, body)
    return shell(base, bvh, "w_leather", COVERS["leather"],
                 off, smooth=3, min_off=0.02, hem=0.005, mat="leather")


# ====================================================================== bottoms
def g_cargo(base, bvh):
    def off(P):
        s, on = _leg_s(P)
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        pocket = np.zeros(len(P))
        for side in ("L", "R"):
            sl, _ = leg_coord(P, side)
            outer = np.clip((np.abs(x) - 0.115) / 0.02, 0, 1)
            pocket += 0.009 * ss((sl - 0.2) / 0.015) * ss((0.42 - sl) / 0.015) * outer * (np.sign(x) == (1 if side == "L" else -1))
        leg = 0.012 + pocket - 0.004 * ss((s - (ANKLE_S - 0.06)) / 0.04)
        waist = 0.007
        return np.where(on > 0, np.minimum(leg, 0.007 + 0.006 * ss((0.98 - z) / 0.08) + pocket), waist)
    return shell(base, bvh, "w_cargo", COVERS["cargo"], off, smooth=3, min_off=0.006, hem=0.004)


def g_jeans(base, bvh):
    def off(P):
        s, on = _leg_s(P)
        z = P[:, 2]
        belt = 0.003 * ss((z - 1.005) / 0.006) * ss((1.04 - z) / 0.006)
        leg = 0.0065 + 0.003 * ss((s - 0.3) / 0.15)
        return np.where(on > 0, leg, 0.006) + belt
    return shell(base, bvh, "w_jeans", COVERS["jeans"], off, smooth=2, min_off=0.005, hem=0.004)


def g_trackpants(base, bvh):
    def off(P):
        s, on = _leg_s(P)
        leg = 0.011 - 0.007 * ss((s - (ANKLE_S - 0.05)) / 0.035)
        return np.where(on > 0, leg, 0.007)
    return shell(base, bvh, "w_trackpants", COVERS["trackpants"], off, smooth=3, min_off=0.005, hem=0.003)


def g_shorts(base, bvh):
    def off(P):
        s, on = _leg_s(P)
        x = P[:, 0]
        pocket = 0.008 * ss((s - 0.2) / 0.015) * ss((0.38 - s) / 0.015) * np.clip((np.abs(x) - 0.115) / 0.02, 0, 1)
        leg = 0.012 + 0.01 * ss((s - 0.15) / 0.2) + pocket
        return np.where(on > 0, leg, 0.007)
    return shell(base, bvh, "w_shorts", COVERS["shorts"], off, smooth=3, min_off=0.006,
                 hem=0.004)


def g_slacks(base, bvh):
    def off(P):
        s, on = _leg_s(P)
        z = P[:, 2]
        belt = 0.003 * ss((z - 1.005) / 0.006) * ss((1.04 - z) / 0.006)
        return np.where(on > 0, 0.009 + 0.004 * ss((s - 0.35) / 0.2), 0.006) + belt
    return shell(base, bvh, "w_slacks", COVERS["slacks"], off, smooth=3, min_off=0.005, hem=0.004)


# ====================================================================== shoes
def _shoe(s, kind, hi):
    sx = 1.0 if s == "L" else -1.0
    x = J[f"ankle.{s}"].x
    res = 0.004 if hi else 0.0055
    f = Family(f"{kind}{s}", res)
    if kind == "sneaker":
        f.ellipsoid((x, 0.03, 0.045), (0.044, 0.05, 0.05))               # heel
        f.ellipsoid((x + 0.004 * sx, -0.045, 0.04), (0.047, 0.065, 0.04))  # midfoot
        f.ellipsoid((x + 0.006 * sx, -0.12, 0.032), (0.043, 0.045, 0.03))  # toe box
        f.capsule((x, 0.02, 0.06), (x, 0.022, 0.135), 0.048)              # ankle collar
        top = 0.14
    else:
        f.ellipsoid((x, 0.032, 0.05), (0.047, 0.055, 0.055))
        f.ellipsoid((x + 0.004 * sx, -0.045, 0.045), (0.05, 0.068, 0.045))
        f.ellipsoid((x + 0.006 * sx, -0.122, 0.036), (0.046, 0.048, 0.034))
        f.capsule((x, 0.018, 0.06), (x, 0.02, 0.2), 0.05)                 # shaft
        top = 0.2
    ob = to_mesh([f], f"{kind}_{s}")
    remesh(ob, 0.004 if hi else 0.0055, smooth=2)
    cut(ob, (0, 0, 0.0), (0, 0, 1), fill=True, fill_mat=0)
    cut(ob, (0, 0, top), (0, 0, -1))
    all_materials(ob, "shoes")
    ob.data.shade_smooth()
    return ob


def g_sneakers(base, bvh):
    a, b = _shoe("L", "sneaker", False), _shoe("R", "sneaker", False)
    a.name = "w_sneakers"
    return join_into(a, [b])


def g_boots(base, bvh):
    a, b = _shoe("L", "boot", False), _shoe("R", "boot", False)
    a.name = "w_boots"
    return join_into(a, [b])


# ====================================================================== hair, hats
def _hairline(fade_back=0.07):
    """Field > 0 above the hairline (a clean cut, not a zig-zag of whole faces)."""
    def field(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        front = ss((-y - 0.03) / 0.05)
        back = ss((y - 0.03) / 0.07)
        center = 1.0 - ss((np.abs(x) - 0.03) / 0.035)
        return z - (1.69 + front * (0.02 + 0.028 * center) - back * fade_back)
    return field


def g_hair_fade(base, bvh):
    f = Family("hair", 0.004)
    f.ellipsoid((0, 0.009, 1.688), (0.081, 0.099, 0.0935))
    f.ellipsoid((0, 0.03, 1.66), (0.079, 0.09, 0.07))
    ob = blob_mesh([f], "w_hair_fade", 0.004, "hair", smooth=0)
    field_cut(ob, _hairline())
    return ob


def g_hair_slick(base, bvh):
    """Slicked back, longer on top, tied in a small knot at the back."""
    f = Family("hair", 0.004)
    f.ellipsoid((0, 0.012, 1.692), (0.082, 0.102, 0.097))
    f.ellipsoid((0, 0.03, 1.665), (0.08, 0.092, 0.072))
    f.ellipsoid((0, 0.02, 1.735), (0.06, 0.09, 0.05))
    f.ball((0, 0.095, 1.735), 0.024)                                      # the knot
    ob = blob_mesh([f], "w_hair_slick", 0.004, "hair", smooth=1)
    field_cut(ob, _hairline(0.05))
    return ob


def g_hair_spiky(base, bvh):
    f = Family("hair", 0.0035)
    f.ellipsoid((0, 0.009, 1.688), (0.081, 0.099, 0.0935))
    f.ellipsoid((0, 0.03, 1.66), (0.079, 0.09, 0.07))
    rng = np.random.default_rng(7)
    for _ in range(26):
        th = rng.uniform(0, 2 * math.pi)
        ph = rng.uniform(0.0, 0.85)
        d = V((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th) * 1.15 - 0.15 * math.sin(ph), math.cos(ph)))
        base_p = V((0, 0.012, 1.665)) + V((d.x * 0.08, d.y * 0.095, d.z * 0.09))
        f.capsule(base_p, base_p + d * rng.uniform(0.018, 0.03) + V((0, 0.01, 0)), 0.0095)
    ob = blob_mesh([f], "w_hair_spiky", 0.0035, "hair", smooth=1)
    field_cut(ob, _hairline(0.075))
    return ob


def g_hair_buzz(base, bvh):
    f = Family("hair", 0.004)
    f.ellipsoid((0, 0.012, 1.686), (0.0765, 0.0945, 0.0925))
    f.ellipsoid((0, 0.03, 1.66), (0.0755, 0.087, 0.067))
    ob = blob_mesh([f], "w_hair_buzz", 0.004, "hair", smooth=0)
    field_cut(ob, _hairline(0.08))
    return ob


def g_cap(base, bvh):
    """Baseball cap: crown and a curved brim."""
    f = Family("cap", 0.004)
    f.ellipsoid((0, 0.008, 1.7), (0.088, 0.104, 0.092))
    crown = blob_mesh([f], "w_cap", 0.004, "cloth", smooth=1)
    cut(crown, (0, 0, 1.676), (0, 0, 1))
    cut(crown, (0, -0.06, 1.70), (0, 0.4, 1), fill=False)  # sits on the forehead, low at the back
    bm = bmesh.new()
    rows, cols = 6, 14
    grid = []
    for i in range(rows + 1):
        t = i / rows
        row = []
        for k in range(cols + 1):
            a = math.radians(-70 + 140 * k / cols)
            r = 0.084 + 0.078 * t * (0.55 + 0.45 * math.cos(a))
            x = r * math.sin(a)
            y = -0.012 - r * math.cos(a)
            # From under the crown's front edge, out and a little down, curved at the sides.
            z = 1.716 - 0.014 * t - 0.006 * t * t - 0.01 * abs(math.sin(a)) * t
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for i in range(rows):
        for k in range(cols):
            bm.faces.new((grid[i][k], grid[i][k + 1], grid[i + 1][k + 1], grid[i + 1][k]))
    brim = common.new_mesh_object("w_cap_brim", bm)
    bm.free()
    apply_mod(brim, "SOLIDIFY", thickness=0.005, offset=0.0)
    all_materials(brim, "cloth")
    brim.data.shade_smooth()
    return join_into(crown, [brim])


def g_beanie(base, bvh):
    f = Family("beanie", 0.004)
    f.ellipsoid((0, 0.01, 1.7), (0.087, 0.104, 0.1))
    f.ellipsoid((0, 0.02, 1.665), (0.088, 0.1, 0.03))   # turned-up band
    ob = blob_mesh([f], "w_beanie", 0.004, "rib", smooth=1)
    cut(ob, (0, 0, 1.652), (0, 0, 1))
    cut(ob, (0, -0.07, 1.682), (0, 0.5, 1))
    return ob


# ====================================================================== accessories
def g_glasses(base, bvh):
    """Sunglasses: two dark lenses, a bridge, arms back to the ears."""
    from body import EYE
    parts = []
    for s, sx in (("L", 1), ("R", -1)):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=6, radius=1.0)
        for v in bm.verts:
            # A rounded-rectangle lens (superellipse), wrapping round toward the temple.
            ang = math.atan2(v.co.z, v.co.x)
            k = (abs(math.cos(ang)) ** 4 + abs(math.sin(ang)) ** 4) ** -0.25
            r = math.hypot(v.co.x, v.co.z)
            lx, lz = math.cos(ang) * r * k * 0.027, math.sin(ang) * r * k * 0.0155
            v.co = V((lx, v.co.y * 0.004 + 0.12 * (lx * sx) ** 2 * 10, lz))
            v.co = Matrix.Rotation(math.radians(-12 * sx), 3, "Z") @ v.co + EYE[s] + V((0.004 * sx, -0.023, 0.003))
        lens = common.new_mesh_object(f"lens_{s}", bm)
        bm.free()
        all_materials(lens, "lens")
        parts.append(lens)
        e = EYE[s]
        parts.append(tube(f"arm_{s}", [e + V((0.024 * sx, -0.018, 0.006)), V((0.074 * sx, -0.04, 1.674)),
                                      V((0.08 * sx, 0.0, 1.672)), V((0.078 * sx, 0.014, 1.66))], 0.0022, 5, False))
    parts.append(tube("bridge", [EYE["R"] + V((0.018, -0.026, 0.008)), V((0, -0.11, 1.678)),
                                 EYE["L"] + V((-0.018, -0.026, 0.008))], 0.0022, 5, False))
    ob = parts[0]
    ob.name = "w_glasses"
    join_into(ob, parts[1:])
    return ob


def g_chain(base, bvh):
    """Heavy gold chain round the neck, lying on the collarbones."""
    pts = []
    for a in np.linspace(0, 2 * math.pi, 40, endpoint=False):
        x = 0.072 * math.sin(a)
        y = 0.018 - 0.072 * math.cos(a) * (1.25 if math.cos(a) > 0 else 0.95)
        z = 1.445 - 0.055 * max(0.0, math.cos(a)) ** 2.2
        pts.append((x, y, z))
    # Sit it on the surface (the body, or a little above whatever it's worn over).
    out = []
    for p in pts:
        loc, nor, _, _ = bvh.find_nearest(V(p))
        out.append(loc + nor * 0.012)
    return tube("w_chain", out, 0.0042, 6, True, mat="metal")


def g_watch(base, bvh):
    """Steel or gold watch on the left wrist, face up."""
    s = "L"
    el, wr = J[f"elbow.{s}"], J[f"wrist.{s}"]
    ax = (wr - el).normalized()
    c = wr - ax * 0.035
    a = ax.orthogonal().normalized()
    b = ax.cross(a)
    ring = []
    for t in np.linspace(0, 2 * math.pi, 16, endpoint=False):
        p = c + (a * math.cos(t) + b * math.sin(t)) * 0.05
        loc, nor, _, _ = bvh.find_nearest(p)
        ring.append(loc + nor * 0.004)
    band = tube("w_watch", ring, 0.0045, 6, True, mat="metal")
    # The case on the back of the wrist (the hand's back faces the hand bone's +Z).
    top = c + (a * 0.0 + b * 0.0)
    loc, nor, _, _ = bvh.find_nearest(c + V((0.0, 0.0, 0.08)))
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.016, radius2=0.015, depth=0.008)
    rot = V((0, 0, 1)).rotation_difference(nor).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc + nor * 0.008) @ rot, verts=bm.verts)
    case = common.new_mesh_object("watch_case", bm)
    bm.free()
    all_materials(case, "metal")
    return join_into(band, [case])


# ====================================================================== plate carrier
def build_vest():
    f = Family("vest", 0.009)
    f.ellipsoid((0, -0.012, 1.25), (0.2, 0.15, 0.17))
    f.ellipsoid((0, -0.02, 1.09), (0.188, 0.142, 0.07))
    ob = to_mesh([f], "vest")
    remesh(ob, 0.009, smooth=2)

    def keep(p):
        if p.z < 1.0 or p.z > 1.45:
            return False
        side = abs(p.x) > 0.16 and abs(p.y + 0.01) < 0.06
        armhole = abs(p.x) > 0.115 and p.z > 1.34 and abs(p.y + 0.01) < 0.12
        strap = abs(abs(p.x) - 0.1) < 0.03
        return not side and (not armhole or strap)
    keep_where(ob, keep)
    apply_mod(ob, "SOLIDIFY", thickness=0.012, offset=1.0)
    all_materials(ob, "vest")
    ob.data.shade_smooth()
    return ob


# ====================================================================== the bank
# id -> (builder, slot, LOW triangle budget). Slots: top (worn alone or over an
# inner), inner (under an open top), bottom, shoes, hair, hat, glasses, neck, wrist.
GARMENTS = {
    "singlet": (g_singlet, "inner", 1300),
    "tee": (g_tee, "inner", 1700),
    "shirt": (g_shirt, "top", 1900),
    "shirt_open": (g_shirt_open, "top", 1900),
    "bomber": (g_bomber, "top", 2300),
    "hoodie": (g_hoodie, "top", 2500),
    "track": (g_track, "top", 2100),
    "leather": (g_leather, "top", 2300),
    "cargo": (g_cargo, "bottom", 1800),
    "jeans": (g_jeans, "bottom", 1500),
    "trackpants": (g_trackpants, "bottom", 1500),
    "shorts": (g_shorts, "bottom", 1200),
    "slacks": (g_slacks, "bottom", 1500),
    "sneakers": (g_sneakers, "shoes", 720),
    "boots": (g_boots, "shoes", 820),
    "hair_fade": (g_hair_fade, "hair", 700),
    "hair_slick": (g_hair_slick, "hair", 800),
    "hair_spiky": (g_hair_spiky, "hair", 900),
    "hair_buzz": (g_hair_buzz, "hair", 500),
    "cap": (g_cap, "hat", 600),
    "beanie": (g_beanie, "hat", 550),
    "glasses": (g_glasses, "glasses", 300),
    "chain": (g_chain, "neck", 240),
    "watch": (g_watch, "wrist", 200),
}


def build_garment(gid, base, bvh):
    fn, slot, budget = GARMENTS[gid]
    ob = fn(base, bvh)
    ob.name = "w_" + gid
    ob.data.name = "w_" + gid
    decimate(ob, budget)
    ob.data.shade_smooth()
    ob["slot"] = slot
    return ob
