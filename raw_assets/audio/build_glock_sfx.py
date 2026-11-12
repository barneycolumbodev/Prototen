"""Glock 22 (.40 S&W, auto sear) player sounds: glock_shot_1..3 and glock_tail_1.

Unsuppressed .40: a hard supersonic-ish crack and a short, punchy blast, plus the
light rattle of the slide cycling at ~1,200 rpm. Reuses the enemy gun synth.

Usage: python3 raw_assets/audio/build_glock_sfx.py [out_dir]  (default assets/audio/sfx)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_enemy_sfx as e  # noqa: E402

w = e.w


def tail():
    sec = 0.9
    return w.at(sec, (0.0, w.band(w.noise(sec), 180, 2200) * w.env(sec, 0.01, 0.22) * 0.5))


def write_all():
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/audio/sfx"
    w.OUT = out
    os.makedirs(out, exist_ok=True)
    for v in (1, 2, 3):
        slide = (0.008, w.click(0.035, (2100 + 90 * v, 3400, 5200), 0.008, bright=1900) * 0.45)
        w.save(f"glock_shot_{v}", e.gun(v, 1.1, 260, 8000, 120, 0.045, sec=0.28, mech=slide), -2)
    w.save("glock_tail_1", tail(), -8)
    print(f"wrote glock sounds to {out}")


if __name__ == "__main__":
    write_all()
