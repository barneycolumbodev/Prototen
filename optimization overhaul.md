# GRAFT — Optimization Overhaul

| | |
|---|---|
| Status | Phase 1 built 2026-11-13 (see §12); waiting for the phone. Phase 0 skipped by the owner. |
| Date | 2026-11-13 |
| Target | Moto G 5G (2025): Dimensity 6300 (2× Cortex-A76 + 6× A55), Mali-G57 MC2, 4 GB RAM, 720×1604 at 120 Hz |
| Goal | A steady 60 fps in Chinatown combat with no loss of look |
| Engine | Godot 4.7.2, Mobile renderer (Vulkan), Jolt, typed GDScript |
| Scope | Rendering, content, CPU, frame pacing, memory, build, measurement |

How to read the task labels: **Look** says whether the picture changes (none / check / changes). **Size** is the expected gain (S under 0.5 ms, M 0.5–2 ms, L over 2 ms of a 16.7 ms frame). **Conf** is how sure I am. Gains are estimates until the phone measures them; only numbers in §3 are measurements.

---

## 1. Summary

**Where the game is.** Chinatown went from 28–29 fps (2026-11-05) to about 45 (2026-11-12) to "sometimes 60 at 70 % with variable resolution" now. The last phone measurement that broke the frame down is from 2026-11-07: GPU 17.9 ms and frame 21.5 ms at 60 % resolution. The frame is right at the 16.7 ms line, so anything extra (a fight, a hot spot of the map, a warm phone) pushes it over.

**What the audit found.** Six things explain most of the inconsistency:

1. **Missing 60 costs more than it looks.** On a 120 Hz screen a late frame waits for the next refresh, so it is shown for 25 ms (40 fps), not 17. An average of 45 fps is roughly one frame in three at 60 pace and two in three at 40 pace. The frame-pacing library is also in a mode that is allowed to lower the target by itself (F-01).
2. **Any render scale under 100 % adds a full-screen pass.** Confirmed in the engine source: at exactly 100 % the Mobile renderer draws and tonemaps in one pass; at 99 % or less it stores the picture, then runs a second pass over the whole 1604×720 screen. So lowering resolution saves less than expected, and 100 % is cheaper per pixel than 90 % (F-02).
3. **The renderer does not draw near things first.** Confirmed in the engine source: opaque objects are ordered by material, not by distance, and this renderer has no depth pre-pass. The world can be drawn before the gun that then covers a large part of it (F-03).
4. **The world shader does work it throws away**, and distance culling of small props is switched off in the map build (F-05, F-06).
5. **Enemy logic is the biggest CPU item**, the game ships as a debug build, and everything runs on one thread (F-10, F-11, F-12).
6. **Deploying some augments adds 70–107 draw calls at once** (F-09).

**The plan.** Five phases, each ending in an APK and a phone measurement:

| Phase | What | Look |
|---|---|---|
| 0 | Measure: frame-time histogram, a longer cost test, a release-mode APK | none |
| 1 | Free wins: pacing, draw order, shader waste, merged models, texture limits | none |
| 2 | Structural: resolution controller, world variants, AI and animation scheduling, pooling, loading | none to check |
| 3 | Only if still short: lighter world lighting, renderer switch, art-direction options | check to changes |
| 4 | Lock budgets, add CI guards, update the docs | none |

I expect Phases 1 and 2 to be enough for a steady 60 at 70–85 %, and I think 100 % is reachable because of finding 2. That is a judgement, not a measurement; Phase 0 decides.

**What I need from you:** install the Phase 0 build, run three tests from the pause menu, send the screenshots (§9).

---

## 2. Definition of done

"Buttery smooth" as numbers, measured on the phone in Chinatown with rolling spawns:

| Measure | Target |
|---|---|
| Frames at or under 16.7 ms | ≥ 99 % over a 5-minute fight |
| Frames over 33 ms | none after the first 10 seconds |
| 1 % low | ≥ 55 fps |
| After 20 minutes of play | the same numbers (no thermal slide) |
| Render scale | never below the chosen floor; no visible resolution pumping |
| Picture | fixed-camera captures match the current build side by side, unless a change was approved |

Working budgets that leave headroom for a warm phone:

| Budget | Target |
|---|---|
| GPU time | ≤ 12.5 ms at the shipped scale, worst sustained view |
| Main-thread CPU | ≤ 10 ms (scripts ≤ 2, physics tick ≤ 4, render submission ≤ 4) |
| Draw calls | ≤ 110 typical, ≤ 150 peak including a deployed augment |
| Triangles | ≤ 150k typical, ≤ 200k peak |
| Blended overdraw | ≤ 1.5 screens in the worst case |
| Video memory | ≤ 450 MB |

