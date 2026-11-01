# M1 plan: gunplay first

Owner decision (2026-11-01): start M1 with the core, static gunplay of the suppressed pistol, with no augments and no enemy AI yet, and hone it until it feels great. Movement tech (slide, wall-run, mantle) and enemies (damage zones, gore, ragdolls, AI, waves) follow in later M1 slices.

Every slice ends with an APK on `dev-latest` and a short "what to try" list in `docs/playtest-log.md`. Tuning values live in `.tres` files (`data/weapons/`, `data/player/`) and the springs can be tuned on the phone.

## M1a — Core gunplay (now)

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

## Later M1 slices

- **M1b — Movement:** sprint polish, slide, wall-run, mantle, air dash; viewmodel reacts to all of them.
- **M1c — Targets that fight back:** locational damage on humanoids, gore and ragdolls, three enemy roles with awareness, suppression and morale, wave mode.

M1 is done when the owner wants to keep playing the wave mode (CLAUDE.md §12).
