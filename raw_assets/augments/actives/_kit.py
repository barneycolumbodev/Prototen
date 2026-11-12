"""Shared kit for the active parts' first-person models (docs/design.md §3.4, 2026-11-10).

Each active with a first-person model has raw_assets/augments/actives/<id>/build.py. They all:
- build rigid pieces (hardsurface.py), join them into named parts with a pivot, parent the parts into a tree;
- key the parts by node transform into ONE clip called "deploy" (the game scrubs it from the part's deploy
  blend, forward to deploy and backward to stow; ArmRig);
- export a glTF with plain factor materials (no bake): the names matter, the game recolours `graft`, `weave`,
  `polymer` and `gunmetal` with the suit colours (BodyColors.NAME_CHANNEL) and drives `glow`;
- render a preview strip of the clip from the player's eye.

Axes (same as the GX-4): +X forward along the forearm, +Z up, origin at the wrist. Right arm: -Y is the outer
side. Left arm: +Y is the outer side (build with side=-1). Metres. In Godot (+Y up) Blender's (x, y, z) is
(x, z, -y).
"""
import argparse
import math
import os
import sys

import bpy  # first: the PyPI bpy module provides bmesh/mathutils
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
import hardsurface as hs  # noqa: E402

V = Vector
FPS = 60
M = {}
REST = {}
scene = None
args = None


def init(tag, end, default_frames, views_default="fp,hero"):
    """Empty scene, arguments, the shared materials. `end`: last frame of the deploy clip."""
    global scene, args
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--preview", default="")
    ap.add_argument("--frames", default=default_frames)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--res", default="800x450")
    ap.add_argument("--views", default=views_default)
    args = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = end
    hs.set_detail(hs.HIGH)
    M.clear()
    REST.clear()
    M["graft"] = hs.material("graft", (0.022, 0.023, 0.026), 0.34, 0.0, coat=0.4)
    M["gunmetal"] = hs.material("gunmetal", (0.10, 0.105, 0.11), 0.36, 1.0)
    M["steel"] = hs.material("steel", (0.42, 0.43, 0.45), 0.26, 1.0)
    M["copper"] = hs.material("copper", (0.86, 0.46, 0.26), 0.30, 1.0)
    M["polymer"] = hs.material("polymer", (0.035, 0.036, 0.04), 0.6, 0.0)
    M["weave"] = hs.material("weave", (0.013, 0.013, 0.015), 0.82, 0.0)
    M["glow"] = hs.material("glow", (0.05, 0.08, 0.12), 0.3, 0.0, emission=((0.36, 0.86, 0.78), 2.5))
    M["tag"] = tag
    return args


def mat(name, base, rough, metal=0.0, emission=None, coat=0.0):
    M[name] = hs.material(name, base, rough, metal, emission=emission, coat=coat) if emission else hs.material(name, base, rough, metal, coat=coat)
    return M[name]


def piece(ob, material, bevel=0.0006, segments=2, angle=35.0, smooth=True):
    """hs.finish() without adding to hs.PARTS (each part joins its own pieces)."""
    hs.finish(ob, M[material] if isinstance(material, str) else material, bevel=bevel, segments=segments, angle=angle, smooth=smooth)
    hs.PARTS.remove(ob)
    return ob


