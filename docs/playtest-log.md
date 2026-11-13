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

Build: `dev-latest` from branch `claude/mg42-light-gun-gu416b` @ 3fad758, CI run #5 (manual run). 117 MB: the MG42's 4K textures ship in both ETC2 and ASTC. Throwaway signing key, so uninstall the old APK first.

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

Build: `dev-latest` from branch `claude/chinatown-playtest-feedback-l1tyox` @ 5c79483, CI run #16 (manual run, GUT passed). `graft-debug.apk`, 225 MB. GUT 197/197 in the cloud.

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

## M2 — 2026-11-05 — The operative, second pass (waiting for the owner)

Owner on the first pass: "technically viable, but it has zero artistic inspiration... meant to be this sleek, baseline, polymer, badass look for the soldier that we can build on top of, but instead it looks like a crash test dummy."

What changed (design §3.4a; previews `docs/previews/operative.png`, `operative_helmet.png`, `body_status.png`):
- **Silhouette:** heroic proportions instead of the blobby egg-headed dummy: broad shoulders and traps, V-taper, narrow ribbed waist, thick neck in a high collar.
- **Helmet:** faceted faceplate with a V jaw and keel, recessed chevron visor with a lit lower lip, ear pods, nape guard, respirator, crown panel lines.
- **Two blacks:** matte graphite polymer suit (seams, ribbed flex zones, striated flanks) under gloss-black faceted plates (breastplate and sternum keel, chevron abdominal lames, hip band, layered pauldrons, keeled forearms and shins, diamond knees, armoured boots, six-node spine). Light only in small accents; the rings round the wrists, waist and neck are gone.
- **Status screen:** relaxed stance (elbows bent, fingers curled), a studio sky that the gloss plates reflect, softer lights so the suit reads black. RX-9's hardware moved to the back of the collar and the nape guard (it was buried inside the new collar and helmet).
- Asset: one skinned mesh, one material, 34.4k triangles, 2K baked textures (ETC2/ASTC). Cloud: GUT passes; screenshots are from the compatibility renderer (no Vulkan in the cloud container).

Please try: press View and turn the operative with your eyes on the phone, not just the previews. Is this the right starting point for the baseline soldier? What would you push further: more armour or more bare suit, glossier or more matte, more or less light?

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: first-person arms in the same suit (the gloves are still the older olive-sleeve set).

## M2 — 2026-11-05 — The operative, third pass: undersuit (waiting for the owner)

