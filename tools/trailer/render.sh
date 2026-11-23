#!/bin/bash
# Renders one trailer shot with Godot's Movie Maker (docs/trailer.md).
# Usage: tools/trailer/render.sh <shot> [preview|final] [out_dir]
#   shot     src/trailer/shots/<shot>.gd; its "## scene:" line picks the map
#   preview  960x540, no MSAA (fast; the simulation is identical)
#   final    1920x1080, MSAA 4x
# Writes <out_dir>/<shot>/f########.png plus f.wav (the game's own audio).
# The renderer is Forward+ (TRAILER_RENDERER=mobile for the phone's look).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
SHOT="$1"; QUALITY="${2:-preview}"; OUT_BASE="${3:-trailer_out}"
SRC="src/trailer/shots/$SHOT.gd"
[ -f "$SRC" ] || { echo "no shot $SRC"; exit 1; }
SCENE="$(grep -m1 '^## scene:' "$SRC" | sed 's/^## scene: *//')"
[ -n "$SCENE" ] || SCENE="res://src/levels/chinatown/chinatown.tscn"
FRAMES="$(grep -m1 '^## frames:' "$SRC" | sed 's/^## frames: *//')"
[ -n "$FRAMES" ] || FRAMES=900
OUT="$OUT_BASE/$QUALITY/$SHOT${TRAILER_TAG:+_$TRAILER_TAG}"
mkdir -p "$OUT"; touch "$OUT_BASE/.gdignore"
find "$OUT" -name 'f*.png' -delete 2>/dev/null
W=960; H=540; MSAA=0
[ "$QUALITY" = "final" ] && { W=1920; H=1080; MSAA=2; }
UDIR="$HOME/.local/share/godot/app_userdata/GRAFT"
mkdir -p "$UDIR"
OVR="$UDIR/settings_override.cfg"
[ -f "$OVR" ] && cp "$OVR" "$OVR.trailer_bak"
cat > "$OVR" <<CFG
[display]
window/size/viewport_width=$W
window/size/viewport_height=$H
[rendering]
anti_aliasing/quality/msaa_3d=$MSAA
textures/default_filters/anisotropic_filtering_level=4
mesh_lod/lod_change/threshold_pixels=0.5
lights_and_shadows/directional_shadow/size=4096
lights_and_shadows/positional_shadow/atlas_size=4096
reflections/reflection_atlas/reflection_size=512
CFG
restore() { rm -f "$OVR"; [ -f "$OVR.trailer_bak" ] && mv "$OVR.trailer_bak" "$OVR"; }
trap restore EXIT
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
RENDERER="${TRAILER_RENDERER:-forward_plus}"
timeout "${TRAILER_TIMEOUT:-14400}" xvfb-run -a -s "-screen 0 ${W}x${H}x24" \
  godot --rendering-method "$RENDERER" --audio-driver Dummy --write-movie "$OUT/f.png" --fixed-fps 60 \
  --quit-after $((FRAMES + 30)) "$SCENE" -- --trailer="$SHOT" ${TRAILER_ARGS:-} 2>&1 \
  | grep -E "trailer|ERROR|SCRIPT|average|recorded" | grep -v "resources still in use" | head -60
echo "frames: $(ls "$OUT" | grep -c png) in $OUT"