These replace the guesses in CLAUDE.md §8 once the phone confirms them.

---

## 3. Evidence

### 3.1 Phone measurements on record

| Date | Result |
|---|---|
| 2026-11-05 | Chinatown 28–29 fps. Test range smooth. |
| 2026-11-07 | Map cost test at 60 % scale: GPU 17.9 ms, frame 21.5 ms. Bloom off: −3.2 ms. Reflections, water streaks, ripples, rain, steam, fog: each within ±0.3 ms. About 46 fps in play. |
| 2026-11-12 | About 45 fps at 70 % with variable resolution. |
| 2026-11-13 | Sometimes 60 at 70 % with variable resolution. |

Not on record: the cost test added on 2026-11-12 (gun hidden, HUD hidden, +10 men, 100/70/50 %), and the Mobile-versus-Compatibility renderer comparison planned for M0. Both are in Phase 0.

### 3.2 Measured in the cloud for this audit

The cloud has no GPU, so these count draw calls, triangles and CPU time only.

Chinatown, Mobile renderer on software Vulkan, 1280×720, rolling spawns with the bot fight, camera turning, 20 s:

| | Average | 95th percentile |
|---|---|---|
| Draw calls | 86 | 134 |
| Triangles | 114k | 252k |
| Render CPU (Xeon) | 0.88 ms | 1.13 ms |

CPU, headless, eight men alive, one system off per run:

| Run | Frame without a physics tick | Frame with one tick |
|---|---|---|
| Everything on | 0.69 ms | 2.45 ms |
| Enemy logic off | 0.61 ms | 1.15 ms |
| Animation off | 0.47 ms | 2.08 ms |
| Skeleton off | 0.55 ms | 1.96 ms |
| Aim pose off | 0.58 ms | 2.20 ms |
| Bot fight (not calm) | 0.60 ms | 2.03 ms, one 13.4 ms frame in 20 s |

Enemy logic is about 1.3 ms per tick for eight men (0.16 ms a man). The phone's big cores in a debug build are plausibly 2–3× slower, which I have not measured.

Content counts read from the files:

| Item | Count |
|---|---|
| Map | 115 meshes (60 main, 39 glow, 16 glass), 313,056 triangles |
| Map LODs | 313k → 133k → 48k across the first three levels; 21 small meshes have none |
| Densest cells | 27.8k and 25.1k triangles |
| Baked lights / live character lights | 412 / 20 (11 spot, 9 omni, ranges 5–14 m) |
| Character lights reaching a point | 0 at 35 % of the map, 1 at 42 %, 2 at 18 %, 3–6 at 5 % |
| Reflection probes | 9; a 12 m cell overlaps 0–5 of them |
| World textures | 3 arrays × 36 layers × 1024² |
| Viewmodels in the player scene | 7 guns and 6 arm sets, all loaded at once, 2K texture sets each |
| First-person view | 22k (MP5) + 8k (arms) triangles, always at full detail |
| Augment models, draw calls | GX-4 107, fan shield 102, whip 90, knife 73, drone 29 |
| Texture memory if every asset were loaded | about 680 MB upper bound |

### 3.3 Confirmed in the Godot 4.7.2 source

- Render scale other than 1.0 disables the single-pass path (`render_forward_mobile.cpp:973`, `renderer_viewport.cpp:147`). Bloom and screen-space anti-aliasing do the same.
- Opaque sort key, most to least significant: render priority, shader, material, mesh, surface, depth band (`render_forward_mobile.h:484–506`). The depth band is 1/16 of the camera range, 18.7 m here.
- No depth pre-pass in the Mobile renderer; FSR upscaling works only in Forward+ (settings reference).
- Each mesh takes at most 8 omni lights, 8 spot lights and 8 reflection probes. Lights whose mask excludes a mesh are not paired with it, so the baked map pays for no character lights (`renderer_scene_cull.cpp:190`). Probes pair with every layer by default, so they also apply to men and the gun (`:224`).
- Texture sharpness bias is log2(scale): −0.51 at 70 %, −0.74 at 60 % (`renderer_viewport.cpp:284`).
- Android frame pacing (Swappy) is on, in mode 2, which "will often downgrade the max FPS until it finds a value that can be maintained".
- Rendering runs on the main thread by default (`thread_model = 1`).
- Half-precision shader variants are used automatically where the GPU supports them.

