#!/usr/bin/env python3
"""Synthesizes the M1a gunplay sounds (no third-party audio; see CREDITS.md).

Layers follow docs/design.md §5.3: mechanism, shot, room tail; impacts per
surface; reload beats; shell tinks; hit/headshot/kill confirms.
The 5.7×28 round is supersonic, so even suppressed it keeps a sharp crack;
the can removes most of the muzzle blast (the low boom) and adds a "pfft".

Usage: python3 raw_assets/audio/build_weapon_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
rng = np.random.default_rng(57)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def noise(sec):
    return rng.standard_normal(int(sec * SR))


def env(sec, attack, decay, curve=1.0):
    x = t(sec)
    a = np.clip(x / max(attack, 1e-5), 0, 1)
    return a * np.exp(-np.maximum(x - attack, 0) / decay) ** curve


def band(x, lo, hi, order=2):
    nyq = SR / 2
    if lo <= 0:
        b, a = signal.butter(order, hi / nyq, "low")
    elif hi >= nyq:
        b, a = signal.butter(order, lo / nyq, "high")
    else:
        b, a = signal.butter(order, [lo / nyq, hi / nyq], "band")
    return signal.lfilter(b, a, x)


def partials(sec, freqs, decays, amps=None, detune=0.0):
    x = t(sec)
    out = np.zeros_like(x)
    amps = amps or [1.0] * len(freqs)
    for f, d, a in zip(freqs, decays, amps):
        f2 = f * (1 + rng.uniform(-detune, detune))
        out += a * np.sin(2 * np.pi * f2 * x + rng.uniform(0, 6.28)) * np.exp(-x / d)
    return out


def at(total_sec, *parts):
    """Mix (offset_sec, signal) pairs into one buffer."""
    out = np.zeros(int(total_sec * SR))
    for off, sig in parts:
        i = int(off * SR)
        n = min(len(sig), len(out) - i)
        if n > 0:
            out[i:i + n] += sig[:n]
    return out


def click(sec=0.03, freqs=(3100, 4700, 6900), decay=0.012, bright=3000):
    tr = band(noise(sec), bright, SR / 2) * env(sec, 0.0002, 0.002)
    ring = partials(sec, freqs, [decay] * len(freqs), [1, 0.7, 0.5], detune=0.03)
    return tr * 0.8 + ring * 0.35


# Rebuilt as dull, unringing sounds by build_metal_sfx.py (owner, 2026-11-07:
# "get rid of the metal dinging"). The old code still runs so the shared rng
# stays in step for every other sound; it just doesn't write these.
REPLACED = {"shell_1", "shell_2", "shell_3", "impact_metal_1", "impact_can_1",
            "ricochet_1", "ricochet_2", "ricochet_3"}


def save(name, x, peak_db=-1.0):
    if name in REPLACED:
        return
    x = x - np.mean(x)
    # Short fades so nothing clicks at the edges.
    fade = min(len(x) // 4, int(0.004 * SR))
    if fade > 0:
        x[-fade:] *= np.linspace(1, 0, fade)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))


def shot(variant):
    sec = 0.42
    # Supersonic crack: short N-wave-like burst, very bright.
    crack = band(noise(0.04), 2500, 11000) * env(0.04, 0.0003, 0.006)
    nwave = np.concatenate([np.linspace(1, -1, int(0.0009 * SR)), np.zeros(10)])
    # Suppressed blast: the "pfft" and a soft low thump.
    pfft = band(noise(0.15), 350, 2600) * env(0.15, 0.001, 0.035)
    thump = band(noise(0.2), 40, 420) * env(0.2, 0.002, 0.05)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(85, 42, int(0.18 * SR))) / SR) * env(0.18, 0.002, 0.06)
    # Mechanism: slide back, then slams forward (the loudest part of a suppressed pistol).
    mech1 = click(0.05, (2900 + variant * 60, 4400, 6600), 0.01)
    mech2 = click(0.07, (2100 + variant * 40, 3500, 5200), 0.02, bright=1800) * 1.2
    return at(sec, (0.0, nwave * 0.9), (0.0, crack * 1.4), (0.001, pfft * 1.1), (0.0, thump * 1.3),
              (0.0, sub * 0.9), (0.008, mech1 * 0.55), (0.048, mech2 * 0.65))


def tail():
    sec = 1.4
    base = band(noise(sec), 250, 3200) * env(sec, 0.01, 0.32)
    refl = at(sec, *[(d, band(noise(0.03), 1500, 7000) * env(0.03, 0.0005, 0.008) * g)
                     for d, g in ((0.011, 0.6), (0.023, 0.45), (0.037, 0.35), (0.058, 0.25), (0.083, 0.18))])
    return base * 0.5 + refl


def write_all():
    os.makedirs(OUT, exist_ok=True)
    for v in (1, 2, 3):
        save(f"shot_{v}", shot(v))
    save("tail_1", tail(), -4)
    save("dry_fire_1", at(0.08, (0, click(0.05, (3800, 5600, 7900), 0.006))), -8)
    rustle = lambda sec: band(noise(sec), 300, 2500) * signal.windows.hann(int(sec * SR)) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t(sec)))
    save("reload_start_1", rustle(0.22), -14)
    save("reload_cancel_1", rustle(0.12), -16)
    slide_out = band(noise(0.13), 1500, 5500) * np.sin(np.pi * t(0.13) / 0.13) ** 2
    save("mag_out_1", at(0.2, (0, click(0.04, (2600, 4100, 5900), 0.01)), (0.03, slide_out * 0.35)), -5)
    slap = band(noise(0.08), 60, 700) * env(0.08, 0.001, 0.02)
    clack = click(0.08, (1250, 2350, 3700), 0.025, bright=1500)
    friction = band(noise(0.09), 1200, 5000) * np.linspace(0.1, 1, int(0.09 * SR))
    save("mag_in_1", at(0.25, (0, friction * 0.3), (0.09, clack * 1.2), (0.09, slap * 1.4)), -3)
    snap = click(0.12, (2200, 3550, 5300), 0.045, bright=2000)
    thunk = band(noise(0.1), 80, 600) * env(0.1, 0.001, 0.025)
    save("slide_release_1", at(0.2, (0, snap * 1.2), (0, thunk)), -3)
    for v in (1, 2, 3):
        f0 = 3000 + v * 230
        tink = partials(0.18, [f0, f0 * 1.63, f0 * 2.41, f0 * 3.3], [0.07, 0.05, 0.035, 0.02], [1, 0.6, 0.4, 0.25], 0.02)
        save(f"shell_{v}", at(0.3, (0, tink), (0.07 + v * 0.01, tink[: int(0.1 * SR)] * 0.35)), -6)
    # Impacts
    for v in (1, 2):
        crack = band(noise(0.05), 900, 7000) * env(0.05, 0.0003, 0.01)
        grit = band(noise(0.12) * (rng.random(int(0.12 * SR)) > 0.985), 1500, 9000) * env(0.12, 0.001, 0.04)
        save(f"impact_concrete_{v}", at(0.2, (0, crack), (0.004, grit * 2.5)), -2)
    save("impact_drywall_1", at(0.15, (0, band(noise(0.1), 80, 1500) * env(0.1, 0.001, 0.025)),
                                 (0.003, band(noise(0.08), 1500, 6000) * env(0.08, 0.001, 0.015) * 0.5)), -3)
    for v in (1, 2):
        knock = partials(0.15, [300 + 40 * v, 520, 910], [0.035, 0.025, 0.015], [1, 0.7, 0.4], 0.05)
        save(f"impact_wood_{v}", at(0.18, (0, knock), (0, band(noise(0.03), 2000, 8000) * env(0.03, 0.0003, 0.006) * 0.8)), -2)
    clang = partials(0.5, [640, 1340, 2210, 3120], [0.12, 0.09, 0.06, 0.04], [1, 0.8, 0.5, 0.35], 0.02)
    save("impact_metal_1", at(0.5, (0, clang), (0, band(noise(0.02), 3000, 12000) * env(0.02, 0.0002, 0.004))), -2)
    for v in (1, 2):
        # The steel plate "ting": slow-decaying inharmonic partials with beating pairs.
        f = [1150 + v * 35, 1158 + v * 35, 2830, 2841, 4100, 5650]
        ring = partials(1.6, f, [0.9, 0.85, 0.55, 0.5, 0.3, 0.18], [1, 0.8, 0.6, 0.5, 0.35, 0.2], 0.0)
        save(f"impact_steel_{v}", at(1.6, (0, ring), (0, band(noise(0.02), 2500, 12000) * env(0.02, 0.0002, 0.003) * 1.5)), -1)
    for v in (1, 2):
        thud = band(noise(0.12), 90, 900) * env(0.12, 0.001, 0.03)
        squelch = band(noise(0.06), 900, 3200) * env(0.06, 0.002, 0.015) * (0.5 + 0.5 * np.sin(2 * np.pi * (60 + 20 * v) * t(0.06)))
        save(f"impact_flesh_{v}", at(0.15, (0, thud * 1.4), (0.004, squelch * 0.7)), -2)
    save("impact_dirt_1", at(0.2, (0, band(noise(0.1), 60, 700) * env(0.1, 0.001, 0.03)),
                               (0.005, band(noise(0.15), 2000, 9000) * env(0.15, 0.002, 0.05) * 0.3)), -4)
    save("impact_can_1", partials(0.25, [2400, 3900, 6100], [0.08, 0.05, 0.03], [1, 0.7, 0.4], 0.03), -4)
    pings = at(0.5, *[(rng.uniform(0, 0.3), partials(0.12, [rng.uniform(3000, 9000)], [0.03])) for _ in range(30)])
    save("impact_glass_1", pings + at(0.5, (0, band(noise(0.35), 2500, 12000) * env(0.35, 0.002, 0.08) * 0.6)), -2)
    # Confirms (UI, non-positional)
    save("hit_marker_1", at(0.06, (0, click(0.04, (2500, 3900), 0.006, bright=2500))), -10)
    save("headshot_1", at(0.3, (0, partials(0.3, [2600, 5210, 7800], [0.1, 0.06, 0.03], [1, 0.4, 0.2])),
                            (0, band(noise(0.06), 60, 400) * env(0.06, 0.001, 0.02) * 1.5)), -6)
    save("kill_1", at(0.4, (0, np.sin(2 * np.pi * np.cumsum(np.linspace(110, 60, int(0.15 * SR))) / SR) * env(0.15, 0.001, 0.05)),
                        (0.01, partials(0.35, [1300, 1950], [0.12, 0.09], [0.5, 0.35]))), -6)
    print("wrote", len([f for f in os.listdir(OUT) if f.endswith(".wav")]), "sounds to", OUT)


if __name__ == "__main__":
    write_all()
