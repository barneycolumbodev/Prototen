#!/usr/bin/env python3
"""Synthesizes the augment sounds (no third-party audio; see CREDITS.md).

RX-9 Reflex Overclock (time slowdown):
- td_in      engage: a servo-like electrical spin-down, a deep pressure
             whoosh and a heavy heartbeat thump as the world drops away.
- td_out     release: the reverse, a rising rush back to speed.
- td_loop    while it's on: slow double heartbeat over a low drone with a
             faint high neural whine. Seamless 4 s loop.
- td_denied  pressed with too little charge: a short dull double blip.

Usage: python3 raw_assets/audio/build_augment_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

SR = w.SR
w.rng = np.random.default_rng(909)


def sweep(sec, f0, f1, curve=2.0):
    x = np.linspace(0, 1, int(sec * SR))
    f = f0 + (f1 - f0) * x ** curve
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def thump(sec=0.35, f=48.0):
    x = w.t(sec)
    body = np.sin(2 * np.pi * f * x * (1 - 0.3 * x / sec)) * np.exp(-x / 0.09)
    click = w.band(w.noise(0.02), 80, 900) * w.env(0.02, 0.0005, 0.006) * 0.4
    return w.at(sec, (0.0, body), (0.0, click))


def heartbeat():
    return w.at(0.6, (0.0, thump(0.35, 50)), (0.22, thump(0.35, 44) * 0.7))


def td_in():
    sec = 1.6
    x = w.t(sec)
    spin = sweep(sec, 1800, 140, 0.6) * np.exp(-x / 0.5) * 0.18
    spin += sweep(sec, 2700, 210, 0.6) * np.exp(-x / 0.4) * 0.08
    whoosh = w.band(w.noise(sec), 60, 1600) * np.clip(x / 0.05, 0, 1) * np.exp(-x / 0.45) * 0.9
    sub = sweep(sec, 70, 32, 1.0) * np.clip(x / 0.04, 0, 1) * np.exp(-x / 0.7) * 0.8
    return w.at(sec, (0.0, spin), (0.0, whoosh), (0.0, sub), (0.1, heartbeat() * 0.9))


def td_out():
    sec = 0.9
    x = w.t(sec)
    rush = w.band(w.noise(sec), 120, 3500) * (x / sec) ** 2 * np.exp(-np.maximum(x - sec * 0.85, 0) / 0.03) * 0.7
    rise = sweep(sec, 160, 1900, 2.5) * (x / sec) ** 1.5 * 0.12
    snap = w.band(w.noise(0.05), 800, 6000) * w.env(0.05, 0.001, 0.01) * 0.5
    return w.at(sec + 0.1, (0.0, rush), (0.0, rise), (sec - 0.02, snap))


def td_loop():
    sec = 4.0
    x = w.t(sec)
    # Drone and whine with whole-number cycles over the loop so it wraps cleanly.
    drone = np.sin(2 * np.pi * 41.0 * x) * 0.25 + np.sin(2 * np.pi * 61.5 * x) * 0.12
    drone *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * x)
    whine = np.sin(2 * np.pi * 3520.0 * x) * (0.012 + 0.006 * np.sin(2 * np.pi * 0.25 * x))
    air = w.band(w.noise(sec), 100, 600) * 0.05
    beats = np.zeros(len(x))
    for start in (0.0, 2.0):
        hb = heartbeat()
        i = int(start * SR)
        beats[i:i + len(hb)] += hb[: len(beats) - i]
    out = drone + whine + air + beats * 0.8
    # Crossfade the ends of the noise so the loop point is seamless.
    n = int(0.05 * SR)
    fade = np.linspace(0, 1, n)
    out[:n] = out[:n] * fade + out[-n:] * (1 - fade)
    return out[: len(out) - n]


def td_denied():
    b1 = sweep(0.07, 420, 380) * w.env(0.07, 0.002, 0.03)
    b2 = sweep(0.07, 330, 300) * w.env(0.07, 0.002, 0.03)
    return w.at(0.22, (0.0, b1), (0.1, b2)) * 0.6


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("td_in_1", td_in(), -3)
    w.save("td_out_1", td_out(), -5)
    w.save("td_denied_1", td_denied(), -8)
    # The loop is written without the save() fades (they'd click at the loop point).
    from scipy.io import wavfile
    x = td_loop()
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (-6 / 20)
    wavfile.write(os.path.join(out, "td_loop_1.wav"), SR, (x * 32767).astype(np.int16))
    print(f"wrote augment sounds to {out}")


if __name__ == "__main__":
    write_all()
