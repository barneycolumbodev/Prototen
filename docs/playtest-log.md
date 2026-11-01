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

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:
