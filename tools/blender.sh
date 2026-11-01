#!/bin/bash
# Run a Blender Python script in background mode (CLAUDE.md §10.3).
# Uses the Blender binary if it is installed; otherwise falls back to the
# bpy module from PyPI in /opt/bpy-venv (same Blender version, no UI).
#
# Usage: tools/blender.sh <script.py> [script args...]
#   e.g. tools/blender.sh raw_assets/_smoke/test_render.py /tmp/smoke.png
set -uo pipefail
[ $# -ge 1 ] || { echo "usage: tools/blender.sh <script.py> [args...]" >&2; exit 2; }
script="$1"; shift
BPY_PY="${BPY_PY:-/opt/bpy-venv/bin/python}"
if command -v blender >/dev/null 2>&1 && [ -x "$(readlink -f "$(command -v blender)")" ]; then
  exec blender -b --factory-startup --python "$script" -- "$@"
elif [ -x "$BPY_PY" ]; then
  exec "$BPY_PY" "$script" -- "$@"
else
  echo "Neither Blender nor the bpy module is installed. See tools/setup_env.sh." >&2
  exit 1
fi
