#!/usr/bin/env python3
"""The .44 Magnum's sounds, from real recordings (CC0; see CREDITS.md).

Owner, 2026-11-23: "really, really punchy ... a meaty fucking hand cannon ...
choose another real sound." Every sound here is cut from a recording of a real
revolver; only the low end is reinforced (a phone speaker can't play what a
magnum puts below 100 Hz, so the weight has to come from 100-300 Hz).

Sources (raw_assets/audio/fetched/magnum/, fetched by the "Fetch sounds" workflow):
- shot: "Weapon_Revolver_Shots_Stereo" (Freesound 541818, Nox_Sound, CC0: seven
  shots of a real revolver recorded at 2 m by a concrete wall on a Zoom H5),
  layered over a Smith & Wesson Model 1917 (.45) revolver recorded on a range at
  96 kHz, stereo (The Free Firearm Sound Library, OpenGameArt, CC0): the
  revolver's crack and blast on top, the big-bore's range boom under it. The
  1 ms spike is held down so the blast comes up; its own lows, saturated, plus
  one short chest thump for weight. (Two ".357 Magnum" clips that came with the
  search, Freesound 683175/683186, are filed as designed sounds, so they're not
  used: the owner asked for a real sound.)
- tail: the 1917's second shot rolling away down the range, under every shot.
- reload_start (cylinder latch, the crane swinging out): "Clean Revolver Reload"
  (Freesound 177863, Dredile, CC0; a prop revolver and real cases).
- mag_in (the speedloader pushing six rounds in, its knob turned): "Revolver
  Reload Break 2" (Freesound 722902, tkane0512, CC0: "break, speed loader, close").
- mag_out (the ejector rod slapped, the cases raining down): ".22lr Revolver
  ejecting bullets from cylinder" (Freesound 693125, serøutōnin--deprivəd, CC0),
  pitched down a fifth: .44 cases are three times the size.
- slide_release (the cylinder snapped shut): "22lr revolver handling clicking
  foley" (Freesound 677159) and tkane0512's close, pitched down.
- dry_fire (the hammer falling on an empty chamber): "Revolver Dryfire"
  (Freesound 508745, AugustSandberg, CC0: a Ruger GP100 .357 Magnum, 96 kHz).

Usage: python3 raw_assets/audio/build_magnum44_sfx.py [out_dir]  (default assets/audio/sfx)
Needs numpy, scipy, ffmpeg.
"""
import glob
import os
import subprocess
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fetched", "magnum")
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
SR = 44100

# (main shot, its index, body layer, its index, body gain) for magnum44_shot_1..3
SHOTS = [
    ("fs_541818_*.mp3", 0, "oga_Prepared_SFX_Library/*1917__B_16P.wav", 0, 0.6),
    ("fs_541818_*.mp3", 2, "oga_Prepared_SFX_Library/*1917__B_16P.wav", 1, 0.6),
    ("fs_541818_*.mp3", 4, "oga_Prepared_SFX_Library/*1917__B_24P.wav", 0, 0.75),
]
SHOT_LEN = 1.2
SHOT_SQUASH_DB = 12.0
# The range's slap-backs held down this much from 60 ms.
ECHO_DUCK_DB = 6.0


def load(pattern, channels=2):
    paths = sorted(glob.glob(os.path.join(SRC, pattern)))
    if not paths:
        sys.exit(f"missing source {pattern} (run the Fetch sounds workflow)")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", paths[0], "-ac", str(channels), "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).astype(np.float64)


def cut(pattern, a, b, channels=2):
    x = load(pattern, channels)
    return x[int(a * SR):int(b * SR)]


def pitch(x, ratio):
    """Slower and lower by `ratio` (tape-style: the length grows by `ratio`)."""
    n = int(len(x) * ratio)
    return signal.resample(x, n, axis=0)


def envelope(x, ms=2.0):
    mono = np.abs(x).max(axis=1)
    n = max(1, int(ms * 0.001 * SR))
    return np.convolve(mono, np.ones(n) / n, mode="same")


def peaks(x, rel=0.45, gap=0.12):
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


