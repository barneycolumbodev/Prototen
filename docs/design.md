# GRAFT — Game design

Moved from `CLAUDE.md` (sections 3–6). Section numbers are kept so references like "§5.3" still work.
Items marked *(proposal)* are Claude's suggestions and can change. Everything else was decided by the owner.

---

## 3. Augmentation

### 3.1 No classes

There are no classes or archetypes. A character is the set of parts installed in their body, plus their gear. What a character can do comes from how those parts combine.

### 3.2 Parts are physical, and they interact

Every part is a physical component of the body. That is what lets combinations work without scripting each pair.

Each part has:

- a body location and mounting points (it can require a mount or provide one)
- mass
- power draw or power output
- heat output or heat removal
- data links: values it reads from or sends to other parts
- stat changes and behavior hooks
- a visible model and the changes it makes to the body

Parts affect each other through these shared quantities. For example:

- A reinforced skeleton raises carrying capacity and recoil tolerance. That's what lets you fire a belt-fed machine gun from the hip.
- Muscle actuators raise speed and jump height, but they draw power and make heat, so a cooling part changes how long you can sprint.
- An optics package that tracks targets can feed a fire-control link in the hand, which changes how the gun handles, but only when both are installed.
- Heavy armor adds mass, which shortens wall-runs and changes slide distance.

New parts should plug into these quantities instead of adding special cases. When two parts do something useful together that nobody scripted, the system is working.

*(proposal)* Parts are also part of the damage model: hits to a body location can damage the parts installed there, and EMP shuts down powered parts. Try this in M2.

### 3.3 Passive parts

- Chosen before a session. Always on.
- Technical hardware names, for example "NW-4 Nanoweave Fiber Vest".
- They change stats and behavior, and they change how you look: your arms and hands in first person, your body in shadows and reflections, and your gear.

### 3.4 Active parts

Assigned to buttons. Pressing one switches you into a separate control mode with its own inputs, camera and HUD. Each has visible hardware and a deploy animation.

The owner's examples:

- **Shoulder-launched suicide drone.** A pod on your shoulder opens and launches the drone. You fly it from its camera and detonate it.
- **Monofilament whip.** Hold LT to stop looking around; the right stick then moves the whip through the air. A melee weapon.
- **Time slowdown.** Heavy, F.E.A.R. and S.T.A.L.K.E.R.-style impacts, especially with a SPAS-12. Hits sometimes knock enemies into ragdoll.

### 3.5 Starter parts *(proposal)*

| Part | Location | Effect | Cost or drawback | Appearance |
|---|---|---|---|---|
| NW-4 Nanoweave Fiber Vest | Torso | Resists small-arms fire | Adds mass | Woven fiber visible at collar and cuffs |
| Ceramic Trauma Plating | Torso | Large armor pool; stops rifle rounds | Heavy | Bolted plates over chest and shoulders |
| Titanium-Lattice Skeleton | Skeleton | Higher carry capacity and recoil tolerance; no fall damage | Adds mass | Anchor bolts at wrists and knuckles |
| Electroactive Myofibrils | Muscle | Faster sprint, higher jump | Power draw, heat | Synthetic muscle bands through forearm vents |
| Synaptic Accelerator | Nervous system | Faster aiming, reloads and recoil recovery | Power draw | Port at the base of the skull |
| Vestibular Stabilizer | Inner ear | Full accuracy while sliding or wall-running | — | Horizon line in the HUD |
| Ocular Ballistics Suite | Eyes | Shows penetration paths and headshot zones | Vulnerable to flashbangs | Optic glow in reflections; reticle overlay |
| Fire-Control Link | Hands | Less recoil and faster follow-up shots with linked weapons | Shut off by EMP | Contact pads on the palm; readout on the gun |
| Dorsal Load Frame | Spine | Hip-fire heavy weapons at full speed | No wall-running | Spinal frame; ammo feed over the shoulder |
| Subdermal Heat Sinks | Skin | Faster cooling | Hot signature; easier to spot | Fins along the forearms; heat shimmer |
| Hemostatic Nanites | Blood | Slow healing out of combat; less bleeding | High capacity cost | Wounds visibly close |
| Kinetic Dampers | Legs | Quiet footsteps, longer slides, softer landings | — | Piston joints at knees and ankles |

More actives *(proposal)*: mark several targets in slow motion and fire at all of them; shoulder ram; brace mode for heavy weapons; grapple line; through-wall scan; take over a turret or drone.

