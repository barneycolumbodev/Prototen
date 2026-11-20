#!/usr/bin/env python3
"""Synthesizes the Steyr AUG sounds (no third-party audio; see CREDITS.md).

Unsuppressed 5.56x45 from a 508 mm barrel: a sharp, high muzzle blast (the
small, fast case burns hot: a bright "crack-bang" with less low end than the
7.62 mm M14), the bullet's N-wave on top, and a short, tight punch. The
bullpup's action sits at the shooter's cheek, so the short-stroke piston and
the bolt carrier's run back on its two guide rods are heard close and
metallic between rounds at 680 rpm, with a polymer-damped knock as the
carrier bottoms in the stock. The tail is long and slapping (a rifle in the
open), with a rolling low echo.

Reload beats: the catch behind the magazine is pressed and the clear
magazine drops out with a hollow plastic rattle (its rounds shift); the new
one goes in with a plastic-on-polymer clack; on an empty gun the folding
cocking handle on the left is pulled back and let go: the carrier slams
home on its rods.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_aug_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(77)
SR = w.SR


def shot(v):
    sec = 0.55
    nwave = np.concatenate([np.linspace(1, -1, int(0.0008 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.03), 2400, 14000) * w.env(0.03, 0.0001, 0.0042)
    blast = w.band(w.noise(0.16), 220, 5200) * w.env(0.16, 0.0006, 0.026)
    punch = w.band(w.noise(0.14), 45, 420) * w.env(0.14, 0.0015, 0.034)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(88 + 4 * v, 42, int(0.16 * SR))) / SR) * w.env(0.16, 0.0015, 0.04)
    ring = w.partials(0.2, (980 + 20 * v, 2350, 4100), (0.03, 0.02, 0.012), (0.5, 0.3, 0.2), 0.02)
    # Piston tap, carrier back on the rods (bright), bottoming in the stock (damped), bolt home.
    piston = w.click(0.03, (3100 + 90 * v, 4700, 7000), 0.006, bright=3200)
    back = w.click(0.05, (2100, 3500, 5600), 0.010, bright=2300)
    knock = w.band(w.noise(0.05), 180, 1300) * w.env(0.05, 0.001, 0.014)
    home = w.click(0.06, (1500, 2700, 4300), 0.016, bright=1600)
    return w.at(sec, (0.0, nwave * 1.0), (0.0, crack * 1.4), (0.0, blast * 1.25), (0.0, punch * 1.1),
                (0.0, sub * 0.75), (0.001, ring * 0.2), (0.004, piston * 0.45), (0.014, back * 0.55),
                (0.03, knock * 0.4), (0.056, home * 0.55))


def tail():
    sec = 1.5
    base = w.band(w.noise(sec), 200, 3600) * w.env(sec, 0.01, 0.30)
    low = w.band(w.noise(sec), 40, 240) * w.env(sec, 0.02, 0.42)
    refl = w.at(sec, *[(d, w.band(w.noise(0.035), 1100, 7000) * w.env(0.035, 0.0005, 0.009) * g)
                       for d, g in ((0.012, 0.6), (0.025, 0.5), (0.041, 0.38), (0.064, 0.28), (0.095, 0.2),
                                    (0.14, 0.13))])
    return base * 0.5 + low * 0.45 + refl


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3, 4):
        w.save(f"aug_shot_{v}", shot(v), -0.5)
    w.save("aug_tail_1", tail(), -5)
    catch = w.click(0.04, (1900, 3100, 4700), 0.010, bright=1900)
    # Clear polymer magazine: a hollow knock and the loose rounds shifting inside.
    hollow = w.band(w.noise(0.09), 350, 2600) * w.env(0.09, 0.001, 0.025)
    rattle = w.at(0.14, *[(d, w.click(0.03, (2600 + 300 * i, 4100, 6200), 0.006, bright=2600) * g)
                          for i, (d, g) in enumerate(((0.0, 0.5), (0.018, 0.35), (0.04, 0.42), (0.066, 0.25)))])
    w.save("aug_reload_start_1", w.at(0.2, (0, w.band(w.noise(0.15), 250, 2400) * np.hanning(int(0.15 * SR)) * 0.4)), -12)
    w.save("aug_mag_out_1", w.at(0.32, (0, catch), (0.02, hollow * 0.8), (0.03, rattle * 0.7)), -4)
    clack = w.click(0.08, (1300, 2400, 3900), 0.022, bright=1500)
    thud = w.band(w.noise(0.07), 90, 900) * w.env(0.07, 0.001, 0.018)
    w.save("aug_mag_in_1", w.at(0.34, (0, rattle * 0.3), (0.07, clack * 1.1), (0.07, thud * 1.0),
                                (0.075, hollow * 0.4)), -2)
    # Cocking handle pulled back (the carrier rides back on its rods), let go: the carrier slams home.
    pull = w.band(w.noise(0.12), 900, 5200) * np.sin(np.pi * w.t(0.12) / 0.12) ** 2
    slam = w.click(0.12, (880, 1700, 3000), 0.04, bright=1200)
    w.save("aug_slide_release_1", w.at(0.42, (0, catch * 0.5), (0.02, pull * 0.45), (0.19, slam * 1.15),
                                       (0.19, thud * 0.9)), -2)
    w.save("aug_dry_fire_1", w.at(0.12, (0, w.click(0.05, (2500, 3900, 6000), 0.008))), -8)
    w.save("aug_reload_cancel_1", w.at(0.15, (0, w.band(w.noise(0.1), 300, 2200) * np.hanning(int(0.1 * SR)))), -14)
    print(f"wrote AUG sounds to {out}")


if __name__ == "__main__":
    write_all()
