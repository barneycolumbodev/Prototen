#!/usr/bin/env python3
"""Synthesizes the GX-4 Gauss arm sounds (no third-party audio; see CREDITS.md).

Owner (2026-11-07): "a horrific electronic weapon. It's very loud and it's
really powerful." What a coilgun the size of a forearm would make:
- six drive coils firing in sequence in under a millisecond each: a
  machine-gun "tchk" smeared into one hard magnetic slam;
- the capacitor bank dumping: an electrical snap, then a falling electric
  roar (a buzzy, detuned sawtooth gliding down, not a bell: nothing rings);
- the slug at Mach 9: a violent N-wave and crack, and a huge sub-bass boom;
- arcing at the muzzle: a sizzle that trails off;
- the tail: a long rolling thunder down the street.
And the arm itself: servo whine, finger joints clicking, a wrist clunk, the
hiss of the plates, the rails sliding, six coils locking one after another
(timed to the animation in raw_assets/augments/gx4_gauss_arm/build.py), the
fins snapping up, and a rising power-up whine that ends armed.

Files (Sfx bank prefix "gx4_"): shot x3, tail, crack, deploy, stow, hum
(seamless loop), recharge, empty, dry, zap x2.
Shares helpers with build_weapon_sfx.py (imported, not copied).

Usage: python3 raw_assets/audio/build_gauss_sfx.py [out_dir]
"""
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(4040)
w.REPLACED = set()
SR = w.SR
rng = w.rng


def glide(sec, f0, f1, curve=1.0):
    """Frequency path from f0 to f1 (exponential, shaped by curve)."""
    x = np.linspace(0, 1, int(sec * SR)) ** curve
    return f0 * (f1 / f0) ** x


def saw(freq):
    ph = np.cumsum(freq) / SR
    return 2.0 * (ph - np.floor(ph + 0.5))


def sine(freq):
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def crackle(sec, density, lo, hi, decay):
    n = int(sec * SR)
    imp = (rng.random(n) < density) * rng.standard_normal(n)
    return w.band(imp, lo, hi) * w.env(sec, 0.0002, decay)


def mix(*xs):
    """Sum signals of different lengths (padded with silence)."""
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def soft_clip(x, drive=1.6):
    return np.tanh(x * drive) / np.tanh(drive)


def clack(sec=0.05, lo=400, hi=5000, decay=0.006):
    """A dead mechanical lock: filtered noise, no ringing partials."""
    return w.band(w.noise(sec), lo, hi) * w.env(sec, 0.0002, decay)


def thunk(sec=0.12, lo=50, hi=500, decay=0.025):
    return w.band(w.noise(sec), lo, hi) * w.env(sec, 0.0008, decay)


def servo(sec, f0, f1, level=1.0):
    """A small electric motor: buzzy, with a little noise."""
    f = glide(sec, f0, f1)
    tone = w.band(saw(f) + 0.4 * saw(f * 2.01), 300, 6000)
    shape = np.sin(np.pi * np.linspace(0, 1, len(f))) ** 0.6
    return (tone * 0.5 + w.band(w.noise(sec), 1500, 7000) * 0.08) * shape * level


