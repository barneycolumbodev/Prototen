"""Shared tools for building gun sounds from real recordings (CC0; see CREDITS.md).

Used by build_real_guns_sfx.py. The same steps the .44 Magnum and SPAS-12
builds use (build_magnum44_sfx.py, build_spas12_real_sfx.py), in one place:

- load(): decode any source (wav, flac, mp3) to float stereo at 44.1 kHz.
- peaks()/onset_before(): find each shot in a recording and its first sample.
- squash(): hold the first 1 ms spike down. A real shot is a spike about 30 dB
  over everything after it; a phone speaker plays what comes after (the blast,
  the body), so that has to come up.
- duck_echo(): hold the range's slap-backs down so they don't read as a second
  shot once the body has come up.
- weight(): the low end a phone can play (150-250 Hz pushed, the lows
  saturated, optionally one short chest thump under the blast).
- save(): level, limit and write 16-bit WAV.
"""
import glob
import os
import shutil
import subprocess
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100


def ffmpeg():
    ff = shutil.which("ffmpeg")
    if not ff:
        import imageio_ffmpeg  # pip install imageio-ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    return ff


def find(src_dir, pattern):
    paths = sorted(glob.glob(os.path.join(src_dir, pattern)))
    if not paths:
        sys.exit(f"missing source {pattern} in {src_dir} (run the Fetch sounds workflow)")
    return paths[0]


_cache = {}


def load(src_dir, pattern, channels=2):
    path = find(src_dir, pattern)
    key = (path, channels)
    if key not in _cache:
        raw = subprocess.run([ffmpeg(), "-v", "error", "-i", path, "-ac", str(channels), "-ar", str(SR),
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        _cache[key] = np.frombuffer(raw, np.float32).reshape(-1, channels).astype(np.float64)
    return _cache[key]


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


def onset_before(x, at, look=0.03, rel=0.02):
    env = envelope(x, 1.0)
    a = max(0, at - int(look * SR))
    floor = env[at] * rel
    quiet = np.where(env[a:at] < floor)[0]
    return a + (quiet[-1] if len(quiet) else 0)


def fade(x, fade_in=0.002, fade_out=0.03, power=2.0):
    y = x.copy()
    a = int(fade_in * SR)
    b = int(fade_out * SR)
    if a:
        y[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        y[-b:] *= (np.linspace(1, 0, b) ** power)[:, None]
    return y


def decay(x, start, tau):
    """Exponential fade from `start` s with time constant `tau` s (shortens a shot
    for automatic fire without cutting the recording's own attack)."""
    t = np.arange(len(x)) / SR
    g = np.where(t < start, 1.0, np.exp(-(t - start) / tau))
    return x * g[:, None]


def limit(x, ceiling_db=-0.5, release=0.05):
    """Look-ahead peak limiter."""
    ceil = 10 ** (ceiling_db / 20)
    peak = np.abs(x).max(axis=1)
    la = int(0.002 * SR)
    # running max over the look-ahead window
    pad = np.concatenate([peak, np.zeros(la)])
    ahead = np.lib.stride_tricks.sliding_window_view(pad, la + 1).max(axis=1)[:len(peak)]
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


def rms_db(x):
    return 20 * np.log10(max(np.sqrt((x ** 2).mean()), 1e-9))


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "low")
    return signal.lfilter(b, a, x, axis=0)


def highpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "high")
    return signal.lfilter(b, a, x, axis=0)


def peaking(x, hz, gain_db, q=1.0):
    """RBJ peaking EQ."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * hz / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def pitch(x, ratio):
    """Tape-style: slower and lower by `ratio` (the length grows by `ratio`)."""
    return signal.resample(x, int(len(x) * ratio), axis=0)


def squash(x, db):
    """Hold the first spike down so the blast behind it comes up."""
    return limit(normalize(x, -1.0), -1.0 - db, release=0.04)


def duck_echo(x, start=0.06, ramp=0.08, db=6.0):
    duck = np.ones(len(x))
    d0, d1 = int(start * SR), int((start + ramp) * SR)
    d1 = min(d1, len(x))
    duck[d0:d1] = np.linspace(1.0, 10 ** (-db / 20), d1 - d0)
    duck[d1:] = 10 ** (-db / 20)
    return x * duck[:, None]


def thump(n, hz=52.0, tau=0.055):
    """One short chest hit (a falling cycle), stereo."""
    t = np.arange(n) / SR
    f = hz + 120 * np.exp(-t / 0.012)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau) * (1 - np.exp(-t / 0.0015))
    return np.stack([y, y], axis=1)


def weight(x, body_hz=190.0, body_db=4.0, low_drive=3.0, low_gain=0.5, thump_gain=0.0, thump_hz=52.0,
           thump_tau=0.055, sat=1.4):
    y = peaking(x, body_hz, body_db, 0.9)
    low = np.tanh(lowpass(y, body_hz * 0.9, 2) * low_drive) * low_gain
    mix = y + low
    if thump_gain:
        mix = mix + thump(len(y), thump_hz, thump_tau) * thump_gain
    return np.tanh(mix * sat) / np.tanh(sat)


def shot_at(x, index, length, rel=0.5, gap=0.5):
    """The `index`th shot in recording `x`, from its onset, `length` s long."""
    p = peaks(x, rel=rel, gap=gap)
    if index >= len(p):
        sys.exit(f"only {len(p)} shots found, wanted #{index}")
    a = onset_before(x, p[index])
    n = int(length * SR)
    seg = x[a:a + n]
    if len(seg) < n:
        seg = np.pad(seg, ((0, n - len(seg)), (0, 0)))
    return seg.copy(), a


def save(out_dir, name, x, peak_db, mono=False, level=None):
    """`level` = (rms_db, window_s): set the loudness over the first `window_s`
    (the level the sound it replaces was mixed at), then limit to `peak_db`."""
    x = x - x.mean(axis=0)
    if mono:
        x = x.mean(axis=1, keepdims=True)
    x = normalize(x, peak_db + 1.5)
    y = limit(x, peak_db)
    if level is not None:
        # The limiter eats some of the gain a real shot's spike needs, so
        # re-level a few times; at most 3 dB more than one pass, to keep the
        # transient.
        db, window = level
        n = int(window * SR)
        gain = 10 ** ((db - rms_db(x[:n])) / 20)
        first = gain
        for _ in range(4):
            y = limit(x * gain, peak_db)
            miss = db - rms_db(y[:n])
            if abs(miss) < 0.2:
                break
            gain = min(gain * 10 ** (miss / 20), first * 10 ** (3 / 20))
    x = y
    os.makedirs(out_dir, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    if mono:
        data = data[:, 0]
    wavfile.write(os.path.join(out_dir, name + ".wav"), SR, data)
    print(f"  {name}: {len(x) / SR:.2f} s, rms {rms_db(x):.1f} dB")
