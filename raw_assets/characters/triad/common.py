"""Shared pieces of the triad generator (build.py, body.py, wardrobe.py).

Skeleton joints, metaball families, mesh operations and the coordinates
garments are defined in (how far along an arm or a leg a point is).
Axes: Blender Z up, the man faces -Y (glTF/Godot +Z), his left is +X.
Import after bpy.ops.wm.read_factory_settings() and call init().
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

V = Vector

# ====================================================================== skeleton
# Rest pose: relaxed A-pose. Joint positions in metres (1.75 m man).
J = {
    "root": V((0, 0, 0)),
    "hips": V((0, 0.0, 0.965)),
    "spine": V((0, 0.0, 1.075)),
    "chest": V((0, 0.0, 1.245)),
    "neck": V((0, 0.012, 1.462)),
    "head": V((0, 0.004, 1.572)),
    "head_end": V((0, 0.004, 1.76)),
}
for _s, _sx in (("L", 1.0), ("R", -1.0)):
    J[f"clav.{_s}"] = V((0.025 * _sx, -0.005, 1.425))
    J[f"shoulder.{_s}"] = V((0.172 * _sx, 0.018, 1.418))
    _up = V((0.6 * _sx, 0.06, -0.8)).normalized()
    J[f"elbow.{_s}"] = J[f"shoulder.{_s}"] + _up * 0.30
    _fo = V((0.5 * _sx, -0.16, -0.85)).normalized()
    J[f"wrist.{_s}"] = J[f"elbow.{_s}"] + _fo * 0.265
    J[f"knuckle.{_s}"] = J[f"wrist.{_s}"] + _fo * 0.088
    J[f"tip.{_s}"] = J[f"knuckle.{_s}"] + _fo * 0.085
    J[f"hip.{_s}"] = V((0.092 * _sx, 0.0, 0.93))
    J[f"knee.{_s}"] = V((0.102 * _sx, -0.012, 0.505))
    J[f"ankle.{_s}"] = V((0.106 * _sx, 0.022, 0.088))
    J[f"ball.{_s}"] = V((0.112 * _sx, -0.105, 0.022))

# name, head, tail, parent, roll-align vector (bone Z axis points along it)
BONES = [
    ("root", V((0, 0, 0)), V((0, -0.2, 0)), None, V((0, 0, 1))),
    ("hips", J["hips"], J["spine"], "root", V((0, -1, 0))),
    ("spine", J["spine"], J["chest"], "hips", V((0, -1, 0))),
    ("chest", J["chest"], V((0, 0.0, 1.44)), "spine", V((0, -1, 0))),
    ("neck", J["neck"], J["head"], "chest", V((0, -1, 0))),
    ("head", J["head"], J["head_end"], "neck", V((0, -1, 0))),
]
for _s, _sx in (("L", 1.0), ("R", -1.0)):
    BONES += [
        (f"clavicle.{_s}", J[f"clav.{_s}"], J[f"shoulder.{_s}"], "chest", V((0, -1, 0))),
        (f"upper_arm.{_s}", J[f"shoulder.{_s}"], J[f"elbow.{_s}"], f"clavicle.{_s}", V((0, -1, 0))),
        (f"forearm.{_s}", J[f"elbow.{_s}"], J[f"wrist.{_s}"], f"upper_arm.{_s}", V((0, -1, 0))),
        (f"hand.{_s}", J[f"wrist.{_s}"], J[f"knuckle.{_s}"], f"forearm.{_s}", V((_sx, 0, 0))),
        (f"fingers.{_s}", J[f"knuckle.{_s}"], J[f"tip.{_s}"], f"hand.{_s}", V((_sx, 0, 0))),
        (f"thigh.{_s}", J[f"hip.{_s}"], J[f"knee.{_s}"], "hips", V((0, -1, 0))),
        (f"shin.{_s}", J[f"knee.{_s}"], J[f"ankle.{_s}"], f"thigh.{_s}", V((0, -1, 0))),
        (f"foot.{_s}", J[f"ankle.{_s}"], J[f"ball.{_s}"], f"shin.{_s}", V((0, 0, 1))),
    ]


def frame(origin, y_axis, z_hint):
    y = V(y_axis).normalized()
    x = y.cross(V(z_hint)).normalized()
    z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(origin)
    return m


# The gun, in its own space: +X muzzle, +Y its left, +Z up, origin = top of the
# pistol grip. Where each hand's bone frame sits on it (hand bone: Y = wrist ->
# knuckles, Z = back of the hand).
GRIP_R = frame((-0.072, -0.016, -0.018), (1.0, 0.05, -0.32), (0.0, -1.0, 0.25))
GRIP_L = frame((0.248, 0.062, -0.012), (0.42, -0.9, 0.05), (0.0, 0.25, -1.0))
# Gun -> weapon bone (bone Y along the barrel, bone Z up).
GUN_TO_BONE = Matrix(((0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

# ====================================================================== materials
MB_SCALE = 1.0 / 0.52  # metaball radius for a wanted surface radius (stiffness 2, threshold 0.6)
# Material slots (each part's faces keep one; baked as the material-id map).
MATS = ["skin", "hair", "cloth", "rib", "shoes", "eye", "inner", "cap", "vest", "metal", "lens", "leather"]
FLAT = {"skin": (0.62, 0.45, 0.34), "hair": (0.03, 0.028, 0.026), "cloth": (0.4, 0.4, 0.4),
        "rib": (0.3, 0.3, 0.3), "shoes": (0.08, 0.08, 0.08), "eye": (0.8, 0.78, 0.74),
        "inner": (0.03, 0.03, 0.03), "cap": (0.4, 0.05, 0.04), "vest": (0.04, 0.04, 0.04),
        "metal": (0.8, 0.6, 0.2), "lens": (0.02, 0.02, 0.025), "leather": (0.06, 0.04, 0.03)}
MAT = {}
COL = None


def init():
    global COL
    COL = bpy.context.scene.collection
    MAT.clear()
    for n in MATS:
        m = bpy.data.materials.new(n)
        m.diffuse_color = (*FLAT[n], 1)
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*FLAT[n], 1)
        bsdf.inputs["Roughness"].default_value = 0.7
        MAT[n] = m


# ====================================================================== metaballs
class Family:
    """One metaball object: its elements blend with each other only."""

    def __init__(self, name, res):
        self.mb = bpy.data.metaballs.new(name)
        self.mb.resolution = res
        self.mb.render_resolution = res
        self.mb.threshold = 0.6
        self.ob = bpy.data.objects.new(name, self.mb)
        COL.objects.link(self.ob)

    def ball(self, p, r, neg=False):
        e = self.mb.elements.new(type="BALL")
        e.co = V(p)
        e.radius = r * MB_SCALE
        e.use_negative = neg
        return e

    def capsule(self, p0, p1, r):
        p0, p1 = V(p0), V(p1)
        e = self.mb.elements.new(type="CAPSULE")
        d = p1 - p0
        e.co = (p0 + p1) / 2
        e.radius = r * MB_SCALE
        e.size_x = max(d.length / 2 - r * 0.35, 0.0005)
        e.rotation = V((1, 0, 0)).rotation_difference(d.normalized())
        return e

    def taper(self, p0, p1, r0, r1, n=4):
        """Chain of balls from p0 (radius r0) to p1 (r1), close enough not to bead."""
        p0, p1 = V(p0), V(p1)
        n = max(n, int(math.ceil((p1 - p0).length / (0.3 * min(r0, r1)))))
        for i in range(n + 1):
            t = i / n
            self.ball(p0.lerp(p1, t), r0 + (r1 - r0) * t)

    def cone(self, p0, p1, r0, r1, n=2):
        """A tapering limb: n capsules end to end, each with its mean radius."""
        p0, p1 = V(p0), V(p1)
        for i in range(n):
            a, b = p0.lerp(p1, i / n), p0.lerp(p1, (i + 1) / n)
            self.capsule(a, b, r0 + (r1 - r0) * (i + 0.5) / n)

    def ellipsoid(self, p, radii, rot=None):
        e = self.mb.elements.new(type="ELLIPSOID")
        e.co = V(p)
        e.radius = MB_SCALE
        e.size_x, e.size_y, e.size_z = radii
        if rot is not None:
            e.rotation = rot
        return e

    def along(self, p0, p1, t, radii, off=(0, 0, 0)):
        """Ellipsoid at fraction t of p0->p1, its Z axis along the segment, offset in world."""
        p0, p1 = V(p0), V(p1)
        d = (p1 - p0).normalized()
        rot = V((0, 0, 1)).rotation_difference(d)
        return self.ellipsoid(p0.lerp(p1, t) + V(off), radii, rot)


def to_mesh(families, name):
    """Converts metaball families to meshes and joins them."""
    meshes = []
    for fam in families:
        bpy.ops.object.select_all(action="DESELECT")
        fam.ob.select_set(True)
        bpy.context.view_layer.objects.active = fam.ob
        bpy.ops.object.convert(target="MESH")
        ob = bpy.context.active_object
        if ob.type == "MESH" and len(ob.data.polygons) > 0:
            meshes.append(ob)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def apply_mod(ob, kind, **kw):
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(m, k, v)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


def remesh(ob, voxel, smooth=0):
    apply_mod(ob, "REMESH", mode="VOXEL", voxel_size=voxel, adaptivity=0.0, use_smooth_shade=True)
    if smooth:
        apply_mod(ob, "SMOOTH", factor=0.5, iterations=smooth)


def cut(ob, co, no, fill=False, fill_mat=1):
    """Keeps the side of the plane (co, no) that `no` points to. `fill` closes the hole."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=V(co), plane_no=-V(no), clear_outer=True)
    if fill:
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            out = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            for f in out["faces"]:
                f.material_index = fill_mat
    bm.to_mesh(ob.data)
    bm.free()


