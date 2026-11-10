#!/usr/bin/env python3
"""Region masks for the colour customizer (docs/design.md §3.7).

The operative and the first-person arms are baked to one texture set each, so the game can't tell a plate
from the weave by material any more. This writes `<name>_regions.png` next to each set: one byte per texel,
the paint channel it belongs to (BodyColors.SUIT_CHANNELS index + 1; 0 = leave alone). The paint shader
(src/body/suit_paint.gdshader) reads it unfiltered and recolours each channel.

How a texel is classified:
- what it is, from the baked ORM and emission maps: each source material has its own roughness/metallic
  (operative: weave 0.60, plate 0.34, sole 0.88, seal 0.45, trim metal 0.95, visor rough 0.04; arms: glove
  0.34, plate 0.42 + metal 0.25, cuff 0.50, sleeve 0.88), lights are whatever glows;
- where it is, from the mesh: every triangle is drawn into UV space tagged with its mesh (suit or helmet) and
  the bone that moves it most (torso, arms, hands, legs, boots).

Rerun after the operative or the arms are rebuilt:
  python3 tools/colors/build_regions.py
It also writes each PNG's .import (lossless, no mipmaps, never VRAM-compressed: the bytes are ids).
"""
import base64
import json
import os
import struct

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SIZE = 1024
# BodyColors.SUIT_CHANNELS order (+1).
HELMET, VISOR, UNDERSUIT, TORSO, ARMS, HANDS, LEGS, BOOTS, TRIM, LIGHTS = range(1, 11)
BONE_REGION = [("hand", HANDS), ("finger", HANDS), ("upper_arm", ARMS), ("forearm", ARMS), ("thigh", LEGS), ("shin", LEGS),
               ("foot", BOOTS), ("toe", BOOTS)]

