#!/usr/bin/env python3
"""Synthesizes the operative's midair dropkick sounds (no third-party audio; see CREDITS.md).

Grounded military-scifi hardware feel (CLAUDE.md §1): heavy augmented legs
driving through the air, twin armored combat boots slamming into a torso, a
crisp weapon whip-up into the diving stance, and a weighty tactical skid landing.
Strong mid-low punch (160-1100 Hz) so hits cut cleanly through phone speakers.

Banks:
- dropkick_launch_1..3 : hydraulic/myomer snap + rushing air whoosh as legs whip up
- dropkick_hit_1..3    : brutal double-boot chest slam (staggered L/R boot crunch + deep sub boom)
- dropkick_land_1..3   : low armored roll/skid touchdown + gear settle
- dropkick_draw_1..2   : tight holster/sling snap as the gun sweeps into diving fire

Usage: python3 raw_assets/audio/build_dropkick_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(1122)
SR = w.SR


def sweep_sine(sec, f0, f1, tau_freq, attack, decay, amp=1.0):
    x = w.t(sec)
    f = f1 + (f0 - f1) * np.exp(-x / max(tau_freq, 1e-4))
    ph = 2.0 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * w.env(sec, attack, decay) * amp


def swept_whoosh(sec, lo0, lo1, hi0, hi1, peak_t, amp=1.0):
    """Dynamic air-cut whoosh: blends low and high noise bands along a rising bell envelope."""
    x = w.t(sec)
    n = w.noise(sec)
    low_b = w.band(n, lo0, hi0, order=2)
    high_b = w.band(n, lo1, hi1, order=2)
    blend = np.clip(x / max(peak_t * 1.4, 0.02), 0.0, 1.0)
    sig = low_b * (1.0 - blend) + high_b * blend
    bell = np.clip(x / max(peak_t, 0.01), 0.0, 1.0) ** 1.4 * np.exp(-np.maximum(x - peak_t, 0.0) / (sec * 0.34))
    return sig * bell * amp


def launch(v):
    sec = 0.36
    # Myomer/hydraulic leg snap + thigh piston punch.
    snap = sweep_sine(sec, 135 + 8 * v, 44, 0.032, 0.002, 0.055, 0.85)
    latch = w.band(w.noise(sec), 550, 2100, order=3) * w.env(sec, 0.001, 0.016) * 0.65
    # Heavy air-cut whoosh as both boots whip forward.
    whoosh = swept_whoosh(sec, 120, 420, 620, 1950, 0.085 + 0.008 * v, 1.15)
    # Suit cloth/plate shift.
    cloth = w.band(w.noise(sec), 1100, 4200, order=2) * w.env(sec, 0.012, 0.055) * 0.28
    # Knee lock-out secondary thump at extension.
    lock = w.band(w.noise(sec), 180, 750, order=2) * w.env(sec, 0.002, 0.025) * 0.5
    mix = w.at(sec,
               (0.0, snap),
               (0.004, latch),
               (0.010, whoosh),
               (0.015, cloth),
               (0.075 + 0.006 * v, lock))
    return np.tanh(mix * 1.15)


def hit(v):
    sec = 0.50
    # Heavy sub-bass body shockwave.
    sub = sweep_sine(sec, 82 + 5 * v, 26, 0.045, 0.0015, 0.145, 1.35)
    # Mid-low chest punch (cuts cleanly through small phone speakers).
    slam = w.band(w.noise(sec), 140, 920, order=3) * w.env(sec, 0.001, 0.048) * 1.55
    thump = sweep_sine(sec, 195 + 11 * v, 68, 0.018, 0.001, 0.042, 0.95)
    # Staggered twin-boot crunch (right lead boot at 0 ms, left boot 14 ms later).
    n1 = w.noise(sec)
    crunch1 = w.band(n1, 850, 4400, order=2) * w.env(sec, 0.0008, 0.028) * 0.90
    grains = (w.rng.random(int(sec * SR)) > 0.978).astype(float) * w.rng.standard_normal(int(sec * SR))
    crack = w.band(grains, 1200, 6200, order=2) * w.env(sec, 0.001, 0.042) * 1.15
    boot2_thud = w.band(w.noise(sec), 180, 1200, order=2) * w.env(sec, 0.001, 0.032) * 0.85
    # Suit plate damped knock + wind knocked out of target.
    plate = w.band(w.noise(sec), 340, 1400, order=3) * w.env(sec, 0.0015, 0.022) * 0.55
    air = w.band(w.noise(sec), 90, 380, order=2) * w.env(sec, 0.018, 0.14) * 0.45
    mix = w.at(sec,
               (0.0, sub),
               (0.0, slam),
               (0.0, thump),
               (0.002, crunch1),
               (0.005, crack),
               (0.014 + 0.003 * v, boot2_thud),
               (0.016, plate),
               (0.024, air))
    return np.tanh(mix * 1.45)


def land(v):
    sec = 0.46
    # Heavy armored back/hip touchdown thump.
    sub = sweep_sine(sec, 62 + 4 * v, 28, 0.045, 0.002, 0.095, 1.05)
    thud = w.band(w.noise(sec), 65, 520, order=2) * w.env(sec, 0.002, 0.045) * 1.15
    knock = w.band(w.noise(sec), 260, 1200, order=3) * w.env(sec, 0.001, 0.020) * 0.85
    # Gritty tactical skid along the floor.
    grains = (w.rng.random(int(sec * SR)) > 0.965).astype(float) * w.rng.standard_normal(int(sec * SR))
    skid = (w.band(w.noise(sec), 750, 3600, order=2) * 0.55
            + w.band(grains, 1400, 6800, order=2) * 0.85) * w.env(sec, 0.018, 0.13) * 0.65
    # Suit gear settling as operative springs back up.
    gear = w.band(w.noise(sec), 420, 1900, order=2) * w.env(sec, 0.004, 0.032) * 0.35
    mix = w.at(sec,
               (0.0, sub),
               (0.0, thud),
               (0.002, knock),
               (0.015, skid),
               (0.095 + 0.01 * v, gear))
    return np.tanh(mix * 1.15)


def draw(v):
    sec = 0.22
    # Crisp kydex/sling whip-up brush + tight mechanical lock-in click.
    brush = swept_whoosh(sec, 600, 1800, 2400, 6200, 0.042 + 0.005 * v, 0.72)
    grip = w.band(w.noise(sec), 320, 1600, order=3) * w.env(sec, 0.0015, 0.018) * 0.65
    clack = w.click(0.035, (1850, 3100, 4800), 0.008, 2200) * 0.42
    mix = w.at(sec,
               (0.0, brush),
               (0.045, grip),
               (0.055 + 0.004 * v, clack))
    return np.tanh(mix * 1.1)


def main():
    os.makedirs(w.OUT, exist_ok=True)
    for i in range(1, 4):
        w.save(f"dropkick_launch_{i}", launch(i), peak_db=-2.5)
        w.save(f"dropkick_hit_{i}", hit(i), peak_db=-0.5)
        w.save(f"dropkick_land_{i}", land(i), peak_db=-3.0)
    for i in range(1, 3):
        w.save(f"dropkick_draw_{i}", draw(i), peak_db=-5.0)
    print(f"dropkick sfx written to {w.OUT}")


if __name__ == "__main__":
    main()
