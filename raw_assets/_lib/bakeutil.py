"""Shared high->low baking helpers for asset generator scripts (CLAUDE.md §7).

Usage from a generator script (run through tools/blender.sh):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
    import bakeutil
    bakeutil.unwrap(low, boost={material: 2.0})
    tex = bakeutil.bake_textures(high, low, materials, 2048, tex_dir, "fp_arms")
    bakeutil.apply_baked_material(low, tex, "fp_arms", emission_strength=2.0)
    bakeutil.export_gltf(low, path)

Channels: base colour (with AO cavity grime), ORM (AO/roughness/metal),
tangent normal, emission. Bakes use Cycles on the CPU with selected-to-active.
"""
import os

import bpy
import numpy as np


def unwrap(low, boost=None, angle_deg=60.0, margin=0.003):
    """Smart-UV-project `low`, scale islands of materials in `boost` (name -> factor), pack."""
    import math
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    if boost:
        names = [m.name if m else "" for m in low.data.materials]
        uv = low.data.uv_layers.active.data
        for poly in low.data.polygons:
            name = names[poly.material_index] if poly.material_index < len(names) else ""
            factor = boost.get(name)
            if factor:
                for li in poly.loop_indices:
                    uv[li].uv = uv[li].uv * factor
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def _new_image(name, size, non_color):
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def _set_target(materials, image):
    for mat in materials:
        nt = mat.node_tree
        node = nt.nodes.get("bake_target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "bake_target"
        node.image = image
        nt.nodes.active = node


def _route(materials, channel):
    for mat in materials:
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.name = "bake_emit"
        if channel == "Emission":
            strength = bsdf.inputs["Emission Strength"].default_value
            emit.inputs["Color"].default_value = bsdf.inputs["Emission Color"].default_value if strength > 0 else (0, 0, 0, 1)
        else:
            src = bsdf.inputs[channel]
            if src.is_linked:
                nt.links.new(src.links[0].from_socket, emit.inputs["Color"])
            else:
                v = src.default_value
                emit.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1)
        nt.links.new(emit.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])


def _restore(materials):
    for mat in materials:
        nt = mat.node_tree
        nt.links.new(nt.nodes["Principled BSDF"].outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
        emit = nt.nodes.get("bake_emit")
        if emit:
            nt.nodes.remove(emit)


def _pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


def bake_textures(high, low, materials, size, tex_dir, prefix, cage=0.0012, ray=0.004, ao_distance=0.02,
                  grime=0.45, log=print):
    """Bakes HIGH -> LOW. Both must use materials from `materials`. Returns {key: image}."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("bake_world")
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low

    def bake(kind, image, samples):
        _set_target(materials, image)
        scene.cycles.samples = samples
        bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=cage,
                            max_ray_distance=ray, margin=12, use_clear=True)

    imgs = {}
    for key, channel, non_color in (("base", "Base Color", False), ("rough", "Roughness", True),
                                    ("metal", "Metallic", True), ("emit", "Emission", False)):
        imgs[key] = _new_image(f"{prefix}_{key}", size, non_color)
        _route(materials, channel)
        bake("EMIT", imgs[key], 1)
        _restore(materials)
        log(f"{prefix}: baked {key}")
    imgs["ao"] = _new_image(f"{prefix}_ao", size, True)
    scene.world.light_settings.distance = ao_distance
    bake("AO", imgs["ao"], 48)
    log(f"{prefix}: baked ao")
    imgs["normal"] = _new_image(f"{prefix}_normal", size, True)
    bake("NORMAL", imgs["normal"], 8)
    log(f"{prefix}: baked normal")

    ao = _pixels(imgs["ao"])[:, 0]
    base = _pixels(imgs["base"])
    base[:, :3] *= ((1.0 - grime) + grime * ao)[:, None]
    out_base = _new_image(f"{prefix}_basecolor", size, False)
    out_base.pixels.foreach_set(base.ravel())
    orm = np.ones((size * size, 4), dtype=np.float32)
    orm[:, 0] = ao
    orm[:, 1] = _pixels(imgs["rough"])[:, 0]
    orm[:, 2] = _pixels(imgs["metal"])[:, 0]
    out_orm = _new_image(f"{prefix}_orm", size, True)
    out_orm.pixels.foreach_set(orm.ravel())

    os.makedirs(tex_dir, exist_ok=True)
    final = {"basecolor": out_base, "orm": out_orm, "normal": imgs["normal"], "emission": imgs["emit"]}
    for key, img in final.items():
        img.filepath_raw = os.path.join(tex_dir, f"{prefix}_{key}.png")
        img.file_format = "PNG"
        img.save()
        img.filepath = img.filepath_raw
    return final


def _gltf_output_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return g


def apply_baked_material(low, tex, name, emission_strength=1.0):
    """Replaces LOW's materials with one material using the baked textures."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]

    def img(i):
        n = N.new("ShaderNodeTexImage")
        n.image = i
        return n

    L.new(img(tex["basecolor"]).outputs["Color"], bsdf.inputs["Base Color"])
    sep = N.new("ShaderNodeSeparateColor")
    L.new(img(tex["orm"]).outputs["Color"], sep.inputs["Color"])
    L.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    L.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    occl = N.new("ShaderNodeGroup")
    occl.node_tree = _gltf_output_group()
    L.new(sep.outputs["Red"], occl.inputs["Occlusion"])
    nmap = N.new("ShaderNodeNormalMap")
    L.new(img(tex["normal"]).outputs["Color"], nmap.inputs["Color"])
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    L.new(img(tex["emission"]).outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.use_backface_culling = True
    low.data.materials.clear()
    low.data.materials.append(mat)
    for poly in low.data.polygons:
        poly.material_index = 0
    return mat


def export_gltf(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="textures",
                              use_selection=True, export_apply=True, export_tangents=True,
                              export_image_format="AUTO")


def tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)
