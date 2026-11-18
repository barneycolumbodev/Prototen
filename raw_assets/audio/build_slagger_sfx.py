#!/usr/bin/env python3
"""Synthesizes the SL-9 Slagger's sounds (no third-party audio; see CREDITS.md).

A plasma pistol built out of a welder (owner, 2026-11-18):
- charge: 2.9 s. Capacitors whine up (a rising tone with its harmonics),
  the arc in the emitter crackles harder and harder, a low magnetic hum
  swells under it. Plays from the first moment of the trigger.
- full: 0.9 s, repeated while held at full: the field straining, a beating
  throb of two close tones, sizzle and the odd loud snap.
- shot: the field opens: a hard electric crack, a deep "whumph" of air
  pushed out of the way, and a tearing hiss as the mass leaves.
- tail: the room rings, a short electrical buzz decays.
- fizzle: let go too early: a pop and a falling hiss.
- overload: held too long: sputtering arcs, a bang, steam.
- impact: where a bolt bursts: a wet, roaring splash of fire.
- plasma_flesh: plasma into a man: a violent sizzle (positional).
- mag_out / mag_in / reload_start / dry_fire / slide_release: the power
  cell clunks out, the new one seats with a rising "ready" chirp.

Usage: python3 raw_assets/audio/build_slagger_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
sys.argv = sys.argv[:1]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(9009)
SR = w.SR
rng = w.rng


def tone(f, sec, amp=1.0):
    """A sweep: f is an array of frequencies (one per sample) or a number."""
    f = np.broadcast_to(np.asarray(f, float), (int(sec * SR),))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * amp


def crackle(sec, rate, bright=3000):
    """Random arc snaps, `rate` per second (array or number)."""
    n = int(sec * SR)
    out = np.zeros(n)
    rate = np.broadcast_to(np.asarray(rate, float), (n,))
    i = 0
    while i < n:
        r = max(rate[i], 1.0)
        i += int(rng.exponential(SR / r))
        if i >= n:
            break
        snap = w.band(w.noise(0.01), bright, SR / 2 - 100) * w.env(0.01, 0.0002, 0.0015) * rng.uniform(0.3, 1.0)
        m = min(len(snap), n - i)
        out[i:i + m] += snap[:m]
    return out


def charge():
    sec = 2.9
    tt = w.t(sec)
    k = np.clip(tt / 2.75, 0, 1)
    f = 260 + 1400 * k ** 1.4
    whine = tone(f, sec, 0.35) + tone(f * 2.01, sec, 0.12) + tone(f * 3.03, sec, 0.05)
    hum = tone(55 + 30 * k, sec, 0.5) * (0.3 + 0.7 * k)
    buzz = w.band(w.noise(sec), 90, 500) * (0.15 + 0.5 * k)
    arcs = crackle(sec, 6 + 90 * k ** 1.5) * (0.4 + 0.8 * k)
    fade = np.clip(tt / 0.04, 0, 1)
    return (whine * (0.4 + 0.6 * k) + hum + buzz + arcs) * fade


def full():
    sec = 0.9
    tt = w.t(sec)
    throb = (tone(1660, sec, 0.3) + tone(1673, sec, 0.3)) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt))
    hum = tone(85, sec, 0.6) * (0.8 + 0.2 * np.sin(2 * np.pi * 6 * tt))
    sizzle = w.band(w.noise(sec), 2500, 9000) * 0.35
    arcs = crackle(sec, 120) * 1.0
    big = w.at(sec, (rng.uniform(0.1, 0.7), w.band(w.noise(0.04), 600, 8000) * w.env(0.04, 0.0003, 0.01) * 1.6))
    x = throb + hum + sizzle + arcs + big
    return x * np.hanning(len(x)) ** 0.15


def shot(v):
    sec = 1.0
    crack = w.band(w.noise(0.03), 1500, 12000) * w.env(0.03, 0.0002, 0.004)
    snap = tone(np.linspace(3200, 900, int(0.05 * SR)), 0.05, 1.0) * w.env(0.05, 0.0002, 0.012)
    whumph = w.band(w.noise(0.45), 35, 300) * w.env(0.45, 0.004, 0.09)
    sub = tone(np.linspace(70 + 4 * v, 28, int(0.5 * SR)), 0.5, 1.0) * w.env(0.5, 0.003, 0.14)
    tear = w.band(w.noise(0.5), 700, 7000) * w.env(0.5, 0.003, 0.11)
    zap = tone(np.linspace(1700, 260, int(0.3 * SR)), 0.3, 0.5) * w.env(0.3, 0.001, 0.07)
    x = w.at(sec, (0.0, crack * 1.2), (0.0, snap * 0.7), (0.0, whumph * 1.6), (0.0, sub * 1.4), (0.004, tear * 0.8),
             (0.0, zap * 0.6))
    return np.tanh(x * 1.3)


def tail():
    sec = 1.8
    base = w.band(w.noise(sec), 120, 2400) * w.env(sec, 0.01, 0.4)
    buzz = tone(110, sec, 0.3) * w.env(sec, 0.01, 0.25) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 55 * w.t(sec))))
    return base * 0.6 + w.band(buzz, 80, 3000) * 0.4


def fizzle():
    sec = 0.6
    pop = w.band(w.noise(0.03), 400, 6000) * w.env(0.03, 0.0003, 0.006)
    hiss = w.band(w.noise(sec), 1500, 8000) * w.env(sec, 0.002, 0.15)
    fall = tone(np.linspace(900, 120, int(sec * SR)), sec, 0.4) * w.env(sec, 0.002, 0.12)
    return w.at(sec, (0.0, pop * 1.2), (0.0, hiss * 0.5), (0.0, fall))


def overload():
    sec = 1.6
    sput = crackle(0.5, 160) * 1.2
    bang = w.band(w.noise(0.3), 40, 3000) * w.env(0.3, 0.001, 0.06)
    sub = tone(np.linspace(80, 30, int(0.4 * SR)), 0.4, 1.0) * w.env(0.4, 0.002, 0.1)
    steam = w.band(w.noise(1.2), 2000, 9000) * w.env(1.2, 0.02, 0.4)
    return w.at(sec, (0.0, sput), (0.45, bang * 1.6), (0.45, sub * 1.2), (0.47, steam * 0.6))


def impact(v):
    sec = 1.2
    burst = w.band(w.noise(0.25), 60, 4000) * w.env(0.25, 0.001, 0.05)
    roar = w.band(w.noise(1.0), 150, 2500) * w.env(1.0, 0.01, 0.25)
    sizzle = w.band(w.noise(1.1), 2500, 10000) * w.env(1.1, 0.01, 0.35)
    sub = tone(np.linspace(60 + 5 * v, 30, int(0.35 * SR)), 0.35, 1.0) * w.env(0.35, 0.002, 0.08)
    return np.tanh(w.at(sec, (0.0, burst * 1.5), (0.0, sub * 1.2), (0.01, roar * 0.7), (0.02, sizzle * 0.5)) * 1.4)


def flesh(v):
    sec = 0.9
    hit = w.band(w.noise(0.08), 100, 1800) * w.env(0.08, 0.001, 0.02)
    sizzle = w.band(w.noise(sec), 1800, 9500) * w.env(sec, 0.004, 0.25) * (1 + 0.5 * np.sin(2 * np.pi * (23 + v) * w.t(sec)))
    pop = crackle(sec, 40) * w.env(sec, 0.01, 0.3)
    return w.at(sec, (0.0, hit * 1.2), (0.005, sizzle * 0.8), (0.01, pop * 0.6))


def write_all():
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("slagger_charge_1", charge(), -2)
    w.save("slagger_full_1", full(), -3)
    for v in (1, 2):
        w.save(f"slagger_shot_{v}", shot(v))
    w.save("slagger_tail_1", tail(), -5)
    w.save("slagger_fizzle_1", fizzle(), -4)
    w.save("slagger_overload_1", overload(), -1)
    for v in (1, 2):
        w.save(f"slagger_impact_{v}", impact(v), -1)
        w.save(f"plasma_flesh_{v}", flesh(v), -2)
    clunk = w.click(0.1, (700, 1400, 2600), 0.03, bright=1200)
    w.save("slagger_mag_out_1", w.at(0.3, (0, clunk), (0.02, w.band(w.noise(0.1), 300, 2000) * np.hanning(int(0.1 * SR)) * 0.4)), -4)
    chirp = tone(np.linspace(600, 2400, int(0.18 * SR)), 0.18, 0.4) * w.env(0.18, 0.005, 0.08)
    w.save("slagger_mag_in_1", w.at(0.45, (0, clunk * 1.2), (0.12, chirp)), -2)
    w.save("slagger_slide_release_1", w.at(0.3, (0, chirp)), -6)
    w.save("slagger_dry_fire_1", w.at(0.2, (0, w.click(0.06, (2200, 3600, 5200), 0.01)), (0.01, fizzle()[: int(0.15 * SR)] * 0.3)), -8)
    w.save("slagger_reload_start_1", w.at(0.2, (0, w.band(w.noise(0.15), 250, 2200) * np.hanning(int(0.15 * SR)) * 0.4)), -12)
    print(f"wrote Slagger sounds to {out}")


if __name__ == "__main__":
    write_all()
