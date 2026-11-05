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

## M1a.4 — 2026-11-02 — Weapon wheel, reticles, M14/P (waiting for the owner)

Build: `dev-latest` from branch `claude/rail-carbine-weapon-a4bxsa` (manual CI run). The Saiga-12K branch is merged in, so this APK has all five guns.

What's new in the APK:
- **Weapon wheel:** hold **Y** — time slows, push the **right stick** toward a gun, let go of Y to draw it. A quick **tap of Y** swaps back to the gun you had before.
- **Five guns:** Five-seveN, MG42, Saiga-12K (D-pad left/right for buck / slug / Dragon's Breath), RC-6 rail carbine, and the new **M14/P**.
- **Reticles:** seaglass green-blue, **crimson** when you're looking at a dummy. The Saiga's reticle is a **circle** the size of its spread, a **dot** with slugs. The PSO scope and the rail carbine's red-dot ring change colour the same way.
- **M14/P:** black polymer M14 with a pistol grip, stubby foregrip and a suppressor. 7.62×51, semi-auto, 20+1, heavy kick. Aim (LT) through the rear aperture to the front post.

Please try:
1. Hold Y and pick each gun. Is the slow-down (30 %) right, or should the wheel not slow time at all? Is 0.2 s the right hold before it opens?
2. Tap Y to flick between two guns. Does it go where you expect?
3. Sweep the reticle across the dummies: does the crimson read instantly? Is seaglass easy to see on the bright range?
4. Saiga: buck circle vs slug dot. Does the circle size match where the pellets land?
5. M14/P: fire fast at the plates, aim through the aperture. Recoil too much or too little? Does it sound suppressed but still powerful?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## M1b + M1c — 2026-11-04 — Triad enemies, gore, ragdolls, AI, waves, movement (waiting for the owner)

Build: `dev-latest` from branch `claude/m1-gore-enemies-fkq87x` @ 339cd0c, CI run #11 (manual run, GUT 168/168). `graft-debug.apk`, 300 MB. Same five guns as M1a.4.

What's new in the APK:
- **Triad members on the range:** the four target spots hold triad members — Gunmen (black jackets, Type 56), an Enforcer (olive jacket, plate carrier, pump shotgun) and a Red Pole (burgundy jacket, SMG). They turn to face you and react to every hit, but on the range they never fire. A new one walks up 9 s after a kill; bodies stay.
- **Locational damage:** 17 zones. Head and neck kill; legs make them stumble, limp and crawl; a hit to the gun hand often knocks the gun away (and they may put their hands up); gut shots double them over; wounds that go through bleed.
- **Gore** (Pause → Gore: Off / Standard / **Maximum**, Maximum by default): wounds open on the body where each round went in and out, blood sprays out of exits onto the wall behind, mist on head shots, drips, pools under bodies. At Maximum, heavy hits take heads, forearms and shins off: the rail carbine does it in one shot, buck does it up close, and the MG42 chews limbs off.
- **Ragdolls:** they fall the way they were shot and freeze once they settle (at most three move at once).
- **Plates:** the Enforcer's chest plates stop pistol rounds and buck (you'll see sparks and an armour marker); go for the head or use the rail carbine.
- **Wave mode:** Pause → Wave mode: start. Waves come in from the edges of the room, take cover behind the crates, peek and fire bursts (only three shoot at you at once; the first rounds go wide). Near misses make them hide; casualties, gore and you getting close break them: they run, cower, fire blind over cover or surrender. Callouts show as subtitles. You have 200 health that comes back after 3 s out of fire; red arcs show where hits came from. Dying restarts at wave 1. Pause → Wave mode: stop brings the range back.
- **Movement:** B while sprinting **slides** (A out of it hops); jump at a wall while pushing forward to **wall-run** along it (A jumps off); A at a ledge (the three blocks on the west wall: 1, 1.5, 2 m) **mantles** onto it.

Please try:
1. Range: shoot a Gunman in the chest with the pistol, then the arm. Do the wounds read? Shoot one in the hand: does he drop the gun?
2. Rail carbine to a head, then to a forearm (Maximum gore). Too much? Not enough?
3. MG42 at a target's legs. Saiga buck at 3 m.
4. Enforcer: pistol to the chest (plate), then the head.
5. Wave mode: play three waves. Are they too accurate or too passive? Does cover-peeking read? Do the callouts help?
6. Slide into a crowd, wall-run along the free-standing wall on the west side, mantle the blocks.
7. Watch the overlay with 8–12 enemies and a few bodies: does it hold 60?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## M1d — 2026-11-04 — Chinatown docks map (waiting for the owner)

Build: `dev-latest` from branch `claude/chinatown-docks-map-d2ojwh` @ 2d6ebea, CI run #13 (manual run, GUT 176/176). `graft-debug.apk`, 356 MB. The game now starts on the new map; the old test range is still there under Pause → Map.

Rebuilt 2026-11-05: the 356 MB APK wouldn't install on the owner's phone ("problem parsing the package"). The file on GitHub verified fine, so the phone's copy was most likely incomplete. `dev-latest` is now branch `ccr-0ed172e0-34bgbk` @ b245573, CI run #15 (GUT 176/176), **222 MB**: the four 4K guns are capped to 2K on import (looks the same at 720p). Two flaky tests fixed on the way, one of them a real bug: an arriving enemy could be nudged into view at a doorway.

What's new in the APK:
- **Chinatown docks at night, in the rain.** A city block on the harbour: the quay with a moored fishing boat (you can board it over the gangplank), a pier, containers and a crane; the Pier 3 cold store; the fish market hall with stalls of fish on ice under red lamps; Harbour Street with lanterns strung overhead, neon and bilingual shop signs, a paifang gate at one end; the Sea View restaurant (walk in the front, through the kitchen and out the back); a narrow alley and the back alley behind the shops; a tenement gallery you can reach by the stairs on the quay side.
- **Enemies on a rolling clock:** 8 triad members at the start; whenever fewer than 4 are still fighting, 3 more arrive. They always come in somewhere you can't see (doorways, alley ends, the boat, the cold room, behind the containers), at least 14 m away, and they know roughly where you are. The HUD shows kills and how many are still hostile. Pause → Enemies turns them off and on.
- **Look and sound:** baked night lighting (every lamp, lantern, neon sign and lit window lights its surroundings), wet streets with puddles and ripples, rain that stops under roofs, steam from drains and kitchen vents, a lit skyline across the bay, light streaks on the water. Rain, harbour water, a ship's horn, neon hum, an extractor fan and a little radio in the restaurant.

Please try:
1. Walk the whole map once with enemies off (Pause → Enemies: off). Anything that looks wrong, broken, floating, too dark or too bright? Which spot do you like most?
2. Turn enemies on and play for ten minutes. Do they ever appear in front of you? Is 8 → "3 more under 4" the right pace?
3. Fight through the market (low cover), the restaurant (close range) and the street (long sight lines). Which works best, which worst?
4. Watch the overlay: FPS on the street looking down its length, in the market, and on the quay looking at the boat. Does it hold 60?
5. Does the rain feel right (too much, too little)? Are the streets wet enough?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## M1d playtest — 2026-11-05 — owner's notes on the Chinatown build

Owner (paraphrased from voice notes): tried the MG42, pistol and railgun earlier; this time the shotgun and the M14 too: "they're both great." Loves the PSO reticle on the slug Saiga: "a scoped slug thrower like that, wielded by an augmented operative... looks fucking awesome." Problems:
- **29 fps on the Chinatown map** (28–29 consistently); the range was buttery smooth, so the map is the cost. Don't reduce fidelity; optimise how the world is loaded and drawn for this phone. The environment has a PS2 / early-2000s PC vibe (black sky) next to detailed weapons; acceptable if it runs well, but polish and a cohesive style are welcome.
- Shooting kept playing **the range's metal clinking sound**.
- **No audio for enemies dying.**
- **Enemies look small** on the phone screen and **don't stand out** from the environment ("think Halo CE").
- **Movement doesn't feel smooth**; "it feels weird interacting with the world." The character should feel like a supremely dexterous super soldier.
- Start the **augmentation foundation**: the base player model (a black synth suit / carapace, like the suit Lex Luthor wears under the mech in Injustice); passives and actives change the look.
- First active: **time slowdown on LB**, press on / press off or until the points run out; the points refill over time like health. No holding.

## M1e / M2 start — 2026-11-05 — Playtest fixes, RX-9 time slowdown, the operative (waiting for the owner)

Build: `dev-latest` from branch `claude/chinatown-playtest-feedback-l1tyox` (manual CI run; details below once it's built). GUT 197/197 in the cloud.

What's new in the APK:
- **Faster Chinatown.** The sky no longer rebuilds its lighting every frame (and isn't black any more: a rain-cloud deck lit amber and violet by the city); the map is cut into small cells so the phone skips what's off-screen or behind buildings; the water, puddle and steam effects are much cheaper; bloom drops its most expensive pass. **Resolution: auto** (pause menu) lowers the 3D resolution only when the phone can't hold 60, and climbs back when it can.
- **Map cost test** (pause menu): stand still for ~40 s; it times the map with everything on and then with each effect off, and shows a table. **Please screenshot it** — those numbers tell me exactly what to cut or keep next.
- **Sounds:** the metal clink was ricochets playing the range's steel ping (concrete ricochets at shallow angles, so most misses on the street did it) and bollards/lamp posts using the range-target metal. Now: the surface's own impact plus a short ricochet whine; posts sound like heavy steel; brass casings are quieter. **Enemies die out loud:** screams, choking on neck/chest hits, a last breath on some head shots, groans when they bleed out or crawl.
- **Enemies:** 8 % bigger, lighter role colours, and a cool rim light that grows with distance so they outline against the dark.
- **Movement:** curbs, door sills and stair treads no longer stop you; the camera eases over them. **Full tilt forward sprints by itself** (L3 still works).
- **LB: RX-9 Reflex Overclock (time slowdown).** Tap LB: the world drops to 30 % while you move, shoot and reload at 65 % (2.2× faster than everyone else); looking stays at full speed. Colour drains, sound muffles and drops, hits throw bodies harder. Tap LB again to drop out, or it ends when the bar (above your health) is empty. The bar refills after 2 s.
- **View button: body status.** The operative, your base body in the black carapace (first pass), on a turntable, with the installed parts, mass, power, heat, capacity and stats.

Please try:
1. Chinatown with the overlay on: FPS in the street, the market and the quay, with enemies. Then **Pause → Map cost test** and screenshot the result.
2. Shoot along the street and at a bollard: any metal clink left?
3. Kill a few enemies with head, neck and body shots; set one on fire; leg one and let him crawl. Do the voices work, or do they sound synthetic in a bad way?
4. Are enemies easier to see now? Big enough?
5. Run along the street onto the sidewalks, up the gallery stairs, through doorways. Does movement feel better? Is auto-sprint welcome or annoying?
6. RX-9: is 30 %/65 % the right feel? 8 s too long or short? Does the refill rate feel like health?
7. Press View: what do you think of the suit as a starting point?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:
