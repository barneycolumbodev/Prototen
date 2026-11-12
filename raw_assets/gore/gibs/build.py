"""Gibs: the pieces a body comes apart into (docs/design.md §5.5, 2026-11-11).

Owner (2026-11-11): Soldier of Fortune style gore, "decapitations,
dismemberments, gibbing". Severed limbs and heads are cut from the enemy's
own mesh (raw_assets/characters/triad/build.py); these are the inside of a
body for a torso blown apart or a head destroyed: a run of ribs off the
sternum, a stretch of vertebrae, a pelvis fragment, organs, a coil of gut,
a skull cap with hair, a lower jaw with teeth, and torn meat with fat and
skin on one side.

Each piece is small, low-poly (≤ ~450 triangles), vertex-coloured (wet
meat, fat, bone, skin, hair) and centred on its own origin with real
dimensions. One glTF, one mesh per piece, named gib_*.

Run:
  tools/blender.sh raw_assets/gore/gibs/build.py --out assets/gore/gibs.gltf --preview docs/previews/gibs.png
"""
import argparse
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector as V, Matrix, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COL = scene.collection
random.seed(11)

MEAT = (0.40, 0.045, 0.04)
FRESH = (0.55, 0.06, 0.05)
FAT = (0.82, 0.7, 0.45)
BONE = (0.86, 0.8, 0.66)
SKIN = (0.62, 0.43, 0.32)
HAIR = (0.03, 0.025, 0.02)
GUT = (0.62, 0.32, 0.30)
LIVER = (0.36, 0.06, 0.06)


def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def new_bm():
    bm = bmesh.new()
    bm.loops.layers.color.new("Col")
    return bm


def paint(bm, fn):
    """fn(vertex co, face normal) -> rgb."""
    cl = bm.loops.layers.color["Col"]
    for f in bm.faces:
        for lp in f.loops:
            lp[cl] = lin(fn(lp.vert.co, lp.vert.normal))


def lump(bm, centre, radius, squash=(1, 1, 1), rough=0.3, subdiv=2, seed=0):
    """A noisy blob (organs, meat)."""
    geom = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in geom["verts"]:
        n = v.co.normalized()
        d = noise.noise(n * 2.3 + V((seed, seed * 1.7, 0))) * rough + noise.noise(n * 6.0 + V((0, seed, 3))) * rough * 0.4
        v.co = V((n.x * squash[0], n.y * squash[1], n.z * squash[2])) * radius * (1 + d) + V(centre)
    return geom["verts"]


def tube(bm, pts, r, sides=6, r_fn=None):
    """A tube along `pts` (ribs, gut). Ends capped."""
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a)
        rr = r_fn(i / (len(pts) - 1)) if r_fn else r
        ring = [bm.verts.new(p + (a * math.cos(k / sides * math.tau) + b * math.sin(k / sides * math.tau)) * rr) for k in range(sides)]
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])


def finish(bm, name, fn):
    bm.normal_update()
    paint(bm, fn)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    mat = bpy.data.materials.new(name + "_mat")
    nt = mat.node_tree
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.32
    me.materials.append(mat)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"[gibs] {name}: {tris} tris")
    return ob


def wet(base, co, k=1.0):
    n = noise.noise(co * 40.0) * 0.5 + 0.5
    return tuple(min(1.0, c * (0.75 + 0.5 * n * k)) for c in base)


def ribs():
    bm = new_bm()
    # Four ribs curving off a strip of sternum, torn meat between them.
    for i in range(4):
        y = -0.035 + i * 0.026
        pts = []
        for k in range(9):
            t = k / 8
            ang = -0.2 + t * 1.5
            pts.append(V((math.sin(ang) * 0.11, y - t * 0.02, math.cos(ang) * 0.09 - 0.05)))
        tube(bm, pts, 0.0065, 5, lambda t: 0.0065 * (1.0 - 0.3 * t))
    s = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    for v in s:
        v.co = V((v.co.x * 0.03, v.co.y * 0.12, v.co.z * 0.012)) + V((-0.02, 0.0, 0.04))
    lump(bm, (0.04, 0.0, 0.035), 0.035, (1.4, 1.6, 0.45), 0.35, 1, 3)
    return finish(bm, "gib_ribs", lambda co, n: wet(BONE, co) if co.z < 0.02 or co.x > 0.075 else wet(MEAT, co))


def spine():
    bm = new_bm()
    for i in range(3):
        z = i * 0.034
        c = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.02, radius2=0.02, depth=0.024)["verts"]
        for v in c:
            v.co = v.co + V((0, 0, z))
        p = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in p:
            v.co = V((v.co.x * 0.008, v.co.y * 0.04, v.co.z * 0.014)) + V((0, 0.036, z - 0.004))
        w = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in w:
            v.co = V((v.co.x * 0.07, v.co.y * 0.01, v.co.z * 0.01)) + V((0, 0.022, z))
    lump(bm, (0.0, 0.03, 0.034), 0.03, (1.5, 0.8, 1.6), 0.4, 1, 5)
    return finish(bm, "gib_spine", lambda co, n: wet(BONE, co) if abs(co.x) < 0.024 and co.y < 0.03 else wet(FRESH if co.z > 0.04 else MEAT, co))