Shared resources *(proposal)*: power, heat, mass, and a capacity budget for the loadout.

---

## 4. Test loadouts

The owner described two combinations. They are benchmarks for the systems, built from the same pool of parts as any other loadout. They are not classes.

### 4.1 Fast pistol loadout (build first)

- **Weapon:** suppressed FN Five-seveN, 5.7×28mm, 20-round magazine, long suppressor. Quiet, precise, fast follow-up shots.
- **Parts:** myofibrils, synaptic accelerator, vestibular stabilizer, kinetic dampers, fire-control link. Actives: whip and time slowdown.
- **Movement:** sprint, slide, wall-run, mantle, air dash.
- **What it should do:** move very fast, land headshots quickly and work through a crowd. Rounds can pass through one enemy into the next.
- **Test** *(proposal)*: 12 enemies in a two-level room. A skilled player clears it in under about 25 seconds without stopping.

### 4.2 Armored machine-gun loadout

- **Weapon:** belt-fed machine gun modeled on the MG42, about 1,200 rounds per minute, built for an augmented carrier. Barrel heat and barrel changes.
  - Owner (2026-11-01): chrome and black steel, 1,200 rpm, a .308-class round (7.62×51), "absolutely shreds".
  - Owner (2026-11-01): later, whether you can wield it and how much it slows you will depend on your strength and parts. For now a flat penalty: you move a little slower with it out, and hip fire is loose (aimed fire is tight). Values in `data/weapons/mg42.tres` → Carry / Accuracy.
  - Built (2026-11-01): open bolt, 150-round box on the left feeding a short visible belt, clamp-on vertical foregrip for hip fire, tracer every third round. Stand-in for the strength system: `carry_*` scales in WeaponData.
- **Parts:** trauma plating, titanium skeleton, dorsal load frame, heat sinks. Actives *(proposal)*: shoulder ram, brace mode.
- **What it should do:** move slowly, absorb a lot of fire, and tear through cover and enemies with sustained fire.
- **Test** *(proposal)*: two squads behind mixed cover in a warehouse.

### 4.3 Shotgun

- **Saiga-12K** (owner, 2026-11-02, added to M1): semi-auto 12-gauge on the AK pattern, curved ("banana") 10-round magazine, milled black steel. You choose the shell type: **00 buck**, **slugs** or **Dragon's Breath**. The slug load carries a PSO-style optic (as on the SVD) at 1x.
  - Built (2026-11-02): each load is an `AmmoData` resource (`data/weapons/ammo/`) that sets pellets, pattern, velocity, drag, penetration, damage, recoil, flash and burn. The chamber and the magazine each track their load. Picking another load (D-pad left/right) swaps in a magazine of it and racks the old shell out. Slugs mount the optic, and the reticle's holdover marks are calculated from the slug's drop. Dragon's Breath fires 14 burning embers that set targets and flammable surfaces alight.
- **Later:** SPAS-12 with time slowdown: clearing rooms in slow motion, with ragdolls.

### 4.4 RC-6 "Lance" personal rail carbine

