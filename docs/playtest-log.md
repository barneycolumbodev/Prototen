# Playtest log

One entry per milestone build (CLAUDE.md §12): the APK tested, what was tried, what felt right or wrong, and numbers measured on the phone.

<!-- Template
## M? — YYYY-MM-DD — build <commit>
- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:
-->

## M0 — 2026-11-01 — first build (waiting for the owner)

What's in the APK:
- Test room: two levels (mezzanine + ramp), cover crates, 1.0/1.5/2.0 m ledges, a wall-run wall, a doorway. Greybox grid shows scale.
- Controller movement: walk, sprint (click L3; ends when you stop pushing forward), crouch (hold B), jump (A). Look on the right stick with a radial deadzone, response curve and turn acceleration when you hold full tilt.
- Debug overlay (top left) and pause menu (Menu button).

Please try, then send a screenshot of the overlay:
1. Walk around for a minute. Is the look speed too fast/slow? Try the three look curves (pause → Look curve).
2. Pause → Run benchmark. Don't touch the controller for 20 s.
3. Pause → Renderer → Compatibility. Close the app fully, open it, run the benchmark again.
4. Screenshot the overlay: it shows both benchmark results side by side.
5. Leave it running 20 minutes; note if it gets hot or the FPS drops.

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## M1a — 2026-11-01 — core gunplay (waiting for the owner)

What's in the APK:
- Suppressed Five-seveN: 20+1, semi-auto with a trigger buffer. **Hold LT** to aim down the sights, **RT** to fire, **X** reload (tactical keeps the chambered round; empty is longer and releases the slide), **Y** or a trigger pull cancels a reload. Firing out of a sprint drops the sprint first.
- Rounds are real projectiles from your eye: drop, drag, travel time, penetration by material and energy, ricochets off steel at shallow angles.
- Recoil is moderate: the view kicks ~1° and springs back; a little climb stays. Slide cycles, shells fly, flash/light/smoke, layered suppressed shot with a room tail, hit/headshot/kill confirms, hit-stop on headshots and kills, rumble.
- Range in the test room: steel poppers (one on the mezzanine at 25 m), four 13-zone dummies (readout shows zone, damage, THROUGH), a penetration lane (drywall, plywood, car door, pine timber, concrete block, AR500) with witness cards and counters, a drywall wall and a plank fence that shoot apart, cans/bottles/crates.
- Pause → **Gun tuning**: live sliders for recoil, springs, ADS, accuracy, ballistics, hit-stop and aim assist. Saved on the phone. **Copy values** puts them on the clipboard.

Please try:
1. Shoot the poppers from spawn, hip and aimed. Does aimed fire feel dead-on? Is recoil moderate enough?
2. Put a tight group into the drywall wall and the fence until they break open, then shoot the dummy behind through the hole.
3. Fire a few rounds through each lane panel and read the signs: which ones let rounds through?
4. Headshot a dummy: is the hit-stop too long, too short, or right?
5. Tactical reload, then cancel a reload by pulling the trigger. Empty the gun and do an empty reload.
6. Tune anything that feels off (pause → Gun tuning), then Copy values and paste them back to me.
7. Screenshot the overlay: the range line shows shots, hit %, headshot % and time between shots.

- Device / renderer / settings: Moto G 5G (2025), controller.
- Measured: —
- Notes from the owner: "Feels good." The way the gun is held looks wrong: the crosshair sits above it and looks weird. Gun tuning could be highlighted but not opened. Stick look is a bit too sensitive, hard to aim (first time playing a mobile FPS on a controller).
- Follow-ups: all three fixed in M1a.1 (see docs/m1-gunplay-plan.md, "Playtest 1").

## M1a.1 — 2026-11-01 — MG42 + playtest fixes (waiting for the owner)

Build: `dev-latest` from branch `claude/mg42-light-gun-gu416b` @ 3fad758, CI run #5 (manual run; CI only builds `main` on push). 117 MB: the MG42's 4K textures ship in both ETC2 and ASTC. Throwaway signing key, so uninstall the old APK first.

What's new in the APK:
- **MG42/A**: press **Y** to switch between the pistol and the MG42. Chrome and black steel, 7.62×51, 1,200 rpm, 150-round belt, tracer every third round. You move slower with it out, hip fire sprays (the cone grows the longer you hold the trigger), aimed fire (hold LT) is tight. **X** reloads the belt: the feed cover opens, the box comes off and on, the cover slams shut.
- Pistol and MG42 sit lower right; the crosshair is clear of the gun and thinner.
- Pause menu: **A** presses, **B** goes back. Gun tuning opens and tunes the gun in your hands (switch with Y to tune the other one).
- Look is about 30 % slower. Pause → **Look speed** (press left/right on it) from 50 % to 150 %.

Update (same day): the pistol model was rebuilt to the MG42's standard, olive finish kept (`docs/previews/pistol_57_v2.png`). New APK on `dev-latest`.

