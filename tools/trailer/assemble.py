#!/usr/bin/env python3
"""Cuts the trailer together (docs/trailer.md).

Reads tools/trailer/edit.json: the clips (a rendered shot and the frame range
to use, straight from Movie Maker's PNG sequence and its WAV), the captions,
the end card and the score. Renders the text (titles.py) and the score
(raw_assets/trailer/score.py), grades, mixes the game's own audio under the
score, and encodes H.264 1080p60 (or the preview size).

Usage: assemble.py [preview|final] [out.mp4]
"""
import json
import os
import numpy as np
from scipy.io import wavfile
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EDIT = os.path.join(ROOT, "tools/trailer/edit.json")
FPS = 60


def main():
    quality = sys.argv[1] if len(sys.argv) > 1 else "preview"
    edit = json.load(open(EDIT))
    w, h = (1920, 1080) if quality == "final" else (960, 540)
    base = os.path.join(ROOT, "trailer_out", quality)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "trailer_out", "graft_trailer_%s.mp4" % quality)
    work = os.path.join(base, "_edit")
    os.makedirs(work, exist_ok=True)

    subprocess.run([sys.executable, os.path.join(ROOT, "tools/trailer/titles.py"), EDIT, work, str(w), str(h)], check=True)
    score = os.path.join(work, "score.wav")
    subprocess.run([sys.executable, os.path.join(ROOT, "raw_assets/trailer/score.py"), score, "--edit", EDIT], check=True)

    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    fc = []
    vlabels = []
    alabels = []
    idx = 0
    t = 0.0
    for k, c in enumerate(edit["clips"]):
        if c["shot"] == "black":
            frames = c["frames"]
            dur = frames / FPS
            fc.append("color=c=black:s=%dx%d:r=%d:d=%.4f,setsar=1,format=yuv420p[v%d]" % (w, h, FPS, dur, k))
            fc.append("anullsrc=r=48000:cl=stereo,atrim=duration=%.4f[a%d]" % (dur, k))
            vlabels.append("[v%d]" % k)
            alabels.append("[a%d]" % k)
            print("clip %2d black %5.2fs at %6.2fs" % (k, dur, t))
            t += dur
            continue
        d = os.path.join(base, c["shot"])
        frames = c["out"] - c["in"]
        args += ["-framerate", str(FPS), "-start_number", str(c["in"]), "-i", os.path.join(d, "f%08d.png")]
        vi = idx
        idx += 1
        args += ["-i", os.path.join(d, "f.wav")]
        ai = idx
        idx += 1
        chain = "[%d:v]trim=end_frame=%d,setpts=PTS-STARTPTS,scale=%d:%d:flags=lanczos,format=gbrp" % (vi, frames, w, h)
        if c.get("grade"):
            chain += "," + c["grade"]
        dur = frames / FPS
        if c.get("fade_in"):
            chain += ",fade=t=in:st=0:d=%.3f" % c["fade_in"]
        if c.get("fade_out"):
            chain += ",fade=t=out:st=%.3f:d=%.3f" % (dur - c["fade_out"], c["fade_out"])
        chain += ",setsar=1,format=yuv420p[v%d]" % k
        fc.append(chain)
        vlabels.append("[v%d]" % k)
        a0 = c["in"] / FPS
        # Level each clip's game audio to the same loudness, then trim.
        sr, x = wavfile.read(os.path.join(d, "f.wav"))
        x = x.astype(np.float64) / (2 ** 31 if x.dtype == np.int32 else 2 ** 15 if x.dtype == np.int16 else 1.0)
        seg = x[int(a0 * sr):int((a0 + dur) * sr)]
        rms_db = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else -60.0
        target = edit.get("mix", {}).get("clip_rms_db", -19.0)
        gain = 10 ** ((target - rms_db) / 20.0) * c.get("gain", 1.0)
        gain = min(gain, 4.0)
        achain = "[%d:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start=%.4f:end=%.4f,asetpts=PTS-STARTPTS,volume=%.3f" % (ai, a0, a0 + dur, gain)
        achain += ",afade=t=in:st=0:d=0.01,afade=t=out:st=%.4f:d=0.02[a%d]" % (max(dur - 0.02, 0), k)
        fc.append(achain)
        alabels.append("[a%d]" % k)
        print("clip %2d %-14s %5d-%5d  %5.2fs  at %6.2fs" % (k, c["shot"], c["in"], c["out"], dur, t))
        t += dur
    # The end card.
    title_dir = os.path.join(work, "title")
    tn = len([f for f in os.listdir(title_dir) if f.endswith(".png")])
    args += ["-framerate", str(FPS), "-i", os.path.join(title_dir, "t%05d.png")]
    ti = idx
    idx += 1
    fc.append("[%d:v]setpts=PTS-STARTPTS,scale=%d:%d,setsar=1,format=yuv420p[vt]" % (ti, w, h))
    vlabels.append("[vt]")
    tdur = tn / FPS
    fc.append("anullsrc=r=48000:cl=stereo,atrim=duration=%.4f[at]" % tdur)
    alabels.append("[at]")
    print("title at %.2fs (%.2fs)" % (t, tdur))
    total = t + tdur
    n = len(vlabels)
    fc.append("%sconcat=n=%d:v=1:a=0[vcat]" % ("".join(vlabels), n))
    fc.append("%sconcat=n=%d:v=0:a=1[game]" % ("".join(alabels), n))
    # The look: a touch of contrast and colour, teal shadows and warm highs,
    # a vignette and fine grain. The end card skips none of it (it's black).
    grade = edit.get("grade", "eq=contrast=1.07:saturation=1.1:gamma=0.97,colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.03,vignette=angle=PI/4.5,noise=alls=5:allf=t")
    fc.append("[vcat]%s[vg]" % grade)
    last = "vg"
    for k, cap in enumerate(edit.get("captions", [])):
        args += ["-framerate", str(FPS), "-i", os.path.join(work, "cap%d" % k, "c%05d.png")]
        ci = idx
        idx += 1
        fc.append("[%d:v]format=rgba,setpts=PTS-STARTPTS+%.4f/TB[c%d]" % (ci, cap["t0"], k))
        fc.append("[%s][c%d]overlay=eof_action=pass:enable='between(t,%.4f,%.4f)'[vo%d]" % (last, k, cap["t0"], cap["t1"], k))
        last = "vo%d" % k
    fc.append("[%s]format=yuv420p[vout]" % last)
    # Sound: the game under the score; the score ducks a little under gunfire.
    args += ["-i", score]
    si = idx
    idx += 1
    mixcfg = edit.get("mix", {})
    fc.append("[game]volume=%.3f,asplit=2[g1][g2]" % mixcfg.get("game", 1.0))
    fc.append("[%d:a]volume=%.3f[sc]" % (si, mixcfg.get("score", 0.8)))
    fc.append("[sc][g1]sidechaincompress=threshold=0.08:ratio=3:attack=4:release=180[scd]")
    fc.append("[scd][g2]amix=inputs=2:normalize=0,alimiter=limit=0.93:attack=2:release=60,atrim=duration=%.4f[aout]" % total)
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-r", str(FPS)]
    if quality == "final":
        args += ["-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high", "-tune", "film"]
    else:
        args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"]
    args += ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    print("trailer: %s (%.2fs)" % (out, total))
    if quality == "final":
        # A 9:16 version for phone feeds: the frame centred over a blurred,
        # darkened fill of itself.
        vert = out.replace(".mp4", "_vertical.mp4")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", out, "-filter_complex",
                        "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                        "boxblur=28:4,eq=brightness=-0.12:saturation=0.8[bg];[b]scale=1080:-2[fg];"
                        "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]",
                        "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                        "-c:a", "copy", "-movflags", "+faststart", vert], check=True)
        print("trailer: %s (vertical)" % vert)


if __name__ == "__main__":
    main()
