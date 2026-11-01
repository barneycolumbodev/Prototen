---
name: blender-assets
description: Use when creating or changing any 3D asset for GRAFT — Blender 5.2 driven by Python in background mode, one generator script per asset in raw_assets/, preview render before commit, glTF export into assets/.
---

# Making assets with Blender

The owner doesn't make assets; Claude does (CLAUDE.md §7). Build gameplay with primitive shapes first, then replace them with finished assets.

## Rules

- Every asset has a generator script: `raw_assets/<category>/<asset>/build.py`. Running it rebuilds the asset from nothing. Never hand-edit an exported file.
- Run: `blender -b --factory-startup --python raw_assets/<...>/build.py -- --out assets/<category>/<asset>.glb --preview /tmp/preview.png`
- Real dimensions in metres. +Y up in Godot (glTF exporter converts from Blender's Z-up). Pivot where the game needs it (weapons: grip; props: base centre).
- Hard-surface: modifiers (bevel, boolean, mirror, array, weighted normals). Apply on export.
- Materials: procedural shaders, baked to texture maps with Cycles on the CPU, then exported as PNG; Godot compresses to ETC2/ASTC on import.
- Each asset: LODs if over ~5k triangles, a simple collision mesh (`-col` suffix or a separate convex hull), correct scale and pivots, glTF (`.glb`) export.
- After each change render a preview (turntable or four views), Read it, and only then commit. Send the important ones to the owner.
- Detail goes first to first-person arms, weapons and augment hardware (always on screen), then hit effects and gore, lighting, enemies, environments (docs/design.md §6).

## Smoke test

`blender -b --factory-startup --python raw_assets/_smoke/test_render.py -- /tmp/smoke.png` builds a bevelled cube and renders it with Cycles on the CPU.

## Humans and animation

- MPFB (MakeHuman for Blender) for rigged bodies; record the asset-pack license in CREDITS.md.
- Animation starts from Quaternius's Universal Animation Library (CC0), retargeted, plus procedural aiming, hit reactions and ragdoll in Godot.

## Budgets

See perf-budget. Keep first-person weapons under ~15k triangles at LOD0 and enemies under ~20k.
