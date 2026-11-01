#!/usr/bin/env python3
"""Synthesizes the MG42 sounds (no third-party audio; see CREDITS.md).

Unsuppressed 7.62x51 at 1,200 rpm: each shot is short (the next one lands
50 ms later), so the "rip" comes from the shots running together. Layers per
shot: supersonic crack, muzzle blast with a low boom, bolt slam. The room tail
is played at most a few times a second by Sfx, so it is long and dark here.
Reload beats for the belt: cover open, box off, box on, belt laid, cover slam,
charging handle.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_mg42_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(42)
SR = w.SR


def shot(variant):
    sec = 0.34
    crack = w.band(w.noise(0.03), 2200, 12000) * w.env(0.03, 0.0002, 0.005)
    nwave = np.concatenate([np.linspace(1, -1, int(0.0011 * SR)), np.zeros(10)])
    # Muzzle blast: broadband bang, then the boom.
    blast = w.band(w.noise(0.12), 120, 5000) * w.env(0.12, 0.0004, 0.018)
    boom = w.band(w.noise(0.3), 30, 260) * w.env(0.3, 0.002, 0.07)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(70 + 4 * variant, 34, int(0.22 * SR))) / SR) * w.env(0.22, 0.001, 0.07)
    # Bolt slams home ~20 ms later (it's what makes it rattle at full rate).
    bolt = w.click(0.05, (1500 + 70 * variant, 2700, 4300), 0.012, bright=1600)
    ring = w.partials(0.2, (820 + 15 * variant, 1960, 3150), (0.05, 0.035, 0.02), (0.4, 0.25, 0.15), detune=0.02)
    return w.at(sec, (0.0, nwave * 1.0), (0.0, crack * 1.2), (0.0, blast * 1.6), (0.0, boom * 1.5),
                (0.0, sub * 1.0), (0.021, bolt * 0.5), (0.0, ring * 0.25))


def tail():
    sec = 1.8
    base = w.band(w.noise(sec), 120, 2400) * w.env(sec, 0.015, 0.42)
    low = w.band(w.noise(sec), 35, 180) * w.env(sec, 0.02, 0.5)
    refl = w.at(sec, *[(d, w.band(w.noise(0.04), 900, 5000) * w.env(0.04, 0.0005, 0.012) * g)
                       for d, g in ((0.014, 0.6), (0.029, 0.5), (0.047, 0.4), (0.071, 0.3), (0.105, 0.22), (0.15, 0.15))])
    return base * 0.55 + low * 0.6 + refl


def metal(sec, freqs, decay, bright=1200):
    return w.click(sec, freqs, decay, bright=bright)


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3, 4):
        w.save(f"mg42_shot_{v}", shot(v))
    w.save("mg42_tail_1", tail(), -3)
    # Reload beats (names match GunMechanism events through WeaponData.sound_prefix).
    latch = metal(0.06, (1900, 3300, 5100), 0.02)
    hinge = w.band(w.noise(0.18), 900, 3000) * np.sin(np.pi * w.t(0.18) / 0.18) ** 2 * (0.5 + 0.5 * np.sin(2 * np.pi * 31 * w.t(0.18)))
    w.save("mg42_reload_start_1", w.at(0.3, (0, latch), (0.05, hinge * 0.3)), -5)
    slide = w.band(w.noise(0.2), 600, 4000) * np.sin(np.pi * w.t(0.2) / 0.2) ** 2
    w.save("mg42_mag_out_1", w.at(0.35, (0, metal(0.05, (1300, 2500, 3900), 0.03)), (0.04, slide * 0.4)), -4)
    thunk = w.band(w.noise(0.12), 50, 600) * w.env(0.12, 0.001, 0.03)
    rattle = w.at(0.3, *[(0.02 + 0.028 * i, metal(0.03, (2400 + 90 * i, 3900, 6100), 0.008) * (0.6 - 0.05 * i))
                         for i in range(8)])
    w.save("mg42_mag_in_1", w.at(0.45, (0, thunk * 1.3), (0.0, metal(0.08, (900, 1700, 2900), 0.04)), (0.1, rattle * 0.6)), -2)
    slam = metal(0.12, (700, 1450, 2600), 0.05, bright=900)
    w.save("mg42_slide_release_1", w.at(0.4, (0, slam), (0, thunk * 1.1), (0.12, metal(0.06, (1800, 3000, 4700), 0.015) * 0.5)), -1)
    w.save("mg42_reload_cancel_1", w.at(0.2, (0, latch * 0.7)), -8)
    w.save("mg42_dry_fire_1", w.at(0.15, (0, metal(0.08, (1100, 2200, 3600), 0.02))), -6)
    # Weapon switch: sling rattle + grip slap.
    for name, base in (("draw_1", 1.0), ("holster_1", 0.8)):
        rustle = w.band(w.noise(0.25), 250, 2200) * np.sin(np.pi * w.t(0.25) / 0.25) ** 1.5
        w.save(name, w.at(0.35, (0, rustle * 0.5), (0.18, metal(0.05, (1600 * base, 2900, 4400), 0.015) * 0.6)), -9)
    print(f"wrote MG42 sounds to {out}")


if __name__ == "__main__":
    write_all()
