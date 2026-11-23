#!/usr/bin/env python3
"""Trailer score (docs/trailer.md): a 30-second synthesized cue, 120 BPM in
D minor, timed to the cut list in tools/trailer/edit.json.

  0.0  drone, rain-tick pulse, guzheng plucks (pentatonic)       act 1
  4.5  braam + sub hit ("YOU'RE NOT.": the GX-4 arm unfolds)
  5.0  riser
  6.0  drop: impact; distorted bass ostinato, taiko, kick/clap    act 2
 14.5  second layer: tom fills, a higher ostinato
 18.0  third layer: octave bass, faster hats
 24.5  one beat of silence
 25.0  title slam: braam, sub boom, long tail                     act 3

Everything is synthesized here with numpy (no samples), deterministic.
Usage: score.py <out.wav> [--edit tools/trailer/edit.json]
"""
import json
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
BPM = 120.0
BEAT = 60.0 / BPM
LEN = 30.0
N = int(LEN * SR)
rng = np.random.default_rng(7)


def t_axis(n):
    return np.arange(n) / SR


def env_adsr(n, a, d, s, r, sus_len=None):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(n - a_n - d_n - r_n, 0) if sus_len is None else int(sus_len * SR)
    e = np.concatenate([np.linspace(0, 1, max(a_n, 1)), np.linspace(1, s, max(d_n, 1)),
                        np.full(s_n, s), np.linspace(s, 0, max(r_n, 1))])
    if len(e) < n:
        e = np.concatenate([e, np.zeros(n - len(e))])
    return e[:n]


def lp(x, fc, order=2):
    sos = butter(order, min(fc, SR * 0.45), 'low', fs=SR, output='sos')
    return sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = butter(order, fc, 'high', fs=SR, output='sos')
    return sosfilt(sos, x)


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, min(hi, SR * 0.45)], 'band', fs=SR, output='sos')
    return sosfilt(sos, x)


def sweep_lp(x, f0, f1, curve=2.0):
    """Time-varying one-pole low-pass from f0 to f1 (Hz)."""
    n = len(x)
    fc = f0 + (f1 - f0) * np.linspace(0, 1, n) ** curve
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros(n)
    z = 0.0
    for i in range(n):
        z = (1 - a[i]) * x[i] + a[i] * z
        y[i] = z
    return y


def saw(freq, n, phase=0.0):
    ph = (phase + np.cumsum(np.full(n, freq) if np.isscalar(freq) else freq) / SR) % 1.0
    return 2 * ph - 1


def note_hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def add(buf, x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


def reverb(x, seconds=2.2, mix=0.3, seed=3):
    """Cheap convolution reverb with a decaying noise tail (per channel)."""
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    tail = r.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    tail = lp(tail, 6000)
    tail /= np.sqrt(np.sum(tail ** 2))
    out = np.zeros_like(x)
    for c in range(x.shape[1]):
        wet = fftconvolve(x[:, c], tail)[: len(x)]
        out[:, c] = x[:, c] * (1 - mix) + wet * mix * 3.0
    return out


# ------------------------------------------------------------------ instruments

def kick(n=0.5, punch=1.0):
    m = int(n * SR)
    t = t_axis(m)
    f = 45 + 110 * np.exp(-t * 28)
    ph = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * ph) * np.exp(-t * 6)
    click = hp(rng.standard_normal(m), 2000) * np.exp(-t * 180) * 0.4
    return soft_clip((body + click) * punch, 1.5)


def clap(n=0.6):
    m = int(n * SR)
    t = t_axis(m)
    noise = bp(rng.standard_normal(m), 900, 4200)
    e = np.zeros(m)
    for k, d in enumerate([0.0, 0.011, 0.022]):
        i = int(d * SR)
        e[i:] += np.exp(-(t[: m - i]) * (60 if k < 2 else 14))
    return noise * e * 0.7


def hat(n=0.12, open_=False):
    m = int(n * SR)
    t = t_axis(m)
    x = hp(rng.standard_normal(m), 7000)
    return x * np.exp(-t * (18 if open_ else 70)) * 0.35


def taiko(n=1.2, pitch=70):
    m = int(n * SR)
    t = t_axis(m)
    f = pitch + 40 * np.exp(-t * 20)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    skin = lp(rng.standard_normal(m), 900) * np.exp(-t * 30) * 0.8
    return soft_clip(body * 1.2 + skin, 1.3)


def tom(pitch=110, n=0.5):
    m = int(n * SR)
    t = t_axis(m)
    f = pitch * (1 + 0.6 * np.exp(-t * 25))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.8