def shot(v):
    sec = 1.4
    # Six coils in sequence: a stutter of slams within ~7 ms.
    coils = w.at(0.03, *[(i * 0.0012, clack(0.012, 300, 9000, 0.0015) * (0.7 + 0.06 * i)) for i in range(6)])
    snap = w.band(w.noise(0.01), 3000, 18000) * w.env(0.01, 0.00005, 0.0012)
    # Falling electric roar: detuned saws gliding down, low-passed as it falls.
    f = glide(0.55, 900 - 40 * v, 70, 0.55)
    roar = saw(f) + saw(f * 1.012) * 0.8 + saw(f * 0.497) * 0.7
    roar = w.band(roar, 40, 5000) * w.env(0.55, 0.001, 0.14)
    roar = soft_clip(roar * 1.4, 2.0)
    # Magnetic slam through the arm (dead, broadband).
    slam = w.band(w.noise(0.12), 80, 2600) * w.env(0.12, 0.0003, 0.02)
    # Slug crack and N-wave.
    nwave = np.concatenate([np.linspace(1, -1, int(0.002 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.04), 1500, 14000) * w.env(0.04, 0.0002, 0.005)
    # Sub boom.
    sub = sine(glide(0.7, 74 + 3 * v, 26, 0.8)) * w.env(0.7, 0.002, 0.2)
    boom = w.band(w.noise(0.9), 22, 180) * w.env(0.9, 0.003, 0.25)
    # Arcing sizzle trailing off.
    sizzle = crackle(0.8, 0.05, 2000, 12000, 0.22)
    hiss = w.band(w.noise(0.6), 3000, 11000) * w.env(0.6, 0.004, 0.12) * 0.25
    out = w.at(sec, (0.0, coils * 1.1), (0.0, snap * 1.3), (0.0, nwave * 1.1), (0.001, crack * 1.4),
               (0.0, slam * 1.6), (0.002, roar * 0.9), (0.0, sub * 1.8), (0.0, boom * 2.0),
               (0.01, sizzle * 0.55), (0.02, hiss))
    return soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.3, 1.4)


def tail():
    sec = 3.2
    low = w.band(w.noise(sec), 25, 140) * w.env(sec, 0.03, 0.9)
    mid = w.band(w.noise(sec), 120, 1600) * w.env(sec, 0.02, 0.55)
    refl = w.at(sec, *[(d, w.band(w.noise(0.07), 300, 3500) * w.env(0.07, 0.0006, 0.02) * g)
                       for d, g in ((0.03, 0.7), (0.07, 0.55), (0.12, 0.45), (0.2, 0.35), (0.31, 0.25), (0.45, 0.18), (0.62, 0.12))])
    # Rolling: slow amplitude wobble like thunder off buildings.
    roll = 0.75 + 0.25 * np.sin(2 * np.pi * 3.1 * w.t(sec)) * np.sin(2 * np.pi * 0.7 * w.t(sec))
    return (low * 1.1 + mid * 0.45) * roll + refl


def crack_layer():
    """A separate near-field electrical crack so the shot cuts through everything."""
    sec = 0.35
    zap = w.band(saw(glide(0.08, 4000, 600, 0.5)), 500, 12000) * w.env(0.08, 0.0002, 0.02)
    arc = crackle(0.3, 0.12, 1500, 14000, 0.06)
    return w.at(sec, (0.0, zap * 0.9), (0.0, arc * 1.2))


def deploy():
    """1.6 s, matched to the animation (frames at 60 fps)."""
    sec = 1.8
    fr = lambda f: (f + 12) / 60.0  # the open hand holds 12 frames first
    parts = []
    # Arm comes up: a cloth/body whoosh and a servo.
    parts.append((0.0, w.band(w.noise(0.35), 200, 2500) * np.sin(np.pi * w.t(0.35) / 0.35) ** 2 * 0.35))
    parts.append((0.0, servo(0.4, 520, 900, 0.5)))
    # Fingers curling: a run of small joint clicks (index first).
    for i in range(4):
        for k in range(3):
            parts.append((fr(4 + i * 2 + k * 5), clack(0.02, 1500, 8000, 0.0012) * 0.35))
    # Wrist turns and locks.
    parts.append((fr(14), servo(0.32, 400, 300, 0.45)))
    parts.append((fr(34), mix(thunk(0.1, 70, 900, 0.02) * 0.9, clack(0.04, 600, 5000, 0.004) * 0.6)))
    # Plates open: pneumatic hiss.
    parts.append((fr(24), w.band(w.noise(0.35), 2500, 11000) * w.env(0.35, 0.01, 0.12) * 0.45))
    parts.append((fr(42), clack(0.05, 300, 4000, 0.006) * 0.7))
    # Jaws split.
    parts.append((fr(30), servo(0.25, 700, 1100, 0.4)))
    parts.append((fr(46), mix(thunk(0.1, 90, 1200, 0.018) * 0.8, clack(0.04, 800, 6000, 0.004) * 0.6)))
    # Rails slide out (a long scrape) and stop.
    parts.append((fr(36), w.band(w.noise(0.4), 900, 6000) * np.linspace(0.2, 1.0, int(0.4 * SR)) * 0.25))
    parts.append((fr(60), mix(clack(0.06, 300, 5000, 0.008) * 0.9, thunk(0.1) * 0.6)))
    # Six coils lock, front to back: hard, rising slightly in pitch.
    for i in range(6):
        f0 = 40 + (5 - i) * 5
        t0 = fr(f0 + 13)
        parts.append((t0, mix(clack(0.05, 350 + 50 * i, 6000, 0.005) * 1.0, thunk(0.08, 60, 700, 0.012) * 0.7)))
    # Muzzle ring and fins snapping up.
    parts.append((fr(70), clack(0.05, 500, 7000, 0.004) * 0.7))
    for k in range(3):
        parts.append((fr(62 + k * 3 + 12), clack(0.03, 1200, 9000, 0.002) * 0.5))
    # Power-up: capacitors charging, a rising whine into an armed chirp.
    rise = sine(glide(0.75, 180, 2400, 1.6)) * np.linspace(0.0, 1.0, int(0.75 * SR)) ** 1.5
    rise = w.band(rise + 0.3 * saw(glide(0.75, 90, 1200, 1.6)), 100, 8000)
    parts.append((fr(50), rise * 0.35))
    chirp = w.band(saw(np.full(int(0.09 * SR), 1760.0)), 800, 9000) * w.env(0.09, 0.002, 0.03)
    parts.append((fr(84), chirp * 0.3))
    parts.append((fr(84), thunk(0.2, 30, 200, 0.06) * 1.2))
    return w.at(sec, *parts)


def stow():
    sec = 1.0
    parts = []
    down = sine(glide(0.5, 2000, 160, 0.7)) * np.linspace(1.0, 0.0, int(0.5 * SR)) ** 1.2
    parts.append((0.0, w.band(down + 0.3 * saw(glide(0.5, 1000, 80, 0.7)), 80, 7000) * 0.3))
    parts.append((0.0, w.band(w.noise(0.3), 2500, 10000) * w.env(0.3, 0.005, 0.1) * 0.35))
    for i in range(6):
        parts.append((0.08 + i * 0.045, clack(0.04, 400 + 40 * i, 6000, 0.004) * 0.7))
    parts.append((0.45, w.band(w.noise(0.25), 900, 5000) * np.linspace(1.0, 0.2, int(0.25 * SR)) * 0.2))
    parts.append((0.62, thunk(0.12, 60, 800, 0.02) * 0.9))
    for k in range(4):
        parts.append((0.66 + k * 0.03, clack(0.02, 1500, 8000, 0.0012) * 0.3))
    parts.append((0.72, servo(0.25, 800, 450, 0.35)))
    return w.at(sec, *parts)


def hum():
    """Seamless 2 s loop: capacitor whine and a low electrical drone."""
    sec = 2.0
    n = int(sec * SR)
    t = np.arange(n) / SR
    drone = np.sin(2 * np.pi * 60 * t) * 0.5 + np.sin(2 * np.pi * 120 * t) * 0.35 + np.sin(2 * np.pi * 180 * t) * 0.15
    whine = np.sin(2 * np.pi * 3150 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.5 * t)) * 0.08
    buzz = w.band(saw(np.full(n, 120.0)), 200, 3000) * 0.12
    x = drone * 0.5 + whine + buzz
    x = x - np.mean(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (-8 / 20)
    from scipy.io import wavfile
    wavfile.write(os.path.join(w.OUT, "gx4_hum_1.wav"), SR, (x * 32767).astype(np.int16))


def recharge():
    sec = 0.55
    f = glide(0.5, 600, 3200, 1.4)
    whine = w.band(sine(f) + 0.25 * saw(f * 0.5), 300, 9000) * np.linspace(0.2, 1.0, len(f)) * np.linspace(1.0, 0.6, len(f))
    return w.at(sec, (0.03, whine * 0.6), (0.5, clack(0.03, 1000, 7000, 0.002) * 0.4))


def empty():
    sec = 0.9
    down = sine(glide(0.7, 1800, 90, 0.6)) * np.linspace(1.0, 0.0, int(0.7 * SR))
    sputter = crackle(0.5, 0.02, 1200, 9000, 0.15)
    return w.at(sec, (0.05, w.band(down, 60, 6000) * 0.5), (0.05, sputter * 0.5), (0.0, clack(0.05, 300, 4000, 0.006) * 0.6))


def dry():
    return w.at(0.25, (0.0, clack(0.03, 900, 7000, 0.003) * 0.8), (0.04, crackle(0.15, 0.02, 2000, 9000, 0.04) * 0.4))


def zap(v):
    sec = 0.6
    arc = crackle(0.55, 0.06 + 0.02 * v, 1500, 13000, 0.2)
    buzz = w.band(saw(np.full(int(0.4 * SR), 100.0 + 20 * v)), 200, 6000) * w.env(0.4, 0.002, 0.12) * 0.3
    return w.at(sec, (0.0, arc), (0.0, buzz))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"gx4_shot_{v}", shot(v), -0.3)
    w.save("gx4_tail_1", tail(), -2)
    w.save("gx4_crack_1", crack_layer(), -3)
    w.save("gx4_deploy_1", deploy(), -2)
    w.save("gx4_stow_1", stow(), -3)
    hum()
    w.save("gx4_recharge_1", recharge(), -8)
    w.save("gx4_empty_1", empty(), -4)
    w.save("gx4_dry_1", dry(), -6)
    for v in (1, 2):
        w.save(f"gx4_zap_{v}", zap(v), -4)
    print("wrote GX-4 sounds to", out)


if __name__ == "__main__":
    write_all()