IMPORT = """[remap]

importer="texture"
type="CompressedTexture2D"
uid="{uid}"
path="res://.godot/imported/{file}-{hash}.ctex"
metadata={{
"vram_texture": false
}}

[deps]

source_file="res://{res}"
dest_files=["res://.godot/imported/{file}-{hash}.ctex"]

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=2
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=false
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


class Gltf:
    def __init__(self, path):
        self.g = json.load(open(path))
        self.dir = os.path.dirname(path)
        self.bufs = []
        for b in self.g["buffers"]:
            uri = b["uri"]
            if uri.startswith("data:"):
                self.bufs.append(base64.b64decode(uri.split(",", 1)[1]))
            else:
                self.bufs.append(open(os.path.join(self.dir, uri), "rb").read())

    def acc(self, i):
        a = self.g["accessors"][i]
        bv = self.g["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        dt = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", 0)
        item = np.dtype(dt).itemsize * n
        raw = self.bufs[bv["buffer"]]
        if stride and stride != item:
            out = np.empty((a["count"], n), dtype=dt)
            for k in range(a["count"]):
                out[k] = np.frombuffer(raw, dtype=dt, count=n, offset=off + k * stride)
            return out
        return np.frombuffer(raw, dtype=dt, count=a["count"] * n, offset=off).reshape(a["count"], n)


def raster(tag, uv, tris, values, size):
    """Draws triangles (uv 0..1, v down as in glTF) into `tag` with per-triangle `values`."""
    p = uv * size
    for t, val in zip(tris, values):
        a, b, c = p[t[0]], p[t[1]], p[t[2]]
        x0, x1 = int(np.floor(min(a[0], b[0], c[0]))) - 1, int(np.ceil(max(a[0], b[0], c[0]))) + 1
        y0, y1 = int(np.floor(min(a[1], b[1], c[1]))) - 1, int(np.ceil(max(a[1], b[1], c[1]))) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        inside = (w0 >= -0.02) & (w1 >= -0.02) & (w0 + w1 <= 1.02)
        sub = tag[y0:y1 + 1, x0:x1 + 1]
        sub[inside] = val


def dilate(tag, rounds=6):
    for _ in range(rounds):
        empty = tag == 0
        if not empty.any():
            break
        best = np.zeros_like(tag)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(tag, (dy, dx), axis=(0, 1))
            best = np.where((best == 0) & (sh != 0), sh, best)
        tag = np.where(empty, best, tag)
    return tag


def load(path, size):
    im = Image.open(path).convert("RGB").resize((size, size), Image.NEAREST)
    return np.asarray(im).astype(np.float32) / 255.0


def write(name, mask, tex_dir):
    out = os.path.join(tex_dir, name + "_regions.png")
    Image.fromarray(mask.astype(np.uint8), "L").save(out, optimize=True)
    res = os.path.relpath(out, ROOT).replace(os.sep, "/")
    imp = out + ".import"
    uid, hsh = None, None
    if os.path.exists(imp):
        for line in open(imp):
            if line.startswith("uid="):
                uid = line.split('"')[1]
            if line.startswith("path=") and ".ctex" in line:
                hsh = line.split("-")[-1].split(".ctex")[0]
    if uid is None:
        import hashlib
        import random
        rnd = random.Random(res)
        uid = "uid://" + "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(13))
        hsh = hashlib.md5(("res://" + res).encode()).hexdigest()
    open(imp, "w").write(IMPORT.format(uid=uid, file=os.path.basename(out), hash=hsh, res=res))
    counts = {int(k): int(v) for k, v in zip(*np.unique(mask, return_counts=True))}
    print(name, counts)


def operative():
    base = os.path.join(ROOT, "assets", "characters", "operative")
    tex = os.path.join(base, "textures")
    g = Gltf(os.path.join(base, "operative.gltf"))
    names = [n.get("name", "") for n in g.g["nodes"]]
    place = np.zeros((SIZE, SIZE), np.uint8)   # body region by bone; 200 = helmet mesh
    for node in g.g["nodes"]:
        if "mesh" not in node or node.get("name") not in ("operative", "operative_helmet"):
            continue
        prim = g.g["meshes"][node["mesh"]]["primitives"][0]
        uv = g.acc(prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
        idx = g.acc(prim["indices"]).reshape(-1, 3)
        if node["name"] == "operative_helmet":
            vals = np.full(len(idx), 200)
        else:
            joints = g.acc(prim["attributes"]["JOINTS_0"])
            weights = g.acc(prim["attributes"]["WEIGHTS_0"]).astype(np.float64)
            skin = g.g["skins"][node["skin"]]["joints"]
            top = joints[np.arange(len(joints)), weights.argmax(1)]
            vreg = np.full(len(joints), TORSO)
            for v, j in enumerate(top):
                bone = names[skin[j]]
                for key, reg in BONE_REGION:
                    if key in bone:
                        vreg[v] = reg
                        break
            # A triangle belongs to the region most of its corners are in.
            tri = vreg[idx]
            vals = np.where(tri[:, 1] == tri[:, 2], tri[:, 1], tri[:, 0])
        raster(place, uv, idx, vals, SIZE)
    place = dilate(place)
    orm = load(os.path.join(tex, "operative_orm.png"), SIZE)
    em = load(os.path.join(tex, "operative_emission.png"), SIZE)
    rough, metal = orm[..., 1], orm[..., 2]
    helmet = place == 200
    used = (rough > 0.02) | (metal > 0.02)
    mask = np.zeros((SIZE, SIZE), np.uint8)
    plate = used & (metal < 0.5) & (rough < 0.42)
    mask[plate] = np.where(helmet, HELMET, place)[plate]
    mask[used & (metal < 0.5) & (rough >= 0.42) & (rough < 0.75)] = UNDERSUIT
    sole = used & (metal < 0.5) & (rough >= 0.75)
    mask[sole] = BOOTS
    mask[used & (metal >= 0.5)] = TRIM
    mask[used & (metal >= 0.5) & (rough < 0.15)] = VISOR
    mask[em.max(-1) > 0.08] = LIGHTS
    # Plates the raster missed (no bone tag) fall back to torso.
    mask[(mask == 0) & plate] = TORSO
    mask[mask == 200] = HELMET
    write("operative", mask, tex)


def arms(name):
    base = os.path.join(ROOT, "assets", "characters", name)
    tex = os.path.join(base, "textures")
    orm = load(os.path.join(tex, name + "_orm.png"), SIZE)
    em = load(os.path.join(tex, name + "_emission.png"), SIZE)
    rough, metal = orm[..., 1], orm[..., 2]
    used = (rough > 0.02) | (metal > 0.02)
    mask = np.zeros((SIZE, SIZE), np.uint8)
    mask[used & (rough < 0.38) & (metal < 0.08)] = HANDS            # glove polymer
    mask[used & (metal >= 0.08)] = ARMS                              # glove plates
    mask[used & (rough >= 0.46) & (rough < 0.7) & (metal < 0.08)] = TRIM   # cuff
    mask[used & (rough >= 0.7)] = UNDERSUIT                          # sleeve fabric
    mask[used & (rough >= 0.38) & (rough < 0.46) & (metal < 0.08)] = HANDS
    mask[em.max(-1) > 0.08] = LIGHTS
    write(name, mask, tex)


if __name__ == "__main__":
    operative()
    for d in sorted(os.listdir(os.path.join(ROOT, "assets", "characters"))):
        if d.startswith("fp_arms"):
            arms(d)
