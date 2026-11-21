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
  - Built (2026-11-05) as **RX-9 Reflex Overclock** (nervous system; a neural co-processor at the base of the skull overclocks perception and motor control). World at 24 % (was 30 %; owner, 2026-11-13: "slow it down just slightly more for them"), the operative still at 65 % (moving, shooting, reloading); looking stays real time. 8 s of charge, refills at 0.45/s after 2 s, needs 1.5 s to start. Colour drains, a cool vignette, everything muffled and pitched down (your own gun less), FOV +3°, ragdoll/limb/flinch impulses ×1.8. Charge bar above the health bar. Values in `data/body/parts/rx9_reflex_overclock.tres`. Not yet: knocking living enemies into a ragdoll.

- **Three actives on one button** (owner, 2026-11-07): "there's going to be basically 3 active augmentations that you can use at one time, but they're all activated by the same button, LB." **D-pad left / down / right** selects slot 1 / 2 / 3; **LB** toggles the selected part. A part keeps running when you select another (RX-9 can stay on while you raise the arm cannon); select it again and press LB to stop it. The HUD rows above the health bar show each part's D-pad arrow and charge, the selected one bright and tagged LB. RB is free. The Saiga's shell type moved to **D-pad up**. Loadout: RX-9 on D-pad left, GX-4 on D-pad down, right empty.
  - 2026-11-10: with nine actives (ten from 2026-11-13, eleven from 2026-11-14), the D-pad directions follow **the order the actives were installed in** (first = left, second = down, third = right; `BodyLoadout.slot_of`). A fourth pushes out the first. On the loadout screen, A on an installed active moves it to the next direction.
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
- The blast (`src/weapons/explosion.gd`): 6.5 m radius, 300 damage at the centre falling off to the edge, line of sight required, bodies thrown, limbs off close in at Maximum gore; it hurts the operative too. Since 2026-11-14 it looks like the grenades' bursts (fireball, smoke, dust ring, scorch: §4.8).
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

