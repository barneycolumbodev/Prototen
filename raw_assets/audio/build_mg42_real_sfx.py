#!/usr/bin/env python3
"""The MG42's shot and tail from a real recording (see CREDITS.md and SOURCE below).

Owner, 2026-11-23: "find a better sound effect for it. They all need to be
real gun sound effects, but for now, just change the MG42 to a real gun sound
effect." The synthesized shot (build_mg42_sfx.py) is replaced; its belt reload
beats and dry fire stay.

How the game plays it: Sfx.play_shot every round (1,200 rpm = one every 50 ms,
eight shot voices round-robin) and a room tail at most every 0.22 s. A real
MG42 burst isn't separate bangs but the shots running together into the
"ripping" sound, so each shot sample here is cut from a real burst as exactly
one cycle: from one shot's onset to the next one's, plus a short fade. Laid
back to back by the game at 50 ms they rebuild the burst as it was recorded.
The cycles are taken from the middle of bursts (the first round of a burst is
cleaner and quieter than the rest). The tail is the recording's own decay after
the last round of a burst.

Usage: python3 raw_assets/audio/build_mg42_real_sfx.py [out_dir]  (default assets/audio/sfx)
       --analyse prints the bursts and cycle lengths found in the source.
Needs numpy, scipy and ffmpeg (or the imageio-ffmpeg wheel).
"""
import glob
import os
import shutil
import subprocess
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fetched", "mg42")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = ARGS[0] if ARGS else "assets/audio/sfx"
SR = 44100
CYCLE = 0.050          # the game's 1,200 rpm


def ffmpeg():
    ff = shutil.which("ffmpeg")
    if not ff:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    return ff


def load(pattern, channels=2):
    paths = sorted(glob.glob(os.path.join(SRC, pattern)))
    if not paths:
        sys.exit(f"missing source {pattern} (run the Fetch sounds workflow)")
    raw = subprocess.run([ffmpeg(), "-v", "error", "-i", paths[0], "-ac", str(channels), "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).astype(np.float64)


def onsets(x, rel=0.3, gap=0.035, hp=1500.0):
    """Sample indices of shot onsets: peaks of the high-passed envelope, at least `gap` s apart."""
    b, a = signal.butter(2, hp / (SR / 2), "high")
    h = np.abs(signal.lfilter(b, a, x.mean(axis=1)))
    n = int(0.002 * SR)
    env = np.convolve(h, np.ones(n) / n, mode="same")
    idx, _ = signal.find_peaks(env, height=env.max() * rel, distance=int(gap * SR))
    return idx, env


def bursts(idx, max_gap=0.15):
    """Groups onsets into bursts (runs closer than max_gap s)."""
    out, cur = [], [idx[0]]
    for i in idx[1:]:
        if i - cur[-1] < max_gap * SR:
            cur.append(i)
        else:
            out.append(cur)
            cur = [i]
    out.append(cur)
    return out


def fade(x, fin, fout):
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def save(name, x, peak_db=-1.0):
    x = x / max(1e-9, np.abs(x).max()) * 10 ** (peak_db / 20)
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))
    print(f"wrote {name} ({len(x) / SR:.3f} s)")


def analyse(pattern):
    x = load(pattern)
    idx, _ = onsets(x)
    for k, bu in enumerate(bursts(idx)):
        d = np.diff(bu) / SR * 1000
        print(f"burst {k}: t={bu[0] / SR:7.2f}s  {len(bu):3d} rounds  cycle {np.median(d) if len(d) else 0:5.1f} ms")


