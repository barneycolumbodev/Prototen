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

## Later M1 slices

- **M1b — Movement:** sprint polish, slide, wall-run, mantle, air dash; viewmodel reacts to all of them.
- **M1c — Targets that fight back:** locational damage on humanoids, gore and ragdolls, three enemy roles with awareness, suppression and morale, wave mode.

M1 is done when the owner wants to keep playing the wave mode (CLAUDE.md §12).
