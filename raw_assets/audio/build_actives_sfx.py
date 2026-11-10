#!/usr/bin/env python3
"""Synthesizes the sounds of the seven active parts added 2026-11-10 (no third-party audio; see CREDITS.md).

What each piece of hardware would sound like:
- MW-7 whip: a reel paying out (a rising ratchet whirr), a filament too thin to hear until it moves fast: a
  thin airy swish, a dry supersonic crack at the bead, a wet zip when it goes through a body, a glassy scrape
  along concrete.
- NT-5 mesh arm: thousands of fibres sliding over each other (a dry, stretchy creak with a low servo under it),
  a whip-like launch, a heavy wet clamp when it wraps a body, a heave when it throws.
- BW-6 fan shield: seven plates slamming round a hub one after another (a fast metallic ripple and a lock), a
  dull ceramic clank when it stops a round, a crack and falling shards when it breaks.
- SD-3 Shrike: a tube pop and a rising four-rotor whine, a steady rotor buzz (seamless loop), a link chirp, a
  dropping tone when the link goes, an alarm; the warhead: a hard crack, a body of low thump, debris, a tail.
- AD-2 arc projector: a servo and a rising capacitor whine, then the arc: a tearing snap, a 60-cycle buzz, a
  thunder tail.
- KR-5 ram thrusters: a valve crack and a roar of expanding gas that falls away, the thud of a body, a dry
  click when they can't fire.
- TC-4 shroud: a soft descending shimmer as the field closes, a faint high loop while it's up, a rising one as
  it opens, a harsh crackle when it fails.

Files (Sfx banks): mw7_deploy, mw7_stow, mw7_swish x3, mw7_crack x2, mw7_cut x3, mw7_scrape x2; nt5_deploy,
nt5_stow, nt5_shoot, nt5_grab, nt5_throw; bw6_deploy, bw6_stow, bw6_hit x3, bw6_break; sd3_launch, sd3_rotor
(loop), sd3_link, sd3_lost, sd3_alarm; explosion x2, explosion_far; ad2_deploy, ad2_stow, ad2_fire x2;
kr5_fire, kr5_hit, kr5_denied; tc4_on, tc4_off, tc4_loop (loop), tc4_fail.
Shares helpers with build_weapon_sfx.py and build_gauss_sfx.py (imported, not copied).

Usage: python3 raw_assets/audio/build_actives_sfx.py [out_dir]
The two loops need edit/loop_mode=2 in their .import files (tools/check.sh imports them first).
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402
import build_gauss_sfx as g  # noqa: E402

w.rng = np.random.default_rng(1110)
g.rng = w.rng
w.REPLACED = set()
SR = w.SR
rng = w.rng


def swell(sec, power=1.0):
    return np.sin(np.pi * np.linspace(0, 1, int(sec * SR))) ** power


def ratchet(sec, r0, r1, lo=1500, hi=9000):
    """Clicks speeding up or slowing down from r0 to r1 per second."""
    out = np.zeros(int(sec * SR))
    t = 0.0
    while t < sec - 0.01:
        rate = r0 + (r1 - r0) * t / sec
        c = g.clack(0.008, lo, hi, 0.0008) * 0.5
        i = int(t * SR)
        out[i:i + len(c)] += c[:len(out) - i]
        t += 1.0 / rate
    return out


def loop(name, x, peak_db):
    x = x - np.mean(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(w.OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))


# ---------------------------------------------------------------- MW-7 whip
def mw7_deploy():
    sec = 0.75
    return w.at(sec, (0.0, w.band(w.noise(0.3), 200, 2500) * swell(0.3, 2) * 0.3), (0.05, g.servo(0.25, 500, 800, 0.4)),
                (0.1, g.clack(0.03, 800, 6000, 0.003) * 0.5), (0.17, ratchet(0.3, 60, 220) * 0.6), (0.17, g.servo(0.3, 900, 2400, 0.35)),
                (0.47, g.mix(g.thunk(0.08, 100, 1200, 0.015) * 0.7, g.clack(0.03, 1500, 9000, 0.002) * 0.6)),
                (0.5, w.band(g.sine(g.glide(0.22, 5200, 7400)), 3000, 12000) * w.env(0.22, 0.01, 0.07) * 0.12))


def mw7_stow():
    sec = 0.5
    return w.at(sec, (0.0, ratchet(0.3, 240, 80) * 0.5), (0.0, g.servo(0.3, 2200, 800, 0.3)),
                (0.3, g.mix(g.thunk(0.08, 100, 1000, 0.015) * 0.6, g.clack(0.03, 1000, 7000, 0.002) * 0.5)))


def mw7_swish(v):
    sec = 0.28
    f = g.glide(sec, 2600 + 500 * v, 5200 + 700 * v, 0.7)
    air = w.band(w.noise(sec), 2500, 13000) * swell(sec, 2.5)
    tone = w.band(g.sine(f), 2000, 9000) * swell(sec, 3) * 0.12
    return air * 0.8 + tone


def mw7_crack(v):
    sec = 0.3
    n = np.concatenate([np.linspace(1, -1, int(0.0012 * SR)), np.zeros(8)])
    snap = w.band(w.noise(0.03), 2500, 16000) * w.env(0.03, 0.0001, 0.004 + 0.001 * v)
    ring = w.band(w.noise(0.25), 1200, 6000) * w.env(0.25, 0.001, 0.05) * 0.2
    return w.at(sec, (0.0, n * 0.9), (0.0, snap * 1.3), (0.004, ring))


def mw7_cut(v):
    sec = 0.3
    zip_ = w.band(w.noise(0.07), 3000 + 400 * v, 14000) * w.env(0.07, 0.0005, 0.016)
    wet = w.band(w.noise(0.2), 180, 1400) * w.env(0.2, 0.004, 0.05)
    return w.at(sec, (0.0, zip_ * 0.9), (0.006, wet * 0.9), (0.02, g.thunk(0.1, 60, 300, 0.03) * 0.5))


def mw7_scrape(v):
    sec = 0.22
    f = g.glide(sec, 5200 + 900 * v, 7600, 1.0)
    return w.band(w.noise(sec) * (0.6 + 0.4 * g.sine(f)), 3500, 14000) * w.env(sec, 0.004, 0.07)


# ---------------------------------------------------------------- NT-5 mesh arm
def fibre(sec, lo, hi, grain=90.0):
    """Fibres slipping: band noise broken into grains."""
    n = int(sec * SR)
    gate = (np.sin(2 * np.pi * grain * w.t(sec) + rng.uniform(0, 6)) > 0.2).astype(float)
    gate = w.band(gate, 0, 400)[:n]
    return w.band(w.noise(sec), lo, hi) * (0.35 + 0.65 * gate)


def nt5_deploy():
    sec = 0.85
    return w.at(sec, (0.0, w.band(w.noise(0.3), 200, 2500) * swell(0.3, 2) * 0.3), (0.12, g.clack(0.03, 600, 5000, 0.004) * 0.5),
                (0.16, g.clack(0.03, 700, 5000, 0.004) * 0.45), (0.2, g.clack(0.03, 800, 5000, 0.004) * 0.45),
                (0.2, fibre(0.5, 500, 5000) * swell(0.5, 0.8) * 0.6), (0.22, g.servo(0.45, 180, 320, 0.5)),
                (0.66, g.thunk(0.12, 60, 500, 0.03) * 0.6))


def nt5_stow():
    sec = 0.55
    return w.at(sec, (0.0, fibre(0.35, 600, 5500, 120) * swell(0.35, 0.8) * 0.5), (0.0, g.servo(0.35, 320, 170, 0.45)),
                (0.33, g.clack(0.03, 700, 5000, 0.004) * 0.5), (0.38, g.thunk(0.1, 70, 600, 0.025) * 0.6))


def nt5_shoot():
    sec = 0.4
    whip = w.band(w.noise(0.3), 800, 9000) * w.env(0.3, 0.003, 0.07)
    zing = w.band(g.saw(g.glide(0.3, 240, 1300, 0.6)), 200, 5000) * w.env(0.3, 0.005, 0.09) * 0.4
    return w.at(sec, (0.0, whip * 0.8), (0.0, zing), (0.0, g.thunk(0.08, 80, 500, 0.02) * 0.5))


def nt5_grab():
    sec = 0.45
    return w.at(sec, (0.0, g.thunk(0.18, 45, 400, 0.04) * 1.2), (0.0, w.band(w.noise(0.12), 250, 2500) * w.env(0.12, 0.001, 0.03) * 0.8),
                (0.03, fibre(0.3, 400, 3500, 160) * w.env(0.3, 0.01, 0.09) * 0.7), (0.05, g.servo(0.3, 150, 90, 0.5)))


def nt5_throw():
    sec = 0.55
    heave = w.band(w.noise(0.4), 150, 3000) * swell(0.4, 3)
    low = g.sine(g.glide(0.3, 120, 50)) * w.env(0.3, 0.02, 0.1)
    return w.at(sec, (0.0, heave * 0.8), (0.05, low * 0.7), (0.0, fibre(0.25, 600, 5000, 200) * w.env(0.25, 0.005, 0.08) * 0.5),
                (0.22, g.clack(0.03, 500, 4000, 0.004) * 0.4))


# ---------------------------------------------------------------- BW-6 shield
def plate(v, sec=0.2):
    """A slab of ceramic over a steel hub being hit: dull, short, a little ring."""
    body = w.band(w.noise(sec), 300, 3500) * w.env(sec, 0.0003, 0.02)
    ring = w.partials(sec, [1380 + 90 * v, 2210 + 60 * v, 3470], [0.035, 0.025, 0.015], [0.5, 0.35, 0.2])
    return body + ring * 0.5 + g.thunk(sec, 60, 400, 0.03) * 0.8


def bw6_deploy():
    sec = 0.7
    parts = [(0.0, w.band(w.noise(0.3), 200, 2500) * swell(0.3, 2) * 0.3), (0.05, g.servo(0.3, 300, 1400, 0.4))]
    for i in range(7):
        parts.append((0.1 + i * 0.04, plate(i % 3, 0.12) * (0.35 + 0.05 * i)))
    parts.append((0.42, g.mix(g.thunk(0.14, 50, 700, 0.03) * 1.1, g.clack(0.05, 500, 6000, 0.006) * 0.8)))
    return w.at(sec, *parts)


def bw6_stow():
    sec = 0.5
    parts = [(0.0, g.servo(0.3, 1200, 300, 0.35))]
    for i in range(7):
        parts.append((0.03 + i * 0.035, plate(i % 3, 0.1) * 0.3))
    parts.append((0.3, g.thunk(0.12, 60, 700, 0.025) * 0.8))
    return w.at(sec, *parts)


def bw6_hit(v):
    sec = 0.3
    return w.at(sec, (0.0, plate(v, 0.28) * 1.0), (0.0, w.band(w.noise(0.02), 2500, 14000) * w.env(0.02, 0.0001, 0.004) * 0.6))


def bw6_break():
    sec = 0.9
    crack = w.band(w.noise(0.08), 900, 12000) * w.env(0.08, 0.0002, 0.012)
    shards = w.at(0.7, *[(rng.uniform(0.03, 0.55), w.partials(0.12, [rng.uniform(2500, 7000), rng.uniform(4000, 9000)], [0.03, 0.02]) * rng.uniform(0.15, 0.4)) for _ in range(14)])
    return w.at(sec, (0.0, crack * 1.4), (0.0, g.thunk(0.25, 40, 500, 0.06) * 1.3), (0.02, shards), (0.1, g.servo(0.4, 900, 200, 0.35)))


# ---------------------------------------------------------------- SD-3 drone and its warhead
def rotor(sec, f0, f1, level=1.0):
    f = g.glide(sec, f0, f1)
    blades = g.saw(f) + 0.6 * g.saw(f * 1.007) + 0.5 * g.saw(f * 2.0) + 0.4 * g.saw(f * 0.5)
    return (w.band(blades, 120, 7000) * 0.5 + w.band(w.noise(sec), 2000, 9000) * 0.12) * level


def sd3_launch():
    sec = 0.9
    pop = g.mix(g.thunk(0.12, 60, 600, 0.03), w.band(w.noise(0.15), 1500, 9000) * w.env(0.15, 0.001, 0.04) * 0.7)
    spin = rotor(0.75, 90, 420) * np.linspace(0.0, 1.0, int(0.75 * SR)) ** 0.7
    return w.at(sec, (0.0, g.clack(0.03, 800, 6000, 0.003) * 0.6), (0.04, pop * 1.1), (0.1, spin * 0.8),
                (0.3, g.clack(0.02, 1500, 8000, 0.002) * 0.4), (0.34, g.clack(0.02, 1500, 8000, 0.002) * 0.4))


def sd3_rotor():
    """Seamless 1 s loop: whole numbers of cycles of every partial."""
    n = SR
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f, a in ((105, 0.5), (210, 1.0), (420, 0.7), (630, 0.4), (840, 0.25), (1260, 0.12)):
        x += a * np.sign(np.sin(2 * np.pi * f * t)) * 0.3 + a * np.sin(2 * np.pi * (f + 1) * t)
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 7 * t)
    hiss = w.band(w.noise(1.0), 2500, 9000) * 0.25
    hiss[:2000] *= np.linspace(0, 1, 2000)
    hiss[-2000:] *= np.linspace(1, 0, 2000)
    return w.band(x, 90, 6000) + hiss


def sd3_link():
    sec = 0.3
    return w.at(sec, (0.0, g.sine(np.full(int(0.07 * SR), 1900.0)) * w.env(0.07, 0.002, 0.03) * 0.5),
                (0.08, g.sine(np.full(int(0.1 * SR), 2850.0)) * w.env(0.1, 0.002, 0.04) * 0.5),
                (0.0, w.band(w.noise(0.25), 3000, 10000) * w.env(0.25, 0.001, 0.05) * 0.25))


def sd3_lost():
    sec = 0.6
    return w.at(sec, (0.0, w.band(g.saw(g.glide(0.45, 1400, 180, 0.7)), 150, 5000) * w.env(0.45, 0.003, 0.16) * 0.6),
                (0.0, g.crackle(0.5, 0.05, 1500, 12000, 0.15) * 0.7))


def sd3_alarm():
    sec = 0.5
    beep = g.sine(np.full(int(0.1 * SR), 1250.0)) * w.env(0.1, 0.003, 0.06) + 0.3 * g.sine(np.full(int(0.1 * SR), 2500.0)) * w.env(0.1, 0.003, 0.05)
    return w.at(sec, (0.0, beep), (0.16, beep), (0.32, beep))


def explosion(v):
    sec = 2.2
    n = np.concatenate([np.linspace(1, -1, int(0.004 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.08), 800, 14000) * w.env(0.08, 0.0002, 0.012)
    body = w.band(w.noise(0.9), 40, 900) * w.env(0.9, 0.002, 0.16 + 0.03 * v)
    sub = g.sine(g.glide(0.9, 85 + 6 * v, 24, 0.7)) * w.env(0.9, 0.002, 0.26)
    grit = g.crackle(1.2, 0.03, 600, 9000, 0.35) * 0.4
    tail = w.band(w.noise(2.0), 60, 1800) * w.env(2.0, 0.05, 0.55) * 0.35
    out = w.at(sec, (0.0, n * 1.2), (0.0, crack * 1.5), (0.0, body * 2.0), (0.0, sub * 2.2), (0.06, grit), (0.05, tail))
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.4, 1.5)


def explosion_far():
    sec = 2.6
    low = w.band(w.noise(sec), 25, 220) * w.env(sec, 0.04, 0.7)
    refl = w.at(sec, *[(d, w.band(w.noise(0.1), 200, 2200) * w.env(0.1, 0.001, 0.03) * a) for d, a in ((0.05, 0.6), (0.13, 0.45), (0.24, 0.3), (0.4, 0.2), (0.6, 0.12))])
    return low + refl


# ---------------------------------------------------------------- AD-2 arc projector
def ad2_deploy():
    sec = 0.55
    f = g.glide(0.4, 700, 4200, 1.3)
    whine = w.band(g.sine(f) + 0.2 * g.saw(f * 0.5), 400, 10000) * np.linspace(0.15, 1.0, len(f)) * 0.5
    return w.at(sec, (0.0, g.servo(0.28, 400, 1100, 0.5)), (0.26, g.mix(g.thunk(0.08, 90, 900, 0.015) * 0.7, g.clack(0.03, 1200, 8000, 0.003) * 0.6)),
                (0.1, whine), (0.32, g.clack(0.02, 2000, 9000, 0.002) * 0.35), (0.36, g.clack(0.02, 2000, 9000, 0.002) * 0.35))


def ad2_stow():
    sec = 0.4
    return w.at(sec, (0.0, g.servo(0.28, 1000, 380, 0.45)), (0.27, g.thunk(0.1, 80, 800, 0.02) * 0.7))


def ad2_fire(v):
    sec = 1.6
    snap = w.band(w.noise(0.02), 2500, 18000) * w.env(0.02, 0.00005, 0.003)
    tear = g.crackle(0.35, 0.3, 900, 15000, 0.07 + 0.01 * v)
    buzz = w.band(g.saw(np.full(int(0.4 * SR), 120.0)) + g.saw(np.full(int(0.4 * SR), 181.0 + 3 * v)), 100, 7000) * w.env(0.4, 0.001, 0.09)
    boom = w.band(w.noise(0.6), 30, 300) * w.env(0.6, 0.002, 0.14)
    tail = w.band(w.noise(1.4), 70, 1500) * w.env(1.4, 0.03, 0.4) * (0.7 + 0.3 * np.sin(2 * np.pi * 2.3 * w.t(1.4)))
    out = w.at(sec, (0.0, snap * 1.5), (0.0, tear * 1.3), (0.0, buzz * 0.8), (0.0, boom * 1.5), (0.03, tail * 0.5))
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.3, 1.4)


# ---------------------------------------------------------------- KR-5 ram thrusters
def kr5_fire():
    sec = 1.0
    valve = g.mix(g.clack(0.03, 500, 8000, 0.003), g.thunk(0.1, 50, 500, 0.02))
    roar = w.band(w.noise(0.8), 120, 7000) * w.env(0.8, 0.004, 0.16)
    hiss = w.band(w.noise(0.8), 3000, 14000) * w.env(0.8, 0.002, 0.2) * 0.6
    sub = g.sine(g.glide(0.5, 95, 38)) * w.env(0.5, 0.004, 0.14)
    out = w.at(sec, (0.0, valve * 1.2), (0.005, roar * 1.4), (0.005, hiss), (0.0, sub * 1.5))
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.25, 1.3)


def kr5_hit():
    sec = 0.4
    return w.at(sec, (0.0, g.thunk(0.3, 35, 350, 0.06) * 1.6), (0.0, w.band(w.noise(0.1), 200, 3000) * w.env(0.1, 0.0005, 0.02)),
                (0.01, w.band(w.noise(0.2), 100, 900) * w.env(0.2, 0.004, 0.05) * 0.8))


def kr5_denied():
    sec = 0.2
    return w.at(sec, (0.0, g.clack(0.03, 900, 7000, 0.003)), (0.05, w.band(w.noise(0.12), 4000, 12000) * w.env(0.12, 0.002, 0.03) * 0.4))


# ---------------------------------------------------------------- TC-4 shroud
def shimmer(sec, f0, f1):
    f = g.glide(sec, f0, f1, 0.8)
    x = g.sine(f) * 0.5 + g.sine(f * 1.5) * 0.3 + g.sine(f * 2.01) * 0.2
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 23 * w.t(sec)[:len(f)])
    return x * trem * swell(sec, 0.7)[:len(f)] + w.band(w.noise(sec), 5000, 14000)[:len(f)] * swell(sec, 1.5)[:len(f)] * 0.25


def tc4_loop():
    n = SR * 2
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 3000 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.0 * t)) * 0.3 + np.sin(2 * np.pi * 4500 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t + 1)) * 0.2
    x += np.sin(2 * np.pi * 90 * t) * 0.25
    return x


def tc4_fail():
    sec = 0.7
    return w.at(sec, (0.0, g.crackle(0.6, 0.12, 1200, 14000, 0.15)), (0.0, w.band(g.saw(g.glide(0.5, 2600, 300, 0.6)), 200, 8000) * w.env(0.5, 0.002, 0.15) * 0.5),
                (0.0, w.band(w.noise(0.3), 3000, 12000) * w.env(0.3, 0.002, 0.08) * 0.5))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("mw7_deploy_1", mw7_deploy(), -3)
    w.save("mw7_stow_1", mw7_stow(), -5)
    for v in (1, 2, 3):
        w.save(f"mw7_swish_{v}", mw7_swish(v), -6)
        w.save(f"mw7_cut_{v}", mw7_cut(v), -2)
        w.save(f"bw6_hit_{v}", bw6_hit(v), -2)
    for v in (1, 2):
        w.save(f"mw7_crack_{v}", mw7_crack(v), -1)
        w.save(f"mw7_scrape_{v}", mw7_scrape(v), -8)
        w.save(f"explosion_{v}", explosion(v), -0.3)
        w.save(f"ad2_fire_{v}", ad2_fire(v), -0.5)
    w.save("nt5_deploy_1", nt5_deploy(), -3)
    w.save("nt5_stow_1", nt5_stow(), -5)
    w.save("nt5_shoot_1", nt5_shoot(), -2)
    w.save("nt5_grab_1", nt5_grab(), -1)
    w.save("nt5_throw_1", nt5_throw(), -2)
    w.save("bw6_deploy_1", bw6_deploy(), -2)
    w.save("bw6_stow_1", bw6_stow(), -4)
    w.save("bw6_break_1", bw6_break(), -1)
    w.save("sd3_launch_1", sd3_launch(), -2)
    loop("sd3_rotor_1", sd3_rotor(), -9)
    w.save("sd3_link_1", sd3_link(), -6)
    w.save("sd3_lost_1", sd3_lost(), -4)
    w.save("sd3_alarm_1", sd3_alarm(), -5)
    w.save("explosion_far_1", explosion_far(), -3)
    w.save("ad2_deploy_1", ad2_deploy(), -4)
    w.save("ad2_stow_1", ad2_stow(), -6)
    w.save("kr5_fire_1", kr5_fire(), -0.5)
    w.save("kr5_hit_1", kr5_hit(), -1)
    w.save("kr5_denied_1", kr5_denied(), -6)
    w.save("tc4_on_1", shimmer(0.6, 5200, 1700), -5)
    w.save("tc4_off_1", shimmer(0.5, 1700, 4800), -6)
    loop("tc4_loop_1", tc4_loop(), -12)
    w.save("tc4_fail_1", tc4_fail(), -2)
    print("wrote the active parts' sounds to", out)


if __name__ == "__main__":
    write_all()
