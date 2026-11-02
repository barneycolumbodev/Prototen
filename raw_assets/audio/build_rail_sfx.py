#!/usr/bin/env python3
"""Synthesizes the RC-6 rail carbine sounds (no third-party audio; see CREDITS.md).

A railgun has no propellant, so there is no muzzle blast in the usual sense.
What you hear instead (grounded in what real electromagnetic launchers do):
- the capacitor bank dumping into the rails: a hard electrical snap, and the
  plasma armature arcing at the muzzle (crackle, fizz);
- the magnetic shock through the gun: a deep metallic "thwack" with a short
  pitch drop, and the rails ringing afterwards;
- the slug leaving at Mach 7.6: a violent supersonic crack and a long, low
  rolling boom down range (the room tail);
- then the capacitors recharging: a rising whine that ends in a ready tone.

Files (Sfx bank prefix "rail_"): shot x3, tail, charge, ready, vent,
overheat, dry_fire, reload_start, mag_out, mag_in, reload_cancel.
Shares helpers with build_weapon_sfx.py (imported, not copied).

Usage: python3 raw_assets/audio/build_rail_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(2600)
SR = w.SR
rng = w.rng


def sweep(sec, f0, f1, curve=1.0):
    """Sine whose frequency moves from f0 to f1 (exponential when curve>1)."""
    x = np.linspace(0, 1, int(sec * SR)) ** curve
    f = f0 * (f1 / f0) ** x
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def crackle(sec, density, lo, hi, decay):
    """Sparse random impulses (electrical arcing), band limited, decaying."""
    n = int(sec * SR)
    imp = (rng.random(n) < density) * rng.standard_normal(n)
    return w.band(imp, lo, hi) * w.env(sec, 0.0002, decay)


def shot(v):
    sec = 0.9
    # Capacitor dump: the hard electrical snap at t=0.
    snap = w.band(w.noise(0.012), 3000, 16000) * w.env(0.012, 0.00005, 0.0012)
    zap = sweep(0.05, 9000 - 400 * v, 1400, 0.6) * w.env(0.05, 0.0002, 0.012)
    arc = crackle(0.09, 0.08, 1800, 12000, 0.025)
    # Magnetic thwack: body of the gun hit by the field, short pitch drop.
    thwack = w.partials(0.18, (172 + 9 * v, 410, 930, 1610), (0.06, 0.045, 0.03, 0.018), (1.0, 0.8, 0.55, 0.3), 0.02)
    thwack *= np.linspace(1.0, 0.85, len(thwack))
    body = w.band(w.noise(0.08), 90, 1800) * w.env(0.08, 0.0003, 0.012)
    # Slug at Mach 7.6: strong N-wave and crack.
    nwave = np.concatenate([np.linspace(1, -1, int(0.0016 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.035), 1500, 13000) * w.env(0.035, 0.0002, 0.0045)
    # Sub punch you feel more than hear.
    sub = sweep(0.32, 62 + 3 * v, 26, 1.0) * w.env(0.32, 0.001, 0.09)
    boom = w.band(w.noise(0.4), 28, 220) * w.env(0.4, 0.002, 0.08)
    # Rails singing after the shot (inharmonic, beating pairs).
    ring = w.partials(0.85, (2210 + 30 * v, 2223 + 30 * v, 3710, 5930, 7480),
                      (0.22, 0.2, 0.14, 0.08, 0.05), (0.5, 0.4, 0.35, 0.2, 0.12), 0.0)
    # Plasma fizz at the muzzle trailing off.
    fizz = w.band(w.noise(0.25), 4000, 14000) * w.env(0.25, 0.002, 0.05) * (0.6 + 0.4 * np.sin(2 * np.pi * 37 * w.t(0.25)))
    return w.at(sec, (0.0, snap * 1.4), (0.0, nwave * 1.1), (0.0005, crack * 1.3), (0.0, zap * 0.35), (0.001, arc * 0.9),
                (0.002, thwack * 0.9), (0.001, body * 1.2), (0.0, sub * 1.3), (0.0, boom * 1.4), (0.006, ring * 0.16),
                (0.004, fizz * 0.35))


def tail():
    # Rolling boom down range with ionized-air crackle on top.
    sec = 2.6
    roll = w.band(w.noise(sec), 30, 300) * w.env(sec, 0.03, 0.7)
    roll *= 0.75 + 0.25 * np.sin(2 * np.pi * 3.1 * w.t(sec) + 1.0)
    mid = w.band(w.noise(sec), 250, 2600) * w.env(sec, 0.012, 0.32)
    refl = w.at(sec, *[(d, w.band(w.noise(0.05), 700, 6000) * w.env(0.05, 0.0005, 0.014) * g)
                       for d, g in ((0.018, 0.7), (0.041, 0.55), (0.066, 0.42), (0.1, 0.3), (0.15, 0.22), (0.23, 0.15),
                                    (0.33, 0.1))])
    sizzle = crackle(sec, 0.004, 3000, 12000, 0.35) * 0.6
    return roll * 0.9 + mid * 0.45 + refl + sizzle


def charge():
    # Capacitors recharging: rising whine (with a sub-harmonic and a little warble) over a mains-like hum.
    sec = 0.95
    rise = 0.62
    n = int(sec * SR)
    x = np.arange(n) / SR
    k = np.clip(x / rise, 0, 1) ** 0.7
    f = 700 * (4600 / 700) ** k
    f *= 1 + 0.004 * np.sin(2 * np.pi * 23 * x)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.35 * np.sin(2 * ph + 0.4) + 0.25 * np.sin(0.5 * ph)
    amp = np.clip(x / 0.04, 0, 1) * (0.35 + 0.65 * k)
    amp *= np.where(x > rise, np.exp(-(x - rise) / 0.12), 1.0)
    hum = w.band(np.sign(np.sin(2 * np.pi * 120 * x)), 100, 2400) * 0.12 * np.clip(x / 0.03, 0, 1) * np.exp(-x / 0.5)
    return tone * amp * 0.5 + hum


def ready():
    # Relay click and a clean two-note tone: capacitor full.
    click = w.click(0.03, (2400, 3800, 5600), 0.006, bright=2500)
    t1 = w.partials(0.09, (2637,), (0.05,), (1.0,)) * w.env(0.09, 0.002, 0.04)
    t2 = w.partials(0.14, (3520, 7040), (0.07, 0.03), (1.0, 0.2)) * w.env(0.14, 0.002, 0.06)
    return w.at(0.25, (0, click * 0.6), (0.004, t1 * 0.5), (0.06, t2 * 0.55))


def vent():
    # Overheat vent: shroud unlocks (clunk), coolant hiss, fan, metal ticking as it cools.
    sec = 1.7
    clunk = w.click(0.1, (520, 1150, 2300), 0.035, bright=900)
    thud = w.band(w.noise(0.08), 60, 500) * w.env(0.08, 0.001, 0.02)
    hiss = w.band(w.noise(sec), 1800, 11000) * w.env(sec, 0.02, 0.45)
    hiss *= 0.85 + 0.15 * np.sin(2 * np.pi * 11 * w.t(sec))
    fan = w.band(np.sign(np.sin(2 * np.pi * np.cumsum(np.linspace(90, 210, int(sec * SR))) / SR)), 150, 3000)
    fan *= np.sin(np.pi * w.t(sec) / sec) ** 0.8 * 0.08
    ticks = w.at(sec, *[(rng.uniform(0.3, 1.6), w.click(0.02, (rng.uniform(3500, 7000), 9000), 0.004, bright=4000)
                         * rng.uniform(0.2, 0.5)) for _ in range(9)])
    return w.at(sec, (0, clunk * 0.9), (0, thud), (0.03, hiss * 0.55), (0.0, fan), (0, ticks))


def overheat():
    beep = w.partials(0.07, (1568, 3136), (0.05, 0.03), (1.0, 0.3)) * w.env(0.07, 0.002, 0.04)
    return w.at(0.3, (0, beep), (0.09, beep), (0.18, beep))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"rail_shot_{v}", shot(v))
    w.save("rail_tail_1", tail(), -2)
    w.save("rail_charge_1", charge(), -9)
    w.save("rail_ready_1", ready(), -10)
    w.save("rail_vent_1", vent(), -4)
    w.save("rail_overheat_1", overheat(), -9)
    # Dry fire / denied: relay clicks, a weak fizz (no charge to dump).
    fizz = w.band(w.noise(0.12), 3000, 9000) * w.env(0.12, 0.001, 0.03)
    w.save("rail_dry_fire_1", w.at(0.2, (0, w.click(0.04, (1900, 3300, 5100), 0.008)), (0.01, fizz * 0.3)), -8)
    # Reload: latch, magazine slides back off the top, new one seats, slugs indexed by a solenoid chirp.
    latch = w.click(0.06, (1700, 2900, 4400), 0.015, bright=1800)
    w.save("rail_reload_start_1", w.at(0.15, (0, latch)), -6)
    slide = w.band(w.noise(0.22), 500, 4500) * np.sin(np.pi * w.t(0.22) / 0.22) ** 2
    w.save("rail_mag_out_1", w.at(0.35, (0, latch * 0.7), (0.03, slide * 0.45)), -4)
    seat = w.click(0.1, (900, 1750, 3100), 0.03, bright=1200)
    thunk = w.band(w.noise(0.1), 50, 600) * w.env(0.1, 0.001, 0.025)
    chirp = sweep(0.12, 1200, 5200, 1.5) * w.env(0.12, 0.004, 0.05)
    w.save("rail_mag_in_1", w.at(0.4, (0, seat * 1.1), (0, thunk * 1.2), (0.11, chirp * 0.25),
                                 (0.11, w.click(0.03, (4200, 6100), 0.005) * 0.4)), -2)
    w.save("rail_reload_cancel_1", w.at(0.15, (0, latch * 0.6)), -9)
    print(f"wrote rail carbine sounds to {out}")


if __name__ == "__main__":
    write_all()