- Owner (2026-11-02): "a personal rail carbine. Sleek industrial bullpup design, unique sound. It needs to function with the enhanced lethality and insane ballistic power of a railgun in real life. Imagine a P90 crossed with the Halo 4 railgun, and maybe the design of Tau weaponry. This could be (but doesn't have to be) the signature weapon of the game."
- Look *(Claude's reading)*: P90 layout (compact bullpup, top magazine with a window onto slugs lying across the gun, integrated reflex optic, support grip joined to the trigger guard by a loop); Halo 4 railgun (two exposed rails forming an open fork at the muzzle, a top shroud that lifts to vent); Tau (pale ceramic plates layered over a dark graphite frame, glowing seams, swept side vanes). Real railgun hardware: copper-tungsten rails heat-tinted toward the muzzle, a capacitor bank with heat-sink fins in the stock, a power cell in the butt.
- Physics *(Claude's reading of "like a real railgun")*: no propellant, no case. A 7 g tungsten-core slug at 2,600 m/s (≈24 kJ, 8× the MG42, 56× the pistol); drop over 100 m is under 1 cm. Long-rod penetrator (`penetration_scale` 1.8): through AR500 plate, ~20 cm of concrete, several bodies. In flesh the drag grows with v² above 900 m/s (`SurfaceMaterial.drag_scaling_speed`), so a slug dumps over 1 kJ into a torso and still exits at ~2,500 m/s: any torso hit kills. Recoil is the slug's momentum (≈18 N·s).
- Capacitor: after a shot the bank recharges over 0.75 s. Fire early and you get as little as half the energy (velocity ∝ √energy, recoil and sound scale with it); wait and you get the full hammer. Rising whine while charging, a tone when full.
- Heat: every shot heats the rails in proportion to its energy. Spamming (~15 rapid shots) overheats them: the top shroud lifts, the rails steam and the gun can't fire for 1.6 s (reloading still works). Paced full-power fire never overheats.
- Every shot leaves an ionized-air trail through everything it crossed; blue-white arc flash; bigger impact effects. Values in `data/weapons/rail_carbine.tres`.

---

## 5. Combat simulation

### 5.1 Locational damage

Soldier of Fortune's GHOUL engine split bodies into 26 damage zones that each reacted differently. Use the same approach.

- Hitboxes on bones, about 20–26 zones: head, neck, upper and lower torso, groin, upper and lower arms, hands, thighs, shins, feet, each side separate.
- Each zone has its own reactions. Leg hits cause stumbling or limping. Arm and hand hits ruin aim or drop the weapon. Gut hits double enemies over. Head and neck hits kill or incapacitate.
- Shooting a weapon out of an enemy's hand can make them surrender.
- Wounded states: crawling, clutching a wound, calling for help.
- Armor: helmets and plates with protection levels. Penetration against protection decides whether a round gets through.
- Dismemberment from heavy rounds, explosions, the whip and the ram.

### 5.2 Ballistics

- Fast rounds are hitscan with penetration. Slow objects (grenades, the drone, the whip tip) are physical.
- Weapon data: damage, falloff, penetration, impulse, spread, recoil pattern.
- Material table for penetration: flesh, wood, drywall, sheet metal, concrete, armor plate. Penetration drops with each surface.

### 5.3 Feedback on every shot

- Camera kick and visible gun recoil, both spring-driven
- Muzzle flash and a brief light
- Layered sound: mechanism, shot, room tail (the tail changes with room size)
- Shell or link ejection
- Hit marker and sound, with separate headshot and kill sounds
- A hit reaction on every hit
- Impact decal and particles by surface
- A few frames of hit-stop on heavy hits and headshots
- Controller rumble where Android allows it
- Cancelable reloads; separate tactical and empty reloads

### 5.4 First-person animation

Weapon and arm motion is procedural: springs for sway, bob, recoil, landing, turning inertia, sprint, and slide and wall-run tilt, blended with a few authored poses. Spring values live in weapon resources and in an on-device tuning menu, so the owner can tune by feel and send the numbers back.

### 5.5 Ragdolls and gore

- Partial ragdoll for hit reactions. Godot's `PhysicalBoneSimulator3D` can simulate selected bones and blend them with animation.
- Full ragdoll on death, with impulse applied at the hit bone and scaled by the weapon.
- Blood: entry spray, exit spray when a round passes through, bigger bursts on headshots, splatter on the wall behind the target, pools under bodies, wound decals that stay on the body.
- Dismemberment: pre-split meshes with caps; gibs from a pool.
- Gore setting: off, standard, maximum.
- Everything pooled and capped (§8).
- Slow motion has to hold up: blood, ragdolls and debris still look right at 25% speed.

### 5.6 Enemy behavior

- Awareness from sight, sound (including suppressed shots at close range) and bodies they find.
- Near misses suppress them: worse accuracy, more time in cover.
- Morale drops with casualties and with seeing an augment up close. When it breaks they flee, freeze, surrender or fire blindly.
- Callouts that react to what you do ("Augment!", "Fall back!").
- Squads flank and suppress together. Only a few enemies shoot at the player at a time.
- Roles *(proposal)*: rifleman, shotgunner, shield carrier, machine gunner, marksman, launcher, anti-augment specialist (EMP grenades, armor-piercing rounds, drone jammer), officer.

---

## 6. Art direction

Decided: see "Visuals" in §2. No anime or cel shading.

*(proposal)*

- Detail goes first to the first-person arms, weapons and augment hardware, since they're always on screen. Then hit effects and gore, then lighting, then enemies, then environments.
- Baked lighting with a few dynamic lights. Height fog, dust, smoke, sparks, emissive lights, color grading.
- Effects built from meshes with scrolling textures, not huge particle counts.
- Heavy, worn, industrial hardware. Explore palettes with test renders in M4.
