#!/usr/bin/env python3
"""Synthesizes the enemy and gore sounds (no third-party audio; see CREDITS.md).

- Enemy guns, heard from the player's side of the room (so drier and duller
  than the player's own guns): Type 56 (7.62x39, unsuppressed, sharp crack),
  pump shotgun (big low boom plus the pump), Type 85 SMG (light, fast).
- Rounds going past the player: supersonic crack-snap or a subsonic whizz.
- Body fall, enemy reload, pain grunt (breath and a voiced "uh", no words).
- Gore: wet flesh tear with a bone crack for severing.
- Player movement: slide scrape, mantle grab.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_enemy_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(56)
SR = w.SR


def chirp(sec, f0, f1):
    return np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, int(sec * SR))) / SR)


def gun(variant, crack_amt, blast_lo, blast_hi, boom_hz, boom_decay, sec=0.45, mech=None):
    crack = w.band(w.noise(0.03), 2400, 11000) * w.env(0.03, 0.0002, 0.005)
    blast = w.band(w.noise(0.14), blast_lo, blast_hi) * w.env(0.14, 0.0004, 0.022)
    boom = w.band(w.noise(sec), 30, 300) * w.env(sec, 0.002, boom_decay)
    sub = chirp(0.25, boom_hz + 5 * variant, boom_hz * 0.5) * w.env(0.25, 0.001, boom_decay * 0.9)
    parts = [(0.0, crack * crack_amt), (0.0, blast * 1.5), (0.0, boom * 1.4), (0.0, sub)]
    if mech is not None:
        parts.append(mech)
    return w.at(sec, *parts)


def body_fall():
    thud = w.band(w.noise(0.35), 40, 500) * w.env(0.35, 0.002, 0.07)
    cloth = w.band(w.noise(0.4), 800, 5000) * np.sin(np.pi * w.t(0.4) / 0.4) ** 2 * 0.25
    second = w.band(w.noise(0.2), 60, 700) * w.env(0.2, 0.002, 0.04)
    return w.at(0.7, (0.0, thud * 1.4), (0.0, cloth), (0.22, second * 0.8))


def grunt(variant):
    sec = 0.42
    x = w.t(sec)
    f0 = 120 + 18 * variant
    pitch = f0 * (1.15 - 0.35 * x / sec)
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    # Glottal-ish buzz (harmonics) through two vowel formants.
    buzz = sum(np.sin(k * phase) / k for k in range(1, 18))
    voiced = w.band(buzz, 250, 900) * 0.9 + w.band(buzz, 1000, 1500) * 0.35
    shape = np.clip(x / 0.03, 0, 1) * np.exp(-np.maximum(x - 0.05, 0) / 0.14)
    breath = w.band(w.noise(sec), 500, 4000) * shape * 0.25
    return (voiced * shape + breath)


def whizz(supersonic):
    if supersonic:
        snap = w.band(w.noise(0.03), 3000, 14000) * w.env(0.03, 0.0001, 0.003)
        nwave = np.concatenate([np.linspace(1, -1, int(0.0006 * SR)), np.zeros(10)])
        hiss = w.band(w.noise(0.12), 2000, 9000) * w.env(0.12, 0.005, 0.03) * 0.3
        return w.at(0.2, (0.0, nwave), (0.0, snap * 1.4), (0.0, hiss))
    sec = 0.3
    x = w.t(sec)
    doppler = chirp(sec, 1900, 700) * np.exp(-((x - 0.1) / 0.06) ** 2)
    air = w.band(w.noise(sec), 900, 5000) * np.exp(-((x - 0.1) / 0.07) ** 2)
    return doppler * 0.4 + air * 0.8


def sever():
    tear = w.band(w.noise(0.3), 300, 3500) * w.env(0.3, 0.002, 0.06)
    squelch = w.band(w.noise(0.25), 120, 900) * w.env(0.25, 0.004, 0.08) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * w.t(0.25)))
    crack = w.click(0.08, (900, 1700, 3100), 0.018, bright=1500)
    splat = w.band(w.noise(0.2), 150, 2500) * w.env(0.2, 0.002, 0.05)
    return w.at(0.6, (0.0, crack * 1.2), (0.0, tear), (0.02, squelch * 1.2), (0.12, splat * 0.6))


def reload():
    latch = w.click(0.05, (1800, 3100, 4900), 0.015)
    seat = w.click(0.08, (900, 1800, 2900), 0.03, bright=1200)
    rack = w.at(0.25, (0, w.click(0.06, (1500, 2600, 4200), 0.02)), (0.12, w.click(0.07, (1100, 2100, 3600), 0.025)))
    return w.at(2.2, (0.3, latch), (1.3, seat * 1.3), (1.9, rack))


def slide():
    sec = 0.7
    x = w.t(sec)
    scrape = w.band(w.noise(sec), 400, 5000) * np.clip(x / 0.03, 0, 1) * np.exp(-x / 0.35) * (0.8 + 0.2 * np.sin(2 * np.pi * 37 * x))
    thud = w.band(w.noise(0.15), 50, 400) * w.env(0.15, 0.002, 0.03)
    return w.at(sec, (0.0, thud * 0.8), (0.0, scrape * 0.7))


def mantle():
    grab = w.band(w.noise(0.12), 200, 2500) * w.env(0.12, 0.001, 0.03)
    push = w.band(w.noise(0.3), 60, 600) * np.sin(np.pi * w.t(0.3) / 0.3) ** 2 * 0.5
    step = w.band(w.noise(0.1), 80, 1500) * w.env(0.1, 0.001, 0.025)
    return w.at(0.5, (0.0, grab), (0.05, push), (0.32, step * 0.8))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        bolt = (0.018, w.click(0.05, (1600 + 80 * v, 2900, 4400), 0.012, bright=1700) * 0.5)
        w.save(f"enemy_t56_shot_{v}", gun(v, 1.3, 200, 6000, 85, 0.08, mech=bolt), -2)
        pump = (0.32, w.at(0.3, (0, w.click(0.06, (900, 1700, 2600), 0.03, bright=1000)),
                           (0.16, w.click(0.07, (1200, 2200, 3300), 0.025, bright=1100))) * 0.6)
        w.save(f"enemy_pump_shot_{v}", gun(v, 0.6, 90, 3500, 60, 0.12, sec=0.75, mech=pump), -1)
        w.save(f"enemy_smg_shot_{v}", gun(v, 0.4, 300, 7000, 110, 0.05, sec=0.3,
                                          mech=(0.012, w.click(0.04, (2400, 3800, 5600), 0.01) * 0.4)), -4)
        w.save(f"enemy_pain_{v}", grunt(v), -6)
        w.save(f"whizz_{v}", whizz(v != 3), -3)
    w.save("body_fall_1", body_fall(), -3)
    w.save("gore_sever_1", sever(), -1)
    w.save("enemy_reload_1", reload(), -6)
    w.save("slide_1", slide(), -6)
    w.save("mantle_1", mantle(), -6)
    print(f"wrote enemy sounds to {out}")


if __name__ == "__main__":
    write_all()
