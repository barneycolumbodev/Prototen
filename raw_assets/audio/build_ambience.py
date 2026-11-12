#!/usr/bin/env python3
"""Synthesizes the Chinatown docks ambience (no third-party audio; see CREDITS.md).

Seamless loops (noise is shaped in the frequency domain, so it wraps):
- amb_rain: steady rain on a city street: hiss, patter, drips from gutters.
- amb_harbour: water slapping the quay and hulls, a creaking mooring line,
  one distant ship's horn per loop.
- amb_neon: transformer hum and buzz of a neon sign (positional).
- amb_exhaust: a kitchen extractor fan with a wobbly bearing (positional).
- amb_radio: a small radio in the restaurant: a plucked pentatonic melody
  (Karplus-Strong, zither-like) over a soft drone, band-limited like a cheap
  speaker, with a little static.

Usage: python3 raw_assets/audio/build_ambience.py [out_dir]  (default assets/audio/sfx)
Godot imports these with loop_mode=forward (see the .import files).
"""
import os
import sys
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(2026)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio", "sfx")


def shaped_noise(sec, lo, hi, tilt=0.0):
    """Periodic band-limited noise: loops without a seam."""
    n = int(sec * SR)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    gain = ((f >= lo) & (f <= hi)).astype(float)
    gain *= np.where(f > 0, (np.maximum(f, 1) / 1000.0) ** tilt, 0)
    # soft edges
    gain *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4) * 1 / (1 + (f / hi) ** 4)
    x = np.fft.irfft(spec * gain, n)
    return x / (np.abs(x).max() + 1e-9)


def periodic_env(n, rate_hz, depth, seed_phase=0.0):
    t = np.arange(n) / SR
    return 1 - depth * (0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * t + seed_phase))


def place(buf, start, x):
    """Add x into a looping buffer (wraps around the end)."""
    n = len(buf)
    idx = (np.arange(len(x)) + start) % n
    np.add.at(buf, idx, x)


def drip(sec=0.08, f0=1800):
    t = np.arange(int(sec * SR)) / SR
    f = f0 * (1 + 0.8 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 55)


def rain(sec=12.0):
    n = int(sec * SR)
    hiss = shaped_noise(sec, 1200, 12000, -0.3) * 0.35
    body = shaped_noise(sec, 250, 2500) * 0.25 * periodic_env(n, 1 / sec, 0.2)
    buf = hiss + body
    # patter: thousands of tiny ticks on hard surfaces
    tick = shaped_noise(0.004, 2000, 9000)[: int(0.004 * SR)] * np.exp(-np.arange(int(0.004 * SR)) / SR * 900)
    for _ in range(int(sec * 260)):
        place(buf, int(rng.integers(0, n)), tick * rng.uniform(0.05, 0.25))
    # gutter drips: a few regular ones
    for k, period in enumerate((0.73, 1.37, 2.9)):
        t0 = rng.uniform(0, period)
        while t0 < sec:
            place(buf, int(t0 * SR), drip(f0=1300 + 600 * k) * 0.12)
            t0 += period * rng.uniform(0.95, 1.05)
    return buf


