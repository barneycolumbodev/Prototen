---
name: godot-verify
description: Use before claiming any GRAFT gameplay or code change works — runs the import/validate/GUT check, takes cloud screenshots, and looks up Godot 4.7 APIs in the local class reference instead of memory.
---

# Verifying GRAFT changes

The owner only has a phone. A change is "done" only with evidence: a passing test, a screenshot you looked at, a CI log, or playtest notes (CLAUDE.md §1).

## 1. Static check and tests — every change

```bash
tools/check.sh                    # import, load every script, run all GUT tests
tools/check.sh -gselect=test_stick   # one test file while iterating
```

- Static-typing warnings are errors. A script that fails to parse makes `check.sh` fail even though GUT itself would exit 0.
- Logs land in `/tmp/graft-check/` (`import.log`, `validate.log`, `gut.log`).
- New logic gets a GUT test in `tests/unit/` (`extends GutTest`, files named `test_*.gd`). Put pure maths (curves, damage, budgets) in static functions so it can be tested without a scene.

## 2. Screenshots — every visible change

```bash
tools/screenshot.sh                                   # main scene, all capture cameras
tools/screenshot.sh res://src/levels/test_room.tscn /tmp/shots
tools/screenshot.sh "" /tmp/shots gl_compatibility    # Compatibility renderer
CAPTURE_ARGS="--capture-only=CapOverview" tools/screenshot.sh
```

- Software Vulkan (lavapipe) under Xvfb; budget about 30 s per shot.
- Each test room has fixed `Camera3D` nodes in the `capture_cameras` group. Add one when a new area needs checking; don't move existing ones (screenshots stay comparable).
- Open the PNG with the Read tool and look at it before saying anything about visuals. Send the important ones to the owner with SendUserFile.
- Lavapipe frame times say nothing about phone performance. Only phone numbers count (see perf-budget).

## 3. API reference — before using an unfamiliar API

```bash
godot --headless --doctool /tmp/godot-doc   # once per session
grep -A20 'name="PhysicalBoneSimulator3D"' /tmp/godot-doc/doc/classes/*.xml
```

Godot 4.7 changed some APIs (e.g. keyboard/mouse device IDs are no longer 0). Check the dump, not memory.

## 4. CI

CI (`.github/workflows/ci.yml`) runs the same GUT suite, exports the debug APK and publishes it to the `dev-latest` release. Check runs with REST only: `gh run list`, `gh api repos/{owner}/{repo}/actions/runs`. Never push git tags.
