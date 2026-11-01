---
name: weapon-feel
description: Use when building or tuning anything about how a GRAFT weapon handles — recoil, camera kick, springs, sway, bob, ADS, aim assist, reloads, hit feedback, hit-stop, rumble. Lists the feedback checklist and where tuning values live.
---

# Weapon feel

Goal: the best gunplay in any mobile shooter (CLAUDE.md §2). References: Call of Duty (handling), Doom (speed), Halo (readability), F.E.A.R./Trepang2 (slow motion, hit reactions), S.T.A.L.K.E.R. (weight), Soldier of Fortune (locational damage).

## Where values live

- All tuning goes in `.tres` resources under `data/weapons/` and `data/player/`, never in code. Scripts only read them.
- Spring values (sway, bob, recoil, landing, turning inertia, sprint/slide/wall-run tilt) live in the weapon resource and are editable in the on-device tuning menu so the owner can tune by feel and send numbers back (docs/design.md §5.4).
- When the owner sends numbers, copy them into the `.tres` in the same commit as the playtest-log entry.

## Feedback checklist — every shot (docs/design.md §5.3)

- [ ] Camera kick and visible gun recoil, both spring-driven
- [ ] Muzzle flash and a brief light (one shared pooled light)
- [ ] Layered sound: mechanism, shot, room tail by room size
- [ ] Shell or link ejection (pooled)
- [ ] Hit marker + sound; separate headshot and kill sounds
- [ ] A hit reaction on every hit
- [ ] Impact decal and particles by surface material
- [ ] A few frames of hit-stop on heavy hits and headshots
- [ ] Controller rumble (`Input.start_joy_vibration`) where Android allows it
- [ ] Cancelable reloads; separate tactical and empty reloads

## Implementation notes

- Fast rounds: hitscan with penetration through the material table (flesh, wood, drywall, sheet metal, concrete, armor plate); penetration drops per surface. Slow objects (grenades, drone, whip tip) are physical.
- Weapon data: damage, falloff, penetration, impulse, spread, recoil pattern.
- Procedural motion = damped springs integrated in `_process` with the player's time scale (slow motion must still feel right).
- Aiming: response-curve presets, radial deadzones, acceleration on full tilt (see `data/input/`), aim assist in layers: slowdown near targets, slight pull while ADS.
- 1,200 rpm MG: pooled hitscan, tracer every few rounds, one shared muzzle light, decals-per-second cap, looping fire sound.

## Verify

GUT tests for maths (spring step, recoil pattern sampling, falloff, penetration). Screenshots for visuals. Feel is only verified by the owner's playtest notes.
