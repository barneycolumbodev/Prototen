"""Shophouse / tenement facades for the Chinatown docks map.

A building is built in local space: the front wall's outer face is the plane
y = 0, facing -Y; the building extends to +Y (depth). `frame(pos, yaw)` maps
it into the world (yaw 0 = front faces south, 180 = north). Walls are real
boxes around each window, so windows sit in recesses with reveals, sills and
lintels; behind each one is a card from the windows atlas (lit rooms, blinds,
curtains, security grilles, TV glow) that glows a little.
"""
import math

import numpy as np

import props as P
from envkit import rot_z
from props import RNG, frame, pick, rnd

WALL_T = 0.3

LIT = ["win_warm_curtain", "win_warm_blind", "win_fluoro", "win_tv", "win_red_lamp", "win_warm_plants", "win_kitchen"]


class Building:
    def __init__(self, k, x0, x1, y_front, depth, floors, facing=-1, ground_h=4.2, floor_h=3.1,
                 wall="plaster", tint=(0.55, 0.5, 0.42), bay=3.0, roof_props=True, parapet=1.0):
        self.k = k
        self.w_ = x1 - x0
        self.depth = depth
        self.floors = floors
        self.gh = ground_h
        self.fh = floor_h
        self.H = ground_h + (floors - 1) * floor_h
        self.wall = wall
        self.tint = tint
        self.bay = bay
        self.facing = facing
        self.yaw = 0.0 if facing < 0 else 180.0
        cx = (x0 + x1) / 2
        self.R, self.w = frame((cx, y_front, 0.0), self.yaw)
        self.parapet = parapet
        self.roof_props = roof_props

    # local box: x0..x1, y0..y1 (y>0 = inside), z0..z1
    def lbox(self, x0, x1, y0, y1, z0, z1, mat=None, tint=None, col=None, chamfer=0.0, faces="all", emit=0.0):
        c = self.w(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        self.k.box(c, (x1 - x0, y1 - y0, z1 - z0), mat or self.wall, tint if tint is not None else (self.tint if mat is None else None),
                   yaw=self.yaw, col=col, chamfer=chamfer, faces=faces, emit=emit)

    def lquad(self, x0, x1, y, z0, z1, mat, rect=None, tint=None, emit=0.0, back=False):
        a, b = self.w((x0, y, z0)), self.w((x1, y, z0))
        c, d = self.w((x1, y, z1)), self.w((x0, y, z1))
        if back:
            self.k.quad(b, a, d, c, mat, tint, emit, rect=rect)
        else:
            self.k.quad(a, b, c, d, mat, tint, emit, rect=rect)

    # ------------------------------------------------------------------ walls with windows
    def window_wall(self, z0, z1, y_face, ext_sign=-1, sill=0.9, wh=1.55, ww=1.3, lit_chance=0.55, extras=True, x_lo=None, x_hi=None):
        """One storey of wall between z0..z1 with a window per bay. ext_sign -1 = outside is -y (front)."""
        hw = self.w_ / 2
        x_lo = -hw if x_lo is None else x_lo
        x_hi = hw if x_hi is None else x_hi
        span = x_hi - x_lo
        nb = max(1, int(span / self.bay))
        bw = span / nb
        y0, y1 = (y_face, y_face + WALL_T) if ext_sign < 0 else (y_face - WALL_T, y_face)
        zs, ze = z0 + sill, z0 + sill + wh
        self.lbox(x_lo, x_hi, y0, y1, z0, zs)
        self.lbox(x_lo, x_hi, y0, y1, ze, z1)
        xs = [x_lo + (i + 0.5) * bw for i in range(nb)]
        prev = x_lo
        for xc in xs:
            self.lbox(prev, xc - ww / 2, y0, y1, zs, ze)
            prev = xc + ww / 2
        self.lbox(prev, x_hi, y0, y1, zs, ze)
        out = y_face + ext_sign * 0.0
        for xc in xs:
            lit = RNG.random() < lit_chance
            rect = pick(LIT) if lit else "win_dark"
            ycard = y_face - ext_sign * 0.14
            self.lquad(xc - ww / 2, xc + ww / 2, ycard, zs, ze, "windows", rect=rect, emit=(rnd(0.8, 1.6) if lit else 0.15), back=ext_sign > 0)
            # sill
            if ext_sign < 0:
                self.lbox(xc - ww / 2 - 0.08, xc + ww / 2 + 0.08, out - 0.1, out + 0.06, zs - 0.06, zs, "stone", (0.5, 0.49, 0.47))
            else:
                self.lbox(xc - ww / 2 - 0.08, xc + ww / 2 + 0.08, out - 0.06, out + 0.1, zs - 0.06, zs, "stone", (0.5, 0.49, 0.47))
            if lit:
                P.light(self.k, self.w((xc, out + ext_sign * 0.6, zs + wh * 0.6)), (1.0, 0.75, 0.5), rnd(6, 14), radius=0.6, rng=4.0)
            if not extras:
                continue
            r = RNG.random()
            outer = out + ext_sign * 0.0
            if r < 0.22:
                # HK window cage
                wf = ext_sign * (1 if self.yaw == 0.0 else -1)
                a = self.w((xc - ww / 2 - 0.1, outer, 0))
                b = self.w((xc + ww / 2 + 0.1, outer, 0))
                xa, xb = sorted((a[0], b[0]))
                P.window_cage(self.k, xa, xb, a[1], zs - 0.05, ze + 0.15, facing=wf)
            elif r < 0.5:
                P.ac_unit(self.k, self.w((xc + rnd(-0.2, 0.2), outer, zs - 0.45)), self.yaw + (0 if ext_sign < 0 else 180))
            elif r < 0.62:
                # laundry pole sticking out with clothes
                p0 = self.w((xc - 0.5, outer + ext_sign * 0.05, ze + 0.1))
                p1 = self.w((xc - 0.5, outer + ext_sign * 1.4, ze + 0.25))
                self.k.cyl(p0, p1, 0.015, "galv", sides=4)
                p2 = self.w((xc + 0.5, outer + ext_sign * 0.05, ze + 0.1))
                p3 = self.w((xc + 0.5, outer + ext_sign * 1.4, ze + 0.25))
                self.k.cyl(p2, p3, 0.015, "galv", sides=4)
                P.laundry(self.k, self.w((xc - 0.5, outer + ext_sign * 0.9, ze + 0.2)), self.w((xc + 0.5, outer + ext_sign * 0.9, ze + 0.2)), sag=0.03)

    def band(self, z, y_face, ext_sign=-1, h=0.18, proj=0.08, mat="stone", tint=(0.42, 0.41, 0.4)):
        hw = self.w_ / 2
        if ext_sign < 0:
            self.lbox(-hw, hw, y_face - proj, y_face + 0.01, z - h / 2, z + h / 2, mat, tint)
        else:
            self.lbox(-hw, hw, y_face - 0.01, y_face + proj, z - h / 2, z + h / 2, mat, tint)

    # ------------------------------------------------------------------ main parts
    def upper_front(self, lit_chance=0.55):
        for f in range(1, self.floors):
            z0 = self.gh + (f - 1) * self.fh
            self.window_wall(z0, z0 + self.fh, 0.0, -1, lit_chance=lit_chance)
            self.band(z0, 0.0)
        self.top()

    def top(self):
        hw = self.w_ / 2
        H = self.H
        # parapet and cornice
        self.lbox(-hw, hw, 0.0, WALL_T, H, H + self.parapet)
        self.lbox(-hw - 0.02, hw + 0.02, -0.18, WALL_T, H + self.parapet, H + self.parapet + 0.12, "stone", (0.4, 0.39, 0.38))
        self.lbox(-hw, hw, -0.12, 0.01, H - 0.15, H + 0.05, "stone", (0.4, 0.39, 0.38))
        # roof slab and back parapet (visible from upper windows elsewhere / silhouettes)
        self.lbox(-hw, hw, WALL_T, self.depth, H - 0.2, H, "roofing")
        self.lbox(-hw, hw, self.depth - WALL_T, self.depth, H, H + self.parapet * 0.8)
        if self.roof_props:
            if RNG.random() < 0.6:
                P.water_tank(self.k, self.w((rnd(-hw + 1.5, hw - 1.5), self.depth * 0.6, H)))
            if RNG.random() < 0.7:
                P.antenna(self.k, self.w((rnd(-hw + 1, hw - 1), self.depth * 0.4, H)), rnd(2.0, 4.0))

    def sides(self, left=True, right=True, windows=True):
        hw = self.w_ / 2
        for side, on in ((-1, left), (1, right)):
            if not on:
                continue
            x0, x1 = (-hw, -hw + WALL_T) if side < 0 else (hw - WALL_T, hw)
            self.lbox(x0, x1, WALL_T, self.depth, 0, self.H + self.parapet)
            if windows:
                for f in range(1, self.floors):
                    z = self.gh + (f - 1) * self.fh + 0.9
                    yc = self.depth * 0.5
                    xf = (x0 - 0.002) if side < 0 else (x1 + 0.002)
                    a = self.w((xf, yc - 0.45, z))
                    b = self.w((xf, yc + 0.45, z))
                    lit = RNG.random() < 0.4
                    p0, p1 = (b, a) if side < 0 else (a, b)
                    self.k.quad(p0, p1, p1 + (0, 0, 1.3), p0 + (0, 0, 1.3), "windows", rect=pick(LIT) if lit else "win_dark", emit=1.0 if lit else 0.1)
            # drainpipe down the corner
            dx = -hw + 0.12 if side < 0 else hw - 0.12
            p = self.w((dx, -0.1, 0))
            P.drainpipe(self.k, p[0], p[1], 0.15, self.H + 0.2)

    def back(self, y_back=None, floors_with_windows=True, door_x=None, fire_escape=False, lit_chance=0.4):
        """Back wall (outside is +y). Windows on the upper floors, a door on the ground."""
        yb = self.depth if y_back is None else y_back
        hw = self.w_ / 2
        # ground floor wall with optional back door
        if door_x is not None:
            self.lbox(-hw, door_x - 0.55, yb - WALL_T, yb, 0, self.gh)
            self.lbox(door_x + 0.55, hw, yb - WALL_T, yb, 0, self.gh)
            self.lbox(door_x - 0.55, door_x + 0.55, yb - WALL_T, yb, 2.2, self.gh)
            self.lbox(door_x - 0.6, door_x + 0.6, yb - 0.02, yb + 0.06, 2.2, 2.3, "paint_metal", (0.25, 0.25, 0.25))
            P.bulb(self.k, self.w((door_x, yb + 0.4, 2.9)), (1.0, 0.8, 0.55), 30.0, cord=0.05, shade=(0.2, 0.25, 0.22))
        else:
            self.lbox(-hw, hw, yb - WALL_T, yb, 0, self.gh)
        for f in range(1, self.floors):
            z0 = self.gh + (f - 1) * self.fh
            if floors_with_windows:
                self.window_wall(z0, z0 + self.fh, yb, +1, lit_chance=lit_chance)
            else:
                self.lbox(-hw, hw, yb - WALL_T, yb, z0, z0 + self.fh)
        P.drainpipe(self.k, *self.w((hw - 0.3, yb + 0.1, 0))[:2], 0.15, self.H)
        if fire_escape and self.floors > 2:
            a = self.w((-hw + 0.8, yb, 0))
            b = self.w((-hw + 0.8 + 4.0, yb, 0))
            xa, xb = sorted((a[0], b[0]))
            P.fire_escape(self.k, xa, xb, a[1], self.floors - 1, z_first=self.gh, floor_h=self.fh, facing=1 if self.facing < 0 else -1)

    # ------------------------------------------------------------------ ground floor shopfronts
    def shopfront(self, kind, sign=None, sign_mat="signs_a", awning=None, vsign=None, interior_lit=True, x_lo=None, x_hi=None, open_depth=2.6,
                  door=None):
        """kind: 'shutter' | 'glass' | 'open' | 'wall'. Pilasters, fascia sign, opening."""
        hw = self.w_ / 2
        x_lo = -hw if x_lo is None else x_lo
        x_hi = hw if x_hi is None else x_hi
        gh = self.gh
        pil = 0.45
        op_top = gh - 1.15
        # pilasters
        for xa, xb in ((x_lo, x_lo + pil), (x_hi - pil, x_hi)):
            self.lbox(xa, xb, -0.08, WALL_T, 0, gh, "mosaic", (0.42, 0.44, 0.4))
            self.lbox(xa - 0.02, xb + 0.02, -0.1, WALL_T, 0, 0.35, "stone", (0.35, 0.34, 0.33))
        # fascia
        ox0, ox1 = x_lo + pil, x_hi - pil
        self.lbox(ox0, ox1, 0.0, WALL_T, op_top, gh)
        if sign:
            sh = 0.85
            self.lbox(ox0 + 0.1, ox1 - 0.1, -0.16, 0.0, op_top + 0.12, op_top + 0.12 + sh, "paint_metal", (0.1, 0.1, 0.1))
            self.lquad(ox0 + 0.12, ox1 - 0.12, -0.165, op_top + 0.14, op_top + 0.1 + sh, sign_mat, rect=sign, emit=0.0)
            # two gooseneck lamps lighting the sign
            for xx in (ox0 + (ox1 - ox0) * 0.25, ox0 + (ox1 - ox0) * 0.75):
                p0 = self.w((xx, -0.16, op_top + sh + 0.25))
                p1 = self.w((xx, -0.55, op_top + sh + 0.3))
                self.k.tube([p0, p1], 0.015, "paint_metal", (0.1, 0.1, 0.1), sides=4)
                self.k.lathe(p1 - (0, 0, 0.06), [(0.09, 0.0), (0.05, 0.08), (0.0, 0.1)], "paint_metal", (0.1, 0.1, 0.1), sides=8, cap_bottom=False)
                P.light(self.k, self.w((xx, -0.5, op_top + sh + 0.12)), (1.0, 0.85, 0.65), 22.0, radius=0.05, kind="SPOT", spot=100,
                        direction=self.R @ np.array([0, 0.5, -1.0]), rng=4.0)
        y_open = 0.12
        if kind == "shutter":
            self.lquad(ox0, ox1, y_open, 0.0, op_top, "shutter", tint=pick([(0.42, 0.42, 0.42), (0.35, 0.42, 0.45), (0.45, 0.4, 0.35)]))
            self.lbox(ox0, ox1, -0.05, y_open, op_top - 0.3, op_top, "paint_metal", (0.25, 0.25, 0.25))
            for xx in (ox0, ox1 - 0.06):
                self.lbox(xx, xx + 0.06, y_open - 0.04, y_open + 0.02, 0, op_top - 0.3, "galv")
            if RNG.random() < 0.6:
                xm = (ox0 + ox1) / 2 + rnd(-0.5, 0.5)
                self.lquad(xm - 0.6, xm + 0.6, y_open - 0.01, 0.6, 2.0, "props", rect="posters")
            self.lbox(ox0, ox1, y_open, y_open + 0.2, 0, op_top, "concrete", col=None)
            self.k.collider(self.w(((ox0 + ox1) / 2, y_open + 0.1, op_top / 2)), (ox1 - ox0, 0.2, op_top), self.yaw, "thin_metal")
        elif kind == "glass":
            # glazed shopfront: low wall, frames, lit interior card behind the glass
            self.lbox(ox0, ox1, y_open, y_open + 0.25, 0, 0.5, "mosaic", (0.3, 0.32, 0.36))
            dx = door if door is not None else ox1 - 1.2
            self.lquad(ox0, ox1, y_open + 1.6, 0.0, op_top, "windows", rect=pick(["win_fluoro", "win_kitchen", "win_warm_blind"]),
                       emit=1.2 if interior_lit else 0.1)
            self.lquad(ox0, ox1, y_open + 0.05, 0.5, op_top, "glass")
            for xx in np.linspace(ox0, ox1, max(2, int((ox1 - ox0) / 1.5) + 1)):
                self.lbox(xx - 0.03, xx + 0.03, y_open, y_open + 0.08, 0.5, op_top, "galv")
            self.lbox(ox0, ox1, y_open, y_open + 0.08, 0.47, 0.53, "galv")
            self.k.collider(self.w(((ox0 + ox1) / 2, y_open + 0.1, op_top / 2)), (ox1 - ox0, 0.2, op_top), self.yaw, "glass")
            if interior_lit:
                P.light(self.k, self.w(((ox0 + ox1) / 2, -0.8, 1.8)), (0.9, 0.95, 1.0), 35.0, radius=1.0, kind="AREA", rng=5.0)
        elif kind == "open":
            # open-fronted shop with a shallow lit interior (shelves of goods)
            d = open_depth
            self.lbox(ox0, ox1, y_open, y_open + d, -0.02, 0.0, "terrazzo", None)
            self.lbox(ox0, ox1, y_open, y_open + d, op_top, op_top + 0.05, "plaster", (0.55, 0.55, 0.52))
            self.lbox(ox0 - 0.05, ox0, y_open, y_open + d, 0, op_top, "mosaic", (0.5, 0.48, 0.4))
            self.lbox(ox1, ox1 + 0.05, y_open, y_open + d, 0, op_top, "mosaic", (0.5, 0.48, 0.4))
            self.lbox(ox0, ox1, y_open + d, y_open + d + 0.05, 0, op_top, "mosaic", (0.5, 0.48, 0.4))
            n = max(1, int((ox1 - ox0) / 1.25))
            for i in range(n):
                xx = ox0 + (i + 0.5) * (ox1 - ox0) / n
                c = self.w((xx, y_open + d - 0.25, 0))
                P.shelf_unit(self.k, c, self.yaw, w_=(ox1 - ox0) / n - 0.1, h=min(2.2, op_top - 0.1))
            P.fluoro(self.k, self.w(((ox0 + ox1) / 2, y_open + d * 0.5, op_top)), self.yaw, length=min(1.8, ox1 - ox0 - 0.4), energy=60.0)
            self.k.collider(self.w(((ox0 + ox1) / 2, y_open + d + 0.4, op_top / 2)), (ox1 - ox0, 0.8, op_top), self.yaw, "concrete")
            for xx in (ox0 - 0.03, ox1 + 0.03):
                self.k.collider(self.w((xx, y_open + d / 2, op_top / 2)), (0.1, d, op_top), self.yaw, "concrete")
        elif kind == "wall":
            self.lbox(ox0, ox1, 0.0, WALL_T, 0, op_top)
            self.k.collider(self.w(((ox0 + ox1) / 2, WALL_T / 2, op_top / 2)), (ox1 - ox0, WALL_T, op_top), self.yaw, "concrete")
        if awning:
            a = self.w((ox0 + 0.05, 0, 0))
            b = self.w((ox1 - 0.05, 0, 0))
            xa, xb = sorted((a[0], b[0]))
            P.awning(self.k, xa, xb, a[1], op_top + 0.02, depth=1.3, drop=0.4, tint=awning, facing=self.facing)
        if vsign:
            # vertical lightbox blade, perpendicular to the facade, double-sided
            xx = x_hi - 0.25
            c = self.w((xx, -0.7, gh + 2.4))
            self.k.sign(c, 0.6, 2.4, self.yaw + 90, "signs_b", vsign, emit=2.2, depth=0.22, double=True, back_tint=(0.2, 0.2, 0.2))
            for zz in (gh + 1.3, gh + 3.5):
                self.k.cyl(self.w((xx, 0.0, zz)), self.w((xx, -0.45, zz)), 0.025, "galv", sides=5)
            P.light(self.k, self.w((xx, -1.2, gh + 2.4)), (1.0, 0.95, 0.9), 18.0, radius=0.5, rng=5.0)
        # wall-mounted overhead wires/pipes along the fascia for clutter
        p0 = self.w((x_lo, -0.05, gh + 0.25))
        p1 = self.w((x_hi, -0.05, gh + 0.25))
        self.k.cyl(p0, p1, 0.02, "plastic", (0.08, 0.08, 0.08), sides=4, caps=False)
