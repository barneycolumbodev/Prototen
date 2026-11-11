#!/usr/bin/env python3
"""Spoken enemy callouts: every line in every triad voice (docs/design.md §5.6).

Owner, 2026-11-11: "I can't hear the actual voices of them in the game."
Until now callouts were subtitles only. This renders each line with
Kokoro-82M (Apache-2.0 neural text-to-speech, run locally with
onnxruntime) in several male voices, then shapes it into a combat shout:
pitched up a little (rendered slower, played faster: no vocoder smear),
high-passed, pushed through a soft clipper and a compressor, with a lift in
the 2-4 kHz presence band so it cuts through gunfire.

Outputs:
  assets/audio/voice/<voice>/<category>_<n>.ogg   (n = index of the line)
  src/ai/voice_lines.gd                           (generated: the lines and voices)

The model comes from npm (this session's network allows npm, not Hugging
Face): `kokoro-q8-shards` holds model_quantized.onnx from
onnx-community/Kokoro-82M-v1.0-ONNX in six pieces (sha256 checked below);
`kokoro-js` (hexgrad, the model's author) ships the voice style vectors.
Both are fetched with `npm pack` into --cache the first time.

Optional check: --verify <faster-whisper model dir> transcribes every clip
with Whisper and fails if a line doesn't come back as written. That is how
the lines were checked in the cloud session (no one could listen).

Run (Python deps: kokoro-onnx soundfile scipy; ffmpeg with libvorbis):
  python3 raw_assets/audio/build_callout_voices.py [--cache DIR] [--verify DIR] [--only voice]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from scipy import signal

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT_DIR = os.path.join(ROOT, "assets", "audio", "voice")
GD_OUT = os.path.join(ROOT, "src", "ai", "voice_lines.gd")
MODEL_SHA = "fbae9257e1e05ffc727e951ef9b9c98418e6d79f1c9b6b13bd59f5c9028a1478"
SR = 24000

# Situation -> lines. The index of a line is its file number. Keep lines short:
# they're shouted across a street in a firefight.
LINES = {
    "contact": ["Augment!", "Contact!", "It's him, the augment!", "There! Shoot him!", "Over there!"],
    "flee": ["Run!", "Pull back!", "He's a machine!", "Get out of here!"],
    "surrender": ["Don't shoot!", "I give up!", "Please! Enough!"],
    "cower": ["No! No! No!", "Help me!", "Stay away from me!"],
    "gut": ["I'm hit! I'm hit!", "Argh, my gut!", "I'm hit! Help me!"],
    "legs": ["My legs!", "I can't walk!"],
    "reload": ["Reloading!", "Cover me, reloading!", "Changing mag!"],
    "man_down": ["Man down!", "They got Ah-Keung!", "He's dead! He's dead!", "Brother's down!"],
    "officer_down": ["They got the Red Pole!", "The Red Pole is down!"],
    "pinned": ["I'm pinned!", "Keep your heads down!", "He's got us pinned!"],
    "lost": ["Where'd he go?", "I lost him!", "Find him!"],
    "advance": ["Move up!", "Rush him!", "Go, go, go!"],
    "burning": ["I'm burning!", "Put it out!"],
    "grabbed": ["Get off me!", "Let me go!"],
    "limb_off": ["My arm! My arm!", "Oh god, my arm!"],
    "rally": ["Hold your ground!", "Nobody runs!"],
}

# Voice id -> (Kokoro voice, language, pitch-up factor, render speed). The
# clip is rendered at `speed`, then played `pitch` times faster: pitch rises
# by that factor and the tempo ends at speed * pitch.
VOICES = {
    "v1": ("am_michael", "en-us", 1.12, 1.0),
    "v2": ("am_fenrir", "en-us", 1.10, 1.02),
    "v3": ("am_puck", "en-us", 1.09, 1.0),
    "v4": ("am_onyx", "en-us", 1.14, 0.98),
    "v5": ("am_echo", "en-us", 1.10, 1.02),
    "v6": ("bm_george", "en-gb", 1.12, 1.0),
}


def npm_fetch(cache):
    model = os.path.join(cache, "kokoro-q8.onnx")
    voices = os.path.join(cache, "voices.npz")
    if os.path.exists(model) and os.path.exists(voices):
        return model, voices
    os.makedirs(cache, exist_ok=True)
    work = tempfile.mkdtemp(dir=cache)
    for pkg in ("kokoro-js@1.2.1", "kokoro-q8-shards@1.0.0"):
        subprocess.run(["npm", "pack", pkg], cwd=work, check=True, stdout=subprocess.DEVNULL)
    for tgz in [f for f in os.listdir(work) if f.endswith(".tgz")]:
        d = os.path.join(work, tgz[:-4])
        os.makedirs(d)
        subprocess.run(["tar", "xzf", os.path.join(work, tgz), "-C", d], check=True)
    shards = os.path.join(work, "kokoro-q8-shards-1.0.0", "package")
    with open(model + ".tmp", "wb") as out:
        for i in range(6):
            with open(os.path.join(shards, f"kokoro-q8.part{i}.bin"), "rb") as f:
                shutil.copyfileobj(f, out)
    h = hashlib.sha256(open(model + ".tmp", "rb").read()).hexdigest()
    if h != MODEL_SHA:
        sys.exit(f"model checksum mismatch: {h}")
    os.replace(model + ".tmp", model)
    vdir = os.path.join(work, "kokoro-js-1.2.1", "package", "voices")
    data = {}
    for f in os.listdir(vdir):
        if f.endswith(".bin"):
            data[f[:-4]] = np.fromfile(os.path.join(vdir, f), dtype=np.float32).reshape(-1, 1, 256)
    np.savez(voices, **data)
    return model, voices


def shout(x, pitch):
    """Render-slow-play-fast pitch shift, then shape it into a shout."""
    x = x.astype(np.float64)
    # Pitch up: resample to fewer samples, same rate.
    n_out = int(round(len(x) / pitch))
    x = signal.resample_poly(x, 1000, int(round(1000 * pitch)))[:n_out]
    # High-pass (no chest boom on a phone speaker), presence lift around 3 kHz.
    sos = signal.butter(2, 110, "highpass", fs=SR, output="sos")
    x = signal.sosfilt(sos, x)
    b, a = signal.iirpeak(3000, 1.2, fs=SR)
    x = x + 0.55 * signal.lfilter(b, a, x)
    # Normalise, drive a soft clipper (strain), then a gentle compressor.
    x = x / (np.max(np.abs(x)) + 1e-9)
    drive = 2.4
    x = np.tanh(x * drive) / np.tanh(drive)
    env = np.abs(x)
    att, rel = np.exp(-1 / (0.002 * SR)), np.exp(-1 / (0.08 * SR))
    e = np.zeros_like(env)
    lvl = 0.0
    for i, v in enumerate(env):
        lvl = att * lvl + (1 - att) * v if v > lvl else rel * lvl + (1 - rel) * v
        e[i] = lvl
    thr, ratio = 0.35, 3.0
    gain = np.where(e > thr, (thr + (e - thr) / ratio) / np.maximum(e, 1e-9), 1.0)
    x = x * gain
    # Trim silence, short fades, peak at -1 dBFS.
    idx = np.nonzero(np.abs(x) > 0.02 * np.max(np.abs(x)))[0]
    if len(idx):
        x = x[max(0, idx[0] - int(0.01 * SR)):idx[-1] + int(0.06 * SR)]
    f = int(0.004 * SR)
    x[:f] *= np.linspace(0, 1, f)
    x[-f * 4:] *= np.linspace(1, 0, f * 4)
    return (x / (np.max(np.abs(x)) + 1e-9) * 0.89).astype(np.float32)


def write_ogg(path, x):
    import soundfile as sf
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        sf.write(t.name, x, SR, subtype="PCM_16")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", t.name, "-c:a", "libvorbis", "-q:a", "5", path],
                   check=True)
    os.remove(t.name)


def norm(s):
    words = re.sub(r"[^a-z ]", "", s.lower().replace("-", " ").replace("'", "")).split()
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]


# Names and fillers can be spelled any way; every other word must be heard.
LOOSE = {"ah", "keung", "argh", "oh"}


class Listener:
    """Whisper (faster-whisper): what a clip says, and whether that's the line."""

    def __init__(self, model_dir):
        from faster_whisper import WhisperModel
        self.m = WhisperModel(model_dir, device="cpu", compute_type="int8")

    def hear(self, x, sr=SR):
        from math import gcd
        g = gcd(sr, 16000)
        a = signal.resample_poly(x, 16000 // g, sr // g).astype(np.float32)
        segs, _ = self.m.transcribe(a, language="en", beam_size=3)
        return " ".join(s.text.strip() for s in segs)

    def check(self, x, text):
        heard = self.hear(x)
        want, got = norm(text), norm(heard)
        missing = [w for w in want if w not in got and w not in LOOSE]
        # Repeated words ("No! No! No!") must be heard as often as written.
        short = any(got.count(w) < want.count(w) for w in set(want) if w not in LOOSE)
        return not missing and not short, heard


def write_gd():
    vo = ", ".join(f'&"{v}"' for v in VOICES)
    rows = []
    for cat, lines in LINES.items():
        items = ", ".join(json.dumps(s) for s in lines)
        rows.append(f'\t&"{cat}": [{items}],')
    src = (
        "class_name VoiceLines\n"
        "extends RefCounted\n"
        "## Generated by raw_assets/audio/build_callout_voices.py: don't edit by hand.\n"
        "## Every callout line (subtitle text) by situation, and the triad voices\n"
        "## that speak them. Clip: res://assets/audio/voice/<voice>/<situation>_<n>.ogg,\n"
        "## n = index of the line.\n\n"
        "const DIR: String = \"res://assets/audio/voice/\"\n"
        f"const VOICES: Array[StringName] = [{vo}]\n"
        "const LINES: Dictionary[StringName, Array] = {\n" + "\n".join(rows) + "\n}\n\n\n"
        "static func path(voice: StringName, situation: StringName, index: int) -> String:\n"
        "\treturn \"%s%s/%s_%d.ogg\" % [DIR, voice, situation, index]\n"
    )
    with open(GD_OUT, "w") as f:
        f.write(src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.expanduser("~/.cache/graft-tts"))
    ap.add_argument("--verify", default="", help="faster-whisper model dir: transcribe and check every clip")
    ap.add_argument("--only", default="", help="one voice id")
    ap.add_argument("--cats", default="", help="comma-separated situations to render (default: all)")
    args = ap.parse_args()
    from kokoro_onnx import Kokoro
    model, voices = npm_fetch(args.cache)
    k = Kokoro(model, voices)
    ear = Listener(args.verify) if args.verify else None
    cats = set(args.cats.split(",")) if args.cats else set(LINES)
    done, bad = 0, []
    for vid, (kv, lang, pitch, speed) in VOICES.items():
        if args.only and vid != args.only:
            continue
        for cat, lines in LINES.items():
            if cat not in cats:
                continue
            for i, text in enumerate(lines):
                # Kokoro reads "Ah-Keung" as two words; the name keeps its spelling in the subtitle.
                spoken = text.replace("Ah-Keung", "Ah Keung")
                # With --verify, a take Whisper mishears is rendered again a bit slower or faster.
                for take, sp in enumerate((speed, speed * 0.9, speed * 1.08, speed * 0.82)):
                    a, sr = k.create(spoken, voice=kv, speed=sp, lang=lang)
                    assert sr == SR
                    x = shout(a, pitch)
                    if ear is None:
                        break
                    ok, heard = ear.check(x, text)
                    if ok:
                        break
                path = os.path.join(OUT_DIR, vid, f"{cat}_{i}.ogg")
                write_ogg(path, x)
                done += 1
                if ear is not None:
                    print(f"  {vid}/{cat}_{i}: '{text}' -> '{heard}'" + ("" if ok else "  MISMATCH") +
                          (f" (take {take + 1})" if take else ""))
                    if not ok:
                        bad.append(f"{vid}/{cat}_{i}")
        print(f"{vid} ({kv}) done")
    write_gd()
    if ear is not None:
        print(f"verify: {done - len(bad)}/{done} lines heard as written" + (f"; misheard: {', '.join(bad)}" if bad else ""))


if __name__ == "__main__":
    main()
