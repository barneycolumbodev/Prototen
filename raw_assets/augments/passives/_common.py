"""Shared helpers for the passive-part hardware (docs/design.md §3.6): pieces modelled on the operative.

Every passive with modelled hardware has raw_assets/augments/passives/<id>/build.py. They all:
- import the finished operative (assets/characters/operative/operative.gltf) so pieces sit on the real suit and
  helmet surfaces in the rest pose (Blender: +Z up, the operative faces -Y, metres);
- build each piece twice, HIGH (bevels, bolts, grooves, lettering) and LOW (the game mesh), tagging every piece
  with the bone it rides on;
- bake HIGH -> LOW into one texture set per part (base colour with cavity grime, ORM, normal, emission);
- export one glTF whose meshes are named "B_<bone>__<piece>" in model space ("forearm.L" -> "forearm_L"); Godot's
  BodyAppearance mounts each mesh on its bone (PartVisual.model_space);
- render previews on the operative.
"""
import math
import os
import sys
import time

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "raw_assets", "_lib"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

OPERATIVE = os.path.join(ROOT, "assets", "characters", "operative", "operative.gltf")
V = Vector
T0 = time.time()
TAG = "part"


def log(*a):
    print(f"[{TAG} {time.time() - T0:6.1f}s]", *a, flush=True)


# ====================================================================== scene and the operative
class Body:
    """The operative as reference geometry: meshes, bone positions and ray casts against the surface."""

    def __init__(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=OPERATIVE)
        for ob in list(bpy.data.objects):
            if ob.name.startswith("Icosphere"):
                bpy.data.objects.remove(ob)
        self.suit = bpy.data.objects["operative"]
        self.helmet = bpy.data.objects["operative_helmet"]
        self.head = bpy.data.objects["operative_head"]
        self.rig = bpy.data.objects["operative_rig"]
        self.bones = {b.name: (self.rig.matrix_world @ b.head_local) for b in self.rig.data.bones}
        self.bvh = {"suit": self._bvh(self.suit), "helmet": self._bvh(self.helmet)}
        self.ref = [self.suit, self.helmet, self.head, self.rig]
        self.show_head(False)

    @staticmethod
    def _bvh(ob):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        return BVHTree.FromPolygons(verts, polys)

    def joint(self, name):
        return V(self.bones[name])

    def cast(self, origin, direction, which=("suit",), dist=2.0):
        """First hit from `origin` along `direction` on the given meshes: (point, normal) or (None, None)."""
        best = None
        d = V(direction).normalized()
        for w in which:
            loc, nrm, _i, t = self.bvh[w].ray_cast(V(origin), d, dist)
            if loc is not None and (best is None or t < best[2]):
                best = (loc, nrm, t)
        if best is None:
            return None, None
        return best[0], best[1]

    def surface_toward(self, target, direction, which=("suit",), back=0.6):
        """Where a ray aimed along `direction` at `target` (from `back` m before it) meets the body."""
        d = V(direction).normalized()
        return self.cast(V(target) - d * back, d, which, back * 2.0)

    def show_head(self, bare=False):
        """Helmet on (default) or the bare head, for previews."""
        self.helmet.hide_render = bare
        self.head.hide_render = not bare

    def hide_reference(self, hidden=True):
        for ob in self.ref:
            ob.hide_render = hidden
            ob.hide_viewport = hidden


def basis4(x, y, z, origin=(0, 0, 0)):
    """A 4x4 matrix whose columns are the axes x, y, z and the origin."""
    m = Matrix.Identity(4)
    for c, axis in enumerate((x, y, z, origin)):
        for r in range(3):
            m[r][c] = axis[r]
    return m


# ====================================================================== pieces
class Piece:
    """One rigid piece of a part: HIGH and LOW objects on one bone."""

    def __init__(self, name, bone, high, low):
        self.name, self.bone, self.high, self.low = name, bone, high, low


PIECES = []


def add_piece(name, bone, high, low):
    p = Piece(name, bone, high, low)
    PIECES.append(p)
    return p


