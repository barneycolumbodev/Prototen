#!/usr/bin/env python3
"""Synthesizes the sounds of the new triad roles (docs/design.md §8.8b-g, 2026-11-16).
No third-party audio (see CREDITS.md); shares helpers with build_weapon_sfx.py and
build_enemy_sfx.py.

- enemy_t79_shot   the Marksman's Type 79 (7.62x54R): a hard supersonic crack and a long rolling boom.
- enemy_t80_shot   the Gunner's Type 80 belt-fed: heavier than the Type 56, with the feed's clack.
- enemy_qbz_shot   the specialist's QBZ-95: a sharp, high, short report.
- enemy_t54_shot   the Shield man's Type 54 pistol: a flat bark.
- molotov_break    glass bursting and the fuel splashing out.
- molotov_burst    the fuel catching: a soft roaring whoomph.
- fire_loop        a burning pool: crackle over a low roar (loops; FirePatch plays it).
- emp_pulse        the EMP grenade: a falling electric zap, a buzz and crackle.

Usage: python3 raw_assets/audio/build_role_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out_arg = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
sys.argv = sys.argv[:1]
import build_weapon_sfx as w  # noqa: E402
import build_enemy_sfx as en  # noqa: E402

w.rng = np.random.default_rng(1116)
SR = w.SR


def crackle(sec, rate, lo=1500, hi=9000):
    """Random sharp pops (burning wood, arcing)."""
    x = np.zeros(int(sec * SR))
    n = int(rate * sec)
    for _ in range(n):
        i = w.rng.integers(0, len(x) - 400)
        k = w.rng.integers(60, 400)
        x[i:i + k] += w.rng.uniform(0.3, 1.0) * np.exp(-np.arange(k) / (k / 5)) * w.rng.choice([-1, 1])
    return w.band(x, lo, hi)


def molotov_break():
    glass = np.zeros(int(0.6 * SR))
    for k in range(9):
        s = w.band(w.noise(0.12), 3000 + 600 * k, 11000) * w.env(0.12, 0.0003, 0.01 + 0.006 * k)
        i = int(w.rng.uniform(0.0, 0.08) * SR)
        glass[i:i + len(s)] += s * w.rng.uniform(0.4, 1.0)
    splash = w.band(w.noise(0.6), 300, 2500) * w.env(0.6, 0.01, 0.16)
    return w.at(0.6, (0.0, glass * 1.4), (0.02, splash * 0.8))


def molotov_burst():
    roar = w.band(w.noise(1.4), 60, 900) * w.env(1.4, 0.12, 0.5)
    hiss = w.band(w.noise(1.4), 1500, 6000) * w.env(1.4, 0.05, 0.35) * 0.3
    return w.at(1.4, (0.0, roar * 1.6), (0.0, hiss), (0.05, crackle(1.3, 30) * 0.4))


def fire_loop():
    sec = 3.0
    roar = w.band(w.noise(sec), 50, 700) * 0.8
    lick = w.band(w.noise(sec), 700, 3000) * (0.25 + 0.15 * np.sin(np.linspace(0, 2 * np.pi * 3, int(sec * SR))))
    x = roar + lick + crackle(sec, 22) * 0.5
    # Crossfade the ends so it loops without a click.
    f = int(0.2 * SR)
    x[:f] = x[:f] * np.linspace(0, 1, f) + x[-f:] * np.linspace(1, 0, f)
    return x[:-f]


def emp_pulse():
    sec = 1.2
    zap = en.chirp(0.5, 2400, 90) * w.env(0.5, 0.001, 0.18)
    buzz = np.sign(np.sin(2 * np.pi * 120 * np.arange(int(0.9 * SR)) / SR)) * w.env(0.9, 0.01, 0.3) * 0.25
    thump = w.band(w.noise(0.4), 40, 220) * w.env(0.4, 0.002, 0.1)
    return w.at(sec, (0.0, zap), (0.0, thump * 1.5), (0.03, w.band(buzz, 200, 4000)), (0.0, crackle(1.0, 70, 2000, 10000) * 0.6))


def write_all():
    w.OUT = out_arg
    os.makedirs(out_arg, exist_ok=True)
    for v in (1, 2, 3):
        bolt = (0.02, w.click(0.05, (1500 + 60 * v, 2700, 4100), 0.014, bright=1600) * 0.45)
        w.save(f"enemy_t79_shot_{v}", en.gun(v, 1.8, 180, 7000, 70, 0.16, sec=0.9, mech=bolt), 0)
        feed = (0.03, w.click(0.04, (1100 + 70 * v, 2300, 3600), 0.01, bright=1300) * 0.6)
        w.save(f"enemy_t80_shot_{v}", en.gun(v, 1.4, 160, 6000, 75, 0.1, sec=0.5, mech=feed), -1)
        w.save(f"enemy_qbz_shot_{v}", en.gun(v, 1.5, 350, 8000, 100, 0.06, sec=0.35,
                                             mech=(0.014, w.click(0.04, (2600, 4100, 6000), 0.009) * 0.4)), -2)
        w.save(f"enemy_t54_shot_{v}", en.gun(v, 0.7, 260, 6000, 120, 0.05, sec=0.3,
                                             mech=(0.01, w.click(0.035, (2000, 3300, 5000), 0.01) * 0.5)), -3)
    w.save("molotov_break_1", molotov_break(), -1)
    w.save("molotov_burst_1", molotov_burst(), -2)
    w.save("fire_loop_1", fire_loop(), -6)
    w.save("emp_pulse_1", emp_pulse(), -1)


if __name__ == "__main__":
    write_all()
