# M1 plan: gunplay first

Owner decision (2026-11-01): start M1 with the core, static gunplay of the suppressed pistol, with no augments and no enemy AI yet, and hone it until it feels great. Movement tech (slide, wall-run, mantle) and enemies (damage zones, gore, ragdolls, AI, waves) follow in later M1 slices.

Every slice ends with an APK on `dev-latest` and a short "what to try" list in `docs/playtest-log.md`. Tuning values live in `.tres` files (`data/weapons/`, `data/player/`) and the springs can be tuned on the phone.

Owner direction (2026-11-01, second message): ADS is **hold LT**; **moderate recoil**, but **supreme simulated accuracy and ballistic destruction**. How that was read:
- Rounds are simulated projectiles from the eye (drop, drag, travel time, energy-based penetration, ricochet), so the round lands exactly where the sights point, give or take the gun's 1.5 MOA when aimed.
- Recoil: ~1.1° camera kick that springs back in ~0.15 s; only 18 % stays as climb. The viewmodel kicks harder than the camera so it still looks violent.
- Destruction: surfaces lose structure to the energy rounds leave in them; drywall and plank walls break out cell by cell and throw debris; props are pushed by lost momentum.

## M1a — Core gunplay (built 2026-11-01, first phone playtest done)

Status: every item below is built and covered by GUT tests (76) and cloud screenshots; feel is unverified until the owner plays it.

1. **Weapon foundation.** `WeaponData` resource for the suppressed Five-seveN: 20-round magazine, semi-auto with a fire-rate cap, damage and falloff, penetration, spread, recoil pattern. Fire state machine: ready / firing / reloading / switching. Hitscan with penetration through a surface material table (flesh, wood, drywall, sheet metal, concrete, armor plate).
2. **Feel (docs/design.md §5.3 / §5.4).**
   - Spring-driven camera kick and viewmodel recoil; slide cycles on each shot.
   - Procedural sway, bob, turn inertia and landing.
   - ADS on LT: viewmodel moves to the sights, FOV tightens, sensitivity scales.
   - Muzzle flash with a brief pooled light; shell ejection.
   - Impact decals and particles by surface.
   - Hit marker; separate headshot and kill confirms; a few frames of hit-stop on headshots.
   - Controller rumble.
   - Tactical vs empty reload, both cancelable.
   - Layered suppressed-shot sound with a room tail.
3. **Shooting range in the test room.** Steel plates that ring and fall, humanoid target dummies with head/torso/limb zones that show where each hit landed, and penetration panels (wood, drywall, sheet metal, concrete).
4. **Aim assist** in layers: slowdown near targets, slight pull while aiming down sights. Tunable; can be switched off.
5. **On-device tuning menu.** Recoil, springs, ADS speed and aim assist strength, with a "copy values" readout you can send back.
6. **Range stats.** Shots, hits, headshot %, time between shots, shown in the overlay.

Sound: CC0 sources where the network allows (needs `opengameart.org` etc. in the allowlist); otherwise synthesized layers. No paid ElevenLabs calls without the owner's OK.

### Playtest 1 (owner, 2026-11-01) and what changed

- "Feels good" overall.
- **Hold looked wrong:** the pistol sat dead centre, angled up, with the crosshair floating on top of it. Now it sits lower right and points forward, the crosshair is clear of the gun, and the crosshair itself is thinner (anti-aliased ticks + dot). Test: `tests/unit/test_viewmodel.gd`.
- **Gun tuning couldn't be opened:** Godot 4.7's built-in menu actions have no controller buttons, so A did nothing on a highlighted button. A now presses, B goes back (tuning → pause menu). Test: `tests/scene/test_menus.gd`.
- **Stick too sensitive:** all three look curves are about 30 % slower (Standard 165°/s yaw, 115°/s pitch, softer centre) and there's a new pause-menu **Look speed** (50–150 %, left/right on the button).

## M1a.1 — MG42 (owner request, 2026-11-01)

Pulled forward from M3: "the next gun is the MG42 light gun — chrome and black steel, 1,200 rounds per minute, a .308 type round, it should absolutely shred. For now a universal penalty: you're a little slower and can't fire it from the hip as easily."

