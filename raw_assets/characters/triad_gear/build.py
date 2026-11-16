"""Gear for the new triad roles (docs/design.md §8.8): what each type wears or carries on his body.

Owner, 2026-11-16: "Enemies and how they look is the absolute weakest part of the game so far." Every
type gets a silhouette of its own, so a player reads what a man does before he does it:

  kit shield      a stolen Hong Kong police ballistic shield (POLICE 警察, a viewport, scuffs and
                  strike marks) held out in front on the chest; a riot helmet with the smoked
                  visor down.                                                  (Shield man)
  kit dao         the graft: a steel guard plate bolted into the outside of the left forearm from
                  the elbow to the wrist, with a hydraulic brace and scar tissue round the bolts.
                                                                               (Dao swordsman)
  kit antiaug     a jammer backpack (two whip antennas, a phased panel, a cooling grille, a lamp
                  strip), shoulder straps, a chest rig with three EMP grenades, a full-face
                  respirator with a side filter.                            (Anti-augment specialist)
  kit gunner      two belts of linked 7.62 crossed over the chest.          (Gunner)
  kit firebomber  a canvas satchel of bottles at the left hip on a strap over the right shoulder,
                  a dark red bandana over the nose and mouth.                (Firebomber)

Each piece is modelled in the triad's rest pose (rig space: Blender Z up, the man faces -Y, his left
is +X; raw_assets/characters/triad/common.py), then moved into the local frame of the bone it rides
on and turned for glTF, so the game hangs it on a BoneAttachment3D with no offset (EnemyGear). The
glTF node names are "<piece>__<bone>" with the bone's "." written "_" (forearm.L -> forearm_L).
Sizes are the unscaled rig's; the game scales the whole man (EnemyConfig.body_scale).

HIGH and LOW are built from the same code, HIGH is baked onto LOW per kit (one texture set per kit,
raw_assets/_lib/bakeutil.py), then the kit is split back into its pieces.

Run (about 4 minutes with bakes; --fast renders HIGH on the man without baking):
  tools/blender.sh raw_assets/characters/triad_gear/build.py --out assets/characters/triad_gear \
      --preview docs/previews/triad_gear.png
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
sys.path.insert(0, os.path.join(HERE, "..", "triad"))
import bakeutil  # noqa: E402
import hardsurface as hs  # noqa: E402

V = Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--tex", type=int, default=1024)
ap.add_argument("--only", default="")
ap.add_argument("--fast", action="store_true")
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
import common  # noqa: E402  (triad skeleton; needs bpy reset first)
common.init()

# ---------------------------------------------------------------- bone frames
ARM = None


def rest_matrices():
    """Rest matrices (rig space) of every bone, from the same BONES as the triad build."""
    global ARM
    data = bpy.data.armatures.new("gear_rig")
    ARM = bpy.data.objects.new("gear_rig", data)
    bpy.context.scene.collection.objects.link(ARM)
    bpy.context.view_layer.objects.active = ARM
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, parent, roll_vec in common.BONES:
        b = data.edit_bones.new(name)
        b.head, b.tail = head, tail
        b.align_roll(roll_vec)
        if parent:
            b.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return {b.name: b.matrix_local.copy() for b in data.bones}


REST = rest_matrices()
J = common.J

# ---------------------------------------------------------------- materials
def stencil_image():
    """White "POLICE 警察" on black for the shield's face, drawn with the vendored Noto Sans TC."""
    import cjk
    from PIL import Image, ImageDraw
    w, h = 1024, 256
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    fs = cjk.FontSet("sans")
    size = 150
    text = "警察"
    tw = fs.width(text, size)
    fs.draw(d, ((w - tw) / 2, 0), text, size, 255)
    # Latin from Pillow's built-in scalable font (the vendored Noto subset only holds the signs' glyphs).
    from PIL import ImageFont
    lat = "P O L I C E"
    font = ImageFont.load_default(size=84)
    lw = d.textlength(lat, font=font)
    d.text(((w - lw) / 2, 158), lat, fill=255, font=font)
    path = os.path.join(bpy.app.tempdir or "/tmp", "shield_stencil.png")
    img.save(path)
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = "Non-Color"
    return im