def harbour(sec=24.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    low = shaped_noise(sec, 60, 700) * 0.5
    # slaps: swells that rise and fall against the quay
    swell = np.zeros(n)
    t0 = 0.3
    while t0 < sec:
        d = rng.uniform(0.5, 1.1)
        seg = np.arange(int(d * SR)) / SR
        shape = np.sin(np.pi * seg / d) ** 2 * (1 - np.exp(-seg * 8))
        slap = shaped_noise(d, 180, 2200)[: len(seg)] * shape
        place(swell, int(t0 * SR), slap * rng.uniform(0.4, 0.9))
        t0 += rng.uniform(1.2, 2.6)
    buf = low * periodic_env(n, 2 / sec, 0.4) + swell * 0.7
    # mooring line creak, twice per loop
    for at in (5.0, 16.5):
        d = 0.9
        seg = np.arange(int(d * SR)) / SR
        f = 210 + 40 * np.sin(2 * np.pi * 1.3 * seg)
        saw = (np.cumsum(f) / SR) % 1.0 * 2 - 1
        cr = saw * (0.5 + 0.5 * (shaped_noise(d, 20, 80)[: len(seg)] > 0)) * np.sin(np.pi * seg / d) ** 2
        place(buf, int(at * SR), cr * 0.06)
    # a ship's horn far away across the bay: two low tones, long tail
    d = 4.5
    seg = np.arange(int(d * SR)) / SR
    tone = sum(np.sin(2 * np.pi * f * seg) / (i + 1) for i, f in enumerate((73.4, 110.0, 146.8, 220.0)))
    env = np.minimum(seg / 0.4, 1) * np.where(seg < 3.0, 1.0, np.exp(-(seg - 3.0) * 2.0))
    horn = tone * env
    # muffle with distance: simple one-pole low-pass
    y = np.zeros_like(horn)
    a = 0.08
    for i in range(1, len(horn)):
        y[i] = y[i - 1] + a * (horn[i] - y[i - 1])
    place(buf, int(11.0 * SR), y * 0.5)
    return buf


def neon(sec=6.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    hum = np.sin(2 * np.pi * 120 * t) * 0.5 + np.sin(2 * np.pi * 240 * t) * 0.25 + np.sin(2 * np.pi * 360 * t) * 0.1
    buzz = np.sign(np.sin(2 * np.pi * 120 * t)) * shaped_noise(sec, 2000, 6000) * 0.12
    flick = periodic_env(n, 0.5, 0.15)
    return (hum + buzz) * flick


def exhaust(sec=8.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    air = shaped_noise(sec, 150, 3500) * 0.6
    rot = 24.75  # rotor (an integer number of turns per loop keeps it seamless)
    blade = (0.6 + 0.4 * np.sin(2 * np.pi * rot * t)) * shaped_noise(sec, 80, 400) * 0.6
    motor = np.sin(2 * np.pi * 99.0 * t) * 0.12 + np.sin(2 * np.pi * 198.0 * t) * 0.05
    rattle = (np.sin(2 * np.pi * rot / 2 * t) > 0.97) * shaped_noise(sec, 1500, 5000) * 0.25
    return air + blade + motor + rattle


def pluck(freq, dur):
    """Karplus-Strong: a zither-ish plucked string."""
    n = int(dur * SR)
    period = int(SR / freq)
    buf = rng.uniform(-1, 1, period)
    out = np.zeros(n)
    for i in range(n):
        v = buf[i % period]
        out[i] = v
        buf[i % period] = 0.996 * 0.5 * (v + buf[(i + 1) % period])
    return out * np.exp(-np.arange(n) / SR * 1.5)


def radio(sec=16.0):
    n = int(sec * SR)
    # D major pentatonic, two phrases
    scale = [293.66, 329.63, 369.99, 440.0, 493.88, 587.33, 659.25]
    phrase = [(0, 3, 0.5), (0.5, 4, 0.5), (1.0, 5, 1.0), (2.0, 4, 0.5), (2.5, 3, 0.5), (3.0, 2, 1.0), (4.0, 1, 0.5), (4.5, 2, 0.5),
              (5.0, 3, 1.5), (6.5, 2, 0.5), (7.0, 0, 1.0),
              (8.0, 5, 0.5), (8.5, 6, 0.5), (9.0, 5, 0.5), (9.5, 4, 0.5), (10.0, 3, 1.0), (11.0, 4, 0.5), (11.5, 2, 0.5), (12.0, 3, 1.0),
              (13.0, 1, 0.5), (13.5, 2, 0.5), (14.0, 0, 2.0)]
    buf = np.zeros(n)
    for beat, note, dur in phrase:
        x = pluck(scale[note], dur * 0.5 + 0.6)
        place(buf, int(beat * 0.5 * SR * 2), x * 0.5)
        # tremolo-ish repeat on long notes, like a guzheng
        if dur >= 1.0:
            for r in range(1, 4):
                place(buf, int((beat * 0.5 * 2 + r * 0.12) * SR), pluck(scale[note], 0.4) * 0.15)
    t = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * 146.83 * t) + 0.5 * np.sin(2 * np.pi * 220.0 * t)) * 0.05
    x = buf + drone
    # cheap speaker: band-pass 400..3500 Hz in the frequency domain (periodic)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / (1 + (400 / np.maximum(f, 1)) ** 4) / (1 + (f / 3500) ** 4)
    x = np.fft.irfft(spec, n)
    x = np.tanh(x * 2.5) * 0.6
    return x + shaped_noise(sec, 3000, 9000) * 0.02


def save(name, x, peak_db=-3.0):
    x = x / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((x * 32767).astype(np.int16).tobytes())
    imp = path + ".import"
    if not os.path.exists(imp):
        with open(imp, "w") as f:
            f.write('[remap]\n\nimporter="wav"\ntype="AudioStreamWAV"\n\n[params]\n\nforce/8_bit=false\nforce/mono=false\n'
                    'force/max_rate=true\nforce/max_rate_hz=22050\nedit/trim=false\nedit/normalize=false\nedit/loop_mode=2\n'
                    'edit/loop_begin=0\nedit/loop_end=-1\ncompress/mode=2\n')
    print("wrote", path)


if __name__ == "__main__":
    save("amb_rain", rain())
    save("amb_harbour", harbour())
    save("amb_neon", neon(), -6.0)
    save("amb_exhaust", exhaust())
    save("amb_radio", radio())