def part(name, pieces, pivot=(0, 0, 0)):
    """Applies modifiers and joins `pieces` into one object named `name` whose origin is `pivot`."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(pieces) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    p = V(pivot)
    ob.data.transform(Matrix.Translation(-p))
    ob.location = p
    for h in hs.HELPERS:
        bpy.data.objects.remove(h)
    hs.HELPERS.clear()
    return ob


def empty(name, loc=(0, 0, 0)):
    ob = hs.link(bpy.data.objects.new(name, None))
    ob.empty_display_size = 0.02
    ob.location = loc
    return ob


def parent(child, par):
    bpy.context.view_layer.update()
    w = child.matrix_world.copy()
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()
    child.matrix_world = w
    return child


def shell(name, x0, x1, r0, r1, phi0, phi1, thick, seg=4):
    """A faceted arc plate around the X axis: angles (deg) from +Z toward -Y, radius r0 at x0 to r1 at x1."""
    bm = bmesh.new()
    rings = []
    for x, r in ((x0, r0), (x1, r1)):
        outer, inner = [], []
        for i in range(seg + 1):
            a = math.radians(phi0 + (phi1 - phi0) * i / seg)
            y, z = -math.sin(a), math.cos(a)
            outer.append(bm.verts.new((x, y * r, z * r)))
            inner.append(bm.verts.new((x, y * (r - thick), z * (r - thick))))
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


def ring(name, x0, x1, r_out, r_in, verts=28):
    """A short tube along X (collar, housing)."""
    n = hs.nverts(verts)
    bm = bmesh.new()
    rings = []
    for x, r in ((x0, r_in), (x0, r_out), (x1, r_out), (x1, r_in)):
        rings.append([bm.verts.new((x, r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n))) for i in range(n)])
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def poly_plate(name, pts, thick, origin=(0, 0, 0), u=(1, 0, 0), v=(0, 0, 1)):
    """A flat outline `pts` [(a, b)] in the plane spanned by u, v at `origin`, extruded `thick` along u × v."""
    u, v = V(u).normalized(), V(v).normalized()
    n = u.cross(v).normalized()
    o = V(origin)
    bm = bmesh.new()
    vs = [bm.verts.new(o + u * a + v * b) for a, b in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=n * thick)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def tube(name, pts, radius, sides=6, radius_end=None):
    """A light round tube through `pts` (straight links, `sides` faces round): strands, cables."""
    pts = [V(p) for p in pts]
    bm = bmesh.new()
    rings = []
    up = None
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if up is None:
            up = t.cross(V((0, 0, 1)) if abs(t.z) < 0.9 else V((1, 0, 0))).normalized()
        up = (up - t * up.dot(t)).normalized()
        side = t.cross(up)
        r = radius if radius_end is None else radius + (radius_end - radius) * i / (n - 1)
        rings.append([bm.verts.new(p + (up * math.cos(2 * math.pi * k / sides) + side * math.sin(2 * math.pi * k / sides)) * r) for k in range(sides)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def helix(name, x0, x1, r0, r1, turns, phase, radius, steps=24, sides=6):
    """A round strand wound round the X axis from x0 to x1 (the braid of the mesh arm)."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = phase + turns * 2 * math.pi * t
        r = r0 + (r1 - r0) * t
        pts.append((x0 + (x1 - x0) * t, r * math.cos(a), r * math.sin(a)))
    return tube(name, pts, radius, sides)


# ---------------------------------------------------------------- the suit forearm and a hand
X_ELBOW, X_WRIST = -0.29, -0.012
R_ELBOW, R_WRIST = 0.050, 0.041


def r_at(x):
    t = (x - X_ELBOW) / (X_WRIST - X_ELBOW)
    return R_ELBOW + (R_WRIST - R_ELBOW) * t


def forearm(side=1, plates=True, top_gap=False):
    """The GS-2 graft suit forearm: weave sleeve, undersuit core, thin graft plates with lit seams, a wrist
    collar. `side` +1 = right arm (outer side -Y), -1 = left. Returns the pieces (one static part)."""
    pcs = []
    pcs.append(piece(hs.lathe_x("sleeve_m", [(-0.47, 0.0), (-0.47, 0.056), (-0.40, 0.057), (-0.33, 0.055), (-0.285, 0.052), (-0.285, 0.0)], verts=28), "weave", bevel=0.0))
    pcs.append(piece(hs.lathe_x("core", [(X_ELBOW - 0.002, 0.0), (X_ELBOW - 0.002, R_ELBOW - 0.004), (X_WRIST, R_WRIST - 0.004), (X_WRIST, 0.0)], verts=28), "weave", bevel=0.0))
    pcs.append(piece(ring("collar", X_WRIST - 0.014, X_WRIST + 0.004, R_WRIST + 0.002, 0.02), "gunmetal", bevel=0.001))
    if plates:
        # Four thin plates round the forearm with bare weave between them (outer, top, inner, under).
        spans = [(50, 130), (-38, 38), (-130, -50), (140, 220)]
        for k, (a0, a1) in enumerate(spans):
            if top_gap and k == 1:
                continue
            a0s, a1s = (a0, a1) if side > 0 else (-a1, -a0)
            pcs.append(piece(shell(f"plate{k}", X_ELBOW + 0.02, X_WRIST - 0.022, r_at(X_ELBOW + 0.02) + 0.0015, r_at(X_WRIST - 0.022) + 0.0015,
                                   a0s, a1s, 0.0045, seg=3), "graft", bevel=0.0008))
        for a in (44, -44):
            y, z = -math.sin(math.radians(a)), math.cos(math.radians(a))
            pcs.append(piece(hs.box("seam", (0.2, 0.0014, 0.0014), (-0.15, y * 0.0465, z * 0.0465)), "glow", bevel=0.0))
    return pcs