def braam(n=3.0, root=38, bright=1.0):
    """Detuned saw stack on root and fifth through a low-pass that blooms and
    closes; distorted. The trailer 'BRAAM'."""
    m = int(n * SR)
    t = t_axis(m)
    x = np.zeros(m)
    for midi, g in [(root - 12, 0.9), (root, 1.0), (root + 7, 0.6), (root + 12, 0.45)]:
        for det in (-0.12, -0.04, 0.05, 0.13):
            hz = note_hz(midi + det)
            x += saw(hz * (1 + 0.002 * np.sin(2 * np.pi * 0.3 * t)), m, rng.random()) * g
    x /= 10.0
    fenv = 120 + 2200 * bright * (np.exp(-t * 1.4) * (1 - np.exp(-t * 40)))
    y = np.zeros(m)
    z1 = z2 = 0.0
    a = np.exp(-2 * np.pi * fenv / SR)
    for i in range(m):
        z1 = (1 - a[i]) * x[i] + a[i] * z1
        z2 = (1 - a[i]) * z1 + a[i] * z2
        y[i] = z2
    y = soft_clip(y * 3.0, 2.0)
    e = env_adsr(m, 0.012, 0.6, 0.55, n * 0.6)
    sub = np.sin(2 * np.pi * note_hz(root - 12) * t) * np.exp(-t * 0.9) * 0.9
    return (y * 0.8 + sub) * e


def impact(n=2.5, depth=1.0):
    m = int(n * SR)
    t = t_axis(m)
    f = 30 + 70 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    crack = lp(rng.standard_normal(m), 3500) * np.exp(-t * 14)
    rumble = lp(rng.standard_normal(m), 180) * np.exp(-t * 2.0) * 1.5
    return soft_clip(sub * 1.3 * depth + crack * 0.6 + rumble * 0.5, 1.6)


def riser(n=1.0):
    m = int(n * SR)
    t = t_axis(m)
    u = t / n
    noise = rng.standard_normal(m)
    x = sweep_lp(noise, 300, 9000, 2.5) * (u ** 2.2)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * u ** 2) / SR) * u ** 3 * 0.25
    return (x * 0.9 + tone)


def whoosh(n=0.5):
    m = int(n * SR)
    t = t_axis(m)
    u = t / n
    return bp(rng.standard_normal(m), 400, 5000) * np.sin(np.pi * u) ** 2 * 0.6


def guzheng(midi, n=2.2):
    """Karplus-Strong pluck with a bright attack and a slow bend-free decay."""
    m = int(n * SR)
    hz = note_hz(midi)
    p = int(SR / hz)
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(m)
    for i in range(m):
        j = i % p
        out[i] = buf[j]
        buf[j] = 0.5 * (buf[j] + buf[(j + 1) % p]) * 0.9965
    t = t_axis(m)
    out += np.sin(2 * np.pi * hz * 2 * t) * np.exp(-t * 6) * 0.15
    return lp(out, 5200) * 0.7


def bass_note(midi, n, drive=2.5, cutoff=900):
    m = int(n * SR)
    t = t_axis(m)
    x = saw(note_hz(midi), m) * 0.6 + saw(note_hz(midi) * 1.004, m, 0.3) * 0.4
    x = lp(x, cutoff, 2)
    x += np.sin(2 * np.pi * note_hz(midi - 12) * t) * 0.6
    e = env_adsr(m, 0.004, 0.08, 0.7, 0.04)
    return soft_clip(x * e, drive) * 0.55


def drone(n, root=26):
    m = int(n * SR)
    t = t_axis(m)
    x = np.sin(2 * np.pi * note_hz(root) * t) + 0.5 * np.sin(2 * np.pi * note_hz(root + 7) * t + 1.0)
    x += lp(saw(note_hz(root + 12), m), 300) * 0.4
    x *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t) ** 2
    return x * 0.35


def string_ostinato(midis, start, end, step):
    """Short bowed-ish notes (filtered saws) on 16ths."""
    m = int((end - start) * SR)
    out = np.zeros(m)
    k = 0
    tt = 0.0
    while tt < end - start - 1e-6:
        midi = midis[k % len(midis)]
        n = int(step * SR * 0.9)
        x = sum(saw(note_hz(midi + d), n, rng.random()) for d in (-0.08, 0.0, 0.07)) / 3
        x = lp(x, 2600) * env_adsr(n, 0.01, 0.05, 0.6, 0.03)
        i = int(tt * SR)
        out[i:i + n] += x[: m - i]
        tt += step
        k += 1
    return out * 0.25


# ------------------------------------------------------------------ the cue

