#!/usr/bin/env python3
"""Synthesizes the M14/P sounds (no third-party audio; see CREDITS.md).

Suppressed 7.62x51: the can takes most of the muzzle blast (a deep "thump"
and a pfft), but the bullet is still supersonic, so the crack stays loud.
The M14 action is heard clearly under a can: the op rod slams back and the
bolt rotates home a few milliseconds later ("ka-chunk"). Reload beats: the
magazine rocks out and in, and an empty reload slaps the op rod handle.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_m14_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(14)
SR = w.SR


def shot(v):
    sec = 0.6
    nwave = np.concatenate([np.linspace(1, -1, int(0.0012 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.035), 2000, 12000) * w.env(0.035, 0.0002, 0.005)
    thump = w.band(w.noise(0.22), 35, 380) * w.env(0.22, 0.002, 0.055)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(64 + 3 * v, 30, int(0.25 * SR))) / SR) * w.env(0.25, 0.002, 0.07)
    pfft = w.band(w.noise(0.16), 300, 2400) * w.env(0.16, 0.001, 0.04)
    can = w.partials(0.3, (410 + 8 * v, 1130, 2280), (0.06, 0.04, 0.025), (0.5, 0.3, 0.2), 0.02)
    oprod = w.click(0.06, (1700 + 60 * v, 2900, 4500), 0.012, bright=1700)
    bolt = w.click(0.09, (1150, 2100, 3400), 0.03, bright=1300)
    return w.at(sec, (0.0, nwave * 1.0), (0.0, crack * 1.3), (0.0, thump * 1.5), (0.0, sub * 1.0), (0.001, pfft * 0.9),
                (0.002, can * 0.25), (0.012, oprod * 0.6), (0.058, bolt * 0.75))


def tail():
    sec = 1.6
    base = w.band(w.noise(sec), 150, 2600) * w.env(sec, 0.012, 0.36)
    low = w.band(w.noise(sec), 35, 200) * w.env(sec, 0.02, 0.4)
    refl = w.at(sec, *[(d, w.band(w.noise(0.04), 1000, 6000) * w.env(0.04, 0.0005, 0.01) * g)
                       for d, g in ((0.013, 0.6), (0.027, 0.48), (0.044, 0.36), (0.068, 0.26), (0.1, 0.18))])
    return base * 0.5 + low * 0.5 + refl


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"m14_shot_{v}", shot(v))
    w.save("m14_tail_1", tail(), -4)
    latch = w.click(0.05, (2000, 3300, 4900), 0.012, bright=2000)
    rock = w.band(w.noise(0.12), 700, 4200) * np.sin(np.pi * w.t(0.12) / 0.12) ** 2
    w.save("m14_reload_start_1", w.at(0.2, (0, w.band(w.noise(0.15), 250, 2200) * np.hanning(int(0.15 * SR)) * 0.4)), -12)
    w.save("m14_mag_out_1", w.at(0.3, (0, latch), (0.02, rock * 0.5)), -4)
    seat = w.click(0.1, (950, 1850, 3200), 0.03, bright=1400)
    slap = w.band(w.noise(0.08), 60, 700) * w.env(0.08, 0.001, 0.02)
    w.save("m14_mag_in_1", w.at(0.35, (0, rock * 0.35), (0.08, seat * 1.1), (0.08, slap * 1.2)), -2)
    slam = w.click(0.12, (760, 1500, 2700), 0.045, bright=1000)
    w.save("m14_slide_release_1", w.at(0.3, (0, latch * 0.6), (0.03, slam * 1.1), (0.03, slap)), -2)
    w.save("m14_dry_fire_1", w.at(0.12, (0, w.click(0.06, (2600, 4100, 6200), 0.008))), -8)
    w.save("m14_reload_cancel_1", w.at(0.15, (0, w.band(w.noise(0.1), 300, 2000) * np.hanning(int(0.1 * SR)))), -14)
    print(f"wrote M14/P sounds to {out}")


if __name__ == "__main__":
    write_all()
