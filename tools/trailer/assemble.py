"""Cuts the GRAFT trailer from timeline.py: grades and letterboxes every
segment to 1920x804 @ 30 fps, adds the text cards and the title, mixes the
game audio with the score. Usage: assemble.py <out.mp4> [--only i,j]"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as TL

S = os.path.dirname(HERE)
RENDER = f"{S}/render"
FOOT = f"{S}/footage"
WORK = f"{S}/work"
SRC = {"big": f"{FOOT}/asset_765657886.mp4", "a": f"{FOOT}/asset_765690058.mp4", "b": f"{FOOT}/asset_765692830.mp4"}
CROP = {"big": "crop=500:209:110:719", "a": "crop=1111:465:247:175", "b": "crop=1111:465:247:175"}
W, H, FPS, WARM = 1920, 804, 30, 14
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
GRADE = ("eq=contrast=1.13:brightness=-0.015:saturation=1.12,"
         "colorbalance=rs=-0.045:gs=-0.01:bs=0.05:rm=0.01:rh=0.05:gh=0.015:bh=-0.045,"
         "vignette=angle=0.6,noise=alls=3:allf=t+u")
os.makedirs(WORK, exist_ok=True)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(" ".join(args))
        print(r.stderr[-3000:])
        raise SystemExit(1)


def spaced(text):
    return "  ".join(" ".join(w) for w in text.split(" "))


def fade_alpha(t_in, t_out, ramp=0.35):
    return (f"if(lt(t,{t_in}),0,if(lt(t,{t_in + ramp}),(t-{t_in})/{ramp},"
            f"if(lt(t,{t_out - ramp}),1,if(lt(t,{t_out}),({t_out}-t)/{ramp},0))))")


def text_filter(o, lower):
    txt = spaced(o["text"]).replace(":", "\\:").replace("'", "")
    size = 38 if lower else 54
    y = "h*0.80" if lower else "(h-text_h)/2"
    return (f",drawtext=fontfile={FONT}:text='{txt}':fontsize={size}:fontcolor=white:"
            f"x=(w-text_w)/2:y={y}:shadowcolor=black@0.7:shadowx=0:shadowy=2:"
            f"alpha='{fade_alpha(o['text_in'], o['text_out'])}'")


def segment(i, kind, src, st, dur, o):
    v = f"{WORK}/seg{i:02d}.mp4"
    a = f"{WORK}/seg{i:02d}.wav"
    n = round(dur * FPS)
    vol = o.get("audio", 1.0)
    lower = i >= 5
    txt = text_filter(o, lower) if "text" in o else ""
    flash = ",fade=in:st=0:d=0.18:color=white" if o.get("flash") else ""
    if "gamma" in o:
        flash = f",eq=gamma={o['gamma']}:brightness=0.04" + flash
    afade = f"afade=in:d=0.012,afade=out:st={dur - 0.02:.3f}:d=0.02"
    venc = ["-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", "-r", str(FPS)]
    if kind == "eng":
        start = WARM + round(st * FPS)
        d = f"{RENDER}/{src}"
        run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-start_number", str(start), "-i", f"{d}/f%08d.png",
             "-frames:v", str(n), "-vf", f"scale={W}:{H},{GRADE}{txt}{flash}", *venc, v])
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{WARM / FPS + st:.4f}", "-i", f"{d}/f.wav", "-t", f"{dur:.4f}",
             "-af", f"aresample=48000,volume={vol},apad,atrim=0:{dur:.4f},{afade}", "-ac", "2", a])
    elif kind in SRC:
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.3f}", "-i", SRC[kind], "-t", f"{dur + 0.5:.3f}",
             "-vf", f"{CROP[kind]},fps={FPS},scale={W}:{H}:flags=lanczos,unsharp=5:5:0.9:3:3:0.0,{GRADE}{txt}{flash}",
             "-frames:v", str(n), "-an", *venc, v])
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.3f}", "-i", SRC[kind], "-t", f"{dur:.4f}", "-vn",
             "-af", f"aresample=48000,volume={vol},apad,atrim=0:{dur:.4f},{afade}", "-ac", "2", a])
    elif kind == "black":
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r={FPS}", "-frames:v", str(n), *venc, v])
        silence(a, dur)
    elif kind == "title":
        title(v, dur, n, venc)
        silence(a, dur)


def silence(a, dur):
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur:.4f}", a])


def title(v, dur, n, venc):
    bg = f"{RENDER}/menu/f00000145.png"
    t1 = TL.CUES["tagline"] - TL.CUES["title"]
    big = spaced("GRAFT").replace("  ", " ")
    tag = spaced("A POWER FANTASY YOU HAVE TO EARN.")
    foot = spaced("IN DEVELOPMENT FOR ANDROID")
    fc = (
        f"[0:v]scale={W}:{H},boxblur=18:2,eq=brightness=-0.30:saturation=0.6,"
        f"zoompan=z='1.04+0.0009*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}[bg];"
        f"color=black@0.0:s={W}x{H}:r={FPS},format=rgba,"
        f"drawtext=fontfile={FONT_BLACK}:text='{big}':fontsize=168:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-40,"
        f"split[t1][t2];[t2]boxblur=14:2,colorchannelmixer=aa=0.85[glow];"
        f"[bg][glow]overlay=format=auto[g1];[g1][t1]overlay=format=auto,"
        f"drawtext=fontfile={FONT}:text='{tag}':fontsize=36:fontcolor=0xd8c9a3:x=(w-text_w)/2:y=h/2+86:"
        f"alpha='{fade_alpha(t1 - (TL.CUES['title'] - TL.CUES['title']), dur + 1, 0.5)}',"
        f"drawtext=fontfile={FONT}:text='{foot}':fontsize=22:fontcolor=0xa0a0a0:x=(w-text_w)/2:y=h-90:"
        f"alpha='{fade_alpha(t1 + 1.0, dur + 1, 0.5)}',"
        f"rgbashift=rh=-8:bh=8:enable='lt(t,0.25)',"
        f"fade=in:st=0:d=0.12:color=white,fade=out:st={dur - 0.9:.2f}:d=0.9,{GRADE}[out]"
    )
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", bg, "-filter_complex", fc, "-map", "[out]",
         "-frames:v", str(n), *venc, v])


def main():
    out = sys.argv[1]
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    segs = TL.apply_overrides()
    for i, (kind, src, st, dur, o) in enumerate(segs):
        if only is None or i in only:
            print(f"seg {i:02d} {kind} {src or ''} {st} {dur}", flush=True)
            segment(i, kind, src, st, dur, o)
    if only is not None:
        return
    with open(f"{WORK}/v.txt", "w") as f:
        for i in range(len(segs)):
            f.write(f"file 'seg{i:02d}.mp4'\n")
    with open(f"{WORK}/a.txt", "w") as f:
        for i in range(len(segs)):
            f.write(f"file 'seg{i:02d}.wav'\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/v.txt", "-c", "copy", f"{WORK}/video.mp4"])
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/a.txt", "-c:a", "pcm_s16le", f"{WORK}/game.wav"])
    run(["python3", f"{HERE}/score.py", f"{WORK}/score.wav"])
    mix = ("[1:a]acompressor=threshold=0.08:ratio=4:attack=5:release=120:makeup=2,volume=0.85[g];"
           "[2:a]volume=0.95[m];[g][m]amix=inputs=2:normalize=0,alimiter=limit=0.95:level=false[a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{WORK}/video.mp4", "-i", f"{WORK}/game.wav", "-i", f"{WORK}/score.wav",
         "-filter_complex", mix, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "256k", "-shortest",
         "-movflags", "+faststart", out])
    print("wrote", out)


if __name__ == "__main__":
    main()
