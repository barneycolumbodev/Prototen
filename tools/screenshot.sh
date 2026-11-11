#!/bin/bash
# Render screenshots in the cloud session (CLAUDE.md §10.4).
# Runs a scene under Xvfb with software Vulkan (Mesa lavapipe). CaptureDirector
# (src/core/debug/capture_director.gd) visits every Camera3D in the
# "capture_cameras" group, then the active camera, saves one PNG each, and quits.
#
# Usage: tools/screenshot.sh [scene] [out_dir] [renderer]
#   scene     res:// path (default: the main scene)
#   out_dir   default: screenshots/
#   renderer  mobile (default) or gl_compatibility
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SCENE="${1:-}"
OUT="$(mkdir -p "${2:-screenshots}" && cd "${2:-screenshots}" && pwd)"
METHOD="${3:-mobile}"
GODOT="${GODOT:-godot}"
LVP=/usr/share/vulkan/icd.d/lvp_icd.json
[ -f "$LVP" ] && export VK_ICD_FILENAMES="$LVP"
DRIVER=vulkan
[ "$METHOD" = "gl_compatibility" ] && DRIVER=opengl3

[ -d .godot ] || timeout 600 "$GODOT" --headless --import >/dev/null 2>&1

RES="${SHOT_RES:-1280x720}"
args=(--rendering-method "$METHOD" --rendering-driver "$DRIVER" --resolution "$RES" --audio-driver Dummy)
[ -n "$SCENE" ] && args+=("$SCENE")
timeout "${SHOT_TIMEOUT:-180}" xvfb-run -a -s "-screen 0 ${RES}x24" \
  "$GODOT" "${args[@]}" -- --capture-dir="$OUT" ${CAPTURE_ARGS:-} 2>&1 \
  | grep -E "capture|ERROR|SCRIPT" | grep -v "^$" | head -40
ls -1 "$OUT"/*.png 2>/dev/null
