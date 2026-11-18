#!/usr/bin/env python3
"""Synthesizes the Governor's sounds (no third-party audio; see CREDITS.md).

A .45-70 from an 18.5-inch barrel with a ported brake, unsuppressed and
indoors (owner, 2026-11-18: "intense sound ... the satisfying audio clunk of
the lever being drawn"):
- shot: the bullet is subsonic-to-transonic, so the crack is small; what
  hits you is the muzzle blast: a hard transient, a wide low-mid boom, the
  brake's side ports slapping the air back at the shooter, and a sub drop
  the size of a door slamming. Three variants.
- tail: a long, dark room tail (marble and glass), with slap-back echoes.
- lever_open: the lever unlocks (a sharp click), the bolt runs back over
  the carrier (a rough metallic slide), the hammer is cocked (a ratchet).
- lever_close: the bolt slams home and the lever latches: a heavy two-part
  "chunk-clack", the satisfying one.
- round_in: a long brass case pushed through the spring-loaded gate.
- dry_fire: the hammer falls on an empty chamber.
- reload_start / slide_release / reload_cancel: hands, the gate snapping shut.

Usage: python3 raw_assets/audio/build_governor_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
sys.argv = sys.argv[:1]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(4570)
SR = w.SR


def shot(v):
    sec = 1.1
    nwave = np.concatenate([np.linspace(1, -1, int(0.0016 * SR)), np.zeros(10)])
    crack = w.band(w.noise(0.03), 1800, 9000) * w.env(0.03, 0.0002, 0.006)
    blast = w.band(w.noise(0.35), 120, 2600) * w.env(0.35, 0.0006, 0.045 + 0.005 * v)
    boom = w.band(w.noise(0.6), 30, 240) * w.env(0.6, 0.002, 0.12)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(58 + 2 * v, 24, int(0.55 * SR))) / SR) * w.env(0.55, 0.002, 0.16)
    ports = w.at(0.2, *[(d, w.band(w.noise(0.05), 600, 5000) * w.env(0.05, 0.0003, 0.008) * g)
                        for d, g in ((0.0008, 1.0), (0.0019, 0.8), (0.0031, 0.6))])
    ring = w.partials(0.5, (220 + 6 * v, 610, 1280), (0.12, 0.07, 0.04), (0.35, 0.2, 0.1), 0.02)
    x = w.at(sec, (0.0, nwave * 1.4), (0.0, crack * 0.7), (0.0, blast * 1.8), (0.0, boom * 2.2), (0.0, sub * 1.9),
             (0.0, ports * 1.2), (0.003, ring * 0.2))
    return np.tanh(x * 1.6)


def tail():
    sec = 3.2
    base = w.band(w.noise(sec), 90, 2200) * w.env(sec, 0.02, 0.7)
    low = w.band(w.noise(sec), 25, 160) * w.env(sec, 0.03, 0.9)
    refl = w.at(sec, *[(d, w.band(w.noise(0.08), 300, 3500) * w.env(0.08, 0.001, 0.02) * g)
                       for d, g in ((0.05, 0.7), (0.11, 0.55), (0.19, 0.42), (0.31, 0.3), (0.47, 0.2), (0.7, 0.12))])
    return base * 0.55 + low * 0.7 + refl


def lever_open():
    unlock = w.click(0.06, (1900, 3400, 5200), 0.01, bright=2200)
    slide_len = 0.11
    slide = w.band(w.noise(slide_len), 1500, 7000) * np.sin(np.pi * w.t(slide_len) / slide_len) ** 0.6
    grind = w.band(w.noise(slide_len), 300, 1400) * np.sin(np.pi * w.t(slide_len) / slide_len)
    ratchet = w.at(0.06, *[(d, w.click(0.02, (2600, 4100, 6000), 0.004, bright=3000) * g) for d, g in ((0.0, 0.6), (0.022, 0.9))])
    stop = w.click(0.08, (900, 1700, 2900), 0.025, bright=1200)
    return w.at(0.32, (0.0, unlock * 1.0), (0.015, slide * 0.35), (0.015, grind * 0.3), (0.05, ratchet * 0.7),
                (0.12, stop * 0.9))


def lever_close():
    slide_len = 0.07
    slide = w.band(w.noise(slide_len), 1200, 6000) * np.sin(np.pi * w.t(slide_len) / slide_len) ** 0.6
    slam = w.click(0.14, (640, 1300, 2400), 0.05, bright=900)
    body = w.band(w.noise(0.12), 60, 600) * w.env(0.12, 0.001, 0.03)
    latch = w.click(0.08, (2100, 3600, 5400), 0.012, bright=2400)
    thud = np.sin(2 * np.pi * np.cumsum(np.linspace(140, 70, int(0.1 * SR))) / SR) * w.env(0.1, 0.001, 0.03)
    return w.at(0.4, (0.0, slide * 0.3), (0.06, slam * 1.3), (0.06, body * 1.4), (0.06, thud * 0.9), (0.105, latch * 1.0))


def round_in():
    push_len = 0.09
    push = w.band(w.noise(push_len), 900, 5000) * np.sin(np.pi * w.t(push_len) / push_len) ** 0.7
    gate = w.click(0.05, (2400, 3900, 5600), 0.009, bright=2600)
    seat = w.click(0.09, (700, 1400, 2500), 0.03, bright=1100)
    spring = w.partials(0.15, (1850, 2950), (0.04, 0.025), (0.3, 0.2), 0.03)
    return w.at(0.3, (0.0, gate * 0.8), (0.01, push * 0.45), (0.01, spring * 0.15), (0.095, seat * 0.9))


def write_all():
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        w.save(f"governor_shot_{v}", shot(v))
    w.save("governor_tail_1", tail(), -3)
    w.save("governor_lever_open_1", lever_open(), -2)
    w.save("governor_lever_close_1", lever_close(), -1)
    w.save("governor_round_in_1", round_in(), -4)
    w.save("governor_dry_fire_1", w.at(0.15, (0, w.click(0.08, (1400, 2600, 4300), 0.015, bright=1800))), -6)
    rustle = w.band(w.noise(0.2), 250, 2400) * np.hanning(int(0.2 * SR))
    w.save("governor_reload_start_1", w.at(0.25, (0, rustle * 0.5)), -12)
    w.save("governor_slide_release_1", w.at(0.15, (0, w.click(0.06, (1800, 3000, 4800), 0.012, bright=2000))), -8)
    w.save("governor_reload_cancel_1", w.at(0.15, (0, rustle[: int(0.12 * SR)] * 0.6)), -14)
    print(f"wrote Governor sounds to {out}")


if __name__ == "__main__":
    write_all()
