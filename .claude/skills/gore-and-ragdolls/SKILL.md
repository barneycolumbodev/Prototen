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

## As built (M1c, 2026-11-04)

- Code: `src/ai/enemy_body.gd` (zones on BoneAttachment3D, ragdoll, sever, wounds), `src/ai/enemy.gd` (reactions), `src/gore/gore.gd` (sprays, splats, pools, gibs), `src/gore/ragdoll_budget.gd` (cap 3), `src/ai/triad.gdshader` (wounds).
- `Skeleton3D.get_bone_global_pose()` does NOT include SkeletonModifier3D results (ragdoll, aim layer) outside the modifier pass. Read shown poses from BoneAttachment3D nodes (`EnemyBody.bone_global()`), and build the frozen pose from them.
- Keep the AnimationTree active while ragdolling: with it off, nothing marks the skeleton dirty and the simulator's pose never reaches the mesh.
- PhysicalBone3D `bone_name` and `joint_constraints/*` are dynamic properties: use `set()`.
- Wounds: rest-pose position in CUSTOM0 (EnemyBody.rest_mesh), wound points converted to rest space via the zone's bone; 8 per body, merged when full.
- Severed parts are pre-cut meshes in the glTF (`part_*`); the intact mesh is swapped for them on the first cut. Gibs reuse the part mesh unskinned, posed by the bone.
