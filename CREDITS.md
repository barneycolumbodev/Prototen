# Credits and licenses

Every third-party file in the repository, with its source and license (CLAUDE.md §7).

| What | Where in repo | Source | Version | License |
|---|---|---|---|---|
| GUT (Godot Unit Test) | `addons/gut/` | https://github.com/bitwes/Gut | 9.7.1 | MIT (`addons/gut/LICENSE.md`) |
| GodotPrompter skills (12 of them) | `.claude/skills/` (all except the six project skills) | https://github.com/jame581/GodotPrompter @ d7b26cd | 2026-10-24 | MIT (`.claude/skills/GODOTPROMPTER-LICENSE.txt`) |

## Original assets (no third-party content)

| What | Where | How it was made |
|---|---|---|
| Gunplay sounds (29: shots, tail, reload, shells, impacts, confirms) | `assets/audio/sfx/` | Synthesized by `raw_assets/audio/build_weapon_sfx.py` (numpy/scipy). |
| Pistol 57 (model v2, 2K baked textures, body/slide/magazine parts) | `assets/weapons/pistol_57/` | `raw_assets/weapons/pistol_57/build.py` (Blender/bpy, procedural materials, high→low bake). |
| MG42/A machine gun (model, 4K baked textures, moving parts) | `assets/weapons/mg42/` | `raw_assets/weapons/mg42/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the MG42 | `assets/characters/fp_arms_mg42/` | `raw_assets/characters/fp_arms_mg42/build.py`. |
| MG42 sounds (13: shots, tail, belt reload beats, draw/holster) | `assets/audio/sfx/mg42_*`, `draw_1`, `holster_1` | Synthesized by `raw_assets/audio/build_mg42_sfx.py` (numpy/scipy). |
| Bullet hole, flash and particle textures | generated at runtime | `src/vfx/fx.gd` |
| RC-6 rail carbine (model, 4K baked textures, magazine/vent/glow/lens parts) | `assets/weapons/rail_carbine/` | `raw_assets/weapons/rail_carbine/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the rail carbine | `assets/characters/fp_arms_rail/` | `raw_assets/characters/fp_arms_rail/build.py`. |
| Rail carbine sounds (13: shots, tail, charge, ready, vent, overheat, reload beats, dry fire) | `assets/audio/sfx/rail_*` | Synthesized by `raw_assets/audio/build_rail_sfx.py` (numpy/scipy). |
| Railgun trail shader | `src/vfx/rail_trail.gdshader` | Written for this project. |
| Saiga-12K shotgun with PSO-pattern 1x optic (model, 4K baked textures, moving parts, tinted shell markers) | `assets/weapons/saiga12k/` | `raw_assets/weapons/saiga12k/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the Saiga-12K | `assets/characters/fp_arms_saiga/` | `raw_assets/characters/fp_arms_saiga/build.py`. |
| Saiga-12K sounds (17: shots, Dragon's Breath roar, tails, AK magazine and charging-handle beats, 12-gauge hulls, ember fire, shell-type click) | `assets/audio/sfx/saiga_*`, `shotshell_*`, `burn_1`, `ammo_select_1` | Synthesized by `raw_assets/audio/build_saiga_sfx.py` (numpy/scipy). |
| Bullet hole, flash, particle, ember and fire textures | generated at runtime | `src/vfx/fx.gd`, `src/weapons/ballistics.gd` |