**Cloud captures:** `-- --demo=active:<part id>` with `--act=lash|grab|throw|fly|boom|arc|ram|deadeye|mark|volley|impact` (`src/core/debug/actives_demo.gd`; the setae's `--hold` is milliseconds of real time after the release).

### 3.4c SX-8 Urticating Setae (built 2026-11-13)

Owner (2026-11-13): "a nanotech augmentation... a series of vents on the side of the arm, little holes that are normally empty. When you activate the ability the guy brings his arm forward, and out of those holes these long but very thin razor-sharp hairs, nanite hairs, grow out. It slows down time a lot, like a dead eye, and you can select any of the targets in the area, up to 4 or 5... you mark them. When you hit the fire button time resumes and you throw those hairs. They become razor sharp and hard in the air and leave devastating cavitation wounds, pretty much wiping out most enemies they hit in a brutal fashion... like the hairs of a tarantula, but with nanotechnology. Finally our AoE."

- **Hardware.** A setae bank grafted along the back of the left forearm: a machined housing with three staggered rows of eight ceramic-collared ports (24), each over a nanite assembler; two feed lines back into the elbow sleeve; gill plates either side that lift to vent assembler heat. The hand spreads into a hooked claw when it deploys. Each port extrudes two fibres (48), hair-thin and still soft as they grow (they sway and curl), stiffened into needles by a phase change in flight. Model: `raw_assets/augments/actives/sx8_urticating_setae/build.py` (18.3k triangles, deploy clip 0.5 s; `port_00`..`port_23` mark the bores); on the body: a bank on the back of the left forearm (`body_hardware.py`).
- **Deploy (LB, 0.45 s).** The gun goes down (it takes the left hand), the arm comes up and forward, the fibres grow out from the elbow end toward the hand in a ripple (each over 0.42 s), and the world slows to ×0.06 (the operative moves at ×0.3; looking stays real time): colour drained to 18 %, sound muffled under a slow heartbeat, an amber vignette, the view narrows 5°.
- **Marking (LT).** LT marks the body part under the crosshair (head, neck, chest, gut, pelvis, a limb), or the nearest head, chest or gut to the crosshair within 3.5° (wider up close). The HUD brackets what LT would mark with its name, puts a numbered amber diamond on each mark, chains them in order with a dashed line, counts MARKS n / 4 and burns down the marking time. One man can take several marks. Each mark lights a share of the fibres, which stiffen and lean toward the targets. **4 marks; 5 with perception ×1.20 (OB-5, TG-6).** Marking time 5 s × processing ÷ 1.20 (3–8 s); when it runs out it throws at what's marked, or folds if nothing is.
- **The throw (RT).** The arm draws back and in (0.16 s) and whips across to the right; 0.03 s into the sweep the fibres leave the ports with an amber flash, and time comes back over 0.5 s. The needles (amber streaks, never thinner than about two pixels) fan out to the right of the sweep, then turn and home on their marks at 150 m/s × √(usable strength ÷ 1.15). LB while marking folds it without spending the throw. RT with nothing marked throws at whatever is under the crosshair.
- **The wound.** Each mark gets a bundle of the 48 needles. The first three to land are punctures of their own (18 damage, 260 J). 40 ms after the first, the cavity opens: one hit of 340 damage carrying 11 kJ × usable strength ÷ 1.15, ballistic, through and through (`AugHit`), so the locational damage and the Maximum-gore model (§5.5) decide what happens: a head mark destroys the head, a limb mark takes the limb off, a torso mark bursts the body (about 12.6 kJ of violence against the 12 kJ gib threshold for the Operator; a lighter body, e.g. FT-1, still kills but leaves the torso in one piece). Blood mists forward and back out of the cavity. A short hit-stop and rumble on the first cavity. Nearly half the needles go on through and stick in the wall behind (lit amber, cooling over 2.5 s, gone after 9 s; at most 96).
- **Cost.** One throw stored; the fibres regrow in about 12 s × spare power ÷ 250 W (0.5–1.6×). 4 kJ of heat per throw; 80 W and 220 W of heat while it's out. Needs **processing ×1.15** (SA-2), so it runs on the Operator. It's the left forearm: not with the NT-5 mesh arm or the BW-6 shield; with the GX-4 in the right.
- **With RX-9.** When the throw gives time back it returns to RX-9's slowdown if RX-9 is running, not to full speed.
- **Sounds** (`raw_assets/audio/build_setae_sfx.py`, 13 files, synthesized): the assemblers' fizz as the fibres grow, a tick and lock tone per mark (a step higher each), the dead-eye heartbeat loop, the windup, the throw (a crack and a swarm of supersonic zips), wet punctures, and the cavity's deep burst.
- Code: `src/augments/active/setae/` (`Setae`, `SetaeData`); tuning in `data/body/parts/sx8_urticating_setae.tres`. Tests: `tests/scene/test_setae.gd`.

### 3.4d LC-6 Lorentz Catcher (built 2026-11-14)

Owner (2026-11-13): "an augment where you have to hold down LB and it collects [the bullets fired at you], and then either when you let go or the timer runs out it releases a cloud of them in a large area of effect where you are aiming. It can only shoot as many back as it picked up." The reference was a giant-robot shooter's catch-and-return hand; this is our own hardware for the same idea.

- **The physics (no magic).** Rounds are copper-jacketed lead. A strong, fast-changing magnetic field drags on any conductor moving through it (eddy currents; the drag is the Lorentz force on the currents it induces), so a pulsed field can brake a round to a stop and hold it, and the same coils run as a coilgun can throw it back. Braking turns the round's energy into heat in the coils.
- **Hardware.** Eight coil petals on a drive ring behind the left wrist. Folded, they lie back along the forearm like a slatted sleeve. Each petal is a satin graft slat with a pack of seven flat copper turns, a lit strip on its inner face, a gunmetal tip shoe and a hinge knuckle; a power conduit runs from the ring back along the inner forearm. Model: `raw_assets/augments/actives/lc6_lorentz_catcher/build.py` (26.3k triangles, deploy clip 0.4 s; `focus` marks the middle of the field, 0.36 m in front of the palm); on the body: the ring and the folded petals on the left forearm (`body_hardware.py`). Previews: `docs/previews/lc6_lorentz_catcher_hero.png`, `_body.png`, `_ingame.png`.
- **Hold LB (0.35 s to deploy).** This is the one active that is held, not toggled (owner's call for this part). The gun goes down (it takes the left hand), the arm comes up, the petals swing forward one after another, overshoot and lock flared round the open hand, and a faint lens of field shimmers in front of it. You move at 82 %.
- **Catching.** A sphere of 1.25 m radius, 0.9 m in front of the eye and a little low, takes every enemy round that flies into it from within 75° of the view (`BulletCatcher`, checked by `Ballistics` on each step of a round's flight, before it can reach anything behind the field); rounds that reach the body from the front under the field are caught too (`Player.hit_interceptors`). Rounds from behind or the side get through. A caught round stops where it was caught on screen, drifts into a slowly turning cloud in front of the palm, glowing orange from the eddy heating and cooling while it's held, nose toward you in a slow tumble. Each catch: a ripple in the field, a fizz and a tick, a light rumble. The HUD counts **CAUGHT n / max**, shows the hold time and the body's heat, and draws the area the release would cover at the crosshair (amber, with "n IN AREA" when bodies are inside it).
- **Release.** Let go of LB, or the hold time runs out (6 s), or the body overheats: the cloud pulls in and the rounds turn down range, the hand punches forward (0.09 s), and every round goes back out in a 0.14 s ripple, each at 92 % of the speed it was caught at, as a hot streak. They spread evenly over a disc of 3 m radius at the aim point (held between 3° and 16° of the view, so it stays wide close in and doesn't vanish far out); 30 % × perception of them go for the bodies inside the disc instead (random body parts). Damage, penetration, gore and ragdolls are the rounds' own (a Type 56 round is a Type 56 round). **Exactly as many go out as came in**; nothing caught, nothing thrown: it just folds. A ring of coil snaps, a magnetic thump, a crack and a swarm of supersonic cracks; a camera kick, a 6° field-of-view punch and a heavy rumble.
- **Stats.** Needs **500 W of cooling** (HS-5, so the Operator; or HP-4 with OC-2): each catch puts 35 % of the round's energy into the body as heat (a rifle round about 0.7 kJ; the store is 30 kJ), and at full heat it lets go of everything at once. **Power supply** sets how many it holds: 40 at the base 450 W, 58 with a PC-3. The **power reserve** pays to throw them (0.4 J per joule they carry out); short of it they leave slower (√ of the shortfall, never below 35 % speed). **Perception** sends more of the spread onto bodies. 6 s of hold, refilled at 0.75/s after 1.5 s; 1.5 s needed to start; 120 W and 200 W of heat while it's up.
- **Left arm.** Not with the NT-5 mesh arm, the BW-6 shield or the SX-8 setae; with the GX-4 or the whip in the right. Installed on the Operator it goes on D-pad right.
- **Sounds** (`raw_assets/audio/build_catcher_sfx.py`, 12 files, synthesized): deploy (servo, eight petal clacks, a rising whine into the hum), the field's hum (loop), four catches, full, release, three returning-round cracks, stow.
- Code: `src/augments/active/catcher/` (`LorentzCatcher`, `LorentzCatcherData`), `src/weapons/bullet_catcher.gd`, the catch step and glowing rounds in `src/weapons/ballistics.gd`; tuning in `data/body/parts/lc6_lorentz_catcher.tres` (generated from `tools/parts/gen_parts.py`; behaviour tuning defaults in `lorentz_catcher_data.gd`). Tests: `tests/scene/test_catcher.gd`. Cloud captures: `-- --demo=active:lc6_lorentz_catcher --act=catch|full|release`.

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
- **Slide hit** = 6.5 m/s × mass/100 × usable strength × impact × slide speed. Since 2026-11-14 (owner) it does no damage: it launches the man, up 4.6 m/s and along 4 m/s × √(hit ÷ 6.5), between ×0.75 and ×1.6 (§5.7). The Operator throws a man about 1.2 m up; the Juggernaut a little higher. The ram charge (KR-5) still uses the old rule: damage grows with the square of the hit, 16 m/s or more breaks the body.
- **R3 strike:** 400 (one cut kills an unaugmented man; owner 2026-11-14) × melee power × usable strength damage; the shove is 7 m/s × mass/100 × usable strength × impact; 17 m/s or more is lethal; recovery 0.5 s ÷ melee speed. A short lunge, hit-stop, rumble, blood. Values in `data/player/melee_default.tres`. Played as a knife slash (2026-11-12): the gun drops away, the right hand comes in from the lower right with the KB-1 combat knife, cocks high right, cuts down-left through the target at the moment of the hit (windup 0.15 s; the whole slash 0.66 s, slowed 2026-11-14 so it reads on the phone) and follows through, with a trail along the edge that runs red after a cut; then the gun comes back. Keyframed in camera space in the same .tres (`knife_*`), model from `raw_assets/weapons/knife/build.py`; preview `docs/previews/knife_slash.png`. Blood builds up on the blade (owner 2026-11-14): each cut adds 0.12 and each kill 0.2 of a full coat, spreading from the tip to the guard; it never comes off, and fresh blood dries dark over 45 s (`blood_*`).
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

**Presets** (`data/body/presets/`, on the loadout screen; 2026-11-10: three more built round the new actives: **Reaper** (whip + fan shield + ram thrusters + ram plating), **Handler** (Shrike drone + arc projector + RX-9 on the uplink, power cell and fuel bladder), **Wraith** (thermoptic shroud + mesh arm, quiet dampers, extra cooling)): **Operator** (the default: TL-3, SA-2, EM-2, HS-5, RX-9, GX-4), **Ghost** (silent and quick; no Gauss arm), **Juggernaut** (CT-7, TN-9, HM-5, DL-1, GX-4: heavy hip fire, slides that throw men high; no slow motion, no wall-running), **Marksman** (NL-3 + MR-1 feed the FC-1 and OB-5; light carbon frame, GX-4).

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

**Loadout screen** (View button; Pause → Body status). Rebuilt 2026-11-11 (owner: "set it up as a menu where all the options are laid out and you can just click on the one you want... if it tells you, oh, you need this, you can just go look and click on it"): every part is a tile on one screen: the presets, the eleven actives (orange; installed ones show their D-pad arrow), then the passives row by row under their body location (installed: teal with +; installed but offline: red). The D-pad or a tap moves the cursor, and the model and every number preview the part under it. **A** (or a second tap, or the button under the card) installs it, or takes it out if it's in, or applies a preset. **X** moves an installed active to the next D-pad direction. When the selected part needs a stat it doesn't have, the card lists every part that supplies it (with its location, tappable), those tiles get an amber outline, and **RB** jumps to the one that fixes it on its own (else the strongest). With nothing selected that needs anything, RB goes to the fix for whichever installed part is offline. The screen opens on an offline part if there is one, and the HUD's OFFLINE line names the fix too ("needs processing ×1.15+ (fit SA-2 or TG-6; View)"). **LB** switches to the Colours page (§3.7), **Y** helmet, **LT** zoom, the right stick turns the model, **B** closes and puts the loadout on the player (saved to `user://loadout.cfg`). The card shows mass, power, heat, capacity, what installing it would take out, every effect coloured by whether it helps, requirements met or not (with the current value) and how the part combines with others.

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
  - Slide (owner, 2026-11-07: "longer", plus "a moderate knockback if you slide into an enemy", later dependent on mass and strength parts): a tap of B slides until the speed runs out; B again, A (slide-hop) or pulling the stick back ends it. Owner, 2026-11-14: shorter (it was about 18 m and felt like an arena shooter), and the hit launches instead of hurting; see §5.7 "Slide, 2026-11-14". Values in `data/player/movement_default.tres` (Slide, Slide knockback, Slide launch).
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
- **SPAS-12:** built 2026-11-20 as a pump gun, stock folded (§4.11).

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

### 4.8 M32A1 MGL grenade launcher (built 2026-11-14, Claude's choice)

The owner (2026-11-14) asked Claude to find something missing and add it: a weapon, an augment or a presentation change, in one pass. *(Claude's reading: proposal.)* Every gun on the wheel fired straight-line bullets, and the only blast in the game was the Shrike drone's, drawn as a handful of tiny particles. Nothing arced, nothing reached a man behind cover, and nothing did area damage from the gun slot. The triad AI hides behind low cover and peeks, so the gun that answers cover is a grenade launcher.

- **The gun** (`raw_assets/weapons/m32/build.py` → `assets/weapons/m32/`, 26.9k triangles, 2K baked maps): an M32A1-pattern six-shot revolver for 40×46 mm low-velocity rounds. Olive-grey cerakote frame, hard-anodised black cylinder (six 40.6 mm chambers on a 46 mm pitch circle, fluted between them, ratchet star, stop notches), recoil shield over the case heads, a 300 mm rifled barrel in a quad-rail handguard with vent slots, a collapsed skeletal stock on a buffer tube. The grip and the clamp-on foregrip sit exactly where the MG42's do, so the MG42's first-person arms hold it. Fire control: the **FCS-40** sight (a tall reflex sight with a round window, a range drum, a laser rangefinder pod with emitter and receiver lenses under its nose) and a cable along the handguard to an **inductive fuze setter** ring at the muzzle, which programs each round's burst range as it leaves (real airburst 40 mm systems work this way). Previews: `docs/previews/m32_*.png`, `m32_open_*.png` (cylinder out).
- **The round** (`data/weapons/ammo/grenade_40mm_hedp.tres`, `GrenadeData`): 230 g at 76 m/s (660 J), quadratic drag (k = 0.001/m gives about 410 m maximum range at 42°, like the real M433). Fired level from the hip it hits the ground about 40 m out: you aim it in an arc. Spins in flight (`assets/weapons/m32/grenade_40mm.gltf`: olive body, yellow band, copper rotating band, fuze nose). World time, so RX-9 slows it.
- **The fuze.** It arms after **9 m** of flight (the real M433 arms at 14-27 m, shortened for the maps' ranges). Inside that it's a dud: a 230 g lump that hits a man like a thrown brick (blunt, about 60 damage, a shove) and bounces off the world, skids, lies there and is cleared after 9 s. Armed, it bursts on contact: on a body exactly where it touched him.
- **Airburst (aim with LT).** Aimed, the rangefinder lases the point under the sight. After 0.12 s the fire control has a solution: the round is launched on the arc that passes through that point (0.35 m over it for a surface, so it clears the cover you aimed at) and its fuze is set to burst **1.5 m past it**. Aim at the top edge of the wall a man is hiding behind, and it bursts over him. Aim at a man and it's an impact burst on him. The HUD readout beside the sight: `RNG 14.2 m`, then `LASING`, `AIRBURST +1.5 m`, `IMPACT` (a body), or `SAFE < 9 m` (inside the arming distance), `NO RETURN` (nothing lased).
- **At the hip** a broken ring shows the spread, and a **diamond marks where the round will land**, with the distance (`SAFE` and grey when it'd still be unarmed there). The prediction steps the same flight model through the world every other tick.
- **The burst** (`Explosion.grenade`):
  - Blast: 3.4 m radius, 260 damage at the centre falling off to the edge, through the chest hitbox, with a line-of-sight check. At Maximum gore within about 1.2 m it bursts the body, out to about 2.3 m it takes limbs (the drone's rules, `GoreConfig.blast_*`).
  - Fragments, simulated per body instead of as a few hundred rays: each live man within 22 m gets the share of 620 fragments his projected area (0.7 m²) covers on the sphere at his distance, drawn as a Poisson count (about 8.6 at 2 m, 1.4 at 5 m, 0.25 at 12 m; at most 8). Each fragment is a real `Ballistics` round (0.4 g at 1,500 m/s, heavy drag) fired from the burst at a random zone, weighted by that zone's size. A wall, a car or another man in the way stops it. It wounds the zone it reaches, so a leg hit makes him limp and an arm hit ruins his aim. Its near misses suppress. Fourteen more fly off at random for pockmarks and sparks on the walls and floor. The operative's share is worked out the same way and comes straight off his health, along with 45 % of the blast.
  - Feel: camera shake that fades out by 26 m; a heavy rumble; within 7 m, stunned hearing (everything muffled, easing back over 2.6 s) and a ringing in the ears; a flash of light; sparks and debris.
- **How a blast looks** (`src/vfx/explosion_fx.gd`, `explosion.gdshader`, `scorch.gdshader`; the Shrike's warhead now uses it too). A white-hot flash swells in 0.04 s into a lumpy fireball that cools through yellow and orange to soot and breaks apart. Three smoke lobes rise and swell for about three seconds, glowing from inside at first. A ring of dust is thrown out along the surface it burst on. A scorch is burnt into that surface, a ragged soot star with embers glowing in it for the first seconds; an airburst near the ground leaves a fainter one. Everything is GPU-animated meshes on a game-time clock: one MultiMesh for every puff of every live blast (one draw call, ≤ 40), one for the scorches (≤ 10). They are opaque with a noise dissolve: no blended billboards, no overdraw sorting, and no "light clouds".
- **The cylinder.** It turns 60° a shot (a 0.07 s index you can see). X opens the crane and the cylinder swings out to the right, 82° about a hinge under it. The gun rolls left in the reload pose so you see it, and the spent aluminium cases tumble out. Then one round goes in every 0.42 s, each case head appearing in its chamber. When it's full the cylinder swings shut and the clockwork spring ratchets as it winds. RT with at least one round in shuts it and fires. Sprinting or switching stops the reload, and what went in stays. A full reload takes 3.3 s (scaled by the body's reload speed). The case heads show in every loaded or spent chamber (`round_0`..`round_5`).
- **Tuning on the phone:** Pause → Tuning shows a Launcher section for it (arming distance, airburst offset, blast radius and damage, fragments, fireball size), saved with the gun; the bullet Ballistics sliders are hidden for it.
- **Handling:** heavy-weapon proficiency; 0.42 s between shots (double action); 4.4° of kick with a slow spring; carries at 90 % speed; 0.26 s to the sights (FOV ×0.72). The sight line is 90 mm over the bore (`ads_eye_position`). Tuning: `data/weapons/m32.tres`, `data/weapons/ammo/grenade_40mm_hedp.tres`, `data/player/viewmodel_m32.tres`.
- **Sounds** (`raw_assets/audio/build_m32_sfx.py`, 19 files, synthesized): the "thoonk" (hammer fall, low pop, the barrel ringing like a pipe, gas hiss, the cylinder indexing), a short tail, the crane latch and swing-out, cases rattling out, rounds seating, the slam shut and spring ratchet, dry fire; the burst (crack, boom, sub-bass, fragments zinging, grit and stones raining down), a far version with street echoes, the ear ring, a dud's tonk off concrete and its thud into a body.
- **Eighth gun on the wheel** (hold Y).

### 4.9 The Governor and the SL-9 Slagger (owner, 2026-11-18)

Two guns that came with map 2 (§7.2).

**The Governor** (`raw_assets/weapons/governor/build.py` → `assets/weapons/governor/`, 6.7k triangles, 2K baked maps). Owner: "a tactical black polymer full size 45-70 lever action rifle ... intense sound, harsh recoil, devastating ballistic impact, and the satisfying haptic and audio clunk of the lever being drawn."

- **The gun:** a modern big-bore "tactical lever": flat-sided receiver in black nitride with a top rail and a ghost-ring rear sight, an exposed hammer, a big loop lever round the trigger, a side loading gate on the right, a full-length tube magazine under a 470 mm barrel, an M-LOK polymer fore-end with a stubby vertical grip, a ported brake, a straight polymer stock with a cheek riser and a thick recoil pad. About 0.97 m long. The pistol grip and the stubby grip are exactly where the M14/P's are, so the M14/P's first-person arms hold it. A front post with a tritium dot.
- **The round:** .45-70 Government, 26 g (405 gr) at 610 m/s, about 4.8 kJ: a man hit in the trunk dies, and is thrown (`ragdoll_push` 2.3: bodies fly further than from any rifle). A limb hit at Maximum gore takes the limb off; a head hit destroys the head. A man it hits and doesn't kill is shoved off his line (`stagger_push`). Hard-cast and heavy, it goes through drywall partitions (the hotel's corridor walls are drywall) and through a man into the next.
- **The lever** (WeaponData "Lever action", `PlayerWeapon._update_lever`). 0.16 s after the shot (the recoil settles) the lever is thrown: down fast, a short dwell at the bottom, back up hard and home with a snap, 0.42 s in all. Through it the bolt runs back, the gun cants (it rolls and lifts about the grip), and at the bottom the empty case flies out and the hammer is cocked. Each end of the stroke has its own sound and rumble: **"lever open"** (an unlock click, the bolt rasping back over the carrier, the hammer ratchet) and **"lever close"** (the bolt slamming home, the lever latching: a heavy two-part chunk-clack, both motors of the controller hard for 0.1 s). 0.6 s between shots.
- **Loading:** six in the tube, one in the chamber (7). X loads one round at a time through the gate on the right (0.38 s each; the gun rolls to show the gate and a cartridge slides in each time). RT with a round in stops loading and fires; if it went in empty, the lever is worked to chamber.
- **Feel:** 6.5° of kick with a slow camera spring, a 15° muzzle flip in the hands, the strongest fire rumble in the game (both motors full, 0.2 s), a huge brake flash and smoke. Sound (`raw_assets/audio/build_governor_sfx.py`): the subsonic-ish round has a small crack, so what hits you is the blast: a hard transient, a wide boom, the brake's ports slapping back, a sub drop; a long dark tail with marble-and-glass slap-back.
- Tuning: `data/weapons/governor.tres`, `data/player/viewmodel_governor.tres`. Rifle proficiency. Survival: from wave 3.

**The SL-9 Slagger** (`raw_assets/weapons/slagger/build.py` → `assets/weapons/slagger/`, 2K baked maps), the first energy weapon. Owner: "a small pistol, it needs an almost makeshift or industrial look, a hybrid of a pistol frame and some kind of industrial welder. It requires charge before firing ... angry orange almost stellar looking red orange plasma at the tip, barely contained by a magnetic field, which is released after you let go of the trigger, 2.75 seconds is a full charge and is devastating ... immense visual recoil on the gun itself, even with high player character strength ... setting them on fire and causing agony and panic with grazing hits, burning holes right through them with direct hits to body trunk, and blowing off limbs and leaving burning charred chunks."

- **The gun:** a polymer pistol frame on the Five-seveN's grip line (the shared pistol hands hold it) with the slide gone; bolted on top, the guts of a plasma cutter in a chipped safety-yellow housing: welded seams, cooling fins with vent slits, a capacitor can, a pressure gauge, "HIGH VOLTAGE" stencilled on it, a braided feed hose looping to the front. Out front, a scorched torch nozzle inside three copper containment coils on standoff rods and an open emitter cup. The grip is wrapped in friction tape; the power cell is the magazine (8 shots).
- **Charge** (`PlasmaData`, `data/weapons/ammo/plasma_bolt.tres`). Hold RT: a ball of plasma gathers in front of the cup (`src/vfx/plasma_charge.gd`, `plasma.gdshader`): white-yellow at the core, angry red-orange at the limb, churning like the face of a star, with broken bands of the magnetic field crawling round it (`plasma_field.gdshader`). It grows with the charge (slow to start, surging toward the end), lights your hands, spits sparks, and the coils and vents glow brighter and whiter. The gun trembles harder and the controller rumbles harder as it fills. 2.75 s is a full charge. Let go to fire. Let go before 12 % and the field collapses with a pop (no shot). Hold at full for 3 s more and the field strains (the bands break up and race, the throb gets louder) then fails: no shot, steam and sparks in your hands, 1.4 s before it charges again. Charging stops a sprint.
- **The bolt** (`src/weapons/plasma_bolts.gd`): a glowing mass that you can watch fly (34 m/s small, 58 m/s full), trailing sparks and lighting the room it passes through, with a slight droop. Size, damage and burn all scale with the charge.
  - **A graze** (it passes within 0.2–0.55 m of a man): he catches fire and goes mad with it: he drops his gun (often), runs blind, lurching one way then another, clawing at himself, screaming, for 6 s. The fire burns 9–24 damage a second for about 5 s.
  - **A square hit to the trunk** at 50 % charge or more **burns a hole clean through him**: you can see through the hole (the enemy shader draws nothing in a tunnel along the bolt's path), its rim charred, embers glowing and cooling over 7 s, cooked pieces and a thin half-boiled spray blown out of his back. The bolt goes on with 60 % of its charge, into the man behind. Below 50 % it stops in him, burning.
  - **A limb** at 35 % or more comes off cauterised (no bleeding stump, a puff of smoke), burning where it lands; at 88 % or more (or a head from 30 %) it's burned to charred, glowing chunks, the first two still on fire.
  - **A surface:** a molten splash (a fireball and scorch above 45 % charge), fire left burning there, and everyone within 1.7 m (at full) catches fire and panics as from a graze.
- **Recoil:** at full charge the gun is thrown up 30° in the hands, rolled 9° and pushed back 12 cm, with 7.5° of camera kick and both motors full; a small shot kicks 30 % of that.
- **Sound** (`raw_assets/audio/build_slagger_sfx.py`): the charge (capacitors whining up, the arc crackling harder, a magnetic hum swelling), the full-charge throb, the shot (an electric crack, a deep whumph, a tearing hiss), the fizzle, the overload, the impact roar and the sizzle when it hits a man.
- Tuning: `data/weapons/slagger.tres`, `data/weapons/ammo/plasma_bolt.tres`. Handgun proficiency. Survival: from wave 4.
- Code: `src/weapons/grenade_data.gd` (`GrenadeData`: flight, launch solution, fragment numbers), `src/weapons/grenades.gd` (the `Grenades` autoload: rounds in flight, fuzes, duds), `src/weapons/explosion.gd` (blast, fragments, feel), `PlayerWeapon` (launch, fire control, landing prediction, cylinder), `GunMechanism` (single-round reload), `ViewmodelRig` (crane, cylinder, case heads), `hud.gd` (landing marker, FCS readout), `Player.add_shake`, `Sfx.concuss`.
- **Evidence:** `tests/unit/test_grenade_data.gd` (12: muzzle energy, ~410 m maximum range, a level shot lands at about 40 m, the launch solution passes within 0.15 m of targets from 14 to 110 m, fragment counts and energy with distance, Poisson means, zone weights, single-round reload, a trigger pull shuts it and fires, a sprint keeps what went in, the tuning menu reaches the launcher values). `tests/scene/test_m32.gd` (10, in the test room: a round bursts on a man and kills him; at 5 m it's a dud that hurts but doesn't kill; fragments don't get through a concrete wall but wound a man in the open; aimed at the top of a wall, it bursts past the wall and kills the man behind it; the cylinder turns 60° a shot; reload swings it out, drops the spent cases and fills every chamber; the hip marker is within 0.8 m of where the round bursts; a burst draws fireball, smoke, dust and a scorch). In-game captures (Mobile renderer, the cloud's software Vulkan; `-- --demo=grenade`, `src/core/debug/grenade_demo.gd`, with Godot's `--fixed-fps 60`): `docs/previews/m32_ingame.png` (aimed with the readout, the burst from the gun, the reload, the hip marker), `m32_ingame_blast.png` (the airburst over a wall side-on, 67 ms to 1.2 s), `m32_ingame_ads.png`, `m32_ingame_hip.png`.
- Not checked in the cloud: how the fireball and smoke read at night on the phone, and frame time with several bursts in view (the puff shader costs a little per pixel while a fireball fills the screen). The arming distance, the 1.5 m airburst offset and the fragment numbers are first guesses for the owner to tune by feel.

### 4.10 Steyr AUG A1 assault rifle (owner, 2026-11-20)

Owner: "I think there's an automatic rifle, like an assault rifle niche that needs filled. So I want a really awesome AUG model. It's super realistic. If you need to look at reference pictures and superimpose them, do that. I want a very realistic Steyr AUG."

- **Model** (`raw_assets/weapons/aug/build.py` → `assets/weapons/aug/`, 4K baked maps): the AUG A1 in the Austrian Army's StG 77 pattern, traced from a public-domain side photo of a real StG 77 (Wikimedia Commons, MoserB). Every outline in the script is in that photo's pixels at 4.82 px/mm (790 mm overall); `--overlay` renders an orthographic left view on top of the photo, and the two line up to a millimetre or two along the whole gun (`docs/previews/aug_overlay.png`). Olive polymer stock sculpted as one piece (signed distance field: the traced outline extruded with a width that changes along the gun and rounded on every edge), the trigger guard that takes the whole gloved hand, the big trigger, crossbolt safety, takedown button, magazine catch behind the well, ejection port open on the right with the bolt behind it and the cover strip on the left, butt plate seam, sling swivels. Black-painted aluminium receiver with its lightening slots and the cocking-handle slot (guide rod visible), the folding cocking handle, the cast carry handle with the 1.5x scope on it (hex adjuster caps, the "H" mark, recessed lenses). Ribbed barrel, gas block with the regulator, three-prong flash hider on its nut, the hinged vertical foregrip.
- **The clear magazine:** 30 rounds of 5.56 mm in a double stack inside a see-through amber shell. The rounds you've fired disappear from the bottom of the stack and the follower rides up the magazine's curve under the last one (`mag_rounds.gdshader`, `ViewmodelRig.set_mag_rounds`); a new magazine comes up full.
- **Handling:** 5.56×45 at 940 m/s (4 g, 1.77 kJ: between the MP5's 9 mm and the M14/P's 7.62), 680 rpm, 30 + 1, rifle proficiency. **Progressive trigger**, like the real AUG's: squeeze RT part way for single shots, pull it through (past 85 % travel) for automatic. Light, straight-back recoil (a bullpup pushes into the shoulder; 0.75° a round). Slightly heavy (96 % speed). Aiming always goes through the **integral 1.5x scope**: the view zooms 1.5x and, near full aim, the HUD's scope view replaces the gun with the StG 77's **circle reticle** (aim point in its centre; coloured like every reticle, §4.7). Bullpup reload: the gun rolls to show the well behind the grip, the magazine drops out along its own lean; on an empty gun the cocking handle is pulled back and let go.
- **Sound** (`raw_assets/audio/build_aug_sfx.py`): a sharp, high 5.56 crack-bang, the piston and carrier running on their rods close to your cheek, a long slapping tail; hollow plastic magazine knocks with the rounds shifting inside, the handle pulled and the carrier slamming home.
- Tuning: `data/weapons/aug.tres`, `data/player/viewmodel_aug.tres`. Arms: `raw_assets/characters/fp_arms_aug/build.py`. Survival: from wave 2 (tags precision, mobility).
- **Numbers:** the gun 12.2k triangles plus the shell (1.5k) and the rounds (1.8k), 4K baked maps (2K on the phone); arms 2K maps.
- **Evidence:** `tests/scene/test_aug.gd` (6 tests: calibre, energy, rate and capacity; full pull automatic, light pull single then squeezed through to automatic; the scope at 1.5x with the viewmodel stepping aside; the clear magazine at 25 after five shots with the follower moved up and 30 after a reload; an empty reload works the handle), `tests/unit/test_weapon_assets.gd` (parts and budget). Captures with `-- --demo=aug:<hip|burst|raise|scope|reload|handle>` (`src/core/debug/aug_demo.gd`): `docs/previews/aug_ingame.png`. The photo match: `docs/previews/aug_overlay.png`.

### 4.11 Franchi SPAS-12, pump only (owner, 2026-11-20)

Owner: "Just the way you found the picture and made that AUG model ... do the same thing for the SPAS 12. Our version of the SPAS 12 is going to have the stock folded up and be iconic ... it needs to be one-to-one with the actual SPAS 12 ... Compared to the Saiga, it needs to be slower firing ... we're going to be exclusively using it pump. And after every shot, almost like the old Doom games, I want the character to kind of raise the barrel and do the pump before putting it back down ... more damage and a little more range ... a slightly tighter spread of pellets with the buckshot and a smaller reticule that's a circle but the same shape ... It also needs a boom." (This is the "Later: SPAS-12" of §4.3.)

- **Model** (`raw_assets/weapons/spas12/build.py` → `assets/weapons/spas12/`, 17.9k triangles, 4K baked maps): the standard SPAS-12 with the 21.5" barrel and the folding stock **folded over the top, hook up**. Traced from a left-side studio photo of exactly that (Rama, Wikimedia Commons, CC BY-SA 3.0 FR), turned 0.52° so the bore is level, at 4.44 px/mm (810 mm folded, the factory figure; it gives a 20 mm barrel and a 25.4 mm tube, as on the real gun). The stock, its holes and the hook were measured from the pixels, not by eye, and the whole gun was checked by rendering an orthographic left view over the photo and colouring the difference (`--overlay`; `docs/previews/spas12_overlay.png`): the silhouettes agree to a few millimetres along the whole gun. Black anodised receiver (Franchi markings on the left, ejection port with the bolt and its handle on the right, loading port and shell lifter underneath, bolt release), the grey perforated heat shield over the barrel that runs back over the action, the big ribbed polymer pump (sculpted: six short grooves in front, eight that wrap round the hand, the selector hole), the knurled thread protector and tall front sight, the 8-round tube with its knurled nut and sling flange, the bare-aluminium trigger group with the lever safety, the sculpted polymer grip and stock housing with its six grooves, and the stamped-steel stock folded on top: two side plates with four lightening holes and a pressed rib, the pivot hubs, the butt plate standing up at the front and the arm hook arching over it.
- **Pump only** (WeaponData "Pump action", `PlayerWeapon._update_pump`). 0.08 s after the shot the gun comes up, muzzle high (24°, rolled toward you, about the grip), the left hand yanks the pump back (a beat at the rear: the hull flies out of the port, red), slams it home, and the gun settles back down: 0.62 s in all, 0.74 s between shots (the Saiga: 0.16 s). The left arm is its own node in the arms model (`support_arm`) and rides the pump all the way. Two sounds and two rumbles: **"pump back"** (unlock, the bars rasping back, the hard stop, the hull bouncing on the floor) and **"pump forward"** (the shell stripped off the carrier, the bolt slamming home: a heavy "CHUNK-chak", both motors full).
- **Against the Saiga's 00 buck:** 9 pellets at 440 m/s (400), 0.16 damage per joule (0.14): about 490 damage a shell against 350 (+38 %); drag 0.0040 (0.0045) and 190 m maximum range (160); pattern 2.6° (3.4°) and hip spread 1.25° (1.6°), so the **ring is about 23 % smaller**, the same circle-and-dot shape. Buck only (no shell types). Heavier: 94 % speed, 93 % turn.
- **Aiming:** the folded stock sits over the sights, so LT shoulders the gun (the view tightens to 0.84, the gun comes in and up) and the **ring stays** on screen, shrunk to the aimed spread (`reticle_when_aimed`).
- **Loading:** eight in the tube and one chambered. X loads a shell at a time through the loading port under the receiver (0.4 s each; the gun rolls to show the port and a shell goes in); RT with a shell in stops loading and fires; if it went in empty, the pump is worked to chamber one.
- **Sound** (`raw_assets/audio/build_spas12_sfx.py`), stereo and built the way a sound designer layers a shotgun: the snap (N-wave and a hard click), a broad blast that differs left and right, a mid "bark" (what a phone speaker actually plays), a 170 → 52 Hz chest punch saturated for harmonics, the boom (a 68 → 26 Hz sub sweep and a body under 260 Hz, squeezed on its own band so it is dense without holding the rest down), the receiver's steel shudder and early reflections, through a look-ahead limiter. A 3.6 s rolling tail with darker slap-backs. Measured through a simulated phone speaker (high-pass 300 Hz) it is about as loud as the Governor's shot in its first 150 ms, with far more of its energy above 500 Hz.
- Tuning: `data/weapons/spas12.tres`, `data/player/viewmodel_spas12.tres`, the Tuning screen's Pump section. Arms: `raw_assets/characters/fp_arms_spas12/build.py`. Survival: from wave 2 (tags close, heavy).
- **Evidence:** `tests/scene/test_spas12.gd` (8+1 pump; slower, harder, further and tighter than the Saiga; the ring smaller and kept when aimed; a shot raises the gun, racks the pump back with the hand on it and brings it home; no second shot mid-pump; a shell at a time to 9 and the pump worked after an empty reload; a shell to the chest at 10 m kills), `tests/unit/test_weapon_assets.gd` (parts, 810 mm, budget, the support arm). Captures with `-- --demo=spas12:<hip|fire|raise|rack|aim|reload>` (`src/core/debug/spas12_demo.gd`): `docs/previews/spas12_ingame.png`.

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
  - **The moment of impact, 2026-11-13.** Owner: "more visual feedback the moment a round hits an enemy... a solid little wound... without that pattern"; "clearly (in slowed time) the round clearly entering, exiting, throwing a blood splatter that's reasonably sized but brutal into a nearby object or surface"; Brutal Doom and Soldier of Fortune, but restrained, and cheap.
    - **Wounds** (`src/ai/triad.gdshader`) are solid shapes with no noise: a black hole, a hard rim (dark and bruised on an entry, raw red on an exit, which tears into a few smooth lobes), a smooth soak that spreads for 3 s and a run below. They pop slightly bigger for a tenth of a second as they open. Drawn bigger than life so a hit reads on a 720p phone: entry radius 1.1–2.4 cm, exit 2–5 cm (`Enemy.on_part_hit`).
    - **Impact bursts** (`src/gore/impact_bursts.gd`, `impact_burst.gdshader`): the thick sheet of blood thrown out of the wound in the first fraction of a second, which drops alone can't show. Entry: a small burst back toward the shooter (0.11 s). Exit: a fan of jets along the round that shoot out, break into drops and are gone (about 0.2 s; 0.22–0.6 m with the energy it carried). Lit and opaque like the drops, never a cloud. Game time, so in RX-9 slow motion you see the jets grow; at full speed it's a sharp spurt. One draw call, ≤ 24 at once.
    - **More out of the exit**: more and faster drops, a few dark bits of tissue (heavier, lumpy, they leave their own marks), and a bigger gout stain on the wall behind (0.38–0.95 m). Drops are drawn 1.5× their size and never under about 2 px, so a spray reads at fighting distance; stains keep the real size.
    - **Wall spatter** (`raw_assets/gore/build_blood_textures.py`, rows 0–1): impact stains are a heavy uneven mass with dark clots, a crown of thick spines with beads at their ends and medium drops round it; forward spatters a heavy mass with thick streaks and tear-shaped drops fanning out.
    - **Round wakes in slow motion** (`src/vfx/round_wakes.gd`, `round_wake.gdshader`): while the RX-9 has the world slowed, each of the operative's rounds leaves a thin pale wake with a hot point at the round (the overclocked eye catching the shock-disturbed air). Depth-tested, so it disappears into a body and shows again where the round comes out; it fades 0.3 s of game time after the round stops. One draw call, ≤ 16.
    - **Bug fixed on the way**: every bullet-impact particle (concrete dust, chalk, sparks, splinters, glass) was drawn about a metre wide, because a billboard particle material drops the particle's scale unless `billboard_keep_scale` is set (`Fx._particle_material`). That was the big pale puff on walls in every capture; it hid the blood behind a man. Now they are their real 2–9 cm, which also cuts overdraw.
    - **Captures**: `docs/previews/impact_slowmo_side.png` (RX-9 slow motion, side-on, frames after the shot), `impact_slowmo_player.png` (the same from beside the gun), `impact_normal_player.png` (full speed), `impact_wall_spatter.png` (the wall behind him afterwards), `impact_before_side.png` (the same shot before this pass). Made with `-- --demo=impact` and Godot's `--fixed-fps 60` (`src/core/debug/impact_demo.gd`).
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
- **Look, 2026-11-17: whole men made with Tripo3D** (§5.6b). The procedural body and wardrobe below are still in the game but every role now wears a Tripo man first (`Outfit.body_chance` 1.0).
- **Look, rebuilt 2026-11-11.** Owner: "The enemies are really hard to see and they lack a lot of detail, they also are quite small and don't stand out against the environment... They need tattoos. They also need clothes they can wear that are randomly selected from a bank." Built (`raw_assets/characters/triad/`, `src/ai/triad_look.gd`, `data/enemies/wardrobe/`, `data/enemies/outfits/`):
  - **A new body**: an athletic man without clothes (torso, arms and legs shaped muscle by muscle, a sculpted head, hands closed for a grip), with muscle definition, collarbones, abs and forearm veins baked into the normal map. Everything a man's clothes leave bare is this skin.
  - **A wardrobe bank of 24 items**, each modelled as a shell over the body (cut along its own hems, cuffs, necklines and armholes, loose where the cloth hangs, clear of the skin): singlet, T-shirt, short-sleeved camp shirt (buttoned or open over a singlet or bare chest), MA-1 bomber with rib knit, hoodie with a kangaroo pocket and the hood down, zipped track top with sleeve stripes, open leather jacket; cargo trousers with side pockets, jeans with a belt, track pants with stripes, cargo shorts, slacks; sneakers, boots; four haircuts (fade, slicked back with a knot, spiky, buzz) or bald; a cap or a beanie; sunglasses, a gold or silver chain, a watch.
  - **Outfits** decide what a role draws from: Gunmen wear *Street* (tees, hoodies, track tops, bombers, open shirts) or *Summer* (singlets, open shirts, shorts: more skin, more tattoos); Enforcers *Muscle* (hoodies, track tops, tees, bombers under the plate carrier; cargos, boots); the Red Pole *Boss* (printed camp shirts, open shirts over a singlet, leather jackets, slacks, more sunglasses and gold). Each man gets an outfit, a garment per slot, colours from each garment's list (many light and bright ones on purpose), sometimes a print (Hawaiian hibiscus, camo, check, cloud brocade), a skin tone, stubble or a goatee, and tattoos. Of 60 Gunmen, 57 wear a different set of clothes before colours are counted, 57 have tattoos and 24 wear a print (`tests/scene/test_wardrobe.gd`). Every value is a `.tres` (`Garment`, `Outfit`, `EnemyConfig.outfits`).
  - **Tattoos**: black-and-grey ink in three sets, each across the whole body: a dragon sleeve through clouds and wind bars, 忠義 down a forearm, a dragon on the back of a hand, the 洪 emblem on the chest; a koi sleeve in waves, tiger stripes round an upper arm and across the chest, 忠義仁勇 across the knuckles; tribal flames and barbed wire, 天地人 down the ribs, 兄弟 on a forearm; a character on the neck in each. Each man shows a random choice of sets and body regions (arms, chest, back, neck, hands), so no two men match, and only where his clothes leave skin. Sheet: `docs/previews/triad_tattoos.png`.
  - **Dismemberment still works the same** (§5.5): every garment is cut at the same joints as the body, so a severed arm flies off in its sleeve, a head with its hair, cap and sunglasses, a shin with its shoe. A man is one mesh and one draw call, before and after cuts (body and clothes merged per look, cached for repeat looks). Since 2026-11-12 the merge runs on a worker thread ahead of the spawn (`src/ai/triad_mesh_baker.gd`; the spawner picks each man's clothes a spawn or two early), together with the mesh after the first cut and the piece each first cut throws, and the merged meshes get LODs (about 12.5k → 6k → 3k → 1.4k triangles with distance, chosen by Godot at under 2 px of error). The LODs of the cut mesh are generated with the pieces pulled apart, so no simplified triangle joins two pieces that can come off.
  - **Readability**: 1.12 scale (about 1.96 m; was 1.08); a soft fill light from the viewer on the triad material so a man's front never drops to black in a dark street (`EnemyConfig.fill_light`, 0.45; the rim went from 0.8 to 1.0), on top of the distance rim; bright clothes. The material is two-sided so cloth folding over itself at the armpits shows its inside, not the skin behind; the skin under clothes is drawn a little further in (more under loose cloth, `Garment.inset`, only as far down the arms and legs as the clothes reach), and a layer under another (a tee under a leather jacket, hair under a cap) steps back too, so nothing shows through where joints bend. Cost: a dressed man is about 13k triangles (was about 10k), still one draw call. Captures: `docs/previews/triad_wardrobe*.png`, `triad_face.png`, `triad_chinatown.png`, `triad_poses.png`, `triad_split.png`, `gore_lineup*.png`.
- **Voices, 2026-11-11.** Owner: "I can't hear the actual voices of them in the game." Callouts had only been subtitles. Now every line is spoken (`assets/audio/voice/`, 46 lines in 16 situations × 6 voices; 55 in 19 since 2026-11-16, §5.6a), still with the subtitle: contact, reloading, man down, the Red Pole down, pinned by fire, lost him, push him (Enforcers), fleeing, a Red Pole yelling at runners to hold, surrendering, cowering, gut shot, legs gone, an arm gone, burning, grabbed by the mesh arm. Each man has his own voice and his own sound source at his head, so gunfire and impacts can't cut him off (they used to share 16 voices with every impact sound, which is why the dying screams were often lost too; those use his voice now). The squad still spaces callouts 2.2 s apart. Made with Kokoro-82M (Apache-2.0 text-to-speech run locally, `raw_assets/audio/build_callout_voices.py`), shaped into a shout (pitched up, presence lift, soft clipping, compression). Checked by transcribing every clip with Whisper: 275 of 276 come back as written (one "Red Pole" is heard as "red pools"). Lines are in English; Cantonese would need a Cantonese voice model, which isn't available in the session.
- Built: awareness from sight (field of view, distance, the player's speed), gunfire (suppressed guns heard at a quarter of the range) and seeing friends die; contact reports spread through the squad. Cover points are found automatically next to low cover; they hide, peek over it and fire, change spots. Only three shoot at the player at once (tokens). Near misses (rounds within 1.6 m) suppress: worse aim, longer in cover. Morale drops with wounds, casualties, gore and the augment within 5 m; it breaks into fleeing, cowering, blind fire over cover or surrendering (hands up, kneeling). First rounds of an engagement go wide on purpose. Callouts appear as subtitles. Enemies' rounds are real Ballistics rounds (tracers on every other one) that hit the player.


### 5.6b The cast, made with Tripo3D (2026-11-17)

Owner, 2026-11-17: "look for models that you're not impressed by or don't fit the narrative or vision... remake them in Tripo... one attempted generation per asset... if you're doing a person... I want them to have the skeleton and be animated." Claude's pass over every model: the guns, the map and the augment hardware hold up; the people didn't. The triad men's metaball bodies and mannequin faces were the weakest thing in the game and the most seen, and the Incense Master's face is on screen through his entrance and his execution. The first-person arms are the other weak model (metaball fingers); left for later because a Tripo arm needs finger rigging and a grip pose per gun (six of them), on hands Tripo tends to fuse.

- **Twelve men, one try each** (`raw_assets/characters/triad_tripo/tripo_generate.py`, prompts and task records in `<id>/tripo/`): a concept image (seedream v5, front view, T-pose, light grey background) then image-to-model (v3.1, detailed geometry and PBR textures). Photographic, Hong Kong Chinese, bright clothes so they read at night, tattoos in the texture. Ten concepts in the first round, nine modelled: `gun_track` (a royal blue tracksuit) came out as a European man and was dropped rather than generated twice. Three more men in a second round (the recruits and an older gunman).

| Body | Role (outfit) | Look |
|---|---|---|
| `gun_bomber` | Gunman (Street) | red satin MA-1 over a white tee, black jeans, white sneakers, neck dragon |
| `gun_hoodie` | Gunman (Street) | mustard hoodie, olive cargos, tan work boots, slicked hair, moustache |
| `gun_older` | Gunman (Street) | fifties, grey crew cut, olive work jacket over a striped polo, brown slacks |
| `sum_hawaii` | Gunman (Summer) | bleached spiky hair, open hibiscus shirt over a tattooed chest, cargo shorts |
| `sum_singlet` | Gunman (Summer) | shaved head, white singlet, full koi and wave sleeves, jeans |
| `lantern_denim` | Blue Lantern (Lantern) | teenager, light blue denim jacket over a white hoodie, a blue lantern charm |
| `lantern_sport` | Blue Lantern (Lantern) | teenager, bowl cut, sky blue windbreaker, grey sweats, slides with socks |
| `enf_hoodie` | Enforcer (Muscle) | black plate carrier with magazine pouches over a grey hoodie, cargos, boots, fingerless gloves |
| `enf_track` | Enforcer (Muscle) | olive plate carrier over a red track top, striped track pants, scarred, bald |
| `hatchet` | Hatchet Man (Hatchet, also Summer and Street) | red headband, open black waistcoat over a tattooed bare torso, kung fu trousers, wrapped fists |
| `red_pole` | Red Pole (Boss) | greying slicked hair, open black leather jacket over a crimson dragon-print silk shirt, gold |
| `incense_master` | the Incense Master | huge, bald, sleeveless black leather vest over a tattooed chest and belly, leather trousers, gold buckle (the Gauss arm and pendant are still `hardware.gltf`, §8.7a) |

- **The rig is ours** (`raw_assets/characters/triad_tripo/build.py`, about a minute a man): no Tripo rig. Tripo's mesh (about 1.9M triangles) is merged and collapsed to 12k, stood up facing the triad's front and scaled to the rig's shoulder height; his joints are found from the mesh (the arm line, the wrist as the narrowest part of the forearm, leg and torso slices at the rig's heights); a source armature on those joints gets Blender's automatic (bone heat) weights, is posed onto the triad rig's rest A-pose (limbs stretched a few per cent, head and hands keep their size) and applied. The mesh then fits the triad skeleton exactly, so **every triad clip plays on him**: the rifle stances, walk and run, cover, the chop and vault, the boss's moves, the kneel and the execution; hands land on the same grips, the damage zones and cut planes line up.
- **Dismemberment** works as before (§5.5): he's cut at the triad's joints with flesh caps (fused trouser legs are split down the middle line first); a severed part is a piece of the same mesh. The hatchet man's left forearm comes off with his hand (his wrapped fists close no wrist ring).
- **In the game** a Tripo man is a whole-body `Garment` (`whole_body`, `data/enemies/bodies/tp_<id>.tres`; `own_vest` hides the enforcer's separate vest mesh), listed in `Outfit.bodies`; `TriadLook.pick` puts one on with `body_chance` and nothing else. `EnemyBody` loads his glTF (`assets/characters/triad_tripo/<id>/`) the first time and gives his material his own maps (2K colour, 1K normal and ORM; Tripo gives no AO), with the tint, tattoo and beard maps off. Everything else is unchanged: one mesh and one draw call, wounds, char, the merge on a worker thread, LODs. The wardrobe bank stays for any outfit without bodies (or with `body_chance` under 1).
- **Costs.** Credits 2026-11-17: 13 concept images × 5 (gun_track's included) + 12 models × 60 = 785 of the account's 810. About 12k triangles a man (the wardrobe man was about 13k); his far LOD stops at about a quarter (3k) where the wardrobe man's reached about a ninth: Tripo's cloth folds are noisier. VRAM: about 6 MB per body compressed.
- **Variety** is now eleven fixed men rather than the bank's mixes: five gunman looks, two recruits, two enforcers, the hatchet man on top of his share of the gunmen's, the Red Pole and the boss. Twins in one wave will happen; more men are one generation each.
- **Previews**: `docs/previews/tripo_sheet.jpg` (all twelve fitted to the rig: front, three-quarter, side; one each in `tripo_<id>.jpg`), `tripo_before_after.jpg`, `tripo_cast.png` and `tripo_cast_close.jpg` (the lineup in the game, `-- --demo=wardrobe --wardrobe-bodies`), `tripo_boss.jpg` (the boss demo: Gauss arm, pound, kneel, execution).
- **Known**: hands are flat (the triad rig has one bone for the fingers), so a grip closes as a block; the hoodie enforcer's severed right thigh flies without its two flesh caps; the source GLBs are reduced masters (`<id>/master.glb`, 60k triangles, 2K maps), Tripo's downloads aren't committed.
- Tests: `tests/scene/test_tripo_bodies.gd`.

### 5.6a The hunt: they come to you, and they work together (2026-11-16)

Owner, 2026-11-16: "They need to come to me. It's unacceptable in a wave shooter that I'm having to walk around an empty map to try to find one last enemy to kill. When there is one more enemy, I need them marked like with an arrow. Once they realize where I'm at, they're coordinating together and they need to pin me down and kill me... working together and trying."

Why it happened: a man who lost the operative walked to where he'd last been, then stood down to idle after six seconds and stayed there; and 8 of the docks' 20 spawn points were on navmesh islands with no path out (three tenement stairwells, the moored boat, the cold room, the first-floor gallery, the west barrier), so a man who arrived there could never reach you.

Built (`src/ai/squad.gd`, `src/ai/enemy.gd`, `src/ai/hunt_config.gd`, tuning in `data/enemies/hunt.tres`). Every squad in a wave mode hunts (Survival, Sandbox on the docks, the test range waves); the range targets and demos don't:
- **Lookouts.** When nobody in the squad has had eyes on you for 5 s, the lookouts phone in where you are (give or take 7 m) and every man still fighting heads there, running when it's more than 10 m off. With two or fewer left it's every 2 s and within 2 m: the last men always come straight for you. Nobody stands down to idle any more; a man who reaches the spot and doesn't find you searches round the latest tip.
- **Contact is shared.** Whoever has eyes on you calls it, so the rest know where to aim and where to go.
- **Pin and flank.** While someone has seen you in the last 4 s, the squad hands out roles every second: up to 2 **pinners** (the men with eyes on you) hold cover, peek longer and, when you duck, keep firing at where you went for 3.5 s ("Covering fire!") so the rounds crack round your cover; up to 2 **flankers** (never more than half the gunmen; never the Red Pole) run for a spot 95° round from the pinners' line at 11 m, cover there if any ("Flank him!"), then fight from there; everyone else **pushes**: after 5 s in one piece of cover he moves up to cover at least 4 m nearer ("Move up!"). Enforcers keep rushing you; Hatchet Men keep their own flanking (§8.8a).
- **Cornered.** With two or fewer left, a man who ran or froze turns back after 5 s instead of hiding until his nerve comes back.
- **Stuck.** A hunter who gets nowhere for 6 s (caught on something, or thrown by the mesh arm onto the boat) is moved to a spawn point you can't see, and only when you can't see him either.
- **Spawn points.** When the docks' navmesh is baked, each spawn point with no path to the player start moves to the nearest ground that has one (all eight were within 6 m: the stairwells' are 0.7 m out on the pavement; the boat's are on the quay beside it). The map itself still has those islands (no gangway onto the boat, no stair to the gallery); fix them when the map is next rebuilt.
- **The last hostile is marked.** When a wave is down to its last man (`mark_when_left`, 1), the wave counter reads LAST HOSTILE and he's marked: a red chevron over his head with the distance (through walls), or a red arrow at the screen edge pointing at him when he's off screen or behind you. Sandbox's rolling spawns never have a last man, so no marker there.
- **Voices.** Three new callouts in all six voices: flank, covering fire, hunting ("Spread out, find him!").

Capture: `docs/previews/hunt_marker.png` (top: the last man behind you to the left, the edge arrow; bottom: ahead behind the counters, the marker). Tests: `tests/scene/test_squad_hunt.gd`.


---

### 5.7 Movement feel (2026-11-11)

Owner (2026-11-11): movement "still feels a little bit jank"; it should be smooth and buttery, with a lot of control over the character, not limited to what a real human can do. What changed (`src/player/player.gd`, `MovementConfig.ground_step / air_step / gravity_scale`, values in `data/player/movement_default.tres` and on the phone under Pause → Tuning → Movement):

- **Camera between physics ticks.** Physics runs at 60 Hz. When the phone drops frames, the body moved in uneven steps per frame (one tick, then two). The camera is now drawn between the last two ticks, so it moves the same distance every frame. Only the player's camera does this: project-wide interpolation would touch gibs, ragdolls and teleports.
- **Turns keep their speed** (replaced 2026-11-17, §5.7a: turns now plant and cost a little speed). Speed and direction are handled separately. The stick swings the velocity round at 13 rad/s (a 90° turn takes about 0.12 s) instead of blending through a slower diagonal; the old blend lost about 30 % of a sprint through a 90° turn. Past 125° you plant and push off the other way.
- **Starts and stops ease out.** Speed closes on the target at a rate proportional to the gap (capped by the old acceleration), so there's no hard snap.
- **Momentum carries.** Speed above the current target (slide-hop, wall jump, dash, mantle at a run) bleeds at 7 m/s² while you keep pushing, instead of being braked away the moment you land (it was 55 m/s²). Let go of the stick to stop.
- **Air control.** The stick steers in the air without slowing you; pulling back brakes.
- **Jump arc.** Tap A for a short hop, hold for full height; a little hang at the top; falls a touch faster than it rises.
- **Sprint holds** while the stick is within 70° of forward (strafing at a run no longer drops it).
- **Slide:** press B just before landing to slide on touchdown; downhill pulls a slide along.
- **Wall-run entry** swings onto the wall over 0.12 s instead of snapping. **Mantles** keep 85 % of the speed you came in with and go faster at a run (a vault).
- **Curbs while landing:** stepping up a lip now works while coming down onto it, not only from the ground.
- **Camera:** a landing dip on a spring, eased crouch, a few degrees of field of view at a sprint and in a slide, and a slight lean into strafes.

**Slide, 2026-11-14 (owner).** "The idea with the slide is almost like in Dishonored... the slide just knocks people back. I don't need it to do damage, I just need it to knock them in the air. I want it to be a useful tool for traversal and setting up skill shots", and "tune back how far you can slide, because it gives it a really arena shooter vibe instead of immersive sim vibe."
- **Shorter.** Boost 1.5 m/s (was 3.5), top speed 13 m/s (was 16), friction 9.5 m/s² (was 4.8), it ends at 5 m/s (was 4) and can't start again for 0.6 s (was 0.35). From a sprint it now covers about 7 m in 0.8 s (was about 18 m). Slide-hops still carry speed, capped lower. A phone that saved tuning before this keeps its other movement values but takes the new slide friction and boost (`TuningMenu.MOVEMENT_RESETS`).
- **The hit launches.** Sliding into a man does no damage: he goes up in front of you, tumbling back with his feet swept out (up to 60°), under lighter gravity (12 m/s² instead of his 20) so he hangs about a second, and he can't think or shoot until he's landed and had 0.8 s to find his feet (`Enemy.launch`). With the Operator he goes about 1.2 m up and 4–5 m along the slide. You lose 80 % of your slide speed so he goes up ahead of you, and the world runs at 45 % for 0.35 s to give you the shot; rumble and a camera knock. Kill him in the air and the ragdoll carries on with his flight. Heavier, stronger bodies (mass × usable strength × impact) throw him higher and further. Launch up/along are on the phone under Pause → Tuning → Movement.
- Cloud evidence: `test_sliding_into_an_enemy_launches_him` (over 0.9 m up, no damage, back on his feet), `test_a_tap_of_b_slides_the_whole_way` (5–10 m), `test_slide_launch_scales_with_momentum`; frames from `-- --demo=slide` in `docs/previews/slide_launch.png`.

Evidence in the cloud is indirect (`tests/unit/test_movement_config.gd`, `tests/scene/test_movement.gd`): no speed lost through a 90° turn, a slide-hop keeps most of its speed 0.3 s after landing, a tapped jump is lower than a held one, and at 40 fps the camera moves an even distance every frame while the body doesn't. Whether it feels better is the owner's call on the phone.


### 5.7a Gait: stepping, not gliding (2026-11-17)

Owner (2026-11-17): "I want it to feel like someone is smoothly, buttery, creamy, smooth stepping, almost like the movement in the reboot 2019 Modern Warfare game, but instead it just feels like a camera is kind of gliding. The only movement that has the quality of feel I'm going for is the slide... I want the other movements to be creamy and crisp as well, so that I can rely on them and not play the game like just an arena shooter."

Why it glided: the camera only translated (no head motion at all, the gun had a free-running sine bob), the player had no footstep sounds, turns carved round at full speed, and stops crept to zero (half the stop was spent under 1.5 m/s). What changed (`src/player/gait.gd`, `MovementConfig` "Gait" and "Footsteps" groups, `WeaponData.move_inertia`):

- **Steps tied to the ground.** A heel strikes every stride of ground covered; the stride grows with speed (2.6 m at a walk × (speed / walk)^0.55), so cadence rises gently: about 2.5 steps/s walking, 3.2 sprinting. The feet never skate, whatever the frame rate.
- **The head rides the stride**: low at each strike, high mid-stride (a smooth wave with a little cusp, `bob_cusp`), over the planted foot and rolled onto it. Each strike lands with weight: a short dip, a nod and a shift onto that foot on a slightly bouncy spring, then it settles. Crouched it's about half; aimed down sights, 30 %.
- **Weight shift.** The head trails the body's velocity on a spring (3 Hz): it rocks back about 0.4° as you push off, pitches forward about 0.5° over a stop, leans into a strafe and counter-sways when the strafe stops. Landing adds a nod.
- **The gun has weight.** It rides the same stride a beat behind the head, nods with each strike, trails back and to the side when you speed up or strafe, carries on over a stop, sinks as you jump and floats as you fall. Heavier guns swing more (`move_inertia`: pistols 0.8, MP5 0.95, Saiga 1.15, rail 1.1, M14 1.25, M32 1.35, MG42 1.7).
- **Footsteps**: a heavy boot on concrete, metal (hollow, no ring), wood or dirt, picked from what's underfoot; the suit's plates and kit on running strides and wall-runs; a both-feet thump on landing; a push-off on a jump. Synthesized (`raw_assets/audio/build_footstep_sfx.py`), on their own three voices so they never cut a reload sound.
- **Planted starts, stops and turns.** The first push builds over the first third of the speed (45 % → 100 % of the acceleration) and arrives firmly; stops brake hard and finish in about 0.15 s instead of creeping (on top of the head's forward pitch). Turns plant and push off: a snap 90° dips the speed about 10 % for a moment (it carved at full speed before), and a sprint turns slower (8.5 rad/s) than a walk (13). Speed above a sprint (slide-hops, wall jumps) still carves and carries: the slide and the slide-hop are unchanged.

All of it is on the phone under Pause → Tuning → Movement and Gait (and "Gun weight on the move" per gun). A phone that saved tuning before keeps its other values but takes the new acceleration, braking and turn values (`TuningMenu.MOVEMENT_RESETS` version 3). Evidence: `tests/unit/test_gait.gd`, `tests/unit/test_movement_config.gd`, `test_walking_takes_steps_and_the_head_rides_them`; traces from the game code in `docs/previews/gait_trace.png` (`tools/gait_trace.gd`, `tools/plot_gait_trace.py`). Whether it feels like stepping is the owner's call on the phone.

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

**Main menu (owner, 2026-11-14).** The game opens here, not in the fight: "load into a main menu that shows your character leaning against a wall... his helmet off... smoking a cigarette... customize your loadout, and as you customize the loadout, it will change what he looks like in that scene... outside a Chinese restaurant in Chinatown." The operative (`MenuSmoker`) leans on the window of the Sea View restaurant under its red lanterns, helmet off (the owner's face), right boot flat on the wall, left arm folded under his right elbow. Every ~10 s the cigarette goes to his lips, the ember flares and lights his face, and he breathes the smoke out; smoke curls off the tip the whole time. The pose is procedural on the operative's skeleton (FK in the rest frame plus two-bone IK for arms and legs), no clip. The menu: Begin, Loadout, Map (◀ ▶: Chinatown docks or the test range), Options (the pause menu's settings), Quit. Loadout opens the loadout screen over the scene with the camera moved so he stands in the clear left quarter, wearing whatever is under the cursor; what's built is saved and goes into the game. Begin fades to black and the game starts on the same map (the map, lights and rain are already built). Pause → Main menu comes back to it. Staging (his spot, the lean, both camera framings, the cigarette's timing, the ember and key light) in `data/levels/main_menu.tres`; code in `src/ui/main_menu/`. Captures: `docs/previews/main_menu.png`, `main_menu_loadout.png`; the pose on its own: `src/levels/lookdev/menu_pose_lookdev.tscn` (`-- --pose-t=<s>` holds the cycle).

**Pipeline.** Materials are a tileable texture array (`raw_assets/env/materials`, `raw_assets/env/atlases`); the map is one generator (`build.py`, with `props.py` and `buildings.py`) and one bake/export step (`bake.py`). Everything rebuilds from scratch.

---

### 7.2 The Golden Dragon Grand Hotel (owner, 2026-11-18)

Map 2. Owner: "a luxurious Chinese 5 star hotel lobby, abandoned ofc but still fully lit. The whole map needs to be inside, waves spawn in elevators that release into the lobby and also enter from outside the building ... an interesting mix of tight corridors that wind around a central lobby atrium ... tight corridor shooting with large amounts of enemies, almost playing the defensive while I hold choke points or offensive sliding through the corridors, dipping in and out of cover. But also ... the long sightlines of the massive atrium to provide the opportunity to stalk my foes." Mostly Blender, not Tripo (the Tripo balance was low).

**Layout** (`raw_assets/levels/hotel/build.py`; plan render `raw_assets/levels/hotel/_build/plan.png`; about 76 × 49 m inside, two storeys):

- **The atrium** (32 × 20 m, open 15 m to a coffered rosewood-and-brass ceiling): an octagonal marble fountain with a brass and onyx centrepiece under the great chandelier, two smaller chandeliers, red silk banners down the void, the reception desk (back-lit onyx front, black marble top) with a rosewood screen behind it carrying the hotel's name, lounges with velvet sofas and marble tables at the corners, a grand piano, planters. The triad have fortified it: sandbags, crates, luggage carts, a toppled sofa. Polished marble with a black border and a brass compass ring.
- **The arcade and the mezzanine gallery** ring the atrium: marble columns with brass capitals every 4 m on both storeys, gold silk walls over rosewood dados, downlights, sconces. The gallery has a glass balustrade with a brass rail (chest high: you shoot over it, bullets go through the glass) and **long sight lines across the atrium**, with sofas, planters and crates for cover. Two **grand staircases** (3 m wide, marble with a carpet runner and brass rods) run along the atrium's sides from the floor to the south gallery.
- **The winding corridors** (2 m wide, red damask, carpet): from each side of the entrance hall a passage runs back, turns north, cuts into the arcade, dog-legs to a dead end, runs the length of the outer wall past the back stair, turns back east and on to the lift hall and the service corridor. Doors into the arcade along the way. Corridor walls are drywall (heavy rounds go through), the outer walls concrete. Room-service trolleys and sandbag stops at the corners.
- **Rooms:** the Dragon Bar (west: bar counter with back-lit onyx shelves of bottles, lacquer tables, armchairs), the restrooms and the security office (east), the concierge office and the luggage store by the entrance. Upstairs: the tea lounge (west) and the ballroom foyer (east), each with two doors onto the gallery; a back stair from the corridors comes up into each.
- **The lift hall** (north): six lifts in a black-marble wall with brass portals, floor indicators and call plates. Behind them the **service corridor** (staff only: concrete, fluorescent tubes, pipes, laundry carts) links the two wings.
- **The entrance hall** (south, 7.5 m high, two chandeliers, the hotel's name over the arch to the atrium) and its glass front with three open door bays, out to the **porte-cochère**: a black marble canopy with downlights, the hotel car left at the door, stone planters, the street beyond a hedge (night, rain).

**Where they come from** (`HotelMap`, `src/levels/hotel/lift.gd`): only the lifts (two places in each of the six cars) and the street (the far ends of the drive, behind the planters and the stone facade). A man (or dog) who spawns in a car waits behind its brass doors: the floor lantern lights, the car chimes, 1.1 s later the doors roll apart and let him out. They stay open at least 3.5 s and until the car is empty (they never close on the operative; the safety edge reopens them), then close. The doors are physics bodies: they stop people, bullets punch through them like sheet metal, and shut, they hide a car from the spawner's line-of-sight test, so a car the player isn't watching is where the next men appear. Same rolling rule as Chinatown in Sandbox (`data/levels/hotel_spawns.tres`: 8, then 3 when fewer than 4 fight; spawns at least 10 m away) and the same Survival waves.

**Glass that breaks** (`src/levels/hotel/glass_panes.gd`): the gallery's balustrade panes and the glass front are tempered glass. The first round, plasma bolt or bolt-splash through a pane bursts all of it into falling shards with a crack and a long tinkle (rounds go on through it). The opening stays open: a man knocked, thrown or slid into it goes over the edge, 4.5 m down into the atrium (the men's own paths still treat the line as a wall). 79 panes, one draw call for all of them.

**The boss on the hotel:** he drops in through the atrium when you're under open sky; anywhere else (corridors, the gallery's covered side) he comes down in the lift nearest you instead: the chime, and the doors open on him.

**Fire spreads** (all fire, plasma and Dragon's Breath): a burning man who comes within about a metre of another sets him alight too, and the panic with it.

**Look and sound.** All indoors and all lit (warm 2700 K downlights, chandeliers, sconces, onyx glow, cool fluorescents in the service corridor, sodium lamps outside). Lighting is baked in Cycles into a 4096² lightmap like Chinatown's; reflection probes over the atrium, arcade, gallery, entrance and lift hall put the chandeliers in the polished marble. Its own texture array (`raw_assets/env/hotel/build.py`: Calacatta and Nero Marquina marble, polished brass, a red-and-gold medallion carpet, rosewood panelling, gold silk with a woven cloud motif, back-lit onyx, a sign and art atlas in Traditional Chinese with English, two ink landscapes and a calligraphy scroll; shared layers cut from the world array). Dust dulls the marble in patches, papers lie scattered. Ambient sound: the ceiling speakers still play a slow guzheng air over electric piano (lobby), a lounge loop in the bar, the fountain, the service corridor's hum, rain outside.

**On the menu:** Map ◀ Golden Dragon hotel ▶, then Begin (Sandbox) or Survival (the run starts on the hotel). Pause → Map cycles to it too.

## 8. Survival: the main mode (owner, 2026-11-15)

Owner: "we have an insanely expressive, fun-to-play, dynamic base... but there's no game rules to really bound them or any kind of progression. It's just a mindless power fantasy at this point." The main mode is **wave-based survival with a run that builds up**: you start with little, every wave gets harder, and between waves you get new hardware. It should be "a power fantasy that you have to earn working with the tools you have available instead of just instantly having the best tools." The power fantasy can break through late in a run.

What exists today stays as a second mode, **Sandbox**: every gun, the full loadout screen, every active at its full strength, rolling spawns or waves (§7.1, §12 M1).

### 8.1 Why waves (Claude's view, asked for by the owner)

The owner asked whether the mechanics would suit an arena shooter or a campaign with a story better. Claude's answer: **waves are the right base.**

- The actives are expressive because they combine. A run that hands them out one at a time makes every combination a decision, and every run shows a different set. A campaign would hand them out in a fixed order, and a pure arena shooter has no place to hand them out at all.
- The simulation (ragdolls, gore, morale, suppression) is at its best with many men on one map. Waves give a steady supply of them, and the map can be learned like a Zombies map.
- One map with rising pressure is the cheapest content per hour of play. It suits a team of one owner and Claude, and a phone.
- The roguelite rule (power comes from choices made in this run) answers the owner's complaint directly.

Two things from the other formats are worth taking, both later: **a light frame around the run** (a handler on the radio, a reason the docks are hot, a few lines between waves), which gives a campaign's sense of place without a campaign's cost; and **objective waves** (hold the restaurant, stop the boat leaving, recover a case from the cold store) every so often, so a run isn't only "kill everyone". *(proposal)*

### 8.2 A run

1. **Main menu → Survival.** Pick the starting kit:
   - **A doctrine: the baseline character.** Each is the graft suit plus two or three passives, and it tilts what the supply drops bring (§8.5). On the bare suit no active comes online (every one needs a stat a passive supplies; checked 2026-11-15), so the baseline body is what decides which actives you can start with.
   - **One gun** from three: the Five-seveN, the MP5/SD-L or the Saiga-12K (owner's list).
   - **One active** at **Mk I** (§8.3), from the two or three that doctrine's body can run (owner: "only some of them will be listed as choices"). Ghost: RX-9, TC-4 or SX-8. Reaper: MW-7, KR-5 or NT-5. Juggernaut: BW-6 or KR-5. Marksman: RX-9 or SX-8. Handler: SD-3 or AD-2. The GX-4 and the LC-6 are never starters: bosses carry them (§8.7).
2. **The body grows from there.** More passives come from drops. The loadout screen (View) shows the body and what each part does, but can't install, remove or reorder parts (`BodyStatus.locked`); the colours still work. The actives sit on the D-pad in the order they came.
3. **Waves** on the Chinatown docks (§8.6). A wave ends when nobody is left fighting.
4. **A supply drop after every wave** (§8.4): either one item picked for you, or a choice between two.
5. **A boss every fifth wave** (§8.7). Bosses drop the active they carry, or an upgrade for it if you already have it.
6. **Death ends the run.** A summary screen: waves survived, kills, what you had. Back to the menu.

Between waves *(proposal, to tune)*: health and active charges refill. A break of a few seconds plus the drop screen. Pressure inside a wave comes from the enemies, not from attrition between them. An ammunition economy can come later if runs feel too safe.

### 8.3 Active marks (Mk I, Mk II, Mk III)

Every active has three marks. Owner: "it's not going to be like the full version of the active ability that we have now. It's going to be tuned down... the needle throwing thing, the first version of it might only have 2 needles... a higher strength requirement for damage. The slowdown time might only last 4 seconds at a full charge when you first get it." And: "most of them right now would work out best as the highest ceiling level of that augmentation in order to maintain tension."

- **Mk III is the active as built** (everything in §3.4–§3.4d). It's the ceiling.
- **Mk I and Mk II change the tuning values only.** They don't add or remove behaviour. Each mark is a list of property overrides on the active's resource (`ActivePartData.marks`, in the part's `.tres`), so marks are tuned like everything else, in data.
- A new active drops at Mk I. A boss drop or a rare supply-drop upgrade raises it one mark.
- Sandbox always uses Mk III.

First pass at the marks *(proposal; values in the part files)*:

| Active | Mk I | Mk II | Mk III (as built) |
|---|---|---|---|
| RX-9 Reflex Overclock | 4 s of charge, world at 40 %, slow refill | 6 s, world at 32 % | 8 s, world at 24 % |
| SX-8 Urticating Setae | 2 marks, needs more strength for full damage (ref 1.5), weaker cavitation | 3 marks (4 with perception), ref 1.3 | 4 marks (5 with perception), ref 1.15 |
| GX-4 Gauss Arm | 4 rounds, slow refill | 7 rounds | 10 rounds |
| MW-7 Monofilament Whip | 4.2 m, lighter cuts | 5.4 m | 6.5 m |
| SD-3 Shrike Drone | 1 drone, 12 s battery, smaller blast | 2 drones, 17 s | 3 drones, 22 s |
| NT-5 Mesh Arm | 10 m reach, 2 grabs, weaker throw | 14 m, 3 grabs | 18 m, 4 grabs |
| KR-5 Ram Thrusters | 1 burn, slower, a softer ram | 2 burns | 2 burns, full speed and ram |
| TC-4 Thermoptic Shroud | 4 s, seen from 5 m, a shot shows you longer | 7 s, 4 m | 10 s, 3 m |
| BW-6 Fan Shield | 50 % integrity, longer to recover from a break | 75 % | as built |
| AD-2 Arc Projector | no chaining, 1 discharge | 1 chain, 2 discharges | 2 chains (more with power), 2 discharges |
| LC-6 Lorentz Catcher | holds 15 rounds, 3 s | 26 rounds, 4.5 s | 40 rounds, 6 s |

### 8.4 Supply drops (the reward table)

After each wave a supply drop comes in *(Claude's framing: the operative's handler sends it; grounded, no loot falling out of bodies)*. Owner: "after every wave, you either get something just automatically selected by the loot table, or you get a choice between 2 things, like for example, a gun or an active augmentation, and you pick it."

- **What can drop:** a gun you don't have; an active you don't have (at Mk I); a passive part; rarely, a mark for an active you have.
- **Choice or pick.** Each drop is either a choice of two (A or B on the drop screen) or one item delivered for you. The first drop of a run is always a choice. The odds are in `data/run/survival.tres`.
- **The two offers differ:** never the same item, and the second is drawn without the doctrine's bias, so there's always a way to pivot.
- **Passives and the body's limits.** Passives install into their location; if it's full, the card says what comes out. A part never drops if it would push out an active, knock an active offline (ER-2 replacing the SA-2 that RX-9 needs), or go over the capacity budget. Power and heat (§3.6) still apply, so a run that takes everything runs hot and slow, which is the point of the parts system. A part that wouldn't come online on your body yet drops less often and its card says what it needs.
- **Actives:** three at most, one per D-pad direction; no new ones drop once you have three (marks still do).
- **Guns:** the wheel holds what you own. *(proposal)* Guns stop dropping once you carry four.
- **Ammunition:** reserves are unlimited for now (as in Sandbox).
- Every entry is a `RewardData` resource in `data/run/rewards/` with a weight, the wave it can first appear on, and tags.

### 8.5 Steering a build: doctrine and affinity

Owner: "There also needs to be a way for you to influence the general likelihood of you getting things... on this playthrough, you're gonna get more stuff that's kitted towards high mobility and stealth... or this is like a juggernaut playthrough."

Every reward has **tags**: `mobility`, `stealth`, `heavy`, `precision`, `close`, `tech`. Three layers bend the odds *(proposal)*:

1. **Doctrine**, picked at the start of a run (it is also the baseline body, §8.2). It multiplies the weight of matching tags (×3 for its main tag, ×2 for its second):
   - **Ghost** (stealth, mobility): SA-2 synaptic accelerator, CM-1 chromatophore mesh, OC-2 respirocytes.
   - **Reaper** (close, mobility): TL-3 titanium skeleton, EM-2 myofibrils, SA-2.
   - **Juggernaut** (heavy, close): CB-1 carbon sheathing, CT-7 trauma plating, LF-8 leg frame.
   - **Marksman** (precision, tech): SA-2, OB-5 ocular ballistics, TG-6 threat graph.
   - **Handler** (tech, precision): NL-3 cortical uplink, PC-3 power cell, MR-1 mesh relay.
   Names reuse the loadout presets. Of the first drops at wave 8, Ghost is offered a stealth item about 4.7 times as often as Juggernaut (`test_doctrine_bends_the_odds`).
2. **Affinity.** Every item you own adds to the weight of its tags (+35 % per item, capped at ×3), so a build that starts pulling one way keeps going that way, as in Hades or Slay the Spire.
3. **Later:** drops that change the doctrine mid-run (a "requisition priority" order from the handler), and boss drops that bias the next few drops.

### 8.6 Waves and the difficulty curve

Each wave has a **threat budget** that grows with the wave number. Each enemy type has a cost and a first wave, and the director spends the budget on the types it has unlocked (`data/run/survival.tres`, `SurvivalWaves.compose`):

- Wave 1 is a handful of the cheapest men. New types arrive one at a time over the first waves, so each one gets a wave to be learned.
- At most 12 alive at once (CLAUDE.md §8). A wave bigger than that comes in as reinforcements while it's being fought, out of sight, like the rolling spawns (§7.1).
- **Crescendo** *(proposal)*: waves build in fives. Waves 1–4 of a block rise, wave 5 is the boss, and the next block starts a little lower than the boss wave and climbs past it.
- **Theme waves** *(proposal, after wave 6)*: now and then a wave is drawn mostly from one family: a rush of melee men and shotguns, a wave of marksmen on the heights, a wave led by two Red Poles.
- What the player gets and what the enemies get have to climb together. The target is that a good player with a sensible build reaches wave 15–20 and a strong build feels like a god by wave 20.

### 8.7 Bosses

Owner: "every so many waves, a unique special boss will come down. I want them to have mechanics... some augmentations could be great counter to certain bosses... bosses, when you defeat them, could drop either an active augmentation that they carry, or if you already have it, an upgrade for it."

- Every fifth wave. A boss arrives with escorts, has a health bar and a name on screen, and at least one mechanic you have to answer, not just more health.
- **Bosses are the exception to "enemies are unaugmented"** (§2): they carry black-market hardware, which is why they drop it.
- Each has a counter among the actives, and none needs one.

Triad bosses for Chinatown *(proposal; ranks are real triad ranks)*:

| Boss | Mechanic | Counters | Drops |
|---|---|---|---|
| **The Straw Sandal** (432, the messenger) | A knife fighter under a thermoptic shroud. Shimmers in and out, flanks, strikes from behind. Visible in the rain and when hit. | Setae marks him through the shroud; thermographic retinas; the fan shield blocks the strike | TC-4 Thermoptic Shroud |
| **The White Paper Fan** (415, the counsellor) | Stays back and runs his men: a drone over the street that spots you for them, and he calls flanks. Kill the drone and the squads go blind. | The arc projector or the Shrike for the drone; the shroud | SD-3 Shrike Drone |
| **The Vanguard** (426, the Red Pole of Red Poles) | Bomb-suit armour and a belt-fed gun; rounds glance off the front plates. Turns slowly. | The LC-6 throws his own rounds back; the Gauss arm goes through the plate; ram thrusters get you behind him | LC-6 Lorentz Catcher |
| **The Incense Master** (438) ✓ (built 2026-11-15, §8.7a) | A huge enforcer with a Gauss prosthetic for a right arm: a haymaker, a ground pound, and a charged Gauss shot through cover. Down on one knee at zero; finished with an execution (§8.7b). | Break line of sight; jump the pound; the LC-6 catches his slug and throws it back (it staggers him); the GX-4 | GX-4 Gauss Arm, or its next mark |
| **The Mountain Master** (489, the head) | Late in a run. Several of the above at once, in phases. | Whatever the build is | A mark for every active you own |

The Incense Master is wave 5's boss (owner, 2026-11-15). The others aren't built yet: a boss wave with no boss left (`SurvivalConfig.bosses`, from `tools/run/gen_pool.py`) is a **lieutenant wave**: two Red Poles and a heavy escort, with a boss drop at the end.

### 8.7a The Incense Master (built 2026-11-15)

Owner: "the first boss of the triad map... he should spawn on wave 5... a massive triad enforcer with a bald head, a leather jacket, and a gold and diamond necklace. He has a powerful prosthetic arm that he uses both in ground pound and melee attacks, but can also launch something similar to the gauss cannon, and the boss drop should be a gauss cannon upgrade or the original item." Code: `src/ai/boss/`; tuning: `data/enemies/incense_master.tres` (body, health, zones) and `data/enemies/bosses/incense_master.tres` (`BossConfig`: everything below).

- **Look.** Since 2026-11-17 a Tripo3D man (§5.6b) at 1.38 scale (about 2.4 m): huge and heavy, bald, stubble and goatee, black-and-grey dragons and incense smoke tattooed over his chest, belly and arms, a sleeveless black leather vest open over the bare chest (sleeveless, so the prosthetic's socket sits on a bare shoulder), leather trousers, a wide belt with a gold buckle, heavy boots (`data/enemies/outfits/incense_master.tres` → `bodies/tp_incense_master.tres`). Before: the triad body in an open leather jacket, slacks, a gold watch and chain. On the chest a gold medallion set with diamonds on a heavy Cuban chain with iced links; the stones glint with the view. His right arm is gone from the middle of the upper arm (hidden the way a cut hides a limb, without the gore) and the **prosthetic** takes its place: a socket clamped on the stump with a gold band, a hydraulic ram down the back of the elbow, a forearm a size bigger than a man's wound with four copper Gauss coils lit blue between them, two rails along the outside past the wrist to a muzzle block, a steel fist with a gold knuckle duster. `raw_assets/characters/incense_master/build.py` models each piece in its bone's space (`assets/characters/incense_master/hardware.gltf`); `BossHardware` hangs them on the bones, so they follow the clips, the aim and the ragdoll. Preview: `docs/previews/incense_master_arm.png`.
- **Body.** 2,600 health; head ×2 (not ×4), neck ×1.6, chest and stomach ×1, limbs ×0.5–0.65. Nothing comes off him while he lives (no dismemberment, no bursting, no crippled legs, no dropped weapon, no fear: he never breaks or surrenders). The prosthetic is steel: rounds spark off it for 8 % blunt damage. Too heavy to shove: slides, the knife and the ram hurt him (capped at 150) but don't move him; the mesh arm can't take him.
- **Movement.** Walks you down at 2.3 m/s; charges at 5 m/s when you're past 12 m or out of his sight. New clips (`raw_assets/characters/triad/build.py`, "brute"): `brute_ready`, `brute_walk`, `brute_run`, `pound`, `swing`, `cannon`, `kneel_down`, `intro`.
- **The haymaker** (within 3.4 m): the prosthetic cocks back by his right side and the body winds up (the tell), then it comes across at head height 0.52 s after the start. Lands within 3.5 m and 130° in front: 48 on the bare suit (scaled by armour), a throw of 11 m/s along the swing and 4 m/s up. He turns after you during the windup, but only so fast: sidestep, slide, back off. 1.8 s before the next.
- **The ground pound** (within 6.5 m, more likely the longer you stay close): both fists go up over his head with a scream (the tell), he rises on his toes, and 1.0 s after the start the prosthetic goes into the ground. A shockwave out to 8 m: 55 at the fist down to 10 at the edge, thrown up (6.5 m/s) and out. **In the air when it lands (0.35 m up) it misses you.** His own men in it are thrown too. A ring of dust, grit, a mark in the ground, loose things kicked. 5.5 s cooldown.
- **The Gauss shot** (6.5–70 m, in sight or just lost): he plants, raises the arm straight out with the left hand bracing it, and it charges for 1.5 s: the coils brighten, a rising whine, a thin blue line from the rails to where it points, which tracks you at 80°/s and **stops tracking 0.28 s before the shot**. The slug is a real Ballistics round (16 g at 1,100 m/s, `data/enemies/weapons/gauss_slug.tres`): about 64 on the bare suit, through thin cover, into anyone in the way. The GX-4's corkscrew beam, flash, crack. Without sight he fires where he last saw you. 6 s cooldown.
- **The LC-6 counter.** His slug is caught like any round. In the field it is drawn as a fat tungsten rod crawling with blue (`LorentzCatcherData.gauss_scale`), the catch hits like a hammer (shake, rumble, a zap), and on the release it goes straight back at the aim point or the chest nearest it, not spread. A Gauss slug (his own, or a GX-4's) **staggers** him.
- **Stagger.** 220 damage inside 0.8 s, or any Gauss slug: he breaks off whatever he was doing and stumbles for 1.1 s. Not again for 4 s.
- **Rage.** Below half health (the mark on the bar): 25 % faster, two slugs a volley (0.55 s apart), cooldowns ×0.7, the coils brighter. He roars ("Enough!").
- **The bar.** His name and health across the top of the screen (CombatHud `BossBar`), gold, orange when enraged; ENRAGED, STAGGERED, ON HIS KNEES under it. The wave banner drops below it.
- **On one knee.** At zero health he doesn't die: he drops to his right knee, hunched, the prosthetic hanging and sparking, breathing hard, and looks up at you as you come near. He's out of the fight (not an enemy for aim assist or the actives) and can't be finished by gunfire. The wave doesn't end until he's executed (§8.7b).
- **Entrance** (`BossIntro`, about 4.4 s, letterboxed; owner: "a badass very short cutscene"): wave 5 starts with him. A low camera in the street on a long lens: he drops out of the sky from 13 m and lands in a crouch with the prosthetic in the ground, a shockwave of dust, the camera shakes. Close from below on his face as he rises and brings the fist up in front of it; the coils light and whine. Wide and low as he spreads his arms and roars; his name comes up in gold, "THE INCENSE MASTER — 438 · Triad enforcer · black-market Gauss arm". Then your eyes again, turned to face him. He lands on the navmesh, under open sky, in your sight, about 13 m in front of where you're looking. Your HUD hides and you can't be hurt while it plays; his escorts (45 % of the wave's budget) start arriving 6 s after it begins.
- **Sounds** (synthesized, `raw_assets/audio/build_boss_sfx.py`): the roar (the project's own death scream an octave down over a growl), the pound, the landing, the charge whine, the swing, the coils lighting; the shot is the GX-4's.
- **The drop** (`RunState.roll_boss_drops`, `BossConfig.drop`): the GX-4 Gauss Arm at Mk I if you don't have it, its next mark if you do. If taking it would cost you an active (the MW-7 is on the same arm, or the D-pad is full) or it's already Mk III, the usual boss drop comes with it as a choice, and the card says what comes off.

### 8.7b The execution (built 2026-11-15)

Owner: "when his health goes to zero, instead of dying he falls to one knee. From here you can walk up to him and a prompt to hit the right bumper pops up, hitting it plays a first person execution on the boss, it's a series of brutal head punches that ends up gibbing his head... player character examines his bloody fist and shakes off the blood."

- **The prompt.** Within 3.2 m of him and looking at him (45°): "RB EXECUTE" under the crosshair. RB is the `execute` action (keyboard F).
- **What plays** (`BossExecution`, about 5.7 s, real time): the operative steps in to arm's length of his face and he's turned to face you; your gun goes down. The left hand comes up and takes his collar (`exec_grab`) and pulls him up to look at you. The right fist (the GS-2 suit's hand, in your colours; `assets/characters/fp_execution/execution_hands.gltf`) draws back and drives into his face: three punches (0.95, 1.4, 1.78 s), each snapping his head back with blood off the face, some onto your view, a wound on the head, a hitstop beat, shake and rumble; the blood builds up on your knuckles. The fourth draws back slower, and lands in slow motion (0.25 for 0.55 s): his head comes apart, the body goes over backwards, the neck pumps. You let go, lift the fist in front of your face and look at the bloody knuckles (blood drips off them), turn it, then shake it off with three flicks that throw blood on the ground. The fist goes down, the gun comes back up.
- You can't be hurt while it plays, and your actives fold away first. His escorts may still be around.
- Timings, distances and the slow motion are in the BossConfig's Execution group.

Not yet *(proposal)*: his own voice lines (he uses the triad callouts), a thrown slug through a wall when he hears you behind it, the fist's blood staying on the operative's knife hand, more execution variations for later bosses.

### 8.8 The enemy roster

Owner: "There also needs to be way more unique enemies, there needs to be melee-focused enemies, there needs to be a wide bank and variety of them per level, even if per level they all fit a certain theme... so you can truly achieve a crescendo of different waves and a smooth difficulty curve."

Each map has a theme and its own roster. For Chinatown, the triad *(proposal; ✓ = built)*:

| Type | Role | Cost | From wave |
|---|---|---|---|
| **Blue Lantern** ✓ (built 2026-11-15) | Uninitiated recruits: Type 85 SMG, poor aim, slow to react, panic early. The bottom of the curve. | 1 | 1 |
| **Gunman** ✓ | Rifleman. Holds cover, peeks, bursts. | 2 | 1 |
| **Hatchet Man** ✓ (built 2026-11-15, §8.8a) | Melee. Cleaver or hatchet, sprints between cover, vaults low walls, comes from the side. Has to be killed or dodged, not out-shot from cover. | 2 | 4 |
| **Enforcer** ✓ | Plate carrier, pump shotgun, pushes in close. | 3 | 2 |
| **Dao swordsman** | Melee elite: a long blade, a guard that turns rounds aside from the front (a grafted forearm plate, so hardware), a lunge. | 4 | 8 |
| **Red Pole** ✓ | Lieutenant. SMG, steadies the men near him; his death breaks them. | 4 | 3 |
| **Firebomber** | Throws molotovs to flush you out of cover and close off streets. | 3 | 6 |
| **Marksman** | A scoped rifle from the gallery and the container stack; a laser and a glint before the shot. | 4 | 7 |
| **Shield man** | A ballistic shield and a pistol; covers others as they advance. | 4 | 9 |
| **Gunner** | A belt-fed gun; suppresses a whole street. | 5 | 11 |
| **Anti-augment specialist** | EMP grenades that stall your actives, armour-piercing rounds, a jammer that grounds the drone. | 6 | 13 |
| **Attack dog** ✓ (owner, 2026-11-17; built 2026-11-17, §8.8b) | A German shepherd that gallops straight at you by scent, leaps the last metres and bites. Fast and low, a small target. | 1.5 | 6 |


Melee men need their own code: the Hatchet Man's is built (§8.8a); the swordsman still needs a block. The Hatchet Man debuts on wave 4, not 3 as first proposed, so the Red Pole (wave 3) and he each get a wave of their own.

### 8.8a The Hatchet Man (built 2026-11-15)

Owner: "start work on the Hatchet Man melee focused enemy." What he does (`src/ai/melee_brain.gd`; tuning in `data/enemies/hatchet_man.tres`, the Melee group of `EnemyConfig`):

- **Kit.** A hand hatchet or a Chinese cleaver, one picked per man (`raw_assets/weapons/enemy_melee/build.py` → `assets/weapons/enemy/hatchet.gltf`, `cleaver.gltf`, on the guns' weapon socket). Tank tops, vests and street clothes, so the tattoos show. 95 health, no armour, brave (courage 0.85), sprints at 6.8 m/s (the operative sprints at 11).
- **Approach** (beyond 9 m): from cover to cover, each one nearer the operative and out of his sight, toward a point 75° off where the operative is looking, on the side the man is already on, with a short crouch (0.35–1.1 s) behind each.
- **Charge** (inside 9 m): straight in, weaving across the operative's line when he's being looked at. Where the straight line only crosses low things (up to 1.25 m) and has ground all along, he takes it and **vaults** what's in the way (0.55 s, a speed vault) instead of following the nav path round.
- **The chop.** Within 3 m, with nothing low between them, the blade goes up high over his right shoulder: **the tell**, with a grunt. He lunges (4.2 m/s) and turns after the operative at 200°/s at most. 0.46 s after the windup starts, the blow lands if the operative is within 2 m and 110° in front of him: 42 damage on the bare suit, scaled by armour (damage per kJ ÷ 7) and pushed back 3 m/s, with a shake and rumble. Then 0.55 s of recovery.
- **Answers.** Dodge it (a sidestep, a slide, a jump or the ram thrusters past him in the windup: he can't turn fast enough); kill him first; stagger him with 20 damage in the windup (two quick Five-seveN rounds, one rifle round, a shotgun blast); the R3 knife kills him in one cut; the BW-6 fan shield turns the blade from the front for 3 integrity. Slides, the mesh arm and blasts knock him out of a chop or a vault.
- **Morale.** He breaks like the others, but never fires blind: he runs, cowers or gives up.
- **Animation** (new clips in `raw_assets/characters/triad/build.py`): `melee_ready`, `melee_run`, `melee_crouch`, `chop` (1.0 s, the blow at 0.46 s, played faster or slower to match `melee_windup`), `vault`. Preview: `docs/previews/hatchet_man_poses.png`.
- **Where he appears.** Survival from wave 4 (cost 2, at most 3 per wave, 5 from wave 10). Sandbox rolling spawns on the docks: 18 % of arrivals.

Not yet *(proposal)*: his own voice lines (a war cry; he uses "Rush him!" for now), a thrown hatchet when the operative is out of reach on a height, blood on the blade after a hit, a sound made for the chop (it uses the whip's swish and cut).

### 8.8b The attack dog (built 2026-11-17)

Owner, 2026-11-17: "German shepherds that run at you... part of the triad map too."

- **What it does.** No gun, no cover, no morale. It knows where the operative is (scent) and gallops straight in at 9.5 m/s (faster than his walk, 6.5, slower than his sprint, 11), by the navmesh when a wall is in the way. From 1.6–4.6 m with a clear line it crouches for 0.16 s (the tell) and leaps; if its mouth reaches his chest in the air the bite lands (24). At his legs it bites standing (14, every 0.75 s). After a leap it backs off a step and comes again. A sidestep in the crouch makes the leap miss. Bites go through `Player.on_melee_hit`, so blocks and shields stop them.
- **Damage.** 60 health; zones on the rig's bones: head ×2.2, neck ×1.8, chest ×1.2, body, legs ×0.6. A hit of 9+ makes it flinch and yelp (and breaks a crouch). One pistol round to the head kills it. Blasts and grenade fragments hurt it, the R3 strike reaches down to it. It isn't an `Enemy`: it joins the `enemies` and `dogs` groups, code that casts to `Enemy` skips it, and the slide doesn't launch it yet. It isn't marked as the last hostile on the HUD.
- **Where.** Chinatown rolling spawns (weight 0.12 of the mix, `data/levels/chinatown_spawns.tres`) and Survival from wave 6, up to 3 a wave (5 from wave 12), cost 1.5 (`tools/run/gen_pool.py`). Tuning: `data/enemies/attack_dog.tres`. Code: `src/ai/dog/`.
- **Model.** Tripo3D: a generated concept image → image-to-model (1.9M triangles) → reduced to 15k with 2K textures (`reduce.py`) → Tripo's quadruped auto-rig (50 bones) → `build.py`: life size (1.28 m long), the texture islands padded (the dark seam cracks were the black atlas background bleeding in), and seven keyframed animations: idle_snarl, run (rotary gallop), trot, lunge, bite, flinch, death. Sounds are synthesized placeholders (`raw_assets/audio/build_dog_sfx.py`: growls, snarls, barks, bites, yelps, a dying whine). Tripo credits used: 165 for the model, 25 for the rig.
- **Not yet.** A ragdoll (it plays a death and slides with the hit), dismemberment, burning, the slide launch, handlers, recorded sounds.

### 8.9 What was built first (2026-11-15)

The foundation, so the loop can be played on the phone before any of it is final:

- **Data** (`tools/run/gen_pool.py` → `data/run/survival.tres`, the source of truth; `src/run/`): `RunItem` (a gun or a part, its tags, weight, first wave, boss-only flag, Mk I and Mk II overrides for actives), `Doctrine` (baseline body, starting actives, favoured tags), `WaveEnemy` (the roster), `SurvivalConfig`. Every gun and part is in the pool. The parts' own `.tres` files are untouched, so Sandbox plays exactly as before.
- **Marks**: Mk I and Mk II for all eleven actives as in the table in §8.3. `RunItem.active_at(mark)` copies the part and sets the overrides; Mk III is the part itself.
- **The run** (`RunState`): the body as a `BodyLoadout`, the guns, the marks, the drops (§8.4, §8.5) and the boss drop. `SurvivalWaves`: the threat budget, debuts (a new type always shows up on its first wave), caps, lieutenant waves on every fifth wave, the dip after them. First numbers: wave 1 is 3–5 men; waves 1/4/8/12/16/20 bring about 3/8/13/17/20/22 men.
- **The Blue Lantern**, the first new enemy type (data only: `data/enemies/blue_lantern.tres`; SMG, 85 health, wide aim, slow to react, low courage).
- **The loop on Chinatown** (`SurvivalRun`, `SurvivalDirector`, `src/ui/survival/`): **Survival** is first on the main menu, and the old Begin is now **Sandbox**. The kit screen (D-pad ▲▼ row, ◀ ▶ change, A deploy) sits over the menu scene. Waves come in out of sight like the rolling spawns, at most 12 alive. The HUD shows the wave banner and how many are left. After a wave: health and charges refill, then the drop screen pauses the game (◀ ▶, A), then 3 s to the next wave. Lieutenant waves show the boss drop first, on a gold card. On death: the run-over screen (wave, kills, kit, what was taken), then A for the main menu. The pause menu hides the map switch, the enemy toggle and the map cost test during a run. `-- --survival=<doctrine>,<gun>,<active>` (indices) starts a run straight away for tests and captures.
- **Evidence:** `tests/unit/test_run_marks.gd`, `test_run_state.gd`, `test_survival_waves.gd`; `tests/scene/test_survival.gd` plays the loop (kit on the player, wave 1 in and cleared, the choice of two, the item in the body or on the wheel, wave 2, death and the run-over screen, Survival from the menu).

Not yet: bosses (the Incense Master came later the same day, §8.7a), the Dao swordsman and the other new types (the Hatchet Man was built next, §8.8a), theme waves, objective waves, an ammunition economy, any meta-progression, sounds for the drop screens beyond the UI ticks.

### 8.10 Open questions

- **Meta-progression.** Does anything carry over between runs (unlocking guns and actives for the pool, starting doctrines, cosmetics)? Most roguelites need some. Claude's suggestion: unlocks that widen the pool, never raw power.
- **More maps.** One map per enemy theme? What comes after the triad?
- **Health and ammo between waves.** Full refill (now) or partial?
- **Run length.** Endless, or a final boss at wave 25 or 30 with an endless mode after?
- **Passives you didn't choose.** Should auto-picks ever be passives that need a part you don't have yet?
