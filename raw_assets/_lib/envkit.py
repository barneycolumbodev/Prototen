"""Environment kit: builds level geometry for the world texture array shader.

A level generator calls primitives (box, quad, cylinder, lathe, tube, prism,
extrusion, sign, bpy objects such as neon text) on a `Kit`. Every face carries:

  layer   texture-array layer (raw_assets/env/materials -> materials.json)
  tint    RGB multiplied by 2 in the shader (0.5 grey = unchanged)
  emit    emission strength (0 = none); the albedo alpha masks where it glows
  wet     1 for outdoor surfaces that rain reaches (puddles, darker, glossier)
  detail  small props go to a separate mesh per chunk with a draw distance
  chunk   picked from the face centre on a grid, one draw call per chunk

UV0 is world-scale: each primitive projects its local box axes (metres /
the layer's tile size), so tileable materials line up across pieces and keep
their real size. Atlas layers (signs, windows, props) map to named rects.
Export writes these as glTF attributes: COLOR_0 = (tint, layer / 255),
TEXCOORD_2 = (emit, wet). UV2 (lightmap) is made by the bake step.

Colliders are separate boxes with a ballistic surface name; markers are named
points (spawns, lights for characters, probes, sounds) for the Godot level.
"""
import json
import math

import numpy as np
from scipy.spatial import ConvexHull


def rot_z(yaw_deg):
    a = math.radians(yaw_deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float64)


def rot_y(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float64)


def basis_from_dir(d):
    """Rotation whose local +Z points along d."""
    d = np.asarray(d, np.float64)
    nd = np.linalg.norm(d)
    d = d / nd if nd > 1e-9 else np.array([0, 0, 1.0])
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.95 else np.array([1.0, 0, 0])
    x = np.cross(up, d)
    x /= np.linalg.norm(x)
    y = np.cross(d, x)
    return np.stack([x, y, d], 1)


class Kit:
    def __init__(self, materials_json, bounds, chunks=(4, 3)):
        meta = json.load(open(materials_json))
        self.layers = meta["layers"]
        self.bounds = bounds  # (xmin, ymin, xmax, ymax)
        self.chunks = chunks
        self.V = []  # list of (n,3) arrays
        self.F = []  # list of faces: (vertex indices, uvs (k,2), attrs dict)
        self.nv = 0
        self.colliders = []
        self.markers = []
        # context state
        self.wet = 1.0
        self.detail = False
        self.lightmap = True
        self.chunk_override = None

    # ------------------------------------------------------------------ materials
    def L(self, name):
        return self.layers[name]["index"]

    def tile(self, name):
        return self.layers[name]["tile_m"]

    def rect(self, layer, name):
        return self.layers[layer]["rects"][name]

    # ------------------------------------------------------------------ core
    def _add(self, verts, faces, uvs, layer, tint, emit, smooth=False):
        verts = np.asarray(verts, np.float64)
        base = self.nv
        self.V.append(verts)
        self.nv += len(verts)
        t = tuple(tint) if tint is not None else (0.5, 0.5, 0.5)
        attrs = (layer, t, float(emit), self.wet, self.detail, self.lightmap, smooth, self.chunk_override)
        for f, uv in zip(faces, uvs):
            self.F.append(([base + i for i in f], uv, attrs))

    def _proj_uv(self, local_pts, normal_local, tile):
        """Box projection in local space: drop the dominant normal axis."""
        n = np.abs(normal_local)
        ax = int(np.argmax(n))
        if ax == 0:
            uv = local_pts[:, [1, 2]] * [np.sign(normal_local[0]) or 1, 1]
        elif ax == 1:
            uv = local_pts[:, [0, 2]] * [-(np.sign(normal_local[1]) or 1), 1]
        else:
            uv = local_pts[:, [0, 1]]
        uv = uv / tile
        return np.stack([uv[:, 0], -uv[:, 1]], 1)

    def mesh(self, local_verts, faces, R, T, mat, tint=None, emit=0.0, smooth=False, uv_origin=None, uvs=None, uv_scale=1.0):
        """Add faces given in local space; UVs box-projected in local space unless given."""
        local_verts = np.asarray(local_verts, np.float64)
        world = local_verts @ R.T + np.asarray(T, np.float64)
        layer = self.L(mat)
        tile = self.tile(mat) / uv_scale
        o = np.zeros(3) if uv_origin is None else np.asarray(uv_origin)
        out_uvs = []
        for fi, f in enumerate(faces):
            if uvs is not None:
                out_uvs.append(np.asarray(uvs[fi], np.float64))
                continue
            p = local_verts[f]
            nrm = np.cross(p[1] - p[0], p[2] - p[0])
            if np.linalg.norm(nrm) < 1e-12 and len(f) > 3:
                nrm = np.cross(p[2] - p[0], p[3] - p[0])
            # project with world offset so neighbouring pieces line up
            out_uvs.append(self._proj_uv(p + (R.T @ np.asarray(T, np.float64) if uv_origin is None else o), nrm, tile))
        self._add(world, faces, out_uvs, layer, tint, emit, smooth)

    # ------------------------------------------------------------------ primitives
    def box(self, c, size, mat, tint=None, yaw=0.0, R=None, chamfer=0.0, emit=0.0, col=None, faces="all", uv_scale=1.0):
        """Axis box (centre c, size sx,sy,sz) rotated by yaw (deg) or R. col=surface adds a collider."""
        sx, sy, sz = [s / 2 for s in size]
        R = rot_z(yaw) if R is None else R
        if chamfer > 0:
            c_ = min(chamfer, sx * 0.45, sy * 0.45, sz * 0.45)
            pts = []
            for a in (-1, 1):
                for b in (-1, 1):
                    for d in (-1, 1):
                        pts += [(a * (sx - c_), b * (sy - c_), d * sz), (a * (sx - c_), b * sy, d * (sz - c_)), (a * sx, b * (sy - c_), d * (sz - c_))]
            pts = np.array(pts)
            hull = ConvexHull(pts)
            fcs = []
            for simp, eq in zip(hull.simplices, hull.equations):
                p = pts[simp]
                if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), eq[:3]) < 0:
                    simp = simp[::-1]
                fcs.append(list(simp))
            self.mesh(pts, fcs, R, c, mat, tint, emit, uv_scale=uv_scale)
        else:
            v = np.array([(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
                          (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)])
            allf = {"-z": [0, 3, 2, 1], "+z": [4, 5, 6, 7], "-y": [0, 1, 5, 4], "+y": [2, 3, 7, 6], "-x": [3, 0, 4, 7], "+x": [1, 2, 6, 5]}
            keys = list(allf) if faces == "all" else faces
            self.mesh(v, [allf[k] for k in keys], R, c, mat, tint, emit, uv_scale=uv_scale)
        if col:
            self.collider(c, size, yaw if R is None or yaw else _yaw_of(R), col)

    def quad(self, p0, p1, p2, p3, mat, tint=None, emit=0.0, rect=None, double=False, uv=None):
        """Quad p0..p3 counter-clockwise seen from the front. rect = atlas rect name."""
        pts = np.array([p0, p1, p2, p3], np.float64)
        layer = self.L(mat)
        if rect is not None or uv is not None:
            u0, v0, u1, v1 = self.rect(mat, rect) if rect is not None else uv
            uvs = np.array([(u0, v1), (u1, v1), (u1, v0), (u0, v0)])
        else:
            nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            # local frame of the quad so tiles follow its edges
            e1 = (pts[1] - pts[0]) / np.linalg.norm(pts[1] - pts[0])
            e2 = np.cross(nrm / np.linalg.norm(nrm), e1)
            rel = pts - pts[0]
            uvs = np.stack([rel @ e1 + pts[0] @ e1, -(rel @ e2 + pts[0][2])], 1) / self.tile(mat)
        self._add(pts, [[0, 1, 2, 3]], [uvs], layer, tint, emit)
        if double:
            self._add(pts, [[3, 2, 1, 0]], [uvs[[3, 2, 1, 0]]], layer, tint, emit)

    def sign(self, centre, w, h, yaw, mat, rect, tint=None, emit=0.0, depth=0.0, back_mat="paint_metal", back_tint=(0.15, 0.15, 0.15), double=False):
        """A sign facing yaw (deg; 0 = facing -Y/south... see `facing`), optional box behind it."""
        R = rot_z(yaw)
        n = R @ np.array([0, -1.0, 0])
        x = R @ np.array([1.0, 0, 0])
        c = np.asarray(centre, np.float64)
        f = c + n * (depth / 2 + 0.002)
        hw, hh = w / 2, h / 2
        z = np.array([0, 0, 1.0])
        self.quad(f - x * hw - z * hh, f + x * hw - z * hh, f + x * hw + z * hh, f - x * hw + z * hh, mat, tint, emit, rect=rect)
        if double:
            b = c - n * (depth / 2 + 0.002)
            self.quad(b + x * hw - z * hh, b - x * hw - z * hh, b - x * hw + z * hh, b + x * hw + z * hh, mat, tint, emit, rect=rect)
        if depth > 0:
            self.box(c, (w + 0.02, depth, h + 0.02), back_mat, back_tint, yaw=yaw, faces=["-z", "+z", "-x", "+x"] + ([] if double else ["+y"]))

    def cyl(self, p0, p1, r, mat, tint=None, sides=12, caps=True, emit=0.0, r1=None, smooth=True, uv_scale=1.0):
        p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
        d = p1 - p0
        L = np.linalg.norm(d)
        R = basis_from_dir(d)
        r1 = r if r1 is None else r1
        a = np.linspace(0, 2 * np.pi, sides + 1)
        ring0 = np.stack([np.cos(a) * r, np.sin(a) * r, np.zeros_like(a)], 1)
        ring1 = np.stack([np.cos(a) * r1, np.sin(a) * r1, np.full_like(a, L)], 1)
        v = np.concatenate([ring0, ring1])
        n = sides + 1
        faces, uvs = [], []
        tile = self.tile(mat) / uv_scale
        circ = 2 * np.pi * max(r, r1)
        for i in range(sides):
            faces.append([i, i + 1, n + i + 1, n + i])
            u0, u1 = i / sides * circ / tile, (i + 1) / sides * circ / tile
            uvs.append(np.array([(u0, 0), (u1, 0), (u1, -L / tile), (u0, -L / tile)]))
        self._add(v @ R.T + p0, faces, uvs, self.L(mat), tint, emit, smooth)
        if caps:
            for ring, rev in ((ring0[:-1], True), (ring1[:-1], False)):
                idx = list(range(sides))
                f = idx[::-1] if rev else idx
                uv = ring[:, :2][f] / tile
                self._add(ring @ R.T + p0, [f], [uv], self.L(mat), tint, emit, False)

    def lathe(self, base, profile, mat, tint=None, sides=12, emit=0.0, R=None, smooth=True, cap_top=True, cap_bottom=True):
        """Surface of revolution around local Z; profile = [(radius, z), ...] bottom to top."""
        R = np.eye(3) if R is None else R
        a = np.linspace(0, 2 * np.pi, sides + 1)
        rings = [np.stack([np.cos(a) * r, np.sin(a) * r, np.full_like(a, z)], 1) for r, z in profile]
        v = np.concatenate(rings)
        n = sides + 1
        tile = self.tile(mat)
        faces, uvs = [], []
        acc = [0.0]
        for k in range(1, len(profile)):
            acc.append(acc[-1] + math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]))
        circ = 2 * np.pi * max(p[0] for p in profile)
        for k in range(len(profile) - 1):
            for i in range(sides):
                faces.append([k * n + i, k * n + i + 1, (k + 1) * n + i + 1, (k + 1) * n + i])
                u0, u1 = i / sides * circ / tile, (i + 1) / sides * circ / tile
                uvs.append(np.array([(u0, -acc[k] / tile), (u1, -acc[k] / tile), (u1, -acc[k + 1] / tile), (u0, -acc[k + 1] / tile)]))
        self._add(v @ R.T + base, faces, uvs, self.L(mat), tint, emit, smooth)
        for k, cap in ((0, cap_bottom), (len(profile) - 1, cap_top)):
            if cap and profile[k][0] > 1e-4:
                ring = rings[k][:-1]
                f = list(range(sides))
                if k == 0:
                    f = f[::-1]
                self._add(ring @ R.T + base, [f], [ring[:, :2][f] / tile], self.L(mat), tint, emit, False)

    def tube(self, pts, r, mat, tint=None, sides=6, emit=0.0, smooth=True, closed=False):
        """Tube along a polyline (wires, ropes, pipes, rails)."""
        pts = np.asarray(pts, np.float64)
        keep = [0] + [i for i in range(1, len(pts)) if np.linalg.norm(pts[i] - pts[i - 1]) > 1e-5]
        pts = pts[keep]
        if len(pts) < 2:
            return
        if closed:
            pts = np.concatenate([pts, pts[:1]])
        nseg = len(pts)
        a = np.linspace(0, 2 * np.pi, sides + 1)
        rings = []
        acc = [0.0]
        for i in range(nseg):
            if i == 0:
                d = pts[1] - pts[0]
            elif i == nseg - 1:
                d = pts[-1] - pts[-2]
            else:
                d = (pts[i + 1] - pts[i]) / (np.linalg.norm(pts[i + 1] - pts[i]) + 1e-9) + (pts[i] - pts[i - 1]) / (np.linalg.norm(pts[i] - pts[i - 1]) + 1e-9)
            B = basis_from_dir(d)
            ring = np.stack([np.cos(a) * r, np.sin(a) * r, np.zeros_like(a)], 1) @ B.T + pts[i]
            rings.append(ring)
            if i:
                acc.append(acc[-1] + np.linalg.norm(pts[i] - pts[i - 1]))
        v = np.concatenate(rings)
        n = sides + 1
        tile = self.tile(mat)
        faces, uvs = [], []
        for k in range(nseg - 1):
            for i in range(sides):
                faces.append([k * n + i, k * n + i + 1, (k + 1) * n + i + 1, (k + 1) * n + i])
                u0, u1 = i / sides * 2 * np.pi * r / tile, (i + 1) / sides * 2 * np.pi * r / tile
                uvs.append(np.array([(acc[k] / tile, u0), (acc[k] / tile, u1), (acc[k + 1] / tile, u1), (acc[k + 1] / tile, u0)]))
        self._add(v, faces, uvs, self.L(mat), tint, emit, smooth)

    def prism(self, poly, z0, z1, mat, tint=None, emit=0.0, top=True, bottom=False, sides=True, col=None):
        """Vertical extrusion of a 2D polygon (counter-clockwise from above)."""
        poly = np.asarray(poly, np.float64)
        n = len(poly)
        lo = np.concatenate([poly, np.full((n, 1), z0)], 1)
        hi = np.concatenate([poly, np.full((n, 1), z1)], 1)
        v = np.concatenate([lo, hi])
        faces = []
        if sides:
            for i in range(n):
                j = (i + 1) % n
                faces.append([i, j, n + j, n + i])
        if top:
            faces.append(list(range(n, 2 * n)))
        if bottom:
            faces.append(list(range(n))[::-1])
        self.mesh(v, faces, np.eye(3), np.zeros(3), mat, tint, emit, uv_origin=np.zeros(3))
        if col:
            mn, mx = poly.min(0), poly.max(0)
            self.collider(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (z0 + z1) / 2), (mx[0] - mn[0], mx[1] - mn[1], z1 - z0), 0, col)

    def extrude(self, profile, p0, p1, mat, tint=None, up=(0, 0, 1), emit=0.0, caps=True, smooth=False):
        """Extrude a 2D profile [(x, y)...] (x = sideways, y = up) along p0 -> p1 (beams, mouldings, rails)."""
        p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
        d = p1 - p0
        L = np.linalg.norm(d)
        fwd = d / L
        upv = np.asarray(up, np.float64)
        side = np.cross(fwd, upv)
        if np.linalg.norm(side) < 1e-6:
            side = np.cross(fwd, [1, 0, 0])
        side /= np.linalg.norm(side)
        upv = np.cross(side, fwd)
        R = np.stack([side, upv, fwd], 1)
        prof = np.asarray(profile, np.float64)
        n = len(prof)
        a = np.concatenate([prof, np.zeros((n, 1))], 1)
        b = np.concatenate([prof, np.full((n, 1), L)], 1)
        v = np.concatenate([a, b])
        faces = [[i, n + i, n + (i + 1) % n, (i + 1) % n] for i in range(n)]
        if caps:
            faces.append(list(range(n))[::-1])
            faces.append(list(range(n, 2 * n)))
        self.mesh(v, faces, R, p0, mat, tint, emit, smooth=smooth, uv_origin=np.zeros(3))

    def add_object(self, obj, mat, tint=None, emit=0.0, smooth=False):
        """Faces of an evaluated bpy mesh object (world space)."""
        import bpy
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        M = np.array(ev.matrix_world)
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        faces = [list(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        self.mesh(co, faces, np.eye(3), np.zeros(3), mat, tint, emit, smooth=smooth, uv_origin=np.zeros(3))

    # ------------------------------------------------------------------ gameplay data
    def collider(self, c, size, yaw, surface):
        self.colliders.append({"c": [round(float(x), 3) for x in c], "s": [round(float(x), 3) for x in size],
                               "yaw": round(float(yaw), 2), "surface": surface})

    def marker(self, kind, pos, **data):
        d = {"kind": kind, "p": [round(float(x), 3) for x in pos]}
        d.update(data)
        self.markers.append(d)

    # ------------------------------------------------------------------ output
    def chunk_of(self, centre):
        xmin, ymin, xmax, ymax = self.bounds
        cx = int(np.clip((centre[0] - xmin) / (xmax - xmin) * self.chunks[0], 0, self.chunks[0] - 1))
        cy = int(np.clip((centre[1] - ymin) / (ymax - ymin) * self.chunks[1], 0, self.chunks[1] - 1))
        return cy * self.chunks[0] + cx

    def stats(self):
        tris = sum(len(f[0]) - 2 for f in self.F)
        return {"verts": self.nv, "faces": len(self.F), "tris": tris, "colliders": len(self.colliders), "markers": len(self.markers)}

    def build_objects(self, name, groups):
        """Make bpy mesh objects. `groups(face_attrs, centre) -> key` decides which object a face
        goes to; returns {key: object}. Attributes: UVMap, Col (tint, layer/255), Data (emit, wet)."""
        import bpy
        V = np.concatenate(self.V)
        buckets = {}
        for verts, uv, attrs in self.F:
            centre = V[verts].mean(0)
            key = groups(attrs, centre, self)
            buckets.setdefault(key, []).append((verts, uv, attrs))
        objs = {}
        for key, faces in buckets.items():
            used = sorted({i for f in faces for i in f[0]})
            remap = {o: n for n, o in enumerate(used)}
            verts = V[used]
            polys = [[remap[i] for i in f[0]] for f in faces]
            me = bpy.data.meshes.new("%s_%s" % (name, key))
            me.from_pydata(verts.tolist(), [], polys)
            me.update()
            nl = sum(len(p) for p in polys)
            uvs = np.concatenate([f[1] for f in faces]).astype(np.float32)
            uvl = me.uv_layers.new(name="UVMap")
            uvl.data.foreach_set("uv", uvs.ravel())
            col = np.zeros((nl, 4), np.float32)
            dat = np.zeros((nl, 2), np.float32)
            smooth = np.zeros(len(polys), bool)
            k = 0
            for fi, (vv, uv, attrs) in enumerate(faces):
                layer, tint, emit, wet = attrs[0], attrs[1], attrs[2], attrs[3]
                col[k:k + len(vv)] = (tint[0], tint[1], tint[2], layer / 255.0)
                dat[k:k + len(vv)] = (emit, wet)
                smooth[fi] = attrs[6]
                k += len(vv)
            lm = me.uv_layers.new(name="UV2")  # lightmap, filled by the bake step
            lm.data.foreach_set("uv", uvs.ravel())
            ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
            ca.data.foreach_set("color", col.ravel())
            d = me.uv_layers.new(name="Data")
            d.data.foreach_set("uv", dat.ravel())
            me.uv_layers.active = uvl
            me.polygons.foreach_set("use_smooth", smooth)
            ob = bpy.data.objects.new(me.name, me)
            bpy.context.scene.collection.objects.link(ob)
            objs[key] = ob
        return objs


def _yaw_of(R):
    return math.degrees(math.atan2(R[1, 0], R[0, 0]))