def keep_where(ob, fn):
    """Deletes faces whose centre fails fn(Vector)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if not fn(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def set_material(ob, name, inner=None):
    ob.data.materials.clear()
    ob.data.materials.append(MAT[name])
    ob.data.materials.append(MAT[inner or "inner"])


def all_materials(ob, name):
    """Gives `ob` every slot in MATS order and puts all its faces on `name`."""
    ob.data.materials.clear()
    for n in MATS:
        ob.data.materials.append(MAT[n])
    idx = MATS.index(name)
    for p in ob.data.polygons:
        p.material_index = idx


def verts_np(ob):
    n = len(ob.data.vertices)
    P = np.empty(n * 3)
    ob.data.vertices.foreach_get("co", P)
    return P.reshape(-1, 3)


def set_verts_np(ob, P):
    ob.data.vertices.foreach_set("co", np.asarray(P, dtype=np.float64).ravel())
    ob.data.update()


def decimate(ob, target_tris):
    ob.data.calc_loop_triangles()
    n = len(ob.data.loop_triangles)
    if n > target_tris:
        apply_mod(ob, "DECIMATE", ratio=target_tris / n)


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def new_mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    return ob


def duplicate(ob, name):
    me = ob.data.copy()
    o2 = bpy.data.objects.new(name, me)
    COL.objects.link(o2)
    o2.matrix_world = ob.matrix_world.copy()
    return o2


def field_cut(ob, field, keep_positive=True):
    """Cuts the mesh along the zero line of a scalar field and keeps one side.

    `field(P)` takes an (n, 3) array of vertex positions and returns n values.
    Edges crossing zero are split where the field (linear along the edge) is
    zero, faces are split along the new vertices, and faces on the negative
    side are deleted (positive side if keep_positive is False).
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    P = np.array([v.co[:] for v in bm.verts])
    f = np.asarray(field(P), dtype=np.float64)
    if not keep_positive:
        f = -f
    val = {v: float(f[i]) for i, v in enumerate(bm.verts)}
    cross = [e for e in bm.edges if (val[e.verts[0]] >= 0.0) != (val[e.verts[1]] >= 0.0)]
    new_verts = set()
    for e in cross:
        a, b = e.verts
        fa, fb = val[a], val[b]
        t = fa / (fa - fb)
        t = min(max(t, 0.0), 1.0)
        if t < 1e-4:
            val[a] = 0.0
            new_verts.add(a)
            continue
        if t > 1 - 1e-4:
            val[b] = 0.0
            new_verts.add(b)
            continue
        _, nv = bmesh.utils.edge_split(e, a, t)
        val[nv] = 0.0
        new_verts.add(nv)
    for face in list(bm.faces):
        if not face.is_valid:
            continue
        on = [v for v in face.verts if v in new_verts]
        if len(on) < 2:
            continue
        pos = any(val[v] > 0 for v in face.verts)
        neg = any(val[v] < 0 for v in face.verts)
        if not (pos and neg):
            continue
        if len(on) == 2:
            a, b = on
            if not any(b in e.verts for e in a.link_edges if e in face.edges):
                try:
                    bmesh.utils.face_split(face, a, b)
                except ValueError:
                    pass
        else:
            try:
                bmesh.ops.connect_verts(bm, verts=on)
            except Exception:
                pass
    dead = []
    for face in bm.faces:
        vs = [val.get(v, 0.0) for v in face.verts]
        if sum(vs) / len(vs) < 0.0:
            dead.append(face)
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


