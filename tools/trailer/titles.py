#!/usr/bin/env python3
"""Text for the trailer (docs/trailer.md): renders each caption in
tools/trailer/edit.json as a transparent PNG sequence, and the end title
card as an opaque one. Rajdhani (SIL OFL, raw_assets/trailer/fonts/).

Usage: titles.py <edit.json> <out_dir> <width> <height>
"""
import json
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_BOLD = os.path.join(ROOT, "raw_assets/trailer/fonts/rajdhani-latin-700-normal.woff")
FONT_SEMI = os.path.join(ROOT, "raw_assets/trailer/fonts/rajdhani-latin-600-normal.woff")
ACCENT = (92, 219, 199)   # the game's augment cyan (MainMenu.C_ACCENT)
FPS = 60


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def tracked(draw, text, font, tracking):
    """Width of `text` with extra letter spacing (px)."""
    w = 0
    for ch in text:
        w += draw.textlength(ch, font=font) + tracking
    return w - tracking


def draw_tracked(img, text, font, cx, y, tracking, fill):
    d = ImageDraw.Draw(img)
    x = cx - tracked(d, text, font, tracking) / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tracking


def glow(img, radius, strength):
    blur = img.filter(ImageFilter.GaussianBlur(radius))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for _ in range(strength):
        out = Image.alpha_composite(out, blur)
    return Image.alpha_composite(out, img)


def caption(spec, w, h, out_dir):
    """A centred line low in frame: fades and opens its tracking."""
    dur = spec["t1"] - spec["t0"]
    n = int(round(dur * FPS))
    size = int(h * spec.get("size", 0.058))
    font = ImageFont.truetype(FONT_BOLD, size)
    y = int(h * spec.get("y", 0.78))
    os.makedirs(out_dir, exist_ok=True)
    for i in range(n):
        t = i / FPS
        a_in = ease(t / 0.35)
        a_out = 1.0 - ease((t - (dur - 0.3)) / 0.3)
        a = a_in * a_out
        track = size * (0.22 + 0.10 * ease(t / dur))
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_tracked(img, spec["text"], font, w / 2, y, track, (235, 238, 240, int(255 * a)))
        img = glow(img, size * 0.25, 1)
        img.save(os.path.join(out_dir, "c%05d.png" % i))
    return n


def label(spec, w, h, out_dir):
    """A hardware callout, lower left: a cyan tick, the name, a dim line under
    it; slides in a few pixels and fades."""
    dur = spec["t1"] - spec["t0"]
    n = int(round(dur * FPS))
    f1 = ImageFont.truetype(FONT_BOLD, int(h * 0.034))
    f2 = ImageFont.truetype(FONT_SEMI, int(h * 0.021))
    x0 = int(w * 0.055)
    y0 = int(h * 0.80)
    os.makedirs(out_dir, exist_ok=True)
    for i in range(n):
        t = i / FPS
        a = ease(t / 0.2) * (1.0 - ease((t - (dur - 0.25)) / 0.25))
        dx = int((1.0 - ease(t / 0.3)) * w * 0.012)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([x0 + dx, y0, x0 + dx + max(3, int(h * 0.005)), y0 + int(h * 0.062)], fill=ACCENT + (int(255 * a),))
        tx = x0 + dx + int(h * 0.018)
        x = tx
        for ch in spec["text"]:
            d.text((x, y0 - int(h * 0.006)), ch, font=f1, fill=(240, 242, 244, int(255 * a)))
            x += d.textlength(ch, font=f1) + f1.size * 0.12
        if spec.get("sub"):
            x = tx
            for ch in spec["sub"]:
                d.text((x, y0 + int(h * 0.036)), ch, font=f2, fill=ACCENT + (int(220 * a),))
                x += d.textlength(ch, font=f2) + f2.size * 0.2
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 0), (0, 0, w, h))
        sh = img.split()[3].filter(ImageFilter.GaussianBlur(h * 0.004))
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 255))
        dark.putalpha(sh.point(lambda v: int(v * 0.7)))
        out = Image.alpha_composite(dark, img)
        out.save(os.path.join(out_dir, "c%05d.png" % i))
    return n


