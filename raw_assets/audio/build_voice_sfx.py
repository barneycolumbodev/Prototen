#!/usr/bin/env python3
"""Synthesizes the enemies' dying voices (no third-party audio; see CREDITS.md).

Source-filter voice model: a glottal pulse train (spectral tilt, jitter,
shimmer, tremor, roughness from sub-harmonics) plus breath noise that pulses
with the glottis, through five formant resonators whose frequencies glide
between vowels. No words, just effort and pain:

- death_scream_N  torso/limb kill: a hard "AAH" that breaks and falls away.
- death_choke_N   neck/chest: a cut-off "ugh", then gurgling and a wet cough.
- death_groan_N   slow kill (bleeding out, crawling, burning out): a long moan.
- death_breath_N  head shot: just the air leaving, a short "hh-k".

Usage: python3 raw_assets/audio/build_voice_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

SR = w.SR
rng = np.random.default_rng(1971)
w.rng = rng

# Formants (Hz) and bandwidths for an adult male voice.
VOWELS = {
    "a": ([730, 1090, 2440, 3400, 4300], [90, 110, 160, 250, 300]),
    "ah": ([680, 1220, 2600, 3500, 4300], [100, 120, 170, 250, 300]),
    "uh": ([570, 1050, 2400, 3350, 4250], [90, 110, 150, 250, 300]),
    "u": ([330, 870, 2250, 3300, 4200], [80, 100, 140, 250, 300]),
    "o": ([480, 800, 2500, 3350, 4250], [90, 100, 150, 250, 300]),
    "e": ([530, 1840, 2480, 3400, 4300], [80, 110, 160, 250, 300]),
}
AMPS = [1.0, 0.55, 0.22, 0.12, 0.06]


def smooth_noise(n, rate_hz, amount):
    """Low-frequency random wobble, unit-ish variance."""
    k = max(2, int(n * rate_hz / SR) + 2)
    pts = rng.standard_normal(k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts) * amount


def glottal(f0, effort, rough=0.0):
    """Pulse train following the per-sample f0 curve. Returns (source, phase)."""
    n = len(f0)
    f = f0 * (1.0 + smooth_noise(n, 30, 0.012) + 0.01 * np.sin(2 * np.pi * 5.5 * np.arange(n) / SR))
    f *= 1.0 + smooth_noise(n, 400, 0.008)  # jitter
    phase = np.cumsum(f) / SR
    ph = phase % 1.0
    # Rosenberg-style pulse: open phase rises/falls, closed phase flat. Pressed
    # (high effort) voices have a shorter open phase: more high harmonics.
    oq = np.clip(0.65 - 0.25 * effort, 0.3, 0.7)
    tp = oq * 0.62
    pulse = np.where(ph < tp, 0.5 * (1 - np.cos(np.pi * ph / tp)),
                     np.where(ph < oq, np.cos(0.5 * np.pi * (ph - tp) / (oq - tp)), 0.0))
    src = np.diff(pulse, prepend=0.0) * SR / np.maximum(f, 40) * 0.05  # flow derivative
    if rough > 0:
        sub = np.sin(np.pi * phase) ** 2  # period-doubling (vocal fry, strain)
        src *= 1.0 - rough * 0.6 * sub
    src *= 1.0 + smooth_noise(n, 200, 0.12)  # shimmer
    return src, ph


def formant_filter(x, vowel_curve):
    """Time-varying resonator bank. vowel_curve: list of (time_sec, vowel)."""
    n = len(x)
    times = np.array([tc for tc, _ in vowel_curve])
    fs = np.array([VOWELS[v][0] for _, v in vowel_curve], dtype=float)
    bws = np.array([VOWELS[v][1] for _, v in vowel_curve], dtype=float)
    ts = np.arange(n) / SR
    out = np.zeros(n)
    hop = 256
    for k in range(5):
        fk = np.interp(ts, times, fs[:, k])
        bk = np.interp(ts, times, bws[:, k])
        y = np.zeros(n)
        zi = np.zeros(2)
        for s in range(0, n, hop):
            e = min(n, s + hop)
            fc = fk[s]
            r = np.exp(-np.pi * bk[s] / SR)
            a = [1.0, -2 * r * np.cos(2 * np.pi * fc / SR), r * r]
            b = [1.0 - r]
            y[s:e], zi = signal.lfilter(b, a, x[s:e], zi=zi)
        out += y * AMPS[k]
    return out


def voice(sec, f0_pts, amp_pts, vowels, effort=0.7, breath=0.3, rough=0.0, rough_pts=None):
    """f0_pts/amp_pts: [(t, value)], interpolated over the sound."""
    n = int(sec * SR)
    ts = np.arange(n) / SR
    f0 = np.interp(ts, [p[0] for p in f0_pts], [p[1] for p in f0_pts])
    amp = np.interp(ts, [p[0] for p in amp_pts], [p[1] for p in amp_pts])
    src, ph = glottal(f0, effort, rough)
    if rough_pts:
        rgh = np.interp(ts, [p[0] for p in rough_pts], [p[1] for p in rough_pts])
        src *= 1.0 - 0.5 * rgh * (rng.random(n) < 0.02).astype(float).cumsum() % 2
    asp = w.band(rng.standard_normal(n), 400, 6000) * (0.35 + 0.65 * (ph < 0.5))
    excit = src * (1 - breath) + asp * breath * 0.6
    v = formant_filter(excit, vowels)
    # Effort lifts the upper formants (a strained voice is brighter): blend in
    # the first difference (+6 dB/oct) in proportion to effort.
    v = v + np.diff(v, prepend=0.0) * effort * 6.0
    v = v / (np.max(np.abs(v)) + 1e-9)
    return v * amp


def gurgle(sec, density=28, wet=1.0):
    """Liquid in the airway: short resonant bubbles at random pitches."""
    n = int(sec * SR)
    out = np.zeros(n)
    count = int(sec * density)
    for _ in range(count):
        st = rng.integers(0, max(1, n - int(0.05 * SR)))
        dur = rng.uniform(0.015, 0.045)
        m = int(dur * SR)
        tt = np.arange(m) / SR
        f = rng.uniform(250, 900) * (1 + 1.8 * tt / dur)  # bubbles rise in pitch
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (dur * 0.35))
        out[st:st + m] += b * rng.uniform(0.3, 1.0)
    rumble = w.band(rng.standard_normal(n), 80, 700) * 0.4
    shape = np.sin(np.pi * np.arange(n) / n) ** 0.5
    return (out * wet + rumble) * shape


def cough(strength=1.0):
    sec = 0.28
    burst = w.band(w.noise(sec), 300, 3500) * w.env(sec, 0.003, 0.05)
    v = voice(sec, [(0, 150), (sec, 110)], [(0, 0), (0.01, 1), (0.08, 0.5), (sec, 0)], [(0, "uh"), (sec, "uh")],
              effort=0.9, breath=0.6, rough=0.6)
    return (burst * 0.7 + v * 0.6 + gurgle(sec, 50) * 0.35) * strength


def reverb_tail(x, amount=0.12, decay=0.25):
    """A touch of street: short noise-burst convolution, mostly dry."""
    m = int(decay * SR)
    ir = rng.standard_normal(m) * np.exp(-np.arange(m) / (decay * SR / 5))
    ir = w.band(ir, 200, 5000)
    wet = signal.fftconvolve(x, ir)
    out = np.zeros(len(wet))
    out[: len(x)] += x
    return out + wet / (np.max(np.abs(wet)) + 1e-9) * amount * np.max(np.abs(x))


def scream(v):
    f_peak = [205, 240, 180][v - 1]
    sec = [0.95, 1.1, 0.8][v - 1]
    vow = [[(0, "ah"), (0.15, "a"), (sec * 0.7, "ah"), (sec, "uh")],
           [(0, "e"), (0.1, "a"), (sec * 0.6, "ah"), (sec, "o")],
           [(0, "uh"), (0.08, "a"), (sec, "uh")]][v - 1]
    f0 = [(0, f_peak * 0.75), (0.06, f_peak * 1.05), (0.25, f_peak), (sec * 0.65, f_peak * 0.8), (sec, f_peak * 0.45)]
    amp = [(0, 0), (0.03, 1.0), (0.3, 0.9), (sec * 0.7, 0.55), (sec, 0.0)]
    body = voice(sec, f0, amp, vow, effort=0.95, breath=0.25, rough=0.45)
    gasp = w.band(w.noise(0.12), 600, 5000) * np.sin(np.pi * w.t(0.12) / 0.12) ** 2 * 0.25
    out = w.at(sec + 0.2, (0.0, gasp), (0.08, body))
    return reverb_tail(out)


def choke(v):
    sec = 1.25
    grunt_sec = 0.32
    g = voice(grunt_sec, [(0, 160 + 10 * v), (grunt_sec, 110)], [(0, 0), (0.015, 1), (0.12, 0.8), (grunt_sec, 0)],
              [(0, "uh"), (grunt_sec, "u")], effort=0.9, breath=0.35, rough=0.7)
    gl = gurgle(0.9, density=34 + 6 * v)
    gv = voice(0.9, [(0, 105), (0.9, 80)], [(0, 0.0), (0.2, 0.35), (0.9, 0.0)], [(0, "o"), (0.9, "u")],
               effort=0.5, breath=0.6, rough=0.9)
    parts = [(0.0, g), (0.22, gl * 0.55 + gv * 0.4)]
    if v != 2:
        parts.append((0.85, cough(0.7)))
    return reverb_tail(w.at(sec + 0.1, *parts), amount=0.08)


def groan(v):
    sec = [1.6, 1.9][v - 1]
    f0 = [(0, 120), (0.3, 132), (sec * 0.6, 105), (sec, 70)]
    amp = [(0, 0), (0.15, 0.8), (sec * 0.5, 0.65), (sec * 0.85, 0.3), (sec, 0)]
    vow = [(0, "uh"), (sec * 0.4, "o"), (sec, "u")] if v == 1 else [(0, "ah"), (sec * 0.5, "uh"), (sec, "u")]
    body = voice(sec, f0, amp, vow, effort=0.5, breath=0.45, rough=0.5)
    exhale = w.band(w.noise(0.5), 300, 3000) * np.sin(np.pi * w.t(0.5) / 0.5) ** 2 * 0.18
    return reverb_tail(w.at(sec + 0.5, (0.0, body), (sec - 0.1, exhale)), amount=0.1)


def breath(v):
    sec = 0.35
    air = w.band(w.noise(sec), 500, 4500) * w.env(sec, 0.004, 0.08) * 0.5
    k = voice(0.09, [(0, 140 + 15 * v), (0.09, 100)], [(0, 0), (0.01, 0.6), (0.09, 0)], [(0, "uh"), (0.09, "uh")],
              effort=0.9, breath=0.5, rough=0.8)
    return w.at(sec + 0.05, (0.0, k * 0.8), (0.02, air))


def finish(x):
    """High-pass at 80 Hz: removes the glottal source's DC and rumble."""
    sos = signal.butter(2, 80, "highpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"death_scream_{v}", finish(scream(v)), -3)
        w.save(f"death_breath_{v}", finish(breath(v)), -8)
    for v in (1, 2):
        w.save(f"death_choke_{v}", finish(choke(v)), -4)
        w.save(f"death_groan_{v}", finish(groan(v)), -5)
    print(f"wrote voice sounds to {out}")


if __name__ == "__main__":
    write_all()