Please try:
1. Pause → Look speed. Find a speed you like and tell me the number.
2. Switch to the MG42 (Y). Hold RT on the drywall wall and the plank fence. Do they come apart fast enough?
3. Hip fire vs aimed (hold LT) at the poppers. Is hip fire too loose, or not loose enough?
4. Walk and sprint with it out vs the pistol. Is the slowdown noticeable but fair?
5. Reload the MG42 (X). Does the cover/box animation read?
6. Watch the overlay FPS while firing long bursts. Does it hold 60?
7. Pause → Gun tuning with the MG42 out, tune anything, Copy values and send them back.

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## M1a.2 — 2026-11-02 — Saiga-12K (waiting for the owner)

Build: `dev-latest` from branch `claude/saiga-12k-shotgun-r43ntd` @ d06aaba, CI run #8 (manual run). `graft-debug.apk`, 175 MB (the Saiga's 4K textures ship in both ETC2 and ASTC, like the MG42's). Not playtested yet.

What's new in the APK:
- **Saiga-12K**: **Y** now cycles pistol → MG42 → Saiga. Semi-auto 12-gauge, 10+1, milled black steel, curved magazine, vertical foregrip, folding stock.
- **Shell types on the D-pad**: right = next, left = previous: **00 Buck** (red tape on the magazine), **Slug** (green), **Dragon's Breath** (orange). The HUD shows `00 BUCK > SLUG` while it's coming. Tap twice quickly to skip one. The gun swaps the magazine and racks the old shell out (you'll see it fly).
- **Slugs mount the PSO-style 1x optic.** Hold LT to look through it: illuminated chevron, small holdover marks for 100/200/300 m, rangefinder curve lower left.
- **Dragon's Breath** throws a jet of burning embers about 50 m. Dummies catch fire and burn down, and the crates and wooden fence catch small fires.

Please try:
1. Buck at the dummies from 5 m, 15 m and 30 m. Does the pattern feel right? Too tight, too loose?
2. Switch to slugs (D-pad right) and shoot the steel plates through the optic. Does the scope view work for you, or would you rather keep the gun model visible?
3. Dragon's Breath at a dummy and at the wooden fence. Is the flame big enough? Does the burn feel good?
4. Swap loads mid-fight: tap D-pad, then pull the trigger before the new magazine is in (it should fire the old shell), and again after (it should fire the new one).
5. Recoil: buck vs slug vs Dragon's Breath. Too much, too little?
6. Watch the overlay FPS while firing Dragon's Breath at the fence. Does it hold 60?
7. Should the optic be on the gun for every load, or only with slugs as now?
- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## M1a.3 — 2026-11-02 — RC-6 "Lance" rail carbine

Build: `dev-latest` from branch `claude/rail-carbine-weapon-a4bxsa`, CI run #9 (manual run). This replaces the Saiga-12K build that was on `dev-latest` (branch `claude/saiga-12k-shotgun-r43ntd`, PR #3); the two branches haven't been merged together yet.

What's new in the APK:
- **RC-6 Lance**: press **Y** twice from the pistol (pistol → MG42 → rail carbine). A bullpup railgun: 7 g tungsten slug at 2,600 m/s (≈24 kJ). It goes through steel plate, walls and bodies; one torso hit kills; every shot leaves a blue-white trail.
- **Capacitor:** after each shot the gun recharges (rising whine, then a tone; the glow strips and the HUD bar fill). Fire fast and each shot has less energy (quieter, less kick); wait ¾ s for the full hit.
- **Heat:** spam RT and the rails overheat: three beeps, the top shroud lifts and steams, and it can't fire for 1.6 s. Reloading still works while it vents.
- **Aim (hold LT):** reflex sight with a ring reticle, 1.6× zoom.
- **Reload (X):** the top magazine slides back and off.
- Pause → Gun tuning with the rail carbine out has a **Railgun** section (charge time, power when fired early, heat, vent time, trail).

Please try:
1. Switch to the rail carbine and put a slug through the steel panel in the penetration lane, then through a dummy behind cover.
2. Tap fast vs pace your shots: can you feel and hear the difference in power? Is ¾ s to full charge right?
3. Spam until it overheats. Is the vent too punishing, or not enough?
4. Aim at the poppers: is the ring reticle clear? Is 1.6× too much zoom?
5. Look at the gun: P90 + Halo 4 railgun + Tau, does it read? Colours (light ceramic, graphite, cyan glow) OK?
6. Does it sound unique? Which part do you like least: the crack, the thwack, the charge whine, the tail?
7. Watch FPS while firing quickly (trails and impact effects are new).

Owner (2026-11-02): "The carbine looks good." Asked for a weapon wheel to carry both the shotgun and the rail carbine, a circle reticle for the shotgun (a dot with slugs), seaglass reticles that turn crimson over an enemy, and an M14-style battle rifle (see M1a.4).

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:
