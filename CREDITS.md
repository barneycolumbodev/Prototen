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
| Pistol moving parts (body/slide/magazine split) | `assets/weapons/pistol_57/` | `raw_assets/weapons/pistol_57/split_parts.py` re-indexes the baked mesh. |
| MG42/A machine gun (model, 4K baked textures, moving parts) | `assets/weapons/mg42/` | `raw_assets/weapons/mg42/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the MG42 | `assets/characters/fp_arms_mg42/` | `raw_assets/characters/fp_arms_mg42/build.py`. |
| MG42 sounds (13: shots, tail, belt reload beats, draw/holster) | `assets/audio/sfx/mg42_*`, `draw_1`, `holster_1` | Synthesized by `raw_assets/audio/build_mg42_sfx.py` (numpy/scipy). |
| Bullet hole, flash and particle textures | generated at runtime | `src/vfx/fx.gd` |