### 3.4 Not known

Everything about the phone's GPU beyond the 2026-11-07 table: how the frame scales with resolution, what the gun, the men and the HUD cost, whether the limit today is GPU, CPU or pacing, and whether the screen stays at 120 Hz while the game runs.

---

## 4. How a frame is built on this phone

At a render scale under 100 % (today):

1. **Scene pass** at the scaled size: opaque, sky, transparent.
2. **Post pass** at 1604×720: tonemap (AgX), saturation and contrast, upscale.
3. **HUD pass** at 1604×720.
4. **Copy to the screen** at 1604×720.

At exactly 100 %, steps 1 and 2 are one pass. A tile-based GPU like the Mali pays for every extra pass in memory traffic, whatever the pass draws.

Pixel counts: 100 % is 1.155 megapixels, 70 % is 0.566 (49 %), 60 % is 0.416 (36 %).

**Why 45 fps feels worse than it sounds.** At 120 Hz a frame can be shown for 8.3, 16.7, 25 or 33 ms. A frame that takes 17.5 ms is shown for 25. A stream that averages 45 fps is a mix of 60-pace and 40-pace frames, which reads as judder. Two consequences: shaving the last 1–2 ms matters a lot, and a locked 40 would look smoother than a wandering 45.

---

## 5. Findings

Severity: **A** likely several ms or a direct cause of inconsistency, **B** likely 0.5–2 ms, **C** small or memory only.

**F-01 (A) Frame pacing is left on automatic.** Swappy mode 2 may lower the target frame rate by itself, and the game offers only 60 and 30 caps (`src/core/settings.gd:14`). No histogram exists, so an average hides what is happening. *Confidence: high on the mechanism, unmeasured on the phone.*

**F-02 (A) Reduced resolution forces a second full-screen pass.** See §3.3 and §4. The variable resolution also moves in arbitrary steps between 60 % and the chosen maximum (`src/core/adaptive_resolution.gd:98`); each change reallocates the render buffers. With the maximum at 70 % it has a 10-point range to work in.

**F-03 (A) Opaque draw order ignores distance.** The world is one material, so its 99 cells are drawn in load order, and whether the gun is drawn before or after them is arbitrary. The Mali's hidden-pixel removal catches some of this, not all. *Confidence: high on the order, medium on the cost.*

**F-04 (B) Reduced resolution makes textures shimmer.** The engine sharpens textures by half to three-quarters of a mip level at 70–60 %, with no anti-aliasing to settle it. This is part of the "grainier" picture reported on 2026-11-07, and sharper mips also cost memory traffic.

**F-05 (B) The world shader pays for rain on every pixel.** `world.gdshader:78` reads the puddle noise twice for walls, ceilings and indoor surfaces, where the result is multiplied by zero. The albedo array is filtered anisotropically on every surface (`:15`). The 4096² lightmap is read without mipmaps (`:91`).

**F-06 (B) Small props are never culled by distance.** The level sets a 42 m limit for meshes named `_detail` (`chinatown.gd:246`), but the map build has `k.detail = False` (`raw_assets/levels/chinatown/build.py:385`) and the map contains no such mesh. The two densest cells alone are 53k triangles at full detail.

**F-07 (B) Men: the wound loop runs in full for every pixel.** `triad.gdshader:223` evaluates up to eight wounds with several smoothsteps each, near a wound or not; a wounded man also computes 16 noise hashes a pixel. Corpses are the most wounded and are seen up close. The shader is two-sided for the whole body (`:24`). `triad_basecolor.png` is 4096² and `triad_skin.png` 2048×4096 with no size limit, against the project's own 2K rule.

**F-08 (B) The first-person view is heavier than it needs to be.** About 30k triangles always at full detail, a large share of the screen (not yet measured), three anisotropic samplers on the arms (`suit_paint.gdshader:10–12`), reflection probes applied, and it may be drawn after the world (F-03). All seven guns and six arm sets stay in memory.

**F-09 (A for consistency) Augment models are split into too many pieces.** Deploying the GX-4 adds 107 draw calls, the fan shield 102, the whip 90, the knife 73, on top of an average of 86. Enemy guns use 2–3 materials each.

**F-10 (A) Enemy logic dominates the tick.** 1.3 of the 1.76 ms tick in the cloud. Movement and action run every tick for every man, near or far, seen or not.

**F-11 (A) The owner plays a debug build.** CI exports with `--export-debug` (`.github/workflows/ci.yml:124`). Debug templates run scripts and engine checks slower. No release-mode number exists.

