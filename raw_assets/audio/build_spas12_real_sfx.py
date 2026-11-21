#!/usr/bin/env python3
"""The SPAS-12's shot and pump from real recordings (CC0; see CREDITS.md).

Owner, 2026-11-21: "the sound effects for it are terrible. I want you to find a
real pump shotgun sound effect ... It sounds like a fucking arcade game with
coins." The synthesized pump (build_spas12_sfx.py) was ringing sine partials,
which is what a coin sounds like; a real rack is broadband steel-on-steel noise.

Sources (raw_assets/audio/fetched/, fetched by the "Fetch sounds" workflow):
- pump: "Remington 870 12 gauge shotgun pump racking cha chock" (Freesound
  755495, TotallyPhilip, CC0): sixteen racks of a real 870. Each rack is cut in
  two: the back stroke (the unlock, the bars running back, the hard stop at the
  rear) and the forward stroke (the next shell lifted, the bolt locking home).
  Three racks give three variants of each, so no two pumps sound the same.
- shot: The Free Firearm Sound Library (OpenGameArt, CC0), 12-gauge pump guns
  recorded on a range at 96 kHz, stereo (SHOT_SOURCES below). Each shot is cut
  from its own silence through its natural decay; under it a low layer (the
  chest punch and a short sub swell, from build_spas12_sfx.py) for weight on a
  phone speaker, which can't play what a real shotgun puts below 100 Hz.
- tail: the late, darker part of the same recordings, faded in, played at
  -8 dB under every shot (Sfx.play_shot) as the room and the distance.

The game starts the pump sounds early (WeaponData.pump_back_sound_t,
pump_forward_sound_t) so the recorded stop and lock land when the animated
fore-end reaches the rear and home.

Usage: python3 raw_assets/audio/build_spas12_real_sfx.py [out_dir]  (default assets/audio/sfx)
Needs ffmpeg, numpy, scipy.
"""
import glob
import os
import subprocess
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fetched")
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
SR = 44100

RACK_SOURCE = "fs_755495_*.mp3"
RACK_PICKS = (2, 6, 11)  # which of the sixteen racks become variants 1..3
# (glob, shot index in the file) for spas12_shot_1..3
# The Benelli Nova and the Mossberg, on the take with the most body and range
# reflections (the "_17P"/"_26P" files; the others are drier and thinner).
SHOT_SOURCES = [
    ("oga_Prepared_SFX_Library/*Nova__O_17P.wav", 0),
    ("oga_Prepared_SFX_Library/*Nova__O_17P.wav", 1),
    ("oga_Prepared_SFX_Library/*Mossberg__N_26P.wav", 0),
]
SHOT_LEN = 1.5
TAIL_FROM = ("oga_Prepared_SFX_Library/*Mossberg__N_26P.wav", 1)
# How far the first spike is held down so the blast's body comes up (a real
# shot is a 1 ms spike 30 dB over everything after it; a phone plays the body).
SHOT_SQUASH_DB = 16.0
# The range's slap-backs come up with the body; held down this much from
# 0.05 s so they don't read as a second shot.
ECHO_DUCK_DB = 7.0


def load(pattern, channels=2):
    paths = sorted(glob.glob(os.path.join(SRC, pattern)))
    if not paths:
        sys.exit(f"missing source {pattern} (run the Fetch sounds workflow)")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", paths[0], "-ac", str(channels), "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).astype(np.float64)


def envelope(x, ms=2.0):
    mono = np.abs(x).max(axis=1)
    n = max(1, int(ms * 0.001 * SR))
    return np.convolve(mono, np.ones(n) / n, mode="same")


def peaks(x, rel=0.45, gap=0.12):
    """Sample indices of the loud transients, at least `gap` s apart."""
    env = envelope(x)
    thr = env.max() * rel
    idx = []
    i = 0
    while i < len(env):
        if env[i] > thr:
            j = i + int(0.03 * SR)
            k = i + int(np.argmax(env[i:j]))
            idx.append(k)
            i = k + int(gap * SR)
        else:
            i += 1
    return idx


def onset_before(x, at, look=0.05, rel=0.02):
    """First sample before `at` where the sound rises out of the silence."""
    env = envelope(x, 1.0)
    a = max(0, at - int(look * SR))
    floor = env[at] * rel
    seg = env[a:at]
    quiet = np.where(seg < floor)[0]
    return a + (quiet[-1] if len(quiet) else 0)


