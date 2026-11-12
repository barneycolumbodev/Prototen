#!/usr/bin/env python3
"""Synthesizes the MP5 sounds (no third-party audio; see CREDITS.md).

Suppressed 9x19 at about 400 m/s: just over the speed of sound, so a small,
dry crack survives, but the can eats the blast and leaves a soft, papery
"thwup". What you mostly hear on a suppressed MP5 is the roller-delayed
action: the bolt head and carrier slam back and forward ("clack-chk") in
the 75 ms between rounds, so the action is mixed loud. The room tail is short
and quiet. Reload beats: paddle release and the curved magazine rocking out,
the new one seated with a slap, and the HK slap (cocking handle slapped down
out of its notch, bolt slamming home) on an empty reload.

Shares helpers with build_weapon_sfx.py (imported, not copied).
Usage: python3 raw_assets/audio/build_mp5_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(5)
SR = w.SR


def shot(v):
    sec = 0.32
    crack = w.band(w.noise(0.012), 2600, 11000) * w.env(0.012, 0.0001, 0.0025)
    thwup = w.band(w.noise(0.09), 140, 1400) * w.env(0.09, 0.0015, 0.022)
    pfft = w.band(w.noise(0.07), 900, 5200) * w.env(0.07, 0.0008, 0.016)
    body = np.sin(2 * np.pi * np.cumsum(np.linspace(118 + 6 * v, 62, int(0.1 * SR))) / SR) * w.env(0.1, 0.001, 0.028)
    can = w.partials(0.14, (720 + 15 * v, 1660, 3150), (0.03, 0.022, 0.014), (0.5, 0.3, 0.2), 0.02)
    # Roller-delayed action: carrier back (bright), bolt head home (lower), a little rattle.
    back = w.click(0.04, (2400 + 80 * v, 3900, 6100), 0.009, bright=2600)
    home = w.click(0.06, (1500, 2600, 4200), 0.016, bright=1700)
    rattle = w.band(w.noise(0.05), 1800, 7000) * w.env(0.05, 0.001, 0.012)
    return w.at(sec, (0.0, crack * 0.5), (0.0, thwup * 1.2), (0.0005, pfft * 0.55), (0.0, body * 0.5),
                (0.001, can * 0.18), (0.006, back * 0.9), (0.038, home * 0.8), (0.04, rattle * 0.25))


def tail():
    sec = 0.7
    base = w.band(w.noise(sec), 250, 3000) * w.env(sec, 0.006, 0.15)
    low = w.band(w.noise(sec), 50, 260) * w.env(sec, 0.01, 0.18)
    refl = w.at(sec, *[(d, w.band(w.noise(0.03), 1200, 6000) * w.env(0.03, 0.0005, 0.008) * g)
                       for d, g in ((0.011, 0.5), (0.023, 0.38), (0.039, 0.27), (0.06, 0.18))])
    return base * 0.45 + low * 0.35 + refl


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3, 4):
        w.save(f"mp5_shot_{v}", shot(v), -1)
    w.save("mp5_tail_1", tail(), -8)
    paddle = w.click(0.04, (2300, 3600, 5400), 0.01, bright=2200)
    rock = w.band(w.noise(0.1), 800, 4600) * np.sin(np.pi * w.t(0.1) / 0.1) ** 2
    w.save("mp5_reload_start_1", w.at(0.18, (0, w.band(w.noise(0.13), 300, 2600) * np.hanning(int(0.13 * SR)) * 0.4)), -13)
    w.save("mp5_mag_out_1", w.at(0.26, (0, paddle), (0.015, rock * 0.55)), -5)
    seat = w.click(0.08, (1100, 2100, 3600), 0.025, bright=1600)
    slap = w.band(w.noise(0.06), 80, 900) * w.env(0.06, 0.001, 0.016)
    w.save("mp5_mag_in_1", w.at(0.3, (0, rock * 0.3), (0.07, seat * 1.1), (0.07, slap * 1.1)), -2)
    # HK slap: palm hits the handle (dull), handle snaps out of the notch, bolt slams home.
    palm = w.band(w.noise(0.05), 70, 700) * w.env(0.05, 0.001, 0.014)
    snap = w.click(0.04, (2600, 4000, 6000), 0.008, bright=2500)
    slam = w.click(0.11, (820, 1600, 2900), 0.04, bright=1100)
    w.save("mp5_slide_release_1", w.at(0.3, (0, palm * 1.2), (0.004, snap * 0.8), (0.022, slam * 1.15),
                                         (0.022, slap * 0.8)), -2)
    w.save("mp5_dry_fire_1", w.at(0.1, (0, w.click(0.05, (2800, 4300, 6500), 0.007))), -9)
    w.save("mp5_reload_cancel_1", w.at(0.14, (0, w.band(w.noise(0.1), 300, 2200) * np.hanning(int(0.1 * SR)))), -15)
    print(f"wrote MP5 sounds to {out}")


if __name__ == "__main__":
    write_all()
