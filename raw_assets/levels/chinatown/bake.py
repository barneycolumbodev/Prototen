"""Lightmap bake and glTF export for the Chinatown docks map.

Run after build.py:
    tools/blender.sh raw_assets/levels/chinatown/bake.py -- [--size 4096] [--samples 256] [--nobake]

1. Opens _build/chinatown.blend.
2. Lightmap UVs (UV2): every lit chunk is unwrapped together (multi-object
   smart project), so they share one atlas.
3. Bake scene: one material reads the per-corner attributes the generator
   wrote (Col = tint + texture-array layer, Data = emission + wet) and turns
   them into a diffuse colour (the layer's mean albedo × tint) and emission,
   so light bounces with the right colour and neon/lanterns/windows light the
   street. Light markers from layout.json become Blender lights; a cool moon
   and a dim, light-polluted sky fill in.
4. Cycles bakes DIFFUSE (direct + indirect, no colour) into a float image:
   the light arriving at each texel. Smoothed, dilated, then stored as
   sqrt(light / LM_MAX) in an 8-bit PNG (the shader squares it back).
5. Exports assets/levels/chinatown/chinatown.gltf (+ .bin), no materials:
   the Godot level assigns its shaders by mesh name.
6. split_cells.py re-cuts the chunks into 12 m cells (culling, LODs).
"""
import json
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "assets", "levels", "chinatown")
BLEND = os.path.join(HERE, "_build", "chinatown.blend")
MATS = os.path.join(ROOT, "assets", "env", "world", "materials.json")
LM_MAX = 8.0
# Layout light energies are relative; these bring them to Cycles units so the
# lit street lands in the lightmap's range (the shader's lm_gain trims it).
LIGHT_SCALE = 14.0
EMIT_SCALE = 3.0

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return type(default)(args[args.index(name) + 1]) if name in args else default


SIZE = arg("--size", 4096)
SAMPLES = arg("--samples", 256)
NOBAKE = "--nobake" in args


def log(*a):
    print("[bake %6.1fs]" % (time.time() - T0), *a, flush=True)


T0 = time.time()


def lit_objects():
    return [o for o in bpy.data.objects if o.type == "MESH" and (o.name.endswith("_main") or o.name.endswith("_detail"))]


def unwrap(objs):
    """One shared lightmap atlas: join every lit chunk (tagged by a temporary
    material), unwrap and pack once, then split back into the same chunks."""
    import math
    names = [o.name for o in objs]
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(bpy.data.materials.new("src:" + o.name))
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    big = bpy.context.view_layer.objects.active
    big.data.uv_layers.active = big.data.uv_layers["UV2"]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=3.0 / SIZE, rotate=True, scale=True, shape_method="CONCAVE")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    out = []
    for o in list(bpy.context.selected_objects):
        src = o.data.materials[0].name[4:] if o.data.materials else None
        o.name = src
        o.data.name = src
        o.data.materials.clear()
        o.data.uv_layers.active = o.data.uv_layers["UVMap"]
        out.append(o)
    assert sorted(x.name for x in out) == sorted(names), "chunk names changed in the unwrap"
    uv = np.concatenate([_uvs(o) for o in out])
    log("UV2 range", uv.min(0), uv.max(0))
    return out


def _uvs(o):
    a = np.zeros(len(o.data.loops) * 2, np.float32)
    o.data.uv_layers["UV2"].data.foreach_get("uv", a)
    return a.reshape(-1, 2)


