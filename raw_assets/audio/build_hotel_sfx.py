#!/usr/bin/env python3
"""Synthesizes the Golden Dragon hotel's sounds (no third-party audio; see CREDITS.md).

Loops (seamless; noise shaped in the frequency domain so it wraps):
- amb_lobby_music: the lobby's ceiling speakers still play: a slow
  pentatonic air on a guzheng-like pluck over a warm electric-piano pad,
  a soft wood block, all through small ceiling speakers. Polite, a little
  sad, in an empty building.
- amb_bar_music: the Dragon Bar: a slow lounge loop (upright bass walking,
  soft Rhodes seventh chords, brushed hi-hat), muffled behind the bar.
- amb_fountain: water falling into the basin, bubbling and trickling.
- amb_hum: the service corridor: fluorescent ballast hum and an air handler.
One-shots:
- lift_ding: the arrival chime (a two-tone bell, down a major third).
- lift_door: the doors running on their track: a motor whine, the rumble
  of the hangers, a soft thump as they meet the stops.

Usage: python3 raw_assets/audio/build_hotel_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out_arg = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "assets", "audio", "sfx")
sys.argv = sys.argv[:1]
import build_ambience as amb  # noqa: E402
import build_weapon_sfx as w  # noqa: E402

amb.OUT = out_arg
w.OUT = out_arg
SR = amb.SR
rng = np.random.default_rng(1888)
amb.rng = rng


def speaker(x, lo=180.0, hi=6000.0, drive=1.6):
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4) / (1 + (f / hi) ** 4)
    y = np.fft.irfft(spec, n)
    y = y / (np.abs(y).max() + 1e-9)
    return np.tanh(y * drive) / np.tanh(drive)


def room(x, delays=(0.031, 0.047, 0.073, 0.11, 0.17, 0.26), decay=0.45):
    """Cheap circular reverb (wraps, so loops stay seamless)."""
    y = x.copy()
    for i, d in enumerate(delays):
        y += np.roll(x, int(d * SR)) * decay ** (i + 1) * (1 if i % 2 else -1)
    return y


def epiano(freq, dur, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    tone = np.sin(2 * np.pi * freq * t + 0.8 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 3)) * np.exp(-t * 1.2)
    tine = np.sin(2 * np.pi * freq * 4.0 * t) * np.exp(-t * 9) * 0.25
    att = np.clip(t / 0.004, 0, 1)
    return (tone + tine) * att * vel


def lobby_music(sec=32.0):
    n = int(sec * SR)
    buf = np.zeros(n)
    # A minor pentatonic-ish (A C D E G), slow: one beat = 0.75 s.
    scale = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25, 587.33, 659.25]
    beat = 0.75
    melody = [(0, 5, 2), (2, 6, 1), (3, 7, 1), (4, 6, 2), (6, 4, 1), (7, 5, 3),
              (10, 3, 1), (11, 4, 1), (12, 5, 2), (14, 3, 1), (15, 2, 1), (16, 3, 4),
              (20, 5, 1), (21, 7, 1), (22, 8, 2), (24, 7, 1), (25, 6, 1), (26, 5, 2), (28, 4, 1), (29, 3, 1), (30, 2, 2),
              (32, 1, 1), (33, 2, 1), (34, 3, 2), (36, 2, 1), (37, 0, 5)]
    for b, note, d in melody:
        x = amb.pluck(scale[note], d * beat * 0.6 + 0.8)
        amb.place(buf, int(b * beat * SR), x * 0.55)
        if d >= 2:  # guzheng tremolo on long notes
            for r in range(1, 5):
                amb.place(buf, int((b * beat + r * 0.11) * SR), amb.pluck(scale[note], 0.35) * 0.12)
    # Pad: Am - F - C - G, one chord per 8 beats.
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
    for i, ch in enumerate(chords * 2):
        start = i * 8 * beat
        if start >= sec:
            break
        for f in ch:
            amb.place(buf, int(start * SR), epiano(f, 8 * beat + 1.0, 0.16))
    # A wood block on beats 1 and 3 of every bar, very soft.
    for b in range(0, int(sec / beat), 4):
        t = np.arange(int(0.08 * SR)) / SR
        blk = np.sin(2 * np.pi * 900 * t) * np.exp(-t * 70)
        amb.place(buf, int(b * beat * SR), blk * 0.08)
    x = room(buf)
    return speaker(x, 220, 5500) * 0.8 + amb.shaped_noise(sec, 3000, 9000) * 0.006


def bar_music(sec=24.0):
    n = int(sec * SR)
    buf = np.zeros(n)
    beat = 60 / 72
    roots = [146.83, 196.0, 130.81, 110.0]  # Dm7 G7 Cmaj7 A7
    chord_tones = [(293.66, 349.23, 440.0, 523.25), (293.66, 349.23, 392.0, 493.88), (261.63, 329.63, 392.0, 493.88),
                   (277.18, 329.63, 392.0, 440.0)]
    nbars = int(sec / (4 * beat))
    for bar in range(nbars):
        c = bar % 4
        t0 = bar * 4 * beat
        for f in chord_tones[c]:
            amb.place(buf, int((t0 + 0.02) * SR), epiano(f, 4 * beat, 0.12))
            amb.place(buf, int((t0 + 2.5 * beat) * SR), epiano(f, 1.4 * beat, 0.06))
        walk = [roots[c], roots[c] * 1.25, roots[c] * 1.5, roots[c] * 1.335]
        for i, f in enumerate(walk):
            t = np.arange(int(beat * SR)) / SR
            b = np.sin(2 * np.pi * f / 2 * t) * np.exp(-t * 3.5) * np.clip(t / 0.01, 0, 1)
            amb.place(buf, int((t0 + i * beat) * SR), b * 0.4)
        for i in range(8):
            hh = amb.shaped_noise(0.12, 5000, 12000)[: int(0.12 * SR)] * np.exp(-np.arange(int(0.12 * SR)) / SR * 30)
            amb.place(buf, int((t0 + i * beat / 2 + (0.08 if i % 2 else 0)) * SR), hh * (0.05 if i % 2 else 0.03))
    x = room(buf, decay=0.35)
    return speaker(x, 120, 3200, 1.3) * 0.8


def fountain(sec=10.0):
    base = amb.shaped_noise(sec, 300, 9000, -0.4) * 0.5
    n = int(sec * SR)
    gurgle = np.zeros(n)
    for _ in range(140):
        f0 = rng.uniform(500, 1600)
        d = rng.uniform(0.02, 0.07)
        t = np.arange(int(d * SR)) / SR
        f = f0 * (1 + 1.2 * t / d)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 2
        amb.place(gurgle, int(rng.uniform(0, sec) * SR), b * rng.uniform(0.1, 0.35))
    splash = amb.shaped_noise(sec, 1200, 7000) * amb.periodic_env(n, 0.7, 0.4) * 0.3
    return base + gurgle + splash


def hum(sec=6.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    mains = sum(np.sin(2 * np.pi * 50 * h * t + h) / h ** 1.2 for h in range(1, 9)) * 0.25
    buzz = amb.shaped_noise(sec, 90, 600) * 0.3 * (0.8 + 0.2 * np.sin(2 * np.pi * 100 * t))
    air = amb.shaped_noise(sec, 40, 900, -0.8) * 0.6
    return mains + buzz + air


def ding():
    sec = 2.2

    def bell(f, start):
        x = w.partials(sec - start, (f, f * 2.0, f * 2.76, f * 5.4), (0.9, 0.45, 0.25, 0.08), (1.0, 0.45, 0.25, 0.12), 0.002)
        x *= np.clip(w.t(sec - start) / 0.002, 0, 1)
        return x
    return w.at(sec, (0.0, bell(987.77, 0.0)), (0.32, bell(783.99, 0.32) * 0.9))


def door():
    sec = 1.5
    tt = w.t(sec)
    motor = np.sin(2 * np.pi * np.cumsum(140 + 60 * np.sin(np.pi * tt / sec)) / SR) * 0.15
    rumble = w.band(w.noise(sec), 60, 500) * np.sin(np.pi * np.clip(tt / 1.2, 0, 1)) ** 0.7 * 0.6
    track = w.band(w.noise(sec), 1500, 5000) * np.sin(np.pi * np.clip(tt / 1.2, 0, 1)) * 0.08
    thump = w.band(w.noise(0.15), 50, 400) * w.env(0.15, 0.002, 0.03)
    clk = w.click(0.05, (1200, 2300, 3700), 0.01, bright=1500)
    return w.at(sec, (0.0, motor + rumble + track), (1.15, thump * 1.5), (1.16, clk * 0.4))


if __name__ == "__main__":
    os.makedirs(out_arg, exist_ok=True)
    amb.save("amb_lobby_music", lobby_music(), -4.0)
    amb.save("amb_bar_music", bar_music(), -4.0)
    amb.save("amb_fountain", fountain(), -6.0)
    amb.save("amb_hum", hum(), -8.0)
    w.save("lift_ding_1", ding(), -3.0)
    w.save("lift_door_1", door(), -4.0)
    print("hotel sounds written to", out_arg)
