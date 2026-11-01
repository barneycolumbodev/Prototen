#!/usr/bin/env python3
"""Splits the exported pistol_57.gltf into moving parts for the viewmodel.

Run after build.py. The game mesh is one baked object; this re-indexes its
triangles into three primitives that share the same vertex data and
textures (no re-bake): `body` (frame, barrel, suppressor), `slide` (slide
and sights, cycles on each shot) and `magazine` (baseplate, drops on reload).
ViewmodelRig finds the parts by node name.

Regions are in glTF weapon space (+X muzzle, +Y up, +Z right), from the
dimensions in build.py: slide from y = -0.010 up, x -0.100..0.098.

Usage: python3 raw_assets/weapons/pistol_57/split_parts.py assets/weapons/pistol_57/pistol_57.gltf
"""
import json, os, sys
import numpy as np

path = sys.argv[1]
g = json.load(open(path))
if len(g["nodes"]) > 1:
    sys.exit(f"{path}: already split ({len(g['nodes'])} nodes)")
bin_path = os.path.join(os.path.dirname(path), g["buffers"][0]["uri"])
data = bytearray(open(bin_path, "rb").read())
prim = g["meshes"][0]["primitives"][0]


def read(acc_i, dtype, comps):
    a = g["accessors"][acc_i]
    bv = g["bufferViews"][a["bufferView"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(bytes(data), dtype=dtype, count=a["count"] * comps, offset=off).reshape(-1, comps).copy()


pos = read(prim["attributes"]["POSITION"], np.float32, 3)
idx_acc = g["accessors"][prim["indices"]]
itype = {5123: np.uint16, 5125: np.uint32}[idx_acc["componentType"]]
tris = read(prim["indices"], itype, 1).reshape(-1, 3)
c = pos[tris].mean(axis=1)  # triangle centroids

slide = (c[:, 0] > -0.1015) & (c[:, 0] < 0.0995) & (c[:, 1] > -0.0098) & (np.abs(c[:, 2]) < 0.0142)
mag = (c[:, 1] < -0.131) & (c[:, 0] < -0.05)
body = ~(slide | mag)
print(f"triangles: body {body.sum()}, slide {slide.sum()}, magazine {mag.sum()}")

g["accessors"] = g["accessors"][:]
g["bufferViews"] = g["bufferViews"][:]
meshes, nodes = [], []
for name, mask in (("body", body), ("slide", slide), ("magazine", mag)):
    part = tris[mask].astype(itype).tobytes()
    while len(data) % 4:
        data.append(0)
    g["bufferViews"].append({"buffer": 0, "byteOffset": len(data), "byteLength": len(part), "target": 34963})
    data.extend(part)
    g["accessors"].append({"bufferView": len(g["bufferViews"]) - 1, "componentType": idx_acc["componentType"],
                           "count": int(mask.sum()) * 3, "type": "SCALAR"})
    p = dict(prim)
    p["indices"] = len(g["accessors"]) - 1
    meshes.append({"name": name, "primitives": [p]})
    nodes.append({"name": name, "mesh": len(meshes) - 1})

# The old whole-mesh index buffer stays in the file unused (harmless, ~40 KB).
g["meshes"] = meshes
g["nodes"] = [{"name": "pistol_57", "children": [1, 2, 3]}] + nodes
g["buffers"][0]["byteLength"] = len(data)
open(bin_path, "wb").write(data)
json.dump(g, open(path, "w"), indent=1)
print(f"wrote {path}: nodes {[n['name'] for n in g['nodes']]}")
