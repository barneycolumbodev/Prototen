#!/usr/bin/env python3
"""Synthesizes GRAFT's adaptive combat score (no third-party audio; see CREDITS.md).

Three stems that loop together (MusicDirector plays them as one
AudioStreamSynchronized, so they never drift), all D minor with a
Phrygian flat second, 120 BPM, 32 bars = 64 s, sharing one chord plan so
any mix of them is in key:

- music_tension: dark industrial sub-bass drone, a slow sub pulse
  (heartbeat on 1 and the and of 2), distant bowed-metal drone and far-off
  clanks in a big reverb, a muted machine tick. Wave breathers, sneaking.
- music_combat: syncopated industrial percussion (distorted kick,
  clanging snare, anvil hits, sixteenth hats) and a distorted saw bass
  riff riding the kick. Fades in when men engage.
- music_boss: low brass braams (seven detuned saws through a swelling
  filter, then driven), heavy toms in a driving pattern, sheet-metal
  crashes on the phrase. Boss fights.

Stingers (1-2 s, in key, so they land on top of any layer):
  sting_wave_start, sting_wave_cleared, sting_supply_drop,
  sting_mk3, sting_boss_kneel, sting_run_over.

Loops are rendered circularly (reverb tails fold back onto the start) so
they wrap without a seam. Output: OGG Vorbis (ffmpeg, libvorbis) into
assets/audio/music/. Total stays under 6 MB (CLAUDE.md §8 RAM budget:
Vorbis stays compressed in memory and decodes as it plays).

Usage: python3 raw_assets/audio/build_music.py [out_dir]  (default assets/audio/music)
       needs numpy, scipy and ffmpeg.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "assets", "audio", "music")
SR = 44100
BPM = 120.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
STEP = BEAT / 4
BARS = 32
LOOP = BARS * BAR
N = int(round(LOOP * SR))
rng = np.random.default_rng(2611)

D2 = 73.416
# Chord plan, semitones from D, one per bar (A, B, A', C sections).
ROOTS = ([0, 0, 0, 1, 0, 0, -4, -5]
         + [-4, -4, -7, -7, -4, -4, -5, -5]
         + [0, 0, 0, 1, 0, 0, -4, -5]
         + [3, 3, 1, 1, 0, 0, 1, -5])


def hz(semi, base=D2):
    return base * 2 ** (semi / 12)


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def lp(x, f, order=2):
    b, a = signal.butter(order, min(f / (SR / 2), 0.99), "low")
    return signal.lfilter(b, a, x)


def hp(x, f, order=2):
    b, a = signal.butter(order, f / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], "band")
    return signal.lfilter(b, a, x)


def saw(freq, sec, phase=None):
    x = tt(sec)
    ph = rng.uniform(0, 1) if phase is None else phase
    return 2.0 * ((freq * x + ph) % 1.0) - 1.0


def drive(x, k):
    return np.tanh(x * k) / np.tanh(k)


def place(buf, t0, x, pan=0.0, gain=1.0, wrap=True):
    """Adds mono `x` at time t0 into stereo `buf` (2, n), panned -1..1. Wraps for loops."""
    i = int(round(t0 * SR))
    n = buf.shape[1]
    gl = np.cos((pan + 1) * np.pi / 4) * gain
    gr = np.sin((pan + 1) * np.pi / 4) * gain
    idx = (np.arange(len(x)) + i)
    if wrap:
        idx %= n
        np.add.at(buf[0], idx, x * gl)
        np.add.at(buf[1], idx, x * gr)
    else:
        m = idx < n
        buf[0, idx[m]] += x[m] * gl
        buf[1, idx[m]] += x[m] * gr


def ir(sec, decay, lo=200.0, hi=6000.0, seed=0):
    r = np.random.default_rng(seed)
    x = tt(sec)
    out = []
    for ch in range(2):
        nz = r.standard_normal(len(x)) * np.exp(-x / decay)
        nz = bp(nz, lo, hi)
        nz[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
        out.append(nz / np.sqrt(np.sum(nz ** 2)))
    return out


def reverb(buf, sec=2.4, decay=0.7, mix=0.35, lo=200.0, hi=6000.0, seed=5, circular=True):
    """Stereo convolution reverb; circular folds the tail back onto the start."""
    imp = ir(sec, decay, lo, hi, seed)
    n = buf.shape[1]
    wet = np.zeros_like(buf)
    for ch in range(2):
        mono = 0.5 * (buf[0] + buf[1]) * 0.6 + buf[ch] * 0.4
        y = signal.fftconvolve(mono, imp[ch])
        if circular:
            full = np.zeros(n)
            for k in range(0, len(y), n):
                seg = y[k:k + n]
                full[: len(seg)] += seg
            wet[ch] = full
        else:
            wet[ch] = y[:n]
    return buf * (1 - mix) + wet * mix * 2.2


def env_ad(sec, a, d):
    x = tt(sec)
    return np.clip(x / max(a, 1e-5), 0, 1) * np.exp(-np.maximum(x - a, 0) / d)


# ---------------------------------------------------------------- instruments

def kick(sec=0.45, punch=1.0, k=3.0):
    x = tt(sec)
    f = 45 + 120 * np.exp(-x / 0.03)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.18)
    click = hp(rng.standard_normal(len(x)), 2500) * np.exp(-x / 0.004) * 0.4
    return drive(body * punch + click, k)


def snare(sec=0.4):
    x = tt(sec)
    body = np.sin(2 * np.pi * 190 * x) * np.exp(-x / 0.05)
    nz = bp(rng.standard_normal(len(x)), 900, 8000) * np.exp(-x / 0.09)
    metal = sum(np.sin(2 * np.pi * f * x + rng.uniform(0, 6)) * np.exp(-x / d)
                for f, d in ((587, 0.12), (1215, 0.09), (1873, 0.06), (2691, 0.05)))
    return drive(body * 0.8 + nz * 0.9 + metal * 0.22, 2.2)


def anvil(f0=880.0, sec=0.6, damp=0.12):
    """Struck steel: inharmonic partials (free bar modes) with a noisy strike."""
    x = tt(sec)
    out = np.zeros_like(x)
    for r, a, d in ((1.0, 1.0, 1.0), (2.756, 0.6, 0.6), (5.404, 0.35, 0.4), (8.933, 0.2, 0.25)):
        out += a * np.sin(2 * np.pi * f0 * r * x + rng.uniform(0, 6)) * np.exp(-x / (damp * d))
    strike = hp(rng.standard_normal(len(x)), 1500) * np.exp(-x / 0.006)
    return out * 0.6 + strike * 0.5


def hat(sec=0.08, open_=False):
    x = tt(sec)
    nz = hp(rng.standard_normal(len(x)), 7000)
    return nz * np.exp(-x / (0.09 if open_ else 0.018))


def tom(f0=82.0, sec=0.9):
    x = tt(sec)
    f = f0 * (1 + 0.6 * np.exp(-x / 0.04))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.35)
    skin = lp(rng.standard_normal(len(x)), 1200) * np.exp(-x / 0.03)
    return drive(body + skin * 0.5, 1.8)


def sheet(sec=3.0, f0=110.0):
    """A big steel sheet (thunder sheet / gong-ish crash)."""
    x = tt(sec)
    nz = rng.standard_normal(len(x))
    ring = sum(np.sin(2 * np.pi * f0 * r * x + rng.uniform(0, 6)) * np.exp(-x / d) * a
               for r, a, d in ((1, 0.5, 1.6), (1.47, 0.4, 1.2), (2.09, 0.35, 0.9), (2.83, 0.3, 0.7),
                               (3.61, 0.25, 0.5), (4.95, 0.2, 0.4)))
    wash = bp(nz, 400, 7000) * np.exp(-x / 0.7) * 0.5
    return ring * 0.6 + wash + hp(nz, 2000) * np.exp(-x / 0.02) * 0.6


def q(f):
    """`f` moved to the nearest whole number of cycles per loop (1/64 Hz steps)."""
    return max(round(f * LOOP), 1) / LOOP


def circ(fn, x, *args):
    """Filters a loop as if it repeated forever (no start-up transient at the seam)."""
    k = min(SR, x.shape[-1])
    y = fn(np.concatenate([x[..., -k:], x], axis=-1), *args)
    return y[..., k:]


def bowed_metal(f0, sec, seed=0):
    """A long bowed-steel drone: inharmonic partials with slow beating swells.
    Periodic over the loop (every rate is quantized with q)."""
    r = np.random.default_rng(seed)
    x = tt(sec)
    out = np.zeros_like(x)
    for ratio, a in ((1.0, 1.0), (2.76, 0.5), (4.1, 0.25), (5.4, 0.22), (7.1, 0.12)):
        f = f0 * ratio * (1 + r.uniform(-0.002, 0.002))
        lfo = 0.55 + 0.45 * np.sin(2 * np.pi * q(r.uniform(0.03, 0.11)) * x + r.uniform(0, 6))
        out += a * np.sin(2 * np.pi * q(f) * x + r.uniform(0, 6)) * lfo
        out += a * 0.5 * np.sin(2 * np.pi * q(f * 1.003) * x + r.uniform(0, 6)) * lfo
    grit = circ(bp, r.standard_normal(len(x)), f0 * 2, f0 * 6) * 0.08
    return out + grit


def brass(semis, sec, swell=0.25, bright=1400.0, base=D2):
    """Braam: a stack of detuned saws per note, a filter that opens and closes, driven."""
    x = tt(sec)
    tone = np.zeros_like(x)
    for s in semis:
        f = hz(s, base)
        for d in (-0.012, -0.006, -0.002, 0.0, 0.003, 0.007, 0.011):
            tone += saw(f * (1 + d), sec)
    tone /= 7 * len(semis)
    a = np.clip(x / swell, 0, 1) ** 1.5
    rel = np.clip((sec - x) / 0.35, 0, 1)
    amp = a * rel * (0.75 + 0.25 * np.exp(-x / 0.6))
    dark = lp(tone, 260)
    br = lp(tone, bright)
    openness = np.clip(x / (swell * 1.4), 0, 1) * np.exp(-np.maximum(x - swell, 0) / 1.0)
    out = dark + (br - dark) * openness
    return drive(out * amp * 2.2, 2.0)


def bass_note(semi, sec, accent=1.0):
    f = hz(semi)
    x = tt(sec)
    tone = saw(f, sec, 0.0) + 0.6 * saw(f * 1.005, sec, 0.3) + 0.5 * np.sin(2 * np.pi * f / 2 * x)
    e = np.clip(x / 0.004, 0, 1) * np.exp(-x / (0.16 + 0.1 * accent))
    e *= np.clip((sec - x) / 0.01, 0, 1)
    fe = np.exp(-x / 0.06)
    dark = lp(tone, 180)
    bright = lp(tone, 1800)
    return drive((dark + (bright - dark) * fe * accent) * e * 1.6, 2.6)


# ---------------------------------------------------------------- stems

def bar_time(b, step=0):
    return b * BAR + step * STEP


def stem_tension():
    buf = np.zeros((2, N))
    # Sub drone: follows the root every bar with smooth glides (rendered per bar, crossfaded).
    x = np.arange(N) / SR
    f = np.zeros(N)
    for b in range(BARS):
        i0, i1 = int(b * BAR * SR), int((b + 1) * BAR * SR)
        f[i0:i1] = hz(ROOTS[b], D2 / 2)
    f = circ(lp, f, 3.0, 1)  # glides between roots
    f *= round(f.sum() / SR) / (f.sum() / SR)  # whole cycles over the loop
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.12 * drive(np.sin(3 * ph), 2)
    swell = 0.7 + 0.3 * np.sin(2 * np.pi * x / (8 * BAR))  # 4 cycles per loop
    sub = sub * swell * 0.55
    buf += sub
    # Heartbeat sub pulse: 1 and the and of 2, each bar.
    for b in range(BARS):
        for st, g in ((0, 1.0), (6, 0.6)):
            xx = tt(0.6)
            fp = hz(ROOTS[b], D2 / 2) * (1 + 0.8 * np.exp(-xx / 0.05))
            th = np.sin(2 * np.pi * np.cumsum(fp) / SR) * np.exp(-xx / 0.22) * g
            place(buf, bar_time(b, st), drive(th, 1.5), 0.0, 0.8)
    # Distant bowed metal: D3 and A3 drones, wide.
    bm1 = bowed_metal(hz(12), LOOP, seed=11)
    bm2 = bowed_metal(hz(19), LOOP, seed=12)
    for ch, g1, g2 in ((0, 0.11, 0.05), (1, 0.06, 0.1)):
        buf[ch] += bm1 * g1 + bm2 * g2
    # B and C sections: a high minor-second whine, barely there.
    xw = tt(16 * BAR)
    wh = (np.sin(2 * np.pi * hz(36) * xw) + np.sin(2 * np.pi * hz(37) * xw)) * np.sin(np.pi * xw / (16 * BAR)) ** 2
    place(buf, bar_time(8), wh * 0.015, -0.6)
    place(buf, bar_time(24), wh[: int(8 * BAR * SR)] * 0.02, 0.6)
    # Far-off clanks every four bars, panned around.
    for k, b in enumerate(range(2, BARS, 4)):
        c = anvil(hz(24 + [0, 7, 3, 1][k % 4]) * 1.0, 1.2, damp=0.4)
        place(buf, bar_time(b, [10, 3, 13, 7][k % 4]), lp(c, 2500) * 0.35, [-0.8, 0.7, -0.4, 0.9][k % 4])
    # Machine tick: muted eighths, a little swing.
    for b in range(BARS):
        for s in range(0, 16, 2):
            g = 0.10 if s % 4 == 0 else 0.06
            tk = lp(hat(0.04), 4500) * g
            place(buf, bar_time(b, s) + (0.012 if s % 4 == 2 else 0), tk, 0.35)
    buf = reverb(buf, sec=3.6, decay=1.1, mix=0.45, lo=120, hi=4000, seed=21)
    return _seam(buf)


KICKS = {
    "A": [0, 3, 6, 10, 11],
    "B": [0, 3, 8, 10, 14],
    "C": [0, 2, 3, 6, 8, 10, 11, 14],
}
BASS = {
    # step: (semitone offset from root, accent)
    "A": {0: (0, 1.0), 2: (0, 0.4), 3: (12, 0.8), 6: (0, 0.9), 8: (0, 0.5), 10: (0, 1.0), 11: (1, 0.7), 14: (12, 0.8)},
    "B": {0: (0, 1.0), 3: (0, 0.7), 6: (7, 0.8), 8: (0, 0.6), 10: (0, 1.0), 12: (3, 0.6), 14: (1, 0.9)},
    "C": {0: (0, 1.0), 1: (0, 0.3), 3: (12, 0.9), 4: (0, 0.4), 6: (0, 1.0), 8: (0, 0.5), 9: (0, 0.4),
          10: (12, 1.0), 11: (1, 0.8), 13: (0, 0.5), 14: (3, 0.9), 15: (1, 0.6)},
}


def section(b):
    return "ABAC"[b // 8]


def stem_combat():
    drums = np.zeros((2, N))
    bass = np.zeros((2, N))
    for b in range(BARS):
        sec = section(b)
        kp = KICKS["C" if sec == "C" else ("B" if sec == "B" else "A")]
        for s in kp:
            place(drums, bar_time(b, s), kick(punch=1.0 if s in (0, 10) else 0.8), 0.0, 0.9)
        # Clanging snare on 2 and 4, ghosts.
        for s in (4, 12):
            place(drums, bar_time(b, s), snare(), 0.05, 0.55)
        for s in ((7,) if b % 2 == 0 else (15,)):
            place(drums, bar_time(b, s), snare(0.2) * 0.3, -0.1, 0.4)
        # Anvil hits on the offbeat syncopations.
        for s, f, pan in ((7, 1320.0, -0.5), (15, 990.0, 0.5)):
            if (b + s) % 3 != 0:
                place(drums, bar_time(b, s), anvil(f, 0.5, damp=0.09) * 0.25, pan)
        # Sixteenth hats with accents, open on the last step of each 2 bars.
        for s in range(16):
            acc = 1.0 if s % 4 == 2 else (0.6 if s % 2 == 0 else 0.35)
            op = (s == 14 and b % 2 == 1)
            place(drums, bar_time(b, s), hat(0.25 if op else 0.07, op) * 0.22 * acc, 0.3 if s % 2 else -0.3)
        # Bass riff riding the kick.
        pat = BASS[sec]
        steps = sorted(pat)
        for j, s in enumerate(steps):
            nxt = steps[j + 1] if j + 1 < len(steps) else 16
            dur = min((nxt - s) * STEP, 3 * STEP) * 0.92
            off, acc = pat[s]
            place(bass, bar_time(b, s), bass_note(ROOTS[b] + off, dur, acc), 0.0, 0.6)
        # Section turnarounds: a reversed-noise swell into the next section.
        if b % 8 == 7:
            xr = tt(BAR)
            rise = hp(rng.standard_normal(len(xr)), 1500) * (xr / BAR) ** 3
            place(drums, bar_time(b), rise * 0.25, 0.0)
    drums = reverb(drums, sec=1.4, decay=0.35, mix=0.18, lo=300, hi=7000, seed=31)
    # Sidechain the bass against the kick (pump) for drive.
    out = drums + bass
    return _seam(out)


def stem_boss():
    buf = np.zeros((2, N))
    # Braams every two bars: root power chord, longer on phrase starts.
    for b in range(0, BARS, 2):
        r = ROOTS[b]
        dur = 2 * BAR - 0.05
        chord = [r - 12, r - 5, r] if b % 8 != 6 else [r - 12, r - 6, r]  # a tritone on the turn
        bm = brass(chord, dur, swell=0.22 if b % 4 == 0 else 0.4, bright=1600 if b % 8 == 0 else 1100)
        place(buf, bar_time(b), bm * 0.8, -0.15)
        place(buf, bar_time(b) + 0.011, bm * 0.8, 0.15)
        # A stab a fifth up on the and of 4 of the second bar.
        st = brass([r + 7, r + 12], 0.45, swell=0.03, bright=2200)
        place(buf, bar_time(b + 1, 14), st * 0.35, 0.3)
    # Heavy toms: driving eighths with flams.
    pat = [0, 3, 6, 8, 10, 11, 14]
    for b in range(BARS):
        for s in pat:
            low = s in (0, 8)
            f0 = hz(ROOTS[b], D2) * (0.75 if low else 1.12)
            t0 = bar_time(b, s)
            place(buf, t0, tom(f0, 0.9 if low else 0.5) * (0.8 if low else 0.5), -0.25 if s % 3 else 0.25)
            if s == 11:
                place(buf, t0 - 0.025, tom(f0 * 1.2, 0.3) * 0.25, 0.4)
        if b % 4 == 0:
            place(buf, bar_time(b), sheet(3.5, 92.0) * 0.28, 0.0)
        # Chain rattle on beat 3 every other bar.
        if b % 2 == 1:
            xc = tt(0.35)
            ch = sum(bp(rng.standard_normal(len(xc)), 2500, 9000) * np.exp(-((xc - k * 0.045) % 0.35) / 0.01)
                     for k in range(5))
            place(buf, bar_time(b, 8), ch * 0.04 * np.exp(-xc / 0.2), 0.6)
    buf = reverb(buf, sec=2.8, decay=0.8, mix=0.3, lo=100, hi=5000, seed=41)
    return _seam(buf)


def _seam(buf):
    """Every note is placed circularly and every drone runs a whole number of
    cycles over the loop (`q`), so the end already meets the start."""
    return buf


# ---------------------------------------------------------------- stingers

def sting_buf(sec):
    return np.zeros((2, int(sec * SR)))


def sting_wave_start():
    b = sting_buf(2.0)
    xr = tt(0.42)
    rise = hp(rng.standard_normal(len(xr)), 800) * (xr / 0.42) ** 2.5
    place(b, 0.0, rise * 0.35, 0.0, wrap=False)
    place(b, 0.42, kick(0.8, 1.2, 4.0), 0.0, 1.0, wrap=False)
    place(b, 0.42, sheet(1.5, 98.0) * 0.5, 0.0, wrap=False)
    place(b, 0.42, anvil(hz(36), 1.2, damp=0.3) * 0.35, -0.4, wrap=False)
    bm = brass([-12, -5, 0], 1.5, swell=0.04, bright=2400)
    place(b, 0.42, bm * 0.9, 0.0, wrap=False)
    return reverb(b, 1.8, 0.5, 0.3, seed=51, circular=False)


def sting_wave_cleared():
    b = sting_buf(2.2)
    # Hydraulic release: noise swept down.
    xh = tt(0.9)
    hiss = rng.standard_normal(len(xh))
    hiss = bp(hiss, 600, 6000) * np.exp(-xh / 0.35)
    hiss = lp(hiss, 3000) * 0.6
    place(b, 0.0, hiss * 0.35, 0.3, wrap=False)
    place(b, 0.0, tom(hz(0, D2), 0.8) * 0.7, 0.0, wrap=False)
    # A ringing fifth, D and A, resolving (relief, not triumph).
    place(b, 0.05, anvil(hz(24), 2.0, damp=0.9) * 0.4, -0.35, wrap=False)
    place(b, 0.22, anvil(hz(31), 1.9, damp=0.8) * 0.35, 0.35, wrap=False)
    pad = brass([0, 7, 12], 1.8, swell=0.3, bright=900)
    place(b, 0.05, pad * 0.45, 0.0, wrap=False)
    return reverb(b, 2.2, 0.7, 0.4, seed=52, circular=False)


def sting_supply_drop():
    b = sting_buf(1.6)
    xh = tt(0.5)
    hiss = bp(rng.standard_normal(len(xh)), 1500, 9000) * np.exp(-xh / 0.15)
    place(b, 0.0, hiss * 0.3, -0.3, wrap=False)
    for k, (t0, f) in enumerate(((0.06, 520.0), (0.2, 470.0), (0.34, 600.0))):
        x = tt(0.25)
        clunk = lp(rng.standard_normal(len(x)), 1800) * np.exp(-x / 0.02) + np.sin(2 * np.pi * f * x) * np.exp(-x / 0.05)
        place(b, t0, drive(clunk, 2.5) * 0.45, [-0.4, 0.4, 0.0][k], wrap=False)
    place(b, 0.34, kick(0.4, 0.6, 2.0) * 0.6, 0.0, wrap=False)
    place(b, 0.42, anvil(hz(43), 1.1, damp=0.5) * 0.3, 0.2, wrap=False)  # a bright A ping
    return reverb(b, 1.2, 0.35, 0.25, seed=53, circular=False)


def sting_mk3():
    b = sting_buf(2.0)
    # Capacitor charge: a servo whine rising D4 -> D6.
    x = tt(0.7)
    f = hz(24) * 2 ** (2 * (x / 0.7) ** 1.6)
    whine = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    whine *= (x / 0.7) ** 1.5 * 0.25
    place(b, 0.0, whine, 0.0, wrap=False)
    place(b, 0.0, hp(rng.standard_normal(len(x)), 3000) * (x / 0.7) ** 3 * 0.15, 0.0, wrap=False)
    place(b, 0.7, kick(0.6, 1.1, 3.5), 0.0, 0.9, wrap=False)
    hit = brass([-12, -5, 0, 7], 1.3, swell=0.02, bright=3000)
    place(b, 0.7, hit, 0.0, 0.9, wrap=False)
    place(b, 0.7, anvil(hz(38), 1.2, damp=0.6) * 0.3, -0.5, wrap=False)
    place(b, 0.72, anvil(hz(45), 1.2, damp=0.6) * 0.25, 0.5, wrap=False)
    return reverb(b, 1.8, 0.5, 0.3, seed=54, circular=False)


def sting_boss_kneel():
    b = sting_buf(2.4)
    place(b, 0.0, kick(1.0, 1.3, 4.0), 0.0, 1.0, wrap=False)
    place(b, 0.0, sheet(2.4, 61.0) * 0.6, 0.0, wrap=False)
    # A braam that sags a semitone as it dies (D -> C#).
    sec = 2.2
    x = tt(sec)
    tone = np.zeros_like(x)
    for s in (-24, -12, -5):
        f = hz(s) * 2 ** (-(np.clip(x - 0.6, 0, None) / 1.6) / 12)
        for d in (-0.01, 0.0, 0.009):
            tone += 2 * ((np.cumsum(f * (1 + d)) / SR + rng.uniform()) % 1) - 1
    tone /= 9
    amp = np.clip(x / 0.03, 0, 1) * np.exp(-x / 0.9)
    br = lp(tone, 1500) * np.exp(-x / 0.4) + lp(tone, 250)
    place(b, 0.0, drive(br * amp * 2.5, 2.2) * 0.9, 0.0, wrap=False)
    return reverb(b, 2.6, 0.9, 0.35, seed=55, circular=False)


def sting_run_over():
    b = sting_buf(2.6)
    sec = 2.5
    x = tt(sec)
    tone = np.zeros_like(x)
    # Descending: D falls a fourth to A below, slowly.
    for s in (-12, 0, 3):
        f = hz(s) * 2 ** (-5 * (x / sec) ** 1.3 / 12)
        for d in (-0.012, -0.004, 0.005, 0.011):
            tone += 2 * ((np.cumsum(f * (1 + d)) / SR + rng.uniform()) % 1) - 1
    tone /= 12
    amp = np.clip(x / 0.06, 0, 1) * np.clip((sec - x) / 1.4, 0, 1)
    flt = lp(tone, 220) + (lp(tone, 1300) - lp(tone, 220)) * np.exp(-x / 0.5)
    place(b, 0.0, drive(flt * amp * 2.2, 2.0) * 0.9, 0.0, wrap=False)
    place(b, 0.0, tom(hz(-12), 1.4), 0.0, 0.9, wrap=False)
    place(b, 0.0, anvil(hz(13), 2.4, damp=1.0) * 0.25, 0.4, wrap=False)  # the flat second, ringing
    return reverb(b, 3.0, 1.0, 0.45, seed=56, circular=False)


# ---------------------------------------------------------------- output

def finish(buf, peak_db, loop):
    buf = buf - buf.mean(axis=1, keepdims=True)
    buf = circ(hp, buf, 25) if loop else hp(buf, 25)  # keep sub-bass but not DC rumble
    if not loop:
        k = int(0.08 * SR)
        buf[:, -k:] *= np.linspace(1, 0, k)
        buf[:, :64] *= np.linspace(0, 1, 64)
    peak = np.abs(buf).max() + 1e-9
    return buf / peak * 10 ** (peak_db / 20)


def write_ogg(name, buf, quality):
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, name + ".wav")
        wavfile.write(wav, SR, (buf.T * 32767).astype(np.int16))
        dst = os.path.join(OUT, name + ".ogg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis",
                        "-q:a", str(quality), dst], check=True)
    rms = 20 * np.log10(np.sqrt(np.mean(buf ** 2)) + 1e-9)
    print(f"{name}: {buf.shape[1] / SR:.2f} s, rms {rms:.1f} dBFS, {os.path.getsize(dst) / 1024:.0f} KB")


def main():
    only = sys.argv[2:] if len(sys.argv) > 2 else None
    stems = {"music_tension": stem_tension, "music_combat": stem_combat, "music_boss": stem_boss}
    stings = {"sting_wave_start": sting_wave_start, "sting_wave_cleared": sting_wave_cleared,
              "sting_supply_drop": sting_supply_drop, "sting_mk3": sting_mk3,
              "sting_boss_kneel": sting_boss_kneel, "sting_run_over": sting_run_over}
    for name, f in stems.items():
        if only and name not in only:
            continue
        write_ogg(name, finish(f(), -3.0, True), 3)
    for name, f in stings.items():
        if only and name not in only:
            continue
        write_ogg(name, finish(f(), -2.0, False), 4)


if __name__ == "__main__":
    main()