# ====================================================================== body coordinates
def ss(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def seg_param(P, a, b):
    """Closest point parameter t (clamped 0..1) and distance of P to segment a-b."""
    a, b = np.array(a[:]), np.array(b[:])
    d = b - a
    t = np.clip(((P - a) @ d) / (d @ d), 0, 1)
    q = a + t[:, None] * d
    return t, np.linalg.norm(P - q, axis=1)


def limb_coord(P, joints):
    """Distance along a polyline of joints (from the first) and from its axis."""
    best = np.full(len(P), np.inf)
    s = np.zeros(len(P))
    acc = 0.0
    for i in range(len(joints) - 1):
        a, b = np.array(joints[i][:]), np.array(joints[i + 1][:])
        L = np.linalg.norm(b - a)
        t = ((P - a) @ (b - a)) / (L * L)
        lo = -np.inf if i == 0 else 0.0
        hi = np.inf if i == len(joints) - 2 else 1.0
        tc = np.clip(t, lo, hi)
        q = a + tc[:, None] * (b - a)
        dist = np.linalg.norm(P - q, axis=1)
        m = dist < best
        best[m] = dist[m]
        s[m] = acc + tc[m] * L
        acc += L
    return s, best


def arm_coord(P, side):
    """(distance from the shoulder along the arm, distance from the arm axis)."""
    return limb_coord(P, [J[f"shoulder.{side}"], J[f"elbow.{side}"], J[f"wrist.{side}"], J[f"knuckle.{side}"]])


def leg_coord(P, side):
    """(distance from the hip joint down the leg, distance from the leg axis)."""
    return limb_coord(P, [J[f"hip.{side}"], J[f"knee.{side}"], J[f"ankle.{side}"]])


ARM_LEN = {s: (J[f"elbow.{s}"] - J[f"shoulder.{s}"]).length + (J[f"wrist.{s}"] - J[f"elbow.{s}"]).length
           for s in ("L", "R")}
UPPER_ARM_LEN = (J["elbow.L"] - J["shoulder.L"]).length
THIGH_LEN = (J["knee.L"] - J["hip.L"]).length
LEG_LEN = THIGH_LEN + (J["ankle.L"] - J["knee.L"]).length


def regions(P):
    """Body regions by position (rest pose): masks arm_L, arm_R, leg_L, leg_R, torso, head."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    out = {}
    torso_score = np.sqrt((x / 0.19) ** 2 + (y / 0.13) ** 2)
    arm = {}
    for s, sx in (("L", 1), ("R", -1)):
        sarm, darm = arm_coord(P, s)
        arm[s] = (darm / 0.068 < torso_score) & (z < 1.47) & (z > 0.75) & (x * sx > 0.1) & (sarm > 0.0)
    head = (z > 1.47) | ((z > 1.43) & (np.sqrt(x * x + (y - 0.012) ** 2) < 0.075))
    pelvis_score = np.sqrt((x / 0.17) ** 2 + (y / 0.12) ** 2)
    leg = {}
    for s, sx in (("L", 1), ("R", -1)):
        _, dleg = leg_coord(P, s)
        leg[s] = ~arm[s] & ((z < 0.86) | ((dleg / 0.095 < pelvis_score) & (z < 0.97))) & (x * sx >= -0.001)
    out["arm_L"], out["arm_R"] = arm["L"], arm["R"]
    out["leg_L"], out["leg_R"] = leg["L"] & ~head, leg["R"] & ~head
    out["head"] = head & ~arm["L"] & ~arm["R"]
    out["torso"] = ~(out["arm_L"] | out["arm_R"] | out["leg_L"] | out["leg_R"] | out["head"])
    return out
