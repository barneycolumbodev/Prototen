---
name: gore-and-ragdolls
description: Use when working on GRAFT damage zones, hit reactions, ragdolls, blood, decals, dismemberment or the gore setting — the locational damage model, PhysicalBoneSimulator3D usage, pooling and caps.
---

# Gore and ragdolls

Design: docs/design.md §5.1 and §5.5. Budgets: perf-budget.

## Damage zones

- ~20–26 zones on bones: head, neck, upper/lower torso, groin, upper/lower arms, hands, thighs, shins, feet, left/right separate.
- One `Area3D`/collision shape per zone attached via `BoneAttachment3D`; zone id and multipliers come from `data/gore/` resources.
- `DamageInfo` carries amount, type, penetration, impulse, zone, bone, point, normal, source, flags (CLAUDE.md §9.2).
- Zone reactions: legs → stumble/limp; arms/hands → aim ruined or weapon dropped (may surrender); gut → doubled over; head/neck → kill or incapacitate. Wounded states: crawl, clutch wound, call for help.
- Armor (helmets, plates) has protection levels; penetration vs protection decides if a round gets through.

## Ragdolls

- Partial ragdoll for hit reactions: `PhysicalBoneSimulator3D` simulating selected bones, blended with animation via `influence`.
- Full ragdoll on death; apply impulse at the hit bone scaled by the weapon.
- Cap: ≤ 3 simulating at once, frozen after ~2.5 s (oldest freezes first).
- Check the class reference for 4.7 (`godot --doctool`) before using `PhysicalBone3D`/`PhysicalBoneSimulator3D` APIs.

## Blood and decals

- Entry spray, exit spray on pass-through, bigger burst on headshots, wall splatter behind the target, pools under bodies, persistent wound decals.
- Everything pooled: decals, blood, gibs. ≤ 48 blood decals, oldest fade out.
- Effects are meshes with scrolling textures, not big particle counts (≤ 1,500 live particles total).

## Dismemberment

Pre-split meshes with caps; gibs from a pool. From heavy rounds, explosions, the whip and the ram.

## Gore setting

`off`, `standard`, `maximum` (how far maximum goes is an open question — ask the owner). Every gore spawner checks the setting.

## Slow motion

Blood, ragdolls and debris must look right at 25% time scale: no frame-rate-dependent particle timing, physics interpolation on.

## Verify

GUT tests for zone lookup, armor/penetration maths and pool caps. Screenshots of hit reactions. Debug overlay shows ragdoll and decal counts on the phone.