def mirror_x(ob, name):
    """A mirrored copy (left <-> right) with normals fixed."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    cp.name = name
    bpy.context.scene.collection.objects.link(cp)
    cp.data.transform(Matrix.Scale(-1.0, 4, (1, 0, 0)))
    bm = bmesh.new()
    bm.from_mesh(cp.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(cp.data)
    bm.free()
    for m in cp.modifiers:
        pass
    return cp


def side_bone(bone, side):
    return bone.replace(".L", "." + side).replace(".R", "." + side)


def apply_all(ob):
    """Applies every modifier on `ob` (text/curves converted first)."""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    if ob.type != "MESH":
        bpy.ops.object.convert(target="MESH")
        ob = bpy.context.active_object
    for m in list(ob.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError as e:  # noqa: PERF203
            log("modifier failed", ob.name, m.name, e)
            ob.modifiers.remove(m)
    return ob


def join(obs, name):
    obs = [o for o in obs if o is not None]
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


# ====================================================================== conformal plates
def poly_mesh(name, poly_uv, frame, subdiv=4, direction=None):
    """A flat polygon (u, v) in `frame` = (origin, U, V), triangulated and subdivided for projection.
    With `direction` the face is wound so its normal points against it (out of the body)."""
    o, U, Vv = frame
    bm = bmesh.new()
    vs = [bm.verts.new(o + U * u + Vv * v) for u, v in poly_uv]
    f = bm.faces.new(vs)
    f.normal_update()
    if direction is not None and f.normal.dot(V(direction)) > 0:
        f.normal_flip()
    bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="BEAUTY")
    for _ in range(subdiv):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=bm.edges[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def project_onto(ob, body, direction, gap, which=("suit",), smooth_r=0.02, samples=6, keep=None, relax=10):
    """Moves every vertex of a flat sheet along `direction` onto the body surface, `gap` off it.
    The surface distance is averaged over a small disc (radius smooth_r), vertices whose rays miss the body
    take their neighbours' distance (a plate overhangs the edge of a limb as a flat skirt), and the
    distance field is relaxed over the mesh `relax` times so the sheet follows the body's big forms only."""
    d = V(direction).normalized()
    a = d.orthogonal().normalized()
    b = d.cross(a).normalized()
    offs = [V((0, 0, 0))] + [a * math.cos(k * 2 * math.pi / samples) * smooth_r + b * math.sin(k * 2 * math.pi / samples) * smooth_r
                              for k in range(samples)]
    me = ob.data
    n = len(me.vertices)
    t = [None] * n
    for v in me.vertices:
        ts = []
        for off in offs:
            o = v.co + off - d * 0.5
            hit, _n = body.cast(o, d, which, 1.2)
            if hit is not None:
                ts.append((hit - o).dot(d))
        if len(ts) * 2 > len(offs):
            t[v.index] = sum(ts) / len(ts)
    nb = [[] for _ in range(n)]
    for e in me.edges:
        i, j = e.vertices
        nb[i].append(j)
        nb[j].append(i)
    if all(x is None for x in t):
        log("project_onto: nothing hit for", ob.name)
        return
    # Fill the misses from their neighbours, ring by ring.
    for _ in range(200):
        missing = [i for i in range(n) if t[i] is None]
        if not missing:
            break
        new = {}
        for i in missing:
            vals = [t[j] for j in nb[i] if t[j] is not None]
            if vals:
                new[i] = min(vals)  # the nearest surface: overhang, never sink in
        for i, val in new.items():
            t[i] = val
    t = [x if x is not None else 0.5 for x in t]
    # Relax: each pass moves a vertex halfway to its neighbours' mean, but never deeper than its own hit.
    floor = list(t)
    for _ in range(relax):
        t = [min(0.5 * t[i] + 0.5 * (sum(t[j] for j in nb[i]) / len(nb[i]) if nb[i] else t[i]), floor[i] + 0.004)
             for i in range(n)]
    for v in me.vertices:
        if keep and keep(v):
            continue
        v.co = v.co - d * 0.5 + d * (t[v.index] - gap)
    me.update()


