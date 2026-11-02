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

## Where the code is (M1a)

- `src/weapons/ballistics.gd` (autoload `Ballistics`): stepped projectiles — drop, drag, energy-based penetration (`thickness × resistance_j_per_cm`), ricochet, exit deflection. Resolves the first tick on the trigger frame.
- `src/weapons/gun_mechanism.gd`: magazine + chamber, buffered semi-auto, tactical/empty reloads (ammo commits only when the mag seats).
- `src/weapons/player_weapon.gd`: loadout of guns with one viewmodel rig each (Y switches and cancels a reload), input (LT held = ADS, RT fire, X reload), carry penalty (`carry_*` in WeaponData), hip walk, tracers, camera recoil spring + permanent climb, bloom/spread, sprint-out, rumble, hit-stop.
- `src/weapons/viewmodel_motion.gd` + `src/core/spring.gd`: exact closed-form springs; `kick(peak)` hits the tuned peak for any damping.
- `src/vfx/fx.gd`, `src/audio/sfx.gd`: pooled flash/light/shells/holes/particles/debris and sound banks.
- Railguns (`data/weapons/rail_carbine.tres`): `WeaponData` "Capacitor and heat" (`charge_time` > 0 makes a gun a railgun), `GunMechanism.charge()/heat/venting/last_power`, `Ballistics.fire(..., power)` and trails (`beam_trail_*`, `src/vfx/rail_trail.gdshader`), `SurfaceMaterial.drag_scaling_speed` (v² drag in flesh above 900 m/s), rig parts `vent`/`glow`/`lens`, `magazine_travel`.
- Shell types (Saiga-12K): `src/weapons/ammo_data.gd` + `data/weapons/ammo/*.tres` override the gun's ballistic/shot/flash/burn values per load (`apply_to()`); the chamber and magazine track their load in GunMechanism; D-pad left/right selects, a swap racks the old shell out. Pellets share a volley id (stats/confirms count a shell once). Tuning-menu ballistic sliders edit the gun, which the loads override, so tune loads in their .tres.
- `src/ui/tuning_menu.gd`: on-device sliders; add new tunables to `WEAPON_PARAMS`. `tools/sync_weapon_tres.py` adds new WeaponData exports to the .tres (check its output: it writes GDScript defaults such as `Vector3.ZERO`, which a .tres can't hold).
- Range targets in `src/levels/range/`; `-- --demo=range|fire|hip|ads|burst` drives the gun for screenshots (`GunplayDemo`), with `--weapon=<slot>` and `--ammo=<load>`.

## Implementation notes

- Fast rounds are simulated projectiles (ray segments per tick, ≈ hitscan cost) with penetration through the surface table in `data/surfaces/`; penetration costs energy per cm. Slow objects (grenades, drone, whip tip) are physical.
- Weapon data: damage, falloff, penetration, impulse, spread, recoil pattern.
- Procedural motion = damped springs stepped in `_process` with scaled delta (slow motion and hit-stop slow them too).
- Aiming: response-curve presets, radial deadzones, acceleration on full tilt (see `data/input/`), aim assist in layers: slowdown near targets, slight pull while ADS.
- 1,200 rpm MG: pooled hitscan, tracer every few rounds, one shared muzzle light, decals-per-second cap, looping fire sound.

## Verify

GUT tests for maths (spring step, recoil pattern sampling, falloff, penetration). Screenshots for visuals. Feel is only verified by the owner's playtest notes.
