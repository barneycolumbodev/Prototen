#!/usr/bin/env python3
"""Synthesizes the SPAS-12's sounds (no third-party audio; see CREDITS.md).

Owner, 2026-11-20: "It also needs a boom. The gun noises in this game aren't
very good so far, so let's try to really take it to the next level with this
one." Built as a sound designer layers a shotgun, in stereo (the player's own
gun plays non-positional, so the width is heard):

- shot: five layers summed and driven through parallel saturation so it is
  loud and dense rather than peaky:
    snap   the first 2 ms: an N-wave and a hard high click (the pressure front)
    blast  broadband muzzle blast, fast decay, a little different left/right
    punch  a 170 -> 52 Hz pitch drop over 120 ms: the chest hit (a kick drum's job)
    boom   a 68 -> 26 Hz sub sweep and a 40-260 Hz body, 0.5 s: the boom; it is
           saturated so its harmonics carry it on a phone speaker that can't play 30 Hz
    steel  the SPAS's heavy steel action shuddering in the receiver
  plus early reflections off nearby walls (different on each side). Three variants.
- tail: 3.5 s of rolling thunder: a low roll with slow surges, slap-back
  echoes that come back darker each time, and a diffuse decay, decorrelated
  left and right.
- pump_back: the action unlocks, the bars rasp back, the hard stop at the
  rear (clack plus a body thump), the hull flicked out and, a beat later,
  bouncing on the floor.
- pump_forward: the bolt strips the next shell off the carrier and slams
  home: a heavy two-part "CHUNK-chak", the satisfying one.
- round_in: a 12-gauge hull thumbed past the carrier latch into the tube.
- mag_out / slide_release / reload_start / reload_cancel / dry_fire: the
  hand going to the loading port and back, the hammer on an empty chamber.

Usage: python3 raw_assets/audio/build_spas12_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys_args = sys.argv[1:]
_paths = [a for a in sys_args if not a.startswith("--")]
out = _paths[0] if _paths else "assets/audio/sfx"
sys.argv = sys.argv[:1]
import build_weapon_sfx as w  # noqa: E402

w.rng = np.random.default_rng(1212)
rng = w.rng
SR = w.SR


def sweep(sec, f0, f1, curve=2.0):
    """A sine whose pitch falls from f0 to f1 (exponential-ish), unit amplitude."""
    k = np.linspace(0, 1, int(sec * SR)) ** (1 / curve)
    f = f0 * (f1 / f0) ** k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def sat(x, drive):
    return np.tanh(x * drive) / np.tanh(drive)


def stereo(left, right):
    n = max(len(left), len(right))
    s = np.zeros((n, 2))
    s[: len(left), 0] = left
    s[: len(right), 1] = right
    return s


def save_stereo(name, x, peak_db=-1.0):
    x = x - np.mean(x, axis=0)
    fade = min(len(x) // 4, int(0.004 * SR))
    if fade > 0:
        x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    wavfile.write(os.path.join(w.OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))


def mix(*parts):
    """Sum of signals of any lengths (padded to the longest)."""
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def limit(x, gain_db, release=0.06):
    """Brick-wall-ish limiter: push `gain_db` into a ceiling of 1, the gain riding a peak
    envelope (2 ms look-ahead, `release` s) so the transient keeps its shape and the body gets dense."""
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (gain_db / 20)
    peak = np.max(np.abs(x), axis=1) if x.ndim == 2 else np.abs(x)
    la = int(0.002 * SR)
    ahead = np.maximum.reduce([np.roll(peak, -k) for k in range(la)])
    env = np.empty_like(ahead)
    a = np.exp(-1.0 / (release * SR))
    e = 0.0
    for i, v in enumerate(ahead):
        e = v if v > e else a * e + (1 - a) * v
        env[i] = e
    g = np.minimum(1.0, 0.98 / np.maximum(env, 1e-9))
    y = x * (g[:, None] if x.ndim == 2 else g)
    return sat(y, 1.15)


def metal(sec, freqs, decay, amps=None):
    """Inharmonic steel ring with a struck transient."""
    ring = w.partials(sec, freqs, [decay * (1.0 - 0.12 * i) for i in range(len(freqs))], amps, detune=0.02)
    hit = w.band(w.noise(sec), 1500, 12000) * w.env(sec, 0.0001, 0.0025)
    return ring + hit * 0.9


def thump(sec, f0, f1, decay):
    return sweep(sec, f0, f1) * w.env(sec, 0.0006, decay)


# ---------------------------------------------------------------- the shot
LOW_MIX = 0.3
LOW_DRIVE = 1.2
HI_RMS = 0.45
LIMIT_DB = 4.5
def shot(v):
    sec = 1.4
    n = int(sec * SR)
    # Snap: the N-wave of the pressure front, then a very short bright click.
    nwave = np.concatenate([np.linspace(1, -1, int(0.0018 * SR)), np.zeros(8)])
    click = highpass(w.noise(0.012), 2500) * w.env(0.012, 0.00005, 0.0012)
    # Blast: broad noise, decays in ~50 ms, with a longer low-mid roar under it.
    blast_l = w.band(w.noise(0.7), 250, 7000) * w.env(0.7, 0.0004, 0.068 + 0.004 * v)
    blast_r = w.band(w.noise(0.7), 250, 7000) * w.env(0.7, 0.0004, 0.068 + 0.004 * v)
    # The shotgun's "bark": a hard mid burst that is what a phone speaker actually plays.
    bark = w.band(w.noise(0.12), 700, 2800, order=3) * w.env(0.12, 0.0003, 0.018)
    roar = w.band(w.noise(1.1), 180, 1600) * w.env(1.1, 0.002, 0.16)
    # Punch: the chest hit, saturated so its harmonics (200-600 Hz) carry it on small speakers.
    punch = sat(thump(0.25, 170 + 6 * v, 52, 0.055) * 1.6, 3.0)
    # Boom: sub sweep and the body below 260 Hz, saturated for harmonics.
    sub = thump(1.3, 68 + 2 * v, 26, 0.20)
    body = w.band(w.noise(1.3), 40, 260, order=3) * w.env(1.3, 0.002, 0.16)
    boom = sat(sub * 1.4 + body * 1.6, 2.2)
    # Steel: the action and the receiver shudder.
    steel = metal(0.25, (430 + 9 * v, 1170, 2310, 3620), 0.045, [0.5, 0.35, 0.22, 0.12])
    core = w.at(sec, (0.0, nwave * 1.3), (0.0, click * 1.2), (0.0, punch * 1.3), (0.0, boom * 0.75),
                (0.0005, bark * 3.6), (0.002, roar * 1.8), (0.004, steel * 0.3))
    left = core + w.at(sec, (0.0, blast_l * 4.2))
    right = core + w.at(sec, (0.0, blast_r * 4.2))
    # Early reflections off nearby walls, darker and different on each side.
    for ch, delays in ((0, (0.0071, 0.0163, 0.0287, 0.041)), (1, (0.0093, 0.0198, 0.0331, 0.047))):
        src = left if ch == 0 else right
        refl = np.zeros(n)
        for k, d in enumerate(delays):
            i = int(d * SR)
            refl[i:] += lowpass(src[: n - i], 3200 - 500 * k) * (0.32 - 0.06 * k)
        if ch == 0:
            left = left + refl
        else:
            right = right + refl
    # Parallel saturation: the dense, loud body under the clean transient.
    left = left + 0.65 * sat(left, 3.5)
    right = right + 0.65 * sat(right, 3.5)
    x = stereo(left, right)
    # Two bands: the boom squeezed hard on its own (dense, with harmonics), the bark and blast
    # kept sharp, so the sub's big slow peaks don't hold the rest down. Then the limiter.
    lo = np.stack([lowpass(x[:, c], 160, 4) for c in range(2)], 1)
    hi = x - lo
    lo = sat(lo / np.max(np.abs(lo)) * LOW_DRIVE, 1.0) * LOW_MIX
    hi = hi / np.sqrt(np.mean(hi[: int(0.1 * SR)] ** 2)) * HI_RMS
    return limit(lo + hi, LIMIT_DB)


def tail():
    sec = 3.6
    chans = []
    for ch in range(2):
        tt = w.t(sec)
        # Rolling thunder: a low roll with slow surges.
        surge = 0.65 + 0.35 * np.sin(2 * np.pi * (0.9 + 0.3 * ch) * tt + rng.uniform(0, 6.28)) \
            * np.sin(2 * np.pi * 0.37 * tt + rng.uniform(0, 6.28))
        roll = w.band(w.noise(sec), 28, 220, order=3) * w.env(sec, 0.04, 0.95) * surge
        diffuse = w.band(w.noise(sec), 160, 2600) * w.env(sec, 0.015, 0.42)
        diffuse = lowpass(diffuse, 2200)
        # Slap-back from buildings: each echo returns darker and later.
        echoes = np.zeros(int(sec * SR))
        for k, (d, g) in enumerate(((0.085, 0.75), (0.19, 0.6), (0.33, 0.48), (0.52, 0.36), (0.78, 0.26),
                                    (1.12, 0.18), (1.55, 0.11))):
            d = d * (1.0 + 0.07 * ch) + rng.uniform(-0.01, 0.01)
            burst = w.at(0.25, (0.0, w.band(w.noise(0.14), 120, 2600 - 280 * k) * w.env(0.14, 0.002, 0.035 + 0.008 * k)))
            burst += w.band(w.noise(0.25), 35, 200) * w.env(0.25, 0.004, 0.07) * 0.9
            i = int(d * SR)
            m = min(len(burst), len(echoes) - i)
            echoes[i:i + m] += burst[:m] * g
        chans.append(sat(roll * 1.3 + diffuse * 0.4 + echoes * 0.8, 1.5))
    return stereo(*chans)


# ---------------------------------------------------------------- the pump
def rasp(sec, lo, hi, chatter_hz):
    tt = w.t(sec)
    shape = np.sin(np.pi * tt / sec) ** 0.6
    chatter = 0.6 + 0.4 * np.abs(np.sin(np.pi * chatter_hz * tt))
    return w.band(w.noise(sec), lo, hi) * shape * chatter


def pump_back():
    sec = 0.62
    unlock = mix(metal(0.06, (1850, 3300, 5100), 0.010, [0.6, 0.4, 0.25]), thump(0.05, 220, 120, 0.012) * 0.6)
    slide = rasp(0.075, 1200, 7500, 190) * 0.2 + rasp(0.075, 250, 1100, 120) * 0.13
    stop = mix(metal(0.18, (520, 1340, 2780, 4100), 0.028, [0.7, 0.5, 0.3, 0.18]) * 1.1,
               thump(0.3, 150, 85, 0.030) * 1.0, w.band(w.noise(0.1), 80, 900) * w.env(0.1, 0.0005, 0.02) * 0.9)
    flick = w.band(w.noise(0.03), 1500, 6500) * w.env(0.03, 0.0005, 0.006)
    # The hull lands: two light plastic tocks.
    tock = mix(w.partials(0.06, (980, 2300, 3700), (0.012, 0.008, 0.005), [0.6, 0.35, 0.2]),
               w.band(w.noise(0.04), 600, 4000) * w.env(0.04, 0.0003, 0.004))
    x = w.at(sec, (0.0, unlock * 0.9), (0.008, slide), (0.08, stop * 1.2), (0.084, flick * 0.5),
             (0.40, tock * 0.22), (0.47, tock * 0.12))
    return sat(x, 1.1)


def pump_forward():
    sec = 0.5
    strip = rasp(0.05, 700, 3600, 140) * 0.17 + rasp(0.05, 1800, 8000, 230) * 0.13
    chunk = mix(thump(0.32, 140, 72, 0.042) * 1.25, metal(0.22, (380, 920, 1900, 3300), 0.036, [0.9, 0.6, 0.35, 0.2]) * 1.1,
                w.band(w.noise(0.12), 60, 700) * w.env(0.12, 0.0005, 0.028) * 1.2)
    chak = mix(metal(0.08, (2150, 3600, 5600), 0.012, [0.7, 0.45, 0.3]) * 0.9, thump(0.05, 260, 160, 0.010) * 0.6)
    rattle = w.band(w.noise(0.12), 1500, 6000) * w.env(0.12, 0.002, 0.02) * 0.15
    x = w.at(sec, (0.0, strip), (0.052, chunk), (0.071, chak), (0.09, rattle))
    return sat(x, 1.25)


def round_in():
    sec = 0.34
    latch = metal(0.04, (2400, 3900, 5600), 0.008, [0.6, 0.4, 0.25])
    push = w.band(w.noise(0.09), 600, 3600) * np.sin(np.pi * w.t(0.09) / 0.09) ** 0.7
    spring = w.partials(0.16, (1650, 2700), (0.04, 0.025), [0.3, 0.2], 0.03)
    seat = mix(thump(0.06, 210, 130, 0.014) * 0.8, w.band(w.noise(0.04), 300, 2500) * w.env(0.04, 0.0003, 0.007) * 0.6)
    return w.at(sec, (0.0, latch * 0.7), (0.012, push * 0.5), (0.012, spring * 0.14), (0.1, seat))


def write_all():
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    # Since 2026-11-21 the shot, tail and pump come from real recordings
    # (build_spas12_real_sfx.py); these synthesized ones are only written
    # with --synth-shot, for comparison.
    if "--synth-shot" in sys_args:
        for v in (1, 2, 3):
            save_stereo(f"spas12_shot_{v}", shot(v), -0.5)
        save_stereo("spas12_tail_1", tail(), -2.0)
        w.save("spas12_pump_back_1", pump_back(), -1.5)
        w.save("spas12_pump_forward_1", pump_forward(), -0.5)
    w.save("spas12_round_in_1", round_in(), -4)
    w.save("spas12_dry_fire_1", w.at(0.15, (0, metal(0.08, (1500, 2700, 4400), 0.012, [0.6, 0.4, 0.2]))), -7)
    rustle = w.band(w.noise(0.2), 250, 2400) * np.hanning(int(0.2 * SR))
    w.save("spas12_reload_start_1", w.at(0.25, (0, rustle * 0.5)), -12)
    w.save("spas12_mag_out_1", w.at(0.2, (0, rustle[: int(0.15 * SR)] * 0.4),
                                    (0.05, metal(0.04, (2100, 3500), 0.006, [0.4, 0.25]) * 0.4)), -14)
    w.save("spas12_slide_release_1", w.at(0.2, (0, rustle[: int(0.12 * SR)] * 0.4),
                                          (0.06, thump(0.05, 200, 130, 0.012) * 0.5)), -12)
    w.save("spas12_reload_cancel_1", w.at(0.15, (0, rustle[: int(0.12 * SR)] * 0.6)), -14)
    print(f"wrote SPAS-12 sounds to {out}")


if __name__ == "__main__":
    write_all()
