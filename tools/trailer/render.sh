#!/bin/bash
# Renders one trailer shot (src/core/debug/trailer_director.gd) to PNG frames
# with Godot's Movie Maker under Xvfb and software Vulkan, 1920x804 @ 30 fps.
# Usage: tools/trailer/render.sh <shot> <out_dir> [scene] [extra user args...]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
SHOT="$1"; OUT="$2"; SCENE="${3:-res://src/levels/chinatown/chinatown.tscn}"; shift 3 2>/dev/null || shift $#
W="${TRAILER_W:-1920}"; H="${TRAILER_H:-804}"
mkdir -p "$OUT"
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
# Movie Maker records at the window size: override it for this run only.
printf '[display]\nwindow/size/window_width_override=%s\nwindow/size/window_height_override=%s\n' "$W" "$H" > override.cfg
timeout "${TRAILER_TIMEOUT:-3000}" xvfb-run -a -s "-screen 0 ${W}x${H}x24" \
  godot --rendering-method mobile --rendering-driver vulkan --audio-driver Dummy \
  --write-movie "$OUT/f.png" --fixed-fps 30 "$SCENE" -- --trailer="$SHOT" "$@" 2>&1 \
  | grep -E "trailer:|SCRIPT ERROR|Movie|recorded" | head -20
rm -f override.cfg
