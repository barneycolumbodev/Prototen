#!/usr/bin/env python3
"""Synthesizes UI sounds for the weapon wheel (no third-party audio; see CREDITS.md).

wheel_open: a soft mechanical detent and a low swell (time slows down).
wheel_tick: a short dry click as the highlight moves to another gun.
Shares helpers with build_weapon_sfx.py (imported, not copied).

Usage: python3 raw_assets/audio/build_ui_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = sys.argv[:2]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(1404)
SR = w.SR


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    detent = w.click(0.05, (1400, 2300, 3600), 0.012, bright=1800)
    x = w.t(0.45)
    swell = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 90, len(x))) / SR) * np.sin(np.pi * x / 0.45) ** 2
    air = w.band(w.noise(0.45), 300, 2000) * np.sin(np.pi * x / 0.45) ** 2
    w.save("wheel_open_1", w.at(0.5, (0, detent * 0.8), (0.0, swell * 0.35), (0.0, air * 0.12)), -8)
    w.save("wheel_tick_1", w.at(0.06, (0, w.click(0.04, (3200, 5100), 0.004, bright=3000))), -10)
    print(f"wrote UI sounds to {out}")


if __name__ == "__main__":
    write_all()