FINGERS = {
    # name: (y, z, [segment lengths])
    "index": (0.0295, 0.002, [0.044, 0.027, 0.021]),
    "middle": (0.0105, 0.002, [0.048, 0.030, 0.022]),
    "ring": (-0.0095, 0.002, [0.045, 0.028, 0.021]),
    "little": (-0.0285, 0.0, [0.036, 0.022, 0.018]),
}
PALM_X0, PALM_X1, PALM_HZ = 0.006, 0.090, 0.0165


def _finger_segment(name, x0, length, y, z, w, h, tip):
    pcs = [piece(hs.cyl_y(name + "_joint", h * 0.42, w * 0.92, (x0, y, z), verts=12), "gunmetal", bevel=0.0004),
           piece(hs.box(name + "_core", (length - 0.004, w * 0.78, h * 0.72), (x0 + length / 2, y, z)), "weave", bevel=0.0010),
           piece(hs.box(name + "_shell", (length - 0.006, w * 0.94, h * 0.34), (x0 + length / 2, y, z + h * 0.30)), "graft", bevel=0.0010),
           piece(hs.box(name + "_pad", (length - 0.008, w * 0.80, h * 0.26), (x0 + length / 2, y, z - h * 0.33)), "polymer", bevel=0.0012)]
    if tip:
        pcs.append(piece(hs.cyl_y(name + "_tip", h * 0.40, w * 0.82, (x0 + length - 0.002, y, z), verts=12), "graft", bevel=0.0004))
    return pcs


def hand(side=1):
    """A gloved graft-suit hand on a `wrist` empty at the origin: palm, four fingers of three segments, a thumb.
    `side` +1 = right hand (thumb on +Y, the inner side), -1 = left (mirrored). Returns
    (wrist, palm, {finger: [seg1, seg2, seg3]}, [thumb1, thumb2, thumb3]). Fingers curl about +Y (positive =
    closing); the thumb's first segment is aimed in and down."""
    wrist = empty("wrist", (0.0, 0.0, 0.0))
    pp = [piece(hs.box("palm_core", (PALM_X1 - PALM_X0 - 0.004, 0.08, PALM_HZ * 2 - 0.006), ((PALM_X0 + PALM_X1) / 2, 0.0, 0.0)), "weave", bevel=0.0016),
          piece(hs.box("back_plate", (PALM_X1 - PALM_X0 - 0.014, 0.07, 0.004), ((PALM_X0 + PALM_X1) / 2 - 0.002, 0.0, PALM_HZ - 0.0005)), "graft", bevel=0.0008),
          piece(hs.box("palm_pad", (PALM_X1 - PALM_X0 - 0.016, 0.07, 0.004), ((PALM_X0 + PALM_X1) / 2, 0.0, -PALM_HZ + 0.0005)), "polymer", bevel=0.0012),
          piece(hs.box("knuckle_glow", (0.0016, 0.066, 0.0014), (PALM_X1 - 0.010, 0.0, PALM_HZ + 0.0016)), "glow", bevel=0.0),
          piece(hs.cyl_between("thumb_mount", (0.016, side * 0.041, -0.004), (0.034, side * 0.047, -0.010), 0.0085, verts=14), "gunmetal", bevel=0.0006)]
    palm = part("palm", pp)
    parent(palm, wrist)
    fingers = {}
    for fname, (y, z, lens) in FINGERS.items():
        x = PALM_X1
        prev = palm
        segs = []
        for k, L in enumerate(lens):
            w = 0.0172 * (1.0 - 0.06 * k)
            h = 0.0162 * (1.0 - 0.08 * k)
            seg = part(f"{fname}_{k + 1}", _finger_segment(f"{fname}{k}", x, L, side * y, z, w, h, k == len(lens) - 1), pivot=(x, side * y, z))
            parent(seg, prev)
            segs.append(seg)
            prev = seg
            x += L
        fingers[fname] = segs
    base = V((0.030, side * 0.046, -0.008))
    tx = base.x
    tsegs = []
    for k, L in enumerate([0.040, 0.030, 0.024]):
        w = 0.019 * (1.0 - 0.05 * k)
        h = 0.017 * (1.0 - 0.06 * k)
        tsegs.append(part(f"thumb_{k + 1}", _finger_segment(f"thumb{k}", tx, L, base.y, base.z, w, h, k == 2), pivot=(tx, base.y, base.z)))
        tx += L
    for k in (1, 2):
        parent(tsegs[k], tsegs[k - 1])
    tsegs[0].rotation_euler = (math.radians(-20 * side), math.radians(18), math.radians(38 * side))
    parent(tsegs[0], palm)
    return wrist, palm, fingers, tsegs


