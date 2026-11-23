#!/usr/bin/env python3
"""Contact sheet of a rendered shot: sheet.py <dir> <out.png> [every=6] [start=0] [end=]"""
import sys, os
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]
every = int(sys.argv[3]) if len(sys.argv) > 3 else 6
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
end = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
files = sorted(f for f in os.listdir(d) if f.endswith('.png'))
pick = [f for i, f in enumerate(files) if start <= i <= end and (i - start) % every == 0]
cols = 6; tw = 320
first = Image.open(os.path.join(d, pick[0])); th = int(tw * first.height / first.width)
rows = (len(pick) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * th), (0, 0, 0))
dr = ImageDraw.Draw(sheet)
for k, f in enumerate(pick):
    im = Image.open(os.path.join(d, f)).convert('RGB').resize((tw, th))
    x, y = (k % cols) * tw, (k // cols) * th
    sheet.paste(im, (x, y))
    idx = files.index(f)
    dr.rectangle([x, y, x + 46, y + 14], fill=(0, 0, 0)); dr.text((x + 2, y + 1), str(idx), fill=(255, 255, 0))
sheet.save(out)
print(len(pick), 'frames ->', out)
