#!/usr/bin/env python3
"""Synthesizes the M32A1 grenade launcher and 40 mm grenade sounds (no
third-party audio; see CREDITS.md). Design §4.8.

40x46 mm low velocity: the high-low pressure system burns the charge in a
small chamber and bleeds it into the case behind the projectile, so there's
no crack (76 m/s is well under the speed of sound) and no big blast. What you
hear is a hollow "thoonk": a low pop, the 300 mm barrel ringing like a pipe,
the gas hiss, the double-action hammer fall before it and the cylinder
indexing to the next chamber after it. Reload: the crane latch and the
cylinder swinging out on its yoke, aluminium cases rattling out, a round
pushed home in each chamber, the cylinder slammed shut and the clockwork
spring ratcheting as it winds.

The grenade: a hard crack (32 g of Comp A5 detonating), the boom and its
sub-bass, steel fragments zinging off, grit and gravel raining down for a
couple of seconds; a far version (rumble and street echoes); the ringing in
the ears after one close by; a dud's dull tonk off concrete and its thud
into a body.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_m32_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(3240)
w.REPLACED = set()
SR = w.SR
rng = w.rng


def sweep(sec, f0, f1, curve=1.0):
    x = np.linspace(0, 1, int(sec * SR)) ** curve
    f = f0 + (f1 - f0) * x
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def metal(sec, freqs, decay, bright=1200):
    return w.click(sec, freqs, decay, bright=bright)


def soft_clip(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


def ratchet(sec, r0, r1, lo=1800, hi=8000, gain=0.5):
    """Pawl clicks speeding from r0 to r1 per second (the clockwork spring winding)."""
    out = np.zeros(int(sec * SR))
    t = 0.0
    while t < sec - 0.01:
        rate = r0 + (r1 - r0) * t / sec
        c = w.band(w.noise(0.012), lo, hi) * w.env(0.012, 0.0002, 0.0015)
        c += metal(0.012, (2600 + rng.uniform(-150, 150), 4300), 0.003, bright=2500) * 0.4
        i = int(t * SR)
        out[i:i + len(c)] += c[:len(out) - i] * gain * rng.uniform(0.7, 1.0)
        t += 1.0 / rate
    return out


def gravel(sec, rate, decay, lo=900, hi=7000):
    """Grit and stones pattering down: random little ticks thinning out."""
    n = int(sec * SR)
    out = np.zeros(n)
    for i in range(int(sec * rate)):
        p = int(rng.uniform(0, 1) ** 1.8 * (n - 600))
        g = rng.uniform(0.15, 1.0) * np.exp(-p / SR / decay)
        tick = w.band(w.noise(0.01), lo * rng.uniform(0.7, 1.3), hi) * w.env(0.01, 0.0002, 0.0018)
        out[p:p + tick.size] += tick * g
    return out


def zing(sec, f0, f1):
    """A fragment whining past: a fast falling whistle with a doppler drop."""
    x = w.t(sec)
    tone = sweep(sec, f0, f1, curve=0.6) * np.exp(-x / (sec * 0.35)) * np.clip(x / 0.004, 0, 1)
    return tone + w.band(w.noise(sec), f1, f0) * np.exp(-x / (sec * 0.2)) * 0.3


# ---------------------------------------------------------------- the launcher
def shot(v):
    sec = 1.0
    hammer = metal(0.03, (2200 + 80 * v, 3900, 5600), 0.006, bright=2200)
    pop = w.band(w.noise(0.07), 140, 1900) * w.env(0.07, 0.0006, 0.011)
    thump = sweep(0.32, 118 + 5 * v, 42) * w.env(0.32, 0.0015, 0.075)
    body = w.band(w.noise(0.25), 50, 420) * w.env(0.25, 0.001, 0.05)
    # The barrel as an open pipe ~0.3 m: a hollow "oonk" a few hundred hertz up.
    tube = w.partials(0.22, (520 + 15 * v, 1060, 1590), (0.045, 0.026, 0.015), (1.0, 0.45, 0.22), detune=0.02)
    hiss = w.band(w.noise(0.35), 900, 6500) * w.env(0.35, 0.004, 0.07)
    # The cylinder indexes on: pawl, star, the stop dropping in.
    index = metal(0.05, (1750 + 50 * v, 3050, 4700), 0.01, bright=1500)
    stop = metal(0.06, (1300, 2350, 3600), 0.016, bright=1200)
    out = w.at(sec, (0.0, hammer * 0.35), (0.012, pop * 1.5), (0.012, thump * 2.4), (0.012, body * 1.4),
               (0.014, tube * 0.55), (0.016, hiss * 0.4), (0.075, index * 0.45), (0.115, stop * 0.4))
    return soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.3, 1.4)


def tail():
    sec = 1.6
    low = w.band(w.noise(sec), 40, 300) * w.env(sec, 0.02, 0.38)
    mid = w.band(w.noise(sec), 250, 1800) * w.env(sec, 0.015, 0.22)
    refl = w.at(sec, *[(d, w.band(w.noise(0.06), 300, 2500) * w.env(0.06, 0.0008, 0.02) * a)
                       for d, a in ((0.03, 0.5), (0.07, 0.38), (0.12, 0.28), (0.19, 0.2), (0.28, 0.12))])
    return low * 0.8 + mid * 0.35 + refl


def dry_fire():
    pull = w.band(w.noise(0.08), 600, 3000) * np.sin(np.pi * w.t(0.08) / 0.08) ** 2 * 0.25
    return w.at(0.3, (0.0, pull), (0.07, metal(0.04, (2200, 3900), 0.006, bright=2200) * 0.6),
                (0.1, metal(0.05, (1750, 3050, 4700), 0.01, bright=1500) * 0.5))


def reload_start():
    latch = metal(0.04, (2600, 4200), 0.006, bright=2400)
    swing = w.band(w.noise(0.25), 300, 2500) * np.sin(np.pi * w.t(0.25) / 0.25) ** 2
    clunk = w.band(w.noise(0.1), 80, 900) * w.env(0.1, 0.001, 0.025)
    ring = metal(0.12, (690, 1420, 2510), 0.04, bright=800)
    return w.at(0.6, (0.0, latch * 0.8), (0.03, swing * 0.35), (0.27, clunk * 1.2), (0.27, ring * 0.5))


def cases_out():
    """Aluminium cases sliding out of the chambers and tumbling down."""
    sec = 1.0
    parts = [(0.0, w.band(w.noise(0.18), 700, 4500) * np.sin(np.pi * w.t(0.18) / 0.18) ** 2 * 0.3)]
    for i in range(6):
        d = 0.05 + i * 0.045 + rng.uniform(-0.015, 0.015)
        f = rng.uniform(820, 1100)
        tonk = w.partials(0.18, (f, f * 2.3, f * 3.9), (0.05, 0.025, 0.012), (1.0, 0.5, 0.3), detune=0.03)
        parts.append((d, tonk * rng.uniform(0.35, 0.6)))
        parts.append((d + 0.18 + rng.uniform(0, 0.15), tonk[: int(0.08 * SR)] * 0.25))
    return w.at(sec, *parts)


def round_in(v):
    slide = w.band(w.noise(0.07), 500, 3000) * np.sin(np.pi * w.t(0.07) / 0.07) ** 2
    seat = w.band(w.noise(0.08), 70, 700) * w.env(0.08, 0.001, 0.02)
    tick = metal(0.04, (1500 + 90 * v, 2700, 4300), 0.008, bright=1500)
    return w.at(0.25, (0.0, slide * 0.4), (0.06, seat * 1.4), (0.062, tick * 0.6))


def close():
    """The cylinder slammed shut on its crane, the latch, then the spring wound."""
    swing = w.band(w.noise(0.12), 300, 2500) * np.sin(np.pi * w.t(0.12) / 0.12) ** 2
    slam = w.band(w.noise(0.12), 60, 800) * w.env(0.12, 0.001, 0.03)
    ring = metal(0.16, (640, 1310, 2380), 0.05, bright=800)
    latch = metal(0.05, (2400, 4100), 0.008, bright=2200)
    return w.at(0.75, (0.0, swing * 0.4), (0.1, slam * 1.6), (0.1, ring * 0.6), (0.12, latch * 0.7),
                (0.2, ratchet(0.42, 22, 34)))


def cancel():
    return w.at(0.25, (0.0, metal(0.06, (2400, 4100), 0.01, bright=2200) * 0.6),
                (0.02, w.band(w.noise(0.08), 70, 700) * w.env(0.08, 0.001, 0.02)))


# ---------------------------------------------------------------- the grenade
def blast(v):
    sec = 3.0
    edge = np.concatenate([np.linspace(1, -1, int(0.003 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.06), 1500, 16000) * w.env(0.06, 0.0001, 0.008)
    bang = w.band(w.noise(0.3), 120, 7000) * w.env(0.3, 0.0003, 0.04)
    boom = w.band(w.noise(1.0), 30, 600) * w.env(1.0, 0.002, 0.18 + 0.02 * v)
    sub = sweep(1.0, 70 + 6 * v, 22, curve=0.5) * w.env(1.0, 0.002, 0.3)
    zings = []
    for i in range(4):
        d = 0.02 + rng.uniform(0, 0.12)
        s = rng.uniform(0.12, 0.25)
        f0 = rng.uniform(4200, 7200)
        zings.append((d, zing(s, f0, f0 * 0.55) * rng.uniform(0.05, 0.12)))
    grit = gravel(2.4, 220, 0.6) * 0.32
    stones = gravel(2.2, 30, 0.9, lo=250, hi=2200) * 0.5
    tail = w.band(w.noise(2.6), 50, 1500) * w.env(2.6, 0.06, 0.6) * 0.32
    out = w.at(sec, (0.0, edge * 1.3), (0.0, crack * 1.8), (0.0, bang * 2.2), (0.0, boom * 2.4), (0.0, sub * 2.6),
               (0.08, grit), (0.25, stones), (0.06, tail), *zings)
    return soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.5, 1.6)


def blast_far():
    sec = 3.2
    thud = w.band(w.noise(0.6), 25, 260) * w.env(0.6, 0.01, 0.2)
    low = w.band(w.noise(sec), 25, 200) * w.env(sec, 0.05, 0.75)
    refl = w.at(sec, *[(d, w.band(w.noise(0.12), 150, 1800) * w.env(0.12, 0.002, 0.04) * a)
                       for d, a in ((0.06, 0.65), (0.15, 0.5), (0.27, 0.38), (0.45, 0.26), (0.7, 0.16), (1.0, 0.1))])
    return w.at(sec, (0.0, thud * 1.4)) + low * 0.9 + refl


def ear_ring():
    sec = 3.4
    x = w.t(sec)
    shape = np.clip(x / 0.04, 0, 1) * np.exp(-np.maximum(x - 0.15, 0) / 1.2)
    wobble = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * x)
    tone = np.sin(2 * np.pi * np.cumsum(3650.0 * wobble) / SR) + 0.4 * np.sin(2 * np.pi * 4120.0 * x)
    hiss = w.band(w.noise(sec), 2500, 7000) * 0.08
    return (tone + hiss) * shape


def dud_bounce(v):
    f = 360 + 50 * v
    tonk = w.partials(0.25, (f, f * 2.6, f * 4.4), (0.05, 0.025, 0.012), (1.0, 0.4, 0.2), detune=0.02)
    knock = w.band(w.noise(0.05), 120, 1600) * w.env(0.05, 0.0005, 0.01)
    return w.at(0.4, (0.0, knock * 1.4), (0.0, tonk * 0.7), (0.11, knock[: int(0.03 * SR)] * 0.4))


def dud_body():
    thud = w.band(w.noise(0.2), 50, 700) * w.env(0.2, 0.001, 0.035)
    slap = w.band(w.noise(0.04), 500, 3500) * w.env(0.04, 0.0003, 0.006)
    return w.at(0.35, (0.0, thud * 1.8), (0.0, slap * 0.6))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"m32_shot_{v}", shot(v))
    w.save("m32_tail_1", tail(), -4)
    w.save("m32_dry_fire_1", dry_fire(), -6)
    w.save("m32_reload_start_1", reload_start(), -5)
    w.save("m32_mag_out_1", cases_out(), -6)
    for v in (1, 2):
        w.save(f"m32_round_in_{v}", round_in(v), -4)
    w.save("m32_slide_release_1", close(), -2)
    w.save("m32_reload_cancel_1", cancel(), -8)
    for v in (1, 2, 3):
        w.save(f"grenade_blast_{v}", blast(v))
    w.save("grenade_blast_far_1", blast_far(), -3)
    w.save("ear_ring_1", ear_ring(), -2)
    for v in (1, 2):
        w.save(f"m32_dud_bounce_{v}", dud_bounce(v), -6)
    w.save("m32_dud_body_1", dud_body(), -3)
    print("m32: wrote launcher and grenade sounds to", out)


if __name__ == "__main__":
    write_all()
