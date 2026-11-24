#!/usr/bin/env python3
"""Synthesizes the HV-3 Harvester Hive's sounds (2026-11-24; no third-party audio, see CREDITS.md).

What the hardware would sound like:
- deploy: the wrist servo, six hard little clacks as the iris petals flip open one after another, a hiss of
  the bays venting, and the hive waking (a faint swarm buzz rising).
- release: the swarm pouring out of the palm: a rush of air, a hatch-click flurry, the buzz swelling up and
  away down range.
- swarm (loop, 3D, follows the swarm): hundreds of tiny motors, each its own pitch and wobble, a dense,
  angry, beating drone.
- feed (3D, at the victim): the motors labouring under load (the buzz drops and roughens), cloth and skin
  shredding, a wet, chewing crackle.
- drop: the stripped body going down: a heavy, wet collapse.
- return: the buzz rushing back in and a flurry of tiny docking clicks.
- heal: the hive's reactor dumping repair nanites into the blood: two deep heartbeat thumps, an injection hiss,
  a warm rising swell.
- stow: the iris closing (six clacks the other way), the servo down, a seat.
- denied: a dull double click (nobody in reach).

Files (Sfx banks): hv3_deploy, hv3_release, hv3_swarm (loop), hv3_feed, hv3_drop, hv3_return, hv3_heal,
hv3_stow, hv3_denied. Shares helpers with build_weapon_sfx.py and build_gauss_sfx.py.

Usage: python3 raw_assets/audio/build_hive_sfx.py [out_dir]
hv3_swarm needs edit/loop_mode=2 in its .import file.
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402
import build_gauss_sfx as g  # noqa: E402

w.rng = np.random.default_rng(1124)
g.rng = w.rng
w.REPLACED = set()
SR = w.SR
rng = w.rng


def swell(sec, power=1.0):
    return np.sin(np.pi * np.linspace(0, 1, int(sec * SR))) ** power


def ramp(sec, a, b, power=1.0):
    return a + (b - a) * np.linspace(0, 1, int(sec * SR)) ** power


def swarm(sec, motors=48, f_lo=170.0, f_hi=420.0, pitch=None, rough=0.0):
    """Many tiny motors: each a buzzy pulse at its own pitch with its own wobble and beat. `pitch`: an
    envelope that scales every motor's frequency (load, approach); `rough`: random pitch jitter under load."""
    n = int(sec * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    scale = np.ones(n) if pitch is None else pitch
    for _ in range(motors):
        f = rng.uniform(f_lo, f_hi)
        wob = 1.0 + 0.04 * np.sin(2 * np.pi * rng.uniform(3, 11) * tt + rng.uniform(0, 6.28))
        jit = 1.0 + rough * w.band(rng.standard_normal(n), 2, 30) * 6.0 if rough > 0 else 1.0
        ph = np.cumsum(f * scale * wob * jit) / SR
        # A buzzy pulse: a few odd harmonics, brighter than a sine.
        x = np.sign(np.sin(2 * np.pi * ph)) * 0.35 + np.sin(2 * np.pi * ph) * 0.65
        am = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(0.5, 4.0) * tt + rng.uniform(0, 6.28))
        out += x * am * rng.uniform(0.4, 1.0)
    out = w.band(out / motors, 120, 7000)
    wings = w.band(w.noise(sec), 2500, 9000) * 0.18
    return out + wings


def clicks(sec, count, lo=2500, hi=12000, level=0.5):
    parts = []
    for _ in range(count):
        parts.append((rng.uniform(0.0, sec * 0.9), g.clack(0.012, lo, hi, 0.0012) * rng.uniform(0.3, 1.0) * level))
    return w.at(sec, *parts)


def deploy():
    sec = 0.6
    parts = [(0.0, g.servo(0.28, 300, 520, 0.5)), (0.0, w.band(w.noise(0.25), 300, 2600) * swell(0.25, 2) * 0.25)]
    # Six petals flip and lock, one after another.
    for k in range(6):
        parts.append((0.06 + k * 0.018, g.clack(0.03, 1400 + 120 * k, 9000, 0.0025) * 0.55))
    parts.append((0.2, g.mix(g.thunk(0.06, 90, 900, 0.015) * 0.5, g.clack(0.02, 3000, 12000, 0.0015) * 0.35)))
    parts.append((0.12, w.band(w.noise(0.35), 3000, 11000) * swell(0.35, 1.5) * 0.22))
    parts.append((0.25, swarm(0.35, 24) * ramp(0.35, 0.0, 0.35, 2.0)))
    return w.at(sec, *parts)


def release():
    sec = 1.0
    rush = w.band(w.noise(0.45), 400, 6000) * w.env(0.45, 0.01, 0.14) * 0.7
    buzz = swarm(0.9, 64, pitch=ramp(0.9, 1.25, 0.85, 0.7)) * w.env(0.9, 0.03, 0.35) * 1.1
    pop = g.thunk(0.08, 60, 500, 0.02) * 0.45
    return g.soft_clip(w.at(sec, (0.0, rush), (0.0, pop), (0.0, clicks(0.18, 26, level=0.45)), (0.02, buzz)), 1.3)