def peaking(x, hz, gain_db, q=1.0):
    """RBJ peaking EQ."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * hz / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def save(name, x, peak_db):
    x = x - x.mean(axis=0)
    x = limit(normalize(x, peak_db + 1.5), peak_db)
    os.makedirs(OUT, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, data)
    print(f"  {name}: {len(x) / SR:.2f} s")


def shot_at(pattern, index, length):
    x = load(pattern, 2)
    p = peaks(x, rel=0.5, gap=0.8)
    a = onset_before(x, p[index])
    seg = x[a:a + int(length * SR)]
    if len(seg) < int(length * SR):
        seg = np.pad(seg, ((0, int(length * SR) - len(seg)), (0, 0)))
    return seg, a


def thump(n, hz=52.0):
    """One short chest hit (a falling cycle), stereo."""
    t = np.arange(n) / SR
    f = hz + 120 * np.exp(-t / 0.012)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.055) * (1 - np.exp(-t / 0.0015))
    return np.stack([y, y], axis=1)


def squash(x, db):
    """Hold the first spike down so the blast behind it comes up."""
    return limit(normalize(x, -1.0), -1.0 - db, release=0.04)


def build_shot(main, mi, body, bi, body_gain):
    a, at_a = shot_at(main, mi, SHOT_LEN)
    b, at_b = shot_at(body, bi, SHOT_LEN)
    print(f"    {main} #{mi} at {at_a / SR:.2f} s + {body.split('/')[-1]} #{bi} at {at_b / SR:.2f} s")
    a = squash(highpass(a, 35), SHOT_SQUASH_DB)
    b = squash(highpass(b, 35), SHOT_SQUASH_DB + 2)
    # The .45's body sits under the revolver's crack: darker, a hair later (2 ms).
    b = np.roll(lowpass(b, 3500, 2), int(0.002 * SR), axis=0)
    real = normalize(a, -1.0) + normalize(b, -1.0) * body_gain
    duck = np.ones(len(real))
    d0, d1 = int(0.06 * SR), int(0.14 * SR)
    duck[d0:d1] = np.linspace(1.0, 10 ** (-ECHO_DUCK_DB / 20), d1 - d0)
    duck[d1:] = 10 ** (-ECHO_DUCK_DB / 20)
    real = normalize(real * duck[:, None], -1.0)
    # Meat: the blast's 150-250 Hz pushed (what a phone can play of the low end),
    # its own lows saturated, and one chest thump.
    real = peaking(real, 190, 5.0, 0.9)
    low = np.tanh(lowpass(real, 170, 2) * 3.2) * 0.6
    mix = real + low + thump(len(real)) * 0.38
    mix = np.tanh(mix * 1.45) / np.tanh(1.45)
    return fade(mix, 0.0005, 0.35)


def build_tail():
    x, a = shot_at("oga_Prepared_SFX_Library/*1917__B_16P.wav", 1, 2.7)
    seg = lowpass(x, 2600, 2)
    env = np.ones(len(seg))
    k = int(0.15 * SR)
    env[:k] = np.linspace(0, 1, k) ** 2  # the shot itself plays the first moments
    return fade(seg * env[:, None], 0.0, 0.9)


def main():
    print(".44 Magnum from recordings:")
    for v, s in enumerate(SHOTS, 1):
        save(f"magnum44_shot_{v}", build_shot(*s), -0.3)
    save("magnum44_tail_1", build_tail(), -3.0)
    # Cylinder latch and the crane swinging out.
    save("magnum44_reload_start_1", fade(cut("fs_177863_*.mp3", 0.27, 0.68), 0.002, 0.06), -4.0)
    # Ejector rod slapped, the cases raining down (pitched a fifth down: .44 brass).
    ej = pitch(cut("fs_693125_*.mp3", 0.03, 1.25), 1.5)
    save("magnum44_mag_out_1", fade(peaking(ej, 300, 3.0, 0.8), 0.001, 0.25), -2.0)
    # Speedloader: the rounds ringing into the chambers, the loader's knob turned.
    sl = pitch(cut("fs_722902_*.mp3", 1.36, 1.78), 1.12)
    save("magnum44_mag_in_1", fade(sl, 0.001, 0.08), -2.5)
    # Cylinder snapped shut (two takes).
    save("magnum44_slide_release_1", fade(pitch(cut("fs_677159_*.mp3", 0.26, 0.64), 1.2), 0.001, 0.08), -1.0)
    save("magnum44_slide_release_2", fade(pitch(cut("fs_722902_*.mp3", 2.22, 2.56), 1.15), 0.001, 0.08), -1.5)
    # The hammer falling on an empty chamber.
    save("magnum44_dry_fire_1", fade(cut("fs_508745_*.mp3", 4.56, 4.82), 0.001, 0.05), -6.0)
    save("magnum44_reload_cancel_1", fade(pitch(cut("fs_677159_*.mp3", 0.07, 0.24), 1.2), 0.001, 0.04), -8.0)


if __name__ == "__main__":
    main()
