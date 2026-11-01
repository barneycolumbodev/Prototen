#!/bin/bash
# Cloud environment setup script (CLAUDE.md §10.1).
# The owner pastes this file's contents into the environment's "Setup script" field at claude.ai/code.
# Runs as root before Claude starts. Must exit 0. Cached if it finishes in about 5 minutes.
GODOT_VERSION="${GODOT_VERSION:-4.7.2}"
BLENDER_SERIES="${BLENDER_SERIES:-5.2}"
BLENDER_VERSION="${BLENDER_VERSION:-5.2.3}"
ERR=/opt/setup-errors.log

apt-get update -qq || true
apt-get install -y -qq xvfb xauth mesa-vulkan-drivers libvulkan1 libgl1 libegl1 \
  libxi6 libxxf86vm1 libxfixes3 libxrender1 libsm6 libxkbcommon0 libxcursor1 \
  libxinerama1 libxrandr2 libasound2t64 fontconfig unzip xz-utils || echo "apt install failed" >> "$ERR"

# Godot editor (Linux, runs headless in the session)
if [ ! -x /opt/godot/godot ]; then
  mkdir -p /opt/godot
  curl -fsSL -o /tmp/godot.zip \
    "https://github.com/godotengine/godot-builds/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip" \
    && unzip -q -o /tmp/godot.zip -d /opt/godot \
    && mv "/opt/godot/Godot_v${GODOT_VERSION}-stable_linux.x86_64" /opt/godot/godot \
    && chmod +x /opt/godot/godot \
    || echo "Godot download failed" >> "$ERR"
  rm -f /tmp/godot.zip
fi
ln -sf /opt/godot/godot /usr/local/bin/godot

# Blender (Linux build, used in background mode)
if [ ! -x /opt/blender/blender ]; then
  mkdir -p /opt/blender
  curl -fsSL "https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
    | tar -xJ --strip-components=1 -C /opt/blender \
    || echo "Blender download failed" >> "$ERR"
fi
ln -sf /opt/blender/blender /usr/local/bin/blender
exit 0
