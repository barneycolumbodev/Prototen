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
- Paid APIs (Meshy, ElevenLabs): ask the owner first and say roughly how many calls you'll make.
- Don't push git tags. The cloud GitHub proxy rejects them; CI creates release tags.
- When a decision changes, update the docs in the same commit.
- Tone: grounded military science fiction. Every ability comes from hardware. No magic, psychic powers, occult or religious-supernatural elements, and no anime styling.

---

## 2. The game

- **Player and enemies.** You are augmented. For now, enemies are ordinary unaugmented humans: triad members (owner, 2026-11-03), in waves in the test range and on a rolling clock on the Chinatown docks map (8 at the start, 3 more whenever fewer than 4 are fighting, out of sight; owner, 2026-11-04). The difference between you and them should show everywhere: speed, strength, durability, perception, what you can carry, and how they react to you. It's a power fantasy, but fights should still take skill.
- **Simulation.** Simulate as much as an immersive sim would (bodies, damage, ballistics, enemy behavior), but keep combat fast. Every system has to work at full speed, without menus or pauses.
- **Gunplay.** The goal is the best gunplay in any mobile shooter. References: Call of Duty for gun handling, Doom for speed and aggression, Halo for readable weapons and enemies, F.E.A.R. and Trepang2 for slow motion and hit reactions, S.T.A.L.K.E.R. for weapon weight, Soldier of Fortune for locational damage and gore.
- **Tone.** Warhammer 40,000's hardware and industrial scale without its supernatural side. Deus Ex's augmentation. Halo's military hardware. Soldier of Fortune's grounded, violent military action.
- **Visuals.** Realistic enough that weapons and violence look convincing. Beyond that, the look relies on color, lighting, atmosphere and effects more than on detailed geometry and textures.
- **Not decided yet:** story, world, factions, mission structure, progression, release platform.

---

## 3–6. Game design

Augmentation (§3), test loadouts (§4), combat simulation (§5), art direction (§6) and maps (§7) live in [`docs/design.md`](docs/design.md).

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

**Optional, paid:** Meshy (text or image to 3D) for props and starting meshes.

Log every third-party file and its license in `CREDITS.md`.

---

## 8. Target device and performance

Moto G 5G (2025): MediaTek Dimensity 6300, Mali-G57 MC2 GPU, 4 GB RAM, 720×1604 screen at 120 Hz.

Starting budgets. These are guesses: measure them on the phone in M0 and replace them.

| Budget | Start |
|---|---|
| Frame rate | 60 fps; locked 30 as a fallback setting |
| Render scale | 0.8–1.0 of 720p |
| Draw calls | ≤ 150 |
| Triangles on screen | ≤ 250k |
| Active enemies | ≤ 12 |
| Ragdolls simulating | ≤ 3, frozen after about 2.5 s |
| Blood decals | ≤ 48, oldest fade out |
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
| Right stick / R3 | Look / melee |
| LT (hold) / RT | Aim down sights / fire |
| LB / RB | Active parts 1 and 2 (LB: RX-9 time slowdown, tap on / tap off; owner, 2026-11-05) |
| A | Jump (wall-run on contact) |
| B | Slide / crouch |
| X | Reload (hold to interact) |
| Y | Tap: previous weapon. Hold: weapon wheel (owner, 2026-11-02; the MG barrel change needs another input in M3) |
| D-pad | Active part 3, items; left/right pick the shell type on guns that take several (Saiga-12K) |
| Menu / View | Pause / body status (built 2026-11-05) |

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

- Runs on pushes to `main` and on manual dispatch.
- Steps: download and cache Godot 4.7.2 and its export templates; import; run GUT and stop on failure; export a debug APK (arm64) signed with a keystore from repository secrets; publish it to a rolling `dev-latest` GitHub Release that the workflow creates.
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
3. **M2 – Parts system.** Loadout screen. Power, heat, mass and capacity. At least 8 passives with visible changes. The drone, whip and time slowdown.
   Done when three different loadouts play noticeably differently.
   Started 2026-11-05 (owner): the parts system foundation, the operative's base body (the GS-2 graft suit; helmet on or off, with the owner's face; Y on the body-status screen) on a body-status screen, and the time slowdown (RX-9 on LB). See design §3.4, §3.4a.
4. **M3 – Heavy weapons.** MG42-style machine gun with heat and barrel changes (the gun itself, its handling and a flat carry penalty were pulled into M1 by the owner on 2026-11-01; heat and barrel changes stay here). Heavy armor parts, two more actives, dismemberment, machine-gunner and anti-augment enemies.
   Done when sustained fire tears up a room and the phone holds its frame rate.
5. **M4 – Look and sound.** Art direction applied to two or three test areas, lighting, an audio pass.

What comes after the prototype gets decided then.

---

## 13. Open questions

- Title.
- Does the controller hold the phone? That decides whether gyro aiming is worth building.
- How far gore goes at the maximum setting.
- Real gun names (Five-seveN, MG42, SPAS-12) are fine in a prototype. Selling the game with them might need licenses, so decide before any release.
- Budget for Meshy and ElevenLabs, if any.
- Public or private repo.