def title_card(spec, w, h, out_dir):
    """The end card: black, the name slams in with a short chromatic split and
    a cyan rule that draws out under it, then the line under that."""
    dur = spec["duration"]
    n = int(round(dur * FPS))
    name = spec.get("name", "GRAFT")
    sub = spec.get("sub", "COMING SOON")
    tag = spec.get("tag", "")
    big = ImageFont.truetype(FONT_BOLD, int(h * 0.20))
    small = ImageFont.truetype(FONT_SEMI, int(h * 0.050))
    tiny = ImageFont.truetype(FONT_SEMI, int(h * 0.026))
    os.makedirs(out_dir, exist_ok=True)
    cy = int(h * 0.44)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
        # The name: in hard on the slam, settling from 108 % over 0.5 s.
        s = 1.0 + 0.08 * (1 - ease(t / 0.5))
        fb = ImageFont.truetype(FONT_BOLD, int(h * 0.30 * s))
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        track = h * 0.07 * s
        a_name = 1.0 - ease((t - (dur - 0.6)) / 0.6)
        draw_tracked(layer, name, fb, w / 2, cy - (fb.size * 0.62), track, (240, 242, 244, int(255 * a_name)))
        # Chromatic split for the first frames, then clean.
        split = int(max(0.0, 1.0 - t / 0.18) * h * 0.012)
        if split > 0:
            r, g, b, a = layer.split()
            lr = Image.merge("RGBA", (r, Image.new("L", r.size, 0), Image.new("L", r.size, 0), a))
            lb = Image.merge("RGBA", (Image.new("L", r.size, 0), g, b, a))
            shifted = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            shifted.paste(lr, (-split, 0), lr)
            shifted = Image.alpha_composite(shifted, Image.new("RGBA", (w, h), (0, 0, 0, 0)))
            tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            tmp.paste(lb, (split, 0), lb)
            layer = Image.alpha_composite(shifted, tmp)
        layer = glow(layer, h * 0.012, 1)
        img = Image.alpha_composite(img, layer)
        d = ImageDraw.Draw(img)
        # The rule.
        k = ease((t - 0.25) / 0.7) * a_name
        half = w * 0.22 * k
        ry = cy + int(h * 0.10)
        if half > 1:
            d.rectangle([w / 2 - half, ry, w / 2 + half, ry + max(2, int(h * 0.003))], fill=ACCENT + (int(255 * a_name),))
        # The line under it.
        a_sub = ease((t - 1.1) / 0.6) * a_name
        if a_sub > 0:
            sub_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw_tracked(sub_layer, sub, small, w / 2, ry + int(h * 0.04), small.size * 0.45, (220, 224, 228, int(255 * a_sub)))
            if tag:
                draw_tracked(sub_layer, tag, tiny, w / 2, ry + int(h * 0.11), tiny.size * 0.5, ACCENT + (int(200 * a_sub),))
            img = Image.alpha_composite(img, sub_layer)
        img.convert("RGB").save(os.path.join(out_dir, "t%05d.png" % i))
    return n


def main():
    edit = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    # Start clean: a shorter caption must not keep an old one's last frames.
    for root, _dirs, files in os.walk(out):
        for f in files:
            if f.endswith(".png"):
                os.remove(os.path.join(root, f))
    w, h = int(sys.argv[3]), int(sys.argv[4])
    for k, c in enumerate(edit.get("captions", [])):
        fn = label if c.get("style") == "label" else caption
        n = fn(c, w, h, os.path.join(out, "cap%d" % k))
        print("caption", k, c["text"], n, "frames")
    if "title" in edit:
        n = title_card(edit["title"], w, h, os.path.join(out, "title"))
        print("title", n, "frames")


if __name__ == "__main__":
    main()