def swarm_loop():
    """Seamless 2 s: the buzz bed, crossfaded over its own seam."""
    sec = 2.0
    n = int(sec * SR)
    pad = int(0.3 * SR)
    x = swarm(sec + 0.31, 72)
    body, tail = x[:n].copy(), x[n:n + pad]
    fade = np.linspace(0, 1, pad)
    body[:pad] = body[:pad] * fade + tail * (1 - fade)
    return body


def feed():
    sec = 1.0
    # The motors under load: lower and rougher.
    load = swarm(0.95, 56, pitch=ramp(0.95, 0.9, 0.7, 0.8), rough=0.02) * w.env(0.95, 0.02, 0.3) * 0.8
    chew = g.crackle(0.9, 0.035, 500, 6000, 0.05) * swell(0.9, 0.4) * 0.9
    # Cloth and skin tearing: band noise chopped fast.
    n = int(0.8 * SR)
    chop = (np.sin(2 * np.pi * np.cumsum(rng.uniform(18, 34, n)) / SR) > 0.3).astype(float)
    tear = w.band(w.noise(0.8), 900, 5000) * chop * swell(0.8, 0.6) * 0.45
    wet = w.band(w.noise(0.9), 150, 1100) * swell(0.9, 0.8) * 0.4
    return g.soft_clip(w.at(sec, (0.0, load), (0.04, chew), (0.06, tear), (0.0, wet)), 1.4)


def drop():
    sec = 0.7
    thud = g.thunk(0.2, 40, 320, 0.06) * 1.0
    slap = w.band(w.noise(0.25), 250, 2200) * w.env(0.25, 0.002, 0.05) * 0.7
    wet = g.crackle(0.3, 0.02, 600, 4000, 0.04) * 0.4
    return g.soft_clip(w.at(sec, (0.0, thud), (0.0, slap), (0.03, wet), (0.12, g.thunk(0.15, 50, 400, 0.04) * 0.4)), 1.2)


def return_():
    sec = 0.8
    buzz = swarm(0.55, 64, pitch=ramp(0.55, 0.8, 1.3, 1.5)) * ramp(0.55, 0.2, 1.0, 2.0) * 1.0
    rush = w.band(w.noise(0.5), 500, 7000) * ramp(0.5, 0.0, 0.5, 3.0)
    dock = clicks(0.3, 40, 2200, 11000, 0.5)
    seat = g.mix(g.thunk(0.06, 90, 700, 0.015) * 0.4, g.clack(0.02, 2000, 9000, 0.0015) * 0.3)
    return g.soft_clip(w.at(sec, (0.0, buzz), (0.05, rush), (0.42, dock), (0.68, seat)), 1.3)


def heal():
    sec = 1.1
    beat = g.mix(g.sine(g.glide(0.22, 78, 40)) * w.env(0.22, 0.004, 0.07), g.thunk(0.14, 30, 200, 0.035) * 0.7)
    hiss = w.band(w.noise(0.4), 4000, 12000) * w.env(0.4, 0.005, 0.12) * 0.3
    warm = g.sine(g.glide(0.9, 110, 220, 0.7)) * swell(0.9, 1.5) * 0.25 + g.sine(g.glide(0.9, 165, 330, 0.7)) * swell(0.9, 1.5) * 0.12
    return w.at(sec, (0.0, beat * 1.2), (0.26, beat * 0.85), (0.02, hiss), (0.08, warm))


def stow():
    sec = 0.5
    parts = [(0.0, g.servo(0.3, 500, 280, 0.4))]
    for k in range(6):
        parts.append((0.08 + k * 0.016, g.clack(0.025, 1800 - 100 * k, 9000, 0.002) * 0.45))
    parts.append((0.3, g.mix(g.thunk(0.08, 70, 600, 0.02) * 0.55, g.clack(0.03, 900, 6000, 0.003) * 0.4)))
    return w.at(sec, *parts)


def denied():
    sec = 0.18
    return w.at(sec, (0.0, g.clack(0.03, 300, 2500, 0.004) * 0.7), (0.07, g.clack(0.03, 300, 2500, 0.004) * 0.6))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("hv3_deploy_1", deploy(), -3)
    w.save("hv3_release_1", release(), -1)
    x = swarm_loop()
    x = x - np.mean(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (-4 / 20)
    wavfile.write(os.path.join(out, "hv3_swarm_1.wav"), SR, (x * 32767).astype(np.int16))
    w.save("hv3_feed_1", feed(), -0.5)
    w.save("hv3_drop_1", drop(), -2)
    w.save("hv3_return_1", return_(), -1.5)
    w.save("hv3_heal_1", heal(), -1)
    w.save("hv3_stow_1", stow(), -5)
    w.save("hv3_denied_1", denied(), -8)
    print("wrote the HV-3's sounds to", out)


if __name__ == "__main__":
    write_all()