def plate(name, body, poly_uv, frame, direction, gap, thickness, which=("suit",), facet_deg=7.0, smooth_r=0.02,
          bevel=0.0018, subdiv=2, chamfer=True, crown=0.0):
    """A conformal plate: a polygon projected onto the body, faceted (planar decimate), given thickness and
    bevelled. Returns (high, low). `crown` lifts the middle (m) so the plate reads as a solid slab."""
    sheet = poly_mesh(name + "_sheet", poly_uv, frame, subdiv, direction)
    project_onto(sheet, body, direction, gap, which, smooth_r)
    if crown:
        cen = sum((v.co for v in sheet.data.vertices), V()) / len(sheet.data.vertices)
        rmax = max((v.co - cen).length for v in sheet.data.vertices)
        for v in sheet.data.vertices:
            k = 1.0 - min((v.co - cen).length / rmax, 1.0)
            v.co -= V(direction).normalized() * crown * (k * k * (3 - 2 * k))
    dec = sheet.modifiers.new("facets", "DECIMATE")
    dec.decimate_type = "DISSOLVE"
    dec.angle_limit = math.radians(facet_deg)
    sheet = apply_all(sheet)
    sol = sheet.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = 1.0  # away from the body (normals face out after recalc)
    sol.use_even_offset = True
    sheet = apply_all(sheet)
    _outward(sheet, direction)
    low = sheet.copy()
    low.data = sheet.data.copy()
    low.name = name + "_low"
    bpy.context.scene.collection.objects.link(low)
    high = sheet
    high.name = name + "_high"
    if chamfer:
        bv = high.modifiers.new("bevel", "BEVEL")
        bv.width = bevel
        bv.segments = 3
        bv.limit_method = "ANGLE"
        bv.angle_limit = math.radians(25)
        bv.harden_normals = True
        high = apply_all(high)
        bl = low.modifiers.new("bevel", "BEVEL")
        bl.width = bevel * 0.8
        bl.segments = 1
        bl.limit_method = "ANGLE"
        bl.angle_limit = math.radians(35)
        low = apply_all(low)
    for o in (high, low):
        o.data.shade_smooth()
        o.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
    return apply_all(high), apply_all(low)


def _outward(ob, direction):
    """Recalculates normals so they point out of the solid."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def groove(target, body_dir, path_pts, width=0.0016, depth=0.0012):
    """Cuts a V-ish groove along a polyline into `target` (HIGH): a thin box per segment, boolean difference."""
    cutters = []
    d = V(body_dir).normalized()
    for a, b in zip(path_pts[:-1], path_pts[1:]):
        a, b = V(a), V(b)
        mid = (a + b) / 2
        ax = (b - a)
        L = ax.length
        ax.normalize()
        side = ax.cross(d).normalized()
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        m = basis4(ax, side, d, mid) @ Matrix.Diagonal((L + width, width, depth * 2, 1))
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
        me = bpy.data.meshes.new("groove")
        bm.to_mesh(me)
        bm.free()
        c = bpy.data.objects.new("groove", me)
        bpy.context.scene.collection.objects.link(c)
        cutters.append(c)
    if not cutters:
        return target
    tool = join(cutters, "groove_tool")
    m = target.modifiers.new("groove", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = tool
    target = apply_all(target)
    bpy.data.objects.remove(tool)
    return target


def bolt(name, at, normal, r=0.0042, h=0.0026, hexagon=True):
    """A hex (or round) bolt head standing on `at`, facing `normal` (HIGH only)."""
    n = V(normal).normalized()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6 if hexagon else 16, radius1=r, radius2=r * 0.92, depth=h)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r * 1.25, radius2=r * 1.25, depth=h * 0.35,
                          matrix=Matrix.Translation((0, 0, -h * 0.5)))
    rot = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(V(at) + n * h * 0.4) @ rot, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bv = ob.modifiers.new("bevel", "BEVEL")
    bv.width = 0.0005
    bv.segments = 2
    return ob


def surface_points(ob, direction, uv_pts, frame, body=None):
    """World points on `ob`'s outer face under each (u, v) of `frame`, and their normals (for bolts, decals)."""
    o, U, Vv = frame
    bvh = Body._bvh(ob)
    d = V(direction).normalized()
    out = []
    for u, v in uv_pts:
        p = o + U * u + Vv * v - d * 0.4
        loc, nrm, _i, _t = bvh.ray_cast(p, d, 1.0)
        if loc is not None:
            out.append((loc, nrm))
    return out


