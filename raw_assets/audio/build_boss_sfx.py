#!/usr/bin/env python3
"""Synthesizes the Incense Master's sounds and the execution's (docs/design.md §8.7a, §8.7b). No third-party
audio: the roar is built over this project's own synthesized death scream (build_voice_sfx.py), pitched an
octave down and run through a growl; everything else is noise, oscillators and filters.

- boss_roar: a huge chest roar: the scream slowed and lowered, a 60-110 Hz vocal-fold growl under it with
  rough formants, distortion. Plays as he spreads his arms in the entrance.
- boss_pound: the prosthetic into the ground: a crack, a body of concrete crunch, a sub drop, a metal clank
  of the arm, debris pattering down.
- boss_land: the landing from the roof: like the pound, longer and lower, with a knee-and-boots thud.
- boss_charge: the Gauss arm charging (about 1.6 s): a whine climbing 180 Hz -> 2.6 kHz with a tremolo that
  speeds up and a crackle that grows; the shot itself is the GX-4's (gx4_shot).
- boss_swing: the haymaker's whoosh: a heavy servo and air.
- boss_flex: the coils lighting in the entrance: a servo, a hum swelling, two capacitor ticks.
- exec_grab: the left hand taking his collar: leather creak and a suit servo.
- exec_punch x3: a fist into a face: a low thud, a slap, bone crunch and a wet squelch.
- exec_skull: the last punch: the head going: a big crunch, a wet burst, a thud.
- exec_flick x2: blood flicked off the fist: a short wet splat with a whoosh.

Usage: python3 raw_assets/audio/build_boss_sfx.py [out_dir]
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402
import build_gauss_sfx as g  # noqa: E402

w.rng = np.random.default_rng(1115)
g.rng = w.rng
w.REPLACED = set()
SR = w.SR
rng = w.rng
HERE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.join(HERE, "..", "..", "assets", "audio", "sfx")


def load(name):
    sr, x = wavfile.read(os.path.join(SFX, name + ".wav"))
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    x /= np.max(np.abs(x)) + 1e-9
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    return x


def repitch(x, factor):
    """Plays `x` `factor` times as fast (lower pitch and longer when < 1)."""
    n = int(len(x) / factor)
    return np.interp(np.arange(n) * factor, np.arange(len(x)), x)


def formant(x, centres, q=6.0):
    out = np.zeros_like(x)
    for f, a in centres:
        out += w.band(x, f / (1 + 1 / q), f * (1 + 1 / q)) * a
    return out


def roar():
    sec = 2.3
    n = int(sec * SR)
    scream = repitch(load("death_scream_2"), 0.52)[:n]
    scream = np.pad(scream, (0, n - len(scream)))
    # Vocal folds: a jittered sawtooth gliding 70 -> 108 -> 72 Hz, rough at the edges.
    shape = np.interp(np.arange(n) / SR, [0.0, 0.5, 1.7, sec], [70.0, 108.0, 96.0, 72.0])
    f0 = shape * (1 + 0.24 * np.convolve(rng.standard_normal(n), np.ones(400) / 400, "same"))
    folds = g.saw(f0) + 0.5 * g.saw(f0 * 0.5 * 1.003)
    growl = formant(folds, [(320, 1.0), (720, 0.8), (1150, 0.45), (2500, 0.25)])
    growl = growl + w.band(rng.standard_normal(n), 300, 3500) * 0.25
    rough = 1 + 0.5 * np.sin(2 * np.pi * 31.0 * np.arange(n) / SR)
    env = np.minimum(np.arange(n) / (0.08 * SR), 1.0) * np.minimum((n - np.arange(n)) / (0.7 * SR), 1.0)
    chest = w.band(rng.standard_normal(n), 50, 220) * env * 0.8
    out = growl * rough * env + w.band(scream, 120, 5000) * 0.9 + chest
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.8, 2.2)


def impact(sec, sub_from, sub_to, body_decay, crunch=1.0, clank=1.0):
    crack = w.band(w.noise(0.07), 900, 12000) * w.env(0.07, 0.0002, 0.01)
    body = w.band(w.noise(0.8), 50, 1400) * w.env(0.8, 0.001, body_decay)
    sub = g.sine(g.glide(1.2, sub_from, sub_to, 0.6)) * w.env(1.2, 0.002, 0.3)
    grit = g.crackle(0.9, 0.05, 700, 8000, 0.18) * 0.7 * crunch
    metal = w.band(w.noise(0.25), 400, 2600) * w.env(0.25, 0.0005, 0.04) * 0.5 * clank
    debris = w.at(sec, *[(0.15 + 0.12 * k + rng.uniform(0, 0.08), w.band(w.noise(0.05), 1200, 7000) * w.env(0.05, 0.0005, 0.012) * rng.uniform(0.1, 0.3)) for k in range(9)])
    out = w.at(sec, (0.0, crack * 1.4), (0.0, body * 2.2), (0.0, sub * 2.6), (0.01, grit), (0.0, metal), (0.0, debris))
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.5, 1.6)


def charge():
    sec = 1.6
    f = g.glide(sec, 180, 2600, 1.6)
    trem_rate = g.glide(sec, 6, 38, 1.2)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(trem_rate) / SR)
    tone = (g.sine(f) * 0.7 + w.band(g.saw(f * 0.5), 200, 7000) * 0.35) * trem
    rise = np.linspace(0.15, 1.0, len(f)) ** 1.5
    crack = g.crackle(sec, 0.004, 2000, 10000, 9.0) * np.linspace(0, 1, len(f)) ** 2 * 2.0
    hum = g.sine(np.full(len(f), 60.0)) * 0.25 + g.sine(np.full(len(f), 120.0)) * 0.15
    return (tone * rise + crack + hum) * np.minimum((len(f) - np.arange(len(f))) / (0.02 * SR), 1.0)


def swing():
    sec = 0.6
    air = w.band(w.noise(sec), 120, 1400) * (np.sin(np.pi * np.linspace(0, 1, int(sec * SR))) ** 2)
    srv = g.servo(0.35, 260, 140, 0.6)
    return w.at(sec, (0.0, srv), (0.08, air * 1.6))


def flex():
    sec = 1.3
    srv = g.servo(0.5, 160, 420, 0.8)
    hum = g.sine(g.glide(1.1, 90, 240, 0.8)) * np.linspace(0, 1, int(1.1 * SR)) ** 1.4 * 0.6
    tick = g.clack(0.03, 2000, 9000, 0.004)
    return w.at(sec, (0.0, srv), (0.15, hum), (0.55, tick), (0.75, tick * 0.8))


def grab():
    sec = 0.4
    creak = w.band(w.noise(0.25), 500, 4000) * w.env(0.25, 0.01, 0.05)
    srv = g.servo(0.2, 300, 520, 0.4)
    return w.at(sec, (0.0, creak), (0.02, srv))


def punch(v):
    sec = 0.55
    thud = w.band(w.noise(0.2), 40, 380) * w.env(0.2, 0.001, 0.05 + 0.01 * v)
    slap = w.band(w.noise(0.06), 700, 4500) * w.env(0.06, 0.0003, 0.008)
    crunch = g.crackle(0.12, 0.08, 1500, 9000, 0.03) * (0.6 + 0.3 * v)
    squelch = w.band(w.noise(0.3), 200, 1600) * w.env(0.3, 0.004, 0.06) * (1 + np.sin(2 * np.pi * 23 * w.t(0.3))) * 0.4
    out = w.at(sec, (0.0, thud * 2.4), (0.0, slap * 1.3), (0.004, crunch), (0.02, squelch))
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.4, 1.5)


def skull():
    sec = 1.4
    crunch = g.crackle(0.25, 0.12, 900, 10000, 0.07) * 1.4
    burst = w.band(w.noise(0.6), 150, 3000) * w.env(0.6, 0.002, 0.12) * (1 + 0.6 * np.sin(2 * np.pi * 17 * w.t(0.6)))
    thud = w.band(w.noise(0.35), 30, 300) * w.env(0.35, 0.001, 0.09)
    drip = w.at(sec, *[(0.3 + 0.1 * k + rng.uniform(0, 0.06), w.band(w.noise(0.04), 600, 3500) * w.env(0.04, 0.0005, 0.01) * rng.uniform(0.1, 0.35)) for k in range(9)])
    out = w.at(sec, (0.0, crunch), (0.0, burst * 1.8), (0.0, thud * 2.5), (0.0, drip))
    return g.soft_clip(out / (np.max(np.abs(out)) + 1e-9) * 1.4, 1.5)


def flick(v):
    sec = 0.35
    whoosh = w.band(w.noise(0.2), 300, 2000) * np.sin(np.pi * np.linspace(0, 1, int(0.2 * SR))) ** 2 * 0.5
    splat = w.at(0.2, *[(0.01 * k, w.band(w.noise(0.05), 400, 3000) * w.env(0.05, 0.0005, 0.012) * rng.uniform(0.4, 1.0)) for k in range(3 + v)])
    return w.at(sec, (0.0, whoosh), (0.09, splat * 1.6))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("boss_roar_1", roar(), -0.5)
    w.save("boss_pound_1", impact(2.0, 70, 22, 0.2), -0.3)
    w.save("boss_land_1", impact(2.4, 55, 18, 0.28, crunch=1.3, clank=0.6), -0.3)
    w.save("boss_charge_1", charge(), -2)
    w.save("boss_swing_1", swing(), -3)
    w.save("boss_flex_1", flex(), -3)
    w.save("exec_grab_1", grab(), -4)
    for v in (1, 2, 3):
        w.save(f"exec_punch_{v}", punch(v), -0.5)
    w.save("exec_skull_1", skull(), -0.3)
    for v in (1, 2):
        w.save(f"exec_flick_{v}", flick(v), -4)
    print("wrote the boss sounds to", out)


if __name__ == "__main__":
    write_all()
