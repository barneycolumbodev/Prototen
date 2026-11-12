"""Lit preview of every cached material (raking light shows the normal maps)."""
import glob, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
size = int(sys.argv[1]) if len(sys.argv) > 1 else 512
names = sys.argv[2].split(",") if len(sys.argv) > 2 else None
files = sorted(glob.glob(os.path.join(HERE, "_cache", "*_%d.npz" % size)), key=os.path.getmtime)
tiles = []
L = np.array([-0.55, 0.45, 0.7]); L /= np.linalg.norm(L)
for f in files:
    name = os.path.basename(f).rsplit("_", 1)[0]
    if names and name not in names:
        continue
    d = np.load(f)
    a = d["albedo"] ** 2.2
    n = d["normal"] * 2 - 1
    ao = d["orm"][..., 0:1]
    rough = d["orm"][..., 1:2]
    ndl = np.clip((n * L).sum(-1, keepdims=True), 0, 1)
    H = L + np.array([0, 0, 1.0]); H /= np.linalg.norm(H)
    spec = np.clip((n * H).sum(-1, keepdims=True), 0, 1) ** (2 / np.maximum(rough, 0.05) ** 4) * (1 - rough) * 0.6
    c = a * ao * (0.15 + 1.1 * ndl) + spec * 0.4 + a * d["emit"][..., None] * 3
    c = np.clip(c, 0, 1) ** (1 / 2.2)
    img = Image.fromarray((c * 255).astype(np.uint8)).resize((384, 384), Image.LANCZOS)
    ImageDraw.Draw(img).text((6, 6), name, fill=(255, 255, 0))
    tiles.append(img)
cols = 4
sheet = Image.new("RGB", (384 * cols, 384 * ((len(tiles) + cols - 1) // cols)))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * 384, (i // cols) * 384))
sheet.save(os.path.join(HERE, "_cache", "lit.png"))
