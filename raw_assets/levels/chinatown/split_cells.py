#!/usr/bin/env python3
"""Split the map's chunks into small cells so the phone can cull them.

bake.py exports 12 big chunks (a 4 x 3 grid over the map, plus props whose
centre fell in a chunk but which stretch beyond it). Almost all of them
touch the view from anywhere, so the GPU drew ~300k triangles every frame
(owner's playtest 2026-11-05: 28-29 fps on the Moto G). This post-process
re-cuts every chunk by triangle into CELL-metre columns, so frustum culling,
occlusion culling and per-mesh LODs can actually drop geometry.

- Each triangle goes to the cell holding its centroid. Triangles longer than
  a cell (road strips, long roofs, the quay edge) go to a "_wide" mesh per
  chunk kind instead, so they don't stretch a small cell's bounds.
- Every vertex attribute is kept as-is (UV, the lightmap UV2, the data
  channel, tangents, colours), so the baked lightmap still lines up.
- Mesh names keep their kind suffix (_main, _glow, _glass): the level picks
  shaders by suffix.

Plain Python + numpy (no Blender). bake.py runs it after export; it can also
be run by hand:
    python3 raw_assets/levels/chinatown/split_cells.py [gltf] [--cell 12]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
WIDE = -(10 ** 6)
DEFAULT = os.path.join(ROOT, "assets", "levels", "chinatown", "chinatown.gltf")

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_accessor(g, buf, idx):
    a = g["accessors"][idx]
    bv = g["bufferViews"][a["bufferView"]]
    dt = np.dtype(COMP[a["componentType"]])
    n = NCOMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0)
    if stride and stride != dt.itemsize * n:
        raise ValueError("interleaved buffers not supported")
    arr = np.frombuffer(buf, dt, a["count"] * n, off).reshape(a["count"], n)
    return arr, a


class Writer:
    def __init__(self):
        self.chunks = []
        self.size = 0
        self.views = []
        self.accessors = []

    def add(self, arr, src_acc, target, minmax=False):
        data = np.ascontiguousarray(arr).tobytes()
        pad = (-self.size) % 4
        if pad:
            self.chunks.append(b"\0" * pad)
            self.size += pad
        self.views.append({"buffer": 0, "byteOffset": self.size, "byteLength": len(data), "target": target})
        self.chunks.append(data)
        self.size += len(data)
        acc = {"bufferView": len(self.views) - 1, "componentType": src_acc["componentType"],
               "count": int(arr.shape[0]), "type": src_acc["type"]}
        if src_acc.get("normalized"):
            acc["normalized"] = True
        if minmax:
            acc["min"] = [float(v) for v in arr.min(0)]
            acc["max"] = [float(v) for v in arr.max(0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1


def split(path, cell=12.0, out_path=None):
    out_path = out_path or path
    g = json.load(open(path))
    bin_path = os.path.join(os.path.dirname(path), g["buffers"][0]["uri"])
    buf = open(bin_path, "rb").read()
    w = Writer()
    meshes, nodes = [], []
    groups = {}  # (kind, key) -> list of per-chunk pieces
    ref_acc = {}
    for node in g["nodes"]:
        if "mesh" not in node:
            continue
        kind = node["name"].rsplit("_", 1)[1]  # main / glow / glass
        prim = g["meshes"][node["mesh"]]["primitives"][0]
        attrs = {k: read_accessor(g, buf, v) for k, v in prim["attributes"].items()}
        for an, (_arr, acc) in attrs.items():
            ref_acc[an] = acc
        idx, _ = read_accessor(g, buf, prim["indices"])
        tri = idx.reshape(-1, 3).astype(np.int64)
        p = attrs["POSITION"][0][tri]  # (T, 3, 3), glTF y-up
        cen = p.mean(1)
        ext = p.max(1) - p.min(1)
        wide = np.maximum(ext[:, 0], ext[:, 2]) > cell
        cx = np.floor(cen[:, 0] / cell).astype(np.int64)
        cz = np.floor(cen[:, 2] / cell).astype(np.int64)
        keys = np.where(wide, WIDE, cx * 1000 + cz)
        for key in np.unique(keys):
            sel = tri[keys == key]
            used, inv = np.unique(sel.reshape(-1), return_inverse=True)
            piece = {an: arr[used] for an, (arr, _a) in attrs.items()}
            groups.setdefault((kind, int(key)), []).append((piece, inv.reshape(-1)))
    stats = {}
    for (kind, key), pieces in sorted(groups.items()):
        names = list(pieces[0][0].keys())
        merged = {an: np.concatenate([pc[an] for pc, _ in pieces]) for an in names}
        offs = np.cumsum([0] + [len(pc["POSITION"]) for pc, _ in pieces[:-1]])
        index = np.concatenate([ix + o for (_, ix), o in zip(pieces, offs)])
        big = len(merged["POSITION"]) > 65535
        ia = {"componentType": 5125 if big else 5123, "type": "SCALAR"}
        new_attrs = {an: w.add(merged[an], ref_acc[an], 34962, minmax=(an == "POSITION")) for an in names}
        ii = w.add(index.astype(np.uint32 if big else np.uint16).reshape(-1, 1), ia, 34963)
        if key == WIDE:
            cname = "ct_wide_%s" % kind
        else:
            kx = int(np.floor((key + 500) / 1000))
            kz = key - kx * 1000
            cname = "ct_x%+03d_z%+03d_%s" % (kx, kz, kind)
        meshes.append({"name": cname, "primitives": [{"attributes": new_attrs, "indices": ii, "mode": 4}]})
        nodes.append({"name": cname, "mesh": len(meshes) - 1})
        stats[kind] = stats.get(kind, 0) + 1
    out_bin = os.path.splitext(os.path.basename(out_path))[0] + ".bin"
    blob = b"".join(w.chunks)
    gl = {
        "asset": g["asset"],
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": w.accessors,
        "bufferViews": w.views,
        "buffers": [{"uri": out_bin, "byteLength": len(blob)}],
    }
    with open(os.path.join(os.path.dirname(out_path), out_bin), "wb") as f:
        f.write(blob)
    with open(out_path, "w") as f:
        json.dump(gl, f, separators=(",", ":"))
    print("split_cells: %d meshes (%s), %.1f MB" % (len(meshes), stats, len(blob) / 1e6))
    return gl


if __name__ == "__main__":
    a = [x for x in sys.argv[1:]]
    cell = 12.0
    if "--cell" in a:
        i = a.index("--cell")
        cell = float(a[i + 1])
        del a[i:i + 2]
    out = None
    if "--out" in a:
        i = a.index("--out")
        out = a[i + 1]
        del a[i:i + 2]
    split(a[0] if a else DEFAULT, cell, out)