def stencil(name, body_text, at, normal, up, size, mat, target=None, lift=0.0004):
    """Stencil lettering lying on a surface (HIGH only; it reaches the game through the bake). With `target`
    the flat letters are shrink-wrapped onto it, `lift` above, so they follow curved and faceted plates."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body_text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    n = V(normal).normalized()
    upv = (V(up) - n * V(up).dot(n)).normalized()
    right = upv.cross(n)
    ob.matrix_world = basis4(right, upv, n, V(at) + n * 0.002)
    ob.data.materials.append(mat)
    ob = apply_all(ob)  # to a mesh
    if target is not None:
        sw = ob.modifiers.new("wrap", "SHRINKWRAP")
        sw.target = target
        sw.wrap_method = "PROJECT"
        sw.use_project_z = True
        sw.use_negative_direction = True
        sw.use_positive_direction = True
        sw.offset = lift
        ob = apply_all(ob)
    return ob


# ====================================================================== materials
def mat_ceramic(name, base=(0.035, 0.036, 0.038), chip=(0.32, 0.31, 0.29)):
    """Boron-carbide trauma ceramic: near-black satin with a faint mottled cast, pale chips on the edges and
    fine pitting."""
    m = hs.material(name, base, 0.42, 0.0, wear=chip, wear_rough=0.7, bump_scale=900.0, bump_strength=0.25)
    _add_mottle(m, 0.06, 40.0)
    return m


def mat_metal(name, base=(0.10, 0.105, 0.11), rough=0.34, wear=(0.55, 0.56, 0.58), brushed=0.06):
    return hs.material(name, base, rough, 1.0, wear=wear, wear_rough=0.2, brushed=brushed)


def mat_chrome(name):
    return hs.material(name, (0.8, 0.81, 0.83), 0.07, 1.0)


def mat_glow(name, color=(0.36, 0.86, 0.78), strength=6.0):
    return hs.material(name, (0.02, 0.02, 0.02), 0.4, 0.0, emission=(color, strength))


def mat_paint(name, color=(0.62, 0.6, 0.55), rough=0.55):
    return hs.material(name, color, rough, 0.0, bump_scale=1500.0, bump_strength=0.15)


def mat_rubber(name):
    return hs.material(name, (0.018, 0.018, 0.02), 0.82, 0.0, bump_scale=2400.0, bump_strength=0.3)


def mat_heat_tint(name, axis_origin, axis, length, base=(0.72, 0.38, 0.2)):
    """Copper-graphene fins with temper colours: copper at the root, straw, then blue-violet toward the tips.
    The gradient runs along `axis` (world) from `axis_origin` for `length` metres (object coordinates)."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.26
    tc = N.new("ShaderNodeTexCoord")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = tuple(V(axis).normalized())
    sub = N.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = tuple(axis_origin)
    L.new(tc.outputs["Object"], sub.inputs[0])
    L.new(sub.outputs[0], dot.inputs[0])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = length
    L.new(dot.outputs["Value"], mr.inputs["Value"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60.0
    add = N.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.12
    L.new(noise.outputs["Fac"], add.inputs[0])
    L.new(mr.outputs["Result"], add.inputs[2])
    ramp = N.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*base, 1)
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.36, 0.42, 0.62, 1)
    for pos, col in ((0.3, (0.82, 0.6, 0.3)), (0.55, (0.58, 0.3, 0.38)), (0.78, (0.3, 0.26, 0.6))):
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    L.new(add.outputs[0], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def _add_mottle(mat, amount, scale):
    """Large, faint value variation over the base colour (cast ceramic, anodising)."""
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 6.0
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "OVERLAY"
    mix.inputs["Factor"].default_value = amount * 4.0
    if src:
        L.new(src, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    L.new(noise.outputs["Color"], mix.inputs["B"])
    L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


# ====================================================================== bake and export
def bake_and_export(part_id, out_path, materials, tex=1024, cage=0.0015, ray=0.006, ao=0.03, grime=0.5,
                    emission_strength=3.0):
    """Joins every LOW piece (tagged with its bone), unwraps and bakes HIGH -> LOW, splits the result back into
    one mesh per bone and exports them as B_<bone>__<part>."""
    lows, highs = [], []
    bone_ids = sorted({p.bone for p in PIECES})
    for p in PIECES:
        bid = bone_ids.index(p.bone)
        lo = p.low
        a = lo.data.attributes.new("bone_id", "INT", "FACE")
        for i in range(len(lo.data.polygons)):
            a.data[i].value = bid
        lows.append(lo)
        highs.append(p.high)
    low = join(lows, part_id + "_low_all")
    low.modifiers.new("tri", "TRIANGULATE")  # tangents need triangles; bake what the game gets
    low = apply_all(low)
    high = join(highs, part_id + "_high_all")
    log("LOW", tris(low), "tris; HIGH", tris(high))
    bakeutil.unwrap(low, angle_deg=55.0, margin=0.004)
    tex_dir = os.path.join(os.path.dirname(out_path), "textures")
    imgs = bakeutil.bake_textures(high, low, materials, tex, tex_dir, part_id, cage=cage, ray=ray, ao_distance=ao,
                                  grime=grime, log=log)
    bakeutil.apply_baked_material(low, imgs, part_id, emission_strength=emission_strength)
    high.hide_render = True
    # Split by bone.
    out = []
    for bid, bone in enumerate(bone_ids):
        cp = low.copy()
        cp.data = low.data.copy()
        bpy.context.scene.collection.objects.link(cp)
        bm = bmesh.new()
        bm.from_mesh(cp.data)
        lay = bm.faces.layers.int.get("bone_id")
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != bid], context="FACES")
        bm.to_mesh(cp.data)
        bm.free()
        cp.data.attributes.remove(cp.data.attributes["bone_id"])
        cp.name = "B_" + bone.replace(".", "_") + "__" + part_id
        cp.data.name = cp.name
        out.append(cp)
    low.hide_render = True
    low.hide_viewport = True
    bpy.ops.object.select_all(action="DESELECT")
    for o in out:
        o.select_set(True)
    bpy.context.view_layer.objects.active = out[0]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True, export_image_format="AUTO")
    total = sum(tris(o) for o in out)
    log("exported", out_path, len(out), "meshes,", total, "tris")
    return out, high


