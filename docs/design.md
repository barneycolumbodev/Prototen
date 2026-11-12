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
  - Owner (2026-11-05): on **LB**. Press to enter, press again to leave, or it runs until the points are gone; the allotment refills over time, like health. No holding, so you can aim and act while it's on.
  - Built (2026-11-05) as **RX-9 Reflex Overclock** (nervous system; a neural co-processor at the base of the skull overclocks perception and motor control). World at 30 %, the operative at 65 % (moving, shooting, reloading); looking stays real time. 8 s of charge, refills at 0.45/s after 2 s, needs 1.5 s to start. Colour drains, a cool vignette, everything muffled and pitched down (your own gun less), FOV +3°, ragdoll/limb/flinch impulses ×1.8. Charge bar above the health bar. Values in `data/body/parts/rx9_reflex_overclock.tres`. Not yet: knocking living enemies into a ragdoll.

- **Three actives on one button** (owner, 2026-11-07): "there's going to be basically 3 active augmentations that you can use at one time, but they're all activated by the same button, LB." **D-pad left / down / right** selects slot 1 / 2 / 3; **LB** toggles the selected part. A part keeps running when you select another (RX-9 can stay on while you raise the arm cannon); select it again and press LB to stop it. The HUD rows above the health bar show each part's D-pad arrow and charge, the selected one bright and tagged LB. RB is free. The Saiga's shell type moved to **D-pad up**. Loadout: RX-9 on D-pad left, GX-4 on D-pad down, right empty.
  - 2026-11-10: with nine actives, the D-pad directions follow **the order the actives were installed in** (first = left, second = down, third = right; `BodyLoadout.slot_of`). A fourth pushes out the first. On the loadout screen, A on an installed active moves it to the next direction.
- **GX-4 Gauss arm** (owner, 2026-11-07): "a prosthetic arm that's also a Gauss cannon... the character lifts up his hand and it badassly, complexly cyber transforms into this almost Doom-like Gauss cannon. You have 10 shots... a very special gore effect where it almost blows a spiral through them... a horrific electronic weapon. Very loud, really powerful, can overpenetrate... like the golden gun in Destiny." Built:
  - **Hardware:** the right forearm is a prosthetic coilgun in the graft-suit look (satin black plates with lit seams over a gunmetal chassis, pistons underneath). Inside, six copper drive coils on two guide rails; a capacitor bank at the elbow; three dorsal heat-sink fins; a ten-LED round counter on the top plate. Model and animation: `raw_assets/augments/gx4_gauss_arm/build.py` (Blender, 33.8k triangles, factor materials, not baked yet). Previews: `docs/previews/gx4_gauss_arm_sequence.png`, `gx4_gauss_arm_ingame.png`.
  - **Transformation (1.6 s, one keyframed clip):** the gun goes down and the open hand comes up, palm in; it holds a beat, the fingers curl into a fist one by one, the wrist turns forward, the forearm plates swing open on the glowing coils, the fist splits into a two-pronged fork, the rails telescope out through it, the six coils slide forward and lock one after another, the muzzle ring runs to the tip, and the fins stand up. A sound sequence is timed to every step (servos, joint clicks, hiss, six coil clacks, a power-up whine). LB folds it back (the clip reversed, 0.8 s); the gun comes back up.
  - **Firing:** RT, one shot per 0.6 s, 10 rounds. A 40 g slug at 3.2 km/s (about 200 kJ): it kills anything it hits and goes on through people and thin cover (24 penetrations, 5× penetration). Heavy camera kick, the arm thrown back, a 7° FOV punch, a beat of hit-stop, full rumble, the coils rippling forward, the glow flashing. The shot is a six-coil stutter, an electrical snap, a falling electric roar, a sub-bass boom and a long rolling tail. Empty, it folds away by itself; rounds refill one at a time (one per 4 s after 3 s) while it's folded. LT zooms a little.
  - **Beam:** a white-hot core and a blue double helix of ionized air that corkscrews round it, spreads out and lingers (`src/vfx/gauss_beam.*`, one mesh built once, 3 pooled).
  - **Gore** (`src/gore/gauss_gore.gd`): replaces the usual sprays. Blood drops and a fine spray leave every body it passes through along a double helix that spins outward (the corkscrew; since 2026-11-11 they are ordinary blood drops that fall and stain); blue arcs crawl between the body's joints for 1.5 s, sparks spit from the wounds, smoke curls off them, and the corpse spasms. At Maximum, chunks blow out of the exit wound; heads and limbs come apart on the usual energy thresholds.
  - Tuning: `data/body/parts/gx4_gauss_arm.tres` (timings, rounds, kick, glow), `data/weapons/gx4_slug.tres` (the round), `data/player/viewmodel_gx4.tres` (where the arm sits).

### 3.4b The seven actives of 2026-11-10

