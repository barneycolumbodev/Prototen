# Credits and licenses

Every third-party file in the repository, with its source and license (CLAUDE.md §7).

| What | Where in repo | Source | Version | License |
|---|---|---|---|---|
| GUT (Godot Unit Test) | `addons/gut/` | https://github.com/bitwes/Gut | 9.7.1 | MIT (`addons/gut/LICENSE.md`) |
| Noto Serif TC (Black) and Noto Sans TC (Bold), only the unicode-range chunks the signs use | `raw_assets/env/fonts/serif/`, `raw_assets/env/fonts/sans/` | npm `@fontsource/noto-serif-tc`, `@fontsource/noto-sans-tc` (Adobe/Google Noto CJK) | 5.1.0 | SIL OFL 1.1 (`OFL.txt` in each folder). Used to draw the sign textures and neon tubes; no font file ships in the game. |
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
| M14/P battle rifle (model, 4K baked textures, slide/magazine/stock parts) | `assets/weapons/m14p/` | `raw_assets/weapons/m14p/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the M14/P | `assets/characters/fp_arms_m14p/` | `raw_assets/characters/fp_arms_m14p/build.py`. |
| M14/P sounds (9: shots, tail, reload beats, dry fire) | `assets/audio/sfx/m14_*` | Synthesized by `raw_assets/audio/build_m14_sfx.py` (numpy/scipy). |
| Weapon wheel icons (5) | `assets/ui/weapon_icons/` | Rendered from the game models by `raw_assets/ui/weapon_icons/build.py`. |
| Weapon wheel sounds (2) | `assets/audio/sfx/wheel_*` | Synthesized by `raw_assets/audio/build_ui_sfx.py`. |
| Triad enemy (rigged body and clothes, 2K painted textures, 17 animation clips, severable parts with flesh caps) | `assets/characters/triad/` | `raw_assets/characters/triad/build.py` (Blender/bpy metaballs, voxel remesh, numpy texture painting from baked position maps; IK-posed clips). No MakeHuman/MPFB or Quaternius assets: their sites aren't reachable from the session. |
| Enemy guns: Type 56 rifle, pump shotgun, SMG (low-poly, factor materials) | `assets/weapons/enemy/` | `raw_assets/weapons/enemy_guns/build.py`. |
| Blood textures (splat atlas, pool, droplet, mist) | `assets/gore/` | `raw_assets/gore/build_blood_textures.py` (numpy). |
| Enemy body shader (role tints, painted wounds, char), blood decal shader | `src/ai/triad.gdshader`, `src/gore/blood_decal.gdshader` | Written for this project. |
| Enemy and gore sounds (enemy shots ×3 guns, whizz/crack, pain, body fall, sever, reload; slide, mantle) | `assets/audio/sfx/enemy_*`, `whizz_*`, `body_fall_1`, `gore_sever_1`, `slide_1`, `mantle_1` | Synthesized by `raw_assets/audio/build_enemy_sfx.py` (numpy/scipy). |
| Environment material library (31 layers: brick, plaster, concrete, wet asphalt, pavers, granite, terrazzo, pier planks, dark wood, lacquer, cardboard, corrugated sheet, painted metal, roller shutter, rust, galvanised steel, grating, mosaic tile, glazed roof tile, roofing felt, epoxy floor, canvas, plastic, glass, damask wallpaper, emissive, lantern paper, and the sign/window/prop atlases) | `assets/env/world/` | `raw_assets/env/materials/build.py` and `raw_assets/env/atlases/build.py` (numpy/scipy/Pillow, procedural, tileable). |
| Chinatown docks map (geometry, colliders, spawn points, baked lightmap) | `assets/levels/chinatown/` | `raw_assets/levels/chinatown/build.py` + `bake.py` (Blender/bpy, Cycles CPU bake). |
| Night sky, harbour water, far-shore skyline, rain and steam shaders | `src/levels/chinatown/*.gdshader` | Written for this project. |
| Chinatown ambience (rain, harbour with ship horn, neon hum, kitchen extractor, radio tune) | `assets/audio/sfx/amb_*` | Synthesized by `raw_assets/audio/build_ambience.py` (numpy). |
| Enemy death voices (screams, choking, groans, last breath) and ricochet whines | `assets/audio/sfx/death_*`, `ricochet_*` | Synthesized by `raw_assets/audio/build_voice_sfx.py` (source-filter voice model) and `build_enemy_sfx.py` (numpy/scipy). No recordings. |
| Harbour night sky panorama | `assets/env/sky/harbour_night.png` | `raw_assets/env/sky/build_night_sky.py` (numpy, procedural). |
| RX-9 time-slowdown sounds (engage, release, heartbeat loop, denied) | `assets/audio/sfx/td_*` | Synthesized by `raw_assets/audio/build_augment_sfx.py` (numpy/scipy). |
| The operative: player base body in the GS-2 graft suit, helmet, and bare head with the owner's face (rigged, same skeleton as the triad) | `assets/characters/operative/` | `raw_assets/characters/operative/build.py` (signed distance fields in numpy meshed with surface nets via `raw_assets/_lib/sdf.py`, HIGH → LOW Cycles bake, analytic weights). Face from the owner's own photos (used with permission; photos not committed) via `likeness/capture.py`. |
| Face landmark model used to capture the owner's face (tool only, not shipped) | not in repo | MediaPipe Face Landmarker `face_landmarker.task`, Google, Apache-2.0 (storage.googleapis.com/mediapipe-models). |
| Canonical face mesh topology and UV layout (468 vertices, 898 triangles) | `raw_assets/characters/operative/likeness/face_tris.npy`, `face_uv.npy` | MediaPipe `canonical_face_model.obj`, Google, Apache-2.0 (github.com/google-ai-edge/mediapipe, `mediapipe/modules/face_geometry/data`). |
