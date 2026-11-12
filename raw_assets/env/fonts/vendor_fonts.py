"""Copy the Noto TC woff2 chunks that hold the characters the signs use.

Run once with the unpacked Fontsource packages (npm: @fontsource/noto-serif-tc
5.1.0 and @fontsource/noto-sans-tc 5.1.0, SIL OFL 1.1):
    python vendor_fonts.py <serif-package-dir> <sans-package-dir>
Add new characters to raw_assets/env/signtext.txt and run it again.
"""
import glob
import os
import shutil
import sys

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
text = open(os.path.join(HERE, "..", "signtext.txt"), encoding="utf-8").read()
chars = {ord(c) for c in text if not c.isspace()}
for pkg, family, weight in ((sys.argv[1], "serif", "900"), (sys.argv[2], "sans", "700")):
    out = os.path.join(HERE, family)
    os.makedirs(out, exist_ok=True)
    need = set(chars)
    for f in sorted(glob.glob(os.path.join(pkg, "files", "*-%s-normal.woff2" % weight))):
        cmap = set(TTFont(f).getBestCmap())
        if cmap & need:
            shutil.copy(f, out)
            need -= cmap
    shutil.copy(os.path.join(pkg, "LICENSE"), os.path.join(out, "OFL.txt"))
    print(family, "missing:", "".join(chr(c) for c in sorted(need)) or "none")
