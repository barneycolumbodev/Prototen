# CLAUDE.md

Working title: GRAFT (placeholder)

A single-player first-person shooter for Android, played with a controller. Military science fiction. The player is a heavily augmented soldier fighting unaugmented human soldiers. The owner works from a phone only. Claude Code does the engineering and makes the assets.

**Current phase: prototype.** The goal is to get the core systems working and feeling right: gunplay, movement, the damage simulation and the augment system. Story, world, progression and release plans are not decided. Don't build around assumptions about them.

Items marked *(proposal)* are Claude's suggestions and can change. Everything else was decided by the owner.

---

## 1. Working rules for Claude Code

### First session (done 2026-11-01; see `docs/tooling-status.md`)

1. Move sections 3–6 (the game design) into `docs/design.md` and leave a one-line pointer here. This file loads every session, so keep it short.
2. Scaffold the repository (§9.3).
3. Add the tooling: `.mcp.json`, `.claude/settings.json`, scripts in `tools/`, project skills (§10).
4. Add the CI workflow (§11).
5. Check every tool in §10.4. Report what works and what doesn't.
6. Start milestone M0 (§12).

Commit after each step.

### Always

- The owner only has a phone. They can't run commands, open an editor or read long diffs. Show progress with screenshots, test results, CI runs and APK builds.
- Don't say something works without evidence: a passing test, a screenshot you looked at, a CI log, or the owner's playtest notes.
- You make the assets (§7). Build each mechanic with simple shapes first so gameplay work isn't blocked, then replace them with finished assets.
- Tuning values (weapons, parts, enemies, gore, camera feel) go in `.tres` resource files, not in code.
- Typed GDScript. Treat static-typing warnings as errors.
- Paid APIs (Meshy, ElevenLabs, Tripo3D): ask the owner first and say roughly how many calls you'll make. Tripo: one generation per asset, no variants or retries unless the owner asks (owner, 2026-11-17); the free rig-check before a rig.
- Don't push git tags. The cloud GitHub proxy rejects them; CI creates release tags.
- When a decision changes, update the docs in the same commit.
- Tone: grounded military science fiction. Every ability comes from hardware. No magic, psychic powers, occult or religious-supernatural elements, and no anime styling.

---

## 2. The game

- **Player and enemies.** You are augmented. For now, enemies are ordinary unaugmented humans: triad members (owner, 2026-11-03), in waves in the test range and on a rolling clock on the Chinatown docks map (8 at the start, 3 more whenever fewer than 4 are fighting, out of sight; owner, 2026-11-04). Each is one of twelve photographic men made with Tripo3D and fitted to the triad rig (2026-11-17, owner: "remake them in Tripo"; design §5.6b; the procedural wardrobe bank of 2026-11-11 stays as a fallback), and speaks his callouts (design §5.6). In wave modes they hunt you down, pin and flank together, and the last man of a wave is marked on the HUD (owner, 2026-11-16; design §5.6a). The first melee type, the Hatchet Man, came 2026-11-15 (design §8.8a); attack dogs (German shepherds) 2026-11-17 (design §8.8b); and the first boss, the Incense Master, on wave 5 (owner, 2026-11-15; design §8.7a, the execution §8.7b). The difference between you and them should show everywhere: speed, strength, durability, perception, what you can carry, and how they react to you. It's a power fantasy, but fights should still take skill.
- **Maps:** Chinatown docks (§7.1) and, from 2026-11-18 (owner), the Golden Dragon hotel: an abandoned, fully lit five-star lobby, all indoors, enemies from six lifts and the street, winding corridors round a central atrium with long sight lines (design §7.2). Mostly Blender, not Tripo (the Tripo balance was low).
- **Main mode: Survival** (owner, 2026-11-15; design §8). Waves on a map, getting harder. You start with a doctrine (a baseline body), one gun (Five-seveN, MP5 or Saiga-12K) and one active at Mk I, a tuned-down version; the actives as built are Mk III, the ceiling. After every wave a supply drop brings one item or a choice of two (guns, actives, passives, marks); the doctrine and what you already own steer the odds, so a run can aim at a build. A boss every fifth wave drops the active he carries or a mark for it. Many more enemy types per map, themed (triad on Chinatown), melee ones included. "A power fantasy that you have to earn." Death ends the run. Today's open mode (every gun and part, the loadout screen) stays as **Sandbox**.
- **Simulation.** Simulate as much as an immersive sim would (bodies, damage, ballistics, enemy behavior), but keep combat fast. Every system has to work at full speed, without menus or pauses.
- **Gunplay.** The goal is the best gunplay in any mobile shooter. References: Call of Duty for gun handling, Doom for speed and aggression, Halo for readable weapons and enemies, F.E.A.R. and Trepang2 for slow motion and hit reactions, S.T.A.L.K.E.R. for weapon weight, Soldier of Fortune for locational damage and gore.
- **Tone.** Warhammer 40,000's hardware and industrial scale without its supernatural side. Deus Ex's augmentation. Halo's military hardware. Soldier of Fortune's grounded, violent military action.
- **Visuals.** Realistic enough that weapons and violence look convincing. Beyond that, the look relies on color, lighting, atmosphere and effects more than on detailed geometry and textures.
- **Not decided yet:** story, world, factions, meta-progression between runs, release platform.

---

## 3–6. Game design

Augmentation (§3; the actives in §3.4, §3.4b, §3.4c and §3.4d, the passive library in §3.6, colours in §3.7), test loadouts (§4; the Governor and the Slagger plasma pistol §4.9, the Steyr AUG §4.10, the SPAS-12 §4.11), combat simulation (§5; the squad hunt §5.6a, tuning `data/enemies/hunt.tres`), art direction (§6), maps (§7) and the Survival mode (§8: runs, marks, drops, doctrines, waves, bosses, the enemy roster) live in [`docs/design.md`](docs/design.md). Survival tuning: `tools/run/gen_pool.py` → `data/run/survival.tres` (don't hand-edit the .tres).

---

## 7. Assets

The owner doesn't make assets. Claude makes them in the cloud session.

**Blender 5.2 LTS**, installed by the setup script and driven by Python. Every asset has a generator script in `raw_assets/`, so it can be rebuilt and adjusted.

- Weapons and augment hardware: hard-surface modeling with modifiers (bevel, boolean, mirror, array, weighted normals), built to real dimensions.
- Environment kits and props: modular pieces on a grid.
- Materials: procedural shaders baked to texture maps with Cycles on the CPU, then compressed for mobile.
- LODs, collision meshes, correct scale and pivots, glTF export.
- After each change, render a preview (turntable or four views) and look at it before committing. Send the important ones to the owner.

**Humans:** MPFB (MakeHuman for Blender, a free extension) generates rigged human bodies. Check and record the license of each asset pack you use. For animation, start from Quaternius's Universal Animation Library (CC0), retargeted, plus procedural layers for aiming, hit reactions and ragdoll.

**Textures and HDRIs:** Poly Haven and ambientCG, both CC0.

**Sound:** layered and processed. Use CC0 sources where they exist. ElevenLabs sound generation needs the owner's approval because it costs money.

**Optional, paid:** Meshy (text or image to 3D) for props and starting meshes. Tripo3D (`openapi.tripo3d.ai/v3`, key added by a network secret; image-to-model and the quadruped auto-rig made the attack dog, `raw_assets/characters/attack_dog/`). Its meshes beat the hand-built ones on organic shapes; review them as critically as your own Blender work. People: `raw_assets/characters/triad_tripo/` (concept image → image-to-model → `build.py` fits him to the triad rig with our own skeleton and weights, cuts him for dismemberment; design §5.6b). Next weak model: the first-person arms.

Log every third-party file and its license in `CREDITS.md`.

---

## 8. Target device and performance

Moto G 5G (2025): MediaTek Dimensity 6300, Mali-G57 MC2 GPU, 4 GB RAM, 720×1604 screen at 120 Hz.

Starting budgets. These are guesses: measure them on the phone in M0 and replace them.

| Budget | Start |
|---|---|
| Frame rate | 60 fps; locked 40 or 30 as fallback settings (40 added 2026-11-13, optimization overhaul P-02) |
| Render scale | 0.8–1.0 of 720p |
| Draw calls | ≤ 150 |
| Triangles on screen | ≤ 250k |
| Active enemies | ≤ 12 |
| Ragdolls simulating | ≤ 3, frozen after about 2.5 s |
| Blood stains | ≤ 48 large + 144 single drops and runs, oldest fade out; ≤ 320 drops in the air (one draw call) |
| Live particles | ≤ 1,500 |
| Dynamic lights | ≤ 4; only one casts shadows |
| RAM | ≤ 1.2 GB |
| Heat | No throttling below target after 20 minutes |

For the machine gun at 1,200 rpm: pooled hitscan, a tracer every few rounds, one shared muzzle light, a cap on decals per second, and a looping fire sound.

---

## 9. Tech

### 9.1 Stack

- Godot 4.7.2, the latest stable release as of 2026-11-01. 4.8 is in beta; consider moving once it's stable.
- Mobile renderer (Vulkan). Compare it with the Compatibility renderer in M0 by measured frame time.
- Typed GDScript, Jolt physics, GUT for tests.
- Android arm64, landscape, gamepad required.

### 9.2 Architecture *(proposal)*

- **Parts:** each part is a resource with the properties in §3.2. A body model adds up mass, power, heat and capacity. Stats are base values plus modifiers from parts. Data links connect parts that read and write shared values.
- **Appearance:** each part lists meshes and attachment points for the first-person arms and the full body. Changing the loadout rebuilds the character model.
- **Input contexts:** base FPS controls sit at the bottom of a stack. Each active part pushes its own control context and pops it when it ends.
- **Active part states:** idle, deploying, active, recovering, cooldown. Handles power and heat costs, interruptions (EMP, damage), and handing over the camera and HUD.
- **DamageInfo:** amount, type, penetration, impulse, zone, bone, point, normal, source, flags.
- **Time:** a global time scale for slowdown, with a separate scale for the player. Audio pitch follows.
- **Pools** for projectiles, decals, blood, gibs, sounds and ragdolls.
- **One event bus** autoload for combat events.

### 9.3 Repository layout

```
project.godot        # the repo root is the Godot project root
addons/              # GUT and other addons
src/
  core/              # event bus, pools, input contexts, settings
  body/              # parts system, stats, appearance
  player/            # movement, camera, first-person arms
  weapons/           # weapons, ballistics, feedback
  augments/active/   # one folder per active part
  ai/                # perception, squads, morale
  gore/              # damage zones, blood, decals, ragdolls, dismemberment
  vfx/ audio/ ui/ levels/
data/                # .tres resources: weapons, parts, enemies, surfaces, gore
assets/              # exported models, textures, audio
raw_assets/          # Blender generator scripts and sources (.gdignore)
tests/               # GUT tests
tools/               # setup, check, screenshot scripts (.gdignore)
docs/                # design, playtest log, credits notes (.gdignore)
.claude/skills/  .claude/settings.json  .mcp.json
.github/workflows/
```

Put an empty `.gdignore` file in `raw_assets/`, `tools/` and `docs/` so Godot doesn't import them.

### 9.4 Default controls (remappable)

| Input | Action |
|---|---|
| Left stick / L3 | Move / sprint |
| Right stick / R3 | Look / melee strike (built 2026-11-08) |
| LT (hold) / RT | Aim down sights / fire |
| LB | The selected active part (tap on / tap off; the LC-6 catcher is held: hold to catch, let go to throw back, owner 2026-11-13). RB: executes a boss who is down on one knee (owner, 2026-11-15; design §8.7b); otherwise free. While a part is out, RT and LT are its own (whip: LT + right stick steers, RT lashes; mesh arm: RT grabs, RT throws; drone: sticks fly, A/B climb/sink, RT detonates; setae: LT marks, RT throws) |
| A | Jump (wall-run on contact) |
| B | Slide (a tap runs it out) / crouch |
| X | Reload (hold to interact; the M32A1, the Governor and the SPAS-12 load a round at a time, RT stops and fires) |
| Y | Tap: previous weapon. Hold: weapon wheel (owner, 2026-11-02; the MG barrel change needs another input in M3) |
| D-pad | Left / down / right: select active part 1 / 2 / 3 for LB, in the order they were installed (default: RX-9 / GX-4 arm / empty; 2026-11-10: any three of nine; 2026-11-13: of ten; 2026-11-14: of eleven). Up: shell type on guns that take several (Saiga-12K) (owner, 2026-11-07) |
| Menu / View | Pause / body status and loadout (in Survival the body can be viewed, not changed) (built 2026-11-05; loadout 2026-11-08; LB there: colours, 2026-11-10; 2026-11-11: every part on one grid, A installs or removes, RB jumps to the part that supplies a missing requirement) |

Aiming: response-curve presets, acceleration on full tilt, radial deadzones, aim assist in layers (slowdown near targets, slight pull while aiming down sights). Gyro aiming from the phone if the controller holds it.

---

## 10. Cloud setup and tooling

### 10.1 Environment (the owner sets this once at claude.ai/code)

Cloud sessions read this repo's `CLAUDE.md`, `.mcp.json`, hooks in `.claude/settings.json`, and `.claude/skills/`. They don't install plugins listed in settings. See the [cloud environment docs](https://code.claude.com/docs/en/cloud-environments.md).

1. **Network access:** Custom. Tick the option to include the default list, then add:

   ```
   download.blender.org
   extensions.blender.org
   static.makehumancommunity.org
   api.polyhaven.com
   dl.polyhaven.org
   ambientcg.com
   opengameart.org
   ```

   Add `api.meshy.ai` and `api.elevenlabs.io` only if you use those services. GitHub, npm, PyPI, Ubuntu packages and Docker Hub are already in the default list.

2. **Setup script:** paste the contents of [`tools/setup_env.sh`](tools/setup_env.sh). It installs the Xvfb/Vulkan packages, Godot 4.7.2 into `/opt/godot` and Blender 5.2.3 into `/opt/blender`, logs failures to `/opt/setup-errors.log`, and always exits 0.

3. **Environment variables:** only if you use paid services: `MESHY_API_KEY`, `ELEVENLABS_API_KEY`. Anyone who can use the environment can read these. Network secrets in the same dialog keep keys hidden from the session.

If something fails:

- The script logs failures to `/opt/setup-errors.log`, and the SessionStart hook prints them.
- If a GitHub download is blocked inside the session, do the download in a GitHub Actions workflow (Actions has open internet access) and commit the result or attach it to a release.
- If the script takes longer than about 5 minutes, the environment isn't cached. Move the Blender download into the SessionStart hook.

Cloud VMs have about 4 CPU cores, 16 GB RAM, 30 GB disk and no GPU. Android exports run in GitHub Actions.

### 10.2 MCP servers

`.mcp.json`:

```json
{
  "mcpServers": {
    "godot": {
      "command": "xvfb-run",
      "args": ["-a", "-s", "-screen 0 1280x720x24", "npx", "-y", "@beremaran/godot-agent-loop@2"],
      "env": { "GODOT_PATH": "/opt/godot/godot" }
    }
  }
}
```

- **Godot Agent Loop** ([releases](https://github.com/beremaran/godot-agent-loop/releases/tag/v2.0.0)) runs the game, takes screenshots, reads the scene tree, sends input, waits for conditions and runs tests. Its developer tests it on Linux under Xvfb with software rendering. 2.0.0 (August 2026) was the latest version checked; use the newest 2.x that works.
- Add Meshy (`npx -y @meshy-ai/meshy-mcp-server`) and ElevenLabs (`uvx elevenlabs-mcp`) entries only after their API keys are set. If an `.mcp.json` variable is unset, Claude Code can silently drop that server ([issue](https://claudeissues.com/issue/60513-stdio-mcp-server-silently-dropped-when-var-substitution-fails-docs-promise-fail)).

### 10.3 Blender tooling

Claude runs Blender directly: `blender -b --factory-startup --python script.py -- <args>`, or `tools/blender.sh script.py <args>`, which falls back to the `bpy` module from PyPI (same version, in `/opt/bpy-venv`) when the binary isn't installed. That covers modeling, materials, baking, rendering and export, so no Blender MCP is needed to start.

The official Blender Lab MCP server (v1.0.3, needs Blender 5.1 or newer) works through a Blender add-on and mainly targets an open Blender window. Its background-mode support is limited. Try it later if direct scripting hits a limit.

### 10.4 Verification

- `tools/check.sh`: import the project, validate scripts, run GUT (`godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit`).
- `tools/screenshot.sh`: run a scene under Xvfb with software Vulkan and save PNGs. Budget about 30 seconds per shot. Use fixed camera positions in each test room (`capture_cameras` group).
- `godot -- --bench=<seconds>` runs the frame-time benchmark at startup, prints JSON and quits.
- `godot --doctool <dir>` dumps the class reference for the installed version. Check APIs there instead of relying on memory.
- `blender --version` and a test render, to confirm Blender works.
- Godot Agent Loop scenarios: scripted input with assertions (enemy dead, ragdoll active, decal count under the cap).
- On the phone: a debug overlay (FPS, frame time, draw calls, memory, counts of enemies, ragdolls and decals); a bug-report button that saves logs, settings and loadout to a file the owner can share; input recording.

### 10.5 Skills

- Copy the relevant GodotPrompter skills (MIT, by jame581) into `.claude/skills/`: architecture, state machines, navigation, animation, input, performance, code review. Keep the license file. ([overview](https://www.sourcepulse.org/projects/31409234))
- Write project skills in M0: `godot-verify`, `blender-assets`, `weapon-feel`, `gore-and-ragdolls`, `perf-budget`, `asset-sources`.

### 10.6 SessionStart hook

`tools/session_start.sh`: exit unless `CLAUDE_CODE_REMOTE=true`. Print the Godot and Blender versions and the contents of `/opt/setup-errors.log`. Import the project if `.godot/` is missing.

---

## 11. CI (GitHub Actions)

- **Every pull request builds an APK**, and so does every push to any branch and a manual dispatch (owner, 2026-11-11 and 2026-11-12). Not only `main`: never tell the owner a build waits for a merge to `main`. The newest build replaces `dev-latest`; its title has the build time and commit, its notes the branch and whether the tests passed.
- Steps: download and cache Godot 4.7.2 and its export templates; import; run GUT (a failure turns the run red but never stops the APK); export a debug APK (arm64) signed with a keystore from repository secrets, or, without them, the fixed debug key in `tools/android/` (never a new key per run: Android then rejects every update); publish it to a rolling `dev-latest` GitHub Release that the workflow creates.
- Run an explicit import before exporting. Headless exports have dropped resources in past Godot versions.
- Claude checks runs with REST commands (`gh run list`, `gh api repos/{owner}/{repo}/actions/runs`). GraphQL commands such as `gh pr` don't work through the proxy.
- Keep the release keystore in GitHub Secrets, and the owner keeps an offline backup.

---

## 12. Milestones

Each milestone ends with an APK on the owner's phone and an entry in `docs/playtest-log.md`.

1. **M0 – Foundation.** Repo, tools and CI producing an APK. A test room, controller movement and camera, the debug overlay, and the renderer comparison.
   Done when the APK installs from Releases, the test room runs at 60 fps on the Moto G, and cloud screenshots work.
2. **M1 – Pistol.** Built in slices, core gunplay first (owner decision 2026-11-01; see `docs/m1-gunplay-plan.md`). Suppressed Five-seveN with the full feedback list (§5.3). Saiga-12K with buck, slugs and Dragon's Breath (owner, 2026-11-02; design §4.3). Sprint, slide, wall-run, mantle. Locational damage, penetration, gore and ragdolls. Three enemy roles with awareness, suppression and morale. Wave mode. First finished assets: the Five-seveN, first-person arms, one enemy.
   Done when the owner wants to keep playing the wave mode. Status 2026-11-04: all slices built (M1a gunplay, M1b movement, M1c triad enemies, gore, ragdolls, AI, waves); waiting for the owner's playtest. Owner, 2026-11-04: M1 is more or less complete; next, polish and atmosphere, starting with the Chinatown docks map with rolling spawns (design §7, now the main scene; the test range is under Pause → Map).
   2026-11-14 (owner): the game opens on a main menu: the operative, helmet off, smoking against the restaurant front; the loadout screen dresses him in the scene; Begin starts the map (design §7.1). The slide is shorter (about 7 m) and launches men into the air instead of hurting them (design §5.7).
   2026-11-17 (owner: "smooth stepping... like Modern Warfare 2019", not "a camera gliding"): footfalls tied to ground covered, the head and gun riding the stride with weight shift, footstep sounds, planted starts, stops and turns; the slide unchanged (design §5.7a).
3. **M2 – Parts system.** Loadout screen. Power, heat, mass and capacity. At least 8 passives with visible changes. The drone, whip and time slowdown.
   Done when three different loadouts play noticeably differently.
   2026-11-08 (owner): the passive system: ~35 core stats with relationships (load, structure cap, momentum, link range, heat), 37 passives with tradeoffs and requirements, four presets, a loadout screen, the R3 strike; four parts with finished hardware (design §3.6).
   2026-11-10 (owner): seven more actives with models, deploy animations and sounds (the monofilament whip, the Shrike drone, the mesh arm that grabs and throws, plus ram thrusters, a thermoptic shroud, a fan shield and an arc projector: nine in all, any three on the D-pad), and the part-by-part colour customizer (design §3.4b, §3.7).
   2026-11-13 (owner): the SX-8 Urticating Setae, the AoE: a dead-eye that marks up to four or five body parts with LT, then throws nanite needles that leave cavitation wounds (design §3.4c). LT/RT while it's out: mark/throw.
   2026-11-14 (owner, asked 2026-11-13): the LC-6 Lorentz Catcher: hold LB and enemy rounds from the front are caught in a magnetic field in front of the left hand; let go (or run out of time or heat) and exactly those rounds go back out over a wide area at the aim point (design §3.4d).
   Started 2026-11-05 (owner): the parts system foundation, the operative's base body (the GS-2 graft suit; helmet on or off, with the owner's face; Y on the body-status screen) on a body-status screen, and the time slowdown (RX-9 on LB). See design §3.4, §3.4a. 2026-11-07: three actives on LB picked with the D-pad, and the second active, the GX-4 Gauss arm.
4. **M3 – Heavy weapons.** MG42-style machine gun with heat and barrel changes (the gun itself, its handling and a flat carry penalty were pulled into M1 by the owner on 2026-11-01; heat and barrel changes stay here). Heavy armor parts, two more actives, dismemberment (pulled forward and built 2026-11-11, design §5.5), machine-gunner and anti-augment enemies.
   Done when sustained fire tears up a room and the phone holds its frame rate.
   2026-11-14 (Claude's choice; owner: "find something missing and add it"): the M32A1 six-shot 40 mm grenade launcher, the first explosive gun. Rounds fly an arc, arm after 9 m, and burst on impact or, aimed, in the air past the point the fire-control sight lased (over cover). Real fragments that cover stops, a revolving cylinder that loads a round at a time, and a new look for every blast (fireball, smoke, dust ring, scorch), the drone's included (design §4.8).
5. **M4 – Look and sound.** Art direction applied to two or three test areas, lighting, an audio pass.
6. **S1 – Survival foundation** (owner, 2026-11-15: the direction for the main mode; design §8). Now the current focus.
   Built 2026-11-15: the design (§8); Mk I/II/III for all eleven actives; the run (doctrines as baseline bodies, supply drops with doctrine and affinity bias, threat-budget waves, lieutenant waves standing in for bosses); the Blue Lantern recruit; Survival on the main menu with the kit screen, the drop screen and the run-over screen. Today's mode is Sandbox.
   2026-11-15 (owner): the Hatchet Man, the first melee enemy: hatchet or cleaver, flanks from cover to cover, vaults low walls, a telegraphed chop to dodge, stagger or block (design §8.8a). Survival from wave 4; Sandbox spawns too.
   2026-11-15 (owner): the first boss, the Incense Master, on wave 5: a huge bald enforcer in black leather with a gold-and-diamond pendant and a Gauss prosthetic for a right arm; a haymaker, a ground pound to jump, a charged Gauss shot the LC-6 can catch and throw back. A short entrance cutscene; at zero he goes down on one knee and RB plays a first-person execution (punches, the head goes, the fist examined and shaken off). He drops the GX-4 or its next mark (design §8.7a, §8.7b).
   2026-11-17 (owner): attack dogs, German shepherds that gallop in, leap and bite; Chinatown spawns and Survival from wave 6. The first Tripo3D asset: generated, reduced, auto-rigged, animated in Blender (design §8.8b).
   2026-11-17 (owner: "remake the models you're not impressed by in Tripo"): every triad man and the Incense Master are now Tripo3D men on the triad rig, eleven looks plus the boss, the Blue Lantern in his own (design §5.6b).
   2026-11-18 (owner): map 2, the Golden Dragon Grand Hotel (design §7.2), and two guns with it (design §4.9): the Governor, a black polymer .45-70 lever action (the lever is thrown after every shot: bolt, case, hammer, a heavy clunk in sound and rumble), and the SL-9 Slagger, the first energy weapon, a welder-built plasma pistol (hold to charge, 2.75 s to full; grazes set men alight and panicking, a charged trunk hit burns a hole through, limbs come off cauterised and burning).
   2026-11-20 (owner: "an automatic rifle, like an assault rifle niche ... a very realistic Steyr AUG"): the AUG A1 (StG 77), traced from reference photos and checked against them by overlay; olive stock, 1.5x integral scope (aiming goes through it, circle reticle), progressive trigger (light pull single, full pull automatic), clear magazine showing the rounds left (design §4.10).
   2026-11-20 (owner: "the SPAS 12 ... stock folded up ... one-to-one with the actual SPAS 12"): the SPAS-12, traced from a studio photo with the stock folded and checked by overlay; pump only, and after every shot the gun comes up while the left hand racks the pump (Doom style); slower than the Saiga, more damage, a little more range, a tighter pattern and a smaller ring; a layered stereo boom (design §4.11).
   Next: more triad types and bosses (the Straw Sandal next), theme waves (design §8.8), then tuning from the owner's runs.
   Done when a run has a difficulty curve the owner wants to replay and builds that play differently.

What comes after the prototype gets decided then.

---

## 13. Open questions

- Title.
- Does the controller hold the phone? That decides whether gyro aiming is worth building.
- ~~How far gore goes at the maximum setting.~~ Owner, 2026-11-11: Soldier of Fortune style: decapitation, dismemberment and gibbing, driven by ballistic impact and hit location (design §5.5).
- Real gun names (Five-seveN, MG42, SPAS-12) are fine in a prototype. Selling the game with them might need licenses, so decide before any release.
- Budget for Meshy and ElevenLabs, if any.
- Survival: meta-progression between runs, run length (endless or a final wave), health and ammunition between waves (design §8.10).
- Public or private repo.
