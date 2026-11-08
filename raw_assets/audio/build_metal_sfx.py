#!/usr/bin/env python3
"""Dull replacements for the sounds that rang like a bell (owner, 2026-11-07:
"I really need you to get rid of the metal dinging. It still dings every
time you shoot.").

The ding was mostly the brass casing: every shot dropped one and its bounce
was three undamped partials at 3-6 kHz that rang for ~70 ms, so each shot
was followed by a "ting". Chinatown also has 120 steel posts, roller
shutters and thin sheet panels whose impacts rang (a 640 Hz clang, a can
ping) and glancing rounds whined as pure tones.

Here nothing is allowed to ring: every partial dies in under 15 ms and the
body of each sound is filtered noise, so they read as "tick", "thunk",
"clack" and a hiss rather than a note.

Runs after build_weapon_sfx.py / build_enemy_sfx.py, which skip these names.
Usage: python3 raw_assets/audio/build_metal_sfx.py [out_dir]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(907)
SR = w.SR
w.REPLACED = set()


def damped(sec, freqs, decay):
    return w.partials(sec, freqs, [decay] * len(freqs), [1.0, 0.6, 0.35][: len(freqs)], detune=0.04)


def casing(v):
    """Brass on wet concrete: a soft tick and a smaller second one, no ring."""
    tick = w.band(w.noise(0.03), 1200, 6000) * w.env(0.03, 0.0002, 0.0025)
    body = damped(0.03, (1500 + 140 * v, 2500 + 90 * v), 0.0035)
    roll = w.band(w.noise(0.09), 900, 3500) * w.env(0.09, 0.004, 0.02) * 0.12
    one = tick + body * 0.25
    return w.at(0.22, (0.0, one), (0.05 + 0.015 * v, one * 0.35), (0.07, roll))


def shutter():
    """A round into a roller shutter or a steel post: a thwack and a short
    rattle of loose slats. Broadband and dead, not a bell."""
    crack = w.band(w.noise(0.03), 1500, 9000) * w.env(0.03, 0.0002, 0.003)
    thwack = w.band(w.noise(0.08), 180, 2400) * w.env(0.08, 0.0005, 0.012)
    thump = w.band(w.noise(0.1), 60, 350) * w.env(0.1, 0.001, 0.02)
    x = w.t(0.18)
    rattle = w.band(w.noise(0.18), 500, 3500) * np.exp(-x / 0.04) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * x)))
    knock = damped(0.04, (420, 980), 0.008)
    return w.at(0.22, (0, crack * 0.9), (0, thwack * 1.3), (0, thump * 1.2), (0.004, knock * 0.3), (0.01, rattle * 0.35))


def sheet():
    """Thin sheet metal / a panel: a flat tsk-thunk."""
    tsk = w.band(w.noise(0.04), 2000, 10000) * w.env(0.04, 0.0002, 0.004)
    flex = w.band(w.noise(0.07), 300, 2200) * w.env(0.07, 0.0005, 0.01)
    return w.at(0.12, (0, tsk), (0, flex * 1.2), (0.002, damped(0.03, (760, 1650), 0.006) * 0.2))


def ricochet(v):
    """A glancing round: a chip and a falling hiss of air (band-passed noise
    sweeping down), not a sine whine."""
    sec = 0.35
    n = int(sec * SR)
    x = w.t(sec)
    src = w.noise(sec)
    out = np.zeros(n)
    hop = 256
    f0 = [3200, 2600, 3800][v - 1]
    for i in range(0, n, hop):
        f = f0 * np.exp(-x[i] * 2.5)
        seg = src[i:i + hop]
        out[i:i + len(seg)] = seg
        out[i:i + len(seg)] = w.band(src[max(0, i - 1024):i + hop], f * 0.6, f * 1.5)[-len(seg):]
    hiss = out * np.clip(x / 0.01, 0, 1) * np.exp(-x / 0.09)
    chip = w.band(w.noise(0.05), 700, 5000) * w.env(0.05, 0.0003, 0.008)
    tick = w.band(w.noise(0.02), 2500, 12000) * w.env(0.02, 0.0002, 0.003)
    return w.at(sec, (0, tick), (0, chip * 0.7), (0.004, hiss * 0.45))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"shell_{v}", casing(v), -12)
        w.save(f"ricochet_{v}", ricochet(v), -10)
    w.save("impact_metal_1", shutter(), -3)
    w.save("impact_can_1", sheet(), -5)
    print("wrote dull metal sounds to", out)


if __name__ == "__main__":
    write_all()
