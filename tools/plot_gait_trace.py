#!/usr/bin/env python3
"""Plots docs/previews/gait_trace.png from the CSV that tools/gait_trace.gd prints.

Usage: godot --headless -s res://tools/gait_trace.gd | grep -E '^[0-9t]' > trace.csv
       python3 tools/plot_gait_trace.py trace.csv
The "before" speed curve re-runs the 2026-11-11 ground model (same inputs).
"""
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

rows = list(csv.DictReader(open(sys.argv[1])))
t = [float(r["t"]) for r in rows]


def col(k):
    return [float(r[k]) for r in rows]


dt = 1 / 60
v = 0.0
old = []
for tt in t:
    if (0.2 <= tt < 1.6) or (2.2 <= tt < 3.4):
        v = min(v + min(70, (6.5 - v) * 14 + 2) * dt, 6.5)
    else:
        v = max(v - min(55, v * 16 + 2.5) * dt, 0)
    old.append(v)
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NEW, OLD, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK})
fig, ax = plt.subplots(3, 1, figsize=(8, 8.6), sharex=True, facecolor=BG)
marks = [(0.2, "walk forward"), (1.6, "let go"), (2.2, "strafe right"), (3.4, "let go")]
for a in ax:
    a.set_facecolor(BG)
    a.grid(True, color=GRID, lw=0.8)
    a.spines[["top", "right"]].set_visible(False)
    for x0, _ in marks:
        a.axvline(x0, color=INK2, lw=0.8, ls=(0, (2, 3)))
ax[0].plot(t, old, color=OLD, lw=2, label="before (11-11)")
ax[0].plot(t, col("speed"), color=NEW, lw=2, label="now")
ax[0].set_ylabel("ground speed (m/s)")
ax[0].set_ylim(0, 8.6)
ax[0].legend(frameon=False, loc="center right")
for x0, lab in marks:
    ax[0].text(x0 + 0.03, 7.9, lab, color=INK2, fontsize=9)
ax[0].set_title("Walk, stop, strafe, stop: speed, head and footfalls", loc="left", fontsize=12, color=INK)
hy = [y * 1000 for y in col("head_y")]
ax[1].plot(t, hy, color=NEW, lw=2)
ff = [tt for tt, r in zip(t, rows) if r["footfall"] != "0"]
ax[1].plot(ff, [min(hy) - 2.5] * len(ff), "v", color=INK2, ms=8, label="heel strike (footstep sound)")
ax[1].set_ylabel("head height (mm)")
ax[1].legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0), borderaxespad=0)
ax[2].plot(t, col("head_pitch"), color=NEW, lw=2, label="pitch (+ nose down)")
ax[2].plot(t, col("head_roll"), color=AQUA, lw=2, label="roll (− right side down)")
ax[2].set_ylabel("head turn (°)")
ax[2].set_xlabel("seconds")
ax[2].set_ylim(-1.0, 1.0)
ax[2].legend(frameon=False, loc="upper right", ncol=2)
fig.text(0.01, 0.005, "Before, the camera only translated: no head motion and no footsteps. "
         "Traces from the game code (tools/gait_trace.gd).", color=INK2, fontsize=8.5)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig("docs/previews/gait_trace.png", dpi=110, facecolor=BG)