- **Model:** `raw_assets/weapons/mg42/build.py`. MG42 proportions (1.22 m, perforated jacket with the barrel-change window, muzzle booster, folding bipod, hinged feed cover, angled stock) in polished chrome and blackened steel, a clamp-on vertical foregrip for hip fire, a 150-round box on the left feeding a brass belt, FCL readout. 17k triangles, 4K baked textures. Moving parts: feed cover, box, belt, stock (hidden while aiming).
- **Arms:** `raw_assets/characters/fp_arms_mg42/build.py`: the pistol hand on the pistol grip, the support hand around the foregrip.
- **Handling (`data/weapons/mg42.tres`):** open bolt, 150-round belt, 1,200 rpm exactly (cycle overshoot carries over, so it doesn't drop to 900 at 60 Hz). 9.5 g at 800 m/s (≈3 kJ, 7× the pistol). Tracer every 3rd round. Carry penalty: 82 % move, 85 % sprint/jump/turn. Hip: 3.2° cone that walks up to +3° under sustained fire; aimed: 2.5 MOA. Belt reload 4.2 s (cover up, box off, box on, cover slams).
- **Controls:** Y switches guns (and cancels a reload). Pulling the trigger still cancels a reload too.
- Heat and barrel changes stay in M3.

## Pistol 57 v2 (owner, 2026-11-01)

"Doesn't look nearly as good as the MG42." It was the first asset: flat extruded frame and slide, few parts, flat finish. Rebuilt with the MG42's tooling, **olive finish kept** (owner): lofted oval grip with stipple texture and finger grooves, rounded dust cover, beavertail, squared trigger-guard loop, slide with lower chamfers, tapered nose, sight channel, extractor, firing-pin cap, chamber indicator, sight dots; lighter cavity grime. Same size and key points (sight line, muzzle, grip frame), so arms, ADS and gameplay are unchanged. 7.9k tris, 2K maps. Previews: `docs/previews/pistol_57_v2.png`.

## M1a.2 — Saiga-12K (owner request, 2026-11-02)

"We need at least one more weapon in M1 ... a Saiga 12K semi-auto shotgun with an AK style banana magazine and black steel milling. You need to be able to choose what kind of rounds: Dragon's Breath, double-aught buck or slugs. A 1x magnification scope with an interesting Russian SVD-like optic on there for the slug variant."

- **Model:** `raw_assets/weapons/saiga12k/build.py`. AK-pattern 12-gauge with a 430 mm barrel. Milled black-steel receiver with lightening pockets, ribbed dust cover, tangent rear sight, hooded front post, slotted brake, milled steel handguards with vent slots, vertical foregrip on a Picatinny strip, side-folding skeleton stock, 10-round curved polymer magazine. Warsaw-pact side rail with a **PSO-1-style optic** on its clamp bracket: long rubber eyecup, sunshade, big elevation drum, windage drum, illumination battery with a red lamp window. 24.5k triangles (8.2k of them the optic), 4K baked textures. Moving parts: bolt carrier and charging handle (cycles each shot, locks back on empty), magazine, stock (hidden while aiming), optic (mounted only for slugs). A strip of **coloured tape** round the magazine and the top shell's hull show which load is in the gun: red for buck, green for slugs, orange for Dragon's Breath.
- **Arms:** `raw_assets/characters/fp_arms_saiga/build.py`. The MG42 arms with the support hand moved to the Saiga's foregrip. The pistol grip uses the same grip frame, so the firing hand is unchanged.
- **Shell types** (`data/weapons/ammo/*.tres`, an `AmmoData` each):

  | Load | Pellets | Each | Speed | Energy | What it does |
  |---|---|---|---|---|---|
  | 00 Buck | 9 | 3.5 g | 400 m/s | 2.5 kJ | 3.4° pattern; a torso-sized group at 5 m, a few pellets on target at 40 m. Pellets slow down fast. |
  | Slug | 1 | 28 g | 450 m/s | 2.8 kJ | 3 MOA aimed, heavy push, goes through cover. Drops 0.3 m at 100 m and 1.5 m at 200 m. Mounts the optic. |
  | Dragon's Breath | 14 embers | 0.6 g | 380 m/s | 0.6 kJ | 9° cone of burning metal that dies out by about 50 m. A flame jet from the muzzle lights up the room. Embers set targets alight (18 HP/s for 4 s, topped up by more hits) and start small fires on wood, crates and cardboard. |

- **Choosing a load:** **D-pad right/left** picks the next/previous load. The HUD shows `00 BUCK > SLUG`, blinking. 0.3 s after the last press (two quick taps skip a load), the gun swaps in a magazine of that load and racks the charging handle, throwing out the live shell in the chamber (its hull is tinted, so you can see what came out). This is the 2.9 s empty-reload length. X with another load selected does the same swap. Pulling the trigger before the new magazine seats cancels the swap and fires what's chambered; pulling after it seats racks instantly and fires the new load. The chamber and the magazine track their load separately, so a normal tactical reload keeps the chambered shell.
- **Optic:** with slugs, LT aims through the PSO. Near full aim the viewmodel steps aside and the HUD draws the view through the eyepiece. At 1x both eyes stay open, so the world outside the eyepiece is dimmed rather than blacked out. The illuminated reticle has the main chevron (aim point), holdover marks for 100/200/300 m **calculated from the slug's real drop** (small at 1x: 2, 5 and 10 px), a windage scale (10 mil ticks) and the stadiametric rangefinder curve for a 1.7 m man. FOV ×0.88.
- **Handling (`data/weapons/saiga12k.tres`):** semi-auto, 0.16 s fastest follow-up, 10+1. Kick 2.8° (×1.3 with slugs, ×0.7 with Dragon's Breath) that recovers quickly. 5 % carry penalty. Tactical reload 2.3 s, empty or swap 2.9 s. 12-gauge hulls eject tinted by load.
- **Stats and feedback:** pellets from one shell share a volley id, so range stats count a shell as one shot and one hit, and the hit confirm plays once per shell (the strongest one). Pellet impacts are 5 dB quieter than single rounds.
- **Controls:** Y cycles pistol → MG42 → Saiga-12K.
- **Previews:** `docs/previews/saiga12k_*.png` (Blender: side, beauty, left, receiver, optic, first person), `fp_arms_saiga.png`, and in-game captures `saiga12k_ingame_hip/irons/scope/dragons_breath.png` (`--demo=hip|ads|fire --weapon=2 --ammo=<0..2>`).
- Tests: `tests/unit/test_saiga_mechanism.gd` (chamber and magazine loads, swap, cancel, rack), `tests/unit/test_ammo_data.gd` (round data, 12-gauge energies, slug drop matches the simulation, pellet pattern), `tests/scene/test_saiga.gd` (9 pellets count as one shot, D-pad swap mounts the optic and tints the tape, scope view, Dragon's Breath sets a dummy alight).

## Later M1 slices

- **M1b — Movement:** sprint polish, slide, wall-run, mantle, air dash; viewmodel reacts to all of them.
- **M1c — Targets that fight back:** locational damage on humanoids, gore and ragdolls, three enemy roles with awareness, suppression and morale, wave mode.

M1 is done when the owner wants to keep playing the wave mode (CLAUDE.md §12).
