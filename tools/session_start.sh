#!/bin/bash
# SessionStart hook (CLAUDE.md §10.6). Prints tool status; imports the project if needed.
# Keep output short: it goes into Claude's context every session.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT" || exit 0
GODOT_VERSION="${GODOT_VERSION:-4.7.2}"
ERR=/opt/setup-errors.log

# Fallback: if the environment's setup script didn't install Godot, fetch it here (about 60 MB).
if ! command -v godot >/dev/null 2>&1 && [ -w /opt ]; then
  mkdir -p /opt/godot
  if curl -fsSL -o /tmp/godot.zip \
      "https://github.com/godotengine/godot-builds/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip" \
      && unzip -q -o /tmp/godot.zip -d /opt/godot \
      && mv "/opt/godot/Godot_v${GODOT_VERSION}-stable_linux.x86_64" /opt/godot/godot; then
    chmod +x /opt/godot/godot && ln -sf /opt/godot/godot /usr/local/bin/godot
    echo "session_start: installed Godot ${GODOT_VERSION} (setup script did not)"
  else
    echo "Godot fallback download failed (session_start.sh)" >> "$ERR"
  fi
  rm -f /tmp/godot.zip
fi

echo "Godot:   $(godot --headless --version 2>/dev/null | tail -n1 || echo 'NOT INSTALLED')"
if command -v blender >/dev/null 2>&1 && [ -x "$(readlink -f "$(command -v blender)")" ]; then
  echo "Blender: $(blender --version 2>/dev/null | head -n1)"
elif [ -x /opt/bpy-venv/bin/python ]; then
  echo "Blender: bpy module $(/opt/bpy-venv/bin/python -c 'import bpy; print(bpy.app.version_string)' 2>/dev/null) (no binary; use tools/blender.sh)"
else
  echo "Blender: NOT INSTALLED. Installing the bpy module in the background (tools/blender.sh will use it)."
  if [ -w /opt ]; then
    nohup bash -c 'python3 -m venv /opt/bpy-venv && /opt/bpy-venv/bin/pip install -q "bpy==${BLENDER_VERSION:-5.2.3}" || echo "bpy fallback install failed (session_start.sh)" >> /opt/setup-errors.log' >/tmp/bpy-install.log 2>&1 &
  fi
fi
if [ -s "$ERR" ]; then
  echo "Setup errors ($ERR):"
  sed 's/^/  /' "$ERR"
fi

if [ ! -d .godot ] && command -v godot >/dev/null 2>&1; then
  echo "Importing project (no .godot/ yet)..."
  timeout 300 godot --headless --import >/tmp/godot-import.log 2>&1 \
    && echo "Import done." || echo "Import failed; see /tmp/godot-import.log"
fi
exit 0