def fade(x, fade_in=0.002, fade_out=0.03):
    y = x.copy()
    a = int(fade_in * SR)
    b = int(fade_out * SR)
    if a:
        y[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        y[-b:] *= np.linspace(1, 0, b)[:, None] ** 2
    return y


def limit(x, ceiling_db=-0.5, release=0.05):
    """Look-ahead peak limiter (the decoded mp3 overshoots full scale)."""
    ceil = 10 ** (ceiling_db / 20)
    peak = np.abs(x).max(axis=1)
    la = int(0.002 * SR)
    ahead = np.array([peak[i:i + la].max() if i < len(peak) else 0 for i in range(len(peak))])
    gain = np.minimum(1.0, ceil / np.maximum(ahead, 1e-9))
    coef = np.exp(-1.0 / (release * SR))
    g = np.empty_like(gain)
    cur = 1.0
    for i, v in enumerate(gain):
        cur = v if v < cur else v + (cur - v) * coef
        g[i] = cur
    return x * g[:, None]


def normalize(x, peak_db):
    return x * (10 ** (peak_db / 20) / max(np.abs(x).max(), 1e-9))


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "low")
    return signal.lfilter(b, a, x, axis=0)


def highpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "high")
    return signal.lfilter(b, a, x, axis=0)


def save(name, x, peak_db):
    x = x - x.mean(axis=0)
    x = limit(normalize(x, peak_db + 1.5), peak_db)
    os.makedirs(OUT, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    if data.shape[1] == 1:
        data = data[:, 0]
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, data)
    print(f"  {name}: {len(x) / SR:.2f} s")


def racks():
    x = load(RACK_SOURCE, 1)
    p = peaks(x, rel=0.5, gap=0.15)
    # Each rack is a rear stop then a lock about 0.2 s later.
    pairs = []
    i = 0
    while i + 1 < len(p):
        if 0.15 * SR < p[i + 1] - p[i] < 0.3 * SR:
            pairs.append((p[i], p[i + 1]))
            i += 2
        else:
            i += 1
    print(f"  {len(pairs)} racks found")
    backs, fwds = [], []
    for k in RACK_PICKS:
        stop, lock = pairs[k]
        # back: from the unlock (~0.1 s before the stop) to just before the forward push
        b0 = stop - int(0.105 * SR)
        f0 = lock - int(0.115 * SR)
        back = x[b0:f0 - int(0.005 * SR)]
        fwd = x[f0:lock + int(0.26 * SR)]
        backs.append((back, (stop - b0) / SR))
        fwds.append((fwd, (lock - f0) / SR))
    return backs, fwds


def shot_cut(pattern, index):
    x = load(pattern, 2)
    p = peaks(x, rel=0.5, gap=1.0)
    at = p[index]
    a = onset_before(x, at, 0.03)
    return x[a:a + int(SHOT_LEN * SR)], x, a


def thump(n):
    """One short chest hit (a single falling cycle, 40 ms), stereo."""
    t = np.arange(n) / SR
    f = 60 + 110 * np.exp(-t / 0.012)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * (1 - np.exp(-t / 0.0015))
    return np.stack([y, y], axis=1)


def build_shot(pattern, index):
    cut, _, at = shot_cut(pattern, index)
    print(f"    {os.path.basename(pattern)} shot {index} at {at / SR:.2f} s")
    real = normalize(highpass(cut, 30), -1.0)
    # Squash the spike so the blast and the range behind it come up.
    real = limit(real, -1.0 - SHOT_SQUASH_DB, release=0.035)
    duck = np.ones(len(real))
    a, b = int(0.05 * SR), int(0.12 * SR)
    duck[a:b] = np.linspace(1.0, 10 ** (-ECHO_DUCK_DB / 20), b - a)
    duck[b:] = 10 ** (-ECHO_DUCK_DB / 20)
    real = normalize(real * duck[:, None], -1.0)
    # Weight from the recording itself: its own lows, saturated a little.
    low = np.tanh(lowpass(real, 160, 2) * 3.0) * 0.55
    mix = real + low + thump(len(real)) * 0.3
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    return fade(mix, 0.0005, 0.3)


def build_tail():
    pattern, index = TAIL_FROM
    _, x, a = shot_cut(pattern, index)
    seg = x[a:a + int(3.2 * SR)]
    seg = lowpass(seg, 2400, 2)
    env = np.ones(len(seg))
    k = int(0.12 * SR)
    env[:k] = np.linspace(0, 1, k) ** 2  # the shot itself plays the first moments
    return fade(seg * env[:, None], 0.0, 0.8)


def main():
    print("SPAS-12 from recordings:")
    backs, fwds = racks()
    for v, (b, at) in enumerate(backs, 1):
        save(f"spas12_pump_back_{v}", fade(b, 0.001, 0.012), -1.0)
        print(f"    rear stop {at:.3f} s in")
    for v, (f, at) in enumerate(fwds, 1):
        save(f"spas12_pump_forward_{v}", fade(f, 0.001, 0.08), -0.5)
        print(f"    lock {at:.3f} s in")
    for v, (pattern, index) in enumerate(SHOT_SOURCES, 1):
        save(f"spas12_shot_{v}", build_shot(pattern, index), -0.3)
    save("spas12_tail_1", build_tail(), -2.0)


if __name__ == "__main__":
    main()