def shield_material():
    """Black polyethylene with the white stencil projected from the front (rig X, Z)."""
    mat = hs.material("gear_shield", (0.025, 0.026, 0.028), 0.6, 0.0, wear=(0.2, 0.2, 0.2), wear_rough=0.4,
                      bump_scale=600.0, bump_strength=0.15)
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    # Object coordinates (rig space): the stencil spans x -0.22..0.28, z 1.3..1.425 on the face (u = 2x + 0.44).
    mp.inputs["Location"].default_value = (0.44, 0.0, -10.4)
    mp.inputs["Scale"].default_value = (2.0, 1.0, 8.0)
    sep = N.new("ShaderNodeSeparateXYZ")
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    L.new(mp.outputs["Vector"], sep.inputs["Vector"])
    L.new(sep.outputs["X"], comb.inputs["X"])
    L.new(sep.outputs["Z"], comb.inputs["Y"])
    tex = N.new("ShaderNodeTexImage")
    tex.image = stencil_image()
    tex.extension = "CLIP"
    L.new(comb.outputs["Vector"], tex.inputs["Vector"])
    # Only on the front face (normal toward -Y).
    geo = N.new("ShaderNodeNewGeometry")
    front = N.new("ShaderNodeMath")
    front.operation = "LESS_THAN"
    sepn = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], sepn.inputs["Vector"])
    L.new(sepn.outputs["Y"], front.inputs[0])
    front.inputs[1].default_value = -0.5
    m = N.new("ShaderNodeMath")
    m.operation = "MULTIPLY"
    L.new(tex.outputs["Color"], m.inputs[0])
    L.new(front.outputs[0], m.inputs[1])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    old = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].is_linked else None
    if old:
        L.new(old, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = (0.025, 0.026, 0.028, 1)
    mix.inputs["B"].default_value = (0.78, 0.78, 0.76, 1)
    L.new(m.outputs[0], mix.inputs["Factor"])
    L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


M = {
    "steel": hs.material("gear_steel", (0.05, 0.052, 0.056), 0.38, 0.9, wear=(0.45, 0.45, 0.46), wear_rough=0.2,
                         bump_scale=800.0, bump_strength=0.1),
    "plate": hs.material("gear_plate", (0.11, 0.115, 0.12), 0.32, 1.0, wear=(0.55, 0.55, 0.56), wear_rough=0.15,
                         bump_scale=300.0, bump_strength=0.25),
    "black": hs.material("gear_black", (0.025, 0.025, 0.027), 0.55, 0.2, wear=(0.2, 0.2, 0.2)),
    "olive": hs.material("gear_olive", (0.075, 0.08, 0.055), 0.75, 0.0, wear=(0.17, 0.17, 0.13), wear_rough=0.6,
                         bump_scale=2400.0, bump_strength=0.35),
    "canvas": hs.material("gear_canvas", (0.2, 0.17, 0.12), 0.85, 0.0, wear=(0.32, 0.28, 0.2), wear_rough=0.7,
                          bump_scale=2600.0, bump_strength=0.45),
    "nylon": hs.material("gear_nylon", (0.03, 0.03, 0.032), 0.75, 0.0, bump_scale=3000.0, bump_strength=0.4),
    "rubber": hs.material("gear_rubber", (0.022, 0.022, 0.024), 0.6, 0.0, bump_scale=1600.0, bump_strength=0.15),
    "lens": hs.material("gear_lens", (0.02, 0.025, 0.03), 0.04, 0.0),
    "visor": hs.material("gear_visor", (0.03, 0.04, 0.05), 0.05, 0.0),
    "brass": hs.material("gear_brass", (0.72, 0.5, 0.18), 0.28, 1.0, wear=(0.85, 0.66, 0.3)),
    "copper": hs.material("gear_copper", (0.8, 0.38, 0.18), 0.3, 1.0),
    "lamp": hs.material("gear_lamp", (0.1, 0.5, 0.9), 0.3, 0.0, emission=((0.3, 0.75, 1.0), 5.0)),
    "red_lamp": hs.material("gear_red_lamp", (0.8, 0.05, 0.03), 0.3, 0.0, emission=((1.0, 0.1, 0.05), 5.0)),
    "scar": hs.material("gear_scar", (0.38, 0.17, 0.14), 0.55, 0.0, bump_scale=900.0, bump_strength=0.5),
    "bandana": hs.material("gear_bandana", (0.24, 0.025, 0.02), 0.85, 0.0, bump_scale=2600.0, bump_strength=0.4),
    "glass": hs.material("gear_glass", (0.07, 0.17, 0.07), 0.06, 0.0),
    "rag": hs.material("gear_rag", (0.42, 0.36, 0.26), 0.9, 0.0, bump_scale=900.0, bump_strength=0.6),
    "shield": shield_material(),
}
MATERIALS = list(M.values())


def F(ob, mat, bevel=0.0015, seg=2, angle=40.0):
    return hs.finish(ob, M[mat], bevel=bevel, segments=seg, angle=angle)


def box(name, mat, size, loc, rot=(0, 0, 0), bevel=0.0015):
    return F(hs.box(name, size, loc, rot), mat, bevel=bevel)


def cyl(name, mat, p0, p1, r, verts=16, bevel=0.0008, r2=None):
    return F(hs.cyl_between(name, p0, p1, r, verts=verts, radius2=r2), mat, bevel=bevel)


def high():
    return hs.D is hs.HIGH


def shell(name, centre, radii, keep, thick=0.006, u=24, v=16):
    """Part of an ellipsoid shell (centre, radii in rig space); `keep(p)` picks the vertices to keep."""
    bm = bmesh.new()
    # Same segments in HIGH and LOW: a coarser LOW shell would sit millimetres inside the HIGH one
    # between its edges, further than the bake's rays reach (stripes).
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    for vt in bm.verts:
        vt.co = V((centre[0] + vt.co.x * radii[0], centre[1] + vt.co.y * radii[1], centre[2] + vt.co.z * radii[2]))
    gone = [vt for vt in bm.verts if not keep(vt.co)]
    bmesh.ops.delete(bm, geom=gone, context="VERTS")
    ob = hs.mesh_object(name, bm)
    sol = ob.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    return ob


# ====================================================================== shield man
def shield():
    """Ballistic shield, 0.56 x 0.95 m, curved about the vertical, held out in front of the chest."""
    cx, cy, z0, z1, w = 0.03, -0.4, 0.82, 1.77, 0.56
    R = 1.4  # curvature radius
    n = hs.nverts(16)
    bm = bmesh.new()
    grid = []
    for j, zz in enumerate((z0, z0 + 0.04, z1 - 0.04, z1)):
        row = []
        for i in range(n + 1):
            a = (i / n - 0.5) * (w / R)
            x = cx + R * math.sin(a)
            y = cy + R * (1.0 - math.cos(a))
            row.append((x, y, zz))
        grid.append(row)
    # front face and back face (thickness 0.03 along +Y)
    vf = [[bm.verts.new(p) for p in row] for row in grid]
    vb = [[bm.verts.new((p[0], p[1] + 0.028, p[2])) for p in row] for row in grid]
    for j in range(len(grid) - 1):
        for i in range(n):
            bm.faces.new((vf[j][i], vf[j][i + 1], vf[j + 1][i + 1], vf[j + 1][i]))
            bm.faces.new((vb[j][i + 1], vb[j][i], vb[j + 1][i], vb[j + 1][i + 1]))
    for j in range(len(grid) - 1):
        for side, i in ((0, 0), (1, n)):
            q = (vf[j][i], vf[j + 1][i], vb[j + 1][i], vb[j][i])
            bm.faces.new(q if side else tuple(reversed(q)))
    for j, row in ((0, 0), (len(grid) - 1, 1)):
        for i in range(n):
            q = (vf[j][i], vb[j][i], vb[j][i + 1], vf[j][i + 1])
            bm.faces.new(q if row == 0 else tuple(reversed(q)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sh = hs.mesh_object("shield_body", bm)
    # Viewport window at eye height.
    hs.cut(sh, hs.box("viewport_cut", (0.26, 0.2, 0.085), (cx, cy, 1.6)))
    F(sh, "shield", bevel=0.006, seg=2)
    box("viewport_glass", "visor", (0.27, 0.035, 0.094), (cx, cy + 0.016, 1.6), bevel=0.003)
    box("viewport_frame", "black", (0.3, 0.02, 0.012), (cx, cy - 0.006, 1.652), bevel=0.003)
    box("viewport_frame2", "black", (0.3, 0.02, 0.012), (cx, cy - 0.006, 1.548), bevel=0.003)
    # Rubber edge trim all round.
    for zz in (z0 + 0.005, z1 - 0.005):
        F(hs.cyl_x("trim", 0.013, cx - w / 2 + 0.03, cx + w / 2 - 0.03, verts=8, z=zz, y=cy + 0.014), "rubber",
          bevel=0.0)
    for sx in (-1, 1):
        a = sx * 0.5 * (w / R)
        x = cx + R * math.sin(a)
        y = cy + R * (1.0 - math.cos(a)) + 0.014
        cyl("trim_side", "rubber", (x, y, z0), (x, y, z1), 0.013, verts=8, bevel=0.0)
    # Back: the arm strap and the vertical handle the left hand holds (HANDLE in the clips).
    cyl("handle", "black", (0.13, cy + 0.075, 1.14), (0.13, cy + 0.075, 1.3), 0.016, verts=12)
    for zz in (1.13, 1.31):
        box("handle_post", "black", (0.03, 0.06, 0.02), (0.13, cy + 0.05, zz), bevel=0.003)
    box("arm_strap", "nylon", (0.09, 0.012, 0.05), (0.02, cy + 0.06, 1.24), bevel=0.003)
    # Strike marks: a few pocked dents on the face (HIGH only, baked into the normal map).
    if high():
        import random
        rnd = random.Random(7)
        for k in range(14):
            x = cx + rnd.uniform(-0.22, 0.22)
            zz = rnd.uniform(0.9, 1.5)
            r = rnd.uniform(0.007, 0.014)
            F(hs.cyl_y(f"strike{k}", r, 0.003, (x, cy - 0.0005, zz), verts=12), "steel", bevel=0.0012)


def helmet():
    """Riot helmet: a shell over the cranium, the smoked visor down over the face, a neck flap."""
    c = (0.0, 0.01, 1.69)
    F(shell("helmet_shell", c, (0.105, 0.122, 0.112), lambda p: p.z > 1.62 or p.y > 0.0, thick=0.008), "black",
      bevel=0.0)
    F(shell("helmet_rim", (0.0, 0.01, 1.66), (0.108, 0.125, 0.05), lambda p: abs(p.z - 1.66) < 0.014, thick=0.01),
      "rubber", bevel=0.0)
    F(shell("visor", (0.0, -0.02, 1.64), (0.112, 0.12, 0.12),
            lambda p: p.y < -0.06 and 1.52 < p.z < 1.73, thick=0.005), "visor", bevel=0.0)
    for sx in (1, -1):
        cyl("visor_pivot", "black", (0.108 * sx, -0.02, 1.66), (0.118 * sx, -0.02, 1.66), 0.018, verts=14)
    F(shell("neck_flap", (0.0, 0.03, 1.6), (0.1, 0.11, 0.1), lambda p: p.y > 0.05 and 1.52 < p.z < 1.62, thick=0.006),
      "nylon", bevel=0.0)


# ====================================================================== dao swordsman
def forearm_plate():
    """A curved steel plate bolted into the outside of the left forearm, elbow to wrist."""
    el, wr = J["elbow.L"], J["wrist.L"]
    ax = (wr - el).normalized()
    out = (V((1, 0, 0)) - ax * ax.x).normalized()
    side = ax.cross(out).normalized()
    bm = bmesh.new()
    n = hs.nverts(12)
    rows = []
    for t, r in ((-0.06, 0.05), (0.05, 0.058), (0.55, 0.054), (0.95, 0.047), (1.08, 0.04)):
        p = el + (wr - el) * t
        ring = []
        for i in range(n + 1):
            a = (i / n - 0.5) * math.radians(200)
            ring.append(bm.verts.new(p + (out * math.cos(a) + side * math.sin(a)) * r))
        rows.append(ring)
    for a, b in zip(rows, rows[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    ob = hs.mesh_object("plate", bm)
    sol = ob.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.009
    sol.offset = 1.0
    F(ob, "plate", bevel=0.0025)
    # A raised spine along the plate (the striking face) and ribs across it.
    cyl("spine", "plate", el + ax * -0.02 + out * 0.062, el + ax * 0.27 + out * 0.054, 0.009, verts=8)
    for t in (0.2, 0.45, 0.7):
        p = el + (wr - el) * t
        cyl("rib", "plate", p + out * 0.05 + side * -0.042, p + out * 0.05 + side * 0.042, 0.005, verts=8)
    # Bolts into the bone, with scar tissue round each where they go into the flesh.
    for t, s in ((0.08, 1), (0.08, -1), (0.6, 1), (0.6, -1), (0.92, 1), (0.92, -1)):
        p = el + (wr - el) * t + side * 0.05 * s + out * 0.012
        cyl("bolt", "steel", p, p + side * 0.014 * s, 0.006, verts=6)
        if high():
            box("scar", "scar", (0.024, 0.024, 0.006), p - side * 0.004 * s, bevel=0.003)
    # Hydraulic brace on the inside of the elbow up to the plate.
    sh = J["shoulder.L"]
    up = el + (sh - el) * 0.3
    cyl("brace_rod", "steel", up + out * 0.04, el + ax * 0.08 + out * 0.055, 0.006, verts=8)
    cyl("brace_cyl", "black", up + out * 0.04, up + (el - up) * 0.55 + out * 0.045, 0.011, verts=10)
    box("brace_band", "plate", (0.1, 0.1, 0.03), up + out * 0.0, bevel=0.004)


# ====================================================================== anti-augment specialist
def jammer():
    """Jammer backpack: a ribbed case on the back, two whip antennas, a phased panel, a lamp strip."""
    c = V((0.0, 0.215, 1.25))
    box("case", "olive", (0.29, 0.13, 0.36), c, bevel=0.012)
    box("case_lid", "olive", (0.3, 0.14, 0.03), c + V((0, 0, 0.19)), bevel=0.008)
    for k in range(6):
        box(f"fin{k}", "black", (0.012, 0.03, 0.22), c + V((-0.1 + k * 0.04, 0.075, -0.02)), bevel=0.002)
    box("panel", "black", (0.2, 0.012, 0.12), c + V((0.0, 0.07, 0.12)), bevel=0.003)
    if high():
        for i in range(4):
            for j in range(3):
                box("elem", "copper", (0.03, 0.004, 0.026), c + V((-0.07 + i * 0.047, 0.078, 0.085 + j * 0.034)),
                    bevel=0.001)
    box("lamps", "lamp", (0.16, 0.006, 0.014), c + V((0.0, 0.07, -0.16)), bevel=0.001)
    box("red", "red_lamp", (0.014, 0.006, 0.014), c + V((0.11, 0.07, -0.16)), bevel=0.001)
    for sx in (1, -1):
        base = c + V((0.12 * sx, 0.02, 0.2))
        cyl("ant_base", "black", base, base + V((0, 0, 0.04)), 0.012, verts=10)
        cyl("ant", "black", base + V((0, 0, 0.04)), base + V((0.06 * sx, 0.06, 0.62)), 0.0045, verts=6, r2=0.0025)
        cyl("ant_tip", "black", base + V((0.06 * sx, 0.06, 0.6)), base + V((0.063 * sx, 0.063, 0.63)), 0.007, verts=8)
    cyl("cable", "rubber", c + V((-0.13, -0.05, -0.1)), V((-0.17, 0.0, 1.08)), 0.008, verts=8)
    # Shoulder straps: from the case top over the shoulders down the front to the rig.
    for sx in (1, -1):
        pts = [(0.09 * sx, 0.16, 1.4), (0.1 * sx, 0.06, 1.47), (0.11 * sx, -0.07, 1.43), (0.1 * sx, -0.125, 1.32),
               (0.095 * sx, -0.13, 1.2)]
        F(hs.tube_path("strap", pts, 0.012, width_scale=1.0), "nylon", bevel=0.0)


def chest_rig():
    """Chest rig with three EMP grenade pouches across the front."""
    box("rig", "olive", (0.26, 0.03, 0.12), (0.0, -0.135, 1.12), bevel=0.008)
    for k, x in enumerate((-0.075, 0.0, 0.075)):
        box(f"pouch{k}", "olive", (0.06, 0.05, 0.08), (x, -0.165, 1.12), bevel=0.008)
        # The grenade tops showing out of each pouch: copper band and a lamp.
        cyl("gren", "olive", (x, -0.165, 1.16), (x, -0.165, 1.2), 0.022, verts=12)
        cyl("gren_coil", "copper", (x, -0.165, 1.17), (x, -0.165, 1.182), 0.0235, verts=12)
        cyl("gren_lamp", "lamp", (x, -0.165, 1.2), (x, -0.165, 1.206), 0.006, verts=8)


def respirator():
    """Full-face respirator: a rubber facepiece from the brow to under the chin, two lenses, a filter."""
    F(shell("mask", (0.0, -0.022, 1.632), (0.09, 0.112, 0.108),
            lambda p: p.y < -0.025 and 1.525 < p.z < 1.725, thick=0.008, u=32, v=20), "rubber", bevel=0.0)
    for sx in (1, -1):
        cyl("lens_ring", "black", (0.034 * sx, -0.112, 1.668), (0.034 * sx, -0.126, 1.668), 0.025, verts=16)
        cyl("lens", "lens", (0.034 * sx, -0.118, 1.668), (0.034 * sx, -0.128, 1.668), 0.021, verts=16, bevel=0.0)
    cyl("voicemitter", "black", (0.0, -0.118, 1.6), (0.0, -0.145, 1.59), 0.024, verts=14)
    cyl("filter_port", "black", (0.04, -0.105, 1.592), (0.066, -0.124, 1.582), 0.021, verts=14)
    cyl("filter", "olive", (0.062, -0.12, 1.584), (0.098, -0.146, 1.57), 0.037, verts=18, bevel=0.003)
    for zz in (1.69, 1.63):
        F(shell("mask_strap", (0.0, 0.01, zz), (0.092, 0.112, 0.02), lambda p: p.y > -0.03, thick=0.004),
          "nylon", bevel=0.0)


# ====================================================================== gunner
def bandoliers():
    """Two belts of linked 7.62 crossed over the chest, each from a shoulder to the other hip."""
    for sx in (1, -1):
        pts = [V((0.13 * sx, 0.04, 1.44)), V((0.09 * sx, -0.1, 1.39)), V((0.0, -0.145, 1.26)),
               V((-0.1 * sx, -0.135, 1.1)), V((-0.155 * sx, -0.05, 0.98))]
        # Resample along the path.
        dense = []
        for a, b in zip(pts, pts[1:]):
            for k in range(10):
                dense.append(a.lerp(b, k / 10))
        dense.append(pts[-1])
        length = sum((b - a).length for a, b in zip(dense, dense[1:]))
        step = 0.016 if high() else 0.024
        s, i, acc = 0.0, 0, 0.0
        while s < length:
            while i < len(dense) - 2 and acc + (dense[i + 1] - dense[i]).length < s:
                acc += (dense[i + 1] - dense[i]).length
                i += 1
            seg = dense[i + 1] - dense[i]
            p = dense[i] + seg.normalized() * (s - acc)
            along = seg.normalized()
            outward = V((p.x * 0.6, p.y - 0.02, 0.0)).normalized()
            across = along.cross(outward).normalized()
            # Each cartridge lies across the belt, bullet pointing up-out of the chest.
            cyl("case", "brass", p - across * 0.018, p + across * 0.02, 0.0058, verts=8, bevel=0.0)
            cyl("tip", "brass", p + across * 0.02, p + across * 0.034, 0.0058, verts=8, bevel=0.0, r2=0.002)
            cyl("link", "black", p - across * 0.008 + outward * 0.002, p + across * 0.004 + outward * 0.002, 0.0068,
                verts=8, bevel=0.0)
            s += step


# ====================================================================== firebomber
def satchel():
    """Canvas satchel at the left hip with three bottles standing in it, rags out of the necks."""
    c = V((0.21, -0.02, 0.9))
    box("bag", "canvas", (0.08, 0.26, 0.2), c, bevel=0.02)
    box("flap", "canvas", (0.086, 0.27, 0.06), c + V((0.004, 0.0, 0.08)), rot=(0.0, 0.0, 0.0), bevel=0.012)
    box("buckle", "brass", (0.01, 0.03, 0.024), c + V((0.048, -0.06, 0.04)), bevel=0.002)
    for k, y in enumerate((-0.07, 0.0, 0.07)):
        b = c + V((0.0, y, 0.1))
        cyl("bottle", "glass", b, b + V((0.0, 0.0, 0.06)), 0.03, verts=12)
        cyl("neck", "glass", b + V((0, 0, 0.06)), b + V((0, 0, 0.12)), 0.011, verts=10, r2=0.0095)
        cyl("rag", "rag", b + V((0, 0, 0.11)), b + V((0.012 * (k - 1), 0.01, 0.17)), 0.009, verts=8, r2=0.005)


def strap():
    pts = [(0.19, -0.06, 1.0), (0.12, -0.13, 1.18), (0.0, -0.14, 1.3), (-0.1, -0.1, 1.42), (-0.14, 0.0, 1.47),
           (-0.08, 0.12, 1.38), (0.06, 0.14, 1.2), (0.19, 0.07, 1.0)]
    F(hs.tube_path("strap", pts, 0.017, width_scale=1.0), "canvas", bevel=0.0)


def bandana():
    """A triangle of dark red cloth tied over the nose and mouth, the knot at the back of the head."""
    F(shell("bandana", (0.0, -0.01, 1.6), (0.084, 0.1, 0.09),
            lambda p: p.y < 0.01 and 1.52 < p.z < 1.648 + 0.3 * min(0.0, p.y + 0.06), thick=0.005), "bandana", bevel=0.0)
    cyl("knot", "bandana", (0.0, 0.1, 1.63), (0.0, 0.13, 1.6), 0.018, verts=10, r2=0.008)


# Pieces: name -> (builder, bone).
KITS = {
    "shield": {"shield": (shield, "chest"), "helmet": (helmet, "head")},
    "dao": {"plate": (forearm_plate, "forearm.L")},
    "antiaug": {"jammer": (jammer, "chest"), "rig": (chest_rig, "chest"), "mask": (respirator, "head")},
    "gunner": {"belts": (bandoliers, "chest")},
    "firebomber": {"satchel": (satchel, "hips"), "strap": (strap, "chest"), "bandana": (bandana, "head")},
}


def build_piece(fn, detail, name):
    hs.set_detail(detail)
    fn()
    ob = hs.join_parts(name)
    return ob


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def to_bone(ob, bone):
    """Rig space -> the bone's local frame (Blender axes), then turned for glTF's Y-up."""
    ob.data.transform(REST[bone].inverted())
    ob.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))


def separate(ob, ids):
    """Splits `ob` by the face attribute "piece" into one object per name in `ids`."""
    out = {}
    for k, name in enumerate(ids):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        layer = bm.faces.layers.int.get("piece")
        gone = [f for f in bm.faces if f[layer] != k]
        bmesh.ops.delete(bm, geom=gone, context="FACES")
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        part = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(part)
        for m in ob.data.materials:
            me.materials.append(m)
        out[name] = part
    return out


def mark_piece(ob, k):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    layer = bm.faces.layers.int.get("piece") or bm.faces.layers.int.new("piece")
    for f in bm.faces:
        f[layer] = k
    bm.to_mesh(ob.data)
    bm.free()


def join_all(obs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = name
    return j


kits = [k for k in KITS if not args.only or k in args.only.split(",")]
shown = []
for kit in kits:
    pieces = KITS[kit]
    names = list(pieces)
    if args.fast:
        for name in names:
            ob = build_piece(pieces[name][0], hs.HIGH, name)
            print(f"{kit}/{name}: HIGH {tris(ob)} tris")
            shown.append(ob)
        continue
    his, los = [], []
    for k, name in enumerate(names):
        hi = build_piece(pieces[name][0], hs.HIGH, name + "_hi")
        lo = build_piece(pieces[name][0], hs.LOW, name + "_lo")
        mark_piece(lo, k)
        his.append(hi)
        los.append(lo)
        print(f"{kit}/{name}: HIGH {tris(hi)} / LOW {tris(lo)} tris", flush=True)
    hi = join_all(his, kit + "_high")
    lo = join_all(los, kit + "_low")
    if args.out:
        bakeutil.unwrap(lo, angle_deg=78.0, margin=0.006)
        tex = bakeutil.bake_textures(hi, lo, MATERIALS, args.tex, os.path.join(args.out, "textures"), f"gear_{kit}",
                                     cage=0.001, ray=0.0025, ao_distance=0.03, grime=0.5)
        bakeutil.apply_baked_material(lo, tex, f"gear_{kit}", emission_strength=1.0)
    bpy.data.objects.remove(hi)
    parts = separate(lo, names)
    bpy.data.objects.remove(lo)
    if args.out:
        for name, ob in parts.items():
            bone = pieces[name][1]
            shown.append(ob.copy())
            shown[-1].data = ob.data.copy()
            bpy.context.scene.collection.objects.link(shown[-1])
            to_bone(ob, bone)
            ob.name = f"{name}__{bone.replace('.', '_')}"
        bpy.ops.object.select_all(action="DESELECT")
        for ob in parts.values():
            ob.select_set(True)
        bpy.context.view_layer.objects.active = list(parts.values())[0]
        os.makedirs(args.out, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(args.out, f"gear_{kit}.gltf"), export_format="GLTF_SEPARATE",
                                  export_texture_dir="textures", use_selection=True, export_apply=True,
                                  export_tangents=True, export_animations=False, export_yup=True)
        for ob in parts.values():
            bpy.data.objects.remove(ob)
        print(f"{kit}: exported", flush=True)
    else:
        shown += list(parts.values())


if args.preview:
    scene = bpy.context.scene
    # The triad man (rest pose) for context, one copy per kit, side by side.
    body = None
    tri_path = os.path.join(ROOT, "assets", "characters", "triad", "triad.gltf")
    groups = {}
    for ob in shown:
        for kit in kits:
            if ob.name.split("__")[0].split(".")[0] in KITS[kit] or any(ob.name.startswith(n) for n in KITS[kit]):
                groups.setdefault(kit, []).append(ob)
                break
    if os.path.exists(tri_path):
        for i, kit in enumerate(kits):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=tri_path)
            new = [o for o in bpy.data.objects if o not in before]
            for o in new:
                if o.type == "MESH" and (o.name.startswith("part_") or o.name.startswith("vest")
                                         or o.name.startswith("Mesh")):
                    o.hide_render = True
                if o.parent is None:
                    o.location.x += 0.75 * i
                if o.animation_data:
                    o.animation_data.action = None
                if o.type == "ARMATURE":
                    o.data.pose_position = "REST"
            for ob in groups.get(kit, []):
                ob.location.x += 0.75 * i
    if ARM:
        ARM.hide_render = True
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = 1800, 900
    world = bpy.data.worlds.new("w")
    world.color = (0.33, 0.34, 0.36)
    scene.world = world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    width = 0.75 * len(kits)
    cam.location = (width / 2 - 0.375 + 0.75, -3.4, 1.25)
    cam.rotation_euler = (math.radians(88), 0, math.radians(14))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(width + 0.4, 2.0)
    scene.camera = cam
    for rot, e in (((50, -20, 30), 3.5), ((70, 30, -140), 1.5)):
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = e
        sun.rotation_euler = tuple(math.radians(a) for a in rot)
        scene.collection.objects.link(sun)
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("preview:", args.preview)