# Sources (raw_assets/audio/fetched/mg42/, fetched by the "Fetch sounds" workflow; CC0):
# - shots: "Machine Gun Burst" (Freesound 482121, qubodup): a burst of a real 7.62 mm belt-fed gun
#   "extracted from US military video (public domain)", 48 kHz stereo. Its shots are 100 ms apart
#   (about 600 rpm: a PKM or M240 class gun, not an MG42); each is followed 40 ms later by a
#   quieter second transient (the echo off the range). No fetchable recording of a real MG42 or
#   MG3 yet (the Commons MG3 footage is rate-limited from the cloud), so each shot here is a
#   real gunshot and the MG42's 1,200 rpm rhythm comes from the game.
# - tail: "Authentic M60 Firing" (Freesound 538302, FranklinRook1984: "a real M60 machine gun
#   being fired"): the range's own decay after the burst ends (7.62x51, outdoors, ~30 dB over 1.3 s).
SHOT_SRC = "fs_482121_*"
SHOT_PICKS = (2, 5, 8, 11)      # which of the burst's 14 shots become mg42_shot_1..4
TAIL_SRC = "fs_538302_*"
TAIL_AT = 7.62                  # s: the M60 burst's last round; the decay follows
ECHO_AT = 0.036                 # s after a shot: duck from here (the echo lands at ~0.041)
ECHO_DUCK = 0.3
SHOT_LEN = CYCLE + 0.012
# The video's audio has almost nothing under 120 Hz (camera microphones). One short chest thump per
# shot, below the recording's range, gives back the weight a 7.62 round has close up (as the
# SPAS-12's real shot does); THUMP_DB is its level against the shot's peak.
THUMP_DB = -12.0
TARGET_DB = -12.2               # sustained fire, dB RMS (burst_rms)


def thump(n, variant):
    t = np.arange(n) / SR
    f = 92.0 + 4 * variant - 38.0 * np.minimum(t / 0.04, 1.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = (1 - np.exp(-t / 0.0015)) * np.exp(-t / 0.016)
    return np.sin(ph) * env


def shot_cut(x, i):
    """One real shot: from just before its onset through one game cycle, the echo held down."""
    a = i - int(0.0015 * SR)
    seg = x[a:a + int(SHOT_LEN * SR)].copy()
    t = np.arange(len(seg)) / SR - 0.0015
    g = np.ones_like(t)
    k = (t > ECHO_AT) & (t < ECHO_AT + 0.004)
    g[k] = np.linspace(1.0, ECHO_DUCK, k.sum())
    g[t >= ECHO_AT + 0.004] = ECHO_DUCK
    return fade(seg * g[:, None], 0.0008, 0.012)


def burst_rms(samples, seconds=1.0, gap=CYCLE):
    """Loudness of sustained fire as the game plays it: these samples every `gap` s, round-robin."""
    n = int((seconds + 0.5) * SR)
    acc = np.zeros((n, 2))
    k = 0
    while k * gap < seconds:
        s = samples[k % len(samples)]
        if s.ndim == 1:
            s = np.stack([s, s], axis=1)
        i = int(k * gap * SR)
        m = min(len(s), n - i)
        acc[i:i + m] += s[:m]
        k += 1
    body = acc[int(0.2 * SR):int(seconds * SR)]
    return 20 * np.log10(np.sqrt((body ** 2).mean()) + 1e-12)


def build():
    x = load(SHOT_SRC)
    idx, _ = onsets(x, rel=0.4, gap=0.08)
    shots = []
    for v, k in enumerate(SHOT_PICKS):
        s = shot_cut(x, idx[k])
        th = thump(len(s), v) * np.abs(s).max() * 10 ** (THUMP_DB / 20)
        shots.append(s + th[:, None])
    # The old synthesized shots' sustained loudness was -13.2 dB (burst_rms); +1 dB, so the mix doesn't move.
    target = TARGET_DB
    gain = 10 ** ((target - burst_rms(shots)) / 20)
    peak = max(np.abs(s).max() for s in shots) * gain
    if peak > 0.98:  # never clip: a soft limit on the peaks only
        shots = [np.tanh(s * gain / 0.98) * 0.98 for s in shots]
        gain = 1.0
    print(f"sustained fire: target {target:.1f} dB, new {burst_rms([s * gain for s in shots]):.1f} dB")
    for n, s in enumerate(shots, 1):
        write(f"mg42_shot_{n}", s * gain)
    y = load(TAIL_SRC)
    i = int(TAIL_AT * SR)
    tail = fade(y[i:i + int(1.6 * SR)], 0.01, 0.5)
    write("mg42_tail_1", tail / max(1e-9, np.abs(tail).max()) * 0.7)


def write(name, x):
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print(f"wrote {name} ({len(x) / SR:.3f} s)")


if __name__ == "__main__" and "--analyse" in sys.argv:
    for p in sorted(glob.glob(os.path.join(SRC, "*"))):
        if p.endswith((".flac", ".mp3", ".wav", ".ogg")):
            print("==", os.path.basename(p))
            analyse(os.path.basename(p))

elif __name__ == "__main__":
    build()