# ====================================================================== previews
def stage(body):
    """Studio stage close to the body-status screen: dark backdrop, warm key, cool rims."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.014, 0.017, 1)
    bg.inputs["Strength"].default_value = 1.0
    for name, rot, energy, col, size in (("key", (55, 0, 35), 4.0, (1.0, 0.93, 0.85), 8),
                                         ("rimL", (70, 0, 150), 6.0, (0.55, 0.8, 1.0), 4),
                                         ("rimR", (70, 0, -145), 4.5, (0.8, 0.9, 1.0), 4),
                                         ("fill", (80, 0, -40), 0.8, (0.8, 0.85, 1.0), 20)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.color = col
        ld.angle = math.radians(size)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = tuple(math.radians(r) for r in rot)
        scene.collection.objects.link(lo)
    floor = bpy.data.meshes.new("floor")
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=0.62, segments=48)
    bm.to_mesh(floor)
    bm.free()
    fo = bpy.data.objects.new("floor", floor)
    scene.collection.objects.link(fo)
    fo.data.materials.append(hs.material("floor", (0.03, 0.033, 0.036), 0.3, 0.0, emission=((0.36, 0.86, 0.78), 0.05)))


def render(path, cam_loc, target, lens=85, res=(900, 1200), samples=48):
    scene = bpy.context.scene
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    cam.location = cam_loc
    d = V(target) - V(cam_loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.cycles.samples = samples
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    log("rendered", path)


def sheet(paths, out, cols=None):
    """Glues renders side by side into one contact sheet (numpy, no PIL needed)."""
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p)
        w, h = im.size
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        imgs.append(a)
        bpy.data.images.remove(im)
    h = max(a.shape[0] for a in imgs)
    row = np.concatenate([np.pad(a, ((0, h - a.shape[0]), (0, 0), (0, 0))) for a in imgs], axis=1)
    H, W = row.shape[:2]
    img = bpy.data.images.new("sheet", W, H, alpha=True)
    img.pixels.foreach_set(row.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    log("sheet", out)
