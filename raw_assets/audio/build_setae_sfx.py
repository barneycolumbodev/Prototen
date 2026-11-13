#!/usr/bin/env python3
"""Synthesizes the SX-8 Urticating Setae's sounds (2026-11-13; no third-party audio, see CREDITS.md).

What the hardware would sound like:
- deploy: the arm's servos, then the assemblers: a fizz of tiny crystalline ticks that thickens as 48 fibres
  extrude, over a wet hiss of feedstock; a soft lock as the gill plates seat.
- stow: the fibres drawn back in (the fizz thinning out), servos down, a clack.
- mark: a dry tick, a sub thump and a short high lock tone (the game raises the pitch per mark).
- denied: a dull double click.
- loop: the dead-eye bed (seamless 2 s): a slow heartbeat under a faint, high shimmer of fibres.
- windup: a short indrawn whoosh and the fibres rattling taut.
- throw: the arm's whoosh, a crack as the fibres stiffen, then a swarm of supersonic zips fanning away.
- hit x3: a burst of thin punctures, wet.
- cavity x3: the temporary cavity: a deep wet thump that bursts out, a tearing crackle, a low tail.

Files (Sfx banks): sx8_deploy, sx8_stow, sx8_mark, sx8_denied, sx8_loop (loop), sx8_windup, sx8_throw,
sx8_hit_1..3, sx8_cavity_1..3. Shares helpers with build_weapon_sfx.py and build_gauss_sfx.py.

Usage: python3 raw_assets/audio/build_setae_sfx.py [out_dir]
sx8_loop needs edit/loop_mode=2 in its .import file.
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402
import build_gauss_sfx as g  # noqa: E402

w.rng = np.random.default_rng(1113)
g.rng = w.rng
w.REPLACED = set()
SR = w.SR
rng = w.rng


def swell(sec, power=1.0):
    return np.sin(np.pi * np.linspace(0, 1, int(sec * SR))) ** power


def fizz(sec, d0, d1, lo=3000, hi=14000):
    """Tiny crystalline ticks whose density goes from d0 to d1 (per sample)."""
    n = int(sec * SR)
    dens = np.linspace(d0, d1, n)
    imp = (rng.random(n) < dens) * rng.standard_normal(n)
    return w.band(imp, lo, hi)


def zip_(sec, f0, f1):
    """One needle going past: a thin descending whistle with an air edge."""
    f = g.glide(sec, f0, f1, 0.6)
    tone = w.band(g.sine(f), 1500, 14000) * w.env(sec, 0.003, sec * 0.35)
    air = w.band(w.noise(sec), 4000, 15000) * w.env(sec, 0.001, sec * 0.25)
    return tone * 0.5 + air * 0.6


def deploy():
    sec = 1.0
    return w.at(sec, (0.0, g.servo(0.32, 260, 420, 0.45)), (0.0, w.band(w.noise(0.35), 200, 2200) * swell(0.35, 2) * 0.35),
                (0.18, fizz(0.7, 0.0005, 0.02) * swell(0.7, 0.6) * 0.55),
                (0.2, w.band(w.noise(0.65), 900, 6000) * swell(0.65, 1.2) * 0.22),
                (0.22, g.clack(0.03, 900, 6000, 0.003) * 0.4), (0.26, g.clack(0.03, 900, 6000, 0.003) * 0.35),
                (0.82, g.mix(g.thunk(0.08, 80, 700, 0.02) * 0.5, g.clack(0.03, 1500, 8000, 0.002) * 0.4)))


def stow():
    sec = 0.6
    return w.at(sec, (0.0, fizz(0.35, 0.015, 0.0005) * swell(0.35, 0.5) * 0.45), (0.0, g.servo(0.3, 420, 240, 0.4)),
                (0.34, g.mix(g.thunk(0.09, 70, 600, 0.02) * 0.6, g.clack(0.03, 900, 6000, 0.003) * 0.5)))


def mark():
    sec = 0.32
    tick = g.clack(0.02, 2500, 12000, 0.0015)
    sub = g.sine(g.glide(0.14, 110, 55)) * w.env(0.14, 0.002, 0.04)
    lock = w.band(g.sine(np.full(int(0.16 * SR), 2350.0)) + 0.5 * g.sine(np.full(int(0.16 * SR), 3520.0)), 1500, 9000) * w.env(0.16, 0.002, 0.045)
    return w.at(sec, (0.0, tick * 0.9), (0.0, sub * 0.8), (0.012, lock * 0.35))


def denied():
    sec = 0.18
    return w.at(sec, (0.0, g.clack(0.03, 300, 2500, 0.004) * 0.7), (0.07, g.clack(0.03, 300, 2500, 0.004) * 0.6))


def loop():
    """Seamless 2 s: two heartbeats and a shimmer crossfaded over its own seam."""
    sec = 2.0
    n = int(sec * SR)
    out = np.zeros(n)
    beat = g.mix(g.sine(g.glide(0.18, 70, 42)) * w.env(0.18, 0.004, 0.05), g.thunk(0.12, 30, 180, 0.03) * 0.6)
    beat2 = beat * 0.65
    for off, b in ((0.0, beat), (0.28, beat2), (1.0, beat), (1.28, beat2)):
        i = int(off * SR)
        out[i:i + len(b)] += b[:n - i]
    # A shimmer of fibres: band noise, crossfaded over the seam so it loops.
    pad = int(0.25 * SR)
    sh = w.band(w.noise(sec + 0.25), 5000, 12000) * 0.05
    body, tail = sh[:n].copy(), sh[n:n + pad]
    fade = np.linspace(0, 1, pad)
    body[:pad] = body[:pad] * fade + tail * (1 - fade)
    hum = g.sine(np.full(n, 55.0)) * 0.06  # 110 whole cycles in 2 s
    return out + body + hum


def windup():
    sec = 0.35
    whoosh = w.band(w.noise(0.3), 300, 3000) * swell(0.3, 2.5)
    rattle = fizz(0.25, 0.004, 0.03, 2000, 9000) * swell(0.25, 1.0) * 0.4
    return w.at(sec, (0.0, whoosh * 0.7), (0.06, rattle))


def throw():
    sec = 1.1
    parts = [(0.0, w.band(w.noise(0.32), 250, 4000) * w.env(0.32, 0.03, 0.08) * 0.9),
             (0.0, g.thunk(0.1, 60, 400, 0.03) * 0.5),
             (0.02, w.band(w.noise(0.03), 2500, 16000) * w.env(0.03, 0.0002, 0.005) * 1.1)]
    for k in range(22):
        off = 0.03 + rng.uniform(0.0, 0.28) * (k / 22) ** 0.6
        f0 = rng.uniform(5200, 8800)
        parts.append((off, zip_(rng.uniform(0.18, 0.4), f0, f0 * rng.uniform(0.35, 0.6)) * rng.uniform(0.2, 0.45)))
    return w.at(sec, *parts)


def hit(v):
    sec = 0.25
    parts = []
    for k in range(3 + v):
        off = k * rng.uniform(0.008, 0.02)
        parts.append((off, w.band(w.noise(0.03), 1800, 9000) * w.env(0.03, 0.0003, 0.004) * rng.uniform(0.5, 0.9)))
    parts.append((0.004, w.band(w.noise(0.15), 200, 1600) * w.env(0.15, 0.003, 0.035) * 0.6))
    return w.at(sec, *parts)


def cavity(v):
    sec = 0.9
    boom = g.sine(g.glide(0.4, 95 + 8 * v, 34)) * w.env(0.4, 0.003, 0.12)
    burst = w.band(w.noise(0.35), 180, 2400) * w.env(0.35, 0.002, 0.06 + 0.01 * v)
    tear = g.crackle(0.3, 0.02, 800, 7000, 0.07) * 0.8
    wet = w.band(w.noise(0.5), 300, 1500) * w.env(0.5, 0.01, 0.12) * 0.35
    return g.soft_clip(w.at(sec, (0.0, boom * 1.1), (0.0, burst), (0.01, tear), (0.03, wet), (0.0, g.thunk(0.15, 40, 260, 0.04) * 0.8)), 1.4)


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("sx8_deploy_1", deploy(), -3)
    w.save("sx8_stow_1", stow(), -5)
    w.save("sx8_mark_1", mark(), -3)
    w.save("sx8_denied_1", denied(), -8)
    x = loop()
    x = x - np.mean(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (-10 / 20)
    wavfile.write(os.path.join(out, "sx8_loop_1.wav"), SR, (x * 32767).astype(np.int16))
    w.save("sx8_windup_1", windup(), -4)
    w.save("sx8_throw_1", throw(), -1)
    for v in (1, 2, 3):
        w.save(f"sx8_hit_{v}", hit(v), -4)
        w.save(f"sx8_cavity_{v}", cavity(v), -0.5)
    print("wrote the SX-8's sounds to", out)


if __name__ == "__main__":
    write_all()
