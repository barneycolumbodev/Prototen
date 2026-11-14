#!/usr/bin/env python3
"""Synthesizes the LC-6 Lorentz Catcher's sounds (2026-11-13; no third-party audio, see CREDITS.md).

What the hardware would sound like:
- deploy: the drive ring's servo, eight petals swinging forward and locking one after another (clacks), and the
  coils charging: a rising electrical whine that settles into the field's hum.
- stow: the whine falling away, the petals folding back (quick clacks), a servo down, a seat.
- loop: the field (seamless 2 s): a transformer hum with its harmonics, beating slowly as the pulses run, a faint
  crackle of the air in the field.
- catch x4: a round arriving: its crack cut short, a fast falling "zeew" as the eddy currents brake it, a sizzle as
  it heats, a small metallic tink as it settles.
- full: a low double tone (the field can't take more).
- release: the coils firing as a coilgun: a ring of eight snaps in a few milliseconds, a heavy magnetic thump with a
  sub boom, a rising whine that breaks into a crack, then the rounds' supersonic cracks going away.
- zip x3: one returned round going away (played on a few of them).

Files (Sfx banks): lc6_deploy, lc6_stow, lc6_loop (loop), lc6_catch_1..4, lc6_full, lc6_release, lc6_zip_1..3.
Shares helpers with build_weapon_sfx.py and build_gauss_sfx.py.

Usage: python3 raw_assets/audio/build_catcher_sfx.py [out_dir]
lc6_loop needs edit/loop_mode=2 in its .import file.
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402
import build_gauss_sfx as g  # noqa: E402

w.rng = np.random.default_rng(1114)
g.rng = w.rng
w.REPLACED = set()
SR = w.SR
rng = w.rng


def swell(sec, power=1.0):
    return np.sin(np.pi * np.linspace(0, 1, int(sec * SR))) ** power


def ramp(sec, a, b):
    return np.linspace(a, b, int(sec * SR))


def whine(sec, f0, f1, curve=1.0):
    """A coil charging: a sine and its third and fifth, gliding."""
    f = g.glide(sec, f0, f1, curve)
    return g.sine(f) + 0.35 * g.sine(f * 3.0) + 0.15 * g.sine(f * 5.0)


def deploy():
    sec = 0.9
    parts = [(0.0, g.servo(0.3, 300, 520, 0.4)),
             (0.05, whine(0.6, 180, 1300, 0.7) * ramp(0.6, 0.0, 1.0) ** 2 * w.env(0.6, 0.15, 0.4) * 0.16)]
    for k in range(8):
        off = 0.04 + k * 0.024
        parts.append((off, g.clack(0.03, 900, 7000, 0.003) * (0.3 + 0.03 * k)))
        parts.append((off + 0.012, g.thunk(0.05, 120, 900, 0.01) * 0.18))
    parts.append((0.3, g.mix(g.thunk(0.09, 70, 600, 0.02) * 0.5, g.clack(0.03, 1500, 8000, 0.002) * 0.45)))
    hum = (g.sine(np.full(int(0.5 * SR), 100.0)) + 0.4 * g.sine(np.full(int(0.5 * SR), 200.0))) * swell(0.5, 0.5) * 0.12
    parts.append((0.38, hum))
    return w.at(sec, *parts)


def stow():
    sec = 0.6
    parts = [(0.0, whine(0.3, 900, 120, 1.5) * w.env(0.3, 0.005, 0.12) * 0.12), (0.02, g.servo(0.28, 480, 260, 0.35))]
    for k in range(8):
        parts.append((0.05 + k * 0.016, g.clack(0.025, 900, 6000, 0.003) * 0.25))
    parts.append((0.3, g.mix(g.thunk(0.09, 70, 600, 0.02) * 0.55, g.clack(0.03, 900, 6000, 0.003) * 0.4)))
    return w.at(sec, *parts)


def loop():
    """Seamless 2 s: 100 Hz and harmonics (whole cycles), a slow beat, a crackle crossfaded over the seam."""
    sec = 2.0
    n = int(sec * SR)
    t = np.arange(n) / SR
    beat = 0.75 + 0.25 * np.sin(2 * np.pi * 2.0 * t)  # 4 beats in 2 s
    hum = (np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 200 * t) + 0.25 * np.sin(2 * np.pi * 300 * t)
           + 0.12 * np.sin(2 * np.pi * 700 * t)) * beat * 0.12
    pad = int(0.25 * SR)
    cr = g.crackle(sec + 0.25, 0.0012, 2000, 9000, 0.004) * 0.12
    body, tail = cr[:n].copy(), cr[n:n + pad]
    fade = np.linspace(0, 1, pad)
    body[:pad] = body[:pad] * fade + tail * (1 - fade)
    air = w.band(w.noise(sec + 0.25), 3000, 9000) * 0.02
    a_body, a_tail = air[:n].copy(), air[n:n + pad]
    a_body[:pad] = a_body[:pad] * fade + a_tail * (1 - fade)
    return hum + body + a_body


def catch(v):
    sec = 0.32
    crack = w.band(w.noise(0.012), 2500, 15000) * w.env(0.012, 0.0002, 0.003) * 0.7
    f0 = 3800 + 500 * v
    zeew = w.band(g.sine(g.glide(0.13, f0, 420 + 60 * v, 0.5)), 300, 9000) * w.env(0.13, 0.002, 0.05) * 0.45
    sizzle = w.band(w.noise(0.2), 4000, 12000) * w.env(0.2, 0.01, 0.07) * 0.18
    tink = w.partials(0.12, [2900 + 300 * v, 4700 + 200 * v, 7100], [0.03, 0.02, 0.012], [0.4, 0.25, 0.12])
    return w.at(sec, (0.0, crack), (0.004, zeew), (0.02, sizzle), (0.1, tink * 0.35))


def full():
    sec = 0.3
    tone = w.band(g.sine(np.full(int(0.08 * SR), 330.0)) + 0.4 * g.sine(np.full(int(0.08 * SR), 495.0)), 200, 3000) * w.env(0.08, 0.004, 0.03)
    return w.at(sec, (0.0, tone * 0.5), (0.12, tone * 0.45))


def zip_(v):
    sec = 0.5
    crack = w.band(w.noise(0.01), 2000, 16000) * w.env(0.01, 0.0001, 0.002) * 0.9
    f0 = 7000 + 900 * v
    z = w.band(g.sine(g.glide(0.3, f0, f0 * 0.45, 0.6)), 1500, 14000) * w.env(0.3, 0.002, 0.1) * 0.35
    air = w.band(w.noise(0.35), 3000, 14000) * w.env(0.35, 0.001, 0.08) * 0.35
    return w.at(sec, (0.0, crack), (0.003, z), (0.0, air))


def release():
    sec = 1.6
    parts = []
    # Eight coils dumping their capacitors in a few milliseconds.
    for k in range(8):
        parts.append((k * 0.0035, w.band(w.noise(0.012), 1200, 14000) * w.env(0.012, 0.0002, 0.003) * 0.6))
    parts.append((0.0, g.thunk(0.22, 35, 300, 0.06) * 1.1))
    parts.append((0.0, g.sine(g.glide(0.5, 110, 32)) * w.env(0.5, 0.003, 0.16) * 0.9))
    parts.append((0.0, whine(0.12, 600, 5200, 0.5) * w.env(0.12, 0.01, 0.04) * 0.18))
    parts.append((0.035, w.band(w.noise(0.05), 800, 12000) * w.env(0.05, 0.0005, 0.012) * 0.9))
    # The rounds going out: a ripple of supersonic cracks fanning away.
    for k in range(26):
        off = 0.03 + 0.15 * (k / 26) + rng.uniform(-0.006, 0.006)
        parts.append((off, zip_(rng.integers(1, 4)) * rng.uniform(0.25, 0.5)))
    parts.append((0.05, w.band(w.noise(1.2), 120, 900) * w.env(1.2, 0.02, 0.35) * 0.25))
    return g.soft_clip(w.at(sec, *parts), 1.3)


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    w.save("lc6_deploy_1", deploy(), -3)
    w.save("lc6_stow_1", stow(), -5)
    x = loop()
    x = x - np.mean(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (-10 / 20)
    wavfile.write(os.path.join(out, "lc6_loop_1.wav"), SR, (x * 32767).astype(np.int16))
    for v in (1, 2, 3, 4):
        w.save(f"lc6_catch_{v}", catch(v), -4)
    w.save("lc6_full_1", full(), -8)
    w.save("lc6_release_1", release(), -0.5)
    for v in (1, 2, 3):
        w.save(f"lc6_zip_{v}", zip_(v), -6)
    print("wrote the LC-6's sounds to", out)


if __name__ == "__main__":
    write_all()