def build(edit):
    mix = np.zeros((N, 2))
    sfx = np.zeros((N, 2))   # hits and whooshes that ride on the cuts
    drop = edit.get("drop", 6.0)
    title = edit.get("title", 25.0)
    gap = edit.get("silence", 24.5)

    # Act 1: drone, pulse, guzheng.
    d = drone(drop + 0.2) * env_adsr(int((drop + 0.2) * SR), 1.5, 0.1, 1.0, 0.2)
    add(mix, d, 0.0, 0.9)
    for i in range(int(drop / (BEAT / 2))):
        tt = i * BEAT / 2
        add(mix, hat(0.05), tt, 0.25 + 0.5 * (tt / drop), pan=0.3 if i % 2 else -0.3)
    plucks = [(0.25, 62, -0.4), (0.75, 65, 0.3), (1.25, 69, -0.2), (2.0, 67, 0.4),
              (3.0, 62, -0.3), (3.5, 60, 0.3), (4.0, 57, 0.0)]
    for tt, midi, pan in plucks:
        add(mix, guzheng(midi), tt, 0.55, pan)
    # The reveal ("YOU'RE NOT."): braam and a sub hit.
    reveal = edit.get("reveal", 4.5)
    add(mix, braam(3.2, 38, 0.8), reveal, 0.75)
    add(sfx, impact(2.4, 0.8), reveal, 0.7)
    # The arm unfolds: riser into the drop.
    add(mix, riser(drop - 5.0 + 0.02), 5.0, 0.55)
    for k in range(4):
        add(mix, tom(140 + 20 * k, 0.3), 5.0 + k * BEAT / 2, 0.5 + 0.12 * k)

    # Act 2: the drop.
    add(sfx, impact(2.0, 1.0), drop, 0.9)
    add(mix, braam(2.0, 38, 1.0), drop, 0.45)
    seq = [38, 38, 50, 38, 41, 38, 43, 41]   # D2 ostinato, minor
    bars_end = gap
    tt = drop
    k = 0
    step = BEAT / 4
    while tt < bars_end - 1e-6:
        layer3 = tt >= edit.get("layer3", 18.0)
        midi = seq[k % len(seq)]
        add(mix, bass_note(midi, step * 0.95, drive=3.0 if layer3 else 2.4, cutoff=700 + 500 * ((tt - drop) / (bars_end - drop))), tt, 0.85)
        if layer3 and k % 2 == 0:
            add(mix, bass_note(midi + 12, step * 0.9, 2.0, 1400), tt, 0.25, pan=0.2)
        tt += step
        k += 1
    beat_i = 0
    tt = drop
    while tt < bars_end - 1e-6:
        layer2 = tt >= edit.get("layer2", 14.5)
        layer3 = tt >= edit.get("layer3", 18.0)
        pos = beat_i % 4
        if pos in (0, 2):
            add(mix, kick(0.5, 1.1), tt, 0.95)
        if pos in (1, 3):
            add(mix, clap(), tt, 0.5)
        if pos == 0:
            add(mix, taiko(1.2, 62), tt, 0.7, pan=-0.2)
        if layer2 and pos == 3:
            add(mix, taiko(1.0, 85), tt + BEAT / 2, 0.45, pan=0.3)
        for h in range(4 if layer3 else 2):
            add(mix, hat(0.08), tt + h * BEAT / (4 if layer3 else 2), 0.35 if h % 2 == 0 else 0.22, pan=0.35)
        tt += BEAT
        beat_i += 1
    if True:
        st = string_ostinato([74, 77, 81, 77, 74, 72, 74, 69], edit.get("layer2", 14.5), gap, BEAT / 4)
        add(mix, st * env_adsr(len(st), 1.5, 0.1, 1.0, 0.05), edit.get("layer2", 14.5), 0.5, pan=-0.25)
    # Fills before the hotel and the end.
    for base in (edit.get("layer3", 18.0) - BEAT, gap - BEAT):
        for k in range(4):
            add(mix, tom(180 - 25 * k, 0.35), base + k * BEAT / 4, 0.7, pan=-0.4 + 0.27 * k)
    # Accents on the cuts.
    for c in edit.get("accents", []):
        add(sfx, whoosh(0.35), c - 0.3, 0.45)
        add(sfx, impact(1.2, 0.5), c, 0.35)
    # The breath: a reversed swell into the title.
    rs = riser(title - gap)[::-1][::-1]
    add(mix, rs * 0.4, gap, 0.35)

    # Act 3: the title slam and its tail.
    add(mix, braam(5.0, 38, 1.2), title, 1.0)
    add(sfx, impact(4.5, 1.3), title, 1.0)
    add(mix, guzheng(62, 4.0), title + 1.6, 0.5, -0.2)
    add(mix, guzheng(57, 4.0), title + 2.1, 0.4, 0.2)
    tail = drone(LEN - title) * np.exp(-np.linspace(0, 3, int((LEN - title) * SR)))
    add(mix, tail, title, 0.8)

    mix = reverb(mix, 2.4, 0.22)
    sfx = reverb(sfx, 1.6, 0.15)
    out = mix + sfx
    # Nothing in the breath before the title (a hard silence sells the slam).
    g0, g1 = int((gap + 0.05) * SR), int(title * SR)
    fade = np.linspace(1, 0, int(0.05 * SR))
    out[int(gap * SR):g0] *= fade[:, None][: g0 - int(gap * SR)]
    out[g0:g1] *= 0.0
    peak = np.max(np.abs(out))
    out = soft_clip(out / peak * 1.4, 1.2) * 0.89
    return out


def main():
    out_path = sys.argv[1]
    edit = {}
    if "--edit" in sys.argv:
        with open(sys.argv[sys.argv.index("--edit") + 1]) as fh:
            edit = json.load(fh).get("score", {})
    out = build(edit)
    wavfile.write(out_path, SR, (out * 32767).astype(np.int16))
    print("score:", out_path, f"{LEN:.1f}s")


if __name__ == "__main__":
    main()