def bake_attributes(objs, meta):
    """Per-corner linear base colour and emission for the bake material."""
    layers = sorted(meta["layers"].values(), key=lambda l: l["index"])
    mean = np.array([l["mean_linear"] for l in layers], np.float32)
    for o in objs:
        me = o.data
        n = len(me.loops)
        col = np.zeros(n * 4, np.float32)
        me.color_attributes["Col"].data.foreach_get("color", col)
        col = col.reshape(-1, 4)
        dat = np.zeros(n * 2, np.float32)
        me.uv_layers["Data"].data.foreach_get("uv", dat)
        dat = dat.reshape(-1, 2)
        idx = np.clip(np.rint(col[:, 3] * 255).astype(int), 0, len(mean) - 1)
        tint = np.clip(col[:, :3] * 2.0, 0, 4)
        base = np.clip(mean[idx] * tint, 0, 0.9)
        emit = base * dat[:, 0:1] * 1.6 * EMIT_SCALE  # emissive albedo is lighter than its mean
        # lantern paper, bulbs and lamp lenses let their own light out (no shadow)
        shell = np.isin(idx, [meta["layers"]["lantern"]["index"], meta["layers"]["emissive"]["index"]]).astype(np.float32)
        for name, arr in (("BakeCol", base), ("BakeEmit", emit), ("BakeShell", np.repeat(shell[:, None], 3, 1))):
            if name in me.color_attributes:
                me.color_attributes.remove(me.color_attributes[name])
            a = me.color_attributes.new(name, "FLOAT_COLOR", "CORNER")
            a.data.foreach_set("color", np.concatenate([arr, np.ones((n, 1), np.float32)], 1).ravel())
        me.color_attributes.active_color = me.color_attributes["Col"]