def pelvis():
    bm = new_bm()
    pts = [V((math.cos(a) * 0.075, math.sin(a) * 0.05, math.sin(a * 2) * 0.012)) for a in [i / 10 * math.pi * 1.1 for i in range(11)]]
    tube(bm, pts, 0.016, 6, lambda t: 0.016 + 0.01 * math.sin(t * math.pi))
    lump(bm, (0.0, 0.035, 0.0), 0.03, (1.8, 0.7, 0.9), 0.4, 1, 7)
    return finish(bm, "gib_pelvis", lambda co, n: wet(BONE, co) if co.y < 0.03 else wet(MEAT, co))


def organ(name, size, col, seed):
    bm = new_bm()
    lump(bm, (0, 0, 0), size, (1.3, 0.85, 0.7), 0.28, 3, seed)
    return finish(bm, name, lambda co, n: wet(col, co, 1.3))


def gut():
    bm = new_bm()
    pts = []
    for k in range(26):
        t = k / 25 * math.tau * 1.4
        r = 0.045 + 0.012 * math.sin(t * 2.3)
        pts.append(V((math.cos(t) * r, math.sin(t) * r, (k / 25 - 0.5) * 0.05 + 0.008 * math.sin(t * 3))))
    tube(bm, pts, 0.012, 7)
    return finish(bm, "gib_gut", lambda co, n: wet(GUT, co, 1.4))


def skull():
    bm = new_bm()
    g = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.085)
    for v in list(g["verts"]):
        if v.co.z < 0.02:
            pass
    dead = [v for v in g["verts"] if v.co.z < 0.015]
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
    for v in bm.verts:
        v.co.z -= 0.03
        v.co *= V((1.0, 1.15, 1.0))
    # Ragged edge.
    for v in bm.verts:
        if v.co.z < -0.005:
            v.co.z += noise.noise(v.co * 50) * 0.01
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.008)
    def col(co, n):
        if n.dot(co.normalized()) < -0.2:
            return wet(FRESH, co)  # the inside
        if co.z > -0.012:
            return HAIR
        return wet(BONE, co)  # the broken rim
    return finish(bm, "gib_skull", col)


def jaw():
    bm = new_bm()
    pts = [V((math.sin(a) * 0.045, math.cos(a) * 0.05 - 0.02, 0)) for a in [-1.35 + i / 10 * 2.7 for i in range(11)]]
    tube(bm, pts, 0.011, 5, lambda t: 0.011 + 0.005 * (1 - abs(t - 0.5) * 2))
    for i in range(9):
        a = -1.0 + i / 8 * 2.0
        c = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.004, radius2=0.003, depth=0.01)["verts"]
        for v in c:
            v.co = v.co + V((math.sin(a) * 0.045, math.cos(a) * 0.05 - 0.02, 0.012))
    lump(bm, (0.0, 0.0, -0.012), 0.03, (1.4, 1.2, 0.5), 0.4, 1, 9)
    return finish(bm, "gib_jaw", lambda co, n: (0.95, 0.92, 0.85) if co.z > 0.008 else (wet(SKIN, co) if co.z < -0.02 else wet(MEAT, co)))


def meat(name, size, seed):
    bm = new_bm()
    lump(bm, (0, 0, 0), size, (1.4, 1.0, 0.65), 0.45, 3, seed)

    def col(co, n):
        if n.z > 0.55:
            return SKIN
        if n.z > 0.3:
            return wet(FAT, co)
        return wet(FRESH if noise.noise(co * 30 + V((seed, 0, 0))) > 0 else MEAT, co)
    return finish(bm, name, col)


pieces = [ribs(), spine(), pelvis(), organ("gib_organ_a", 0.045, LIVER, 13), organ("gib_organ_b", 0.032, FRESH, 17),
          gut(), skull(), jaw(), meat("gib_meat_a", 0.04, 21), meat("gib_meat_b", 0.028, 23), meat("gib_meat_c", 0.05, 29)]

if args.out:
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    kw = dict(filepath=args.out, export_format="GLTF_SEPARATE", use_selection=True, export_apply=True)
    # Only the painted set, as COLOR_0 (Godot reads the first set only).
    bpy.ops.export_scene.gltf(**kw, export_vertex_color="NAME", export_vertex_color_name="Col",
                              export_all_vertex_colors=False)
    print("[gibs] exported", args.out)

if args.preview:
    for i, ob in enumerate(pieces):
        ob.location = V(((i % 4) * 0.2 - 0.3, 0, -(i // 4) * 0.2 + 0.2))
        ob.rotation_euler = (0.5, 0.3, 0.4 * i)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 700
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("w")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.3, 0.31, 0.33, 1)
    scene.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), 0, math.radians(30))
    COL.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    COL.objects.link(cam)
    cam.location = (0, -1.25, 0.05)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.lens = 50
    scene.camera = cam
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("[gibs] preview", args.preview)
