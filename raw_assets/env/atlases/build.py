"""Non-tiling atlas layers for the world texture array: shop signs, vertical
lightboxes and paper couplets, lit window interiors, and prop skins (fish,
roast duck, styrofoam, ice, newspaper, AC grille).

Imported by ../materials/build.py, which packs these after the tileable
materials. Each atlas returns the same channels as a material plus `rects`:
name -> [u0, v0, u1, v1] (0..1, v down), which the level generator uses to map
a quad onto one sign/window/prop. Text is real Traditional Chinese set in Noto
Serif TC / Noto Sans TC (raw_assets/env/fonts, SIL OFL).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_lib"))
from cjk import FontSet  # noqa: E402
from texsynth import Synth  # noqa: E402

SERIF = FontSet("serif")
SANS = FontSet("sans")
SS = 2  # supersampling for drawing

ATLASES = [{"name": "signs_a"}, {"name": "signs_b"}, {"name": "windows"}, {"name": "props"}]


class Canvas:
    """Draws at SS × size; base colour, height, roughness, metal, emission layers."""

    def __init__(self, S, seed):
        self.S = S
        self.k = S / 1024.0 * SS  # atlas units (1024 grid) -> pixels
        n = S * SS
        self.col = Image.new("RGB", (n, n), (20, 20, 20))
        self.h = Image.new("L", (n, n), 0)
        self.r = Image.new("L", (n, n), 200)
        self.m = Image.new("L", (n, n), 0)
        self.e = Image.new("L", (n, n), 0)
        self.dc = ImageDraw.Draw(self.col)
        self.dh = ImageDraw.Draw(self.h)
        self.dr = ImageDraw.Draw(self.r)
        self.dm = ImageDraw.Draw(self.m)
        self.de = ImageDraw.Draw(self.e)
        self.rects = {}
        self.syn = Synth(S, 1.0, seed)
        self.overlays = []  # (rect_px, kind) for numpy weathering after drawing

    def px(self, *v):
        return [x * self.k for x in v]

    def rect(self, name, x0, y0, x1, y1):
        self.rects[name] = [x0 / 1024, y0 / 1024, x1 / 1024, y1 / 1024]

    def box(self, x0, y0, x1, y1, col=None, h=None, r=None, m=None, e=None, radius=0):
        b = self.px(x0, y0, x1, y1)
        for d, v in ((self.dc, col), (self.dh, h), (self.dr, r), (self.dm, m), (self.de, e)):
            if v is not None:
                if radius:
                    d.rounded_rectangle(b, radius * self.k, fill=v)
                else:
                    d.rectangle(b, fill=v)

    def text(self, font, xy, s, size, col=None, h=None, r=None, m=None, e=None, vertical=False, tracking=0.0, anchor="mm", stroke=0):
        x, y = self.px(*xy)
        sz = int(size * self.k)
        for d, v in ((self.dc, col), (self.dh, h), (self.dr, r), (self.dm, m), (self.de, e)):
            if v is not None:
                font.draw(d, (x, y), s, sz, v, vertical=vertical, tracking=tracking, anchor=anchor,
                          stroke=int(stroke * self.k), stroke_fill=v)

    def weather(self, x0, y0, x1, y1, amount=1.0, streaks=True):
        self.overlays.append(((x0, y0, x1, y1), amount, streaks))

    def finish(self):
        S = self.S
        col = np.asarray(self.col.resize((S, S), Image.LANCZOS), np.float32) / 255
        h = np.asarray(self.h.filter(ImageFilter.GaussianBlur(0.8 * SS)).resize((S, S), Image.LANCZOS), np.float32) / 255
        r = np.asarray(self.r.resize((S, S), Image.LANCZOS), np.float32) / 255
        m = np.asarray(self.m.resize((S, S), Image.LANCZOS), np.float32) / 255
        e = np.asarray(self.e.resize((S, S), Image.LANCZOS), np.float32) / 255
        s = self.syn
        dirt = s.smooth(-0.5, 2.0, s.noise(beta=2.2, fmin=3))
        runs = np.clip(s.streak(s.smooth(1.2, 2.4, s.noise(beta=1.4, fmin=12)), 40 * S / 1024) * 2.5, 0, 1)
        grain = s.noise(beta=1.0, fmin=80) * 0.03
        mask = np.zeros((S, S), np.float32)
        smask = np.zeros((S, S), np.float32)
        for (x0, y0, x1, y1), amount, streaks in self.overlays:
            a, b, c, d = [int(v * S / 1024) for v in (x0, y0, x1, y1)]
            mask[b:d, a:c] = amount
            smask[b:d, a:c] = amount if streaks else 0
        col = col * (1 - (dirt * 0.22 * mask)[..., None]) * (1 - (runs * 0.35 * smask)[..., None]) * (1 + grain[..., None] * mask[..., None])
        r = np.clip(r + dirt * 0.2 * mask, 0, 1)
        hm = h * 0.004 + s.noise(beta=1.2, fmin=40) * 0.00015 * mask
        return dict(albedo=np.clip(col, 0, 1), normal=s.normal_from_height(hm, 1.0),
                    orm=np.stack([np.clip(s.cavity(hm) * 0.6 + 0.4, 0, 1), r, m], -1),
                    emit=e, rects=self.rects)


def C(r, g, b):
    return (int(r), int(g), int(b))


GOLD = C(214, 168, 72)
RED = C(150, 18, 16)
CREAM = C(236, 226, 200)


def board(cv, name, x0, y0, x1, y1, bg, fg, han, latin="", font=SERIF, frame=GOLD, raised=True, latin_col=None, han_size=None, lightbox=False):
    """A shop signboard: frame, Chinese name, small English line."""
    cv.rect(name, x0, y0, x1, y1)
    w, hgt = x1 - x0, y1 - y0
    cv.box(x0, y0, x1, y1, col=frame, h=60, r=110, m=160 if frame == GOLD else 0, e=0)
    b = 6 if hgt < 160 else 9
    cv.box(x0 + b, y0 + b, x1 - b, y1 - b, col=bg, h=40, r=170 if not lightbox else 90, m=0, e=235 if lightbox else 0)
    size = han_size or min(hgt * (0.62 if latin else 0.74), (w - 40) / max(len(han), 1) * 0.92)
    cy = y0 + hgt * (0.42 if latin else 0.5)
    cv.text(font, ((x0 + x1) / 2, cy), han, size, col=fg, h=120 if raised else 40, r=90 if fg == GOLD else 160,
            m=200 if fg == GOLD else 0, e=0 if not lightbox else 255, tracking=0.12)
    if latin:
        cv.text(SANS, ((x0 + x1) / 2, y0 + hgt * 0.83), latin, hgt * 0.14, col=latin_col or fg, h=90, tracking=0.25)
    cv.weather(x0, y0, x1, y1, 0.8 if not lightbox else 0.5)


def signs_a(S):
    cv = Canvas(S, 11)
    board(cv, "seaview", 0, 0, 1024, 168, C(120, 12, 10), GOLD, "海景酒家", "SEA VIEW RESTAURANT  ·  DIM SUM  ·  BBQ")
    board(cv, "fishmarket", 0, 168, 1024, 336, C(18, 70, 92), CREAM, "鮮魚市場", "FRESH FISH MARKET  ·  WHOLESALE & RETAIL", frame=C(200, 200, 196))
    board(cv, "herbal", 0, 336, 512, 464, C(16, 16, 14), GOLD, "參茸藥行", "GINSENG & HERBS")
    board(cv, "bakery", 512, 336, 1024, 464, CREAM, C(170, 20, 20), "金華餅家", "KAM WAH BAKERY", frame=C(170, 20, 20))
    board(cv, "noodle", 0, 464, 512, 592, C(22, 96, 52), CREAM, "雲吞麵 粥", "WONTON NOODLES", frame=C(230, 230, 220))
    board(cv, "grocery", 512, 464, 1024, 592, C(232, 196, 60), C(150, 20, 18), "永安雜貨", "WING ON GROCERY", frame=C(150, 20, 18))
    board(cv, "warehouse", 0, 592, 1024, 720, C(40, 70, 110), C(235, 235, 230), "三號碼頭 冷藏庫", "PIER 3  ·  COLD STORAGE  ·  NO PUBLIC ACCESS",
          frame=C(230, 230, 225), raised=False)
    board(cv, "laundry", 0, 720, 512, 848, C(232, 240, 245), C(30, 70, 150), "洗衣", "LAUNDRY & DRY CLEAN", font=SANS, frame=C(30, 70, 150), lightbox=True)
    board(cv, "travel", 512, 720, 1024, 848, C(250, 250, 245), C(200, 20, 30), "華人旅行社", "CHINA TRAVEL", font=SANS, frame=C(200, 20, 30), lightbox=True)
    board(cv, "gate", 0, 848, 512, 1024, C(22, 46, 110), GOLD, "天下為公", "")
    board(cv, "mahjong", 512, 848, 1024, 1024, C(18, 18, 20), C(60, 230, 120), "麻雀館", "MAHJONG CLUB  2/F", font=SANS, frame=C(60, 60, 64), lightbox=True)
    return cv.finish()


def vsign(cv, name, x0, y0, x1, y1, bg, fg, han, font=SANS, frame=C(240, 240, 235), lightbox=True):
    cv.rect(name, x0, y0, x1, y1)
    cv.box(x0, y0, x1, y1, col=frame, h=60, r=120, e=0)
    cv.box(x0 + 7, y0 + 7, x1 - 7, y1 - 7, col=bg, h=40, r=80, e=255 if lightbox else 0)
    n = len(han)
    size = min((x1 - x0) * 0.72, (y1 - y0 - 30) / n * 0.86)
    cv.text(font, ((x0 + x1) / 2, (y0 + y1) / 2), han, size, col=fg, h=110, e=255 if lightbox else 0, vertical=True, tracking=0.12)
    cv.weather(x0, y0, x1, y1, 0.5)


def signs_b(S):
    cv = Canvas(S, 12)
    vsign(cv, "v_hotel", 0, 0, 128, 512, C(250, 250, 245), C(20, 60, 150), "永利賓館")
    vsign(cv, "v_restaurant", 128, 0, 256, 512, C(170, 16, 14), C(255, 220, 120), "海景大酒樓")
    # pawnshop: the bat-and-coin sign hangs as its own prop; here its plaque
    vsign(cv, "v_pawn", 256, 0, 384, 512, C(240, 236, 220), C(120, 10, 10), "大押", font=SERIF, lightbox=False, frame=C(120, 10, 10))
    vsign(cv, "v_barber", 384, 0, 512, 512, C(245, 245, 245), C(20, 20, 120), "理髮")
    vsign(cv, "v_pharmacy", 512, 0, 640, 512, C(30, 120, 70), C(250, 250, 245), "源昌藥房")
    vsign(cv, "v_gold", 640, 0, 768, 512, C(150, 15, 15), C(255, 210, 90), "泰記金行")
    # red paper couplets
    for i, (nm, txt) in enumerate((("c1", "出入平安"), ("c2", "恭喜發財"), ("c3", "招財進寶"), ("c4", "如意吉祥"))):
        x = 768 + i * 64
        cv.rect(nm, x, 0, x + 64, 512)
        cv.box(x + 3, 0, x + 61, 512, col=C(190, 22, 18), h=20, r=210, e=0)
        cv.text(SERIF, (x + 32, 256), txt, 50, col=C(20, 14, 10) if i % 2 else GOLD, h=30, vertical=True, tracking=0.6)
        cv.weather(x, 0, x + 64, 512, 1.0)
    # daily specials menu board (chalk on black)
    cv.rect("menu", 0, 512, 512, 768)
    cv.box(0, 512, 512, 768, col=C(70, 46, 26), h=60, r=160)
    cv.box(12, 524, 500, 756, col=C(22, 26, 24), h=30, r=200)
    cv.text(SERIF, (256, 556), "每日特價", 44, col=C(240, 230, 120), h=40, tracking=0.2)
    items = (("叉燒飯", "$12"), ("牛腩麵", "$14"), ("雲吞麵", "$11"), ("燒鴨飯", "$13"))
    for i, (it, pr) in enumerate(items):
        y = 604 + i * 38
        cv.text(SERIF, (150, y), it, 32, col=C(235, 235, 230), h=30, tracking=0.1)
        cv.text(SANS, (380, y), pr, 30, col=C(250, 160, 150), h=30)
    cv.weather(0, 512, 512, 768, 0.7)
    # lion-dance poster and a parking notice
    cv.rect("poster", 512, 512, 768, 768)
    cv.box(512, 512, 768, 768, col=C(200, 30, 24), h=10, r=220)
    cv.dc.ellipse(cv.px(560, 560, 720, 720), fill=C(240, 190, 60))
    cv.dc.ellipse(cv.px(580, 580, 700, 700), fill=C(200, 30, 24))
    cv.text(SERIF, (640, 640), "福", 96, col=C(250, 210, 90), h=10)
    cv.text(SERIF, (640, 742), "恭喜發財", 30, col=C(250, 230, 160), h=10, tracking=0.2)
    cv.text(SANS, (640, 536), "LION DANCE  SAT 8PM", 18, col=C(255, 240, 200), h=10)
    cv.weather(512, 512, 768, 768, 1.0)
    cv.rect("notice", 768, 512, 1024, 768)
    cv.box(768, 512, 1024, 768, col=C(238, 238, 232), h=10, r=220)
    cv.box(780, 524, 1012, 590, col=C(190, 20, 20), h=10)
    cv.text(SERIF, (896, 557), "請勿泊車", 40, col=C(255, 255, 255), h=10, tracking=0.2)
    cv.text(SANS, (896, 630), "NO PARKING", 34, col=C(30, 30, 30), h=10)
    cv.text(SANS, (896, 690), "LOADING DOCK 24 HRS", 18, col=C(60, 60, 60), h=10)
    cv.weather(768, 512, 1024, 768, 1.0)
    # small plates
    def plate(name, x0, y0, x1, y1, bg, fg, han, latin, emit=False):
        cv.rect(name, x0, y0, x1, y1)
        cv.box(x0, y0, x1, y1, col=C(230, 230, 228), h=40, r=120, m=100)
        cv.box(x0 + 4, y0 + 4, x1 - 4, y1 - 4, col=bg, h=30, r=120, e=220 if emit else 0)
        hh = y1 - y0
        if latin:
            cv.text(SERIF, ((x0 + x1) / 2, y0 + hh * 0.38), han, hh * 0.46, col=fg, h=60, e=255 if emit else 0, tracking=0.15)
            cv.text(SANS, ((x0 + x1) / 2, y0 + hh * 0.79), latin, hh * 0.22, col=fg, h=60, e=255 if emit else 0, tracking=0.2)
        else:
            cv.text(SERIF, ((x0 + x1) / 2, (y0 + y1) / 2), han, hh * 0.62, col=fg, h=60, e=255 if emit else 0, tracking=0.15)
        cv.weather(x0, y0, x1, y1, 0.6)
    plate("street", 0, 768, 256, 832, C(25, 60, 140), C(250, 250, 250), "港灣街", "HARBOUR STREET")
    plate("exit", 256, 768, 384, 832, C(20, 150, 70), C(250, 255, 250), "出口", "EXIT", emit=True)
    plate("danger", 384, 768, 512, 832, C(240, 200, 30), C(20, 20, 20), "危險", "DANGER")
    plate("nosmoke", 512, 768, 768, 832, C(245, 245, 245), C(190, 20, 20), "禁止吸煙", "NO SMOKING")
    plate("open", 768, 768, 1024, 832, C(30, 10, 12), C(255, 60, 70), "營業中", "OPEN", emit=True)
    plate("slippery", 0, 832, 256, 896, C(240, 200, 30), C(20, 20, 20), "小心地滑", "WET FLOOR")
    plate("welcome", 256, 832, 512, 896, C(150, 15, 15), GOLD, "歡迎光臨", "WELCOME")
    plate("pier3", 512, 832, 768, 896, C(20, 30, 40), C(240, 240, 235), "三號碼頭", "PIER 3")
    plate("hotel_lb", 768, 832, 1024, 896, C(250, 250, 245), C(20, 60, 150), "永利賓館", "HOTEL  2/F", emit=True)
    # fish price cards
    prices = (("$38/斤", "石斑"), ("$22/斤", "鮮蝦"), ("$16/斤", "鯖魚"), ("$45/斤", "游水"), ("$28/斤", "生猛"), ("$19/斤", "鮮魚"),
              ("$60/斤", "大蟹"), ("$12/斤", "特價"))
    for i, (p, tname) in enumerate(prices):
        x0 = (i % 8) * 128
        y0 = 896
        cv.rect("tag%d" % i, x0, y0, x0 + 128, y0 + 128)
        cv.box(x0 + 4, y0 + 4, x0 + 124, y0 + 124, col=C(245, 242, 230), h=10, r=200)
        cv.text(SERIF, (x0 + 64, y0 + 42), tname, 34, col=C(30, 30, 30), h=10, tracking=0.1)
        cv.text(SANS, (x0 + 64, y0 + 92), p, 28, col=C(200, 20, 20), h=10)
        cv.weather(x0, y0, x0 + 128, y0 + 128, 0.8, streaks=False)
    return cv.finish()


def windows(S):
    """Eight lit interiors (top row: warm; bottom: mixed) seen through glass, 256×512 each."""
    cv = Canvas(S, 13)
    rng = np.random.default_rng(5)
    looks = [
        ("warm_curtain", C(255, 196, 120)), ("warm_blind", C(255, 210, 150)), ("fluoro", C(210, 240, 225)),
        ("tv", C(110, 150, 255)), ("red_lamp", C(255, 90, 60)), ("warm_plants", C(255, 180, 110)),
        ("kitchen", C(235, 245, 230)), ("dark", C(30, 30, 40)),
    ]
    for i, (name, light) in enumerate(looks):
        x0, y0 = (i % 4) * 256, (i // 4) * 512
        x1, y1 = x0 + 256, y0 + 512
        cv.rect("win_" + name, x0, y0, x1, y1)
        lit = name != "dark"
        # back wall: vertical gradient, hotspot near the lamp
        img = cv.col
        wall = np.zeros((512 * SS, 256 * SS, 3), np.float32)
        yy, xx = np.mgrid[0:512 * SS, 0:256 * SS] / SS
        lx, ly = rng.uniform(60, 196), rng.uniform(80, 200)
        d = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2)
        glow = np.exp(-d / 140.0)
        base = np.array(light, np.float32) / 255
        wall[:] = base * (0.25 + 0.75 * glow[..., None]) * (0.55 if lit else 0.15)
        wall[yy > 360] *= 0.55  # floor/furniture zone darker
        patch = Image.fromarray((np.clip(wall, 0, 1) * 255).astype(np.uint8))
        bx, by = int(x0 * cv.k), int(y0 * cv.k)
        img.paste(patch.resize((int(256 * cv.k), int(512 * cv.k))), (bx, by))
        cv.box(x0, y0, x1, y1, e=200 if lit else 10, r=30, h=0)
        dk = C(*(np.array(light) * 0.12).astype(int))
        # furniture silhouettes
        if name in ("warm_curtain", "red_lamp", "kitchen"):
            cv.box(x0 + 20, y0 + 300, x0 + 110, y0 + 512, col=dk, e=40)  # cabinet
            cv.box(x0 + 150, y0 + 180, x0 + 236, y0 + 320, col=dk, e=40)  # shelf
            for k in range(3):
                cv.box(x0 + 156, y0 + 196 + k * 40, x0 + 230, y0 + 200 + k * 40, col=C(*light), e=120)
        if name == "tv":
            cv.box(x0 + 60, y0 + 250, x0 + 200, y0 + 340, col=C(160, 200, 255), e=255)
            cv.box(x0 + 40, y0 + 380, x0 + 216, y0 + 512, col=C(15, 15, 25), e=20)  # sofa back
        if name == "warm_plants" or name == "fluoro":
            for k in range(5):
                px = x0 + 30 + k * 45
                cv.dc.ellipse(cv.px(px - 22, y0 + 390, px + 22, y0 + 450), fill=C(20, 30, 15))
                cv.box(px - 14, y0 + 440, px + 14, y0 + 480, col=C(60, 30, 20), e=0)
            cv.box(x0, y0 + 478, x1, y0 + 490, col=C(40, 40, 40), e=0)
        if name == "fluoro" or name == "kitchen":
            cv.box(x0 + 30, y0 + 40, x0 + 226, y0 + 52, col=C(250, 255, 250), e=255)
        if name == "red_lamp":
            cv.dc.ellipse(cv.px(x0 + 90, y0 + 90, x0 + 166, y0 + 170), fill=C(255, 70, 40))
        # curtains / blinds
        if name in ("warm_curtain", "red_lamp", "warm_plants", "dark"):
            cc = C(150, 40, 30) if name != "warm_plants" else C(200, 190, 150)
            for side in (0, 1):
                cx0 = x0 if side == 0 else x1 - 70
                for k in range(7):
                    shade = 0.6 + 0.4 * np.sin(k * 1.7)
                    cv.box(cx0 + k * 10, y0, cx0 + k * 10 + 10, y1, col=C(*(np.array(cc) * shade)), e=60 if lit else 0)
        if name == "warm_blind":
            for k in range(0, 300, 14):
                cv.box(x0, y0 + k, x1, y0 + k + 9, col=C(230, 200, 150), e=150)
        # security grille (very Hong Kong): bars over the bottom half
        if name in ("kitchen", "fluoro", "dark", "warm_blind"):
            for k in range(6):
                bx_ = x0 + 20 + k * 43
                cv.box(bx_, y0 + 230, bx_ + 6, y1, col=C(25, 25, 25), e=0, m=200)
            cv.box(x0, y0 + 230, x1, y0 + 238, col=C(25, 25, 25), e=0, m=200)
        # window frame mullion
        cv.box(x0, y0 + 220, x1, y0 + 230, col=C(60, 60, 58), e=0, h=80)
        cv.box(x0, y0, x0 + 8, y1, col=C(60, 60, 58), e=0, h=80)
        cv.box(x1 - 8, y0, x1, y1, col=C(60, 60, 58), e=0, h=80)
    # seen through old glass: soften everything a little
    cv.col = cv.col.filter(ImageFilter.GaussianBlur(1.2 * SS))
    cv.e = cv.e.filter(ImageFilter.GaussianBlur(1.2 * SS))
    return cv.finish()


def props(S):
    cv = Canvas(S, 14)
    syn = cv.syn
    # ---- fish skins: u along the body (head at left), v back (top) to belly
    species = [
        ("fish_mackerel", (40, 70, 90), (225, 230, 230), "bars"),
        ("fish_snapper", (190, 50, 50), (240, 190, 180), "plain"),
        ("fish_grouper", (80, 70, 50), (170, 150, 120), "spots"),
        ("fish_pomfret", (150, 155, 160), (230, 232, 235), "plain"),
    ]
    W, H = 512 * SS, 128 * SS
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H
    rng = np.random.default_rng(3)
    for i, (name, back, belly, pat) in enumerate(species):
        y0 = i * 128
        cv.rect(name, 0, y0, 512, y0 + 128)
        b, w = np.array(back, np.float32) / 255, np.array(belly, np.float32) / 255
        t = np.clip((v - 0.25) / 0.45, 0, 1)
        c = b * (1 - t[..., None]) + w * t[..., None]
        if pat == "bars":
            bars = (np.sin(u * 60 + np.sin(v * 9 + u * 7) * 2.2) > 0.3) & (v < 0.45)
            c[bars] *= 0.35
        if pat == "spots":
            for _ in range(160):
                sx, sy, sr = rng.uniform(0.1, 0.95) * W, rng.uniform(0.1, 0.9) * H, rng.uniform(2, 5) * SS
                m = (xx - sx) ** 2 + (yy - sy) ** 2 < sr ** 2
                c[m] *= 0.55
        scales = (np.sin(u * 420 + v * 100) * np.sin(u * 420 - v * 100)) * 0.06
        c *= (1 + scales[..., None])
        # head: darker gill line, eye
        gill = np.exp(-((u - 0.2) ** 2) / 0.0004) * 0.4
        c *= (1 - gill[..., None])
        ex, ey = 0.08 * W, 0.4 * H
        de = np.sqrt((xx - ex) ** 2 + (yy - ey) ** 2) / SS
        c[de < 11] = (0.85, 0.8, 0.6)
        c[de < 8] = (0.02, 0.02, 0.02)
        c[(de < 3)] = (0.9, 0.9, 0.9)
        tail = np.clip((u - 0.86) / 0.14, 0, 1)
        c *= (1 - tail[..., None] * 0.3)
        img = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
        cv.col.paste(img, (0, int(y0 * cv.k)))
        cv.box(0, y0, 512, y0 + 128, r=60, m=40)
    # ---- roast duck / char siu glaze
    def glaze(name, x0, y0, x1, y1, a, b2):
        cv.rect(name, x0, y0, x1, y1)
        w, h = int((x1 - x0) * cv.k), int((y1 - y0) * cv.k)
        n = np.asarray(Image.fromarray(((syn.noise01(beta=2.2, fmin=3)) * 255).astype(np.uint8)).resize((w, h)), np.float32) / 255
        ca, cb = np.array(a, np.float32) / 255, np.array(b2, np.float32) / 255
        c = ca * (1 - n[..., None]) + cb * n[..., None]
        cv.col.paste(Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)), (int(x0 * cv.k), int(y0 * cv.k)))
        cv.box(x0, y0, x1, y1, r=50, h=30)
    glaze("duck", 512, 0, 768, 256, (90, 30, 10), (190, 90, 30))
    glaze("charsiu", 768, 0, 1024, 128, (120, 15, 15), (200, 50, 30))
    glaze("ice", 768, 128, 1024, 256, (150, 175, 190), (235, 245, 250))
    cv.box(768, 128, 1024, 256, r=20, h=60)
    # ---- styrofoam box side with printed label
    cv.rect("styro", 512, 256, 768, 512)
    cv.box(512, 256, 768, 512, col=C(232, 232, 226), h=60, r=230)
    cv.box(560, 330, 720, 440, col=C(210, 210, 205), h=40)
    cv.text(SERIF, (640, 370), "海鮮", 44, col=C(30, 80, 160), h=40, tracking=0.2)
    cv.text(SANS, (640, 420), "SEAFOOD  FRAGILE", 14, col=C(30, 80, 160), h=40)
    cv.weather(512, 256, 768, 512, 0.6, streaks=False)
    # ---- newspaper
    cv.rect("newspaper", 768, 256, 1024, 512)
    cv.box(768, 256, 1024, 512, col=C(205, 200, 185), h=0, r=240)
    cv.text(SERIF, (896, 290), "華人日報", 40, col=C(20, 20, 20), h=0, tracking=0.2)
    filler = "港灣碼頭新舊華人老字號大酒樓宵夜冰室奶茶咖啡涼水永安利源昌盛泰記東南西北坊會館公所書報社"
    for col_i in range(9):
        x = 1004 - col_i * 25
        s_ = "".join(filler[(col_i * 7 + k * 3) % len(filler)] for k in range(8))
        cv.text(SERIF, (x, 330), s_, 20, col=C(40, 40, 40), h=0, vertical=True, anchor="lt", tracking=0.05)
    cv.weather(768, 256, 1024, 512, 0.8)
    # ---- AC unit front: fan grille
    cv.rect("ac_front", 0, 512, 256, 768)
    cv.box(0, 512, 256, 768, col=C(205, 205, 198), h=120, r=150)
    cv.dc.ellipse(cv.px(70, 556, 230, 716), fill=C(30, 30, 30))
    cv.dh.ellipse(cv.px(70, 556, 230, 716), fill=0)
    for k in range(9):
        r_ = 10 + k * 9
        cv.dc.ellipse(cv.px(150 - r_, 636 - r_, 150 + r_, 636 + r_), outline=C(170, 170, 168), width=int(2 * cv.k))
        cv.dh.ellipse(cv.px(150 - r_, 636 - r_, 150 + r_, 636 + r_), outline=180, width=int(2 * cv.k))
    for k in range(14):
        cv.box(14, 540 + k * 15, 56, 546 + k * 15, col=C(40, 40, 40), h=0)
    cv.weather(0, 512, 256, 768, 1.0)
    # ---- wooden crate stencil
    cv.rect("crate", 256, 512, 512, 768)
    cv.box(256, 512, 512, 768, col=C(150, 110, 70), h=60, r=220)
    for k in range(4):
        cv.box(256, 512 + k * 64, 512, 516 + k * 64, col=C(60, 40, 25), h=0)
    cv.text(SERIF, (384, 610), "生猛海鮮", 40, col=C(40, 25, 15), h=60, tracking=0.1)
    cv.text(SANS, (384, 680), "LIVE SEAFOOD  HK-SF", 16, col=C(40, 25, 15), h=60)
    cv.weather(256, 512, 512, 768, 1.0)
    # ---- mahjong tile faces, fruit-crate label, lucky red envelope colour pad
    cv.rect("red_pad", 512, 512, 640, 640)
    cv.box(512, 512, 640, 640, col=C(190, 20, 18), h=20, r=120)
    cv.rect("gold_pad", 640, 512, 768, 640)
    cv.box(640, 512, 768, 640, col=GOLD, h=20, r=80, m=220)
    cv.rect("black_pad", 512, 640, 640, 768)
    cv.box(512, 640, 640, 768, col=C(14, 14, 14), h=20, r=120)
    cv.rect("white_pad", 640, 640, 768, 768)
    cv.box(640, 640, 768, 768, col=C(230, 230, 225), h=20, r=140)
    # ---- graffiti tags for shutters (no text, just shapes) and a torn poster wall
    cv.rect("posters", 768, 512, 1024, 768)
    rngp = np.random.default_rng(9)
    for k in range(9):
        px0, py0 = 768 + rngp.uniform(-20, 200), 512 + rngp.uniform(-20, 200)
        colp = C(*rngp.integers(60, 240, 3))
        cv.box(px0, py0, px0 + 90, py0 + 120, col=colp, h=10, r=220)
        cv.text(SERIF, (px0 + 45, py0 + 40), "".join(rngp.choice(list("華人老字號大酒樓宵夜冰室奶茶")) for _ in range(3)), 22,
                col=C(20, 20, 20), h=10)
    cv.weather(768, 512, 1024, 768, 1.0)
    # ---- bottom strip: fluorescent tube, neon backing board, lantern tassel
    cv.rect("tube", 0, 768, 1024, 800)
    cv.box(0, 768, 1024, 800, col=C(240, 250, 245), e=255, r=60)
    cv.rect("rope", 0, 800, 1024, 832)
    for k in range(64):
        cv.box(k * 16, 800, k * 16 + 10, 832, col=C(150, 130, 90), h=100, r=230)
        cv.box(k * 16 + 10, 800, k * 16 + 16, 832, col=C(90, 75, 50), h=0, r=230)
    cv.rect("net", 0, 832, 512, 1024)
    cv.box(0, 832, 512, 1024, col=C(30, 60, 50), h=0, r=230)
    for k in range(0, 512, 16):
        cv.dc.line(cv.px(k, 832, k + 96, 1024), fill=C(90, 140, 110), width=int(2 * cv.k))
        cv.dc.line(cv.px(k + 96, 832, k, 1024), fill=C(90, 140, 110), width=int(2 * cv.k))
    cv.rect("tarp_print", 512, 832, 1024, 1024)
    cv.box(512, 832, 1024, 1024, col=C(30, 80, 150), h=20, r=200)
    for k in range(0, 512, 32):
        cv.box(512 + k, 832, 512 + k + 16, 1024, col=C(220, 220, 215), h=20)
    cv.weather(512, 832, 1024, 1024, 1.0)
    return cv.finish()


def build(name, S):
    return {"signs_a": signs_a, "signs_b": signs_b, "windows": windows, "props": props}[name](S)


if __name__ == "__main__":
    out = os.path.join(HERE, "_preview")
    os.makedirs(out, exist_ok=True)
    for a in ATLASES:
        r = build(a["name"], 1024)
        c = r["albedo"] * (0.35 + 0.65 * (r["normal"][..., 1:2])) + r["albedo"] * r["emit"][..., None] * 0.6
        Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, a["name"] + ".png"))
        print(a["name"], len(r["rects"]))
