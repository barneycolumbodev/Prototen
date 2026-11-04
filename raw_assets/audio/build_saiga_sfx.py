#!/usr/bin/env python3
"""Synthesizes the Saiga-12K sounds (no third-party audio; see CREDITS.md).

12-gauge from a 430 mm barrel, unsuppressed: a heavy broadband bang with a
deep boom, a slight crack (buck and slugs leave at ~400-450 m/s, just over
the speed of sound), then the gas-driven carrier slamming back and forward
(the AK clatter). Dragon's Breath has a smaller bang and a roaring jet of
burning metal that crackles as it flies. Reload beats for an AK-pattern
magazine: paddle click, rock out, rock in, charging handle slammed home.
Also: 12-gauge hulls hitting the floor, the ember fire catching, and the
shell-type selector click.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_saiga_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(12)
SR = w.SR


def sweep(sec, f0, f1):
    return np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, int(sec * SR))) / SR)


def metal(sec, freqs, decay, bright=1200):
    return w.click(sec, freqs, decay, bright=bright)


def crackle(sec, rate, lo=1500, hi=9000, decay=0.25):
    """Random sparks popping: short clicks at `rate` per second, fading."""
    n = int(sec * SR)
    out = np.zeros(n)
    count = int(sec * rate)
    for i in range(count):
        p = int(w.rng.uniform(0, 1) ** 1.6 * (n - 400))
        g = w.rng.uniform(0.2, 1.0) * np.exp(-p / SR / decay)
        pop = w.band(w.noise(0.006), lo, hi) * w.env(0.006, 0.0001, 0.0012)
        out[p:p + pop.size] += pop * g
    return out


def shot(variant):
    sec = 0.7
    crack = w.band(w.noise(0.02), 2500, 12000) * w.env(0.02, 0.0002, 0.003)
    blast = w.band(w.noise(0.16), 90, 5500) * w.env(0.16, 0.0004, 0.028)
    boom = w.band(w.noise(0.45), 25, 220) * w.env(0.45, 0.002, 0.11)
    sub = sweep(0.32, 62 + 3 * variant, 28) * w.env(0.32, 0.001, 0.1)
    # Carrier back (~18 ms), then slammed forward with the next shell (~70 ms).
    back = metal(0.05, (1200 + 60 * variant, 2300, 3900), 0.012, bright=1300)
    home = metal(0.09, (820 + 40 * variant, 1650, 2900), 0.03, bright=900)
    ring = w.partials(0.35, (610 + 12 * variant, 1490, 2630), (0.08, 0.05, 0.03), (0.4, 0.25, 0.15), detune=0.02)
    return w.at(sec, (0.0, crack * 0.5), (0.0, blast * 1.8), (0.0, boom * 1.9), (0.0, sub * 1.3),
                (0.018, back * 0.45), (0.07, home * 0.55), (0.0, ring * 0.2))


def tail():
    sec = 2.2
    base = w.band(w.noise(sec), 110, 2200) * w.env(sec, 0.018, 0.5)
    low = w.band(w.noise(sec), 30, 160) * w.env(sec, 0.025, 0.62)
    refl = w.at(sec, *[(d, w.band(w.noise(0.05), 700, 4500) * w.env(0.05, 0.0005, 0.016) * g)
                       for d, g in ((0.016, 0.65), (0.033, 0.5), (0.052, 0.42), (0.08, 0.32), (0.12, 0.24), (0.17, 0.16))])
    return base * 0.6 + low * 0.7 + refl


def db_shot(variant):
    sec = 1.1
    blast = w.band(w.noise(0.12), 120, 4500) * w.env(0.12, 0.0005, 0.022)
    boom = w.band(w.noise(0.35), 30, 240) * w.env(0.35, 0.002, 0.08)
    # The jet: a roar that swells for ~80 ms and burns off over half a second.
    x = w.t(0.9)
    swell = np.clip(x / 0.08, 0, 1) * np.exp(-np.maximum(x - 0.08, 0) / 0.22)
    roar = w.band(w.noise(0.9), 180, 2600) * swell
    rumble = w.band(w.noise(0.9), 40, 260) * swell
    flutter = 0.75 + 0.25 * np.sin(2 * np.pi * (23 + 3 * variant) * x)
    home = metal(0.09, (840 + 30 * variant, 1700, 2950), 0.03, bright=900)
    return w.at(sec, (0.0, blast * 1.3), (0.0, boom * 1.3), (0.006, roar * flutter * 1.1), (0.006, rumble * 0.9),
                (0.02, crackle(0.9, 140, decay=0.35) * 0.9), (0.07, home * 0.5))


def db_tail():
    sec = 2.2
    return tail() * 0.8 + w.at(sec, (0.05, crackle(1.6, 60, decay=0.6) * 0.35))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"saiga_shot_{v}", shot(v))
    w.save("saiga_tail_1", tail(), -3)
    for v in (1, 2):
        w.save(f"saiga_db_shot_{v}", db_shot(v))
    w.save("saiga_db_tail_1", db_tail(), -4)

    # Reload beats (names match GunMechanism events through WeaponData.sound_prefix "saiga_").
    rustle = w.band(w.noise(0.22), 300, 2600) * np.sin(np.pi * w.t(0.22) / 0.22) ** 1.5
    w.save("saiga_reload_start_1", w.at(0.3, (0, rustle * 0.6)), -12)
    paddle = metal(0.04, (2100, 3600, 5400), 0.008)
    scrape = w.band(w.noise(0.16), 500, 3500) * np.sin(np.pi * w.t(0.16) / 0.16) ** 2
    w.save("saiga_mag_out_1", w.at(0.35, (0, paddle), (0.03, scrape * 0.45), (0.12, metal(0.04, (1500, 2700), 0.01) * 0.4)), -4)
    thump = w.band(w.noise(0.12), 45, 500) * w.env(0.12, 0.001, 0.03)
    latch = metal(0.07, (1800, 3100, 4700), 0.02, bright=1500)
    w.save("saiga_mag_in_1", w.at(0.4, (0, scrape[: int(0.08 * SR)] * 0.35), (0.07, thump * 1.4), (0.075, latch * 1.0)), -2)
    # Charging handle: a short scrape, then the carrier slams home.
    slam = metal(0.14, (680, 1380, 2500), 0.06, bright=850)
    w.save("saiga_slide_release_1", w.at(0.45, (0, scrape[: int(0.06 * SR)] * 0.5), (0.05, slam), (0.05, thump * 1.2),
                                         (0.16, metal(0.05, (1900, 3100), 0.012) * 0.35)), -1)
    w.save("saiga_dry_fire_1", w.at(0.15, (0, metal(0.08, (1000, 2050, 3400), 0.02))), -6)
    w.save("saiga_reload_cancel_1", w.at(0.2, (0, rustle[: int(0.12 * SR)] * 0.5)), -14)

    # 12-gauge hull on the floor: hollow plastic tock, brass head tick.
    for v in (1, 2):
        tock = w.partials(0.12, (430 + 40 * v, 980, 1700), (0.02, 0.012, 0.008), (1.0, 0.5, 0.25), detune=0.03)
        tick = metal(0.05, (3300 + 200 * v, 5200), 0.01, bright=3000)
        w.save(f"shotshell_{v}", w.at(0.25, (0, tock), (0.002, tick * 0.35), (0.09, tock[: int(0.05 * SR)] * 0.3)), -7)

    # Ember fire catching: a soft whump and a crackle.
    whump = w.band(w.noise(0.4), 60, 700) * w.env(0.4, 0.03, 0.12)
    w.save("burn_1", w.at(1.0, (0, whump * 0.8), (0.02, crackle(0.95, 45, decay=0.5) * 0.7)), -8)
    # Shell-type selector: a dry tactile click.
    w.save("ammo_select_1", w.at(0.08, (0, metal(0.05, (2900, 4600), 0.005, bright=2600))), -12)
    print(f"wrote Saiga sounds to {out}")


if __name__ == "__main__":
    write_all()
