---
name: perf-budget
description: Use when adding anything that costs frame time or memory in GRAFT (enemies, effects, lights, decals, ragdolls, assets) or when the owner sends phone measurements — the Moto G 5G budgets, how to measure, and how to update them.
---

# Performance budget

Target: Moto G 5G (2025) — Dimensity 6300, Mali-G57 MC2, 4 GB RAM, 720×1604 at 120 Hz (CLAUDE.md §8).

| Budget | Start value (replace with phone measurements) |
|---|---|
| Frame rate | 60 fps; locked 30 as a fallback setting |
| Render scale | 0.8–1.0 of 720p |
| Draw calls | ≤ 150 |
| Triangles on screen | ≤ 250k |
| Active enemies | ≤ 12 |
| Ragdolls simulating | ≤ 3, frozen after ~2.5 s |
| Blood stains | ≤ 48 large + 144 single drops and runs, oldest fade out; ≤ 320 drops in the air (one draw call, ≤ 110 trace rays a frame) |
| Gibs | ≤ 32 rigid bodies, one draw call each, frozen when still; chunks recycled before limbs (2026-11-11, for whole-body gibbing; not yet measured on the phone) |
| Live particles | ≤ 1,500 |
| Dynamic lights | ≤ 4; only one casts shadows |
| RAM | ≤ 1.2 GB |
| Heat | No throttling below target after 20 minutes |

## Measuring

- Only phone numbers count. Cloud screenshots run on a software rasterizer.
- **Map cost test** (Pause, Chinatown) is the phone measurement to ask for: GPU ms, render-CPU ms (`rcpu`), frame ms, triangles and draw calls per row: everything on, +10 triad men (with LODs and without), each atmosphere effect off, gun hidden, HUD hidden, 100/70/50 % resolution. Frame much higher than GPU means the CPU or pacing is the limit; GPU barely moving with resolution means the cost is vertices, fixed passes or the 2D layer, not pixels.
- **Cloud CPU probe** (`src/core/debug/perf_probe.gd`): `godot --headless -- --perf=15` on Chinatown runs the rolling spawns with a bot firing the M14 at random men, uncapped, and prints one JSON line: frame time split into frames with and without a physics tick (process vs process + physics cost), the slowest frames and what ran in them, peaks. `--perf-calm` (no bot, a steady 8 men), `--perf-exp=noanim|nopose|noai|hide|hidemap` (switch one system off), `--perf-dump` (visible geometry by kind). Scripts can time sections with `PerfProbe.add(&"name", usec)`. Not headless (xvfb + lavapipe) it also reports draw calls, triangles and render-CPU ms. Headless note: Godot sleeps `low_processor_usage_mode_sleep_usec` every frame when it can't draw; the probe sets it to 0.
- `Performance.TIME_PROCESS` / `TIME_PHYSICS_PROCESS` report the worst frame of the last second, not an average. Don't average them.
- 2026-11-12 cloud baseline (8 men fighting, Xeon 2.3 GHz): ~0.55 ms process per frame, ~1.8 ms with a physics tick; spikes were mesh merges (8–15 ms at a first cut, 5–10 ms at a spawn), now 1–3 ms and 3–6 ms.
- In-game debug overlay (on by default in debug builds): FPS, frame time avg/max, draw calls, primitives, memory, enemies/ragdolls/decals counts, renderer.
- Pause menu → "Run benchmark": fixed 20 s camera sweep of the test room; shows avg/p95/p99 frame time and saves JSON to `user://bench/`. The owner runs it once per renderer (Mobile and Compatibility, switched in the pause menu, then restart the app) and sends a screenshot.
- When measurements arrive: update the table above **and** CLAUDE.md §8 in the same commit, and add a playtest-log entry.

## Rules of thumb

- Pool everything spawned in combat (projectiles, decals, blood, gibs, sounds, ragdolls).
- One `CSGCombiner3D`/mesh per material per room chunk; share materials.
- Baked lighting + ≤ 4 dynamic lights; one shadow caster. On baked maps (Chinatown) the map's own lights are in the lightmap; the ~20 "character lights" (no shadows) skip the map's visual layer and only touch enemies, the player's gun and effects, so they don't count against the 4. Check them on the phone.
- Baked maps: one draw call per chunk (texture-array shader), ~315k triangles in total, small props in `_detail` meshes that stop drawing past 42 m.
- Textures ship at 2K at most: bake at 4K if you like, but set `process/size_limit=2048` in the `.import` file. On a 720p screen 4K looks the same and costs 4× the download and VRAM (four 4K guns pushed the APK to 356 MB and the owner's phone couldn't install it, 2026-11-05). Exception: the Chinatown lightmap (4096², one texture for the whole map).
- No per-frame allocations in hot paths (reuse arrays, avoid string building in `_process`).
- No mesh building on the main thread during play: `SurfaceTool` merges and `Mesh.surface_get_arrays()` (a GPU readback on Vulkan) belong on a worker thread or at load. Follow `TriadMeshBaker`: read source arrays once on the main thread, merge on `WorkerThreadPool`, finish the `ArrayMesh` on the main thread.
- Meshes built at runtime get no importer LODs: give them LODs (`ImporterMesh.generate_lods`, off the main thread). The triad men: −65 % of their triangles with LODs at the same picture.
- Full-screen 2D (HUD vignettes, overlays) runs at the phone's native 1604×720 whatever the 3D render scale: one pass at most, never stacked translucent layers.
- Mobile renderer first; Compatibility only if the M0 comparison says so.