Owner on the second pass: much better, but it reads as 80s Star Wars (Death Troopers). Wanted: sleek and modern, substantially less armour, an undersuit that augments and armour load on top of (like Halo's techsuit under the Mjolnir); the helmet a little smaller with the same design; a polarized visor.

What changed: all the carapace plates are gone except a slim collar, low spine nodes and the boots. The suit carries the look with satin compression panels over the muscle groups on a matte black base. Flat gunmetal hardpoint pads (shoulders, forearms, thighs, sternum) mark where parts dock. Helmet at 93 %, same design; the visor is now a dark violet-tinted mirror. 22.9k triangles. Previews: `docs/previews/operative.png`, `operative_hero.png`, `operative_helmet.png`, `body_status.png`.

- Notes from the owner:
- Follow-ups: first-person arms in the same suit.

## 2026-11-07 — APK "package appears to be invalid"

Owner: the latest APK (CI run #17, 7a0f3e7) wouldn't install: "App not installed as package appears to be invalid".

Cause: not the file. The release copy verifies (zip intact, v1/v2/v3 signatures, versionCode 17, sha256 matches GitHub's digest), and the phone's installer read the name and icon from it, so the download was complete. CI's run annotation says the keystore secrets aren't set, so every run signed with a newly generated key; Android refuses an update whose signature differs from the installed copy.

Fix: CI now signs with one fixed debug key committed at `tools/android/graft-debug.keystore` (debug only). **One last time:** uninstall GRAFT, then install. After that, new builds install over the old one.

## 2026-11-07 — Map cost results, the ding, slide knockback, three actives, GX-4 Gauss arm (waiting for the owner)

Owner's notes on the last build: "the game felt genuinely satisfying to kill enemies for the first time." Map cost test (screenshot, Moto G, resolution auto had dropped to 60 %): all on GPU 17.9 ms / frame 21.5 ms; bloom off −3.2 ms GPU (frame 18.4); reflections, water streaks, ripples, rain, steam, fog each within ±0.3 ms (noise). Average ~46 fps in play; the picture looked grainier (the auto resolution sitting at its 60 % floor). Still dings on every shot. Wants: a longer slide with a moderate knockback into enemies; three actives on LB, picked with the D-pad; the next active, a prosthetic arm that transforms into a Gauss cannon (10 shots, spiral gore, loud, overpenetrates).

What changed:
- **Bloom off by default** (Pause → Bloom to compare). Cloud captures of Chinatown with and without it are nearly identical; on the phone it was 3.2 ms of 17.9. With that headroom the auto resolution should climb back up, which is what the grain was. The world shader also uses the cheaper diffuse model (its lighting is baked, so nothing visible changes). The map cost test now also times "gun hidden" and the map at 100 % and 70 % resolution, so the next screenshot shows how much the frame depends on pixels.
- **The ding:** every shot ejects a casing, and its bounce was a pure 3–6 kHz ring, so each shot was followed by a "ting". Casings now tick once, quietly and dull; shutter and steel-post hits are a dead thwack and rattle instead of a clang; thin metal is a flat tsk; ricochets are a short hiss and only 40 % of them are heard.
- **Slide:** a tap of B runs the whole slide (~18 m from a sprint); B again, A or stick back ends it. Sliding into an enemy shoves him ~1.5 m and staggers him (scales with mass × strength × speed).
- **Actives:** D-pad left/down/right picks which active LB uses (RX-9 on left, GX-4 on down). Shell type moved to D-pad up. RB is free.
- **GX-4 Gauss arm** (design §3.4): select with D-pad down, LB. Gun down, open hand up, fist, the fist splits into a fork, forearm opens, rails and coils slide out, fins up (1.6 s). RT fires; 10 rounds on the forearm LEDs and the HUD; goes through everyone in line; corkscrew beam and blood spiral, the bodies electrocuted. LB folds it away; empty, it folds by itself; rounds come back while folded.

Build: `dev-latest` from branch `claude/map-cause-perf-combat-nt6g7g` @ 40ff0de, CI run #19 (manual run, GUT passed), `graft-debug.apk` 249 MB. GUT 209/209 in the cloud. Installs over the previous build (same fixed debug key).

Cloud evidence: GUT (new: slide distance, B cancels, slide shove, knockback scaling; arm deploys and stows the gun, transforms fully, a slug kills two men in line, empty → folds and the gun returns, LB early keeps rounds, RX-9 and the arm together). Captures: `docs/previews/gx4_gauss_arm_sequence.png` (Blender), `gx4_gauss_arm_ingame.png` (in game, software renderer, daylight test range).

Please try:
1. Pause → Map cost test in Chinatown again and screenshot it. Does FPS hold nearer 60 with bloom off? Does the picture look sharper? Flip Bloom on and off: can you see a difference?
2. Shoot along the street, at shutters and posts: any ding left?
3. Slide (tap B) into an enemy. Is the slide length right? Is the shove too weak or strong?
4. D-pad down, LB: watch the arm transform. Too slow or too fast? Fire through a group. Is the beam and the corkscrew readable at night? Is the shot loud enough?
5. RX-9 (D-pad left, LB), then the arm (D-pad down, LB) while time is slowed.

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups: the arm's materials are flat colours (no baked textures yet); first-person suit arms for the guns; the arm on the full body (body-status screen).

## 2026-11-08 — Passive augments: core stats, the library, the loadout screen (waiting for the owner)

Owner: hasn't played the GX-4 build yet. Asked for the passive system: core stats (mobility, melee, gun proficiency by type, hitbox size, slide knock power from momentum and strength), a large library of grounded passives that each trade one thing for another, stat requirements and stat effects on actives (connectivity for drones and their range), a few parts with finished looks and neutral placeholders for the rest.

What changed (design §3.6):
- **Core stats:** about 35, in eight groups, each read by gameplay: movement (speed, agility, jump, slide, wall-run, climb), strength and structure, melee, firearms (recoil, aim, reload, handling, stability, proficiency for handguns, shotguns, rifles, heavy weapons), signature (silhouette, signature, noise: enemies see and hear you by them), neural (processing, connectivity, perception), power and heat.
- **Relationships:** load = mass ÷ usable strength slows heavy bodies; strength is capped by structure; slide and melee impact come from mass × strength × impact; heat raises your signature and stops regen when full; an empty power reserve stops powered actives.
- **37 passives** in 15 body locations, each with a tradeoff; some need stats from others (HM-5 muscle needs a reinforced skeleton, the FC-1 link needs connectivity, the spinal bus needs processing). Parts that don't meet their requirements go offline.
- **Actives read stats:** RX-9 needs processing (SA-2) and gets faster and longer with more; GX-4 needs structure (TL-3) and kicks less on a stronger frame, recharges faster with spare power.
- **R3 strike** (new): a lunge and a blow; how hard depends on strength, mass, impact and melee power.
- **Loadout screen** (View): browse parts per body location, the body and every number preview them, A installs, X removes, presets at the top (Operator, Ghost, Juggernaut, Marksman), LT zooms, right stick turns, B applies. Saved between sessions.
- **Finished hardware:** CT-7 trauma plating, HS-5 heat sinks, NL-3 cortical uplink, KD-2 dampers (baked textures). The rest are gunmetal placeholders.
- **The default loadout changed** to the Operator: TL-3 skeleton, SA-2, EM-2 myofibrils, HS-5, RX-9, GX-4. With EM-2 you run about 10 % faster than the last build.

Please try:
1. View → browse the Torso row to CT-7, then the presets. Does the body look right? Are the numbers readable on the phone?
2. Play each preset in the wave mode. Do they feel different? Juggernaut: slide into enemies (should break them), hip-fire the MG42. Ghost: can you get close before they notice?
3. R3 near an enemy: does the strike land and feel heavy?
4. Take SA-2 out: RX-9 should show OFFLINE on the HUD.

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: finished hardware for more parts; first-person arms showing forearm parts (HS-5 fins, EM-2 vents); a drone active using connectivity.

## 2026-11-09 — Passive hardware: 17 more finished parts (waiting for the owner)

Owner: "replace the placeholder assets, at least a decent amount of them, with new assets that are in line with all the other ones... that match the passive augmentation."

What changed (design §3.6, "Finished hardware"):
- **16 more passives modelled, baked and mounted** (20 of 37 now), plus the **RX-9** module: EM-2, TL-3, SA-2, DL-1, HM-5, TN-9, FC-1, VS-1, PC-3, SP-6, KS-2, RP-2, OB-5, MR-1, CM-1, DG-3. Same pipeline and look as CT-7/HS-5/NL-3/KD-2: Blender generators, modelled on the operative, HIGH → LOW bake into 1024² base colour / ORM / normal / emission, mounted on the bones.
- **Every preset is now fully finished**: Operator, Ghost, Juggernaut and Marksman show no placeholders. Parts in the same preset were built around each other (DL-1 over CT-7, RX-9 between the NL-3 blades, five forearm parts sharing the forearm).
- The 9 remaining placeholders are minor parts (ER-2, TG-6, IR-3, NW-4, AB-1, SR-3, GP-1, LF-8, SB-2); 8 internal parts have nothing to show.
- RP-2's text now says shoulders and sternum (it had said forearms; the forearms are taken by the arm parts).
- Gameplay numbers are unchanged.

Cloud evidence: GUT 235/236 in the cloud (the one failure is the existing pistol camera-kick test, which samples the peak frame by frame and missed its lower bound by about 1 %; it passed on rerun; no stats changed). The passive asset test now covers all 20 parts (bones, triangle budget 300–6000, baked textures, VRAM compression) and checks every preset part with hardware uses a finished model. Previews: `docs/previews/passives_overview.png` (Blender close-ups) and `docs/previews/<id>.png`; in game: `docs/previews/passives_ingame.png` (the four presets on the loadout screen, cloud software renderer).

Please try:
1. View → Presets: look at each of the four builds, front and back (right stick turns, LT zooms). Do any pieces look wrong, float, or clip the suit?
2. Which three parts look best and which look worst? That decides what gets a second pass.
3. Juggernaut: turn to the back. Does the DL-1 frame and the ammo chute read as a machine-gun mount?

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: the 9 remaining placeholders; first-person arms showing forearm and hand parts (EM-2, HS-5, TL-3, FC-1, DG-3, KS-2, TN-9); a second pass on whatever the owner flags.

## 2026-11-10 — Seven active parts and the colour customizer (waiting for the owner)

Owner: "it's time to instantiate the ability keys, the active augmentations. Mono filament razor whip, shoulder launcher suicide drone, ultra prehensile nanotech mesh arm thing that grabs and can throw enemies. I also want a full part by part color customizer for my character. I need at least 4 more active augmentations added in this pass... with animations and models and stuff."

What changed (design §3.4b, §3.7):
- **Seven new actives**, nine in all, any three on the D-pad (the order you install them: left, down, right). Each needs stats from the passives and changes with them:
  - **MW-7 Monofilament Whip** (right arm; needs processing ×1.10): LB draws it. Hold LT and the right stick swings it; RT lashes across the crosshair. It cuts what it crosses.
  - **NT-5 Prehensile Mesh Arm** (left arm; strength ×1.15, structure ×1.20): RT grabs the man under the crosshair and holds him in front of you; RT again throws him.
  - **BW-6 Bulwark Fan Shield** (left arm; structure ×1.15): stops rounds from the front until its integrity is gone; R3 becomes a shield bash.
  - **SD-3 Shrike Drone Pod** (back; connectivity 3): fly it from its camera, RT detonates. Range = connectivity × 40 m.
  - **AD-2 Arc Projector** (back; 600 W supply): LB fires a chaining arc from a shoulder emitter; the gun stays up. 18 kJ of reserve per arc.
  - **KR-5 Ram Thrusters** (back; structure ×1.30): a dash through people; the hit scales with mass, strength and impact.
  - **TC-4 Thermoptic Shroud** (skin; 420 W cooling): invisible beyond 3 m; firing breaks it; it traps heat.
- **Two parts at once by hand**: the whip or the Gauss arm in the right hand with the shield or the mesh arm on the left. The gun goes away while either hand is busy.
- **Three new presets**: Reaper (whip, shield, ram), Handler (drone, arc, RX-9), Wraith (shroud, mesh arm).
- **Colours page** (View, then LB): every suit piece and every installed part's hardware and lights; a palette plus hue / saturation / brightness / finish sliders. The first-person arms follow it.
- Models: five first-person models with deploy clips (the whip arm, the braided mesh arm, the fan shield, the shoulder emitter, the drone) and baked hardware on the body for all seven. 42 new sounds.

Cloud evidence: `tools/check.sh` passes, 258 tests (22 new: `tests/scene/test_actives.gd` plays each part in the test room: a lash cuts a man, the arm seizes, holds and throws one who dies where he lands, the shield stops a round from the front and not from behind and breaks, the drone kills with its warhead and the view comes back, the link drops out of range, the arc chains to a second man and takes 18 kJ, the ram goes through a man, the shroud hides and a shot breaks it, whip and shield run together; `tests/unit/test_actives_data.gd` covers slots, mounts, requirements, colours and the region maps). The pistol camera-kick test (frame-timing sensitive, noted on 2026-11-09) failed once while Blender bakes were using the CPU and passed on an idle machine. Captures with the Mobile renderer on the cloud's software Vulkan: `docs/previews/actives_ingame.png` (each part in the test room: lash, grab, throw, shield, drone view, detonation, arc, ram, shroud), `docs/previews/colours_ingame.png` (the Colours page, the painted operative seen from the drone, painted first-person arms), `docs/previews/actives_loadout.png` (the three new presets and the Actives row), `docs/previews/<id>_hero.png` (the first-person models' deploy clips), `docs/previews/<id>_body.png` (the hardware on the body). Not checked in the cloud: how any of it feels on a controller, sound levels, frame time on the phone (the drone view adds the operative's full body, about 35k triangles plus parts, while you fly).

Please try (View → Presets has a build for each):
1. **Reaper**: D-pad to the whip, LB. Hold LT and sweep the right stick through a group; then RT lashes without LT. Does steering it feel right, or should the stick move it faster or further? Is the filament easy enough to see?
2. **Reaper**: shield up (LB on its slot) with the whip out. Walk into fire. Then R3 someone with the shield up, then the ram thrusters through a group.
3. **Wraith**: raise the shroud, walk round a squad, grab one with the mesh arm (RT) and throw him at another (RT). Does the held body sit in a good place on screen?
4. **Handler**: launch the Shrike. Is it flyable (speed, turning)? Is 22 s enough? Then the arc projector into a group.
5. **Colours**: View → LB. Paint a few pieces. Do the plates take colour the way you expect? Anything that should be its own piece and isn't?
6. Which of the seven is weakest? That one gets the next pass.

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: left/right and pattern options for colours; forearm hardware on the first-person gun arms; enemies that react to the drone; RX-9 knocking living enemies into ragdolls; heat and barrel changes for the MG42 (M3).

## 2026-11-11 — Movement overhaul, Soldier of Fortune gore, loadout grid (waiting for the owner)

Owner: "an overhaul of movement... smooth and buttery... how much control the player has... It still feels a little bit jank"; "the gore system implemented in the detailed way in which it was supposed to... Soldier of Fortune, with decapitations, dismemberments, gibbing, but like based on ballistic impact and location"; "fix the menu... set it up as a menu where all the options are laid out and you can just click on the one you want... if it tells you, oh, you need this, you can just go look and click on it real quick."

What changed:
- **Movement** (design §5.7): the camera is drawn between physics ticks, so it moves evenly when the frame rate dips; turns keep their speed (they used to lose about 30 % through 90°); starts and stops ease; speed from a slide-hop, wall jump or dash carries after landing instead of being braked away; air steering without losing speed; tap A for a short hop, hold for full height; sprint holds while strafing forward; B just before landing slides on touchdown; mantles keep your speed; smoother wall-run entry; landing dip, sprint and slide FOV, slight strafe lean. Every value is on Pause → Tuning (Movement section) and copies out with "Copy values".
- **Gore** (design §5.5, Maximum only): the body comes apart at the joint nearest where the round lands: head, arm at the upper arm, forearm, hand, leg above the knee, shin. What it takes depends on the energy the round leaves plus what it arrives with. A pistol round never takes a limb off by itself; a rail round takes any limb it passes through; buckshot does it up close, not at range; MG42 and M14 fire saw limbs off over a few rounds. Way past the threshold, the piece is destroyed instead of flying off. **Changed:** at Maximum, the GX-4 into a torso now bursts the man instead of leaving the electrocuted corpse; say if you'd rather keep the arcs. A Gauss slug to the torso, a drone blast up close, or a corpse under sustained fire bursts the whole body: head and limbs, ribs, spine, organs and gut fly, blood goes over everything near. Losing a leg puts him on the ground crawling; losing an arm makes him cower or run; stumps spurt.
- **Loadout screen** (design §3.6): every part is a tile on one screen, grouped by body location, with presets and the nine actives at the top. D-pad or tap to select (the body and numbers preview it); A or a second tap installs or removes; X moves an active's D-pad slot. When a part needs a stat it doesn't have, the card names every part that supplies it (tap one to go there), those tiles get an amber outline, and **RB** jumps straight to the one that fixes it. The HUD's OFFLINE line names them too, and View opens on the offline part.

Cloud evidence: `tools/check.sh` passes, 291 tests; new tests in `tests/unit/test_movement_config.gd`, `tests/scene/test_movement.gd`, `tests/scene/test_gore.gd`, `tests/scene/test_loadout.gd`. Captures: `docs/previews/loadout_grid.png`, `docs/previews/loadout_grid_fix.png` (phone resolution 1604×720), `docs/previews/gore_lineup*.png`, `docs/previews/gore_burst.png`, `docs/previews/gibs.png`. The gore captures and `loadout_grid_fix.png` use the Mobile renderer on software Vulkan; in the cloud, the test room with five dismembered bodies and a burst in view drew 197 draw calls (budget 150), so frame rate after bursts is the thing to watch. Not checked in the cloud: how movement feels on the controller, and frame time on the phone with several bursts in view (up to 32 gibs, one draw call each).

Please try:
1. **Movement** in Chinatown: sprint and snap 90° turns, slide-hop and keep running, wall-run and jump off, vault a ledge at a run. Smoother? Too slippery or too twitchy anywhere? If something's off, change it under Pause → Tuning → Movement and send the copied values.
2. **Gore** in the range (gore on Maximum): rail carbine into an upper arm, a thigh and a neck; Saiga at arm's length to a forearm; MG42 on a corpse; the Gauss arm into a chest. Does what comes off match where you hit? Too much or too little?
3. **Loadout**: View, take SA-2 out, select RX-9, press RB. Did it go straight to the fix? Can you read the tiles on the phone?
4. Frame rate in the range after a few bursts.

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: the burst's red mist is strong on the Mobile renderer, so say if it's too much; gore on the player's own melee and the whip (they use the same cuts already; tune blade_factor by feel); torso halves (a waist cut) if wanted; vertex-coloured gib pieces could get baked textures.

## 2026-11-11 — Gore second pass: pieces come off with every gun, blood as drops (waiting for the owner)

Owner, after playing the first gore pass: "The recent gore additions don't seem to have taken effect in the gameplay, they do cower or crawl away sometimes, but no heads, arms, or anything else is coming off, also the blood is very simple and not simulate accurately, rather but obnoxious light red clouds."

What was wrong:
- **Nothing came off** because the thresholds were set so only the rail carbine and the Gauss slug could reach them. A rifle round going through a man only loses ~300 J in him, and the first pass counted little more than that. The cowering and crawling you saw came from wounds, not from cuts.
- **The blood** was flat, unlit particle sprites plus big soft "mist" sprites, which the Mobile renderer drew as pale red clouds.

What changed (design §5.5):
- **Dismemberment retuned**, measured by shooting every gun at every body part at 3 m and 8 m:

  | Gun | What it takes |
  |---|---|
  | Five-seveN | Nothing in one round. 2–3 rounds take a hand, a forearm or a shin; about 4 an arm |
  | Saiga buckshot | At 3 m one shell takes the head, an arm or a leg. At 8 m a hand or the head |
  | M14 / MG42 | One round through a limb takes it (arm at the upper arm, leg above the knee in two). One to the head breaks it apart |
  | RC-6 rail carbine | Any limb or head in one round |
  | GX-4 slug | Bursts the whole body (still the only one-shot burst) |

  A neck hit takes the head off whole; a hit on the head itself breaks it into skull, jaw and chunks.
- **Blood is drops, not clouds.** Each drop flies on its own path under gravity and air drag (fine spray stops in half a metre and sinks; heavy drops arc across the room), lit by the scene and streaked when fast. Where they come down they leave stains that match how they hit: round drops falling straight, long drops with tails at an angle, spatter where the gout from an exit wound hits the wall behind, runs down walls, smears behind a crawling man. Stains start wet red and dry dark. A cut-off limb's stump pumps a stream in heartbeats that weakens and stops. Slow motion slows all of it.
- **Two new sliders**, Pause → Tuning → Gore: *Body toughness* (higher = harder to take apart) and *Blood amount*. "Copy values" includes them.
- CI fix carried over from PR #15, which wasn't merged: the camera-kick test no longer fails on a slow runner (it had failed again in this run).

Cloud evidence: `tools/check.sh` passes, 311 tests (new: `tests/scene/test_blood.gd`, `tests/unit/test_blood_drops.gd`, and 6 more in `tests/scene/test_gore.gd`). Captures with the Mobile renderer on software Vulkan: `docs/previews/gore_burst.png`, `gore_lineup_left.png`, `gore_lineup_close.png` (0.27 s after six men are shot with the M14, MG42, pistol, buckshot, M14 to the head and the Gauss arm), `gore_lineup.png`, `blood_wall.png`, `blood_floor.png` (after it all lands), `blood_stains.png` (the stain shapes). Not checked in the cloud: how the blood reads at night in Chinatown on the phone, and frame time with a lot of blood in the air (up to 320 drops in one draw call; stains add one more).

Please try (gore on Maximum):
1. In Chinatown, shoot arms, legs and heads with the Five-seveN and the M14. Do they come off often enough now, or too often? Move *Body toughness* until it feels right and send the copied values.
2. Shotgun to the head and to a leg up close.
3. Look at the walls and floor after a fight. Does the blood look like blood, and is there too much or too little? (*Blood amount*.)
4. Frame rate during a big fight with a lot of blood about.

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: the pale grey puffs in the captures are concrete dust from rounds hitting the wall behind (impact effects, not blood); say if those read as clouds too. Gore on the player's melee and the whip still uses the same cuts (tune blade_factor by feel).

## 2026-11-11 — Triad wardrobe, tattoos and spoken callouts (waiting for the owner)

Owner: "The enemies are really hard to see and they lack a lot of detail, they also are quite small and don't stand out against the environment. Without fucking up the gore system you just implemented, fix it so that the triad members actually look good. They need tattoos. They also need clothes they can wear that are randomly selected from a bank, also I can't hear the actual voices of them in the game."

What changed (design §5.6, §6):
- **New triad body**, muscled and sculpted (the old one was a blobby man in one jacket), and a **wardrobe bank of 24 items**: singlet, tee, camp shirt (buttoned or open), bomber, hoodie, track top, leather jacket; cargos, jeans, track pants, shorts, slacks; sneakers, boots; four haircuts or bald; cap, beanie; sunglasses, chain, watch. Each man draws an outfit for his role (Gunmen: street or summer clothes; Enforcers: hoodies and track tops under the plate carrier; the Red Pole: printed shirts, leather, gold), then colours, sometimes a print (Hawaiian, camo, check, cloud brocade), skin tone and stubble or a goatee. Of 60 Gunmen, 57 come out in different clothes before colours are counted.
- **Tattoos**: dragon and koi sleeves, tiger stripes, 忠義 and other characters on forearms, chest, ribs, neck and knuckles, in three sets; each man shows a random mix of them on whatever skin his clothes leave bare.
- **Easier to see**: 1.12 scale (about 1.96 m, was 1.08), a soft fill light on their fronts so they don't sink into the dark streets, a stronger distance rim (1.0, was 0.8), and mostly light and bright clothes (black is rare on tops now).
- **Gore is unchanged** and every garment comes apart with the body: an arm comes off in its sleeve, a head with its hair, cap and glasses, a shin with its shoe. A man is still one draw call before and after cuts. All 20 gore tests pass.
- **They talk.** Every callout is now spoken as well as subtitled, in six different voices (a voice per man): contact, reloading, man down, the Red Pole down, pinned by fire, lost him, push him, fleeing, the Red Pole yelling at runners, surrender, cowering, gut shot, legs gone, an arm gone, burning, grabbed by the mesh arm. Their voices come from their own heads and gunfire can't cut them off anymore. That was also why death screams got lost: every impact sound used to steal from the same 16 sound slots.

Cloud evidence: `tools/check.sh` passes, 324 tests; new tests `tests/scene/test_wardrobe.gd` (bank, looks, one mesh, a severed arm takes its sleeve), `tests/scene/test_enemy_voice.gd` (spoken with subtitle, from the head, not cut off by 40 impacts, squad spacing), `tests/unit/test_voice_lines.gd` (all 276 clips load). Every clip was transcribed by Whisper in the session: 275 of 276 come back as written. Captures (Mobile renderer, software Vulkan): `docs/previews/triad_wardrobe*.png` (eight men in the range, front, back, close, from 11 m), `docs/previews/triad_face.png` (a face up close), `docs/previews/triad_chinatown.png` (three men at 9, 17 and 28 m from the player start in the fish market), `docs/previews/triad_tattoos.png`, `docs/previews/triad_poses.png`, `docs/previews/triad_split.png` (the pieces, clothes included), `docs/previews/gore_lineup*.png` (redone with the new men). Not checked in the cloud: how the voices sound through the phone's speaker or headphones, and frame time with 12 dressed men in view (each man is now about 13k triangles instead of 10k; the overlay is in the captures).

Please try:
1. Chinatown: can you pick the men out of the street now at 20–30 m? Too bright, too gaudy, or still too dark?
2. Get close to a few. Do the clothes, faces and tattoos look good? Anything that looks wrong (a sleeve poking through, a bald patch, a floating cap)?
3. Listen in a fight: do you hear the callouts over the guns? Do the voices sound like angry men or like a computer? Too loud, too quiet, too chatty?
4. Gore on Maximum: shoot arms and legs off. Do the sleeves, trouser legs and shoes go with them?

- Device / renderer / settings:
- Notes from the owner:
- Follow-ups: Cantonese callouts would need a Cantonese voice model (not available in the session); a few more garments (vests, tank tops with prints, suit jackets) and face shapes are easy to add to the bank.

## 2026-11-12 — Performance pass: no hitches on cuts and spawns, LODs for the men (waiting for the owner)

Owner: "The latest build has slightly worse performance averaging around 45 frames per second even on 70 percent and variable resolution. Optimize it without compromising fidelity."

Build: `dev-latest` from branch `ccr-1f8f82b9-ssbn8k` @ c6b6df0, CI run #28 (manual run, GUT passed), `graft-debug.apk` 210,921,731 bytes. Installs over the previous build.

What was measured (cloud; the phone's GPU can't be measured here):
- A new probe (`-- --perf=15` on Chinatown) plays the map with the rolling spawns and a bot shooting men with the M14, and times every frame on the CPU. Eight men fighting cost ~0.55 ms a frame plus ~1.3 ms per physics tick on the cloud's CPU, so steady game logic isn't what holds the phone at 45.
- **The hitches were mesh merges on the main thread.** Each man is one mesh of his body and clothes, merged when he spawns (5–10 ms) and merged again into all his pieces at his first cut (8–15 ms), on the cloud's CPU, roughly 3× that on the phone, plus a GPU readback per piece. Every spawn of three and every first limb off dropped one or two frames.
- **The merged men had no LODs.** Godot's importer makes LODs for the glTF's own meshes, not for meshes built at runtime, so a man 30 m away drew all ~12.5k triangles, and up to 12 men plus 10 bodies can be in view.
- **The HUD's red and dark edge vignette** (hurt or under fire) drew 40 stacked translucent strips at the phone's native 1604×720. Native resolution, so lowering the render scale never touched it: about five full screens of blending in every firefight.

What changed (no visual change intended anywhere):
- **Men's meshes are built on a worker thread** (`src/ai/triad_mesh_baker.gd`), ahead of time: the spawner picks each man's clothes a spawn or two early, so his intact mesh, the mesh after his first cut and the piece each first cut throws are ready before he appears. In the cloud the worst first cut went from 10–15 ms to 1–3 ms, the worst spawn from 10 ms to 3–6 ms.
- **LODs for every man and body**: about 12.5k → 6k → 3k → 1.4k triangles with distance; Godot switches only when the difference is under 2 pixels. The cut mesh's LODs never join two pieces, so nothing stretches when a limb comes off (tested). Ten men round the player: +38.5k triangles without LODs, +13.3k with. A/B at 3× zoom: `docs/previews/triad_lod_ab.png` (top LODs, bottom full detail; the only differences are rain and gun sway).
- **The vignette** is four gradient strips (a tenth of the pixels), matched to the old stacked strips within 4 % (`tests/unit/test_perf_tuning.gd`).
- **Men's shader** skips its wound/blood/char noise (16 hash functions a pixel) on men who have none of those. Identical result.
- **Auto resolution** only lowers the render scale when the GPU timer says the GPU is busy. Before, any missed frame lowered it, even when the misses were the CPU's, which only made the picture grainier.
- **Map cost test** (Pause): new rows "+10 men" and "+10 men, no LODs" (ten men placed round the spot), "HUD hidden" and "50 % res"; new columns: render-CPU ms (rcpu), triangles and draw calls.

Cloud evidence: `tools/check.sh` passes, 333 tests; new tests `tests/scene/test_mesh_baker.gd` (baked mesh = the old merge, has LODs, no LOD triangle spans two pieces, baked gibs match, spawns get LODs, a man spawned without a prefetch gets them swapped in) and `tests/unit/test_perf_tuning.gd`. Not checked: anything on the phone's GPU. I can't tell yet whether 45 fps is the GPU, the CPU or frame pacing, so the next screenshot decides the next step.

Please try:
1. Play Chinatown with the overlay on through a few waves, shooting limbs off. Any hitch when a limb comes off or men arrive? What fps in a fight?
2. **Pause → Map cost test** (~80 s, don't touch the controller) and screenshot the table. That tells me exactly where the 45 comes from: if *frame* is well above *gpu*, it's the CPU or pacing; if *gpu* barely changes between 100/70/50 %, it's vertices or fixed passes, not pixels.
3. Look at men at a distance: anything popping or changing shape as they walk away?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups: if the CPU side is the limit, try rendering on its own thread (needs a crash-safe toggle); spawns still cost 3–6 ms in the cloud (building the animation tree and hitboxes), so pooling men is next for those.

## 2026-11-12 — MP5/SD-L: run-and-gun SMG with a red dot and a green laser (waiting for the owner)

Owner's ask: "a very detailed mp5, with a red dot sight, suppressor, under barrel green laser ... great hipfire spread ... high mobility run and gun, contained hipfire, which is accurate to the green laser, even while moving, jumping, or walk running." Details in design §4.6.

What's in the build:
- The MP5 is the sixth gun on the weapon wheel (hold Y). Full auto, 800 rpm, 30 + 1, suppressed 9 mm, about two torso hits per gunman.
- **Fire on the run:** with the MP5, RT doesn't stop a sprint. You keep sprint speed and the gun comes up out of the sprint pose while you fire. LT still ends the sprint. Other guns are unchanged.
- **The laser is the reticle:** at the hip the crosshair disappears while the green dot is on something; rounds go to the dot (within a cone about a fist wide at 10 m). Walking, running and jumping don't move the dot; whipping the view round makes it lag a touch and settle, and the rounds follow it.
- No weight penalty, fast draw (0.3 s), fast to the sights (0.14 s) through the red dot.
- Empty reloads end with the HK slap: the cocking handle stays back until the reload slaps it home.

Cloud evidence: `tools/check.sh` passes, 348 tests; `tests/scene/test_mp5.gd` (14 tests). Measured there: a 15-round burst while strafing and jumping stayed within 0.47° of the laser line; on a wall 28 m off, strafing and jumping, every round landed within 0.40 m of the dot; a running gunman at 10 m went down in 2 rounds. In-game screenshots: `docs/previews/mp5_ingame_hip.png`, `mp5_ingame_ads.png`, `mp5_ingame_burst.png`. Not checked: how it feels on the controller, the sounds by ear, and the phone's frame rate with it out (the laser adds two draw calls and no light).

Please try:
1. Sprint with the MP5 and hold RT while running and jumping across the range. Does the dot stay where the rounds go? Is the cone tight enough, or too tight?
2. Flick the view quickly while firing. Is the dot's lag nice, or annoying? (It follows 60 % of the gun's sway; Pause → Tuning → Laser "Dot follows gun sway" changes it live, 0 pins it to the screen centre.)
3. Is the laser easy to see: dot size, beam brightness? Do the sounds read as a suppressed MP5?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## Optimization Phase 1 — 2026-11-13 — free wins (waiting for the owner)

What's in the APK (details in `optimization overhaul.md` §12): no change to the picture is intended.
- The gun is drawn before the men and the map, so the map isn't shaded under it.
- Cheaper shaders: rain work only on wet ground, wounds only near wounds, plainer filtering on the arms.
- Augment arms, the drone and the knife draw in 6–8 calls instead of 29–107; enemy guns in one call each, all contact shadows in one.
- The HUD redraws only when something on it changes; frozen corpses stop running code; steam shares its materials and fades when you're inside a puff.
- After a hitch, at most 3 physics steps in one frame (was 8).
- Pause → Frame cap now has 40 (three refreshes of the 120 Hz screen).
- Pause → **Frame pacing** (applies after restarting the app): "fixed" never lowers the frame rate by itself; "auto" is what the game used until now.

Please try:
1. A Chinatown fight with the overlay on. Screenshot the overlay. Does it feel steadier than the last build?
2. Pause → Frame pacing → fixed. Close and reopen the app. Fight again: steadier or worse?
3. Deploy the GX-4 and the fan shield in a fight: any hitch when they come out?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## Impact feedback and RX-9 — 2026-11-13 (waiting for the owner)

Owner: slow the world a little more under the RX-9 without slowing the operative; more feedback the moment a round hits ("a solid little wound... without that pattern"); in slow motion, clearly see the round go in, come out and throw a brutal but restrained splatter onto what's behind (Brutal Doom, Soldier of Fortune); cheap.

What's in the APK (design §3.4 RX-9 and §5.5 "The moment of impact"):
- RX-9: the world at 24 % (was 30 %); you still move, shoot and reload at 65 % of real time.
- Wounds: solid shapes, no noise pattern. Black hole, hard rim, a soaked patch that spreads for 3 s and runs down. Exits are torn and bigger. Drawn bigger than life so they read at fighting distance.
- The moment of impact: a burst of blood at the entry, a fan of jets out of the exit, more drops, bits of tissue, a bigger splatter on the wall behind with spines and runs.
- In slow motion your rounds leave a thin wake, so you see each one go in and come out the back.
- Bug fixed: every bullet-impact particle (dust, sparks, splinters, glass) was drawn about a metre wide. That was the big pale puff on walls; it hid the blood. They're now their real few centimetres, which also costs less.
- Cost: two more draw calls at most (bursts, wakes); wound shading is cheaper than before (no noise).

Please try:
1. Shoot a man standing in front of a wall with the Five-seveN, normal speed. Do you see a hit land? Is the wall splatter the right size?
2. Same with the RX-9 on. Do you see the round go in and come out? Too much, too little, too slow?
3. Is the wound on his clothes readable at fighting distance? Does it look like a wound or a sticker?
4. Does the RX-9 feel slower for them and the same for you?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

## SX-8 Urticating Setae — 2026-11-13 (waiting for the owner)

Owner: a new active, nanotech: vents on the side of the arm that grow long razor-thin nanite hairs; a dead-eye where you mark up to 4 or 5 targets; the fire button throws the hairs, which harden in the air and leave cavitation wounds that wipe most enemies out. "Our AoE." A badass throwing animation.

What's in the APK (design §3.4c):
- Loadout screen (View): the SX-8 is an orange tile among the actives. It takes the left forearm (it replaces the NT-5 or BW-6) and runs on the Operator as it is. Install it and it goes on D-pad right.
- LB: the gun goes down, the left arm comes forward, 48 fibres grow out of 24 ports, the world slows almost to a stop (colour drained, a heartbeat, amber edges).
- LT marks the body part under the crosshair (it snaps to the nearest head or chest if you're close). 4 marks, 5 with OB-5 or TG-6 eyes. Several on one man are allowed. 5 s to mark (more with more processing).
- RT: the arm whips across, the fibres leave as needles, time comes back. Head marks lose the head, limb marks lose the limb, torso marks burst the body (Maximum gore). Needles that go through stick in the wall.
- LB while marking folds it and keeps the throw. One throw; it regrows in about 12 s.

Please try:
1. Wave mode or the docks: mark four men, throw. Does it feel like a finishing move? Is the throw animation strong enough?
2. Is 5 s of marking right? Is ×0.06 too slow or not slow enough?
3. Are the needles readable in flight? Do you see them reach each man?
4. Too strong? It kills four men every 12 s. Options: longer regrowth, fewer marks, or torso marks that only kill.
5. Is LT for marking natural, or would you rather mark by holding RT and release to throw?

- Device / renderer / settings:
- Measured:
- Notes from the owner:
- Follow-ups:

