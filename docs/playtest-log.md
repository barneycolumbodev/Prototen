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
