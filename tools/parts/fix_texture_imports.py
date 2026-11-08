#!/usr/bin/env python3
"""After the first Godot import of a passive part's glTF: VRAM-compress its textures, with mipmaps, and mark
normal maps (blender-assets skill: headless imports default to lossless). Usage: fix_texture_imports.py [dirs...]"""
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dirs = sys.argv[1:] or glob.glob(os.path.join(ROOT, "assets", "augments", "passives", "*", "textures"))
for d in dirs:
    for f in glob.glob(os.path.join(d, "*.png.import")):
        s = open(f).read()
        s = re.sub(r"compress/mode=\d+", "compress/mode=2", s)
        s = re.sub(r"mipmaps/generate=\w+", "mipmaps/generate=true", s)
        if "_normal.png" in f:
            s = re.sub(r"compress/normal_map=\d+", "compress/normal_map=1", s)
        open(f, "w").write(s)
        print("fixed", os.path.relpath(f, ROOT))
