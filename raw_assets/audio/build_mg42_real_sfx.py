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


if __name__ == "__main__" and "--analyse" in sys.argv:
    for p in sorted(glob.glob(os.path.join(SRC, "*"))):
        if p.endswith((".flac", ".mp3", ".wav", ".ogg")):
            print("==", os.path.basename(p))
            analyse(os.path.basename(p))
