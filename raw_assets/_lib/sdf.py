"""Signed-distance sculpting for generator scripts (CLAUDE.md §7).

Shapes are signed distance fields evaluated with numpy on a regular grid and
meshed with surface nets (one vertex per surface cell, one quad per crossing
grid edge), which gives even, all-quad meshes that bake and decimate well.

    g = sdf.Grid(lo, hi, h)                     # metres
    m = sdf.Model()
    m.add(sdf.RoundCone(a, b, ra, rb), k=0.02)  # smooth union
    m.sub(sdf.Sphere(c, r), k=0.004)            # smooth subtraction
    m.fn(aabb_lo, aabb_hi, lambda f, x, y, z: f + ...)   # local displacement
    F = m.evaluate(g)
    me = sdf.to_mesh("name", F, g)

Every operation only touches the grid block inside its bounding box (plus the
blend radius), so a model with a hundred shapes evaluates in seconds.
Blender: +Z up, the character faces -Y.
"""
import math

import numpy as np

F32 = np.float32


# ---------------------------------------------------------------------- blends
def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def cmax(a, b, r):
    """Hard intersection with a 45-degree chamfer of size r on the edge."""
    m = np.maximum(a, b)
    if r <= 0:
        return m
    return np.maximum(m, (a + b + r) * F32(math.sqrt(0.5)))


def cmin(a, b, r):
    """Hard union with a 45-degree fillet-like chamfer of size r."""
    return -cmax(-a, -b, r)


