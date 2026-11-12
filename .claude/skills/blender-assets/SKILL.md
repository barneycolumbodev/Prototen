---
name: blender-assets
description: Use when creating or changing any 3D asset for GRAFT — Blender 5.2 driven by Python in background mode, one generator script per asset in raw_assets/, preview render before commit, glTF export into assets/.
---

# Making assets with Blender

The owner doesn't make assets; Claude does (CLAUDE.md §7). Build gameplay with primitive shapes first, then replace them with finished assets.

## Rules

- Every asset has a generator script: `raw_assets/<category>/<asset>/build.py`. Running it rebuilds the asset from nothing. Never hand-edit an exported file.
- Run: `tools/blender.sh raw_assets/<...>/build.py --out assets/<category>/<asset>.glb --preview /tmp/preview.png` (Blender binary if installed, else the `bpy` module from PyPI)
- Real dimensions in metres. +Y up in Godot (glTF exporter converts from Blender's Z-up). Pivot where the game needs it (weapons: grip; props: base centre).
- Hard-surface: modifiers (bevel, boolean, mirror, array, weighted normals). Apply on export.
- Materials: procedural shaders, baked to texture maps with Cycles on the CPU, then exported as PNG; Godot compresses to ETC2/ASTC on import.
- Each asset: LODs if over ~5k triangles, a simple collision mesh (`-col` suffix or a separate convex hull), correct scale and pivots, glTF (`.glb`) export.
- After each change render a preview (turntable or four views), Read it, and only then commit. Send the important ones to the owner.
- Detail goes first to first-person arms, weapons and augment hardware (always on screen), then hit effects and gore, lighting, enemies, environments (docs/design.md §6).

## Smoke test

`tools/blender.sh raw_assets/_smoke/test_render.py /tmp/smoke.png` builds a bevelled cube and renders it with Cycles on the CPU.

## Humans and animation

- MPFB (MakeHuman for Blender) for rigged bodies; record the asset-pack license in CREDITS.md.
- Animation starts from Quaternius's Universal Animation Library (CC0), retargeted, plus procedural aiming, hit reactions and ragdoll in Godot.

## Budgets

See perf-budget. Keep first-person weapons under ~15k triangles at LOD0 and enemies under ~20k.

## High → low bake (reference: raw_assets/weapons/pistol_57/build.py)

- Build HIGH (smooth bevels, dense cylinders, embossed text) and LOW (game mesh) from the same code with a detail setting.
- UV-unwrap LOW (smart project, then scale islands for surfaces the player sees most before packing).
- Bake HIGH → LOW with selected-to-active: channels via EMIT (route each Principled input to an Emission shader), AO, tangent NORMAL. Pack AO/roughness/metal into one ORM texture; multiply AO into base colour for cavity grime.
- Export glTF **separate** (`.gltf` + `.bin` + `textures/`) so Godot imports each texture on its own.
- After the first import, set every texture's `.import` to `compress/mode=2` (VRAM, ETC2/ASTC), `mipmaps/generate=true`, and `compress/normal_map=1` on normal maps. Godot's headless import defaults to lossless. `tests/unit/test_weapon_assets.gd` checks this.
- Check it in-engine: `tools/screenshot.sh res://src/levels/lookdev/weapon_lookdev.tscn /tmp/shots`.

## Sculpted (SDF) parts and bake pitfalls (reference: raw_assets/weapons/glock22/build.py)

- Moulded polymer (frames, grips) reads best as one `raw_assets/_lib/sdf.py` sculpt with smooth unions; steel stays hard-surface.
- Offset the SDF grid by odd fractions of a cell. A flat face that lands exactly on a grid plane makes the mesher emit stair-step slivers, which show up as noise, fake wear and black bake wedges.
- LOW from a sculpt: mesh a coarser grid (~0.9 mm) and decimate once, without the symmetry option. Finer bases, symmetry and multi-pass decimation fold triangles over each other (z-fighting slivers). The Glock's `--diagnose` counts folds.
- Parts that sit within a few mm of each other (slide on frame, magazine in grip): explode them apart for the bake, or rays pick up the neighbour's surface (olive/yellow islands in the normal map).
- On LOW: clear custom normals, mark sharp by angle (~35°), unwrap with the same angle, then area-weighted normals. Long triangles otherwise smear gradients across flat faces.
- No pointiness edge-wear on sculpted meshes; the fine mesh noise reads as speckled wear.
- A grip texture from a 3D voronoi goes flat wherever a curved surface slices between cell centres. Project a 2D pattern three ways (triplanar).
