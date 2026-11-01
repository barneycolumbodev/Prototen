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
| GitHub Actions CI | ⏳ Pending first run | Workflow added. The Android export was verified locally: signed arm64 debug APK (28 MB), `apksigner verify` OK, using a minimal SDK made from Ubuntu's `apksigner`/`adb` packages. CI uses the runner's real Android SDK. |
| Android SDK in the session | ❌ Blocked | `dl.google.com` is not reachable. Not needed: Android exports run in CI (§10.1). |
| SessionStart hook | ✅ Works | `tools/session_start.sh` prints versions and setup errors when `CLAUDE_CODE_REMOTE=true`, silent otherwise. |
| `.claude/settings.json` permission allowlist | ⚠️ Not added | The session's safety check refused a settings file that pre-approves commands for Claude. Only the SessionStart hook is configured. The owner can add an allowlist if prompts get in the way. |
| On-phone debug overlay, benchmark | 🚧 M0 | Being built in M0. |

## What the owner can fix in the environment settings (claude.ai/code)

1. **Network access → Custom**, keep the defaults, add the hosts in CLAUDE.md §10.1 (at least `download.blender.org`, `extensions.blender.org`, `api.polyhaven.com`, `dl.polyhaven.org`, `ambientcg.com`).
2. **Setup script**: paste `tools/setup_env.sh`.
3. **Repository secrets** (GitHub → Settings → Secrets → Actions) for a stable APK signature: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEYSTORE_ALIAS`. Without them CI signs each build with a new throwaway key, so the old APK must be uninstalled before installing a new one.