def ss(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------- frames
def frame(x_axis, up_hint=(0.0, 0.0, 1.0)):
    """3x3 rotation (columns = local axes in world) with local X along `x_axis`."""
    x = np.asarray(x_axis, float)
    x = x / np.linalg.norm(x)
    u = np.asarray(up_hint, float)
    if abs(np.dot(u, x)) > 0.95:
        u = np.array((0.0, 1.0, 0.0)) if abs(x[1]) < 0.9 else np.array((1.0, 0.0, 0.0))
    y = np.cross(u, x)
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    return np.stack([x, y, z], 1)


def rot(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = math.radians(deg)
    K = np.array(((0, -a[2], a[1]), (a[2], 0, -a[0]), (-a[1], a[0], 0)))
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def _local(R, c, x, y, z):
    px, py, pz = x - F32(c[0]), y - F32(c[1]), z - F32(c[2])
    if R is None:
        return px, py, pz
    R = np.asarray(R, float)
    return (px * F32(R[0, 0]) + py * F32(R[1, 0]) + pz * F32(R[2, 0]),
            px * F32(R[0, 1]) + py * F32(R[1, 1]) + pz * F32(R[2, 1]),
            px * F32(R[0, 2]) + py * F32(R[1, 2]) + pz * F32(R[2, 2]))


# ---------------------------------------------------------------------- primitives
class Prim:
    def aabb(self):
        raise NotImplementedError

    def __call__(self, x, y, z):
        raise NotImplementedError


class Sphere(Prim):
    def __init__(self, c, r):
        self.c, self.r = np.asarray(c, float), float(r)

    def aabb(self):
        return self.c - self.r, self.c + self.r

    def __call__(self, x, y, z):
        px, py, pz = _local(None, self.c, x, y, z)
        return np.sqrt(px * px + py * py + pz * pz) - F32(self.r)


class Ellipsoid(Prim):
    """Radii along the local axes of R (columns); approximate distance (iq)."""

    def __init__(self, c, radii, R=None):
        self.c, self.r, self.R = np.asarray(c, float), np.asarray(radii, float), R

    def aabb(self):
        m = self.r.max()
        return self.c - m, self.c + m

    def __call__(self, x, y, z):
        qx, qy, qz = _local(self.R, self.c, x, y, z)
        rx, ry, rz = (F32(v) for v in self.r)
        k0 = np.sqrt((qx / rx) ** 2 + (qy / ry) ** 2 + (qz / rz) ** 2)
        k1 = np.sqrt((qx / (rx * rx)) ** 2 + (qy / (ry * ry)) ** 2 + (qz / (rz * rz)) ** 2)
        return k0 * (k0 - 1.0) / np.maximum(k1, F32(1e-9))


class RoundCone(Prim):
    """Capsule from a (radius ra) to b (radius rb); exact (iq)."""

    def __init__(self, a, b, ra, rb):
        self.a, self.b = np.asarray(a, float), np.asarray(b, float)
        self.ra, self.rb = float(ra), float(rb)

    def aabb(self):
        r = max(self.ra, self.rb)
        return np.minimum(self.a, self.b) - r, np.maximum(self.a, self.b) + r

    def __call__(self, x, y, z):
        ba = self.b - self.a
        l2 = float(ba @ ba)
        rr = self.ra - self.rb
        a2 = l2 - rr * rr
        il2 = 1.0 / l2
        px, py, pz = x - F32(self.a[0]), y - F32(self.a[1]), z - F32(self.a[2])
        yv = px * F32(ba[0]) + py * F32(ba[1]) + pz * F32(ba[2])
        zv = yv - F32(l2)
        qx = px * F32(l2) - F32(ba[0]) * yv
        qy = py * F32(l2) - F32(ba[1]) * yv
        qz = pz * F32(l2) - F32(ba[2]) * yv
        x2 = qx * qx + qy * qy + qz * qz
        y2 = yv * yv * F32(l2)
        z2 = zv * zv * F32(l2)
        k = F32(math.copysign(1.0, rr) * rr * rr) * x2
        d_tip = np.sqrt(x2 + z2) * F32(il2) - F32(self.rb)
        d_base = np.sqrt(x2 + y2) * F32(il2) - F32(self.ra)
        d_side = (np.sqrt(x2 * F32(a2 * il2)) + yv * F32(rr)) * F32(il2) - F32(self.ra)
        return np.where(np.sign(zv) * F32(a2) * z2 > k, d_tip,
                        np.where(np.sign(yv) * F32(a2) * y2 < k, d_base, d_side))


class RoundBox(Prim):
    def __init__(self, c, half, R=None, r=0.0):
        self.c, self.h, self.R, self.r = np.asarray(c, float), np.asarray(half, float), R, float(r)

    def aabb(self):
        R = np.eye(3) if self.R is None else np.asarray(self.R, float)
        ext = np.abs(R) @ self.h
        return self.c - ext, self.c + ext

    def __call__(self, x, y, z):
        qx, qy, qz = _local(self.R, self.c, x, y, z)
        r = F32(self.r)
        dx = np.abs(qx) - F32(self.h[0] - self.r)
        dy = np.abs(qy) - F32(self.h[1] - self.r)
        dz = np.abs(qz) - F32(self.h[2] - self.r)
        out = np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2 + np.maximum(dz, 0) ** 2)
        inside = np.minimum(np.maximum(dx, np.maximum(dy, dz)), 0)
        return out + inside - r


class Plane(Prim):
    """Positive on the side `n` points to."""

    def __init__(self, p, n):
        n = np.asarray(n, float)
        self.n = n / np.linalg.norm(n)
        self.p = np.asarray(p, float)

    def __call__(self, x, y, z):
        return ((x - F32(self.p[0])) * F32(self.n[0]) + (y - F32(self.p[1])) * F32(self.n[1])
                + (z - F32(self.p[2])) * F32(self.n[2]))


def plane_mx(p, n):
    """Plane mirrored across x = 0 (uses |x|): one call makes both sides."""
    pl = Plane(p, n)

    def f(x, y, z):
        return pl(np.abs(x), y, z)
    return f


# ---------------------------------------------------------------------- grid
class Grid:
    def __init__(self, lo, hi, h):
        self.lo = np.asarray(lo, float)
        self.h = float(h)
        self.shape = tuple(int(math.ceil((hi[i] - lo[i]) / h)) + 1 for i in range(3))
        self.axes = [(self.lo[i] + np.arange(self.shape[i]) * h).astype(F32) for i in range(3)]

    def block(self, bmin, bmax):
        sl = []
        for i in range(3):
            i0 = max(0, int(math.floor((bmin[i] - self.lo[i]) / self.h)))
            i1 = min(self.shape[i], int(math.ceil((bmax[i] - self.lo[i]) / self.h)) + 1)
            if i1 <= i0:
                return None
            sl.append(slice(i0, i1))
        return tuple(sl)

    def coords(self, sl=None):
        if sl is None:
            sl = (slice(None),) * 3
        return (self.axes[0][sl[0]][:, None, None], self.axes[1][sl[1]][None, :, None],
                self.axes[2][sl[2]][None, None, :])

    @property
    def size(self):
        return self.shape[0] * self.shape[1] * self.shape[2]


class Model:
    """An ordered list of field operations, evaluable on any grid."""

    def __init__(self):
        self.ops = []

    def add(self, prim, k=0.0):
        self.ops.append(("add", prim, k))
        return prim

    def sub(self, prim, k=0.0):
        self.ops.append(("sub", prim, k))
        return prim

    def fn(self, lo, hi, f):
        """f(field_block, x, y, z) -> new field block, applied inside the box lo..hi."""
        self.ops.append(("fn", (np.asarray(lo, float), np.asarray(hi, float)), f))

    def evaluate_points(self, P, far=1.0):
        """The field at points P (N, 3)."""
        P = np.asarray(P, dtype=F32)
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        F = np.full(len(P), F32(far), dtype=F32)
        for kind, prim, k in self.ops:
            if kind == "fn":
                lo, hi = prim
                m = np.all((P >= lo) & (P <= hi), 1)
                if m.any():
                    F[m] = k(F[m], x[m], y[m], z[m]).astype(F32)
                continue
            lo, hi = prim.aabb()
            mg = k + 0.004
            m = np.all((P >= lo - mg) & (P <= hi + mg), 1)
            if not m.any():
                continue
            d = prim(x[m], y[m], z[m])
            F[m] = smin(F[m], d, k) if kind == "add" else smax(F[m], -d, k)
        return F

    def copy(self):
        m = Model()
        m.ops = list(self.ops)
        return m

    def evaluate(self, grid, far=1.0):
        F = np.full(grid.shape, F32(far), dtype=F32)
        for kind, prim, k in self.ops:
            if kind == "fn":
                lo, hi = prim
                sl = grid.block(lo, hi)
                if sl is None:
                    continue
                F[sl] = k(F[sl], *grid.coords(sl)).astype(F32)
                continue
            lo, hi = prim.aabb()
            m = k + 2 * grid.h + 0.002
            sl = grid.block(lo - m, hi + m)
            if sl is None:
                continue
            d = prim(*grid.coords(sl))
            if kind == "add":
                F[sl] = smin(F[sl], d, k)
            else:
                F[sl] = smax(F[sl], -d, k)
        return F


# ---------------------------------------------------------------------- meshing
_CORNERS = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)])
_EDGES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]


