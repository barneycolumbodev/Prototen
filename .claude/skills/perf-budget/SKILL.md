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
| Blood decals | ≤ 48, oldest fade out |
| Live particles | ≤ 1,500 |
| Dynamic lights | ≤ 4; only one casts shadows |
| RAM | ≤ 1.2 GB |
| Heat | No throttling below target after 20 minutes |

## Measuring

- Only phone numbers count. Cloud screenshots run on a software rasterizer.
- In-game debug overlay (on by default in debug builds): FPS, frame time avg/max, draw calls, primitives, memory, enemies/ragdolls/decals counts, renderer.
- Pause menu → "Run benchmark": fixed 20 s camera sweep of the test room; shows avg/p95/p99 frame time and saves JSON to `user://bench/`. The owner runs it once per renderer (Mobile and Compatibility, switched in the pause menu, then restart the app) and sends a screenshot.
- When measurements arrive: update the table above **and** CLAUDE.md §8 in the same commit, and add a playtest-log entry.

## Rules of thumb

- Pool everything spawned in combat (projectiles, decals, blood, gibs, sounds, ragdolls).
- One `CSGCombiner3D`/mesh per material per room chunk; share materials.
- Baked lighting + ≤ 4 dynamic lights; one shadow caster.
- No per-frame allocations in hot paths (reuse arrays, avoid string building in `_process`).
- Mobile renderer first; Compatibility only if the M0 comparison says so.