# ---------------------------------------------------------------- animation
def capture_rest():
    """Call once the tree is built, before keying."""
    bpy.context.view_layer.update()
    for ob in bpy.data.objects:
        ob.rotation_mode = "XYZ"
        REST[ob.name] = (ob.location.copy(), ob.rotation_euler.copy(), ob.scale.copy())


def key(ob, frame, dloc=(0, 0, 0), drot=(0, 0, 0), scale=None):
    """Keys `ob` at `frame` as rest + offset (location m, rotation deg); `scale` multiplies the rest scale."""
    loc, rot, scl = REST[ob.name]
    ob.location = loc + V(dloc)
    ob.rotation_euler = (rot[0] + math.radians(drot[0]), rot[1] + math.radians(drot[1]), rot[2] + math.radians(drot[2]))
    ob.keyframe_insert("location", frame=frame)
    ob.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        s = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
        ob.scale = (scl[0] * s[0], scl[1] * s[1], scl[2] * s[2])
        ob.keyframe_insert("scale", frame=frame)


def track(ob, keys):
    """keys: [(frame, dloc, drot)] or [(frame, dloc, drot, scale)]."""
    for k in keys:
        key(ob, *k)


def hold(ob, end):
    """A static part still needs keys so it is in the clip."""
    track(ob, [(0, (0, 0, 0), (0, 0, 0)), (end, (0, 0, 0), (0, 0, 0))])


def curl(fingers, tsegs, f0, f1, end, open_deg=(8, 12, 8), fist_deg=(82, 92, 58), which=("index", "middle", "ring", "little"), stagger=2):
    """Fingers from relaxed to curled between f0 and f1 (index first)."""
    for i, fname in enumerate(FINGERS):
        segs = fingers[fname]
        a = f0 + i * stagger
        closes = fname in which
        for k, seg in enumerate(segs):
            o = open_deg[k] + i * 2
            c = fist_deg[k] if closes else o + 4
            track(seg, [(0, (0, 0, 0), (0, o, 0)), (a, (0, 0, 0), (0, o, 0)), (f1 + i * stagger, (0, 0, 0), (0, c, 0)), (end, (0, 0, 0), (0, c, 0))])
    if tsegs:
        s = 1.0 if tsegs[0].rotation_euler[2] > 0 else -1.0
        track(tsegs[0], [(0, (0, 0, 0), (0, 0, 0)), (f0, (0, 0, 0), (0, 0, 0)), (f1, (0, 0, 0), (18 * s, 6, -40 * s)), (end, (0, 0, 0), (18 * s, 6, -40 * s))])
        track(tsegs[1], [(0, (0, 0, 0), (0, 10, 0)), (f0, (0, 0, 0), (0, 10, 0)), (f1, (0, 0, 0), (0, 40, 0)), (end, (0, 0, 0), (0, 40, 0))])
        track(tsegs[2], [(0, (0, 0, 0), (0, 8, 0)), (f0, (0, 0, 0), (0, 8, 0)), (f1, (0, 0, 0), (0, 35, 0)), (end, (0, 0, 0), (0, 35, 0))])