def surface_nets(F, grid, sharp=True, reg=0.04):
    """Returns (verts (N,3) float64 world, quads (M,4) int64), outward-facing.

    sharp: place each cell's vertex at the least-squares intersection of the
    tangent planes at its edge crossings (dual contouring's QEF, regularised
    toward the mean crossing point by `reg`), which keeps hard edges and
    corners crisp instead of stair-stepping them."""
    s = F < 0
    nx, ny, nz = F.shape
    cs = (nx - 1, ny - 1, nz - 1)
    any_in = np.zeros(cs, bool)
    all_in = np.ones(cs, bool)
    for a, b, c in _CORNERS:
        v = s[a:a + cs[0], b:b + cs[1], c:c + cs[2]]
        any_in |= v
        all_in &= v
    active = any_in & ~all_in
    del any_in, all_in
    idx = np.flatnonzero(active)
    del active
    ci, cj, ck = np.unravel_index(idx, cs)
    vals = np.stack([F[ci + a, cj + b, ck + c] for a, b, c in _CORNERS], 1).astype(np.float64)
    acc = np.zeros((len(idx), 3))
    cnt = np.zeros(len(idx))
    cpos = _CORNERS.astype(float)
    for e0, e1 in _EDGES:
        v0, v1 = vals[:, e0], vals[:, e1]
        m = (v0 < 0) != (v1 < 0)
        t = np.where(m, v0 / np.where(m, v0 - v1, 1.0), 0.0)
        acc += (cpos[e0] + t[:, None] * (cpos[e1] - cpos[e0])) * m[:, None]
        cnt += m
    local = acc / np.maximum(cnt, 1)[:, None]
    if sharp:
        local = _qef(F, ci, cj, ck, vals, local, reg)
    verts = grid.lo + (np.stack([ci, cj, ck], 1) + local) * grid.h

    def vid(i, j, k):
        return np.searchsorted(idx, np.ravel_multi_index((i, j, k), cs))

    quads = []
    # x edges: cells (i, j-1..j, k-1..k); (y, z) order gives +x normals.
    e = s[:-1, 1:-1, 1:-1] != s[1:, 1:-1, 1:-1]
    i, j, k = np.nonzero(e)
    j, k = j + 1, k + 1
    q = np.stack([vid(i, j - 1, k - 1), vid(i, j, k - 1), vid(i, j, k), vid(i, j - 1, k)], 1)
    flip = ~s[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    # y edges: cells (i-1..i, j, k-1..k); (z, x) order gives +y normals.
    e = s[1:-1, :-1, 1:-1] != s[1:-1, 1:, 1:-1]
    i, j, k = np.nonzero(e)
    i, k = i + 1, k + 1
    q = np.stack([vid(i - 1, j, k - 1), vid(i - 1, j, k), vid(i, j, k), vid(i, j, k - 1)], 1)
    flip = ~s[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    # z edges: cells (i-1..i, j-1..j, k); (x, y) order gives +z normals.
    e = s[1:-1, 1:-1, :-1] != s[1:-1, 1:-1, 1:]
    i, j, k = np.nonzero(e)
    i, j = i + 1, j + 1
    q = np.stack([vid(i - 1, j - 1, k), vid(i, j - 1, k), vid(i, j, k), vid(i - 1, j, k)], 1)
    flip = ~s[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    return verts, np.concatenate(quads, 0)


def _qef(F, ci, cj, ck, vals, mass, reg):
    nx, ny, nz = F.shape

    def grad(i, j, k):
        g = np.empty((len(i), 3))
        g[:, 0] = F[np.minimum(i + 1, nx - 1), j, k] - F[np.maximum(i - 1, 0), j, k]
        g[:, 1] = F[i, np.minimum(j + 1, ny - 1), k] - F[i, np.maximum(j - 1, 0), k]
        g[:, 2] = F[i, j, np.minimum(k + 1, nz - 1)] - F[i, j, np.maximum(k - 1, 0)]
        return g

    G = [grad(ci + a, cj + b, ck + c) for a, b, c in _CORNERS]
    cpos = _CORNERS.astype(float)
    ata = np.zeros((len(ci), 3, 3))
    atb = np.zeros((len(ci), 3))
    for e0, e1 in _EDGES:
        v0, v1 = vals[:, e0], vals[:, e1]
        m = (v0 < 0) != (v1 < 0)
        t = np.where(m, v0 / np.where(m, v0 - v1, 1.0), 0.0)
        p = cpos[e0] + t[:, None] * (cpos[e1] - cpos[e0])
        n = G[e0] * (1 - t)[:, None] + G[e1] * t[:, None]
        ln = np.linalg.norm(n, axis=1)
        n = n / np.where(ln > 1e-12, ln, 1.0)[:, None] * m[:, None]
        ata += n[:, :, None] * n[:, None, :]
        atb += n * np.sum(n * p, axis=1)[:, None]
    ata += reg * np.eye(3)[None]
    atb += reg * mass
    x = np.linalg.solve(ata, atb[:, :, None])[:, :, 0]
    return np.clip(x, 0.0, 1.0)


def to_mesh(name, F, grid):
    """Surface-nets mesh of the field as a new bpy mesh datablock."""
    import bpy
    verts, quads = surface_nets(F, grid)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", np.arange(0, quads.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    return me