**F-12 (B) One thread does everything.** Scripts, physics, culling and draw submission share the main thread; the second big core is mostly idle.

**F-13 (B) Slow frames feed themselves.** Physics runs at 60 Hz. At 40-pace frames the engine runs two ticks in every second frame, and after a 100 ms hitch it may run six in one frame (the limit is 8).

**F-14 (B) Spawns still cost a frame.** 3–6 ms in the cloud per man, in batches of three (2026-11-12 log), from building his animation tree and hitboxes.

**F-15 (C) Frozen corpses still run code.** Ten bodies keep `_process` and `_physics_process` (`enemy_body.gd:447`, `enemy.gd:637`).

**F-16 (C) The HUD redraws every frame** whether or not a value changed (`combat_hud.gd:171`, `hud.gd:47`, `:190`).

**F-17 (C) Steam emitters share nothing.** Nine particle systems, each with its own process material, mesh and shader material.

**F-18 (C) Memory.** Up to 680 MB of textures exist; how much is resident in a Chinatown session is unmeasured. The map imports shadow meshes that nothing uses.

**F-19 (C) Hot spots.** Five percent of the map is reached by 3–6 character lights and some cells by 4–5 probes, which moves those pixels to the costlier shader variant. A small cause of "fine here, slow there".

**F-20 (tooling) Cloud captures were not trustworthy in this session.** The software Vulkan driver was missing, the import cache was older than the checkout (the game failed to load the MP5 and Glock), and `timeout` did not stop a hung Godot under `xvfb-run`. I worked round all three in the session only.

Checked and found fine: no shader reads the screen or depth texture; bloom is off; shadows are off everywhere; the sky is a static panorama; the vignette fix from 2026-11-12 is in; character lights are sparser than their count suggests; world LODs exist and are sound.

---

## 6. The work

### WS-0 Measurement (Phase 0)

**M-01 Frame-time histogram.** Overlay and benchmark JSON gain: share of frames at ≤ 8.4, ≤ 16.7, ≤ 25, ≤ 33.4 and above; 1 % low; the screen's refresh rate; the pacing mode; physics ticks per frame.

**M-02 Cost test, two parts** (about 90 s each, pause menu):
- *A, pixels and passes:* 100, 95, 85, 70, 60, 50 % scale; tonemap AgX vs Filmic; adjustments off; HUD hidden; overlay hidden. Fitting GPU time against pixel count gives the fixed cost and the per-pixel cost separately.
- *B, content:* gun hidden; gun drawn first; world with lighting off (baked light only); world without normal maps; world without rain code; anisotropy off; men hidden; +10 men; +10 wounded men; character lights off; probes off; occlusion culling off; LOD threshold 1, 2, 4 px; glass, water and skyline hidden.

