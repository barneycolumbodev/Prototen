# Tooling status

Checked 2026-11-01 in the first cloud session (CLAUDE.md §1 step 5, §10.4). Update this file when something changes.

| Tool | Status | Evidence / notes |
|---|---|---|
| Godot 4.7.2 (headless) | ✅ Works | `godot --version` → `4.7.2.stable.official.ed1daf0bf`. The environment setup script was not configured for this session, so Godot came from the same GitHub URL the script uses; `session_start.sh` now does this as a fallback. |
| `tools/check.sh` (import, script validation, GUT 9.7.1) | ✅ Works | 4/4 tests pass. Negative test: an untyped script makes it fail. Note: GUT exits 0 when a test file fails to parse, so `check.sh` also scans the log. |
| `tools/screenshot.sh`, Mobile renderer | ✅ Works | Xvfb + Mesa lavapipe (software Vulkan). Smoke scene captured from a fixed camera in a few seconds. |
| `tools/screenshot.sh`, Compatibility renderer | ✅ Works | Same scene through OpenGL (llvmpipe). |
| `godot --doctool` | ✅ Works | Dumped 810 class files for 4.7.2. |
| Blender binary 5.2.3 | ❌ Blocked | `download.blender.org` is not in this environment's network allowlist (proxy refuses the connection). |
| Blender via `bpy` 5.2.3 from PyPI | ✅ Works (fallback) | `tools/blender.sh raw_assets/_smoke/test_render.py out.png`: Cycles CPU render of a bevelled cube in ~2 s, glTF export OK. Setup script and SessionStart hook install it when the binary is missing. Limits: no Blender UI (none needed); MPFB still needs `extensions.blender.org` (untested). |
| Godot Agent Loop MCP (`@beremaran/godot-agent-loop@2`) | ❌ Not found | npm returns 404 for the package; the GitHub repo is not reachable from this session. `.mcp.json` keeps the entry from §10.2, but the server cannot start. Screenshots use `tools/screenshot.sh` meanwhile; scripted-input scenarios can be done as GUT scene tests. |
| GitHub Actions CI | ✅ Works | Run #1 on `main` (2026-11-01, ~90 s): 21 scripts validated, 32/32 GUT tests, signed arm64 debug APK (28 MB) published to the `dev-latest` release. Signed with a throwaway key until the keystore secrets are set. Note: the workflow only registered with GitHub once it existed on `main`. |
| Android SDK in the session | ❌ Blocked | `dl.google.com` is not reachable. Not needed: Android exports run in CI (§10.1). |
| SessionStart hook | ✅ Works | `tools/session_start.sh` prints versions and setup errors when `CLAUDE_CODE_REMOTE=true`, silent otherwise. |
| `.claude/settings.json` permission allowlist | ⚠️ Not added | The session's safety check refused a settings file that pre-approves commands for Claude. Only the SessionStart hook is configured. The owner can add an allowlist if prompts get in the way. |
| On-phone debug overlay | ✅ Built (cloud-verified) | FPS, frame/GPU/CPU time, draw calls, primitives, memory, VRAM, enemy/ragdoll/decal counts, controller name, benchmark results. Needs a phone run. |
| Benchmark + renderer switch | ✅ Built (cloud-verified) | Pause menu → Run benchmark (20 s fixed sweep), or `-- --bench=<s>` on the command line. Renderer switch writes `user://settings_override.cfg`; after a restart the game ran on Compatibility/OpenGL. Lavapipe frame times are meaningless; phone numbers decide. |
| Bug-report button, input recording | ⏳ Later | Not started; planned after M0. |

## Session 2 notes (2026-11-01)

- This session had no setup script again: Godot came from the SessionStart fallback; `mesa-vulkan-drivers` had no install candidate, so `tools/screenshot.sh` fell back to the Compatibility renderer (OpenGL/llvmpipe) for all M1a screenshots. Looks are comparable; Mobile-renderer frame times still need the phone.
- `pip install bpy` failed (pypi.org didn't resolve from the background install). Not needed for M1a: the pistol's moving parts were split from the existing glTF with `split_parts.py` (plain Python).

## Session 3 notes (2026-11-01)

- `bpy` 5.2.3 installed fine this session (`/opt/bpy-venv`), so the MG42 and its arms were modelled and baked with Cycles on the CPU (MG42: 4K maps, ~20 min per bake on 4 cores).
- `scipy` wasn't installed for the system Python; `pip install scipy` worked (needed by `raw_assets/audio/*.py`).
- The Godot Agent Loop MCP server failed to connect again (package still missing); screenshots use `tools/screenshot.sh` with the new `--demo=hip|ads|burst` and `--weapon=<index>` capture args.

## Session 5 notes (2026-11-04, M1b/M1c)

- No setup script again: Godot from the SessionStart fallback. No Vulkan driver in the container (`VK_KHR_surface` missing), so screenshots use the Compatibility renderer.
- `bpy` 5.2.3 worked; Pillow had to be installed into `/opt/bpy-venv` for preview sheets, and scipy into the system Python for the sound scripts (`pip install pillow` / `pip install scipy`).
- `extensions.blender.org`, `static.makehumancommunity.org`, `quaternius.com`, Poly Haven and ambientCG are still blocked, so the triad enemy is fully procedural (no MPFB, no Quaternius animations).
- The Godot Agent Loop MCP server still fails to connect. Gameplay was checked with GUT scene tests, headless debug runs and `tools/screenshot.sh` with `--demo=gore` / `--waves --god`.

## Session 6 notes (2026-11-04, Chinatown docks map)

- Fonts: GitHub raw downloads are blocked for repos outside this session, but npm works: Noto Serif/Sans TC came from `@fontsource/*` packages (OFL).
- Blender's compositor (OIDN denoise) needs a GPU/EGL context in background mode and hangs; the lightmap is smoothed with a coverage-aware blur instead (`bake.py`).
- Pillow's WebP encoder drops colour under alpha = 0 unless `exact=True` (the albedo array keeps its emission mask in alpha).
- The glTF exporter flips V on every UV set, including the custom data channel: `envkit` writes `1 - wet` so the shader reads `wet`.
- Final lightmap bake: 4096², 128 samples, 412 lights, about 11 minutes on 4 CPU cores. Re-exporting with `--nobake` reuses the lightmap (the unwrap is deterministic; checked).
- Screenshots are still Compatibility/llvmpipe only (no Vulkan in the container), so the Mobile renderer's reflection probes (wet-street reflections) are unverified until the phone.

## What the owner can fix in the environment settings (claude.ai/code)

1. **Network access → Custom**, keep the defaults, add the hosts in CLAUDE.md §10.1 (at least `download.blender.org`, `extensions.blender.org`, `api.polyhaven.com`, `dl.polyhaven.org`, `ambientcg.com`).
2. **Setup script**: paste `tools/setup_env.sh`.
3. **Repository secrets** (GitHub → Settings → Secrets → Actions) for a stable APK signature: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEYSTORE_ALIAS`. Without them CI signs each build with a new throwaway key, so the old APK must be uninstalled before installing a new one.