def bake_material(img):
    m = bpy.data.materials.new("bake")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "BakeCol"
    e = nt.nodes.new("ShaderNodeAttribute")
    e.attribute_name = "BakeEmit"
    nt.links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(e.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    # light shells (lantern paper, bulbs) are invisible to shadow rays
    sh = nt.nodes.new("ShaderNodeAttribute")
    sh.attribute_name = "BakeShell"
    lp = nt.nodes.new("ShaderNodeLightPath")
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(sh.outputs["Fac"], mul.inputs[0])
    nt.links.new(lp.outputs["Is Shadow Ray"], mul.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes["Material Output"]
    nt.links.new(mul.outputs[0], mix.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.nodes.active = t
    return m


def make_lights(layout):
    col = bpy.data.collections.new("bake_lights")
    bpy.context.scene.collection.children.link(col)
    n = 0
    for mk in layout["markers"]:
        if mk["kind"] != "light":
            continue
        kind = mk["type"]
        ld = bpy.data.lights.new("L", "AREA" if kind == "AREA" else ("SPOT" if kind == "SPOT" else "POINT"))
        ld.color = mk["color"]
        ld.energy = mk["energy"] * LIGHT_SCALE
        if kind == "AREA":
            ld.shape = "DISK"
            ld.size = max(0.1, mk["radius"])
        else:
            ld.shadow_soft_size = mk["radius"]
        if kind == "SPOT":
            import math
            ld.spot_size = math.radians(mk.get("spot", 90))
            ld.spot_blend = 0.6
        ob = bpy.data.objects.new("L", ld)
        ob.location = mk["p"]
        d = mk.get("dir")
        if d is not None:
            from mathutils import Vector
            ob.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
        # (area lights face down, -Z, by default)
        col.objects.link(ob)
        n += 1
    # moon: cool, low, from the south-east over the harbour
    sd = bpy.data.lights.new("moon", "SUN")
    sd.color = (0.55, 0.65, 1.0)
    sd.energy = 1.2
    sd.angle = 0.02
    so = bpy.data.objects.new("moon", sd)
    so.rotation_euler = (0.95, 0.0, 2.6)
    col.objects.link(so)
    # sky: deep blue overhead, orange light pollution at the horizon
    w = bpy.data.worlds.new("night")
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    grad = nt.nodes.new("ShaderNodeTexGradient")
    geo = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(geo.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (0.05, 0.035, 0.03, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.012, 0.018, 0.035, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 14.0
    bpy.context.scene.world = w
    return n


def denoise(img, cover):
    """Coverage-aware blur: smooths sampling noise without pulling in empty texels.
    (Blender's OIDN compositor node needs a GPU context in background mode.)"""
    from scipy import ndimage
    px = np.array(img.pixels[:], np.float32).reshape(SIZE, SIZE, 4)
    m = cover.astype(np.float32)
    sigma = 1.3 * SIZE / 4096
    w = ndimage.gaussian_filter(m, sigma)
    for c in range(3):
        px[..., c] = np.where(m > 0, ndimage.gaussian_filter(px[..., c] * m, sigma) / np.maximum(w, 1e-4), 0)
    log("smoothed")
    return px


def dilate(px, cover, n=8):
    """Grow lit texels into empty space so mip levels and filtering don't pull in black."""
    from scipy import ndimage
    rgb = px[..., :3].copy()
    m = cover.astype(np.float32)
    for _ in range(n):
        s = ndimage.uniform_filter(rgb * m[..., None], size=(3, 3, 1))
        w = ndimage.uniform_filter(m, size=3)
        grow = (m == 0) & (w > 0)
        rgb[grow] = s[grow] / w[grow][:, None]
        m = np.maximum(m, grow.astype(np.float32))
    return rgb


def export(path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("ct_"):
            o.select_set(True)
            o.data.materials.clear()
            for name in ("BakeCol", "BakeEmit", "BakeShell"):
                if name in o.data.color_attributes:
                    o.data.color_attributes.remove(o.data.color_attributes[name])
            o.data.color_attributes.active_color = o.data.color_attributes["Col"]
            tri = o.modifiers.new("tri", "TRIANGULATE")
            tri.min_vertices = 5  # n-gons only (tangents need tris/quads)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format="GLTF_SEPARATE", export_materials="NONE",
                              export_tangents=True, export_vertex_color="ACTIVE", export_all_vertex_colors=False,
                              export_yup=True, export_apply=True, export_texcoords=True, export_normals=True)


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    meta = json.load(open(MATS))
    layout = json.load(open(os.path.join(OUT_DIR, "layout.json")))
    objs = lit_objects()
    log("lit objects:", len(objs), "faces:", sum(len(o.data.polygons) for o in objs))
    objs = unwrap(objs)
    log("unwrapped")
    if not NOBAKE:
        allm = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("ct_")]
        bake_attributes(allm, meta)
        img = bpy.data.images.new("lightmap", SIZE, SIZE, float_buffer=True, alpha=True)
        img.generated_color = (0, 0, 0, 0)
        mat = bake_material(img)
        for o in allm:
            o.data.materials.clear()
            o.data.materials.append(mat)
            if o.name.endswith("_glass"):
                o.visible_shadow = False
        nl = make_lights(layout)
        log("lights:", nl)
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = SAMPLES
        sc.cycles.use_denoising = False
        sc.cycles.max_bounces = 4
        sc.cycles.diffuse_bounces = 3
        sc.cycles.glossy_bounces = 1
        sc.cycles.transmission_bounces = 1
        sc.cycles.use_light_tree = True
        sc.render.bake.margin = 6
        sc.render.bake.use_clear = True
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        log("baking %d² at %d spp ..." % (SIZE, SAMPLES))
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, uv_layer="UV2", margin=6, use_clear=True)
        log("baked")
        raw = np.array(img.pixels[:], np.float32).reshape(SIZE, SIZE, 4)
        cover = raw[..., 3] > 0.5
        img.filepath_raw = os.path.join(HERE, "_build", "lm_raw.exr")
        img.file_format = "OPEN_EXR"
        img.save()
        px = denoise(img, cover)
        rgb = dilate(px, cover | (px[..., :3].sum(-1) > 0))
        enc = np.sqrt(np.clip(rgb / LM_MAX, 0, 1))
        from PIL import Image
        out = (enc[::-1] * 255 + 0.5).astype(np.uint8)  # Blender pixels start bottom-left
        Image.fromarray(out, "RGB").save(os.path.join(OUT_DIR, "lightmap.png"), optimize=True)
        log("lightmap written, mean light %.3f, p99 %.3f" % (float(rgb.mean()), float(np.percentile(rgb, 99))))
    export(os.path.join(OUT_DIR, "chinatown.gltf"))
    log("exported")
    # Re-cut the 12 chunks into small cells so the phone can cull them.
    sys.path.insert(0, HERE)
    import split_cells
    split_cells.split(os.path.join(OUT_DIR, "chinatown.gltf"))
    log("split into cells")


if __name__ == "__main__":
    main()