**M-03 Hitch log.** A ring buffer of the last 30 s of frame times, tagged with events (spawn, cut, burst, augment deploy, resolution change, pipeline compilations from the engine's `PIPELINE_COMPILATIONS_*` counters). Saved with the bug report and listed on the pause screen.

**M-04 Soak test.** 20 minutes of the bot fight; per-minute average, 1 % low, render scale and, if Android lets the app read it, temperature.

**M-05 Release-mode APK.** CI builds a second APK from the release template, signed with the same key, published next to the debug one.

**M-06 Renderer comparison.** Run the existing benchmark once on Mobile and once on Compatibility and record it. The switch is already in the pause menu.

**M-07 Cloud guards.** The probe's draw-call and triangle percentiles reported on every CI run, and tests for the resolution controller.

**M-08 Tooling.** Session start re-imports when the cache is older than the checkout and reports a missing Vulkan driver; capture scripts use `timeout -k`.

### WS-1 Pacing and resolution

**P-01 Fixed pacing mode.** Compare Swappy mode 0 (honour the cap, never downgrade) with the automatic modes on the histogram; ship the steadier one. It is read at start, so it switches through the same override file as the renderer. *Look none · Size M · Conf medium.*

**P-02 A 40 fps cap** beside 60 and 30: three refreshes at 120 Hz, evenly paced. A fallback, not the goal. *Look none.*

**P-03 Resolution controller v2.** Fixed steps (60, 67, 75, 85, 100 %); a cost model fitted from M-02 so it jumps straight to the step that fits; slower to rise than to fall; at most one change a second; never changes because of a CPU miss (kept from 2026-11-12). 100 % becomes a real step because it is the cheap path. *Look none · Size M · Conf high.*

**P-04 Texture sharpness correction.** Offset the mip bias the engine applies at reduced scale so textures stop shimmering. Check on fixed-camera captures at 70 %. *Look check, expected better · Size S.*

**P-05 Cap physics catch-up** at 2–3 ticks a frame (default 8). After a hitch the game briefly runs slow instead of stuttering further. *Look none · Size S, removes a failure mode.*

### WS-2 Passes and draw order

**R-01 Draw the gun first.** Give the world, then the men, a higher render priority than the viewmodel (positive values only: the sort key stores priority unsigned). Every world pixel under the gun is then rejected before shading. *Look none · Size M · Conf medium-high. Verify: "gun hidden" row shrinks to near zero.*

**R-02 Near cells first.** One material instance per map cell, its priority set from distance to the camera a few times a second. *Look none · Size S–M · Conf medium. Keep only if M-02 shows a gain.*

**R-03 Tonemap cost.** If AgX plus adjustments measures above about 0.7 ms, propose a cheaper tonemapper matched by eye, with side-by-side captures for approval. *Look check.*

**R-04 Bloom stays off.** If the neon glow is missed, see A-04.

### WS-3 World

**W-01 Skip rain work where there is no rain.** Read the puddle noise only on upward-facing wet pixels. Identical output. *Look none · Size S–M · Conf high.*

**W-02 Dry and wet variants.** Route indoor triangles to a variant with no rain code at all. Only if W-01 leaves a measurable gap. *Look none.*

**W-03 Far variant.** Cells beyond about 45 m use a version without normal map and roughness texture. Fog already removes half the contrast at that range. *Look check · Size M · Conf medium.*

**W-04 Restore distance culling for small props.** Mark props under about 0.5 m as `_detail` in the build; the level code that hides them past 42 m already exists. *Look check at range · Size M on triangles · Conf high.*

**W-05 Split the two densest cells** into interior and exterior, so the market's contents are not drawn from outside its walls. *Look none · Size M.*

**W-06 Occluder audit.** Count and visualise the box occluders, add roof and floor slabs where missing, measure the culling's own CPU cost on the phone and tune its ray count. *Look none.*

**W-07 Anisotropy.** Try 2× instead of 4× on the world albedo. *Look check on the road at grazing angles · Size S.*

**W-08 Lightmap mipmaps**, with the bake's padding checked so light does not bleed between islands. *Look check · Size S.*

**W-09 Probe layout.** Resize the nine probes so a cell or the gun rarely sits in more than one, with a 1 m blend at borders. *Look check on wet streets and gun metal · Size S–M.*

**W-10 Housekeeping.** Stop importing unused shadow meshes; slim the unused half of the data channel in the vertex format. *Look none · Size S, memory.*

**W-11 Lighter world lighting (gated).** Only if M-02 shows the lit world costs over about 3 ms more than baked-only at the target scale: an unshaded world shader that adds its own reflection, muzzle-flash light and fog. Large change; see Phase 3.

### WS-4 Characters and first-person view

**C-01 Wound loop early-out.** Skip a wound when the pixel is outside its largest radius; compute the fine noise only near wounds. Identical output. *Look none · Size M on wounded men and corpses · Conf high.*

**C-02 Triad textures to the 2K rule.** Check on the face close-up capture. *Look check · memory.*

**C-03 Character light ranges.** Shorten ranges to where each light still contributes, fade lights out beyond about 35 m from the camera, thin the 3–6-light hot spots. *Look check · Size S–M, evens out the map.*

**C-04 Arms shader.** Plain trilinear filtering (anisotropy does nothing on a surface facing the camera); skip the region lookup when no custom colours are set. *Look none · Size S.*

**C-05 First-person meshes.** A build step that removes faces the first-person camera can never see (far side, internals) from the in-hand copy of each gun; the full model stays for the wheel and loadout. *Look none in play · Size M on triangles.*

**C-06 Load only the gun in hand** and the last one used; others load on a background thread at switch. *Look none · memory, with a switch-hitch risk to test.*

**C-07 Merge augment models by material** at export, keeping moving groups separate: GX-4, shield, whip, knife and drone to about 8–12 draws each. *Look none · Size M–L at the moment of deploy · Conf high.*

**C-08 One material per enemy gun; one multimesh for blob shadows.** Up to 35 fewer draws in a full fight. *Look none · Size S.*

**C-09 Two-sided men.** Only if "+10 men" in M-02 is expensive: back-face culling for the body and closed garments. Costs one extra draw a man. *Look check.*

### WS-5 CPU

**U-01 Judge on the release build** (M-05). *Size unknown until measured; commonly large for script-heavy ticks.*

**U-02 Enemy scheduling.** Section timers inside the tick first. Then: full rate for men within 25 m or on screen, half rate for the rest with scaled time steps; skip the character-body move when standing still. Target: 40 % off the enemy tick. *Look none · Size M–L · Conf medium.*

**U-03 Animation scheduling.** Half rate for men off screen or beyond 30 m; no aim-pose pass off screen; frozen corpses stop processing entirely (F-15). *Look check at range · Size S–M.*

**U-04 Enemy pool.** Twelve reusable men, re-dressed by swapping mesh and material, so a spawn no longer builds a tree. *Look none · removes spawn hitches.*

**U-05 Render thread.** Try `thread_model = 2` behind a restart toggle; keep it only if the histogram improves and nothing crashes in a soak test. *Look none · Size M · Conf low–medium.*

**U-06 Physics hygiene.** Sleep thresholds for gibs, shells and debris; confirm ragdolls do not collide with each other; watch the tick in bursts. *Look none · Size S.*

**U-07 HUD redraw on change only.** *Look none · Size S.*

**U-08 Hot-path allocations.** Audit group queries and temporary arrays inside per-tick code. *Look none · Size S.*

### WS-6 Effects

**E-01 Steam shares one process material and one mesh**, and fades when the camera is inside a puff. *Look check · Size S.*

**E-02 Overdraw evidence.** Cloud captures in the engine's overdraw view during a scripted fight at the fixed cameras, to hold the 1.5-screen budget. *Look none.*

**E-03 Blood trace rays.** If the hitch log shows bursts costing CPU, lower the 110 rays a frame. *Look check.*

**E-04 Muzzle light.** Confirm its first use causes no pipeline compile; shorten its range if the map cells it touches show in the log. *Look check.*

### WS-7 Memory and hitches

**H-01 Warm-up.** If the hitch log shows pipeline compilations during play, show each effect and light combination once behind the loading screen.

**H-02 Texture rule as a test.** A GUT test fails on any imported texture above 2048 outside a short whitelist.

**H-03 Memory on record.** Video and system memory from the overlay in every playtest entry.

### WS-8 Art-direction options (only with your approval)

Offered because you said some stylisation is welcome. None is needed for Phases 1–2.

**A-01 Graphic far field.** Past about 45 m, buildings become dark silhouettes with lit windows, like the skyline across the bay. Suits the night setting and removes far-field shading cost.

**A-02 Chunkier small props.** Market clutter rebuilt with fewer, harder-edged shapes and strong baked light. At 720p it reads the same or cleaner.

**A-03 Simple men at range.** Beyond about 20 m a man is flat colour with the existing rim and fill light, which already carry his readability.

**A-04 Painted bloom.** Soft additive cards on neon signs and lamps, in place of the 3.2 ms full-screen bloom.

**A-05 Weather tied to load.** Rain and steam density follow the render scale.

---

## 7. Phases and gates

**Phase 0 — Measure.** M-01 to M-08. Ends with two APKs (debug and release) and your three screenshots.

**Gate 1 — classify the bottleneck from Phase 0:**

| If the phone shows | Then first |
|---|---|
| GPU time falls steeply with resolution | WS-3, WS-4 (pixels) |
| GPU time barely moves with resolution | WS-2, P-03 (passes, 100 % path), triangles (W-04, W-05, C-05) |
| Frame time well above GPU time | WS-5 (CPU), U-05 |
| Release build much faster than debug | Judge everything on release; CPU work drops in priority |
| Histogram is two spikes at 16.7 and 25 ms | WS-1 first |
| Compatibility renderer clearly faster | Add it to Phase 3 as a serious option |

**Phase 1 — Free wins, no change to the picture.** P-01, P-02, P-05, R-01, W-01, C-01, C-04, C-07, C-08, U-07, F-15 fix, W-10, H-02, E-01. Each with a before/after capture pair.

**Phase 2 — Structural.** P-03, P-04, R-02, W-03 to W-09, C-02, C-03, C-05, C-06, U-02 to U-06, U-08, H-01.

**Gate 2.** If the §2 targets hold at 85 % or better, stop and go to Phase 4.

**Phase 3 — Only if needed.** W-11, R-03, C-09, a renderer switch if Gate 1 pointed there, and any WS-8 options you pick.

**Phase 4 — Lock in.** New budgets into CLAUDE.md §8 and the perf-budget skill, CI guards on, playtest-log entry, design-doc updates for anything that changed.

Order inside a phase: cheapest and safest first, one change per measurement where possible, so every gain is attributable.

---

## 8. Verification

- **Every change:** `tools/check.sh` passes; fixed-camera captures before and after, compared side by side; the cloud probe's draw calls, triangles and CPU numbers recorded.
- **Every phase:** the cost test, the histogram and the soak test on the phone; results into `docs/playtest-log.md`.
- **Look:** a change marked "check" ships only with its capture pair shown to you; a change marked "changes" ships only after you approve it.
- **No claim without a phone number.** The cloud cannot measure this GPU.

---

## 9. What I need from you

At the end of Phase 0:

1. Install the new build. Play one Chinatown fight with the overlay on and screenshot the histogram line.
2. Pause → **Cost test A**, then **Cost test B**. Leave the controller alone; screenshot each table.
3. Pause → **Soak test**, leave it 20 minutes on a table, screenshot the result.
4. Install the release-mode APK and repeat step 1.

Two decisions when convenient:

- Is 85 % resolution acceptable as the shipped setting if 100 % cannot hold 60, or is native resolution the aim?
- Do you want the 40 fps cap offered as a fallback?

---

## 10. Considered and set aside

| Option | Why not |
|---|---|
| FSR upscaling | The engine supports it only in Forward+, not the Mobile renderer. |
| Depth pre-pass | Not available in the Mobile renderer; R-01 and R-02 get part of the benefit. |
| Variable-rate shading | To my knowledge this GPU generation lacks it; a one-line capability check in Phase 0 settles it. |
| 30 Hz physics with interpolation | Halves tick cost but changes input timing and gun feel. Kept in reserve. |
| Vertex-only lighting for everything | Large gain, large loss of look. |
| Fewer enemies or less gore | Design decisions, not optimizations. |
| MSAA at reduced resolution | Might hide low-resolution edges cheaply on this GPU, but it is a quality option, not a saving. Worth one row in cost test A later. |
| Moving to Godot 4.8 | Still in beta. |

---

## 11. Risks

- **The phone disagrees with the cloud.** Expected; that is why Phase 0 comes first and every phase ends on the phone.
- **Render thread instability.** Behind a restart toggle, off by default until soaked.
- **Priority-based draw order depends on engine internals.** Read from the 4.7.2 source; re-check on any engine upgrade.
- **On-demand weapon loading adds a switch hitch.** Keep the last weapon cached; measure in the hitch log.
- **Controller tuning oscillates.** Covered by tests on recorded GPU traces from the phone.
- **Thermal behaviour.** If the soak test slides after 10–15 minutes, the working budget in §2 tightens further.

---

## Appendix A — Raw results from this audit

Render probe (`-- --perf=20 --perf-spin`, Mobile on lavapipe): draws avg 85.6 / p95 134; primitives avg 114.2k / p95 251.5k; objects avg 638 / p95 702; render CPU avg 0.88 / p95 1.13 ms; peak 7 enemies, 3 active ragdolls, 32 gibs, 180 stains.

CPU probe (`--headless -- --perf=12 --perf-calm [--perf-exp=…]`): see §3.2.

Map LOD chain, triangles if every mesh used LOD n: 313,056 → 133,518 → 48,178 → 19,448 → 10,223.

Engine files read (godotengine/godot, tag `4.7.2-stable`): `servers/rendering/renderer_rd/forward_mobile/render_forward_mobile.cpp` and `.h`, `scene_shader_forward_mobile.h`, `servers/rendering/renderer_viewport.cpp`, `servers/rendering/renderer_scene_cull.cpp`, `doc/classes/ProjectSettings.xml`.

## Appendix B — Files this plan touches

| Area | Files |
|---|---|
| Pacing, resolution | `project.godot`, `src/core/settings.gd`, `src/core/adaptive_resolution.gd` |
| Measurement | `src/ui/debug_overlay.gd`, `src/core/debug/feature_sweep.gd`, `frame_bench.gd`, `perf_probe.gd`, `.github/workflows/ci.yml`, `export_presets.cfg` |
| World | `src/levels/chinatown/world.gdshader`, `chinatown.gd`, `night_atmosphere.gd`, `raw_assets/levels/chinatown/build.py`, `split_cells.py` |
| Men | `src/ai/triad.gdshader`, `enemy.gd`, `enemy_body.gd`, `src/levels/rolling_spawner.gd`, `assets/characters/triad/textures/*.import` |
| First person | `src/player/player.tscn`, `viewmodel_rig.gd`, `src/body/suit_paint.gdshader`, weapon and augment generators in `raw_assets/` |
| HUD, effects | `src/ui/hud.gd`, `combat_hud.gd`, `src/vfx/fx.gd` |
| Tooling | `tools/session_start.sh`, `tools/screenshot.sh` |

---

## 12. Progress

### Phase 1 — built 2026-11-13 (owner: "start with phase one and not zero")

Phase 0 was skipped at the owner's request, so nothing below has a phone number yet. Cloud evidence: `tools/check.sh` passes (all GUT tests, 5 new), and fixed-camera captures before and after were compared.

| Task | What was done | Evidence in the cloud |
|---|---|---|
| P-01 | Pause → **Frame pacing**: Swappy mode fixed (0), auto pipelined (1) or auto (2, engine default). Applies at the next start, through the same override file as the renderer. The default is unchanged (2): pick the steadier one on the phone. | — (Android only) |
| P-02 | Frame cap 60 / **40** / 30. Adaptive resolution already targets the cap. | — |
| P-05 | `physics/common/max_physics_steps_per_frame = 3` (was 8). | — |
| R-01 | Opaque draw order: gun and arms 0, men 1 (`EnemyBody.RENDER_PRIORITY`), map 2 (`ChinatownMap.WORLD_PRIORITY`). The Mobile renderer sorts ascending by priority (checked in the 4.7.2 source; the offset makes negative values legal too, contrary to §6). | Captures match within run-to-run noise. |
| W-01 | World shader reads the puddle noise only on wet, upward-facing pixels, with gradients taken outside the branch. | Same output by construction; captures within noise. |
| C-01 | Wound loop skips wounds whose widest radius can't reach the pixel; both noise values are computed only near a wound. | Same wounded man with the old and new shader in one run: **pixel-identical**. |
| C-04 | Arm and suit textures trilinear instead of anisotropic; the region map is skipped when no suit colour is set. | Captures within noise. |
| C-07 | `RigidMerge` (src/core/rigid_merge.gd): each rigid-piece model becomes one skinned mesh per material, one bone per piece, bones following the original (now empty) nodes. Done when the model is built, not in the Blender export, so the generators and the code that drives the pieces stay as they are. GX-4 107 → 8 surfaces, fan shield 102 → 6, whip 90 → 8, knife 73 → 8, drone 29 → 8, every triangle kept. | GUT; GX-4 deployed frame 114 → 73 draws; captures match. The merged meshes have no LODs (first person; the drone flies at range with 6.6k triangles). |
| C-08 | Enemy guns: one surface each (`GunFlatten`, palette texture for the old materials' values, LODs regenerated). Blob shadows: one `MultiMeshInstance3D` for all men. | Gun A/B against the imported materials: max difference 4/255 on 359 edge pixels. |
| U-07 | Reticle, rail gauge, health bar and vignette redraw only when a value they show changes. | GUT. |
| F-15 | A frozen corpse stops `_process` once its wounds stop spreading (5 s) and `_physics_process` once it stops bleeding; a hit, cut or throw wakes it. | GUT. |
| W-10 | Map import: no shadow meshes; a post-import step (`tools/import/map_post_import.gd`) stores the world data channel (CUSTOM0) as half floats, keeping LODs and compression. Imported map 12 MB → 8.5 MB. | Captures within noise. |
| H-02 | `tests/unit/test_texture_sizes.gd`: fails on any imported texture over 2048, outside a whitelist (map lightmap; the two triad textures until C-02). | Fails when an entry is removed from the whitelist. |
| E-01 | Steam: one process material and one mesh for all vents; a puff the camera is inside fades and stops drawing. | Captures within noise. |

Notes from building it:

- **Cloud captures are not deterministic on Chinatown.** Two runs of the same old build differ on up to 9 % of pixels (reflection probes still filling in, rain, steam, swinging lanterns). Judge "no change" against that spread, or A/B inside one run as for C-01 and C-08.
- **A custom spatial shader that passes per-vertex values in its own varyings rendered without the ambient light** in the lit pass (Mobile renderer, lavapipe); the same values as uniforms or through the built-in UV were correct. Not investigated further. Worth remembering for future shaders.
- F-20 still applies: the session had no software Vulkan driver until `mesa-vulkan-drivers` was installed by hand.

**For the owner:** install the build, play a Chinatown fight with the overlay on, and compare with the last build. Then try Pause → Frame pacing → fixed (restart the app) and say which feels steadier. Any screenshot of the overlay helps.
