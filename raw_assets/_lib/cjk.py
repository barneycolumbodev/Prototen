"""Draw Chinese + Latin text into PIL images with the vendored Noto fonts.

The fonts come from Fontsource's npm packages (@fontsource/noto-serif-tc and
@fontsource/noto-sans-tc, SIL OFL 1.1), which split each weight into
unicode-range chunks (.woff2). raw_assets/env/fonts/ keeps only the chunks the
game's signs use (see vendor_fonts.py). This module finds the chunk holding
each character and draws text one glyph at a time.
"""
import glob
import os

from fontTools.ttLib import TTFont
from PIL import ImageFont

FONT_ROOT = os.path.join(os.path.dirname(__file__), "..", "env", "fonts")


class FontSet:
    def __init__(self, family):
        self.files = sorted(glob.glob(os.path.join(FONT_ROOT, family, "*.woff2")))
        if not self.files:
            raise RuntimeError("no fonts in " + os.path.join(FONT_ROOT, family))
        self.cmap = {}
        for f in self.files:
            for code in TTFont(f).getBestCmap():
                self.cmap.setdefault(code, f)
        self._cache = {}

    def has(self, ch):
        return ord(ch) in self.cmap

    def font(self, ch, size):
        f = self.cmap.get(ord(ch))
        if f is None:
            raise KeyError("glyph %r (U+%04X) not in vendored fonts" % (ch, ord(ch)))
        key = (f, size)
        if key not in self._cache:
            self._cache[key] = ImageFont.truetype(f, size)
        return self._cache[key]

    def advance(self, ch, size):
        if ch == " ":
            return size * 0.3
        return self.font(ch, size).getlength(ch)

    def width(self, text, size, tracking=0.0):
        return sum(self.advance(c, size) for c in text) + tracking * size * max(0, len(text) - 1)

    def draw(self, draw, xy, text, size, fill, vertical=False, tracking=0.0, anchor="lt", stroke=0, stroke_fill=None):
        """Draw `text` with its top-left (anchor 'lt') or centre ('mm') at xy."""
        x, y = xy
        if vertical:
            step = size * (1.0 + tracking)
            total = step * len(text) - size * tracking
            if anchor == "mm":
                y -= total / 2
            for c in text:
                if c != " ":
                    draw.text((x, y + size / 2), c, font=self.font(c, size), fill=fill, anchor="mm",
                              stroke_width=stroke, stroke_fill=stroke_fill)
                y += step
            return
        total = self.width(text, size, tracking)
        if anchor == "mm":
            x -= total / 2
        for c in text:
            if c != " ":
                draw.text((x, y), c, font=self.font(c, size), fill=fill, anchor="lm" if anchor == "mm" else "lt",
                          stroke_width=stroke, stroke_fill=stroke_fill)
            x += self.advance(c, size) + tracking * size
