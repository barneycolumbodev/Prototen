#!/usr/bin/env python3
"""Synthesizes the operative's footsteps (no third-party audio; see CREDITS.md).

Owner, 2026-11-17: movement should feel like "someone smoothly stepping",
not a camera gliding. Every heel strike is heard (src/player/gait.gd picks
them off the stride). The operative is a heavy augmented body in a hardened
suit and combat boots, so each step is a low, weighty thud with the sole's
grit on top, then the roll onto the toe. No ringing on metal (owner,
2026-11-07: "get rid of the metal dinging"): metal is a hollow, damped thump.

Banks (4 variants each, so a run never repeats the same step):
- step_concrete: wet harbour concrete and asphalt (the default)
- step_metal: container roofs, deck plate, gratings
- step_wood: the pier boards and crates (a hollow knock under the heel)
- step_dirt: sandbags, earth (soft crunch)
- step_land: both feet taking a fall (body and suit, layered with the surface)
- step_gear: the suit's plates and kit shifting on a running stride

Usage: python3 raw_assets/audio/build_footstep_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(1117)
SR = w.SR
SEC = 0.32


def heel(lo, hi, decay, amp=1.0):
    """The heel's thud: a short low burst."""
    return w.band(w.noise(SEC), lo, hi) * w.env(SEC, 0.0015, decay) * amp


def grit(lo, hi, decay, amp):
    """The sole's scrape and grit on top of the thud."""
    g = w.band(w.noise(SEC), lo, hi) * w.env(SEC, 0.0008, decay)
    # Grains: a sparse crackle, not a smooth hiss.
    grains = (w.rng.random(int(SEC * SR)) > 0.985).astype(float) * w.rng.standard_normal(int(SEC * SR))
    g += w.band(grains, lo * 1.5, min(hi * 1.5, 16000)) * w.env(SEC, 0.001, decay * 1.6) * 0.8
    return g * amp


def knock(lo, hi, decay, amp):
    """The boot sole meeting the ground: the mid-range knock that a phone
    speaker can actually play (most of the thud is below what it reproduces)."""
    return w.band(w.noise(SEC), lo, hi, order=3) * w.env(SEC, 0.0008, decay) * amp


def body(f0, decay, amp):
    """The weight going through the leg: a sub-bass push, felt more than heard."""
    x = w.t(SEC)
    f = f0 * (1.0 - 0.35 * np.clip(x / 0.06, 0, 1))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return s * np.clip(x / 0.004, 0, 1) * np.exp(-x / decay) * amp


def step(v, surface):
    roll = 0.045 + 0.012 * v + w.rng.uniform(-0.006, 0.006)
    if surface == "concrete":
        parts = [
            (0.0, heel(45, 320, 0.022, 0.9)),
            (0.0, knock(220, 1100, 0.012, 1.6)),
            (0.0, body(62 + 3 * v, 0.03, 0.35)),
            (0.002, grit(1800, 7500, 0.018, 0.3)),
            (roll, knock(300, 1400, 0.01, 0.6)),
            (roll, grit(2500, 9000, 0.03, 0.2)),
        ]
    elif surface == "metal":
        # Hollow and damped: a low box resonance under the heel, no ring.
        x = w.t(SEC)
        box = (np.sin(2 * np.pi * (185 + 9 * v) * x) * np.exp(-x / 0.03)
               + 0.5 * np.sin(2 * np.pi * (410 + 13 * v) * x) * np.exp(-x / 0.018))
        parts = [
            (0.0, heel(50, 420, 0.02, 0.8)),
            (0.0, knock(250, 1000, 0.014, 1.3)),
            (0.0, box * 0.45),
            (0.0, body(58 + 3 * v, 0.03, 0.3)),
            (0.001, grit(1500, 5200, 0.012, 0.3)),
            (roll, heel(90, 700, 0.014, 0.45)),
            (roll, box[: int(0.1 * SR)] * 0.2),
        ]
    elif surface == "wood":
        x = w.t(SEC)
        wknock = (np.sin(2 * np.pi * (215 + 9 * v) * x) * np.exp(-x / 0.035)
                 + 0.4 * np.sin(2 * np.pi * (480 + 17 * v) * x) * np.exp(-x / 0.02))
        creak = w.band(w.noise(SEC), 600, 1800) * w.env(SEC, 0.02, 0.05) * 0.12
        parts = [
            (0.0, heel(60, 600, 0.02, 0.7)),
            (0.0, knock(260, 1200, 0.012, 1.1)),
            (0.0, wknock * 0.6),
            (0.0, body(66 + 3 * v, 0.028, 0.3)),
            (0.002, grit(1600, 6000, 0.014, 0.28)),
            (roll, heel(90, 800, 0.016, 0.45)),
            (roll * 0.8, creak),
        ]
    else:  # dirt
        parts = [
            (0.0, heel(40, 260, 0.03, 0.8)),
            (0.0, knock(180, 900, 0.02, 1.2)),
            (0.0, body(55 + 3 * v, 0.035, 0.3)),
            (0.004, grit(700, 4200, 0.05, 0.55)),
            (roll, grit(900, 5000, 0.045, 0.35)),
        ]
    return w.at(SEC, *parts)


def land(v):
    """Both feet and the body taking a fall: a deep thump and the suit settling."""
    sec = 0.55
    x = w.t(sec)
    f = (52 + 4 * v) * (1.0 - 0.4 * np.clip(x / 0.08, 0, 1))
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(x / 0.003, 0, 1) * np.exp(-x / 0.07)
    thud = w.band(w.noise(sec), 35, 380) * w.env(sec, 0.002, 0.04)
    second = w.band(w.noise(sec), 50, 500) * w.env(sec, 0.002, 0.025)
    plates = gear_burst(sec, 0.03, 0.12, 5)
    mid = w.band(w.noise(sec), 150, 1100, order=3) * w.env(sec, 0.001, 0.03)
    return w.at(sec, (0.0, sub * 0.8), (0.0, thud * 0.9), (0.0, mid * 2.2), (0.028, second * 0.8), (0.01, plates * 0.9))


def gear_burst(sec, start, spread, n):
    """Hard plates and buckles knocking: dull clicks, no ring."""
    out = np.zeros(int(sec * SR))
    for _ in range(n):
        at = start + w.rng.uniform(0, spread)
        c = w.band(w.noise(0.03), 900 + w.rng.uniform(0, 1400), 5200) * w.env(0.03, 0.0003, 0.004)
        i = int(at * SR)
        m = min(len(c), len(out) - i)
        if m > 0:
            out[i:i + m] += c[:m] * w.rng.uniform(0.4, 1.0)
    return out


def gear(v):
    """The kit shifting on a running stride: a few soft knocks and fabric."""
    sec = 0.25
    cloth = w.band(w.noise(sec), 700, 3800) * np.sin(np.pi * np.clip(w.t(sec) / 0.14, 0, 1)) ** 2 * 0.25
    return w.at(sec, (0.0, gear_burst(sec, 0.01, 0.07, 3 + v % 2)), (0.0, cloth))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for surface in ("concrete", "metal", "wood", "dirt"):
        for v in (1, 2, 3, 4):
            w.save(f"step_{surface}_{v}", step(v, surface), -4)
    for v in (1, 2):
        w.save(f"step_land_{v}", land(v), -3)
    for v in (1, 2, 3):
        w.save(f"step_gear_{v}", gear(v), -8)


if __name__ == "__main__":
    write_all()