Owner (2026-11-10): "Based on the system of passive augments we have and how they set requirements, it's time to instantiate the ability keys, the active augmentations. Mono filament razor whip, shoulder launcher suicide drone, ultra prehensile nanotech mesh arm thing that grabs and can throw enemies... I need at least 4 more active augmentations added in this pass... with animations and models and stuff." The three the owner named, and four more *(Claude's choice: proposal)*: ram thrusters, a thermoptic shroud, a fan shield, an arc projector. All are hardware; each needs stats from the passives and changes with them.

| Part | Where | Needs | What the body's stats change |
|---|---|---|---|
| **MW-7 Monofilament Whip** | right arm | processing ×1.10 | melee speed: how fast it swings and lashes; melee power: how deep it cuts |
| **NT-5 Prehensile Mesh Arm** | left arm | strength ×1.15, structure ×1.20 | throw speed = 17 m/s × usable strength ÷ 1.15 × √impact (9–34 m/s) |
| **BW-6 Bulwark Fan Shield** | left arm | structure ×1.15 | integrity = 14 kJ × structure ÷ 1.45; the R3 bash uses mass, strength and impact |
| **SD-3 Shrike Drone Pod** | back hardpoint | connectivity 3 | link range = connectivity × 40 m; processing sharpens its turning |
| **AD-2 Arc Projector** | back hardpoint | power supply 600 W | each arc takes 18 kJ of reserve; +1 chain link per 30 kJ of extra reserve; spare power refills charges faster |
| **KR-5 Ram Thrusters** | back hardpoint | structure ×1.30 | the hit = the slide hit × 1.8 (mass × usable strength × impact); lighter bodies fly faster; 7 kJ and 4.5 kJ of heat per burn |
| **TC-4 Thermoptic Shroud** | skin | cooling 420 W | traps 2.4 kW while up: cooling decides how long before it overheats and fails; signature scales the distance they see through it |

- **Hands** (`Player.claim_hand`): a part that needs a hand takes it while it runs; two parts can't share a hand; the gun needs both, so it goes away while either is taken. Right hand: GX-4, whip. Left hand: mesh arm, shield. So the whip and the shield run together, or the Gauss arm behind the shield. The arc projector, ram thrusters, shroud, drone and RX-9 need no hand: the gun stays up.
- **One part per arm** (`PartData.mount`): the GX-4 and the whip are both the right forearm; the mesh arm and the shield are both the left. Installing one takes the other out.
- **A new body location, back hardpoints** (two slots): the drone pod (behind the left shoulder), the arc projector (over the right shoulder), the ram thrusters (shoulder blades).

**MW-7 Monofilament Whip** (owner, §3.4: "Hold LT to stop looking around; the right stick then moves the whip through the air. A melee weapon.")
- A reel on the back of the right wrist pays out 6.5 m of filament with a tungsten bead. The filament is 17 points simulated in the world: the reel is its root, the direction the hand points drags each link (hard near the hand, weakly at the bead, so the tip lags and cracks), every link keeps its length, the world stops it (sparks, a scrape).
- **LT held:** the view freezes and the right stick places the hand (full stick = 62° to the side, 42° up or down). **RT:** a lash, a 115° sweep across the crosshair in 0.2 s, alternating sides. Otherwise it hangs low on the right.
- Whatever a link crosses at 8 m/s or more is cut: an `AugHit` on the hitbox it crossed (95 damage × √melee power, treated as 1.5 kJ for wounds), so at Maximum gore limbs and heads come off, and corpses can be cut up. A swoosh trail behind the bead, a crack above 75 m/s, a short hit-stop and rumble on each cut.
- Model: `raw_assets/augments/actives/mw7_monofilament_whip/build.py` (14k triangles): the graft-suit forearm, a copper drum between cheek plates, a feed boom that slides out over the knuckles, a ceramic nozzle whose jaws open, two blade guards that stand up, the hand making a two-finger point. Deploy clip 0.6 s.

**NT-5 Prehensile Mesh Arm**
- The left forearm is a braid of twelve carbon-nanotube muscle strands. Deploy (0.7 s): three clamp plates lift off, the braid loosens and turns, the hand draws into the wrist ring and a four-fingered claw takes its place.
- **RT** shoots the tendril (75 m/s, 18 m reach) at whoever is nearest the crosshair. On contact the man is **seized** (`Enemy.seize`): he drops his gun, goes limp as a living ragdoll, leaves the fight, and is hauled to a point in front and left of the operative, where he takes the rounds meant for you. **RT again** throws him along the view (`Enemy.release`): he flies, anyone within a metre of his path is knocked down (killed at 13 m/s or more), and he dies where he lands. LB folds the arm and drops him. Four grabs stored, one back every 5 s.
- The tendril and claw are drawn every frame as tubes along a curve from the wrist (`src/vfx/tube.gd`), with lit seams that pulse on a grab or throw.
- Model: `nt5_mesh_arm/build.py` (10.7k triangles).

**BW-6 Bulwark Fan Shield**
- Seven boron-carbide leaves on a hub on the left forearm fan out into half a disc 0.4 m in radius (0.5 s; each leaf overshoots and latches). You hold it across your chest and look over the top edge.
- Rounds from within 75° of the view are stopped (`Player.hit_interceptors`): no damage, sparks, a clank, the arm jolts; the round's energy in kJ comes out of the integrity (the charge). At zero it breaks: it folds and can't come up for 5 s. Integrity refills at 1.2 kJ/s after 3 s.
- While it's up you move at 85 % and the R3 strike shoves ×1.6 (a shield bash). The rim seam goes from amber to red as it wears.
- Model: `bw6_fan_shield/build.py` (24.7k triangles).

**SD-3 Shrike** (owner, §3.4: "A pod on your shoulder opens and launches the drone. You fly it from its camera and detonate it.")
- LB launches one of three: it leaves the pod, flies out in front of you unfolding (0.75 s), and the view cuts to its camera (84° field of view; the front rotors and the warhead frame the picture). Left stick flies (15 m/s), right stick looks, A/B climb and sink, **RT detonates**, **LB cuts the link**. Touching an enemy or hitting anything at 8 m/s or more sets it off.
- The blast (`src/weapons/explosion.gd`): 6.5 m radius, 300 damage at the centre falling off to the edge, line of sight required, bodies thrown, limbs off close in at Maximum gore; it hurts the operative too.
- The HUD shows link %, distance over range, battery (22 s), brackets with the distance on every enemy (red inside the blast radius). The picture breaks up beyond 60 % of the link range and the drone drops at 100 %. Your body stands where you left it (`BodyAppearance`, in your colours and hardware) and is still shot at: BODY UNDER FIRE flashes, and below 30 % health the link drops by itself.
- New drones are printed one every 30 s. Model: `sd3_shrike_drone/build.py` (6.6k triangles, an unfold clip).

**AD-2 Arc Projector**
- An electrolaser on a mast over the right shoulder: finned capacitor body, quartz window, three tungsten electrodes. LB swings it up into the top right of the view (0.4 s) and it fires at whoever is nearest the crosshair within 16° and 22 m; LB again fires the second charge; it folds 2.2 s after the last one. The gun stays in your hands.
- The arc does 130 damage to the first body, then jumps to the nearest body within 7 m (×0.7 each jump): two jumps with the base 60 kJ reserve, four with an FB-1. Bodies it doesn't kill stagger and lose their nerve; all of them arc and spasm (the GX-4's electrocution).
- Each discharge takes 18 kJ from the power reserve (it's offline below that) and puts 3 kJ of heat into the body. Charges refill one per 10 s × spare power ÷ 300 W.
- Model: `ad2_arc_projector/build.py` (9.3k triangles); the bolt is `src/vfx/arc_bolt.gd`.

**KR-5 Ram Thrusters**
- One press: thrown along the view at 27 m/s × √(125 kg ÷ mass) for 0.26 s (up to 22° up, 8° down), through anyone in the way (`Player.start_dash`). Each body gets the slide hit × 1.8: about 17 m/s from the Operator (lethal at 16), a shove from a light body. Speed lines, a 13° field-of-view punch, hit-stop on contact. Two burns stored, one back every 4.5 s.
- No first-person model (they're on your back); on the body: two nacelles with bell nozzles and a gas bottle.

**TC-4 Thermoptic Shroud**
- LB raises it (0.5 s), LB drops it; 10 s of charge. While it's up enemies don't see the operative beyond 3 m × signature (`BodyModel.hidden_at`, checked in `Enemy._update_perception`); they still hear footsteps and remember where they last saw you. Firing shows you for 1.1 s and costs 1.2 s of charge; a hit shows you for 0.6 s.
- Your own arms and gun turn to glass outlines; a lattice shimmers at the edge of the view.
- It takes the skin slot (no HS-5) and traps 2.4 kW: ten seconds leaves the body near three quarters heat (which raises your signature once it's down); overheat and it fails.

**On the body** (the loadout screen and the drone's view of you): each of the seven has baked hardware modelled on the operative (`raw_assets/augments/actives/body_hardware.py`): the three-tube pod, the stowed emitter head, the thruster nacelles, hexagonal emitter studs over the whole suit, the reel on the right wrist, the braid over the left forearm, the folded leaves along it.

**Sounds:** 42 files synthesized by `raw_assets/audio/build_actives_sfx.py`.

**Cloud captures:** `-- --demo=active:<part id>` with `--act=lash|grab|throw|fly|boom|arc|ram` (`src/core/debug/actives_demo.gd`).

### 3.4a Parts system and the operative (built 2026-11-05)

- **The operative** (owner, 2026-11-05): "a dude in a black synth suit... a really sleek-looking black carapace over his body. That's what our baseline augmented soldiers should look like. The different passives and actives can change the look." First pass rejected the same day ("technically viable, but zero artistic inspiration... looks like a crash test dummy"; the owner wants "sleek, baseline, polymer, badass"). Second pass: a gloss carapace (owner: "a mix of what I genuinely want with... Imperial Death Troopers... not Star Wars... substantially less armor and more of a sleek interface for the rest of the augmentations"). Third pass: an undersuit with interface hardware only. Armour is a loadout part that goes on top of the suit.
  - **Fourth pass: the GS-2 graft suit** (owner, 2026-11-05, on the third pass: "the suit is better... but still not good enough... the massive... [chest plate]... the whole design needs to be more synthetic, nano-weave, smooth, flat plates grafted together on a nylon base and an undersuit, rather than bulky, mechanical, pre-configured metal shell... a lethal undersuit"). Rebuilt in `raw_assets/characters/operative/build.py`:
    - **Physique** from the owner's reference photo: heavy traps, capped delts, wide lats, a narrow waist, about 8 heads, 1.86 m, same skeleton as the triad. The pectorals are flat slabs in the anatomy, so nothing reads as a bust.
    - **Undersuit:** matte black nanoweave (a fine diamond weave in the normal map) with panel seams. The ribbed flex zones are gone.
    - **Grafted plates:** thin (4–6 mm), flat-faceted, angular, satin black, each a separate piece with bare weave around it: split pectoral plates with straight lower edges and a weave channel down the sternum, collarbone strips, paired abdominal plates, serratus slats, a trap yoke, scapula and lat plates, a segmented spine, deltoid caps and lames, triceps and forearm strips, back-of-hand and knuckle plates, split quad plates, outer thigh strips, diamond knees, shin strips, faceted boots.
    - **Hardpoints:** gunmetal pads with a light dot standing proud of the plates on the shoulders, forearms and thighs, where part hardware docks.
    - **Neck:** bare weave up to a clean seal under the jaw. No rings or tube.
  - **Helmet** (owner: "more angular and predatory, maybe like the bottom of an Oni mask"; the ribbed neck "screams hacky sci-fi"): a faceted skull with a central ridge; the brow is a keel that recedes at the sides and overhangs a narrow V visor (inner corners low, two slits split by a bridge, lit lower lip at the outer ends). The lower half is an oni-style mask: a faceted muzzle with flared cheeks, a nose keel, cheek ridges from the mouth corners to the cheekbones, a snarl-shaped mouth recess with vertical vanes, and a pointed V chin. Flat side panels with a sensor slit, nape lames at the back. Light only on the visor lip and the sensor slits.
  - **Helmet off: the owner's face** (owner, 2026-11-05: "I want the operative to have my face"). `raw_assets/characters/operative/likeness/capture.py` runs MediaPipe Face Landmarker on the owner's selfies, averages the aligned 3D landmarks for the face shape, unwraps the most front-on photo into the canonical face UVs and evens out its lighting (the shadowed half is re-toned from the lit half). Only the derived files are committed (shape, topology, unwrapped texture); **the photos stay out of the repo.** The head is a sculpted skull with ears and a neck; its front is morphed onto the face surface where the photo can be trusted, and the jaw sides are built from the face outline. Colour is computed per texel: the photo inside the face, matched procedural skin with freckles and jaw stubble elsewhere, curly brown hair with golden tips (clustered curl volumes and small ringlet loops). It's a likeness from photos, not a scan: shape detail is limited to what the landmarks capture.
  - **Three meshes:** the suit with its plates (about 26.6k triangles), the helmet (about 8.9k) and the bare head (about 9.4k with hair); about 35.5k on screen either way. Suit and helmet share one baked atlas (base colour, ORM, normal, emission); the head has its own (base colour, ORM, normal). `BodyAppearance.helmet_on` swaps helmet and head; on the body-status screen **Y** toggles it (cloud capture: `--capture-body --capture-bare`).
  - Seen on the **body-status screen** (View button): a turntable in a relaxed stance (arms down, elbows bent, fingers curled) under a studio sky that only the gloss plates reflect. Next: first-person arms in the same suit, the full body in shadows and reflections.
- **Code** (§9.2 proposal, now built): `PartData` (location, mass, power, heat, capacity, `StatModifier`s, `PartVisual`s), `ActivePartData` (button slot, timings, charge), `BodyLoadout`, `BodyModel` (totals; stat = (base + Σadd) × Πmul; a power reserve and stored heat), `ActivePart` (idle → deploying → active → recovering → cooldown, interrupt), `Augments` (LB/RB/D-pad up), `BodyAppearance` (mounts part hardware on bone sockets). Frame values (mass, capacity, power, heat) in `data/player/body_default.tres`; parts in `data/body/parts/`; the default loadout (GS-2 graft suit, part id `cs1_carapace`, + RX-9) in `data/body/loadout_default.tres`.
- Wired so far: see §3.6 (2026-11-08): every core stat is read by gameplay, power and heat have consequences, and the loadout screen builds bodies from the passive library.

### 3.5 Starter parts *(proposal, superseded by the §3.6 library)*

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

### 3.6 Core stats, passive library and the loadout screen (built 2026-11-08)

Owner (2026-11-08): "Each passive augment needs to make sense, have a high effort corresponding texture on the character, and contribute to a solid stat boost in one direction with a tradeoff in another... Core stats should affect mobility, melee, potentially gun proficiency of different types, hitbox size, knock power when sliding (derived from a momentum/strength function which is heavily rooted in passive augments)... an extensive library... baseline stats from passives are necessary to meet requirements to use some active augs, or the passive stat changes something about how the active is used... connectivity... controls if remote control of drone-type augments can be used... and how far the drone can fly... Relationships like this should be very common." Not every part needs its finished look yet; a few should look really good, neutral placeholders for the rest.

**Core stats** (`src/body/stats.gd` lists them with what reads each; base values in `data/player/body_default.tres`). Every stat = (base + Σ add) × Π mul over the parts that are online, clamped to a range.

| Group | Stats and what reads them |
|---|---|
| Durability | health; damage per kJ of a hit (armour); regen rate; regen delay |
| Mobility | move speed; agility (acceleration, braking, air control, slide steering, mantle speed); jump; slide (friction and launch); wall-run (duration; 0 = can't); climb (highest mantle) |
| Strength | strength (muscle force); structure (skeletal rating); carry (kg of weapon without a handling penalty); impact (how hard the body hits) |
| Melee | melee power; melee speed (R3 strike, new) |
| Firearms | recoil; aim speed; reload speed; handling (draw, holster, sprint-to-fire); stability (accuracy moving and in the air); proficiency per class: handguns, shotguns, rifles (and rail guns), heavy weapons — each scales recoil (÷), spread (÷ √), aim and reload speed (×) for its guns |
| Signature | silhouette (hitbox size: enemies' aim error ÷ it, spotted faster); signature (thermal/visual: how fast enemies spot you); noise (how far enemies hear you move: 13 m at a sprint ×1, quieter crouched) |
| Neural | processing; connectivity (0 without a neural link); perception (aim-assist strength) |
| Power and heat | power supply; power reserve; cooling; capacity (the loadout budget, 16) |

**Relationships** (`src/body/body_model.gd`):
- **Usable strength** = min(strength, structure × 1.3): muscle stronger than the skeleton can take is throttled.
- **Load** = mass ÷ usable strength. Up to 104 kg nothing changes; above it speed, jump and wall-run fall off, down to −40 % at 174 kg. Below 88 kg a light body gets +6 %. So heavy armour needs muscle, and muscle needs bone.
- **Slide hit** = 6.5 m/s × mass/100 × usable strength × impact × slide speed; damage grows with its square; 16 m/s or more breaks the body (lethal, ragdoll). The base operative shoves (~9 m/s, 16 damage); the Juggernaut kills.
- **R3 strike:** 55 × melee power × usable strength damage; the shove is 7 m/s × mass/100 × usable strength × impact; 17 m/s or more is lethal; recovery 0.42 s ÷ melee speed. A short lunge, hit-stop, rumble, blood. Values in `data/player/melee_default.tres`. Played as a knife slash (2026-11-12): the gun drops away, the right hand comes in from the lower right with the KB-1 combat knife, cocks high right, cuts down-left through the target at the moment of the hit (windup 0.11 s) and follows through, with a trail along the edge that runs red after a cut; then the gun comes back. Keyframed in camera space in the same .tres (`knife_*`), model from `raw_assets/weapons/knife/build.py`; preview `docs/previews/knife_slash.png`.
- **Heavy weapons:** recoil also ÷ √(usable strength × structure); the carry penalty of a heavy gun shrinks with the carry stat (base 40 kg ÷ carry).
- **Link range** = connectivity × 40 m (for drones, when they exist).
- **Signature now** = signature × (1 + stored heat fraction); enemies spot you at silhouette × signature.
- **Power:** constant draw above supply drains the reserve; an empty reserve (brown-out) stops actives that draw power from starting. **Heat:** stored heat (30 kJ) fills when heat made exceeds cooling; full = overheated: no regen, a hot signature.
- **Requirements:** a part can need stats (`StatRequirement`). If they're not met it stays installed (mass and capacity count) but is **offline**: no stats, power or heat; an offline active shows OFFLINE and the reason on the HUD and can't start. Requirements chain (taking one part offline can take others with it).
- **Actives read stats** (the seven of 2026-11-10 are in §3.4b): RX-9 needs processing ×1.15; processing sets the operative's speed in slow motion (×0.65 of real time at ×1.20, faster above) and the charge (8 s at ×1.20). GX-4 needs structure ×1.25; bracing (structure × usable strength) scales its kick (×1 for the Operator, about half for the Juggernaut); power headroom sets how fast rounds recharge. FC-1 needs connectivity 1. Future drones: connectivity gates them and sets their range.

**Body locations** (each holds one part unless noted): suit (fixed: the GS-2), cranial, eyes, inner ear, nervous system (2), skeleton, musculature, organs (2), torso armour, arms (2; one part per arm among the GX-4, whip, mesh arm and shield), hands, legs, spine, back hardpoints (2; 2026-11-10), skin, blood.

**Passive library** (37 passives; generated from the table in `tools/parts/gen_parts.py` into `data/body/parts/`, listed in `data/body/part_library.tres`). Each improves something and costs something (mass, power, heat, capacity, a requirement or a stat):

| Location | Parts |
|---|---|
| Nervous | SA-2 Synaptic Accelerator (processing, aim, reload); ER-2 Reflex Arc Bypass (agility, melee speed, handling; more recoil); MR-1 Mesh Relay Lattice (connectivity 1.5; signature) |
| Cranial | NL-3 Cortical Uplink (connectivity 3; signature); TG-6 Threat-Graph Co-processor (perception, processing; hot) |
| Eyes | OB-5 Ocular Ballistics Suite (perception, rifles, handguns); IR-3 Thermographic Retinas (perception, cheap) |
| Inner ear | VS-1 Vestibular Stabilizer (stability ×1.6, wall-run) |
| Skeleton | TL-3 Titanium-Lattice (structure ×1.45, carry, recoil, health); CB-1 Carbon-Weave Sheathing (structure ×1.25, light); TN-9 Tungsten Long-Bone Cores (structure ×1.9, impact, health; 18 kg, less jump and agility) |
| Musculature | EM-2 Electroactive Myofibrils (speed, jump, strength; power, heat); HM-5 Hydraulic Myomer (strength +0.65, melee; needs structure 1.2, slower to turn, loud); FT-1 Fast-Twitch Graft (agility, melee speed; less strength and health) |
| Organs | HP-4 Hyperoxic Lungs (regen delay, cooling); CH-2 Cardiac Pump (regen, health); PC-3 Power Cell (+200 W; heat, signature); FB-1 Fuel Bladder (+60 kJ reserve) |
| Torso armour | NW-4 Nanoweave (armour, light); CT-7 Ceramic Trauma Plating (armour ×0.62, health, impact; 18 kg, silhouette, noise, traps heat); RP-2 Reactive Ram Plating (impact ×1.7, melee); AB-1 Ablative Shell (armour, low signature; slow regen, hot) |
| Arms | SR-3 Servo-Recoil Struts (recoil ×0.75, heavy); KS-2 Kinetic Striker Rams (melee ×1.7; needs structure 1.15) |
| Hands | FC-1 Fire-Control Link (recoil, all proficiencies; needs connectivity 1); DG-3 Dexterity Grafts (reload ×1.3, handling); GP-1 Setal Grip Pads (climb, wall-run) |
| Legs | KD-2 Kinetic Dampers (noise ×0.55, slide ×1.3); SP-6 Sprint Pistons (speed, jump; noise ×1.4); LF-8 Leg Frame (carry, impact; less agility and slide) |
| Spine | DL-1 Dorsal Load Frame (carry +55, heavy ×1.35; no wall-running, big silhouette; needs structure 1.2); SB-2 Spinal Bus Extender (+3 capacity; needs processing 1.1) |
| Skin | HS-5 Heat Sinks (cooling +260 W; signature ×1.3); CM-1 Chromatophore Mesh (signature ×0.55, smaller silhouette; thinner); DS-2 Dermal Lattice (armour, health; holds heat) |
| Blood | HN-1 Hemostatic Nanites (regen); OC-2 Respirocytes (speed, regen delay, cooling) |

**Presets** (`data/body/presets/`, on the loadout screen; 2026-11-10: three more built round the new actives: **Reaper** (whip + fan shield + ram thrusters + ram plating), **Handler** (Shrike drone + arc projector + RX-9 on the uplink, power cell and fuel bladder), **Wraith** (thermoptic shroud + mesh arm, quiet dampers, extra cooling)): **Operator** (the default: TL-3, SA-2, EM-2, HS-5, RX-9, GX-4), **Ghost** (silent and quick; no Gauss arm), **Juggernaut** (CT-7, TN-9, HM-5, DL-1, GX-4: heavy hip fire, killing slides; no slow motion, no wall-running), **Marksman** (NL-3 + MR-1 feed the FC-1 and OB-5; light carbon frame, GX-4).

**Finished hardware** (Blender, baked 1024² texture sets; generators in `raw_assets/augments/passives/<id>/build.py`, sharing `_common.py`; each piece modelled on the operative's real surface and mounted on its bone). 20 of the 37 passives, every passive with hardware in the four presets, and the RX-9 active (2026-11-09: owner, "replace the placeholder assets, at least a decent amount of them"). Overview: `docs/previews/passives_overview.png`; per part: `docs/previews/<id>.png`. Parts that share a preset were built around each other (DL-1 clears CT-7's back plate and anchors through its spine channel; HM-5 leaves the back to them; RX-9 sits between NL-3's blades; the forearm is shared out: HS-5 outside, EM-2 front, TN-9 ulna edge, KS-2 inside, FC-1 inner wrist, TL-3 back of the wrist).

| Part | Hardware |
|---|---|
| CT-7 | Split faceted breastplate with a chevron edge, abdominal lames, back plate with a spine channel, pauldrons with lower lames, collar guards; hex bolts, stencils, status lights. |
| HS-5 | Temper-coloured fin stacks on the outer forearms over an amber hot core. |
| NL-3 | Nape transceiver with swept antenna blades along the helmet, fibre trunk and junction block. |
| KD-2 | Knee hubs with a light ring, chrome piston rods into damper bodies, ankle dampers. |
| EM-2 | Vented trays on the front of the forearms and biceps: striated polymer strands with electric-blue light between them, cross straps, tendon anchors. |
| TL-3 | Titanium wrist saddles pocketed with the hex lattice, gold-anodised anchor bolts; a knuckle bar with one anchor per metacarpal. |
| SA-2 | Two signal spools on the sides of the neck: pearl myelin discs lit teal in a faceted capsule, fibre leads round to the spine. |
| RX-9 (active) | Slim module on the occipital keel between the NL-3 blades: a cold white escapement slit, heat-sink ribs, fibre leads into the nape. |
| DL-1 | Twin-rail spine beam on standoffs into the vertebrae, yoke and outrigger hubs, hooked arms over the shoulders to chest clamps, lumbar belt; a 250-round canister on the right hip feeding an armoured chute over the right shoulder to a hazard-banded feed mouth. Dark olive over gunmetal. |
| HM-5 | Corrugated myomer bellows around a chrome ram on each thigh, a big ram on each triceps, hip pumps with an amber pressure window and a gauge. |
| TN-9 | Segmented tungsten strike bars down the ulna edge and the shins, the core exposed in the gaps (machined rings, steel collars); core caps below the knees. |
| RP-2 | Crowned shoulder wedges and a sternum prow faced with reactive tiles (chevrons, bolts) and a red firing strip. |
| KS-2 | Twin pneumatic rams on the inner forearm, valve block with a ready light, air bottle, striker yoke at the wrist. |
| FC-1 | Gold contact grid in each palm inside a teal link ring; inner-wrist link module with a bore-alignment readout; fibre between them. |
| OB-5 | Laser rangefinder pod on the right brow (violet objective, red emitter, amber ready light) and a ballistic sensor on the left. |
| MR-1 | Geodesic filament lattice over the crown with lit relay nodes; the forehead stays clear. |
| VS-1 | Gyro pucks behind the ears: brass gimbal rings in a recessed bezel, a teal horizon bar, a teardrop fairing into the helmet. |
| PC-3 | Sealed tritium cell on the left flank in a cradle: green phosphor window, yellow trefoil band, knurled caps, conduit into the ribs. |
| SP-6 | Twin gas pistons down the back of each calf from a manifold to heel spurs; oxide-red gas bottle and a sooty exhaust block on the outer calf. |
| CM-1 | Panels of hexagonal chromatophore cells in mixed dark tones on the outer upper arms and the flanks, with driver nodes. |
| DG-3 | Four micro-actuators over the extensor tendons on the back of each hand, from a lit header at the wrist; gold tips. |

Of the other 17 passives, 9 still show neutral gunmetal or glow placeholders at their mount points (ER-2, TG-6, IR-3, NW-4, AB-1, SR-3, GP-1, LF-8, SB-2) and 8 are internal with nothing to show (CB-1, FT-1, HP-4, CH-2, FB-1, DS-2, HN-1, OC-2). Shared kit for new parts in `_common.py` (2026-11-09): `cyl`, `slab`, `prism`, `sweep`, `link_chain`, `cable`, `add_obstacle` (cast against another part so pieces clear it) and `run` (bake, export, preview sheet).

**Loadout screen** (View button; Pause → Body status). Rebuilt 2026-11-11 (owner: "set it up as a menu where all the options are laid out and you can just click on the one you want... if it tells you, oh, you need this, you can just go look and click on it"): every part is a tile on one screen: the presets, the nine actives (orange; installed ones show their D-pad arrow), then the passives row by row under their body location (installed: teal with +; installed but offline: red). The D-pad or a tap moves the cursor, and the model and every number preview the part under it. **A** (or a second tap, or the button under the card) installs it, or takes it out if it's in, or applies a preset. **X** moves an installed active to the next D-pad direction. When the selected part needs a stat it doesn't have, the card lists every part that supplies it (with its location, tappable), those tiles get an amber outline, and **RB** jumps to the one that fixes it on its own (else the strongest). With nothing selected that needs anything, RB goes to the fix for whichever installed part is offline. The screen opens on an offline part if there is one, and the HUD's OFFLINE line names the fix too ("needs processing ×1.15+ (fit SA-2 or TG-6; View)"). **LB** switches to the Colours page (§3.7), **Y** helmet, **LT** zoom, the right stick turns the model, **B** closes and puts the loadout on the player (saved to `user://loadout.cfg`). The card shows mass, power, heat, capacity, what installing it would take out, every effect coloured by whether it helps, requirements met or not (with the current value) and how the part combines with others.

### 3.7 Colours (built 2026-11-10)

Owner (2026-11-10): "I also want a full part by part color customizer for my character."

- **Colours page** on the loadout screen (LB). One row per suit piece: helmet, visor, undersuit, torso plates, arm plates, hand plates, leg plates, boots, trim and hardpoints, suit lights; then two rows per installed part with hardware: its paint and its lights. Left/right steps through a 27-colour palette, A opens sliders (hue, saturation, brightness, finish: as built / matte / satin / gloss / metal), X puts the piece back the way it was built. The model previews every change. Saved with the loadout (`user://loadout.cfg`).
- **How it paints** (`src/body/body_colors.gd`, `src/body/suit_paint.gdshader`): the suit and the first-person arms are baked texture sets, so each has a **region map** beside it (`<name>_regions.png`, one byte per texel: which piece it is). `tools/colors/build_regions.py` makes them from what the bake already holds: the material from the ORM map (each source material has its own roughness and metallic), the body area from the mesh (which bone moves each triangle most). The shader looks the texel's piece up and replaces its colour, scaled by how light the texel was against the piece's own base colour, so grime, edge wear and the weave survive. Lights keep their brightness and take the new hue. A part's hardware is painted as one piece the same way.
- **Where it shows:** the loadout screen, the first-person arms on every gun (arm plates, hand, undersuit, lights), the actives' first-person arms (their plates, weave and pads follow the suit by material name), and the operative seen from the Shrike.
- Not yet: separate colours for left and right, patterns or decals, the guns.

---

## 4. Test loadouts

The owner described two combinations. They are benchmarks for the systems, built from the same pool of parts as any other loadout. They are not classes.

### 4.1 Fast pistol loadout (build first)

- **Weapon:** suppressed FN Five-seveN, 5.7×28mm, 20-round magazine, long suppressor. Quiet, precise, fast follow-up shots.
- **Parts:** myofibrils, synaptic accelerator, vestibular stabilizer, kinetic dampers, fire-control link. Actives: whip and time slowdown.
- **Movement:** sprint, slide, wall-run, mantle, air dash.
  - Slide (owner, 2026-11-07: "longer", plus "a moderate knockback if you slide into an enemy", later dependent on mass and strength parts): a tap of B slides until the speed runs out (about 18 m from a sprint); B again, A (slide-hop) or pulling the stick back ends it. Sliding into a living enemy shoves him along the slide (6.5 m/s for a 100 kg operative at strength 1; scales with body mass × the `strength` stat × slide speed), staggers him, costs him 8 health and morale, and costs you 20 % of your speed; hit-stop, rumble and a camera knock. Values in `data/player/movement_default.tres` (Slide, Slide knockback). The `strength` stat exists for parts to raise.
  - Owner (2026-11-05): "the goal is for your character to feel like a supremely dexterous super soldier"; on the Chinatown map movement "doesn't feel smooth, it feels weird interacting with the world." Built: step-up over curbs, sills and treads up to 45 cm at full speed (the camera eases over), snapping down steps instead of falling, and auto-sprint at full tilt (L3 still works). Values in `data/player/movement_default.tres` (Steps, `auto_sprint*`).
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

### 4.5 M14/P battle rifle

- Owner (2026-11-02): "a black polymer M14 style battle rifle, with a suppressor and stubby foregrip."
- Built *(Claude's reading)*: an M14 action in a one-piece black polymer stock with a pistol grip, after the M14A1 (which had a pistol-grip stock and a forward grip): open-top receiver with the bolt visible, op rod and charging handle on the right, rear aperture sight, ventilated upper handguard, front band, gas cylinder, a front sight post on the gas lock (the can covers the flash suppressor's), 20-round box magazine, steel butt plate, a stubby vertical grip on a short rail, and a suppressor. 7.62×51 ball (9.5 g, 850 m/s, 3.4 kJ), semi-auto, 20+1; heavy but controllable kick. Values in `data/weapons/m14p.tres`.

### 4.5a Glock 22 with a switch

Owner, 2026-11-12: a Glock with a dropped-in auto sear, chambered in .40 S&W, at a realistic but high fire rate. Full auto at 1,200 rpm (switched Glocks run about 1,100–1,300), a 22-round factory extended magazine (empty in about 1.1 s), 180 gr at 300 m/s. Hits harder per round than the Five-seveN but penetrates less; the muzzle climbs hard and walks sideways, so it's a close-range room-clearer. Unsuppressed, with its own synthesized shot (`raw_assets/audio/build_glock_sfx.py`). Tuning in `data/weapons/glock22.tres`; seventh slot on the wheel, after the MP5.

- Model, second version (owner, 2026-11-12: the first one "looked like a Roblox gun... a piece of polygon chunk"; asked for a faithful Glock at the Five-seveN's level of realism, same mechanics): `raw_assets/weapons/glock22/build.py` → `assets/weapons/glock22/`. A Glock 22 Gen 4 to Glock's published dimensions (slide 186.5 × 25.5 mm, 114 mm barrel, 165 mm sight radius, bore 10 mm under the slide top). The polymer frame is one signed-distance sculpt, so grip, dust cover, beavertail and trigger guard blend like a moulded part: three Gen 4 finger grooves, the backstrap hump, flared magazine well with the side cut-outs, squared trigger guard, single-slot rail, rough-texture (RTF) panels, the circle-G emblem. Steel parts are hard-surface: boxy slide with Gen 4 top and nose bevels, nine rear serrations, ejection port with the barrel hood, extractor, slide-stop notch, "GLOCK 22 Gen4 / AUSTRIA .40" and a serial; steel night sights (U-notch rear with two tritium dots, dot front post); safe-action trigger with its blade, slide stop, takedown tabs, pins, magazine catch; guide rod in the nose. The switch replaces the slide cover plate: a machined back plate with the sear block and a selector lever reaching out past the right side. The 22-round magazine sticks out 40 mm (witness holes, front rib, floor plate, a round on top for reloads). 12.4k triangles, 4K baked maps (2K on the phone). Grip on the Five-seveN's grip line so the shared pistol hands close on it; sight line 16.3 mm over the bore (`ads_eye_position` in `data/weapons/glock22.tres`).
- Why the Glock wasn't in the game (2026-11-12): its pull request went into `main`, but builds come from the repository's default branch (`ccr-9bb9a33f-fkn5sb`), so it never reached an APK. Merged into the default branch with the MP5; it is the seventh gun on the wheel.

### 4.6 MP5/SD-L submachine gun (built 2026-11-12)

- Owner (2026-11-12): "a very detailed mp5, with a red dot sight, suppressor, under barrel green laser. It must have great hipfire spread, really need to fill the niche of high mobility run and gun, contained hipfire, which is accurate to the green laser, even while moving, jumping, or walk running." First the baked model only, then (same day) "rig it up and make it functional in game with the strengths I detailed".
- Model *(Claude's reading)*: `raw_assets/weapons/mp5/build.py` → `assets/weapons/mp5/`. MP5A3 / Navy pattern: stamped receiver with the rounded top, ejection port with the bolt showing, cocking tube with its slot, hold-open notch and handle, drum rear sight and hooded front post, polymer trigger housing with ambidextrous selector and bullet pictograms, collapsed retractable stock, curved 30-round magazine. An enclosed red-dot sight on a receiver-top rail, a quick-detach suppressor, the LA-9G green laser on a rail under the handguard (pressure pad and cable), the MG42's vertical foregrip behind it. 21.7k triangles, 4K baked maps (2K on the phone). Arms `raw_assets/characters/fp_arms_mp5/build.py` (the Saiga hold, foregrip 50 mm further back). Synthesized sounds: a papery suppressed "thwup" with the roller-delayed bolt's "clack-chk" loud over it, short tail, HK slap on empty reloads.
- Handling *(Claude's reading of "run and gun")*: 9×19 at 400 m/s (8 g, 640 J, about two torso hits on a gunman), 800 rpm full auto, 30 + 1, handgun proficiency (submachine guns count as handguns). No carry penalty at all; draw 0.3 s, holster 0.16 s, to the sights in 0.14 s, 85 % speed aimed. Hip cone 0.45° standing, +0.2° walking, +0.35° in the air, bloom 0.05° a round up to 0.5°: moving or jumping it is tighter than any other gun's (tested). Light recoil (0.32° a round, fast spring). Values in `data/weapons/mp5.tres`.
- Run and gun: the trigger doesn't end a sprint (`sprint_fire`); the gun comes up out of the sprint pose while you fire and you keep sprint speed. Aiming still ends a sprint. Every other gun still drops the sprint to fire.
- Laser = where the rounds go: the rounds and the laser share one aim line (`PlayerWeapon.aim_forward()`). It follows 60 % of the gun's sway and pose turn (so the dot drifts a little when you whip the view round and settles), but not walk bob, landing or the viewmodel's recoil flip, so running and jumping don't move it. The dot is the centre of the shot cone at the hip and aimed; while it's on a surface the hip reticle is hidden. Tested: a jumping, strafing burst stays within half the cone of the dot; on a wall 28 m away while strafing and jumping every round landed within 0.4 m of it; a running gunman at 10 m dropped in 2 rounds. The beam is faint (a 5 mW laser), brightest near the gun; the dot is a green disc about 0.9° across. It swings with the gun during reloads and the sprint pose, and goes off while the gun is down (switching, the knife, an active part holding the hands).
- Red dot: aiming goes through the sight window (eye 13 cm behind the rear glass); its dot is coloured like every reticle (seaglass, crimson on an enemy, §4.7). The laser stays on aimed.
- Moving parts: bolt (cycles through the port), magazine (drops forward-down), stock (hidden aimed), cocking handle (stays back in its notch on an empty gun until the reload slaps it home).

### 4.7 Weapon wheel and reticles

- Owner (2026-11-02): "I need a weapon wheel for now so I can have both the shotgun and the rail carbine." **Y:** a tap goes back to the previous gun; holding it opens the wheel (time slows to 30 %, the right stick points at a gun, letting go draws it). Tuning in `data/input/weapon_wheel.tres`.
- Owner (2026-11-02): "the reticle for the shotgun should be a circle, with it being a dot when slugs are attached. The reticle is seaglass green-blue normally but turns crimson when over an enemy, for all weapons." Applies to the hip reticle of every gun, the Saiga's PSO scope reticle and the rail carbine's reflex ring. "Over an enemy" = the first thing along the line of sight is a live enemy (group `enemies`; the range dummies for now).

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
- Built (M1c, 2026-11-04): 17 zones on the triad enemy's bones (head, neck, chest, stomach, pelvis, upper arms, forearms, hands, thighs, shins, feet), multipliers in `data/enemies/*.tres`. Legs: stumble, then limp (one crippled), crawl (both, or one when badly hurt). Arms/hands: aim gets worse, weapon dropped (hand 80 %, forearm 50 %), and with low morale they surrender. Stomach/pelvis: doubled over for a few seconds. Head/neck: kill. Pass-through wounds bleed (damage over time, drips on the floor). Armour is physical: the Enforcer's carrier holds AR500 plates (`armor_plate` surface), so Ballistics decides what gets through (pistol and buck stop, the rail carbine doesn't); stopped rounds still bruise and stagger.
- Built: dismemberment at the Maximum gore setting (first pass M1c; rebuilt 2026-11-11, see §5.5): a cut at every joint, and the cut that goes is the one nearest where the round landed.

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
- Built (M1c): `src/gore/gore.gd` (autoload). Pools that grow under bodies once they settle, gibs that bleed and stain where they land. Wounds are painted by the enemy's shader in the mesh's rest pose (no decals): small dark entry holes, torn exit wounds, blood soaking into the cloth and running down. Ragdolls: `PhysicalBoneSimulator3D` with 12 bodies, impulse at the hit bone, frozen when settled (≤ 3 simulate). Hit reactions are procedural springs on the torso and head (not partial ragdoll) plus a stumble clip. Gore setting in the pause menu: Off, Standard (blood, wounds, pools), Maximum (adds dismemberment; default for now).
- **Blood as drops, rebuilt 2026-11-11.** Owner, after the first gore playtest: "the blood is very simple and not simulated accurately, rather obnoxious light red clouds." The billboard particle clouds are gone. Blood is now drops with real paths, stains where they land, and stains shaped by how they landed.
  - **In the air** (`src/gore/blood_drops.gd`, `src/gore/blood_drop.gdshader`). Every drop flies under gravity and air drag, and drag is stronger the smaller the drop: a fine spray stops within half a metre and sinks, while heavy drops arc across the room. The path has a closed form, so the GPU draws each drop from its launch state and the clock, and nothing is stepped per frame. Drops are lit (dark in a dark street, with a wet highlight under a lamp), round when slow and streaked along their motion when fast. They follow game time, so slow motion slows them. All of them are one draw call, ≤ 320 at once.
  - **What leaves a body.** Entry: a little fine back-spatter toward the shooter. Exit (the round went through): a cone of drops along the round, faster and heavier with the energy it left, plus one gout that carries on to whatever is behind and leaves the big stain there. Head shots throw drops up and out. A stump pumps in beats: a stream on each heartbeat (2.3 a second), weaker each time as the pressure falls, then drips; once the heart stops it fades in under a second. A destroyed head throws drops all round; a burst body throws three wide gouts and cones of drops that land on the walls and floor around it. Flying pieces trail drops for their first second and a half. A wounded man still moving drips; a crawling one leaves a smear behind him.
  - **On surfaces.** Drops that stain are traced against the level when they're launched (one ray per 70 ms of flight, ≤ 110 rays a frame; past that they fall to the floor found under the wound). Where one lands, the stain appears when it gets there, shaped by how it hit: square on, a round drop with a scalloped edge; at an angle, a long drop whose length is its width ÷ the sine of the impact angle, its tail pointing the way it was going (as in real bloodstain patterns). Gouts leave spatter stains: an impact stain, or a fan of drops when they hit at an angle. Big drops on a wall run down it over a few seconds. Stains start red and wet and dry dark and matte over half a minute, thin edges first. Shapes are an atlas of 16 (`assets/gore/splat_atlas.png` from `raw_assets/gore/build_blood_textures.py`; preview `docs/previews/blood_stains.png`): four impact stains, four forward spatters, round and long drops, runs, smears. The texture holds thickness, not colour; the shader colours it.
  - **Caps.** One MultiMesh: 48 large stains and 144 single drops and runs, the oldest fading out. Pools stay at 8.
  - **Tuning** on the phone: Pause → Tuning → Gore has *Blood amount* (× every count) and *Body toughness* (× every cut threshold). Both save on the phone and copy out with the other values.
  - **Evidence:** `tests/unit/test_blood_drops.gd` (the path matches a numerical integration of gravity and drag; fine drops stop where heavy ones carry; fall times) and `tests/scene/test_blood.gd` (no particle clouds left; a drop stains the floor where and when it lands; a drop thrown at a wall stains the wall at the height it got there; round vs long stains and the tail direction; a run down a wall; a rifle round through a man puts blood on the wall behind him; a stump bleeds in beats; slow motion slows the fall; caps; Off spills nothing). Captures: `docs/previews/blood_wall.png`, `docs/previews/blood_floor.png`, `docs/previews/gore_lineup_left.png` (a stump pumping a stream to the floor). Not checked in the cloud: how it reads at night on the phone, and frame time with a lot of blood in the air.
- **Dismemberment and gibbing, rebuilt 2026-11-11.** Owner: "I really want something of Soldier of Fortune, with decapitations, dismemberments, gibbing, but like based on ballistic impact and location and everything." Numbers are in `data/gore/gore_default.tres` (`GoreConfig`); the model is in `src/gore/dismemberment.gd`. Maximum only; Standard keeps wounds and blood; Off spawns nothing.
  - **Cuts at every joint**, pre-cut in the enemy glTF with flesh caps on both sides (`raw_assets/characters/triad/build.py`): the neck, 60 % down each upper arm, the forearms, the wrists, 65 % down each thigh (just above the knee), and below the knees. The jacket is fused to the flank and the trouser legs to each other higher up, so the arm and leg cuts can't go nearer the shoulder or hip. Cuts nest: an arm off at the upper arm takes the forearm and hand with it, and they fly as one piece.
  - **Location.** A hit acts on the cut nearest where it landed: full strength within 10 cm, nothing beyond 40 cm. A thigh hit near the knee takes the shin; one higher up takes the leg above the knee. A hit on the head itself acts on the head at full strength. A torso hit takes no limb; it counts toward bursting the body.
  - **Ballistic impact.** A hit's violence is the energy it left in the body plus 30 % of what it arrived with (a round going through still tears: the ballistics take only ~11 J per cm out of a rifle round in flesh, far less than the wound it makes), × 2.2 for blades and × 0.5 for blunt. One volley (a shot, or every pellet of a shell) past a cut's threshold severs it: hand 300 J, head 600, forearm 600, shin 750, upper arm 1,000, thigh 1,300. Hits of at least 20 % of a threshold add up, and the total severs at 1.25 × the threshold, so a few pistol rounds take a hand and sustained fire saws limbs off. Energy *left in* a piece past 2.6 × its threshold destroys it (chunks, no limb), so buckshot at arm's length pulps a forearm and a rail round through it cuts it off whole. A hit on the head past 800 J breaks it apart (skull cap, jaw, chunks); a neck hit takes it off whole. On the phone, Pause → Tuning → Gore → *Body toughness* scales every threshold.
  - **Retuned 2026-11-11 (second pass).** Owner, after playing the first pass: "they do cower or crawl away sometimes, but no heads, arms, or anything else is coming off." Measured by shooting every gun at every zone at 3 m and 8 m: with the first numbers only the rail carbine and the Gauss slug ever reached a cut. Now: a pistol round never takes anything with one round, but two or three take a hand, a forearm or a shin and four an arm; one shell of buckshot at 3 m takes a head, an arm or a leg, at 8 m a hand or a head; one M14, MG42 or rail round through a limb takes it, and one to the head takes the head. The Gauss slug is still the only round that bursts a man in one shot (a rail round into the torso carries ~8 kJ of violence, under the 12 kJ burst).
  - **Gibbing.** One volley of 12 kJ into the torso (the Gauss slug), or 8 kJ in total into a corpse (an MG42 burst on a body), bursts the whole body. The head and all four limbs fly off, some in pieces, along with ribs, a stretch of spine, the pelvis, organs, gut and meat (`assets/gore/gibs.gltf` from `raw_assets/gore/gibs/build.py`, vertex-coloured, 80–380 triangles each). Blood is thrown all round and lands on the walls and floor near him, and a pool spreads where he stood. Blasts tear limbs by how close each cut is to the centre and burst the body up close (the drone). Changed by this: at Maximum, a GX-4 slug into a torso bursts the man (and usually the one behind him) instead of leaving a corkscrewed, electrocuted corpse; the corkscrew and arcs still show on limb and head hits and at Standard.
  - **Reactions.** Losing a head kills. Losing a leg puts him on the ground crawling. Losing an arm makes him cower or run, and he drops the gun if it was the gun hand. Stumps pump blood in beats. Severed and burst pieces trail blood and stain where they land.
  - **Cost.** A body with anything cut off is one mesh (all the pieces merged; the shader hides the severed ones), so it costs one draw call however many pieces are gone. A gib in the air is one draw call. The gib pool went from 14 to 32. When it's full, cleared pieces are reused first, then small chunks, then limbs and heads; a chunk is skipped rather than push out a limb that landed less than 20 s ago. Gibs collide as boxes the size of the piece, centred on it, with friction, so they land and stay near where they fell. Before this, a severed limb's collision sat at the character's feet in the rest pose, so limbs rolled away or fell through the floor.
  - **Evidence:** `tests/scene/test_gore.gd` (20 tests: the cut nearest the hit goes, cuts nest, one mesh after a cut, one pistol round takes nothing but a few take the hand, a rifle round takes the arm it goes through and breaks a head, buckshot takes a head at 3 m and a leg at 2 m but not at 22 m, pistol fire saws a shin off a body, toughness ×3 keeps limbs on, the Gauss burst, a corpse under the MG42, blasts by distance, the gib cap, Off and Standard) and `tests/unit/test_ammo_data.gd` (the outcome rules). Captures (cloud, Mobile renderer on software Vulkan, `--demo=gore-lineup`): six men 1.5 m in front of a wall, each shot from 5 m with an ordinary gun: an M14 round through the upper arm, two MG42 rounds through the thigh, three pistol rounds into the hand, a shell of buckshot at the head from 3 m, an M14 round into the head, a Gauss slug into the chest. `docs/previews/gore_burst.png`, `gore_lineup_left.png`, `gore_lineup_close.png` (0.27 s after: pieces and blood in the air), `docs/previews/gore_lineup.png` (landed). Gib pieces: `docs/previews/gibs.png`. The overlay showed 197 draw calls for the whole test room with five dismembered bodies, a burst and its gibs in view (budget 150; gibs cast no shadows). Not measured on the phone: frame time with several bursts in view.

### 5.6 Enemy behavior

- Awareness from sight, sound (including suppressed shots at close range) and bodies they find.
- Near misses suppress them: worse accuracy, more time in cover.
- Morale drops with casualties and with seeing an augment up close. When it breaks they flee, freeze, surrender or fire blindly.
- Callouts that react to what you do ("Augment!", "Fall back!").
- Squads flank and suppress together. Only a few enemies shoot at the player at a time.
- Roles *(proposal)*: rifleman, shotgunner, shield carrier, machine gunner, marksman, launcher, anti-augment specialist (EMP grenades, armor-piercing rounds, drone jammer), officer.
- Owner (2026-11-03): the first enemies are **triad members**. Built (M1c) as three roles *(Claude's reading)*; since 2026-11-11 each man is dressed from his role's outfits (below):
  - **Gunman** (street clothes, Type 56 rifle): holds cover, peeks and fires bursts.
  - **Enforcer** (plate carrier over a hoodie or track top, pump shotgun): pushes in close and holds there.
  - **Red Pole** (printed shirts, leather, gold; SMG; the triad rank for an enforcer-lieutenant): steadies the men near him; when he dies everyone's morale drops.
- **Look, rebuilt 2026-11-11.** Owner: "The enemies are really hard to see and they lack a lot of detail, they also are quite small and don't stand out against the environment... They need tattoos. They also need clothes they can wear that are randomly selected from a bank." Built (`raw_assets/characters/triad/`, `src/ai/triad_look.gd`, `data/enemies/wardrobe/`, `data/enemies/outfits/`):
  - **A new body**: an athletic man without clothes (torso, arms and legs shaped muscle by muscle, a sculpted head, hands closed for a grip), with muscle definition, collarbones, abs and forearm veins baked into the normal map. Everything a man's clothes leave bare is this skin.
  - **A wardrobe bank of 24 items**, each modelled as a shell over the body (cut along its own hems, cuffs, necklines and armholes, loose where the cloth hangs, clear of the skin): singlet, T-shirt, short-sleeved camp shirt (buttoned or open over a singlet or bare chest), MA-1 bomber with rib knit, hoodie with a kangaroo pocket and the hood down, zipped track top with sleeve stripes, open leather jacket; cargo trousers with side pockets, jeans with a belt, track pants with stripes, cargo shorts, slacks; sneakers, boots; four haircuts (fade, slicked back with a knot, spiky, buzz) or bald; a cap or a beanie; sunglasses, a gold or silver chain, a watch.
  - **Outfits** decide what a role draws from: Gunmen wear *Street* (tees, hoodies, track tops, bombers, open shirts) or *Summer* (singlets, open shirts, shorts: more skin, more tattoos); Enforcers *Muscle* (hoodies, track tops, tees, bombers under the plate carrier; cargos, boots); the Red Pole *Boss* (printed camp shirts, open shirts over a singlet, leather jackets, slacks, more sunglasses and gold). Each man gets an outfit, a garment per slot, colours from each garment's list (many light and bright ones on purpose), sometimes a print (Hawaiian hibiscus, camo, check, cloud brocade), a skin tone, stubble or a goatee, and tattoos. Of 60 Gunmen, 57 wear a different set of clothes before colours are counted, 57 have tattoos and 24 wear a print (`tests/scene/test_wardrobe.gd`). Every value is a `.tres` (`Garment`, `Outfit`, `EnemyConfig.outfits`).
  - **Tattoos**: black-and-grey ink in three sets, each across the whole body: a dragon sleeve through clouds and wind bars, 忠義 down a forearm, a dragon on the back of a hand, the 洪 emblem on the chest; a koi sleeve in waves, tiger stripes round an upper arm and across the chest, 忠義仁勇 across the knuckles; tribal flames and barbed wire, 天地人 down the ribs, 兄弟 on a forearm; a character on the neck in each. Each man shows a random choice of sets and body regions (arms, chest, back, neck, hands), so no two men match, and only where his clothes leave skin. Sheet: `docs/previews/triad_tattoos.png`.
  - **Dismemberment still works the same** (§5.5): every garment is cut at the same joints as the body, so a severed arm flies off in its sleeve, a head with its hair, cap and sunglasses, a shin with its shoe. A man is one mesh and one draw call, before and after cuts (body and clothes merged per look, cached for repeat looks). Since 2026-11-12 the merge runs on a worker thread ahead of the spawn (`src/ai/triad_mesh_baker.gd`; the spawner picks each man's clothes a spawn or two early), together with the mesh after the first cut and the piece each first cut throws, and the merged meshes get LODs (about 12.5k → 6k → 3k → 1.4k triangles with distance, chosen by Godot at under 2 px of error). The LODs of the cut mesh are generated with the pieces pulled apart, so no simplified triangle joins two pieces that can come off.
  - **Readability**: 1.12 scale (about 1.96 m; was 1.08); a soft fill light from the viewer on the triad material so a man's front never drops to black in a dark street (`EnemyConfig.fill_light`, 0.45; the rim went from 0.8 to 1.0), on top of the distance rim; bright clothes. The material is two-sided so cloth folding over itself at the armpits shows its inside, not the skin behind; the skin under clothes is drawn a little further in (more under loose cloth, `Garment.inset`, only as far down the arms and legs as the clothes reach), and a layer under another (a tee under a leather jacket, hair under a cap) steps back too, so nothing shows through where joints bend. Cost: a dressed man is about 13k triangles (was about 10k), still one draw call. Captures: `docs/previews/triad_wardrobe*.png`, `triad_face.png`, `triad_chinatown.png`, `triad_poses.png`, `triad_split.png`, `gore_lineup*.png`.
- **Voices, 2026-11-11.** Owner: "I can't hear the actual voices of them in the game." Callouts had only been subtitles. Now every line is spoken (`assets/audio/voice/`, 46 lines in 16 situations × 6 voices), still with the subtitle: contact, reloading, man down, the Red Pole down, pinned by fire, lost him, push him (Enforcers), fleeing, a Red Pole yelling at runners to hold, surrendering, cowering, gut shot, legs gone, an arm gone, burning, grabbed by the mesh arm. Each man has his own voice and his own sound source at his head, so gunfire and impacts can't cut him off (they used to share 16 voices with every impact sound, which is why the dying screams were often lost too; those use his voice now). The squad still spaces callouts 2.2 s apart. Made with Kokoro-82M (Apache-2.0 text-to-speech run locally, `raw_assets/audio/build_callout_voices.py`), shaped into a shout (pitched up, presence lift, soft clipping, compression). Checked by transcribing every clip with Whisper: 275 of 276 come back as written (one "Red Pole" is heard as "red pools"). Lines are in English; Cantonese would need a Cantonese voice model, which isn't available in the session.
- Built: awareness from sight (field of view, distance, the player's speed), gunfire (suppressed guns heard at a quarter of the range) and seeing friends die; contact reports spread through the squad. Cover points are found automatically next to low cover; they hide, peek over it and fire, change spots. Only three shoot at the player at once (tokens). Near misses (rounds within 1.6 m) suppress: worse aim, longer in cover. Morale drops with wounds, casualties, gore and the augment within 5 m; it breaks into fleeing, cowering, blind fire over cover or surrendering (hands up, kneeling). First rounds of an engagement go wide on purpose. Callouts appear as subtitles. Enemies' rounds are real Ballistics rounds (tracers on every other one) that hit the player.


---

### 5.7 Movement feel (2026-11-11)

Owner (2026-11-11): movement "still feels a little bit jank"; it should be smooth and buttery, with a lot of control over the character, not limited to what a real human can do. What changed (`src/player/player.gd`, `MovementConfig.ground_step / air_step / gravity_scale`, values in `data/player/movement_default.tres` and on the phone under Pause → Tuning → Movement):

- **Camera between physics ticks.** Physics runs at 60 Hz. When the phone drops frames, the body moved in uneven steps per frame (one tick, then two). The camera is now drawn between the last two ticks, so it moves the same distance every frame. Only the player's camera does this: project-wide interpolation would touch gibs, ragdolls and teleports.
- **Turns keep their speed.** Speed and direction are handled separately. The stick swings the velocity round at 13 rad/s (a 90° turn takes about 0.12 s) instead of blending through a slower diagonal; the old blend lost about 30 % of a sprint through a 90° turn. Past 125° you plant and push off the other way.
- **Starts and stops ease out.** Speed closes on the target at a rate proportional to the gap (capped by the old acceleration), so there's no hard snap.
- **Momentum carries.** Speed above the current target (slide-hop, wall jump, dash, mantle at a run) bleeds at 7 m/s² while you keep pushing, instead of being braked away the moment you land (it was 55 m/s²). Let go of the stick to stop.
- **Air control.** The stick steers in the air without slowing you; pulling back brakes.
- **Jump arc.** Tap A for a short hop, hold for full height; a little hang at the top; falls a touch faster than it rises.
- **Sprint holds** while the stick is within 70° of forward (strafing at a run no longer drops it).
- **Slide:** press B just before landing to slide on touchdown; downhill pulls a slide along.
- **Wall-run entry** swings onto the wall over 0.12 s instead of snapping. **Mantles** keep 85 % of the speed you came in with and go faster at a run (a vault).
- **Curbs while landing:** stepping up a lip now works while coming down onto it, not only from the ground.
- **Camera:** a landing dip on a spring, eased crouch, a few degrees of field of view at a sprint and in a slide, and a slight lean into strafes.

Evidence in the cloud is indirect (`tests/unit/test_movement_config.gd`, `tests/scene/test_movement.gd`): no speed lost through a 90° turn, a slide-hop keeps most of its speed 0.3 s after landing, a tapped jump is lower than a held one, and at 40 fps the camera moves an even distance every frame while the body doesn't. Whether it feels better is the owner's call on the phone.

## 6. Art direction

Decided: see "Visuals" in §2. No anime or cel shading.

- **Enemy readability** (owner, 2026-11-05: "they come across as pretty small on the screen... they need to be more clearly standing out against the environment. Think of Halo CE"). Built: enemies at 1.08 scale (~1.89 m); a cool rim light on the body that grows with distance (far men outline against dark streets, near ones look natural) and fades when they die; lighter role colours (charcoal/blue-grey Gunman, olive Enforcer, crimson Red Pole). Values in `data/enemies/*.tres` (`body_scale`, `rim_color`, `rim_strength`).
  2026-11-11 (owner: still "really hard to see", "quite small"): 1.12 scale, a fill light from the viewer (`fill_light`), and clothes from a wardrobe with many bright colours, prints and tattoos instead of one dark jacket per role (§5.6).
- **Owner on the look** (2026-11-05): the weapons are detailed and look good; the environment has "an eerie PS2 / early-2000s PC" vibe with the black sky. That vibe is acceptable if the game runs well and the gameplay carries, but more polish and a more cohesive style are welcome, never at the cost of frame rate. First step: a lit night sky instead of black (§7.1).

*(proposal)*

- Detail goes first to the first-person arms, weapons and augment hardware, since they're always on screen. Then hit effects and gore, then lighting, then enemies, then environments.
- Baked lighting with a few dynamic lights. Height fog, dust, smoke, sparks, emissive lights, color grading.
- Effects built from meshes with scrolling textures, not huge particle counts.
- Heavy, worn, industrial hardware. Explore palettes with test renders in M4.

## 7. Maps

### 7.1 Chinatown docks (owner, 2026-11-04)

A self-contained city block on the harbour at night, roughly the size of a Black Ops 1 map (about 92 × 66 m of play space). The owner asked for atmosphere, charm and a sense of place, with environment detail on par with the weapons.

**Layout** (south to north; Blender plan in `raw_assets/levels/chinatown/build.py`):

- **Water and pier.** A timber pier with pilings and a steel fishing boat moored alongside (wheelhouse, mast lights, net drum, tyres over the side); a gangplank lets you board. Across the bay: a lit skyline and dark hills.
- **Quay.** Bollards, fenders, crate and styrofoam stacks, drums, a forklift, shipping containers (climbable stack) and a gantry crane over the water.
- **South row.** The Pier 3 cold store (enterable through roll-up doors on both sides and a side door), the open-sided fish market hall (stall rows with fish on ice under red lamps, live-seafood tanks, a cold room with strip curtains), a loading road with a box truck, and a tiled tenement with a first-floor gallery reached by steel stairs from the quay.
- **Harbour Street.** Sunken road, sidewalks, lantern strings across the street, street lamps, parked vans, signboards and vertical lightboxes in Traditional Chinese with English, 3D neon (龍鳳, 冰室, 麻雀, 宵夜, OPEN), a paifang gate (天下為公) at the west end with the road closed beyond it, plywood hoarding at the east end.
- **North row.** Hotel and pawnshop, herbal shop, the Sea View restaurant (enterable: dining room with round tables, roast-meat window, fish tanks, kitchen with woks, back door), bakery, noodle shop, a narrow alley to the back, grocery with mahjong club above, gold shop, pharmacy, barber.
- **Back alley.** Dumpsters, bags, gas cylinders, AC units, kitchen extractors with steam, fire escapes, laundry strung between buildings.

Three loops connect it all: quay ↔ west alley or market ↔ street; street ↔ restaurant ↔ back alley ↔ alley ↔ street; cold store doors between quay and street. Low cover everywhere (stalls, crates, vans, barriers); height at the gallery and the container stack.

**Enemies** arrive on a rolling clock (`RollingSpawner`, `data/levels/chinatown_spawns.tres`): 8 at the start, and whenever fewer than 4 are still fighting (dead, surrendered and crawling men don't count) 3 more come in. Each one appears at one of 20 spawn points (doorways, alley ends, the boat, the cold room, behind the containers...) that the player's camera can't see at chest or head height, at least 14 m away, preferably behind the player. They know roughly where the player is and close in. Dying restarts the round.

**Look.** Rainy night. Lighting is baked in Cycles into one 4096² lightmap (lamps, lanterns, neon, lit windows, a low moon, a light-polluted sky); real-time lights only touch characters and guns. Wet surfaces get darker and glossier, puddles ripple, rain stops under roofs, steam rises from drains and vents, reflection probes give the wet street its sheen (Mobile renderer), the harbour water shows streaks of the quay lights. Ambient sound: rain, water against the quay, a distant ship's horn, neon hum, an extractor fan, a radio in the restaurant.

**Performance (2026-11-05).** The owner measured 28–29 fps here on the Moto G (the range was smooth). Changes: a pre-rendered sky panorama instead of a TIME-driven sky shader (which rebuilt radiance every frame); the map re-cut into 12 m cells (`split_cells.py`) with wall occluders, so culling and LODs work; cheaper water, world, steam shaders; bloom without its half-resolution level; adaptive resolution. Pause → Map cost test measures what each effect costs on the phone.

**Pipeline.** Materials are a tileable texture array (`raw_assets/env/materials`, `raw_assets/env/atlases`); the map is one generator (`build.py`, with `props.py` and `buildings.py`) and one bake/export step (`bake.py`). Everything rebuilds from scratch.