def to_nla(name="deploy"):
    """Every part's keys onto an NLA track named `name`, so the exporter merges them into one clip."""
    for ob in bpy.data.objects:
        ad = ob.animation_data
        if ad is None or ad.action is None:
            continue
        act = ad.action
        slot = ad.action_slot
        tr = ad.nla_tracks.new()
        tr.name = name
        strip = tr.strips.new(name, 0, act)
        if slot is not None and hasattr(strip, "action_slot"):
            strip.action_slot = slot
        ad.action = None


def tri_count():
    return sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in bpy.data.objects if ob.type == "MESH")


def export(path, animated=True):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    if animated:
        to_nla()
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_apply=True,
                              export_animations=animated, export_animation_mode="NLA_TRACKS",
                              export_merge_animation="NLA_TRACK", export_force_sampling=True, export_frame_range=True,
                              export_optimize_animation_size=False, export_extras=False,
                              export_yup=True, export_cameras=False, export_lights=False)
    print(f"{M['tag']}: exported {path} ({tri_count()} triangles)")


# ---------------------------------------------------------------- preview
def render_previews(stem, views, aim=(-0.05, 0, 0)):
    """views: {name: (camera location, target, vertical fov deg or 0 for a 40 mm lens)}. Writes one strip per
    view (<stem>_<view>.png): the frames in --frames side by side."""
    w, h = (int(x) for x in args.res.split("x"))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("night")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.022, 0.03, 1)
    scene.world = world

    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.color, ld.size = energy, color, size
        ob = hs.link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (V(aim) - V(loc)).to_track_quat("-Z", "Y").to_euler()

    area("key", (-0.3, -0.9, 0.8), 34, 1.0, (1.0, 0.9, 0.85))
    area("neon_l", (0.4, 0.9, 0.3), 20, 0.8, (1.0, 0.35, 0.45))
    area("neon_r", (0.6, -0.8, -0.1), 16, 0.8, (0.35, 0.7, 1.0))
    area("top", (0.0, 0.0, 0.9), 12, 1.2, (0.8, 0.85, 1.0))
    cam = hs.link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    scene.camera = cam
    frames = [int(f) for f in args.frames.split(",") if f]
    import numpy as np
    for view in [v for v in args.views.split(",") if v]:
        loc, target, fov = views[view]
        d = cam.data
        d.clip_start = 0.01
        if fov:
            d.sensor_fit = "VERTICAL"
            d.angle = math.radians(fov)
        else:
            d.sensor_fit = "AUTO"
            d.lens = 40
        cam.location = loc
        cam.rotation_euler = (V(target) - V(loc)).to_track_quat("-Z", "Y").to_euler()
        tiles = []
        for f in frames:
            scene.frame_set(f)
            scene.render.filepath = f"{stem}_{view}_{f:02d}.png"
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(scene.render.filepath)
            tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
            bpy.data.images.remove(img)
            os.remove(scene.render.filepath)
        # A grid two frames wide (image rows run bottom to top).
        while len(tiles) % 2:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.concatenate(tiles[i:i + 2], axis=1) for i in range(0, len(tiles), 2)]
        strip = np.concatenate(rows[::-1], axis=0)
        out = bpy.data.images.new("strip", strip.shape[1], strip.shape[0], alpha=False)
        out.pixels.foreach_set(strip.ravel())
        out.filepath_raw = f"{stem}_{view}.png"
        out.file_format = "PNG"
        out.save()
        print(f"{M['tag']}: preview {out.filepath_raw}")


def finish(root_objects, end, views):
    """Exports and renders according to the arguments."""
    print(f"{M['tag']}: {tri_count()} triangles")
    if args.preview:
        render_previews(args.preview.rsplit(".", 1)[0], views)
    if args.out:
        export(args.out)
