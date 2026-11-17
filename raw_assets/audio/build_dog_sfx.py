#!/usr/bin/env python3
"""Synthesizes the attack dog's sounds (no third-party audio; see CREDITS.md).

A source-filter voice: a jittered glottal pulse train (plus breath noise) at a
pitch contour, through three formant resonators sized for a big dog
(German shepherd: lower formants than a small dog). Growls add a 20-30 Hz
flutter (the "rattle" of a growl) and a lot of noise.

  dog_growl_1..3   low rumbling growl while it closes in (about 1.2 s)
  dog_snarl_1..2   the lunge: growl that rips open into a roar (0.6 s)
  dog_bark_1..3    single deep barks
  dog_bite_1..3    teeth clacking shut on flesh
  dog_yelp_1..3    hit: a sharp yelp
  dog_death_1..2   dying whine, trailing off

Usage: python3 raw_assets/audio/build_dog_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
rng = np.random.default_rng(1117)


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def contour(sec, points):
    """Piecewise-linear curve through (time_frac, value) points."""
    x = tt(sec) / sec
    px, py = zip(*points)
    return np.interp(x, px, py)


def pulses(f0, jitter=0.03, shape=0.6):
    """Glottal-ish pulse train following the f0 array (Hz)."""
    f = f0 * (1.0 + jitter * signal.lfilter([1.0], [1.0, -0.995], rng.standard_normal(len(f0))) * 0.05)
    ph = np.cumsum(f) / SR
    frac = ph % 1.0
    # Rosenberg-like pulse: rise then a sharp closure.
    p = np.where(frac < shape, 0.5 * (1 - np.cos(np.pi * frac / shape)), np.cos(np.pi * (frac - shape) / (2 * (1 - shape))))
    return np.diff(p, prepend=0.0) * 40.0


def formants(x, freqs, bws, gains):
    out = np.zeros_like(x)
    for f, bw, g in zip(freqs, bws, gains):
        r = np.exp(-np.pi * bw / SR)
        th = 2 * np.pi * f / SR
        out += g * signal.lfilter([1 - r], [1, -2 * r * np.cos(th), r * r], x)
    return out


def band(x, lo, hi, order=2):
    nyq = SR / 2
    b, a = signal.butter(order, [lo / nyq, min(hi, nyq * 0.98) / nyq], "band")
    return signal.lfilter(b, a, x)


def amp_env(sec, points):
    return contour(sec, points)


def norm(x, peak=0.89):
    x = x - np.mean(x)
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def write(name, x):
    os.makedirs(OUT, exist_ok=True)
    fade = min(len(x), int(0.01 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (norm(x) * 32767).astype(np.int16))
    print("wrote", name, f"{len(x) / SR:.2f}s")


DOG_F = [520, 1300, 2500]  # big-dog formants (Hz)


def voice(sec, f0_pts, env_pts, breath=0.25, f_shift=1.0, bws=(160, 220, 320), gains=(1.0, 0.55, 0.25), jitter=0.04):
    f0 = contour(sec, f0_pts)
    src = pulses(f0, jitter) + breath * rng.standard_normal(len(f0))
    v = formants(src, [f * f_shift for f in DOG_F], bws, gains)
    return v * amp_env(sec, env_pts)


def growl(sec, base, flutter_hz, roughness=0.6):
    x = tt(sec)
    f0 = base * (1 + 0.08 * np.sin(2 * np.pi * 0.7 * x + rng.uniform(0, 6)))
    src = pulses(f0, 0.15) + 0.9 * rng.standard_normal(len(x))
    v = formants(src, [380, 1050, 2300], (240, 300, 400), (1.0, 0.5, 0.2))
    # The rattle: amplitude flutter with uneven depth.
    fl = 0.5 + 0.5 * np.sin(2 * np.pi * flutter_hz * x + 0.6 * np.sin(2 * np.pi * 3.1 * x))
    fl = (1 - roughness) + roughness * fl ** 1.6
    rumble = band(rng.standard_normal(len(x)), 60, 260) * 0.8
    return (v + rumble * fl) * fl


for i in range(3):
    sec = 1.2 + 0.2 * i
    g = growl(sec, 78 + 9 * i, 24 + 3 * i)
    g *= amp_env(sec, [(0, 0), (0.08, 0.8), (0.3, 1.0), (0.6, 0.85), (0.85, 1.0), (1.0, 0)])
    write(f"dog_growl_{i + 1}", g)

for i in range(2):
    sec = 0.62
    g = growl(sec, 95 + 12 * i, 28) * amp_env(sec, [(0, 0.2), (0.35, 0.9), (0.45, 0.4), (1, 0)])
    roar = voice(sec, [(0, 180), (0.4, 320 + 30 * i), (0.6, 260), (1, 170)], [(0, 0), (0.35, 0), (0.42, 1.0), (0.7, 0.7), (1, 0)],
                 breath=0.9, f_shift=0.95, bws=(260, 320, 420))
    write(f"dog_snarl_{i + 1}", g * 0.7 + roar)

for i in range(3):
    sec = 0.32 + 0.04 * i
    start = 430 + 40 * i
    b = voice(sec, [(0, start * 0.7), (0.06, start), (0.35, start * 0.72), (1, start * 0.45)],
              [(0, 0), (0.03, 1.0), (0.25, 0.8), (0.55, 0.25), (1, 0)], breath=0.5, f_shift=0.9 + 0.05 * i)
    burst = band(rng.standard_normal(len(b)), 300, 3500) * amp_env(sec, [(0, 0), (0.02, 0.6), (0.12, 0.1), (1, 0)])
    write(f"dog_bark_{i + 1}", b + burst * 0.4)

for i in range(3):
    sec = 0.22
    x = tt(sec)
    clack = np.zeros_like(x)
    for k, off in enumerate([0.0, 0.012 + 0.004 * i]):
        n0 = int(off * SR)
        n = int(0.025 * SR)
        click = band(rng.standard_normal(n), 1800, 7000) * np.exp(-np.arange(n) / (0.004 * SR))
        clack[n0:n0 + n] += click * (1.0 if k == 0 else 0.5)
    thud = band(rng.standard_normal(len(x)), 90, 600) * np.exp(-x / 0.05)
    wet = band(rng.standard_normal(len(x)), 500, 2500) * np.exp(-x / 0.03) * 0.4
    write(f"dog_bite_{i + 1}", clack * 1.2 + thud * 0.7 + wet)

for i in range(3):
    sec = 0.28 + 0.05 * i
    y = voice(sec, [(0, 700 + 60 * i), (0.15, 1350 + 80 * i), (0.6, 1050), (1, 650)],
              [(0, 0), (0.05, 1.0), (0.5, 0.7), (1, 0)], breath=0.15, f_shift=1.35, bws=(120, 180, 260), jitter=0.02)
    write(f"dog_yelp_{i + 1}", y)

for i in range(2):
    sec = 1.1 + 0.25 * i
    w = voice(sec, [(0, 880), (0.2, 760), (0.6, 520), (1, 360)], [(0, 0), (0.06, 1.0), (0.4, 0.6), (0.75, 0.35), (1, 0)],
              breath=0.45, f_shift=1.2, bws=(140, 200, 300), jitter=0.06)
    # The breath catches: two gaps.
    gate = np.ones_like(w)
    for g0 in (0.38 + 0.05 * i, 0.66):
        a, b = int(g0 * sec * SR), int((g0 + 0.05) * sec * SR)
        gate[a:b] = 0.15
    gate = signal.lfilter([0.02], [1, -0.98], gate) / 1.0
    write(f"dog_death_{i + 1}", w * gate)
