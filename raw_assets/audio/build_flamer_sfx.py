#!/usr/bin/env python3
"""Synthesizes the Triad Flamer sounds (no third-party audio; see CREDITS.md).

- flamer_ignite_1..3: lighter flint spark + pressurized aerosol hiss-fwoosh (the tell).
- flamer_spray_1..2: turbulent roaring aerosol flame stream (nozzle hiss + fire roar).
- flamer_can_boom_1..3: metallic can puncture pop into a deep fuel-air WHOOMPH fireball.
- player_burn_1..2: close-up scorching sizzle when caught in the flame.

Usage: python3 raw_assets/audio/build_flamer_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(771)
SR = w.SR


def _low_mod(sec, f_lo, f_hi):
    """Slow random flutter (turbulent flame modulation) in 0.45..1.35."""
    n = w.noise(sec)
    m = w.band(n, f_lo, f_hi)
    m = m / (np.max(np.abs(m)) + 1e-6)
    return 0.9 + 0.45 * m


def flamer_ignite(variant):
    """Flint-wheel strike + pressurized aerosol hiss catching fire (0.48 s)."""
    sec = 0.48
    # Metallic flint scratch & wheel click
    flint = w.click(0.035, (3200 + 220 * variant, 5400, 8200), 0.008, bright=3400)
    spark = w.band(w.noise(0.04), 4500, 12000) * w.env(0.04, 0.0005, 0.009)
    # Pressurized aerosol hiss before the plume catches
    hiss_t = w.t(0.24)
    hiss_env = np.clip(hiss_t / 0.015, 0, 1) * np.exp(-np.maximum(hiss_t - 0.06, 0) / 0.09)
    hiss = w.band(w.noise(0.24), 2600, 10500) * hiss_env * 0.7
    # Fuel-air ignition "fwoosh!" blooming upward
    fw_t = w.t(0.36)
    fw_env = np.clip(fw_t / 0.03, 0, 1) * np.exp(-np.maximum(fw_t - 0.05, 0) / 0.12)
    fw_lo = w.band(w.noise(0.36), 85, 520) * fw_env * 1.4
    fw_mid = w.band(w.noise(0.36), 450, 2200) * fw_env * 0.85
    return w.at(sec, (0.0, flint * 0.9), (0.008, spark * 0.7), (0.045, hiss), (0.09, fw_lo + fw_mid))


def flamer_spray(variant):
    """Continuous turbulent aerosol flame jet (1.5 s, soft edges for clean re-triggering)."""
    sec = 1.5
    x = w.t(sec)
    # Smooth fade in/out so looping or chaining never clicks
    edge = np.clip(x / 0.06, 0, 1) * np.clip((sec - x) / 0.12, 0, 1)
    flutter = _low_mod(sec, 4.0 + variant, 16.0 + 2.0 * variant)
    flutter2 = _low_mod(sec, 12.0, 34.0)
    # Deep billowing combustion roar
    roar = w.band(w.noise(sec), 75, 480) * flutter * 1.45
    # Mid flame body turbulence
    body = w.band(w.noise(sec), 420, 2400) * flutter2 * 0.95
    # Pressurized aerosol nozzle hiss
    hiss = w.band(w.noise(sec), 3200, 11500) * (0.6 + 0.25 * flutter2) * 0.65
    # Sparse hot fuel crackles
    crackle_imp = (w.rng.random(int(sec * SR)) < (18.0 / SR)).astype(np.float64)
    crackle = w.band(crackle_imp * w.rng.standard_normal(len(crackle_imp)), 1800, 7500) * 6.0
    return (roar + body + hiss + crackle) * edge


def flamer_can_boom(variant):
    """Aerosol can shot -> metallic tin puncture pop + billowing BLEVE fireball WHOOMPH (1.35 s)."""
    sec = 1.35
    # Sharp metallic tin-can puncture & pressurized rupture snap
    pop = w.click(0.045, (1450 + 110 * variant, 2900, 5200), 0.011, bright=2400) * 1.1
    vent = w.band(w.noise(0.07), 3000, 11000) * w.env(0.07, 0.001, 0.02) * 0.85
    # Deep fuel-air WHOOMPH (blooms over 40 ms rather than a sharp HE crack!)
    x = w.t(1.25)
    bloom = np.clip(x / 0.038, 0, 1) ** 0.7 * np.exp(-np.maximum(x - 0.04, 0) / 0.28)
    sub_f = np.linspace(115.0 + 8.0 * variant, 34.0, len(x))
    sub = np.sin(2 * np.pi * np.cumsum(sub_f) / SR) * np.clip(x / 0.02, 0, 1) * np.exp(-x / 0.24) * 1.15
    whoomph = w.band(w.noise(1.25), 55, 360) * bloom * 1.85
    # Billowing fireball roar & turbulent tail
    tail_env = np.clip(x / 0.05, 0, 1) * np.exp(-np.maximum(x - 0.08, 0) / 0.42)
    fire_tail = w.band(w.noise(1.25), 240, 2600) * tail_env * _low_mod(1.25, 5.0, 22.0) * 1.1
    # Hot spark & flame crackle shower after the bloom
    cr_imp = (w.rng.random(len(x)) < (42.0 / SR)).astype(np.float64) * tail_env
    crackle = w.band(cr_imp * w.rng.standard_normal(len(x)), 1600, 8000) * 5.5
    return w.at(sec, (0.0, pop), (0.005, vent), (0.016, sub + whoomph + fire_tail + crackle))


def player_burn(variant):
    """Short visceral flame scorch/sizzle on the player (0.34 s)."""
    sec = 0.34
    x = w.t(sec)
    env = np.clip(x / 0.012, 0, 1) * np.exp(-np.maximum(x - 0.03, 0) / 0.11)
    sizzle = w.band(w.noise(sec), 1800, 9500) * env * 0.9
    heat = w.band(w.noise(sec), 140 + 25 * variant, 900) * env * 1.1
    return sizzle + heat


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"flamer_ignite_{v}", flamer_ignite(v), -3)
        w.save(f"flamer_can_boom_{v}", flamer_can_boom(v), -1)
    for v in (1, 2):
        w.save(f"flamer_spray_{v}", flamer_spray(v), -4)
        w.save(f"player_burn_{v}", player_burn(v), -5)
    print(f"wrote flamer sounds to {out}")


if __name__ == "__main__":
    write_all()
