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
- (Superseded 2026-11-11, below.) Severed parts were five pre-cut meshes swapped in on the first cut; gibs reused the part mesh unskinned, posed by the bone.

## As built (2026-11-11: dismemberment and gibbing)

- Model and numbers: `src/gore/gore_config.gd` (doc comment), `data/gore/gore_default.tres`, `src/gore/dismemberment.gd` (pure: violence, nearest cut, outcome). Design §5.5.
- Segments: `EnemyBody.SEGMENTS` / `SEGMENT_ORDER` (must match `cut_specs()` in `raw_assets/characters/triad/build.py`). `sever(seg)` takes `attached(seg)` (the subtree still on it).
- Split body = one merged mesh (`merged_mesh`, CUSTOM0.w = segment id) and the shader's `severed_mask` collapses severed vertices. Every enemy mesh's CUSTOM0 is RGBA float now (rest xyz + id).
- Gib meshes are merged per subtree and stored **centred on their middle** (`_gib_centres`); the body is placed at the centre. Gib collision is a box from the mesh AABB. Never put a gib body at the model origin.
- Gib pool: `Gore.MAX_GIBS` 32; `big` gibs (limbs, heads) are recycled last; chunks skip when only big gibs are left.
- Rebuilding the triad cuts: `--fast --no-anim --split-preview <png prefix>` renders an exploded view in ~25 s; check it before the full bake (~2 min). Cuts use connected bands of faces the plane crosses within the limb's radius, and islands vote on their part, so a plane never slices the torso or the other leg.
- glTF vertex colours from Blender: export with `export_vertex_color="NAME"` and the attribute name, or COLOR_0 comes out white.
- Captures: `--demo=gore-lineup` (five men, one round each), `--lineup-at=<frames>` pauses the tree that soon after for a mid-air shot.

## As built (2026-11-11, second pass: blood as drops, retuned cuts)

- Owner's playtest of the first pass: nothing came off in play, and blood was "obnoxious light red clouds". Cause of the first: with the first thresholds only the rail carbine and the Gauss slug ever reached a cut; ballistics take only ~11 J/cm out of a rifle round in flesh, so `deposited()` is small for everything else. Before retuning, measure: shoot every gun at every zone at 3 m and 8 m (a throwaway GUT test spawning a fresh Enemy per case) and print what came off.
- Dismemberment numbers now (`data/gore/gore_default.tres`): arrival share 0.3, reach 0.4 m (full within 0.1), hits of 20 % of a threshold add up and sever at 1.25 ×. A hit on the head acts on the head at full strength and breaks it past `head_destroy_j` (800); a neck hit takes it off whole. PULP needs energy *left in the piece* past threshold × 2.6 (`Enemy._cut_left`), so a round that goes through severs instead of pulping. `toughness` × every threshold, `blood_amount` × every count; both are on Pause → Tuning → Gore.
- Blood in the air: `BloodDrops` (child of Gore). Closed-form path under gravity + linear drag (`position_at`); the shader evaluates the same formula from the instance transform (X = launch velocity, Y = (launch time, end time, size), Z = (drag, seed)). Don't integrate per frame and don't use CPUParticles for blood. Drag from size: `drag_for(size, base)`.
- Drops that stain are traced when launched (`STEP` 70 ms per ray, `RAYS_PER_FRAME` 110); a drop that runs out of budget mid-trace falls back to the floor height under the wound. A Landing is queued for its arrival time; `Gore._on_landing` shapes the stain (round / long with tail / run / spatter). The stain's shape is width ÷ sin(impact angle).
- Stains: one MultiMesh, two rings (48 big, 144 spots). `Gore.stain_transform(i)` / `stain_cell(i)` read back what a slot holds; the MultiMesh can't be read back under the headless renderer. Atlas is 4 × 4, thickness in RGB and coverage in A (two-channel LA PNGs imported striped on the Mobile renderer). The decal shader pulls quads 0.4 % toward the camera in clip space instead of a fixed offset, and fades specular at grazing angles; both were needed against banding.
- Stumps: `Enemy.Bleeder` pumps at `BLEED_HEART_HZ` with exponentially falling pressure (faster once dead) via `Gore.spurt`.
- Gib pool: hidden (cleared) gibs are reused first; a chunk may replace a limb that has lain `GIB_KEEP_TIME` (20 s). Without that, a long fight filled every slot with old limbs and bursts threw nothing.
- Captures: `--demo=gore-lineup` now has six men, ordinary guns (M14 arm, MG42 leg, pistol hand, buckshot head, M14 head, Gauss burst), a wall 1.5 m behind them, and cameras CapLineup, CapLineupL/R, CapLineupWall, CapLineupFloor. The test room's grid shader aliases into horizontal lines on surfaces seen edge-on; that isn't the blood.

## As built (2026-11-13: the moment of impact)

- Design: docs/design.md §5.5 "The moment of impact". Entry/exit bursts: `src/gore/impact_bursts.gd` + `impact_burst.gdshader` (MultiMesh, launch state in the instance transform, game clock from `Gore.drops.clock`). Round wakes in RX-9 slow motion: `src/vfx/round_wakes.gd` (owned by Ballistics, `Projectile.wake`). Tissue bits: `BloodDrops.KIND_CHUNK` in the drop's Z axis.
- Wounds in `triad.gdshader` are solid (no noise): hole, rim, lobed exits, soak darker near the hole. Keep the early-out radius in step with the widest shape (soak × 1.2 for the uneven edge, 1.34 r for exit lobes).
- `BaseMaterial3D.BILLBOARD_PARTICLES` drops the particle's scale unless `billboard_keep_scale` is true. Without it every CPUParticles3D quad is drawn at the mesh's 1 m size.
- Captures: `-- --demo=impact` with Godot's `--fixed-fps 60` so each frame is the same slice of time; `--impact-cam=shooter`, `--impact-normal`, `--impact-gun=<weapon>`, `--impact-zone=<zone>`. Frame sequence PNGs into the capture dir. Install `mesa-vulkan-drivers` first or captures silently fall back to Compatibility.
